"""Preference/PREF MCP shadow-intelligence context.

PREF-8 lets Phase 2 packets see Preference context as read-only challenge
material. This module deliberately reuses PREF-3 sample observations, PREF-5
provenance, and PREF-7 domain packs without granting live MCP, source-quorum,
trade-candidate, risk, execution, broker, quantum, scheduler, or live-capital
authority.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.preference_mcp_adapter import PreferenceMCPAdapter
from orchestrator.preference_mcp_domain_packs import (
    build_preference_domain_pack_mapping,
    validate_preference_domain_pack_mapping,
)
from orchestrator.preference_mcp_identity import (
    PREFERENCE_PROVIDER_LABEL,
    PREFERENCE_SOURCE_KEY,
    SECRET_LIKE_PATTERNS,
    build_preference_mcp_identity_status,
)
from orchestrator.preference_mcp_provenance import (
    build_preference_source_quorum_report,
    validate_preference_source_quorum_report,
)

PREFERENCE_SHADOW_CONTEXT_SCHEMA_VERSION = 1
PREFERENCE_SHADOW_CONTEXT_STAGE = "PREF-8"
PREFERENCE_SHADOW_CONTEXT_ARTIFACT_TYPE = "preference_mcp_shadow_intelligence_context"
PREFERENCE_SHADOW_CONTEXT_ARTIFACT_ID = "preference:pref-8:shadow-intelligence-context"
PREFERENCE_SHADOW_CONTEXT_EVENT_TYPE = "preference_mcp_shadow_context_checked"
PREFERENCE_SHADOW_CONTEXT_EVENT_COMPONENT = "preference_mcp_shadow_context"
PREFERENCE_SHADOW_CONTEXT_MAX_AGE = timedelta(hours=48)
PREFERENCE_SHADOW_CONTEXT_ROLE = "read_only_shadow_challenge_context"
PREFERENCE_SHADOW_CONTEXT_BOUNDARY = (
    "Preference/PREF MCP PREF-8 can enrich Research Analyst and Strategy Lead "
    "shadow packets as read-only challenge context only. Preference-only "
    "confirmation is a hold condition; orderbook depth is market context, not "
    "venue or execution permission; wallet/KOL movement is sentiment and risk "
    "context, not factual corporate evidence. PREF-8 cannot call live MCP "
    "domain tools, consume paid tools, satisfy source quorum, create trade "
    "candidates, approve risk, hand off to execution, stage or submit paper "
    "orders, write to brokers, call quantum providers, submit hardware jobs, "
    "enable schedulers, provide fills, receipts, reconciliation truth, or "
    "enable live capital."
)

PREFERENCE_SHADOW_AUTHORITY_FLAGS: tuple[str, ...] = (
    "live_mcp_call_allowed",
    "search_tools_allowed",
    "domain_tool_calls_allowed",
    "paid_tool_calls_allowed",
    "source_quorum_credit_allowed",
    "preference_only_confirmation_allowed",
    "signal_authority",
    "trade_candidate_creation_allowed",
    "risk_handoff_allowed",
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

PREFERENCE_SHADOW_POLICY_CHALLENGES: tuple[str, ...] = (
    "Refresh Preference context before relying on it when context_stale is true.",
    "Add independent non-Preference evidence when Preference is single-source.",
    "Reject Preference context with missing or invalid provenance.",
    "Verify non-anonymous Preference identity and quota before any live Preference use.",
    "Treat Preference-only confirmation as a hold condition, not corroboration.",
)

DOMAIN_CONTEXT_ROLES = {
    "prediction_markets": "market_context_only",
    "physical_movement": "physical_context_only",
    "macro_commodities": "macro_commodity_context_only",
    "filings_corporate": "filing_context_only",
    "crypto_wallets": "risk_sentiment_only",
    "news_narrative": "narrative_context_only",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _authority_flags() -> dict[str, bool]:
    return {flag: False for flag in PREFERENCE_SHADOW_AUTHORITY_FLAGS}


def _contains_secret_like_value(payload: Any) -> bool:
    encoded = json.dumps(payload, sort_keys=True, default=str)
    return any(pattern.search(encoded) for pattern in SECRET_LIKE_PATTERNS)


def _events(envelope: dict[str, Any]) -> list[dict[str, Any]]:
    events = envelope.get("events", [])
    return [event for event in events if isinstance(event, dict)] if isinstance(events, list) else []


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _freshness(events: list[dict[str, Any]]) -> tuple[str | None, bool]:
    observed_times = tuple(
        parsed
        for event in events
        if (parsed := _parse_time(event.get("ingested_at"))) is not None
    )
    if not observed_times:
        return None, True
    latest = max(observed_times)
    return latest.isoformat(), latest < datetime.now(timezone.utc) - PREFERENCE_SHADOW_CONTEXT_MAX_AGE


def _shadow_observation(event: dict[str, Any]) -> dict[str, Any]:
    raw_payload = event.get("raw_payload", {})
    raw_payload = raw_payload if isinstance(raw_payload, dict) else {}
    domain_pack = str(raw_payload.get("domain_pack") or "unknown_domain")
    signal_class = str(raw_payload.get("signal_class") or "unknown_signal_class")
    context_role = DOMAIN_CONTEXT_ROLES.get(domain_pack, "supplemental_context_only")
    return {
        "event_id": str(event.get("event_id") or "unknown_event")[:160],
        "source": str(event.get("source") or "supplemental.preference_mcp")[:120],
        "event_type": str(event.get("event_type") or "preference_context")[:120],
        "domain_pack": domain_pack,
        "upstream_source": str(raw_payload.get("upstream_source") or "unknown_upstream")[:120],
        "signal_class": signal_class,
        "context_role": context_role,
        "summary": str(event.get("normalised_summary") or "")[:280],
        "observed_at": str(event.get("ingested_at") or "")[:80],
        "provenance_required": True,
        "source_quorum_credit_allowed": False,
        "trade_candidate_creation_allowed": False,
        "orderbook_depth_execution_or_venue_permission": False,
        "wallet_kol_company_truth_allowed": False,
        "boundary": (
            "Preference observation is read-only challenge context. It cannot "
            "satisfy source quorum or create a trade candidate."
        ),
    }


def _active_challenges(
    *,
    context_stale: bool,
    single_source_hold: bool,
    missing_provenance_hold: bool,
    quota_degraded: bool,
) -> list[str]:
    challenges: list[str] = []
    if context_stale:
        challenges.append(PREFERENCE_SHADOW_POLICY_CHALLENGES[0])
    if single_source_hold:
        challenges.append(PREFERENCE_SHADOW_POLICY_CHALLENGES[1])
    if missing_provenance_hold:
        challenges.append(PREFERENCE_SHADOW_POLICY_CHALLENGES[2])
    if quota_degraded:
        challenges.append(PREFERENCE_SHADOW_POLICY_CHALLENGES[3])
    challenges.append(PREFERENCE_SHADOW_POLICY_CHALLENGES[4])
    return list(dict.fromkeys(challenges))


def build_preference_shadow_context(
    *,
    settings: Settings | None = None,
    event_log: EventLog | None = None,
    record_event: bool = False,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    event_log = event_log or EventLog(echo=False)
    identity_status = build_preference_mcp_identity_status(
        settings=settings,
        live_status_check=False,
        record_event=False,
    )
    domain_packs = build_preference_domain_pack_mapping(settings=settings)
    domain_errors = validate_preference_domain_pack_mapping(domain_packs)
    envelope = PreferenceMCPAdapter(settings=settings, event_log=event_log).fetch_sample().to_dict()
    events = _events(envelope)
    provenance = build_preference_source_quorum_report(preference_events=events, record_event=False)
    provenance_errors = validate_preference_source_quorum_report(provenance)
    latest_observed_at, context_stale = _freshness(events)

    upstream_count = int(provenance.get("preference_distinct_upstream_source_count", 0) or 0)
    missing_provenance_hold = bool(provenance_errors) or int(
        provenance.get("quarantined_observation_count", 0) or 0
    ) > 0
    single_source_hold = upstream_count < 2
    quota_degraded = (
        identity_status.get("status") != "verified_non_anonymous"
        or identity_status.get("quota_metadata_present") is not True
    )
    offline_context_allowed = (
        not domain_errors
        and not missing_provenance_hold
        and not single_source_hold
        and bool(events)
        and envelope.get("degraded") is not True
    )
    active_challenges = _active_challenges(
        context_stale=context_stale,
        single_source_hold=single_source_hold,
        missing_provenance_hold=missing_provenance_hold,
        quota_degraded=quota_degraded,
    )
    status = "challenge_only_ready" if offline_context_allowed else "challenge_only_hold"

    artifact = {
        "schema_version": PREFERENCE_SHADOW_CONTEXT_SCHEMA_VERSION,
        "artifact_type": PREFERENCE_SHADOW_CONTEXT_ARTIFACT_TYPE,
        "artifact_id": PREFERENCE_SHADOW_CONTEXT_ARTIFACT_ID,
        "phase": "PREF",
        "stage": PREFERENCE_SHADOW_CONTEXT_STAGE,
        "status": status,
        "generated_at": _now(),
        "public_safe": True,
        "source_key": PREFERENCE_SOURCE_KEY,
        "provider_label": PREFERENCE_PROVIDER_LABEL,
        "context_role": PREFERENCE_SHADOW_CONTEXT_ROLE,
        "sample_context_mode": "deterministic_sample",
        "identity_gate_status": identity_status.get("status"),
        "identity_gate_identity_status": identity_status.get("identity_status"),
        "quota_metadata_present": identity_status.get("quota_metadata_present"),
        "quota_degraded": quota_degraded,
        "catalog_status": domain_packs.get("catalog_status"),
        "domain_pack_status": domain_packs.get("status"),
        "domain_pack_validation_error_count": len(domain_errors),
        "provenance_status": provenance.get("status"),
        "provenance_context_status": provenance.get("preference_context_status"),
        "provenance_validation_error_count": len(provenance_errors),
        "preference_observation_count": len(events),
        "shadow_observation_count": len(events),
        "shadow_observations": [_shadow_observation(event) for event in events],
        "latest_observed_at": latest_observed_at,
        "context_stale": context_stale,
        "max_age_seconds": int(PREFERENCE_SHADOW_CONTEXT_MAX_AGE.total_seconds()),
        "preference_distinct_upstream_source_count": upstream_count,
        "preference_multi_source_context_allowed": provenance.get(
            "preference_multi_source_context_allowed"
        ),
        "single_source_hold": single_source_hold,
        "missing_provenance_hold": missing_provenance_hold,
        "source_quorum_credit_allowed": False,
        "preference_only_confirmation_allowed": False,
        "orderbook_depth_role": "market_context_only",
        "orderbook_depth_execution_or_venue_permission": False,
        "wallet_kol_role": "risk_sentiment_only",
        "wallet_kol_company_truth_allowed": False,
        "research_analyst_context_allowed": offline_context_allowed,
        "strategy_lead_context_allowed": offline_context_allowed,
        "signal_integrity_context_allowed": offline_context_allowed,
        "live_mcp_call_attempted": False,
        "search_tools_call_attempted": False,
        "domain_tool_call_attempted": False,
        "paid_tool_call_attempted": False,
        "trade_candidate_creation_allowed": False,
        "risk_handoff_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
        "policy_challenges": list(PREFERENCE_SHADOW_POLICY_CHALLENGES),
        "active_required_challenges": active_challenges,
        "active_required_challenge_count": len(active_challenges),
        "authority_flags": _authority_flags(),
        "boundary": PREFERENCE_SHADOW_CONTEXT_BOUNDARY,
    }
    artifact["validation_errors"] = validate_preference_shadow_context(artifact)
    artifact["status"] = "challenge_only_ready" if not artifact["validation_errors"] else "rejected"

    if record_event:
        event_log.write(
            PREFERENCE_SHADOW_CONTEXT_EVENT_TYPE,
            PREFERENCE_SHADOW_CONTEXT_EVENT_COMPONENT,
            {
                "stage": artifact["stage"],
                "status": artifact["status"],
                "context_role": artifact["context_role"],
                "shadow_observation_count": artifact["shadow_observation_count"],
                "active_required_challenge_count": artifact["active_required_challenge_count"],
                "quota_degraded": artifact["quota_degraded"],
                "context_stale": artifact["context_stale"],
                "single_source_hold": artifact["single_source_hold"],
                "missing_provenance_hold": artifact["missing_provenance_hold"],
                "source_quorum_credit_allowed": False,
                "trade_candidate_creation_allowed": False,
                "broker_write_allowed": False,
                "live_capital_enabled": False,
            },
        )
    return artifact


def validate_preference_shadow_context(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version",
        "artifact_type",
        "stage",
        "status",
        "public_safe",
        "source_key",
        "provider_label",
        "context_role",
        "shadow_observation_count",
        "shadow_observations",
        "context_stale",
        "single_source_hold",
        "missing_provenance_hold",
        "quota_degraded",
        "source_quorum_credit_allowed",
        "preference_only_confirmation_allowed",
        "orderbook_depth_execution_or_venue_permission",
        "wallet_kol_company_truth_allowed",
        "active_required_challenges",
        "authority_flags",
        "boundary",
    }
    for field in sorted(required - set(artifact)):
        errors.append(f"missing_field:{field}")
    if artifact.get("schema_version") != PREFERENCE_SHADOW_CONTEXT_SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if artifact.get("artifact_type") != PREFERENCE_SHADOW_CONTEXT_ARTIFACT_TYPE:
        errors.append("artifact_type_not_preference_shadow_context")
    if artifact.get("stage") != PREFERENCE_SHADOW_CONTEXT_STAGE:
        errors.append("stage_not_pref_8")
    if artifact.get("public_safe") is not True:
        errors.append("public_safe_not_true")
    if artifact.get("source_key") != PREFERENCE_SOURCE_KEY:
        errors.append("source_key_mismatch")
    if artifact.get("provider_label") != PREFERENCE_PROVIDER_LABEL:
        errors.append("provider_label_mismatch")
    if artifact.get("context_role") != PREFERENCE_SHADOW_CONTEXT_ROLE:
        errors.append("context_role_mismatch")
    if artifact.get("domain_pack_status") != "validated":
        errors.append("domain_pack_not_validated")
    if artifact.get("provenance_status") != "validated":
        errors.append("provenance_not_validated")

    observations = artifact.get("shadow_observations", [])
    if not isinstance(observations, list) or not observations:
        errors.append("shadow_observations_missing")
        observations = []
    if artifact.get("shadow_observation_count") != len(observations):
        errors.append("shadow_observation_count_mismatch")
    for index, observation in enumerate(observations):
        if not isinstance(observation, dict):
            errors.append(f"shadow_observation_not_object:{index}")
            continue
        if observation.get("provenance_required") is not True:
            errors.append(f"shadow_observation_provenance_not_required:{index}")
        for key in (
            "source_quorum_credit_allowed",
            "trade_candidate_creation_allowed",
            "orderbook_depth_execution_or_venue_permission",
            "wallet_kol_company_truth_allowed",
        ):
            if observation.get(key) is not False:
                errors.append(f"shadow_observation_authority_enabled:{index}:{key}")
        if observation.get("domain_pack") == "crypto_wallets":
            if observation.get("context_role") != "risk_sentiment_only":
                errors.append(f"wallet_context_role_invalid:{index}")
            if observation.get("wallet_kol_company_truth_allowed") is not False:
                errors.append(f"wallet_company_truth_allowed:{index}")
        if observation.get("signal_class") == "orderbook_depth":
            if observation.get("context_role") != "market_context_only":
                errors.append(f"orderbook_context_role_invalid:{index}")

    active_challenges = artifact.get("active_required_challenges", [])
    if not isinstance(active_challenges, list) or not active_challenges:
        errors.append("active_required_challenges_missing")
        active_challenges = []
    challenge_text = " ".join(str(item) for item in active_challenges).lower()
    if artifact.get("context_stale") is True and "stale" not in challenge_text:
        errors.append("stale_context_without_challenge")
    if artifact.get("single_source_hold") is True and "single-source" not in challenge_text:
        errors.append("single_source_without_challenge")
    if artifact.get("missing_provenance_hold") is True and "provenance" not in challenge_text:
        errors.append("missing_provenance_without_challenge")
    if artifact.get("quota_degraded") is True and "quota" not in challenge_text:
        errors.append("quota_degraded_without_challenge")
    if "preference-only confirmation" not in challenge_text:
        errors.append("preference_only_confirmation_challenge_missing")

    for key in (
        "source_quorum_credit_allowed",
        "preference_only_confirmation_allowed",
        "orderbook_depth_execution_or_venue_permission",
        "wallet_kol_company_truth_allowed",
        "live_mcp_call_attempted",
        "search_tools_call_attempted",
        "domain_tool_call_attempted",
        "paid_tool_call_attempted",
        "trade_candidate_creation_allowed",
        "risk_handoff_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
    ):
        if artifact.get(key) is not False:
            errors.append(f"artifact_authority_enabled:{key}")

    flags = artifact.get("authority_flags", {})
    if not isinstance(flags, dict):
        errors.append("authority_flags_not_object")
    else:
        for flag in PREFERENCE_SHADOW_AUTHORITY_FLAGS:
            if flags.get(flag) is not False:
                errors.append(f"authority_flag_enabled:{flag}")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "Preference-only confirmation is a hold condition",
        "orderbook depth is market context",
        "wallet/KOL movement is sentiment and risk context",
        "cannot call live MCP domain tools",
        "create trade candidates",
    ):
        if phrase not in boundary:
            errors.append(f"boundary_missing:{phrase}")
    if _contains_secret_like_value(artifact):
        errors.append("secret_like_value_exposed")
    return errors


def preference_shadow_context_paths(settings: Settings | None = None) -> tuple[Path, Path]:
    settings = settings or Settings.from_env()
    runtime_dir = Path(settings.runtime_dir)
    return (
        runtime_dir / "preference_shadow_context.json",
        runtime_dir / "preference_shadow_context_history.jsonl",
    )


def write_preference_shadow_context(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
) -> tuple[Path, Path]:
    output_path, history_path = preference_shadow_context_paths(settings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    artifact["runtime_artifact_path"] = str(output_path)
    artifact["history_log_path"] = str(history_path)
    artifact["validation_errors"] = validate_preference_shadow_context(artifact)
    artifact["status"] = "challenge_only_ready" if not artifact["validation_errors"] else "rejected"
    output_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PREFERENCE_SHADOW_CONTEXT_SCHEMA_VERSION,
        "artifact_id": artifact.get("artifact_id"),
        "stage": artifact.get("stage"),
        "status": artifact.get("status"),
        "generated_at": artifact.get("generated_at"),
        "recorded_at": _now(),
        "context_role": artifact.get("context_role"),
        "shadow_observation_count": artifact.get("shadow_observation_count"),
        "active_required_challenge_count": artifact.get("active_required_challenge_count"),
        "quota_degraded": artifact.get("quota_degraded"),
        "validation_error_count": len(artifact.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path


def preference_shadow_packet_context(artifact: dict[str, Any]) -> dict[str, Any]:
    observations = artifact.get("shadow_observations", [])
    if not isinstance(observations, list):
        observations = []
    return {
        "source_key": artifact.get("source_key", PREFERENCE_SOURCE_KEY),
        "provider_label": artifact.get("provider_label", PREFERENCE_PROVIDER_LABEL),
        "stage": artifact.get("stage", PREFERENCE_SHADOW_CONTEXT_STAGE),
        "status": artifact.get("status", "unknown"),
        "context_role": artifact.get("context_role", PREFERENCE_SHADOW_CONTEXT_ROLE),
        "sample_context_mode": artifact.get("sample_context_mode", "deterministic_sample"),
        "shadow_observation_count": int(artifact.get("shadow_observation_count", 0) or 0),
        "observation_refs": [
            {
                "event_id": item.get("event_id"),
                "domain_pack": item.get("domain_pack"),
                "upstream_source": item.get("upstream_source"),
                "signal_class": item.get("signal_class"),
                "context_role": item.get("context_role"),
            }
            for item in observations[:6]
            if isinstance(item, dict)
        ],
        "active_required_challenges": list(artifact.get("active_required_challenges", []))[:6],
        "context_stale": bool(artifact.get("context_stale")),
        "single_source_hold": bool(artifact.get("single_source_hold")),
        "missing_provenance_hold": bool(artifact.get("missing_provenance_hold")),
        "quota_degraded": bool(artifact.get("quota_degraded")),
        "source_quorum_credit_allowed": False,
        "preference_only_confirmation_allowed": False,
        "orderbook_depth_execution_or_venue_permission": False,
        "wallet_kol_company_truth_allowed": False,
        "trade_candidate_creation_allowed": False,
        "risk_handoff_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
        "boundary": PREFERENCE_SHADOW_CONTEXT_BOUNDARY,
    }
