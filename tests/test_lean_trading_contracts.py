from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json

import pytest

from orchestrator.qadam_graph_active_discovery import _qeg_hypothesis
from orchestrator.qadam_tradeability_reliability import _run_producer_contract_canary
from orchestrator.research.playbooks import capacity_projection, playbook_definition


def test_unknown_return_producer_reaches_guarded_handoff_with_registered_rules():
    result = _run_producer_contract_canary("lean-unknown-no-broker")
    assert result["actual"] == "accepted_for_guarded_paperops_sequence"
    assert 0 < result["risk_proposed_notional_usd"] <= 250
    assert result["decision"]["lineage"]["strategy_version_id"].startswith("paper-strategy-version:")
    assert result["handoff"]["maximum_loss_at_invalidation"] <= 5


def test_graph_definition_survives_quote_refresh_but_not_rule_change():
    contract = {"strategy_family_id": "energy", "instrument": "XLE", "time_horizon": "3d_forward",
                "entry_rule": "registered event", "invalidation_rule": "source correction",
                "exit_rule": "stop or expiry", "maximum_notional_usd": 250}
    strategy = {"strategy_version_id": "graph-v", "contract": contract, "experiment_id": "e",
                "evidence_class": "experimental_unvalidated", "decision_economics": {
                    "current_expectancy_state": "ready_for_discovery_micro_review",
                    "current_expectancy_id": "quote-one", "current_total_cost": .001,
                    "expected_return_class": "unestimated_discovery_experiment"}}
    candidate = {"pattern_relationship_id": "event-one", "strategy_family_id": "energy", "instrument": "XLE",
                 "source_path": [{"source_key": "rss", "fresh": True, "trust_score": .8}]}
    direction = {"actionable_direction": "long"}
    first = _qeg_hypothesis(strategy, candidate, direction, {}, generated_at="2026-10-20T13:00:00Z")
    refreshed = deepcopy(strategy)
    refreshed["decision_economics"].update(current_expectancy_id="quote-two", current_total_cost=.002)
    second = _qeg_hypothesis(refreshed, {**candidate, "pattern_relationship_id": "event-two"}, direction, {},
                             generated_at="2026-10-20T13:05:00Z")
    assert first["strategy_version_id"] == second["strategy_version_id"]
    refreshed["contract"]["time_horizon"] = "2d_forward"
    third = _qeg_hypothesis(refreshed, candidate, direction, {}, generated_at="2026-10-20T13:05:00Z")
    assert third["strategy_version_id"] != first["strategy_version_id"]
    assert second["expected_edge_range"]["net_expectancy"] is None


def test_activity_counts_do_not_call_fills_new_trades(tmp_path):
    from orchestrator.execution.ledger import OperatingLedger
    from orchestrator.config import Settings
    from dataclasses import replace
    from orchestrator.presentation.trading_activity import activity_report
    ledger = OperatingLedger(replace(Settings.from_env(), runtime_dir=str(tmp_path)))
    report = activity_report(tmp_path, as_of=datetime.now(timezone.utc).isoformat())
    assert report["available"]
    assert report["independent_acknowledged_entry_events"] == 0
    assert report["counts"]["fill_records"] == 0
    assert report["trade_quota_enforced"] is False
    assert ledger.store.integrity_report()["status"] == "passed"


def test_capacity_and_short_horizon_are_not_hidden_risk_expansion():
    assert capacity_projection(average_holding_sessions=5)["full_utilisation_entry_capacity"] == 3
    assert capacity_projection(average_holding_sessions=2)["full_utilisation_entry_capacity"] == 7.5
    profile = playbook_definition("semiconductor_policy_options_asymmetry")
    assert profile["maximum_unestimated_notional_usd"] == 250
    assert profile["short_horizon_challenger"]["automatic_horizon_change_allowed"] is False


def test_missing_registered_definition_blocks_before_broker(tmp_path, monkeypatch):
    from tests.test_qadam_operating_ledger import _settings, _persist_ready_lineage, _candidate, _activate
    from orchestrator.execution.ledger import OperatingLedger
    from orchestrator.storage.control_plane import ControlPlaneError
    settings = _settings(tmp_path)
    state = _persist_ready_lineage(settings)
    ledger = OperatingLedger(settings)
    ledger.record_research_generation(state)
    _activate(monkeypatch, ledger)
    with ledger.store.transaction() as connection:
        connection.execute("DELETE FROM operating_events WHERE aggregate_type='strategy_version'")
    with pytest.raises(ControlPlaneError, match="canonical_strategy_definition_not_registered"):
        ledger.prepare_order(_candidate())
    assert ledger.store.read_table("canonical_orders") == []


def test_new_elapsed_horizon_exit_does_not_rewrite_old_session_rules(tmp_path):
    from tests.test_qadam_canonical_exit_engine import _settings, _seed_due_position
    from orchestrator.execution.ledger import OperatingLedger
    ledger = OperatingLedger(_settings(tmp_path))
    _seed_due_position(ledger)
    opened = datetime(2026, 8, 20, 14, 30, tzinfo=timezone.utc)
    with ledger.store.transaction() as connection:
        connection.execute("UPDATE positions SET current_price=50")
        connection.execute("UPDATE exit_plans SET payload_json=?", (json.dumps({"maximum_holding_seconds": 86400}),))
    assert ledger.due_exit_candidates(current_time=opened+timedelta(hours=23)) == []
    assert ledger.due_exit_candidates(current_time=opened+timedelta(hours=25))[0]["trigger"] == "maximum_holding_period"
