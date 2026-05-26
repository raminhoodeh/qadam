#!/usr/bin/env python3
"""Validate the Q6-0 Phase 6 re-entry readiness gate."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase6_readiness import (  # noqa: E402
    PHASE6_READINESS_SCHEMA_VERSION,
    build_phase6_readiness,
    phase6_readiness_paths,
    validate_phase6_readiness,
    write_phase6_readiness,
)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = phase6_readiness_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    artifact = build_phase6_readiness(settings=settings)
    output_path, history_path, event_log_path, written = write_phase6_readiness(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase6_readiness(written)
    replay = EventLog(event_log_path, echo=False).replay()

    implementation_probe = deepcopy(written)
    implementation_probe["phase6_learning_loop_implementation_allowed"] = True
    implementation_probe["phase6_postmortem_ingestion_allowed"] = True
    implementation_probe["phase6_postmortem_ingestion_allowed_count"] = 1
    implementation_errors = validate_phase6_readiness(implementation_probe)

    learning_write_probe = deepcopy(written)
    learning_write_probe["phase6_learning_write_allowed"] = True
    learning_write_probe["phase6_knowledge_graph_write_allowed"] = True
    learning_write_probe["phase6_learning_write_allowed_count"] = 1
    learning_write_errors = validate_phase6_readiness(learning_write_probe)

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase6_readiness(proof_credit_probe)

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled_count"] = 1
    live_capital_errors = validate_phase6_readiness(live_capital_probe)

    venue_write_probe = deepcopy(written)
    venue_write_probe["broker_post_called_count"] = 1
    venue_write_probe["prediction_market_write_allowed_count"] = 1
    venue_write_probe["crypto_perps_write_allowed_count"] = 1
    venue_write_errors = validate_phase6_readiness(venue_write_probe)

    false_handoff_probe = deepcopy(written)
    false_handoff_probe["phase5_certified"] = False
    false_handoff_probe["q5e_handoff_status"] = "blocked"
    false_handoff_probe["blockers"] = []
    false_handoff_probe["blocker_count"] = 0
    false_handoff_errors = validate_phase6_readiness(false_handoff_probe)

    policy_mutation_probe = deepcopy(written)
    policy_mutation_probe["phase6_architect_policy_mutation_allowed"] = True
    policy_mutation_probe["phase6_policy_mutation_allowed_count"] = 1
    policy_mutation_errors = validate_phase6_readiness(policy_mutation_probe)

    if validation_errors:
        errors.extend(validation_errors)
    if written["status"] != "ready_for_q6_1_artifact_schema":
        errors.append("phase6_readiness_not_ready")
    if written["readiness_state"] != "phase6_re_entry_gate_passed":
        errors.append("phase6_readiness_state_not_passed")
    if written["phase6_re_entry_gate_passed"] is not True:
        errors.append("phase6_re_entry_gate_not_passed")
    if written["q5e_handoff_artifact_recorded"] is not True:
        errors.append("q5e_handoff_artifact_not_recorded")
    if written["q5e_handoff_validation_error_count"] != 0:
        errors.append("q5e_handoff_validation_errors")
    if written["q5e_handoff_status"] != "eligible":
        errors.append("q5e_handoff_not_eligible")
    if written["q5e_handoff_state"] != "phase6_learning_loop_plan_ready":
        errors.append("q5e_handoff_state_mismatch")
    if written["phase5_certified"] is not True:
        errors.append("phase5_not_certified")
    if written["phase5_exit_gate"] is not True:
        errors.append("phase5_exit_gate_not_passed")
    if written["phase6_handoff_allowed"] is not True:
        errors.append("phase6_handoff_not_allowed")
    if written["phase6_learning_loop_plan_allowed"] is not True:
        errors.append("phase6_plan_not_allowed")
    if written["phase6_learning_loop_implementation_allowed"] is not False:
        errors.append("phase6_implementation_allowed")
    if written["phase6_postmortem_ingestion_allowed"] is not False:
        errors.append("phase6_postmortem_ingestion_allowed")
    if written["phase6_learning_write_allowed"] is not False:
        errors.append("phase6_learning_write_allowed")
    if written["phase6_knowledge_graph_write_allowed"] is not False:
        errors.append("phase6_knowledge_graph_write_allowed")
    if written["phase7_proof_credit_allowed"] is not False:
        errors.append("phase7_proof_credit_allowed")
    if written["phase5_test_trades_count_for_phase7"] is not False:
        errors.append("phase5_test_trades_count_for_phase7")
    if written["paper_trade_drill_complete"] is not True:
        errors.append("paper_trade_drill_not_complete")
    if written["paper_trade_drill_exit_gate_passed"] is not True:
        errors.append("paper_trade_drill_exit_not_passed")
    if written["paper_trade_drill_blocker_count"] != 0:
        errors.append("paper_trade_drill_blockers_present")
    for count_key in (
        "downstream_staging_allowed_count",
        "submitted_order_count",
        "mirrored_order_count",
        "closed_trade_count",
        "postmortem_due_count",
    ):
        if int(written.get(count_key, 0) or 0) < 1:
            errors.append(f"phase6_readiness_missing_count:{count_key}")
    if written["failed_reconciliation_count"] != 0:
        errors.append("failed_reconciliation_present")
    if written["guarded_postmortem_due_ready"] is not True:
        errors.append("guarded_postmortem_due_not_ready")
    if written["phase6_frozen_scope_count"] != 17:
        errors.append("phase6_scope_count_mismatch")
    if written["unsafe_write_counter_total"] != 0:
        errors.append("unsafe_write_counter_nonzero")
    if written["blocker_count"] != 0:
        errors.append("phase6_readiness_blockers_present")
    if written["event_log_written"] is not True:
        errors.append("event_log_not_written")
    if written["event_log_event_count"] != 1:
        errors.append("event_log_count_mismatch")
    if replay["total_events"] != 1:
        errors.append("event_replay_count_mismatch")
    if (
        "phase6_readiness_authority_enabled:phase6_learning_loop_implementation_allowed"
        not in implementation_errors
    ):
        errors.append("implementation_probe_not_rejected")
    if "phase6_readiness_unsafe_count_nonzero:phase6_learning_write_allowed_count" not in (
        learning_write_errors
    ):
        errors.append("learning_write_probe_not_rejected")
    if "phase7_proof_credit_allowed" not in proof_credit_errors:
        errors.append("proof_credit_probe_not_rejected")
    if "phase6_readiness_unsafe_count_nonzero:live_capital_enabled_count" not in (
        live_capital_errors
    ):
        errors.append("live_capital_probe_not_rejected")
    if "phase6_readiness_unsafe_count_nonzero:broker_post_called_count" not in (
        venue_write_errors
    ):
        errors.append("venue_write_probe_not_rejected")
    if "phase6_readiness_passed_missing_true:phase5_certified" not in false_handoff_errors:
        errors.append("false_handoff_probe_not_rejected")
    if (
        "phase6_readiness_authority_enabled:phase6_architect_policy_mutation_allowed"
        not in policy_mutation_errors
    ):
        errors.append("policy_mutation_probe_not_rejected")

    print(f"phase6_readiness_status={written['status']}")
    print(f"phase6_readiness_schema_version={PHASE6_READINESS_SCHEMA_VERSION}")
    print(f"phase6_readiness_artifact_path={output_path}")
    print(f"phase6_readiness_history_path={history_path}")
    print(f"phase6_readiness_event_log_path={event_log_path}")
    print(f"phase6_readiness_state={written['readiness_state']}")
    print(f"phase6_readiness_re_entry_gate_passed={written['phase6_re_entry_gate_passed']}")
    print(f"phase6_readiness_q5e_handoff_status={written['q5e_handoff_status']}")
    print(f"phase6_readiness_q5e_handoff_state={written['q5e_handoff_state']}")
    print(f"phase6_readiness_phase5_certified={written['phase5_certified']}")
    print(f"phase6_readiness_phase5_exit_gate={written['phase5_exit_gate']}")
    print(f"phase6_readiness_phase6_handoff_allowed={written['phase6_handoff_allowed']}")
    print(
        "phase6_readiness_phase6_plan_allowed="
        f"{written['phase6_learning_loop_plan_allowed']}"
    )
    print(
        "phase6_readiness_phase6_implementation_allowed="
        f"{written['phase6_learning_loop_implementation_allowed']}"
    )
    print(
        "phase6_readiness_phase6_postmortem_ingestion_allowed="
        f"{written['phase6_postmortem_ingestion_allowed']}"
    )
    print(
        "phase6_readiness_phase6_learning_write_allowed="
        f"{written['phase6_learning_write_allowed']}"
    )
    print(
        "phase6_readiness_phase6_knowledge_graph_write_allowed="
        f"{written['phase6_knowledge_graph_write_allowed']}"
    )
    print(
        "phase6_readiness_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(
        "phase6_readiness_q6_1_artifact_schema_stage_allowed="
        f"{written['q6_1_artifact_schema_stage_allowed']}"
    )
    print(f"phase6_readiness_frozen_scope_count={written['phase6_frozen_scope_count']}")
    print(f"phase6_readiness_closed_trade_count={written['closed_trade_count']}")
    print(f"phase6_readiness_postmortem_due_count={written['postmortem_due_count']}")
    print(f"phase6_readiness_unsafe_write_counter_total={written['unsafe_write_counter_total']}")
    print(f"phase6_readiness_blocker_count={written['blocker_count']}")
    print(f"phase6_readiness_event_log_replay_total_events={replay['total_events']}")
    print(
        "phase6_readiness_implementation_probe_error_count="
        f"{len(implementation_errors)}"
    )
    print(
        "phase6_readiness_learning_write_probe_error_count="
        f"{len(learning_write_errors)}"
    )
    print(f"phase6_readiness_proof_credit_probe_error_count={len(proof_credit_errors)}")
    print(f"phase6_readiness_live_capital_probe_error_count={len(live_capital_errors)}")
    print(f"phase6_readiness_venue_write_probe_error_count={len(venue_write_errors)}")
    print(f"phase6_readiness_false_handoff_probe_error_count={len(false_handoff_errors)}")
    print(
        "phase6_readiness_policy_mutation_probe_error_count="
        f"{len(policy_mutation_errors)}"
    )
    print(f"phase6_readiness_next_stage={written['recommended_next_stage']}")
    print("phase6_readiness_boundary=" + written["boundary"])

    if errors:
        for error in sorted(set(errors)):
            print(f"phase6_readiness_error={error}")
        print("phase6_readiness_check=failed")
        return 1

    print("phase6_readiness_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
