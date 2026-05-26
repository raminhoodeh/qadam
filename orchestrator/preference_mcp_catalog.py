"""Preference/PREF MCP tool catalog contract.

PREF-2 builds a public-safe catalog ledger for the Preference data plane. It
records the Qadam domain packs and safe discovery queries without calling
``search_tools`` or any discovered domain tool. Live discovery is a later gate
after PREF-1 proves a non-anonymous identity with quota metadata.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.preference_mcp_identity import (
    PREFERENCE_CLASSIFICATION,
    PREFERENCE_DISCOVERY_TOOL_NAME,
    PREFERENCE_PROVIDER_LABEL,
    PREFERENCE_SOURCE_KEY,
    SECRET_LIKE_PATTERNS,
    build_preference_mcp_identity_status,
    validate_preference_mcp_identity_status,
)

PREFERENCE_TOOL_CATALOG_SCHEMA_VERSION = 1
PREFERENCE_TOOL_CATALOG_ARTIFACT_TYPE = "preference_mcp_tool_catalog"
PREFERENCE_TOOL_CATALOG_EVENT_TYPE = "preference_mcp_tool_catalog_snapshot_built"
PREFERENCE_TOOL_CATALOG_EVENT_COMPONENT = "preference_mcp_catalog"
PREFERENCE_TOOL_CATALOG_STAGE = "PREF-2"
PREFERENCE_TOOL_CATALOG_ARTIFACT_ID = "preference:pref-2:tool-catalog"
PREFERENCE_TOOL_CATALOG_BOUNDARY = (
    "Preference/PREF MCP PREF-2 is catalog-only. It can define planned "
    "search_tools queries and approval states, but it cannot call search_tools, "
    "call market/orderbook/wallet/filing/weather tools, consume paid tools, "
    "create observations, satisfy source quorum, create trade candidates, "
    "approve risk, stage or submit paper orders, write to brokers, call quantum "
    "providers, submit hardware jobs, enable schedulers, provide fills, "
    "receipts, reconciliation truth, or enable live capital."
)
PREFERENCE_TOOL_CATALOG_ALLOWED_STATUSES = (
    "approved_for_catalog_only",
    "candidate_read_only",
    "blocked_paid_tool",
    "blocked_no_provenance",
    "blocked_outside_scope",
)

CATALOG_DOMAIN_PACKS: tuple[dict[str, Any], ...] = (
    {
        "domain_pack": "prediction_markets",
        "label": "Prediction markets",
        "source_scope": "in_scope",
        "queries": (
            "Polymarket orderbook depth for geopolitical and macro event markets",
            "Kalshi market liquidity and event contract metadata",
            "prediction market cross venue arbitrage and provenance",
        ),
        "expected_signal_classes": (
            "event_probability",
            "orderbook_depth",
            "cross_venue_liquidity",
        ),
        "allowed_upstream_source_classes": ("polymarket", "kalshi", "prediction_markets"),
    },
    {
        "domain_pack": "physical_movement",
        "label": "Physical movement",
        "source_scope": "in_scope",
        "queries": (
            "vessel tracking chokepoint movements Strait of Hormuz",
            "satellite imagery activity signal with provenance",
            "aircraft and logistics movement event monitoring",
        ),
        "expected_signal_classes": (
            "vessel_position",
            "satellite_activity",
            "logistics_movement",
        ),
        "allowed_upstream_source_classes": ("vessel_tracking", "satellite", "aircraft"),
    },
    {
        "domain_pack": "filings_corporate",
        "label": "Filings and corporate disclosures",
        "source_scope": "in_scope",
        "queries": (
            "SEC filing metadata latest 8-K 10-Q 13F with source link",
            "corporate disclosure extraction provenance",
            "insider ownership and institutional filing event context",
        ),
        "expected_signal_classes": (
            "regulatory_filing",
            "corporate_disclosure",
            "ownership_change",
        ),
        "allowed_upstream_source_classes": ("sec", "edgar", "corporate_filings"),
    },
    {
        "domain_pack": "macro_commodities",
        "label": "Macro and commodities",
        "source_scope": "in_scope",
        "queries": (
            "NOAA weather event forecast commodity market impact provenance",
            "oil linked physical signal and energy market context",
            "rates inflation commodities macro event data with citations",
        ),
        "expected_signal_classes": (
            "weather_event",
            "energy_physical_signal",
            "macro_release",
        ),
        "allowed_upstream_source_classes": ("noaa", "weather", "commodities", "macro"),
    },
    {
        "domain_pack": "crypto_wallets",
        "label": "Crypto wallets and derivatives",
        "source_scope": "in_scope",
        "queries": (
            "top KOL wallet movement last four hours with provenance",
            "Hyperliquid positioning and derivatives flow context",
            "dFlow smart money routing and on-chain market signal",
        ),
        "expected_signal_classes": (
            "wallet_flow",
            "derivatives_positioning",
            "onchain_routing",
        ),
        "allowed_upstream_source_classes": ("wallets", "hyperliquid", "dflow", "onchain"),
    },
    {
        "domain_pack": "news_narrative",
        "label": "News and narrative context",
        "source_scope": "in_scope",
        "queries": (
            "event driven news monitoring with source provenance",
            "market narrative change detection cited sources",
            "latest geopolitical event summary with upstream source links",
        ),
        "expected_signal_classes": (
            "news_event",
            "narrative_shift",
            "source_corroboration",
        ),
        "allowed_upstream_source_classes": ("news", "media_monitoring", "event_summary"),
    },
    {
        "domain_pack": "sports_lines",
        "label": "Sports lines",
        "source_scope": "outside_current_strategy_universe",
        "queries": (
            "sports betting lines market odds provenance",
            "sports event orderbook and line movement context",
        ),
        "expected_signal_classes": ("sports_line", "odds_movement"),
        "allowed_upstream_source_classes": ("sportsbooks", "sports_lines"),
    },
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _blank_authority_flags() -> dict[str, bool]:
    return {
        "search_tools_allowed": False,
        "domain_tool_calls_allowed": False,
        "paid_tool_calls_allowed": False,
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


def _entry_status(domain_pack: dict[str, Any], settings: Settings) -> tuple[str, str]:
    domain_key = str(domain_pack["domain_pack"])
    if domain_pack.get("source_scope") != "in_scope":
        return "blocked_outside_scope", "outside_current_strategy_universe"
    if domain_key not in settings.preference_mcp_domain_allowlist:
        return "blocked_outside_scope", "domain_pack_not_in_preference_allowlist"
    return "approved_for_catalog_only", "planned_query_live_discovery_deferred"


def _domain_pack_rows(settings: Settings) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pack in CATALOG_DOMAIN_PACKS:
        status, reason = _entry_status(pack, settings)
        rows.append(
            {
                "domain_pack": pack["domain_pack"],
                "label": pack["label"],
                "source_scope": pack["source_scope"],
                "query_count": len(pack["queries"]),
                "expected_signal_classes": list(pack["expected_signal_classes"]),
                "allowed_upstream_source_classes": list(pack["allowed_upstream_source_classes"]),
                "allowed_by_config": pack["domain_pack"] in settings.preference_mcp_domain_allowlist,
                "approval_status": status,
                "status_reason": reason,
                "provenance_required": True,
                "source_quorum_credit_allowed": False,
                "domain_tool_calls_allowed": False,
                "paid_tool_allowed": False,
            }
        )
    return rows


def _catalog_entries(settings: Settings) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for pack in CATALOG_DOMAIN_PACKS:
        status, reason = _entry_status(pack, settings)
        for ordinal, query in enumerate(pack["queries"], start=1):
            entries.append(
                {
                    "entry_type": "planned_search_query",
                    "catalog_source": "planned_query",
                    "domain_pack": pack["domain_pack"],
                    "domain_pack_label": pack["label"],
                    "source_scope": pack["source_scope"],
                    "query_ordinal": ordinal,
                    "query": query,
                    "discovery_tool_name": PREFERENCE_DISCOVERY_TOOL_NAME,
                    "detail_level_requested": "none_until_verified_identity",
                    "tool_ref": None,
                    "tool_name": None,
                    "live_discovered": False,
                    "callable_schema_available": False,
                    "call_template_available": False,
                    "call_template_allowed": False,
                    "approval_status": status,
                    "status_reason": reason,
                    "expected_signal_classes": list(pack["expected_signal_classes"]),
                    "allowed_upstream_source_classes": list(
                        pack["allowed_upstream_source_classes"]
                    ),
                    "provenance_required": True,
                    "provenance_path_present": False,
                    "domain_tool_call_allowed": False,
                    "paid_tool_allowed": False,
                    "counts_against_source_quorum": False,
                    "can_create_observation": False,
                    "can_create_trade_candidate": False,
                    "broker_write_authority": False,
                    "live_capital_authority": False,
                }
            )
    return entries


def build_preference_tool_catalog(
    *,
    settings: Settings | None = None,
    identity_status: dict[str, Any] | None = None,
    event_log: EventLog | None = None,
    record_event: bool = False,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    identity_status = identity_status or build_preference_mcp_identity_status(
        settings=settings,
        live_status_check=False,
        record_event=False,
    )
    entries = _catalog_entries(settings)
    domain_packs = _domain_pack_rows(settings)
    status_counts = dict(Counter(str(entry["approval_status"]) for entry in entries))
    identity_verified = identity_status.get("status") == "verified_non_anonymous"
    blocked_reasons = [
        "domain_tool_calls_disabled_in_pref_2",
        "live_catalog_not_requested_in_pref_2",
        "paid_tools_disabled_in_pref_2",
        "search_tools_call_disabled_in_pref_2",
    ]
    if not identity_verified:
        blocked_reasons.append("verified_identity_required_for_live_catalog")
    if settings.preference_mcp_paid_tools_allowed:
        blocked_reasons.append("paid_tools_config_must_remain_false")

    artifact = {
        "schema_version": PREFERENCE_TOOL_CATALOG_SCHEMA_VERSION,
        "artifact_type": PREFERENCE_TOOL_CATALOG_ARTIFACT_TYPE,
        "artifact_id": PREFERENCE_TOOL_CATALOG_ARTIFACT_ID,
        "phase": "PREF",
        "stage": PREFERENCE_TOOL_CATALOG_STAGE,
        "status": (
            "catalog_schema_ready_pending_live_discovery"
            if identity_verified
            else "blocked_pending_verified_identity"
        ),
        "generated_at": _now(),
        "public_safe": True,
        "classification": PREFERENCE_CLASSIFICATION,
        "source_key": PREFERENCE_SOURCE_KEY,
        "provider_label": PREFERENCE_PROVIDER_LABEL,
        "endpoint": settings.preference_mcp_endpoint,
        "transport": settings.preference_mcp_transport,
        "enabled": settings.preference_mcp_enabled,
        "discovery_tool_name": PREFERENCE_DISCOVERY_TOOL_NAME,
        "live_catalog_requested": False,
        "live_catalog_call_attempted": False,
        "search_tools_allowed": False,
        "search_tools_call_attempted": False,
        "domain_tool_calls_allowed": False,
        "paid_tool_calls_allowed": False,
        "paid_tools_allowed_by_config": settings.preference_mcp_paid_tools_allowed,
        "daily_call_budget": settings.preference_mcp_daily_call_budget,
        "run_call_budget": settings.preference_mcp_run_call_budget,
        "tool_allowlist_count": len(settings.preference_mcp_tool_allowlist),
        "domain_allowlist": list(settings.preference_mcp_domain_allowlist),
        "domain_allowlist_count": len(settings.preference_mcp_domain_allowlist),
        "identity_status": identity_status,
        "identity_gate_status": identity_status.get("status"),
        "identity_gate_identity_status": identity_status.get("identity_status"),
        "identity_gate_quota_metadata_present": identity_status.get("quota_metadata_present"),
        "allowed_statuses": list(PREFERENCE_TOOL_CATALOG_ALLOWED_STATUSES),
        "domain_packs": domain_packs,
        "domain_pack_count": len(domain_packs),
        "catalog_entries": entries,
        "catalog_entry_count": len(entries),
        "status_counts": status_counts,
        "approved_for_catalog_only_count": status_counts.get("approved_for_catalog_only", 0),
        "candidate_read_only_count": status_counts.get("candidate_read_only", 0),
        "blocked_paid_tool_count": status_counts.get("blocked_paid_tool", 0),
        "blocked_no_provenance_count": status_counts.get("blocked_no_provenance", 0),
        "blocked_outside_scope_count": status_counts.get("blocked_outside_scope", 0),
        "blocked_reasons": sorted(set(blocked_reasons)),
        "blocked_reason_count": len(set(blocked_reasons)),
        "authority_flags": _blank_authority_flags(),
        "boundary": PREFERENCE_TOOL_CATALOG_BOUNDARY,
    }
    artifact["validation_errors"] = validate_preference_tool_catalog(artifact)

    if record_event:
        event_log = event_log or EventLog(echo=False)
        event_log.write(
            PREFERENCE_TOOL_CATALOG_EVENT_TYPE,
            PREFERENCE_TOOL_CATALOG_EVENT_COMPONENT,
            {
                "stage": artifact["stage"],
                "status": artifact["status"],
                "identity_gate_status": artifact["identity_gate_status"],
                "live_catalog_call_attempted": False,
                "search_tools_call_attempted": False,
                "domain_tool_calls_allowed": False,
                "paid_tool_calls_allowed": False,
                "catalog_entry_count": artifact["catalog_entry_count"],
                "status_counts": artifact["status_counts"],
                "broker_write_allowed": False,
                "live_capital_enabled": False,
            },
        )
    return artifact


def preference_tool_catalog_paths(settings: Settings | None = None) -> tuple[Path, Path]:
    settings = settings or Settings.from_env()
    runtime_dir = Path(settings.runtime_dir)
    return (
        runtime_dir / "preference_tool_catalog.json",
        runtime_dir / "preference_tool_catalog_history.jsonl",
    )


def write_preference_tool_catalog(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
) -> tuple[Path, Path]:
    output_path, history_path = preference_tool_catalog_paths(settings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    artifact["runtime_artifact_path"] = str(output_path)
    artifact["history_log_path"] = str(history_path)
    artifact["validation_errors"] = validate_preference_tool_catalog(artifact)
    output_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PREFERENCE_TOOL_CATALOG_SCHEMA_VERSION,
        "artifact_id": artifact.get("artifact_id"),
        "stage": artifact.get("stage"),
        "status": artifact.get("status"),
        "generated_at": artifact.get("generated_at"),
        "recorded_at": _now(),
        "identity_gate_status": artifact.get("identity_gate_status"),
        "catalog_entry_count": artifact.get("catalog_entry_count"),
        "status_counts": artifact.get("status_counts"),
        "live_catalog_call_attempted": artifact.get("live_catalog_call_attempted"),
        "search_tools_call_attempted": artifact.get("search_tools_call_attempted"),
        "domain_tool_calls_allowed": artifact.get("domain_tool_calls_allowed"),
        "paid_tool_calls_allowed": artifact.get("paid_tool_calls_allowed"),
        "validation_error_count": len(artifact.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path


def validate_preference_tool_catalog(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version",
        "artifact_type",
        "stage",
        "status",
        "public_safe",
        "classification",
        "source_key",
        "provider_label",
        "discovery_tool_name",
        "live_catalog_call_attempted",
        "search_tools_call_attempted",
        "search_tools_allowed",
        "domain_tool_calls_allowed",
        "paid_tool_calls_allowed",
        "identity_status",
        "catalog_entries",
        "catalog_entry_count",
        "status_counts",
        "authority_flags",
        "boundary",
    }
    missing = sorted(required - set(artifact))
    for field in missing:
        errors.append(f"missing_field:{field}")
    if artifact.get("schema_version") != PREFERENCE_TOOL_CATALOG_SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if artifact.get("artifact_type") != PREFERENCE_TOOL_CATALOG_ARTIFACT_TYPE:
        errors.append("artifact_type_not_preference_mcp_tool_catalog")
    if artifact.get("stage") != PREFERENCE_TOOL_CATALOG_STAGE:
        errors.append("stage_not_pref_2")
    if artifact.get("public_safe") is not True:
        errors.append("public_safe_not_true")
    if artifact.get("classification") != PREFERENCE_CLASSIFICATION:
        errors.append("classification_mismatch")
    if artifact.get("source_key") != PREFERENCE_SOURCE_KEY:
        errors.append("source_key_mismatch")
    if artifact.get("provider_label") != PREFERENCE_PROVIDER_LABEL:
        errors.append("provider_label_mismatch")
    if artifact.get("discovery_tool_name") != PREFERENCE_DISCOVERY_TOOL_NAME:
        errors.append("discovery_tool_name_mismatch")
    if artifact.get("live_catalog_call_attempted") is not False:
        errors.append("live_catalog_call_attempted")
    if artifact.get("search_tools_call_attempted") is not False:
        errors.append("search_tools_call_attempted")
    if artifact.get("search_tools_allowed") is not False:
        errors.append("search_tools_allowed")
    if artifact.get("domain_tool_calls_allowed") is not False:
        errors.append("domain_tool_calls_allowed")
    if artifact.get("paid_tool_calls_allowed") is not False:
        errors.append("paid_tool_calls_allowed")
    if artifact.get("paid_tools_allowed_by_config") is not False:
        errors.append("paid_tools_allowed_by_config")

    identity_status = artifact.get("identity_status")
    if not isinstance(identity_status, dict):
        errors.append("identity_status_not_object")
    else:
        identity_errors = validate_preference_mcp_identity_status(identity_status)
        for error in identity_errors:
            errors.append(f"identity_status_invalid:{error}")
        if (
            artifact.get("live_catalog_call_attempted") is True
            and identity_status.get("status") != "verified_non_anonymous"
        ):
            errors.append("live_catalog_without_verified_identity")

    flags = artifact.get("authority_flags", {})
    if not isinstance(flags, dict):
        errors.append("authority_flags_not_object")
    else:
        for key, value in flags.items():
            if value is not False:
                errors.append(f"authority_flag_enabled:{key}")

    entries = artifact.get("catalog_entries", [])
    if not isinstance(entries, list) or not entries:
        errors.append("catalog_entries_missing")
        entries = []
    if artifact.get("catalog_entry_count") != len(entries):
        errors.append("catalog_entry_count_mismatch")
    allowed_statuses = set(PREFERENCE_TOOL_CATALOG_ALLOWED_STATUSES)
    domain_allowlist = set(artifact.get("domain_allowlist", []))
    status_counts = Counter()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"catalog_entry_not_object:{index}")
            continue
        status = entry.get("approval_status")
        status_counts[str(status)] += 1
        if status not in allowed_statuses:
            errors.append(f"catalog_entry_invalid_status:{index}:{status}")
        if entry.get("domain_tool_call_allowed") is not False:
            errors.append(f"catalog_entry_domain_tool_call_allowed:{index}")
        if entry.get("paid_tool_allowed") is not False:
            errors.append(f"catalog_entry_paid_tool_allowed:{index}")
        if entry.get("call_template_allowed") is not False:
            errors.append(f"catalog_entry_call_template_allowed:{index}")
        if entry.get("counts_against_source_quorum") is not False:
            errors.append(f"catalog_entry_source_quorum_credit_allowed:{index}")
        if entry.get("can_create_observation") is not False:
            errors.append(f"catalog_entry_observation_creation_allowed:{index}")
        if entry.get("can_create_trade_candidate") is not False:
            errors.append(f"catalog_entry_trade_candidate_allowed:{index}")
        if entry.get("broker_write_authority") is not False:
            errors.append(f"catalog_entry_broker_write_authority:{index}")
        if entry.get("live_capital_authority") is not False:
            errors.append(f"catalog_entry_live_capital_authority:{index}")
        if entry.get("provenance_required") is not True:
            errors.append(f"catalog_entry_provenance_not_required:{index}")
        if status == "candidate_read_only" and entry.get("live_discovered") is not True:
            errors.append(f"candidate_read_only_without_live_discovery:{index}")
        if status == "candidate_read_only" and not entry.get("tool_ref"):
            errors.append(f"candidate_read_only_without_tool_ref:{index}")
        if status == "approved_for_catalog_only" and entry.get("tool_ref"):
            errors.append(f"catalog_only_entry_has_tool_ref:{index}")
        if entry.get("source_scope") != "in_scope" and status != "blocked_outside_scope":
            errors.append(f"outside_scope_entry_not_blocked:{index}")
        if (
            entry.get("source_scope") == "in_scope"
            and entry.get("domain_pack") not in domain_allowlist
            and status != "blocked_outside_scope"
        ):
            errors.append(f"not_allowlisted_entry_not_blocked:{index}")

    artifact_counts = artifact.get("status_counts", {})
    if not isinstance(artifact_counts, dict):
        errors.append("status_counts_not_object")
    else:
        normalized_counts = dict(status_counts)
        if artifact_counts != normalized_counts:
            errors.append("status_counts_mismatch")
        for status in PREFERENCE_TOOL_CATALOG_ALLOWED_STATUSES:
            count_field = f"{status}_count"
            if count_field in artifact and artifact[count_field] != normalized_counts.get(status, 0):
                errors.append(f"{count_field}_mismatch")

    domain_packs = artifact.get("domain_packs", [])
    if not isinstance(domain_packs, list) or not domain_packs:
        errors.append("domain_packs_missing")
    else:
        for index, pack in enumerate(domain_packs):
            if not isinstance(pack, dict):
                errors.append(f"domain_pack_not_object:{index}")
                continue
            if pack.get("domain_tool_calls_allowed") is not False:
                errors.append(f"domain_pack_tool_call_allowed:{index}")
            if pack.get("paid_tool_allowed") is not False:
                errors.append(f"domain_pack_paid_tool_allowed:{index}")
            if pack.get("source_quorum_credit_allowed") is not False:
                errors.append(f"domain_pack_source_quorum_credit_allowed:{index}")
            if pack.get("source_scope") != "in_scope" and pack.get(
                "approval_status"
            ) != "blocked_outside_scope":
                errors.append(f"outside_scope_domain_pack_not_blocked:{index}")

    if _contains_secret_like_value(artifact):
        errors.append("secret_like_value_exposed")
    return errors
