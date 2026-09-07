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
