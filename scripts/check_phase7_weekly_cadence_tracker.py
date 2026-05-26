#!/usr/bin/env python3
"""Validate Q7-4 Phase 7 Demo Proof weekly cadence tracker."""

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
from orchestrator.phase7_qualified_setup_ledger import (  # noqa: E402
    build_phase7_qualified_setup_ledger,
    validate_phase7_qualified_setup_ledger,
)
from orchestrator.phase7_readiness import (  # noqa: E402
    PHASE7_WEEKLY_PROOF_TRADE_TARGET,
    build_phase7_readiness,
    validate_phase7_readiness,
)
from orchestrator.phase7_weekly_cadence import (  # noqa: E402
    PHASE7_WEEKLY_CADENCE_SCHEMA_VERSION,
    build_phase7_weekly_cadence_tracker,
    phase7_weekly_cadence_paths,
    validate_phase7_weekly_cadence_tracker,
    write_phase7_weekly_cadence_tracker,
)


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = phase7_weekly_cadence_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    readiness = build_phase7_readiness(settings=settings)
    readiness_errors = validate_phase7_readiness(readiness)
    setup_ledger = build_phase7_qualified_setup_ledger(settings=settings)
    setup_ledger_errors = validate_phase7_qualified_setup_ledger(setup_ledger)
    artifact = build_phase7_weekly_cadence_tracker(settings=settings)
    output_path, history_path, event_log_path, written = write_phase7_weekly_cadence_tracker(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase7_weekly_cadence_tracker(written)
    replay = EventLog(event_log_path, echo=False).replay()
    runtime_copy = _read_json(output_path)

    missing_week_probe = deepcopy(written)
    missing_week_probe["weekly_cadence_records"] = missing_week_probe[
        "weekly_cadence_records"
    ][:-1]
    missing_week_errors = validate_phase7_weekly_cadence_tracker(missing_week_probe)

    stale_target_probe = deepcopy(written)
    stale_target_probe["weekly_cadence_records"][0]["target_proof_trade_count"] = (
        PHASE7_WEEKLY_PROOF_TRADE_TARGET
    )
    stale_target_errors = validate_phase7_weekly_cadence_tracker(stale_target_probe)

    forced_trade_probe = deepcopy(written)
    forced_trade_probe["cadence_policy"]["no_forced_trades"] = False
    forced_trade_probe["weekly_cadence_records"][0]["forced_trade_allowed"] = True
    forced_trade_errors = validate_phase7_weekly_cadence_tracker(forced_trade_probe)

    missed_setup_probe = deepcopy(written)
    missed_setup_probe["weekly_cadence_records"][0]["qualified_setup_count"] = 2
    missed_setup_probe["weekly_cadence_records"][0]["target_proof_trade_count"] = 2
    missed_setup_probe["weekly_cadence_records"][0]["missed_qualified_setup_count"] = 0
    missed_setup_probe["weekly_cadence_records"][0]["cadence_satisfied"] = True
    missed_setup_errors = validate_phase7_weekly_cadence_tracker(missed_setup_probe)

    missing_explanation_probe = deepcopy(written)
    missing_explanation_probe["weekly_cadence_records"][0][
        "no_trade_explanation_recorded"
    ] = False
    missing_explanation_probe["weekly_cadence_records"][0][
        "no_forced_trade_exception_recorded"
    ] = False
    missing_explanation_errors = validate_phase7_weekly_cadence_tracker(
        missing_explanation_probe
    )

    partial_week_probe = deepcopy(written)
    partial_week_probe["weekly_cadence_records"][4][
        "partial_week_trade_pressure_allowed"
    ] = True
    partial_week_probe["partial_week_trade_pressure_allowed"] = True
    partial_week_errors = validate_phase7_weekly_cadence_tracker(partial_week_probe)

    proof_trade_probe = deepcopy(written)
    proof_trade_probe["proof_trade_count"] = 1
    proof_trade_probe["proof_trade_created_count"] = 1
    proof_trade_probe["weekly_cadence_records"][0]["proof_trade_count"] = 1
    proof_trade_errors = validate_phase7_weekly_cadence_tracker(proof_trade_probe)

    auto_approval_probe = deepcopy(written)
    auto_approval_probe["phase7_test_mode_auto_approval_allowed"] = True
    auto_approval_probe["authority_ledger"]["phase7_test_mode_auto_approval_allowed"] = (
        True
    )
    auto_approval_errors = validate_phase7_weekly_cadence_tracker(auto_approval_probe)

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["authority_ledger"]["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase7_weekly_cadence_tracker(proof_credit_probe)

    broker_probe = deepcopy(written)
    broker_probe["broker_post_allowed"] = True
    broker_probe["authority_ledger"]["broker_post_allowed"] = True
    broker_probe["broker_post_called_count"] = 1
    broker_probe["live_endpoint_allowed"] = True
    broker_probe["authority_ledger"]["live_endpoint_allowed"] = True
    broker_errors = validate_phase7_weekly_cadence_tracker(broker_probe)

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_probe["authority_ledger"]["live_capital_enabled"] = True
    live_capital_probe["live_capital_enabled_count"] = 1
    live_capital_errors = validate_phase7_weekly_cadence_tracker(live_capital_probe)

    manual_override_probe = deepcopy(written)
    manual_override_probe["manual_trade_level_override_allowed"] = True
    manual_override_probe["authority_ledger"][
        "manual_trade_level_override_allowed"
    ] = True
    manual_override_probe["manual_trade_level_override_count"] = 1
    manual_override_errors = validate_phase7_weekly_cadence_tracker(
        manual_override_probe
    )

    phase5_reuse_probe = deepcopy(written)
    phase5_reuse_probe["phase5_test_trades_count_for_phase7"] = True
    phase5_reuse_probe["phase5_test_trade_reuse_count"] = 1
    phase5_reuse_probe["proof_contract"]["phase5_test_trade_reuse_allowed"] = True
    phase5_reuse_errors = validate_phase7_weekly_cadence_tracker(phase5_reuse_probe)

    source_posture_probe = deepcopy(written)
    source_posture_probe["source_posture"]["preference_mcp_source_quorum_credit_allowed"] = (
        True
    )
    source_posture_probe["source_posture"]["qctrl_role"] = "execution_truth"
    source_posture_errors = validate_phase7_weekly_cadence_tracker(source_posture_probe)

    local_path_probe = deepcopy(written)
    local_path_probe["provenance"]["source_refs"] = [
        "/Users/raminhoodeh/Desktop/qadam/data/runtime/private.json"
    ]
    local_path_errors = validate_phase7_weekly_cadence_tracker(local_path_probe)

    gate_probe = deepcopy(written)
    gate_probe["q7_4_weekly_cadence_tracker_stage_allowed"] = False
    gate_errors = validate_phase7_weekly_cadence_tracker(gate_probe)

    print(f"phase7_weekly_cadence_status={written['status']}")
    print(f"phase7_weekly_cadence_stage_status={written['stage_status']}")
    print(f"phase7_weekly_cadence_schema_version={PHASE7_WEEKLY_CADENCE_SCHEMA_VERSION}")
    print(f"phase7_weekly_cadence_artifact_path={output_path}")
    print(f"phase7_weekly_cadence_history_path={history_path}")
    print(f"phase7_weekly_cadence_event_log_path={event_log_path}")
    print(
        "phase7_weekly_cadence_source_setup_ledger_status="
        f"{written['source_setup_ledger_status']}"
    )
    print(
        "phase7_weekly_cadence_record_count="
        f"{written['weekly_cadence_record_count']}"
    )
    print(
        "phase7_weekly_cadence_satisfied_count="
        f"{written['weekly_cadence_satisfied_count']}"
    )
    print(
        "phase7_weekly_cadence_failed_count="
        f"{written['weekly_cadence_failed_count']}"
    )
    print(f"phase7_weekly_cadence_weekly_target_total={written['weekly_target_total']}")
    print(f"phase7_weekly_cadence_weekly_target_formula={written['weekly_target_formula']}")
    print(
        "phase7_weekly_cadence_weekly_proof_trade_target="
        f"{written['weekly_proof_trade_target']}"
    )
    print(f"phase7_weekly_cadence_qualified_setup_count={written['qualified_setup_count']}")
    print(f"phase7_weekly_cadence_target_proof_trade_count={written['target_proof_trade_count']}")
    print(f"phase7_weekly_cadence_proof_trade_count={written['proof_trade_count']}")
    print(
        "phase7_weekly_cadence_missed_qualified_setup_count="
        f"{written['missed_qualified_setup_count']}"
    )
    print(
        "phase7_weekly_cadence_no_forced_trade_exception_count="
        f"{written['no_forced_trade_exception_count']}"
    )
    print(
        "phase7_weekly_cadence_no_trade_week_explanation_count="
        f"{written['no_trade_week_explanation_count']}"
    )
    print(
        "phase7_weekly_cadence_partial_week_trade_pressure_allowed="
        f"{written['partial_week_trade_pressure_allowed']}"
    )
    print(
        "phase7_weekly_cadence_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(f"phase7_weekly_cadence_live_capital_enabled={written['live_capital_enabled']}")
    print(
        "phase7_weekly_cadence_manual_trade_level_override_allowed="
        f"{written['manual_trade_level_override_allowed']}"
    )
    print(
        "phase7_weekly_cadence_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(f"phase7_weekly_cadence_blocker_count={written['blocker_count']}")
    print(f"phase7_weekly_cadence_event_log_replay_total_events={replay['total_events']}")
    print(f"phase7_weekly_cadence_readiness_error_count={len(readiness_errors)}")
    print(f"phase7_weekly_cadence_setup_ledger_error_count={len(setup_ledger_errors)}")
    print(
        "phase7_weekly_cadence_q7_5_test_mode_auto_approval_router_stage_allowed="
        f"{written['q7_5_test_mode_auto_approval_router_stage_allowed']}"
    )
    print(f"phase7_weekly_cadence_missing_week_probe_error_count={len(missing_week_errors)}")
    print(f"phase7_weekly_cadence_stale_target_probe_error_count={len(stale_target_errors)}")
    print(f"phase7_weekly_cadence_forced_trade_probe_error_count={len(forced_trade_errors)}")
    print(f"phase7_weekly_cadence_missed_setup_probe_error_count={len(missed_setup_errors)}")
    print(
        "phase7_weekly_cadence_missing_explanation_probe_error_count="
        f"{len(missing_explanation_errors)}"
    )
    print(f"phase7_weekly_cadence_partial_week_probe_error_count={len(partial_week_errors)}")
    print(f"phase7_weekly_cadence_proof_trade_probe_error_count={len(proof_trade_errors)}")
    print(f"phase7_weekly_cadence_auto_approval_probe_error_count={len(auto_approval_errors)}")
    print(f"phase7_weekly_cadence_proof_credit_probe_error_count={len(proof_credit_errors)}")
    print(f"phase7_weekly_cadence_broker_probe_error_count={len(broker_errors)}")
    print(f"phase7_weekly_cadence_live_capital_probe_error_count={len(live_capital_errors)}")
    print(
        "phase7_weekly_cadence_manual_override_probe_error_count="
        f"{len(manual_override_errors)}"
    )
    print(f"phase7_weekly_cadence_phase5_reuse_probe_error_count={len(phase5_reuse_errors)}")
    print(
        "phase7_weekly_cadence_source_posture_probe_error_count="
        f"{len(source_posture_errors)}"
    )
    print(f"phase7_weekly_cadence_local_path_probe_error_count={len(local_path_errors)}")
    print(f"phase7_weekly_cadence_gate_probe_error_count={len(gate_errors)}")
    print(f"phase7_weekly_cadence_next_stage={written['recommended_next_stage']}")
    print("phase7_weekly_cadence_boundary=" + written["boundary"])

    if readiness_errors:
        errors.extend(readiness_errors)
    if setup_ledger_errors:
        errors.extend(setup_ledger_errors)
    if validation_errors:
        errors.extend(validation_errors)
    if runtime_copy.get("artifact_id") != written["artifact_id"]:
        errors.append("runtime_phase7_weekly_cadence_not_written")
    if written["status"] != "cadence_satisfied_no_q7_setups":
        errors.append("phase7_weekly_cadence_status_invalid")
    if written["stage_status"] != "weekly_cadence_recorded_no_qualified_setups":
        errors.append("phase7_weekly_cadence_stage_status_invalid")
    if written["weekly_cadence_record_count"] != 5:
        errors.append("phase7_weekly_cadence_record_count_mismatch")
    if written["weekly_cadence_satisfied_count"] != 5:
        errors.append("phase7_weekly_cadence_satisfied_count_mismatch")
    if written["weekly_cadence_failed_count"] != 0:
        errors.append("phase7_weekly_cadence_failed_count_nonzero")
    for count_key in (
        "weekly_target_total",
        "qualified_setup_count",
        "target_proof_trade_count",
        "proof_trade_count",
        "missed_qualified_setup_count",
        "unsafe_write_counter_total",
        "blocker_count",
    ):
        if written[count_key] != 0:
            errors.append(f"phase7_weekly_cadence_count_nonzero:{count_key}")
    if written["no_forced_trade_exception_count"] != 5:
        errors.append("phase7_weekly_cadence_no_forced_exception_count_mismatch")
    if written["no_trade_week_explanation_count"] != 5:
        errors.append("phase7_weekly_cadence_no_trade_week_count_mismatch")
    for flag_key in (
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
            errors.append(f"phase7_weekly_cadence_authority_enabled:{flag_key}")
    if written["event_log_written"] is not True:
        errors.append("phase7_weekly_cadence_event_log_not_written")
    if replay["total_events"] != 1:
        errors.append("phase7_weekly_cadence_event_log_replay_count_mismatch")
    if written["q7_5_test_mode_auto_approval_router_stage_allowed"] is not True:
        errors.append("phase7_weekly_cadence_q7_5_not_allowed")

    if "weekly_cadence_record_count_mismatch" not in missing_week_errors:
        errors.append("missing_week_probe_not_rejected")
    if "weekly_cadence_record_target_invalid" not in stale_target_errors:
        errors.append("stale_target_probe_not_rejected")
    if "weekly_cadence_policy_missing_true:no_forced_trades" not in forced_trade_errors:
        errors.append("forced_trade_policy_probe_not_rejected")
    if "weekly_cadence_forced_trade_allowed" not in forced_trade_errors:
        errors.append("forced_trade_record_probe_not_rejected")
    if "weekly_cadence_record_missed_count_invalid" not in missed_setup_errors:
        errors.append("missed_setup_count_probe_not_rejected")
    if "weekly_cadence_missed_setup_marked_satisfied" not in missed_setup_errors:
        errors.append("missed_setup_satisfied_probe_not_rejected")
    if "weekly_cadence_no_trade_explanation_missing" not in missing_explanation_errors:
        errors.append("missing_explanation_probe_not_rejected")
    if "weekly_cadence_no_forced_exception_missing" not in missing_explanation_errors:
        errors.append("missing_no_forced_exception_probe_not_rejected")
    if "weekly_cadence_partial_week_pressure_allowed" not in partial_week_errors:
        errors.append("partial_week_probe_not_rejected")
    if "weekly_cadence_count_nonzero:proof_trade_count" not in proof_trade_errors:
        errors.append("proof_trade_count_probe_not_rejected")
    if "weekly_cadence_unsafe_count_nonzero:proof_trade_created_count" not in (
        proof_trade_errors
    ):
        errors.append("proof_trade_unsafe_probe_not_rejected")
    if "weekly_cadence_authority_enabled:phase7_test_mode_auto_approval_allowed" not in (
        auto_approval_errors
    ):
        errors.append("auto_approval_authority_probe_not_rejected")
    if "weekly_cadence_authority_enabled:phase7_proof_credit_allowed" not in (
        proof_credit_errors
    ):
        errors.append("proof_credit_authority_probe_not_rejected")
    if "weekly_cadence_unsafe_count_nonzero:phase7_proof_credit_allowed_count" not in (
        proof_credit_errors
    ):
        errors.append("proof_credit_counter_probe_not_rejected")
    if "weekly_cadence_authority_enabled:broker_post_allowed" not in broker_errors:
        errors.append("broker_authority_probe_not_rejected")
    if "weekly_cadence_authority_enabled:live_endpoint_allowed" not in broker_errors:
        errors.append("live_endpoint_authority_probe_not_rejected")
    if "weekly_cadence_unsafe_count_nonzero:broker_post_called_count" not in (
        broker_errors
    ):
        errors.append("broker_counter_probe_not_rejected")
    if "weekly_cadence_authority_enabled:live_capital_enabled" not in (
        live_capital_errors
    ):
        errors.append("live_capital_authority_probe_not_rejected")
    if "weekly_cadence_unsafe_count_nonzero:live_capital_enabled_count" not in (
        live_capital_errors
    ):
        errors.append("live_capital_counter_probe_not_rejected")
    if "weekly_cadence_authority_enabled:manual_trade_level_override_allowed" not in (
        manual_override_errors
    ):
        errors.append("manual_override_authority_probe_not_rejected")
    if "weekly_cadence_unsafe_count_nonzero:manual_trade_level_override_count" not in (
        manual_override_errors
    ):
        errors.append("manual_override_counter_probe_not_rejected")
    if "weekly_cadence_forbidden:phase5_test_trades_count_for_phase7" not in (
        phase5_reuse_errors
    ):
        errors.append("phase5_reuse_probe_not_rejected")
    if "weekly_cadence_proof_contract_phase5_reuse_allowed" not in phase5_reuse_errors:
        errors.append("phase5_reuse_contract_probe_not_rejected")
    if "weekly_cadence_preference_quorum_credit_allowed" not in source_posture_errors:
        errors.append("source_posture_preference_probe_not_rejected")
    if "weekly_cadence_qctrl_role_invalid" not in source_posture_errors:
        errors.append("source_posture_qctrl_probe_not_rejected")
    if "weekly_cadence_provenance_local_path_leak" not in local_path_errors:
        errors.append("local_path_probe_not_rejected")
    if "q7_4_weekly_cadence_tracker_not_allowed" not in gate_errors:
        errors.append("gate_probe_not_rejected")

    if errors:
        for error in sorted(set(errors)):
            print(f"phase7_weekly_cadence_error={error}")
        print("phase7_weekly_cadence_tracker_check=failed")
        return 1

    print("phase7_weekly_cadence_tracker_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
