#!/usr/bin/env python3
"""Exercise all disk-backed canonical tradeability journeys."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_tradeability_reliability import (
    build_and_write_golden_journeys,
)


def main() -> int:
    _payload, checks, errors = build_and_write_golden_journeys()
    print(f"status={checks.get('status')}")
    print(f"journey_count={checks.get('journey_count')}")
    print(f"passed_count={checks.get('passed_count')}")
    for error in errors:
        print(f"error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
