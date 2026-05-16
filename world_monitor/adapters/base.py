"""Base types for Qadam source adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from world_monitor.source_registry import SourceSpec


@dataclass
class NormalizedEvent:
    source: str
    source_type: str
    event_type: str
    observed_at: datetime
    normalised_summary: str
    raw_payload: dict[str, Any]
    coordinates: tuple[float, float] | None = None
    trust_score_at_collection: float | None = None
    ingested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PollResult:
    source: str
    events: tuple[NormalizedEvent, ...]
    degraded: bool = False
    message: str = ""


class SourceAdapter(ABC):
    def __init__(self, spec: SourceSpec) -> None:
        self.spec = spec

    @abstractmethod
    async def poll(self) -> PollResult:
        """Fetch source data and return normalized event candidates."""
