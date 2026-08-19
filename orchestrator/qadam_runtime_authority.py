"""Executable one-writer and supersession registry for Qadam runtime truth."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any, Iterable

from orchestrator.qadam_operator_ready_common import now_iso

SCHEMA_VERSION = "qadam_runtime_authority_check.v1"
REPO_ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_REGISTRY = REPO_ROOT / "config" / "qadam_runtime_authority_registry.json"
SUPERSESSION_REGISTRY = REPO_ROOT / "config" / "qadam_supersession_registry.json"


def _read(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _service_commands() -> list[dict[str, str]]:
    from orchestrator.qadam_operator_service import SERVICE_DEFINITIONS

    rows: list[dict[str, str]] = []
    for service in SERVICE_DEFINITIONS:
        for command in service.command_sequence:
            rows.append(
                {
                    "service_id": service.service_id,
                    "command": " ".join(command),
                    "ownership": service.ownership,
                    "safety_mode": service.safety_mode,
                }
            )
    return rows


def _python_imports(paths: Iterable[Path]) -> list[dict[str, str]]:
    markers = {
        "qadam_router_v2_paperops_handoff": "router_v2_active_projection",
        "qsase_strategy_router": "qsase_decision_consumers",
        "qadam_qeg_akber": "qeg_direct_akber_router",
    }
    rows: list[dict[str, str]] = []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for marker, component in markers.items():
            if marker in text:
                rows.append(
                    {
                        "path": str(path.relative_to(REPO_ROOT)),
                        "marker": marker,
                        "component_id": component,
                    }
                )
    return rows


def build_runtime_authority_audit() -> dict[str, Any]:
    authority = _read(AUTHORITY_REGISTRY)
    supersession = _read(SUPERSESSION_REGISTRY)
    resources = authority.get("resources") if isinstance(authority.get("resources"), list) else []
    entries = supersession.get("entries") if isinstance(supersession.get("entries"), list) else []
    commands = _service_commands()
    errors: list[str] = []

    resource_ids = [str(row.get("resource_id") or "") for row in resources if isinstance(row, dict)]
    owners = [str(row.get("canonical_owner") or "") for row in resources if isinstance(row, dict)]
    duplicate_resources = sorted(
        resource_id for resource_id, count in Counter(resource_ids).items() if resource_id and count > 1
    )
    if not resources:
        errors.append("authority_registry_empty")
    if any(not value for value in resource_ids):
        errors.append("authority_resource_identity_missing")
    if any(not value for value in owners):
        errors.append("authority_owner_missing")
    if duplicate_resources:
        errors.extend(f"multiple_active_writers:{value}" for value in duplicate_resources)
    if authority.get("paper_only") is not True:
        errors.append("paper_only_boundary_missing")
    if authority.get("live_capital_enabled") is not False:
        errors.append("live_capital_authority_detected")

    forbidden = set(str(value) for value in authority.get("forbidden_owners", []) if str(value))
    active_forbidden = sorted(
        {row["ownership"] for row in commands if row["ownership"] in forbidden}
    )
    if active_forbidden:
        errors.extend(f"forbidden_owner_scheduled:{value}" for value in active_forbidden)

    retired_by_id = {
        str(row.get("component_id") or ""): row
        for row in entries
        if isinstance(row, dict)
    }
    router_v2_commands = [
        row for row in commands if "check_qadam_router_v2_paperops_handoff.py" in row["command"]
    ]
    if router_v2_commands:
        errors.append("router_v2_still_scheduled")
    for component_id, row in retired_by_id.items():
        if row.get("must_not_be_scheduled") is True and not row.get("superseded_by"):
            errors.append(f"retired_component_without_owner:{component_id}")

    source_paths = list((REPO_ROOT / "orchestrator").glob("*.py")) + list(
        (REPO_ROOT / "scripts").glob("*.py")
    )
    compatibility_imports = _python_imports(source_paths)
    active_imports = [
        row
        for row in compatibility_imports
        if row["path"] in {command["command"].split()[0] for command in commands}
    ]

    broker_owner_count = sum(
        1
        for row in resources
        if isinstance(row, dict)
        and row.get("resource_id") == "broker_write"
        and row.get("canonical_owner") == "canonical_paperops_wrapper_only"
    )
    if broker_owner_count != 1:
        errors.append("guarded_paper_broker_owner_count_invalid")

    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_runtime_authority_audit",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "authority_registry_path": str(AUTHORITY_REGISTRY.relative_to(REPO_ROOT)),
        "supersession_registry_path": str(SUPERSESSION_REGISTRY.relative_to(REPO_ROOT)),
        "resource_count": len(resources),
        "unique_resource_count": len(set(resource_ids)),
        "broker_write_owner_count": broker_owner_count,
        "scheduled_command_count": len(commands),
        "router_v2_scheduled_count": len(router_v2_commands),
        "compatibility_imports": compatibility_imports,
        "active_compatibility_imports": active_imports,
        "retired_component_count": sum(
            1 for row in entries if isinstance(row, dict) and row.get("status") == "retired"
        ),
        "validation_errors": errors,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
    }


__all__ = ["build_runtime_authority_audit"]
