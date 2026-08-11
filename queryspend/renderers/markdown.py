"""GitHub-safe Markdown renderer with an idempotent comment marker."""

from __future__ import annotations

from decimal import Decimal

from queryspend.estimator import cents_string
from queryspend.models import QuerySpendReport
from queryspend.renderers.terminal import _largest

MARKER = "<!-- queryspend-report:v1 -->"


class MarkdownRenderer:
    def render(self, report: QuerySpendReport) -> str:
        summary = report.summary
        heading = "## queryspend cost estimate"
        if report.run.simulated:
            heading += " — SIMULATED DEMO"
        not_known = summary.unknown_models + summary.unsupported_models + summary.error_models
        value = summary.known_monthly_delta_usd
        if summary.affected_models == 0:
            cost = "No cost-affecting model changes"
        elif value is None:
            cost = "Unknown — no complete USD estimate"
        else:
            label = "Known monthly change" if summary.complete else "Known monthly subtotal"
            cost = f"{label}: **{cents_string(Decimal(value))} USD/month**"
        threshold = report.policy.thresholds.get("max_monthly_delta_usd") or "not configured"
        lines = [
            MARKER,
            heading,
            "",
            "> Estimate, not an invoice. Unknown values are never treated as $0.",
            "",
            f"**Decision:** `{report.policy.decision.value.upper()}` — "
            f"{_escape(report.policy.reason)}  ",
            f"**Cost:** {cost}  ",
            f"**Coverage:** {summary.known_models} known / {summary.affected_models} affected; "
            f"{not_known} not known  ",
            f"**Confidence:** `{summary.confidence.value}`  ",
            f"**USD threshold:** `{threshold}`",
            "",
        ]
        largest = _largest(report.models)
        if largest is not None:
            lines.append(
                f"Largest known contributor: `{_escape_code(largest.unique_id)}` "
                f"({cents_string(Decimal(largest.monthly_cost_delta_usd or '0'))} USD/month)."
            )
            lines.append("")
        lines.extend(
            [
                "<details>",
                "<summary>Model evidence and uncertainty</summary>",
                "",
                "| Model | Change | Monthly delta | Confidence | Status |",
                "|---|---|---:|---|---|",
            ]
        )
        for model in report.models[:10]:
            delta = (
                f"{cents_string(Decimal(model.monthly_cost_delta_usd))} USD/month"
                if model.monthly_cost_delta_usd is not None
                else "Unknown — " + ", ".join(reason.value for reason in model.reason_codes)
            )
            lines.append(
                f"| `{_escape_code(model.unique_id)}` | {_escape(model.change_type.value)} | "
                f"{_escape(delta)} | {_escape(model.confidence.value)} | "
                f"{_escape(model.status.value.upper())} |"
            )
        if len(report.models) > 10:
            lines.append(
                f"\n{len(report.models) - 10} more model(s) are in "
                "`queryspend-report.json`."
            )
        if not report.models:
            lines.append("| _No cost-affecting model changes_ | — | — | — | PASS |")
        lines.extend(["", "</details>", "", "Full evidence: `queryspend-report.json`", ""])
        return "\n".join(lines)


def _escape(value: object) -> str:
    text = str(value)
    clean = "".join(char if char.isprintable() and char not in "\r\n\x1b" else "?" for char in text)
    return clean.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("|", "\\|")


def _escape_code(value: str) -> str:
    return _escape(value).replace("`", "\\`")
