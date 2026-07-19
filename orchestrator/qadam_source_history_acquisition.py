"""Bounded official-provider source-history acquisition for OR-3.

The module only performs idempotent reads. Current-revision macro series are
stored with an explicit non-vintage-safe label so later alignment cannot treat
them as point-in-time evidence.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import time
from typing import Any, Callable
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
import zipfile

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    authority_flags,
    now_iso,
    read_json,
    runtime_dir,
)
from orchestrator.secrets import secret_value

SCHEMA_VERSION = "qadam_source_history_acquisition.v1"
SOURCE_MANIFEST_ARTIFACT = "qadam_source_backfill_manifest.json"
PRICE_MANIFEST_ARTIFACT = "qadam_price_backfill_manifest.json"
RUN_ARTIFACT = "qadam_source_history_acquisition.json"
DEFERRED_ACTIONS_ARTIFACT = "qadam_or3_deferred_source_actions.json"
RESEARCH_ROOT = ROOT / "data" / "research"

BLS_SERIES = {
    "CUUR0000SA0": "US consumer price index",
    "CES0000000001": "US nonfarm payroll employment",
    "WPU00000000": "US producer price index",
}
BIS_FLOWS = (
    "WS_CREDIT_GAP",
    "WS_DPP",
    "WS_EER",
    "WS_LONG_CPI",
)
SEC_CIKS = {
    "NVDA": "0001045810",
    "LMT": "0000936468",
}
SEC_USER_AGENT = "Qadam private research dev@qadam.trade"
UCDP_GED_VERSION = "26.1"
UCDP_CANDIDATE_VERSION = "26.0.5"
UCDP_GED_URL = "https://ucdp.uu.se/downloads/ged/ged261-csv.zip"
UCDP_CANDIDATE_URL = (
    "https://ucdp.uu.se/downloads/candidateged/GEDEvent_v26_0_5.csv"
)
SUPPORTED_NETWORK_SOURCES = frozenset(
    {
        "bis",
        "bls",
        "ecb",
        "kalshi",
        "polymarket",
        "sec_edgar",
        "stock_act",
        "ucdp",
        "usgs",
    }
)
SUPPORTED_LOCAL_SOURCES = frozenset({"alpaca"})
RETRYABLE_JOB_STATES = frozenset({"pending_source_adapter", "retryable_failure"})
PREDICTION_SEARCH_TERMS = (
    "crude oil",
    "WTI",
    "silver",
    "gold",
    "Federal Reserve",
    "interest rates",
    "inflation",
    "recession",
    "unemployment",
    "GDP",
    "Iran",
    "Israel",
    "war",
    "Red Sea",
    "Taiwan",
    "China",
    "semiconductor",
    "Nvidia",
    "sanctions",
    "tariffs",
    "election",
)
PREDICTION_RELEVANCE_TERMS = (
    "oil",
    "crude",
    "wti",
    "brent",
    "silver",
    "gold",
    "federal reserve",
    "fed",
    "interest rate",
    "interest rates",
    "inflation",
    "cpi",
    "recession",
    "unemployment",
    "jobs report",
    "gdp",
    "iran",
    "israel",
    "war",
    "conflict",
    "red sea",
    "strait of hormuz",
    "taiwan",
    "china",
    "semiconductor",
    "nvidia",
    "sanction",
    "tariff",
    "defence",
    "defense",
    "election",
    "president",
    "senate",
)
PREDICTION_DISCOVERY_LIMIT_PER_TERM = 20
PREDICTION_MARKET_LIMIT_PER_PLATFORM = 500
PREDICTION_MARKET_LIMIT_PER_YEAR = 60
PREDICTION_PROVIDER_CACHE: dict[str, Any] = {}
DEFERRED_SOURCE_CLASSIFICATIONS: dict[str, dict[str, Any]] = {
    "gdelt": {
        "typed_reason": "archive_volume_exceeds_approved_local_storage_and_query_scope",
        "current_state": "official_archive_available_but_not_bounded_for_local_run",
        "operator_action": (
            "Approve a bounded GDELT BigQuery or archive query design, including date, "
            "geography, theme, row, storage, and cost ceilings."
        ),
    },
    "nasa_firms": {
        "typed_reason": "operator_generated_earthdata_archive_export_required",
        "current_state": "official_archive_requires_interactive_export_or_earthdata_access",
        "operator_action": (
            "Generate the approved NASA FIRMS annual archive export through Earthdata "
            "and place it in the documented private import path."
        ),
    },
    "patents": {
        "typed_reason": "official_uspto_subset_scope_not_frozen",
        "current_state": "official_bulk_history_available_but_unbounded",
        "operator_action": (
            "Approve a bounded USPTO assignee and technology-theme scope for the "
            "semiconductor and defence research lanes before bulk acquisition."
        ),
    },
}


@dataclass(frozen=True, kw_only=True)
class SourceHistoryOptions:
    allow_network: bool = False
    provider_terms_reviewed: bool = False
    resume: bool = True
    max_jobs: int = 0
    timeout_seconds: int = 45
    sleep_between_calls: float = 0.25
    source_keys: tuple[str, ...] = ()
    classify_deferred: bool = False


def _atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _fetch_json(request: Request, *, timeout_seconds: int) -> tuple[bytes, Any]:
    with urlopen(  # noqa: S310 - callers use frozen official provider endpoints
        request,
        timeout=timeout_seconds,
    ) as response:
        raw = response.read()
    return raw, json.loads(raw)


def _fetch_bytes(request: Request, *, timeout_seconds: int) -> bytes:
    with urlopen(  # noqa: S310 - callers use frozen official provider endpoints
        request,
        timeout=timeout_seconds,
    ) as response:
        return response.read()


def _year_bounds_iso(year: int) -> tuple[str, str]:
    return f"{year:04d}-01-01T00:00:00Z", f"{year + 1:04d}-01-01T00:00:00Z"


def _year_bounds_epoch(year: int) -> tuple[int, int]:
    start = datetime(year, 1, 1, tzinfo=timezone.utc)
    end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    return int(start.timestamp()), int(end.timestamp()) - 1


def _period_timestamp(period: str) -> str | None:
    value = period.strip()
    try:
        if len(value) == 4:
            return f"{value}-01-01T00:00:00+00:00"
        if len(value) == 7 and value[4] == "-" and value[5] == "Q":
            month = (int(value[6]) - 1) * 3 + 1
            return f"{value[:4]}-{month:02d}-01T00:00:00+00:00"
        if len(value) == 7:
            return f"{value}-01T00:00:00+00:00"
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def _bis_partition(
    year: int,
    *,
    settings: Settings,
    timeout_seconds: int,
) -> tuple[bytes, list[dict[str, Any]], dict[str, Any]]:
    del settings
    fetched_at = now_iso()
    payloads: dict[str, str] = {}
    records: list[dict[str, Any]] = []
    unavailable_flows: list[dict[str, Any]] = []
    for flow in BIS_FLOWS:
        params = urlencode({"startPeriod": str(year), "endPeriod": str(year)})
        endpoint = f"https://stats.bis.org/api/v1/data/{flow}/all/all?{params}"
        try:
            raw = _fetch_bytes(
                Request(
                    endpoint,
                    headers={"Accept": "application/xml", "User-Agent": "Qadam/1.0 research"},
                ),
                timeout_seconds=timeout_seconds,
            )
        except HTTPError as exc:
            if exc.code != 404:
                raise
            response_body = exc.read().decode("utf-8", errors="replace")
            payloads[flow] = response_body
            unavailable_flows.append(
                {
                    "flow": flow,
                    "status_code": exc.code,
                    "typed_reason": "provider_has_no_partition_for_requested_period",
                }
            )
            continue
        payloads[flow] = raw.decode("utf-8", errors="replace")
        root = ET.fromstring(raw)
        for series in root.iter():
            if not series.tag.endswith("Series"):
                continue
            dimensions = dict(series.attrib)
            for observation in series:
                if not observation.tag.endswith("Obs"):
                    continue
                period = str(observation.attrib.get("TIME_PERIOD") or "")
                if not period.startswith(str(year)):
                    continue
                records.append(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "source_key": "bis",
                        "flow": flow,
                        "series_dimensions": dimensions,
                        "event_timestamp": _period_timestamp(period),
                        "source_available_at": fetched_at,
                        "value": observation.attrib.get("OBS_VALUE"),
                        "observation_status": observation.attrib.get("OBS_STATUS"),
                        "observation_confidentiality": observation.attrib.get("OBS_CONF"),
                        "point_in_time_safe": False,
                        "vintage_state": "current_revision_snapshot_not_historical_vintage",
                    }
                )
    raw_bundle = json.dumps(payloads, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return raw_bundle, records, {
        "endpoint": "https://stats.bis.org/api/v1/data/{flow}/all/all",
        "flows": list(BIS_FLOWS),
        "unavailable_flows": unavailable_flows,
        "credentials_recorded": False,
        "fetched_at": fetched_at,
    }


def _bls_partition(
    year: int,
    *,
    settings: Settings,
    timeout_seconds: int,
) -> tuple[bytes, list[dict[str, Any]], dict[str, Any]]:
    fetched_at = now_iso()
    body: dict[str, Any] = {
        "seriesid": list(BLS_SERIES),
        "startyear": str(year),
        "endyear": str(year),
    }
    registration_key = secret_value("BLS_API_KEY", settings)
    if registration_key:
        body["registrationkey"] = registration_key
    encoded = json.dumps(body, separators=(",", ":")).encode("utf-8")
    request = Request(
        "https://api.bls.gov/publicAPI/v2/timeseries/data/",
        data=encoded,
        headers={"Content-Type": "application/json", "User-Agent": "Qadam/1.0 research"},
        method="POST",
    )
    raw, payload = _fetch_json(request, timeout_seconds=timeout_seconds)
    if not isinstance(payload, dict) or payload.get("status") != "REQUEST_SUCCEEDED":
        raise RuntimeError("bls_provider_response_not_successful")
    series_rows = payload.get("Results", {}).get("series", [])
    records: list[dict[str, Any]] = []
    for series in series_rows if isinstance(series_rows, list) else []:
        series_id = str(series.get("seriesID") or "")
        for item in series.get("data", []):
            period = str(item.get("period") or "")
            if not period.startswith("M") or period == "M13":
                continue
            month = int(period[1:])
            records.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "source_key": "bls",
                    "series_id": series_id,
                    "series_name": BLS_SERIES.get(series_id, series_id),
                    "event_timestamp": f"{year:04d}-{month:02d}-01T00:00:00+00:00",
                    "source_available_at": fetched_at,
                    "value": item.get("value"),
                    "period": period,
                    "footnotes": item.get("footnotes", []),
                    "point_in_time_safe": False,
                    "vintage_state": "current_revision_snapshot_not_historical_vintage",
                }
            )
    return raw, records, {
        "endpoint": "https://api.bls.gov/publicAPI/v2/timeseries/data/",
        "series_ids": list(BLS_SERIES),
        "registration_key_used": bool(registration_key),
        "credentials_recorded": False,
        "fetched_at": fetched_at,
    }


def _ecb_partition(
    year: int,
    *,
    settings: Settings,
    timeout_seconds: int,
) -> tuple[bytes, list[dict[str, Any]], dict[str, Any]]:
    del settings
    fetched_at = now_iso()
    params = urlencode(
        {
            "startPeriod": f"{year:04d}-01-01",
            "endPeriod": f"{year:04d}-12-31",
            "format": "csvdata",
        }
    )
    endpoint = f"https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A?{params}"
    request = Request(endpoint, headers={"Accept": "text/csv", "User-Agent": "Qadam/1.0 research"})
    with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
        raw = response.read()
    records: list[dict[str, Any]] = []
    for row in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))):
        period = str(row.get("TIME_PERIOD") or "")
        if not period:
            continue
        records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "source_key": "ecb",
                "series_id": str(row.get("KEY") or "EXR.D.USD.EUR.SP00.A"),
                "series_name": row.get("TITLE_COMPL") or row.get("TITLE"),
                "event_timestamp": f"{period}T00:00:00+00:00",
                "source_available_at": fetched_at,
                "value": row.get("OBS_VALUE"),
                "observation_status": row.get("OBS_STATUS"),
                "point_in_time_safe": False,
                "vintage_state": "current_revision_snapshot_not_historical_vintage",
            }
        )
    return raw, records, {
        "endpoint": endpoint.split("?", 1)[0],
        "series_id": "EXR.D.USD.EUR.SP00.A",
        "credentials_recorded": False,
        "fetched_at": fetched_at,
    }


def _epoch_millis_iso(value: Any) -> str | None:
    if not isinstance(value, (int, float)):
        return None
    return datetime.fromtimestamp(float(value) / 1000.0, tz=timezone.utc).isoformat()


def _usgs_partition(
    year: int,
    *,
    settings: Settings,
    timeout_seconds: int,
) -> tuple[bytes, list[dict[str, Any]], dict[str, Any]]:
    del settings
    fetched_at = now_iso()
    params = urlencode(
        {
            "format": "geojson",
            "starttime": f"{year:04d}-01-01",
            "endtime": f"{year + 1:04d}-01-01",
            "minmagnitude": 5,
            "orderby": "time-asc",
            "limit": 20000,
        }
    )
    endpoint = f"https://earthquake.usgs.gov/fdsnws/event/1/query?{params}"
    request = Request(endpoint, headers={"Accept": "application/json", "User-Agent": "Qadam/1.0 research"})
    raw, payload = _fetch_json(request, timeout_seconds=timeout_seconds)
    features = payload.get("features", []) if isinstance(payload, dict) else []
    records: list[dict[str, Any]] = []
    for feature in features if isinstance(features, list) else []:
        properties = feature.get("properties", {})
        geometry = feature.get("geometry", {})
        coordinates = geometry.get("coordinates", []) if isinstance(geometry, dict) else []
        records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "source_key": "usgs",
                "provider_event_id": feature.get("id"),
                "event_timestamp": _epoch_millis_iso(properties.get("time")),
                "source_available_at": (
                    _epoch_millis_iso(properties.get("updated")) or fetched_at
                ),
                "magnitude": properties.get("mag"),
                "place": properties.get("place"),
                "longitude": coordinates[0] if len(coordinates) > 0 else None,
                "latitude": coordinates[1] if len(coordinates) > 1 else None,
                "depth_km": coordinates[2] if len(coordinates) > 2 else None,
                "significance": properties.get("sig"),
                "point_in_time_safe": True,
                "vintage_state": "provider_event_with_updated_timestamp",
            }
        )
    return raw, records, {
        "endpoint": endpoint.split("?", 1)[0],
        "minimum_magnitude": 5,
        "credentials_recorded": False,
        "fetched_at": fetched_at,
    }


def _sec_partition(
    year: int,
    *,
    settings: Settings,
    timeout_seconds: int,
) -> tuple[bytes, list[dict[str, Any]], dict[str, Any]]:
    del settings
    fetched_at = now_iso()
    payloads: dict[str, Any] = {}
    records: list[dict[str, Any]] = []
    seen_accessions: set[str] = set()

    def append_rows(ticker: str, cik: str, filing_rows: dict[str, Any]) -> None:
        forms = filing_rows.get("form", [])
        filing_dates = filing_rows.get("filingDate", [])
        acceptances = filing_rows.get("acceptanceDateTime", [])
        accessions = filing_rows.get("accessionNumber", [])
        primary_documents = filing_rows.get("primaryDocument", [])
        count = min(
            len(forms),
            len(filing_dates),
            len(accessions),
            len(primary_documents),
        )
        for index in range(count):
            filing_date = str(filing_dates[index] or "")
            if not filing_date.startswith(str(year)):
                continue
            accession = str(accessions[index] or "")
            if not accession or accession in seen_accessions:
                continue
            seen_accessions.add(accession)
            acceptance = str(acceptances[index] or "") if index < len(acceptances) else ""
            available_at, timestamp_precision = _sec_available_at(
                acceptance,
                filing_date=filing_date,
            )
            records.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "source_key": "sec_edgar",
                    "ticker": ticker,
                    "cik": cik,
                    "form": forms[index],
                    "accession_number": accession,
                    "primary_document": primary_documents[index],
                    "event_timestamp": f"{filing_date}T00:00:00+00:00",
                    "source_available_at": available_at,
                    "availability_timestamp_precision": timestamp_precision,
                    "point_in_time_safe": True,
                    "vintage_state": "filing_acceptance_timestamp",
                }
            )

    for ticker, cik in SEC_CIKS.items():
        endpoint = f"https://data.sec.gov/submissions/CIK{cik}.json"
        request = Request(
            endpoint,
            headers={
                "Accept": "application/json",
                "User-Agent": SEC_USER_AGENT,
            },
        )
        _raw, payload = _fetch_json(request, timeout_seconds=timeout_seconds)
        payloads[ticker] = {"submissions": payload, "historical_files": {}}
        recent = payload.get("filings", {}).get("recent", {}) if isinstance(payload, dict) else {}
        append_rows(ticker, cik, recent)
        history_files = payload.get("filings", {}).get("files", []) if isinstance(payload, dict) else []
        for history_file in history_files if isinstance(history_files, list) else []:
            filing_from = str(history_file.get("filingFrom") or "")
            filing_to = str(history_file.get("filingTo") or "")
            if filing_from > f"{year:04d}-12-31" or filing_to < f"{year:04d}-01-01":
                continue
            name = str(history_file.get("name") or "")
            if not name:
                continue
            history_endpoint = f"https://data.sec.gov/submissions/{name}"
            history_request = Request(
                history_endpoint,
                headers={"Accept": "application/json", "User-Agent": SEC_USER_AGENT},
            )
            _history_raw, history_payload = _fetch_json(
                history_request,
                timeout_seconds=timeout_seconds,
            )
            payloads[ticker]["historical_files"][name] = history_payload
            if isinstance(history_payload, dict):
                append_rows(ticker, cik, history_payload)
    raw = json.dumps(payloads, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return raw, records, {
        "endpoint": "https://data.sec.gov/submissions/CIK##########.json",
        "tickers": list(SEC_CIKS),
        "credentials_recorded": False,
        "fetched_at": fetched_at,
    }


def _sec_available_at(acceptance: str, *, filing_date: str) -> tuple[str, str]:
    if acceptance:
        normalized = acceptance.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            try:
                parsed = datetime.strptime(acceptance, "%Y%m%d%H%M%S").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                parsed = None
        if parsed is not None:
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).isoformat(), "acceptance_datetime"
    return f"{filing_date}T23:59:59+00:00", "conservative_filing_day_end"


def _house_disclosure_partition(
    year: int,
    *,
    settings: Settings,
    timeout_seconds: int,
) -> tuple[bytes, list[dict[str, Any]], dict[str, Any]]:
    del settings
    fetched_at = now_iso()
    endpoint = (
        "https://disclosures-clerk.house.gov/public_disc/financial-pdfs/"
        f"{year:04d}FD.zip"
    )
    raw = _fetch_bytes(
        Request(
            endpoint,
            headers={
                "Accept": "application/zip,*/*",
                "Referer": "https://disclosures-clerk.house.gov/FinancialDisclosure/ViewReport",
                "User-Agent": "Mozilla/5.0 Qadam private research",
            },
        ),
        timeout_seconds=timeout_seconds,
    )
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        xml_names = [name for name in archive.namelist() if name.lower().endswith(".xml")]
        if not xml_names:
            raise RuntimeError("house_disclosure_xml_index_missing")
        xml_payload = archive.read(xml_names[0])
    root = ET.fromstring(xml_payload.decode("utf-8-sig"))
    records: list[dict[str, Any]] = []
    for member in root.findall(".//Member"):
        filing_date = (member.findtext("FilingDate") or "").strip()
        try:
            parsed_date = datetime.strptime(filing_date, "%m/%d/%Y").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            continue
        available_at = parsed_date.replace(hour=23, minute=59, second=59).isoformat()
        filing_type = (member.findtext("FilingType") or "").strip()
        records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "source_key": "stock_act",
                "record_type": "house_financial_disclosure_index",
                "event_timestamp": available_at,
                "source_available_at": available_at,
                "first_name": (member.findtext("First") or "").strip(),
                "last_name": (member.findtext("Last") or "").strip(),
                "state_district": (member.findtext("StateDst") or "").strip(),
                "filing_type": filing_type,
                "document_id": (member.findtext("DocID") or "").strip(),
                "periodic_transaction_report": filing_type == "P",
                "transaction_detail_state": "official_index_metadata_only",
                "point_in_time_safe": True,
                "vintage_state": "official_filing_date_conservative_day_end",
            }
        )
    return raw, records, {
        "endpoint": endpoint,
        "archive_member": xml_names[0],
        "raw_extension": "zip",
        "credentials_recorded": False,
        "fetched_at": fetched_at,
        "transaction_detail_state": "official_index_metadata_only",
    }


def _ucdp_shared_archives(
    *,
    timeout_seconds: int,
) -> tuple[Path, Path, dict[str, Any]]:
    root = RESEARCH_ROOT / "raw_shared" / "source=ucdp"
    ged_path = root / f"dataset=ged/version={UCDP_GED_VERSION}/ged261-csv.zip"
    candidate_path = (
        root
        / f"dataset=candidate-ged/version={UCDP_CANDIDATE_VERSION}"
        / "GEDEvent_v26_0_5.csv"
    )
    provider_call_count = 0
    if not ged_path.is_file():
        payload = _fetch_bytes(
            Request(
                UCDP_GED_URL,
                headers={
                    "Accept": "application/zip,*/*",
                    "User-Agent": "Qadam/1.0 research",
                },
            ),
            timeout_seconds=timeout_seconds,
        )
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            if "GEDEvent_v26_1.csv" not in archive.namelist():
                raise RuntimeError("ucdp_ged_archive_member_missing")
        _atomic_bytes(ged_path, payload)
        provider_call_count += 1
    if not candidate_path.is_file():
        payload = _fetch_bytes(
            Request(
                UCDP_CANDIDATE_URL,
                headers={
                    "Accept": "text/csv,*/*",
                    "User-Agent": "Qadam/1.0 research",
                },
            ),
            timeout_seconds=timeout_seconds,
        )
        if not payload.startswith(b"id,relid,year,"):
            raise RuntimeError("ucdp_candidate_csv_header_invalid")
        _atomic_bytes(candidate_path, payload)
        provider_call_count += 1
    return ged_path, candidate_path, {
        "ged_sha256": _sha256(ged_path.read_bytes()),
        "candidate_sha256": _sha256(candidate_path.read_bytes()),
        "provider_call_count": provider_call_count,
    }


def _ucdp_timestamp(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def _ucdp_number(value: Any, *, integer: bool = False) -> int | float | None:
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return int(number) if integer else number


def _ucdp_record(
    row: dict[str, Any],
    *,
    dataset_version: str,
    dataset_state: str,
    fetched_at: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "source_key": "ucdp",
        "record_type": "georeferenced_conflict_event",
        "provider_event_id": row.get("id"),
        "provider_relationship_id": row.get("relid"),
        "event_timestamp": _ucdp_timestamp(row.get("date_start")),
        "event_end_timestamp": _ucdp_timestamp(row.get("date_end")),
        "source_available_at": fetched_at,
        "type_of_violence": _ucdp_number(row.get("type_of_violence"), integer=True),
        "conflict_name": row.get("conflict_name"),
        "dyad_name": row.get("dyad_name"),
        "side_a": row.get("side_a"),
        "side_b": row.get("side_b"),
        "country": row.get("country"),
        "region": row.get("region"),
        "administrative_area_1": row.get("adm_1"),
        "administrative_area_2": row.get("adm_2"),
        "location_description": row.get("where_description"),
        "latitude": _ucdp_number(row.get("latitude")),
        "longitude": _ucdp_number(row.get("longitude")),
        "reported_source_count": _ucdp_number(
            row.get("number_of_sources"), integer=True
        ),
        "best_death_estimate": _ucdp_number(row.get("best"), integer=True),
        "low_death_estimate": _ucdp_number(row.get("low"), integer=True),
        "high_death_estimate": _ucdp_number(row.get("high"), integer=True),
        "dataset_version": dataset_version,
        "dataset_state": dataset_state,
        "point_in_time_safe": False,
        "vintage_state": "current_revision_snapshot_not_historical_vintage",
    }


def _ucdp_partition(
    year: int,
    *,
    settings: Settings,
    timeout_seconds: int,
) -> tuple[bytes, list[dict[str, Any]], dict[str, Any]]:
    del settings
    fetched_at = now_iso()
    ged_path, candidate_path, archive_metadata = _ucdp_shared_archives(
        timeout_seconds=timeout_seconds
    )
    rows: list[dict[str, Any]] = []
    if year == 2026:
        dataset_version = UCDP_CANDIDATE_VERSION
        dataset_state = "candidate_ged_current_snapshot"
        with candidate_path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = [
                row
                for row in csv.DictReader(handle)
                if str(row.get("year")) == str(year)
            ]
        archive_member = candidate_path.name
    else:
        dataset_version = UCDP_GED_VERSION
        dataset_state = "ged_current_release_snapshot"
        with zipfile.ZipFile(ged_path) as archive:
            archive_member = "GEDEvent_v26_1.csv"
            with archive.open(archive_member) as binary_handle:
                with io.TextIOWrapper(
                    binary_handle, encoding="utf-8-sig", newline=""
                ) as handle:
                    rows = [
                        row
                        for row in csv.DictReader(handle)
                        if str(row.get("year")) == str(year)
                    ]
    records = [
        _ucdp_record(
            row,
            dataset_version=dataset_version,
            dataset_state=dataset_state,
            fetched_at=fetched_at,
        )
        for row in rows
    ]
    raw_reference = {
        "provider": "Uppsala Conflict Data Program",
        "dataset_version": dataset_version,
        "dataset_state": dataset_state,
        "archive_member": archive_member,
        "ged_archive_path": str(ged_path.relative_to(ROOT)),
        "ged_archive_sha256": archive_metadata["ged_sha256"],
        "candidate_archive_path": str(candidate_path.relative_to(ROOT)),
        "candidate_archive_sha256": archive_metadata["candidate_sha256"],
        "date_partition": str(year),
    }
    raw = json.dumps(raw_reference, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return raw, records, {
        "endpoint": UCDP_GED_URL if year < 2026 else UCDP_CANDIDATE_URL,
        "official_downloads_page": "https://ucdp.uu.se/downloads/",
        "dataset_version": dataset_version,
        "dataset_state": dataset_state,
        "archive_member": archive_member,
        "shared_immutable_archive": True,
        "shared_archive_reference": raw_reference,
        "provider_call_count": archive_metadata["provider_call_count"],
        "credentials_recorded": False,
        "fetched_at": fetched_at,
        "point_in_time_state": "current_revision_only_not_backtest_eligible",
        "license": "CC BY 4.0 with UCDP attribution",
        "empty_reason": "provider_has_no_partition_for_requested_period",
    }


def _paginated_json(
    base_url: str,
    *,
    params: dict[str, Any],
    collection_key: str,
    cursor_key: str | None,
    timeout_seconds: int,
    max_pages: int = 100,
) -> tuple[list[Any], list[dict[str, Any]], int]:
    records: list[Any] = []
    payloads: list[dict[str, Any]] = []
    cursor = ""
    for page in range(max_pages):
        request_params = dict(params)
        if cursor and cursor_key:
            request_params["cursor"] = cursor
        endpoint = f"{base_url}?{urlencode(request_params)}"
        _raw, payload = _fetch_json(
            Request(endpoint, headers={"Accept": "application/json", "User-Agent": "Qadam/1.0 research"}),
            timeout_seconds=timeout_seconds,
        )
        if not isinstance(payload, dict):
            raise RuntimeError("paginated_provider_payload_not_object")
        payloads.append(payload)
        page_rows = payload.get(collection_key, [])
        if not isinstance(page_rows, list):
            raise RuntimeError("paginated_provider_collection_not_list")
        records.extend(page_rows)
        if cursor_key:
            cursor = str(payload.get(cursor_key) or "")
            if not cursor:
                return records, payloads, page + 1
        else:
            limit = int(params.get("limit") or 100)
            if len(page_rows) < limit:
                return records, payloads, page + 1
            params = {**params, "offset": int(params.get("offset") or 0) + limit}
    raise RuntimeError("paginated_provider_page_ceiling_reached")


def _parse_utc(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _epoch_seconds_iso(value: Any) -> str | None:
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return None


def _timestamp_in_year(value: Any, year: int) -> bool:
    parsed = _parse_utc(value)
    return parsed is not None and parsed.year == year


def _market_overlaps_year(start: Any, end: Any, year: int) -> bool:
    start_at = _parse_utc(start)
    end_at = _parse_utc(end)
    year_start = datetime(year, 1, 1, tzinfo=timezone.utc)
    year_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    if start_at is None and end_at is None:
        return False
    effective_start = start_at or datetime.min.replace(tzinfo=timezone.utc)
    effective_end = end_at or datetime.max.replace(tzinfo=timezone.utc)
    return effective_start < year_end and effective_end >= year_start


def _prediction_title_is_relevant(title: Any) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", " ", str(title or "").lower()).strip()
    if not normalized:
        return False
    padded = f" {normalized} "
    return any(f" {term} " in padded for term in PREDICTION_RELEVANCE_TERMS)


def _json_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return [str(item) for item in parsed if str(item)] if isinstance(parsed, list) else []


def _chunks(values: list[str], size: int) -> list[list[str]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def _oddspipe_prediction_discovery(
    platform: str,
    *,
    settings: Settings,
    timeout_seconds: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    cache_key = f"oddspipe_discovery:{platform}"
    cached = PREDICTION_PROVIDER_CACHE.get(cache_key)
    if isinstance(cached, dict):
        return cached["markets"], cached["payloads"], 0

    api_key = secret_value("ODDSPIPE_API_KEY", settings)
    if not api_key:
        raise RuntimeError("oddspipe_api_key_missing")
    headers = {
        "Accept": "application/json",
        "User-Agent": "Qadam/1.0 read-only research",
        "x-api-key": api_key,
    }
    discovered: dict[str, dict[str, Any]] = {}
    payloads: list[dict[str, Any]] = []
    call_count = 0
    for term in PREDICTION_SEARCH_TERMS:
        params = urlencode(
            {
                "q": term,
                "platform": platform,
                "status": "resolved",
                "limit": PREDICTION_DISCOVERY_LIMIT_PER_TERM,
            }
        )
        endpoint = f"https://oddspipe.com/v1/markets/search?{params}"
        _raw, payload = _fetch_json(
            Request(endpoint, headers=headers),
            timeout_seconds=timeout_seconds,
        )
        call_count += 1
        if not isinstance(payload, dict):
            raise RuntimeError("oddspipe_search_payload_not_object")
        payloads.append({"query": term, "payload": payload})
        items = payload.get("items", [])
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict) or not _prediction_title_is_relevant(item.get("title")):
                continue
            source = item.get("source") if isinstance(item.get("source"), dict) else {}
            if str(source.get("platform") or "").lower() != platform:
                continue
            provider_market_id = str(source.get("platform_market_id") or "")
            if not provider_market_id:
                continue
            current = discovered.setdefault(
                provider_market_id,
                {
                    "oddspipe_market_id": item.get("id"),
                    "provider_market_id": provider_market_id,
                    "provider_event_id": source.get("platform_event_id"),
                    "title": item.get("title"),
                    "category": item.get("category"),
                    "status": item.get("status"),
                    "provider_url": source.get("url"),
                    "matched_terms": [],
                },
            )
            current["matched_terms"] = sorted({*current["matched_terms"], term})

    markets = sorted(
        discovered.values(),
        key=lambda item: (-len(item["matched_terms"]), str(item["provider_market_id"])),
    )[:PREDICTION_MARKET_LIMIT_PER_PLATFORM]
    PREDICTION_PROVIDER_CACHE[cache_key] = {"markets": markets, "payloads": payloads}
    return markets, payloads, call_count


def _kalshi_market_metadata(
    discoveries: list[dict[str, Any]],
    *,
    timeout_seconds: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    cache_key = "kalshi_official_market_metadata"
    cached = PREDICTION_PROVIDER_CACHE.get(cache_key)
    if isinstance(cached, dict):
        return cached["markets"], cached["payloads"], 0

    headers = {"Accept": "application/json", "User-Agent": "Qadam/1.0 read-only research"}
    tickers = [str(item["provider_market_id"]) for item in discoveries]
    by_ticker: dict[str, dict[str, Any]] = {}
    payloads: list[dict[str, Any]] = []
    call_count = 0
    for ticker_chunk in _chunks(tickers, 100):
        encoded_tickers = ",".join(ticker_chunk)
        for lane, endpoint in (
            (
                "historical",
                "https://external-api.kalshi.com/trade-api/v2/historical/markets",
            ),
            ("live", "https://external-api.kalshi.com/trade-api/v2/markets"),
        ):
            request_url = f"{endpoint}?{urlencode({'tickers': encoded_tickers, 'limit': 1000})}"
            _raw, payload = _fetch_json(
                Request(request_url, headers=headers),
                timeout_seconds=timeout_seconds,
            )
            call_count += 1
            if not isinstance(payload, dict):
                raise RuntimeError("kalshi_market_payload_not_object")
            payloads.append({"lane": lane, "payload": payload})
            for market in payload.get("markets", []):
                if not isinstance(market, dict):
                    continue
                ticker = str(market.get("ticker") or "")
                if ticker and ticker not in by_ticker:
                    by_ticker[ticker] = {**market, "_provider_lane": lane}

    markets = [by_ticker[ticker] for ticker in tickers if ticker in by_ticker]
    PREDICTION_PROVIDER_CACHE[cache_key] = {"markets": markets, "payloads": payloads}
    return markets, payloads, call_count


def _kalshi_daily_candles(
    market: dict[str, Any],
    year: int,
    *,
    timeout_seconds: int,
) -> tuple[list[dict[str, Any]], dict[str, Any], int]:
    ticker = str(market.get("ticker") or "")
    cache_key = f"kalshi_candles:{ticker}:{year}"
    cached = PREDICTION_PROVIDER_CACHE.get(cache_key)
    if isinstance(cached, dict):
        return cached["candles"], cached["payload"], 0

    start_ts, end_ts = _year_bounds_epoch(year)
    headers = {"Accept": "application/json", "User-Agent": "Qadam/1.0 read-only research"}
    params = urlencode(
        {"start_ts": start_ts, "end_ts": end_ts, "period_interval": 1440}
    )
    if market.get("_provider_lane") == "historical":
        endpoint = (
            "https://external-api.kalshi.com/trade-api/v2/historical/markets/"
            f"{quote(ticker, safe='')}/candlesticks?{params}"
        )
        _raw, payload = _fetch_json(
            Request(endpoint, headers=headers),
            timeout_seconds=timeout_seconds,
        )
        candles = payload.get("candlesticks", []) if isinstance(payload, dict) else []
    else:
        endpoint = (
            "https://external-api.kalshi.com/trade-api/v2/markets/candlesticks?"
            + urlencode(
                {
                    "market_tickers": ticker,
                    "start_ts": start_ts,
                    "end_ts": end_ts,
                    "period_interval": 1440,
                }
            )
        )
        _raw, payload = _fetch_json(
            Request(endpoint, headers=headers),
            timeout_seconds=timeout_seconds,
        )
        market_rows = payload.get("markets", []) if isinstance(payload, dict) else []
        selected = next(
            (
                item
                for item in market_rows
                if isinstance(item, dict) and item.get("market_ticker") == ticker
            ),
            {},
        )
        candles = selected.get("candlesticks", []) if isinstance(selected, dict) else []
    if not isinstance(candles, list):
        raise RuntimeError("kalshi_candlestick_collection_not_list")
    result = {"endpoint": endpoint, "payload": payload}
    PREDICTION_PROVIDER_CACHE[cache_key] = {"candles": candles, "payload": result}
    return candles, result, 1


def _kalshi_partition(
    year: int,
    *,
    settings: Settings,
    timeout_seconds: int,
) -> tuple[bytes, list[dict[str, Any]], dict[str, Any]]:
    fetched_at = now_iso()
    if year < 2021:
        return b"{}", [], {
            "endpoint": "https://external-api.kalshi.com/trade-api/v2/historical/markets",
            "credentials_recorded": False,
            "fetched_at": fetched_at,
            "empty_reason": "pre_inception_instrument",
            "provider_call_count": 0,
        }
    discoveries, discovery_payloads, discovery_calls = _oddspipe_prediction_discovery(
        "kalshi",
        settings=settings,
        timeout_seconds=timeout_seconds,
    )
    markets, metadata_payloads, metadata_calls = _kalshi_market_metadata(
        discoveries,
        timeout_seconds=timeout_seconds,
    )
    discovery_by_ticker = {
        str(item["provider_market_id"]): item for item in discoveries
    }
    records: list[dict[str, Any]] = []
    candle_payloads: list[dict[str, Any]] = []
    candle_calls = 0
    year_markets = [
        market
        for market in markets
        if _market_overlaps_year(
            market.get("open_time") or market.get("created_time"),
            market.get("settlement_ts") or market.get("close_time"),
            year,
        )
    ][:PREDICTION_MARKET_LIMIT_PER_YEAR]
    for event in year_markets:
        if not isinstance(event, dict):
            continue
        opened_at = event.get("open_time") or event.get("created_time")
        settled_at = event.get("settlement_ts") or event.get("close_time")
        ticker = str(event.get("ticker") or "")
        discovery = discovery_by_ticker.get(ticker, {})
        if _timestamp_in_year(opened_at, year):
            records.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "source_key": "kalshi",
                    "record_type": "prediction_market_open",
                    "event_timestamp": opened_at,
                    "source_available_at": opened_at,
                    "event_ticker": event.get("event_ticker"),
                    "market_ticker": ticker,
                    "title": event.get("title") or discovery.get("title"),
                    "market_type": event.get("market_type"),
                    "matched_research_terms": discovery.get("matched_terms", []),
                    "point_in_time_safe": True,
                    "vintage_state": "official_market_open_without_future_result",
                }
            )
        candles, candle_payload, calls = _kalshi_daily_candles(
            event,
            year,
            timeout_seconds=timeout_seconds,
        )
        candle_calls += calls
        candle_payloads.append({"ticker": ticker, **candle_payload})
        for candle in candles:
            observed_at = _epoch_seconds_iso(candle.get("end_period_ts"))
            if observed_at is None or not _timestamp_in_year(observed_at, year):
                continue
            records.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "source_key": "kalshi",
                    "record_type": "prediction_market_daily_candle",
                    "event_timestamp": observed_at,
                    "source_available_at": observed_at,
                    "event_ticker": event.get("event_ticker"),
                    "market_ticker": ticker,
                    "title": event.get("title") or discovery.get("title"),
                    "price": candle.get("price"),
                    "yes_bid": candle.get("yes_bid"),
                    "yes_ask": candle.get("yes_ask"),
                    "volume": candle.get("volume") or candle.get("volume_fp"),
                    "open_interest": candle.get("open_interest")
                    or candle.get("open_interest_fp"),
                    "matched_research_terms": discovery.get("matched_terms", []),
                    "point_in_time_safe": True,
                    "vintage_state": "official_daily_candlestick",
                }
            )
        if _timestamp_in_year(settled_at, year):
            records.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "source_key": "kalshi",
                    "record_type": "prediction_market_settlement",
                    "event_timestamp": settled_at,
                    "source_available_at": settled_at,
                    "event_ticker": event.get("event_ticker"),
                    "market_ticker": ticker,
                    "title": event.get("title") or discovery.get("title"),
                    "result": event.get("result"),
                    "settlement_value_dollars": event.get("settlement_value_dollars"),
                    "point_in_time_safe": True,
                    "vintage_state": "official_outcome_available_at_settlement_only",
                }
            )
    raw_bundle = {
        "oddspipe_discovery": discovery_payloads,
        "official_market_metadata": metadata_payloads,
        "official_candlesticks": candle_payloads,
    }
    raw = json.dumps(raw_bundle, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return raw, records, {
        "endpoint": "https://external-api.kalshi.com/trade-api/v2/historical/markets",
        "discovery_endpoint": "https://oddspipe.com/v1/markets/search",
        "discovery_role": "bounded_macro_contract_identity_only",
        "historical_evidence_provider": "Kalshi official historical API",
        "provider_call_count": discovery_calls + metadata_calls + candle_calls,
        "discovered_market_count": len(discoveries),
        "official_market_count": len(markets),
        "selection_scope": "resolved_macro_relevant_contracts",
        "full_exchange_universe_claimed": False,
        "credentials_recorded": False,
        "fetched_at": fetched_at,
        "empty_reason": "no_macro_relevant_provider_records_for_partition",
        "candlestick_state": "official_daily_history_acquired_where_available",
    }


def _polymarket_market_metadata(
    discoveries: list[dict[str, Any]],
    *,
    timeout_seconds: int,
) -> tuple[list[dict[str, Any]], list[Any], int]:
    cache_key = "polymarket_official_market_metadata"
    cached = PREDICTION_PROVIDER_CACHE.get(cache_key)
    if isinstance(cached, dict):
        return cached["markets"], cached["payloads"], 0

    condition_ids = [str(item["provider_market_id"]) for item in discoveries]
    headers = {"Accept": "application/json", "User-Agent": "Qadam/1.0 read-only research"}
    markets: list[dict[str, Any]] = []
    payloads: list[Any] = []
    call_count = 0
    for condition_chunk in _chunks(condition_ids, 50):
        query = urlencode(
            [("condition_ids", condition_id) for condition_id in condition_chunk]
            + [("limit", "100"), ("closed", "true")]
        )
        endpoint = f"https://gamma-api.polymarket.com/markets?{query}"
        _raw, payload = _fetch_json(
            Request(endpoint, headers=headers),
            timeout_seconds=timeout_seconds,
        )
        call_count += 1
        if not isinstance(payload, list):
            raise RuntimeError("polymarket_market_payload_not_list")
        payloads.append(payload)
        markets.extend(item for item in payload if isinstance(item, dict))
    PREDICTION_PROVIDER_CACHE[cache_key] = {"markets": markets, "payloads": payloads}
    return markets, payloads, call_count


def _polymarket_token_history(
    token_id: str,
    *,
    timeout_seconds: int,
) -> tuple[list[dict[str, Any]], dict[str, Any], int]:
    cache_key = f"polymarket_token_history:{token_id}"
    cached = PREDICTION_PROVIDER_CACHE.get(cache_key)
    if isinstance(cached, dict):
        return cached["history"], cached["payload"], 0
    endpoint = "https://clob.polymarket.com/prices-history?" + urlencode(
        {"market": token_id, "interval": "max", "fidelity": 1440}
    )
    _raw, payload = _fetch_json(
        Request(
            endpoint,
            headers={"Accept": "application/json", "User-Agent": "Qadam/1.0 read-only research"},
        ),
        timeout_seconds=timeout_seconds,
    )
    history = payload.get("history", []) if isinstance(payload, dict) else []
    if not isinstance(history, list):
        raise RuntimeError("polymarket_history_collection_not_list")
    result = {"endpoint": endpoint, "payload": payload}
    PREDICTION_PROVIDER_CACHE[cache_key] = {"history": history, "payload": result}
    return history, result, 1


def _polymarket_partition(
    year: int,
    *,
    settings: Settings,
    timeout_seconds: int,
) -> tuple[bytes, list[dict[str, Any]], dict[str, Any]]:
    fetched_at = now_iso()
    if year < 2020:
        return b"{}", [], {
            "endpoint": "https://gamma-api.polymarket.com/markets",
            "credentials_recorded": False,
            "fetched_at": fetched_at,
            "empty_reason": "pre_inception_instrument",
            "provider_call_count": 0,
        }
    discoveries, discovery_payloads, discovery_calls = _oddspipe_prediction_discovery(
        "polymarket",
        settings=settings,
        timeout_seconds=timeout_seconds,
    )
    all_markets, market_payloads, metadata_calls = _polymarket_market_metadata(
        discoveries,
        timeout_seconds=timeout_seconds,
    )
    discovery_by_condition = {
        str(item["provider_market_id"]): item for item in discoveries
    }
    records: list[dict[str, Any]] = []
    history_payloads: list[dict[str, Any]] = []
    history_calls = 0
    year_markets = [
        market
        for market in all_markets
        if _market_overlaps_year(
            market.get("createdAt") or market.get("startDate"),
            market.get("closedTime") or market.get("endDate"),
            year,
        )
    ][:PREDICTION_MARKET_LIMIT_PER_YEAR]
    for market in year_markets:
        if not isinstance(market, dict):
            continue
        market_id = str(market.get("id") or market.get("conditionId") or "")
        condition_id = str(market.get("conditionId") or "")
        if not market_id or not condition_id:
            continue
        opened_at = market.get("createdAt") or market.get("startDate")
        closed_at = market.get("closedTime") or market.get("endDate")
        discovery = discovery_by_condition.get(condition_id, {})
        if _timestamp_in_year(opened_at, year):
            records.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "source_key": "polymarket",
                    "record_type": "prediction_market_open",
                    "event_timestamp": opened_at,
                    "source_available_at": opened_at,
                    "market_id": market_id,
                    "condition_id": condition_id,
                    "question": market.get("question"),
                    "category": market.get("category"),
                    "clob_token_ids": market.get("clobTokenIds"),
                    "matched_research_terms": discovery.get("matched_terms", []),
                    "price_history_state": "official_clob_daily_history_acquired_where_available",
                    "point_in_time_safe": True,
                    "vintage_state": "market_open_metadata_without_future_outcome",
                }
            )
        tokens = _json_string_list(market.get("clobTokenIds"))
        outcomes = _json_string_list(market.get("outcomes"))
        for token_index, token_id in enumerate(tokens):
            history, history_payload, calls = _polymarket_token_history(
                token_id,
                timeout_seconds=timeout_seconds,
            )
            history_calls += calls
            history_payloads.append(
                {
                    "condition_id": condition_id,
                    "token_id": token_id,
                    **history_payload,
                }
            )
            for point in history:
                observed_at = _epoch_seconds_iso(point.get("t"))
                if observed_at is None or not _timestamp_in_year(observed_at, year):
                    continue
                records.append(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "source_key": "polymarket",
                        "record_type": "prediction_market_daily_price",
                        "event_timestamp": observed_at,
                        "source_available_at": observed_at,
                        "market_id": market_id,
                        "condition_id": condition_id,
                        "question": market.get("question"),
                        "token_id": token_id,
                        "outcome": outcomes[token_index] if token_index < len(outcomes) else None,
                        "price": point.get("p"),
                        "matched_research_terms": discovery.get("matched_terms", []),
                        "point_in_time_safe": True,
                        "vintage_state": "official_clob_historical_price_point",
                    }
                )
        if _timestamp_in_year(closed_at, year) and market.get("closed") is True:
            records.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "source_key": "polymarket",
                    "record_type": "prediction_market_settlement",
                    "event_timestamp": closed_at,
                    "source_available_at": closed_at,
                    "market_id": market_id,
                    "condition_id": condition_id,
                    "question": market.get("question"),
                    "outcomes": market.get("outcomes"),
                    "outcome_prices": market.get("outcomePrices"),
                    "point_in_time_safe": True,
                    "vintage_state": "outcome_available_at_market_close_only",
                }
            )
    raw_bundle = {
        "oddspipe_discovery": discovery_payloads,
        "official_market_metadata": market_payloads,
        "official_token_price_history": history_payloads,
    }
    raw = json.dumps(raw_bundle, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return raw, records, {
        "endpoint": "https://gamma-api.polymarket.com/markets",
        "price_history_endpoint": "https://clob.polymarket.com/prices-history",
        "discovery_endpoint": "https://oddspipe.com/v1/markets/search",
        "discovery_role": "bounded_macro_contract_identity_only",
        "historical_evidence_provider": "Polymarket official Gamma and CLOB APIs",
        "provider_call_count": discovery_calls + metadata_calls + history_calls,
        "discovered_market_count": len(discoveries),
        "official_market_count": len(all_markets),
        "selection_scope": "resolved_macro_relevant_contracts",
        "full_exchange_universe_claimed": False,
        "credentials_recorded": False,
        "fetched_at": fetched_at,
        "empty_reason": "no_macro_relevant_provider_records_for_partition",
        "price_history_state": "official_daily_history_acquired_where_available",
    }


def _alpaca_link_partition(
    year: int,
    *,
    price_manifest: dict[str, Any],
) -> tuple[bytes, list[dict[str, Any]], dict[str, Any]]:
    records: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []
    for job in price_manifest.get("jobs", []):
        if job.get("provider") != "alpaca_market_data_v2":
            continue
        if str(job.get("date_partition")) != str(year) or job.get("status") != "complete":
            continue
        symbol = str(job.get("instrument") or "")
        path = RESEARCH_ROOT / "prices" / f"symbol={symbol}" / "interval=1d" / f"year={year}" / "bars.jsonl"
        if not path.is_file():
            continue
        references.append(
            {
                "symbol": symbol,
                "path": str(path.relative_to(ROOT)),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            bar = json.loads(line)
            records.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "source_key": "alpaca",
                    "symbol": symbol,
                    "event_timestamp": bar.get("observed_at"),
                    "source_available_at": bar.get("available_at"),
                    "close": bar.get("close"),
                    "volume": bar.get("volume"),
                    "raw_ref": str(path.relative_to(ROOT)),
                    "point_in_time_safe": True,
                    "vintage_state": "adjusted_daily_market_bar",
                }
            )
    raw = json.dumps({"references": references}, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return raw, records, {
        "endpoint": "local_link_to_alpaca_provider_backed_price_partitions",
        "linked_partition_count": len(references),
        "credentials_recorded": False,
        "fetched_at": now_iso(),
    }


NETWORK_FETCHERS: dict[
    str,
    Callable[..., tuple[bytes, list[dict[str, Any]], dict[str, Any]]],
] = {
    "bis": _bis_partition,
    "bls": _bls_partition,
    "ecb": _ecb_partition,
    "kalshi": _kalshi_partition,
    "polymarket": _polymarket_partition,
    "usgs": _usgs_partition,
    "sec_edgar": _sec_partition,
    "stock_act": _house_disclosure_partition,
    "ucdp": _ucdp_partition,
}


def _pid_is_running(pid: Any) -> bool:
    try:
        process_id = int(pid)
    except (TypeError, ValueError):
        return False
    if process_id <= 0:
        return False
    try:
        os.kill(process_id, 0)
    except (OSError, PermissionError):
        return False
    return True


def _recover_interrupted_jobs(jobs: list[dict[str, Any]]) -> int:
    recovered = 0
    for job in jobs:
        if job.get("status") != "running" or _pid_is_running(job.get("runner_pid")):
            continue
        job.update(
            {
                "status": "retryable_failure",
                "failure_category": "interrupted_previous_run",
                "last_error_type": "InterruptedRun",
                "recovered_at": now_iso(),
                "runner_pid": None,
            }
        )
        recovered += 1
    return recovered


def _classify_deferred_source_jobs(
    jobs: list[dict[str, Any]],
    *,
    source_keys: tuple[str, ...] = (),
) -> tuple[int, list[dict[str, Any]]]:
    classified_at = now_iso()
    selected_sources = set(source_keys) if source_keys else set(DEFERRED_SOURCE_CLASSIFICATIONS)
    newly_classified = 0
    actions: list[dict[str, Any]] = []
    for source, classification in DEFERRED_SOURCE_CLASSIFICATIONS.items():
        if source not in selected_sources:
            continue
        source_jobs = [job for job in jobs if job.get("source") == source]
        for job in source_jobs:
            if str(job.get("status") or "") not in RETRYABLE_JOB_STATES:
                continue
            job.update(
                {
                    "status": "unavailable_classified",
                    "failure_category": classification["typed_reason"],
                    "typed_unavailable_reason": classification["typed_reason"],
                    "classification_state": classification["current_state"],
                    "classified_at": classified_at,
                    "operator_action_required": True,
                    "operator_action": classification["operator_action"],
                    "retry_class": "operator_action_then_idempotent_read",
                    "row_count": 0,
                    "evidence_credit_allowed": False,
                    "proxy_credit_allowed": False,
                    "credentials_recorded": False,
                    "runner_pid": None,
                }
            )
            newly_classified += 1
        actions.append(
            {
                "source_key": source,
                "status": "operator_action_required_for_full_historical_coverage",
                "typed_reason": classification["typed_reason"],
                "current_state": classification["current_state"],
                "operator_action": classification["operator_action"],
                "partition_count": len(source_jobs),
                "unavailable_classified_partition_count": sum(
                    job.get("status") == "unavailable_classified" for job in source_jobs
                ),
                "evidence_credit_allowed": False,
                "or3_terminal_classification_allowed": True,
                "authority": authority_flags(),
            }
        )
    return newly_classified, actions


def _write_partition(
    job: dict[str, Any],
    raw: bytes,
    records: list[dict[str, Any]],
    request_metadata: dict[str, Any],
) -> dict[str, Any]:
    source = str(job["source"])
    year = str(job["date_partition"])
    raw_root = RESEARCH_ROOT / "raw" / f"source={source}" / f"date={year}"
    normalized_root = RESEARCH_ROOT / "normalized" / f"source={source}" / f"date={year}"
    safe_job = str(job["job_id"]).replace(":", "_")
    raw_extension = str(request_metadata.get("raw_extension") or "json").strip(".")
    raw_path = raw_root / f"{safe_job}.{raw_extension}"
    normalized_path = normalized_root / "records.jsonl"
    metadata_path = normalized_root / "metadata.json"
    encoded = b"".join(
        (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        for record in records
    )
    _atomic_bytes(raw_path, raw)
    _atomic_bytes(normalized_path, encoded)
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_source_history_partition_metadata",
        "generated_at": now_iso(),
        "job_id": job["job_id"],
        "source_key": source,
        "provider": job.get("provider"),
        "date_partition": year,
        "request": request_metadata,
        "raw_payload_path": str(raw_path.relative_to(ROOT)),
        "raw_payload_sha256": _sha256(raw),
        "normalized_path": str(normalized_path.relative_to(ROOT)),
        "normalized_sha256": _sha256(encoded),
        "normalized_row_count": len(records),
        "point_in_time_safe_row_count": sum(
            record.get("point_in_time_safe") is True for record in records
        ),
        "current_revision_only_row_count": sum(
            record.get("point_in_time_safe") is not True for record in records
        ),
        "parser_version": SCHEMA_VERSION,
        "credentials_recorded": False,
        "authority": authority_flags(),
    }
    _atomic_bytes(
        metadata_path,
        (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    metadata["metadata_path"] = str(metadata_path.relative_to(ROOT))
    return metadata


def run_source_history_acquisition(
    settings: Settings | None = None,
    *,
    options: SourceHistoryOptions,
) -> tuple[dict[str, Any], list[str]]:
    active = settings or Settings.from_env()
    runtime = runtime_dir(active)
    store = AtomicArtifactStore(runtime)
    manifest = read_json(runtime / SOURCE_MANIFEST_ARTIFACT)
    price_manifest = read_json(runtime / PRICE_MANIFEST_ARTIFACT)
    jobs = manifest.get("jobs") if isinstance(manifest.get("jobs"), list) else []
    errors: list[str] = []
    if not jobs:
        return {}, ["source_backfill_manifest_missing"]
    if not options.provider_terms_reviewed:
        return {}, ["provider_terms_review_not_confirmed"]

    recovered_interrupted_jobs = _recover_interrupted_jobs(jobs)
    if recovered_interrupted_jobs:
        manifest["generated_at"] = now_iso()
        store.write_json(SOURCE_MANIFEST_ARTIFACT, manifest)

    classified_deferred_job_count = 0
    deferred_actions: list[dict[str, Any]] = []
    if options.classify_deferred:
        classified_deferred_job_count, deferred_actions = _classify_deferred_source_jobs(
            jobs,
            source_keys=options.source_keys,
        )
        manifest["generated_at"] = now_iso()
        store.write_json(SOURCE_MANIFEST_ARTIFACT, manifest)
        store.write_json(
            DEFERRED_ACTIONS_ARTIFACT,
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_or3_deferred_source_actions",
                "generated_at": now_iso(),
                "status": (
                    "operator_action_required_for_full_historical_coverage"
                    if deferred_actions
                    else "no_deferred_sources_selected"
                ),
                "or3_manifest_can_close_with_typed_classifications": True,
                "or4_must_not_grant_missing_history_evidence_credit": True,
                "newly_classified_partition_count": classified_deferred_job_count,
                "actions": deferred_actions,
                "authority": authority_flags(),
            },
        )

    processed = 0
    attempted = 0
    for job in jobs:
        source = str(job.get("source") or "")
        if source not in SUPPORTED_NETWORK_SOURCES | SUPPORTED_LOCAL_SOURCES:
            continue
        if options.source_keys and source not in options.source_keys:
            continue
        job_status = str(job.get("status") or "")
        if options.resume and job_status in {"complete", "unavailable_classified"}:
            continue
        refreshable = not options.resume and job_status in {
            "complete",
            "unavailable_classified",
        }
        if job_status not in RETRYABLE_JOB_STATES and not refreshable:
            continue
        if options.max_jobs and processed >= options.max_jobs:
            break
        if source in SUPPORTED_NETWORK_SOURCES and not options.allow_network:
            continue
        attempted += 1
        year = int(job["date_partition"])
        job.update(
            {
                "status": "running",
                "started_at": now_iso(),
                "last_attempt_at": now_iso(),
                "attempt_count": int(job.get("attempt_count") or 0) + 1,
                "runner_pid": os.getpid(),
            }
        )
        store.write_json(SOURCE_MANIFEST_ARTIFACT, manifest)
        try:
            if source == "alpaca":
                raw, records, request_metadata = _alpaca_link_partition(
                    year,
                    price_manifest=price_manifest,
                )
            else:
                raw, records, request_metadata = NETWORK_FETCHERS[source](
                    year,
                    settings=active,
                    timeout_seconds=options.timeout_seconds,
                )
            metadata = _write_partition(job, raw, records, request_metadata)
            empty_reason = str(
                request_metadata.get("empty_reason") or "provider_valid_empty_partition"
            )
            job.update(
                {
                    "status": "complete" if records else "unavailable_classified",
                    "completed_at": now_iso(),
                    "row_count": len(records),
                    "checksum": metadata["normalized_sha256"],
                    "normalized_path": metadata["normalized_path"],
                    "metadata_path": metadata["metadata_path"],
                    "point_in_time_safe_row_count": metadata[
                        "point_in_time_safe_row_count"
                    ],
                    "current_revision_only_row_count": metadata[
                        "current_revision_only_row_count"
                    ],
                    "failure_category": None if records else empty_reason,
                    "typed_unavailable_reason": None if records else empty_reason,
                    "credentials_recorded": False,
                    "runner_pid": None,
                }
            )
        except KeyboardInterrupt:
            job.update(
                {
                    "status": "retryable_failure",
                    "failure_category": "interrupted_current_run",
                    "last_error_type": "KeyboardInterrupt",
                    "runner_pid": None,
                }
            )
            manifest["generated_at"] = now_iso()
            store.write_json(SOURCE_MANIFEST_ARTIFACT, manifest)
            raise
        except Exception as exc:  # noqa: BLE001 - classified safe read failure
            category = "rate_limited" if "429" in repr(exc) else "provider_read_failure"
            job.update(
                {
                    "status": "retryable_failure",
                    "failure_category": category,
                    "last_error_type": exc.__class__.__name__,
                    "runner_pid": None,
                }
            )
            errors.append(f"{job.get('job_id')}:{category}:{exc.__class__.__name__}")
        processed += 1
        store.write_json(SOURCE_MANIFEST_ARTIFACT, manifest)
        if options.sleep_between_calls > 0:
            time.sleep(options.sleep_between_calls)

    status_counts: dict[str, int] = {}
    for job in jobs:
        status = str(job.get("status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    result = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_source_history_acquisition",
        "generated_at": now_iso(),
        "status": "complete_for_supported_sources" if not errors else "degraded",
        "supported_sources": sorted(SUPPORTED_NETWORK_SOURCES | SUPPORTED_LOCAL_SOURCES),
        "processed_job_count": processed,
        "attempted_job_count": attempted,
        "recovered_interrupted_job_count": recovered_interrupted_jobs,
        "classified_deferred_job_count": classified_deferred_job_count,
        "deferred_source_action_count": len(deferred_actions),
        "status_counts": dict(sorted(status_counts.items())),
        "errors": errors,
        "credentials_recorded": False,
        "paper_trial_calendar_advanced": False,
        "trade_candidate_created_count": 0,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "authority": authority_flags(),
    }
    store.write_json(RUN_ARTIFACT, result)
    return result, errors
