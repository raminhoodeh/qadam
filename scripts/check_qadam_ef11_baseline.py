#!/usr/bin/env python3
"""Build and validate the EF11 baseline and contract reconciliation."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_ef11_open_market_conversion import build_and_write_ef11_state  # noqa: E402


def main() -> int:
    bundle, checks, errors = build_and_write_ef11_state()
    baseline = bundle["baseline"]
    print(f"status={checks['status']}")
    print(f"baseline_id={baseline['baseline_id']}")
    print(f"source_count={baseline['source_count']}")
    print(f"instrument_count={baseline['instrument_count']}")
    print(f"eligible_market_days_observed={baseline['eligible_market_days_observed']}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
