#!/usr/bin/env python3
"""Validate bounded automatic paper-risk tiering."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_ef11_open_market_conversion import build_and_write_ef11_state  # noqa: E402


def main() -> int:
    bundle, _checks, errors = build_and_write_ef11_state()
    ladder = bundle["risk_ladder"]
    if ladder.get("absolute_notional_ceiling_usd") != 5000.0:
        errors.append("paper_risk_ceiling_not_5000")
    print(f"status={'passed' if not errors else 'blocked'}")
    print(f"default_tier={bundle['risk_status']['current_default_tier']}")
    print(f"first_time_notional_usd={bundle['risk_status']['maximum_current_first_time_notional_usd']}")
    print(f"absolute_notional_ceiling_usd={ladder['absolute_notional_ceiling_usd']}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
