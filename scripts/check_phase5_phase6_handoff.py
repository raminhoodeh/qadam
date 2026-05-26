#!/usr/bin/env python3
"""Validate the Q5E-10 Phase 5 to Phase 6 handoff closeout."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase5_phase6_handoff import (  # noqa: E402
    PHASE5_PHASE6_HANDOFF_SCHEMA_VERSION,
    build_phase5_phase6_handoff,
    phase5_phase6_handoff_paths,
    validate_phase5_phase6_handoff,
    write_phase5_phase6_handoff,
)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = phase5_phase6_handoff_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    artifact = build_phase5_phase6_handoff(settings=settings)
    output_path, history_path, event_log_path, written = write_phase5_phase6_handoff(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase5_phase6_handoff(written)
    replay = EventLog(event_log_path, echo=False).replay()

    implementation_probe = deepcopy(written)
    implementation_probe["phase6_learning_loop_implementation_allowed"] = True
    implementation_probe["phase6_learning_write_allowed"] = True
    implementation_probe["phase6_learning_write_allowed_count"] = 1
    implementation_errors = validate_phase5_phase6_handoff(implementation_probe)

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase5_phase6_handoff(proof_credit_probe)

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_probe["live_capital_enabled_count"] = 1
    live_capital_errors = validate_phase5_phase6_handoff(live_capital_probe)

    false_plan_probe = deepcopy(written)
    false_plan_probe["phase5_certified"] = False
    false_plan_probe["blockers"] = []
    false_plan_probe["blocker_count"] = 0
    false_plan_errors = validate_phase5_phase6_handoff(false_plan_probe)

    if validation_errors:
        errors.extend(validation_errors)
    if written["status"] != "eligible":
        errors.append("handoff_not_eligible")
    if written["handoff_state"] != "phase6_learning_loop_plan_ready":
        errors.append("handoff_state_mismatch")
    if written["phase5_certified"] is not True:
        errors.append("phase5_not_certified")
    if written["phase5_exit_gate"] is not True:
        errors.append("phase5_exit_gate_not_open")
    if written["phase6_handoff_allowed"] is not True:
        errors.append("phase6_handoff_not_allowed")
    if written["phase7_planning_allowed"] is not True:
        errors.append("phase7_planning_not_allowed")
    if written["phase7_proof_credit_allowed"] is not False:
        errors.append("phase7_proof_credit_allowed")
    if written["phase6_learning_loop_plan_allowed"] is not True:
        errors.append("phase6_plan_not_allowed")
    if written["phase6_learning_loop_implementation_allowed"] is not False:
        errors.append("phase6_implementation_allowed")
    if written["paper_trade_drill_complete"] is not True:
        errors.append("paper_trade_drill_not_complete")
    if written["paper_trade_drill_exit_gate_passed"] is not True:
        errors.append("paper_trade_drill_exit_not_passed")
    if written["paper_trade_drill_blocker_count"] != 0:
        errors.append("paper_trade_drill_blockers_present")
    if written["downstream_staging_allowed_count"] != 1:
        errors.append("downstream_staging_count_mismatch")
    for count_key in (
        "submitted_order_count",
        "mirrored_order_count",
        "closed_trade_count",
        "postmortem_due_count",
    ):
        if int(written.get(count_key, 0) or 0) < 1:
            errors.append(f"handoff_missing_count:{count_key}")
    if written["failed_reconciliation_count"] != 0:
        errors.append("failed_reconciliation_present")
    if written["guarded_postmortem_due_ready"] is not True:
        errors.append("guarded_postmortem_due_not_ready")
    if written["source_validation_error_count"] != 0:
        errors.append("source_validation_errors_present")
    if written["source_recorded_count"] != written["required_source_count"]:
        errors.append("source_recorded_count_mismatch")
    if written["blocker_count"] != 0:
        errors.append("handoff_blockers_present")
    if written["event_log_written"] is not True:
        errors.append("event_log_not_written")
    if written["event_log_event_count"] != 1:
        errors.append("event_log_count_mismatch")
    if replay["total_events"] != 1:
        errors.append("event_replay_count_mismatch")
    if "phase6_authority_enabled_before_q6_0:phase6_learning_loop_implementation_allowed" not in (
        implementation_errors
    ):
        errors.append("implementation_probe_not_rejected")
    if "phase7_proof_credit_allowed" not in proof_credit_errors:
        errors.append("proof_credit_probe_not_rejected")
    if "handoff_phase5_authority_enabled:live_capital_enabled" not in live_capital_errors:
        errors.append("live_capital_probe_not_rejected")
    if "handoff_plan_allowed_missing_true:phase5_certified" not in false_plan_errors:
        errors.append("false_plan_probe_not_rejected")

    print(f"phase5_phase6_handoff_status={written['status']}")
    print(f"phase5_phase6_handoff_schema_version={PHASE5_PHASE6_HANDOFF_SCHEMA_VERSION}")
    print(f"phase5_phase6_handoff_artifact_path={output_path}")
    print(f"phase5_phase6_handoff_history_path={history_path}")
    print(f"phase5_phase6_handoff_event_log_path={event_log_path}")
    print(f"phase5_phase6_handoff_state={written['handoff_state']}")
    print(f"phase5_phase6_handoff_phase5_certified={written['phase5_certified']}")
    print(f"phase5_phase6_handoff_phase5_exit_gate={written['phase5_exit_gate']}")
    print(f"phase5_phase6_handoff_phase6_handoff_allowed={written['phase6_handoff_allowed']}")
    print(
        "phase5_phase6_handoff_phase6_plan_allowed="
        f"{written['phase6_learning_loop_plan_allowed']}"
    )
    print(
        "phase5_phase6_handoff_phase6_implementation_allowed="
        f"{written['phase6_learning_loop_implementation_allowed']}"
    )
    print(
        "phase5_phase6_handoff_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(
        "phase5_phase6_handoff_paper_trade_drill_complete="
        f"{written['paper_trade_drill_complete']}"
    )
    print(
        "phase5_phase6_handoff_paper_trade_drill_exit_gate_passed="
        f"{written['paper_trade_drill_exit_gate_passed']}"
    )
    print(
        "phase5_phase6_handoff_downstream_staging_allowed_count="
        f"{written['downstream_staging_allowed_count']}"
    )
    print(f"phase5_phase6_handoff_closed_trade_count={written['closed_trade_count']}")
    print(f"phase5_phase6_handoff_postmortem_due_count={written['postmortem_due_count']}")
    print(
        "phase5_phase6_handoff_guarded_postmortem_due_ready="
        f"{written['guarded_postmortem_due_ready']}"
    )
    print(f"phase5_phase6_handoff_blocker_count={written['blocker_count']}")
    print(
        "phase5_phase6_handoff_live_capital_enabled_count="
        f"{written['live_capital_enabled_count']}"
    )
    print(
        "phase5_phase6_handoff_event_log_replay_total_events="
        f"{replay['total_events']}"
    )
    print(
        "phase5_phase6_handoff_implementation_probe_error_count="
        f"{len(implementation_errors)}"
    )
    print(
        "phase5_phase6_handoff_proof_credit_probe_error_count="
        f"{len(proof_credit_errors)}"
    )
    print(
        "phase5_phase6_handoff_live_capital_probe_error_count="
        f"{len(live_capital_errors)}"
    )
    print(
        "phase5_phase6_handoff_false_plan_probe_error_count="
        f"{len(false_plan_errors)}"
    )
    print(f"phase5_phase6_handoff_next_stage={written['recommended_next_stage']}")
    print("phase5_phase6_handoff_boundary=" + written["boundary"])

    if errors:
        for error in sorted(set(errors)):
            print(f"phase5_phase6_handoff_error={error}")
        print("phase5_phase6_handoff_check=failed")
        return 1

    print("phase5_phase6_handoff_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
