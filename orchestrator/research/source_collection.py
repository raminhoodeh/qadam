"""Provider-safe recovery schedules and honest catalog-wide collection coverage."""

from collections import Counter
from datetime import timedelta

from orchestrator.qadam_wave_b_common import parse_timestamp


ALIASES = {
    "ais_or_shipping": ("ais_maritime",),
    "social.rss": ("rss",),
    "yahoo_finance_or_tradingview": ("yahoo_finance", "tradingview_mcp"),
}
EXTERNAL_OWNERS = {
    "yahoo_finance": "market_data_refresh",
    "tradingview_mcp": "configured_readonly_mcp_bridge",
    "tradingview_paid_alerts": "configured_alert_receiver",
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
    return {
        "last_attempt_at": now.isoformat(),
        "last_success_at": now.isoformat() if failure == "none" else prior.get("last_success_at"),
        "next_attempt_at": (now + timedelta(seconds=delay)).isoformat(),
        "consecutive_failures": count, "failure_class": failure,
        "collection_status": "collected" if failure == "none" else "needs_configuration" if
            failure == "configuration_or_entitlement" else "needs_adapter_repair" if
            failure == "provider_contract" else "retry_scheduled",
        "event_count": int(validation.get("event_count") or 0),
        "last_error": validation.get("degraded_reason"),
        "next_action": "poll_on_provider_cadence" if failure == "none" else
            "restore_credentials_entitlement_or_local_bridge" if failure == "configuration_or_entitlement" else
            "review_provider_contract_without_substituting_evidence" if failure == "provider_contract" else
            "bounded_readonly_retry",
    }


def build_collection_coverage(universe, specs, scheduled, *, generated_at):
    spec_by_key = {spec.key: spec for spec in specs}
    source_by_key = {row["source_key"]: row for row in universe.get("sources", [])
                     if row.get("source_key")}
    rows = []
    now = parse_timestamp(generated_at)
    for key in sorted(set(spec_by_key) | set(source_by_key)):
        spec, source = spec_by_key.get(key), source_by_key.get(key, {})
        detail = dict(scheduled.get(key, {}))
        if detail:
            due = parse_timestamp(detail.get("next_attempt_at"))
            if not due or (now and now > due + timedelta(minutes=15)):
                detail["collection_status"] = "overdue"
            owner = "source_ingestion"
        elif key in ALIASES:
            owner = "derived_from_upstream"
            detail = {"collection_status": "derived_alias", "upstream_sources": list(ALIASES[key]),
                      "next_action": "inspect_upstream_collection_not_a_separate_feed"}
        elif key in EXTERNAL_OWNERS:
            owner = EXTERNAL_OWNERS[key]
            detail = {"collection_status": "external_collector", "next_action": "verify_owner_receipt_and_provider_timestamp"}
        elif spec and getattr(spec, "status", "") == "intentionally_disabled":
            owner = "operator_configuration"
            detail = {"collection_status": "intentionally_disabled", "next_action": "requires_explicit_reenable_and_entitlement_review"}
        else:
            owner = "source_ingestion"
            detail = {"collection_status": "not_scheduled", "next_action": "implement_or_configure_readonly_collector"}
        rows.append({"source_key": key, "owner": owner, **detail,
                     "selection_status": getattr(spec, "selection_status", "external_or_derived"),
                     "configured_operator_action": getattr(spec, "operator_action", "inspect_owner"),
                     "provider_event_latest_at": source.get("provider_event_latest_at"),
                     "observed_at": source.get("observed_timestamp"),
                     "evidence_freshness": source.get("freshness_status", "unknown"),
                     "collection_success_is_not_trade_evidence": True})
    counts = dict(Counter(row["collection_status"] for row in rows))
    return {"generated_at": generated_at, "catalogue_count": len(rows), "sources": rows,
            "collection_state_counts": counts,
            "all_sources_collecting": bool(rows) and all(row["collection_status"] == "collected" for row in rows),
            "catalogue_count_is_not_independent_feed_count": True,
            "broker_write_count": 0}
