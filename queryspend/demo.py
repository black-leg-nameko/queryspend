"""Credential-free, network-free synthetic demonstration."""

from __future__ import annotations

from importlib.resources import as_file, files

from queryspend.engine import evaluate
from queryspend.models import EvaluationRequest, QuerySpendReport
from queryspend.providers.recorded import RecordedProvider


def build_demo_report() -> QuerySpendReport:
    root = files("queryspend.data") / "demo"
    with (
        as_file(root / "base_manifest.json") as base,
        as_file(root / "head_manifest.json") as head,
        as_file(root / "queryspend.yml") as config,
        as_file(root / "recorded_evidence.json") as recording,
    ):
        return evaluate(
            EvaluationRequest(base_manifest=base, head_manifest=head, config=config),
            provider=RecordedProvider(recording),
            simulated=True,
            case_id="northstar-retail-demo",
        )

