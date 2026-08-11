"""Deterministic evidence-completeness confidence labels."""

from __future__ import annotations

from queryspend.models import ChangeType, Confidence, DryRunEvidence, ReasonCode

CONFIDENCE_RANK = {
    Confidence.UNKNOWN: 0,
    Confidence.LOW: 1,
    Confidence.MEDIUM: 2,
    Confidence.HIGH: 3,
}


def estimate_confidence(
    *,
    change_type: ChangeType,
    base: DryRunEvidence | None,
    head: DryRunEvidence | None,
    has_frequency: bool,
    has_price: bool,
) -> Confidence:
    if not has_frequency or not has_price:
        return Confidence.UNKNOWN
    evidence = [item for item in (base, head) if item is not None]
    if not evidence or any(item.status.value != "known" for item in evidence):
        return Confidence.UNKNOWN
    if any(ReasonCode.CLUSTERED_TABLE_UPPER_BOUND in item.reason_codes for item in evidence):
        return Confidence.LOW
    if change_type in {ChangeType.ADDED, ChangeType.DELETED}:
        return Confidence.MEDIUM
    if any(item.table_count is None for item in evidence):
        return Confidence.MEDIUM
    return Confidence.HIGH


def aggregate_confidence(confidences: list[Confidence]) -> Confidence:
    if not confidences:
        return Confidence.UNKNOWN
    return min(confidences, key=CONFIDENCE_RANK.__getitem__)

