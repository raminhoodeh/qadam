"""Source heartbeat model."""

from __future__ import annotations

from dataclasses import dataclass

from orchestrator.source_health import build_data_environment_map


@dataclass(frozen=True)
class Heartbeat:
    source: str
    status: str
    checked_at: str
    message: str = ""


def registry_heartbeats() -> tuple[Heartbeat, ...]:
    data_map = build_data_environment_map()
    checked_at = str(data_map["generated_at"])
    return tuple(
        Heartbeat(
            source=source["source_key"],
            status=source["runtime_status"],
            checked_at=checked_at,
            message=source["registry_status"],
        )
        for source in data_map["sources"]
    )
