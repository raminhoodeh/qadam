#!/usr/bin/env python3
"""Validate the append-only conversion ledger and deterministic daily reducer."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_ef11_open_market_conversion import build_and_write_ef11_state  # noqa: E402


def main() -> int:
    bundle, checks, errors = build_and_write_ef11_state()
    cycles = bundle["cycles"]
    ids = [row.get("cycle_id") for row in cycles]
    if len(ids) != len(set(ids)):
        errors.append("conversion_cycle_identity_duplicate")
    print(f"status={'passed' if not errors else 'blocked'}")
    print(f"cycle_count={len(cycles)}")
    print(f"daily_summary_count={len(bundle['daily_summaries'])}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
