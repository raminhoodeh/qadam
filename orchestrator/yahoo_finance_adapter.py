"""Supplemental Yahoo Finance market-confirmation adapter.

This adapter is intentionally outside the canonical 35-source registry. It is a
read-only market confirmation tool and cannot create signals, orders, fills, or
reconciliation truth.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
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
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT

YAHOO_FINANCE_SOURCE_KEY = "yahoo_finance"
YAHOO_FINANCE_SOURCE_LABEL = "market.yahoo_finance"
YAHOO_FINANCE_EVENT_TYPE = "market_price_confirmation"
YAHOO_FINANCE_TRUST_SCORE = 0.58
YAHOO_FINANCE_CLASSIFICATION = "accepted_supplemental_pending_live_dependencies"

DEFAULT_SAMPLE_MARKET_RECORDS: tuple[dict[str, Any], ...] = (
    {
        "symbol": "CL=F",
        "instrument_name": "WTI crude oil futures proxy",
        "last_close": 79.42,
        "previous_close": 78.81,
        "percent_move": 0.774,
        "volume": 238000,
        "average_volume_20d": 212000,
        "volume_ratio": 1.123,
        "rolling_volatility_20d": 0.021,
        "option_chain_available": False,
        "market_state": "sample_closed",
    },
    {
        "symbol": "SLV",
        "instrument_name": "Silver ETF proxy",
        "last_close": 28.63,
        "previous_close": 28.11,
        "percent_move": 1.85,
        "volume": 32100000,
        "average_volume_20d": 24600000,
        "volume_ratio": 1.305,
        "rolling_volatility_20d": 0.018,
        "option_chain_available": True,
        "market_state": "sample_closed",
    },
    {
        "symbol": "SMH",
        "instrument_name": "Semiconductor ETF proxy",
        "last_close": 247.18,
        "previous_close": 249.04,
        "percent_move": -0.747,
        "volume": 8210000,
        "average_volume_20d": 7750000,
        "volume_ratio": 1.059,
        "rolling_volatility_20d": 0.026,
        "option_chain_available": True,
        "market_state": "sample_closed",
    },
)


@dataclass(frozen=True)
class YahooFinanceDependencyStatus:
    importable: bool
    version: str | None
    local_checkout_exists: bool
    missing_dependency: str | None
    error: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "importable": self.importable,
            "version": self.version,
            "local_checkout_exists": self.local_checkout_exists,
            "missing_dependency": self.missing_dependency,
            "error": self.error,
        }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _local_checkout() -> Path:
    return _repo_root() / "yahoo-finance-api"


def _safe_symbols(symbols: tuple[str, ...], settings: Settings) -> tuple[str, ...]:
    allowlist = set(settings.yfinance_symbol_allowlist)
    requested = tuple(dict.fromkeys(symbol.strip().upper() for symbol in symbols if symbol.strip()))
    if not requested:
        requested = settings.yfinance_symbol_allowlist[: min(3, settings.yfinance_request_budget_per_run)]
    budget = max(1, settings.yfinance_request_budget_per_run)
    return tuple(symbol for symbol in requested if symbol in allowlist)[:budget]


def _import_yfinance() -> Any:
    try:
        import yfinance as yf  # type: ignore[import-not-found]

        return yf
    except ImportError:
        checkout = _local_checkout()
        if checkout.exists() and str(checkout) not in sys.path:
            sys.path.insert(0, str(checkout))
        try:
            import yfinance as yf  # type: ignore[import-not-found]

            return yf
        except ImportError as second_error:
            raise RuntimeError(
                f"yfinance is not importable from the environment or local checkout: {second_error}"
            ) from second_error


def yahoo_finance_dependency_status() -> YahooFinanceDependencyStatus:
    checkout_exists = _local_checkout().exists()
    try:
        yf = _import_yfinance()
    except RuntimeError as exc:
        cause = exc.__cause__
        missing = getattr(cause, "name", None) if cause else None
        return YahooFinanceDependencyStatus(
            importable=False,
            version=None,
            local_checkout_exists=checkout_exists,
            missing_dependency=missing,
            error=str(exc),
        )
    return YahooFinanceDependencyStatus(
        importable=True,
        version=str(getattr(yf, "__version__", "unknown")),
        local_checkout_exists=checkout_exists,
        missing_dependency=None,
        error=None,
    )


class YahooFinanceAdapter:
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

    def sample_payload(self, symbols: tuple[str, ...] | None = None) -> dict[str, Any]:
        requested = set(_safe_symbols(symbols, self.settings)) if symbols else set()
        records = (
            [
                record
                for record in DEFAULT_SAMPLE_MARKET_RECORDS
                if str(record["symbol"]).upper() in requested
            ]
            if requested
            else list(DEFAULT_SAMPLE_MARKET_RECORDS)
        )
        if not records:
            records = list(DEFAULT_SAMPLE_MARKET_RECORDS[:1])
        return {
            "sample": True,
            "classification": YAHOO_FINANCE_CLASSIFICATION,
            "provider": "yahoo_finance_via_yfinance",
            "source": YAHOO_FINANCE_SOURCE_LABEL,
            "records": records,
            "request_budget_per_run": self.settings.yfinance_request_budget_per_run,
            "canonical_source_count": EXPECTED_SOURCE_COUNT,
            "boundary": "Read-only supplemental market confirmation; no execution or reconciliation authority.",
        }

    def normalize_payload(self, payload: dict[str, Any]) -> tuple[UnifiedEvent, ...]:
        records = payload.get("records", [])
        if not isinstance(records, list):
            return ()
        events: list[UnifiedEvent] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            symbol = str(record.get("symbol") or "UNKNOWN")[:24]
            instrument_name = str(record.get("instrument_name") or symbol)[:80]
            last_close = record.get("last_close")
            percent_move = record.get("percent_move")
            volume_ratio = record.get("volume_ratio")
            summary = (
                f"{symbol} {instrument_name} market confirmation: close={last_close}, "
                f"move={percent_move}%, volume_ratio={volume_ratio}"
            )
            events.append(
                UnifiedEvent(
                    schema_version=UNIFIED_EVENT_SCHEMA_VERSION,
                    event_id=str(uuid4()),
                    source=YAHOO_FINANCE_SOURCE_LABEL,
                    trust_score_at_ingestion=YAHOO_FINANCE_TRUST_SCORE,
                    event_type=YAHOO_FINANCE_EVENT_TYPE,
                    raw_payload={
                        "symbol": symbol,
                        "instrument_name": instrument_name,
                        "last_close": last_close,
                        "previous_close": record.get("previous_close"),
                        "percent_move": percent_move,
                        "volume": record.get("volume"),
                        "volume_ratio": volume_ratio,
                        "rolling_volatility_20d": record.get("rolling_volatility_20d"),
                        "option_chain_available": bool(record.get("option_chain_available")),
                        "market_state": record.get("market_state"),
                        "sample": bool(payload.get("sample")),
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
    ) -> SourceEnvelope:
        archive_path = self.archive.write(YAHOO_FINANCE_SOURCE_KEY, payload)
        events = self.normalize_payload(payload)
        envelope = SourceEnvelope(
            events=events,
            source=YAHOO_FINANCE_SOURCE_LABEL,
            trust_score=YAHOO_FINANCE_TRUST_SCORE,
            fetched_at=_now(),
            degraded=degraded,
            degraded_reason=degraded_reason,
            raw_archive_path=str(archive_path),
        )
        self.event_log.write(
            "source_adapter_fetch_completed",
            "yahoo_finance_adapter",
            {
                "source": YAHOO_FINANCE_SOURCE_LABEL,
                "classification": YAHOO_FINANCE_CLASSIFICATION,
                "event_count": len(events),
                "degraded": degraded,
                "degraded_reason": degraded_reason,
                "execution_allowed": False,
                "paper_order_allowed": False,
                "broker_write_allowed": False,
                "canonical_source_count": EXPECTED_SOURCE_COUNT,
            },
        )
        return envelope

    def fetch_sample(self, symbols: tuple[str, ...] | None = None) -> SourceEnvelope:
        return self.envelope_from_payload(self.sample_payload(symbols))

    def fetch_live(
        self,
        *,
        symbols: tuple[str, ...] | None = None,
        period: str = "1mo",
        interval: str = "1d",
    ) -> SourceEnvelope:
        safe_symbols = _safe_symbols(symbols or (), self.settings)
        if not self.settings.yfinance_enabled:
            return self.envelope_from_payload(
                {
                    "sample": False,
                    "provider": "yahoo_finance_via_yfinance",
                    "source": YAHOO_FINANCE_SOURCE_LABEL,
                    "records": [],
                    "requested_symbols": list(safe_symbols),
                    "enabled": False,
                    "canonical_source_count": EXPECTED_SOURCE_COUNT,
                    "boundary": "YFINANCE_ENABLED is false; live Yahoo Finance reads are disabled.",
                },
                degraded=True,
                degraded_reason="disabled:YFINANCE_ENABLED_false",
            )

        dep_status = yahoo_finance_dependency_status()
        if not dep_status.importable:
            return self.envelope_from_payload(
                {
                    "sample": False,
                    "provider": "yahoo_finance_via_yfinance",
                    "source": YAHOO_FINANCE_SOURCE_LABEL,
                    "records": [],
                    "requested_symbols": list(safe_symbols),
                    "dependency_status": dep_status.to_dict(),
                    "canonical_source_count": EXPECTED_SOURCE_COUNT,
                    "boundary": "Live Yahoo Finance read degraded before provider call.",
                },
                degraded=True,
                degraded_reason=f"missing_dependency:{dep_status.missing_dependency or 'yfinance'}",
            )

        try:
            yf = _import_yfinance()
            cache_dir = Path(self.settings.yfinance_cache_dir)
            cache_dir.mkdir(parents=True, exist_ok=True)
            if hasattr(yf, "set_tz_cache_location"):
                yf.set_tz_cache_location(str(cache_dir))
            data = yf.download(
                " ".join(safe_symbols),
                period=period,
                interval=interval,
                progress=False,
                threads=False,
                timeout=10,
            )
            records = self._records_from_dataframe(data, safe_symbols)
        except Exception as exc:  # noqa: BLE001 - live provider failure should degrade explicitly
            return self.envelope_from_payload(
                {
                    "sample": False,
                    "provider": "yahoo_finance_via_yfinance",
                    "source": YAHOO_FINANCE_SOURCE_LABEL,
                    "records": [],
                    "requested_symbols": list(safe_symbols),
                    "error_type": exc.__class__.__name__,
                    "error": repr(exc)[:500],
                    "canonical_source_count": EXPECTED_SOURCE_COUNT,
                    "boundary": "Live Yahoo Finance provider read degraded; no signal or execution authority.",
                },
                degraded=True,
                degraded_reason=f"live_fetch_error:{exc.__class__.__name__}",
            )

        return self.envelope_from_payload(
            {
                "sample": False,
                "provider": "yahoo_finance_via_yfinance",
                "source": YAHOO_FINANCE_SOURCE_LABEL,
                "records": records,
                "requested_symbols": list(safe_symbols),
                "period": period,
                "interval": interval,
                "canonical_source_count": EXPECTED_SOURCE_COUNT,
                "boundary": "Read-only supplemental market confirmation; no execution or reconciliation authority.",
            },
            degraded=not records,
            degraded_reason="no_market_records" if not records else None,
        )

    @staticmethod
    def _records_from_dataframe(data: Any, symbols: tuple[str, ...]) -> list[dict[str, Any]]:
        if data is None or getattr(data, "empty", True):
            return []
        records: list[dict[str, Any]] = []
        for symbol in symbols:
            try:
                if hasattr(data.columns, "levels") and symbol in data.columns.get_level_values(0):
                    frame = data[symbol].dropna(how="all")
                else:
                    frame = data.dropna(how="all")
                if frame.empty:
                    continue
                close = frame["Close"].dropna()
                volume = frame["Volume"].dropna() if "Volume" in frame else []
                if len(close) < 2:
                    continue
                last_close = float(close.iloc[-1])
                previous_close = float(close.iloc[-2])
                percent_move = ((last_close - previous_close) / previous_close) * 100 if previous_close else 0.0
                latest_volume = int(volume.iloc[-1]) if len(volume) else None
                avg_volume = float(volume.tail(20).mean()) if len(volume) else None
                records.append(
                    {
                        "symbol": symbol,
                        "instrument_name": symbol,
                        "last_close": round(last_close, 6),
                        "previous_close": round(previous_close, 6),
                        "percent_move": round(percent_move, 3),
                        "volume": latest_volume,
                        "average_volume_20d": round(avg_volume, 3) if avg_volume else None,
                        "volume_ratio": round(latest_volume / avg_volume, 3)
                        if latest_volume and avg_volume
                        else None,
                        "rolling_volatility_20d": None,
                        "option_chain_available": False,
                        "market_state": "live_snapshot",
                    }
                )
            except Exception:
                continue
        return records


def yahoo_finance_adapter_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    dep_status = yahoo_finance_dependency_status()
    archive_root = Path(settings.raw_payload_dir) / YAHOO_FINANCE_SOURCE_KEY
    return {
        "status": "ok",
        "classification": YAHOO_FINANCE_CLASSIFICATION,
        "source": YAHOO_FINANCE_SOURCE_LABEL,
        "canonical_source_count": EXPECTED_SOURCE_COUNT,
        "enabled": settings.yfinance_enabled,
        "request_budget_per_run": settings.yfinance_request_budget_per_run,
        "symbol_allowlist_count": len(settings.yfinance_symbol_allowlist),
        "local_checkout_exists": dep_status.local_checkout_exists,
        "dependency_importable": dep_status.importable,
        "dependency_version": dep_status.version,
        "missing_dependency": dep_status.missing_dependency,
        "raw_archive_exists": archive_root.exists(),
        "public_safe_status_boundary": (
            "Do not expose cookies, crumb tokens, cache paths, raw HTML, raw payloads, or full provider errors."
        ),
        "live_boundary": (
            "Read-only supplemental market confirmation. Cannot create signals, risk approvals, "
            "orders, broker writes, fills, receipts, reconciliation truth, live capital, or quantum jobs."
        ),
    }


def fetch_yahoo_finance_sample(symbols: tuple[str, ...] | None = None) -> dict[str, Any]:
    return YahooFinanceAdapter().fetch_sample(symbols).to_dict()


def fetch_yahoo_finance_live(
    *,
    symbols: tuple[str, ...] | None = None,
    period: str = "1mo",
    interval: str = "1d",
) -> dict[str, Any]:
    return YahooFinanceAdapter().fetch_live(symbols=symbols, period=period, interval=interval).to_dict()
