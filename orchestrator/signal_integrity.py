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

SIGNAL_INTEGRITY_SCHEMA_VERSION = 3
SIGNAL_INTEGRITY_STATUSES = {"blocked", "hold_for_corroboration", "passed_to_risk_shadow"}
MARKET_CONFIRMATION_MAX_AGE = timedelta(hours=48)
MARKET_CONFIRMATION_EVENT_TYPE = "market_price_confirmation"
YAHOO_FINANCE_SOURCE = "market.yahoo_finance"
PREFERENCE_MCP_SOURCE = "supplemental.preference_mcp"
PRICING_GAP_EVENT_TYPES = {"pricing_gap_assumption", "transaction_cost_assumption"}
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


def _pricing_gap_status(items: tuple[dict[str, Any], ...]) -> str:
    summary_text = " ".join(str(item.get("summary") or "") for item in items).lower()
    explicit_event = any(
        str(item.get("event_type") or "").lower() in PRICING_GAP_EVENT_TYPES for item in items
    )
    explicit_marker = any(marker in summary_text for marker in PRICING_GAP_CONFIRMATION_MARKERS)
    return "pass_pricing_gap_confirmed" if explicit_event or explicit_marker else "hold_pricing_gap_required"


def _market_confirmation_policy(
    *,
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

    return {
        "status": status,
        "market_price_confirmation": (
            "pass_supplemental_corroboration"
            if status == "market_confirmation_corroboration_available"
            else f"hold_{status}"
        ),
        "pricing_gap": _pricing_gap_status(items),
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


def _akber_filter(
    *,
    evidence_item_count: int,
    source_count: int,
    missing: tuple[str, ...],
    average_trust_score: float,
    market_policy: dict[str, Any],
) -> dict[str, str]:
    catalyst = "pass" if evidence_item_count > 0 and average_trust_score >= 0.5 else "fail_missing_trusted_catalyst"
    return {
        "low_volatility": "missing_volatility_context",
        "options_distribution_gap": str(market_policy["pricing_gap"]),
        "catalyst_identification": catalyst,
        "technical_setup": "missing_market_price_confirmation"
        if "market_price_confirmation" in missing
        or source_count < 2
        or market_policy["status"] != "market_confirmation_corroboration_available"
        else "shadow_pass",
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
    if market_policy["pricing_gap"] != "pass_pricing_gap_confirmed":
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
) -> str:
    preference_hold_status = preference_policy["status"] in {
        "preference_only_confirmation_hold",
        "preference_context_missing_provenance_hold",
        "preference_context_stale_hold",
        "preference_context_quota_degraded_hold",
    }
    if evidence_item_count < 1 or min_trust_score < 0.5 or signal_confidence < 0.45:
        return "blocked"
    if (
        source_count < 2
        or missing
        or average_trust_score < 0.65
        or market_policy["status"] != "market_confirmation_corroboration_available"
        or market_policy["pricing_gap"] != "pass_pricing_gap_confirmed"
        or preference_hold_status
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
    if "maritime_confirmation" in failure_reasons:
        steps.append("Add maritime, logistics, or vessel confirmation.")
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
    market_policy = _market_confirmation_policy(trail=trail, source_count=source_count)
    preference_policy = _preference_context_policy(trail=trail, source_count=source_count)
    status = _review_status(
        evidence_item_count=evidence_item_count,
        source_count=source_count,
        average_trust_score=average_trust_score,
        min_trust_score=min_trust_score,
        signal_confidence=signal_confidence,
        missing=missing,
        market_policy=market_policy,
        preference_policy=preference_policy,
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
        ),
        market_confirmation_policy=market_policy,
        preference_context_policy=preference_policy,
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
        "event_log": event_log.health(),
        "boundary": health["boundary"],
    }


def signal_integrity_summary(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    return SignalIntegrityReviewStore(settings=settings).health()
