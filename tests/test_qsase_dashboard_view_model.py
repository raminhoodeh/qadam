import copy

from orchestrator import qsase_dashboard_view_model as dashboard_view_model_module
from orchestrator.qsase_dashboard_view_model import (
    DASHBOARD_AUTHORITY_FLAGS,
    build_dashboard_view_model,
    build_source_network,
    run_dashboard_anti_slop_checks,
    validate_dashboard_view_model,
    validate_negative_dashboard_view_model_probes,
)


def test_power_research_extension_is_visible_without_rewriting_frozen_baseline():
    context = {
        "universal_matrix": {
            "source_universe": {
                "source_families": {
                    "market": {
                        "source_count": 1,
                        "fresh_count": 1,
                        "degraded_count": 0,
                        "credential_gated_count": 0,
                        "quorum_contributing_count": 1,
                    }
                },
                "sources": [
                    {
                        "source_key": "alpaca",
                        "source_name": "Alpaca",
                        "source_family": "market",
                        "state": "online",
                        "freshness_status": "fresh",
                        "source_quorum_contribution": {"can_contribute": True},
                    }
                ],
            },
            "trading_universe": {
                "instruments": [
                    {
                        "instrument_id": "instrument:spy",
                        "symbol": "SPY",
                        "market_family": "macro_watchlist",
                    }
                ]
            },
        },
        "power_market_checks": {"safe_to_consume": True},
        "power_market_dashboard": {
            "generated_at": "2026-07-31T12:00:00+00:00",
            "research_extension": {
                "status": "research_running",
                "label": "Power & Grid Constraints",
                "source_feeds": [
                    {
                        "source_key": "caiso_oasis_day_ahead_lmp",
                        "source_name": "CAISO Day-Ahead Electricity Prices",
                        "state": "provider_backed_live",
                        "freshness_status": "fresh",
                        "quorum_contribution": True,
                    }
                ],
                "instruments": [
                    {
                        "symbol": "CEG",
                        "market_family": "power_markets",
                        "paper_route_available": True,
                    }
                ],
            },
        },
    }

    section = build_source_network(context, "2026-07-31T12:00:00+00:00")

    assert section["canonical_source_row_count"] == 1
    assert section["canonical_category_row_count"] == 1
    assert section["canonical_trading_universe_row_count"] == 1
    assert section["research_extension_source_row_count"] == 1
    assert section["research_extension_trading_row_count"] == 1
    assert section["source_row_count"] == 2
    assert section["trading_universe_row_count"] == 2
    assert any(row.get("family") == "power_grid_constraints" for row in section["category_rows"])
    assert any(row.get("symbol") == "CEG" for row in section["trading_universe_rows"])


def test_dashboard_view_model_exposes_required_default_sections():
    payload = build_dashboard_view_model()

    assert payload["portfolio_value"]["line_graph_available"] is True
    assert payload["portfolio_value_series_count"] > 0
    assert payload["current_position_count"] >= 0
    assert payload["trading_history_row_count"] >= 0
    assert payload["source_category_row_count"] > 0
    assert payload["source_row_count"] > 0
    assert payload["trading_universe_row_count"] > 0
    assert payload["all_strategy_count"] > 0
    assert "currently_in_play_rows" in payload["strategy_universe"]
    strategy_universe = payload["strategy_universe"]
    assert strategy_universe["defined_strategy_count"] == len(strategy_universe["all_strategy_rows"])
    assert strategy_universe["validated_strategy_count"] >= 0
    assert strategy_universe["strategy_discovery_engine"]["strategy_agnostic_scan_count"] > 0
    assert len(strategy_universe["strategy_discovery_engine"]["methods"]) >= 5
    assert strategy_universe["emerging_strategy_candidates"]["candidate_count"] == len(
        strategy_universe["emerging_strategy_candidates"]["rows"]
    )
    assert strategy_universe["strategy_admission_path"]["current_stage_id"]
    assert len(strategy_universe["strategy_admission_path"]["stages"]) >= 6
    assert strategy_universe["strategy_admission_path"]["next_destination"]["label"] == "Decision Room"
    assert all(
        "akber" not in label.lower()
        for label in strategy_universe["strategy_admission_path"]["after_admission"]
    )
    assert all(row["defined_playbook"] is True for row in strategy_universe["all_strategy_rows"])
    assert all("validated_edge_count" in row for row in strategy_universe["all_strategy_rows"])
    assert payload["linear_pattern_count"] > 0
    assert payload["nonlinear_pattern_count"] > 0
    assert payload["trade_intent_count"] > 0
    assert payload["learning_ledger_row_count"] > 0
    assert payload["repair_queue_count"] >= 0
    assert validate_dashboard_view_model(payload) == []


def test_dashboard_decision_records_are_compact_and_artifact_backed():
    payload = build_dashboard_view_model()
    records = payload["decision_records"]["records"]

    assert records
    assert payload["system_map"]["overview_detail_policy"]["detailed_ledgers_in_overview"] is False
    for record in records:
        assert record["state"]
        assert record["reason"]
        assert record["blocker"]
        assert record["next_allowed_action"]
        assert record["artifact_refs"]
        assert len(record["headline"]) <= 120
        assert len(record["reason"]) <= 220
        assert len(record["next_allowed_action"]) <= 180
        assert record["applied_change"] is False
        assert record["paper_order_created"] is False
        assert record["proof_credit_allowed"] is False
        assert record["live_capital_enabled"] is False


def test_dashboard_trade_intents_are_not_orders_or_approvals():
    payload = build_dashboard_view_model()

    assert payload["trade_intents"]["rows_are_not_orders"] is True
    assert payload["trade_intents"]["rows_are_not_approvals"] is True
    assert payload["trade_intents"]["rows_are_not_qualified_setups"] is True
    for row in payload["trade_intents"]["rows"]:
        assert row["row_type"] == "trade_intent_review_record"
        assert row["is_trade"] is False
        assert row["is_order"] is False
        assert row["is_approval"] is False
        assert row["is_qualified_setup"] is False
        assert row["paper_order_created"] is False


def test_dashboard_is_read_only_and_anti_slop_negative_probes_work():
    payload = build_dashboard_view_model()

    assert payload["authority_flags"] == DASHBOARD_AUTHORITY_FLAGS
    assert all(value is False for value in payload["authority"].values())
    assert payload["applied_change_count"] == 0
    assert payload["paper_order_created_count"] == 0
    assert payload["broker_write_count"] == 0
    assert payload["proof_credit_allowed"] is False
    assert payload["live_capital_enabled"] is False
    assert payload["anti_slop_audit"]["error_count"] == 0

    duplicate_probe = copy.deepcopy(payload)
    duplicate_probe["decision_records"]["records"][1]["headline"] = duplicate_probe["decision_records"]["records"][0]["headline"]
    duplicate_audit = run_dashboard_anti_slop_checks(duplicate_probe)
    assert any("duplicate_headline" in error for error in duplicate_audit["errors"])

    generic_probe = copy.deepcopy(payload)
    generic_probe["decision_records"]["records"][0]["reason"] = "AI-powered seamless dynamic insights"
    generic_audit = run_dashboard_anti_slop_checks(generic_probe)
    assert any("generic_phrase" in error for error in generic_audit["errors"])

    assert validate_negative_dashboard_view_model_probes() == []


def test_negative_authority_probe_handles_an_empty_trade_intent_queue(monkeypatch):
    payload = build_dashboard_view_model()
    payload["trade_intents"]["rows"] = []

    monkeypatch.setattr(
        dashboard_view_model_module,
        "build_dashboard_view_model",
        lambda: copy.deepcopy(payload),
    )

    assert dashboard_view_model_module.validate_negative_dashboard_view_model_probes() == []
