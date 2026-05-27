"""Read-only TradingView MCP technical-analysis adapter.

TradingView MCP is supplemental market/technical context for Qadam. It can
observe and analyse; it cannot create source quorum, trade candidates, orders,
broker writes, fills, receipts, reconciliation truth, quantum jobs, or live
capital authority.
"""

from __future__ import annotations

import importlib
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
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
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT

TRADINGVIEW_MCP_SCHEMA_VERSION = 1
TRADINGVIEW_MCP_SOURCE_KEY = "tradingview_mcp"
TRADINGVIEW_MCP_SOURCE_LABEL = "market.tradingview_mcp"
TRADINGVIEW_MCP_PROVIDER_LABEL = "local_tradingview_mcp_server"
TRADINGVIEW_MCP_EVENT_TYPE = "technical_analysis_context"
TRADINGVIEW_MCP_TRUST_SCORE = 0.57
TRADINGVIEW_MCP_CLASSIFICATION = "supplemental_technical_analysis_context"
TRADINGVIEW_MCP_RUNTIME_ARTIFACT = "tradingview_mcp_technical_context.json"
TRADINGVIEW_MCP_HISTORY_ARTIFACT = "tradingview_mcp_technical_context_history.jsonl"
TRADINGVIEW_MCP_BOUNDARY = (
    "TradingView MCP is read-only supplemental technical analysis. It can observe "
    "market structure, indicator state, volatility, support/resistance, and watchlist "
    "context, but it cannot create source quorum, trade candidates, paper orders, "
    "broker writes, fills, receipts, reconciliation truth, quantum jobs, or live capital."
)

DEFAULT_TECHNICAL_CONTEXT_RECORDS: tuple[dict[str, Any], ...] = (
    {
        "symbol": "TVC:USOIL",
        "instrument_name": "WTI crude oil technical context",
        "timeframe": "1D",
        "tool_name": "bollinger_scan",
        "setup_type": "volatility_compression_watch",
        "direction": "watch_long_volatility",
        "technical_score": 0.72,
        "volatility_state": "compressed_range",
        "indicator_state": {
            "bollinger_width": "compressed",
            "trend": "range_bound",
            "volume": "needs_confirmation",
            "rsi": "neutral_recovering",
        },
        "support_resistance": {
            "support": "prior weekly demand zone",
            "resistance": "prior disruption spike high",
        },
        "candidate_watchlist_context": "Crude is worth monitoring when geopolitics creates a confirmed catalyst.",
        "obvious_technical_context_flag": True,
    },
    {
        "symbol": "SLV",
        "instrument_name": "Silver ETF technical context",
        "timeframe": "1D",
        "tool_name": "volume_breakout_scanner",
        "setup_type": "volume_expansion_watch",
        "direction": "watch_long_momentum",
        "technical_score": 0.66,
        "volatility_state": "expanding_from_base",
        "indicator_state": {
            "relative_volume": "above_recent_average",
            "trend": "constructive",
            "rsi": "not_overbought",
        },
        "support_resistance": {
            "support": "recent breakout shelf",
            "resistance": "prior swing high",
        },
        "candidate_watchlist_context": "Silver can support a thesis only after macro and flow corroboration.",
        "obvious_technical_context_flag": False,
    },
    {
        "symbol": "SMH",
        "instrument_name": "Semiconductor ETF technical context",
        "timeframe": "1D",
        "tool_name": "multi_timeframe_analysis",
        "setup_type": "trend_confirmation_watch",
        "direction": "watch_relative_strength",
        "technical_score": 0.63,
        "volatility_state": "trend_with_event_risk",
        "indicator_state": {
            "multi_timeframe_trend": "mixed_positive",
            "volume": "normal",
            "momentum": "positive_but_extended",
        },
        "support_resistance": {
            "support": "20 day moving average area",
            "resistance": "recent high",
        },
        "candidate_watchlist_context": "Semiconductor context needs export-control or earnings evidence.",
        "obvious_technical_context_flag": False,
    },
)


@dataclass(frozen=True)
class TradingViewMCPDependencyStatus:
    local_checkout_exists: bool
    mcp_config_exists: bool
    package_importable: bool
    service_importable: bool
    missing_dependency: str | None
    error: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _local_checkout() -> Path:
    return _repo_root() / "tradingview-mcp-main"


def _local_src() -> Path:
    return _local_checkout() / "src"


def _runtime_path(settings: Settings) -> Path:
    return Path(settings.runtime_dir) / TRADINGVIEW_MCP_RUNTIME_ARTIFACT


def _history_path(settings: Settings) -> Path:
    return Path(settings.runtime_dir) / TRADINGVIEW_MCP_HISTORY_ARTIFACT


def _safe_symbol(value: Any) -> str:
    return str(value or "UNKNOWN").strip()[:40]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _ensure_local_src_on_path() -> None:
    src = _local_src()
    if src.exists() and str(src) not in sys.path:
        sys.path.insert(0, str(src))


def tradingview_mcp_dependency_status() -> TradingViewMCPDependencyStatus:
    checkout = _local_checkout()
    config = checkout / ".codex-mcp.json"
    package_importable = False
    service_importable = False
    missing_dependency: str | None = None
    error: str | None = None
    try:
        _ensure_local_src_on_path()
        importlib.import_module("tradingview_mcp")
        package_importable = True
        importlib.import_module("tradingview_mcp.core.services.screener_service")
        importlib.import_module("tradingview_mcp.core.services.scanner_service")
        service_importable = True
    except ImportError as exc:
        missing_dependency = getattr(exc, "name", None)
        error = str(exc)
    except Exception as exc:  # noqa: BLE001 - public status should degrade safely
        error = f"{exc.__class__.__name__}: {exc}"

    return TradingViewMCPDependencyStatus(
        local_checkout_exists=checkout.exists(),
        mcp_config_exists=config.exists(),
        package_importable=package_importable,
        service_importable=service_importable,
        missing_dependency=missing_dependency,
        error=error,
    )


def _settings_enabled(settings: Settings) -> bool:
    return bool(getattr(settings, "tradingview_mcp_enabled", True))


def _live_calls_enabled(settings: Settings) -> bool:
    return bool(getattr(settings, "tradingview_mcp_live_calls_enabled", False))


def _symbols(settings: Settings) -> tuple[str, ...]:
    configured = getattr(settings, "tradingview_mcp_symbol_allowlist", ())
    if configured:
        return tuple(str(symbol).strip().upper() for symbol in configured if str(symbol).strip())
    return ("USO", "SLV", "SMH")


def _record_summary(record: dict[str, Any]) -> str:
    symbol = _safe_symbol(record.get("symbol"))
    setup = str(record.get("setup_type") or "technical_context")[:80]
    direction = str(record.get("direction") or "watch")[:80]
    score = _safe_float(record.get("technical_score"))
    volatility = str(record.get("volatility_state") or "unknown_volatility")[:80]
    return (
        f"TradingView MCP technical context for {symbol}: {setup}, "
        f"direction={direction}, score={score:.2f}, volatility={volatility}."
    )


def _safe_record(record: dict[str, Any], *, sample: bool) -> dict[str, Any]:
    indicator_state = record.get("indicator_state")
    if not isinstance(indicator_state, dict):
        indicator_state = {}
    support_resistance = record.get("support_resistance")
    if not isinstance(support_resistance, dict):
        support_resistance = {}
    return {
        "symbol": _safe_symbol(record.get("symbol")),
        "instrument_name": str(record.get("instrument_name") or record.get("symbol") or "unknown")[:120],
        "timeframe": str(record.get("timeframe") or "1D")[:20],
        "tool_name": str(record.get("tool_name") or "technical_context")[:80],
        "setup_type": str(record.get("setup_type") or "technical_context")[:100],
        "direction": str(record.get("direction") or "watch")[:80],
        "technical_score": round(max(0.0, min(1.0, _safe_float(record.get("technical_score")))), 3),
        "volatility_state": str(record.get("volatility_state") or "unknown")[:120],
        "indicator_state": {
            str(key)[:80]: str(value)[:160]
            for key, value in list(indicator_state.items())[:12]
        },
        "support_resistance": {
            str(key)[:80]: str(value)[:160]
            for key, value in list(support_resistance.items())[:8]
        },
        "candidate_watchlist_context": str(
            record.get("candidate_watchlist_context") or "Technical context only."
        )[:260],
        "obvious_technical_context_flag": bool(record.get("obvious_technical_context_flag")),
        "trade_candidate_created": False,
        "paper_order_allowed": False,
        "execution_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
        "sample": sample,
        "observed_at": str(record.get("observed_at") or _now()),
        "boundary": TRADINGVIEW_MCP_BOUNDARY,
    }


def _live_records(settings: Settings) -> tuple[dict[str, Any], ...]:
    if not _live_calls_enabled(settings):
        return ()
    _ensure_local_src_on_path()
    screener = importlib.import_module("tradingview_mcp.core.services.screener_service")
    scanner = importlib.import_module("tradingview_mcp.core.services.scanner_service")
    records: list[dict[str, Any]] = []
    try:
        for row in screener.fetch_bollinger_analysis(
            "NASDAQ",
            timeframe="1D",
            bbw_filter=0.08,
            limit=min(10, max(1, len(_symbols(settings)))),
        ):
            if not isinstance(row, dict):
                continue
            indicators = row.get("indicators") if isinstance(row.get("indicators"), dict) else {}
            records.append(
                _safe_record(
                    {
                        "symbol": row.get("symbol"),
                        "instrument_name": row.get("symbol"),
                        "timeframe": "1D",
                        "tool_name": "bollinger_scan",
                        "setup_type": "volatility_compression_scan",
                        "direction": "watch_breakout_or_mean_reversion",
                        "technical_score": min(0.78, 0.55 + abs(_safe_float(row.get("changePercent"))) / 100),
                        "volatility_state": "bollinger_scan_live",
                        "indicator_state": indicators,
                        "support_resistance": {},
                        "candidate_watchlist_context": "Live TradingView MCP scan requires Qadam corroboration.",
                        "obvious_technical_context_flag": False,
                    },
                    sample=False,
                )
            )
    except Exception:
        records = []

    if records:
        return tuple(records)

    try:
        for row in scanner.volume_breakout_scan(
            "NASDAQ",
            timeframe="1D",
            volume_multiplier=1.5,
            price_change_min=2.0,
            limit=min(10, max(1, len(_symbols(settings)))),
        ):
            if not isinstance(row, dict):
                continue
            records.append(
                _safe_record(
                    {
                        "symbol": row.get("symbol"),
                        "instrument_name": row.get("symbol"),
                        "timeframe": "1D",
                        "tool_name": "volume_breakout_scanner",
                        "setup_type": "volume_breakout_scan",
                        "direction": "watch_volume_confirmation",
                        "technical_score": 0.62,
                        "volatility_state": "volume_breakout_live",
                        "indicator_state": row,
                        "support_resistance": {},
                        "candidate_watchlist_context": "Volume breakout scan requires Qadam corroboration.",
                        "obvious_technical_context_flag": False,
                    },
                    sample=False,
                )
            )
    except Exception:
        return ()
    return tuple(records)


class TradingViewMCPAdapter:
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
            "schema_version": TRADINGVIEW_MCP_SCHEMA_VERSION,
            "sample": True,
            "provider": TRADINGVIEW_MCP_PROVIDER_LABEL,
            "source": TRADINGVIEW_MCP_SOURCE_LABEL,
            "classification": TRADINGVIEW_MCP_CLASSIFICATION,
            "records": [_safe_record(record, sample=True) for record in DEFAULT_TECHNICAL_CONTEXT_RECORDS],
            "canonical_source_count": EXPECTED_SOURCE_COUNT,
            "boundary": TRADINGVIEW_MCP_BOUNDARY,
        }

    def live_payload(self) -> dict[str, Any]:
        dep_status = tradingview_mcp_dependency_status()
        if not _settings_enabled(self.settings):
            return {
                "schema_version": TRADINGVIEW_MCP_SCHEMA_VERSION,
                "sample": False,
                "provider": TRADINGVIEW_MCP_PROVIDER_LABEL,
                "source": TRADINGVIEW_MCP_SOURCE_LABEL,
                "classification": TRADINGVIEW_MCP_CLASSIFICATION,
                "records": [],
                "enabled": False,
                "dependency_status": dep_status.to_dict(),
                "canonical_source_count": EXPECTED_SOURCE_COUNT,
                "boundary": "TRADINGVIEW_MCP_ENABLED is false; live TradingView MCP reads are disabled.",
            }
        if not dep_status.service_importable:
            return {
                "schema_version": TRADINGVIEW_MCP_SCHEMA_VERSION,
                "sample": False,
                "provider": TRADINGVIEW_MCP_PROVIDER_LABEL,
                "source": TRADINGVIEW_MCP_SOURCE_LABEL,
                "classification": TRADINGVIEW_MCP_CLASSIFICATION,
                "records": [],
                "enabled": True,
                "dependency_status": dep_status.to_dict(),
                "canonical_source_count": EXPECTED_SOURCE_COUNT,
                "boundary": "TradingView MCP local service import failed before any provider call.",
            }
        if not _live_calls_enabled(self.settings):
            return {
                "schema_version": TRADINGVIEW_MCP_SCHEMA_VERSION,
                "sample": False,
                "provider": TRADINGVIEW_MCP_PROVIDER_LABEL,
                "source": TRADINGVIEW_MCP_SOURCE_LABEL,
                "classification": TRADINGVIEW_MCP_CLASSIFICATION,
                "records": [],
                "enabled": True,
                "dependency_status": dep_status.to_dict(),
                "live_calls_enabled": False,
                "canonical_source_count": EXPECTED_SOURCE_COUNT,
                "boundary": "TradingView MCP is connected locally; live provider calls are disabled by policy.",
            }
        records = _live_records(self.settings)
        return {
            "schema_version": TRADINGVIEW_MCP_SCHEMA_VERSION,
            "sample": False,
            "provider": TRADINGVIEW_MCP_PROVIDER_LABEL,
            "source": TRADINGVIEW_MCP_SOURCE_LABEL,
            "classification": TRADINGVIEW_MCP_CLASSIFICATION,
            "records": list(records),
            "enabled": True,
            "dependency_status": dep_status.to_dict(),
            "live_calls_enabled": True,
            "canonical_source_count": EXPECTED_SOURCE_COUNT,
            "boundary": TRADINGVIEW_MCP_BOUNDARY,
        }

    def normalize_payload(self, payload: dict[str, Any]) -> tuple[UnifiedEvent, ...]:
        records = payload.get("records", [])
        if not isinstance(records, list):
            return ()
        events: list[UnifiedEvent] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            safe = _safe_record(record, sample=bool(payload.get("sample")))
            summary = _record_summary(safe)
            events.append(
                UnifiedEvent(
                    schema_version=UNIFIED_EVENT_SCHEMA_VERSION,
                    event_id=str(uuid4()),
                    source=TRADINGVIEW_MCP_SOURCE_LABEL,
                    trust_score_at_ingestion=TRADINGVIEW_MCP_TRUST_SCORE,
                    event_type=TRADINGVIEW_MCP_EVENT_TYPE,
                    raw_payload={
                        "symbol": safe["symbol"],
                        "instrument_name": safe["instrument_name"],
                        "timeframe": safe["timeframe"],
                        "tool_name": safe["tool_name"],
                        "setup_type": safe["setup_type"],
                        "direction": safe["direction"],
                        "technical_score": safe["technical_score"],
                        "volatility_state": safe["volatility_state"],
                        "indicator_state": safe["indicator_state"],
                        "support_resistance": safe["support_resistance"],
                        "candidate_watchlist_context": safe["candidate_watchlist_context"],
                        "obvious_technical_context_flag": safe["obvious_technical_context_flag"],
                        "trade_candidate_created": False,
                        "paper_order_allowed": False,
                        "execution_allowed": False,
                    },
                    normalised_summary=summary[:240],
                    coordinates=None,
                    ingested_at=str(safe.get("observed_at") or _now()),
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
        archive_path = self.archive.write(TRADINGVIEW_MCP_SOURCE_KEY, payload)
        events = self.normalize_payload(payload)
        envelope = SourceEnvelope(
            events=events,
            source=TRADINGVIEW_MCP_SOURCE_LABEL,
            trust_score=TRADINGVIEW_MCP_TRUST_SCORE,
            fetched_at=_now(),
            degraded=degraded,
            degraded_reason=degraded_reason,
            raw_archive_path=str(archive_path),
        )
        if persist_context:
            write_tradingview_mcp_context(envelope.to_dict(), self.settings)
        self.event_log.write(
            "source_adapter_fetch_completed",
            "tradingview_mcp_adapter",
            {
                "source": TRADINGVIEW_MCP_SOURCE_LABEL,
                "classification": TRADINGVIEW_MCP_CLASSIFICATION,
                "event_count": len(events),
                "degraded": degraded,
                "degraded_reason": degraded_reason,
                "execution_allowed": False,
                "paper_order_allowed": False,
                "trade_candidate_created": False,
                "broker_write_allowed": False,
                "canonical_source_count": EXPECTED_SOURCE_COUNT,
            },
        )
        return envelope

    def fetch_sample(self) -> SourceEnvelope:
        return self.envelope_from_payload(self.sample_payload())

    def fetch_live(self) -> SourceEnvelope:
        payload = self.live_payload()
        records = payload.get("records", [])
        dep_status = payload.get("dependency_status", {})
        degraded = not bool(records)
        if not _settings_enabled(self.settings):
            degraded_reason = "disabled:TRADINGVIEW_MCP_ENABLED_false"
        elif not dep_status.get("service_importable", False):
            degraded_reason = f"missing_dependency:{dep_status.get('missing_dependency') or 'tradingview_mcp'}"
        elif not _live_calls_enabled(self.settings):
            degraded_reason = "disabled:TRADINGVIEW_MCP_LIVE_CALLS_ENABLED_false"
        elif not records:
            degraded_reason = "no_technical_context_records"
        else:
            degraded_reason = None
            degraded = False
        return self.envelope_from_payload(payload, degraded=degraded, degraded_reason=degraded_reason)


def write_tradingview_mcp_context(envelope: dict[str, Any], settings: Settings | None = None) -> Path:
    settings = settings or Settings.from_env()
    events = envelope.get("events", [])
    if not isinstance(events, list):
        events = []
    context = {
        "schema_version": TRADINGVIEW_MCP_SCHEMA_VERSION,
        "status": "technical_context_recorded" if events else "no_technical_context",
        "source": TRADINGVIEW_MCP_SOURCE_LABEL,
        "classification": TRADINGVIEW_MCP_CLASSIFICATION,
        "provider": TRADINGVIEW_MCP_PROVIDER_LABEL,
        "event_count": len(events),
        "technical_contexts": [
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
        "live_capital_enabled": False,
        "written_at": _now(),
        "boundary": TRADINGVIEW_MCP_BOUNDARY,
    }
    path = _runtime_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(context, indent=2, sort_keys=True), encoding="utf-8")
    history = _history_path(settings)
    with history.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(context, sort_keys=True) + "\n")
    return path


def _safe_context_from_event(event: dict[str, Any]) -> dict[str, Any]:
    raw = event.get("raw_payload") if isinstance(event.get("raw_payload"), dict) else {}
    return {
        "event_id": str(event.get("event_id") or "")[:160],
        "symbol": _safe_symbol(raw.get("symbol")),
        "instrument_name": str(raw.get("instrument_name") or raw.get("symbol") or "unknown")[:120],
        "timeframe": str(raw.get("timeframe") or "1D")[:20],
        "tool_name": str(raw.get("tool_name") or "technical_context")[:80],
        "setup_type": str(raw.get("setup_type") or "technical_context")[:100],
        "direction": str(raw.get("direction") or "watch")[:80],
        "technical_score": round(_safe_float(raw.get("technical_score")), 3),
        "volatility_state": str(raw.get("volatility_state") or "unknown")[:120],
        "indicator_state": raw.get("indicator_state") if isinstance(raw.get("indicator_state"), dict) else {},
        "support_resistance": raw.get("support_resistance")
        if isinstance(raw.get("support_resistance"), dict)
        else {},
        "candidate_watchlist_context": str(raw.get("candidate_watchlist_context") or "")[:260],
        "obvious_technical_context_flag": bool(raw.get("obvious_technical_context_flag")),
        "normalised_summary": str(event.get("normalised_summary") or "")[:240],
        "observed_at": str(event.get("ingested_at") or _now()),
        "trade_candidate_created": False,
        "paper_order_allowed": False,
        "execution_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
        "boundary": TRADINGVIEW_MCP_BOUNDARY,
    }


def tradingview_mcp_context(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    path = _runtime_path(settings)
    if not path.exists():
        return {
            "schema_version": TRADINGVIEW_MCP_SCHEMA_VERSION,
            "status": "not_initialized",
            "source": TRADINGVIEW_MCP_SOURCE_LABEL,
            "classification": TRADINGVIEW_MCP_CLASSIFICATION,
            "provider": TRADINGVIEW_MCP_PROVIDER_LABEL,
            "event_count": 0,
            "technical_contexts": [],
            "source_quorum_credit_allowed": False,
            "trade_candidate_creation_allowed": False,
            "risk_handoff_allowed": False,
            "execution_allowed": False,
            "paper_order_allowed": False,
            "broker_write_allowed": False,
            "live_capital_enabled": False,
            "boundary": TRADINGVIEW_MCP_BOUNDARY,
        }
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "schema_version": TRADINGVIEW_MCP_SCHEMA_VERSION,
            "status": "degraded",
            "source": TRADINGVIEW_MCP_SOURCE_LABEL,
            "classification": TRADINGVIEW_MCP_CLASSIFICATION,
            "provider": TRADINGVIEW_MCP_PROVIDER_LABEL,
            "event_count": 0,
            "technical_contexts": [],
            "source_quorum_credit_allowed": False,
            "trade_candidate_creation_allowed": False,
            "risk_handoff_allowed": False,
            "execution_allowed": False,
            "paper_order_allowed": False,
            "broker_write_allowed": False,
            "live_capital_enabled": False,
            "boundary": "TradingView MCP context artifact could not be read safely.",
        }
    return loaded if isinstance(loaded, dict) else {}


def tradingview_mcp_packet_context(settings: Settings | None = None) -> dict[str, Any]:
    context = tradingview_mcp_context(settings)
    contexts = context.get("technical_contexts", [])
    if not isinstance(contexts, list):
        contexts = []
    challenge_rows = [
        (
            f"Verify {row.get('symbol', 'instrument')} technical setup with canonical catalyst, "
            "market price confirmation, risk, and Q-CTRL paper consultation before any paper order."
        )
        for row in contexts[:4]
        if isinstance(row, dict)
    ]
    return {
        "source_key": TRADINGVIEW_MCP_SOURCE_KEY,
        "status": str(context.get("status") or "not_initialized")[:80],
        "context_role": "read_only_supplemental_technical_confirmation",
        "technical_context_count": len(contexts),
        "technical_context_refs": [
            {
                "symbol": str(row.get("symbol") or "unknown")[:40],
                "setup_type": str(row.get("setup_type") or "technical_context")[:100],
                "technical_score": row.get("technical_score"),
                "obvious_technical_context_flag": bool(row.get("obvious_technical_context_flag")),
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
        "live_capital_enabled": False,
        "boundary": TRADINGVIEW_MCP_BOUNDARY,
    }


def tradingview_mcp_evidence_items(envelope: dict[str, Any]) -> tuple[EvidenceItem, ...]:
    events = envelope.get("events", [])
    if not isinstance(events, list):
        return ()
    items: list[EvidenceItem] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        items.append(
            EvidenceItem(
                evidence_id=f"tradingview_mcp:{event.get('event_id', 'unknown')}",
                source=TRADINGVIEW_MCP_SOURCE_LABEL,
                event_type=TRADINGVIEW_MCP_EVENT_TYPE,
                summary=str(event.get("normalised_summary") or "TradingView MCP technical context.")[:600],
                trust_score=TRADINGVIEW_MCP_TRUST_SCORE,
                observed_at=str(event.get("ingested_at") or _now()),
                raw_ref=None,
            )
        )
    return tuple(items)


def tradingview_mcp_adapter_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    dep_status = tradingview_mcp_dependency_status()
    context = tradingview_mcp_context(settings)
    connected = (
        _settings_enabled(settings)
        and dep_status.local_checkout_exists
        and dep_status.mcp_config_exists
        and dep_status.package_importable
        and dep_status.service_importable
    )
    return {
        "schema_version": TRADINGVIEW_MCP_SCHEMA_VERSION,
        "status": "connected" if connected else "degraded",
        "source": TRADINGVIEW_MCP_SOURCE_LABEL,
        "source_key": TRADINGVIEW_MCP_SOURCE_KEY,
        "provider": TRADINGVIEW_MCP_PROVIDER_LABEL,
        "classification": TRADINGVIEW_MCP_CLASSIFICATION,
        "enabled": _settings_enabled(settings),
        "connected": connected,
        "local_checkout_exists": dep_status.local_checkout_exists,
        "mcp_config_exists": dep_status.mcp_config_exists,
        "package_importable": dep_status.package_importable,
        "service_importable": dep_status.service_importable,
        "live_calls_enabled": _live_calls_enabled(settings),
        "sample_mode_available": True,
        "technical_context_status": context.get("status", "not_initialized"),
        "technical_context_count": int(context.get("event_count", 0) or 0),
        "obvious_technical_context_count": sum(
            1
            for row in context.get("technical_contexts", [])
            if isinstance(row, dict) and row.get("obvious_technical_context_flag") is True
        )
        if isinstance(context.get("technical_contexts"), list)
        else 0,
        "canonical_source": False,
        "canonical_source_count": EXPECTED_SOURCE_COUNT,
        "source_quorum_credit_allowed": False,
        "technical_confirmation_role": "supplemental_technical_confirmation_only",
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
        "live_capital_enabled": False,
        "raw_payload_exposed": False,
        "local_path_exposed": False,
        "public_safe": True,
        "boundary": TRADINGVIEW_MCP_BOUNDARY,
    }


def fetch_tradingview_mcp_sample() -> dict[str, Any]:
    return TradingViewMCPAdapter().fetch_sample().to_dict()


def fetch_tradingview_mcp_live() -> dict[str, Any]:
    return TradingViewMCPAdapter().fetch_live().to_dict()
