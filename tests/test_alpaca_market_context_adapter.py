from __future__ import annotations

from orchestrator.alpaca_market_context_adapter import (
    ALPACA_MARKET_CONTEXT_PROVIDER,
    build_alpaca_market_context_records,
)
from orchestrator.market_context import (
    _select_current_research_goals,
    build_market_context_packet,
)


def test_builds_exact_provider_backed_price_volume_risk_context() -> None:
    bars = {
        "bars": {
            "BNO": [
                {
                    "t": f"2026-07-{day:02d}T20:00:00Z",
                    "c": 30.0 + day / 10,
                    "v": 100_000 + day * 1_000,
                }
                for day in range(1, 23)
            ]
        }
    }
    quotes = {
        "quotes": {
            "BNO": {
                "t": "2026-07-22T18:59:59Z",
                "bp": 32.19,
                "ap": 32.21,
            }
        }
    }

    records = build_alpaca_market_context_records(
        {"BNO", "CL=F", "KALSHI:EVENTS"},
        bars,
        quotes,
        generated_at="2026-07-22T19:00:02+00:00",
    )

    assert len(records) == 1
    record = records[0]
    assert record["symbol"] == "BNO"
    assert record["provider"] == ALPACA_MARKET_CONTEXT_PROVIDER
    assert record["provider_backed"] is True
    assert record["read_only_market_data"] is True
    assert record["broker_endpoint_used"] is False
    assert record["current_price"] == 32.2
    assert record["volume_ratio"] is not None
    assert record["rolling_volatility_20d"] is not None
    assert record["annualized_volatility"] is not None
    assert record["average_daily_dollar_volume"] > 0
    assert 0 < record["spread_bps"] < 100
    assert record["quote_state"] == "fresh_regular_session_quote"
    assert record["quote_actionable"] is True
    assert record["session_state"] == "regular_session"


def test_rejects_futures_and_prediction_market_identifiers_from_stock_endpoint() -> None:
    records = build_alpaca_market_context_records(
        {"CL=F", "KALSHI:EVENTS"},
        {"bars": {}},
        {"quotes": {}},
        generated_at="2026-07-22T20:00:02+00:00",
    )

    assert records == []


def test_off_session_quote_is_context_but_not_actionable_spread_evidence() -> None:
    bars = {
        "bars": {
            "USO": [
                {"t": "2026-07-30T04:00:00Z", "c": 126.0, "v": 100_000},
                {"t": "2026-07-31T04:00:00Z", "c": 128.0, "v": 120_000},
            ]
        }
    }
    quotes = {
        "quotes": {
            "USO": {
                "t": "2026-07-31T20:00:00Z",
                "bp": 125.0,
                "ap": 132.0,
            }
        }
    }

    record = build_alpaca_market_context_records(
        {"USO"},
        bars,
        quotes,
        generated_at="2026-08-02T09:00:00+00:00",
    )[0]

    assert record["spread_bps"] is None
    assert record["observed_non_actionable_spread_bps"] > 100
    assert record["quote_state"] == "outside_regular_session"
    assert record["quote_actionable"] is False
    assert record["session_state"] == "outside_regular_session"


def test_market_context_prefers_exact_alpaca_records_without_granting_authority() -> None:
    record = {
        "source": ALPACA_MARKET_CONTEXT_PROVIDER,
        "symbol": "USO",
        "last_close": 125.0,
        "current_price": 125.01,
        "volume_ratio": 1.2,
        "rolling_volatility_20d": 0.02,
        "annualized_volatility": 0.317,
        "average_daily_dollar_volume": 25_000_000.0,
        "spread_bps": 1.6,
        "market_state": "provider_latest_read_only_observation",
        "provider_backed": True,
        "read_only_market_data": True,
        "broker_endpoint_used": False,
    }
    packet = build_market_context_packet(
        {
            "goal_id": "goal:oil",
            "status": "active",
            "market_channel": "crude_oil",
            "hypothesis": "Oil reprices after a fresh disruption catalyst.",
            "watched_instruments": ["CL=F", "USO"],
            "required_sources": ["conflict_tracker"],
            "source_event_refs": ["conflict_tracker:event-1"],
            "source_quorum_score": 1.0,
            "latency_freshness_score": 1.0,
            "market_confirmation_score": 1.0,
        },
        source_results=[{"source_key": "conflict_tracker", "status": "ok"}],
        alpaca_context={"status": "ok", "records": [record]},
        alpaca_status={"status": "ok"},
        yahoo_envelope={"events": []},
        yahoo_status={"status": "disabled"},
        tradingview_context={"technical_context_refs": []},
        tradingview_status={"status": "unavailable"},
        bookmap_context={"orderflow_context_refs": []},
        bookmap_status={"status": "unavailable"},
        paper_context={"status": "ok", "mode": "paper"},
        durable_replay_summary={"replay_status": "not_requested"},
        generated_at="2026-07-22T19:00:02+00:00",
    )

    price_context = packet["price_volume_context"]
    assert price_context["provider"] == ALPACA_MARKET_CONTEXT_PROVIDER
    assert price_context["canonical_source"] is True
    assert price_context["records"] == [record]
    assert price_context["paper_order_allowed"] is False
    assert price_context["broker_write_allowed"] is False
    assert packet["paper_order_allowed"] is False


def test_current_goal_selection_excludes_samples_and_preserves_source_diversity() -> None:
    goals = [
        {
            "goal_id": "sample",
            "origin": "sample_source",
            "market_channel": "macro_liquidity",
            "source_event_refs": ["ecb:sample"],
            "updated_at": "2026-08-02T09:59:00+00:00",
        },
        {
            "goal_id": "ecb-old",
            "origin": "live_source",
            "market_channel": "macro_liquidity",
            "source_event_refs": ["ecb:event:old"],
            "updated_at": "2026-08-02T09:00:00+00:00",
        },
        {
            "goal_id": "ecb-new",
            "origin": "live_source",
            "market_channel": "macro_liquidity",
            "source_event_refs": ["ecb:event:new"],
            "updated_at": "2026-08-02T10:00:00+00:00",
        },
        {
            "goal_id": "conflict",
            "origin": "live_source",
            "market_channel": "energy_transport",
            "source_event_refs": ["conflict_tracker:event:new"],
            "updated_at": "2026-08-02T09:30:00+00:00",
        },
    ]

    selected = _select_current_research_goals(goals, limit=10)

    assert [row["goal_id"] for row in selected] == ["ecb-new", "conflict"]
