import copy

from orchestrator import qsase_dashboard_view_model as dashboard_view_model_module
from orchestrator.qsase_dashboard_view_model import (
    DASHBOARD_AUTHORITY_FLAGS,
    build_dashboard_view_model,
    run_dashboard_anti_slop_checks,
    validate_dashboard_view_model,
    validate_negative_dashboard_view_model_probes,
)


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
