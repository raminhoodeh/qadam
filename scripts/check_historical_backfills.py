#!/usr/bin/env python3
"""Check Phase 1 historical backfill planning."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.historical_backfill import build_historical_backfill_plan, run_historical_backfill


def main() -> int:
    payload = build_historical_backfill_plan()
    print(f"historical_backfill_status={payload['status']}")
    print(f"historical_backfill_plan_count={payload['plan_count']}")
    print(f"historical_backfill_ready_count={payload['ready_count']}")
    print(f"historical_backfill_blocked_count={payload['blocked_count']}")
    print(f"historical_backfill_boundary={payload['boundary']}")
    if payload["plan_count"] < 8:
        print("historical_backfill_plan_count_too_low=true")
        return 1
    run = run_historical_backfill()
    print(f"historical_backfill_run_status={run['status']}")
    print(f"historical_backfill_run_recorded_count={run['recorded_count']}")
    print(f"historical_backfill_run_blocked_count={run['blocked_count']}")
    print(f"historical_backfill_run_sample_event_count={run['sample_event_count']}")
    print(f"historical_backfill_store_status={run['store']['status']}")
    if run["requested_count"] != payload["plan_count"]:
        print("historical_backfill_run_plan_mismatch=true")
        return 1
    if run["recorded_count"] < 4:
        print("historical_backfill_run_recorded_count_too_low=true")
        return 1
    if run["store"]["status"] != "ok":
        print("historical_backfill_store_not_ok=true")
        return 1
    print("historical_backfill_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
