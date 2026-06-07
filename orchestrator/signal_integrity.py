"""Signal Integrity Gate for Phase 2 shadow intelligence.

The gate audits shadow signals before they can ever be considered by a future
Risk Agent. It can block or hold weak signals, and it can mark a signal as
ready for risk-review shadowing, but it cannot create trade candidates or
approve paper/live orders.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.intelligence import ShadowSignalStore, run_shadow_intelligence_sample

SIGNAL_INTEGRITY_SCHEMA_VERSION = 6
SIGNAL_INTEGRITY_FUNNEL_DIAGNOSTICS_SCHEMA_VERSION = 2
SIGNAL_INTEGRITY_STATUSES = {"blocked", "hold_for_corroboration", "passed_to_risk_shadow"}
MARKET_CONFIRMATION_MAX_AGE = timedelta(hours=48)
MARKET_CONFIRMATION_EVENT_TYPE = "market_price_confirmation"
YAHOO_FINANCE_SOURCE = "market.yahoo_finance"
PREFERENCE_MCP_SOURCE = "supplemental.preference_mcp"
TRADINGVIEW_MCP_SOURCE = "market.tradingview_mcp"
TRADINGVIEW_MCP_EVENT_TYPE = "technical_analysis_context"
PRICING_GAP_EVENT_TYPES = {"pricing_gap_assumption", "transaction_cost_assumption"}
# Legacy text markers are fallback-only for older signals that predate
# structured pricing-gap evidence items.
PRICING_GAP_CONFIRMATION_MARKERS = (
    "pricing gap confirmed",
    "pass_pricing_gap_confirmed",
    "transaction-cost assumptions confirmed",
    "transaction cost assumptions confirmed",
    "spread and slippage assumptions confirmed",
)
PREFERENCE_CONTEXT_MARKERS = (
    "preference mcp",
    "preference_mcp",
    "preference-only confirmation",
    "orderbook depth is market context",
    "wallet/kol movement",
)
TRADINGVIEW_MCP_CONTEXT_MARKERS = (
    "tradingview mcp",
    "tradingview_mcp",
    "technical context is supplemental",
    "technical analysis context",
    "support/resistance",
)
SIGNAL_INTEGRITY_FUNNEL_DIAGNOSTICS_RUNTIME_ARTIFACT = (
    "signal_integrity_funnel_diagnostics.json"
)
PHASE5_RISK_SIZING_RUNTIME_ARTIFACT = "phase5_risk_sizing_reviews.json"
PRICING_GAP_POLICY_TIERS = {"required_strict", "required_light", "not_required"}
PRICING_GAP_ROLLOUT_STAGES = {"stage_a", "stage_b"}
INSTRUMENT_FOCUS_PRICING_GAP_POLICY_TIER = {
    "prediction_markets": "not_required",
    "crude_oil": "required_light",
    "defence": "required_light",
    "silver": "required_light",
    "semiconductors": "required_strict",
}
PRICING_GAP_ONLY_RISK_BLOCKER_PREFIX = "signal_pricing_gap_"


@dataclass(frozen=True)
class SignalIntegrityReview:
    schema_version: int
    review_id: str
    source_signal_id: str
    status: str
    instrument_focus: str
    integrity_score: float
    source_count: int
    evidence_item_count: int
    average_trust_score: float
    min_trust_score: float
    signal_confidence: float
    missing_correlations: tuple[str, ...]
    akber_filter: dict[str, str]
    market_confirmation_policy: dict[str, Any]
    preference_context_policy: dict[str, Any]
    technical_context_policy: dict[str, Any]
    failure_reasons: tuple[str, ...]
    required_next_steps: tuple[str, ...]
    worldview_prior_status: str
    execution_allowed: bool
    paper_order_allowed: bool
    trade_candidate_created: bool
    reviewed_at: str
    boundary: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["missing_correlations"] = list(self.missing_correlations)
        payload["failure_reasons"] = list(self.failure_reasons)
        payload["required_next_steps"] = list(self.required_next_steps)
        return payload


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _signal_trail(signal: dict[str, Any]) -> dict[str, Any]:
    trail = signal.get("evidence_trail", {})
    return trail if isinstance(trail, dict) else {}


def _missing_correlations(trail: dict[str, Any]) -> tuple[str, ...]:
    missing = trail.get("missing_correlations", [])
    if not isinstance(missing, list):
        return ()
    return tuple(str(item).strip() for item in missing if str(item).strip())[:8]


def _evidence_item_count(trail: dict[str, Any]) -> int:
    items = trail.get("evidence_items", [])
    return len(items) if isinstance(items, list) else 0


def _evidence_items(trail: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    items = trail.get("evidence_items", [])
    if not isinstance(items, list):
        return ()
    return tuple(item for item in items if isinstance(item, dict))


def _parse_observed_at(value: Any) -> datetime | None:
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


def _is_market_confirmation_item(item: dict[str, Any]) -> bool:
    source = str(item.get("source") or "").lower()
    event_type = str(item.get("event_type") or "").lower()
    summary = str(item.get("summary") or "").lower()
    return (
        event_type == MARKET_CONFIRMATION_EVENT_TYPE
        or YAHOO_FINANCE_SOURCE in source
        or YAHOO_FINANCE_SOURCE in summary
    )


def _pricing_gap_policy_tier_for_signal(signal: dict[str, Any]) -> str:
    instrument_focus = str(signal.get("instrument_focus") or "").strip()
    return INSTRUMENT_FOCUS_PRICING_GAP_POLICY_TIER.get(
        instrument_focus,
        "required_light",
    )


def _pricing_gap_rollout_stage_for_signal(signal: dict[str, Any]) -> str:
    stage = str(
        signal.get("pricing_gap_rollout_stage")
        or Settings.from_env().pricing_gap_rollout_stage
        or "stage_a"
    ).strip().lower()
    if stage not in PRICING_GAP_ROLLOUT_STAGES:
        return "stage_a"
    return stage


def _pricing_gap_status_is_satisfied(pricing_gap_status: str) -> bool:
    return pricing_gap_status in {
        "pass_pricing_gap_confirmed",
        "pass_pricing_gap_transaction_cost_only",
        "pass_pricing_gap_not_required",
    }


def _pricing_gap_policy(
    items: tuple[dict[str, Any], ...],
    *,
    market_confirmation_status: str,
    pricing_gap_policy_tier: str,
    pricing_gap_rollout_stage: str,
) -> dict[str, Any]:
    if pricing_gap_policy_tier not in PRICING_GAP_POLICY_TIERS:
        pricing_gap_policy_tier = "required_light"
    if pricing_gap_rollout_stage not in PRICING_GAP_ROLLOUT_STAGES:
        pricing_gap_rollout_stage = "stage_a"
    explicit_event = _signal_has_pricing_gap_event(items)
    transaction_cost_present = _signal_has_transaction_cost_event(items)
    explicit_marker = _signal_has_pricing_gap_marker(items)
    legacy_marker_fallback = False
    relaxed_policy_enabled = pricing_gap_rollout_stage == "stage_b"
    relaxed_candidate = (
        pricing_gap_policy_tier == "not_required"
        or (pricing_gap_policy_tier == "required_light" and transaction_cost_present)
    )
    if explicit_event:
        detailed_status = "pass_pricing_gap_confirmed"
        failure_reason = None
        result = "confirmed"
        confirmation_source = "structured_event"
    elif not explicit_event and explicit_marker:
        detailed_status = "pass_pricing_gap_confirmed"
        failure_reason = None
        result = "confirmed"
        confirmation_source = "legacy_summary_marker"
        legacy_marker_fallback = True
    elif (
        relaxed_policy_enabled
        and pricing_gap_policy_tier == "required_light"
        and transaction_cost_present
    ):
        detailed_status = "pass_pricing_gap_transaction_cost_only"
        failure_reason = None
        result = "confirmed_light"
        confirmation_source = "structured_transaction_cost_event"
    elif relaxed_policy_enabled and pricing_gap_policy_tier == "not_required":
        detailed_status = "pass_pricing_gap_not_required"
        failure_reason = None
        result = "not_required"
        confirmation_source = "not_required_by_policy"
    elif relaxed_candidate and not relaxed_policy_enabled:
        detailed_status = "pricing_gap_rollout_stage_a_strict_hold"
        failure_reason = "pricing_gap_rollout_stage_a_strict_hold"
        result = "held_pending_stage_b"
        confirmation_source = "rollout_stage_a_strict"
    elif market_confirmation_status == "market_confirmation_unavailable":
        detailed_status = "pricing_gap_unavailable_market_confirmation_unavailable"
        failure_reason = "pricing_gap_unavailable_market_confirmation_unavailable"
        result = "unavailable"
        confirmation_source = "missing"
    elif market_confirmation_status == "market_confirmation_stale":
        detailed_status = "pricing_gap_unavailable_market_confirmation_stale"
        failure_reason = "pricing_gap_unavailable_market_confirmation_stale"
        result = "unavailable"
        confirmation_source = "missing"
    elif market_confirmation_status == "market_confirmation_single_source_hold":
        detailed_status = "pricing_gap_unavailable_single_source_hold"
        failure_reason = "pricing_gap_unavailable_single_source_hold"
        result = "unavailable"
        confirmation_source = "missing"
    else:
        detailed_status = "pricing_gap_unavailable_not_modeled"
        failure_reason = "pricing_gap_unavailable_not_modeled"
        result = "unavailable"
        confirmation_source = "missing"
    return {
        "pricing_gap": (
            detailed_status if _pricing_gap_status_is_satisfied(detailed_status) else "hold_pricing_gap_required"
        ),
        "pricing_gap_status": detailed_status,
        "pricing_gap_result": result,
        "pricing_gap_policy_tier": pricing_gap_policy_tier,
        "pricing_gap_rollout_stage": pricing_gap_rollout_stage,
        "pricing_gap_relaxed_policy_enabled": relaxed_policy_enabled,
        "pricing_gap_relaxed_candidate": relaxed_candidate,
        "pricing_gap_confirmation_source": confirmation_source,
        "pricing_gap_event_present": explicit_event,
        "transaction_cost_event_present": transaction_cost_present,
        "pricing_gap_marker_present": explicit_marker,
        "pricing_gap_legacy_marker_fallback_used": legacy_marker_fallback,
        "pricing_gap_failure_reason": failure_reason,
        "pricing_gap_signal_invalid": False,
    }


def _market_confirmation_policy(
    *,
    signal: dict[str, Any],
    trail: dict[str, Any],
    source_count: int,
) -> dict[str, Any]:
    items = _evidence_items(trail)
    market_items = tuple(item for item in items if _is_market_confirmation_item(item))
    providers = sorted(
        {
            str(item.get("source") or "unknown_market_source")[:80]
            for item in market_items
            if str(item.get("source") or "").strip()
        }
    )
    provider_text = " ".join(providers).lower()
    summary_text = " ".join(str(item.get("summary") or "") for item in market_items).lower()
    uses_yahoo = YAHOO_FINANCE_SOURCE in provider_text or YAHOO_FINANCE_SOURCE in summary_text
    unavailable = not market_items or any(
        token in summary_text
        for token in (
            "disabled",
            "degraded",
            "missing_dependency",
            "market_confirmation_unavailable",
            "unavailable",
        )
    )

    observed_times = tuple(
        parsed
        for item in market_items
        if (parsed := _parse_observed_at(item.get("observed_at"))) is not None
    )
    latest_observed_at = max(observed_times).isoformat() if observed_times else None
    stale = bool(observed_times) and max(observed_times) < datetime.now(timezone.utc) - MARKET_CONFIRMATION_MAX_AGE

    if unavailable:
        status = "market_confirmation_unavailable"
    elif stale:
        status = "market_confirmation_stale"
    elif source_count < 2:
        status = "market_confirmation_single_source_hold"
    else:
        status = "market_confirmation_corroboration_available"

    pricing_gap_policy = _pricing_gap_policy(
        items,
        market_confirmation_status=status,
        pricing_gap_policy_tier=_pricing_gap_policy_tier_for_signal(signal),
        pricing_gap_rollout_stage=_pricing_gap_rollout_stage_for_signal(signal),
    )
    return {
        "status": status,
        "market_price_confirmation": (
            "pass_supplemental_corroboration"
            if status == "market_confirmation_corroboration_available"
            else f"hold_{status}"
        ),
        "providers": providers,
        "uses_yahoo_finance": uses_yahoo,
        "single_source_hold": source_count < 2,
        "stale": stale,
        "unavailable": unavailable,
        "latest_observed_at": latest_observed_at,
        "max_age_seconds": int(MARKET_CONFIRMATION_MAX_AGE.total_seconds()),
        "signal_authority": False,
        "order_authority": False,
        "broker_reconciliation_authority": False,
        "boundary": (
            "Market confirmation is supplemental corroboration only. Yahoo Finance can inform price "
            "context but cannot create signals, orders, fills, receipts, or reconciliation truth."
        ),
        **pricing_gap_policy,
    }


def _is_preference_context_item(item: dict[str, Any]) -> bool:
    source = str(item.get("source") or "").lower()
    event_type = str(item.get("event_type") or "").lower()
    summary = str(item.get("summary") or "").lower()
    return (
        PREFERENCE_MCP_SOURCE in source
        or "preference" in event_type
        or any(marker in summary for marker in PREFERENCE_CONTEXT_MARKERS)
    )


def _preference_context_policy(
    *,
    trail: dict[str, Any],
    source_count: int,
) -> dict[str, Any]:
    items = _evidence_items(trail)
    preference_items = tuple(item for item in items if _is_preference_context_item(item))
    summary_text = " ".join(str(item.get("summary") or "") for item in preference_items).lower()
    preference_context_present = bool(preference_items)
    missing_provenance = "missing provenance" in summary_text or "invalid provenance" in summary_text
    stale = "stale" in summary_text
    quota_degraded = "quota" in summary_text or "non-anonymous preference identity" in summary_text
    preference_only_hold = preference_context_present and source_count < 2

    if not preference_context_present:
        status = "preference_context_absent"
    elif missing_provenance:
        status = "preference_context_missing_provenance_hold"
    elif stale:
        status = "preference_context_stale_hold"
    elif preference_only_hold:
        status = "preference_only_confirmation_hold"
    elif quota_degraded:
        status = "preference_context_quota_degraded_hold"
    else:
        status = "preference_context_challenge_only"

    return {
        "status": status,
        "preference_context_present": preference_context_present,
        "preference_item_count": len(preference_items),
        "preference_only_confirmation_hold": preference_only_hold,
        "missing_provenance_hold": missing_provenance,
        "context_stale_hold": stale,
        "quota_degraded_hold": quota_degraded,
        "source_quorum_credit_allowed": False,
        "preference_only_confirmation_allowed": False,
        "orderbook_depth_role": "market_context_only",
        "orderbook_depth_execution_or_venue_permission": False,
        "wallet_kol_role": "risk_sentiment_only",
        "wallet_kol_company_truth_allowed": False,
        "signal_authority": False,
        "trade_candidate_creation_allowed": False,
        "risk_handoff_allowed": False,
        "order_authority": False,
        "broker_reconciliation_authority": False,
        "boundary": (
            "Preference context can challenge a shadow signal only. Preference-only "
            "confirmation is a hold condition; orderbook depth is not execution or "
            "venue permission; wallet/KOL movement is not factual corporate evidence."
        ),
    }


def _is_technical_context_item(item: dict[str, Any]) -> bool:
    source = str(item.get("source") or "").lower()
    event_type = str(item.get("event_type") or "").lower()
    summary = str(item.get("summary") or "").lower()
    return (
        TRADINGVIEW_MCP_SOURCE in source
        or event_type == TRADINGVIEW_MCP_EVENT_TYPE
        or any(marker in summary for marker in TRADINGVIEW_MCP_CONTEXT_MARKERS)
    )


def _technical_context_policy(
    *,
    trail: dict[str, Any],
    source_count: int,
) -> dict[str, Any]:
    items = _evidence_items(trail)
    technical_items = tuple(item for item in items if _is_technical_context_item(item))
    summary_text = " ".join(str(item.get("summary") or "") for item in technical_items).lower()
    present = bool(technical_items)
    stale = "stale" in summary_text
    technical_only_hold = present and source_count < 2
    if not present:
        status = "technical_context_absent"
    elif stale:
        status = "technical_context_stale_hold"
    elif technical_only_hold:
        status = "tradingview_mcp_context_only_hold"
    else:
        status = "supplemental_technical_confirmation_available"
    return {
        "status": status,
        "technical_context_present": present,
        "technical_item_count": len(technical_items),
        "tradingview_mcp_context_only_hold": technical_only_hold,
        "context_stale_hold": stale,
        "source_quorum_credit_allowed": False,
        "technical_context_only_confirmation_allowed": False,
        "signal_authority": False,
        "trade_candidate_creation_allowed": False,
        "risk_handoff_allowed": False,
        "order_authority": False,
        "paper_order_authority": False,
        "broker_write_authority": False,
        "live_capital_authority": False,
        "boundary": (
            "TradingView MCP technical context can corroborate technical setup only. "
            "It cannot satisfy source quorum, create trade candidates, create paper "
            "orders, write to brokers, or enable live capital."
        ),
    }


def _akber_filter(
    *,
    evidence_item_count: int,
    source_count: int,
    missing: tuple[str, ...],
    average_trust_score: float,
    market_policy: dict[str, Any],
    technical_policy: dict[str, Any],
) -> dict[str, str]:
    catalyst = "pass" if evidence_item_count > 0 and average_trust_score >= 0.5 else "fail_missing_trusted_catalyst"
    return {
        "low_volatility": "missing_volatility_context",
        "options_distribution_gap": str(market_policy["pricing_gap"]),
        "catalyst_identification": catalyst,
        "technical_setup": (
            "supplemental_technical_confirmation_available"
            if technical_policy["status"] == "supplemental_technical_confirmation_available"
            else "missing_market_price_confirmation"
            if "market_price_confirmation" in missing
            or source_count < 2
            or market_policy["status"] != "market_confirmation_corroboration_available"
            else "shadow_pass"
        ),
        "obv_volume": "missing_volume_confirmation",
        "approval_policy": "not_reached_risk_agent_absent",
    }


def _failure_reasons(
    *,
    evidence_item_count: int,
    source_count: int,
    average_trust_score: float,
    min_trust_score: float,
    signal_confidence: float,
    missing: tuple[str, ...],
    market_policy: dict[str, Any],
    preference_policy: dict[str, Any],
    technical_policy: dict[str, Any],
) -> tuple[str, ...]:
    reasons: list[str] = []
    if evidence_item_count < 1:
        reasons.append("missing_evidence_items")
    if source_count < 2:
        reasons.append("second_independent_source_required")
    if average_trust_score < 0.6:
        reasons.append("average_trust_score_below_gate")
    if min_trust_score < 0.5:
        reasons.append("minimum_trust_score_below_gate")
    if signal_confidence < 0.45:
        reasons.append("signal_confidence_below_gate")
    if market_policy["status"] != "market_confirmation_corroboration_available":
        reasons.append(str(market_policy["status"]))
    if preference_policy["status"] in {
        "preference_only_confirmation_hold",
        "preference_context_missing_provenance_hold",
        "preference_context_stale_hold",
        "preference_context_quota_degraded_hold",
    }:
        reasons.append(str(preference_policy["status"]))
    if technical_policy["status"] in {
        "tradingview_mcp_context_only_hold",
        "technical_context_stale_hold",
    }:
        reasons.append(str(technical_policy["status"]))
    if not _pricing_gap_status_is_satisfied(str(market_policy.get("pricing_gap_status") or "")):
        detailed_pricing_gap_reason = str(market_policy.get("pricing_gap_failure_reason") or "").strip()
        if detailed_pricing_gap_reason:
            reasons.append(detailed_pricing_gap_reason)
        reasons.append("missing_pricing_gap")
    reasons.extend(missing)
    return tuple(dict.fromkeys(reasons))[:10]


def _integrity_score(
    *,
    source_count: int,
    evidence_item_count: int,
    average_trust_score: float,
    signal_confidence: float,
    missing: tuple[str, ...],
) -> float:
    score = (
        average_trust_score * 0.35
        + min(1.0, signal_confidence) * 0.2
        + min(1.0, source_count / 3) * 0.2
        + min(1.0, evidence_item_count / 5) * 0.1
        + (0.15 if not missing else 0.0)
        - min(0.25, len(missing) * 0.06)
    )
    return round(max(0.0, min(1.0, score)), 3)


def _review_status(
    *,
    evidence_item_count: int,
    source_count: int,
    average_trust_score: float,
    min_trust_score: float,
    signal_confidence: float,
    missing: tuple[str, ...],
    market_policy: dict[str, Any],
    preference_policy: dict[str, Any],
    technical_policy: dict[str, Any],
) -> str:
    preference_hold_status = preference_policy["status"] in {
        "preference_only_confirmation_hold",
        "preference_context_missing_provenance_hold",
        "preference_context_stale_hold",
        "preference_context_quota_degraded_hold",
    }
    pricing_gap_satisfied = _pricing_gap_status_is_satisfied(
        str(market_policy.get("pricing_gap_status") or "")
    )
    if evidence_item_count < 1 or min_trust_score < 0.5 or signal_confidence < 0.45:
        return "blocked"
    if (
        source_count < 2
        or missing
        or average_trust_score < 0.65
        or market_policy["status"] != "market_confirmation_corroboration_available"
        or not pricing_gap_satisfied
        or preference_hold_status
        or technical_policy["status"]
        in {"tradingview_mcp_context_only_hold", "technical_context_stale_hold"}
    ):
        return "hold_for_corroboration"
    return "passed_to_risk_shadow"


def _next_steps(status: str, failure_reasons: tuple[str, ...]) -> tuple[str, ...]:
    steps: list[str] = []
    if "second_independent_source_required" in failure_reasons:
        steps.append("Add a second independent source before any Strategy or Risk review.")
    if "market_price_confirmation" in failure_reasons:
        steps.append("Add market price or probability confirmation.")
    if "market_confirmation_unavailable" in failure_reasons:
        steps.append("Attach a current market confirmation source before risk review.")
    if "market_confirmation_stale" in failure_reasons:
        steps.append("Refresh market confirmation before risk review.")
    if "market_confirmation_single_source_hold" in failure_reasons:
        steps.append("Add non-Yahoo independent corroboration; Yahoo Finance cannot move a signal alone.")
    if "preference_only_confirmation_hold" in failure_reasons:
        steps.append("Add canonical non-Preference corroboration; Preference-only context is a hold.")
    if "preference_context_missing_provenance_hold" in failure_reasons:
        steps.append("Reject or refresh Preference context with missing provenance.")
    if "preference_context_stale_hold" in failure_reasons:
        steps.append("Refresh Preference context before Strategy Lead review.")
    if "preference_context_quota_degraded_hold" in failure_reasons:
        steps.append("Verify Preference identity and quota before live Preference use.")
    if "tradingview_mcp_context_only_hold" in failure_reasons:
        steps.append("Add canonical non-TradingView corroboration; technical context alone is a hold.")
    if "technical_context_stale_hold" in failure_reasons:
        steps.append("Refresh TradingView MCP technical context before Strategy Lead review.")
    if "maritime_confirmation" in failure_reasons:
        steps.append("Add maritime, logistics, or vessel confirmation.")
    if "pricing_gap_unavailable_market_confirmation_unavailable" in failure_reasons:
        steps.append("Attach current market confirmation before modeling pricing-gap assumptions.")
    if "pricing_gap_unavailable_market_confirmation_stale" in failure_reasons:
        steps.append("Refresh market confirmation, then refresh pricing-gap assumptions.")
    if "pricing_gap_unavailable_single_source_hold" in failure_reasons:
        steps.append("Add a second independent market source before treating pricing-gap assumptions as usable.")
    if "pricing_gap_unavailable_not_modeled" in failure_reasons:
        steps.append("Attach explicit pricing-gap and transaction-cost assumptions to the evidence trail.")
    if "pricing_gap_rollout_stage_a_strict_hold" in failure_reasons:
        steps.append("Stage A strict rollout is active; keep structured evidence visible and wait for Stage B enablement.")
    if "missing_pricing_gap" in failure_reasons:
        steps.append("Attach pricing-gap and transaction-cost assumptions.")
    steps.append("Keep Risk Agent and broker-write routes blocked until later phases.")
    return tuple(dict.fromkeys(steps))[:6]


def validate_signal_integrity_review(review: SignalIntegrityReview) -> None:
    if review.schema_version != SIGNAL_INTEGRITY_SCHEMA_VERSION:
        raise ValueError("signal integrity review schema version mismatch")
    if review.status not in SIGNAL_INTEGRITY_STATUSES:
        raise ValueError(f"invalid signal integrity status: {review.status}")
    if review.execution_allowed:
        raise ValueError("Signal Integrity Gate cannot allow execution")
    if review.paper_order_allowed:
        raise ValueError("Signal Integrity Gate cannot allow paper orders")
    if review.trade_candidate_created:
        raise ValueError("Signal Integrity Gate cannot create trade candidates")
    if review.market_confirmation_policy.get("signal_authority") is not False:
        raise ValueError("market confirmation cannot create signal authority")
    if review.market_confirmation_policy.get("order_authority") is not False:
        raise ValueError("market confirmation cannot create order authority")
    if review.market_confirmation_policy.get("broker_reconciliation_authority") is not False:
        raise ValueError("market confirmation cannot create broker reconciliation authority")
    if review.preference_context_policy.get("source_quorum_credit_allowed") is not False:
        raise ValueError("Preference context cannot satisfy source quorum")
    if review.preference_context_policy.get("preference_only_confirmation_allowed") is not False:
        raise ValueError("Preference-only confirmation cannot pass Signal Integrity")
    if review.preference_context_policy.get("orderbook_depth_execution_or_venue_permission") is not False:
        raise ValueError("Preference orderbook depth cannot grant venue or execution permission")
    if review.preference_context_policy.get("wallet_kol_company_truth_allowed") is not False:
        raise ValueError("Preference wallet/KOL movement cannot be company truth")
    for key in (
        "signal_authority",
        "trade_candidate_creation_allowed",
        "risk_handoff_allowed",
        "order_authority",
        "broker_reconciliation_authority",
    ):
        if review.preference_context_policy.get(key) is not False:
            raise ValueError(f"Preference context policy authority enabled: {key}")
    if review.technical_context_policy.get("source_quorum_credit_allowed") is not False:
        raise ValueError("TradingView MCP context cannot satisfy source quorum")
    if review.technical_context_policy.get("technical_context_only_confirmation_allowed") is not False:
        raise ValueError("TradingView MCP-only confirmation cannot pass Signal Integrity")
    for key in (
        "signal_authority",
        "trade_candidate_creation_allowed",
        "risk_handoff_allowed",
        "order_authority",
        "paper_order_authority",
        "broker_write_authority",
        "live_capital_authority",
    ):
        if review.technical_context_policy.get(key) is not False:
            raise ValueError(f"TradingView MCP technical context authority enabled: {key}")
    if not 0 <= review.integrity_score <= 1:
        raise ValueError("signal integrity score must be between 0 and 1")


def build_signal_integrity_review(signal: dict[str, Any]) -> SignalIntegrityReview:
    trail = _signal_trail(signal)
    missing = _missing_correlations(trail)
    evidence_item_count = _evidence_item_count(trail)
    source_count = int(_float(trail.get("source_count"), 0))
    average_trust_score = round(_float(trail.get("average_trust_score"), 0), 3)
    min_trust_score = round(_float(trail.get("min_trust_score"), 0), 3)
    signal_confidence = round(_float(signal.get("confidence"), 0), 3)
    market_policy = _market_confirmation_policy(signal=signal, trail=trail, source_count=source_count)
    preference_policy = _preference_context_policy(trail=trail, source_count=source_count)
    technical_policy = _technical_context_policy(trail=trail, source_count=source_count)
    status = _review_status(
        evidence_item_count=evidence_item_count,
        source_count=source_count,
        average_trust_score=average_trust_score,
        min_trust_score=min_trust_score,
        signal_confidence=signal_confidence,
        missing=missing,
        market_policy=market_policy,
        preference_policy=preference_policy,
        technical_policy=technical_policy,
    )
    failures = _failure_reasons(
        evidence_item_count=evidence_item_count,
        source_count=source_count,
        average_trust_score=average_trust_score,
        min_trust_score=min_trust_score,
        signal_confidence=signal_confidence,
        missing=missing,
        market_policy=market_policy,
        preference_policy=preference_policy,
        technical_policy=technical_policy,
    )
    review = SignalIntegrityReview(
        schema_version=SIGNAL_INTEGRITY_SCHEMA_VERSION,
        review_id=str(uuid4()),
        source_signal_id=str(signal.get("signal_id") or "unknown_signal"),
        status=status,
        instrument_focus=str(signal.get("instrument_focus") or "macro_watchlist")[:120],
        integrity_score=_integrity_score(
            source_count=source_count,
            evidence_item_count=evidence_item_count,
            average_trust_score=average_trust_score,
            signal_confidence=signal_confidence,
            missing=missing,
        ),
        source_count=source_count,
        evidence_item_count=evidence_item_count,
        average_trust_score=average_trust_score,
        min_trust_score=min_trust_score,
        signal_confidence=signal_confidence,
        missing_correlations=missing,
        akber_filter=_akber_filter(
            evidence_item_count=evidence_item_count,
            source_count=source_count,
            missing=missing,
            average_trust_score=average_trust_score,
            market_policy=market_policy,
            technical_policy=technical_policy,
        ),
        market_confirmation_policy=market_policy,
        preference_context_policy=preference_policy,
        technical_context_policy=technical_policy,
        failure_reasons=failures,
        required_next_steps=_next_steps(status, failures),
        worldview_prior_status="private_prior_only_not_evidence",
        execution_allowed=False,
        paper_order_allowed=False,
        trade_candidate_created=False,
        reviewed_at=_now(),
        boundary=(
            "Signal Integrity Gate can block or hold shadow signals only. It cannot approve "
            "risk, create trade candidates, create paper orders, or access broker writes."
        ),
    )
    validate_signal_integrity_review(review)
    return review


class SignalIntegrityReviewStore:
    def __init__(self, path: str | Path | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self.path = Path(path or Path(self.settings.runtime_dir) / "signal_integrity_reviews.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, review: SignalIntegrityReview, *, event_log: EventLog | None = None) -> SignalIntegrityReview:
        validate_signal_integrity_review(review)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(review.to_dict(), sort_keys=True) + "\n")
        (event_log or EventLog(echo=False)).write(
            "signal_integrity_review_recorded",
            "signal_integrity",
            {
                "review_id": review.review_id,
                "source_signal_id": review.source_signal_id,
                "status": review.status,
                "integrity_score": review.integrity_score,
                "execution_allowed": review.execution_allowed,
                "paper_order_allowed": review.paper_order_allowed,
                "trade_candidate_created": review.trade_candidate_created,
            },
        )
        return review

    def read(self, limit: int | None = None) -> tuple[dict[str, Any], ...]:
        if not self.path.exists():
            return ()
        reviews: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    loaded = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid signal integrity review line {line_number} in {self.path}") from exc
                if isinstance(loaded, dict):
                    reviews.append(loaded)
        if limit is not None:
            reviews = reviews[-limit:]
        return tuple(reviews)

    def health(self) -> dict[str, Any]:
        try:
            reviews = self.read()
        except Exception as exc:  # noqa: BLE001 - health should report the failure.
            return {
                "status": "degraded",
                "schema_version": SIGNAL_INTEGRITY_SCHEMA_VERSION,
                "error": str(exc),
            }
        counts = Counter(str(review.get("status", "unknown")) for review in reviews)
        return {
            "status": "ok",
            "schema_version": SIGNAL_INTEGRITY_SCHEMA_VERSION,
            "review_count": len(reviews),
            "by_status": dict(sorted(counts.items())),
            "execution_allowed_count": sum(1 for review in reviews if review.get("execution_allowed") is True),
            "paper_order_allowed_count": sum(1 for review in reviews if review.get("paper_order_allowed") is True),
            "trade_candidate_created_count": sum(1 for review in reviews if review.get("trade_candidate_created") is True),
            "boundary": (
                "Signal Integrity Gate reviews are non-executable. They can block or hold, "
                "but cannot create candidates or orders."
            ),
        }


def signal_integrity_funnel_diagnostics_path(
    settings: Settings | None = None,
) -> Path:
    settings = settings or Settings.from_env()
    return Path(settings.runtime_dir) / SIGNAL_INTEGRITY_FUNNEL_DIAGNOSTICS_RUNTIME_ARTIFACT


def _runtime_json_artifact(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _phase5_risk_sizing_runtime_artifact(settings: Settings) -> dict[str, Any]:
    return _runtime_json_artifact(Path(settings.runtime_dir) / PHASE5_RISK_SIZING_RUNTIME_ARTIFACT)


def _signal_generated_by(signal: dict[str, Any]) -> str:
    return str(signal.get("generated_by") or "unknown_generator")[:120]


def _signal_items(signal: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    return _evidence_items(_signal_trail(signal))


def _signal_has_pricing_gap_event(items: tuple[dict[str, Any], ...]) -> bool:
    return any(
        str(item.get("event_type") or "").lower() == "pricing_gap_assumption"
        for item in items
    )


def _signal_has_transaction_cost_event(items: tuple[dict[str, Any], ...]) -> bool:
    return any(
        str(item.get("event_type") or "").lower() == "transaction_cost_assumption"
        for item in items
    )


def _signal_has_pricing_gap_marker(items: tuple[dict[str, Any], ...]) -> bool:
    summary_text = " ".join(str(item.get("summary") or "") for item in items).lower()
    return any(marker in summary_text for marker in PRICING_GAP_CONFIRMATION_MARKERS)


def _latest_reviews_by_signal_id(
    reviews: tuple[dict[str, Any], ...],
) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for review in reviews:
        signal_id = str(review.get("source_signal_id") or "").strip()
        if signal_id:
            latest[signal_id] = review
    return latest


def _producer_summary(
    *,
    generated_by: str,
    signals: list[dict[str, Any]],
    latest_reviews: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    producer_signals = [signal for signal in signals if _signal_generated_by(signal) == generated_by]
    review_status_counts: Counter[str] = Counter()
    instrument_focuses: Counter[str] = Counter()
    market_confirmation_signal_count = 0
    pricing_gap_event_signal_count = 0
    transaction_cost_event_signal_count = 0
    pricing_gap_marker_signal_count = 0
    pricing_gap_confirmed_signal_count = 0
    pricing_gap_confirmed_structured_signal_count = 0
    pricing_gap_confirmed_legacy_fallback_signal_count = 0
    hold_missing_pricing_gap_count = 0
    latest_signal_created_at = ""

    for signal in producer_signals:
        instrument_focuses[str(signal.get("instrument_focus") or "unknown_focus")] += 1
        latest_signal_created_at = max(
            latest_signal_created_at,
            str(signal.get("created_at") or ""),
        )
        items = _signal_items(signal)
        has_market_confirmation = bool(tuple(item for item in items if _is_market_confirmation_item(item)))
        has_pricing_gap_event = _signal_has_pricing_gap_event(items)
        has_transaction_cost_event = _signal_has_transaction_cost_event(items)
        has_pricing_gap_marker = _signal_has_pricing_gap_marker(items)
        if has_market_confirmation:
            market_confirmation_signal_count += 1
        if has_pricing_gap_event:
            pricing_gap_event_signal_count += 1
        if has_transaction_cost_event:
            transaction_cost_event_signal_count += 1
        if has_pricing_gap_marker:
            pricing_gap_marker_signal_count += 1
        signal_pricing_gap_policy = _pricing_gap_policy(
            items,
            market_confirmation_status=(
                "market_confirmation_corroboration_available"
                if has_market_confirmation
                else "market_confirmation_unavailable"
            ),
            pricing_gap_policy_tier=_pricing_gap_policy_tier_for_signal(signal),
            pricing_gap_rollout_stage=_pricing_gap_rollout_stage_for_signal(signal),
        )
        if _pricing_gap_status_is_satisfied(
            str(signal_pricing_gap_policy.get("pricing_gap_status") or "")
        ):
            pricing_gap_confirmed_signal_count += 1
            if signal_pricing_gap_policy["pricing_gap_confirmation_source"] == "structured_event":
                pricing_gap_confirmed_structured_signal_count += 1
            if signal_pricing_gap_policy["pricing_gap_confirmation_source"] == "structured_transaction_cost_event":
                pricing_gap_confirmed_structured_signal_count += 1
            if signal_pricing_gap_policy["pricing_gap_confirmation_source"] == "legacy_summary_marker":
                pricing_gap_confirmed_legacy_fallback_signal_count += 1

        review = latest_reviews.get(str(signal.get("signal_id") or ""), {})
        status = str(review.get("status") or "missing_review")
        review_status_counts[status] += 1
        failure_reasons = review.get("failure_reasons", [])
        if (
            status == "hold_for_corroboration"
            and isinstance(failure_reasons, list)
            and "missing_pricing_gap" in failure_reasons
        ):
            hold_missing_pricing_gap_count += 1

    return {
        "generated_by": generated_by,
        "signal_count": len(producer_signals),
        "instrument_focuses": dict(sorted(instrument_focuses.items())),
        "latest_signal_created_at": latest_signal_created_at or None,
        "market_confirmation_signal_count": market_confirmation_signal_count,
        "pricing_gap_event_signal_count": pricing_gap_event_signal_count,
        "transaction_cost_event_signal_count": transaction_cost_event_signal_count,
        "pricing_gap_marker_signal_count": pricing_gap_marker_signal_count,
        "pricing_gap_confirmed_signal_count": pricing_gap_confirmed_signal_count,
        "pricing_gap_confirmed_structured_signal_count": pricing_gap_confirmed_structured_signal_count,
        "pricing_gap_confirmed_legacy_fallback_signal_count": (
            pricing_gap_confirmed_legacy_fallback_signal_count
        ),
        "review_status_counts": dict(sorted(review_status_counts.items())),
        "hold_missing_pricing_gap_count": hold_missing_pricing_gap_count,
        "likely_missing_pricing_gap_producer": (
            market_confirmation_signal_count > 0
            and pricing_gap_confirmed_signal_count == 0
            and hold_missing_pricing_gap_count > 0
        ),
    }


def build_signal_integrity_funnel_diagnostics(
    *,
    settings: Settings | None = None,
    signal_store: ShadowSignalStore | None = None,
    review_store: SignalIntegrityReviewStore | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    signal_store = signal_store or ShadowSignalStore(settings=settings)
    review_store = review_store or SignalIntegrityReviewStore(settings=settings)
    signals = list(signal_store.read())
    reviews = review_store.read()
    latest_reviews = _latest_reviews_by_signal_id(reviews)
    risk_sizing_bundle = _phase5_risk_sizing_runtime_artifact(settings)
    rollout_stage = (
        settings.pricing_gap_rollout_stage
        if settings.pricing_gap_rollout_stage in PRICING_GAP_ROLLOUT_STAGES
        else "stage_a"
    )
    generated_bys = sorted({_signal_generated_by(signal) for signal in signals})
    producer_summaries = [
        _producer_summary(
            generated_by=generated_by,
            signals=signals,
            latest_reviews=latest_reviews,
        )
        for generated_by in generated_bys
    ]

    signals_with_market_confirmation_count = 0
    signals_with_pricing_gap_evidence_count = 0
    signals_blocked_only_by_missing_pricing_gap_count = 0
    signals_passed_to_risk_count = 0
    stage_b_candidate_signal_count = 0
    unresolved_signals: list[dict[str, Any]] = []
    for signal in signals:
        signal_id = str(signal.get("signal_id") or "")
        items = _signal_items(signal)
        review = latest_reviews.get(signal_id, {})
        failure_reasons = review.get("failure_reasons", [])
        has_market_confirmation = bool(tuple(item for item in items if _is_market_confirmation_item(item)))
        has_pricing_gap_event = _signal_has_pricing_gap_event(items)
        has_transaction_cost_event = _signal_has_transaction_cost_event(items)
        has_pricing_gap_marker = _signal_has_pricing_gap_marker(items)
        if has_market_confirmation:
            signals_with_market_confirmation_count += 1
        if has_pricing_gap_event or has_transaction_cost_event or has_pricing_gap_marker:
            signals_with_pricing_gap_evidence_count += 1
        review_status = str(review.get("status") or "missing_review")
        if review_status == "passed_to_risk_shadow":
            signals_passed_to_risk_count += 1
        signal_policy = _pricing_gap_policy(
            items,
            market_confirmation_status=(
                "market_confirmation_corroboration_available"
                if has_market_confirmation
                else "market_confirmation_unavailable"
            ),
            pricing_gap_policy_tier=_pricing_gap_policy_tier_for_signal(signal),
            pricing_gap_rollout_stage=_pricing_gap_rollout_stage_for_signal(signal),
        )
        if signal_policy.get("pricing_gap_status") == "pricing_gap_rollout_stage_a_strict_hold":
            stage_b_candidate_signal_count += 1
        if (
            isinstance(failure_reasons, list)
            and set(str(reason) for reason in failure_reasons) == {"missing_pricing_gap"}
        ):
            signals_blocked_only_by_missing_pricing_gap_count += 1
        unresolved_signals.append(
            {
                "signal_id": signal_id,
                "generated_by": _signal_generated_by(signal),
                "instrument_focus": str(signal.get("instrument_focus") or "unknown_focus"),
                "created_at": str(signal.get("created_at") or ""),
                "source_count": int(_float(_signal_trail(signal).get("source_count"), 0)),
                "market_confirmation_present": has_market_confirmation,
                "pricing_gap_event_present": has_pricing_gap_event,
                "transaction_cost_event_present": has_transaction_cost_event,
                "pricing_gap_marker_present": has_pricing_gap_marker,
                "pricing_gap_status_from_signal": signal_policy["pricing_gap_status"],
                "pricing_gap_confirmation_source_from_signal": signal_policy[
                    "pricing_gap_confirmation_source"
                ],
                "review_status": review_status,
                "review_failure_reasons": (
                    [str(reason) for reason in failure_reasons[:6]]
                    if isinstance(failure_reasons, list)
                    else []
                ),
            }
        )

    unresolved_signals.sort(
        key=lambda item: (
            item["review_status"] != "hold_for_corroboration",
            not item["market_confirmation_present"],
            not _pricing_gap_status_is_satisfied(item["pricing_gap_status_from_signal"]),
            item["generated_by"],
            item["signal_id"],
        )
    )
    flagged_producers = [
        summary["generated_by"]
        for summary in producer_summaries
        if summary.get("likely_missing_pricing_gap_producer") is True
    ]
    risk_reviews = risk_sizing_bundle.get("reviews", [])
    if not isinstance(risk_reviews, list):
        risk_reviews = []
    risk_reviews_blocked_only_by_pricing_gap_policy_count = 0
    for review in risk_reviews:
        if not isinstance(review, dict):
            continue
        blockers = review.get("risk_blockers", [])
        if not isinstance(blockers, list) or not blockers:
            continue
        normalized_blockers = [str(blocker) for blocker in blockers if str(blocker).strip()]
        if (
            normalized_blockers
            and review.get("status") == "blocked"
            and review.get("pricing_gap_policy_satisfied") is False
            and all(blocker.startswith(PRICING_GAP_ONLY_RISK_BLOCKER_PREFIX) for blocker in normalized_blockers)
        ):
            risk_reviews_blocked_only_by_pricing_gap_policy_count += 1
    return {
        "schema_version": SIGNAL_INTEGRITY_FUNNEL_DIAGNOSTICS_SCHEMA_VERSION,
        "artifact_type": "signal_integrity_funnel_diagnostics",
        "artifact_id": "signal_integrity:funnel-diagnostics",
        "generated_at": _now(),
        "public_safe": True,
        "pricing_gap_rollout_stage": rollout_stage,
        "pricing_gap_rollout_relaxed_policy_enabled": rollout_stage == "stage_b",
        "shadow_signal_count": len(signals),
        "review_count": len(reviews),
        "missing_review_count": sum(
            1 for signal in signals if str(signal.get("signal_id") or "") not in latest_reviews
        ),
        "signals_with_market_confirmation_count": signals_with_market_confirmation_count,
        "signals_with_pricing_gap_evidence_count": signals_with_pricing_gap_evidence_count,
        "signals_blocked_only_by_missing_pricing_gap_count": (
            signals_blocked_only_by_missing_pricing_gap_count
        ),
        "signals_passed_to_risk_count": signals_passed_to_risk_count,
        "risk_review_count": (
            len(risk_reviews)
            if risk_sizing_bundle.get("artifact_type") == "phase5_risk_sizing_review_bundle"
            else 0
        ),
        "risk_reviews_blocked_only_by_pricing_gap_policy_count": (
            risk_reviews_blocked_only_by_pricing_gap_policy_count
        ),
        "stage_b_candidate_signal_count": stage_b_candidate_signal_count,
        "producer_count": len(producer_summaries),
        "flagged_missing_pricing_gap_producer_count": len(flagged_producers),
        "flagged_missing_pricing_gap_producers": flagged_producers,
        "producer_summaries": producer_summaries,
        "unresolved_signals": unresolved_signals[:50],
        "boundary": (
            "Signal Integrity funnel diagnostics are read-only. They inspect shadow-signal "
            "evidence and Signal Integrity review outputs only; they cannot create signals, "
            "change gate decisions, create trade candidates, or enable orders."
        ),
    }


def write_signal_integrity_funnel_diagnostics(
    *,
    settings: Settings | None = None,
    signal_store: ShadowSignalStore | None = None,
    review_store: SignalIntegrityReviewStore | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    artifact = build_signal_integrity_funnel_diagnostics(
        settings=settings,
        signal_store=signal_store,
        review_store=review_store,
    )
    path = signal_integrity_funnel_diagnostics_path(settings)
    path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return artifact


def run_signal_integrity_gate(
    *,
    limit: int = 5,
    settings: Settings | None = None,
    store: SignalIntegrityReviewStore | None = None,
    event_log: EventLog | None = None,
    seed_sample_if_empty: bool = False,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    if seed_sample_if_empty and not ShadowSignalStore(settings=settings).read():
        run_shadow_intelligence_sample(store=ShadowSignalStore(settings=settings), event_log=event_log)
    signal_store = ShadowSignalStore(settings=settings)
    review_store = store or SignalIntegrityReviewStore(settings=settings)
    event_log = event_log or EventLog(echo=False)
    signals = signal_store.read()
    selected = signals[-limit:] if limit > 0 else signals
    reviews = tuple(build_signal_integrity_review(signal) for signal in selected)
    for review in reviews:
        review_store.write(review, event_log=event_log)
    health = review_store.health()
    funnel_diagnostics = write_signal_integrity_funnel_diagnostics(
        settings=settings,
        signal_store=signal_store,
        review_store=review_store,
    )
    return {
        "status": "ok",
        "schema_version": SIGNAL_INTEGRITY_SCHEMA_VERSION,
        "signal_count": len(signals),
        "processed_signal_count": len(selected),
        "review_count": len(reviews),
        "blocked_count": sum(1 for review in reviews if review.status == "blocked"),
        "hold_count": sum(1 for review in reviews if review.status == "hold_for_corroboration"),
        "passed_to_risk_shadow_count": sum(1 for review in reviews if review.status == "passed_to_risk_shadow"),
        "execution_allowed_count": sum(1 for review in reviews if review.execution_allowed),
        "paper_order_allowed_count": sum(1 for review in reviews if review.paper_order_allowed),
        "trade_candidate_created_count": sum(1 for review in reviews if review.trade_candidate_created),
        "store": health,
        "funnel_diagnostics_artifact_path": str(signal_integrity_funnel_diagnostics_path(settings)),
        "flagged_missing_pricing_gap_producer_count": int(
            funnel_diagnostics.get("flagged_missing_pricing_gap_producer_count", 0) or 0
        ),
        "event_log": event_log.health(),
        "boundary": health["boundary"],
    }


def signal_integrity_summary(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    health = SignalIntegrityReviewStore(settings=settings).health()
    diagnostics_path = signal_integrity_funnel_diagnostics_path(settings)
    if diagnostics_path.exists():
        diagnostics = _runtime_json_artifact(diagnostics_path)
        health["funnel_diagnostics_artifact_path"] = str(diagnostics_path)
        for key in (
            "shadow_signal_count",
            "signals_with_market_confirmation_count",
            "signals_with_pricing_gap_evidence_count",
            "signals_blocked_only_by_missing_pricing_gap_count",
            "signals_passed_to_risk_count",
            "risk_review_count",
            "risk_reviews_blocked_only_by_pricing_gap_policy_count",
            "stage_b_candidate_signal_count",
            "flagged_missing_pricing_gap_producer_count",
        ):
            health[key] = int(diagnostics.get(key, 0) or 0)
        health["pricing_gap_rollout_stage"] = str(
            diagnostics.get("pricing_gap_rollout_stage") or "stage_a"
        )
        health["pricing_gap_rollout_relaxed_policy_enabled"] = (
            diagnostics.get("pricing_gap_rollout_relaxed_policy_enabled") is True
        )
    return health
