#!/usr/bin/env python3
"""Build and validate OR-7 separate forward-label and cost contracts."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_forward_labels import (  # noqa: E402
    CHECK_ARTIFACT,
    COST_MODEL_ARTIFACT,
    COVERAGE_ARTIFACT,
    MANIFEST_ARTIFACT,
    QUALITY_ARTIFACT,
    build_and_write_forward_labels,
)
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    _state, checks, errors = build_and_write_forward_labels(settings)
    for name in (
        MANIFEST_ARTIFACT,
        COST_MODEL_ARTIFACT,
        COVERAGE_ARTIFACT,
        QUALITY_ARTIFACT,
        CHECK_ARTIFACT,
    ):
        print(f"artifact={runtime / name}")
    for key in (
        "status",
        "acceptance_passed",
        "implementation_ready",
        "empirical_labels_complete",
        "score_tape_row_count",
        "label_count",
        "gross_label_count",
        "net_label_count",
        "cost_adjusted_counterfactual_label_count",
        "typed_missing_label_count",
        "classification_ratio",
        "cost_model_instrument_count",
        "unsupported_cost_model_count",
        "score_label_order_violation_count",
        "score_plane_unchanged",
        "overlap_group_count",
        "independent_effective_sample_count",
    ):
        print(f"{key}={checks[key]}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 0 if checks.get("acceptance_passed") is True and not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
