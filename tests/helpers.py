from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def manifest(
    path: Path,
    *,
    version: int = 12,
    nodes: dict[str, dict[str, Any]] | None = None,
    sources: dict[str, dict[str, Any]] | None = None,
    adapter: str = "bigquery",
    project: str = "test_project",
) -> Path:
    data = {
        "metadata": {
            "dbt_schema_version": f"https://schemas.getdbt.com/dbt/manifest/v{version}.json",
            "adapter_type": adapter,
            "project_name": project,
        },
        "nodes": nodes or {},
        "sources": sources or {},
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def model_node(
    unique_id: str,
    *,
    sql: str | None = "select 1",
    materialized: str = "table",
    dependencies: list[str] | None = None,
    checksum: str = "same",
    package: str = "test_project",
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    name = unique_id.rsplit(".", 1)[-1]
    node: dict[str, Any] = {
        "unique_id": unique_id,
        "resource_type": "model",
        "package_name": package,
        "name": name,
        "config": {
            "enabled": True,
            "materialized": materialized,
            "meta": meta or {},
        },
        "depends_on": {"nodes": dependencies or []},
        "database": "project",
        "schema": "analytics",
        "alias": name,
        "checksum": {"name": "sha256", "checksum": checksum},
    }
    if sql is not None:
        node["compiled_code"] = sql
    return node

