#!/usr/bin/env python3
"""Validate the Q7-0 Phase 7 Demo Proof re-entry gate."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase7_readiness import (  # noqa: E402
    PHASE7_HARNESS_DAY_COUNT,
    PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
    PHASE7_READINESS_SCHEMA_VERSION,
    PHASE7_WEEKLY_PROOF_TRADE_TARGET,
    build_phase7_readiness,
    phase7_readiness_paths,
    validate_phase7_readiness,
    write_phase7_readiness,
)


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = phase7_readiness_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    artifact = build_phase7_readiness(settings=settings)
    output_path, history_path, event_log_path, written = write_phase7_readiness(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase7_readiness(written)
    replay = EventLog(event_log_path, echo=False).replay()

    stale_90_day_probe = deepcopy(written)
    stale_90_day_probe["phase7_harness_day_count"] = 90
    stale_90_day_probe["proof_contract"]["harness_day_count"] = 90
    stale_90_day_errors = validate_phase7_readiness(stale_90_day_probe)

    stale_two_trade_probe = deepcopy(written)
    stale_two_trade_probe["phase7_weekly_proof_trade_target"] = 2
    stale_two_trade_probe["proof_contract"]["weekly_proof_trade_target"] = 2
    stale_two_trade_errors = validate_phase7_readiness(stale_two_trade_probe)

    forced_trade_probe = deepcopy(written)
    forced_trade_probe["phase7_no_forced_trades"] = False
    forced_trade_probe["phase7_weekly_target_applies_only_where_qualified_setups_exist"] = False
    forced_trade_probe["proof_contract"]["no_forced_trades"] = False
    forced_trade_errors = validate_phase7_readiness(forced_trade_probe)

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase7_readiness(proof_credit_probe)

    phase5_reuse_probe = deepcopy(written)
    phase5_reuse_probe["phase5_test_trades_count_for_phase7"] = True
    phase5_reuse_probe["phase5_test_trade_reuse_count"] = 1
    phase5_reuse_errors = validate_phase7_readiness(phase5_reuse_probe)

    execution_probe = deepcopy(written)
    execution_probe["phase7_proof_trade_execution_allowed"] = True
    execution_probe["phase7_proof_trade_submission_allowed"] = True
    execution_probe["proof_trade_created_count"] = 1
    execution_errors = validate_phase7_readiness(execution_probe)

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_probe["live_capital_enabled_count"] = 1
    live_capital_errors = validate_phase7_readiness(live_capital_probe)

    broker_probe = deepcopy(written)
    broker_probe["broker_post_allowed"] = True
    broker_probe["alpaca_post_called_count"] = 1
    broker_errors = validate_phase7_readiness(broker_probe)

    manual_override_probe = deepcopy(written)
    manual_override_probe["manual_trade_level_override_allowed"] = True
    manual_override_probe["manual_trade_level_override_count"] = 1
    manual_override_errors = validate_phase7_readiness(manual_override_probe)

    false_phase6_probe = deepcopy(written)
    false_phase6_probe["phase6_certified"] = False
    false_phase6_probe["phase6_exit_gate"] = False
    false_phase6_probe["blockers"] = []
    false_phase6_probe["blocker_count"] = 0
    false_phase6_errors = validate_phase7_readiness(false_phase6_probe)

    if validation_errors:
        errors.extend(validation_errors)
    if written["status"] != "ready_for_q7_1_artifact_schema":
        errors.append("phase7_readiness_not_ready")
    if written["readiness_state"] != "phase7_demo_proof_re_entry_gate_passed":
        errors.append("phase7_readiness_state_not_passed")
    if written["phase7_re_entry_gate_passed"] is not True:
        errors.append("phase7_re_entry_gate_not_passed")
    if written["phase6_certification_artifact_recorded"] is not True:
        errors.append("phase6_certification_artifact_not_recorded")
    if written["phase6_certification_validation_error_count"] != 0:
        errors.append("phase6_certification_validation_errors")
    if written["phase6_certification_status"] != "certified":
        errors.append("phase6_certification_not_certified")
    if written["phase6_certification_stage_status"] != "phase6_certified":
        errors.append("phase6_stage_status_not_certified")
    if written["phase6_certified"] is not True:
        errors.append("phase6_certified_not_true")
    if written["phase6_exit_gate"] is not True:
        errors.append("phase6_exit_gate_not_true")
    if written["phase7_demo_proof_planning_allowed"] is not True:
        errors.append("phase7_demo_proof_planning_not_allowed")
    if written["phase7_proof_credit_allowed"] is not False:
        errors.append("phase7_proof_credit_allowed")
    if written["phase5_test_trades_count_for_phase7"] is not False:
        errors.append("phase5_test_trades_count_for_phase7")
    if written["phase7_harness_day_count"] != PHASE7_HARNESS_DAY_COUNT:
        errors.append("phase7_harness_day_count_mismatch")
    if written["phase7_weekly_proof_trade_target"] != PHASE7_WEEKLY_PROOF_TRADE_TARGET:
        errors.append("phase7_weekly_trade_target_mismatch")
    if written["phase7_no_forced_trades"] is not True:
        errors.append("phase7_no_forced_trades_not_true")
    if written["phase7_weekly_target_applies_only_where_qualified_setups_exist"] is not True:
        errors.append("phase7_weekly_target_forces_trades")
    if written["phase7_mature_closed_trade_benchmark"] != PHASE7_MATURE_CLOSED_TRADE_BENCHMARK:
        errors.append("phase7_mature_benchmark_mismatch")
    if written["phase7_statistical_immaturity_allowed"] is not True:
        errors.append("phase7_statistical_immaturity_not_allowed")
    if written["phase7_harness_started"] is not False:
        errors.append("phase7_harness_started")
    if written["q7_1_artifact_schema_stage_allowed"] is not True:
        errors.append("q7_1_artifact_schema_stage_not_allowed")
    if written["phase7_controlled_stage_work_allowed"] is not True:
        errors.append("phase7_controlled_stage_work_not_allowed")
    if written["phase7_demo_proof_implementation_allowed"] is not False:
        errors.append("phase7_demo_proof_implementation_allowed")
    if written["phase7_proof_trade_execution_allowed"] is not False:
        errors.append("phase7_proof_trade_execution_allowed")
    if written["live_capital_enabled"] is not False:
        errors.append("live_capital_enabled")
    if written["manual_trade_level_override_allowed"] is not False:
        errors.append("manual_trade_level_override_allowed")
    if written["phase7_frozen_scope_count"] != 18:
        errors.append("phase7_scope_count_mismatch")
    if written["unsafe_write_counter_total"] != 0:
        errors.append("unsafe_write_counter_total_nonzero")
    if written["blocker_count"] != 0:
        errors.append("phase7_readiness_blockers_present")
    if written["event_log_written"] is not True:
        errors.append("event_log_not_written")
    if written["event_log_event_count"] != 1:
        errors.append("event_log_count_mismatch")
    if replay["total_events"] != 1:
        errors.append("event_log_replay_count_mismatch")

    if "phase7_readiness_harness_day_count_mismatch" not in stale_90_day_errors:
        errors.append("stale_90_day_probe_not_rejected")
    if "phase7_readiness_weekly_target_mismatch" not in stale_two_trade_errors:
        errors.append("stale_two_trade_probe_not_rejected")
    if "phase7_readiness_forced_trades_allowed" not in forced_trade_errors:
        errors.append("forced_trade_probe_not_rejected")
    if "phase7_proof_credit_allowed" not in proof_credit_errors:
        errors.append("proof_credit_probe_not_rejected")
    if "phase5_test_trades_count_for_phase7" not in phase5_reuse_errors:
        errors.append("phase5_reuse_probe_not_rejected")
    if (
        "phase7_readiness_authority_enabled:phase7_proof_trade_execution_allowed"
        not in execution_errors
    ):
        errors.append("execution_authority_probe_not_rejected")
    if "phase7_readiness_unsafe_count_nonzero:proof_trade_created_count" not in (
        execution_errors
    ):
        errors.append("execution_count_probe_not_rejected")
    if "phase7_readiness_authority_enabled:live_capital_enabled" not in live_capital_errors:
        errors.append("live_capital_authority_probe_not_rejected")
    if "phase7_readiness_unsafe_count_nonzero:live_capital_enabled_count" not in (
        live_capital_errors
    ):
        errors.append("live_capital_count_probe_not_rejected")
    if "phase7_readiness_authority_enabled:broker_post_allowed" not in broker_errors:
        errors.append("broker_authority_probe_not_rejected")
    if "phase7_readiness_unsafe_count_nonzero:alpaca_post_called_count" not in broker_errors:
        errors.append("broker_count_probe_not_rejected")
    if (
        "phase7_readiness_authority_enabled:manual_trade_level_override_allowed"
        not in manual_override_errors
    ):
        errors.append("manual_override_authority_probe_not_rejected")
    if "phase7_readiness_unsafe_count_nonzero:manual_trade_level_override_count" not in (
        manual_override_errors
    ):
        errors.append("manual_override_count_probe_not_rejected")
    if "phase7_readiness_passed_missing_true:phase6_certified" not in false_phase6_errors:
        errors.append("false_phase6_probe_not_rejected")

    print(f"phase7_readiness_status={written['status']}")
    print(f"phase7_readiness_schema_version={PHASE7_READINESS_SCHEMA_VERSION}")
    print(f"phase7_readiness_artifact_path={output_path}")
    print(f"phase7_readiness_history_path={history_path}")
    print(f"phase7_readiness_event_log_path={event_log_path}")
    print(f"phase7_readiness_state={written['readiness_state']}")
    print(f"phase7_readiness_re_entry_gate_passed={written['phase7_re_entry_gate_passed']}")
    print(f"phase7_readiness_phase6_certification_status={written['phase6_certification_status']}")
    print(f"phase7_readiness_phase6_certified={written['phase6_certified']}")
    print(f"phase7_readiness_phase6_exit_gate={written['phase6_exit_gate']}")
    print(
        "phase7_readiness_phase7_demo_proof_planning_allowed="
        f"{written['phase7_demo_proof_planning_allowed']}"
    )
    print(
        "phase7_readiness_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(
        "phase7_readiness_phase5_test_trades_count_for_phase7="
        f"{written['phase5_test_trades_count_for_phase7']}"
    )
    print(f"phase7_readiness_harness_day_count={written['phase7_harness_day_count']}")
    print(
        "phase7_readiness_consecutive_calendar_days_required="
        f"{written['phase7_consecutive_calendar_days_required']}"
    )
    print(
        "phase7_readiness_weekly_proof_trade_target="
        f"{written['phase7_weekly_proof_trade_target']}"
    )
    print(
        "phase7_readiness_weekly_target_where_qualified_setups_exist="
        f"{written['phase7_weekly_target_applies_only_where_qualified_setups_exist']}"
    )
    print(f"phase7_readiness_no_forced_trades={written['phase7_no_forced_trades']}")
    print(
        "phase7_readiness_mature_closed_trade_benchmark="
        f"{written['phase7_mature_closed_trade_benchmark']}"
    )
    print(
        "phase7_readiness_statistical_immaturity_allowed="
        f"{written['phase7_statistical_immaturity_allowed']}"
    )
    print(f"phase7_readiness_harness_started={written['phase7_harness_started']}")
    print(
        "phase7_readiness_q7_1_artifact_schema_stage_allowed="
        f"{written['q7_1_artifact_schema_stage_allowed']}"
    )
    print(
        "phase7_readiness_phase7_demo_proof_implementation_allowed="
        f"{written['phase7_demo_proof_implementation_allowed']}"
    )
    print(
        "phase7_readiness_phase7_proof_trade_execution_allowed="
        f"{written['phase7_proof_trade_execution_allowed']}"
    )
    print(f"phase7_readiness_live_capital_enabled={written['live_capital_enabled']}")
    print(
        "phase7_readiness_manual_trade_level_override_allowed="
        f"{written['manual_trade_level_override_allowed']}"
    )
    print(f"phase7_readiness_frozen_scope_count={written['phase7_frozen_scope_count']}")
    print(f"phase7_readiness_unsafe_write_counter_total={written['unsafe_write_counter_total']}")
    print(f"phase7_readiness_blocker_count={written['blocker_count']}")
    print(f"phase7_readiness_event_log_replay_total_events={replay['total_events']}")
    print(f"phase7_readiness_stale_90_day_probe_error_count={len(stale_90_day_errors)}")
    print(f"phase7_readiness_stale_two_trade_probe_error_count={len(stale_two_trade_errors)}")
    print(f"phase7_readiness_forced_trade_probe_error_count={len(forced_trade_errors)}")
    print(f"phase7_readiness_proof_credit_probe_error_count={len(proof_credit_errors)}")
    print(f"phase7_readiness_phase5_reuse_probe_error_count={len(phase5_reuse_errors)}")
    print(f"phase7_readiness_execution_probe_error_count={len(execution_errors)}")
    print(f"phase7_readiness_live_capital_probe_error_count={len(live_capital_errors)}")
    print(f"phase7_readiness_broker_probe_error_count={len(broker_errors)}")
    print(f"phase7_readiness_manual_override_probe_error_count={len(manual_override_errors)}")
    print(f"phase7_readiness_false_phase6_probe_error_count={len(false_phase6_errors)}")
    print(f"phase7_readiness_next_stage={written['recommended_next_stage']}")
    print("phase7_readiness_boundary=" + written["boundary"])

    if errors:
        for error in sorted(set(errors)):
            print(f"phase7_readiness_error={error}")
        print("phase7_readiness_check=failed")
        return 1

    print("phase7_readiness_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
