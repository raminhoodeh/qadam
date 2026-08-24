from __future__ import annotations

from copy import deepcopy
import json

from orchestrator.qadam_decision_transaction import (
    SCHEMA_VERSION as DECISION_SCHEMA_VERSION,
    migrate_decision_transaction_payload,
)
from orchestrator.qadam_layered_market_judgment import (
    _operator_health_snapshot,
    _provider_capabilities,
    build_activity_quality,
    build_delayed_entry_queue,
    build_market_judgment,
    canonical_strategy_id,
    validate_layered_state,
)
from orchestrator.qadam_portfolio_risk_engine import (
    default_portfolio_policy,
    evaluate_position_size,
)
from orchestrator.qadam_router_v3_paperops import route_setup


NOW = "2026-08-20T14:00:00+00:00"


def _envelope(*, missing: list[str], session_state: str = "regular_session") -> dict:
    evidence = {
        field: {
            "available": field not in missing,
            "state": "missing" if field in missing else "available",
            "source_refs": [f"provider:{field}"] if field not in missing else [],
            "provider": f"provider:{field}",
            "value": 1.0 if field not in missing else None,
        }
        for field in (
            "source_price_context",
            "fresh_catalyst",
            "technical_confirmation",
            "volume_or_flow_confirmation",
            "volatility_context",
            "pricing_gap_evidence",
            "nonlinear_quantum_review",
            "risk_reward_context",
            "invalidation_clarity",
            "liquidity_and_spread",
            "paperability_proxy",
        )
    }
    return {
        "envelope_id": "envelope:test",
        "generated_at": NOW,
        "identity": {
            "research_goal_id": "goal:test",
            "strategy_version_id": "strategy-version:test",
        },
        "generation": {
            "decision_generation_id": "generation:test",
            "decision_at": NOW,
        },
        "strategy": {
            "strategy_family_id": "semiconductor_policy_asymmetry",
            "falsifier": "The current trigger reverses.",
        },
        "pattern": {
            "pattern_relationship_id": "pattern:test",
            "horizon": "5d_forward",
            "research_score": 0.64,
        },
        "direction": {"state": "long"},
        "current_trigger": {
            "state": "confirmed",
            "active": True,
            "observed_at": NOW,
            "expires_at": "2026-08-25T14:00:00+00:00",
        },
        "market_context": {
            "execution_proxy": "SMH",
            "session_state": session_state,
        },
        "economics": {
            "net_expectancy": 0.01,
            "positive_after_costs": True,
            "source_method": "provider_backed_event_replay",
            "evidence_label": "provisional",
        },
        "invalidation": {"conditions": ["Trigger reverses."]},
        "evidence_profile": {"profile_id": "event_catalyst", "evidence": evidence},
        "completeness": {
            "missing_field_ids": missing,
            "unavailable_field_ids": [],
            "structurally_uncollectable_field_ids": [],
            "adverse_field_ids": [],
        },
    }


def _portfolio() -> dict:
    return {
        "equity": 100_000.0,
        "daily_loss_pct": 0.0,
        "trailing_drawdown_pct": 0.0,
        "new_notional_today": 0.0,
        "positions": [],
    }


def _risk_setup(multiplier: float) -> dict:
    return {
        "setup_id": f"risk:{multiplier}",
        "hypothesis_id": "hypothesis:test",
        "evidence_class": "experimental_unvalidated",
        "experimental_tier": "discovery_micro",
        "pattern_relationship_id": "pattern:test",
        "score_id": "score:test",
        "research_goal_id": "goal:test",
        "instrument": "SMH",
        "strategy_family_id": "semiconductor_policy_options_asymmetry",
        "correlated_cluster": "semiconductors",
        "direction": "long",
        "expected_net_return": 0.01,
        "expected_return_class": "provisional_empirical_estimate",
        "annualized_volatility": 0.20,
        "current_price": 100.0,
        "invalidation": {"invalidation_price": 95.0},
        "liquidity": {"spread_bps": 5.0, "average_daily_dollar_volume": 10_000_000.0},
        "paperable": True,
        "paper_route": "guarded_alpaca_paper_via_paperops",
        "market_context_fresh": True,
        "market_context_age_seconds": 0.0,
        "market_session_actionable": True,
        "edge_confidence_class": "experimental_discovery_micro",
        "uncertainty": 0.75,
        "source_concentration": 0.25,
        "source_families": ["sec_edgar", "earnings_calls"],
        "correlation_to_existing": [],
        "akber_decision": "pass",
        "shadow_promotion_ready": False,
        "decision_time_shadow_snapshot_ready": True,
        "quantity_increment": 1.0,
        "soft_evidence_size_multiplier": multiplier,
    }


def _release() -> dict:
    return {
        "experimental_paper_release_effective": True,
        "release_effective": False,
    }


def _router_setup() -> dict:
    return {
        "setup_id": "router:test",
        "evidence_class": "experimental_unvalidated",
        "experimental_tier": "discovery_micro",
        "candidate_identity_id": "candidate:test",
        "decision_generation_id": "generation:test",
        "lineage": {
            "research_goal_id": "goal:test",
            "score_id": "score:test",
            "pattern_relationship_id": "pattern:test",
            "hypothesis_id": "hypothesis:test",
            "akber_result_id": "akber:test",
            "shadow_evidence_id": "shadow:test",
            "risk_proposal_id": "risk:test",
        },
        "instrument": "SMH",
        "execution_symbol": "SMH",
        "market_family": "semiconductors",
        "direction": "long",
        "horizon": "5d_forward",
        "akber_decision": "pass",
        "akber_layered_decision": "pass_reduced_size",
        "source_quorum_passed": True,
        "expected_net_return_positive_after_costs": True,
        "duplicate_exposure_conflict": False,
        "same_signal_reentry_conflict": False,
        "drawdown_context_complete": True,
        "drawdown_breached": False,
        "qctrl_state": "pass",
        "instrument_paperable": True,
        "route": "guarded_alpaca_paper_via_paperops",
        "risk_proposal_complete": True,
        "decision_time_shadow_snapshot_ready": True,
        "strategy_version_operator_approved": True,
        "risk_policy_operator_approved": True,
        "current_trigger_state": "confirmed",
        "proposed_quantity": 2.0,
        "proposed_notional_usd": 1_000.0,
        "soft_evidence_size_multiplier": 0.5,
        "soft_evidence_multiplier_applied_exactly_once": True,
        "economic_signal_identity_id": "signal:test",
        "evidence_digest": "digest:test",
    }


def test_strategy_alias_resolves_before_profile_lookup() -> None:
    assert canonical_strategy_id("semiconductor_policy_asymmetry") == (
        "semiconductor_policy_options_asymmetry"
    )


def test_layered_health_does_not_deadlock_on_self_or_publication_circuits() -> None:
    health = _operator_health_snapshot(
        {
            "open_circuit_count": 2,
            "services": {
                "portfolio_router_review": {"state": "open"},
                "public_status_publication": {"state": "open"},
                "canonical_tradeability": {"state": "closed"},
                "forward_shadow": {"state": "closed"},
            },
        },
        {
            "open_request_count": 2,
            "requests": [
                {
                    "state": "repair_requested",
                    "evidence": {"service_id": "portfolio_router_review"},
                },
                {
                    "state": "repair_requested",
                    "evidence": {"service_id": "public_status_publication"},
                },
            ],
        },
    )
    errors = validate_layered_state({"operator_health": health})
    assert health["decision_dependency_open_circuit_count"] == 0
    assert health["decision_dependency_open_repair_request_count"] == 0
    assert health["non_blocking_open_circuit_count"] == 2
    assert "decision_dependency_circuit_open" not in errors
    assert "decision_dependency_repair_request_open" not in errors


def test_layered_health_still_blocks_real_upstream_decision_failure() -> None:
    health = _operator_health_snapshot(
        {
            "open_circuit_count": 1,
            "services": {
                "canonical_tradeability": {"state": "closed"},
                "forward_shadow": {"state": "open"},
            },
        },
        {
            "open_request_count": 1,
            "requests": [
                {
                    "state": "repair_requested",
                    "evidence": {"service_id": "forward_shadow"},
                }
            ],
        },
    )
    errors = validate_layered_state({"operator_health": health})
    assert health["decision_dependency_open_circuit_service_ids"] == [
        "forward_shadow"
    ]
    assert "decision_dependency_circuit_open" in errors
    assert "decision_dependency_repair_request_open" in errors


def test_optional_evidence_becomes_haircut_not_veto() -> None:
    judgment = build_market_judgment(_envelope(missing=["technical_confirmation"]))
    action = judgment.missingness_assessment[0]
    assert action.action.value == "soft_size_haircut"
    assert action.can_veto is False
    assert 0 < judgment.adaptive_size.combined_multiplier < 1
    assert judgment.primary_consequence == "reduced_size"


def test_closed_market_execution_gap_becomes_delayed_entry() -> None:
    judgment = build_market_judgment(
        _envelope(missing=["liquidity_and_spread"], session_state="outside_regular_session")
    )
    assert judgment.missingness_assessment[0].action.value == "delay_until_market_window"
    assert judgment.primary_consequence == "delayed_entry"
    queue = build_delayed_entry_queue(
        [judgment.model_dump(mode="json")], {}, generated_at=NOW
    )
    assert queue["record_count"] == 1
    assert queue["broker_write_allowed"] is False


def test_adverse_evidence_remains_veto_capable() -> None:
    envelope = _envelope(missing=[])
    envelope["completeness"]["adverse_field_ids"] = ["risk_reward_context"]
    envelope["evidence_profile"]["evidence"]["risk_reward_context"]["state"] = "adverse"
    judgment = build_market_judgment(envelope)
    assert judgment.primary_consequence == "hard_hold_or_veto"
    assert judgment.missingness_assessment[0].can_veto is True


def test_risk_applies_soft_multiplier_once_and_never_increases_size() -> None:
    policy = default_portfolio_policy(NOW)
    full = evaluate_position_size(
        _risk_setup(1.0), _portfolio(), policy, generated_at=NOW
    )["proposal"]
    reduced = evaluate_position_size(
        _risk_setup(0.5), _portfolio(), policy, generated_at=NOW
    )["proposal"]
    assert full is not None and reduced is not None
    assert reduced["proposed_quantity"] <= full["proposed_quantity"]
    assert reduced["soft_evidence_multiplier_applied_exactly_once"] is True
    assert reduced["proposed_quantity"] <= reduced["base_quantity_before_soft_evidence"]


def test_router_reports_reduced_size_and_blocks_unchanged_signal_reentry() -> None:
    setup = _router_setup()
    decision = route_setup(setup, _release(), generated_at=NOW)
    assert decision["final_state"] == "experimental_paper_review_candidate"
    assert decision["decision_consequence"] == "reduced_size_paper_review"
    blocked_setup = deepcopy(setup)
    blocked_setup["same_signal_reentry_conflict"] = True
    blocked = route_setup(blocked_setup, _release(), generated_at=NOW)
    assert blocked["final_state"] == "reject"
    assert "same_signal_reentry_without_material_change" in blocked["hard_vetoes"]


def test_router_identity_changes_only_when_immutable_signal_material_changes() -> None:
    setup = _router_setup()
    first = route_setup(setup, _release(), generated_at=NOW)
    replay = route_setup(deepcopy(setup), _release(), generated_at=NOW)
    changed = deepcopy(setup)
    changed["economic_signal_identity_id"] = "signal:successor"
    changed["evidence_digest"] = "digest:successor"
    successor = route_setup(changed, _release(), generated_at=NOW)
    assert replay["router_decision_id"] == first["router_decision_id"]
    assert successor["router_decision_id"] != first["router_decision_id"]


def test_activity_health_separates_orders_from_distinct_signals() -> None:
    orders = [
        {
            "status": "filled",
            "direction": "buy",
            "position_intent": "buy_to_open",
            "instrument": "SMH",
            "economic_signal_identity_id": "signal:a",
            "evidence_digest": "digest:1",
            "submitted_at": NOW,
        },
        {
            "status": "filled",
            "direction": "sell",
            "position_intent": "sell_to_close",
            "instrument": "SMH",
            "economic_signal_identity_id": "signal:a",
            "evidence_digest": "digest:1",
            "submitted_at": NOW,
        },
    ]
    activity = build_activity_quality(orders, [], {"records": []}, generated_at=NOW)
    window = activity["windows"]["trailing_24_hours"]
    assert window["filled_orders"] == 2
    assert window["entries"] == 1
    assert window["exits"] == 1
    assert window["distinct_economic_hypotheses"] == 1
    assert activity["raw_order_count_is_independent_trade_count"] is False


def test_activity_conversion_joins_router_signal_to_real_order_ledger() -> None:
    setup = _router_setup()
    decision = route_setup(setup, _release(), generated_at=NOW)
    orders = [
        {
            "status": "filled",
            "direction": "buy",
            "position_intent": "buy_to_open",
            "instrument": "SMH",
            "economic_signal_identity_id": "signal:test",
            "submitted_at": NOW,
        }
    ]
    activity = build_activity_quality(
        orders,
        [decision],
        {"records": []},
        generated_at=NOW,
    )
    assert activity["eligible_setups_seen"] == 1
    assert activity["eligible_setups_submitted"] == 1
    assert activity["eligible_opportunity_capture_rate"] == 1.0


def test_legacy_decision_transaction_migration_is_explicit() -> None:
    migrated = migrate_decision_transaction_payload(
        {"schema_version": "qadam_decision_transaction.v1", "decision_id": "old"}
    )
    assert migrated["schema_version"] == DECISION_SCHEMA_VERSION
    assert migrated["market_judgment"] == {}
    assert migrated["adaptive_size"] == {}


def test_provider_capability_projection_preserves_identity_and_truth(tmp_path) -> None:
    payload = {
        "sources": [
            {
                "source_key": "alpaca",
                "source_name": "Alpaca",
                "source_family": "market",
                "operating_state": "online",
                "live_freshness": "fresh",
                "provider_backed_current": True,
                "historical_alpha_usable": False,
                "sample_or_fixture": False,
                "status_reason": "Provider-backed current quote.",
            },
            {
                "source_key": "stock_act",
                "source_name": "STOCK Act",
                "source_family": "social",
                "operating_state": "online",
                "live_freshness": "unknown",
                "provider_backed_current": False,
                "historical_alpha_usable": True,
                "sample_or_fixture": False,
                "status_reason": "Licensed historical archive.",
            },
        ]
    }
    (tmp_path / "qadam_source_capability_registry.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    projection = _provider_capabilities(NOW, tmp_path)
    providers = {row["provider_id"]: row for row in projection["providers"]}
    assert providers["alpaca"]["status"] == "live"
    assert providers["stock_act"]["status"] == "historical_only"
