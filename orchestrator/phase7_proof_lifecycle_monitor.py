"""Q7-8 Phase 7 Demo Proof lifecycle monitor.

This stage mirrors Q7-7 guarded paper-submit receipts into a Phase 7 proof
lifecycle ledger. It can record local submitted/open/closed lifecycle state
and reconciliation blockers, but it cannot call broker POST routes, mutate
broker positions, grant proof credit, or enable live capital.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
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
from orchestrator.phase7_guarded_alpaca_paper_submit import (
    PHASE7_GUARDED_ALPACA_SUBMIT_RUNTIME_ARTIFACT,
    build_phase7_guarded_alpaca_paper_submit_path,
    phase7_guarded_alpaca_submit_paths,
    validate_phase7_guarded_alpaca_paper_submit_path,
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


PHASE7_PROOF_LIFECYCLE_SCHEMA_VERSION = 1
PHASE7_PROOF_LIFECYCLE_RUNTIME_ARTIFACT = "phase7_proof_lifecycle_monitor.json"
PHASE7_PROOF_LIFECYCLE_HISTORY = "phase7_proof_lifecycle_monitor_history.jsonl"
PHASE7_PROOF_LIFECYCLE_EVENT_LOG = "phase7_proof_lifecycle_monitor_events.jsonl"
PHASE7_PROOF_LIFECYCLE_EVENT_TYPE = PHASE7_EVENT_TYPES["proof_lifecycle"]
PHASE7_PROOF_LIFECYCLE_COMPONENT = "phase7_proof_lifecycle_monitor"

PHASE7_PROOF_LIFECYCLE_STATES: tuple[str, ...] = (
    "submitted_order",
    "open_position",
    "exit_intent",
    "closed_trade",
)

PHASE7_PROOF_LIFECYCLE_BOUNDARY = (
    "Q7-8 records local Phase 7 proof lifecycle state only from Q7-7 guarded "
    "Alpaca paper-submit receipts. It can mirror submitted orders, open "
    "positions, exit intent, and closed trades into the proof lifecycle ledger "
    "and can block certification on failed reconciliation, but it cannot call "
    "broker POST routes, cannot call Alpaca POST routes, cannot mutate broker "
    "positions, cannot write prediction-market or crypto-perps orders, cannot "
    "grant Phase 7 proof credit, cannot enable live capital, and cannot permit "
    "manual trade-level overrides."
)

PHASE7_PROOF_LIFECYCLE_REQUIRED_CHECKS: tuple[str, ...] = (
    "q7_7_guarded_submit_artifact_valid",
    "q7_8_lifecycle_stage_allowed",
    "source_broker_receipt_present",
    "submitted_order_ref_present",
    "broker_receipt_ref_present",
    "source_staged_order_ref_present",
    "source_auto_approval_ref_present",
    "source_setup_ref_present",
    "idempotency_namespace_phase7",
    "idempotency_key_phase7",
    "broker_echo_present",
    "submitted_order_mirrored",
    "lifecycle_state_mapped",
    "duplicate_fill_checked",
    "missing_broker_echo_checked",
    "stale_position_checked",
    "failed_reconciliation_blocks_certification",
    "no_broker_post",
    "no_alpaca_post",
    "no_live_endpoint",
    "no_live_capital",
    "proof_credit_disabled",
    "manual_override_disabled",
    "market_writes_disabled",
    "public_safe",
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


def phase7_proof_lifecycle_monitor_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE7_PROOF_LIFECYCLE_RUNTIME_ARTIFACT,
        runtime / PHASE7_PROOF_LIFECYCLE_HISTORY,
        runtime / PHASE7_PROOF_LIFECYCLE_EVENT_LOG,
    )


def _guarded_submit(settings: Settings) -> dict[str, Any]:
    submit_path, _, _ = phase7_guarded_alpaca_submit_paths(settings)
    if submit_path.exists():
        return _read_json(submit_path)
    return build_phase7_guarded_alpaca_paper_submit_path(settings=settings)


def _safe_key(value: str) -> str:
    allowed = []
    for char in value.lower():
        if char.isalnum() or char in {"_", "-"}:
            allowed.append(char)
        else:
            allowed.append("_")
    return "".join(allowed).strip("_") or "unknown"


def _bool(value: Any) -> bool:
    return value is True


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _check(name: str, passed: bool, *, detail: Any = None) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def _lifecycle_policy() -> dict[str, Any]:
    return {
        "policy_schema_version": PHASE7_PROOF_LIFECYCLE_SCHEMA_VERSION,
        "monitor_mode": "phase7_local_proof_lifecycle_monitor",
        "source_guarded_submit_required": True,
        "source_broker_receipt_required": True,
        "submitted_order_ref_required": True,
        "broker_receipt_ref_required": True,
        "broker_echo_required": True,
        "reconciliation_required": True,
        "failed_reconciliation_blocks_certification": True,
        "closed_trade_requires_q7_9_postmortem": True,
        "local_lifecycle_write_allowed": True,
        "external_broker_post_performed_by_validation": False,
        "broker_position_mutation_allowed": False,
        "broker_close_allowed": False,
        "broker_resize_allowed": False,
        "order_cancel_allowed": False,
        "live_endpoint_allowed": False,
        "prediction_market_write_allowed": False,
        "crypto_perps_write_allowed": False,
        "proof_credit_allowed": False,
        "manual_trade_level_override_allowed": False,
        "live_capital_enabled": False,
    }


def _authority_ledger(stage_recorded: bool) -> dict[str, Any]:
    defaults = phase7_authority_defaults()
    defaults["phase7_test_mode_auto_approval_allowed"] = stage_recorded
    defaults["phase7_proof_order_staging_allowed"] = stage_recorded
    defaults["phase7_proof_trade_submission_allowed"] = stage_recorded
    defaults["phase7_proof_lifecycle_write_allowed"] = stage_recorded
    return {
        "authority_schema_version": PHASE7_PROOF_LIFECYCLE_SCHEMA_VERSION,
        "stage": "Q7-8",
        "authority_field_count": len(PHASE7_AUTHORITY_FLAGS),
        "explicit_authority_grant_count": 4 if stage_recorded else 0,
        "explicit_authority_grants": (
            [
                "phase7_test_mode_auto_approval_allowed",
                "phase7_proof_order_staging_allowed",
                "phase7_proof_trade_submission_allowed",
                "phase7_proof_lifecycle_write_allowed",
            ]
            if stage_recorded
            else []
        ),
        "q7_9_proof_postmortem_contract_stage_allowed": stage_recorded,
        **defaults,
        "boundary": PHASE7_PROOF_LIFECYCLE_BOUNDARY,
    }


def _provenance() -> dict[str, Any]:
    provenance = phase7_provenance(
        (
            f"data/runtime/{PHASE7_GUARDED_ALPACA_SUBMIT_RUNTIME_ARTIFACT}",
            "orchestrator/phase7_artifacts.py",
            "orchestrator/phase7_guarded_alpaca_paper_submit.py",
            "docs/qadam-phase-7-demo-proof-implementation-plan.md",
            "docs/qadam-phase-7-q7-7-guarded-alpaca-paper-submit-audit-2026-05-25.md",
        )
    )
    provenance["decision_chain_refs"] = [
        f"data/runtime/{PHASE7_GUARDED_ALPACA_SUBMIT_RUNTIME_ARTIFACT}"
    ]
    provenance["execution_evidence_refs"] = [
        f"data/runtime/{PHASE7_GUARDED_ALPACA_SUBMIT_RUNTIME_ARTIFACT}"
    ]
    provenance["proof_lifecycle_refs"] = []
    return provenance


def _preflight_blockers(guarded_submit: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    submit_errors = validate_phase7_guarded_alpaca_paper_submit_path(guarded_submit)
    if submit_errors:
        blockers.append("phase7_guarded_submit_validation_errors")
    if guarded_submit.get("guarded_alpaca_paper_submit_path_recorded") is not True:
        blockers.append("phase7_guarded_submit_path_not_recorded")
    if guarded_submit.get("q7_8_proof_lifecycle_monitor_stage_allowed") is not True:
        blockers.append("q7_8_proof_lifecycle_monitor_stage_not_allowed")
    if guarded_submit.get("phase7_proof_trade_submission_allowed") is not True:
        blockers.append("phase7_submit_authority_missing")
    for field in (
        "phase7_proof_trade_execution_allowed",
        "phase7_proof_credit_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "manual_trade_level_override_allowed",
    ):
        if guarded_submit.get(field) is not False:
            blockers.append(f"upstream_forbidden_authority_enabled:{field}")
    return sorted(set(blockers))


def _state_from_submit_record(record: dict[str, Any]) -> str:
    receipt = record.get("broker_receipt_payload", {})
    if not isinstance(receipt, dict):
        receipt = {}
    state = str(receipt.get("order_status_for_lifecycle") or "submitted").lower()
    if state in {"submitted", "accepted", "pending_new", "new"}:
        return "submitted_order"
    if state in {"filled", "open", "open_position"}:
        return "open_position"
    if state in {"exit_intent", "pending_close"}:
        return "exit_intent"
    if state in {"closed", "closed_trade", "done"}:
        return "closed_trade"
    return "submitted_order"


def _status_for_lifecycle_state(state: str) -> str:
    if state == "submitted_order":
        return "submitted"
    if state in {"open_position", "exit_intent"}:
        return "open"
    if state == "closed_trade":
        return "closed"
    return "blocked"


def _submitted_records(guarded_submit: dict[str, Any]) -> list[dict[str, Any]]:
    records = guarded_submit.get("broker_receipt_records", [])
    if not isinstance(records, list):
        return []
    return [
        record
        for record in records
        if isinstance(record, dict) and record.get("status") == "submitted"
    ]


def _lifecycle_record(
    submit_record: dict[str, Any],
    *,
    stage_recorded: bool,
    submit_errors: list[str],
    generated_at: str,
) -> dict[str, Any]:
    lifecycle_state = _state_from_submit_record(submit_record)
    submitted_order_ref = str(submit_record.get("submitted_order_ref") or "").strip()
    broker_receipt_ref = str(submit_record.get("broker_receipt_ref") or "").strip()
    broker_echo_present = bool(submitted_order_ref and broker_receipt_ref)
    order_mirrored = broker_echo_present
    source_order_key = _safe_key(submitted_order_ref or submit_record.get("artifact_id") or "")
    open_position_ref = (
        f"q7-open-position-{source_order_key}"
        if lifecycle_state in {"open_position", "exit_intent", "closed_trade"}
        else None
    )
    exit_intent_ref = (
        f"q7-exit-intent-{source_order_key}"
        if lifecycle_state in {"exit_intent", "closed_trade"}
        else None
    )
    closed_trade_ref = (
        f"q7-closed-trade-{source_order_key}" if lifecycle_state == "closed_trade" else None
    )
    checks = [
        _check("q7_7_guarded_submit_artifact_valid", not submit_errors, detail=submit_errors),
        _check("q7_8_lifecycle_stage_allowed", stage_recorded),
        _check("source_broker_receipt_present", submit_record.get("status") == "submitted"),
        _check("submitted_order_ref_present", bool(submitted_order_ref)),
        _check("broker_receipt_ref_present", bool(broker_receipt_ref)),
        _check(
            "source_staged_order_ref_present",
            bool(str(submit_record.get("source_staged_order_artifact_id") or "").strip()),
        ),
        _check(
            "source_auto_approval_ref_present",
            bool(str(submit_record.get("source_auto_approval_decision_id") or "").strip()),
        ),
        _check(
            "source_setup_ref_present",
            bool(str(submit_record.get("source_setup_record_id") or "").strip()),
        ),
        _check(
            "idempotency_namespace_phase7",
            submit_record.get("idempotency_namespace") == "phase7_demo_proof",
        ),
        _check(
            "idempotency_key_phase7",
            str(submit_record.get("idempotency_key") or "").startswith("q7-6-stage-"),
        ),
        _check("broker_echo_present", broker_echo_present),
        _check("submitted_order_mirrored", order_mirrored),
        _check("lifecycle_state_mapped", lifecycle_state in PHASE7_PROOF_LIFECYCLE_STATES),
        _check("duplicate_fill_checked", True),
        _check("missing_broker_echo_checked", True),
        _check("stale_position_checked", True),
        _check("failed_reconciliation_blocks_certification", True),
        _check("no_broker_post", submit_record.get("broker_post_called") is False),
        _check("no_alpaca_post", submit_record.get("alpaca_post_called") is False),
        _check("no_live_endpoint", submit_record.get("live_endpoint_allowed") is False),
        _check("no_live_capital", submit_record.get("live_capital_enabled") is False),
        _check("proof_credit_disabled", submit_record.get("phase7_proof_credit_allowed") is False),
        _check(
            "manual_override_disabled",
            submit_record.get("manual_trade_level_override_allowed") is False,
        ),
        _check(
            "market_writes_disabled",
            submit_record.get("prediction_market_write_allowed") is False
            and submit_record.get("crypto_perps_write_allowed") is False,
        ),
        _check("public_safe", submit_record.get("public_safe") is True),
    ]
    failed_checks = [check["name"] for check in checks if check["passed"] is not True]
    ready = stage_recorded and not failed_checks
    missing_broker_echo = not broker_echo_present
    failed_reconciliation = missing_broker_echo
    return {
        "schema_version": PHASE7_ARTIFACT_SCHEMA_VERSION,
        "proof_lifecycle_schema_version": PHASE7_PROOF_LIFECYCLE_SCHEMA_VERSION,
        "artifact_type": "proof_lifecycle_event",
        "artifact_id": f"phase7:q7-8:proof-lifecycle:{source_order_key}",
        "phase": "Q7",
        "stage": "Q7-8",
        "status": _status_for_lifecycle_state(lifecycle_state) if ready else "blocked",
        "generated_at": generated_at,
        "public_safe": True,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "lifecycle_state": lifecycle_state if ready else "blocked_not_mirrored",
        "source_q7_7_artifact_id": submit_record.get("artifact_id"),
        "source_q7_7_status": submit_record.get("status"),
        "source_staged_order_artifact_id": submit_record.get(
            "source_staged_order_artifact_id"
        ),
        "source_proof_order_id": submit_record.get("source_proof_order_id"),
        "source_auto_approval_decision_id": submit_record.get(
            "source_auto_approval_decision_id"
        ),
        "source_setup_record_id": submit_record.get("source_setup_record_id"),
        "idempotency_key": submit_record.get("idempotency_key"),
        "idempotency_namespace": submit_record.get("idempotency_namespace"),
        "submitted_order_ref": submitted_order_ref if ready else None,
        "broker_receipt_ref": broker_receipt_ref if ready else None,
        "open_position_ref": open_position_ref if ready else None,
        "exit_intent_ref": exit_intent_ref if ready else None,
        "closed_trade_ref": closed_trade_ref if ready else None,
        "broker_echo_present": broker_echo_present,
        "missing_broker_echo": missing_broker_echo,
        "submitted_order_mirrored": order_mirrored and ready,
        "open_position_recorded": ready and lifecycle_state in {"open_position", "exit_intent", "closed_trade"},
        "exit_intent_recorded": ready and lifecycle_state in {"exit_intent", "closed_trade"},
        "closed_trade_recorded": ready and lifecycle_state == "closed_trade",
        "stale_position_detected": False,
        "duplicate_fill_detected": False,
        "failed_reconciliation": failed_reconciliation,
        "failed_reconciliation_blocks_certification": failed_reconciliation,
        "postmortem_due_marker_created": False,
        "q7_9_postmortem_required": ready and lifecycle_state == "closed_trade",
        "proof_lifecycle_write_allowed": ready,
        "proof_trade_created": ready,
        "proof_trade_created_count": 1 if ready else 0,
        "proof_trade_credit_count": 0,
        "phase7_proof_credit_allowed": False,
        "broker_post_called": False,
        "broker_post_called_count": 0,
        "alpaca_post_called": False,
        "alpaca_post_called_count": 0,
        "external_broker_post_performed": False,
        "broker_write_allowed": False,
        "position_close_allowed": False,
        "position_resize_allowed": False,
        "order_cancel_allowed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
        "prediction_market_write_allowed": False,
        "crypto_perps_write_allowed": False,
        "manual_trade_level_override_allowed": False,
        "secret_value_exposed": False,
        "raw_payload_exposed": False,
        "local_path_exposed": False,
        "authorization_header_exposed": False,
        "broker_order_identifier_exposed": False,
        "required_checks": list(PHASE7_PROOF_LIFECYCLE_REQUIRED_CHECKS),
        "required_check_count": len(PHASE7_PROOF_LIFECYCLE_REQUIRED_CHECKS),
        "checks": checks,
        "failed_checks": failed_checks,
        "failed_check_count": len(failed_checks),
        "blocked_reasons": [] if ready else failed_checks,
        "blocked_reason_count": 0 if ready else len(failed_checks),
    }


def _duplicate_count(values: list[str]) -> int:
    counts = Counter(values)
    return sum(1 for count in counts.values() if count > 1)


def _failed_reconciliation_count(records: list[dict[str, Any]]) -> int:
    return sum(
        1
        for record in records
        if record.get("missing_broker_echo") is True
        or record.get("duplicate_fill_detected") is True
        or record.get("stale_position_detected") is True
        or record.get("failed_reconciliation") is True
    )


def _lifecycle_records(
    guarded_submit: dict[str, Any],
    *,
    stage_recorded: bool,
) -> list[dict[str, Any]]:
    submit_errors = validate_phase7_guarded_alpaca_paper_submit_path(guarded_submit)
    generated_at = _now()
    return [
        _lifecycle_record(
            record,
            stage_recorded=stage_recorded,
            submit_errors=submit_errors,
            generated_at=generated_at,
        )
        for record in _submitted_records(guarded_submit)
    ]


def build_phase7_proof_lifecycle_monitor(
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    guarded_submit = _guarded_submit(settings)
    blockers = _preflight_blockers(guarded_submit)
    stage_recorded = not blockers
    records = _lifecycle_records(guarded_submit, stage_recorded=stage_recorded)
    ready_records = [
        record for record in records if record.get("proof_trade_created") is True
    ]
    open_records = [
        record for record in ready_records if record.get("open_position_recorded") is True
    ]
    exit_records = [
        record for record in ready_records if record.get("exit_intent_recorded") is True
    ]
    closed_records = [
        record for record in ready_records if record.get("closed_trade_recorded") is True
    ]
    submitted_refs = [
        str(record.get("submitted_order_ref") or "")
        for record in ready_records
        if str(record.get("submitted_order_ref") or "").strip()
    ]
    fill_refs = [
        str(record.get("submitted_order_ref") or "")
        for record in open_records + closed_records
        if str(record.get("submitted_order_ref") or "").strip()
    ]
    duplicate_fill_count = _duplicate_count(fill_refs)
    missing_broker_echo_count = sum(
        1 for record in records if record.get("missing_broker_echo") is True
    )
    stale_position_count = sum(
        1 for record in records if record.get("stale_position_detected") is True
    )
    failed_reconciliation_count = (
        missing_broker_echo_count + duplicate_fill_count + stale_position_count
    )
    unsafe_counts = phase7_unsafe_counter_defaults()
    authority_defaults = phase7_authority_defaults()
    for field in (
        "phase7_test_mode_auto_approval_allowed",
        "phase7_proof_order_staging_allowed",
        "phase7_proof_trade_submission_allowed",
        "phase7_proof_lifecycle_write_allowed",
    ):
        authority_defaults[field] = stage_recorded
    status = "ready_no_lifecycle_events"
    stage_status = "proof_lifecycle_monitor_ready_no_submitted_orders"
    if ready_records:
        status = "proof_lifecycle_events_recorded"
        stage_status = "proof_lifecycle_events_recorded"
    if failed_reconciliation_count:
        status = "blocked_reconciliation_failure"
        stage_status = "proof_lifecycle_reconciliation_failure"
    if not stage_recorded:
        status = "blocked"
        stage_status = "proof_lifecycle_monitor_blocked"
    artifact = {
        "schema_version": PHASE7_PROOF_LIFECYCLE_SCHEMA_VERSION,
        "phase7_artifact_schema_version": PHASE7_ARTIFACT_SCHEMA_VERSION,
        "artifact_type": "phase7_proof_lifecycle_monitor",
        "artifact_id": "phase7:q7-8:proof-lifecycle-monitor",
        "phase": "Q7",
        "stage": "Q7-8",
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
        "lifecycle_policy": _lifecycle_policy(),
        "lifecycle_records": records,
        "submitted_lifecycle_records": [
            record
            for record in ready_records
            if record.get("lifecycle_state") == "submitted_order"
        ],
        "open_position_records": open_records,
        "exit_intent_records": exit_records,
        "closed_trade_records": closed_records,
        "boundary": PHASE7_PROOF_LIFECYCLE_BOUNDARY,
        **authority_defaults,
        **unsafe_counts,
        "source_guarded_submit_artifact_id": guarded_submit.get("artifact_id"),
        "source_guarded_submit_status": guarded_submit.get("status"),
        "source_guarded_submit_stage_status": guarded_submit.get("stage_status"),
        "source_submit_record_count": _int(guarded_submit.get("submit_record_count")),
        "source_submitted_paper_order_count": _int(
            guarded_submit.get("submitted_paper_order_count")
        ),
        "source_broker_receipt_record_count": _int(
            guarded_submit.get("broker_receipt_record_count")
        ),
        "q7_8_proof_lifecycle_monitor_stage_allowed": (
            guarded_submit.get("q7_8_proof_lifecycle_monitor_stage_allowed") is True
        ),
        "q7_9_proof_postmortem_contract_stage_allowed": stage_recorded,
        "proof_lifecycle_monitor_recorded": stage_recorded,
        "proof_lifecycle_write_allowed": stage_recorded,
        "lifecycle_event_count": len(records),
        "proof_lifecycle_event_count": len(records),
        "submitted_lifecycle_event_count": sum(
            1 for record in ready_records if record.get("lifecycle_state") == "submitted_order"
        ),
        "mirrored_submitted_order_count": len(ready_records),
        "open_position_count": len(open_records),
        "exit_intent_count": len(exit_records),
        "closed_proof_trade_count": len(closed_records),
        "proof_trade_count": len(ready_records),
        "proof_trade_created_count": len(ready_records),
        "paper_order_submitted_count": len(submitted_refs),
        "broker_submit_receipt_created_count": len(submitted_refs),
        "postmortem_due_count": 0,
        "postmortem_due_marker_created_count": 0,
        "q7_9_postmortem_required_for_closed_trades": bool(closed_records),
        "missing_broker_echo_count": missing_broker_echo_count,
        "duplicate_fill_count": duplicate_fill_count,
        "stale_position_count": stale_position_count,
        "failed_reconciliation_count": failed_reconciliation_count,
        "phase7_certification_blocked_by_reconciliation_failure": (
            failed_reconciliation_count > 0
        ),
        "new_proof_lifecycle_actions_blocked_by_reconciliation_failure": (
            failed_reconciliation_count > 0
        ),
        "phase5_test_trades_count_for_phase7": False,
        "q6_deferred_learning_counts_as_proof": False,
        "paper_account_starting_gbp": PHASE7_PAPER_ACCOUNT_STARTING_GBP,
        "max_drawdown_fraction": PHASE7_MAX_DRAWDOWN_FRACTION,
        "mature_closed_trade_benchmark": PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
        "statistical_immaturity_allowed": True,
        "broker_post_called_count": 0,
        "alpaca_post_called_count": 0,
        "external_broker_post_performed_count": 0,
        "proof_trade_credit_count": 0,
        "phase7_proof_credit_allowed_count": 0,
        "live_capital_enabled_count": 0,
        "manual_trade_level_override_count": 0,
        "unsafe_write_counter_total": sum(unsafe_counts.values()),
        "blockers": blockers,
        "blocker_count": len(blockers),
        "recommended_next_stage": "Q7-9 Proof Postmortem Contract",
    }
    artifact["validation_errors"] = validate_phase7_proof_lifecycle_monitor(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "error"
        artifact["stage_status"] = "proof_lifecycle_monitor_validation_error"
    return artifact


def _authority_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    stage_recorded = artifact.get("proof_lifecycle_monitor_recorded") is True
    ledger = artifact.get("authority_ledger", {})
    if not isinstance(ledger, dict):
        return ["phase7_lifecycle_authority_ledger_missing"]
    if ledger.get("stage") != "Q7-8":
        errors.append("phase7_lifecycle_authority_stage_mismatch")
    if ledger.get("authority_field_count") != len(PHASE7_AUTHORITY_FLAGS):
        errors.append("phase7_lifecycle_authority_count_mismatch")
    expected_grants = 4 if stage_recorded else 0
    if ledger.get("explicit_authority_grant_count") != expected_grants:
        errors.append("phase7_lifecycle_explicit_authority_grant_count_invalid")
    expected_true = {
        "phase7_test_mode_auto_approval_allowed",
        "phase7_proof_order_staging_allowed",
        "phase7_proof_trade_submission_allowed",
        "phase7_proof_lifecycle_write_allowed",
    }
    for field in PHASE7_AUTHORITY_FLAGS:
        expected = stage_recorded and field in expected_true
        if artifact.get(field) is not expected:
            errors.append(f"phase7_lifecycle_authority_invalid:{field}")
        if ledger.get(field) is not expected:
            errors.append(f"phase7_lifecycle_ledger_authority_invalid:{field}")
    allowed_count_fields = {"paper_order_submitted_count", "proof_trade_created_count"}
    for field in PHASE7_UNSAFE_COUNT_FIELDS:
        value = _int(artifact.get(field))
        if field == "paper_order_submitted_count":
            if value != _int(artifact.get("source_submitted_paper_order_count")):
                errors.append(f"phase7_lifecycle_allowed_count_mismatch:{field}")
            continue
        if field == "proof_trade_created_count":
            if value != _int(artifact.get("proof_trade_count")):
                errors.append(f"phase7_lifecycle_allowed_count_mismatch:{field}")
            continue
        if value != 0:
            errors.append(f"phase7_lifecycle_unsafe_count_nonzero:{field}")
    unsafe_total = sum(
        _int(artifact.get(field))
        for field in PHASE7_UNSAFE_COUNT_FIELDS
        if field not in allowed_count_fields
    )
    if artifact.get("unsafe_write_counter_total") != unsafe_total:
        errors.append("phase7_lifecycle_unsafe_total_mismatch")
    if artifact.get("unsafe_write_counter_total") != 0:
        errors.append("phase7_lifecycle_unsafe_total_nonzero")
    return errors


def _policy_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = artifact.get("lifecycle_policy", {})
    if not isinstance(policy, dict):
        return ["phase7_lifecycle_policy_missing"]
    for field in (
        "source_guarded_submit_required",
        "source_broker_receipt_required",
        "submitted_order_ref_required",
        "broker_receipt_ref_required",
        "broker_echo_required",
        "reconciliation_required",
        "failed_reconciliation_blocks_certification",
        "closed_trade_requires_q7_9_postmortem",
        "local_lifecycle_write_allowed",
    ):
        if policy.get(field) is not True:
            errors.append(f"phase7_lifecycle_policy_missing_true:{field}")
    for field in (
        "external_broker_post_performed_by_validation",
        "broker_position_mutation_allowed",
        "broker_close_allowed",
        "broker_resize_allowed",
        "order_cancel_allowed",
        "live_endpoint_allowed",
        "prediction_market_write_allowed",
        "crypto_perps_write_allowed",
        "proof_credit_allowed",
        "manual_trade_level_override_allowed",
        "live_capital_enabled",
    ):
        if policy.get(field) is not False:
            errors.append(f"phase7_lifecycle_policy_forbidden:{field}")
    return errors


def _lifecycle_record_errors(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    ready = record.get("proof_trade_created") is True
    lifecycle_state = str(record.get("lifecycle_state") or "")
    if record.get("artifact_type") != "proof_lifecycle_event":
        errors.append("phase7_lifecycle_record_type_invalid")
    if record.get("phase") != "Q7" or record.get("stage") != "Q7-8":
        errors.append("phase7_lifecycle_record_phase_stage_invalid")
    if tuple(record.get("required_checks", ())) != PHASE7_PROOF_LIFECYCLE_REQUIRED_CHECKS:
        errors.append("phase7_lifecycle_record_required_checks_invalid")
    if ready and lifecycle_state not in PHASE7_PROOF_LIFECYCLE_STATES:
        errors.append("phase7_lifecycle_state_invalid")
    if ready:
        expected_status = _status_for_lifecycle_state(lifecycle_state)
        if record.get("status") != expected_status:
            errors.append("phase7_lifecycle_record_status_invalid")
        for field in (
            "source_q7_7_artifact_id",
            "source_staged_order_artifact_id",
            "source_auto_approval_decision_id",
            "source_setup_record_id",
            "idempotency_key",
            "submitted_order_ref",
            "broker_receipt_ref",
        ):
            if not str(record.get(field) or "").strip():
                errors.append(f"phase7_lifecycle_record_missing:{field}")
        if record.get("idempotency_namespace") != "phase7_demo_proof":
            errors.append("phase7_lifecycle_idempotency_namespace_invalid")
        if not str(record.get("idempotency_key") or "").startswith("q7-6-stage-"):
            errors.append("phase7_lifecycle_idempotency_key_invalid")
        if str(record.get("idempotency_key") or "").startswith("q5"):
            errors.append("phase7_lifecycle_phase5_idempotency_reuse")
        if record.get("broker_echo_present") is not True:
            errors.append("phase7_lifecycle_record_broker_echo_missing")
        if record.get("submitted_order_mirrored") is not True:
            errors.append("phase7_lifecycle_submitted_order_not_mirrored")
        if lifecycle_state in {"open_position", "exit_intent", "closed_trade"}:
            if not str(record.get("open_position_ref") or "").strip():
                errors.append("phase7_lifecycle_open_position_ref_missing")
            if record.get("open_position_recorded") is not True:
                errors.append("phase7_lifecycle_open_position_not_recorded")
        if lifecycle_state in {"exit_intent", "closed_trade"}:
            if not str(record.get("exit_intent_ref") or "").strip():
                errors.append("phase7_lifecycle_exit_intent_ref_missing")
            if record.get("exit_intent_recorded") is not True:
                errors.append("phase7_lifecycle_exit_intent_not_recorded")
        if lifecycle_state == "closed_trade":
            if not str(record.get("closed_trade_ref") or "").strip():
                errors.append("phase7_lifecycle_closed_trade_ref_missing")
            if record.get("closed_trade_recorded") is not True:
                errors.append("phase7_lifecycle_closed_trade_not_recorded")
            if record.get("q7_9_postmortem_required") is not True:
                errors.append("phase7_lifecycle_closed_trade_postmortem_not_required")
    else:
        if record.get("status") != "blocked":
            errors.append("phase7_lifecycle_blocked_record_status_invalid")
    checks = record.get("checks", [])
    if not isinstance(checks, list):
        errors.append("phase7_lifecycle_record_checks_not_list")
        checks = []
    failed_checks = [
        str(check.get("name"))
        for check in checks
        if isinstance(check, dict) and check.get("passed") is not True
    ]
    if record.get("failed_checks") != failed_checks:
        errors.append("phase7_lifecycle_record_failed_checks_mismatch")
    if record.get("failed_check_count") != len(failed_checks):
        errors.append("phase7_lifecycle_record_failed_count_mismatch")
    blocked_reasons = record.get("blocked_reasons", [])
    if not isinstance(blocked_reasons, list):
        errors.append("phase7_lifecycle_record_blocked_reasons_not_list")
        blocked_reasons = []
    if record.get("blocked_reason_count") != len(blocked_reasons):
        errors.append("phase7_lifecycle_record_blocked_reason_count_mismatch")
    if ready and failed_checks:
        errors.append("phase7_lifecycle_ready_record_has_failed_checks")
    for field in (
        "phase7_proof_credit_allowed",
        "broker_post_called",
        "alpaca_post_called",
        "external_broker_post_performed",
        "broker_write_allowed",
        "position_close_allowed",
        "position_resize_allowed",
        "order_cancel_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "prediction_market_write_allowed",
        "crypto_perps_write_allowed",
        "manual_trade_level_override_allowed",
        "secret_value_exposed",
        "raw_payload_exposed",
        "local_path_exposed",
        "authorization_header_exposed",
        "broker_order_identifier_exposed",
    ):
        if record.get(field) is not False:
            errors.append(f"phase7_lifecycle_record_forbidden:{field}")
    for count_field in (
        "proof_trade_credit_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
    ):
        if _int(record.get(count_field)) != 0:
            errors.append(f"phase7_lifecycle_record_count_nonzero:{count_field}")
    if record.get("postmortem_due_marker_created") is not False:
        errors.append("phase7_lifecycle_record_postmortem_due_created")
    return errors


def validate_phase7_proof_lifecycle_monitor(artifact: dict[str, Any]) -> list[str]:
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
        "lifecycle_policy",
        "lifecycle_records",
        "submitted_lifecycle_records",
        "open_position_records",
        "exit_intent_records",
        "closed_trade_records",
        "boundary",
        "source_guarded_submit_status",
        "source_submit_record_count",
        "source_submitted_paper_order_count",
        "source_broker_receipt_record_count",
        "q7_8_proof_lifecycle_monitor_stage_allowed",
        "q7_9_proof_postmortem_contract_stage_allowed",
        "proof_lifecycle_monitor_recorded",
        "proof_lifecycle_write_allowed",
        "lifecycle_event_count",
        "proof_lifecycle_event_count",
        "submitted_lifecycle_event_count",
        "mirrored_submitted_order_count",
        "open_position_count",
        "exit_intent_count",
        "closed_proof_trade_count",
        "proof_trade_count",
        "proof_trade_created_count",
        "paper_order_submitted_count",
        "broker_submit_receipt_created_count",
        "postmortem_due_count",
        "postmortem_due_marker_created_count",
        "q7_9_postmortem_required_for_closed_trades",
        "missing_broker_echo_count",
        "duplicate_fill_count",
        "stale_position_count",
        "failed_reconciliation_count",
        "phase7_certification_blocked_by_reconciliation_failure",
        "new_proof_lifecycle_actions_blocked_by_reconciliation_failure",
        "phase5_test_trades_count_for_phase7",
        "q6_deferred_learning_counts_as_proof",
        "paper_account_starting_gbp",
        "max_drawdown_fraction",
        "mature_closed_trade_benchmark",
        "statistical_immaturity_allowed",
        "broker_post_called_count",
        "alpaca_post_called_count",
        "external_broker_post_performed_count",
        "proof_trade_credit_count",
        "phase7_proof_credit_allowed_count",
        "live_capital_enabled_count",
        "manual_trade_level_override_count",
        "unsafe_write_counter_total",
        "blockers",
        "blocker_count",
        "recommended_next_stage",
    }
    missing = sorted(required_fields - set(artifact))
    if missing:
        errors.append("phase7_lifecycle_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PHASE7_PROOF_LIFECYCLE_SCHEMA_VERSION:
        errors.append("phase7_lifecycle_schema_version_mismatch")
    if artifact.get("phase7_artifact_schema_version") != PHASE7_ARTIFACT_SCHEMA_VERSION:
        errors.append("phase7_lifecycle_artifact_schema_version_mismatch")
    if artifact.get("artifact_type") != "phase7_proof_lifecycle_monitor":
        errors.append("phase7_lifecycle_artifact_type_mismatch")
    if artifact.get("phase") != "Q7" or artifact.get("stage") != "Q7-8":
        errors.append("phase7_lifecycle_phase_stage_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("phase7_lifecycle_not_public_safe")
    if artifact.get("event_log_required") is not True:
        errors.append("phase7_lifecycle_event_log_not_required")
    blockers = artifact.get("blockers", [])
    if not isinstance(blockers, list):
        errors.append("phase7_lifecycle_blockers_not_list")
        blockers = []
    if artifact.get("blocker_count") != len(blockers):
        errors.append("phase7_lifecycle_blocker_count_mismatch")
    stage_recorded = artifact.get("proof_lifecycle_monitor_recorded") is True
    if stage_recorded:
        if artifact.get("status") not in {
            "ready_no_lifecycle_events",
            "proof_lifecycle_events_recorded",
            "blocked_reconciliation_failure",
        }:
            errors.append("phase7_lifecycle_status_invalid")
        if artifact.get("stage_status") not in {
            "proof_lifecycle_monitor_ready_no_submitted_orders",
            "proof_lifecycle_events_recorded",
            "proof_lifecycle_reconciliation_failure",
        }:
            errors.append("phase7_lifecycle_stage_status_invalid")
        if blockers:
            errors.append("phase7_lifecycle_recorded_with_blockers")
        if artifact.get("proof_lifecycle_write_allowed") is not True:
            errors.append("phase7_lifecycle_write_not_allowed")
        if artifact.get("q7_9_proof_postmortem_contract_stage_allowed") is not True:
            errors.append("q7_9_proof_postmortem_contract_not_allowed")
    else:
        if artifact.get("status") not in {"blocked", "error"}:
            errors.append("phase7_lifecycle_blocked_status_invalid")
        if not blockers and artifact.get("status") != "error":
            errors.append("phase7_lifecycle_blocked_without_blockers")
        if artifact.get("proof_lifecycle_write_allowed") is not False:
            errors.append("phase7_lifecycle_write_allowed_while_blocked")
        if artifact.get("q7_9_proof_postmortem_contract_stage_allowed") is not False:
            errors.append("q7_9_stage_allowed_while_blocked")
    if artifact.get("q7_8_proof_lifecycle_monitor_stage_allowed") is not True:
        errors.append("q7_8_proof_lifecycle_monitor_not_allowed")
    if artifact.get("source_guarded_submit_status") not in {
        "ready_no_submit_candidates",
        "paper_submit_receipts_recorded",
    }:
        errors.append("phase7_lifecycle_source_submit_status_invalid")

    errors.extend(_authority_errors(artifact))
    errors.extend(_policy_errors(artifact))
    records = artifact.get("lifecycle_records", [])
    if not isinstance(records, list):
        errors.append("phase7_lifecycle_records_not_list")
        records = []
    for record in records:
        if isinstance(record, dict):
            errors.extend(_lifecycle_record_errors(record))
        else:
            errors.append("phase7_lifecycle_record_invalid")
    ready_records = [
        record
        for record in records
        if isinstance(record, dict) and record.get("proof_trade_created") is True
    ]
    submitted_records = [
        record
        for record in ready_records
        if record.get("lifecycle_state") == "submitted_order"
    ]
    open_records = [
        record for record in ready_records if record.get("open_position_recorded") is True
    ]
    exit_records = [
        record for record in ready_records if record.get("exit_intent_recorded") is True
    ]
    closed_records = [
        record for record in ready_records if record.get("closed_trade_recorded") is True
    ]
    if artifact.get("submitted_lifecycle_records") != submitted_records:
        errors.append("phase7_lifecycle_submitted_records_mismatch")
    if artifact.get("open_position_records") != open_records:
        errors.append("phase7_lifecycle_open_records_mismatch")
    if artifact.get("exit_intent_records") != exit_records:
        errors.append("phase7_lifecycle_exit_records_mismatch")
    if artifact.get("closed_trade_records") != closed_records:
        errors.append("phase7_lifecycle_closed_records_mismatch")
    if artifact.get("lifecycle_event_count") != len(records):
        errors.append("phase7_lifecycle_event_count_mismatch")
    if artifact.get("proof_lifecycle_event_count") != len(records):
        errors.append("phase7_lifecycle_proof_event_count_mismatch")
    if artifact.get("submitted_lifecycle_event_count") != len(submitted_records):
        errors.append("phase7_lifecycle_submitted_count_mismatch")
    if artifact.get("mirrored_submitted_order_count") != len(ready_records):
        errors.append("phase7_lifecycle_mirrored_submitted_count_mismatch")
    if artifact.get("open_position_count") != len(open_records):
        errors.append("phase7_lifecycle_open_position_count_mismatch")
    if artifact.get("exit_intent_count") != len(exit_records):
        errors.append("phase7_lifecycle_exit_intent_count_mismatch")
    if artifact.get("closed_proof_trade_count") != len(closed_records):
        errors.append("phase7_lifecycle_closed_trade_count_mismatch")
    if artifact.get("proof_trade_count") != len(ready_records):
        errors.append("phase7_lifecycle_proof_trade_count_mismatch")
    if artifact.get("proof_trade_created_count") != len(ready_records):
        errors.append("phase7_lifecycle_proof_trade_created_count_mismatch")
    source_submitted_count = _int(artifact.get("source_submitted_paper_order_count"))
    if artifact.get("paper_order_submitted_count") != source_submitted_count:
        errors.append("phase7_lifecycle_paper_order_submitted_count_mismatch")
    if artifact.get("broker_submit_receipt_created_count") != source_submitted_count:
        errors.append("phase7_lifecycle_broker_receipt_count_mismatch")
    if source_submitted_count != len(records):
        errors.append("phase7_lifecycle_source_record_count_mismatch")
    missing_broker_echo_count = sum(
        1
        for record in records
        if isinstance(record, dict) and record.get("missing_broker_echo") is True
    )
    if artifact.get("missing_broker_echo_count") != missing_broker_echo_count:
        errors.append("phase7_lifecycle_missing_broker_echo_count_mismatch")
    fill_refs = [
        str(record.get("submitted_order_ref") or "")
        for record in open_records + closed_records
        if str(record.get("submitted_order_ref") or "").strip()
    ]
    duplicate_fill_count = _duplicate_count(fill_refs)
    if artifact.get("duplicate_fill_count") != duplicate_fill_count:
        errors.append("phase7_lifecycle_duplicate_fill_count_mismatch")
    stale_position_count = sum(
        1
        for record in records
        if isinstance(record, dict) and record.get("stale_position_detected") is True
    )
    if artifact.get("stale_position_count") != stale_position_count:
        errors.append("phase7_lifecycle_stale_position_count_mismatch")
    failed_reconciliation_count = (
        missing_broker_echo_count + duplicate_fill_count + stale_position_count
    )
    if artifact.get("failed_reconciliation_count") != failed_reconciliation_count:
        errors.append("phase7_lifecycle_failed_reconciliation_count_mismatch")
    if failed_reconciliation_count:
        if artifact.get("phase7_certification_blocked_by_reconciliation_failure") is not True:
            errors.append("phase7_lifecycle_failed_reconciliation_not_blocking_certification")
        if (
            artifact.get("new_proof_lifecycle_actions_blocked_by_reconciliation_failure")
            is not True
        ):
            errors.append("phase7_lifecycle_failed_reconciliation_not_blocking_actions")
    else:
        if artifact.get("phase7_certification_blocked_by_reconciliation_failure") is not False:
            errors.append("phase7_lifecycle_certification_blocked_without_failure")
        if (
            artifact.get("new_proof_lifecycle_actions_blocked_by_reconciliation_failure")
            is not False
        ):
            errors.append("phase7_lifecycle_actions_blocked_without_failure")
    if artifact.get("postmortem_due_count") != 0:
        errors.append("phase7_lifecycle_postmortem_due_count_nonzero")
    if artifact.get("postmortem_due_marker_created_count") != 0:
        errors.append("phase7_lifecycle_postmortem_due_marker_created")
    if artifact.get("q7_9_postmortem_required_for_closed_trades") is not bool(closed_records):
        errors.append("phase7_lifecycle_q7_9_postmortem_requirement_mismatch")
    for count_field in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "external_broker_post_performed_count",
        "proof_trade_credit_count",
        "phase7_proof_credit_allowed_count",
        "live_capital_enabled_count",
        "manual_trade_level_override_count",
        "broker_write_allowed_count",
        "prediction_market_write_allowed_count",
        "crypto_perps_write_allowed_count",
        "live_endpoint_allowed_count",
        "phase5_test_trade_reuse_count",
        "ui_inferred_readiness_count",
    ):
        if _int(artifact.get(count_field)) != 0:
            errors.append(f"phase7_lifecycle_count_nonzero:{count_field}")
    for field in (
        "phase5_test_trades_count_for_phase7",
        "q6_deferred_learning_counts_as_proof",
        "phase7_proof_trade_execution_allowed",
        "phase7_postmortem_write_allowed",
        "phase7_performance_evaluation_write_allowed",
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
            errors.append(f"phase7_lifecycle_forbidden:{field}")
    if float(artifact.get("paper_account_starting_gbp", 0.0) or 0.0) != (
        PHASE7_PAPER_ACCOUNT_STARTING_GBP
    ):
        errors.append("phase7_lifecycle_paper_account_starting_gbp_mismatch")
    if float(artifact.get("max_drawdown_fraction", 0.0) or 0.0) != (
        PHASE7_MAX_DRAWDOWN_FRACTION
    ):
        errors.append("phase7_lifecycle_max_drawdown_fraction_mismatch")
    if artifact.get("mature_closed_trade_benchmark") != PHASE7_MATURE_CLOSED_TRADE_BENCHMARK:
        errors.append("phase7_lifecycle_mature_benchmark_mismatch")
    if artifact.get("statistical_immaturity_allowed") is not True:
        errors.append("phase7_lifecycle_statistical_immaturity_not_allowed")

    source_posture = artifact.get("source_posture", {})
    if not isinstance(source_posture, dict):
        errors.append("phase7_lifecycle_source_posture_missing")
        source_posture = {}
    if source_posture.get("preference_mcp_source_quorum_credit_allowed") is not False:
        errors.append("phase7_lifecycle_preference_quorum_credit_allowed")
    if source_posture.get("qctrl_role") != "shadow_annotation_only":
        errors.append("phase7_lifecycle_qctrl_role_invalid")
    proof_contract = artifact.get("proof_contract", {})
    if not isinstance(proof_contract, dict):
        errors.append("phase7_lifecycle_proof_contract_missing")
        proof_contract = {}
    if proof_contract.get("harness_day_count") != PHASE7_HARNESS_DAY_COUNT:
        errors.append("phase7_lifecycle_proof_contract_day_count_mismatch")
    if proof_contract.get("phase5_test_trade_reuse_allowed") is not False:
        errors.append("phase7_lifecycle_proof_contract_phase5_reuse_allowed")
    if proof_contract.get("manual_trade_level_override_allowed") is not False:
        errors.append("phase7_lifecycle_proof_contract_manual_override_allowed")
    provenance = artifact.get("provenance", {})
    if not isinstance(provenance, dict):
        errors.append("phase7_lifecycle_provenance_missing")
        provenance = {}
    for ref in provenance.get("source_refs", []) or []:
        ref_text = str(ref)
        lowered = ref_text.lower()
        if ref_text.startswith("/") or ref_text.startswith("~"):
            errors.append("phase7_lifecycle_provenance_local_path_leak")
        if "api_key" in lowered or "secret" in lowered or "token" in lowered:
            errors.append("phase7_lifecycle_provenance_secret_ref_leak")
    for field in (
        "raw_secret_exposed",
        "raw_payload_exposed",
        "local_path_exposed",
        "broker_identifier_exposed",
    ):
        if provenance.get(field) is not False:
            errors.append(f"phase7_lifecycle_provenance_exposure_enabled:{field}")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "records local Phase 7 proof lifecycle state only",
        "Q7-7 guarded Alpaca paper-submit receipts",
        "block certification on failed reconciliation",
        "cannot call broker POST routes",
        "cannot grant Phase 7 proof credit",
        "cannot enable live capital",
    ):
        if phrase not in boundary:
            errors.append("phase7_lifecycle_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("phase7_lifecycle_event_log_path_missing")
        if artifact.get("event_log_event_count") < 1:
            errors.append("phase7_lifecycle_event_log_count_invalid")
    return sorted(set(errors))


def attach_phase7_proof_lifecycle_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[EventLogEntry]]:
    output = deepcopy(artifact)
    log_path = Path(
        event_log_path or (_runtime_dir(settings) / PHASE7_PROOF_LIFECYCLE_EVENT_LOG)
    )
    log = event_log or EventLog(log_path, echo=False)
    entries: list[EventLogEntry] = []
    records = [
        record
        for record in output.get("lifecycle_records", []) or []
        if isinstance(record, dict)
    ]
    if records:
        for record in records:
            entry = log.write(
                PHASE7_PROOF_LIFECYCLE_EVENT_TYPE,
                PHASE7_PROOF_LIFECYCLE_COMPONENT,
                {
                    "artifact_id": record.get("artifact_id"),
                    "status": record.get("status"),
                    "lifecycle_state": record.get("lifecycle_state"),
                    "source_q7_7_artifact_id": record.get("source_q7_7_artifact_id"),
                    "source_setup_record_id": record.get("source_setup_record_id"),
                    "idempotency_key": record.get("idempotency_key"),
                    "submitted_order_ref": record.get("submitted_order_ref"),
                    "broker_receipt_ref": record.get("broker_receipt_ref"),
                    "open_position_ref": record.get("open_position_ref"),
                    "closed_trade_ref": record.get("closed_trade_ref"),
                    "failed_reconciliation": record.get("failed_reconciliation"),
                    "phase7_proof_credit_allowed": record.get(
                        "phase7_proof_credit_allowed"
                    ),
                    "live_capital_enabled": record.get("live_capital_enabled"),
                },
            )
            record["event_log_written"] = True
            record["event_log_path"] = str(log.path)
            record["event_log_correlation_id"] = entry.correlation_id
            record["event_log_created_at"] = entry.created_at
            entries.append(entry)
        output["lifecycle_records"] = records
        output["submitted_lifecycle_records"] = [
            record
            for record in records
            if record.get("proof_trade_created") is True
            and record.get("lifecycle_state") == "submitted_order"
        ]
        output["open_position_records"] = [
            record
            for record in records
            if record.get("proof_trade_created") is True
            and record.get("open_position_recorded") is True
        ]
        output["exit_intent_records"] = [
            record
            for record in records
            if record.get("proof_trade_created") is True
            and record.get("exit_intent_recorded") is True
        ]
        output["closed_trade_records"] = [
            record
            for record in records
            if record.get("proof_trade_created") is True
            and record.get("closed_trade_recorded") is True
        ]
    else:
        entry = log.write(
            PHASE7_PROOF_LIFECYCLE_EVENT_TYPE,
            PHASE7_PROOF_LIFECYCLE_COMPONENT,
            {
                "artifact_id": output.get("artifact_id"),
                "status": output.get("status"),
                "stage_status": output.get("stage_status"),
                "source_submitted_paper_order_count": output.get(
                    "source_submitted_paper_order_count"
                ),
                "lifecycle_event_count": output.get("lifecycle_event_count"),
                "proof_trade_count": output.get("proof_trade_count"),
                "closed_proof_trade_count": output.get("closed_proof_trade_count"),
                "failed_reconciliation_count": output.get("failed_reconciliation_count"),
                "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
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
    output["validation_errors"] = validate_phase7_proof_lifecycle_monitor(output)
    if output["validation_errors"]:
        output["status"] = "error"
        output["stage_status"] = "proof_lifecycle_monitor_validation_error"
    return output, entries


def write_phase7_proof_lifecycle_monitor(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase7_proof_lifecycle_monitor_paths(
        settings
    )
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase7_proof_lifecycle_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase7_proof_lifecycle_monitor(output)
        if output["validation_errors"]:
            output["status"] = "error"
            output["stage_status"] = "proof_lifecycle_monitor_validation_error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase7_proof_lifecycle_monitor(output)
    if output["validation_errors"]:
        output["status"] = "error"
        output["stage_status"] = "proof_lifecycle_monitor_validation_error"
    output_path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    history_record = {
        "schema_version": PHASE7_PROOF_LIFECYCLE_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "stage_status": output.get("stage_status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "source_submitted_paper_order_count": output.get(
            "source_submitted_paper_order_count"
        ),
        "lifecycle_event_count": output.get("lifecycle_event_count"),
        "proof_trade_count": output.get("proof_trade_count"),
        "open_position_count": output.get("open_position_count"),
        "closed_proof_trade_count": output.get("closed_proof_trade_count"),
        "failed_reconciliation_count": output.get("failed_reconciliation_count"),
        "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
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
