#!/usr/bin/env python3
"""Build and validate OR-11 Strategy Foundry V3."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402
from orchestrator.qadam_strategy_foundry_v3 import (  # noqa: E402
    CHECK_ARTIFACT,
    DASHBOARD_ARTIFACT,
    HYPOTHESES_ARTIFACT,
    PRIMARY_ARTIFACT,
    REJECTIONS_ARTIFACT,
    build_and_write_strategy_foundry_v3,
)


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    _state, checks, errors = build_and_write_strategy_foundry_v3(settings)
    for name in (
        PRIMARY_ARTIFACT,
        HYPOTHESES_ARTIFACT,
        REJECTIONS_ARTIFACT,
        DASHBOARD_ARTIFACT,
        CHECK_ARTIFACT,
    ):
        print(f"artifact={runtime / name}")
    for key in (
        "status",
        "implementation_ready",
        "implementation_complete",
        "valid_no_hypothesis_outcome",
        "admission_contract",
        "input_validation_error_count",
        "edge_count",
        "strategy_family_count",
        "hypothesis_count",
        "rejection_count",
        "akber_review_eligible_count",
        "exploratory_shadow_only_count",
        "pattern_score_rows_consumed_count",
        "candidate_created_count",
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
