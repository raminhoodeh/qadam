#!/usr/bin/env python3
"""Validate Q7-12 Phase 7 Demo Proof override detector."""

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
from orchestrator.phase7_drawdown_risk_sentinel import (  # noqa: E402
    build_phase7_drawdown_risk_sentinel,
    validate_phase7_drawdown_risk_sentinel,
    write_phase7_drawdown_risk_sentinel,
)
from orchestrator.phase7_override_detector import (  # noqa: E402
    PHASE7_OVERRIDE_DETECTOR_SCHEMA_VERSION,
    PHASE7_OVERRIDE_REQUIRED_CHECKS,
    _authority_ledger,
    _governance_feedback_records,
    _kind_count,
    _override_record,
    build_phase7_override_detector,
    phase7_override_detector_paths,
    validate_phase7_override_detector,
    write_phase7_override_detector,
)
from orchestrator.phase7_readiness import phase7_authority_defaults  # noqa: E402


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _checks() -> list[dict[str, object]]:
    return [
        {"name": name, "passed": True, "detail": None}
        for name in PHASE7_OVERRIDE_REQUIRED_CHECKS
    ]


def _governance_source() -> dict[str, object]:
    return {
        "artifact_id": "phase7:q7-5:test-mode-auto-approval-router",
        "governance_feedback_channels": [
            "strategy_toggles",
            "kill_switches",
            "governance_comments",
        ],
    }


def _with_override_records(
    artifact: dict[str, object],
    records: list[dict[str, object]],
    *,
    source_drawdown_frozen: bool = False,
) -> dict[str, object]:
    probe = deepcopy(artifact)
    governance_records = _governance_feedback_records(_governance_source())
    override_count = sum(int(record.get("intervention_count", 0) or 0) for record in records)
    manual_count = _kind_count(
        records,
        "manual_trade_level_approval",
        "manual_trade_level_rejection",
        "manual_quantity_edit",
        "manual_price_edit",
        "manual_exit",
        "manual_trade_level_override_attempt",
    )
    broker_count = _kind_count(records, "broker_side_intervention")
    unlinked_count = _kind_count(records, "unlinked_lifecycle_record")
    contaminated = override_count > 0
    frozen = contaminated or source_drawdown_frozen
    authorities = phase7_authority_defaults()
    authorities["phase7_proof_lifecycle_write_allowed"] = True
    authorities["phase7_postmortem_write_allowed"] = True
    authorities["phase7_performance_evaluation_write_allowed"] = True
    if not frozen:
        authorities["phase7_test_mode_auto_approval_allowed"] = True
        authorities["phase7_proof_order_staging_allowed"] = True
        authorities["phase7_proof_trade_submission_allowed"] = True
    probe.update(
        {
            "status": "contaminated" if contaminated else "clean_no_overrides",
            "stage_status": (
                "override_detector_sample_contaminated"
                if contaminated
                else "override_detector_clean_no_interventions"
            ),
            "authority_ledger": _authority_ledger(
                stage_recorded=True,
                new_proof_trades_frozen=frozen,
            ),
            "override_records": records,
            "governance_feedback_records": governance_records,
            "source_drawdown_new_proof_trades_frozen": source_drawdown_frozen,
            "q7_12_override_detector_stage_allowed": True,
            "q7_13_signal_funnel_evidence_stage_allowed": True,
            "override_detector_recorded": True,
            "override_detection_write_allowed": True,
            "override_count": override_count,
            "override_record_count": len(records),
            "manual_trade_level_approval_count": _kind_count(
                records,
                "manual_trade_level_approval",
            ),
            "manual_trade_level_rejection_count": _kind_count(
                records,
                "manual_trade_level_rejection",
            ),
            "manual_trade_level_quantity_edit_count": _kind_count(
                records,
                "manual_quantity_edit",
            ),
            "manual_trade_level_price_edit_count": _kind_count(
                records,
                "manual_price_edit",
            ),
            "manual_trade_level_exit_count": _kind_count(records, "manual_exit"),
            "manual_trade_level_override_attempt_count": _kind_count(
                records,
                "manual_trade_level_override_attempt",
            ),
            "manual_trade_level_override_count": manual_count,
            "broker_side_intervention_count": broker_count,
            "unlinked_lifecycle_record_count": unlinked_count,
            "governance_feedback_record_count": len(governance_records),
            "governance_feedback_trade_level_intervention_count": 0,
            "governance_feedback_affects_future_policy_only": True,
            "sample_contaminated": contaminated,
            "clean_sample": not contaminated,
            "phase7_certification_blocked_by_override": contaminated,
            "phase7_certification_blocked_by_contaminated_sample": contaminated,
            "run_restart_required": contaminated,
            "restart_reason": (
                "manual_trade_level_intervention" if contaminated else None
            ),
            "sample_contamination_freeze_active": frozen,
            "new_proof_trades_frozen": frozen,
            "new_proof_trades_frozen_by_override": contaminated,
            "new_proof_trades_frozen_by_drawdown": source_drawdown_frozen,
            "new_proof_order_staging_allowed": not frozen,
            "new_proof_trade_submission_allowed": not frozen,
            "existing_lifecycle_closeout_allowed": True,
            "unsafe_write_counter_total": manual_count,
            "checks": _checks(),
            "failed_checks": [],
            "failed_check_count": 0,
            "blockers": [],
            "blocker_count": 0,
            "validation_errors": [],
            **authorities,
        }
    )
    return probe


def _manual_record(kind: str = "manual_trade_level_approval") -> dict[str, object]:
    return _override_record(
        override_kind=kind,
        source_artifact_id="phase7:q7-5:auto-approval:probe",
        source_ref=f"probe:{kind}",
        source_stage="Q7-5",
    )


def _broker_record() -> dict[str, object]:
    return _override_record(
        override_kind="broker_side_intervention",
        source_artifact_id="phase7:q7-8:lifecycle:broker-probe",
        source_ref="probe:broker-side-change",
        source_stage="Q7-8",
    )


def _unlinked_record() -> dict[str, object]:
    return _override_record(
        override_kind="unlinked_lifecycle_record",
        source_artifact_id="phase7:q7-8:lifecycle:unlinked-probe",
        source_ref="probe:unlinked-lifecycle",
        source_stage="Q7-8",
    )


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = phase7_override_detector_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    drawdown = build_phase7_drawdown_risk_sentinel(settings=settings)
    _, _, drawdown_event_path, drawdown_written = write_phase7_drawdown_risk_sentinel(
        drawdown,
        settings=settings,
        record_event=True,
    )
    drawdown_errors = validate_phase7_drawdown_risk_sentinel(drawdown_written)

    artifact = build_phase7_override_detector(settings=settings)
    output_path, history_path, event_log_path, written = write_phase7_override_detector(
        artifact,
        settings=settings,
        record_event=True,
        event_log_path=event_log_path,
    )
    validation_errors = validate_phase7_override_detector(written)
    replay = EventLog(event_log_path, echo=False).replay()
    runtime_copy = _read_json(output_path)

    valid_governance_probe = _with_override_records(written, [])
    valid_governance_errors = validate_phase7_override_detector(valid_governance_probe)

    valid_manual_probe = _with_override_records(written, [_manual_record()])
    valid_manual_errors = validate_phase7_override_detector(valid_manual_probe)

    valid_broker_probe = _with_override_records(written, [_broker_record()])
    valid_broker_errors = validate_phase7_override_detector(valid_broker_probe)

    valid_unlinked_probe = _with_override_records(written, [_unlinked_record()])
    valid_unlinked_errors = validate_phase7_override_detector(valid_unlinked_probe)

    valid_source_frozen_probe = _with_override_records(
        written,
        [],
        source_drawdown_frozen=True,
    )
    valid_source_frozen_errors = validate_phase7_override_detector(
        valid_source_frozen_probe
    )

    contamination_not_blocking_probe = deepcopy(valid_manual_probe)
    contamination_not_blocking_probe["phase7_certification_blocked_by_override"] = False
    contamination_not_blocking_probe[
        "phase7_certification_blocked_by_contaminated_sample"
    ] = False
    contamination_not_blocking_errors = validate_phase7_override_detector(
        contamination_not_blocking_probe
    )

    contamination_not_frozen_probe = deepcopy(valid_manual_probe)
    contamination_not_frozen_probe["new_proof_trades_frozen"] = False
    contamination_not_frozen_probe["sample_contamination_freeze_active"] = False
    contamination_not_frozen_probe["new_proof_order_staging_allowed"] = True
    contamination_not_frozen_probe["new_proof_trade_submission_allowed"] = True
    contamination_not_frozen_errors = validate_phase7_override_detector(
        contamination_not_frozen_probe
    )

    governance_contaminates_probe = deepcopy(valid_governance_probe)
    governance_contaminates_probe["governance_feedback_records"][0][
        "sample_contaminating"
    ] = True
    governance_contaminates_errors = validate_phase7_override_detector(
        governance_contaminates_probe
    )

    manual_count_probe = deepcopy(valid_manual_probe)
    manual_count_probe["manual_trade_level_override_count"] = 0
    manual_count_probe["unsafe_write_counter_total"] = 0
    manual_count_errors = validate_phase7_override_detector(manual_count_probe)

    clean_with_override_count_probe = deepcopy(written)
    clean_with_override_count_probe["manual_trade_level_override_count"] = 1
    clean_with_override_count_probe["unsafe_write_counter_total"] = 1
    clean_with_override_count_errors = validate_phase7_override_detector(
        clean_with_override_count_probe
    )

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["authority_ledger"]["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase7_override_detector(proof_credit_probe)

    broker_post_probe = deepcopy(written)
    broker_post_probe["broker_post_allowed"] = True
    broker_post_probe["authority_ledger"]["broker_post_allowed"] = True
    broker_post_probe["broker_post_called_count"] = 1
    broker_post_errors = validate_phase7_override_detector(broker_post_probe)

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_probe["authority_ledger"]["live_capital_enabled"] = True
    live_capital_probe["live_capital_enabled_count"] = 1
    live_capital_errors = validate_phase7_override_detector(live_capital_probe)

    market_write_probe = deepcopy(written)
    market_write_probe["prediction_market_write_allowed"] = True
    market_write_probe["authority_ledger"]["prediction_market_write_allowed"] = True
    market_write_probe["prediction_market_write_allowed_count"] = 1
    market_write_probe["crypto_perps_write_allowed"] = True
    market_write_probe["authority_ledger"]["crypto_perps_write_allowed"] = True
    market_write_probe["crypto_perps_write_allowed_count"] = 1
    market_write_errors = validate_phase7_override_detector(market_write_probe)

    manual_authority_probe = deepcopy(written)
    manual_authority_probe["manual_trade_level_override_allowed"] = True
    manual_authority_probe["authority_ledger"][
        "manual_trade_level_override_allowed"
    ] = True
    manual_authority_errors = validate_phase7_override_detector(manual_authority_probe)

    source_posture_probe = deepcopy(written)
    source_posture_probe["source_posture"][
        "preference_mcp_source_quorum_credit_allowed"
    ] = True
    source_posture_probe["source_posture"]["qctrl_role"] = "execution_truth"
    source_posture_errors = validate_phase7_override_detector(source_posture_probe)

    local_path_probe = deepcopy(written)
    local_path_probe["provenance"]["source_refs"] = [
        "/Users/raminhoodeh/Desktop/qadam/data/runtime/private.json"
    ]
    local_path_errors = validate_phase7_override_detector(local_path_probe)

    gate_probe = deepcopy(written)
    gate_probe["q7_12_override_detector_stage_allowed"] = False
    gate_errors = validate_phase7_override_detector(gate_probe)

    next_stage_gate_probe = deepcopy(written)
    next_stage_gate_probe["q7_13_signal_funnel_evidence_stage_allowed"] = False
    next_stage_gate_errors = validate_phase7_override_detector(next_stage_gate_probe)

    print(f"phase7_override_status={written['status']}")
    print(f"phase7_override_stage_status={written['stage_status']}")
    print(f"phase7_override_schema_version={PHASE7_OVERRIDE_DETECTOR_SCHEMA_VERSION}")
    print(f"phase7_override_artifact_path={output_path}")
    print(f"phase7_override_history_path={history_path}")
    print(f"phase7_override_event_log_path={event_log_path}")
    print(f"phase7_override_source_drawdown_status={written['source_drawdown_status']}")
    print(
        "phase7_override_source_drawdown_new_proof_trades_frozen="
        f"{written['source_drawdown_new_proof_trades_frozen']}"
    )
    print(
        "phase7_override_q7_13_signal_stage_allowed="
        f"{written['q7_13_signal_funnel_evidence_stage_allowed']}"
    )
    print(
        "phase7_override_detection_write_allowed="
        f"{written['override_detection_write_allowed']}"
    )
    print(f"phase7_override_sample_contaminated={written['sample_contaminated']}")
    print(f"phase7_override_clean_sample={written['clean_sample']}")
    print(f"phase7_override_count={written['override_count']}")
    print(f"phase7_override_record_count={written['override_record_count']}")
    print(
        "phase7_override_manual_trade_level_override_count="
        f"{written['manual_trade_level_override_count']}"
    )
    print(
        "phase7_override_broker_side_intervention_count="
        f"{written['broker_side_intervention_count']}"
    )
    print(
        "phase7_override_unlinked_lifecycle_record_count="
        f"{written['unlinked_lifecycle_record_count']}"
    )
    print(
        "phase7_override_governance_feedback_record_count="
        f"{written['governance_feedback_record_count']}"
    )
    print(
        "phase7_override_governance_feedback_trade_level_intervention_count="
        f"{written['governance_feedback_trade_level_intervention_count']}"
    )
    print(
        "phase7_override_new_proof_trades_frozen="
        f"{written['new_proof_trades_frozen']}"
    )
    print(
        "phase7_override_new_proof_order_staging_allowed="
        f"{written['new_proof_order_staging_allowed']}"
    )
    print(
        "phase7_override_new_proof_trade_submission_allowed="
        f"{written['new_proof_trade_submission_allowed']}"
    )
    print(
        "phase7_override_phase7_certification_blocked_by_override="
        f"{written['phase7_certification_blocked_by_override']}"
    )
    print(f"phase7_override_run_restart_required={written['run_restart_required']}")
    print(
        "phase7_override_phase7_proof_credit_allowed="
        f"{written['phase7_proof_credit_allowed']}"
    )
    print(f"phase7_override_live_capital_enabled={written['live_capital_enabled']}")
    print(
        "phase7_override_broker_post_called_count="
        f"{written['broker_post_called_count']}"
    )
    print(
        "phase7_override_alpaca_post_called_count="
        f"{written['alpaca_post_called_count']}"
    )
    print(
        "phase7_override_unsafe_write_counter_total="
        f"{written['unsafe_write_counter_total']}"
    )
    print(f"phase7_override_blocker_count={written['blocker_count']}")
    print(f"phase7_override_event_log_replay_total_events={replay['total_events']}")
    print(f"phase7_override_source_drawdown_event_log_path={drawdown_event_path}")
    print(f"phase7_override_source_drawdown_error_count={len(drawdown_errors)}")
    print(
        "phase7_override_valid_governance_probe_error_count="
        f"{len(valid_governance_errors)}"
    )
    print(
        "phase7_override_valid_manual_probe_error_count="
        f"{len(valid_manual_errors)}"
    )
    print(
        "phase7_override_valid_broker_probe_error_count="
        f"{len(valid_broker_errors)}"
    )
    print(
        "phase7_override_valid_unlinked_probe_error_count="
        f"{len(valid_unlinked_errors)}"
    )
    print(
        "phase7_override_valid_source_frozen_probe_error_count="
        f"{len(valid_source_frozen_errors)}"
    )
    print(
        "phase7_override_contamination_not_blocking_probe_error_count="
        f"{len(contamination_not_blocking_errors)}"
    )
    print(
        "phase7_override_contamination_not_frozen_probe_error_count="
        f"{len(contamination_not_frozen_errors)}"
    )
    print(
        "phase7_override_governance_contaminates_probe_error_count="
        f"{len(governance_contaminates_errors)}"
    )
    print(
        "phase7_override_manual_count_probe_error_count="
        f"{len(manual_count_errors)}"
    )
    print(
        "phase7_override_clean_with_override_count_probe_error_count="
        f"{len(clean_with_override_count_errors)}"
    )
    print(
        "phase7_override_proof_credit_probe_error_count="
        f"{len(proof_credit_errors)}"
    )
    print(
        "phase7_override_broker_post_probe_error_count="
        f"{len(broker_post_errors)}"
    )
    print(
        "phase7_override_live_capital_probe_error_count="
        f"{len(live_capital_errors)}"
    )
    print(
        "phase7_override_market_write_probe_error_count="
        f"{len(market_write_errors)}"
    )
    print(
        "phase7_override_manual_authority_probe_error_count="
        f"{len(manual_authority_errors)}"
    )
    print(
        "phase7_override_source_posture_probe_error_count="
        f"{len(source_posture_errors)}"
    )
    print(f"phase7_override_local_path_probe_error_count={len(local_path_errors)}")
    print(f"phase7_override_gate_probe_error_count={len(gate_errors)}")
    print(
        "phase7_override_next_stage_gate_probe_error_count="
        f"{len(next_stage_gate_errors)}"
    )
    print(f"phase7_override_next_stage={written['recommended_next_stage']}")
    print("phase7_override_boundary=" + written["boundary"])

    if drawdown_errors:
        errors.extend(drawdown_errors)
    if validation_errors:
        errors.extend(validation_errors)
    if runtime_copy.get("artifact_id") != written["artifact_id"]:
        errors.append("runtime_phase7_override_not_written")
    if written["status"] != "clean_no_overrides":
        errors.append("phase7_override_status_invalid")
    if written["stage_status"] != "override_detector_clean_no_interventions":
        errors.append("phase7_override_stage_status_invalid")
    if written["override_detection_write_allowed"] is not True:
        errors.append("phase7_override_write_authority_missing")
    if written["q7_13_signal_funnel_evidence_stage_allowed"] is not True:
        errors.append("phase7_override_q7_13_not_allowed")
    for count_key in (
        "override_count",
        "override_record_count",
        "manual_trade_level_override_count",
        "broker_side_intervention_count",
        "unlinked_lifecycle_record_count",
        "governance_feedback_trade_level_intervention_count",
        "paper_order_submitted_count",
        "proof_trade_created_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
        "unsafe_write_counter_total",
        "blocker_count",
    ):
        if written[count_key] != 0:
            errors.append(f"phase7_override_count_nonzero:{count_key}")
    for flag_key in (
        "sample_contaminated",
        "phase7_certification_blocked_by_override",
        "run_restart_required",
        "new_proof_trades_frozen",
        "phase7_proof_trade_execution_allowed",
        "phase7_proof_credit_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "manual_trade_level_override_allowed",
    ):
        if written[flag_key] is not False:
            errors.append(f"phase7_override_forbidden_or_unexpected:{flag_key}")
    if written["clean_sample"] is not True:
        errors.append("phase7_override_clean_sample_missing")
    if written["new_proof_order_staging_allowed"] is not True:
        errors.append("phase7_override_staging_not_allowed_without_contamination")
    if written["new_proof_trade_submission_allowed"] is not True:
        errors.append("phase7_override_submission_not_allowed_without_contamination")
    if written["governance_feedback_record_count"] != 3:
        errors.append("phase7_override_governance_record_count_invalid")
    if written["event_log_written"] is not True:
        errors.append("phase7_override_event_log_not_written")
    if replay["total_events"] != 1:
        errors.append("phase7_override_event_log_replay_count_mismatch")
    if valid_governance_errors:
        errors.append("valid_governance_probe_rejected")
    if valid_manual_errors:
        errors.append("valid_manual_override_probe_rejected")
    if valid_broker_errors:
        errors.append("valid_broker_intervention_probe_rejected")
    if valid_unlinked_errors:
        errors.append("valid_unlinked_lifecycle_probe_rejected")
    if valid_source_frozen_errors:
        errors.append("valid_source_frozen_probe_rejected")
    if "phase7_override_contamination_not_blocking_certification" not in (
        contamination_not_blocking_errors
    ):
        errors.append("contamination_not_blocking_probe_not_rejected")
    if "phase7_override_contamination_not_frozen" not in (
        contamination_not_frozen_errors
    ):
        errors.append("contamination_not_frozen_probe_not_rejected")
    if "phase7_override_governance_forbidden:sample_contaminating" not in (
        governance_contaminates_errors
    ):
        errors.append("governance_contaminates_probe_not_rejected")
    if "phase7_override_manual_count_mismatch" not in manual_count_errors:
        errors.append("manual_count_probe_not_rejected")
    if "phase7_override_manual_count_without_contamination" not in (
        clean_with_override_count_errors
    ):
        errors.append("clean_with_override_count_probe_not_rejected")
    if "phase7_override_authority_invalid:phase7_proof_credit_allowed" not in (
        proof_credit_errors
    ):
        errors.append("proof_credit_authority_probe_not_rejected")
    if "phase7_override_unsafe_count_nonzero:phase7_proof_credit_allowed_count" not in (
        proof_credit_errors
    ):
        errors.append("proof_credit_count_probe_not_rejected")
    if "phase7_override_authority_invalid:broker_post_allowed" not in (
        broker_post_errors
    ):
        errors.append("broker_post_authority_probe_not_rejected")
    if "phase7_override_count_nonzero:broker_post_called_count" not in (
        broker_post_errors
    ):
        errors.append("broker_post_count_probe_not_rejected")
    if "phase7_override_authority_invalid:live_capital_enabled" not in (
        live_capital_errors
    ):
        errors.append("live_capital_authority_probe_not_rejected")
    if "phase7_override_unsafe_count_nonzero:live_capital_enabled_count" not in (
        live_capital_errors
    ):
        errors.append("live_capital_count_probe_not_rejected")
    if "phase7_override_authority_invalid:prediction_market_write_allowed" not in (
        market_write_errors
    ):
        errors.append("prediction_market_authority_probe_not_rejected")
    if "phase7_override_authority_invalid:crypto_perps_write_allowed" not in (
        market_write_errors
    ):
        errors.append("crypto_perps_authority_probe_not_rejected")
    if "phase7_override_authority_invalid:manual_trade_level_override_allowed" not in (
        manual_authority_errors
    ):
        errors.append("manual_authority_probe_not_rejected")
    if "phase7_override_preference_quorum_credit_allowed" not in (
        source_posture_errors
    ):
        errors.append("source_posture_preference_probe_not_rejected")
    if "phase7_override_qctrl_role_invalid" not in source_posture_errors:
        errors.append("source_posture_qctrl_probe_not_rejected")
    if "phase7_override_provenance_local_path_leak" not in local_path_errors:
        errors.append("local_path_probe_not_rejected")
    if "q7_12_override_detector_not_allowed" not in gate_errors:
        errors.append("gate_probe_not_rejected")
    if "q7_13_signal_funnel_evidence_not_allowed" not in next_stage_gate_errors:
        errors.append("next_stage_gate_probe_not_rejected")

    if errors:
        for error in sorted(set(errors)):
            print(f"phase7_override_error={error}")
        print("phase7_override_detector_check=failed")
        return 1

    print("phase7_override_detector_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
