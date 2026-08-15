from orchestrator.qadam_discovery_micro_conversion import (
    adapt_discovery_blockers,
    build_calibration_state,
    build_current_expectancy_v2,
)
from orchestrator.qadam_experimental_paper_policy import default_policy

NOW = "2026-08-08T12:00:00+00:00"


def _candidate() -> dict:
    return {
        "pattern_relationship_id": "pattern:one",
        "score_id": "score:one",
        "strategy_family_id": "semiconductor_policy_options_asymmetry",
        "instrument": "SMH",
        "research_rank": 0.64,
        "horizon": "5d_forward",
    }


def _direction() -> dict:
    return {
        "direction_resolution_id": "direction:one",
        "actionable_direction": "long",
        "causal_classification": {"confidence": 0.66},
    }


def _market(*, session_state: str = "regular_session") -> dict:
    return {
        "symbol": "SMH",
        "provider": "alpaca_market_data_v2",
        "provider_backed": True,
        "session_state": session_state,
        "quote_actionable": session_state == "regular_session",
        "trade_actionable": False,
        "current_price": 100.0,
        "percent_move": 0.6,
        "volume_ratio": 1.5,
        "rolling_volatility_20d": 0.02,
        "spread_bps": 8.0,
        "quote_observed_at": NOW,
    }


def test_current_expectancy_uses_current_market_without_historical_edge() -> None:
    result = build_current_expectancy_v2(
        _candidate(),
        _direction(),
        _market(),
        {},
        default_policy(NOW),
        generated_at=NOW,
    )

    assert result["ready_for_discovery_micro_review"] is True
    assert result["economics"]["net_expectancy"] > 0
    assert result["historical_expectancy_required"] is False
    assert result["validated_edge_required"] is False
    assert result["research_score_is_probability"] is False
    assert result["not_execution_approval"] is True


def test_current_expectancy_waits_for_actionable_session() -> None:
    result = build_current_expectancy_v2(
        _candidate(),
        _direction(),
        _market(session_state="closed"),
        {},
        default_policy(NOW),
        generated_at=NOW,
    )

    assert result["ready_for_discovery_micro_review"] is False
    assert "actionable_current_market_context_missing" in result["blockers"]


def test_non_quorum_support_can_remove_only_the_optional_quorum_blocker() -> None:
    policy = default_policy(NOW)
    blockers, diagnostics = adapt_discovery_blockers(
        ["fresh_source_quorum", "current_trigger_missing"],
        [
            {
                "source_key": "rss",
                "fresh": True,
                "trust_score": 0.78,
                "quorum_eligible": False,
            }
        ],
        policy,
    )

    assert blockers == ["current_trigger_missing"]
    assert diagnostics["non_quorum_support_used"] is True
    assert diagnostics["non_quorum_support_claimed_as_quorum"] is False


def test_calibration_never_backfills_or_mutates_policy() -> None:
    pending = build_calibration_state([], [], generated_at=NOW)
    complete = build_calibration_state(
        [
            {
                "session_id": f"session:{index}",
                "shortlisted": 1,
                "hypotheses": 0,
            }
            for index in range(5)
        ],
        [
            {
                "session_id": f"session:{index}",
                "eligible_for_conversion_measurement": True,
            }
            for index in range(5)
        ],
        generated_at=NOW,
    )

    assert pending["status"] == "pending_real_market_sessions"
    assert complete["status"] == "proposal_ready"
    assert complete["proposal_only"] is True
    assert complete["automatic_threshold_mutation_allowed"] is False
    assert complete["automatic_risk_or_authority_mutation_allowed"] is False
    assert complete["simulated_or_backfilled_sessions_used"] is False
