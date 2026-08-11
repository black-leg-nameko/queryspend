"""dbt manifest v10-v12 normalization and semantic fingerprints."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from queryspend.exceptions import InputError

MAX_MANIFEST_BYTES = 100 * 1024 * 1024
MAX_COMPILED_SQL_BYTES = 2 * 1024 * 1024
MAX_NODES = 100_000
MAX_IDENTIFIER_CHARS = 4096
MAX_JSON_DEPTH = 64
SUPPORTED_MANIFEST_VERSIONS = {10, 11, 12}
VERSION_PATTERN = re.compile(r"(?:manifest/)?v(\d+)(?:\.json)?/?$")


@dataclass(frozen=True)
class NormalizedNode:
    unique_id: str
    resource_type: str
    package_name: str
    name: str
    materialized: str
    meta: dict[str, Any]
    dependencies: tuple[str, ...]
    compiled_code: str | None
    sql_sha256: str | None
    database: str | None
    schema_name: str | None
    alias: str | None
    checksum: str
    fingerprint: str


@dataclass(frozen=True)
class NormalizedManifest:
    path: Path
    sha256: str
    schema_version: int
    adapter_type: str | None
    root_project: str | None
    nodes: dict[str, NormalizedNode]
    known_resource_ids: frozenset[str]


class ArtifactNormalizer(Protocol):
    def normalize(self, path: Path) -> NormalizedManifest: ...


class ManifestNormalizer:
    """Normalize supported dbt manifest shapes into the internal v1 model."""

    def normalize(self, path: Path) -> NormalizedManifest:
        try:
            resolved = path.resolve(strict=True)
            if not resolved.is_file():
                raise InputError(f"Manifest is not a regular file: {path}")
            size = resolved.stat().st_size
            if size > MAX_MANIFEST_BYTES:
                raise InputError(f"Manifest exceeds {MAX_MANIFEST_BYTES} bytes: {path}")
            raw = resolved.read_bytes()
        except (OSError, RuntimeError) as error:
            raise InputError(f"Could not read manifest {path}: {error}") from error
        try:
            data = json.loads(
                raw,
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_json_constant,
                parse_float=_finite_json_float,
            )
        except RecursionError as error:
            raise InputError(
                f"Manifest JSON exceeds nesting limit of {MAX_JSON_DEPTH}: {path}"
            ) from error
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as error:
            raise InputError(
                f"Manifest is not valid duplicate-free JSON within bounds: {path}"
            ) from error
        _assert_bounded_json_depth(data)
        if not isinstance(data, dict):
            raise InputError(f"Manifest root must be an object: {path}")
        metadata = data.get("metadata")
        if not isinstance(metadata, dict):
            raise InputError("Manifest metadata.dbt_schema_version is required")
        version = _manifest_version(metadata.get("dbt_schema_version"))
        adapter = metadata.get("adapter_type")
        if adapter is not None and adapter != "bigquery":
            raise InputError("unsupported_adapter: expected bigquery")
        raw_nodes = data.get("nodes")
        if not isinstance(raw_nodes, dict):
            raise InputError("Manifest nodes must be an object")
        sources = data.get("sources", {})
        if not isinstance(sources, dict):
            raise InputError("Manifest sources must be an object")
        if len(raw_nodes) + len(sources) > MAX_NODES:
            raise InputError(f"Manifest exceeds resource limit of {MAX_NODES}")
        for source_id in sources:
            _bounded_string(source_id, "Manifest source ID")
        known_ids = frozenset((*raw_nodes.keys(), *sources.keys()))
        parent_map = data.get("parent_map", {})
        if not isinstance(parent_map, dict):
            parent_map = {}
        nodes: dict[str, NormalizedNode] = {}
        for key, raw_node in raw_nodes.items():
            if not isinstance(key, str) or not isinstance(raw_node, dict):
                raise InputError("Manifest node IDs and objects must be valid")
            _bounded_string(key, "Manifest node ID")
            config = raw_node.get("config")
            if config is None:
                config = {}
            elif not isinstance(config, dict):
                raise InputError(f"Node {key} config.materialized must be in an object")
            if config.get("enabled", True) is False:
                continue
            resource_type = raw_node.get("resource_type")
            if not isinstance(resource_type, str):
                raise InputError(f"Node {key} has no resource_type")
            if resource_type != "model":
                continue
            dependencies = _dependencies(raw_node, parent_map.get(key))
            for dependency in dependencies:
                _bounded_string(dependency, f"Node {key} dependency")
            missing = [
                item
                for item in dependencies
                if (item.startswith("model.") or item.startswith("source."))
                and item not in known_ids
            ]
            if missing:
                raise InputError(f"Node {key} references missing graph node {missing[0]}")
            compiled = raw_node.get("compiled_code", raw_node.get("compiled_sql"))
            if compiled is not None and not isinstance(compiled, str):
                raise InputError(f"Node {key} compiled_code must be a string")
            if compiled is not None:
                try:
                    compiled_size = len(compiled.encode("utf-8"))
                except UnicodeEncodeError as error:
                    raise InputError(f"Node {key} compiled SQL is not valid UTF-8") from error
                if compiled_size > MAX_COMPILED_SQL_BYTES:
                    raise InputError(
                        f"Node {key} compiled SQL exceeds {MAX_COMPILED_SQL_BYTES} bytes"
                    )
            normalized_sql = normalize_sql(compiled) if compiled is not None else None
            sql_hash = _sha256_text(normalized_sql) if normalized_sql is not None else None
            checksum = _canonical_checksum(raw_node.get("checksum"))
            materialized = config.get("materialized", "view")
            if not isinstance(materialized, str):
                raise InputError(f"Node {key} config.materialized must be a string")
            package_name = raw_node.get("package_name")
            name = raw_node.get("name")
            if not isinstance(package_name, str) or not isinstance(name, str):
                raise InputError(f"Node {key} requires package_name and name")
            _bounded_string(package_name, f"Node {key} package_name")
            _bounded_string(name, f"Node {key} name")
            meta = config.get("meta", {})
            if not isinstance(meta, dict):
                raise InputError(f"Node {key} config.meta must be an object")
            database = _optional_string(raw_node.get("database"), key, "database")
            schema_name = _optional_string(raw_node.get("schema"), key, "schema")
            alias = _optional_string(raw_node.get("alias"), key, "alias")
            fingerprint_payload = {
                "compiled_code_sha256": sql_hash,
                "checksum": checksum,
                "materialized": materialized,
                "database": database,
                "schema": schema_name,
                "alias": alias,
                "dependencies": sorted(
                    item
                    for item in dependencies
                    if item.startswith("model.") or item.startswith("source.")
                ),
            }
            fingerprint = hashlib.sha256(
                json.dumps(
                    fingerprint_payload, sort_keys=True, separators=(",", ":")
                ).encode("utf-8")
            ).hexdigest()
            nodes[key] = NormalizedNode(
                unique_id=key,
                resource_type=resource_type,
                package_name=package_name,
                name=name,
                materialized=materialized,
                meta=meta,
                dependencies=dependencies,
                compiled_code=compiled,
                sql_sha256=sql_hash,
                database=database,
                schema_name=schema_name,
                alias=alias,
                checksum=checksum,
                fingerprint=fingerprint,
            )
        root_project = metadata.get("project_name")
        if root_project is not None and not isinstance(root_project, str):
            raise InputError("Manifest metadata.project_name must be a string")
        if root_project is not None:
            _bounded_string(root_project, "Manifest metadata.project_name")
        return NormalizedManifest(
            path=resolved,
            sha256=hashlib.sha256(raw).hexdigest(),
            schema_version=version,
            adapter_type=adapter if isinstance(adapter, str) else None,
            root_project=root_project,
            nodes=nodes,
            known_resource_ids=known_ids,
        )


def _manifest_version(value: object) -> int:
    if not isinstance(value, str):
        raise InputError("unsupported_manifest_version: metadata.dbt_schema_version is required")
    match = VERSION_PATTERN.search(value.rstrip("/"))
    if match is None:
        raise InputError(
            "unsupported_manifest_version: cannot parse metadata.dbt_schema_version"
        )
    version = int(match.group(1))
    if version not in SUPPORTED_MANIFEST_VERSIONS:
        raise InputError(
            f"unsupported_manifest_version: v{version}; supported versions are v10-v12"
        )
    return version


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key {key!r}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> float:
    raise ValueError(f"non-finite JSON constant is not supported: {value}")


def _finite_json_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError("non-finite JSON number is not supported")
    return parsed


def _assert_bounded_json_depth(value: object) -> None:
    stack: list[tuple[object, int]] = [(value, 1)]
    while stack:
        current, depth = stack.pop()
        if depth > MAX_JSON_DEPTH:
            raise InputError(f"Manifest JSON exceeds nesting limit of {MAX_JSON_DEPTH}")
        if isinstance(current, dict):
            stack.extend((item, depth + 1) for item in current.values())
        elif isinstance(current, list):
            stack.extend((item, depth + 1) for item in current)


def _dependencies(node: dict[str, Any], parent_entry: object) -> tuple[str, ...]:
    depends_on = node.get("depends_on")
    candidates: object = None
    if isinstance(depends_on, dict):
        candidates = depends_on.get("nodes")
    if candidates is None:
        candidates = parent_entry
    if candidates is None:
        return ()
    if not isinstance(candidates, list) or not all(isinstance(item, str) for item in candidates):
        raise InputError(f"Node {node.get('unique_id', '<unknown>')} dependencies must be strings")
    return tuple(sorted(set(candidates)))


def _canonical_checksum(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, RecursionError) as error:
        raise InputError("Node checksum must be bounded canonical JSON") from error


def _optional_string(value: object, unique_id: str, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise InputError(f"Node {unique_id} {field} must be a string or null")
    _bounded_string(value, f"Node {unique_id} {field}")
    return value


def _bounded_string(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise InputError(f"{field} must be a string")
    if len(value) > MAX_IDENTIFIER_CHARS:
        raise InputError(f"{field} exceeds {MAX_IDENTIFIER_CHARS} characters")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise InputError(f"{field} contains control characters")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise InputError(f"{field} is not valid UTF-8") from error
    return value


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_sql(sql: str) -> str:
    """Normalize whitespace outside quoted literals without exposing SQL."""

    output: list[str] = []
    quote: str | None = None
    pending_space = False
    index = 0
    while index < len(sql):
        char = sql[index]
        if quote is not None:
            output.append(char)
            if char == quote:
                if index + 1 < len(sql) and sql[index + 1] == quote:
                    output.append(sql[index + 1])
                    index += 1
                else:
                    quote = None
            elif char == "\\" and index + 1 < len(sql):
                output.append(sql[index + 1])
                index += 1
        elif char in {"'", '"', "`"}:
            if pending_space and output:
                output.append(" ")
            pending_space = False
            output.append(char)
            quote = char
        elif char.isspace():
            pending_space = True
        else:
            if pending_space and output:
                output.append(" ")
            pending_space = False
            output.append(char)
        index += 1
    return "".join(output).strip()
