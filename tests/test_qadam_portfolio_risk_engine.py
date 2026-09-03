from __future__ import annotations

from orchestrator.qadam_portfolio_risk_engine import (
    ABSOLUTE_TRADE_CEILING_USD,
    DISCOVERY_MICRO_TRADE_CEILING_USD,
    _apply_discovery_micro_cycle_capacity,
    _current_portfolio_state,
    _market_context_fresh,
    _setup_from_lineage,
    _simulate_portfolio_lane,
    _stress_test,
    default_portfolio_policy,
    evaluate_position_size,
)
from orchestrator.qadam_forward_shadow import economic_signal_identity_for_hypothesis
from orchestrator.qadam_experimental_paper_policy import (
    DISCOVERY_MICRO_TIER,
    EXPERIMENTAL_UNVALIDATED,
)


NOW = "2026-07-18T08:00:00+00:00"


def _portfolio() -> dict:
    return {
        "equity": 100_000.0,
        "daily_loss_pct": 0.0,
        "trailing_drawdown_pct": 0.0,
        "new_notional_today": 0.0,
        "positions": [],
    }


def _setup() -> dict:
    return {
        "setup_id": "risk-setup:test",
        "hypothesis_id": "hypothesis:test",
        "edge_id": "edge:test",
        "research_goal_id": "research-goal:test",
        "instrument": "SMH",
        "strategy_family_id": "semiconductor_policy_options_asymmetry",
        "correlated_cluster": "semiconductors",
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
        "source_families": ["sec_edgar", "patents"],
        "correlation_to_existing": [],
        "akber_decision": "pass",
        "shadow_promotion_ready": True,
        "quantity_increment": 1.0,
    }


def _micro_setup() -> dict:
    setup = _setup()
    setup.update(
        {
            "evidence_class": EXPERIMENTAL_UNVALIDATED,
            "experimental_tier": DISCOVERY_MICRO_TIER,
            "edge_id": None,
            "pattern_relationship_id": "pattern:micro",
            "score_id": "score:micro",
            "edge_confidence_class": "experimental_discovery_micro",
            "expected_net_return": 0.0025,
            "uncertainty": 0.75,
            "decision_time_shadow_snapshot_ready": True,
            "shadow_promotion_ready": False,
        }
    )
    return setup


def _micro_lineage_context() -> tuple[dict, dict]:
    hypothesis = {
        "hypothesis_id": "hypothesis:refreshed",
        "evidence_class": EXPERIMENTAL_UNVALIDATED,
        "experimental_tier": DISCOVERY_MICRO_TIER,
        "edge_lineage": {"edge_id": None},
        "pattern_lineage": {
            "pattern_relationship_id": "pattern:micro",
            "score_id": "score:micro",
            "raw_research_score": 0.58,
            "independent_market_confirmation": {
                "current_market_price": 1.0,
                "volatility_context": 1.0,
            },
        },
        "research_goal_lineage": {"research_goal_id": "goal:micro"},
        "instrument_proxy_mapping": {"execution_proxy": "XLE"},
        "direction_horizon": {"direction": "long", "horizon": "3d_forward"},
        "expected_edge_range": {"net_expectancy": 0.0025},
        "risk_concept": {"correlation_to_existing": []},
    }
    akber_input = {
        "akber_input_id": "akber-input:refreshed",
        "hypothesis_id": hypothesis["hypothesis_id"],
        "generated_at": NOW,
        "context_complete": True,
        "fixture_or_sample_evidence_count": 0,
        "stale_evidence_count": 0,
        "incomplete_provenance_count": 0,
        "current_trigger_sources": ["rss"],
        "confirmation_alternative_satisfied": True,
        "evidence": {
            "fresh_catalyst": {
                "available": True,
                "observed_at": NOW,
                "source_refs": ["rss:event:test"],
                "value": "energy market catalyst",
            },
            "technical_confirmation": {
                "value": {"current_price": 100.0, "annualized_volatility": 0.2}
            },
            "volatility_context": {
                "value": {"current_price": 100.0, "annualized_volatility": 0.2}
            },
            "liquidity_and_spread": {
                "details": {
                    "spread_bps": 2.0,
                    "average_daily_dollar_volume": 100_000_000.0,
                }
            },
            "invalidation_clarity": {
                "details": {"invalidation_price": 95.0, "max_loss_per_unit": 5.0}
            },
            "paperability_proxy": {
                "available": True,
                "details": {
                    "paperable": True,
                    "paper_route": "guarded_alpaca_paper_via_paperops",
                    "quantity_increment": 1.0,
                },
            },
        },
    }
    return hypothesis, akber_input


def test_refreshed_hypothesis_reuses_passing_shadow_for_same_economic_signal() -> None:
    hypothesis, akber_input = _micro_lineage_context()
    signal_id = economic_signal_identity_for_hypothesis(hypothesis, akber_input)
    setup = _setup_from_lineage(
        hypothesis,
        {},
        akber_input,
        {
            "akber_result_id": "akber:pass",
            "akber_input_id": akber_input["akber_input_id"],
            "decision": "pass",
        },
        [
            {
                "hypothesis_id": "hypothesis:previous-generation",
                "economic_signal_identity_id": signal_id,
                "decision_id": "shadow:previous-generation",
                "decision_at": NOW,
                "entry_observation_provider_backed": True,
                "simulated_elapsed_time": False,
                "lifecycle_state": "frozen_waiting_for_outcome",
                "akber_decision": "pass",
                "promotion_evidence_allowed": True,
            }
        ],
        [],
        {},
        {"instruments": [{"symbol": "XLE", "market_family": "energy"}]},
        default_portfolio_policy(NOW),
        generated_at=NOW,
    )

    assert setup["decision_time_shadow_snapshot_ready"] is True
    assert setup["shadow_economic_signal_identity_id"] == signal_id


def test_counterfactual_hold_shadow_cannot_be_reused_for_trade_progression() -> None:
    hypothesis, akber_input = _micro_lineage_context()
    signal_id = economic_signal_identity_for_hypothesis(hypothesis, akber_input)
    setup = _setup_from_lineage(
        hypothesis,
        {},
        akber_input,
        {"akber_input_id": akber_input["akber_input_id"], "decision": "pass"},
        [
            {
                "hypothesis_id": "hypothesis:previous-generation",
                "economic_signal_identity_id": signal_id,
                "decision_id": "shadow:hold",
                "decision_at": NOW,
                "entry_observation_provider_backed": True,
                "simulated_elapsed_time": False,
                "lifecycle_state": "frozen_waiting_for_outcome",
                "akber_decision": "hold_missing_context",
                "promotion_evidence_allowed": False,
            }
        ],
        [],
        {},
        {"instruments": [{"symbol": "XLE", "market_family": "energy"}]},
        default_portfolio_policy(NOW),
        generated_at=NOW,
    )

    assert setup["decision_time_shadow_snapshot_ready"] is False


def test_optional_stale_evidence_does_not_invalidate_fresh_execution_context() -> None:
    _hypothesis, akber_input = _micro_lineage_context()
    akber_input.update(
        {
            "fixture_or_sample_evidence_count": 1,
            "stale_evidence_count": 1,
            "incomplete_provenance_count": 1,
        }
    )
    akber_input["evidence"].update(
        {
            "technical_confirmation": {
                "available": False,
                "fixture_backed": True,
                "state": "sample_or_fixture_not_admissible",
            },
            "nonlinear_quantum_review": {
                "available": False,
                "freshness_state": "stale",
                "state": "stale",
            },
        }
    )

    fresh, age = _market_context_fresh(
        akber_input,
        generated_at=NOW,
        policy=default_portfolio_policy(NOW),
    )

    assert fresh is True
    assert age == 0.0


def test_missing_provider_spread_keeps_execution_context_fail_closed() -> None:
    _hypothesis, akber_input = _micro_lineage_context()
    akber_input["evidence"]["liquidity_and_spread"] = {
        "available": False,
        "provenance_complete": True,
        "freshness_state": "fresh",
        "state": "missing",
        "details": {"spread_bps": None},
    }

    fresh, _age = _market_context_fresh(
        akber_input,
        generated_at=NOW,
        policy=default_portfolio_policy(NOW),
    )

    assert fresh is False


def test_absolute_trade_ceiling_and_invalidation_budget_are_both_enforced() -> None:
    result = evaluate_position_size(
        _setup(), _portfolio(), default_portfolio_policy(NOW), generated_at=NOW
    )
    proposal = result["proposal"]
    assert proposal is not None
    assert proposal["proposed_notional"] <= ABSOLUTE_TRADE_CEILING_USD
    assert proposal["maximum_loss_at_invalidation"] <= proposal[
        "risk_budget_dollars_after_uncertainty_haircut"
    ]
    assert proposal["proposal_only"] is True
    assert proposal["risk_approval_created"] is False
    assert proposal["paper_order_created"] is False


def test_risk_proposal_identity_is_immutable_per_decision_generation() -> None:
    first_setup = _setup()
    first_setup["decision_generation_id"] = "decision-generation:first"
    first = evaluate_position_size(
        first_setup, _portfolio(), default_portfolio_policy(NOW), generated_at=NOW
    )["proposal"]
    replay = evaluate_position_size(
        first_setup, _portfolio(), default_portfolio_policy(NOW), generated_at=NOW
    )["proposal"]
    second_setup = {**first_setup, "decision_generation_id": "decision-generation:second"}
    second = evaluate_position_size(
        second_setup, _portfolio(), default_portfolio_policy(NOW), generated_at=NOW
    )["proposal"]

    assert first is not None
    assert replay is not None
    assert second is not None
    assert first["proposal_id"] == replay["proposal_id"]
    assert first["proposal_id"] != second["proposal_id"]


def test_discovery_micro_size_is_capped_at_five_thousand_dollars() -> None:
    result = evaluate_position_size(
        _micro_setup(), _portfolio(), default_portfolio_policy(NOW), generated_at=NOW
    )
    proposal = result["proposal"]

    assert proposal is not None
    assert proposal["experimental_tier"] == DISCOVERY_MICRO_TIER
    assert proposal["proposed_notional"] <= DISCOVERY_MICRO_TRADE_CEILING_USD
    assert proposal["risk_approval_created"] is False
    assert proposal["paper_order_created"] is False


def test_discovery_micro_can_use_one_lot_for_narrow_soft_rounding_shortfall() -> None:
    setup = _micro_setup()
    setup.update(
        {
            "current_price": 224.20,
            "annualized_volatility": 0.4477,
            "invalidation": {"max_loss_per_unit": 6.32},
            "causal_support_source_count": 1,
            "independent_market_confirmation_passed": True,
            "soft_evidence_size_multiplier": 1.0,
        }
    )

    result = evaluate_position_size(
        setup, _portfolio(), default_portfolio_policy(NOW), generated_at=NOW
    )
    proposal = result["proposal"]

    assert proposal is not None
    assert proposal["proposed_quantity"] == 1.0
    assert proposal["minimum_viable_lot_applied"] is True
    assert proposal["rounding_mode"] == "bounded_minimum_viable_lot"
    assert proposal["maximum_loss_at_invalidation"] <= proposal[
        "minimum_viable_lot_assessment"
    ]["hard_risk_cap"]


def test_minimum_lot_cannot_override_hard_notional_or_risk_caps() -> None:
    policy = default_portfolio_policy(NOW)
    setup = _micro_setup()
    setup.update(
        {
            "current_price": 6_000.0,
            "invalidation": {"max_loss_per_unit": 600.0},
            "causal_support_source_count": 1,
            "independent_market_confirmation_passed": True,
            "soft_evidence_size_multiplier": 1.0,
        }
    )

    result = evaluate_position_size(setup, _portfolio(), policy, generated_at=NOW)

    assert result["proposal"] is None
    assessment = result["rejection"]["minimum_viable_lot_assessment"]
    assert assessment["within_hard_risk_cap"] is False
    assert assessment["within_all_notional_limits"] is False


def test_discovery_micro_rejects_a_fourth_unresolved_exposure() -> None:
    portfolio = _portfolio()
    portfolio["open_discovery_micro_exposure_count"] = 3
    result = evaluate_position_size(
        _micro_setup(), portfolio, default_portfolio_policy(NOW), generated_at=NOW
    )

    assert result["proposal"] is None
    assert "discovery_micro_concurrent_position_limit_reached" in result[
        "rejection"
    ]["rejection_reasons"]


def test_cycle_keeps_only_one_discovery_setup_per_correlated_cluster() -> None:
    policy = default_portfolio_policy(NOW)
    first = evaluate_position_size(
        _micro_setup(), _portfolio(), policy, generated_at=NOW
    )["proposal"]
    assert first is not None
    first["research_score"] = 0.60
    first["expected_net_return"] = 0.004
    first["spread_bps"] = 4.0
    first["average_daily_dollar_volume"] = 20_000_000.0

    second = dict(first)
    second.update(
        {
            "proposal_id": "proposal:second",
            "setup_id": "setup:second",
            "hypothesis_id": "hypothesis:second",
            "instrument": "SOXX",
            "research_score": 0.50,
            "expected_net_return": 0.002,
        }
    )
    retained, rejections = _apply_discovery_micro_cycle_capacity(
        [second, first], [], _portfolio(), policy, generated_at=NOW
    )

    assert [row["proposal_id"] for row in retained] == [first["proposal_id"]]
    assert rejections[0]["rejection_reasons"] == [
        "discovery_micro_correlated_cluster_slot_occupied"
    ]


def test_cycle_can_retain_three_distinct_discovery_clusters() -> None:
    policy = default_portfolio_policy(NOW)
    proposals = []
    for index, (instrument, cluster) in enumerate(
        (("SMH", "semiconductors"), ("ITA", "defence"), ("SLV", "silver"))
    ):
        setup = _micro_setup()
        setup.update(
            {
                "setup_id": f"setup:{instrument}",
                "hypothesis_id": f"hypothesis:{instrument}",
                "instrument": instrument,
                "correlated_cluster": cluster,
                "strategy_family_id": f"strategy:{cluster}",
            }
        )
        proposal = evaluate_position_size(
            setup, _portfolio(), policy, generated_at=NOW
        )["proposal"]
        assert proposal is not None
        proposal.update(
            {
                "research_score": 0.70 - index * 0.05,
                "expected_net_return": 0.005 - index * 0.001,
                "spread_bps": 5.0,
                "average_daily_dollar_volume": 20_000_000.0,
            }
        )
        proposals.append(proposal)

    retained, rejections = _apply_discovery_micro_cycle_capacity(
        proposals, [], _portfolio(), policy, generated_at=NOW
    )

    assert {row["instrument"] for row in retained} == {"SMH", "ITA", "SLV"}
    assert rejections == []


def test_existing_position_uses_labelled_conservative_correlation_context() -> None:
    portfolio = _portfolio()
    portfolio["positions"] = [
        {
            "instrument": "QQQ",
            "strategy_family_id": "semiconductor_policy_options_asymmetry",
            "correlated_cluster": "semiconductors",
            "source_families": ["sec_edgar"],
            "notional": 2_000.0,
        }
    ]
    result = evaluate_position_size(
        _setup(), portfolio, default_portfolio_policy(NOW), generated_at=NOW
    )
    proposal = result["proposal"]
    assert proposal is not None
    assert proposal["correlation_context_basis"] == "conservative_cluster_proxy"
    assert proposal["derived_correlation_record_count"] == 1
    assert proposal["maximum_pairwise_absolute_correlation"] == 0.85


def test_same_instrument_conservative_proxy_preserves_duplicate_exposure_veto() -> None:
    portfolio = _portfolio()
    portfolio["positions"] = [
        {
            "instrument": "SMH",
            "strategy_family_id": "other",
            "correlated_cluster": "semiconductors",
            "source_families": ["other"],
            "notional": 1_000.0,
        }
    ]
    result = evaluate_position_size(
        _setup(), portfolio, default_portfolio_policy(NOW), generated_at=NOW
    )
    assert result["proposal"] is None
    assert "pairwise_correlation_exceeds_frozen_maximum" in result["rejection"][
        "rejection_reasons"
    ]


def test_broker_orders_supply_daily_notional_and_sleeve_classification() -> None:
    state = _current_portfolio_state(
        {
            "status": "broker_mirror_fresh",
            "rows": [
                {
                    "instrument": "ITA",
                    "market_value": 1_200.0,
                    "quantity": 5.0,
                    "current_price": 240.0,
                }
            ],
        },
        [
            {
                "observed_at": NOW,
                "equity_gbp": 100_000.0,
                "peak_equity_gbp": 100_000.0,
            }
        ],
        [
            {
                "instrument": "ITA",
                "client_order_id": "q7-operator-sleeve-test",
                "position_intent": "buy_to_open",
                "status": "filled",
                "submitted_at": NOW,
                "filled_avg_price": 240.0,
                "quantity": 5.0,
                "filled_quantity": 5.0,
            },
            {
                "instrument": "ITA",
                "client_order_id": "q7-operator-exit-test",
                "position_intent": "sell_to_close",
                "status": "held",
                "submitted_at": NOW,
                "quantity": 5.0,
            },
        ],
        {"instruments": [{"symbol": "ITA", "market_family": "defence"}]},
        generated_at=NOW,
    )

    assert state["new_notional_today"] == 1_200.0
    assert state["daily_notional_context_complete"] is True
    assert state["open_discovery_micro_exposure_count"] == 0
    assert state["positions"][0]["strategy_family_id"] == "operator_exploratory_sleeve"
    assert state["positions"][0]["source_families"] == [
        "operator_exploratory_sleeve"
    ]


def test_canonical_discovery_order_consumes_only_the_canonical_micro_slot() -> None:
    state = _current_portfolio_state(
        {"status": "broker_mirror_fresh", "rows": []},
        [
            {
                "observed_at": NOW,
                "equity_gbp": 100_000.0,
                "peak_equity_gbp": 100_000.0,
            }
        ],
        [
            {
                "instrument": "XAR",
                "client_order_id": "q7-6-stage-test",
                "position_intent": "buy_to_open",
                "status": "accepted",
                "submitted_at": NOW,
                "limit_price": 200.0,
                "quantity": 1.0,
            }
        ],
        {"instruments": [{"symbol": "XAR", "market_family": "defence"}]},
        generated_at=NOW,
    )

    assert state["open_discovery_micro_exposure_count"] == 1
    assert state["open_discovery_micro_symbols"] == ["XAR"]


def test_stale_context_and_unguarded_route_cannot_be_sized() -> None:
    setup = _setup()
    setup["market_context_age_seconds"] = 3_601.0
    setup["paper_route"] = "direct_broker"
    result = evaluate_position_size(
        setup, _portfolio(), default_portfolio_policy(NOW), generated_at=NOW
    )
    assert result["proposal"] is None
    assert "guarded_paper_route_not_confirmed" in result["rejection"][
        "rejection_reasons"
    ]
    assert "market_context_exceeds_frozen_maximum_age" in result["rejection"][
        "rejection_reasons"
    ]


def test_pairwise_correlation_and_source_family_caps_fail_closed() -> None:
    policy = default_portfolio_policy(NOW)
    portfolio = _portfolio()
    portfolio["positions"] = [
        {
            "instrument": "QQQ",
            "strategy_family_id": "other",
            "correlated_cluster": "macro",
            "source_families": ["sec_edgar"],
            "notional": 20_000.0,
        }
    ]
    setup = _setup()
    setup["correlation_to_existing"] = [{"instrument": "QQQ", "correlation": 0.96}]
    correlated = evaluate_position_size(setup, portfolio, policy, generated_at=NOW)
    assert correlated["proposal"] is None
    assert "pairwise_correlation_exceeds_frozen_maximum" in correlated["rejection"][
        "rejection_reasons"
    ]

    setup["correlation_to_existing"] = [{"instrument": "QQQ", "correlation": 0.10}]
    source_capped = evaluate_position_size(setup, portfolio, policy, generated_at=NOW)
    assert source_capped["proposal"] is None
    assert source_capped["rejection"]["binding_limit"] == "source_family"


def test_historical_aggregates_are_not_misrepresented_as_portfolio_simulation() -> None:
    policy = default_portfolio_policy(NOW)
    lane = _simulate_portfolio_lane(
        [
            {
                "replay_id": "replay:test",
                "replay_is_result_level_diagnostic_not_portfolio_simulation": True,
                "outcome_available_at": "2026-07-17T00:00:00+00:00",
                "outcome": {"net_return": 0.02},
            }
        ],
        lane="historical",
        policy=policy,
        initial_equity=100_000.0,
        generated_at=NOW,
    )
    assert lane["status"] == "not_measurable_no_eligible_tape"
    assert lane["eligible_record_count"] == 0
    assert lane["excluded_reason_counts"] == {
        "aggregate_result_not_chronological_trade_tape": 1
    }


def test_real_shadow_outcomes_can_be_simulated_without_orders_or_proof() -> None:
    policy = default_portfolio_policy(NOW)
    lane = _simulate_portfolio_lane(
        [
            {
                "outcome_id": "shadow-outcome:test",
                "outcome_available_at": "2026-07-17T00:00:00+00:00",
                "net_return": 0.02,
                "simulated_elapsed_time": False,
            }
        ],
        lane="forward_shadow",
        policy=policy,
        initial_equity=100_000.0,
        generated_at=NOW,
    )
    assert lane["status"] == "measured_research_only"
    assert lane["ending_equity"] == 100_100.0
    assert lane["paper_order_created"] is False
    assert lane["proof_eligible"] is False


def test_stress_test_contains_both_required_simulation_lanes() -> None:
    policy = default_portfolio_policy(NOW)
    stress = _stress_test(
        _portfolio(),
        policy,
        NOW,
        historical_replays=[],
        shadow_outcomes=[],
    )
    assert stress["tail_stress_gate_passed"] is True
    assert "historical_portfolio_simulation" in stress
    assert "forward_shadow_portfolio_simulation" in stress
    assert stress["risk_approval_created"] is False
