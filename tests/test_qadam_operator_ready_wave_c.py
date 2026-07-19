from __future__ import annotations

import pytest

from orchestrator.qadam_akber_filter_v3 import (
    CONTEXT_FIELDS,
    build_akber_input,
    evaluate_akber_input,
)
from orchestrator.qadam_dynamic_plan import PHASE_ORDER, program_status
from orchestrator.qadam_forward_shadow import (
    complete_shadow_outcome,
    freeze_shadow_decision,
)
from orchestrator.qadam_portfolio_risk_engine import (
    default_portfolio_policy,
    evaluate_position_size,
)
from orchestrator.qadam_strategy_foundry_v3 import (
    build_strategy_hypothesis,
    hypothesis_rejection_reasons,
)

NOW = "2026-01-01T00:00:00+00:00"


def _edge(*, promotion_class: str = "validated_research_edge") -> dict:
    return {
        "edge_id": "edge-v3:test",
        "promotion_class": promotion_class,
        "source_feature_definition": "fresh disruption sources lead TEST returns",
        "instrument": "TEST",
        "direction": "upside_under_confirmed_disruption",
        "horizon": "3d_forward",
        "regime": "risk_on",
        "score_version": "score:v3",
        "label_version": "label:v1",
        "backtest_run_id": "backtest:test",
        "fold_ids": ["fold-001"],
        "dataset_hashes": {"scores": "abc", "labels": "def"},
        "applied_learning_version_ids": ["learning:v1"],
        "stage1_learning_input_version": "stage1-input:v1",
        "strategy_fit_vector": {"strategy:test": 0.8},
        "gross_expectancy": 0.02,
        "net_expectancy": 0.01,
        "confidence_distribution": {"lower": 0.001, "upper": 0.02},
        "decay_state": "current",
        "falsifiers": ["source-price relationship reverses"],
        "retirement_conditions": ["net expectancy turns non-positive"],
    }


def _strategy() -> dict:
    return {
        "strategy_family_id": "strategy:test",
        "label": "Test Macro Strategy",
        "instrument_contribution": {
            "instruments": [
                {
                    "symbol": "TEST",
                    "paper_route_available": True,
                }
            ]
        },
    }


def _hypothesis(*, promotion_class: str = "validated_research_edge") -> dict:
    return build_strategy_hypothesis(
        _edge(promotion_class=promotion_class),
        _strategy(),
        generated_at=NOW,
    )


def _complete_akber_context() -> dict:
    context = {
        field: {"available": True, "state": "available"}
        for field in CONTEXT_FIELDS
    }
    context["risk_reward_context"]["details"] = {
        "expected_net_return": 0.01,
        "reward_to_risk": 2.0,
    }
    context["invalidation_clarity"]["details"] = {"defined": True}
    context["liquidity_and_spread"]["details"] = {"spread_bps": 10.0}
    context["paperability_proxy"]["details"] = {"paperable": True}
    return context


def _portfolio() -> dict:
    return {
        "equity": 100_000.0,
        "daily_loss_pct": 0.0,
        "trailing_drawdown_pct": 0.0,
        "new_notional_today": 0.0,
        "positions": [],
    }


def _risk_setup() -> dict:
    return {
        "setup_id": "setup:test",
        "hypothesis_id": "hypothesis:test",
        "edge_id": "edge:test",
        "research_goal_id": "research-goal:test",
        "instrument": "TEST",
        "strategy_family_id": "strategy:test",
        "correlated_cluster": "cluster:test",
        "direction": "long",
        "expected_net_return": 0.01,
        "annualized_volatility": 0.20,
        "current_price": 100.0,
        "invalidation": {"invalidation_price": 95.0},
        "liquidity": {
            "spread_bps": 10.0,
            "average_daily_dollar_volume": 10_000_000.0,
        },
        "paperable": True,
        "paper_route": "guarded_alpaca_paper_via_paperops",
        "market_context_fresh": True,
        "market_context_age_seconds": 0.0,
        "edge_confidence_class": "validated_research_edge",
        "uncertainty": 0.20,
        "source_concentration": 0.30,
        "source_families": ["source:test"],
        "correlation_to_existing": [],
        "akber_decision": "pass",
        "shadow_promotion_ready": True,
        "quantity_increment": 1.0,
    }


def test_foundry_requires_edge_and_preserves_research_only_boundary() -> None:
    reasons = hypothesis_rejection_reasons(
        {"promotion_class": "validated_research_edge"}, _strategy()
    )
    assert "missing_edge_registry_reference" in reasons
    hypothesis = _hypothesis()
    assert hypothesis["edge_lineage"]["edge_id"] == "edge-v3:test"
    assert hypothesis["research_goal_lineage"]["complete"] is True
    assert hypothesis["edge_lineage"]["applied_learning_version_ids"] == [
        "learning:v1"
    ]
    assert hypothesis["edge_lineage"]["stage1_learning_input_version"] == (
        "stage1-input:v1"
    )
    assert hypothesis["hypothesis_state"] == "ready_for_akber_review"
    assert hypothesis["trade_candidate_created"] is False
    assert hypothesis["paper_order_created"] is False


def test_exploratory_foundry_hypothesis_cannot_leave_shadow() -> None:
    hypothesis = _hypothesis(promotion_class="exploratory_research_edge")
    assert hypothesis["hypothesis_state"] == "shadow_only"
    assert hypothesis["akber_review_allowed"] is False
    assert hypothesis["blocker_state"]["router_eligible"] is False


def test_akber_holds_missing_context_and_pass_is_not_execution_approval() -> None:
    hypothesis = _hypothesis()
    missing_input = build_akber_input(hypothesis, {}, generated_at=NOW)
    held = evaluate_akber_input(missing_input)
    assert held["decision"] == "hold_missing_context"
    assert held["missing_critical_context_count"] == len(CONTEXT_FIELDS)
    assert held["router_eligible"] is False

    complete_input = build_akber_input(
        hypothesis, _complete_akber_context(), generated_at=NOW
    )
    assert complete_input["applied_learning_version_ids"] == ["learning:v1"]
    assert complete_input["stage1_learning_input_version"] == "stage1-input:v1"
    passed = evaluate_akber_input(complete_input)
    assert passed["decision"] == "pass"
    assert passed["router_eligible"] is True
    assert passed["akber_pass_is_execution_approval"] is False
    assert passed["execution_approval_created"] is False
    assert passed["applied_learning_version_ids"] == ["learning:v1"]


def test_akber_explicit_adverse_evidence_vetoes() -> None:
    context = _complete_akber_context()
    context["risk_reward_context"]["details"]["expected_net_return"] = -0.01
    result = evaluate_akber_input(
        build_akber_input(_hypothesis(), context, generated_at=NOW)
    )
    assert result["decision"] == "veto"
    assert "expected_return_non_positive_after_costs" in result["hard_vetoes"]


def test_forward_shadow_requires_real_time_ordering_and_never_grants_proof() -> None:
    hypothesis = _hypothesis()
    akber = evaluate_akber_input(
        build_akber_input(hypothesis, _complete_akber_context(), generated_at=NOW)
    )
    decision = freeze_shadow_decision(hypothesis, akber, decision_at=NOW)
    assert decision["decision_frozen_before_outcome"] is True
    assert decision["paper_order_created"] is False
    with pytest.raises(ValueError, match="not_after_decision"):
        complete_shadow_outcome(
            decision,
            outcome_available_at=NOW,
            gross_return=0.01,
            cost_bps=5.0,
        )
    outcome = complete_shadow_outcome(
        decision,
        outcome_available_at="2026-01-04T00:00:00+00:00",
        gross_return=0.01,
        cost_bps=5.0,
    )
    assert outcome["real_elapsed_seconds"] == 259_200.0
    assert outcome["net_return"] == 0.0095
    assert outcome["simulated_elapsed_time"] is False
    assert outcome["proof_eligible"] is False


def test_portfolio_risk_fails_closed_without_invalidation_or_on_drawdown() -> None:
    policy = default_portfolio_policy(NOW)
    setup = _risk_setup()
    setup["invalidation"] = None
    missing = evaluate_position_size(setup, _portfolio(), policy, generated_at=NOW)
    assert missing["proposal"] is None
    assert "invalidation_context_missing" in missing["rejection"]["rejection_reasons"]

    portfolio = _portfolio()
    portfolio["trailing_drawdown_pct"] = 0.08
    drawdown = evaluate_position_size(
        _risk_setup(), portfolio, policy, generated_at=NOW
    )
    assert drawdown["proposal"] is None
    assert "trailing_drawdown_gate_breached" in drawdown["rejection"]["rejection_reasons"]


def test_portfolio_risk_caps_correlated_exposure_and_emits_proposals_only() -> None:
    policy = default_portfolio_policy(NOW)
    result = evaluate_position_size(
        _risk_setup(), _portfolio(), policy, generated_at=NOW
    )
    proposal = result["proposal"]
    assert proposal is not None
    assert proposal["proposed_quantity"] > 0
    assert proposal["proposal_only"] is True
    assert proposal["llm_size_input_used"] is False
    assert proposal["quantum_size_input_used"] is False
    assert proposal["risk_approval_created"] is False
    assert proposal["paper_order_created"] is False

    portfolio = _portfolio()
    portfolio["positions"] = [
        {
            "instrument": "OTHER",
            "strategy_family_id": "strategy:other",
            "correlated_cluster": "cluster:test",
            "source_families": ["source:other"],
            "notional": 20_000.0,
        }
    ]
    setup = _risk_setup()
    setup["correlation_to_existing"] = [
        {"instrument": "OTHER", "correlation": 0.80}
    ]
    capped = evaluate_position_size(
        setup, portfolio, policy, generated_at=NOW
    )
    assert capped["proposal"] is None
    assert capped["rejection"]["binding_limit"] == "correlated_cluster"


def test_wave_c_status_stays_evidence_maturing_until_akber_and_shadow_mature() -> None:
    phases = {phase: {"state": "not_started"} for phase in PHASE_ORDER}
    for phase in PHASE_ORDER[:8]:
        phases[phase]["state"] = "passed"
    for index in range(0, 15):
        phases[f"OR-{index}"]["state"] = "passed"
    for phase in ("OR-3", "OR-6", "OR-7", "OR-8", "OR-9", "OR-12", "OR-13"):
        phases[phase]["state"] = "evidence_maturing"
    assert program_status(phases) == "wave_c_evidence_maturing"
