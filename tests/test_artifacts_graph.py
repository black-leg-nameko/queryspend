from __future__ import annotations

import json
from pathlib import Path

import pytest

from queryspend.dbt_artifacts import ManifestNormalizer, normalize_sql
from queryspend.exceptions import InputError
from queryspend.graph import diff_and_affected
from queryspend.models import AffectedReason, ChangeType
from tests.helpers import manifest, model_node


@pytest.mark.parametrize("version", [10, 11, 12])
def test_normalizes_supported_manifest_versions(tmp_path: Path, version: int) -> None:
    path = manifest(
        tmp_path / f"v{version}.json",
        version=version,
        nodes={"model.test.orders": model_node("model.test.orders")},
    )
    normalized = ManifestNormalizer().normalize(path)
    assert normalized.schema_version == version
    assert normalized.nodes["model.test.orders"].materialized == "table"


def test_sql_normalization_preserves_literals_and_ignores_outer_whitespace() -> None:
    assert normalize_sql(" select  *\nfrom t ") == "select * from t"
    assert normalize_sql("select 'a  b'") != normalize_sql("select 'a b'")


def test_semantic_diff_and_descendant_union(tmp_path: Path) -> None:
    base = manifest(
        tmp_path / "base.json",
        nodes={
            "model.test.parent": model_node("model.test.parent", sql="select 1"),
            "model.test.child": model_node(
                "model.test.child", dependencies=["model.test.parent"]
            ),
        },
    )
    head = manifest(
        tmp_path / "head.json",
        nodes={
            "model.test.parent": model_node(
                "model.test.parent", sql="select 2", checksum="changed"
            ),
            "model.test.child": model_node(
                "model.test.child", dependencies=["model.test.parent"]
            ),
        },
    )
    normalizer = ManifestNormalizer()
    affected = diff_and_affected(normalizer.normalize(base), normalizer.normalize(head))
    assert [item.unique_id for item in affected] == ["model.test.parent", "model.test.child"]
    assert affected[0].change_type is ChangeType.MODIFIED
    assert affected[1].affected_reason is AffectedReason.DOWNSTREAM


def test_add_delete_materialization_and_cycle(tmp_path: Path) -> None:
    base = manifest(
        tmp_path / "base.json",
        nodes={
            "model.test.deleted": model_node("model.test.deleted"),
            "model.test.transition": model_node("model.test.transition"),
        },
    )
    head = manifest(
        tmp_path / "head.json",
        nodes={
            "model.test.added": model_node("model.test.added"),
            "model.test.transition": model_node(
                "model.test.transition", materialized="view"
            ),
        },
    )
    normalizer = ManifestNormalizer()
    changes = {
        item.unique_id: item.change_type
        for item in diff_and_affected(normalizer.normalize(base), normalizer.normalize(head))
    }
    assert changes == {
        "model.test.added": ChangeType.ADDED,
        "model.test.deleted": ChangeType.DELETED,
        "model.test.transition": ChangeType.MATERIALIZATION_CHANGED,
    }
    cycle = manifest(
        tmp_path / "cycle.json",
        nodes={
            "model.test.a": model_node("model.test.a", dependencies=["model.test.b"]),
            "model.test.b": model_node("model.test.b", dependencies=["model.test.a"]),
        },
    )
    normalized = normalizer.normalize(cycle)
    with pytest.raises(InputError, match=r"cycle.*model\.test\.a"):
        diff_and_affected(normalized, normalized)


def test_rejects_unknown_version_adapter_missing_node_and_duplicates(tmp_path: Path) -> None:
    normalizer = ManifestNormalizer()
    with pytest.raises(InputError, match="unsupported_manifest_version"):
        normalizer.normalize(manifest(tmp_path / "v13.json", version=13))
    with pytest.raises(InputError, match="unsupported_adapter"):
        normalizer.normalize(manifest(tmp_path / "snowflake.json", adapter="snowflake"))
    broken = manifest(
        tmp_path / "missing.json",
        nodes={
            "model.test.a": model_node(
                "model.test.a", dependencies=["model.test.missing"]
            )
        },
    )
    with pytest.raises(InputError, match="missing graph node"):
        normalizer.normalize(broken)
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"metadata":{},"metadata":{},"nodes":{}}', encoding="utf-8")
    with pytest.raises(InputError, match="duplicate"):
        normalizer.normalize(duplicate)


def test_manifest_shape_and_size_limits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    normalizer = ManifestNormalizer()
    missing = tmp_path / "absent.json"
    with pytest.raises(InputError, match="Could not read"):
        normalizer.normalize(missing)
    invalid = tmp_path / "invalid.json"
    invalid.write_text("not json", encoding="utf-8")
    with pytest.raises(InputError, match="valid duplicate-free JSON"):
        normalizer.normalize(invalid)
    root_list = tmp_path / "list.json"
    root_list.write_text("[]", encoding="utf-8")
    with pytest.raises(InputError, match="root must be an object"):
        normalizer.normalize(root_list)
    monkeypatch.setattr("queryspend.dbt_artifacts.MAX_MANIFEST_BYTES", 1)
    with pytest.raises(InputError, match="exceeds"):
        normalizer.normalize(root_list)


def test_manifest_rejects_nonfinite_deep_and_oversized_identifiers(tmp_path: Path) -> None:
    nonfinite = tmp_path / "nonfinite.json"
    nonfinite.write_text(
        '{"metadata":{"dbt_schema_version":"v12"},"nodes":{},"extra":NaN}',
        encoding="utf-8",
    )
    with pytest.raises(InputError, match="duplicate-free JSON within bounds"):
        ManifestNormalizer().normalize(nonfinite)

    deeply_nested = tmp_path / "deep.json"
    deeply_nested.write_text("[" * 2000 + "0" + "]" * 2000, encoding="utf-8")
    with pytest.raises(InputError, match="nesting limit"):
        ManifestNormalizer().normalize(deeply_nested)

    oversized_id = "model.test." + "x" * 4096
    path = manifest(
        tmp_path / "oversized.json",
        nodes={oversized_id: model_node(oversized_id)},
    )
    with pytest.raises(InputError, match="exceeds"):
        ManifestNormalizer().normalize(path)


def test_deep_acyclic_graph_is_iterative_and_stable(tmp_path: Path) -> None:
    count = 2500
    base_nodes = {}
    head_nodes = {}
    for index in range(count):
        unique_id = f"model.test.node_{index:04d}"
        dependencies = [f"model.test.node_{index - 1:04d}"] if index else []
        base_nodes[unique_id] = model_node(unique_id, dependencies=dependencies)
        head_nodes[unique_id] = model_node(
            unique_id,
            dependencies=dependencies,
            sql="select 2" if index == 0 else "select 1",
            checksum="changed" if index == 0 else "checksum",
        )
    normalizer = ManifestNormalizer()
    base = normalizer.normalize(manifest(tmp_path / "deep-base.json", nodes=base_nodes))
    head = normalizer.normalize(manifest(tmp_path / "deep-head.json", nodes=head_nodes))
    affected = diff_and_affected(base, head)
    assert len(affected) == count
    assert affected[0].unique_id == "model.test.node_0000"
    assert affected[-1].unique_id == f"model.test.node_{count - 1:04d}"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ({"metadata": None}, "metadata"),
        ({"nodes": []}, "nodes"),
        ({"sources": []}, "sources"),
        ({"metadata": {"dbt_schema_version": 12}}, "unsupported_manifest_version"),
        ({"metadata": {"dbt_schema_version": "not-a-version"}}, "cannot parse"),
    ],
)
def test_manifest_global_shape_errors(
    tmp_path: Path, mutation: dict[str, object], message: str
) -> None:
    data: dict[str, object] = {
        "metadata": {
            "dbt_schema_version": "https://schemas.getdbt.com/dbt/manifest/v12.json",
            "adapter_type": "bigquery",
        },
        "nodes": {},
        "sources": {},
    }
    data.update(mutation)
    path = tmp_path / f"{message}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(InputError, match=message):
        ManifestNormalizer().normalize(path)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"config": "bad"}, "config.materialized"),
        ({"resource_type": None}, "resource_type"),
        ({"compiled_code": 12}, "compiled_code"),
        ({"package_name": None}, "package_name"),
        ({"config": {"materialized": 12}}, "materialized"),
        ({"config": {"materialized": "table", "meta": []}}, "config.meta"),
        ({"database": 12}, "database"),
        ({"depends_on": {"nodes": [12]}}, "dependencies"),
    ],
)
def test_manifest_node_shape_errors(
    tmp_path: Path, change: dict[str, object], message: str
) -> None:
    node = model_node("model.test.orders")
    node.update(change)
    path = manifest(
        tmp_path / f"{message.replace('.', '-')}.json",
        nodes={"model.test.orders": node},
    )
    with pytest.raises(InputError, match=message):
        ManifestNormalizer().normalize(path)


def test_parent_map_old_compiled_sql_and_disabled_node(tmp_path: Path) -> None:
    parent = model_node("model.test.parent")
    child = model_node("model.test.child")
    child.pop("compiled_code")
    child["compiled_sql"] = "select 2"
    child.pop("depends_on")
    disabled = model_node("model.test.disabled")
    disabled["config"]["enabled"] = False
    data = {
        "metadata": {
            "dbt_schema_version": "https://schemas.getdbt.com/dbt/manifest/v10.json",
            "adapter_type": "bigquery",
            "project_name": "test_project",
        },
        "nodes": {
            "model.test.parent": parent,
            "model.test.child": child,
            "model.test.disabled": disabled,
        },
        "sources": {},
        "parent_map": {"model.test.child": ["model.test.parent"]},
    }
    path = tmp_path / "old.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    normalized = ManifestNormalizer().normalize(path)
    assert normalized.nodes["model.test.child"].dependencies == ("model.test.parent",)
    assert normalized.nodes["model.test.child"].compiled_code == "select 2"
    assert "model.test.disabled" not in normalized.nodes
