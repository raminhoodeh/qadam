#!/usr/bin/env python3
"""Validate Q7-9 Phase 7 Demo Proof postmortem contract."""

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
from orchestrator.phase6_postmortem_packets import (  # noqa: E402
    ALLOWED_ASSERTION_KINDS,
    ASSERTION_REQUIRED_FIELDS,
    POSTMORTEM_PACKET_SECTIONS,
)
from orchestrator.phase7_proof_lifecycle_monitor import (  # noqa: E402
    build_phase7_proof_lifecycle_monitor,
    validate_phase7_proof_lifecycle_monitor,
    write_phase7_proof_lifecycle_monitor,
)
from orchestrator.phase7_proof_postmortem_contract import (  # noqa: E402
    PHASE7_POSTMORTEM_DUE_WITHIN_HOURS,
    PHASE7_PROOF_POSTMORTEM_REQUIRED_CHECKS,
    PHASE7_PROOF_POSTMORTEM_SCHEMA_VERSION,
    build_phase7_proof_postmortem_contract,
    phase7_proof_postmortem_contract_paths,
    validate_phase7_proof_postmortem_contract,
    write_phase7_proof_postmortem_contract,
)


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _packet_payload(*, template_only: bool = True, cited: bool = True) -> dict[str, object]:
    sections: list[dict[str, object]] = []
    for section_key in POSTMORTEM_PACKET_SECTIONS:
        assertions = []
        if not template_only:
            source_refs = ["data/runtime/phase7_proof_lifecycle_monitor.json"] if cited else []
            assertions.append(
                {
                    "assertion_id": f"q7-postmortem:{section_key}:1",
                    "assertion_kind": (
                        "proposed_learning_action"
                        if section_key == "proposed_learning_actions"
                        else "evidence"
                    ),
                    "statement": (
                        f"{section_key} is cited to the Q7 lifecycle evidence or "
                        "must remain explicitly deferred."
                    ),
                    "source_refs": source_refs,
                    "is_hypothesis": False,
                    "hypothesis_reason": None,
                    "conclusion": section_key in {"thesis", "execution_read"},
                    "review_required": True,
                }
            )
        sections.append(
            {
                "section_key": section_key,
                "required": True,
                "assertions": assertions,
                "assertion_count": len(assertions),
                "source_refs_or_hypothesis_required": True,
                "uncited_conclusion_allowed": False,
                "minimum_assertion_count_for_submitted_packet": 1,
            }
        )
    return {
        "template_only": template_only,
        "packet_state": (
            "postmortem_due_template_not_submitted"
            if template_only
            else "postmortem_packet_submitted"
        ),
        "source_lifecycle_event_ref": "phase7:q7-8:proof-lifecycle:probe0001",
        "source_closed_trade_ref": "q7-closed-trade-probe0001",
        "source_setup_record_id": "probe:q7-setup",
        "source_auto_approval_decision_id": "probe:auto-approval:q7-setup",
        "source_staged_order_artifact_id": "phase7:q7-6:staged-proof-order:probe",
        "source_order_ref": "q7-paper-order-probe0001",
        "source_broker_receipt_ref": "q7-local-broker-receipt-probe0001",
        "narrative_only": False,
        "narrative_body": None,
        "sections": sections,
        "write_authority": False,
        "postmortem_approved": False,
        "learning_write_allowed": False,
        "learning_write_created": False,
        "knowledge_graph_write_created": False,
        "model_weight_update_created": False,
        "trust_score_update_created": False,
        "policy_mutation_created": False,
        "strategy_mutation_created": False,
        "phase7_proof_credit_allowed": False,
    }


def _valid_postmortem_record(
    *,
    submitted: bool = False,
    reviewed: bool = False,
    deferred: bool = False,
) -> dict[str, object]:
    checks = [
        {"name": name, "passed": True, "detail": None}
        for name in PHASE7_PROOF_POSTMORTEM_REQUIRED_CHECKS
    ]
    return {
        "schema_version": 1,
        "proof_postmortem_schema_version": PHASE7_PROOF_POSTMORTEM_SCHEMA_VERSION,
        "artifact_type": "proof_postmortem_packet",
        "artifact_id": "phase7:q7-9:proof-postmortem:q7_closed_trade_probe0001",
        "phase": "Q7",
        "stage": "Q7-9",
        "status": "postmortem_due",
        "generated_at": "2026-05-25T00:00:00+00:00",
        "public_safe": True,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "postmortem_state": "postmortem_due",
        "source_q7_8_artifact_id": "phase7:q7-8:proof-lifecycle:probe0001",
        "source_lifecycle_event_ref": "phase7:q7-8:proof-lifecycle:probe0001",
        "source_closed_trade_ref": "q7-closed-trade-probe0001",
        "source_setup_record_id": "probe:q7-setup",
        "source_auto_approval_decision_id": "probe:auto-approval:q7-setup",
        "source_staged_order_artifact_id": "phase7:q7-6:staged-proof-order:probe",
        "source_submitted_order_ref": "q7-paper-order-probe0001",
        "source_broker_receipt_ref": "q7-local-broker-receipt-probe0001",
        "idempotency_key": "q7-6-stage-probe0001",
        "idempotency_namespace": "phase7_demo_proof",
        "postmortem_due_marker_created": True,
        "postmortem_due_at": "2026-05-25T00:00:00+00:00",
        "postmortem_due_by": "2026-05-26T00:00:00+00:00",
        "postmortem_due_within_hours": PHASE7_POSTMORTEM_DUE_WITHIN_HOURS,
        "postmortem_packet_required": True,
        "postmortem_packet_template_created": True,
        "postmortem_packet_submitted": submitted,
        "postmortem_reviewed": reviewed,
        "postmortem_explicitly_deferred": deferred,
        "postmortem_late": False,
        "postmortem_missing": False,
        "postmortem_coverage_state": "due_marker_created_packet_pending",
        "certification_blocked_by_missing_postmortem": False,
        "packet_payload": _packet_payload(template_only=not submitted),
        "packet_section_count": len(POSTMORTEM_PACKET_SECTIONS),
        "required_section_count": len(POSTMORTEM_PACKET_SECTIONS),
        "assertion_source_refs_required": True,
        "uncited_conclusion_allowed": False,
        "narrative_only_allowed": False,
        "review_required": True,
        "deferred_review_allowed_with_explicit_reason": True,
        "postmortem_approved": False,
        "learning_write_allowed": False,
        "learning_write_created": False,
        "knowledge_graph_write_created": False,
        "model_weight_update_created": False,
        "trust_score_update_created": False,
        "policy_mutation_created": False,
        "strategy_mutation_created": False,
        "phase7_proof_credit_allowed": False,
        "proof_trade_credit_count": 0,
        "broker_post_called": False,
        "broker_post_called_count": 0,
        "alpaca_post_called": False,
        "alpaca_post_called_count": 0,
        "external_broker_post_performed": False,
        "broker_write_allowed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
        "prediction_market_write_allowed": False,
        "crypto_perps_write_allowed": False,
        "manual_trade_level_override_allowed": False,
        "secret_value_exposed": False,
        "raw_payload_exposed": False,
        "local_path_exposed": False,
        "authorization_header_exposed": False,
        "broker_order_identifier_exposed": False,
        "required_checks": list(PHASE7_PROOF_POSTMORTEM_REQUIRED_CHECKS),
        "required_check_count": len(PHASE7_PROOF_POSTMORTEM_REQUIRED_CHECKS),
        "checks": checks,
        "failed_checks": [],
        "failed_check_count": 0,
        "blocked_reasons": [],
        "blocked_reason_count": 0,
    }


def _with_postmortem_records(
    artifact: dict[str, object],
    records: list[dict[str, object]],
    *,
    closed_trade_count: int | None = None,
) -> dict[str, object]:
    probe = deepcopy(artifact)
    due_records = [
        record for record in records if record.get("postmortem_due_marker_created") is True
    ]
    template_records = [
        record
        for record in due_records
        if record.get("postmortem_packet_template_created") is True
    ]
    submitted_records = [
        record for record in records if record.get("postmortem_packet_submitted") is True
    ]
    reviewed_records = [
        record for record in records if record.get("postmortem_reviewed") is True
    ]
    deferred_records = [
        record
        for record in records
        if record.get("postmortem_explicitly_deferred") is True
    ]
    late_records = [record for record in records if record.get("postmortem_late") is True]
    missing_records = [
        record for record in records if record.get("postmortem_missing") is True
    ]
    source_closed_count = closed_trade_count if closed_trade_count is not None else len(records)
    missing_coverage_count = max(0, source_closed_count - len(due_records)) + len(
        missing_records
    )
    probe["status"] = (
        "blocked_missing_postmortem_coverage"
        if missing_coverage_count
        else "postmortem_due_markers_recorded"
    )
    probe["stage_status"] = (
        "proof_postmortem_missing_coverage"
        if missing_coverage_count
        else "proof_postmortem_due_markers_recorded"
    )
    probe["source_lifecycle_status"] = "proof_lifecycle_events_recorded"
    probe["source_proof_trade_count"] = source_closed_count
    probe["source_closed_proof_trade_count"] = source_closed_count
    probe["source_lifecycle_event_count"] = source_closed_count
    probe["postmortem_records"] = records
    probe["postmortem_due_records"] = due_records
    probe["postmortem_packet_template_records"] = template_records
    probe["postmortem_packet_submitted_records"] = submitted_records
    probe["postmortem_reviewed_records"] = reviewed_records
    probe["postmortem_explicitly_deferred_records"] = deferred_records
    probe["postmortem_late_records"] = late_records
    probe["postmortem_missing_records"] = missing_records
    probe["postmortem_record_count"] = len(records)
    probe["postmortem_due_count"] = len(due_records)
    probe["postmortem_due_marker_created_count"] = len(due_records)
    probe["postmortem_packet_required_count"] = source_closed_count
    probe["postmortem_packet_template_count"] = len(template_records)
    probe["postmortem_packet_submitted_count"] = len(submitted_records)
    probe["postmortem_reviewed_count"] = len(reviewed_records)
    probe["postmortem_explicitly_deferred_count"] = len(deferred_records)
    probe["postmortem_late_count"] = len(late_records)
    probe["postmortem_missing_count"] = len(missing_records)
    probe["closed_trade_without_postmortem_coverage_count"] = missing_coverage_count
    probe["phase7_certification_blocked_by_missing_postmortem"] = (
        missing_coverage_count > 0
    )
    probe["proof_trade_created_count"] = source_closed_count
    return probe


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = phase7_proof_postmortem_contract_paths(
        settings
    )
    if event_log_path.exists():
        event_log_path.unlink()

    lifecycle = build_phase7_proof_lifecycle_monitor(settings=settings)
    _, _, lifecycle_event_path, lifecycle_written = write_phase7_proof_lifecycle_monitor(
        lifecycle,
        settings=settings,
        record_event=True,
    )
    lifecycle_errors = validate_phase7_proof_lifecycle_monitor(lifecycle_written)
    artifact = build_phase7_proof_postmortem_contract(settings=settings)
    output_path, history_path, event_log_path, written = (
        write_phase7_proof_postmortem_contract(
            artifact,
            settings=settings,
            record_event=True,
            event_log_path=event_log_path,
        )
    )
    validation_errors = validate_phase7_proof_postmortem_contract(written)
    replay = EventLog(event_log_path, echo=False).replay()
    runtime_copy = _read_json(output_path)

    valid_due_probe = _with_postmortem_records(written, [_valid_postmortem_record()])
    valid_due_errors = validate_phase7_proof_postmortem_contract(valid_due_probe)

    valid_reviewed_probe = _with_postmortem_records(
        written,
        [_valid_postmortem_record(submitted=True, reviewed=True)],
    )
    valid_reviewed_errors = validate_phase7_proof_postmortem_contract(
        valid_reviewed_probe
    )

    valid_deferred_probe = _with_postmortem_records(
        written,
        [_valid_postmortem_record(submitted=True, deferred=True)],
    )
    valid_deferred_errors = validate_phase7_proof_postmortem_contract(
        valid_deferred_probe
    )

    missing_due_probe = _with_postmortem_records(written, [], closed_trade_count=1)
    missing_due_errors = validate_phase7_proof_postmortem_contract(missing_due_probe)

    late_record = _valid_postmortem_record()
    late_record["postmortem_late"] = True
    late_probe = _with_postmortem_records(written, [late_record])
    late_probe["postmortem_late_count"] = 0
    late_errors = validate_phase7_proof_postmortem_contract(late_probe)

    narrative_probe = _with_postmortem_records(written, [_valid_postmortem_record()])
    narrative_probe["postmortem_records"][0]["packet_payload"]["narrative_only"] = True
    narrative_errors = validate_phase7_proof_postmortem_contract(narrative_probe)

    uncited_probe = _with_postmortem_records(
        written,
        [_valid_postmortem_record(submitted=True)],
    )
    uncited_probe["postmortem_records"][0]["packet_payload"] = _packet_payload(
        template_only=False,
        cited=False,
    )
    uncited_errors = validate_phase7_proof_postmortem_contract(uncited_probe)

    approval_probe = _with_postmortem_records(written, [_valid_postmortem_record()])
    approval_probe["postmortem_records"][0]["postmortem_approved"] = True
    approval_errors = validate_phase7_proof_postmortem_contract(approval_probe)

    learning_probe = deepcopy(written)
    learning_probe["learning_write_created"] = True
    learning_probe["knowledge_graph_write_created"] = True
    learning_errors = validate_phase7_proof_postmortem_contract(learning_probe)

    proof_credit_probe = deepcopy(written)
    proof_credit_probe["phase7_proof_credit_allowed"] = True
    proof_credit_probe["authority_ledger"]["phase7_proof_credit_allowed"] = True
    proof_credit_probe["phase7_proof_credit_allowed_count"] = 1
    proof_credit_errors = validate_phase7_proof_postmortem_contract(proof_credit_probe)

    broker_post_probe = deepcopy(written)
    broker_post_probe["broker_post_allowed"] = True
    broker_post_probe["authority_ledger"]["broker_post_allowed"] = True
    broker_post_probe["broker_post_called_count"] = 1
    broker_post_errors = validate_phase7_proof_postmortem_contract(broker_post_probe)

    live_capital_probe = deepcopy(written)
    live_capital_probe["live_capital_enabled"] = True
    live_capital_probe["authority_ledger"]["live_capital_enabled"] = True
    live_capital_probe["live_capital_enabled_count"] = 1
    live_capital_errors = validate_phase7_proof_postmortem_contract(live_capital_probe)

    market_write_probe = deepcopy(written)
    market_write_probe["prediction_market_write_allowed"] = True
    market_write_probe["authority_ledger"]["prediction_market_write_allowed"] = True
    market_write_probe["prediction_market_write_allowed_count"] = 1
    market_write_probe["crypto_perps_write_allowed"] = True
    market_write_probe["authority_ledger"]["crypto_perps_write_allowed"] = True
    market_write_probe["crypto_perps_write_allowed_count"] = 1
    market_write_errors = validate_phase7_proof_postmortem_contract(market_write_probe)

    manual_override_probe = deepcopy(written)
    manual_override_probe["manual_trade_level_override_allowed"] = True
    manual_override_probe["authority_ledger"][
        "manual_trade_level_override_allowed"
    ] = True
    manual_override_probe["manual_trade_level_override_count"] = 1
    manual_override_errors = validate_phase7_proof_postmortem_contract(
        manual_override_probe
    )

    source_posture_probe = deepcopy(written)
    source_posture_probe["source_posture"][
        "preference_mcp_source_quorum_credit_allowed"
    ] = True
    source_posture_probe["source_posture"]["qctrl_role"] = "execution_truth"
    source_posture_errors = validate_phase7_proof_postmortem_contract(
        source_posture_probe
    )

    local_path_probe = deepcopy(written)
    local_path_probe["provenance"]["source_refs"] = [
        "/Users/raminhoodeh/Desktop/qadam/data/runtime/private.json"
    ]
    local_path_errors = validate_phase7_proof_postmortem_contract(local_path_probe)

    gate_probe = deepcopy(written)
    gate_probe["q7_9_proof_postmortem_contract_stage_allowed"] = False
    gate_errors = validate_phase7_proof_postmortem_contract(gate_probe)

    assertion_field_probe = deepcopy(written)
    assertion_field_probe["assertion_required_fields"] = list(ASSERTION_REQUIRED_FIELDS[:-1])
    assertion_field_errors = validate_phase7_proof_postmortem_contract(
        assertion_field_probe
    )

    print(f"phase7_postmortem_status={written['status']}")
    print(f"phase7_postmortem_stage_status={written['stage_status']}")
    print(
        "phase7_postmortem_schema_version="
        f"{PHASE7_PROOF_POSTMORTEM_SCHEMA_VERSION}"
    )
    print(f"phase7_postmortem_artifact_path={output_path}")
    print(f"phase7_postmortem_history_path={history_path}")
    print(f"phase7_postmortem_event_log_path={event_log_path}")
    print(f"phase7_postmortem_source_lifecycle_status={written['source_lifecycle_status']}")
    print(f"phase7_postmortem_q7_10_performance_stage_allowed={written['q7_10_performance_evaluator_stage_allowed']}")
    print(f"phase7_postmortem_write_allowed={written['phase7_postmortem_write_allowed']}")
    print(f"phase7_postmortem_source_closed_proof_trade_count={written['source_closed_proof_trade_count']}")
    print(f"phase7_postmortem_record_count={written['postmortem_record_count']}")
    print(f"phase7_postmortem_due_count={written['postmortem_due_count']}")
    print(f"phase7_postmortem_due_marker_created_count={written['postmortem_due_marker_created_count']}")
    print(f"phase7_postmortem_packet_required_count={written['postmortem_packet_required_count']}")
    print(f"phase7_postmortem_packet_template_count={written['postmortem_packet_template_count']}")
    print(f"phase7_postmortem_packet_submitted_count={written['postmortem_packet_submitted_count']}")
    print(f"phase7_postmortem_reviewed_count={written['postmortem_reviewed_count']}")
    print(f"phase7_postmortem_explicitly_deferred_count={written['postmortem_explicitly_deferred_count']}")
    print(f"phase7_postmortem_late_count={written['postmortem_late_count']}")
    print(f"phase7_postmortem_missing_count={written['postmortem_missing_count']}")
    print(f"phase7_postmortem_missing_coverage_count={written['closed_trade_without_postmortem_coverage_count']}")
    print(f"phase7_postmortem_phase7_proof_credit_allowed={written['phase7_proof_credit_allowed']}")
    print(f"phase7_postmortem_live_capital_enabled={written['live_capital_enabled']}")
    print(f"phase7_postmortem_broker_post_called_count={written['broker_post_called_count']}")
    print(f"phase7_postmortem_alpaca_post_called_count={written['alpaca_post_called_count']}")
    print(f"phase7_postmortem_unsafe_write_counter_total={written['unsafe_write_counter_total']}")
    print(f"phase7_postmortem_blocker_count={written['blocker_count']}")
    print(f"phase7_postmortem_event_log_replay_total_events={replay['total_events']}")
    print(f"phase7_postmortem_lifecycle_event_log_path={lifecycle_event_path}")
    print(f"phase7_postmortem_lifecycle_error_count={len(lifecycle_errors)}")
    print(f"phase7_postmortem_packet_section_count={written['packet_section_count']}")
    print(f"phase7_postmortem_allowed_assertion_kind_count={len(ALLOWED_ASSERTION_KINDS)}")
    print(f"phase7_postmortem_valid_due_probe_error_count={len(valid_due_errors)}")
    print(f"phase7_postmortem_valid_reviewed_probe_error_count={len(valid_reviewed_errors)}")
    print(f"phase7_postmortem_valid_deferred_probe_error_count={len(valid_deferred_errors)}")
    print(f"phase7_postmortem_missing_due_probe_error_count={len(missing_due_errors)}")
    print(f"phase7_postmortem_late_probe_error_count={len(late_errors)}")
    print(f"phase7_postmortem_narrative_probe_error_count={len(narrative_errors)}")
    print(f"phase7_postmortem_uncited_probe_error_count={len(uncited_errors)}")
    print(f"phase7_postmortem_approval_probe_error_count={len(approval_errors)}")
    print(f"phase7_postmortem_learning_probe_error_count={len(learning_errors)}")
    print(f"phase7_postmortem_proof_credit_probe_error_count={len(proof_credit_errors)}")
    print(f"phase7_postmortem_broker_post_probe_error_count={len(broker_post_errors)}")
    print(f"phase7_postmortem_live_capital_probe_error_count={len(live_capital_errors)}")
    print(f"phase7_postmortem_market_write_probe_error_count={len(market_write_errors)}")
    print(f"phase7_postmortem_manual_override_probe_error_count={len(manual_override_errors)}")
    print(f"phase7_postmortem_source_posture_probe_error_count={len(source_posture_errors)}")
    print(f"phase7_postmortem_local_path_probe_error_count={len(local_path_errors)}")
    print(f"phase7_postmortem_gate_probe_error_count={len(gate_errors)}")
    print(f"phase7_postmortem_assertion_field_probe_error_count={len(assertion_field_errors)}")
    print(f"phase7_postmortem_next_stage={written['recommended_next_stage']}")
    print("phase7_postmortem_boundary=" + written["boundary"])

    if lifecycle_errors:
        errors.extend(lifecycle_errors)
    if validation_errors:
        errors.extend(validation_errors)
    if runtime_copy.get("artifact_id") != written["artifact_id"]:
        errors.append("runtime_phase7_postmortem_not_written")
    if written["status"] != "ready_no_closed_trades":
        errors.append("phase7_postmortem_status_invalid")
    if written["stage_status"] != "proof_postmortem_contract_ready_no_closed_trades":
        errors.append("phase7_postmortem_stage_status_invalid")
    if written["phase7_postmortem_write_allowed"] is not True:
        errors.append("phase7_postmortem_write_authority_missing")
    if written["q7_10_performance_evaluator_stage_allowed"] is not True:
        errors.append("phase7_postmortem_q7_10_not_allowed")
    for count_key in (
        "source_closed_proof_trade_count",
        "postmortem_record_count",
        "postmortem_due_count",
        "postmortem_due_marker_created_count",
        "postmortem_packet_required_count",
        "postmortem_packet_template_count",
        "postmortem_packet_submitted_count",
        "postmortem_reviewed_count",
        "postmortem_explicitly_deferred_count",
        "postmortem_late_count",
        "postmortem_missing_count",
        "closed_trade_without_postmortem_coverage_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
        "unsafe_write_counter_total",
        "blocker_count",
    ):
        if written[count_key] != 0:
            errors.append(f"phase7_postmortem_count_nonzero:{count_key}")
    for flag_key in (
        "phase7_proof_trade_execution_allowed",
        "phase7_performance_evaluation_write_allowed",
        "phase7_proof_credit_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "manual_trade_level_override_allowed",
        "postmortem_approved",
        "learning_write_created",
        "knowledge_graph_write_created",
    ):
        if written[flag_key] is not False:
            errors.append(f"phase7_postmortem_forbidden_authority:{flag_key}")
    if written["packet_section_count"] != len(POSTMORTEM_PACKET_SECTIONS):
        errors.append("phase7_postmortem_packet_section_count_invalid")
    if written["event_log_written"] is not True:
        errors.append("phase7_postmortem_event_log_not_written")
    if replay["total_events"] != 1:
        errors.append("phase7_postmortem_event_log_replay_count_mismatch")
    if valid_due_errors:
        errors.append("valid_due_postmortem_probe_rejected")
    if valid_reviewed_errors:
        errors.append("valid_reviewed_postmortem_probe_rejected")
    if valid_deferred_errors:
        errors.append("valid_deferred_postmortem_probe_rejected")
    if "phase7_postmortem_due_count_not_equal_closed_trade_count" not in (
        missing_due_errors
    ):
        errors.append("missing_due_probe_not_rejected")
    if "phase7_postmortem_late_count_mismatch" not in late_errors:
        errors.append("late_probe_not_rejected")
    if (
        "phase7_postmortem_packet:phase7_postmortem_narrative_only_packet"
        not in narrative_errors
    ):
        errors.append("narrative_only_probe_not_rejected")
    if not any("phase7_postmortem_packet_assertion_source_refs_missing" in error for error in uncited_errors):
        errors.append("uncited_source_probe_not_rejected")
    if "phase7_postmortem_record_approved" not in approval_errors:
        errors.append("approval_probe_not_rejected")
    if "phase7_postmortem_contract_write_enabled:learning_write_created" not in (
        learning_errors
    ):
        errors.append("learning_write_probe_not_rejected")
    if "phase7_postmortem_contract_write_enabled:knowledge_graph_write_created" not in (
        learning_errors
    ):
        errors.append("knowledge_graph_probe_not_rejected")
    if "phase7_postmortem_authority_invalid:phase7_proof_credit_allowed" not in (
        proof_credit_errors
    ):
        errors.append("proof_credit_authority_probe_not_rejected")
    if "phase7_postmortem_unsafe_count_nonzero:phase7_proof_credit_allowed_count" not in (
        proof_credit_errors
    ):
        errors.append("proof_credit_count_probe_not_rejected")
    if "phase7_postmortem_authority_invalid:broker_post_allowed" not in (
        broker_post_errors
    ):
        errors.append("broker_post_authority_probe_not_rejected")
    if "phase7_postmortem_count_nonzero:broker_post_called_count" not in (
        broker_post_errors
    ):
        errors.append("broker_post_count_probe_not_rejected")
    if "phase7_postmortem_authority_invalid:live_capital_enabled" not in (
        live_capital_errors
    ):
        errors.append("live_capital_authority_probe_not_rejected")
    if "phase7_postmortem_unsafe_count_nonzero:live_capital_enabled_count" not in (
        live_capital_errors
    ):
        errors.append("live_capital_count_probe_not_rejected")
    if "phase7_postmortem_authority_invalid:prediction_market_write_allowed" not in (
        market_write_errors
    ):
        errors.append("prediction_market_authority_probe_not_rejected")
    if "phase7_postmortem_authority_invalid:crypto_perps_write_allowed" not in (
        market_write_errors
    ):
        errors.append("crypto_perps_authority_probe_not_rejected")
    if "phase7_postmortem_authority_invalid:manual_trade_level_override_allowed" not in (
        manual_override_errors
    ):
        errors.append("manual_override_authority_probe_not_rejected")
    if "phase7_postmortem_preference_quorum_credit_allowed" not in source_posture_errors:
        errors.append("source_posture_preference_probe_not_rejected")
    if "phase7_postmortem_qctrl_role_invalid" not in source_posture_errors:
        errors.append("source_posture_qctrl_probe_not_rejected")
    if "phase7_postmortem_provenance_local_path_leak" not in local_path_errors:
        errors.append("local_path_probe_not_rejected")
    if "q7_9_proof_postmortem_contract_not_allowed" not in gate_errors:
        errors.append("gate_probe_not_rejected")
    if "phase7_postmortem_assertion_required_fields_mismatch" not in (
        assertion_field_errors
    ):
        errors.append("assertion_field_probe_not_rejected")

    if errors:
        for error in sorted(set(errors)):
            print(f"phase7_postmortem_error={error}")
        print("phase7_proof_postmortem_contract_check=failed")
        return 1

    print("phase7_proof_postmortem_contract_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
