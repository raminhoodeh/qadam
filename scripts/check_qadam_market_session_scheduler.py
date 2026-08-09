#!/usr/bin/env python3
"""Validate reserved operator capacity for latency-sensitive conversion work."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_ef11_open_market_conversion import build_and_write_ef11_state  # noqa: E402


def main() -> int:
    bundle, _checks, errors = build_and_write_ef11_state()
    capacity = bundle["capacity"]
    if capacity.get("critical_path_reserved") is not True:
        errors.append("critical_market_path_not_reserved")
    print(f"status={'passed' if not errors else 'blocked'}")
    print(f"critical_path_reserved={capacity['critical_path_reserved']}")
    print(f"critical_budget_exhausted_count={bundle['scheduler_status']['critical_budget_exhausted_count']}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
