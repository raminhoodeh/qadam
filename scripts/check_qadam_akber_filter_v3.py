#!/usr/bin/env python3
"""Build and validate OR-12 Akber Filter V3."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_akber_filter_v3 import (  # noqa: E402
    ABLATION_ARTIFACT,
    CHECK_ARTIFACT,
    DASHBOARD_ARTIFACT,
    INPUTS_ARTIFACT,
    REPLAY_ARTIFACT,
    RESULTS_ARTIFACT,
    THRESHOLD_PROPOSALS_ARTIFACT,
    build_and_write_akber_filter_v3,
)
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    _state, checks, errors = build_and_write_akber_filter_v3(settings)
    for name in (
        INPUTS_ARTIFACT,
        RESULTS_ARTIFACT,
        REPLAY_ARTIFACT,
        ABLATION_ARTIFACT,
        THRESHOLD_PROPOSALS_ARTIFACT,
        DASHBOARD_ARTIFACT,
        CHECK_ARTIFACT,
    ):
        print(f"artifact={runtime / name}")
    for key in (
        "status",
        "implementation_ready",
        "implementation_complete",
        "valid_no_current_hypothesis_outcome",
        "policy_version",
        "input_validation_error_count",
        "input_count",
        "result_count",
        "pass_count",
        "hold_count",
        "veto_count",
        "historical_qadam_result_count",
        "historical_replay_count",
        "historical_exclusion_count",
        "ablation_count",
        "threshold_proposal_count",
        "net_historical_contribution_measurable",
        "router_eligible_with_missing_context_count",
        "sample_or_fixture_context_admitted_count",
        "threshold_change_applied_count",
        "risk_approval_created_count",
        "execution_approval_created_count",
        "trade_candidate_created_count",
        "order_created_count",
        "broker_write_count",
        "proof_credit_created_count",
        "paper_calendar_advanced",
        "paperops_watch_only",
    ):
        print(f"{key}={checks[key]}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
