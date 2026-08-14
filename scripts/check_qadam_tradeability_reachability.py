#!/usr/bin/env python3
"""Run the broker-disabled canonical tradeability reachability canary."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_tradeability_reliability import (
    build_and_write_reachability_canary,
)


def main() -> int:
    _payload, checks, errors = build_and_write_reachability_canary()
    print(f"status={checks.get('status')}")
    print(f"reachability_state={checks.get('reachability_state')}")
    print(f"current_setup_state={checks.get('current_setup_state')}")
    print(
        "accepted_broker_disabled_handoff_count="
        f"{checks.get('accepted_broker_disabled_handoff_count')}"
    )
    for error in errors:
        print(f"error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
