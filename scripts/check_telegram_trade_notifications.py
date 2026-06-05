#!/usr/bin/env python3
"""Validate Telegram group alerts for submitted paper trade decisions."""

from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.telegram_trade_notifications import (  # noqa: E402
    TELEGRAM_TRADE_NOTIFICATIONS_SCHEMA_VERSION,
    build_telegram_trade_notifications,
    telegram_trade_notifications_paths,
    validate_telegram_trade_notification_record,
    validate_telegram_trade_notifications,
    write_telegram_trade_notifications,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--send-live",
        action="store_true",
        help=(
            "Actually send eligible submitted-paper-order notifications to the "
            "configured Telegram group when the trade notification live gate is enabled."
        ),
    )
    return parser.parse_args()


def _first_record(artifact: dict) -> dict:
    for record in artifact.get("records", []):
        if isinstance(record, dict):
            return record
    return {}


def main() -> int:
    args = _parse_args()
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_path = telegram_trade_notifications_paths(settings)
    if event_path.exists():
        event_path.unlink()

    artifact = build_telegram_trade_notifications(
        settings=settings,
        send_requested=args.send_live,
    )
    output_path, history_path, event_path, written = write_telegram_trade_notifications(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_path,
    )
    validation_errors = validate_telegram_trade_notifications(written)
    replay = EventLog(event_path, echo=False).replay()
    record = _first_record(written)

    command_probe = deepcopy(record)
    command_probe["telegram_command_path_enabled"] = True
    command_errors = validate_telegram_trade_notification_record(command_probe) if record else []

    broker_probe = deepcopy(record)
    broker_probe["broker_write_allowed"] = True
    broker_errors = validate_telegram_trade_notification_record(broker_probe) if record else []

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_errors = validate_telegram_trade_notifications(live_capital_probe)

    secret_probe = deepcopy(written)
    secret_probe["bot_token_exposed"] = True
    secret_errors = validate_telegram_trade_notifications(secret_probe)

    print(f"telegram_trade_notifications_status={written['status']}")
    print(
        "telegram_trade_notifications_schema_version="
        f"{TELEGRAM_TRADE_NOTIFICATIONS_SCHEMA_VERSION}"
    )
    print(f"telegram_trade_notifications_artifact_path={output_path}")
    print(f"telegram_trade_notifications_history_path={history_path}")
    print(f"telegram_trade_notifications_event_log_path={event_path}")
    print(f"telegram_trade_notifications_mode={written['mode']}")
    print(f"telegram_trade_notifications_send_requested={written['send_requested']}")
    print(
        "telegram_trade_notifications_enabled="
        f"{written['trade_group_notifications_enabled']}"
    )
    print(
        "telegram_trade_notifications_dry_run="
        f"{written['trade_group_notifications_dry_run']}"
    )
    print(f"telegram_trade_notifications_bot_configured={written['bot_configured']}")
    print(
        "telegram_trade_notifications_group_chat_configured="
        f"{written['group_chat_configured']}"
    )
    print(
        "telegram_trade_notifications_source_selected_record_count="
        f"{written['source_selected_record_count']}"
    )
    print(
        "telegram_trade_notifications_eligible_count="
        f"{written['eligible_notification_count']}"
    )
    print(
        "telegram_trade_notifications_live_send_attempted_count="
        f"{written['live_send_attempted_count']}"
    )
    print(
        "telegram_trade_notifications_live_send_succeeded_count="
        f"{written['live_send_succeeded_count']}"
    )
    print(
        "telegram_trade_notifications_failed_delivery_count="
        f"{written['failed_delivery_count']}"
    )
    print(
        "telegram_trade_notifications_already_sent_count="
        f"{written['already_sent_count']}"
    )
    if record:
        print(
            "telegram_trade_notifications_trade_summary="
            f"{record.get('trade_summary')}"
        )
        print(
            "telegram_trade_notifications_portfolio_value_gbp="
            f"{record.get('portfolio_value_gbp')}"
        )
        print(
            "telegram_trade_notifications_portfolio_total_pnl_gbp="
            f"{record.get('portfolio_total_pnl_gbp')}"
        )
        print(
            "telegram_trade_notifications_portfolio_performance_pct="
            f"{record.get('portfolio_performance_pct')}"
        )
        print(
            "telegram_trade_notifications_specificity_status="
            f"{record.get('message_specificity_status')}"
        )
        print(
            "telegram_trade_notifications_specificity_score="
            f"{record.get('message_specificity_score')}"
        )
    print(f"telegram_trade_notifications_event_log_events={replay['total_events']}")
    print(f"telegram_trade_notifications_validation_errors={validation_errors}")
    print(
        "telegram_trade_notifications_command_probe_error_count="
        f"{len(command_errors)}"
    )
    print(
        "telegram_trade_notifications_broker_probe_error_count="
        f"{len(broker_errors)}"
    )
    print(
        "telegram_trade_notifications_live_capital_probe_error_count="
        f"{len(live_capital_errors)}"
    )
    print(
        "telegram_trade_notifications_secret_probe_error_count="
        f"{len(secret_errors)}"
    )

    if validation_errors:
        errors.extend(validation_errors)
    if replay["total_events"] != 1:
        errors.append("telegram_trade_notifications_event_log_count_mismatch")
    if written["mode"] != "paper":
        errors.append("telegram_trade_notifications_mode_not_paper")
    if written["live_capital_enabled"] is not False:
        errors.append("telegram_trade_notifications_live_capital_enabled")
    if not args.send_live and written["live_send_attempted_count"] != 0:
        errors.append("telegram_trade_notifications_sent_without_send_live")
    if written["trade_group_notifications_dry_run"] is True and written["live_send_attempted_count"] != 0:
        errors.append("telegram_trade_notifications_sent_in_dry_run")
    if written["trade_group_notifications_enabled"] is False and written["live_send_attempted_count"] != 0:
        errors.append("telegram_trade_notifications_sent_while_disabled")
    for field in (
        "telegram_command_path_enabled",
        "telegram_trade_command_enabled",
        "broker_write_allowed",
        "paper_order_allowed",
        "paper_order_submission_allowed",
        "position_close_allowed",
        "live_endpoint_allowed",
        "phase7_proof_credit_allowed",
        "secret_value_exposed",
        "chat_id_exposed",
        "bot_token_exposed",
        "broker_order_identifier_exposed",
    ):
        if written.get(field) is not False:
            errors.append(f"telegram_trade_notifications_forbidden_enabled:{field}")
    if record:
        expected = (
            (
                "telegram_trade_notification_authority_enabled:telegram_command_path_enabled",
                command_errors,
            ),
            (
                "telegram_trade_notification_authority_enabled:broker_write_allowed",
                broker_errors,
            ),
            (
                "telegram_trade_notifications_authority_enabled:live_capital_enabled",
                live_capital_errors,
            ),
            (
                "telegram_trade_notifications_authority_enabled:bot_token_exposed",
                secret_errors,
            ),
        )
        for marker, probe_errors in expected:
            if marker not in probe_errors:
                errors.append(f"telegram_trade_notifications_probe_not_rejected:{marker}")
    if "cannot create trade candidates" not in written["boundary"]:
        errors.append("telegram_trade_notifications_boundary_weak")
    if record:
        preview = record.get("message_preview", {})
        body = str(preview.get("body") or "") if isinstance(preview, dict) else ""
        for marker in (
            "Trade:",
            "Why this trade was sent:",
            "Evidence:",
            "Portfolio:",
            "Performance:",
            "Current impact:",
            "Mode: paper only; live capital remains blocked.",
            "Dashboard: qadam.trade/dashboard/",
        ):
            if marker not in body:
                errors.append(f"telegram_trade_notifications_message_marker_missing:{marker}")
        if "%" not in body:
            errors.append("telegram_trade_notifications_message_percent_missing")
        if record.get("portfolio_value_gbp") is None:
            errors.append("telegram_trade_notifications_portfolio_value_missing")
        if record.get("portfolio_performance_pct") is None:
            errors.append("telegram_trade_notifications_portfolio_performance_missing")
        if record.get("message_specificity_status") != "specific":
            errors.append("telegram_trade_notifications_not_specific")
        if int(record.get("message_specificity_score", 0) or 0) < 70:
            errors.append("telegram_trade_notifications_specificity_score_low")

    if errors:
        for error in errors:
            print(f"telegram_trade_notifications_error={error}")
        print("telegram_trade_notifications_check=failed")
        return 1

    print("telegram_trade_notifications_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
