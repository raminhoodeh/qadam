#!/usr/bin/env python3
"""Run one guarded, paper-only open-market conversion cycle."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_open_market_conversion import run_open_market_conversion  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--broker-disabled-canary", action="store_true")
    parser.add_argument("--no-paperops", action="store_true")
    args = parser.parse_args()
    result, errors = run_open_market_conversion(
        allow_network=args.allow_network,
        broker_disabled_canary=args.broker_disabled_canary,
        allow_paperops=not args.no_paperops,
    )
    print(f"status={result['status']}")
    print(f"conversion_generation_id={result.get('conversion_generation_id')}")
    print(f"market_session_phase={result.get('market_session_phase')}")
    print(f"market_session_actionable={result.get('market_session_actionable')}")
    print(f"pre_staged_setup_count={result.get('pre_staged_setup_count')}")
    print(f"handoff_count={result.get('handoff_count')}")
    print(f"paper_order_count={result.get('paper_order_count')}")
    print("broker_write_count_by_coordinator=0")
    print("live_capital_enabled=False")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
