"""Source adapter contracts and read-only public source adapters."""

from __future__ import annotations

import asyncio
import csv
import hashlib
import io
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
from statistics import fmean, pstdev
from typing import Any
from uuid import uuid4

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.secrets import secret_value

UNIFIED_EVENT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class UnifiedEvent:
    schema_version: int
    event_id: str
    source: str
    trust_score_at_ingestion: float
    event_type: str
    raw_payload: dict[str, Any]
    normalised_summary: str
    coordinates: dict[str, float] | None
    ingested_at: str
    linked_catalyst_id: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SourceEnvelope:
    events: tuple[UnifiedEvent, ...]
    source: str
    trust_score: float
    fetched_at: str
    degraded: bool
    degraded_reason: str | None
    raw_archive_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["events"] = [event.to_dict() for event in self.events]
        return payload


class RawPayloadArchive:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self.root = Path(self.settings.raw_payload_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    def write(self, source_key: str, payload: dict[str, Any]) -> Path:
        now = datetime.now(timezone.utc)
        folder = self.root / source_key / now.strftime("%Y-%m-%d")
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{now.strftime('%H%M%S')}-{uuid4()}.json"
        path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")
        return path


class GDELTAdapter:
    source_key = "gdelt"
    source_name = "GDELT Project API"
    source_label = "conflict.gdelt"
    base_url = "https://api.gdeltproject.org/api/v2/doc/doc"
    trust_score = 0.65

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

    @staticmethod
    def _gdelt_datetime(value: datetime) -> str:
        return value.astimezone(timezone.utc).strftime("%Y%m%d%H%M%S")

    @staticmethod
    def _parse_since(since_iso: str | None) -> datetime:
        if not since_iso:
            return datetime.now(timezone.utc) - timedelta(hours=6)
        parsed = datetime.fromisoformat(since_iso.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed

    def request_params(
        self,
        *,
        query: str,
        since_iso: str | None = None,
        theme_code: str | None = None,
        maxrecords: int = 25,
    ) -> dict[str, str]:
        since = self._parse_since(since_iso)
        params = {
            "query": query,
            "mode": "ArtList",
            "maxrecords": str(max(1, min(maxrecords, 250))),
            "startdatetime": self._gdelt_datetime(since),
            "format": "json",
            "SOURCELANG": "eng",
        }
        if theme_code:
            params["THEME"] = theme_code
        return params

    def sample_payload(self, query: str = "oil") -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        return {
            "articles": [
                {
                    "url": "https://example.com/qadam/gdelt/oil-shipping-risk",
                    "title": "Shipping risk rises near a key energy corridor",
                    "seendate": now,
                    "domain": "example.com",
                    "language": "English",
                    "sourcecountry": "United States",
                },
                {
                    "url": "https://example.com/qadam/gdelt/chip-export-controls",
                    "title": "Chip export controls become focus of renewed US China negotiations",
                    "seendate": now,
                    "domain": "example.com",
                    "language": "English",
                    "sourcecountry": "United States",
                },
            ],
            "query": query,
            "sample": True,
        }

    def normalize_payload(self, payload: dict[str, Any]) -> tuple[UnifiedEvent, ...]:
        events: list[UnifiedEvent] = []
        articles = payload.get("articles")
        if not isinstance(articles, list):
            return ()

        for article in articles:
            if not isinstance(article, dict):
                continue
            title = str(article.get("title") or "Untitled GDELT article")
            url = str(article.get("url") or "")
            seen = str(article.get("seendate") or datetime.now(timezone.utc).isoformat())
            summary = title[:240]
            events.append(
                UnifiedEvent(
                    schema_version=UNIFIED_EVENT_SCHEMA_VERSION,
                    event_id=str(uuid4()),
                    source=self.source_label,
                    trust_score_at_ingestion=self.trust_score,
                    event_type="conflict_event",
                    raw_payload={
                        "url": url,
                        "title": title,
                        "domain": article.get("domain"),
                        "sourcecountry": article.get("sourcecountry"),
                        "language": article.get("language"),
                    },
                    normalised_summary=summary,
                    coordinates=None,
                    ingested_at=seen,
                    linked_catalyst_id=None,
                )
            )
        return tuple(events)

    def envelope_from_payload(
        self,
        payload: dict[str, Any],
        *,
        archive: bool = True,
        degraded: bool = False,
        degraded_reason: str | None = None,
    ) -> SourceEnvelope:
        archive_path = self.archive.write(self.source_key, payload) if archive else None
        events = self.normalize_payload(payload)
        envelope = SourceEnvelope(
            events=events,
            source=self.source_label,
            trust_score=self.trust_score,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            degraded=degraded,
            degraded_reason=degraded_reason,
            raw_archive_path=str(archive_path) if archive_path else None,
        )
        self.event_log.write(
            "source_adapter_fetch_completed",
            "gdelt_adapter",
            {
                "source": self.source_label,
                "event_count": len(events),
                "degraded": degraded,
                "raw_archive_path": envelope.raw_archive_path,
            },
        )
        return envelope

    async def fetch_live(
        self,
        *,
        query: str = "oil",
        since_iso: str | None = None,
        theme_code: str | None = None,
        maxrecords: int = 25,
        timeout_seconds: float = 12.0,
    ) -> SourceEnvelope:
        try:
            import httpx
        except ImportError as exc:
            raise RuntimeError("httpx is not installed. Run scripts/bootstrap_runtime.sh first.") from exc

        params = self.request_params(
            query=query,
            since_iso=since_iso,
            theme_code=theme_code,
            maxrecords=maxrecords,
        )
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            payload = {
                "articles": [],
                "_qadam_request": {"url": self.base_url, "params": params},
                "_qadam_error_type": exc.__class__.__name__,
                "_qadam_error": repr(exc),
            }
            return self.envelope_from_payload(
                payload,
                degraded=True,
                degraded_reason=f"gdelt_http_error:{exc.__class__.__name__}",
            )
        payload["_qadam_request"] = {"url": self.base_url, "params": params}
        return self.envelope_from_payload(payload)

    def fetch_sample(self, *, query: str = "oil") -> SourceEnvelope:
        return self.envelope_from_payload(self.sample_payload(query=query))


def gdelt_adapter_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    archive_root = Path(settings.raw_payload_dir) / GDELTAdapter.source_key
    return {
        "key": GDELTAdapter.source_key,
        "source": GDELTAdapter.source_label,
        "mode": "sample_ready_live_optional",
        "auth": "none",
        "trust_score": GDELTAdapter.trust_score,
        "raw_archive_root": str(archive_root),
        "raw_archive_exists": archive_root.exists(),
        "live_boundary": "Read-only. No trading or signal confidence changes from adapter output alone.",
    }


def fetch_gdelt_sample(query: str = "oil") -> dict[str, Any]:
    return GDELTAdapter().fetch_sample(query=query).to_dict()


async def fetch_gdelt_live(
    query: str = "oil",
    since_iso: str | None = None,
    theme_code: str | None = None,
    maxrecords: int = 25,
) -> dict[str, Any]:
    envelope = await GDELTAdapter().fetch_live(
        query=query,
        since_iso=since_iso,
        theme_code=theme_code,
        maxrecords=maxrecords,
    )
    return envelope.to_dict()


def fetch_gdelt_live_sync(
    query: str = "oil",
    since_iso: str | None = None,
    theme_code: str | None = None,
    maxrecords: int = 25,
) -> dict[str, Any]:
    return asyncio.run(fetch_gdelt_live(query, since_iso, theme_code, maxrecords))


class OrefAdapter:
    source_key = "oref"
    source_name = "Oref API"
    source_label = "conflict.oref"
    base_url = "https://www.oref.org.il/WarningMessages/alert/alerts.json"
    trust_score = 0.95

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
        now = datetime.now(timezone.utc).isoformat()
        return {
            "alerts": [
                {
                    "id": "sample-oref-1",
                    "cat": "Rocket and missile fire",
                    "title": "Red Alert",
                    "data": ["Ashkelon", "Zikim"],
                    "desc": "Enter the protected space",
                    "alertDate": now,
                }
            ],
            "sample": True,
        }

    @staticmethod
    def _coerce_payload(payload: Any) -> dict[str, Any]:
        if isinstance(payload, list):
            return {"alerts": payload}
        if isinstance(payload, dict):
            if "alerts" in payload:
                return payload
            if not payload:
                return {"alerts": [], "empty_response": True}
            return {"alerts": [payload]}
        return {"alerts": [], "unexpected_payload_type": type(payload).__name__}

    def normalize_payload(self, payload: dict[str, Any]) -> tuple[UnifiedEvent, ...]:
        events: list[UnifiedEvent] = []
        alerts = payload.get("alerts")
        if not isinstance(alerts, list):
            return ()

        for alert in alerts:
            if not isinstance(alert, dict):
                continue
            areas_raw = alert.get("data", [])
            if isinstance(areas_raw, str):
                areas = [areas_raw]
            elif isinstance(areas_raw, list):
                areas = [str(area) for area in areas_raw if str(area).strip()]
            else:
                areas = []

            category = str(alert.get("cat") or alert.get("title") or "alert")
            title = str(alert.get("title") or category)
            alert_date = str(alert.get("alertDate") or datetime.now(timezone.utc).isoformat())
            area_text = ", ".join(areas) if areas else "unknown zone"
            summary = f"Red alert in {area_text} ({category})"

            events.append(
                UnifiedEvent(
                    schema_version=UNIFIED_EVENT_SCHEMA_VERSION,
                    event_id=str(uuid4()),
                    source=self.source_label,
                    trust_score_at_ingestion=self.trust_score,
                    event_type="conflict_event",
                    raw_payload={
                        "id": alert.get("id"),
                        "cat": category,
                        "title": title,
                        "data": areas,
                        "desc": alert.get("desc"),
                    },
                    normalised_summary=summary[:240],
                    coordinates=None,
                    ingested_at=alert_date,
                    linked_catalyst_id=None,
                )
            )
        return tuple(events)

    def envelope_from_payload(
        self,
        payload: dict[str, Any],
        *,
        archive: bool = True,
        degraded: bool = False,
        degraded_reason: str | None = None,
    ) -> SourceEnvelope:
        archive_path = self.archive.write(self.source_key, payload) if archive else None
        events = self.normalize_payload(payload)
        envelope = SourceEnvelope(
            events=events,
            source=self.source_label,
            trust_score=self.trust_score,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            degraded=degraded,
            degraded_reason=degraded_reason,
            raw_archive_path=str(archive_path) if archive_path else None,
        )
        self.event_log.write(
            "source_adapter_fetch_completed",
            "oref_adapter",
            {
                "source": self.source_label,
                "event_count": len(events),
                "degraded": degraded,
                "raw_archive_path": envelope.raw_archive_path,
            },
        )
        return envelope

    async def fetch_live(self, *, timeout_seconds: float = 12.0) -> SourceEnvelope:
        try:
            import httpx
        except ImportError as exc:
            raise RuntimeError("httpx is not installed. Run scripts/bootstrap_runtime.sh first.") from exc

        headers = {
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.oref.org.il/",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Qadam/0.1 read-only source adapter",
        }
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
                response = await client.get(self.base_url, headers=headers)
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                if "json" not in content_type.lower() and response.text.lstrip().startswith("<"):
                    payload = {
                        "alerts": [],
                        "_qadam_request": {"url": self.base_url, "headers": "oref_required_headers"},
                        "_qadam_error_type": "UnexpectedContentType",
                        "_qadam_error": content_type,
                    }
                    return self.envelope_from_payload(
                        payload,
                        degraded=True,
                        degraded_reason="oref_unexpected_content_type",
                    )
                payload = self._coerce_payload(response.json())
        except (httpx.HTTPError, ValueError) as exc:
            payload = {
                "alerts": [],
                "_qadam_request": {"url": self.base_url, "headers": "oref_required_headers"},
                "_qadam_error_type": exc.__class__.__name__,
                "_qadam_error": repr(exc),
            }
            return self.envelope_from_payload(
                payload,
                degraded=True,
                degraded_reason=f"oref_http_or_parse_error:{exc.__class__.__name__}",
            )
        payload["_qadam_request"] = {"url": self.base_url, "headers": "oref_required_headers"}
        return self.envelope_from_payload(payload)

    def fetch_sample(self) -> SourceEnvelope:
        return self.envelope_from_payload(self.sample_payload())


def oref_adapter_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    archive_root = Path(settings.raw_payload_dir) / OrefAdapter.source_key
    return {
        "key": OrefAdapter.source_key,
        "source": OrefAdapter.source_label,
        "mode": "sample_ready_live_optional",
        "auth": "none",
        "trust_score": OrefAdapter.trust_score,
        "raw_archive_root": str(archive_root),
        "raw_archive_exists": archive_root.exists(),
        "live_boundary": "Read-only. Empty live alerts are healthy; timeouts or HTML responses become degraded.",
    }


def fetch_oref_sample() -> dict[str, Any]:
    return OrefAdapter().fetch_sample().to_dict()


async def fetch_oref_live() -> dict[str, Any]:
    envelope = await OrefAdapter().fetch_live()
    return envelope.to_dict()


def fetch_oref_live_sync() -> dict[str, Any]:
    return asyncio.run(fetch_oref_live())


DEFAULT_FRED_SERIES: tuple[dict[str, str], ...] = (
    {"series_id": "DFF", "title": "Fed Funds Rate"},
    {"series_id": "DGS10", "title": "10-Year Treasury Yield"},
    {"series_id": "DGS2", "title": "2-Year Treasury Yield"},
    {"series_id": "T10Y2Y", "title": "10Y-2Y Yield Curve"},
    {"series_id": "DTWEXBGS", "title": "Broad Dollar Index"},
    {"series_id": "VIXCLS", "title": "VIX"},
    {"series_id": "BAMLH0A0HYM2", "title": "HY Credit Spread"},
    {"series_id": "IORB", "title": "Interest on Reserve Balances"},
    {"series_id": "DCOILWTICO", "title": "WTI Crude Oil"},
)


def _parse_float(value: Any) -> float | None:
    try:
        text = str(value).strip()
        if not text or text == ".":
            return None
        return float(text)
    except (TypeError, ValueError):
        return None


def _series_title(series_id: str) -> str:
    for series in DEFAULT_FRED_SERIES:
        if series["series_id"] == series_id:
            return series["title"]
    return series_id


class FREDAdapter:
    source_key = "fred"
    source_name = "FRED API"
    source_label = "macro.fred"
    base_url = "https://api.stlouisfed.org/fred/series/observations"
    csv_base_url = "https://fred.stlouisfed.org/graph/fredgraph.csv"
    trust_score = 0.90

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

    def sample_payload(self, series_ids: tuple[str, ...] = ()) -> dict[str, Any]:
        today = datetime.now(timezone.utc).date()
        requested = series_ids or ("DGS10", "T10Y2Y", "DCOILWTICO")
        baseline_values = {
            "DGS10": (4.31, 4.36, 4.40, 4.45),
            "T10Y2Y": (-0.36, -0.33, -0.29, -0.24),
            "DCOILWTICO": (77.4, 78.2, 80.1, 81.6),
            "DFF": (5.33, 5.33, 5.33, 5.33),
            "DGS2": (4.78, 4.75, 4.70, 4.66),
            "DTWEXBGS": (124.6, 124.9, 125.1, 125.5),
            "VIXCLS": (14.9, 15.5, 16.8, 18.1),
            "BAMLH0A0HYM2": (3.19, 3.24, 3.31, 3.42),
            "IORB": (5.40, 5.40, 5.40, 5.40),
        }
        series_payloads: list[dict[str, Any]] = []
        for series_id in requested:
            values = baseline_values.get(series_id, (1.0, 1.1, 1.2, 1.3))
            observations = [
                {
                    "date": (today - timedelta(days=len(values) - index - 1)).isoformat(),
                    "value": value,
                }
                for index, value in enumerate(values)
            ]
            series_payloads.append(
                {
                    "series_id": series_id,
                    "title": _series_title(series_id),
                    "observations": observations,
                    "access_mode": "sample",
                }
            )
        return {"series": series_payloads, "sample": True}

    def normalize_payload(
        self,
        payload: dict[str, Any],
        *,
        alert_on_sigma: float | None = None,
    ) -> tuple[UnifiedEvent, ...]:
        events: list[UnifiedEvent] = []
        series_list = payload.get("series")
        if not isinstance(series_list, list):
            return ()

        for series in series_list:
            if not isinstance(series, dict):
                continue
            series_id = str(series.get("series_id") or "").strip()
            title = str(series.get("title") or _series_title(series_id))
            observations = series.get("observations")
            if not series_id or not isinstance(observations, list):
                continue

            cleaned: list[tuple[str, float]] = []
            for observation in observations:
                if not isinstance(observation, dict):
                    continue
                date = str(observation.get("date") or "").strip()
                value = _parse_float(observation.get("value"))
                if date and value is not None:
                    cleaned.append((date, value))
            if not cleaned:
                continue

            cleaned.sort(key=lambda item: item[0])
            latest_date, latest_value = cleaned[-1]
            previous_value = cleaned[-2][1] if len(cleaned) >= 2 else None
            previous_window = [value for _, value in cleaned[-21:-1]]
            mean_value = fmean(previous_window) if previous_window else latest_value
            sigma_base = pstdev(previous_window) if len(previous_window) >= 2 else 0.0
            sigma = (latest_value - mean_value) / sigma_base if sigma_base else 0.0
            if alert_on_sigma is not None and abs(sigma) < alert_on_sigma:
                continue

            delta = latest_value - previous_value if previous_value is not None else 0.0
            pct_change = (delta / previous_value * 100) if previous_value not in (None, 0.0) else 0.0
            summary = (
                f"{series_id} {title} latest {latest_value:g} on {latest_date}; "
                f"delta {delta:+.3g} ({pct_change:+.2f}%), {sigma:+.2f} sigma"
            )
            events.append(
                UnifiedEvent(
                    schema_version=UNIFIED_EVENT_SCHEMA_VERSION,
                    event_id=str(uuid4()),
                    source=self.source_label,
                    trust_score_at_ingestion=self.trust_score,
                    event_type="macro_shift",
                    raw_payload={
                        "series_id": series_id,
                        "title": title,
                        "date": latest_date,
                        "value": latest_value,
                        "previous_value": previous_value,
                        "delta": delta,
                        "pct_change": pct_change,
                        "sigma": sigma,
                        "access_mode": series.get("access_mode"),
                    },
                    normalised_summary=summary[:240],
                    coordinates=None,
                    ingested_at=f"{latest_date}T00:00:00+00:00",
                    linked_catalyst_id=None,
                )
            )
        return tuple(events)

    def envelope_from_payload(
        self,
        payload: dict[str, Any],
        *,
        alert_on_sigma: float | None = None,
        archive: bool = True,
        degraded: bool = False,
        degraded_reason: str | None = None,
    ) -> SourceEnvelope:
        archive_path = self.archive.write(self.source_key, payload) if archive else None
        events = self.normalize_payload(payload, alert_on_sigma=alert_on_sigma)
        envelope = SourceEnvelope(
            events=events,
            source=self.source_label,
            trust_score=self.trust_score,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            degraded=degraded,
            degraded_reason=degraded_reason,
            raw_archive_path=str(archive_path) if archive_path else None,
        )
        self.event_log.write(
            "source_adapter_fetch_completed",
            "fred_adapter",
            {
                "source": self.source_label,
                "event_count": len(events),
                "degraded": degraded,
                "raw_archive_path": envelope.raw_archive_path,
            },
        )
        return envelope

    async def _fetch_series_via_api(
        self,
        client: Any,
        *,
        series_id: str,
        api_key: str,
        observation_start: str,
        limit: int,
    ) -> dict[str, Any]:
        response = await client.get(
            self.base_url,
            params={
                "series_id": series_id,
                "api_key": api_key,
                "file_type": "json",
                "observation_start": observation_start,
                "sort_order": "desc",
                "limit": str(limit),
            },
        )
        response.raise_for_status()
        body = response.json()
        observations = body.get("observations", [])
        if not isinstance(observations, list):
            observations = []
        return {
            "series_id": series_id,
            "title": _series_title(series_id),
            "observations": [
                {"date": item.get("date"), "value": item.get("value")}
                for item in observations
                if isinstance(item, dict)
            ],
            "access_mode": "fred_api",
            "api_key_configured": True,
        }

    async def _fetch_series_via_csv(
        self,
        client: Any,
        *,
        series_id: str,
        observation_start: str,
        limit: int,
    ) -> dict[str, Any]:
        response = await client.get(self.csv_base_url, params={"id": series_id, "cosd": observation_start})
        response.raise_for_status()
        reader = csv.DictReader(io.StringIO(response.text))
        rows: list[dict[str, Any]] = []
        for row in reader:
            date = row.get("observation_date") or row.get("DATE") or row.get("date")
            value = row.get(series_id)
            if date and _parse_float(value) is not None:
                rows.append({"date": date, "value": value})
        return {
            "series_id": series_id,
            "title": _series_title(series_id),
            "observations": rows[-limit:],
            "access_mode": "fred_public_csv",
            "api_key_configured": False,
        }

    async def fetch_live(
        self,
        *,
        series_ids: tuple[str, ...] = (),
        observation_start: str | None = None,
        limit: int = 45,
        alert_on_sigma: float | None = None,
        timeout_seconds: float = 12.0,
    ) -> SourceEnvelope:
        try:
            import httpx
        except ImportError as exc:
            raise RuntimeError("httpx is not installed. Run scripts/bootstrap_runtime.sh first.") from exc

        requested = series_ids or tuple(series["series_id"] for series in DEFAULT_FRED_SERIES)
        observation_start = observation_start or (datetime.now(timezone.utc).date() - timedelta(days=120)).isoformat()
        limit = max(2, min(limit, 120))
        api_key = secret_value("FRED_API_KEY", self.settings)
        fetched: list[dict[str, Any]] = []
        failures: list[dict[str, str]] = []
        headers = {
            "Accept": "application/json, text/csv, */*",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Safari/537.36",
        }

        async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True, headers=headers) as client:
            for series_id in requested:
                try:
                    if api_key:
                        fetched.append(
                            await self._fetch_series_via_api(
                                client,
                                series_id=series_id,
                                api_key=api_key,
                                observation_start=observation_start,
                                limit=limit,
                            )
                        )
                    else:
                        fetched.append(
                            await self._fetch_series_via_csv(
                                client,
                                series_id=series_id,
                                observation_start=observation_start,
                                limit=limit,
                            )
                        )
                except (httpx.HTTPError, ValueError) as exc:
                    failures.append({"series_id": series_id, "reason": exc.__class__.__name__})

        payload = {
            "series": fetched,
            "failures": failures,
            "_qadam_request": {
                "series_ids": list(requested),
                "observation_start": observation_start,
                "limit": limit,
                "access_mode": "fred_api" if api_key else "fred_public_csv",
                "api_key_configured": bool(api_key),
            },
        }
        degraded = bool(failures) and not fetched
        degraded_reason = "fred_all_series_failed" if degraded else ("fred_partial_series_failures" if failures else None)
        return self.envelope_from_payload(
            payload,
            alert_on_sigma=alert_on_sigma,
            degraded=degraded,
            degraded_reason=degraded_reason,
        )

    def fetch_sample(
        self,
        *,
        series_ids: tuple[str, ...] = (),
        alert_on_sigma: float | None = None,
    ) -> SourceEnvelope:
        return self.envelope_from_payload(
            self.sample_payload(series_ids=series_ids),
            alert_on_sigma=alert_on_sigma,
        )


def fred_adapter_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    archive_root = Path(settings.raw_payload_dir) / FREDAdapter.source_key
    return {
        "key": FREDAdapter.source_key,
        "source": FREDAdapter.source_label,
        "mode": "sample_ready_live_optional",
        "auth": "optional_api_key_with_public_csv_fallback",
        "trust_score": FREDAdapter.trust_score,
        "default_series_count": len(DEFAULT_FRED_SERIES),
        "raw_archive_root": str(archive_root),
        "raw_archive_exists": archive_root.exists(),
        "live_boundary": "Read-only. Macro shifts provide context only until corroborated by strategy gates.",
    }


def fetch_fred_sample(
    series_ids: tuple[str, ...] = (),
    alert_on_sigma: float | None = None,
) -> dict[str, Any]:
    return FREDAdapter().fetch_sample(series_ids=series_ids, alert_on_sigma=alert_on_sigma).to_dict()


async def fetch_fred_live(
    series_ids: tuple[str, ...] = (),
    observation_start: str | None = None,
    limit: int = 45,
    alert_on_sigma: float | None = None,
) -> dict[str, Any]:
    envelope = await FREDAdapter().fetch_live(
        series_ids=series_ids,
        observation_start=observation_start,
        limit=limit,
        alert_on_sigma=alert_on_sigma,
    )
    return envelope.to_dict()


def fetch_fred_live_sync(
    series_ids: tuple[str, ...] = (),
    observation_start: str | None = None,
    limit: int = 45,
    alert_on_sigma: float | None = None,
) -> dict[str, Any]:
    return asyncio.run(fetch_fred_live(series_ids, observation_start, limit, alert_on_sigma))


DEFAULT_RSS_FEEDS: tuple[dict[str, str], ...] = (
    {"name": "BBC World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
    {"name": "BBC Middle East", "url": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml"},
    {"name": "Reuters Business", "url": "https://news.google.com/rss/search?q=site:reuters.com+business+markets+when:1d&hl=en-US&gl=US&ceid=US:en"},
    {"name": "CNBC", "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html"},
    {"name": "OilPrice.com", "url": "https://oilprice.com/rss/main"},
    {"name": "Defense News", "url": "https://www.defensenews.com/arc/outboundfeeds/rss/?outputType=xml"},
    {"name": "Semiconductors", "url": "https://news.google.com/rss/search?q=semiconductor+chips+when:1d&hl=en-US&gl=US&ceid=US:en"},
)


def _strip_html(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _child_text(element: ET.Element, names: tuple[str, ...]) -> str:
    wanted = {name.lower() for name in names}
    for child in list(element):
        if _local_name(child.tag) in wanted and child.text:
            return _strip_html(child.text)
    return ""


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class RSSAdapter:
    source_key = "rss"
    source_name = "RSS / Atom Feeds"
    source_label = "social.rss"
    trust_score = 0.78

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
        now = datetime.now(timezone.utc).isoformat()
        return {
            "feeds": [
                {
                    "name": "Qadam Sample Macro Feed",
                    "url": "https://example.com/qadam/rss/macro.xml",
                    "items": [
                        {
                            "title": "Oil prices rise as shipping risk builds near a strategic corridor",
                            "link": "https://example.com/qadam/rss/oil-shipping-risk",
                            "published": now,
                            "summary": "A sample headline for Qadam's crude oil and geopolitical monitoring layer.",
                        },
                        {
                            "title": "Chipmakers watch new export control negotiations",
                            "link": "https://example.com/qadam/rss/chip-export-controls",
                            "published": now,
                            "summary": "A sample headline for Qadam's semiconductor and US-China monitoring layer.",
                        },
                    ],
                }
            ],
            "sample": True,
        }

    @staticmethod
    def looks_like_rss_xml(text: str) -> bool:
        head = text[:2048].lower()
        if re.search(r"<!doctype\s+html|<html[\s>]", head):
            return False
        return bool(re.search(r"<rss[\s>]|<feed[\s>]|<rdf:rdf[\s>]", head))

    def _parse_xml_feed(self, xml_text: str, feed: dict[str, str]) -> dict[str, Any]:
        root = ET.fromstring(xml_text)
        entries = root.findall(".//item")
        if not entries:
            entries = [element for element in root.iter() if _local_name(element.tag) == "entry"]

        items: list[dict[str, Any]] = []
        for entry in entries:
            title = _child_text(entry, ("title",))
            link = _child_text(entry, ("link",))
            if not link:
                for child in list(entry):
                    if _local_name(child.tag) == "link":
                        link = str(child.attrib.get("href") or "")
                        break
            published = _child_text(entry, ("pubDate", "published", "updated", "dc:date"))
            summary = _child_text(entry, ("description", "summary", "content", "content:encoded"))
            if not title:
                continue
            items.append(
                {
                    "title": title,
                    "link": link,
                    "published": published,
                    "summary": summary,
                    "feed_name": feed.get("name", "RSS Feed"),
                    "feed_url": feed.get("url", ""),
                }
            )
        return {"name": feed.get("name", "RSS Feed"), "url": feed.get("url", ""), "items": items}

    def normalize_payload(
        self,
        payload: dict[str, Any],
        *,
        since_iso: str | None = None,
        keyword_filter: tuple[str, ...] = (),
    ) -> tuple[UnifiedEvent, ...]:
        since = GDELTAdapter._parse_since(since_iso) if since_iso else None
        keywords = tuple(keyword.lower() for keyword in keyword_filter if keyword.strip())
        events: list[UnifiedEvent] = []
        seen_keys: set[str] = set()

        feeds = payload.get("feeds", [])
        if not isinstance(feeds, list):
            return ()

        for feed in feeds:
            if not isinstance(feed, dict):
                continue
            for item in feed.get("items", []):
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title") or "").strip()
                if not title:
                    continue
                summary = str(item.get("summary") or "").strip()
                haystack = f"{title} {summary}".lower()
                if keywords and not any(keyword in haystack for keyword in keywords):
                    continue
                published = str(item.get("published") or "")
                parsed = _parse_datetime(published)
                if since and parsed and parsed < since:
                    continue
                dedupe_key = hashlib.sha256(f"{title}|{published}".encode("utf-8")).hexdigest()
                if dedupe_key in seen_keys:
                    continue
                seen_keys.add(dedupe_key)
                ingested_at = parsed.isoformat() if parsed else datetime.now(timezone.utc).isoformat()
                normalised_summary = title[:240]
                events.append(
                    UnifiedEvent(
                        schema_version=UNIFIED_EVENT_SCHEMA_VERSION,
                        event_id=str(uuid4()),
                        source=self.source_label,
                        trust_score_at_ingestion=self.trust_score,
                        event_type="social_signal",
                        raw_payload={
                            "title": title,
                            "link": item.get("link"),
                            "published": published,
                            "summary": summary,
                            "feed_name": item.get("feed_name") or feed.get("name"),
                            "feed_url": item.get("feed_url") or feed.get("url"),
                            "dedupe_key": dedupe_key,
                        },
                        normalised_summary=normalised_summary,
                        coordinates=None,
                        ingested_at=ingested_at,
                        linked_catalyst_id=None,
                    )
                )
        return tuple(events)

    def envelope_from_payload(
        self,
        payload: dict[str, Any],
        *,
        since_iso: str | None = None,
        keyword_filter: tuple[str, ...] = (),
        archive: bool = True,
        degraded: bool = False,
        degraded_reason: str | None = None,
    ) -> SourceEnvelope:
        archive_path = self.archive.write(self.source_key, payload) if archive else None
        events = self.normalize_payload(
            payload,
            since_iso=since_iso,
            keyword_filter=keyword_filter,
        )
        envelope = SourceEnvelope(
            events=events,
            source=self.source_label,
            trust_score=self.trust_score,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            degraded=degraded,
            degraded_reason=degraded_reason,
            raw_archive_path=str(archive_path) if archive_path else None,
        )
        self.event_log.write(
            "source_adapter_fetch_completed",
            "rss_adapter",
            {
                "source": self.source_label,
                "event_count": len(events),
                "degraded": degraded,
                "raw_archive_path": envelope.raw_archive_path,
            },
        )
        return envelope

    async def fetch_live(
        self,
        *,
        feed_urls: tuple[str, ...] = (),
        since_iso: str | None = None,
        keyword_filter: tuple[str, ...] = (),
        timeout_seconds: float = 12.0,
    ) -> SourceEnvelope:
        try:
            import httpx
        except ImportError as exc:
            raise RuntimeError("httpx is not installed. Run scripts/bootstrap_runtime.sh first.") from exc

        feeds = (
            tuple({"name": f"Custom Feed {index + 1}", "url": url} for index, url in enumerate(feed_urls))
            if feed_urls
            else DEFAULT_RSS_FEEDS
        )
        headers = {
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
            "User-Agent": "Qadam/0.1 read-only RSS adapter",
        }
        parsed_feeds: list[dict[str, Any]] = []
        failures: list[dict[str, str]] = []
        async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
            for feed in feeds:
                url = feed["url"]
                try:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    text = response.text
                    if not self.looks_like_rss_xml(text):
                        failures.append({"name": feed["name"], "url": url, "reason": "not_rss_xml"})
                        continue
                    parsed_feeds.append(self._parse_xml_feed(text, feed))
                except (httpx.HTTPError, ET.ParseError) as exc:
                    failures.append({"name": feed["name"], "url": url, "reason": exc.__class__.__name__})

        payload = {
            "feeds": parsed_feeds,
            "failures": failures,
            "_qadam_request": {
                "feed_count": len(feeds),
                "keyword_filter": list(keyword_filter),
                "since_iso": since_iso,
            },
        }
        degraded = bool(failures) and not parsed_feeds
        degraded_reason = "rss_all_feeds_failed" if degraded else ("rss_partial_feed_failures" if failures else None)
        return self.envelope_from_payload(
            payload,
            since_iso=since_iso,
            keyword_filter=keyword_filter,
            degraded=degraded,
            degraded_reason=degraded_reason,
        )

    def fetch_sample(
        self,
        *,
        since_iso: str | None = None,
        keyword_filter: tuple[str, ...] = (),
    ) -> SourceEnvelope:
        return self.envelope_from_payload(
            self.sample_payload(),
            since_iso=since_iso,
            keyword_filter=keyword_filter,
        )


def rss_adapter_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    archive_root = Path(settings.raw_payload_dir) / RSSAdapter.source_key
    return {
        "key": RSSAdapter.source_key,
        "source": RSSAdapter.source_label,
        "mode": "sample_ready_live_optional",
        "auth": "none",
        "trust_score": RSSAdapter.trust_score,
        "default_feed_count": len(DEFAULT_RSS_FEEDS),
        "raw_archive_root": str(archive_root),
        "raw_archive_exists": archive_root.exists(),
        "live_boundary": "Read-only. Headlines become narrative observations, not trade triggers.",
    }


def fetch_rss_sample(keyword_filter: tuple[str, ...] = ()) -> dict[str, Any]:
    return RSSAdapter().fetch_sample(keyword_filter=keyword_filter).to_dict()


async def fetch_rss_live(
    feed_urls: tuple[str, ...] = (),
    since_iso: str | None = None,
    keyword_filter: tuple[str, ...] = (),
) -> dict[str, Any]:
    envelope = await RSSAdapter().fetch_live(
        feed_urls=feed_urls,
        since_iso=since_iso,
        keyword_filter=keyword_filter,
    )
    return envelope.to_dict()


def fetch_rss_live_sync(
    feed_urls: tuple[str, ...] = (),
    since_iso: str | None = None,
    keyword_filter: tuple[str, ...] = (),
) -> dict[str, Any]:
    return asyncio.run(fetch_rss_live(feed_urls, since_iso, keyword_filter))
