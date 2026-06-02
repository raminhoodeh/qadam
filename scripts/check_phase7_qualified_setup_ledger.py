#!/usr/bin/env python3
"""Validate Q7-3 Phase 7 Demo Proof qualified setup ledger."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase7_calendar_harness import (  # noqa: E402
    build_phase7_calendar_harness,
    validate_phase7_calendar_harness,
)
from orchestrator.phase7_qualified_setup_ledger import (  # noqa: E402
    PHASE7_QUALIFIED_SETUP_LEDGER_SCHEMA_VERSION,
    QUALIFICATION_GATE_KEYS,
    build_phase7_qualified_setup_ledger,
    phase7_qualified_setup_ledger_paths,
    validate_phase7_qualified_setup_ledger,
    write_phase7_qualified_setup_ledger,
)
from orchestrator.phase7_readiness import (  # noqa: E402
    PHASE7_HARNESS_DAY_COUNT,
    build_phase7_readiness,
    validate_phase7_readiness,
)


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = phase7_qualified_setup_ledger_paths(
        settings
    )
    if event_log_path.exists():
        event_log_path.unlink()

    readiness = build_phase7_readiness(settings=settings)
    readiness_errors = validate_phase7_readiness(readiness)
    calendar = build_phase7_calendar_harness(settings=settings, start_date="2026-05-25")
    calendar_errors = validate_phase7_calendar_harness(calendar)
    artifact = build_phase7_qualified_setup_ledger(settings=settings)
    output_path, history_path, event_log_path, written = write_phase7_qualified_setup_ledger(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase7_qualified_setup_ledger(written)
    replay = EventLog(event_log_path, echo=False).replay()
    runtime_copy = _read_json(output_path)

    missing_daily_probe = deepcopy(written)
    missing_daily_probe["daily_setup_decisions"] = missing_daily_probe[
        "daily_setup_decisions"
    ][:-1]
    missing_daily_errors = validate_phase7_qualified_setup_ledger(missing_daily_probe)

    missing_day_no_trade_probe = deepcopy(written)
    missing_day_no_trade_probe["daily_setup_decisions"][0][
        "no_trade_explanation_recorded"
    ] = False
    missing_day_no_trade_errors = validate_phase7_qualified_setup_ledger(
        missing_day_no_trade_probe
    )

    missing_week_no_trade_probe = deepcopy(written)
    missing_week_no_trade_probe["weekly_setup_summaries"][0][
        "no_trade_explanation_recorded"
    ] = False
    missing_week_no_trade_errors = validate_phase7_qualified_setup_ledger(
        missing_week_no_trade_probe
    )

    phase5_reuse_probe = deepcopy(written)
    phase5_reuse_probe["candidate_setup_records"][0]["qualified_setup"] = True
    phase5_reuse_probe["candidate_setup_records"][0][
        "phase5_lifecycle_counts_as_q7_proof"
    ] = True
    phase5_reuse_probe["phase5_test_trades_count_for_phase7"] = True
    phase5_reuse_probe["phase5_test_trade_reuse_count"] = 1
    phase5_reuse_errors = validate_phase7_qualified_setup_ledger(phase5_reuse_probe)

    supplemental_probe = deepcopy(written)
    supplemental_record = {
        "setup_record_id": "probe:supplemental-only-qualified",
        "source_phase": "Q7",
        "qualified_setup": True,
        "supplemental_only": True,
        "phase5_lifecycle_counts_as_q7_proof": False,
        "phase5_test_trade_counted_for_phase7": False,
        "proof_trade_created": False,
        "proof_credit_allowed": False,
        "canonical_source_quorum_passed": False,
        "all_required_gates_passed": True,
        "gate_results": [
            {"gate_key": gate_key, "status": "pass"}
            for gate_key in QUALIFICATION_GATE_KEYS
        ],
    }
    supplemental_probe["candidate_setup_records"].append(supplemental_record)
    supplemental_probe["candidate_setup_record_count"] += 1
    supplemental_errors = validate_phase7_qualified_setup_ledger(supplemental_probe)

    missing_gate_probe = deepcopy(written)
    missing_gate_record = {
        "setup_record_id": "probe:missing-gate-qualified",
        "source_phase": "Q7",
        "qualified_setup": True,
        "supplemental_only": False,
        "phase5_lifecycle_counts_as_q7_proof": False,
        "phase5_test_trade_counted_for_phase7": False,
        "proof_trade_created": False,
        "proof_credit_allowed": False,
        "canonical_source_quorum_passed": True,
        "all_required_gates_passed": True,
        "gate_results": [
            {"gate_key": gate_key, "status": "pass"}
            for gate_key in QUALIFICATION_GATE_KEYS[:-1]
        ],
    }
    missing_gate_probe["candidate_setup_records"].append(missing_gate_record)
    missing_gate_probe["candidate_setup_record_count"] += 1
    missing_gate_errors = validate_phase7_qualified_setup_ledger(missing_gate_probe)

    contract_probe = deepcopy(written)
    contract_probe["qualification_contract"]["supplemental_only_qualification_allowed"] = (
        True
    )
    contract_probe["qualification_contract"]["phase5_lifecycle_counts_as_q7_proof"] = (
        True
    )
    contract_errors = validate_phase7_qualified_setup_ledger(contract_probe)

    source_posture_probe = deepcopy(written)
    source_posture_probe["source_posture"]["yahoo_finance_role"] = "canonical_source"
    source_posture_probe["source_posture"][
        "preference_mcp_source_quorum_credit_allowed"
    ] = True
    source_posture_probe["source_posture"]["qctrl_role"] = "execution_truth"
    source_posture_errors = validate_phase7_qualified_setup_ledger(source_posture_probe)

    proof_trade_probe = deepcopy(written)
    proof_trade_probe["proof_trade_count"] = 1
    proof_trade_probe["proof_trade_created_count"] = 1
    proof_trade_probe["daily_setup_decisions"][0]["proof_trade_count"] = 1
    proof_trade_errors = validate_phase7_qualified_setup_ledger(proof_trade_probe)

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["authority_ledger"]["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase7_qualified_setup_ledger(proof_credit_probe)

    broker_probe = deepcopy(written)
    broker_probe["broker_post_allowed"] = True
    broker_probe["authority_ledger"]["broker_post_allowed"] = True
    broker_probe["broker_post_called_count"] = 1
    broker_probe["live_endpoint_allowed"] = True
    broker_probe["authority_ledger"]["live_endpoint_allowed"] = True
    broker_errors = validate_phase7_qualified_setup_ledger(broker_probe)

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_probe["authority_ledger"]["live_capital_enabled"] = True
    live_capital_probe["live_capital_enabled_count"] = 1
    live_capital_errors = validate_phase7_qualified_setup_ledger(live_capital_probe)

    manual_override_probe = deepcopy(written)
    manual_override_probe["manual_trade_level_override_allowed"] = True
    manual_override_probe["authority_ledger"][
        "manual_trade_level_override_allowed"
    ] = True
    manual_override_probe["manual_trade_level_override_count"] = 1
    manual_override_errors = validate_phase7_qualified_setup_ledger(
        manual_override_probe
    )

    local_path_probe = deepcopy(written)
    local_path_probe["provenance"]["source_refs"] = [
        "/Users/raminhoodeh/Desktop/qadam/data/runtime/private.json"
    ]
    local_path_errors = validate_phase7_qualified_setup_ledger(local_path_probe)

    calendar_gate_probe = deepcopy(written)
    calendar_gate_probe["q7_3_qualified_setup_ledger_stage_allowed"] = False
    calendar_gate_errors = validate_phase7_qualified_setup_ledger(calendar_gate_probe)

    print(f"phase7_setup_ledger_status={written['status']}")
    print(f"phase7_setup_ledger_stage_status={written['stage_status']}")
    print(
        "phase7_setup_ledger_schema_version="
        f"{PHASE7_QUALIFIED_SETUP_LEDGER_SCHEMA_VERSION}"
    )
    print(f"phase7_setup_ledger_artifact_path={output_path}")
    print(f"phase7_setup_ledger_history_path={history_path}")
    print(f"phase7_setup_ledger_event_log_path={event_log_path}")
    print(f"phase7_setup_ledger_calendar_status={written['source_calendar_status']}")
    print(
        "phase7_setup_ledger_calendar_day_record_count="
        f"{written['calendar_day_record_count']}"
    )
    print(
        "phase7_setup_ledger_daily_setup_decision_count="
        f"{written['daily_setup_decision_count']}"
    )
    print(
        "phase7_setup_ledger_weekly_setup_summary_count="
        f"{written['weekly_setup_summary_count']}"
    )
    print(
        "phase7_setup_ledger_candidate_setup_record_count="
        f"{written['candidate_setup_record_count']}"
    )
    print(
        "phase7_setup_ledger_qualified_setup_record_count="
        f"{written['qualified_setup_record_count']}"
    )
    print(f"phase7_setup_ledger_eligible_setup_count={written['eligible_setup_count']}")
    print(f"phase7_setup_ledger_qualified_setup_count={written['qualified_setup_count']}")
    print(f"phase7_setup_ledger_blocked_setup_count={written['blocked_setup_count']}")
    print(f"phase7_setup_ledger_expired_setup_count={written['expired_setup_count']}")
    print(
        "phase7_setup_ledger_no_trade_day_explanation_count="
        f"{written['no_trade_day_explanation_count']}"
    )
    print(
        "phase7_setup_ledger_no_trade_week_explanation_count="
        f"{written['no_trade_week_explanation_count']}"
    )
    print(
        "phase7_setup_ledger_rejected_phase5_lifecycle_count="
        f"{written['rejected_phase5_lifecycle_count']}"
    )
    print(
        "phase7_setup_ledger_supplemental_only_qualification_allowed="
        f"{written['supplemental_only_qualification_allowed']}"
    )
    print(
        "phase7_setup_ledger_phase5_test_trades_count_for_phase7="
        f"{written['phase5_test_trades_count_for_phase7']}"
    )
    print(f"phase7_setup_ledger_proof_trade_count={written['proof_trade_count']}")
    print(
        "phase7_setup_ledger_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(f"phase7_setup_ledger_live_capital_enabled={written['live_capital_enabled']}")
    print(
        "phase7_setup_ledger_manual_trade_level_override_allowed="
        f"{written['manual_trade_level_override_allowed']}"
    )
    print(
        "phase7_setup_ledger_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(f"phase7_setup_ledger_blocker_count={written['blocker_count']}")
    print(f"phase7_setup_ledger_event_log_replay_total_events={replay['total_events']}")
    print(f"phase7_setup_ledger_readiness_error_count={len(readiness_errors)}")
    print(f"phase7_setup_ledger_calendar_error_count={len(calendar_errors)}")
    print(
        "phase7_setup_ledger_q7_4_weekly_cadence_tracker_stage_allowed="
        f"{written['q7_4_weekly_cadence_tracker_stage_allowed']}"
    )
    print(
        "phase7_setup_ledger_required_gate_count="
        f"{written['qualification_contract']['required_gate_count']}"
    )
    print(f"phase7_setup_ledger_missing_daily_probe_error_count={len(missing_daily_errors)}")
    print(
        "phase7_setup_ledger_missing_day_no_trade_probe_error_count="
        f"{len(missing_day_no_trade_errors)}"
    )
    print(
        "phase7_setup_ledger_missing_week_no_trade_probe_error_count="
        f"{len(missing_week_no_trade_errors)}"
    )
    print(f"phase7_setup_ledger_phase5_reuse_probe_error_count={len(phase5_reuse_errors)}")
    print(
        "phase7_setup_ledger_supplemental_probe_error_count="
        f"{len(supplemental_errors)}"
    )
    print(f"phase7_setup_ledger_missing_gate_probe_error_count={len(missing_gate_errors)}")
    print(f"phase7_setup_ledger_contract_probe_error_count={len(contract_errors)}")
    print(
        "phase7_setup_ledger_source_posture_probe_error_count="
        f"{len(source_posture_errors)}"
    )
    print(f"phase7_setup_ledger_proof_trade_probe_error_count={len(proof_trade_errors)}")
    print(f"phase7_setup_ledger_proof_credit_probe_error_count={len(proof_credit_errors)}")
    print(f"phase7_setup_ledger_broker_probe_error_count={len(broker_errors)}")
    print(f"phase7_setup_ledger_live_capital_probe_error_count={len(live_capital_errors)}")
    print(
        "phase7_setup_ledger_manual_override_probe_error_count="
        f"{len(manual_override_errors)}"
    )
    print(f"phase7_setup_ledger_local_path_probe_error_count={len(local_path_errors)}")
    print(f"phase7_setup_ledger_calendar_gate_probe_error_count={len(calendar_gate_errors)}")
    print(f"phase7_setup_ledger_next_stage={written['recommended_next_stage']}")
    print("phase7_setup_ledger_boundary=" + written["boundary"])

    if readiness_errors:
        errors.extend(readiness_errors)
    if calendar_errors:
        errors.extend(calendar_errors)
    if validation_errors:
        errors.extend(validation_errors)
    if runtime_copy.get("artifact_id") != written["artifact_id"]:
        errors.append("runtime_phase7_setup_ledger_not_written")
    has_qualified_setup = written["qualified_setup_count"] > 0
    expected_status = (
        "read_only_q7_setups_recorded"
        if has_qualified_setup
        else "read_only_no_q7_setups"
    )
    expected_stage_status = (
        "qualified_setup_ledger_recorded_with_q7_setups"
        if has_qualified_setup
        else "qualified_setup_ledger_recorded_no_q7_setup_window"
    )
    if written["status"] != expected_status:
        errors.append("phase7_setup_ledger_status_invalid")
    if written["stage_status"] != expected_stage_status:
        errors.append("phase7_setup_ledger_stage_status_invalid")
    if written["calendar_day_record_count"] != PHASE7_HARNESS_DAY_COUNT:
        errors.append("phase7_setup_ledger_calendar_day_count_mismatch")
    if written["daily_setup_decision_count"] != PHASE7_HARNESS_DAY_COUNT:
        errors.append("phase7_setup_ledger_daily_decision_count_mismatch")
    if written["weekly_setup_summary_count"] != 5:
        errors.append("phase7_setup_ledger_weekly_summary_count_mismatch")
    if written["candidate_setup_record_count"] < 1:
        errors.append("phase7_setup_ledger_candidate_records_missing")
    if has_qualified_setup:
        if written["qualified_setup_record_count"] != written["qualified_setup_count"]:
            errors.append("phase7_setup_ledger_qualified_record_count_mismatch")
        if written["eligible_setup_count"] != written["qualified_setup_count"]:
            errors.append("phase7_setup_ledger_eligible_count_mismatch")
        if written["target_proof_trade_count"] <= 0:
            errors.append("phase7_setup_ledger_target_count_missing")
    for count_key in (
        "expired_setup_count",
        "proof_trade_count",
        "closed_proof_trade_count",
        "unsafe_write_counter_total",
        "blocker_count",
    ):
        if written[count_key] != 0:
            errors.append(f"phase7_setup_ledger_count_nonzero:{count_key}")
    expected_no_trade_days = sum(
        1
        for day in written["daily_setup_decisions"]
        if day.get("no_trade_explanation_recorded") is True
    )
    expected_no_trade_weeks = sum(
        1
        for week in written["weekly_setup_summaries"]
        if week.get("no_trade_explanation_recorded") is True
    )
    if written["no_trade_day_explanation_count"] != expected_no_trade_days:
        errors.append("phase7_setup_ledger_no_trade_day_count_mismatch")
    if written["no_trade_week_explanation_count"] != expected_no_trade_weeks:
        errors.append("phase7_setup_ledger_no_trade_week_count_mismatch")
    if written["rejected_phase5_lifecycle_count"] < 1:
        errors.append("phase7_setup_ledger_phase5_rejection_missing")
    for flag_key in (
        "phase7_qualified_setup_creation_allowed",
        "phase7_test_mode_auto_approval_allowed",
        "phase7_proof_order_staging_allowed",
        "phase7_proof_trade_execution_allowed",
        "phase7_proof_credit_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "manual_trade_level_override_allowed",
    ):
        if written[flag_key] is not False:
            errors.append(f"phase7_setup_ledger_authority_enabled:{flag_key}")
    if written["event_log_written"] is not True:
        errors.append("phase7_setup_ledger_event_log_not_written")
    if replay["total_events"] != 1:
        errors.append("phase7_setup_ledger_event_log_replay_count_mismatch")
    if written["q7_4_weekly_cadence_tracker_stage_allowed"] is not True:
        errors.append("phase7_setup_ledger_q7_4_not_allowed")

    if "daily_setup_decision_count_mismatch" not in missing_daily_errors:
        errors.append("missing_daily_probe_not_rejected")
    if "daily_setup_no_trade_explanation_missing" not in missing_day_no_trade_errors:
        errors.append("missing_day_no_trade_probe_not_rejected")
    if "weekly_setup_no_trade_explanation_missing" not in missing_week_no_trade_errors:
        errors.append("missing_week_no_trade_probe_not_rejected")
    if "phase5_lifecycle_marked_qualified" not in phase5_reuse_errors:
        errors.append("phase5_reuse_qualified_probe_not_rejected")
    if "phase5_lifecycle_counts_as_q7_proof" not in phase5_reuse_errors:
        errors.append("phase5_reuse_contract_probe_not_rejected")
    if "qualified_setup_forbidden:phase5_test_trades_count_for_phase7" not in (
        phase5_reuse_errors
    ):
        errors.append("phase5_reuse_top_level_probe_not_rejected")
    if "supplemental_only_setup_marked_qualified" not in supplemental_errors:
        errors.append("supplemental_qualified_probe_not_rejected")
    if "qualified_setup_missing_canonical_source_quorum" not in supplemental_errors:
        errors.append("supplemental_canonical_probe_not_rejected")
    if "qualified_setup_missing_required_gate_pass" not in missing_gate_errors:
        errors.append("missing_gate_probe_not_rejected")
    if "qualification_contract_forbidden:supplemental_only_qualification_allowed" not in (
        contract_errors
    ):
        errors.append("contract_supplemental_probe_not_rejected")
    if "qualification_contract_forbidden:phase5_lifecycle_counts_as_q7_proof" not in (
        contract_errors
    ):
        errors.append("contract_phase5_probe_not_rejected")
    if "qualified_setup_yahoo_finance_role_invalid" not in source_posture_errors:
        errors.append("source_posture_yahoo_probe_not_rejected")
    if "qualified_setup_preference_quorum_credit_allowed" not in source_posture_errors:
        errors.append("source_posture_preference_probe_not_rejected")
    if "qualified_setup_qctrl_role_invalid" not in source_posture_errors:
        errors.append("source_posture_qctrl_probe_not_rejected")
    if "qualified_setup_count_nonzero:proof_trade_count" not in proof_trade_errors:
        errors.append("proof_trade_count_probe_not_rejected")
    if "qualified_setup_unsafe_count_nonzero:proof_trade_created_count" not in (
        proof_trade_errors
    ):
        errors.append("proof_trade_unsafe_probe_not_rejected")
    if "qualified_setup_authority_enabled:phase7_proof_credit_allowed" not in (
        proof_credit_errors
    ):
        errors.append("proof_credit_authority_probe_not_rejected")
    if "qualified_setup_unsafe_count_nonzero:phase7_proof_credit_allowed_count" not in (
        proof_credit_errors
    ):
        errors.append("proof_credit_counter_probe_not_rejected")
    if "qualified_setup_authority_enabled:broker_post_allowed" not in broker_errors:
        errors.append("broker_authority_probe_not_rejected")
    if "qualified_setup_authority_enabled:live_endpoint_allowed" not in broker_errors:
        errors.append("live_endpoint_authority_probe_not_rejected")
    if "qualified_setup_unsafe_count_nonzero:broker_post_called_count" not in (
        broker_errors
    ):
        errors.append("broker_counter_probe_not_rejected")
    if "qualified_setup_authority_enabled:live_capital_enabled" not in (
        live_capital_errors
    ):
        errors.append("live_capital_authority_probe_not_rejected")
    if "qualified_setup_unsafe_count_nonzero:live_capital_enabled_count" not in (
        live_capital_errors
    ):
        errors.append("live_capital_counter_probe_not_rejected")
    if "qualified_setup_authority_enabled:manual_trade_level_override_allowed" not in (
        manual_override_errors
    ):
        errors.append("manual_override_authority_probe_not_rejected")
    if "qualified_setup_unsafe_count_nonzero:manual_trade_level_override_count" not in (
        manual_override_errors
    ):
        errors.append("manual_override_counter_probe_not_rejected")
    if "qualified_setup_provenance_local_path_leak" not in local_path_errors:
        errors.append("local_path_probe_not_rejected")
    if "q7_3_qualified_setup_ledger_not_allowed" not in calendar_gate_errors:
        errors.append("calendar_gate_probe_not_rejected")

    if errors:
        for error in sorted(set(errors)):
            print(f"phase7_setup_ledger_error={error}")
        print("phase7_qualified_setup_ledger_check=failed")
        return 1

    print("phase7_qualified_setup_ledger_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
