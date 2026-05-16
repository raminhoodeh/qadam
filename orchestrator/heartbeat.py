"""Source heartbeat model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from world_monitor.source_registry import SOURCE_SPECS


@dataclass(frozen=True)
class Heartbeat:
    source: str
    status: str
    checked_at: str
    message: str = ""


def registry_heartbeats() -> tuple[Heartbeat, ...]:
    checked_at = datetime.now(timezone.utc).isoformat()
    return tuple(
        Heartbeat(
            source=source.key,
            status="registered",
            checked_at=checked_at,
            message=source.status,
        )
        for source in SOURCE_SPECS
    )
