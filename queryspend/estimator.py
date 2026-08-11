"""Decimal-only recurring BigQuery analysis cost estimation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal

MIB = 2**20
TIB = 2**40
SIX_PLACES = Decimal("0.000001")


@dataclass(frozen=True)
class Estimate:
    base_billed_bytes: int
    head_billed_bytes: int
    monthly_bytes_delta: Decimal
    monthly_cost_delta_usd: Decimal | None


def estimated_billed_bytes(raw_bytes: int, table_count: int | None) -> int:
    """Apply the documented per-query/per-table minimum approximation."""

    if raw_bytes < 0:
        raise ValueError("raw_bytes must not be negative")
    if table_count is not None and table_count < 0:
        raise ValueError("table_count must not be negative")
    if raw_bytes == 0 and table_count == 0:
        return 0
    minimum = 10 * MIB
    if table_count is not None:
        minimum = max(minimum, table_count * 10 * MIB)
    target = max(raw_bytes, minimum)
    return ((target + MIB - 1) // MIB) * MIB


def estimate_recurring_delta(
    *,
    base_raw_bytes: int,
    base_table_count: int | None,
    head_raw_bytes: int,
    head_table_count: int | None,
    runs_per_month: Decimal,
    price_per_tib_usd: Decimal | None,
) -> Estimate:
    """Calculate one model's recurring monthly delta without binary floats."""

    if not runs_per_month.is_finite() or runs_per_month < 0:
        raise ValueError("runs_per_month must be a finite non-negative Decimal")
    if price_per_tib_usd is not None and (
        not price_per_tib_usd.is_finite() or price_per_tib_usd <= 0
    ):
        raise ValueError("price_per_tib_usd must be a finite positive Decimal")
    base_billed = estimated_billed_bytes(base_raw_bytes, base_table_count)
    head_billed = estimated_billed_bytes(head_raw_bytes, head_table_count)
    monthly_bytes = (Decimal(head_billed) - Decimal(base_billed)) * runs_per_month
    monthly_cost = None
    if price_per_tib_usd is not None:
        monthly_cost = monthly_bytes / Decimal(TIB) * price_per_tib_usd
    return Estimate(
        base_billed_bytes=base_billed,
        head_billed_bytes=head_billed,
        monthly_bytes_delta=monthly_bytes,
        monthly_cost_delta_usd=monthly_cost,
    )


def decimal_string(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value.quantize(SIX_PLACES), "f")


def cents_string(value: Decimal) -> str:
    rounded = value.quantize(Decimal("0.01"))
    return f"{rounded:+,.2f}"


def nearest_rank_percentile(values: list[Decimal], percentile: int) -> Decimal:
    if not values:
        raise ValueError("percentile requires at least one value")
    if not 1 <= percentile <= 100:
        raise ValueError("percentile must be between 1 and 100")
    ordered = sorted(values)
    rank = (Decimal(percentile) / Decimal(100) * Decimal(len(ordered))).to_integral_value(
        rounding=ROUND_CEILING
    )
    return ordered[int(rank) - 1]
