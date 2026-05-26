#!/usr/bin/env python3
"""Validate the Q5-15 Phase 5 certification gate."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase5_certification import (  # noqa: E402
    PHASE5_CERTIFICATION_SCHEMA_VERSION,
    PHASE5_CERTIFICATION_REQUIRED_INPUT_STAGES,
    build_phase5_certification,
    phase5_certification_paths,
    validate_phase5_certification,
    write_phase5_certification,
)


def _first_gate(artifact: dict) -> dict:
    gates = artifact.get("gate_records", [])
    if not gates:
        raise RuntimeError("no Q5-15 gate records produced")
    return gates[0]


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = phase5_certification_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    artifact = build_phase5_certification(settings=settings)
    output_path, history_path, event_log_path, written = write_phase5_certification(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase5_certification(written)
    replay = EventLog(event_log_path, echo=False).replay()

    false_certified_probe = deepcopy(written)
    if written["phase5_certified"] is True:
        false_certified_probe["certification_blockers"] = ["probe_certified_with_blocker"]
        false_certified_probe["certification_blocker_count"] = 1
    else:
        false_certified_probe["phase5_certified"] = True
        false_certified_probe["phase5_complete"] = True
        false_certified_probe["phase5_exit_gate"] = True
        false_certified_probe["phase6_handoff_allowed"] = True
        false_certified_probe["phase7_planning_allowed"] = True
        false_certified_probe["status"] = "eligible"
    false_certified_errors = validate_phase5_certification(false_certified_probe)

    phase7_probe = deepcopy(written)
    phase7_probe["phase7_proof_credit_allowed"] = True
    phase7_errors = validate_phase5_certification(phase7_probe)

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_errors = validate_phase5_certification(live_capital_probe)

    prediction_write_probe = deepcopy(written)
    prediction_write_probe["prediction_market_write_allowed_count"] = 1
    prediction_write_errors = validate_phase5_certification(prediction_write_probe)

    gate_display_probe = deepcopy(written)
    gate_display_probe["gate_records"][0]["display_status"] = "dishonest_status"
    gate_display_errors = validate_phase5_certification(gate_display_probe)

    missing_event_probe = deepcopy(written)
    missing_event_probe["event_log_written"] = False
    missing_event_probe["event_log_event_count"] = 0
    missing_event_errors = validate_phase5_certification(missing_event_probe)

    if validation_errors:
        errors.extend(validation_errors)
    if written["schema_version"] != 1:
        errors.append("artifact_schema_version_mismatch")
    if written["phase5_certification_schema_version"] != PHASE5_CERTIFICATION_SCHEMA_VERSION:
        errors.append("certification_schema_version_mismatch")
    if written["phase7_proof_credit_allowed"] is not False:
        errors.append("phase7_proof_credit_allowed")
    if written["input_gate_count"] != len(PHASE5_CERTIFICATION_REQUIRED_INPUT_STAGES):
        errors.append("input_gate_count_mismatch")
    if written["phase5_certified"] is True:
        if written["status"] != "eligible":
            errors.append("certification_not_eligible")
        if written["stage_status"] != "phase5_certified":
            errors.append("certification_stage_status_mismatch")
        if written["phase5_exit_gate"] is not True:
            errors.append("phase5_exit_gate_not_true")
        if written["phase6_handoff_allowed"] is not True:
            errors.append("phase6_handoff_not_allowed")
        if written["phase7_planning_allowed"] is not True:
            errors.append("phase7_planning_not_allowed")
        if written["input_gate_blocked_count"] != 0:
            errors.append("input_gate_blocked_count_nonzero")
        if written["certification_blocker_count"] != 0:
            errors.append("certification_blocker_count_nonzero")
        if written["certification_blockers"]:
            errors.append("certification_blockers_present")
        if written["paper_trade_drill_complete"] is not True:
            errors.append("paper_trade_drill_not_complete")
        if written["paper_trade_drill_exit_gate_passed"] is not True:
            errors.append("paper_trade_drill_exit_gate_not_passed")
        for count_key in (
            "submitted_paper_order_count",
            "open_position_count",
            "closed_trade_count",
            "postmortem_due_count",
        ):
            if int(written.get(count_key, 0) or 0) <= 0:
                errors.append(f"certification_missing_count:{count_key}")
    else:
        if written["status"] != "blocked":
            errors.append("certification_not_blocked")
        if written["phase5_exit_gate"] is not False:
            errors.append("phase5_exit_gate_true")
        if written["phase6_handoff_allowed"] is not False:
            errors.append("phase6_handoff_allowed")
        if written["phase7_planning_allowed"] is not False:
            errors.append("phase7_planning_allowed")
        if written["input_gate_blocked_count"] < 1:
            errors.append("input_gate_blocked_count_missing")
        if "q5_14_exit_gate_not_passed" not in written["certification_blockers"]:
            errors.append("q5_14_exit_gate_blocker_missing")
        if "q5_14_paper_trade_lifecycle_incomplete" not in written["certification_blockers"]:
            errors.append("q5_14_lifecycle_blocker_missing")
        if written["paper_trade_drill_complete"] is not False:
            errors.append("paper_trade_drill_complete_true")
        if written["paper_trade_drill_exit_gate_passed"] is not False:
            errors.append("paper_trade_drill_exit_gate_true")
        if int(written.get("postmortem_due_count", 0) or 0) > 0:
            if "postmortem_due_missing" in written["certification_blockers"]:
                errors.append("postmortem_due_still_blocked")
        elif "postmortem_due_missing" not in written["certification_blockers"]:
            errors.append("postmortem_due_blocker_missing")
    for count_key in (
        "live_capital_enabled_count",
        "phase7_proof_credit_allowed_count",
    ):
        if int(written.get(count_key, 0) or 0) != 0:
            errors.append(f"blocked_certification_count_nonzero:{count_key}")
    if written["event_log_written"] is not True:
        errors.append("event_log_not_written")
    if written["event_log_event_count"] != 1:
        errors.append("event_log_event_count_mismatch")
    if replay["total_events"] != 1:
        errors.append("event_log_replay_count_mismatch")
    first_gate = _first_gate(written)
    if first_gate.get("display_status") != first_gate.get("backend_status"):
        errors.append("first_gate_display_backend_mismatch")
    if first_gate.get("ui_inferred_readiness") is not False:
        errors.append("first_gate_ui_inferred_readiness")
    if "phase5_certified_with_blockers" not in false_certified_errors:
        errors.append("false_certification_probe_not_rejected")
    if "phase7_proof_credit_allowed" not in phase7_errors:
        errors.append("phase7_probe_not_rejected")
    if "certification_authority_enabled:live_capital_enabled" not in live_capital_errors:
        errors.append("live_capital_probe_not_rejected")
    if (
        "certification_blocking_count_nonzero:prediction_market_write_allowed_count"
        not in prediction_write_errors
    ):
        errors.append("prediction_write_probe_not_rejected")
    if "gate_display_backend_mismatch" not in gate_display_errors:
        errors.append("gate_display_probe_not_rejected")
    if "blocked_certification_without_blockers" in missing_event_errors:
        errors.append("missing_event_probe_mutated_blockers")

    print(f"phase5_certification_status={written['status']}")
    print(f"phase5_certification_schema_version={PHASE5_CERTIFICATION_SCHEMA_VERSION}")
    print(f"phase5_certification_artifact_path={output_path}")
    print(f"phase5_certification_history_path={history_path}")
    print(f"phase5_certification_event_log_path={event_log_path}")
    print(f"phase5_certification_stage_status={written['stage_status']}")
    print(f"phase5_certification_phase5_certified={written['phase5_certified']}")
    print(f"phase5_certification_phase5_exit_gate={written['phase5_exit_gate']}")
    print(f"phase5_certification_phase6_handoff_allowed={written['phase6_handoff_allowed']}")
    print(f"phase5_certification_phase7_planning_allowed={written['phase7_planning_allowed']}")
    print(
        "phase5_certification_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(f"phase5_certification_input_gate_count={written['input_gate_count']}")
    print(f"phase5_certification_input_gate_passed_count={written['input_gate_passed_count']}")
    print(f"phase5_certification_input_gate_blocked_count={written['input_gate_blocked_count']}")
    print(f"phase5_certification_blocker_count={written['certification_blocker_count']}")
    print(
        "phase5_certification_paper_trade_drill_complete="
        f"{written['paper_trade_drill_complete']}"
    )
    print(
        "phase5_certification_paper_trade_drill_exit_gate_passed="
        f"{written['paper_trade_drill_exit_gate_passed']}"
    )
    print(
        "phase5_certification_submitted_paper_order_count="
        f"{written['submitted_paper_order_count']}"
    )
    print(f"phase5_certification_open_position_count={written['open_position_count']}")
    print(f"phase5_certification_closed_trade_count={written['closed_trade_count']}")
    print(f"phase5_certification_postmortem_due_count={written['postmortem_due_count']}")
    print(f"phase5_certification_live_capital_enabled_count={written['live_capital_enabled_count']}")
    print(f"phase5_certification_event_log_written={written['event_log_written']}")
    print(f"phase5_certification_event_log_event_count={written['event_log_event_count']}")
    print(f"phase5_certification_event_log_replay_total_events={replay['total_events']}")
    print(f"phase5_certification_false_certified_probe_error_count={len(false_certified_errors)}")
    print(f"phase5_certification_phase7_probe_error_count={len(phase7_errors)}")
    print(f"phase5_certification_live_capital_probe_error_count={len(live_capital_errors)}")
    print(
        "phase5_certification_prediction_write_probe_error_count="
        f"{len(prediction_write_errors)}"
    )
    print(f"phase5_certification_gate_display_probe_error_count={len(gate_display_errors)}")
    print(f"phase5_certification_missing_event_probe_error_count={len(missing_event_errors)}")
    print("phase5_certification_boundary=" + written["boundary"])

    if errors:
        for error in sorted(set(errors)):
            print(f"phase5_certification_error={error}")
        print("phase5_certification_check=failed")
        return 1

    print("phase5_certification_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
