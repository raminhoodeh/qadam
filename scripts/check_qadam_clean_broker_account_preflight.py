#!/usr/bin/env python3
"""Run the GET-only clean Alpaca Paper account preflight."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_clean_broker_preflight import (  # noqa: E402
    build_clean_broker_preflight,
    validate_clean_broker_preflight,
)


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Return success after writing an honest blocked preflight.",
    )
    return parser.parse_args()


def main() -> int:
    args = _args()
    payload = build_clean_broker_preflight()
    errors = validate_clean_broker_preflight(payload)
    print(f"clean_broker_preflight_status={payload['status']}")
    print(f"clean_broker_preflight_passed={str(payload['preflight_passed']).lower()}")
    print(f"clean_broker_currency={payload['account_currency']}")
    print(f"clean_broker_equity={payload['equity']}")
    print(f"clean_broker_cash={payload['cash']}")
    print(f"clean_broker_position_count={payload['position_count']}")
    print(f"clean_broker_order_count={payload['order_count']}")
    print(
        "clean_broker_account_fingerprint_is_new="
        f"{str(payload['account_fingerprint_is_new']).lower()}"
    )
    print("clean_broker_broker_write_count=0")
    for blocker in payload.get("blockers", []):
        print(f"clean_broker_blocker={blocker}")
    for error in errors:
        print(f"clean_broker_validation_error={error}")
    return 0 if (payload["preflight_passed"] and not errors) or args.report_only else 1


if __name__ == "__main__":
    raise SystemExit(main())
