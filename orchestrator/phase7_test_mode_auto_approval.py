"""Q7-5 Phase 7 Demo Proof test-mode auto-approval router.

This stage removes Fund Manager trade-level approval from the paper proof
decision path while preserving all source, policy, risk, and kill-switch gates.
It grants only narrow test-mode auto-approval authority. It does not stage or
submit orders, create proof trades, grant proof credit, or enable live capital.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
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
from orchestrator.phase7_qualified_setup_ledger import (
    PHASE7_QUALIFIED_SETUP_LEDGER_RUNTIME_ARTIFACT,
    QUALIFICATION_GATE_KEYS,
    build_phase7_qualified_setup_ledger,
    phase7_qualified_setup_ledger_paths,
    validate_phase7_qualified_setup_ledger,
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
from orchestrator.phase7_weekly_cadence import (
    PHASE7_WEEKLY_CADENCE_RUNTIME_ARTIFACT,
    build_phase7_weekly_cadence_tracker,
    phase7_weekly_cadence_paths,
    validate_phase7_weekly_cadence_tracker,
)


PHASE7_TEST_MODE_AUTO_APPROVAL_SCHEMA_VERSION = 1
PHASE7_TEST_MODE_AUTO_APPROVAL_RUNTIME_ARTIFACT = (
    "phase7_test_mode_auto_approval_router.json"
)
PHASE7_TEST_MODE_AUTO_APPROVAL_HISTORY = (
    "phase7_test_mode_auto_approval_router_history.jsonl"
)
PHASE7_TEST_MODE_AUTO_APPROVAL_EVENT_LOG = (
    "phase7_test_mode_auto_approval_router_events.jsonl"
)
PHASE7_TEST_MODE_AUTO_APPROVAL_EVENT_TYPE = PHASE7_EVENT_TYPES["auto_approval"]
PHASE7_TEST_MODE_AUTO_APPROVAL_COMPONENT = "phase7_test_mode_auto_approval_router"

PHASE7_TEST_MODE_AUTO_APPROVAL_BOUNDARY = (
    "Q7-5 grants narrow test-mode auto-approval authority only after a setup "
    "is qualified by Q7 source, policy, risk, execution-policy, venue, broker "
    "paper-readiness, and kill-switch gates. It cannot bypass risk or kill "
    "switches, cannot use Fund Manager trade-level approval, cannot stage or "
    "submit proof orders, cannot create proof trades, cannot grant Phase 7 "
    "proof credit, cannot reuse Phase 5 test trades as proof, cannot call "
    "broker POST routes, cannot call live endpoints, cannot enable live "
    "capital, and cannot permit manual trade-level overrides."
)

GOVERNANCE_FEEDBACK_CHANNELS: tuple[str, ...] = (
    "strategy_toggles",
    "kill_switches",
    "governance_comments",
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


def phase7_test_mode_auto_approval_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE7_TEST_MODE_AUTO_APPROVAL_RUNTIME_ARTIFACT,
        runtime / PHASE7_TEST_MODE_AUTO_APPROVAL_HISTORY,
        runtime / PHASE7_TEST_MODE_AUTO_APPROVAL_EVENT_LOG,
    )


def _setup_ledger(settings: Settings) -> dict[str, Any]:
    ledger_path, _, _ = phase7_qualified_setup_ledger_paths(settings)
    if ledger_path.exists():
        return _read_json(ledger_path)
    return build_phase7_qualified_setup_ledger(settings=settings)


def _weekly_cadence(settings: Settings) -> dict[str, Any]:
    cadence_path, _, _ = phase7_weekly_cadence_paths(settings)
    if cadence_path.exists():
        return _read_json(cadence_path)
    return build_phase7_weekly_cadence_tracker(settings=settings)


def _approval_policy() -> dict[str, Any]:
    return {
        "policy_schema_version": PHASE7_TEST_MODE_AUTO_APPROVAL_SCHEMA_VERSION,
        "approval_mode": "test_mode_auto_approval",
        "qualified_setup_required": True,
        "all_prior_gates_required": True,
        "all_required_gates_must_pass": True,
        "source_quorum_required": True,
        "risk_gate_required": True,
        "execution_policy_gate_required": True,
        "kill_switches_required_clear": True,
        "venue_availability_required": True,
        "broker_paper_readiness_required": True,
        "fund_manager_trade_level_approval_required": False,
        "fund_manager_trade_level_approval_allowed": False,
        "manual_approval_rejection_resize_exit_contaminates_sample": True,
        "manual_trade_level_override_allowed": False,
        "governance_feedback_affects_future_policy_only": True,
        "strategy_toggles_affect_future_policy_only": True,
        "kill_switch_changes_affect_future_policy_only": True,
        "auto_approval_cannot_bypass_risk_or_kill_switches": True,
        "proof_order_staging_allowed": False,
        "proof_trade_creation_allowed": False,
        "proof_credit_allowed": False,
        "broker_post_allowed": False,
        "live_capital_enabled": False,
    }


def _authority_ledger(router_recorded: bool) -> dict[str, Any]:
    defaults = phase7_authority_defaults()
    defaults["phase7_test_mode_auto_approval_allowed"] = router_recorded
    return {
        "authority_schema_version": PHASE7_TEST_MODE_AUTO_APPROVAL_SCHEMA_VERSION,
        "stage": "Q7-5",
        "authority_field_count": len(PHASE7_AUTHORITY_FLAGS),
        "explicit_authority_grant_count": 1 if router_recorded else 0,
        "explicit_authority_grants": (
            ["phase7_test_mode_auto_approval_allowed"] if router_recorded else []
        ),
        "q7_6_proof_order_staging_stage_allowed": router_recorded,
        **defaults,
        "boundary": PHASE7_TEST_MODE_AUTO_APPROVAL_BOUNDARY,
    }


def _provenance() -> dict[str, Any]:
    provenance = phase7_provenance(
        (
            f"data/runtime/{PHASE7_WEEKLY_CADENCE_RUNTIME_ARTIFACT}",
            f"data/runtime/{PHASE7_QUALIFIED_SETUP_LEDGER_RUNTIME_ARTIFACT}",
            "orchestrator/phase7_artifacts.py",
            "orchestrator/phase7_qualified_setup_ledger.py",
            "orchestrator/phase7_weekly_cadence.py",
            "docs/qadam-phase-7-demo-proof-implementation-plan.md",
            "docs/qadam-phase-7-q7-4-weekly-cadence-tracker-audit-2026-05-25.md",
        )
    )
    provenance["decision_chain_refs"] = [
        f"data/runtime/{PHASE7_QUALIFIED_SETUP_LEDGER_RUNTIME_ARTIFACT}",
        f"data/runtime/{PHASE7_WEEKLY_CADENCE_RUNTIME_ARTIFACT}",
    ]
    provenance["governance_refs"] = [
        "docs/qadam-phase-7-demo-proof-implementation-plan.md"
    ]
    return provenance


def _gate_status(record: dict[str, Any], gate_key: str) -> str:
    for gate in record.get("gate_results", []) or []:
        if isinstance(gate, dict) and gate.get("gate_key") == gate_key:
            return str(gate.get("status") or "missing")
    return "missing"


def _passed_required_gates(record: dict[str, Any]) -> set[str]:
    return {
        str(gate.get("gate_key"))
        for gate in record.get("gate_results", []) or []
        if isinstance(gate, dict) and gate.get("status") == "pass"
    }


def _base_decision_record(
    setup: dict[str, Any],
    *,
    router_recorded: bool,
) -> dict[str, Any]:
    setup_id = str(setup.get("setup_record_id") or "unknown")
    source_phase = str(setup.get("source_phase") or "unknown")
    passed_gates = _passed_required_gates(setup)
    source_quorum_passed = (
        setup.get("canonical_source_quorum_passed") is True
        or setup.get("source_quorum_passed") is True
    )
    qualified_setup = setup.get("qualified_setup") is True
    risk_gate_passed = _gate_status(setup, "risk_agent_paper_sizing") == "pass"
    execution_policy_gate_passed = _gate_status(setup, "execution_policy") == "pass"
    kill_switches_clear = _gate_status(setup, "kill_switches") == "pass"
    venue_available = _gate_status(setup, "venue_availability") == "pass"
    broker_paper_ready = _gate_status(setup, "broker_paper_readiness") == "pass"
    all_required_gates_passed = (
        setup.get("all_required_gates_passed") is True
        and passed_gates == set(QUALIFICATION_GATE_KEYS)
    )

    rejection_reasons = list(setup.get("rejection_reasons", []) or [])
    defer_reasons: list[str] = []
    expiry_reasons: list[str] = []
    if source_phase != "Q7":
        rejection_reasons.append("source_phase_not_q7")
    if setup.get("phase5_lifecycle_counts_as_q7_proof") is not False:
        rejection_reasons.append("phase5_lifecycle_counts_as_q7_proof")
    if setup.get("phase5_test_trade_counted_for_phase7") is not False:
        rejection_reasons.append("phase5_test_trade_counted_for_phase7")
    if setup.get("supplemental_only") is True:
        rejection_reasons.append("supplemental_only_setup")
    if not source_quorum_passed:
        rejection_reasons.append("canonical_source_quorum_not_passed")
    if not all_required_gates_passed:
        rejection_reasons.append("required_gates_not_passed")
    if not risk_gate_passed:
        rejection_reasons.append("risk_gate_not_passed")
    if not execution_policy_gate_passed:
        rejection_reasons.append("execution_policy_gate_not_passed")
    if not kill_switches_clear:
        rejection_reasons.append("kill_switch_not_clear")
    if not venue_available:
        rejection_reasons.append("venue_not_available")
    if not broker_paper_ready:
        rejection_reasons.append("broker_paper_not_ready")

    auto_approved = (
        router_recorded
        and qualified_setup
        and source_phase == "Q7"
        and source_quorum_passed
        and all_required_gates_passed
        and risk_gate_passed
        and execution_policy_gate_passed
        and kill_switches_clear
        and venue_available
        and broker_paper_ready
        and not rejection_reasons
    )
    if auto_approved:
        decision_state = "auto_approved"
    elif str(setup.get("setup_state") or "") == "expired":
        decision_state = "expired"
        expiry_reasons.append("source_setup_expired")
    elif qualified_setup:
        decision_state = "deferred"
        defer_reasons.extend(sorted(set(rejection_reasons)))
        rejection_reasons = []
    else:
        decision_state = "rejected"

    return {
        "decision_id": f"q7-5:auto-approval:{setup_id}",
        "artifact_type": "auto_approval_decision",
        "setup_record_id": setup_id,
        "source_phase": source_phase,
        "source_artifact_ref": setup.get("source_artifact_ref"),
        "strategy_family_key": setup.get("strategy_family_key", "unknown"),
        "instrument": setup.get("instrument", "unknown"),
        "approval_mode": "test_mode_auto_approval",
        "decision_state": decision_state,
        "auto_approved": auto_approved,
        "auto_approval_blocked": not auto_approved,
        "qualified_setup": qualified_setup,
        "eligible_setup": setup.get("eligible_setup") is True,
        "source_quorum_passed": source_quorum_passed,
        "all_required_gates_passed": all_required_gates_passed,
        "passed_required_gate_count": len(passed_gates),
        "required_gate_count": len(QUALIFICATION_GATE_KEYS),
        "risk_gate_passed": risk_gate_passed,
        "execution_policy_gate_passed": execution_policy_gate_passed,
        "kill_switches_clear": kill_switches_clear,
        "venue_available": venue_available,
        "broker_paper_ready": broker_paper_ready,
        "gate_results": deepcopy(setup.get("gate_results", []) or []),
        "rejection_reasons": sorted(set(rejection_reasons)),
        "defer_reasons": sorted(set(defer_reasons)),
        "expiry_reasons": sorted(set(expiry_reasons)),
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


def _approval_decision_records(
    setup_ledger: dict[str, Any],
    *,
    router_recorded: bool,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for setup in setup_ledger.get("qualified_setup_records", []) or []:
        if isinstance(setup, dict):
            records.append(_base_decision_record(setup, router_recorded=router_recorded))
    for setup in setup_ledger.get("candidate_setup_records", []) or []:
        if isinstance(setup, dict) and setup.get("qualified_setup") is not True:
            records.append(_base_decision_record(setup, router_recorded=router_recorded))
    return records


def _preflight_blockers(
    setup_ledger: dict[str, Any],
    weekly_cadence: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    setup_errors = validate_phase7_qualified_setup_ledger(setup_ledger)
    cadence_errors = validate_phase7_weekly_cadence_tracker(weekly_cadence)
    if setup_errors:
        blockers.append("phase7_setup_ledger_validation_errors")
    if cadence_errors:
        blockers.append("phase7_weekly_cadence_validation_errors")
    if setup_ledger.get("qualified_setup_ledger_recorded") is not True:
        blockers.append("phase7_setup_ledger_not_recorded")
    if weekly_cadence.get("weekly_cadence_tracker_recorded") is not True:
        blockers.append("phase7_weekly_cadence_not_recorded")
    if weekly_cadence.get("q7_5_test_mode_auto_approval_router_stage_allowed") is not True:
        blockers.append("q7_5_test_mode_auto_approval_router_not_allowed")
    if int(weekly_cadence.get("weekly_cadence_failed_count", 0) or 0) != 0:
        blockers.append("phase7_weekly_cadence_failed")
    if int(weekly_cadence.get("missed_qualified_setup_unexplained_count", 0) or 0) != 0:
        blockers.append("phase7_unexplained_missed_qualified_setups")
    if setup_ledger.get("phase5_test_trades_count_for_phase7") is not False:
        blockers.append("phase5_test_trades_count_for_phase7")
    if weekly_cadence.get("phase7_proof_credit_allowed") is not False:
        blockers.append("phase7_proof_credit_already_allowed")
    if weekly_cadence.get("broker_post_allowed") is not False:
        blockers.append("broker_post_already_allowed")
    if weekly_cadence.get("live_capital_enabled") is not False:
        blockers.append("live_capital_already_enabled")
    return sorted(set(blockers))


def _count_decisions(records: list[dict[str, Any]], state: str) -> int:
    return sum(1 for record in records if record.get("decision_state") == state)


def build_phase7_test_mode_auto_approval_router(
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    setup_ledger = _setup_ledger(settings)
    weekly_cadence = _weekly_cadence(settings)
    blockers = _preflight_blockers(setup_ledger, weekly_cadence)
    router_recorded = not blockers
    decision_records = _approval_decision_records(
        setup_ledger,
        router_recorded=router_recorded,
    )
    auto_approved_count = _count_decisions(decision_records, "auto_approved")
    rejected_count = _count_decisions(decision_records, "rejected")
    deferred_count = _count_decisions(decision_records, "deferred")
    expired_count = _count_decisions(decision_records, "expired")
    unsafe_counts = phase7_unsafe_counter_defaults()
    authority_defaults = phase7_authority_defaults()
    authority_defaults["phase7_test_mode_auto_approval_allowed"] = router_recorded
    status = "ready_no_auto_approved_setups"
    stage_status = "test_mode_auto_approval_router_ready_no_q7_setups"
    if auto_approved_count:
        status = "auto_approval_ready"
        stage_status = "test_mode_auto_approval_decisions_recorded"
    if not router_recorded:
        status = "blocked"
        stage_status = "test_mode_auto_approval_router_blocked"
    artifact = {
        "schema_version": PHASE7_TEST_MODE_AUTO_APPROVAL_SCHEMA_VERSION,
        "phase7_artifact_schema_version": PHASE7_ARTIFACT_SCHEMA_VERSION,
        "artifact_type": "phase7_test_mode_auto_approval_router",
        "artifact_id": "phase7:q7-5:test-mode-auto-approval-router",
        "phase": "Q7",
        "stage": "Q7-5",
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
        "authority_ledger": _authority_ledger(router_recorded),
        "proof_contract": phase7_proof_contract(),
        "source_posture": phase7_source_posture(),
        "provenance": _provenance(),
        "approval_policy": _approval_policy(),
        "approval_decision_records": decision_records,
        "boundary": PHASE7_TEST_MODE_AUTO_APPROVAL_BOUNDARY,
        **authority_defaults,
        **unsafe_counts,
        "source_setup_ledger_artifact_id": setup_ledger.get("artifact_id"),
        "source_setup_ledger_status": setup_ledger.get("status"),
        "source_setup_ledger_stage_status": setup_ledger.get("stage_status"),
        "source_weekly_cadence_artifact_id": weekly_cadence.get("artifact_id"),
        "source_weekly_cadence_status": weekly_cadence.get("status"),
        "source_weekly_cadence_stage_status": weekly_cadence.get("stage_status"),
        "q7_5_test_mode_auto_approval_router_stage_allowed": (
            weekly_cadence.get("q7_5_test_mode_auto_approval_router_stage_allowed")
            is True
        ),
        "q7_6_proof_order_staging_stage_allowed": router_recorded,
        "test_mode_auto_approval_router_recorded": router_recorded,
        "test_mode_auto_approval_allowed": router_recorded,
        "approval_decision_record_count": len(decision_records),
        "qualified_setup_count": int(setup_ledger.get("qualified_setup_count", 0) or 0),
        "qualified_setup_decision_count": sum(
            1 for record in decision_records if record.get("qualified_setup") is True
        ),
        "auto_approved_setup_count": auto_approved_count,
        "rejected_setup_decision_count": rejected_count,
        "deferred_setup_decision_count": deferred_count,
        "expired_setup_decision_count": expired_count,
        "phase5_candidate_rejected_count": sum(
            1
            for record in decision_records
            if record.get("source_phase") == "Q5"
            and record.get("decision_state") == "rejected"
        ),
        "fund_manager_trade_level_approval_count": 0,
        "manual_trade_level_approval_count": 0,
        "manual_trade_level_rejection_count": 0,
        "manual_trade_level_resize_count": 0,
        "manual_trade_level_exit_count": 0,
        "manual_trade_level_override_attempt_count": 0,
        "sample_contaminated": False,
        "contamination_reasons": [],
        "governance_feedback_channels": list(GOVERNANCE_FEEDBACK_CHANNELS),
        "governance_feedback_affects_future_policy_only": True,
        "strategy_toggles_affect_future_policy_only": True,
        "kill_switch_changes_affect_future_policy_only": True,
        "risk_or_kill_switch_bypass_count": 0,
        "source_quorum_bypass_count": 0,
        "proof_order_staged_count": 0,
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
        "recommended_next_stage": "Q7-6 Proof Order Staging And Idempotency",
    }
    artifact["validation_errors"] = validate_phase7_test_mode_auto_approval_router(
        artifact
    )
    if artifact["validation_errors"]:
        artifact["status"] = "error"
        artifact["stage_status"] = "test_mode_auto_approval_router_validation_error"
    return artifact


def _authority_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    router_recorded = artifact.get("test_mode_auto_approval_router_recorded") is True
    ledger = artifact.get("authority_ledger", {})
    if not isinstance(ledger, dict):
        return ["auto_approval_authority_ledger_missing"]
    if ledger.get("stage") != "Q7-5":
        errors.append("auto_approval_authority_stage_mismatch")
    if ledger.get("authority_field_count") != len(PHASE7_AUTHORITY_FLAGS):
        errors.append("auto_approval_authority_count_mismatch")
    expected_grants = 1 if router_recorded else 0
    if ledger.get("explicit_authority_grant_count") != expected_grants:
        errors.append("auto_approval_explicit_authority_grant_count_invalid")
    expected_grant_list = (
        ["phase7_test_mode_auto_approval_allowed"] if router_recorded else []
    )
    if ledger.get("explicit_authority_grants") != expected_grant_list:
        errors.append("auto_approval_explicit_authority_grants_invalid")
    for field in PHASE7_AUTHORITY_FLAGS:
        expected = router_recorded and field == "phase7_test_mode_auto_approval_allowed"
        if artifact.get(field) is not expected:
            errors.append(f"auto_approval_authority_invalid:{field}")
        if ledger.get(field) is not expected:
            errors.append(f"auto_approval_ledger_authority_invalid:{field}")
    for field in PHASE7_UNSAFE_COUNT_FIELDS:
        if int(artifact.get(field, 0) or 0) != 0:
            errors.append(f"auto_approval_unsafe_count_nonzero:{field}")
    unsafe_total = sum(
        int(artifact.get(field, 0) or 0) for field in PHASE7_UNSAFE_COUNT_FIELDS
    )
    if artifact.get("unsafe_write_counter_total") != unsafe_total:
        errors.append("auto_approval_unsafe_total_mismatch")
    if artifact.get("unsafe_write_counter_total") != 0:
        errors.append("auto_approval_unsafe_total_nonzero")
    return errors


def _policy_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = artifact.get("approval_policy", {})
    if not isinstance(policy, dict):
        return ["auto_approval_policy_missing"]
    for field in (
        "qualified_setup_required",
        "all_prior_gates_required",
        "all_required_gates_must_pass",
        "source_quorum_required",
        "risk_gate_required",
        "execution_policy_gate_required",
        "kill_switches_required_clear",
        "venue_availability_required",
        "broker_paper_readiness_required",
        "manual_approval_rejection_resize_exit_contaminates_sample",
        "governance_feedback_affects_future_policy_only",
        "strategy_toggles_affect_future_policy_only",
        "kill_switch_changes_affect_future_policy_only",
        "auto_approval_cannot_bypass_risk_or_kill_switches",
    ):
        if policy.get(field) is not True:
            errors.append(f"auto_approval_policy_missing_true:{field}")
    for field in (
        "fund_manager_trade_level_approval_required",
        "fund_manager_trade_level_approval_allowed",
        "manual_trade_level_override_allowed",
        "proof_order_staging_allowed",
        "proof_trade_creation_allowed",
        "proof_credit_allowed",
        "broker_post_allowed",
        "live_capital_enabled",
    ):
        if policy.get(field) is not False:
            errors.append(f"auto_approval_policy_forbidden:{field}")
    if policy.get("approval_mode") != "test_mode_auto_approval":
        errors.append("auto_approval_policy_mode_invalid")
    return errors


def _decision_record_errors(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    records = artifact.get("approval_decision_records", [])
    if not isinstance(records, list):
        return ["auto_approval_decision_records_not_list"]
    for record in records:
        if not isinstance(record, dict):
            errors.append("auto_approval_decision_record_invalid")
            continue
        if record.get("artifact_type") != "auto_approval_decision":
            errors.append("auto_approval_decision_type_invalid")
        if record.get("approval_mode") != "test_mode_auto_approval":
            errors.append("auto_approval_decision_mode_invalid")
        if record.get("fund_manager_trade_level_approval_required") is not False:
            errors.append("auto_approval_decision_fund_manager_required")
        if record.get("fund_manager_trade_level_approval_recorded") is not False:
            errors.append("auto_approval_decision_fund_manager_recorded")
        if record.get("manual_trade_level_override_attempted") is not False:
            errors.append("auto_approval_decision_manual_override_attempted")
        if record.get("manual_attempt_contaminates_sample") is not True:
            errors.append("auto_approval_manual_attempt_not_contaminating")
        for field in (
            "proof_order_staging_allowed",
            "proof_trade_creation_allowed",
            "proof_credit_allowed",
            "broker_post_allowed",
            "live_endpoint_allowed",
            "live_capital_enabled",
        ):
            if record.get(field) is not False:
                errors.append(f"auto_approval_decision_forbidden:{field}")
        if record.get("auto_approved") is True:
            if record.get("decision_state") != "auto_approved":
                errors.append("auto_approval_state_mismatch")
            if record.get("qualified_setup") is not True:
                errors.append("auto_approval_unqualified_setup")
            if record.get("source_phase") != "Q7":
                errors.append("auto_approval_non_q7_setup")
            if record.get("source_quorum_passed") is not True:
                errors.append("auto_approval_source_quorum_bypass")
            if record.get("all_required_gates_passed") is not True:
                errors.append("auto_approval_required_gate_bypass")
            if record.get("risk_gate_passed") is not True:
                errors.append("auto_approval_risk_gate_bypass")
            if record.get("execution_policy_gate_passed") is not True:
                errors.append("auto_approval_execution_policy_bypass")
            if record.get("kill_switches_clear") is not True:
                errors.append("auto_approval_kill_switch_bypass")
            if record.get("venue_available") is not True:
                errors.append("auto_approval_venue_bypass")
            if record.get("broker_paper_ready") is not True:
                errors.append("auto_approval_broker_readiness_bypass")
            if record.get("rejection_reasons"):
                errors.append("auto_approval_with_rejection_reasons")
            if record.get("defer_reasons"):
                errors.append("auto_approval_with_defer_reasons")
            if record.get("expiry_reasons"):
                errors.append("auto_approval_with_expiry_reasons")
        else:
            if record.get("decision_state") == "auto_approved":
                errors.append("auto_approval_false_but_state_approved")
            if record.get("auto_approval_blocked") is not True:
                errors.append("auto_approval_blocked_flag_missing")
            if record.get("decision_state") == "rejected" and not record.get(
                "rejection_reasons"
            ):
                errors.append("auto_approval_rejection_reasons_missing")
            if record.get("decision_state") == "deferred" and not record.get(
                "defer_reasons"
            ):
                errors.append("auto_approval_defer_reasons_missing")
            if record.get("decision_state") == "expired" and not record.get(
                "expiry_reasons"
            ):
                errors.append("auto_approval_expiry_reasons_missing")
    return errors


def validate_phase7_test_mode_auto_approval_router(
    artifact: dict[str, Any],
) -> list[str]:
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
        "approval_policy",
        "approval_decision_records",
        "boundary",
        "source_setup_ledger_status",
        "source_weekly_cadence_status",
        "q7_5_test_mode_auto_approval_router_stage_allowed",
        "q7_6_proof_order_staging_stage_allowed",
        "test_mode_auto_approval_router_recorded",
        "test_mode_auto_approval_allowed",
        "approval_decision_record_count",
        "qualified_setup_count",
        "qualified_setup_decision_count",
        "auto_approved_setup_count",
        "rejected_setup_decision_count",
        "deferred_setup_decision_count",
        "expired_setup_decision_count",
        "phase5_candidate_rejected_count",
        "fund_manager_trade_level_approval_count",
        "manual_trade_level_approval_count",
        "manual_trade_level_rejection_count",
        "manual_trade_level_resize_count",
        "manual_trade_level_exit_count",
        "manual_trade_level_override_attempt_count",
        "sample_contaminated",
        "contamination_reasons",
        "governance_feedback_channels",
        "governance_feedback_affects_future_policy_only",
        "strategy_toggles_affect_future_policy_only",
        "kill_switch_changes_affect_future_policy_only",
        "risk_or_kill_switch_bypass_count",
        "source_quorum_bypass_count",
        "proof_order_staged_count",
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
        errors.append("auto_approval_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PHASE7_TEST_MODE_AUTO_APPROVAL_SCHEMA_VERSION:
        errors.append("auto_approval_schema_version_mismatch")
    if artifact.get("phase7_artifact_schema_version") != PHASE7_ARTIFACT_SCHEMA_VERSION:
        errors.append("auto_approval_artifact_schema_version_mismatch")
    if artifact.get("artifact_type") != "phase7_test_mode_auto_approval_router":
        errors.append("auto_approval_artifact_type_mismatch")
    if artifact.get("phase") != "Q7" or artifact.get("stage") != "Q7-5":
        errors.append("auto_approval_phase_stage_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("auto_approval_not_public_safe")
    if artifact.get("event_log_required") is not True:
        errors.append("auto_approval_event_log_not_required")

    blockers = artifact.get("blockers", [])
    if not isinstance(blockers, list):
        errors.append("auto_approval_blockers_not_list")
        blockers = []
    if artifact.get("blocker_count") != len(blockers):
        errors.append("auto_approval_blocker_count_mismatch")
    router_recorded = artifact.get("test_mode_auto_approval_router_recorded") is True
    if router_recorded:
        if artifact.get("status") not in {
            "ready_no_auto_approved_setups",
            "auto_approval_ready",
        }:
            errors.append("auto_approval_status_invalid")
        if artifact.get("stage_status") not in {
            "test_mode_auto_approval_router_ready_no_q7_setups",
            "test_mode_auto_approval_decisions_recorded",
        }:
            errors.append("auto_approval_stage_status_invalid")
        if blockers:
            errors.append("auto_approval_recorded_with_blockers")
        if artifact.get("test_mode_auto_approval_allowed") is not True:
            errors.append("test_mode_auto_approval_not_allowed")
        if artifact.get("q7_6_proof_order_staging_stage_allowed") is not True:
            errors.append("q7_6_proof_order_staging_not_allowed")
    else:
        if artifact.get("status") not in {"blocked", "error"}:
            errors.append("auto_approval_blocked_status_invalid")
        if not blockers and artifact.get("status") != "error":
            errors.append("auto_approval_blocked_without_blockers")
        if artifact.get("test_mode_auto_approval_allowed") is not False:
            errors.append("test_mode_auto_approval_allowed_while_blocked")
        if artifact.get("q7_6_proof_order_staging_stage_allowed") is not False:
            errors.append("q7_6_stage_allowed_while_auto_approval_blocked")

    if artifact.get("q7_5_test_mode_auto_approval_router_stage_allowed") is not True:
        errors.append("q7_5_test_mode_auto_approval_router_not_allowed")
    if artifact.get("source_setup_ledger_status") != "read_only_no_q7_setups":
        errors.append("auto_approval_source_setup_status_invalid")
    if artifact.get("source_weekly_cadence_status") != "cadence_satisfied_no_q7_setups":
        errors.append("auto_approval_source_cadence_status_invalid")

    errors.extend(_authority_errors(artifact))
    errors.extend(_policy_errors(artifact))
    errors.extend(_decision_record_errors(artifact))

    records = artifact.get("approval_decision_records", [])
    if isinstance(records, list):
        if artifact.get("approval_decision_record_count") != len(records):
            errors.append("auto_approval_decision_count_mismatch")
        auto_count = _count_decisions(records, "auto_approved")
        rejected_count = _count_decisions(records, "rejected")
        deferred_count = _count_decisions(records, "deferred")
        expired_count = _count_decisions(records, "expired")
        qualified_decisions = sum(
            1
            for record in records
            if isinstance(record, dict) and record.get("qualified_setup") is True
        )
        phase5_rejected_count = sum(
            1
            for record in records
            if isinstance(record, dict)
            and record.get("source_phase") == "Q5"
            and record.get("decision_state") == "rejected"
        )
        if artifact.get("auto_approved_setup_count") != auto_count:
            errors.append("auto_approval_count_mismatch")
        if artifact.get("rejected_setup_decision_count") != rejected_count:
            errors.append("auto_approval_rejected_count_mismatch")
        if artifact.get("deferred_setup_decision_count") != deferred_count:
            errors.append("auto_approval_deferred_count_mismatch")
        if artifact.get("expired_setup_decision_count") != expired_count:
            errors.append("auto_approval_expired_count_mismatch")
        if artifact.get("qualified_setup_decision_count") != qualified_decisions:
            errors.append("auto_approval_qualified_decision_count_mismatch")
        if artifact.get("phase5_candidate_rejected_count") != phase5_rejected_count:
            errors.append("auto_approval_phase5_rejected_count_mismatch")
        if auto_count > int(artifact.get("qualified_setup_count", 0) or 0):
            errors.append("auto_approval_count_exceeds_qualified_setups")

    for count_field in (
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
        "closed_proof_trade_count",
    ):
        if int(artifact.get(count_field, 0) or 0) != 0:
            errors.append(f"auto_approval_count_nonzero:{count_field}")
    if artifact.get("sample_contaminated") is not False:
        errors.append("auto_approval_sample_contaminated")
    contamination_reasons = artifact.get("contamination_reasons", [])
    if not isinstance(contamination_reasons, list):
        errors.append("auto_approval_contamination_reasons_not_list")
    elif contamination_reasons:
        errors.append("auto_approval_contamination_reasons_present")
    if tuple(artifact.get("governance_feedback_channels", ())) != (
        GOVERNANCE_FEEDBACK_CHANNELS
    ):
        errors.append("auto_approval_governance_channels_invalid")
    for field in (
        "governance_feedback_affects_future_policy_only",
        "strategy_toggles_affect_future_policy_only",
        "kill_switch_changes_affect_future_policy_only",
        "statistical_immaturity_allowed",
    ):
        if artifact.get(field) is not True:
            errors.append(f"auto_approval_missing_true:{field}")
    for field in (
        "phase5_test_trades_count_for_phase7",
        "q6_deferred_learning_counts_as_proof",
        "phase7_proof_order_staging_allowed",
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
            errors.append(f"auto_approval_forbidden:{field}")
    if float(artifact.get("paper_account_starting_gbp", 0.0) or 0.0) != (
        PHASE7_PAPER_ACCOUNT_STARTING_GBP
    ):
        errors.append("auto_approval_paper_account_starting_gbp_mismatch")
    if float(artifact.get("max_drawdown_fraction", 0.0) or 0.0) != (
        PHASE7_MAX_DRAWDOWN_FRACTION
    ):
        errors.append("auto_approval_max_drawdown_fraction_mismatch")
    if artifact.get("mature_closed_trade_benchmark") != PHASE7_MATURE_CLOSED_TRADE_BENCHMARK:
        errors.append("auto_approval_mature_benchmark_mismatch")

    source_posture = artifact.get("source_posture", {})
    if not isinstance(source_posture, dict):
        errors.append("auto_approval_source_posture_missing")
        source_posture = {}
    if source_posture.get("supplemental_source_bypass_allowed") is not False:
        errors.append("auto_approval_supplemental_bypass_allowed")
    if source_posture.get("preference_mcp_source_quorum_credit_allowed") is not False:
        errors.append("auto_approval_preference_quorum_credit_allowed")
    if source_posture.get("qctrl_role") != "shadow_annotation_only":
        errors.append("auto_approval_qctrl_role_invalid")

    proof_contract = artifact.get("proof_contract", {})
    if not isinstance(proof_contract, dict):
        errors.append("auto_approval_proof_contract_missing")
        proof_contract = {}
    if proof_contract.get("harness_day_count") != PHASE7_HARNESS_DAY_COUNT:
        errors.append("auto_approval_proof_contract_day_count_mismatch")
    if proof_contract.get("phase5_test_trade_reuse_allowed") is not False:
        errors.append("auto_approval_proof_contract_phase5_reuse_allowed")
    if proof_contract.get("manual_trade_level_override_allowed") is not False:
        errors.append("auto_approval_proof_contract_manual_override_allowed")

    provenance = artifact.get("provenance", {})
    if not isinstance(provenance, dict):
        errors.append("auto_approval_provenance_missing")
        provenance = {}
    for ref in provenance.get("source_refs", []) or []:
        ref_text = str(ref)
        lowered = ref_text.lower()
        if ref_text.startswith("/") or ref_text.startswith("~"):
            errors.append("auto_approval_provenance_local_path_leak")
        if "api_key" in lowered or "secret" in lowered or "token" in lowered:
            errors.append("auto_approval_provenance_secret_ref_leak")
    for field in (
        "raw_secret_exposed",
        "raw_payload_exposed",
        "local_path_exposed",
        "broker_identifier_exposed",
    ):
        if provenance.get(field) is not False:
            errors.append(f"auto_approval_provenance_exposure_enabled:{field}")

    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "cannot bypass risk or kill switches",
        "cannot use Fund Manager trade-level approval",
        "cannot stage or submit proof orders",
        "cannot create proof trades",
        "cannot grant Phase 7 proof credit",
        "cannot enable live capital",
        "cannot permit manual trade-level overrides",
    ):
        if phrase not in boundary:
            errors.append("auto_approval_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("auto_approval_event_log_path_missing")
        if not str(artifact.get("event_log_correlation_id") or "").strip():
            errors.append("auto_approval_event_correlation_missing")
        if artifact.get("event_log_event_count") != 1:
            errors.append("auto_approval_event_log_count_mismatch")
    return sorted(set(errors))


def attach_phase7_test_mode_auto_approval_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(
        event_log_path or (_runtime_dir(settings) / PHASE7_TEST_MODE_AUTO_APPROVAL_EVENT_LOG)
    )
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PHASE7_TEST_MODE_AUTO_APPROVAL_EVENT_TYPE,
        PHASE7_TEST_MODE_AUTO_APPROVAL_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "stage_status": output.get("stage_status"),
            "test_mode_auto_approval_allowed": output.get(
                "test_mode_auto_approval_allowed"
            ),
            "approval_decision_record_count": output.get(
                "approval_decision_record_count"
            ),
            "qualified_setup_count": output.get("qualified_setup_count"),
            "auto_approved_setup_count": output.get("auto_approved_setup_count"),
            "rejected_setup_decision_count": output.get("rejected_setup_decision_count"),
            "fund_manager_trade_level_approval_count": output.get(
                "fund_manager_trade_level_approval_count"
            ),
            "sample_contaminated": output.get("sample_contaminated"),
            "phase7_proof_order_staging_allowed": output.get(
                "phase7_proof_order_staging_allowed"
            ),
            "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
            "live_capital_enabled": output.get("live_capital_enabled"),
            "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
            "recommended_next_stage": output.get("recommended_next_stage"),
            "boundary": output.get("boundary"),
        },
    )
    output["recorded"] = True
    output["event_log_written"] = True
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = 1
    output["event_log_correlation_id"] = entry.correlation_id
    output["event_log_created_at"] = entry.created_at
    output["validation_errors"] = validate_phase7_test_mode_auto_approval_router(output)
    if output["validation_errors"]:
        output["status"] = "error"
        output["stage_status"] = "test_mode_auto_approval_router_validation_error"
    return output, entry


def write_phase7_test_mode_auto_approval_router(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase7_test_mode_auto_approval_paths(
        settings
    )
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase7_test_mode_auto_approval_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase7_test_mode_auto_approval_router(
            output
        )
        if output["validation_errors"]:
            output["status"] = "error"
            output["stage_status"] = "test_mode_auto_approval_router_validation_error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase7_test_mode_auto_approval_router(output)
    if output["validation_errors"]:
        output["status"] = "error"
        output["stage_status"] = "test_mode_auto_approval_router_validation_error"
    output_path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    history_record = {
        "schema_version": PHASE7_TEST_MODE_AUTO_APPROVAL_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "stage_status": output.get("stage_status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "test_mode_auto_approval_allowed": output.get(
            "test_mode_auto_approval_allowed"
        ),
        "approval_decision_record_count": output.get("approval_decision_record_count"),
        "qualified_setup_count": output.get("qualified_setup_count"),
        "auto_approved_setup_count": output.get("auto_approved_setup_count"),
        "rejected_setup_decision_count": output.get("rejected_setup_decision_count"),
        "fund_manager_trade_level_approval_count": output.get(
            "fund_manager_trade_level_approval_count"
        ),
        "sample_contaminated": output.get("sample_contaminated"),
        "phase7_proof_order_staging_allowed": output.get(
            "phase7_proof_order_staging_allowed"
        ),
        "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
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
