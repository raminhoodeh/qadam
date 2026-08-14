from __future__ import annotations

from orchestrator.qadam_decision_evidence_packets import (
    build_decision_evidence_packets_from_inputs,
    validate_decision_evidence_packets,
)

NOW = "2026-08-08T12:00:00+00:00"


def _hypothesis():
    return {
        "generated_at": NOW,
        "hypothesis_id": "hypothesis:test",
        "hypothesis_state": "ready_for_akber_review",
        "akber_review_allowed": True,
        "evidence_class": "experimental_unvalidated",
        "experimental_tier": "discovery_micro",
        "edge_lineage": {"edge_id": None, "edge_registry_reference": {"complete": False}},
        "pattern_lineage": {
            "complete": True,
            "pattern_relationship_id": "pattern:test",
            "score_id": "score:test",
            "source_confirmation_mode": "profile_specific_current_trigger_plus_one_live_market_confirmation",
            "evidence_profile": "event_catalyst",
            "fresh_support_sources": ["rss"],
            "fresh_quorum_sources": [],
            "provider_availability_is_not_trigger": True,
        },
        "research_goal_lineage": {"research_goal_id": "goal:test"},
        "candidate_identity_material": {"candidate_identity_id": "identity:test"},
        "strategy_mapping": {"strategy_family_id": "semiconductor_policy_options_asymmetry"},
        "instrument_proxy_mapping": {
            "observed_instrument": "SMH",
            "execution_proxy": "SMH",
            "proxy_basis": "direct",
            "proxy_review_required": False,
        },
        "direction_horizon": {
            "direction": "short",
            "horizon": "5d_forward",
            "direction_resolution_id": "resolution:test",
        },
        "expected_edge_range": {"net_expectancy": 0.002, "not_a_validated_expectancy": True},
        "invalidation_exit": {"invalidation_conditions": ["event reverses"]},
        "risk_concept": {"expected_reward_to_risk": 1.5},
        "freshness": {"expires_at": "2026-08-13T12:00:00+00:00"},
    }


def _artifacts(market_state="closed", session_state=None):
    return {
        "market_context": {
            "recent_packets": [
                {
                    "packet_id": "market:test",
                    "packet_role": "universal_current_market_context",
                    "generated_at": NOW,
                    "watched_instruments": ["SMH"],
                    "price_volume_context": {
                        "status": "ok",
                        "provider": "alpaca_market_data_v2",
                        "records": [
                            {
                                "symbol": "SMH",
                                "last_close": 100.0,
                                "rolling_volatility_20d": 0.02,
                                "volume_ratio": 1.2,
                                "spread_bps": 5.0,
                                "market_state": market_state,
                                "session_state": session_state,
                            }
                        ],
                    },
                    "technical_context": {"status": "unavailable", "records": []},
                    "orderflow_context": {"status": "unavailable", "records": []},
                }
            ]
        },
        "signal_integrity_reviews": [],
        "alpaca_mirror": {
            "status": "ok",
            "write_authority": False,
            "snapshot": {
                "mode": "paper",
                "connection_status": "alpaca_paper_readonly_connected",
                "observed_at": NOW,
            },
        },
        "tradingview_status": {},
        "tradingview_context": {},
        "bookmap_context": {"sample": True},
        "nonlinear_comparisons": [],
    }


def test_closed_market_is_inactive_not_adverse_and_packet_is_generation_bound() -> None:
    resolution = {
        "direction_resolution_id": "resolution:test",
        "score_id": "score:test",
        "actionable_direction": "short",
        "evidence_ids": ["trigger:test"],
    }
    trigger = {
        "trigger_id": "trigger:test",
        "trigger_state": "active",
        "source_keys": ["rss"],
        "available_at": NOW,
    }
    state = build_decision_evidence_packets_from_inputs(
        [_hypothesis()], [resolution], [trigger], [], [], _artifacts(), generated_at=NOW
    )
    assert validate_decision_evidence_packets(state) == []
    packet = state["packets"][0]
    assert packet["market_session"]["state"] == "closed_inactive"
    assert packet["evidence_states"]["liquidity_and_spread"] == "inactive"
    assert packet["mixed_generation_join"] is False


def test_generation_identity_is_stable_when_only_compiler_time_changes() -> None:
    resolution = {
        "direction_resolution_id": "resolution:test",
        "score_id": "score:test",
        "actionable_direction": "short",
        "evidence_ids": ["trigger:test"],
    }
    trigger = {
        "trigger_id": "trigger:test",
        "trigger_state": "active",
        "source_keys": ["rss"],
        "available_at": NOW,
    }
    first = build_decision_evidence_packets_from_inputs(
        [_hypothesis()], [resolution], [trigger], [], [], _artifacts(), generated_at=NOW
    )
    second = build_decision_evidence_packets_from_inputs(
        [_hypothesis()],
        [resolution],
        [trigger],
        [],
        [],
        _artifacts(),
        generated_at="2026-08-08T12:05:00+00:00",
    )

    assert (
        first["summary"]["decision_generation_id"]
        == second["summary"]["decision_generation_id"]
    )


def test_generation_identity_changes_when_evidence_changes() -> None:
    resolution = {
        "direction_resolution_id": "resolution:test",
        "score_id": "score:test",
        "actionable_direction": "short",
        "evidence_ids": ["trigger:test"],
    }
    trigger = {
        "trigger_id": "trigger:test",
        "trigger_state": "active",
        "source_keys": ["rss"],
        "available_at": NOW,
    }
    changed = dict(trigger)
    changed["source_keys"] = ["rss", "gdelt"]
    first = build_decision_evidence_packets_from_inputs(
        [_hypothesis()], [resolution], [trigger], [], [], _artifacts(), generated_at=NOW
    )
    second = build_decision_evidence_packets_from_inputs(
        [_hypothesis()], [resolution], [changed], [], [], _artifacts(), generated_at=NOW
    )

    assert (
        first["summary"]["decision_generation_id"]
        != second["summary"]["decision_generation_id"]
    )


def test_experimental_hypothesis_without_resolution_fails_closed() -> None:
    state = build_decision_evidence_packets_from_inputs(
        [_hypothesis()], [], [], [], [], _artifacts(), generated_at=NOW
    )
    assert state["packets"] == []
    assert state["rejections"][0]["reasons"] == ["experimental_direction_resolution_missing"]
    assert validate_decision_evidence_packets(state) == []


def test_regular_session_field_makes_fresh_spread_actionable() -> None:
    resolution = {
        "direction_resolution_id": "resolution:test",
        "score_id": "score:test",
        "actionable_direction": "short",
        "evidence_ids": ["trigger:test"],
    }
    trigger = {
        "trigger_id": "trigger:test",
        "trigger_state": "active",
        "source_keys": ["rss"],
        "available_at": NOW,
    }
    state = build_decision_evidence_packets_from_inputs(
        [_hypothesis()],
        [resolution],
        [trigger],
        [],
        [],
        _artifacts("provider_latest_read_only_observation", "regular_session"),
        generated_at=NOW,
    )
    assert validate_decision_evidence_packets(state) == []
    packet = state["packets"][0]
    assert packet["market_session"]["state"] == "open_actionable"
    assert packet["evidence_states"]["liquidity_and_spread"] == "available"
