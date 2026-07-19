#!/usr/bin/env python3
"""Build and fail-closed validate the OR-2R gate before OR-3."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402
from orchestrator.qadam_or3_acquisition_readiness import (  # noqa: E402
    CONNECTION_TRUTH_ARTIFACT,
    PILOT_MANIFEST_ARTIFACT,
    PILOT_RESULTS_ARTIFACT,
    PURCHASE_MATRIX_ARTIFACT,
    READINESS_ARTIFACT,
    SOURCE_MATRIX_ARTIFACT,
    TERMS_REVIEW_ARTIFACT,
    TRADINGVIEW_STATUS_ARTIFACT,
    build_and_write_or3_acquisition_readiness,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run-pilot",
        action="store_true",
        help="Run the bounded real-data pilot. Without this flag, reuse existing pilot results.",
    )
    parser.add_argument("--timeout-seconds", type=int, default=30)
    args = parser.parse_args()
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    readiness, errors = build_and_write_or3_acquisition_readiness(
        settings,
        run_pilot=args.run_pilot,
        timeout_seconds=max(5, min(args.timeout_seconds, 120)),
    )
    for name in (
        CONNECTION_TRUTH_ARTIFACT,
        TRADINGVIEW_STATUS_ARTIFACT,
        PURCHASE_MATRIX_ARTIFACT,
        SOURCE_MATRIX_ARTIFACT,
        TERMS_REVIEW_ARTIFACT,
        PILOT_MANIFEST_ARTIFACT,
        PILOT_RESULTS_ARTIFACT,
        READINESS_ARTIFACT,
    ):
        print(f"artifact={runtime / name}")
    for key in (
        "status",
        "implementation_ready",
        "or3_start_allowed",
        "connection_truth_passed",
        "tradingview_connection_state",
        "instrument_count",
        "source_count",
        "pilot_status",
        "pilot_provider_row_count",
        "blocking_matrix_row_count",
        "operator_action_count",
        "projected_budget_ready",
        "research_lock_active",
        "paperops_watch_only_mode",
        "trade_candidate_created_count",
        "paper_order_created_count",
        "broker_write_count",
        "proof_credit_created_count",
    ):
        print(f"{key}={readiness.get(key)}")
    for action in readiness.get("operator_actions", []):
        print(f"operator_action={action.get('action_id')}:{action.get('action')}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    # This checker is the OR-3 start gate, not merely a schema checker.
    return 0 if readiness.get("or3_start_allowed") is True and not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
