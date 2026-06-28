from orchestrator.qsase_strategy_router import (
    ROUTER_AUTHORITY_FLAGS,
    ROUTER_STATES,
    build_paper_review_candidate_handoff,
    build_strategy_router_decisions,
    validate_negative_strategy_router_probes,
    validate_strategy_router_decisions,
)


def test_strategy_router_routes_every_input_with_specific_reasons_and_vetoes():
    payload = build_strategy_router_decisions()

    assert payload["strategy_input_count"] > 0
    assert payload["strategy_input_count"] == len(payload["router_decisions"])
    assert payload["paper_review_candidate_count"] == 0
    assert payload["blocked_safety_boundary_count"] > 0
    assert payload["hard_veto_count"] > 0
    assert payload["why_not_trading_now"]["reason"]
    assert validate_strategy_router_decisions(payload) == []

    for decision in payload["router_decisions"]:
        output = decision["decision"]["router_output"]
        assert output in ROUTER_STATES
        assert decision["decision"]["reason"]
        assert decision["decision"]["why_not_trading_now"]
        assert decision["hard_vetoes"] or decision["soft_blockers"]
        assert output != "paper_review_candidate"
        assert decision["paper_review_candidate_handoff"] is None


def test_strategy_router_scoreboard_why_not_and_dashboard_are_safe():
    payload = build_strategy_router_decisions()
    top_decision = payload["router_decisions"][0]

    assert payload["scoreboard"]["ranked_count"] == payload["strategy_input_count"]
    assert payload["scoreboard"]["top_ranked_strategy"]
    assert payload["why_not_trading_now"]["blocking_layer"] == "strategy_router"
    assert payload["why_not_trading_now"]["paper_order_created"] is False
    assert payload["why_not_trading_now"]["proof_credit_allowed"] is False
    assert payload["dashboard_safe_summary"]["authority_state"] == "strategy_router_no_order_authority"
    assert payload["dashboard_safe_summary"]["no_paper_orders_created"] is True
    assert payload["dashboard_safe_summary"]["no_proof_credit_granted"] is True
    assert top_decision["scores"]["router_total_score"] >= 0
    assert top_decision["hard_vetoes"] or top_decision["soft_blockers"]
    assert build_paper_review_candidate_handoff(top_decision) is None


def test_strategy_router_has_no_order_authority_and_negative_probes():
    payload = build_strategy_router_decisions()

    assert payload["authority_flags"] == ROUTER_AUTHORITY_FLAGS
    assert all(value is False for value in payload["authority"].values())
    assert payload["trade_candidate_created"] is False
    assert payload["qualified_setup_created"] is False
    assert payload["risk_handoff_allowed"] is False
    assert payload["execution_allowed"] is False
    assert payload["paper_order_allowed"] is False
    assert payload["broker_write_allowed"] is False
    assert payload["proof_credit_allowed"] is False
    assert payload["live_capital_enabled"] is False

    for decision in payload["router_decisions"]:
        assert decision["telegram_summary"]["review_only"] is True
        assert decision["telegram_summary"]["command_disabled"] is True
        assert decision["telegram_summary"]["contains_command"] is False
        assert decision["telegram_summary"]["contains_broker_instruction"] is False
        assert all(decision[flag] is False for flag in ROUTER_AUTHORITY_FLAGS)
        assert all(decision["authority"][flag] is False for flag in ROUTER_AUTHORITY_FLAGS)

    assert validate_negative_strategy_router_probes() == []
