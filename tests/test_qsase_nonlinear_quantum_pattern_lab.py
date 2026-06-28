from orchestrator.qsase_nonlinear_quantum_pattern_lab import (
    ALLOWED_QUANTUM_BACKENDS,
    ALLOWED_QUANTUM_JOB_TYPES,
    ALLOWED_QUANTUM_MODES,
    NONLINEAR_AUTHORITY_FLAGS,
    NONLINEAR_METHOD_FAMILIES,
    build_nonlinear_quantum_pattern_lab,
    validate_negative_nonlinear_quantum_probes,
    validate_nonlinear_pattern_results,
    validate_quantum_pattern_reviews,
)


def test_nonlinear_quantum_lab_records_interactions_against_linear_baseline():
    payload = build_nonlinear_quantum_pattern_lab()

    assert payload["tested_interaction_count"] > 0
    assert payload["candidate_input_count"] == payload["tested_interaction_count"]
    assert set(NONLINEAR_METHOD_FAMILIES).issubset(payload["nonlinear_method_families"])
    assert payload["linear_baseline_not_beat_count"] == payload["tested_interaction_count"]
    assert validate_nonlinear_pattern_results(payload) == []

    for result in payload["nonlinear_results"]:
        assert result["baseline"]["linear_pattern_id"] == result["source_linear_pattern_id"]
        assert result["nonlinear_method_type"] == "interaction_regime_path_review"
        assert result["nonlinear_tests"]["method_families"]
        assert "regime_dependence_score" in result["nonlinear_tests"]
        assert "path_dependence_score" in result["nonlinear_tests"]
        assert result["nonlinear_tests"]["overfit_controls"]["multiple_testing_penalty_applied"] is True
        assert result["decision"]["candidate_for_paper_route"] is False


def test_quantum_reviews_are_labeled_fallback_and_not_authority():
    payload = build_nonlinear_quantum_pattern_lab()

    assert payload["reviewed_pattern_count"] == payload["candidate_for_quantum_review_count"]
    assert payload["quantum_summary"]["quantum_backend"] in ALLOWED_QUANTUM_BACKENDS
    assert payload["quantum_summary"]["quantum_mode"] in ALLOWED_QUANTUM_MODES
    assert payload["quantum_summary"]["hardware_submission_allowed"] is False
    assert payload["quantum_summary"]["provider_call_allowed"] is False
    assert payload["quantum_review_is_not_trade_approval"] is True
    assert validate_quantum_pattern_reviews(payload) == []

    for review in payload["quantum_reviews"]:
        assert review["job_type"] in ALLOWED_QUANTUM_JOB_TYPES
        assert review["backend"] in ALLOWED_QUANTUM_BACKENDS
        assert review["quantum_mode"] in ALLOWED_QUANTUM_MODES
        assert review["hardware_submission_allowed"] is False
        assert review["hardware_submitted"] is False
        assert review["provider_call_allowed"] is False
        assert review["execution_allowed"] is False
        assert review["paper_order_allowed"] is False
        assert review["proof_credit_allowed"] is False
        assert review["quantum_usefulness"]["ambiguity_recorded"] is True
        assert review["quantum_usefulness"]["not_trade_confirmation"] is True


def test_nonlinear_quantum_lab_is_research_only_and_negative_probes_fail_closed():
    payload = build_nonlinear_quantum_pattern_lab()

    assert payload["authority_flags"] == NONLINEAR_AUTHORITY_FLAGS
    assert all(value is False for value in payload["authority"].values())
    assert payload["no_strategy_hypotheses_created"] is True
    assert payload["no_trade_candidates_created"] is True
    assert payload["no_paper_orders_created"] is True
    assert payload["no_proof_credit_granted"] is True
    assert payload["candidate_for_strategy_foundry_count"] == 0
    assert payload["dashboard_safe_summary"]["quantum_review_is_not_trade_confirmation"] is True

    for result in payload["nonlinear_results"]:
        assert result["candidate_for_paper_route"] is False
        assert result["candidate_for_strategy_foundry"] is False
        assert result["trade_candidate_created"] is False
        assert result["paper_order_created"] is False
        assert result["proof_credit_allowed"] is False
        assert all(result[flag] is False for flag in NONLINEAR_AUTHORITY_FLAGS)

    assert validate_negative_nonlinear_quantum_probes() == []
