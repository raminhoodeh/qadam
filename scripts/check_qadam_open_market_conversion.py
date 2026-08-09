#!/usr/bin/env python3
"""Validate EF11 same-generation conversion contracts without placing orders."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_ef11_open_market_conversion import build_and_write_ef11_state  # noqa: E402


def main() -> int:
    bundle, checks, errors = build_and_write_ef11_state()
    print(f"status={checks['status']}")
    print(f"engineering_contract_ready={checks['engineering_contract_ready']}")
    print(f"certification_state={bundle['certification']['status']}")
    print("broker_write_count=0")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
