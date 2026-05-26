"""Preference/PREF MCP first-trading-universe domain-pack mapping.

PREF-7 maps the existing Preference catalog domain packs to Qadam's five
first-trading-universe strategy families. It is a planning artifact only: no
MCP, search_tools, domain tool, paid tool, source-quorum, signal, trade, broker,
quantum, scheduler, or live-capital authority is granted here.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.phase4_candidate_strategy_universe import build_candidate_strategy_universe
from orchestrator.preference_mcp_catalog import build_preference_tool_catalog
from orchestrator.preference_mcp_identity import (
    PREFERENCE_PROVIDER_LABEL,
    PREFERENCE_SOURCE_KEY,
    SECRET_LIKE_PATTERNS,
)


PREFERENCE_DOMAIN_PACK_SCHEMA_VERSION = 1
PREFERENCE_DOMAIN_PACK_STAGE = "PREF-7"
PREFERENCE_DOMAIN_PACK_ARTIFACT_TYPE = "preference_mcp_first_universe_domain_packs"
PREFERENCE_DOMAIN_PACK_ARTIFACT_ID = "preference:pref-7:first-universe-domain-packs"
PREFERENCE_DOMAIN_PACK_BOUNDARY = (
    "Preference/PREF MCP PREF-7 maps allowed domain packs to Qadam strategy "
    "families only. It cannot call live MCP tools, call search_tools, call "
    "domain tools, consume paid tools, satisfy source quorum, create trade "
    "candidates, approve risk, stage or submit paper orders, write to brokers, "
    "call quantum providers, submit hardware jobs, enable schedulers, provide "
    "fills, receipts, reconciliation truth, or enable live capital."
)

PREFERENCE_DOMAIN_PACK_AUTHORITY_FLAGS: tuple[str, ...] = (
    "live_mcp_call_allowed",
    "search_tools_allowed",
    "domain_tool_calls_allowed",
    "paid_tool_calls_allowed",
    "source_quorum_credit_allowed",
    "signal_authority",
    "trade_candidate_creation_allowed",
    "risk_approval_authority",
    "execution_authority",
    "paper_order_authority",
    "broker_write_authority",
    "fill_confirmation_authority",
    "receipt_evidence_authority",
    "reconciliation_truth_authority",
    "quantum_provider_call_allowed",
    "hardware_submission_allowed",
    "scheduler_enabled",
    "live_capital_authority",
)

REQUIRED_STRATEGY_FAMILIES: tuple[str, ...] = (
    "prediction_market_geopolitical_dislocation",
    "crude_oil_energy_security_disruption",
    "defence_repricing_geopolitical_watch",
    "silver_macro_liquidity_stress",
    "semiconductor_policy_options_asymmetry",
)

STRATEGY_DOMAIN_PACK_BLUEPRINTS: dict[str, tuple[dict[str, Any], ...]] = {
    "prediction_market_geopolitical_dislocation": (
        {
            "domain_pack": "prediction_markets",
            "strategy_role": "event_probability_and_liquidity_context",
            "tool_intents": ("orderbook_depth", "market_liquidity", "cross_venue_polymarket_kalshi_comparison"),
            "allowed_context_role": "market_context_only",
            "company_truth_allowed": False,
        },
        {
            "domain_pack": "news_narrative",
            "strategy_role": "geopolitical_narrative_context",
            "tool_intents": ("event_news_monitoring", "narrative_shift", "source_corroboration"),
            "allowed_context_role": "narrative_context_only",
            "company_truth_allowed": False,
        },
    ),
    "crude_oil_energy_security_disruption": (
        {
            "domain_pack": "physical_movement",
            "strategy_role": "vessel_chokepoint_context",
            "tool_intents": ("vessel_movement", "chokepoint_monitoring", "logistics_dislocation"),
            "allowed_context_role": "physical_context_only",
            "company_truth_allowed": False,
        },
        {
            "domain_pack": "macro_commodities",
            "strategy_role": "weather_and_oil_linked_context",
            "tool_intents": ("noaa_weather_context", "oil_linked_physical_signal", "commodity_macro_context"),
            "allowed_context_role": "commodity_context_only",
            "company_truth_allowed": False,
        },
        {
            "domain_pack": "prediction_markets",
            "strategy_role": "oil_linked_prediction_market_context",
            "tool_intents": ("oil_event_pricing", "orderbook_depth", "market_liquidity"),
            "allowed_context_role": "market_context_only",
            "company_truth_allowed": False,
        },
    ),
    "defence_repricing_geopolitical_watch": (
        {
            "domain_pack": "filings_corporate",
            "strategy_role": "sec_filing_metadata_context",
            "tool_intents": ("sec_filing_metadata", "corporate_disclosure_context", "ownership_change_context"),
            "allowed_context_role": "filing_context_only",
            "company_truth_allowed": True,
        },
        {
            "domain_pack": "news_narrative",
            "strategy_role": "procurement_and_policy_narrative_context",
            "tool_intents": ("procurement_narrative", "policy_signal_context", "defence_news_context"),
            "allowed_context_role": "narrative_context_only",
            "company_truth_allowed": False,
        },
        {
            "domain_pack": "prediction_markets",
            "strategy_role": "conflict_and_defence_event_market_context",
            "tool_intents": ("conflict_event_pricing", "market_liquidity", "cross_venue_comparison"),
            "allowed_context_role": "market_context_only",
            "company_truth_allowed": False,
        },
    ),
    "silver_macro_liquidity_stress": (
        {
            "domain_pack": "macro_commodities",
            "strategy_role": "macro_weather_physical_supply_context",
            "tool_intents": ("macro_release_context", "weather_supply_context", "commodity_physical_context"),
            "allowed_context_role": "macro_commodity_context_only",
            "company_truth_allowed": False,
        },
        {
            "domain_pack": "news_narrative",
            "strategy_role": "market_stress_narrative_context",
            "tool_intents": ("liquidity_stress_news", "currency_confidence_narrative", "source_corroboration"),
            "allowed_context_role": "narrative_context_only",
            "company_truth_allowed": False,
        },
    ),
    "semiconductor_policy_options_asymmetry": (
        {
            "domain_pack": "filings_corporate",
            "strategy_role": "sec_filing_and_disclosure_context",
            "tool_intents": ("sec_filing_metadata", "corporate_disclosure_context", "supply_constraint_disclosure"),
            "allowed_context_role": "filing_context_only",
            "company_truth_allowed": True,
        },
        {
            "domain_pack": "news_narrative",
            "strategy_role": "policy_export_control_narrative_context",
            "tool_intents": ("export_control_context", "policy_shift_narrative", "ai_chip_news_context"),
            "allowed_context_role": "narrative_context_only",
            "company_truth_allowed": False,
        },
        {
            "domain_pack": "macro_commodities",
            "strategy_role": "rates_and_macro_policy_context",
            "tool_intents": ("rates_macro_context", "policy_event_context", "supply_chain_macro_context"),
            "allowed_context_role": "macro_context_only",
            "company_truth_allowed": False,
        },
        {
            "domain_pack": "crypto_wallets",
            "strategy_role": "risk_sentiment_only",
            "tool_intents": ("kol_wallet_risk_sentiment", "onchain_liquidity_stress_context"),
            "allowed_context_role": "risk_sentiment_only",
            "company_truth_allowed": False,
            "company_truth_forbidden_reason": "wallet_and_kol_activity_is_sentiment_context_not_company_truth",
        },
    ),
}


@dataclass(frozen=True)
class PreferenceDomainPackMapping:
    candidate_key: str
    candidate_name: str
    instrument_universe: tuple[str, ...]
    mapped_domain_packs: tuple[dict[str, Any], ...]
    allowed_domain_pack_count: int
    preference_context_allowed: bool
    preference_only_confirmation_allowed: bool
    source_quorum_credit_allowed: bool
    market_confirmation_as_corroboration_only: bool
    no_trade_boundary: str
    authority_flags: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["instrument_universe"] = list(self.instrument_universe)
        payload["mapped_domain_packs"] = list(self.mapped_domain_packs)
        return payload


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _authority_flags() -> dict[str, bool]:
    return {flag: False for flag in PREFERENCE_DOMAIN_PACK_AUTHORITY_FLAGS}


def _contains_secret_like_value(payload: Any) -> bool:
    encoded = json.dumps(payload, sort_keys=True, default=str)
    return any(pattern.search(encoded) for pattern in SECRET_LIKE_PATTERNS)


def _catalog_domain_pack_lookup(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(pack.get("domain_pack")): pack
        for pack in catalog.get("domain_packs", [])
        if isinstance(pack, dict) and pack.get("domain_pack")
    }


def _candidate_lookup(candidate_universe: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(candidate.get("candidate_key")): candidate
        for candidate in candidate_universe.get("candidates", [])
        if isinstance(candidate, dict) and candidate.get("candidate_key")
    }


def _domain_pack_row(blueprint: dict[str, Any], catalog_lookup: dict[str, dict[str, Any]]) -> dict[str, Any]:
    domain_pack = str(blueprint["domain_pack"])
    catalog_pack = catalog_lookup.get(domain_pack, {})
    allowed_by_config = catalog_pack.get("allowed_by_config") is True
    approval_status = str(catalog_pack.get("approval_status") or "missing_catalog_pack")
    source_scope = str(catalog_pack.get("source_scope") or "missing_catalog_pack")
    return {
        "domain_pack": domain_pack,
        "label": catalog_pack.get("label") or domain_pack,
        "strategy_role": blueprint["strategy_role"],
        "tool_intents": list(blueprint["tool_intents"]),
        "allowed_context_role": blueprint["allowed_context_role"],
        "allowed_upstream_source_classes": list(catalog_pack.get("allowed_upstream_source_classes") or ()),
        "expected_signal_classes": list(catalog_pack.get("expected_signal_classes") or ()),
        "source_scope": source_scope,
        "allowed_by_config": allowed_by_config,
        "approval_status": approval_status,
        "approved_for_pref_7_mapping": (
            allowed_by_config
            and source_scope == "in_scope"
            and approval_status == "approved_for_catalog_only"
        ),
        "provenance_required": True,
        "domain_tool_calls_allowed": False,
        "paid_tool_allowed": False,
        "source_quorum_credit_allowed": False,
        "trade_candidate_creation_allowed": False,
        "company_truth_allowed": bool(blueprint.get("company_truth_allowed", False)),
        "company_truth_forbidden_reason": blueprint.get("company_truth_forbidden_reason"),
        "boundary": (
            "This Preference domain pack can provide read-only supplemental context only. "
            "It cannot create observations for strategy use until later stages, satisfy source quorum, "
            "create trade candidates, authorize venue access, provide broker truth, or enable execution."
        ),
    }


def _mapping_from_candidate(
    candidate: dict[str, Any],
    *,
    catalog_lookup: dict[str, dict[str, Any]],
) -> PreferenceDomainPackMapping:
    candidate_key = str(candidate["candidate_key"])
    mapped_packs = tuple(
        _domain_pack_row(blueprint, catalog_lookup)
        for blueprint in STRATEGY_DOMAIN_PACK_BLUEPRINTS.get(candidate_key, ())
    )
    allowed_count = sum(1 for pack in mapped_packs if pack["approved_for_pref_7_mapping"])
    return PreferenceDomainPackMapping(
        candidate_key=candidate_key,
        candidate_name=str(candidate.get("name") or candidate_key),
        instrument_universe=tuple(str(item) for item in candidate.get("instrument_universe", ())),
        mapped_domain_packs=mapped_packs,
        allowed_domain_pack_count=allowed_count,
        preference_context_allowed=allowed_count > 0,
        preference_only_confirmation_allowed=False,
        source_quorum_credit_allowed=False,
        market_confirmation_as_corroboration_only=True,
        no_trade_boundary=(
            "Preference context is a hold condition unless corroborated by canonical Qadam sources. "
            "Preference-only context, missing provenance, stale catalog status, disabled domain allowlists, "
            "paid-tool requirements, or any request for risk/execution/paper/broker authority means no trade."
        ),
        authority_flags=_authority_flags(),
    )


def build_preference_domain_pack_mapping(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    catalog = build_preference_tool_catalog(settings=settings, record_event=False)
    candidate_universe = build_candidate_strategy_universe(settings=settings)
    catalog_lookup = _catalog_domain_pack_lookup(catalog)
    candidates_by_key = _candidate_lookup(candidate_universe)
    mappings = [
        _mapping_from_candidate(candidates_by_key[key], catalog_lookup=catalog_lookup)
        for key in REQUIRED_STRATEGY_FAMILIES
        if key in candidates_by_key
    ]
    mapping_rows = [mapping.to_dict() for mapping in mappings]
    unique_domain_packs = sorted(
        {
            str(pack["domain_pack"])
            for mapping in mapping_rows
            for pack in mapping.get("mapped_domain_packs", [])
        }
    )
    authority_flags = _authority_flags()
    artifact = {
        "schema_version": PREFERENCE_DOMAIN_PACK_SCHEMA_VERSION,
        "artifact_type": PREFERENCE_DOMAIN_PACK_ARTIFACT_TYPE,
        "artifact_id": PREFERENCE_DOMAIN_PACK_ARTIFACT_ID,
        "phase": "PREF",
        "stage": PREFERENCE_DOMAIN_PACK_STAGE,
        "status": "validated",
        "generated_at": _now(),
        "public_safe": True,
        "source_key": PREFERENCE_SOURCE_KEY,
        "provider_label": PREFERENCE_PROVIDER_LABEL,
        "catalog_artifact_id": catalog.get("artifact_id"),
        "catalog_stage": catalog.get("stage"),
        "catalog_status": catalog.get("status"),
        "catalog_live_call_attempted": catalog.get("live_catalog_call_attempted"),
        "candidate_strategy_universe_artifact_id": candidate_universe.get("artifact_id"),
        "candidate_strategy_universe_status": candidate_universe.get("status"),
        "first_trading_universe": list(candidate_universe.get("first_trading_universe", [])),
        "required_strategy_families": list(REQUIRED_STRATEGY_FAMILIES),
        "strategy_family_count": len(mapping_rows),
        "expected_strategy_family_count": len(REQUIRED_STRATEGY_FAMILIES),
        "strategy_family_with_allowed_pack_count": sum(
            1 for mapping in mappings if mapping.allowed_domain_pack_count > 0
        ),
        "unique_domain_packs": unique_domain_packs,
        "unique_domain_pack_count": len(unique_domain_packs),
        "mappings": mapping_rows,
        "live_mcp_call_allowed": False,
        "search_tools_allowed": False,
        "domain_tool_calls_allowed": False,
        "paid_tool_calls_allowed": False,
        "source_quorum_credit_allowed": False,
        "preference_only_confirmation_allowed": False,
        "trade_candidate_creation_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
        "authority_flags": authority_flags,
        "boundary": PREFERENCE_DOMAIN_PACK_BOUNDARY,
    }
    artifact["validation_errors"] = validate_preference_domain_pack_mapping(artifact)
    artifact["status"] = "validated" if not artifact["validation_errors"] else "rejected"
    return artifact


def validate_preference_domain_pack_mapping(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version",
        "artifact_type",
        "stage",
        "public_safe",
        "source_key",
        "provider_label",
        "mappings",
        "strategy_family_count",
        "expected_strategy_family_count",
        "strategy_family_with_allowed_pack_count",
        "unique_domain_packs",
        "authority_flags",
        "boundary",
    }
    for field in sorted(required - set(artifact)):
        errors.append(f"missing_field:{field}")
    if artifact.get("schema_version") != PREFERENCE_DOMAIN_PACK_SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if artifact.get("artifact_type") != PREFERENCE_DOMAIN_PACK_ARTIFACT_TYPE:
        errors.append("artifact_type_not_preference_domain_pack_mapping")
    if artifact.get("stage") != PREFERENCE_DOMAIN_PACK_STAGE:
        errors.append("stage_not_pref_7")
    if artifact.get("public_safe") is not True:
        errors.append("public_safe_not_true")
    if artifact.get("source_key") != PREFERENCE_SOURCE_KEY:
        errors.append("source_key_mismatch")
    if artifact.get("provider_label") != PREFERENCE_PROVIDER_LABEL:
        errors.append("provider_label_mismatch")

    mappings = artifact.get("mappings", [])
    if not isinstance(mappings, list):
        errors.append("mappings_not_list")
        mappings = []
    if artifact.get("strategy_family_count") != len(mappings):
        errors.append("strategy_family_count_mismatch")
    if artifact.get("expected_strategy_family_count") != len(REQUIRED_STRATEGY_FAMILIES):
        errors.append("expected_strategy_family_count_mismatch")
    if len(mappings) != len(REQUIRED_STRATEGY_FAMILIES):
        errors.append("required_strategy_family_mapping_missing")
    observed_keys = {str(mapping.get("candidate_key")) for mapping in mappings if isinstance(mapping, dict)}
    for key in REQUIRED_STRATEGY_FAMILIES:
        if key not in observed_keys:
            errors.append(f"strategy_family_missing_domain_pack:{key}")

    families_with_allowed = 0
    unique_domain_packs: set[str] = set()
    for mapping in mappings:
        if not isinstance(mapping, dict):
            errors.append("mapping_not_object")
            continue
        candidate_key = str(mapping.get("candidate_key") or "unknown_candidate")
        packs = mapping.get("mapped_domain_packs")
        if not isinstance(packs, list) or not packs:
            errors.append(f"strategy_family_domain_packs_missing:{candidate_key}")
            packs = []
        if mapping.get("preference_context_allowed") is not True:
            errors.append(f"strategy_family_preference_context_not_allowed:{candidate_key}")
        if mapping.get("preference_only_confirmation_allowed") is not False:
            errors.append(f"strategy_family_preference_only_confirmation_allowed:{candidate_key}")
        if mapping.get("source_quorum_credit_allowed") is not False:
            errors.append(f"strategy_family_source_quorum_credit_allowed:{candidate_key}")
        if mapping.get("market_confirmation_as_corroboration_only") is not True:
            errors.append(f"strategy_family_market_confirmation_not_corroboration_only:{candidate_key}")
        if not str(mapping.get("no_trade_boundary") or "").strip():
            errors.append(f"strategy_family_no_trade_boundary_missing:{candidate_key}")
        allowed_pack_count = sum(1 for pack in packs if pack.get("approved_for_pref_7_mapping") is True)
        if mapping.get("allowed_domain_pack_count") != allowed_pack_count:
            errors.append(f"strategy_family_allowed_pack_count_mismatch:{candidate_key}")
        if allowed_pack_count < 1:
            errors.append(f"strategy_family_no_allowed_domain_pack:{candidate_key}")
        else:
            families_with_allowed += 1

        flags = mapping.get("authority_flags", {})
        if not isinstance(flags, dict):
            errors.append(f"strategy_family_authority_flags_missing:{candidate_key}")
        else:
            for flag in PREFERENCE_DOMAIN_PACK_AUTHORITY_FLAGS:
                if flags.get(flag) is not False:
                    errors.append(f"strategy_family_authority_enabled:{candidate_key}:{flag}")

        for index, pack in enumerate(packs):
            if not isinstance(pack, dict):
                errors.append(f"domain_pack_not_object:{candidate_key}:{index}")
                continue
            domain_pack = str(pack.get("domain_pack") or "")
            unique_domain_packs.add(domain_pack)
            if domain_pack == "sports_lines":
                errors.append(f"sports_lines_domain_pack_mapped:{candidate_key}")
            if domain_pack not in {
                "prediction_markets",
                "physical_movement",
                "filings_corporate",
                "macro_commodities",
                "crypto_wallets",
                "news_narrative",
            }:
                errors.append(f"unknown_domain_pack_mapped:{candidate_key}:{domain_pack}")
            if pack.get("source_scope") != "in_scope":
                errors.append(f"domain_pack_outside_scope:{candidate_key}:{domain_pack}")
            if pack.get("allowed_by_config") is not True:
                errors.append(f"domain_pack_not_allowlisted:{candidate_key}:{domain_pack}")
            if pack.get("approval_status") != "approved_for_catalog_only":
                errors.append(f"domain_pack_not_catalog_only:{candidate_key}:{domain_pack}")
            if pack.get("provenance_required") is not True:
                errors.append(f"domain_pack_provenance_not_required:{candidate_key}:{domain_pack}")
            for key in (
                "domain_tool_calls_allowed",
                "paid_tool_allowed",
                "source_quorum_credit_allowed",
                "trade_candidate_creation_allowed",
            ):
                if pack.get(key) is not False:
                    errors.append(f"domain_pack_authority_enabled:{candidate_key}:{domain_pack}:{key}")
            if domain_pack == "crypto_wallets":
                if pack.get("allowed_context_role") != "risk_sentiment_only":
                    errors.append(f"crypto_wallets_not_risk_sentiment_only:{candidate_key}")
                if pack.get("company_truth_allowed") is not False:
                    errors.append(f"crypto_wallets_company_truth_allowed:{candidate_key}")
            if not pack.get("tool_intents"):
                errors.append(f"domain_pack_tool_intents_missing:{candidate_key}:{domain_pack}")
            if not str(pack.get("boundary") or "").strip():
                errors.append(f"domain_pack_boundary_missing:{candidate_key}:{domain_pack}")

    if artifact.get("strategy_family_with_allowed_pack_count") != families_with_allowed:
        errors.append("strategy_family_with_allowed_pack_count_mismatch")
    if artifact.get("strategy_family_with_allowed_pack_count") != len(REQUIRED_STRATEGY_FAMILIES):
        errors.append("not_all_strategy_families_have_allowed_domain_pack")
    if sorted(artifact.get("unique_domain_packs", [])) != sorted(unique_domain_packs):
        errors.append("unique_domain_packs_mismatch")

    flags = artifact.get("authority_flags", {})
    if not isinstance(flags, dict):
        errors.append("authority_flags_not_object")
    else:
        for flag in PREFERENCE_DOMAIN_PACK_AUTHORITY_FLAGS:
            if flags.get(flag) is not False:
                errors.append(f"authority_flag_enabled:{flag}")
    for key in (
        "live_mcp_call_allowed",
        "search_tools_allowed",
        "domain_tool_calls_allowed",
        "paid_tool_calls_allowed",
        "source_quorum_credit_allowed",
        "preference_only_confirmation_allowed",
        "trade_candidate_creation_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
    ):
        if artifact.get(key) is not False:
            errors.append(f"artifact_authority_enabled:{key}")
    if artifact.get("catalog_live_call_attempted") is not False:
        errors.append("catalog_live_call_attempted")
    if _contains_secret_like_value(artifact):
        errors.append("secret_like_value_exposed")
    return errors


def preference_domain_pack_paths(settings: Settings | None = None) -> tuple[Path, Path]:
    settings = settings or Settings.from_env()
    runtime_dir = Path(settings.runtime_dir)
    return (
        runtime_dir / "preference_domain_packs.json",
        runtime_dir / "preference_domain_packs_history.jsonl",
    )


def write_preference_domain_pack_mapping(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
) -> tuple[Path, Path]:
    output_path, history_path = preference_domain_pack_paths(settings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    artifact["runtime_artifact_path"] = str(output_path)
    artifact["history_log_path"] = str(history_path)
    artifact["validation_errors"] = validate_preference_domain_pack_mapping(artifact)
    artifact["status"] = "validated" if not artifact["validation_errors"] else "rejected"
    output_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PREFERENCE_DOMAIN_PACK_SCHEMA_VERSION,
        "artifact_id": artifact.get("artifact_id"),
        "stage": artifact.get("stage"),
        "status": artifact.get("status"),
        "generated_at": artifact.get("generated_at"),
        "recorded_at": _now(),
        "strategy_family_count": artifact.get("strategy_family_count"),
        "strategy_family_with_allowed_pack_count": artifact.get(
            "strategy_family_with_allowed_pack_count"
        ),
        "unique_domain_pack_count": artifact.get("unique_domain_pack_count"),
        "validation_error_count": len(artifact.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path
