"""Read-only Risk Agent policy router.

The Risk Agent is deterministic infrastructure. In the current phase it can
inspect Signal Integrity reviews, local trade intents, and paper-account state.
It can block or hold. It cannot approve risk, create orders, or write to a
broker.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.paper_account import paper_account_shadow_context
from orchestrator.signal_integrity import SignalIntegrityReviewStore
from orchestrator.trade_intent import TradeIntent, TradeIntentStore

RISK_AGENT_SCHEMA_VERSION = 1
RISK_AGENT_STATUSES = {"blocked_before_risk", "policy_hold", "risk_shadow_ready"}
MAX_RISK_PCT_PER_IDEA = 1.0


@dataclass(frozen=True)
class RiskPolicyReview:
    schema_version: int
    review_id: str
    source_type: str
    source_ref: str
    status: str
    instrument: str
    policy_score: float
    proposed_risk_gbp: float
    proposed_risk_pct: float
    max_risk_gbp: float
    max_risk_pct: float
    checks: dict[str, str]
    blocked_reasons: tuple[str, ...]
    required_next_steps: tuple[str, ...]
    paper_account_status: str
    signal_integrity_status: str
    execution_allowed: bool
    paper_order_allowed: bool
    order_created: bool
    broker_write_allowed: bool
    reviewed_at: str
    boundary: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["blocked_reasons"] = list(self.blocked_reasons)
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


def _risk_cap(settings: Settings) -> tuple[float, float]:
    max_risk_pct = _float(MAX_RISK_PCT_PER_IDEA, 1.0)
    max_risk_gbp = round(float(settings.trial_balance_gbp) * max_risk_pct / 100, 2)
    return max_risk_gbp, max_risk_pct


def _account_checks(account: dict[str, Any]) -> dict[str, str]:
    checks = {
        "mode": "pass_paper_mode" if account.get("mode") == "paper" else "fail_not_paper_mode",
        "live_capital": "pass_disabled" if account.get("live_capital_enabled") is False else "fail_live_capital_enabled",
        "broker_write": "pass_disabled" if account.get("write_authority") is False else "fail_write_authority_enabled",
        "paper_order_authority": "pass_disabled"
        if account.get("paper_order_allowed") is False
        else "fail_paper_order_authority_enabled",
        "drawdown": "pass_within_cap" if _float(account.get("drawdown_pct"), 0) <= 10 else "fail_drawdown_above_cap",
        "closed_trade_maturity": "informational_below_100_closed_trades"
        if int(_float(account.get("maturity_closed_trade_count"), 0)) < 100
        else "pass_maturity_benchmark",
        "execution_policy": "fail_closed_not_implemented",
        "kill_switch": "fail_closed_not_implemented",
        "broker_order_route": "fail_closed_no_order_route",
    }
    return checks


def _policy_blockers(checks: dict[str, str]) -> tuple[str, ...]:
    return tuple(
        key
        for key, value in checks.items()
        if value.startswith("fail_") and key in {"execution_policy", "kill_switch", "broker_order_route"}
    )


def _hard_failures(checks: dict[str, str]) -> tuple[str, ...]:
    return tuple(
        key
        for key, value in checks.items()
        if value.startswith("fail_") and key not in {"execution_policy", "kill_switch", "broker_order_route"}
    )


def _status(checks: dict[str, str], blocked_reasons: tuple[str, ...]) -> str:
    hard_failures = _hard_failures(checks)
    policy_blockers = _policy_blockers(checks)
    material_reasons = tuple(reason for reason in blocked_reasons if reason not in policy_blockers)
    if hard_failures or material_reasons:
        return "blocked_before_risk"
    if policy_blockers:
        return "policy_hold"
    return "risk_shadow_ready"


def _score(checks: dict[str, str], blocked_reasons: tuple[str, ...], base_score: float) -> float:
    penalty = 0.09 * len(tuple(reason for reason in blocked_reasons if reason not in _policy_blockers(checks)))
    pass_bonus = 0.03 * sum(1 for value in checks.values() if value.startswith("pass_"))
    score = base_score + pass_bonus - penalty
    return round(max(0.0, min(1.0, score)), 3)


def _next_steps(status: str, blocked_reasons: tuple[str, ...]) -> tuple[str, ...]:
    steps: list[str] = []
    if "signal_integrity_not_passed" in blocked_reasons:
        steps.append("Wait for Signal Integrity Gate to pass before any Risk Agent sizing.")
    if "source_signal_not_passed_signal_integrity" in blocked_reasons:
        steps.append("Link candidate to a signal that has passed Signal Integrity review.")
    if "risk_size_above_policy_cap" in blocked_reasons:
        steps.append("Reduce theoretical risk below the first-release cap.")
    if "missing_invalidation" in blocked_reasons:
        steps.append("Add a concrete invalidation level or condition.")
    steps.append("Implement deterministic execution policy, kill-switch, and broker-order contracts before paper orders.")
    steps.append("Keep broker writes and live capital disabled.")
    return tuple(dict.fromkeys(steps))[:6]


def validate_risk_policy_review(review: RiskPolicyReview) -> None:
    if review.schema_version != RISK_AGENT_SCHEMA_VERSION:
        raise ValueError("risk policy review schema version mismatch")
    if review.status not in RISK_AGENT_STATUSES:
        raise ValueError(f"invalid risk policy review status: {review.status}")
    if review.execution_allowed:
        raise ValueError("Risk Agent shadow review cannot allow execution")
    if review.paper_order_allowed:
        raise ValueError("Risk Agent shadow review cannot allow paper orders")
    if review.order_created:
        raise ValueError("Risk Agent shadow review cannot create orders")
    if review.broker_write_allowed:
        raise ValueError("Risk Agent shadow review cannot allow broker writes")
    if not 0 <= review.policy_score <= 1:
        raise ValueError("risk policy score must be between 0 and 1")


def build_risk_review_from_signal_integrity(
    signal_review: dict[str, Any],
    *,
    settings: Settings,
    account_context: dict[str, Any],
) -> RiskPolicyReview:
    max_risk_gbp, max_risk_pct = _risk_cap(settings)
    checks = _account_checks(account_context)
    signal_status = str(signal_review.get("status") or "unknown")
    checks.update(
        {
            "signal_integrity": "pass"
            if signal_status == "passed_to_risk_shadow"
            else f"fail_{signal_status}",
            "source_count": "pass" if int(_float(signal_review.get("source_count"), 0)) >= 2 else "fail_source_count",
            "trust_floor": "pass" if _float(signal_review.get("min_trust_score"), 0) >= 0.5 else "fail_trust_floor",
            "missing_correlations": "pass"
            if not signal_review.get("missing_correlations")
            else "fail_missing_correlations",
            "invalidation": "fail_missing_invalidation",
        }
    )
    blocked = list(_policy_blockers(checks))
    if signal_status != "passed_to_risk_shadow":
        blocked.append("signal_integrity_not_passed")
    if checks["source_count"].startswith("fail"):
        blocked.append("insufficient_independent_sources")
    if checks["missing_correlations"].startswith("fail"):
        blocked.append("missing_correlations")
    blocked.append("missing_invalidation")
    blocked_reasons = tuple(dict.fromkeys(blocked))
    status = _status(checks, blocked_reasons)
    review = RiskPolicyReview(
        schema_version=RISK_AGENT_SCHEMA_VERSION,
        review_id=str(uuid4()),
        source_type="signal_integrity_review",
        source_ref=str(signal_review.get("review_id") or signal_review.get("source_signal_id") or "unknown_signal"),
        status=status,
        instrument=str(signal_review.get("instrument_focus") or "macro_watchlist")[:120],
        policy_score=_score(checks, blocked_reasons, _float(signal_review.get("integrity_score"), 0.0)),
        proposed_risk_gbp=0.0,
        proposed_risk_pct=0.0,
        max_risk_gbp=max_risk_gbp,
        max_risk_pct=max_risk_pct,
        checks=checks,
        blocked_reasons=blocked_reasons,
        required_next_steps=_next_steps(status, blocked_reasons),
        paper_account_status=str(account_context.get("connection_status") or account_context.get("status") or "unknown"),
        signal_integrity_status=signal_status,
        execution_allowed=False,
        paper_order_allowed=False,
        order_created=False,
        broker_write_allowed=False,
        reviewed_at=_now(),
        boundary=(
            "Risk Agent policy review is read-only. It can block or hold a signal, "
            "but cannot approve risk, create paper orders, or write to a broker."
        ),
    )
    validate_risk_policy_review(review)
    return review


def build_risk_review_from_trade_intent(
    intent: TradeIntent,
    *,
    settings: Settings,
    account_context: dict[str, Any],
    signal_reviews_by_signal: dict[str, dict[str, Any]],
) -> RiskPolicyReview:
    max_risk_gbp, max_risk_pct = _risk_cap(settings)
    checks = _account_checks(account_context)
    signal_review = signal_reviews_by_signal.get(str(intent.source_signal_id or ""))
    signal_status = str(signal_review.get("status") if signal_review else "not_reviewed")
    checks.update(
        {
            "intent_state": "pass_candidate" if intent.status in {"candidate", "risk_review"} else f"fail_{intent.status}",
            "signal_integrity": "pass"
            if signal_status == "passed_to_risk_shadow"
            else f"fail_{signal_status}",
            "risk_size": "pass"
            if intent.risk_size_gbp <= max_risk_gbp and intent.risk_size_pct <= max_risk_pct
            else "fail_above_policy_cap",
            "invalidation": "pass" if intent.invalidation and intent.invalidation != "none" else "fail_missing_invalidation",
            "entry": "pass" if intent.proposed_entry and intent.proposed_entry != "none" else "fail_missing_entry",
            "unauthorized_authority_flags": "pass"
            if not intent.execution_allowed and not intent.paper_order_allowed
            else "fail_authority_enabled",
        }
    )
    blocked = list(_policy_blockers(checks))
    if intent.status == "blocked":
        blocked.append("intent_status_blocked")
    elif intent.status not in {"candidate", "risk_review"}:
        blocked.append("intent_not_candidate")
    if signal_status != "passed_to_risk_shadow":
        blocked.append("source_signal_not_passed_signal_integrity")
    if checks["risk_size"].startswith("fail"):
        blocked.append("risk_size_above_policy_cap")
    if checks["invalidation"].startswith("fail"):
        blocked.append("missing_invalidation")
    if checks["entry"].startswith("fail"):
        blocked.append("missing_entry")
    if checks["unauthorized_authority_flags"].startswith("fail"):
        blocked.append("unauthorized_authority_flag")
    blocked_reasons = tuple(dict.fromkeys(blocked))
    base_score = _float(signal_review.get("integrity_score") if signal_review else 0.25, 0.25)
    status = _status(checks, blocked_reasons)
    review = RiskPolicyReview(
        schema_version=RISK_AGENT_SCHEMA_VERSION,
        review_id=str(uuid4()),
        source_type="trade_intent",
        source_ref=intent.intent_id,
        status=status,
        instrument=intent.instrument[:120],
        policy_score=_score(checks, blocked_reasons, base_score),
        proposed_risk_gbp=round(float(intent.risk_size_gbp), 2),
        proposed_risk_pct=round(float(intent.risk_size_pct), 3),
        max_risk_gbp=max_risk_gbp,
        max_risk_pct=max_risk_pct,
        checks=checks,
        blocked_reasons=blocked_reasons,
        required_next_steps=_next_steps(status, blocked_reasons),
        paper_account_status=str(account_context.get("connection_status") or account_context.get("status") or "unknown"),
        signal_integrity_status=signal_status,
        execution_allowed=False,
        paper_order_allowed=False,
        order_created=False,
        broker_write_allowed=False,
        reviewed_at=_now(),
        boundary=(
            "Risk Agent policy review is read-only. It can block or hold a candidate, "
            "but cannot approve risk, create paper orders, or write to a broker."
        ),
    )
    validate_risk_policy_review(review)
    return review


class RiskPolicyReviewStore:
    def __init__(self, path: str | Path | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self.path = Path(path or Path(self.settings.runtime_dir) / "risk_policy_reviews.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, review: RiskPolicyReview, *, event_log: EventLog | None = None) -> RiskPolicyReview:
        validate_risk_policy_review(review)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(review.to_dict(), sort_keys=True) + "\n")
        (event_log or EventLog(echo=False)).write(
            "risk_policy_review_recorded",
            "risk_agent",
            {
                "review_id": review.review_id,
                "source_type": review.source_type,
                "source_ref": review.source_ref,
                "status": review.status,
                "policy_score": review.policy_score,
                "execution_allowed": review.execution_allowed,
                "paper_order_allowed": review.paper_order_allowed,
                "order_created": review.order_created,
                "broker_write_allowed": review.broker_write_allowed,
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
                    raise ValueError(f"invalid risk policy review line {line_number} in {self.path}") from exc
                if isinstance(loaded, dict):
                    reviews.append(loaded)
        if limit is not None:
            reviews = reviews[-limit:]
        return tuple(reviews)

    def health(self) -> dict[str, Any]:
        try:
            reviews = self.read()
        except Exception as exc:  # noqa: BLE001 - health should report failure.
            return {
                "status": "degraded",
                "schema_version": RISK_AGENT_SCHEMA_VERSION,
                "error": str(exc),
            }
        counts = Counter(str(review.get("status", "unknown")) for review in reviews)
        return {
            "status": "ok",
            "schema_version": RISK_AGENT_SCHEMA_VERSION,
            "review_count": len(reviews),
            "by_status": dict(sorted(counts.items())),
            "execution_allowed_count": sum(1 for review in reviews if review.get("execution_allowed") is True),
            "paper_order_allowed_count": sum(1 for review in reviews if review.get("paper_order_allowed") is True),
            "order_created_count": sum(1 for review in reviews if review.get("order_created") is True),
            "broker_write_allowed_count": sum(1 for review in reviews if review.get("broker_write_allowed") is True),
            "boundary": (
                "Risk Agent policy reviews are read-only. They can block or hold, "
                "but cannot approve risk, create orders, or write to brokers."
            ),
        }


def run_risk_policy_router(
    *,
    settings: Settings | None = None,
    store: RiskPolicyReviewStore | None = None,
    event_log: EventLog | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    review_store = store or RiskPolicyReviewStore(settings=settings)
    event_log = event_log or EventLog(echo=False)
    account_context = paper_account_shadow_context(settings)
    signal_reviews = SignalIntegrityReviewStore(settings=settings).read(limit=limit)
    trade_intents = TradeIntentStore(settings=settings).read_intents(limit=limit)
    signal_reviews_by_signal = {
        str(review.get("source_signal_id")): review
        for review in signal_reviews
        if review.get("source_signal_id")
    }
    reviews: list[RiskPolicyReview] = []
    reviews.extend(
        build_risk_review_from_signal_integrity(
            signal_review,
            settings=settings,
            account_context=account_context,
        )
        for signal_review in signal_reviews
    )
    reviews.extend(
        build_risk_review_from_trade_intent(
            intent,
            settings=settings,
            account_context=account_context,
            signal_reviews_by_signal=signal_reviews_by_signal,
        )
        for intent in trade_intents
    )
    for review in reviews:
        review_store.write(review, event_log=event_log)
    health = review_store.health()
    return {
        "status": "ok",
        "schema_version": RISK_AGENT_SCHEMA_VERSION,
        "signal_review_count": len(signal_reviews),
        "trade_intent_count": len(trade_intents),
        "review_count": len(reviews),
        "blocked_count": sum(1 for review in reviews if review.status == "blocked_before_risk"),
        "policy_hold_count": sum(1 for review in reviews if review.status == "policy_hold"),
        "risk_shadow_ready_count": sum(1 for review in reviews if review.status == "risk_shadow_ready"),
        "execution_allowed_count": sum(1 for review in reviews if review.execution_allowed),
        "paper_order_allowed_count": sum(1 for review in reviews if review.paper_order_allowed),
        "order_created_count": sum(1 for review in reviews if review.order_created),
        "broker_write_allowed_count": sum(1 for review in reviews if review.broker_write_allowed),
        "store": health,
        "event_log": event_log.health(),
        "boundary": health["boundary"],
    }


def risk_agent_summary(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    return RiskPolicyReviewStore(settings=settings).health()
