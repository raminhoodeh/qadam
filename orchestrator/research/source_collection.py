"""Provider-safe recovery schedules and honest catalog-wide collection coverage."""

from collections import Counter
from datetime import timedelta

from orchestrator.qadam_wave_b_common import parse_timestamp


ALIASES = {
    "conflict_tracker": ("acled", "gdelt"),
    "ais_or_shipping": ("ais_maritime",),
    "social.rss": ("rss",),
    "yahoo_finance_or_tradingview": ("yahoo_finance", "tradingview_mcp"),
}
EXTERNAL_OWNERS = {
    "yahoo_finance": "market_data_refresh",
    "tradingview_mcp": "configured_readonly_mcp_bridge",
    "tradingview_paid_alerts": "configured_alert_receiver",
}
ACCESS_ACTIONS = {
    "acled": "confirm_acled_consent_profile_and_api_access_group_with_provider",
    "oref": "provider_denies_access_no_geographic_or_authentication_bypass",
    "twitter_x": "restore_x_api_credit_or_endpoint_entitlement",
    "ucdp": "configure_provider_issued_UCDP_ACCESS_TOKEN",
    "patents": "configure_provider_issued_PATENTSVIEW_API_KEY",
    "bookmap": "start_authenticated_local_bookmap_bridge_and_configure_BOOKMAP_BRIDGE_URL",
    "tradingview_paid_alerts": "configure_authenticated_alert_receiver_and_verify_delivery",
}


def retry_class(validation):
    reason = str(validation.get("degraded_reason") or "").lower()
    if validation.get("validation_status") == "live" and not validation.get("degraded"):
        return "none"
    if any(part in reason for part in ("credential", "http_401", "http_402", "http_403", "bridge_url_missing", "endpoint_unconfirmed")):
        return "configuration_or_entitlement"
    if "http_429" in reason or "rate_limit" in reason:
        return "rate_limited"
    if any(part in reason for part in ("http_400", "http_404", "http_410", "parse", "jsondecode", "valueerror", "provider_error_response")):
        return "provider_contract"
    return "transient_or_unclassified"


def collection_schedule(validation, prior, *, cadence_seconds, now):
    failure = retry_class(validation)
    count = 0 if failure == "none" else int(prior.get("consecutive_failures") or 0) + 1
    if failure == "none":
        delay = cadence_seconds
    elif failure in {"configuration_or_entitlement", "provider_contract"}:
        delay = max(cadence_seconds, 6 * 3600)
    else:
        # Slow publication cadence must not postpone recovery for an entire week.
        delay = min(cadence_seconds, min(3600, 300 * 2 ** min(count - 1, 4)))
        if failure == "rate_limited":
            delay = max(delay, 3600)
    retry_after = validation.get("retry_after_seconds")
    if failure != "none" and isinstance(retry_after, (float, int)) and not isinstance(retry_after, bool):
        delay = max(delay, min(86400, max(0, retry_after)))
    return {
        "last_attempt_at": now.isoformat(),
        "last_success_at": now.isoformat() if failure == "none" else prior.get("last_success_at"),
        "next_attempt_at": (now + timedelta(seconds=delay)).isoformat(),
        "consecutive_failures": count, "failure_class": failure,
        "collection_status": "collected" if failure == "none" else "needs_configuration" if
            failure == "configuration_or_entitlement" else "needs_adapter_repair" if
            failure == "provider_contract" else "retry_scheduled",
        "event_count": int(validation.get("event_count") or 0),
        "observation_count": int(validation.get("observation_count") or 0),
        "provider_record_count": int(validation.get("provider_record_count") or 0),
        "collection_evidence_state": validation.get("collection_evidence_state", "unverified"),
        "latest_provider_observation_at": validation.get("latest_event_at"),
        "timestamp_verified_observation_count": validation.get("timestamp_verified_observation_count", 0),
        "timestamp_unverified_observation_count": validation.get("timestamp_unverified_observation_count", 0),
        "retry_after_seconds": retry_after,
        "last_error": validation.get("degraded_reason"),
        "next_action": "poll_on_provider_cadence" if failure == "none" else
            "restore_credentials_entitlement_or_local_bridge" if failure == "configuration_or_entitlement" else
            "review_provider_contract_without_substituting_evidence" if failure == "provider_contract" else
            "bounded_readonly_retry",
    }


def build_collection_coverage(universe, specs, scheduled, *, generated_at, context=None):
    spec_by_key = {spec.key: spec for spec in specs}
    source_by_key = {row["source_key"]: row for row in universe.get("sources", [])
                     if row.get("source_key")}
    rows = []
    now = parse_timestamp(generated_at)
    context = context or {}
    context_stamp = parse_timestamp(context.get("generated_at"))
    context_current = bool(now and context_stamp and 0 <= (now - context_stamp).total_seconds() <= 1800)
    context_keys = set(context.get("context_sources_used_in_packets", [])) if context_current else set()
    for key in sorted(set(spec_by_key) | set(source_by_key)):
        spec, source = spec_by_key.get(key), source_by_key.get(key, {})
        detail = dict(scheduled.get(key, {}))
        if key in ALIASES:
            owner = "derived_from_upstream"
            detail = {"collection_status": "derived_alias", "upstream_sources": list(ALIASES[key]),
                      "next_action": "inspect_upstream_collection_not_a_separate_feed"}
        elif detail:
            due = parse_timestamp(detail.get("next_attempt_at"))
            if not due or (now and now > due + timedelta(minutes=15)):
                detail["collection_status"] = "overdue"
            owner = "source_ingestion"
        elif key in EXTERNAL_OWNERS:
            owner = EXTERNAL_OWNERS[key]
            detail = {"collection_status": "needs_configuration" if key == "tradingview_paid_alerts" else "external_collector",
                      "next_action": "configure_authenticated_alert_receiver_and_real_delivery" if key == "tradingview_paid_alerts" else
                      "verify_owner_receipt_and_provider_timestamp"}
        elif spec and getattr(spec, "status", "") == "intentionally_disabled":
            owner = "operator_configuration"
            detail = {"collection_status": "intentionally_disabled", "next_action": "requires_explicit_reenable_and_entitlement_review"}
        elif spec and getattr(spec, "selection_status", "") == "not_selected":
            owner = "operator_configuration"
            detail = {"collection_status": "not_selected", "next_action": getattr(spec, "operator_action", "define_research_role")}
        else:
            owner = "source_ingestion"
            detail = {"collection_status": "not_scheduled", "next_action": "implement_or_configure_readonly_collector"}
        rows.append({"source_key": key, "owner": owner, **detail,
                     "forward_context_available": key in context_keys,
                     "context_receipt_count": context.get("source_receipt_counts", {}).get(key, 0) if context_current else 0,
                     "context_timestamp_basis": "durable_first_seen_no_publication_claim" if key in context_keys else None,
                     "context_is_not_fresh_catalyst_or_execution_quote": True,
                     "access_repair_action": ACCESS_ACTIONS.get(key) if detail.get("collection_status") == "needs_configuration" else None,
                     "repair_requires_user_or_provider": detail.get("collection_status") == "needs_configuration",
                     "selection_status": getattr(spec, "selection_status", "external_or_derived"),
                     "configured_operator_action": getattr(spec, "operator_action", "inspect_owner"),
                     "provider_event_latest_at": source.get("provider_event_latest_at"),
                     "observed_at": source.get("observed_timestamp"),
                     "evidence_freshness": source.get("freshness_status", "unknown"),
                     "collection_success_is_not_trade_evidence": True})
    counts = dict(Counter(row["collection_status"] for row in rows))
    return {"generated_at": generated_at, "catalogue_count": len(rows), "sources": rows,
            "collection_state_counts": counts,
            "all_sources_collecting": bool(rows) and all(
                row["collection_status"] == "collected" and row.get("observation_count", 0) > 0 for row in rows),
            "observation_state_counts": dict(Counter(row.get("collection_evidence_state", "not_applicable") for row in rows)),
            "catalogue_count_is_not_independent_feed_count": True,
            "forward_context_source_count": len(context_keys),
            "context_projection_current": context_current,
            "unresolved_access_actions": [{"source_key": row["source_key"], "action": row.get("access_repair_action") or row.get("next_action")}
                                          for row in rows if row.get("repair_requires_user_or_provider")],
            "broker_write_count": 0}
