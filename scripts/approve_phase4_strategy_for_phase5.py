#!/usr/bin/env python3
"""Record explicit Phase 4 strategy approval and refresh Phase 5 readiness."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.phase4_approval_record import (  # noqa: E402
    build_fund_manager_approval_event,
    validate_fund_manager_approval_event,
    write_fund_manager_approval_event,
)
from orchestrator.phase4_certification import (  # noqa: E402
    build_phase4_certification,
    validate_phase4_certification,
    write_phase4_certification,
)
from orchestrator.phase4_strategy_toggles import (  # noqa: E402
    build_strategy_toggle_snapshot,
    validate_strategy_toggle_snapshot,
    write_strategy_toggle_snapshot,
)
from orchestrator.phase5_readiness import (  # noqa: E402
    build_phase5_layer_b_readiness,
    validate_phase5_layer_b_readiness,
    write_phase5_layer_b_readiness,
)


APPROVAL_INSTRUCTION = (
    "Fund Manager instruction in the Codex thread on 2026-05-24: do the work "
    "to ensure explicit Fund Manager approval is logged for the amended Phase 4 "
    "strategy, Q4-10 reports approved, Q4-12 certifies, and Phase 5 readiness "
    "allows Layer B implementation."
)


def main() -> int:
    settings = Settings.from_env()

    approval_event = build_fund_manager_approval_event(
        approval_state="approved",
        approver_label="fund_manager_ramin",
        approval_instruction=APPROVAL_INSTRUCTION,
        settings=settings,
    )
    approval_path, approval_event = write_fund_manager_approval_event(
        approval_event,
        settings=settings,
        record_event=True,
    )
    approval_errors = validate_fund_manager_approval_event(approval_event)

    toggle_snapshot = build_strategy_toggle_snapshot(
        settings=settings,
        approval_event=approval_event,
    )
    toggle_path, toggle_snapshot = write_strategy_toggle_snapshot(
        toggle_snapshot,
        settings=settings,
        record_event=True,
    )
    toggle_errors = validate_strategy_toggle_snapshot(toggle_snapshot)

    certification = build_phase4_certification(
        settings=settings,
        approval_event=approval_event,
        strategy_toggle_snapshot=toggle_snapshot,
    )
    certification_path, certification = write_phase4_certification(
        certification,
        settings=settings,
        record_event=True,
    )
    certification_errors = validate_phase4_certification(certification)

    readiness = build_phase5_layer_b_readiness(
        settings=settings,
        phase4_certification=certification,
    )
    readiness_path, readiness_history_path = write_phase5_layer_b_readiness(
        readiness,
        settings=settings,
    )
    readiness_errors = validate_phase5_layer_b_readiness(readiness)

    print(f"phase4_approval_path={approval_path}")
    print(f"phase4_approval_state={approval_event['approval_state']}")
    print(f"phase4_approval_logged={approval_event['approval_logged']}")
    print(f"phase4_approval_error_count={len(approval_errors)}")
    print(f"phase4_toggle_path={toggle_path}")
    print(f"phase4_toggle_approved_shadow_count={toggle_snapshot['approved_shadow_toggle_count']}")
    print(f"phase4_toggle_error_count={len(toggle_errors)}")
    print(f"phase4_certification_path={certification_path}")
    print(f"phase4_certified={certification['phase4_certified']}")
    print(f"phase5_handoff_allowed={certification['phase5_handoff_allowed']}")
    print(f"phase4_certification_error_count={len(certification_errors)}")
    print(f"phase5_readiness_path={readiness_path}")
    print(f"phase5_readiness_history_path={readiness_history_path}")
    print(
        "phase5_layer_b_implementation_allowed="
        f"{readiness['phase5_layer_b_implementation_allowed']}"
    )
    print(f"phase5_readiness_error_count={len(readiness_errors)}")

    errors = approval_errors + toggle_errors + certification_errors + readiness_errors
    if approval_event["approval_state"] != "approved":
        errors.append("approval_state_not_approved")
    if approval_event["approval_logged"] is not True:
        errors.append("approval_not_logged")
    if toggle_snapshot["approved_shadow_toggle_count"] != toggle_snapshot["toggle_count"]:
        errors.append("toggles_not_approved_shadow")
    if certification["phase4_certified"] is not True:
        errors.append("phase4_not_certified")
    if certification["phase5_handoff_allowed"] is not True:
        errors.append("phase5_handoff_not_allowed")
    if readiness["phase5_layer_b_implementation_allowed"] is not True:
        errors.append("phase5_implementation_not_allowed")

    if errors:
        for error in errors:
            print(f"phase4_approval_enablement_error={error}")
        print("phase4_approval_enablement=failed")
        return 1

    print("phase4_approval_enablement=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
