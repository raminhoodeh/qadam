#!/usr/bin/env python3
"""Run Qadam's safe self-healing supervisor."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qadam_self_healing_supervisor import build_and_write_self_healing_state


def main() -> int:
    payload, written, errors = build_and_write_self_healing_state(Settings.from_env(), perform_refresh=True)
    print(f"artifact={written.get('primary')}")
    print(f"quarantine={written.get('quarantine')}")
    print(f"repair_requests={written.get('repair_requests')}")
    print(f"status={payload.get('status')}")
    print(f"self_healing_passed={payload.get('self_healing_passed')}")
    print(f"refresh_success_count={payload.get('refresh_tier', {}).get('refresh_success_count')}")
    print(f"refresh_failure_count={payload.get('refresh_tier', {}).get('refresh_failure_count')}")
    print(f"quarantine_record_count={payload.get('quarantine_tier', {}).get('quarantine_record_count')}")
    print(f"source_quorum_protected={payload.get('quarantine_tier', {}).get('source_quorum_protected')}")
    print(f"repair_request_count={payload.get('repair_request_tier', {}).get('repair_request_count')}")
    print(f"paper_order_created_count={payload.get('paper_order_created_count')}")
    print(f"broker_write_count={payload.get('broker_write_count')}")
    print(f"live_capital_enabled={payload.get('live_capital_enabled')}")
    if errors:
        for error in errors:
            print(f"error={error}")
        return 1
    print("qadam_self_healing_supervisor_run=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
