"""QSASE-10 Strategy Router.

The Strategy Router chooses the next allowed strategy state after Strategy
Foundry, Akber Filter, and Shadow Strategy Simulator review. It is not an
execution engine and cannot create candidates, approvals, orders, broker writes,
live-capital authority, or paper proof ledger credit.
"""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qsase_governance_safety_contract import (
    PHASE_STATUS_ARTIFACT,
    universal_authority_flags,
)

SCHEMA_VERSION = "qsase_strategy_router.v1"
PHASE_ID = "qsase_10_strategy_router"
PHASE_NAME = "QSASE-10: Strategy Router"
IMPLEMENTATION_LOG = "docs/qsase-implementation-log.md"

PRIMARY_ARTIFACT = "qsase_strategy_router_decisions.json"
DECISIONS_ARTIFACT = "qsase_strategy_router_decisions.jsonl"
HISTORY_ARTIFACT = "qsase_strategy_router_decisions_history.jsonl"
EVENTS_ARTIFACT = "qsase_strategy_router_decisions_events.jsonl"
SCOREBOARD_ARTIFACT = "qsase_strategy_router_scoreboard.json"
WHY_NOT_ARTIFACT = "qsase_why_not_trading_now.json"
HARD_VETOES_ARTIFACT = "qsase_strategy_router_hard_vetoes.jsonl"
SOFT_BLOCKERS_ARTIFACT = "qsase_strategy_router_soft_blockers.jsonl"
DASHBOARD_SUMMARY_ARTIFACT = "qsase_strategy_router_dashboard_summary.json"

STRATEGY_FOUNDRY_READY_STATUSES = {
    "qsase_strategy_foundry_ready",
    "qsase_strategy_foundry_ready_with_probationary_hypotheses",
}

SELF_MODEL_READY_STATUSES = {
    "qsase_self_model_ready",
    "qsase_self_model_ready_with_gaps",
    "ready",
}

AKBER_READY_STATUSES = {
    "qsase_akber_filter_integration_ready",
    "qsase_akber_filter_integration_ready_with_holds",
}

SHADOW_SIMULATOR_READY_STATUSES = {
    "qsase_shadow_strategy_simulator_ready",
    "qsase_shadow_strategy_simulator_ready_with_holds",
}

SELF_MODEL_ARTIFACT = "qsase_self_model.json"
STRATEGY_FOUNDRY_ARTIFACT = "qsase_strategy_hypotheses.json"
STRATEGY_HYPOTHESES_ARTIFACT = "qsase_strategy_hypotheses.jsonl"
REJECTED_STRATEGY_HYPOTHESES_ARTIFACT = "qsase_rejected_strategy_hypotheses.jsonl"
AKBER_FILTER_ARTIFACT = "qsase_akber_filter_integration.json"
AKBER_FILTER_RESULTS_ARTIFACT = "qsase_akber_filter_results.jsonl"
SHADOW_SIMULATOR_ARTIFACT = "qsase_shadow_strategy_simulator.json"
SHADOW_RESULTS_ARTIFACT = "qsase_shadow_strategy_results.jsonl"
LINEAR_LAB_ARTIFACT = "qsase_linear_pattern_lab.json"
NONLINEAR_LAB_ARTIFACT = "qsase_nonlinear_quantum_pattern_lab.json"
QUANTUM_REVIEWS_ARTIFACT = "qsase_quantum_pattern_reviews.jsonl"
HISTORICAL_MEMORY_ARTIFACT = "qsase_historical_source_price_memory.json"
PAPEROPS_SUMMARY_ARTIFACT = "paperops_autonomous_pass_summary.json"

ROUTER_STATES = {
    "paper_review_candidate",
    "shadow_only",
    "watchlist_only",
    "reject",
    "hold_missing_evidence",
    "hold_route_unavailable",
    "repair_requested",
    "blocked_safety_boundary",
}

ROUTER_AUTHORITY_FLAGS = {
    "trade_candidate_creation_allowed": False,
    "trade_candidate_created": False,
    "qualified_setup_created": False,
    "risk_handoff_allowed": False,
    "risk_approval_allowed": False,
    "risk_approval_created": False,
    "execution_allowed": False,
    "execution_approval_allowed": False,
    "execution_approval_created": False,
    "execution_intent_created": False,
    "paper_order_allowed": False,
    "paper_order_created": False,
    "broker_write_allowed": False,
    "live_broker_endpoint_allowed": False,
    "paperops_direct_call_allowed": False,
    "paperops_handoff_created": False,
    "paperops_bypass_allowed": False,
    "qctrl_bypass_allowed": False,
    "idempotency_override_allowed": False,
    "duplicate_exposure_override_allowed": False,
    "daily_drawdown_override_allowed": False,
    "risk_budget_override_allowed": False,
    "strategy_mutation_allowed": False,
    "strategy_mutation_created": False,
    "policy_mutation_allowed": False,
    "policy_mutation_created": False,
    "model_weight_update_allowed": False,
    "model_weight_update_created": False,
    "source_trust_update_allowed": False,
    "source_trust_update_created": False,
    "proof_credit_allowed": False,
    "paper_proof_ledger_write_allowed": False,
    "paper_proof_ledger_credit_allowed": False,
    "paper_growth_trial_calendar_advance_allowed": False,
    "simulated_elapsed_time_allowed": False,
    "telegram_command_path_enabled": False,
    "telegram_trade_command_enabled": False,
    "live_capital_enabled": False,
}

REQUIRED_DECISION_FIELDS = (
    "router_decision_id",
    "router_input_type",
    "strategy_family",
    "scores",
    "gates",
    "hard_vetoes",
    "soft_blockers",
    "decision",
    "lineage",
    "paper_review_candidate_handoff",
    "telegram_summary",
    "authority",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _runtime_dir(settings: Settings | None = None) -> Path:
    active_settings = settings or Settings.from_env()
    path = Path(active_settings.runtime_dir)
    if not path.is_absolute():
        path = _repo_root() / path
    return path


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _json_dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _jsonl_line(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True) + "\n"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    if limit is not None:
        lines = lines[-limit:]
    records: list[dict[str, Any]] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_dump(payload), encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(_jsonl_line(record) for record in records), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(_jsonl_line(payload))


def _hash_id(parts: list[Any], prefix: str) -> str:
    raw = "|".join(str(part) for part in parts)
    return f"{prefix}:{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]}"


def _float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _authority_block() -> dict[str, Any]:
    return {
        "router_decision_only": True,
        "paper_review_candidate_is_not_order": True,
        "no_broker_or_execution_authority": True,
        **ROUTER_AUTHORITY_FLAGS,
    }


def _load_context(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "runtime_dir": runtime,
        "self_model": _read_json(runtime / SELF_MODEL_ARTIFACT),
        "strategy_foundry": _read_json(runtime / STRATEGY_FOUNDRY_ARTIFACT),
        "strategy_hypotheses": _read_jsonl(runtime / STRATEGY_HYPOTHESES_ARTIFACT),
        "rejected_strategy_hypotheses": _read_jsonl(runtime / REJECTED_STRATEGY_HYPOTHESES_ARTIFACT),
        "akber_filter": _read_json(runtime / AKBER_FILTER_ARTIFACT),
        "akber_results": _read_jsonl(runtime / AKBER_FILTER_RESULTS_ARTIFACT),
        "shadow_simulator": _read_json(runtime / SHADOW_SIMULATOR_ARTIFACT),
        "shadow_results": _read_jsonl(runtime / SHADOW_RESULTS_ARTIFACT),
        "linear_lab": _read_json(runtime / LINEAR_LAB_ARTIFACT),
        "nonlinear_lab": _read_json(runtime / NONLINEAR_LAB_ARTIFACT),
        "quantum_reviews": _read_jsonl(runtime / QUANTUM_REVIEWS_ARTIFACT),
        "historical_memory": _read_json(runtime / HISTORICAL_MEMORY_ARTIFACT),
        "paperops_summary": _read_json(runtime / PAPEROPS_SUMMARY_ARTIFACT),
    }


def _source_refs() -> dict[str, str]:
    return {
        "self_model_ref": f"data/runtime/{SELF_MODEL_ARTIFACT}",
        "foundry_ref": f"data/runtime/{STRATEGY_FOUNDRY_ARTIFACT}",
        "akber_ref": f"data/runtime/{AKBER_FILTER_ARTIFACT}",
        "shadow_ref": f"data/runtime/{SHADOW_SIMULATOR_ARTIFACT}",
        "historical_memory_ref": f"data/runtime/{HISTORICAL_MEMORY_ARTIFACT}",
        "paperops_ref": f"data/runtime/{PAPEROPS_SUMMARY_ARTIFACT}",
    }


def _record_by_id(records: list[dict[str, Any]], key: str, value: Any) -> dict[str, Any]:
    if not value:
        return {}
    for record in records:
        if record.get(key) == value:
            return record
    return {}


def _input_records(context: dict[str, Any]) -> list[dict[str, Any]]:
    inputs: list[dict[str, Any]] = []
    for akber in context["akber_results"]:
        rejected = _record_by_id(
            context["rejected_strategy_hypotheses"],
            "rejected_hypothesis_id",
            akber.get("source_rejected_hypothesis_id"),
        )
        hypothesis = _record_by_id(
            context["strategy_hypotheses"],
            "strategy_hypothesis_id",
            akber.get("strategy_hypothesis_id"),
        )
        source = hypothesis or rejected
        item = copy.deepcopy(source)
        item["router_input_type"] = (
            "strategy_hypothesis" if hypothesis else "rejected_strategy_hypothesis"
        )
        item["akber_result"] = akber
        inputs.append(item)
    if inputs:
        return inputs
    for hypothesis in context["strategy_hypotheses"]:
        item = copy.deepcopy(hypothesis)
        item["router_input_type"] = "strategy_hypothesis"
        item["akber_result"] = {}
        inputs.append(item)
    for rejected in context["rejected_strategy_hypotheses"]:
        item = copy.deepcopy(rejected)
        item["router_input_type"] = "rejected_strategy_hypothesis"
        item["akber_result"] = {}
        inputs.append(item)
    return inputs


def _strategy_key(strategy: dict[str, Any]) -> str:
    return (
        strategy.get("strategy_hypothesis_id")
        or strategy.get("rejected_hypothesis_id")
        or strategy.get("source_pattern_id")
        or strategy.get("akber_result", {}).get("akber_filter_result_id")
        or "unknown_strategy"
    )


def _candidate_identity(strategy: dict[str, Any]) -> dict[str, Any]:
    if isinstance(strategy.get("candidate_identity"), dict):
        return strategy["candidate_identity"]
    akber = strategy.get("akber_result", {})
    return {
        "candidate_identity_key": akber.get("candidate_identity_key"),
        "instrument": None,
        "thesis": None,
    }


def _strategy_family(strategy: dict[str, Any]) -> dict[str, Any]:
    family = strategy.get("strategy_family")
    primary = None
    if isinstance(family, dict):
        primary = family.get("mapped_existing_family") or family.get("primary_family")
    elif isinstance(family, str):
        primary = family
    lineage = strategy.get("research_goal_lineage", {})
    return {
        "type": "rejected_or_shadow_family_candidate"
        if strategy.get("router_input_type") == "rejected_strategy_hypothesis"
        else "strategy_hypothesis_candidate",
        "primary_family": primary or lineage.get("target_strategy_family") or "unmapped_strategy_family",
        "secondary_families": [],
        "family_fit_reason": "Inherited from Strategy Foundry mapping.",
        "families_rejected": [],
        "foundry_review_required": primary is None,
    }


def _shadow_for_strategy(strategy: dict[str, Any], context: dict[str, Any]) -> list[dict[str, Any]]:
    akber_id = strategy.get("akber_result", {}).get("akber_filter_result_id")
    rejected_id = strategy.get("rejected_hypothesis_id") or strategy.get("akber_result", {}).get("source_rejected_hypothesis_id")
    hypothesis_id = strategy.get("strategy_hypothesis_id")
    matches = []
    for record in context["shadow_results"]:
        if akber_id and record.get("akber_filter_result_id") == akber_id:
            matches.append(record)
        elif rejected_id and record.get("rejected_hypothesis_id") == rejected_id:
            matches.append(record)
        elif hypothesis_id and record.get("strategy_hypothesis_id") == hypothesis_id:
            matches.append(record)
    return matches


def _self_model_soft_blockers(context: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    self_model = context["self_model"]
    if self_model.get("status") not in SELF_MODEL_READY_STATUSES:
        blockers.append("self_model_not_ready")
    for component in self_model.get("degraded_components", []):
        if isinstance(component, dict):
            name = str(component.get("component") or "component")
            reason = str(component.get("reason") or "degraded")
            blockers.append(f"{name}:{reason}")
    return blockers[:8]


def _system_repair_blockers(context: dict[str, Any]) -> list[str]:
    repair: list[str] = []
    for key, label in (
        ("self_model", "self_model_missing"),
        ("strategy_foundry", "strategy_foundry_missing"),
        ("akber_filter", "akber_filter_missing"),
        ("historical_memory", "historical_memory_missing"),
    ):
        if not context.get(key):
            repair.append(label)
    if not context.get("shadow_simulator"):
        repair.append("shadow_simulator_missing")
    return repair


def _gate_state(strategy: dict[str, Any], context: dict[str, Any]) -> dict[str, str]:
    akber = strategy.get("akber_result", {})
    shadow_records = _shadow_for_strategy(strategy, context)
    paperability = strategy.get("paperability", {})
    evidence = strategy.get("evidence_summary", strategy.get("evidence", {}))
    quantum = evidence.get("quantum_recommendation")
    return {
        "source_quorum": "pass" if evidence.get("source_price_lineage_present") else "not_recorded",
        "catalyst": "pass" if _candidate_identity(strategy).get("thesis") else "missing",
        "akber_filter": akber.get("decision", {}).get("filter_decision", "missing"),
        "linear_review": evidence.get("linear_status", "not_recorded"),
        "nonlinear_review": "pass_for_research" if evidence.get("nonlinear_score") is not None else "not_recorded",
        "quantum_review": quantum or "missing",
        "shadow_replay": _shadow_gate(shadow_records),
        "duplicate_exposure": "not_yet_reviewed_by_router",
        "daily_drawdown": context["self_model"].get("risk_state", {}).get("drawdown_state", "not_recorded"),
        "risk_budget": "downstream_risk_agent_only",
        "paper_route": paperability.get("paperability_state") or "not_yet_reviewed",
    }


def _shadow_gate(shadow_records: list[dict[str, Any]]) -> str:
    if not shadow_records:
        return "missing"
    statuses = {record.get("decision", {}).get("shadow_status") for record in shadow_records}
    if "candidate_for_router_review" in statuses:
        return "candidate_for_router_review"
    if "reject_after_shadow_replay" in statuses:
        return "reject_after_shadow_replay"
    if "watch_only" in statuses:
        return "watch_only"
    if "hold_for_more_shadow_data" in statuses:
        return "hold_for_more_shadow_data"
    return "audit_only"


def apply_router_vetoes(strategy: dict[str, Any], context: dict[str, Any]) -> dict[str, list[str]]:
    hard: list[str] = []
    soft: list[str] = []
    akber = strategy.get("akber_result", {})
    akber_decision = akber.get("decision", {})
    if akber_decision.get("filter_decision") == "reject":
        hard.append(f"akber_filter_reject:{akber_decision.get('veto_reason') or 'unspecified'}")
    if akber_decision.get("filter_decision") in {"hold_missing_context", "hold_wait_for_confirmation"}:
        soft.append(f"akber_filter_{akber_decision.get('filter_decision')}")
    for evidence in akber_decision.get("next_required_evidence", []):
        soft.append(f"missing_{evidence}")
    for reason in strategy.get("rejection_reasons", []):
        if reason in {
            "point_in_time_leakage",
            "source_quorum_weak",
            "quantum_ambiguity_too_high",
            "instrument_is_observable_or_futures_symbol_not_guarded_paper_route",
            "no_clean_paper_expression",
            "risk_shape_unacceptable",
            "live_only_expression_not_allowed",
        }:
            hard.append(reason)
        else:
            soft.append(reason)
    paperability = strategy.get("paperability", {})
    for blocker in paperability.get("paperability_blockers", []):
        hard.append(f"paperability:{blocker}")
    if paperability.get("paper_order_allowed") is True:
        hard.append("upstream_paper_order_authority_detected")
    self_why = context["self_model"].get("why_not_trading_now", {})
    if self_why.get("category") == "duplicate_or_idempotency_hold":
        soft.append("paperops_current_duplicate_hold_requires_distinct_idempotency_key")
    if context["self_model"].get("risk_state", {}).get("current_exposure", {}).get("open_order_count", 0):
        soft.append("open_order_state_requires_downstream_duplicate_check")
    if context["shadow_simulator"].get("candidate_for_router_count", 0) == 0:
        soft.append("shadow_replay_has_no_router_candidate")
    if strategy.get("probationary_strategy_hypothesis") is True:
        soft.append("missing_foundry_promotion_confirmation")
    if context["akber_filter"].get("status") not in AKBER_READY_STATUSES:
        soft.append("akber_filter_artifact_degraded")
    elif context["akber_filter"].get("status") == "qsase_akber_filter_integration_ready_with_holds":
        soft.append("akber_filter_waiting_for_confirmation")
    if context["strategy_foundry"].get("status") not in STRATEGY_FOUNDRY_READY_STATUSES:
        soft.append("strategy_foundry_artifact_degraded")
    elif context["strategy_foundry"].get("status") == "qsase_strategy_foundry_ready_with_probationary_hypotheses":
        soft.append("foundry_probationary_research_needs_confirmation")
    soft.extend(_self_model_soft_blockers(context))
    return {"hard_vetoes": sorted(set(hard)), "soft_blockers": sorted(set(soft))}


def score_strategy_for_router(strategy: dict[str, Any], context: dict[str, Any]) -> dict[str, float]:
    akber = strategy.get("akber_result", {})
    evidence = strategy.get("evidence_summary", strategy.get("evidence", {}))
    hard_soft = apply_router_vetoes(strategy, context)
    shadow_records = _shadow_for_strategy(strategy, context)
    shadow_score = max(
        [record.get("scores", {}).get("shadow_variant_score", 0.0) for record in shadow_records] or [0.0]
    )
    akber_score = _float(akber.get("scores", {}).get("akber_filter_score"), 0.0)
    linear_score = _float(evidence.get("linear_score"), 0.0)
    nonlinear_score = _float(evidence.get("nonlinear_score"), 0.0)
    market_edge = _clamp((akber_score * 0.35) + (linear_score * 0.25) + (nonlinear_score * 0.25) + (shadow_score * 0.15))
    stack_fitness = 0.62
    if context["self_model"].get("status") != "qsase_self_model_ready":
        stack_fitness -= 0.16
    if evidence.get("quantum_recommendation") in {"upgrade", "pass_for_research"}:
        stack_fitness += 0.08
    if evidence.get("quantum_recommendation") == "downgrade_or_hold":
        stack_fitness -= 0.08
    route_readiness = 0.72
    if hard_soft["hard_vetoes"]:
        route_readiness = 0.0
    elif hard_soft["soft_blockers"]:
        route_readiness = 0.35
    learning_value = 0.88 if strategy.get("router_input_type") == "rejected_strategy_hypothesis" else 0.72
    risk_cleanliness = 0.65 if not hard_soft["hard_vetoes"] else 0.18
    source_freshness = 0.55 if "source_state:missing_optional_source_credentials" in hard_soft["soft_blockers"] else 0.75
    evidence_diversity = 0.62 if evidence.get("source_price_lineage_present") else 0.25
    total = (
        market_edge * 0.24
        + stack_fitness * 0.16
        + route_readiness * 0.24
        + learning_value * 0.16
        + risk_cleanliness * 0.12
        + evidence_diversity * 0.08
    )
    return {
        "market_edge_score": round(_clamp(market_edge), 6),
        "stack_fitness_score": round(_clamp(stack_fitness), 6),
        "route_readiness_score": round(_clamp(route_readiness), 6),
        "learning_value_score": round(_clamp(learning_value), 6),
        "risk_cleanliness_score": round(_clamp(risk_cleanliness), 6),
        "source_freshness_score": round(_clamp(source_freshness), 6),
        "evidence_diversity_score": round(_clamp(evidence_diversity), 6),
        "shadow_replay_support_score": round(_clamp(shadow_score), 6),
        "router_total_score": round(_clamp(total), 6),
    }


def _decision_state(
    strategy: dict[str, Any],
    scores: dict[str, float],
    gates: dict[str, str],
    hard_vetoes: list[str],
    soft_blockers: list[str],
    repair_blockers: list[str],
) -> dict[str, Any]:
    if repair_blockers:
        output = "repair_requested"
        reason = f"Router cannot evaluate cleanly because {repair_blockers[0]}."
        next_action = "repair_missing_or_invalid_router_input"
    elif any(_is_safety_veto(veto) for veto in hard_vetoes):
        output = "blocked_safety_boundary"
        reason = f"Hard safety boundary blocks paper review: {hard_vetoes[0]}."
        next_action = "clear_safety_boundary_or_remap_to_paperable_expression"
    elif hard_vetoes:
        output = "reject"
        reason = f"Hard evidence veto blocks this strategy: {hard_vetoes[0]}."
        next_action = "reject_and_keep_learning_evidence"
    elif gates.get("shadow_replay") in {"missing", "hold_for_more_shadow_data"}:
        output = "shadow_only"
        reason = "Shadow replay evidence is incomplete; keep this strategy in shadow-only observation."
        next_action = "run_or_refresh_shadow_replay"
    elif any("missing_" in blocker for blocker in soft_blockers):
        output = "hold_missing_evidence"
        reason = f"Required evidence is missing: {soft_blockers[0]}."
        next_action = "watch_for_missing_confirmation"
    elif any("route" in blocker or "paper" in blocker for blocker in soft_blockers):
        output = "hold_route_unavailable"
        reason = f"Route readiness is not clean: {soft_blockers[0]}."
        next_action = "refresh_route_and_paperability_state"
    elif scores["router_total_score"] < 0.52:
        output = "watchlist_only"
        reason = "Evidence is relevant but not strong enough for PaperOps gate-interface review."
        next_action = "continue_watchlist_monitoring"
    else:
        output = "paper_review_candidate"
        reason = "All router hard vetoes cleared; this is eligible for PaperOps Gate Interface review only."
        next_action = "prepare_paperops_gate_interface_review"
    why = (
        "Eligible for PaperOps Gate Interface review only; no order, risk approval, or execution approval exists."
        if output == "paper_review_candidate"
        else reason
    )
    return {
        "router_output": output,
        "reason": reason,
        "next_required_action": next_action,
        "paper_review_candidate": output == "paper_review_candidate",
        "why_not_trading_now": why,
        "authority_boundary": "router output is not execution approval and creates no paper order",
    }


def _is_safety_veto(veto: str) -> bool:
    safety_terms = (
        "point_in_time",
        "paperability",
        "paper_route",
        "paper_expression",
        "live",
        "broker",
        "duplicate",
        "idempotency",
        "drawdown",
        "risk",
        "telegram",
        "observable_or_futures",
    )
    return any(term in veto for term in safety_terms)


def build_paper_review_candidate_handoff(decision: dict[str, Any]) -> dict[str, Any] | None:
    if decision.get("decision", {}).get("router_output") != "paper_review_candidate":
        return None
    identity = decision.get("candidate_identity", {})
    return {
        "router_decision_id": decision.get("router_decision_id"),
        "strategy_hypothesis_id": decision.get("strategy_hypothesis_id"),
        "research_goal_id": decision.get("lineage", {}).get("research_goal_id"),
        "candidate_identity_key": identity.get("candidate_identity_key"),
        "proposed_strategy_family": decision.get("strategy_family", {}).get("primary_family"),
        "evidence_summary": decision.get("evidence_summary", {}),
        "required_gates": decision.get("gates", {}),
        "current_blockers_cleared": True,
        "known_residual_risks": decision.get("soft_blockers", []),
        "idempotency_seed": _hash_id(
            [
                decision.get("router_decision_id"),
                identity.get("candidate_identity_key"),
                decision.get("lineage", {}).get("research_goal_id"),
            ],
            "qsase-router-idempotency-seed",
        ),
        "exposure_summary": "downstream_risk_agent_required_before_any_order",
        "why_not_trading_now": decision.get("decision", {}).get("why_not_trading_now"),
        "paper_order_created": False,
        "qualified_setup_created": False,
        "authority": _authority_block(),
    }


def _telegram_summary(decision: dict[str, Any], identity: dict[str, Any]) -> dict[str, Any]:
    strategy = identity.get("thesis") or decision.get("strategy_family", {}).get("primary_family")
    text = (
        f"Qadam router {decision['decision']['router_output']}\n"
        f"Strategy: {str(strategy)[:72]}\n"
        f"Reason: {decision['decision']['reason'][:96]}\n"
        "Next: watch, no paper order\n"
        "Dashboard: qadam.trade/dashboard/"
    )
    return {
        "review_only": True,
        "command_disabled": True,
        "live_send_allowed": False,
        "contains_command": False,
        "contains_broker_instruction": False,
        "text": text,
    }


def _build_router_decision(strategy: dict[str, Any], context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    repair_blockers = _system_repair_blockers(context)
    hard_soft = apply_router_vetoes(strategy, context)
    gates = _gate_state(strategy, context)
    scores = score_strategy_for_router(strategy, context)
    decision = _decision_state(
        strategy,
        scores,
        gates,
        hard_soft["hard_vetoes"],
        hard_soft["soft_blockers"],
        repair_blockers,
    )
    identity = _candidate_identity(strategy)
    lineage = {
        **_source_refs(),
        "research_goal_id": strategy.get("research_goal_lineage", {}).get("research_goal_id")
        or strategy.get("akber_result", {}).get("research_goal_id"),
        "candidate_identity_key": identity.get("candidate_identity_key"),
        "source_pattern_id": strategy.get("source_pattern_id"),
        "akber_filter_result_id": strategy.get("akber_result", {}).get("akber_filter_result_id"),
        "shadow_replay_ids": [
            record.get("shadow_replay_id") for record in _shadow_for_strategy(strategy, context)
        ],
        "paper_growth_trial_calendar_advance_allowed": False,
        "paper_proof_ledger_credit_allowed": False,
    }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "router_decision_id": _hash_id([SCHEMA_VERSION, _strategy_key(strategy)], "qsase-router"),
        "generated_at": generated_at,
        "router_input_type": strategy.get("router_input_type"),
        "strategy_hypothesis_id": strategy.get("strategy_hypothesis_id"),
        "rejected_hypothesis_id": strategy.get("rejected_hypothesis_id")
        or strategy.get("akber_result", {}).get("source_rejected_hypothesis_id"),
        "source_pattern_id": strategy.get("source_pattern_id"),
        "candidate_identity": identity,
        "strategy_family": _strategy_family(strategy),
        "evidence_summary": strategy.get("evidence_summary", strategy.get("evidence", {})),
        "scores": scores,
        "gates": gates,
        "hard_vetoes": hard_soft["hard_vetoes"],
        "soft_blockers": hard_soft["soft_blockers"],
        "repair_blockers": repair_blockers,
        "decision": decision,
        "lineage": lineage,
        "paper_review_candidate_handoff": None,
        "telegram_summary": {},
        "authority": _authority_block(),
        **ROUTER_AUTHORITY_FLAGS,
    }
    payload["paper_review_candidate_handoff"] = build_paper_review_candidate_handoff(payload)
    payload["telegram_summary"] = _telegram_summary(payload, identity)
    return payload


def _hard_veto_records(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records = []
    for decision in decisions:
        for veto in decision.get("hard_vetoes", []):
            records.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "hard_veto_id": _hash_id([decision["router_decision_id"], veto], "qsase-router-veto"),
                    "router_decision_id": decision["router_decision_id"],
                    "strategy_key": decision.get("strategy_hypothesis_id") or decision.get("rejected_hypothesis_id"),
                    "veto": veto,
                    "blocks_paper_review_candidate": True,
                    "paper_order_created": False,
                    "proof_credit_allowed": False,
                    "authority": _authority_block(),
                }
            )
    return records


def _soft_blocker_records(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records = []
    for decision in decisions:
        for blocker in decision.get("soft_blockers", []):
            records.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "soft_blocker_id": _hash_id([decision["router_decision_id"], blocker], "qsase-router-soft"),
                    "router_decision_id": decision["router_decision_id"],
                    "strategy_key": decision.get("strategy_hypothesis_id") or decision.get("rejected_hypothesis_id"),
                    "blocker": blocker,
                    "next_required_action": decision.get("decision", {}).get("next_required_action"),
                    "paper_order_created": False,
                    "proof_credit_allowed": False,
                    "authority": _authority_block(),
                }
            )
    return records


def _state_counts(decisions: list[dict[str, Any]]) -> dict[str, int]:
    counts = {state: 0 for state in ROUTER_STATES}
    for decision in decisions:
        state = decision.get("decision", {}).get("router_output")
        if state in counts:
            counts[state] += 1
    return counts


def _scoreboard(decisions: list[dict[str, Any]], generated_at: str) -> dict[str, Any]:
    ranked = sorted(
        decisions,
        key=lambda item: item.get("scores", {}).get("router_total_score", 0.0),
        reverse=True,
    )
    top = ranked[0] if ranked else {}
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_strategy_router_scoreboard",
        "generated_at": generated_at,
        "status": "scoreboard_ready",
        "ranked_count": len(ranked),
        "top_ranked_strategy": top.get("router_decision_id"),
        "top_router_output": top.get("decision", {}).get("router_output"),
        "top_reason": top.get("decision", {}).get("reason"),
        "ranked_decisions": [
            {
                "rank": index + 1,
                "router_decision_id": decision.get("router_decision_id"),
                "router_output": decision.get("decision", {}).get("router_output"),
                "router_total_score": decision.get("scores", {}).get("router_total_score"),
                "primary_family": decision.get("strategy_family", {}).get("primary_family"),
                "candidate_identity_key": decision.get("candidate_identity", {}).get("candidate_identity_key"),
                "hard_veto_count": len(decision.get("hard_vetoes", [])),
                "soft_blocker_count": len(decision.get("soft_blockers", [])),
            }
            for index, decision in enumerate(ranked)
        ],
        "authority": _authority_block(),
    }


def _why_not_trading_now(decisions: list[dict[str, Any]], generated_at: str, context: dict[str, Any]) -> dict[str, Any]:
    paper_candidates = [d for d in decisions if d.get("decision", {}).get("router_output") == "paper_review_candidate"]
    if paper_candidates:
        reason = "router_has_paper_review_candidate_but_no_order_authority"
        category = "paper_review_candidate_not_order"
        next_action = "send_to_qsase_11_paperops_handoff_interface_when_requested"
        repair_required = False
        details = {"paper_review_candidate_count": len(paper_candidates)}
    else:
        top = sorted(decisions, key=lambda d: d.get("scores", {}).get("router_total_score", 0.0), reverse=True)[0] if decisions else {}
        reason = top.get("decision", {}).get("why_not_trading_now") or "no_router_decisions_available"
        category = top.get("decision", {}).get("router_output") or "router_no_decision"
        next_action = top.get("decision", {}).get("next_required_action") or "repair_router_inputs"
        repair_required = category == "repair_requested"
        details = {
            "router_decision_id": top.get("router_decision_id"),
            "hard_vetoes": top.get("hard_vetoes", []),
            "soft_blockers": top.get("soft_blockers", [])[:8],
            "paperops_why_not_trading_now": context["self_model"].get("why_not_trading_now", {}),
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_why_not_trading_now",
        "generated_at": generated_at,
        "status": "why_not_trading_now_recorded",
        "blocking_layer": "strategy_router",
        "category": category,
        "reason": reason,
        "next_allowed_action": next_action,
        "repair_required": repair_required,
        "paper_review_candidate_count": len(paper_candidates),
        "paper_order_created": False,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "details": details,
        "authority": _authority_block(),
    }


def _dashboard_summary(payload: dict[str, Any]) -> dict[str, Any]:
    top = payload.get("scoreboard", {})
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_strategy_router_dashboard_summary",
        "generated_at": payload["generated_at"],
        "status": payload["status"],
        "public_safe": True,
        "command_disabled": True,
        "live_send_allowed": False,
        "summary_rows": [
            {"label": "Router status", "value": payload["status"]},
            {"label": "Strategy inputs", "value": payload["strategy_input_count"]},
            {"label": "Paper-review candidates", "value": payload["paper_review_candidate_count"]},
            {"label": "Hard vetoes", "value": payload["hard_veto_count"]},
            {"label": "Soft blockers", "value": payload["soft_blocker_count"]},
            {"label": "Top output", "value": top.get("top_router_output")},
            {"label": "Authority", "value": "no paper order"},
        ],
        "top_strategy": top.get("top_ranked_strategy"),
        "router_output": top.get("top_router_output"),
        "why_not_trading_now": payload["why_not_trading_now"]["reason"],
        "hard_vetoes": payload.get("hard_veto_records", [])[:5],
        "soft_blockers": payload.get("soft_blocker_records", [])[:5],
        "score_components": top.get("ranked_decisions", [])[:3],
        "next_required_action": payload["why_not_trading_now"]["next_allowed_action"],
        "authority_state": "strategy_router_no_order_authority",
        "no_trade_candidates_created": True,
        "no_paper_orders_created": True,
        "no_proof_credit_granted": True,
        "authority_flags_false": all(value is False for value in payload["authority_flags"].values()),
    }


def build_strategy_router_decisions(settings: Settings | None = None) -> dict[str, Any]:
    context = _load_context(settings)
    generated_at = _iso(_now())
    strategies = _input_records(context)
    decisions = [_build_router_decision(strategy, context, generated_at) for strategy in strategies]
    hard_vetoes = _hard_veto_records(decisions)
    soft_blockers = _soft_blocker_records(decisions)
    scoreboard = _scoreboard(decisions, generated_at)
    why_not = _why_not_trading_now(decisions, generated_at, context)
    counts = _state_counts(decisions)
    repair_blockers = _system_repair_blockers(context)
    degraded_reasons: list[str] = []
    if context["self_model"].get("status") not in SELF_MODEL_READY_STATUSES:
        degraded_reasons.append("self_model_not_ready")
    if context["strategy_foundry"].get("status") not in STRATEGY_FOUNDRY_READY_STATUSES:
        degraded_reasons.append("strategy_foundry_degraded")
    if context["akber_filter"].get("status") not in AKBER_READY_STATUSES:
        degraded_reasons.append("akber_filter_degraded")
    if context["shadow_simulator"].get("status") not in SHADOW_SIMULATOR_READY_STATUSES:
        degraded_reasons.append("shadow_simulator_degraded")
    if not strategies:
        degraded_reasons.append("no_strategy_inputs")
    status = "qsase_strategy_router_ready"
    if repair_blockers:
        status = "qsase_strategy_router_blocked"
    elif degraded_reasons:
        status = "qsase_strategy_router_degraded"
    elif not counts["paper_review_candidate"]:
        status = "qsase_strategy_router_ready_no_paper_candidate"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_strategy_router_decisions",
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "generated_at": generated_at,
        "status": status,
        "public_safe": True,
        "command_disabled": True,
        "paper_only": True,
        "research_only": True,
        "proposal_first": True,
        "strategy_input_count": len(strategies),
        "watch_count": counts["watchlist_only"],
        "watchlist_only_count": counts["watchlist_only"],
        "research_count": 0,
        "hold_count": counts["hold_missing_evidence"] + counts["hold_route_unavailable"],
        "hold_missing_evidence_count": counts["hold_missing_evidence"],
        "hold_route_unavailable_count": counts["hold_route_unavailable"],
        "reject_count": counts["reject"],
        "shadow_replay_count": counts["shadow_only"],
        "shadow_only_count": counts["shadow_only"],
        "strategy_foundry_review_count": 0,
        "repair_requested_count": counts["repair_requested"],
        "blocked_safety_boundary_count": counts["blocked_safety_boundary"],
        "paper_review_candidate_count": counts["paper_review_candidate"],
        "hard_veto_count": len(hard_vetoes),
        "soft_blocker_count": len(soft_blockers),
        "top_ranked_strategy": scoreboard.get("top_ranked_strategy"),
        "why_not_trading_now": why_not,
        "router_decisions": decisions,
        "scoreboard": scoreboard,
        "hard_veto_records": hard_vetoes,
        "soft_blocker_records": soft_blockers,
        "paper_review_candidate_handoffs": [
            decision["paper_review_candidate_handoff"]
            for decision in decisions
            if decision.get("paper_review_candidate_handoff")
        ],
        "input_artifacts": _source_refs(),
        "missing_required_state": repair_blockers,
        "degraded_reasons": sorted(set(degraded_reasons)),
        "paper_review_candidate_is_not_order": True,
        "router_output_creates_no_orders": True,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "trade_candidate_created": False,
        "qualified_setup_created": False,
        "risk_handoff_allowed": False,
        "execution_intent_created": False,
        "paper_order_created": False,
        "paper_proof_ledger_credit_allowed": False,
        "paper_growth_trial_calendar_advanced": False,
        "simulated_elapsed_time_allowed": False,
        "authority": universal_authority_flags(),
        "authority_flags": dict(ROUTER_AUTHORITY_FLAGS),
    }
    payload["dashboard_safe_summary"] = _dashboard_summary(payload)
    return payload


def _summary_without_records(payload: dict[str, Any]) -> dict[str, Any]:
    summary = dict(payload)
    summary.pop("router_decisions", None)
    summary.pop("hard_veto_records", None)
    summary.pop("soft_blocker_records", None)
    return summary


def load_strategy_router_decisions(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    payload = _read_json(runtime / PRIMARY_ARTIFACT)
    if payload:
        payload["router_decisions"] = _read_jsonl(runtime / DECISIONS_ARTIFACT)
        payload["hard_veto_records"] = _read_jsonl(runtime / HARD_VETOES_ARTIFACT)
        payload["soft_blocker_records"] = _read_jsonl(runtime / SOFT_BLOCKERS_ARTIFACT)
        scoreboard = _read_json(runtime / SCOREBOARD_ARTIFACT)
        why_not = _read_json(runtime / WHY_NOT_ARTIFACT)
        if scoreboard:
            payload["scoreboard"] = scoreboard
        if why_not:
            payload["why_not_trading_now"] = why_not
    return payload


def _validate_authority(flags: dict[str, Any], prefix: str) -> list[str]:
    errors: list[str] = []
    for key, expected in ROUTER_AUTHORITY_FLAGS.items():
        if flags.get(key) is not expected:
            errors.append(f"{prefix}_{key}_must_be_false")
    return errors


def validate_strategy_router_decisions(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("artifact_type") != "qsase_strategy_router_decisions":
        errors.append("artifact_type_invalid")
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if payload.get("status") not in {
        "qsase_strategy_router_ready",
        "qsase_strategy_router_ready_no_paper_candidate",
        "qsase_strategy_router_degraded",
        "qsase_strategy_router_blocked",
    }:
        errors.append("status_invalid")
    if payload.get("public_safe") is not True or payload.get("command_disabled") is not True:
        errors.append("public_safe_command_disabled_required")
    for key in (
        "paper_review_candidate_is_not_order",
        "router_output_creates_no_orders",
    ):
        if payload.get(key) is not True:
            errors.append(f"{key}_must_be_true")
    for key in (
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "proof_credit_allowed",
        "live_capital_enabled",
        "trade_candidate_created",
        "qualified_setup_created",
        "risk_handoff_allowed",
        "execution_intent_created",
        "paper_order_created",
        "paper_proof_ledger_credit_allowed",
        "paper_growth_trial_calendar_advanced",
        "simulated_elapsed_time_allowed",
    ):
        if payload.get(key) is not False:
            errors.append(f"{key}_must_be_false")
    authority = payload.get("authority", {})
    if not isinstance(authority, dict) or any(value is not False for value in authority.values()):
        errors.append("universal_authority_flags_must_all_be_false")
    errors.extend(_validate_authority(payload.get("authority_flags", {}), "router"))
    decisions = payload.get("router_decisions")
    if not isinstance(decisions, list):
        errors.append("router_decisions_missing")
        decisions = []
    if payload.get("strategy_input_count") != len(decisions):
        errors.append("strategy_input_count_mismatch")
    for decision in decisions:
        decision_id = decision.get("router_decision_id")
        for field in REQUIRED_DECISION_FIELDS:
            if field not in decision:
                errors.append(f"router_decision_{decision_id}_missing_{field}")
        output = decision.get("decision", {}).get("router_output")
        if output not in ROUTER_STATES:
            errors.append(f"router_decision_{decision_id}_invalid_router_output")
        if not str(decision.get("decision", {}).get("reason") or "").strip():
            errors.append(f"router_decision_{decision_id}_missing_reason")
        why = str(decision.get("decision", {}).get("why_not_trading_now") or "").strip()
        if not why:
            errors.append(f"router_decision_{decision_id}_missing_why_not_trading_now")
        if decision.get("hard_vetoes") and output == "paper_review_candidate":
            errors.append(f"router_decision_{decision_id}_hard_veto_paper_review_candidate")
        handoff = decision.get("paper_review_candidate_handoff")
        if output == "paper_review_candidate" and not handoff:
            errors.append(f"router_decision_{decision_id}_missing_paper_review_handoff")
        if output != "paper_review_candidate" and handoff is not None:
            errors.append(f"router_decision_{decision_id}_unexpected_paper_review_handoff")
        if decision.get("decision", {}).get("paper_review_candidate") != (output == "paper_review_candidate"):
            errors.append(f"router_decision_{decision_id}_paper_review_candidate_flag_mismatch")
        telegram = decision.get("telegram_summary", {})
        if telegram.get("review_only") is not True or telegram.get("command_disabled") is not True:
            errors.append(f"router_decision_{decision_id}_telegram_not_review_only")
        if telegram.get("contains_command") is not False or telegram.get("contains_broker_instruction") is not False:
            errors.append(f"router_decision_{decision_id}_telegram_command_or_broker_language")
        if len(str(telegram.get("text") or "")) > 320:
            errors.append(f"router_decision_{decision_id}_telegram_too_long")
        for key in ROUTER_AUTHORITY_FLAGS:
            if decision.get(key) is not False:
                errors.append(f"router_decision_{decision_id}_{key}_must_be_false")
            if decision.get("authority", {}).get(key) is not False:
                errors.append(f"router_decision_{decision_id}_authority_{key}_must_be_false")
    paper_candidates = [d for d in decisions if d.get("decision", {}).get("router_output") == "paper_review_candidate"]
    seen_lineage: set[tuple[Any, Any]] = set()
    for candidate in paper_candidates:
        lineage_key = (
            candidate.get("lineage", {}).get("research_goal_id"),
            candidate.get("candidate_identity", {}).get("candidate_identity_key"),
        )
        if None in lineage_key or not all(lineage_key):
            errors.append(f"router_decision_{candidate.get('router_decision_id')}_paper_candidate_lineage_missing")
        if lineage_key in seen_lineage:
            errors.append("paper_review_candidate_distinct_lineage_violation")
        seen_lineage.add(lineage_key)
    why_not = payload.get("why_not_trading_now", {})
    if not why_not.get("reason"):
        errors.append("why_not_trading_now_reason_missing")
    if why_not.get("paper_order_created") is not False:
        errors.append("why_not_trading_now_paper_order_created")
    if why_not.get("proof_credit_allowed") is not False:
        errors.append("why_not_trading_now_proof_credit_allowed")
    scoreboard = payload.get("scoreboard", {})
    if scoreboard.get("ranked_count") != len(decisions):
        errors.append("scoreboard_ranked_count_mismatch")
    hard_veto_records = payload.get("hard_veto_records", [])
    for record in hard_veto_records:
        if record.get("blocks_paper_review_candidate") is not True:
            errors.append(f"hard_veto_{record.get('hard_veto_id')}_does_not_block_paper_review")
        errors.extend(_validate_authority(record.get("authority", {}), f"hard_veto_{record.get('hard_veto_id')}_authority"))
    soft_blocker_records = payload.get("soft_blocker_records", [])
    for record in soft_blocker_records:
        errors.extend(_validate_authority(record.get("authority", {}), f"soft_blocker_{record.get('soft_blocker_id')}_authority"))
    summary = payload.get("dashboard_safe_summary", {})
    if summary:
        if summary.get("public_safe") is not True or summary.get("command_disabled") is not True:
            errors.append("dashboard_summary_public_safe_required")
        if summary.get("live_send_allowed") is not False:
            errors.append("dashboard_summary_live_send_must_be_false")
        if summary.get("authority_state") != "strategy_router_no_order_authority":
            errors.append("dashboard_summary_authority_boundary_required")
    return sorted(set(errors))


def build_qsase_phase_implementation_status(payload: dict[str, Any]) -> dict[str, Any]:
    runtime_dir = _runtime_dir()
    existing = _read_json(runtime_dir / PHASE_STATUS_ARTIFACT)
    phases = existing.get("phases") if isinstance(existing.get("phases"), dict) else {}
    phases[PHASE_ID] = {
        "name": PHASE_NAME,
        "status": payload["status"],
        "artifact_path": f"data/runtime/{PRIMARY_ARTIFACT}",
        "decisions_path": f"data/runtime/{DECISIONS_ARTIFACT}",
        "scoreboard_path": f"data/runtime/{SCOREBOARD_ARTIFACT}",
        "why_not_trading_now_path": f"data/runtime/{WHY_NOT_ARTIFACT}",
        "hard_vetoes_path": f"data/runtime/{HARD_VETOES_ARTIFACT}",
        "soft_blockers_path": f"data/runtime/{SOFT_BLOCKERS_ARTIFACT}",
        "strategy_input_count": payload["strategy_input_count"],
        "paper_review_candidate_count": payload["paper_review_candidate_count"],
        "blocked_safety_boundary_count": payload["blocked_safety_boundary_count"],
        "reject_count": payload["reject_count"],
        "hold_count": payload["hold_count"],
        "shadow_only_count": payload["shadow_only_count"],
        "watchlist_only_count": payload["watchlist_only_count"],
        "repair_requested_count": payload["repair_requested_count"],
        "hard_veto_count": payload["hard_veto_count"],
        "soft_blocker_count": payload["soft_blocker_count"],
        "paper_only": True,
        "research_only": True,
        "proposal_first": True,
        "public_safe": True,
        "paper_review_candidate_is_not_order": True,
        "router_output_creates_no_orders": True,
        "no_trade_candidates_created": True,
        "no_paper_orders_created": True,
        "no_proof_credit_granted": True,
        "authority_flags_false": True,
        "later_qsase_phases_implemented": False,
    }
    return {
        "schema_version": 1,
        "generated_at": payload["generated_at"],
        "active_phase": PHASE_ID,
        "phases": phases,
        "safety": payload["authority"],
    }


def _append_implementation_log(payload: dict[str, Any]) -> None:
    log_path = _repo_root() / IMPLEMENTATION_LOG
    log_path.parent.mkdir(parents=True, exist_ok=True)
    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else "# QSASE Implementation Log\n"
    marker = f"<!-- {PHASE_ID} -->"
    entry = (
        f"{marker}\n"
        f"## QSASE-10: Strategy Router\n\n"
        f"- Generated at: `{payload.get('generated_at')}`\n"
        f"- Status: `{payload.get('status')}`\n"
        f"- Runtime artifact: `data/runtime/{PRIMARY_ARTIFACT}`\n"
        f"- Strategy inputs: `{payload.get('strategy_input_count')}`\n"
        f"- Paper-review candidates: `{payload.get('paper_review_candidate_count')}`\n"
        f"- Blocked safety boundary / reject / hold / shadow-only / watchlist / repair: `{payload.get('blocked_safety_boundary_count')}` / `{payload.get('reject_count')}` / `{payload.get('hold_count')}` / `{payload.get('shadow_only_count')}` / `{payload.get('watchlist_only_count')}` / `{payload.get('repair_requested_count')}`\n"
        f"- Hard vetoes / soft blockers: `{payload.get('hard_veto_count')}` / `{payload.get('soft_blocker_count')}`\n"
        f"- Why-not-trading-now: `{payload.get('why_not_trading_now', {}).get('reason')}`\n"
        f"- Safety: router output is not execution approval; no trade candidates, risk approvals, execution intents, paper orders, broker writes, live capital, or proof credit created.\n"
    )
    if marker in existing:
        before = existing.split(marker, 1)[0].rstrip()
        updated = before + "\n\n" + entry
    elif existing.endswith("\n"):
        updated = existing + "\n" + entry
    else:
        updated = existing + "\n\n" + entry
    log_path.write_text(updated, encoding="utf-8")


def write_strategy_router_decisions(
    payload: dict[str, Any],
    settings: Settings | None = None,
    *,
    append_history: bool = True,
    append_log: bool = True,
) -> dict[str, str]:
    runtime_dir = _runtime_dir(settings)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "strategy_router": runtime_dir / PRIMARY_ARTIFACT,
        "router_decisions": runtime_dir / DECISIONS_ARTIFACT,
        "scoreboard": runtime_dir / SCOREBOARD_ARTIFACT,
        "why_not_trading_now": runtime_dir / WHY_NOT_ARTIFACT,
        "hard_vetoes": runtime_dir / HARD_VETOES_ARTIFACT,
        "soft_blockers": runtime_dir / SOFT_BLOCKERS_ARTIFACT,
        "dashboard_summary": runtime_dir / DASHBOARD_SUMMARY_ARTIFACT,
        "phase_status": runtime_dir / PHASE_STATUS_ARTIFACT,
    }
    _write_json(paths["strategy_router"], _summary_without_records(payload))
    _write_jsonl(paths["router_decisions"], payload["router_decisions"])
    _write_json(paths["scoreboard"], payload["scoreboard"])
    _write_json(paths["why_not_trading_now"], payload["why_not_trading_now"])
    _write_jsonl(paths["hard_vetoes"], payload["hard_veto_records"])
    _write_jsonl(paths["soft_blockers"], payload["soft_blocker_records"])
    _write_json(paths["dashboard_summary"], payload["dashboard_safe_summary"])
    _write_json(paths["phase_status"], build_qsase_phase_implementation_status(payload))
    written = {key: str(path) for key, path in paths.items()}
    if append_history:
        history_path = runtime_dir / HISTORY_ARTIFACT
        events_path = runtime_dir / EVENTS_ARTIFACT
        _append_jsonl(
            history_path,
            {
                "generated_at": payload["generated_at"],
                "status": payload["status"],
                "strategy_input_count": payload["strategy_input_count"],
                "paper_review_candidate_count": payload["paper_review_candidate_count"],
                "hard_veto_count": payload["hard_veto_count"],
                "soft_blocker_count": payload["soft_blocker_count"],
                "why_not_trading_now": payload["why_not_trading_now"]["reason"],
                "no_paper_orders_created": True,
            },
        )
        _append_jsonl(
            events_path,
            {
                "generated_at": payload["generated_at"],
                "event_type": "qsase_strategy_router_decisions_written",
                "status": payload["status"],
                "public_safe": True,
                "authority_flags_false": True,
            },
        )
        written["history"] = str(history_path)
        written["events"] = str(events_path)
    if append_log:
        _append_implementation_log(payload)
        written["implementation_log"] = str(_repo_root() / IMPLEMENTATION_LOG)
    return written


def build_and_write_strategy_router_decisions(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    payload = build_strategy_router_decisions(settings)
    errors = validate_strategy_router_decisions(payload)
    written = write_strategy_router_decisions(payload, settings)
    return payload, written, errors


def validate_negative_strategy_router_probes() -> list[str]:
    base = build_strategy_router_decisions()
    errors: list[str] = []
    for flag in ROUTER_AUTHORITY_FLAGS:
        probe = copy.deepcopy(base)
        probe["authority_flags"][flag] = True
        if not any(flag in error for error in validate_strategy_router_decisions(probe)):
            errors.append(f"negative_probe_failed_for_{flag}")
    order_probe = copy.deepcopy(base)
    order_probe["paper_order_created"] = True
    if not any("paper_order_created" in error for error in validate_strategy_router_decisions(order_probe)):
        errors.append("negative_probe_failed_for_paper_order_created")
    if base["router_decisions"]:
        reason_probe = copy.deepcopy(base)
        reason_probe["router_decisions"][0]["decision"]["reason"] = ""
        if not any("missing_reason" in error for error in validate_strategy_router_decisions(reason_probe)):
            errors.append("negative_probe_failed_for_missing_reason")
        why_probe = copy.deepcopy(base)
        why_probe["router_decisions"][0]["decision"]["why_not_trading_now"] = ""
        if not any("missing_why_not_trading_now" in error for error in validate_strategy_router_decisions(why_probe)):
            errors.append("negative_probe_failed_for_missing_why")
        hard_veto_probe = copy.deepcopy(base)
        hard_index = next(
            (
                index
                for index, decision in enumerate(hard_veto_probe["router_decisions"])
                if decision.get("hard_vetoes")
            ),
            0,
        )
        if not hard_veto_probe["router_decisions"][hard_index].get("hard_vetoes"):
            hard_veto_probe["router_decisions"][hard_index]["hard_vetoes"] = ["synthetic_negative_probe_hard_veto"]
        hard_veto_probe["router_decisions"][hard_index]["decision"]["router_output"] = "paper_review_candidate"
        hard_veto_probe["router_decisions"][hard_index]["decision"]["paper_review_candidate"] = True
        hard_veto_probe["router_decisions"][hard_index]["paper_review_candidate_handoff"] = {
            "router_decision_id": hard_veto_probe["router_decisions"][hard_index]["router_decision_id"],
        }
        if not any("hard_veto_paper_review_candidate" in error for error in validate_strategy_router_decisions(hard_veto_probe)):
            errors.append("negative_probe_failed_for_hard_veto_candidate")
    dashboard_probe = copy.deepcopy(base)
    dashboard_probe["dashboard_safe_summary"]["live_send_allowed"] = True
    if not any("dashboard_summary_live_send" in error for error in validate_strategy_router_decisions(dashboard_probe)):
        errors.append("negative_probe_failed_for_dashboard_live_send")
    return errors


if __name__ == "__main__":
    artifact = build_strategy_router_decisions()
    print(_json_dump(_summary_without_records(artifact)))
