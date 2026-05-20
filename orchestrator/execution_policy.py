"""Read-only execution policy and kill-switch contract.

This layer sits after the Risk Agent. In the current phase it can explain why a
reviewed idea cannot become a staged paper order. It cannot stage orders, create
orders, enable broker writes, or enable live capital.
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
from orchestrator.execution import execution_registry
from orchestrator.paper_account import paper_account_shadow_context
from orchestrator.risk_agent import RiskPolicyReviewStore

EXECUTION_POLICY_SCHEMA_VERSION = 1
EXECUTION_POLICY_STATUSES = {"blocked_by_policy", "kill_switch_hold", "paper_order_shadow_ready"}


@dataclass(frozen=True)
class ExecutionPolicyReview:
    schema_version: int
    review_id: str
    source_risk_review_id: str
    status: str
    instrument: str
    selected_venue: str
    venue_mode: str
    policy_score: float
    checks: dict[str, str]
    kill_switches: dict[str, str]
    blocked_reasons: tuple[str, ...]
    required_next_steps: tuple[str, ...]
    execution_allowed: bool
    staged_paper_order_allowed: bool
    paper_order_created: bool
    broker_write_allowed: bool
    live_capital_enabled: bool
    reviewed_at: str
    boundary: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["blocked_reasons"] = list(self.blocked_reasons)
        payload["required_next_steps"] = list(self.required_next_steps)
        return payload


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _venue_for_review(risk_review: dict[str, Any]) -> dict[str, Any]:
    venues = execution_registry()
    instrument = str(risk_review.get("instrument") or "").lower()
    if any(term in instrument for term in ("polymarket", "kalshi", "prediction")):
        preferred = "prediction_market_router"
    else:
        preferred = "alpaca_paper"
    for venue in venues:
        if venue.get("key") == preferred:
            return venue
    return venues[0] if venues else {"key": "none", "mode": "disabled", "write_health": "blocked"}


def _kill_switches(venue: dict[str, Any]) -> dict[str, str]:
    return {
        "global": "engaged_blocking_all_orders",
        "strategy": "engaged_pending_strategy_approval",
        "venue": f"engaged_{venue.get('key', 'unknown')}_write_blocked",
        "model": "engaged_no_model_order_authority",
        "data": "engaged_requires_fresh_replayable_observations",
    }


def _checks(
    risk_review: dict[str, Any],
    *,
    settings: Settings,
    venue: dict[str, Any],
    account_context: dict[str, Any],
    kill_switches: dict[str, str],
) -> dict[str, str]:
    risk_status = str(risk_review.get("status") or "unknown")
    return {
        "operating_mode": "pass_paper_mode" if settings.mode == "paper" else "fail_not_paper_mode",
        "live_capital": "pass_disabled"
        if account_context.get("live_capital_enabled") is False
        else "fail_live_capital_enabled",
        "risk_agent": "pass_shadow_ready" if risk_status == "risk_shadow_ready" else f"fail_{risk_status}",
        "risk_agent_authority": "pass_read_only_reviewed"
        if risk_review.get("execution_allowed") is False
        and risk_review.get("paper_order_allowed") is False
        and risk_review.get("broker_write_allowed") is False
        else "fail_risk_agent_authority_enabled",
        "execution_policy_registry": "fail_closed_read_only_contract",
        "global_kill_switch": "fail_" + kill_switches["global"],
        "strategy_kill_switch": "fail_" + kill_switches["strategy"],
        "venue_kill_switch": "fail_" + kill_switches["venue"],
        "paper_order_contract": "fail_closed_not_implemented",
        "broker_order_route": "fail_closed_no_broker_order_route",
        "venue_registry": "fail_all_write_routes_disabled"
        if str(venue.get("write_health", "")).startswith("blocked")
        else "fail_unexpected_write_route_state",
        "event_log": "pass_jsonl_audit_ready",
        "closed_trade_maturity": "informational_below_100_closed_trades"
        if int(account_context.get("maturity_closed_trade_count") or 0) < 100
        else "pass_maturity_benchmark",
    }


def _blocked_reasons(checks: dict[str, str]) -> tuple[str, ...]:
    reasons = [key for key, value in checks.items() if value.startswith("fail_")]
    return tuple(dict.fromkeys(reasons))


def _status(checks: dict[str, str]) -> str:
    reasons = _blocked_reasons(checks)
    if not reasons:
        return "paper_order_shadow_ready"
    if any(reason.endswith("_kill_switch") for reason in reasons):
        return "kill_switch_hold"
    if any(reason in {"global_kill_switch", "strategy_kill_switch", "venue_kill_switch"} for reason in reasons):
        return "kill_switch_hold"
    return "blocked_by_policy"


def _next_steps(blocked_reasons: tuple[str, ...]) -> tuple[str, ...]:
    steps: list[str] = []
    if "risk_agent" in blocked_reasons:
        steps.append("Wait for Risk Agent to produce a risk-shadow-ready review.")
    if "execution_policy_registry" in blocked_reasons:
        steps.append("Implement deterministic execution-policy rules before staging paper orders.")
    if any(reason.endswith("kill_switch") for reason in blocked_reasons) or "global_kill_switch" in blocked_reasons:
        steps.append("Define Fund Manager kill-switch controls and logged reset rules.")
    if "paper_order_contract" in blocked_reasons:
        steps.append("Create a staged paper-order contract that is still broker-write blocked.")
    if "broker_order_route" in blocked_reasons:
        steps.append("Keep broker-order routes disabled until paper-order reconciliation exists.")
    steps.append("Keep live capital disabled.")
    return tuple(dict.fromkeys(steps))[:6]


def _score(risk_review: dict[str, Any], checks: dict[str, str]) -> float:
    base = float(risk_review.get("policy_score") or 0)
    penalty = 0.05 * len(_blocked_reasons(checks))
    bonus = 0.02 * sum(1 for value in checks.values() if value.startswith("pass_"))
    return round(max(0.0, min(1.0, base + bonus - penalty)), 3)


def validate_execution_policy_review(review: ExecutionPolicyReview) -> None:
    if review.schema_version != EXECUTION_POLICY_SCHEMA_VERSION:
        raise ValueError("execution policy review schema version mismatch")
    if review.status not in EXECUTION_POLICY_STATUSES:
        raise ValueError(f"invalid execution policy review status: {review.status}")
    if review.execution_allowed:
        raise ValueError("execution policy cannot allow execution in the current phase")
    if review.staged_paper_order_allowed:
        raise ValueError("execution policy cannot allow staged paper orders in the current phase")
    if review.paper_order_created:
        raise ValueError("execution policy cannot create paper orders")
    if review.broker_write_allowed:
        raise ValueError("execution policy cannot allow broker writes")
    if review.live_capital_enabled:
        raise ValueError("execution policy cannot enable live capital")
    if not 0 <= review.policy_score <= 1:
        raise ValueError("execution policy score must be between 0 and 1")


def build_execution_policy_review(
    risk_review: dict[str, Any],
    *,
    settings: Settings,
    account_context: dict[str, Any],
) -> ExecutionPolicyReview:
    venue = _venue_for_review(risk_review)
    kill_switches = _kill_switches(venue)
    checks = _checks(risk_review, settings=settings, venue=venue, account_context=account_context, kill_switches=kill_switches)
    blocked = _blocked_reasons(checks)
    review = ExecutionPolicyReview(
        schema_version=EXECUTION_POLICY_SCHEMA_VERSION,
        review_id=str(uuid4()),
        source_risk_review_id=str(risk_review.get("review_id") or "unknown_risk_review"),
        status=_status(checks),
        instrument=str(risk_review.get("instrument") or "unknown")[:120],
        selected_venue=str(venue.get("key") or "none"),
        venue_mode=str(venue.get("mode") or "disabled"),
        policy_score=_score(risk_review, checks),
        checks=checks,
        kill_switches=kill_switches,
        blocked_reasons=blocked,
        required_next_steps=_next_steps(blocked),
        execution_allowed=False,
        staged_paper_order_allowed=False,
        paper_order_created=False,
        broker_write_allowed=False,
        live_capital_enabled=False,
        reviewed_at=_now(),
        boundary=(
            "Execution policy is read-only. It can explain why a paper order is blocked, "
            "but cannot stage orders, create orders, enable live capital, or write to brokers."
        ),
    )
    validate_execution_policy_review(review)
    return review


class ExecutionPolicyReviewStore:
    def __init__(self, path: str | Path | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self.path = Path(path or Path(self.settings.runtime_dir) / "execution_policy_reviews.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, review: ExecutionPolicyReview, *, event_log: EventLog | None = None) -> ExecutionPolicyReview:
        validate_execution_policy_review(review)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(review.to_dict(), sort_keys=True) + "\n")
        (event_log or EventLog(echo=False)).write(
            "execution_policy_review_recorded",
            "execution_policy",
            {
                "review_id": review.review_id,
                "source_risk_review_id": review.source_risk_review_id,
                "status": review.status,
                "selected_venue": review.selected_venue,
                "execution_allowed": review.execution_allowed,
                "staged_paper_order_allowed": review.staged_paper_order_allowed,
                "paper_order_created": review.paper_order_created,
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
                    raise ValueError(f"invalid execution policy review line {line_number} in {self.path}") from exc
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
                "schema_version": EXECUTION_POLICY_SCHEMA_VERSION,
                "error": str(exc),
            }
        counts = Counter(str(review.get("status", "unknown")) for review in reviews)
        return {
            "status": "ok",
            "schema_version": EXECUTION_POLICY_SCHEMA_VERSION,
            "review_count": len(reviews),
            "by_status": dict(sorted(counts.items())),
            "execution_allowed_count": sum(1 for review in reviews if review.get("execution_allowed") is True),
            "staged_paper_order_allowed_count": sum(
                1 for review in reviews if review.get("staged_paper_order_allowed") is True
            ),
            "paper_order_created_count": sum(1 for review in reviews if review.get("paper_order_created") is True),
            "broker_write_allowed_count": sum(1 for review in reviews if review.get("broker_write_allowed") is True),
            "live_capital_enabled_count": sum(1 for review in reviews if review.get("live_capital_enabled") is True),
            "kill_switch_block_count": sum(
                1
                for review in reviews
                if any(str(reason).endswith("kill_switch") for reason in review.get("blocked_reasons", []))
            ),
            "boundary": (
                "Execution policy reviews are read-only. They can explain holds and kill-switch blocks, "
                "but cannot stage paper orders, create orders, enable live capital, or write to brokers."
            ),
        }


def run_execution_policy_router(
    *,
    settings: Settings | None = None,
    store: ExecutionPolicyReviewStore | None = None,
    event_log: EventLog | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    review_store = store or ExecutionPolicyReviewStore(settings=settings)
    event_log = event_log or EventLog(echo=False)
    account_context = paper_account_shadow_context(settings)
    risk_reviews = RiskPolicyReviewStore(settings=settings).read(limit=limit)
    reviews = [
        build_execution_policy_review(risk_review, settings=settings, account_context=account_context)
        for risk_review in risk_reviews
    ]
    for review in reviews:
        review_store.write(review, event_log=event_log)
    health = review_store.health()
    return {
        "status": "ok",
        "schema_version": EXECUTION_POLICY_SCHEMA_VERSION,
        "risk_review_count": len(risk_reviews),
        "review_count": len(reviews),
        "blocked_by_policy_count": sum(1 for review in reviews if review.status == "blocked_by_policy"),
        "kill_switch_hold_count": sum(1 for review in reviews if review.status == "kill_switch_hold"),
        "paper_order_shadow_ready_count": sum(1 for review in reviews if review.status == "paper_order_shadow_ready"),
        "execution_allowed_count": sum(1 for review in reviews if review.execution_allowed),
        "staged_paper_order_allowed_count": sum(1 for review in reviews if review.staged_paper_order_allowed),
        "paper_order_created_count": sum(1 for review in reviews if review.paper_order_created),
        "broker_write_allowed_count": sum(1 for review in reviews if review.broker_write_allowed),
        "live_capital_enabled_count": sum(1 for review in reviews if review.live_capital_enabled),
        "store": health,
        "event_log": event_log.health(),
        "boundary": health["boundary"],
    }


def execution_policy_summary(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    return ExecutionPolicyReviewStore(settings=settings).health()
