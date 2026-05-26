#!/usr/bin/env python3
"""Validate the Q5-12 signal review UI and governance action contract."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase5_signal_review import (  # noqa: E402
    PHASE5_SIGNAL_REVIEW_SCHEMA_VERSION,
    SIGNAL_REVIEW_CHAIN_STEPS,
    SIGNAL_REVIEW_REQUIRED_CHECKS,
    build_phase5_signal_review,
    phase5_signal_review_paths,
    validate_phase5_signal_review_bundle,
    validate_phase5_signal_review_record,
    write_phase5_signal_review,
)


def _first_record(bundle: dict) -> dict:
    records = bundle.get("records", [])
    if not records:
        raise RuntimeError("missing Q5-12 signal review record")
    return records[0]


def _record_errors(record: dict, **updates: object) -> list[str]:
    probe = deepcopy(record)
    for key, value in updates.items():
        probe[key] = value
    return validate_phase5_signal_review_record(probe)


def _chain_probe_errors(record: dict, *, step: str, **updates: object) -> list[str]:
    probe = deepcopy(record)
    probe["decision_chain"][step].update(updates)
    return validate_phase5_signal_review_record(probe)


def _action_probe_errors(record: dict, **updates: object) -> list[str]:
    probe = deepcopy(record)
    probe["governance_action"].update(updates)
    for key in (
        "governance_comment_event_log_written",
        "kill_switch_action_event_log_written",
    ):
        if key in updates:
            probe[key] = updates[key]
    return validate_phase5_signal_review_record(probe)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = phase5_signal_review_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    bundle = build_phase5_signal_review(settings=settings)
    output_path, history_path, event_log_path, written_bundle = write_phase5_signal_review(
        bundle,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase5_signal_review_bundle(written_bundle)
    event_replay = EventLog(event_log_path, echo=False).replay()
    first_record = _first_record(written_bundle)

    inferred_probe_errors = _record_errors(first_record, ui_inferred_readiness=True)
    broker_probe_errors = _record_errors(first_record, broker_write_allowed=True)
    order_probe_errors = _record_errors(first_record, order_place_control_enabled=True)
    approve_probe_errors = _record_errors(first_record, trade_approval_control_enabled=True)
    resize_probe_errors = _record_errors(first_record, position_resize_control_enabled=True)
    close_probe_errors = _record_errors(first_record, position_close_control_enabled=True)
    cancel_probe_errors = _record_errors(first_record, order_cancel_control_enabled=True)
    prediction_probe_errors = _record_errors(first_record, prediction_market_write_allowed=True)
    live_probe_errors = _record_errors(first_record, live_capital_enabled=True)
    raw_payload_probe_errors = _record_errors(first_record, raw_payload_exposed=True)
    chain_mismatch_probe_errors = _chain_probe_errors(
        first_record,
        step="risk_agent",
        display_status="eligible",
    )
    chain_inferred_probe_errors = _chain_probe_errors(
        first_record,
        step="approval_policy",
        ui_inferred=True,
    )
    action_target_probe_errors = _action_probe_errors(first_record, target_artifact_id="")
    kill_mutation_probe_errors = _action_probe_errors(
        first_record,
        kill_switch_mutation_authority=True,
    )

    print("phase5_signal_review_status=" + written_bundle["status"])
    print(f"phase5_signal_review_schema_version={PHASE5_SIGNAL_REVIEW_SCHEMA_VERSION}")
    print(f"phase5_signal_review_artifact_path={output_path}")
    print(f"phase5_signal_review_history_path={history_path}")
    print(f"phase5_signal_review_event_log_path={event_log_path}")
    print(f"phase5_signal_review_record_count={written_bundle['signal_review_record_count']}")
    print(f"phase5_signal_review_chain_step_count={written_bundle['chain_step_count']}")
    print(f"phase5_signal_review_decision_chain_count={written_bundle['decision_chain_count']}")
    print(f"phase5_signal_review_required_check_count={written_bundle['required_check_count']}")
    print(f"phase5_signal_review_governance_action_count={written_bundle['governance_action_count']}")
    print(f"phase5_signal_review_governance_comment_count={written_bundle['governance_comment_count']}")
    print(
        "phase5_signal_review_governance_comment_event_count="
        f"{written_bundle['governance_comment_event_count']}"
    )
    print(
        "phase5_signal_review_kill_switch_action_available_count="
        f"{written_bundle['kill_switch_action_available_count']}"
    )
    print(
        "phase5_signal_review_kill_switch_action_event_count="
        f"{written_bundle['kill_switch_action_event_count']}"
    )
    print(f"phase5_signal_review_backend_truth_displayed_count={written_bundle['backend_truth_displayed_count']}")
    print(f"phase5_signal_review_ui_inferred_readiness_count={written_bundle['ui_inferred_readiness_count']}")
    print(f"phase5_signal_review_event_log_written={written_bundle['event_log_written']}")
    print(f"phase5_signal_review_event_log_total_events={event_replay['total_events']}")
    print(f"phase5_signal_review_validation_error_count={len(validation_errors)}")
    print(f"phase5_signal_review_q5_4_kill_switch_ledger_recorded={written_bundle['q5_4_kill_switch_ledger_recorded']}")
    print(f"phase5_signal_review_backend_validation_error_count={written_bundle['backend_validation_error_count']}")
    for key in (
        "trade_approval_control_enabled_count",
        "trade_rejection_control_enabled_count",
        "order_place_control_enabled_count",
        "order_modify_control_enabled_count",
        "position_resize_control_enabled_count",
        "position_close_control_enabled_count",
        "order_cancel_control_enabled_count",
        "kill_switch_mutation_authority_count",
        "kill_switch_action_mutates_state_count",
        "broker_write_allowed_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
        "prediction_market_write_allowed_count",
        "telegram_command_path_enabled_count",
        "live_endpoint_allowed_count",
        "live_capital_enabled_count",
        "secret_value_exposed_count",
        "raw_payload_exposed_count",
        "local_path_exposed_count",
        "authorization_header_exposed_count",
        "account_identifier_exposed_count",
        "broker_order_identifier_exposed_count",
    ):
        print(f"phase5_signal_review_{key}={written_bundle[key]}")
    print(f"phase5_signal_review_inferred_probe_error_count={len(inferred_probe_errors)}")
    print(f"phase5_signal_review_broker_probe_error_count={len(broker_probe_errors)}")
    print(f"phase5_signal_review_order_probe_error_count={len(order_probe_errors)}")
    print(f"phase5_signal_review_approve_probe_error_count={len(approve_probe_errors)}")
    print(f"phase5_signal_review_resize_probe_error_count={len(resize_probe_errors)}")
    print(f"phase5_signal_review_close_probe_error_count={len(close_probe_errors)}")
    print(f"phase5_signal_review_cancel_probe_error_count={len(cancel_probe_errors)}")
    print(f"phase5_signal_review_prediction_probe_error_count={len(prediction_probe_errors)}")
    print(f"phase5_signal_review_live_probe_error_count={len(live_probe_errors)}")
    print(f"phase5_signal_review_raw_payload_probe_error_count={len(raw_payload_probe_errors)}")
    print(f"phase5_signal_review_chain_mismatch_probe_error_count={len(chain_mismatch_probe_errors)}")
    print(f"phase5_signal_review_chain_inferred_probe_error_count={len(chain_inferred_probe_errors)}")
    print(f"phase5_signal_review_action_target_probe_error_count={len(action_target_probe_errors)}")
    print(f"phase5_signal_review_kill_mutation_probe_error_count={len(kill_mutation_probe_errors)}")
    print("phase5_signal_review_boundary=" + written_bundle["boundary"])

    if validation_errors:
        errors.extend(validation_errors)
    if written_bundle["status"] != "ok":
        errors.append("signal_review_bundle_not_ok")
    if written_bundle["signal_review_record_count"] < 1:
        errors.append("signal_review_records_missing")
    if written_bundle["chain_step_count"] != len(SIGNAL_REVIEW_CHAIN_STEPS):
        errors.append("signal_review_chain_step_count_mismatch")
    if written_bundle["decision_chain_count"] != (
        written_bundle["signal_review_record_count"] * len(SIGNAL_REVIEW_CHAIN_STEPS)
    ):
        errors.append("signal_review_decision_chain_count_mismatch")
    if written_bundle["required_check_count"] != len(SIGNAL_REVIEW_REQUIRED_CHECKS):
        errors.append("signal_review_required_check_count_mismatch")
    if written_bundle["backend_truth_displayed_count"] != written_bundle["signal_review_record_count"]:
        errors.append("signal_review_backend_truth_display_count_mismatch")
    if written_bundle["ui_inferred_readiness_count"] != 0:
        errors.append("signal_review_ui_inferred_readiness_nonzero")
    if written_bundle["governance_action_count"] != written_bundle["signal_review_record_count"]:
        errors.append("signal_review_governance_action_count_mismatch")
    if written_bundle["governance_comment_event_count"] != written_bundle["signal_review_record_count"]:
        errors.append("signal_review_governance_comment_event_count_mismatch")
    if written_bundle["kill_switch_action_available_count"] != written_bundle["signal_review_record_count"]:
        errors.append("signal_review_kill_switch_action_available_count_mismatch")
    if written_bundle["kill_switch_action_event_count"] != written_bundle["signal_review_record_count"]:
        errors.append("signal_review_kill_switch_action_event_count_mismatch")
    if event_replay["total_events"] != (
        written_bundle["signal_review_record_count"]
        + written_bundle["governance_comment_event_count"]
        + written_bundle["kill_switch_action_event_count"]
    ):
        errors.append("signal_review_event_log_count_mismatch")
    if written_bundle["backend_validation_error_count"] != 0:
        errors.append("signal_review_backend_validation_errors")
    for key in (
        "trade_approval_control_enabled_count",
        "trade_rejection_control_enabled_count",
        "order_place_control_enabled_count",
        "order_modify_control_enabled_count",
        "position_resize_control_enabled_count",
        "position_close_control_enabled_count",
        "order_cancel_control_enabled_count",
        "kill_switch_mutation_authority_count",
        "kill_switch_action_mutates_state_count",
        "broker_write_allowed_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
        "prediction_market_write_allowed_count",
        "telegram_command_path_enabled_count",
        "live_endpoint_allowed_count",
        "live_capital_enabled_count",
        "secret_value_exposed_count",
        "raw_payload_exposed_count",
        "local_path_exposed_count",
        "authorization_header_exposed_count",
        "account_identifier_exposed_count",
        "broker_order_identifier_exposed_count",
    ):
        if written_bundle.get(key) != 0:
            errors.append(f"signal_review_boundary_count_not_zero:{key}")
    expected_probe_markers = (
        ("ui_inferred_readiness_enabled", inferred_probe_errors),
        ("signal_review_boundary_enabled:broker_write_allowed", broker_probe_errors),
        ("signal_review_boundary_enabled:order_place_control_enabled", order_probe_errors),
        ("signal_review_boundary_enabled:trade_approval_control_enabled", approve_probe_errors),
        ("signal_review_boundary_enabled:position_resize_control_enabled", resize_probe_errors),
        ("signal_review_boundary_enabled:position_close_control_enabled", close_probe_errors),
        ("signal_review_boundary_enabled:order_cancel_control_enabled", cancel_probe_errors),
        ("signal_review_boundary_enabled:prediction_market_write_allowed", prediction_probe_errors),
        ("phase5_authority_enabled:live_capital_enabled", live_probe_errors),
        ("signal_review_exposure_enabled:raw_payload_exposed", raw_payload_probe_errors),
        ("decision_chain_display_status_mismatch:risk_agent", chain_mismatch_probe_errors),
        ("decision_chain_step_inferred:approval_policy", chain_inferred_probe_errors),
        ("governance_action_target_missing", action_target_probe_errors),
        ("kill_switch_action_mutation_authority_enabled", kill_mutation_probe_errors),
    )
    for marker, probe_errors in expected_probe_markers:
        if marker not in probe_errors:
            errors.append(f"signal_review_probe_not_rejected:{marker}")
    if "cannot call brokers or venues" not in written_bundle["boundary"]:
        errors.append("signal_review_boundary_weak")

    if errors:
        for error in errors:
            print(f"phase5_signal_review_error={error}")
        print("phase5_signal_review_check=failed")
        return 1

    print("phase5_signal_review_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
