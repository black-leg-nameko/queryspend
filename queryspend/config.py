"""Strict, explicit configuration loading."""

from __future__ import annotations

import os
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)
from yaml.composer import ComposerError
from yaml.constructor import ConstructorError
from yaml.events import AliasEvent

from queryspend.exceptions import InputError
from queryspend.models import Confidence

MAX_CONFIG_BYTES = 1024 * 1024
MAX_DECIMAL = Decimal("1e30")


class _StrictSafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects aliases and duplicate mapping keys."""

    def compose_node(
        self, parent: yaml.Node | None, index: int
    ) -> yaml.Node | None:
        if self.check_event(AliasEvent):  # type: ignore[no-untyped-call]
            event = self.peek_event()  # type: ignore[no-untyped-call]
            raise ComposerError(
                "while composing queryspend config",
                None,
                "YAML aliases are not supported",
                event.start_mark,
            )
        return super().compose_node(parent, index)

    def construct_mapping(self, node: yaml.Node, deep: bool = False) -> dict[object, object]:
        if not isinstance(node, yaml.MappingNode):
            raise ConstructorError(
                None, None, "expected a mapping node", node.start_mark
            )
        mapping: dict[object, object] = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                duplicate = key in mapping
            except TypeError as error:
                raise ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "found an unhashable mapping key",
                    key_node.start_mark,
                ) from error
            if duplicate:
                raise ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "found a duplicate mapping key",
                    key_node.start_mark,
                )
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


def _decimal_string(value: object, *, allow_zero: bool, field_name: str) -> Decimal | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a quoted decimal string")
    try:
        parsed = Decimal(value)
    except InvalidOperation as error:
        raise ValueError(f"{field_name} must be a finite decimal string") from error
    if not parsed.is_finite() or parsed.copy_abs() > MAX_DECIMAL:
        raise ValueError(f"{field_name} must be a finite decimal within supported bounds")
    if parsed < 0 or (not allow_zero and parsed == 0):
        qualifier = "non-negative" if allow_zero else "positive"
        raise ValueError(f"{field_name} must be {qualifier}")
    return parsed


class ConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WarehouseConfig(ConfigModel):
    provider: Literal["bigquery"] = "bigquery"
    billing_model: Literal["on_demand"] = "on_demand"
    billing_project: str | None = None
    location: str | None = None
    price_per_tib_usd: Decimal | None = None

    @field_validator("price_per_tib_usd", mode="before")
    @classmethod
    def validate_price(cls, value: object) -> Decimal | None:
        return _decimal_string(
            value, allow_zero=False, field_name="warehouse.price_per_tib_usd"
        )

    @field_validator("billing_project", "location")
    @classmethod
    def reject_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("value must not be blank")
        if value is not None and (
            len(value) > 1024
            or any(ord(character) < 32 or ord(character) == 127 for character in value)
        ):
            raise ValueError("value contains unsupported characters or exceeds 1024 characters")
        return value


class FrequenciesConfig(ConfigModel):
    default_runs_per_month: Decimal | None = None
    models: dict[str, Decimal] = Field(default_factory=dict)

    @field_validator("default_runs_per_month", mode="before")
    @classmethod
    def validate_default(cls, value: object) -> Decimal | None:
        return _decimal_string(
            value, allow_zero=True, field_name="frequencies.default_runs_per_month"
        )

    @field_validator("models", mode="before")
    @classmethod
    def validate_models(cls, value: object) -> dict[str, Decimal]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ValueError("frequencies.models must be a mapping")
        parsed: dict[str, Decimal] = {}
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise ValueError("frequency model keys must be non-empty dbt unique IDs")
            if len(key) > 4096 or any(
                ord(character) < 32 or ord(character) == 127 for character in key
            ):
                raise ValueError("frequency model keys contain unsupported characters")
            result = _decimal_string(
                item, allow_zero=True, field_name="frequencies.models value"
            )
            assert result is not None
            parsed[key] = result
        return parsed


class PolicyConfig(ConfigModel):
    max_monthly_delta_usd: Decimal | None = None
    max_monthly_delta_bytes: int | None = None
    action: Literal["warn", "block"] = "warn"
    minimum_confidence: Confidence = Confidence.HIGH
    unknown_behavior: Literal["warn", "block", "ignore"] = "warn"

    @field_validator("max_monthly_delta_usd", mode="before")
    @classmethod
    def validate_usd_threshold(cls, value: object) -> Decimal | None:
        return _decimal_string(
            value, allow_zero=True, field_name="policy.max_monthly_delta_usd"
        )

    @field_validator("max_monthly_delta_bytes", mode="before")
    @classmethod
    def validate_byte_threshold(cls, value: object) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("policy.max_monthly_delta_bytes must be a non-negative integer")
        return value


class PrivacyConfig(ConfigModel):
    include_model_names: bool = True
    include_relation_names: bool = False


class QuerySpendConfig(ConfigModel):
    version: Literal[1] = 1
    warehouse: WarehouseConfig = Field(default_factory=WarehouseConfig)
    frequencies: FrequenciesConfig = Field(default_factory=FrequenciesConfig)
    policy: PolicyConfig = Field(default_factory=PolicyConfig)
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig)

    @model_validator(mode="after")
    def validate_provider_contract(self) -> QuerySpendConfig:
        # Literal fields already reject unsupported values with useful paths.
        return self


def find_config(start: Path) -> Path | None:
    """Find .queryspend.yml up to and including the nearest Git root."""

    current = start.resolve()
    if current.is_file():
        current = current.parent
    while True:
        candidate = current / ".queryspend.yml"
        if candidate.is_file():
            return candidate
        if (current / ".git").exists() or current.parent == current:
            return None
        current = current.parent


def load_config(path: Path | None, *, search_from: Path | None = None) -> QuerySpendConfig:
    """Load a strict config, or zero-config defaults when none is found."""

    resolved = path
    if resolved is None:
        resolved = find_config(search_from or Path.cwd())
    data: dict[str, Any] = {}
    if resolved is not None:
        try:
            resolved = resolved.resolve(strict=True)
            if not resolved.is_file():
                raise InputError(f"Config is not a regular file: {resolved}")
            size = resolved.stat().st_size
            if size > MAX_CONFIG_BYTES:
                raise InputError(f"Config exceeds {MAX_CONFIG_BYTES} bytes: {resolved}")
            source = resolved.read_text(encoding="utf-8")
            loader = _StrictSafeLoader(source)
            try:
                loaded = loader.get_single_data()
            finally:
                loader.dispose()  # type: ignore[no-untyped-call]
        except InputError:
            raise
        except yaml.YAMLError as error:
            mark = getattr(error, "problem_mark", None)
            location = f" at line {mark.line + 1}, column {mark.column + 1}" if mark else ""
            raise InputError(f"Could not read or parse config {resolved}{location}") from error
        except (OSError, RuntimeError, UnicodeError) as error:
            raise InputError(f"Could not read config {resolved}") from error
        if loaded is None:
            loaded = {}
        if not isinstance(loaded, dict):
            raise InputError(f"Config root must be a mapping: {resolved}")
        data = loaded

    # Safe environment overrides support ADC quota-project based CI without secrets in YAML.
    warehouse = data.setdefault("warehouse", {})
    if not isinstance(warehouse, dict):
        raise InputError("warehouse must be a mapping")
    if "billing_project" not in warehouse and os.getenv("QUERYSPEND_BILLING_PROJECT"):
        warehouse["billing_project"] = os.environ["QUERYSPEND_BILLING_PROJECT"]
    if "location" not in warehouse and os.getenv("QUERYSPEND_LOCATION"):
        warehouse["location"] = os.environ["QUERYSPEND_LOCATION"]
    try:
        return QuerySpendConfig.model_validate(data)
    except ValidationError as error:
        details = []
        for item in error.errors(
            include_url=False, include_context=False, include_input=False
        ):
            location = ".".join(str(part) for part in item["loc"])
            details.append(f"{location}: {item['msg']}" if location else str(item["msg"]))
        raise InputError("Invalid queryspend config: " + "; ".join(details)) from error


def resolve_frequency(
    config: QuerySpendConfig,
    unique_id: str,
    head_meta: dict[str, Any] | None,
    base_meta: dict[str, Any] | None,
) -> tuple[Decimal | None, str | None, bool]:
    """Resolve explicit frequency in canonical priority order."""

    if unique_id in config.frequencies.models:
        overridden = (
            _meta_frequency(head_meta) is not None or _meta_frequency(base_meta) is not None
        )
        return config.frequencies.models[unique_id], "config_model", overridden
    for side, meta in (("head_meta", head_meta), ("base_meta", base_meta)):
        candidate = _meta_frequency(meta)
        if candidate is not None:
            return candidate, side, False
    if config.frequencies.default_runs_per_month is not None:
        return config.frequencies.default_runs_per_month, "config_default", False
    return None, None, False


def _meta_frequency(meta: dict[str, Any] | None) -> Decimal | None:
    if not meta:
        return None
    queryspend_meta = meta.get("queryspend")
    if not isinstance(queryspend_meta, dict) or "runs_per_month" not in queryspend_meta:
        return None
    try:
        return _decimal_string(
            queryspend_meta["runs_per_month"],
            allow_zero=True,
            field_name="config.meta.queryspend.runs_per_month",
        )
    except ValueError as error:
        raise InputError(str(error)) from error
