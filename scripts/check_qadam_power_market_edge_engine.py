#!/usr/bin/env python3
"""Certify Qadam's power-market research sleeve and authority boundary."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_operator_ready_common import read_json, read_jsonl, runtime_dir  # noqa: E402
from orchestrator.qadam_power_market_edge_engine import (  # noqa: E402
    BACKTEST_ARTIFACT,
    CHECK_ARTIFACT,
    CONTEXT_ARTIFACT,
    MANIFEST_ARTIFACT,
    PATTERN_SCORES_ARTIFACT,
    PRIMARY_ARTIFACT,
    STRATEGY_ARTIFACT,
    build_and_write_power_market_edge_engine,
    research_paths_are_ignored,
    validate_power_market_state,
)


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Refresh cached artifacts without making network requests.",
    )
    return parser.parse_args()


def main() -> int:
    args = _args()
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    if args.refresh:
        build_and_write_power_market_edge_engine(
            settings,
            allow_network=False,
            max_partitions=0,
        )
    state = read_json(runtime / PRIMARY_ARTIFACT)
    manifest = read_json(runtime / MANIFEST_ARTIFACT)
    backtest = read_json(runtime / BACKTEST_ARTIFACT)
    strategy = read_json(runtime / STRATEGY_ARTIFACT)
    scores = read_jsonl(runtime / PATTERN_SCORES_ARTIFACT)
    context = read_json(runtime / CONTEXT_ARTIFACT)
    checks = read_json(runtime / CHECK_ARTIFACT)
    errors: list[str] = []
    if not research_paths_are_ignored():
        errors.append("power_market_research_path_not_git_ignored")
    if not all((state, manifest, backtest, strategy, context, checks)):
        errors.append("power_market_required_artifact_missing_or_empty")
    if state and manifest and backtest and strategy and context:
        errors.extend(
            validate_power_market_state(
                state,
                manifest,
                backtest,
                strategy,
                scores,
                context,
            )
        )
    if checks.get("status") != "passed":
        errors.append("power_market_checks_not_passed")
    if checks.get("safe_to_consume") is not True:
        errors.append("power_market_not_safe_to_consume")
    if any(row.get("paper_order_allowed") is not False for row in scores):
        errors.append("power_market_score_granted_order_authority")
    errors = sorted(set(errors))
    print(f"power_market_check_status={'failed' if errors else 'passed'}")
    print(f"power_market_safe_to_consume={checks.get('safe_to_consume')}")
    print(f"power_market_daily_evidence_count={state.get('daily_evidence_count')}")
    print(f"power_market_proxy_bar_count={state.get('proxy_bar_count')}")
    print(f"power_market_backtest_hypothesis_count={backtest.get('hypothesis_count')}")
    print(f"power_market_current_pattern_score_count={len(scores)}")
    print(f"power_market_strategy_state={strategy.get('status')}")
    print(f"power_market_errors={errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
