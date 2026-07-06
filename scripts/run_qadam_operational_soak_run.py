#!/usr/bin/env python3
"""Run Qadam operational soak monitor."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qadam_operational_soak_run import build_and_write_operational_soak_run


def main() -> int:
    payload, final_declaration, written, errors = build_and_write_operational_soak_run(Settings.from_env(), refresh_certification=True)
    print(f"artifact={written.get('primary')}")
    print(f"daily_summaries={written.get('daily_summaries')}")
    print(f"incident_log={written.get('incident_log')}")
    print(f"final_declaration={written.get('final_declaration')}")
    print(f"status={payload.get('status')}")
    print(f"soak_complete={payload.get('soak_complete')}")
    print(f"observed_soak_day_count={payload.get('observed_soak_day_count')}")
    print(f"required_soak_days={payload.get('required_soak_days')}")
    print(f"operationally_complete={payload.get('operationally_complete')}")
    print(f"final_declaration_status={final_declaration.get('status')}")
    print(f"paper_order_created_count={payload.get('paper_order_created_count')}")
    print(f"broker_write_count={payload.get('broker_write_count')}")
    print(f"live_capital_enabled={payload.get('live_capital_enabled')}")
    if errors:
        for error in errors:
            print(f"error={error}")
        return 1
    print("qadam_operational_soak_run=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
