#!/usr/bin/env python3
"""Validate the Q5-11 paper position monitor and reconciliation loop."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase5_position_monitor import (  # noqa: E402
    PHASE5_POSITION_MONITOR_SCHEMA_VERSION,
    POSITION_LIFECYCLE_STATES,
    POSITION_MONITOR_REQUIRED_CHECKS,
    build_phase5_position_monitor,
    position_monitor_paths,
    validate_phase5_position_monitor_bundle,
    validate_phase5_position_monitor_record,
    write_phase5_position_monitor,
)


def _record(bundle: dict, artifact_type: str) -> dict:
    for record in bundle.get("records", []):
        if isinstance(record, dict) and record.get("artifact_type") == artifact_type:
            return record
    raise RuntimeError(f"missing record type {artifact_type}")


def _record_errors(record: dict, **updates: object) -> list[str]:
    probe = deepcopy(record)
    for key, value in updates.items():
        probe[key] = value
    return validate_phase5_position_monitor_record(probe)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = position_monitor_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    bundle = build_phase5_position_monitor(settings=settings)
    output_path, history_path, event_log_path, written_bundle = write_phase5_position_monitor(
        bundle,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase5_position_monitor_bundle(written_bundle)
    event_replay = EventLog(event_log_path, echo=False).replay()
    position_record = _record(written_bundle, "position_state")
    closed_trade_record = _record(written_bundle, "closed_trade_summary")

    submit_probe_errors = _record_errors(position_record, paper_order_allowed=True)
    close_probe_errors = _record_errors(position_record, position_close_allowed=True)
    resize_probe_errors = _record_errors(position_record, position_resize_allowed=True)
    cancel_probe_errors = _record_errors(position_record, order_cancel_allowed=True)
    broker_write_probe_errors = _record_errors(position_record, broker_write_allowed=True)
    broker_post_probe_errors = _record_errors(position_record, broker_post_called=True)
    alpaca_post_probe_errors = _record_errors(position_record, alpaca_post_called=True)
    monitor_write_probe_errors = _record_errors(position_record, position_monitor_write_authority=True)
    live_capital_probe_errors = _record_errors(position_record, live_capital_enabled=True)
    raw_payload_probe_errors = _record_errors(position_record, raw_payload_exposed=True)
    account_identifier_probe_errors = _record_errors(position_record, account_identifier_exposed=True)
    open_position_probe_errors = _record_errors(
        position_record,
        status="open_position",
        open_position_count=0,
    )
    failed_reconciliation_probe_errors = _record_errors(
        position_record,
        status="failed_reconciliation",
        failed_reconciliation_count=0,
    )
    failed_reconciliation_unblocked_probe_errors = _record_errors(
        position_record,
        failed_reconciliation_count=1,
        new_actions_blocked_by_reconciliation_failure=False,
    )
    closed_trade_tag_probe_errors = _record_errors(closed_trade_record, phase5_test_trade=False)

    print("phase5_position_monitor_status=" + written_bundle["status"])
    print(f"phase5_position_monitor_schema_version={PHASE5_POSITION_MONITOR_SCHEMA_VERSION}")
    print(f"phase5_position_monitor_artifact_path={output_path}")
    print(f"phase5_position_monitor_history_path={history_path}")
    print(f"phase5_position_monitor_event_log_path={event_log_path}")
    print(f"phase5_position_monitor_position_record_count={written_bundle['position_record_count']}")
    print(
        "phase5_position_monitor_closed_trade_summary_count="
        f"{written_bundle['closed_trade_summary_count']}"
    )
    print(f"phase5_position_monitor_monitor_record_count={written_bundle['monitor_record_count']}")
    print(f"phase5_position_monitor_lifecycle_state_count={written_bundle['lifecycle_state_count']}")
    print(f"phase5_position_monitor_submitted_order_count={written_bundle['submitted_order_count']}")
    print(f"phase5_position_monitor_mirrored_order_count={written_bundle['mirrored_order_count']}")
    print(f"phase5_position_monitor_open_order_count={written_bundle['open_order_count']}")
    print(f"phase5_position_monitor_open_position_count={written_bundle['open_position_count']}")
    print(f"phase5_position_monitor_closed_trade_count={written_bundle['closed_trade_count']}")
    print(f"phase5_position_monitor_postmortem_due_count={written_bundle['postmortem_due_count']}")
    print(f"phase5_position_monitor_account_equity_gbp={written_bundle['account_equity_gbp']}")
    print(f"phase5_position_monitor_realized_pnl_gbp={written_bundle['realized_pnl_gbp']}")
    print(f"phase5_position_monitor_unrealized_pnl_gbp={written_bundle['unrealized_pnl_gbp']}")
    print(
        "phase5_position_monitor_failed_reconciliation_count="
        f"{written_bundle['failed_reconciliation_count']}"
    )
    print(f"phase5_position_monitor_duplicate_state_count={written_bundle['duplicate_state_count']}")
    print(f"phase5_position_monitor_missing_state_count={written_bundle['missing_state_count']}")
    print(
        "phase5_position_monitor_contradictory_state_count="
        f"{written_bundle['contradictory_state_count']}"
    )
    print(f"phase5_position_monitor_unknown_state_count={written_bundle['unknown_state_count']}")
    print(f"phase5_position_monitor_stuck_state_count={written_bundle['stuck_state_count']}")
    print(
        "phase5_position_monitor_new_actions_blocked_by_reconciliation_failure="
        f"{written_bundle['new_actions_blocked_by_reconciliation_failure']}"
    )
    print(f"phase5_position_monitor_paper_submit_gate_status={written_bundle['paper_submit_gate_status']}")
    print(f"phase5_position_monitor_telegram_notifier_status={written_bundle['telegram_notifier_status']}")
    print(f"phase5_position_monitor_event_log_written={written_bundle['event_log_written']}")
    print(f"phase5_position_monitor_event_log_total_events={event_replay['total_events']}")
    print(f"phase5_position_monitor_validation_error_count={len(validation_errors)}")
    print(f"phase5_position_monitor_required_check_count={written_bundle['required_check_count']}")
    for key in (
        "risk_approval_allowed_count",
        "trade_candidate_created_count",
        "execution_allowed_count",
        "execution_intent_created_count",
        "execution_adapter_write_authority_count",
        "paper_execution_allowed_count",
        "paper_order_allowed_count",
        "paper_order_staging_allowed_count",
        "paper_order_submission_allowed_count",
        "paper_order_submitted_count",
        "broker_write_allowed_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
        "broker_submit_receipt_created_count",
        "prediction_market_write_allowed_count",
        "telegram_live_notifications_allowed_count",
        "position_created_count",
        "position_monitor_write_authority_count",
        "position_close_allowed_count",
        "position_resize_allowed_count",
        "order_cancel_allowed_count",
        "live_endpoint_allowed_count",
        "live_capital_enabled_count",
        "secret_value_exposed_count",
        "raw_payload_exposed_count",
        "local_path_exposed_count",
        "authorization_header_exposed_count",
        "account_identifier_exposed_count",
        "broker_order_identifier_exposed_count",
    ):
        print(f"phase5_position_monitor_{key}={written_bundle[key]}")
    print(f"phase5_position_monitor_submit_probe_error_count={len(submit_probe_errors)}")
    print(f"phase5_position_monitor_close_probe_error_count={len(close_probe_errors)}")
    print(f"phase5_position_monitor_resize_probe_error_count={len(resize_probe_errors)}")
    print(f"phase5_position_monitor_cancel_probe_error_count={len(cancel_probe_errors)}")
    print(f"phase5_position_monitor_broker_write_probe_error_count={len(broker_write_probe_errors)}")
    print(f"phase5_position_monitor_broker_post_probe_error_count={len(broker_post_probe_errors)}")
    print(f"phase5_position_monitor_alpaca_post_probe_error_count={len(alpaca_post_probe_errors)}")
    print(f"phase5_position_monitor_monitor_write_probe_error_count={len(monitor_write_probe_errors)}")
    print(f"phase5_position_monitor_live_capital_probe_error_count={len(live_capital_probe_errors)}")
    print(f"phase5_position_monitor_raw_payload_probe_error_count={len(raw_payload_probe_errors)}")
    print(
        "phase5_position_monitor_account_identifier_probe_error_count="
        f"{len(account_identifier_probe_errors)}"
    )
    print(f"phase5_position_monitor_open_position_probe_error_count={len(open_position_probe_errors)}")
    print(
        "phase5_position_monitor_failed_reconciliation_probe_error_count="
        f"{len(failed_reconciliation_probe_errors)}"
    )
    print(
        "phase5_position_monitor_failed_reconciliation_unblocked_probe_error_count="
        f"{len(failed_reconciliation_unblocked_probe_errors)}"
    )
    print(
        "phase5_position_monitor_closed_trade_tag_probe_error_count="
        f"{len(closed_trade_tag_probe_errors)}"
    )
    print("phase5_position_monitor_boundary=" + written_bundle["boundary"])

    if validation_errors:
        errors.extend(validation_errors)
    if written_bundle["status"] != "ok":
        errors.append("position_monitor_bundle_not_ok")
    if written_bundle["position_record_count"] < 1:
        errors.append("position_monitor_position_record_missing")
    if written_bundle["closed_trade_summary_count"] < 1:
        errors.append("position_monitor_closed_trade_summary_missing")
    if written_bundle["monitor_record_count"] != (
        written_bundle["position_record_count"] + written_bundle["closed_trade_summary_count"]
    ):
        errors.append("position_monitor_record_count_mismatch")
    if written_bundle["lifecycle_state_count"] != len(POSITION_LIFECYCLE_STATES):
        errors.append("position_monitor_lifecycle_state_count_mismatch")
    if written_bundle["required_check_count"] != len(POSITION_MONITOR_REQUIRED_CHECKS):
        errors.append("position_monitor_required_check_count_mismatch")
    if written_bundle["paper_submit_gate_validation_error_count"] != 0:
        errors.append("position_monitor_paper_submit_gate_validation_errors")
    if written_bundle["telegram_notifier_validation_error_count"] != 0:
        errors.append("position_monitor_telegram_notifier_validation_errors")
    if written_bundle["event_log_written"] is not True:
        errors.append("position_monitor_event_log_not_written")
    if event_replay["total_events"] != written_bundle["monitor_record_count"]:
        errors.append("position_monitor_event_log_count_mismatch")
    if written_bundle["failed_reconciliation_count"] != 0:
        errors.append("position_monitor_unexpected_reconciliation_failures")
    if written_bundle["submitted_order_count"] == 0:
        if written_bundle["mirrored_order_count"] != 0:
            errors.append("position_monitor_unexpected_mirrored_orders")
        if position_record["position_state"] != "no_submitted_paper_orders":
            errors.append("position_monitor_expected_no_submitted_order_sentinel")
        if position_record["status"] != "blocked":
            errors.append("position_monitor_sentinel_not_blocked")
    else:
        if written_bundle["mirrored_order_count"] < written_bundle["submitted_order_count"]:
            errors.append("position_monitor_submitted_order_not_mirrored")
        if position_record["position_state"] == "no_submitted_paper_orders":
            errors.append("position_monitor_unexpected_no_submitted_order_sentinel")
        if position_record["lifecycle_state"] not in POSITION_LIFECYCLE_STATES:
            errors.append("position_monitor_lifecycle_state_invalid")
    if written_bundle["closed_trade_count"] == 0:
        if written_bundle["postmortem_due_count"] != 0:
            errors.append("position_monitor_postmortem_due_without_closed_trade")
        if closed_trade_record["closed_trade_state"] != "not_closed":
            errors.append("position_monitor_expected_no_closed_trade_sentinel")
    if closed_trade_record["phase5_test_trade"] is not True:
        errors.append("position_monitor_closed_trade_sentinel_not_phase5_test")
    for key in (
        "risk_approval_allowed_count",
        "trade_candidate_created_count",
        "execution_allowed_count",
        "execution_intent_created_count",
        "execution_adapter_write_authority_count",
        "paper_execution_allowed_count",
        "paper_order_allowed_count",
        "paper_order_staging_allowed_count",
        "paper_order_submission_allowed_count",
        "paper_order_submitted_count",
        "broker_write_allowed_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
        "broker_submit_receipt_created_count",
        "prediction_market_write_allowed_count",
        "telegram_live_notifications_allowed_count",
        "position_created_count",
        "position_monitor_write_authority_count",
        "position_close_allowed_count",
        "position_resize_allowed_count",
        "order_cancel_allowed_count",
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
            errors.append(f"position_monitor_boundary_count_not_zero:{key}")
    expected_probe_markers = (
        ("phase5_authority_enabled:paper_order_allowed", submit_probe_errors),
        ("position_monitor_boundary_enabled:position_close_allowed", close_probe_errors),
        ("position_monitor_boundary_enabled:position_resize_allowed", resize_probe_errors),
        ("position_monitor_boundary_enabled:order_cancel_allowed", cancel_probe_errors),
        ("phase5_authority_enabled:broker_write_allowed", broker_write_probe_errors),
        ("position_monitor_boundary_enabled:broker_post_called", broker_post_probe_errors),
        ("position_monitor_boundary_enabled:alpaca_post_called", alpaca_post_probe_errors),
        ("phase5_authority_enabled:position_monitor_write_authority", monitor_write_probe_errors),
        ("phase5_authority_enabled:live_capital_enabled", live_capital_probe_errors),
        ("position_monitor_exposure_enabled:raw_payload_exposed", raw_payload_probe_errors),
        ("position_monitor_exposure_enabled:account_identifier_exposed", account_identifier_probe_errors),
        ("open_position_status_without_position", open_position_probe_errors),
        ("failed_reconciliation_without_failure_count", failed_reconciliation_probe_errors),
        (
            "reconciliation_failure_does_not_block_new_actions",
            failed_reconciliation_unblocked_probe_errors,
        ),
        ("closed_trade_not_tagged_phase5_test_trade", closed_trade_tag_probe_errors),
    )
    for marker, probe_errors in expected_probe_markers:
        if marker not in probe_errors:
            errors.append(f"position_monitor_probe_not_rejected:{marker}")
    if "cannot submit, close, resize, cancel" not in written_bundle["boundary"]:
        errors.append("position_monitor_boundary_weak")

    if errors:
        for error in errors:
            print(f"phase5_position_monitor_error={error}")
        print("phase5_position_monitor_check=failed")
        return 1

    print("phase5_position_monitor_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
