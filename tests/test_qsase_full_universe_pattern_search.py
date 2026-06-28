from orchestrator.qsase_full_universe_pattern_search import (
    FULL_UNIVERSE_AUTHORITY_FLAGS,
    SCAN_METHODS,
    build_full_universe_pattern_search,
    validate_full_universe_pattern_search,
    validate_negative_pattern_search_probes,
)


def test_full_universe_pattern_search_scans_full_matrix_and_methods():
    payload = build_full_universe_pattern_search()
    scope = payload["full_universe_scope"]
    method_names = {method["method"] for method in payload["scan_methods"]}

    assert payload["matrix_row_count"] == payload["relationship_count"]
    assert payload["matrix_row_count"] > 0
    assert scope["all_sources_scanned"] is True
    assert scope["all_markets_scanned"] is True
    assert scope["all_time_windows_scanned"] is True
    assert scope["strategy_sleeve_only_scan"] is False
    assert set(SCAN_METHODS).issubset(method_names)
    assert validate_full_universe_pattern_search(payload) == []


def test_full_universe_pattern_search_candidates_and_rejects_are_research_only():
    payload = build_full_universe_pattern_search()

    assert payload["candidate_pattern_count"] > 0
    assert payload["rejected_pattern_count"] > 0
    assert payload["patterns_are_not_strategies"] is True
    assert payload["no_strategy_hypotheses_created"] is True
    assert payload["no_trade_candidates_created"] is True
    assert payload["new_strategy_candidate_count"] == 0
    assert payload["authority_flags"] == FULL_UNIVERSE_AUTHORITY_FLAGS
    assert all(value is False for value in payload["authority"].values())

    for candidate in payload["candidate_patterns"]:
        assert candidate["matrix_row_ids"]
        assert candidate["pattern_not_strategy"] is True
        assert candidate["candidate_for_paper_route"] is False
        assert candidate["candidate_for_strategy_foundry"] is False
        assert candidate["new_strategy_candidate"] is False
        assert "strategy_foundry" not in candidate["next_required_review"]
        assert all(candidate[flag] is False for flag in FULL_UNIVERSE_AUTHORITY_FLAGS)

    for rejected in payload["rejected_patterns"]:
        assert rejected["rejection_reasons"]
        assert rejected["pattern_not_strategy"] is True
        assert all(rejected[flag] is False for flag in FULL_UNIVERSE_AUTHORITY_FLAGS)


def test_full_universe_pattern_search_evaluates_required_relationship_types_and_negative_probes():
    payload = build_full_universe_pattern_search()
    pattern_types = {candidate["pattern_type"] for candidate in payload["candidate_patterns"]} | {
        rejected["pattern_type"] for rejected in payload["rejected_patterns"]
    }

    assert "source_to_asset_lag" in pattern_types
    assert "source_cluster_to_asset" in pattern_types
    assert "source_to_source" in pattern_types
    assert "asset_to_asset" in pattern_types
    assert "regime_to_asset" in pattern_types
    assert payload["dashboard_safe_summary"]["no_trade_candidates_created"] is True
    assert validate_negative_pattern_search_probes() == []
