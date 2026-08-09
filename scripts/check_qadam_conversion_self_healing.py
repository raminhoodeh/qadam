#!/usr/bin/env python3
"""Validate typed root cause and bounded self-healing policy."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_ef11_open_market_conversion import build_and_write_ef11_state  # noqa: E402


def main() -> int:
    bundle, _checks, errors = build_and_write_ef11_state()
    root = bundle["root_cause"]
    if not root.get("primary_root_cause"):
        errors.append("conversion_primary_root_cause_missing")
    print(f"status={'passed' if not errors else 'blocked'}")
    print(f"primary_root_cause={root.get('primary_root_cause')}")
    print(f"repair_request_count={bundle['repair_queue']['repair_request_count']}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
