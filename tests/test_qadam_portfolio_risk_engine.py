from __future__ import annotations

from orchestrator.qadam_portfolio_risk_engine import (
    ABSOLUTE_TRADE_CEILING_USD,
    DISCOVERY_MICRO_TRADE_CEILING_USD,
    _apply_discovery_micro_cycle_capacity,
    _simulate_portfolio_lane,
    _stress_test,
    default_portfolio_policy,
    evaluate_position_size,
)
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


def test_discovery_micro_size_is_capped_at_five_hundred_dollars() -> None:
    result = evaluate_position_size(
        _micro_setup(), _portfolio(), default_portfolio_policy(NOW), generated_at=NOW
    )
    proposal = result["proposal"]

    assert proposal is not None
    assert proposal["experimental_tier"] == DISCOVERY_MICRO_TIER
    assert proposal["proposed_notional"] <= DISCOVERY_MICRO_TRADE_CEILING_USD
    assert proposal["risk_approval_created"] is False
    assert proposal["paper_order_created"] is False


def test_discovery_micro_rejects_a_second_unresolved_exposure() -> None:
    portfolio = _portfolio()
    portfolio["open_discovery_micro_exposure_count"] = 1
    result = evaluate_position_size(
        _micro_setup(), portfolio, default_portfolio_policy(NOW), generated_at=NOW
    )

    assert result["proposal"] is None
    assert "discovery_micro_concurrent_position_limit_reached" in result[
        "rejection"
    ]["rejection_reasons"]


def test_cycle_keeps_only_the_strongest_discovery_micro_proposal() -> None:
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
        "discovery_micro_cycle_capacity_reserved_for_higher_ranked_setup"
    ]


def test_existing_position_requires_complete_pairwise_correlation_context() -> None:
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
    assert result["proposal"] is None
    assert "cross_position_correlation_context_missing" in result["rejection"][
        "rejection_reasons"
    ]


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
