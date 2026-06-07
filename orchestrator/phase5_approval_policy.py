"""Q5-2 approval policy router.

The approval policy router consumes the certified Phase 4 strategy posture and
approved-shadow strategy toggles, then emits replayable policy decisions for the
next Phase 5 stage. It does not create trade candidates, risk approvals, orders,
broker receipts, positions, or execution authority.
"""

from __future__ import annotations

import json
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.phase4_candidate_strategy_universe import (
    FIRST_TRADING_UNIVERSE,
    PREFERENCE_CONTEXT_AUTHORITY_FLAGS,
    build_candidate_strategy_universe,
    validate_candidate_strategy_universe,
)
from orchestrator.phase4_certification import (
    build_phase4_certification,
    validate_phase4_certification,
)
from orchestrator.phase4_strategy_toggles import (
    build_strategy_toggle_snapshot,
    validate_strategy_toggle_snapshot,
)
from orchestrator.phase5_artifacts import (
    PHASE5_ARTIFACT_SCHEMA_VERSION,
    PHASE5_AUTHORITY_FIELDS,
    phase5_authority_defaults,
    phase5_authority_ledger,
    phase5_provenance,
    phase5_source_posture,
    validate_phase5_artifact,
)
from orchestrator.phase5_readiness import (
    build_phase5_layer_b_readiness,
    validate_phase5_layer_b_readiness,
)
from world_monitor.source_registry import (
    EXPECTED_SOURCE_COUNT,
    canonical_decision_source_coverage,
)


PHASE5_APPROVAL_POLICY_SCHEMA_VERSION = 1
APPROVAL_POLICY_RUNTIME_ARTIFACT = "phase5_approval_policy_decisions.json"
APPROVAL_POLICY_HISTORY = "phase5_approval_policy_decisions_history.jsonl"
APPROVAL_POLICY_EVENT_LOG = "phase5_approval_policy_events.jsonl"
APPROVAL_POLICY_EVENT_TYPE = "phase5_approval_policy_decision_written"
APPROVAL_POLICY_COMPONENT = "phase5_approval_policy_router"
APPROVAL_POLICY_SOURCE_REFS: tuple[str, ...] = (
    "data/runtime/phase4_certification.json",
    "data/runtime/phase4_strategy_toggle_snapshot.json",
    "data/runtime/phase4_candidate_strategy_universe.json",
    "data/runtime/phase5_layer_b_readiness.json",
    "data/runtime/preference_source_promotion_decisions.json",
    "data/runtime/preference_provenance_source_quorum.json",
)

POLICY_DECISION_ORDER_BOUNDARY_FIELDS: tuple[str, ...] = (
    "trade_candidate_created",
    "risk_agent_handoff_allowed",
    "risk_sizing_review_created",
    "execution_policy_handoff_allowed",
    "execution_allowed",
    "execution_intent_created",
    "paper_order_allowed",
    "paper_order_staging_allowed",
    "staged_paper_order_allowed",
    "staged_order_created",
    "paper_order_submission_allowed",
    "paper_order_submitted",
    "broker_write_allowed",
    "broker_post_called",
    "broker_submit_receipt_created",
    "position_created",
    "live_capital_enabled",
)

POLICY_DECISION_COUNT_FIELDS: tuple[str, ...] = (
    "trade_candidate_created_count",
    "risk_agent_handoff_allowed_count",
    "risk_sizing_review_created_count",
    "execution_allowed_count",
    "execution_intent_created_count",
    "paper_order_allowed_count",
    "staged_order_created_count",
    "paper_order_submitted_count",
    "broker_write_allowed_count",
    "broker_submit_receipt_created_count",
    "position_created_count",
    "live_capital_enabled_count",
)

POLICY_BOUNDARY = (
    "Q5-2 policy decisions can mark approved-shadow strategy families as eligible "
    "for the later Q5-3 risk sizing contract only. They cannot create trade "
    "candidates, hand off to Risk Agent, create execution intents, stage or "
    "submit paper orders, write brokers, create receipts, create positions, or "
    "enable live capital."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _candidate_universe(settings: Settings | None = None) -> dict[str, Any]:
    runtime_path = _runtime_dir(settings) / "phase4_candidate_strategy_universe.json"
    return _read_json(runtime_path) or build_candidate_strategy_universe(settings)


def _phase4_certification(settings: Settings | None = None) -> dict[str, Any]:
    runtime_path = _runtime_dir(settings) / "phase4_certification.json"
    return _read_json(runtime_path) or build_phase4_certification(settings=settings)


def _phase5_readiness(settings: Settings | None = None) -> dict[str, Any]:
    runtime_path = _runtime_dir(settings) / "phase5_layer_b_readiness.json"
    return _read_json(runtime_path) or build_phase5_layer_b_readiness(settings=settings)


def _strategy_toggle_snapshot(settings: Settings | None = None) -> dict[str, Any]:
    runtime_path = _runtime_dir(settings) / "phase4_strategy_toggle_snapshot.json"
    return _read_json(runtime_path) or build_strategy_toggle_snapshot(settings=settings)


def _authority_ledger() -> dict[str, Any]:
    ledger = phase5_authority_ledger()
    ledger["stage"] = "Q5-2"
    ledger["boundary"] = (
        "Q5-2 records approval-policy decisions only. Every authority flag stays "
        "false; later Q5 stages must explicitly grant and verify paper authority."
    )
    return ledger


def _candidate_by_key(candidate_universe: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(candidate.get("candidate_key")): candidate
        for candidate in candidate_universe.get("candidates", [])
        if isinstance(candidate, dict) and candidate.get("candidate_key")
    }


def _toggle_by_key(toggle_snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(toggle.get("strategy_key")): toggle
        for toggle in toggle_snapshot.get("toggles", [])
        if isinstance(toggle, dict) and toggle.get("strategy_key")
    }


def _check(name: str, passed: bool, *, detail: Any = None) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def _all_false(payload: dict[str, Any], fields: tuple[str, ...]) -> bool:
    return all(payload.get(field) is False for field in fields)


def _source_weight_summary(candidate: dict[str, Any]) -> dict[str, Any]:
    required_sources = [str(source) for source in candidate.get("required_source_groups", [])]
    weights = candidate.get("source_weights", {})
    if not isinstance(weights, dict):
        weights = {}
    coverage = candidate.get("decision_source_coverage")
    if not isinstance(coverage, dict):
        coverage = canonical_decision_source_coverage(
            required_source_groups=required_sources,
            source_weights=weights,
            coverage_scope="phase5_approval_policy_source_summary",
        )
    missing_sources = sorted(set(required_sources) - set(weights))
    zero_weight_sources = sorted(
        source for source, weight in weights.items() if float(weight or 0.0) <= 0
    )
    total_weight = round(sum(float(weight or 0.0) for weight in weights.values()), 4)
    return {
        "required_source_group_count": len(required_sources),
        "source_weight_count": len(weights),
        "source_weight_sum": total_weight,
        "missing_source_weights": missing_sources,
        "zero_weight_sources": zero_weight_sources,
        "source_weights_normalized": 0.995 <= total_weight <= 1.005,
        "canonical_source_count": int(coverage.get("canonical_source_count", 0) or 0),
        "all_canonical_sources_considered": (
            coverage.get("all_canonical_sources_considered") is True
        ),
        "decision_source_usage_complete": (
            coverage.get("decision_source_usage_complete") is True
        ),
        "source_quorum_bypass_allowed": (
            coverage.get("source_quorum_bypass_allowed") is True
        ),
        "decision_source_coverage": coverage,
    }


def _model_weight_summary(candidate: dict[str, Any]) -> dict[str, Any]:
    weights = candidate.get("model_weights", {})
    if not isinstance(weights, dict):
        weights = {}
    total_weight = round(sum(float(weight or 0.0) for weight in weights.values()), 4)
    return {
        "model_weight_count": len(weights),
        "model_weight_sum": total_weight,
        "model_weights_normalized": 0.995 <= total_weight <= 1.005,
    }


def _market_confirmation_summary(candidate: dict[str, Any]) -> dict[str, Any]:
    policy = candidate.get("market_confirmation_requirements", {})
    if not isinstance(policy, dict):
        policy = {}
    return {
        "required": policy.get("required") is True,
        "non_yahoo_independent_confirmation_required": (
            policy.get("non_yahoo_independent_confirmation_required") is True
        ),
        "yahoo_finance_role": str(policy.get("yahoo_finance_role") or "missing"),
        "yahoo_only_confirmation_allowed": policy.get("yahoo_only_confirmation_allowed") is True,
        "stale_confirmation_allowed": policy.get("stale_confirmation_allowed") is True,
        "single_source_confirmation_allowed": policy.get("single_source_confirmation_allowed") is True,
        "pricing_gap_required": policy.get("pricing_gap_required") is True,
        "pricing_gap_policy_tier": str(policy.get("pricing_gap_policy_tier") or "missing"),
        "pricing_gap_satisfaction_rule": str(policy.get("pricing_gap_satisfaction_rule") or "missing"),
    }


def _preference_summary(candidate: dict[str, Any]) -> dict[str, Any]:
    policy = candidate.get("preference_context_policy", {})
    if not isinstance(policy, dict):
        policy = {}
    flags = policy.get("authority_flags", {})
    if not isinstance(flags, dict):
        flags = {}
    authority_enabled = sorted(
        field
        for field in PREFERENCE_CONTEXT_AUTHORITY_FLAGS
        if flags.get(field) is not False
    )
    return {
        "source_key": str(policy.get("source_key") or "missing"),
        "source_role": str(policy.get("source_role") or "missing"),
        "status": str(policy.get("status") or "missing"),
        "approved_domain_pack_count": int(policy.get("approved_domain_pack_count", 0) or 0),
        "source_quorum_credit_allowed": policy.get("source_quorum_credit_allowed") is True,
        "preference_only_confirmation_allowed": (
            policy.get("preference_only_confirmation_allowed") is True
        ),
        "trade_candidate_creation_allowed": (
            policy.get("trade_candidate_creation_allowed") is True
        ),
        "risk_handoff_allowed": policy.get("risk_handoff_allowed") is True,
        "execution_allowed": policy.get("execution_allowed") is True,
        "paper_order_allowed": policy.get("paper_order_allowed") is True,
        "broker_write_allowed": policy.get("broker_write_allowed") is True,
        "live_capital_enabled": policy.get("live_capital_enabled") is True,
        "quota_degraded": policy.get("quota_degraded") is True,
        "context_stale": policy.get("context_stale") is True,
        "authority_enabled_fields": authority_enabled,
    }


def _global_context_errors(
    *,
    certification: dict[str, Any],
    readiness: dict[str, Any],
    toggle_snapshot: dict[str, Any],
    candidate_universe: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    certification_errors = validate_phase4_certification(certification)
    readiness_errors = validate_phase5_layer_b_readiness(readiness)
    toggle_errors = validate_strategy_toggle_snapshot(toggle_snapshot)
    candidate_errors = validate_candidate_strategy_universe(candidate_universe)
    if certification_errors:
        errors.append("phase4_certification_validation_failed")
    if readiness_errors:
        errors.append("phase5_readiness_validation_failed")
    if toggle_errors:
        errors.append("strategy_toggle_snapshot_validation_failed")
    if candidate_errors:
        errors.append("candidate_strategy_universe_validation_failed")
    if certification.get("phase4_certified") is not True:
        errors.append("phase4_not_certified")
    if certification.get("phase5_handoff_allowed") is not True:
        errors.append("phase5_handoff_not_allowed")
    if certification.get("approval_state") != "approved":
        errors.append("approval_state_not_approved")
    if readiness.get("phase5_layer_b_implementation_allowed") is not True:
        errors.append("phase5_layer_b_implementation_not_allowed")
    if readiness.get("phase5_orchestration_start_allowed") is not False:
        errors.append("phase5_orchestration_start_allowed")
    preference_gate = certification.get("preference_mcp_certification_gate", {})
    if not isinstance(preference_gate, dict) or preference_gate.get("status") != "validated":
        errors.append("preference_certification_gate_not_validated")
    else:
        if int(preference_gate.get("certification_blocker_count", 0) or 0) != 0:
            errors.append("preference_certification_gate_blocked")
        if preference_gate.get("source_promotion_status") != "validated":
            errors.append("preference_source_promotion_not_validated")
        if int(preference_gate.get("source_promotion_promoted_decision_count", 0) or 0) != 0:
            errors.append("preference_source_promotion_promoted")
        if int(preference_gate.get("source_promotion_canonical_source_count_after", 0) or 0) != EXPECTED_SOURCE_COUNT:
            errors.append("preference_source_promotion_source_count_mismatch")
        if preference_gate.get("preference_mcp_source_36") is not False:
            errors.append("preference_mcp_source_36")
        if preference_gate.get("paid_tool_calls_allowed") is not False:
            errors.append("preference_paid_tool_calls_allowed")
        if preference_gate.get("source_quorum_credit_allowed") is not False:
            errors.append("preference_source_quorum_credit_allowed")
    market_policy = certification.get("market_confirmation_policy", {})
    if market_policy.get("yahoo_finance_role") != "supplemental_market_confirmation_only":
        errors.append("yahoo_finance_policy_not_supplemental")
    if market_policy.get("yahoo_only_confirmation_allowed") is not False:
        errors.append("yahoo_only_confirmation_allowed")
    return sorted(dict.fromkeys(errors))


def _strategy_decision(
    strategy_key: str,
    *,
    toggle: dict[str, Any] | None,
    candidate: dict[str, Any] | None,
    global_errors: list[str],
    certification: dict[str, Any],
    readiness: dict[str, Any],
) -> dict[str, Any]:
    toggle = toggle or {}
    candidate = candidate or {}
    source_summary = _source_weight_summary(candidate)
    model_summary = _model_weight_summary(candidate)
    market_summary = _market_confirmation_summary(candidate)
    preference_summary = _preference_summary(candidate)
    instrument_universe = [
        str(instrument) for instrument in candidate.get("instrument_universe", [])
    ]
    catalyst_classes = [
        str(catalyst) for catalyst in candidate.get("catalyst_classes", [])
    ]
    toggle_authority_fields = (
        "risk_agent_handoff_allowed",
        "execution_policy_handoff_allowed",
        "trade_candidate_created",
        "execution_allowed",
        "paper_order_allowed",
        "staged_paper_order_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
    )
    candidate_authority_fields = (
        "risk_agent_handoff_allowed",
        "execution_policy_handoff_allowed",
        "trade_candidate_created",
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
    )
    checks = [
        _check("global_context_validated", not global_errors, detail=global_errors),
        _check("phase4_certified", certification.get("phase4_certified") is True),
        _check("phase5_handoff_allowed", certification.get("phase5_handoff_allowed") is True),
        _check(
            "phase5_implementation_allowed",
            readiness.get("phase5_layer_b_implementation_allowed") is True,
        ),
        _check(
            "phase5_orchestration_not_started",
            readiness.get("phase5_orchestration_start_allowed") is False,
        ),
        _check("approval_state_approved", certification.get("approval_state") == "approved"),
        _check("strategy_toggle_present", bool(toggle)),
        _check("strategy_toggle_approved_shadow", toggle.get("toggle_state") == "approved_shadow"),
        _check("strategy_toggle_transition_logged", toggle.get("transition_event_logged") is True),
        _check("strategy_toggle_has_no_authority", _all_false(toggle, toggle_authority_fields)),
        _check("candidate_family_present", bool(candidate)),
        _check("active_instrument_present", bool(instrument_universe)),
        _check(
            "active_instrument_in_first_universe",
            bool(instrument_universe)
            and set(instrument_universe).issubset(set(FIRST_TRADING_UNIVERSE)),
            detail=instrument_universe,
        ),
        _check("allowed_catalyst_class_present", bool(catalyst_classes)),
        _check("source_weights_present", source_summary["source_weight_count"] > 0),
        _check("source_weights_normalized", source_summary["source_weights_normalized"]),
        _check("source_weights_nonzero", not source_summary["zero_weight_sources"]),
        _check(
            "canonical_decision_source_coverage_complete",
            source_summary["canonical_source_count"] == EXPECTED_SOURCE_COUNT
            and source_summary["all_canonical_sources_considered"] is True
            and source_summary["decision_source_usage_complete"] is True
            and source_summary["source_quorum_bypass_allowed"] is False,
        ),
        _check("model_weights_present", model_summary["model_weight_count"] > 0),
        _check("model_weights_normalized", model_summary["model_weights_normalized"]),
        _check("candidate_has_no_authority", _all_false(candidate, candidate_authority_fields)),
        _check("market_confirmation_required", market_summary["required"]),
        _check(
            "non_yahoo_market_confirmation_required",
            market_summary["non_yahoo_independent_confirmation_required"],
        ),
        _check(
            "yahoo_supplemental_only",
            market_summary["yahoo_finance_role"] == "supplemental_market_confirmation_only",
        ),
        _check("yahoo_only_confirmation_blocked", not market_summary["yahoo_only_confirmation_allowed"]),
        _check("stale_confirmation_blocked", not market_summary["stale_confirmation_allowed"]),
        _check(
            "single_source_confirmation_blocked",
            not market_summary["single_source_confirmation_allowed"],
        ),
        _check("preference_source_role_supplemental", preference_summary["source_role"] == "supplemental_multi_source_data_plane"),
        _check("preference_domain_pack_mapped", preference_summary["approved_domain_pack_count"] > 0),
        _check("preference_not_source_quorum", not preference_summary["source_quorum_credit_allowed"]),
        _check(
            "preference_not_sole_confirmation",
            not preference_summary["preference_only_confirmation_allowed"],
        ),
        _check(
            "preference_has_no_authority",
            not any(
                preference_summary[field]
                for field in (
                    "trade_candidate_creation_allowed",
                    "risk_handoff_allowed",
                    "execution_allowed",
                    "paper_order_allowed",
                    "broker_write_allowed",
                    "live_capital_enabled",
                )
            )
            and not preference_summary["authority_enabled_fields"],
        ),
    ]
    blockers = [
        check["name"]
        for check in checks
        if not check["passed"] and check["name"] != "global_context_validated"
    ]
    blockers.extend(global_errors)
    blockers = sorted(dict.fromkeys(blockers))
    hold_reasons: list[str] = []
    cautions: list[str] = []
    if preference_summary["quota_degraded"]:
        cautions.append("preference_quota_degraded_context_only")
    if preference_summary["context_stale"]:
        cautions.append("preference_context_stale_context_only")

    if blockers:
        status = "blocked"
        policy_decision = "blocked_policy_gate_failed"
    elif hold_reasons:
        status = "hold"
        policy_decision = "hold_requires_context_repair"
    else:
        status = "eligible"
        policy_decision = "eligible_for_q5_3_risk_sizing_contract"

    decision = {
        "schema_version": PHASE5_ARTIFACT_SCHEMA_VERSION,
        "approval_policy_schema_version": PHASE5_APPROVAL_POLICY_SCHEMA_VERSION,
        "artifact_type": "approval_policy_decision",
        "artifact_id": f"phase5:q5-2:approval-policy:{strategy_key}",
        "phase": "Q5",
        "stage": "Q5-2",
        "status": status,
        "generated_at": _now(),
        "public_safe": True,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "authority_ledger": _authority_ledger(),
        "source_posture": phase5_source_posture(),
        "provenance": phase5_provenance(APPROVAL_POLICY_SOURCE_REFS),
        "boundary": POLICY_BOUNDARY,
        **phase5_authority_defaults(),
        "strategy_family_key": strategy_key,
        "policy_decision": policy_decision,
        "approved_strategy_toggle_state": str(toggle.get("toggle_state") or "missing"),
        "source_candidate_key": str(toggle.get("source_candidate_key") or strategy_key),
        "candidate_status": str(candidate.get("status") or "missing"),
        "operating_mode": "phase5_layer_b_contract_build",
        "phase5_readiness_status": str(readiness.get("status") or "missing"),
        "phase5_layer_b_implementation_allowed": (
            readiness.get("phase5_layer_b_implementation_allowed") is True
        ),
        "phase5_orchestration_start_allowed": False,
        "phase4_certified": certification.get("phase4_certified") is True,
        "phase5_handoff_allowed": certification.get("phase5_handoff_allowed") is True,
        "approval_state": str(certification.get("approval_state") or "missing"),
        "instrument_universe": instrument_universe,
        "primary_instrument": instrument_universe[0] if instrument_universe else None,
        "catalyst_classes": catalyst_classes,
        "catalyst_class_count": len(catalyst_classes),
        "required_source_group_count": source_summary["required_source_group_count"],
        "source_weight_count": source_summary["source_weight_count"],
        "source_weight_sum": source_summary["source_weight_sum"],
        "zero_weight_sources": source_summary["zero_weight_sources"],
        "canonical_source_count": source_summary["canonical_source_count"],
        "all_canonical_sources_considered": source_summary[
            "all_canonical_sources_considered"
        ],
        "decision_source_usage_complete": source_summary[
            "decision_source_usage_complete"
        ],
        "source_quorum_bypass_allowed": source_summary[
            "source_quorum_bypass_allowed"
        ],
        "decision_source_coverage": source_summary["decision_source_coverage"],
        "model_weight_count": model_summary["model_weight_count"],
        "model_weight_sum": model_summary["model_weight_sum"],
        "market_confirmation_policy": market_summary,
        "yahoo_finance_role": market_summary["yahoo_finance_role"],
        "yahoo_only_confirmation_allowed": market_summary["yahoo_only_confirmation_allowed"],
        "preference_policy": preference_summary,
        "preference_mcp_role": "supplemental_multi_source_data_plane",
        "preference_mcp_source_36": False,
        "preference_paid_tools_allowed": False,
        "preference_source_quorum_credit_allowed": preference_summary["source_quorum_credit_allowed"],
        "preference_only_confirmation_allowed": preference_summary["preference_only_confirmation_allowed"],
        "policy_checks": checks,
        "policy_blockers": blockers,
        "policy_blocker_count": len(blockers),
        "hold_reasons": hold_reasons,
        "hold_reason_count": len(hold_reasons),
        "cautions": cautions,
        "caution_count": len(cautions),
        "next_required_stage": "Q5-3" if status == "eligible" else "Q5-2_repair",
        "next_required_action": (
            "Evaluate under Q5-3 risk sizing contract without creating an order."
            if status == "eligible"
            else "Repair blocked or hold policy inputs before any Risk Agent review."
        ),
        "router_contract_active": True,
        "risk_agent_handoff_allowed": False,
        "risk_sizing_review_created": False,
        "execution_policy_handoff_allowed": False,
        "execution_allowed": False,
        "execution_intent_created": False,
        "paper_order_allowed": False,
        "paper_order_staging_allowed": False,
        "staged_paper_order_allowed": False,
        "staged_order_created": False,
        "paper_order_submission_allowed": False,
        "paper_order_submitted": False,
        "broker_write_allowed": False,
        "broker_post_called": False,
        "broker_submit_receipt_created": False,
        "position_created": False,
        "trade_candidate_created": False,
        "live_capital_enabled": False,
    }
    decision["validation_errors"] = validate_phase5_approval_policy_decision(decision)
    return decision


def build_phase5_approval_policy_decisions(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    certification = _phase4_certification(settings)
    readiness = _phase5_readiness(settings)
    toggle_snapshot = _strategy_toggle_snapshot(settings)
    candidate_universe = _candidate_universe(settings)
    global_errors = _global_context_errors(
        certification=certification,
        readiness=readiness,
        toggle_snapshot=toggle_snapshot,
        candidate_universe=candidate_universe,
    )
    candidates = _candidate_by_key(candidate_universe)
    toggles = _toggle_by_key(toggle_snapshot)
    strategy_keys = sorted(set(toggles) | set(candidates))
    decisions = [
        _strategy_decision(
            strategy_key,
            toggle=toggles.get(strategy_key),
            candidate=candidates.get(strategy_key),
            global_errors=global_errors,
            certification=certification,
            readiness=readiness,
        )
        for strategy_key in strategy_keys
    ]
    status_counts = Counter(str(decision.get("status") or "unknown") for decision in decisions)
    artifact = {
        "schema_version": PHASE5_APPROVAL_POLICY_SCHEMA_VERSION,
        "artifact_type": "phase5_approval_policy_decision_bundle",
        "artifact_id": "phase5:q5-2:approval-policy-decisions",
        "phase": "Q5",
        "stage": "Q5-2",
        "status": "ok",
        "generated_at": _now(),
        "public_safe": True,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_event_count": 0,
        "runtime_artifact_path": None,
        "history_log_path": None,
        "authority_ledger": _authority_ledger(),
        "source_posture": phase5_source_posture(),
        "provenance": phase5_provenance(APPROVAL_POLICY_SOURCE_REFS),
        "boundary": POLICY_BOUNDARY,
        **phase5_authority_defaults(),
        "phase4_certified": certification.get("phase4_certified") is True,
        "phase5_handoff_allowed": certification.get("phase5_handoff_allowed") is True,
        "phase5_layer_b_implementation_allowed": (
            readiness.get("phase5_layer_b_implementation_allowed") is True
        ),
        "phase5_orchestration_start_allowed": False,
        "approval_state": str(certification.get("approval_state") or "missing"),
        "strategy_toggle_count": int(toggle_snapshot.get("toggle_count", 0) or 0),
        "approved_shadow_toggle_count": int(
            toggle_snapshot.get("approved_shadow_toggle_count", 0) or 0
        ),
        "candidate_strategy_family_count": int(
            candidate_universe.get("strategy_family_candidate_count", 0) or 0
        ),
        "global_policy_errors": global_errors,
        "global_policy_error_count": len(global_errors),
        "decision_count": len(decisions),
        "eligible_count": status_counts.get("eligible", 0),
        "hold_count": status_counts.get("hold", 0),
        "blocked_count": status_counts.get("blocked", 0),
        "decision_status_counts": dict(sorted(status_counts.items())),
        "canonical_source_count": EXPECTED_SOURCE_COUNT,
        "yahoo_finance_role": "supplemental_market_confirmation_only",
        "preference_mcp_role": "supplemental_multi_source_data_plane",
        "preference_mcp_source_36": False,
        "preference_paid_tools_allowed": False,
        "preference_source_quorum_credit_allowed": False,
        "preference_only_confirmation_allowed": False,
        "decisions": decisions,
    }
    for field in POLICY_DECISION_COUNT_FIELDS:
        artifact[field] = 0
    artifact["status"] = "ok" if not validate_phase5_approval_policy_bundle(artifact) else "error"
    artifact["validation_errors"] = validate_phase5_approval_policy_bundle(artifact)
    return artifact


def _decision_status_consistency_errors(decision: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    status = str(decision.get("status") or "missing")
    policy_decision = str(decision.get("policy_decision") or "")
    blockers = decision.get("policy_blockers", [])
    hold_reasons = decision.get("hold_reasons", [])
    if not isinstance(blockers, list):
        errors.append("policy_blockers_not_list")
        blockers = []
    if not isinstance(hold_reasons, list):
        errors.append("hold_reasons_not_list")
        hold_reasons = []
    if decision.get("policy_blocker_count") != len(blockers):
        errors.append("policy_blocker_count_mismatch")
    if decision.get("hold_reason_count") != len(hold_reasons):
        errors.append("hold_reason_count_mismatch")
    if status == "eligible":
        if not policy_decision.startswith("eligible_"):
            errors.append("eligible_policy_decision_prefix_invalid")
        if blockers:
            errors.append("eligible_decision_has_blockers")
        if hold_reasons:
            errors.append("eligible_decision_has_hold_reasons")
        if decision.get("approved_strategy_toggle_state") != "approved_shadow":
            errors.append("eligible_without_approved_shadow_toggle")
        if decision.get("next_required_stage") != "Q5-3":
            errors.append("eligible_next_stage_not_q5_3")
    elif status == "hold":
        if not policy_decision.startswith("hold_"):
            errors.append("hold_policy_decision_prefix_invalid")
        if not hold_reasons:
            errors.append("hold_decision_without_hold_reasons")
    elif status == "blocked":
        if not policy_decision.startswith("blocked_"):
            errors.append("blocked_policy_decision_prefix_invalid")
        if not blockers:
            errors.append("blocked_decision_without_blockers")
    return errors


def validate_phase5_approval_policy_decision(decision: dict[str, Any]) -> list[str]:
    errors = list(validate_phase5_artifact(decision, expected_stage="Q5-2"))
    if decision.get("artifact_type") != "approval_policy_decision":
        errors.append("artifact_type_not_approval_policy_decision")
    if decision.get("approval_policy_schema_version") != PHASE5_APPROVAL_POLICY_SCHEMA_VERSION:
        errors.append("approval_policy_schema_version_mismatch")
    if decision.get("router_contract_active") is not True:
        errors.append("router_contract_not_active")
    if decision.get("event_log_required") is not True:
        errors.append("event_log_required_not_true")
    if decision.get("event_log_written") is True:
        if not str(decision.get("event_log_correlation_id") or "").strip():
            errors.append("event_log_correlation_id_missing")
        if not str(decision.get("event_log_path") or "").strip():
            errors.append("event_log_path_missing")
    if decision.get("phase4_certified") is not True and decision.get("status") != "blocked":
        errors.append("nonblocked_without_phase4_certification")
    if decision.get("phase5_handoff_allowed") is not True and decision.get("status") != "blocked":
        errors.append("nonblocked_without_phase5_handoff")
    if decision.get("phase5_layer_b_implementation_allowed") is not True and decision.get("status") != "blocked":
        errors.append("nonblocked_without_phase5_implementation_gate")
    if decision.get("phase5_orchestration_start_allowed") is not False:
        errors.append("phase5_orchestration_start_allowed")
    if decision.get("approval_state") != "approved" and decision.get("status") != "blocked":
        errors.append("nonblocked_without_approval")
    if decision.get("yahoo_finance_role") != "supplemental_market_confirmation_only":
        errors.append("yahoo_finance_role_not_supplemental")
    if decision.get("yahoo_only_confirmation_allowed") is not False:
        errors.append("yahoo_only_confirmation_allowed")
    if decision.get("preference_mcp_role") != "supplemental_multi_source_data_plane":
        errors.append("preference_mcp_role_invalid")
    if decision.get("preference_mcp_source_36") is not False:
        errors.append("preference_mcp_source_36")
    if decision.get("preference_paid_tools_allowed") is not False:
        errors.append("preference_paid_tools_allowed")
    if decision.get("preference_source_quorum_credit_allowed") is not False:
        errors.append("preference_source_quorum_credit_allowed")
    if decision.get("preference_only_confirmation_allowed") is not False:
        errors.append("preference_only_confirmation_allowed")
    coverage = decision.get("decision_source_coverage")
    if decision.get("canonical_source_count") != EXPECTED_SOURCE_COUNT:
        errors.append("canonical_source_count_mismatch")
    if decision.get("all_canonical_sources_considered") is not True:
        errors.append("canonical_sources_not_considered")
    if decision.get("source_quorum_bypass_allowed") is not False:
        errors.append("source_quorum_bypass_allowed")
    if not isinstance(coverage, dict):
        errors.append("decision_source_coverage_missing")
    else:
        if coverage.get("canonical_source_count") != EXPECTED_SOURCE_COUNT:
            errors.append("decision_source_coverage_count_mismatch")
        if coverage.get("source_quorum_bypass_allowed") is not False:
            errors.append("decision_source_coverage_quorum_bypass_allowed")
        if (
            decision.get("status") == "eligible"
            and coverage.get("decision_source_usage_complete") is not True
        ):
            errors.append("eligible_without_decision_source_coverage")
    for field in POLICY_DECISION_ORDER_BOUNDARY_FIELDS:
        if decision.get(field) is not False:
            errors.append(f"policy_decision_order_boundary_enabled:{field}")
    if decision.get("authority_ledger", {}).get("explicit_authority_grant_count") != 0:
        errors.append("explicit_authority_grants_present")
    for field in PHASE5_AUTHORITY_FIELDS:
        if decision.get(field) is not False:
            errors.append(f"phase5_authority_enabled:{field}")
    if not isinstance(decision.get("policy_checks"), list) or not decision.get("policy_checks"):
        errors.append("policy_checks_missing")
    errors.extend(_decision_status_consistency_errors(decision))
    return sorted(set(errors))


def validate_phase5_approval_policy_bundle(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schema_version",
        "artifact_type",
        "artifact_id",
        "phase",
        "stage",
        "status",
        "generated_at",
        "public_safe",
        "event_log_required",
        "event_log_written",
        "authority_ledger",
        "source_posture",
        "provenance",
        "decision_count",
        "eligible_count",
        "hold_count",
        "blocked_count",
        "decisions",
        "boundary",
    }
    missing = sorted(required_fields - set(bundle))
    if missing:
        errors.append("bundle_missing_fields:" + ",".join(missing))
    if bundle.get("schema_version") != PHASE5_APPROVAL_POLICY_SCHEMA_VERSION:
        errors.append("bundle_schema_version_mismatch")
    if bundle.get("artifact_type") != "phase5_approval_policy_decision_bundle":
        errors.append("bundle_artifact_type_mismatch")
    if bundle.get("phase") != "Q5" or bundle.get("stage") != "Q5-2":
        errors.append("bundle_phase_stage_mismatch")
    if bundle.get("public_safe") is not True:
        errors.append("bundle_public_safe_not_true")
    decisions = bundle.get("decisions", [])
    if not isinstance(decisions, list):
        errors.append("decisions_not_list")
        decisions = []
    if bundle.get("decision_count") != len(decisions):
        errors.append("decision_count_mismatch")
    status_counts = Counter(str(decision.get("status") or "unknown") for decision in decisions)
    if bundle.get("eligible_count") != status_counts.get("eligible", 0):
        errors.append("eligible_count_mismatch")
    if bundle.get("hold_count") != status_counts.get("hold", 0):
        errors.append("hold_count_mismatch")
    if bundle.get("blocked_count") != status_counts.get("blocked", 0):
        errors.append("blocked_count_mismatch")
    if bundle.get("event_log_written") is True:
        if not str(bundle.get("event_log_path") or "").strip():
            errors.append("bundle_event_log_path_missing")
        if bundle.get("event_log_event_count") != len(decisions):
            errors.append("bundle_event_log_count_mismatch")
    if bundle.get("phase5_orchestration_start_allowed") is not False:
        errors.append("bundle_phase5_orchestration_start_allowed")
    for field in PHASE5_AUTHORITY_FIELDS:
        if bundle.get(field) is not False:
            errors.append(f"bundle_phase5_authority_enabled:{field}")
    for field in POLICY_DECISION_COUNT_FIELDS:
        if bundle.get(field) != 0:
            errors.append(f"bundle_boundary_count_not_zero:{field}")
    if bundle.get("yahoo_finance_role") != "supplemental_market_confirmation_only":
        errors.append("bundle_yahoo_finance_role_not_supplemental")
    if bundle.get("preference_mcp_source_36") is not False:
        errors.append("bundle_preference_mcp_source_36")
    if bundle.get("preference_paid_tools_allowed") is not False:
        errors.append("bundle_preference_paid_tools_allowed")
    if bundle.get("preference_source_quorum_credit_allowed") is not False:
        errors.append("bundle_preference_source_quorum_credit_allowed")
    if bundle.get("preference_only_confirmation_allowed") is not False:
        errors.append("bundle_preference_only_confirmation_allowed")
    for decision in decisions:
        errors.extend(validate_phase5_approval_policy_decision(decision))
    return sorted(set(errors))


def attach_phase5_approval_policy_event_log(
    bundle: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], tuple[EventLogEntry, ...]]:
    output = deepcopy(bundle)
    log_path = Path(event_log_path or (_runtime_dir(settings) / APPROVAL_POLICY_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entries: list[EventLogEntry] = []
    for decision in output.get("decisions", []):
        if not isinstance(decision, dict):
            continue
        entry = log.write(
            APPROVAL_POLICY_EVENT_TYPE,
            APPROVAL_POLICY_COMPONENT,
            {
                "artifact_id": decision.get("artifact_id"),
                "strategy_family_key": decision.get("strategy_family_key"),
                "status": decision.get("status"),
                "policy_decision": decision.get("policy_decision"),
                "approved_strategy_toggle_state": decision.get(
                    "approved_strategy_toggle_state"
                ),
                "policy_blocker_count": decision.get("policy_blocker_count"),
                "hold_reason_count": decision.get("hold_reason_count"),
                "caution_count": decision.get("caution_count"),
                "risk_agent_handoff_allowed": decision.get("risk_agent_handoff_allowed"),
                "execution_allowed": decision.get("execution_allowed"),
                "paper_order_allowed": decision.get("paper_order_allowed"),
                "broker_write_allowed": decision.get("broker_write_allowed"),
                "live_capital_enabled": decision.get("live_capital_enabled"),
                "boundary": decision.get("boundary"),
            },
        )
        decision["event_log_written"] = True
        decision["event_log_path"] = str(log.path)
        decision["event_log_correlation_id"] = entry.correlation_id
        decision["event_log_created_at"] = entry.created_at
        decision["validation_errors"] = validate_phase5_approval_policy_decision(decision)
        entries.append(entry)
    output["event_log_written"] = bool(entries)
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = len(entries)
    output["validation_errors"] = validate_phase5_approval_policy_bundle(output)
    output["status"] = "ok" if not output["validation_errors"] else "error"
    return output, tuple(entries)


def phase5_approval_policy_paths(settings: Settings | None = None) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / APPROVAL_POLICY_RUNTIME_ARTIFACT,
        runtime / APPROVAL_POLICY_HISTORY,
        runtime / APPROVAL_POLICY_EVENT_LOG,
    )


def write_phase5_approval_policy_decisions(
    bundle: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(bundle)
    output_path, history_path, default_event_log_path = phase5_approval_policy_paths(settings)
    event_path = Path(event_log_path or default_event_log_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase5_approval_policy_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase5_approval_policy_bundle(output)
        output["status"] = "ok" if not output["validation_errors"] else "error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase5_approval_policy_bundle(output)
    output["status"] = "ok" if not output["validation_errors"] else "error"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE5_APPROVAL_POLICY_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "decision_count": output.get("decision_count"),
        "eligible_count": output.get("eligible_count"),
        "hold_count": output.get("hold_count"),
        "blocked_count": output.get("blocked_count"),
        "event_log_written": output.get("event_log_written"),
        "event_log_event_count": output.get("event_log_event_count"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output
