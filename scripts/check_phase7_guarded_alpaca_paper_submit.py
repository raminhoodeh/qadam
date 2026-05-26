#!/usr/bin/env python3
"""Validate Q7-7 Phase 7 Demo Proof guarded Alpaca paper submit path."""

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
from orchestrator.phase7_guarded_alpaca_paper_submit import (  # noqa: E402
    PHASE7_ALPACA_PAPER_SUBMIT_PATH_KEY,
    PHASE7_GUARDED_ALPACA_SUBMIT_REQUIRED_CHECKS,
    PHASE7_GUARDED_ALPACA_SUBMIT_SCHEMA_VERSION,
    build_phase7_guarded_alpaca_paper_submit_path,
    phase7_guarded_alpaca_submit_paths,
    validate_phase7_guarded_alpaca_paper_submit_path,
    write_phase7_guarded_alpaca_paper_submit_path,
)
from orchestrator.phase7_proof_order_staging import (  # noqa: E402
    build_phase7_proof_order_staging,
    validate_phase7_proof_order_staging,
)
from orchestrator.phase7_readiness import (  # noqa: E402
    build_phase7_readiness,
    validate_phase7_readiness,
)


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _submit_path() -> dict[str, object]:
    return {
        "path_key": PHASE7_ALPACA_PAPER_SUBMIT_PATH_KEY,
        "adapter": "alpaca",
        "selected_venue": "alpaca_paper",
        "account_mode_required": "paper",
        "endpoint_classification": "alpaca_paper_endpoint",
        "paper_only": True,
        "available": True,
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
        "boundary": "Q7-7 synthetic submit path for contract validation.",
    }


def _valid_submit_record() -> dict[str, object]:
    checks = [
        {"name": name, "passed": True, "detail": None}
        for name in PHASE7_GUARDED_ALPACA_SUBMIT_REQUIRED_CHECKS
    ]
    request_payload = {
        "schema_version": PHASE7_GUARDED_ALPACA_SUBMIT_SCHEMA_VERSION,
        "request_type": "phase7_alpaca_paper_order_request",
        "source_staged_order_artifact_id": "phase7:q7-6:staged-proof-order:probe",
        "proof_order_id": "q7-proof-order-probe0001",
        "source_auto_approval_decision_id": "probe:auto-approval:q7-setup",
        "source_setup_record_id": "probe:q7-setup",
        "idempotency_key": "q7-6-stage-probe0001",
        "idempotency_namespace": "phase7_demo_proof",
        "selected_venue": "alpaca_paper",
        "instrument": "spy",
        "symbol": "SPY",
        "side": "buy",
        "qty": "1.00000000",
        "type": "market",
        "time_in_force": "day",
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
    receipt_payload = {
        "schema_version": PHASE7_GUARDED_ALPACA_SUBMIT_SCHEMA_VERSION,
        "receipt_type": "phase7_guarded_alpaca_paper_receipt",
        "receipt_state": "local_guarded_paper_receipt_recorded",
        "submitted_order_ref": "q7-paper-order-probe0001",
        "broker_receipt_ref": "q7-local-broker-receipt-probe0001",
        "source_staged_order_artifact_id": "phase7:q7-6:staged-proof-order:probe",
        "proof_order_id": "q7-proof-order-probe0001",
        "source_auto_approval_decision_id": "probe:auto-approval:q7-setup",
        "source_setup_record_id": "probe:q7-setup",
        "idempotency_key": "q7-6-stage-probe0001",
        "idempotency_namespace": "phase7_demo_proof",
        "order_status_for_lifecycle": "submitted",
        "submitted_at": "2026-05-25T00:00:00+00:00",
        "paper_order_submitted": True,
        "broker_submit_receipt_created": True,
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
    return {
        "schema_version": 1,
        "guarded_submit_schema_version": PHASE7_GUARDED_ALPACA_SUBMIT_SCHEMA_VERSION,
        "artifact_type": "proof_broker_receipt",
        "artifact_id": "phase7:q7-7:guarded-alpaca-submit:probe",
        "phase": "Q7",
        "stage": "Q7-7",
        "status": "submitted",
        "receipt_state": "paper_broker_receipt_recorded",
        "public_safe": True,
        "source_staged_order_artifact_id": "phase7:q7-6:staged-proof-order:probe",
        "source_proof_order_id": "q7-proof-order-probe0001",
        "source_auto_approval_decision_id": "probe:auto-approval:q7-setup",
        "source_setup_record_id": "probe:q7-setup",
        "source_idempotency_key": "q7-6-stage-probe0001",
        "idempotency_key": "q7-6-stage-probe0001",
        "idempotency_namespace": "phase7_demo_proof",
        "selected_venue": "alpaca_paper",
        "broker_adapter": "alpaca",
        "path_key": PHASE7_ALPACA_PAPER_SUBMIT_PATH_KEY,
        "submit_path": _submit_path(),
        "submit_request_payload": request_payload,
        "broker_receipt_payload": receipt_payload,
        "duplicate_order_guard": {
            "schema_version": PHASE7_GUARDED_ALPACA_SUBMIT_SCHEMA_VERSION,
            "collision_checked": True,
            "collision_detected": False,
            "duplicate_detected": False,
            "idempotency_key": "q7-6-stage-probe0001",
            "guard_scope": "phase7_demo_proof_guarded_submit",
        },
        "pre_trade_snapshot": {
            "snapshot_schema_version": 1,
            "snapshot_type": "phase7_pre_trade_snapshot",
            "source_setup_record_id": "probe:q7-setup",
            "paper_account_starting_gbp": 1000.0,
            "max_drawdown_fraction": 0.2,
            "broker_identifier_exposed": False,
            "raw_payload_exposed": False,
            "local_path_exposed": False,
        },
        "event_log_prewrite_ref": "probe-prewrite-correlation",
        "submitted_order_ref": "q7-paper-order-probe0001",
        "broker_receipt_ref": "q7-local-broker-receipt-probe0001",
        "paper_order_submitted": True,
        "paper_order_submitted_count": 1,
        "broker_submit_receipt_created": True,
        "broker_submit_receipt_created_count": 1,
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
        "failed_checks": [],
        "failed_check_count": 0,
        "blocked_reasons": [],
        "blocked_reason_count": 0,
    }


def _with_valid_submit_record(artifact: dict[str, object]) -> dict[str, object]:
    probe = deepcopy(artifact)
    record = _valid_submit_record()
    probe["submit_records"] = [record]
    probe["broker_receipt_records"] = [record]
    probe["status"] = "paper_submit_receipts_recorded"
    probe["stage_status"] = "guarded_alpaca_submit_receipts_recorded"
    probe["source_proof_order_staging_status"] = "staged_orders_recorded"
    probe["source_staged_order_count"] = 1
    probe["submit_record_count"] = 1
    probe["submitted_paper_order_count"] = 1
    probe["broker_receipt_record_count"] = 1
    probe["blocked_submit_record_count"] = 0
    probe["idempotency_key_count"] = 1
    probe["duplicate_idempotency_key_count"] = 0
    probe["phase5_order_id_reuse_count"] = 0
    probe["paper_order_submitted_count"] = 1
    probe["broker_submit_receipt_created_count"] = 1
    return probe


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = phase7_guarded_alpaca_submit_paths(
        settings
    )
    if event_log_path.exists():
        event_log_path.unlink()

    readiness = build_phase7_readiness(settings=settings)
    readiness_errors = validate_phase7_readiness(readiness)
    staging = build_phase7_proof_order_staging(settings=settings)
    staging_errors = validate_phase7_proof_order_staging(staging)
    artifact = build_phase7_guarded_alpaca_paper_submit_path(settings=settings)
    output_path, history_path, event_log_path, written = (
        write_phase7_guarded_alpaca_paper_submit_path(
            artifact,
            settings=settings,
            record_event=True,
            event_log_path=event_log_path,
        )
    )
    validation_errors = validate_phase7_guarded_alpaca_paper_submit_path(written)
    replay = EventLog(event_log_path, echo=False).replay()
    runtime_copy = _read_json(output_path)

    valid_submit_probe = _with_valid_submit_record(written)
    valid_submit_errors = validate_phase7_guarded_alpaca_paper_submit_path(
        valid_submit_probe
    )

    duplicate_probe = _with_valid_submit_record(written)
    duplicate_record = deepcopy(duplicate_probe["submit_records"][0])
    duplicate_probe["submit_records"].append(duplicate_record)
    duplicate_probe["broker_receipt_records"].append(duplicate_record)
    duplicate_probe["submit_record_count"] = 2
    duplicate_probe["submitted_paper_order_count"] = 2
    duplicate_probe["broker_receipt_record_count"] = 2
    duplicate_probe["idempotency_key_count"] = 2
    duplicate_probe["duplicate_idempotency_key_count"] = 1
    duplicate_probe["paper_order_submitted_count"] = 2
    duplicate_probe["broker_submit_receipt_created_count"] = 2
    duplicate_errors = validate_phase7_guarded_alpaca_paper_submit_path(duplicate_probe)

    phase5_reuse_probe = _with_valid_submit_record(written)
    phase5_reuse_probe["submit_records"][0]["idempotency_key"] = "q5-7-dryrun-reused"
    phase5_reuse_probe["broker_receipt_records"][0]["idempotency_key"] = (
        "q5-7-dryrun-reused"
    )
    phase5_reuse_probe["phase5_order_id_reuse_count"] = 1
    phase5_reuse_errors = validate_phase7_guarded_alpaca_paper_submit_path(
        phase5_reuse_probe
    )

    live_endpoint_probe = _with_valid_submit_record(written)
    live_endpoint_probe["submit_records"][0]["submit_request_payload"][
        "live_endpoint_allowed"
    ] = True
    live_endpoint_errors = validate_phase7_guarded_alpaca_paper_submit_path(
        live_endpoint_probe
    )

    live_credentials_probe = _with_valid_submit_record(written)
    live_credentials_probe["submit_records"][0]["submit_request_payload"][
        "authorization_header_included"
    ] = True
    live_credentials_probe["submit_records"][0]["submit_path"]["base_url_exposed"] = True
    live_credentials_errors = validate_phase7_guarded_alpaca_paper_submit_path(
        live_credentials_probe
    )

    broker_post_probe = deepcopy(written)
    broker_post_probe["broker_post_called_count"] = 1
    broker_post_probe["broker_post_allowed"] = True
    broker_post_probe["authority_ledger"]["broker_post_allowed"] = True
    broker_post_errors = validate_phase7_guarded_alpaca_paper_submit_path(
        broker_post_probe
    )

    receipt_link_probe = _with_valid_submit_record(written)
    receipt_link_probe["submit_records"][0]["broker_receipt_ref"] = None
    receipt_link_probe["broker_receipt_records"][0]["broker_receipt_ref"] = None
    receipt_link_errors = validate_phase7_guarded_alpaca_paper_submit_path(
        receipt_link_probe
    )

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["authority_ledger"]["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase7_guarded_alpaca_paper_submit_path(
        proof_credit_probe
    )

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_probe["authority_ledger"]["live_capital_enabled"] = True
    live_capital_probe["live_capital_enabled_count"] = 1
    live_capital_errors = validate_phase7_guarded_alpaca_paper_submit_path(
        live_capital_probe
    )

    market_write_probe = deepcopy(written)
    market_write_probe["prediction_market_write_allowed"] = True
    market_write_probe["authority_ledger"]["prediction_market_write_allowed"] = True
    market_write_probe["prediction_market_write_allowed_count"] = 1
    market_write_probe["crypto_perps_write_allowed"] = True
    market_write_probe["authority_ledger"]["crypto_perps_write_allowed"] = True
    market_write_probe["crypto_perps_write_allowed_count"] = 1
    market_write_errors = validate_phase7_guarded_alpaca_paper_submit_path(
        market_write_probe
    )

    manual_override_probe = deepcopy(written)
    manual_override_probe["manual_trade_level_override_allowed"] = True
    manual_override_probe["authority_ledger"][
        "manual_trade_level_override_allowed"
    ] = True
    manual_override_probe["manual_trade_level_override_count"] = 1
    manual_override_errors = validate_phase7_guarded_alpaca_paper_submit_path(
        manual_override_probe
    )

    source_posture_probe = deepcopy(written)
    source_posture_probe["source_posture"][
        "preference_mcp_source_quorum_credit_allowed"
    ] = True
    source_posture_probe["source_posture"]["qctrl_role"] = "execution_truth"
    source_posture_errors = validate_phase7_guarded_alpaca_paper_submit_path(
        source_posture_probe
    )

    local_path_probe = deepcopy(written)
    local_path_probe["provenance"]["source_refs"] = [
        "/Users/raminhoodeh/Desktop/qadam/data/runtime/private.json"
    ]
    local_path_errors = validate_phase7_guarded_alpaca_paper_submit_path(
        local_path_probe
    )

    gate_probe = deepcopy(written)
    gate_probe["q7_7_guarded_alpaca_paper_submit_path_stage_allowed"] = False
    gate_errors = validate_phase7_guarded_alpaca_paper_submit_path(gate_probe)

    print(f"phase7_guarded_submit_status={written['status']}")
    print(f"phase7_guarded_submit_stage_status={written['stage_status']}")
    print(
        "phase7_guarded_submit_schema_version="
        f"{PHASE7_GUARDED_ALPACA_SUBMIT_SCHEMA_VERSION}"
    )
    print(f"phase7_guarded_submit_artifact_path={output_path}")
    print(f"phase7_guarded_submit_history_path={history_path}")
    print(f"phase7_guarded_submit_event_log_path={event_log_path}")
    print(
        "phase7_guarded_submit_source_proof_order_staging_status="
        f"{written['source_proof_order_staging_status']}"
    )
    print(
        "phase7_guarded_submit_path_available="
        f"{written['guarded_alpaca_paper_submit_path_available']}"
    )
    print(
        "phase7_guarded_submit_phase7_proof_trade_submission_allowed="
        f"{written['phase7_proof_trade_submission_allowed']}"
    )
    print(
        "phase7_guarded_submit_q7_8_lifecycle_stage_allowed="
        f"{written['q7_8_proof_lifecycle_monitor_stage_allowed']}"
    )
    print(f"phase7_guarded_submit_source_staged_order_count={written['source_staged_order_count']}")
    print(f"phase7_guarded_submit_submit_record_count={written['submit_record_count']}")
    print(f"phase7_guarded_submit_submitted_paper_order_count={written['submitted_paper_order_count']}")
    print(f"phase7_guarded_submit_broker_receipt_record_count={written['broker_receipt_record_count']}")
    print(f"phase7_guarded_submit_idempotency_key_count={written['idempotency_key_count']}")
    print(f"phase7_guarded_submit_duplicate_idempotency_key_count={written['duplicate_idempotency_key_count']}")
    print(f"phase7_guarded_submit_phase5_order_id_reuse_count={written['phase5_order_id_reuse_count']}")
    print(f"phase7_guarded_submit_broker_post_called_count={written['broker_post_called_count']}")
    print(f"phase7_guarded_submit_alpaca_post_called_count={written['alpaca_post_called_count']}")
    print(f"phase7_guarded_submit_paper_order_submitted_count={written['paper_order_submitted_count']}")
    print(f"phase7_guarded_submit_broker_receipt_created_count={written['broker_submit_receipt_created_count']}")
    print(f"phase7_guarded_submit_proof_trade_count={written['proof_trade_count']}")
    print(f"phase7_guarded_submit_phase7_proof_credit_allowed={written['phase7_proof_credit_allowed']}")
    print(f"phase7_guarded_submit_live_capital_enabled={written['live_capital_enabled']}")
    print(f"phase7_guarded_submit_unsafe_write_counter_total={written['unsafe_write_counter_total']}")
    print(f"phase7_guarded_submit_blocker_count={written['blocker_count']}")
    print(f"phase7_guarded_submit_event_log_replay_total_events={replay['total_events']}")
    print(f"phase7_guarded_submit_readiness_error_count={len(readiness_errors)}")
    print(f"phase7_guarded_submit_staging_error_count={len(staging_errors)}")
    print(f"phase7_guarded_submit_valid_submit_probe_error_count={len(valid_submit_errors)}")
    print(f"phase7_guarded_submit_duplicate_probe_error_count={len(duplicate_errors)}")
    print(f"phase7_guarded_submit_phase5_reuse_probe_error_count={len(phase5_reuse_errors)}")
    print(f"phase7_guarded_submit_live_endpoint_probe_error_count={len(live_endpoint_errors)}")
    print(f"phase7_guarded_submit_live_credentials_probe_error_count={len(live_credentials_errors)}")
    print(f"phase7_guarded_submit_broker_post_probe_error_count={len(broker_post_errors)}")
    print(f"phase7_guarded_submit_receipt_link_probe_error_count={len(receipt_link_errors)}")
    print(f"phase7_guarded_submit_proof_credit_probe_error_count={len(proof_credit_errors)}")
    print(f"phase7_guarded_submit_live_capital_probe_error_count={len(live_capital_errors)}")
    print(f"phase7_guarded_submit_market_write_probe_error_count={len(market_write_errors)}")
    print(f"phase7_guarded_submit_manual_override_probe_error_count={len(manual_override_errors)}")
    print(f"phase7_guarded_submit_source_posture_probe_error_count={len(source_posture_errors)}")
    print(f"phase7_guarded_submit_local_path_probe_error_count={len(local_path_errors)}")
    print(f"phase7_guarded_submit_gate_probe_error_count={len(gate_errors)}")
    print(f"phase7_guarded_submit_next_stage={written['recommended_next_stage']}")
    print("phase7_guarded_submit_boundary=" + written["boundary"])

    if readiness_errors:
        errors.extend(readiness_errors)
    if staging_errors:
        errors.extend(staging_errors)
    if validation_errors:
        errors.extend(validation_errors)
    if runtime_copy.get("artifact_id") != written["artifact_id"]:
        errors.append("runtime_phase7_guarded_submit_not_written")
    if written["status"] != "ready_no_submit_candidates":
        errors.append("phase7_guarded_submit_status_invalid")
    if written["stage_status"] != "guarded_alpaca_submit_path_ready_no_staged_orders":
        errors.append("phase7_guarded_submit_stage_status_invalid")
    if written["guarded_alpaca_paper_submit_path_available"] is not True:
        errors.append("phase7_guarded_submit_path_not_available")
    if written["phase7_proof_trade_submission_allowed"] is not True:
        errors.append("phase7_guarded_submit_submission_authority_missing")
    if written["q7_8_proof_lifecycle_monitor_stage_allowed"] is not True:
        errors.append("phase7_guarded_submit_q7_8_not_allowed")
    for count_key in (
        "source_staged_order_count",
        "submit_record_count",
        "submitted_paper_order_count",
        "broker_receipt_record_count",
        "idempotency_key_count",
        "duplicate_idempotency_key_count",
        "phase5_order_id_reuse_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
        "paper_order_submitted_count",
        "broker_submit_receipt_created_count",
        "proof_trade_count",
        "unsafe_write_counter_total",
        "blocker_count",
    ):
        if written[count_key] != 0:
            errors.append(f"phase7_guarded_submit_count_nonzero:{count_key}")
    for flag_key in (
        "phase7_proof_trade_execution_allowed",
        "phase7_proof_lifecycle_write_allowed",
        "phase7_proof_credit_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "manual_trade_level_override_allowed",
    ):
        if written[flag_key] is not False:
            errors.append(f"phase7_guarded_submit_forbidden_authority:{flag_key}")
    if written["event_log_written"] is not True:
        errors.append("phase7_guarded_submit_event_log_not_written")
    if replay["total_events"] != 1:
        errors.append("phase7_guarded_submit_event_log_replay_count_mismatch")

    if valid_submit_errors:
        errors.append("valid_submit_probe_rejected")
    if "guarded_submit_duplicate_idempotency_key" not in duplicate_errors:
        errors.append("duplicate_idempotency_probe_not_rejected")
    if "guarded_submit_idempotency_key_invalid" not in phase5_reuse_errors:
        errors.append("phase5_idempotency_probe_not_rejected")
    if "guarded_submit_phase5_idempotency_reuse" not in phase5_reuse_errors:
        errors.append("phase5_reuse_probe_not_rejected")
    if "guarded_submit_phase5_order_id_reuse" not in phase5_reuse_errors:
        errors.append("phase5_reuse_count_probe_not_rejected")
    if "guarded_submit_request_forbidden:live_endpoint_allowed" not in live_endpoint_errors:
        errors.append("live_endpoint_probe_not_rejected")
    if "guarded_submit_request_forbidden:authorization_header_included" not in (
        live_credentials_errors
    ):
        errors.append("live_credentials_header_probe_not_rejected")
    if "guarded_submit_path_forbidden:base_url_exposed" not in live_credentials_errors:
        errors.append("live_credentials_base_url_probe_not_rejected")
    if "guarded_submit_authority_invalid:broker_post_allowed" not in broker_post_errors:
        errors.append("broker_post_authority_probe_not_rejected")
    if "guarded_submit_count_nonzero:broker_post_called_count" not in broker_post_errors:
        errors.append("broker_post_count_probe_not_rejected")
    if "guarded_submit_broker_receipt_ref_missing" not in receipt_link_errors:
        errors.append("receipt_link_probe_not_rejected")
    if "guarded_submit_authority_invalid:phase7_proof_credit_allowed" not in (
        proof_credit_errors
    ):
        errors.append("proof_credit_authority_probe_not_rejected")
    if "guarded_submit_unsafe_count_nonzero:phase7_proof_credit_allowed_count" not in (
        proof_credit_errors
    ):
        errors.append("proof_credit_count_probe_not_rejected")
    if "guarded_submit_authority_invalid:live_capital_enabled" not in live_capital_errors:
        errors.append("live_capital_authority_probe_not_rejected")
    if "guarded_submit_unsafe_count_nonzero:live_capital_enabled_count" not in (
        live_capital_errors
    ):
        errors.append("live_capital_count_probe_not_rejected")
    if "guarded_submit_authority_invalid:prediction_market_write_allowed" not in (
        market_write_errors
    ):
        errors.append("prediction_market_authority_probe_not_rejected")
    if "guarded_submit_authority_invalid:crypto_perps_write_allowed" not in (
        market_write_errors
    ):
        errors.append("crypto_perps_authority_probe_not_rejected")
    if "guarded_submit_authority_invalid:manual_trade_level_override_allowed" not in (
        manual_override_errors
    ):
        errors.append("manual_override_authority_probe_not_rejected")
    if "guarded_submit_preference_quorum_credit_allowed" not in source_posture_errors:
        errors.append("source_posture_preference_probe_not_rejected")
    if "guarded_submit_qctrl_role_invalid" not in source_posture_errors:
        errors.append("source_posture_qctrl_probe_not_rejected")
    if "guarded_submit_provenance_local_path_leak" not in local_path_errors:
        errors.append("local_path_probe_not_rejected")
    if "q7_7_guarded_alpaca_paper_submit_path_not_allowed" not in gate_errors:
        errors.append("gate_probe_not_rejected")

    if errors:
        for error in sorted(set(errors)):
            print(f"phase7_guarded_submit_error={error}")
        print("phase7_guarded_alpaca_paper_submit_check=failed")
        return 1

    print("phase7_guarded_alpaca_paper_submit_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
