"""Export the four canonical v1 JSON schemas from strict Pydantic models."""

from __future__ import annotations

import json
from pathlib import Path

from queryspend.config import QuerySpendConfig
from queryspend.models import QuerySpendReport
from queryspend.validation import Observation, ValidationReport

ROOT = Path(__file__).resolve().parents[1]
DECIMAL_PATTERN = r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$"


def main() -> None:
    schemas = {
        "report": QuerySpendReport.model_json_schema(by_alias=True),
        "config": QuerySpendConfig.model_json_schema(),
        "observation": Observation.model_json_schema(),
        "validation": ValidationReport.model_json_schema(by_alias=True),
    }
    _enforce_decimal_string_contracts(schemas)
    for name, schema in schemas.items():
        path = ROOT / "schemas" / name / "v1.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


def _enforce_decimal_string_contracts(schemas: dict[str, dict[str, object]]) -> None:
    decimal_string = {"type": "string", "pattern": DECIMAL_PATTERN}
    nullable_decimal = {"anyOf": [decimal_string, {"type": "null"}]}
    config_defs = schemas["config"]["$defs"]
    assert isinstance(config_defs, dict)
    warehouse = config_defs["WarehouseConfig"]
    frequencies = config_defs["FrequenciesConfig"]
    policy = config_defs["PolicyConfig"]
    for definition in (warehouse, frequencies, policy):
        assert isinstance(definition, dict)
    warehouse["properties"]["price_per_tib_usd"] = {
        **nullable_decimal,
        "default": None,
        "title": "Price Per Tib Usd",
    }
    frequencies["properties"]["default_runs_per_month"] = {
        **nullable_decimal,
        "default": None,
        "title": "Default Runs Per Month",
    }
    frequencies["properties"]["models"]["additionalProperties"] = decimal_string
    policy["properties"]["max_monthly_delta_usd"] = {
        **nullable_decimal,
        "default": None,
        "title": "Max Monthly Delta Usd",
    }
    observation_properties = schemas["observation"]["properties"]
    assert isinstance(observation_properties, dict)
    for name in (
        "policy_threshold_usd",
        "actual_monthly_delta_usd",
        "actual_monthly_bytes_delta",
        "actual_runs_per_month",
    ):
        existing = observation_properties[name]
        assert isinstance(existing, dict)
        observation_properties[name] = {**decimal_string, "title": existing.get("title", name)}


if __name__ == "__main__":
    main()
