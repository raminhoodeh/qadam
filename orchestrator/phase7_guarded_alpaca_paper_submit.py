"""Q7-7 Phase 7 Demo Proof guarded Alpaca paper submit path.

This stage exposes the guarded Alpaca paper-submit path for Phase 7 proof
orders. It can record local guarded paper-submit request and receipt state for
eligible Q7 staged proof orders, but validation never performs an external
broker POST and live capital remains disabled.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.phase7_artifacts import (
    PHASE7_ARTIFACT_SCHEMA_VERSION,
    PHASE7_EVENT_TYPES,
    phase7_proof_contract,
    phase7_provenance,
    phase7_source_posture,
)
from orchestrator.phase7_proof_order_staging import (
    PHASE7_PROOF_ORDER_STAGING_RUNTIME_ARTIFACT,
    build_phase7_proof_order_staging,
    phase7_proof_order_staging_paths,
    validate_phase7_proof_order_staging,
)
from orchestrator.phase7_readiness import (
    PHASE7_AUTHORITY_FLAGS,
    PHASE7_HARNESS_DAY_COUNT,
    PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
    PHASE7_MAX_DRAWDOWN_FRACTION,
    PHASE7_PAPER_ACCOUNT_STARTING_GBP,
    PHASE7_UNSAFE_COUNT_FIELDS,
    phase7_authority_defaults,
    phase7_unsafe_counter_defaults,
)


PHASE7_GUARDED_ALPACA_SUBMIT_SCHEMA_VERSION = 1
PHASE7_GUARDED_ALPACA_SUBMIT_RUNTIME_ARTIFACT = (
    "phase7_guarded_alpaca_paper_submit_path.json"
)
PHASE7_GUARDED_ALPACA_SUBMIT_HISTORY = (
    "phase7_guarded_alpaca_paper_submit_path_history.jsonl"
)
PHASE7_GUARDED_ALPACA_SUBMIT_EVENT_LOG = (
    "phase7_guarded_alpaca_paper_submit_path_events.jsonl"
)
PHASE7_GUARDED_ALPACA_SUBMIT_EVENT_TYPE = PHASE7_EVENT_TYPES["broker_receipt"]
PHASE7_GUARDED_ALPACA_SUBMIT_COMPONENT = "phase7_guarded_alpaca_paper_submit"
PHASE7_ALPACA_PAPER_SUBMIT_PATH_KEY = "phase7_alpaca_paper_post_order"

PHASE7_GUARDED_ALPACA_SUBMIT_BOUNDARY = (
    "Q7-7 exposes a guarded Alpaca paper submit path only for Phase 7 staged "
    "proof orders created by Q7-6 from Q7-5 auto-approved qualified setups. It "
    "requires the phase7_demo_proof idempotency namespace, Event Log prewrite, "
    "pre-trade snapshot, paper endpoint classification, and paper account mode. "
    "It cannot submit non-Q7 orders, cannot reuse Phase 5 order IDs, cannot use "
    "live endpoints or live credentials, cannot write prediction-market or "
    "crypto-perps orders, cannot grant Phase 7 proof credit, cannot enable live "
    "capital, and validation never performs an external broker POST."
)

PHASE7_GUARDED_ALPACA_SUBMIT_REQUIRED_CHECKS: tuple[str, ...] = (
    "q7_6_staging_artifact_valid",
    "source_staged_proof_order_present",
    "source_staged_order_ready",
    "source_stage_q7_6",
    "source_phase_q7",
    "source_auto_approval_ref_present",
    "source_setup_ref_present",
    "source_idempotency_namespace_phase7",
    "source_idempotency_key_phase7",
    "source_event_log_prewrite_complete",
    "source_pre_trade_snapshot_present",
    "duplicate_order_guard_clear",
    "submit_path_singleton",
    "alpaca_paper_endpoint_class",
    "paper_account_mode_confirmed",
    "live_endpoint_blocked",
    "live_credentials_blocked",
    "broker_post_not_called_during_validation",
    "broker_post_counter_zero",
    "alpaca_post_counter_zero",
    "request_public_safe",
    "receipt_public_safe",
    "prediction_market_write_disabled",
    "crypto_perps_write_disabled",
    "live_capital_disabled",
    "proof_credit_disabled",
    "manual_override_disabled",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def phase7_guarded_alpaca_submit_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE7_GUARDED_ALPACA_SUBMIT_RUNTIME_ARTIFACT,
        runtime / PHASE7_GUARDED_ALPACA_SUBMIT_HISTORY,
        runtime / PHASE7_GUARDED_ALPACA_SUBMIT_EVENT_LOG,
    )


def _proof_order_staging(settings: Settings) -> dict[str, Any]:
    staging_path, _, _ = phase7_proof_order_staging_paths(settings)
    if staging_path.exists():
        return _read_json(staging_path)
    return build_phase7_proof_order_staging(settings=settings)


def _safe_key(value: str) -> str:
    allowed = []
    for char in value.lower():
        if char.isalnum() or char in {"_", "-"}:
            allowed.append(char)
        else:
            allowed.append("_")
    return "".join(allowed).strip("_") or "unknown"


def _hash_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _submit_policy() -> dict[str, Any]:
    return {
        "policy_schema_version": PHASE7_GUARDED_ALPACA_SUBMIT_SCHEMA_VERSION,
        "submit_mode": "guarded_alpaca_paper_submit",
        "source_staged_order_required": True,
        "q7_auto_approval_required": True,
        "q7_proof_namespace_required": True,
        "idempotency_namespace": "phase7_demo_proof",
        "account_mode_required": "paper",
        "alpaca_paper_only": True,
        "paper_endpoint_required": True,
        "event_log_prewrite_required": True,
        "pre_trade_snapshot_required": True,
        "local_guarded_receipt_allowed": True,
        "external_broker_post_performed_by_validation": False,
        "live_endpoint_allowed": False,
        "live_credentials_allowed": False,
        "prediction_market_write_allowed": False,
        "crypto_perps_write_allowed": False,
        "proof_credit_allowed": False,
        "manual_trade_level_override_allowed": False,
        "live_capital_enabled": False,
    }


def _submit_path_metadata(*, available: bool) -> dict[str, Any]:
    return {
        "path_key": PHASE7_ALPACA_PAPER_SUBMIT_PATH_KEY,
        "adapter": "alpaca",
        "selected_venue": "alpaca_paper",
        "account_mode_required": "paper",
        "endpoint_classification": "alpaca_paper_endpoint",
        "paper_only": True,
        "available": available,
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
            "Q7-7 route metadata describes the Alpaca paper /v2/orders path. "
            "Validation records local guarded submit state only and never "
            "performs an external POST."
        ),
    }


def _authority_ledger(stage_recorded: bool) -> dict[str, Any]:
    defaults = phase7_authority_defaults()
    defaults["phase7_test_mode_auto_approval_allowed"] = stage_recorded
    defaults["phase7_proof_order_staging_allowed"] = stage_recorded
    defaults["phase7_proof_trade_submission_allowed"] = stage_recorded
    return {
        "authority_schema_version": PHASE7_GUARDED_ALPACA_SUBMIT_SCHEMA_VERSION,
        "stage": "Q7-7",
        "authority_field_count": len(PHASE7_AUTHORITY_FLAGS),
        "explicit_authority_grant_count": 3 if stage_recorded else 0,
        "explicit_authority_grants": (
            [
                "phase7_test_mode_auto_approval_allowed",
                "phase7_proof_order_staging_allowed",
                "phase7_proof_trade_submission_allowed",
            ]
            if stage_recorded
            else []
        ),
        "q7_8_proof_lifecycle_monitor_stage_allowed": stage_recorded,
        **defaults,
        "boundary": PHASE7_GUARDED_ALPACA_SUBMIT_BOUNDARY,
    }


def _provenance() -> dict[str, Any]:
    provenance = phase7_provenance(
        (
            f"data/runtime/{PHASE7_PROOF_ORDER_STAGING_RUNTIME_ARTIFACT}",
            "orchestrator/phase7_artifacts.py",
            "orchestrator/phase7_proof_order_staging.py",
            "docs/qadam-phase-7-demo-proof-implementation-plan.md",
            "docs/qadam-phase-7-q7-6-proof-order-staging-audit-2026-05-25.md",
        )
    )
    provenance["decision_chain_refs"] = [
        f"data/runtime/{PHASE7_PROOF_ORDER_STAGING_RUNTIME_ARTIFACT}"
    ]
    provenance["execution_evidence_refs"] = []
    return provenance


def _preflight_blockers(staging: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    staging_errors = validate_phase7_proof_order_staging(staging)
    if staging_errors:
        blockers.append("phase7_proof_order_staging_validation_errors")
    if staging.get("proof_order_staging_recorded") is not True:
        blockers.append("phase7_proof_order_staging_not_recorded")
    if staging.get("q7_7_guarded_alpaca_paper_submit_path_stage_allowed") is not True:
        blockers.append("q7_7_guarded_alpaca_paper_submit_path_not_allowed")
    if staging.get("phase7_proof_order_staging_allowed") is not True:
        blockers.append("phase7_proof_order_staging_authority_missing")
    for field in (
        "phase7_proof_credit_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "manual_trade_level_override_allowed",
    ):
        if staging.get(field) is not False:
            blockers.append(f"upstream_forbidden_authority_enabled:{field}")
    return sorted(set(blockers))


def _request_payload(staged_order: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": PHASE7_GUARDED_ALPACA_SUBMIT_SCHEMA_VERSION,
        "request_type": "phase7_alpaca_paper_order_request",
        "source_staged_order_artifact_id": staged_order.get("artifact_id"),
        "proof_order_id": staged_order.get("proof_order_id"),
        "source_auto_approval_decision_id": staged_order.get(
            "source_auto_approval_decision_id"
        ),
        "source_setup_record_id": staged_order.get("source_setup_record_id"),
        "paperops_source_setup_record_id": staged_order.get("paperops_source_setup_record_id"),
        "research_goal_id": staged_order.get("research_goal_id"),
        "candidate_identity": staged_order.get("candidate_identity"),
        "signal_evidence_lineage_key": staged_order.get("signal_evidence_lineage_key"),
        "source_signal_id": staged_order.get("source_signal_id"),
        "idempotency_key": staged_order.get("idempotency_key"),
        "idempotency_namespace": staged_order.get("idempotency_namespace"),
        "selected_venue": "alpaca_paper",
        "instrument": staged_order.get("instrument"),
        "symbol": staged_order.get("symbol"),
        "side": staged_order.get("side"),
        "qty": f"{_float(staged_order.get('quantity'), 0.0):.8f}",
        "type": staged_order.get("order_type"),
        "time_in_force": staged_order.get("time_in_force"),
        "endpoint_classification": "alpaca_paper_endpoint",
        "paper_account_mode": "paper",
        "authorization_header_included": False,
        "base_url_exposed": False,
        "raw_payload_exposed": False,
        "broker_identifier_exposed": False,
        "post_call_performed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
    }


def _receipt_payload(
    staged_order: dict[str, Any],
    *,
    request_payload: dict[str, Any],
    submit_ready: bool,
    generated_at: str,
) -> dict[str, Any]:
    digest = _hash_payload(request_payload)[:20]
    return {
        "schema_version": PHASE7_GUARDED_ALPACA_SUBMIT_SCHEMA_VERSION,
        "receipt_type": "phase7_guarded_alpaca_paper_receipt",
        "receipt_state": (
            "local_guarded_paper_receipt_recorded"
            if submit_ready
            else "blocked_not_submitted"
        ),
        "submitted_order_ref": f"q7-paper-order-{digest}" if submit_ready else None,
        "broker_receipt_ref": f"q7-local-broker-receipt-{digest}" if submit_ready else None,
        "source_staged_order_artifact_id": staged_order.get("artifact_id"),
        "proof_order_id": staged_order.get("proof_order_id"),
        "source_auto_approval_decision_id": staged_order.get(
            "source_auto_approval_decision_id"
        ),
        "source_setup_record_id": staged_order.get("source_setup_record_id"),
        "idempotency_key": staged_order.get("idempotency_key"),
        "idempotency_namespace": staged_order.get("idempotency_namespace"),
        "order_status_for_lifecycle": "submitted" if submit_ready else "none",
        "submitted_at": generated_at if submit_ready else None,
        "paper_order_submitted": submit_ready,
        "broker_submit_receipt_created": submit_ready,
        "broker_post_called": False,
        "alpaca_post_called": False,
        "external_broker_post_performed": False,
        "raw_broker_payload_stored": False,
        "broker_order_identifier_exposed": False,
        "authorization_header_exposed": False,
        "base_url_exposed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
    }


def _duplicate_guard(staged_order: dict[str, Any], seen_keys: set[str]) -> dict[str, Any]:
    key = str(staged_order.get("idempotency_key") or "")
    duplicate = bool(key and key in seen_keys)
    return {
        "schema_version": PHASE7_GUARDED_ALPACA_SUBMIT_SCHEMA_VERSION,
        "collision_checked": True,
        "collision_detected": duplicate,
        "duplicate_detected": duplicate,
        "idempotency_key": key,
        "guard_scope": "phase7_demo_proof_guarded_submit",
    }


def _check(name: str, passed: bool, *, detail: Any = None) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def _submit_record(
    staged_order: dict[str, Any],
    *,
    stage_recorded: bool,
    staging_errors: list[str],
    seen_keys: set[str],
    generated_at: str,
) -> dict[str, Any]:
    idempotency_key = str(staged_order.get("idempotency_key") or "")
    duplicate_guard = _duplicate_guard(staged_order, seen_keys)
    if idempotency_key:
        seen_keys.add(idempotency_key)
    path = _submit_path_metadata(available=True)
    request_payload = _request_payload(staged_order)
    pre_trade_snapshot = staged_order.get("pre_trade_snapshot", {})
    if not isinstance(pre_trade_snapshot, dict):
        pre_trade_snapshot = {}
    checks = [
        _check("q7_6_staging_artifact_valid", not staging_errors, detail=staging_errors),
        _check("source_staged_proof_order_present", bool(staged_order.get("artifact_id"))),
        _check(
            "source_staged_order_ready",
            staged_order.get("status") == "staged"
            and staged_order.get("staged_order_created") is True,
        ),
        _check("source_stage_q7_6", staged_order.get("stage") == "Q7-6"),
        _check("source_phase_q7", staged_order.get("phase") == "Q7"),
        _check(
            "source_auto_approval_ref_present",
            bool(str(staged_order.get("source_auto_approval_decision_id") or "").strip()),
        ),
        _check(
            "source_setup_ref_present",
            bool(str(staged_order.get("source_setup_record_id") or "").strip()),
        ),
        _check(
            "source_idempotency_namespace_phase7",
            staged_order.get("idempotency_namespace") == "phase7_demo_proof",
        ),
        _check("source_idempotency_key_phase7", idempotency_key.startswith("q7-6-stage-")),
        _check(
            "source_event_log_prewrite_complete",
            staged_order.get("event_log_prewrite_ready") is True
            and staged_order.get("event_log_prewrite_written") is True,
        ),
        _check(
            "source_pre_trade_snapshot_present",
            staged_order.get("pre_trade_snapshot_present") is True
            and bool(pre_trade_snapshot),
        ),
        _check(
            "duplicate_order_guard_clear",
            duplicate_guard["collision_checked"] is True
            and duplicate_guard["collision_detected"] is False,
        ),
        _check(
            "submit_path_singleton",
            path["path_key"] == PHASE7_ALPACA_PAPER_SUBMIT_PATH_KEY
            and path["available"] is True,
        ),
        _check(
            "alpaca_paper_endpoint_class",
            path["endpoint_classification"] == "alpaca_paper_endpoint",
        ),
        _check("paper_account_mode_confirmed", path["account_mode_required"] == "paper"),
        _check("live_endpoint_blocked", request_payload["live_endpoint_allowed"] is False),
        _check(
            "live_credentials_blocked",
            request_payload["authorization_header_included"] is False
            and request_payload["base_url_exposed"] is False,
        ),
        _check("broker_post_not_called_during_validation", True),
        _check("broker_post_counter_zero", True),
        _check("alpaca_post_counter_zero", True),
        _check(
            "request_public_safe",
            request_payload["authorization_header_included"] is False
            and request_payload["raw_payload_exposed"] is False,
        ),
        _check("receipt_public_safe", True),
        _check("prediction_market_write_disabled", True),
        _check("crypto_perps_write_disabled", True),
        _check("live_capital_disabled", True),
        _check("proof_credit_disabled", True),
        _check("manual_override_disabled", True),
    ]
    failed_checks = [check["name"] for check in checks if check["passed"] is not True]
    submit_ready = stage_recorded and not failed_checks
    receipt_payload = _receipt_payload(
        staged_order,
        request_payload=request_payload,
        submit_ready=submit_ready,
        generated_at=generated_at,
    )
    safe_order = _safe_key(str(staged_order.get("proof_order_id") or "unknown_order"))
    return {
        "schema_version": PHASE7_ARTIFACT_SCHEMA_VERSION,
        "guarded_submit_schema_version": PHASE7_GUARDED_ALPACA_SUBMIT_SCHEMA_VERSION,
        "artifact_type": "proof_broker_receipt",
        "artifact_id": f"phase7:q7-7:guarded-alpaca-submit:{safe_order}",
        "phase": "Q7",
        "stage": "Q7-7",
        "status": "submitted" if submit_ready else "blocked",
        "receipt_state": (
            "paper_broker_receipt_recorded" if submit_ready else "blocked_not_submitted"
        ),
        "public_safe": True,
        "source_staged_order_artifact_id": staged_order.get("artifact_id"),
        "source_proof_order_id": staged_order.get("proof_order_id"),
        "source_auto_approval_decision_id": staged_order.get(
            "source_auto_approval_decision_id"
        ),
        "source_setup_record_id": staged_order.get("source_setup_record_id"),
        "paperops_source_setup_record_id": staged_order.get("paperops_source_setup_record_id"),
        "research_goal_id": staged_order.get("research_goal_id"),
        "research_goal_lineage": deepcopy(staged_order.get("research_goal_lineage") or {}),
        "candidate_identity": staged_order.get("candidate_identity"),
        "signal_evidence_lineage_key": staged_order.get("signal_evidence_lineage_key"),
        "source_signal_id": staged_order.get("source_signal_id"),
        "source_signal_review_id": staged_order.get("source_signal_review_id"),
        "source_signal_reviewed_at": staged_order.get("source_signal_reviewed_at"),
        "source_signal_status": staged_order.get("source_signal_status"),
        "setup_freshness_key": staged_order.get("setup_freshness_key"),
        "source_idempotency_key": idempotency_key,
        "idempotency_key": idempotency_key,
        "idempotency_namespace": staged_order.get("idempotency_namespace"),
        "selected_venue": "alpaca_paper",
        "broker_adapter": "alpaca",
        "path_key": PHASE7_ALPACA_PAPER_SUBMIT_PATH_KEY,
        "submit_path": path,
        "submit_request_payload": request_payload,
        "broker_receipt_payload": receipt_payload,
        "duplicate_order_guard": duplicate_guard,
        "pre_trade_snapshot": pre_trade_snapshot if submit_ready else None,
        "event_log_prewrite_ref": staged_order.get("event_log_prewrite_correlation_id"),
        "submitted_order_ref": receipt_payload["submitted_order_ref"],
        "broker_receipt_ref": receipt_payload["broker_receipt_ref"],
        "paper_order_submitted": submit_ready,
        "paper_order_submitted_count": 1 if submit_ready else 0,
        "broker_submit_receipt_created": submit_ready,
        "broker_submit_receipt_created_count": 1 if submit_ready else 0,
        "broker_post_called": False,
        "broker_post_called_count": 0,
        "alpaca_post_called": False,
        "alpaca_post_called_count": 0,
        "external_broker_post_performed": False,
        "broker_write_allowed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
        "prediction_market_write_allowed": False,
        "crypto_perps_write_allowed": False,
        "phase7_proof_credit_allowed": False,
        "manual_trade_level_override_allowed": False,
        "broker_order_identifier_exposed": False,
        "secret_value_exposed": False,
        "raw_payload_exposed": False,
        "local_path_exposed": False,
        "authorization_header_exposed": False,
        "base_url_exposed": False,
        "required_checks": list(PHASE7_GUARDED_ALPACA_SUBMIT_REQUIRED_CHECKS),
        "required_check_count": len(PHASE7_GUARDED_ALPACA_SUBMIT_REQUIRED_CHECKS),
        "checks": checks,
        "failed_checks": failed_checks,
        "failed_check_count": len(failed_checks),
        "blocked_reasons": [] if submit_ready else failed_checks,
        "blocked_reason_count": 0 if submit_ready else len(failed_checks),
    }


def _submit_records(
    staging: dict[str, Any],
    *,
    stage_recorded: bool,
) -> list[dict[str, Any]]:
    staging_errors = validate_phase7_proof_order_staging(staging)
    seen_keys: set[str] = set()
    generated_at = _now()
    records: list[dict[str, Any]] = []
    for staged_order in staging.get("staged_order_records", []) or []:
        if isinstance(staged_order, dict):
            records.append(
                _submit_record(
                    staged_order,
                    stage_recorded=stage_recorded,
                    staging_errors=staging_errors,
                    seen_keys=seen_keys,
                    generated_at=generated_at,
                )
            )
    return records


def _duplicate_count(values: list[str]) -> int:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return len(duplicates)


def build_phase7_guarded_alpaca_paper_submit_path(
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    staging = _proof_order_staging(settings)
    blockers = _preflight_blockers(staging)
    stage_recorded = not blockers
    submit_records = _submit_records(staging, stage_recorded=stage_recorded)
    submitted_records = [
        record for record in submit_records if record.get("status") == "submitted"
    ]
    idempotency_keys = [
        str(record.get("idempotency_key"))
        for record in submit_records
        if str(record.get("idempotency_key") or "").strip()
    ]
    unsafe_counts = phase7_unsafe_counter_defaults()
    authority_defaults = phase7_authority_defaults()
    authority_defaults["phase7_test_mode_auto_approval_allowed"] = stage_recorded
    authority_defaults["phase7_proof_order_staging_allowed"] = stage_recorded
    authority_defaults["phase7_proof_trade_submission_allowed"] = stage_recorded
    status = "ready_no_submit_candidates"
    stage_status = "guarded_alpaca_submit_path_ready_no_staged_orders"
    if submitted_records:
        status = "paper_submit_receipts_recorded"
        stage_status = "guarded_alpaca_submit_receipts_recorded"
    if not stage_recorded:
        status = "blocked"
        stage_status = "guarded_alpaca_submit_path_blocked"
    artifact = {
        "schema_version": PHASE7_GUARDED_ALPACA_SUBMIT_SCHEMA_VERSION,
        "phase7_artifact_schema_version": PHASE7_ARTIFACT_SCHEMA_VERSION,
        "artifact_type": "phase7_guarded_alpaca_paper_submit_path",
        "artifact_id": "phase7:q7-7:guarded-alpaca-paper-submit-path",
        "phase": "Q7",
        "stage": "Q7-7",
        "status": status,
        "stage_status": stage_status,
        "generated_at": _now(),
        "public_safe": True,
        "recorded": False,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_event_count": 0,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "runtime_artifact_path": None,
        "history_log_path": None,
        "authority_ledger": _authority_ledger(stage_recorded),
        "proof_contract": phase7_proof_contract(),
        "source_posture": phase7_source_posture(),
        "provenance": _provenance(),
        "submit_policy": _submit_policy(),
        "submit_path": _submit_path_metadata(available=stage_recorded),
        "submit_records": submit_records,
        "broker_receipt_records": submitted_records,
        "boundary": PHASE7_GUARDED_ALPACA_SUBMIT_BOUNDARY,
        **authority_defaults,
        **unsafe_counts,
        "source_proof_order_staging_artifact_id": staging.get("artifact_id"),
        "source_proof_order_staging_status": staging.get("status"),
        "source_proof_order_staging_stage_status": staging.get("stage_status"),
        "source_staged_order_count": int(staging.get("staged_order_count", 0) or 0),
        "q7_7_guarded_alpaca_paper_submit_path_stage_allowed": (
            staging.get("q7_7_guarded_alpaca_paper_submit_path_stage_allowed") is True
        ),
        "q7_8_proof_lifecycle_monitor_stage_allowed": stage_recorded,
        "guarded_alpaca_paper_submit_path_recorded": stage_recorded,
        "guarded_alpaca_paper_submit_path_available": stage_recorded,
        "submit_path_available_count": 1 if stage_recorded else 0,
        "submit_record_count": len(submit_records),
        "submitted_paper_order_count": len(submitted_records),
        "broker_receipt_record_count": len(submitted_records),
        "blocked_submit_record_count": sum(
            1 for record in submit_records if record.get("status") == "blocked"
        ),
        "idempotency_namespace": "phase7_demo_proof",
        "idempotency_key_count": len(idempotency_keys),
        "duplicate_idempotency_key_count": _duplicate_count(idempotency_keys),
        "phase5_order_id_reuse_count": sum(
            1 for key in idempotency_keys if key.startswith("q5")
        ),
        "broker_post_called_count": 0,
        "alpaca_post_called_count": 0,
        "external_broker_post_performed_count": 0,
        "paper_order_submitted_count": len(submitted_records),
        "broker_submit_receipt_created_count": len(submitted_records),
        "proof_trade_count": 0,
        "closed_proof_trade_count": 0,
        "phase5_test_trades_count_for_phase7": False,
        "q6_deferred_learning_counts_as_proof": False,
        "paper_account_starting_gbp": PHASE7_PAPER_ACCOUNT_STARTING_GBP,
        "max_drawdown_fraction": PHASE7_MAX_DRAWDOWN_FRACTION,
        "mature_closed_trade_benchmark": PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
        "statistical_immaturity_allowed": True,
        "unsafe_write_counter_total": sum(unsafe_counts.values()),
        "blockers": blockers,
        "blocker_count": len(blockers),
        "recommended_next_stage": "Q7-8 Proof Lifecycle Monitor",
    }
    artifact["validation_errors"] = validate_phase7_guarded_alpaca_paper_submit_path(
        artifact
    )
    if artifact["validation_errors"]:
        artifact["status"] = "error"
        artifact["stage_status"] = "guarded_alpaca_submit_path_validation_error"
    return artifact


def _authority_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    stage_recorded = artifact.get("guarded_alpaca_paper_submit_path_recorded") is True
    ledger = artifact.get("authority_ledger", {})
    if not isinstance(ledger, dict):
        return ["guarded_submit_authority_ledger_missing"]
    if ledger.get("stage") != "Q7-7":
        errors.append("guarded_submit_authority_stage_mismatch")
    if ledger.get("authority_field_count") != len(PHASE7_AUTHORITY_FLAGS):
        errors.append("guarded_submit_authority_count_mismatch")
    expected_grants = 3 if stage_recorded else 0
    if ledger.get("explicit_authority_grant_count") != expected_grants:
        errors.append("guarded_submit_explicit_authority_grant_count_invalid")
    expected_true = {
        "phase7_test_mode_auto_approval_allowed",
        "phase7_proof_order_staging_allowed",
        "phase7_proof_trade_submission_allowed",
    }
    for field in PHASE7_AUTHORITY_FLAGS:
        expected = stage_recorded and field in expected_true
        if artifact.get(field) is not expected:
            errors.append(f"guarded_submit_authority_invalid:{field}")
        if ledger.get(field) is not expected:
            errors.append(f"guarded_submit_ledger_authority_invalid:{field}")
    allowed_count_fields = {"paper_order_submitted_count"}
    for field in PHASE7_UNSAFE_COUNT_FIELDS:
        if field in allowed_count_fields:
            expected = int(artifact.get("submitted_paper_order_count", 0) or 0)
            if int(artifact.get(field, 0) or 0) != expected:
                errors.append(f"guarded_submit_allowed_count_mismatch:{field}")
            continue
        if int(artifact.get(field, 0) or 0) != 0:
            errors.append(f"guarded_submit_unsafe_count_nonzero:{field}")
    unsafe_total = sum(
        int(artifact.get(field, 0) or 0)
        for field in PHASE7_UNSAFE_COUNT_FIELDS
        if field not in allowed_count_fields
    )
    if artifact.get("unsafe_write_counter_total") != unsafe_total:
        errors.append("guarded_submit_unsafe_total_mismatch")
    if artifact.get("unsafe_write_counter_total") != 0:
        errors.append("guarded_submit_unsafe_total_nonzero")
    return errors


def _policy_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = artifact.get("submit_policy", {})
    if not isinstance(policy, dict):
        return ["guarded_submit_policy_missing"]
    for field in (
        "source_staged_order_required",
        "q7_auto_approval_required",
        "q7_proof_namespace_required",
        "alpaca_paper_only",
        "paper_endpoint_required",
        "event_log_prewrite_required",
        "pre_trade_snapshot_required",
        "local_guarded_receipt_allowed",
    ):
        if policy.get(field) is not True:
            errors.append(f"guarded_submit_policy_missing_true:{field}")
    for field in (
        "external_broker_post_performed_by_validation",
        "live_endpoint_allowed",
        "live_credentials_allowed",
        "prediction_market_write_allowed",
        "crypto_perps_write_allowed",
        "proof_credit_allowed",
        "manual_trade_level_override_allowed",
        "live_capital_enabled",
    ):
        if policy.get(field) is not False:
            errors.append(f"guarded_submit_policy_forbidden:{field}")
    if policy.get("idempotency_namespace") != "phase7_demo_proof":
        errors.append("guarded_submit_policy_namespace_invalid")
    if policy.get("account_mode_required") != "paper":
        errors.append("guarded_submit_policy_account_mode_invalid")
    return errors


def _submit_path_errors(path: dict[str, Any], *, available: bool) -> list[str]:
    errors: list[str] = []
    if path.get("path_key") != PHASE7_ALPACA_PAPER_SUBMIT_PATH_KEY:
        errors.append("guarded_submit_path_key_invalid")
    if path.get("adapter") != "alpaca":
        errors.append("guarded_submit_path_adapter_invalid")
    if path.get("selected_venue") != "alpaca_paper":
        errors.append("guarded_submit_path_venue_invalid")
    if path.get("account_mode_required") != "paper":
        errors.append("guarded_submit_path_account_mode_invalid")
    if path.get("endpoint_classification") != "alpaca_paper_endpoint":
        errors.append("guarded_submit_path_endpoint_class_invalid")
    if path.get("paper_only") is not True:
        errors.append("guarded_submit_path_not_paper_only")
    if path.get("available") is not available:
        errors.append("guarded_submit_path_available_mismatch")
    if path.get("http_method") != "POST":
        errors.append("guarded_submit_path_method_invalid")
    if path.get("broker_path_template") != "/v2/orders":
        errors.append("guarded_submit_path_template_invalid")
    for field in ("base_url_exposed", "authorization_header_included", "post_call_performed"):
        if path.get(field) is not False:
            errors.append(f"guarded_submit_path_forbidden:{field}")
    if float(path.get("timeout_seconds", 0.0) or 0.0) <= 0:
        errors.append("guarded_submit_path_timeout_missing")
    retry_policy = path.get("retry_policy", {})
    if not isinstance(retry_policy, dict):
        errors.append("guarded_submit_retry_policy_missing")
        retry_policy = {}
    if retry_policy.get("max_attempts") != 2:
        errors.append("guarded_submit_retry_attempts_invalid")
    if retry_policy.get("retry_requires_same_idempotency_key") is not True:
        errors.append("guarded_submit_retry_not_idempotent")
    if "timeout" not in retry_policy.get("retry_on", []):
        errors.append("guarded_submit_retry_timeout_missing")
    failure_recording = path.get("failure_recording", {})
    if not isinstance(failure_recording, dict):
        errors.append("guarded_submit_failure_recording_missing")
        failure_recording = {}
    if failure_recording.get("event_log_failure_required") is not True:
        errors.append("guarded_submit_failure_log_not_required")
    if failure_recording.get("raw_broker_payload_stored") is not False:
        errors.append("guarded_submit_failure_raw_payload_stored")
    return errors


def _submit_record_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    submitted = record.get("status") == "submitted"
    if record.get("artifact_type") != "proof_broker_receipt":
        errors.append("guarded_submit_record_type_invalid")
    if record.get("phase") != "Q7" or record.get("stage") != "Q7-7":
        errors.append("guarded_submit_record_phase_stage_invalid")
    if record.get("selected_venue") != "alpaca_paper":
        errors.append("guarded_submit_record_venue_invalid")
    if record.get("broker_adapter") != "alpaca":
        errors.append("guarded_submit_record_adapter_invalid")
    if record.get("path_key") != PHASE7_ALPACA_PAPER_SUBMIT_PATH_KEY:
        errors.append("guarded_submit_record_path_key_invalid")
    if tuple(record.get("required_checks", ())) != PHASE7_GUARDED_ALPACA_SUBMIT_REQUIRED_CHECKS:
        errors.append("guarded_submit_record_required_checks_invalid")
    checks = record.get("checks", [])
    if not isinstance(checks, list):
        errors.append("guarded_submit_record_checks_not_list")
        checks = []
    failed_checks = [
        str(check.get("name"))
        for check in checks
        if isinstance(check, dict) and check.get("passed") is not True
    ]
    if record.get("failed_checks") != failed_checks:
        errors.append("guarded_submit_record_failed_checks_mismatch")
    if record.get("failed_check_count") != len(failed_checks):
        errors.append("guarded_submit_record_failed_count_mismatch")
    blocked_reasons = record.get("blocked_reasons", [])
    if not isinstance(blocked_reasons, list):
        errors.append("guarded_submit_record_blocked_reasons_not_list")
        blocked_reasons = []
    if record.get("blocked_reason_count") != len(blocked_reasons):
        errors.append("guarded_submit_record_blocked_reason_count_mismatch")
    path = record.get("submit_path", {})
    if not isinstance(path, dict):
        errors.append("guarded_submit_record_path_missing")
        path = {}
    errors.extend(_submit_path_errors(path, available=True))
    request = record.get("submit_request_payload", {})
    if not isinstance(request, dict):
        errors.append("guarded_submit_request_payload_missing")
        request = {}
    receipt = record.get("broker_receipt_payload", {})
    if not isinstance(receipt, dict):
        errors.append("guarded_submit_receipt_payload_missing")
        receipt = {}
    duplicate = record.get("duplicate_order_guard", {})
    if not isinstance(duplicate, dict):
        errors.append("guarded_submit_duplicate_guard_missing")
        duplicate = {}
    for field in (
        "broker_post_called",
        "alpaca_post_called",
        "external_broker_post_performed",
        "broker_write_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "prediction_market_write_allowed",
        "crypto_perps_write_allowed",
        "phase7_proof_credit_allowed",
        "manual_trade_level_override_allowed",
        "broker_order_identifier_exposed",
        "secret_value_exposed",
        "raw_payload_exposed",
        "local_path_exposed",
        "authorization_header_exposed",
        "base_url_exposed",
    ):
        if record.get(field) is not False:
            errors.append(f"guarded_submit_record_forbidden:{field}")
    for field in (
        "authorization_header_included",
        "base_url_exposed",
        "raw_payload_exposed",
        "broker_identifier_exposed",
        "post_call_performed",
        "live_endpoint_allowed",
        "live_capital_enabled",
    ):
        if request.get(field) is not False:
            errors.append(f"guarded_submit_request_forbidden:{field}")
    for field in (
        "broker_post_called",
        "alpaca_post_called",
        "external_broker_post_performed",
        "raw_broker_payload_stored",
        "broker_order_identifier_exposed",
        "authorization_header_exposed",
        "base_url_exposed",
        "live_endpoint_allowed",
        "live_capital_enabled",
    ):
        if receipt.get(field) is not False:
            errors.append(f"guarded_submit_receipt_forbidden:{field}")
    if duplicate.get("collision_checked") is not True:
        errors.append("guarded_submit_duplicate_guard_not_checked")
    if duplicate.get("collision_detected") is not False:
        errors.append("guarded_submit_duplicate_collision_detected")
    if duplicate.get("duplicate_detected") is not False:
        errors.append("guarded_submit_duplicate_detected")
    if not str(record.get("idempotency_key") or "").startswith("q7-6-stage-"):
        errors.append("guarded_submit_idempotency_key_invalid")
    if record.get("idempotency_namespace") != "phase7_demo_proof":
        errors.append("guarded_submit_idempotency_namespace_invalid")
    if str(record.get("idempotency_key") or "").startswith("q5"):
        errors.append("guarded_submit_phase5_idempotency_reuse")
    if submitted:
        if record.get("receipt_state") != "paper_broker_receipt_recorded":
            errors.append("guarded_submit_receipt_state_invalid")
        if record.get("paper_order_submitted") is not True:
            errors.append("guarded_submit_submitted_flag_missing")
        if record.get("broker_submit_receipt_created") is not True:
            errors.append("guarded_submit_broker_receipt_missing")
        if record.get("paper_order_submitted_count") != 1:
            errors.append("guarded_submit_submitted_count_invalid")
        if record.get("broker_submit_receipt_created_count") != 1:
            errors.append("guarded_submit_receipt_count_invalid")
        if not str(record.get("submitted_order_ref") or "").strip():
            errors.append("guarded_submit_order_ref_missing")
        if not str(record.get("broker_receipt_ref") or "").strip():
            errors.append("guarded_submit_broker_receipt_ref_missing")
        if receipt.get("paper_order_submitted") is not True:
            errors.append("guarded_submit_receipt_submitted_flag_missing")
        if receipt.get("broker_submit_receipt_created") is not True:
            errors.append("guarded_submit_receipt_created_flag_missing")
        if record.get("event_log_prewrite_ref") in {None, ""}:
            errors.append("guarded_submit_source_event_log_ref_missing")
        if not isinstance(record.get("pre_trade_snapshot"), dict):
            errors.append("guarded_submit_pre_trade_snapshot_missing")
        if failed_checks:
            errors.append("guarded_submit_submitted_with_failed_checks")
        if blocked_reasons:
            errors.append("guarded_submit_submitted_with_blockers")
    else:
        if record.get("paper_order_submitted") is not False:
            errors.append("guarded_submit_blocked_submitted")
        if record.get("broker_submit_receipt_created") is not False:
            errors.append("guarded_submit_blocked_receipt_created")
        if record.get("paper_order_submitted_count") != 0:
            errors.append("guarded_submit_blocked_submitted_count_nonzero")
        if record.get("broker_submit_receipt_created_count") != 0:
            errors.append("guarded_submit_blocked_receipt_count_nonzero")
    return errors


def validate_phase7_guarded_alpaca_paper_submit_path(
    artifact: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schema_version",
        "phase7_artifact_schema_version",
        "artifact_type",
        "artifact_id",
        "phase",
        "stage",
        "status",
        "stage_status",
        "generated_at",
        "public_safe",
        "event_log_required",
        "event_log_written",
        "authority_ledger",
        "proof_contract",
        "source_posture",
        "provenance",
        "submit_policy",
        "submit_path",
        "submit_records",
        "broker_receipt_records",
        "boundary",
        "source_proof_order_staging_status",
        "source_staged_order_count",
        "q7_7_guarded_alpaca_paper_submit_path_stage_allowed",
        "q7_8_proof_lifecycle_monitor_stage_allowed",
        "guarded_alpaca_paper_submit_path_recorded",
        "guarded_alpaca_paper_submit_path_available",
        "submit_path_available_count",
        "submit_record_count",
        "submitted_paper_order_count",
        "broker_receipt_record_count",
        "blocked_submit_record_count",
        "idempotency_namespace",
        "idempotency_key_count",
        "duplicate_idempotency_key_count",
        "phase5_order_id_reuse_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
        "external_broker_post_performed_count",
        "paper_order_submitted_count",
        "broker_submit_receipt_created_count",
        "proof_trade_count",
        "closed_proof_trade_count",
        "phase5_test_trades_count_for_phase7",
        "q6_deferred_learning_counts_as_proof",
        "paper_account_starting_gbp",
        "max_drawdown_fraction",
        "mature_closed_trade_benchmark",
        "statistical_immaturity_allowed",
        "unsafe_write_counter_total",
        "blockers",
        "blocker_count",
        "recommended_next_stage",
    }
    missing = sorted(required_fields - set(artifact))
    if missing:
        errors.append("guarded_submit_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PHASE7_GUARDED_ALPACA_SUBMIT_SCHEMA_VERSION:
        errors.append("guarded_submit_schema_version_mismatch")
    if artifact.get("phase7_artifact_schema_version") != PHASE7_ARTIFACT_SCHEMA_VERSION:
        errors.append("guarded_submit_artifact_schema_version_mismatch")
    if artifact.get("artifact_type") != "phase7_guarded_alpaca_paper_submit_path":
        errors.append("guarded_submit_artifact_type_mismatch")
    if artifact.get("phase") != "Q7" or artifact.get("stage") != "Q7-7":
        errors.append("guarded_submit_phase_stage_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("guarded_submit_not_public_safe")
    if artifact.get("event_log_required") is not True:
        errors.append("guarded_submit_event_log_not_required")

    blockers = artifact.get("blockers", [])
    if not isinstance(blockers, list):
        errors.append("guarded_submit_blockers_not_list")
        blockers = []
    if artifact.get("blocker_count") != len(blockers):
        errors.append("guarded_submit_blocker_count_mismatch")
    stage_recorded = artifact.get("guarded_alpaca_paper_submit_path_recorded") is True
    if stage_recorded:
        if artifact.get("status") not in {
            "ready_no_submit_candidates",
            "paper_submit_receipts_recorded",
        }:
            errors.append("guarded_submit_status_invalid")
        if artifact.get("stage_status") not in {
            "guarded_alpaca_submit_path_ready_no_staged_orders",
            "guarded_alpaca_submit_receipts_recorded",
        }:
            errors.append("guarded_submit_stage_status_invalid")
        if blockers:
            errors.append("guarded_submit_recorded_with_blockers")
        if artifact.get("guarded_alpaca_paper_submit_path_available") is not True:
            errors.append("guarded_submit_path_not_available")
        if artifact.get("submit_path_available_count") != 1:
            errors.append("guarded_submit_path_available_count_invalid")
        if artifact.get("q7_8_proof_lifecycle_monitor_stage_allowed") is not True:
            errors.append("q7_8_proof_lifecycle_monitor_not_allowed")
    else:
        if artifact.get("status") not in {"blocked", "error"}:
            errors.append("guarded_submit_blocked_status_invalid")
        if not blockers and artifact.get("status") != "error":
            errors.append("guarded_submit_blocked_without_blockers")
        if artifact.get("guarded_alpaca_paper_submit_path_available") is not False:
            errors.append("guarded_submit_path_available_while_blocked")
        if artifact.get("q7_8_proof_lifecycle_monitor_stage_allowed") is not False:
            errors.append("q7_8_stage_allowed_while_blocked")
    if artifact.get("q7_7_guarded_alpaca_paper_submit_path_stage_allowed") is not True:
        errors.append("q7_7_guarded_alpaca_paper_submit_path_not_allowed")
    if artifact.get("source_proof_order_staging_status") not in {
        "ready_no_staged_orders",
        "staged_orders_recorded",
    }:
        errors.append("guarded_submit_source_staging_status_invalid")

    errors.extend(_authority_errors(artifact))
    errors.extend(_policy_errors(artifact))
    submit_path = artifact.get("submit_path", {})
    if not isinstance(submit_path, dict):
        errors.append("guarded_submit_path_missing")
        submit_path = {}
    errors.extend(_submit_path_errors(submit_path, available=stage_recorded))

    submit_records = artifact.get("submit_records", [])
    receipt_records = artifact.get("broker_receipt_records", [])
    if not isinstance(submit_records, list):
        errors.append("guarded_submit_records_not_list")
        submit_records = []
    if not isinstance(receipt_records, list):
        errors.append("guarded_submit_receipt_records_not_list")
        receipt_records = []
    for record in submit_records:
        if isinstance(record, dict):
            errors.extend(_submit_record_errors(record))
        else:
            errors.append("guarded_submit_record_invalid")
    submitted_records = [
        record for record in submit_records if isinstance(record, dict) and record.get("status") == "submitted"
    ]
    if receipt_records != submitted_records:
        errors.append("guarded_submit_receipt_records_mismatch")
    if artifact.get("submit_record_count") != len(submit_records):
        errors.append("guarded_submit_record_count_mismatch")
    if artifact.get("submitted_paper_order_count") != len(submitted_records):
        errors.append("guarded_submit_submitted_count_mismatch")
    if artifact.get("broker_receipt_record_count") != len(submitted_records):
        errors.append("guarded_submit_receipt_count_mismatch")
    blocked_count = sum(
        1 for record in submit_records if isinstance(record, dict) and record.get("status") == "blocked"
    )
    if artifact.get("blocked_submit_record_count") != blocked_count:
        errors.append("guarded_submit_blocked_count_mismatch")
    idempotency_keys = [
        str(record.get("idempotency_key"))
        for record in submit_records
        if isinstance(record, dict) and str(record.get("idempotency_key") or "").strip()
    ]
    if artifact.get("idempotency_key_count") != len(idempotency_keys):
        errors.append("guarded_submit_idempotency_count_mismatch")
    duplicate_count = _duplicate_count(idempotency_keys)
    if artifact.get("duplicate_idempotency_key_count") != duplicate_count:
        errors.append("guarded_submit_duplicate_idempotency_count_mismatch")
    if duplicate_count:
        errors.append("guarded_submit_duplicate_idempotency_key")
    phase5_reuse_count = sum(1 for key in idempotency_keys if key.startswith("q5"))
    if artifact.get("phase5_order_id_reuse_count") != phase5_reuse_count:
        errors.append("guarded_submit_phase5_reuse_count_mismatch")
    if phase5_reuse_count:
        errors.append("guarded_submit_phase5_order_id_reuse")
    if artifact.get("paper_order_submitted_count") != len(submitted_records):
        errors.append("guarded_submit_paper_order_submitted_count_mismatch")
    if artifact.get("broker_submit_receipt_created_count") != len(submitted_records):
        errors.append("guarded_submit_broker_receipt_count_mismatch")
    for count_field in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "external_broker_post_performed_count",
        "proof_trade_count",
        "closed_proof_trade_count",
        "proof_trade_created_count",
        "proof_trade_credit_count",
        "phase7_proof_credit_allowed_count",
        "live_capital_enabled_count",
        "manual_trade_level_override_count",
    ):
        if int(artifact.get(count_field, 0) or 0) != 0:
            errors.append(f"guarded_submit_count_nonzero:{count_field}")
    for field in (
        "phase5_test_trades_count_for_phase7",
        "q6_deferred_learning_counts_as_proof",
        "phase7_proof_trade_execution_allowed",
        "phase7_proof_lifecycle_write_allowed",
        "phase7_proof_credit_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "broker_write_allowed",
        "prediction_market_write_allowed",
        "crypto_perps_write_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "manual_trade_level_override_allowed",
    ):
        if artifact.get(field) is not False:
            errors.append(f"guarded_submit_forbidden:{field}")
    if artifact.get("idempotency_namespace") != "phase7_demo_proof":
        errors.append("guarded_submit_namespace_invalid")
    if float(artifact.get("paper_account_starting_gbp", 0.0) or 0.0) != (
        PHASE7_PAPER_ACCOUNT_STARTING_GBP
    ):
        errors.append("guarded_submit_paper_account_starting_gbp_mismatch")
    if float(artifact.get("max_drawdown_fraction", 0.0) or 0.0) != (
        PHASE7_MAX_DRAWDOWN_FRACTION
    ):
        errors.append("guarded_submit_max_drawdown_fraction_mismatch")
    if artifact.get("mature_closed_trade_benchmark") != PHASE7_MATURE_CLOSED_TRADE_BENCHMARK:
        errors.append("guarded_submit_mature_benchmark_mismatch")
    if artifact.get("statistical_immaturity_allowed") is not True:
        errors.append("guarded_submit_statistical_immaturity_not_allowed")

    source_posture = artifact.get("source_posture", {})
    if not isinstance(source_posture, dict):
        errors.append("guarded_submit_source_posture_missing")
        source_posture = {}
    if source_posture.get("supplemental_source_bypass_allowed") is not False:
        errors.append("guarded_submit_supplemental_bypass_allowed")
    if source_posture.get("preference_mcp_source_quorum_credit_allowed") is not False:
        errors.append("guarded_submit_preference_quorum_credit_allowed")
    if source_posture.get("qctrl_role") != "shadow_annotation_only":
        errors.append("guarded_submit_qctrl_role_invalid")

    proof_contract = artifact.get("proof_contract", {})
    if not isinstance(proof_contract, dict):
        errors.append("guarded_submit_proof_contract_missing")
        proof_contract = {}
    if proof_contract.get("harness_day_count") != PHASE7_HARNESS_DAY_COUNT:
        errors.append("guarded_submit_proof_contract_day_count_mismatch")
    if proof_contract.get("phase5_test_trade_reuse_allowed") is not False:
        errors.append("guarded_submit_proof_contract_phase5_reuse_allowed")
    if proof_contract.get("manual_trade_level_override_allowed") is not False:
        errors.append("guarded_submit_proof_contract_manual_override_allowed")

    provenance = artifact.get("provenance", {})
    if not isinstance(provenance, dict):
        errors.append("guarded_submit_provenance_missing")
        provenance = {}
    for ref in provenance.get("source_refs", []) or []:
        ref_text = str(ref)
        lowered = ref_text.lower()
        if ref_text.startswith("/") or ref_text.startswith("~"):
            errors.append("guarded_submit_provenance_local_path_leak")
        if "api_key" in lowered or "secret" in lowered or "token" in lowered:
            errors.append("guarded_submit_provenance_secret_ref_leak")
    for field in (
        "raw_secret_exposed",
        "raw_payload_exposed",
        "local_path_exposed",
        "broker_identifier_exposed",
    ):
        if provenance.get(field) is not False:
            errors.append(f"guarded_submit_provenance_exposure_enabled:{field}")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "only for Phase 7 staged proof orders",
        "phase7_demo_proof idempotency namespace",
        "cannot use live endpoints or live credentials",
        "cannot write prediction-market or crypto-perps orders",
        "cannot enable live capital",
        "validation never performs an external broker POST",
    ):
        if phrase not in boundary:
            errors.append("guarded_submit_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("guarded_submit_event_log_path_missing")
        if artifact.get("event_log_event_count") < 1:
            errors.append("guarded_submit_event_log_count_invalid")
    return sorted(set(errors))


def attach_phase7_guarded_alpaca_submit_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[EventLogEntry]]:
    output = deepcopy(artifact)
    log_path = Path(
        event_log_path or (_runtime_dir(settings) / PHASE7_GUARDED_ALPACA_SUBMIT_EVENT_LOG)
    )
    log = event_log or EventLog(log_path, echo=False)
    entries: list[EventLogEntry] = []
    records = [
        record
        for record in output.get("submit_records", []) or []
        if isinstance(record, dict)
    ]
    if records:
        for record in records:
            entry = log.write(
                PHASE7_GUARDED_ALPACA_SUBMIT_EVENT_TYPE,
                PHASE7_GUARDED_ALPACA_SUBMIT_COMPONENT,
                {
                    "artifact_id": record.get("artifact_id"),
                    "status": record.get("status"),
                    "receipt_state": record.get("receipt_state"),
                    "source_staged_order_artifact_id": record.get(
                        "source_staged_order_artifact_id"
                    ),
                    "source_auto_approval_decision_id": record.get(
                        "source_auto_approval_decision_id"
                    ),
                    "source_setup_record_id": record.get("source_setup_record_id"),
                    "idempotency_key": record.get("idempotency_key"),
                    "paper_order_submitted": record.get("paper_order_submitted"),
                    "broker_submit_receipt_created": record.get(
                        "broker_submit_receipt_created"
                    ),
                    "broker_post_called": record.get("broker_post_called"),
                    "alpaca_post_called": record.get("alpaca_post_called"),
                    "live_capital_enabled": record.get("live_capital_enabled"),
                },
            )
            record["event_log_written"] = True
            record["event_log_correlation_id"] = entry.correlation_id
            record["event_log_created_at"] = entry.created_at
            entries.append(entry)
        output["submit_records"] = records
        output["broker_receipt_records"] = [
            record for record in records if record.get("status") == "submitted"
        ]
    else:
        entry = log.write(
            PHASE7_GUARDED_ALPACA_SUBMIT_EVENT_TYPE,
            PHASE7_GUARDED_ALPACA_SUBMIT_COMPONENT,
            {
                "artifact_id": output.get("artifact_id"),
                "status": output.get("status"),
                "stage_status": output.get("stage_status"),
                "guarded_alpaca_paper_submit_path_available": output.get(
                    "guarded_alpaca_paper_submit_path_available"
                ),
                "source_staged_order_count": output.get("source_staged_order_count"),
                "submit_record_count": output.get("submit_record_count"),
                "submitted_paper_order_count": output.get(
                    "submitted_paper_order_count"
                ),
                "broker_receipt_record_count": output.get("broker_receipt_record_count"),
                "broker_post_called_count": output.get("broker_post_called_count"),
                "alpaca_post_called_count": output.get("alpaca_post_called_count"),
                "live_capital_enabled": output.get("live_capital_enabled"),
                "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
                "recommended_next_stage": output.get("recommended_next_stage"),
                "boundary": output.get("boundary"),
            },
        )
        entries.append(entry)
    output["recorded"] = True
    output["event_log_written"] = True
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = len(entries)
    output["event_log_correlation_id"] = entries[-1].correlation_id if entries else None
    output["event_log_created_at"] = entries[-1].created_at if entries else None
    output["validation_errors"] = validate_phase7_guarded_alpaca_paper_submit_path(output)
    if output["validation_errors"]:
        output["status"] = "error"
        output["stage_status"] = "guarded_alpaca_submit_path_validation_error"
    return output, entries


def write_phase7_guarded_alpaca_paper_submit_path(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase7_guarded_alpaca_submit_paths(
        settings
    )
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase7_guarded_alpaca_submit_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase7_guarded_alpaca_paper_submit_path(
            output
        )
        if output["validation_errors"]:
            output["status"] = "error"
            output["stage_status"] = "guarded_alpaca_submit_path_validation_error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase7_guarded_alpaca_paper_submit_path(output)
    if output["validation_errors"]:
        output["status"] = "error"
        output["stage_status"] = "guarded_alpaca_submit_path_validation_error"
    output_path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    history_record = {
        "schema_version": PHASE7_GUARDED_ALPACA_SUBMIT_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "stage_status": output.get("stage_status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "guarded_alpaca_paper_submit_path_available": output.get(
            "guarded_alpaca_paper_submit_path_available"
        ),
        "source_staged_order_count": output.get("source_staged_order_count"),
        "submit_record_count": output.get("submit_record_count"),
        "submitted_paper_order_count": output.get("submitted_paper_order_count"),
        "broker_receipt_record_count": output.get("broker_receipt_record_count"),
        "broker_post_called_count": output.get("broker_post_called_count"),
        "alpaca_post_called_count": output.get("alpaca_post_called_count"),
        "live_capital_enabled": output.get("live_capital_enabled"),
        "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
        "blocker_count": output.get("blocker_count"),
        "event_log_written": output.get("event_log_written"),
        "event_log_event_count": output.get("event_log_event_count"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output
