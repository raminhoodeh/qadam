from datetime import datetime, timedelta, timezone
import json
import sqlite3

import pytest

from orchestrator.execution.entry_quote import reference_price
from orchestrator.execution.order_projection import project_order
from orchestrator.learning.comparators import MARKET_BASELINE, freeze_market_baseline
from orchestrator.qadam_control_plane_store import ControlPlaneError
from orchestrator.runtime.availability import session_care_availability


def test_all_non_broker_work_is_isolated_but_cannot_become_a_broker_worker():
    from dataclasses import replace
    from orchestrator.runtime.services import SERVICE_DEFINITIONS, worker_execution_permitted
    for definition in SERVICE_DEFINITIONS:
        assert definition.isolated_worker == (definition.service_id != "guarded_paperops")
        assert worker_execution_permitted(definition) == (definition.service_id != "guarded_paperops")
    conversion = next(row for row in SERVICE_DEFINITIONS if row.service_id == "open_market_conversion")
    assert not worker_execution_permitted(replace(conversion, command_sequence=(("unsafe",),)))


def test_broker_projection_keeps_contract_and_recovers_only_exact_order():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("CREATE TABLE operating_events(event_id, aggregate_type, aggregate_id, event_type, payload_json, created_at)")
    original = {"purpose": "canonical_position_entry", "candidate": {"strategy_version_id": "v1"}}
    connection.execute("INSERT INTO operating_events VALUES (?,?,?,?,?,?)",
                       ("e1", "order", "order1", "order_prepared_with_exit_plan", json.dumps(original), "2026-10-20"))
    payload, source = project_order(connection, "order1", {"status": "filled"}, {})
    assert payload == {**original, "status": "filled"}
    assert source == "e1"
    payload, source = project_order(connection, "order1", {"status": "canceled"}, payload)
    assert payload["purpose"] == original["purpose"] and payload["status"] == "canceled"
    assert source is None
    payload, source = project_order(connection, "other_order", {"status": "filled"}, {})
    assert "purpose" not in payload and source is None


def test_worker_start_and_finish_are_separate_immutable_receipts(tmp_path):
    from orchestrator.runtime.operator import _append_receipt
    from orchestrator.qadam_control_plane_store import ControlPlaneStore
    row = {"receipt_id": "same-run", "service_id": "dashboard_refresh",
           "generated_at": "2026-10-20T14:00:00+00:00", "state": "worker_started"}
    _append_receipt(tmp_path, row)
    _append_receipt(tmp_path, {**row, "state": "worker_completed", "completed_at": "2026-10-20T14:00:10+00:00"})
    rows = ControlPlaneStore(tmp_path / "qadam-control-plane.sqlite3").read_table("service_runs")
    assert {record["status"] for record in rows} == {"worker_started", "worker_completed"}
    assert len(rows) == 2


def test_exit_anchor_is_executable_price_not_approved_budget():
    now = datetime.now(timezone.utc)
    quote = {"symbol": "XAR", "bid": 221.5, "ask": 221.6,
             "observed_at": now.isoformat(), "provider_backed": True}
    assert reference_price(quote, symbol="XAR", side="buy", now=now) == 221.6
    assert reference_price(quote, symbol="XAR", side="sell", now=now) == 221.5
    for change in ({"observed_at": (now-timedelta(seconds=61)).isoformat()},
                   {"observed_at": (now+timedelta(seconds=2)).isoformat()},
                   {"ask": float("nan")}, {"bid": 230}, {"provider_backed": False}):
        with pytest.raises(ControlPlaneError, match="fresh_entry_quote_unavailable"):
            reference_price({**quote, **change}, symbol="XAR", side="buy", now=now)
    assert reference_price({**quote, "observed_at": (now+timedelta(milliseconds=11)).isoformat()},
                           symbol="XAR", side="buy", now=now) == 221.6


def test_quote_deferral_never_hides_an_attempted_or_unrelated_failure():
    from orchestrator.execution.entry_quote import pre_submit_quote_deferral
    now = datetime.now(timezone.utc)
    row = {"generated_at": now.isoformat(), "broker_post_called_count": 0, "alpaca_paper_post_called_count": 0,
           "precondition_failures": ["immediate_pre_entry_reconciliation_and_prewrite"],
           "precondition_records": [{"passed": False, "detail": "fresh_entry_quote_unavailable"}]}
    assert pre_submit_quote_deferral(row, pass_started_at=now) == "fresh_entry_quote_unavailable"
    assert pre_submit_quote_deferral({**row, "broker_post_called_count": 1}, pass_started_at=now) is None
    assert pre_submit_quote_deferral(row, pass_started_at=now+timedelta(seconds=1)) is None
    assert pre_submit_quote_deferral({**row, "precondition_records": [{"passed": False, "detail": "ambiguous_broker_write"}]}, pass_started_at=now) is None


def test_market_comparator_rejects_future_or_stale_information():
    now = datetime.now(timezone.utc)
    contract = {"market_baseline": MARKET_BASELINE}
    row = {"symbol": "XAR", "provider_backed": True, "percent_move": .3,
           "rolling_volatility_20d": .02, "quote_observed_at": now.isoformat(),
           "available_at": now.isoformat()}
    def freeze(row):
        return freeze_market_baseline(contract, {"source_price_context": {"value": {"price_volume_records": [row]}}},
                                      "XAR", decision_at=now.isoformat())
    assert freeze(row)["direction"] == "long"
    assert freeze({**row, "quote_observed_at": (now+timedelta(milliseconds=11)).isoformat()})["available"] is True
    assert freeze({**row, "quote_observed_at": (now+timedelta(seconds=2)).isoformat()})["available"] is False
    assert freeze({**row, "available_at": (now+timedelta(seconds=1)).isoformat()})["available"] is False
    assert freeze({**row, "quote_observed_at": (now-timedelta(seconds=301)).isoformat()})["available"] is False


def test_soak_cannot_count_one_good_sample_as_a_complete_session(tmp_path):
    from orchestrator.qadam_control_plane_store import ControlPlaneStore
    from tests.test_qadam_operating_ledger import _settings
    store = ControlPlaneStore.from_settings(_settings(tmp_path))
    opening = datetime(2026, 10, 20, 13, 30, tzinfo=timezone.utc)
    closing = opening + timedelta(minutes=390)
    payload = {"minute": opening.isoformat(), "available": True, "simulated": False,
               "backfilled": False, "market_session_date": "2026-10-20"}
    with store.transaction() as connection:
        connection.execute("INSERT INTO operating_events VALUES (?,?,?,?,?,?,?)",
                           ("sample1", "care_availability", "build1", "minute_observed", json.dumps(payload), "sha", opening.isoformat()))
    result = session_care_availability(store, "build1", "2026-10-20", opening, closing)
    assert result["healthy_minutes"] == 1
    assert result["unobserved_minutes"] == 389
    assert result["meets_target"] is False
