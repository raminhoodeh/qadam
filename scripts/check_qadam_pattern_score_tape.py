#!/usr/bin/env python3
"""Build and validate OR-6 historical score-tape state."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402
from orchestrator.qadam_pattern_score_tape import (  # noqa: E402
    CHECK_ARTIFACT,
    MANIFEST_ARTIFACT,
    PROGRESS_ARTIFACT,
    QUALITY_ARTIFACT,
    build_and_write_pattern_score_tape,
)


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    _state, checks, errors = build_and_write_pattern_score_tape(settings)
    for name in (MANIFEST_ARTIFACT, PROGRESS_ARTIFACT, QUALITY_ARTIFACT, CHECK_ARTIFACT):
        print(f"artifact={runtime / name}")
    for key in (
        "status",
        "implementation_ready",
        "empirical_score_tape_complete",
        "partition_count",
        "completed_partition_count",
        "score_tape_row_count",
        "input_alignment_record_count",
        "input_alignment_coverage_ratio",
        "label_column_detected",
        "labels_accessed",
        "future_horizon_metadata_accessed",
        "duplicate_score_count",
    ):
        print(f"{key}={checks[key]}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
