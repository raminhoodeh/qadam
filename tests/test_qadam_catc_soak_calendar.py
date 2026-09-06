from datetime import datetime, timezone

import pytest

from orchestrator import qadam_catc_soak as soak


@pytest.fixture
def harness(tmp_path, monkeypatch):
    payloads = {}
    history = []
    monkeypatch.setattr(soak, "runtime_dir", lambda settings: tmp_path)
    monkeypatch.setattr(soak, "read_json", lambda path: payloads.get(path.name, {}))
    monkeypatch.setattr(soak, "read_jsonl", lambda path: list(history))
    monkeypatch.setattr(soak, "append_jsonl_durable", lambda path, row: history.append(row))
    monkeypatch.setattr(soak, "write_json_atomic", lambda path, row: payloads.__setitem__(path.name, row))
    monkeypatch.setattr(soak.ControlPlaneStore, "from_settings", lambda settings: type(
        "Store", (), {"integrity_report": lambda self: {"status": "passed"}})())
    build = {"git_commit": "release-a", "dependency_lock_digest": "deps",
             "service_contract_hash": "contracts", "dirty_worktree": False}
    payloads["qadam_operator_service_status.json"] = {"build_identity": {
        "running": build, "running_build_matches_current": True}}

    def run(day="2026-09-08", hour=21, session=True, close="16:00", state="completed", exact=True):
        now = datetime.fromisoformat(f"{day}T{hour:02}:00:00+00:00")
        payloads["alpaca_paper_mirror.json"] = {"market_calendar": {
            "provider": "alpaca_calendar_v2", "observed_at": now.isoformat(),
            "start": "2026-01-01", "end": "2026-12-31",
            "sessions": [{"date": day if session else "2026-09-08",
                          "open": "09:30", "close": close}]}}
        payloads["qadam_operator_service_receipt_index.json"] = {"latest_successful_receipts": {
            service: {"receipt_id": service, "state": state,
                      "started_at": f"{day}T14:00:00Z", "completed_at": f"{day}T14:01:00Z",
                      "operator_build_identity": build if exact else {}}
            for service in soak.REQUIRED_EXECUTION_SERVICES}}
        return soak.update_real_market_soak(timestamp=now)
    return run, payloads, history, build


def test_exchange_session_counts_once_with_intraday_exact_build_work(harness):
    run, _, history, _ = harness
    assert run()["verified_same_build_session_count"] == 1
    assert run()["verified_same_build_session_count"] == 1
    assert len(history) == 1


@pytest.mark.parametrize("day", ["2026-09-07", "2026-09-06"])
def test_holiday_and_weekend_cannot_earn_soak_credit(harness, day):
    run, _, history, _ = harness
    result = run(day=day, session=False)
    assert not result["current_session_eligible"]
    assert "not_an_exchange_session" in result["current_session_errors"]
    assert not history


def test_early_close_uses_provider_close_not_fixed_four_pm(harness):
    run, _, _, _ = harness
    assert run(day="2026-11-27", hour=19, close="13:00")["current_session_after_close"]


@pytest.mark.parametrize("state,exact", [("skipped", True), ("completed", False)])
def test_skipped_or_unbound_work_cannot_count(harness, state, exact):
    run, _, _, _ = harness
    assert not run(state=state, exact=exact)["current_session_eligible"]


def test_other_build_or_legacy_five_sessions_cannot_certify_current_build(harness):
    run, _, history, build = harness
    key = soak._build_key({**build, "git_commit": "old-release"})
    for date in range(1, 6):
        history.append({"schema_version": soak.SCHEMA_VERSION, "simulated": False,
                        "backfilled": False, "build_key": key, "provider_session": {"date": date},
                        "market_session_date": f"2026-08-{date:02}"})
    result = run()
    assert result["verified_same_build_session_count"] == 1
    assert not result["observation_ready"]


def test_intraday_circuit_failure_remains_ineligible_after_recovery(harness):
    run, payloads, _, _ = harness
    payloads["qadam_operator_circuit_breakers.json"] = {"services": {
        "guarded_paperops": {"state": "open"}}}
    run(hour=15)
    payloads["qadam_operator_circuit_breakers.json"] = {}
    result = run()
    assert not result["current_session_eligible"]
    assert "execution_circuit_not_closed:guarded_paperops" in result["current_session_incidents"]


def test_missing_calendar_cannot_use_weekday_fallback(harness):
    run, payloads, _, _ = harness
    run(hour=15)
    payloads["alpaca_paper_mirror.json"] = {}
    result = soak.update_real_market_soak(timestamp=datetime(2026, 9, 8, 21, tzinfo=timezone.utc))
    assert not result["current_session_eligible"]
    assert "provider_calendar_missing_or_stale" in result["current_session_errors"]
