"""Daily learning automation artifact for Qadam.

Stage 6 records the once-daily edge-learning pass. It coordinates the daily
edge findings and Stage 6A Telegram learning brief, but it does not create
trades, mutate strategy, call brokers, or enable live capital.
"""

from __future__ import annotations

from datetime import datetime, time, timezone
import json
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from orchestrator.config import Settings
from orchestrator.daily_edge_findings import validate_daily_edge_findings_brief
from orchestrator.daily_telegram_learning_brief import (
    validate_daily_telegram_learning_brief,
)
from orchestrator.event_log import EventLog
from orchestrator.telegram_human_brief import TELEGRAM_HUMAN_BRIEF_FALSE_FIELDS


DAILY_LEARNING_AUTOMATION_SCHEMA_VERSION = 1
DAILY_LEARNING_AUTOMATION_RUNTIME_ARTIFACT = "daily_learning_automation.json"
DAILY_LEARNING_AUTOMATION_HISTORY = "daily_learning_automation_history.jsonl"
DAILY_LEARNING_AUTOMATION_EVENT_LOG = "daily_learning_automation_events.jsonl"
DAILY_LEARNING_AUTOMATION_EVENT_TYPE = "daily_learning_automation_recorded"
DAILY_LEARNING_AUTOMATION_COMPONENT = "daily_learning_automation"

DAILY_LEARNING_AUTOMATION_STATUSES = {
    "daily_learning_automation_disabled",
    "daily_learning_automation_not_due",
    "daily_learning_automation_blocked",
    "daily_learning_automation_dry_run_ready",
    "daily_learning_automation_ready_to_send",
    "daily_learning_automation_sent",
    "daily_learning_automation_failed",
    "daily_learning_automation_already_sent",
}

DAILY_LEARNING_AUTOMATION_BOUNDARY = (
    "Daily Learning Automation records the daily source/price learning pass "
    "and the Stage 6A Telegram learning brief. It can decide whether a daily "
    "learning notification is due, but it cannot create trade candidates, "
    "approve risk, approve execution, submit or close broker orders, handle "
    "Telegram commands, call quantum providers, mutate strategy, expose "
    "secrets or chat ids, grant proof credit, deploy code, or enable live "
    "capital."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_timestamp(value: Any) -> datetime:
    text = str(value or "").strip().replace("Z", "+00:00")
    if text:
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            parsed = datetime.now(timezone.utc)
    else:
        parsed = datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _configured_timezone(settings: Settings) -> ZoneInfo:
    try:
        return ZoneInfo(settings.daily_learning_automation_timezone)
    except Exception:  # noqa: BLE001 - fail closed to UTC for invalid config.
        return ZoneInfo("UTC")


def _parse_local_cutoff(settings: Settings) -> time:
    text = settings.daily_learning_automation_after_local_time.strip()
    try:
        hour_text, minute_text, *_ = text.split(":")
        return time(hour=max(0, min(23, int(hour_text))), minute=max(0, min(59, int(minute_text))))
    except (TypeError, ValueError):
        return time(hour=20, minute=0)


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def daily_learning_automation_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / DAILY_LEARNING_AUTOMATION_RUNTIME_ARTIFACT,
        runtime / DAILY_LEARNING_AUTOMATION_HISTORY,
        runtime / DAILY_LEARNING_AUTOMATION_EVENT_LOG,
    )


def daily_learning_local_context(
    *,
    settings: Settings | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = generated_at or _now()
    generated = _parse_timestamp(generated_at)
    tz = _configured_timezone(settings)
    local_now = generated.astimezone(tz)
    cutoff = _parse_local_cutoff(settings)
    return {
        "timezone": getattr(tz, "key", settings.daily_learning_automation_timezone),
        "local_date": local_now.date().isoformat(),
        "local_time": local_now.strftime("%H:%M"),
        "delivery_after_local_time": cutoff.strftime("%H:%M"),
        "due_for_delivery": local_now.time() >= cutoff,
    }


def build_daily_learning_automation(
    *,
    daily_edge_findings: dict[str, Any],
    daily_telegram_learning_brief: dict[str, Any],
    settings: Settings | None = None,
    send_requested: bool = False,
    force_delivery_window: bool = False,
    generated_at: str | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = generated_at or _now()
    validate_daily_edge_findings_brief(daily_edge_findings)
    validate_daily_telegram_learning_brief(daily_telegram_learning_brief)
    local_context = daily_learning_local_context(settings=settings, generated_at=generated_at)
    due = local_context["due_for_delivery"] or force_delivery_window
    enabled = settings.daily_learning_automation_enabled
    dry_run = settings.daily_learning_automation_dry_run
    learning_status = str(daily_telegram_learning_brief.get("status") or "")
    learning_ready = learning_status in {
        "daily_telegram_learning_brief_dry_run_ready",
        "daily_telegram_learning_brief_ready_to_send",
        "daily_telegram_learning_brief_sent",
        "daily_telegram_learning_brief_already_sent",
    }
    automation_live_send_allowed = (
        enabled
        and not dry_run
        and due
        and daily_telegram_learning_brief.get("telegram_live_send_allowed") is True
    )

    blockers: list[str] = []
    if not enabled:
        blockers.append("daily_learning_automation_disabled")
    if not due:
        blockers.append("daily_learning_automation_not_due")
    if dry_run:
        blockers.append("daily_learning_automation_dry_run")
    if daily_edge_findings.get("status") != "daily_edge_findings_ready_for_review":
        blockers.append("daily_edge_findings_not_ready")
    if daily_edge_findings.get("quantum_mandatory_review_gate_passed") is not True:
        blockers.append("quantum_gate_not_passed")
    if not learning_ready:
        blockers.append("daily_telegram_learning_brief_not_ready")
    if (
        send_requested
        and due
        and not dry_run
        and learning_status != "daily_telegram_learning_brief_sent"
        and daily_telegram_learning_brief.get("telegram_live_send_allowed") is not True
    ):
        blockers.append("telegram_learning_brief_live_send_not_allowed")

    status = "daily_learning_automation_blocked"
    if not enabled:
        status = "daily_learning_automation_disabled"
    elif not due:
        status = "daily_learning_automation_not_due"
    elif learning_status == "daily_telegram_learning_brief_failed":
        status = "daily_learning_automation_failed"
    elif learning_status == "daily_telegram_learning_brief_sent":
        status = "daily_learning_automation_sent"
    elif learning_status == "daily_telegram_learning_brief_already_sent":
        status = "daily_learning_automation_already_sent"
    elif learning_ready and dry_run:
        status = "daily_learning_automation_dry_run_ready"
    elif learning_ready and automation_live_send_allowed:
        status = "daily_learning_automation_ready_to_send"
    elif learning_ready and not dry_run:
        status = "daily_learning_automation_ready_to_send"

    artifact = {
        "schema_version": DAILY_LEARNING_AUTOMATION_SCHEMA_VERSION,
        "artifact_type": "daily_learning_automation",
        "artifact_id": f"daily-learning-automation:{local_context['local_date']}",
        "stage": "Stage 6 - Daily Automation",
        "generated_at": generated_at,
        "status": status,
        "public_safe": True,
        "cadence": "daily",
        "enabled": enabled,
        "dry_run": dry_run,
        "send_requested": send_requested,
        "effective_send_requested": (
            send_requested
            and due
            and enabled
            and not dry_run
        ),
        "force_delivery_window": force_delivery_window,
        "timezone": local_context["timezone"],
        "local_date": local_context["local_date"],
        "local_time": local_context["local_time"],
        "delivery_after_local_time": local_context["delivery_after_local_time"],
        "due_for_delivery": local_context["due_for_delivery"],
        "due_or_forced": due,
        "automation_live_send_allowed": automation_live_send_allowed,
        "daily_edge_findings_status": daily_edge_findings.get("status"),
        "daily_telegram_learning_brief_status": learning_status,
        "daily_telegram_learning_brief_specificity_status": daily_telegram_learning_brief.get(
            "message_specificity_status"
        ),
        "daily_telegram_learning_brief_specificity_score": daily_telegram_learning_brief.get(
            "message_specificity_score"
        ),
        "daily_telegram_learning_brief_human_style_status": daily_telegram_learning_brief.get(
            "message_human_style_status"
        ),
        "daily_telegram_learning_brief_live_send_allowed": (
            daily_telegram_learning_brief.get("telegram_live_send_allowed") is True
        ),
        "live_send_attempted": daily_telegram_learning_brief.get("live_send_attempted") is True,
        "live_send_succeeded": daily_telegram_learning_brief.get("live_send_succeeded") is True,
        "already_sent": daily_telegram_learning_brief.get("already_sent") is True,
        "last_delivery_failure_category": daily_telegram_learning_brief.get(
            "last_delivery_failure_category"
        ),
        "source_count": _int(daily_edge_findings.get("source_count")),
        "watched_instrument_count": _int(daily_edge_findings.get("watched_instrument_count")),
        "candidate_pattern_count": _int(daily_edge_findings.get("candidate_pattern_count")),
        "validated_edge_count": _int(daily_edge_findings.get("validated_edge_count")),
        "quantum_required": True,
        "quantum_review_status": daily_edge_findings.get("quantum_review_status"),
        "quantum_backend": daily_edge_findings.get("quantum_backend"),
        "quantum_gate_status": daily_edge_findings.get("quantum_mandatory_review_gate_status"),
        "quantum_gate_passed": (
            daily_edge_findings.get("quantum_mandatory_review_gate_passed") is True
        ),
        "promotion_review_ready_count": _int(
            daily_telegram_learning_brief.get("promotion_review_ready_count")
        ),
        "promotion_gate_held_count": _int(
            daily_telegram_learning_brief.get("promotion_gate_held_count")
        ),
        "human_approval_missing_count": _int(
            daily_telegram_learning_brief.get("human_approval_missing_count")
        ),
        "strategy_learning_applied_count": 0,
        "blockers": sorted(set(blockers)),
        "blocker_count": len(set(blockers)),
        "documentation_routes": {
            "runtime_artifact": f"data/runtime/{DAILY_LEARNING_AUTOMATION_RUNTIME_ARTIFACT}",
            "history": f"data/runtime/{DAILY_LEARNING_AUTOMATION_HISTORY}",
            "event_log": f"data/runtime/{DAILY_LEARNING_AUTOMATION_EVENT_LOG}",
            "stage_6a_artifact": "data/runtime/daily_telegram_learning_brief.json",
            "source_daily_edge_findings": "data/runtime/daily_edge_findings_brief.json",
            "dashboard_surface": "Communications",
        },
        "boundary": DAILY_LEARNING_AUTOMATION_BOUNDARY,
    }
    for field in TELEGRAM_HUMAN_BRIEF_FALSE_FIELDS:
        artifact[field] = False
    return artifact


def validate_daily_learning_automation(payload: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "artifact_type",
        "artifact_id",
        "stage",
        "generated_at",
        "status",
        "public_safe",
        "cadence",
        "enabled",
        "dry_run",
        "send_requested",
        "effective_send_requested",
        "force_delivery_window",
        "timezone",
        "local_date",
        "local_time",
        "delivery_after_local_time",
        "due_for_delivery",
        "due_or_forced",
        "automation_live_send_allowed",
        "daily_edge_findings_status",
        "daily_telegram_learning_brief_status",
        "daily_telegram_learning_brief_specificity_status",
        "daily_telegram_learning_brief_specificity_score",
        "daily_telegram_learning_brief_human_style_status",
        "daily_telegram_learning_brief_live_send_allowed",
        "live_send_attempted",
        "live_send_succeeded",
        "already_sent",
        "last_delivery_failure_category",
        "source_count",
        "watched_instrument_count",
        "candidate_pattern_count",
        "validated_edge_count",
        "quantum_required",
        "quantum_review_status",
        "quantum_backend",
        "quantum_gate_status",
        "quantum_gate_passed",
        "promotion_review_ready_count",
        "promotion_gate_held_count",
        "human_approval_missing_count",
        "strategy_learning_applied_count",
        "blockers",
        "blocker_count",
        "documentation_routes",
        "boundary",
        *TELEGRAM_HUMAN_BRIEF_FALSE_FIELDS,
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"Daily learning automation missing fields: {missing}")
    if payload.get("schema_version") != DAILY_LEARNING_AUTOMATION_SCHEMA_VERSION:
        raise ValueError("Daily learning automation schema mismatch")
    if payload.get("artifact_type") != "daily_learning_automation":
        raise ValueError("Daily learning automation artifact type mismatch")
    if payload.get("status") not in DAILY_LEARNING_AUTOMATION_STATUSES:
        raise ValueError("Daily learning automation status invalid")
    if payload.get("public_safe") is not True:
        raise ValueError("Daily learning automation must be public-safe")
    if payload.get("cadence") != "daily":
        raise ValueError("Daily learning automation cadence mismatch")
    if "records the daily source/price learning pass" not in str(payload.get("boundary", "")):
        raise ValueError("Daily learning automation boundary weak")
    for field in TELEGRAM_HUMAN_BRIEF_FALSE_FIELDS:
        if payload.get(field) is not False:
            raise ValueError(f"Daily learning automation authority leak: {field}")
    if _int(payload.get("source_count")) < 30:
        raise ValueError("Daily learning automation source count below contract")
    if _int(payload.get("watched_instrument_count")) < 20:
        raise ValueError("Daily learning automation watched instrument count below contract")
    if _int(payload.get("candidate_pattern_count")) < 5:
        raise ValueError("Daily learning automation candidate pattern count below contract")
    if payload.get("quantum_required") is not True:
        raise ValueError("Daily learning automation must require quantum")
    if payload.get("quantum_gate_passed") is not True:
        raise ValueError("Daily learning automation quantum gate not passed")
    if payload.get("daily_edge_findings_status") != "daily_edge_findings_ready_for_review":
        raise ValueError("Daily learning automation daily findings not ready")
    if payload.get("daily_telegram_learning_brief_human_style_status") != "human":
        raise ValueError("Daily learning automation learning brief not human")
    if payload.get("daily_telegram_learning_brief_specificity_status") != "specific":
        raise ValueError("Daily learning automation learning brief not specific")
    if _int(payload.get("daily_telegram_learning_brief_specificity_score")) < 70:
        raise ValueError("Daily learning automation learning brief specificity too low")
    if _int(payload.get("promotion_review_ready_count")) != 5:
        raise ValueError("Daily learning automation review-ready count mismatch")
    if _int(payload.get("human_approval_missing_count")) < 1:
        raise ValueError("Daily learning automation must show human approval missing")
    if _int(payload.get("strategy_learning_applied_count")) != 0:
        raise ValueError("Daily learning automation cannot apply learning")
    if payload.get("automation_live_send_allowed") is True:
        if payload.get("enabled") is not True:
            raise ValueError("Daily learning automation live send allowed while disabled")
        if payload.get("dry_run") is not False:
            raise ValueError("Daily learning automation live send allowed in dry run")
        if payload.get("due_or_forced") is not True:
            raise ValueError("Daily learning automation live send allowed before due")
        if payload.get("daily_telegram_learning_brief_live_send_allowed") is not True:
            raise ValueError("Daily learning automation live send bypasses learning brief")
    if payload.get("live_send_succeeded") is True and payload.get("live_send_attempted") is not True:
        raise ValueError("Daily learning automation succeeded without attempted send")
    if payload.get("effective_send_requested") is True:
        if payload.get("send_requested") is not True:
            raise ValueError("Daily learning automation effective send without request")
        if payload.get("enabled") is not True or payload.get("dry_run") is not False:
            raise ValueError("Daily learning automation effective send while gated")


def write_daily_learning_automation(
    payload: dict[str, Any],
    settings: Settings | None = None,
) -> dict[str, Any]:
    validate_daily_learning_automation(payload)
    output_path, history_path, event_path = daily_learning_automation_paths(settings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    event = {
        "schema_version": DAILY_LEARNING_AUTOMATION_SCHEMA_VERSION,
        "event_type": DAILY_LEARNING_AUTOMATION_EVENT_TYPE,
        "component": DAILY_LEARNING_AUTOMATION_COMPONENT,
        "created_at": payload.get("generated_at") or _now(),
        "status": payload.get("status"),
        "local_date": payload.get("local_date"),
        "due_or_forced": payload.get("due_or_forced") is True,
        "daily_telegram_learning_brief_status": payload.get(
            "daily_telegram_learning_brief_status"
        ),
        "live_send_attempted": payload.get("live_send_attempted") is True,
        "live_send_succeeded": payload.get("live_send_succeeded") is True,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "strategy_learning_applied_count": 0,
        "live_capital_enabled": False,
        "boundary": DAILY_LEARNING_AUTOMATION_BOUNDARY,
    }
    with event_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    EventLog(echo=False).write(
        event_type=DAILY_LEARNING_AUTOMATION_EVENT_TYPE,
        component=DAILY_LEARNING_AUTOMATION_COMPONENT,
        payload=event,
    )
    return {
        "output_path": str(output_path),
        "history_path": str(history_path),
        "event_path": str(event_path),
    }
