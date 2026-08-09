#!/usr/bin/env python3
"""Build the canonical three-layer EF11 conversion certification."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_ef11_open_market_conversion import build_and_write_ef11_state  # noqa: E402


def main() -> int:
    bundle, checks, errors = build_and_write_ef11_state()
    certification = bundle["certification"]
    print(f"status={checks['status']}")
    print(f"certification_state={certification['status']}")
    print(f"structural_ready={certification['structural_ready']}")
    print(f"provider_conversion_ready={certification['provider_conversion_ready']}")
    print(f"empirically_conversion_proven={certification['empirically_conversion_proven']}")
    print(f"eligible_market_days_observed={certification['eligible_market_days_observed']}")
    print("live_capital_enabled=False")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
