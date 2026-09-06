"""Compile-time evidence collectability for Qadam paper strategies."""

from __future__ import annotations

from collections import Counter
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_akber_filter_v3 import (
    CONTEXT_FIELDS,
    DISCOVERY_MICRO_CONFIRMATION_ALTERNATIVES,
    DISCOVERY_MICRO_REQUIRED_FIELDS,
)
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    runtime_dir,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_qualitative_common import (
    LANE_REGISTRY_PATH,
    LANE_SCHEMA_VERSION,
    read_json as read_policy_json,
    repo_root,
)

SCHEMA_VERSION = "qadam_tradeability_capability_matrix.v1"
MATRIX_ARTIFACT = "qadam_tradeability_capability_matrix.json"
STRATEGY_AUDIT_ARTIFACT = "qadam_strategy_collectability_audit.json"
REPAIRS_ARTIFACT = "qadam_uncollectable_requirement_repairs.jsonl"
CHECK_ARTIFACT = "qadam_capability_matrix_checks.json"

FIELD_CAPABILITIES: dict[str, dict[str, Any]] = {
    "source_price_context": {
        "producer": "qadam_edge_registry_and_pattern_score",
        "providers": ["provider_backed_historical_lake", "qadam_pattern_score_v3"],
        "availability": "historical_or_current_relationship",
        "fallback": None,
    },
    "fresh_catalyst": {
        "producer": "qadam_trigger_factory",
        "providers": ["registered_source_adapters"],
        "availability": "current_event_regime_or_dislocation",
        "fallback": None,
    },
    "technical_confirmation": {
        "producer": "market_context_packet",
        "providers": ["alpaca_market_data_v2", "tradingview_supplemental"],
        "availability": "current_or_supplemental",
        "fallback": "confirmation_alternative",
    },
    "volume_or_flow_confirmation": {
        "producer": "market_context_packet",
        "providers": ["alpaca_market_data_v2", "unusual_whales_supplemental"],
        "availability": "current_or_supplemental",
        "fallback": "confirmation_alternative",
    },
    "volatility_context": {
        "producer": "market_context_packet",
        "providers": ["alpaca_market_data_v2", "databento_glbx_mdp3"],
        "availability": "current_market_context",
        "fallback": None,
    },
    "pricing_gap_evidence": {
        "producer": "qadam_trigger_factory_and_market_context",
        "providers": ["alpaca_market_data_v2", "kalshi_official_api", "polymarket_official_clob"],
        "availability": "profile_specific",
        "fallback": "confirmation_alternative",
    },
    "nonlinear_quantum_review": {
        "producer": "qadam_nonlinear_quantum_value",
        "providers": ["matched_classical", "ibm_quantum_when_declared"],
        "availability": "research_review",
        "fallback": "confirmation_alternative",
    },
    "risk_reward_context": {
        "producer": "qadam_decision_evidence_packets",
        "providers": ["deterministic_expectancy_cost_and_invalidation_calculation"],
        "availability": "derived",
        "fallback": None,
    },
    "invalidation_clarity": {
        "producer": "qadam_strategy_foundry_and_market_context",
        "providers": ["deterministic_strategy_contract"],
        "availability": "derived",
        "fallback": None,
    },
    "liquidity_and_spread": {
        "producer": "market_context_packet",
        "providers": ["alpaca_market_data_v2"],
        "availability": "regular_session_current_quote",
        "fallback": None,
    },
    "paperability_proxy": {
        "producer": "qadam_instrument_role_registry",
        "providers": ["guarded_alpaca_paper_route_registry"],
        "availability": "deterministic_route_registry",
        "fallback": None,
    },
}

PROFILE_REQUIREMENTS = {
    "validated_paper_strategy": {
        "hard_fields": list(CONTEXT_FIELDS),
        "confirmation_alternatives": [],
    },
    "discovery_micro": {
        "hard_fields": list(DISCOVERY_MICRO_REQUIRED_FIELDS),
        "confirmation_alternatives": list(DISCOVERY_MICRO_CONFIRMATION_ALTERNATIVES),
    },
    "event_catalyst": {
        "hard_fields": list(DISCOVERY_MICRO_REQUIRED_FIELDS),
        "confirmation_alternatives": list(DISCOVERY_MICRO_CONFIRMATION_ALTERNATIVES),
    },
    "regime_state": {
        "hard_fields": list(DISCOVERY_MICRO_REQUIRED_FIELDS),
        "confirmation_alternatives": list(DISCOVERY_MICRO_CONFIRMATION_ALTERNATIVES),
    },
    "market_dislocation": {
        "hard_fields": list(DISCOVERY_MICRO_REQUIRED_FIELDS),
        "confirmation_alternatives": list(DISCOVERY_MICRO_CONFIRMATION_ALTERNATIVES),
    },
}


def _source_capability(row: dict[str, Any]) -> dict[str, Any]:
    state = str(row.get("state") or row.get("adapter_status") or "unknown")
    if row.get("sample_fixture") is True:
        capability = "sample_only"
    elif row.get("provider_backed_observation") is True:
        capability = "live_provider_backed"
    elif row.get("supplemental_context_only") is True:
        capability = "supplemental"
    elif state in {"degraded", "offline", "unavailable"}:
        capability = "temporarily_unavailable"
    else:
        capability = "registered_no_current_observation"
    return {
        "source_key": row.get("source_key"),
        "source_family": row.get("source_family"),
        "capability": capability,
        "freshness_status": row.get("freshness_status"),
        "provider_backed_observation": row.get("provider_backed_observation") is True,
        "quorum_eligible": row.get("source_quorum_contribution", {}).get("can_contribute") is True,
        "sample_fixture": row.get("sample_fixture") is True,
    }


def _instrument_capability(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol": row.get("symbol"),
        "market_family": row.get("market_family"),
        "research_observable": row.get("observable_for_research") is True,
        "paper_route_available": row.get("paper_route_available") is True,
        "paperability_state": row.get("paperability_state"),
        "price_data_state": row.get("price_data_state"),
        "venue_or_provider": row.get("venue_or_provider"),
    }


def build_capability_matrix(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    generated_at = now_iso()
    source_universe = read_json(runtime / "qsase_source_universe.json")
    trading_universe = read_json(runtime / "qsase_trading_universe.json")
    strategy_map = read_json(runtime / "qadam_strategy_evidence_map_v3.json")
    lane_registry = read_policy_json(repo_root() / LANE_REGISTRY_PATH)
    source_rows = [
        _source_capability(row)
        for row in source_universe.get("sources", [])
        if isinstance(row, dict)
    ]
    instrument_rows = [
        _instrument_capability(row)
        for row in trading_universe.get("instruments", [])
        if isinstance(row, dict)
    ]
    field_rows = []
    for field_id in CONTEXT_FIELDS:
        contract = FIELD_CAPABILITIES.get(field_id)
        if contract is None:
            field_rows.append(
                {
                    "field_id": field_id,
                    "collectability": "structurally_uncollectable",
                    "producer": None,
                    "providers": [],
                    "fallback": None,
                }
            )
            continue
        field_rows.append(
            {
                "field_id": field_id,
                **contract,
                "collectability": "collectable_or_typed_unavailable",
                "fixture_can_satisfy_current_decision": False,
                "unknown_value_can_be_invented": False,
            }
        )
    strategies = []
    for row in strategy_map.get("strategies", []):
        if not isinstance(row, dict):
            continue
        source_contribution = row.get("source_contribution")
        source_contribution = (
            source_contribution if isinstance(source_contribution, dict) else {}
        )
        instrument_contribution = row.get("instrument_contribution")
        instrument_contribution = (
            instrument_contribution if isinstance(instrument_contribution, dict) else {}
        )
        strategies.append(
            {
                "strategy_family_id": row.get("strategy_family_id"),
                "evidence_profile": "discovery_micro",
                "required_fields": list(DISCOVERY_MICRO_REQUIRED_FIELDS),
                "confirmation_alternatives": list(
                    DISCOVERY_MICRO_CONFIRMATION_ALTERNATIVES
                ),
                "configured_sources": source_contribution.get("configured_sources", []),
                "paperable_proxy_symbols": instrument_contribution.get(
                    "paperable_proxy_symbols", []
                ),
                "hard_requirement_structurally_uncollectable": False,
            }
        )
    errors: list[str] = []
    if source_universe.get("source_count") != 41:
        errors.append("canonical_source_count_not_41")
    if trading_universe.get("watched_market_count") != 19:
        errors.append("canonical_instrument_count_not_19")
    if set(FIELD_CAPABILITIES) != set(CONTEXT_FIELDS):
        errors.append("field_capability_contract_incomplete")
    if any(row["collectability"] == "structurally_uncollectable" for row in field_rows):
        errors.append("hard_field_structurally_uncollectable")
    lanes = lane_registry.get("lanes")
    lanes = lanes if isinstance(lanes, list) else []
    lane_ids = [str(row.get("lane_id") or "") for row in lanes if isinstance(row, dict)]
    if lane_registry.get("schema_version") != LANE_SCHEMA_VERSION:
        errors.append("lane_capability_schema_invalid")
    if not lanes:
        errors.append("lane_capability_registry_empty")
    if any(not value for value in lane_ids) or len(lane_ids) != len(set(lane_ids)):
        errors.append("lane_capability_identity_missing_or_duplicate")
    if any(row.get("direct_broker_authority") is not False for row in lanes):
        errors.append("lane_direct_broker_authority_detected")
    if any(str(row.get("maximum_authority") or "") not in {"A0", "A1", "A2", "A3", "A4", "A5", "A6"} for row in lanes):
        errors.append("lane_maximum_authority_invalid")
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_tradeability_capability_matrix",
        "generated_at": generated_at,
        "status": "passed" if not errors else "blocked",
        "source_count": len(source_rows),
        "instrument_count": len(instrument_rows),
        "strategy_count": len(strategies),
        "lane_count": len(lanes),
        "field_count": len(field_rows),
        "profile_requirements": PROFILE_REQUIREMENTS,
        "fields": field_rows,
        "sources": source_rows,
        "instruments": instrument_rows,
        "strategies": strategies,
        "lanes": lanes,
        "lane_authority_tiers": lane_registry.get("authority_tiers", {}),
        "source_capability_counts": dict(
            Counter(row["capability"] for row in source_rows)
        ),
        "validation_errors": errors,
        "authority": authority_flags(),
    }


def uncollectable_fields_for_profile(
    matrix: dict[str, Any], profile_id: str
) -> list[str]:
    profile = matrix.get("profile_requirements", {}).get(profile_id, {})
    hard_fields = set(profile.get("hard_fields") or [])
    states = {
        str(row.get("field_id")): str(row.get("collectability"))
        for row in matrix.get("fields", [])
    }
    return sorted(
        field_id
        for field_id in hard_fields
        if states.get(field_id) != "collectable_or_typed_unavailable"
    )


def validate_capability_matrix(payload: dict[str, Any]) -> list[str]:
    errors = list(payload.get("validation_errors") or [])
    if payload.get("source_count") != 41:
        errors.append("capability_source_count_mismatch")
    if payload.get("instrument_count") != 19:
        errors.append("capability_instrument_count_mismatch")
    field_ids = [str(row.get("field_id") or "") for row in payload.get("fields", [])]
    if set(field_ids) != set(CONTEXT_FIELDS) or len(field_ids) != len(set(field_ids)):
        errors.append("capability_field_identity_mismatch")
    for profile_id in payload.get("profile_requirements", {}):
        if uncollectable_fields_for_profile(payload, profile_id):
            errors.append(f"profile_structurally_uncollectable:{profile_id}")
    lane_rows = payload.get("lanes") if isinstance(payload.get("lanes"), list) else []
    if payload.get("lane_count") != len(lane_rows) or not lane_rows:
        errors.append("capability_lane_count_mismatch")
    if any(row.get("direct_broker_authority") is not False for row in lane_rows):
        errors.append("capability_lane_broker_authority_detected")
    errors.extend(validate_authority(payload.get("authority", {}), prefix="capability_matrix"))
    return unique_errors(errors)


def build_and_write_capability_matrix(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    return write_capability_matrix(build_capability_matrix(settings), settings)


def write_capability_matrix(
    payload: dict[str, Any], settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    """Publish the exact checked input, without rebuilding a different generation."""
    runtime = runtime_dir(settings)
    errors = validate_capability_matrix(payload)
    repairs = [
        {
            "field_id": row.get("field_id"),
            "defect_class": "capability_matrix_mismatch",
            "safe_next_action": "add a reviewed producer or remove the impossible hard requirement",
            "automatic_policy_change_allowed": False,
            "authority": authority_flags(),
        }
        for row in payload.get("fields", [])
        if row.get("collectability") == "structurally_uncollectable"
    ]
    audit = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_strategy_collectability_audit",
        "generated_at": payload["generated_at"],
        "status": "passed" if not errors else "blocked",
        "strategy_count": payload.get("strategy_count"),
        "uncollectable_strategy_count": sum(
            row.get("hard_requirement_structurally_uncollectable") is True
            for row in payload.get("strategies", [])
        ),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    checks = {
        **audit,
        "artifact_type": "qadam_capability_matrix_checks",
        "implementation_complete": not errors,
        "source_count": payload.get("source_count"),
        "instrument_count": payload.get("instrument_count"),
        "field_count": payload.get("field_count"),
        "lane_count": payload.get("lane_count"),
        "repair_count": len(repairs),
    }
    store = AtomicArtifactStore(runtime)
    store.write_json(MATRIX_ARTIFACT, payload)
    store.write_json(STRATEGY_AUDIT_ARTIFACT, audit)
    store.write_jsonl(REPAIRS_ARTIFACT, repairs)
    store.write_json(CHECK_ARTIFACT, checks)
    return payload, checks, errors


__all__ = [
    "CHECK_ARTIFACT",
    "FIELD_CAPABILITIES",
    "MATRIX_ARTIFACT",
    "PROFILE_REQUIREMENTS",
    "build_and_write_capability_matrix",
    "build_capability_matrix",
    "uncollectable_fields_for_profile",
    "validate_capability_matrix",
    "write_capability_matrix",
]
