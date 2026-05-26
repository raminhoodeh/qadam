"""Q5-8 paper-submit enablement gate.

This module adds the explicit approval and prerequisite gate for the first
guarded Alpaca paper-submit path. It does not perform broker POST calls. In the
current runtime state, no separate paper-submit approval exists and Q5-7 has no
request previews, so the gate records remain blocked.
"""

from __future__ import annotations

import json
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.paper_account import paper_account_shadow_context
from orchestrator.phase5_alpaca_paper_dry_run import (
    ALPACA_PAPER_DRY_RUN_RUNTIME_ARTIFACT,
    build_phase5_alpaca_paper_dry_run,
    validate_phase5_alpaca_paper_dry_run_bundle,
)
from orchestrator.phase5_artifacts import (
    PHASE5_ARTIFACT_SCHEMA_VERSION,
    PHASE5_AUTHORITY_FIELDS,
    phase5_authority_defaults,
    phase5_authority_ledger,
    phase5_provenance,
    phase5_source_posture,
    validate_phase5_artifact,
)
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT


PHASE5_PAPER_SUBMIT_ENABLEMENT_SCHEMA_VERSION = 1
PAPER_SUBMIT_ENABLEMENT_RUNTIME_ARTIFACT = "phase5_paper_submit_enablement_gate.json"
PAPER_SUBMIT_ENABLEMENT_HISTORY = "phase5_paper_submit_enablement_gate_history.jsonl"
PAPER_SUBMIT_ENABLEMENT_EVENT_LOG = "phase5_paper_submit_enablement_events.jsonl"
PAPER_SUBMIT_ENABLEMENT_EVENT_TYPE = "phase5_paper_submit_enablement_written"
PAPER_SUBMIT_ENABLEMENT_COMPONENT = "phase5_paper_submit_enablement_gate"
PAPER_SUBMIT_APPROVAL_RUNTIME_ARTIFACT = "phase5_paper_submit_approval.json"
PAPER_SUBMIT_APPROVAL_EVENT_LOG = "phase5_paper_submit_approval_events.jsonl"
PAPER_SUBMIT_APPROVAL_EVENT_TYPE = "phase5_paper_submit_approval_recorded"
PAPER_SUBMIT_APPROVAL_COMPONENT = "phase5_paper_submit_approval"
GUARDED_PAPER_SUBMIT_RECEIPT_RUNTIME_ARTIFACT = "phase5_guarded_paper_submit_receipt.json"
GUARDED_PAPER_SUBMIT_RECEIPT_HISTORY = "phase5_guarded_paper_submit_receipt_history.jsonl"
GUARDED_PAPER_SUBMIT_RECEIPT_EVENT_LOG = "phase5_guarded_paper_submit_receipt_events.jsonl"
GUARDED_PAPER_SUBMIT_RECEIPT_EVENT_TYPE = "phase5_guarded_paper_submit_receipt_recorded"
GUARDED_PAPER_SUBMIT_RECEIPT_COMPONENT = "phase5_guarded_paper_submit_receipt"
GUARDED_PAPER_SUBMIT_TARGET_STRATEGY = "crude_oil_energy_security_disruption"

PAPER_SUBMIT_ENABLEMENT_SOURCE_REFS: tuple[str, ...] = (
    "data/runtime/phase5_alpaca_paper_dry_run.json",
    "data/runtime/phase5_paper_order_staging_gate.json",
    "data/runtime/phase5_execution_adapter_status.json",
    "data/runtime/phase5_kill_switch_ledger.json",
    "data/runtime/paper_account_snapshots.jsonl",
    "data/runtime/phase5_paper_submit_approval.json",
)

PAPER_SUBMIT_ENABLEMENT_ALLOWED_AUTHORITY_FIELDS: tuple[str, ...] = (
    "execution_adapter_write_authority",
    "paper_execution_allowed",
    "paper_order_allowed",
    "paper_order_submission_allowed",
    "broker_write_allowed",
)

PAPER_SUBMIT_ENABLEMENT_REQUIRED_CHECKS: tuple[str, ...] = (
    "q5_7_dry_run_bundle_valid",
    "source_dry_run_record_present",
    "source_dry_run_receipt_ready",
    "source_request_preview_ready",
    "paper_submit_approval_present",
    "paper_account_mode_confirmed",
    "live_endpoint_blocked",
    "kill_switch_clear",
    "duplicate_order_guard_clear",
    "event_log_prewrite_complete",
    "pre_trade_snapshot_captured",
    "idempotency_key_allocated_for_submit",
    "submit_path_singleton",
    "submit_path_timeout_configured",
    "submit_path_retry_policy_configured",
    "submit_path_failure_recording_configured",
    "live_capital_disabled",
    "prediction_market_write_disabled",
    "broker_post_not_called_before_submit",
    "paper_order_not_submitted_before_submit",
)

PAPER_SUBMIT_ENABLEMENT_BOUNDARY_FIELDS: tuple[str, ...] = (
    "risk_approval_allowed",
    "trade_candidate_created",
    "execution_policy_handoff_allowed",
    "execution_allowed",
    "execution_intent_created",
    "paper_order_staging_allowed",
    "paper_order_submitted",
    "broker_post_called",
    "alpaca_post_called",
    "broker_submit_receipt_created",
    "prediction_market_write_allowed",
    "telegram_live_notifications_allowed",
    "position_created",
    "position_monitor_write_authority",
    "live_capital_enabled",
    "live_endpoint_allowed",
    "crypto_perps_write_allowed",
    "paid_preference_tools_allowed",
    "source_quorum_bypass_allowed",
)

PAPER_SUBMIT_ENABLEMENT_COUNT_FIELDS: tuple[str, ...] = (
    "execution_adapter_write_authority_count",
    "paper_execution_allowed_count",
    "paper_order_allowed_count",
    "paper_order_submission_allowed_count",
    "paper_order_submitted_count",
    "broker_write_allowed_count",
    "broker_submit_receipt_created_count",
    "broker_post_called_count",
    "alpaca_post_called_count",
    "prediction_market_write_allowed_count",
    "telegram_live_notifications_allowed_count",
    "position_created_count",
    "live_capital_enabled_count",
    "live_endpoint_allowed_count",
    "crypto_perps_write_allowed_count",
    "secret_value_exposed_count",
    "raw_payload_exposed_count",
    "local_path_exposed_count",
    "authorization_header_exposed_count",
    "base_url_exposed_count",
)

PAPER_SUBMIT_PATH_KEY = "alpaca_paper_post_order"
PAPER_SUBMIT_ENABLEMENT_BOUNDARY = (
    "Q5-8 defines a single guarded Alpaca paper POST path only after a separate "
    "paper-submit approval and all Q5-0 through Q5-7 prerequisites are present. "
    "This gate cannot submit without that approval, cannot use live endpoints, "
    "cannot enable live capital, cannot write prediction-market venues, cannot "
    "expose secrets, and does not perform broker POST calls during validation."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_key(value: str) -> str:
    allowed = []
    for char in value.lower():
        if char.isalnum() or char in {"_", "-"}:
            allowed.append(char)
        else:
            allowed.append("_")
    return "".join(allowed).strip("_") or "unknown"


def _authority_ledger(*, submit_path_available: bool) -> dict[str, Any]:
    ledger = phase5_authority_ledger()
    ledger["stage"] = "Q5-8"
    ledger["boundary"] = (
        "Q5-8 can grant only the named paper-submit path authority fields, and "
        "only when explicit paper-submit approval plus all prerequisites pass. "
        "Live capital, live endpoints, prediction-market writes, positions, "
        "notifications, and actual broker POST calls stay separately blocked."
    )
    if submit_path_available:
        for field in PAPER_SUBMIT_ENABLEMENT_ALLOWED_AUTHORITY_FIELDS:
            ledger[field] = True
        ledger["explicit_authority_grant_count"] = len(
            PAPER_SUBMIT_ENABLEMENT_ALLOWED_AUTHORITY_FIELDS
        )
    return ledger


def _check(name: str, passed: bool, *, detail: Any = None) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def paper_submit_enablement_paths(settings: Settings | None = None) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PAPER_SUBMIT_ENABLEMENT_RUNTIME_ARTIFACT,
        runtime / PAPER_SUBMIT_ENABLEMENT_HISTORY,
        runtime / PAPER_SUBMIT_ENABLEMENT_EVENT_LOG,
    )


def paper_submit_approval_path(settings: Settings | None = None) -> Path:
    return _runtime_dir(settings) / PAPER_SUBMIT_APPROVAL_RUNTIME_ARTIFACT


def paper_submit_approval_event_log_path(settings: Settings | None = None) -> Path:
    return _runtime_dir(settings) / PAPER_SUBMIT_APPROVAL_EVENT_LOG


def guarded_paper_submit_receipt_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / GUARDED_PAPER_SUBMIT_RECEIPT_RUNTIME_ARTIFACT,
        runtime / GUARDED_PAPER_SUBMIT_RECEIPT_HISTORY,
        runtime / GUARDED_PAPER_SUBMIT_RECEIPT_EVENT_LOG,
    )


def paper_submit_approval_status(settings: Settings | None = None) -> dict[str, Any]:
    path = paper_submit_approval_path(settings)
    approval = _read_json(path)
    if not approval:
        return {
            "schema_version": PHASE5_PAPER_SUBMIT_ENABLEMENT_SCHEMA_VERSION,
            "approval_state": "missing",
            "approval_scope": "alpaca_paper_submit",
            "approval_present": False,
            "approval_logged": False,
            "explicit_paper_submit_approval": False,
            "public_safe": True,
            "approval_artifact_present": False,
            "approval_artifact_path_exposed": False,
            "approver_label": None,
            "approved_at": None,
            "boundary": (
                "No separate paper-submit approval artifact exists. User "
                "permission to implement Q5-8 is not paper-submit approval."
            ),
        }
    approval_state = str(approval.get("approval_state") or "missing")
    approval_scope = str(approval.get("approval_scope") or "missing")
    validation_errors = validate_phase5_paper_submit_approval(approval)
    explicit = (
        approval_state == "approved"
        and approval_scope == "alpaca_paper_submit"
        and approval.get("explicit_paper_submit_approval") is True
        and approval.get("paper_account_mode_confirmed") is True
        and approval.get("live_endpoint_allowed") is False
        and approval.get("live_capital_enabled") is False
        and approval.get("public_safe") is True
        and not validation_errors
    )
    return {
        "schema_version": int(
            approval.get("schema_version", PHASE5_PAPER_SUBMIT_ENABLEMENT_SCHEMA_VERSION)
            or PHASE5_PAPER_SUBMIT_ENABLEMENT_SCHEMA_VERSION
        ),
        "approval_state": approval_state,
        "approval_scope": approval_scope,
        "approval_present": explicit,
        "approval_logged": approval.get("approval_logged") is True,
        "explicit_paper_submit_approval": approval.get("explicit_paper_submit_approval") is True,
        "public_safe": approval.get("public_safe") is True,
        "approval_artifact_present": True,
        "approval_artifact_path_exposed": False,
        "approver_label": str(approval.get("approver_label") or "not_disclosed"),
        "approved_at": approval.get("approved_at"),
        "paper_account_mode_confirmed": approval.get("paper_account_mode_confirmed") is True,
        "live_endpoint_allowed": approval.get("live_endpoint_allowed") is True,
        "live_capital_enabled": approval.get("live_capital_enabled") is True,
        "validation_error_count": len(validation_errors),
        "boundary": (
            "Paper-submit approval is scoped only to Alpaca paper submit and "
            "cannot authorize live endpoints, live capital, or any non-Alpaca "
            "write path."
        ),
    }


def build_phase5_paper_submit_approval(
    *,
    approver_label: str = "fund_manager_ramin",
    approval_instruction: str | None = None,
    approval_source: str = "codex_thread_q5_14_exit_unblock",
    settings: Settings | None = None,
) -> dict[str, Any]:
    _ = settings
    generated_at = _now()
    artifact = {
        "schema_version": PHASE5_PAPER_SUBMIT_ENABLEMENT_SCHEMA_VERSION,
        "artifact_type": "phase5_paper_submit_approval",
        "artifact_id": "phase5:q5-14:paper-submit-approval",
        "phase": "Q5",
        "stage": "Q5-14",
        "status": "approved",
        "generated_at": generated_at,
        "approved_at": generated_at,
        "public_safe": True,
        "approval_state": "approved",
        "approval_scope": "alpaca_paper_submit",
        "approval_present": True,
        "approval_logged": False,
        "explicit_paper_submit_approval": True,
        "approver_label": approver_label,
        "approval_source": approval_source,
        "approval_instruction": approval_instruction,
        "paper_account_mode_confirmed": True,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
        "broker_post_called": False,
        "alpaca_post_called": False,
        "paper_order_submitted": False,
        "broker_write_allowed": False,
        "paper_order_submission_allowed_without_prerequisites": False,
        "prediction_market_write_allowed": False,
        "crypto_perps_write_allowed": False,
        "telegram_live_notifications_allowed": False,
        "phase7_proof_credit_allowed": False,
        "secret_value_exposed": False,
        "raw_payload_exposed": False,
        "local_path_exposed": False,
        "authorization_header_exposed": False,
        "broker_order_identifier_exposed": False,
        "event_log_required": True,
        "event_log_correlation_id": None,
        "event_log_path": None,
        "event_log_created_at": None,
        "boundary": (
            "This approval is scoped only to the guarded Alpaca paper-submit "
            "gate. It does not submit an order, cannot bypass Q5-3/Q5-6/Q5-7 "
            "prerequisites, cannot authorize live endpoints or live capital, "
            "and cannot grant Phase 7 proof credit."
        ),
    }
    artifact["validation_errors"] = validate_phase5_paper_submit_approval(artifact)
    return artifact


def validate_phase5_paper_submit_approval(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version",
        "artifact_type",
        "artifact_id",
        "phase",
        "stage",
        "status",
        "generated_at",
        "approved_at",
        "public_safe",
        "approval_state",
        "approval_scope",
        "approval_present",
        "approval_logged",
        "explicit_paper_submit_approval",
        "paper_account_mode_confirmed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "boundary",
    }
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("approval_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PHASE5_PAPER_SUBMIT_ENABLEMENT_SCHEMA_VERSION:
        errors.append("approval_schema_version_mismatch")
    if artifact.get("artifact_type") != "phase5_paper_submit_approval":
        errors.append("approval_artifact_type_mismatch")
    if artifact.get("phase") != "Q5" or artifact.get("stage") != "Q5-14":
        errors.append("approval_phase_stage_mismatch")
    if artifact.get("status") != "approved":
        errors.append("approval_status_not_approved")
    if artifact.get("public_safe") is not True:
        errors.append("approval_not_public_safe")
    if artifact.get("approval_state") != "approved":
        errors.append("approval_state_not_approved")
    if artifact.get("approval_scope") != "alpaca_paper_submit":
        errors.append("approval_scope_not_alpaca_paper_submit")
    if artifact.get("approval_present") is not True:
        errors.append("approval_present_not_true")
    if artifact.get("approval_logged") is not True:
        errors.append("approval_not_logged")
    if artifact.get("explicit_paper_submit_approval") is not True:
        errors.append("explicit_paper_submit_approval_missing")
    if artifact.get("paper_account_mode_confirmed") is not True:
        errors.append("paper_account_mode_not_confirmed")
    for field in (
        "live_endpoint_allowed",
        "live_capital_enabled",
        "broker_post_called",
        "alpaca_post_called",
        "paper_order_submitted",
        "broker_write_allowed",
        "paper_order_submission_allowed_without_prerequisites",
        "prediction_market_write_allowed",
        "crypto_perps_write_allowed",
        "telegram_live_notifications_allowed",
        "phase7_proof_credit_allowed",
        "secret_value_exposed",
        "raw_payload_exposed",
        "local_path_exposed",
        "authorization_header_exposed",
        "broker_order_identifier_exposed",
    ):
        if artifact.get(field) is not False:
            errors.append(f"approval_unsafe_field_enabled:{field}")
    if not str(artifact.get("approver_label") or "").strip():
        errors.append("approver_label_missing")
    if not str(artifact.get("approval_instruction") or "").strip():
        errors.append("approval_instruction_missing")
    if artifact.get("event_log_required") is not True:
        errors.append("approval_event_log_not_required")
    if artifact.get("approval_logged") is True:
        if not str(artifact.get("event_log_correlation_id") or "").strip():
            errors.append("approval_event_log_correlation_missing")
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("approval_event_log_path_missing")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "guarded Alpaca paper-submit",
        "does not submit an order",
        "cannot bypass Q5-3/Q5-6/Q5-7",
        "cannot authorize live endpoints or live capital",
        "cannot grant Phase 7 proof credit",
    ):
        if phrase not in boundary:
            errors.append("approval_boundary_weak")
            break
    return sorted(set(errors))


def attach_phase5_paper_submit_approval_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(event_log_path or paper_submit_approval_event_log_path(settings))
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PAPER_SUBMIT_APPROVAL_EVENT_TYPE,
        PAPER_SUBMIT_APPROVAL_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "approval_state": output.get("approval_state"),
            "approval_scope": output.get("approval_scope"),
            "approver_label": output.get("approver_label"),
            "approval_source": output.get("approval_source"),
            "approval_instruction": output.get("approval_instruction"),
            "paper_account_mode_confirmed": output.get("paper_account_mode_confirmed"),
            "live_endpoint_allowed": output.get("live_endpoint_allowed"),
            "live_capital_enabled": output.get("live_capital_enabled"),
            "broker_post_called": output.get("broker_post_called"),
            "paper_order_submitted": output.get("paper_order_submitted"),
            "boundary": output.get("boundary"),
        },
    )
    output["approval_logged"] = True
    output["event_log_correlation_id"] = entry.correlation_id
    output["event_log_path"] = str(log.path)
    output["event_log_created_at"] = entry.created_at
    output["validation_errors"] = validate_phase5_paper_submit_approval(output)
    return output, entry


def write_phase5_paper_submit_approval(
    artifact: dict[str, Any],
    path: str | Path | None = None,
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, dict[str, Any]]:
    output = deepcopy(artifact)
    if record_event:
        output, _ = attach_phase5_paper_submit_approval_event_log(
            output,
            event_log_path=event_log_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase5_paper_submit_approval(output)
    output_path = Path(path or paper_submit_approval_path(settings))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path, output


def _runtime_paper_submit_gate(settings: Settings | None = None) -> dict[str, Any]:
    runtime_path = _runtime_dir(settings) / PAPER_SUBMIT_ENABLEMENT_RUNTIME_ARTIFACT
    return _read_json(runtime_path) or build_phase5_paper_submit_enablement_gate(settings=settings)


def _target_submit_record(
    bundle: dict[str, Any],
    *,
    strategy_family_key: str = GUARDED_PAPER_SUBMIT_TARGET_STRATEGY,
) -> dict[str, Any]:
    for record in bundle.get("records", []):
        if (
            isinstance(record, dict)
            and record.get("strategy_family_key") == strategy_family_key
            and record.get("submit_path_available") is True
        ):
            return record
    return {}


def _request_body_preview(record: dict[str, Any]) -> dict[str, Any]:
    preview = record.get("submit_request_preview", {})
    if not isinstance(preview, dict):
        return {}
    body = preview.get("request_body_preview", {})
    return dict(body) if isinstance(body, dict) else {}


def build_phase5_guarded_paper_submit_receipt(
    *,
    settings: Settings | None = None,
    strategy_family_key: str = GUARDED_PAPER_SUBMIT_TARGET_STRATEGY,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    submit_gate = _runtime_paper_submit_gate(settings)
    submit_gate_errors = validate_phase5_paper_submit_enablement_bundle(submit_gate)
    target = _target_submit_record(submit_gate, strategy_family_key=strategy_family_key)
    request_body = _request_body_preview(target)
    idempotency_key = str(target.get("idempotency_key") or "").strip()
    safe_strategy = _safe_key(strategy_family_key)
    gate_ready = (
        bool(target)
        and not submit_gate_errors
        and target.get("paper_submit_gate_state") == "ready_for_guarded_paper_submit"
        and target.get("submit_path_available") is True
        and target.get("paper_submit_approval_present") is True
        and target.get("idempotency_key_allocated_for_submit") is True
        and target.get("broker_post_called") is False
        and target.get("alpaca_post_called") is False
        and target.get("live_endpoint_allowed") is False
        and target.get("live_capital_enabled") is False
        and bool(idempotency_key)
    )
    not_yet_recorded = (
        target.get("paper_order_submitted") is False
        and target.get("broker_submit_receipt_created") is False
    )
    already_recorded_locally = (
        target.get("paper_order_submitted") is True
        and target.get("broker_submit_receipt_created") is True
        and target.get("receipt_state") == "paper_submit_receipt_recorded"
        and bool(str(target.get("submitted_order_ref") or "").strip())
        and bool(str(target.get("broker_receipt_ref") or "").strip())
    )
    submitted_ready = gate_ready and (not_yet_recorded or already_recorded_locally)
    submitted_order_ref = f"q5e5-paper-order-{safe_strategy}"
    broker_receipt_ref = f"q5e5-local-broker-receipt-{safe_strategy}"
    artifact = {
        "schema_version": PHASE5_PAPER_SUBMIT_ENABLEMENT_SCHEMA_VERSION,
        "artifact_type": "phase5_guarded_paper_submit_receipt",
        "artifact_id": f"phase5:q5e-5:guarded-paper-submit-receipt:{safe_strategy}",
        "phase": "Q5",
        "stage": "Q5E-5",
        "status": "submitted_paper_order" if submitted_ready else "blocked",
        "generated_at": generated_at,
        "public_safe": True,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "source_q5_8_artifact_id": target.get("artifact_id"),
        "source_q5_8_gate_state": target.get("paper_submit_gate_state", "missing"),
        "source_q5_8_submit_path_available": target.get("submit_path_available") is True,
        "source_q5_8_validation_error_count": len(submit_gate_errors),
        "strategy_family_key": strategy_family_key,
        "selected_venue": "alpaca_paper",
        "broker_adapter": "alpaca",
        "path_key": PAPER_SUBMIT_PATH_KEY,
        "idempotency_key": idempotency_key,
        "submitted_order_ref": submitted_order_ref if submitted_ready else None,
        "broker_receipt_ref": broker_receipt_ref if submitted_ready else None,
        "broker_receipt_state": (
            "local_guarded_receipt_recorded" if submitted_ready else "blocked_not_submitted"
        ),
        "paper_order_state": (
            "submitted_paper_order_recorded" if submitted_ready else "not_submitted"
        ),
        "order_status_for_mirror": "new" if submitted_ready else "none",
        "instrument": request_body.get("instrument") or "crude_oil",
        "symbol": request_body.get("symbol"),
        "side": request_body.get("side") or "buy",
        "quantity": float(request_body.get("qty", 0.0) or 0.0),
        "notional_gbp": float(request_body.get("notional_gbp", 0.0) or 0.0),
        "order_type": request_body.get("type") or "market",
        "time_in_force": request_body.get("time_in_force") or "day",
        "submitted_at": generated_at if submitted_ready else None,
        "paper_order_submitted": submitted_ready,
        "paper_order_submitted_count": 1 if submitted_ready else 0,
        "broker_submit_receipt_created": submitted_ready,
        "broker_submit_receipt_created_count": 1 if submitted_ready else 0,
        "broker_post_called": False,
        "broker_post_called_count": 0,
        "alpaca_post_called": False,
        "alpaca_post_called_count": 0,
        "external_broker_post_performed": False,
        "broker_write_allowed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
        "prediction_market_write_allowed": False,
        "phase7_proof_credit_allowed": False,
        "secret_value_exposed": False,
        "raw_payload_exposed": False,
        "local_path_exposed": False,
        "authorization_header_exposed": False,
        "base_url_exposed": False,
        "broker_order_identifier_exposed": False,
        "blocked_reasons": []
        if submitted_ready
        else [
            reason
            for reason, failed in (
                ("q5_8_submit_gate_not_ready", not target),
                ("q5_8_validation_errors", bool(submit_gate_errors)),
                ("submit_path_unavailable", target.get("submit_path_available") is not True),
                ("submit_idempotency_missing", not idempotency_key),
            )
            if failed
        ],
        "boundary": (
            "Q5E-5 records a local guarded submitted-paper-order and broker "
            "receipt state from the approved Q5-8 path. It does not perform an "
            "Alpaca POST, cannot expose broker identifiers, cannot use live "
            "endpoints, cannot enable live capital, and cannot count toward "
            "Phase 7 proof."
        ),
    }
    artifact["blocked_reason_count"] = len(artifact["blocked_reasons"])
    artifact["validation_errors"] = validate_phase5_guarded_paper_submit_receipt(artifact)
    artifact["status"] = "submitted_paper_order" if not artifact["validation_errors"] and submitted_ready else "blocked"
    return artifact


def validate_phase5_guarded_paper_submit_receipt(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version",
        "artifact_type",
        "artifact_id",
        "phase",
        "stage",
        "status",
        "generated_at",
        "public_safe",
        "event_log_required",
        "event_log_written",
        "strategy_family_key",
        "selected_venue",
        "path_key",
        "idempotency_key",
        "paper_order_submitted",
        "broker_submit_receipt_created",
        "broker_post_called",
        "alpaca_post_called",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "phase7_proof_credit_allowed",
        "blocked_reasons",
        "boundary",
    }
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("guarded_submit_receipt_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PHASE5_PAPER_SUBMIT_ENABLEMENT_SCHEMA_VERSION:
        errors.append("guarded_submit_receipt_schema_version_mismatch")
    if artifact.get("artifact_type") != "phase5_guarded_paper_submit_receipt":
        errors.append("guarded_submit_receipt_artifact_type_mismatch")
    if artifact.get("phase") != "Q5" or artifact.get("stage") != "Q5E-5":
        errors.append("guarded_submit_receipt_phase_stage_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("guarded_submit_receipt_not_public_safe")
    if artifact.get("selected_venue") != "alpaca_paper":
        errors.append("guarded_submit_receipt_venue_not_alpaca_paper")
    if artifact.get("path_key") != PAPER_SUBMIT_PATH_KEY:
        errors.append("guarded_submit_receipt_path_key_invalid")
    if not str(artifact.get("idempotency_key") or "").startswith("q5-7-dryrun-"):
        errors.append("guarded_submit_receipt_idempotency_not_q5_7_scoped")
    if artifact.get("paper_order_submitted") is True:
        if artifact.get("status") != "submitted_paper_order":
            errors.append("guarded_submit_receipt_status_not_submitted")
        if artifact.get("broker_submit_receipt_created") is not True:
            errors.append("guarded_submit_receipt_missing_receipt")
        if artifact.get("paper_order_submitted_count") != 1:
            errors.append("guarded_submit_receipt_submitted_count_mismatch")
        if artifact.get("broker_submit_receipt_created_count") != 1:
            errors.append("guarded_submit_receipt_receipt_count_mismatch")
        if not str(artifact.get("submitted_order_ref") or "").strip():
            errors.append("guarded_submit_receipt_order_ref_missing")
        if not str(artifact.get("broker_receipt_ref") or "").strip():
            errors.append("guarded_submit_receipt_ref_missing")
        if artifact.get("order_status_for_mirror") != "new":
            errors.append("guarded_submit_receipt_mirror_status_invalid")
    else:
        if artifact.get("paper_order_submitted_count") != 0:
            errors.append("guarded_submit_receipt_blocked_submitted_count_nonzero")
        if artifact.get("broker_submit_receipt_created_count") != 0:
            errors.append("guarded_submit_receipt_blocked_receipt_count_nonzero")
    for field in (
        "broker_post_called",
        "alpaca_post_called",
        "external_broker_post_performed",
        "broker_write_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "prediction_market_write_allowed",
        "phase7_proof_credit_allowed",
        "secret_value_exposed",
        "raw_payload_exposed",
        "local_path_exposed",
        "authorization_header_exposed",
        "base_url_exposed",
        "broker_order_identifier_exposed",
    ):
        if artifact.get(field) is not False:
            errors.append(f"guarded_submit_receipt_unsafe_field_enabled:{field}")
    if artifact.get("blocked_reason_count") != len(artifact.get("blocked_reasons", [])):
        errors.append("guarded_submit_receipt_blocked_reason_count_mismatch")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "does not perform an Alpaca POST",
        "cannot enable live capital",
        "cannot count toward Phase 7 proof",
    ):
        if phrase not in boundary:
            errors.append("guarded_submit_receipt_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_correlation_id") or "").strip():
            errors.append("guarded_submit_receipt_event_correlation_missing")
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("guarded_submit_receipt_event_path_missing")
    return sorted(set(errors))


def attach_phase5_guarded_paper_submit_receipt_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    _, _, default_event_path = guarded_paper_submit_receipt_paths(settings)
    log_path = Path(event_log_path or default_event_path)
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        GUARDED_PAPER_SUBMIT_RECEIPT_EVENT_TYPE,
        GUARDED_PAPER_SUBMIT_RECEIPT_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "strategy_family_key": output.get("strategy_family_key"),
            "status": output.get("status"),
            "paper_order_submitted": output.get("paper_order_submitted"),
            "broker_submit_receipt_created": output.get("broker_submit_receipt_created"),
            "broker_post_called": output.get("broker_post_called"),
            "alpaca_post_called": output.get("alpaca_post_called"),
            "live_capital_enabled": output.get("live_capital_enabled"),
            "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
            "boundary": output.get("boundary"),
        },
    )
    output["event_log_written"] = True
    output["event_log_path"] = str(log.path)
    output["event_log_correlation_id"] = entry.correlation_id
    output["event_log_created_at"] = entry.created_at
    output["validation_errors"] = validate_phase5_guarded_paper_submit_receipt(output)
    output["status"] = (
        "submitted_paper_order"
        if output.get("paper_order_submitted") is True and not output["validation_errors"]
        else "blocked"
    )
    return output, entry


def write_phase5_guarded_paper_submit_receipt(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = guarded_paper_submit_receipt_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase5_guarded_paper_submit_receipt_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase5_guarded_paper_submit_receipt(output)
        output["status"] = (
            "submitted_paper_order"
            if output.get("paper_order_submitted") is True and not output["validation_errors"]
            else "blocked"
        )
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE5_PAPER_SUBMIT_ENABLEMENT_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "paper_order_submitted": output.get("paper_order_submitted"),
        "broker_submit_receipt_created": output.get("broker_submit_receipt_created"),
        "broker_post_called": output.get("broker_post_called"),
        "alpaca_post_called": output.get("alpaca_post_called"),
        "live_capital_enabled": output.get("live_capital_enabled"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output


def _guarded_paper_submit_receipt(settings: Settings | None = None) -> dict[str, Any] | None:
    path, _, _ = guarded_paper_submit_receipt_paths(settings)
    artifact = _read_json(path)
    if not artifact:
        return None
    if validate_phase5_guarded_paper_submit_receipt(artifact):
        return None
    return artifact


def _dry_run_bundle(settings: Settings | None = None) -> dict[str, Any]:
    runtime_path = _runtime_dir(settings) / ALPACA_PAPER_DRY_RUN_RUNTIME_ARTIFACT
    return _read_json(runtime_path) or build_phase5_alpaca_paper_dry_run(settings=settings)


def _submit_path_metadata(*, submit_path_available: bool) -> dict[str, Any]:
    return {
        "path_key": PAPER_SUBMIT_PATH_KEY,
        "adapter": "alpaca",
        "selected_venue": "alpaca_paper",
        "account_mode_required": "paper",
        "paper_only": True,
        "available": submit_path_available,
        "http_method": "POST",
        "broker_path_template": "/v2/orders",
        "base_url_exposed": False,
        "authorization_header_included": False,
        "post_call_performed": False,
        "timeout_seconds": 12.0,
        "retry_policy": {
            "max_attempts": 2,
            "retry_requires_same_idempotency_key": True,
            "retry_on": ["timeout", "http_429", "http_5xx"],
            "non_retryable": ["http_4xx_except_429"],
        },
        "failure_recording": {
            "event_log_failure_required": True,
            "record_timeout": True,
            "record_http_error": True,
            "record_rejected_order": True,
            "raw_broker_payload_stored": False,
            "redaction": "public_safe",
        },
        "boundary": (
            "The only Q5-8 write path is an Alpaca paper /v2/orders POST. It is "
            "unavailable until explicit paper-submit approval and all prerequisite "
            "checks pass, and validation never performs the POST."
        ),
    }


def _event_log_prewrite(source_record: dict[str, Any], *, ready: bool) -> dict[str, Any]:
    return {
        "schema_version": PHASE5_PAPER_SUBMIT_ENABLEMENT_SCHEMA_VERSION,
        "prewrite_complete": ready,
        "prewrite_event_type": "phase5_paper_submit_attempt_prewrite",
        "prewrite_component": PAPER_SUBMIT_ENABLEMENT_COMPONENT,
        "source_dry_run_artifact_id": source_record.get("artifact_id"),
        "event_log_required": True,
        "event_log_written_before_submit": ready,
        "raw_payload_exposed": False,
        "boundary": (
            "A broker submit attempt must be prewritten before any future POST. "
            "Current Q5-8 validation only records the gate state."
        ),
    }


def _pre_trade_snapshot(source_record: dict[str, Any], *, captured: bool) -> dict[str, Any]:
    source_snapshot = source_record.get("pre_trade_snapshot_schema", {})
    if not isinstance(source_snapshot, dict):
        source_snapshot = {}
    return {
        "schema_version": PHASE5_PAPER_SUBMIT_ENABLEMENT_SCHEMA_VERSION,
        "captured": captured,
        "source_schema_status": source_snapshot.get("status", "missing"),
        "snapshot_ref": "q5_8_probe_snapshot" if captured else "not_captured",
        "account_scope": source_snapshot.get("account_scope", "paper"),
        "mode": source_snapshot.get("mode", "paper"),
        "connection_status": source_snapshot.get("connection_status", "unknown"),
        "current_balance_gbp": float(source_snapshot.get("current_balance_gbp", 0.0) or 0.0),
        "open_position_count": int(source_snapshot.get("open_position_count", 0) or 0),
        "open_order_count": int(source_snapshot.get("open_order_count", 0) or 0),
        "write_authority": False,
        "live_capital_enabled": False,
        "raw_payload_exposed": False,
        "boundary": (
            "Pre-trade snapshot must be captured before a future submit. It carries "
            "paper account state only and no broker write authority."
        ),
    }


def _submit_request_preview(source_record: dict[str, Any]) -> dict[str, Any]:
    preview = deepcopy(source_record.get("request_preview", {}))
    if not isinstance(preview, dict):
        preview = {}
    preview["post_call_allowed"] = False
    preview["authorization_header_included"] = False
    preview["base_url_exposed"] = False
    preview["raw_payload_exposed"] = False
    preview["http_method_preview"] = str(preview.get("http_method_preview") or "POST_DISABLED_PREVIEW_ONLY")
    return preview


def _broker_submit_result(submit_execution: dict[str, Any] | None = None) -> dict[str, Any]:
    if submit_execution and submit_execution.get("paper_order_submitted") is True:
        return {
            "schema_version": PHASE5_PAPER_SUBMIT_ENABLEMENT_SCHEMA_VERSION,
            "status": "submitted_paper_order_recorded",
            "broker_receipt_state": submit_execution.get(
                "broker_receipt_state",
                "local_guarded_receipt_recorded",
            ),
            "submitted_order_ref": submit_execution.get("submitted_order_ref"),
            "broker_receipt_ref": submit_execution.get("broker_receipt_ref"),
            "broker_post_called": False,
            "alpaca_post_called": False,
            "external_broker_post_performed": False,
            "paper_order_submitted": True,
            "broker_submit_receipt_created": True,
            "broker_order_id_exposed": False,
            "raw_broker_payload_stored": False,
            "event_log_failure_recorded": False,
            "event_log_correlation_id": submit_execution.get("event_log_correlation_id"),
            "boundary": (
                "Q5E-5 records a local guarded paper-submit receipt and submitted "
                "paper-order state for the lifecycle drill. It does not perform "
                "an Alpaca POST, expose broker identifiers, or enable live capital."
            ),
        }
    return {
        "schema_version": PHASE5_PAPER_SUBMIT_ENABLEMENT_SCHEMA_VERSION,
        "status": "not_submitted",
        "broker_post_called": False,
        "alpaca_post_called": False,
        "external_broker_post_performed": False,
        "paper_order_submitted": False,
        "broker_submit_receipt_created": False,
        "broker_order_id_exposed": False,
        "raw_broker_payload_stored": False,
        "event_log_failure_recorded": False,
        "boundary": (
            "No broker submit result exists until a separate future submit call "
            "passes approval and prerequisite gates."
        ),
    }


def _source_check_passed(source_record: dict[str, Any], check_name: str) -> bool:
    for check in source_record.get("checks", []):
        if isinstance(check, dict) and check.get("name") == check_name:
            return check.get("passed") is True
    return False


def _source_ready_for_submit_path(
    source_record: dict[str, Any],
    *,
    dry_run_errors: list[str],
    approval: dict[str, Any],
    account_context: dict[str, Any],
    duplicate_guard: dict[str, Any],
) -> bool:
    request_preview = source_record.get("request_preview", {})
    if not isinstance(request_preview, dict):
        request_preview = {}
    simulated_receipt = source_record.get("simulated_submit_receipt", {})
    if not isinstance(simulated_receipt, dict):
        simulated_receipt = {}
    endpoint_classification = str(source_record.get("endpoint_classification") or "missing")
    return all(
        (
            not dry_run_errors,
            source_record.get("request_preview_allowed") is True,
            source_record.get("dry_run_receipt_created") is True,
            source_record.get("receipt_state") == "dry_run_receipt_preview_ready",
            request_preview.get("post_call_allowed") is False,
            request_preview.get("authorization_header_included") is False,
            request_preview.get("base_url_exposed") is False,
            simulated_receipt.get("receipt_created") is True,
            simulated_receipt.get("broker_post_called") is False,
            simulated_receipt.get("paper_order_submitted") is False,
            approval.get("approval_present") is True,
            approval.get("approval_logged") is True,
            approval.get("explicit_paper_submit_approval") is True,
            account_context.get("mode") == "paper",
            source_record.get("paper_mode_confirmed") is True,
            endpoint_classification not in {"live_endpoint", "live_or_unknown_endpoint_blocked"},
            source_record.get("live_endpoint_allowed") is False,
            source_record.get("live_capital_enabled") is False,
            source_record.get("prediction_market_write_allowed") is False,
            source_record.get("broker_post_called") is False,
            source_record.get("paper_order_submitted") is False,
            source_record.get("kill_switch_clear") is True
            or _source_check_passed(source_record, "kill_switch_clear"),
            duplicate_guard.get("collision_checked") is True,
            duplicate_guard.get("collision_detected") is False,
            duplicate_guard.get("duplicate_detected") is False,
        )
    )


def _checks(
    source_record: dict[str, Any],
    *,
    dry_run_errors: list[str],
    approval: dict[str, Any],
    account_context: dict[str, Any],
    duplicate_guard: dict[str, Any],
    event_log_prewrite: dict[str, Any],
    pre_trade_snapshot: dict[str, Any],
    submit_path: dict[str, Any],
    idempotency_key_allocated_for_submit: bool,
) -> list[dict[str, Any]]:
    request_preview = source_record.get("request_preview", {})
    if not isinstance(request_preview, dict):
        request_preview = {}
    simulated_receipt = source_record.get("simulated_submit_receipt", {})
    if not isinstance(simulated_receipt, dict):
        simulated_receipt = {}
    retry_policy = submit_path.get("retry_policy", {})
    failure_recording = submit_path.get("failure_recording", {})
    if not isinstance(retry_policy, dict):
        retry_policy = {}
    if not isinstance(failure_recording, dict):
        failure_recording = {}
    endpoint_classification = str(source_record.get("endpoint_classification") or "missing")
    return [
        _check("q5_7_dry_run_bundle_valid", not dry_run_errors, detail=dry_run_errors),
        _check("source_dry_run_record_present", bool(source_record.get("artifact_id"))),
        _check(
            "source_dry_run_receipt_ready",
            source_record.get("dry_run_receipt_created") is True
            and simulated_receipt.get("receipt_created") is True
            and simulated_receipt.get("broker_post_called") is False,
        ),
        _check(
            "source_request_preview_ready",
            source_record.get("request_preview_allowed") is True
            and request_preview.get("post_call_allowed") is False
            and request_preview.get("authorization_header_included") is False
            and request_preview.get("base_url_exposed") is False,
        ),
        _check(
            "paper_submit_approval_present",
            approval.get("approval_present") is True
            and approval.get("approval_logged") is True
            and approval.get("explicit_paper_submit_approval") is True,
        ),
        _check(
            "paper_account_mode_confirmed",
            account_context.get("mode") == "paper"
            and source_record.get("paper_mode_confirmed") is True,
        ),
        _check(
            "live_endpoint_blocked",
            endpoint_classification != "live_endpoint"
            and endpoint_classification != "live_or_unknown_endpoint_blocked"
            and source_record.get("live_endpoint_allowed") is False,
        ),
        _check(
            "kill_switch_clear",
            source_record.get("kill_switch_clear") is True
            or _source_check_passed(source_record, "kill_switch_clear"),
        ),
        _check(
            "duplicate_order_guard_clear",
            duplicate_guard.get("collision_checked") is True
            and duplicate_guard.get("collision_detected") is False
            and duplicate_guard.get("duplicate_detected") is False,
        ),
        _check("event_log_prewrite_complete", event_log_prewrite.get("prewrite_complete") is True),
        _check("pre_trade_snapshot_captured", pre_trade_snapshot.get("captured") is True),
        _check("idempotency_key_allocated_for_submit", idempotency_key_allocated_for_submit),
        _check(
            "submit_path_singleton",
            submit_path.get("path_key") == PAPER_SUBMIT_PATH_KEY
            and submit_path.get("available") is True,
        ),
        _check(
            "submit_path_timeout_configured",
            float(submit_path.get("timeout_seconds", 0.0) or 0.0) > 0,
        ),
        _check(
            "submit_path_retry_policy_configured",
            retry_policy.get("max_attempts") == 2
            and retry_policy.get("retry_requires_same_idempotency_key") is True
            and "timeout" in retry_policy.get("retry_on", []),
        ),
        _check(
            "submit_path_failure_recording_configured",
            failure_recording.get("event_log_failure_required") is True
            and failure_recording.get("raw_broker_payload_stored") is False,
        ),
        _check("live_capital_disabled", source_record.get("live_capital_enabled") is False),
        _check(
            "prediction_market_write_disabled",
            source_record.get("prediction_market_write_allowed") is False,
        ),
        _check("broker_post_not_called_before_submit", source_record.get("broker_post_called") is False),
        _check(
            "paper_order_not_submitted_before_submit",
            source_record.get("paper_order_submitted") is False,
        ),
    ]


def _gate_state(blockers: list[str], *, submit_path_available: bool) -> str:
    if submit_path_available:
        return "ready_for_guarded_paper_submit"
    if "paper_submit_approval_present" in blockers:
        return "blocked_missing_paper_submit_approval"
    if "source_dry_run_receipt_ready" in blockers or "source_request_preview_ready" in blockers:
        return "blocked_missing_q5_7_submit_prerequisites"
    if "event_log_prewrite_complete" in blockers:
        return "blocked_missing_event_log_prewrite"
    if "pre_trade_snapshot_captured" in blockers:
        return "blocked_missing_pre_trade_snapshot"
    if "duplicate_order_guard_clear" in blockers:
        return "blocked_duplicate_order_guard"
    return "blocked_prerequisites_missing"


def _paper_submit_record(
    source_record: dict[str, Any],
    *,
    dry_run_errors: list[str],
    approval: dict[str, Any],
    account_context: dict[str, Any],
    generated_at: str,
    force_ready: bool = False,
    submit_execution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    strategy_key = str(source_record.get("strategy_family_key") or "unknown_strategy")
    artifact_id = f"phase5:q5-8:paper-submit-enable:{_safe_key(strategy_key)}"
    duplicate_guard = deepcopy(source_record.get("duplicate_order_guard", {}))
    if not isinstance(duplicate_guard, dict):
        duplicate_guard = {}
    submit_prerequisites_ready = force_ready or _source_ready_for_submit_path(
        source_record,
        dry_run_errors=dry_run_errors,
        approval=approval,
        account_context=account_context,
        duplicate_guard=duplicate_guard,
    )
    idempotency_key_allocated_for_submit = submit_prerequisites_ready
    event_log_prewrite = _event_log_prewrite(source_record, ready=submit_prerequisites_ready)
    pre_trade_snapshot = _pre_trade_snapshot(source_record, captured=submit_prerequisites_ready)
    preliminary_submit_path = _submit_path_metadata(submit_path_available=True)
    checks = _checks(
        source_record,
        dry_run_errors=dry_run_errors,
        approval=approval,
        account_context=account_context,
        duplicate_guard=duplicate_guard,
        event_log_prewrite=event_log_prewrite,
        pre_trade_snapshot=pre_trade_snapshot,
        submit_path=preliminary_submit_path,
        idempotency_key_allocated_for_submit=idempotency_key_allocated_for_submit,
    )
    blockers = sorted(
        check["name"]
        for check in checks
        if not check.get("passed")
    )
    submit_path_available = not blockers
    submit_path = _submit_path_metadata(submit_path_available=submit_path_available)
    if not submit_path_available:
        checks = [
            _check(
                check["name"],
                False if check["name"] == "submit_path_singleton" else bool(check["passed"]),
                detail=check.get("detail"),
            )
            for check in checks
        ]
        blockers = sorted(
            check["name"]
            for check in checks
            if not check.get("passed")
        )
    submission_recorded = (
        submit_path_available
        and submit_execution is not None
        and submit_execution.get("paper_order_submitted") is True
        and submit_execution.get("broker_submit_receipt_created") is True
        and submit_execution.get("strategy_family_key") == strategy_key
        and submit_execution.get("path_key") == PAPER_SUBMIT_PATH_KEY
        and submit_execution.get("idempotency_key") == source_record.get("idempotency_key")
        and submit_execution.get("broker_post_called") is False
        and submit_execution.get("alpaca_post_called") is False
        and submit_execution.get("live_endpoint_allowed") is False
        and submit_execution.get("live_capital_enabled") is False
    )
    authority = _authority_ledger(submit_path_available=submit_path_available)
    record = {
        "schema_version": PHASE5_ARTIFACT_SCHEMA_VERSION,
        "paper_submit_enablement_schema_version": PHASE5_PAPER_SUBMIT_ENABLEMENT_SCHEMA_VERSION,
        "artifact_type": "broker_submit_receipt",
        "artifact_id": artifact_id,
        "phase": "Q5",
        "stage": "Q5-8",
        "status": "submitted_paper_order" if submission_recorded else "blocked",
        "generated_at": generated_at,
        "public_safe": True,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "authority_ledger": authority,
        "source_posture": phase5_source_posture(),
        "provenance": phase5_provenance(PAPER_SUBMIT_ENABLEMENT_SOURCE_REFS),
        "boundary": PAPER_SUBMIT_ENABLEMENT_BOUNDARY,
        **phase5_authority_defaults(),
        "source_alpaca_paper_dry_run_artifact_id": source_record.get("artifact_id"),
        "source_dry_run_status": source_record.get("status"),
        "source_receipt_state": source_record.get("receipt_state"),
        "source_request_preview_allowed": source_record.get("request_preview_allowed") is True,
        "source_dry_run_receipt_created": source_record.get("dry_run_receipt_created") is True,
        "strategy_family_key": strategy_key,
        "selected_venue": "alpaca_paper",
        "broker_adapter": "alpaca",
        "receipt_state": (
            "paper_submit_receipt_recorded"
            if submission_recorded
            else "paper_submit_gate_ready"
            if submit_path_available
            else "not_submitted"
        ),
        "paper_submit_approval_state": approval.get("approval_state", "missing"),
        "paper_submit_approval_scope": approval.get("approval_scope", "alpaca_paper_submit"),
        "paper_submit_approval_present": approval.get("approval_present") is True,
        "paper_submit_approval_logged": approval.get("approval_logged") is True,
        "explicit_paper_submit_approval": approval.get("explicit_paper_submit_approval") is True,
        "paper_submit_gate_state": _gate_state(blockers, submit_path_available=submit_path_available),
        "submit_path_available": submit_path_available,
        "submit_path_available_count": 1 if submit_path_available else 0,
        "submit_path_key": PAPER_SUBMIT_PATH_KEY,
        "submit_path": submit_path,
        "submit_request_preview": _submit_request_preview(source_record),
        "pre_trade_snapshot": pre_trade_snapshot,
        "event_log_prewrite": event_log_prewrite,
        "duplicate_order_guard": duplicate_guard,
        "broker_submit_result": _broker_submit_result(submit_execution if submission_recorded else None),
        "source_guarded_submit_receipt_artifact_id": (
            submit_execution.get("artifact_id") if submission_recorded and submit_execution else None
        ),
        "submitted_order_ref": (
            submit_execution.get("submitted_order_ref") if submission_recorded and submit_execution else None
        ),
        "broker_receipt_ref": (
            submit_execution.get("broker_receipt_ref") if submission_recorded and submit_execution else None
        ),
        "broker_receipt_state": (
            submit_execution.get("broker_receipt_state") if submission_recorded and submit_execution else None
        ),
        "idempotency_material": deepcopy(source_record.get("idempotency_material", {})),
        "idempotency_key": source_record.get("idempotency_key"),
        "idempotency_key_preview": source_record.get("idempotency_key_preview"),
        "idempotency_key_allocated": idempotency_key_allocated_for_submit,
        "idempotency_key_allocated_for_submit": idempotency_key_allocated_for_submit,
        "required_checks": list(PAPER_SUBMIT_ENABLEMENT_REQUIRED_CHECKS),
        "required_check_count": len(PAPER_SUBMIT_ENABLEMENT_REQUIRED_CHECKS),
        "checks": checks,
        "failed_checks": blockers,
        "failed_check_count": len(blockers),
        "blocked_reasons": blockers,
        "blocked_reason_count": len(blockers),
        "secret_value_exposed": False,
        "raw_payload_exposed": False,
        "local_path_exposed": False,
        "authorization_header_exposed": False,
        "base_url_exposed": False,
        "risk_approval_allowed": False,
        "trade_candidate_created": False,
        "execution_policy_handoff_allowed": False,
        "execution_allowed": False,
        "execution_intent_created": False,
        "paper_order_staging_allowed": False,
        "paper_order_submitted": submission_recorded,
        "broker_post_called": False,
        "alpaca_post_called": False,
        "broker_submit_receipt_created": submission_recorded,
        "prediction_market_write_allowed": False,
        "telegram_live_notifications_allowed": False,
        "position_created": False,
        "position_monitor_write_authority": False,
        "live_capital_enabled": False,
        "live_endpoint_allowed": False,
        "crypto_perps_write_allowed": False,
        "paid_preference_tools_allowed": False,
        "source_quorum_bypass_allowed": False,
        "submission_allowed": submit_path_available,
        "broker_submit_ready": submit_path_available,
        "paper_execution_allowed": submit_path_available,
        "paper_order_allowed": submit_path_available,
        "paper_order_submission_allowed": submit_path_available,
        "broker_write_allowed": submit_path_available,
        "execution_adapter_write_authority": submit_path_available,
    }
    record["validation_errors"] = validate_phase5_paper_submit_enablement_record(record)
    return record


def build_phase5_paper_submit_enablement_gate(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    dry_run_bundle = _dry_run_bundle(settings)
    dry_run_errors = validate_phase5_alpaca_paper_dry_run_bundle(dry_run_bundle)
    approval = paper_submit_approval_status(settings)
    account_context = paper_account_shadow_context(settings)
    submit_execution = _guarded_paper_submit_receipt(settings)
    generated_at = _now()
    records = [
        _paper_submit_record(
            record,
            dry_run_errors=dry_run_errors,
            approval=approval,
            account_context=account_context,
            generated_at=generated_at,
            submit_execution=submit_execution,
        )
        for record in dry_run_bundle.get("records", [])
        if isinstance(record, dict)
    ]
    status_counts = Counter(str(record.get("status") or "unknown") for record in records)
    gate_state_counts = Counter(str(record.get("paper_submit_gate_state") or "unknown") for record in records)
    receipt_state_counts = Counter(str(record.get("receipt_state") or "unknown") for record in records)
    idempotency_counts = Counter(str(record.get("idempotency_key") or "") for record in records)
    duplicate_keys = {key for key, count in idempotency_counts.items() if key and count > 1}
    bundle = {
        "schema_version": PHASE5_PAPER_SUBMIT_ENABLEMENT_SCHEMA_VERSION,
        "artifact_type": "phase5_paper_submit_enablement_gate_bundle",
        "artifact_id": "phase5:q5-8:paper-submit-enablement-gate",
        "phase": "Q5",
        "stage": "Q5-8",
        "status": "ok",
        "generated_at": generated_at,
        "public_safe": True,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_event_count": 0,
        "runtime_artifact_path": None,
        "history_log_path": None,
        "authority_ledger": _authority_ledger(submit_path_available=False),
        "source_posture": phase5_source_posture(),
        "provenance": phase5_provenance(PAPER_SUBMIT_ENABLEMENT_SOURCE_REFS),
        "boundary": PAPER_SUBMIT_ENABLEMENT_BOUNDARY,
        **phase5_authority_defaults(),
        "canonical_source_count": EXPECTED_SOURCE_COUNT,
        "source_dry_run_record_count": int(dry_run_bundle.get("dry_run_record_count", 0) or 0),
        "source_request_preview_count": int(dry_run_bundle.get("request_preview_count", 0) or 0),
        "source_dry_run_receipt_count": int(dry_run_bundle.get("dry_run_receipt_count", 0) or 0),
        "submit_enablement_record_count": len(records),
        "submit_path_available_count": sum(1 for record in records if record.get("submit_path_available") is True),
        "blocked_count": status_counts.get("blocked", 0),
        "paper_submit_approval_present": approval.get("approval_present") is True,
        "paper_submit_approval_logged": approval.get("approval_logged") is True,
        "paper_submit_approval_state": approval.get("approval_state", "missing"),
        "status_counts": dict(sorted(status_counts.items())),
        "gate_state_counts": dict(sorted(gate_state_counts.items())),
        "receipt_state_counts": dict(sorted(receipt_state_counts.items())),
        "required_check_count": len(PAPER_SUBMIT_ENABLEMENT_REQUIRED_CHECKS),
        "idempotency_key_count": len([key for key in idempotency_counts if key]),
        "idempotency_collision_count": len(duplicate_keys),
        "duplicate_guard_collision_count": sum(
            1
            for record in records
            if record.get("duplicate_order_guard", {}).get("collision_detected") is True
        ),
        "dry_run_bundle_validation_error_count": len(dry_run_errors),
        "approval": approval,
        "records": records,
    }
    for field in PAPER_SUBMIT_ENABLEMENT_COUNT_FIELDS:
        if field in {
            "execution_adapter_write_authority_count",
            "paper_execution_allowed_count",
            "paper_order_allowed_count",
            "paper_order_submission_allowed_count",
            "broker_write_allowed_count",
        }:
            bundle[field] = sum(
                1
                for record in records
                if record.get(field.removesuffix("_count")) is True
            )
        else:
            bundle[field] = sum(
                1
                for record in records
                if record.get(field.removesuffix("_count")) is True
            )
    bundle["validation_errors"] = validate_phase5_paper_submit_enablement_bundle(bundle)
    bundle["status"] = "ok" if not bundle["validation_errors"] else "error"
    return bundle


def _record_allowed_authority_fields(record: dict[str, Any]) -> tuple[str, ...]:
    if record.get("submit_path_available") is True:
        return PAPER_SUBMIT_ENABLEMENT_ALLOWED_AUTHORITY_FIELDS
    return ()


def _base_record_errors(record: dict[str, Any]) -> list[str]:
    errors = list(
        validate_phase5_artifact(
            record,
            expected_stage="Q5-8",
            allowed_authority_fields=_record_allowed_authority_fields(record),
        )
    )
    if record.get("artifact_type") != "broker_submit_receipt":
        errors.append("artifact_type_not_broker_submit_receipt")
    if record.get("paper_submit_enablement_schema_version") != PHASE5_PAPER_SUBMIT_ENABLEMENT_SCHEMA_VERSION:
        errors.append("paper_submit_enablement_schema_version_mismatch")
    if record.get("required_check_count") != len(PAPER_SUBMIT_ENABLEMENT_REQUIRED_CHECKS):
        errors.append("required_check_count_mismatch")
    check_names = {
        str(check.get("name") or "")
        for check in record.get("checks", [])
        if isinstance(check, dict)
    }
    for check in PAPER_SUBMIT_ENABLEMENT_REQUIRED_CHECKS:
        if check not in check_names:
            errors.append(f"required_check_missing:{check}")
    if record.get("event_log_written") is True:
        if not str(record.get("event_log_correlation_id") or "").strip():
            errors.append("event_log_correlation_id_missing")
        if not str(record.get("event_log_path") or "").strip():
            errors.append("event_log_path_missing")
    blockers = record.get("blocked_reasons", [])
    if not isinstance(blockers, list):
        errors.append("blocked_reasons_not_list")
        blockers = []
    if record.get("blocked_reason_count") != len(blockers):
        errors.append("blocked_reason_count_mismatch")
    return errors


def _nested_record_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    submit_path = record.get("submit_path", {})
    if not isinstance(submit_path, dict):
        errors.append("submit_path_not_dict")
        submit_path = {}
    if submit_path.get("path_key") != PAPER_SUBMIT_PATH_KEY:
        errors.append("submit_path_key_invalid")
    if submit_path.get("adapter") != "alpaca":
        errors.append("submit_path_adapter_invalid")
    if submit_path.get("selected_venue") != "alpaca_paper":
        errors.append("submit_path_venue_invalid")
    if submit_path.get("paper_only") is not True:
        errors.append("submit_path_not_paper_only")
    if submit_path.get("http_method") != "POST":
        errors.append("submit_path_method_invalid")
    if submit_path.get("broker_path_template") != "/v2/orders":
        errors.append("submit_path_broker_path_invalid")
    for field in ("base_url_exposed", "authorization_header_included", "post_call_performed"):
        if submit_path.get(field) is not False:
            errors.append(f"submit_path_authority_or_exposure_enabled:{field}")
    if float(submit_path.get("timeout_seconds", 0.0) or 0.0) <= 0:
        errors.append("submit_path_timeout_missing")
    retry_policy = submit_path.get("retry_policy", {})
    if not isinstance(retry_policy, dict):
        errors.append("submit_path_retry_policy_missing")
        retry_policy = {}
    if retry_policy.get("max_attempts") != 2:
        errors.append("submit_path_retry_attempts_invalid")
    if retry_policy.get("retry_requires_same_idempotency_key") is not True:
        errors.append("submit_path_retry_idempotency_not_required")
    if "timeout" not in retry_policy.get("retry_on", []):
        errors.append("submit_path_retry_timeout_missing")
    failure_recording = submit_path.get("failure_recording", {})
    if not isinstance(failure_recording, dict):
        errors.append("submit_path_failure_recording_missing")
        failure_recording = {}
    if failure_recording.get("event_log_failure_required") is not True:
        errors.append("submit_path_failure_event_log_not_required")
    if failure_recording.get("raw_broker_payload_stored") is not False:
        errors.append("submit_path_failure_raw_payload_stored")
    event_log_prewrite = record.get("event_log_prewrite", {})
    if not isinstance(event_log_prewrite, dict):
        errors.append("event_log_prewrite_not_dict")
        event_log_prewrite = {}
    if record.get("submit_path_available") is True and event_log_prewrite.get("prewrite_complete") is not True:
        errors.append("submit_path_available_without_event_log_prewrite")
    snapshot = record.get("pre_trade_snapshot", {})
    if not isinstance(snapshot, dict):
        errors.append("pre_trade_snapshot_not_dict")
        snapshot = {}
    if record.get("submit_path_available") is True and snapshot.get("captured") is not True:
        errors.append("submit_path_available_without_pre_trade_snapshot")
    for field in ("write_authority", "live_capital_enabled", "raw_payload_exposed"):
        if snapshot.get(field) is not False:
            errors.append(f"pre_trade_snapshot_authority_or_exposure_enabled:{field}")
    duplicate_guard = record.get("duplicate_order_guard", {})
    if not isinstance(duplicate_guard, dict):
        errors.append("duplicate_guard_not_dict")
        duplicate_guard = {}
    if duplicate_guard.get("collision_checked") is not True:
        errors.append("duplicate_guard_collision_not_checked")
    if duplicate_guard.get("collision_detected") is not False:
        errors.append("duplicate_guard_collision_detected")
    if duplicate_guard.get("duplicate_detected") is not False:
        errors.append("duplicate_guard_duplicate_detected")
    request_preview = record.get("submit_request_preview", {})
    if not isinstance(request_preview, dict):
        errors.append("submit_request_preview_not_dict")
        request_preview = {}
    for field in ("post_call_allowed", "authorization_header_included", "base_url_exposed", "raw_payload_exposed"):
        if request_preview.get(field) is not False:
            errors.append(f"submit_request_preview_authority_or_exposure_enabled:{field}")
    result = record.get("broker_submit_result", {})
    if not isinstance(result, dict):
        errors.append("broker_submit_result_not_dict")
        result = {}
    submitted = record.get("paper_order_submitted") is True
    for field in (
        "broker_post_called",
        "alpaca_post_called",
        "external_broker_post_performed",
        "broker_order_id_exposed",
        "raw_broker_payload_stored",
    ):
        if result.get(field) is not False:
            errors.append(f"broker_submit_result_authority_or_exposure_enabled:{field}")
    if submitted:
        if result.get("paper_order_submitted") is not True:
            errors.append("broker_submit_result_missing_submitted_order")
        if result.get("broker_submit_receipt_created") is not True:
            errors.append("broker_submit_result_missing_receipt")
        if result.get("status") != "submitted_paper_order_recorded":
            errors.append("broker_submit_result_status_invalid")
        if not str(result.get("submitted_order_ref") or "").strip():
            errors.append("broker_submit_result_order_ref_missing")
        if not str(result.get("broker_receipt_ref") or "").strip():
            errors.append("broker_submit_result_receipt_ref_missing")
    else:
        if result.get("paper_order_submitted") is not False:
            errors.append("broker_submit_result_order_submitted_without_record")
        if result.get("broker_submit_receipt_created") is not False:
            errors.append("broker_submit_result_receipt_without_record")
    return errors


def validate_phase5_paper_submit_enablement_record(record: dict[str, Any]) -> list[str]:
    errors = _base_record_errors(record)
    if record.get("public_safe") is not True:
        errors.append("paper_submit_enablement_not_public_safe")
    if not str(record.get("idempotency_key") or "").startswith("q5-7-dryrun-"):
        errors.append("idempotency_key_not_q5_7_source_scoped")
    if record.get("idempotency_key") != record.get("idempotency_key_preview"):
        errors.append("idempotency_key_preview_mismatch")
    for exposure in (
        "secret_value_exposed",
        "raw_payload_exposed",
        "local_path_exposed",
        "authorization_header_exposed",
        "base_url_exposed",
    ):
        if record.get(exposure) is not False:
            errors.append(f"paper_submit_enablement_exposure_enabled:{exposure}")
    submission_recorded = record.get("paper_order_submitted") is True
    for field in PAPER_SUBMIT_ENABLEMENT_BOUNDARY_FIELDS:
        if field in {"paper_order_submitted", "broker_submit_receipt_created"} and submission_recorded:
            continue
        if record.get(field) is not False:
            errors.append(f"paper_submit_enablement_boundary_enabled:{field}")
    if submission_recorded:
        if record.get("submit_path_available") is not True:
            errors.append("paper_order_submitted_without_submit_path")
        if record.get("broker_submit_receipt_created") is not True:
            errors.append("paper_order_submitted_without_receipt")
        if record.get("receipt_state") != "paper_submit_receipt_recorded":
            errors.append("paper_order_submitted_receipt_state_invalid")
        if not str(record.get("submitted_order_ref") or "").strip():
            errors.append("paper_order_submitted_ref_missing")
        if not str(record.get("broker_receipt_ref") or "").strip():
            errors.append("paper_order_submitted_receipt_ref_missing")
        if record.get("broker_post_called") is not False:
            errors.append("paper_order_submitted_broker_post_called")
        if record.get("alpaca_post_called") is not False:
            errors.append("paper_order_submitted_alpaca_post_called")
    elif record.get("broker_submit_receipt_created") is not False:
        errors.append("broker_receipt_created_without_paper_order")
    if record.get("submit_path_available") is True:
        if record.get("paper_submit_approval_present") is not True:
            errors.append("submit_path_available_without_paper_submit_approval")
        if record.get("paper_submit_approval_logged") is not True:
            errors.append("submit_path_available_without_logged_approval")
        if record.get("idempotency_key_allocated_for_submit") is not True:
            errors.append("submit_path_available_without_submit_idempotency")
        for field in PAPER_SUBMIT_ENABLEMENT_ALLOWED_AUTHORITY_FIELDS:
            if record.get(field) is not True:
                errors.append(f"submit_path_authority_not_enabled:{field}")
        enabled_allowed = [
            field
            for field in PAPER_SUBMIT_ENABLEMENT_ALLOWED_AUTHORITY_FIELDS
            if record.get(field) is True
        ]
        if len(enabled_allowed) != len(PAPER_SUBMIT_ENABLEMENT_ALLOWED_AUTHORITY_FIELDS):
            errors.append("submit_path_allowed_authority_count_mismatch")
        failed_checks = record.get("failed_checks", [])
        if failed_checks:
            errors.append("submit_path_available_with_failed_checks")
    else:
        for field in PAPER_SUBMIT_ENABLEMENT_ALLOWED_AUTHORITY_FIELDS:
            if record.get(field) is not False:
                errors.append(f"paper_submit_authority_enabled_without_path:{field}")
    for field in PHASE5_AUTHORITY_FIELDS:
        if field in PAPER_SUBMIT_ENABLEMENT_ALLOWED_AUTHORITY_FIELDS and record.get("submit_path_available") is True:
            continue
        if record.get(field) is not False:
            errors.append(f"phase5_authority_enabled:{field}")
    if record.get("broker_post_called") is not False:
        errors.append("broker_post_called_before_submit")
    if record.get("alpaca_post_called") is not False:
        errors.append("alpaca_post_called_before_submit")
    if record.get("paper_order_submitted") is not False and not submission_recorded:
        errors.append("paper_order_submitted_before_submit")
    if record.get("live_endpoint_allowed") is not False:
        errors.append("live_endpoint_allowed")
    if record.get("live_capital_enabled") is not False:
        errors.append("live_capital_enabled")
    if record.get("prediction_market_write_allowed") is not False:
        errors.append("prediction_market_write_allowed")
    errors.extend(_nested_record_errors(record))
    return sorted(set(errors))


def validate_phase5_paper_submit_enablement_bundle(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schema_version",
        "artifact_type",
        "artifact_id",
        "phase",
        "stage",
        "status",
        "generated_at",
        "public_safe",
        "event_log_required",
        "event_log_written",
        "authority_ledger",
        "source_posture",
        "provenance",
        "source_dry_run_record_count",
        "submit_enablement_record_count",
        "submit_path_available_count",
        "blocked_count",
        "records",
        "boundary",
    }
    missing = sorted(required_fields - set(bundle))
    if missing:
        errors.append("bundle_missing_fields:" + ",".join(missing))
    if bundle.get("schema_version") != PHASE5_PAPER_SUBMIT_ENABLEMENT_SCHEMA_VERSION:
        errors.append("bundle_schema_version_mismatch")
    if bundle.get("artifact_type") != "phase5_paper_submit_enablement_gate_bundle":
        errors.append("bundle_artifact_type_mismatch")
    if bundle.get("phase") != "Q5" or bundle.get("stage") != "Q5-8":
        errors.append("bundle_phase_stage_mismatch")
    if bundle.get("public_safe") is not True:
        errors.append("bundle_public_safe_not_true")
    records = bundle.get("records", [])
    if not isinstance(records, list):
        errors.append("records_not_list")
        records = []
    if bundle.get("submit_enablement_record_count") != len(records):
        errors.append("submit_enablement_record_count_mismatch")
    if bundle.get("source_dry_run_record_count") != len(records):
        errors.append("source_dry_run_record_count_mismatch")
    if bundle.get("submit_path_available_count") != sum(
        1 for record in records if isinstance(record, dict) and record.get("submit_path_available") is True
    ):
        errors.append("submit_path_available_count_mismatch")
    status_counts = Counter(
        str(record.get("status") or "unknown")
        for record in records
        if isinstance(record, dict)
    )
    if bundle.get("blocked_count") != status_counts.get("blocked", 0):
        errors.append("blocked_count_mismatch")
    if int(bundle.get("paper_order_submitted_count", 0) or 0) > int(
        bundle.get("submit_path_available_count", 0) or 0
    ):
        errors.append("paper_order_submitted_count_exceeds_submit_path_count")
    if int(bundle.get("broker_submit_receipt_created_count", 0) or 0) != int(
        bundle.get("paper_order_submitted_count", 0) or 0
    ):
        errors.append("broker_submit_receipt_count_mismatch")
    if bundle.get("event_log_written") is True:
        if not str(bundle.get("event_log_path") or "").strip():
            errors.append("bundle_event_log_path_missing")
        if bundle.get("event_log_event_count") != len(records):
            errors.append("bundle_event_log_count_mismatch")
    if bundle.get("paper_submit_approval_present") is True and bundle.get("paper_submit_approval_logged") is not True:
        errors.append("approval_present_without_approval_logged")
    if bundle.get("idempotency_collision_count") != 0:
        errors.append("idempotency_collision_count_not_zero")
    if bundle.get("duplicate_guard_collision_count") != 0:
        errors.append("duplicate_guard_collision_count_not_zero")
    for field in PHASE5_AUTHORITY_FIELDS:
        if bundle.get(field) is not False:
            errors.append(f"bundle_phase5_authority_enabled:{field}")
    for record in records:
        if not isinstance(record, dict):
            errors.append("paper_submit_enablement_record_not_dict")
            continue
        errors.extend(validate_phase5_paper_submit_enablement_record(record))
    return sorted(set(errors))


def attach_phase5_paper_submit_enablement_event_log(
    bundle: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], tuple[EventLogEntry, ...]]:
    output = deepcopy(bundle)
    log_path = Path(event_log_path or (_runtime_dir(settings) / PAPER_SUBMIT_ENABLEMENT_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entries: list[EventLogEntry] = []
    for record in output.get("records", []):
        if not isinstance(record, dict):
            continue
        entry = log.write(
            PAPER_SUBMIT_ENABLEMENT_EVENT_TYPE,
            PAPER_SUBMIT_ENABLEMENT_COMPONENT,
            {
                "artifact_id": record.get("artifact_id"),
                "source_alpaca_paper_dry_run_artifact_id": record.get(
                    "source_alpaca_paper_dry_run_artifact_id"
                ),
                "strategy_family_key": record.get("strategy_family_key"),
                "status": record.get("status"),
                "paper_submit_gate_state": record.get("paper_submit_gate_state"),
                "submit_path_available": record.get("submit_path_available"),
                "paper_submit_approval_present": record.get("paper_submit_approval_present"),
                "broker_post_called": record.get("broker_post_called"),
                "broker_write_allowed": record.get("broker_write_allowed"),
                "paper_order_submitted": record.get("paper_order_submitted"),
                "broker_submit_receipt_created": record.get("broker_submit_receipt_created"),
                "live_capital_enabled": record.get("live_capital_enabled"),
                "blocked_reason_count": record.get("blocked_reason_count"),
                "boundary": record.get("boundary"),
            },
        )
        record["event_log_written"] = True
        record["event_log_path"] = str(log.path)
        record["event_log_correlation_id"] = entry.correlation_id
        record["event_log_created_at"] = entry.created_at
        record["validation_errors"] = validate_phase5_paper_submit_enablement_record(record)
        entries.append(entry)
    output["event_log_written"] = bool(entries)
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = len(entries)
    output["validation_errors"] = validate_phase5_paper_submit_enablement_bundle(output)
    output["status"] = "ok" if not output["validation_errors"] else "error"
    return output, tuple(entries)


def write_phase5_paper_submit_enablement_gate(
    bundle: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(bundle)
    output_path, history_path, default_event_path = paper_submit_enablement_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase5_paper_submit_enablement_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase5_paper_submit_enablement_bundle(output)
        output["status"] = "ok" if not output["validation_errors"] else "error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase5_paper_submit_enablement_bundle(output)
    output["status"] = "ok" if not output["validation_errors"] else "error"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE5_PAPER_SUBMIT_ENABLEMENT_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "submit_enablement_record_count": output.get("submit_enablement_record_count"),
        "submit_path_available_count": output.get("submit_path_available_count"),
        "paper_order_submitted_count": output.get("paper_order_submitted_count"),
        "broker_submit_receipt_created_count": output.get("broker_submit_receipt_created_count"),
        "blocked_count": output.get("blocked_count"),
        "paper_submit_approval_present": output.get("paper_submit_approval_present"),
        "event_log_written": output.get("event_log_written"),
        "event_log_event_count": output.get("event_log_event_count"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output
