from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json

import pytest

from orchestrator.execution.candidate_selection import defer_held_entries
from orchestrator.execution.entry_quote import pre_submit_quote_deferral
from orchestrator.qadam_control_plane_store import ControlPlaneStore
from tests.test_qadam_operating_ledger import _activate, _settings
from orchestrator.qadam_operating_ledger import OperatingLedger


def fixture_snapshot(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    store = ControlPlaneStore.from_settings(settings)
    ledger = OperatingLedger(settings, store=store)
    _activate(monkeypatch, ledger)
    now = datetime.now(timezone.utc)
    payload = json.dumps({"instrument": "XLE", "quantity": 2}, sort_keys=True)
    with store.transaction() as connection:
        connection.execute(
            "INSERT INTO positions (position_key,instrument,trading_lane,quantity,"
            "average_entry_price,current_price,unrealized_pnl,state,payload_json,"
            "payload_sha256,opened_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            ("paper:XLE", "XLE", "discovery", 2, 70, 70, 0, "open", payload,
             sha256(payload.encode()).hexdigest(), now.isoformat(), now.isoformat()),
        )
    check = ledger.record_direct_reconciliation(
        phase="incident_recovery", expected={}, blockers=[], observed={
            "mirror_observed_at": now.isoformat(), "position_count": 1,
            "position_protection_digest": "protection-hash",
        },
    )
    return store, check, now


def candidates():
    return [{"instrument": symbol, "request_preview": {"symbol": symbol},
             "fresh_for_paper_post": True, "previously_submitted_to_alpaca_paper": False,
             "eligible_for_paper_post": True, "status": "eligible"}
            for symbol in ("XLE", "NVDA")]


def test_existing_exposure_cannot_starve_an_unrelated_fresh_candidate(tmp_path, monkeypatch):
    _, check, now = fixture_snapshot(tmp_path, monkeypatch)
    rows = candidates()
    defer_held_entries(rows, tmp_path, now=now)
    assert rows[0]["status"] == "held_existing_open_position"
    assert rows[0]["eligible_for_paper_post"] is True
    assert rows[0]["previously_submitted_to_alpaca_paper"] is False
    assert rows[0]["entry_hold_reconciliation_id"] == check["reconciliation_id"]
    assert [r["instrument"] for r in rows if r["fresh_for_paper_post"]] == ["NVDA"]
    rows[0].update(fresh_for_paper_post=False, previously_submitted_to_alpaca_paper=True,
                   status="blocked_duplicate_paper_submit")
    defer_held_entries(rows, tmp_path, now=now)
    assert rows[0]["status"] == "blocked_duplicate_paper_submit"


@pytest.mark.parametrize("fault", ["stale", "future", "hash", "position_hash", "blocked", "live", "count"])
def test_unknown_or_unverified_snapshot_never_changes_preview(tmp_path, monkeypatch, fault):
    store, _, now = fixture_snapshot(tmp_path, monkeypatch)
    with store.transaction() as connection:
        row = connection.execute("SELECT * FROM reconciliation_runs LIMIT 1").fetchone()
        data = json.loads(row["payload_json"])
        if fault in {"stale", "future"}:
            data["observed"]["mirror_observed_at"] = (now + timedelta(seconds=181 if fault == "future" else -181)).isoformat()
        elif fault == "blocked":
            data["status"] = "blocked"
        elif fault == "live":
            data["live_capital_enabled"] = True
        elif fault == "count":
            data["observed"]["position_count"] = 2
        elif fault == "position_hash":
            connection.execute("UPDATE positions SET payload_sha256='corrupt'")
        payload = json.dumps(data, sort_keys=True)
        connection.execute("UPDATE reconciliation_runs SET payload_json=?,payload_sha256=?",
                           (payload, "corrupt" if fault == "hash" else sha256(payload.encode()).hexdigest()))
    rows = candidates()
    defer_held_entries(rows, tmp_path, now=now)
    assert all(r["fresh_for_paper_post"] for r in rows)


def test_missing_database_is_not_created(tmp_path):
    rows = candidates()
    defer_held_entries(rows, tmp_path)
    assert not (tmp_path / "qadam-control-plane.sqlite3").exists()
    assert all(r["fresh_for_paper_post"] for r in rows)


def test_duplicate_race_is_only_a_deferral_if_no_write_was_attempted():
    now = datetime.now(timezone.utc)
    row = {"generated_at": now.isoformat(), "broker_post_called_count": 0,
           "alpaca_paper_post_called_count": 0,
           "precondition_failures": ["immediate_pre_entry_reconciliation_and_prewrite"],
           "precondition_records": [{"passed": False, "detail": "duplicate_open_position_in_ledger"}]}
    assert pre_submit_quote_deferral(row, pass_started_at=now) == "duplicate_open_position_in_ledger"
    for field in ("broker_post_called_count", "alpaca_paper_post_called_count"):
        assert pre_submit_quote_deferral({**row, field: 1}, pass_started_at=now) is None
    assert pre_submit_quote_deferral(row, pass_started_at=now + timedelta(seconds=1)) is None
