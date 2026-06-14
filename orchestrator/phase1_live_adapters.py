"""Phase 1 read-only adapter promotion layer.

These adapters make the remaining Phase 1 sources explicit without giving them
signal confidence or execution authority. Each source has sample mode, masked
credential status, raw archive writes, normalized events, and a live path that
fails closed when credentials or provider details are missing.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from orchestrator.adapters import RawPayloadArchive, SourceEnvelope, UnifiedEvent, UNIFIED_EVENT_SCHEMA_VERSION
from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.secrets import secret_status, secret_value
from world_monitor.source_registry import get_source


@dataclass(frozen=True)
class Phase1AdapterConfig:
    key: str
    source_label: str
    event_type: str
    trust_score: float
    sample_summary: str
    primary_endpoint: str
    method: str = "GET"
    public_live: bool = False
    required_any_secret_groups: tuple[tuple[str, ...], ...] = ()
    notes: str = ""


PHASE1_LIVE_ADAPTERS: dict[str, Phase1AdapterConfig] = {
    "acled": Phase1AdapterConfig(
        key="acled",
        source_label="conflict.acled",
        event_type="conflict_event",
        trust_score=0.86,
        sample_summary="ACLED conflict event near an energy or defence-relevant region.",
        primary_endpoint="https://acleddata.com/api/acled/read",
        required_any_secret_groups=(("ACLED_ACCESS_TOKEN",), ("ACLED_EMAIL", "ACLED_PASSWORD")),
        notes=(
            "Credential-gated ACLED read path. Token preferred; email/password remains "
            "tracked for refresh-token automation. ACLED_REFRESH_TOKEN is tracked for "
            "automatic token renewal."
        ),
    ),
    "ucdp": Phase1AdapterConfig(
        key="ucdp",
        source_label="conflict.ucdp",
        event_type="conflict_base_rate",
        trust_score=0.62,
        sample_summary="UCDP historical conflict observation available for geopolitical base-rate context.",
        primary_endpoint="https://ucdpapi.pcr.uu.se/api/gedevents/23.1",
        public_live=True,
        notes="Read-only historical conflict/base-rate context. It cannot create signal confidence by itself.",
    ),
    "conflict_tracker": Phase1AdapterConfig(
        key="conflict_tracker",
        source_label="conflict.tracker",
        event_type="derived_conflict_context",
        trust_score=0.72,
        sample_summary="Derived conflict tracker fuses ACLED/GDELT context for corridor and escalation review.",
        primary_endpoint="internal://conflict_tracker",
        public_live=True,
        notes="Internal read-only derived context. It cannot create orders or bypass source quorum.",
    ),
    "stock_act": Phase1AdapterConfig(
        key="stock_act",
        source_label="social.stock_act",
        event_type="politician_trade_disclosure",
        trust_score=0.72,
        sample_summary="STOCK Act congressional trade disclosure requiring cross-check against price action and filings.",
        primary_endpoint="https://www.capitoltrades.com/trades",
        required_any_secret_groups=(("CAPITOL_TRADES_API_KEY",),),
        notes=(
            "Provider direction updated: Capitol Trades or its selected API path is the v1 STOCK Act source. "
            "Output is read-only evidence, not trade authority."
        ),
    ),
    "polymarket": Phase1AdapterConfig(
        key="polymarket",
        source_label="market.polymarket",
        event_type="prediction_market",
        trust_score=0.74,
        sample_summary="Polymarket public market quote available for a geopolitical or macro question.",
        primary_endpoint="https://clob.polymarket.com/markets",
        public_live=True,
    ),
    "kalshi": Phase1AdapterConfig(
        key="kalshi",
        source_label="market.kalshi",
        event_type="prediction_market",
        trust_score=0.76,
        sample_summary="Kalshi market metadata available for a macro, election, rates, or geopolitical contract.",
        primary_endpoint="https://trading-api.kalshi.com/trade-api/v2/markets",
        required_any_secret_groups=(("KALSHI_API_KEY", "KALSHI_API_SECRET"),),
        notes="Kalshi is region/account gated for Ramin; authenticated paths stay read-only when available.",
    ),
    "hyperliquid": Phase1AdapterConfig(
        key="hyperliquid",
        source_label="market.hyperliquid",
        event_type="crypto_derivatives_context",
        trust_score=0.48,
        sample_summary="Hyperliquid public perps context available for crypto/liquidity regime monitoring.",
        primary_endpoint="https://api.hyperliquid.xyz/info",
        method="POST",
        public_live=True,
        notes="Read-only public crypto/perps context. Qadam cannot write orders through this adapter.",
    ),
    "alpaca": Phase1AdapterConfig(
        key="alpaca",
        source_label="market.alpaca",
        event_type="broker_account_snapshot",
        trust_score=0.82,
        sample_summary="Alpaca paper account and market-data read-only mirror candidate.",
        primary_endpoint="https://paper-api.alpaca.markets/v2/account",
        required_any_secret_groups=(("ALPACA_API_KEY", "ALPACA_API_SECRET"),),
        notes="Read-only mirror target only. No order endpoint is implemented here.",
    ),
    "bookmap": Phase1AdapterConfig(
        key="bookmap",
        source_label="market.bookmap",
        event_type="local_orderflow_context",
        trust_score=0.52,
        sample_summary="Bookmap local order-flow bridge contract available when the local bridge is configured and running.",
        primary_endpoint="ws://localhost:8765/bookmap",
        public_live=True,
        required_any_secret_groups=(("BOOKMAP_BRIDGE_URL",),),
        notes="Local bridge only. It remains disconnected until BOOKMAP_BRIDGE_URL points at a running read-only bridge.",
    ),
    "ais_maritime": Phase1AdapterConfig(
        key="ais_maritime",
        source_label="physical.ais_maritime",
        event_type="logistics_signal",
        trust_score=0.79,
        sample_summary="AIS vessel-density or route-change observation near an energy chokepoint.",
        primary_endpoint="https://stream.aisstream.io/v0/stream",
        required_any_secret_groups=(("AISSTREAM_API_KEY",), ("SPIRE_API_KEY",), ("MARINETRAFFIC_API_KEY",)),
        notes="AISStream is the v1 read-only MVP path; Spire and MarineTraffic remain paid fallback candidates.",
    ),
    "arcgis_usace": Phase1AdapterConfig(
        key="arcgis_usace",
        source_label="physical.arcgis_usace",
        event_type="infrastructure_context",
        trust_score=0.58,
        sample_summary="Public ArcGIS/USACE infrastructure layer available for ports, waterways, and physical-risk context.",
        primary_endpoint="https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/",
        public_live=True,
        notes="Public geospatial context only. Qadam treats it as background evidence.",
    ),
    "space_track_celestrak": Phase1AdapterConfig(
        key="space_track_celestrak",
        source_label="physical.space_track_celestrak",
        event_type="space_infrastructure_state",
        trust_score=0.66,
        sample_summary="CelesTrak public GP/TLE observation for satellite infrastructure context.",
        primary_endpoint="https://celestrak.org/NORAD/elements/gp.php",
        public_live=True,
        required_any_secret_groups=(("SPACE_TRACK_USERNAME", "SPACE_TRACK_PASSWORD"),),
        notes="CelesTrak public GP JSON is the fallback/smoke path; Space-Track credentials remain the fuller authenticated path.",
    ),
    "gps_jamming": Phase1AdapterConfig(
        key="gps_jamming",
        source_label="physical.gps_jamming",
        event_type="navigation_disruption",
        trust_score=0.57,
        sample_summary="GPS interference observation available for navigation and electronic-warfare context.",
        primary_endpoint="https://gpsjam.org/api",
        public_live=True,
        notes="Public navigation-disruption context only.",
    ),
    "internet_outage": Phase1AdapterConfig(
        key="internet_outage",
        source_label="physical.internet_outage",
        event_type="infrastructure_disruption",
        trust_score=0.58,
        sample_summary="IODA internet-outage observation available for infrastructure and political-risk context.",
        primary_endpoint="https://ioda.inetintel.cc.gatech.edu/api",
        public_live=True,
        notes="Public internet-outage context only.",
    ),
    "aviationstack": Phase1AdapterConfig(
        key="aviationstack",
        source_label="physical.aviationstack",
        event_type="logistics_signal",
        trust_score=0.73,
        sample_summary="ADS-B flight activity anomaly near a conflict, defence, or supply-chain region.",
        primary_endpoint="https://api.aviationstack.com/v1/flights",
        required_any_secret_groups=(("AVIATIONSTACK_API_KEY",),),
        notes="Aviationstack replaces Wingbits as Qadam's v1 flight-data provider.",
    ),
    "bls": Phase1AdapterConfig(
        key="bls",
        source_label="macro.bls",
        event_type="macro_release",
        trust_score=0.88,
        sample_summary="BLS labor/inflation time series release available for macro regime context.",
        primary_endpoint="https://api.bls.gov/publicAPI/v2/timeseries/data/",
        method="POST",
        public_live=True,
        required_any_secret_groups=(("BLS_API_KEY",),),
        notes="Public mode may work without a key at lower limits; key remains recommended.",
    ),
    "bis": Phase1AdapterConfig(
        key="bis",
        source_label="macro.bis",
        event_type="macro_release",
        trust_score=0.78,
        sample_summary="BIS statistics observation available for global liquidity, banking, and credit-cycle context.",
        primary_endpoint="https://stats.bis.org/api/v1/data/",
        public_live=True,
        notes="Public macro/liquidity context only.",
    ),
    "ecb": Phase1AdapterConfig(
        key="ecb",
        source_label="macro.ecb",
        event_type="macro_release",
        trust_score=0.86,
        sample_summary="ECB series observation available for liquidity, rates, or EUR macro context.",
        primary_endpoint="https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A",
        public_live=True,
    ),
    "usgs": Phase1AdapterConfig(
        key="usgs",
        source_label="macro.usgs",
        event_type="physical_supply_risk",
        trust_score=0.74,
        sample_summary="USGS mineral/supply-chain or geophysical observation relevant to commodities and defence.",
        primary_endpoint="https://earthquake.usgs.gov/fdsnws/event/1/query",
        public_live=True,
        notes=(
            "Scope decision: minerals/supply-chain context is the strategic role; the public earthquake API is the "
            "event-driven physical-risk adapter path."
        ),
    ),
    "un_comtrade": Phase1AdapterConfig(
        key="un_comtrade",
        source_label="macro.un_comtrade",
        event_type="trade_flow",
        trust_score=0.81,
        sample_summary="UN Comtrade flow observation for commodity, defence, or semiconductor trade corridors.",
        primary_endpoint="https://comtradeapi.un.org/data/v1/get/",
        required_any_secret_groups=(("COMTRADE_API_KEY",),),
    ),
    "sec_edgar": Phase1AdapterConfig(
        key="sec_edgar",
        source_label="social.sec_edgar",
        event_type="filing_event",
        trust_score=0.84,
        sample_summary="SEC EDGAR filing or company update relevant to Qadam watchlists.",
        primary_endpoint="https://data.sec.gov/submissions/CIK0000320193.json",
        public_live=True,
        required_any_secret_groups=(("SEC_USER_AGENT",),),
        notes="SEC requires a useful User-Agent. Default placeholder is treated as missing.",
    ),
    "patents": Phase1AdapterConfig(
        key="patents",
        source_label="social.patents",
        event_type="patent_context",
        trust_score=0.5,
        sample_summary="Patent filing observation available for defence, semiconductor, and industrial-technology context.",
        primary_endpoint="https://api.patentsview.org/patents/query",
        public_live=True,
        notes="Public patent context only; no strategy or execution authority.",
    ),
    "reddit": Phase1AdapterConfig(
        key="reddit",
        source_label="social.reddit",
        event_type="narrative_signal",
        trust_score=0.46,
        sample_summary="Reddit narrative observation requiring corroboration before any research weight.",
        primary_endpoint="https://oauth.reddit.com/r/worldnews/new",
        required_any_secret_groups=(("REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET"),),
    ),
    "twitter_x": Phase1AdapterConfig(
        key="twitter_x",
        source_label="social.twitter_x",
        event_type="narrative_signal",
        trust_score=0.52,
        sample_summary="X/Twitter narrative observation requiring independent corroboration.",
        primary_endpoint="https://api.twitter.com/2/tweets/search/recent",
        required_any_secret_groups=(("X_BEARER_TOKEN",),),
    ),
    "telegram": Phase1AdapterConfig(
        key="telegram",
        source_label="social.telegram",
        event_type="narrative_signal",
        trust_score=0.55,
        sample_summary="Telegram channel or bot update captured as narrative context only.",
        primary_endpoint="https://api.telegram.org/bot{TOKEN}/getUpdates",
        required_any_secret_groups=(("TELEGRAM_BOT_TOKEN",), ("TELEGRAM_API_ID", "TELEGRAM_API_HASH", "TELEGRAM_SESSION")),
        notes="Bot API and MTProto are separate future paths. Neither can trigger execution.",
    ),
}

PHASE1_LIVE_ADAPTER_KEYS: tuple[str, ...] = tuple(PHASE1_LIVE_ADAPTERS)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _secret_groups_status(config: Phase1AdapterConfig, settings: Settings) -> dict[str, Any]:
    groups: list[dict[str, Any]] = []
    for group in config.required_any_secret_groups:
        statuses = [secret_status(key, settings) for key in group]
        groups.append(
            {
                "keys": list(group),
                "configured": all(status.configured for status in statuses),
                "sources": [status.source for status in statuses],
            }
        )
    any_configured = not groups or any(group["configured"] for group in groups)
    missing_groups = [group["keys"] for group in groups if not group["configured"]]
    return {
        "credential_configured": any_configured,
        "configured_secret_group_count": sum(1 for group in groups if group["configured"]),
        "required_group_count": len(groups),
        "missing_secret_groups": missing_groups,
    }


def _safe_endpoint(endpoint: str) -> str:
    parsed = urlparse(endpoint)
    if parsed.scheme and parsed.netloc:
        path = parsed.path
        if parsed.netloc == "api.telegram.org" and path.startswith("/bot"):
            parts = path.split("/", 2)
            path = "/bot<redacted>"
            if len(parts) > 2 and parts[2]:
                path = f"{path}/{parts[2]}"
        return f"{parsed.scheme}://{parsed.netloc}{path}"
    return endpoint


def _event_summary(config: Phase1AdapterConfig, record: dict[str, Any]) -> str:
    properties = record.get("properties")
    if isinstance(properties, dict):
        for key in ("title", "place", "name", "event", "summary"):
            value = properties.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()[:240]
    for key in (
        "title",
        "name",
        "question",
        "headline",
        "summary",
        "event",
        "text",
        "ticker",
        "seriesID",
        "OBJECT_NAME",
        "NORAD_CAT_ID",
        "REPRESENTATIVE",
        "ISSUER",
        "REPORT_DATE",
        "flight_status",
        "callsign",
        "airport_name",
        "series",
        "dataset",
        "contract",
        "patent_title",
    ):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:240]
        if isinstance(value, (int, float)):
            return f"{key} {value}"[:240]
    return config.sample_summary[:240]


def _records_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [record for record in payload if isinstance(record, dict)]
    if not isinstance(payload, dict):
        return []
    for key in (
        "data",
        "events",
        "markets",
        "results",
        "Result",
        "articles",
        "observations",
        "series",
        "feed",
        "alerts",
        "features",
        "patents",
    ):
        value = payload.get(key)
        if isinstance(value, list):
            return [record for record in value if isinstance(record, dict)]
    return [payload]


class Phase1ReadOnlyAdapter:
    def __init__(
        self,
        source_key: str,
        *,
        settings: Settings | None = None,
        archive: RawPayloadArchive | None = None,
        event_log: EventLog | None = None,
    ) -> None:
        if source_key not in PHASE1_LIVE_ADAPTERS:
            raise KeyError(f"unknown Phase 1 adapter: {source_key}")
        self.config = PHASE1_LIVE_ADAPTERS[source_key]
        self.source = get_source(source_key)
        self.settings = settings or Settings.from_env()
        self.archive = archive or RawPayloadArchive(self.settings)
        self.event_log = event_log or EventLog(echo=False)

    def sample_payload(self) -> dict[str, Any]:
        return {
            "sample": True,
            "source_key": self.config.key,
            "source_name": self.source.name,
            "pipeline": self.source.pipeline,
            "tier": self.source.tier,
            "records": [
                {
                    "id": f"sample-{self.config.key}-1",
                    "title": self.config.sample_summary,
                    "observed_at": _now(),
                    "endpoint": _safe_endpoint(self.config.primary_endpoint),
                    "auth": self.source.auth,
                    "cadence": self.source.cadence,
                }
            ],
        }

    def normalize_payload(self, payload: dict[str, Any]) -> tuple[UnifiedEvent, ...]:
        records = _records_from_payload(payload.get("records") if payload.get("sample") else payload)
        events: list[UnifiedEvent] = []
        for record in records[:25]:
            summary = _event_summary(self.config, record)
            observed_at = str(record.get("observed_at") or record.get("date") or record.get("timestamp") or _now())
            events.append(
                UnifiedEvent(
                    schema_version=UNIFIED_EVENT_SCHEMA_VERSION,
                    event_id=str(uuid4()),
                    source=self.config.source_label,
                    trust_score_at_ingestion=self.config.trust_score,
                    event_type=self.config.event_type,
                    raw_payload={
                        "source_key": self.config.key,
                        "record_id": record.get("id") or record.get("event_id") or record.get("ticker"),
                        "title": record.get("title") or record.get("name") or record.get("question"),
                        "endpoint": _safe_endpoint(self.config.primary_endpoint),
                        "sample": bool(payload.get("sample")),
                    },
                    normalised_summary=summary,
                    coordinates=None,
                    ingested_at=observed_at,
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
        archive_path = self.archive.write(self.config.key, payload)
        events = self.normalize_payload(payload)
        envelope = SourceEnvelope(
            events=events,
            source=self.config.source_label,
            trust_score=self.config.trust_score,
            fetched_at=_now(),
            degraded=degraded,
            degraded_reason=degraded_reason,
            raw_archive_path=str(archive_path),
        )
        self.event_log.write(
            "source_adapter_fetch_completed",
            "phase1_live_adapter",
            {
                "source": self.config.source_label,
                "source_key": self.config.key,
                "event_count": len(events),
                "degraded": degraded,
                "degraded_reason": degraded_reason,
                "raw_archive_path": envelope.raw_archive_path,
                "execution_allowed": False,
            },
        )
        return envelope

    def fetch_sample(self) -> SourceEnvelope:
        return self.envelope_from_payload(self.sample_payload())

    def _request_headers(self) -> dict[str, str]:
        key = self.config.key
        headers = {"User-Agent": "Qadam/0.1 read-only source adapter"}
        if key == "stock_act":
            token = secret_value("CAPITOL_TRADES_API_KEY", self.settings)
            if token:
                headers["Authorization"] = f"Bearer {token}"
        elif key == "alpaca":
            api_key = secret_value("ALPACA_API_KEY", self.settings)
            api_secret = secret_value("ALPACA_API_SECRET", self.settings)
            if api_key and api_secret:
                headers["APCA-API-KEY-ID"] = api_key
                headers["APCA-API-SECRET-KEY"] = api_secret
        elif key == "acled":
            token = secret_value("ACLED_ACCESS_TOKEN", self.settings)
            if token:
                headers["Authorization"] = f"Bearer {token}"
                headers["Content-Type"] = "application/json"
        elif key == "twitter_x":
            token = secret_value("X_BEARER_TOKEN", self.settings)
            if token:
                headers["Authorization"] = f"Bearer {token}"
        elif key == "sec_edgar":
            user_agent = secret_value("SEC_USER_AGENT", self.settings)
            if user_agent and "contact@example.com" not in user_agent:
                headers["User-Agent"] = user_agent
        elif key == "telegram":
            token = secret_value("TELEGRAM_BOT_TOKEN", self.settings)
            if token:
                # Telegram token belongs in the URL. We never archive it.
                headers["X-Qadam-Auth-Mode"] = "telegram_bot_token_configured"
        return headers

    def _request_params(self) -> dict[str, Any]:
        key = self.config.key
        if key == "ucdp":
            return {"pagesize": 25}
        if key == "acled":
            return {"limit": 25, "_format": "json"}
        if key == "polymarket":
            return {"limit": 25}
        if key == "kalshi":
            return {"limit": 25}
        if key in {"unusual_whales", "stock_act"}:
            return {"limit": 25}
        if key == "space_track_celestrak":
            return {"GROUP": "stations", "FORMAT": "json"}
        if key == "arcgis_usace":
            return {"f": "json"}
        if key == "gps_jamming":
            return {}
        if key == "internet_outage":
            return {}
        if key == "usgs":
            return {"format": "geojson", "orderby": "time", "minmagnitude": 4.5, "limit": 25}
        if key == "aviationstack":
            api_key = secret_value("AVIATIONSTACK_API_KEY", self.settings)
            return {"access_key": api_key or "", "limit": 25}
        if key == "bls":
            return {}
        if key == "ecb":
            return {"lastNObservations": 25, "format": "jsondata"}
        if key == "bis":
            return {}
        if key == "un_comtrade":
            return {"max": 25}
        if key == "sec_edgar":
            return {}
        if key == "patents":
            return {"q": json.dumps({"_gte": {"patent_date": "2025-01-01"}}), "f": json.dumps(["patent_id", "patent_title", "patent_date"])}
        if key == "twitter_x":
            return {"query": "oil OR semiconductors OR defense", "max_results": 10}
        return {}

    def _request_body(self) -> dict[str, Any] | None:
        if self.config.key == "bls":
            body: dict[str, Any] = {
                "seriesid": ["CUSR0000SA0", "CES0000000001"],
                "latest": "true",
            }
            api_key = secret_value("BLS_API_KEY", self.settings)
            if api_key:
                body["registrationkey"] = api_key
            return body
        if self.config.key == "hyperliquid":
            return {"type": "metaAndAssetCtxs"}
        return None

    def _live_url(self) -> str:
        if self.config.key == "telegram":
            token = secret_value("TELEGRAM_BOT_TOKEN", self.settings)
            if token:
                return f"https://api.telegram.org/bot{token}/getUpdates"
        if self.config.key == "bookmap":
            return secret_value("BOOKMAP_BRIDGE_URL", self.settings) or self.config.primary_endpoint
        return self.config.primary_endpoint

    async def fetch_live(self, *, timeout_seconds: float = 12.0) -> SourceEnvelope:
        credential_state = _secret_groups_status(self.config, self.settings)
        if not credential_state["credential_configured"] and not self.config.public_live:
            return self.envelope_from_payload(
                {
                    "records": [],
                    "_qadam_request": {
                        "url": _safe_endpoint(self.config.primary_endpoint),
                        "method": self.config.method,
                    },
                    "_qadam_credential_status": "missing_required_credentials",
                    "_qadam_missing_secret_groups": credential_state["missing_secret_groups"],
                },
                degraded=True,
                degraded_reason="missing_credentials",
            )

        if self.config.key == "conflict_tracker":
            return self.envelope_from_payload(
                {
                    "records": [
                        {
                            "id": "derived-conflict-tracker-status",
                            "title": self.config.sample_summary,
                            "observed_at": _now(),
                            "derived": True,
                            "inputs": ["acled", "gdelt"],
                        }
                    ],
                    "_qadam_request": {
                        "url": _safe_endpoint(self.config.primary_endpoint),
                        "method": "DERIVED",
                        "credential_configured": True,
                    },
                }
            )
        if self.config.key == "bookmap" and self._live_url().startswith("ws://"):
            return self.envelope_from_payload(
                {
                    "records": [],
                    "_qadam_request": {
                        "url": _safe_endpoint(self._live_url()),
                        "method": "WEBSOCKET_LOCAL_BRIDGE",
                        "credential_configured": credential_state["credential_configured"],
                    },
                    "_qadam_error_type": "local_bridge_probe_required",
                    "_qadam_error": "Bookmap uses a local WebSocket bridge; run a dedicated bridge probe before marking it connected.",
                },
                degraded=True,
                degraded_reason="local_bridge_probe_required",
            )

        try:
            import httpx
        except ImportError:
            return self.envelope_from_payload(
                {
                    "records": [],
                    "_qadam_request": {
                        "url": _safe_endpoint(self._live_url()),
                        "method": self.config.method,
                    },
                    "_qadam_error_type": "missing_dependency",
                    "_qadam_error": "httpx is not installed in this Python environment.",
                },
                degraded=True,
                degraded_reason="missing_dependency:httpx",
            )

        url = self._live_url()
        headers = self._request_headers()
        params = self._request_params()
        body = self._request_body()
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
                if self.config.method == "POST":
                    response = await client.post(url, headers=headers, json=body or params)
                else:
                    response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                text = response.text
                content_type = response.headers.get("content-type", "")
                payload = response.json() if "json" in content_type.lower() or text.strip().startswith(("{", "[")) else {"records": [], "body_preview": text[:500]}
        except (httpx.HTTPError, ValueError) as exc:
            return self.envelope_from_payload(
                {
                    "records": [],
                    "_qadam_request": {
                        "url": _safe_endpoint(url),
                        "method": self.config.method,
                        "params": {
                            key: (
                                "configured"
                                if key
                                in {
                                    "access_key",
                                    "access_token",
                                    "apikey",
                                    "api_key",
                                    "email",
                                    "password",
                                    "registrationkey",
                                }
                                else value
                            )
                            for key, value in params.items()
                        },
                    },
                    "_qadam_error_type": exc.__class__.__name__,
                    "_qadam_error": repr(exc),
                },
                degraded=True,
                degraded_reason=f"live_fetch_error:{exc.__class__.__name__}",
            )

        if isinstance(payload, dict):
            payload["_qadam_request"] = {
                "url": _safe_endpoint(url),
                "method": self.config.method,
                "credential_configured": credential_state["credential_configured"],
            }
        return self.envelope_from_payload(payload if isinstance(payload, dict) else {"records": payload})


def phase1_live_adapter_status(source_key: str, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    config = PHASE1_LIVE_ADAPTERS[source_key]
    credential_state = _secret_groups_status(config, settings)
    archive_root = Path(settings.raw_payload_dir) / config.key
    return {
        "key": config.key,
        "source": config.source_label,
        "mode": "sample_ready_live_optional" if config.public_live else "sample_ready_credential_gated",
        "auth": get_source(source_key).auth,
        "credential_configured": credential_state["credential_configured"],
        "configured_secret_group_count": credential_state["configured_secret_group_count"],
        "required_group_count": credential_state["required_group_count"],
        "trust_score": config.trust_score,
        "raw_archive_root": str(archive_root),
        "raw_archive_exists": archive_root.exists(),
        "live_boundary": "Read-only. Adapter output cannot change signal confidence or create orders by itself.",
        "notes": config.notes,
    }


def phase1_live_adapter_registry(settings: Settings | None = None) -> dict[str, Any]:
    statuses = [phase1_live_adapter_status(key, settings) for key in PHASE1_LIVE_ADAPTER_KEYS]
    return {
        "status": "ok",
        "adapter_count": len(statuses),
        "configured_count": sum(1 for status in statuses if status["credential_configured"]),
        "public_or_optional_count": sum(1 for key in PHASE1_LIVE_ADAPTER_KEYS if PHASE1_LIVE_ADAPTERS[key].public_live),
        "adapters": statuses,
        "boundary": "Phase 1 promoted adapters are read-only and cannot authorize signal confidence or execution.",
    }


def fetch_phase1_live_adapter_sample(source_key: str) -> dict[str, Any]:
    return Phase1ReadOnlyAdapter(source_key).fetch_sample().to_dict()


async def fetch_phase1_live_adapter_live(source_key: str) -> dict[str, Any]:
    return (await Phase1ReadOnlyAdapter(source_key).fetch_live()).to_dict()


def fetch_phase1_live_adapter_live_sync(source_key: str) -> dict[str, Any]:
    return asyncio.run(fetch_phase1_live_adapter_live(source_key))
