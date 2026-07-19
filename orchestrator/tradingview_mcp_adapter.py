"""Read-only TradingView MCP technical-analysis adapter.

TradingView MCP is supplemental market/technical context for Qadam. It can
observe and analyse; it cannot create source quorum, trade candidates, orders,
broker writes, fills, receipts, reconciliation truth, quantum jobs, or live
capital authority.
"""

from __future__ import annotations

import importlib
import importlib.metadata
import importlib.util
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
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
TRADINGVIEW_MCP_SAMPLE_ARTIFACT = "fixtures/tradingview_mcp_sample_context.json"
TRADINGVIEW_MCP_TERMS_NOTE = (
    "Third-party supplemental adapter using public TradingView-analysis libraries. "
    "It is not an official TradingView market-data API and is not licensed historical coverage."
)
TRADINGVIEW_MCP_CONNECTION_STATES = (
    "disabled",
    "sample_only",
    "dependency_missing",
    "live_supplemental",
    "provider_empty",
    "provider_rate_limited",
    "provider_error",
    "stale",
)
TRADINGVIEW_MCP_STALE_AFTER = timedelta(hours=36)
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
    tradingview_ta_importable: bool
    tradingview_screener_importable: bool
    library_versions: dict[str, str | None]
    missing_dependency: str | None
    error: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TradingViewMCPFetchResult:
    connection_state: str
    records: tuple[dict[str, Any], ...]
    provider_call_attempted: bool
    retrieved_at: str | None
    error_class: str | None = None
    error: str | None = None

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


def _sample_path(settings: Settings) -> Path:
    return Path(settings.runtime_dir) / TRADINGVIEW_MCP_SAMPLE_ARTIFACT


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


def _library_version(distribution: str) -> str | None:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None


def tradingview_mcp_dependency_status() -> TradingViewMCPDependencyStatus:
    checkout = _local_checkout()
    config = checkout / ".codex-mcp.json"
    package_importable = False
    service_importable = False
    tradingview_ta_importable = False
    tradingview_screener_importable = False
    missing_dependency: str | None = None
    error: str | None = None
    try:
        _ensure_local_src_on_path()
        importlib.import_module("tradingview_mcp")
        package_importable = True
        tradingview_ta_importable = importlib.util.find_spec("tradingview_ta") is not None
        tradingview_screener_importable = (
            importlib.util.find_spec("tradingview_screener") is not None
        )
        if not tradingview_ta_importable:
            raise ImportError("tradingview_ta is not installed", name="tradingview_ta")
        if not tradingview_screener_importable:
            raise ImportError(
                "tradingview_screener is not installed", name="tradingview_screener"
            )
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
        tradingview_ta_importable=tradingview_ta_importable,
        tradingview_screener_importable=tradingview_screener_importable,
        library_versions={
            "tradingview-ta": _library_version("tradingview-ta"),
            "tradingview-screener": _library_version("tradingview-screener"),
            "tradingview-mcp": _library_version("tradingview-mcp"),
        },
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


TRADINGVIEW_SYMBOL_MAP: dict[str, tuple[str, str]] = {
    "BNO": ("AMEX", "BNO"),
    "GLD": ("AMEX", "GLD"),
    "ITA": ("AMEX", "ITA"),
    "LMT": ("NYSE", "LMT"),
    "NVDA": ("NASDAQ", "NVDA"),
    "PPA": ("NASDAQ", "PPA"),
    "QQQ": ("NASDAQ", "QQQ"),
    "SIL": ("AMEX", "SIL"),
    "SLV": ("AMEX", "SLV"),
    "SMH": ("NASDAQ", "SMH"),
    "SOXX": ("NASDAQ", "SOXX"),
    "SPY": ("AMEX", "SPY"),
    "USO": ("AMEX", "USO"),
    "XAR": ("AMEX", "XAR"),
    "XLE": ("AMEX", "XLE"),
}


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
    retrieved_at = str(record.get("retrieved_at") or _now())
    observed_at = str(record.get("observed_at") or retrieved_at)
    raw_fingerprint = {
        key: value
        for key, value in record.items()
        if key not in {"provider_response_sha256", "retrieved_at"}
    }
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
        "fixture_namespace": "tradingview_mcp_sample" if sample else None,
        "provider": TRADINGVIEW_MCP_PROVIDER_LABEL,
        "provider_interface": "third_party_public_analysis_libraries",
        "venue": str(record.get("venue") or "unknown")[:40],
        "qadam_symbol": str(record.get("qadam_symbol") or record.get("symbol") or "unknown")[:40],
        "provider_symbol": _safe_symbol(record.get("provider_symbol") or record.get("symbol")),
        "market_data_state": str(record.get("market_data_state") or "delay_not_verified")[:80],
        "retrieved_at": retrieved_at,
        "observed_at": observed_at,
        "provider_response_sha256": str(
            record.get("provider_response_sha256")
            or hashlib.sha256(
                json.dumps(raw_fingerprint, sort_keys=True, default=str).encode("utf-8")
            ).hexdigest()
        ),
        "library_versions": record.get("library_versions")
        if isinstance(record.get("library_versions"), dict)
        else {},
        "terms_note": TRADINGVIEW_MCP_TERMS_NOTE,
        "boundary": TRADINGVIEW_MCP_BOUNDARY,
    }


def _provider_failure_state(message: str) -> str:
    lowered = message.lower()
    if "429" in lowered or "rate limit" in lowered or "too many requests" in lowered:
        return "provider_rate_limited"
    return "provider_error"


def _record_is_stale(record: dict[str, Any], *, now: datetime | None = None) -> bool:
    value = str(record.get("observed_at") or "")
    try:
        observed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return True
    reference = now or datetime.now(timezone.utc)
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    return reference - observed.astimezone(timezone.utc) > TRADINGVIEW_MCP_STALE_AFTER


def _live_records(settings: Settings) -> TradingViewMCPFetchResult:
    if not _live_calls_enabled(settings):
        return TradingViewMCPFetchResult(
            connection_state="disabled",
            records=(),
            provider_call_attempted=False,
            retrieved_at=None,
        )
    _ensure_local_src_on_path()
    retrieved_at = _now()
    try:
        scanner = importlib.import_module("tradingview_mcp.core.services.scanner_service")
    except Exception as exc:  # noqa: BLE001 - surfaced as typed connection truth
        return TradingViewMCPFetchResult(
            connection_state="dependency_missing" if isinstance(exc, ImportError) else "provider_error",
            records=(),
            provider_call_attempted=False,
            retrieved_at=retrieved_at,
            error_class=exc.__class__.__name__,
            error=str(exc)[:300],
        )

    dep_status = tradingview_mcp_dependency_status()
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    queried_symbols: list[str] = []
    for qadam_symbol in _symbols(settings):
        mapping = TRADINGVIEW_SYMBOL_MAP.get(qadam_symbol)
        if mapping is None:
            errors.append(f"unsupported_allowlist_symbol:{qadam_symbol}")
            continue
        venue, provider_symbol = mapping
        queried_symbols.append(qadam_symbol)
        try:
            row = scanner.volume_confirmation_analyze(provider_symbol, venue, "1D")
        except Exception as exc:  # noqa: BLE001 - provider failures must remain typed
            errors.append(f"{qadam_symbol}:{exc.__class__.__name__}:{exc}")
            continue
        if not isinstance(row, dict):
            errors.append(f"{qadam_symbol}:invalid_provider_response")
            continue
        if row.get("error"):
            errors.append(f"{qadam_symbol}:{row['error']}")
            continue
        price_data = row.get("price_data") if isinstance(row.get("price_data"), dict) else {}
        volume = row.get("volume_analysis") if isinstance(row.get("volume_analysis"), dict) else {}
        indicators = (
            row.get("technical_indicators")
            if isinstance(row.get("technical_indicators"), dict)
            else {}
        )
        assessment = (
            row.get("overall_assessment")
            if isinstance(row.get("overall_assessment"), dict)
            else {}
        )
        provider_fingerprint = json.dumps(row, sort_keys=True, default=str).encode("utf-8")
        records.append(
            _safe_record(
                {
                    "symbol": qadam_symbol,
                    "qadam_symbol": qadam_symbol,
                    "provider_symbol": f"{venue}:{provider_symbol}",
                    "venue": venue,
                    "instrument_name": f"{qadam_symbol} technical confirmation",
                    "timeframe": "1D",
                    "tool_name": "allowlisted_volume_confirmation",
                    "setup_type": "technical_confirmation_review",
                    "direction": "watch_for_corroboration",
                    "technical_score": min(
                        1.0,
                        max(
                            0.0,
                            0.5
                            + abs(_safe_float(price_data.get("change_percent"))) / 100.0
                            + _safe_float(volume.get("volume_ratio")) / 20.0,
                        ),
                    ),
                    "volatility_state": "provider_current_snapshot",
                    "indicator_state": {**price_data, **volume, **indicators, **assessment},
                    "support_resistance": {},
                    "candidate_watchlist_context": (
                        "Current technical confirmation is supplemental and requires Qadam evidence."
                    ),
                    "obvious_technical_context_flag": False,
                    "retrieved_at": retrieved_at,
                    "observed_at": retrieved_at,
                    "market_data_state": "provider_snapshot_timestamped_at_retrieval",
                    "provider_response_sha256": hashlib.sha256(provider_fingerprint).hexdigest(),
                    "library_versions": dep_status.library_versions,
                },
                sample=False,
            )
        )

    if not records:
        error = ";".join(errors)[:600] if errors else None
        state = _provider_failure_state(error) if error else "provider_empty"
        return TradingViewMCPFetchResult(
            connection_state=state,
            records=(),
            provider_call_attempted=bool(queried_symbols),
            retrieved_at=retrieved_at,
            error_class="provider_response_error" if error else None,
            error=error,
        )
    state = "stale" if all(_record_is_stale(record) for record in records) else "live_supplemental"
    return TradingViewMCPFetchResult(
        connection_state=state,
        records=tuple(records),
        provider_call_attempted=True,
        retrieved_at=retrieved_at,
        error=";".join(errors)[:600] or None,
    )


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
            "connection_state": "sample_only",
            "origin_class": "fixture",
            "evidence_eligible": False,
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
                "connection_state": "disabled",
                "origin_class": "qadam_runtime",
                "evidence_eligible": False,
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
                "connection_state": "dependency_missing",
                "origin_class": "qadam_runtime",
                "evidence_eligible": False,
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
                "connection_state": "disabled",
                "origin_class": "qadam_runtime",
                "evidence_eligible": False,
                "dependency_status": dep_status.to_dict(),
                "live_calls_enabled": False,
                "canonical_source_count": EXPECTED_SOURCE_COUNT,
                "boundary": "TradingView MCP is connected locally; live provider calls are disabled by policy.",
            }
        result = _live_records(self.settings)
        return {
            "schema_version": TRADINGVIEW_MCP_SCHEMA_VERSION,
            "sample": False,
            "provider": TRADINGVIEW_MCP_PROVIDER_LABEL,
            "source": TRADINGVIEW_MCP_SOURCE_LABEL,
            "classification": TRADINGVIEW_MCP_CLASSIFICATION,
            "records": list(result.records),
            "enabled": True,
            "connection_state": result.connection_state,
            "origin_class": "provider_current",
            "evidence_eligible": result.connection_state == "live_supplemental",
            "dependency_status": dep_status.to_dict(),
            "live_calls_enabled": True,
            "provider_call_attempted": result.provider_call_attempted,
            "retrieved_at": result.retrieved_at,
            "provider_error_class": result.error_class,
            "provider_error": result.error,
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
                        "provider": safe["provider"],
                        "provider_interface": safe["provider_interface"],
                        "venue": safe["venue"],
                        "qadam_symbol": safe["qadam_symbol"],
                        "provider_symbol": safe["provider_symbol"],
                        "market_data_state": safe["market_data_state"],
                        "retrieved_at": safe["retrieved_at"],
                        "provider_response_sha256": safe["provider_response_sha256"],
                        "library_versions": safe["library_versions"],
                        "terms_note": safe["terms_note"],
                        "sample": safe["sample"],
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
        payload = self.sample_payload()
        path = _sample_path(self.settings)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return self.envelope_from_payload(payload, persist_context=False)

    def fetch_live(self) -> SourceEnvelope:
        payload = self.live_payload()
        dep_status = payload.get("dependency_status", {})
        connection_state = str(payload.get("connection_state") or "provider_error")
        degraded = connection_state != "live_supplemental"
        if connection_state == "dependency_missing":
            degraded_reason = f"dependency_missing:{dep_status.get('missing_dependency') or 'unknown'}"
        elif degraded:
            degraded_reason = connection_state
        else:
            degraded_reason = None
        return self.envelope_from_payload(payload, degraded=degraded, degraded_reason=degraded_reason)


def write_tradingview_mcp_context(envelope: dict[str, Any], settings: Settings | None = None) -> Path:
    settings = settings or Settings.from_env()
    events = envelope.get("events", [])
    if not isinstance(events, list):
        events = []
    degraded_reason = str(envelope.get("degraded_reason") or "")
    connection_state = "live_supplemental" if events else degraded_reason.split(":", 1)[0]
    if connection_state not in TRADINGVIEW_MCP_CONNECTION_STATES:
        connection_state = "provider_error" if events == [] else "live_supplemental"
    context = {
        "schema_version": TRADINGVIEW_MCP_SCHEMA_VERSION,
        "status": connection_state,
        "connection_state": connection_state,
        "source": TRADINGVIEW_MCP_SOURCE_LABEL,
        "classification": TRADINGVIEW_MCP_CLASSIFICATION,
        "provider": TRADINGVIEW_MCP_PROVIDER_LABEL,
        "event_count": len(events),
        "origin_class": "provider_current" if events else "qadam_runtime",
        "evidence_eligible": connection_state == "live_supplemental" and bool(events),
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
        "provider": str(raw.get("provider") or TRADINGVIEW_MCP_PROVIDER_LABEL)[:100],
        "provider_interface": str(raw.get("provider_interface") or "unknown")[:120],
        "venue": str(raw.get("venue") or "unknown")[:40],
        "qadam_symbol": str(raw.get("qadam_symbol") or raw.get("symbol") or "unknown")[:40],
        "provider_symbol": str(raw.get("provider_symbol") or raw.get("symbol") or "unknown")[:80],
        "market_data_state": str(raw.get("market_data_state") or "unknown")[:80],
        "retrieved_at": str(raw.get("retrieved_at") or event.get("ingested_at") or _now()),
        "provider_response_sha256": str(raw.get("provider_response_sha256") or "")[:64],
        "library_versions": raw.get("library_versions")
        if isinstance(raw.get("library_versions"), dict)
        else {},
        "terms_note": str(raw.get("terms_note") or TRADINGVIEW_MCP_TERMS_NOTE)[:400],
        "sample": bool(raw.get("sample")),
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
    contexts = context.get("technical_contexts")
    if not isinstance(contexts, list):
        contexts = []
    sample_context_count = sum(
        bool(row.get("sample")) for row in contexts if isinstance(row, dict)
    )
    if not _settings_enabled(settings):
        connection_state = "disabled"
    elif not _live_calls_enabled(settings):
        connection_state = "sample_only"
    elif not dep_status.service_importable:
        connection_state = "dependency_missing"
    else:
        connection_state = str(
            context.get("connection_state") or context.get("status") or "provider_empty"
        )
        if connection_state not in TRADINGVIEW_MCP_CONNECTION_STATES:
            connection_state = "provider_error"
    provider_records = [row for row in contexts if isinstance(row, dict) and not row.get("sample")]
    if connection_state == "live_supplemental" and (
        not provider_records or all(_record_is_stale(row) for row in provider_records)
    ):
        connection_state = "stale" if provider_records else "provider_empty"
    connected = connection_state == "live_supplemental"
    return {
        "schema_version": TRADINGVIEW_MCP_SCHEMA_VERSION,
        "status": connection_state,
        "connection_state": connection_state,
        "legacy_status": "connected" if connected else "degraded",
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
        "tradingview_ta_importable": dep_status.tradingview_ta_importable,
        "tradingview_screener_importable": dep_status.tradingview_screener_importable,
        "library_versions": dep_status.library_versions,
        "missing_dependency": dep_status.missing_dependency,
        "dependency_error": dep_status.error,
        "live_calls_enabled": _live_calls_enabled(settings),
        "sample_mode_available": True,
        "sample_records_in_canonical_context_count": sample_context_count,
        "actual_provider_response_required_for_live": True,
        "official_tradingview_market_data_api": False,
        "terms_note": TRADINGVIEW_MCP_TERMS_NOTE,
        "technical_context_status": context.get("status", "not_initialized"),
        "technical_context_count": int(context.get("event_count", 0) or 0),
        "obvious_technical_context_count": sum(
            1
            for row in contexts
            if isinstance(row, dict) and row.get("obvious_technical_context_flag") is True
        )
        if contexts
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
