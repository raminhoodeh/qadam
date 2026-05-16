"""Phase 1 test-data ingestion spine.

This module proves the source-adapter contract without calling live APIs. Real
adapters can later replace `build_test_observation` one source at a time.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT, SOURCE_SPECS, SourceSpec

INGESTION_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class SourceObservation:
    schema_version: int
    source_key: str
    source_name: str
    pipeline: str
    tier: int
    mode: str
    adapter_status: str
    observed_at: str
    latency_ms: int
    trust_score: float
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TestIngestionStore:
    def __init__(self, path: str | Path | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self.path = Path(path or Path(self.settings.runtime_dir) / "test_ingestion_snapshots.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, observation: SourceObservation) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(observation.to_dict(), sort_keys=True) + "\n")

    def read(self) -> tuple[SourceObservation, ...]:
        if not self.path.exists():
            return ()
        observations: list[SourceObservation] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    observations.append(SourceObservation(**json.loads(stripped)))
                except (TypeError, json.JSONDecodeError) as exc:
                    raise ValueError(f"invalid ingestion line {line_number} in {self.path}") from exc
        return tuple(observations)

    def health(self) -> dict[str, Any]:
        try:
            observations = self.read()
        except Exception as exc:  # noqa: BLE001 - health should report the failure
            return {"status": "degraded", "path": str(self.path), "error": str(exc)}
        return {
            "status": "ok",
            "path": str(self.path),
            "schema_version": INGESTION_SCHEMA_VERSION,
            "observation_count": len(observations),
            "mode": "test_data",
        }


def _deterministic_score(key: str) -> float:
    return round((sum(ord(character) for character in key) % 100) / 100, 2)


def _adapter_status(source: SourceSpec) -> str:
    if source.status in {"needs_clarity", "needs_choice"}:
        return "deferred_pending_resolution"
    if source.status == "derived":
        return "derived_test_ready"
    return "test_ready"


def build_test_observation(source: SourceSpec) -> SourceObservation:
    score = _deterministic_score(source.key)
    return SourceObservation(
        schema_version=INGESTION_SCHEMA_VERSION,
        source_key=source.key,
        source_name=source.name,
        pipeline=source.pipeline,
        tier=source.tier,
        mode="test_data",
        adapter_status=_adapter_status(source),
        observed_at=datetime.now(timezone.utc).isoformat(),
        latency_ms=25 + int(score * 100),
        trust_score=score,
        payload={
            "test_signal_strength": score,
            "cadence": source.cadence,
            "auth_mode": source.auth,
            "tool_name": source.tool_name,
            "endpoint_count": len(source.endpoints),
            "unresolved_note": source.notes if source.status in {"needs_clarity", "needs_choice"} else "",
        },
    )


def selected_sources(
    *,
    limit: int | None = None,
    tier: int | None = None,
    pipeline: str | None = None,
) -> tuple[SourceSpec, ...]:
    sources = SOURCE_SPECS
    if tier is not None:
        sources = tuple(source for source in sources if source.tier == tier)
    if pipeline is not None:
        sources = tuple(source for source in sources if source.pipeline == pipeline)
    if limit is not None:
        sources = sources[:limit]
    return sources


def run_test_ingestion(
    *,
    limit: int | None = None,
    tier: int | None = None,
    pipeline: str | None = None,
    store: TestIngestionStore | None = None,
    event_log: EventLog | None = None,
) -> dict[str, Any]:
    store = store or TestIngestionStore()
    event_log = event_log or EventLog(echo=False)
    observations = [build_test_observation(source) for source in selected_sources(limit=limit, tier=tier, pipeline=pipeline)]

    for observation in observations:
        store.write(observation)
        event_log.write(
            "source_test_observation_recorded",
            "ingestion",
            {
                "source_key": observation.source_key,
                "pipeline": observation.pipeline,
                "tier": observation.tier,
                "mode": observation.mode,
                "adapter_status": observation.adapter_status,
            },
        )

    deferred = [observation.source_key for observation in observations if observation.adapter_status == "deferred_pending_resolution"]
    return {
        "status": "ok",
        "mode": "test_data",
        "schema_version": INGESTION_SCHEMA_VERSION,
        "selected_count": len(observations),
        "expected_source_count": EXPECTED_SOURCE_COUNT,
        "deferred_count": len(deferred),
        "deferred_sources": deferred,
        "store": store.health(),
        "event_log": event_log.health(),
    }


def ingestion_spine_summary(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    store = TestIngestionStore(settings=settings)
    return {
        "status": "test_data_ready",
        "mode": "test_data",
        "source_count": len(SOURCE_SPECS),
        "expected_source_count": EXPECTED_SOURCE_COUNT,
        "store": store.health(),
        "boundary": "No live API calls; observations are deterministic test data until individual adapters are promoted.",
    }
