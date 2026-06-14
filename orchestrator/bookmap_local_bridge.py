"""Read-only Bookmap local bridge adapter.

Bookmap is optional local order-flow context for Qadam. It can observe local
market microstructure through a user-run bridge; it cannot create source quorum,
trade candidates, orders, broker writes, fills, receipts, reconciliation truth,
quantum jobs, or live capital authority.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen
from uuid import uuid4

from orchestrator.adapters import (
    RawPayloadArchive,
    SourceEnvelope,
    UNIFIED_EVENT_SCHEMA_VERSION,
    UnifiedEvent,
)
from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.intelligence import EvidenceItem
from orchestrator.secrets import secret_value
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT

BOOKMAP_LOCAL_BRIDGE_SCHEMA_VERSION = 1
BOOKMAP_LOCAL_BRIDGE_SOURCE_KEY = "bookmap"
BOOKMAP_LOCAL_BRIDGE_SOURCE_LABEL = "market.bookmap"
BOOKMAP_LOCAL_BRIDGE_PROVIDER_LABEL = "bookmap_local_readonly_bridge"
BOOKMAP_LOCAL_BRIDGE_EVENT_TYPE = "orderflow_context"
BOOKMAP_LOCAL_BRIDGE_TRUST_SCORE = 0.52
BOOKMAP_LOCAL_BRIDGE_CLASSIFICATION = "local_orderflow_confirmation_context"
BOOKMAP_LOCAL_BRIDGE_RUNTIME_ARTIFACT = "bookmap_local_bridge_context.json"
BOOKMAP_LOCAL_BRIDGE_HISTORY_ARTIFACT = "bookmap_local_bridge_context_history.jsonl"
BOOKMAP_LOCAL_BRIDGE_BOUNDARY = (
    "Bookmap local bridge is read-only supplemental order-flow context. It can "
    "observe local order book, liquidity, absorption, imbalance, range, support, "
    "resistance, and watchlist context, but it cannot create source quorum, "
    "trade candidates, paper orders, broker writes, fills, receipts, "
    "reconciliation truth, quantum jobs, or live capital."
)

DEFAULT_ORDERFLOW_CONTEXT_RECORDS: tuple[dict[str, Any], ...] = (
    {
        "symbol": "CL",
        "instrument_name": "Crude oil futures order-flow context",
        "venue": "local_bookmap",
        "timeframe": "intraday",
        "bridge_channel": "heatmap_snapshot",
        "setup_type": "absorption_range_watch",
        "direction": "watch_breakout_or_reversal",
        "orderflow_score": 0.68,
        "liquidity_state": "resting_liquidity_near_range_edges",
        "absorption_state": "possible_absorption_needs_catalyst_confirmation",
        "imbalance_state": "mixed",
        "support_resistance": {
            "support": "local liquidity shelf below current range",
            "resistance": "local offer wall near prior impulse high",
        },
        "candidate_watchlist_context": "Crude order-flow can refine entry timing only after Qadam has catalyst and risk approval.",
        "obvious_orderflow_context_flag": False,
    },
    {
        "symbol": "SLV",
        "instrument_name": "Silver ETF order-flow proxy context",
        "venue": "local_bookmap",
        "timeframe": "intraday",
        "bridge_channel": "volume_delta_snapshot",
        "setup_type": "liquidity_sweep_watch",
        "direction": "watch_long_if_confirmed",
        "orderflow_score": 0.61,
        "liquidity_state": "thin_liquidity_after_sweep",
        "absorption_state": "unconfirmed",
        "imbalance_state": "buyer_delta_needs_follow_through",
        "support_resistance": {
            "support": "recent sweep low",
            "resistance": "prior day value high",
        },
        "candidate_watchlist_context": "Silver order-flow is supplemental; macro and price context still govern.",
        "obvious_orderflow_context_flag": False,
    },
    {
        "symbol": "SMH",
        "instrument_name": "Semiconductor ETF order-flow proxy context",
        "venue": "local_bookmap",
        "timeframe": "intraday",
        "bridge_channel": "depth_and_imbalance_snapshot",
        "setup_type": "relative_strength_liquidity_watch",
        "direction": "watch_relative_strength",
        "orderflow_score": 0.58,
        "liquidity_state": "normal_depth_with_event_risk",
        "absorption_state": "no_clear_absorption",
        "imbalance_state": "balanced",
        "support_resistance": {
            "support": "VWAP area",
            "resistance": "recent high liquidity pocket",
        },
        "candidate_watchlist_context": "Semiconductor order-flow needs earnings, export-control, or supply-chain evidence.",
        "obvious_orderflow_context_flag": False,
    },
)


@dataclass(frozen=True)
class BookmapBridgeUrlStatus:
    configured: bool
    local_only: bool
    scheme: str
    host_class: str
    sanitized_endpoint: str | None
    degraded_reason: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_path(settings: Settings) -> Path:
    return Path(settings.runtime_dir) / BOOKMAP_LOCAL_BRIDGE_RUNTIME_ARTIFACT


def _history_path(settings: Settings) -> Path:
    return Path(settings.runtime_dir) / BOOKMAP_LOCAL_BRIDGE_HISTORY_ARTIFACT


def _safe_symbol(value: Any) -> str:
    return str(value or "UNKNOWN").strip().upper()[:40]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _settings_enabled(settings: Settings) -> bool:
    return bool(getattr(settings, "bookmap_local_bridge_enabled", True))


def _live_probe_enabled(settings: Settings) -> bool:
    return bool(getattr(settings, "bookmap_local_bridge_live_probe_enabled", False))


def _timeout_seconds(settings: Settings) -> float:
    return max(0.5, min(float(getattr(settings, "bookmap_local_bridge_timeout_seconds", 3)), 10.0))


def _bridge_url(settings: Settings) -> str:
    return str(secret_value("BOOKMAP_BRIDGE_URL", settings) or "").strip()


def _is_loopback_host(host: str | None) -> bool:
    normalized = (host or "").strip().lower().strip("[]")
    return normalized in {"localhost", "127.0.0.1", "::1"} or normalized.startswith("127.")


def _sanitize_endpoint(url: str) -> str | None:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return None
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", "", "", ""))


def bookmap_bridge_url_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    url = _bridge_url(settings)
    if not url:
        return BookmapBridgeUrlStatus(
            configured=False,
            local_only=False,
            scheme="missing",
            host_class="missing",
            sanitized_endpoint=None,
            degraded_reason="local_bridge_url_missing",
        ).to_dict()
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    local = _is_loopback_host(parsed.hostname)
    if scheme not in {"http", "https", "ws", "wss"}:
        degraded_reason = "unsupported_bridge_scheme"
    elif not local:
        degraded_reason = "nonlocal_bridge_url_blocked"
    else:
        degraded_reason = None
    return BookmapBridgeUrlStatus(
        configured=True,
        local_only=local,
        scheme=scheme or "missing",
        host_class="local_loopback" if local else "blocked_nonlocal",
        sanitized_endpoint=_sanitize_endpoint(url),
        degraded_reason=degraded_reason,
    ).to_dict()


def _record_summary(record: dict[str, Any]) -> str:
    symbol = _safe_symbol(record.get("symbol"))
    setup = str(record.get("setup_type") or "orderflow_context")[:80]
    direction = str(record.get("direction") or "watch")[:80]
    score = _safe_float(record.get("orderflow_score"))
    liquidity = str(record.get("liquidity_state") or "unknown_liquidity")[:80]
    return (
        f"Bookmap local order-flow context for {symbol}: {setup}, "
        f"direction={direction}, score={score:.2f}, liquidity={liquidity}."
    )


def _safe_mapping(value: Any, *, limit: int = 8) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key)[:80]: str(item)[:160] for key, item in list(value.items())[:limit]}


def _safe_record(record: dict[str, Any], *, sample: bool) -> dict[str, Any]:
    return {
        "symbol": _safe_symbol(record.get("symbol")),
        "instrument_name": str(record.get("instrument_name") or record.get("symbol") or "unknown")[:120],
        "venue": str(record.get("venue") or "local_bookmap")[:80],
        "timeframe": str(record.get("timeframe") or "intraday")[:40],
        "bridge_channel": str(record.get("bridge_channel") or record.get("channel") or "snapshot")[:80],
        "setup_type": str(record.get("setup_type") or "orderflow_context")[:100],
        "direction": str(record.get("direction") or "watch")[:80],
        "orderflow_score": round(max(0.0, min(1.0, _safe_float(record.get("orderflow_score")))), 3),
        "liquidity_state": str(record.get("liquidity_state") or "unknown")[:120],
        "absorption_state": str(record.get("absorption_state") or "unknown")[:120],
        "imbalance_state": str(record.get("imbalance_state") or "unknown")[:120],
        "support_resistance": _safe_mapping(record.get("support_resistance")),
        "candidate_watchlist_context": str(
            record.get("candidate_watchlist_context") or "Bookmap order-flow context only."
        )[:260],
        "obvious_orderflow_context_flag": bool(record.get("obvious_orderflow_context_flag")),
        "trade_candidate_created": False,
        "paper_order_allowed": False,
        "execution_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
        "bookmap_order_injection_allowed": False,
        "bookmap_trading_mode_allowed": False,
        "sample": sample,
        "observed_at": str(record.get("observed_at") or _now()),
        "boundary": BOOKMAP_LOCAL_BRIDGE_BOUNDARY,
    }


def _records_from_payload(payload: Any, *, sample: bool) -> tuple[dict[str, Any], ...]:
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = []
        for key in ("records", "events", "orderflow", "contexts", "snapshots", "bookmap_context"):
            value = payload.get(key)
            if isinstance(value, list):
                rows = value
                break
        if not rows and any(key in payload for key in ("symbol", "instrument_name", "orderflow_score")):
            rows = [payload]
    else:
        rows = []
    return tuple(_safe_record(row, sample=sample) for row in rows[:25] if isinstance(row, dict))


def _http_snapshot(url: str, settings: Settings) -> dict[str, Any]:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.setdefault("mode", "readonly")
    query.setdefault("source", "qadam")
    request_url = urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path or "/", "", urlencode(query), "")
    )
    request = Request(
        request_url,
        headers={
            "Accept": "application/json",
            "User-Agent": "Qadam/0.1 read-only Bookmap local bridge",
            "X-Qadam-Bridge-Mode": "read-only",
        },
        method="GET",
    )
    with urlopen(request, timeout=_timeout_seconds(settings)) as response:  # noqa: S310 - guarded loopback only.
        body = response.read(1_000_000)
    return json.loads(body.decode("utf-8"))


async def _websocket_snapshot(url: str, settings: Settings) -> dict[str, Any]:
    try:
        import websockets
    except ImportError as exc:
        raise RuntimeError("missing_dependency:websockets") from exc
    request = {
        "schema_version": BOOKMAP_LOCAL_BRIDGE_SCHEMA_VERSION,
        "request_type": "snapshot_readonly",
        "source": "qadam",
        "max_records": 25,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
    }
    async with websockets.connect(url, open_timeout=_timeout_seconds(settings)) as websocket:
        await websocket.send(json.dumps(request, sort_keys=True))
        raw = await asyncio.wait_for(websocket.recv(), timeout=_timeout_seconds(settings))
    return json.loads(str(raw))


async def _live_payload_async(settings: Settings) -> tuple[dict[str, Any], bool, str | None]:
    url_status = bookmap_bridge_url_status(settings)
    base = {
        "schema_version": BOOKMAP_LOCAL_BRIDGE_SCHEMA_VERSION,
        "sample": False,
        "provider": BOOKMAP_LOCAL_BRIDGE_PROVIDER_LABEL,
        "source": BOOKMAP_LOCAL_BRIDGE_SOURCE_LABEL,
        "source_key": BOOKMAP_LOCAL_BRIDGE_SOURCE_KEY,
        "classification": BOOKMAP_LOCAL_BRIDGE_CLASSIFICATION,
        "records": [],
        "enabled": _settings_enabled(settings),
        "live_probe_enabled": _live_probe_enabled(settings),
        "bridge_url_status": url_status,
        "canonical_source_count": EXPECTED_SOURCE_COUNT,
        "boundary": BOOKMAP_LOCAL_BRIDGE_BOUNDARY,
    }
    if not _settings_enabled(settings):
        base["boundary"] = "BOOKMAP_LOCAL_BRIDGE_ENABLED is false; Bookmap reads are disabled."
        return base, True, "disabled:BOOKMAP_LOCAL_BRIDGE_ENABLED_false"
    if not url_status.get("configured"):
        base["boundary"] = "Bookmap local bridge URL is not configured."
        return base, True, "local_bridge_url_missing"
    if url_status.get("degraded_reason"):
        base["boundary"] = "Bookmap local bridge URL must point to localhost/loopback only."
        return base, True, str(url_status["degraded_reason"])
    if not _live_probe_enabled(settings):
        base["boundary"] = "Bookmap local bridge is configured but live probing is disabled by policy."
        return base, True, "disabled:BOOKMAP_LOCAL_BRIDGE_LIVE_PROBE_ENABLED_false"

    url = _bridge_url(settings)
    try:
        if str(url_status.get("scheme")) in {"http", "https"}:
            provider_payload = _http_snapshot(url, settings)
        else:
            provider_payload = await _websocket_snapshot(url, settings)
    except RuntimeError as exc:
        base["_qadam_error_type"] = str(exc)
        return base, True, str(exc)
    except (HTTPError, URLError, OSError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
        base["_qadam_error_type"] = exc.__class__.__name__
        base["_qadam_error"] = repr(exc)[:500]
        return base, True, f"local_bridge_probe_error:{exc.__class__.__name__}"

    records = _records_from_payload(provider_payload, sample=False)
    base["records"] = list(records)
    base["provider_payload_shape"] = (
        sorted(provider_payload.keys())[:12] if isinstance(provider_payload, dict) else "list"
    )
    degraded = not bool(records)
    return base, degraded, None if records else "no_orderflow_context_records"


class BookmapLocalBridgeAdapter:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        archive: RawPayloadArchive | None = None,
        event_log: EventLog | None = None,
    ) -> None:
        self.settings = settings or Settings.from_env()
        self.archive = archive or RawPayloadArchive(self.settings)
        self.event_log = event_log or EventLog(echo=False)

    def sample_payload(self) -> dict[str, Any]:
        return {
            "schema_version": BOOKMAP_LOCAL_BRIDGE_SCHEMA_VERSION,
            "sample": True,
            "provider": BOOKMAP_LOCAL_BRIDGE_PROVIDER_LABEL,
            "source": BOOKMAP_LOCAL_BRIDGE_SOURCE_LABEL,
            "source_key": BOOKMAP_LOCAL_BRIDGE_SOURCE_KEY,
            "classification": BOOKMAP_LOCAL_BRIDGE_CLASSIFICATION,
            "records": [_safe_record(record, sample=True) for record in DEFAULT_ORDERFLOW_CONTEXT_RECORDS],
            "canonical_source_count": EXPECTED_SOURCE_COUNT,
            "boundary": BOOKMAP_LOCAL_BRIDGE_BOUNDARY,
        }

    def normalize_payload(self, payload: dict[str, Any]) -> tuple[UnifiedEvent, ...]:
        records = _records_from_payload(payload.get("records", []), sample=bool(payload.get("sample")))
        events: list[UnifiedEvent] = []
        for record in records:
            summary = _record_summary(record)
            events.append(
                UnifiedEvent(
                    schema_version=UNIFIED_EVENT_SCHEMA_VERSION,
                    event_id=str(uuid4()),
                    source=BOOKMAP_LOCAL_BRIDGE_SOURCE_LABEL,
                    trust_score_at_ingestion=BOOKMAP_LOCAL_BRIDGE_TRUST_SCORE,
                    event_type=BOOKMAP_LOCAL_BRIDGE_EVENT_TYPE,
                    raw_payload={
                        "symbol": record["symbol"],
                        "instrument_name": record["instrument_name"],
                        "venue": record["venue"],
                        "timeframe": record["timeframe"],
                        "bridge_channel": record["bridge_channel"],
                        "setup_type": record["setup_type"],
                        "direction": record["direction"],
                        "orderflow_score": record["orderflow_score"],
                        "liquidity_state": record["liquidity_state"],
                        "absorption_state": record["absorption_state"],
                        "imbalance_state": record["imbalance_state"],
                        "support_resistance": record["support_resistance"],
                        "candidate_watchlist_context": record["candidate_watchlist_context"],
                        "obvious_orderflow_context_flag": record["obvious_orderflow_context_flag"],
                        "trade_candidate_created": False,
                        "paper_order_allowed": False,
                        "execution_allowed": False,
                        "broker_write_allowed": False,
                    },
                    normalised_summary=summary[:240],
                    coordinates=None,
                    ingested_at=str(record.get("observed_at") or _now()),
                    linked_catalyst_id=None,
                )
            )
        return tuple(events)

    def envelope_from_payload(
        self,
        payload: dict[str, Any],
        *,
        degraded: bool = False,
        degraded_reason: str | None = None,
        persist_context: bool = True,
    ) -> SourceEnvelope:
        archive_path = self.archive.write(BOOKMAP_LOCAL_BRIDGE_SOURCE_KEY, payload)
        events = self.normalize_payload(payload)
        envelope = SourceEnvelope(
            events=events,
            source=BOOKMAP_LOCAL_BRIDGE_SOURCE_LABEL,
            trust_score=BOOKMAP_LOCAL_BRIDGE_TRUST_SCORE,
            fetched_at=_now(),
            degraded=degraded,
            degraded_reason=degraded_reason,
            raw_archive_path=str(archive_path),
        )
        if persist_context:
            write_bookmap_local_bridge_context(
                envelope.to_dict(),
                self.settings,
                sample=bool(payload.get("sample")),
            )
        self.event_log.write(
            "source_adapter_fetch_completed",
            "bookmap_local_bridge",
            {
                "source": BOOKMAP_LOCAL_BRIDGE_SOURCE_LABEL,
                "classification": BOOKMAP_LOCAL_BRIDGE_CLASSIFICATION,
                "event_count": len(events),
                "degraded": degraded,
                "degraded_reason": degraded_reason,
                "execution_allowed": False,
                "paper_order_allowed": False,
                "trade_candidate_created": False,
                "broker_write_allowed": False,
                "bookmap_order_injection_allowed": False,
                "bookmap_trading_mode_allowed": False,
                "canonical_source_count": EXPECTED_SOURCE_COUNT,
            },
        )
        return envelope

    def fetch_sample(self) -> SourceEnvelope:
        return self.envelope_from_payload(self.sample_payload())

    async def fetch_live_async(self) -> SourceEnvelope:
        payload, degraded, degraded_reason = await _live_payload_async(self.settings)
        return self.envelope_from_payload(
            payload,
            degraded=degraded,
            degraded_reason=degraded_reason,
        )

    def fetch_live(self) -> SourceEnvelope:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.fetch_live_async())
        return self.envelope_from_payload(
            {
                "schema_version": BOOKMAP_LOCAL_BRIDGE_SCHEMA_VERSION,
                "sample": False,
                "provider": BOOKMAP_LOCAL_BRIDGE_PROVIDER_LABEL,
                "source": BOOKMAP_LOCAL_BRIDGE_SOURCE_LABEL,
                "source_key": BOOKMAP_LOCAL_BRIDGE_SOURCE_KEY,
                "classification": BOOKMAP_LOCAL_BRIDGE_CLASSIFICATION,
                "records": [],
                "enabled": _settings_enabled(self.settings),
                "live_probe_enabled": _live_probe_enabled(self.settings),
                "bridge_url_status": bookmap_bridge_url_status(self.settings),
                "boundary": "Bookmap live probe must use the async adapter path inside an existing event loop.",
            },
            degraded=True,
            degraded_reason="local_bridge_async_fetch_required",
        )


def _safe_context_from_event(event: dict[str, Any]) -> dict[str, Any]:
    raw = event.get("raw_payload") if isinstance(event.get("raw_payload"), dict) else {}
    return {
        "event_id": str(event.get("event_id") or "")[:160],
        "symbol": _safe_symbol(raw.get("symbol")),
        "instrument_name": str(raw.get("instrument_name") or raw.get("symbol") or "unknown")[:120],
        "venue": str(raw.get("venue") or "local_bookmap")[:80],
        "timeframe": str(raw.get("timeframe") or "intraday")[:40],
        "bridge_channel": str(raw.get("bridge_channel") or "snapshot")[:80],
        "setup_type": str(raw.get("setup_type") or "orderflow_context")[:100],
        "direction": str(raw.get("direction") or "watch")[:80],
        "orderflow_score": round(_safe_float(raw.get("orderflow_score")), 3),
        "liquidity_state": str(raw.get("liquidity_state") or "unknown")[:120],
        "absorption_state": str(raw.get("absorption_state") or "unknown")[:120],
        "imbalance_state": str(raw.get("imbalance_state") or "unknown")[:120],
        "support_resistance": raw.get("support_resistance") if isinstance(raw.get("support_resistance"), dict) else {},
        "candidate_watchlist_context": str(raw.get("candidate_watchlist_context") or "")[:260],
        "obvious_orderflow_context_flag": bool(raw.get("obvious_orderflow_context_flag")),
        "normalised_summary": str(event.get("normalised_summary") or "")[:240],
        "observed_at": str(event.get("ingested_at") or _now()),
        "trade_candidate_created": False,
        "paper_order_allowed": False,
        "execution_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
        "bookmap_order_injection_allowed": False,
        "bookmap_trading_mode_allowed": False,
        "boundary": BOOKMAP_LOCAL_BRIDGE_BOUNDARY,
    }


def write_bookmap_local_bridge_context(
    envelope: dict[str, Any],
    settings: Settings | None = None,
    *,
    sample: bool,
) -> Path:
    settings = settings or Settings.from_env()
    events = envelope.get("events", [])
    if not isinstance(events, list):
        events = []
    context = {
        "schema_version": BOOKMAP_LOCAL_BRIDGE_SCHEMA_VERSION,
        "status": "orderflow_context_recorded" if events else "no_orderflow_context",
        "source": BOOKMAP_LOCAL_BRIDGE_SOURCE_LABEL,
        "source_key": BOOKMAP_LOCAL_BRIDGE_SOURCE_KEY,
        "classification": BOOKMAP_LOCAL_BRIDGE_CLASSIFICATION,
        "provider": BOOKMAP_LOCAL_BRIDGE_PROVIDER_LABEL,
        "event_count": len(events),
        "sample": sample,
        "orderflow_contexts": [
            _safe_context_from_event(event)
            for event in events
            if isinstance(event, dict)
        ],
        "source_quorum_credit_allowed": False,
        "trade_candidate_creation_allowed": False,
        "risk_handoff_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "bookmap_order_injection_allowed": False,
        "bookmap_trading_mode_allowed": False,
        "live_capital_enabled": False,
        "written_at": _now(),
        "boundary": BOOKMAP_LOCAL_BRIDGE_BOUNDARY,
    }
    path = _runtime_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(context, indent=2, sort_keys=True), encoding="utf-8")
    with _history_path(settings).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(context, sort_keys=True) + "\n")
    return path


def bookmap_local_bridge_context(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    path = _runtime_path(settings)
    if not path.exists():
        return {
            "schema_version": BOOKMAP_LOCAL_BRIDGE_SCHEMA_VERSION,
            "status": "not_initialized",
            "source": BOOKMAP_LOCAL_BRIDGE_SOURCE_LABEL,
            "source_key": BOOKMAP_LOCAL_BRIDGE_SOURCE_KEY,
            "classification": BOOKMAP_LOCAL_BRIDGE_CLASSIFICATION,
            "provider": BOOKMAP_LOCAL_BRIDGE_PROVIDER_LABEL,
            "event_count": 0,
            "sample": False,
            "orderflow_contexts": [],
            "source_quorum_credit_allowed": False,
            "trade_candidate_creation_allowed": False,
            "risk_handoff_allowed": False,
            "execution_allowed": False,
            "paper_order_allowed": False,
            "broker_write_allowed": False,
            "bookmap_order_injection_allowed": False,
            "bookmap_trading_mode_allowed": False,
            "live_capital_enabled": False,
            "boundary": BOOKMAP_LOCAL_BRIDGE_BOUNDARY,
        }
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "schema_version": BOOKMAP_LOCAL_BRIDGE_SCHEMA_VERSION,
            "status": "degraded",
            "source": BOOKMAP_LOCAL_BRIDGE_SOURCE_LABEL,
            "source_key": BOOKMAP_LOCAL_BRIDGE_SOURCE_KEY,
            "classification": BOOKMAP_LOCAL_BRIDGE_CLASSIFICATION,
            "provider": BOOKMAP_LOCAL_BRIDGE_PROVIDER_LABEL,
            "event_count": 0,
            "sample": False,
            "orderflow_contexts": [],
            "source_quorum_credit_allowed": False,
            "trade_candidate_creation_allowed": False,
            "risk_handoff_allowed": False,
            "execution_allowed": False,
            "paper_order_allowed": False,
            "broker_write_allowed": False,
            "bookmap_order_injection_allowed": False,
            "bookmap_trading_mode_allowed": False,
            "live_capital_enabled": False,
            "boundary": "Bookmap local bridge context artifact could not be read safely.",
        }
    return loaded if isinstance(loaded, dict) else {}


def bookmap_local_bridge_packet_context(settings: Settings | None = None) -> dict[str, Any]:
    context = bookmap_local_bridge_context(settings)
    contexts = context.get("orderflow_contexts", [])
    if not isinstance(contexts, list):
        contexts = []
    challenge_rows = [
        (
            f"Verify {row.get('symbol', 'instrument')} order-flow context with canonical catalyst, "
            "market price confirmation, signal integrity, risk, and Q-CTRL paper consultation before any paper order."
        )
        for row in contexts[:4]
        if isinstance(row, dict)
    ]
    return {
        "source_key": BOOKMAP_LOCAL_BRIDGE_SOURCE_KEY,
        "status": str(context.get("status") or "not_initialized")[:80],
        "context_role": "read_only_supplemental_orderflow_confirmation",
        "orderflow_context_count": len(contexts),
        "orderflow_context_refs": [
            {
                "symbol": str(row.get("symbol") or "unknown")[:40],
                "setup_type": str(row.get("setup_type") or "orderflow_context")[:100],
                "orderflow_score": row.get("orderflow_score"),
                "obvious_orderflow_context_flag": bool(row.get("obvious_orderflow_context_flag")),
            }
            for row in contexts[:6]
            if isinstance(row, dict)
        ],
        "active_required_challenges": challenge_rows[:6],
        "source_quorum_credit_allowed": False,
        "trade_candidate_creation_allowed": False,
        "risk_handoff_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "bookmap_order_injection_allowed": False,
        "bookmap_trading_mode_allowed": False,
        "live_capital_enabled": False,
        "boundary": BOOKMAP_LOCAL_BRIDGE_BOUNDARY,
    }


def bookmap_local_bridge_evidence_items(envelope: dict[str, Any]) -> tuple[EvidenceItem, ...]:
    events = envelope.get("events", [])
    if not isinstance(events, list):
        return ()
    items: list[EvidenceItem] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        items.append(
            EvidenceItem(
                evidence_id=f"bookmap:{event.get('event_id', 'unknown')}",
                source=BOOKMAP_LOCAL_BRIDGE_SOURCE_LABEL,
                event_type=BOOKMAP_LOCAL_BRIDGE_EVENT_TYPE,
                summary=str(event.get("normalised_summary") or "Bookmap local order-flow context.")[:600],
                trust_score=BOOKMAP_LOCAL_BRIDGE_TRUST_SCORE,
                observed_at=str(event.get("ingested_at") or _now()),
                raw_ref=None,
            )
        )
    return tuple(items)


def bookmap_local_bridge_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    context = bookmap_local_bridge_context(settings)
    url_status = bookmap_bridge_url_status(settings)
    orderflow_contexts = context.get("orderflow_contexts", [])
    if not isinstance(orderflow_contexts, list):
        orderflow_contexts = []
    context_count = int(context.get("event_count", 0) or 0)
    live_context_recorded = context.get("status") == "orderflow_context_recorded" and context.get("sample") is False
    sample_context_recorded = context.get("status") == "orderflow_context_recorded" and context.get("sample") is True
    if not _settings_enabled(settings):
        public_status = "disabled"
        runtime_status = "intentionally_disabled"
        degraded_reason = "disabled:BOOKMAP_LOCAL_BRIDGE_ENABLED_false"
    elif url_status.get("degraded_reason") == "nonlocal_bridge_url_blocked":
        public_status = "degraded"
        runtime_status = "degraded"
        degraded_reason = "nonlocal_bridge_url_blocked"
    elif live_context_recorded:
        public_status = "connected"
        runtime_status = "local_bridge_connected"
        degraded_reason = None
    elif sample_context_recorded:
        public_status = "sample_ready"
        runtime_status = "local_bridge_sample_ready"
        degraded_reason = None
    elif url_status.get("configured") and url_status.get("local_only"):
        public_status = "configured_pending_probe"
        runtime_status = "local_bridge_configured_pending_probe"
        degraded_reason = (
            None
            if _live_probe_enabled(settings)
            else "disabled:BOOKMAP_LOCAL_BRIDGE_LIVE_PROBE_ENABLED_false"
        )
    else:
        public_status = "local_bridge_required"
        runtime_status = "local_bridge_required"
        degraded_reason = "local_bridge_url_missing"
    return {
        "schema_version": BOOKMAP_LOCAL_BRIDGE_SCHEMA_VERSION,
        "status": public_status,
        "runtime_status": runtime_status,
        "source": BOOKMAP_LOCAL_BRIDGE_SOURCE_LABEL,
        "source_key": BOOKMAP_LOCAL_BRIDGE_SOURCE_KEY,
        "provider": BOOKMAP_LOCAL_BRIDGE_PROVIDER_LABEL,
        "classification": BOOKMAP_LOCAL_BRIDGE_CLASSIFICATION,
        "enabled": _settings_enabled(settings),
        "connected": live_context_recorded,
        "bridge_url_configured": bool(url_status.get("configured")),
        "bridge_url_local": bool(url_status.get("local_only")),
        "bridge_scheme": url_status.get("scheme"),
        "bridge_host_class": url_status.get("host_class"),
        "sanitized_endpoint": url_status.get("sanitized_endpoint"),
        "live_probe_enabled": _live_probe_enabled(settings),
        "sample_mode_available": True,
        "orderflow_context_status": context.get("status", "not_initialized"),
        "orderflow_context_count": context_count,
        "obvious_orderflow_context_count": sum(
            1
            for row in orderflow_contexts
            if isinstance(row, dict) and row.get("obvious_orderflow_context_flag") is True
        ),
        "degraded_reason": degraded_reason,
        "canonical_source": False,
        "canonical_source_count": EXPECTED_SOURCE_COUNT,
        "source_quorum_credit_allowed": False,
        "orderflow_confirmation_role": "supplemental_orderflow_confirmation_only",
        "signal_authority": False,
        "risk_approval_authority": False,
        "trade_candidate_creation_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "fill_confirmation_authority": False,
        "receipt_evidence_authority": False,
        "reconciliation_truth_authority": False,
        "quantum_job_authority": False,
        "bookmap_order_injection_allowed": False,
        "bookmap_trading_mode_allowed": False,
        "live_capital_enabled": False,
        "raw_payload_exposed": False,
        "local_path_exposed": False,
        "public_safe": True,
        "boundary": BOOKMAP_LOCAL_BRIDGE_BOUNDARY,
    }


def fetch_bookmap_local_bridge_sample() -> dict[str, Any]:
    return BookmapLocalBridgeAdapter().fetch_sample().to_dict()


def fetch_bookmap_local_bridge_live() -> dict[str, Any]:
    return BookmapLocalBridgeAdapter().fetch_live().to_dict()


async def fetch_bookmap_local_bridge_live_async() -> dict[str, Any]:
    return (await BookmapLocalBridgeAdapter().fetch_live_async()).to_dict()


async def fetch_bookmap_local_bridge_live_envelope_async(
    *,
    settings: Settings | None = None,
    archive: RawPayloadArchive | None = None,
    event_log: EventLog | None = None,
) -> SourceEnvelope:
    return await BookmapLocalBridgeAdapter(
        settings=settings,
        archive=archive,
        event_log=event_log,
    ).fetch_live_async()
