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
            }.get(label, "live_capital_enabled"),
            "False",
        )
        == "True",
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

    initial = build_paperops_active_paper_trading_automation(
        settings=settings,
        execute_automation_requested=args.execute_paper_automation,
    )
    action_records: list[dict[str, Any]] = []
    command_failed = False

    if args.execute_paper_automation:
        if initial.get("paper_submit_step_allowed") is True:
            submit = _run_step(
                "paper_submit",
                "scripts/check_paperops_alpaca_paper_post.py",
                "--submit-paper-order",
            )
            action_records.append(submit)
            command_failed = command_failed or not submit["ok"]

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

        after_poll = build_paperops_active_paper_trading_automation(
            settings=settings,
            execute_automation_requested=args.execute_paper_automation,
            action_records=action_records,
        )
        if after_poll.get("paper_exit_step_allowed") is True:
            exit_step = _run_step(
                "paper_exit",
                "scripts/check_paperops_paper_exit_path.py",
                "--execute-paper-exit",
            )
            action_records.append(exit_step)
            command_failed = command_failed or not exit_step["ok"]

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
    print(f"paperops_active_runner_action_record_count={written['action_record_count']}")
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
