#!/usr/bin/env python3
"""Run the guarded PT-8 active paper-trading automation controller."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.paperops_active_paper_trading_automation import (  # noqa: E402
    build_paperops_active_paper_trading_automation,
    paperops_active_paper_trading_automation_paths,
    validate_paperops_active_paper_trading_automation,
    write_paperops_active_paper_trading_automation,
)
from orchestrator.telegram_trade_notifications import (  # noqa: E402
    build_telegram_trade_notifications,
    telegram_trade_notifications_paths,
    validate_telegram_trade_notifications,
    write_telegram_trade_notifications,
)
from orchestrator.telegram_daily_portfolio_digest import (  # noqa: E402
    build_daily_portfolio_digest,
    telegram_daily_portfolio_digest_paths,
    validate_daily_portfolio_digest,
    write_daily_portfolio_digest,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute-paper-automation",
        action="store_true",
        help=(
            "Allow this controller to delegate to PaperOps-2/3/4 explicit "
            "paper-only flags when the recorded PT-8 gates allow it."
        ),
    )
    return parser.parse_args()


def _parse_output(output: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in output.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def _run_step(label: str, script: str, *args: str) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, script, *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    parsed = _parse_output(stdout)
    return {
        "label": label,
        "script": script,
        "args": list(args),
        "returncode": result.returncode,
        "ok": result.returncode == 0,
        "parsed": parsed,
        "stdout_tail": stdout.splitlines()[-12:],
        "stderr_tail": stderr.splitlines()[-12:],
        "live_endpoint_called_count": int(
            parsed.get(
                {
                    "paper_submit": "paperops_alpaca_post_live_endpoint_called_count",
                    "paper_poll": "paperops_lifecycle_poller_live_endpoint_called_count",
                    "paper_exit": "paperops_exit_live_endpoint_called_count",
                    "first_week_trade_mandate": "live_endpoint_called_count",
                    "first_week_trade_mandate_refresh": "live_endpoint_called_count",
                }.get(label, "live_endpoint_called_count"),
                "0",
            )
            or 0
        ),
        "live_capital_enabled": parsed.get(
            {
                "paper_submit": "paperops_alpaca_post_live_capital_enabled",
                "paper_poll": "paperops_lifecycle_poller_live_capital_enabled",
                "paper_exit": "paperops_exit_live_capital_enabled",
                "first_week_trade_mandate": (
                    "paperops_first_week_trade_mandate_live_capital_enabled"
                ),
                "first_week_trade_mandate_refresh": (
                    "paperops_first_week_trade_mandate_live_capital_enabled"
                ),
            }.get(label, "live_capital_enabled"),
            "False",
        )
        == "True",
        "secret_value_exposed": False,
    }


def _run_telegram_trade_notifications(settings: Settings) -> dict[str, Any]:
    output_path, history_path, event_path = telegram_trade_notifications_paths(settings)
    if event_path.exists():
        event_path.unlink()
    artifact = build_telegram_trade_notifications(
        settings=settings,
        send_requested=True,
    )
    output_path, history_path, event_path, written = write_telegram_trade_notifications(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_path,
    )
    validation_errors = validate_telegram_trade_notifications(written)
    first_record = next(
        (record for record in written.get("records", []) if isinstance(record, dict)),
        {},
    )
    return {
        "label": "telegram_trade_notification",
        "script": "orchestrator.telegram_trade_notifications",
        "args": ["send_requested=True"],
        "returncode": 0 if not validation_errors else 1,
        "ok": not validation_errors,
        "parsed": {
            "telegram_trade_notifications_status": str(written.get("status")),
            "telegram_trade_notifications_eligible_count": str(
                written.get("eligible_notification_count", 0)
            ),
            "telegram_trade_notifications_live_send_attempted_count": str(
                written.get("live_send_attempted_count", 0)
            ),
            "telegram_trade_notifications_live_send_succeeded_count": str(
                written.get("live_send_succeeded_count", 0)
            ),
            "telegram_trade_notifications_trade_summary": str(
                first_record.get("trade_summary", "")
            ),
            "telegram_trade_notifications_portfolio_value_gbp": str(
                first_record.get("portfolio_value_gbp", "")
            ),
            "telegram_trade_notifications_portfolio_performance_pct": str(
                first_record.get("portfolio_performance_pct", "")
            ),
            "telegram_trade_notifications_artifact_path": str(output_path),
            "telegram_trade_notifications_history_path": str(history_path),
        },
        "stdout_tail": [
            f"telegram_trade_notifications_status={written.get('status')}",
            "telegram_trade_notifications_eligible_count="
            f"{written.get('eligible_notification_count', 0)}",
            "telegram_trade_notifications_live_send_attempted_count="
            f"{written.get('live_send_attempted_count', 0)}",
            "telegram_trade_notifications_live_send_succeeded_count="
            f"{written.get('live_send_succeeded_count', 0)}",
            "telegram_trade_notifications_trade_summary="
            f"{first_record.get('trade_summary', '')}",
            "telegram_trade_notifications_portfolio_value_gbp="
            f"{first_record.get('portfolio_value_gbp', '')}",
            "telegram_trade_notifications_portfolio_performance_pct="
            f"{first_record.get('portfolio_performance_pct', '')}",
        ],
        "stderr_tail": [],
        "live_endpoint_called_count": 0,
        "live_capital_enabled": False,
        "secret_value_exposed": False,
    }


def _run_daily_portfolio_digest(settings: Settings) -> dict[str, Any]:
    output_path, history_path, event_path = telegram_daily_portfolio_digest_paths(settings)
    if event_path.exists():
        event_path.unlink()
    artifact = build_daily_portfolio_digest(
        settings=settings,
        send_requested=True,
        force=False,
    )
    output_path, history_path, event_path, written = write_daily_portfolio_digest(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_path,
    )
    validation_errors = validate_daily_portfolio_digest(written)
    return {
        "label": "telegram_daily_portfolio_digest",
        "script": "orchestrator.telegram_daily_portfolio_digest",
        "args": ["send_requested=True", "force=False"],
        "returncode": 0 if not validation_errors and written.get("status") != "failed" else 1,
        "ok": not validation_errors and written.get("status") != "failed",
        "parsed": {
            "telegram_daily_portfolio_digest_status": str(written.get("status")),
            "telegram_daily_portfolio_digest_due_for_delivery": str(
                written.get("due_for_delivery")
            ),
            "telegram_daily_portfolio_digest_portfolio_balance_gbp": str(
                written.get("portfolio_balance_gbp", "")
            ),
            "telegram_daily_portfolio_digest_portfolio_performance_pct": str(
                written.get("portfolio_performance_pct", "")
            ),
            "telegram_daily_portfolio_digest_daily_trade_count": str(
                written.get("daily_trade_count", 0)
            ),
            "telegram_daily_portfolio_digest_live_send_attempted": str(
                written.get("live_send_attempted")
            ),
            "telegram_daily_portfolio_digest_live_send_succeeded": str(
                written.get("live_send_succeeded")
            ),
            "telegram_daily_portfolio_digest_artifact_path": str(output_path),
            "telegram_daily_portfolio_digest_history_path": str(history_path),
        },
        "stdout_tail": [
            f"telegram_daily_portfolio_digest_status={written.get('status')}",
            "telegram_daily_portfolio_digest_due_for_delivery="
            f"{written.get('due_for_delivery')}",
            "telegram_daily_portfolio_digest_portfolio_balance_gbp="
            f"{written.get('portfolio_balance_gbp', '')}",
            "telegram_daily_portfolio_digest_portfolio_performance_pct="
            f"{written.get('portfolio_performance_pct', '')}",
            "telegram_daily_portfolio_digest_daily_trade_count="
            f"{written.get('daily_trade_count', 0)}",
            "telegram_daily_portfolio_digest_live_send_attempted="
            f"{written.get('live_send_attempted')}",
            "telegram_daily_portfolio_digest_live_send_succeeded="
            f"{written.get('live_send_succeeded')}",
        ],
        "stderr_tail": [],
        "live_endpoint_called_count": 0,
        "live_capital_enabled": False,
        "secret_value_exposed": False,
    }


def main() -> int:
    args = _parse_args()
    settings = Settings.from_env()
    output_path, history_path, event_path = (
        paperops_active_paper_trading_automation_paths(settings)
    )
    if event_path.exists():
        event_path.unlink()

    action_records: list[dict[str, Any]] = []
    command_failed = False

    if args.execute_paper_automation:
        mandate = _run_step(
            "first_week_trade_mandate",
            "scripts/check_paperops_first_week_paper_trade_mandate.py",
        )
        action_records.append(mandate)
        command_failed = command_failed or not mandate["ok"]

    initial = build_paperops_active_paper_trading_automation(
        settings=settings,
        execute_automation_requested=args.execute_paper_automation,
        action_records=action_records,
    )

    if args.execute_paper_automation:
        max_submit_attempts = int(
            initial.get("rs5_max_guarded_submit_attempts_per_run", 0) or 0
        )
        submit_attempt_count = 0
        while submit_attempt_count < max_submit_attempts:
            current = build_paperops_active_paper_trading_automation(
                settings=settings,
                execute_automation_requested=args.execute_paper_automation,
                action_records=action_records,
            )
            if current.get("paper_submit_step_allowed") is not True:
                break
            submit = _run_step(
                "paper_submit",
                "scripts/check_paperops_alpaca_paper_post.py",
                "--submit-paper-order",
            )
            action_records.append(submit)
            command_failed = command_failed or not submit["ok"]
            submit_attempt_count += 1

            refresh = _run_step(
                "first_week_trade_mandate_refresh",
                "scripts/check_paperops_first_week_paper_trade_mandate.py",
            )
            action_records.append(refresh)
            command_failed = command_failed or not refresh["ok"]

            if submit["parsed"].get("paperops_alpaca_post_status") != (
                "submitted_to_alpaca_paper"
            ):
                break

        after_submit = build_paperops_active_paper_trading_automation(
            settings=settings,
            execute_automation_requested=args.execute_paper_automation,
            action_records=action_records,
        )
        if after_submit.get("paper_poll_step_allowed") is True:
            poll = _run_step(
                "paper_poll",
                "scripts/check_paperops_paper_lifecycle_poller.py",
                "--poll-paper-orders",
            )
            action_records.append(poll)
            command_failed = command_failed or not poll["ok"]

        telegram_step = _run_telegram_trade_notifications(settings)
        action_records.append(telegram_step)
        command_failed = command_failed or not telegram_step["ok"]

        daily_digest_step = _run_daily_portfolio_digest(settings)
        action_records.append(daily_digest_step)
        command_failed = command_failed or not daily_digest_step["ok"]

    final = build_paperops_active_paper_trading_automation(
        settings=settings,
        execute_automation_requested=args.execute_paper_automation,
        action_records=action_records,
    )
    _, _, _, written = write_paperops_active_paper_trading_automation(
        final,
        settings=settings,
        record_event=True,
        event_log_path=event_path,
    )
    validation_errors = validate_paperops_active_paper_trading_automation(written)

    print(f"paperops_active_runner_status={written['status']}")
    print(f"paperops_active_runner_artifact_path={output_path}")
    print(f"paperops_active_runner_history_path={history_path}")
    print(f"paperops_active_runner_event_log_path={event_path}")
    print(
        "paperops_active_runner_execute_requested="
        f"{written['execute_automation_requested']}"
    )
    print(
        "paperops_active_runner_submit_step_allowed="
        f"{written['paper_submit_step_allowed']}"
    )
    print(
        "paperops_active_runner_unattended_delegation_enabled="
        f"{written['unattended_paper_execution_delegation_enabled']}"
    )
    print(
        "paperops_active_runner_unattended_delegation_reason="
        f"{written['unattended_paper_execution_delegation_reason']}"
    )
    print(
        "paperops_active_runner_fresh_submit_count="
        f"{written['paperops2_fresh_eligible_submit_record_count']}"
    )
    print(
        "paperops_active_runner_duplicate_submit_count="
        f"{written['paperops2_duplicate_submit_record_count']}"
    )
    print(
        "paperops_active_runner_duplicate_submit_interpretation="
        f"{written['paperops2_duplicate_submit_interpretation']}"
    )
    print(
        "paperops_active_runner_submit_regression_guard_status="
        f"{written['paperops_submit_regression_guard_status']}"
    )
    print(
        "paperops_active_runner_submit_regression_guard_blocker_count="
        f"{written['paperops_submit_regression_guard_blocker_count']}"
    )
    print(
        "paperops_active_runner_submit_regression_guard_fresh_submitted_ledger_collision_count="
        f"{written['paperops_submit_regression_guard_fresh_submitted_ledger_collision_count']}"
    )
    print(
        "paperops_active_runner_submit_regression_guard_duplicate_misclassified_as_fresh_count="
        f"{written['paperops_submit_regression_guard_duplicate_misclassified_as_fresh_count']}"
    )
    print(
        "paperops_active_runner_submit_regression_guard_source_stale_after_post_count="
        f"{written['paperops_submit_regression_guard_source_stale_after_post_count']}"
    )
    print(
        "paperops_active_runner_submit_regression_guard_validation_error_count="
        f"{written['paperops_submit_regression_guard_validation_error_count']}"
    )
    print(
        "paperops_active_runner_first_week_mandate_status="
        f"{written['first_week_paper_trade_mandate_status']}"
    )
    print(
        "paperops_active_runner_first_week_mandate_active="
        f"{written['first_week_paper_trade_mandate_active']}"
    )
    print(
        "paperops_active_runner_first_week_mandate_day_number="
        f"{written['first_week_paper_trade_mandate_day_number']}"
    )
    print(
        "paperops_active_runner_first_week_mandate_daily_target_trade_count="
        f"{written['first_week_paper_trade_mandate_daily_target_trade_count']}"
    )
    print(
        "paperops_active_runner_first_week_mandate_minimum_notional_usd="
        f"{written['first_week_paper_trade_mandate_minimum_notional_usd']}"
    )
    print(
        "paperops_active_runner_first_week_mandate_daily_ready_submit_count="
        f"{written['first_week_paper_trade_mandate_daily_ready_submit_count']}"
    )
    print(
        "paperops_active_runner_first_week_mandate_daily_submitted_count="
        f"{written['first_week_paper_trade_mandate_daily_submitted_count']}"
    )
    print(
        "paperops_active_runner_rs5_daily_target_policy="
        f"{written['rs5_daily_target_policy']}"
    )
    print(
        "paperops_active_runner_rs5_daily_target_is_minimum="
        f"{written['rs5_daily_target_is_minimum']}"
    )
    print(
        "paperops_active_runner_rs5_daily_target_blocks_additional_setups="
        f"{written['rs5_daily_target_blocks_additional_qualified_setups']}"
    )
    print(
        "paperops_active_runner_rs5_max_guarded_submit_attempts_per_run="
        f"{written['rs5_max_guarded_submit_attempts_per_run']}"
    )
    print(
        "paperops_active_runner_rs5_available_distinct_setup_count="
        f"{written['rs5_available_distinct_setup_count']}"
    )
    print(
        "paperops_active_runner_rs5_can_submit_multiple_today="
        f"{written['rs5_can_submit_multiple_today']}"
    )
    print(
        "paperops_active_runner_rs5_guard_status="
        f"{written['rs5_multiple_submission_guard_status']}"
    )
    print(
        "paperops_active_runner_why_not_trading_now="
        f"{written['why_not_trading_now']}"
    )
    submitted_paper_order_count = sum(
        int(
            record.get("parsed", {}).get(
                "paperops_alpaca_post_succeeded_count",
                "0",
            )
            or 0
        )
        for record in action_records
        if record.get("label") == "paper_submit"
    )
    print(
        "paperops_active_runner_submitted_paper_order_count="
        f"{submitted_paper_order_count}"
    )
    print(
        "paperops_active_runner_poll_step_allowed="
        f"{written['paper_poll_step_allowed']}"
    )
    print(
        "paperops_active_runner_exit_step_allowed="
        f"{written['paper_exit_step_allowed']}"
    )
    print(
        "paperops_active_runner_qctrl_hold="
        f"{written['qctrl_consultation_hold_active']}"
    )
    print(f"paperops_active_runner_idle_reason={written['idle_reason'] or ''}")
    print(
        "paperops_active_runner_idempotency_guard_message="
        f"{written['idempotency_guard_message']}"
    )
    print(f"paperops_active_runner_action_record_count={written['action_record_count']}")
    daily_digest_record = next(
        (
            record
            for record in action_records
            if record.get("label") == "telegram_daily_portfolio_digest"
        ),
        {"parsed": {}},
    )
    daily_digest_parsed = daily_digest_record.get("parsed", {})
    print(
        "paperops_active_runner_daily_portfolio_digest_status="
        f"{daily_digest_parsed.get('telegram_daily_portfolio_digest_status', 'not_run')}"
    )
    print(
        "paperops_active_runner_daily_portfolio_digest_due_for_delivery="
        f"{daily_digest_parsed.get('telegram_daily_portfolio_digest_due_for_delivery', 'False')}"
    )
    print(
        "paperops_active_runner_daily_portfolio_digest_live_send_succeeded="
        f"{daily_digest_parsed.get('telegram_daily_portfolio_digest_live_send_succeeded', 'False')}"
    )
    print(
        "paperops_active_runner_live_endpoint_called_count="
        f"{written['live_endpoint_called_count']}"
    )
    print(
        "paperops_active_runner_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(f"paperops_active_runner_validation_errors={validation_errors}")

    if validation_errors:
        print("paperops_active_paper_trading_automation_runner=failed")
        return 1
    if command_failed:
        print("paperops_active_paper_trading_automation_runner=failed")
        return 1
    print("paperops_active_paper_trading_automation_runner=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
