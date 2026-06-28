#!/usr/bin/env python3
"""Validate the daily Telegram paper portfolio digest contract."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.telegram_daily_portfolio_digest import (  # noqa: E402
    TELEGRAM_DAILY_PORTFOLIO_DIGEST_SCHEMA_VERSION,
    build_daily_portfolio_digest,
    telegram_daily_portfolio_digest_paths,
    telegram_daily_portfolio_digest_public_status,
    validate_daily_portfolio_digest,
    write_daily_portfolio_digest,
)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_path = telegram_daily_portfolio_digest_paths(settings)
    if event_path.exists():
        event_path.unlink()

    artifact = build_daily_portfolio_digest(settings=settings, send_requested=False, force=False)
    output_path, history_path, event_path, written = write_daily_portfolio_digest(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_path,
    )
    validation_errors = validate_daily_portfolio_digest(written)
    replay = EventLog(event_path, echo=False).replay()
    public_status = telegram_daily_portfolio_digest_public_status(settings)
    forced_preview = build_daily_portfolio_digest(settings=settings, send_requested=False, force=True)
    forced_validation_errors = validate_daily_portfolio_digest(forced_preview)

    command_probe = deepcopy(forced_preview)
    command_probe["telegram_command_path_enabled"] = True
    command_probe_errors = validate_daily_portfolio_digest(command_probe)

    broker_probe = deepcopy(forced_preview)
    broker_probe["broker_write_allowed"] = True
    broker_probe_errors = validate_daily_portfolio_digest(broker_probe)

    live_capital_probe = deepcopy(forced_preview)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_errors = validate_daily_portfolio_digest(live_capital_probe)

    secret_probe = deepcopy(forced_preview)
    secret_probe["bot_token_exposed"] = True
    secret_probe_errors = validate_daily_portfolio_digest(secret_probe)

    print(f"telegram_daily_portfolio_digest_status={written['status']}")
    print(
        "telegram_daily_portfolio_digest_schema_version="
        f"{TELEGRAM_DAILY_PORTFOLIO_DIGEST_SCHEMA_VERSION}"
    )
    print(f"telegram_daily_portfolio_digest_artifact_path={output_path}")
    print(f"telegram_daily_portfolio_digest_history_path={history_path}")
    print(f"telegram_daily_portfolio_digest_event_log_path={event_path}")
    print(f"telegram_daily_portfolio_digest_local_date={written['local_date']}")
    print(f"telegram_daily_portfolio_digest_timezone={written['timezone']}")
    print(
        "telegram_daily_portfolio_digest_delivery_after_local_time="
        f"{written['delivery_after_local_time']}"
    )
    print(f"telegram_daily_portfolio_digest_due_for_delivery={written['due_for_delivery']}")
    print(f"telegram_daily_portfolio_digest_enabled={written['daily_portfolio_digest_enabled']}")
    print(f"telegram_daily_portfolio_digest_dry_run={written['daily_portfolio_digest_dry_run']}")
    print(f"telegram_daily_portfolio_digest_bot_configured={written['bot_configured']}")
    print(
        "telegram_daily_portfolio_digest_group_chat_configured="
        f"{written['group_chat_configured']}"
    )
    print(f"telegram_daily_portfolio_digest_send_requested={written['send_requested']}")
    print(f"telegram_daily_portfolio_digest_already_sent={written['already_sent']}")
    print(
        "telegram_daily_portfolio_digest_portfolio_balance_gbp="
        f"{written['portfolio_balance_gbp']}"
    )
    print(
        "telegram_daily_portfolio_digest_portfolio_total_pnl_gbp="
        f"{written['portfolio_total_pnl_gbp']}"
    )
    print(
        "telegram_daily_portfolio_digest_portfolio_performance_pct="
        f"{written['portfolio_performance_pct']}"
    )
    print(f"telegram_daily_portfolio_digest_daily_trade_count={written['daily_trade_count']}")
    print(
        "telegram_daily_portfolio_digest_paperops_idle_reason="
        f"{written['paperops_idle_reason']}"
    )
    print(
        "telegram_daily_portfolio_digest_specificity_status="
        f"{written['message_specificity_status']}"
    )
    print(
        "telegram_daily_portfolio_digest_specificity_score="
        f"{written['message_specificity_score']}"
    )
    print(
        "telegram_daily_portfolio_digest_forced_preview_status="
        f"{forced_preview['status']}"
    )
    print(
        "telegram_daily_portfolio_digest_forced_preview_due="
        f"{forced_preview['due_for_delivery']}"
    )
    print(
        "telegram_daily_portfolio_digest_forced_validation_errors="
        f"{forced_validation_errors}"
    )
    print(f"telegram_daily_portfolio_digest_event_log_events={replay['total_events']}")
    print(
        "telegram_daily_portfolio_digest_public_status="
        f"{public_status['status']}"
    )
    print(
        "telegram_daily_portfolio_digest_public_daily_trade_count="
        f"{public_status['daily_trade_count']}"
    )
    print(f"telegram_daily_portfolio_digest_validation_errors={validation_errors}")
    print(
        "telegram_daily_portfolio_digest_command_probe_error_count="
        f"{len(command_probe_errors)}"
    )
    print(
        "telegram_daily_portfolio_digest_broker_probe_error_count="
        f"{len(broker_probe_errors)}"
    )
    print(
        "telegram_daily_portfolio_digest_live_capital_probe_error_count="
        f"{len(live_capital_errors)}"
    )
    print(
        "telegram_daily_portfolio_digest_secret_probe_error_count="
        f"{len(secret_probe_errors)}"
    )

    if validation_errors:
        errors.extend(validation_errors)
    if replay["total_events"] != 1:
        errors.append("telegram_daily_portfolio_digest_event_log_count_mismatch")
    if forced_validation_errors:
        errors.extend(forced_validation_errors)
    if forced_preview["due_for_delivery"] is not True:
        errors.append("telegram_daily_portfolio_digest_force_not_due")
    if written.get("message_specificity_status") != "specific":
        errors.append("telegram_daily_portfolio_digest_not_specific")
    if int(written.get("message_specificity_score", 0) or 0) < 70:
        errors.append("telegram_daily_portfolio_digest_specificity_score_low")
    if not str(written.get("paperops_idle_reason") or "").strip():
        errors.append("telegram_daily_portfolio_digest_idle_reason_missing")
    preview_body = forced_preview.get("message_preview", {}).get("body", "")
    for phrase in ("paper portfolio", "Today Qadam recorded", "paper-trading update", "live capital remains off"):
        if phrase not in preview_body:
            errors.append(f"telegram_daily_portfolio_digest_preview_missing:{phrase}")
    for phrase in (
        "Portfolio balance:",
        "Performance:",
        "Why no/next trade:",
        "PaperOps context:",
        "Current impact:",
        "Dashboard:",
        "Mode:",
    ):
        if phrase in preview_body:
            errors.append(f"telegram_daily_portfolio_digest_preview_too_verbose:{phrase}")
    for phrase in (
        "PaperOps",
        "source_status=",
        "broker_status=",
        "idempotency_key",
        "submitted_to_alpaca_paper",
        "paperops_proxy_symbol_map",
    ):
        if phrase in preview_body:
            errors.append(f"telegram_daily_portfolio_digest_preview_internal_noise:{phrase}")
    if len([line for line in preview_body.splitlines() if line.strip()]) > 3:
        errors.append("telegram_daily_portfolio_digest_preview_too_many_lines")
    expected_probe_errors = (
        (
            "telegram_daily_portfolio_digest_authority_enabled:telegram_command_path_enabled",
            command_probe_errors,
        ),
        (
            "telegram_daily_portfolio_digest_authority_enabled:broker_write_allowed",
            broker_probe_errors,
        ),
        (
            "telegram_daily_portfolio_digest_authority_enabled:live_capital_enabled",
            live_capital_errors,
        ),
        (
            "telegram_daily_portfolio_digest_authority_enabled:bot_token_exposed",
            secret_probe_errors,
        ),
    )
    for marker, probe_errors in expected_probe_errors:
        if marker not in probe_errors:
            errors.append(f"telegram_daily_portfolio_digest_probe_not_rejected:{marker}")
    if public_status["telegram_command_path_enabled"] is not False:
        errors.append("telegram_daily_portfolio_digest_public_command_path_enabled")
    if public_status["broker_write_allowed"] is not False:
        errors.append("telegram_daily_portfolio_digest_public_broker_write_allowed")
    if public_status["paper_order_allowed"] is not False:
        errors.append("telegram_daily_portfolio_digest_public_paper_order_allowed")
    if public_status["live_capital_enabled"] is not False:
        errors.append("telegram_daily_portfolio_digest_public_live_capital_enabled")

    if errors:
        print("telegram_daily_portfolio_digest_check=failed")
        for error in errors:
            print(f"telegram_daily_portfolio_digest_error={error}")
        return 1
    print("telegram_daily_portfolio_digest_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
