#!/usr/bin/env python3
"""Validate Q7-6 Phase 7 Demo Proof order staging and idempotency."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase7_proof_order_staging import (  # noqa: E402
    PHASE7_PROOF_ORDER_STAGING_REQUIRED_CHECKS,
    PHASE7_PROOF_ORDER_STAGING_SCHEMA_VERSION,
    build_phase7_proof_order_staging,
    phase7_proof_order_staging_paths,
    validate_phase7_proof_order_staging,
    write_phase7_proof_order_staging,
)
from orchestrator.release_contract import PAPER_ACCOUNT_BALANCE_GBP  # noqa: E402
from orchestrator.phase7_readiness import (  # noqa: E402
    build_phase7_readiness,
    validate_phase7_readiness,
)
from orchestrator.phase7_test_mode_auto_approval import (  # noqa: E402
    build_phase7_test_mode_auto_approval_router,
    validate_phase7_test_mode_auto_approval_router,
)


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _valid_staged_record() -> dict[str, object]:
    checks = [
        {"name": name, "passed": True, "detail": None}
        for name in PHASE7_PROOF_ORDER_STAGING_REQUIRED_CHECKS
    ]
    prewrite_payload = {
        "schema_version": PHASE7_PROOF_ORDER_STAGING_SCHEMA_VERSION,
        "prewrite_type": "phase7_staged_proof_order_prewrite",
        "artifact_id": "phase7:q7-6:staged-proof-order:probe_q7_setup",
        "proof_order_id": "q7-proof-order-probe0000001",
        "idempotency_namespace": "phase7_demo_proof",
        "source_auto_approval_decision_id": "probe:auto-approval:q7-setup",
        "source_setup_record_id": "probe:q7-setup",
        "selected_venue": "alpaca_paper",
        "instrument": "spy",
        "side": "buy",
        "quantity": "1.00000000",
        "order_type": "market",
        "time_in_force": "day",
        "paper_submit_allowed": False,
        "broker_post_allowed": False,
        "live_capital_enabled": False,
    }
    return {
        "schema_version": 1,
        "proof_order_staging_schema_version": PHASE7_PROOF_ORDER_STAGING_SCHEMA_VERSION,
        "artifact_type": "staged_proof_order",
        "artifact_id": "phase7:q7-6:staged-proof-order:probe_q7_setup",
        "phase": "Q7",
        "stage": "Q7-6",
        "status": "staged",
        "order_state": "staged_ready_for_guarded_paper_submit",
        "public_safe": True,
        "source_auto_approval_decision_id": "probe:auto-approval:q7-setup",
        "source_setup_record_id": "probe:q7-setup",
        "source_decision_state": "auto_approved",
        "source_auto_approved": True,
        "qualified_setup": True,
        "source_phase": "Q7",
        "source_quorum_passed": True,
        "all_required_gates_passed": True,
        "risk_gate_passed": True,
        "execution_policy_gate_passed": True,
        "kill_switches_clear": True,
        "venue_available": True,
        "broker_paper_ready": True,
        "strategy_family_key": "probe_strategy",
        "selected_venue": "alpaca_paper",
        "instrument": "spy",
        "side": "buy",
        "quantity": 1.0,
        "order_type": "market",
        "time_in_force": "day",
        "proof_order_id": "q7-proof-order-probe0000001",
        "idempotency_namespace": "phase7_demo_proof",
        "idempotency_material": {
            "stage": "Q7-6",
            "idempotency_namespace": "phase7_demo_proof",
            "source_auto_approval_decision_id": "probe:auto-approval:q7-setup",
            "source_setup_record_id": "probe:q7-setup",
            "strategy_family_key": "probe_strategy",
            "instrument": "spy",
            "selected_venue": "alpaca_paper",
            "side": "buy",
            "quantity": "1.00000000",
            "order_type": "market",
            "time_in_force": "day",
            "fingerprint": "probe0000001",
        },
        "idempotency_key": "q7-6-stage-probe0000001",
        "idempotency_reused_from_phase5": False,
        "phase5_order_id_reused": False,
        "phase5_order_id": None,
        "pre_trade_snapshot_required": True,
        "pre_trade_snapshot_present": True,
        "pre_trade_snapshot": {
            "snapshot_schema_version": PHASE7_PROOF_ORDER_STAGING_SCHEMA_VERSION,
            "snapshot_type": "phase7_pre_trade_snapshot",
            "source_auto_approval_decision_id": "probe:auto-approval:q7-setup",
            "source_setup_record_id": "probe:q7-setup",
            "strategy_family_key": "probe_strategy",
            "instrument": "spy",
            "selected_venue": "alpaca_paper",
            "paper_account_starting_gbp": float(PAPER_ACCOUNT_BALANCE_GBP),
            "max_drawdown_fraction": 0.2,
            "source_quorum_passed": True,
            "risk_gate_passed": True,
            "kill_switches_clear": True,
            "broker_identifier_exposed": False,
            "raw_payload_exposed": False,
            "local_path_exposed": False,
        },
        "event_log_prewrite_required": True,
        "event_log_prewrite_ready": True,
        "event_log_prewrite_written": True,
        "event_log_prewrite_payload": prewrite_payload,
        "event_log_prewrite_fingerprint": "probe-prewrite-fingerprint",
        "event_log_prewrite_correlation_id": "probe-correlation-id",
        "event_log_prewrite_created_at": "2026-05-25T00:00:00+00:00",
        "staged_order_created": True,
        "paper_submit_allowed": False,
        "broker_submit_ready": False,
        "broker_post_allowed": False,
        "alpaca_post_allowed": False,
        "broker_write_allowed": False,
        "prediction_market_write_allowed": False,
        "crypto_perps_write_allowed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
        "proof_trade_created": False,
        "proof_credit_allowed": False,
        "manual_trade_level_override_allowed": False,
        "required_checks": list(PHASE7_PROOF_ORDER_STAGING_REQUIRED_CHECKS),
        "required_check_count": len(PHASE7_PROOF_ORDER_STAGING_REQUIRED_CHECKS),
        "checks": checks,
        "failed_checks": [],
        "failed_check_count": 0,
        "blocked_reasons": [],
        "blocked_reason_count": 0,
        "cancellation_conditions": [
            "source_auto_approval_retracted",
            "source_setup_expires_before_submit",
            "risk_or_policy_gate_retracted",
            "kill_switch_activates_after_staging",
            "broker_paper_readiness_degrades_before_submit",
            "idempotency_collision_detected",
            "pre_trade_snapshot_stale_before_submit",
        ],
        "cancellation_condition_count": 7,
    }


def _with_valid_staged_order(artifact: dict[str, object]) -> dict[str, object]:
    probe = deepcopy(artifact)
    record = _valid_staged_record()
    records = list(probe["staging_decision_records"])
    records.append(record)
    probe["staging_decision_records"] = records
    probe["staged_order_records"] = [record]
    probe["status"] = "staged_orders_recorded"
    probe["stage_status"] = "proof_order_staging_records_written"
    probe["source_auto_approval_status"] = "auto_approval_ready"
    probe["source_auto_approved_setup_count"] = 1
    probe["auto_approved_setup_count"] = 1
    probe["qualified_setup_count"] = 1
    probe["staging_decision_record_count"] = len(records)
    probe["staged_order_count"] = 1
    probe["proof_order_staged_count"] = 1
    probe["blocked_staging_decision_count"] = sum(
        1 for item in records if isinstance(item, dict) and item.get("status") == "blocked"
    )
    probe["idempotency_key_count"] = 1
    probe["duplicate_idempotency_key_count"] = 0
    probe["duplicate_proof_order_id_count"] = 0
    probe["phase5_order_id_reuse_count"] = 0
    probe["event_log_prewrite_ready_count"] = 1
    probe["event_log_prewrite_written_count"] = 1
    probe["pre_trade_snapshot_present_count"] = 1
    return probe


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = phase7_proof_order_staging_paths(
        settings
    )
    if event_log_path.exists():
        event_log_path.unlink()

    readiness = build_phase7_readiness(settings=settings)
    readiness_errors = validate_phase7_readiness(readiness)
    auto_approval = build_phase7_test_mode_auto_approval_router(settings=settings)
    auto_approval_errors = validate_phase7_test_mode_auto_approval_router(
        auto_approval
    )
    artifact = build_phase7_proof_order_staging(settings=settings)
    output_path, history_path, event_log_path, written = write_phase7_proof_order_staging(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase7_proof_order_staging(written)
    replay = EventLog(event_log_path, echo=False).replay()
    runtime_copy = _read_json(output_path)

    valid_staged_probe = _with_valid_staged_order(written)
    valid_staged_errors = validate_phase7_proof_order_staging(valid_staged_probe)

    duplicate_probe = _with_valid_staged_order(written)
    duplicate_record = deepcopy(duplicate_probe["staged_order_records"][0])
    duplicate_probe["staging_decision_records"].append(duplicate_record)
    duplicate_probe["staged_order_records"].append(duplicate_record)
    duplicate_probe["staging_decision_record_count"] += 1
    duplicate_probe["staged_order_count"] += 1
    duplicate_probe["proof_order_staged_count"] += 1
    duplicate_probe["auto_approved_setup_count"] = 2
    duplicate_probe["duplicate_idempotency_key_count"] = 1
    duplicate_probe["duplicate_proof_order_id_count"] = 1
    duplicate_probe["idempotency_key_count"] = 2
    duplicate_probe["event_log_prewrite_ready_count"] = 2
    duplicate_probe["event_log_prewrite_written_count"] = 2
    duplicate_probe["pre_trade_snapshot_present_count"] = 2
    duplicate_errors = validate_phase7_proof_order_staging(duplicate_probe)

    non_approved_probe = _with_valid_staged_order(written)
    non_approved_probe["staged_order_records"][0]["source_auto_approved"] = False
    non_approved_probe["staging_decision_records"][-1]["source_auto_approved"] = False
    non_approved_errors = validate_phase7_proof_order_staging(non_approved_probe)

    phase5_reuse_probe = _with_valid_staged_order(written)
    phase5_reuse_probe["staged_order_records"][0]["idempotency_key"] = "q5-6-stage-reused"
    phase5_reuse_probe["staged_order_records"][0]["phase5_order_id_reused"] = True
    phase5_reuse_probe["staged_order_records"][0]["phase5_order_id"] = "phase5-order-1"
    phase5_reuse_probe["staging_decision_records"][-1] = phase5_reuse_probe[
        "staged_order_records"
    ][0]
    phase5_reuse_probe["phase5_order_id_reuse_count"] = 1
    phase5_reuse_errors = validate_phase7_proof_order_staging(phase5_reuse_probe)

    prewrite_probe = _with_valid_staged_order(written)
    prewrite_probe["staged_order_records"][0]["event_log_prewrite_ready"] = False
    prewrite_probe["staged_order_records"][0]["event_log_prewrite_written"] = False
    prewrite_probe["staging_decision_records"][-1] = prewrite_probe["staged_order_records"][0]
    prewrite_probe["event_log_prewrite_ready_count"] = 0
    prewrite_probe["event_log_prewrite_written_count"] = 0
    prewrite_errors = validate_phase7_proof_order_staging(prewrite_probe)

    snapshot_probe = _with_valid_staged_order(written)
    snapshot_probe["staged_order_records"][0]["pre_trade_snapshot_present"] = False
    snapshot_probe["staged_order_records"][0]["pre_trade_snapshot"] = None
    snapshot_probe["staging_decision_records"][-1] = snapshot_probe["staged_order_records"][0]
    snapshot_probe["pre_trade_snapshot_present_count"] = 0
    snapshot_errors = validate_phase7_proof_order_staging(snapshot_probe)

    submit_probe = deepcopy(written)
    submit_probe["phase7_proof_trade_submission_allowed"] = True
    submit_probe["authority_ledger"]["phase7_proof_trade_submission_allowed"] = True
    submit_probe["paper_order_submitted_count"] = 1
    submit_errors = validate_phase7_proof_order_staging(submit_probe)

    broker_probe = deepcopy(written)
    broker_probe["broker_post_allowed"] = True
    broker_probe["authority_ledger"]["broker_post_allowed"] = True
    broker_probe["broker_post_called_count"] = 1
    broker_probe["live_endpoint_allowed"] = True
    broker_probe["authority_ledger"]["live_endpoint_allowed"] = True
    broker_errors = validate_phase7_proof_order_staging(broker_probe)

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_probe["authority_ledger"]["live_capital_enabled"] = True
    live_capital_probe["live_capital_enabled_count"] = 1
    live_capital_errors = validate_phase7_proof_order_staging(live_capital_probe)

    market_write_probe = deepcopy(written)
    market_write_probe["prediction_market_write_allowed"] = True
    market_write_probe["authority_ledger"]["prediction_market_write_allowed"] = True
    market_write_probe["prediction_market_write_allowed_count"] = 1
    market_write_probe["crypto_perps_write_allowed"] = True
    market_write_probe["authority_ledger"]["crypto_perps_write_allowed"] = True
    market_write_probe["crypto_perps_write_allowed_count"] = 1
    market_write_errors = validate_phase7_proof_order_staging(market_write_probe)

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["authority_ledger"]["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase7_proof_order_staging(proof_credit_probe)

    manual_override_probe = deepcopy(written)
    manual_override_probe["manual_trade_level_override_allowed"] = True
    manual_override_probe["authority_ledger"][
        "manual_trade_level_override_allowed"
    ] = True
    manual_override_probe["manual_trade_level_override_count"] = 1
    manual_override_errors = validate_phase7_proof_order_staging(manual_override_probe)

    source_posture_probe = deepcopy(written)
    source_posture_probe["source_posture"][
        "preference_mcp_source_quorum_credit_allowed"
    ] = True
    source_posture_probe["source_posture"]["qctrl_role"] = "execution_truth"
    source_posture_errors = validate_phase7_proof_order_staging(source_posture_probe)

    local_path_probe = deepcopy(written)
    local_path_probe["provenance"]["source_refs"] = [
        "/Users/raminhoodeh/Desktop/qadam/data/runtime/private.json"
    ]
    local_path_errors = validate_phase7_proof_order_staging(local_path_probe)

    gate_probe = deepcopy(written)
    gate_probe["q7_6_proof_order_staging_stage_allowed"] = False
    gate_errors = validate_phase7_proof_order_staging(gate_probe)

    print(f"phase7_proof_order_staging_status={written['status']}")
    print(f"phase7_proof_order_staging_stage_status={written['stage_status']}")
    print(
        "phase7_proof_order_staging_schema_version="
        f"{PHASE7_PROOF_ORDER_STAGING_SCHEMA_VERSION}"
    )
    print(f"phase7_proof_order_staging_artifact_path={output_path}")
    print(f"phase7_proof_order_staging_history_path={history_path}")
    print(f"phase7_proof_order_staging_event_log_path={event_log_path}")
    print(
        "phase7_proof_order_staging_source_auto_approval_status="
        f"{written['source_auto_approval_status']}"
    )
    print(
        "phase7_proof_order_staging_allowed="
        f"{written['proof_order_staging_allowed']}"
    )
    print(
        "phase7_proof_order_staging_phase7_proof_order_staging_allowed="
        f"{written['phase7_proof_order_staging_allowed']}"
    )
    print(
        "phase7_proof_order_staging_q7_7_guarded_alpaca_stage_allowed="
        f"{written['q7_7_guarded_alpaca_paper_submit_path_stage_allowed']}"
    )
    print(
        "phase7_proof_order_staging_decision_record_count="
        f"{written['staging_decision_record_count']}"
    )
    print(f"phase7_proof_order_staging_staged_order_count={written['staged_order_count']}")
    print(
        "phase7_proof_order_staging_blocked_decision_count="
        f"{written['blocked_staging_decision_count']}"
    )
    print(
        "phase7_proof_order_staging_auto_approved_setup_count="
        f"{written['auto_approved_setup_count']}"
    )
    print(
        "phase7_proof_order_staging_idempotency_key_count="
        f"{written['idempotency_key_count']}"
    )
    print(
        "phase7_proof_order_staging_duplicate_idempotency_key_count="
        f"{written['duplicate_idempotency_key_count']}"
    )
    print(
        "phase7_proof_order_staging_phase5_order_id_reuse_count="
        f"{written['phase5_order_id_reuse_count']}"
    )
    print(
        "phase7_proof_order_staging_event_log_prewrite_ready_count="
        f"{written['event_log_prewrite_ready_count']}"
    )
    print(
        "phase7_proof_order_staging_event_log_prewrite_written_count="
        f"{written['event_log_prewrite_written_count']}"
    )
    print(
        "phase7_proof_order_staging_pre_trade_snapshot_present_count="
        f"{written['pre_trade_snapshot_present_count']}"
    )
    print(f"phase7_proof_order_staging_proof_trade_count={written['proof_trade_count']}")
    print(
        "phase7_proof_order_staging_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(f"phase7_proof_order_staging_broker_post_allowed={written['broker_post_allowed']}")
    print(f"phase7_proof_order_staging_live_capital_enabled={written['live_capital_enabled']}")
    print(
        "phase7_proof_order_staging_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(f"phase7_proof_order_staging_blocker_count={written['blocker_count']}")
    print(f"phase7_proof_order_staging_event_log_replay_total_events={replay['total_events']}")
    print(f"phase7_proof_order_staging_readiness_error_count={len(readiness_errors)}")
    print(
        "phase7_proof_order_staging_auto_approval_error_count="
        f"{len(auto_approval_errors)}"
    )
    print(
        "phase7_proof_order_staging_valid_staged_probe_error_count="
        f"{len(valid_staged_errors)}"
    )
    print(
        "phase7_proof_order_staging_duplicate_probe_error_count="
        f"{len(duplicate_errors)}"
    )
    print(
        "phase7_proof_order_staging_non_approved_probe_error_count="
        f"{len(non_approved_errors)}"
    )
    print(
        "phase7_proof_order_staging_phase5_reuse_probe_error_count="
        f"{len(phase5_reuse_errors)}"
    )
    print(f"phase7_proof_order_staging_prewrite_probe_error_count={len(prewrite_errors)}")
    print(f"phase7_proof_order_staging_snapshot_probe_error_count={len(snapshot_errors)}")
    print(f"phase7_proof_order_staging_submit_probe_error_count={len(submit_errors)}")
    print(f"phase7_proof_order_staging_broker_probe_error_count={len(broker_errors)}")
    print(
        "phase7_proof_order_staging_live_capital_probe_error_count="
        f"{len(live_capital_errors)}"
    )
    print(
        "phase7_proof_order_staging_market_write_probe_error_count="
        f"{len(market_write_errors)}"
    )
    print(
        "phase7_proof_order_staging_proof_credit_probe_error_count="
        f"{len(proof_credit_errors)}"
    )
    print(
        "phase7_proof_order_staging_manual_override_probe_error_count="
        f"{len(manual_override_errors)}"
    )
    print(
        "phase7_proof_order_staging_source_posture_probe_error_count="
        f"{len(source_posture_errors)}"
    )
    print(f"phase7_proof_order_staging_local_path_probe_error_count={len(local_path_errors)}")
    print(f"phase7_proof_order_staging_gate_probe_error_count={len(gate_errors)}")
    print(f"phase7_proof_order_staging_next_stage={written['recommended_next_stage']}")
    print("phase7_proof_order_staging_boundary=" + written["boundary"])

    if readiness_errors:
        errors.extend(readiness_errors)
    if auto_approval_errors:
        errors.extend(auto_approval_errors)
    if validation_errors:
        errors.extend(validation_errors)
    if runtime_copy.get("artifact_id") != written["artifact_id"]:
        errors.append("runtime_phase7_proof_order_staging_not_written")
    has_staged_order = written["staged_order_count"] > 0
    expected_status = (
        "staged_orders_recorded" if has_staged_order else "ready_no_staged_orders"
    )
    expected_stage_status = (
        "proof_order_staging_records_written"
        if has_staged_order
        else "proof_order_staging_ready_no_auto_approved_setups"
    )
    if written["status"] != expected_status:
        errors.append("phase7_proof_order_staging_status_invalid")
    if written["stage_status"] != expected_stage_status:
        errors.append("phase7_proof_order_staging_stage_status_invalid")
    if written["proof_order_staging_allowed"] is not True:
        errors.append("phase7_proof_order_staging_not_allowed")
    if written["phase7_proof_order_staging_allowed"] is not True:
        errors.append("phase7_proof_order_staging_authority_not_granted")
    if written["q7_7_guarded_alpaca_paper_submit_path_stage_allowed"] is not True:
        errors.append("phase7_proof_order_staging_q7_7_not_allowed")
    expected_decision_count = written["source_approval_decision_record_count"]
    if written["staging_decision_record_count"] != expected_decision_count:
        errors.append("phase7_proof_order_staging_decision_count_mismatch")
    if written["staged_order_count"] != written["auto_approved_setup_count"]:
        errors.append("phase7_proof_order_staging_staged_order_count_mismatch")
    expected_blocked_count = (
        written["staging_decision_record_count"] - written["staged_order_count"]
    )
    if written["blocked_staging_decision_count"] != expected_blocked_count:
        errors.append("phase7_proof_order_staging_blocked_decision_count_mismatch")
    if has_staged_order:
        for count_key in (
            "idempotency_key_count",
            "event_log_prewrite_ready_count",
            "event_log_prewrite_written_count",
            "pre_trade_snapshot_present_count",
        ):
            if written[count_key] != written["staged_order_count"]:
                errors.append(f"phase7_proof_order_staging_count_mismatch:{count_key}")
    for count_key in (
        "duplicate_idempotency_key_count",
        "phase5_order_id_reuse_count",
        "proof_trade_count",
        "unsafe_write_counter_total",
        "blocker_count",
    ):
        if written[count_key] != 0:
            errors.append(f"phase7_proof_order_staging_count_nonzero:{count_key}")
    for flag_key in (
        "phase7_proof_trade_submission_allowed",
        "phase7_proof_trade_execution_allowed",
        "phase7_proof_credit_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "manual_trade_level_override_allowed",
    ):
        if written[flag_key] is not False:
            errors.append(f"phase7_proof_order_staging_forbidden_authority:{flag_key}")
    if written["event_log_written"] is not True:
        errors.append("phase7_proof_order_staging_event_log_not_written")
    if replay["total_events"] != 1:
        errors.append("phase7_proof_order_staging_event_log_replay_count_mismatch")

    if not has_staged_order and valid_staged_errors:
        errors.append("valid_staged_probe_rejected")
    if "proof_order_staging_duplicate_idempotency_key" not in duplicate_errors:
        errors.append("duplicate_idempotency_probe_not_rejected")
    if "proof_order_staging_duplicate_proof_order_id" not in duplicate_errors:
        errors.append("duplicate_order_probe_not_rejected")
    if "proof_order_staging_staged_without_auto_approval" not in non_approved_errors:
        errors.append("non_approved_staged_probe_not_rejected")
    if "proof_order_staging_idempotency_key_invalid" not in phase5_reuse_errors:
        errors.append("phase5_idempotency_probe_not_rejected")
    if "proof_order_staging_phase5_order_id_reused" not in phase5_reuse_errors:
        errors.append("phase5_order_reuse_probe_not_rejected")
    if "proof_order_staging_phase5_order_id_reuse" not in phase5_reuse_errors:
        errors.append("phase5_reuse_count_probe_not_rejected")
    if "proof_order_staging_event_log_prewrite_not_ready" not in prewrite_errors:
        errors.append("prewrite_probe_not_rejected")
    if "proof_order_staging_event_log_prewrite_not_written" not in prewrite_errors:
        errors.append("prewrite_written_probe_not_rejected")
    if "proof_order_staging_pre_trade_snapshot_missing" not in snapshot_errors:
        errors.append("snapshot_probe_not_rejected")
    if "proof_order_staging_pre_trade_snapshot_invalid" not in snapshot_errors:
        errors.append("snapshot_invalid_probe_not_rejected")
    if "proof_order_staging_authority_invalid:phase7_proof_trade_submission_allowed" not in (
        submit_errors
    ):
        errors.append("submit_authority_probe_not_rejected")
    if "proof_order_staging_count_nonzero:paper_order_submitted_count" not in (
        submit_errors
    ):
        errors.append("submit_count_probe_not_rejected")
    if "proof_order_staging_authority_invalid:broker_post_allowed" not in broker_errors:
        errors.append("broker_authority_probe_not_rejected")
    if "proof_order_staging_authority_invalid:live_endpoint_allowed" not in broker_errors:
        errors.append("live_endpoint_authority_probe_not_rejected")
    if "proof_order_staging_unsafe_count_nonzero:broker_post_called_count" not in (
        broker_errors
    ):
        errors.append("broker_count_probe_not_rejected")
    if "proof_order_staging_authority_invalid:live_capital_enabled" not in (
        live_capital_errors
    ):
        errors.append("live_capital_authority_probe_not_rejected")
    if "proof_order_staging_unsafe_count_nonzero:live_capital_enabled_count" not in (
        live_capital_errors
    ):
        errors.append("live_capital_count_probe_not_rejected")
    if (
        "proof_order_staging_authority_invalid:prediction_market_write_allowed"
        not in market_write_errors
    ):
        errors.append("prediction_market_authority_probe_not_rejected")
    if "proof_order_staging_authority_invalid:crypto_perps_write_allowed" not in (
        market_write_errors
    ):
        errors.append("crypto_perps_authority_probe_not_rejected")
    if "proof_order_staging_authority_invalid:phase7_proof_credit_allowed" not in (
        proof_credit_errors
    ):
        errors.append("proof_credit_authority_probe_not_rejected")
    if "proof_order_staging_unsafe_count_nonzero:phase7_proof_credit_allowed_count" not in (
        proof_credit_errors
    ):
        errors.append("proof_credit_count_probe_not_rejected")
    if "proof_order_staging_authority_invalid:manual_trade_level_override_allowed" not in (
        manual_override_errors
    ):
        errors.append("manual_override_authority_probe_not_rejected")
    if "proof_order_staging_unsafe_count_nonzero:manual_trade_level_override_count" not in (
        manual_override_errors
    ):
        errors.append("manual_override_count_probe_not_rejected")
    if "proof_order_staging_preference_quorum_credit_allowed" not in source_posture_errors:
        errors.append("source_posture_preference_probe_not_rejected")
    if "proof_order_staging_qctrl_role_invalid" not in source_posture_errors:
        errors.append("source_posture_qctrl_probe_not_rejected")
    if "proof_order_staging_provenance_local_path_leak" not in local_path_errors:
        errors.append("local_path_probe_not_rejected")
    if "q7_6_proof_order_staging_not_allowed" not in gate_errors:
        errors.append("gate_probe_not_rejected")

    if errors:
        for error in sorted(set(errors)):
            print(f"phase7_proof_order_staging_error={error}")
        print("phase7_proof_order_staging_check=failed")
        return 1

    print("phase7_proof_order_staging_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
