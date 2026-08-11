"""Regenerate checked-in offline demo aliases and synthetic validation fixtures."""

from __future__ import annotations

import json
import shutil
from decimal import Decimal
from pathlib import Path

from queryspend.models import (
    AffectedReason,
    ChangeType,
    Confidence,
    Decision,
    InputInfo,
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
from queryspend.renderers.json import JsonRenderer

ROOT = Path(__file__).resolve().parents[1]

CASES: list[tuple[str, str, str, str | None]] = [
    ("northstar-remove-partition-filter", "model.northstar.fct_orders", "640", "620"),
    ("northstar-column-projection", "model.northstar.dim_customer", "-180", "-175"),
    ("northstar-added-table", "model.northstar.fct_returns", "250", "260"),
    ("northstar-deleted-table", "model.northstar.legacy_rollup", "-90", "-95"),
    ("harbor-join-fanout", "model.harbor.fct_matches", "800", "760"),
    ("harbor-source-scan", "model.harbor.search_events", "500", "520"),
    ("harbor-cluster-upper", "model.harbor.fct_quotes", "120", "114"),
    ("lumen-source-reduction", "model.lumen.feature_usage", "200", "210"),
    ("lumen-view-consumer", "model.lumen.active_users_view", "20", None),
    ("lumen-zero-change", "model.lumen.dim_plan", "0", "5"),
]


def main() -> None:
    _copy_demo_aliases()
    predictions = ROOT / "validation" / "predictions"
    predictions.mkdir(parents=True, exist_ok=True)
    observation_lines: list[str] = []
    renderer = JsonRenderer()
    for index, (case_id, unique_id, actual, predicted) in enumerate(CASES, 1):
        report = _prediction_report(index, case_id, unique_id, predicted)
        (predictions / f"{case_id}.json").write_text(
            renderer.render(report), encoding="utf-8"
        )
        observation_lines.append(
            json.dumps(
                {
                    "schema_version": 1,
                    "case_id": case_id,
                    "model_unique_id": unique_id,
                    "policy_threshold_usd": "1000.000000",
                    "actual_monthly_delta_usd": f"{Decimal(actual):.6f}",
                    "actual_monthly_bytes_delta": (
                        f"{Decimal(actual) * Decimal(2**40) / Decimal('6.25'):.6f}"
                    ),
                    "actual_runs_per_month": "30",
                    "ground_truth_attributed": True,
                    "source": "synthetic_fixture_not_live",
                    "observation_window_days": 7,
                    "observation_complete": True,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    observations = ROOT / "validation" / "observations.jsonl"
    observations.parent.mkdir(parents=True, exist_ok=True)
    observations.write_text("\n".join(observation_lines) + "\n", encoding="utf-8")


def _copy_demo_aliases() -> None:
    source = ROOT / "queryspend" / "data" / "demo"
    fixture = ROOT / "fixtures" / "northstar"
    for side in ("base", "head"):
        target = fixture / side / "manifest.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / f"{side}_manifest.json", target)
    shutil.copyfile(source / "queryspend.yml", fixture / "queryspend.yml")
    shutil.copyfile(source / "recorded_evidence.json", fixture / "recorded_evidence.json")


def _prediction_report(
    index: int, case_id: str, unique_id: str, predicted: str | None
) -> QuerySpendReport:
    known = predicted is not None
    prediction = f"{Decimal(predicted):.6f}" if predicted is not None else None
    status = ModelStatus.KNOWN if known else ModelStatus.UNKNOWN
    model = ModelContribution(
        unique_id=unique_id,
        display_name=unique_id.rsplit(".", 1)[-1],
        change_type=ChangeType.MODIFIED,
        affected_reason=AffectedReason.CHANGED,
        base_materialization="table",
        head_materialization="table",
        runs_per_month="30",
        frequency_source="config_model",
        base=SideEvidence(raw_bytes=1, estimated_billed_bytes=10485760, table_count=1),
        head=SideEvidence(raw_bytes=2, estimated_billed_bytes=20971520, table_count=1),
        monthly_bytes_delta="314572800.000000" if known else None,
        monthly_cost_delta_usd=prediction,
        confidence=Confidence.HIGH if known else Confidence.UNKNOWN,
        status=status,
        reason_codes=[] if known else [ReasonCode.UNKNOWN_VIEW_CONSUMER_COST],
        fingerprint_base=f"base-{index:02d}",
        fingerprint_head=f"head-{index:02d}",
    )
    return QuerySpendReport(
        run=RunInfo(
            id=f"00000000-0000-0000-0000-{index:012d}",
            started_at="2026-08-11T00:00:00Z",
            duration_ms=1,
            queryspend_version="0.1.0",
            case_id=case_id,
            simulated=True,
        ),
        inputs=InputInfo(
            base_manifest_sha256=f"{index:064x}",
            head_manifest_sha256=f"{index + 100:064x}",
            dbt_manifest_versions=[10 + (index % 3), 10 + ((index + 1) % 3)],
            provider="bigquery",
            billing_model="on_demand",
            billing_project="synthetic-validation",
            location="US",
            price_per_tib_usd="6.250000",
        ),
        summary=Summary(
            affected_models=1,
            known_models=1 if known else 0,
            unknown_models=0 if known else 1,
            complete=known,
            known_monthly_bytes_delta="314572800.000000" if known else None,
            known_monthly_delta_usd=prediction,
            gross_monthly_increase_usd=(
                prediction if prediction is not None and Decimal(prediction) > 0 else "0.000000"
            )
            if known
            else None,
            gross_monthly_decrease_usd=(
                prediction if prediction is not None and Decimal(prediction) < 0 else "0.000000"
            )
            if known
            else None,
            confidence=Confidence.HIGH if known else Confidence.UNKNOWN,
            largest_known_contributor=unique_id if known else None,
        ),
        policy=PolicyDecision(
            decision=Decision.PASS if known else Decision.WARN,
            reason="within_thresholds" if known else "unknown_models_present",
            thresholds={"max_monthly_delta_usd": "1000.000000"},
            actuals={"unknown_models": 0 if known else 1},
        ),
        models=[model],
        privacy=PrivacyInfo(),
    )


if __name__ == "__main__":
    main()
