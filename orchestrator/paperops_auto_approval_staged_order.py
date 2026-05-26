"""PT-4 guarded auto-approval and staged paper-order handoff.

PT-4 consumes PT-3 production-qualified setup records and creates the narrow
paper-only auto-approval plus staged-order handoff for PaperOps. It does not
submit to Alpaca, call brokers, mutate Q7 source artifacts, force trades, grant
proof credit, or enable live capital.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.paperops_qualified_setup_production import (
    read_latest_paperops_qualified_setup_production,
    validate_paperops_qualified_setup_production,
)


PAPEROPS_AUTO_APPROVAL_STAGED_ORDER_SCHEMA_VERSION = 1
PAPEROPS_AUTO_APPROVAL_STAGED_ORDER_RUNTIME_ARTIFACT = (
    "paperops_auto_approval_staged_order.json"
)
PAPEROPS_AUTO_APPROVAL_STAGED_ORDER_HISTORY = (
    "paperops_auto_approval_staged_order_history.jsonl"
)
PAPEROPS_AUTO_APPROVAL_STAGED_ORDER_EVENT_LOG = (
    "paperops_auto_approval_staged_order_events.jsonl"
)
PAPEROPS_AUTO_APPROVAL_STAGED_ORDER_EVENT_TYPE = (
    "paperops_auto_approval_staged_order_recorded"
)
PAPEROPS_AUTO_APPROVAL_STAGED_ORDER_COMPONENT = (
    "paperops_auto_approval_staged_order"
)

PAPEROPS_AUTO_APPROVAL_STAGED_ORDER_BOUNDARY = (
    "PT-4 consumes PT-3 production-qualified setups and records a guarded "
    "paper-only auto-approval plus staged paper-order handoff. It can auto-"
    "approve only after the PT-3 production gates pass, and it can stage only "
    "a paper order with deterministic idempotency, Event Log prewrite, and a "
    "pre-trade snapshot. It cannot mutate the Q7 source ledger, cannot submit "
    "paper orders, cannot call brokers, cannot call live endpoints, cannot "
    "force trades, cannot grant Phase 7 proof credit, cannot expose secrets, "
    "and cannot enable live capital."
)

PAPEROPS_AUTO_APPROVAL_STAGED_ORDER_PUBLIC_FIELDS: tuple[str, ...] = (
    "schema_version",
    "artifact_type",
    "artifact_id",
    "phase",
    "stage",
    "status",
    "generated_at",
    "public_safe",
    "mode",
    "source_pt3_status",
    "source_pt3_path_ready",
    "source_pt3_candidate_count",
    "source_pt3_qualified_setup_count",
    "source_pt3_ready_to_stage_q7_order",
    "source_pt3_q7_ledger_count",
    "qctrl_consultation_required_for_full_parity",
    "qctrl_paper_consultation_status",
    "qctrl_paper_consultation_connected",
    "qctrl_consultation_blocker",
    "auto_approval_policy",
    "auto_approval_record_count",
    "auto_approved_setup_count",
    "auto_approval_blocked_count",
    "staging_decision_record_count",
    "staged_order_count",
    "blocked_staged_order_count",
    "ready_for_paperops2_submit",
    "idempotency_namespace",
    "idempotency_key_count",
    "duplicate_idempotency_key_count",
    "event_log_prewrite_ready_count",
    "event_log_prewrite_written_count",
    "pre_trade_snapshot_present_count",
    "auto_approval_records",
    "staged_order_records",
    "q7_source_ledger_mutation_performed",
    "q7_auto_approval_artifact_mutation_performed",
    "q7_staging_artifact_mutation_performed",
    "paper_order_submission_allowed",
    "broker_post_allowed",
    "alpaca_post_allowed",
    "live_endpoint_allowed",
    "live_capital_enabled",
    "qctrl_direct_execution_allowed",
    "qctrl_broker_post_allowed",
    "phase7_proof_credit_allowed",
    "forced_trades_allowed",
    "manual_trade_level_override_allowed",
    "broker_post_called_count",
    "alpaca_post_called_count",
    "live_endpoint_called_count",
    "qctrl_broker_post_called_count",
    "qctrl_live_endpoint_called_count",
    "phase7_proof_credit_granted_count",
    "forced_trade_count",
    "secret_value_exposed_count",
    "raw_payload_exposed_count",
    "unsafe_write_counter_total",
    "blockers",
    "blocker_count",
    "next_required_action",
    "boundary",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _safe_key(value: str) -> str:
    output = []
    for char in value.lower():
        if char.isalnum() or char in {"_", "-"}:
            output.append(char)
        else:
            output.append("_")
    return "".join(output).strip("_") or "unknown"


def _hash_payload(payload: dict[str, Any]) -> str:
    return sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def _duplicate_count(values: list[str]) -> int:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return len(duplicates)


def _gate_pass(candidate: dict[str, Any], gate_key: str) -> bool:
    return any(
        gate.get("gate_key") == gate_key and gate.get("passed") is True
        for gate in candidate.get("gate_results", [])
        if isinstance(gate, dict)
    )


def paperops_auto_approval_staged_order_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PAPEROPS_AUTO_APPROVAL_STAGED_ORDER_RUNTIME_ARTIFACT,
        runtime / PAPEROPS_AUTO_APPROVAL_STAGED_ORDER_HISTORY,
        runtime / PAPEROPS_AUTO_APPROVAL_STAGED_ORDER_EVENT_LOG,
    )


def read_latest_paperops_auto_approval_staged_order(
    settings: Settings | None = None,
) -> dict[str, Any]:
    output_path, _, _ = paperops_auto_approval_staged_order_paths(settings)
    return _read_json(output_path)


def _auto_approval_policy() -> dict[str, Any]:
    return {
        "policy_schema_version": PAPEROPS_AUTO_APPROVAL_STAGED_ORDER_SCHEMA_VERSION,
        "approval_mode": "paperops_test_mode_auto_approval",
        "pt3_production_qualified_setup_required": True,
        "all_pt3_production_gates_required": True,
        "fund_manager_trade_level_approval_required": False,
        "manual_trade_level_override_allowed": False,
        "governance_feedback_affects_future_policy_only": True,
        "qctrl_consultation_required_for_full_parity": True,
        "qctrl_direct_execution_allowed": False,
        "paper_order_staging_allowed": True,
        "paper_order_submission_allowed": False,
        "broker_post_allowed": False,
        "live_endpoint_allowed": False,
        "proof_trade_creation_allowed": False,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
    }


def _source_snapshot(settings: Settings) -> dict[str, dict[str, Any]]:
    runtime = _runtime_dir(settings)
    return {
        "pt3": read_latest_paperops_qualified_setup_production(settings),
        "paper_operational_mode": _read_json(runtime / "paper_operational_mode.json"),
        "phase7_demo_run": _read_json(runtime / "phase7_demo_proof_run.json"),
    }


def _source_blockers(pt3: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not pt3:
        blockers.append("pt3_artifact_missing")
        return blockers
    validation_errors = validate_paperops_qualified_setup_production(pt3)
    if validation_errors:
        blockers.append("pt3_validation_errors")
    if pt3.get("recorded") is not True:
        blockers.append("pt3_not_recorded")
    if pt3.get("status") not in {
        "production_path_ready_with_qualified_setup",
        "production_path_ready_no_current_qualified_setup",
    }:
        blockers.append("pt3_status_not_ready")
    if pt3.get("qualified_setup_production_path_ready") is not True:
        blockers.append("pt3_path_not_ready")
    if pt3.get("paper_operational_mode_effective") is not True:
        blockers.append("paper_operational_mode_not_effective")
    if pt3.get("phase7_run_state") != "active":
        blockers.append("phase7_run_not_active")
    for key in (
        "paper_order_submission_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "qctrl_direct_execution_allowed",
        "phase7_proof_credit_allowed",
        "forced_trades_allowed",
        "manual_trade_level_override_allowed",
        "qualified_setup_creation_forced",
        "source_quorum_bypass_allowed",
        "supplemental_source_bypass_allowed",
    ):
        if pt3.get(key) is not False:
            blockers.append(f"pt3_forbidden:{key}")
    for key in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "live_endpoint_called_count",
        "qctrl_broker_post_called_count",
        "qctrl_live_endpoint_called_count",
        "phase7_proof_credit_granted_count",
        "forced_trade_count",
        "unsafe_write_counter_total",
    ):
        if _int(pt3.get(key)) != 0:
            blockers.append(f"pt3_unsafe_counter_nonzero:{key}")
    return sorted(set(blockers))


def _auto_approval_record(
    candidate: dict[str, Any],
    *,
    source_ready: bool,
) -> dict[str, Any]:
    setup_id = str(candidate.get("setup_record_id") or "unknown")
    all_required_gates_passed = candidate.get("all_required_gates_passed") is True
    required_gate_pass_count = sum(
        1
        for gate in candidate.get("gate_results", [])
        if isinstance(gate, dict) and gate.get("passed") is True
    )
    source_quorum_passed = candidate.get("source_quorum_passed") is True
    signal_integrity_passed = candidate.get("signal_integrity_passed") is True
    risk_gate_passed = candidate.get("risk_paper_sizing_passed") is True
    kill_switches_clear = candidate.get("kill_switches_clear") is True
    execution_ready = _gate_pass(candidate, "execution_adapter_read_ready")
    venue_ready = _gate_pass(candidate, "venue_read_available")
    broker_write_blocked = _gate_pass(candidate, "broker_write_blocked")
    safety_boundaries = _gate_pass(candidate, "phase7_safety_boundaries")
    rejection_reasons = list(candidate.get("rejection_reasons", []) or [])
    if candidate.get("qualified_setup") is not True:
        rejection_reasons.append("pt3_candidate_not_qualified")
    if not source_ready:
        rejection_reasons.append("pt3_source_not_ready")
    if not all_required_gates_passed:
        rejection_reasons.append("pt3_required_gates_not_passed")
    if not source_quorum_passed:
        rejection_reasons.append("source_quorum_not_passed")
    if not signal_integrity_passed:
        rejection_reasons.append("signal_integrity_not_passed")
    if not risk_gate_passed:
        rejection_reasons.append("risk_paper_sizing_not_passed")
    if not kill_switches_clear:
        rejection_reasons.append("kill_switches_not_clear")
    if not execution_ready:
        rejection_reasons.append("execution_adapter_not_read_ready")
    if not venue_ready:
        rejection_reasons.append("venue_not_read_available")
    if not broker_write_blocked:
        rejection_reasons.append("broker_write_not_blocked")
    if not safety_boundaries:
        rejection_reasons.append("phase7_safety_boundaries_not_preserved")
    if candidate.get("phase5_lifecycle_counts_as_q7_proof") is not False:
        rejection_reasons.append("phase5_lifecycle_counts_as_q7_proof")
    if candidate.get("proof_credit_allowed") is not False:
        rejection_reasons.append("proof_credit_allowed")
    auto_approved = not sorted(set(rejection_reasons))
    return {
        "schema_version": PAPEROPS_AUTO_APPROVAL_STAGED_ORDER_SCHEMA_VERSION,
        "record_type": "paperops_auto_approval_decision",
        "auto_approval_decision_id": (
            f"paperops:pt-4:auto-approval:{_safe_key(setup_id)}"
        ),
        "source_setup_record_id": setup_id,
        "source_pt3_candidate_state": candidate.get("setup_state"),
        "source_phase": "PT-3",
        "original_source_phase": candidate.get("source_phase"),
        "strategy_family_key": candidate.get("strategy_family_key"),
        "instrument": candidate.get("instrument"),
        "selected_venue": candidate.get("selected_venue"),
        "side": candidate.get("side"),
        "quantity": _float(candidate.get("quantity")),
        "order_type": candidate.get("order_type"),
        "time_in_force": candidate.get("time_in_force"),
        "notional_gbp": _float(candidate.get("notional_gbp")),
        "risk_gbp": _float(candidate.get("risk_gbp")),
        "approval_mode": "paperops_test_mode_auto_approval",
        "approval_state": "auto_approved" if auto_approved else "blocked",
        "auto_approved": auto_approved,
        "auto_approval_blocked": not auto_approved,
        "qualified_setup": candidate.get("qualified_setup") is True,
        "eligible_setup": candidate.get("eligible_setup") is True,
        "all_required_gates_passed": all_required_gates_passed,
        "source_quorum_passed": source_quorum_passed,
        "signal_integrity_passed": signal_integrity_passed,
        "risk_gate_passed": risk_gate_passed,
        "execution_adapter_read_ready": execution_ready,
        "venue_read_available": venue_ready,
        "kill_switches_clear": kill_switches_clear,
        "broker_write_blocked": broker_write_blocked,
        "phase7_safety_boundaries_preserved": safety_boundaries,
        "passed_required_gate_count": required_gate_pass_count,
        "required_gate_count": len(candidate.get("gate_results", []) or []),
        "gate_results": deepcopy(candidate.get("gate_results", []) or []),
        "rejection_reasons": sorted(set(rejection_reasons)),
        "fund_manager_trade_level_approval_required": False,
        "fund_manager_trade_level_approval_recorded": False,
        "manual_trade_level_override_attempted": False,
        "governance_feedback_channel": "future_policy_only",
        "phase5_lifecycle_counts_as_q7_proof": False,
        "proof_order_staging_allowed": auto_approved,
        "paper_order_submission_allowed": False,
        "proof_trade_creation_allowed": False,
        "proof_credit_allowed": False,
        "broker_post_allowed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
    }


def _approval_records(pt3: dict[str, Any], *, source_ready: bool) -> list[dict[str, Any]]:
    return [
        _auto_approval_record(candidate, source_ready=source_ready)
        for candidate in pt3.get("candidate_setup_records", [])
        if isinstance(candidate, dict)
    ]


def _order_material(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "stage": "PT-4",
        "idempotency_namespace": "phase7_demo_proof",
        "source_auto_approval_decision_id": record["auto_approval_decision_id"],
        "source_setup_record_id": record["source_setup_record_id"],
        "strategy_family_key": str(record.get("strategy_family_key") or "unknown"),
        "instrument": str(record.get("instrument") or "unknown"),
        "selected_venue": "alpaca_paper",
        "side": str(record.get("side") or "buy").lower(),
        "quantity": f"{_float(record.get('quantity')):.8f}",
        "order_type": str(record.get("order_type") or "market").lower(),
        "time_in_force": str(record.get("time_in_force") or "day").lower(),
    }


def _pre_trade_snapshot(record: dict[str, Any], material: dict[str, Any]) -> dict[str, Any]:
    return {
        "snapshot_schema_version": PAPEROPS_AUTO_APPROVAL_STAGED_ORDER_SCHEMA_VERSION,
        "snapshot_type": "paperops_pt4_pre_trade_snapshot",
        "source_auto_approval_decision_id": record["auto_approval_decision_id"],
        "source_setup_record_id": record["source_setup_record_id"],
        "strategy_family_key": material["strategy_family_key"],
        "instrument": material["instrument"],
        "selected_venue": material["selected_venue"],
        "notional_gbp": _float(record.get("notional_gbp")),
        "risk_gbp": _float(record.get("risk_gbp")),
        "source_quorum_passed": record.get("source_quorum_passed") is True,
        "signal_integrity_passed": record.get("signal_integrity_passed") is True,
        "risk_gate_passed": record.get("risk_gate_passed") is True,
        "kill_switches_clear": record.get("kill_switches_clear") is True,
        "broker_identifier_exposed": False,
        "raw_payload_exposed": False,
        "local_path_exposed": False,
        "secret_value_exposed": False,
    }


def _event_log_prewrite_payload(
    *,
    artifact_id: str,
    staged_order_id: str,
    material: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": PAPEROPS_AUTO_APPROVAL_STAGED_ORDER_SCHEMA_VERSION,
        "prewrite_type": "paperops_pt4_staged_paper_order_prewrite",
        "artifact_id": artifact_id,
        "staged_order_id": staged_order_id,
        "idempotency_namespace": material["idempotency_namespace"],
        "source_auto_approval_decision_id": material[
            "source_auto_approval_decision_id"
        ],
        "source_setup_record_id": material["source_setup_record_id"],
        "selected_venue": material["selected_venue"],
        "instrument": material["instrument"],
        "side": material["side"],
        "quantity": material["quantity"],
        "order_type": material["order_type"],
        "time_in_force": material["time_in_force"],
        "paper_submit_allowed": False,
        "broker_post_allowed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
    }


def _staged_order_record(record: dict[str, Any]) -> dict[str, Any]:
    material = _order_material(record)
    fingerprint = _hash_payload(material)
    setup_key = _safe_key(str(record.get("source_setup_record_id") or "unknown"))
    artifact_id = f"paperops:pt-4:staged-paper-order:{setup_key}"
    staged_order_id = f"paperops-pt4-paper-order-{fingerprint[:20]}"
    idempotency_key = f"q7-6-stage-{fingerprint[:24]}"
    pre_trade_snapshot = _pre_trade_snapshot(record, material)
    prewrite_payload = _event_log_prewrite_payload(
        artifact_id=artifact_id,
        staged_order_id=staged_order_id,
        material=material,
    )
    source_auto_approved = record.get("auto_approved") is True
    quantity = _float(record.get("quantity"))
    side = str(record.get("side") or "").lower()
    order_type = str(record.get("order_type") or "").lower()
    time_in_force = str(record.get("time_in_force") or "").lower()
    checks = [
        {"name": "source_auto_approved", "passed": source_auto_approved},
        {"name": "qualified_setup", "passed": record.get("qualified_setup") is True},
        {"name": "source_quorum_passed", "passed": record.get("source_quorum_passed") is True},
        {"name": "signal_integrity_passed", "passed": record.get("signal_integrity_passed") is True},
        {"name": "risk_gate_passed", "passed": record.get("risk_gate_passed") is True},
        {"name": "kill_switches_clear", "passed": record.get("kill_switches_clear") is True},
        {"name": "execution_adapter_read_ready", "passed": record.get("execution_adapter_read_ready") is True},
        {"name": "venue_read_available", "passed": record.get("venue_read_available") is True},
        {"name": "broker_write_blocked", "passed": record.get("broker_write_blocked") is True},
        {"name": "selected_venue_alpaca_paper", "passed": material["selected_venue"] == "alpaca_paper"},
        {"name": "side_valid", "passed": side in {"buy", "sell"}},
        {"name": "quantity_positive", "passed": quantity > 0.0},
        {"name": "order_type_valid", "passed": order_type in {"market", "limit", "stop", "stop_limit"}},
        {"name": "time_in_force_valid", "passed": time_in_force in {"day", "gtc", "opg", "cls", "ioc", "fok"}},
        {"name": "idempotency_key_phase7_namespace", "passed": idempotency_key.startswith("q7-6-stage-")},
        {"name": "event_log_prewrite_ready", "passed": bool(prewrite_payload)},
        {"name": "pre_trade_snapshot_present", "passed": bool(pre_trade_snapshot)},
        {"name": "paper_submit_separated", "passed": True},
        {"name": "broker_post_disabled", "passed": True},
        {"name": "live_endpoint_disabled", "passed": True},
        {"name": "proof_credit_disabled", "passed": True},
    ]
    failed_checks = [check["name"] for check in checks if check["passed"] is not True]
    staged = source_auto_approved and not failed_checks
    return {
        "schema_version": PAPEROPS_AUTO_APPROVAL_STAGED_ORDER_SCHEMA_VERSION,
        "record_type": "paperops_staged_paper_order",
        "artifact_id": artifact_id,
        "phase": "PaperOps",
        "stage": "PT-4",
        "status": "staged" if staged else "blocked",
        "order_state": "staged_ready_for_paperops2_submit" if staged else "blocked_not_staged",
        "public_safe": True,
        "source_auto_approval_decision_id": record["auto_approval_decision_id"],
        "source_setup_record_id": record["source_setup_record_id"],
        "source_approval_state": record["approval_state"],
        "source_auto_approved": source_auto_approved,
        "qualified_setup": record.get("qualified_setup") is True,
        "strategy_family_key": material["strategy_family_key"],
        "selected_venue": material["selected_venue"],
        "instrument": material["instrument"],
        "side": side,
        "quantity": quantity,
        "order_type": order_type,
        "time_in_force": time_in_force,
        "staged_order_id": staged_order_id if staged else None,
        "proof_order_id": staged_order_id if staged else None,
        "idempotency_namespace": "phase7_demo_proof",
        "idempotency_material": material,
        "idempotency_key": idempotency_key if staged else None,
        "idempotency_reused_from_phase5": False,
        "phase5_order_id_reused": False,
        "pre_trade_snapshot_required": True,
        "pre_trade_snapshot_present": staged,
        "pre_trade_snapshot": pre_trade_snapshot if staged else None,
        "event_log_prewrite_required": True,
        "event_log_prewrite_ready": staged,
        "event_log_prewrite_written": False,
        "event_log_prewrite_payload": prewrite_payload if staged else None,
        "event_log_prewrite_fingerprint": _hash_payload(prewrite_payload)
        if staged
        else None,
        "event_log_prewrite_ref": None,
        "staged_order_created": staged,
        "ready_for_paperops2_submit": staged,
        "paper_submit_allowed": False,
        "broker_submit_ready": False,
        "broker_post_allowed": False,
        "alpaca_post_allowed": False,
        "broker_write_allowed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
        "proof_trade_created": False,
        "proof_credit_allowed": False,
        "manual_trade_level_override_allowed": False,
        "checks": checks,
        "failed_checks": failed_checks,
        "failed_check_count": len(failed_checks),
        "blocked_reasons": [] if staged else failed_checks,
        "blocked_reason_count": 0 if staged else len(failed_checks),
    }


def _staged_order_records(
    approval_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [_staged_order_record(record) for record in approval_records]


def build_paperops_auto_approval_staged_order(
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    snapshot = _source_snapshot(settings)
    pt3 = snapshot["pt3"]
    source_blockers = _source_blockers(pt3)
    source_ready = not source_blockers and pt3.get("qualified_setup_count", 0) >= 0
    approval_records = _approval_records(pt3, source_ready=source_ready)
    auto_approved_records = [
        record for record in approval_records if record.get("auto_approved") is True
    ]
    staged_records = _staged_order_records(approval_records)
    active_staged_records = [
        record for record in staged_records if record.get("status") == "staged"
    ]
    idempotency_keys = [
        str(record.get("idempotency_key"))
        for record in active_staged_records
        if str(record.get("idempotency_key") or "").strip()
    ]
    blockers = list(source_blockers)
    if settings.mode != "paper":
        blockers.append("mode_not_paper")
    if settings.live_capital_enabled:
        blockers.append("live_capital_enabled")
    if not pt3 and not blockers:
        blockers.append("pt3_artifact_missing")
    if blockers:
        status = "blocked_pending_pt3_prerequisite"
        next_action = "Restore PT-3 qualified setup production before PT-4."
    elif active_staged_records:
        status = "staged_paper_order_ready"
        next_action = (
            "Keep the staged order guarded; the next stage is PaperOps-2 "
            "explicit Alpaca paper submit enablement."
        )
    else:
        status = "ready_no_current_auto_approved_setup"
        next_action = "Keep the PaperOps runner active until PT-3 produces a setup."
    unsafe_total = sum(
        _int(value)
        for value in (
            pt3.get("broker_post_called_count"),
            pt3.get("alpaca_post_called_count"),
            pt3.get("live_endpoint_called_count"),
            pt3.get("qctrl_broker_post_called_count"),
            pt3.get("qctrl_live_endpoint_called_count"),
            pt3.get("phase7_proof_credit_granted_count"),
            pt3.get("forced_trade_count"),
            pt3.get("unsafe_write_counter_total"),
        )
    )
    artifact = {
        "schema_version": PAPEROPS_AUTO_APPROVAL_STAGED_ORDER_SCHEMA_VERSION,
        "artifact_type": "paperops_auto_approval_staged_order",
        "artifact_id": "paperops:pt-4:auto-approval-staged-order",
        "phase": "PaperOps",
        "stage": "PT-4",
        "status": status,
        "generated_at": generated_at,
        "public_safe": True,
        "recorded": False,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_event_count": 0,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "runtime_artifact_path": None,
        "history_log_path": None,
        "mode": settings.mode,
        "source_pt3_status": pt3.get("status", "missing"),
        "source_pt3_path_ready": pt3.get("qualified_setup_production_path_ready")
        is True,
        "source_pt3_candidate_count": _int(pt3.get("production_candidate_count")),
        "source_pt3_qualified_setup_count": _int(pt3.get("qualified_setup_count")),
        "source_pt3_ready_to_stage_q7_order": pt3.get("ready_to_stage_q7_order")
        is True,
        "source_pt3_q7_ledger_count": _int(
            pt3.get("source_qualified_setup_ledger_count")
        ),
        "qctrl_consultation_required_for_full_parity": pt3.get(
            "qctrl_consultation_required_for_full_parity"
        )
        is True,
        "qctrl_paper_consultation_status": pt3.get(
            "qctrl_paper_consultation_status",
            "missing",
        ),
        "qctrl_paper_consultation_connected": pt3.get(
            "qctrl_paper_consultation_connected"
        )
        is True,
        "qctrl_consultation_blocker": pt3.get("qctrl_consultation_blocker"),
        "auto_approval_policy": _auto_approval_policy(),
        "auto_approval_record_count": len(approval_records),
        "auto_approved_setup_count": len(auto_approved_records),
        "auto_approval_blocked_count": len(approval_records) - len(auto_approved_records),
        "staging_decision_record_count": len(staged_records),
        "staged_order_count": len(active_staged_records),
        "blocked_staged_order_count": len(staged_records) - len(active_staged_records),
        "ready_for_paperops2_submit": bool(active_staged_records),
        "idempotency_namespace": "phase7_demo_proof",
        "idempotency_key_count": len(idempotency_keys),
        "duplicate_idempotency_key_count": _duplicate_count(idempotency_keys),
        "event_log_prewrite_ready_count": sum(
            1 for record in active_staged_records if record.get("event_log_prewrite_ready")
        ),
        "event_log_prewrite_written_count": 0,
        "pre_trade_snapshot_present_count": sum(
            1 for record in active_staged_records if record.get("pre_trade_snapshot_present")
        ),
        "auto_approval_records": approval_records,
        "staged_order_records": staged_records,
        "q7_source_ledger_mutation_performed": False,
        "q7_auto_approval_artifact_mutation_performed": False,
        "q7_staging_artifact_mutation_performed": False,
        "paper_order_submission_allowed": False,
        "broker_post_allowed": False,
        "alpaca_post_allowed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": settings.live_capital_enabled,
        "qctrl_direct_execution_allowed": False,
        "qctrl_broker_post_allowed": False,
        "phase7_proof_credit_allowed": False,
        "forced_trades_allowed": False,
        "manual_trade_level_override_allowed": False,
        "broker_post_called_count": _int(pt3.get("broker_post_called_count")),
        "alpaca_post_called_count": _int(pt3.get("alpaca_post_called_count")),
        "live_endpoint_called_count": _int(pt3.get("live_endpoint_called_count")),
        "qctrl_broker_post_called_count": _int(
            pt3.get("qctrl_broker_post_called_count")
        ),
        "qctrl_live_endpoint_called_count": _int(
            pt3.get("qctrl_live_endpoint_called_count")
        ),
        "phase7_proof_credit_granted_count": 0,
        "forced_trade_count": 0,
        "secret_value_exposed_count": 0,
        "raw_payload_exposed_count": 0,
        "unsafe_write_counter_total": unsafe_total,
        "blockers": sorted(set(blockers)),
        "blocker_count": len(set(blockers)),
        "next_required_action": next_action,
        "boundary": PAPEROPS_AUTO_APPROVAL_STAGED_ORDER_BOUNDARY,
    }
    artifact["validation_errors"] = validate_paperops_auto_approval_staged_order(
        artifact
    )
    if artifact["validation_errors"]:
        artifact["status"] = "invalid"
    artifact["public_status"] = (
        paperops_auto_approval_staged_order_public_status_from_artifact(artifact)
    )
    return artifact


def _validate_auto_approval_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("record_type") != "paperops_auto_approval_decision":
        errors.append("pt4_auto_approval_record_type_invalid")
    approved = record.get("auto_approved") is True
    if approved:
        if record.get("approval_state") != "auto_approved":
            errors.append("pt4_auto_approval_state_invalid")
        for key in (
            "qualified_setup",
            "all_required_gates_passed",
            "source_quorum_passed",
            "signal_integrity_passed",
            "risk_gate_passed",
            "execution_adapter_read_ready",
            "venue_read_available",
            "kill_switches_clear",
            "broker_write_blocked",
            "phase7_safety_boundaries_preserved",
        ):
            if record.get(key) is not True:
                errors.append(f"pt4_auto_approval_gate_not_passed:{key}")
        if record.get("rejection_reasons"):
            errors.append("pt4_auto_approval_with_rejections")
    else:
        if record.get("auto_approval_blocked") is not True:
            errors.append("pt4_auto_approval_blocked_flag_missing")
    for key in (
        "fund_manager_trade_level_approval_required",
        "fund_manager_trade_level_approval_recorded",
        "manual_trade_level_override_attempted",
        "phase5_lifecycle_counts_as_q7_proof",
        "paper_order_submission_allowed",
        "proof_trade_creation_allowed",
        "proof_credit_allowed",
        "broker_post_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
    ):
        if record.get(key) is not False:
            errors.append(f"pt4_auto_approval_record_forbidden:{key}")
    return errors


def _validate_staged_order_record(record: dict[str, Any], *, artifact_recorded: bool) -> list[str]:
    errors: list[str] = []
    if record.get("record_type") != "paperops_staged_paper_order":
        errors.append("pt4_staged_order_record_type_invalid")
    staged = record.get("status") == "staged"
    checks = record.get("checks", [])
    if not isinstance(checks, list):
        errors.append("pt4_staged_order_checks_not_list")
        checks = []
    failed_checks = [
        str(check.get("name"))
        for check in checks
        if isinstance(check, dict) and check.get("passed") is not True
    ]
    if record.get("failed_checks") != failed_checks:
        errors.append("pt4_staged_order_failed_checks_mismatch")
    if record.get("failed_check_count") != len(failed_checks):
        errors.append("pt4_staged_order_failed_check_count_mismatch")
    if staged:
        if record.get("source_auto_approved") is not True:
            errors.append("pt4_staged_order_without_auto_approval")
        if record.get("qualified_setup") is not True:
            errors.append("pt4_staged_order_without_qualified_setup")
        if record.get("selected_venue") != "alpaca_paper":
            errors.append("pt4_staged_order_non_alpaca_venue")
        if not str(record.get("idempotency_key") or "").startswith("q7-6-stage-"):
            errors.append("pt4_staged_order_idempotency_invalid")
        if record.get("idempotency_namespace") != "phase7_demo_proof":
            errors.append("pt4_staged_order_namespace_invalid")
        if record.get("pre_trade_snapshot_present") is not True:
            errors.append("pt4_staged_order_snapshot_missing")
        if record.get("event_log_prewrite_ready") is not True:
            errors.append("pt4_staged_order_prewrite_not_ready")
        if artifact_recorded and record.get("event_log_prewrite_written") is not True:
            errors.append("pt4_staged_order_prewrite_not_written")
        if record.get("ready_for_paperops2_submit") is not True:
            errors.append("pt4_staged_order_not_ready_for_paperops2")
        if failed_checks:
            errors.append("pt4_staged_order_with_failed_checks")
    else:
        if record.get("staged_order_created") is not False:
            errors.append("pt4_blocked_order_created")
        if str(record.get("idempotency_key") or "").strip():
            errors.append("pt4_blocked_order_has_idempotency")
    for key in (
        "paper_submit_allowed",
        "broker_submit_ready",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "broker_write_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "proof_trade_created",
        "proof_credit_allowed",
        "manual_trade_level_override_allowed",
    ):
        if record.get(key) is not False:
            errors.append(f"pt4_staged_order_forbidden:{key}")
    return errors


def validate_paperops_auto_approval_staged_order(
    artifact: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    required = set(PAPEROPS_AUTO_APPROVAL_STAGED_ORDER_PUBLIC_FIELDS) | {
        "recorded",
        "event_log_required",
        "event_log_written",
        "event_log_correlation_id",
    }
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("paperops_pt4_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PAPEROPS_AUTO_APPROVAL_STAGED_ORDER_SCHEMA_VERSION:
        errors.append("paperops_pt4_schema_mismatch")
    if artifact.get("artifact_type") != "paperops_auto_approval_staged_order":
        errors.append("paperops_pt4_type_mismatch")
    if artifact.get("phase") != "PaperOps" or artifact.get("stage") != "PT-4":
        errors.append("paperops_pt4_phase_stage_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("paperops_pt4_not_public_safe")
    if artifact.get("mode") != "paper":
        errors.append("paperops_pt4_mode_not_paper")
    blockers = artifact.get("blockers", [])
    if not isinstance(blockers, list):
        errors.append("paperops_pt4_blockers_not_list")
        blockers = []
    if artifact.get("blocker_count") != len(blockers):
        errors.append("paperops_pt4_blocker_count_mismatch")
    recorded = artifact.get("recorded") is True
    if recorded:
        if artifact.get("event_log_written") is not True:
            errors.append("paperops_pt4_event_log_missing")
        if artifact.get("event_log_event_count") != 1:
            errors.append("paperops_pt4_event_count_mismatch")
        if not artifact.get("event_log_correlation_id"):
            errors.append("paperops_pt4_event_correlation_missing")
    if artifact.get("status") == "staged_paper_order_ready":
        if artifact.get("staged_order_count", 0) < 1:
            errors.append("paperops_pt4_ready_without_staged_order")
        if artifact.get("auto_approved_setup_count", 0) < 1:
            errors.append("paperops_pt4_ready_without_auto_approval")
        if artifact.get("ready_for_paperops2_submit") is not True:
            errors.append("paperops_pt4_not_ready_for_paperops2")
        if blockers:
            errors.append("paperops_pt4_ready_with_blockers")
    elif artifact.get("status") == "ready_no_current_auto_approved_setup":
        if artifact.get("auto_approved_setup_count", 0) != 0:
            errors.append("paperops_pt4_no_current_with_approval")
    elif artifact.get("status") == "blocked_pending_pt3_prerequisite":
        if not blockers:
            errors.append("paperops_pt4_blocked_without_blockers")
    elif artifact.get("status") != "invalid":
        errors.append("paperops_pt4_status_invalid")
    policy = artifact.get("auto_approval_policy", {})
    if not isinstance(policy, dict):
        errors.append("paperops_pt4_policy_missing")
        policy = {}
    for key in (
        "pt3_production_qualified_setup_required",
        "all_pt3_production_gates_required",
        "governance_feedback_affects_future_policy_only",
        "qctrl_consultation_required_for_full_parity",
        "paper_order_staging_allowed",
    ):
        if policy.get(key) is not True:
            errors.append(f"paperops_pt4_policy_missing_true:{key}")
    for key in (
        "fund_manager_trade_level_approval_required",
        "manual_trade_level_override_allowed",
        "qctrl_direct_execution_allowed",
        "paper_order_submission_allowed",
        "broker_post_allowed",
        "live_endpoint_allowed",
        "proof_trade_creation_allowed",
        "proof_credit_allowed",
        "live_capital_enabled",
    ):
        if policy.get(key) is not False:
            errors.append(f"paperops_pt4_policy_forbidden:{key}")
    auto_records = artifact.get("auto_approval_records", [])
    if not isinstance(auto_records, list):
        errors.append("paperops_pt4_auto_records_not_list")
        auto_records = []
    staged_records = artifact.get("staged_order_records", [])
    if not isinstance(staged_records, list):
        errors.append("paperops_pt4_staged_records_not_list")
        staged_records = []
    for record in auto_records:
        if isinstance(record, dict):
            errors.extend(_validate_auto_approval_record(record))
        else:
            errors.append("paperops_pt4_auto_record_invalid")
    for record in staged_records:
        if isinstance(record, dict):
            errors.extend(_validate_staged_order_record(record, artifact_recorded=recorded))
        else:
            errors.append("paperops_pt4_staged_record_invalid")
    auto_approved_count = sum(
        1 for record in auto_records if isinstance(record, dict) and record.get("auto_approved") is True
    )
    staged_count = sum(
        1 for record in staged_records if isinstance(record, dict) and record.get("status") == "staged"
    )
    if artifact.get("auto_approval_record_count") != len(auto_records):
        errors.append("paperops_pt4_auto_record_count_mismatch")
    if artifact.get("auto_approved_setup_count") != auto_approved_count:
        errors.append("paperops_pt4_auto_approved_count_mismatch")
    if artifact.get("staged_order_count") != staged_count:
        errors.append("paperops_pt4_staged_count_mismatch")
    idempotency_keys = [
        str(record.get("idempotency_key"))
        for record in staged_records
        if isinstance(record, dict) and str(record.get("idempotency_key") or "").strip()
    ]
    if artifact.get("idempotency_key_count") != len(idempotency_keys):
        errors.append("paperops_pt4_idempotency_count_mismatch")
    if artifact.get("duplicate_idempotency_key_count") != _duplicate_count(idempotency_keys):
        errors.append("paperops_pt4_duplicate_count_mismatch")
    if artifact.get("duplicate_idempotency_key_count"):
        errors.append("paperops_pt4_duplicate_idempotency")
    prewrite_ready = sum(
        1
        for record in staged_records
        if isinstance(record, dict) and record.get("event_log_prewrite_ready") is True
    )
    prewrite_written = sum(
        1
        for record in staged_records
        if isinstance(record, dict) and record.get("event_log_prewrite_written") is True
    )
    snapshot_count = sum(
        1
        for record in staged_records
        if isinstance(record, dict) and record.get("pre_trade_snapshot_present") is True
    )
    if artifact.get("event_log_prewrite_ready_count") != prewrite_ready:
        errors.append("paperops_pt4_prewrite_ready_count_mismatch")
    if artifact.get("event_log_prewrite_written_count") != prewrite_written:
        errors.append("paperops_pt4_prewrite_written_count_mismatch")
    if artifact.get("pre_trade_snapshot_present_count") != snapshot_count:
        errors.append("paperops_pt4_snapshot_count_mismatch")
    for key in (
        "q7_source_ledger_mutation_performed",
        "q7_auto_approval_artifact_mutation_performed",
        "q7_staging_artifact_mutation_performed",
        "paper_order_submission_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "qctrl_direct_execution_allowed",
        "qctrl_broker_post_allowed",
        "phase7_proof_credit_allowed",
        "forced_trades_allowed",
        "manual_trade_level_override_allowed",
    ):
        if artifact.get(key) is not False:
            errors.append(f"paperops_pt4_forbidden:{key}")
    for key in (
        "broker_post_called_count",
        "alpaca_post_called_count",
        "live_endpoint_called_count",
        "qctrl_broker_post_called_count",
        "qctrl_live_endpoint_called_count",
        "phase7_proof_credit_granted_count",
        "forced_trade_count",
        "secret_value_exposed_count",
        "raw_payload_exposed_count",
        "unsafe_write_counter_total",
    ):
        if _int(artifact.get(key)) != 0:
            errors.append(f"paperops_pt4_unsafe_counter_nonzero:{key}")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "guarded paper-only auto-approval",
        "cannot mutate the Q7 source ledger",
        "cannot submit paper orders",
        "cannot call brokers",
        "cannot grant Phase 7 proof credit",
        "cannot force trades",
        "cannot enable live capital",
    ):
        if phrase not in boundary:
            errors.append("paperops_pt4_boundary_weak")
            break
    return sorted(set(errors))


def paperops_auto_approval_staged_order_public_status_from_artifact(
    artifact: dict[str, Any],
) -> dict[str, Any]:
    public_status = {
        field: deepcopy(artifact.get(field))
        for field in PAPEROPS_AUTO_APPROVAL_STAGED_ORDER_PUBLIC_FIELDS
        if field in artifact
    }
    public_status["validation_error_count"] = len(
        artifact.get("validation_errors", []) or []
    )
    public_status["recorded"] = artifact.get("recorded") is True
    public_status["event_log_written"] = artifact.get("event_log_written") is True
    public_status["event_log_event_count"] = artifact.get("event_log_event_count", 0)
    return public_status


def paperops_auto_approval_staged_order_public_status(
    settings: Settings | None = None,
) -> dict[str, Any]:
    artifact = read_latest_paperops_auto_approval_staged_order(settings)
    if not artifact:
        return {
            "schema_version": PAPEROPS_AUTO_APPROVAL_STAGED_ORDER_SCHEMA_VERSION,
            "artifact_type": "paperops_auto_approval_staged_order",
            "artifact_id": "paperops:pt-4:auto-approval-staged-order",
            "phase": "PaperOps",
            "stage": "PT-4",
            "status": "not_run",
            "public_safe": True,
            "recorded": False,
            "event_log_written": False,
            "event_log_event_count": 0,
            "mode": "paper",
            "source_pt3_status": "not_run",
            "source_pt3_path_ready": False,
            "auto_approved_setup_count": 0,
            "staged_order_count": 0,
            "ready_for_paperops2_submit": False,
            "event_log_prewrite_written_count": 0,
            "q7_source_ledger_mutation_performed": False,
            "q7_auto_approval_artifact_mutation_performed": False,
            "q7_staging_artifact_mutation_performed": False,
            "paper_order_submission_allowed": False,
            "broker_post_allowed": False,
            "broker_post_called_count": 0,
            "live_endpoint_allowed": False,
            "live_capital_enabled": False,
            "phase7_proof_credit_allowed": False,
            "forced_trades_allowed": False,
            "unsafe_write_counter_total": 0,
            "validation_error_count": 0,
            "boundary": PAPEROPS_AUTO_APPROVAL_STAGED_ORDER_BOUNDARY,
        }
    return paperops_auto_approval_staged_order_public_status_from_artifact(artifact)


def attach_paperops_auto_approval_staged_order_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(
        event_log_path
        or (_runtime_dir(settings) / PAPEROPS_AUTO_APPROVAL_STAGED_ORDER_EVENT_LOG)
    )
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PAPEROPS_AUTO_APPROVAL_STAGED_ORDER_EVENT_TYPE,
        PAPEROPS_AUTO_APPROVAL_STAGED_ORDER_COMPONENT,
        {
            "status": output.get("status"),
            "source_pt3_status": output.get("source_pt3_status"),
            "auto_approved_setup_count": output.get("auto_approved_setup_count"),
            "staged_order_count": output.get("staged_order_count"),
            "ready_for_paperops2_submit": output.get("ready_for_paperops2_submit"),
            "broker_post_called_count": output.get("broker_post_called_count"),
            "live_endpoint_called_count": output.get("live_endpoint_called_count"),
            "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
            "blocker_count": output.get("blocker_count"),
        },
    )
    output["recorded"] = True
    output["event_log_written"] = True
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = 1
    output["event_log_correlation_id"] = entry.correlation_id
    output["event_log_created_at"] = entry.created_at
    updated_records = []
    for record in output.get("staged_order_records", []):
        if isinstance(record, dict) and record.get("status") == "staged":
            updated = deepcopy(record)
            updated["event_log_prewrite_written"] = True
            updated["event_log_prewrite_ref"] = entry.correlation_id
            updated_records.append(updated)
        else:
            updated_records.append(record)
    output["staged_order_records"] = updated_records
    output["event_log_prewrite_written_count"] = sum(
        1
        for record in updated_records
        if isinstance(record, dict) and record.get("event_log_prewrite_written") is True
    )
    output["validation_errors"] = validate_paperops_auto_approval_staged_order(
        output
    )
    if output["validation_errors"]:
        output["status"] = "invalid"
    output["public_status"] = (
        paperops_auto_approval_staged_order_public_status_from_artifact(output)
    )
    return output, entry


def write_paperops_auto_approval_staged_order(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = (
        paperops_auto_approval_staged_order_paths(settings)
    )
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_paperops_auto_approval_staged_order_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_paperops_auto_approval_staged_order(
            output
        )
        output["public_status"] = (
            paperops_auto_approval_staged_order_public_status_from_artifact(output)
        )
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_paperops_auto_approval_staged_order(
        output
    )
    if output["validation_errors"]:
        output["status"] = "invalid"
    output["public_status"] = (
        paperops_auto_approval_staged_order_public_status_from_artifact(output)
    )
    output_path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    history_record = {
        "schema_version": PAPEROPS_AUTO_APPROVAL_STAGED_ORDER_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "recorded_at": _now(),
        "source_pt3_status": output.get("source_pt3_status"),
        "auto_approved_setup_count": output.get("auto_approved_setup_count"),
        "staged_order_count": output.get("staged_order_count"),
        "ready_for_paperops2_submit": output.get("ready_for_paperops2_submit"),
        "broker_post_called_count": output.get("broker_post_called_count"),
        "live_endpoint_called_count": output.get("live_endpoint_called_count"),
        "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
        "validation_error_count": len(output.get("validation_errors", []) or []),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output
