#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_qeg_reliability import build_qeg_reliability, validate_qeg_reliability


if __name__ == "__main__":
    payload, build_errors = build_qeg_reliability()
    errors = sorted(set([*build_errors, *validate_qeg_reliability()]))
    trial = payload.get("trial") or {}
    print(f"status={'passed' if not errors else 'blocked'}")
    print(f"service_registered={str(payload.get('service_registered')).lower()}")
    print(f"graph_health={payload.get('graph_health')}")
    print(f"trial_state={trial.get('status')}")
    print(f"real_market_days={trial.get('completed_real_market_day_count', 0)}/{trial.get('target_real_market_days', 5)}")
    for error in errors:
        print(f"error={error}")
    raise SystemExit(1 if errors else 0)
