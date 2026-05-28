"""Inbound Telegram intake for member-submitted research.

This module treats Telegram messages as read-only inputs. It can record
world-event datapoints, queue Research Analyst shadow triage packets, and add
trading-strategy considerations. It cannot create trade candidates, approve
risk, submit orders, open command paths, or enable live capital.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from orchestrator.agent_runtime import create_shadow_triage_packet
from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.secrets import secret_status, secret_value

TELEGRAM_INBOUND_SCHEMA_VERSION = 1
TELEGRAM_INBOUND_RECORDS = "telegram_inbound_intake.jsonl"
TELEGRAM_INBOUND_WORLD_EVENTS = "telegram_world_event_datapoints.jsonl"
TELEGRAM_INBOUND_STRATEGY_CONSIDERATIONS = "telegram_strategy_considerations.jsonl"
TELEGRAM_INBOUND_SUMMARY = "telegram_inbound_intake_summary.json"
TELEGRAM_INBOUND_OFFSET = "telegram_inbound_offset.json"

TELEGRAM_INBOUND_BOUNDARY = (
    "Telegram inbound intake is read-only member research intake. It can log "
    "world-event datapoints, queue Research Analyst shadow review, and add "
    "strategy considerations, but it cannot create signals, trade candidates, "
    "risk approvals, execution approvals, paper orders, broker writes, Telegram "
    "commands, Q-CTRL jobs, or live-capital authority."
)

AUTHORITY_FLAGS: tuple[str, ...] = (
    "signal_authority",
    "trade_candidate_creation_allowed",
    "risk_handoff_allowed",
    "risk_approval_authority",
    "execution_allowed",
    "execution_authority",
    "paper_order_allowed",
    "paper_order_authority",
    "broker_write_allowed",
    "broker_write_authority",
    "telegram_command_authority",
    "telegram_trade_command_allowed",
    "qctrl_provider_call_allowed",
    "quantum_hardware_submission_allowed",
    "live_capital_enabled",
    "live_capital_authority",
)

URL_PATTERN = re.compile(r"https?://[^\s<>()\"']+", re.IGNORECASE)
TOKEN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\d{6,}:[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bvcp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
    re.compile(r"\bsb_secret_[0-9A-Za-z_-]{12,}\b"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"@[A-Za-z0-9_]{5,}"),
    re.compile(r"/Users/[^ \n\t]+|/private/[^ \n\t]+|/var/folders/[^ \n\t]+"),
)

STRATEGY_TERMS = (
    "trading strategy",
    "strategy",
    "philosophy",
    "approach",
    "playbook",
    "edge",
    "entry",
    "exit",
    "stop loss",
    "risk reward",
    "position sizing",
    "sizing",
    "backtest",
    "mean reversion",
    "momentum",
    "trend following",
    "breakout",
    "opening range",
    "pead",
    "portfolio construction",
    "hedge",
)

WORLD_EVENT_TERMS = (
    "article",
    "news",
    "world event",
    "event",
    "war",
    "conflict",
    "missile",
    "sanction",
    "election",
    "central bank",
    "fed",
    "rate",
    "inflation",
    "oil",
    "crude",
    "shipping",
    "hormuz",
    "taiwan",
    "china",
    "iran",
    "russia",
    "ukraine",
    "semiconductor",
    "defence",
    "defense",
    "silver",
    "sec filing",
)

TOPIC_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("crude_oil", ("oil", "crude", "wti", "brent", "hormuz", "tanker", "opec")),
    ("defence", ("defence", "defense", "missile", "military", "lockheed", "rtx", "northrop")),
    ("semiconductors", ("semiconductor", "chip", "taiwan", "tsmc", "nvidia", "asml")),
    ("silver", ("silver", "slv", "miner", "precious metal")),
    ("macro", ("fed", "rate", "inflation", "cpi", "jobs", "treasury", "dollar")),
    ("prediction_markets", ("polymarket", "kalshi", "prediction market", "odds")),
    ("strategy_research", STRATEGY_TERMS),
)


@dataclass(frozen=True)
class TelegramInboundRecord:
    schema_version: int
    intake_id: str
    dedupe_key: str
    update_ref_hash: str
    chat_ref_hash: str
    sender_ref_hash: str
    intake_type: str
    status: str
    source: str
    source_type: str
    text_excerpt: str
    normalized_summary: str
    url_refs: tuple[str, ...]
    topic_tags: tuple[str, ...]
    observed_at: str
    received_at: str
    event_log_written: bool
    research_triage_packet_id: str | None
    strategy_consideration_written: bool
    world_event_datapoint_written: bool
    authority_flags: dict[str, bool]
    signal_authority: bool
    trade_candidate_creation_allowed: bool
    risk_handoff_allowed: bool
    execution_allowed: bool
    paper_order_allowed: bool
    broker_write_allowed: bool
    telegram_command_authority: bool
    live_capital_enabled: bool
    boundary: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["url_refs"] = list(self.url_refs)
        payload["topic_tags"] = list(self.topic_tags)
        return payload


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_path(settings: Settings, filename: str) -> Path:
    path = Path(settings.runtime_dir) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _authority_defaults() -> dict[str, bool]:
    return {field: False for field in AUTHORITY_FLAGS}


def _hash_ref(value: Any) -> str:
    text = str(value or "unknown").encode("utf-8")
    return hashlib.sha256(text).hexdigest()[:24]


def _sanitize_text(value: Any, *, limit: int = 2000) -> str:
    text = str(value or "").replace("\x00", " ").strip()
    for pattern in TOKEN_PATTERNS:
        text = pattern.sub("[redacted]", text)
    text = re.sub(r"\s+", " ", text)
    return text[:limit]


def _safe_urls(text: str) -> tuple[str, ...]:
    refs: list[str] = []
    for match in URL_PATTERN.findall(text):
        parsed = urllib.parse.urlsplit(match.rstrip(".,;!?)"))
        if not parsed.scheme or not parsed.netloc:
            continue
        safe = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
        if safe not in refs:
            refs.append(safe[:500])
    return tuple(refs[:5])


def _topic_tags(text: str, intake_type: str) -> tuple[str, ...]:
    lowered = text.lower()
    tags = [tag for tag, needles in TOPIC_KEYWORDS if any(needle in lowered for needle in needles)]
    if intake_type == "world_event" and "member_world_event" not in tags:
        tags.insert(0, "member_world_event")
    if intake_type == "strategy_consideration" and "member_strategy_consideration" not in tags:
        tags.insert(0, "member_strategy_consideration")
    return tuple(dict.fromkeys(tags))[:8]


def classify_telegram_text(text: str) -> str:
    lowered = text.lower()
    if "#strategy" in lowered or "#trading" in lowered:
        return "strategy_consideration"
    if any(term in lowered for term in STRATEGY_TERMS):
        return "strategy_consideration"
    if URL_PATTERN.search(text) or "#news" in lowered or "#world" in lowered:
        return "world_event"
    if any(term in lowered for term in WORLD_EVENT_TERMS):
        return "world_event"
    return "ignored_unclassified"


def _extract_message(update: dict[str, Any]) -> dict[str, Any] | None:
    for key in ("message", "channel_post", "edited_message", "edited_channel_post"):
        value = update.get(key)
        if isinstance(value, dict):
            return value
    return None


def _message_text(message: dict[str, Any]) -> str:
    return str(message.get("text") or message.get("caption") or "").strip()


def _dedupe_key(update: dict[str, Any], message: dict[str, Any], text: str) -> str:
    identity = {
        "update_id": update.get("update_id"),
        "message_id": message.get("message_id"),
        "chat_id": (message.get("chat") or {}).get("id") if isinstance(message.get("chat"), dict) else None,
        "date": message.get("date"),
        "text_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_telegram_inbound_record(update: dict[str, Any]) -> TelegramInboundRecord | None:
    message = _extract_message(update)
    if not message:
        return None
    raw_text = _message_text(message)
    if not raw_text:
        return None
    text = _sanitize_text(raw_text)
    intake_type = classify_telegram_text(text)
    chat = message.get("chat") if isinstance(message.get("chat"), dict) else {}
    sender = message.get("from") if isinstance(message.get("from"), dict) else {}
    observed_at = _now()
    if isinstance(message.get("date"), int):
        observed_at = datetime.fromtimestamp(int(message["date"]), tz=timezone.utc).isoformat()
    status = {
        "world_event": "recorded_world_event_datapoint",
        "strategy_consideration": "recorded_strategy_consideration",
    }.get(intake_type, "ignored_unclassified")
    summary_prefix = {
        "world_event": "Telegram member-submitted world event",
        "strategy_consideration": "Telegram member-submitted strategy consideration",
    }.get(intake_type, "Telegram member message")
    return TelegramInboundRecord(
        schema_version=TELEGRAM_INBOUND_SCHEMA_VERSION,
        intake_id=f"telegram-inbound:{uuid4()}",
        dedupe_key=_dedupe_key(update, message, text),
        update_ref_hash=_hash_ref(update.get("update_id")),
        chat_ref_hash=_hash_ref(chat.get("id")),
        sender_ref_hash=_hash_ref(sender.get("id") or sender.get("username") or sender.get("first_name")),
        intake_type=intake_type,
        status=status,
        source="telegram_member_submission",
        source_type="telegram_inbound_message",
        text_excerpt=text[:700],
        normalized_summary=f"{summary_prefix}: {text[:240]}",
        url_refs=_safe_urls(text),
        topic_tags=_topic_tags(text, intake_type),
        observed_at=observed_at,
        received_at=_now(),
        event_log_written=False,
        research_triage_packet_id=None,
        strategy_consideration_written=False,
        world_event_datapoint_written=False,
        authority_flags=_authority_defaults(),
        signal_authority=False,
        trade_candidate_creation_allowed=False,
        risk_handoff_allowed=False,
        execution_allowed=False,
        paper_order_allowed=False,
        broker_write_allowed=False,
        telegram_command_authority=False,
        live_capital_enabled=False,
        boundary=TELEGRAM_INBOUND_BOUNDARY,
    )


def validate_telegram_inbound_record(record: TelegramInboundRecord | dict[str, Any]) -> list[str]:
    payload = record.to_dict() if isinstance(record, TelegramInboundRecord) else record
    errors: list[str] = []
    if payload.get("schema_version") != TELEGRAM_INBOUND_SCHEMA_VERSION:
        errors.append("telegram_inbound_schema_version_mismatch")
    if payload.get("intake_type") not in {"world_event", "strategy_consideration", "ignored_unclassified"}:
        errors.append("telegram_inbound_type_invalid")
    if not str(payload.get("dedupe_key") or "").strip():
        errors.append("telegram_inbound_dedupe_missing")
    if "@" in json.dumps(payload, sort_keys=True):
        errors.append("telegram_inbound_handle_like_content_exposed")
    for forbidden in ("chat_id", "username", "first_name", "last_name", "token", "api_key"):
        if forbidden in json.dumps(payload, sort_keys=True).lower():
            errors.append(f"telegram_inbound_forbidden_content:{forbidden}")
    for field in (
        "signal_authority",
        "trade_candidate_creation_allowed",
        "risk_handoff_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "telegram_command_authority",
        "live_capital_enabled",
    ):
        if payload.get(field) is not False:
            errors.append(f"telegram_inbound_authority_enabled:{field}")
    flags = payload.get("authority_flags", {})
    if not isinstance(flags, dict):
        errors.append("telegram_inbound_authority_flags_missing")
    else:
        for field in AUTHORITY_FLAGS:
            if flags.get(field) is not False:
                errors.append(f"telegram_inbound_authority_flag_enabled:{field}")
    if "read-only member research intake" not in str(payload.get("boundary") or ""):
        errors.append("telegram_inbound_boundary_weak")
    return errors


class TelegramInboundIntakeStore:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self.records_path = _runtime_path(self.settings, TELEGRAM_INBOUND_RECORDS)
        self.world_events_path = _runtime_path(self.settings, TELEGRAM_INBOUND_WORLD_EVENTS)
        self.strategy_considerations_path = _runtime_path(
            self.settings,
            TELEGRAM_INBOUND_STRATEGY_CONSIDERATIONS,
        )
        self.summary_path = _runtime_path(self.settings, TELEGRAM_INBOUND_SUMMARY)
        self.offset_path = _runtime_path(self.settings, TELEGRAM_INBOUND_OFFSET)

    def read_records(self, limit: int | None = None) -> tuple[TelegramInboundRecord, ...]:
        records = self._read_records_file(self.records_path)
        if limit is not None:
            records = records[-limit:]
        return tuple(records)

    def read_strategy_considerations(self, limit: int | None = None) -> tuple[dict[str, Any], ...]:
        rows = self._read_jsonl(self.strategy_considerations_path)
        if limit is not None:
            rows = rows[-limit:]
        return tuple(rows)

    def read_world_events(self, limit: int | None = None) -> tuple[dict[str, Any], ...]:
        rows = self._read_jsonl(self.world_events_path)
        if limit is not None:
            rows = rows[-limit:]
        return tuple(rows)

    def add_record(
        self,
        record: TelegramInboundRecord,
        *,
        log_event: bool = True,
        queue_research: bool = True,
    ) -> dict[str, Any]:
        errors = validate_telegram_inbound_record(record)
        if errors:
            raise ValueError("invalid Telegram inbound record: " + ",".join(errors))
        existing = {item.dedupe_key for item in self.read_records()}
        if record.dedupe_key in existing:
            return {
                "status": "duplicate_ignored",
                "intake_id": record.intake_id,
                "dedupe_key": record.dedupe_key,
                "created": False,
            }

        payload = record.to_dict()
        event_log_written = False
        research_packet_id: str | None = None
        strategy_written = False
        world_event_written = False

        if record.intake_type == "world_event":
            world_row = self._world_event_row(payload)
            with self.world_events_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(world_row, sort_keys=True) + "\n")
            world_event_written = True
            if queue_research:
                packet = create_shadow_triage_packet(
                    source_event_refs=(f"telegram_world_event:{record.intake_id}",),
                    summary=record.normalized_summary,
                    uncertainty="member_submitted_requires_corroboration",
                    read_only_context={
                        "telegram_inbound_intake": {
                            "intake_id": record.intake_id,
                            "intake_type": record.intake_type,
                            "topic_tags": list(record.topic_tags),
                            "url_count": len(record.url_refs),
                            "source_quorum_credit_allowed": False,
                            "trade_candidate_creation_allowed": False,
                            "paper_order_allowed": False,
                            "boundary": TELEGRAM_INBOUND_BOUNDARY,
                        }
                    },
                    settings=self.settings,
                    event_log=EventLog(echo=False),
                )
                research_packet_id = str(packet.get("packet_id") or "")
        elif record.intake_type == "strategy_consideration":
            strategy_row = self._strategy_consideration_row(payload)
            with self.strategy_considerations_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(strategy_row, sort_keys=True) + "\n")
            strategy_written = True

        if log_event:
            event_type = {
                "world_event": "telegram_world_event_datapoint_recorded",
                "strategy_consideration": "telegram_strategy_consideration_recorded",
            }.get(record.intake_type, "telegram_inbound_message_ignored")
            EventLog(echo=False).write(
                event_type,
                "telegram_inbound_intake",
                {
                    "intake_id": record.intake_id,
                    "intake_type": record.intake_type,
                    "status": record.status,
                    "url_count": len(record.url_refs),
                    "topic_tags": list(record.topic_tags),
                    "research_triage_packet_id": research_packet_id,
                    "strategy_consideration_written": strategy_written,
                    "world_event_datapoint_written": world_event_written,
                    "trade_candidate_creation_allowed": False,
                    "execution_allowed": False,
                    "paper_order_allowed": False,
                    "broker_write_allowed": False,
                    "telegram_command_authority": False,
                    "boundary": TELEGRAM_INBOUND_BOUNDARY,
                },
            )
            event_log_written = True

        payload["event_log_written"] = event_log_written
        payload["research_triage_packet_id"] = research_packet_id
        payload["strategy_consideration_written"] = strategy_written
        payload["world_event_datapoint_written"] = world_event_written
        with self.records_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
        self.write_summary()
        return {
            "status": "created",
            "intake_id": record.intake_id,
            "dedupe_key": record.dedupe_key,
            "created": True,
            "intake_type": record.intake_type,
            "research_triage_packet_id": research_packet_id,
        }

    def latest_offset(self) -> int | None:
        if not self.offset_path.exists():
            return None
        try:
            payload = json.loads(self.offset_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
        value = payload.get("next_update_offset")
        return int(value) if isinstance(value, int) else None

    def write_offset(self, next_update_offset: int) -> None:
        self.offset_path.write_text(
            json.dumps(
                {
                    "schema_version": TELEGRAM_INBOUND_SCHEMA_VERSION,
                    "updated_at": _now(),
                    "next_update_offset": next_update_offset,
                    "boundary": "Offset only. No chat IDs, handles, or message bodies are persisted here.",
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def summary(self) -> dict[str, Any]:
        records = self.read_records()
        world_events = self.read_world_events()
        strategy_considerations = self.read_strategy_considerations()
        latest = records[-1] if records else None
        return {
            "status": "ready" if records else "ready_no_messages",
            "schema_version": TELEGRAM_INBOUND_SCHEMA_VERSION,
            "enabled": bool(getattr(self.settings, "telegram_inbound_intake_enabled", True)),
            "bot_configured": secret_status("TELEGRAM_BOT_TOKEN", self.settings).configured,
            "polling_mode": "getUpdates_explicit_poll",
            "record_count": len(records),
            "world_event_datapoint_count": len(world_events),
            "strategy_consideration_count": len(strategy_considerations),
            "ignored_message_count": sum(1 for item in records if item.intake_type == "ignored_unclassified"),
            "research_triage_packet_count": sum(1 for item in records if item.research_triage_packet_id),
            "latest_intake_type": latest.intake_type if latest else None,
            "latest_status": latest.status if latest else None,
            "latest_observed_at": latest.observed_at if latest else None,
            "recent_records": [self._public_record(item) for item in records[-5:]][::-1],
            "recent_strategy_considerations": [
                self._public_strategy_row(row) for row in strategy_considerations[-5:]
            ][::-1],
            "recent_world_events": [self._public_world_row(row) for row in world_events[-5:]][::-1],
            "trade_candidate_creation_allowed": False,
            "risk_handoff_allowed": False,
            "execution_allowed": False,
            "paper_order_allowed": False,
            "broker_write_allowed": False,
            "telegram_command_authority": False,
            "live_capital_enabled": False,
            "boundary": TELEGRAM_INBOUND_BOUNDARY,
        }

    def write_summary(self) -> dict[str, Any]:
        summary = self.summary()
        self.summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return summary

    def _world_event_row(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": TELEGRAM_INBOUND_SCHEMA_VERSION,
            "datapoint_id": payload["intake_id"],
            "source": "telegram_member_submission",
            "source_type": "member_submitted_world_event",
            "summary": payload["normalized_summary"],
            "text_excerpt": payload["text_excerpt"],
            "url_refs": payload["url_refs"],
            "topic_tags": payload["topic_tags"],
            "observed_at": payload["observed_at"],
            "source_quorum_credit_allowed": False,
            "trade_candidate_creation_allowed": False,
            "paper_order_allowed": False,
            "execution_allowed": False,
            "boundary": TELEGRAM_INBOUND_BOUNDARY,
        }

    def _strategy_consideration_row(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": TELEGRAM_INBOUND_SCHEMA_VERSION,
            "consideration_id": payload["intake_id"],
            "source": "telegram_member_submission",
            "source_type": "member_submitted_strategy_consideration",
            "summary": payload["normalized_summary"],
            "text_excerpt": payload["text_excerpt"],
            "url_refs": payload["url_refs"],
            "topic_tags": payload["topic_tags"],
            "observed_at": payload["observed_at"],
            "strategy_lead_context_allowed": True,
            "phase4_annotation_allowed": True,
            "trade_candidate_creation_allowed": False,
            "risk_handoff_allowed": False,
            "execution_allowed": False,
            "paper_order_allowed": False,
            "broker_write_allowed": False,
            "live_capital_enabled": False,
            "boundary": TELEGRAM_INBOUND_BOUNDARY,
        }

    def _public_record(self, record: TelegramInboundRecord) -> dict[str, Any]:
        return {
            "intake_id": record.intake_id,
            "intake_type": record.intake_type,
            "status": record.status,
            "summary": record.normalized_summary[:260],
            "url_count": len(record.url_refs),
            "topic_tags": list(record.topic_tags),
            "observed_at": record.observed_at,
            "research_triage_packet_created": bool(record.research_triage_packet_id),
            "strategy_consideration_written": record.strategy_consideration_written,
            "world_event_datapoint_written": record.world_event_datapoint_written,
        }

    def _public_strategy_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "consideration_id": str(row.get("consideration_id") or "")[:160],
            "summary": str(row.get("summary") or "")[:260],
            "topic_tags": list(row.get("topic_tags") or [])[:8],
            "observed_at": str(row.get("observed_at") or ""),
            "strategy_lead_context_allowed": row.get("strategy_lead_context_allowed") is True,
            "trade_candidate_creation_allowed": False,
        }

    def _public_world_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "datapoint_id": str(row.get("datapoint_id") or "")[:160],
            "summary": str(row.get("summary") or "")[:260],
            "topic_tags": list(row.get("topic_tags") or [])[:8],
            "url_count": len(row.get("url_refs") or []),
            "observed_at": str(row.get("observed_at") or ""),
            "source_quorum_credit_allowed": False,
        }

    def _read_records_file(self, path: Path) -> list[TelegramInboundRecord]:
        records: list[TelegramInboundRecord] = []
        for payload in self._read_jsonl(path):
            records.append(TelegramInboundRecord(**payload))
        for record in records:
            errors = validate_telegram_inbound_record(record)
            if errors:
                raise ValueError("invalid Telegram inbound record on disk: " + ",".join(errors))
        return records

    def _read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    payload = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid Telegram inbound JSONL line {line_number} in {path.name}") from exc
                if isinstance(payload, dict):
                    rows.append(payload)
        return rows


def _telegram_request(token: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    data = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(request, timeout=20) as response:
        loaded = json.loads(response.read().decode("utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("Telegram getUpdates returned non-object response")
    return loaded


def poll_telegram_inbound_updates(
    *,
    settings: Settings | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    store = TelegramInboundIntakeStore(settings=settings)
    if not getattr(settings, "telegram_inbound_intake_enabled", True):
        return {"status": "disabled", "created_count": 0, "duplicate_count": 0, "ignored_count": 0}
    token = secret_value("TELEGRAM_BOT_TOKEN", settings)
    if not token:
        return {"status": "missing_bot_token", "created_count": 0, "duplicate_count": 0, "ignored_count": 0}
    request_payload: dict[str, Any] = {
        "limit": max(1, min(int(limit), 100)),
        "timeout": 0,
        "allowed_updates": json.dumps(["message", "channel_post", "edited_message", "edited_channel_post"]),
    }
    offset = store.latest_offset()
    if offset is not None:
        request_payload["offset"] = offset
    try:
        response = _telegram_request(token, request_payload)
    except Exception:  # noqa: BLE001 - never expose provider URLs or tokens in tracebacks
        return {
            "status": "provider_error",
            "created_count": 0,
            "duplicate_count": 0,
            "ignored_count": 0,
            "boundary": TELEGRAM_INBOUND_BOUNDARY,
        }
    updates = response.get("result", [])
    if not response.get("ok") or not isinstance(updates, list):
        return {"status": "provider_error", "created_count": 0, "duplicate_count": 0, "ignored_count": 0}
    created = 0
    duplicates = 0
    ignored = 0
    max_update_id: int | None = None
    for update in updates:
        if not isinstance(update, dict):
            continue
        update_id = update.get("update_id")
        if isinstance(update_id, int):
            max_update_id = max(update_id, max_update_id or update_id)
        record = build_telegram_inbound_record(update)
        if record is None:
            ignored += 1
            continue
        result = store.add_record(record)
        if result["status"] == "created":
            created += 1
        else:
            duplicates += 1
    if max_update_id is not None:
        store.write_offset(max_update_id + 1)
    summary = store.write_summary()
    return {
        "status": "ok",
        "fetched_update_count": len(updates),
        "created_count": created,
        "duplicate_count": duplicates,
        "ignored_count": ignored,
        "next_update_offset_written": max_update_id is not None,
        "record_count": summary["record_count"],
        "world_event_datapoint_count": summary["world_event_datapoint_count"],
        "strategy_consideration_count": summary["strategy_consideration_count"],
        "boundary": TELEGRAM_INBOUND_BOUNDARY,
    }


def sample_telegram_world_event_update() -> dict[str, Any]:
    return {
        "update_id": 900001,
        "message": {
            "message_id": 101,
            "date": 1_779_922_800,
            "chat": {"id": -1001234567890, "type": "group", "title": "Qadam Test"},
            "from": {"id": 42, "first_name": "Member"},
            "text": (
                "Interesting article on Strait of Hormuz tanker risk and crude volatility: "
                "https://example.com/world/oil-hormuz-risk"
            ),
        },
    }


def sample_telegram_strategy_update() -> dict[str, Any]:
    return {
        "update_id": 900002,
        "message": {
            "message_id": 102,
            "date": 1_779_922_860,
            "chat": {"id": -1001234567890, "type": "group", "title": "Qadam Test"},
            "from": {"id": 43, "first_name": "Member"},
            "text": (
                "#strategy Qadam should consider a volatility breakout approach: wait for "
                "confirmed catalyst, enter only after price breaks the opening range, size "
                "by risk, and exit if the catalyst is invalidated."
            ),
        },
    }


def ensure_sample_telegram_inbound_intake(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    store = TelegramInboundIntakeStore(settings=settings)
    results: list[dict[str, Any]] = []
    for update in (sample_telegram_world_event_update(), sample_telegram_strategy_update()):
        record = build_telegram_inbound_record(update)
        if record is not None:
            results.append(store.add_record(record))
    summary = store.write_summary()
    return {
        "status": "ok",
        "created_count": sum(1 for result in results if result.get("created") is True),
        "duplicate_count": sum(1 for result in results if result.get("status") == "duplicate_ignored"),
        "result_count": len(results),
        "summary": summary,
        "boundary": TELEGRAM_INBOUND_BOUNDARY,
    }


def telegram_inbound_intake_public_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    return TelegramInboundIntakeStore(settings=settings).summary()
