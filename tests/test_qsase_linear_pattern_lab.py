from orchestrator.qsase_linear_pattern_lab import (
    LINEAR_AUTHORITY_FLAGS,
    TEST_FAMILIES,
    build_linear_pattern_results,
    validate_linear_pattern_results,
    validate_negative_linear_pattern_probes,
)


def test_linear_pattern_lab_runs_required_transparent_tests():
    payload = build_linear_pattern_results()
    families = set(payload["test_families"])

    assert payload["tested_relationship_count"] > 0
    assert set(TEST_FAMILIES).issubset(families)
    assert payload["linear_results"]
    assert payload["historical_memory"]["point_in_time_safety_required"] is True
    assert payload["linear_success_is_research_evidence_only"] is True
    assert validate_linear_pattern_results(payload) == []

    for result in payload["linear_results"]:
        tests = result["tests"]
        assert tests["event_study"]["test_family"] == "event_study"
        assert tests["lead_lag"]["test_family"] == "lead_lag"
        assert tests["correlation"]["test_family"] == "correlation"
        assert tests["regression"]["test_family"] == "regression"
        assert tests["factor_control"]["test_family"] == "factor_control"
        assert tests["walk_forward_validation"]["out_of_sample_check_present"] is True
        assert tests["false_positive_control"]["multiple_testing_checked"] is True
        assert result["risk"]["test_family"] == "hit_rate_expectancy"
        assert tests["drawdown_adverse_excursion"]["test_family"] == "drawdown_adverse_excursion"


def test_linear_pattern_lab_is_research_only_and_cannot_route_trades():
    payload = build_linear_pattern_results()

    assert payload["authority_flags"] == LINEAR_AUTHORITY_FLAGS
    assert all(value is False for value in payload["authority"].values())
    assert payload["no_strategy_hypotheses_created"] is True
    assert payload["no_trade_candidates_created"] is True
    assert payload["no_paper_orders_created"] is True
    assert payload["no_proof_credit_granted"] is True
    assert payload["candidate_for_strategy_foundry_count"] == 0

    for result in payload["linear_results"]:
        assert result["linear_success_is_research_evidence_only"] is True
        assert result["candidate_for_paper_route"] is False
        assert result["candidate_for_strategy_foundry"] is False
        assert result["trade_candidate_created"] is False
        assert result["paper_order_created"] is False
        assert result["proof_credit_allowed"] is False
        assert all(result[flag] is False for flag in LINEAR_AUTHORITY_FLAGS)

    for rejected in payload["linear_rejected_patterns"]:
        assert rejected["linear_success_is_research_evidence_only"] is True
        assert rejected["candidate_for_paper_route"] is False
        assert rejected["candidate_for_strategy_foundry"] is False
        assert rejected["rejection_reasons"]
        assert all(rejected[flag] is False for flag in LINEAR_AUTHORITY_FLAGS)


def test_linear_pattern_lab_rejects_weak_patterns_and_negative_probes():
    payload = build_linear_pattern_results()
    decisions = {result["decision"]["linear_status"] for result in payload["linear_results"]}
    rejected_reasons = {
        reason
        for rejected in payload["linear_rejected_patterns"]
        for reason in rejected["rejection_reasons"]
    }

    assert payload["rejected_linear_pattern_count"] > 0
    assert payload["inconclusive_linear_pattern_count"] > 0
    assert "linear_accept_research_evidence_only" not in decisions
    assert rejected_reasons
    assert payload["dashboard_safe_summary"]["no_trade_candidates_created"] is True
    assert validate_negative_linear_pattern_probes() == []
