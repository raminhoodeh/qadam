#!/usr/bin/env python3
"""Validate measured execution evidence and conservative limit fallback."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_ef11_open_market_conversion import build_and_write_ef11_state  # noqa: E402


def main() -> int:
    bundle, _checks, errors = build_and_write_ef11_state()
    for row in bundle["execution_context"]:
        if row.get("execution_mode") == "fresh_trade_limit_only":
            if row.get("order_type") != "limit" or float(row.get("maximum_notional_usd") or 0) > 500:
                errors.append(f"unsafe_execution_fallback:{row.get('context_id')}")
    print(f"status={'passed' if not errors else 'blocked'}")
    print(f"context_count={len(bundle['execution_context'])}")
    print(f"actionable_count={sum(row.get('execution_context_actionable') is True for row in bundle['execution_context'])}")
    print(f"spread_profile_count={bundle['spread_profiles']['profile_count']}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
