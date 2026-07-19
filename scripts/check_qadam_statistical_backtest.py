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
    PROTOCOL_ARTIFACT,
    REJECTIONS_ARTIFACT,
    SUMMARY_ARTIFACT,
    WALK_FORWARD_ARTIFACT,
    build_and_write_statistical_backtest,
)


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    _state, checks, errors = build_and_write_statistical_backtest(settings)
    for name in (
        PROTOCOL_ARTIFACT,
        MANIFEST_ARTIFACT,
        SUMMARY_ARTIFACT,
        REJECTIONS_ARTIFACT,
        MULTIPLE_TESTING_ARTIFACT,
        WALK_FORWARD_ARTIFACT,
        DASHBOARD_ARTIFACT,
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
        "false_discovery_adjusted_result_count",
        "holdout_tuning_violation_count",
        "bulk_outputs_reused",
    ):
        print(f"{key}={checks[key]}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 0 if checks.get("acceptance_passed") is True and not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
