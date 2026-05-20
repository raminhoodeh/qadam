"""Disabled staged paper-order contract.

This layer sits after Execution Policy. In the current phase it can explain the
paper order that would be considered later and the reconciliation checks that
must exist first. It cannot stage, submit, create, or write any order.
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
from orchestrator.execution_policy import ExecutionPolicyReviewStore
from orchestrator.paper_account import paper_account_shadow_context

STAGED_PAPER_ORDER_SCHEMA_VERSION = 1
STAGED_PAPER_ORDER_STATUSES = {
    "blocked_before_staging",
    "reconciliation_hold",
    "disabled_contract_hold",
}


@dataclass(frozen=True)
class StagedPaperOrderReview:
    schema_version: int
    review_id: str
    source_execution_policy_review_id: str
    status: str
    instrument: str
    selected_venue: str
    venue_mode: str
    account_scope: str
    hypothetical_order: dict[str, Any]
    reconciliation_checks: dict[str, str]
    blocked_reasons: tuple[str, ...]
    required_next_steps: tuple[str, ...]
    execution_allowed: bool
    staged_paper_order_created: bool
    paper_order_submittable: bool
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


def _hypothetical_order(execution_review: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "not_created",
        "instrument": str(execution_review.get("instrument") or "unknown")[:120],
        "venue": str(execution_review.get("selected_venue") or "none"),
        "direction": "not_determined",
        "order_type": "not_applicable",
        "quantity": 0,
        "notional_gbp": 0.0,
        "risk_gbp": 0.0,
        "invalidation": "requires_candidate_entry_and_invalidation_before_staging",
        "idempotency_key": "not_allocated",
        "event_log_ref": "not_written",
    }


def _reconciliation_checks(
    execution_review: dict[str, Any],
    *,
    account_context: dict[str, Any],
) -> dict[str, str]:
    execution_status = str(execution_review.get("status") or "unknown")
    return {
        "execution_policy": "pass_shadow_ready"
        if execution_status == "paper_order_shadow_ready"
        else f"fail_{execution_status}",
        "staging_contract": "fail_disabled_read_only_contract",
        "paper_account_mirror": "pass_read_only_connected"
        if account_context.get("status") == "ok"
        else f"fail_{account_context.get('status', 'unknown')}",
        "paper_account_write_authority": "pass_disabled"
        if account_context.get("write_authority") is False
        else "fail_write_authority_enabled",
        "live_capital": "pass_disabled"
        if account_context.get("live_capital_enabled") is False
        else "fail_live_capital_enabled",
        "broker_route": "fail_closed_no_broker_write_route",
        "idempotency_key": "fail_not_allocated",
        "event_log_prewrite": "fail_not_written",
        "pre_trade_snapshot": "fail_not_created",
        "post_submit_reconciliation": "fail_not_available",
        "duplicate_order_guard": "fail_not_available",
        "postmortem_link": "fail_not_available",
    }


def _blocked_reasons(checks: dict[str, str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(key for key, value in checks.items() if value.startswith("fail_")))


def _status(blocked_reasons: tuple[str, ...]) -> str:
    if "execution_policy" in blocked_reasons:
        return "blocked_before_staging"
    if "staging_contract" in blocked_reasons:
        return "disabled_contract_hold"
    return "reconciliation_hold"


def _next_steps(blocked_reasons: tuple[str, ...]) -> tuple[str, ...]:
    steps: list[str] = []
    if "execution_policy" in blocked_reasons:
        steps.append("Wait for Execution Policy to return paper-order-shadow-ready.")
    if "staging_contract" in blocked_reasons:
        steps.append("Implement the staged paper-order schema as disabled/read-only first.")
    if "idempotency_key" in blocked_reasons:
        steps.append("Define deterministic idempotency keys before any order can be staged.")
    if "event_log_prewrite" in blocked_reasons:
        steps.append("Require an Event Log prewrite before any future paper-order submission.")
    if "pre_trade_snapshot" in blocked_reasons:
        steps.append("Capture paper-account snapshot before future staging.")
    if "post_submit_reconciliation" in blocked_reasons:
        steps.append("Define broker echo reconciliation before any broker-write route exists.")
    steps.append("Keep staged paper-order creation, broker writes, and live capital disabled.")
    return tuple(dict.fromkeys(steps))[:7]


def validate_staged_paper_order_review(review: StagedPaperOrderReview) -> None:
    if review.schema_version != STAGED_PAPER_ORDER_SCHEMA_VERSION:
        raise ValueError("staged paper-order review schema version mismatch")
    if review.status not in STAGED_PAPER_ORDER_STATUSES:
        raise ValueError(f"invalid staged paper-order review status: {review.status}")
    if review.execution_allowed:
        raise ValueError("staged paper-order contract cannot allow execution")
    if review.staged_paper_order_created:
        raise ValueError("staged paper-order contract cannot create staged orders")
    if review.paper_order_submittable:
        raise ValueError("staged paper-order contract cannot mark orders submittable")
    if review.broker_write_allowed:
        raise ValueError("staged paper-order contract cannot allow broker writes")
    if review.live_capital_enabled:
        raise ValueError("staged paper-order contract cannot enable live capital")
    if review.hypothetical_order.get("status") != "not_created":
        raise ValueError("hypothetical order must remain not_created")


def build_staged_paper_order_review(
    execution_review: dict[str, Any],
    *,
    account_context: dict[str, Any],
) -> StagedPaperOrderReview:
    checks = _reconciliation_checks(execution_review, account_context=account_context)
    blocked = _blocked_reasons(checks)
    review = StagedPaperOrderReview(
        schema_version=STAGED_PAPER_ORDER_SCHEMA_VERSION,
        review_id=str(uuid4()),
        source_execution_policy_review_id=str(execution_review.get("review_id") or "unknown_execution_review"),
        status=_status(blocked),
        instrument=str(execution_review.get("instrument") or "unknown")[:120],
        selected_venue=str(execution_review.get("selected_venue") or "none"),
        venue_mode=str(execution_review.get("venue_mode") or "disabled"),
        account_scope=str(account_context.get("account_scope") or "first_release_gbp_1000_trial"),
        hypothetical_order=_hypothetical_order(execution_review),
        reconciliation_checks=checks,
        blocked_reasons=blocked,
        required_next_steps=_next_steps(blocked),
        execution_allowed=False,
        staged_paper_order_created=False,
        paper_order_submittable=False,
        broker_write_allowed=False,
        live_capital_enabled=False,
        reviewed_at=_now(),
        boundary=(
            "Staged paper-order contract is disabled and read-only. It can describe "
            "a hypothetical order and required reconciliation, but cannot create a "
            "staged order, submit a paper order, enable live capital, or write to brokers."
        ),
    )
    validate_staged_paper_order_review(review)
    return review


class StagedPaperOrderReviewStore:
    def __init__(self, path: str | Path | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self.path = Path(path or Path(self.settings.runtime_dir) / "staged_paper_order_reviews.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, review: StagedPaperOrderReview, *, event_log: EventLog | None = None) -> StagedPaperOrderReview:
        validate_staged_paper_order_review(review)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(review.to_dict(), sort_keys=True) + "\n")
        (event_log or EventLog(echo=False)).write(
            "staged_paper_order_review_recorded",
            "staged_paper_order",
            {
                "review_id": review.review_id,
                "source_execution_policy_review_id": review.source_execution_policy_review_id,
                "status": review.status,
                "selected_venue": review.selected_venue,
                "staged_paper_order_created": review.staged_paper_order_created,
                "paper_order_submittable": review.paper_order_submittable,
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
                    raise ValueError(f"invalid staged paper-order review line {line_number} in {self.path}") from exc
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
                "schema_version": STAGED_PAPER_ORDER_SCHEMA_VERSION,
                "error": str(exc),
            }
        counts = Counter(str(review.get("status", "unknown")) for review in reviews)
        return {
            "status": "ok",
            "schema_version": STAGED_PAPER_ORDER_SCHEMA_VERSION,
            "review_count": len(reviews),
            "by_status": dict(sorted(counts.items())),
            "execution_allowed_count": sum(1 for review in reviews if review.get("execution_allowed") is True),
            "staged_paper_order_created_count": sum(
                1 for review in reviews if review.get("staged_paper_order_created") is True
            ),
            "paper_order_submittable_count": sum(
                1 for review in reviews if review.get("paper_order_submittable") is True
            ),
            "broker_write_allowed_count": sum(1 for review in reviews if review.get("broker_write_allowed") is True),
            "live_capital_enabled_count": sum(1 for review in reviews if review.get("live_capital_enabled") is True),
            "reconciliation_ready_count": sum(
                1
                for review in reviews
                if review.get("status") == "reconciliation_hold"
                and not review.get("blocked_reasons")
            ),
            "boundary": (
                "Staged paper-order reviews are disabled and read-only. They can describe "
                "hypothetical staging and reconciliation requirements, but cannot create "
                "staged orders, submit paper orders, enable live capital, or write to brokers."
            ),
        }


def run_staged_paper_order_contract(
    *,
    settings: Settings | None = None,
    store: StagedPaperOrderReviewStore | None = None,
    event_log: EventLog | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    review_store = store or StagedPaperOrderReviewStore(settings=settings)
    event_log = event_log or EventLog(echo=False)
    account_context = paper_account_shadow_context(settings)
    execution_reviews = ExecutionPolicyReviewStore(settings=settings).read(limit=limit)
    reviews = [
        build_staged_paper_order_review(execution_review, account_context=account_context)
        for execution_review in execution_reviews
    ]
    for review in reviews:
        review_store.write(review, event_log=event_log)
    health = review_store.health()
    return {
        "status": "ok",
        "schema_version": STAGED_PAPER_ORDER_SCHEMA_VERSION,
        "execution_policy_review_count": len(execution_reviews),
        "review_count": len(reviews),
        "blocked_before_staging_count": sum(1 for review in reviews if review.status == "blocked_before_staging"),
        "reconciliation_hold_count": sum(1 for review in reviews if review.status == "reconciliation_hold"),
        "disabled_contract_hold_count": sum(1 for review in reviews if review.status == "disabled_contract_hold"),
        "execution_allowed_count": sum(1 for review in reviews if review.execution_allowed),
        "staged_paper_order_created_count": sum(1 for review in reviews if review.staged_paper_order_created),
        "paper_order_submittable_count": sum(1 for review in reviews if review.paper_order_submittable),
        "broker_write_allowed_count": sum(1 for review in reviews if review.broker_write_allowed),
        "live_capital_enabled_count": sum(1 for review in reviews if review.live_capital_enabled),
        "store": health,
        "event_log": event_log.health(),
        "boundary": health["boundary"],
    }


def staged_paper_order_summary(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    return StagedPaperOrderReviewStore(settings=settings).health()
