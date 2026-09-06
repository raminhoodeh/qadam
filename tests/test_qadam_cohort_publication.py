from dataclasses import replace
from hashlib import sha256
import json
import sqlite3

import pytest

from orchestrator.config import Settings
from orchestrator.execution import ledger as module
from orchestrator.storage.control_plane import ControlPlaneError, ControlPlaneStore


def insert_outcome(store, identity, **changes):
    row = {"strategy_id": "power", "strategy_version": "v1", "trading_lane": "discovery",
        "attribution_status": "exact_entry_decision", "independent_event_id": identity,
        "net_return": .01, "benchmark_net_return": .002, "entry_notional": 100,
        "cost_bps": 5, "cost_model_version": "cost-v1", "cost_basis": "modelled",
        "costs_are_modelled_not_live_execution_costs": True, "costs_measured": False,
        "cost_assumption_registered_at": "2026-09-01T00:00:00Z",
        "broker_account_fingerprint": "fixture-account", "paper_epoch_id": "fixture-epoch",
        "accounting_status": "gross_reconstructed", **changes}
    encoded = json.dumps(row)
    # A separate writer with a short timeout reproduces broker contention without
    # any broker, live state, or thread timing dependency.
    connection = sqlite3.connect(store.path, timeout=.1)
    try:
        connection.execute("INSERT INTO outcomes (outcome_id,strategy_id,strategy_version,"
            "trading_lane,state,payload_json,payload_sha256,observed_at) "
            "VALUES (?,'power','v1','discovery','closed',?,?,?)",
            (identity, encoded, sha256(encoded.encode()).hexdigest(), "2026-09-02T00:00:00Z"))
        connection.commit()
    finally:
        connection.close()


@pytest.fixture
def ledger(tmp_path):
    settings = replace(Settings.from_env(), runtime_dir=str(tmp_path), state_root=str(tmp_path))
    return module.OperatingLedger(settings, store=ControlPlaneStore(tmp_path / "qadam-control-plane.sqlite3"))


def test_changed_outcomes_do_not_publish_a_stale_cohort_or_hold_the_writer(ledger, monkeypatch):
    insert_outcome(ledger.store, "first")
    prior = ledger.rebuild_cohorts()
    original = module.cohort_metrics

    def new_fill_during_calculation(rows):
        insert_outcome(ledger.store, "second")
        return original(rows)

    monkeypatch.setattr(module, "cohort_metrics", new_fill_during_calculation)
    with pytest.raises(ControlPlaneError, match="cohort_inputs_changed_retry_next_cycle"):
        ledger.rebuild_cohorts()
    with ledger.store.connect() as connection:
        assert [json.loads(row[0]) for row in connection.execute("SELECT payload_json FROM strategy_cohorts")] == prior
        assert connection.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0] == 2
        assert connection.execute("SELECT frozen FROM execution_state").fetchone()[0] == 0
    monkeypatch.setattr(module, "cohort_metrics", original)
    fresh = ledger.rebuild_cohorts()
    assert fresh[0]["independent_outcome_count"] == 2
    assert fresh[0]["outcome_source_digest"] != prior[0]["outcome_source_digest"]
    assert fresh == ledger.rebuild_cohorts()


def test_summary_streams_lots_without_changing_accounting(ledger, monkeypatch):
    insert_outcome(ledger.store, "one")
    insert_outcome(ledger.store, "two", attribution_status="exact_entry_allocations",
        attributed_lots=[{"cost_basis": "modelled"}, {"cost_basis": "unavailable"}])
    insert_outcome(ledger.store, "three", attribution_status="unresolved", costs_measured=True)
    original = module.learning_lots
    sizes = []

    def one_record_at_a_time(rows):
        sizes.append(len(rows))
        assert len(rows) == 1
        return original(rows)

    monkeypatch.setattr(module, "learning_lots", one_record_at_a_time)
    result = ledger.summary()["outcome_accounting"]
    assert sizes == [1, 1, 1]
    assert result == {"closed_record_count": 3, "exact_entry_attribution_count": 1,
        "exact_multi_entry_allocation_count": 1, "unresolved_attribution_count": 1,
        "modelled_cost_lot_count": 3, "gross_reconstructed_count": 3,
        "cost_measured_count": 1, "placeholder_zero_is_measurement": False,
        "gross_estimates_are_not_net_edge_evidence": True}
