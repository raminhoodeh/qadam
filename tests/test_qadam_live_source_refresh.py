from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import replace
from types import SimpleNamespace

import pytest

from orchestrator.phase1_live_adapters import (
    PHASE1_LIVE_ADAPTERS,
    Phase1ReadOnlyAdapter,
)
from orchestrator.research_goal import ResearchGoalStore
from scripts.run_qadam_live_source_refresh import (
    _close_non_event_research_goals,
    _new_research_goal_events,
)


NOW = datetime(2026, 8, 2, 10, 0, tzinfo=timezone.utc)


def _event(*, observed_at: str, summary: str = "Oil shipping disruption reported") -> dict:
    return {
        "event_id": "provider-random-id",
        "normalised_summary": summary,
        "ingested_at": observed_at,
        "raw_payload": {"record_id": "provider-record-1", "sample": False},
    }


def test_selects_only_fresh_real_provider_events() -> None:
    selected, counts = _new_research_goal_events(
        "conflict_tracker",
        {
            "events": [
                _event(observed_at="2026-08-02T09:30:00+00:00"),
                _event(
                    observed_at="2026-07-20T09:30:00+00:00",
                    summary="Old disruption report",
                ),
                {
                    **_event(observed_at="2026-08-02T09:45:00+00:00"),
                    "raw_payload": {"record_id": "sample", "sample": True},
                },
            ]
        },
        seen_event_refs=set(),
        now=NOW,
    )

    assert len(selected) == 1
    assert selected[0]["event_ref"].startswith("conflict_tracker:event:")
    assert counts["stale"] == 1
    assert counts["sample"] == 1


def test_stable_fingerprint_suppresses_provider_random_id_duplicates() -> None:
    result = {"events": [_event(observed_at="2026-08-02T09:30:00+00:00")]}
    first, _counts = _new_research_goal_events(
        "conflict_tracker", result, seen_event_refs=set(), now=NOW
    )
    duplicate_event = {
        **_event(observed_at="2026-08-02T09:45:00+00:00"),
        "event_id": "different-random-id-on-second-fetch",
    }
    second, counts = _new_research_goal_events(
        "conflict_tracker",
        {"events": [duplicate_event]},
        seen_event_refs={first[0]["event_ref"]},
        now=NOW,
    )

    assert second == []
    assert counts["duplicate"] == 1


def test_derived_status_record_cannot_become_research_evidence() -> None:
    event = _event(
        observed_at="2026-08-02T09:30:00+00:00",
        summary="Derived conflict tracker status",
    )
    event["raw_payload"] = {
        "record_id": "derived-conflict-tracker-status",
        "sample": False,
        "derived": True,
        "status_only": True,
        "event_evidence_eligible": False,
    }

    selected, counts = _new_research_goal_events(
        "conflict_tracker",
        {"events": [event]},
        seen_event_refs=set(),
        now=NOW,
    )

    assert selected == []
    assert counts["non_event_status"] == 1


def test_live_adapter_preserves_non_event_evidence_boundary() -> None:
    adapter = object.__new__(Phase1ReadOnlyAdapter)
    adapter.config = PHASE1_LIVE_ADAPTERS["conflict_tracker"]

    events = adapter.normalize_payload(
        {
            "records": [
                {
                    "id": "derived-conflict-tracker-status",
                    "title": "Derived conflict tracker status",
                    "observed_at": "2026-08-02T09:30:00+00:00",
                    "derived": True,
                    "status_only": True,
                    "event_evidence_eligible": False,
                }
            ]
        }
    )

    assert len(events) == 1
    assert events[0].raw_payload["derived"] is True
    assert events[0].raw_payload["status_only"] is True
    assert events[0].raw_payload["event_evidence_eligible"] is False


def test_fetch_timestamp_and_fallback_summary_cannot_become_research_evidence() -> None:
    event = _event(
        observed_at="2026-08-02T09:30:00+00:00",
        summary="ECB series observation available for liquidity, rates, or EUR macro context.",
    )
    event["raw_payload"] = {
        "record_id": None,
        "sample": False,
        "event_timestamp_fallback_to_fetch_time": True,
        "summary_fallback_to_source_description": True,
    }

    selected, counts = _new_research_goal_events(
        "ecb",
        {"events": [event]},
        seen_event_refs=set(),
        now=NOW,
    )

    assert selected == []
    assert counts["non_event_fetch_snapshot"] == 1


def test_nested_provider_timestamp_is_preserved_for_real_event() -> None:
    adapter = object.__new__(Phase1ReadOnlyAdapter)
    adapter.config = PHASE1_LIVE_ADAPTERS["usgs"]

    events = adapter.normalize_payload(
        {
            "features": [
                {
                    "id": "earthquake-1",
                    "properties": {
                        "title": "M 5.0 - test event",
                        "time": 1785748666000,
                    },
                }
            ]
        }
    )

    assert events[0].ingested_at == "2026-08-03T09:17:46+00:00"
    assert events[0].raw_payload["provider_timestamp_present"] is True
    assert events[0].raw_payload["event_timestamp_fallback_to_fetch_time"] is False
    assert events[0].raw_payload["summary_fallback_to_source_description"] is False


def test_old_fallback_summary_goal_is_closed_append_only(tmp_path) -> None:
    store = ResearchGoalStore(path=tmp_path / "research_goals.jsonl")
    goal = store.add_from_observation(
        summary="ECB series observation available for liquidity, rates, or EUR macro context.",
        source_event_refs=("ecb:event:status",),
        origin="live_source",
        observed_at="2026-08-02T09:30:00+00:00",
    )

    closed_count = _close_non_event_research_goals(store=store, now=NOW)
    rows = store.read()

    assert closed_count == 1
    assert len(rows) == 2
    assert rows[0]["goal_id"] == goal.goal_id
    assert rows[0].get("close_reason") != "non_event_provider_snapshot_or_status"
    assert rows[1]["status"] == "closed_no_trade"
    assert rows[1]["close_reason"] == "non_event_provider_snapshot_or_status"

    hardening = store.harden_lifecycle()
    latest = store.latest_by_goal_id()[goal.goal_id]

    assert hardening["status"] == "ok"
    assert latest["status"] == "closed_no_trade"
    assert latest["close_reason"] == "non_event_provider_snapshot_or_status"


def _ingestion(tmp_path, monkeypatch, count=5):
    from orchestrator.config import Settings
    from scripts import run_qadam_live_source_refresh as runner
    settings = replace(Settings.from_env(), runtime_dir=str(tmp_path))
    events = []
    for index in range(count):
        event = _event(observed_at="2026-08-02T09:30:00+00:00", summary=f"Oil supply event {index}")
        event["raw_payload"]["record_id"] = f"event-{index}"
        events.append(event)
    kwargs = dict(settings=settings, runtime=tmp_path, selected=["conflict_tracker"],
                  validations={"conflict_tracker": SimpleNamespace(freshness_evidence_eligible=True)},
                  captured_results={"conflict_tracker": {"events": events}}, now=NOW)
    return runner, settings, kwargs


def test_capacity_limited_events_are_pending_not_acknowledged_and_drain_without_refetch(tmp_path, monkeypatch):
    runner, settings, kwargs = _ingestion(tmp_path, monkeypatch)
    first = runner._ingest_research_goals(**kwargs)
    assert first["created_goal_count"] == 2
    assert len(first["seen_event_refs"]) == 2
    assert first["pending_event_count"] == 3
    assert first["completeness_state"] == "bounded_pending"
    no_fetch = {**kwargs, "selected": [], "captured_results": {}}
    second = runner._ingest_research_goals(**no_fetch)
    third = runner._ingest_research_goals(**no_fetch)
    assert [second["created_goal_count"], third["created_goal_count"]] == [2, 1]
    assert third["pending_event_count"] == 0
    replay = runner._ingest_research_goals(**kwargs)
    assert replay["created_goal_count"] == 0
    assert replay["material_change_detected"] is False
    assert len(ResearchGoalStore(settings=settings).read()) == 5
    assert all(not row["paper_order_allowed"] for row in ResearchGoalStore(settings=settings).read())


def test_crash_after_goal_append_reconciles_without_duplicate_goal_or_loss(tmp_path, monkeypatch):
    runner, settings, kwargs = _ingestion(tmp_path, monkeypatch)
    write = runner.write_json_atomic
    def fail_ack(path, payload):
        if payload.get("status") == "ok":
            raise OSError("fixture crash before cursor acknowledgement")
        return write(path, payload)
    monkeypatch.setattr(runner, "write_json_atomic", fail_ack)
    with pytest.raises(OSError, match="fixture crash"):
        runner._ingest_research_goals(**kwargs)
    assert len(ResearchGoalStore(settings=settings).read()) == 2
    monkeypatch.setattr(runner, "write_json_atomic", write)
    runner._ingest_research_goals(**{**kwargs, "selected": [], "captured_results": {}})
    runner._ingest_research_goals(**{**kwargs, "selected": [], "captured_results": {}})
    assert len(ResearchGoalStore(settings=settings).read()) == 5


def test_duplicate_events_within_one_batch_do_not_consume_research_capacity():
    event = _event(observed_at="2026-08-02T09:30:00+00:00")
    selected, counts = _new_research_goal_events(
        "conflict_tracker", {"events": [event, event]}, seen_event_refs=set(), now=NOW,
    )
    assert len(selected) == 1
    assert counts["duplicate"] == 1


def test_overflow_and_expiry_are_explicit_and_not_completed(tmp_path, monkeypatch):
    runner, _settings, kwargs = _ingestion(tmp_path, monkeypatch)
    monkeypatch.setattr(runner, "MAX_PENDING_RESEARCH_EVENTS", 3)
    first = runner._ingest_research_goals(**kwargs)
    assert first["event_counts"]["queue_overflow_not_acknowledged"] == 2
    assert len(first["seen_event_refs"]) == 2
    assert first["completeness_state"] == "backpressure_provider_replay_required"
    from datetime import timedelta
    expired = runner._ingest_research_goals(**{**kwargs, "selected": [], "now": NOW + timedelta(days=4)})
    assert expired["created_goal_count"] == 0
    assert expired["event_counts"]["pending_expired"] == 1
    assert expired["provider_replay_required"] is True
    assert expired["completeness_state"] == "backpressure_provider_replay_required"


def test_busy_sources_do_not_starve_later_sources(tmp_path, monkeypatch):
    runner, _settings, kwargs = _ingestion(tmp_path, monkeypatch)
    monkeypatch.setattr(runner, "MAX_RESEARCH_GOAL_SOURCES_PER_CYCLE", 1)
    kwargs["selected"].append("gdelt")
    kwargs["validations"]["gdelt"] = SimpleNamespace(freshness_evidence_eligible=True)
    kwargs["captured_results"]["gdelt"] = kwargs["captured_results"]["conflict_tracker"]
    first = runner._ingest_research_goals(**kwargs)
    second = runner._ingest_research_goals(**{**kwargs, "selected": [], "captured_results": {}})
    assert {row["source_key"] for row in first["created_goals"]} == {"conflict_tracker"}
    assert {row["source_key"] for row in second["created_goals"]} == {"gdelt"}


def test_secret_like_provider_content_is_rejected_before_pending_or_goal_write(tmp_path, monkeypatch):
    runner, settings, kwargs = _ingestion(tmp_path, monkeypatch, count=1)
    forbidden = "ghp_" + "x" * 30
    kwargs["captured_results"]["conflict_tracker"]["events"][0]["normalised_summary"] = forbidden
    result = runner._ingest_research_goals(**kwargs)
    assert result["created_goal_count"] == 0
    assert result["event_counts"]["secret_like_content"] == 1
    assert forbidden not in (tmp_path / runner.RESEARCH_GOAL_INGESTION_ARTIFACT).read_text()
    assert ResearchGoalStore(settings=settings).read() == ()


def test_corrupt_or_future_pending_event_is_not_replayed(tmp_path, monkeypatch):
    runner, settings, kwargs = _ingestion(tmp_path, monkeypatch, count=0)
    runner.write_json_atomic(tmp_path / runner.RESEARCH_GOAL_INGESTION_ARTIFACT, {
        "pending_events": [{"event_ref": "incomplete", "source_key": "gdelt"}, {
            "event_ref": "future", "source_key": "gdelt", "summary": "Oil event",
            "observed_at": NOW.isoformat(), "available_at": "2099-01-01T00:00:00+00:00"}],
    })
    result = runner._ingest_research_goals(**kwargs)
    assert result["created_goal_count"] == 0
    assert result["event_counts"]["pending_invalid"] == 2
    assert ResearchGoalStore(settings=settings).read() == ()
