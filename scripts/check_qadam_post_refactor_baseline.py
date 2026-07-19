#!/usr/bin/env python3
"""Build and validate RF-6 legacy quarantine and post-refactor baseline."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402
from orchestrator.qadam_post_refactor_baseline import (  # noqa: E402
    BEHAVIOR_DIFF_ARTIFACT,
    CHECK_ARTIFACT,
    PLAN_REBASELINE_ARTIFACT,
    POST_BASELINE_ARTIFACT,
    QUARANTINE_ARTIFACT,
    build_and_write_post_refactor_baseline,
)


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    bundle, checks, errors = build_and_write_post_refactor_baseline(settings)
    quarantine = bundle["quarantine"]
    behavior = bundle["behavior"]
    plan = bundle["plan"]
    print(f"quarantine_artifact={runtime / QUARANTINE_ARTIFACT}")
    print(f"post_baseline_artifact={runtime / POST_BASELINE_ARTIFACT}")
    print(f"behavior_diff_artifact={runtime / BEHAVIOR_DIFF_ARTIFACT}")
    print(f"plan_rebaseline_artifact={runtime / PLAN_REBASELINE_ARTIFACT}")
    print(f"checks_artifact={runtime / CHECK_ARTIFACT}")
    print(f"status={checks['status']}")
    print(f"legacy_component_count={quarantine['legacy_component_count']}")
    print(f"legacy_file_deletion_count={quarantine['legacy_file_deletion_count']}")
    print(f"wave0_legacy_import_count={quarantine['wave0_legacy_import_count']}")
    print(f"canonical_runtime_collision_count={quarantine['canonical_runtime_collision_count']}")
    print(f"unexpected_behavior_diff_count={behavior['unexpected_diff_count']}")
    print(f"plan_drift_status={plan['plan_drift_status']}")
    print(f"prior_wave0_phase_pass_count={plan['prior_wave0_phase_pass_count']}")
    print(f"order_call_count={checks['order_call_count']}")
    print(f"broker_write_count={checks['broker_write_count']}")
    print(f"live_capital_enabled={checks['authority']['live_capital_enabled']}")
    print(f"next_phase={checks['next_phase']}")
    print(f"validation_error_count={len(errors)}")
    if errors:
        for error in errors:
            print(f"error={error}")
        return 1
    print("qadam_post_refactor_baseline_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
