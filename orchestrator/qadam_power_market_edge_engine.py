"""Provider-backed power-market research and emerging-strategy admission.

This module adds a mechanism-first research sleeve without creating a second
execution path. CAISO OASIS and Alpaca market-data reads are normalized into a
bounded historical tape, tested chronologically, and exposed to Strategy
Foundry only when the frozen experimental-paper policy is satisfied.

The module never submits an order, approves risk, grants proof credit, changes
live-capital settings, or treats a provisional result as a validated edge.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import random
from statistics import fmean, pstdev
import subprocess
import time
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
import zipfile

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    authority_flags,
    canonical_json,
    now_iso,
    read_json,
    runtime_dir,
    sha256_json,
    unique_errors,
    validate_authority,
    write_json_atomic,
)
from orchestrator.qadam_wave_b_common import record_set_hash, stable_id
from orchestrator.secrets import secret_value


SCHEMA_VERSION = "qadam_power_market_edge_engine.v1"
POLICY_VERSION = "qadam-power-market-research.1-frozen"

PRIMARY_ARTIFACT = "qadam_power_market_edge_engine.json"
MANIFEST_ARTIFACT = "qadam_power_market_acquisition_manifest.json"
BACKTEST_ARTIFACT = "qadam_power_market_backtest.json"
STRATEGY_ARTIFACT = "qadam_power_market_strategy_registry.json"
PATTERN_SCORES_ARTIFACT = "qadam_power_market_pattern_scores.jsonl"
CONTEXT_ARTIFACT = "qadam_power_market_context.json"
DASHBOARD_ARTIFACT = "qadam_power_market_dashboard_summary.json"
CHECK_ARTIFACT = "qadam_power_market_edge_engine_checks.json"

RESEARCH_ROOT = ROOT / "data" / "research" / "power_market"
RAW_ROOT = RESEARCH_ROOT / "raw"
NORMALIZED_ROOT = RESEARCH_ROOT / "normalized"
DAILY_EVIDENCE_PATH = NORMALIZED_ROOT / "power_market_daily_evidence.jsonl"
PROXY_BARS_PATH = NORMALIZED_ROOT / "alpaca_proxy_bars.jsonl"

CAISO_BASE_URL = "https://oasis.caiso.com/oasisapi/SingleZip"
ALPACA_DATA_BASE_URL = "https://data.alpaca.markets/v2"
CAISO_NODES = (
    "TH_NP15_GEN-APND",
    "TH_SP15_GEN-APND",
    "TH_ZP26_GEN-APND",
)
POWER_PROXY_SYMBOLS = ("CEG", "VST", "NRG", "TLN", "XLU", "GRID", "UNG")
PRODUCER_PROXY_SYMBOLS = frozenset({"CEG", "VST", "NRG", "TLN"})
STRATEGY_FAMILY_ID = "power_scarcity_congestion"

POWER_RESEARCH_SOURCE_FEEDS = (
    {
        "source_key": "caiso_oasis_day_ahead_lmp",
        "source_name": "CAISO Day-Ahead Electricity Prices",
        "description": (
            "Hourly day-ahead locational electricity prices used to measure expected "
            "scarcity and regional congestion before the following market session."
        ),
        "provider_url": "https://www.caiso.com/todays-outlook/prices",
    },
    {
        "source_key": "caiso_oasis_real_time_lmp",
        "source_name": "CAISO Real-Time Electricity Prices",
        "description": (
            "Real-time locational prices used to measure whether actual grid conditions "
            "diverged from the day-ahead plan."
        ),
        "provider_url": "https://www.caiso.com/todays-outlook/prices",
    },
    {
        "source_key": "caiso_oasis_demand_forecast",
        "source_name": "CAISO Electricity Demand Forecast",
        "description": (
            "The grid operator's day-ahead demand forecast, used to estimate how tight "
            "the balance between expected consumption and available supply may become."
        ),
        "provider_url": "https://www.caiso.com/todays-outlook/demand",
    },
    {
        "source_key": "caiso_oasis_renewable_forecast",
        "source_name": "CAISO Renewable Generation Forecast",
        "description": (
            "Day-ahead renewable-generation expectations used to identify supply "
            "shortfalls that may require more expensive marginal generation."
        ),
        "provider_url": "https://www.caiso.com/todays-outlook/supply",
    },
)

CAISO_DATASETS: dict[str, dict[str, str]] = {
    "dam_lmp": {
        "queryname": "PRC_LMP",
        "version": "12",
        "market_run_id": "DAM",
    },
    "rtm_lmp": {
        "queryname": "PRC_INTVL_LMP",
        "version": "3",
        "market_run_id": "RTM",
    },
    "demand_forecast": {
        "queryname": "SLD_FCST",
        "version": "1",
        "market_run_id": "DAM",
    },
    "renewable_forecast": {
        "queryname": "SLD_REN_FCST",
        "version": "1",
        "market_run_id": "DAM",
    },
}

METHODS = (
    "scarcity_pressure",
    "congestion_divergence",
    "renewable_shortfall",
    "day_ahead_price_pressure",
)
HORIZONS = (1, 3)

MAX_RAW_RESPONSE_BYTES = 25 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 200 * 1024 * 1024
MAX_RESEARCH_STORE_BYTES = 8 * 1024 * 1024 * 1024
MIN_PROVISIONAL_HOLDOUT_EVENTS = 20
MIN_VALIDATED_HOLDOUT_EVENTS = 30
PARTITION_RETRY_BASE_SECONDS = 900
PARTITION_RETRY_MAX_SECONDS = 21_600
ROUND_TRIP_COST_RATE = 0.0015
CURRENT_CONTEXT_MAX_AGE_SECONDS = 172_800


@dataclass(frozen=True)
class AcquisitionResult:
    raw: bytes
    rows: list[dict[str, Any]]
    metadata: dict[str, Any]


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _mean(values: Iterable[float]) -> float | None:
    clean = [value for value in values if math.isfinite(value)]
    return fmean(clean) if clean else None


def _quantile(values: Iterable[float], probability: float) -> float | None:
    clean = sorted(value for value in values if math.isfinite(value))
    if not clean:
        return None
    if len(clean) == 1:
        return clean[0]
    position = max(0.0, min(1.0, probability)) * (len(clean) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return clean[lower]
    weight = position - lower
    return clean[lower] * (1.0 - weight) + clean[upper] * weight


def _safe_ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in {None, 0.0}:
        return None
    return numerator / denominator


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _write_jsonl_atomic(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    encoded = "".join(canonical_json(row) + "\n" for row in rows).encode("utf-8")
    _atomic_bytes(path, encoded)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _directory_size(path: Path) -> int:
    total = 0
    if not path.exists():
        return total
    for candidate in path.rglob("*"):
        if candidate.is_file():
            try:
                total += candidate.stat().st_size
            except OSError:
                continue
    return total


def _month_windows(start: date, end_exclusive: date) -> list[tuple[date, date]]:
    cursor = date(start.year, start.month, 1)
    windows: list[tuple[date, date]] = []
    while cursor < end_exclusive:
        next_month = (
            date(cursor.year + 1, 1, 1)
            if cursor.month == 12
            else date(cursor.year, cursor.month + 1, 1)
        )
        windows.append((max(cursor, start), min(next_month, end_exclusive)))
        cursor = next_month
    return windows


def _year_windows(start: date, end_exclusive: date) -> list[tuple[date, date]]:
    windows: list[tuple[date, date]] = []
    for year in range(start.year, end_exclusive.year + 1):
        left = max(start, date(year, 1, 1))
        right = min(end_exclusive, date(year + 1, 1, 1))
        if left < right:
            windows.append((left, right))
    return windows


def _week_windows(start: date, end_exclusive: date) -> list[tuple[date, date]]:
    windows: list[tuple[date, date]] = []
    cursor = start
    while cursor < end_exclusive:
        right = min(cursor + timedelta(days=7), end_exclusive)
        windows.append((cursor, right))
        cursor = right
    return windows


def _caiso_timestamp(day: date) -> str:
    return f"{day.isoformat().replace('-', '')}T07:00-0000"


def _caiso_url(dataset: str, start: date, end_exclusive: date) -> str:
    definition = CAISO_DATASETS[dataset]
    params: dict[str, str] = {
        "resultformat": "6",
        "queryname": definition["queryname"],
        "version": definition["version"],
        "market_run_id": definition["market_run_id"],
        "startdatetime": _caiso_timestamp(start),
        "enddatetime": _caiso_timestamp(end_exclusive),
    }
    if dataset in {"dam_lmp", "rtm_lmp"}:
        params["node"] = ",".join(CAISO_NODES)
    return f"{CAISO_BASE_URL}?{urlencode(params)}"


def _fetch_bytes(url: str, *, headers: dict[str, str], timeout_seconds: int) -> bytes:
    request = Request(url, headers=headers)
    with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
        status = int(getattr(response, "status", 200))
        if status != 200:
            raise RuntimeError(f"provider_http_status:{status}")
        payload = response.read(MAX_RAW_RESPONSE_BYTES + 1)
    if len(payload) > MAX_RAW_RESPONSE_BYTES:
        raise RuntimeError("provider_response_exceeded_byte_ceiling")
    return payload


def _fetch_caiso_bytes(url: str, *, timeout_seconds: int) -> tuple[bytes, str]:
    """Use verified Python TLS, then the macOS trust store via curl.

    Some Mac Python distributions do not inherit user/system certificate roots.
    The fallback keeps certificate verification enabled and is CAISO-only, so
    no broker credential can be exposed through process arguments.
    """

    headers = {"Accept": "application/zip", "User-Agent": "Qadam-Research/1.0 read-only"}
    try:
        return _fetch_bytes(url, headers=headers, timeout_seconds=timeout_seconds), "urllib_verified_tls"
    except URLError as exc:
        if "CERTIFICATE_VERIFY_FAILED" not in str(exc):
            raise
    completed = subprocess.run(
        [
            "curl",
            "--fail",
            "--silent",
            "--show-error",
            "--location",
            "--max-time",
            str(timeout_seconds),
            "--max-filesize",
            str(MAX_RAW_RESPONSE_BYTES),
            "--header",
            "Accept: application/zip",
            "--header",
            "User-Agent: Qadam-Research/1.0 read-only",
            url,
        ],
        check=False,
        capture_output=True,
        timeout=timeout_seconds + 5,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"caiso_curl_verified_tls_failed:{completed.returncode}:{detail}")
    if not completed.stdout or len(completed.stdout) > MAX_RAW_RESPONSE_BYTES:
        raise RuntimeError("caiso_curl_response_invalid_or_over_byte_ceiling")
    return completed.stdout, "curl_system_verified_tls"


def _zip_csv_rows(raw: bytes) -> tuple[list[dict[str, Any]], str]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile as exc:
        raise RuntimeError("provider_response_not_valid_zip") from exc
    members = [member for member in archive.infolist() if member.filename.lower().endswith(".csv")]
    if len(members) != 1:
        error_members = [member for member in archive.infolist() if member.filename.lower().endswith(".xml")]
        detail = ""
        if error_members:
            detail = archive.read(error_members[0]).decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"provider_zip_csv_member_invalid:{len(members)}:{detail}")
    member = members[0]
    if member.file_size > MAX_UNCOMPRESSED_BYTES:
        raise RuntimeError("provider_zip_uncompressed_byte_ceiling_exceeded")
    text = archive.read(member).decode("utf-8-sig")
    rows = [dict(row) for row in csv.DictReader(io.StringIO(text))]
    if not rows:
        raise RuntimeError("provider_csv_empty")
    return rows, member.filename


def fetch_caiso_partition(
    dataset: str,
    start: date,
    end_exclusive: date,
    *,
    timeout_seconds: int = 90,
) -> AcquisitionResult:
    """Fetch one bounded read-only CAISO OASIS partition."""

    if dataset not in CAISO_DATASETS:
        raise ValueError(f"unsupported_caiso_dataset:{dataset}")
    if start >= end_exclusive or (end_exclusive - start).days > 31:
        raise ValueError("caiso_partition_window_invalid")
    url = _caiso_url(dataset, start, end_exclusive)
    fetched_at = now_iso()
    raw, transport = _fetch_caiso_bytes(url, timeout_seconds=timeout_seconds)
    rows, member = _zip_csv_rows(raw)
    return AcquisitionResult(
        raw=raw,
        rows=rows,
        metadata={
            "provider": "CAISO OASIS",
            "dataset": dataset,
            "fetched_at": fetched_at,
            "start": start.isoformat(),
            "end_exclusive": end_exclusive.isoformat(),
            "row_count": len(rows),
            "zip_member": member,
            "raw_sha256": _sha256_bytes(raw),
            "request_url_sha256": hashlib.sha256(url.encode("utf-8")).hexdigest(),
            "credentials_used": False,
            "provider_backed": True,
            "transport": transport,
            "tls_verification_disabled": False,
        },
    )


def fetch_alpaca_bars(
    symbol: str,
    start: date,
    end_exclusive: date,
    *,
    api_key: str,
    api_secret: str,
    timeout_seconds: int = 45,
) -> AcquisitionResult:
    """Fetch adjusted IEX daily bars without exposing credentials."""

    if symbol not in POWER_PROXY_SYMBOLS:
        raise ValueError(f"power_proxy_not_allowlisted:{symbol}")
    page_token: str | None = None
    pages: list[dict[str, Any]] = []
    request_hashes: list[str] = []
    while True:
        params: dict[str, Any] = {
            "timeframe": "1Day",
            "start": f"{start.isoformat()}T00:00:00Z",
            "end": f"{end_exclusive.isoformat()}T00:00:00Z",
            "limit": 10000,
            "adjustment": "all",
            "feed": "iex",
            "sort": "asc",
        }
        if page_token:
            params["page_token"] = page_token
        url = f"{ALPACA_DATA_BASE_URL}/stocks/{quote(symbol, safe='')}/bars?{urlencode(params)}"
        raw_page = _fetch_bytes(
            url,
            headers={
                "APCA-API-KEY-ID": api_key,
                "APCA-API-SECRET-KEY": api_secret,
                "Accept": "application/json",
                "User-Agent": "Qadam-Research/1.0 read-only",
            },
            timeout_seconds=timeout_seconds,
        )
        payload = json.loads(raw_page)
        if not isinstance(payload, dict):
            raise RuntimeError("alpaca_bars_payload_not_object")
        pages.append(payload)
        request_hashes.append(hashlib.sha256(url.encode("utf-8")).hexdigest())
        token = payload.get("next_page_token")
        if not isinstance(token, str) or not token.strip():
            break
        if len(pages) >= 100:
            raise RuntimeError("alpaca_bars_pagination_ceiling_exceeded")
        page_token = token.strip()
    fetched_at = now_iso()
    rows: list[dict[str, Any]] = []
    for page in pages:
        page_rows = page.get("bars")
        if page_rows is None:
            continue
        if not isinstance(page_rows, list):
            raise RuntimeError("alpaca_bars_field_not_array_or_null")
        for row in page_rows:
            if not isinstance(row, dict) or not row.get("t"):
                continue
            rows.append(
                {
                    "symbol": symbol,
                    "date": str(row["t"])[:10],
                    "observed_at": row["t"],
                    "available_at": fetched_at,
                    "open": _float(row.get("o")),
                    "high": _float(row.get("h")),
                    "low": _float(row.get("l")),
                    "close": _float(row.get("c")),
                    "volume": _float(row.get("v")),
                    "trade_count": row.get("n"),
                    "vwap": _float(row.get("vw")),
                    "provider": "Alpaca Market Data IEX",
                    "provider_backed": True,
                }
            )
    rows.sort(key=lambda row: str(row.get("date") or ""))
    raw = canonical_json({"pages": pages}).encode("utf-8")
    return AcquisitionResult(
        raw=raw,
        rows=rows,
        metadata={
            "provider": "Alpaca Market Data IEX",
            "symbol": symbol,
            "fetched_at": fetched_at,
            "start": start.isoformat(),
            "end_exclusive": end_exclusive.isoformat(),
            "row_count": len(rows),
            "page_count": len(pages),
            "raw_sha256": _sha256_bytes(raw),
            "request_url_sha256": request_hashes,
            "credentials_used": True,
            "credentials_recorded": False,
            "provider_backed": True,
        },
    )


def fetch_alpaca_latest_quote(
    symbol: str,
    *,
    api_key: str,
    api_secret: str,
    timeout_seconds: int = 20,
) -> dict[str, Any]:
    if symbol not in POWER_PROXY_SYMBOLS:
        raise ValueError(f"power_proxy_not_allowlisted:{symbol}")
    url = f"{ALPACA_DATA_BASE_URL}/stocks/{quote(symbol, safe='')}/quotes/latest?feed=iex"
    raw = _fetch_bytes(
        url,
        headers={
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": api_secret,
            "Accept": "application/json",
            "User-Agent": "Qadam-Research/1.0 read-only",
        },
        timeout_seconds=timeout_seconds,
    )
    payload = json.loads(raw)
    quote_row = payload.get("quote") if isinstance(payload, dict) else None
    quote_row = quote_row if isinstance(quote_row, dict) else {}
    bid = _float(quote_row.get("bp"))
    ask = _float(quote_row.get("ap"))
    midpoint = (bid + ask) / 2.0 if bid is not None and ask is not None else None
    spread_bps = (
        ((ask - bid) / midpoint) * 10_000
        if midpoint not in {None, 0.0} and ask is not None and bid is not None
        else None
    )
    return {
        "symbol": symbol,
        "observed_at": quote_row.get("t") or now_iso(),
        "bid": bid,
        "ask": ask,
        "spread_bps": spread_bps,
        "provider": "Alpaca Market Data IEX",
        "provider_backed": True,
        "credentials_recorded": False,
    }


def _hour_key(row: dict[str, Any]) -> str | None:
    return str(row.get("INTERVALSTARTTIME_GMT") or "") or None


def _aggregate_caiso_rows(dataset: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse provider rows into bounded daily features while preserving lineage."""

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        operating_date = str(row.get("OPR_DT") or "")[:10]
        if _parse_date(operating_date) is not None:
            grouped[operating_date].append(row)
    output: list[dict[str, Any]] = []
    for operating_date, day_rows in sorted(grouped.items()):
        record: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "provider": "CAISO OASIS",
            "dataset": dataset,
            "operating_date": operating_date,
            "provider_backed": True,
            "source_row_count": len(day_rows),
        }
        if dataset in {"dam_lmp", "rtm_lmp"}:
            value_field = "MW" if dataset == "dam_lmp" else "VALUE"
            by_node_type: dict[tuple[str, str], list[float]] = defaultdict(list)
            hourly_lmp: dict[str, dict[str, list[float]]] = defaultdict(
                lambda: defaultdict(list)
            )
            for row in day_rows:
                node = str(row.get("NODE") or row.get("NODE_ID") or "")
                lmp_type = str(row.get("LMP_TYPE") or "")
                value = _float(row.get(value_field))
                hour = _hour_key(row)
                if not node or value is None:
                    continue
                by_node_type[(node, lmp_type)].append(value)
                if lmp_type == "LMP" and hour:
                    hourly_lmp[node][hour].append(value)
            nodes: dict[str, Any] = {}
            for node in CAISO_NODES:
                lmp_values = by_node_type.get((node, "LMP"), [])
                congestion = by_node_type.get((node, "MCC"), [])
                nodes[node] = {
                    "mean_lmp": _mean(lmp_values),
                    "max_lmp": max(lmp_values) if lmp_values else None,
                    "min_lmp": min(lmp_values) if lmp_values else None,
                    "p95_lmp": _quantile(lmp_values, 0.95),
                    "lmp_volatility": pstdev(lmp_values) if len(lmp_values) > 1 else 0.0,
                    "mean_congestion_component": _mean(congestion),
                    "positive_spike_count": sum(value >= 100.0 for value in lmp_values),
                    "negative_price_count": sum(value < 0.0 for value in lmp_values),
                    "sample_count": len(lmp_values),
                }
            hourly_spreads: list[float] = []
            all_hours = sorted({hour for values in hourly_lmp.values() for hour in values})
            for hour in all_hours:
                node_means = [
                    _mean(hourly_lmp[node].get(hour, []))
                    for node in CAISO_NODES
                ]
                clean = [value for value in node_means if value is not None]
                if len(clean) >= 2:
                    hourly_spreads.append(max(clean) - min(clean))
            record.update(
                {
                    "nodes": nodes,
                    "system_mean_lmp": _mean(
                        value
                        for node in nodes.values()
                        for value in [node.get("mean_lmp")]
                        if value is not None
                    ),
                    "system_max_lmp": max(
                        (node.get("max_lmp") for node in nodes.values() if node.get("max_lmp") is not None),
                        default=None,
                    ),
                    "cross_zone_spread_mean": _mean(hourly_spreads),
                    "cross_zone_spread_p95": _quantile(hourly_spreads, 0.95),
                }
            )
        elif dataset == "demand_forecast":
            selected = [
                row
                for row in day_rows
                if str(row.get("TAC_AREA_NAME") or "") == "CA ISO-TAC"
                and str(row.get("XML_DATA_ITEM") or "") == "SYS_FCST_DA_MW"
            ]
            hourly = sorted(
                (
                    (str(row.get("INTERVALSTARTTIME_GMT") or ""), _float(row.get("MW")))
                    for row in selected
                ),
                key=lambda item: item[0],
            )
            values = [value for _hour, value in hourly if value is not None]
            ramps = [abs(right - left) for left, right in zip(values, values[1:])]
            record.update(
                {
                    "hourly_mw": {hour: value for hour, value in hourly if value is not None},
                    "mean_demand_mw": _mean(values),
                    "peak_demand_mw": max(values) if values else None,
                    "minimum_demand_mw": min(values) if values else None,
                    "maximum_hourly_ramp_mw": max(ramps) if ramps else None,
                    "sample_count": len(values),
                }
            )
        elif dataset == "renewable_forecast":
            hourly_values: dict[str, float] = defaultdict(float)
            type_values: dict[str, list[float]] = defaultdict(list)
            for row in day_rows:
                if str(row.get("XML_DATA_ITEM") or "") != "RENEW_FCST_DA_MW":
                    continue
                value = _float(row.get("MW"))
                hour = _hour_key(row)
                if value is None or not hour:
                    continue
                hourly_values[hour] += value
                type_values[str(row.get("RENEWABLE_TYPE") or "unknown")].append(value)
            values = list(hourly_values.values())
            record.update(
                {
                    "hourly_mw": dict(sorted(hourly_values.items())),
                    "mean_renewable_mw": _mean(values),
                    "peak_renewable_mw": max(values) if values else None,
                    "renewable_type_mean_mw": {
                        key: _mean(value) for key, value in sorted(type_values.items())
                    },
                    "sample_count": len(values),
                }
            )
        output.append(record)
    return output


def _build_jobs(start: date, today: date) -> list[dict[str, Any]]:
    caiso_core_jobs: list[dict[str, Any]] = []
    caiso_rtm_jobs: list[dict[str, Any]] = []
    alpaca_jobs: list[dict[str, Any]] = []
    # Include the bounded current partial month/year. Excluding them produced a
    # structurally non-overlapping lake: current CAISO evidence was paired with
    # only prior-year proxy prices, so two healthy providers yielded no testable
    # relationships.
    current_end_exclusive = today + timedelta(days=1)
    for left, right in reversed(_month_windows(start, current_end_exclusive)):
        period = left.strftime("%Y-%m")
        for dataset in ("dam_lmp", "demand_forecast", "renewable_forecast"):
            caiso_core_jobs.append(
                {
                    "job_id": f"caiso:{dataset}:{period}",
                    "provider": "caiso_oasis",
                    "dataset": dataset,
                    "period": period,
                    "start": left.isoformat(),
                    "end_exclusive": right.isoformat(),
                    "status": "pending",
                    "attempt_count": 0,
                }
            )
        for week_left, week_right in reversed(_week_windows(left, right)):
            period = f"{week_left.isoformat()}_{week_right.isoformat()}"
            caiso_rtm_jobs.append(
                {
                    "job_id": f"caiso:rtm_lmp:{period}",
                    "provider": "caiso_oasis",
                    "dataset": "rtm_lmp",
                    "period": period,
                    "start": week_left.isoformat(),
                    "end_exclusive": week_right.isoformat(),
                    "status": "pending",
                    "attempt_count": 0,
                }
            )
    for left, right in reversed(_year_windows(start, current_end_exclusive)):
        for symbol in POWER_PROXY_SYMBOLS:
            alpaca_jobs.append(
                {
                    "job_id": f"alpaca:{symbol}:{left.year}",
                    "provider": "alpaca_iex",
                    "dataset": "daily_bars",
                    "symbol": symbol,
                    "period": str(left.year),
                    "start": left.isoformat(),
                    "end_exclusive": right.isoformat(),
                    "status": "pending",
                    "attempt_count": 0,
                }
            )
    # Seed both evidence and outcome history in the first bounded run. Without
    # this interleave, hundreds of CAISO partitions would complete before the
    # first proxy-price partition and the backtest would remain unusable.
    jobs: list[dict[str, Any]] = []
    while caiso_core_jobs or alpaca_jobs:
        jobs.extend(caiso_core_jobs[:3])
        del caiso_core_jobs[:3]
        jobs.extend(alpaca_jobs[:7])
        del alpaca_jobs[:7]
    jobs.extend(caiso_rtm_jobs)
    return jobs


def build_acquisition_manifest(
    existing: dict[str, Any] | None = None,
    *,
    generated_at: str,
    start: date,
    today: date,
) -> dict[str, Any]:
    prior = {
        str(row.get("job_id")): row
        for row in (existing or {}).get("jobs", [])
        if isinstance(row, dict) and row.get("job_id")
    }
    jobs = []
    for template in _build_jobs(start, today):
        old = prior.get(template["job_id"], {})
        merged = {**template, **old}
        for immutable in ("job_id", "provider", "dataset", "period", "start", "end_exclusive"):
            merged[immutable] = template[immutable]
        jobs.append(merged)
    counts: dict[str, int] = defaultdict(int)
    for job in jobs:
        counts[str(job.get("status") or "pending")] += 1
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_power_market_acquisition_manifest",
        "generated_at": generated_at,
        "policy_version": POLICY_VERSION,
        "research_start": start.isoformat(),
        "job_count": len(jobs),
        "job_state_counts": dict(sorted(counts.items())),
        "complete_job_count": counts.get("complete", 0),
        "remaining_job_count": len(jobs) - counts.get("complete", 0),
        "jobs": jobs,
        "raw_store": str(RAW_ROOT.relative_to(ROOT)),
        "normalized_store": str(NORMALIZED_ROOT.relative_to(ROOT)),
        "resumable": True,
        "idempotent": True,
        "provider_writes_allowed": False,
        "authority": authority_flags(),
    }


def _write_caiso_job(job: dict[str, Any], result: AcquisitionResult) -> dict[str, Any]:
    dataset = str(job["dataset"])
    period = str(job["period"])
    raw_path = RAW_ROOT / "caiso" / dataset / f"{period}.zip"
    normalized_path = NORMALIZED_ROOT / "caiso" / dataset / f"{period}.jsonl"
    metadata_path = NORMALIZED_ROOT / "caiso" / dataset / f"{period}.metadata.json"
    normalized = _aggregate_caiso_rows(dataset, result.rows)
    _atomic_bytes(raw_path, result.raw)
    _write_jsonl_atomic(normalized_path, normalized)
    metadata = {
        **result.metadata,
        "normalized_row_count": len(normalized),
        "normalized_record_set_hash": record_set_hash(normalized),
        "raw_path": str(raw_path.relative_to(ROOT)),
        "normalized_path": str(normalized_path.relative_to(ROOT)),
    }
    write_json_atomic(metadata_path, metadata)
    return {
        **job,
        "status": "complete",
        "completed_at": now_iso(),
        "attempt_count": int(job.get("attempt_count") or 0) + 1,
        "raw_path": metadata["raw_path"],
        "normalized_path": metadata["normalized_path"],
        "raw_sha256": result.metadata["raw_sha256"],
        "normalized_record_set_hash": metadata["normalized_record_set_hash"],
        "normalized_row_count": len(normalized),
        "last_error": None,
    }


def _write_alpaca_job(job: dict[str, Any], result: AcquisitionResult) -> dict[str, Any]:
    symbol = str(job["symbol"])
    period = str(job["period"])
    raw_path = RAW_ROOT / "alpaca" / symbol / f"{period}.json"
    normalized_path = NORMALIZED_ROOT / "alpaca" / symbol / f"{period}.jsonl"
    metadata_path = NORMALIZED_ROOT / "alpaca" / symbol / f"{period}.metadata.json"
    _atomic_bytes(raw_path, result.raw)
    _write_jsonl_atomic(normalized_path, result.rows)
    metadata = {
        **result.metadata,
        "normalized_record_set_hash": record_set_hash(result.rows),
        "raw_path": str(raw_path.relative_to(ROOT)),
        "normalized_path": str(normalized_path.relative_to(ROOT)),
    }
    write_json_atomic(metadata_path, metadata)
    return {
        **job,
        "status": "complete",
        "completed_at": now_iso(),
        "attempt_count": int(job.get("attempt_count") or 0) + 1,
        "raw_path": metadata["raw_path"],
        "normalized_path": metadata["normalized_path"],
        "raw_sha256": result.metadata["raw_sha256"],
        "normalized_record_set_hash": metadata["normalized_record_set_hash"],
        "normalized_row_count": len(result.rows),
        "last_error": None,
    }


def acquire_historical_partitions(
    manifest: dict[str, Any],
    *,
    max_partitions: int,
    allow_network: bool,
    settings: Settings,
) -> dict[str, Any]:
    if max_partitions < 0 or max_partitions > 32:
        raise ValueError("power_market_max_partitions_out_of_bounds")
    if not allow_network or max_partitions == 0:
        return manifest
    if _directory_size(RESEARCH_ROOT) >= MAX_RESEARCH_STORE_BYTES:
        raise RuntimeError("power_market_research_store_ceiling_reached")
    api_key = secret_value("ALPACA_API_KEY", settings)
    api_secret = secret_value("ALPACA_API_SECRET", settings)
    jobs = list(manifest.get("jobs", []))
    processed = 0
    attempted_at = datetime.now(timezone.utc)

    def retry_due(job: dict[str, Any]) -> bool:
        if job.get("status") != "retryable_error":
            return True
        due_at = _parse_timestamp(job.get("next_retry_at"))
        return due_at is None or due_at <= attempted_at

    # New partitions always advance before provider retries. A repeatedly slow
    # endpoint therefore remains visible and recoverable without starving the
    # rest of the evidence universe.
    candidate_indices = [
        index
        for index, job in enumerate(jobs)
        if job.get("status") == "pending"
    ] + [
        index
        for index, job in enumerate(jobs)
        if job.get("status") == "retryable_error" and retry_due(job)
    ]
    for index in candidate_indices:
        if processed >= max_partitions:
            break
        job = jobs[index]
        try:
            if job.get("provider") == "caiso_oasis":
                result = fetch_caiso_partition(
                    str(job["dataset"]),
                    date.fromisoformat(str(job["start"])),
                    date.fromisoformat(str(job["end_exclusive"])),
                )
                jobs[index] = _write_caiso_job(job, result)
            elif job.get("provider") == "alpaca_iex":
                if not api_key or not api_secret:
                    raise RuntimeError("alpaca_market_data_credentials_missing")
                result = fetch_alpaca_bars(
                    str(job["symbol"]),
                    date.fromisoformat(str(job["start"])),
                    date.fromisoformat(str(job["end_exclusive"])),
                    api_key=api_key,
                    api_secret=api_secret,
                )
                jobs[index] = _write_alpaca_job(job, result)
            else:
                raise RuntimeError("unsupported_power_market_provider")
        except (HTTPError, URLError, TimeoutError, OSError, RuntimeError, ValueError) as exc:
            attempt_count = int(job.get("attempt_count") or 0) + 1
            retry_seconds = min(
                PARTITION_RETRY_MAX_SECONDS,
                PARTITION_RETRY_BASE_SECONDS * (2 ** min(attempt_count - 1, 5)),
            )
            jobs[index] = {
                **job,
                "status": "retryable_error",
                "attempt_count": attempt_count,
                "last_attempt_at": now_iso(),
                "next_retry_at": (
                    attempted_at + timedelta(seconds=retry_seconds)
                ).isoformat(),
                "retry_backoff_seconds": retry_seconds,
                "last_error": f"{type(exc).__name__}:{str(exc)[:300]}",
            }
        processed += 1
        time.sleep(0.2)
    updated = dict(manifest)
    updated["jobs"] = jobs
    updated["generated_at"] = now_iso()
    counts: dict[str, int] = defaultdict(int)
    for job in jobs:
        counts[str(job.get("status") or "pending")] += 1
    updated["job_state_counts"] = dict(sorted(counts.items()))
    updated["complete_job_count"] = counts.get("complete", 0)
    updated["remaining_job_count"] = len(jobs) - counts.get("complete", 0)
    updated["partitions_attempted_this_run"] = processed
    updated["research_store_bytes"] = _directory_size(RESEARCH_ROOT)
    return updated


def _load_completed_caiso(manifest: dict[str, Any]) -> dict[str, dict[str, dict[str, Any]]]:
    by_dataset: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for job in manifest.get("jobs", []):
        if not isinstance(job, dict) or job.get("status") != "complete":
            continue
        if job.get("provider") != "caiso_oasis":
            continue
        path = ROOT / str(job.get("normalized_path") or "")
        for row in _read_jsonl(path):
            operating_date = str(row.get("operating_date") or "")
            if operating_date:
                by_dataset[str(job.get("dataset"))][operating_date] = row
    return by_dataset


def _load_completed_proxy_bars(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    for job in manifest.get("jobs", []):
        if not isinstance(job, dict) or job.get("status") != "complete":
            continue
        if job.get("provider") != "alpaca_iex":
            continue
        path = ROOT / str(job.get("normalized_path") or "")
        for row in _read_jsonl(path):
            symbol = str(row.get("symbol") or "")
            day = str(row.get("date") or "")
            if symbol and day:
                indexed[(symbol, day)] = row
    return [indexed[key] for key in sorted(indexed)]


def refresh_live_inputs(
    *,
    allow_network: bool,
    settings: Settings,
    today: date,
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Refresh a small rolling provider window independent of backfill progress."""

    if not allow_network:
        live_caiso = {
            dataset: _read_jsonl(NORMALIZED_ROOT / "live" / f"{dataset}.jsonl")
            for dataset in CAISO_DATASETS
        }
        live_bars = _read_jsonl(NORMALIZED_ROOT / "live" / "alpaca_proxy_bars.jsonl")
        live_quotes = _read_jsonl(NORMALIZED_ROOT / "live" / "alpaca_proxy_quotes.jsonl")
        return live_caiso, live_bars, live_quotes
    api_key = secret_value("ALPACA_API_KEY", settings)
    api_secret = secret_value("ALPACA_API_SECRET", settings)
    if not api_key or not api_secret:
        raise RuntimeError("alpaca_market_data_credentials_missing")
    live_caiso: dict[str, list[dict[str, Any]]] = {}
    for dataset in CAISO_DATASETS:
        if dataset == "rtm_lmp":
            left, right = today - timedelta(days=1), today
        else:
            left, right = today - timedelta(days=2), today + timedelta(days=2)
        result = fetch_caiso_partition(dataset, left, right)
        raw_path = RAW_ROOT / "live" / f"{dataset}.zip"
        normalized_path = NORMALIZED_ROOT / "live" / f"{dataset}.jsonl"
        metadata_path = NORMALIZED_ROOT / "live" / f"{dataset}.metadata.json"
        normalized = _aggregate_caiso_rows(dataset, result.rows)
        _atomic_bytes(raw_path, result.raw)
        _write_jsonl_atomic(normalized_path, normalized)
        write_json_atomic(
            metadata_path,
            {
                **result.metadata,
                "normalized_record_set_hash": record_set_hash(normalized),
                "normalized_row_count": len(normalized),
            },
        )
        live_caiso[dataset] = normalized
        time.sleep(0.15)
    left = date(today.year, 1, 1)
    right = today + timedelta(days=1)
    live_bars: list[dict[str, Any]] = []
    live_quotes: list[dict[str, Any]] = []
    for symbol in POWER_PROXY_SYMBOLS:
        result = fetch_alpaca_bars(
            symbol,
            left,
            right,
            api_key=api_key,
            api_secret=api_secret,
        )
        live_bars.extend(result.rows)
        try:
            live_quotes.append(
                fetch_alpaca_latest_quote(
                    symbol,
                    api_key=api_key,
                    api_secret=api_secret,
                )
            )
        except (HTTPError, URLError, TimeoutError, OSError, RuntimeError, ValueError):
            live_quotes.append(
                {
                    "symbol": symbol,
                    "observed_at": now_iso(),
                    "spread_bps": None,
                    "provider": "Alpaca Market Data IEX",
                    "provider_backed": False,
                }
            )
        time.sleep(0.1)
    _write_jsonl_atomic(NORMALIZED_ROOT / "live" / "alpaca_proxy_bars.jsonl", live_bars)
    _write_jsonl_atomic(NORMALIZED_ROOT / "live" / "alpaca_proxy_quotes.jsonl", live_quotes)
    return live_caiso, live_bars, live_quotes


def _merge_live_caiso(
    historical: dict[str, dict[str, dict[str, Any]]],
    live: dict[str, list[dict[str, Any]]],
) -> dict[str, dict[str, dict[str, Any]]]:
    merged = {dataset: dict(rows) for dataset, rows in historical.items()}
    for dataset, rows in live.items():
        target = merged.setdefault(dataset, {})
        for row in rows:
            operating_date = str(row.get("operating_date") or "")
            if operating_date:
                target[operating_date] = row
    return merged


def build_daily_power_evidence(
    datasets: dict[str, dict[str, dict[str, Any]]]
) -> list[dict[str, Any]]:
    dates = sorted(
        set(datasets.get("dam_lmp", {}))
        & set(datasets.get("demand_forecast", {}))
        & set(datasets.get("renewable_forecast", {}))
    )
    rows: list[dict[str, Any]] = []
    for day in dates:
        dam = datasets["dam_lmp"][day]
        rtm = datasets.get("rtm_lmp", {}).get(day, {})
        demand = datasets["demand_forecast"][day]
        renewable = datasets["renewable_forecast"][day]
        demand_hourly = demand.get("hourly_mw", {})
        renewable_hourly = renewable.get("hourly_mw", {})
        net_loads = [
            float(demand_value) - float(renewable_hourly.get(hour, 0.0))
            for hour, demand_value in demand_hourly.items()
            if _float(demand_value) is not None
        ]
        demand_peak = _float(demand.get("peak_demand_mw"))
        renewable_mean = _float(renewable.get("mean_renewable_mw"))
        record = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_power_market_daily_evidence",
            "operating_date": day,
            "decision_available_at": f"{(date.fromisoformat(day) - timedelta(days=1)).isoformat()}T23:59:00+00:00",
            "availability_rule": "conservative_day_ahead_market_schedule_cutoff",
            "availability_timestamp_directly_exported_by_provider": False,
            "dam_system_mean_lmp": _float(dam.get("system_mean_lmp")),
            "dam_system_max_lmp": _float(dam.get("system_max_lmp")),
            "dam_cross_zone_spread_mean": _float(dam.get("cross_zone_spread_mean")),
            "dam_cross_zone_spread_p95": _float(dam.get("cross_zone_spread_p95")),
            "rtm_system_mean_lmp": _float(rtm.get("system_mean_lmp")),
            "rtm_system_max_lmp": _float(rtm.get("system_max_lmp")),
            "rtm_cross_zone_spread_p95": _float(rtm.get("cross_zone_spread_p95")),
            "demand_peak_mw": demand_peak,
            "demand_mean_mw": _float(demand.get("mean_demand_mw")),
            "maximum_hourly_ramp_mw": _float(demand.get("maximum_hourly_ramp_mw")),
            "renewable_mean_mw": renewable_mean,
            "renewable_peak_mw": _float(renewable.get("peak_renewable_mw")),
            "net_load_peak_mw": max(net_loads) if net_loads else None,
            "renewable_to_peak_demand_ratio": _safe_ratio(renewable_mean, demand_peak),
            "provider_backed": True,
            "point_in_time_safe": True,
            "target_outcome_available": bool(rtm),
            "provider_lineage": {
                "dam_lmp": "CAISO OASIS PRC_LMP DAM",
                "rtm_lmp": "CAISO OASIS PRC_INTVL_LMP RTM",
                "demand": "CAISO OASIS SLD_FCST DAM",
                "renewables": "CAISO OASIS SLD_REN_FCST DAM",
            },
            "paper_order_allowed": False,
            "authority": authority_flags(),
        }
        rows.append(record)
    return rows


def _feature_value(row: dict[str, Any], method: str) -> float | None:
    if method == "scarcity_pressure":
        net = _float(row.get("net_load_peak_mw"))
        ramp = _float(row.get("maximum_hourly_ramp_mw"))
        price = _float(row.get("dam_system_max_lmp"))
        if None in {net, ramp, price}:
            return None
        return float(net) + 2.0 * float(ramp) + 20.0 * float(price)
    if method == "congestion_divergence":
        return _float(row.get("dam_cross_zone_spread_p95"))
    if method == "renewable_shortfall":
        ratio = _float(row.get("renewable_to_peak_demand_ratio"))
        return None if ratio is None else -ratio
    if method == "day_ahead_price_pressure":
        return _float(row.get("dam_system_max_lmp"))
    raise ValueError(f"unknown_power_market_method:{method}")


def _bar_index(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("symbol") and row.get("date") and row.get("open") is not None and row.get("close") is not None:
            by_symbol[str(row["symbol"])].append(row)
    for symbol in by_symbol:
        by_symbol[symbol].sort(key=lambda row: str(row["date"]))
    return by_symbol


def _forward_proxy_returns(
    bars: list[dict[str, Any]], horizon: int
) -> dict[str, float]:
    output: dict[str, float] = {}
    for index, bar in enumerate(bars):
        exit_index = index + horizon - 1
        if exit_index >= len(bars):
            continue
        entry = _float(bar.get("open"))
        exit_price = _float(bars[exit_index].get("close"))
        if entry not in {None, 0.0} and exit_price is not None:
            output[str(bar["date"])] = (exit_price - entry) / entry
    return output


def _maximum_drawdown(returns: list[float]) -> float | None:
    if not returns:
        return None
    wealth = 1.0
    peak = 1.0
    drawdown = 0.0
    for value in returns:
        wealth *= 1.0 + value
        peak = max(peak, wealth)
        drawdown = min(drawdown, wealth / peak - 1.0)
    return drawdown


def _one_sided_mean_p_value(values: list[float]) -> float:
    if len(values) < 2:
        return 1.0
    standard = pstdev(values)
    if standard <= 0:
        return 0.0 if fmean(values) > 0 else 1.0
    statistic = fmean(values) / (standard / math.sqrt(len(values)))
    return 0.5 * math.erfc(statistic / math.sqrt(2.0))


def _permutation_p_value(
    returns: list[float],
    selected_count: int,
    observed_mean: float,
    *,
    iterations: int = 200,
    seed: str,
) -> float:
    if selected_count <= 0 or selected_count > len(returns):
        return 1.0
    generator = random.Random(int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16], 16))
    exceed = 0
    indices = list(range(len(returns)))
    for _ in range(iterations):
        sample = generator.sample(indices, selected_count)
        if fmean(returns[index] for index in sample) >= observed_mean:
            exceed += 1
    return (exceed + 1) / (iterations + 1)


def _bh_adjust(results: list[dict[str, Any]]) -> None:
    ranked = sorted(
        enumerate(results),
        key=lambda pair: float(pair[1].get("raw_p_value") or 1.0),
    )
    total = len(ranked)
    running = 1.0
    adjusted: dict[int, float] = {}
    for rank_index in range(total - 1, -1, -1):
        original_index, row = ranked[rank_index]
        rank = rank_index + 1
        candidate = min(1.0, float(row.get("raw_p_value") or 1.0) * total / rank)
        running = min(running, candidate)
        adjusted[original_index] = running
    for index, row in enumerate(results):
        row["adjusted_p_value"] = adjusted.get(index, 1.0)


def build_power_market_backtest(
    daily_rows: list[dict[str, Any]],
    proxy_bars: list[dict[str, Any]],
    *,
    generated_at: str,
) -> dict[str, Any]:
    bars_by_symbol = _bar_index(proxy_bars)
    evidence_by_date = {str(row.get("operating_date")): row for row in daily_rows}
    results: list[dict[str, Any]] = []
    for symbol in POWER_PROXY_SYMBOLS:
        bars = bars_by_symbol.get(symbol, [])
        for horizon in HORIZONS:
            returns_by_date = _forward_proxy_returns(bars, horizon)
            dates = sorted(set(evidence_by_date).intersection(returns_by_date))
            if len(dates) < 90:
                continue
            train_end = max(1, int(len(dates) * 0.60))
            validation_end = max(train_end + 1, int(len(dates) * 0.80))
            train_dates = dates[:train_end]
            validation_dates = dates[train_end:validation_end]
            holdout_dates = dates[validation_end:]
            for method in METHODS:
                train_features = [
                    _feature_value(evidence_by_date[day], method) for day in train_dates
                ]
                threshold = _quantile(
                    (value for value in train_features if value is not None), 0.80
                )
                if threshold is None:
                    continue

                def selected(segment: list[str]) -> list[tuple[str, float]]:
                    return [
                        (day, returns_by_date[day] - ROUND_TRIP_COST_RATE)
                        for day in segment
                        if (_feature_value(evidence_by_date[day], method) or -math.inf)
                        >= threshold
                    ]

                train_selected = selected(train_dates)
                validation_selected = selected(validation_dates)
                holdout_selected = selected(holdout_dates)
                holdout_net = [value for _day, value in holdout_selected]
                validation_net = [value for _day, value in validation_selected]
                train_net = [value for _day, value in train_selected]
                gross_holdout = [value + ROUND_TRIP_COST_RATE for value in holdout_net]
                holdout_all = [returns_by_date[day] - ROUND_TRIP_COST_RATE for day in holdout_dates]
                mean_net = _mean(holdout_net)
                validation_mean = _mean(validation_net)
                benchmark_mean = _mean(holdout_all)
                yearly: dict[str, list[float]] = defaultdict(list)
                for day, value in holdout_selected:
                    yearly[day[:4]].append(value)
                positive_year_ratio = (
                    sum((_mean(values) or 0.0) > 0 for values in yearly.values()) / len(yearly)
                    if yearly
                    else 0.0
                )
                raw_p = max(
                    _one_sided_mean_p_value(holdout_net),
                    _permutation_p_value(
                        holdout_all,
                        len(holdout_net),
                        mean_net or 0.0,
                        seed=f"{symbol}:{method}:{horizon}",
                    ),
                )
                result = {
                    "result_id": stable_id(
                        "power-market-backtest", symbol, method, horizon, threshold, dates
                    ),
                    "strategy_family_id": STRATEGY_FAMILY_ID,
                    "instrument": symbol,
                    "method": method,
                    "direction": "long",
                    "horizon_days": horizon,
                    "threshold": threshold,
                    "sample_date_start": dates[0],
                    "sample_date_end": dates[-1],
                    "sample_count": len(dates),
                    "train_event_count": len(train_net),
                    "validation_event_count": len(validation_net),
                    "holdout_event_count": len(holdout_net),
                    "train_mean_net_return": _mean(train_net),
                    "validation_mean_net_return": validation_mean,
                    "holdout_mean_gross_return": _mean(gross_holdout),
                    "holdout_mean_net_return": mean_net,
                    "holdout_hit_rate": (
                        sum(value > 0 for value in holdout_net) / len(holdout_net)
                        if holdout_net
                        else None
                    ),
                    "holdout_maximum_drawdown": _maximum_drawdown(holdout_net),
                    "holdout_benchmark_mean_net_return": benchmark_mean,
                    "holdout_uplift_vs_unconditional": (
                        mean_net - benchmark_mean
                        if mean_net is not None and benchmark_mean is not None
                        else None
                    ),
                    "positive_holdout_year_ratio": positive_year_ratio,
                    "raw_p_value": raw_p,
                    "adjusted_p_value": None,
                    "cost_rate": ROUND_TRIP_COST_RATE,
                    "walk_forward_split": "60_train_20_validation_20_untouched_holdout",
                    "threshold_fit_on_train_only": True,
                    "holdout_untouched_during_threshold_fit": True,
                    "provider_backed": True,
                    "not_a_return_guarantee": True,
                }
                results.append(result)
    _bh_adjust(results)
    for result in results:
        mean_net = _float(result.get("holdout_mean_net_return")) or 0.0
        validation_mean = _float(result.get("validation_mean_net_return")) or 0.0
        hit_rate = _float(result.get("holdout_hit_rate")) or 0.0
        drawdown = _float(result.get("holdout_maximum_drawdown"))
        uplift = _float(result.get("holdout_uplift_vs_unconditional")) or 0.0
        provisional = bool(
            int(result.get("holdout_event_count") or 0) >= MIN_PROVISIONAL_HOLDOUT_EVENTS
            and mean_net > 0
            and validation_mean > 0
            and hit_rate >= 0.50
        )
        validated = bool(
            provisional
            and int(result.get("holdout_event_count") or 0) >= MIN_VALIDATED_HOLDOUT_EVENTS
            and hit_rate >= 0.52
            and drawdown is not None
            and drawdown >= -0.15
            and uplift > 0
            and float(result.get("adjusted_p_value") or 1.0) <= 0.10
            and float(result.get("positive_holdout_year_ratio") or 0.0) >= 0.50
        )
        result["provisional_positive_after_costs"] = provisional
        result["validated_edge_candidate"] = validated
        result["status"] = (
            "validated_edge_candidate_pending_canonical_or10_admission"
            if validated
            else "positive_provisional_result"
            if provisional
            else "rejected_or_under_evidenced"
        )
        result["authority"] = authority_flags()
    ranked = sorted(
        results,
        key=lambda row: (
            row.get("validated_edge_candidate") is True,
            row.get("provisional_positive_after_costs") is True,
            _float(row.get("holdout_mean_net_return")) or -1.0,
            int(row.get("holdout_event_count") or 0),
        ),
        reverse=True,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_power_market_backtest",
        "generated_at": generated_at,
        "status": (
            "complete_with_validated_candidate"
            if any(row["validated_edge_candidate"] for row in results)
            else "complete_with_provisional_candidates"
            if any(row["provisional_positive_after_costs"] for row in results)
            else "complete_no_surviving_candidate"
            if results
            else "waiting_for_historical_coverage"
        ),
        "daily_evidence_count": len(daily_rows),
        "proxy_bar_count": len(proxy_bars),
        "hypothesis_count": len(results),
        "provisional_positive_count": sum(
            row["provisional_positive_after_costs"] for row in results
        ),
        "validated_candidate_count": sum(row["validated_edge_candidate"] for row in results),
        "best_result": ranked[0] if ranked else None,
        "results": ranked,
        "multiple_testing_correction": "Benjamini-Hochberg",
        "negative_control": "deterministic_return_permutation",
        "cost_adjusted": True,
        "point_in_time_safe": True,
        "strategy_or_order_created": False,
        "authority": authority_flags(),
    }


def _rolling_market_context(bars: list[dict[str, Any]], symbol: str) -> dict[str, Any]:
    rows = sorted(
        [row for row in bars if row.get("symbol") == symbol and row.get("close") is not None],
        key=lambda row: str(row.get("date") or ""),
    )
    if not rows:
        return {}
    closes = [float(row["close"]) for row in rows]
    volumes = [float(row.get("volume") or 0.0) for row in rows]
    returns = [right / left - 1.0 for left, right in zip(closes, closes[1:]) if left]
    latest = rows[-1]
    ma20 = _mean(closes[-20:])
    ma50 = _mean(closes[-50:])
    vol20 = pstdev(returns[-20:]) * math.sqrt(252) if len(returns) >= 2 else None
    volume20 = _mean(volumes[-20:])
    return {
        "symbol": symbol,
        "observed_at": latest.get("observed_at") or f"{latest.get('date')}T20:00:00+00:00",
        "last_close": latest.get("close"),
        "previous_close": rows[-2].get("close") if len(rows) >= 2 else None,
        "rolling_volatility_20d": vol20,
        "volume_ratio": (
            float(latest.get("volume") or 0.0) / volume20
            if volume20 not in {None, 0.0}
            else None
        ),
        "moving_average_20d": ma20,
        "moving_average_50d": ma50,
        "trend_state": (
            "above_20d_and_50d"
            if ma20 is not None and ma50 is not None and closes[-1] > ma20 > ma50
            else "mixed_or_not_confirmed"
        ),
        "provider": "Alpaca Market Data IEX",
        "market_state": "provider_live_read_only",
        "origin_class": "provider_backed_market_context",
    }


def _current_feature_percentile(
    daily_rows: list[dict[str, Any]], method: str, current: dict[str, Any]
) -> tuple[float | None, float | None]:
    value = _feature_value(current, method)
    history = [
        candidate
        for row in daily_rows
        for candidate in [_feature_value(row, method)]
        if candidate is not None and str(row.get("operating_date")) < str(current.get("operating_date"))
    ]
    if value is None or len(history) < 20:
        return value, None
    percentile = sum(candidate <= value for candidate in history) / len(history)
    return value, percentile


def build_strategy_and_current_context(
    daily_rows: list[dict[str, Any]],
    proxy_bars: list[dict[str, Any]],
    live_quotes: list[dict[str, Any]],
    backtest: dict[str, Any],
    *,
    generated_at: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    best = backtest.get("best_result")
    best = best if isinstance(best, dict) else {}
    complete_current = [
        row
        for row in daily_rows
        if row.get("provider_backed") is True
        and _feature_value(row, str(best.get("method") or "scarcity_pressure")) is not None
    ]
    current = max(complete_current, key=lambda row: str(row.get("operating_date")), default={})
    method = str(best.get("method") or "scarcity_pressure")
    current_value, current_percentile = _current_feature_percentile(daily_rows, method, current)
    proxy = str(best.get("instrument") or "")
    proxy_context = _rolling_market_context(proxy_bars, proxy) if proxy else {}
    quote_by_symbol = {
        str(row.get("symbol")): row for row in live_quotes if isinstance(row, dict)
    }
    quote_row = quote_by_symbol.get(proxy, {})
    if proxy_context and quote_row:
        proxy_context["spread_bps"] = quote_row.get("spread_bps")
        proxy_context["quote_observed_at"] = quote_row.get("observed_at")
    provisional = best.get("provisional_positive_after_costs") is True
    current_signal_active = bool(
        provisional
        and current_percentile is not None
        and current_percentile >= 0.80
        and proxy_context
    )
    expectancy = _float(best.get("holdout_mean_net_return"))
    drawdown = abs(_float(best.get("holdout_maximum_drawdown")) or 0.0)
    reward_to_risk = (
        max(0.0, expectancy or 0.0) / max(drawdown, 0.005)
        if expectancy is not None
        else None
    )
    research_score = min(
        1.0,
        max(
            0.0,
            0.25
            + 0.35 * float(current_percentile or 0.0)
            + 0.20 * min(1.0, max(0.0, float(best.get("holdout_hit_rate") or 0.0)))
            + 0.20 * (1.0 if provisional else 0.0),
        ),
    )
    strategy_state = (
        "validated_candidate_pending_canonical_edge_admission"
        if best.get("validated_edge_candidate") is True
        else "emerging_strategy_admitted_for_current_experimental_review"
        if current_signal_active and research_score >= 0.50
        else "emerging_strategy_watching_for_current_trigger"
        if provisional
        else "research_sleeve_under_evidenced"
    )
    instrument_rows = [
        {
            "symbol": symbol,
            "paper_route_available": True,
            "role": (
                "direct_power_producer_proxy"
                if symbol in PRODUCER_PROXY_SYMBOLS
                else "secondary_power_market_proxy"
            ),
        }
        for symbol in POWER_PROXY_SYMBOLS
    ]
    strategy_row = {
        "strategy_family_id": STRATEGY_FAMILY_ID,
        "label": "Power Scarcity & Congestion",
        "strategy_kind": "pattern_sourced_emerging",
        "admission_state": strategy_state,
        "evidence_class": (
            "evidence_backed"
            if best.get("validated_edge_candidate") is True
            else "under_evidenced"
        ),
        "thesis": (
            "Qadam tests whether day-ahead electricity scarcity, renewable shortfalls, "
            "and congestion contain timely information about listed power-market proxies."
        ),
        "plain_english": (
            "When California expects unusually tight electricity supply, high demand, or "
            "grid congestion, Qadam checks whether listed power producers and grid-related "
            "funds tend to reprice after the information becomes available."
        ),
        "mechanism": (
            "Day-ahead load and renewable forecasts affect expected net load; constrained "
            "transmission can separate regional prices; higher marginal power prices can "
            "change expected producer economics and sector positioning."
        ),
        "source_keys": [
            "caiso_oasis_day_ahead_lmp",
            "caiso_oasis_real_time_lmp",
            "caiso_oasis_demand_forecast",
            "caiso_oasis_renewable_forecast",
            "alpaca_power_proxy_market_data",
        ],
        "instrument_contribution": {"instruments": instrument_rows},
        "watched_markets": instrument_rows,
        "best_observed_rejected_result": {
            "result_id": best.get("result_id"),
            "mean_gross_return": best.get("holdout_mean_gross_return"),
            "mean_net_return": best.get("holdout_mean_net_return"),
            "hit_rate": best.get("holdout_hit_rate"),
            "holdout_event_count": best.get("holdout_event_count"),
            "adjusted_p_value": best.get("adjusted_p_value"),
            # OR-10 remains the only canonical edge-admission boundary. Even a
            # strong sleeve result is provisional while it enters that review.
            "not_a_validated_expectancy": True,
            "rejection_reasons": (
                []
                if best.get("validated_edge_candidate") is True
                else ["canonical_edge_validation_not_yet_complete"]
            ),
        },
        "confidence_distribution": {
            "holdout_mean_net_return": best.get("holdout_mean_net_return"),
            "holdout_hit_rate": best.get("holdout_hit_rate"),
            "holdout_event_count": best.get("holdout_event_count"),
        },
        "empirical_evidence": {
            "backtest_status": backtest.get("status"),
            "hypothesis_count": backtest.get("hypothesis_count"),
            "provisional_positive_count": backtest.get("provisional_positive_count"),
            "validated_candidate_count": backtest.get("validated_candidate_count"),
            "best_result_id": best.get("result_id"),
        },
        "failure_modes": [
            {"reason": "wholesale_power_signal_may_not_transfer_to_equity_proxy"},
            {"reason": "day_ahead_publication_timestamp_is_schedule_derived"},
            {"reason": "multiple_testing_false_discovery"},
            {"reason": "power_price_regime_or_policy_change"},
            {"reason": "spread_slippage_or_proxy_basis_erases_expectancy"},
        ],
        "next_evidence_requirement": (
            "Collect real forward outcomes under frozen rules and rerun the holdout tests."
        ),
        "current_signal": {
            "active": current_signal_active,
            "method": method,
            "operating_date": current.get("operating_date"),
            "feature_value": current_value,
            "historical_percentile": current_percentile,
            "research_score": research_score,
            "proxy": proxy or None,
        },
        "expected_reward_to_risk": reward_to_risk,
        "automatic_admission_policy": {
            "policy_version": POLICY_VERSION,
            "bounded_paper_only": True,
            "human_trade_approval_required_after_mandate": False,
            "risk_envelope_mutation_allowed": False,
            "live_capital_allowed": False,
        },
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "proof_credit_allowed": False,
        "authority": authority_flags(),
    }
    strategy_registry = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_power_market_strategy_registry",
        "generated_at": generated_at,
        "status": strategy_state,
        "policy_version": POLICY_VERSION,
        "strategy_count": 1,
        "strategies": [strategy_row],
        "automatic_strategy_admission_enabled": True,
        "automatic_risk_envelope_expansion_enabled": False,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    scores: list[dict[str, Any]] = []
    if current_signal_active and proxy and research_score >= 0.50:
        scoring_at = generated_at
        score_id = stable_id(
            "power-market-pattern-score",
            STRATEGY_FAMILY_ID,
            proxy,
            method,
            current.get("operating_date"),
        )
        scores.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_pattern_score_v3_compatible_extension",
                "score_id": score_id,
                "feature_vector_id": stable_id("power-market-feature-vector", score_id),
                "input_fingerprint": sha256_json(
                    {
                        "current": current,
                        "best_result_id": best.get("result_id"),
                        "proxy_context": proxy_context,
                    }
                ),
                "model_version": "power_market_mechanism_score.v1",
                "operating_date": current.get("operating_date"),
                "raw_pattern_score": round(research_score, 8),
                "confidence_state": "score_ready_for_tape",
                "negative_control": False,
                "missing_critical_features": [],
                "direction_hypothesis": "upside_under_power_scarcity",
                "horizon_hypothesis": f"{int(best.get('horizon_days') or 1)}d_forward",
                "instrument": proxy,
                "market_family": "power_markets",
                "strategy_family_id": STRATEGY_FAMILY_ID,
                "strategy_agnostic": True,
                "features": {
                    "strategy_fit": 1.0,
                    "current_anomaly_percentile": current_percentile,
                    "historical_after_cost_support": 1.0 if provisional else 0.0,
                    "paperability_context": 1.0,
                },
                "feature_inputs": [
                    {
                        "source_key": "caiso_oasis_power_market_fundamentals",
                        "fresh": True,
                        "quorum_eligible": True,
                        "independence_cluster_id": "caiso_market_operator",
                    },
                    {
                        "source_key": "alpaca_power_proxy_market_data",
                        "fresh": True,
                        "quorum_eligible": True,
                        "independence_cluster_id": "alpaca_market_data",
                    },
                ],
                "expected_reward_to_risk": reward_to_risk,
                "scoring_as_of": scoring_at,
                "provider_backed": True,
                "paper_order_allowed": False,
                "authority": authority_flags(),
            }
        )
    price_record = dict(proxy_context)
    price_record.setdefault("spread_bps", quote_row.get("spread_bps"))
    packet = {
        "packet_id": stable_id(
            "power-market-context-packet", current.get("operating_date"), proxy, method
        ),
        "generated_at": generated_at,
        "market_channel": "power_markets",
        "watched_instruments": [proxy] if proxy else [],
        "market_context_status": "context_ready" if scores else "watching_no_current_trigger",
        "source_quorum_result": {
            "status": "pass" if scores else "hold",
            "score": 1.0 if scores else 0.5,
            "independent_provider_count": 2 if scores else 1,
            "providers": ["CAISO OASIS", "Alpaca Market Data IEX"],
        },
        "hypothesis": (
            f"{method.replace('_', ' ').title()} is at the "
            f"{round(float(current_percentile or 0.0) * 100, 1)}th historical percentile; "
            f"Qadam is testing {proxy or 'the proxy basket'} under the frozen paper-only policy."
        ),
        "price_volume_context": {
            "status": "provider_live_read_only" if proxy_context else "missing",
            "provider": "Alpaca Market Data IEX",
            "records": [price_record] if price_record else [],
        },
        "technical_context": {
            "status": "provider_backed_calculated" if proxy_context else "missing",
            "provider": "Alpaca Market Data IEX derived from adjusted daily bars",
            "records": [price_record] if price_record else [],
        },
        "orderflow_context": {"status": "not_required_for_daily_proxy", "records": []},
        "pricing_gap_evidence": {
            "available": bool(scores),
            "state": "measured" if scores else "missing",
            "observed_at": generated_at,
            "value": {
                "feature_percentile": current_percentile,
                "feature_value": current_value,
                "method": method,
            },
            "provider": "CAISO OASIS mechanism feature engine",
            "origin_class": "provider_backed_calculation",
            "reason": (
                "The current day-ahead power signal is unusually high relative to history."
                if scores
                else "The current mechanism feature has not crossed its frozen trigger."
            ),
        },
        "nonlinear_review": {
            "available": backtest.get("hypothesis_count", 0) > 0,
            "state": "reviewed" if backtest.get("hypothesis_count", 0) > 0 else "missing",
            "observed_at": generated_at,
            "value": {
                "methods": list(METHODS),
                "best_method": method,
                "validated_candidate_count": backtest.get("validated_candidate_count"),
            },
            "provider": "Qadam matched classical power-market research",
            "origin_class": "provider_backed_research_calculation",
            "reason": (
                "Linear and regime-conditioned mechanism tests were compared on untouched time periods."
            ),
        },
        "paper_order_allowed": False,
        "authority": authority_flags(),
    }
    context = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_power_market_context",
        "generated_at": generated_at,
        "status": packet["market_context_status"],
        "recent_packets": [packet],
        "authority": authority_flags(),
    }
    return strategy_registry, scores, context


def validate_power_market_state(
    state: dict[str, Any],
    manifest: dict[str, Any],
    backtest: dict[str, Any],
    strategy: dict[str, Any],
    scores: list[dict[str, Any]],
    context: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if manifest.get("resumable") is not True or manifest.get("idempotent") is not True:
        errors.append("power_market_manifest_not_resumable_and_idempotent")
    if manifest.get("provider_writes_allowed") is not False:
        errors.append("power_market_provider_write_authority_enabled")
    if state.get("research_store_bytes", 0) > MAX_RESEARCH_STORE_BYTES:
        errors.append("power_market_research_store_over_ceiling")
    if backtest.get("point_in_time_safe") is not True:
        errors.append("power_market_backtest_not_point_in_time_safe")
    if backtest.get("cost_adjusted") is not True:
        errors.append("power_market_backtest_cost_adjustment_missing")
    if strategy.get("automatic_risk_envelope_expansion_enabled") is not False:
        errors.append("power_market_automatic_risk_expansion_enabled")
    if strategy.get("live_capital_enabled") is not False:
        errors.append("power_market_live_capital_enabled")
    if any(score.get("negative_control") is not False for score in scores):
        errors.append("power_market_negative_control_admitted")
    if any(score.get("provider_backed") is not True for score in scores):
        errors.append("power_market_non_provider_score_admitted")
    for payload, prefix in (
        (state, "power_market_state"),
        (manifest, "power_market_manifest"),
        (backtest, "power_market_backtest"),
        (strategy, "power_market_strategy"),
        (context, "power_market_context"),
    ):
        errors.extend(validate_authority(payload.get("authority", {}), prefix=prefix))
    for score in scores:
        errors.extend(validate_authority(score.get("authority", {}), prefix="power_market_score"))
    return unique_errors(errors)


def build_and_write_power_market_edge_engine(
    settings: Settings | None = None,
    *,
    allow_network: bool = False,
    max_partitions: int = 0,
    research_start: date | None = None,
    generated_at: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    active = settings or Settings.from_env()
    generated = generated_at or now_iso()
    current_day = (_parse_timestamp(generated) or datetime.now(timezone.utc)).date()
    start = research_start or date(2019, 1, 1)
    runtime = runtime_dir(active)
    store = AtomicArtifactStore(runtime)
    existing_manifest = read_json(runtime / MANIFEST_ARTIFACT)
    manifest = build_acquisition_manifest(
        existing_manifest,
        generated_at=generated,
        start=start,
        today=current_day,
    )
    manifest = acquire_historical_partitions(
        manifest,
        max_partitions=max_partitions,
        allow_network=allow_network,
        settings=active,
    )
    live_errors: list[str] = []
    try:
        live_caiso, live_bars, live_quotes = refresh_live_inputs(
            allow_network=allow_network,
            settings=active,
            today=current_day,
        )
    except (HTTPError, URLError, TimeoutError, OSError, RuntimeError, ValueError) as exc:
        live_errors.append(f"power_market_live_refresh:{type(exc).__name__}:{str(exc)[:300]}")
        live_caiso, live_bars, live_quotes = refresh_live_inputs(
            allow_network=False,
            settings=active,
            today=current_day,
        )
    historical_caiso = _load_completed_caiso(manifest)
    datasets = _merge_live_caiso(historical_caiso, live_caiso)
    historical_bars = _load_completed_proxy_bars(manifest)
    bar_index = {
        (str(row.get("symbol")), str(row.get("date"))): row
        for row in [*historical_bars, *live_bars]
        if row.get("symbol") and row.get("date")
    }
    proxy_bars = [bar_index[key] for key in sorted(bar_index)]
    daily_rows = build_daily_power_evidence(datasets)
    _write_jsonl_atomic(DAILY_EVIDENCE_PATH, daily_rows)
    _write_jsonl_atomic(PROXY_BARS_PATH, proxy_bars)
    backtest = build_power_market_backtest(
        daily_rows,
        proxy_bars,
        generated_at=generated,
    )
    strategy, scores, context = build_strategy_and_current_context(
        daily_rows,
        proxy_bars,
        live_quotes,
        backtest,
        generated_at=generated,
    )
    research_store_bytes = _directory_size(RESEARCH_ROOT)
    state = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_power_market_edge_engine",
        "generated_at": generated,
        "status": (
            "operational_with_current_strategy_signal"
            if scores
            else "operational_collecting_and_testing"
            if daily_rows
            else "waiting_for_provider_evidence"
        ),
        "policy_version": POLICY_VERSION,
        "provider_state": {
            "caiso_oasis": (
                "provider_backed_live"
                if any(live_caiso.values())
                else "cached_or_unavailable"
            ),
            "alpaca_iex": "provider_backed_live" if live_bars else "cached_or_unavailable",
        },
        "daily_evidence_count": len(daily_rows),
        "proxy_bar_count": len(proxy_bars),
        "historical_partition_complete_count": manifest.get("complete_job_count"),
        "historical_partition_remaining_count": manifest.get("remaining_job_count"),
        "backtest_status": backtest.get("status"),
        "backtest_hypothesis_count": backtest.get("hypothesis_count"),
        "provisional_positive_count": backtest.get("provisional_positive_count"),
        "validated_candidate_count": backtest.get("validated_candidate_count"),
        "current_pattern_score_count": len(scores),
        "strategy_admission_state": strategy.get("status"),
        "research_store_bytes": research_store_bytes,
        "research_store_ceiling_bytes": MAX_RESEARCH_STORE_BYTES,
        "live_refresh_errors": live_errors,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    errors = [
        *live_errors,
        *validate_power_market_state(
            state,
            manifest,
            backtest,
            strategy,
            scores,
            context,
        ),
    ]
    # A transient live-provider failure is visible but does not invalidate an
    # otherwise safe cached research state. It remains a retryable service error.
    hard_errors = [error for error in errors if not error.startswith("power_market_live_refresh:")]
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_power_market_edge_engine_checks",
        "generated_at": generated,
        "status": "passed" if not hard_errors else "failed",
        "implementation_ready": not hard_errors,
        "safe_to_consume": not hard_errors and bool(daily_rows),
        "provider_backed_live_refresh": not live_errors,
        "daily_evidence_count": len(daily_rows),
        "proxy_bar_count": len(proxy_bars),
        "historical_partition_complete_count": manifest.get("complete_job_count"),
        "historical_partition_remaining_count": manifest.get("remaining_job_count"),
        "backtest_hypothesis_count": backtest.get("hypothesis_count"),
        "provisional_positive_count": backtest.get("provisional_positive_count"),
        "validated_candidate_count": backtest.get("validated_candidate_count"),
        "current_pattern_score_count": len(scores),
        "strategy_admission_state": strategy.get("status"),
        "automatic_strategy_admission_enabled": True,
        "automatic_risk_envelope_expansion_enabled": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_count": 0,
        "live_capital_enabled": False,
        "errors": hard_errors,
        "retryable_provider_errors": live_errors,
        "authority": authority_flags(),
    }
    dashboard = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_power_market_dashboard_summary",
        "generated_at": generated,
        "status": state["status"],
        "eyebrow": "Pattern-sourced research sleeve",
        "headline": "Power Scarcity & Congestion",
        "plain_english": strategy["strategies"][0]["plain_english"],
        "admission_state": strategy.get("status"),
        "daily_evidence_count": len(daily_rows),
        "tested_hypothesis_count": backtest.get("hypothesis_count"),
        "provisional_positive_count": backtest.get("provisional_positive_count"),
        "validated_candidate_count": backtest.get("validated_candidate_count"),
        "current_pattern_score_count": len(scores),
        "best_result": backtest.get("best_result"),
        "research_extension": {
            "status": "research_running",
            "label": "Power & Grid Constraints",
            "region": "California ISO",
            "canonical_whole_universe_baseline": {
                "source_count": 41,
                "instrument_count": 19,
                "included_in_prior_whole_universe_backtest": False,
            },
            "source_feeds": [
                {
                    **row,
                    "source_family": "power_grid_constraints",
                    "state": state["provider_state"]["caiso_oasis"],
                    "freshness_status": (
                        "fresh"
                        if state["provider_state"]["caiso_oasis"]
                        == "provider_backed_live"
                        else "cached_or_unavailable"
                    ),
                    "provider_backed": True,
                    "quorum_contribution": True,
                    "research_extension": True,
                }
                for row in POWER_RESEARCH_SOURCE_FEEDS
            ],
            "instruments": [
                {
                    "symbol": symbol,
                    "display_name": symbol,
                    "market_family": "power_markets",
                    "role": (
                        "direct_power_producer_proxy"
                        if symbol in PRODUCER_PROXY_SYMBOLS
                        else "secondary_power_market_proxy"
                    ),
                    "paper_route_available": True,
                    "paperability_state": "guarded_alpaca_paper_proxy_available",
                    "research_extension": True,
                }
                for symbol in POWER_PROXY_SYMBOLS
            ],
            "provider_independence_note": (
                "The four CAISO feeds are separate measurements from one grid operator; "
                "they count as one provider family. Alpaca supplies the independent "
                "listed-market price context."
            ),
            "next_provider_extensions": [
                "PJM Data Miner",
                "EIA grid and generator history",
                "NOAA point-in-time weather history",
            ],
        },
        "next_action": (
            "Current evidence has entered Strategy Foundry for Akber review."
            if scores
            else "Continue provider-backed acquisition and wait for the frozen current trigger."
        ),
        "authority_boundary": (
            "Automatic admission creates a paper-only research strategy. Akber, Router, risk, "
            "and guarded PaperOps still decide whether a paper order is permitted."
        ),
        "authority": authority_flags(),
    }
    store.write_json(MANIFEST_ARTIFACT, manifest)
    store.write_json(BACKTEST_ARTIFACT, backtest)
    store.write_json(STRATEGY_ARTIFACT, strategy)
    store.write_jsonl(PATTERN_SCORES_ARTIFACT, scores)
    store.write_json(CONTEXT_ARTIFACT, context)
    store.write_json(DASHBOARD_ARTIFACT, dashboard)
    store.write_json(PRIMARY_ARTIFACT, state)
    store.write_json(CHECK_ARTIFACT, checks)
    return state, checks, errors


def research_paths_are_ignored() -> bool:
    """Fail closed if bulk provider data could accidentally enter Git."""

    import subprocess

    completed = subprocess.run(
        ["git", "check-ignore", "-q", str(RESEARCH_ROOT.relative_to(ROOT))],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return completed.returncode == 0


def offline_contract_check(settings: Settings | None = None) -> list[str]:
    runtime = runtime_dir(settings)
    errors: list[str] = []
    if not research_paths_are_ignored():
        errors.append("power_market_research_path_not_git_ignored")
    for artifact in (
        PRIMARY_ARTIFACT,
        MANIFEST_ARTIFACT,
        BACKTEST_ARTIFACT,
        STRATEGY_ARTIFACT,
        CONTEXT_ARTIFACT,
        DASHBOARD_ARTIFACT,
        CHECK_ARTIFACT,
    ):
        if not (runtime / artifact).is_file():
            errors.append(f"power_market_artifact_missing:{artifact}")
    checks = read_json(runtime / CHECK_ARTIFACT)
    if checks and checks.get("status") != "passed":
        errors.append("power_market_checks_not_passed")
    return unique_errors(errors)
