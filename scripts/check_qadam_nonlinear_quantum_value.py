#!/usr/bin/env python3
"""Build and validate OR-9 nonlinear/quantum incremental-value state."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_nonlinear_quantum_value import (  # noqa: E402
    CHECK_ARTIFACT,
    COMPARISONS_ARTIFACT,
    EXPERIMENTS_ARTIFACT,
    OVERFIT_ARTIFACT,
    SUMMARY_ARTIFACT,
    build_and_write_nonlinear_quantum_value,
)
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    _state, checks, errors = build_and_write_nonlinear_quantum_value(settings)
    for name in (
        EXPERIMENTS_ARTIFACT,
        COMPARISONS_ARTIFACT,
        SUMMARY_ARTIFACT,
        OVERFIT_ARTIFACT,
        CHECK_ARTIFACT,
    ):
        print(f"artifact={runtime / name}")
    for key in (
        "status",
        "implementation_ready",
        "acceptance_passed",
        "empirical_incremental_value_complete",
        "experiment_count",
        "measured_comparison_count",
        "nonlinear_comparison_count",
        "quantum_comparison_count",
        "useful_nonlinear_comparison_count",
        "useful_quantum_comparison_count",
        "quantum_usefulness_score",
        "quantum_contribution_verdict",
        "classical_baseline_missing_count",
        "holdout_tuning_violation_count",
        "negative_control_false_positive_count",
        "provider_call_attempted",
        "hardware_submission_attempted",
        "hardware_used",
        "quantum_advantage_claim_allowed",
        "edge_creation_allowed",
        "candidate_creation_allowed",
    ):
        print(f"{key}={checks[key]}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 0 if checks.get("acceptance_passed") is True and not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
