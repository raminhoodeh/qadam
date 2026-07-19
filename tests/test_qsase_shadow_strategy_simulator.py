from orchestrator.qsase_shadow_strategy_simulator import (
    EVIDENCE_CLASSES,
    REPLAY_MODES,
    SHADOW_AUTHORITY_FLAGS,
    build_shadow_strategy_replay,
    build_shadow_variant_matrix,
    compare_actual_vs_hypothetical,
    score_shadow_variants,
    validate_negative_shadow_strategy_probes,
    validate_shadow_strategy_replay,
)


def test_shadow_strategy_simulator_records_modes_evidence_and_no_order_state():
    payload = build_shadow_strategy_replay()

    assert payload["replay_record_count"] > 0
    assert payload["variant_count"] == 3
    assert payload["evaluated_replay_count"] > 0
    assert (
        payload["active_replay_count"] + payload["blocked_replay_count"]
    ) == payload["replay_record_count"]
    assert payload["candidate_for_router_count"] == 0
    assert "historical_hypothesis_replay" in payload["replay_modes"]
    assert "forward_shadow_replay" in payload["replay_modes"]
    assert "counterfactual_strategy_replay" in payload["replay_modes"]
    assert validate_shadow_strategy_replay(payload) == []

    for record in payload["shadow_replay_records"]:
        assert record["replay_mode"] in REPLAY_MODES
        assert record["evidence_class"] in EVIDENCE_CLASSES
        assert record["time_window"]["decision_timestamps_point_in_time_safe"] is True
        assert record["source_refs"]
        assert record["decision"]["candidate_for_paper_review"] is False
        assert record["decision"]["paper_order_ready"] is False
        assert record["decision"]["proof_credit_ready"] is False
        assert record["hypothetical_decision"]["would_have_created_paper_order"] is False
        assert record["outcome"]["shadow_success_cannot_create_order"] is True
        assert record["outcome"]["shadow_success_cannot_create_proof_credit"] is True


def test_shadow_strategy_simulator_dashboard_matrix_and_comparison_are_safe():
    payload = build_shadow_strategy_replay()
    matrix = build_shadow_variant_matrix()
    comparison = compare_actual_vs_hypothetical(payload["shadow_replay_records"])
    scores = score_shadow_variants(payload["shadow_replay_records"])

    assert matrix["variant_count"] == len(matrix["variants"])
    assert all(variant["threshold_change_applied"] is False for variant in matrix["variants"])
    assert comparison["actual_vs_hypothetical_count"] == payload["replay_record_count"]
    assert comparison["actual_lifecycle_mutated"] is False
    assert comparison["paper_proof_ledger_mutated"] is False
    assert scores["candidate_for_router_count"] == payload["candidate_for_router_count"]
    assert payload["dashboard_safe_summary"]["authority_state"] == "shadow_replay_research_only_no_order"
    assert payload["dashboard_safe_summary"]["no_paper_orders_created"] is True
    assert payload["dashboard_safe_summary"]["no_proof_credit_granted"] is True


def test_shadow_strategy_simulator_authority_and_negative_probes():
    payload = build_shadow_strategy_replay()

    assert payload["authority_flags"] == SHADOW_AUTHORITY_FLAGS
    assert all(value is False for value in payload["authority"].values())
    assert payload["trade_candidate_created_count"] == 0
    assert payload["paper_order_created_count"] == 0
    assert payload["execution_intent_created_count"] == 0
    assert payload["broker_write_count"] == 0
    assert payload["proof_credit_allowed"] is False
    assert payload["live_capital_enabled"] is False
    assert payload["shadow_success_cannot_be_paper_order"] is True
    assert payload["shadow_success_cannot_be_paper_proof_ledger_credit"] is True

    for record in payload["shadow_replay_records"]:
        assert record["telegram_summary"]["review_only"] is True
        assert record["telegram_summary"]["command_disabled"] is True
        assert record["telegram_summary"]["contains_command"] is False
        assert record["telegram_summary"]["contains_broker_instruction"] is False
        assert all(record[flag] is False for flag in SHADOW_AUTHORITY_FLAGS)
        assert all(record["authority"][flag] is False for flag in SHADOW_AUTHORITY_FLAGS)

    for rejection in payload["shadow_rejections"]:
        assert rejection["candidate_for_router"] is False
        assert rejection["paper_order_created"] is False
        assert rejection["proof_credit_allowed"] is False

    assert validate_negative_shadow_strategy_probes() == []
