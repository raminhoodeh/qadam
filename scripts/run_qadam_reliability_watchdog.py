#!/usr/bin/env python3
"""Run one fast Qadam reliability-watchdog pass."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_reliability_watchdog import (  # noqa: E402
    run_reliability_watchdog,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Observe and write status without waking the operator or critic.",
    )
    args = parser.parse_args()
    payload, errors = run_reliability_watchdog(
        Settings.from_env(),
        repair=not args.report_only,
    )
    print(f"qadam_reliability_watchdog={payload.get('status')}")
    print(f"operating_state={payload.get('operating_state')}")
    print(f"covered_service_count={payload.get('covered_service_count')}")
    print(f"action_count={len(payload.get('actions') or [])}")
    print(f"blocker_count={len(payload.get('blockers') or [])}")
    for error in errors:
        print(f"error={error}")
    return 1 if payload.get("status") == "blocked" or errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
