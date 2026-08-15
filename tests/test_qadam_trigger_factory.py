from orchestrator.qadam_trigger_factory import (
    build_event_triggers,
    build_market_dislocations,
    build_regime_observations,
)

NOW = "2026-08-08T12:00:00+00:00"


def _source_contract() -> dict:
    return {
        "sources": [
            {
                "source_key": "rss",
                "canonical_source_key": "rss",
                "availability_state": "live_fresh",
                "allowed_roles": ["current_trigger"],
                "trust_score": 0.78,
            },
            {
                "source_key": "reddit",
                "canonical_source_key": "reddit",
                "availability_state": "supplemental_current",
                "allowed_roles": ["supplemental_context", "negative_control"],
                "trust_score": 0.46,
            },
        ]
    }


def test_event_builder_accepts_relevant_defence_event_and_rejects_broad_social_overlap() -> None:
    goals = [
        {
            "goal_id": "g1",
            "origin": "live_source",
            "created_at": "2026-08-08T10:00:00+00:00",
            "source_event_refs": ["rss:e1"],
            "hypothesis": "defence observation may become relevant if independent sources corroborate it: New defense procurement deal",
        },
        {
            "goal_id": "g2",
            "origin": "live_source",
            "created_at": "2026-08-08T10:00:00+00:00",
            "source_event_refs": ["reddit:e2"],
            "hypothesis": "defence observation may become relevant if independent sources corroborate it: Retail attention changed",
        },
    ]
    packets = {
        "recent_packets": [
            {
                "research_goal_id": "g1",
                "research_goal_origin": "live_source",
                "market_channel": "defence_geopolitics",
                "hypothesis": goals[0]["hypothesis"],
                "watched_instruments": ["XAR"],
                "generated_at": NOW,
                "source_taxonomy": [{"source_key": "rss", "observed_in_goal": True}],
            },
            {
                "research_goal_id": "g2",
                "research_goal_origin": "live_source",
                "market_channel": "defence_geopolitics",
                "hypothesis": goals[1]["hypothesis"],
                "watched_instruments": ["XAR"],
                "generated_at": NOW,
                "source_taxonomy": [{"source_key": "reddit", "observed_in_goal": True}],
            },
        ]
    }
    triggers, rejections = build_event_triggers(
        packets, goals, _source_contract(), generated_at=NOW
    )
    assert len(triggers) == 1
    assert triggers[0]["strategy_family_id"] == "defence_repricing_geopolitical_watch"
    assert any("no_explicit_strategy_causal_relevance" in row["reasons"] for row in rejections)


def test_semiconductor_capacity_event_has_structured_causal_expression() -> None:
    goal = {
        "goal_id": "semis-capacity",
        "origin": "live_source",
        "created_at": "2026-08-08T10:00:00+00:00",
        "source_event_refs": ["rss:semis-capacity"],
        "hypothesis": (
            "semiconductor observation may become relevant if independent sources "
            "corroborate it: New semiconductor fabrication plant capacity announced"
        ),
    }
    packets = {
        "recent_packets": [
            {
                "research_goal_id": goal["goal_id"],
                "research_goal_origin": "live_source",
                "market_channel": "semiconductors",
                "hypothesis": goal["hypothesis"],
                "watched_instruments": ["SMH"],
                "generated_at": NOW,
                "source_taxonomy": [
                    {"source_key": "rss", "observed_in_goal": True}
                ],
            }
        ]
    }

    triggers, rejections = build_event_triggers(
        packets, [goal], _source_contract(), generated_at=NOW
    )

    assert rejections == []
    trigger = triggers[0]
    causal = trigger["causal_classification"]
    assert causal["mechanism"] == "fabrication_capacity_or_investment_expansion"
    assert causal["direction_clue"] == "positive_for_strategy_expression"
    assert causal["invalidation"]
    assert trigger["instrument_expressions"]["SMH"]["role"] == (
        "semiconductor_sector_proxy"
    )


def test_silver_regime_is_numeric_and_inactive_is_not_missing() -> None:
    records = []
    for symbol, move, volume in (
        ("SIL", 2.0, 1.4),
        ("SLV", 1.5, 1.2),
        ("GLD", 0.5, 1.0),
        ("SPY", 0.2, 1.0),
    ):
        records.append(
            {
                "symbol": symbol,
                "provider_backed": True,
                "percent_move": move,
                "volume_ratio": volume,
                "observed_at": "2026-08-08T10:00:00+00:00",
            }
        )
    market = {
        "recent_packets": [
            {
                "packet_role": "universal_current_market_context",
                "price_volume_context": {"records": records},
            }
        ]
    }
    macro = [
        {"series_id": "DGS10", "value": 4.5, "previous_value": 4.5, "observed_at": NOW},
        {"series_id": "VIXCLS", "value": 15.0, "previous_value": 15.0, "observed_at": NOW},
        {
            "series_id": "EXR.D.USD.EUR.SP00.A",
            "value": 1.15,
            "previous_value": 1.15,
            "observed_at": NOW,
        },
    ]
    rows = build_regime_observations(market, macro, {"recent_packets": []}, generated_at=NOW)
    assert rows[0]["numeric_measurements"]["regime_score"] is not None
    assert rows[0]["regime_state"] in {"active", "inactive"}


def test_dislocation_requires_compatible_settlement_rules() -> None:
    rows, _rejections = build_market_dislocations(
        [
            {
                "venue": "kalshi",
                "title": "Will event X happen?",
                "contract_id": "k1",
                "probability": 0.60,
                "liquidity": 100,
                "observed_at": NOW,
                "settlement_rule_hash": "same",
            },
            {
                "venue": "polymarket",
                "title": "Will event X happen?",
                "contract_id": "p1",
                "probability": 0.48,
                "liquidity": 100,
                "observed_at": NOW,
                "settlement_rule_hash": "same",
            },
        ],
        generated_at=NOW,
    )
    assert len(rows) == 1
    assert round(rows[0]["probability_gap"], 2) == 0.12
    assert rows[0]["listed_proxy"] is None
