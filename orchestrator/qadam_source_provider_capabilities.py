"""OR-2 source freshness policy and historical provider capabilities."""

from __future__ import annotations

from collections import Counter
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    unique_errors,
    validate_authority,
)
from orchestrator.qsase_source_reliability import CATEGORY_SCHEDULES
from orchestrator.unusual_whales_adapter import (
    FEATURE_MANIFEST_ARTIFACT as UNUSUAL_WHALES_FEATURE_MANIFEST_ARTIFACT,
    STATUS_ARTIFACT as UNUSUAL_WHALES_STATUS_ARTIFACT,
)

SCHEMA_VERSION = "qadam_source_provider_capabilities.v1"
PHASE_ID = "OR-2"

CAPABILITY_ARTIFACT = "qadam_provider_capability_registry.jsonl"
FRESHNESS_POLICY_ARTIFACT = "qadam_source_freshness_policy.json"
OPERATIONAL_STATE_ARTIFACT = "qadam_source_operational_state.jsonl"
QUARANTINE_ARTIFACT = "qadam_source_quarantine.jsonl"
REPAIR_REQUESTS_ARTIFACT = "qadam_provider_repair_requests.jsonl"
CHECK_ARTIFACT = "qadam_source_provider_capabilities_checks.json"

SOURCE_UNIVERSE_ARTIFACT = "qsase_source_universe.json"
RELIABILITY_RECORDS_ARTIFACT = "qsase_source_reliability_records.jsonl"

HISTORICAL_SUPPORTED = {
    "acled",
    "alpaca",
    "arcgis_usace",
    "bis",
    "bls",
    "ecb",
    "fred",
    "gdelt",
    "github",
    "hyperliquid",
    "internet_outage",
    "kalshi",
    "nasa_firms",
    "patents",
    "polymarket",
    "sec_edgar",
    "space_track_celestrak",
    "stock_act",
    "ucdp",
    "un_comtrade",
    "usgs",
    "yahoo_finance",
}
FORWARD_ONLY = {
    "oref",
    "reddit",
    "rss",
    "telegram",
    "tradingview_mcp",
    "tradingview_paid_alerts",
    "twitter_x",
}
DERIVED_ONLY = {
    "ais_or_shipping",
    "conflict_tracker",
    "social.rss",
    "yahoo_finance_or_tradingview",
}
DISABLED_OR_UNSELECTED = {
    "chainlink",
    "coinglass",
    "rapidapi",
    "unusual_whales",
}

PROFILES: dict[str, dict[str, Any]] = {
    "acled": {"granularity": "event", "pagination": "page_or_cursor", "revision": "provider_updates_possible"},
    "alpaca": {"granularity": "minute_to_day", "pagination": "page_token", "revision": "corporate_action_adjustment"},
    "bis": {"granularity": "monthly_to_quarterly", "pagination": "series_query", "revision": "revisions_possible"},
    "bls": {"granularity": "monthly", "pagination": "series_year_ranges", "revision": "vintage_revision_possible"},
    "ecb": {"granularity": "daily_to_monthly", "pagination": "time_range_query", "revision": "revisions_possible"},
    "fred": {"granularity": "series_native", "pagination": "observation_offset", "revision": "vintage_requires_alfred"},
    "gdelt": {"granularity": "event_or_document", "pagination": "time_window", "revision": "append_or_correction_possible"},
    "nasa_firms": {"granularity": "observation", "pagination": "bounded_date_window", "revision": "near_real_time_then_archive"},
    "sec_edgar": {"granularity": "filing", "pagination": "submission_history", "revision": "amendments_are_new_filings"},
    "ucdp": {"granularity": "event", "pagination": "page", "revision": "dataset_versioned"},
    "un_comtrade": {"granularity": "monthly_or_annual", "pagination": "offset_or_period", "revision": "revisions_possible"},
    "usgs": {"granularity": "event_or_dataset", "pagination": "time_window", "revision": "event_updates_possible"},
    "yahoo_finance": {"granularity": "minute_to_day", "pagination": "period_range", "revision": "adjusted_history_may_change"},
}


def _capability_class(source_key: str) -> str:
    if source_key in HISTORICAL_SUPPORTED:
        return "historical_interface_supported_validation_required"
    if source_key in FORWARD_ONLY:
        return "forward_only_or_unarchived"
    if source_key in DERIVED_ONLY:
        return "derived_from_upstream_history"
    if source_key in DISABLED_OR_UNSELECTED:
        return "unavailable_or_provider_unselected"
    return "historical_capability_unknown_provider_review_required"


def _failure_class(reliability: dict[str, Any]) -> str:
    state = str(reliability.get("adapter_status") or "unknown").lower()
    credential = str(reliability.get("credential_status") or "unknown").lower()
    reason = str(reliability.get("outage_reason") or "unknown").lower()
    freshness = str(reliability.get("freshness_state") or "unknown").lower()
    if credential in {"missing", "expired", "invalid", "not_configured", "denied"}:
        return "credential_failure"
    if "rate" in reason and "limit" in reason:
        return "rate_limited"
    if "parse" in reason or "schema" in reason:
        return "parser_defect"
    if "market_closed" in reason or "holiday" in reason:
        return "market_closure"
    if "empty_valid" in reason:
        return "empty_valid_response"
    if state in {"disabled", "not_selected", "future", "receiver_pending"}:
        return "unsupported_or_not_selected"
    if state not in {"online", "ready", "connected", "ok", "sample_ready"}:
        return "provider_or_adapter_unavailable"
    if freshness != "fresh":
        return "stale_observation"
    return "none"


def _build_capability(
    source: dict[str, Any],
    reliability: dict[str, Any],
    *,
    unusual_whales_status: dict[str, Any] | None = None,
    unusual_whales_features: dict[str, Any] | None = None,
) -> dict[str, Any]:
    key = str(source.get("source_key") or "unknown")
    if key == "unusual_whales":
        status = unusual_whales_status or {}
        features = unusual_whales_features or {}
        adapter_state = str(status.get("status") or "ready_not_initialized")
        feature_ready = features.get("backtest_feature_ready") is True
        fresh_ingestion_allowed = status.get("fresh_ingestion_allowed") is True
        return {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_provider_capability",
            "generated_at": now_iso(),
            "source_key": key,
            "source_name": source.get("source_name") or "Unusual Whales",
            "source_family": source.get("source_family"),
            "source_category": reliability.get("source_category") or "market",
            "current_data_support": adapter_state,
            "historical_capability_class": "time_bounded_historical_research_adapter",
            "historical_api_supported": True,
            "historical_interface_validated_this_run": status.get("adapter_implemented") is True,
            "earliest_available_date": features.get("coverage_start"),
            "earliest_available_date_state": (
                "captured_feature_coverage" if feature_ready else "provider_entitlement_probe_required"
            ),
            "pagination_model": "bounded_date_window_and_time_cursor",
            "revision_vintage_semantics": "provider_snapshot_revision_semantics_not_verified",
            "rate_limit_policy": "conservative_local_daily_and_per_run_budget",
            "credential_requirement": {
                "state": status.get("credential_state") or "not_configured",
                "required_or_optional": "required_during_trial_capture_only",
                "automation_may_edit_secret": False,
            },
            "terms_licensing_note": "provider_terms_review_required_before_capture_or_raw_retention",
            "native_granularity": "event_to_five_minute_and_daily",
            "expected_data_quality": "point_in_time_and_entitlement_validation_required",
            "fallback_or_proxy": "none_approved",
            "forward_only": False,
            "supplemental_context_only": True,
            "historical_research_only": True,
            "historical_capture_mode": "supplemental_feature_manifest",
            "provider_backfill_adapter": "unusual_whales_historical_research",
            "provider_backfill_eligible_now": fresh_ingestion_allowed,
            "provider_backfill_blocker": (
                None if fresh_ingestion_allowed else adapter_state
            ),
            "access_expires_on": status.get("access_expires_on") or "2026-07-21",
            "post_expiry_mode": "historical_archive_only",
            "backtest_feature_ready": feature_ready,
            "backtest_eligible_record_count": int(
                features.get("backtest_eligible_record_count") or 0
            ),
            "coverage_start": features.get("coverage_start"),
            "coverage_end": features.get("coverage_end"),
            "source_quorum_allowed": False,
            "execution_allowed": False,
            "proof_credit_allowed": False,
            "authority": authority_flags(),
        }
    capability_class = _capability_class(key)
    profile = PROFILES.get(key, {})
    credential_state = str(source.get("credential_status") or "unknown")
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_provider_capability",
        "generated_at": now_iso(),
        "source_key": key,
        "source_name": source.get("source_name") or key,
        "source_family": source.get("source_family"),
        "source_category": reliability.get("source_category") or "other",
        "current_data_support": (
            "configured" if source.get("adapter_status") in {"online", "ready", "connected", "ok"} else "not_verified"
        ),
        "historical_capability_class": capability_class,
        "historical_api_supported": key in HISTORICAL_SUPPORTED,
        "historical_interface_validated_this_run": False,
        "earliest_available_date": None,
        "earliest_available_date_state": "provider_query_required",
        "pagination_model": profile.get("pagination", "provider_review_required"),
        "revision_vintage_semantics": profile.get("revision", "provider_review_required"),
        "rate_limit_policy": "bounded_provider_specific_budget_required",
        "credential_requirement": {
            "state": credential_state,
            "required_or_optional": "credential_or_provider_contract_specific",
            "automation_may_edit_secret": False,
        },
        "terms_licensing_note": "review_required_before_bulk_historical_acquisition",
        "native_granularity": profile.get("granularity", "provider_native_unknown"),
        "expected_data_quality": source.get("trust_posture") or "unscored",
        "fallback_or_proxy": (
            "upstream_sources_only" if key in DERIVED_ONLY else "none_approved"
        ),
        "forward_only": key in FORWARD_ONLY,
        "supplemental_context_only": bool(source.get("supplemental_context_only")),
        "provider_backfill_eligible_now": False,
        "provider_backfill_blocker": (
            "historical_interface_and_terms_not_validated_this_run"
            if key in HISTORICAL_SUPPORTED
            else capability_class
        ),
        "execution_allowed": False,
        "authority": authority_flags(),
    }


def build_source_provider_capabilities(
    settings: Settings | None = None,
) -> dict[str, list[dict[str, Any]] | dict[str, Any]]:
    runtime = runtime_dir(settings)
    universe = read_json(runtime / SOURCE_UNIVERSE_ARTIFACT)
    sources = universe.get("sources") if isinstance(universe.get("sources"), list) else []
    reliability_records = read_jsonl(runtime / RELIABILITY_RECORDS_ARTIFACT)
    unusual_whales_status = read_json(runtime / UNUSUAL_WHALES_STATUS_ARTIFACT)
    unusual_whales_features = read_json(runtime / UNUSUAL_WHALES_FEATURE_MANIFEST_ARTIFACT)
    reliability_by_key = {str(record.get("source_key")): record for record in reliability_records}
    capabilities: list[dict[str, Any]] = []
    operational: list[dict[str, Any]] = []
    quarantine: list[dict[str, Any]] = []
    repair_requests: list[dict[str, Any]] = []
    for source in sources:
        key = str(source.get("source_key") or "unknown")
        reliability = reliability_by_key.get(key, {})
        capability = _build_capability(
            source,
            reliability,
            unusual_whales_status=unusual_whales_status,
            unusual_whales_features=unusual_whales_features,
        )
        capabilities.append(capability)
        failure_class = _failure_class(reliability)
        fresh = reliability.get("freshness_state") == "fresh"
        supplemental = bool(capability["supplemental_context_only"])
        can_contribute = bool(
            fresh
            and not supplemental
            and reliability.get("source_quorum_contribution", {}).get("can_contribute") is True
        )
        state = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_source_operational_state",
            "generated_at": now_iso(),
            "source_key": key,
            "freshness_state": reliability.get("freshness_state") or "unknown",
            "freshness_budget_seconds": reliability.get("freshness_budget_seconds"),
            "observed_at": reliability.get("observed_timestamp"),
            "observed_age_seconds": reliability.get("observed_age_seconds"),
            "failure_class": failure_class,
            "context_visible": True,
            "raw_scoring_eligible": can_contribute,
            "source_quorum_eligible": can_contribute,
            "historical_capability_class": capability["historical_capability_class"],
            "authority": authority_flags(),
        }
        operational.append(state)
        if not can_contribute:
            quarantine.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "artifact_type": "qadam_source_quarantine",
                    "generated_at": now_iso(),
                    "source_key": key,
                    "quarantine_scope": ["raw_pattern_score", "source_quorum"],
                    "context_visibility_preserved": True,
                    "reason_class": failure_class if not supplemental else "supplemental_context_only",
                    "release_condition": "fresh independently validated observation and eligible source role",
                    "automatic_trust_promotion_allowed": False,
                    "authority": authority_flags(),
                }
            )
        if failure_class in {
            "credential_failure",
            "parser_defect",
            "provider_or_adapter_unavailable",
            "rate_limited",
        }:
            blocks_current_scoring = (
                reliability.get("required_for_reliability_target") is True
                and supplemental is False
            )
            repair_requests.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "artifact_type": "qadam_provider_repair_request",
                    "generated_at": now_iso(),
                    "source_key": key,
                    "failure_class": failure_class,
                    "requested_action": "operator_review_or_safe_read_only_adapter_repair",
                    "repair_scope": (
                        "blocking_required_source"
                        if blocks_current_scoring
                        else "nonblocking_quarantined_or_optional_source"
                    ),
                    "blocks_current_scoring": blocks_current_scoring,
                    "context_visibility_preserved": True,
                    "secret_edit_allowed": False,
                    "code_edit_allowed": False,
                    "authority": authority_flags(),
                }
            )
    policy = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_source_freshness_policy",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "policy_ready",
        "category_policies": CATEGORY_SCHEDULES,
        "market_session_semantics": "provider_market_calendar_required_for_market_closure_classification",
        "stale_source_raw_scoring_allowed": False,
        "stale_source_quorum_allowed": False,
        "context_only_visibility_allowed": True,
        "sources_are_strategy_specific_not_universally_required": True,
        "authority": authority_flags(),
    }
    return {
        "policy": policy,
        "capabilities": capabilities,
        "operational": operational,
        "quarantine": quarantine,
        "repair_requests": repair_requests,
    }


def validate_source_provider_capabilities(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    capabilities = bundle.get("capabilities") if isinstance(bundle.get("capabilities"), list) else []
    operational = bundle.get("operational") if isinstance(bundle.get("operational"), list) else []
    quarantine = bundle.get("quarantine") if isinstance(bundle.get("quarantine"), list) else []
    policy = bundle.get("policy") if isinstance(bundle.get("policy"), dict) else {}
    capability_keys = {record.get("source_key") for record in capabilities}
    operational_keys = {record.get("source_key") for record in operational}
    if not capabilities:
        errors.append("provider_capability_registry_empty")
    if capability_keys != operational_keys:
        errors.append("provider_operational_registry_source_mismatch")
    required_fields = {
        "current_data_support",
        "historical_capability_class",
        "historical_api_supported",
        "earliest_available_date_state",
        "pagination_model",
        "revision_vintage_semantics",
        "rate_limit_policy",
        "credential_requirement",
        "terms_licensing_note",
        "native_granularity",
        "expected_data_quality",
        "fallback_or_proxy",
        "forward_only",
    }
    for record in capabilities:
        for field in required_fields:
            if field not in record:
                errors.append(f"provider_capability_field_missing:{record.get('source_key')}:{field}")
        errors.extend(validate_authority(record.get("authority", {}), prefix="provider_capability"))
    for record in operational:
        if record.get("freshness_state") != "fresh" and (
            record.get("raw_scoring_eligible") is not False
            or record.get("source_quorum_eligible") is not False
        ):
            errors.append(f"stale_source_not_quarantined:{record.get('source_key')}")
    quarantined_keys = {record.get("source_key") for record in quarantine}
    expected_quarantine = {
        record.get("source_key") for record in operational if record.get("raw_scoring_eligible") is not True
    }
    if not expected_quarantine.issubset(quarantined_keys):
        errors.append("source_quarantine_incomplete")
    if policy.get("stale_source_raw_scoring_allowed") is not False:
        errors.append("freshness_policy_allows_stale_scoring")
    errors.extend(validate_authority(policy.get("authority", {}), prefix="freshness_policy"))
    return unique_errors(errors)


def build_and_write_source_provider_capabilities(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    bundle = build_source_provider_capabilities(settings)
    store.write_json(FRESHNESS_POLICY_ARTIFACT, bundle["policy"])
    store.write_jsonl(CAPABILITY_ARTIFACT, bundle["capabilities"])
    store.write_jsonl(OPERATIONAL_STATE_ARTIFACT, bundle["operational"])
    store.write_jsonl(QUARANTINE_ARTIFACT, bundle["quarantine"])
    store.write_jsonl(REPAIR_REQUESTS_ARTIFACT, bundle["repair_requests"])
    errors = validate_source_provider_capabilities(bundle)
    operational = bundle["operational"]
    classes = Counter(record.get("failure_class") for record in operational)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_source_provider_capabilities_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "registered_source_count": len(bundle["capabilities"]),
        "operational_state_count": len(operational),
        "fresh_scoring_eligible_count": sum(
            record.get("raw_scoring_eligible") is True for record in operational
        ),
        "quarantined_or_context_only_count": len(bundle["quarantine"]),
        "repair_request_count": len(bundle["repair_requests"]),
        "blocking_repair_request_count": sum(
            record.get("blocks_current_scoring") is True
            for record in bundle["repair_requests"]
        ),
        "nonblocking_repair_request_count": sum(
            record.get("blocks_current_scoring") is not True
            for record in bundle["repair_requests"]
        ),
        "failure_class_counts": dict(sorted(classes.items())),
        "historical_supported_interface_count": sum(
            record.get("historical_api_supported") is True for record in bundle["capabilities"]
        ),
        "historical_validated_this_run_count": sum(
            record.get("historical_interface_validated_this_run") is True
            for record in bundle["capabilities"]
        ),
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "broker_write_count": 0,
        "authority": authority_flags(),
    }
    store.write_json(CHECK_ARTIFACT, checks)
    return bundle, checks, errors
