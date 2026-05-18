"""Historical backfill planning for Phase 1.

This module defines the local contract before any large data pull is attempted.
Backfills remain read-only, local-first, and credential-aware.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.adapters import fetch_fred_sample, fetch_gdelt_sample, fetch_nasa_firms_sample, fetch_rss_sample
from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.ingestion import SourceObservation, build_test_observation
from orchestrator.phase1_live_adapters import PHASE1_LIVE_ADAPTERS, phase1_live_adapter_status
from orchestrator.phase1_live_adapters import fetch_phase1_live_adapter_sample
from world_monitor.source_registry import get_source

HISTORICAL_BACKFILL_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class HistoricalBackfillPlan:
    source_key: str
    window_days: int
    mode: str
    credential_required: bool
    credential_configured: bool
    storage_target: str
    boundary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HistoricalBackfillRun:
    schema_version: int
    source_key: str
    mode: str
    status: str
    window_days: int
    record_count: int
    event_count: int
    observed_at: str
    storage_target: str
    blocked_reason: str | None
    boundary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class HistoricalBackfillStore:
    def __init__(self, path: str | Path | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self.path = Path(path or Path(self.settings.runtime_dir) / "historical_backfill_runs.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, record: HistoricalBackfillRun) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.to_dict(), sort_keys=True) + "\n")

    def read(self) -> tuple[dict[str, Any], ...]:
        if not self.path.exists():
            return ()
        records: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    loaded = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid historical backfill line {line_number} in {self.path}") from exc
                if isinstance(loaded, dict):
                    records.append(loaded)
        return tuple(records)

    def health(self) -> dict[str, Any]:
        try:
            records = self.read()
        except Exception as exc:  # noqa: BLE001 - health should report the failure
            return {"status": "degraded", "path": str(self.path), "error": str(exc)}
        return {
            "status": "ok",
            "path": str(self.path),
            "schema_version": HISTORICAL_BACKFILL_SCHEMA_VERSION,
            "record_count": len(records),
        }


DEFAULT_BACKFILL_WINDOWS: dict[str, int] = {
    "acled": 365,
    "gdelt": 365,
    "nasa_firms": 180,
    "fred": 3650,
    "rss": 90,
    "polymarket": 365,
    "kalshi": 365,
    "alpaca": 365,
    "bls": 3650,
    "ecb": 3650,
    "un_comtrade": 3650,
    "sec_edgar": 3650,
}

DEDICATED_SAMPLE_FETCHERS = {
    "gdelt": fetch_gdelt_sample,
    "nasa_firms": fetch_nasa_firms_sample,
    "fred": fetch_fred_sample,
    "rss": fetch_rss_sample,
}


def build_historical_backfill_plan(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    plans: list[HistoricalBackfillPlan] = []
    for source_key, window_days in DEFAULT_BACKFILL_WINDOWS.items():
        if source_key in PHASE1_LIVE_ADAPTERS:
            status = phase1_live_adapter_status(source_key, settings)
            credential_required = status["required_group_count"] > 0
            credential_configured = bool(status["credential_configured"])
        else:
            credential_required = False
            credential_configured = True
        mode = "ready_read_only" if not credential_required or credential_configured else "blocked_missing_credentials"
        plans.append(
            HistoricalBackfillPlan(
                source_key=source_key,
                window_days=window_days,
                mode=mode,
                credential_required=credential_required,
                credential_configured=credential_configured,
                storage_target="local_raw_archive_then_source_observation",
                boundary="Backfill can write local observations only. It cannot create signals or orders.",
            )
        )
    return {
        "status": "ok",
        "plan_count": len(plans),
        "ready_count": sum(1 for plan in plans if plan.mode == "ready_read_only"),
        "blocked_count": sum(1 for plan in plans if plan.mode == "blocked_missing_credentials"),
        "plans": [plan.to_dict() for plan in plans],
        "boundary": "Historical backfills are local read-only data preparation jobs.",
    }


def _sample_event_count(source_key: str) -> int:
    if source_key in PHASE1_LIVE_ADAPTERS:
        payload = fetch_phase1_live_adapter_sample(source_key)
    elif source_key in DEDICATED_SAMPLE_FETCHERS:
        payload = DEDICATED_SAMPLE_FETCHERS[source_key]()
    else:
        payload = {"events": []}
    events = payload.get("events", []) if isinstance(payload, dict) else []
    return len(events) if isinstance(events, list) else 0


def _backfill_observation(source_key: str, plan: HistoricalBackfillPlan, event_count: int) -> SourceObservation:
    base = build_test_observation(get_source(source_key))
    return SourceObservation(
        schema_version=base.schema_version,
        source_key=base.source_key,
        source_name=base.source_name,
        pipeline=base.pipeline,
        tier=base.tier,
        mode="historical_backfill_sample",
        adapter_status=plan.mode,
        observed_at=datetime.now(timezone.utc).isoformat(),
        latency_ms=base.latency_ms,
        trust_score=base.trust_score,
        payload={
            **base.payload,
            "backfill_window_days": plan.window_days,
            "sample_event_count": event_count,
            "storage_target": plan.storage_target,
            "historical_backfill_live_pull": False,
        },
    )


def run_historical_backfill(
    *,
    source_keys: tuple[str, ...] = (),
    settings: Settings | None = None,
    store: HistoricalBackfillStore | None = None,
    event_log: EventLog | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    store = store or HistoricalBackfillStore(settings=settings)
    event_log = event_log or EventLog(echo=False)
    plan_payload = build_historical_backfill_plan(settings)
    requested = set(source_keys)
    plans = [
        HistoricalBackfillPlan(**plan)
        for plan in plan_payload["plans"]
        if not requested or plan["source_key"] in requested
    ]
    runs: list[HistoricalBackfillRun] = []
    observations: list[SourceObservation] = []

    for plan in plans:
        blocked = plan.mode == "blocked_missing_credentials"
        event_count = 0 if blocked else _sample_event_count(plan.source_key)
        record = HistoricalBackfillRun(
            schema_version=HISTORICAL_BACKFILL_SCHEMA_VERSION,
            source_key=plan.source_key,
            mode="sample_contract",
            status="blocked" if blocked else "recorded",
            window_days=plan.window_days,
            record_count=0 if blocked else 1,
            event_count=event_count,
            observed_at=datetime.now(timezone.utc).isoformat(),
            storage_target=plan.storage_target,
            blocked_reason="missing_credentials" if blocked else None,
            boundary="Backfill sample records are local read-only. True historical pulls require live credentials and provider-specific windows.",
        )
        store.write(record)
        runs.append(record)
        if not blocked:
            observations.append(_backfill_observation(plan.source_key, plan, event_count))
        event_log.write(
            "historical_backfill_sample_recorded",
            "historical_backfill",
            {
                "source_key": plan.source_key,
                "status": record.status,
                "mode": record.mode,
                "window_days": plan.window_days,
                "event_count": event_count,
                "execution_allowed": False,
            },
        )

    return {
        "status": "ok",
        "schema_version": HISTORICAL_BACKFILL_SCHEMA_VERSION,
        "requested_count": len(plans),
        "recorded_count": sum(1 for run in runs if run.status == "recorded"),
        "blocked_count": sum(1 for run in runs if run.status == "blocked"),
        "sample_event_count": sum(run.event_count for run in runs),
        "observations": [observation.to_dict() for observation in observations],
        "runs": [run.to_dict() for run in runs],
        "store": store.health(),
        "event_log": event_log.health(),
        "boundary": "Historical backfill runner currently writes local sample backfill records only. Live historical pulls remain credential-gated.",
    }
