#!/usr/bin/env python3
"""Build and validate OR-4 point-in-time evidence classification."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402
from orchestrator.qadam_point_in_time_evidence import (  # noqa: E402
    ALIGNMENT_ARTIFACT,
    CHECK_ARTIFACT,
    ELIGIBILITY_ARTIFACT,
    FORWARD_COVERAGE_ARTIFACT,
    LEAKAGE_ARTIFACT,
    PROVIDER_ALIGNMENT_ARTIFACT,
    TYPED_COMPLETION_ARTIFACT,
    build_and_write_point_in_time_evidence,
)
from orchestrator.qadam_learning_backtest_gap_closure import validate_stage  # noqa: E402


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    _bundle, checks, errors = build_and_write_point_in_time_evidence(settings)
    errors = [*errors, *validate_stage("PLBG-9", settings)]
    for name in (
        ALIGNMENT_ARTIFACT,
        ELIGIBILITY_ARTIFACT,
        FORWARD_COVERAGE_ARTIFACT,
        TYPED_COMPLETION_ARTIFACT,
        LEAKAGE_ARTIFACT,
        PROVIDER_ALIGNMENT_ARTIFACT,
        CHECK_ARTIFACT,
    ):
        print(f"artifact={runtime / name}")
    print(f"status={checks['status']}")
    print(f"relationship_count={checks['relationship_count']}")
    print(f"classified_window_count={checks['classified_window_count']}")
    print(f"eligible_forward_score_input_count={checks['eligible_forward_score_input_count']}")
    print(f"provider_alignment_record_count={checks['provider_alignment_record_count']}")
    print(
        "provider_eligible_forward_window_count="
        f"{checks['provider_eligible_forward_window_count']}"
    )
    print(
        "provider_future_label_value_count="
        f"{checks['provider_future_label_value_count']}"
    )
    print(f"typed_evidence_gap_count={checks['typed_evidence_gap_count']}")
    print(f"typed_evidence_completed_count={checks['typed_evidence_completed_count']}")
    print(f"eligible_leakage_violation_count={checks['eligible_leakage_violation_count']}")
    print("plbg_v2_overlay=validated")
    print(f"source_independence_cluster_count={checks['source_independence_cluster_count']}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
