#!/usr/bin/env python3
"""Validate Q7-5 Phase 7 Demo Proof test-mode auto-approval router."""

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
    QUALIFICATION_GATE_KEYS,
    build_phase7_qualified_setup_ledger,
    validate_phase7_qualified_setup_ledger,
)
from orchestrator.phase7_readiness import (  # noqa: E402
    build_phase7_readiness,
    validate_phase7_readiness,
)
from orchestrator.phase7_test_mode_auto_approval import (  # noqa: E402
    PHASE7_TEST_MODE_AUTO_APPROVAL_SCHEMA_VERSION,
    build_phase7_test_mode_auto_approval_router,
    phase7_test_mode_auto_approval_paths,
    validate_phase7_test_mode_auto_approval_router,
    write_phase7_test_mode_auto_approval_router,
)
from orchestrator.phase7_weekly_cadence import (  # noqa: E402
    build_phase7_weekly_cadence_tracker,
    validate_phase7_weekly_cadence_tracker,
)


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _synthetic_auto_approved_record() -> dict[str, object]:
    return {
        "decision_id": "probe:auto-approved:q7-qualified-setup",
        "artifact_type": "auto_approval_decision",
        "setup_record_id": "probe:q7-qualified-setup",
        "source_phase": "Q7",
        "source_artifact_ref": "data/runtime/phase7_qualified_setup_ledger.json",
        "strategy_family_key": "probe_strategy",
        "instrument": "probe_instrument",
        "approval_mode": "test_mode_auto_approval",
        "decision_state": "auto_approved",
        "auto_approved": True,
        "auto_approval_blocked": False,
        "qualified_setup": True,
        "eligible_setup": True,
        "source_quorum_passed": True,
        "all_required_gates_passed": True,
        "passed_required_gate_count": len(QUALIFICATION_GATE_KEYS),
        "required_gate_count": len(QUALIFICATION_GATE_KEYS),
        "risk_gate_passed": True,
        "execution_policy_gate_passed": True,
        "kill_switches_clear": True,
        "venue_available": True,
        "broker_paper_ready": True,
        "gate_results": [
            {"gate_key": gate_key, "status": "pass"}
            for gate_key in QUALIFICATION_GATE_KEYS
        ],
        "rejection_reasons": [],
        "defer_reasons": [],
        "expiry_reasons": [],
        "fund_manager_trade_level_approval_required": False,
        "fund_manager_trade_level_approval_recorded": False,
        "manual_trade_level_override_attempted": False,
        "manual_attempt_contaminates_sample": True,
        "governance_feedback_channel": "future_policy_only",
        "strategy_toggle_channel": "future_policy_only",
        "kill_switch_change_channel": "future_policy_only",
        "proof_order_staging_allowed": False,
        "proof_trade_creation_allowed": False,
        "proof_credit_allowed": False,
        "broker_post_allowed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
    }


def _append_probe_approval(artifact: dict[str, object]) -> dict[str, object]:
    probe = deepcopy(artifact)
    records = list(probe["approval_decision_records"])
    records.append(_synthetic_auto_approved_record())
    probe["approval_decision_records"] = records
    probe["approval_decision_record_count"] = len(records)
    probe["qualified_setup_count"] = 1
    probe["qualified_setup_decision_count"] = 1
    probe["auto_approved_setup_count"] = 1
    return probe


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = phase7_test_mode_auto_approval_paths(
        settings
    )
    if event_log_path.exists():
        event_log_path.unlink()

    readiness = build_phase7_readiness(settings=settings)
    readiness_errors = validate_phase7_readiness(readiness)
    setup_ledger = build_phase7_qualified_setup_ledger(settings=settings)
    setup_ledger_errors = validate_phase7_qualified_setup_ledger(setup_ledger)
    weekly_cadence = build_phase7_weekly_cadence_tracker(settings=settings)
    weekly_cadence_errors = validate_phase7_weekly_cadence_tracker(weekly_cadence)
    artifact = build_phase7_test_mode_auto_approval_router(settings=settings)
    output_path, history_path, event_log_path, written = (
        write_phase7_test_mode_auto_approval_router(
            artifact,
            settings=settings,
            record_event=True,
            event_log_path=event_log_path,
        )
    )
    validation_errors = validate_phase7_test_mode_auto_approval_router(written)
    replay = EventLog(event_log_path, echo=False).replay()
    runtime_copy = _read_json(output_path)

    gate_probe = deepcopy(written)
    gate_probe["q7_5_test_mode_auto_approval_router_stage_allowed"] = False
    gate_errors = validate_phase7_test_mode_auto_approval_router(gate_probe)

    manual_approval_probe = deepcopy(written)
    manual_approval_probe["fund_manager_trade_level_approval_count"] = 1
    manual_approval_probe["manual_trade_level_approval_count"] = 1
    manual_approval_errors = validate_phase7_test_mode_auto_approval_router(
        manual_approval_probe
    )

    contaminated_probe = deepcopy(written)
    contaminated_probe["sample_contaminated"] = True
    contaminated_probe["contamination_reasons"] = ["manual_trade_level_approval_attempt"]
    contaminated_errors = validate_phase7_test_mode_auto_approval_router(
        contaminated_probe
    )

    risk_bypass_probe = _append_probe_approval(written)
    risk_bypass_probe["approval_decision_records"][-1]["risk_gate_passed"] = False
    risk_bypass_errors = validate_phase7_test_mode_auto_approval_router(
        risk_bypass_probe
    )

    kill_switch_probe = _append_probe_approval(written)
    kill_switch_probe["approval_decision_records"][-1]["kill_switches_clear"] = False
    kill_switch_errors = validate_phase7_test_mode_auto_approval_router(
        kill_switch_probe
    )

    source_quorum_probe = _append_probe_approval(written)
    source_quorum_probe["approval_decision_records"][-1]["source_quorum_passed"] = False
    source_quorum_errors = validate_phase7_test_mode_auto_approval_router(
        source_quorum_probe
    )

    phase5_approval_probe = _append_probe_approval(written)
    phase5_approval_probe["approval_decision_records"][-1]["source_phase"] = "Q5"
    phase5_approval_errors = validate_phase7_test_mode_auto_approval_router(
        phase5_approval_probe
    )

    staging_probe = deepcopy(written)
    staging_probe["phase7_proof_order_staging_allowed"] = True
    staging_probe["authority_ledger"]["phase7_proof_order_staging_allowed"] = True
    staging_errors = validate_phase7_test_mode_auto_approval_router(staging_probe)

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["authority_ledger"]["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase7_test_mode_auto_approval_router(
        proof_credit_probe
    )

    broker_probe = deepcopy(written)
    broker_probe["broker_post_allowed"] = True
    broker_probe["authority_ledger"]["broker_post_allowed"] = True
    broker_probe["broker_post_called_count"] = 1
    broker_probe["live_endpoint_allowed"] = True
    broker_probe["authority_ledger"]["live_endpoint_allowed"] = True
    broker_errors = validate_phase7_test_mode_auto_approval_router(broker_probe)

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_probe["authority_ledger"]["live_capital_enabled"] = True
    live_capital_probe["live_capital_enabled_count"] = 1
    live_capital_errors = validate_phase7_test_mode_auto_approval_router(
        live_capital_probe
    )

    manual_override_probe = deepcopy(written)
    manual_override_probe["manual_trade_level_override_allowed"] = True
    manual_override_probe["authority_ledger"][
        "manual_trade_level_override_allowed"
    ] = True
    manual_override_probe["manual_trade_level_override_count"] = 1
    manual_override_errors = validate_phase7_test_mode_auto_approval_router(
        manual_override_probe
    )

    phase5_reuse_probe = deepcopy(written)
    phase5_reuse_probe["phase5_test_trades_count_for_phase7"] = True
    phase5_reuse_probe["phase5_test_trade_reuse_count"] = 1
    phase5_reuse_probe["proof_contract"]["phase5_test_trade_reuse_allowed"] = True
    phase5_reuse_errors = validate_phase7_test_mode_auto_approval_router(
        phase5_reuse_probe
    )

    source_posture_probe = deepcopy(written)
    source_posture_probe["source_posture"][
        "preference_mcp_source_quorum_credit_allowed"
    ] = True
    source_posture_probe["source_posture"]["qctrl_role"] = "execution_truth"
    source_posture_errors = validate_phase7_test_mode_auto_approval_router(
        source_posture_probe
    )

    policy_probe = deepcopy(written)
    policy_probe["approval_policy"][
        "governance_feedback_affects_future_policy_only"
    ] = False
    policy_errors = validate_phase7_test_mode_auto_approval_router(policy_probe)

    local_path_probe = deepcopy(written)
    local_path_probe["provenance"]["source_refs"] = [
        "/Users/raminhoodeh/Desktop/qadam/data/runtime/private.json"
    ]
    local_path_errors = validate_phase7_test_mode_auto_approval_router(local_path_probe)

    print(f"phase7_auto_approval_status={written['status']}")
    print(f"phase7_auto_approval_stage_status={written['stage_status']}")
    print(
        "phase7_auto_approval_schema_version="
        f"{PHASE7_TEST_MODE_AUTO_APPROVAL_SCHEMA_VERSION}"
    )
    print(f"phase7_auto_approval_artifact_path={output_path}")
    print(f"phase7_auto_approval_history_path={history_path}")
    print(f"phase7_auto_approval_event_log_path={event_log_path}")
    print(
        "phase7_auto_approval_source_setup_ledger_status="
        f"{written['source_setup_ledger_status']}"
    )
    print(
        "phase7_auto_approval_source_weekly_cadence_status="
        f"{written['source_weekly_cadence_status']}"
    )
    print(
        "phase7_auto_approval_test_mode_auto_approval_allowed="
        f"{written['test_mode_auto_approval_allowed']}"
    )
    print(
        "phase7_auto_approval_phase7_test_mode_auto_approval_allowed="
        f"{written['phase7_test_mode_auto_approval_allowed']}"
    )
    print(
        "phase7_auto_approval_q7_6_proof_order_staging_stage_allowed="
        f"{written['q7_6_proof_order_staging_stage_allowed']}"
    )
    print(
        "phase7_auto_approval_decision_record_count="
        f"{written['approval_decision_record_count']}"
    )
    print(f"phase7_auto_approval_qualified_setup_count={written['qualified_setup_count']}")
    print(
        "phase7_auto_approval_qualified_setup_decision_count="
        f"{written['qualified_setup_decision_count']}"
    )
    print(
        "phase7_auto_approval_auto_approved_setup_count="
        f"{written['auto_approved_setup_count']}"
    )
    print(
        "phase7_auto_approval_rejected_setup_decision_count="
        f"{written['rejected_setup_decision_count']}"
    )
    print(
        "phase7_auto_approval_phase5_candidate_rejected_count="
        f"{written['phase5_candidate_rejected_count']}"
    )
    print(
        "phase7_auto_approval_fund_manager_trade_level_approval_count="
        f"{written['fund_manager_trade_level_approval_count']}"
    )
    print(
        "phase7_auto_approval_manual_trade_level_override_attempt_count="
        f"{written['manual_trade_level_override_attempt_count']}"
    )
    print(f"phase7_auto_approval_sample_contaminated={written['sample_contaminated']}")
    print(f"phase7_auto_approval_risk_or_kill_switch_bypass_count={written['risk_or_kill_switch_bypass_count']}")
    print(f"phase7_auto_approval_proof_order_staged_count={written['proof_order_staged_count']}")
    print(f"phase7_auto_approval_proof_trade_count={written['proof_trade_count']}")
    print(
        "phase7_auto_approval_phase7_proof_order_staging_allowed="
        f"{written['phase7_proof_order_staging_allowed']}"
    )
    print(
        "phase7_auto_approval_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(f"phase7_auto_approval_live_capital_enabled={written['live_capital_enabled']}")
    print(
        "phase7_auto_approval_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(f"phase7_auto_approval_blocker_count={written['blocker_count']}")
    print(f"phase7_auto_approval_event_log_replay_total_events={replay['total_events']}")
    print(f"phase7_auto_approval_readiness_error_count={len(readiness_errors)}")
    print(f"phase7_auto_approval_setup_ledger_error_count={len(setup_ledger_errors)}")
    print(f"phase7_auto_approval_weekly_cadence_error_count={len(weekly_cadence_errors)}")
    print(f"phase7_auto_approval_gate_probe_error_count={len(gate_errors)}")
    print(
        "phase7_auto_approval_manual_approval_probe_error_count="
        f"{len(manual_approval_errors)}"
    )
    print(
        "phase7_auto_approval_contaminated_probe_error_count="
        f"{len(contaminated_errors)}"
    )
    print(f"phase7_auto_approval_risk_bypass_probe_error_count={len(risk_bypass_errors)}")
    print(f"phase7_auto_approval_kill_switch_probe_error_count={len(kill_switch_errors)}")
    print(
        "phase7_auto_approval_source_quorum_probe_error_count="
        f"{len(source_quorum_errors)}"
    )
    print(f"phase7_auto_approval_phase5_approval_probe_error_count={len(phase5_approval_errors)}")
    print(f"phase7_auto_approval_staging_probe_error_count={len(staging_errors)}")
    print(f"phase7_auto_approval_proof_credit_probe_error_count={len(proof_credit_errors)}")
    print(f"phase7_auto_approval_broker_probe_error_count={len(broker_errors)}")
    print(f"phase7_auto_approval_live_capital_probe_error_count={len(live_capital_errors)}")
    print(
        "phase7_auto_approval_manual_override_probe_error_count="
        f"{len(manual_override_errors)}"
    )
    print(f"phase7_auto_approval_phase5_reuse_probe_error_count={len(phase5_reuse_errors)}")
    print(
        "phase7_auto_approval_source_posture_probe_error_count="
        f"{len(source_posture_errors)}"
    )
    print(f"phase7_auto_approval_policy_probe_error_count={len(policy_errors)}")
    print(f"phase7_auto_approval_local_path_probe_error_count={len(local_path_errors)}")
    print(f"phase7_auto_approval_next_stage={written['recommended_next_stage']}")
    print("phase7_auto_approval_boundary=" + written["boundary"])

    if readiness_errors:
        errors.extend(readiness_errors)
    if setup_ledger_errors:
        errors.extend(setup_ledger_errors)
    if weekly_cadence_errors:
        errors.extend(weekly_cadence_errors)
    if validation_errors:
        errors.extend(validation_errors)
    if runtime_copy.get("artifact_id") != written["artifact_id"]:
        errors.append("runtime_phase7_auto_approval_not_written")
    if written["status"] != "ready_no_auto_approved_setups":
        errors.append("phase7_auto_approval_status_invalid")
    if written["stage_status"] != "test_mode_auto_approval_router_ready_no_q7_setups":
        errors.append("phase7_auto_approval_stage_status_invalid")
    if written["test_mode_auto_approval_allowed"] is not True:
        errors.append("phase7_test_mode_auto_approval_not_allowed")
    if written["phase7_test_mode_auto_approval_allowed"] is not True:
        errors.append("phase7_auto_approval_authority_not_granted")
    if written["q7_6_proof_order_staging_stage_allowed"] is not True:
        errors.append("phase7_auto_approval_q7_6_not_allowed")
    if written["approval_decision_record_count"] != 1:
        errors.append("phase7_auto_approval_decision_record_count_mismatch")
    if written["qualified_setup_count"] != 0:
        errors.append("phase7_auto_approval_qualified_setup_count_nonzero")
    if written["qualified_setup_decision_count"] != 0:
        errors.append("phase7_auto_approval_qualified_decision_count_nonzero")
    if written["auto_approved_setup_count"] != 0:
        errors.append("phase7_auto_approval_auto_approved_count_nonzero")
    if written["rejected_setup_decision_count"] != 1:
        errors.append("phase7_auto_approval_rejected_count_mismatch")
    if written["phase5_candidate_rejected_count"] != 1:
        errors.append("phase7_auto_approval_phase5_rejected_count_mismatch")
    for count_key in (
        "fund_manager_trade_level_approval_count",
        "manual_trade_level_approval_count",
        "manual_trade_level_rejection_count",
        "manual_trade_level_resize_count",
        "manual_trade_level_exit_count",
        "manual_trade_level_override_attempt_count",
        "risk_or_kill_switch_bypass_count",
        "source_quorum_bypass_count",
        "proof_order_staged_count",
        "proof_trade_count",
        "unsafe_write_counter_total",
        "blocker_count",
    ):
        if written[count_key] != 0:
            errors.append(f"phase7_auto_approval_count_nonzero:{count_key}")
    if written["sample_contaminated"] is not False:
        errors.append("phase7_auto_approval_sample_contaminated")
    for flag_key in (
        "phase7_proof_order_staging_allowed",
        "phase7_proof_trade_submission_allowed",
        "phase7_proof_trade_execution_allowed",
        "phase7_proof_credit_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "manual_trade_level_override_allowed",
    ):
        if written[flag_key] is not False:
            errors.append(f"phase7_auto_approval_forbidden_authority:{flag_key}")
    if written["event_log_written"] is not True:
        errors.append("phase7_auto_approval_event_log_not_written")
    if replay["total_events"] != 1:
        errors.append("phase7_auto_approval_event_log_replay_count_mismatch")

    if "q7_5_test_mode_auto_approval_router_not_allowed" not in gate_errors:
        errors.append("gate_probe_not_rejected")
    if (
        "auto_approval_count_nonzero:fund_manager_trade_level_approval_count"
        not in manual_approval_errors
    ):
        errors.append("manual_fund_manager_approval_probe_not_rejected")
    if (
        "auto_approval_count_nonzero:manual_trade_level_approval_count"
        not in manual_approval_errors
    ):
        errors.append("manual_trade_approval_probe_not_rejected")
    if "auto_approval_sample_contaminated" not in contaminated_errors:
        errors.append("contamination_probe_not_rejected")
    if "auto_approval_contamination_reasons_present" not in contaminated_errors:
        errors.append("contamination_reason_probe_not_rejected")
    if "auto_approval_risk_gate_bypass" not in risk_bypass_errors:
        errors.append("risk_bypass_probe_not_rejected")
    if "auto_approval_kill_switch_bypass" not in kill_switch_errors:
        errors.append("kill_switch_probe_not_rejected")
    if "auto_approval_source_quorum_bypass" not in source_quorum_errors:
        errors.append("source_quorum_probe_not_rejected")
    if "auto_approval_non_q7_setup" not in phase5_approval_errors:
        errors.append("phase5_approval_probe_not_rejected")
    if (
        "auto_approval_authority_invalid:phase7_proof_order_staging_allowed"
        not in staging_errors
    ):
        errors.append("staging_authority_probe_not_rejected")
    if "auto_approval_forbidden:phase7_proof_order_staging_allowed" not in (
        staging_errors
    ):
        errors.append("staging_forbidden_probe_not_rejected")
    if "auto_approval_authority_invalid:phase7_proof_credit_allowed" not in (
        proof_credit_errors
    ):
        errors.append("proof_credit_authority_probe_not_rejected")
    if "auto_approval_unsafe_count_nonzero:phase7_proof_credit_allowed_count" not in (
        proof_credit_errors
    ):
        errors.append("proof_credit_counter_probe_not_rejected")
    if "auto_approval_authority_invalid:broker_post_allowed" not in broker_errors:
        errors.append("broker_authority_probe_not_rejected")
    if "auto_approval_authority_invalid:live_endpoint_allowed" not in broker_errors:
        errors.append("live_endpoint_authority_probe_not_rejected")
    if "auto_approval_unsafe_count_nonzero:broker_post_called_count" not in (
        broker_errors
    ):
        errors.append("broker_counter_probe_not_rejected")
    if "auto_approval_authority_invalid:live_capital_enabled" not in live_capital_errors:
        errors.append("live_capital_authority_probe_not_rejected")
    if "auto_approval_unsafe_count_nonzero:live_capital_enabled_count" not in (
        live_capital_errors
    ):
        errors.append("live_capital_counter_probe_not_rejected")
    if "auto_approval_authority_invalid:manual_trade_level_override_allowed" not in (
        manual_override_errors
    ):
        errors.append("manual_override_authority_probe_not_rejected")
    if "auto_approval_unsafe_count_nonzero:manual_trade_level_override_count" not in (
        manual_override_errors
    ):
        errors.append("manual_override_counter_probe_not_rejected")
    if "auto_approval_forbidden:phase5_test_trades_count_for_phase7" not in (
        phase5_reuse_errors
    ):
        errors.append("phase5_reuse_probe_not_rejected")
    if "auto_approval_proof_contract_phase5_reuse_allowed" not in phase5_reuse_errors:
        errors.append("phase5_reuse_contract_probe_not_rejected")
    if "auto_approval_preference_quorum_credit_allowed" not in source_posture_errors:
        errors.append("source_posture_preference_probe_not_rejected")
    if "auto_approval_qctrl_role_invalid" not in source_posture_errors:
        errors.append("source_posture_qctrl_probe_not_rejected")
    if (
        "auto_approval_policy_missing_true:governance_feedback_affects_future_policy_only"
        not in policy_errors
    ):
        errors.append("policy_governance_probe_not_rejected")
    if "auto_approval_provenance_local_path_leak" not in local_path_errors:
        errors.append("local_path_probe_not_rejected")

    if errors:
        for error in sorted(set(errors)):
            print(f"phase7_auto_approval_error={error}")
        print("phase7_test_mode_auto_approval_router_check=failed")
        return 1

    print("phase7_test_mode_auto_approval_router_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
