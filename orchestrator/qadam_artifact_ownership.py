"""Machine-readable ownership and dependency audit for hot Qadam artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from orchestrator.qadam_operator_ready_common import (
    ROOT,
    atomic_write_text,
    authority_flags,
    now_iso,
    runtime_dir,
    write_json_atomic,
)
from orchestrator.qadam_operator_service import SERVICE_DEFINITIONS
from orchestrator.qadam_resource_locks import RESOURCE_ORDER

SCHEMA_VERSION = "qadam_artifact_ownership.v1"
REGISTRY_PATH = ROOT / "config" / "qadam_runtime_artifact_ownership.json"


def _registry() -> dict[str, Any]:
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("artifact_ownership_registry_invalid")
    return payload


def _dependency_cycles() -> list[list[str]]:
    graph = {
        definition.service_id: set(definition.dependencies) for definition in SERVICE_DEFINITIONS
    }
    cycles: list[list[str]] = []

    def visit(node: str, stack: list[str], visiting: set[str], visited: set[str]) -> None:
        if node in visiting:
            start = stack.index(node)
            cycles.append(stack[start:] + [node])
            return
        if node in visited:
            return
        visiting.add(node)
        stack.append(node)
        for dependency in sorted(graph.get(node, set())):
            visit(dependency, stack, visiting, visited)
        stack.pop()
        visiting.remove(node)
        visited.add(node)

    visited: set[str] = set()
    for service_id in sorted(graph):
        visit(service_id, [], set(), visited)
    return cycles


def build_artifact_ownership_audit(runtime: Path | None = None) -> dict[str, Any]:
    runtime = (runtime or runtime_dir()).resolve()
    registry = _registry()
    records = registry.get("artifacts") or []
    owners: dict[str, list[str]] = {}
    for record in records:
        owners.setdefault(str(record.get("artifact") or ""), []).append(
            str(record.get("producer") or "")
        )
    multi_writer = [
        {"artifact": artifact, "producers": sorted(set(producers))}
        for artifact, producers in owners.items()
        if len(set(producers)) != 1
    ]
    registry_by_artifact = {str(record.get("artifact") or ""): record for record in records}
    undeclared: list[dict[str, str]] = []
    invalid_invokers: list[dict[str, str]] = []
    uncovered_write_resources: list[dict[str, str]] = []
    registered_resources = {str(record.get("logical_resource") or "") for record in records}
    service_contracts = []
    for definition in SERVICE_DEFINITIONS:
        claims = definition.resource_claims()
        claims.validate()
        service_contracts.append(
            {
                "service_id": definition.service_id,
                "reads": list(claims.reads),
                "writes": list(claims.writes),
                "appends": list(claims.appends),
                "dependencies": list(definition.dependencies),
            }
        )
        for artifact in definition.generation_artifacts:
            record = registry_by_artifact.get(artifact)
            if record is None:
                undeclared.append({"service_id": definition.service_id, "artifact": artifact})
                continue
            allowed = set(record.get("authorized_invokers") or ())
            if definition.service_id not in allowed:
                invalid_invokers.append({"service_id": definition.service_id, "artifact": artifact})
        for resource in (*definition.write_resources, *definition.append_resources):
            if resource not in registered_resources:
                uncovered_write_resources.append(
                    {"service_id": definition.service_id, "resource": resource}
                )
    unknown_resources = sorted(
        {str(record.get("logical_resource") or "") for record in records} - set(RESOURCE_ORDER)
    )
    cycles = _dependency_cycles()
    blockers = []
    if multi_writer:
        blockers.append("artifact_multi_writer_violation")
    if undeclared:
        blockers.append("undeclared_generation_artifact")
    if invalid_invokers:
        blockers.append("unauthorized_artifact_invoker")
    if uncovered_write_resources:
        blockers.append("write_resource_without_registered_artifact")
    if unknown_resources:
        blockers.append("unknown_logical_resource")
    if cycles:
        blockers.append("service_dependency_cycle")
    generated_at = now_iso()
    audit = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_artifact_ownership_audit",
        "generated_at": generated_at,
        "status": "passed" if not blockers else "blocked",
        "registered_artifact_count": len(records),
        "registered_service_count": len(service_contracts),
        "autonomous_processes": registry.get("autonomous_processes") or [],
        "service_contracts": service_contracts,
        "undeclared_artifacts": undeclared,
        "invalid_invokers": invalid_invokers,
        "uncovered_write_resources": uncovered_write_resources,
        "unknown_resources": unknown_resources,
        "dependency_cycles": cycles,
        "multi_writer_violation_count": len(multi_writer),
        "blockers": blockers,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "authority": authority_flags(),
    }
    graph = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_artifact_dependency_graph",
        "generated_at": generated_at,
        "nodes": service_contracts,
        "edges": [
            {"from": dependency, "to": definition.service_id}
            for definition in SERVICE_DEFINITIONS
            for dependency in definition.dependencies
        ],
        "cycle_count": len(cycles),
        "authority": authority_flags(),
    }
    write_json_atomic(runtime / "qadam_artifact_ownership_audit.json", audit)
    write_json_atomic(runtime / "qadam_artifact_dependency_graph.json", graph)
    violations_path = runtime / "qadam_artifact_multi_writer_violations.jsonl"
    atomic_write_text(
        violations_path,
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in multi_writer),
    )
    return audit
