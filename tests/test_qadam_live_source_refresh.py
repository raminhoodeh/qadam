from __future__ import annotations

from datetime import datetime, timezone

from scripts.run_qadam_live_source_refresh import _new_research_goal_events


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
