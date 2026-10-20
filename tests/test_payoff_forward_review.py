from datetime import datetime, timedelta, timezone

from orchestrator.learning.forward_evaluation import evaluate_forward_version


def _rows(values, protocol):
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    provider = {"provider_backed": True}
    return [{"strategy_version_id": "v", "economic_signal_identity_id": f"event:{i}",
             "outcome_id": f"o:{i}", "simulated_elapsed_time": False,
             "decision_at": (start+timedelta(days=2*i)).isoformat(),
             "outcome_available_at": (start+timedelta(days=2*i+1)).isoformat(),
             "net_return": value, "benchmark_net_return": 0,
             "evaluation_contract": {"version": protocol}, "benchmark_comparison_available": True,
             "entry_observation": provider, "outcome_observation": provider,
             "benchmark_observation": provider} for i, value in enumerate(values)]


def test_payoff_review_does_not_require_majority_winners_or_rewrite_old_protocol():
    protocol = "matched-forward.2-payoff"
    rows = _rows(([.04] + [-.005]*3)*320, protocol)
    result = evaluate_forward_version("v", rows, as_of="2030-01-01T00:00:00Z",
                                      evaluation_contract={"version": protocol})
    assert result["hit_rate"] == .25
    assert result["mean_net_return"] > 0
    assert result["eligible_for_emerging_review"] is True
    assert result["validated_lane_authority_granted"] is False
    legacy = evaluate_forward_version("v", _rows(([.04]+[-.005]*3)*320, "matched-forward.1"),
                                       as_of="2030-01-01T00:00:00Z")
    assert "multiplicity_adjusted_win_consistency_not_demonstrated" in legacy["blockers"]
    bad = evaluate_forward_version("v", _rows(([.001]*9+[-.03])*128, protocol),
        as_of="2030-01-01T00:00:00Z", evaluation_contract={"version": protocol})
    assert bad["hit_rate"] > .8
    assert bad["mean_net_return"] < 0
    assert bad["eligible_for_emerging_review"] is False


def test_legacy_outcomes_cannot_be_relabelled_into_new_protocol():
    result = evaluate_forward_version("v", _rows([.01]*20, "matched-forward.1"),
        as_of="2030-01-01T00:00:00Z", evaluation_contract={"version": "matched-forward.2-payoff"})
    assert result["independent_outcome_count"] == 0
    assert result["exclusion_counts"]["evaluation_contract_mismatch"] == 20
