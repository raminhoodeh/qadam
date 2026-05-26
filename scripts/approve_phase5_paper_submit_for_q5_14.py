#!/usr/bin/env python3
"""Record Q5-14 paper-submit approval and refresh dependent fail-closed gates."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.cockpit_status import build_cockpit_status, export_cockpit_status  # noqa: E402
from orchestrator.config import Settings  # noqa: E402
from orchestrator.phase5_certification import (  # noqa: E402
    build_phase5_certification,
    validate_phase5_certification,
    write_phase5_certification,
)
from orchestrator.phase5_paper_submit_enablement import (  # noqa: E402
    build_phase5_paper_submit_approval,
    build_phase5_paper_submit_enablement_gate,
    validate_phase5_paper_submit_approval,
    validate_phase5_paper_submit_enablement_bundle,
    write_phase5_paper_submit_approval,
    write_phase5_paper_submit_enablement_gate,
)
from orchestrator.phase5_paper_trade_drill import (  # noqa: E402
    build_phase5_paper_trade_drill,
    validate_phase5_paper_trade_drill_bundle,
    write_phase5_paper_trade_drill,
)
from orchestrator.phase5_system_map import (  # noqa: E402
    validate_phase5_system_map_bundle,
    write_phase5_system_map,
)


APPROVAL_INSTRUCTION = (
    "Fund Manager instruction in the Codex thread on 2026-05-24: proceed with "
    "the Q5-14 exit unblock that you described. This is recorded as explicit "
    "approval for the guarded Alpaca paper-submit gate only, with Q5-3/Q5-6/Q5-7 "
    "prerequisites, broker POST safety checks, live-capital disablement, and "
    "Phase 7 proof-credit denial still enforced."
)


def main() -> int:
    settings = Settings.from_env()

    approval = build_phase5_paper_submit_approval(
        approver_label="fund_manager_ramin",
        approval_instruction=APPROVAL_INSTRUCTION,
        settings=settings,
    )
    approval_path, approval = write_phase5_paper_submit_approval(
        approval,
        settings=settings,
        record_event=True,
    )
    approval_errors = validate_phase5_paper_submit_approval(approval)

    submit_bundle = build_phase5_paper_submit_enablement_gate(settings=settings)
    submit_path, submit_history_path, submit_event_path, submit_bundle = (
        write_phase5_paper_submit_enablement_gate(
            submit_bundle,
            settings=settings,
            record_event=True,
        )
    )
    submit_errors = validate_phase5_paper_submit_enablement_bundle(submit_bundle)

    cockpit_before_drill = build_cockpit_status(settings)
    system_map_path, system_map_history_path, system_map_event_path, system_map = (
        write_phase5_system_map(
            cockpit_before_drill["phase5_system_map"],
            settings=settings,
            record_event=True,
        )
    )
    system_map_errors = validate_phase5_system_map_bundle(system_map)

    drill = build_phase5_paper_trade_drill(settings=settings)
    drill_path, drill_history_path, drill_event_path, drill = write_phase5_paper_trade_drill(
        drill,
        settings=settings,
        record_event=True,
    )
    drill_errors = validate_phase5_paper_trade_drill_bundle(drill)

    certification = build_phase5_certification(settings=settings)
    certification_path, certification_history_path, certification_event_path, certification = (
        write_phase5_certification(
            certification,
            settings=settings,
            record_event=True,
        )
    )
    certification_errors = validate_phase5_certification(certification)

    cockpit_export = export_cockpit_status(
        settings=settings,
        landing_repo_path=ROOT / "landing-page-repo",
    )

    print(f"phase5_paper_submit_approval_path={approval_path}")
    print(f"phase5_paper_submit_approval_state={approval['approval_state']}")
    print(f"phase5_paper_submit_approval_logged={approval['approval_logged']}")
    print(f"phase5_paper_submit_approval_scope={approval['approval_scope']}")
    print(f"phase5_paper_submit_approval_error_count={len(approval_errors)}")
    print(f"phase5_paper_submit_enablement_path={submit_path}")
    print(f"phase5_paper_submit_enablement_history_path={submit_history_path}")
    print(f"phase5_paper_submit_enablement_event_path={submit_event_path}")
    print(
        "phase5_paper_submit_enablement_approval_present="
        f"{submit_bundle['paper_submit_approval_present']}"
    )
    print(
        "phase5_paper_submit_enablement_submit_path_available_count="
        f"{submit_bundle['submit_path_available_count']}"
    )
    print(f"phase5_paper_submit_enablement_blocked_count={submit_bundle['blocked_count']}")
    print(f"phase5_paper_submit_enablement_error_count={len(submit_errors)}")
    print(f"phase5_system_map_path={system_map_path}")
    print(f"phase5_system_map_history_path={system_map_history_path}")
    print(f"phase5_system_map_event_path={system_map_event_path}")
    print(
        "phase5_system_map_paper_submit_approval_state="
        f"{system_map['guardrails']['paper_submit_approval_state']}"
    )
    print(f"phase5_system_map_error_count={len(system_map_errors)}")
    print(f"phase5_paper_trade_drill_path={drill_path}")
    print(f"phase5_paper_trade_drill_history_path={drill_history_path}")
    print(f"phase5_paper_trade_drill_event_path={drill_event_path}")
    print(f"phase5_paper_trade_drill_state={drill['paper_trade_drill_state']}")
    print(
        "phase5_paper_trade_drill_approval_present="
        f"{drill['paper_submit_approval_present']}"
    )
    print(
        "phase5_paper_trade_drill_submit_path_available_count="
        f"{drill['paper_submit_path_available_count']}"
    )
    print(
        "phase5_paper_trade_drill_exit_gate_passed="
        f"{drill['phase5_paper_trade_drill_exit_gate_passed']}"
    )
    print(f"phase5_paper_trade_drill_blockers={','.join(drill['blockers'])}")
    print(f"phase5_paper_trade_drill_error_count={len(drill_errors)}")
    print(f"phase5_certification_path={certification_path}")
    print(f"phase5_certification_history_path={certification_history_path}")
    print(f"phase5_certification_event_path={certification_event_path}")
    print(f"phase5_certification_status={certification['status']}")
    print(f"phase5_certification_phase5_certified={certification['phase5_certified']}")
    print(
        "phase5_certification_phase6_handoff_allowed="
        f"{certification['phase6_handoff_allowed']}"
    )
    print(f"phase5_certification_error_count={len(certification_errors)}")
    print(f"cockpit_status_runtime_path={cockpit_export['runtime_path']}")
    print(f"cockpit_status_landing_path={cockpit_export['landing_path']}")

    errors = (
        approval_errors
        + submit_errors
        + system_map_errors
        + drill_errors
        + certification_errors
    )
    if approval["approval_state"] != "approved" or approval["approval_logged"] is not True:
        errors.append("paper_submit_approval_not_recorded")
    if submit_bundle["paper_submit_approval_present"] is not True:
        errors.append("submit_enablement_approval_not_visible")
    if submit_bundle["submit_path_available_count"] != 0:
        errors.append("submit_path_opened_before_upstream_prerequisites")
    if drill["paper_submit_approval_present"] is not True:
        errors.append("drill_approval_not_visible")
    if drill["phase5_paper_trade_drill_exit_gate_passed"] is not False:
        errors.append("drill_exit_gate_opened_without_lifecycle")
    if certification["phase5_certified"] is not False:
        errors.append("phase5_certified_without_q5_14_lifecycle")
    if certification["phase6_handoff_allowed"] is not False:
        errors.append("phase6_handoff_allowed_without_q5_14_lifecycle")

    if errors:
        for error in sorted(set(errors)):
            print(f"phase5_paper_submit_approval_unblock_error={error}")
        print("phase5_paper_submit_approval_unblock=failed")
        return 1

    print("phase5_paper_submit_approval_unblock=ok_fail_closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
