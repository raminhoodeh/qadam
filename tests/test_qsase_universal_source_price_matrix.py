from orchestrator.qsase_universal_source_price_matrix import (
    MATRIX_AUTHORITY_FLAGS,
    TIME_WINDOWS,
    build_qsase_universal_source_price_matrix,
    build_source_price_edges,
    validate_negative_matrix_probes,
    validate_qsase_universal_source_price_matrix,
)


def test_qsase_matrix_builds_full_source_market_window_cross_product():
    payload = build_qsase_universal_source_price_matrix()
    edges = build_source_price_edges(
        payload["source_universe"],
        payload["trading_universe"],
        payload["generated_at"],
    )
    scope = payload["matrix_scope"]

    assert scope["all_sources_cross_all_markets"] is True
    assert scope["time_windows"] == TIME_WINDOWS
    assert scope["matrix_row_count"] == len(edges)
    assert scope["expected_row_count"] == (
        payload["source_universe"]["source_count"]
        * payload["trading_universe"]["watched_market_count"]
        * len(TIME_WINDOWS)
    )
    assert validate_qsase_universal_source_price_matrix(payload, edges) == []


def test_qsase_matrix_preserves_unavailable_members_of_frozen_source_universe():
    payload = build_qsase_universal_source_price_matrix()
    source_keys = {
        source["source_key"] for source in payload["source_universe"]["sources"]
    }

    assert payload["source_universe"]["source_count"] == 41
    assert {"ais_or_shipping", "social.rss"} <= source_keys


def test_qsase_matrix_keeps_sources_markets_and_rows_non_authoritative():
    payload = build_qsase_universal_source_price_matrix()
    edges = build_source_price_edges(
        payload["source_universe"],
        payload["trading_universe"],
        payload["generated_at"],
    )

    assert payload["authority_flags"] == MATRIX_AUTHORITY_FLAGS
    assert all(value is False for value in payload["authority"].values())
    assert payload["no_strategy_hypotheses_created"] is True
    assert payload["no_trade_candidates_created"] is True
    assert payload["no_paper_orders_created"] is True
    assert payload["no_proof_credit_granted"] is True
    assert all(edge["strategy_labels"] == [] for edge in edges[:50])
    assert all(edge["execution_allowed"] is False for edge in edges[:50])
    assert all(edge["proof_credit_allowed"] is False for edge in edges[:50])


def test_qsase_matrix_quorum_paperability_and_negative_probes():
    payload = build_qsase_universal_source_price_matrix()
    sources = payload["source_universe"]["sources"]
    instruments = payload["trading_universe"]["instruments"]

    assert all(
        source["source_quorum_contribution"]["can_contribute"] is False
        for source in sources
        if source["credential_gated"] or source["state"] == "degraded" or source["supplemental_context_only"]
    )
    assert all(
        source["source_quorum_contribution"]["can_contribute"] is False
        for source in sources
        if source["provider_backed_observation"] is not True
        or source["freshness_status"] not in {"fresh", "recent"}
    )
    assert any(source["supplemental_context_only"] for source in sources)
    assert any(instrument["paper_route_available"] for instrument in instruments)
    assert all(instrument["paper_order_allowed"] is False for instrument in instruments)
    assert all(instrument["live_capital_enabled"] is False for instrument in instruments)
    assert validate_negative_matrix_probes() == []
