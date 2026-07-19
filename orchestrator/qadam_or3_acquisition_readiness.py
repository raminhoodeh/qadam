"""OR-2R connection truth and OR-3 acquisition-readiness gate.

The gate proves transport and storage mechanics on a bounded real-data slice.
It never promotes pilot rows into canonical evidence and never purchases data,
edits credentials, creates a trade object, or advances paper-trial time.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    sha256_json,
    unique_errors,
    validate_authority,
    write_json_atomic,
)
from orchestrator.qadam_source_provider_capabilities import (
    DERIVED_ONLY,
    DISABLED_OR_UNSELECTED,
    FORWARD_ONLY,
    HISTORICAL_SUPPORTED,
)
from orchestrator.tradingview_mcp_adapter import (
    TRADINGVIEW_MCP_CONNECTION_STATES,
    TradingViewMCPAdapter,
    tradingview_mcp_adapter_status,
)

SCHEMA_VERSION = "qadam_or3_acquisition_readiness.v1"
PHASE_ID = "OR-2R"
PAPER_ACCOUNT_STARTING_CAPITAL_USD = 100_000

CONNECTION_TRUTH_ARTIFACT = "qadam_connection_truth.json"
TRADINGVIEW_STATUS_ARTIFACT = "qadam_tradingview_supplemental_status.json"
PURCHASE_MATRIX_ARTIFACT = "qadam_historical_provider_purchase_matrix.json"
SOURCE_MATRIX_ARTIFACT = "qadam_historical_source_coverage_matrix.json"
TERMS_REVIEW_ARTIFACT = "qadam_or3_provider_terms_review.json"
PILOT_MANIFEST_ARTIFACT = "qadam_or3_provider_pilot_manifest.json"
PILOT_RESULTS_ARTIFACT = "qadam_or3_provider_pilot_results.json"
READINESS_ARTIFACT = "qadam_or3_acquisition_readiness.json"

SOURCE_UNIVERSE_ARTIFACT = "qsase_source_universe.json"
TRADING_UNIVERSE_ARTIFACT = "qsase_trading_universe.json"
CAPABILITY_ARTIFACT = "qadam_provider_capability_registry.jsonl"
LONG_LOCK_ARTIFACT = "qadam_long_backtest_lock.json"
BACKFILL_SOURCE_MANIFEST = "qadam_source_backfill_manifest.json"
BACKFILL_PRICE_MANIFEST = "qadam_price_backfill_manifest.json"

RESEARCH_ROOT = ROOT / "data" / "research" / "or2r_pilot"
OPERATOR_APPROVAL_CONTRACT = ROOT / "ops" / "qadam_or3_operator_approval.json"
PROVIDER_TERMS_REVIEW_CONTRACT = ROOT / "ops" / "qadam_or3_provider_terms_review.json"
ALLOWED_MATRIX_STATES = {
    "pilot_ready",
    "blocked_credentials",
    "blocked_purchase_review",
    "unsupported_history",
    "proxy_proposed",
    "forward_only",
    "excluded",
}


def _read_contract(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _operator_approval() -> dict[str, Any]:
    return _read_contract(OPERATOR_APPROVAL_CONTRACT)


def _provider_terms_review() -> dict[str, Any]:
    return _read_contract(PROVIDER_TERMS_REVIEW_CONTRACT)

EQUITY_ETF_SYMBOLS = {
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
}
FUTURES_PROXIES = {"CL=F": ["USO", "BNO"], "SI=F": ["SLV", "SIL"]}
PREDICTION_PROVIDERS = {
    "KALSHI:EVENTS": (
        "Kalshi public/trading APIs",
        "https://docs.kalshi.com/",
    ),
    "POLYMARKET:EVENTS": (
        "Polymarket Gamma and CLOB APIs",
        "https://docs.polymarket.com/",
    ),
}


def _safe_relative(path: Path) -> str:
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else path.name


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.part")
    with temporary.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _lock_state(runtime: Path) -> tuple[dict[str, Any], list[str]]:
    lock = read_json(runtime / LONG_LOCK_ARTIFACT)
    errors: list[str] = []
    if lock.get("status") != "active":
        errors.append("research_lock_not_active")
    if lock.get("paperops_watch_only_mode") is not True:
        errors.append("paperops_not_watch_only")
    for key in (
        "paper_order_creation_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
        "paper_growth_trial_calendar_advance_allowed",
        "simulated_elapsed_time_allowed",
    ):
        if lock.get(key) is not False:
            errors.append(f"unsafe_lock_field:{key}")
    return lock, errors


def build_connection_truth(settings: Settings | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    active = settings or Settings.from_env()
    # A live-mode fetch writes only live/degraded truth. It never substitutes fixtures.
    TradingViewMCPAdapter(settings=active).fetch_live()
    tradingview = tradingview_mcp_adapter_status(active)
    state = str(tradingview.get("connection_state") or "provider_error")
    truthful = (
        state in TRADINGVIEW_MCP_CONNECTION_STATES
        and tradingview.get("connected") is (state == "live_supplemental")
        and int(tradingview.get("sample_records_in_canonical_context_count") or 0) == 0
    )
    generated_at = now_iso()
    supplemental = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_tradingview_supplemental_status",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": state,
        "connection_state": state,
        "truthful_state": truthful,
        "connected": tradingview.get("connected") is True,
        "enabled": tradingview.get("enabled") is True,
        "live_calls_enabled": tradingview.get("live_calls_enabled") is True,
        "local_checkout_exists": tradingview.get("local_checkout_exists") is True,
        "local_package_importable": tradingview.get("package_importable") is True,
        "service_importable": tradingview.get("service_importable") is True,
        "tradingview_ta_importable": tradingview.get("tradingview_ta_importable") is True,
        "tradingview_screener_importable": tradingview.get("tradingview_screener_importable") is True,
        "missing_dependency": tradingview.get("missing_dependency"),
        "library_versions": tradingview.get("library_versions", {}),
        "provider_backed_record_count": (
            int(tradingview.get("technical_context_count") or 0)
            if state == "live_supplemental"
            else 0
        ),
        "sample_record_count_in_canonical_state": int(
            tradingview.get("sample_records_in_canonical_context_count") or 0
        ),
        "official_tradingview_market_data_api": False,
        "historical_coverage_credit_allowed": False,
        "source_quorum_credit_allowed": False,
        "optional_manual_subscription_required": False,
        "terms_note": tradingview.get("terms_note"),
        "boundary": (
            "TradingView is optional supplemental confirmation. A local import or fixture is not a "
            "live connection and cannot close historical coverage."
        ),
        "authority": authority_flags(),
    }
    truth = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_connection_truth",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "truthful" if truthful else "invalid",
        "components": [
            {
                "component_id": "tradingview_supplemental",
                "reported_state": state,
                "local_import_counts_as_live": False,
                "fixture_counts_as_live": False,
                "real_provider_response_required": True,
                "truthful": truthful,
            },
            {
                "component_id": "historical_provider_pilot",
                "reported_state": "not_run_until_pilot_results_are_written",
                "local_import_counts_as_live": False,
                "fixture_counts_as_live": False,
                "real_provider_response_required": True,
                "truthful": True,
            },
        ],
        "false_live_connection_count": 0 if truthful else 1,
        "authority": authority_flags(),
    }
    return truth, supplemental


def _instrument_row(instrument: dict[str, Any]) -> dict[str, Any]:
    symbol = str(instrument.get("symbol") or "").upper()
    family = str(instrument.get("market_family") or "unknown")
    paperability = str(instrument.get("paperability_state") or "unknown")
    if symbol in EQUITY_ETF_SYMBOLS:
        asset_class = "equity" if symbol in {"LMT", "NVDA"} else "etf"
        provider = "Alpaca Market Data API"
        api = "https://docs.alpaca.markets/reference/stockbars"
        status = "blocked_purchase_review"
        proxy = symbol
        coverage = "US listed history subject to plan entitlement and symbol availability"
        credential = "operator-managed Alpaca market-data credentials"
        rate_limit = "plan-specific; bounded serial acquisition required"
        licensing = "research/commercial retention and redistribution review required"
        adjustment = "provider adjustment mode, splits, dividends, and symbol changes must be frozen"
        expected_cost = "unknown until Alpaca data entitlement is confirmed"
    elif symbol in FUTURES_PROXIES:
        asset_class = "continuous_futures_research_context"
        provider = "Licensed futures history provider not selected"
        api = "operator selection required"
        status = "proxy_proposed"
        proxy = ", ".join(FUTURES_PROXIES[symbol])
        coverage = "continuous-contract and roll history not yet licensed"
        credential = "provider account not selected"
        rate_limit = "unknown until provider selection"
        licensing = "futures history license and commercial research rights required"
        adjustment = "roll schedule, back-adjustment, expiry, timezone, and basis risk required"
        expected_cost = "purchase review required"
    else:
        asset_class = "prediction_market_contract_history"
        provider, api = PREDICTION_PROVIDERS.get(
            symbol, ("Prediction-market provider not selected", "operator review required")
        )
        status = "blocked_purchase_review"
        proxy = "none approved"
        coverage = "contract identity, lifecycle, settlement, and archive depth require validation"
        credential = "public reads where supported; trading credentials are out of scope"
        rate_limit = "provider-specific public API budget"
        licensing = "archive, retention, redistribution, and commercial-use review required"
        adjustment = "contract version, expiry, settlement, and event taxonomy required"
        expected_cost = "unknown pending archive/interface review"
    return {
        "matrix_row_id": "instrument-provider:" + sha256_json({"symbol": symbol, "provider": provider})[:20],
        "canonical_dataset": f"price_history:{symbol}",
        "symbol": symbol,
        "market_family": family,
        "strategy_and_discovery_roles": [family, "whole_universe_pattern_search"],
        "asset_class": asset_class,
        "venue_and_contract_identity": "provider canonical mapping required",
        "paperability_state": paperability,
        "paper_proxy": proxy,
        "target_initial_resolution": "1d adjusted bars or provider-native settled event history",
        "intraday_required_for_initial_run": False,
        "provider": provider,
        "official_api_or_interface": api,
        "api_availability": "documented_interface_operator_validation_required",
        "historical_coverage": coverage,
        "earliest_supported_timestamp": "provider query required",
        "latest_supported_timestamp": "provider query required",
        "expected_gaps": "holidays, suspensions, symbol changes, and provider-specific omissions",
        "granularity": "daily baseline",
        "timezone_semantics": "exchange calendar and UTC normalization required",
        "adjustment_roll_revision_semantics": adjustment,
        "pagination": "provider-native page token or bounded date partitions",
        "rate_limits": rate_limit,
        "credential_class": credential,
        "manual_setup_required": True,
        "licensing": licensing,
        "retention_and_redistribution": "operator and legal review required before bulk acquisition",
        "expected_cost": expected_cost,
        "estimated_rows": 3000 if asset_class in {"equity", "etf"} else 5000,
        "estimated_storage_mb": 2 if asset_class in {"equity", "etf"} else 5,
        "estimated_duration_minutes": 3,
        "fallback_provider_or_proxy": proxy,
        "proxy_approval_state": "operator_review_required",
        "pilot_provider": "Yahoo Finance public chart interface" if symbol in {"USO", "SLV"} else None,
        "pilot_status": "pilot_ready" if symbol in {"USO", "SLV"} else "not_in_pilot",
        "status": status,
        "system_review_complete": True,
        "operator_approval_complete": False,
        "purchase_performed": False,
        "terms_accepted_by_automation": False,
        "authority": authority_flags(),
    }


def _apply_instrument_approval(
    row: dict[str, Any],
    approval: dict[str, Any],
) -> dict[str, Any]:
    symbol = str(row.get("symbol") or "").upper()
    decisions = approval.get("instrument_provider_decisions", {})
    decision = decisions.get(symbol, {}) if isinstance(decisions, dict) else {}
    if not isinstance(decision, dict):
        decision = {}
    approved = decision.get("operator_approved") is True
    provider_state = str(decision.get("state") or "unrecorded")

    updates: dict[str, Any] = {
        "operator_approval_complete": approved,
        "operator_decision_state": provider_state,
        "operator_decision_recorded_at": approval.get("recorded_at"),
        "operator_use_case": approval.get("current_use_case"),
        "redistribution_allowed": False,
        "future_commercial_relicense_required": approval.get(
            "future_commercial_relicense_required"
        )
        is True,
    }
    if symbol in EQUITY_ETF_SYMBOLS and approved:
        updates.update(
            {
                "status": "pilot_ready",
                "api_availability": "existing_account_entitlement_operator_approved",
                "manual_setup_required": False,
                "licensing": (
                    "Approved for current private internal non-commercial research under the "
                    "operator's existing Alpaca account terms; no redistribution."
                ),
                "retention_and_redistribution": (
                    "Local research retention only; no raw redistribution; re-review before any "
                    "commercial deployment."
                ),
                "expected_cost": "existing entitlement; no incremental historical purchase assumed",
                "proxy_approval_state": "same_symbol_history_approved",
            }
        )
    elif symbol in FUTURES_PROXIES:
        databento = approval.get("databento", {})
        if not isinstance(databento, dict):
            databento = {}
        quote = databento.get("definitive_quote_usd")
        budget = approval.get("historical_data_purchase_budget_usd")
        monthly_limit = databento.get("historical_monthly_limit_usd")
        download_authorized = databento.get("download_authorized") is True
        cost_approved = (
            isinstance(quote, (int, float))
            and isinstance(budget, (int, float))
            and quote <= budget
            and isinstance(monthly_limit, (int, float))
            and quote <= monthly_limit <= budget
            and download_authorized
        )
        updates.update(
            {
                "provider": "Databento CME Globex MDP 3.0",
                "official_api_or_interface": "https://databento.com/docs/portal",
                "api_availability": "account_enabled_quote_required_before_download",
                "historical_coverage": (
                    "CME crude-oil and silver futures history; exact date coverage must be frozen "
                    "in the quoted request."
                ),
                "credential_class": "operator-managed Databento API key; never stored in this contract",
                "rate_limits": "Databento batch-download and account usage limits",
                "licensing": (
                    "Private internal non-commercial research only; no redistribution; exchange "
                    "entitlements and request terms must remain attached to the batch manifest."
                ),
                "retention_and_redistribution": (
                    "Local private research retention only; no redistribution; re-license before "
                    "commercial packaging."
                ),
                "expected_cost": quote if isinstance(quote, (int, float)) else "definitive quote pending",
                "fallback_provider_or_proxy": ", ".join(FUTURES_PROXIES[symbol]),
                "proxy_approval_state": "approved_for_basis_risk_and_execution_context_only",
                "manual_setup_required": not cost_approved,
                "status": "pilot_ready" if cost_approved else "blocked_purchase_review",
                "operator_approval_complete": cost_approved,
                "databento_quote_usd": quote,
                "historical_data_purchase_budget_usd": budget,
                "historical_monthly_limit_usd": monthly_limit,
                "download_authorized": download_authorized,
                "initial_schema": databento.get("initial_schema") or "ohlcv-1d",
                "dataset": databento.get("dataset") or "GLBX.MDP3",
            }
        )
    elif symbol == "KALSHI:EVENTS" and approved:
        updates.update(
            {
                "status": "pilot_ready",
                "provider": "Kalshi historical API with Oddspipe read-only bridge",
                "api_availability": "official_historical_endpoints_documented_adapter_pilot_required",
                "manual_setup_required": False,
                "credential_class": (
                    "Oddspipe read-only key configured; direct Kalshi keypair not verified"
                ),
                "licensing": (
                    "Operator accepted the Kalshi Developer Agreement for current private internal "
                    "non-commercial research; no redistribution."
                ),
                "retention_and_redistribution": "Local normalized research records only; no redistribution.",
                "expected_cost": "no historical purchase approved or expected",
            }
        )
    elif symbol == "POLYMARKET:EVENTS" and approved:
        updates.update(
            {
                "status": "pilot_ready",
                "provider": "Polymarket Gamma and CLOB public APIs",
                "api_availability": "public_market_data_no_authentication_required",
                "manual_setup_required": False,
                "credential_class": "no API key required for public read-only market data",
                "licensing": (
                    "Operator reviewed and accepted applicable terms for current private internal "
                    "non-commercial research; no redistribution."
                ),
                "retention_and_redistribution": "Local normalized research records only; no redistribution.",
                "expected_cost": "public read-only endpoints; no historical purchase expected",
            }
        )
    return {**row, **updates}


def build_purchase_matrix(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    universe = read_json(runtime / TRADING_UNIVERSE_ARTIFACT)
    instruments = universe.get("instruments") if isinstance(universe.get("instruments"), list) else []
    approval = _operator_approval()
    rows = [_apply_instrument_approval(_instrument_row(record), approval) for record in instruments]
    blocking = [
        row
        for row in rows
        if row.get("status") not in {"forward_only", "excluded"}
        and row.get("operator_approval_complete") is not True
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_historical_provider_purchase_matrix",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "reviewed_with_blockers" if blocking else "reviewed",
        "instrument_count": len(rows),
        "rows": rows,
        "status_counts": {state: sum(row["status"] == state for row in rows) for state in sorted(ALLOWED_MATRIX_STATES)},
        "purchase_performed_count": 0,
        "terms_accepted_by_automation_count": 0,
        "baseline_resolution": "daily_or_event",
        "operator_contract_path": str(OPERATOR_APPROVAL_CONTRACT.relative_to(ROOT)),
        "operator_contract_present": bool(approval),
        "blocking_row_count": len(blocking),
        "authority": authority_flags(),
    }


def _source_interface(source_key: str, source_name: str) -> tuple[str, str]:
    known = {
        "fred": ("FRED public CSV/API", "https://fred.stlouisfed.org/docs/api/fred/"),
        "usgs": ("USGS Earthquake Catalog API", "https://earthquake.usgs.gov/fdsnws/event/1/"),
        "acled": ("ACLED API", "https://acleddata.com/acled-api-documentation"),
        "gdelt": ("GDELT APIs and archives", "https://www.gdeltproject.org/"),
        "sec_edgar": ("SEC EDGAR submissions/data APIs", "https://www.sec.gov/edgar/sec-api-documentation"),
        "un_comtrade": ("UN Comtrade API", "https://comtradeapi.un.org/"),
        "yahoo_finance": ("Yahoo Finance public chart interface", "unofficial interface; terms review required"),
        "kalshi": ("Kalshi APIs", "https://docs.kalshi.com/"),
        "polymarket": ("Polymarket APIs", "https://docs.polymarket.com/"),
    }
    return known.get(source_key, (source_name, "provider interface review required"))


def _source_row(source: dict[str, Any], capability: dict[str, Any]) -> dict[str, Any]:
    key = str(source.get("source_key") or "unknown")
    name = str(source.get("source_name") or key)
    category = str(capability.get("source_category") or source.get("source_family") or "other")
    provider, interface = _source_interface(key, name)
    if key in {"fred", "usgs"}:
        status = "pilot_ready"
        licensing = "public read-only pilot allowed; bulk retention and commercial use still require review"
        operator_approval = False
    elif key in HISTORICAL_SUPPORTED:
        status = "blocked_purchase_review"
        licensing = "provider terms, retention, redistribution, and commercial use require review"
        operator_approval = False
    elif key in FORWARD_ONLY:
        status = "forward_only"
        licensing = "capture prospectively only under existing adapter terms"
        operator_approval = True
    elif key in DERIVED_ONLY:
        status = "proxy_proposed"
        licensing = "derive only from reviewed upstream records; never double-count as independent history"
        operator_approval = False
    elif key in DISABLED_OR_UNSELECTED:
        status = "excluded"
        licensing = "not selected for initial historical run"
        operator_approval = True
    else:
        status = "unsupported_history"
        licensing = "historical interface not established"
        operator_approval = False
    estimated_rows = 50000 if key in HISTORICAL_SUPPORTED else 0
    return {
        "matrix_row_id": "source-provider:" + sha256_json({"source": key, "provider": provider})[:20],
        "canonical_dataset": f"source_history:{key}",
        "source_key": key,
        "source_name": name,
        "source_category": category,
        "strategy_and_discovery_roles": ["whole_universe_pattern_search", category],
        "provider": provider,
        "official_api_or_interface": interface,
        "api_availability": capability.get("historical_capability_class") or "unknown",
        "historical_coverage": capability.get("earliest_available_date_state") or "provider query required",
        "earliest_supported_timestamp": capability.get("earliest_available_date"),
        "latest_supported_timestamp": "provider query required",
        "expected_gaps": "source-specific outages, revisions, and archive limits",
        "granularity": capability.get("native_granularity") or "provider native",
        "timezone_semantics": "provider event time normalized to UTC; availability time retained separately",
        "adjustment_roll_revision_semantics": capability.get("revision_vintage_semantics") or "review required",
        "pagination": capability.get("pagination_model") or "review required",
        "rate_limits": capability.get("rate_limit_policy") or "bounded provider-specific budget",
        "credential_class": capability.get("credential_requirement", {}),
        "manual_setup_required": status in {"blocked_credentials", "blocked_purchase_review"},
        "licensing": licensing,
        "retention_and_redistribution": "operator review required unless explicitly forward-only or excluded",
        "expected_cost": "unknown pending provider decision" if status == "blocked_purchase_review" else "no purchase in pilot",
        "estimated_rows": estimated_rows,
        "estimated_storage_mb": round(estimated_rows * 600 / 1_000_000, 2),
        "estimated_duration_minutes": max(1, round(estimated_rows / 10000)) if estimated_rows else 0,
        "fallback_provider_or_proxy": capability.get("fallback_or_proxy") or "none approved",
        "status": status,
        "system_review_complete": True,
        "operator_approval_complete": operator_approval,
        "purchase_performed": False,
        "terms_accepted_by_automation": False,
        "forward_only": status == "forward_only",
        "evidence_eligible_from_pilot": False,
        "authority": authority_flags(),
    }


def _apply_source_terms_review(
    row: dict[str, Any],
    review: dict[str, Any],
) -> dict[str, Any]:
    records = review.get("sources") if isinstance(review.get("sources"), list) else []
    by_key = {str(record.get("source_key")): record for record in records}
    decision = by_key.get(str(row.get("source_key")))
    if not isinstance(decision, dict):
        return {
            **row,
            "status": "excluded",
            "operator_approval_complete": True,
            "terms_review_state": "missing_review_excluded_fail_closed",
            "licensing": "No reviewed retention contract is present; excluded from OR-3.",
            "retention_and_redistribution": "No acquisition or retention allowed.",
        }
    classification = str(decision.get("classification") or "excluded")
    status = {
        "historical_approved": "pilot_ready",
        "forward_only": "forward_only",
        "excluded": "excluded",
    }.get(classification, "excluded")
    return {
        **row,
        "status": status,
        "operator_approval_complete": True,
        "forward_only": status == "forward_only",
        "manual_setup_required": False,
        "terms_review_state": "reviewed",
        "terms_reviewed_at": review.get("reviewed_at"),
        "terms_reference": decision.get("terms_reference"),
        "licensing": decision.get("licensing_summary"),
        "retention_and_redistribution": decision.get("retention_policy"),
        "classification_reason": decision.get("reason"),
        "current_use_scope": review.get("current_use_scope"),
        "future_commercial_relicense_required": review.get(
            "future_commercial_relicense_required"
        )
        is True,
        "estimated_rows": int(row.get("estimated_rows") or 0)
        if status == "pilot_ready"
        else 0,
        "estimated_storage_mb": row.get("estimated_storage_mb") if status == "pilot_ready" else 0,
        "estimated_duration_minutes": (
            row.get("estimated_duration_minutes") if status == "pilot_ready" else 0
        ),
    }


def build_provider_terms_review(settings: Settings | None = None) -> dict[str, Any]:
    del settings
    contract = _provider_terms_review()
    sources = contract.get("sources") if isinstance(contract.get("sources"), list) else []
    counts = {
        classification: sum(row.get("classification") == classification for row in sources)
        for classification in ("historical_approved", "forward_only", "excluded")
    }
    return {
        **contract,
        "schema_version": "qadam_or3_provider_terms_review.v1",
        "artifact_type": "qadam_or3_provider_terms_review",
        "generated_at": now_iso(),
        "source_count": len(sources),
        "classification_counts": counts,
        "legal_advice": False,
        "review_scope": (
            "Operational provider-terms screening for private internal non-commercial research; "
            "not legal advice."
        ),
        "authority": authority_flags(),
    }


def build_source_matrix(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    universe = read_json(runtime / SOURCE_UNIVERSE_ARTIFACT)
    sources = universe.get("sources") if isinstance(universe.get("sources"), list) else []
    capabilities = {str(row.get("source_key")): row for row in read_jsonl(runtime / CAPABILITY_ARTIFACT)}
    review = _provider_terms_review()
    rows = [
        _apply_source_terms_review(
            _source_row(source, capabilities.get(str(source.get("source_key")), {})),
            review,
        )
        for source in sources
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_historical_source_coverage_matrix",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "reviewed" if len(review.get("sources", [])) == len(rows) else "review_incomplete",
        "source_count": len(rows),
        "rows": rows,
        "status_counts": {state: sum(row["status"] == state for row in rows) for state in sorted(ALLOWED_MATRIX_STATES)},
        "purchase_performed_count": 0,
        "terms_accepted_by_automation_count": 0,
        "terms_review_contract_path": str(PROVIDER_TERMS_REVIEW_CONTRACT.relative_to(ROOT)),
        "terms_review_contract_present": bool(review),
        "authority": authority_flags(),
    }


def build_pilot_manifest(settings: Settings | None = None) -> dict[str, Any]:
    jobs = [
        {
            "job_id": "or2r:source:fred:dgs10:2024-01-02_2024-01-10",
            "record_path": "source_event",
            "provider": "fred_public_csv",
            "source_key": "fred",
            "source_category": "macro_trade",
            "dataset": "DGS10",
            "start": "2024-01-02",
            "end": "2024-01-10",
            "pagination": {"mode": "bounded_date_window", "page_size": None, "expected_pages": 1},
        },
        {
            "job_id": "or2r:source:usgs:m6:2024-01-01_2024-01-08",
            "record_path": "source_event",
            "provider": "usgs_earthquake_catalog",
            "source_key": "usgs",
            "source_category": "physical_world",
            "dataset": "earthquakes_magnitude_6_plus",
            "start": "2024-01-01",
            "end": "2024-01-08",
            "pagination": {"mode": "offset", "page_size": 1, "expected_pages": 2},
        },
        *[
            {
                "job_id": f"or2r:price:yahoo:{symbol}:2024-01-01_2024-01-08",
                "record_path": "price_bar",
                "provider": "yahoo_finance_chart_read_only",
                "source_key": "yahoo_finance",
                "source_category": "market_technical",
                "instrument": symbol,
                "market_family": family,
                "start": "2024-01-01",
                "end": "2024-01-08",
                "pagination": {"mode": "bounded_date_window", "page_size": None, "expected_pages": 1},
            }
            for symbol, family in (("USO", "crude_oil"), ("SLV", "silver"))
        ],
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_or3_provider_pilot_manifest",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "ready_for_explicit_read_only_pilot",
        "pilot_window": {"start": "2024-01-01", "end": "2024-01-10"},
        "job_count": len(jobs),
        "jobs": [
            {
                **job,
                "status": "pending",
                "retry_class": "idempotent_read",
                "rate_limit_delay_seconds": 0.25,
                "raw_storage": True,
                "normalized_storage": True,
                "evidence_eligible": False,
                "proof_eligible": False,
                "authority": authority_flags(),
            }
            for job in jobs
        ],
        "network_call_budget": 5,
        "fixture_fallback_allowed": False,
        "research_root": _safe_relative(RESEARCH_ROOT),
        "authority": authority_flags(),
    }


def _request(url: str, *, timeout_seconds: int) -> tuple[bytes, dict[str, Any]]:
    request = Request(url, headers={"User-Agent": "Qadam-OR2R-Research/1.0 read-only"})
    started = time.monotonic()
    with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - allowlisted read-only URLs
        raw = response.read()
        status = int(getattr(response, "status", 200))
        content_type = str(response.headers.get("Content-Type") or "")
    return raw, {
        "http_status": status,
        "content_type": content_type,
        "retrieved_at": now_iso(),
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "url_sha256": hashlib.sha256(url.encode("utf-8")).hexdigest(),
    }


def _parse_fred(raw: bytes, metadata: dict[str, Any], job: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in csv.DictReader(io.StringIO(raw.decode("utf-8"))):
        value = row.get("DGS10")
        if value in {None, "", "."}:
            continue
        observed = f"{row['observation_date']}T00:00:00+00:00"
        rows.append(
            {
                "record_id": f"or2r:fred:DGS10:{row['observation_date']}",
                "record_type": "SourceEvent",
                "origin_class": "provider_historical_pilot",
                "source_key": "fred",
                "event_type": "macro_series_observation",
                "observed_at": observed,
                "available_at": metadata["retrieved_at"],
                "value": float(value),
                "unit": "percent",
                "dataset": job["dataset"],
                "point_in_time_state": "transport_proven_vintage_requires_alfred_for_edge_use",
                "evidence_eligible": False,
                "proof_eligible": False,
            }
        )
    return rows


def _parse_usgs(raw_pages: list[bytes], metadata: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in raw_pages:
        payload = json.loads(raw)
        for feature in payload.get("features", []):
            properties = feature.get("properties") if isinstance(feature.get("properties"), dict) else {}
            event_ms = properties.get("time")
            updated_ms = properties.get("updated")
            if event_ms is None:
                continue
            observed = datetime.fromtimestamp(float(event_ms) / 1000, timezone.utc).isoformat()
            available = (
                datetime.fromtimestamp(float(updated_ms) / 1000, timezone.utc).isoformat()
                if updated_ms is not None
                else metadata["retrieved_at"]
            )
            rows.append(
                {
                    "record_id": f"or2r:usgs:{feature.get('id')}",
                    "record_type": "SourceEvent",
                    "origin_class": "provider_historical_pilot",
                    "source_key": "usgs",
                    "event_type": "earthquake",
                    "observed_at": observed,
                    "available_at": available,
                    "magnitude": properties.get("mag"),
                    "place": properties.get("place"),
                    "point_in_time_state": "provider_event_and_update_times_retained",
                    "evidence_eligible": False,
                    "proof_eligible": False,
                }
            )
    return rows


def _parse_yahoo(raw: bytes, metadata: dict[str, Any], job: dict[str, Any]) -> list[dict[str, Any]]:
    payload = json.loads(raw)
    chart = payload.get("chart") if isinstance(payload.get("chart"), dict) else {}
    if chart.get("error"):
        raise RuntimeError(f"provider_chart_error:{chart['error']}")
    results = chart.get("result") if isinstance(chart.get("result"), list) else []
    if not results:
        return []
    result = results[0]
    timestamps = result.get("timestamp") if isinstance(result.get("timestamp"), list) else []
    quotes = result.get("indicators", {}).get("quote", [])
    quote_row = quotes[0] if quotes and isinstance(quotes[0], dict) else {}
    adjusted_rows = result.get("indicators", {}).get("adjclose", [])
    adjusted = adjusted_rows[0].get("adjclose", []) if adjusted_rows else []
    rows: list[dict[str, Any]] = []
    for index, timestamp in enumerate(timestamps):
        def at(values: Any) -> Any:
            return values[index] if isinstance(values, list) and index < len(values) else None

        observed = datetime.fromtimestamp(int(timestamp), timezone.utc).isoformat()
        rows.append(
            {
                "record_id": f"or2r:yahoo:{job['instrument']}:{int(timestamp)}",
                "record_type": "PriceEvidence",
                "origin_class": "provider_historical_pilot",
                "provider": job["provider"],
                "instrument": job["instrument"],
                "market_family": job["market_family"],
                "interval": "1d",
                "observed_at": observed,
                "available_at": metadata["retrieved_at"],
                "open": at(quote_row.get("open")),
                "high": at(quote_row.get("high")),
                "low": at(quote_row.get("low")),
                "close": at(quote_row.get("close")),
                "adjusted_close": at(adjusted),
                "volume": at(quote_row.get("volume")),
                "point_in_time_state": "transport_proven_historical_release_time_not_edge_certified",
                "evidence_eligible": False,
                "proof_eligible": False,
            }
        )
    return rows


def _job_paths(job: dict[str, Any]) -> tuple[Path, Path, Path]:
    safe_id = str(job["job_id"]).replace(":", "_")
    base = RESEARCH_ROOT / f"provider={job['provider']}" / safe_id
    return base / "raw.json", base / "records.jsonl", base / "metadata.json"


def _resume_metadata(job: dict[str, Any]) -> dict[str, Any] | None:
    raw_path, rows_path, metadata_path = _job_paths(job)
    metadata = read_json(metadata_path)
    if metadata.get("status") != "complete" or metadata.get("job_id") != job.get("job_id"):
        return None
    if not raw_path.is_file() or not rows_path.is_file():
        return None
    if metadata.get("raw_sha256") != _sha256_bytes(raw_path.read_bytes()):
        return None
    if metadata.get("normalized_sha256") != _sha256_bytes(rows_path.read_bytes()):
        return None
    return metadata


def _execute_job(job: dict[str, Any], *, timeout_seconds: int) -> dict[str, Any]:
    resumed = _resume_metadata(job)
    if resumed:
        return {**resumed, "resume_skipped": True, "network_calls_this_attempt": 0}
    raw_path, rows_path, metadata_path = _job_paths(job)
    raw_pages: list[bytes] = []
    page_metadata: list[dict[str, Any]] = []
    provider = job["provider"]
    if provider == "fred_public_csv":
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv?" + urlencode(
            {"id": job["dataset"], "cosd": job["start"], "coed": job["end"]}
        )
        raw, metadata = _request(url, timeout_seconds=timeout_seconds)
        raw_pages.append(raw)
        page_metadata.append(metadata)
        rows = _parse_fred(raw, metadata, job)
    elif provider == "usgs_earthquake_catalog":
        for offset in (1, 2):
            url = "https://earthquake.usgs.gov/fdsnws/event/1/query?" + urlencode(
                {
                    "format": "geojson",
                    "starttime": job["start"],
                    "endtime": job["end"],
                    "minmagnitude": 6,
                    "orderby": "time-asc",
                    "limit": 1,
                    "offset": offset,
                }
            )
            raw, metadata = _request(url, timeout_seconds=timeout_seconds)
            raw_pages.append(raw)
            page_metadata.append(metadata)
            time.sleep(float(job.get("rate_limit_delay_seconds") or 0.0))
        rows = _parse_usgs(raw_pages, page_metadata[-1])
    elif provider == "yahoo_finance_chart_read_only":
        start = int(datetime.fromisoformat(job["start"]).replace(tzinfo=timezone.utc).timestamp())
        end = int(datetime.fromisoformat(job["end"]).replace(tzinfo=timezone.utc).timestamp())
        params = urlencode(
            {
                "period1": start,
                "period2": end,
                "interval": "1d",
                "events": "div,splits",
                "includeAdjustedClose": "true",
            }
        )
        url = f"https://query2.finance.yahoo.com/v8/finance/chart/{quote(job['instrument'])}?{params}"
        raw, metadata = _request(url, timeout_seconds=timeout_seconds)
        raw_pages.append(raw)
        page_metadata.append(metadata)
        rows = _parse_yahoo(raw, metadata, job)
    else:
        raise RuntimeError(f"pilot_provider_not_allowlisted:{provider}")

    unique_rows = {str(row["record_id"]): row for row in rows}
    rows = [
        {
            **row,
            "provider_response_sha256": _sha256_bytes(b"\n".join(raw_pages)),
            "pilot_only": True,
            "trade_candidate_created": False,
            "paper_order_created": False,
            "broker_write_count": 0,
            "proof_credit_created": False,
            "authority": authority_flags(),
        }
        for row in unique_rows.values()
    ]
    raw_bundle = json.dumps(
        {
            "job_id": job["job_id"],
            "pages": [json.loads(page) if page.lstrip().startswith((b"{", b"[")) else page.decode("utf-8") for page in raw_pages],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    normalized = b"".join(
        (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        for row in rows
    )
    _atomic_bytes(raw_path, raw_bundle)
    _atomic_bytes(rows_path, normalized)
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_or3_provider_pilot_partition",
        "generated_at": now_iso(),
        "status": "complete" if rows else "provider_empty",
        "job_id": job["job_id"],
        "provider": provider,
        "source_category": job["source_category"],
        "record_path": job["record_path"],
        "instrument": job.get("instrument"),
        "market_family": job.get("market_family"),
        "page_count": len(raw_pages),
        "pagination_mode": job["pagination"]["mode"],
        "pagination_validated": len(raw_pages) == int(job["pagination"]["expected_pages"]),
        "rate_limit_delay_seconds": float(job.get("rate_limit_delay_seconds") or 0.0),
        "rate_limit_policy_exercised": True,
        "network_calls_this_attempt": len(raw_pages),
        "row_count": len(rows),
        "raw_path": _safe_relative(raw_path),
        "normalized_path": _safe_relative(rows_path),
        "raw_sha256": _sha256_bytes(raw_bundle),
        "normalized_sha256": _sha256_bytes(normalized),
        "page_request_metadata": page_metadata,
        "resume_skipped": False,
        "evidence_eligible": False,
        "proof_eligible": False,
        "authority": authority_flags(),
    }
    write_json_atomic(metadata_path, metadata)
    return metadata


def _pilot_error(exc: Exception) -> tuple[str, str]:
    if isinstance(exc, HTTPError) and exc.code == 429:
        return "provider_rate_limited", f"HTTPError:{exc.code}"
    if isinstance(exc, HTTPError):
        return "provider_http_error", f"HTTPError:{exc.code}"
    if isinstance(exc, URLError):
        return "provider_network_error", f"URLError:{exc.reason}"
    return "provider_or_parser_error", f"{exc.__class__.__name__}:{exc}"


def _projection(
    pilot_rows: list[dict[str, Any]],
    purchase_matrix: dict[str, Any],
    source_matrix: dict[str, Any],
    runtime: Path,
) -> dict[str, Any]:
    measured_calls = sum(int(row.get("network_calls_this_attempt") or 0) for row in pilot_rows)
    measured_seconds = sum(
        sum(float(page.get("elapsed_seconds") or 0.0) for page in row.get("page_request_metadata", []))
        for row in pilot_rows
    )
    measured_rows = sum(int(row.get("row_count") or 0) for row in pilot_rows)
    measured_bytes = sum(
        (ROOT / str(row["raw_path"])).stat().st_size + (ROOT / str(row["normalized_path"])).stat().st_size
        for row in pilot_rows
        if row.get("raw_path") and row.get("normalized_path")
    )
    source_manifest = read_json(runtime / BACKFILL_SOURCE_MANIFEST)
    price_manifest = read_json(runtime / BACKFILL_PRICE_MANIFEST)
    planned_calls = int(source_manifest.get("job_count") or 0) + int(price_manifest.get("job_count") or 0)
    if planned_calls <= 0:
        planned_calls = 450
    estimated_rows = sum(int(row.get("estimated_rows") or 0) for row in purchase_matrix.get("rows", []))
    estimated_rows += sum(int(row.get("estimated_rows") or 0) for row in source_matrix.get("rows", []))
    bytes_per_row = measured_bytes / max(measured_rows, 1)
    projected_bytes = int(bytes_per_row * max(estimated_rows, 1) * 2.0)
    available_bytes = shutil.disk_usage(RESEARCH_ROOT.parent).free
    measured_seconds_per_call = measured_seconds / max(measured_calls, 1)
    # Tiny public samples understate authentication, pagination, retries, and
    # provider-specific pacing. Keep a deliberately conservative floor.
    projected_hours = max(
        planned_calls * max(measured_seconds_per_call, 0.25) * 8.0 / 3600,
        12.0,
    )
    return {
        "measured_provider_call_count": measured_calls,
        "measured_row_count": measured_rows,
        "measured_bytes": measured_bytes,
        "measured_seconds": round(measured_seconds, 4),
        "planned_full_run_call_count": planned_calls,
        "estimated_full_run_row_count": estimated_rows,
        "projected_full_run_storage_bytes": projected_bytes,
        "projected_full_run_storage_gb": round(projected_bytes / (1024**3), 3),
        "available_disk_gb": round(available_bytes / (1024**3), 3),
        "disk_budget_fit": projected_bytes < max(0, available_bytes - 20 * 1024**3),
        "projected_full_run_duration_hours": {
            "base": round(projected_hours, 2),
            "high": round(projected_hours * 6, 2),
        },
        "five_day_window_fit": projected_hours * 6 <= 120,
        "projected_full_run_cost_usd": None,
        "cost_budget_fit": False,
        "cost_state": "operator_provider_selection_and_budget_required",
        "paper_account_starting_capital_usd": PAPER_ACCOUNT_STARTING_CAPITAL_USD,
        "paper_capital_available_for_data_purchases": False,
        "projection_confidence": "low_until_provider_selection_and_larger_pilot",
    }


def run_provider_pilot(
    manifest: dict[str, Any],
    purchase_matrix: dict[str, Any],
    source_matrix: dict[str, Any],
    settings: Settings | None = None,
    *,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    results: list[dict[str, Any]] = []
    for job in manifest.get("jobs", []):
        started_at = now_iso()
        try:
            result = _execute_job(job, timeout_seconds=timeout_seconds)
            results.append({**result, "started_at": started_at})
        except Exception as exc:  # noqa: BLE001 - provider errors remain typed and non-destructive
            category, message = _pilot_error(exc)
            results.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "status": "failed",
                    "job_id": job.get("job_id"),
                    "provider": job.get("provider"),
                    "source_category": job.get("source_category"),
                    "record_path": job.get("record_path"),
                    "instrument": job.get("instrument"),
                    "market_family": job.get("market_family"),
                    "failure_category": category,
                    "error": message[:400],
                    "started_at": started_at,
                    "completed_at": now_iso(),
                    "network_calls_this_attempt": 0,
                    "row_count": 0,
                    "authority": authority_flags(),
                }
            )
        time.sleep(float(job.get("rate_limit_delay_seconds") or 0.0))

    # A second pass must resolve entirely from checksummed partitions.
    resume_results = [
        _execute_job(job, timeout_seconds=timeout_seconds)
        for job in manifest.get("jobs", [])
        if any(row.get("job_id") == job.get("job_id") and row.get("status") == "complete" for row in results)
    ]
    completed = [row for row in results if row.get("status") == "complete"]
    record_ids: list[str] = []
    for row in completed:
        path = ROOT / str(row["normalized_path"])
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record_ids.append(str(json.loads(line).get("record_id")))
    timestamp_errors: list[str] = []
    for row in completed:
        path = ROOT / str(row["normalized_path"])
        for line in path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            try:
                observed = datetime.fromisoformat(str(record["observed_at"]).replace("Z", "+00:00"))
                available = datetime.fromisoformat(str(record["available_at"]).replace("Z", "+00:00"))
            except (KeyError, ValueError):
                timestamp_errors.append(f"timestamp_invalid:{record.get('record_id')}")
                continue
            if observed > available:
                timestamp_errors.append(f"observed_after_available:{record.get('record_id')}")
    projection = _projection(completed, purchase_matrix, source_matrix, runtime)
    source_categories = sorted({str(row.get("source_category")) for row in completed if row.get("record_path") == "source_event"})
    market_families = sorted({str(row.get("market_family")) for row in completed if row.get("record_path") == "price_bar"})
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_or3_provider_pilot_results",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if len(completed) == int(manifest.get("job_count") or 0) else "blocked",
        "real_provider_backed": bool(completed),
        "fixture_fallback_used": False,
        "job_count": int(manifest.get("job_count") or 0),
        "completed_job_count": len(completed),
        "failed_job_count": len(results) - len(completed),
        "source_event_job_count": sum(row.get("record_path") == "source_event" for row in completed),
        "price_bar_job_count": sum(row.get("record_path") == "price_bar" for row in completed),
        "source_categories": source_categories,
        "market_families": market_families,
        "provider_row_count": sum(int(row.get("row_count") or 0) for row in completed),
        "results": results,
        "provenance_complete": all(
            row.get("raw_sha256") and row.get("normalized_sha256") and row.get("page_request_metadata")
            for row in completed
        ),
        "timestamp_validation_passed": not timestamp_errors,
        "timestamp_errors": timestamp_errors,
        "point_in_time_safety": {
            "status": "passed_for_non_eligible_transport_pilot" if not timestamp_errors else "blocked",
            "pilot_rows_evidence_eligible": False,
            "pilot_rows_proof_eligible": False,
            "historical_vintage_certification_complete": False,
            "future_data_credit_count": 0,
        },
        "checksums_validated": all(_resume_metadata(job) is not None for job in manifest.get("jobs", [])),
        "pagination_validated": all(row.get("pagination_validated") is True for row in completed),
        "rate_limit_policy_validated": all(row.get("rate_limit_policy_exercised") is True for row in completed),
        "atomic_write_validated": all(not list((ROOT / str(row["raw_path"])).parent.glob("*.part")) for row in completed),
        "resume_validation": {
            "second_pass_job_count": len(resume_results),
            "second_pass_network_call_count": sum(int(row.get("network_calls_this_attempt") or 0) for row in resume_results),
            "second_pass_logical_write_count": sum(not row.get("resume_skipped") for row in resume_results),
            "interruption_safe_resume_passed": bool(resume_results)
            and all(row.get("resume_skipped") is True for row in resume_results),
        },
        "deduplication": {
            "logical_record_count": len(record_ids),
            "unique_record_count": len(set(record_ids)),
            "duplicate_logical_record_count": len(record_ids) - len(set(record_ids)),
        },
        "projection": projection,
        "paper_trial_calendar_advanced": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "authority": authority_flags(),
    }


def _operator_actions(
    purchase: dict[str, Any],
    sources: dict[str, Any],
    pilot: dict[str, Any],
    approval: dict[str, Any],
    *,
    cost_budget_fit: bool,
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    price_rows = purchase.get("rows") if isinstance(purchase.get("rows"), list) else []
    source_rows = sources.get("rows") if isinstance(sources.get("rows"), list) else []
    blocked_price_symbols = [
        str(row.get("symbol"))
        for row in price_rows
        if row.get("status") == "blocked_purchase_review"
    ]
    if blocked_price_symbols:
        actions.append(
            {
                "action_id": "complete_databento_quote_and_download_authorization",
                "required": True,
                "owner": "operator",
                "action": (
                    "Set a Databento historical monthly limit, obtain the definitive GLBX.MDP3 "
                    "OHLCV-1d quote for CL.FUT and SI.FUT, record it, then explicitly authorize "
                    "the bounded download."
                ),
                "affected_instruments": blocked_price_symbols,
                "automation_may_purchase": False,
                "automation_may_accept_terms": False,
            }
        )
    blocked_sources = [row["source_key"] for row in source_rows if row.get("status") in {"blocked_credentials", "blocked_purchase_review", "unsupported_history", "proxy_proposed"}]
    if blocked_sources:
        actions.append(
            {
                "action_id": "review_historical_source_scope",
                "required": True,
                "owner": "operator",
                "action": "Approve, exclude, or classify the remaining historical source interfaces before bulk acquisition.",
                "affected_source_count": len(blocked_sources),
                "affected_sources": blocked_sources,
                "automation_may_edit_secrets": False,
            }
        )
    if not cost_budget_fit:
        actions.append(
            {
                "action_id": "set_full_run_data_budget",
                "required": True,
                "owner": "operator",
                "action": (
                    "Set a separate historical-data acquisition budget after the definitive "
                    "Databento quote is known. The US$5,000 paper-trade preference is not this budget."
                ),
                "automation_may_purchase": False,
            }
        )
    if approval.get("databento", {}).get("historical_monthly_limit_usd") is None:
        actions.append(
            {
                "action_id": "set_databento_historical_monthly_limit",
                "required": True,
                "owner": "operator",
                "action": (
                    "Replace Databento's Unlimited usage state with a hard historical monthly "
                    "limit before requesting data."
                ),
                "automation_may_purchase": False,
            }
        )
    return actions


def build_readiness(
    connection: dict[str, Any],
    tradingview: dict[str, Any],
    purchase: dict[str, Any],
    sources: dict[str, Any],
    manifest: dict[str, Any],
    pilot: dict[str, Any],
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    approval = _operator_approval()
    terms_review = _provider_terms_review()
    _lock, lock_errors = _lock_state(runtime)
    errors: list[str] = list(lock_errors)
    if connection.get("status") != "truthful":
        errors.append("connection_truth_invalid")
    if tradingview.get("connection_state") not in TRADINGVIEW_MCP_CONNECTION_STATES:
        errors.append("tradingview_state_invalid")
    if tradingview.get("truthful_state") is not True:
        errors.append("tradingview_state_not_truthful")
    if int(purchase.get("instrument_count") or 0) != 19:
        errors.append("purchase_matrix_not_19_instruments")
    if int(sources.get("source_count") or 0) != 41:
        errors.append("source_matrix_not_41_sources")
    if len(terms_review.get("sources", [])) != 41:
        errors.append("provider_terms_review_not_41_sources")
    if approval.get("private_internal_research") is not True:
        errors.append("operator_private_internal_research_not_confirmed")
    if approval.get("redistribution_allowed") is not False:
        errors.append("operator_redistribution_boundary_unsafe")
    if approval.get("paper_capital_available_for_data_purchases") is not False:
        errors.append("paper_capital_misclassified_for_data_purchase")
    for matrix_name, matrix in (("purchase", purchase), ("source", sources)):
        for row in matrix.get("rows", []):
            if row.get("status") not in ALLOWED_MATRIX_STATES:
                errors.append(f"{matrix_name}_matrix_status_invalid:{row.get('status')}")
            if row.get("system_review_complete") is not True:
                errors.append(f"{matrix_name}_matrix_row_unreviewed:{row.get('matrix_row_id')}")
            if row.get("terms_accepted_by_automation") is not False:
                errors.append(f"{matrix_name}_matrix_terms_autoaccepted:{row.get('matrix_row_id')}")
            errors.extend(validate_authority(row.get("authority", {}), prefix=f"{matrix_name}_matrix"))
    if pilot.get("status") != "passed":
        errors.append("provider_pilot_not_passed")
    for field in (
        "real_provider_backed",
        "provenance_complete",
        "timestamp_validation_passed",
        "checksums_validated",
        "pagination_validated",
        "rate_limit_policy_validated",
        "atomic_write_validated",
    ):
        if pilot.get(field) is not True:
            errors.append(f"provider_pilot_{field}_false")
    if len(pilot.get("source_categories", [])) < 2:
        errors.append("provider_pilot_source_category_coverage_insufficient")
    if len(pilot.get("market_families", [])) < 2:
        errors.append("provider_pilot_market_family_coverage_insufficient")
    if int(pilot.get("source_event_job_count") or 0) < 2 or int(pilot.get("price_bar_job_count") or 0) < 2:
        errors.append("provider_pilot_path_coverage_insufficient")
    if pilot.get("resume_validation", {}).get("second_pass_logical_write_count") != 0:
        errors.append("provider_pilot_resume_duplicate_write")
    if pilot.get("deduplication", {}).get("duplicate_logical_record_count") != 0:
        errors.append("provider_pilot_duplicate_record")
    if pilot.get("fixture_fallback_used") is not False:
        errors.append("provider_pilot_fixture_fallback_used")
    if pilot.get("point_in_time_safety", {}).get("pilot_rows_evidence_eligible") is not False:
        errors.append("provider_pilot_rows_miscredited_as_evidence")
    if pilot.get("paper_trial_calendar_advanced") is not False:
        errors.append("provider_pilot_advanced_paper_calendar")
    errors.extend(validate_authority(pilot.get("authority", {}), prefix="provider_pilot"))
    errors = unique_errors(errors)
    blocking_matrix_rows = sum(
        row.get("operator_approval_complete") is not True
        for matrix in (purchase, sources)
        for row in matrix.get("rows", [])
        if row.get("status") not in {"forward_only", "excluded"}
    )
    databento = approval.get("databento", {}) if isinstance(approval.get("databento"), dict) else {}
    quote = databento.get("definitive_quote_usd")
    purchase_budget = approval.get("historical_data_purchase_budget_usd")
    monthly_limit = databento.get("historical_monthly_limit_usd")
    cost_budget_fit = (
        isinstance(quote, (int, float))
        and isinstance(purchase_budget, (int, float))
        and isinstance(monthly_limit, (int, float))
        and quote <= monthly_limit <= purchase_budget
        and databento.get("download_authorized") is True
    )
    projection = {
        **pilot.get("projection", {}),
        "projected_full_run_cost_usd": quote,
        "historical_data_purchase_budget_usd": purchase_budget,
        "databento_historical_monthly_limit_usd": monthly_limit,
        "cost_budget_fit": cost_budget_fit,
        "cost_state": (
            "quoted_capped_and_authorized"
            if cost_budget_fit
            else "databento_quote_monthly_limit_budget_and_authorization_required"
        ),
    }
    actions = _operator_actions(
        purchase,
        sources,
        {**pilot, "projection": projection},
        approval,
        cost_budget_fit=cost_budget_fit,
    )
    budget_ready = (
        pilot.get("projection", {}).get("disk_budget_fit") is True
        and pilot.get("projection", {}).get("five_day_window_fit") is True
        and cost_budget_fit
    )
    or3_start_allowed = not errors and not actions and blocking_matrix_rows == 0 and budget_ready
    readiness = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_or3_acquisition_readiness",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "ready" if or3_start_allowed else ("blocked" if errors else "blocked_operator_action"),
        "implementation_ready": not errors,
        "or3_start_allowed": or3_start_allowed,
        "connection_truth_passed": connection.get("status") == "truthful",
        "tradingview_connection_state": tradingview.get("connection_state"),
        "tradingview_required_for_or3": False,
        "instrument_count": purchase.get("instrument_count"),
        "source_count": sources.get("source_count"),
        "pilot_status": pilot.get("status"),
        "pilot_provider_row_count": pilot.get("provider_row_count"),
        "blocking_matrix_row_count": blocking_matrix_rows,
        "operator_action_count": len(actions),
        "operator_actions": actions,
        "projected_full_run": projection,
        "projected_budget_ready": budget_ready,
        "paper_account": {
            "starting_capital": PAPER_ACCOUNT_STARTING_CAPITAL_USD,
            "currency": "USD",
            "capital_type": "paper_only",
            "available_for_provider_purchases": False,
        },
        "historical_data_purchase_budget_usd": purchase_budget,
        "operator_approval_contract": str(OPERATOR_APPROVAL_CONTRACT.relative_to(ROOT)),
        "provider_terms_review_contract": str(PROVIDER_TERMS_REVIEW_CONTRACT.relative_to(ROOT)),
        "current_use_case": approval.get("current_use_case"),
        "redistribution_allowed": False,
        "future_commercial_relicense_required": approval.get(
            "future_commercial_relicense_required"
        )
        is True,
        "paper_trade_max_notional_operator_preference_usd": approval.get(
            "paper_trade_max_notional_operator_preference_usd"
        ),
        "paper_trade_preference_applied_to_risk_policy": approval.get(
            "paper_trade_max_notional_applied_to_risk_policy"
        )
        is True,
        "prediction_market_access": approval.get("prediction_market_access", {}),
        "research_lock_active": True,
        "paperops_watch_only_mode": True,
        "fixture_only_acceptance_allowed": False,
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "paper_trial_calendar_advanced": False,
        "trade_candidate_created_count": 0,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "source_artifacts": {
            "connection_truth": f"data/runtime/{CONNECTION_TRUTH_ARTIFACT}",
            "tradingview": f"data/runtime/{TRADINGVIEW_STATUS_ARTIFACT}",
            "purchase_matrix": f"data/runtime/{PURCHASE_MATRIX_ARTIFACT}",
            "source_matrix": f"data/runtime/{SOURCE_MATRIX_ARTIFACT}",
            "provider_terms_review": f"data/runtime/{TERMS_REVIEW_ARTIFACT}",
            "pilot_manifest": f"data/runtime/{PILOT_MANIFEST_ARTIFACT}",
            "pilot_results": f"data/runtime/{PILOT_RESULTS_ARTIFACT}",
        },
        "authority": authority_flags(),
    }
    return readiness, errors


def build_and_write_or3_acquisition_readiness(
    settings: Settings | None = None,
    *,
    run_pilot: bool = False,
    timeout_seconds: int = 30,
) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    connection, tradingview = build_connection_truth(settings)
    purchase = build_purchase_matrix(settings)
    sources = build_source_matrix(settings)
    terms_review = build_provider_terms_review(settings)
    manifest = build_pilot_manifest(settings)
    existing_pilot = read_json(runtime / PILOT_RESULTS_ARTIFACT)
    pilot = (
        run_provider_pilot(
            manifest,
            purchase,
            sources,
            settings,
            timeout_seconds=timeout_seconds,
        )
        if run_pilot
        else existing_pilot
    )
    if not pilot:
        pilot = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_or3_provider_pilot_results",
            "phase_id": PHASE_ID,
            "generated_at": now_iso(),
            "status": "not_run",
            "real_provider_backed": False,
            "fixture_fallback_used": False,
            "results": [],
            "authority": authority_flags(),
        }
    store.write_json(CONNECTION_TRUTH_ARTIFACT, connection)
    store.write_json(TRADINGVIEW_STATUS_ARTIFACT, tradingview)
    store.write_json(PURCHASE_MATRIX_ARTIFACT, purchase)
    store.write_json(SOURCE_MATRIX_ARTIFACT, sources)
    store.write_json(TERMS_REVIEW_ARTIFACT, terms_review)
    store.write_json(PILOT_MANIFEST_ARTIFACT, manifest)
    store.write_json(PILOT_RESULTS_ARTIFACT, pilot)
    readiness, errors = build_readiness(
        connection,
        tradingview,
        purchase,
        sources,
        manifest,
        pilot,
        settings,
    )
    store.write_json(READINESS_ARTIFACT, readiness)
    return readiness, errors
