#!/usr/bin/env python3
"""Run the explicit OR-18 local operator-service monitor."""

from __future__ import annotations

import argparse
from pathlib import Path
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402
from orchestrator.qadam_operator_service import (  # noqa: E402
    OperatorServiceLease,
    build_and_write_operator_service,
    run_safe_operator_control_cycle,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--status", action="store_true")
    mode.add_argument("--once", action="store_true")
    mode.add_argument("--serve", action="store_true")
    mode.add_argument(
        "--integration-probe",
        action="store_true",
        help="Run each required non-executing research job through its approved entry point.",
    )
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--max-jobs-per-cycle", type=int, default=4)
    args = parser.parse_args()
    if args.poll_seconds < 15:
        parser.error("--poll-seconds must be at least 15")
    settings = Settings.from_env()
    if args.status:
        _state, checks, errors = build_and_write_operator_service(settings)
        print(f"status={checks['status']}")
        print(f"service_running={checks['service_running']}")
        return 1 if errors else 0

    lease = OperatorServiceLease(
        runtime_dir(settings), lease_ttl_seconds=max(args.poll_seconds * 3, 180)
    )
    acquired, reason = lease.acquire()
    if not acquired:
        print("status=blocked")
        print(f"reason={reason}")
        return 1
    stopping = False

    def stop(_signum: int, _frame: object) -> None:
        nonlocal stopping
        stopping = True

    previous = {signum: signal.getsignal(signum) for signum in (signal.SIGTERM, signal.SIGINT)}
    for signum in previous:
        signal.signal(signum, stop)
    try:
        while True:
            cycle = run_safe_operator_control_cycle(
                settings,
                integration_probe=args.integration_probe,
                max_jobs=max(1, args.max_jobs_per_cycle),
            )
            print(f"status={cycle['status']}", flush=True)
            print(f"dispatch_status={cycle['dispatch_status']}", flush=True)
            print(f"dispatch_executed_count={cycle['dispatch_executed_count']}", flush=True)
            print(f"dispatch_failed_count={cycle['dispatch_failed_count']}", flush=True)
            print(f"paper_order_created_count={cycle['paper_order_created_count']}", flush=True)
            print(f"broker_write_count={cycle['broker_write_count']}", flush=True)
            if args.once or args.integration_probe or stopping:
                return 0 if cycle["status"] == "passed" else 1
            lease.renew()
            slept = 0
            while slept < args.poll_seconds and not stopping:
                time.sleep(1)
                slept += 1
            if stopping:
                return 0
    finally:
        lease.release(reason="signal_stop" if stopping else "clean_exit")
        for signum, handler in previous.items():
            signal.signal(signum, handler)


if __name__ == "__main__":
    raise SystemExit(main())
