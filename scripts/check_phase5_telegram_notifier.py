#!/usr/bin/env python3
"""Validate the Q5-10 Telegram notifier contract."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase5_telegram_notifier import (  # noqa: E402
    PHASE5_TELEGRAM_NOTIFIER_SCHEMA_VERSION,
    TELEGRAM_ALERT_TYPES,
    TELEGRAM_REQUIRED_CHECKS,
    build_phase5_telegram_notifier,
    telegram_notifier_paths,
    validate_phase5_telegram_notifier_bundle,
    validate_phase5_telegram_notifier_record,
    write_phase5_telegram_notifier,
)
from orchestrator.telegram_comms import FORBIDDEN_TELEGRAM_TEXT, TelegramCommunicationsStore  # noqa: E402


def _record(bundle: dict, alert_type: str) -> dict:
    for record in bundle.get("records", []):
        if isinstance(record, dict) and record.get("alert_type") == alert_type:
            return record
    raise RuntimeError(f"missing alert record {alert_type}")


def _record_errors(record: dict, **updates: object) -> list[str]:
    probe = deepcopy(record)
    for key, value in updates.items():
        probe[key] = value
    return validate_phase5_telegram_notifier_record(probe)


def _policy_probe_errors(record: dict, policy_key: str, field: str, value: object) -> list[str]:
    probe = deepcopy(record)
    policy = dict(probe.get(policy_key, {}))
    policy[field] = value
    probe[policy_key] = policy
    return validate_phase5_telegram_notifier_record(probe)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = telegram_notifier_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    bundle = build_phase5_telegram_notifier(settings=settings)
    output_path, history_path, event_log_path, written_bundle = write_phase5_telegram_notifier(
        bundle,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
        queue_outbox=True,
    )
    validation_errors = validate_phase5_telegram_notifier_bundle(written_bundle)
    event_replay = EventLog(event_log_path, echo=False).replay()
    risk_blocked = _record(written_bundle, "risk_blocked")
    kill_switch = _record(written_bundle, "kill_switch_change")
    degraded = _record(written_bundle, "degraded_source_or_venue")
    policy_blocked = _record(written_bundle, "policy_blocked")
    staged = _record(written_bundle, "staged_paper_order")

    command_probe_errors = _record_errors(risk_blocked, telegram_command_path_enabled=True)
    live_send_probe_errors = _record_errors(risk_blocked, live_send_allowed=True)
    place_trade_probe_errors = _record_errors(risk_blocked, telegram_place_trade_command_enabled=True)
    approve_trade_probe_errors = _record_errors(risk_blocked, telegram_approve_trade_command_enabled=True)
    reject_trade_probe_errors = _record_errors(risk_blocked, telegram_reject_trade_command_enabled=True)
    modify_trade_probe_errors = _record_errors(risk_blocked, telegram_modify_trade_command_enabled=True)
    resize_trade_probe_errors = _record_errors(risk_blocked, telegram_resize_trade_command_enabled=True)
    close_trade_probe_errors = _record_errors(risk_blocked, telegram_close_trade_command_enabled=True)
    cancel_trade_probe_errors = _record_errors(risk_blocked, telegram_cancel_trade_command_enabled=True)
    broker_write_probe_errors = _record_errors(risk_blocked, broker_write_allowed=True)
    paper_order_probe_errors = _record_errors(risk_blocked, paper_order_allowed=True)
    paper_submitted_probe_errors = _record_errors(risk_blocked, paper_order_submitted=True)
    live_capital_probe_errors = _record_errors(risk_blocked, live_capital_enabled=True)
    backend_missing_probe_errors = _record_errors(
        risk_blocked,
        status="eligible",
        backend_state_count=0,
        backend_state_matched=False,
    )
    outbox_send_probe_errors = _record_errors(
        risk_blocked,
        outbox_send_allowed=True,
        outbox_message_written=True,
    )
    raw_payload_probe_errors = _record_errors(risk_blocked, raw_payload_exposed=True)
    chat_id_probe_errors = _record_errors(risk_blocked, chat_id_exposed=True)
    bot_token_probe_errors = _record_errors(risk_blocked, bot_token_exposed=True)
    missing_delivery_policy_errors = deepcopy(risk_blocked)
    missing_delivery_policy_errors.pop("delivery_policy", None)
    missing_delivery_policy = validate_phase5_telegram_notifier_record(missing_delivery_policy_errors)
    retry_live_probe_errors = _policy_probe_errors(
        risk_blocked,
        "retry_policy",
        "live_retry_enabled",
        True,
    )
    fallback_broker_probe_errors = _policy_probe_errors(
        risk_blocked,
        "fallback_policy",
        "broker_action_on_failure",
        True,
    )

    outbox = TelegramCommunicationsStore(settings=settings).read_outbox()
    outbox_by_id = {message.message_id: message for message in outbox}
    q5_written_records = [
        record
        for record in written_bundle.get("records", [])
        if isinstance(record, dict) and record.get("outbox_message_written") is True
    ]

    print("phase5_telegram_notifier_status=" + written_bundle["status"])
    print(f"phase5_telegram_notifier_schema_version={PHASE5_TELEGRAM_NOTIFIER_SCHEMA_VERSION}")
    print(f"phase5_telegram_notifier_artifact_path={output_path}")
    print(f"phase5_telegram_notifier_history_path={history_path}")
    print(f"phase5_telegram_notifier_event_log_path={event_log_path}")
    print(f"phase5_telegram_notifier_alert_type_count={written_bundle['alert_type_count']}")
    print(
        "phase5_telegram_notifier_notification_record_count="
        f"{written_bundle['notification_record_count']}"
    )
    print(f"phase5_telegram_notifier_eligible_alert_count={written_bundle['eligible_alert_count']}")
    print(f"phase5_telegram_notifier_suppressed_alert_count={written_bundle['suppressed_alert_count']}")
    print(
        "phase5_telegram_notifier_queued_dry_run_alert_count="
        f"{written_bundle['queued_dry_run_alert_count']}"
    )
    print(
        "phase5_telegram_notifier_outbox_message_written_count="
        f"{written_bundle['outbox_message_written_count']}"
    )
    print(f"phase5_telegram_notifier_telegram_status={written_bundle['telegram_status']}")
    print(f"phase5_telegram_notifier_telegram_mode={written_bundle['telegram_mode']}")
    print(f"phase5_telegram_notifier_send_gate={written_bundle['telegram_send_gate']}")
    print(f"phase5_telegram_notifier_send_test_gate_state={written_bundle['send_test_gate_state']}")
    print(
        "phase5_telegram_notifier_private_send_test_allowed="
        f"{written_bundle['private_send_test_allowed']}"
    )
    print(f"phase5_telegram_notifier_event_log_written={written_bundle['event_log_written']}")
    print(f"phase5_telegram_notifier_event_log_total_events={event_replay['total_events']}")
    print(f"phase5_telegram_notifier_validation_error_count={len(validation_errors)}")
    print(f"phase5_telegram_notifier_risk_blocked_state_count={risk_blocked['backend_state_count']}")
    print(f"phase5_telegram_notifier_kill_switch_state_count={kill_switch['backend_state_count']}")
    print(f"phase5_telegram_notifier_degraded_state_count={degraded['backend_state_count']}")
    print(f"phase5_telegram_notifier_policy_blocked_state_count={policy_blocked['backend_state_count']}")
    print(f"phase5_telegram_notifier_staged_state_count={staged['backend_state_count']}")
    for key in (
        "telegram_command_path_enabled_count",
        "telegram_trade_command_enabled_count",
        "telegram_place_trade_command_enabled_count",
        "telegram_approve_trade_command_enabled_count",
        "telegram_reject_trade_command_enabled_count",
        "telegram_modify_trade_command_enabled_count",
        "telegram_resize_trade_command_enabled_count",
        "telegram_close_trade_command_enabled_count",
        "telegram_cancel_trade_command_enabled_count",
        "telegram_live_notifications_allowed_count",
        "live_send_allowed_count",
        "broker_write_allowed_count",
        "broker_post_called_count",
        "paper_order_allowed_count",
        "paper_order_submitted_count",
        "execution_allowed_count",
        "prediction_market_write_allowed_count",
        "live_endpoint_allowed_count",
        "live_capital_enabled_count",
        "secret_value_exposed_count",
        "raw_payload_exposed_count",
        "local_path_exposed_count",
        "authorization_header_exposed_count",
        "chat_id_exposed_count",
        "bot_token_exposed_count",
    ):
        print(f"phase5_telegram_notifier_{key}={written_bundle[key]}")
    print(f"phase5_telegram_notifier_command_probe_error_count={len(command_probe_errors)}")
    print(f"phase5_telegram_notifier_live_send_probe_error_count={len(live_send_probe_errors)}")
    print(f"phase5_telegram_notifier_place_trade_probe_error_count={len(place_trade_probe_errors)}")
    print(f"phase5_telegram_notifier_approve_trade_probe_error_count={len(approve_trade_probe_errors)}")
    print(f"phase5_telegram_notifier_reject_trade_probe_error_count={len(reject_trade_probe_errors)}")
    print(f"phase5_telegram_notifier_modify_trade_probe_error_count={len(modify_trade_probe_errors)}")
    print(f"phase5_telegram_notifier_resize_trade_probe_error_count={len(resize_trade_probe_errors)}")
    print(f"phase5_telegram_notifier_close_trade_probe_error_count={len(close_trade_probe_errors)}")
    print(f"phase5_telegram_notifier_cancel_trade_probe_error_count={len(cancel_trade_probe_errors)}")
    print(f"phase5_telegram_notifier_broker_write_probe_error_count={len(broker_write_probe_errors)}")
    print(f"phase5_telegram_notifier_paper_order_probe_error_count={len(paper_order_probe_errors)}")
    print(f"phase5_telegram_notifier_paper_submitted_probe_error_count={len(paper_submitted_probe_errors)}")
    print(f"phase5_telegram_notifier_live_capital_probe_error_count={len(live_capital_probe_errors)}")
    print(f"phase5_telegram_notifier_backend_missing_probe_error_count={len(backend_missing_probe_errors)}")
    print(f"phase5_telegram_notifier_outbox_send_probe_error_count={len(outbox_send_probe_errors)}")
    print(f"phase5_telegram_notifier_raw_payload_probe_error_count={len(raw_payload_probe_errors)}")
    print(f"phase5_telegram_notifier_chat_id_probe_error_count={len(chat_id_probe_errors)}")
    print(f"phase5_telegram_notifier_bot_token_probe_error_count={len(bot_token_probe_errors)}")
    print(f"phase5_telegram_notifier_missing_delivery_policy_probe_error_count={len(missing_delivery_policy)}")
    print(f"phase5_telegram_notifier_retry_live_probe_error_count={len(retry_live_probe_errors)}")
    print(f"phase5_telegram_notifier_fallback_broker_probe_error_count={len(fallback_broker_probe_errors)}")
    print("phase5_telegram_notifier_boundary=" + written_bundle["boundary"])

    if validation_errors:
        errors.extend(validation_errors)
    if written_bundle["status"] != "ok":
        errors.append("telegram_notifier_bundle_not_ok")
    if written_bundle["alert_type_count"] != len(TELEGRAM_ALERT_TYPES):
        errors.append("telegram_notifier_alert_type_count_mismatch")
    if written_bundle["notification_record_count"] != len(TELEGRAM_ALERT_TYPES):
        errors.append("telegram_notifier_record_count_mismatch")
    if written_bundle["eligible_alert_count"] < 3:
        errors.append("telegram_notifier_expected_eligible_alerts_missing")
    if written_bundle["suppressed_alert_count"] < 1:
        errors.append("telegram_notifier_suppressed_alerts_missing")
    if written_bundle["queued_dry_run_alert_count"] != written_bundle["eligible_alert_count"]:
        errors.append("telegram_notifier_queued_count_mismatch")
    if written_bundle["outbox_message_written_count"] != written_bundle["eligible_alert_count"]:
        errors.append("telegram_notifier_outbox_written_count_mismatch")
    if written_bundle["required_check_count"] != len(TELEGRAM_REQUIRED_CHECKS):
        errors.append("telegram_notifier_required_check_count_mismatch")
    if written_bundle["telegram_mode"] != "dry_run":
        errors.append("telegram_notifier_mode_not_dry_run")
    if written_bundle["telegram_send_gate"] != "disabled":
        errors.append("telegram_notifier_send_gate_not_disabled")
    if written_bundle["private_send_test_allowed"] is not False:
        errors.append("telegram_notifier_private_send_test_allowed_without_gate")
    if written_bundle["event_log_written"] is not True:
        errors.append("telegram_notifier_event_log_not_written")
    if event_replay["total_events"] != written_bundle["notification_record_count"]:
        errors.append("telegram_notifier_event_log_count_mismatch")
    for record in q5_written_records:
        message_id = str(record.get("outbox_message_id") or "")
        message = outbox_by_id.get(message_id)
        if message is None:
            errors.append(f"telegram_notifier_outbox_message_missing:{message_id}")
            continue
        if message.mode != "dry_run":
            errors.append(f"telegram_notifier_outbox_message_not_dry_run:{message_id}")
        if message.status != "queued":
            errors.append(f"telegram_notifier_outbox_message_not_queued:{message_id}")
        if message.send_allowed:
            errors.append(f"telegram_notifier_outbox_message_send_allowed:{message_id}")
        if "Dashboard: qadam.trade/dashboard/" not in message.body:
            errors.append(f"telegram_notifier_outbox_dashboard_missing:{message_id}")
        for pattern in FORBIDDEN_TELEGRAM_TEXT:
            if pattern.search(message.title) or pattern.search(message.body):
                errors.append(f"telegram_notifier_outbox_forbidden_text:{message_id}")
                break
    for key in (
        "telegram_command_path_enabled_count",
        "telegram_trade_command_enabled_count",
        "telegram_place_trade_command_enabled_count",
        "telegram_approve_trade_command_enabled_count",
        "telegram_reject_trade_command_enabled_count",
        "telegram_modify_trade_command_enabled_count",
        "telegram_resize_trade_command_enabled_count",
        "telegram_close_trade_command_enabled_count",
        "telegram_cancel_trade_command_enabled_count",
        "telegram_live_notifications_allowed_count",
        "live_send_allowed_count",
        "broker_write_allowed_count",
        "broker_post_called_count",
        "paper_order_allowed_count",
        "paper_order_submitted_count",
        "execution_allowed_count",
        "prediction_market_write_allowed_count",
        "live_endpoint_allowed_count",
        "live_capital_enabled_count",
        "secret_value_exposed_count",
        "raw_payload_exposed_count",
        "local_path_exposed_count",
        "authorization_header_exposed_count",
        "chat_id_exposed_count",
        "bot_token_exposed_count",
    ):
        if written_bundle.get(key) != 0:
            errors.append(f"telegram_notifier_boundary_count_not_zero:{key}")
    expected_probe_markers = (
        ("telegram_boundary_enabled:telegram_command_path_enabled", command_probe_errors),
        ("telegram_live_send_allowed", live_send_probe_errors),
        ("telegram_boundary_enabled:telegram_place_trade_command_enabled", place_trade_probe_errors),
        ("telegram_boundary_enabled:telegram_approve_trade_command_enabled", approve_trade_probe_errors),
        ("telegram_boundary_enabled:telegram_reject_trade_command_enabled", reject_trade_probe_errors),
        ("telegram_boundary_enabled:telegram_modify_trade_command_enabled", modify_trade_probe_errors),
        ("telegram_boundary_enabled:telegram_resize_trade_command_enabled", resize_trade_probe_errors),
        ("telegram_boundary_enabled:telegram_close_trade_command_enabled", close_trade_probe_errors),
        ("telegram_boundary_enabled:telegram_cancel_trade_command_enabled", cancel_trade_probe_errors),
        ("phase5_authority_enabled:broker_write_allowed", broker_write_probe_errors),
        ("phase5_authority_enabled:paper_order_allowed", paper_order_probe_errors),
        ("telegram_boundary_enabled:paper_order_submitted", paper_submitted_probe_errors),
        ("phase5_authority_enabled:live_capital_enabled", live_capital_probe_errors),
        ("eligible_without_backend_state", backend_missing_probe_errors),
        ("outbox_send_allowed", outbox_send_probe_errors),
        ("telegram_exposure_enabled:raw_payload_exposed", raw_payload_probe_errors),
        ("telegram_exposure_enabled:chat_id_exposed", chat_id_probe_errors),
        ("telegram_exposure_enabled:bot_token_exposed", bot_token_probe_errors),
        ("delivery_policy_missing_or_invalid", missing_delivery_policy),
        ("retry_policy_live_retry_enabled", retry_live_probe_errors),
        ("fallback_policy_broker_action_enabled", fallback_broker_probe_errors),
    )
    for marker, probe_errors in expected_probe_markers:
        if marker not in probe_errors:
            errors.append(f"telegram_notifier_probe_not_rejected:{marker}")
    if "cannot place, approve, reject, modify, resize, close, or cancel trades" not in written_bundle["boundary"]:
        errors.append("telegram_notifier_boundary_weak")

    if errors:
        for error in errors:
            print(f"phase5_telegram_notifier_error={error}")
        print("phase5_telegram_notifier_check=failed")
        return 1

    print("phase5_telegram_notifier_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
