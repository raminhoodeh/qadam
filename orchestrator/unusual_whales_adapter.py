"""Time-bounded Unusual Whales historical research adapter.

The adapter is deliberately separate from Qadam's live source-quorum adapters.
It can collect and normalize read-only market-positioning history for later
backtests, but it cannot create signals, candidates, approvals, or orders.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Callable, Iterable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import ROOT, authority_flags, now_iso, runtime_dir
from orchestrator.secrets import secret_status, secret_value


SCHEMA_VERSION = "unusual_whales_historical_research.v1"
PARSER_VERSION = "unusual_whales_normalizer.v1"
SOURCE_KEY = "unusual_whales"
SOURCE_LABEL = "market.unusual_whales"
BASE_URL = "https://api.unusualwhales.com"
CLIENT_API_ID = "100001"
DEFAULT_ACCESS_EXPIRES_ON = date(2026, 7, 21)
DEFAULT_TIMEZONE = "Asia/Dubai"
DEFAULT_DAILY_REQUEST_BUDGET = 3_000
DEFAULT_RUN_REQUEST_BUDGET = 500

STATUS_ARTIFACT = "unusual_whales_research_status.json"
FEATURE_MANIFEST_ARTIFACT = "unusual_whales_backtest_feature_manifest.json"
RESEARCH_ROOT = ROOT / "data" / "research" / SOURCE_KEY

DEFAULT_SYMBOLS = (
    "BNO",
    "GLD",
    "ITA",
    "LMT",
    "NVDA",
    "PPA",
    "QQQ",
    "SIL",
    "SLV",
    "SMH",
    "SOXX",
    "SPY",
    "USO",
    "XAR",
    "XLE",
)

RESEARCH_AUTHORITY = {
    **authority_flags(),
    "source_quorum_allowed": False,
    "signal_approval_allowed": False,
    "strategy_hypothesis_creation_allowed": False,
    "trade_candidate_creation_allowed": False,
    "risk_approval_allowed": False,
    "execution_allowed": False,
    "paper_order_allowed": False,
    "broker_write_allowed": False,
    "proof_credit_allowed": False,
}


@dataclass(frozen=True)
class EndpointSpec:
    key: str
    path_template: str
    feature_family: str
    strategy_roles: tuple[str, ...]
    allowed_query_params: frozenset[str]
    requires_symbol: bool = False
    requires_function: bool = False
    time_paginated: bool = False
    maximum_limit: int | None = None


ENDPOINTS: dict[str, EndpointSpec] = {
    "market_tide": EndpointSpec(
        key="market_tide",
        path_template="/api/market/market-tide",
        feature_family="market_options_sentiment",
        strategy_roles=("regime_conditioning", "entry_confirmation"),
        allowed_query_params=frozenset({"date", "otm_only", "interval_5m"}),
    ),
    "flow_alerts": EndpointSpec(
        key="flow_alerts",
        path_template="/api/option-trades/flow-alerts",
        feature_family="unusual_options_flow",
        strategy_roles=("signal_generator", "lead_lag_confirmation", "entry_confirmation"),
        allowed_query_params=frozenset(
            {
                "ticker_symbol",
                "unusual",
                "min_premium",
                "max_premium",
                "min_size",
                "max_size",
                "min_volume",
                "max_volume",
                "min_open_interest",
                "max_open_interest",
                "all_opening",
                "is_floor",
                "is_sweep",
                "is_call",
                "is_put",
                "is_ask_side",
                "is_bid_side",
                "is_otm",
                "min_volume_oi_ratio",
                "min_ask_perc",
                "size_greater_oi",
                "vol_greater_oi",
                "newer_than",
                "older_than",
                "limit",
            }
        ),
        time_paginated=True,
        maximum_limit=200,
    ),
    "darkpool_ticker": EndpointSpec(
        key="darkpool_ticker",
        path_template="/api/darkpool/{ticker}",
        feature_family="darkpool_positioning",
        strategy_roles=("institutional_confirmation", "divergence_confirmation"),
        allowed_query_params=frozenset(
            {
                "date",
                "newer_than",
                "older_than",
                "min_premium",
                "max_premium",
                "min_size",
                "max_size",
                "min_volume",
                "max_volume",
                "limit",
                "order",
                "order_by",
            }
        ),
        requires_symbol=True,
        time_paginated=True,
        maximum_limit=500,
    ),
    "options_volume": EndpointSpec(
        key="options_volume",
        path_template="/api/stock/{ticker}/options-volume",
        feature_family="options_volume_positioning",
        strategy_roles=("regime_conditioning", "entry_confirmation"),
        allowed_query_params=frozenset({"limit"}),
        requires_symbol=True,
        maximum_limit=500,
    ),
    "net_premium_ticks": EndpointSpec(
        key="net_premium_ticks",
        path_template="/api/stock/{ticker}/net-prem-ticks",
        feature_family="ticker_net_premium",
        strategy_roles=("signal_generator", "lead_lag_confirmation"),
        allowed_query_params=frozenset({"date"}),
        requires_symbol=True,
    ),
    "greeks": EndpointSpec(
        key="greeks",
        path_template="/api/stock/{ticker}/greeks",
        feature_family="options_greeks",
        strategy_roles=("regime_conditioning", "entry_confirmation"),
        allowed_query_params=frozenset({"date"}),
        requires_symbol=True,
    ),
    "spot_gex": EndpointSpec(
        key="spot_gex",
        path_template="/api/stock/{ticker}/spot-exposures/strike",
        feature_family="gamma_exposure",
        strategy_roles=("regime_conditioning", "breakout_confirmation"),
        allowed_query_params=frozenset({"date"}),
        requires_symbol=True,
    ),
    "interpolated_iv": EndpointSpec(
        key="interpolated_iv",
        path_template="/api/stock/{ticker}/interpolated-iv",
        feature_family="implied_volatility",
        strategy_roles=("regime_conditioning", "breakout_confirmation"),
        allowed_query_params=frozenset({"date"}),
        requires_symbol=True,
    ),
    "technical_indicator": EndpointSpec(
        key="technical_indicator",
        path_template="/api/stock/{ticker}/technical-indicator/{function}",
        feature_family="provider_technical_crosscheck",
        strategy_roles=("entry_confirmation",),
        allowed_query_params=frozenset({"interval", "time_period", "series_type", "month"}),
        requires_symbol=True,
        requires_function=True,
    ),
}

TECHNICAL_FUNCTIONS = frozenset({"RSI", "SMA", "EMA", "MACD", "BBANDS", "STOCH", "VWAP"})
SYMBOL_PATTERN = re.compile(r"^[A-Z][A-Z0-9.\-]{0,14}$")
TIME_FIELDS = (
    "timestamp",
    "created_at",
    "executed_at",
    "trf_executed_at",
    "date",
    "start_time",
    "end_time",
)
SYMBOL_FIELDS = ("ticker", "ticker_symbol", "symbol", "underlying_symbol")
DIMENSION_FIELDS = (
    "alert_rule",
    "rule_name",
    "type",
    "option_chain",
    "expiry",
    "issue_type",
    "market_center",
    "sale_cond_codes",
    "function",
    "interval",
)


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default


def _parse_date(value: str | None, fallback: date) -> date:
    if not value:
        return fallback
    try:
        return date.fromisoformat(value)
    except ValueError:
        return fallback


def _csv_symbols(value: str | None) -> tuple[str, ...]:
    raw = value.split(",") if value else DEFAULT_SYMBOLS
    return tuple(dict.fromkeys(item.strip().upper() for item in raw if SYMBOL_PATTERN.fullmatch(item.strip().upper())))


@dataclass(frozen=True)
class UnusualWhalesResearchConfig:
    enabled: bool
    access_expires_on: date
    timezone_name: str
    client_api_id: str
    daily_request_budget: int
    run_request_budget: int
    symbol_allowlist: tuple[str, ...]
    provider_terms_reviewed: bool
    raw_retention_allowed: bool

    @classmethod
    def from_env(cls) -> "UnusualWhalesResearchConfig":
        return cls(
            enabled=_env_bool("UNUSUAL_WHALES_RESEARCH_ENABLED", False),
            access_expires_on=_parse_date(
                os.getenv("UNUSUAL_WHALES_ACCESS_EXPIRES_ON"),
                DEFAULT_ACCESS_EXPIRES_ON,
            ),
            timezone_name=os.getenv("UNUSUAL_WHALES_ACCESS_TIMEZONE", DEFAULT_TIMEZONE),
            client_api_id=os.getenv("UNUSUAL_WHALES_CLIENT_API_ID", CLIENT_API_ID),
            daily_request_budget=_env_int(
                "UNUSUAL_WHALES_DAILY_REQUEST_BUDGET",
                DEFAULT_DAILY_REQUEST_BUDGET,
            ),
            run_request_budget=_env_int(
                "UNUSUAL_WHALES_RUN_REQUEST_BUDGET",
                DEFAULT_RUN_REQUEST_BUDGET,
            ),
            symbol_allowlist=_csv_symbols(os.getenv("UNUSUAL_WHALES_SYMBOL_ALLOWLIST")),
            provider_terms_reviewed=_env_bool("UNUSUAL_WHALES_PROVIDER_TERMS_REVIEWED", False),
            raw_retention_allowed=_env_bool("UNUSUAL_WHALES_RAW_RETENTION_ALLOWED", False),
        )


def _aware_now(now: datetime | None = None) -> datetime:
    active = now or datetime.now(timezone.utc)
    if active.tzinfo is None:
        return active.replace(tzinfo=timezone.utc)
    return active


def access_state(
    config: UnusualWhalesResearchConfig,
    *,
    credential_configured: bool,
    now: datetime | None = None,
) -> str:
    local_now = _aware_now(now).astimezone(ZoneInfo(config.timezone_name))
    if local_now.date() > config.access_expires_on:
        return "expired_archive_only"
    if not config.enabled:
        return "ready_disabled"
    if not credential_configured:
        return "ready_missing_credential"
    if not config.provider_terms_reviewed:
        return "ready_terms_review_required"
    return "trial_active"


def build_headers(token: str, *, client_api_id: str = CLIENT_API_ID) -> dict[str, str]:
    clean_token = token.strip()
    if not clean_token:
        raise ValueError("unusual_whales_token_missing")
    if any(character.isspace() or ord(character) < 33 for character in clean_token):
        raise ValueError("unusual_whales_token_invalid")
    if client_api_id != CLIENT_API_ID:
        raise ValueError("unusual_whales_client_api_id_invalid")
    return {
        "Authorization": f"Bearer {clean_token}",
        "Accept": "application/json",
        "UW-CLIENT-API-ID": client_api_id,
        "User-Agent": "Qadam-Historical-Research/1.0 read-only",
    }


def _validate_symbol(symbol: str | None, allowlist: tuple[str, ...]) -> str:
    candidate = str(symbol or "").strip().upper()
    if not SYMBOL_PATTERN.fullmatch(candidate):
        raise ValueError("unusual_whales_symbol_invalid")
    if candidate not in allowlist:
        raise ValueError("unusual_whales_symbol_not_allowlisted")
    return candidate


def build_request_url(
    endpoint_key: str,
    *,
    params: Mapping[str, Any] | None = None,
    symbol: str | None = None,
    function: str | None = None,
    symbol_allowlist: tuple[str, ...] = DEFAULT_SYMBOLS,
) -> str:
    if endpoint_key not in ENDPOINTS:
        raise ValueError("unusual_whales_endpoint_not_allowlisted")
    spec = ENDPOINTS[endpoint_key]
    active_params = dict(params or {})
    unknown = sorted(set(active_params) - spec.allowed_query_params)
    if unknown:
        raise ValueError(f"unusual_whales_query_param_not_allowlisted:{','.join(unknown)}")
    if spec.maximum_limit is not None and "limit" in active_params:
        limit = int(active_params["limit"])
        if limit < 1 or limit > spec.maximum_limit:
            raise ValueError("unusual_whales_limit_out_of_range")
    if "ticker_symbol" in active_params:
        tickers = [
            _validate_symbol(value, symbol_allowlist)
            for value in str(active_params["ticker_symbol"]).split(",")
            if value.strip()
        ]
        if not tickers:
            raise ValueError("unusual_whales_ticker_list_empty")
        active_params["ticker_symbol"] = ",".join(tickers)
    if "date" in active_params:
        try:
            active_params["date"] = date.fromisoformat(str(active_params["date"])).isoformat()
        except ValueError as exc:
            raise ValueError("unusual_whales_market_date_invalid") from exc
    if active_params.get("order") not in {None, "asc", "desc"}:
        raise ValueError("unusual_whales_order_invalid")
    if active_params.get("order_by") not in {
        None,
        "executed_at",
        "trf_executed_at",
        "premium",
        "size",
        "volume",
    }:
        raise ValueError("unusual_whales_order_by_invalid")
    path = spec.path_template
    if spec.requires_symbol:
        ticker = _validate_symbol(symbol, symbol_allowlist)
        path = path.replace("{ticker}", quote(ticker, safe=""))
    if spec.requires_function:
        active_function = str(function or "").strip().upper()
        if active_function not in TECHNICAL_FUNCTIONS:
            raise ValueError("unusual_whales_technical_function_not_allowlisted")
        path = path.replace("{function}", quote(active_function, safe=""))
    query = urlencode(active_params, doseq=True)
    return f"{BASE_URL}{path}{'?' + query if query else ''}"


def _records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        return [data]
    return [payload] if payload else []


def _number(value: Any) -> float | int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if value == value else None
    if isinstance(value, str):
        try:
            parsed = float(value.replace(",", ""))
        except ValueError:
            return None
        return int(parsed) if parsed.is_integer() else parsed
    return None


def _event_at(record: dict[str, Any], fetched_at: str) -> str:
    for key in TIME_FIELDS:
        value = record.get(key)
        if isinstance(value, (str, int, float)) and str(value).strip():
            return str(value)
    return fetched_at


def _symbol(record: dict[str, Any], fallback: str | None) -> str:
    for key in SYMBOL_FIELDS:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().upper()
    return fallback or "US_OPTIONS_MARKET"


def _parse_timestamp(value: str) -> datetime | None:
    text = value.strip()
    if not text:
        return None
    if text.isdigit():
        seconds = int(text)
        if seconds > 10_000_000_000:
            seconds //= 1000
        try:
            return datetime.fromtimestamp(seconds, timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        text += "T00:00:00+00:00"
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _available_at(event_at: str, fetched_at: str) -> tuple[str, str]:
    event_dt = _parse_timestamp(event_at)
    if event_dt is None:
        return fetched_at, "retrieval_time_fallback"
    if len(event_at.strip()) == 10 and event_at[4] == "-" and event_at[7] == "-":
        conservative = event_dt + timedelta(days=1)
        return conservative.isoformat(), "provider_market_date_end_of_day_proxy"
    return event_dt.isoformat(), "provider_event_timestamp"


def _feature_values(record: dict[str, Any]) -> dict[str, float | int | bool]:
    features: dict[str, float | int | bool] = {}
    excluded = set(TIME_FIELDS) | set(SYMBOL_FIELDS) | set(DIMENSION_FIELDS) | {
        "id",
        "option_symbol",
        "contract",
    }
    for key, value in record.items():
        if key in excluded:
            continue
        if isinstance(value, bool):
            features[key] = value
            continue
        numeric = _number(value)
        if numeric is not None:
            features[key] = numeric
    return features


def _derived_features(endpoint_key: str, features: dict[str, Any]) -> dict[str, float]:
    derived: dict[str, float] = {}
    if endpoint_key == "market_tide":
        calls = _number(features.get("net_call_premium"))
        puts = _number(features.get("net_put_premium"))
        if calls is not None and puts is not None:
            derived["net_options_premium"] = float(calls) + float(puts)
            denominator = abs(float(calls)) + abs(float(puts))
            if denominator:
                derived["call_put_premium_balance"] = (float(calls) + float(puts)) / denominator
    elif endpoint_key == "flow_alerts":
        ask = _number(features.get("total_ask_side_prem"))
        bid = _number(features.get("total_bid_side_prem"))
        if ask is not None and bid is not None:
            derived["ask_minus_bid_premium"] = float(ask) - float(bid)
    elif endpoint_key == "options_volume":
        calls = _number(features.get("call_volume"))
        puts = _number(features.get("put_volume"))
        if calls not in {None, 0} and puts is not None:
            derived["put_call_volume_ratio"] = float(puts) / float(calls)
    return derived


def normalize_payload(
    endpoint_key: str,
    payload: Any,
    *,
    fetched_at: str,
    symbol: str | None = None,
    capture_id: str,
    access_expires_on: date = DEFAULT_ACCESS_EXPIRES_ON,
) -> list[dict[str, Any]]:
    spec = ENDPOINTS[endpoint_key]
    fetched_dt = _parse_timestamp(fetched_at)
    normalized: list[dict[str, Any]] = []
    for index, record in enumerate(_records(payload)):
        event_at = _event_at(record, fetched_at)
        event_dt = _parse_timestamp(event_at)
        available_at, availability_basis = _available_at(event_at, fetched_at)
        available_dt = _parse_timestamp(available_at)
        features = _feature_values(record)
        features.update(_derived_features(endpoint_key, features))
        dimensions = {
            key: record[key]
            for key in DIMENSION_FIELDS
            if isinstance(record.get(key), (str, int, float, bool))
        }
        instrument = _symbol(record, symbol)
        provider_identifier = (
            record.get("id")
            or record.get("option_chain")
            or record.get("option_symbol")
            or f"{event_at}:{index}"
        )
        fingerprint = json.dumps(
            {
                "endpoint": endpoint_key,
                "instrument": instrument,
                "provider_identifier": provider_identifier,
                "event_at": event_at,
                "features": features,
            },
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        point_in_time_safe = bool(
            event_dt
            and available_dt
            and fetched_dt
            and event_dt <= available_dt <= fetched_dt
        )
        normalized.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "unusual_whales_backtest_feature",
                "record_id": f"uw-feature:{hashlib.sha256(fingerprint.encode('utf-8')).hexdigest()[:24]}",
                "capture_id": capture_id,
                "provider": SOURCE_KEY,
                "source_key": SOURCE_KEY,
                "source_label": SOURCE_LABEL,
                "endpoint_key": endpoint_key,
                "feature_family": spec.feature_family,
                "strategy_roles": list(spec.strategy_roles),
                "instrument": instrument,
                "event_at": event_at,
                "available_at": available_at,
                "retrieved_at": fetched_at,
                "availability_basis": availability_basis,
                "features": features,
                "dimensions": dimensions,
                "point_in_time_safe": point_in_time_safe,
                "backtest_feature_eligible": point_in_time_safe and bool(features),
                "historical_research_only": True,
                "trial_access_expires_on": access_expires_on.isoformat(),
                "source_quorum_allowed": False,
                "trade_candidate_creation_allowed": False,
                "execution_allowed": False,
                "paper_order_allowed": False,
                "broker_write_allowed": False,
                "proof_credit_allowed": False,
            }
        )
    return normalized


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


class UnusualWhalesResearchStore:
    def __init__(
        self,
        *,
        root: Path | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.root = (root or RESEARCH_ROOT).resolve()
        if not self.root.is_relative_to((ROOT / "data").resolve()):
            raise ValueError("unusual_whales_store_outside_data")
        self.runtime = runtime_dir(settings)
        self.manifest_path = self.root / "manifests" / "capture_manifest.json"
        self.usage_path = self.root / "manifests" / "request_usage.json"

    def load_manifest(self) -> dict[str, Any]:
        return _read_json(self.manifest_path)

    def reserve_request(self, *, local_date: str, daily_budget: int) -> int:
        usage = _read_json(self.usage_path)
        counts = usage.get("counts") if isinstance(usage.get("counts"), dict) else {}
        current = int(counts.get(local_date) or 0)
        if current >= daily_budget:
            raise RuntimeError("unusual_whales_daily_request_budget_exhausted")
        counts[local_date] = current + 1
        payload = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "unusual_whales_request_usage",
            "updated_at": now_iso(),
            "counts": counts,
            "secret_values_recorded": False,
            "authority": RESEARCH_AUTHORITY,
        }
        _atomic_write(self.usage_path, (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode())
        return counts[local_date]

    def write_capture(
        self,
        *,
        capture_id: str,
        endpoint_key: str,
        params: dict[str, Any],
        symbol: str | None,
        fetched_at: str,
        request_url: str,
        payload: Any,
        records: list[dict[str, Any]],
        retain_raw: bool,
        response_sha256: str,
    ) -> dict[str, Any]:
        partition = str(params.get("date") or fetched_at[:10])
        safe_partition = re.sub(r"[^0-9A-Za-z_.-]", "_", partition)
        raw_path = self.root / "raw" / f"endpoint={endpoint_key}" / f"date={safe_partition}" / f"{capture_id}.json"
        normalized_path = self.root / "normalized" / f"endpoint={endpoint_key}" / f"date={safe_partition}" / f"{capture_id}.jsonl"
        metadata_path = self.root / "metadata" / f"endpoint={endpoint_key}" / f"date={safe_partition}" / f"{capture_id}.json"
        if retain_raw:
            _atomic_write(raw_path, (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode())
        encoded_records = b"".join(
            (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
            for record in records
        )
        _atomic_write(normalized_path, encoded_records)
        event_times = [str(record.get("event_at")) for record in records if record.get("event_at")]
        feature_names = sorted(
            {
                str(name)
                for record in records
                for name in (record.get("features") or {})
            }
        )
        instruments = sorted({str(record.get("instrument")) for record in records if record.get("instrument")})
        metadata = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "unusual_whales_capture_metadata",
            "capture_id": capture_id,
            "provider": SOURCE_KEY,
            "endpoint_key": endpoint_key,
            "fetched_at": fetched_at,
            "request": {
                "method": "GET",
                "url": request_url,
                "params": params,
                "symbol": symbol,
                "authorization_header_recorded": False,
                "client_api_id_header_recorded": False,
            },
            "response_sha256": response_sha256,
            "parser_version": PARSER_VERSION,
            "raw_payload_retained": retain_raw,
            "raw_payload_path": str(raw_path.relative_to(ROOT)) if retain_raw else None,
            "normalized_path": str(normalized_path.relative_to(ROOT)),
            "normalized_sha256": hashlib.sha256(encoded_records).hexdigest(),
            "normalized_record_count": len(records),
            "backtest_eligible_record_count": sum(record.get("backtest_feature_eligible") is True for record in records),
            "point_in_time_safe_record_count": sum(record.get("point_in_time_safe") is True for record in records),
            "coverage_start": min(event_times) if event_times else None,
            "coverage_end": max(event_times) if event_times else None,
            "feature_names": feature_names,
            "instruments": instruments,
            "historical_research_only": True,
            "authority": RESEARCH_AUTHORITY,
        }
        _atomic_write(metadata_path, (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode())
        manifest = self.load_manifest()
        captures = manifest.get("captures") if isinstance(manifest.get("captures"), dict) else {}
        captures[capture_id] = metadata
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "unusual_whales_capture_manifest",
            "updated_at": now_iso(),
            "capture_count": len(captures),
            "captures": captures,
            "historical_research_only": True,
            "authority": RESEARCH_AUTHORITY,
        }
        _atomic_write(self.manifest_path, (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode())
        return metadata


Transport = Callable[[str, Mapping[str, str], float], tuple[int, bytes]]


def _default_transport(url: str, headers: Mapping[str, str], timeout_seconds: float) -> tuple[int, bytes]:
    request = Request(url, headers=dict(headers), method="GET")
    with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - fixed HTTPS host and allowlisted paths
        return int(getattr(response, "status", 200)), response.read()


class UnusualWhalesResearchAdapter:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        config: UnusualWhalesResearchConfig | None = None,
        store: UnusualWhalesResearchStore | None = None,
        transport: Transport | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self.settings = settings or Settings.from_env()
        self.config = config or UnusualWhalesResearchConfig.from_env()
        self.store = store or UnusualWhalesResearchStore(settings=self.settings)
        self.transport = transport or _default_transport
        self.now_provider = now_provider or (lambda: datetime.now(timezone.utc))

    def public_status(self) -> dict[str, Any]:
        credential = secret_status("UNUSUAL_WHALES_API_KEY", self.settings).configured
        now = _aware_now(self.now_provider())
        local_now = now.astimezone(ZoneInfo(self.config.timezone_name))
        state = access_state(self.config, credential_configured=credential, now=now)
        manifest = build_feature_manifest(self.store.load_manifest(), config=self.config, now=now)
        return {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "unusual_whales_research_status",
            "generated_at": now.isoformat(),
            "status": state,
            "provider": "Unusual Whales",
            "mode": "historical_research_only",
            "adapter_implemented": True,
            "enabled": self.config.enabled,
            "credential_state": "configured" if credential else "not_configured",
            "provider_terms_reviewed": self.config.provider_terms_reviewed,
            "raw_retention_allowed": self.config.raw_retention_allowed,
            "access_expires_on": self.config.access_expires_on.isoformat(),
            "access_timezone": self.config.timezone_name,
            "days_remaining": max((self.config.access_expires_on - local_now.date()).days, 0),
            "fresh_ingestion_allowed": state == "trial_active",
            "historical_backtest_allowed": manifest["backtest_feature_ready"],
            "post_expiry_mode": "historical_archive_only",
            "normalized_record_count": manifest["normalized_record_count"],
            "backtest_eligible_record_count": manifest["backtest_eligible_record_count"],
            "coverage_start": manifest["coverage_start"],
            "coverage_end": manifest["coverage_end"],
            "source_quorum_allowed": False,
            "execution_allowed": False,
            "proof_credit_allowed": False,
            "boundary": (
                "Unusual Whales is an expiring read-only historical research provider. "
                "It cannot satisfy catalyst quorum, approve risk, create trades, or route orders."
            ),
            "authority": RESEARCH_AUTHORITY,
        }

    def capture(
        self,
        endpoint_key: str,
        *,
        params: Mapping[str, Any] | None = None,
        symbol: str | None = None,
        function: str | None = None,
        allow_network: bool = False,
        provider_terms_reviewed: bool = False,
        retain_raw: bool = False,
        timeout_seconds: float = 20.0,
    ) -> dict[str, Any]:
        now = _aware_now(self.now_provider())
        token = secret_value("UNUSUAL_WHALES_API_KEY", self.settings)
        state = access_state(self.config, credential_configured=bool(token), now=now)
        if not allow_network:
            return self._blocked_result(endpoint_key, state="network_not_explicitly_allowed")
        if state == "expired_archive_only":
            return self._blocked_result(endpoint_key, state=state)
        if state in {"ready_disabled", "ready_missing_credential"}:
            return self._blocked_result(endpoint_key, state=state)
        if self.config.client_api_id != CLIENT_API_ID:
            return self._blocked_result(endpoint_key, state="client_api_id_invalid")
        terms_ok = provider_terms_reviewed or self.config.provider_terms_reviewed
        if not terms_ok:
            return self._blocked_result(endpoint_key, state="provider_terms_review_required")
        url = build_request_url(
            endpoint_key,
            params=params,
            symbol=symbol,
            function=function,
            symbol_allowlist=self.config.symbol_allowlist,
        )
        request_params = dict(params or {})
        capture_fingerprint = json.dumps(
            {
                "endpoint": endpoint_key,
                "params": request_params,
                "symbol": symbol,
                "function": function,
            },
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        try:
            headers = build_headers(token or "", client_api_id=self.config.client_api_id)
        except ValueError as exc:
            return self._blocked_result(endpoint_key, state=str(exc))
        local_date = now.astimezone(ZoneInfo(self.config.timezone_name)).date().isoformat()
        self.store.reserve_request(
            local_date=local_date,
            daily_budget=self.config.daily_request_budget,
        )
        try:
            status_code, raw = self.transport(url, headers, timeout_seconds)
            if status_code != 200:
                return self._blocked_result(
                    endpoint_key,
                    state=f"provider_http_{status_code}",
                    network_called=True,
                )
            payload = json.loads(raw)
        except HTTPError as exc:
            provider_state = "credential_expired_or_denied" if exc.code in {401, 403} else (
                "rate_limited" if exc.code == 429 else f"provider_http_{exc.code}"
            )
            return self._blocked_result(endpoint_key, state=provider_state, network_called=True)
        except (URLError, TimeoutError) as exc:
            return self._blocked_result(
                endpoint_key,
                state=f"provider_transport_error:{exc.__class__.__name__}",
                network_called=True,
            )
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            return self._blocked_result(
                endpoint_key,
                state=f"provider_payload_error:{exc.__class__.__name__}",
                network_called=True,
            )
        fetched_at = now.isoformat()
        response_sha256 = hashlib.sha256(raw).hexdigest()
        capture_id = "uw-capture:" + hashlib.sha256(
            f"{capture_fingerprint}:{response_sha256}".encode("utf-8")
        ).hexdigest()[:24]
        records = normalize_payload(
            endpoint_key,
            payload,
            fetched_at=fetched_at,
            symbol=str(symbol).upper() if symbol else None,
            capture_id=capture_id,
            access_expires_on=self.config.access_expires_on,
        )
        metadata = self.store.write_capture(
            capture_id=capture_id,
            endpoint_key=endpoint_key,
            params=request_params,
            symbol=str(symbol).upper() if symbol else None,
            fetched_at=fetched_at,
            request_url=url,
            payload=payload,
            records=records,
            retain_raw=retain_raw and self.config.raw_retention_allowed,
            response_sha256=response_sha256,
        )
        write_public_artifacts(self.settings, self.public_status(), self.store.load_manifest(), self.config, now)
        return {
            "status": "captured",
            "endpoint_key": endpoint_key,
            "capture_id": capture_id,
            "normalized_record_count": len(records),
            "backtest_eligible_record_count": metadata["backtest_eligible_record_count"],
            "coverage_start": metadata["coverage_start"],
            "coverage_end": metadata["coverage_end"],
            "metadata": metadata,
            "records": records,
            "network_called": True,
            "execution_allowed": False,
            "proof_credit_allowed": False,
        }

    @staticmethod
    def _blocked_result(
        endpoint_key: str,
        *,
        state: str,
        network_called: bool = False,
    ) -> dict[str, Any]:
        return {
            "status": "blocked",
            "endpoint_key": endpoint_key,
            "reason": state,
            "normalized_record_count": 0,
            "backtest_eligible_record_count": 0,
            "records": [],
            "network_called": network_called,
            "execution_allowed": False,
            "proof_credit_allowed": False,
        }


def build_feature_manifest(
    capture_manifest: dict[str, Any],
    *,
    config: UnusualWhalesResearchConfig | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    active = config or UnusualWhalesResearchConfig.from_env()
    captures = capture_manifest.get("captures") if isinstance(capture_manifest.get("captures"), dict) else {}
    records = [record for record in captures.values() if isinstance(record, dict)]
    coverage_starts = [str(record["coverage_start"]) for record in records if record.get("coverage_start")]
    coverage_ends = [str(record["coverage_end"]) for record in records if record.get("coverage_end")]
    feature_names = sorted(
        {
            str(name)
            for record in records
            for name in record.get("feature_names", [])
        }
    )
    instruments = sorted(
        {
            str(symbol)
            for record in records
            for symbol in record.get("instruments", [])
        }
    )
    endpoint_counts: dict[str, int] = {}
    for record in records:
        key = str(record.get("endpoint_key") or "unknown")
        endpoint_counts[key] = endpoint_counts.get(key, 0) + 1
    eligible = sum(int(record.get("backtest_eligible_record_count") or 0) for record in records)
    normalized = sum(int(record.get("normalized_record_count") or 0) for record in records)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "unusual_whales_backtest_feature_manifest",
        "generated_at": _aware_now(now).isoformat(),
        "status": "ready" if eligible else "ready_no_captured_features",
        "provider": SOURCE_KEY,
        "mode": "historical_research_only",
        "access_expires_on": active.access_expires_on.isoformat(),
        "post_expiry_mode": "historical_archive_only",
        "capture_count": len(records),
        "normalized_record_count": normalized,
        "backtest_eligible_record_count": eligible,
        "backtest_feature_ready": eligible > 0,
        "point_in_time_availability_required": True,
        "coverage_start": min(coverage_starts) if coverage_starts else None,
        "coverage_end": max(coverage_ends) if coverage_ends else None,
        "endpoint_counts": dict(sorted(endpoint_counts.items())),
        "feature_names": feature_names,
        "instruments": instruments,
        "dataset_paths": sorted(
            {
                str(record.get("normalized_path"))
                for record in records
                if record.get("normalized_path")
            }
        ),
        "required_backtest_comparisons": [
            "qadam_core_without_unusual_whales",
            "qadam_core_plus_unusual_whales",
            "unusual_whales_only",
            "time_shifted_negative_control",
            "shuffled_negative_control",
        ],
        "source_quorum_allowed": False,
        "strategy_mutation_allowed": False,
        "execution_allowed": False,
        "proof_credit_allowed": False,
        "authority": RESEARCH_AUTHORITY,
    }


def write_public_artifacts(
    settings: Settings | None,
    status: dict[str, Any],
    capture_manifest: dict[str, Any],
    config: UnusualWhalesResearchConfig,
    now: datetime | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    feature_manifest = build_feature_manifest(capture_manifest, config=config, now=now)
    store = AtomicArtifactStore(runtime_dir(settings))
    store.write_json(STATUS_ARTIFACT, status)
    store.write_json(FEATURE_MANIFEST_ARTIFACT, feature_manifest)
    return status, feature_manifest


def refresh_unusual_whales_public_artifacts(
    settings: Settings | None = None,
    *,
    config: UnusualWhalesResearchConfig | None = None,
    root: Path | None = None,
    now: datetime | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    active = config or UnusualWhalesResearchConfig.from_env()
    active_now = _aware_now(now)
    adapter = UnusualWhalesResearchAdapter(
        settings=settings,
        config=active,
        store=UnusualWhalesResearchStore(root=root, settings=settings),
        now_provider=lambda: active_now,
    )
    status = adapter.public_status()
    return write_public_artifacts(
        settings,
        status,
        adapter.store.load_manifest(),
        active,
        active_now,
    )


def load_backtest_feature_records(
    feature_manifest: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Load only normalized datasets registered by the public feature manifest."""
    records_by_id: dict[str, dict[str, Any]] = {}
    normalized_root = (RESEARCH_ROOT / "normalized").resolve()
    for relative_path in feature_manifest.get("dataset_paths", []):
        path = (ROOT / str(relative_path)).resolve()
        if not path.is_relative_to(normalized_root) or path.suffix != ".jsonl":
            raise ValueError("unusual_whales_feature_dataset_path_invalid")
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError("unusual_whales_feature_dataset_invalid_jsonl") from exc
                if not isinstance(record, dict) or record.get("source_key") != SOURCE_KEY:
                    raise ValueError("unusual_whales_feature_dataset_record_invalid")
                record_id = str(record.get("record_id") or "")
                if not record_id:
                    raise ValueError("unusual_whales_feature_record_id_missing")
                records_by_id[record_id] = record
    return [records_by_id[key] for key in sorted(records_by_id)]


def select_point_in_time_features(
    records: Iterable[Mapping[str, Any]],
    *,
    instrument: str,
    scoring_as_of: str,
    maximum_records: int = 5_000,
) -> list[dict[str, Any]]:
    """Return provider rows that were available by a historical scoring time."""
    as_of = _parse_timestamp(scoring_as_of)
    if as_of is None:
        raise ValueError("unusual_whales_scoring_as_of_invalid")
    if maximum_records < 1:
        raise ValueError("unusual_whales_maximum_records_invalid")
    active_instrument = instrument.strip().upper()
    selected: list[dict[str, Any]] = []
    for value in records:
        record = dict(value)
        record_instrument = str(record.get("instrument") or "").upper()
        available_at = _parse_timestamp(str(record.get("available_at") or ""))
        if record.get("backtest_feature_eligible") is not True:
            continue
        if record_instrument not in {active_instrument, "US_OPTIONS_MARKET"}:
            continue
        if available_at is None or available_at > as_of:
            continue
        selected.append(record)
    selected.sort(
        key=lambda record: (
            str(record.get("available_at") or ""),
            str(record.get("event_at") or ""),
            str(record.get("record_id") or ""),
        )
    )
    return selected[-maximum_records:]


def build_point_in_time_feature_snapshot(
    records: Iterable[Mapping[str, Any]],
    *,
    instrument: str,
    scoring_as_of: str,
    maximum_records: int = 5_000,
) -> dict[str, Any]:
    selected = select_point_in_time_features(
        records,
        instrument=instrument,
        scoring_as_of=scoring_as_of,
        maximum_records=maximum_records,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "unusual_whales_point_in_time_feature_snapshot",
        "provider": SOURCE_KEY,
        "instrument": instrument.strip().upper(),
        "scoring_as_of": scoring_as_of,
        "record_count": len(selected),
        "feature_families": sorted(
            {str(record.get("feature_family")) for record in selected if record.get("feature_family")}
        ),
        "records": selected,
        "point_in_time_asof_join_enforced": True,
        "future_feature_access_allowed": False,
        "historical_research_only": True,
        "source_quorum_allowed": False,
        "execution_allowed": False,
        "proof_credit_allowed": False,
        "authority": RESEARCH_AUTHORITY,
    }


def validate_unusual_whales_contract(
    status: dict[str, Any],
    feature_manifest: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if status.get("adapter_implemented") is not True:
        errors.append("unusual_whales_adapter_not_implemented")
    if status.get("access_expires_on") != DEFAULT_ACCESS_EXPIRES_ON.isoformat():
        errors.append("unusual_whales_expiry_contract_changed")
    if status.get("source_quorum_allowed") is not False:
        errors.append("unusual_whales_source_quorum_enabled")
    if status.get("execution_allowed") is not False:
        errors.append("unusual_whales_execution_enabled")
    if status.get("proof_credit_allowed") is not False:
        errors.append("unusual_whales_proof_credit_enabled")
    if feature_manifest.get("point_in_time_availability_required") is not True:
        errors.append("unusual_whales_point_in_time_requirement_missing")
    if feature_manifest.get("strategy_mutation_allowed") is not False:
        errors.append("unusual_whales_strategy_mutation_enabled")
    comparisons = set(feature_manifest.get("required_backtest_comparisons", []))
    if {
        "qadam_core_without_unusual_whales",
        "qadam_core_plus_unusual_whales",
        "unusual_whales_only",
        "time_shifted_negative_control",
        "shuffled_negative_control",
    } - comparisons:
        errors.append("unusual_whales_backtest_ablation_incomplete")
    return errors
