"""Auditable safe-checkpoint state for a clean paper-epoch cutover."""

from __future__ import annotations

from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    runtime_dir,
    unique_errors,
    validate_authority,
)

SCHEMA_VERSION = "qadam_clean_epoch_quiescence.v1"
ARTIFACT = "qadam_clean_epoch_quiescence.json"
PAUSE_RECEIPT_ARTIFACT = "qadam_clean_epoch_pause_receipt.json"


def build_clean_epoch_quiescence(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    service = read_json(runtime / "qadam_operator_service_checks.json")
    lease = read_json(runtime / "qadam_operator_service_lease.json")
    workers = read_json(runtime / "qadam_operator_workers.json")
    lifecycle = read_json(runtime / "qadam_paper_lifecycle_v3.json")
    lock = read_json(runtime / "qadam_long_backtest_lock.json")
    worker_rows = workers.get("workers") if isinstance(workers.get("workers"), list) else []
    active_workers = [
        row for row in worker_rows if isinstance(row, dict) and row.get("state") == "running"
    ]
    service_running = bool(
        service.get("service_running") is True
        or lease.get("status") == "active"
        or lease.get("single_instance_active") is True
    )
    unresolved_orders = int(
        lifecycle.get("ambiguous_order_count")
        or lifecycle.get("unresolved_order_count")
        or 0
    )
    blockers: list[str] = []
    if service_running:
        blockers.append("operator_service_not_paused")
    if active_workers:
        blockers.append("operator_workers_still_running")
    if unresolved_orders:
        blockers.append("ambiguous_or_unresolved_paper_orders")
    if not (
        lock.get("status") == "active"
        or lock.get("research_lock_active") is True
        or lock.get("paperops_watch_only_mode") is True
    ):
        blockers.append("research_lock_not_active")
    blockers = unique_errors(blockers)
    generated = now_iso()
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_clean_epoch_quiescence",
        "generated_at": generated,
        "status": "safe_checkpoint" if not blockers else "not_quiescent",
        "quiescent": not blockers,
        "operator_service_running": service_running,
        "active_worker_count": len(active_workers),
        "ambiguous_or_unresolved_order_count": unresolved_orders,
        "research_lock_active": "research_lock_not_active" not in blockers,
        "paperops_watch_only": True,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }


def validate_clean_epoch_quiescence(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("quiescent") is True:
        for field in (
            "operator_service_running",
            "active_worker_count",
            "ambiguous_or_unresolved_order_count",
        ):
            if payload.get(field) not in (False, 0):
                errors.append(f"quiescence_passed_with_active_state:{field}")
        if payload.get("research_lock_active") is not True:
            errors.append("quiescence_passed_without_research_lock")
    if int(payload.get("broker_write_count") or 0) != 0:
        errors.append("quiescence_broker_write_detected")
    if payload.get("live_capital_enabled") is not False:
        errors.append("quiescence_live_capital_enabled")
    errors.extend(validate_authority(payload.get("authority", {}), prefix="quiescence"))
    return unique_errors(errors)


def build_and_write_clean_epoch_quiescence(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    payload = build_clean_epoch_quiescence(settings)
    errors = validate_clean_epoch_quiescence(payload)
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_clean_epoch_pause_receipt",
        "generated_at": payload["generated_at"],
        "status": "paused_at_safe_checkpoint" if payload["quiescent"] else "pause_required",
        "pause_verified": payload["quiescent"],
        "service_was_stopped_by_checker": False,
        "automatic_service_stop_allowed": False,
        "blockers": payload["blockers"],
        "authority": authority_flags(),
    }
    store = AtomicArtifactStore(runtime_dir(settings))
    store.write_json(ARTIFACT, payload)
    store.write_json(PAUSE_RECEIPT_ARTIFACT, receipt)
    return payload, receipt, errors


__all__ = [
    "ARTIFACT",
    "PAUSE_RECEIPT_ARTIFACT",
    "build_and_write_clean_epoch_quiescence",
    "build_clean_epoch_quiescence",
    "validate_clean_epoch_quiescence",
]
