"""Lightweight scheduler guard for Qadam's twice-daily learning brief."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.daily_learning_automation import daily_learning_local_context
from orchestrator.daily_telegram_learning_brief import (
    daily_telegram_learning_delivery_key,
)


DAILY_LEARNING_SCHEDULER_ARTIFACT = "daily_learning_scheduler.json"
DAILY_LEARNING_SCHEDULER_RETRY_MINUTES = 15


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_timestamp(value: Any) -> datetime | None:
    text = str(value or "").strip().replace("Z", "+00:00")
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _runtime_dir(settings: Settings) -> Path:
    return Path(settings.runtime_dir)


def daily_learning_scheduler_path(settings: Settings | None = None) -> Path:
    settings = settings or Settings.from_env()
    return _runtime_dir(settings) / DAILY_LEARNING_SCHEDULER_ARTIFACT


def read_daily_learning_scheduler_state(
    settings: Settings | None = None,
) -> dict[str, Any]:
    path = daily_learning_scheduler_path(settings)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def sent_daily_learning_delivery_keys(settings: Settings | None = None) -> set[str]:
    settings = settings or Settings.from_env()
    path = _runtime_dir(settings) / "telegram-deliveries.jsonl"
    if not path.is_file():
        return set()
    keys: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            if (
                payload.get("message_class") == "daily_telegram_learning_brief"
                and payload.get("target") == "group"
                and payload.get("status") == "sent"
            ):
                key = str(payload.get("delivery_key") or "")
                if key:
                    keys.add(key)
    return keys


def build_daily_learning_scheduler_decision(
    *,
    settings: Settings | None = None,
    generated_at: str | None = None,
    sent_delivery_keys: set[str] | None = None,
    scheduler_state: dict[str, Any] | None = None,
    retry_minutes: int = DAILY_LEARNING_SCHEDULER_RETRY_MINUTES,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = generated_at or _now()
    generated = _parse_timestamp(generated_at) or datetime.now(timezone.utc)
    local_context = daily_learning_local_context(
        settings=settings,
        generated_at=generated_at,
    )
    delivery_key = daily_telegram_learning_delivery_key(
        local_context["local_date"],
        local_context["brief_slot"],
    )
    sent_keys = (
        sent_delivery_keys
        if sent_delivery_keys is not None
        else sent_daily_learning_delivery_keys(settings)
    )
    state = (
        scheduler_state
        if isinstance(scheduler_state, dict)
        else read_daily_learning_scheduler_state(settings)
    )
    last_attempt = None
    if state.get("delivery_key") == delivery_key:
        last_attempt = _parse_timestamp(state.get("last_attempt_at"))
    retry_after = last_attempt + timedelta(minutes=max(1, retry_minutes)) if last_attempt else None
    retry_ready = retry_after is None or generated >= retry_after
    already_sent = delivery_key in sent_keys
    due = local_context["due_for_delivery"] is True
    should_run = due and not already_sent and retry_ready
    if not due:
        reason = "slot_not_due"
    elif already_sent:
        reason = "slot_already_sent"
    elif not retry_ready:
        reason = "retry_cooldown_active"
    else:
        reason = "due_unsent_slot"
    return {
        "schema_version": 1,
        "artifact_type": "qadam_daily_learning_scheduler_decision",
        "generated_at": generated_at,
        "timezone": local_context["timezone"],
        "local_date": local_context["local_date"],
        "local_time": local_context["local_time"],
        "brief_slot": local_context["brief_slot"],
        "brief_slot_label": local_context["brief_slot_label"],
        "delivery_after_local_time": local_context["delivery_after_local_time"],
        "delivery_key": delivery_key,
        "due": due,
        "already_sent": already_sent,
        "retry_ready": retry_ready,
        "retry_after": retry_after.isoformat() if retry_after else None,
        "should_run": should_run,
        "reason": reason,
        "public_safe": True,
        "paper_only": True,
        "telegram_command_path_enabled": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
    }


def write_daily_learning_scheduler_attempt(
    *,
    decision: dict[str, Any],
    exit_code: int,
    automation: dict[str, Any],
    settings: Settings | None = None,
) -> Path:
    settings = settings or Settings.from_env()
    path = daily_learning_scheduler_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        **decision,
        "artifact_type": "qadam_daily_learning_scheduler_state",
        "last_attempt_at": decision.get("generated_at"),
        "last_exit_code": int(exit_code),
        "automation_status": automation.get("status"),
        "live_send_attempted": automation.get("live_send_attempted") is True,
        "live_send_succeeded": automation.get("live_send_succeeded") is True,
        "last_delivery_failure_category": automation.get(
            "last_delivery_failure_category"
        ),
    }
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)
    return path
