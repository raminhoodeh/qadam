#!/usr/bin/env python3
"""Build and validate OR-13 continuous forward shadow state."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_forward_shadow import (  # noqa: E402
    CALIBRATION_ARTIFACT,
    CHECK_ARTIFACT,
    DECISIONS_ARTIFACT,
    HEARTBEAT_ARTIFACT,
    OUTCOMES_ARTIFACT,
    PROMOTION_ARTIFACT,
    STATE_ARTIFACT,
    build_and_write_forward_shadow,
)
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    _bundle, checks, errors = build_and_write_forward_shadow(settings)
    for name in (
        STATE_ARTIFACT,
        DECISIONS_ARTIFACT,
        OUTCOMES_ARTIFACT,
        CALIBRATION_ARTIFACT,
        PROMOTION_ARTIFACT,
        HEARTBEAT_ARTIFACT,
        CHECK_ARTIFACT,
    ):
        print(f"artifact={runtime / name}")
    for key in (
        "status",
        "implementation_ready",
        "implementation_complete",
        "phase_acceptance_ready",
        "service_state",
        "supervisor_running",
        "supervisor_heartbeat_proves_shadow_cycle",
        "shadow_service_cycle_fresh",
        "continuous_scheduler_installed",
        "shadow_service_running",
        "eligible_hypothesis_count",
        "eligible_waiting_for_entry_count",
        "valid_no_eligible_hypothesis_outcome",
        "decision_count",
        "outcome_count",
        "completed_or_typed_expiry_count",
        "promotion_ready",
        "real_elapsed_days",
        "estimated_power",
        "calibration_state",
        "simulated_elapsed_time_count",
        "paper_order_created_count",
        "proof_credit_count",
        "broker_write_count",
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
