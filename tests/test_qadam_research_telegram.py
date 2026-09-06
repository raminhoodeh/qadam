from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace
import urllib.error

import pytest

from orchestrator import qadam_research_telegram as reporting


NOW = datetime(2026, 9, 6, 11, 0, tzinfo=timezone.utc)


def put(path, payload, lines=False):
    path.write_text("\n".join(json.dumps(row) for row in payload) if lines else json.dumps(payload))


def fixture_data(runtime, now=NOW):
    stamp = now.isoformat()
    row = {
        "pattern_id": "p1",
        "title": "Supply constraints versus semiconductor prices",
        "strategy_family_id": "semiconductors",
        "instrument_symbols": ["SMH", "NVDA"],
        "detected_signal": "Does constrained supply precede sector repricing?",
        "direction": "conditional long",
        "current_stage": "Under historical test",
        "raw_pattern_score": 0.64,
        "fresh_source_count": 2,
        "contributing_source_count": 5,
        "freshness": {"observed_at": stamp, "is_current": True},
        "historical_evidence": {
            "validated_edge": False,
            "holdout_state": "not available",
            "summary": "After-cost performance remains unproven.",
        },
    }
    put(
        runtime / "qadam_pattern_discovery_dashboard.json",
        {"public_safe": True, "generated_at": stamp, "relationships": [row]},
    )
    event = {
        "trigger_id": "t1",
        "sample_or_fixture": False,
        "trigger_state": "active",
        "source_event_refs": ["provider:earnings:1"],
        "source_keys": ["earnings"],
        "publication_at": stamp,
        "generated_at": stamp,
        "available_at": stamp,
        "expires_at": (now + timedelta(days=1)).isoformat(),
        "strategy_family_id": "semiconductors",
        "affected_instruments": ["SMH"],
        "direction_clue": "long",
        "event_summary": "Management reports capacity booked through next year",
        "causal_classification": {"mechanism": "supply_constraint"},
    }
    put(runtime / "qadam_current_event_triggers.jsonl", [event], True)
    return row, event


@pytest.fixture
def env(tmp_path, monkeypatch):
    settings = SimpleNamespace(
        runtime_dir=str(tmp_path),
        mode="paper",
        live_capital_enabled=False,
        telegram_daily_learning_brief_enabled=True,
        telegram_daily_learning_brief_dry_run=False,
        daily_learning_automation_timezone="Asia/Dubai",
        daily_learning_automation_after_local_time="20:00",
    )
    monkeypatch.setattr(reporting, "secret_value", lambda *args: "configured-not-exposed")
    fixture_data(tmp_path)
    sent = []

    def sender(token, target, body):
        sent.append(body)
        return {"ok": True, "result": {"message_id": len(sent)}}

    def run(now=NOW, **kwargs):
        return reporting.run_research_notifications(
            settings, live=True, now=now, sender=kwargs.pop("sender", sender), **kwargs
        )

    return tmp_path, settings, sent, run


def change_event(runtime, now=NOW, suffix="2"):
    events = reporting._read(runtime / "qadam_current_event_triggers.jsonl", lines=True)
    event = deepcopy(events[0])
    event.update(
        trigger_id="t" + suffix,
        source_event_refs=["earnings:" + suffix],
        event_summary="Management raised its delivery forecast " + suffix,
        publication_at=now.isoformat(),
        generated_at=now.isoformat(),
    )
    put(runtime / "qadam_current_event_triggers.jsonl", events + [event], True)


def test_baseline_is_quiet_and_preview_does_not_consume_it(env):
    runtime, settings, sent, run = env
    reporting.run_research_notifications(settings, now=NOW)
    assert not (runtime / reporting.STATE).exists()
    result = run()
    assert result["status"] == "healthy"
    assert result["baseline_at"] == NOW.isoformat()
    assert not sent


def test_new_evidence_delivered_once_with_receipt_across_restart(env):
    runtime, _, sent, run = env
    run()
    change_event(runtime)
    assert run()["sent_this_pass"] == 1
    assert run()["sent_this_pass"] == 0
    assert len(sent) == 1
    assert "Management raised its delivery forecast" in sent[0]
    assert "SMH" in sent[0] and "not a probability of profit" in sent[0]
    assert "repeatable after-cost edge remains unproven" in sent[0]
    state = reporting._read(runtime / reporting.STATE)
    assert next(iter(state["outbox"].values()))["message_id"] == 1
    assert "configured-not-exposed" not in (runtime / reporting.STATE).read_text()


@pytest.mark.parametrize(
    "direction", ["positive_for_strategy_expression", "negative_for_strategy_expression"]
)
def test_real_trigger_factory_direction_vocabulary(env, direction):
    runtime, _, sent, run = env
    run()
    change_event(runtime)
    events = reporting._read(runtime / "qadam_current_event_triggers.jsonl", lines=True)
    events[-1]["direction_clue"] = direction
    events[-1]["causal_classification"]["mechanism"] = "strategy_supporting_event_language"
    put(runtime / "qadam_current_event_triggers.jsonl", events, True)
    assert run()["sent_this_pass"] == 1
    assert "New linked evidence" in sent[0]


def test_removed_then_returning_event_is_not_reannounced(env):
    runtime, _, sent, run = env
    run()
    events = reporting._read(runtime / "qadam_current_event_triggers.jsonl", lines=True)
    put(runtime / "qadam_current_event_triggers.jsonl", [], True)
    run()
    put(runtime / "qadam_current_event_triggers.jsonl", events, True)
    run()
    assert not sent


def test_stale_pending_alert_is_not_sent_during_provider_outage(env):
    runtime, _, sent, run = env
    run()
    change_event(runtime)
    run(sender=lambda *args: {"ok": False})
    (runtime / "qadam_pattern_discovery_dashboard.json").write_text("{}")
    run(now=NOW + timedelta(minutes=15))
    assert not sent


def test_refresh_score_and_source_counts_do_not_invent_discoveries(env):
    runtime, _, sent, run = env
    run()
    data = reporting._read(runtime / "qadam_pattern_discovery_dashboard.json")
    data["relationships"][0].update(raw_pattern_score=0.71, fresh_source_count=5)
    put(runtime / "qadam_pattern_discovery_dashboard.json", data)
    event = reporting._read(runtime / "qadam_current_event_triggers.jsonl", lines=True)[0]
    event.update(available_at=(NOW + timedelta(minutes=1)).isoformat(), trigger_id="new-wrapper-id")
    put(runtime / "qadam_current_event_triggers.jsonl", [event], True)
    run(now=NOW + timedelta(minutes=1))
    assert not sent


@pytest.mark.parametrize(
    "field,value",
    [
        ("sample_or_fixture", True),
        ("trigger_state", "expired"),
        ("source_event_refs", []),
        ("direction_clue", "ambiguous"),
        ("affected_instruments", ["UNRELATED"]),
        ("publication_at", "2027-01-01T00:00:00Z"),
        ("expires_at", "2025-01-01T00:00:00Z"),
    ],
)
def test_invalid_or_unrelated_events_never_sent(env, field, value):
    runtime, _, sent, run = env
    run()
    change_event(runtime)
    events = reporting._read(runtime / "qadam_current_event_triggers.jsonl", lines=True)
    events[-1][field] = value
    put(runtime / "qadam_current_event_triggers.jsonl", events, True)
    run()
    assert not sent


def test_new_relationship_and_changed_holdout_are_reported(env):
    runtime, _, sent, run = env
    run()
    data = reporting._read(runtime / "qadam_pattern_discovery_dashboard.json")
    second = deepcopy(data["relationships"][0])
    second["pattern_id"] = "p2"
    data["relationships"].append(second)
    put(runtime / "qadam_pattern_discovery_dashboard.json", data)
    run()
    assert sent and "New research candidate" in sent[-1]
    data["relationships"][0]["historical_evidence"].update(
        holdout_state="failed", summary="The holdout failed after costs."
    )
    put(runtime / "qadam_pattern_discovery_dashboard.json", data)
    run()
    assert "holdout failed after costs" in sent[-1]


def test_stale_evidence_and_corrupt_state_fail_closed(env):
    runtime, _, sent, run = env
    run()
    change_event(runtime)
    result = run(now=NOW + timedelta(hours=2))
    assert result["status"] == "needs_attention" and not sent
    (runtime / reporting.STATE).write_text("broken")
    assert run()["status"] == "needs_attention"
    assert (runtime / reporting.STATE).read_text() == "broken"


def test_rejection_retries_but_timeout_never_blindly_duplicates(env):
    runtime, _, sent, run = env
    run()
    change_event(runtime)
    run(sender=lambda *args: {"ok": False})
    assert run()["sent_this_pass"] == 0
    assert run(now=NOW + timedelta(minutes=15))["sent_this_pass"] == 1
    change_event(runtime, suffix="3")

    def timeout(*args):
        raise TimeoutError("secret-bearing URL must not be persisted")

    result = run(sender=timeout)
    assert result["delivery_counts"]["delivery_uncertain"] == 1
    run()
    assert len(sent) == 1
    assert "secret-bearing" not in (runtime / reporting.STATE).read_text()


def test_crash_in_sending_becomes_uncertain(env):
    runtime, _, _, run = env
    run()
    change_event(runtime)
    run(sender=lambda *args: {"ok": False})
    state = reporting._read(runtime / reporting.STATE)
    next(iter(state["outbox"].values()))["status"] = "sending"
    put(runtime / reporting.STATE, state)
    assert run()["delivery_counts"]["delivery_uncertain"] == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("telegram_daily_learning_brief_dry_run", True),
        ("telegram_daily_learning_brief_enabled", False),
        ("mode", "live"),
        ("live_capital_enabled", True),
    ],
)
def test_delivery_flags_and_paper_boundary(env, field, value):
    runtime, settings, sent, run = env
    run()
    change_event(runtime)
    setattr(settings, field, value)
    result = run()
    assert result["status"] == "needs_attention" and not sent
    assert result["broker_write_allowed"] is False
    assert result["strategy_mutation_allowed"] is False


def strategy_data(runtime, now):
    fixture_data(runtime, now)
    h = {
        "generated_at": now.isoformat(),
        "strategy_version_id": "v1",
        "freshness": {"expires_at": (now + timedelta(days=1)).isoformat()},
        "direction_horizon": {
            "direction": "long",
            "horizon": "5d_forward",
            "direction_resolution_evidence_ids": ["t1"],
        },
        "candidate_identity_material": {"strategy_family_id": "semiconductors"},
        "instrument_proxy_mapping": {"execution_proxy": "SMH"},
        "evidence_class": "experimental_unvalidated",
        "hypothesis_state": "ready_for_akber_review",
        "entry_concept": {"entry_authorized": False},
        "invalidation_exit": {
            "invalidation_conditions": ["price confirmation reverses"],
            "exit_conditions": ["horizon completes"],
        },
        "market_judgment": {"primary_consequence": "delayed_entry"},
    }
    put(runtime / "qadam_strategy_hypotheses_v3.jsonl", [h], True)
    put(
        runtime / "qadam_router_v3_why_not_trading_now.json",
        {
            "generated_at": now.isoformat(),
            "current_router_state": "hold",
            "primary_reason": "Waiting for current liquidity evidence.",
        },
    )


def test_strategy_once_each_actual_local_evening_and_truthfully_unchanged(env):
    runtime, _, sent, run = env
    evening = NOW.replace(hour=16)
    strategy_data(runtime, evening)
    assert run(now=evening - timedelta(minutes=1))["sent_this_pass"] == 0
    assert run(now=evening)["sent_this_pass"] == 1
    assert "SMH: long" in sent[-1] and "capacity booked" in sent[-1]
    assert "price confirmation reverses" in sent[-1] and "unvalidated" in sent[-1]
    assert "Waiting for current liquidity" in sent[-1]
    assert run(now=evening + timedelta(minutes=5))["sent_this_pass"] == 0
    tomorrow = evening + timedelta(days=1)
    # Regenerating wrapper timestamps/IDs does not change the strategy explanation.
    hypotheses = reporting._read(runtime / "qadam_strategy_hypotheses_v3.jsonl", lines=True)
    hypotheses[0]["generated_at"] = tomorrow.isoformat()
    hypotheses[0]["freshness"]["expires_at"] = (tomorrow + timedelta(days=1)).isoformat()
    put(runtime / "qadam_strategy_hypotheses_v3.jsonl", hypotheses, True)
    events = reporting._read(runtime / "qadam_current_event_triggers.jsonl", lines=True)
    events[0].update(
        generated_at=tomorrow.isoformat(), expires_at=(tomorrow + timedelta(days=1)).isoformat()
    )
    put(runtime / "qadam_current_event_triggers.jsonl", events, True)
    router = reporting._read(runtime / "qadam_router_v3_why_not_trading_now.json")
    router["generated_at"] = tomorrow.isoformat()
    put(runtime / "qadam_router_v3_why_not_trading_now.json", router)
    run(now=tomorrow)
    assert "unchanged since the previous strategy update" in sent[-1]
    assert len(sent) == 2


def test_strategy_no_backfill_and_missing_research_does_not_block_honest_daily_note(env):
    runtime, _, sent, run = env
    evening = NOW.replace(hour=16)
    (runtime / "qadam_pattern_discovery_dashboard.json").write_text("partial json")
    run(now=evening)
    assert len(sent) == 1 and "No fresh directional strategy hypothesis" in sent[0]
    run(now=evening + timedelta(hours=8))
    assert len(sent) == 1


def test_pending_daily_strategy_refreshes_before_retry(env):
    runtime, _, sent, run = env
    evening = NOW.replace(hour=16)
    strategy_data(runtime, evening)
    run(now=evening, sender=lambda *args: {"ok": False})
    put(runtime / "qadam_strategy_hypotheses_v3.jsonl", [], True)
    run(now=evening + timedelta(minutes=15))
    assert "No fresh directional strategy hypothesis" in sent[-1]


def test_real_strategy_version_change_is_not_described_as_unchanged(env):
    runtime, _, _, _ = env
    strategy_data(runtime, NOW)
    snapshot = reporting.strategy_snapshot(runtime, NOW)
    _, fingerprint = reporting.strategy_message(snapshot, None, "2026-09-06")
    snapshot["strategies"][0]["version"] = "new-reviewed-definition"
    body, _ = reporting.strategy_message(snapshot, {"fingerprint": fingerprint}, "2026-09-07")
    assert "unchanged" not in body


def test_daily_body_fits_telegram_with_many_strategies(env):
    runtime, _, _, _ = env
    strategy_data(runtime, NOW)
    snapshot = reporting.strategy_snapshot(runtime, NOW)
    snapshot["strategies"] *= 10
    body, _ = reporting.strategy_message(snapshot, None, "2026-09-06")
    assert len(body) < 3900 and "additional hypotheses" in body


def test_router_explanation_requires_exact_strategy_version_and_hypothesis(env):
    runtime, _, _, _ = env
    strategy_data(runtime, NOW)
    h = reporting._read(runtime / "qadam_strategy_hypotheses_v3.jsonl", lines=True)[0]
    h["hypothesis_id"] = "h1"
    put(runtime / "qadam_strategy_hypotheses_v3.jsonl", [h], True)
    decision = {
        "generated_at": NOW.isoformat(),
        "hypothesis_id": "h1",
        "lineage": {"strategy_version_id": "v1"},
        "hard_vetoes": ["duplicate_exposure_conflict"],
    }
    put(runtime / "qadam_router_v3_decisions.jsonl", [decision], True)
    assert reporting.strategy_snapshot(runtime, NOW)["strategies"][0]["vetoes"] == [
        "duplicate_exposure_conflict"
    ]
    decision["lineage"]["strategy_version_id"] = "old-version"
    put(runtime / "qadam_router_v3_decisions.jsonl", [decision], True)
    assert not reporting.strategy_snapshot(runtime, NOW)["strategies"][0]["vetoes"]


def test_unsafe_source_text_never_leaks(env):
    runtime, _, sent, run = env
    run()
    change_event(runtime)
    events = reporting._read(runtime / "qadam_current_event_triggers.jsonl", lines=True)
    events[-1]["event_summary"] = "/Users/private/secret.txt"
    put(runtime / "qadam_current_event_triggers.jsonl", events, True)
    assert run()["delivery_counts"]["unsafe"] == 1
    assert not sent


def test_notification_health_reports_failure_and_stale_scheduler(env):
    runtime, _, _, run = env
    run()
    assert reporting.notification_health(runtime, NOW)[0] == "healthy"
    assert reporting.notification_health(runtime, NOW + timedelta(minutes=16))[0] == "stale"
    change_event(runtime)
    run(sender=lambda *args: {"ok": False})
    assert reporting.notification_health(runtime, NOW)[0] == "needs_attention"


def test_queue_is_bounded_per_pass_and_expired_messages_are_visible(env):
    runtime, _, sent, run = env
    run()
    data = reporting._read(runtime / "qadam_pattern_discovery_dashboard.json")
    for i in range(5):
        row = deepcopy(data["relationships"][0])
        row["pattern_id"] = f"new-{i}"
        data["relationships"].append(row)
    put(runtime / "qadam_pattern_discovery_dashboard.json", data)
    result = run()
    assert len(sent) == 3 and result["delivery_counts"]["pending"] == 2
    result = run(now=NOW + timedelta(hours=2))
    assert result["delivery_counts"]["expired_unsent"] == 2
    assert result["status"] == "needs_attention"


def test_http_rejection_does_not_record_token_url(env):
    runtime, _, _, run = env
    run()
    change_event(runtime)

    def reject(*args):
        raise urllib.error.HTTPError("secret-token-url", 429, "rate limited", {}, None)

    run(sender=reject)
    assert "secret-token-url" not in (runtime / reporting.STATE).read_text()


def test_scheduler_calls_notification_pass_before_daily_due_guard():
    from pathlib import Path

    text = (Path(__file__).parents[1] / "scripts/run_scheduled_daily_learning_brief.py").read_text()
    assert text.index("notification = run_research_notifications") < text.index(
        'if decision["should_run"]'
    )
