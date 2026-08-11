"""Versioned public and internal data models.

Report models intentionally have no field capable of storing raw SQL.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

REPORT_SCHEMA = "https://queryspend.dev/schemas/report/v1.json"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ModelStatus(StrEnum):
    KNOWN = "known"
    UNKNOWN = "unknown"
    UNSUPPORTED = "unsupported"
    ERROR = "error"


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class Decision(StrEnum):
    PASS = "pass"  # noqa: S105 - policy result, not a credential
    WARN = "warn"
    BLOCK = "block"
    UNKNOWN = "unknown"


class ChangeType(StrEnum):
    ADDED = "added"
    DELETED = "deleted"
    MODIFIED = "modified"
    MATERIALIZATION_CHANGED = "materialization_changed"
    UNCHANGED = "unchanged"


class AffectedReason(StrEnum):
    CHANGED = "changed"
    DOWNSTREAM = "downstream"


class ReasonCode(StrEnum):
    MISSING_COMPILED_SQL = "missing_compiled_sql"
    UNKNOWN_FREQUENCY = "unknown_frequency"
    UNKNOWN_PRICE = "unknown_price"
    UNSUPPORTED_MANIFEST_VERSION = "unsupported_manifest_version"
    UNSUPPORTED_ADAPTER = "unsupported_adapter"
    UNSUPPORTED_MATERIALIZATION = "unsupported_materialization"
    UNKNOWN_MATERIALIZATION_TRANSITION = "unknown_materialization_transition"
    UNKNOWN_VIEW_CONSUMER_COST = "unknown_view_consumer_cost"
    UNKNOWN_DOWNSTREAM_DATA_SHAPE = "unknown_downstream_data_shape"
    EXTERNAL_SOURCE_ESTIMATE_UNAVAILABLE = "external_source_estimate_unavailable"
    REFERENCED_TABLE_COUNT_UNKNOWN = "referenced_table_count_unknown"
    REFERENCED_TABLE_METADATA_UNAVAILABLE = "referenced_table_metadata_unavailable"
    LOCATION_MISMATCH = "location_mismatch"
    DRY_RUN_SYNTAX_ERROR = "dry_run_syntax_error"
    PERMISSION_DENIED = "permission_denied"
    RATE_LIMIT_EXHAUSTED = "rate_limit_exhausted"
    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_ERROR = "provider_error"
    NO_CHANGED_MODELS = "no_changed_models"
    CLUSTERED_TABLE_UPPER_BOUND = "clustered_table_upper_bound"
    FREQUENCY_OVERRIDDEN = "frequency_overridden"
    FREQUENCY_CHANGE_NOT_MODELED = "frequency_change_not_modeled"
    IDENTICAL_INPUTS = "identical_inputs"
    PACKAGE_MODEL_OUT_OF_SCOPE = "package_model_out_of_scope"
    UNSUPPORTED_STATEMENT_TYPE = "unsupported_statement_type"


class EvaluationRequest(StrictModel):
    """Inputs accepted by both the CLI and Python API."""

    base_manifest: Path
    head_manifest: Path
    config: Path | None = None


class DryRunRequest(StrictModel):
    model_unique_id: str
    side: str
    sql: str = Field(repr=False)
    sql_sha256: str
    billing_project: str
    location: str | None = None


class DryRunEvidence(StrictModel):
    status: ModelStatus = ModelStatus.KNOWN
    raw_bytes: int | None = None
    table_count: int | None = None
    location: str | None = None
    statement_type: str | None = None
    referenced_table_types: list[str] = Field(default_factory=list)
    clustered_table_detected: bool = False
    timestamp: str
    latency_ms: int
    sql_sha256: str
    fixture: bool = False
    reason_codes: list[ReasonCode] = Field(default_factory=list)


class SideEvidence(StrictModel):
    raw_bytes: int | None = None
    estimated_billed_bytes: int | None = None
    table_count: int | None = None
    location: str | None = None
    statement_type: str | None = None
    sql_sha256: str | None = None
    latency_ms: int | None = None
    fixture: bool = False


class ModelContribution(StrictModel):
    unique_id: str
    display_name: str | None = None
    change_type: ChangeType
    affected_reason: AffectedReason
    base_materialization: str | None = None
    head_materialization: str | None = None
    runs_per_month: str | None = None
    frequency_source: str | None = None
    base: SideEvidence | None = None
    head: SideEvidence | None = None
    monthly_bytes_delta: str | None = None
    monthly_cost_delta_usd: str | None = None
    confidence: Confidence = Confidence.UNKNOWN
    status: ModelStatus
    reason_codes: list[ReasonCode] = Field(default_factory=list)
    fingerprint_base: str | None = None
    fingerprint_head: str | None = None


class Diagnostic(StrictModel):
    level: str
    code: str
    message: str
    model_unique_id: str | None = None


class RunInfo(StrictModel):
    id: str
    started_at: str
    duration_ms: int
    queryspend_version: str
    case_id: str | None = None
    simulated: bool = False


class InputInfo(StrictModel):
    base_manifest_sha256: str
    head_manifest_sha256: str
    dbt_manifest_versions: list[int]
    provider: str
    billing_model: str
    billing_project: str | None = None
    location: str | None = None
    price_per_tib_usd: str | None = None


class Summary(StrictModel):
    affected_models: int
    known_models: int
    unknown_models: int
    unsupported_models: int = 0
    error_models: int = 0
    complete: bool
    known_monthly_bytes_delta: str | None = None
    known_monthly_delta_usd: str | None = None
    gross_monthly_increase_usd: str | None = None
    gross_monthly_decrease_usd: str | None = None
    confidence: Confidence
    largest_known_contributor: str | None = None


class PolicyDecision(StrictModel):
    decision: Decision
    reason: str
    thresholds: dict[str, str | None] = Field(default_factory=dict)
    actuals: dict[str, str | int | None] = Field(default_factory=dict)


class PrivacyInfo(StrictModel):
    sql_included: bool = False
    model_names_included: bool = True
    relation_names_included: bool = False


class LocalEvent(StrictModel):
    name: str
    properties: dict[str, str | int | bool | None] = Field(default_factory=dict)


class QuerySpendReport(StrictModel):
    schema_: str = Field(default=REPORT_SCHEMA, alias="schema", serialization_alias="schema")
    schema_version: int = 1
    run: RunInfo
    inputs: InputInfo
    summary: Summary
    policy: PolicyDecision
    models: list[ModelContribution]
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    events: list[LocalEvent] = Field(default_factory=list)
    privacy: PrivacyInfo = Field(default_factory=PrivacyInfo)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    def json_dict(self) -> dict[str, object]:
        """Return the canonical JSON-compatible representation."""

        return self.model_dump(mode="json", by_alias=True, exclude_none=False)
