from __future__ import annotations

from orchestrator.qadam_outcome_learning_promotion import (
    evaluate_strategy_promotion,
)
from orchestrator.qadam_portfolio_risk_engine import default_portfolio_policy


NOW = "2026-08-31T12:00:00+00:00"


def _strategy() -> dict:
    return {
        "hypothesis_id": "hypothesis:power",
        "strategy_family_id": "power_scarcity_congestion",
        "strategy_version_id": "paper-strategy-version:power-v1",
        "experimental_tier": "discovery_micro",
        "direction_horizon": {"direction": "long", "horizon": "3d_forward"},
        "instrument_proxy_mapping": {"execution_proxy": "VST"},
        "pattern_lineage": {"score_id": "score:power"},
        "risk_concept": {"invalidation": "regime clears"},
    }


def _outcomes(count: int, net_return: float = 0.01) -> list[dict]:
    return [
        {
            "outcome_id": f"outcome:{index}",
            "hypothesis_id": "hypothesis:power",
            "strategy_family_id": "power_scarcity_congestion",
            "strategy_version_id": "paper-strategy-version:power-v1",
            "economic_signal_identity_id": f"economic-event:{index}",
            "decision_at": f"2026-08-{index + 1:02d}T10:00:00+00:00",
            "outcome_available_at": f"2026-08-{index + 1:02d}T16:00:00+00:00",
            "simulated_elapsed_time": False,
            "net_return": net_return,
            "benchmark_net_return": 0.001,
            "benchmark_comparison_available": True,
            "evaluation_contract": {"version": "matched-forward.1"},
            "entry_observation": {"provider_backed": True},
            "outcome_observation": {"provider_backed": True},
            "benchmark_observation": {"provider_backed": True},
        }
        for index in range(count)
    ]


def test_proven_strategy_can_auto_admit_only_as_emerging_paper_strategy() -> None:
    proposal, decision = evaluate_strategy_promotion(
        _strategy(),
        {"edge_id": "edge:power", "validated_edge": True},
        _outcomes(20),
        default_portfolio_policy(NOW),
        generated_at=NOW,
    )
    assert proposal["automatic_paper_admission_recommended"] is True
    assert decision["decision"] == "admitted_emerging_paper_strategy"
    assert decision["promotion_state"] == "emerging_paper_strategy"
    assert decision["risk_envelope_mutated"] is False
    assert decision["live_strategy_admitted"] is False
    assert decision["paper_order_created"] is False


def test_forward_matched_evidence_can_support_emerging_review_without_historical_edge():
    proposal, decision = evaluate_strategy_promotion(
        _strategy(), None, _outcomes(20), default_portfolio_policy(NOW), generated_at=NOW,
    )
    assert proposal["validated_edge_present"] is False
    assert decision["paper_strategy_admitted"] is True
    assert decision["live_strategy_admitted"] is False


def test_repeated_or_wrong_version_outcomes_cannot_promote():
    records = _outcomes(20)
    for record in records:
        record["economic_signal_identity_id"] = "same-event"
    proposal, _ = evaluate_strategy_promotion(
        _strategy(), None, records, default_portfolio_policy(NOW), generated_at=NOW,
    )
    assert proposal["forward_evaluation"]["independent_outcome_count"] == 1
    assert proposal["automatic_paper_admission_recommended"] is False
    for record in records:
        record["strategy_version_id"] = "different-version"
    proposal, _ = evaluate_strategy_promotion(
        _strategy(), None, records, default_portfolio_policy(NOW), generated_at=NOW,
    )
    assert proposal["real_forward_outcome_count"] == 0


def test_insufficient_forward_evidence_cannot_auto_admit() -> None:
    proposal, decision = evaluate_strategy_promotion(
        _strategy(),
        {"edge_id": "edge:power", "validated_edge": True},
        _outcomes(2),
        default_portfolio_policy(NOW),
        generated_at=NOW,
    )
    assert proposal["automatic_paper_admission_recommended"] is False
    assert "insufficient_real_forward_outcomes" in proposal["blockers"]
    assert decision["paper_strategy_admitted"] is False
