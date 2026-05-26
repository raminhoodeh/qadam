#!/usr/bin/env python3
"""Validate Q7-13 Phase 7 source and signal funnel evidence."""

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
from orchestrator.phase7_override_detector import (  # noqa: E402
    build_phase7_override_detector,
    validate_phase7_override_detector,
    write_phase7_override_detector,
)
from orchestrator.phase7_readiness import phase7_authority_defaults  # noqa: E402
from orchestrator.phase7_signal_funnel_evidence import (  # noqa: E402
    PHASE7_REQUIRED_SIGNAL_CHAIN_KEYS,
    PHASE7_SIGNAL_FUNNEL_EVIDENCE_SCHEMA_VERSION,
    PHASE7_SIGNAL_FUNNEL_REQUIRED_CHECKS,
    _authority_ledger,
    _signal_evidence_record,
    _signal_evidence_summary,
    _source_contexts,
    build_phase7_signal_funnel_evidence,
    phase7_signal_funnel_evidence_paths,
    validate_phase7_signal_funnel_evidence,
    write_phase7_signal_funnel_evidence,
)


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _checks(*, missing_chain: bool = False, private_priors_only: bool = False) -> list[dict[str, object]]:
    checks: list[dict[str, object]] = []
    for name in PHASE7_SIGNAL_FUNNEL_REQUIRED_CHECKS:
        passed = True
        if missing_chain and name.endswith("_ref_present_or_no_sample"):
            passed = False
        if private_priors_only and name == "private_priors_not_counted_as_proof":
            passed = False
        checks.append({"name": name, "passed": passed, "detail": None})
    return checks


def _with_records(
    artifact: dict[str, object],
    records: list[dict[str, object]],
    *,
    frozen: bool = False,
) -> dict[str, object]:
    probe = deepcopy(artifact)
    summary = _signal_evidence_summary(records)
    blocked = bool(summary["phase7_certification_blocked_by_signal_evidence"])
    status = "blocked_missing_signal_evidence" if blocked else "signal_funnel_evidence_recorded"
    stage_status = (
        "signal_funnel_evidence_certification_blocked"
        if blocked
        else "signal_funnel_evidence_recorded"
    )
    authorities = phase7_authority_defaults()
    authorities["phase7_proof_lifecycle_write_allowed"] = True
    authorities["phase7_postmortem_write_allowed"] = True
    authorities["phase7_performance_evaluation_write_allowed"] = True
    if not frozen:
        authorities["phase7_test_mode_auto_approval_allowed"] = True
        authorities["phase7_proof_order_staging_allowed"] = True
        authorities["phase7_proof_trade_submission_allowed"] = True
    checks = _checks(
        missing_chain=bool(summary["missing_decision_chain_count"]),
        private_priors_only=bool(summary["private_priors_only_proof_trade_count"]),
    )
    failed_checks = [
        str(check["name"]) for check in checks if check.get("passed") is not True
    ]
    probe.update(
        {
            "status": status,
            "stage_status": stage_status,
            "authority_ledger": _authority_ledger(
                stage_recorded=True,
                new_proof_trades_frozen=frozen,
            ),
            "signal_evidence_records": records,
            "source_override_status": "clean_no_overrides",
            "source_override_stage_status": "override_detector_clean_no_interventions",
            "source_override_sample_contaminated": False,
            "source_override_clean_sample": True,
            "source_override_new_proof_trades_frozen": frozen,
            "source_override_manual_trade_level_override_count": 0,
            "source_lifecycle_event_count": len(records),
            "source_proof_trade_count": len(records),
            "q7_13_signal_funnel_evidence_stage_allowed": True,
            "q7_14_maturity_tracker_stage_allowed": True,
            "signal_funnel_evidence_recorded": True,
            "signal_funnel_evidence_write_allowed": True,
            "evidence_state": status,
            "phase7_certification_blocked_by_override": False,
            "phase7_certification_blocked_by_contaminated_sample": False,
            "new_proof_trades_frozen": frozen,
            "new_proof_order_staging_allowed": not frozen,
            "new_proof_trade_submission_allowed": not frozen,
            "existing_lifecycle_closeout_allowed": True,
            "paper_order_submitted_count": len(records),
            "proof_trade_created_count": len(records),
            "manual_trade_level_override_count": 0,
            "unsafe_write_counter_total": 0,
            "checks": checks,
            "failed_checks": failed_checks,
            "failed_check_count": len(failed_checks),
            "blockers": [],
            "blocker_count": 0,
            "validation_errors": [],
            **authorities,
            **summary,
        }
    )
    return probe


def _source_contexts_present() -> dict[str, dict[str, object]]:
    contexts = _source_contexts()
    contexts["preference_mcp"]["present"] = True
    contexts["yahoo_finance"]["present"] = True
    contexts["qctrl_quantum"]["present"] = True
    return contexts


def _complete_record() -> dict[str, object]:
    setup_id = "q7-setup-probe-source-signal-chain"
    decision_id = f"q7-5:auto-approval:{setup_id}"
    staged_id = f"phase7:q7-6:staged-proof-order:{setup_id}"
    submitted_ref = "q7-paper-order-source-signal-probe"
    broker_ref = "q7-local-broker-receipt-source-signal-probe"
    gate_results = [
        {"gate_key": "source_quorum", "status": "pass"},
        {"gate_key": "akber_filter", "status": "pass"},
        {"gate_key": "signal_integrity", "status": "pass"},
        {"gate_key": "risk_agent_paper_sizing", "status": "pass"},
        {"gate_key": "execution_policy", "status": "pass"},
        {"gate_key": "kill_switches", "status": "pass"},
        {"gate_key": "venue_availability", "status": "pass"},
        {"gate_key": "broker_paper_readiness", "status": "pass"},
    ]
    lifecycle_record = {
        "artifact_id": "phase7:q7-8:proof-lifecycle:source-signal-probe",
        "lifecycle_state": "closed_trade",
        "proof_trade_created": True,
        "source_setup_record_id": setup_id,
        "source_auto_approval_decision_id": decision_id,
        "source_staged_order_artifact_id": staged_id,
        "submitted_order_ref": submitted_ref,
        "broker_receipt_ref": broker_ref,
        "closed_trade_ref": "q7-closed-trade-source-signal-probe",
    }
    setup_record = {
        "setup_record_id": setup_id,
        "source_phase": "Q7",
        "supplemental_only": False,
        "source_quorum_passed": True,
        "canonical_source_quorum_passed": True,
        "gate_results": gate_results,
    }
    decision_record = {
        "decision_id": decision_id,
        "setup_record_id": setup_id,
        "source_phase": "Q7",
        "source_quorum_passed": True,
        "risk_gate_passed": True,
        "execution_policy_gate_passed": True,
        "kill_switches_clear": True,
        "broker_paper_ready": True,
        "gate_results": gate_results,
    }
    staged_order = {
        "artifact_id": staged_id,
        "status": "staged",
        "quantity": 1,
        "idempotency_namespace": "phase7_demo_proof",
    }
    receipt_record = {
        "artifact_id": "phase7:q7-7:guarded-alpaca-submit:source-signal-probe",
        "status": "submitted",
        "submitted_order_ref": submitted_ref,
        "broker_receipt_ref": broker_ref,
    }
    return _signal_evidence_record(
        lifecycle_record,
        setup_record=setup_record,
        decision_record=decision_record,
        staged_order_record=staged_order,
        broker_receipt_record=receipt_record,
        source_contexts=_source_contexts_present(),
    )


def _missing_chain_record() -> dict[str, object]:
    record = deepcopy(_complete_record())
    record["decision_chain_refs"]["akber_filter"] = None
    missing = [key for key in PHASE7_REQUIRED_SIGNAL_CHAIN_KEYS if not record["decision_chain_refs"].get(key)]
    record["missing_decision_chain_refs"] = missing
    record["missing_decision_chain_ref_count"] = len(missing)
    record["decision_chain_ref_count"] = sum(
        1 for value in record["decision_chain_refs"].values() if value
    )
    record["complete_decision_chain"] = False
    record["status"] = "blocked"
    record["evidence_state"] = "blocked_missing_decision_chain"
    record["phase7_certification_blocked_by_signal_evidence"] = True
    for check in record["checks"]:
        if check["name"] == "akber_filter_ref_present_or_no_sample":
            check["passed"] = False
    record["failed_checks"] = [
        str(check["name"]) for check in record["checks"] if check.get("passed") is not True
    ]
    record["failed_check_count"] = len(record["failed_checks"])
    return record


def _private_prior_record() -> dict[str, object]:
    record = deepcopy(_complete_record())
    record["private_priors_only"] = True
    record["complete_decision_chain"] = False
    record["status"] = "blocked"
    record["evidence_state"] = "blocked_private_priors_only"
    record["phase7_certification_blocked_by_signal_evidence"] = True
    for check in record["checks"]:
        if check["name"] == "private_priors_not_counted_as_proof":
            check["passed"] = False
    record["failed_checks"] = [
        str(check["name"]) for check in record["checks"] if check.get("passed") is not True
    ]
    record["failed_check_count"] = len(record["failed_checks"])
    return record


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = phase7_signal_funnel_evidence_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    override = build_phase7_override_detector(settings=settings)
    _, _, override_event_path, override_written = write_phase7_override_detector(
        override,
        settings=settings,
        record_event=True,
    )
    override_errors = validate_phase7_override_detector(override_written)

    artifact = build_phase7_signal_funnel_evidence(settings=settings)
    output_path, history_path, event_log_path, written = write_phase7_signal_funnel_evidence(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase7_signal_funnel_evidence(written)
    replay = EventLog(event_log_path, echo=False).replay()
    runtime_copy = _read_json(output_path)

    valid_complete_probe = _with_records(written, [_complete_record()])
    valid_complete_errors = validate_phase7_signal_funnel_evidence(valid_complete_probe)

    valid_missing_probe = _with_records(written, [_missing_chain_record()])
    valid_missing_errors = validate_phase7_signal_funnel_evidence(valid_missing_probe)

    missing_not_blocking_probe = deepcopy(valid_missing_probe)
    missing_not_blocking_probe["phase7_certification_blocked_by_signal_evidence"] = False
    missing_not_blocking_errors = validate_phase7_signal_funnel_evidence(
        missing_not_blocking_probe
    )

    valid_private_probe = _with_records(written, [_private_prior_record()])
    valid_private_errors = validate_phase7_signal_funnel_evidence(valid_private_probe)

    private_not_blocking_probe = deepcopy(valid_private_probe)
    private_not_blocking_probe["phase7_certification_blocked_by_signal_evidence"] = False
    private_not_blocking_errors = validate_phase7_signal_funnel_evidence(
        private_not_blocking_probe
    )

    preference_counts_probe = deepcopy(valid_complete_probe)
    preference_counts_probe["signal_evidence_records"][0]["preference_context"][
        "counts_as_proof"
    ] = True
    preference_counts_errors = validate_phase7_signal_funnel_evidence(
        preference_counts_probe
    )

    yahoo_counts_probe = deepcopy(valid_complete_probe)
    yahoo_counts_probe["signal_evidence_records"][0]["yahoo_context"][
        "counts_as_source_quorum"
    ] = True
    yahoo_counts_probe["signal_evidence_records"][0]["yahoo_context"][
        "counts_as_proof"
    ] = True
    yahoo_counts_errors = validate_phase7_signal_funnel_evidence(yahoo_counts_probe)

    quantum_counts_probe = deepcopy(valid_complete_probe)
    quantum_counts_probe["signal_evidence_records"][0]["quantum_shadow_annotation"][
        "counts_as_execution_truth"
    ] = True
    quantum_counts_probe["signal_evidence_records"][0]["quantum_shadow_annotation"][
        "counts_as_proof"
    ] = True
    quantum_counts_errors = validate_phase7_signal_funnel_evidence(quantum_counts_probe)

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["authority_ledger"]["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase7_signal_funnel_evidence(proof_credit_probe)

    broker_post_probe = deepcopy(written)
    broker_post_probe["broker_post_allowed"] = True
    broker_post_probe["authority_ledger"]["broker_post_allowed"] = True
    broker_post_probe["broker_post_called_count"] = 1
    broker_post_errors = validate_phase7_signal_funnel_evidence(broker_post_probe)

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_probe["authority_ledger"]["live_capital_enabled"] = True
    live_capital_probe["live_capital_enabled_count"] = 1
    live_capital_errors = validate_phase7_signal_funnel_evidence(live_capital_probe)

    market_write_probe = deepcopy(written)
    market_write_probe["prediction_market_write_allowed"] = True
    market_write_probe["authority_ledger"]["prediction_market_write_allowed"] = True
    market_write_probe["prediction_market_write_allowed_count"] = 1
    market_write_probe["crypto_perps_write_allowed"] = True
    market_write_probe["authority_ledger"]["crypto_perps_write_allowed"] = True
    market_write_probe["crypto_perps_write_allowed_count"] = 1
    market_write_errors = validate_phase7_signal_funnel_evidence(market_write_probe)

    manual_authority_probe = deepcopy(written)
    manual_authority_probe["manual_trade_level_override_allowed"] = True
    manual_authority_probe["authority_ledger"]["manual_trade_level_override_allowed"] = True
    manual_authority_errors = validate_phase7_signal_funnel_evidence(
        manual_authority_probe
    )

    source_posture_probe = deepcopy(written)
    source_posture_probe["source_posture"]["preference_mcp_source_quorum_credit_allowed"] = True
    source_posture_probe["source_posture"]["qctrl_role"] = "execution_truth"
    source_posture_errors = validate_phase7_signal_funnel_evidence(source_posture_probe)

    local_path_probe = deepcopy(written)
    local_path_probe["provenance"]["source_refs"] = [
        "/Users/raminhoodeh/Desktop/qadam/data/runtime/private.json"
    ]
    local_path_errors = validate_phase7_signal_funnel_evidence(local_path_probe)

    gate_probe = deepcopy(written)
    gate_probe["q7_13_signal_funnel_evidence_stage_allowed"] = False
    gate_errors = validate_phase7_signal_funnel_evidence(gate_probe)

    next_stage_gate_probe = deepcopy(written)
    next_stage_gate_probe["q7_14_maturity_tracker_stage_allowed"] = False
    next_stage_gate_errors = validate_phase7_signal_funnel_evidence(
        next_stage_gate_probe
    )

    print(f"phase7_signal_evidence_status={written['status']}")
    print(f"phase7_signal_evidence_stage_status={written['stage_status']}")
    print(
        "phase7_signal_evidence_schema_version="
        f"{PHASE7_SIGNAL_FUNNEL_EVIDENCE_SCHEMA_VERSION}"
    )
    print(f"phase7_signal_evidence_artifact_path={output_path}")
    print(f"phase7_signal_evidence_history_path={history_path}")
    print(f"phase7_signal_evidence_event_log_path={event_log_path}")
    print(f"phase7_signal_evidence_source_override_status={written['source_override_status']}")
    print(
        "phase7_signal_evidence_source_override_sample_contaminated="
        f"{written['source_override_sample_contaminated']}"
    )
    print(
        "phase7_signal_evidence_q7_14_maturity_stage_allowed="
        f"{written['q7_14_maturity_tracker_stage_allowed']}"
    )
    print(
        "phase7_signal_evidence_write_allowed="
        f"{written['signal_funnel_evidence_write_allowed']}"
    )
    print(
        "phase7_signal_evidence_record_count="
        f"{written['proof_trade_evidence_record_count']}"
    )
    print(
        "phase7_signal_evidence_complete_decision_chain_count="
        f"{written['complete_decision_chain_count']}"
    )
    print(
        "phase7_signal_evidence_missing_decision_chain_count="
        f"{written['missing_decision_chain_count']}"
    )
    print(
        "phase7_signal_evidence_private_priors_only_proof_trade_count="
        f"{written['private_priors_only_proof_trade_count']}"
    )
    print(
        "phase7_signal_evidence_challenge_only_preference_context_count="
        f"{written['challenge_only_preference_context_count']}"
    )
    print(
        "phase7_signal_evidence_yahoo_supplemental_context_count="
        f"{written['yahoo_supplemental_context_count']}"
    )
    print(
        "phase7_signal_evidence_quantum_shadow_annotation_count="
        f"{written['quantum_shadow_annotation_count']}"
    )
    print(
        "phase7_signal_evidence_phase7_certification_blocked_by_signal_evidence="
        f"{written['phase7_certification_blocked_by_signal_evidence']}"
    )
    print(
        "phase7_signal_evidence_private_prior_counts_as_proof="
        f"{written['private_prior_counts_as_proof']}"
    )
    print(
        "phase7_signal_evidence_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(f"phase7_signal_evidence_live_capital_enabled={written['live_capital_enabled']}")
    print(
        "phase7_signal_evidence_broker_post_called_count="
        f"{written['broker_post_called_count']}"
    )
    print(
        "phase7_signal_evidence_alpaca_post_called_count="
        f"{written['alpaca_post_called_count']}"
    )
    print(
        "phase7_signal_evidence_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(f"phase7_signal_evidence_blocker_count={written['blocker_count']}")
    print(f"phase7_signal_evidence_event_log_replay_total_events={replay['total_events']}")
    print(f"phase7_signal_evidence_source_override_event_log_path={override_event_path}")
    print(f"phase7_signal_evidence_source_override_error_count={len(override_errors)}")
    print(
        "phase7_signal_evidence_valid_complete_probe_error_count="
        f"{len(valid_complete_errors)}"
    )
    print(
        "phase7_signal_evidence_valid_missing_probe_error_count="
        f"{len(valid_missing_errors)}"
    )
    print(
        "phase7_signal_evidence_missing_not_blocking_probe_error_count="
        f"{len(missing_not_blocking_errors)}"
    )
    print(
        "phase7_signal_evidence_valid_private_probe_error_count="
        f"{len(valid_private_errors)}"
    )
    print(
        "phase7_signal_evidence_private_not_blocking_probe_error_count="
        f"{len(private_not_blocking_errors)}"
    )
    print(
        "phase7_signal_evidence_preference_counts_probe_error_count="
        f"{len(preference_counts_errors)}"
    )
    print(
        "phase7_signal_evidence_yahoo_counts_probe_error_count="
        f"{len(yahoo_counts_errors)}"
    )
    print(
        "phase7_signal_evidence_quantum_counts_probe_error_count="
        f"{len(quantum_counts_errors)}"
    )
    print(
        "phase7_signal_evidence_proof_credit_probe_error_count="
        f"{len(proof_credit_errors)}"
    )
    print(
        "phase7_signal_evidence_broker_post_probe_error_count="
        f"{len(broker_post_errors)}"
    )
    print(
        "phase7_signal_evidence_live_capital_probe_error_count="
        f"{len(live_capital_errors)}"
    )
    print(
        "phase7_signal_evidence_market_write_probe_error_count="
        f"{len(market_write_errors)}"
    )
    print(
        "phase7_signal_evidence_manual_authority_probe_error_count="
        f"{len(manual_authority_errors)}"
    )
    print(
        "phase7_signal_evidence_source_posture_probe_error_count="
        f"{len(source_posture_errors)}"
    )
    print(f"phase7_signal_evidence_local_path_probe_error_count={len(local_path_errors)}")
    print(f"phase7_signal_evidence_gate_probe_error_count={len(gate_errors)}")
    print(
        "phase7_signal_evidence_next_stage_gate_probe_error_count="
        f"{len(next_stage_gate_errors)}"
    )
    print(f"phase7_signal_evidence_next_stage={written['recommended_next_stage']}")
    print("phase7_signal_evidence_boundary=" + written["boundary"])

    if override_errors:
        errors.extend(override_errors)
    if validation_errors:
        errors.extend(validation_errors)
    if runtime_copy.get("artifact_id") != written["artifact_id"]:
        errors.append("runtime_phase7_signal_evidence_not_written")
    if written["status"] != "ready_no_proof_trades":
        errors.append("phase7_signal_evidence_status_invalid")
    if written["stage_status"] != "signal_funnel_evidence_ready_no_proof_trades":
        errors.append("phase7_signal_evidence_stage_status_invalid")
    if written["signal_funnel_evidence_write_allowed"] is not True:
        errors.append("phase7_signal_evidence_write_authority_missing")
    if written["q7_14_maturity_tracker_stage_allowed"] is not True:
        errors.append("phase7_signal_evidence_q7_14_not_allowed")
    for count_key in (
        "proof_trade_evidence_record_count",
        "complete_decision_chain_count",
        "missing_decision_chain_count",
        "private_priors_only_proof_trade_count",
        "challenge_only_preference_context_count",
        "yahoo_supplemental_context_count",
        "quantum_shadow_annotation_count",
        "paper_order_submitted_count",
        "proof_trade_created_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
        "unsafe_write_counter_total",
        "blocker_count",
    ):
        if written[count_key] != 0:
            errors.append(f"phase7_signal_evidence_count_nonzero:{count_key}")
    for flag_key in (
        "source_override_sample_contaminated",
        "phase7_certification_blocked_by_signal_evidence",
        "private_prior_counts_as_proof",
        "private_priors_only_certification_allowed",
        "source_quorum_bypass_allowed",
        "supplemental_source_bypass_allowed",
        "preference_mcp_source_quorum_credit_allowed",
        "phase7_proof_trade_execution_allowed",
        "phase7_proof_credit_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "manual_trade_level_override_allowed",
    ):
        if written[flag_key] is not False:
            errors.append(f"phase7_signal_evidence_forbidden_or_unexpected:{flag_key}")
    if written["source_override_clean_sample"] is not True:
        errors.append("phase7_signal_evidence_source_clean_sample_missing")
    if written["event_log_written"] is not True:
        errors.append("phase7_signal_evidence_event_log_not_written")
    if replay["total_events"] != 1:
        errors.append("phase7_signal_evidence_event_log_replay_count_mismatch")
    if valid_complete_errors:
        errors.append("valid_complete_signal_chain_probe_rejected")
    if valid_missing_errors:
        errors.append("valid_missing_signal_chain_blocked_probe_rejected")
    if "phase7_signal_evidence_summary_mismatch:phase7_certification_blocked_by_signal_evidence" not in missing_not_blocking_errors:
        errors.append("missing_not_blocking_probe_not_rejected")
    if valid_private_errors:
        errors.append("valid_private_prior_blocked_probe_rejected")
    if "phase7_signal_evidence_summary_mismatch:phase7_certification_blocked_by_signal_evidence" not in private_not_blocking_errors:
        errors.append("private_not_blocking_probe_not_rejected")
    if "phase7_signal_evidence_preference_counts_as_proof" not in preference_counts_errors:
        errors.append("preference_counts_as_proof_probe_not_rejected")
    if "phase7_signal_evidence_yahoo_quorum_credit_allowed" not in yahoo_counts_errors:
        errors.append("yahoo_quorum_credit_probe_not_rejected")
    if "phase7_signal_evidence_yahoo_counts_as_proof" not in yahoo_counts_errors:
        errors.append("yahoo_counts_as_proof_probe_not_rejected")
    if "phase7_signal_evidence_quantum_execution_truth_allowed" not in quantum_counts_errors:
        errors.append("quantum_execution_truth_probe_not_rejected")
    if "phase7_signal_evidence_quantum_counts_as_proof" not in quantum_counts_errors:
        errors.append("quantum_counts_as_proof_probe_not_rejected")
    if "phase7_signal_evidence_authority_invalid:phase7_proof_credit_allowed" not in proof_credit_errors:
        errors.append("proof_credit_authority_probe_not_rejected")
    if "phase7_signal_evidence_unsafe_count_nonzero:phase7_proof_credit_allowed_count" not in proof_credit_errors:
        errors.append("proof_credit_count_probe_not_rejected")
    if "phase7_signal_evidence_authority_invalid:broker_post_allowed" not in broker_post_errors:
        errors.append("broker_post_authority_probe_not_rejected")
    if "phase7_signal_evidence_count_nonzero:broker_post_called_count" not in broker_post_errors:
        errors.append("broker_post_count_probe_not_rejected")
    if "phase7_signal_evidence_authority_invalid:live_capital_enabled" not in live_capital_errors:
        errors.append("live_capital_authority_probe_not_rejected")
    if "phase7_signal_evidence_unsafe_count_nonzero:live_capital_enabled_count" not in live_capital_errors:
        errors.append("live_capital_count_probe_not_rejected")
    if "phase7_signal_evidence_authority_invalid:prediction_market_write_allowed" not in market_write_errors:
        errors.append("prediction_market_authority_probe_not_rejected")
    if "phase7_signal_evidence_authority_invalid:crypto_perps_write_allowed" not in market_write_errors:
        errors.append("crypto_perps_authority_probe_not_rejected")
    if "phase7_signal_evidence_authority_invalid:manual_trade_level_override_allowed" not in manual_authority_errors:
        errors.append("manual_authority_probe_not_rejected")
    if "phase7_signal_evidence_preference_quorum_credit_allowed" not in source_posture_errors:
        errors.append("source_posture_preference_probe_not_rejected")
    if "phase7_signal_evidence_qctrl_role_invalid" not in source_posture_errors:
        errors.append("source_posture_qctrl_probe_not_rejected")
    if "phase7_signal_evidence_provenance_local_path_leak" not in local_path_errors:
        errors.append("local_path_probe_not_rejected")
    if "q7_13_signal_funnel_evidence_not_allowed" not in gate_errors:
        errors.append("gate_probe_not_rejected")
    if "q7_14_maturity_tracker_not_allowed" not in next_stage_gate_errors:
        errors.append("next_stage_gate_probe_not_rejected")
    if written["recommended_next_stage"] != "Q7-14 100-Trade Maturity Tracker":
        errors.append("phase7_signal_evidence_next_stage_mismatch")

    if errors:
        print("phase7_signal_evidence_check=FAIL")
        for error in sorted(set(errors)):
            print(f"error={error}")
        return 1
    print("phase7_signal_evidence_check=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
