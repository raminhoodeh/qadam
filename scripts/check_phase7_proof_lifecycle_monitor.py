#!/usr/bin/env python3
"""Validate Q7-8 Phase 7 Demo Proof lifecycle monitor."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase7_guarded_alpaca_paper_submit import (  # noqa: E402
    build_phase7_guarded_alpaca_paper_submit_path,
    validate_phase7_guarded_alpaca_paper_submit_path,
    write_phase7_guarded_alpaca_paper_submit_path,
)
from orchestrator.phase7_proof_lifecycle_monitor import (  # noqa: E402
    PHASE7_PROOF_LIFECYCLE_REQUIRED_CHECKS,
    PHASE7_PROOF_LIFECYCLE_SCHEMA_VERSION,
    build_phase7_proof_lifecycle_monitor,
    phase7_proof_lifecycle_monitor_paths,
    validate_phase7_proof_lifecycle_monitor,
    write_phase7_proof_lifecycle_monitor,
)


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _status_for_state(state: str) -> str:
    if state == "submitted_order":
        return "submitted"
    if state in {"open_position", "exit_intent"}:
        return "open"
    if state == "closed_trade":
        return "closed"
    return "blocked"


def _valid_lifecycle_record(
    *,
    state: str = "submitted_order",
    order_suffix: str = "probe0001",
) -> dict[str, object]:
    checks = [
        {"name": name, "passed": True, "detail": None}
        for name in PHASE7_PROOF_LIFECYCLE_REQUIRED_CHECKS
    ]
    source_order_ref = f"q7-paper-order-{order_suffix}"
    open_position_ref = (
        f"q7-open-position-{order_suffix}"
        if state in {"open_position", "exit_intent", "closed_trade"}
        else None
    )
    exit_intent_ref = (
        f"q7-exit-intent-{order_suffix}"
        if state in {"exit_intent", "closed_trade"}
        else None
    )
    closed_trade_ref = f"q7-closed-trade-{order_suffix}" if state == "closed_trade" else None
    return {
        "schema_version": 1,
        "proof_lifecycle_schema_version": PHASE7_PROOF_LIFECYCLE_SCHEMA_VERSION,
        "artifact_type": "proof_lifecycle_event",
        "artifact_id": f"phase7:q7-8:proof-lifecycle:{order_suffix}",
        "phase": "Q7",
        "stage": "Q7-8",
        "status": _status_for_state(state),
        "generated_at": "2026-05-25T00:00:00+00:00",
        "public_safe": True,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "lifecycle_state": state,
        "source_q7_7_artifact_id": "phase7:q7-7:guarded-alpaca-submit:probe",
        "source_q7_7_status": "submitted",
        "source_staged_order_artifact_id": "phase7:q7-6:staged-proof-order:probe",
        "source_proof_order_id": "q7-proof-order-probe0001",
        "source_auto_approval_decision_id": "probe:auto-approval:q7-setup",
        "source_setup_record_id": "probe:q7-setup",
        "idempotency_key": f"q7-6-stage-{order_suffix}",
        "idempotency_namespace": "phase7_demo_proof",
        "submitted_order_ref": source_order_ref,
        "broker_receipt_ref": f"q7-local-broker-receipt-{order_suffix}",
        "open_position_ref": open_position_ref,
        "exit_intent_ref": exit_intent_ref,
        "closed_trade_ref": closed_trade_ref,
        "broker_echo_present": True,
        "missing_broker_echo": False,
        "submitted_order_mirrored": True,
        "open_position_recorded": state in {"open_position", "exit_intent", "closed_trade"},
        "exit_intent_recorded": state in {"exit_intent", "closed_trade"},
        "closed_trade_recorded": state == "closed_trade",
        "stale_position_detected": False,
        "duplicate_fill_detected": False,
        "failed_reconciliation": False,
        "failed_reconciliation_blocks_certification": False,
        "postmortem_due_marker_created": False,
        "q7_9_postmortem_required": state == "closed_trade",
        "proof_lifecycle_write_allowed": True,
        "proof_trade_created": True,
        "proof_trade_created_count": 1,
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
        "failed_checks": [],
        "failed_check_count": 0,
        "blocked_reasons": [],
        "blocked_reason_count": 0,
    }


def _duplicate_count(values: list[str]) -> int:
    return sum(1 for count in Counter(values).values() if count > 1)


def _with_lifecycle_records(
    artifact: dict[str, object],
    records: list[dict[str, object]],
) -> dict[str, object]:
    probe = deepcopy(artifact)
    ready_records = [
        record for record in records if record.get("proof_trade_created") is True
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
    fill_refs = [
        str(record.get("submitted_order_ref") or "")
        for record in open_records + closed_records
        if str(record.get("submitted_order_ref") or "").strip()
    ]
    missing_count = sum(
        1 for record in records if record.get("missing_broker_echo") is True
    )
    duplicate_count = _duplicate_count(fill_refs)
    stale_count = sum(
        1 for record in records if record.get("stale_position_detected") is True
    )
    failed_count = missing_count + duplicate_count + stale_count
    probe["status"] = (
        "blocked_reconciliation_failure"
        if failed_count
        else "proof_lifecycle_events_recorded"
    )
    probe["stage_status"] = (
        "proof_lifecycle_reconciliation_failure"
        if failed_count
        else "proof_lifecycle_events_recorded"
    )
    probe["source_guarded_submit_status"] = "paper_submit_receipts_recorded"
    probe["source_guarded_submit_stage_status"] = "guarded_alpaca_submit_receipts_recorded"
    probe["source_submit_record_count"] = len(records)
    probe["source_submitted_paper_order_count"] = len(records)
    probe["source_broker_receipt_record_count"] = len(records)
    probe["lifecycle_records"] = records
    probe["submitted_lifecycle_records"] = submitted_records
    probe["open_position_records"] = open_records
    probe["exit_intent_records"] = exit_records
    probe["closed_trade_records"] = closed_records
    probe["lifecycle_event_count"] = len(records)
    probe["proof_lifecycle_event_count"] = len(records)
    probe["submitted_lifecycle_event_count"] = len(submitted_records)
    probe["mirrored_submitted_order_count"] = len(ready_records)
    probe["open_position_count"] = len(open_records)
    probe["exit_intent_count"] = len(exit_records)
    probe["closed_proof_trade_count"] = len(closed_records)
    probe["proof_trade_count"] = len(ready_records)
    probe["proof_trade_created_count"] = len(ready_records)
    probe["paper_order_submitted_count"] = len(records)
    probe["broker_submit_receipt_created_count"] = len(records)
    probe["postmortem_due_count"] = 0
    probe["postmortem_due_marker_created_count"] = 0
    probe["q7_9_postmortem_required_for_closed_trades"] = bool(closed_records)
    probe["missing_broker_echo_count"] = missing_count
    probe["duplicate_fill_count"] = duplicate_count
    probe["stale_position_count"] = stale_count
    probe["failed_reconciliation_count"] = failed_count
    probe["phase7_certification_blocked_by_reconciliation_failure"] = failed_count > 0
    probe["new_proof_lifecycle_actions_blocked_by_reconciliation_failure"] = (
        failed_count > 0
    )
    return probe


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = phase7_proof_lifecycle_monitor_paths(
        settings
    )
    if event_log_path.exists():
        event_log_path.unlink()

    guarded_submit = build_phase7_guarded_alpaca_paper_submit_path(settings=settings)
    _, _, guarded_event_path, guarded_written = write_phase7_guarded_alpaca_paper_submit_path(
        guarded_submit,
        settings=settings,
        record_event=True,
    )
    guarded_errors = validate_phase7_guarded_alpaca_paper_submit_path(guarded_written)
    artifact = build_phase7_proof_lifecycle_monitor(settings=settings)
    output_path, history_path, event_log_path, written = (
        write_phase7_proof_lifecycle_monitor(
            artifact,
            settings=settings,
            record_event=True,
            event_log_path=event_log_path,
        )
    )
    validation_errors = validate_phase7_proof_lifecycle_monitor(written)
    replay = EventLog(event_log_path, echo=False).replay()
    runtime_copy = _read_json(output_path)

    valid_submitted_probe = _with_lifecycle_records(
        written,
        [_valid_lifecycle_record(state="submitted_order")],
    )
    valid_submitted_errors = validate_phase7_proof_lifecycle_monitor(
        valid_submitted_probe
    )

    valid_closed_probe = _with_lifecycle_records(
        written,
        [_valid_lifecycle_record(state="closed_trade")],
    )
    valid_closed_errors = validate_phase7_proof_lifecycle_monitor(valid_closed_probe)

    missing_echo_record = _valid_lifecycle_record(state="submitted_order")
    missing_echo_record["broker_echo_present"] = False
    missing_echo_record["missing_broker_echo"] = True
    missing_echo_record["submitted_order_mirrored"] = False
    missing_echo_probe = _with_lifecycle_records(written, [missing_echo_record])
    missing_echo_errors = validate_phase7_proof_lifecycle_monitor(missing_echo_probe)

    duplicate_probe = _with_lifecycle_records(
        written,
        [
            _valid_lifecycle_record(state="open_position", order_suffix="dupe"),
            _valid_lifecycle_record(state="open_position", order_suffix="dupe"),
        ],
    )
    duplicate_probe["duplicate_fill_count"] = 0
    duplicate_errors = validate_phase7_proof_lifecycle_monitor(duplicate_probe)

    stale_record = _valid_lifecycle_record(state="open_position")
    stale_record["stale_position_detected"] = True
    stale_probe = _with_lifecycle_records(written, [stale_record])
    stale_probe["stale_position_count"] = 0
    stale_errors = validate_phase7_proof_lifecycle_monitor(stale_probe)

    failed_reconciliation_probe = _with_lifecycle_records(
        written,
        [_valid_lifecycle_record(state="submitted_order")],
    )
    failed_reconciliation_probe["failed_reconciliation_count"] = 1
    failed_reconciliation_probe[
        "phase7_certification_blocked_by_reconciliation_failure"
    ] = False
    failed_reconciliation_probe[
        "new_proof_lifecycle_actions_blocked_by_reconciliation_failure"
    ] = False
    failed_reconciliation_errors = validate_phase7_proof_lifecycle_monitor(
        failed_reconciliation_probe
    )

    postmortem_probe = _with_lifecycle_records(
        written,
        [_valid_lifecycle_record(state="closed_trade")],
    )
    postmortem_probe["postmortem_due_count"] = 1
    postmortem_errors = validate_phase7_proof_lifecycle_monitor(postmortem_probe)

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["authority_ledger"]["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase7_proof_lifecycle_monitor(proof_credit_probe)

    broker_post_probe = deepcopy(written)
    broker_post_probe["broker_post_allowed"] = True
    broker_post_probe["authority_ledger"]["broker_post_allowed"] = True
    broker_post_probe["broker_post_called_count"] = 1
    broker_post_errors = validate_phase7_proof_lifecycle_monitor(broker_post_probe)

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_probe["authority_ledger"]["live_capital_enabled"] = True
    live_capital_probe["live_capital_enabled_count"] = 1
    live_capital_errors = validate_phase7_proof_lifecycle_monitor(live_capital_probe)

    market_write_probe = deepcopy(written)
    market_write_probe["prediction_market_write_allowed"] = True
    market_write_probe["authority_ledger"]["prediction_market_write_allowed"] = True
    market_write_probe["prediction_market_write_allowed_count"] = 1
    market_write_probe["crypto_perps_write_allowed"] = True
    market_write_probe["authority_ledger"]["crypto_perps_write_allowed"] = True
    market_write_probe["crypto_perps_write_allowed_count"] = 1
    market_write_errors = validate_phase7_proof_lifecycle_monitor(market_write_probe)

    manual_override_probe = deepcopy(written)
    manual_override_probe["manual_trade_level_override_allowed"] = True
    manual_override_probe["authority_ledger"][
        "manual_trade_level_override_allowed"
    ] = True
    manual_override_probe["manual_trade_level_override_count"] = 1
    manual_override_errors = validate_phase7_proof_lifecycle_monitor(
        manual_override_probe
    )

    phase5_reuse_probe = _with_lifecycle_records(
        written,
        [_valid_lifecycle_record(state="submitted_order")],
    )
    phase5_reuse_probe["lifecycle_records"][0]["idempotency_key"] = "q5-reused"
    phase5_reuse_errors = validate_phase7_proof_lifecycle_monitor(phase5_reuse_probe)

    source_posture_probe = deepcopy(written)
    source_posture_probe["source_posture"][
        "preference_mcp_source_quorum_credit_allowed"
    ] = True
    source_posture_probe["source_posture"]["qctrl_role"] = "execution_truth"
    source_posture_errors = validate_phase7_proof_lifecycle_monitor(
        source_posture_probe
    )

    local_path_probe = deepcopy(written)
    local_path_probe["provenance"]["source_refs"] = [
        "/Users/raminhoodeh/Desktop/qadam/data/runtime/private.json"
    ]
    local_path_errors = validate_phase7_proof_lifecycle_monitor(local_path_probe)

    gate_probe = deepcopy(written)
    gate_probe["q7_8_proof_lifecycle_monitor_stage_allowed"] = False
    gate_errors = validate_phase7_proof_lifecycle_monitor(gate_probe)

    print(f"phase7_lifecycle_status={written['status']}")
    print(f"phase7_lifecycle_stage_status={written['stage_status']}")
    print(
        "phase7_lifecycle_schema_version="
        f"{PHASE7_PROOF_LIFECYCLE_SCHEMA_VERSION}"
    )
    print(f"phase7_lifecycle_artifact_path={output_path}")
    print(f"phase7_lifecycle_history_path={history_path}")
    print(f"phase7_lifecycle_event_log_path={event_log_path}")
    print(f"phase7_lifecycle_source_guarded_submit_status={written['source_guarded_submit_status']}")
    print(f"phase7_lifecycle_q7_9_postmortem_stage_allowed={written['q7_9_proof_postmortem_contract_stage_allowed']}")
    print(f"phase7_lifecycle_write_allowed={written['phase7_proof_lifecycle_write_allowed']}")
    print(f"phase7_lifecycle_source_submitted_paper_order_count={written['source_submitted_paper_order_count']}")
    print(f"phase7_lifecycle_event_count={written['lifecycle_event_count']}")
    print(f"phase7_lifecycle_mirrored_submitted_order_count={written['mirrored_submitted_order_count']}")
    print(f"phase7_lifecycle_open_position_count={written['open_position_count']}")
    print(f"phase7_lifecycle_exit_intent_count={written['exit_intent_count']}")
    print(f"phase7_lifecycle_closed_proof_trade_count={written['closed_proof_trade_count']}")
    print(f"phase7_lifecycle_proof_trade_count={written['proof_trade_count']}")
    print(f"phase7_lifecycle_postmortem_due_count={written['postmortem_due_count']}")
    print(f"phase7_lifecycle_missing_broker_echo_count={written['missing_broker_echo_count']}")
    print(f"phase7_lifecycle_duplicate_fill_count={written['duplicate_fill_count']}")
    print(f"phase7_lifecycle_stale_position_count={written['stale_position_count']}")
    print(f"phase7_lifecycle_failed_reconciliation_count={written['failed_reconciliation_count']}")
    print(f"phase7_lifecycle_phase7_proof_credit_allowed={written['phase7_proof_credit_allowed']}")
    print(f"phase7_lifecycle_live_capital_enabled={written['live_capital_enabled']}")
    print(f"phase7_lifecycle_broker_post_called_count={written['broker_post_called_count']}")
    print(f"phase7_lifecycle_alpaca_post_called_count={written['alpaca_post_called_count']}")
    print(f"phase7_lifecycle_unsafe_write_counter_total={written['unsafe_write_counter_total']}")
    print(f"phase7_lifecycle_blocker_count={written['blocker_count']}")
    print(f"phase7_lifecycle_event_log_replay_total_events={replay['total_events']}")
    print(f"phase7_lifecycle_guarded_event_log_path={guarded_event_path}")
    print(f"phase7_lifecycle_guarded_submit_error_count={len(guarded_errors)}")
    print(f"phase7_lifecycle_valid_submitted_probe_error_count={len(valid_submitted_errors)}")
    print(f"phase7_lifecycle_valid_closed_probe_error_count={len(valid_closed_errors)}")
    print(f"phase7_lifecycle_missing_echo_probe_error_count={len(missing_echo_errors)}")
    print(f"phase7_lifecycle_duplicate_probe_error_count={len(duplicate_errors)}")
    print(f"phase7_lifecycle_stale_position_probe_error_count={len(stale_errors)}")
    print(f"phase7_lifecycle_failed_reconciliation_probe_error_count={len(failed_reconciliation_errors)}")
    print(f"phase7_lifecycle_postmortem_probe_error_count={len(postmortem_errors)}")
    print(f"phase7_lifecycle_proof_credit_probe_error_count={len(proof_credit_errors)}")
    print(f"phase7_lifecycle_broker_post_probe_error_count={len(broker_post_errors)}")
    print(f"phase7_lifecycle_live_capital_probe_error_count={len(live_capital_errors)}")
    print(f"phase7_lifecycle_market_write_probe_error_count={len(market_write_errors)}")
    print(f"phase7_lifecycle_manual_override_probe_error_count={len(manual_override_errors)}")
    print(f"phase7_lifecycle_phase5_reuse_probe_error_count={len(phase5_reuse_errors)}")
    print(f"phase7_lifecycle_source_posture_probe_error_count={len(source_posture_errors)}")
    print(f"phase7_lifecycle_local_path_probe_error_count={len(local_path_errors)}")
    print(f"phase7_lifecycle_gate_probe_error_count={len(gate_errors)}")
    print(f"phase7_lifecycle_next_stage={written['recommended_next_stage']}")
    print("phase7_lifecycle_boundary=" + written["boundary"])

    if guarded_errors:
        errors.extend(guarded_errors)
    if validation_errors:
        errors.extend(validation_errors)
    if runtime_copy.get("artifact_id") != written["artifact_id"]:
        errors.append("runtime_phase7_lifecycle_not_written")
    has_lifecycle_event = written["lifecycle_event_count"] > 0
    expected_status = (
        "proof_lifecycle_events_recorded"
        if has_lifecycle_event
        else "ready_no_lifecycle_events"
    )
    expected_stage_status = (
        "proof_lifecycle_events_recorded"
        if has_lifecycle_event
        else "proof_lifecycle_monitor_ready_no_submitted_orders"
    )
    if written["status"] != expected_status:
        errors.append("phase7_lifecycle_status_invalid")
    if written["stage_status"] != expected_stage_status:
        errors.append("phase7_lifecycle_stage_status_invalid")
    if written["phase7_proof_lifecycle_write_allowed"] is not True:
        errors.append("phase7_lifecycle_write_authority_missing")
    if written["q7_9_proof_postmortem_contract_stage_allowed"] is not True:
        errors.append("phase7_lifecycle_q7_9_not_allowed")
    if has_lifecycle_event:
        if written["source_submitted_paper_order_count"] != written["lifecycle_event_count"]:
            errors.append("phase7_lifecycle_source_event_count_mismatch")
        if written["proof_trade_count"] != written["lifecycle_event_count"]:
            errors.append("phase7_lifecycle_proof_trade_count_mismatch")
        if written["mirrored_submitted_order_count"] != written["lifecycle_event_count"]:
            errors.append("phase7_lifecycle_mirrored_order_count_mismatch")
    for count_key in (
        "open_position_count",
        "exit_intent_count",
        "closed_proof_trade_count",
        "postmortem_due_count",
        "missing_broker_echo_count",
        "duplicate_fill_count",
        "stale_position_count",
        "failed_reconciliation_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
        "unsafe_write_counter_total",
        "blocker_count",
    ):
        if written[count_key] != 0:
            errors.append(f"phase7_lifecycle_count_nonzero:{count_key}")
    for flag_key in (
        "phase7_proof_trade_execution_allowed",
        "phase7_postmortem_write_allowed",
        "phase7_proof_credit_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "manual_trade_level_override_allowed",
    ):
        if written[flag_key] is not False:
            errors.append(f"phase7_lifecycle_forbidden_authority:{flag_key}")
    if written["event_log_written"] is not True:
        errors.append("phase7_lifecycle_event_log_not_written")
    if replay["total_events"] != 1:
        errors.append("phase7_lifecycle_event_log_replay_count_mismatch")
    if valid_submitted_errors:
        errors.append("valid_submitted_lifecycle_probe_rejected")
    if valid_closed_errors:
        errors.append("valid_closed_lifecycle_probe_rejected")
    if "phase7_lifecycle_record_broker_echo_missing" not in missing_echo_errors:
        errors.append("missing_broker_echo_probe_not_rejected")
    if "phase7_lifecycle_duplicate_fill_count_mismatch" not in duplicate_errors:
        errors.append("duplicate_fill_probe_not_rejected")
    if "phase7_lifecycle_stale_position_count_mismatch" not in stale_errors:
        errors.append("stale_position_probe_not_rejected")
    if "phase7_lifecycle_failed_reconciliation_count_mismatch" not in (
        failed_reconciliation_errors
    ):
        errors.append("failed_reconciliation_count_probe_not_rejected")
    if "phase7_lifecycle_postmortem_due_count_nonzero" not in postmortem_errors:
        errors.append("postmortem_due_probe_not_rejected")
    if "phase7_lifecycle_authority_invalid:phase7_proof_credit_allowed" not in (
        proof_credit_errors
    ):
        errors.append("proof_credit_authority_probe_not_rejected")
    if "phase7_lifecycle_unsafe_count_nonzero:phase7_proof_credit_allowed_count" not in (
        proof_credit_errors
    ):
        errors.append("proof_credit_count_probe_not_rejected")
    if "phase7_lifecycle_authority_invalid:broker_post_allowed" not in (
        broker_post_errors
    ):
        errors.append("broker_post_authority_probe_not_rejected")
    if "phase7_lifecycle_count_nonzero:broker_post_called_count" not in (
        broker_post_errors
    ):
        errors.append("broker_post_count_probe_not_rejected")
    if "phase7_lifecycle_authority_invalid:live_capital_enabled" not in (
        live_capital_errors
    ):
        errors.append("live_capital_authority_probe_not_rejected")
    if "phase7_lifecycle_unsafe_count_nonzero:live_capital_enabled_count" not in (
        live_capital_errors
    ):
        errors.append("live_capital_count_probe_not_rejected")
    if "phase7_lifecycle_authority_invalid:prediction_market_write_allowed" not in (
        market_write_errors
    ):
        errors.append("prediction_market_authority_probe_not_rejected")
    if "phase7_lifecycle_authority_invalid:crypto_perps_write_allowed" not in (
        market_write_errors
    ):
        errors.append("crypto_perps_authority_probe_not_rejected")
    if "phase7_lifecycle_authority_invalid:manual_trade_level_override_allowed" not in (
        manual_override_errors
    ):
        errors.append("manual_override_authority_probe_not_rejected")
    if "phase7_lifecycle_idempotency_key_invalid" not in phase5_reuse_errors:
        errors.append("phase5_idempotency_probe_not_rejected")
    if "phase7_lifecycle_phase5_idempotency_reuse" not in phase5_reuse_errors:
        errors.append("phase5_reuse_probe_not_rejected")
    if "phase7_lifecycle_preference_quorum_credit_allowed" not in source_posture_errors:
        errors.append("source_posture_preference_probe_not_rejected")
    if "phase7_lifecycle_qctrl_role_invalid" not in source_posture_errors:
        errors.append("source_posture_qctrl_probe_not_rejected")
    if "phase7_lifecycle_provenance_local_path_leak" not in local_path_errors:
        errors.append("local_path_probe_not_rejected")
    if "q7_8_proof_lifecycle_monitor_not_allowed" not in gate_errors:
        errors.append("gate_probe_not_rejected")

    if errors:
        for error in sorted(set(errors)):
            print(f"phase7_lifecycle_error={error}")
        print("phase7_proof_lifecycle_monitor_check=failed")
        return 1

    print("phase7_proof_lifecycle_monitor_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
