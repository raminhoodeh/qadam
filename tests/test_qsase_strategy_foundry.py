from orchestrator.qsase_strategy_foundry import (
    FOUNDRY_AUTHORITY_FLAGS,
    KNOWN_STRATEGY_FAMILIES,
    build_strategy_hypotheses,
    map_patterns_to_strategy_families,
    reject_unfit_strategy_hypotheses,
    validate_negative_strategy_foundry_probes,
    validate_strategy_hypotheses,
)


def test_strategy_foundry_maps_inputs_and_preserves_rejections():
    payload = build_strategy_hypotheses()

    assert payload["input_pattern_count"] > 0
    assert payload["strategy_family_map"]["known_families"]
    assert payload["strategy_family_map"]["pattern_family_mappings"]
    assert payload["rejected_pattern_count"] == len(payload["rejected_strategy_hypotheses"])
    assert payload["shadow_only_monitor_count"] == sum(
        record.get("decision_type") == "shadow_only_monitor"
        for record in payload["rejected_strategy_hypotheses"]
    )
    assert payload["paper_review_candidate_count"] == 0
    assert validate_strategy_hypotheses(payload) == []

    for rejected in payload["rejected_strategy_hypotheses"]:
        assert rejected["source_price_pattern_lineage"]["nonlinear_pattern_ids"]
        assert rejected["research_goal_lineage"]["research_goal_id"]
        assert rejected["candidate_identity"]["candidate_identity_key"]
        assert rejected["strategy_family"]["hypothesis_only"] is True
        assert rejected["rejection_reasons"]
        assert rejected["paperability"]["paper_order_allowed"] is False


def test_strategy_foundry_does_not_create_trades_setups_or_orders():
    payload = build_strategy_hypotheses()

    assert payload["authority_flags"] == FOUNDRY_AUTHORITY_FLAGS
    assert all(value is False for value in payload["authority"].values())
    assert payload["strategy_hypotheses_are_not_trades"] is True
    assert payload["strategy_hypotheses_are_not_qualified_setups"] is True
    assert payload["strategy_hypotheses_are_not_orders"] is True
    assert payload["trade_candidate_created"] is False
    assert payload["qualified_setup_created"] is False
    assert payload["paper_order_allowed"] is False
    assert payload["proof_credit_allowed"] is False
    assert payload["live_capital_enabled"] is False
    assert payload["dashboard_safe_summary"]["authority_state"] == "strategy_hypothesis_only_no_execution"

    for hypothesis in payload["strategy_hypotheses"]:
        assert hypothesis["authority"]["not_trade_candidate"] is True
        assert hypothesis["authority"]["not_qualified_setup"] is True
        assert hypothesis["authority"]["not_order"] is True
        assert hypothesis["route_readiness"]["akber_filter_passed"] is False
        assert hypothesis["route_readiness"]["shadow_replay_executed"] is False
        assert hypothesis["route_readiness"]["paperops_direct_handoff_allowed"] is False
        assert all(hypothesis[flag] is False for flag in FOUNDRY_AUTHORITY_FLAGS)

    for rejected in payload["rejected_strategy_hypotheses"]:
        assert rejected["trade_candidate_created"] is False
        assert rejected["qualified_setup_created"] is False
        assert rejected["paper_order_created"] is False
        assert rejected["paperops_direct_handoff_allowed"] is False
        assert all(rejected[flag] is False for flag in FOUNDRY_AUTHORITY_FLAGS)


def test_strategy_foundry_family_mapping_and_negative_probes():
    payload = build_strategy_hypotheses()
    mappings = map_patterns_to_strategy_families(
        payload["strategy_family_map"]["pattern_family_mappings"],
        KNOWN_STRATEGY_FAMILIES,
    )

    assert isinstance(mappings, list)
    assert reject_unfit_strategy_hypotheses(payload["strategy_hypotheses"]) == []
    assert validate_negative_strategy_foundry_probes() == []
