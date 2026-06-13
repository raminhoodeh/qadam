"""Q7-6 Phase 7 Demo Proof order staging and idempotency.

This stage converts Q7-5 auto-approved setups into Phase 7 proof paper-order
staging records. It grants staging authority only: it does not submit orders,
call broker POST routes, create proof trades, grant proof credit, or enable
live capital.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.phase7_artifacts import (
    PHASE7_ARTIFACT_SCHEMA_VERSION,
    PHASE7_EVENT_TYPES,
    phase7_proof_contract,
    phase7_provenance,
    phase7_source_posture,
)
from orchestrator.phase7_readiness import (
    PHASE7_AUTHORITY_FLAGS,
    PHASE7_HARNESS_DAY_COUNT,
    PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
    PHASE7_MAX_DRAWDOWN_FRACTION,
    PHASE7_PAPER_ACCOUNT_STARTING_GBP,
    PHASE7_UNSAFE_COUNT_FIELDS,
    phase7_authority_defaults,
    phase7_unsafe_counter_defaults,
)
from orchestrator.phase7_test_mode_auto_approval import (
    PHASE7_TEST_MODE_AUTO_APPROVAL_RUNTIME_ARTIFACT,
    build_phase7_test_mode_auto_approval_router,
    phase7_test_mode_auto_approval_paths,
    validate_phase7_test_mode_auto_approval_router,
)


PHASE7_PROOF_ORDER_STAGING_SCHEMA_VERSION = 1
PHASE7_PROOF_ORDER_STAGING_RUNTIME_ARTIFACT = "phase7_proof_order_staging.json"
PHASE7_PROOF_ORDER_STAGING_HISTORY = "phase7_proof_order_staging_history.jsonl"
PHASE7_PROOF_ORDER_STAGING_EVENT_LOG = "phase7_proof_order_staging_events.jsonl"
PHASE7_PROOF_ORDER_STAGING_EVENT_TYPE = PHASE7_EVENT_TYPES["staged_order"]
PHASE7_PROOF_ORDER_STAGING_COMPONENT = "phase7_proof_order_staging"

PHASE7_PROOF_ORDER_STAGING_BOUNDARY = (
    "Q7-6 can create Phase 7 proof paper-order staging records only from Q7-5 "
    "auto-approved qualified setups with source, policy, risk, execution, "
    "venue, broker paper-readiness, idempotency, Event Log prewrite, and "
    "pre-trade snapshot checks passed. It cannot reuse Phase 5 order IDs, "
    "cannot submit paper orders, cannot call broker POST routes, cannot write "
    "prediction-market or crypto-perps orders, cannot create proof trades, "
    "cannot grant Phase 7 proof credit, cannot call live endpoints, cannot "
    "enable live capital, and cannot permit manual trade-level overrides."
)

PHASE7_PROOF_ORDER_STAGING_REQUIRED_CHECKS: tuple[str, ...] = (
    "source_auto_approval_router_valid",
    "source_decision_auto_approved",
    "qualified_setup",
    "source_phase_q7",
    "source_quorum_passed",
    "all_required_gates_passed",
    "risk_gate_passed",
    "execution_policy_gate_passed",
    "kill_switches_clear",
    "venue_available",
    "broker_paper_ready",
    "fund_manager_trade_level_approval_absent",
    "manual_trade_level_override_absent",
    "selected_venue_alpaca_paper",
    "instrument_present",
    "side_valid",
    "quantity_positive",
    "order_type_valid",
    "time_in_force_valid",
    "idempotency_key_phase7",
    "idempotency_not_reused_from_phase5",
    "event_log_prewrite_ready",
    "pre_trade_snapshot_present",
    "paper_submit_separated",
    "broker_post_disabled",
    "live_endpoint_disabled",
    "prediction_market_write_disabled",
    "crypto_perps_write_disabled",
)

PHASE7_PROOF_ORDER_STAGING_CANCELLATION_CONDITIONS: tuple[str, ...] = (
    "source_auto_approval_retracted",
    "source_setup_expires_before_submit",
    "risk_or_policy_gate_retracted",
    "kill_switch_activates_after_staging",
    "broker_paper_readiness_degrades_before_submit",
    "idempotency_collision_detected",
    "pre_trade_snapshot_stale_before_submit",
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


def phase7_proof_order_staging_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE7_PROOF_ORDER_STAGING_RUNTIME_ARTIFACT,
        runtime / PHASE7_PROOF_ORDER_STAGING_HISTORY,
        runtime / PHASE7_PROOF_ORDER_STAGING_EVENT_LOG,
    )


def _auto_approval_router(settings: Settings) -> dict[str, Any]:
    auto_path, _, _ = phase7_test_mode_auto_approval_paths(settings)
    if auto_path.exists():
        return _read_json(auto_path)
    return build_phase7_test_mode_auto_approval_router(settings=settings)


def _phase5_idempotency_keys(settings: Settings) -> set[str]:
    phase5_path = _runtime_dir(settings) / "phase5_paper_order_staging_gate.json"
    phase5 = _read_json(phase5_path)
    keys: set[str] = set()
    for record in phase5.get("records", []) or []:
        if isinstance(record, dict) and str(record.get("idempotency_key") or "").strip():
            keys.add(str(record["idempotency_key"]))
    return keys


def _safe_key(value: str) -> str:
    allowed = []
    for char in value.lower():
        if char.isalnum() or char in {"_", "-"}:
            allowed.append(char)
        else:
            allowed.append("_")
    return "".join(allowed).strip("_") or "unknown"


def _hash_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _staging_policy() -> dict[str, Any]:
    return {
        "policy_schema_version": PHASE7_PROOF_ORDER_STAGING_SCHEMA_VERSION,
        "staging_mode": "phase7_proof_paper_order_staging",
        "auto_approved_setup_required": True,
        "qualified_setup_required": True,
        "source_phase_q7_required": True,
        "fund_manager_trade_level_approval_allowed": False,
        "manual_trade_level_override_allowed": False,
        "phase5_order_id_reuse_allowed": False,
        "phase5_idempotency_reuse_allowed": False,
        "idempotency_namespace": "phase7_demo_proof",
        "event_log_prewrite_required": True,
        "pre_trade_snapshot_required": True,
        "alpaca_paper_only": True,
        "paper_submit_allowed": False,
        "broker_post_allowed": False,
        "prediction_market_write_allowed": False,
        "crypto_perps_write_allowed": False,
        "live_endpoint_allowed": False,
        "proof_trade_creation_allowed": False,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
    }


def _authority_ledger(stage_recorded: bool) -> dict[str, Any]:
    defaults = phase7_authority_defaults()
    defaults["phase7_test_mode_auto_approval_allowed"] = stage_recorded
    defaults["phase7_proof_order_staging_allowed"] = stage_recorded
    return {
        "authority_schema_version": PHASE7_PROOF_ORDER_STAGING_SCHEMA_VERSION,
        "stage": "Q7-6",
        "authority_field_count": len(PHASE7_AUTHORITY_FLAGS),
        "explicit_authority_grant_count": 2 if stage_recorded else 0,
        "explicit_authority_grants": (
            [
                "phase7_test_mode_auto_approval_allowed",
                "phase7_proof_order_staging_allowed",
            ]
            if stage_recorded
            else []
        ),
        "q7_7_guarded_alpaca_paper_submit_path_stage_allowed": stage_recorded,
        **defaults,
        "boundary": PHASE7_PROOF_ORDER_STAGING_BOUNDARY,
    }


def _provenance() -> dict[str, Any]:
    provenance = phase7_provenance(
        (
            f"data/runtime/{PHASE7_TEST_MODE_AUTO_APPROVAL_RUNTIME_ARTIFACT}",
            "orchestrator/phase7_artifacts.py",
            "orchestrator/phase7_test_mode_auto_approval.py",
            "docs/qadam-phase-7-demo-proof-implementation-plan.md",
            "docs/qadam-phase-7-q7-5-test-mode-auto-approval-router-audit-2026-05-25.md",
        )
    )
    provenance["decision_chain_refs"] = [
        f"data/runtime/{PHASE7_TEST_MODE_AUTO_APPROVAL_RUNTIME_ARTIFACT}"
    ]
    return provenance


def _preflight_blockers(auto_approval: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    auto_errors = validate_phase7_test_mode_auto_approval_router(auto_approval)
    if auto_errors:
        blockers.append("phase7_auto_approval_router_validation_errors")
    if auto_approval.get("test_mode_auto_approval_router_recorded") is not True:
        blockers.append("phase7_auto_approval_router_not_recorded")
    if auto_approval.get("q7_6_proof_order_staging_stage_allowed") is not True:
        blockers.append("q7_6_proof_order_staging_not_allowed")
    if auto_approval.get("phase7_test_mode_auto_approval_allowed") is not True:
        blockers.append("phase7_test_mode_auto_approval_not_allowed")
    if int(auto_approval.get("fund_manager_trade_level_approval_count", 0) or 0) != 0:
        blockers.append("fund_manager_trade_level_approval_present")
    if int(auto_approval.get("manual_trade_level_override_attempt_count", 0) or 0) != 0:
        blockers.append("manual_trade_level_override_attempt_present")
    if auto_approval.get("sample_contaminated") is not False:
        blockers.append("phase7_sample_contaminated")
    for field in (
        "phase7_proof_credit_allowed",
        "broker_post_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "manual_trade_level_override_allowed",
    ):
        if auto_approval.get(field) is not False:
            blockers.append(f"upstream_forbidden_authority_enabled:{field}")
    return sorted(set(blockers))


def _order_material(decision: dict[str, Any]) -> dict[str, Any]:
    quantity = _float(decision.get("quantity"), 0.0)
    material = {
        "stage": "Q7-6",
        "idempotency_namespace": "phase7_demo_proof",
        "source_auto_approval_decision_id": str(decision.get("decision_id") or "unknown"),
        "source_setup_record_id": str(decision.get("setup_record_id") or "unknown"),
        "paperops_source_setup_record_id": str(
            decision.get("paperops_source_setup_record_id")
            or decision.get("source_origin_record_id")
            or "unknown_paperops_setup"
        ),
        "research_goal_id": str(decision.get("research_goal_id") or "unknown_research_goal"),
        "candidate_identity": str(decision.get("candidate_identity") or "unknown_candidate"),
        "signal_evidence_lineage_key": str(
            decision.get("signal_evidence_lineage_key") or "unknown_signal_lineage"
        ),
        "source_signal_id": str(decision.get("source_signal_id") or "unknown_source_signal"),
        "strategy_family_key": str(decision.get("strategy_family_key") or "unknown_strategy"),
        "instrument": str(decision.get("instrument") or "unknown_instrument"),
        "selected_venue": "alpaca_paper",
        "side": str(decision.get("side") or "not_determined"),
        "quantity": f"{quantity:.8f}",
        "order_type": str(decision.get("order_type") or "market"),
        "time_in_force": str(decision.get("time_in_force") or "day"),
    }
    material["fingerprint"] = _hash_payload(material)
    return material


def _pre_trade_snapshot(decision: dict[str, Any], material: dict[str, Any]) -> dict[str, Any]:
    return {
        "snapshot_schema_version": PHASE7_PROOF_ORDER_STAGING_SCHEMA_VERSION,
        "snapshot_type": "phase7_pre_trade_snapshot",
        "source_auto_approval_decision_id": material["source_auto_approval_decision_id"],
        "source_setup_record_id": material["source_setup_record_id"],
        "paperops_source_setup_record_id": material["paperops_source_setup_record_id"],
        "research_goal_id": material["research_goal_id"],
        "candidate_identity": material["candidate_identity"],
        "signal_evidence_lineage_key": material["signal_evidence_lineage_key"],
        "source_signal_id": material["source_signal_id"],
        "strategy_family_key": material["strategy_family_key"],
        "instrument": material["instrument"],
        "selected_venue": material["selected_venue"],
        "paper_account_starting_gbp": PHASE7_PAPER_ACCOUNT_STARTING_GBP,
        "max_drawdown_fraction": PHASE7_MAX_DRAWDOWN_FRACTION,
        "source_quorum_passed": decision.get("source_quorum_passed") is True,
        "risk_gate_passed": decision.get("risk_gate_passed") is True,
        "kill_switches_clear": decision.get("kill_switches_clear") is True,
        "broker_identifier_exposed": False,
        "raw_payload_exposed": False,
        "local_path_exposed": False,
    }


def _event_log_prewrite_payload(
    *,
    artifact_id: str,
    proof_order_id: str,
    material: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": PHASE7_PROOF_ORDER_STAGING_SCHEMA_VERSION,
        "prewrite_type": "phase7_staged_proof_order_prewrite",
        "artifact_id": artifact_id,
        "proof_order_id": proof_order_id,
        "idempotency_namespace": material["idempotency_namespace"],
        "source_auto_approval_decision_id": material["source_auto_approval_decision_id"],
        "source_setup_record_id": material["source_setup_record_id"],
        "paperops_source_setup_record_id": material["paperops_source_setup_record_id"],
        "research_goal_id": material["research_goal_id"],
        "candidate_identity": material["candidate_identity"],
        "signal_evidence_lineage_key": material["signal_evidence_lineage_key"],
        "source_signal_id": material["source_signal_id"],
        "selected_venue": material["selected_venue"],
        "instrument": material["instrument"],
        "side": material["side"],
        "quantity": material["quantity"],
        "order_type": material["order_type"],
        "time_in_force": material["time_in_force"],
        "paper_submit_allowed": False,
        "broker_post_allowed": False,
        "live_capital_enabled": False,
    }


def _check(name: str, passed: bool, *, detail: Any = None) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def _staging_decision_record(
    decision: dict[str, Any],
    *,
    stage_recorded: bool,
    phase5_idempotency_keys: set[str],
) -> dict[str, Any]:
    material = _order_material(decision)
    source_decision_id = material["source_auto_approval_decision_id"]
    setup_id = material["source_setup_record_id"]
    artifact_id = f"phase7:q7-6:staged-proof-order:{_safe_key(setup_id)}"
    proof_order_id = f"q7-proof-order-{material['fingerprint'][:20]}"
    idempotency_key = f"q7-6-stage-{material['fingerprint'][:24]}"
    pre_trade_snapshot = _pre_trade_snapshot(decision, material)
    prewrite_payload = _event_log_prewrite_payload(
        artifact_id=artifact_id,
        proof_order_id=proof_order_id,
        material=material,
    )
    side = material["side"]
    quantity = _float(material["quantity"], 0.0)
    order_type = material["order_type"]
    time_in_force = material["time_in_force"]
    source_auto_approved = decision.get("auto_approved") is True
    checks = [
        _check("source_auto_approval_router_valid", stage_recorded),
        _check("source_decision_auto_approved", source_auto_approved),
        _check("qualified_setup", decision.get("qualified_setup") is True),
        _check("source_phase_q7", decision.get("source_phase") == "Q7"),
        _check("source_quorum_passed", decision.get("source_quorum_passed") is True),
        _check("all_required_gates_passed", decision.get("all_required_gates_passed") is True),
        _check("risk_gate_passed", decision.get("risk_gate_passed") is True),
        _check("execution_policy_gate_passed", decision.get("execution_policy_gate_passed") is True),
        _check("kill_switches_clear", decision.get("kill_switches_clear") is True),
        _check("venue_available", decision.get("venue_available") is True),
        _check("broker_paper_ready", decision.get("broker_paper_ready") is True),
        _check(
            "fund_manager_trade_level_approval_absent",
            decision.get("fund_manager_trade_level_approval_recorded") is False,
        ),
        _check(
            "manual_trade_level_override_absent",
            decision.get("manual_trade_level_override_attempted") is False,
        ),
        _check("selected_venue_alpaca_paper", material["selected_venue"] == "alpaca_paper"),
        _check("instrument_present", material["instrument"] not in {"", "unknown_instrument"}),
        _check("side_valid", side in {"buy", "sell"}),
        _check("quantity_positive", quantity > 0.0),
        _check("order_type_valid", order_type in {"market", "limit", "stop", "stop_limit"}),
        _check("time_in_force_valid", time_in_force in {"day", "gtc", "opg", "cls", "ioc", "fok"}),
        _check("idempotency_key_phase7", idempotency_key.startswith("q7-6-stage-")),
        _check(
            "idempotency_not_reused_from_phase5",
            idempotency_key not in phase5_idempotency_keys
            and not idempotency_key.startswith("q5"),
        ),
        _check("event_log_prewrite_ready", bool(prewrite_payload)),
        _check("pre_trade_snapshot_present", bool(pre_trade_snapshot)),
        _check("paper_submit_separated", True),
        _check("broker_post_disabled", True),
        _check("live_endpoint_disabled", True),
        _check("prediction_market_write_disabled", True),
        _check("crypto_perps_write_disabled", True),
    ]
    failed_checks = [check["name"] for check in checks if check["passed"] is not True]
    staged = source_auto_approved and not failed_checks
    blocked_reasons = sorted(set(failed_checks + list(decision.get("rejection_reasons", []) or [])))
    return {
        "schema_version": PHASE7_ARTIFACT_SCHEMA_VERSION,
        "proof_order_staging_schema_version": PHASE7_PROOF_ORDER_STAGING_SCHEMA_VERSION,
        "artifact_type": "staged_proof_order",
        "artifact_id": artifact_id,
        "phase": "Q7",
        "stage": "Q7-6",
        "status": "staged" if staged else "blocked",
        "order_state": "staged_ready_for_guarded_paper_submit" if staged else "blocked_not_staged",
        "public_safe": True,
        "source_auto_approval_decision_id": source_decision_id,
        "source_setup_record_id": setup_id,
        "paperops_source_setup_record_id": material["paperops_source_setup_record_id"],
        "research_goal_id": material["research_goal_id"],
        "research_goal_lineage": deepcopy(decision.get("research_goal_lineage") or {}),
        "candidate_identity": material["candidate_identity"],
        "signal_evidence_lineage_key": material["signal_evidence_lineage_key"],
        "source_signal_id": material["source_signal_id"],
        "source_signal_review_id": decision.get("source_signal_review_id"),
        "source_signal_reviewed_at": decision.get("source_signal_reviewed_at"),
        "source_signal_status": decision.get("source_signal_status"),
        "setup_freshness_key": decision.get("setup_freshness_key"),
        "source_decision_state": decision.get("decision_state"),
        "source_auto_approved": source_auto_approved,
        "qualified_setup": decision.get("qualified_setup") is True,
        "source_phase": decision.get("source_phase"),
        "source_quorum_passed": decision.get("source_quorum_passed") is True,
        "all_required_gates_passed": decision.get("all_required_gates_passed") is True,
        "risk_gate_passed": decision.get("risk_gate_passed") is True,
        "execution_policy_gate_passed": decision.get("execution_policy_gate_passed") is True,
        "kill_switches_clear": decision.get("kill_switches_clear") is True,
        "venue_available": decision.get("venue_available") is True,
        "broker_paper_ready": decision.get("broker_paper_ready") is True,
        "strategy_family_key": material["strategy_family_key"],
        "selected_venue": material["selected_venue"],
        "instrument": material["instrument"],
        "side": side,
        "quantity": quantity,
        "order_type": order_type,
        "time_in_force": time_in_force,
        "proof_order_id": proof_order_id if staged else None,
        "idempotency_namespace": "phase7_demo_proof",
        "idempotency_material": material,
        "idempotency_key": idempotency_key if staged else None,
        "idempotency_reused_from_phase5": False,
        "phase5_order_id_reused": False,
        "phase5_order_id": None,
        "pre_trade_snapshot_required": True,
        "pre_trade_snapshot_present": staged,
        "pre_trade_snapshot": pre_trade_snapshot if staged else None,
        "event_log_prewrite_required": True,
        "event_log_prewrite_ready": staged,
        "event_log_prewrite_written": False,
        "event_log_prewrite_payload": prewrite_payload if staged else None,
        "event_log_prewrite_fingerprint": _hash_payload(prewrite_payload) if staged else None,
        "event_log_prewrite_correlation_id": None,
        "event_log_prewrite_created_at": None,
        "staged_order_created": staged,
        "paper_submit_allowed": False,
        "broker_submit_ready": False,
        "broker_post_allowed": False,
        "alpaca_post_allowed": False,
        "broker_write_allowed": False,
        "prediction_market_write_allowed": False,
        "crypto_perps_write_allowed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
        "proof_trade_created": False,
        "proof_credit_allowed": False,
        "manual_trade_level_override_allowed": False,
        "required_checks": list(PHASE7_PROOF_ORDER_STAGING_REQUIRED_CHECKS),
        "required_check_count": len(PHASE7_PROOF_ORDER_STAGING_REQUIRED_CHECKS),
        "checks": checks,
        "failed_checks": failed_checks,
        "failed_check_count": len(failed_checks),
        "blocked_reasons": [] if staged else blocked_reasons,
        "blocked_reason_count": 0 if staged else len(blocked_reasons),
        "cancellation_conditions": list(PHASE7_PROOF_ORDER_STAGING_CANCELLATION_CONDITIONS),
        "cancellation_condition_count": len(PHASE7_PROOF_ORDER_STAGING_CANCELLATION_CONDITIONS),
    }


def _staging_records(
    auto_approval: dict[str, Any],
    *,
    stage_recorded: bool,
    phase5_idempotency_keys: set[str],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for decision in auto_approval.get("approval_decision_records", []) or []:
        if isinstance(decision, dict):
            records.append(
                _staging_decision_record(
                    decision,
                    stage_recorded=stage_recorded,
                    phase5_idempotency_keys=phase5_idempotency_keys,
                )
            )
    return records


def _duplicate_count(values: list[str]) -> int:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return len(duplicates)


def build_phase7_proof_order_staging(
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    auto_approval = _auto_approval_router(settings)
    blockers = _preflight_blockers(auto_approval)
    stage_recorded = not blockers
    phase5_idempotency_keys = _phase5_idempotency_keys(settings)
    staging_records = _staging_records(
        auto_approval,
        stage_recorded=stage_recorded,
        phase5_idempotency_keys=phase5_idempotency_keys,
    )
    staged_records = [
        record for record in staging_records if record.get("status") == "staged"
    ]
    idempotency_keys = [
        str(record.get("idempotency_key"))
        for record in staged_records
        if str(record.get("idempotency_key") or "").strip()
    ]
    proof_order_ids = [
        str(record.get("proof_order_id"))
        for record in staged_records
        if str(record.get("proof_order_id") or "").strip()
    ]
    unsafe_counts = phase7_unsafe_counter_defaults()
    authority_defaults = phase7_authority_defaults()
    authority_defaults["phase7_test_mode_auto_approval_allowed"] = stage_recorded
    authority_defaults["phase7_proof_order_staging_allowed"] = stage_recorded
    status = "ready_no_staged_orders"
    stage_status = "proof_order_staging_ready_no_auto_approved_setups"
    if staged_records:
        status = "staged_orders_recorded"
        stage_status = "proof_order_staging_records_written"
    if not stage_recorded:
        status = "blocked"
        stage_status = "proof_order_staging_blocked"
    artifact = {
        "schema_version": PHASE7_PROOF_ORDER_STAGING_SCHEMA_VERSION,
        "phase7_artifact_schema_version": PHASE7_ARTIFACT_SCHEMA_VERSION,
        "artifact_type": "phase7_proof_order_staging",
        "artifact_id": "phase7:q7-6:proof-order-staging",
        "phase": "Q7",
        "stage": "Q7-6",
        "status": status,
        "stage_status": stage_status,
        "generated_at": _now(),
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
        "authority_ledger": _authority_ledger(stage_recorded),
        "proof_contract": phase7_proof_contract(),
        "source_posture": phase7_source_posture(),
        "provenance": _provenance(),
        "staging_policy": _staging_policy(),
        "staging_decision_records": staging_records,
        "staged_order_records": staged_records,
        "boundary": PHASE7_PROOF_ORDER_STAGING_BOUNDARY,
        **authority_defaults,
        **unsafe_counts,
        "source_auto_approval_artifact_id": auto_approval.get("artifact_id"),
        "source_auto_approval_status": auto_approval.get("status"),
        "source_auto_approval_stage_status": auto_approval.get("stage_status"),
        "source_auto_approved_setup_count": int(
            auto_approval.get("auto_approved_setup_count", 0) or 0
        ),
        "source_approval_decision_record_count": int(
            auto_approval.get("approval_decision_record_count", 0) or 0
        ),
        "q7_6_proof_order_staging_stage_allowed": (
            auto_approval.get("q7_6_proof_order_staging_stage_allowed") is True
        ),
        "q7_7_guarded_alpaca_paper_submit_path_stage_allowed": stage_recorded,
        "proof_order_staging_recorded": stage_recorded,
        "proof_order_staging_allowed": stage_recorded,
        "staging_decision_record_count": len(staging_records),
        "staged_order_count": len(staged_records),
        "proof_order_staged_count": len(staged_records),
        "blocked_staging_decision_count": sum(
            1 for record in staging_records if record.get("status") == "blocked"
        ),
        "auto_approved_setup_count": int(
            auto_approval.get("auto_approved_setup_count", 0) or 0
        ),
        "qualified_setup_count": int(auto_approval.get("qualified_setup_count", 0) or 0),
        "idempotency_namespace": "phase7_demo_proof",
        "idempotency_key_count": len(idempotency_keys),
        "duplicate_idempotency_key_count": _duplicate_count(idempotency_keys),
        "duplicate_proof_order_id_count": _duplicate_count(proof_order_ids),
        "phase5_order_id_reuse_count": sum(
            1
            for record in staged_records
            if record.get("phase5_order_id_reused") is True
            or str(record.get("idempotency_key") or "").startswith("q5")
        ),
        "event_log_prewrite_required_for_staged_orders": True,
        "event_log_prewrite_ready_count": sum(
            1 for record in staged_records if record.get("event_log_prewrite_ready") is True
        ),
        "event_log_prewrite_written_count": sum(
            1
            for record in staged_records
            if record.get("event_log_prewrite_written") is True
        ),
        "pre_trade_snapshot_required": True,
        "pre_trade_snapshot_present_count": sum(
            1 for record in staged_records if record.get("pre_trade_snapshot_present") is True
        ),
        "required_check_count": len(PHASE7_PROOF_ORDER_STAGING_REQUIRED_CHECKS),
        "cancellation_condition_count": len(PHASE7_PROOF_ORDER_STAGING_CANCELLATION_CONDITIONS),
        "proof_trade_count": 0,
        "closed_proof_trade_count": 0,
        "phase5_test_trades_count_for_phase7": False,
        "q6_deferred_learning_counts_as_proof": False,
        "paper_account_starting_gbp": PHASE7_PAPER_ACCOUNT_STARTING_GBP,
        "max_drawdown_fraction": PHASE7_MAX_DRAWDOWN_FRACTION,
        "mature_closed_trade_benchmark": PHASE7_MATURE_CLOSED_TRADE_BENCHMARK,
        "statistical_immaturity_allowed": True,
        "unsafe_write_counter_total": sum(unsafe_counts.values()),
        "blockers": blockers,
        "blocker_count": len(blockers),
        "recommended_next_stage": "Q7-7 Guarded Alpaca Paper Submit Path",
    }
    artifact["validation_errors"] = validate_phase7_proof_order_staging(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "error"
        artifact["stage_status"] = "proof_order_staging_validation_error"
    return artifact


def _authority_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    stage_recorded = artifact.get("proof_order_staging_recorded") is True
    ledger = artifact.get("authority_ledger", {})
    if not isinstance(ledger, dict):
        return ["proof_order_staging_authority_ledger_missing"]
    if ledger.get("stage") != "Q7-6":
        errors.append("proof_order_staging_authority_stage_mismatch")
    if ledger.get("authority_field_count") != len(PHASE7_AUTHORITY_FLAGS):
        errors.append("proof_order_staging_authority_count_mismatch")
    expected_grants = 2 if stage_recorded else 0
    if ledger.get("explicit_authority_grant_count") != expected_grants:
        errors.append("proof_order_staging_explicit_authority_grant_count_invalid")
    expected_true = {
        "phase7_test_mode_auto_approval_allowed",
        "phase7_proof_order_staging_allowed",
    }
    for field in PHASE7_AUTHORITY_FLAGS:
        expected = stage_recorded and field in expected_true
        if artifact.get(field) is not expected:
            errors.append(f"proof_order_staging_authority_invalid:{field}")
        if ledger.get(field) is not expected:
            errors.append(f"proof_order_staging_ledger_authority_invalid:{field}")
    for field in PHASE7_UNSAFE_COUNT_FIELDS:
        if int(artifact.get(field, 0) or 0) != 0:
            errors.append(f"proof_order_staging_unsafe_count_nonzero:{field}")
    unsafe_total = sum(
        int(artifact.get(field, 0) or 0) for field in PHASE7_UNSAFE_COUNT_FIELDS
    )
    if artifact.get("unsafe_write_counter_total") != unsafe_total:
        errors.append("proof_order_staging_unsafe_total_mismatch")
    if artifact.get("unsafe_write_counter_total") != 0:
        errors.append("proof_order_staging_unsafe_total_nonzero")
    return errors


def _policy_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = artifact.get("staging_policy", {})
    if not isinstance(policy, dict):
        return ["proof_order_staging_policy_missing"]
    for field in (
        "auto_approved_setup_required",
        "qualified_setup_required",
        "source_phase_q7_required",
        "event_log_prewrite_required",
        "pre_trade_snapshot_required",
        "alpaca_paper_only",
    ):
        if policy.get(field) is not True:
            errors.append(f"proof_order_staging_policy_missing_true:{field}")
    for field in (
        "fund_manager_trade_level_approval_allowed",
        "manual_trade_level_override_allowed",
        "phase5_order_id_reuse_allowed",
        "phase5_idempotency_reuse_allowed",
        "paper_submit_allowed",
        "broker_post_allowed",
        "prediction_market_write_allowed",
        "crypto_perps_write_allowed",
        "live_endpoint_allowed",
        "proof_trade_creation_allowed",
        "proof_credit_allowed",
        "live_capital_enabled",
    ):
        if policy.get(field) is not False:
            errors.append(f"proof_order_staging_policy_forbidden:{field}")
    if policy.get("idempotency_namespace") != "phase7_demo_proof":
        errors.append("proof_order_staging_policy_namespace_invalid")
    return errors


def _staging_record_errors(record: dict[str, Any], *, event_log_written: bool) -> list[str]:
    errors: list[str] = []
    status = record.get("status")
    staged = status == "staged"
    if record.get("artifact_type") != "staged_proof_order":
        errors.append("proof_order_staging_record_type_invalid")
    if record.get("phase") != "Q7" or record.get("stage") != "Q7-6":
        errors.append("proof_order_staging_record_phase_stage_invalid")
    if tuple(record.get("required_checks", ())) != PHASE7_PROOF_ORDER_STAGING_REQUIRED_CHECKS:
        errors.append("proof_order_staging_record_required_checks_invalid")
    if record.get("required_check_count") != len(PHASE7_PROOF_ORDER_STAGING_REQUIRED_CHECKS):
        errors.append("proof_order_staging_record_required_check_count_invalid")
    checks = record.get("checks", [])
    if not isinstance(checks, list):
        errors.append("proof_order_staging_record_checks_not_list")
        checks = []
    failed_checks = [
        str(check.get("name"))
        for check in checks
        if isinstance(check, dict) and check.get("passed") is not True
    ]
    if record.get("failed_checks") != failed_checks:
        errors.append("proof_order_staging_record_failed_checks_mismatch")
    if record.get("failed_check_count") != len(failed_checks):
        errors.append("proof_order_staging_record_failed_check_count_mismatch")
    blocked_reasons = record.get("blocked_reasons", [])
    if not isinstance(blocked_reasons, list):
        errors.append("proof_order_staging_record_blocked_reasons_not_list")
        blocked_reasons = []
    if record.get("blocked_reason_count") != len(blocked_reasons):
        errors.append("proof_order_staging_record_blocked_reason_count_mismatch")
    for field in (
        "paper_submit_allowed",
        "broker_submit_ready",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "broker_write_allowed",
        "prediction_market_write_allowed",
        "crypto_perps_write_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "proof_trade_created",
        "proof_credit_allowed",
        "manual_trade_level_override_allowed",
    ):
        if record.get(field) is not False:
            errors.append(f"proof_order_staging_record_forbidden:{field}")
    if staged:
        if record.get("source_decision_state") != "auto_approved":
            errors.append("proof_order_staging_staged_without_auto_approved_state")
        if record.get("source_auto_approved") is not True:
            errors.append("proof_order_staging_staged_without_auto_approval")
        if record.get("qualified_setup") is not True:
            errors.append("proof_order_staging_staged_without_qualified_setup")
        if record.get("source_phase") != "Q7":
            errors.append("proof_order_staging_staged_non_q7_source")
        for gate_field in (
            "source_quorum_passed",
            "all_required_gates_passed",
            "risk_gate_passed",
            "execution_policy_gate_passed",
            "kill_switches_clear",
            "venue_available",
            "broker_paper_ready",
        ):
            if record.get(gate_field) is not True:
                errors.append(f"proof_order_staging_staged_gate_not_passed:{gate_field}")
        if record.get("selected_venue") != "alpaca_paper":
            errors.append("proof_order_staging_staged_non_alpaca_venue")
        if str(record.get("side") or "") not in {"buy", "sell"}:
            errors.append("proof_order_staging_staged_side_invalid")
        if _float(record.get("quantity"), 0.0) <= 0.0:
            errors.append("proof_order_staging_staged_quantity_invalid")
        if str(record.get("order_type") or "") not in {"market", "limit", "stop", "stop_limit"}:
            errors.append("proof_order_staging_staged_order_type_invalid")
        if str(record.get("time_in_force") or "") not in {"day", "gtc", "opg", "cls", "ioc", "fok"}:
            errors.append("proof_order_staging_staged_tif_invalid")
        if not str(record.get("proof_order_id") or "").startswith("q7-proof-order-"):
            errors.append("proof_order_staging_proof_order_id_invalid")
        if not str(record.get("idempotency_key") or "").startswith("q7-6-stage-"):
            errors.append("proof_order_staging_idempotency_key_invalid")
        if record.get("idempotency_namespace") != "phase7_demo_proof":
            errors.append("proof_order_staging_idempotency_namespace_invalid")
        if record.get("idempotency_reused_from_phase5") is not False:
            errors.append("proof_order_staging_phase5_idempotency_reused")
        if record.get("phase5_order_id_reused") is not False:
            errors.append("proof_order_staging_phase5_order_id_reused")
        if str(record.get("phase5_order_id") or "").strip():
            errors.append("proof_order_staging_phase5_order_id_present")
        if record.get("pre_trade_snapshot_present") is not True:
            errors.append("proof_order_staging_pre_trade_snapshot_missing")
        if not isinstance(record.get("pre_trade_snapshot"), dict):
            errors.append("proof_order_staging_pre_trade_snapshot_invalid")
        if record.get("event_log_prewrite_ready") is not True:
            errors.append("proof_order_staging_event_log_prewrite_not_ready")
        if not isinstance(record.get("event_log_prewrite_payload"), dict):
            errors.append("proof_order_staging_event_log_prewrite_payload_missing")
        if not str(record.get("event_log_prewrite_fingerprint") or "").strip():
            errors.append("proof_order_staging_event_log_prewrite_fingerprint_missing")
        if event_log_written and record.get("event_log_prewrite_written") is not True:
            errors.append("proof_order_staging_event_log_prewrite_not_written")
        if record.get("staged_order_created") is not True:
            errors.append("proof_order_staging_staged_record_not_created")
        if failed_checks:
            errors.append("proof_order_staging_staged_with_failed_checks")
        if blocked_reasons:
            errors.append("proof_order_staging_staged_with_blockers")
    else:
        if record.get("staged_order_created") is not False:
            errors.append("proof_order_staging_blocked_record_created_order")
        if str(record.get("idempotency_key") or "").strip():
            errors.append("proof_order_staging_blocked_record_has_idempotency")
        if str(record.get("proof_order_id") or "").strip():
            errors.append("proof_order_staging_blocked_record_has_order_id")
        if record.get("event_log_prewrite_ready") is not False:
            errors.append("proof_order_staging_blocked_prewrite_ready")
        if record.get("pre_trade_snapshot_present") is not False:
            errors.append("proof_order_staging_blocked_snapshot_present")
    return errors


def validate_phase7_proof_order_staging(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schema_version",
        "phase7_artifact_schema_version",
        "artifact_type",
        "artifact_id",
        "phase",
        "stage",
        "status",
        "stage_status",
        "generated_at",
        "public_safe",
        "event_log_required",
        "event_log_written",
        "authority_ledger",
        "proof_contract",
        "source_posture",
        "provenance",
        "staging_policy",
        "staging_decision_records",
        "staged_order_records",
        "boundary",
        "source_auto_approval_status",
        "q7_6_proof_order_staging_stage_allowed",
        "q7_7_guarded_alpaca_paper_submit_path_stage_allowed",
        "proof_order_staging_recorded",
        "proof_order_staging_allowed",
        "staging_decision_record_count",
        "staged_order_count",
        "proof_order_staged_count",
        "blocked_staging_decision_count",
        "auto_approved_setup_count",
        "qualified_setup_count",
        "idempotency_namespace",
        "idempotency_key_count",
        "duplicate_idempotency_key_count",
        "duplicate_proof_order_id_count",
        "phase5_order_id_reuse_count",
        "event_log_prewrite_required_for_staged_orders",
        "event_log_prewrite_ready_count",
        "event_log_prewrite_written_count",
        "pre_trade_snapshot_required",
        "pre_trade_snapshot_present_count",
        "required_check_count",
        "cancellation_condition_count",
        "proof_trade_count",
        "closed_proof_trade_count",
        "phase5_test_trades_count_for_phase7",
        "q6_deferred_learning_counts_as_proof",
        "paper_account_starting_gbp",
        "max_drawdown_fraction",
        "mature_closed_trade_benchmark",
        "statistical_immaturity_allowed",
        "unsafe_write_counter_total",
        "blockers",
        "blocker_count",
        "recommended_next_stage",
    }
    missing = sorted(required_fields - set(artifact))
    if missing:
        errors.append("proof_order_staging_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PHASE7_PROOF_ORDER_STAGING_SCHEMA_VERSION:
        errors.append("proof_order_staging_schema_version_mismatch")
    if artifact.get("phase7_artifact_schema_version") != PHASE7_ARTIFACT_SCHEMA_VERSION:
        errors.append("proof_order_staging_artifact_schema_version_mismatch")
    if artifact.get("artifact_type") != "phase7_proof_order_staging":
        errors.append("proof_order_staging_artifact_type_mismatch")
    if artifact.get("phase") != "Q7" or artifact.get("stage") != "Q7-6":
        errors.append("proof_order_staging_phase_stage_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("proof_order_staging_not_public_safe")
    if artifact.get("event_log_required") is not True:
        errors.append("proof_order_staging_event_log_not_required")

    blockers = artifact.get("blockers", [])
    if not isinstance(blockers, list):
        errors.append("proof_order_staging_blockers_not_list")
        blockers = []
    if artifact.get("blocker_count") != len(blockers):
        errors.append("proof_order_staging_blocker_count_mismatch")
    stage_recorded = artifact.get("proof_order_staging_recorded") is True
    if stage_recorded:
        if artifact.get("status") not in {"ready_no_staged_orders", "staged_orders_recorded"}:
            errors.append("proof_order_staging_status_invalid")
        if artifact.get("stage_status") not in {
            "proof_order_staging_ready_no_auto_approved_setups",
            "proof_order_staging_records_written",
        }:
            errors.append("proof_order_staging_stage_status_invalid")
        if blockers:
            errors.append("proof_order_staging_recorded_with_blockers")
        if artifact.get("proof_order_staging_allowed") is not True:
            errors.append("proof_order_staging_not_allowed")
        if artifact.get("q7_7_guarded_alpaca_paper_submit_path_stage_allowed") is not True:
            errors.append("q7_7_guarded_alpaca_paper_submit_path_not_allowed")
    else:
        if artifact.get("status") not in {"blocked", "error"}:
            errors.append("proof_order_staging_blocked_status_invalid")
        if not blockers and artifact.get("status") != "error":
            errors.append("proof_order_staging_blocked_without_blockers")
        if artifact.get("proof_order_staging_allowed") is not False:
            errors.append("proof_order_staging_allowed_while_blocked")
        if artifact.get("q7_7_guarded_alpaca_paper_submit_path_stage_allowed") is not False:
            errors.append("q7_7_stage_allowed_while_blocked")

    if artifact.get("q7_6_proof_order_staging_stage_allowed") is not True:
        errors.append("q7_6_proof_order_staging_not_allowed")
    if artifact.get("source_auto_approval_status") not in {
        "ready_no_auto_approved_setups",
        "auto_approval_ready",
    }:
        errors.append("proof_order_staging_source_auto_approval_status_invalid")
    errors.extend(_authority_errors(artifact))
    errors.extend(_policy_errors(artifact))

    staging_records = artifact.get("staging_decision_records", [])
    staged_records = artifact.get("staged_order_records", [])
    if not isinstance(staging_records, list):
        errors.append("proof_order_staging_decision_records_not_list")
        staging_records = []
    if not isinstance(staged_records, list):
        errors.append("proof_order_staging_staged_records_not_list")
        staged_records = []
    for record in staging_records:
        if isinstance(record, dict):
            errors.extend(
                _staging_record_errors(
                    record,
                    event_log_written=artifact.get("event_log_written") is True,
                )
            )
        else:
            errors.append("proof_order_staging_decision_record_invalid")
    staged_from_decisions = [
        record
        for record in staging_records
        if isinstance(record, dict) and record.get("status") == "staged"
    ]
    if staged_records != staged_from_decisions:
        errors.append("proof_order_staging_staged_records_mismatch")
    idempotency_keys = [
        str(record.get("idempotency_key"))
        for record in staged_records
        if isinstance(record, dict) and str(record.get("idempotency_key") or "").strip()
    ]
    proof_order_ids = [
        str(record.get("proof_order_id"))
        for record in staged_records
        if isinstance(record, dict) and str(record.get("proof_order_id") or "").strip()
    ]
    if artifact.get("staging_decision_record_count") != len(staging_records):
        errors.append("proof_order_staging_decision_count_mismatch")
    if artifact.get("staged_order_count") != len(staged_records):
        errors.append("proof_order_staging_staged_count_mismatch")
    if artifact.get("proof_order_staged_count") != len(staged_records):
        errors.append("proof_order_staging_proof_order_staged_count_mismatch")
    blocked_count = sum(
        1 for record in staging_records if isinstance(record, dict) and record.get("status") == "blocked"
    )
    if artifact.get("blocked_staging_decision_count") != blocked_count:
        errors.append("proof_order_staging_blocked_count_mismatch")
    if artifact.get("idempotency_key_count") != len(idempotency_keys):
        errors.append("proof_order_staging_idempotency_key_count_mismatch")
    duplicate_idempotency_count = _duplicate_count(idempotency_keys)
    duplicate_order_count = _duplicate_count(proof_order_ids)
    if artifact.get("duplicate_idempotency_key_count") != duplicate_idempotency_count:
        errors.append("proof_order_staging_duplicate_idempotency_count_mismatch")
    if artifact.get("duplicate_proof_order_id_count") != duplicate_order_count:
        errors.append("proof_order_staging_duplicate_order_count_mismatch")
    if duplicate_idempotency_count:
        errors.append("proof_order_staging_duplicate_idempotency_key")
    if duplicate_order_count:
        errors.append("proof_order_staging_duplicate_proof_order_id")
    phase5_reuse_count = sum(
        1
        for record in staged_records
        if isinstance(record, dict)
        and (
            record.get("phase5_order_id_reused") is True
            or str(record.get("phase5_order_id") or "").strip()
            or str(record.get("idempotency_key") or "").startswith("q5")
        )
    )
    if artifact.get("phase5_order_id_reuse_count") != phase5_reuse_count:
        errors.append("proof_order_staging_phase5_reuse_count_mismatch")
    if phase5_reuse_count:
        errors.append("proof_order_staging_phase5_order_id_reuse")
    if artifact.get("auto_approved_setup_count") < len(staged_records):
        errors.append("proof_order_staging_more_staged_than_auto_approved")
    if artifact.get("event_log_prewrite_required_for_staged_orders") is not True:
        errors.append("proof_order_staging_prewrite_not_required")
    if artifact.get("pre_trade_snapshot_required") is not True:
        errors.append("proof_order_staging_snapshot_not_required")
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
    snapshot_present = sum(
        1
        for record in staged_records
        if isinstance(record, dict) and record.get("pre_trade_snapshot_present") is True
    )
    if artifact.get("event_log_prewrite_ready_count") != prewrite_ready:
        errors.append("proof_order_staging_prewrite_ready_count_mismatch")
    if artifact.get("event_log_prewrite_written_count") != prewrite_written:
        errors.append("proof_order_staging_prewrite_written_count_mismatch")
    if artifact.get("pre_trade_snapshot_present_count") != snapshot_present:
        errors.append("proof_order_staging_snapshot_present_count_mismatch")
    if artifact.get("event_log_written") is True and staged_records:
        if prewrite_written != len(staged_records):
            errors.append("proof_order_staging_not_all_prewrites_written")
    if artifact.get("required_check_count") != len(PHASE7_PROOF_ORDER_STAGING_REQUIRED_CHECKS):
        errors.append("proof_order_staging_required_check_count_mismatch")
    if artifact.get("cancellation_condition_count") != len(
        PHASE7_PROOF_ORDER_STAGING_CANCELLATION_CONDITIONS
    ):
        errors.append("proof_order_staging_cancellation_condition_count_mismatch")

    for count_field in (
        "proof_trade_count",
        "closed_proof_trade_count",
        "paper_order_submitted_count",
        "broker_post_called_count",
        "alpaca_post_called_count",
        "proof_trade_created_count",
        "proof_trade_credit_count",
        "phase7_proof_credit_allowed_count",
        "manual_trade_level_override_count",
    ):
        if int(artifact.get(count_field, 0) or 0) != 0:
            errors.append(f"proof_order_staging_count_nonzero:{count_field}")
    for field in (
        "phase5_test_trades_count_for_phase7",
        "q6_deferred_learning_counts_as_proof",
        "phase7_proof_trade_submission_allowed",
        "phase7_proof_trade_execution_allowed",
        "phase7_proof_credit_allowed",
        "broker_post_allowed",
        "alpaca_post_allowed",
        "broker_write_allowed",
        "prediction_market_write_allowed",
        "crypto_perps_write_allowed",
        "live_endpoint_allowed",
        "live_capital_enabled",
        "manual_trade_level_override_allowed",
    ):
        if artifact.get(field) is not False:
            errors.append(f"proof_order_staging_forbidden:{field}")
    if artifact.get("idempotency_namespace") != "phase7_demo_proof":
        errors.append("proof_order_staging_namespace_invalid")
    if float(artifact.get("paper_account_starting_gbp", 0.0) or 0.0) != (
        PHASE7_PAPER_ACCOUNT_STARTING_GBP
    ):
        errors.append("proof_order_staging_paper_account_starting_gbp_mismatch")
    if float(artifact.get("max_drawdown_fraction", 0.0) or 0.0) != (
        PHASE7_MAX_DRAWDOWN_FRACTION
    ):
        errors.append("proof_order_staging_max_drawdown_fraction_mismatch")
    if artifact.get("mature_closed_trade_benchmark") != PHASE7_MATURE_CLOSED_TRADE_BENCHMARK:
        errors.append("proof_order_staging_mature_benchmark_mismatch")
    if artifact.get("statistical_immaturity_allowed") is not True:
        errors.append("proof_order_staging_statistical_immaturity_not_allowed")

    source_posture = artifact.get("source_posture", {})
    if not isinstance(source_posture, dict):
        errors.append("proof_order_staging_source_posture_missing")
        source_posture = {}
    if source_posture.get("supplemental_source_bypass_allowed") is not False:
        errors.append("proof_order_staging_supplemental_bypass_allowed")
    if source_posture.get("preference_mcp_source_quorum_credit_allowed") is not False:
        errors.append("proof_order_staging_preference_quorum_credit_allowed")
    if source_posture.get("qctrl_role") != "shadow_annotation_only":
        errors.append("proof_order_staging_qctrl_role_invalid")

    proof_contract = artifact.get("proof_contract", {})
    if not isinstance(proof_contract, dict):
        errors.append("proof_order_staging_proof_contract_missing")
        proof_contract = {}
    if proof_contract.get("harness_day_count") != PHASE7_HARNESS_DAY_COUNT:
        errors.append("proof_order_staging_proof_contract_day_count_mismatch")
    if proof_contract.get("phase5_test_trade_reuse_allowed") is not False:
        errors.append("proof_order_staging_proof_contract_phase5_reuse_allowed")
    if proof_contract.get("manual_trade_level_override_allowed") is not False:
        errors.append("proof_order_staging_proof_contract_manual_override_allowed")

    provenance = artifact.get("provenance", {})
    if not isinstance(provenance, dict):
        errors.append("proof_order_staging_provenance_missing")
        provenance = {}
    for ref in provenance.get("source_refs", []) or []:
        ref_text = str(ref)
        lowered = ref_text.lower()
        if ref_text.startswith("/") or ref_text.startswith("~"):
            errors.append("proof_order_staging_provenance_local_path_leak")
        if "api_key" in lowered or "secret" in lowered or "token" in lowered:
            errors.append("proof_order_staging_provenance_secret_ref_leak")
    for field in (
        "raw_secret_exposed",
        "raw_payload_exposed",
        "local_path_exposed",
        "broker_identifier_exposed",
    ):
        if provenance.get(field) is not False:
            errors.append(f"proof_order_staging_provenance_exposure_enabled:{field}")

    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "only from Q7-5 auto-approved qualified setups",
        "cannot reuse Phase 5 order IDs",
        "cannot submit paper orders",
        "cannot call broker POST routes",
        "cannot write prediction-market or crypto-perps orders",
        "cannot enable live capital",
    ):
        if phrase not in boundary:
            errors.append("proof_order_staging_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("proof_order_staging_event_log_path_missing")
        if artifact.get("event_log_event_count") < 1:
            errors.append("proof_order_staging_event_log_count_invalid")
    return sorted(set(errors))


def _refresh_counts(output: dict[str, Any]) -> None:
    staged_records = [
        record
        for record in output.get("staged_order_records", []) or []
        if isinstance(record, dict)
    ]
    output["event_log_prewrite_written_count"] = sum(
        1 for record in staged_records if record.get("event_log_prewrite_written") is True
    )


def attach_phase7_proof_order_staging_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[EventLogEntry]]:
    output = deepcopy(artifact)
    log_path = Path(event_log_path or (_runtime_dir(settings) / PHASE7_PROOF_ORDER_STAGING_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entries: list[EventLogEntry] = []
    staged_records = [
        record
        for record in output.get("staged_order_records", []) or []
        if isinstance(record, dict)
    ]
    if staged_records:
        for record in staged_records:
            entry = log.write(
                PHASE7_PROOF_ORDER_STAGING_EVENT_TYPE,
                PHASE7_PROOF_ORDER_STAGING_COMPONENT,
                record.get("event_log_prewrite_payload", {}),
            )
            record["event_log_prewrite_written"] = True
            record["event_log_prewrite_correlation_id"] = entry.correlation_id
            record["event_log_prewrite_created_at"] = entry.created_at
            entries.append(entry)
        output["staging_decision_records"] = [
            next(
                (
                    staged
                    for staged in staged_records
                    if staged.get("artifact_id") == record.get("artifact_id")
                ),
                record,
            )
            for record in output.get("staging_decision_records", []) or []
        ]
        output["staged_order_records"] = staged_records
    else:
        entry = log.write(
            PHASE7_PROOF_ORDER_STAGING_EVENT_TYPE,
            PHASE7_PROOF_ORDER_STAGING_COMPONENT,
            {
                "artifact_id": output.get("artifact_id"),
                "status": output.get("status"),
                "stage_status": output.get("stage_status"),
                "proof_order_staging_allowed": output.get("proof_order_staging_allowed"),
                "source_auto_approved_setup_count": output.get(
                    "source_auto_approved_setup_count"
                ),
                "staging_decision_record_count": output.get(
                    "staging_decision_record_count"
                ),
                "staged_order_count": output.get("staged_order_count"),
                "blocked_staging_decision_count": output.get(
                    "blocked_staging_decision_count"
                ),
                "duplicate_idempotency_key_count": output.get(
                    "duplicate_idempotency_key_count"
                ),
                "phase5_order_id_reuse_count": output.get(
                    "phase5_order_id_reuse_count"
                ),
                "phase7_proof_credit_allowed": output.get(
                    "phase7_proof_credit_allowed"
                ),
                "broker_post_allowed": output.get("broker_post_allowed"),
                "live_capital_enabled": output.get("live_capital_enabled"),
                "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
                "recommended_next_stage": output.get("recommended_next_stage"),
                "boundary": output.get("boundary"),
            },
        )
        entries.append(entry)
    output["recorded"] = True
    output["event_log_written"] = True
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = len(entries)
    output["event_log_correlation_id"] = entries[-1].correlation_id if entries else None
    output["event_log_created_at"] = entries[-1].created_at if entries else None
    _refresh_counts(output)
    output["validation_errors"] = validate_phase7_proof_order_staging(output)
    if output["validation_errors"]:
        output["status"] = "error"
        output["stage_status"] = "proof_order_staging_validation_error"
    return output, entries


def write_phase7_proof_order_staging(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase7_proof_order_staging_paths(
        settings
    )
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase7_proof_order_staging_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase7_proof_order_staging(output)
        if output["validation_errors"]:
            output["status"] = "error"
            output["stage_status"] = "proof_order_staging_validation_error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase7_proof_order_staging(output)
    if output["validation_errors"]:
        output["status"] = "error"
        output["stage_status"] = "proof_order_staging_validation_error"
    output_path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    history_record = {
        "schema_version": PHASE7_PROOF_ORDER_STAGING_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "stage_status": output.get("stage_status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "proof_order_staging_allowed": output.get("proof_order_staging_allowed"),
        "staging_decision_record_count": output.get("staging_decision_record_count"),
        "staged_order_count": output.get("staged_order_count"),
        "blocked_staging_decision_count": output.get("blocked_staging_decision_count"),
        "duplicate_idempotency_key_count": output.get("duplicate_idempotency_key_count"),
        "phase5_order_id_reuse_count": output.get("phase5_order_id_reuse_count"),
        "event_log_prewrite_written_count": output.get(
            "event_log_prewrite_written_count"
        ),
        "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
        "broker_post_allowed": output.get("broker_post_allowed"),
        "live_capital_enabled": output.get("live_capital_enabled"),
        "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
        "blocker_count": output.get("blocker_count"),
        "event_log_written": output.get("event_log_written"),
        "event_log_event_count": output.get("event_log_event_count"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output
