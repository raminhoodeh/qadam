#!/usr/bin/env python3
"""Build and validate OR-5 Pattern Score V3."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402
from orchestrator.qadam_pattern_score_v3 import (  # noqa: E402
    CHECK_ARTIFACT,
    DASHBOARD_ARTIFACT,
    FEATURE_REGISTRY_ARTIFACT,
    PRIMARY_ARTIFACT,
    RECORDS_ARTIFACT,
    REJECTIONS_ARTIFACT,
    build_and_write_pattern_score_v3,
)


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    _bundle, checks, errors = build_and_write_pattern_score_v3(settings)
    from orchestrator.runtime.command import report_work_result
    report_work_result(checks, errors)
    for name in (
        FEATURE_REGISTRY_ARTIFACT,
        PRIMARY_ARTIFACT,
        RECORDS_ARTIFACT,
        REJECTIONS_ARTIFACT,
        DASHBOARD_ARTIFACT,
        CHECK_ARTIFACT,
    ):
        print(f"artifact={runtime / name}")
    for key in (
        "status",
        "record_count",
        "strategy_agnostic_record_count",
        "negative_control_record_count",
        "deterministic_rerun_passed",
        "material_change_detected",
        "canonical_score_generation_preserved",
        "last_material_change_at",
        "future_field_denial_passed",
        "missing_feature_policy_passed",
    ):
        print(f"{key}={checks[key]}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
