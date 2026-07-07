#!/usr/bin/env python3
"""Certify the Phase 1 whole-universe backfill/backtest baseline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings
from orchestrator.qsase_whole_universe_backfill_backtest import (
    AKBER_BACKTEST_CALIBRATION_ARTIFACT,
    BASELINE_SHADOW_ROUTER_MAP_ARTIFACT,
    BASELINE_EVIDENCE_MAP_ARTIFACT,
    BASELINE_REJECTIONS_ARTIFACT,
    BASELINE_RESULTS_ARTIFACT,
    BASELINE_STRATEGY_EVIDENCE_MAP_ARTIFACT,
    DASHBOARD_SUMMARY_ARTIFACT,
    FORWARD_WINDOW_COMPLETION_ARTIFACT,
    MANIFEST_ARTIFACT,
    PRICE_HISTORY_MANIFEST_ARTIFACT,
    PROVIDER_CAPABILITY_ARTIFACT,
    SOURCE_HISTORY_MANIFEST_ARTIFACT,
    STATE_ARTIFACT,
    SUMMARY_ARTIFACT,
    UNIVERSE_FREEZE_ARTIFACT,
    _paths,
    build_preflight,
    load_whole_universe_backfill_backtest,
    validate_negative_whole_universe_probes,
    validate_whole_universe_backfill_backtest,
)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()

    settings = Settings.from_env()
    paths = _paths(settings)
    if args.preflight:
        payload = build_preflight(settings)
        print(f"status={payload.get('status')}")
        print(f"source_row_count={payload.get('source_row_count')}")
        print(f"watched_instrument_count={payload.get('watched_instrument_count')}")
        print(f"memory_record_count={payload.get('memory_record_count')}")
        print(f"long_backtest_lock_active={payload.get('long_backtest_lock_active')}")
        print(f"paperops_watch_only_mode={payload.get('paperops_watch_only_mode')}")
        print(f"phase_1_backfill_started={payload.get('phase_1_backfill_started')}")
        print(f"error_count={payload.get('error_count')}")
        if payload.get("errors"):
            for error in payload["errors"]:
                print(f"error={error}")
            return 1
        print("qsase_whole_universe_backfill_backtest_preflight=ok")
        return 0

    bundle = load_whole_universe_backfill_backtest(settings)
    validation_errors = []
    validation_errors.extend(validate_whole_universe_backfill_backtest(bundle))
    validation_errors.extend(validate_negative_whole_universe_probes())
    required = (
        MANIFEST_ARTIFACT,
        STATE_ARTIFACT,
        SUMMARY_ARTIFACT,
        DASHBOARD_SUMMARY_ARTIFACT,
        UNIVERSE_FREEZE_ARTIFACT,
        PROVIDER_CAPABILITY_ARTIFACT,
        SOURCE_HISTORY_MANIFEST_ARTIFACT,
        PRICE_HISTORY_MANIFEST_ARTIFACT,
        FORWARD_WINDOW_COMPLETION_ARTIFACT,
        BASELINE_RESULTS_ARTIFACT,
        BASELINE_REJECTIONS_ARTIFACT,
        BASELINE_EVIDENCE_MAP_ARTIFACT,
        BASELINE_STRATEGY_EVIDENCE_MAP_ARTIFACT,
        AKBER_BACKTEST_CALIBRATION_ARTIFACT,
        BASELINE_SHADOW_ROUTER_MAP_ARTIFACT,
    )
    for filename in required:
        path = paths.get(
            {
                MANIFEST_ARTIFACT: "manifest",
                STATE_ARTIFACT: "state",
                SUMMARY_ARTIFACT: "summary",
                DASHBOARD_SUMMARY_ARTIFACT: "dashboard_summary",
                UNIVERSE_FREEZE_ARTIFACT: "universe_freeze",
                PROVIDER_CAPABILITY_ARTIFACT: "provider_capability",
                SOURCE_HISTORY_MANIFEST_ARTIFACT: "source_history_manifest",
                PRICE_HISTORY_MANIFEST_ARTIFACT: "price_history_manifest",
                FORWARD_WINDOW_COMPLETION_ARTIFACT: "forward_window_completion",
                BASELINE_RESULTS_ARTIFACT: "baseline_results",
                BASELINE_REJECTIONS_ARTIFACT: "baseline_rejections",
                BASELINE_EVIDENCE_MAP_ARTIFACT: "baseline_evidence_map",
                BASELINE_STRATEGY_EVIDENCE_MAP_ARTIFACT: "baseline_strategy_evidence_map",
                AKBER_BACKTEST_CALIBRATION_ARTIFACT: "akber_backtest_calibration",
                BASELINE_SHADOW_ROUTER_MAP_ARTIFACT: "baseline_shadow_router_map",
            }[filename]
        )
        if path is None or not path.exists():
            validation_errors.append(f"{filename}_missing")

    summary = _load_json(paths["summary"])
    forward = _load_json(paths["forward_window_completion"])
    print(f"manifest={paths['manifest']}")
    print(f"state={paths['state']}")
    print(f"summary={paths['summary']}")
    print(f"dashboard_summary={paths['dashboard_summary']}")
    print(f"status={summary.get('status')}")
    print(f"source_count={summary.get('source_count')}")
    print(f"watched_instrument_count={summary.get('watched_instrument_count')}")
    print(f"complete_forward_window_count={summary.get('complete_forward_window_count')}")
    print(f"missing_forward_window_count={summary.get('missing_forward_window_count')}")
    print(f"complete_forward_window_ratio={summary.get('complete_forward_window_ratio')}")
    print(f"missing_windows_materially_reduced={forward.get('missing_windows_materially_reduced')}")
    print(f"baseline_result_count={summary.get('baseline_result_count')}")
    print(f"baseline_rejection_count={summary.get('baseline_rejection_count')}")
    print(f"strategy_evidence_count={summary.get('strategy_evidence_count')}")
    print(f"akber_calibration_state={summary.get('akber_calibration_state')}")
    print(f"akber_calibrated_strategy_count={summary.get('akber_calibrated_strategy_count')}")
    print(f"akber_thresholds_mutated={summary.get('akber_thresholds_mutated')}")
    print(f"shadow_router_state={summary.get('shadow_router_state')}")
    print(f"shadow_only_count={summary.get('shadow_only_count')}")
    print(f"shadow_router_paper_review_candidate_count={summary.get('shadow_router_paper_review_candidate_count')}")
    print(f"paper_order_created_count={summary.get('paper_order_created_count')}")
    print(f"broker_write_count={summary.get('broker_write_count')}")
    print(f"live_capital_enabled={summary.get('live_capital_enabled')}")
    print(f"proof_credit_allowed={summary.get('proof_credit_allowed')}")
    print(f"validation_error_count={len(set(validation_errors))}")

    if validation_errors:
        for error in sorted(set(validation_errors)):
            print(f"error={error}")
        return 1
    print("qsase_whole_universe_backfill_backtest_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
