#!/usr/bin/env python3
"""Refresh only due read-only source adapters and preserve observation provenance."""

from __future__ import annotations

import argparse
from dataclasses import fields
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase1_live_adapters import PHASE1_LIVE_ADAPTERS  # noqa: E402
from orchestrator.qadam_operator_ready_common import (  # noqa: E402
    authority_flags,
    now_iso,
    read_json,
    write_json_atomic,
)
from orchestrator.research_goal import ResearchGoalStore  # noqa: E402
from scripts.check_phase1_live_source_hardening import (  # noqa: E402
    LiveSourceValidation,
    PROMOTED_SOURCE_KEYS,
    _contains_secret_like_value,
    build_report_from_validations,
    validate_source,
    write_report,
)
from world_monitor.source_registry import SOURCE_SPECS  # noqa: E402

SCHEMA_VERSION = "qadam_live_source_scheduler.v1"
STATE_ARTIFACT = "qadam_live_source_scheduler.json"
RECEIPT_ARTIFACT = "qadam_live_source_refresh_receipt.json"
RESEARCH_GOAL_INGESTION_ARTIFACT = "qadam_source_research_goal_ingestion.json"
RESEARCH_GOAL_EVENT_MAX_AGE = timedelta(hours=72)
MAX_RESEARCH_GOAL_EVENTS_PER_SOURCE = 2
MAX_SEEN_EVENT_REFS = 5_000
MAX_PENDING_RESEARCH_EVENTS = 256
MAX_RESEARCH_GOAL_SOURCES_PER_CYCLE = 10
RESEARCH_GOAL_EVENT_COUNTER_KEYS = (
    "inspected",
    "duplicate",
    "stale",
    "future",
    "missing_timestamp_or_summary",
    "sample",
    "non_event_status",
    "non_event_fetch_snapshot",
    "secret_like_content",
)


def _empty_research_goal_event_counts() -> dict[str, int]:
    return {key: 0 for key in RESEARCH_GOAL_EVENT_COUNTER_KEYS}


def _parse(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _cadence_seconds(value: str) -> int:
    text = value.lower()
    if "weekly" in text:
        return 7 * 86400
    if "daily" in text:
        return 86400
    if "6 hours" in text:
        return 6 * 3600
    if "3 hours" in text:
        return 3 * 3600
    if "hourly" in text:
        return 3600
    if "30 minutes" in text or "20-30" in text:
        return 1800
    if "15 minutes" in text:
        return 900
    if "10 minutes" in text:
        return 600
    if "5 minutes" in text or "1-5 minutes" in text:
        return 300
    if "real-time" in text or "5 seconds" in text or "derived" in text:
        return 300
    return 3600


def _validation_from_dict(payload: dict[str, Any]) -> LiveSourceValidation | None:
    required = {field.name for field in fields(LiveSourceValidation)}
    if not required.issubset(payload):
        return None
    return LiveSourceValidation(**{key: payload[key] for key in required})


def _event_timestamp(event: dict[str, Any]) -> tuple[str | None, datetime | None]:
    for key in ("event_timestamp", "observed_at", "ingested_at"):
        value = event.get(key)
        parsed = _parse(value)
        if parsed is not None:
            return str(value), parsed
    return None, None


def _event_summary(event: dict[str, Any]) -> str:
    summary = str(event.get("normalised_summary") or "").strip()
    raw = event.get("raw_payload")
    raw = raw if isinstance(raw, dict) else {}
    if not summary:
        for key in ("title", "summary", "question", "name", "ticker"):
            value = raw.get(key)
            if value:
                summary = str(value).strip()
                break
    return " ".join(summary.split())[:500]


def _stable_event_ref(source_key: str, event: dict[str, Any]) -> str:
    observed_at, observed = _event_timestamp(event)
    raw = event.get("raw_payload")
    raw = raw if isinstance(raw, dict) else {}
    provider_record_id = raw.get("record_id") or raw.get("id")
    material = {
        "source_key": source_key,
        "summary": _event_summary(event),
        "provider_record_id": provider_record_id,
    }
    if not provider_record_id:
        # Some providers expose no stable record ID and stamp fetch time as the
        # event time. Admit identical content at most once per UTC day.
        material["observed_day"] = (
            observed.date().isoformat() if observed is not None else observed_at
        )
    digest = hashlib.sha256(
        json.dumps(material, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:24]
    return f"{source_key}:event:{digest}"


def _new_research_goal_events(
    source_key: str,
    result: dict[str, Any],
    *,
    seen_event_refs: set[str],
    now: datetime,
) -> tuple[list[dict[str, str]], dict[str, int]]:
    events = result.get("events")
    rows = events if isinstance(events, list) else []
    candidates: list[tuple[datetime, dict[str, str]]] = []
    counts = _empty_research_goal_event_counts()
    batch_refs = set(seen_event_refs)
    for event in rows:
        if not isinstance(event, dict):
            continue
        counts["inspected"] += 1
        raw = event.get("raw_payload")
        raw = raw if isinstance(raw, dict) else {}
        if raw.get("sample") is True or result.get("sample") is True:
            counts["sample"] += 1
            continue
        if (
            raw.get("status_only") is True
            or raw.get("event_evidence_eligible") is False
            or (
                raw.get("derived") is True
                and str(raw.get("record_id") or "").endswith("-status")
            )
        ):
            counts["non_event_status"] += 1
            continue
        if (
            raw.get("event_timestamp_fallback_to_fetch_time") is True
            or raw.get("summary_fallback_to_source_description") is True
        ):
            counts["non_event_fetch_snapshot"] += 1
            continue
        observed_at, observed = _event_timestamp(event)
        summary = _event_summary(event)
        if observed is None or not observed_at or not summary:
            counts["missing_timestamp_or_summary"] += 1
            continue
        if _contains_secret_like_value(summary):
            counts["secret_like_content"] += 1
            continue
        age = now - observed
        if age < timedelta(minutes=-5):
            counts["future"] += 1
            continue
        if age > RESEARCH_GOAL_EVENT_MAX_AGE:
            counts["stale"] += 1
            continue
        event_ref = _stable_event_ref(source_key, event)
        if event_ref in batch_refs:
            counts["duplicate"] += 1
            continue
        batch_refs.add(event_ref)
        candidates.append(
            (
                observed,
                {
                    "event_ref": event_ref,
                    "observed_at": observed.isoformat(),
                    "summary": summary,
                },
            )
        )
    candidates.sort(key=lambda item: item[0], reverse=True)
    return [row for _observed, row in candidates], counts


def _ingest_research_goals(
    *,
    settings: Settings,
    runtime: Path,
    selected: list[str],
    validations: dict[str, LiveSourceValidation],
    captured_results: dict[str, dict[str, Any]],
    now: datetime,
) -> dict[str, Any]:
    runtime.mkdir(parents=True, exist_ok=True)
    with (runtime / ".source-research-ingestion.lock").open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            return _ingest_research_goals_locked(
                settings=settings, runtime=runtime, selected=selected,
                validations=validations, captured_results=captured_results, now=now,
            )
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _scheduled_goal_events(pending, source_keys):
    budget = MAX_RESEARCH_GOAL_EVENTS_PER_SOURCE * MAX_RESEARCH_GOAL_SOURCES_PER_CYCLE
    queues = {
        key: [event for event in pending.values() if event["source_key"] == key]
        for key in source_keys[:MAX_RESEARCH_GOAL_SOURCES_PER_CYCLE]
    }
    scheduled = []
    # Give each selected source its fair share first, then reuse idle shares.
    # This preserves the total cycle budget even when only one source is busy.
    while len(scheduled) < budget:
        before = len(scheduled)
        for key, events in queues.items():
            take = min(MAX_RESEARCH_GOAL_EVENTS_PER_SOURCE, budget - len(scheduled))
            scheduled.extend((key, event) for event in events[:take])
            del events[:take]
        if len(scheduled) == before:
            break
    return scheduled


def _ingest_research_goals_locked(
    *, settings: Settings, runtime: Path, selected: list[str],
    validations: dict[str, LiveSourceValidation],
    captured_results: dict[str, dict[str, Any]], now: datetime,
) -> dict[str, Any]:
    previous = read_json(runtime / RESEARCH_GOAL_INGESTION_ARTIFACT)
    seen_rows = previous.get("seen_event_refs")
    prior_seen = [
        str(value)
        for value in (seen_rows if isinstance(seen_rows, list) else [])
        if value
    ]
    seen = set(prior_seen)
    appended_seen = list(dict.fromkeys(prior_seen))
    store = ResearchGoalStore(settings=settings)
    # Goal IDs are stable. A completed goal is the acknowledgement if a crash
    # occurred after its durable append but before the cursor was published.
    existing_refs = {
        str(ref) for row in store.latest_by_goal_id().values()
        if row.get("origin") == "live_source"
        for ref in row.get("source_event_refs", [])
    }
    seen.update(existing_refs)
    closed_non_event_goal_count = _close_non_event_research_goals(
        store=store,
        now=now,
    )
    created: list[dict[str, str]] = []
    counters = {
        **_empty_research_goal_event_counts(),
        "provider_ineligible": 0,
        "not_promoted_capacity": 0,
        "pending_expired": 0,
        "pending_invalid": 0,
        "queue_overflow_not_acknowledged": 0,
    }
    pending: dict[str, dict[str, str]] = {}
    for event in previous.get("pending_events", []):
        required = ("event_ref", "source_key", "observed_at", "available_at", "summary")
        if (not isinstance(event, dict)
                or any(not isinstance(event.get(key), str) or not event[key] for key in required)
                or _contains_secret_like_value(event)):
            counters["pending_invalid"] += 1
            continue
        observed = _parse(event.get("observed_at"))
        available = _parse(event.get("available_at"))
        if not observed or not available or available > now or observed > now + timedelta(minutes=5):
            counters["pending_invalid"] += 1
        elif now - observed > RESEARCH_GOAL_EVENT_MAX_AGE:
            counters["pending_expired"] += 1
        elif event["event_ref"] not in seen:
            pending[event["event_ref"]] = {key: event[key] for key in required}
    for source_key in selected:
        validation = validations.get(source_key)
        result = captured_results.get(source_key)
        if (
            validation is None
            or validation.freshness_evidence_eligible is not True
            or not isinstance(result, dict)
        ):
            counters["provider_ineligible"] += 1
            continue
        events, source_counts = _new_research_goal_events(
            source_key,
            result,
            seen_event_refs=seen | set(pending),
            now=now,
        )
        for key, value in source_counts.items():
            counters[key] += value
        for event in events:
            if len(pending) >= MAX_PENDING_RESEARCH_EVENTS:
                counters["queue_overflow_not_acknowledged"] += 1
                continue
            pending[event["event_ref"]] = {
                **event, "source_key": source_key, "available_at": now.isoformat(),
            }
    # Persist accepted work before invoking its idempotent consumer. Capacity
    # overflow is explicit and is never added to the completed cursor.
    replay_required = bool(previous.get("provider_replay_required") or
                           previous.get("queue_overflow_not_acknowledged") or
                           counters["queue_overflow_not_acknowledged"])
    write_json_atomic(runtime / RESEARCH_GOAL_INGESTION_ARTIFACT, {
        "generated_at": now.isoformat(), "status": "processing",
        "last_served_source": previous.get("last_served_source"),
        "pending_events": list(pending.values()), "seen_event_refs": prior_seen,
        "queue_overflow_not_acknowledged": counters["queue_overflow_not_acknowledged"],
        "provider_replay_required": replay_required,
        "paper_order_created_count": 0, "broker_write_count": 0,
        "live_capital_enabled": False, "authority": authority_flags(),
    })
    source_keys = list(dict.fromkeys(event["source_key"] for event in pending.values()))
    last_served = previous.get("last_served_source")
    if last_served in source_keys:
        pivot = source_keys.index(last_served) + 1
        source_keys = source_keys[pivot:] + source_keys[:pivot]
    for source_key, event in _scheduled_goal_events(pending, source_keys):
        goal = store.add_from_observation(
            summary=event["summary"],
            source_event_refs=(event["event_ref"],),
            origin="live_source",
            observed_at=event["observed_at"],
            event_log=EventLog(echo=False),
        )
        created.append(
            {
                "goal_id": goal.goal_id,
                "source_key": source_key,
                "source_event_ref": event["event_ref"],
                "observed_at": event["observed_at"],
                "market_channel": goal.market_channel,
            }
        )
        seen.add(event["event_ref"])
        appended_seen.append(event["event_ref"])
        del pending[event["event_ref"]]
        last_served = source_key
    counters["not_promoted_capacity"] = len(pending)
    deduped_seen = list(dict.fromkeys(appended_seen))[-MAX_SEEN_EVENT_REFS:]
    artifact = {
        "schema_version": "qadam_source_research_goal_ingestion.v1",
        "artifact_type": "qadam_source_research_goal_ingestion",
        "generated_at": now.isoformat(),
        "status": "ok",
        "selected_source_count": len(selected),
        "created_goal_count": len(created),
        "created_goals": created,
        "event_counts": counters,
        "closed_non_event_goal_count": closed_non_event_goal_count,
        "seen_event_refs": deduped_seen,
        "pending_events": list(pending.values()),
        "pending_event_count": len(pending),
        "pending_capacity": MAX_PENDING_RESEARCH_EVENTS,
        "maximum_goals_per_cycle": MAX_RESEARCH_GOAL_EVENTS_PER_SOURCE * MAX_RESEARCH_GOAL_SOURCES_PER_CYCLE,
        "last_served_source": last_served,
        "provider_replay_required": replay_required,
        "material_change_detected": bool(created or closed_non_event_goal_count),
        "completeness_state": (
            "backpressure_provider_replay_required"
            if replay_required else "bounded_pending" if pending else "caught_up"
        ),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
        "boundary": (
            "Fresh provider events may create pre-signal research goals only. "
            "They cannot satisfy a strategy, risk, Router, order, or proof gate alone."
        ),
    }
    if _contains_secret_like_value(artifact):
        raise ValueError("source research-goal ingestion contains a secret-like value")
    write_json_atomic(runtime / RESEARCH_GOAL_INGESTION_ARTIFACT, artifact)
    return artifact


def _close_non_event_research_goals(
    *,
    store: ResearchGoalStore,
    now: datetime,
) -> int:
    """Close old fetch-status goals without rewriting their audit history."""

    summaries = {
        source_key: config.sample_summary.strip().lower()
        for source_key, config in PHASE1_LIVE_ADAPTERS.items()
        if config.sample_summary.strip()
    }
    closed_count = 0
    for row in store.latest_by_goal_id().values():
        if row.get("origin") != "live_source":
            continue
        refs = row.get("source_event_refs")
        refs = refs if isinstance(refs, list) else []
        source_key = str(refs[0]).split(":", 1)[0] if refs else ""
        summary = summaries.get(source_key)
        if not summary or summary not in str(row.get("hypothesis") or "").lower():
            continue
        if (
            row.get("status") == "closed_no_trade"
            and row.get("close_reason") == "non_event_provider_snapshot_or_status"
        ):
            continue
        store.add_record(
            {
                **row,
                "status": "closed_no_trade",
                "close_reason": "non_event_provider_snapshot_or_status",
                "updated_at": now.isoformat(),
            },
            event_log=EventLog(echo=False),
        )
        closed_count += 1
    return closed_count


def run_refresh(*, max_sources: int = 10, force_all: bool = False) -> dict[str, Any]:
    settings = Settings.from_env()
    runtime = Path(settings.runtime_dir)
    if not runtime.is_absolute():
        runtime = ROOT / runtime
    runtime.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    checked_at = now.isoformat()
    spec_by_key = {spec.key: spec for spec in SOURCE_SPECS}
    previous_report = read_json(runtime / "phase1_live_source_validation.json")
    previous = {
        row.get("source_key"): row
        for row in previous_report.get("validations", [])
        if isinstance(row, dict) and row.get("source_key")
    }
    due: list[tuple[float, str]] = []
    for source_key in PROMOTED_SOURCE_KEYS:
        prior = previous.get(source_key, {})
        last_checked = _parse(prior.get("checked_at"))
        cadence = _cadence_seconds(spec_by_key[source_key].cadence)
        overdue = float("inf") if last_checked is None else (now - last_checked).total_seconds() - cadence
        if force_all or last_checked is None or overdue >= 0:
            due.append((overdue, source_key))
    due.sort(key=lambda item: (-item[0], item[1]))
    selected = [source_key for _overdue, source_key in due[: max(1, max_sources)]]

    validations: dict[str, LiveSourceValidation] = {}
    captured_results: dict[str, dict[str, Any]] = {}
    for source_key, row in previous.items():
        restored = _validation_from_dict(row)
        if restored is not None:
            validations[source_key] = restored
    for source_key in selected:
        validations[source_key] = validate_source(
            source_key,
            settings=settings,
            live=True,
            checked_at=checked_at,
            result_sink=lambda key, result: captured_results.__setitem__(key, result),
        )

    research_goal_ingestion = _ingest_research_goals(
        settings=settings,
        runtime=runtime,
        selected=selected,
        validations=validations,
        captured_results=captured_results,
        now=datetime.now(timezone.utc),
    )

    ordered = tuple(
        validations[source_key]
        for source_key in PROMOTED_SOURCE_KEYS
        if source_key in validations
    )
    report = build_report_from_validations(ordered, checked_at=checked_at, live=True)
    report["scheduler"] = {
        "selected_source_count": len(selected),
        "selected_sources": selected,
        "due_source_count_before_run": len(due),
        "remaining_due_source_count": max(0, len(due) - len(selected)),
        "force_all": force_all,
    }
    if _contains_secret_like_value(report):
        raise ValueError("live source refresh report contains a secret-like value")
    write_report(settings, report)

    state = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_live_source_scheduler",
        "generated_at": now_iso(),
        "status": "active",
        "selected_source_count": len(selected),
        "selected_sources": selected,
        "due_source_count_before_run": len(due),
        "remaining_due_source_count": max(0, len(due) - len(selected)),
        "tracked_source_count": len(ordered),
        "provider_backed_freshness_evidence_count": report[
            "provider_backed_freshness_evidence_count"
        ],
        "sample_fixture_count": report["sample_fixture_count"],
        "research_goal_created_count": research_goal_ingestion["created_goal_count"],
        "research_goal_pending_count": research_goal_ingestion["pending_event_count"],
        "research_goal_completeness_state": research_goal_ingestion["completeness_state"],
        "research_goal_provider_replay_required": research_goal_ingestion["provider_replay_required"],
        "research_goal_event_duplicate_count": research_goal_ingestion["event_counts"][
            "duplicate"
        ],
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    write_json_atomic(runtime / STATE_ARTIFACT, state)
    receipt = {
        **state,
        "artifact_type": "qadam_live_source_refresh_receipt",
        "degraded_source_count": report["degraded_count"],
        "missing_credentials_count": report["missing_credentials_count"],
        "boundary": (
            "Read-only due-source refresh. Fresh provider events may create pre-signal "
            "research goals; health checks and fixtures never count as event evidence, "
            "source quorum, candidates, orders, or proof."
        ),
    }
    write_json_atomic(runtime / RECEIPT_ARTIFACT, receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-sources", type=int, default=10)
    parser.add_argument("--force-all", action="store_true")
    args = parser.parse_args()
    receipt = run_refresh(max_sources=args.max_sources, force_all=args.force_all)
    from orchestrator.runtime.command import report_work_result
    report_work_result({**receipt, "material_change_detected": bool(receipt["research_goal_created_count"])})
    print(f"live_source_refresh_status={receipt['status']}")
    print(f"live_source_refresh_selected={receipt['selected_source_count']}")
    print(f"live_source_refresh_remaining_due={receipt['remaining_due_source_count']}")
    print(
        "live_source_refresh_provider_backed_evidence="
        f"{receipt['provider_backed_freshness_evidence_count']}"
    )
    print(
        "live_source_refresh_research_goals_created="
        f"{receipt['research_goal_created_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
