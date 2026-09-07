from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import json

import pytest

from orchestrator.qadam_exchange_calendar import (
    calendar_cache_reusable, calendar_phase, elapsed_market_seconds,
)
from orchestrator.qadam_operator_dashboard import (
    EF11_DASHBOARD_ARTIFACT, EF11_CERTIFICATION_ARTIFACT, FRESHNESS_SPECS,
    build_freshness_audit,
)
from orchestrator.runtime.freshness import ARTIFACT_REFRESH_SERVICES, artifact_refresh_services
from orchestrator.runtime.operator import _build_repair_queue, _scheduled_market_is_open


def calendar(now, sessions=None):
    return {
        "provider": "alpaca_calendar_v2", "observed_at": now,
        "start": "2026-09-01", "end": "2026-09-30",
        "sessions": sessions or [
            {"date": "2026-09-03", "open": "09:30", "close": "16:00"},
            {"date": "2026-09-04", "open": "09:30", "close": "16:00"},
            {"date": "2026-09-08", "open": "09:30", "close": "16:00"},
        ],
    }


def audit(tmp_path, monkeypatch, now, *, artifact_time="2026-09-04T20:00:56+00:00", receipt=None):
    monkeypatch.setattr("orchestrator.qadam_operator_dashboard.runtime_dir", lambda _: tmp_path)
    for filename in FRESHNESS_SPECS:
        generated = artifact_time if filename.startswith("qadam_ef11_") else now
        (tmp_path / filename).write_text(json.dumps({"generated_at": generated}))
    (tmp_path / "alpaca_paper_mirror.json").write_text(json.dumps({"market_calendar": receipt if receipt is not None else calendar(now)}))
    result = build_freshness_audit(generated_at=now)
    records = {row["artifact"].split("/")[-1]: row for row in result["records"]}
    return result, records[EF11_DASHBOARD_ARTIFACT]


@pytest.mark.parametrize("now,phase", [
    ("2026-09-06T15:00:00+00:00", "weekend"),
    ("2026-09-07T15:00:00+00:00", "holiday"),
    ("2026-09-08T13:29:59+00:00", "pre_market"),
])
def test_closed_session_carry_forward_survives_long_weekend_without_fake_freshness(tmp_path, monkeypatch, now, phase):
    result, record = audit(tmp_path, monkeypatch, now)
    assert result["provider_calendar_phase"] == phase
    assert result["not_due_market_closed_count"] == 2
    assert result["fresh_count"] == 11
    assert result["stale_count"] == 0
    assert record["freshness_state"] == "not_due_market_closed"
    assert record["generated_at"] == "2026-09-04T20:00:56+00:00"
    assert record["elapsed_market_seconds"] == 0
    assert record["display_label_required"] is True
    assert record["stale_after_seconds"] == 1800
    assert _scheduled_market_is_open(datetime.fromisoformat(now), tmp_path) is False
    (tmp_path / "qadam_operator_dashboard_freshness.json").write_text(json.dumps(result))
    queue = _build_repair_queue(tmp_path, service_installed=True, process_running=True, generated_at=now)
    assert queue["open_request_count"] == 0


def test_next_open_requires_new_conversion_evidence(tmp_path, monkeypatch):
    now = "2026-09-08T13:30:00+00:00"
    result, record = audit(tmp_path, monkeypatch, now)
    assert record["freshness_state"] == "awaiting_open_revalidation"
    assert record["generated_at"] == "2026-09-04T20:00:56+00:00"
    assert record["display_label_required"] is True
    assert result["fresh_count"] == 11
    assert _scheduled_market_is_open(datetime.fromisoformat(now), tmp_path) is True
    now = "2026-09-08T14:00:01+00:00"
    result, record = audit(tmp_path, monkeypatch, now)
    assert record["freshness_state"] == "stale"
    assert result["stale_count"] == 2
    (tmp_path / "qadam_operator_dashboard_freshness.json").write_text(json.dumps(result))
    queue = _build_repair_queue(tmp_path, service_installed=True, process_running=True, generated_at=now)
    assert queue["open_request_count"] == 1
    assert artifact_refresh_services(queue["requests"][0]["evidence"]["artifacts"]) == {
        "market_price_refresh", "open_market_conversion", "dashboard_refresh", "public_status_publication",
    }


def test_actual_producer_refresh_clears_open_session_repair(tmp_path, monkeypatch):
    now = "2026-09-08T14:00:01+00:00"
    result, record = audit(tmp_path, monkeypatch, now, artifact_time=now)
    assert record["freshness_state"] == "fresh"
    assert result["fresh_count"] == len(FRESHNESS_SPECS)
    assert result["awaiting_open_revalidation_count"] == 0


@pytest.mark.parametrize("artifact_time", ["2026-09-03T20:00:00+00:00", "2026-09-04T18:00:00+00:00", "2026-09-07T16:00:00+00:00"])
def test_holiday_cannot_hide_missed_open_session_or_future_evidence(tmp_path, monkeypatch, artifact_time):
    result, record = audit(tmp_path, monkeypatch, "2026-09-07T15:00:00+00:00", artifact_time=artifact_time)
    assert record["freshness_state"] == "stale"
    assert result["not_due_market_closed_count"] == 0


@pytest.mark.parametrize("change", ["missing", "expired", "future", "coverage", "malformed", "wrong_provider"])
def test_unverified_calendar_cannot_waive_freshness(tmp_path, monkeypatch, change):
    now = "2026-09-07T15:00:00+00:00"
    receipt = calendar(now)
    if change == "missing":
        receipt = {}
    elif change == "expired":
        receipt["observed_at"] = "2026-09-07T08:00:00+00:00"
    elif change == "future":
        receipt["observed_at"] = "2026-09-07T16:00:00+00:00"
    elif change == "coverage":
        receipt["start"] = "2026-09-08"
    elif change == "malformed":
        receipt["sessions"][0]["close"] = "invalid"
    else:
        receipt["provider"] = "weekday_guess"
    result, record = audit(tmp_path, monkeypatch, now, receipt=receipt)
    assert record["freshness_state"] == "stale"
    assert result["provider_calendar_phase"] == "unavailable"


def test_early_close_is_provider_backed_and_requires_latest_session_work(tmp_path, monkeypatch):
    now = "2026-09-08T18:00:00+00:00"
    receipt = calendar(now, [{"date": "2026-09-08", "open": "09:30", "close": "13:00"}])
    result, record = audit(tmp_path, monkeypatch, now, artifact_time="2026-09-08T17:00:00+00:00", receipt=receipt)
    assert result["provider_calendar_phase"] == "post_market"
    assert record["freshness_state"] == "not_due_market_closed"
    assert not _scheduled_market_is_open(datetime.fromisoformat(now), tmp_path)


def test_clock_calendar_disagreement_cannot_waive_freshness(tmp_path, monkeypatch):
    now = "2026-09-07T15:00:00+00:00"
    audit(tmp_path, monkeypatch, now)
    (tmp_path / "alpaca_paper_mirror.json").write_text(json.dumps({
        "market_calendar": calendar(now), "market_clock": {"timestamp": now, "is_open": True},
        "snapshot": {"observed_at": now},
    }))
    result = build_freshness_audit(generated_at=now)
    assert result["not_due_market_closed_count"] == 0
    assert result["stale_count"] == 2


def test_missing_artifact_is_not_carried_forward(tmp_path, monkeypatch):
    now = "2026-09-07T15:00:00+00:00"
    audit(tmp_path, monkeypatch, now)
    (tmp_path / EF11_CERTIFICATION_ARTIFACT).unlink()
    result = build_freshness_audit(generated_at=now)
    assert result["missing_count"] == 1


@pytest.mark.parametrize("offset,expected", [(0.01, "fresh"), (6, "stale")])
def test_concurrent_publication_is_not_confused_with_future_dating(tmp_path, monkeypatch, offset, expected):
    now = datetime(2026, 9, 7, 15, tzinfo=timezone.utc)
    _result, record = audit(tmp_path, monkeypatch, now.isoformat(), artifact_time=(now + timedelta(seconds=offset)).isoformat())
    assert record["freshness_state"] == expected


def test_market_seconds_uses_dst_and_requires_coverage():
    now = "2026-11-02T16:00:00+00:00"
    receipt = {**calendar(now), "start": "2026-10-01", "end": "2026-11-30", "sessions": [
        {"date": "2026-10-30", "open": "09:30", "close": "16:00"},
        {"date": "2026-11-02", "open": "09:30", "close": "16:00"},
    ]}
    assert calendar_phase(datetime.fromisoformat(now), receipt) == "regular"
    assert elapsed_market_seconds(datetime.fromisoformat("2026-10-30T20:00:00+00:00"), datetime.fromisoformat(now), receipt) == 5400
    assert elapsed_market_seconds(datetime.fromisoformat("2026-09-30T20:00:00+00:00"), datetime.fromisoformat(now), receipt) is None


def test_calendar_cache_refreshes_before_validity_gap():
    now = datetime(2026, 9, 7, 15, tzinfo=timezone.utc)
    assert calendar_cache_reusable(calendar((now - timedelta(hours=5)).isoformat()), now)
    assert not calendar_cache_reusable(calendar((now - timedelta(hours=5, minutes=50)).isoformat()), now)
    assert not calendar_cache_reusable(calendar((now + timedelta(seconds=1)).isoformat()), now)


def test_mirror_refreshes_calendar_before_expiration(tmp_path, monkeypatch):
    from orchestrator import paper_account

    now = datetime(2026, 9, 7, 15, tzinfo=timezone.utc)

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return now

    monkeypatch.setattr(paper_account, "datetime", Clock)
    cached = calendar((now - timedelta(hours=5, minutes=50)).isoformat())
    (tmp_path / "alpaca_paper_mirror.json").write_text(json.dumps({"market_calendar": cached}))
    mirror = object.__new__(paper_account.AlpacaReadOnlyPaperMirror)
    mirror.settings = SimpleNamespace(runtime_dir=str(tmp_path))
    calls = []

    def get(path, **kwargs):
        calls.append(path)
        return cached["sessions"]

    mirror._get = get
    refreshed = mirror._calendar_receipt()
    assert calls == ["/calendar"]
    assert refreshed["observed_at"] == now.isoformat()


def test_every_monitored_artifact_has_explicit_recovery_owner():
    from orchestrator.qadam_reliability_critic import _operator_full_heal_allowed
    assert set(FRESHNESS_SPECS) == set(ARTIFACT_REFRESH_SERVICES)
    assert all(_operator_full_heal_allowed(owner) for owners in ARTIFACT_REFRESH_SERVICES.values() for owner in owners)
    assert artifact_refresh_services(["../../qadam_router_v3_scoreboard.json"]) is None
    assert artifact_refresh_services(["unknown.json"]) is None


@pytest.mark.parametrize("age_minutes,usable", [(350, True), (370, False)])
def test_failed_calendar_renewal_preserves_only_unexpired_provider_receipt(tmp_path, monkeypatch, age_minutes, usable):
    from orchestrator import paper_account
    now = datetime(2026, 9, 7, 15, tzinfo=timezone.utc)

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return now

    monkeypatch.setattr(paper_account, "datetime", Clock)
    cached = calendar((now - timedelta(minutes=age_minutes)).isoformat())
    (tmp_path / "alpaca_paper_mirror.json").write_text(json.dumps({"market_calendar": cached}))
    mirror = object.__new__(paper_account.AlpacaReadOnlyPaperMirror)
    mirror.settings = SimpleNamespace(runtime_dir=str(tmp_path))

    def get(*args, **kwargs):
        raise TimeoutError("provider temporarily unavailable")

    mirror._get = get
    result = mirror._calendar_receipt()
    if usable:
        assert result == cached
    else:
        assert result["status"] == "unavailable"
