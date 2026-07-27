#!/usr/bin/env python3
"""Refresh the real elapsed-time operator reliability soak."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_permanent_operator_reliability import (  # noqa: E402
    build_reliability_soak,
)


def main() -> int:
    result = build_reliability_soak()
    print(f"qadam_reliability_soak_status={result['status']}")
    print(f"qadam_reliability_soak_elapsed_seconds={result['real_elapsed_seconds']:.0f}")
    print(f"qadam_reliability_soak_session_count={result['real_session_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
