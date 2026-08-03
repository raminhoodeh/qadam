from __future__ import annotations

from datetime import datetime, timezone

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
    assert rows[0]["status"] != "closed_no_trade"
    assert rows[1]["status"] == "closed_no_trade"
    assert rows[1]["close_reason"] == "non_event_provider_snapshot_or_status"

    hardening = store.harden_lifecycle()
    latest = store.latest_by_goal_id()[goal.goal_id]

    assert hardening["status"] == "ok"
    assert latest["status"] == "closed_no_trade"
    assert latest["close_reason"] == "non_event_provider_snapshot_or_status"
