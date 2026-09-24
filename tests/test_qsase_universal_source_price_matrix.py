import pytest

from orchestrator import qsase_universal_source_price_matrix as matrix_module
from orchestrator.qsase_universal_source_price_matrix import (
    MATRIX_AUTHORITY_FLAGS,
    TIME_WINDOWS,
    build_qsase_universal_source_price_matrix,
    build_source_price_edges,
    validate_negative_matrix_probes,
    validate_qsase_universal_source_price_matrix,
)


@pytest.fixture(autouse=True)
def isolated_declared_universe(monkeypatch):
    # A declared, deliberately unavailable catalogue, not live provider evidence.
    sources = [{"source_key": key, "state": "degraded", "provider_backed_observation": False}
               for key in ["ais_or_shipping", "social.rss", *[f"fixture.source_{i}" for i in range(39)]]]
    documents = {
        "qsase_backtest_universe_freeze.json": {"sources": sources},
        "cockpit-status.json": {"mission_control": {"strategy": {"strategy_families": [
            {"instrument": "SPY", "route_fit": "clean_alpaca_paper_proxy_fit"}]}}},
        "market_context_packet.json": {"recent_packets": [
            {"market_channel": "macro_watchlist", "watched_instruments": ["SPY"]}]},
    }
    monkeypatch.setattr(matrix_module, "_read_json", lambda path: documents.get(path.name, {}))
    monkeypatch.setattr(matrix_module, "_read_jsonl", lambda *args, **kwargs: [])


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


def market_packet(price, observed_at, *, provider_backed=True, **overrides):
    return {
        "generated_at": "2026-09-24T18:00:00+00:00",
        "packet_role": "universal_current_market_context",
        "price_volume_context": {"records": [{
            "symbol": "SMH", "current_price": price, "last_close": 590.0,
            "provider": "alpaca_market_data_v2", "provider_backed": provider_backed,
            "quote_actionable": True, "quote_observed_at": observed_at,
            "rolling_volatility_20d": 0.02, "volume_ratio": 0.8,
            "session_state": "regular_session", **overrides,
        }]},
    }


@pytest.mark.parametrize("reverse", [False, True])
def test_supplemental_indicators_cannot_erase_price_snapshot(reverse):
    price = market_packet(597.9, "2026-09-24T17:51:00+00:00")
    technical = {"generated_at": "2026-09-24T18:00:00+00:00",
                 "technical_context": {"provider": "tradingview_mcp", "records": [
                     {"symbol": "SMH", "technical_score": 0.6}]},
                 "orderflow_context": {"records": [{"symbol": "SMH", "orderflow_score": 0.5}]}}
    packets = [price, technical]
    record = matrix_module._collect_market_records({"recent_packets": packets[::-1] if reverse else packets})["SMH"]
    assert record["last_close"] == 597.9
    assert record["provider"] == "alpaca_market_data_v2"
    assert record["market_observation_timestamp"] == "2026-09-24T17:51:00+00:00"
    assert record["rolling_volatility_20d"] == 0.02
    assert record["volume_ratio"] == 0.8
    assert record["technical_score"] == 0.6
    assert record["orderflow_score"] == 0.5


@pytest.mark.parametrize("reverse", [False, True])
def test_latest_provider_snapshot_wins_without_borrowing_old_fields(reverse):
    old = market_packet(580, "2026-09-24T17:45:00+00:00")
    new = market_packet(597.9, "2026-09-24T17:51:00+00:00", rolling_volatility_20d=None)
    sample = market_packet(900, "2026-09-24T18:00:00+00:00", provider_backed=False)
    packets = [new, sample, old]
    record = matrix_module._collect_market_records({"recent_packets": packets[::-1] if reverse else packets})["SMH"]
    assert record["last_close"] == 597.9
    assert record["rolling_volatility_20d"] is None


def test_technical_only_records_cannot_invent_price_or_market_timestamp():
    record = matrix_module._collect_market_records({"recent_packets": [{
        "generated_at": "2026-09-24T18:00:00+00:00",
        "technical_context": {"records": [{"symbol": "SMH", "technical_score": 0.6}]},
    }]})["SMH"]
    assert record.get("last_close") is None
    assert record.get("market_observation_timestamp") is None


def test_cockpit_selected_instrument_cannot_narrow_declared_universe():
    packet = market_packet(150.0, "2026-09-24T17:51:00+00:00")
    packet["price_volume_context"]["records"][0]["symbol"] = "USO"
    context = {
        "cockpit_status": {"mission_control": {"strategy": {
            "strategy_families": [{"instrument": "BNO", "route_fit": "conditional_paper_proxy_fit"}],
            "universe": ["crude oil"],
        }}},
        "market_context": {"recent_packets": [packet]},
        "universe_freeze": {"instruments": [
            {"symbol": symbol, "instrument_family": "crude_oil", "paper_route_available": True}
            for symbol in ["BNO", "USO", "XLE", "CL=F"]
        ] + [{"symbol": "SPY", "instrument_family": "macro_watchlist", "paper_route_available": False}]},
    }
    result = matrix_module.build_qsase_trading_universe(context, "2026-09-24T18:00:00+00:00")
    rows = {row["symbol"]: row for row in result["instruments"]}
    assert set(rows) == {"BNO", "USO", "XLE", "CL=F", "SPY"}
    assert rows["BNO"]["market_family"] == "crude_oil"
    assert rows["USO"]["price_or_odds_value"] == 150.0
    assert rows["USO"]["rolling_volatility_20d"] == 0.02
    assert rows["USO"]["paper_route_available"] is True
    assert rows["XLE"]["paper_route_available"] is True
    assert rows["XLE"]["market_observation_timestamp"] is None
    assert rows["SPY"]["paper_route_available"] is False
    assert rows["CL=F"]["paper_route_available"] is False
    assert all(row["paper_order_allowed"] is False for row in rows.values())
