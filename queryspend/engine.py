"""Shared evaluation pipeline for API, CLI, and GitHub Action."""

from __future__ import annotations

import hashlib
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast

from queryspend import __version__
from queryspend.confidence import aggregate_confidence, estimate_confidence
from queryspend.config import QuerySpendConfig, load_config, resolve_frequency
from queryspend.dbt_artifacts import ManifestNormalizer, NormalizedManifest, NormalizedNode
from queryspend.estimator import decimal_string, estimate_recurring_delta
from queryspend.exceptions import AuthenticationError, ProviderGlobalError, QuerySpendError
from queryspend.graph import AffectedNode, diff_and_affected
from queryspend.models import (
    AffectedReason,
    Confidence,
    Decision,
    Diagnostic,
    DryRunEvidence,
    DryRunRequest,
    EvaluationRequest,
    InputInfo,
    LocalEvent,
    ModelContribution,
    ModelStatus,
    PolicyDecision,
    PrivacyInfo,
    QuerySpendReport,
    ReasonCode,
    RunInfo,
    SideEvidence,
    Summary,
)
from queryspend.policy import Policy
from queryspend.providers.base import ProviderRequestError, WarehouseProvider

MAX_CONCURRENCY = 4


def evaluate(
    request: EvaluationRequest,
    *,
    provider: WarehouseProvider | None = None,
    normalizer: ManifestNormalizer | None = None,
    simulated: bool = False,
    case_id: str | None = None,
) -> QuerySpendReport:
    """Evaluate a base/head dbt artifact pair using one shared report object."""

    clock_start = time.monotonic()
    started_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    run_id = str(uuid.uuid4())
    config = load_config(request.config)
    artifact_normalizer = normalizer or ManifestNormalizer()
    base = artifact_normalizer.normalize(request.base_manifest)
    head = artifact_normalizer.normalize(request.head_manifest)
    affected = diff_and_affected(base, head)
    diagnostics: list[Diagnostic] = []
    if base.sha256 == head.sha256:
        diagnostics.append(
            Diagnostic(
                level="warning",
                code=ReasonCode.IDENTICAL_INPUTS.value,
                message="Base and head manifest contents are identical.",
            )
        )
    if not affected:
        diagnostics.append(
            Diagnostic(
                level="info",
                code=ReasonCode.NO_CHANGED_MODELS.value,
                message="No cost-affecting model changes were found.",
            )
        )
        return _finalize_report(
            run_id=run_id,
            started_at=started_at,
            clock_start=clock_start,
            case_id=case_id,
            simulated=simulated,
            base=base,
            head=head,
            config=config,
            models=[],
            diagnostics=diagnostics,
            policy=PolicyDecision(decision=Decision.PASS, reason="no_changed_models"),
            dry_run_events=[],
        )

    billing_project = config.warehouse.billing_project
    requests = _build_dry_run_requests(
        affected, billing_project or "", config.warehouse.location
    )
    provider_init_error: QuerySpendError | None = None
    actual_provider = provider
    if requests and actual_provider is None:
        try:
            from queryspend.providers.bigquery import BigQueryProvider

            actual_provider = BigQueryProvider(billing_project)
            resolved_project = getattr(actual_provider, "billing_project", None)
            assert isinstance(resolved_project, str)
            billing_project = resolved_project
            requests = _build_dry_run_requests(
                affected, billing_project, config.warehouse.location
            )
        except QuerySpendError as error:
            provider_init_error = error

    evidence: dict[tuple[str, str], DryRunEvidence] = {}
    failures: dict[tuple[str, str], ProviderRequestError] = {}
    if provider_init_error is not None:
        for key in requests:
            failures[key] = ProviderRequestError(
                ReasonCode.PERMISSION_DENIED,
                "Configure Application Default Credentials and least-privilege BigQuery roles",
                authentication=isinstance(provider_init_error, AuthenticationError),
            )
    elif requests:
        assert actual_provider is not None
        with ThreadPoolExecutor(max_workers=MAX_CONCURRENCY) as executor:
            future_keys = {
                executor.submit(actual_provider.dry_run, dry_request): key
                for key, dry_request in requests.items()
            }
            for future in as_completed(future_keys):
                key = future_keys[future]
                try:
                    evidence[key] = future.result()
                except ProviderRequestError as error:
                    failures[key] = error
                except Exception as error:  # sanitized at the provider boundary
                    failures[key] = ProviderRequestError(
                        ReasonCode.PROVIDER_ERROR, "Provider failed unexpectedly"
                    )
                    _ = error

    root_project = head.root_project or base.root_project
    contributions = [
        _build_contribution(
            item,
            config=config,
            evidence=evidence,
            failures=failures,
            root_project=root_project,
            run_id=run_id,
        )
        for item in affected
    ]
    policy = Policy.evaluate(contributions, config.policy)
    dry_run_events = [
        LocalEvent(
            name="dry_run_completed",
            properties={
                "provider": "bigquery",
                "status": result.status.value,
                "latency_ms": result.latency_ms,
                "bytes_bucket": _bytes_bucket(result.raw_bytes),
                "reason_code": result.reason_codes[0].value if result.reason_codes else None,
            },
        )
        for _, result in sorted(evidence.items())
    ]
    report = _finalize_report(
        run_id=run_id,
        started_at=started_at,
        clock_start=clock_start,
        case_id=case_id,
        simulated=simulated,
        base=base,
        head=head,
        config=config,
        models=contributions,
        diagnostics=diagnostics,
        policy=policy,
        dry_run_events=dry_run_events,
        billing_project=billing_project,
    )
    if requests and not evidence:
        if failures and all(item.authentication for item in failures.values()):
            raise AuthenticationError(
                "Every eligible BigQuery dry-run failed authentication or authorization. "
                "No SQL or provider message was logged.",
                partial_report=report,
            )
        raise ProviderGlobalError(
            "Every eligible BigQuery dry-run failed after retry. No stale estimate was used.",
            partial_report=report,
        )
    return report


def _build_dry_run_requests(
    affected: list[AffectedNode], billing_project: str, location: str | None
) -> dict[tuple[str, str], DryRunRequest]:
    requests: dict[tuple[str, str], DryRunRequest] = {}
    for item in affected:
        if item.affected_reason is AffectedReason.DOWNSTREAM:
            continue
        before_materialization = item.base.materialized if item.base else None
        after_materialization = item.head.materialized if item.head else None
        materials = {value for value in (before_materialization, after_materialization) if value}
        if not materials or not materials <= {"table"}:
            continue
        for side, node in (("base", item.base), ("head", item.head)):
            if node is None or node.compiled_code is None or node.sql_sha256 is None:
                continue
            requests[(item.unique_id, side)] = DryRunRequest(
                model_unique_id=item.unique_id,
                side=side,
                sql=node.compiled_code,
                sql_sha256=node.sql_sha256,
                billing_project=billing_project,
                location=location,
            )
    return requests


def _build_contribution(
    item: AffectedNode,
    *,
    config: QuerySpendConfig,
    evidence: dict[tuple[str, str], DryRunEvidence],
    failures: dict[tuple[str, str], ProviderRequestError],
    root_project: str | None,
    run_id: str,
) -> ModelContribution:
    node = item.head or item.base
    assert node is not None
    display_id = _display_model_id(item.unique_id, config, run_id)
    display_name = node.name if config.privacy.include_model_names else None
    base_materialized = item.base.materialized if item.base else None
    head_materialized = item.head.materialized if item.head else None
    frequency, frequency_source, overridden = resolve_frequency(
        config,
        item.unique_id,
        item.head.meta if item.head else None,
        item.base.meta if item.base else None,
    )
    reasons: list[ReasonCode] = []
    if overridden:
        reasons.append(ReasonCode.FREQUENCY_OVERRIDDEN)
    common: dict[str, Any] = {
        "unique_id": display_id,
        "display_name": display_name,
        "change_type": item.change_type,
        "affected_reason": item.affected_reason,
        "base_materialization": base_materialized,
        "head_materialization": head_materialized,
        "runs_per_month": str(frequency) if frequency is not None else None,
        "frequency_source": frequency_source,
        "fingerprint_base": item.base.fingerprint if item.base else None,
        "fingerprint_head": item.head.fingerprint if item.head else None,
    }
    if root_project and node.package_name != root_project:
        return ModelContribution(
            **common,
            status=ModelStatus.UNSUPPORTED,
            reason_codes=[*reasons, ReasonCode.PACKAGE_MODEL_OUT_OF_SCOPE],
        )
    if item.affected_reason is AffectedReason.DOWNSTREAM:
        return ModelContribution(
            **common,
            status=ModelStatus.UNKNOWN,
            reason_codes=[*reasons, ReasonCode.UNKNOWN_DOWNSTREAM_DATA_SHAPE],
        )
    materializations = {
        value for value in (base_materialized, head_materialized) if value is not None
    }
    if not materializations <= {"table", "view"}:
        return ModelContribution(
            **common,
            status=ModelStatus.UNSUPPORTED,
            reason_codes=[*reasons, ReasonCode.UNSUPPORTED_MATERIALIZATION],
        )
    if len(materializations) > 1:
        return ModelContribution(
            **common,
            status=ModelStatus.UNKNOWN,
            reason_codes=[*reasons, ReasonCode.UNKNOWN_MATERIALIZATION_TRANSITION],
        )
    if materializations == {"view"}:
        return ModelContribution(
            **common,
            status=ModelStatus.UNKNOWN,
            reason_codes=[*reasons, ReasonCode.UNKNOWN_VIEW_CONSUMER_COST],
        )

    base_result = evidence.get((item.unique_id, "base"))
    head_result = evidence.get((item.unique_id, "head"))
    side_failures = [
        failure
        for key in ((item.unique_id, "base"), (item.unique_id, "head"))
        if (failure := failures.get(key)) is not None
    ]
    if side_failures:
        return ModelContribution(
            **common,
            base=_side_evidence(base_result),
            head=_side_evidence(head_result),
            status=ModelStatus.ERROR,
            reason_codes=_unique_reasons(
                [*reasons, *(failure.reason_code for failure in side_failures)]
            ),
        )
    missing_sql = (
        item.base is not None and item.base.compiled_code is None
    ) or (item.head is not None and item.head.compiled_code is None)
    if missing_sql:
        return ModelContribution(
            **common,
            base=_side_evidence(base_result),
            head=_side_evidence(head_result),
            status=ModelStatus.UNKNOWN,
            reason_codes=[*reasons, ReasonCode.MISSING_COMPILED_SQL],
        )
    provider_reasons = [
        reason for result in (base_result, head_result) if result for reason in result.reason_codes
    ]
    if any(
        result is not None and result.status is not ModelStatus.KNOWN
        for result in (base_result, head_result)
    ):
        unsupported = any(
            result is not None and result.status is ModelStatus.UNSUPPORTED
            for result in (base_result, head_result)
        )
        return ModelContribution(
            **common,
            base=_side_evidence(base_result),
            head=_side_evidence(head_result),
            status=ModelStatus.UNSUPPORTED if unsupported else ModelStatus.UNKNOWN,
            reason_codes=_unique_reasons([*reasons, *provider_reasons]),
        )
    if frequency is None:
        reasons.append(ReasonCode.UNKNOWN_FREQUENCY)
    if config.warehouse.price_per_tib_usd is None:
        reasons.append(ReasonCode.UNKNOWN_PRICE)
    reasons.extend(provider_reasons)
    if frequency is None:
        return ModelContribution(
            **common,
            base=_side_evidence(base_result),
            head=_side_evidence(head_result),
            confidence=Confidence.UNKNOWN,
            status=ModelStatus.UNKNOWN,
            reason_codes=_unique_reasons(reasons),
        )
    base_raw, base_count = _side_values(item.base, base_result)
    head_raw, head_count = _side_values(item.head, head_result)
    estimate = estimate_recurring_delta(
        base_raw_bytes=base_raw,
        base_table_count=base_count,
        head_raw_bytes=head_raw,
        head_table_count=head_count,
        runs_per_month=frequency,
        price_per_tib_usd=config.warehouse.price_per_tib_usd,
    )
    confidence = estimate_confidence(
        change_type=item.change_type,
        base=base_result,
        head=head_result,
        has_frequency=True,
        has_price=config.warehouse.price_per_tib_usd is not None,
    )
    base_side = _side_evidence(base_result)
    head_side = _side_evidence(head_result)
    if item.base is None:
        base_side = SideEvidence(raw_bytes=0, estimated_billed_bytes=0, table_count=0)
    elif base_side is not None:
        base_side.estimated_billed_bytes = estimate.base_billed_bytes
    if item.head is None:
        head_side = SideEvidence(raw_bytes=0, estimated_billed_bytes=0, table_count=0)
    elif head_side is not None:
        head_side.estimated_billed_bytes = estimate.head_billed_bytes
    status = (
        ModelStatus.KNOWN
        if estimate.monthly_cost_delta_usd is not None
        else ModelStatus.UNKNOWN
    )
    return ModelContribution(
        **common,
        base=base_side,
        head=head_side,
        monthly_bytes_delta=decimal_string(estimate.monthly_bytes_delta),
        monthly_cost_delta_usd=decimal_string(estimate.monthly_cost_delta_usd),
        confidence=confidence,
        status=status,
        reason_codes=_unique_reasons(reasons),
    )


def _side_values(
    node: NormalizedNode | None, result: DryRunEvidence | None
) -> tuple[int, int | None]:
    if node is None:
        return 0, 0
    assert result is not None and result.raw_bytes is not None
    return result.raw_bytes, result.table_count


def _side_evidence(result: DryRunEvidence | None) -> SideEvidence | None:
    if result is None:
        return None
    return SideEvidence(
        raw_bytes=result.raw_bytes,
        table_count=result.table_count,
        location=result.location,
        statement_type=result.statement_type,
        sql_sha256=result.sql_sha256,
        latency_ms=result.latency_ms,
        fixture=result.fixture,
    )


def _display_model_id(unique_id: str, config: QuerySpendConfig, run_id: str) -> str:
    if config.privacy.include_model_names:
        return _sanitize_identifier(unique_id)
    digest = hashlib.sha256(f"{run_id}:{unique_id}".encode()).hexdigest()[:12]
    return f"model:{digest}"


def _sanitize_identifier(value: str) -> str:
    return "".join(char if char.isprintable() and char not in "\r\n\x1b" else "?" for char in value)


def _unique_reasons(reasons: list[ReasonCode]) -> list[ReasonCode]:
    return sorted(set(reasons), key=lambda item: item.value)


def _finalize_report(
    *,
    run_id: str,
    started_at: str,
    clock_start: float,
    case_id: str | None,
    simulated: bool,
    base: NormalizedManifest,
    head: NormalizedManifest,
    config: QuerySpendConfig,
    models: list[ModelContribution],
    diagnostics: list[Diagnostic],
    policy: PolicyDecision,
    dry_run_events: list[LocalEvent],
    billing_project: str | None = None,
) -> QuerySpendReport:
    known_costs = [
        Decimal(item.monthly_cost_delta_usd)
        for item in models
        if item.monthly_cost_delta_usd is not None
    ]
    known_bytes = [
        Decimal(item.monthly_bytes_delta)
        for item in models
        if item.monthly_bytes_delta is not None
    ]
    known_contributors = [item for item in models if item.status is ModelStatus.KNOWN]
    largest = None
    if known_contributors:
        largest = sorted(
            known_contributors,
            key=lambda item: (
                -abs(Decimal(cast(str, item.monthly_cost_delta_usd))),
                item.unique_id,
            ),
        )[0].unique_id
    summary = Summary(
        affected_models=len(models),
        known_models=sum(item.status is ModelStatus.KNOWN for item in models),
        unknown_models=sum(item.status is ModelStatus.UNKNOWN for item in models),
        unsupported_models=sum(item.status is ModelStatus.UNSUPPORTED for item in models),
        error_models=sum(item.status is ModelStatus.ERROR for item in models),
        complete=all(item.status is ModelStatus.KNOWN for item in models),
        known_monthly_bytes_delta=decimal_string(sum(known_bytes, Decimal(0)))
        if known_bytes
        else None,
        known_monthly_delta_usd=decimal_string(sum(known_costs, Decimal(0)))
        if known_costs
        else None,
        gross_monthly_increase_usd=decimal_string(
            sum((value for value in known_costs if value > 0), Decimal(0))
        )
        if known_costs
        else None,
        gross_monthly_decrease_usd=decimal_string(
            sum((value for value in known_costs if value < 0), Decimal(0))
        )
        if known_costs
        else None,
        confidence=aggregate_confidence([item.confidence for item in known_contributors]),
        largest_known_contributor=largest,
    )
    duration_ms = round((time.monotonic() - clock_start) * 1000)
    events = [
        LocalEvent(
            name="check_started",
            properties={
                "run_id": run_id,
                "manifest_versions": f"{base.schema_version},{head.schema_version}",
                "affected_count": len(models),
            },
        ),
        *dry_run_events,
        LocalEvent(
            name="check_completed",
            properties={
                "duration_ms": duration_ms,
                "known_count": summary.known_models,
                "unknown_count": summary.unknown_models,
                "decision": policy.decision.value,
                "confidence": summary.confidence.value,
            },
        ),
    ]
    if policy.decision.value == "block":
        events.append(
            LocalEvent(
                name="policy_blocked",
                properties={
                    "threshold_type": policy.reason,
                    "reason": policy.reason,
                    "confidence": summary.confidence.value,
                },
            )
        )
    return QuerySpendReport(
        run=RunInfo(
            id=run_id,
            started_at=started_at,
            duration_ms=duration_ms,
            queryspend_version=__version__,
            case_id=case_id,
            simulated=simulated,
        ),
        inputs=InputInfo(
            base_manifest_sha256=base.sha256,
            head_manifest_sha256=head.sha256,
            dbt_manifest_versions=[base.schema_version, head.schema_version],
            provider="bigquery",
            billing_model=config.warehouse.billing_model,
            billing_project=billing_project or config.warehouse.billing_project,
            location=config.warehouse.location,
            price_per_tib_usd=decimal_string(config.warehouse.price_per_tib_usd),
        ),
        summary=summary,
        policy=policy,
        models=models,
        diagnostics=diagnostics,
        events=events,
        privacy=PrivacyInfo(
            sql_included=False,
            model_names_included=config.privacy.include_model_names,
            relation_names_included=config.privacy.include_relation_names,
        ),
    )


def _bytes_bucket(value: int | None) -> str:
    if value is None:
        return "unknown"
    if value == 0:
        return "0"
    if value < 2**30:
        return "lt_1_gib"
    if value < 2**40:
        return "lt_1_tib"
    return "gte_1_tib"
