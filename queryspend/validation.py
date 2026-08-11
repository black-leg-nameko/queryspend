"""Auditable technical-gate-v1 validation evaluator."""

from __future__ import annotations

import glob
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from queryspend.estimator import decimal_string, nearest_rank_percentile
from queryspend.exceptions import InputError
from queryspend.models import Decision, ModelStatus, QuerySpendReport

VALIDATION_SCHEMA = "https://queryspend.dev/schemas/validation/v1.json"


class ValidationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Observation(ValidationModel):
    schema_version: Literal[1] = 1
    case_id: str
    model_unique_id: str
    policy_threshold_usd: Decimal
    actual_monthly_delta_usd: Decimal
    actual_monthly_bytes_delta: Decimal
    actual_runs_per_month: Decimal
    ground_truth_attributed: bool
    source: str
    observation_window_days: int
    observation_complete: bool = True

    @field_validator(
        "policy_threshold_usd",
        "actual_monthly_delta_usd",
        "actual_monthly_bytes_delta",
        "actual_runs_per_month",
        mode="before",
    )
    @classmethod
    def decimal_strings_only(cls, value: object) -> Decimal:
        if not isinstance(value, str):
            raise ValueError("validation decimals must be quoted strings")
        try:
            parsed = Decimal(value)
        except InvalidOperation as error:
            raise ValueError("validation decimal is invalid") from error
        if not parsed.is_finite():
            raise ValueError("validation decimal must be finite")
        return parsed


class ValidationMetrics(ValidationModel):
    corpus_cases: int
    observations: int
    eligible_ape_cases: int
    excluded_small_actual_cases: int
    unknown_prediction_cases: int
    median_ape_percent: str | None
    p90_ape_percent: str | None
    cost_weighted_attribution_percent: str | None
    false_blocker_percent: str | None
    false_blockers: int
    actual_non_block_cases: int
    coverage_percent: str | None
    absolute_error_usd: str


class ValidationReport(ValidationModel):
    schema_: str = Field(
        default=VALIDATION_SCHEMA, alias="schema", serialization_alias="schema"
    )
    schema_version: Literal[1] = 1
    profile: Literal["technical-gate-v1"] = "technical-gate-v1"
    evaluated_at: str
    decision: Literal["pass", "fail"]
    failed_criteria: list[str]
    metrics: ValidationMetrics
    events: list[dict[str, object]]

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


def evaluate_validation(prediction_pattern: str, observations_path: Path) -> ValidationReport:
    predictions = _load_predictions(prediction_pattern)
    observations = _load_observations(observations_path)
    reports_by_case: dict[str, QuerySpendReport] = {}
    for path, prediction_report in predictions:
        case_id = prediction_report.run.case_id or path.stem
        if case_id in reports_by_case:
            raise InputError(f"Duplicate prediction case_id: {case_id}")
        reports_by_case[case_id] = prediction_report
    apes: list[Decimal] = []
    absolute_error = Decimal(0)
    excluded_small = 0
    unknown_predictions = 0
    attributed_numerator = Decimal(0)
    attributed_denominator = Decimal(0)
    known_cost_bearing = 0
    total_cost_bearing = 0
    actual_by_case: dict[str, Decimal] = defaultdict(Decimal)
    threshold_by_case: dict[str, Decimal] = {}
    for observation in observations:
        candidate_report = reports_by_case.get(observation.case_id)
        model = None
        if candidate_report is not None:
            model = next(
                (
                    item
                    for item in candidate_report.models
                    if item.unique_id == observation.model_unique_id
                ),
                None,
            )
        predicted = (
            Decimal(model.monthly_cost_delta_usd)
            if model is not None
            and model.status is ModelStatus.KNOWN
            and model.monthly_cost_delta_usd is not None
            else None
        )
        if predicted is None:
            unknown_predictions += 1
        else:
            absolute_error += abs(predicted - observation.actual_monthly_delta_usd)
        if observation.actual_monthly_delta_usd != 0:
            total_cost_bearing += 1
            if predicted is not None:
                known_cost_bearing += 1
        if (
            observation.observation_complete
            and observation.actual_monthly_delta_usd != 0
            and abs(observation.actual_monthly_delta_usd) >= Decimal("10")
        ):
            if predicted is not None:
                apes.append(
                    abs(predicted - observation.actual_monthly_delta_usd)
                    / abs(observation.actual_monthly_delta_usd)
                    * Decimal(100)
                )
        elif abs(observation.actual_monthly_delta_usd) < Decimal("10"):
            excluded_small += 1
        if observation.ground_truth_attributed:
            weight = abs(observation.actual_monthly_delta_usd)
            attributed_denominator += weight
            if predicted is not None and _same_nonzero_sign(
                predicted, observation.actual_monthly_delta_usd
            ):
                attributed_numerator += weight
        actual_by_case[observation.case_id] += max(
            observation.actual_monthly_delta_usd, Decimal(0)
        )
        threshold_by_case[observation.case_id] = observation.policy_threshold_usd

    false_blockers = 0
    actual_non_block = 0
    for case_id, actual_increase in actual_by_case.items():
        threshold = threshold_by_case[case_id]
        if actual_increase <= threshold:
            actual_non_block += 1
            candidate_report = reports_by_case.get(case_id)
            if (
                candidate_report is not None
                and candidate_report.policy.decision is Decision.BLOCK
                and candidate_report.policy.reason
                in {"usd_threshold_exceeded", "bytes_threshold_exceeded"}
            ):
                false_blockers += 1
    median = _median(apes) if apes else None
    p90 = nearest_rank_percentile(apes, 90) if apes else None
    attribution = (
        attributed_numerator / attributed_denominator * Decimal(100)
        if attributed_denominator
        else None
    )
    false_rate = (
        Decimal(false_blockers) / Decimal(actual_non_block) * Decimal(100)
        if actual_non_block
        else None
    )
    coverage = (
        Decimal(known_cost_bearing) / Decimal(total_cost_bearing) * Decimal(100)
        if total_cost_bearing
        else None
    )
    failed: list[str] = []
    if len(apes) < 8:
        failed.append("eligible_ape_sample_below_8")
    if median is None or median > Decimal(15):
        failed.append("median_ape_above_15_percent")
    if p90 is None or p90 > Decimal(30):
        failed.append("p90_ape_above_30_percent")
    if attribution is None or attribution < Decimal(80):
        failed.append("cost_weighted_attribution_below_80_percent")
    if false_rate is None or false_rate > Decimal(5):
        failed.append("false_blocker_above_5_percent_or_no_denominator")
    metrics = ValidationMetrics(
        corpus_cases=len(reports_by_case),
        observations=len(observations),
        eligible_ape_cases=len(apes),
        excluded_small_actual_cases=excluded_small,
        unknown_prediction_cases=unknown_predictions,
        median_ape_percent=decimal_string(median),
        p90_ape_percent=decimal_string(p90),
        cost_weighted_attribution_percent=decimal_string(attribution),
        false_blocker_percent=decimal_string(false_rate),
        false_blockers=false_blockers,
        actual_non_block_cases=actual_non_block,
        coverage_percent=decimal_string(coverage),
        absolute_error_usd=decimal_string(absolute_error) or "0.000000",
    )
    return ValidationReport(
        evaluated_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        decision="fail" if failed else "pass",
        failed_criteria=failed,
        metrics=metrics,
        events=[
            {
                "name": "validation_evaluated",
                "properties": {
                    "corpus_size": len(reports_by_case),
                    "decision": "fail" if failed else "pass",
                    "median_ape_percent": decimal_string(median),
                    "p90_ape_percent": decimal_string(p90),
                    "attribution_percent": decimal_string(attribution),
                    "false_blocker_percent": decimal_string(false_rate),
                },
            }
        ],
    )


def _load_predictions(pattern: str) -> list[tuple[Path, QuerySpendReport]]:
    paths = [Path(item) for item in sorted(glob.glob(pattern))]
    if not paths:
        raise InputError(f"Prediction pattern matched no files: {pattern}")
    reports: list[tuple[Path, QuerySpendReport]] = []
    for path in paths:
        try:
            reports.append(
                (path, QuerySpendReport.model_validate_json(path.read_text(encoding="utf-8")))
            )
        except (OSError, UnicodeError, ValueError) as error:
            raise InputError(f"Invalid prediction report {path}: {error}") from error
    return reports


def _load_observations(path: Path) -> list[Observation]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise InputError(f"Could not read observations {path}: {error}") from error
    observations: list[Observation] = []
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            observations.append(Observation.model_validate_json(line))
        except ValueError as error:
            raise InputError(f"Invalid observation {path}:{number}: {error}") from error
    if not observations:
        raise InputError("Observation corpus is empty")
    return observations


def _median(values: list[Decimal]) -> Decimal:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / Decimal(2)


def _same_nonzero_sign(left: Decimal, right: Decimal) -> bool:
    return left != 0 and right != 0 and (left > 0) == (right > 0)
