"""Append-only Event Log.

Phase 0 writes to a local JSONL file so the system can replay state before
Postgres is running. The SQL migration in `migrations/` defines the durable
Timescale-backed target for the same event shape.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from orchestrator.config import Settings

EVENT_LOG_SCHEMA_VERSION = 1
VALID_SEVERITIES = {"debug", "info", "warning", "error", "critical"}


@dataclass(frozen=True)
class EventLogEntry:
    schema_version: int
    event_type: str
    component: str
    severity: str
    payload: dict[str, Any]
    correlation_id: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EventLog:
    def __init__(self, path: str | Path | None = None, *, echo: bool = True) -> None:
        settings = Settings.from_env()
        self.path = Path(path or Path(settings.runtime_dir) / "event_log.jsonl")
        self.echo = echo
        self._entries: list[EventLogEntry] = []
        self._last_write_at: str | None = None
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(
        self,
        event_type: str,
        component: str,
        payload: dict[str, Any] | None = None,
        severity: str = "info",
        correlation_id: str | None = None,
    ) -> EventLogEntry:
        if severity not in VALID_SEVERITIES:
            raise ValueError(f"invalid event severity: {severity}")

        entry = EventLogEntry(
            schema_version=EVENT_LOG_SCHEMA_VERSION,
            event_type=event_type,
            component=component,
            severity=severity,
            payload=payload or {},
            correlation_id=correlation_id or str(uuid4()),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._entries.append(entry)
        self._last_write_at = entry.created_at

        encoded = json.dumps(entry.to_dict(), sort_keys=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(encoded + "\n")
        if self.echo:
            print(encoded, flush=True)
        return entry

    def read_entries(self) -> tuple[EventLogEntry, ...]:
        entries: list[EventLogEntry] = []
        if not self.path.exists():
            return tuple(entries)

        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    payload = json.loads(stripped)
                    entries.append(EventLogEntry(**payload))
                except (TypeError, json.JSONDecodeError) as exc:
                    raise ValueError(f"invalid event log line {line_number} in {self.path}") from exc
        return tuple(entries)

    def read_recent_entries(self, limit: int) -> tuple[EventLogEntry, ...]:
        """Read a bounded tail without materializing the complete audit log."""

        if limit <= 0 or not self.path.exists():
            return ()

        chunk_size = 64 * 1024
        with self.path.open("rb") as handle:
            handle.seek(0, 2)
            position = handle.tell()
            buffered = b""
            recent_lines: list[bytes] = []
            while position > 0:
                read_size = min(chunk_size, position)
                position -= read_size
                handle.seek(position)
                buffered = handle.read(read_size) + buffered
                recent_lines = [line for line in buffered.splitlines() if line.strip()]
                if len(recent_lines) >= limit:
                    break

        entries: list[EventLogEntry] = []
        for line in recent_lines[-limit:]:
            try:
                payload = json.loads(line.decode("utf-8"))
                entries.append(EventLogEntry(**payload))
            except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError(f"invalid recent event log entry in {self.path}") from exc
        return tuple(entries)

    def replay(self) -> dict[str, Any]:
        entries = self.read_entries()
        by_type = Counter(entry.event_type for entry in entries)
        by_component = Counter(entry.component for entry in entries)
        last_by_component: dict[str, dict[str, Any]] = {}
        for entry in entries:
            last_by_component[entry.component] = entry.to_dict()

        return {
            "schema_version": EVENT_LOG_SCHEMA_VERSION,
            "path": str(self.path),
            "total_events": len(entries),
            "by_type": dict(sorted(by_type.items())),
            "by_component": dict(sorted(by_component.items())),
            "last_created_at": entries[-1].created_at if entries else None,
            "last_by_component": last_by_component,
        }

    def health(self) -> dict[str, Any]:
        try:
            total_events = 0
            if self.path.exists():
                with self.path.open("r", encoding="utf-8") as handle:
                    for line_number, line in enumerate(handle, start=1):
                        stripped = line.strip()
                        if not stripped:
                            continue
                        try:
                            payload = json.loads(stripped)
                            EventLogEntry(**payload)
                        except (TypeError, json.JSONDecodeError) as exc:
                            raise ValueError(
                                f"invalid event log line {line_number} in {self.path}"
                            ) from exc
                        total_events += 1
        except Exception as exc:  # noqa: BLE001 - health should report the failure
            return {
                "status": "degraded",
                "backend": "local_jsonl",
                "path": str(self.path),
                "last_write_at": self._last_write_at,
                "error": str(exc),
            }

        return {
            "status": "ok",
            "backend": "local_jsonl",
            "path": str(self.path),
            "schema_version": EVENT_LOG_SCHEMA_VERSION,
            "last_write_at": self._last_write_at,
            "events_on_disk": total_events,
            "events_in_memory": len(self._entries),
        }

    @property
    def entries(self) -> tuple[EventLogEntry, ...]:
        return tuple(self._entries)
