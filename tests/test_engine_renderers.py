from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from queryspend.demo import build_demo_report
from queryspend.engine import evaluate
from queryspend.exceptions import AuthenticationError, ProviderGlobalError
from queryspend.models import (
    Decision,
    DryRunEvidence,
    EvaluationRequest,
    ModelStatus,
    ReasonCode,
)
from queryspend.providers.base import ProviderRequestError
from queryspend.providers.recorded import RecordedProvider
from queryspend.renderers import JsonRenderer, MarkdownRenderer, TerminalRenderer
from tests.helpers import manifest, model_node

ROOT = Path(__file__).resolve().parents[1]


class NeverProvider:
    def dry_run(self, request: object) -> object:
        raise AssertionError(f"provider must not be called: {request!r}")


class StaticProvider:
    def __init__(
        self,
        *,
        status: ModelStatus = ModelStatus.KNOWN,
        reason: ReasonCode | None = None,
        failure: ProviderRequestError | None = None,
    ) -> None:
        self.status = status
        self.reason = reason
        self.failure = failure
        self.calls: list[object] = []

    def dry_run(self, request: object) -> DryRunEvidence:
        self.calls.append(request)
        if self.failure is not None:
            raise self.failure
        side = request.side
        return DryRunEvidence(
            status=self.status,
            raw_bytes=2**40 if side == "base" else 2 * 2**40,
            table_count=1,
            location="US",
            statement_type="SELECT",
            timestamp="2026-08-11T00:00:00Z",
            latency_ms=1,
            sql_sha256=request.sql_sha256,
            reason_codes=[self.reason] if self.reason else [],
        )


def config_file(tmp_path: Path, *, price: bool = True, frequency: bool = True) -> Path:
    path = tmp_path / "queryspend.yml"
    lines = ["version: 1", "warehouse:", "  billing_project: test"]
    if price:
        lines.append('  price_per_tib_usd: "6.25"')
    lines.extend(["frequencies:", "  models:"])
    if frequency:
        lines.append('    model.test.orders: "30"')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_demo_report_has_known_unknown_and_no_sql() -> None:
    report = build_demo_report()
    assert report.run.simulated is True
    assert report.policy.decision is Decision.WARN
    assert report.summary.known_models == 2
    assert report.summary.unknown_models == 3
    # Integer byte evidence plus MiB billing rounding is preserved in JSON.
    assert report.summary.known_monthly_delta_usd == "487.499893"
    serialized = JsonRenderer().render(report)
    assert "select *" not in serialized.lower()
    assert "compiled_code" not in serialized
    assert '"sql_included": false' in serialized
    schema = json.loads((ROOT / "schemas/report/v1.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(report.json_dict())


def test_config_schema_requires_decimal_strings() -> None:
    schema = json.loads((ROOT / "schemas/config/v1.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    assert not list(
        validator.iter_errors(
            {"version": 1, "warehouse": {"price_per_tib_usd": "6.25"}}
        )
    )
    assert list(
        validator.iter_errors({"version": 1, "warehouse": {"price_per_tib_usd": 6.25}})
    )


def test_renderers_share_one_decision_and_escape_untrusted_names() -> None:
    report = build_demo_report()
    report.models[0].unique_id = "model.test.<script>|`bad`\x1b"
    terminal = TerminalRenderer().render(report)
    markdown = MarkdownRenderer().render(report)
    json_output = JsonRenderer().render(report)
    for rendered in (terminal, markdown, json_output):
        assert report.policy.decision.value in rendered.lower()
    assert "<script>" not in markdown
    assert "\x1b" not in terminal
    assert "<!-- queryspend-report:v1 -->" in markdown
    assert "model.test.&lt;script&gt;" in markdown
    assert "unknown_downstream_data_shape" in markdown


def test_no_change_makes_zero_provider_calls(tmp_path: Path) -> None:
    path = manifest(
        tmp_path / "same.json",
        nodes={"model.test.orders": model_node("model.test.orders")},
    )
    report = evaluate(
        EvaluationRequest(base_manifest=path, head_manifest=path), provider=NeverProvider()
    )
    assert report.policy.decision is Decision.PASS
    assert report.policy.reason == ReasonCode.NO_CHANGED_MODELS.value
    assert report.models == []


def test_modified_view_is_partial_unknown_without_provider(tmp_path: Path) -> None:
    base = manifest(
        tmp_path / "base.json",
        nodes={
            "model.test.orders_view": model_node(
                "model.test.orders_view", materialized="view", sql="select 1"
            )
        },
    )
    head = manifest(
        tmp_path / "head.json",
        nodes={
            "model.test.orders_view": model_node(
                "model.test.orders_view",
                materialized="view",
                sql="select 2",
                checksum="changed",
            )
        },
    )
    report = evaluate(
        EvaluationRequest(base_manifest=base, head_manifest=head), provider=NeverProvider()
    )
    assert report.models[0].status is ModelStatus.UNKNOWN
    assert report.models[0].reason_codes == [ReasonCode.UNKNOWN_VIEW_CONSUMER_COST]
    assert report.summary.complete is False


def test_recorded_provider_report_is_deterministic_except_run_fields() -> None:
    base = ROOT / "fixtures/northstar/base/manifest.json"
    head = ROOT / "fixtures/northstar/head/manifest.json"
    config = ROOT / "fixtures/northstar/queryspend.yml"
    recording = ROOT / "fixtures/northstar/recorded_evidence.json"
    first = evaluate(
        EvaluationRequest(base_manifest=base, head_manifest=head, config=config),
        provider=RecordedProvider(recording),
    ).json_dict()
    second = evaluate(
        EvaluationRequest(base_manifest=base, head_manifest=head, config=config),
        provider=RecordedProvider(recording),
    ).json_dict()
    for result in (first, second):
        run = result["run"]
        assert isinstance(run, dict)
        for key in ("id", "started_at", "duration_ms"):
            run.pop(key)
        events = result["events"]
        assert isinstance(events, list)
        for event in events:
            if isinstance(event, dict) and event.get("name") == "check_started":
                properties = event.get("properties")
                if isinstance(properties, dict):
                    properties.pop("run_id", None)
            if isinstance(event, dict) and event.get("name") == "check_completed":
                properties = event.get("properties")
                if isinstance(properties, dict):
                    properties.pop("duration_ms", None)
    assert first == second


def test_table_price_and_frequency_unknown_boundaries(tmp_path: Path) -> None:
    base = manifest(
        tmp_path / "base.json",
        nodes={"model.test.orders": model_node("model.test.orders", sql="select 1")},
    )
    head = manifest(
        tmp_path / "head.json",
        nodes={
            "model.test.orders": model_node(
                "model.test.orders", sql="select 2", checksum="changed"
            )
        },
    )
    no_price = evaluate(
        EvaluationRequest(
            base_manifest=base,
            head_manifest=head,
            config=config_file(tmp_path, price=False),
        ),
        provider=StaticProvider(),
    )
    assert no_price.models[0].monthly_bytes_delta is not None
    assert no_price.models[0].monthly_cost_delta_usd is None
    assert ReasonCode.UNKNOWN_PRICE in no_price.models[0].reason_codes
    no_frequency = evaluate(
        EvaluationRequest(
            base_manifest=base,
            head_manifest=head,
            config=config_file(tmp_path, frequency=False),
        ),
        provider=StaticProvider(),
    )
    assert no_frequency.models[0].monthly_bytes_delta is None
    assert ReasonCode.UNKNOWN_FREQUENCY in no_frequency.models[0].reason_codes


def test_added_deleted_and_materialization_boundaries(tmp_path: Path) -> None:
    base = manifest(
        tmp_path / "base.json",
        nodes={
            "model.test.orders": model_node("model.test.orders"),
            "model.test.transition": model_node("model.test.transition"),
            "model.test.incremental": model_node(
                "model.test.incremental", materialized="incremental"
            ),
        },
    )
    head = manifest(
        tmp_path / "head.json",
        nodes={
            "model.test.orders": model_node(
                "model.test.orders", sql="select 2", checksum="changed"
            ),
            "model.test.transition": model_node(
                "model.test.transition", materialized="view"
            ),
            "model.test.incremental": model_node(
                "model.test.incremental", materialized="incremental", checksum="changed"
            ),
        },
    )
    report = evaluate(
        EvaluationRequest(
            base_manifest=base,
            head_manifest=head,
            config=config_file(tmp_path),
        ),
        provider=StaticProvider(),
    )
    by_id = {model.unique_id: model for model in report.models}
    assert by_id["model.test.transition"].reason_codes == [
        ReasonCode.UNKNOWN_MATERIALIZATION_TRANSITION
    ]
    assert by_id["model.test.incremental"].status is ModelStatus.UNSUPPORTED
    assert ReasonCode.UNSUPPORTED_MATERIALIZATION in by_id[
        "model.test.incremental"
    ].reason_codes


def test_missing_sql_package_scope_and_provider_unknown(tmp_path: Path) -> None:
    config = config_file(tmp_path)
    base = manifest(
        tmp_path / "base.json",
        nodes={
            "model.test.orders": model_node("model.test.orders", sql=None),
            "model.other.package": model_node(
                "model.other.package", package="other", sql="select 1"
            ),
        },
    )
    head = manifest(
        tmp_path / "head.json",
        nodes={
            "model.test.orders": model_node(
                "model.test.orders", sql="select 2", checksum="changed"
            ),
            "model.other.package": model_node(
                "model.other.package", package="other", sql="select 2", checksum="changed"
            ),
        },
    )
    report = evaluate(
        EvaluationRequest(base_manifest=base, head_manifest=head, config=config),
        provider=StaticProvider(),
    )
    by_id = {model.unique_id: model for model in report.models}
    assert ReasonCode.MISSING_COMPILED_SQL in by_id["model.test.orders"].reason_codes
    assert ReasonCode.PACKAGE_MODEL_OUT_OF_SCOPE in by_id["model.other.package"].reason_codes
    unknown = evaluate(
        EvaluationRequest(
            base_manifest=manifest(
                tmp_path / "external-base.json",
                nodes={"model.test.orders": model_node("model.test.orders", sql="select 1")},
            ),
            head_manifest=manifest(
                tmp_path / "external-head.json",
                nodes={
                    "model.test.orders": model_node(
                        "model.test.orders", sql="select 2", checksum="changed"
                    )
                },
            ),
            config=config,
        ),
        provider=StaticProvider(
            status=ModelStatus.UNKNOWN,
            reason=ReasonCode.EXTERNAL_SOURCE_ESTIMATE_UNAVAILABLE,
        ),
    )
    assert ReasonCode.EXTERNAL_SOURCE_ESTIMATE_UNAVAILABLE in unknown.models[0].reason_codes


@pytest.mark.parametrize("authentication", [True, False])
def test_global_provider_failure_has_partial_diagnostic_report(
    tmp_path: Path, authentication: bool
) -> None:
    base = manifest(
        tmp_path / "base.json",
        nodes={"model.test.orders": model_node("model.test.orders")},
    )
    head = manifest(
        tmp_path / "head.json",
        nodes={
            "model.test.orders": model_node(
                "model.test.orders", sql="select 2", checksum="changed"
            )
        },
    )
    failure = ProviderRequestError(
        ReasonCode.PERMISSION_DENIED if authentication else ReasonCode.PROVIDER_ERROR,
        "safe remediation",
        authentication=authentication,
    )
    expected = AuthenticationError if authentication else ProviderGlobalError
    with pytest.raises(expected) as captured:
        evaluate(
            EvaluationRequest(
                base_manifest=base,
                head_manifest=head,
                config=config_file(tmp_path),
            ),
            provider=StaticProvider(failure=failure),
        )
    assert captured.value.partial_report is not None
    assert captured.value.partial_report.models[0].status is ModelStatus.ERROR
