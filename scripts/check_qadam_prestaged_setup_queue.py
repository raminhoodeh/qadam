#!/usr/bin/env python3
"""Validate the paper-authority-free EF11 pre-stage queue."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_ef11_open_market_conversion import build_and_write_ef11_state  # noqa: E402


def main() -> int:
    bundle, _checks, errors = build_and_write_ef11_state()
    for row in bundle["prestage"]:
        if row.get("paper_order_created") is not False or row.get("broker_write_count") != 0:
            errors.append(f"unsafe_prestage_record:{row.get('prestage_id')}")
    print(f"status={'passed' if not errors else 'blocked'}")
    print(f"setup_count={bundle['prestage_status']['setup_count']}")
    print(f"ready_count={bundle['prestage_status']['ready_for_open_market_revalidation_count']}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
