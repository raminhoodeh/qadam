from datetime import datetime, timezone
import json

import pytest

from orchestrator.research.economics import build_report, load_report, record_expense
from orchestrator.storage.control_plane import ControlPlaneStore, ControlPlaneError

NOW = "2026-09-06T12:00:00+00:00"


def expense(**changes):
    return {"receipt_id": "fixture-bill-1", "component_id": "source:sec", "category": "subscription",
            "period_start": "2026-09-01T00:00:00+00:00", "period_end": "2026-10-01T00:00:00+00:00",
            "source_reference": "fixture://invoice", "amount_usd": 10.0, "currency": "USD",
            "basis": "reconciled_provider_receipt", **changes}


def report(**changes):
    return build_report(**{"hypotheses": [], "expenses": [], "ablations": [],
                           "selected_sources": ["sec"], "as_of": NOW, **changes})


def test_no_receipts_is_unknown_not_free_and_paper_profit_is_not_cash():
    result = report()
    assert result["subscription_expense_usd"] is None
    assert result["model_expense_usd"] is None
    assert all(row["reconciled_period_expense_usd"] is None for row in result["components"])
    assert result["paper_pnl_is_cash_income"] is False
    assert result["automatic_budget_expansion"] is False


def test_association_deduplicates_economic_events_but_is_not_causal_value():
    hypothesis = {"economic_signal_identity_id": "event-1", "current_trigger_sources": ["sec"]}
    result = build_report(hypotheses=[hypothesis, hypothesis], expenses=[], ablations=[], selected_sources=[], as_of=NOW)
    source = next(row for row in result["components"] if row["component_id"] == "source:sec")
    assert source["associated_event_count"] == 1
    assert source["association_is_incremental_value"] is False
    assert source["marginal_value_state"] == "unproven_no_registered_paired_outcomes"


def test_expense_is_immutable_idempotent_and_correction_preserves_original(tmp_path):
    store = ControlPlaneStore(tmp_path / "qadam-control-plane.sqlite3")
    assert record_expense(store, expense()) is True
    assert record_expense(store, expense()) is False
    with pytest.raises(ControlPlaneError, match="immutable_identity_collision"):
        record_expense(store, expense(amount_usd=20))
    record_expense(store, expense(receipt_id="correction", amount_usd=8, supersedes_receipt_id="fixture-bill-1"))
    with pytest.raises(ValueError, match="already_superseded"):
        record_expense(store, expense(receipt_id="conflicting", amount_usd=5, supersedes_receipt_id="fixture-bill-1"))
    result = load_report(tmp_path, selected_sources=["sec"], as_of=NOW)
    assert result["subscription_expense_usd"] == 8
    with store.connect() as connection:
        originals = [json.loads(row[0]) for row in connection.execute("SELECT payload_json FROM operating_events")]
    assert sorted(row["amount_usd"] for row in originals) == [8, 10]


@pytest.mark.parametrize("changes", [
    {"amount_usd": True}, {"amount_usd": float("nan")}, {"amount_usd": -10},
    {"currency": "GBP"}, {"basis": "user_estimate"}, {"source_reference": ""},
    {"period_start": "2026-09-01"}, {"period_end": "2026-08-01T00:00:00Z"},
])
def test_unverified_or_invalid_expense_does_not_enter_ledger(tmp_path, changes):
    store = ControlPlaneStore(tmp_path / "state.sqlite3")
    with pytest.raises(ValueError):
        record_expense(store, expense(**changes))
    with store.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM operating_events").fetchone()[0] == 0


def test_missing_database_is_non_authoritative_incomplete_report(tmp_path):
    result = load_report(tmp_path, selected_sources=["sec"], as_of=NOW)
    assert result["status"] == "incomplete_input_window"
    assert list(tmp_path.iterdir()) == []


def test_ablation_requires_prospective_registered_matched_evidence_and_keeps_losses():
    pair = {"registration_id": "study-1", "component_id": "model:ibm_quantum", "independent_event_id": "event-1",
        "registered_at": "2026-09-01T00:00:00Z", "event_available_at": "2026-09-02T00:00:00Z",
        "completed_at": "2026-09-05T00:00:00Z", "registration_receipt_verified": True,
        "provider_backed_outcome": True, "same_event_same_window": True, "same_risk_budget": True,
        "hypotheses_mutated": False, "holdout_reused": False, "frozen_with_version": "q1",
        "frozen_without_version": "c1", "with_component_net_return": -.002, "without_component_net_return": .001}
    invalid = {**pair, "independent_event_id": "late-registration", "registered_at": "2026-09-04T00:00:00Z"}
    result = build_report(hypotheses=[], expenses=[], ablations=[pair, pair, invalid], selected_sources=[], as_of=NOW)
    row = next(row for row in result["components"] if row["component_id"] == "model:ibm_quantum")
    assert row["ablations"][0]["independent_event_count"] == 1
    assert row["ablations"][0]["mean_modelled_return_delta"] == pytest.approx(-.003)
    assert row["ablations"][0]["promotion_authority"] is False
    assert result["excluded_ablation_count"] == 1


def test_expired_bill_is_not_presented_as_current_cost():
    result = build_report(hypotheses=[], expenses=[expense()], ablations=[], selected_sources=[],
                          as_of=datetime(2026, 10, 1, tzinfo=timezone.utc).isoformat())
    assert result["subscription_expense_usd"] is None
