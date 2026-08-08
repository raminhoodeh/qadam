"""EF-1 strategy-aware source, instrument, and execution-proxy truth.

The contract reconciles current provider state, historical coverage, frozen
strategy recipes, and locally proven guarded Alpaca Paper routes.  It never
creates an order or turns research-only symbols into broker symbols.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    runtime_dir,
    sha256_json,
    unique_errors,
    validate_authority,
)

SCHEMA_VERSION = "qadam_universe_contract.v1"
PHASE_ID = "EF-1"

SOURCE_CONTRACT_ARTIFACT = "qadam_strategy_source_contract.json"
INSTRUMENT_REGISTRY_ARTIFACT = "qadam_instrument_role_registry.json"
PROXY_REGISTRY_ARTIFACT = "qadam_execution_proxy_registry.json"
FRESHNESS_SLA_ARTIFACT = "qadam_source_freshness_sla.json"
CHECK_ARTIFACT = "qadam_universe_contract_checks.json"

CURRENT_SOURCE_ARTIFACT = "qsase_source_universe.json"
CURRENT_INSTRUMENT_ARTIFACT = "qsase_trading_universe.json"
HISTORICAL_SOURCE_ARTIFACT = "qadam_historical_source_coverage_matrix.json"
STRATEGY_MAP_ARTIFACT = "qadam_strategy_evidence_map_v3.json"
SUBMISSION_LEDGER_ARTIFACT = "paperops_alpaca_paper_post_submission_ledger.json"
BACKTEST_COVERAGE_ARTIFACT = "qadam_backtest_completion_coverage.json"

SOURCE_STATES = {
    "live_fresh",
    "historical_only",
    "forward_only",
    "supplemental_current",
    "temporarily_degraded",
    "unavailable",
    "excluded",
}
SOURCE_ROLES = {
    "historical_causal_support",
    "current_trigger",
    "market_confirmation",
    "supplemental_context",
    "negative_control",
}
INSTRUMENT_ROLES = {
    "direct_paper_instrument",
    "approved_execution_proxy",
    "research_price_context",
    "prediction_contract_context",
    "emerging_sleeve_instrument",
}
HISTORICALLY_SCORED_SOURCES = {
    "kalshi",
    "polymarket",
    "sec_edgar",
    "stock_act",
    "usgs",
}
SUPPLEMENTAL_KEYS = {
    "alpaca",
    "bookmap",
    "tradingview_mcp",
    "tradingview_paid_alerts",
    "yahoo_finance",
    "yahoo_finance_or_tradingview",
}
MARKET_CONFIRMATION_KEYS = {
    "alpaca",
    "bookmap",
    "coinglass",
    "hyperliquid",
    "tradingview_mcp",
    "tradingview_paid_alerts",
    "unusual_whales",
    "yahoo_finance",
    "yahoo_finance_or_tradingview",
}
SOURCE_ALIASES = {"sec": "sec_edgar", "ais_or_shipping": "ais_maritime"}


def _normalise_source(value: Any) -> str:
    key = str(value or "").strip().lower()
    return SOURCE_ALIASES.get(key, key)


def _freshness_sla(source: dict[str, Any]) -> dict[str, Any]:
    original_key = str(source.get("source_key") or "").strip().lower()
    key = _normalise_source(original_key)
    family = str(source.get("source_family") or "").lower()
    if key in {"alpaca", "bookmap", "tradingview_mcp", "unusual_whales"}:
        seconds = 300
    elif key in {"telegram", "rss", "reddit", "twitter_x", "social.rss"}:
        seconds = 1800
    elif any(token in family for token in ("macro", "filing", "trade", "statistics")):
        seconds = 86_400
    elif any(token in family for token in ("physical", "geopolit", "conflict")):
        seconds = 3_600
    else:
        seconds = 21_600
    return {
        "source_key": original_key,
        "canonical_source_key": key,
        "maximum_age_seconds": seconds,
        "session_aware": key in MARKET_CONFIRMATION_KEYS,
        "stale_state": "cannot_satisfy_current_trigger",
        "unknown_age_state": "not_current_evidence",
    }


def _historical_state(row: dict[str, Any]) -> str:
    status = str(row.get("status") or "").lower()
    if row.get("evidence_eligible_from_pilot") is True or status in {
        "provider_backed_acquired",
        "acquired",
        "complete",
    }:
        return "provider_backed_acquired"
    if row.get("forward_only") is True or status == "forward_only":
        return "forward_only"
    if status in {"excluded", "terminally_unavailable", "unavailable"}:
        return status
    return status or "unknown"


def _current_source_state(source: dict[str, Any], historical: dict[str, Any]) -> str:
    freshness = str(source.get("freshness_status") or "").lower()
    adapter = str(source.get("adapter_status") or source.get("state") or "").lower()
    provider_backed = source.get("provider_backed_observation") is True
    supplemental = (
        source.get("supplemental_context_only") is True
        or _normalise_source(source.get("source_key")) in SUPPLEMENTAL_KEYS
    )
    fixture = source.get("sample_fixture") is True
    historical_state = _historical_state(historical)
    if fixture:
        return "excluded"
    if freshness == "fresh" and provider_backed:
        return "supplemental_current" if supplemental else "live_fresh"
    if any(token in adapter for token in ("degraded", "error", "failed", "offline")):
        return "temporarily_degraded"
    if historical_state == "provider_backed_acquired":
        return "historical_only"
    if historical_state == "forward_only":
        return "forward_only"
    if historical_state in {"excluded", "terminally_unavailable"}:
        return "excluded"
    if supplemental and any(token in adapter for token in ("online", "live", "ok")):
        return "supplemental_current"
    return "unavailable"


def _strategy_recipes(
    strategy_map: dict[str, Any],
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    by_source: dict[str, set[str]] = defaultdict(set)
    by_instrument: dict[str, set[str]] = defaultdict(set)
    for strategy in strategy_map.get("strategies", []):
        if not isinstance(strategy, dict):
            continue
        strategy_id = str(strategy.get("strategy_family_id") or "")
        contribution = strategy.get("source_contribution")
        contribution = contribution if isinstance(contribution, dict) else {}
        for source_key in contribution.get("configured_sources", []):
            by_source[_normalise_source(source_key)].add(strategy_id)
        instruments = strategy.get("instrument_contribution")
        instruments = instruments if isinstance(instruments, dict) else {}
        for row in instruments.get("instruments", []):
            if isinstance(row, dict) and row.get("symbol"):
                by_instrument[str(row["symbol"]).upper()].add(strategy_id)
    return by_source, by_instrument


def _proven_routes(ledger: dict[str, Any]) -> dict[str, list[str]]:
    proofs: dict[str, list[str]] = defaultdict(list)
    for row in ledger.get("submission_records", []):
        if not isinstance(row, dict) or row.get("alpaca_paper_post_succeeded") is not True:
            continue
        symbol = str(
            row.get("symbol") or row.get("request_preview", {}).get("symbol") or ""
        ).upper()
        if symbol:
            proofs[symbol].append(str(row.get("recorded_at") or row.get("submitted_at") or ""))
    return dict(proofs)


def build_universe_contract_from_inputs(
    source_universe: dict[str, Any],
    trading_universe: dict[str, Any],
    historical_matrix: dict[str, Any],
    strategy_map: dict[str, Any],
    submission_ledger: dict[str, Any],
    backtest_coverage: dict[str, Any],
    *,
    generated_at: str,
) -> dict[str, Any]:
    history_by_source = {
        _normalise_source(row.get("source_key")): row
        for row in historical_matrix.get("rows", [])
        if isinstance(row, dict) and row.get("source_key")
    }
    strategies_by_source, strategies_by_instrument = _strategy_recipes(strategy_map)
    route_proofs = _proven_routes(submission_ledger)

    source_rows: list[dict[str, Any]] = []
    sla_rows: list[dict[str, Any]] = []
    for source in source_universe.get("sources", []):
        if not isinstance(source, dict) or not source.get("source_key"):
            continue
        original_key = str(source.get("source_key") or "").strip().lower()
        key = _normalise_source(original_key)
        history = history_by_source.get(key, {})
        state = _current_source_state(source, history)
        roles: set[str] = {"supplemental_context"}
        strategy_ids = sorted(strategies_by_source.get(key, set()))
        if key in HISTORICALLY_SCORED_SOURCES:
            roles.add("historical_causal_support")
        if (
            state == "live_fresh"
            and strategy_ids
            and source.get("eligible_for_signal_review") is True
        ):
            roles.add("current_trigger")
        if key in MARKET_CONFIRMATION_KEYS and state in {"live_fresh", "supplemental_current"}:
            roles.add("market_confirmation")
        if key in {"github", "reddit", "social.rss"}:
            roles.add("negative_control")
        sla = _freshness_sla(source)
        sla_rows.append(sla)
        source_rows.append(
            {
                "source_key": original_key,
                "canonical_source_key": key,
                "alias_of": key if original_key != key else None,
                "source_name": source.get("source_name") or original_key,
                "source_family": source.get("source_family"),
                "availability_state": state,
                "allowed_roles": sorted(roles),
                "strategy_family_ids": strategy_ids,
                "historical_state": _historical_state(history),
                "historical_causal_support": key in HISTORICALLY_SCORED_SOURCES,
                "current_trigger_eligible": "current_trigger" in roles,
                "current_trigger_active": False,
                "freshness_status": source.get("freshness_status"),
                "observed_at": source.get("observed_timestamp")
                or source.get("provider_event_latest_at"),
                "available_at": source.get("latest_health_check_at"),
                "provider_backed": source.get("provider_backed_observation") is True,
                "sample_or_fixture": source.get("sample_fixture") is True,
                "trust_score": source.get("trust_score"),
                "freshness_sla_seconds": sla["maximum_age_seconds"],
                "supplemental_cannot_claim_causal_quorum": source.get("supplemental_context_only")
                is True,
                "trade_candidate_creation_allowed": False,
                "authority": authority_flags(),
            }
        )

    instrument_rows: list[dict[str, Any]] = []
    for instrument in trading_universe.get("instruments", []):
        if not isinstance(instrument, dict) or not instrument.get("symbol"):
            continue
        symbol = str(instrument["symbol"]).upper()
        legacy_route = instrument.get("paper_route_available") is True
        local_route_proof = bool(route_proofs.get(symbol))
        route_confirmed = legacy_route or local_route_proof
        if symbol in {"KALSHI:EVENTS", "POLYMARKET:EVENTS"}:
            role = "prediction_contract_context"
            route_state = "context_only_never_alpaca_symbol"
            route_confirmed = False
        elif symbol in {"CL=F", "SI=F"}:
            role = "research_price_context"
            route_state = "research_only_no_paper_futures_route"
            route_confirmed = False
        elif route_confirmed:
            role = "direct_paper_instrument"
            route_state = "guarded_alpaca_paper_confirmed"
        else:
            role = "research_price_context"
            route_state = "guarded_paper_route_unverified"
        instrument_rows.append(
            {
                "symbol": symbol,
                "display_name": instrument.get("display_name") or symbol,
                "market_family": instrument.get("market_family"),
                "observation_role": role,
                "route_state": route_state,
                "guarded_paper_route_confirmed": route_confirmed,
                "route_proof": (
                    {
                        "type": "sanitized_alpaca_paper_submission_ledger",
                        "artifact": SUBMISSION_LEDGER_ARTIFACT,
                        "timestamps": route_proofs.get(symbol, []),
                    }
                    if local_route_proof
                    else {
                        "type": "legacy_frozen_universe_contract" if legacy_route else "none",
                        "artifact": CURRENT_INSTRUMENT_ARTIFACT,
                    }
                ),
                "strategy_family_ids": sorted(strategies_by_instrument.get(symbol, set())),
                "historical_state": (
                    "provider_backed_history_available"
                    if backtest_coverage.get("status") == "complete"
                    and instrument.get("backtest_gap_reason") in {None, "none", ""}
                    else instrument.get("backtest_gap_reason")
                    or "explicitly_unavailable_or_unverified"
                ),
                "paper_order_allowed": False,
                "broker_write_allowed": False,
                "live_capital_enabled": False,
                "authority": authority_flags(),
            }
        )

    registry_by_symbol = {row["symbol"]: row for row in instrument_rows}
    proxy_rows: list[dict[str, Any]] = []
    preferred = {
        "CL=F": ["BNO", "XLE", "USO"],
        "SI=F": ["SIL", "SLV", "GLD"],
    }
    for instrument in instrument_rows:
        symbol = instrument["symbol"]
        candidates = preferred.get(symbol, [symbol])
        approved = [
            candidate
            for candidate in candidates
            if registry_by_symbol.get(candidate, {}).get("guarded_paper_route_confirmed") is True
        ]
        proxy_rows.append(
            {
                "research_symbol": symbol,
                "research_role": instrument["observation_role"],
                "approved_paper_proxies": approved,
                "preferred_proxy": approved[0] if approved else None,
                "basis_risk_state": (
                    "direct"
                    if approved == [symbol]
                    else "proxy_basis_review_required"
                    if approved
                    else "no_approved_proxy"
                ),
                "context_symbol_may_be_sent_to_alpaca": False,
                "paper_order_allowed": False,
                "authority": authority_flags(),
            }
        )

    source_contract = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_strategy_source_contract",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "complete",
        "source_count": len(source_rows),
        "availability_counts": dict(
            sorted(Counter(row["availability_state"] for row in source_rows).items())
        ),
        "role_counts": dict(
            sorted(Counter(role for row in source_rows for role in row["allowed_roles"]).items())
        ),
        "historically_scored_source_keys": sorted(HISTORICALLY_SCORED_SOURCES),
        "sources": source_rows,
        "contract_hash": sha256_json(source_rows),
        "authority": authority_flags(),
    }
    instrument_registry = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_instrument_role_registry",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "complete",
        "instrument_count": len(instrument_rows),
        "role_counts": dict(
            sorted(Counter(row["observation_role"] for row in instrument_rows).items())
        ),
        "guarded_route_count": sum(row["guarded_paper_route_confirmed"] for row in instrument_rows),
        "instruments": instrument_rows,
        "contract_hash": sha256_json(instrument_rows),
        "authority": authority_flags(),
    }
    proxy_registry = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_execution_proxy_registry",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "complete",
        "mapping_count": len(proxy_rows),
        "mappings": proxy_rows,
        "authority": authority_flags(),
    }
    freshness = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_source_freshness_sla",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "complete",
        "source_count": len(sla_rows),
        "sources": sla_rows,
        "authority": authority_flags(),
    }
    return {
        "source_contract": source_contract,
        "instrument_registry": instrument_registry,
        "proxy_registry": proxy_registry,
        "freshness": freshness,
    }


def validate_universe_contract(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    sources = state.get("source_contract", {}).get("sources", [])
    instruments = state.get("instrument_registry", {}).get("instruments", [])
    proxies = state.get("proxy_registry", {}).get("mappings", [])
    if len(sources) != 41:
        errors.append("universe_source_count_not_41")
    if len(instruments) != 19:
        errors.append("universe_instrument_count_not_19")
    if len({row.get("source_key") for row in sources}) != len(sources):
        errors.append("universe_source_key_missing_or_duplicate")
    if len({row.get("symbol") for row in instruments}) != len(instruments):
        errors.append("universe_instrument_symbol_missing_or_duplicate")
    for row in sources:
        if row.get("availability_state") not in SOURCE_STATES:
            errors.append(f"source_state_invalid:{row.get('source_key')}")
        roles = set(row.get("allowed_roles") or [])
        if not roles or not roles.issubset(SOURCE_ROLES):
            errors.append(f"source_roles_invalid:{row.get('source_key')}")
        if (
            row.get("availability_state") not in {"live_fresh", "supplemental_current"}
            and row.get("current_trigger_active") is True
        ):
            errors.append(f"unavailable_source_claimed_trigger:{row.get('source_key')}")
        if row.get("sample_or_fixture") is True and row.get("current_trigger_eligible") is True:
            errors.append(f"fixture_source_trigger_eligible:{row.get('source_key')}")
        errors.extend(validate_authority(row.get("authority", {}), prefix="source_contract"))
    for row in instruments:
        symbol = row.get("symbol")
        if row.get("observation_role") not in INSTRUMENT_ROLES:
            errors.append(f"instrument_role_invalid:{symbol}")
        if (
            symbol in {"CL=F", "SI=F", "KALSHI:EVENTS", "POLYMARKET:EVENTS"}
            and row.get("guarded_paper_route_confirmed") is True
        ):
            errors.append(f"context_symbol_has_guarded_alpaca_route:{symbol}")
        errors.extend(validate_authority(row.get("authority", {}), prefix="instrument_registry"))
    if len(proxies) != len(instruments):
        errors.append("proxy_registry_does_not_cover_instrument_universe")
    for row in proxies:
        if row.get("context_symbol_may_be_sent_to_alpaca") is not False:
            errors.append(
                f"proxy_mapping_grants_context_order_authority:{row.get('research_symbol')}"
            )
        errors.extend(validate_authority(row.get("authority", {}), prefix="proxy_registry"))
    for payload, prefix in (
        (state.get("source_contract", {}), "source_contract_summary"),
        (state.get("instrument_registry", {}), "instrument_registry_summary"),
        (state.get("proxy_registry", {}), "proxy_registry_summary"),
        (state.get("freshness", {}), "freshness_summary"),
    ):
        errors.extend(validate_authority(payload.get("authority", {}), prefix=prefix))
    return unique_errors(errors)


def build_universe_contract_state(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    return build_universe_contract_from_inputs(
        read_json(runtime / CURRENT_SOURCE_ARTIFACT),
        read_json(runtime / CURRENT_INSTRUMENT_ARTIFACT),
        read_json(runtime / HISTORICAL_SOURCE_ARTIFACT),
        read_json(runtime / STRATEGY_MAP_ARTIFACT),
        read_json(runtime / SUBMISSION_LEDGER_ARTIFACT),
        read_json(runtime / BACKTEST_COVERAGE_ARTIFACT),
        generated_at=now_iso(),
    )


def build_and_write_universe_contract(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    state = build_universe_contract_state(settings)
    errors = validate_universe_contract(state)
    store.write_json(SOURCE_CONTRACT_ARTIFACT, state["source_contract"])
    store.write_json(INSTRUMENT_REGISTRY_ARTIFACT, state["instrument_registry"])
    store.write_json(PROXY_REGISTRY_ARTIFACT, state["proxy_registry"])
    store.write_json(FRESHNESS_SLA_ARTIFACT, state["freshness"])
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_universe_contract_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "implementation_ready": not errors,
        "source_count": state["source_contract"]["source_count"],
        "instrument_count": state["instrument_registry"]["instrument_count"],
        "guarded_route_count": state["instrument_registry"]["guarded_route_count"],
        "context_symbol_route_count": sum(
            row.get("guarded_paper_route_confirmed") is True
            for row in state["instrument_registry"]["instruments"]
            if row.get("observation_role")
            in {"research_price_context", "prediction_contract_context"}
        ),
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "candidate_created_count": 0,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "authority": authority_flags(),
    }
    store.write_json(CHECK_ARTIFACT, checks)
    return state, checks, errors
