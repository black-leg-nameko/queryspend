"""Deterministic semantic diff and base/head downstream graph union."""

from __future__ import annotations

import heapq
from collections import deque
from dataclasses import dataclass

from queryspend.dbt_artifacts import NormalizedManifest, NormalizedNode
from queryspend.exceptions import InputError
from queryspend.models import AffectedReason, ChangeType


@dataclass(frozen=True)
class AffectedNode:
    unique_id: str
    base: NormalizedNode | None
    head: NormalizedNode | None
    change_type: ChangeType
    affected_reason: AffectedReason


def diff_and_affected(
    base: NormalizedManifest, head: NormalizedManifest
) -> list[AffectedNode]:
    """Return changed nodes and descendants from either graph in stable order."""

    _assert_acyclic(base)
    _assert_acyclic(head)
    all_ids = set(base.nodes) | set(head.nodes)
    changes: dict[str, ChangeType] = {}
    for unique_id in sorted(all_ids):
        before = base.nodes.get(unique_id)
        after = head.nodes.get(unique_id)
        if before is None:
            changes[unique_id] = ChangeType.ADDED
        elif after is None:
            changes[unique_id] = ChangeType.DELETED
        elif before.materialized != after.materialized:
            changes[unique_id] = ChangeType.MATERIALIZATION_CHANGED
        elif before.fingerprint != after.fingerprint:
            changes[unique_id] = ChangeType.MODIFIED
    if not changes:
        return []
    descendants = set(changes)
    for manifest in (base, head):
        reverse = _reverse_edges(manifest)
        queue = deque(sorted(changes))
        while queue:
            current = queue.popleft()
            for child in reverse.get(current, ()):
                if child not in descendants:
                    descendants.add(child)
                    queue.append(child)
    order = _topological_union_order(descendants, base, head)
    return [
        AffectedNode(
            unique_id=unique_id,
            base=base.nodes.get(unique_id),
            head=head.nodes.get(unique_id),
            change_type=changes.get(unique_id, ChangeType.UNCHANGED),
            affected_reason=(
                AffectedReason.CHANGED if unique_id in changes else AffectedReason.DOWNSTREAM
            ),
        )
        for unique_id in order
    ]


def _reverse_edges(manifest: NormalizedManifest) -> dict[str, tuple[str, ...]]:
    reverse_lists: dict[str, list[str]] = {}
    for node in manifest.nodes.values():
        for dependency in node.dependencies:
            if dependency in manifest.nodes:
                reverse_lists.setdefault(dependency, []).append(node.unique_id)
    return {key: tuple(sorted(value)) for key, value in reverse_lists.items()}


def _assert_acyclic(manifest: NormalizedManifest) -> None:
    indegree = {unique_id: 0 for unique_id in manifest.nodes}
    children: dict[str, list[str]] = {}
    for unique_id, node in manifest.nodes.items():
        for dependency in node.dependencies:
            if dependency in manifest.nodes:
                indegree[unique_id] += 1
                children.setdefault(dependency, []).append(unique_id)
    ready = [unique_id for unique_id, count in indegree.items() if count == 0]
    heapq.heapify(ready)
    visited = 0
    while ready:
        current = heapq.heappop(ready)
        visited += 1
        for child in sorted(children.get(current, ())):
            indegree[child] -= 1
            if indegree[child] == 0:
                heapq.heappush(ready, child)
    if visited != len(manifest.nodes):
        cyclic = min(unique_id for unique_id, count in indegree.items() if count > 0)
        raise InputError(f"Manifest graph cycle includes {cyclic}")


def _topological_union_order(
    affected: set[str], base: NormalizedManifest, head: NormalizedManifest
) -> list[str]:
    dependencies: dict[str, set[str]] = {item: set() for item in affected}
    for manifest in (base, head):
        for unique_id in affected:
            node = manifest.nodes.get(unique_id)
            if node is not None:
                dependencies[unique_id].update(
                    dependency for dependency in node.dependencies if dependency in affected
                )
    children: dict[str, list[str]] = {}
    indegree = {item: len(items) for item, items in dependencies.items()}
    for child, items in dependencies.items():
        for dependency in items:
            children.setdefault(dependency, []).append(child)
    ready = [item for item, count in indegree.items() if count == 0]
    heapq.heapify(ready)
    result: list[str] = []
    while ready:
        current = heapq.heappop(ready)
        result.append(current)
        for child in sorted(children.get(current, ())):
            indegree[child] -= 1
            if indegree[child] == 0:
                heapq.heappush(ready, child)
    if len(result) != len(affected):
        raise InputError("Manifest graph union contains a cycle")
    return result
