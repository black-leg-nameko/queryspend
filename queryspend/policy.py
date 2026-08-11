"""Pure policy evaluator shared by API, CLI, and GitHub Action."""

from __future__ import annotations

from decimal import Decimal

from queryspend.confidence import CONFIDENCE_RANK
from queryspend.config import PolicyConfig
from queryspend.models import (
    ChangeType,
    Confidence,
    Decision,
    ModelContribution,
    ModelStatus,
    PolicyDecision,
    ReasonCode,
)


class Policy:
    @staticmethod
    def evaluate(models: list[ModelContribution], config: PolicyConfig) -> PolicyDecision:
        unknown_count = sum(item.status is not ModelStatus.KNOWN for item in models)
        minimum = CONFIDENCE_RANK[config.minimum_confidence]
        positive_usd_all = Decimal(0)
        positive_usd_eligible = Decimal(0)
        positive_bytes_all = Decimal(0)
        positive_bytes_eligible = Decimal(0)
        for item in models:
            usd = _decimal(item.monthly_cost_delta_usd)
            byte_delta = _decimal(item.monthly_bytes_delta)
            eligible = CONFIDENCE_RANK[item.confidence] >= minimum
            if usd is not None and usd > 0:
                positive_usd_all += usd
                if eligible:
                    positive_usd_eligible += usd
            if byte_delta is not None and byte_delta > 0:
                positive_bytes_all += byte_delta
                if _byte_confidence_rank(item) >= minimum:
                    positive_bytes_eligible += byte_delta
        thresholds = {
            "max_monthly_delta_usd": (
                str(config.max_monthly_delta_usd)
                if config.max_monthly_delta_usd is not None
                else None
            ),
            "max_monthly_delta_bytes": (
                str(config.max_monthly_delta_bytes)
                if config.max_monthly_delta_bytes is not None
                else None
            ),
            "minimum_confidence": config.minimum_confidence.value,
        }
        actuals: dict[str, str | int | None] = {
            "gross_monthly_increase_usd": str(positive_usd_all),
            "gross_monthly_increase_bytes": str(positive_bytes_all),
            "unknown_models": unknown_count,
        }
        usd_exceeded = (
            config.max_monthly_delta_usd is not None
            and positive_usd_eligible > config.max_monthly_delta_usd
        )
        bytes_exceeded = (
            config.max_monthly_delta_bytes is not None
            and positive_bytes_eligible > Decimal(config.max_monthly_delta_bytes)
        )
        if usd_exceeded or bytes_exceeded:
            reason = "usd_threshold_exceeded" if usd_exceeded else "bytes_threshold_exceeded"
            decision = Decision.BLOCK if config.action == "block" else Decision.WARN
            return PolicyDecision(
                decision=decision, reason=reason, thresholds=thresholds, actuals=actuals
            )
        confidence_shortfall = (
            config.max_monthly_delta_usd is not None
            and positive_usd_all > config.max_monthly_delta_usd
        ) or (
            config.max_monthly_delta_bytes is not None
            and positive_bytes_all > Decimal(config.max_monthly_delta_bytes)
        )
        if confidence_shortfall:
            return PolicyDecision(
                decision=Decision.WARN,
                reason="threshold_exceeded_below_minimum_confidence",
                thresholds=thresholds,
                actuals=actuals,
            )
        if unknown_count:
            if config.unknown_behavior == "block":
                return PolicyDecision(
                    decision=Decision.BLOCK,
                    reason="blocked_by_unknown_policy",
                    thresholds=thresholds,
                    actuals=actuals,
                )
            if config.unknown_behavior == "ignore":
                return PolicyDecision(
                    decision=Decision.PASS,
                    reason="unknown_models_ignored",
                    thresholds=thresholds,
                    actuals=actuals,
                )
            decision = (
                Decision.WARN
                if config.max_monthly_delta_usd is None
                and config.max_monthly_delta_bytes is None
                else Decision.UNKNOWN
            )
            return PolicyDecision(
                decision=decision,
                reason="unknown_models_present",
                thresholds=thresholds,
                actuals=actuals,
            )
        return PolicyDecision(
            decision=Decision.PASS,
            reason="within_thresholds",
            thresholds=thresholds,
            actuals=actuals,
        )


def _decimal(value: str | None) -> Decimal | None:
    return Decimal(value) if value is not None else None


def _byte_confidence_rank(item: ModelContribution) -> int:
    """Price-free confidence used only by an explicit byte threshold."""

    if item.monthly_bytes_delta is None or item.status in {
        ModelStatus.ERROR,
        ModelStatus.UNSUPPORTED,
    }:
        return 0
    reasons = set(item.reason_codes)
    allowed = {
        ReasonCode.UNKNOWN_PRICE,
        ReasonCode.FREQUENCY_OVERRIDDEN,
        ReasonCode.REFERENCED_TABLE_COUNT_UNKNOWN,
        ReasonCode.CLUSTERED_TABLE_UPPER_BOUND,
    }
    if reasons - allowed:
        return 0
    if ReasonCode.CLUSTERED_TABLE_UPPER_BOUND in reasons:
        return CONFIDENCE_RANK[Confidence.LOW]
    if (
        item.change_type in {ChangeType.ADDED, ChangeType.DELETED}
        or ReasonCode.REFERENCED_TABLE_COUNT_UNKNOWN in reasons
    ):
        return CONFIDENCE_RANK[Confidence.MEDIUM]
    return CONFIDENCE_RANK[Confidence.HIGH]
