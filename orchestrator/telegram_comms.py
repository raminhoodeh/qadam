"""Local Telegram communications rail for founding Fund Managers.

D8A starts in dry-run mode. It renders safe outbound messages into a local
outbox and exposes only public-safe delivery state to the cockpit.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.intelligence import shadow_intelligence_summary
from orchestrator.secrets import secret_status
from orchestrator.telegram_message_quality import (
    assert_specific_telegram_message,
    telegram_human_message_style,
)
from orchestrator.trade_intent import TradeIntentStore, ensure_d5_sample_trade_intents

TELEGRAM_COMMUNICATIONS_SCHEMA_VERSION = 1

FOUNDING_TELEGRAM_MEMBERS: tuple[tuple[str, str], ...] = (
    ("ramin", "Ramin"),
    ("troy", "Troy"),
    ("ion", "Ion"),
    ("akber", "Akber"),
    ("anas", "Anas"),
)

TELEGRAM_MESSAGE_CLASSES = {
    "observed_signal",
    "trade_candidate",
    "blocked_trade",
    "staged_paper_order",
    "submitted_paper_order",
    "open_position",
    "closed_trade",
    "postmortem_due",
    "postmortem_complete",
    "insight_digest",
    "source_degraded",
    "model_degraded",
    "kill_switch",
    "dashboard_snapshot_stale",
    "codebase_upgrade",
}

TELEGRAM_OUTBOX_STATUSES = {"queued", "sent", "failed", "retried", "suppressed"}
TELEGRAM_ALLOWED_PAPER_ORDER_STATES = {"staged_paper_order", "submitted_paper_order"}
FORBIDDEN_TELEGRAM_TEXT = (
    re.compile(r"\babout to trade\b", re.IGNORECASE),
    re.compile(r"\bguaranteed\b", re.IGNORECASE),
    re.compile(r"\bsure thing\b", re.IGNORECASE),
    re.compile(r"\brisk[- ]?free\b", re.IGNORECASE),
    re.compile(r"\d{6,}:[A-Za-z0-9_-]{20,}"),
    re.compile(r"@[A-Za-z0-9_]{5,}"),
    re.compile(r"/Users/|/private/|/var/folders/|\\Users\\"),
)


@dataclass(frozen=True)
class TelegramMember:
    schema_version: int
    member_key: str
    display_name: str
    status: str
    delivery_preference: str
    chat_id: str | None
    handle: str | None
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TelegramOutboxMessage:
    schema_version: int
    message_id: str
    message_class: str
    title: str
    body: str
    status: str
    mode: str
    recipient_scope: str
    target_ref: str
    retry_count: int
    failure_reason: str
    send_allowed: bool
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_path(settings: Settings, filename: str) -> Path:
    path = Path(settings.runtime_dir) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _assert_safe_message(text: str) -> None:
    for pattern in FORBIDDEN_TELEGRAM_TEXT:
        if pattern.search(text):
            raise ValueError("unsafe Telegram message text")


def _normalize_status(status: str) -> str:
    if status not in TELEGRAM_OUTBOX_STATUSES:
        raise ValueError(f"invalid Telegram outbox status: {status}")
    return status


def _display_ref(value: str | None, fallback: str = "qadam") -> str:
    text = str(value or fallback).strip()
    return text.replace("\n", " ")[:120] or fallback


def render_telegram_message(message_class: str, context: dict[str, Any]) -> tuple[str, str]:
    if message_class not in TELEGRAM_MESSAGE_CLASSES:
        raise ValueError(f"invalid Telegram message class: {message_class}")

    if message_class == "trade_candidate":
        title = f"Candidate: {_display_ref(context.get('instrument'), 'trade candidate')}"
        body = (
            f"Qadam is looking at {_display_ref(context.get('instrument'), 'a paper trade idea')} as a possible paper-trade candidate. "
            f"The reason is {_display_ref(context.get('catalyst'), 'a structured market signal changed')}, and the supporting context is "
            f"{_display_ref(context.get('evidence_summary'), 'still being gathered')}."
            "\n\n"
            f"For now, this is only something to watch. {_display_ref(context.get('current_impact'), 'No paper order exists yet')}, "
            "and Telegram cannot approve it or move it into the broker route."
        )
    elif message_class == "blocked_trade":
        title = f"Blocked: {_display_ref(context.get('instrument'), 'trade idea')}"
        body = (
            f"Qadam considered {_display_ref(context.get('instrument'), 'a paper trade idea')} but decided not to let it move forward. "
            f"The setup mattered because {_display_ref(context.get('catalyst'), 'a market signal changed')}, but the evidence was "
            f"{_display_ref(context.get('evidence_summary'), 'not strong enough')}."
            "\n\n"
            f"The block is {_display_ref(context.get('blocked_reason'), 'it did not clear the safety gates')}. "
            f"{_display_ref(context.get('current_impact'), 'The idea remains research only')}, with no paper order and no broker action."
        )
    elif message_class in TELEGRAM_ALLOWED_PAPER_ORDER_STATES:
        title = f"{message_class.replace('_', ' ').title()}: {_display_ref(context.get('instrument'), 'paper order')}"
        body = (
            f"Qadam has reached a paper-order lifecycle step for {_display_ref(context.get('instrument'), 'a paper instrument')}. "
            f"This happened because {_display_ref(context.get('catalyst'), 'the guarded paper workflow reached the next state')}, "
            f"with supporting context of {_display_ref(context.get('evidence_summary'), 'the paper ledger state')}."
            "\n\n"
            f"{_display_ref(context.get('current_impact'), 'Members can review the state, but cannot act through Telegram')}. "
            "This is still paper mode only, and live capital remains off."
        )
    elif message_class == "insight_digest":
        title = _display_ref(context.get("title"), "Insight digest")
        body = (
            f"Qadam's current research focus is {_display_ref(context.get('theme'), 'the latest market evidence')}. "
            f"This matters because {_display_ref(context.get('why_it_matters'), 'the research picture changed')}, "
            f"and the evidence is {_display_ref(context.get('evidence'), 'available in the research ledger')}."
            "\n\n"
            f"{_display_ref(context.get('current_impact'), 'This changes research context only')}. "
            f"The important limit is that {_display_ref(context.get('block'), 'this is not yet executable')}, so this message is not a trade signal."
        )
    elif message_class in {"source_degraded", "model_degraded", "kill_switch", "dashboard_snapshot_stale"}:
        title = _display_ref(context.get("title"), message_class.replace("_", " ").title())
        body = (
            f"Qadam has noticed a system warning around {_display_ref(context.get('subject'), 'one part of the system')}. "
            f"This matters because {_display_ref(context.get('why_it_matters'), 'member attention may be needed')}, "
            f"and the current evidence is {_display_ref(context.get('evidence'), 'a health status change')}."
            "\n\n"
            f"{_display_ref(context.get('current_impact'), 'Qadam fails closed for the affected workflow until recovery')}. "
            f"The block is {_display_ref(context.get('block'), 'fail closed until recovered')}, and Telegram still has no trade command path."
        )
    else:
        title = _display_ref(context.get("title"), message_class.replace("_", " ").title())
        why_it_matters = context.get("why_it_matters") or context.get("catalyst")
        evidence = context.get("evidence") or context.get("evidence_summary")
        body = (
            f"Qadam has a new update about {_display_ref(context.get('subject'), 'the paper lifecycle')}. "
            f"It matters because {_display_ref(why_it_matters, 'the paper lifecycle evidence changed')}, "
            f"with supporting context of {_display_ref(evidence, 'the recorded lifecycle state')}."
            "\n\n"
            f"{_display_ref(context.get('current_impact'), 'Members can review the state but cannot act from Telegram')}. "
            f"The important limit is {_display_ref(context.get('block'), 'Telegram has no live-capital or trade authority')}."
        )

    _assert_safe_message(title)
    _assert_safe_message(body)
    assert_specific_telegram_message(title, body)
    style = telegram_human_message_style(title, body)
    if style["status"] != "human":
        raise ValueError("technical Telegram message text")
    return title, body


class TelegramCommunicationsStore:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self.members_path = _runtime_path(self.settings, "telegram-members.json")
        self.outbox_path = _runtime_path(self.settings, "telegram-outbox.jsonl")
        self.deliveries_path = _runtime_path(self.settings, "telegram-deliveries.jsonl")
        self.digests_path = _runtime_path(self.settings, "telegram-digests.jsonl")

    def ensure_member_registry(self) -> tuple[TelegramMember, ...]:
        if not self.members_path.exists():
            now = _now()
            members = [
                TelegramMember(
                    schema_version=TELEGRAM_COMMUNICATIONS_SCHEMA_VERSION,
                    member_key=member_key,
                    display_name=display_name,
                    status="pending_chat_id",
                    delivery_preference="critical_trades_and_digests",
                    chat_id=None,
                    handle=None,
                    created_at=now,
                    updated_at=now,
                )
                for member_key, display_name in FOUNDING_TELEGRAM_MEMBERS
            ]
            self.members_path.write_text(
                json.dumps([member.to_dict() for member in members], indent=2, sort_keys=True),
                encoding="utf-8",
            )
        return self.read_members()

    def read_members(self) -> tuple[TelegramMember, ...]:
        if not self.members_path.exists():
            return ()
        payload = json.loads(self.members_path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("telegram member registry must be a list")
        members: list[TelegramMember] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            members.append(
                TelegramMember(
                    schema_version=int(item.get("schema_version", TELEGRAM_COMMUNICATIONS_SCHEMA_VERSION)),
                    member_key=str(item.get("member_key", "")),
                    display_name=str(item.get("display_name", "")),
                    status=str(item.get("status", "pending_chat_id")),
                    delivery_preference=str(item.get("delivery_preference", "critical_trades_and_digests")),
                    chat_id=item.get("chat_id"),
                    handle=item.get("handle"),
                    created_at=str(item.get("created_at", _now())),
                    updated_at=str(item.get("updated_at", _now())),
                )
            )
        return tuple(members)

    def read_outbox(self, limit: int | None = None) -> tuple[TelegramOutboxMessage, ...]:
        if not self.outbox_path.exists():
            return ()
        messages: list[TelegramOutboxMessage] = []
        with self.outbox_path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    payload = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid Telegram outbox line {line_number}") from exc
                messages.append(TelegramOutboxMessage(**payload))
        if limit is not None:
            messages = messages[-limit:]
        return tuple(messages)

    def add_outbox_message(
        self,
        *,
        message_class: str,
        context: dict[str, Any],
        target_ref: str,
        message_id: str | None = None,
        status: str = "queued",
        log_event: bool = True,
    ) -> TelegramOutboxMessage:
        status = _normalize_status(status)
        title, body = render_telegram_message(message_class, context)
        mode = "dry_run" if self.settings.telegram_dry_run else "live_send"
        send_allowed = bool(self.settings.telegram_enabled and not self.settings.telegram_dry_run)
        now = _now()
        message = TelegramOutboxMessage(
            schema_version=TELEGRAM_COMMUNICATIONS_SCHEMA_VERSION,
            message_id=message_id or str(uuid4()),
            message_class=message_class,
            title=title,
            body=body,
            status=status,
            mode=mode,
            recipient_scope="founding_fund_managers",
            target_ref=_display_ref(target_ref),
            retry_count=0,
            failure_reason="",
            send_allowed=send_allowed,
            created_at=now,
            updated_at=now,
        )
        with self.outbox_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(message.to_dict(), sort_keys=True) + "\n")
        if log_event:
            EventLog(echo=False).write(
                event_type="telegram_message_queued",
                component="telegram_communications",
                payload={
                    "message_id": message.message_id,
                    "message_class": message.message_class,
                    "status": message.status,
                    "mode": message.mode,
                    "send_allowed": message.send_allowed,
                    "boundary": "Telegram message queued locally without execution authority.",
                },
            )
        return message

    def public_status(self) -> dict[str, Any]:
        members = self.ensure_member_registry()
        outbox = self.read_outbox()
        trade_notifications_path = _runtime_path(
            self.settings,
            "telegram_trade_notifications.json",
        )
        trade_notifications: dict[str, Any] = {}
        if trade_notifications_path.exists():
            try:
                payload = json.loads(trade_notifications_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    trade_notifications = payload
            except json.JSONDecodeError:
                trade_notifications = {"status": "invalid_json"}
        daily_digest_path = _runtime_path(
            self.settings,
            "telegram_daily_portfolio_digest.json",
        )
        daily_digest: dict[str, Any] = {}
        if daily_digest_path.exists():
            try:
                payload = json.loads(daily_digest_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    daily_digest = payload
            except json.JSONDecodeError:
                daily_digest = {"status": "invalid_json"}
        codebase_upgrade_path = _runtime_path(
            self.settings,
            "telegram_codebase_upgrade_notification.json",
        )
        codebase_upgrade: dict[str, Any] = {}
        if codebase_upgrade_path.exists():
            try:
                payload = json.loads(codebase_upgrade_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    codebase_upgrade = payload
            except json.JSONDecodeError:
                codebase_upgrade = {"status": "invalid_json"}
        bot_configured = secret_status("TELEGRAM_BOT_TOKEN", self.settings).configured
        bot_username_configured = secret_status("TELEGRAM_BOT_USERNAME", self.settings).configured
        default_chat_configured = secret_status("TELEGRAM_DEFAULT_CHAT_ID", self.settings).configured
        group_chat_configured = secret_status("TELEGRAM_GROUP_CHAT_ID", self.settings).configured
        delivery_target_count = int(default_chat_configured) + int(group_chat_configured)
        counts = Counter(message.status for message in outbox)
        verified_members = [
            member for member in members if member.status == "verified" and bool(member.chat_id)
        ]
        pending_members = [
            member for member in members if member.status != "verified" or not member.chat_id
        ]
        failed_members = [member for member in members if member.status == "failed"]
        sent_messages = [message for message in outbox if message.status == "sent"]
        failed_messages = [message for message in outbox if message.status == "failed"]
        digest_messages = [message for message in outbox if message.message_class == "insight_digest"]
        recent = tuple(reversed(outbox[-5:]))
        if self.settings.telegram_dry_run:
            status = "dry_run"
        elif not self.settings.telegram_enabled:
            status = "disabled"
        elif not bot_configured:
            status = "degraded"
        else:
            status = "configured"
        return {
            "status": status,
            "schema_version": TELEGRAM_COMMUNICATIONS_SCHEMA_VERSION,
            "mode": "dry_run" if self.settings.telegram_dry_run else "live_send",
            "send_gate": "enabled" if self.settings.telegram_enabled else "disabled",
            "bot_configured": bot_configured,
            "bot_username_configured": bot_username_configured,
            "default_chat_configured": default_chat_configured,
            "group_chat_configured": group_chat_configured,
            "delivery_target_count": delivery_target_count,
            "delivery_target_modes": [
                mode
                for mode, configured in (
                    ("private_default", default_chat_configured),
                    ("group", group_chat_configured),
                )
                if configured
            ],
            "member_count": len(members),
            "verified_member_count": len(verified_members),
            "pending_member_count": len(pending_members),
            "failed_member_count": len(failed_members),
            "pending_queue_count": counts.get("queued", 0),
            "sent_count": counts.get("sent", 0),
            "failed_count": counts.get("failed", 0),
            "retried_count": counts.get("retried", 0),
            "suppressed_count": counts.get("suppressed", 0),
            "last_sent_time": sent_messages[-1].updated_at if sent_messages else None,
            "last_failure_reason": failed_messages[-1].failure_reason if failed_messages else "",
            "last_digest_title": digest_messages[-1].title if digest_messages else "",
            "active_message_classes": sorted({message.message_class for message in outbox}),
            "dry_run_message_count": sum(1 for message in outbox if message.mode == "dry_run"),
            "trade_group_notifications_enabled": (
                self.settings.telegram_trade_group_notifications_enabled
            ),
            "trade_group_notifications_dry_run": (
                self.settings.telegram_trade_group_notifications_dry_run
            ),
            "trade_group_notifications_status": trade_notifications.get("status", "not_run"),
            "trade_group_notifications_eligible_count": int(
                trade_notifications.get("eligible_notification_count", 0) or 0
            ),
            "trade_group_notifications_live_send_attempted_count": int(
                trade_notifications.get("live_send_attempted_count", 0) or 0
            ),
            "trade_group_notifications_live_send_succeeded_count": int(
                trade_notifications.get("live_send_succeeded_count", 0) or 0
            ),
            "daily_portfolio_digest_enabled": (
                self.settings.telegram_daily_portfolio_digest_enabled
            ),
            "daily_portfolio_digest_dry_run": (
                self.settings.telegram_daily_portfolio_digest_dry_run
            ),
            "daily_portfolio_digest_status": daily_digest.get("status", "not_run"),
            "daily_portfolio_digest_local_date": daily_digest.get("local_date"),
            "daily_portfolio_digest_due_for_delivery": (
                daily_digest.get("due_for_delivery") is True
            ),
            "daily_portfolio_digest_portfolio_balance_gbp": daily_digest.get(
                "portfolio_balance_gbp"
            ),
            "daily_portfolio_digest_portfolio_performance_pct": daily_digest.get(
                "portfolio_performance_pct"
            ),
            "daily_portfolio_digest_daily_trade_count": int(
                daily_digest.get("daily_trade_count", 0) or 0
            ),
            "daily_portfolio_digest_live_send_succeeded": (
                daily_digest.get("live_send_succeeded") is True
            ),
            "codebase_upgrade_notifications_enabled": (
                self.settings.telegram_codebase_upgrade_notifications_enabled
            ),
            "codebase_upgrade_notifications_dry_run": (
                self.settings.telegram_codebase_upgrade_notifications_dry_run
            ),
            "codebase_upgrade_notifications_status": codebase_upgrade.get("status", "not_run"),
            "codebase_upgrade_notifications_source": codebase_upgrade.get("source"),
            "codebase_upgrade_notifications_root_commit_short": codebase_upgrade.get(
                "root_commit_short"
            ),
            "codebase_upgrade_notifications_dashboard_commit_short": codebase_upgrade.get(
                "dashboard_commit_short"
            ),
            "codebase_upgrade_notifications_live_send_attempted": (
                codebase_upgrade.get("live_send_attempted") is True
            ),
            "codebase_upgrade_notifications_live_send_succeeded": (
                codebase_upgrade.get("live_send_succeeded") is True
            ),
            "recent_messages": [
                {
                    "message_id": message.message_id,
                    "message_class": message.message_class,
                    "title": message.title,
                    "status": message.status,
                    "mode": message.mode,
                    "target_ref": message.target_ref,
                    "send_allowed": message.send_allowed,
                    "created_at": message.created_at,
                }
                for message in recent
            ],
            "boundary": (
                "Telegram is outbound-only member communication. It cannot place, approve, "
                "reject, modify, close, or resize trades."
            ),
        }


def ensure_d8a_telegram_dry_run(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    ensure_d5_sample_trade_intents(settings)
    store = TelegramCommunicationsStore(settings=settings)
    store.ensure_member_registry()
    existing_ids = {message.message_id for message in store.read_outbox()}
    trade_store = TradeIntentStore(settings=settings)
    intents = trade_store.read_intents()
    candidate = next((intent for intent in intents if intent.status in {"candidate", "risk_review"}), None)
    blocked = next((intent for intent in intents if intent.status == "blocked"), None)
    shadow_summary = shadow_intelligence_summary(settings)
    samples: list[tuple[str, str, dict[str, Any], str]] = []
    if candidate:
        samples.append(
            (
                "d8a-sample-trade-candidate",
                "trade_candidate",
                candidate.to_dict(),
                f"trade_intent:{candidate.intent_id}",
            )
        )
    if blocked:
        samples.append(
            (
                "d8a-sample-blocked-trade",
                "blocked_trade",
                blocked.to_dict(),
                f"trade_intent:{blocked.intent_id}",
            )
        )
    samples.append(
        (
            "d8a-sample-insight-digest",
            "insight_digest",
            {
                "title": "Insight digest: shadow research queue",
                "theme": "Research Analyst shadow review",
                "why_it_matters": "members need high-signal updates without keeping the dashboard open",
                "evidence": f"{shadow_summary.get('store', {}).get('proposal_count', 0)} shadow proposals tracked",
                "block": "Signal Integrity Gate and Risk Agent are not reached",
            },
            "cognition:shadow_intelligence",
        )
    )
    samples.append(
        (
            "d8a-sample-system-warning",
            "source_degraded",
            {
                "title": "System warning: credentials pending",
                "subject": "source credential readiness",
                "why_it_matters": "missing credentials reduce evidence strength",
                "evidence": "status contract marks credential-gated sources separately",
                "block": "affected sources cannot influence signals until configured",
            },
            "system:source_health",
        )
    )

    created: list[str] = []
    for message_id, message_class, context, target_ref in samples:
        if message_id in existing_ids:
            continue
        store.add_outbox_message(
            message_id=message_id,
            message_class=message_class,
            context=context,
            target_ref=target_ref,
            status="queued",
        )
        created.append(message_id)
    return {
        "status": "ok",
        "created_count": len(created),
        "created_message_ids": created,
        "telegram": store.public_status(),
    }


def telegram_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    return TelegramCommunicationsStore(settings=settings).public_status()
