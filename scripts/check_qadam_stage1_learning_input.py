#!/usr/bin/env python3
"""Build and validate the applied-only Stage 1 learning input."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402
from orchestrator.qadam_stage1_learning_input import (  # noqa: E402
    CHECK_ARTIFACT,
    STAGE1_HANDOFFS_ARTIFACT,
    STAGE1_INPUT_ARTIFACT,
    build_and_write_stage1_learning_input,
)


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    _model, checks, errors = build_and_write_stage1_learning_input(settings)
    for name in (STAGE1_INPUT_ARTIFACT, STAGE1_HANDOFFS_ARTIFACT, CHECK_ARTIFACT):
        print(f"artifact={runtime / name}")
    for key in (
        "status",
        "implementation_ready",
        "applied_handoff_count",
        "rejected_non_applied_record_count",
        "only_applied_versions_consumed",
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
