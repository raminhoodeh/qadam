#!/usr/bin/env python3
"""Build and validate the canonical Tests & Improvements projection."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_improvement_pipeline_view_model import (  # noqa: E402
    CHECK_ARTIFACT,
    IMPROVEMENT_PIPELINE_ARTIFACT,
    IMPROVEMENT_PROPOSALS_ARTIFACT,
    build_and_write_improvement_pipeline_view_model,
)
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    _model, checks, errors = build_and_write_improvement_pipeline_view_model(settings)
    for name in (IMPROVEMENT_PIPELINE_ARTIFACT, IMPROVEMENT_PROPOSALS_ARTIFACT, CHECK_ARTIFACT):
        print(f"artifact={runtime / name}")
    for key in (
        "status",
        "implementation_ready",
        "attribution_record_count",
        "excluded_mirror_record_count",
        "proposal_record_count",
        "active_candidate_count",
        "ready_for_review_count",
        "applied_version_count",
        "mirror_records_excluded_from_proposals",
        "non_applied_stage1_handoffs_are_inert",
        "paper_order_created_count",
        "broker_write_count",
    ):
        print(f"{key}={checks[key]}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
