from datetime import datetime, timedelta, timezone

from orchestrator.qadam_paper_economic_review import advance_review


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
