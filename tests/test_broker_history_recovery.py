from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from orchestrator.config import Settings
from orchestrator.contracts.broker_history import history_allocation_freeze
from orchestrator.execution import incident_alert
from orchestrator.paper_account import AlpacaReadOnlyPaperMirror
from orchestrator.runtime.recovery_policy import classify_failure, retry_policy


def _stamp(index):
    return (datetime(2026, 9, 9, tzinfo=timezone.utc) - timedelta(seconds=index)).isoformat()


def test_pagination_keeps_old_fills_and_nested_legs(monkeypatch):
    mirror = object.__new__(AlpacaReadOnlyPaperMirror)
    pages = [[{"id": str(i), "submitted_at": _stamp(i)}
              for i in range(500)], [{"id": "old-entry", "submitted_at": _stamp(501), "legs": [{"id": "old-leg"}]}], []]
    calls = []

    def get(path, *, params):
        calls.append((path, params))
        if "after" in params:
            return [{"id": "boundary-tie", "submitted_at": _stamp(499)}]
        return pages.pop(0)

    monkeypatch.setattr(mirror, "_get", get)
    orders, receipt = mirror._fetch_order_history()
    assert receipt["status"] == "complete"
    assert receipt["page_count"] == 3
    assert len(mirror._flatten_order_payloads(orders)) == 503
    assert calls[2][1]["until"] == _stamp(499)
    assert all(call[0] == "/orders" for call in calls)


@pytest.mark.parametrize("count", [0, 100, 101, 499, 500, 1000])
def test_history_is_not_truncated_at_a_page_boundary(monkeypatch, count):
    mirror = object.__new__(AlpacaReadOnlyPaperMirror)
    rows = [{"id": str(i), "submitted_at": _stamp(i)} for i in range(count)]

    def get(path, *, params):
        def included(row):
            stamp = datetime.fromisoformat(row["submitted_at"])
            return ("until" not in params or stamp < datetime.fromisoformat(params["until"])) and (
                "after" not in params or stamp > datetime.fromisoformat(params["after"]))
        return [row for row in rows if included(row)][:500]

    monkeypatch.setattr(mirror, "_get", get)
    result, receipt = mirror._fetch_order_history()
    assert result == rows
    assert receipt["page_count"] == (count + 499) // 500 + 1


@pytest.mark.parametrize("bad_page", [None, {}, [{"symbol": "ITA"}], [{"id": "x"}, {"id": "x"}]])
def test_bad_history_never_returns_partial_success(monkeypatch, bad_page):
    mirror = object.__new__(AlpacaReadOnlyPaperMirror)
    monkeypatch.setattr(mirror, "_get", lambda *a, **k: bad_page)
    with pytest.raises(ValueError, match="broker_order_history_"):
        mirror._fetch_order_history()


def test_ignored_cursor_fails_closed(monkeypatch):
    mirror = object.__new__(AlpacaReadOnlyPaperMirror)
    monkeypatch.setattr(mirror, "_get", lambda *a, **k: [{"id": "same", "submitted_at": _stamp(0)}])
    with pytest.raises(ValueError, match="cursor_not_advancing"):
        mirror._fetch_order_history()


def test_second_page_transport_failure_cannot_publish_partial_mirror(monkeypatch):
    mirror = object.__new__(AlpacaReadOnlyPaperMirror)

    def get(path, *, params):
        if "until" in params:
            raise TimeoutError("test")
        return [{"id": "first", "submitted_at": _stamp(0)}]

    monkeypatch.setattr(mirror, "_get", get)
    with pytest.raises(TimeoutError):
        mirror.fetch()


def test_short_nested_page_is_not_mistaken_for_complete_history(monkeypatch):
    mirror = object.__new__(AlpacaReadOnlyPaperMirror)
    pages = [[{"id": "parent", "submitted_at": _stamp(0),
               "legs": [{"id": str(i)} for i in range(499)]}],
             [{"id": "earlier", "submitted_at": _stamp(2)}], []]
    def get(path, *, params):
        return [] if "after" in params else pages.pop(0)
    monkeypatch.setattr(mirror, "_get", get)
    rows, receipt = mirror._fetch_order_history()
    assert receipt["status"] == "complete"
    assert rows[-1]["id"] == "earlier"


def test_saturated_timestamp_boundary_fails_closed(monkeypatch):
    mirror = object.__new__(AlpacaReadOnlyPaperMirror)
    monkeypatch.setattr(mirror, "_get", lambda *a, **k: [
        {"id": str(i), "submitted_at": _stamp(0)} for i in range(500)])
    with pytest.raises(ValueError, match="ambiguous_timestamp_boundary"):
        mirror._fetch_order_history()


def test_history_repair_is_typed_bounded_and_not_broker_authority():
    marker = "paperops_recovery_class=broker_history_incomplete"
    assert classify_failure(marker) == "broker_history_incomplete"
    assert classify_failure("unauthorized write " + marker) == "safety_violation"
    assert classify_failure("position_entry_allocation_unresolved:ITA") == "code_defect"
    policy = retry_policy("broker_history_incomplete", attempt_count=3)
    assert policy["automatic_retry_allowed"] is False
    assert policy["broker_write_retry_allowed"] is False
    assert history_allocation_freeze("broker_reconciliation_disagreement:position_entry_allocation_unresolved:ITA")
    assert not history_allocation_freeze("operator_manual_stop")
    assert not history_allocation_freeze("broker_reconciliation_disagreement:position_entry_allocation_unresolved:ITA,unexplained_broker_order:other")


def test_incident_alert_retries_deduplicates_and_reports_verified_recovery(tmp_path, monkeypatch):
    settings = replace(Settings.from_env(), runtime_dir=str(tmp_path))
    monkeypatch.setattr(incident_alert, "secret_value", lambda *args: "test")
    snapshot = {"control_plane": {"present": True, "execution_state": {
        "frozen": True, "reason": "broker_reconciliation_disagreement:position_entry_allocation_unresolved:ITA",
    }, "latest_reconciliation": {"status": "blocked"}}}
    messages = []

    def sender(token, target, message, reply):
        messages.append(message)
        return {"ok": len(messages) != 1, "message_id": len(messages)}

    assert incident_alert.publish_execution_incident(snapshot, settings, sender=sender)["status"] == "retry_pending"
    assert incident_alert.publish_execution_incident(snapshot, settings, sender=sender)["delivered"]
    assert "due exits are blocked" in messages[0]
    assert incident_alert.publish_execution_incident(snapshot, settings, sender=sender)["status"] == "already_delivered"
    snapshot["control_plane"]["execution_state"] = {"frozen": False}
    assert incident_alert.publish_execution_incident(snapshot, settings, sender=sender)["status"] == "recovery_unverified"
    snapshot["control_plane"]["latest_reconciliation"]["status"] = "passed"
    assert incident_alert.publish_execution_incident(snapshot, settings, sender=sender)["delivered"]
    assert len(messages) == 3
    assert "does not confirm a new order" in messages[-1]
