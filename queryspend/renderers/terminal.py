"""Accessible no-ANSI terminal renderer."""

from __future__ import annotations

from decimal import Decimal

from queryspend.estimator import cents_string
from queryspend.models import ModelContribution, QuerySpendReport


class TerminalRenderer:
    def render(self, report: QuerySpendReport) -> str:
        summary = report.summary
        lines: list[str] = []
        if report.run.simulated:
            lines.append("SIMULATED DEMO — not a live BigQuery estimate")
        lines.append("QUERYSPEND — ESTIMATE, NOT AN INVOICE")
        lines.append(
            f"Decision: {report.policy.decision.value.upper()} ({_words(report.policy.reason)})"
        )
        lines.append(_cost_summary(report))
        not_known = (
            summary.unknown_models + summary.unsupported_models + summary.error_models
        )
        lines.append(
            f"Coverage: {summary.known_models} known / {summary.affected_models} affected; "
            f"{not_known} not known"
        )
        lines.append(f"Confidence: {summary.confidence.value}")
        largest = _largest(report.models)
        if largest is not None:
            lines.append(
                "Largest known contributor: "
                f"{_middle_truncate(largest.unique_id)} "
                f"({cents_string(Decimal(largest.monthly_cost_delta_usd or '0'))} USD/month)"
            )
        elif summary.affected_models == 0:
            lines.append("Largest known contributor: none (no changed models)")
        else:
            lines.append("Largest known contributor: none")
        lines.append("")
        lines.append(
            "Model                                      Change       Monthly delta       "
            "Confidence  Status"
        )
        lines.append("-" * 108)
        for model in _sorted_models(report.models)[:10]:
            value = (
                f"{cents_string(Decimal(model.monthly_cost_delta_usd))} USD/month"
                if model.monthly_cost_delta_usd is not None
                else "Unknown"
            )
            lines.append(
                f"{_middle_truncate(model.unique_id, 40):40} "
                f"{model.change_type.value:12} {value:19} "
                f"{model.confidence.value:11} {model.status.value.upper()}"
            )
            if model.reason_codes:
                lines.append("  Reasons: " + ", ".join(item.value for item in model.reason_codes))
        if len(report.models) > 10:
            lines.append(f"... {len(report.models) - 10} more model(s); see the JSON artifact.")
        if report.diagnostics:
            lines.append("")
            lines.append("Diagnostics:")
            for diagnostic in report.diagnostics:
                lines.append(f"- {diagnostic.code}: {_plain(diagnostic.message)}")
        lines.append("")
        lines.append(
            "Estimates use explicit frequency and price; unknown values are never treated as $0."
        )
        return "\n".join(lines) + "\n"


def _cost_summary(report: QuerySpendReport) -> str:
    if report.summary.affected_models == 0:
        return "Known monthly change: +0.00 USD/month (no model changes)"
    value = report.summary.known_monthly_delta_usd
    if value is None:
        return "Known monthly change: Unknown (no complete USD estimate)"
    amount = Decimal(value)
    direction = "increase" if amount >= 0 else "decrease"
    prefix = "Known monthly" if report.summary.complete else "Known monthly subtotal"
    return f"{prefix} {direction}: {cents_string(amount)} USD/month"


def _largest(models: list[ModelContribution]) -> ModelContribution | None:
    known = [item for item in models if item.monthly_cost_delta_usd is not None]
    if not known:
        return None
    return sorted(
        known,
        key=lambda item: (-abs(Decimal(item.monthly_cost_delta_usd or "0")), item.unique_id),
    )[0]


def _sorted_models(models: list[ModelContribution]) -> list[ModelContribution]:
    return sorted(
        models,
        key=lambda item: (
            -(abs(Decimal(item.monthly_cost_delta_usd)))
            if item.monthly_cost_delta_usd is not None
            else Decimal(1),
            item.unique_id,
        ),
    )


def _middle_truncate(value: str, limit: int = 64) -> str:
    clean = _plain(value)
    if len(clean) <= limit:
        return clean
    left = (limit - 3) // 2
    return clean[:left] + "..." + clean[-(limit - 3 - left) :]


def _plain(value: str) -> str:
    return "".join(char if char.isprintable() and char not in "\r\n\x1b" else "?" for char in value)


def _words(value: str) -> str:
    return value.replace("_", " ")
