#!/usr/bin/env python3
"""Run the resumable whole-universe historical backfill/backtest baseline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_whole_universe_backfill_backtest import (
    RunnerOptions,
    run_whole_universe_backfill_backtest,
)


def _csv_tuple(value: str | None) -> tuple[str, ...]:
    if not value or value == "all":
        return ()
    return tuple(item.strip() for item in value.split(",") if item.strip())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-runtime-hours", type=float, default=120.0)
    parser.add_argument("--batch-limit", type=int)
    parser.add_argument("--sources", default="all")
    parser.add_argument("--instruments", default="all")
    parser.add_argument("--source", action="append", default=[])
    parser.add_argument("--instrument", action="append", default=[])
    parser.add_argument("--from-date")
    parser.add_argument("--to-date")
    parser.add_argument("--max-provider-calls", type=int, default=0)
    parser.add_argument("--sleep-between-calls", type=float, default=0.0)
    parser.add_argument("--network-disabled", action="store_true", default=True)
    parser.add_argument("--paperops-paused-required", action="store_true", default=True)
    args = parser.parse_args()

    selected_sources = tuple(args.source) or _csv_tuple(args.sources)
    selected_instruments = tuple(args.instrument) or _csv_tuple(args.instruments)
    options = RunnerOptions(
        dry_run=args.dry_run,
        resume=args.resume,
        max_runtime_hours=args.max_runtime_hours,
        batch_limit=args.batch_limit,
        sources=selected_sources,
        instruments=selected_instruments,
        from_date=args.from_date,
        to_date=args.to_date,
        max_provider_calls=args.max_provider_calls,
        sleep_between_calls=args.sleep_between_calls,
        network_disabled=args.network_disabled,
        paperops_paused_required=args.paperops_paused_required,
    )
    settings = Settings.from_env()
    payload, written, errors = run_whole_universe_backfill_backtest(
        settings=settings,
        options=options,
    )

    print(f"manifest={written.get('manifest')}")
    print(f"state={written.get('state')}")
    print(f"summary={written.get('summary')}")
    print(f"dashboard_summary={written.get('dashboard_summary')}")
    print(f"status={payload.get('status')}")
    print(f"run_mode={'dry_run' if args.dry_run else 'resume'}")
    print(f"source_count={payload.get('source_count')}")
    print(f"watched_instrument_count={payload.get('watched_instrument_count')}")
    print(f"complete_forward_window_count={payload.get('complete_forward_window_count')}")
    print(f"missing_forward_window_count={payload.get('missing_forward_window_count')}")
    print(f"baseline_result_count={payload.get('baseline_result_count')}")
    print(f"baseline_rejection_count={payload.get('baseline_rejection_count')}")
    print(f"strategy_supported_count={payload.get('strategy_supported_count')}")
    print(f"akber_calibration_state={payload.get('akber_calibration_state')}")
    print(f"akber_calibrated_strategy_count={payload.get('akber_calibrated_strategy_count')}")
    print(f"akber_thresholds_mutated={payload.get('akber_thresholds_mutated')}")
    print(f"shadow_router_state={payload.get('shadow_router_state')}")
    print(f"shadow_only_count={payload.get('shadow_only_count')}")
    print(f"shadow_router_paper_review_candidate_count={payload.get('shadow_router_paper_review_candidate_count')}")
    print(f"phase_1_backfill_started={payload.get('phase_1_backfill_started')}")
    print(f"paper_order_created_count={payload.get('paper_order_created_count')}")
    print(f"broker_write_count={payload.get('broker_write_count')}")
    print(f"live_capital_enabled={payload.get('live_capital_enabled')}")
    print(f"proof_credit_allowed={payload.get('proof_credit_allowed')}")
    print(f"validation_error_count={len(errors)}")
    if errors:
        for error in errors:
            print(f"error={error}")
        return 1
    print("qsase_whole_universe_backfill_backtest_run=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
