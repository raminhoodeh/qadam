from datetime import datetime, timedelta, timezone

import pytest

from orchestrator.research import component_studies as studies
from orchestrator.research.economics import load_report
from orchestrator.storage.control_plane import ControlPlaneStore
from orchestrator.qadam_operator_ready_common import sha256_json


def test_real_producer_pairs_are_prospective_durable_idempotent_and_keep_losses(tmp_path, monkeypatch):
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    class Clock(datetime):
        current = start
        @classmethod
        def now(cls, tz=None):
            return cls.current
    monkeypatch.setattr(studies, "datetime", Clock)
    store = ControlPlaneStore(tmp_path / "qadam-control-plane.sqlite3")
    hypotheses = [{"hypothesis_id": "fixture-h", "strategy_version_id": "fixture-version"}]
    inputs = [{"hypothesis_id": "fixture-h", "current_trigger_sources": ["eia"]}]
    assert studies.register_studies(store, hypotheses, inputs) == 1
    Clock.current += timedelta(hours=1)
    assert studies.register_studies(store, hypotheses, inputs) == 0
    entry = {"instrument": "XLE", "provider_backed": True, "price": 100,
             "observed_at": Clock.current.isoformat(), "available_at": Clock.current.isoformat()}
    frozen = {"current_trigger_sources": ["eia"], "entry_observation": entry,
              "direction": "long", "evaluation_contract": {"cost_bps": 10}}
    decision = {"decision_id": "fixture-decision", "decision_at": Clock.current.isoformat(),
        "outcome_due_at": (Clock.current + timedelta(days=1)).isoformat(),
        "simulated_elapsed_time": False, "frozen_decision_payload": frozen,
        "frozen_decision_hash": sha256_json(frozen), "strategy_version_id": "fixture-version",
        "economic_signal_identity_id": "fixture-independent-event"}
    assert studies.record_study_decisions(store, [decision]) == 1
    assert studies.record_study_decisions(store, [decision]) == 0
    Clock.current += timedelta(days=1, minutes=1)
    outcome = {"decision_id": "fixture-decision", "outcome_id": "fixture-outcome",
        "outcome_observation": {**entry, "price": 95, "observed_at": Clock.current.isoformat(),
                                "available_at": Clock.current.isoformat()}}
    assert studies.record_study_outcomes(store, [outcome]) == 1
    assert studies.record_study_outcomes(store, [outcome]) == 0
    report = load_report(tmp_path, selected_sources=["eia"], as_of=Clock.current.isoformat())
    row = next(row for row in report["components"] if row["component_id"] == "source:eia")
    assert row["ablations"][0]["mean_modelled_return_delta"] == pytest.approx(-.051)
    assert row["ablations"][0]["scope"] == "source_dependent_setup_vs_abstention"
    assert row["ablations"][0]["component_causal_value_proven"] is False
    assert report["subscription_expense_usd"] is None
    # A newly created study cannot claim an already completed decision/outcome.
    assert studies.record_study_decisions(store, [{**decision, "decision_id": "late"}]) == 0
    with store.connect() as connection:
        assert connection.execute("SELECT count(*) FROM canonical_orders").fetchone()[0] == 0


def test_unmatched_result_boolean_is_not_economics_evidence(tmp_path):
    store = ControlPlaneStore(tmp_path / "state.sqlite3")
    with store.connect() as connection:
        assert studies.verified_results(connection, [{"registration_receipt_verified": True}]) == []


@pytest.mark.parametrize("baseline_direction,expected_without", [("short", .049), ("long", -.051), ("abstain", 0.0), (None, None)])
def test_economic_policy_is_measured_against_frozen_price_only_not_just_abstention(tmp_path, monkeypatch, baseline_direction, expected_without):
    from orchestrator.learning.comparators import MARKET_BASELINE
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    class Clock(datetime):
        current = start
        @classmethod
        def now(cls, tz=None):
            return cls.current
    monkeypatch.setattr(studies, "datetime", Clock)
    store = ControlPlaneStore(tmp_path / "qadam-control-plane.sqlite3")
    context = {"economic_policy_version": "economic-changes.1", "economic_changes": [{"feature_id": "feature1"}]}
    assert studies.register_studies(store, [{"hypothesis_id": "h", "strategy_version_id": "v"}],
        [{"hypothesis_id": "h", "cross_source_context": context}]) == 1
    Clock.current += timedelta(hours=1)
    entry = {"instrument": "NVDA", "provider_backed": True, "price": 100,
             "observed_at": Clock.current.isoformat(), "available_at": Clock.current.isoformat()}
    frozen = {"cross_source_context": context, "entry_observation": entry, "direction": "long",
        "evaluation_contract": {"cost_bps": 10},
        "market_baseline": {"available": baseline_direction is not None,
                            "direction": baseline_direction, "contract": MARKET_BASELINE}}
    decision = {"decision_id": "d", "decision_at": Clock.current.isoformat(),
        "outcome_due_at": (Clock.current + timedelta(days=1)).isoformat(),
        "simulated_elapsed_time": False, "frozen_decision_payload": frozen,
        "frozen_decision_hash": sha256_json(frozen), "strategy_version_id": "v",
        "economic_signal_identity_id": "independent-event1"}
    assert studies.record_study_decisions(store, [decision]) == int(baseline_direction is not None)
    Clock.current += timedelta(days=1, minutes=1)
    outcome = {"decision_id": "d", "outcome_id": "o", "outcome_observation": {**entry, "price": 95,
        "observed_at": Clock.current.isoformat(), "available_at": Clock.current.isoformat()}}
    assert studies.record_study_outcomes(store, [outcome]) == int(baseline_direction is not None)
    assert studies.record_study_outcomes(store, [outcome]) == 0
    with store.connect() as connection:
        results = [__import__("json").loads(row[0]) for row in connection.execute(
            "SELECT payload_json FROM operating_events WHERE aggregate_type='component_result'")]
    if expected_without is None:
        assert results == []
    else:
        result, = results
        assert result["with_component_net_return"] == pytest.approx(-.051)
        assert result["without_component_net_return"] == pytest.approx(expected_without)
        assert result["incremental_modelled_return"] == pytest.approx(-.051 - expected_without)
        assert result["scope"] == "economic_context_policy_vs_frozen_price_only"
        assert result["economic_feature_ids"] == ["feature1"]
        assert not result["component_causal_value_proven"]
        assert result["decision_changed"] == (baseline_direction != "long")
