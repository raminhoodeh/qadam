from datetime import datetime, timedelta, timezone
from dataclasses import replace
import json
import pytest

from orchestrator.qadam_paper_economic_review import advance_review, register_review, economic_review


def run(previous=None, *, day="2026-09-08", hour=15, ready=True, equity=100000,
        policy="frozen-policy", holiday=False, fresh=True):
    current = datetime.fromisoformat(f"{day}T{hour:02}:00:00+00:00")
    mirror = {"broker_account_fingerprint": "account", "paper_epoch_id": "epoch",
              "snapshot": {"observed_at": (current if fresh else current-timedelta(hours=1)).isoformat(),
                           "equity": equity, "cash": 99000, "broker_reconciliation_status": "ok"},
              "market_calendar": {"provider": "alpaca_calendar_v2", "observed_at": current.isoformat(),
                                  "start": "2026-09-01", "end": "2026-11-30", "sessions": [
                                      {"date": "2026-09-08" if holiday else day,
                                       "open": "09:30", "close": "16:00"}]}}
    return advance_review(previous or {}, current=current, policy_digest=policy, mirror=mirror,
                          soak={"schema_version": "qadam_catc_real_market_soak.v2", "observation_ready": ready},
                          metrics={"available": True, "independent_completed_experiments": 0,
                                   "outcome_comparison": {"net_expectancy": None, "benchmark_delta": None}})


def test_review_waits_for_soak_and_does_not_backfill_closed_days():
    state = run(ready=False)
    assert state["sessions_completed"] == 0
    assert run(state, hour=21)["activated_at"] is None
    assert run(state, day="2026-09-07", holiday=True)["activated_at"] is None
    state = run(state)
    assert len(state["sessions"]) == 1
    assert run(state, hour=21)["sessions_completed"] == 1


def test_reruns_preserve_frozen_baseline_and_unknown_economics():
    state = run()
    for _ in range(5):
        state = run(state, hour=16, equity=100200)
    assert state["baseline"]["equity_usd"] == 100000
    assert len(state["sessions"]) == 1
    assert state["comparison"]["net_experiment_return"] is None
    assert state["comparison"]["human_interventions"] is None
    assert state["automatic_risk_increase_allowed"] is False


def test_policy_change_cannot_reuse_the_old_evaluation():
    state = run()
    changed = run(state, policy="new-policy")
    assert changed["status"] == "requires_new_policy_or_account_evaluation"
    assert changed["binding"] == state["binding"]


def test_missing_measurements_remain_in_observed_sessions():
    state = run()
    state = run(state, hour=16, fresh=False)
    assert state["sessions"]["2026-09-08"]["measurement_gaps"] == ["broker_snapshot_missing_or_stale"]
    assert run(state, hour=21)["sessions_completed"] == 1


def test_twenty_observed_sessions_produce_a_review_not_authority():
    state = {}
    current = datetime(2026, 9, 8, tzinfo=timezone.utc)
    for _ in range(20):
        while current.weekday() >= 5:
            current += timedelta(days=1)
        day = current.date().isoformat()
        state = run(state, day=day)
        state = run(state, day=day, hour=21)
        current += timedelta(days=1)
    assert state["status"] == "review_due"
    assert state["sessions_completed"] == 20
    assert state["recommendation"].startswith("do_not_expand")
    assert state["broker_write_count"] == 0
    assert state["validated_edge_credit_allowed"] is False
    original = state["sessions"]
    assert run(state, day=current.date().isoformat())["sessions"] == original


@pytest.fixture
def registration_environment(tmp_path, monkeypatch):
    from orchestrator.config import Settings
    from orchestrator.qadam_control_plane_store import ControlPlaneStore, DATABASE_NAME
    import orchestrator.execution.ledger as ledger

    settings = replace(Settings.from_env(), runtime_dir=str(tmp_path), mode="paper", live_capital_enabled=False)
    store = ControlPlaneStore(tmp_path / DATABASE_NAME)
    monkeypatch.setattr(ledger, "read_operating_health", lambda _: {
        "status": "healthy", "pre_submit_reconciliation_fresh": True})
    (tmp_path / "alpaca_paper_mirror.json").write_text(json.dumps({
        "broker_account_fingerprint": "account", "paper_epoch_id": "epoch",
        "snapshot": {"observed_at": datetime.now(timezone.utc).isoformat()}}))
    (tmp_path / "qadam_active_discovery_trial_contract.json").write_text(json.dumps({
        "policy_binding": {"approved_position_limit": 5000}}))
    (tmp_path / "qadam_active_discovery_trial_status.json").write_text(json.dumps({
        "economic_evaluation": run(ready=False)}))
    return settings, store, tmp_path


def test_reviewed_registration_archives_old_state_and_is_idempotent(registration_environment):
    settings, store, runtime = registration_environment
    old = json.loads((runtime / "qadam_active_discovery_trial_status.json").read_text())["economic_evaluation"]
    with pytest.raises(ValueError):
        register_review(settings)
    approved = register_review(settings, reviewed=True)
    assert approved["previous_evaluation"] == old
    assert register_review(settings, reviewed=True)["evaluation_id"] == approved["evaluation_id"]
    with store.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM operating_events WHERE aggregate_type='paper_economic_review'").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM canonical_orders").fetchone()[0] == 0
    current = economic_review(runtime, {"approved_position_limit": 5000})
    assert current["evaluation_id"] == approved["evaluation_id"]
    assert current["status"] == "waiting_for_five_verified_sessions_then_next_observed_open"
    assert current["sessions_completed"] == 0 and current["activated_at"] is None
    assert current["registered_at"] == approved["registered_at"]
    (runtime / "qadam_active_discovery_trial_status.json").write_text(json.dumps({"economic_evaluation": current}))
    assert economic_review(runtime, {"different_policy": True})["status"] == "requires_new_policy_or_account_evaluation"


@pytest.mark.parametrize("fault", ["live", "stale", "unreconciled", "missing_policy"])
def test_registration_requires_reviewed_current_paper_truth(registration_environment, monkeypatch, fault):
    settings, store, runtime = registration_environment
    if fault == "live":
        settings = replace(settings, live_capital_enabled=True)
    elif fault == "stale":
        mirror = json.loads((runtime / "alpaca_paper_mirror.json").read_text())
        mirror["snapshot"]["observed_at"] = "2000-01-01T00:00:00+00:00"
        (runtime / "alpaca_paper_mirror.json").write_text(json.dumps(mirror))
    elif fault == "missing_policy":
        (runtime / "qadam_active_discovery_trial_contract.json").write_text("{}")
    else:
        import orchestrator.execution.ledger as ledger
        monkeypatch.setattr(ledger, "read_operating_health", lambda _: {"status": "blocked"})
    with pytest.raises(ValueError):
        register_review(settings, reviewed=True)
    with store.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM operating_events").fetchone()[0] == 0


def test_corrupt_registration_does_not_reset_or_advance_review(registration_environment):
    settings, store, runtime = registration_environment
    register_review(settings, reviewed=True)
    with store.transaction() as db:
        db.execute("UPDATE operating_events SET payload_sha256='wrong' WHERE aggregate_type='paper_economic_review'")
    result = economic_review(runtime, {"approved_position_limit": 5000})
    assert result["status"] == "economic_review_registration_unavailable"
    assert result["broker_write_count"] == 0
    with pytest.raises(ValueError):
        register_review(settings, reviewed=True)
