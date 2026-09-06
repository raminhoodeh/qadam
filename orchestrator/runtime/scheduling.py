"""Pure scheduling decisions independent of worker, broker and presentation state."""

from datetime import datetime, timedelta
from typing import Any
from orchestrator.contracts.timestamps import _parse_timestamp
from orchestrator.qadam_operator_ready_common import now_iso
from orchestrator.runtime.services import ServiceDefinition


def _next_due_at(definition: ServiceDefinition, receipt: dict[str, Any] | None) -> str:
    completed = _parse_timestamp((receipt or {}).get("completed_at"))
    if completed is None:
        return now_iso()
    return (completed + timedelta(seconds=definition.cadence_seconds)).isoformat()

def _is_due(
    definition: ServiceDefinition,
    receipt: dict[str, Any] | None,
    *,
    timestamp: datetime,
) -> bool:
    if not receipt:
        return True
    due_at = _parse_timestamp(_next_due_at(definition, receipt))
    return due_at is None or due_at <= timestamp

def _dependency_advanced(
    definition: ServiceDefinition,
    successful: dict[str, dict[str, Any]],
    cycle_successes: set[str],
) -> bool:
    """Run a dependent service whenever an upstream result is newer."""

    if not definition.wake_on_dependency_advance:
        return False
    if any(dependency in cycle_successes for dependency in definition.dependencies):
        return True
    own_completed = _parse_timestamp(
        (successful.get(definition.service_id) or {}).get("completed_at")
    )
    if own_completed is None:
        return False
    for dependency in definition.dependencies:
        dependency_completed = _parse_timestamp(
            (successful.get(dependency) or {}).get("completed_at")
        )
        if dependency_completed is not None and dependency_completed > own_completed:
            return True
    return False

def _cycle_material_change_state(
    receipts: list[dict[str, Any]], service_id: str
) -> bool | None:
    for receipt in reversed(receipts):
        if receipt.get("service_id") != service_id:
            continue
        for result in reversed(receipt.get("command_results", [])):
            material = (result.get("work_result") or {}).get("material_change_detected")
            if isinstance(material, bool):
                return material
        return None
    return None

def _freshness_deadline_priority(
    definition: ServiceDefinition,
    successful: dict[str, dict[str, Any]],
    *,
    timestamp: datetime,
) -> int:
    """Elevate a service before its declared output freshness deadline expires."""

    if definition.latency_sensitive:
        return 0
    deadline = definition.freshness_deadline_seconds or max(
        definition.cadence_seconds * 3,
        900,
    )
    completed = _parse_timestamp(
        (successful.get(definition.service_id) or {}).get("completed_at")
    )
    if completed is None:
        return 1
    age_seconds = max(0.0, (timestamp - completed).total_seconds())
    if age_seconds >= deadline:
        return 0
    guard_seconds = min(5 * 60, max(60, deadline // 3))
    return 2 if age_seconds >= max(0, deadline - guard_seconds) else 3
