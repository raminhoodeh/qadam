#!/usr/bin/env python3
"""Run Qadam's bounded provider-backed power-market research sleeve."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_power_market_edge_engine import (  # noqa: E402
    build_and_write_power_market_edge_engine,
)


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Run one bounded cycle.")
    parser.add_argument(
        "--allow-network",
        action="store_true",
        help="Permit read-only CAISO and Alpaca market-data requests.",
    )
    parser.add_argument(
        "--max-partitions",
        type=int,
        default=0,
        help="Historical partitions to attempt in this cycle (0-32).",
    )
    parser.add_argument("--research-start", default="2019-01-01")
    return parser.parse_args()


def main() -> int:
    args = _args()
    if not args.once:
        print("power_market_edge_engine_status=refused_missing_once")
        return 2
    try:
        research_start = date.fromisoformat(args.research_start)
    except ValueError:
        print("power_market_edge_engine_status=invalid_research_start")
        return 2
    try:
        state, checks, errors = build_and_write_power_market_edge_engine(
            Settings.from_env(),
            allow_network=args.allow_network,
            max_partitions=args.max_partitions,
            research_start=research_start,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"power_market_edge_engine_status=failed:{type(exc).__name__}")
        print(f"power_market_edge_engine_error={str(exc)[:500]}")
        return 1
    print(f"power_market_edge_engine_status={state.get('status')}")
    print(f"power_market_provider_state={state.get('provider_state')}")
    print(f"power_market_daily_evidence_count={state.get('daily_evidence_count')}")
    print(f"power_market_proxy_bar_count={state.get('proxy_bar_count')}")
    print(
        "power_market_historical_partitions="
        f"{state.get('historical_partition_complete_count')}/"
        f"{(state.get('historical_partition_complete_count') or 0) + (state.get('historical_partition_remaining_count') or 0)}"
    )
    print(f"power_market_backtest_hypothesis_count={state.get('backtest_hypothesis_count')}")
    print(f"power_market_provisional_positive_count={state.get('provisional_positive_count')}")
    print(f"power_market_validated_candidate_count={state.get('validated_candidate_count')}")
    print(f"power_market_current_pattern_score_count={state.get('current_pattern_score_count')}")
    print(f"power_market_strategy_admission_state={state.get('strategy_admission_state')}")
    print(f"power_market_checks={checks.get('status')}")
    print(f"power_market_retryable_provider_errors={checks.get('retryable_provider_errors')}")
    print(f"power_market_errors={errors}")
    return 0 if checks.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
