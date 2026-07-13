#!/usr/bin/env python3
"""Build and validate the canonical Results & Lessons projection."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_learning_cycle_view_model import (  # noqa: E402
    CHECK_ARTIFACT,
    LEARNING_CYCLE_ARTIFACT,
    LEARNING_CYCLE_EVENTS_ARTIFACT,
    build_and_write_learning_cycle_view_model,
)
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    _model, checks, errors = build_and_write_learning_cycle_view_model(settings)
    for name in (LEARNING_CYCLE_ARTIFACT, LEARNING_CYCLE_EVENTS_ARTIFACT, CHECK_ARTIFACT):
        print(f"artifact={runtime / name}")
    for key in (
        "status",
        "implementation_ready",
        "attribution_record_count",
        "qadam_origin_outcome_count",
        "learnable_postmortem_count",
        "learnable_event_count",
        "mirror_reference_count",
        "proof_eligible_count",
        "mirror_records_are_reference_only",
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
