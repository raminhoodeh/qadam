#!/usr/bin/env python3
"""Validate the PaperOps-5 notification and review contract."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.paperops_notification_review import (  # noqa: E402
    PAPEROPS_LIFECYCLE_NOTIFICATION_TYPES,
    PAPEROPS_NOTIFICATION_REVIEW_SCHEMA_VERSION,
    PAPEROPS_NOTIFICATION_TYPES,
    build_paperops_notification_review,
    paperops_notification_review_paths,
    validate_paperops_notification_record,
    validate_paperops_notification_review,
    write_paperops_notification_review,
)


def _record(bundle: dict, notification_type: str) -> dict:
    for record in bundle.get("records", []):
        if isinstance(record, dict) and record.get("notification_type") == notification_type:
            return record
    raise RuntimeError(f"missing notification record {notification_type}")


def _record_probe_errors(record: dict, **updates: object) -> list[str]:
    probe = deepcopy(record)
    for key, value in updates.items():
        probe[key] = value
    return validate_paperops_notification_record(probe)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = paperops_notification_review_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    artifact = build_paperops_notification_review(settings=settings)
    output_path, history_path, event_log_path, written = write_paperops_notification_review(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_paperops_notification_review(written)
    replay = EventLog(event_log_path, echo=False).replay()
    readiness_record = _record(written, "paperops_readiness_review")
    operations_record = _record(written, "paperops_30_day_operations")
    active_automation_record = _record(written, "active_paper_automation")
    qctrl_hold_record = _record(written, "qctrl_consultation_hold")
    exit_record = _record(written, "paper_exit_path")

    command_probe_errors = _record_probe_errors(
        readiness_record,
        telegram_command_path_enabled=True,
    )
    approve_probe_errors = _record_probe_errors(
        readiness_record,
        telegram_approve_trade_command_enabled=True,
    )
    close_probe_errors = _record_probe_errors(
        exit_record,
        telegram_close_trade_command_enabled=True,
    )
    live_send_probe_errors = _record_probe_errors(readiness_record, live_send_allowed=True)
    outbox_probe_errors = _record_probe_errors(
        readiness_record,
        outbox_message_written=True,
    )
    active_automation_submit_probe_errors = _record_probe_errors(
        active_automation_record,
        paper_order_submission_allowed=True,
    )
    broker_probe_errors = _record_probe_errors(readiness_record, broker_write_allowed=True)
    paper_order_probe_errors = _record_probe_errors(readiness_record, paper_order_allowed=True)
    position_close_probe_errors = _record_probe_errors(exit_record, position_close_allowed=True)
    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_probe["live_capital_enabled_count"] = 1
    live_capital_errors = validate_paperops_notification_review(live_capital_probe)
    unsafe_preview = deepcopy(readiness_record)
    unsafe_preview["message_preview"] = {
        "title": "Unsafe /Users/example",
        "body": "Dashboard: qadam.trade/dashboard/",
    }
    unsafe_preview_errors = validate_paperops_notification_record(unsafe_preview)
    event_probe = deepcopy(written)
    event_probe["event_log_written"] = False
    event_probe["event_log_event_count"] = 0
    event_errors = validate_paperops_notification_review(event_probe)

    print(f"paperops_notification_status={written['status']}")
    print(f"paperops_notification_schema_version={PAPEROPS_NOTIFICATION_REVIEW_SCHEMA_VERSION}")
    print(f"paperops_notification_artifact_path={output_path}")
    print(f"paperops_notification_history_path={history_path}")
    print(f"paperops_notification_event_log_path={event_log_path}")
    print(f"paperops_notification_mode={written['mode']}")
    print(f"paperops_notification_public_safe={written['public_safe']}")
    print(f"paperops_notification_recorded={written['recorded']}")
    print(f"paperops_notification_event_log_written={written['event_log_written']}")
    print(f"paperops_notification_event_log_events={replay['total_events']}")
    print(f"paperops_notification_type_count={written['notification_type_count']}")
    print(
        "paperops_notification_lifecycle_type_count="
        f"{written['lifecycle_notification_type_count']}"
    )
    print(f"paperops_notification_record_count={written['notification_record_count']}")
    print(f"paperops_notification_eligible_review_count={written['eligible_review_count']}")
    print(
        "paperops_notification_suppressed_count="
        f"{written['suppressed_notification_count']}"
    )
    print(f"paperops_notification_paperops_blocker_count={written['paperops_blocker_count']}")
    print(f"paperops_notification_paperops_blockers={','.join(written['paperops_blockers'])}")
    print(
        "paperops_notification_operations_record_status="
        f"{operations_record['status']}"
    )
    print(
        "paperops_notification_active_automation_record_status="
        f"{active_automation_record['status']}"
    )
    print(
        "paperops_notification_qctrl_hold_record_status="
        f"{qctrl_hold_record['status']}"
    )
    print(f"paperops_notification_readiness_status={written['readiness_status']}")
    print(f"paperops_notification_alpaca_post_status={written['alpaca_paper_post_status']}")
    print(f"paperops_notification_lifecycle_poller_status={written['lifecycle_poller_status']}")
    print(f"paperops_notification_exit_path_status={written['exit_path_status']}")
    print(
        "paperops_notification_source_submitted_paper_order_count="
        f"{written['source_submitted_paper_order_count']}"
    )
    print(
        "paperops_notification_source_broker_receipt_count="
        f"{written['source_broker_receipt_count']}"
    )
    print(
        "paperops_notification_source_paperops_30_day_operations_count="
        f"{written['source_paperops_30_day_operations_count']}"
    )
    print(
        "paperops_notification_source_active_paper_automation_count="
        f"{written['source_active_paper_automation_count']}"
    )
    print(
        "paperops_notification_source_qctrl_consultation_hold_count="
        f"{written['source_qctrl_consultation_hold_count']}"
    )
    print(
        "paperops_notification_source_open_position_count="
        f"{written['source_open_position_count']}"
    )
    print(
        "paperops_notification_source_closed_trade_count="
        f"{written['source_closed_trade_count']}"
    )
    print(
        "paperops_notification_source_postmortem_due_count="
        f"{written['source_postmortem_due_count']}"
    )
    print(
        "paperops_notification_source_exit_path_state_count="
        f"{written['source_exit_path_state_count']}"
    )
    print(f"paperops_notification_telegram_status={written['telegram_status']}")
    print(f"paperops_notification_telegram_mode={written['telegram_mode']}")
    print(f"paperops_notification_telegram_send_gate={written['telegram_send_gate']}")
    print(f"paperops_notification_send_test_gate_state={written['send_test_gate_state']}")
    print(
        "paperops_notification_send_test_approval_present="
        f"{written['send_test_approval_present']}"
    )
    print(
        "paperops_notification_private_send_test_allowed="
        f"{written['private_send_test_allowed']}"
    )
    for key in (
        "live_send_allowed_count",
        "telegram_command_path_enabled_count",
        "telegram_trade_command_enabled_count",
        "telegram_approve_trade_command_enabled_count",
        "telegram_close_trade_command_enabled_count",
        "broker_write_allowed_count",
        "broker_post_allowed_count",
        "paper_order_allowed_count",
        "position_close_allowed_count",
        "position_resize_allowed_count",
        "prediction_market_write_allowed_count",
        "crypto_perps_write_allowed_count",
        "live_endpoint_allowed_count",
        "live_capital_enabled_count",
        "phase7_proof_credit_allowed_count",
        "secret_value_exposed_count",
        "raw_payload_exposed_count",
        "authorization_header_exposed_count",
        "chat_id_exposed_count",
        "bot_token_exposed_count",
    ):
        print(f"paperops_notification_{key}={written[key]}")
    print(f"paperops_notification_validation_errors={validation_errors}")
    print(f"paperops_notification_command_probe_error_count={len(command_probe_errors)}")
    print(f"paperops_notification_approve_probe_error_count={len(approve_probe_errors)}")
    print(f"paperops_notification_close_probe_error_count={len(close_probe_errors)}")
    print(f"paperops_notification_live_send_probe_error_count={len(live_send_probe_errors)}")
    print(f"paperops_notification_outbox_probe_error_count={len(outbox_probe_errors)}")
    print(
        "paperops_notification_active_automation_submit_probe_error_count="
        f"{len(active_automation_submit_probe_errors)}"
    )
    print(f"paperops_notification_broker_probe_error_count={len(broker_probe_errors)}")
    print(f"paperops_notification_paper_order_probe_error_count={len(paper_order_probe_errors)}")
    print(
        "paperops_notification_position_close_probe_error_count="
        f"{len(position_close_probe_errors)}"
    )
    print(f"paperops_notification_live_capital_probe_error_count={len(live_capital_errors)}")
    print(f"paperops_notification_unsafe_preview_probe_error_count={len(unsafe_preview_errors)}")
    print(f"paperops_notification_missing_event_probe_error_count={len(event_errors)}")
    print(f"paperops_notification_boundary={written['boundary']}")

    if validation_errors:
        errors.extend(validation_errors)
    if written["status"] != "review_ready":
        errors.append("paperops_notification_not_review_ready")
    if replay["total_events"] != 1:
        errors.append("paperops_notification_event_log_did_not_record_once")
    if written["notification_type_count"] != len(PAPEROPS_NOTIFICATION_TYPES):
        errors.append("paperops_notification_type_count_mismatch")
    if written["lifecycle_notification_type_count"] != len(PAPEROPS_LIFECYCLE_NOTIFICATION_TYPES):
        errors.append("paperops_notification_lifecycle_type_count_mismatch")
    if written["notification_record_count"] != len(PAPEROPS_NOTIFICATION_TYPES):
        errors.append("paperops_notification_record_count_mismatch")
    if written["eligible_review_count"] < 1:
        errors.append("paperops_notification_expected_review_missing")
    if operations_record["status"] != "eligible_for_review":
        errors.append("paperops_notification_operations_record_not_eligible")
    if active_automation_record["status"] != "eligible_for_review":
        errors.append("paperops_notification_active_automation_record_not_eligible")
    if qctrl_hold_record["status"] != "eligible_for_review":
        errors.append("paperops_notification_qctrl_hold_record_not_eligible")
    if written["source_paperops_30_day_operations_count"] < 1:
        errors.append("paperops_notification_operations_source_missing")
    if written["source_active_paper_automation_count"] < 1:
        errors.append("paperops_notification_active_automation_source_missing")
    if written["source_qctrl_consultation_hold_count"] < 1:
        errors.append("paperops_notification_qctrl_hold_source_missing")
    if written["telegram_mode"] != "dry_run":
        errors.append("paperops_notification_not_dry_run")
    if written["telegram_send_gate"] != "disabled":
        errors.append("paperops_notification_send_gate_not_disabled")
    if written["normal_live_notification_allowed"] is not False:
        errors.append("paperops_notification_normal_live_notification_allowed")
    for key in (
        "live_send_allowed_count",
        "telegram_command_path_enabled_count",
        "telegram_trade_command_enabled_count",
        "telegram_approve_trade_command_enabled_count",
        "telegram_close_trade_command_enabled_count",
        "broker_write_allowed_count",
        "broker_post_allowed_count",
        "paper_order_allowed_count",
        "position_close_allowed_count",
        "position_resize_allowed_count",
        "prediction_market_write_allowed_count",
        "crypto_perps_write_allowed_count",
        "live_endpoint_allowed_count",
        "live_capital_enabled_count",
        "phase7_proof_credit_allowed_count",
        "secret_value_exposed_count",
        "raw_payload_exposed_count",
        "authorization_header_exposed_count",
        "chat_id_exposed_count",
        "bot_token_exposed_count",
    ):
        if written[key] != 0:
            errors.append(f"paperops_notification_unsafe_count_nonzero:{key}")
    expected_markers = (
        ("paperops_notification_authority_enabled:telegram_command_path_enabled", command_probe_errors),
        (
            "paperops_notification_authority_enabled:telegram_approve_trade_command_enabled",
            approve_probe_errors,
        ),
        (
            "paperops_notification_authority_enabled:telegram_close_trade_command_enabled",
            close_probe_errors,
        ),
        ("paperops_notification_authority_enabled:live_send_allowed", live_send_probe_errors),
        ("paperops_notification_outbox_written", outbox_probe_errors),
        (
            "paperops_notification_authority_enabled:paper_order_submission_allowed",
            active_automation_submit_probe_errors,
        ),
        ("paperops_notification_authority_enabled:broker_write_allowed", broker_probe_errors),
        ("paperops_notification_authority_enabled:paper_order_allowed", paper_order_probe_errors),
        (
            "paperops_notification_authority_enabled:position_close_allowed",
            position_close_probe_errors,
        ),
        ("paperops_notification_live_capital_enabled", live_capital_errors),
        ("paperops_notification_preview_forbidden_text", unsafe_preview_errors),
        ("paperops_notification_event_log_missing", event_errors),
    )
    for marker, probe_errors in expected_markers:
        if marker not in probe_errors:
            errors.append(f"paperops_notification_probe_not_rejected:{marker}")
    if "Telegram remains notify-only" not in written["boundary"]:
        errors.append("paperops_notification_boundary_weak")

    if errors:
        for error in errors:
            print(f"paperops_notification_error={error}")
        print("paperops_notification_review_check=failed")
        return 1

    print("paperops_notification_review_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
