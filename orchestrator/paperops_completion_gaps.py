"""Public-safe completion gap contract for guarded PaperOps.

This module consolidates the remaining non-blocking setup work into one
readable artifact. It does not grant source authority, execution authority, or
live-capital authority; it only says what is still missing and whether it blocks
guarded Alpaca Paper operation.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from orchestrator.bookmap_local_bridge import bookmap_local_bridge_status
from orchestrator.config import Settings
from orchestrator.paper_live_certification import paper_live_certification_public_status
from orchestrator.paperops_30_day_operations import paperops_30_day_operations_public_status
from orchestrator.paperops_active_paper_trading_automation import (
    paperops_active_paper_trading_automation_public_status,
)
from orchestrator.paperops_source_gap_visibility import (
    paperops_source_gap_visibility_public_status,
)
from orchestrator.quantum import qctrl_fire_opal_ibm_readiness, quantum_oracle_summary


PAPEROPS_COMPLETION_GAPS_SCHEMA_VERSION = 1
PAPEROPS_COMPLETION_GAPS_RUNTIME_ARTIFACT = "paperops_completion_gaps.json"
PAPEROPS_COMPLETION_GAPS_HISTORY = "paperops_completion_gaps_history.jsonl"
PAPEROPS_COMPLETION_GAPS_BOUNDARY = (
    "Completion-gap readiness is public-safe status only. It can report missing "
    "optional credentials, local-only adapters, quantum hardware proof status, "
    "and PaperOps monitoring state, but it cannot create signals, create trade "
    "candidates, approve risk, submit paper orders, call brokers, cannot call live "
    "endpoints, cannot expose secrets, cannot enable live capital, or grant proof credit."
)

ZERO_AUTHORITY_FIELDS = (
    "signal_authority",
    "trade_candidate_creation_allowed",
    "risk_approval_allowed",
    "execution_allowed",
    "paper_order_allowed",
    "broker_write_allowed",
    "live_endpoint_called",
    "secret_value_exposed",
    "raw_secret_key_exposed",
    "live_capital_enabled",
    "proof_credit_allowed",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _artifact_paths(settings: Settings | None = None) -> tuple[Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PAPEROPS_COMPLETION_GAPS_RUNTIME_ARTIFACT,
        runtime / PAPEROPS_COMPLETION_GAPS_HISTORY,
    )


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _quantum_method_label(quantum: dict[str, Any]) -> str:
    backend = str(quantum.get("latest_backend") or quantum.get("backend") or "").lower()
    mode = str(
        quantum.get("latest_local_simulation_mode") or quantum.get("mode") or ""
    ).lower()
    if any(token in f"{backend} {mode}" for token in ("classical", "fallback", "shadow", "deterministic")):
        return "Classical Fallback (Deterministic)"
    if _int(quantum.get("hardware_submitted_count")) > 0 and any(
        token in backend for token in ("ibm", "qctrl", "qiskit", "hardware")
    ):
        return "IBM / Q-CTRL Hardware"
    return "Classical Fallback (Deterministic)"


def _quantum_proof_item(
    quantum: dict[str, Any],
    fire_opal: dict[str, Any],
) -> dict[str, Any]:
    method = _quantum_method_label(quantum)
    hardware_confirmed = method == "IBM / Q-CTRL Hardware"
    status = (
        "hardware_execution_confirmed"
        if hardware_confirmed
        else "paper_quantum_review_wired_classical_shadow"
    )
    if not hardware_confirmed and fire_opal.get("status") in {
        "device_probe_submitted",
        "device_probe_recorded",
    }:
        status = "device_discovery_ready_not_hardware_execution"
    return {
        "gap_key": "quantum_hardware_execution_proof",
        "label": "Quantum hardware execution proof",
        "category": "quantum",
        "status": status,
        "configured": bool(fire_opal.get("ibm_quantum_token_configured"))
        and bool(fire_opal.get("ibm_quantum_instance_configured")),
        "paper_operation_blocking": False,
        "operator_required": not hardware_confirmed,
        "current_state": method,
        "latest_backend": quantum.get("latest_backend", "classical_fallback"),
        "latest_local_simulation_mode": quantum.get(
            "latest_local_simulation_mode",
            "not_run",
        ),
        "fire_opal_ibm_status": fire_opal.get("status", "not_exported"),
        "fire_opal_ibm_blocker": fire_opal.get("blocker", "not_exported"),
        "next_action": (
            "No action required for paper trading. To prove hardware execution, run the explicit Fire Opal / IBM device path and only label hardware after the actual oracle run reports a hardware backend."
            if not hardware_confirmed
            else "No action required."
        ),
        "public_safe": True,
    }


def _bookmap_item(bookmap: dict[str, Any]) -> dict[str, Any]:
    connected = bool(bookmap.get("connected"))
    configured = bool(bookmap.get("bridge_url_configured"))
    return {
        "gap_key": "bookmap_local_bridge_not_connected",
        "label": "Bookmap local order-flow bridge",
        "category": "local_adapter",
        "status": "connected" if connected else bookmap.get("status", "local_bridge_required"),
        "configured": configured,
        "paper_operation_blocking": False,
        "operator_required": not connected,
        "current_state": (
            "Connected to a local loopback bridge"
            if connected
            else (
                "Configured but live probe is disabled or pending"
                if configured
                else "Local bridge URL not configured"
            )
        ),
        "next_action": (
            "No action required."
            if connected
            else "Run a local Bookmap observation bridge on the Mac and set BOOKMAP_BRIDGE_URL to a localhost or 127.0.0.1 endpoint; enable live probing only when the bridge is running."
        ),
        "public_safe": True,
    }


def _source_gap_items(source_gaps: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for record in source_gaps.get("optional_gap_records", []) or []:
        if not isinstance(record, dict):
            continue
        if record.get("gap_present") is not True:
            continue
        items.append(
            {
                "gap_key": record.get("gap_key"),
                "label": record.get("source_name") or record.get("source_key"),
                "category": "optional_source_credential",
                "status": record.get("credential_status", "missing_optional"),
                "coverage_role": record.get("coverage_role"),
                "configured": False,
                "paper_operation_blocking": False,
                "operator_required": True,
                "current_state": "Optional credential missing",
                "next_action": record.get(
                    "next_action",
                    "Configure optional source credentials to expand context coverage.",
                ),
                "public_safe": True,
            }
        )
    return items


def _paperops_item(
    operations: dict[str, Any],
    certification: dict[str, Any],
    active_automation: dict[str, Any],
) -> dict[str, Any]:
    certified = bool(
        certification.get("paper_live_certified")
        or certification.get("paper_live_control_plane_certified")
    )
    cycle_ready = str(operations.get("cycle_status") or "").endswith("ready")
    active = bool(active_automation.get("enabled")) and str(
        active_automation.get("status") or ""
    ) in {
        "active_automation_ready_to_poll",
        "active_automation_enabled_idle",
        "active_automation_enabled_noop",
    }
    blocker_count = _int(certification.get("blocker_count")) + _int(
        operations.get("blocker_count")
    )
    paper_blocking = not certified or blocker_count > 0
    return {
        "gap_key": "paperops_monitoring",
        "label": "PaperOps unattended monitoring",
        "category": "paperops",
        "status": (
            "paper_operational_monitoring_ready"
            if certified and cycle_ready and active
            else "paper_operational_monitoring_needs_attention"
        ),
        "configured": certified and active,
        "paper_operation_blocking": paper_blocking,
        "operator_required": paper_blocking,
        "current_state": (
            f"{operations.get('status', 'unknown')} / {active_automation.get('status', 'unknown')}"
        ),
        "next_action": (
            "No action required; continue monitoring daily paper lifecycle, source freshness, and postmortems."
            if not paper_blocking
            else "Review PaperOps certification and operations artifacts before relying on unattended paper trading."
        ),
        "public_safe": True,
    }


def build_paperops_completion_gaps(
    settings: Settings | None = None,
    *,
    generated_at: str | None = None,
    source_gaps: dict[str, Any] | None = None,
    bookmap: dict[str, Any] | None = None,
    quantum: dict[str, Any] | None = None,
    fire_opal: dict[str, Any] | None = None,
    operations: dict[str, Any] | None = None,
    certification: dict[str, Any] | None = None,
    active_automation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    source_gaps = source_gaps or paperops_source_gap_visibility_public_status(settings)
    bookmap = bookmap or bookmap_local_bridge_status(settings)
    quantum = quantum or quantum_oracle_summary(settings)
    fire_opal = fire_opal or qctrl_fire_opal_ibm_readiness(settings)
    operations = operations or paperops_30_day_operations_public_status(settings)
    certification = certification or paper_live_certification_public_status(settings)
    active_automation = active_automation or paperops_active_paper_trading_automation_public_status(settings)
    items = [
        *_source_gap_items(source_gaps),
        _bookmap_item(bookmap),
        _quantum_proof_item(quantum, fire_opal),
        _paperops_item(operations, certification, active_automation),
    ]
    user_required = [item for item in items if item.get("operator_required")]
    paper_blocking = [item for item in items if item.get("paper_operation_blocking")]
    artifact = {
        "schema_version": PAPEROPS_COMPLETION_GAPS_SCHEMA_VERSION,
        "artifact_type": "paperops_completion_gaps",
        "artifact_id": "paperops:completion-gaps:latest",
        "generated_at": generated_at or _now(),
        "status": (
            "paper_operational_with_non_blocking_completion_gaps"
            if user_required and not paper_blocking
            else (
                "paper_operational_all_completion_items_done"
                if not user_required and not paper_blocking
                else "paper_operation_attention_required"
            )
        ),
        "public_safe": True,
        "paper_operation_blocking_gap_count": len(paper_blocking),
        "operator_required_item_count": len(user_required),
        "optional_source_gap_count": len(
            [item for item in items if item.get("category") == "optional_source_credential"]
        ),
        "bookmap_connected": bool(bookmap.get("connected")),
        "quantum_hardware_execution_confirmed": (
            _quantum_method_label(quantum) == "IBM / Q-CTRL Hardware"
        ),
        "paperops_monitoring_ready": not bool(_paperops_item(operations, certification, active_automation).get("paper_operation_blocking")),
        "items": items,
        "paper_blocking_items": paper_blocking,
        "operator_required_items": user_required,
        "next_required_action": (
            "Paper trading can continue. Remaining items improve coverage or proof quality but do not block guarded Alpaca Paper operation."
            if user_required and not paper_blocking
            else (
                "No remaining completion actions are required."
                if not user_required and not paper_blocking
                else "Resolve paper-operation blocking items before relying on unattended paper trading."
            )
        ),
        "boundary": PAPEROPS_COMPLETION_GAPS_BOUNDARY,
    }
    for field in ZERO_AUTHORITY_FIELDS:
        artifact[field] = False
    artifact["validation_errors"] = validate_paperops_completion_gaps(artifact)
    artifact["validation_error_count"] = len(artifact["validation_errors"])
    if artifact["validation_errors"]:
        artifact["status"] = "invalid"
    return artifact


def validate_paperops_completion_gaps(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "artifact_id",
        "artifact_type",
        "boundary",
        "generated_at",
        "items",
        "next_required_action",
        "operator_required_item_count",
        "paper_blocking_items",
        "paper_operation_blocking_gap_count",
        "public_safe",
        "schema_version",
        "status",
    }
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("paperops_completion_gaps_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PAPEROPS_COMPLETION_GAPS_SCHEMA_VERSION:
        errors.append("paperops_completion_gaps_schema_mismatch")
    if artifact.get("artifact_type") != "paperops_completion_gaps":
        errors.append("paperops_completion_gaps_type_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("paperops_completion_gaps_not_public_safe")
    if artifact.get("status") not in {
        "paper_operational_with_non_blocking_completion_gaps",
        "paper_operational_all_completion_items_done",
        "paper_operation_attention_required",
        "invalid",
    }:
        errors.append("paperops_completion_gaps_status_invalid")
    for field in ZERO_AUTHORITY_FIELDS:
        if artifact.get(field) is not False:
            errors.append(f"paperops_completion_gaps_forbidden:{field}")
    items = artifact.get("items", [])
    if not isinstance(items, list):
        errors.append("paperops_completion_gaps_items_not_list")
        items = []
    paper_blocking = [item for item in items if isinstance(item, dict) and item.get("paper_operation_blocking")]
    user_required = [item for item in items if isinstance(item, dict) and item.get("operator_required")]
    if _int(artifact.get("paper_operation_blocking_gap_count")) != len(paper_blocking):
        errors.append("paperops_completion_gaps_paper_blocking_count_mismatch")
    if _int(artifact.get("operator_required_item_count")) != len(user_required):
        errors.append("paperops_completion_gaps_operator_required_count_mismatch")
    for item in items:
        if not isinstance(item, dict):
            errors.append("paperops_completion_gaps_item_invalid")
            continue
        for key in ("gap_key", "label", "category", "status", "paper_operation_blocking", "operator_required", "next_action", "public_safe"):
            if key not in item:
                errors.append(f"paperops_completion_gaps_item_missing:{key}")
        if item.get("public_safe") is not True:
            errors.append("paperops_completion_gaps_item_not_public_safe")
        if item.get("category") == "optional_source_credential" and item.get("paper_operation_blocking") is not False:
            errors.append("paperops_completion_gaps_optional_source_blocks_paper")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "public-safe status only",
        "cannot create signals",
        "cannot call live endpoints",
        "cannot expose secrets",
        "cannot enable live capital",
    ):
        if phrase not in boundary:
            errors.append("paperops_completion_gaps_boundary_weak")
            break
    return sorted(set(errors))


def write_paperops_completion_gaps(
    artifact: dict[str, Any],
    settings: Settings | None = None,
) -> tuple[Path, Path, dict[str, Any]]:
    output_path, history_path = _artifact_paths(settings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = deepcopy(artifact)
    written["validation_errors"] = validate_paperops_completion_gaps(written)
    written["validation_error_count"] = len(written["validation_errors"])
    if written["validation_errors"]:
        written["status"] = "invalid"
    output_path.write_text(
        json.dumps(written, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    history_record = {
        "schema_version": PAPEROPS_COMPLETION_GAPS_SCHEMA_VERSION,
        "artifact_id": written.get("artifact_id"),
        "status": written.get("status"),
        "recorded_at": _now(),
        "operator_required_item_count": written.get("operator_required_item_count"),
        "paper_operation_blocking_gap_count": written.get("paper_operation_blocking_gap_count"),
        "optional_source_gap_count": written.get("optional_source_gap_count"),
        "bookmap_connected": written.get("bookmap_connected"),
        "quantum_hardware_execution_confirmed": written.get("quantum_hardware_execution_confirmed"),
        "paperops_monitoring_ready": written.get("paperops_monitoring_ready"),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, written


def paperops_completion_gaps_public_status(
    settings: Settings | None = None,
    *,
    generated_at: str | None = None,
    source_gaps: dict[str, Any] | None = None,
    bookmap: dict[str, Any] | None = None,
    quantum: dict[str, Any] | None = None,
    fire_opal: dict[str, Any] | None = None,
    operations: dict[str, Any] | None = None,
    certification: dict[str, Any] | None = None,
    active_automation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    artifact = build_paperops_completion_gaps(
        settings,
        generated_at=generated_at,
        source_gaps=source_gaps,
        bookmap=bookmap,
        quantum=quantum,
        fire_opal=fire_opal,
        operations=operations,
        certification=certification,
        active_automation=active_automation,
    )
    keys = (
        "schema_version",
        "artifact_type",
        "artifact_id",
        "status",
        "generated_at",
        "public_safe",
        "paper_operation_blocking_gap_count",
        "operator_required_item_count",
        "optional_source_gap_count",
        "bookmap_connected",
        "quantum_hardware_execution_confirmed",
        "paperops_monitoring_ready",
        "items",
        "paper_blocking_items",
        "operator_required_items",
        "next_required_action",
        "boundary",
        "validation_error_count",
        *ZERO_AUTHORITY_FIELDS,
    )
    return {key: deepcopy(artifact.get(key)) for key in keys}
