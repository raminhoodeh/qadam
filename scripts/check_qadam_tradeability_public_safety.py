#!/usr/bin/env python3
"""Build dashboard-safe compiler visibility and verify authority boundaries."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_tradeability_audits import build_and_write_visibility


def main() -> int:
    dashboard, safety, errors = build_and_write_visibility()
    print(f"status={safety.get('status')}")
    print(f"operational_health={dashboard.get('operational_health')}")
    print(f"tradeability_reachability={dashboard.get('tradeability_reachability')}")
    print(f"current_setup_state={dashboard.get('current_setup_state')}")
    print(f"forbidden_token_count={safety.get('forbidden_token_count')}")
    for error in errors:
        print(f"error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
