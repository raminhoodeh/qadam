#!/usr/bin/env python3
"""Monitor and, when due, close the approved operator exploratory paper sleeve."""

from __future__ import annotations

import argparse
import fcntl
from pathlib import Path
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_operator_exploratory_exit_manager import (  # noqa: E402
    SLEEVE_ARTIFACT,
    SUBMISSION_ARTIFACT,
    build_exit_approval,
    build_operator_exploratory_exit_manager,
    validate_exit_approval,
    write_exit_approval,
    write_operator_exploratory_exit_manager,
)
from orchestrator.qadam_operator_ready_common import read_json  # noqa: E402


def _print_status(artifact: dict[str, object]) -> None:
    print(f"operator_exit_manager_status={artifact.get('status')}", flush=True)
    print(f"operator_exit_manager_sleeve_id={artifact.get('sleeve_id')}", flush=True)
    print(
        f"operator_exit_manager_open_position_count={artifact.get('open_position_count')}",
        flush=True,
    )
    print(
        "operator_exit_manager_protected_open_position_count="
        f"{artifact.get('protected_open_position_count')}",
        flush=True,
    )
    print(
        f"operator_exit_manager_time_exit_due_count={artifact.get('time_exit_due_count')}",
        flush=True,
    )
    print(
        f"operator_exit_manager_repair_required_count={artifact.get('repair_required_count')}",
        flush=True,
    )
    print(
        f"operator_exit_manager_broker_write_called_count={artifact.get('broker_write_called_count')}",
        flush=True,
    )
    print(
        "operator_exit_manager_broker_write_succeeded_count="
        f"{artifact.get('broker_write_succeeded_count')}",
        flush=True,
    )
    print(
        "operator_exit_manager_blockers=" + ",".join(artifact.get("blockers") or []),
        flush=True,
    )
    print(
        "operator_exit_manager_validation_errors="
        + ",".join(artifact.get("validation_errors") or []),
        flush=True,
    )


def _record_approval(settings: Settings) -> int:
    runtime = Path(settings.runtime_dir).resolve()
    sleeve = read_json(runtime / SLEEVE_ARTIFACT)
    submission = read_json(runtime / SUBMISSION_ARTIFACT)
    approval = build_exit_approval(
        sleeve=sleeve,
        submission=submission,
        explicit_operator_approval=True,
    )
    errors = validate_exit_approval(approval, sleeve, submission)
    if errors:
        print("operator_exit_approval_status=blocked")
        print("operator_exit_approval_errors=" + ",".join(errors))
        return 1
    path = write_exit_approval(approval, settings)
    print("operator_exit_approval_status=approved")
    print(f"operator_exit_approval_path={path}")
    print(f"operator_exit_approval_sleeve_id={approval.get('sleeve_id')}")
    return 0


def _run_once(settings: Settings, *, execute_due_exits: bool) -> tuple[int, dict[str, object]]:
    artifact = build_operator_exploratory_exit_manager(
        settings,
        execute_due_exits=execute_due_exits,
    )
    write_operator_exploratory_exit_manager(artifact, settings)
    _print_status(artifact)
    failed = artifact.get("status") in {"blocked", "invalid", "repair_required"}
    return (1 if failed else 0), artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--record-operator-exit-approval",
        action="store_true",
        help="Record durable approval for this exact already-submitted paper sleeve.",
    )
    parser.add_argument(
        "--execute-due-paper-exits",
        action="store_true",
        help="Allow only due risk-reducing cancels and exact paper-position closes.",
    )
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--poll-seconds", type=int, default=60)
    args = parser.parse_args()
    if args.poll_seconds < 15:
        parser.error("--poll-seconds must be at least 15")

    settings = Settings.from_env()
    if args.record_operator_exit_approval:
        result = _record_approval(settings)
        if result != 0 or not args.serve:
            return result

    if not args.serve:
        code, _artifact = _run_once(
            settings,
            execute_due_exits=args.execute_due_paper_exits,
        )
        return code

    runtime = Path(settings.runtime_dir).resolve()
    lock_path = runtime / ".qadam_operator_exploratory_exit_manager.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_handle = lock_path.open("a+", encoding="utf-8")
    try:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("operator_exit_manager_status=blocked_duplicate_instance")
        lock_handle.close()
        return 1

    stopping = False

    def stop(_signum: int, _frame: object) -> None:
        nonlocal stopping
        stopping = True

    previous = {signum: signal.getsignal(signum) for signum in (signal.SIGTERM, signal.SIGINT)}
    for signum in previous:
        signal.signal(signum, stop)
    try:
        while not stopping:
            _code, artifact = _run_once(
                settings,
                execute_due_exits=args.execute_due_paper_exits,
            )
            if artifact.get("status") == "complete_all_legs_closed":
                return 0
            slept = 0
            while slept < args.poll_seconds and not stopping:
                time.sleep(1)
                slept += 1
        return 0
    finally:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        lock_handle.close()
        for signum, handler in previous.items():
            signal.signal(signum, handler)


if __name__ == "__main__":
    raise SystemExit(main())
