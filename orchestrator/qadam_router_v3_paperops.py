"""OR-15 Router V3 and guarded PaperOps release boundary.

Router V3 assigns exactly one research state to every V3 setup. Only a clean
paper-review candidate may produce an upstream PaperOps handoff, and a handoff
is never an order or permission to bypass the canonical PaperOps wrapper.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    sha256_json,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_wave_b_common import safe_float, stable_id

SCHEMA_VERSION = "qadam_router_v3_paperops.v1"
PHASE_ID = "OR-15"

DECISIONS_ARTIFACT = "qadam_router_v3_decisions.jsonl"
SCOREBOARD_ARTIFACT = "qadam_router_v3_scoreboard.json"
WHY_NOT_ARTIFACT = "qadam_router_v3_why_not_trading_now.json"
HANDOFF_ARTIFACT = "qadam_paperops_handoff_v3.jsonl"
HANDOFF_ACCEPTED_ARTIFACT = "qadam_paperops_handoff_v3_accepted.jsonl"
HANDOFF_REJECTIONS_ARTIFACT = "qadam_paperops_handoff_v3_rejections.jsonl"
HANDOFF_RECEIPTS_ARTIFACT = "qadam_paperops_handoff_v3_consumption_receipts.jsonl"
HANDOFF_CONSUMER_STATE_ARTIFACT = "qadam_paperops_handoff_v3_consumer_state.json"
HANDOFF_CONSUMER_CHECK_ARTIFACT = "qadam_paperops_handoff_v3_consumer_checks.json"
RELEASE_READINESS_ARTIFACT = "qadam_research_lock_release_readiness.json"
CHECK_ARTIFACT = "qadam_router_v3_paperops_checks.json"
RELEASE_CHECK_ARTIFACT = "qadam_research_lock_release_checks.json"

PHASE_STATUS_ARTIFACT = "qadam_operator_ready_phase_status.json"
LOCK_ARTIFACT = "qadam_long_backtest_lock.json"
OPERATOR_APPROVALS_ARTIFACT = "qadam_operator_strategy_policy_approvals.json"
STRATEGY_HYPOTHESES_ARTIFACT = "qadam_strategy_hypotheses_v3.jsonl"
PATTERN_SCORES_ARTIFACT = "qadam_pattern_score_v3_records.jsonl"
EDGE_REGISTRY_ARTIFACT = "qadam_edge_registry.jsonl"
EDGE_SUMMARY_ARTIFACT = "qadam_edge_registry_summary.json"
AKBER_RESULTS_ARTIFACT = "qadam_akber_filter_v3_results.jsonl"
SHADOW_DECISIONS_ARTIFACT = "qadam_forward_shadow_decisions.jsonl"
SHADOW_OUTCOMES_ARTIFACT = "qadam_forward_shadow_outcomes.jsonl"
SHADOW_PROMOTION_ARTIFACT = "qadam_shadow_promotion_readiness.json"
RISK_PROPOSALS_ARTIFACT = "qadam_position_size_proposals.jsonl"
RISK_STATE_ARTIFACT = "qadam_portfolio_risk_state.json"
RISK_POLICY_ARTIFACT = "qadam_portfolio_policy.json"
PAPEROPS_SUMMARY_ARTIFACT = "paperops_autonomous_pass_summary.json"
QCTRL_ARTIFACT = "paperops_qctrl_paper_consultation.json"
PAPER_POSITIONS_ARTIFACT = "paper_positions.jsonl"
PAPER_ORDERS_ARTIFACT = "paper_orders.jsonl"
PAPEROPS_SUBMISSION_LEDGER_ARTIFACT = "paperops_alpaca_paper_post_submission_ledger.json"

HANDOFF_MAXIMUM_AGE_SECONDS = 15 * 60
HANDOFF_FUTURE_TOLERANCE_SECONDS = 60
ABSOLUTE_PAPER_TRADE_CEILING_USD = 5_000.0

FINAL_STATES = {
    "reject",
    "watchlist",
    "shadow-only",
    "hold",
    "repair-requested",
    "blocked-safety-boundary",
    "paper-review-candidate",
}

REQUIRED_PHASES_FOR_RELEASE = tuple(f"OR-{index}" for index in range(15))
OPEN_EXPOSURE_STATES = {
    "accepted",
    "new",
    "open",
    "pending",
    "pending_new",
    "partially_filled",
    "submitted",
}
REQUIRED_LINEAGE_REFS = (
    "research_goal_id",
    "score_id",
    "edge_id",
    "hypothesis_id",
    "akber_result_id",
    "shadow_evidence_id",
    "risk_proposal_id",
)


def build_release_readiness(
    phase_status: dict[str, Any],
    lock: dict[str, Any],
    approvals: dict[str, Any],
    risk_policy: dict[str, Any],
    edge_summary: dict[str, Any],
    shadow_promotion: dict[str, Any],
    paperops: dict[str, Any],
    *,
    generated_at: str,
) -> dict[str, Any]:
    phases = phase_status.get("phases")
    phases = phases if isinstance(phases, dict) else {}
    phase_states = {
        phase: str(phases.get(phase, {}).get("state") or "missing")
        for phase in REQUIRED_PHASES_FOR_RELEASE
    }
    nonpassing = [phase for phase, state in phase_states.items() if state != "passed"]
    strategy_approved = approvals.get("strategy_version_approved") is True
    risk_policy_approved = approvals.get("risk_policy_version_approved") is True and approvals.get(
        "risk_policy_version"
    ) == risk_policy.get("policy_version")
    explicit_release_approved = approvals.get("research_lock_release_approved") is True
    lock_active = lock.get("status") == "active" or lock.get("paperops_watch_only_mode") is True
    lock_released = not lock_active and explicit_release_approved
    live_capital_disabled = (
        paperops.get("safety", {}).get("live_capital_enabled") is not True
        and paperops.get("live_capital_enabled") is not True
    )
    validated_edge_available = safe_float(edge_summary.get("validated_edge_count")) > 0
    forward_shadow_ready = shadow_promotion.get("promotion_ready") is True
    blockers: list[str] = []
    blockers.extend(f"phase_not_passed:{phase}:{phase_states[phase]}" for phase in nonpassing)
    if not validated_edge_available:
        blockers.append("no_validated_edge_available")
    if not forward_shadow_ready:
        blockers.append("forward_shadow_promotion_not_ready")
    if not strategy_approved:
        blockers.append("strategy_version_not_operator_approved")
    if not risk_policy_approved:
        blockers.append("risk_policy_version_not_operator_approved")
    if not explicit_release_approved:
        blockers.append("explicit_research_lock_release_not_approved")
    if lock_active:
        blockers.append("long_research_lock_active")
    if not live_capital_disabled:
        blockers.append("live_capital_safety_violation")
    recommendation_preconditions_pass = (
        not nonpassing
        and validated_edge_available
        and forward_shadow_ready
        and strategy_approved
        and risk_policy_approved
        and live_capital_disabled
    )
    release_recommended = recommendation_preconditions_pass
    release_effective = (
        recommendation_preconditions_pass and explicit_release_approved and not lock_active
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_research_lock_release_readiness",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": (
            "released_and_effective"
            if release_effective
            else ("release_recommended_operator_action_required" if release_recommended else "hold")
        ),
        "required_phase_states": phase_states,
        "nonpassing_phase_count": len(nonpassing),
        "nonpassing_phases": nonpassing,
        "all_or0_through_or14_passed": not nonpassing,
        "validated_edge_available": validated_edge_available,
        "forward_shadow_promotion_ready": forward_shadow_ready,
        "strategy_version_operator_approved": strategy_approved,
        "risk_policy_version_operator_approved": risk_policy_approved,
        "risk_policy_version": risk_policy.get("policy_version"),
        "explicit_research_lock_release_approved": explicit_release_approved,
        "research_lock_active": lock_active,
        "research_lock_released": lock_released,
        "live_capital_disabled": live_capital_disabled,
        "release_recommended": release_recommended,
        "release_performed": False,
        "release_effective": release_effective,
        "release_requires_explicit_operator_action": True,
        "self_healing_release_allowed": False,
        "automatic_lock_file_mutation_allowed": False,
        "blockers": unique_errors(blockers),
        "next_action": (
            "Operator may perform the separately audited lock-release action."
            if release_recommended and not release_effective
            else (
                "The explicitly released boundary is effective for clean paper-review candidates."
                if release_effective
                else "Keep PaperOps watch-only while evidence and approvals mature."
            )
        ),
        "authority": authority_flags(),
    }


def validate_release_readiness(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    states = record.get("required_phase_states")
    states = states if isinstance(states, dict) else {}
    all_passed = all(states.get(phase) == "passed" for phase in REQUIRED_PHASES_FOR_RELEASE)
    if record.get("all_or0_through_or14_passed") is not all_passed:
        errors.append("release_phase_summary_mismatch")
    if record.get("release_recommended") is True and not all_passed:
        errors.append("release_recommended_before_all_required_phases_passed")
    if record.get("release_recommended") is True:
        for field in (
            "validated_edge_available",
            "forward_shadow_promotion_ready",
            "strategy_version_operator_approved",
            "risk_policy_version_operator_approved",
            "live_capital_disabled",
        ):
            if record.get(field) is not True:
                errors.append(f"release_recommended_without_gate:{field}")
    if record.get("release_performed") is not False:
        errors.append("router_release_checker_performed_release")
    if record.get("self_healing_release_allowed") is not False:
        errors.append("self_healing_lock_release_allowed")
    if record.get("automatic_lock_file_mutation_allowed") is not False:
        errors.append("automatic_lock_mutation_allowed")
    errors.extend(validate_authority(record.get("authority", {}), prefix="release_readiness"))
    return unique_errors(errors)


def _idempotency_material(setup: dict[str, Any]) -> dict[str, Any]:
    lineage = setup.get("lineage") if isinstance(setup.get("lineage"), dict) else {}
    identity = str(setup.get("candidate_identity_id") or "")
    material = {
        "research_goal_id": lineage.get("research_goal_id"),
        "candidate_identity_id": identity,
        "edge_id": lineage.get("edge_id"),
        "hypothesis_id": lineage.get("hypothesis_id"),
        "instrument": setup.get("instrument"),
        "direction": setup.get("direction"),
        "horizon": setup.get("horizon"),
    }
    return {
        "idempotency_namespace": "qadam_router_v3_paper_review",
        "idempotency_key": stable_id("qadam-paper-review-v3", material),
        "identity_material": material,
        "distinct_setup_required": True,
        "idempotency_bypass_allowed": False,
        "not_broker_order_idempotency_key": True,
    }


def route_setup(
    setup: dict[str, Any],
    release_readiness: dict[str, Any],
    *,
    generated_at: str,
    duplicate_idempotency: bool = False,
) -> dict[str, Any]:
    setup_id = str(setup.get("setup_id") or "")
    if not setup_id:
        raise ValueError("router_setup_id_missing")
    lineage = setup.get("lineage") if isinstance(setup.get("lineage"), dict) else {}
    missing_lineage = [field for field in REQUIRED_LINEAGE_REFS if not lineage.get(field)]
    idempotency = _idempotency_material(setup)
    repair_reasons = [f"missing_lineage:{field}" for field in missing_lineage]
    hard_vetoes: list[str] = []
    hold_reasons: list[str] = []
    if setup.get("akber_decision") == "veto":
        hard_vetoes.append("akber_veto")
    if setup.get("expected_net_return_positive_after_costs") is not True:
        hard_vetoes.append("expected_return_not_positive_after_costs")
    if setup.get("source_quorum_passed") is not True:
        hold_reasons.append("source_quorum_not_passed")
    if setup.get("duplicate_exposure_conflict") is True:
        hard_vetoes.append("duplicate_exposure_conflict")
    if duplicate_idempotency:
        hard_vetoes.append("duplicate_idempotency_material")
    if setup.get("drawdown_context_complete") is not True:
        hold_reasons.append("drawdown_context_incomplete")
    elif setup.get("drawdown_breached") is True:
        hard_vetoes.append("drawdown_breach")
    if setup.get("qctrl_state") != "pass":
        hold_reasons.append("qctrl_consultation_hold")
    if setup.get("instrument_paperable") is not True:
        hard_vetoes.append("instrument_not_paperable")
    if setup.get("route") != "guarded_alpaca_paper_via_paperops":
        hard_vetoes.append("unguarded_or_unsupported_route")
    if (
        setup.get("market_family") == "prediction_market"
        and setup.get("separately_governed_prediction_market_paper_route") is not True
    ):
        hard_vetoes.append("prediction_market_context_only")
    if setup.get("risk_proposal_complete") is not True:
        hold_reasons.append("risk_proposal_incomplete")
    if setup.get("akber_decision") != "pass":
        hold_reasons.append("akber_pass_missing")
    if setup.get("shadow_promotion_ready") is not True:
        hold_reasons.append("forward_shadow_not_promoted")
    if setup.get("strategy_version_operator_approved") is not True:
        hold_reasons.append("strategy_version_not_approved")
    if setup.get("risk_policy_operator_approved") is not True:
        hold_reasons.append("risk_policy_not_approved")

    if repair_reasons:
        final_state = "repair-requested"
        final_reason = "Required evidence lineage is incomplete."
    elif release_readiness.get("release_effective") is not True:
        final_state = "blocked-safety-boundary"
        final_reason = "The research lock remains active or release prerequisites are incomplete."
    elif hard_vetoes:
        final_state = "reject"
        final_reason = "A hard safety or tradeability veto rejected the setup."
    elif setup.get("edge_promotion_class") == "exploratory_research_edge":
        final_state = "shadow-only"
        final_reason = "Exploratory evidence may be observed only in shadow mode."
    elif setup.get("fresh_catalyst_state") == "watching":
        final_state = "watchlist"
        final_reason = "The edge is valid, but the current catalyst has not activated."
    elif hold_reasons:
        final_state = "hold"
        final_reason = "Current confirmation or risk context is incomplete."
    else:
        final_state = "paper-review-candidate"
        final_reason = "Every research, safety, risk, and guarded paper-route gate passed."
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_router_v3_decision",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "router_decision_id": stable_id("router-decision-v3", setup_id, final_state),
        "setup_id": setup_id,
        "candidate_identity_id": setup.get("candidate_identity_id"),
        "lineage": lineage,
        "instrument": setup.get("instrument"),
        "market_family": setup.get("market_family"),
        "direction": setup.get("direction"),
        "horizon": setup.get("horizon"),
        "final_state": final_state,
        "exactly_one_final_state": final_state in FINAL_STATES,
        "final_reason": final_reason,
        "repair_reasons": unique_errors(repair_reasons),
        "hard_vetoes": unique_errors(hard_vetoes),
        "hold_reasons": unique_errors(hold_reasons),
        "gate_snapshot": {
            "source_quorum_passed": setup.get("source_quorum_passed") is True,
            "duplicate_exposure_conflict": setup.get("duplicate_exposure_conflict") is True,
            "drawdown_context_complete": setup.get("drawdown_context_complete") is True,
            "drawdown_breached": setup.get("drawdown_breached") is True,
            "qctrl_state": setup.get("qctrl_state"),
            "instrument_paperable": setup.get("instrument_paperable") is True,
            "route": setup.get("route"),
            "shadow_promotion_ready": setup.get("shadow_promotion_ready") is True,
            "risk_proposal_complete": setup.get("risk_proposal_complete") is True,
            "research_lock_release_effective": release_readiness.get("release_effective") is True,
        },
        "idempotency_material": idempotency,
        "paperops_handoff_allowed": final_state == "paper-review-candidate",
        "paper_review_candidate_is_not_order": True,
        "qualified_setup_created": False,
        "risk_approval_created": False,
        "execution_approval_created": False,
        "paper_order_created": False,
        "proof_credit_allowed": False,
        "authority": authority_flags(),
    }


def build_handoff(decision: dict[str, Any], setup: dict[str, Any]) -> dict[str, Any]:
    if decision.get("final_state") != "paper-review-candidate":
        raise ValueError("router_decision_not_paper_review_candidate")
    route = decision.get("gate_snapshot", {}).get("route")
    if route != "guarded_alpaca_paper_via_paperops":
        raise ValueError("paperops_handoff_route_not_guarded_alpaca_paper")
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_paperops_handoff_v3",
        "phase_id": PHASE_ID,
        "generated_at": decision.get("generated_at"),
        "paperops_handoff_id": stable_id(
            "paperops-handoff-v3",
            decision.get("router_decision_id"),
            decision.get("idempotency_material", {}).get("idempotency_key"),
        ),
        "router_decision_id": decision.get("router_decision_id"),
        "setup_id": decision.get("setup_id"),
        "candidate_identity_id": decision.get("candidate_identity_id"),
        "lineage": decision.get("lineage"),
        "instrument": decision.get("instrument"),
        "market_family": decision.get("market_family"),
        "strategy_family_id": setup.get("strategy_family_id"),
        "direction": decision.get("direction"),
        "horizon": decision.get("horizon"),
        "proposed_quantity": setup.get("proposed_quantity"),
        "proposed_notional_usd": setup.get("proposed_notional_usd"),
        "notional_currency": "USD",
        "maximum_loss_at_invalidation": setup.get("maximum_loss_at_invalidation"),
        "risk_policy_version": setup.get("risk_policy_version"),
        "idempotency_material": decision.get("idempotency_material"),
        "source_quorum": setup.get("source_quorum"),
        "source_quorum_passed": setup.get("source_quorum_passed") is True,
        "duplicate_exposure_conflict": False,
        "drawdown_context_complete": setup.get("drawdown_context_complete") is True,
        "drawdown_breached": False,
        "qctrl_state": "pass",
        "instrument_paperable": setup.get("instrument_paperable") is True,
        "route": route,
        "canonical_unattended_wrapper": (
            ".venv/bin/python scripts/run_paperops_autonomous_pass.py"
        ),
        "paperops_handoff_is_not_order": True,
        "paperops_direct_call_allowed": False,
        "supplemental_source_bypass_allowed": False,
        "paper_order_created": False,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
        "authority": authority_flags(),
    }


def _open_exposure_symbols(
    positions: list[dict[str, Any]], orders: list[dict[str, Any]]
) -> set[str]:
    symbols = {
        str(record.get("instrument") or record.get("symbol") or "").upper()
        for record in positions
        if safe_float(record.get("quantity") or record.get("qty")) != 0
    }
    symbols.update(
        str(record.get("instrument") or record.get("symbol") or "").upper()
        for record in orders
        if str(record.get("status") or "").lower() in OPEN_EXPOSURE_STATES
    )
    return {symbol for symbol in symbols if symbol}


def _assemble_setup(
    hypothesis: dict[str, Any],
    *,
    edge: dict[str, Any],
    score: dict[str, Any],
    akber: dict[str, Any],
    shadow_decision: dict[str, Any],
    shadow_outcome: dict[str, Any],
    shadow_promotion: dict[str, Any],
    risk_proposal: dict[str, Any],
    risk_state: dict[str, Any],
    qctrl: dict[str, Any],
    approvals: dict[str, Any],
    open_symbols: set[str],
) -> dict[str, Any]:
    mapping = hypothesis.get("instrument_proxy_mapping", {})
    instrument = str(mapping.get("execution_proxy") or "")
    direction_horizon = hypothesis.get("direction_horizon", {})
    source_quorum = hypothesis.get("source_quorum")
    source_quorum = source_quorum if isinstance(source_quorum, dict) else {}
    qctrl_recommendation = qctrl.get("head_of_quant_note", {}).get("latest_oracle_recommendation")
    qctrl_state = (
        "pass"
        if qctrl.get("status") == "consultation_recorded"
        and qctrl_recommendation not in {"hold", "veto"}
        else "hold"
    )
    risk_policy_version = risk_proposal.get("policy_version")
    return {
        "setup_id": stable_id("router-setup-v3", hypothesis.get("hypothesis_id")),
        "candidate_identity_id": hypothesis.get("candidate_identity_material", {}).get(
            "candidate_identity_id"
        ),
        "lineage": {
            "research_goal_id": hypothesis.get("research_goal_lineage", {}).get("research_goal_id"),
            "score_id": edge.get("score_id") or score.get("score_id"),
            "edge_id": hypothesis.get("edge_lineage", {}).get("edge_id"),
            "hypothesis_id": hypothesis.get("hypothesis_id"),
            "akber_result_id": akber.get("akber_result_id"),
            "shadow_evidence_id": shadow_outcome.get("outcome_id")
            or shadow_decision.get("decision_id"),
            "risk_proposal_id": risk_proposal.get("proposal_id"),
            "applied_learning_version_ids": hypothesis.get("edge_lineage", {}).get(
                "applied_learning_version_ids", score.get("applied_learning_version_ids", [])
            ),
            "stage1_learning_input_version": hypothesis.get("edge_lineage", {}).get(
                "stage1_learning_input_version", score.get("stage1_learning_input_version")
            ),
        },
        "instrument": instrument,
        "market_family": edge.get("market_family") or score.get("market_family"),
        "direction": direction_horizon.get("direction"),
        "horizon": direction_horizon.get("horizon"),
        "edge_promotion_class": hypothesis.get("edge_lineage", {}).get("promotion_class"),
        "fresh_catalyst_state": "confirmed" if akber.get("decision") == "pass" else "watching",
        "akber_decision": akber.get("decision"),
        "source_quorum": source_quorum,
        "source_quorum_passed": source_quorum.get("passed") is True,
        "expected_net_return_positive_after_costs": safe_float(
            risk_proposal.get("expected_net_return"), 0.0
        )
        > 0,
        "shadow_promotion_ready": shadow_promotion.get("promotion_ready") is True,
        "risk_proposal_complete": bool(
            risk_proposal.get("proposal_id")
            and safe_float(risk_proposal.get("proposed_quantity")) > 0
            and risk_proposal.get("risk_approval_created") is False
        ),
        "proposed_quantity": risk_proposal.get("proposed_quantity"),
        "proposed_notional_usd": risk_proposal.get("proposed_notional"),
        "maximum_loss_at_invalidation": risk_proposal.get("maximum_loss_at_invalidation"),
        "risk_policy_version": risk_proposal.get("policy_version"),
        "strategy_family_id": hypothesis.get("strategy_mapping", {}).get("strategy_family_id"),
        "duplicate_exposure_conflict": instrument.upper() in open_symbols if instrument else True,
        "drawdown_context_complete": risk_state.get("drawdown_context_complete") is True,
        "drawdown_breached": (
            safe_float(risk_state.get("daily_loss_pct"), 1.0) >= 0.02
            or safe_float(risk_state.get("trailing_drawdown_pct"), 1.0) >= 0.08
        ),
        "qctrl_state": qctrl_state,
        "instrument_paperable": hypothesis.get("paperability", {}).get("execution_proxy")
        is not None,
        "route": "guarded_alpaca_paper_via_paperops",
        "separately_governed_prediction_market_paper_route": False,
        "strategy_version_operator_approved": approvals.get("strategy_version_approved") is True,
        "risk_policy_operator_approved": (
            approvals.get("risk_policy_version_approved") is True
            and approvals.get("risk_policy_version") == risk_policy_version
        ),
    }


def build_router_v3_state(
    settings: Settings | None = None,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    generated = generated_at or now_iso()
    phase_status = read_json(runtime / PHASE_STATUS_ARTIFACT)
    lock = read_json(runtime / LOCK_ARTIFACT)
    approvals = read_json(runtime / OPERATOR_APPROVALS_ARTIFACT)
    risk_policy = read_json(runtime / RISK_POLICY_ARTIFACT)
    edge_summary = read_json(runtime / EDGE_SUMMARY_ARTIFACT)
    shadow_promotion = read_json(runtime / SHADOW_PROMOTION_ARTIFACT)
    paperops = read_json(runtime / PAPEROPS_SUMMARY_ARTIFACT)
    release = build_release_readiness(
        phase_status,
        lock,
        approvals,
        risk_policy,
        edge_summary,
        shadow_promotion,
        paperops,
        generated_at=generated,
    )
    hypotheses = read_jsonl(runtime / STRATEGY_HYPOTHESES_ARTIFACT)
    scores = read_jsonl(runtime / PATTERN_SCORES_ARTIFACT)
    edges = read_jsonl(runtime / EDGE_REGISTRY_ARTIFACT)
    akber_results = read_jsonl(runtime / AKBER_RESULTS_ARTIFACT)
    shadow_decisions = read_jsonl(runtime / SHADOW_DECISIONS_ARTIFACT)
    shadow_outcomes = read_jsonl(runtime / SHADOW_OUTCOMES_ARTIFACT)
    risk_proposals = read_jsonl(runtime / RISK_PROPOSALS_ARTIFACT)
    risk_state = read_json(runtime / RISK_STATE_ARTIFACT)
    qctrl = read_json(runtime / QCTRL_ARTIFACT)
    positions = read_jsonl(runtime / PAPER_POSITIONS_ARTIFACT)
    orders = read_jsonl(runtime / PAPER_ORDERS_ARTIFACT)
    open_symbols = _open_exposure_symbols(positions, orders)
    score_by_id = {
        str(record.get("score_id")): record for record in scores if record.get("score_id")
    }
    edge_by_id = {str(record.get("edge_id")): record for record in edges if record.get("edge_id")}
    akber_by_hypothesis = {
        str(record.get("hypothesis_id")): record
        for record in akber_results
        if record.get("hypothesis_id")
    }
    shadow_decision_by_hypothesis = {
        str(record.get("hypothesis_id")): record
        for record in shadow_decisions
        if record.get("hypothesis_id")
    }
    shadow_outcome_by_hypothesis = {
        str(record.get("hypothesis_id")): record
        for record in shadow_outcomes
        if record.get("hypothesis_id")
    }
    risk_by_hypothesis = {
        str(record.get("hypothesis_id")): record
        for record in risk_proposals
        if record.get("hypothesis_id")
    }
    setups: list[dict[str, Any]] = []
    for hypothesis in hypotheses:
        hypothesis_id = str(hypothesis.get("hypothesis_id") or "")
        edge_id = str(hypothesis.get("edge_lineage", {}).get("edge_id") or "")
        edge = edge_by_id.get(edge_id, {})
        score = score_by_id.get(str(edge.get("score_id") or ""), {})
        setups.append(
            _assemble_setup(
                hypothesis,
                edge=edge,
                score=score,
                akber=akber_by_hypothesis.get(hypothesis_id, {}),
                shadow_decision=shadow_decision_by_hypothesis.get(hypothesis_id, {}),
                shadow_outcome=shadow_outcome_by_hypothesis.get(hypothesis_id, {}),
                shadow_promotion=shadow_promotion,
                risk_proposal=risk_by_hypothesis.get(hypothesis_id, {}),
                risk_state=risk_state,
                qctrl=qctrl,
                approvals=approvals,
                open_symbols=open_symbols,
            )
        )
    idempotency_keys = [_idempotency_material(setup)["idempotency_key"] for setup in setups]
    duplicate_keys = {key for key, count in Counter(idempotency_keys).items() if count > 1}
    decisions = [
        route_setup(
            setup,
            release,
            generated_at=generated,
            duplicate_idempotency=(
                _idempotency_material(setup)["idempotency_key"] in duplicate_keys
            ),
        )
        for setup in setups
    ]
    setup_by_id = {str(setup["setup_id"]): setup for setup in setups}
    handoffs = [
        build_handoff(decision, setup_by_id[str(decision["setup_id"])])
        for decision in decisions
        if decision.get("final_state") == "paper-review-candidate"
    ]
    state_counts = Counter(record.get("final_state") for record in decisions)
    scoreboard = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_router_v3_scoreboard",
        "phase_id": PHASE_ID,
        "generated_at": generated,
        "status": "router_ready" if setups else "router_ready_no_setups",
        "setup_count": len(setups),
        "decision_count": len(decisions),
        "state_counts": dict(sorted(state_counts.items(), key=lambda item: str(item[0]))),
        "paper_review_candidate_count": state_counts.get("paper-review-candidate", 0),
        "handoff_count": len(handoffs),
        "duplicate_idempotency_count": len(duplicate_keys),
        "open_exposure_symbol_count": len(open_symbols),
        "multiple_paper_trades_per_day_policy": (
            "allowed_only_for_distinct_lineage_identity_and_idempotency_material_after_all_gates"
        ),
        "prediction_market_default": "context_only_without_separately_governed_paper_route",
        "legacy_v2_decision_consumed_count": 0,
        "qualified_setup_created_count": 0,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "authority": authority_flags(),
    }
    why_not = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_router_v3_why_not_trading_now",
        "phase_id": PHASE_ID,
        "generated_at": generated,
        "status": "paper_review_candidate_available" if handoffs else "not_trading",
        "primary_reason": (
            "A clean paper-review candidate is available to the existing guarded PaperOps chain."
            if handoffs
            else (
                "No validated edge-backed setup exists yet."
                if not setups
                else decisions[0].get("final_reason")
            )
        ),
        "current_router_state": (
            "paper-review-candidate"
            if handoffs
            else (decisions[0].get("final_state") if decisions else "no-setup")
        ),
        "release_blockers": release.get("blockers", []),
        "setup_count": len(setups),
        "handoff_count": len(handoffs),
        "paperops_watch_only": lock.get("paperops_watch_only_mode") is True,
        "paper_order_created_count": 0,
        "authority": authority_flags(),
    }
    return {
        "release": release,
        "setups": setups,
        "decisions": decisions,
        "handoffs": handoffs,
        "scoreboard": scoreboard,
        "why_not": why_not,
    }


def validate_router_v3_state(state: dict[str, Any]) -> list[str]:
    errors = validate_release_readiness(state["release"])
    decisions = state["decisions"]
    handoffs = state["handoffs"]
    setup_count = len(state["setups"])
    if len(decisions) != setup_count:
        errors.append("router_setup_decision_count_mismatch")
    decision_ids: set[str] = set()
    idempotency_keys: list[str] = []
    for decision in decisions:
        decision_id = str(decision.get("router_decision_id") or "")
        if not decision_id or decision_id in decision_ids:
            errors.append("router_decision_id_missing_or_duplicate")
        decision_ids.add(decision_id)
        if decision.get("final_state") not in FINAL_STATES:
            errors.append(f"router_final_state_invalid:{decision_id}")
        if decision.get("exactly_one_final_state") is not True:
            errors.append(f"router_final_state_not_exactly_one:{decision_id}")
        if (
            decision.get("paperops_handoff_allowed") is True
            and decision.get("final_state") != "paper-review-candidate"
        ):
            errors.append(f"router_handoff_allowed_for_non_candidate:{decision_id}")
        if decision.get("paper_order_created") is not False:
            errors.append(f"router_created_paper_order:{decision_id}")
        key = decision.get("idempotency_material", {}).get("idempotency_key")
        if key:
            idempotency_keys.append(str(key))
        errors.extend(validate_authority(decision.get("authority", {}), prefix="router_decision"))
    candidate_ids = {
        record.get("router_decision_id")
        for record in decisions
        if record.get("final_state") == "paper-review-candidate"
    }
    if len(handoffs) != len(candidate_ids):
        errors.append("router_candidate_handoff_count_mismatch")
    handoff_keys: set[str] = set()
    for handoff in handoffs:
        if handoff.get("router_decision_id") not in candidate_ids:
            errors.append("paperops_handoff_without_candidate_decision")
        if handoff.get("route") != "guarded_alpaca_paper_via_paperops":
            errors.append("paperops_handoff_unguarded_route")
        if handoff.get("market_family") == "prediction_market":
            errors.append("prediction_market_handoff_without_separate_route")
        if handoff.get("paperops_handoff_is_not_order") is not True:
            errors.append("paperops_handoff_order_boundary_missing")
        if handoff.get("paper_order_created") is not False:
            errors.append("paperops_handoff_created_order")
        key = handoff.get("idempotency_material", {}).get("idempotency_key")
        if not key or key in handoff_keys:
            errors.append("paperops_handoff_idempotency_missing_or_duplicate")
        handoff_keys.add(str(key))
        errors.extend(validate_authority(handoff.get("authority", {}), prefix="paperops_handoff"))
    if len(idempotency_keys) != len(set(idempotency_keys)) and handoffs:
        errors.append("duplicate_router_idempotency_reached_handoff")
    scoreboard = state["scoreboard"]
    if scoreboard.get("legacy_v2_decision_consumed_count") != 0:
        errors.append("router_v3_consumed_legacy_v2_decisions")
    for field in (
        "qualified_setup_created_count",
        "paper_order_created_count",
        "broker_write_count",
    ):
        if scoreboard.get(field) != 0:
            errors.append(f"router_forbidden_count_nonzero:{field}")
    errors.extend(validate_authority(scoreboard.get("authority", {}), prefix="router_scoreboard"))
    errors.extend(
        validate_authority(state["why_not"].get("authority", {}), prefix="router_why_not")
    )
    return unique_errors(errors)


def _parse_utc_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _handoff_consumption_errors(
    handoff: dict[str, Any],
    decision: dict[str, Any],
    release: dict[str, Any],
    lock: dict[str, Any],
    *,
    generated_at: str,
    duplicate_handoff_id: bool,
    duplicate_idempotency_key: bool,
    submitted_idempotency_keys: set[str],
) -> list[str]:
    errors: list[str] = []
    if handoff.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if handoff.get("artifact_type") != "qadam_paperops_handoff_v3":
        errors.append("artifact_type_invalid")
    for field in (
        "paperops_handoff_id",
        "router_decision_id",
        "setup_id",
        "candidate_identity_id",
        "instrument",
        "direction",
    ):
        if not str(handoff.get(field) or "").strip():
            errors.append(f"required_field_missing:{field}")
    if duplicate_handoff_id:
        errors.append("duplicate_handoff_id_in_batch")
    lineage = handoff.get("lineage")
    lineage = lineage if isinstance(lineage, dict) else {}
    for field in REQUIRED_LINEAGE_REFS:
        if not str(lineage.get(field) or "").strip():
            errors.append(f"lineage_missing:{field}")
    idempotency = handoff.get("idempotency_material")
    idempotency = idempotency if isinstance(idempotency, dict) else {}
    idempotency_key = str(idempotency.get("idempotency_key") or "")
    if not idempotency_key:
        errors.append("idempotency_key_missing")
    if idempotency.get("idempotency_bypass_allowed") is not False:
        errors.append("idempotency_bypass_not_disabled")
    if duplicate_idempotency_key:
        errors.append("duplicate_idempotency_key_in_batch")
    if idempotency_key and idempotency_key in submitted_idempotency_keys:
        errors.append("idempotency_key_already_submitted")
    generated = _parse_utc_timestamp(generated_at)
    observed = _parse_utc_timestamp(handoff.get("generated_at"))
    if generated is None or observed is None:
        errors.append("handoff_timestamp_invalid")
    else:
        age_seconds = (generated - observed).total_seconds()
        if age_seconds < -HANDOFF_FUTURE_TOLERANCE_SECONDS:
            errors.append("handoff_timestamp_in_future")
        if age_seconds > HANDOFF_MAXIMUM_AGE_SECONDS:
            errors.append("handoff_stale")
    if not decision:
        errors.append("router_decision_missing")
    else:
        if decision.get("final_state") != "paper-review-candidate":
            errors.append("router_decision_not_paper_review_candidate")
        if decision.get("paperops_handoff_allowed") is not True:
            errors.append("router_decision_handoff_not_allowed")
        if decision.get("router_decision_id") != handoff.get("router_decision_id"):
            errors.append("router_decision_id_mismatch")
        if decision.get("setup_id") != handoff.get("setup_id"):
            errors.append("router_setup_id_mismatch")
        if decision.get("candidate_identity_id") != handoff.get("candidate_identity_id"):
            errors.append("router_candidate_identity_mismatch")
        if decision.get("lineage") != lineage:
            errors.append("router_lineage_mismatch")
        decision_key = decision.get("idempotency_material", {}).get("idempotency_key")
        if decision_key != idempotency_key:
            errors.append("router_idempotency_mismatch")
    if release.get("release_effective") is not True:
        errors.append("research_release_not_effective")
    if lock.get("status") == "active" or lock.get("paperops_watch_only_mode") is True:
        errors.append("research_lock_active")
    if handoff.get("source_quorum_passed") is not True:
        errors.append("source_quorum_not_passed")
    source_quorum = handoff.get("source_quorum")
    source_quorum = source_quorum if isinstance(source_quorum, dict) else {}
    if source_quorum.get("passed") is not True:
        errors.append("source_quorum_record_not_passed")
    if handoff.get("duplicate_exposure_conflict") is not False:
        errors.append("duplicate_exposure_conflict")
    if handoff.get("drawdown_context_complete") is not True:
        errors.append("drawdown_context_incomplete")
    if handoff.get("drawdown_breached") is not False:
        errors.append("drawdown_breach")
    if handoff.get("qctrl_state") != "pass":
        errors.append("qctrl_not_clear")
    if handoff.get("instrument_paperable") is not True:
        errors.append("instrument_not_paperable")
    if handoff.get("route") != "guarded_alpaca_paper_via_paperops":
        errors.append("route_not_guarded_alpaca_paper")
    if handoff.get("market_family") == "prediction_market":
        errors.append("prediction_market_context_only")
    quantity = safe_float(handoff.get("proposed_quantity"), 0.0)
    notional = safe_float(handoff.get("proposed_notional_usd"), 0.0)
    maximum_loss = safe_float(handoff.get("maximum_loss_at_invalidation"), 0.0)
    if quantity <= 0:
        errors.append("proposed_quantity_not_positive")
    if notional <= 0:
        errors.append("proposed_notional_not_positive")
    elif notional > ABSOLUTE_PAPER_TRADE_CEILING_USD:
        errors.append("proposed_notional_above_absolute_ceiling")
    if maximum_loss <= 0:
        errors.append("maximum_loss_at_invalidation_not_positive")
    if handoff.get("notional_currency") != "USD":
        errors.append("notional_currency_not_usd")
    for field, safe_value in (
        ("paperops_handoff_is_not_order", True),
        ("paperops_direct_call_allowed", False),
        ("paper_order_created", False),
        ("live_capital_enabled", False),
        ("proof_credit_allowed", False),
    ):
        if handoff.get(field) is not safe_value:
            errors.append(f"unsafe_handoff_field:{field}")
    if int(handoff.get("broker_write_count") or 0) != 0:
        errors.append("unsafe_handoff_field:broker_write_count")
    errors.extend(validate_authority(handoff.get("authority", {}), prefix="handoff_consumer"))
    return unique_errors(errors)


def build_handoff_consumption_state(
    handoffs: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    release: dict[str, Any],
    lock: dict[str, Any],
    *,
    generated_at: str,
    submitted_idempotency_keys: set[str] | None = None,
) -> dict[str, Any]:
    submitted_keys = submitted_idempotency_keys or set()
    decision_by_id = {
        str(record.get("router_decision_id")): record
        for record in decisions
        if record.get("router_decision_id")
    }
    handoff_id_counts = Counter(str(record.get("paperops_handoff_id") or "") for record in handoffs)
    key_counts = Counter(
        str(record.get("idempotency_material", {}).get("idempotency_key") or "")
        for record in handoffs
    )
    receipts: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []
    for handoff_index, handoff in enumerate(handoffs):
        handoff_id = str(handoff.get("paperops_handoff_id") or "")
        router_decision_id = str(handoff.get("router_decision_id") or "")
        idempotency_key = str(handoff.get("idempotency_material", {}).get("idempotency_key") or "")
        handoff_hash = sha256_json(handoff)
        reasons = _handoff_consumption_errors(
            handoff,
            decision_by_id.get(router_decision_id, {}),
            release,
            lock,
            generated_at=generated_at,
            duplicate_handoff_id=bool(handoff_id and handoff_id_counts[handoff_id] > 1),
            duplicate_idempotency_key=bool(idempotency_key and key_counts[idempotency_key] > 1),
            submitted_idempotency_keys=submitted_keys,
        )
        accepted_for_sequence = not reasons
        receipt_id = stable_id(
            "paperops-handoff-v3-consumption-receipt",
            handoff_id or handoff_hash,
            handoff_hash,
            handoff_index,
        )
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_paperops_handoff_v3_consumption_receipt",
            "phase_id": PHASE_ID,
            "generated_at": generated_at,
            "consumption_receipt_id": receipt_id,
            "paperops_handoff_id": handoff_id or None,
            "router_decision_id": router_decision_id or None,
            "source_handoff_sha256": handoff_hash,
            "idempotency_key": idempotency_key or None,
            "status": (
                "accepted_for_guarded_paperops_sequence"
                if accepted_for_sequence
                else "rejected_before_guarded_paperops_sequence"
            ),
            "accepted": accepted_for_sequence,
            "rejection_reasons": reasons,
            "canonical_wrapper": ".venv/bin/python scripts/run_paperops_autonomous_pass.py",
            "handoff_is_not_order": True,
            "paper_order_created": False,
            "broker_write_count": 0,
            "live_capital_enabled": False,
            "proof_credit_allowed": False,
            "authority": authority_flags(),
        }
        receipts.append(receipt)
        if accepted_for_sequence:
            accepted.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "artifact_type": "qadam_paperops_handoff_v3_accepted",
                    "phase_id": PHASE_ID,
                    "generated_at": generated_at,
                    "consumption_receipt_id": receipt_id,
                    "source_handoff_sha256": handoff_hash,
                    "source_handoff": handoff,
                    "paper_order_created": False,
                    "broker_write_count": 0,
                    "proof_credit_allowed": False,
                    "authority": authority_flags(),
                }
            )
        else:
            rejections.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "artifact_type": "qadam_paperops_handoff_v3_rejection",
                    "phase_id": PHASE_ID,
                    "generated_at": generated_at,
                    "consumption_receipt_id": receipt_id,
                    "paperops_handoff_id": handoff_id or None,
                    "router_decision_id": router_decision_id or None,
                    "source_handoff_sha256": handoff_hash,
                    "rejection_reasons": reasons,
                    "paper_order_created": False,
                    "broker_write_count": 0,
                    "proof_credit_allowed": False,
                    "authority": authority_flags(),
                }
            )
    sequence_allowed = bool(accepted) and not rejections
    state = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_paperops_handoff_v3_consumer_state",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": (
            "accepted_for_guarded_paperops_sequence"
            if sequence_allowed
            else "ready_no_handoffs"
            if not handoffs
            else "blocked_handoff_rejected"
        ),
        "enforcement_active": True,
        "canonical_wrapper_only": True,
        "handoff_count": len(handoffs),
        "receipt_count": len(receipts),
        "accepted_handoff_count": len(accepted),
        "rejected_handoff_count": len(rejections),
        "accepted_handoff_ids": [
            record["source_handoff"].get("paperops_handoff_id") for record in accepted
        ],
        "guarded_paperops_command_sequence_allowed": sequence_allowed,
        "new_paper_submission_allowed": sequence_allowed,
        "maximum_handoff_age_seconds": HANDOFF_MAXIMUM_AGE_SECONDS,
        "absolute_paper_trade_ceiling_usd": ABSOLUTE_PAPER_TRADE_CEILING_USD,
        "research_lock_active": lock.get("status") == "active"
        or lock.get("paperops_watch_only_mode") is True,
        "release_effective": release.get("release_effective") is True,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
        "receipts": receipts,
        "accepted_handoffs": accepted,
        "rejections": rejections,
        "authority": authority_flags(),
    }
    return state


def validate_handoff_consumption_state(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    receipts = state.get("receipts") if isinstance(state.get("receipts"), list) else []
    accepted = (
        state.get("accepted_handoffs") if isinstance(state.get("accepted_handoffs"), list) else []
    )
    rejections = state.get("rejections") if isinstance(state.get("rejections"), list) else []
    if state.get("enforcement_active") is not True:
        errors.append("handoff_consumer_enforcement_not_active")
    if state.get("canonical_wrapper_only") is not True:
        errors.append("handoff_consumer_alternate_route_allowed")
    if int(state.get("receipt_count") or 0) != int(state.get("handoff_count") or 0):
        errors.append("handoff_consumer_receipt_count_mismatch")
    if len(receipts) != int(state.get("receipt_count") or 0):
        errors.append("handoff_consumer_receipt_records_mismatch")
    if len(accepted) != int(state.get("accepted_handoff_count") or 0):
        errors.append("handoff_consumer_accepted_count_mismatch")
    if len(rejections) != int(state.get("rejected_handoff_count") or 0):
        errors.append("handoff_consumer_rejected_count_mismatch")
    expected_allowed = bool(accepted) and not rejections
    if state.get("guarded_paperops_command_sequence_allowed") is not expected_allowed:
        errors.append("handoff_consumer_sequence_gate_mismatch")
    if state.get("new_paper_submission_allowed") is not expected_allowed:
        errors.append("handoff_consumer_submission_gate_mismatch")
    receipt_ids: set[str] = set()
    for receipt in receipts:
        receipt_id = str(receipt.get("consumption_receipt_id") or "")
        if not receipt_id or receipt_id in receipt_ids:
            errors.append("handoff_consumer_receipt_id_missing_or_duplicate")
        receipt_ids.add(receipt_id)
        if receipt.get("accepted") is True and receipt.get("rejection_reasons"):
            errors.append(f"handoff_consumer_accepted_receipt_has_reasons:{receipt_id}")
        if receipt.get("accepted") is not True and not receipt.get("rejection_reasons"):
            errors.append(f"handoff_consumer_rejected_receipt_missing_reason:{receipt_id}")
        errors.extend(validate_authority(receipt.get("authority", {}), prefix="handoff_receipt"))
    for record in accepted:
        source = record.get("source_handoff")
        source = source if isinstance(source, dict) else {}
        if record.get("source_handoff_sha256") != sha256_json(source):
            errors.append("handoff_consumer_accepted_hash_mismatch")
        if record.get("consumption_receipt_id") not in receipt_ids:
            errors.append("handoff_consumer_accepted_receipt_missing")
        errors.extend(validate_authority(record.get("authority", {}), prefix="accepted_handoff"))
    for record in rejections:
        if record.get("consumption_receipt_id") not in receipt_ids:
            errors.append("handoff_consumer_rejection_receipt_missing")
        errors.extend(validate_authority(record.get("authority", {}), prefix="rejected_handoff"))
    for field in ("paper_order_created_count", "broker_write_count"):
        if int(state.get(field) or 0) != 0:
            errors.append(f"handoff_consumer_forbidden_count_nonzero:{field}")
    if state.get("live_capital_enabled") is not False:
        errors.append("handoff_consumer_live_capital_enabled")
    if state.get("proof_credit_allowed") is not False:
        errors.append("handoff_consumer_proof_credit_allowed")
    errors.extend(validate_authority(state.get("authority", {}), prefix="handoff_consumer_state"))
    return unique_errors(errors)


def validate_handoff_consumer_negative_probes() -> list[str]:
    generated = now_iso()
    setup = {
        "setup_id": "setup:negative-probe",
        "candidate_identity_id": "candidate:negative-probe",
        "lineage": {field: f"{field}:negative-probe" for field in REQUIRED_LINEAGE_REFS},
        "instrument": "SPY",
        "market_family": "equity",
        "strategy_family_id": "strategy:negative-probe",
        "direction": "long",
        "horizon": "3d_forward",
        "edge_promotion_class": "validated_research_edge",
        "fresh_catalyst_state": "confirmed",
        "akber_decision": "pass",
        "source_quorum": {"passed": True, "independent_source_count": 3},
        "source_quorum_passed": True,
        "expected_net_return_positive_after_costs": True,
        "shadow_promotion_ready": True,
        "risk_proposal_complete": True,
        "proposed_quantity": 1,
        "proposed_notional_usd": 500.0,
        "maximum_loss_at_invalidation": 25.0,
        "risk_policy_version": "policy:negative-probe",
        "duplicate_exposure_conflict": False,
        "drawdown_context_complete": True,
        "drawdown_breached": False,
        "qctrl_state": "pass",
        "instrument_paperable": True,
        "route": "guarded_alpaca_paper_via_paperops",
        "separately_governed_prediction_market_paper_route": False,
        "strategy_version_operator_approved": True,
        "risk_policy_operator_approved": True,
    }
    release = {"release_effective": True}
    decision = route_setup(setup, release, generated_at=generated)
    handoff = build_handoff(decision, setup)
    failures: list[str] = []

    locked = build_handoff_consumption_state(
        [handoff],
        [decision],
        release,
        {"status": "active", "paperops_watch_only_mode": True},
        generated_at=generated,
    )
    if locked.get("accepted_handoff_count") != 0 or not any(
        "research_lock_active" in record.get("rejection_reasons", [])
        for record in locked.get("rejections", [])
    ):
        failures.append("negative_probe_failed:research_lock")

    live_route = dict(handoff)
    live_route["route"] = "alpaca_live"
    live = build_handoff_consumption_state(
        [live_route],
        [decision],
        release,
        {"status": "released", "paperops_watch_only_mode": False},
        generated_at=generated,
    )
    if live.get("accepted_handoff_count") != 0:
        failures.append("negative_probe_failed:live_route")

    unsafe = dict(handoff)
    unsafe["paper_order_created"] = True
    unsafe_state = build_handoff_consumption_state(
        [unsafe],
        [decision],
        release,
        {"status": "released", "paperops_watch_only_mode": False},
        generated_at=generated,
    )
    if unsafe_state.get("accepted_handoff_count") != 0:
        failures.append("negative_probe_failed:precreated_order")

    duplicate = build_handoff_consumption_state(
        [handoff, handoff],
        [decision],
        release,
        {"status": "released", "paperops_watch_only_mode": False},
        generated_at=generated,
    )
    if duplicate.get("accepted_handoff_count") != 0:
        failures.append("negative_probe_failed:duplicate_idempotency")

    submitted = build_handoff_consumption_state(
        [handoff],
        [decision],
        release,
        {"status": "released", "paperops_watch_only_mode": False},
        generated_at=generated,
        submitted_idempotency_keys={
            str(handoff.get("idempotency_material", {}).get("idempotency_key"))
        },
    )
    if submitted.get("accepted_handoff_count") != 0:
        failures.append("negative_probe_failed:submitted_idempotency")
    return unique_errors(failures)


def build_and_write_handoff_consumption(
    settings: Settings | None = None,
    *,
    router_state: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    generated = now_iso()
    state = router_state or {
        "handoffs": read_jsonl(runtime / HANDOFF_ARTIFACT),
        "decisions": read_jsonl(runtime / DECISIONS_ARTIFACT),
        "release": read_json(runtime / RELEASE_READINESS_ARTIFACT),
    }
    submission_ledger = read_json(runtime / PAPEROPS_SUBMISSION_LEDGER_ARTIFACT)
    submitted_keys = {
        str(value)
        for value in submission_ledger.get("submitted_source_idempotency_keys", [])
        if str(value)
    }
    consumer = build_handoff_consumption_state(
        state.get("handoffs", []),
        state.get("decisions", []),
        state.get("release", {}),
        read_json(runtime / LOCK_ARTIFACT),
        generated_at=generated,
        submitted_idempotency_keys=submitted_keys,
    )
    errors = validate_handoff_consumption_state(consumer)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_paperops_handoff_v3_consumer_checks",
        "phase_id": PHASE_ID,
        "generated_at": generated,
        "status": "passed" if not errors else "blocked",
        "implementation_ready": not errors,
        "consumer_status": consumer["status"],
        "enforcement_active": consumer["enforcement_active"],
        "handoff_count": consumer["handoff_count"],
        "receipt_count": consumer["receipt_count"],
        "accepted_handoff_count": consumer["accepted_handoff_count"],
        "rejected_handoff_count": consumer["rejected_handoff_count"],
        "guarded_paperops_command_sequence_allowed": consumer[
            "guarded_paperops_command_sequence_allowed"
        ],
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    store.write_json(
        HANDOFF_CONSUMER_STATE_ARTIFACT,
        {
            k: v
            for k, v in consumer.items()
            if k not in {"receipts", "accepted_handoffs", "rejections"}
        },
    )
    store.write_jsonl(HANDOFF_RECEIPTS_ARTIFACT, consumer["receipts"])
    store.write_jsonl(HANDOFF_ACCEPTED_ARTIFACT, consumer["accepted_handoffs"])
    store.write_jsonl(HANDOFF_REJECTIONS_ARTIFACT, consumer["rejections"])
    store.write_json(HANDOFF_CONSUMER_CHECK_ARTIFACT, checks)
    router_checks = read_json(runtime / CHECK_ARTIFACT)
    if router_checks:
        combined_errors = unique_errors(
            [*(router_checks.get("validation_errors", []) or []), *errors]
        )
        router_checks.update(
            {
                "status": "passed" if not combined_errors else "blocked",
                "implementation_ready": not combined_errors,
                "canonical_wrapper_consumer_implemented": True,
                "handoff_consumer_status": consumer["status"],
                "handoff_consumer_enforcement_active": consumer["enforcement_active"],
                "handoff_consumption_receipt_count": consumer["receipt_count"],
                "accepted_handoff_count": consumer["accepted_handoff_count"],
                "rejected_handoff_count": consumer["rejected_handoff_count"],
                "guarded_paperops_command_sequence_allowed": consumer[
                    "guarded_paperops_command_sequence_allowed"
                ],
                "validation_error_count": len(combined_errors),
                "validation_errors": combined_errors,
            }
        )
        store.write_json(CHECK_ARTIFACT, router_checks)
    return consumer, checks, errors


def read_consumed_v3_handoffs_for_paperops(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    runtime = runtime_dir(settings)
    state = read_json(runtime / HANDOFF_CONSUMER_STATE_ARTIFACT)
    accepted = read_jsonl(runtime / HANDOFF_ACCEPTED_ARTIFACT)
    errors: list[str] = []
    if state.get("enforcement_active") is not True:
        errors.append("v3_handoff_consumer_not_enforced")
    expected_ids = set(state.get("accepted_handoff_ids", []) or [])
    actual_ids: set[str] = set()
    for record in accepted:
        source = record.get("source_handoff")
        source = source if isinstance(source, dict) else {}
        handoff_id = str(source.get("paperops_handoff_id") or "")
        if not handoff_id:
            errors.append("accepted_v3_handoff_id_missing")
        actual_ids.add(handoff_id)
        if record.get("source_handoff_sha256") != sha256_json(source):
            errors.append(f"accepted_v3_handoff_hash_mismatch:{handoff_id}")
    if actual_ids != expected_ids:
        errors.append("accepted_v3_handoff_state_mismatch")
    if state.get("guarded_paperops_command_sequence_allowed") is not bool(accepted):
        errors.append("accepted_v3_handoff_sequence_state_mismatch")
    return state, accepted, unique_errors(errors)


def build_and_write_release_readiness(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    generated = now_iso()
    release = build_release_readiness(
        read_json(runtime / PHASE_STATUS_ARTIFACT),
        read_json(runtime / LOCK_ARTIFACT),
        read_json(runtime / OPERATOR_APPROVALS_ARTIFACT),
        read_json(runtime / RISK_POLICY_ARTIFACT),
        read_json(runtime / EDGE_SUMMARY_ARTIFACT),
        read_json(runtime / SHADOW_PROMOTION_ARTIFACT),
        read_json(runtime / PAPEROPS_SUMMARY_ARTIFACT),
        generated_at=generated,
    )
    errors = validate_release_readiness(release)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_research_lock_release_checks",
        "phase_id": PHASE_ID,
        "generated_at": generated,
        "status": "passed" if not errors else "blocked",
        "implementation_ready": not errors,
        "release_state": release["status"],
        "release_recommended": release["release_recommended"],
        "release_performed": release["release_performed"],
        "nonpassing_phase_count": release["nonpassing_phase_count"],
        "blocker_count": len(release["blockers"]),
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "broker_write_count": 0,
        "authority": authority_flags(),
    }
    store = AtomicArtifactStore(runtime)
    store.write_json(RELEASE_READINESS_ARTIFACT, release)
    store.write_json(RELEASE_CHECK_ARTIFACT, checks)
    return release, checks, errors


def build_and_write_router_v3(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    state = build_router_v3_state(settings)
    store.write_json(RELEASE_READINESS_ARTIFACT, state["release"])
    store.write_jsonl(DECISIONS_ARTIFACT, state["decisions"])
    store.write_json(SCOREBOARD_ARTIFACT, state["scoreboard"])
    store.write_json(WHY_NOT_ARTIFACT, state["why_not"])
    store.write_jsonl(HANDOFF_ARTIFACT, state["handoffs"])
    errors = validate_router_v3_state(state)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_router_v3_paperops_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "implementation_ready": not errors,
        "release_state": state["release"]["status"],
        "release_recommended": state["release"]["release_recommended"],
        "release_performed": state["release"]["release_performed"],
        "setup_count": len(state["setups"]),
        "decision_count": len(state["decisions"]),
        "paper_review_candidate_count": state["scoreboard"]["paper_review_candidate_count"],
        "handoff_count": len(state["handoffs"]),
        "qualified_setup_created_count": 0,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    store.write_json(CHECK_ARTIFACT, checks)
    return state, checks, errors
