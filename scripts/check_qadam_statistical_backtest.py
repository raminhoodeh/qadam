#!/usr/bin/env python3
"""Build and validate OR-8 whole-universe statistical backtest state."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402
from orchestrator.qadam_statistical_backtest import (  # noqa: E402
    CHECK_ARTIFACT,
    DASHBOARD_ARTIFACT,
    MANIFEST_ARTIFACT,
    MULTIPLE_TESTING_ARTIFACT,
    NEGATIVE_CONTROL_DIAGNOSTICS_ARTIFACT,
    PROTOCOL_ARTIFACT,
    REJECTIONS_ARTIFACT,
    SUMMARY_ARTIFACT,
    WALK_FORWARD_ARTIFACT,
    build_and_write_statistical_backtest,
)
from orchestrator.qadam_learning_backtest_gap_closure import validate_stage  # noqa: E402


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    _state, checks, errors = build_and_write_statistical_backtest(settings)
    errors = [*errors, *validate_stage("PLBG-11", settings)]
    from orchestrator.runtime.command import report_work_result
    report_work_result(checks, errors)
    for name in (
        PROTOCOL_ARTIFACT,
        MANIFEST_ARTIFACT,
        SUMMARY_ARTIFACT,
        REJECTIONS_ARTIFACT,
        MULTIPLE_TESTING_ARTIFACT,
        WALK_FORWARD_ARTIFACT,
        DASHBOARD_ARTIFACT,
        NEGATIVE_CONTROL_DIAGNOSTICS_ARTIFACT,
        CHECK_ARTIFACT,
    ):
        print(f"artifact={runtime / name}")
    for key in (
        "status",
        "acceptance_passed",
        "implementation_ready",
        "empirical_backtest_complete",
        "paired_score_label_count",
        "independent_pair_count",
        "attempted_hypothesis_count",
        "fold_result_count",
        "untouched_holdout_result_count",
        "cost_adjusted_result_count",
        "historical_edge_candidate_count",
        "validated_edge_count",
        "negative_control_validated_count",
        "negative_control_guard_trigger_count",
        "negative_control_promotion_gate_breach_count",
        "false_discovery_adjusted_result_count",
        "holdout_tuning_violation_count",
        "bulk_outputs_reused",
    ):
        print(f"{key}={checks[key]}")
    print("plbg_v4_focus_provider_overlay=validated_with_classified_gaps")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 0 if checks.get("acceptance_passed") is True and not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
