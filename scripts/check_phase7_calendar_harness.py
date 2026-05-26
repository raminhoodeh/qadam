#!/usr/bin/env python3
"""Validate Q7-2 Phase 7 Demo Proof 30-day calendar harness."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase7_artifacts import (  # noqa: E402
    build_phase7_sample_artifacts,
    phase7_artifact_bundle_summary,
)
from orchestrator.phase7_calendar_harness import (  # noqa: E402
    PHASE7_CALENDAR_HARNESS_SCHEMA_VERSION,
    PROOF_WEEK_RANGES,
    build_phase7_calendar_harness,
    phase7_calendar_harness_paths,
    validate_phase7_calendar_harness,
    write_phase7_calendar_harness,
)
from orchestrator.phase7_readiness import (  # noqa: E402
    PHASE7_HARNESS_DAY_COUNT,
    PHASE7_WEEKLY_PROOF_TRADE_TARGET,
    build_phase7_readiness,
    validate_phase7_readiness,
)


CHECK_START_DATE = date(2026, 5, 25)


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = phase7_calendar_harness_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    readiness = build_phase7_readiness(settings=settings)
    readiness_errors = validate_phase7_readiness(readiness)
    schema_summary = phase7_artifact_bundle_summary(build_phase7_sample_artifacts())
    artifact = build_phase7_calendar_harness(
        settings=settings,
        start_date=CHECK_START_DATE,
    )
    output_path, history_path, event_log_path, written = write_phase7_calendar_harness(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase7_calendar_harness(written)
    replay = EventLog(event_log_path, echo=False).replay()
    runtime_copy = _read_json(output_path)

    missing_day_probe = deepcopy(written)
    missing_day_probe["proof_calendar_days"] = missing_day_probe["proof_calendar_days"][:-1]
    missing_day_errors = validate_phase7_calendar_harness(missing_day_probe)

    non_consecutive_probe = deepcopy(written)
    non_consecutive_probe["proof_calendar_days"][9]["calendar_date"] = "2026-06-04"
    non_consecutive_errors = validate_phase7_calendar_harness(non_consecutive_probe)

    bad_week_mapping_probe = deepcopy(written)
    bad_week_mapping_probe["proof_calendar_days"][28]["proof_week_number"] = 4
    bad_week_mapping_errors = validate_phase7_calendar_harness(bad_week_mapping_probe)

    partial_week_probe = deepcopy(written)
    partial_week_probe["proof_weeks"][4]["partial_week_trade_pressure_allowed"] = True
    partial_week_errors = validate_phase7_calendar_harness(partial_week_probe)

    forced_trade_probe = deepcopy(written)
    forced_trade_probe["no_forced_trades"] = False
    forced_trade_probe["proof_weeks"][0]["forced_trade_allowed"] = True
    forced_trade_probe["proof_calendar_days"][0]["forced_trade_allowed"] = True
    forced_trade_errors = validate_phase7_calendar_harness(forced_trade_probe)

    harness_start_probe = deepcopy(written)
    harness_start_probe["calendar_harness_started"] = True
    harness_start_probe["harness_started"] = True
    harness_start_probe["phase7_harness_start_allowed"] = True
    harness_start_probe["authority_ledger"]["phase7_harness_start_allowed"] = True
    harness_start_errors = validate_phase7_calendar_harness(harness_start_probe)

    proof_trade_probe = deepcopy(written)
    proof_trade_probe["proof_trade_count"] = 1
    proof_trade_probe["proof_trade_created_count"] = 1
    proof_trade_probe["proof_calendar_days"][0]["proof_trade_count"] = 1
    proof_trade_probe["proof_weeks"][0]["proof_trade_count"] = 1
    proof_trade_errors = validate_phase7_calendar_harness(proof_trade_probe)

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["authority_ledger"]["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase7_calendar_harness(proof_credit_probe)

    broker_probe = deepcopy(written)
    broker_probe["broker_post_allowed"] = True
    broker_probe["authority_ledger"]["broker_post_allowed"] = True
    broker_probe["broker_post_called_count"] = 1
    broker_probe["live_endpoint_allowed"] = True
    broker_probe["authority_ledger"]["live_endpoint_allowed"] = True
    broker_errors = validate_phase7_calendar_harness(broker_probe)

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_probe["authority_ledger"]["live_capital_enabled"] = True
    live_capital_probe["live_capital_enabled_count"] = 1
    live_capital_errors = validate_phase7_calendar_harness(live_capital_probe)

    phase5_reuse_probe = deepcopy(written)
    phase5_reuse_probe["phase5_test_trades_count_for_phase7"] = True
    phase5_reuse_probe["phase5_test_trade_reuse_count"] = 1
    phase5_reuse_probe["proof_contract"]["phase5_test_trade_reuse_allowed"] = True
    phase5_reuse_errors = validate_phase7_calendar_harness(phase5_reuse_probe)

    source_posture_probe = deepcopy(written)
    source_posture_probe["source_posture"]["preference_mcp_source_quorum_credit_allowed"] = (
        True
    )
    source_posture_probe["source_posture"]["qctrl_role"] = "execution_truth"
    source_posture_errors = validate_phase7_calendar_harness(source_posture_probe)

    local_path_probe = deepcopy(written)
    local_path_probe["provenance"]["source_refs"] = [
        "/Users/raminhoodeh/Desktop/qadam/data/runtime/phase7_calendar_harness.json"
    ]
    local_path_errors = validate_phase7_calendar_harness(local_path_probe)

    policy_probe = deepcopy(written)
    policy_probe["calendar_policy"]["proof_trade_creation_allowed"] = True
    policy_errors = validate_phase7_calendar_harness(policy_probe)

    q7_1_probe = deepcopy(written)
    q7_1_probe["q7_1_artifact_schema_passed"] = False
    q7_1_errors = validate_phase7_calendar_harness(q7_1_probe)

    print(f"phase7_calendar_status={written['status']}")
    print(f"phase7_calendar_stage_status={written['stage_status']}")
    print(f"phase7_calendar_schema_version={PHASE7_CALENDAR_HARNESS_SCHEMA_VERSION}")
    print(f"phase7_calendar_artifact_path={output_path}")
    print(f"phase7_calendar_history_path={history_path}")
    print(f"phase7_calendar_event_log_path={event_log_path}")
    print(f"phase7_calendar_scheduled_start_date={written['scheduled_start_date']}")
    print(f"phase7_calendar_scheduled_end_date={written['scheduled_end_date']}")
    print(f"phase7_calendar_day_record_count={written['calendar_day_record_count']}")
    print(f"phase7_calendar_record_present_count={written['calendar_record_present_count']}")
    print(
        "phase7_calendar_consecutive_calendar_days_validated="
        f"{written['consecutive_calendar_days_validated']}"
    )
    print(f"phase7_calendar_proof_week_count={written['proof_week_count']}")
    print(f"phase7_calendar_full_proof_week_count={written['full_proof_week_count']}")
    print(f"phase7_calendar_partial_proof_week_count={written['partial_proof_week_count']}")
    print(
        "phase7_calendar_partial_week_trade_pressure_allowed="
        f"{written['partial_week_trade_pressure_allowed']}"
    )
    print(f"phase7_calendar_weekly_proof_trade_target={written['weekly_proof_trade_target']}")
    print(f"phase7_calendar_weekly_target_formula={written['weekly_target_formula']}")
    print(f"phase7_calendar_no_forced_trades={written['no_forced_trades']}")
    print(f"phase7_calendar_harness_started={written['calendar_harness_started']}")
    print(f"phase7_calendar_phase7_demo_day_count={written['phase7_demo_day_count']}")
    print(f"phase7_calendar_qualified_setup_count={written['qualified_setup_count']}")
    print(f"phase7_calendar_proof_trade_count={written['proof_trade_count']}")
    print(f"phase7_calendar_closed_proof_trade_count={written['closed_proof_trade_count']}")
    print(
        "phase7_calendar_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(f"phase7_calendar_live_capital_enabled={written['live_capital_enabled']}")
    print(
        "phase7_calendar_manual_trade_level_override_allowed="
        f"{written['manual_trade_level_override_allowed']}"
    )
    print(f"phase7_calendar_unsafe_write_counter_total={written['unsafe_write_counter_total']}")
    print(f"phase7_calendar_blocker_count={written['blocker_count']}")
    print(f"phase7_calendar_event_log_replay_total_events={replay['total_events']}")
    print(f"phase7_calendar_readiness_error_count={len(readiness_errors)}")
    print(f"phase7_calendar_q7_1_schema_status={schema_summary['status']}")
    print(
        "phase7_calendar_q7_3_qualified_setup_ledger_stage_allowed="
        f"{written['q7_3_qualified_setup_ledger_stage_allowed']}"
    )
    print(f"phase7_calendar_proof_week_range_count={len(PROOF_WEEK_RANGES)}")
    print(f"phase7_calendar_missing_day_probe_error_count={len(missing_day_errors)}")
    print(
        "phase7_calendar_non_consecutive_probe_error_count="
        f"{len(non_consecutive_errors)}"
    )
    print(
        "phase7_calendar_bad_week_mapping_probe_error_count="
        f"{len(bad_week_mapping_errors)}"
    )
    print(f"phase7_calendar_partial_week_probe_error_count={len(partial_week_errors)}")
    print(f"phase7_calendar_forced_trade_probe_error_count={len(forced_trade_errors)}")
    print(f"phase7_calendar_harness_start_probe_error_count={len(harness_start_errors)}")
    print(f"phase7_calendar_proof_trade_probe_error_count={len(proof_trade_errors)}")
    print(f"phase7_calendar_proof_credit_probe_error_count={len(proof_credit_errors)}")
    print(f"phase7_calendar_broker_probe_error_count={len(broker_errors)}")
    print(f"phase7_calendar_live_capital_probe_error_count={len(live_capital_errors)}")
    print(f"phase7_calendar_phase5_reuse_probe_error_count={len(phase5_reuse_errors)}")
    print(
        "phase7_calendar_source_posture_probe_error_count="
        f"{len(source_posture_errors)}"
    )
    print(f"phase7_calendar_local_path_probe_error_count={len(local_path_errors)}")
    print(f"phase7_calendar_policy_probe_error_count={len(policy_errors)}")
    print(f"phase7_calendar_q7_1_probe_error_count={len(q7_1_errors)}")
    print(f"phase7_calendar_next_stage={written['recommended_next_stage']}")
    print("phase7_calendar_boundary=" + written["boundary"])

    if readiness_errors:
        errors.extend(readiness_errors)
    if schema_summary["status"] != "ok":
        errors.append("q7_1_schema_not_valid")
    if validation_errors:
        errors.extend(validation_errors)
    if runtime_copy.get("artifact_id") != written["artifact_id"]:
        errors.append("runtime_phase7_calendar_not_written")
    if written["status"] != "scheduled":
        errors.append("phase7_calendar_not_scheduled")
    if written["stage_status"] != "phase7_calendar_harness_scheduled":
        errors.append("phase7_calendar_stage_status_not_scheduled")
    if written["calendar_day_record_count"] != PHASE7_HARNESS_DAY_COUNT:
        errors.append("phase7_calendar_day_count_mismatch")
    if written["calendar_record_present_count"] != PHASE7_HARNESS_DAY_COUNT:
        errors.append("phase7_calendar_present_count_mismatch")
    if written["consecutive_calendar_days_validated"] is not True:
        errors.append("phase7_calendar_consecutive_days_not_validated")
    if written["proof_week_count"] != len(PROOF_WEEK_RANGES):
        errors.append("phase7_calendar_proof_week_count_mismatch")
    if written["full_proof_week_count"] != 4:
        errors.append("phase7_calendar_full_week_count_mismatch")
    if written["partial_proof_week_count"] != 1:
        errors.append("phase7_calendar_partial_week_count_mismatch")
    if written["partial_week_trade_pressure_allowed"] is not False:
        errors.append("phase7_calendar_partial_week_trade_pressure")
    if written["weekly_proof_trade_target"] != PHASE7_WEEKLY_PROOF_TRADE_TARGET:
        errors.append("phase7_calendar_weekly_target_mismatch")
    if written["weekly_target_formula"] != "min(3, qualified_setup_count)":
        errors.append("phase7_calendar_weekly_formula_mismatch")
    if written["no_forced_trades"] is not True:
        errors.append("phase7_calendar_forced_trades_allowed")
    if written["calendar_harness_started"] is not False:
        errors.append("phase7_calendar_harness_started")
    for count_key in (
        "phase7_demo_day_count",
        "qualified_setup_count",
        "proof_trade_count",
        "closed_proof_trade_count",
        "postmortem_due_count",
        "unsafe_write_counter_total",
        "blocker_count",
    ):
        if written[count_key] != 0:
            errors.append(f"phase7_calendar_count_nonzero:{count_key}")
    for flag_key in (
        "phase7_harness_start_allowed",
        "phase7_qualified_setup_creation_allowed",
        "phase7_proof_trade_execution_allowed",
        "phase7_proof_credit_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "manual_trade_level_override_allowed",
    ):
        if written[flag_key] is not False:
            errors.append(f"phase7_calendar_authority_enabled:{flag_key}")
    if written["event_log_written"] is not True:
        errors.append("phase7_calendar_event_log_not_written")
    if replay["total_events"] != 1:
        errors.append("phase7_calendar_event_log_replay_count_mismatch")
    if written["q7_3_qualified_setup_ledger_stage_allowed"] is not True:
        errors.append("phase7_calendar_q7_3_not_allowed")

    if "calendar_day_count_mismatch" not in missing_day_errors:
        errors.append("missing_day_probe_not_rejected")
    if "calendar_dates_not_consecutive" not in non_consecutive_errors:
        errors.append("non_consecutive_probe_not_rejected")
    if "calendar_day_week_mapping_invalid" not in bad_week_mapping_errors:
        errors.append("bad_week_mapping_probe_not_rejected")
    if "partial_week_trade_pressure_allowed" not in partial_week_errors:
        errors.append("partial_week_probe_not_rejected")
    if "forced_trades_allowed" not in forced_trade_errors:
        errors.append("forced_trade_top_level_probe_not_rejected")
    if "proof_week_forced_trade_allowed" not in forced_trade_errors:
        errors.append("forced_trade_week_probe_not_rejected")
    if "calendar_day_forbidden:forced_trade_allowed" not in forced_trade_errors:
        errors.append("forced_trade_day_probe_not_rejected")
    if "phase7_calendar_harness_started" not in harness_start_errors:
        errors.append("harness_start_probe_not_rejected")
    if "phase7_calendar_authority_enabled:phase7_harness_start_allowed" not in (
        harness_start_errors
    ):
        errors.append("harness_start_authority_probe_not_rejected")
    if "phase7_calendar_premature_count:proof_trade_count" not in proof_trade_errors:
        errors.append("proof_trade_count_probe_not_rejected")
    if "phase7_calendar_unsafe_count_nonzero:proof_trade_created_count" not in (
        proof_trade_errors
    ):
        errors.append("proof_trade_unsafe_probe_not_rejected")
    if "phase7_calendar_authority_enabled:phase7_proof_credit_allowed" not in (
        proof_credit_errors
    ):
        errors.append("proof_credit_authority_probe_not_rejected")
    if "phase7_calendar_unsafe_count_nonzero:phase7_proof_credit_allowed_count" not in (
        proof_credit_errors
    ):
        errors.append("proof_credit_counter_probe_not_rejected")
    if "phase7_calendar_authority_enabled:broker_post_allowed" not in broker_errors:
        errors.append("broker_authority_probe_not_rejected")
    if "phase7_calendar_authority_enabled:live_endpoint_allowed" not in broker_errors:
        errors.append("live_endpoint_authority_probe_not_rejected")
    if "phase7_calendar_unsafe_count_nonzero:broker_post_called_count" not in (
        broker_errors
    ):
        errors.append("broker_counter_probe_not_rejected")
    if "phase7_calendar_authority_enabled:live_capital_enabled" not in (
        live_capital_errors
    ):
        errors.append("live_capital_authority_probe_not_rejected")
    if "phase7_calendar_unsafe_count_nonzero:live_capital_enabled_count" not in (
        live_capital_errors
    ):
        errors.append("live_capital_counter_probe_not_rejected")
    if "phase5_test_trades_count_for_phase7" not in phase5_reuse_errors:
        errors.append("phase5_reuse_probe_not_rejected")
    if "proof_contract_phase5_reuse_allowed" not in phase5_reuse_errors:
        errors.append("phase5_reuse_contract_probe_not_rejected")
    if "source_posture_preference_quorum_credit_allowed" not in source_posture_errors:
        errors.append("source_posture_preference_probe_not_rejected")
    if "source_posture_qctrl_role_invalid" not in source_posture_errors:
        errors.append("source_posture_qctrl_probe_not_rejected")
    if "provenance_local_path_leak" not in local_path_errors:
        errors.append("local_path_probe_not_rejected")
    if "calendar_policy_proof_trade_creation_allowed" not in policy_errors:
        errors.append("policy_probe_not_rejected")
    if "phase7_calendar_q7_1_schema_not_passed" not in q7_1_errors:
        errors.append("q7_1_schema_probe_not_rejected")

    if errors:
        for error in sorted(set(errors)):
            print(f"phase7_calendar_error={error}")
        print("phase7_calendar_harness_check=failed")
        return 1

    print("phase7_calendar_harness_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
