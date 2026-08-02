"""Read-only Alpaca market context for current paper-trade decisions.

The adapter reads stock and ETF bars and quotes from Alpaca's market-data API.
It never calls a broker endpoint and cannot create candidates, approvals, or
orders. Credentials are consumed from the existing secret boundary and are
never written to artifacts.
"""

from __future__ import annotations

import json
import math
import re
from datetime import datetime, timedelta, timezone
from statistics import pstdev
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from orchestrator.config import Settings
from orchestrator.secrets import secret_value

ALPACA_MARKET_CONTEXT_PROVIDER = "alpaca_market_data_v2"
ALPACA_MARKET_CONTEXT_PROVIDER_LABEL = "Alpaca Market Data IEX"
ALPACA_DATA_BASE_URL = "https://data.alpaca.markets/v2"
ALPACA_MARKET_CONTEXT_TRUST_SCORE = 0.76
LOOKBACK_DAYS = 45
MAX_SYMBOLS_PER_REFRESH = 32
SAFE_SYMBOL = re.compile(r"[A-Z][A-Z0-9.\-]{0,14}")
MAX_ACTIONABLE_QUOTE_AGE_SECONDS = 5 * 60


def _as_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _safe_symbols(symbols: list[str] | tuple[str, ...] | set[str]) -> list[str]:
    return sorted(
        {
            str(symbol).upper().strip()
            for symbol in symbols
            if SAFE_SYMBOL.fullmatch(str(symbol).upper().strip())
        }
    )[:MAX_SYMBOLS_PER_REFRESH]


def _parse_timestamp(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def _actionable_quote_state(generated_at: str, quote_at: Any) -> tuple[bool, str, float | None]:
    generated = _parse_timestamp(generated_at)
    quote_time = _parse_timestamp(quote_at)
    if generated is None or quote_time is None:
        return False, "quote_timestamp_missing", None
    quote_age = max((generated - quote_time).total_seconds(), 0.0)
    eastern = generated.astimezone(ZoneInfo("America/New_York"))
    minute = eastern.hour * 60 + eastern.minute
    regular_session = eastern.weekday() < 5 and 570 <= minute < 960
    if not regular_session:
        return False, "outside_regular_session", quote_age
    if quote_age > MAX_ACTIONABLE_QUOTE_AGE_SECONDS:
        return False, "stale_regular_session_quote", quote_age
    return True, "fresh_regular_session_quote", quote_age


def _provider_headers(api_key: str, api_secret: str) -> dict[str, str]:
    return {
        "APCA-API-KEY-ID": api_key,
        "APCA-API-SECRET-KEY": api_secret,
        "Accept": "application/json",
        "User-Agent": "qadam-market-context/1 read-only",
    }


def _fetch_json(url: str, headers: dict[str, str], timeout_seconds: int) -> dict[str, Any]:
    request = Request(url, headers=headers, method="GET")
    with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("alpaca_market_context_payload_not_object")
    return payload


def build_alpaca_market_context_records(
    symbols: list[str] | tuple[str, ...] | set[str],
    bars_payload: dict[str, Any],
    quotes_payload: dict[str, Any],
    *,
    generated_at: str,
) -> list[dict[str, Any]]:
    """Normalize bounded provider payloads into public-safe decision evidence."""

    safe_symbols = _safe_symbols(symbols)
    bars_by_symbol = bars_payload.get("bars")
    bars_by_symbol = bars_by_symbol if isinstance(bars_by_symbol, dict) else {}
    quotes_by_symbol = quotes_payload.get("quotes")
    quotes_by_symbol = quotes_by_symbol if isinstance(quotes_by_symbol, dict) else {}
    records: list[dict[str, Any]] = []
    for symbol in safe_symbols:
        raw_bars = bars_by_symbol.get(symbol)
        raw_bars = raw_bars if isinstance(raw_bars, list) else []
        bars = [row for row in raw_bars if isinstance(row, dict) and _as_float(row.get("c"))]
        bars.sort(key=lambda row: str(row.get("t") or ""))
        if len(bars) < 2:
            continue
        closes = [_as_float(row.get("c")) for row in bars]
        closes = [value for value in closes if value is not None and value > 0]
        if len(closes) < 2:
            continue
        latest = bars[-1]
        latest_close = _as_float(latest.get("c"))
        previous_close = _as_float(bars[-2].get("c"))
        if latest_close is None or previous_close in {None, 0.0}:
            continue
        returns = [right / left - 1.0 for left, right in zip(closes, closes[1:]) if left]
        rolling_daily_volatility = pstdev(returns[-20:]) if len(returns) >= 2 else None
        volumes = [_as_float(row.get("v")) or 0.0 for row in bars]
        average_volume = sum(volumes[-20:]) / max(len(volumes[-20:]), 1)
        latest_volume = volumes[-1]
        dollar_volumes = [
            (_as_float(row.get("c")) or 0.0) * (_as_float(row.get("v")) or 0.0)
            for row in bars[-20:]
        ]
        average_daily_dollar_volume = sum(dollar_volumes) / max(len(dollar_volumes), 1)
        quote = quotes_by_symbol.get(symbol)
        quote = quote if isinstance(quote, dict) else {}
        bid = _as_float(quote.get("bp"))
        ask = _as_float(quote.get("ap"))
        midpoint = (bid + ask) / 2.0 if bid is not None and ask is not None else None
        observed_spread_bps = (
            ((ask - bid) / midpoint) * 10_000
            if midpoint not in {None, 0.0} and ask is not None and bid is not None and ask >= bid
            else None
        )
        quote_actionable, quote_state, quote_age_seconds = _actionable_quote_state(
            generated_at, quote.get("t")
        )
        spread_bps = observed_spread_bps if quote_actionable else None
        records.append(
            {
                "source": ALPACA_MARKET_CONTEXT_PROVIDER,
                "symbol": symbol,
                "instrument_name": symbol,
                "last_close": round(latest_close, 6),
                "current_price": round((midpoint if quote_actionable else None) or latest_close, 6),
                "previous_close": round(previous_close, 6),
                "percent_move": round((latest_close / previous_close - 1.0) * 100.0, 4),
                "volume": latest_volume,
                "average_volume_20d": round(average_volume, 3),
                "volume_ratio": round(latest_volume / average_volume, 4)
                if average_volume > 0
                else None,
                "rolling_volatility_20d": round(rolling_daily_volatility, 8)
                if rolling_daily_volatility is not None
                else None,
                "annualized_volatility": round(rolling_daily_volatility * math.sqrt(252.0), 8)
                if rolling_daily_volatility is not None
                else None,
                "average_daily_dollar_volume": round(average_daily_dollar_volume, 2),
                "spread_bps": round(spread_bps, 4) if spread_bps is not None else None,
                "observed_non_actionable_spread_bps": round(observed_spread_bps, 4)
                if observed_spread_bps is not None and not quote_actionable
                else None,
                "observed_at": latest.get("t"),
                "quote_observed_at": quote.get("t"),
                "quote_age_seconds": round(quote_age_seconds, 3)
                if quote_age_seconds is not None
                else None,
                "quote_state": quote_state,
                "quote_actionable": quote_actionable,
                "available_at": generated_at,
                "market_state": "provider_latest_read_only_observation",
                "provider": ALPACA_MARKET_CONTEXT_PROVIDER,
                "provider_label": ALPACA_MARKET_CONTEXT_PROVIDER_LABEL,
                "provider_backed": True,
                "origin_class": "provider_backed_market_context",
                "trust_score": ALPACA_MARKET_CONTEXT_TRUST_SCORE,
                "authority": "supplemental_market_confirmation_only",
                "read_only_market_data": True,
                "broker_endpoint_used": False,
            }
        )
    return records


def fetch_alpaca_market_context(
    symbols: list[str] | tuple[str, ...] | set[str],
    *,
    settings: Settings | None = None,
    generated_at: str | None = None,
    timeout_seconds: int = 15,
) -> dict[str, Any]:
    """Fetch one bounded bars-and-quotes snapshot from read-only endpoints."""

    settings = settings or Settings.from_env()
    generated_at = generated_at or datetime.now(timezone.utc).isoformat()
    safe_symbols = _safe_symbols(symbols)
    status: dict[str, Any] = {
        "provider": ALPACA_MARKET_CONTEXT_PROVIDER,
        "provider_label": ALPACA_MARKET_CONTEXT_PROVIDER_LABEL,
        "generated_at": generated_at,
        "status": "pending" if safe_symbols else "no_supported_symbols",
        "requested_symbols": safe_symbols,
        "requested_symbol_count": len(safe_symbols),
        "record_count": 0,
        "records": [],
        "provider_backed": False,
        "read_only_market_data": True,
        "broker_endpoint_used": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
    }
    if not safe_symbols:
        return status
    api_key = secret_value("ALPACA_API_KEY", settings)
    api_secret = secret_value("ALPACA_API_SECRET", settings)
    if not api_key or not api_secret:
        status["status"] = "missing_credentials"
        return status
    generated = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    if generated.tzinfo is None:
        generated = generated.replace(tzinfo=timezone.utc)
    params = {
        "symbols": ",".join(safe_symbols),
        "timeframe": "1Day",
        "start": (generated - timedelta(days=LOOKBACK_DAYS)).isoformat(),
        "end": generated.isoformat(),
        "limit": 10000,
        "adjustment": "all",
        "feed": "iex",
        "sort": "asc",
    }
    headers = _provider_headers(api_key, api_secret)
    try:
        bars_payload = _fetch_json(
            f"{ALPACA_DATA_BASE_URL}/stocks/bars?{urlencode(params)}",
            headers,
            timeout_seconds,
        )
        if bars_payload.get("next_page_token"):
            raise RuntimeError("alpaca_market_context_unexpected_pagination")
        quote_params = urlencode({"symbols": ",".join(safe_symbols), "feed": "iex"})
        quotes_payload = _fetch_json(
            f"{ALPACA_DATA_BASE_URL}/stocks/quotes/latest?{quote_params}",
            headers,
            timeout_seconds,
        )
        records = build_alpaca_market_context_records(
            safe_symbols,
            bars_payload,
            quotes_payload,
            generated_at=generated_at,
        )
    except Exception as exc:  # Provider errors become typed evidence gaps.
        status.update(
            {
                "status": "provider_error",
                "failure_category": type(exc).__name__,
                "error_detail_redacted": True,
            }
        )
        return status
    status.update(
        {
            "status": "ok" if records else "empty_provider_response",
            "record_count": len(records),
            "records": records,
            "provider_backed": bool(records),
        }
    )
    return status
