#!/usr/bin/env python3
"""Validate PT-10 paper-live certification."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.paper_live_certification import (  # noqa: E402
    PAPER_LIVE_CERTIFICATION_SCHEMA_VERSION,
    build_paper_live_certification,
    paper_live_certification_paths,
    validate_paper_live_certification,
    write_paper_live_certification,
)


def _has_error(errors: list[str], expected: str) -> bool:
    return any(error == expected or error.startswith(expected) for error in errors)


def _expected_status(written: dict) -> str:
    if written["paper_live_certified"] is True:
        return "paper_live_certified"
    if written["paper_live_control_plane_certified"] is not True:
        return "blocked_paper_live_control_plane"
    blockers = set(written["certification_blockers"])
    has_qctrl_blocker = bool(
        blockers
        & {
            "qctrl_product_access_ready",
            "qctrl_hold_cleared_for_submit",
        }
    )
    has_phase7_blocker = bool(
        blockers
        & {
            "phase7_30_day_run_complete",
            "phase7_demo_proof_certified",
        }
    )
    if has_qctrl_blocker and has_phase7_blocker:
        return "blocked_pending_qctrl_and_phase7_proof"
    if has_qctrl_blocker:
        return "blocked_pending_qctrl"
    if has_phase7_blocker:
        return "blocked_pending_phase7_proof"
    return "blocked_pending_certification_gates"


def _paper_live_submission_delegation_error(written: dict) -> str | None:
    expected = (
        written["paper_live_certified"] is True
        and written["paper_submit_step_allowed"] is True
        and written["qctrl_hold_active"] is not True
    )
    actual = written["paper_live_submission_delegation_allowed"] is True
    if actual == expected:
        return None
    if expected:
        return "paper_live_submission_delegation_not_enabled"
    return "paper_live_submission_unexpectedly_delegated"


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = paper_live_certification_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    artifact = build_paper_live_certification(settings=settings)
    output_path, history_path, event_log_path, written = write_paper_live_certification(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_paper_live_certification(written)
    replay = EventLog(event_log_path, echo=False).replay()

    false_certified_probe = deepcopy(written)
    false_certified_probe["paper_live_certified"] = True
    false_certified_probe["paper_live_control_plane_certified"] = True
    false_certified_probe["paper_live_operation_allowed"] = True
    false_certified_probe["paper_live_submission_delegation_allowed"] = True
    false_certified_probe["status"] = "paper_live_certified"
    false_certified_probe["stage_status"] = "paper_live_certified"
    false_certified_probe["certification_state"] = "certified"
    false_certified_probe["certification_blockers"] = ["probe_blocker"]
    false_certified_probe["certification_blocker_count"] = 1
    false_certified_errors = validate_paper_live_certification(false_certified_probe)

    qctrl_bypass_probe = deepcopy(written)
    qctrl_bypass_probe["qctrl_hold_active"] = True
    qctrl_bypass_probe["paper_submit_step_allowed"] = True
    qctrl_bypass_errors = validate_paper_live_certification(qctrl_bypass_probe)

    hidden_hold_probe = deepcopy(written)
    hidden_hold_probe["qctrl_hold_active"] = True
    hidden_hold_probe["paper_submit_visible_as_held"] = False
    hidden_hold_errors = validate_paper_live_certification(hidden_hold_probe)

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_probe["unsafe_write_counter_total"] = 1
    live_capital_errors = validate_paper_live_certification(live_capital_probe)

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_errors = validate_paper_live_certification(proof_credit_probe)

    live_send_probe = deepcopy(written)
    live_send_probe["notification_live_send_allowed_count"] = 1
    live_send_probe["unsafe_write_counter_total"] = 1
    live_send_errors = validate_paper_live_certification(live_send_probe)

    gate_display_probe = deepcopy(written)
    gate_display_probe["gate_records"][0]["display_status"] = "dishonest_status"
    gate_display_errors = validate_paper_live_certification(gate_display_probe)

    gate_ui_probe = deepcopy(written)
    gate_ui_probe["gate_records"][0]["ui_inferred_readiness"] = True
    gate_ui_errors = validate_paper_live_certification(gate_ui_probe)

    missing_event_probe = deepcopy(written)
    missing_event_probe["event_log_written"] = False
    missing_event_probe["event_log_event_count"] = 0
    missing_event_errors = validate_paper_live_certification(missing_event_probe)

    if validation_errors:
        errors.extend(validation_errors)
    if written["schema_version"] != PAPER_LIVE_CERTIFICATION_SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if written["stage"] != "PT-10":
        errors.append("stage_mismatch")
    if written["paper_live_certification_gate_evaluated"] is not True:
        errors.append("certification_gate_not_evaluated")
    if written["paper_live_control_plane_certified"] is not True:
        errors.append("control_plane_not_certified")
    if written["control_plane_blocker_count"] != 0:
        errors.append("control_plane_blockers_present")
    if written["paper_live_certified"] is not True:
        errors.append("paper_live_not_certified")
    if written["paper_live_operation_allowed"] is not True:
        errors.append("paper_live_operation_not_allowed")
    if written["paper_live_unattended_execution_delegation_enabled"] is not True:
        errors.append("paper_live_unattended_delegation_not_enabled")
    if submission_error := _paper_live_submission_delegation_error(written):
        errors.append(submission_error)
    if written["status"] != _expected_status(written):
        errors.append("unexpected_pt10_status")
    if written["stage_status"] != "paper_live_certified":
        errors.append("unexpected_stage_status")
    required_current_blockers = set()
    if written["qctrl_product_access_verified"] is not True:
        required_current_blockers.add("qctrl_product_access_ready")
    if written["qctrl_hold_active"] is True:
        required_current_blockers.add("qctrl_hold_cleared_for_submit")
    if not required_current_blockers.issubset(set(written["certification_blockers"])):
        errors.append("expected_current_certification_blockers_missing")
    if "phase7_30_day_run_complete" in written["certification_blockers"]:
        errors.append("legacy_30_day_proof_still_blocks_paper_live")
    if "phase7_demo_proof_certified" in written["certification_blockers"]:
        errors.append("legacy_demo_proof_still_blocks_paper_live")
    if written["qctrl_product_access_verified"] is True:
        if "qctrl_product_access_ready" in written["certification_blockers"]:
            errors.append("qctrl_product_access_still_blocking_after_verification")
    else:
        if "qctrl_product_access_ready" not in written["certification_blockers"]:
            errors.append("qctrl_product_access_blocker_missing")
    if written["qctrl_hold_active"] is True:
        if written["qctrl_hold_visible"] is not True:
            errors.append("qctrl_hold_not_visible")
        if written["paper_submit_visible_as_held"] is not True:
            errors.append("submit_hold_not_visible")
    else:
        if "qctrl_hold_cleared_for_submit" in written["certification_blockers"]:
            errors.append("qctrl_hold_still_blocking_after_clear")
    if written["phase7_30_day_run_complete"] is not False:
        errors.append("legacy_30_day_unexpectedly_complete")
    if written["phase7_demo_proof_certified"] is not False:
        errors.append("legacy_proof_unexpectedly_certified")
    if written["paper_growth_trial_target_active"] is not True:
        errors.append("paper_growth_trial_target_not_active")
    if written["paper_growth_trial_starting_value_gbp"] != 100000:
        errors.append("paper_growth_trial_starting_value_mismatch")
    if written["paper_growth_trial_target_value_gbp"] != 200000:
        errors.append("paper_growth_trial_target_value_mismatch")
    if written["paper_growth_trial_horizon_days"] != 60:
        errors.append("paper_growth_trial_horizon_mismatch")
    if written["live_capital_enabled"] is not False:
        errors.append("live_capital_enabled")
    if written["phase7_proof_credit_allowed"] is not False:
        errors.append("phase7_proof_credit_allowed")
    if written["unsafe_write_counter_total"] != 0:
        errors.append("unsafe_write_counter_nonzero")
    if written["event_log_written"] is not True:
        errors.append("event_log_not_written")
    if written["event_log_event_count"] != 1:
        errors.append("event_log_event_count_mismatch")
    if replay["total_events"] != 1:
        errors.append("event_log_replay_count_mismatch")
    if not _has_error(false_certified_errors, "paper_live_certified_with_blockers"):
        errors.append("false_certified_probe_not_rejected")
    if not _has_error(qctrl_bypass_errors, "paper_live_certification_qctrl_hold_bypassed"):
        errors.append("qctrl_bypass_probe_not_rejected")
    if not _has_error(hidden_hold_errors, "paper_live_certification_qctrl_hold_not_visible"):
        errors.append("hidden_hold_probe_not_rejected")
    if not _has_error(live_capital_errors, "paper_live_certification_forbidden:live_capital_enabled"):
        errors.append("live_capital_probe_not_rejected")
    if not _has_error(proof_credit_errors, "paper_live_certification_phase7_proof_credit_allowed"):
        errors.append("proof_credit_probe_not_rejected")
    if not _has_error(
        live_send_errors,
        "paper_live_certification_unsafe_counter_nonzero:notification_live_send_allowed_count",
    ):
        errors.append("live_send_probe_not_rejected")
    if not _has_error(gate_display_errors, "paper_live_certification_gate_display_mismatch"):
        errors.append("gate_display_probe_not_rejected")
    if not _has_error(gate_ui_errors, "paper_live_certification_gate_ui_inferred"):
        errors.append("gate_ui_probe_not_rejected")
    if not _has_error(missing_event_errors, "paper_live_certification_event_log_missing"):
        errors.append("missing_event_probe_not_rejected")

    print(f"paper_live_certification_status={written['status']}")
    print(f"paper_live_certification_schema_version={PAPER_LIVE_CERTIFICATION_SCHEMA_VERSION}")
    print(f"paper_live_certification_artifact_path={output_path}")
    print(f"paper_live_certification_history_path={history_path}")
    print(f"paper_live_certification_event_log_path={event_log_path}")
    print(f"paper_live_certification_stage_status={written['stage_status']}")
    print(
        "paper_live_certification_control_plane_certified="
        f"{written['paper_live_control_plane_certified']}"
    )
    print(f"paper_live_certification_paper_live_certified={written['paper_live_certified']}")
    print(
        "paper_live_certification_operation_allowed="
        f"{written['paper_live_operation_allowed']}"
    )
    print(
        "paper_live_certification_unattended_delegation_enabled="
        f"{written['paper_live_unattended_execution_delegation_enabled']}"
    )
    print(
        "paper_live_certification_unattended_delegation_reason="
        f"{written['paper_live_unattended_execution_delegation_reason']}"
    )
    print(
        "paper_live_certification_submission_delegation_allowed="
        f"{written['paper_live_submission_delegation_allowed']}"
    )
    print(f"paper_live_certification_input_gate_count={written['input_gate_count']}")
    print(
        "paper_live_certification_input_gate_passed_count="
        f"{written['input_gate_passed_count']}"
    )
    print(
        "paper_live_certification_input_gate_blocked_count="
        f"{written['input_gate_blocked_count']}"
    )
    print(
        "paper_live_certification_control_plane_blocker_count="
        f"{written['control_plane_blocker_count']}"
    )
    print(
        "paper_live_certification_blocker_count="
        f"{written['certification_blocker_count']}"
    )
    print(
        "paper_live_certification_blockers="
        + ",".join(written["certification_blockers"])
    )
    print(
        "paper_live_certification_qctrl_product_access_verified="
        f"{written['qctrl_product_access_verified']}"
    )
    print(
        "paper_live_certification_qctrl_paper_consultation_ready="
        f"{written['qctrl_paper_consultation_ready']}"
    )
    print(f"paper_live_certification_qctrl_hold_active={written['qctrl_hold_active']}")
    print(f"paper_live_certification_qctrl_hold_visible={written['qctrl_hold_visible']}")
    print(
        "paper_live_certification_paper_submit_step_allowed="
        f"{written['paper_submit_step_allowed']}"
    )
    print(
        "paper_live_certification_paper_submit_visible_as_held="
        f"{written['paper_submit_visible_as_held']}"
    )
    print(
        "paper_live_certification_phase7_run_state="
        f"{written['phase7_run_state']}"
    )
    print(
        "paper_live_certification_phase7_active_day_number="
        f"{written['phase7_active_day_number']}"
    )
    print(
        "paper_live_certification_phase7_30_day_run_complete="
        f"{written['phase7_30_day_run_complete']}"
    )
    print(
        "paper_live_certification_phase7_demo_proof_certified="
        f"{written['phase7_demo_proof_certified']}"
    )
    print(
        "paper_live_certification_paperops_30_day_operations_status="
        f"{written['paperops_30_day_operations_status']}"
    )
    print(
        "paper_live_certification_paperops_cockpit_notification_status="
        f"{written['paperops_cockpit_notification_status']}"
    )
    print(
        "paper_live_certification_paper_operational_cycle_command_count="
        f"{written['paper_operational_cycle_command_count']}"
    )
    print(
        "paper_live_certification_live_capital_enabled="
        f"{written['live_capital_enabled']}"
    )
    print(
        "paper_live_certification_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(
        "paper_live_certification_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(f"paper_live_certification_event_log_written={written['event_log_written']}")
    print(f"paper_live_certification_event_log_event_count={written['event_log_event_count']}")
    print(
        "paper_live_certification_event_log_replay_total_events="
        f"{replay['total_events']}"
    )
    print(
        "paper_live_certification_paper_growth_trial="
        f"{written['paper_growth_trial_starting_value_gbp']}->"
        f"{written['paper_growth_trial_target_value_gbp']}"
        f"/{written['paper_growth_trial_horizon_days']}d"
    )
    print(
        "paper_live_certification_false_certified_probe_error_count="
        f"{len(false_certified_errors)}"
    )
    print(
        "paper_live_certification_qctrl_bypass_probe_error_count="
        f"{len(qctrl_bypass_errors)}"
    )
    print(
        "paper_live_certification_hidden_hold_probe_error_count="
        f"{len(hidden_hold_errors)}"
    )
    print(
        "paper_live_certification_live_capital_probe_error_count="
        f"{len(live_capital_errors)}"
    )
    print(
        "paper_live_certification_proof_credit_probe_error_count="
        f"{len(proof_credit_errors)}"
    )
    print(
        "paper_live_certification_live_send_probe_error_count="
        f"{len(live_send_errors)}"
    )
    print(
        "paper_live_certification_gate_display_probe_error_count="
        f"{len(gate_display_errors)}"
    )
    print(
        "paper_live_certification_gate_ui_probe_error_count="
        f"{len(gate_ui_errors)}"
    )
    print(
        "paper_live_certification_missing_event_probe_error_count="
        f"{len(missing_event_errors)}"
    )
    print("paper_live_certification_boundary=" + written["boundary"])

    if errors:
        for error in sorted(set(errors)):
            print(f"paper_live_certification_error={error}")
        print("paper_live_certification_check=failed")
        return 1

    print("paper_live_certification_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
