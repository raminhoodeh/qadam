from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.event_log import EventLog  # noqa: E402


def test_read_recent_entries_returns_only_requested_tail(tmp_path):
    event_log = EventLog(path=tmp_path / "events.jsonl", echo=False)
    for index in range(12):
        event_log.write(
            "test_event",
            "test_component",
            {"index": index},
            correlation_id=f"event-{index}",
        )

    recent = event_log.read_recent_entries(3)

    assert [entry.payload["index"] for entry in recent] == [9, 10, 11]


def test_read_recent_entries_ignores_blank_trailing_lines(tmp_path):
    path = tmp_path / "events.jsonl"
    event_log = EventLog(path=path, echo=False)
    event_log.write("first", "test", {"index": 1})
    event_log.write("second", "test", {"index": 2})
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n\n")

    recent = event_log.read_recent_entries(1)

    assert len(recent) == 1
    assert recent[0].event_type == "second"


def test_health_streams_and_validates_log_without_using_replay(tmp_path, monkeypatch):
    event_log = EventLog(path=tmp_path / "events.jsonl", echo=False)
    for index in range(5):
        event_log.write("test_event", "test", {"index": index})
    monkeypatch.setattr(
        event_log,
        "replay",
        lambda: (_ for _ in ()).throw(AssertionError("health must not materialize replay")),
    )

    health = event_log.health()

    assert health["status"] == "ok"
    assert health["events_on_disk"] == 5


def test_health_reports_invalid_event_line(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text(json.dumps({"schema_version": 1}) + "\n", encoding="utf-8")

    health = EventLog(path=path, echo=False).health()

    assert health["status"] == "degraded"
    assert "invalid event log line 1" in health["error"]
