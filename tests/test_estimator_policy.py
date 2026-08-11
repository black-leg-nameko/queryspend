from __future__ import annotations

from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from queryspend.confidence import aggregate_confidence, estimate_confidence
from queryspend.config import PolicyConfig
from queryspend.estimator import (
    MIB,
    TIB,
    cents_string,
    decimal_string,
    estimate_recurring_delta,
    estimated_billed_bytes,
    nearest_rank_percentile,
)
from queryspend.models import (
    AffectedReason,
    ChangeType,
    Confidence,
    Decision,
    DryRunEvidence,
    ModelContribution,
    ModelStatus,
    ReasonCode,
)
from queryspend.policy import Policy


def contribution(
    value: str | None,
    *,
    confidence: Confidence = Confidence.HIGH,
    status: ModelStatus = ModelStatus.KNOWN,
    byte_value: str | None = None,
    reasons: list[ReasonCode] | None = None,
) -> ModelContribution:
    return ModelContribution(
        unique_id=f"model.test.{value}",
        change_type=ChangeType.MODIFIED,
        affected_reason=AffectedReason.CHANGED,
        monthly_cost_delta_usd=value,
        monthly_bytes_delta=byte_value,
        confidence=confidence,
        status=status,
        reason_codes=reasons or [],
    )


@given(raw=st.integers(min_value=0, max_value=10**15), tables=st.integers(0, 100))
def test_minimum_billing_is_mib_aligned_and_not_below_raw(raw: int, tables: int) -> None:
    result = estimated_billed_bytes(raw, tables)
    assert result % MIB == 0
    assert result >= raw
    if raw == 0 and tables == 0:
        assert result == 0


def test_decimal_formula_gross_direction_and_zero() -> None:
    estimate = estimate_recurring_delta(
        base_raw_bytes=TIB,
        base_table_count=1,
        head_raw_bytes=2 * TIB,
        head_table_count=1,
        runs_per_month=Decimal(30),
        price_per_tib_usd=Decimal("6.25"),
    )
    assert estimate.monthly_bytes_delta == Decimal(30 * TIB)
    assert estimate.monthly_cost_delta_usd == Decimal("187.50")
    with pytest.raises(ValueError):
        estimated_billed_bytes(-1, 1)
    with pytest.raises(ValueError):
        estimated_billed_bytes(1, -1)
    assert estimated_billed_bytes(0, None) == 10 * MIB
    assert estimated_billed_bytes(1, 2) == 20 * MIB
    with pytest.raises(ValueError, match="runs_per_month"):
        estimate_recurring_delta(
            base_raw_bytes=0,
            base_table_count=0,
            head_raw_bytes=1,
            head_table_count=1,
            runs_per_month=Decimal("NaN"),
            price_per_tib_usd=None,
        )
    with pytest.raises(ValueError, match="price_per_tib_usd"):
        estimate_recurring_delta(
            base_raw_bytes=0,
            base_table_count=0,
            head_raw_bytes=1,
            head_table_count=1,
            runs_per_month=Decimal(1),
            price_per_tib_usd=Decimal(0),
        )
    assert decimal_string(None) is None
    assert decimal_string(Decimal("1.2345678")) == "1.234568"
    assert cents_string(Decimal("-1.235")) == "-1.24"


def test_percentile_validation_and_nearest_rank() -> None:
    assert nearest_rank_percentile([Decimal(1), Decimal(2), Decimal(100)], 90) == 100
    with pytest.raises(ValueError, match="at least one"):
        nearest_rank_percentile([], 90)
    with pytest.raises(ValueError, match="between"):
        nearest_rank_percentile([Decimal(1)], 0)


def evidence(
    *,
    status: ModelStatus = ModelStatus.KNOWN,
    count: int | None = 1,
    reasons: list[ReasonCode] | None = None,
) -> DryRunEvidence:
    return DryRunEvidence(
        status=status,
        raw_bytes=1,
        table_count=count,
        timestamp="2026-08-11T00:00:00Z",
        latency_ms=1,
        sql_sha256="a" * 64,
        reason_codes=reasons or [],
    )


def test_confidence_complete_truth_table() -> None:
    known = evidence()
    assert (
        estimate_confidence(
            change_type=ChangeType.MODIFIED,
            base=known,
            head=known,
            has_frequency=False,
            has_price=True,
        )
        is Confidence.UNKNOWN
    )
    assert (
        estimate_confidence(
            change_type=ChangeType.MODIFIED,
            base=None,
            head=None,
            has_frequency=True,
            has_price=True,
        )
        is Confidence.UNKNOWN
    )
    assert (
        estimate_confidence(
            change_type=ChangeType.MODIFIED,
            base=evidence(status=ModelStatus.UNKNOWN),
            head=known,
            has_frequency=True,
            has_price=True,
        )
        is Confidence.UNKNOWN
    )
    assert (
        estimate_confidence(
            change_type=ChangeType.MODIFIED,
            base=evidence(reasons=[ReasonCode.CLUSTERED_TABLE_UPPER_BOUND]),
            head=known,
            has_frequency=True,
            has_price=True,
        )
        is Confidence.LOW
    )
    assert (
        estimate_confidence(
            change_type=ChangeType.ADDED,
            base=None,
            head=known,
            has_frequency=True,
            has_price=True,
        )
        is Confidence.MEDIUM
    )
    assert (
        estimate_confidence(
            change_type=ChangeType.MODIFIED,
            base=evidence(count=None),
            head=known,
            has_frequency=True,
            has_price=True,
        )
        is Confidence.MEDIUM
    )
    assert (
        estimate_confidence(
            change_type=ChangeType.MODIFIED,
            base=known,
            head=known,
            has_frequency=True,
            has_price=True,
        )
        is Confidence.HIGH
    )
    assert aggregate_confidence([]) is Confidence.UNKNOWN
    assert aggregate_confidence([Confidence.HIGH, Confidence.LOW]) is Confidence.LOW


def test_policy_uses_gross_increase_not_savings() -> None:
    config = PolicyConfig.model_validate(
        {
            "max_monthly_delta_usd": "100",
            "action": "block",
            "minimum_confidence": "high",
        }
    )
    decision = Policy.evaluate([contribution("120"), contribution("-1000")], config)
    assert decision.decision is Decision.BLOCK
    assert decision.reason == "usd_threshold_exceeded"


def test_policy_unknown_and_confidence_truth_table() -> None:
    unknown = contribution(None, confidence=Confidence.UNKNOWN, status=ModelStatus.UNKNOWN)
    assert Policy.evaluate([unknown], PolicyConfig()).decision is Decision.WARN
    blocking = PolicyConfig.model_validate({"unknown_behavior": "block"})
    assert Policy.evaluate([unknown], blocking).decision is Decision.BLOCK
    ignored = PolicyConfig.model_validate({"unknown_behavior": "ignore"})
    assert Policy.evaluate([unknown], ignored).decision is Decision.PASS
    low = contribution("200", confidence=Confidence.LOW)
    threshold = PolicyConfig.model_validate(
        {"max_monthly_delta_usd": "100", "action": "block"}
    )
    decision = Policy.evaluate([low], threshold)
    assert decision.decision is Decision.WARN
    assert "below_minimum_confidence" in decision.reason


def test_explicit_byte_threshold_can_block_without_price() -> None:
    bytes_only = contribution(
        None,
        confidence=Confidence.UNKNOWN,
        status=ModelStatus.UNKNOWN,
        byte_value="200",
        reasons=[ReasonCode.UNKNOWN_PRICE],
    )
    config = PolicyConfig.model_validate(
        {"max_monthly_delta_bytes": 100, "action": "block"}
    )
    decision = Policy.evaluate([bytes_only], config)
    assert decision.decision is Decision.BLOCK
    assert decision.reason == "bytes_threshold_exceeded"
