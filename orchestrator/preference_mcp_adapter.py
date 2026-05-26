"""Offline Preference/PREF MCP sample adapter.

PREF-3 makes Preference look like a normal Qadam adapter without any live MCP
access. The adapter only emits deterministic sample records, archives the raw
sample payload locally, and writes a no-authority Event Log entry.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.adapters import (
    RawPayloadArchive,
    SourceEnvelope,
    UNIFIED_EVENT_SCHEMA_VERSION,
    UnifiedEvent,
)
from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.preference_mcp_catalog import (
    build_preference_tool_catalog,
    validate_preference_tool_catalog,
)
from orchestrator.preference_mcp_identity import (
    PREFERENCE_CLASSIFICATION,
    PREFERENCE_DISCOVERY_TOOL_NAME,
    PREFERENCE_PROVIDER_LABEL,
    PREFERENCE_SOURCE_KEY,
    PREFERENCE_STATUS_TOOL_NAME,
    SECRET_LIKE_PATTERNS,
    build_preference_mcp_identity_status,
    validate_preference_mcp_identity_status,
)
from orchestrator.preference_mcp_provenance import build_preference_provenance_block
from orchestrator.secrets import secret_status, secret_value
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT

PREFERENCE_MCP_ADAPTER_SCHEMA_VERSION = 1
PREFERENCE_MCP_ADAPTER_STAGE = "PREF-3"
PREFERENCE_MCP_LIVE_SMOKE_SCHEMA_VERSION = 1
PREFERENCE_MCP_LIVE_SMOKE_STAGE = "PREF-4"
PREFERENCE_MCP_LIVE_SMOKE_ARTIFACT_TYPE = "preference_mcp_live_smoke_gate"
PREFERENCE_MCP_LIVE_SMOKE_ARTIFACT_ID = "preference:pref-4:live-smoke-gate"
PREFERENCE_MCP_LIVE_SMOKE_EVENT_TYPE = "preference_mcp_live_smoke_checked"
PREFERENCE_MCP_LIVE_SMOKE_EVENT_COMPONENT = "preference_mcp_live_smoke"
PREFERENCE_MCP_ADAPTER_SOURCE_LABEL = "supplemental.preference_mcp"
PREFERENCE_MCP_ADAPTER_COMPONENT = "preference_mcp_adapter"
PREFERENCE_MCP_SAMPLE_TRUST_SCORE = 0.5
PREFERENCE_MCP_ADAPTER_CLASSIFICATION = (
    "supplemental_offline_sample_pending_identity_catalog_provenance"
)
PREFERENCE_MCP_ADAPTER_BOUNDARY = (
    "Preference/PREF MCP PREF-3 is offline sample-only. It cannot call the MCP, "
    "call search_tools, call domain tools, consume paid tools, satisfy source "
    "quorum, create trade candidates, approve risk, stage or submit paper "
    "orders, write to brokers, call quantum providers, submit hardware jobs, "
    "enable schedulers, provide fills, receipts, reconciliation truth, or "
    "enable live capital."
)
PREFERENCE_MCP_LIVE_SMOKE_BOUNDARY = (
    "Preference/PREF MCP PREF-4 is live status/catalog smoke only. It can call "
    "preference_account_status and, after a verified non-anonymous identity, "
    "search_tools. It cannot call Preference domain tools, request domain data, "
    "consume paid tools, satisfy source quorum, create observations for strategy "
    "use, create trade candidates, approve risk, stage or submit paper orders, "
    "write to brokers, call quantum providers, submit hardware jobs, enable "
    "schedulers, provide fills, receipts, reconciliation truth, or enable live "
    "capital."
)
PREFERENCE_MCP_LIVE_CATALOG_QUERY = (
    "Qadam read-only candidate tools across Polymarket Kalshi vessel tracking "
    "NOAA weather SEC filings smart wallets provenance"
)

DEFAULT_PREFERENCE_SAMPLE_RECORDS: tuple[dict[str, Any], ...] = (
    {
        "record_id": "pref-sample-polymarket-orderbook-depth",
        "domain_pack": "prediction_markets",
        "upstream_source": "polymarket",
        "signal_class": "orderbook_depth",
        "event_type": "prediction_market_orderbook_context",
        "title": "Polymarket oil chokepoint risk orderbook depth sample",
        "summary": (
            "Sample Polymarket event market shows 62 percent implied probability, "
            "0.18 bid-ask spread, and 42000 USD simulated top-five depth."
        ),
        "subject": "Strait of Hormuz disruption market",
        "metric": "implied_probability",
        "value": 0.62,
        "unit": "probability",
        "secondary_metric": "top_five_depth_usd",
        "secondary_value": 42000,
        "observed_at": "2026-05-24T00:00:00+00:00",
        "source_url": "https://polymarket.com/",
        "provenance_path": ("preference_mcp_sample", "polymarket", "orderbook_depth"),
    },
    {
        "record_id": "pref-sample-kalshi-market-summary",
        "domain_pack": "prediction_markets",
        "upstream_source": "kalshi",
        "signal_class": "event_probability",
        "event_type": "prediction_market_summary_context",
        "title": "Kalshi macro event market summary sample",
        "summary": (
            "Sample Kalshi contract metadata shows 54 percent implied probability "
            "and active yes/no quote depth for a macro policy event."
        ),
        "subject": "Macro policy event contract",
        "metric": "implied_probability",
        "value": 0.54,
        "unit": "probability",
        "secondary_metric": "open_interest_contracts",
        "secondary_value": 18500,
        "observed_at": "2026-05-24T00:00:00+00:00",
        "source_url": "https://kalshi.com/",
        "provenance_path": ("preference_mcp_sample", "kalshi", "market_summary"),
    },
    {
        "record_id": "pref-sample-hormuz-vessel-movement",
        "domain_pack": "physical_movement",
        "upstream_source": "vessel_tracking",
        "signal_class": "vessel_position",
        "event_type": "physical_movement_context",
        "title": "Vessel movement near Strait of Hormuz sample",
        "summary": (
            "Sample vessel feed shows tanker density 17 percent below baseline "
            "near a chokepoint corridor with provenance preserved."
        ),
        "subject": "Strait of Hormuz tanker flow",
        "metric": "density_delta_vs_baseline",
        "value": -0.17,
        "unit": "ratio",
        "secondary_metric": "sample_vessels_observed",
        "secondary_value": 38,
        "observed_at": "2026-05-24T00:00:00+00:00",
        "source_url": "https://pref.trade/",
        "coordinates": {"lat": 26.566, "lon": 56.25},
        "provenance_path": ("preference_mcp_sample", "vessel_tracking", "chokepoint"),
    },
    {
        "record_id": "pref-sample-noaa-weather-event",
        "domain_pack": "macro_commodities",
        "upstream_source": "noaa",
        "signal_class": "weather_event",
        "event_type": "weather_commodity_context",
        "title": "NOAA weather event commodity context sample",
        "summary": (
            "Sample NOAA-style weather context flags elevated Gulf storm risk "
            "for energy logistics monitoring."
        ),
        "subject": "Gulf energy logistics weather watch",
        "metric": "storm_risk_index",
        "value": 0.71,
        "unit": "index",
        "secondary_metric": "forecast_window_hours",
        "secondary_value": 72,
        "observed_at": "2026-05-24T00:00:00+00:00",
        "source_url": "https://www.noaa.gov/",
        "coordinates": {"lat": 27.5, "lon": -90.0},
        "provenance_path": ("preference_mcp_sample", "noaa", "weather_event"),
    },
    {
        "record_id": "pref-sample-sec-filing-metadata",
        "domain_pack": "filings_corporate",
        "upstream_source": "sec_edgar",
        "signal_class": "regulatory_filing",
        "event_type": "filing_metadata_context",
        "title": "SEC filing metadata sample",
        "summary": (
            "Sample SEC metadata identifies an 8-K filing reference for a "
            "semiconductor watchlist company with accession metadata preserved."
        ),
        "subject": "Semiconductor watchlist disclosure",
        "metric": "filing_materiality_watch",
        "value": 1,
        "unit": "binary",
        "secondary_metric": "document_count",
        "secondary_value": 3,
        "observed_at": "2026-05-24T00:00:00+00:00",
        "source_url": "https://www.sec.gov/edgar",
        "provenance_path": ("preference_mcp_sample", "sec_edgar", "filing_metadata"),
    },
    {
        "record_id": "pref-sample-smart-wallet-movement",
        "domain_pack": "crypto_wallets",
        "upstream_source": "kol_wallets",
        "signal_class": "wallet_flow",
        "event_type": "crypto_wallet_flow_context",
        "title": "Top wallet movement sample",
        "summary": (
            "Sample smart-wallet context shows net stablecoin inflow from a "
            "watchlist cohort over the last four hours."
        ),
        "subject": "Top wallet cohort flow",
        "metric": "net_stablecoin_flow_usd",
        "value": 1250000,
        "unit": "usd",
        "secondary_metric": "wallet_count",
        "secondary_value": 12,
        "observed_at": "2026-05-24T00:00:00+00:00",
        "source_url": "https://pref.trade/",
        "provenance_path": ("preference_mcp_sample", "kol_wallets", "wallet_flow"),
    },
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _blank_authority_flags() -> dict[str, bool]:
    return {
        "live_mcp_call_allowed": False,
        "search_tools_allowed": False,
        "domain_tool_calls_allowed": False,
        "paid_tool_calls_allowed": False,
        "source_quorum_credit_allowed": False,
        "trade_candidate_creation_allowed": False,
        "risk_approval_authority": False,
        "execution_authority": False,
        "paper_order_authority": False,
        "broker_write_authority": False,
        "fill_confirmation_authority": False,
        "receipt_evidence_authority": False,
        "reconciliation_truth_authority": False,
        "quantum_provider_call_allowed": False,
        "hardware_submission_allowed": False,
        "scheduler_enabled": False,
        "live_capital_authority": False,
    }


def _contains_secret_like_value(payload: Any) -> bool:
    encoded = json.dumps(payload, sort_keys=True, default=str)
    return any(pattern.search(encoded) for pattern in SECRET_LIKE_PATTERNS)


def _jsonrpc_tool_call(
    *,
    settings: Settings,
    api_key: str,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    request_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments,
        },
    }
    encoded = json.dumps(request_payload).encode("utf-8")
    request = urllib.request.Request(
        settings.preference_mcp_endpoint,
        data=encoded,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=settings.preference_mcp_timeout_seconds) as response:
        decoded = json.loads(response.read().decode("utf-8"))
    if not isinstance(decoded, dict):
        raise ValueError("preference_mcp_jsonrpc_response_not_object")
    return decoded


def _live_tool_call(
    *,
    settings: Settings,
    api_key: str,
    tool_name: str,
    arguments: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return _jsonrpc_tool_call(
            settings=settings,
            api_key=api_key,
            tool_name=tool_name,
            arguments=arguments,
        ), None
    except urllib.error.HTTPError as exc:
        return None, f"http_error:{exc.code}"
    except urllib.error.URLError as exc:
        return None, f"url_error:{exc.reason.__class__.__name__}"
    except TimeoutError:
        return None, "timeout"
    except Exception as exc:  # noqa: BLE001 - live smoke should degrade explicitly
        return None, f"live_tool_call_error:{exc.__class__.__name__}"


def _walk_values(payload: Any) -> list[Any]:
    values: list[Any] = []
    if isinstance(payload, dict):
        for value in payload.values():
            values.append(value)
            values.extend(_walk_values(value))
    elif isinstance(payload, list):
        for item in payload:
            values.append(item)
            values.extend(_walk_values(item))
    return values


def _count_tool_like_items(payload: dict[str, Any]) -> int:
    count = 0
    for value in _walk_values(payload):
        if isinstance(value, dict) and (
            "tool_ref" in value or "input_schema" in value or "call_tool" in value
        ):
            count += 1
    return count


def _sanitized_catalog_response_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "jsonrpc_error_present": "error" in payload,
        "result_present": "result" in payload,
        "tool_like_item_count": _count_tool_like_items(payload),
        "top_level_keys": sorted(str(key) for key in payload.keys()),
    }


def _live_preflight_reasons(settings: Settings, *, mode: str) -> list[str]:
    credential = secret_status("PREFERENCE_API_KEY", settings)
    reasons: list[str] = []
    if not settings.preference_mcp_enabled:
        reasons.append("preference_mcp_disabled")
    if not credential.configured:
        reasons.append("preference_api_key_missing")
    if settings.preference_mcp_transport != "streamable-http":
        reasons.append("unsupported_transport")
    if settings.preference_mcp_paid_tools_allowed:
        reasons.append("paid_tools_config_must_remain_false")
    if settings.preference_mcp_daily_call_budget < 1:
        reasons.append("daily_call_budget_exhausted")
    minimum_run_budget = 2 if mode == "live_catalog_only" else 1
    if settings.preference_mcp_run_call_budget < minimum_run_budget:
        reasons.append("run_call_budget_too_low")
    return reasons


def _event_summary(record: dict[str, Any]) -> str:
    return (
        f"{record['domain_pack']} {record['signal_class']}: {record['summary']} "
        f"metric={record['metric']} value={record['value']} {record['unit']}"
    )[:240]


def _sample_query(record: dict[str, Any]) -> str:
    return (
        f"Preference sample {record['domain_pack']} {record['upstream_source']} "
        f"{record['signal_class']} {record['subject']}"
    )


def _payload_fingerprint_fields(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_id": record["record_id"],
        "domain_pack": record["domain_pack"],
        "upstream_source": record["upstream_source"],
        "signal_class": record["signal_class"],
        "subject": record["subject"],
        "metric": record["metric"],
        "value": record["value"],
        "unit": record["unit"],
        "secondary_metric": record["secondary_metric"],
        "secondary_value": record["secondary_value"],
        "source_url": record["source_url"],
        "observed_at": record["observed_at"],
    }


def _event_raw_payload(record: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    authority_flags = _blank_authority_flags()
    provenance = build_preference_provenance_block(
        tool_ref=None,
        pref_request_id=payload.get("pref_request_id"),
        response_id=payload.get("pref_response_id"),
        query=_sample_query(record),
        upstream_source_name=str(record["upstream_source"]),
        upstream_provenance_url=str(record["source_url"]),
        upstream_provenance_id=str(record["record_id"]),
        provenance_path=record["provenance_path"],
        fetched_at=str(payload.get("fetched_at") or _now()),
        observed_at=str(record["observed_at"]),
        freshness_seconds=0,
        cadence="deterministic_sample",
        credit_cost_metadata={
            "mode": "offline_sample",
            "paid_tool": False,
            "credits_consumed": 0,
        },
        payload_fingerprint_fields=_payload_fingerprint_fields(record),
        live_discovered=False,
        raw_response_archived=True,
    )
    return {
        "schema_version": PREFERENCE_MCP_ADAPTER_SCHEMA_VERSION,
        "stage": PREFERENCE_MCP_ADAPTER_STAGE,
        "sample": True,
        "source_key": PREFERENCE_SOURCE_KEY,
        "provider_label": PREFERENCE_PROVIDER_LABEL,
        "classification": PREFERENCE_MCP_ADAPTER_CLASSIFICATION,
        "record_id": record["record_id"],
        "domain_pack": record["domain_pack"],
        "upstream_source": record["upstream_source"],
        "signal_class": record["signal_class"],
        "title": record["title"],
        "subject": record["subject"],
        "metric": record["metric"],
        "value": record["value"],
        "unit": record["unit"],
        "secondary_metric": record["secondary_metric"],
        "secondary_value": record["secondary_value"],
        "source_url": record["source_url"],
        "preference_provenance": provenance,
        "catalog_gate_status": payload["catalog_gate_status"],
        "identity_gate_status": payload["identity_gate_status"],
        "live_mcp_call_attempted": False,
        "search_tools_call_attempted": False,
        "domain_tool_call_attempted": False,
        "paid_tool_call_attempted": False,
        "counts_against_source_quorum": False,
        "sample_observation_only": True,
        "authority_flags": authority_flags,
        "boundary": PREFERENCE_MCP_ADAPTER_BOUNDARY,
    }


class PreferenceMCPAdapter:
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
        identity_status = build_preference_mcp_identity_status(
            settings=self.settings,
            live_status_check=False,
            record_event=False,
        )
        catalog = build_preference_tool_catalog(
            settings=self.settings,
            identity_status=identity_status,
            record_event=False,
        )
        return {
            "schema_version": PREFERENCE_MCP_ADAPTER_SCHEMA_VERSION,
            "stage": PREFERENCE_MCP_ADAPTER_STAGE,
            "sample": True,
            "mode": "deterministic_sample",
            "source_key": PREFERENCE_SOURCE_KEY,
            "source": PREFERENCE_MCP_ADAPTER_SOURCE_LABEL,
            "provider_label": PREFERENCE_PROVIDER_LABEL,
            "classification": PREFERENCE_MCP_ADAPTER_CLASSIFICATION,
            "base_classification": PREFERENCE_CLASSIFICATION,
            "pref_request_id": "pref-sample-request-2026-05-24",
            "pref_response_id": "pref-sample-response-2026-05-24",
            "fetched_at": _now(),
            "identity_gate_status": identity_status.get("status"),
            "identity_gate_identity_status": identity_status.get("identity_status"),
            "catalog_gate_status": catalog.get("status"),
            "catalog_validation_error_count": len(catalog.get("validation_errors", [])),
            "records": deepcopy(list(DEFAULT_PREFERENCE_SAMPLE_RECORDS)),
            "record_count": len(DEFAULT_PREFERENCE_SAMPLE_RECORDS),
            "canonical_source_count": EXPECTED_SOURCE_COUNT,
            "live_mcp_call_attempted": False,
            "search_tools_call_attempted": False,
            "domain_tool_call_attempted": False,
            "paid_tool_call_attempted": False,
            "counts_against_source_quorum": False,
            "authority_flags": _blank_authority_flags(),
            "boundary": PREFERENCE_MCP_ADAPTER_BOUNDARY,
        }

    def normalize_payload(self, payload: dict[str, Any]) -> tuple[UnifiedEvent, ...]:
        records = payload.get("records", [])
        if not isinstance(records, list):
            return ()
        events: list[UnifiedEvent] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            coordinates = record.get("coordinates")
            events.append(
                UnifiedEvent(
                    schema_version=UNIFIED_EVENT_SCHEMA_VERSION,
                    event_id=f"preference-sample:{record['record_id']}",
                    source=PREFERENCE_MCP_ADAPTER_SOURCE_LABEL,
                    trust_score_at_ingestion=PREFERENCE_MCP_SAMPLE_TRUST_SCORE,
                    event_type=str(record["event_type"]),
                    raw_payload=_event_raw_payload(record, payload),
                    normalised_summary=_event_summary(record),
                    coordinates=coordinates if isinstance(coordinates, dict) else None,
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
        archive_path = self.archive.write(PREFERENCE_SOURCE_KEY, payload)
        events = self.normalize_payload(payload)
        envelope = SourceEnvelope(
            events=events,
            source=PREFERENCE_MCP_ADAPTER_SOURCE_LABEL,
            trust_score=PREFERENCE_MCP_SAMPLE_TRUST_SCORE,
            fetched_at=_now(),
            degraded=degraded,
            degraded_reason=degraded_reason,
            raw_archive_path=str(archive_path),
        )
        self.event_log.write(
            "source_adapter_fetch_completed",
            PREFERENCE_MCP_ADAPTER_COMPONENT,
            {
                "stage": PREFERENCE_MCP_ADAPTER_STAGE,
                "source": PREFERENCE_MCP_ADAPTER_SOURCE_LABEL,
                "source_key": PREFERENCE_SOURCE_KEY,
                "classification": PREFERENCE_MCP_ADAPTER_CLASSIFICATION,
                "mode": payload.get("mode"),
                "event_count": len(events),
                "raw_archive_path": envelope.raw_archive_path,
                "identity_gate_status": payload.get("identity_gate_status"),
                "catalog_gate_status": payload.get("catalog_gate_status"),
                "live_mcp_call_attempted": False,
                "search_tools_call_attempted": False,
                "domain_tool_calls_allowed": False,
                "paid_tool_calls_allowed": False,
                "source_quorum_credit_allowed": False,
                "execution_allowed": False,
                "paper_order_allowed": False,
                "broker_write_allowed": False,
                "live_capital_enabled": False,
                "authority_flags": _blank_authority_flags(),
            },
        )
        return envelope

    def fetch_sample(self) -> SourceEnvelope:
        return self.envelope_from_payload(self.sample_payload())


def preference_mcp_adapter_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    identity_status = build_preference_mcp_identity_status(
        settings=settings,
        live_status_check=False,
        record_event=False,
    )
    catalog = build_preference_tool_catalog(
        settings=settings,
        identity_status=identity_status,
        record_event=False,
    )
    archive_root = Path(settings.raw_payload_dir) / PREFERENCE_SOURCE_KEY
    return {
        "status": "ok",
        "schema_version": PREFERENCE_MCP_ADAPTER_SCHEMA_VERSION,
        "stage": PREFERENCE_MCP_ADAPTER_STAGE,
        "mode": "offline_sample_only",
        "classification": PREFERENCE_MCP_ADAPTER_CLASSIFICATION,
        "source_key": PREFERENCE_SOURCE_KEY,
        "source": PREFERENCE_MCP_ADAPTER_SOURCE_LABEL,
        "provider_label": PREFERENCE_PROVIDER_LABEL,
        "canonical_source_count": EXPECTED_SOURCE_COUNT,
        "sample_fixture_count": len(DEFAULT_PREFERENCE_SAMPLE_RECORDS),
        "raw_archive_exists": archive_root.exists(),
        "preference_mcp_enabled": settings.preference_mcp_enabled,
        "identity_gate_status": identity_status.get("status"),
        "identity_gate_identity_status": identity_status.get("identity_status"),
        "identity_validation_error_count": len(
            validate_preference_mcp_identity_status(identity_status)
        ),
        "catalog_gate_status": catalog.get("status"),
        "catalog_entry_count": catalog.get("catalog_entry_count"),
        "catalog_validation_error_count": len(validate_preference_tool_catalog(catalog)),
        "live_mcp_call_allowed": False,
        "search_tools_allowed": False,
        "domain_tool_calls_allowed": False,
        "paid_tool_calls_allowed": False,
        "source_quorum_credit_allowed": False,
        "authority_flags": _blank_authority_flags(),
        "boundary": PREFERENCE_MCP_ADAPTER_BOUNDARY,
        "public_safe_status_boundary": (
            "Do not expose Preference keys, raw MCP responses, callable templates, "
            "or paid-tool metadata in public status."
        ),
    }


def build_preference_mcp_live_smoke(
    *,
    mode: str,
    settings: Settings | None = None,
    event_log: EventLog | None = None,
    record_event: bool = False,
) -> dict[str, Any]:
    if mode not in {"live_status_only", "live_catalog_only"}:
        raise ValueError(f"unsupported Preference live smoke mode: {mode}")

    settings = settings or Settings.from_env()
    credential = secret_status("PREFERENCE_API_KEY", settings)
    api_key = secret_value("PREFERENCE_API_KEY", settings)
    preflight_reasons = _live_preflight_reasons(settings, mode=mode)
    identity_status = build_preference_mcp_identity_status(
        settings=settings,
        live_status_check=True,
        record_event=False,
    )
    identity_errors = validate_preference_mcp_identity_status(identity_status)
    identity_verified = identity_status.get("status") == "verified_non_anonymous"

    catalog_call_attempted = False
    catalog_response_summary: dict[str, Any] | None = None
    catalog_error: str | None = None
    catalog_arguments_summary: dict[str, Any] | None = None
    blocked_reasons: list[str] = list(preflight_reasons)

    if identity_errors:
        blocked_reasons.append("identity_status_validation_failed")
    if mode == "live_catalog_only":
        catalog_arguments_summary = {
            "query": PREFERENCE_MCP_LIVE_CATALOG_QUERY,
            "detail_level": "summary",
            "domain_data_requested": False,
        }
        if not identity_verified:
            blocked_reasons.append("verified_identity_required_for_live_catalog")
        if api_key and identity_verified and not preflight_reasons and not identity_errors:
            catalog_call_attempted = True
            response, catalog_error = _live_tool_call(
                settings=settings,
                api_key=api_key,
                tool_name=PREFERENCE_DISCOVERY_TOOL_NAME,
                arguments={
                    "query": PREFERENCE_MCP_LIVE_CATALOG_QUERY,
                    "detail_level": "summary",
                },
            )
            if response is None:
                blocked_reasons.append(catalog_error or "live_catalog_call_failed")
            else:
                catalog_response_summary = _sanitized_catalog_response_summary(response)
                if catalog_response_summary["jsonrpc_error_present"]:
                    blocked_reasons.append("live_catalog_jsonrpc_error")

    live_call_attempt_count = int(bool(identity_status.get("live_status_call_attempted"))) + int(
        catalog_call_attempted
    )
    if mode == "live_status_only":
        status = "verified_live_status" if identity_verified else "blocked_preflight"
    elif catalog_call_attempted and catalog_error:
        status = "degraded_live_catalog_error"
    elif catalog_call_attempted and catalog_response_summary:
        status = "live_catalog_checked"
    else:
        status = "blocked_pending_verified_identity"

    artifact = {
        "schema_version": PREFERENCE_MCP_LIVE_SMOKE_SCHEMA_VERSION,
        "artifact_type": PREFERENCE_MCP_LIVE_SMOKE_ARTIFACT_TYPE,
        "artifact_id": PREFERENCE_MCP_LIVE_SMOKE_ARTIFACT_ID,
        "phase": "PREF",
        "stage": PREFERENCE_MCP_LIVE_SMOKE_STAGE,
        "status": status,
        "mode": mode,
        "generated_at": _now(),
        "public_safe": True,
        "classification": PREFERENCE_MCP_ADAPTER_CLASSIFICATION,
        "source_key": PREFERENCE_SOURCE_KEY,
        "provider_label": PREFERENCE_PROVIDER_LABEL,
        "endpoint": settings.preference_mcp_endpoint,
        "transport": settings.preference_mcp_transport,
        "enabled": settings.preference_mcp_enabled,
        "credential_status": {
            "key": "PREFERENCE_API_KEY",
            "configured": credential.configured,
            "source": credential.source,
        },
        "daily_call_budget": settings.preference_mcp_daily_call_budget,
        "run_call_budget": settings.preference_mcp_run_call_budget,
        "live_call_attempt_count": live_call_attempt_count,
        "paid_tools_allowed_by_config": settings.preference_mcp_paid_tools_allowed,
        "identity_status": identity_status,
        "identity_gate_status": identity_status.get("status"),
        "identity_gate_identity_status": identity_status.get("identity_status"),
        "identity_gate_quota_metadata_present": identity_status.get("quota_metadata_present"),
        "identity_validation_error_count": len(identity_errors),
        "status_tool_name": PREFERENCE_STATUS_TOOL_NAME,
        "discovery_tool_name": PREFERENCE_DISCOVERY_TOOL_NAME,
        "live_status_only_requested": mode == "live_status_only",
        "live_catalog_only_requested": mode == "live_catalog_only",
        "live_status_call_attempted": bool(identity_status.get("live_status_call_attempted")),
        "live_catalog_call_attempted": catalog_call_attempted,
        "search_tools_call_attempted": catalog_call_attempted,
        "catalog_arguments_summary": catalog_arguments_summary,
        "catalog_response_summary": catalog_response_summary,
        "catalog_error": catalog_error,
        "domain_tool_call_attempted": False,
        "paid_tool_call_attempted": False,
        "live_read_only_tool_call_attempted": False,
        "domain_data_requested": False,
        "source_quorum_credit_allowed": False,
        "domain_tool_calls_allowed": False,
        "paid_tool_calls_allowed": False,
        "blocked_reasons": sorted(set(blocked_reasons)),
        "blocked_reason_count": len(set(blocked_reasons)),
        "authority_flags": _blank_authority_flags(),
        "boundary": PREFERENCE_MCP_LIVE_SMOKE_BOUNDARY,
    }
    artifact["validation_errors"] = validate_preference_mcp_live_smoke(artifact)

    if record_event:
        event_log = event_log or EventLog(echo=False)
        event_log.write(
            PREFERENCE_MCP_LIVE_SMOKE_EVENT_TYPE,
            PREFERENCE_MCP_LIVE_SMOKE_EVENT_COMPONENT,
            {
                "stage": artifact["stage"],
                "status": artifact["status"],
                "mode": artifact["mode"],
                "identity_gate_status": artifact["identity_gate_status"],
                "live_status_call_attempted": artifact["live_status_call_attempted"],
                "live_catalog_call_attempted": artifact["live_catalog_call_attempted"],
                "search_tools_call_attempted": artifact["search_tools_call_attempted"],
                "domain_tool_call_attempted": False,
                "paid_tool_call_attempted": False,
                "source_quorum_credit_allowed": False,
                "domain_tool_calls_allowed": False,
                "paid_tool_calls_allowed": False,
                "broker_write_allowed": False,
                "live_capital_enabled": False,
                "blocked_reasons": artifact["blocked_reasons"],
            },
        )
    return artifact


def preference_mcp_live_smoke_paths(settings: Settings | None = None) -> tuple[Path, Path]:
    settings = settings or Settings.from_env()
    runtime_dir = Path(settings.runtime_dir)
    return (
        runtime_dir / "preference_mcp_live_smoke.json",
        runtime_dir / "preference_mcp_live_smoke_history.jsonl",
    )


def write_preference_mcp_live_smoke(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
) -> tuple[Path, Path]:
    output_path, history_path = preference_mcp_live_smoke_paths(settings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    artifact["runtime_artifact_path"] = str(output_path)
    artifact["history_log_path"] = str(history_path)
    artifact["validation_errors"] = validate_preference_mcp_live_smoke(artifact)
    output_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PREFERENCE_MCP_LIVE_SMOKE_SCHEMA_VERSION,
        "artifact_id": artifact.get("artifact_id"),
        "stage": artifact.get("stage"),
        "mode": artifact.get("mode"),
        "status": artifact.get("status"),
        "generated_at": artifact.get("generated_at"),
        "recorded_at": _now(),
        "identity_gate_status": artifact.get("identity_gate_status"),
        "live_status_call_attempted": artifact.get("live_status_call_attempted"),
        "live_catalog_call_attempted": artifact.get("live_catalog_call_attempted"),
        "search_tools_call_attempted": artifact.get("search_tools_call_attempted"),
        "domain_tool_call_attempted": artifact.get("domain_tool_call_attempted"),
        "paid_tool_call_attempted": artifact.get("paid_tool_call_attempted"),
        "blocked_reasons": artifact.get("blocked_reasons"),
        "validation_error_count": len(artifact.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path


def validate_preference_mcp_live_smoke(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version",
        "artifact_type",
        "stage",
        "status",
        "mode",
        "public_safe",
        "credential_status",
        "identity_status",
        "live_status_call_attempted",
        "live_catalog_call_attempted",
        "search_tools_call_attempted",
        "domain_tool_call_attempted",
        "paid_tool_call_attempted",
        "live_read_only_tool_call_attempted",
        "domain_data_requested",
        "source_quorum_credit_allowed",
        "domain_tool_calls_allowed",
        "paid_tool_calls_allowed",
        "authority_flags",
        "boundary",
    }
    for field in sorted(required - set(artifact)):
        errors.append(f"missing_field:{field}")
    if artifact.get("schema_version") != PREFERENCE_MCP_LIVE_SMOKE_SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if artifact.get("artifact_type") != PREFERENCE_MCP_LIVE_SMOKE_ARTIFACT_TYPE:
        errors.append("artifact_type_not_preference_mcp_live_smoke_gate")
    if artifact.get("stage") != PREFERENCE_MCP_LIVE_SMOKE_STAGE:
        errors.append("stage_not_pref_4")
    if artifact.get("mode") not in {"live_status_only", "live_catalog_only"}:
        errors.append("unsupported_live_smoke_mode")
    if artifact.get("public_safe") is not True:
        errors.append("public_safe_not_true")
    if artifact.get("domain_tool_call_attempted") is not False:
        errors.append("domain_tool_call_attempted")
    if artifact.get("paid_tool_call_attempted") is not False:
        errors.append("paid_tool_call_attempted")
    if artifact.get("live_read_only_tool_call_attempted") is not False:
        errors.append("live_read_only_tool_call_attempted")
    if artifact.get("domain_data_requested") is not False:
        errors.append("domain_data_requested")
    if artifact.get("source_quorum_credit_allowed") is not False:
        errors.append("source_quorum_credit_allowed")
    if artifact.get("domain_tool_calls_allowed") is not False:
        errors.append("domain_tool_calls_allowed")
    if artifact.get("paid_tool_calls_allowed") is not False:
        errors.append("paid_tool_calls_allowed")
    if artifact.get("paid_tools_allowed_by_config") is not False:
        errors.append("paid_tools_allowed_by_config")
    if int(artifact.get("live_call_attempt_count") or 0) > int(
        artifact.get("run_call_budget") or 0
    ):
        errors.append("live_call_attempt_count_exceeds_run_budget")

    identity_status = artifact.get("identity_status")
    if not isinstance(identity_status, dict):
        errors.append("identity_status_not_object")
    else:
        identity_errors = validate_preference_mcp_identity_status(identity_status)
        for error in identity_errors:
            errors.append(f"identity_status_invalid:{error}")

    if artifact.get("mode") == "live_status_only":
        if artifact.get("live_catalog_call_attempted") is not False:
            errors.append("live_status_only_attempted_catalog")
        if artifact.get("search_tools_call_attempted") is not False:
            errors.append("live_status_only_attempted_search_tools")

    if artifact.get("mode") == "live_catalog_only":
        if artifact.get("search_tools_call_attempted") != artifact.get(
            "live_catalog_call_attempted"
        ):
            errors.append("search_tools_attempt_mismatch")
        if (
            artifact.get("live_catalog_call_attempted") is True
            and artifact.get("identity_gate_status") != "verified_non_anonymous"
        ):
            errors.append("live_catalog_without_verified_identity")
        if (
            artifact.get("status") == "live_catalog_checked"
            and artifact.get("catalog_response_summary") is None
        ):
            errors.append("live_catalog_checked_without_summary")
    if artifact.get("status", "").startswith("blocked") and not artifact.get("blocked_reasons"):
        errors.append("blocked_without_reason")

    flags = artifact.get("authority_flags", {})
    if not isinstance(flags, dict):
        errors.append("authority_flags_not_object")
    else:
        for key, value in flags.items():
            if value is not False:
                errors.append(f"authority_flag_enabled:{key}")
    credential_status = artifact.get("credential_status", {})
    if isinstance(credential_status, dict) and any(
        str(value).startswith("pref_agent_") for value in credential_status.values()
    ):
        errors.append("credential_secret_value_exposed")
    if _contains_secret_like_value(artifact):
        errors.append("secret_like_value_exposed")
    return errors


def validate_preference_mcp_sample_envelope(envelope: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {"events", "source", "trust_score", "fetched_at", "degraded", "raw_archive_path"}
    for field in sorted(required - set(envelope)):
        errors.append(f"missing_field:{field}")
    if envelope.get("source") != PREFERENCE_MCP_ADAPTER_SOURCE_LABEL:
        errors.append("source_mismatch")
    if envelope.get("degraded") is not False:
        errors.append("sample_envelope_degraded")
    archive_path = str(envelope.get("raw_archive_path") or "")
    if PREFERENCE_SOURCE_KEY not in archive_path:
        errors.append("raw_archive_path_not_preference_mcp")
    events = envelope.get("events", [])
    if not isinstance(events, list) or not events:
        errors.append("events_missing")
        events = []
    if len(events) != len(DEFAULT_PREFERENCE_SAMPLE_RECORDS):
        errors.append("sample_event_count_mismatch")

    expected_event_ids = {
        f"preference-sample:{record['record_id']}" for record in DEFAULT_PREFERENCE_SAMPLE_RECORDS
    }
    observed_event_ids: set[str] = set()
    observed_domain_packs: set[str] = set()
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            errors.append(f"event_not_object:{index}")
            continue
        if event.get("schema_version") != UNIFIED_EVENT_SCHEMA_VERSION:
            errors.append(f"event_schema_version_mismatch:{index}")
        event_id = str(event.get("event_id") or "")
        observed_event_ids.add(event_id)
        raw_payload = event.get("raw_payload")
        if not isinstance(raw_payload, dict):
            errors.append(f"event_raw_payload_missing:{index}")
            continue
        observed_domain_packs.add(str(raw_payload.get("domain_pack") or ""))
        if raw_payload.get("sample") is not True:
            errors.append(f"event_not_sample:{index}")
        if raw_payload.get("stage") != PREFERENCE_MCP_ADAPTER_STAGE:
            errors.append(f"event_stage_mismatch:{index}")
        if raw_payload.get("live_mcp_call_attempted") is not False:
            errors.append(f"event_live_mcp_call_attempted:{index}")
        if raw_payload.get("search_tools_call_attempted") is not False:
            errors.append(f"event_search_tools_call_attempted:{index}")
        if raw_payload.get("domain_tool_call_attempted") is not False:
            errors.append(f"event_domain_tool_call_attempted:{index}")
        if raw_payload.get("paid_tool_call_attempted") is not False:
            errors.append(f"event_paid_tool_call_attempted:{index}")
        if raw_payload.get("counts_against_source_quorum") is not False:
            errors.append(f"event_counts_against_source_quorum:{index}")
        provenance = raw_payload.get("preference_provenance")
        if not isinstance(provenance, dict):
            errors.append(f"event_preference_provenance_missing:{index}")
        else:
            if provenance.get("provenance_mode") != "deterministic_sample":
                errors.append(f"event_provenance_mode_mismatch:{index}")
            if provenance.get("live_discovered") is not False:
                errors.append(f"event_live_discovered:{index}")
            if provenance.get("tool_ref") is not None:
                errors.append(f"event_tool_ref_present:{index}")
        flags = raw_payload.get("authority_flags", {})
        if not isinstance(flags, dict):
            errors.append(f"event_authority_flags_missing:{index}")
        else:
            for key, value in flags.items():
                if value is not False:
                    errors.append(f"event_authority_flag_enabled:{index}:{key}")
        if event.get("source") != PREFERENCE_MCP_ADAPTER_SOURCE_LABEL:
            errors.append(f"event_source_mismatch:{index}")
        if not str(event.get("normalised_summary") or "").strip():
            errors.append(f"event_summary_missing:{index}")

    if observed_event_ids != expected_event_ids:
        errors.append("sample_event_ids_mismatch")
    required_domain_packs = {
        "prediction_markets",
        "physical_movement",
        "macro_commodities",
        "filings_corporate",
        "crypto_wallets",
    }
    if not required_domain_packs.issubset(observed_domain_packs):
        errors.append("required_domain_packs_missing")
    if "sports_lines" in observed_domain_packs:
        errors.append("sports_lines_sample_included")
    if _contains_secret_like_value(envelope):
        errors.append("secret_like_value_exposed")
    return errors


def fetch_preference_mcp_sample() -> dict[str, Any]:
    return PreferenceMCPAdapter().fetch_sample().to_dict()
