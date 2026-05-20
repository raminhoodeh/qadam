"""Read-only broker adapter and reconciliation contract.

This layer sits after the disabled staged paper-order contract. It defines the
broker echo, idempotency, Event Log prewrite, duplicate-order guard,
post-submit reconciliation, and postmortem links that must exist before any
paper-order submit route can be considered. It cannot submit, create, or write
orders.
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
from orchestrator.staged_paper_order import StagedPaperOrderReviewStore

BROKER_RECONCILIATION_SCHEMA_VERSION = 1
BROKER_RECONCILIATION_STATUSES = {
    "blocked_before_broker_reconciliation",
    "broker_route_closed",
    "reconciliation_contract_hold",
}


@dataclass(frozen=True)
class BrokerReconciliationReview:
    schema_version: int
    review_id: str
    source_staged_paper_order_review_id: str
    source_execution_policy_review_id: str
    status: str
    instrument: str
    selected_venue: str
    venue_mode: str
    account_scope: str
    hypothetical_order: dict[str, Any]
    broker_echo: dict[str, Any]
    reconciliation_checks: dict[str, str]
    blocked_reasons: tuple[str, ...]
    required_next_steps: tuple[str, ...]
    idempotency_key_allocated: bool
    event_log_prewrite_created: bool
    pre_trade_snapshot_created: bool
    duplicate_order_guard_ready: bool
    broker_echo_verified: bool
    post_submit_reconciliation_ready: bool
    postmortem_link_ready: bool
    paper_order_submit_allowed: bool
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


def _venue(selected_venue: str) -> dict[str, Any]:
    for venue in execution_registry():
        if venue.get("key") == selected_venue:
            return venue
    return {
        "key": selected_venue or "none",
        "adapter": "none",
        "mode": "disabled",
        "write_health": "blocked_no_registered_venue",
        "read_health": "not_started",
        "kill_switch_status": "armed",
    }


def _broker_echo(staged_review: dict[str, Any], venue: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "not_requested",
        "adapter": str(venue.get("adapter") or "none"),
        "venue": str(staged_review.get("selected_venue") or venue.get("key") or "none"),
        "external_order_id": "not_created",
        "client_order_id": "not_allocated",
        "submitted_at": "not_submitted",
        "ack_status": "not_available",
        "fill_status": "not_available",
        "raw_broker_payload_stored": False,
    }


def _checks(
    staged_review: dict[str, Any],
    *,
    account_context: dict[str, Any],
    venue: dict[str, Any],
) -> dict[str, str]:
    staged_status = str(staged_review.get("status") or "unknown")
    write_health = str(venue.get("write_health") or "unknown")
    return {
        "staged_order_contract": "pass_reviewed"
        if staged_review.get("review_id")
        else "fail_missing_staged_review",
        "staged_order_created": "pass_not_created"
        if staged_review.get("staged_paper_order_created") is False
        else "fail_staged_order_created_unexpectedly",
        "paper_order_submittable": "pass_disabled"
        if staged_review.get("paper_order_submittable") is False
        else "fail_paper_order_submittable",
        "source_staged_status": f"fail_{staged_status}"
        if staged_status != "reconciliation_hold"
        else "pass_reconciliation_hold",
        "broker_adapter_mode": "fail_read_only_contract_no_submit_adapter",
        "broker_route": "fail_closed_no_broker_submit_route",
        "venue_registry_write_health": f"pass_{write_health}"
        if write_health.startswith("blocked")
        else "fail_unexpected_write_health",
        "kill_switch": "pass_armed"
        if str(venue.get("kill_switch_status") or "") == "armed"
        else "fail_kill_switch_not_armed",
        "paper_account_mirror": "pass_read_only_connected"
        if account_context.get("status") == "ok"
        else f"fail_{account_context.get('status', 'unknown')}",
        "paper_account_write_authority": "pass_disabled"
        if account_context.get("write_authority") is False
        else "fail_write_authority_enabled",
        "live_capital": "pass_disabled"
        if account_context.get("live_capital_enabled") is False
        else "fail_live_capital_enabled",
        "idempotency_key": "fail_not_allocated",
        "event_log_prewrite": "fail_not_written",
        "pre_trade_snapshot": "fail_not_created",
        "duplicate_order_guard": "fail_not_available",
        "broker_echo": "fail_not_available",
        "post_submit_reconciliation": "fail_not_available",
        "postmortem_link": "fail_not_available",
    }


def _blocked_reasons(checks: dict[str, str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(key for key, value in checks.items() if value.startswith("fail_")))


def _status(blocked_reasons: tuple[str, ...]) -> str:
    if "source_staged_status" in blocked_reasons:
        return "blocked_before_broker_reconciliation"
    if "broker_route" in blocked_reasons or "broker_adapter_mode" in blocked_reasons:
        return "broker_route_closed"
    return "reconciliation_contract_hold"


def _next_steps(blocked_reasons: tuple[str, ...]) -> tuple[str, ...]:
    steps: list[str] = []
    if "source_staged_status" in blocked_reasons:
        steps.append("Wait for staged paper-order contract to reach reconciliation hold.")
    if "broker_adapter_mode" in blocked_reasons or "broker_route" in blocked_reasons:
        steps.append("Keep broker submit adapters disabled while defining the read-only adapter contract.")
    if "idempotency_key" in blocked_reasons:
        steps.append("Define deterministic client-order idempotency keys.")
    if "event_log_prewrite" in blocked_reasons:
        steps.append("Require Event Log prewrite before any future paper-order submission.")
    if "pre_trade_snapshot" in blocked_reasons:
        steps.append("Capture paper-account snapshot before any future paper-order submission.")
    if "duplicate_order_guard" in blocked_reasons:
        steps.append("Define duplicate-order guard before any submit route exists.")
    if "broker_echo" in blocked_reasons or "post_submit_reconciliation" in blocked_reasons:
        steps.append("Define broker echo and post-submit reconciliation before broker writes.")
    steps.append("Keep paper-order submission, broker writes, and live capital disabled.")
    return tuple(dict.fromkeys(steps))[:8]


def validate_broker_reconciliation_review(review: BrokerReconciliationReview) -> None:
    if review.schema_version != BROKER_RECONCILIATION_SCHEMA_VERSION:
        raise ValueError("broker reconciliation review schema version mismatch")
    if review.status not in BROKER_RECONCILIATION_STATUSES:
        raise ValueError(f"invalid broker reconciliation review status: {review.status}")
    if review.idempotency_key_allocated:
        raise ValueError("broker reconciliation contract cannot allocate idempotency keys yet")
    if review.event_log_prewrite_created:
        raise ValueError("broker reconciliation contract cannot create Event Log prewrites yet")
    if review.pre_trade_snapshot_created:
        raise ValueError("broker reconciliation contract cannot create pre-trade snapshots yet")
    if review.duplicate_order_guard_ready:
        raise ValueError("broker reconciliation contract cannot mark duplicate guards ready yet")
    if review.broker_echo_verified:
        raise ValueError("broker reconciliation contract cannot verify broker echo yet")
    if review.post_submit_reconciliation_ready:
        raise ValueError("broker reconciliation contract cannot mark post-submit reconciliation ready yet")
    if review.postmortem_link_ready:
        raise ValueError("broker reconciliation contract cannot mark postmortem links ready yet")
    if review.paper_order_submit_allowed:
        raise ValueError("broker reconciliation contract cannot allow paper-order submission")
    if review.broker_write_allowed:
        raise ValueError("broker reconciliation contract cannot allow broker writes")
    if review.live_capital_enabled:
        raise ValueError("broker reconciliation contract cannot enable live capital")
    if review.broker_echo.get("status") != "not_requested":
        raise ValueError("broker echo must remain not_requested")


def build_broker_reconciliation_review(
    staged_review: dict[str, Any],
    *,
    account_context: dict[str, Any],
) -> BrokerReconciliationReview:
    venue = _venue(str(staged_review.get("selected_venue") or "none"))
    checks = _checks(staged_review, account_context=account_context, venue=venue)
    blocked = _blocked_reasons(checks)
    review = BrokerReconciliationReview(
        schema_version=BROKER_RECONCILIATION_SCHEMA_VERSION,
        review_id=str(uuid4()),
        source_staged_paper_order_review_id=str(staged_review.get("review_id") or "unknown_staged_review"),
        source_execution_policy_review_id=str(
            staged_review.get("source_execution_policy_review_id") or "unknown_execution_review"
        ),
        status=_status(blocked),
        instrument=str(staged_review.get("instrument") or "unknown")[:120],
        selected_venue=str(staged_review.get("selected_venue") or venue.get("key") or "none"),
        venue_mode=str(staged_review.get("venue_mode") or venue.get("mode") or "disabled"),
        account_scope=str(staged_review.get("account_scope") or account_context.get("account_scope") or "paper"),
        hypothetical_order=staged_review.get("hypothetical_order", {}),
        broker_echo=_broker_echo(staged_review, venue),
        reconciliation_checks=checks,
        blocked_reasons=blocked,
        required_next_steps=_next_steps(blocked),
        idempotency_key_allocated=False,
        event_log_prewrite_created=False,
        pre_trade_snapshot_created=False,
        duplicate_order_guard_ready=False,
        broker_echo_verified=False,
        post_submit_reconciliation_ready=False,
        postmortem_link_ready=False,
        paper_order_submit_allowed=False,
        broker_write_allowed=False,
        live_capital_enabled=False,
        reviewed_at=_now(),
        boundary=(
            "Broker reconciliation contract is read-only. It can define broker echo, "
            "idempotency, Event Log prewrite, duplicate-order guard, post-submit "
            "reconciliation, and postmortem requirements, but cannot submit paper "
            "orders, create broker orders, enable live capital, or write to brokers."
        ),
    )
    validate_broker_reconciliation_review(review)
    return review


class BrokerReconciliationReviewStore:
    def __init__(self, path: str | Path | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self.path = Path(path or Path(self.settings.runtime_dir) / "broker_reconciliation_reviews.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(
        self,
        review: BrokerReconciliationReview,
        *,
        event_log: EventLog | None = None,
    ) -> BrokerReconciliationReview:
        validate_broker_reconciliation_review(review)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(review.to_dict(), sort_keys=True) + "\n")
        (event_log or EventLog(echo=False)).write(
            "broker_reconciliation_review_recorded",
            "broker_reconciliation",
            {
                "review_id": review.review_id,
                "source_staged_paper_order_review_id": review.source_staged_paper_order_review_id,
                "status": review.status,
                "selected_venue": review.selected_venue,
                "paper_order_submit_allowed": review.paper_order_submit_allowed,
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
                    raise ValueError(f"invalid broker reconciliation review line {line_number} in {self.path}") from exc
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
                "schema_version": BROKER_RECONCILIATION_SCHEMA_VERSION,
                "error": str(exc),
            }
        counts = Counter(str(review.get("status", "unknown")) for review in reviews)
        return {
            "status": "ok",
            "schema_version": BROKER_RECONCILIATION_SCHEMA_VERSION,
            "review_count": len(reviews),
            "by_status": dict(sorted(counts.items())),
            "idempotency_key_allocated_count": sum(
                1 for review in reviews if review.get("idempotency_key_allocated") is True
            ),
            "event_log_prewrite_created_count": sum(
                1 for review in reviews if review.get("event_log_prewrite_created") is True
            ),
            "pre_trade_snapshot_created_count": sum(
                1 for review in reviews if review.get("pre_trade_snapshot_created") is True
            ),
            "duplicate_order_guard_ready_count": sum(
                1 for review in reviews if review.get("duplicate_order_guard_ready") is True
            ),
            "broker_echo_verified_count": sum(1 for review in reviews if review.get("broker_echo_verified") is True),
            "post_submit_reconciliation_ready_count": sum(
                1 for review in reviews if review.get("post_submit_reconciliation_ready") is True
            ),
            "postmortem_link_ready_count": sum(1 for review in reviews if review.get("postmortem_link_ready") is True),
            "paper_order_submit_allowed_count": sum(
                1 for review in reviews if review.get("paper_order_submit_allowed") is True
            ),
            "broker_write_allowed_count": sum(1 for review in reviews if review.get("broker_write_allowed") is True),
            "live_capital_enabled_count": sum(1 for review in reviews if review.get("live_capital_enabled") is True),
            "boundary": (
                "Broker reconciliation reviews are read-only. They can define broker echo, "
                "idempotency, Event Log prewrite, duplicate-order guard, post-submit "
                "reconciliation, and postmortem requirements, but cannot submit paper "
                "orders, create broker orders, enable live capital, or write to brokers."
            ),
        }


def run_broker_reconciliation_contract(
    *,
    settings: Settings | None = None,
    store: BrokerReconciliationReviewStore | None = None,
    event_log: EventLog | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    review_store = store or BrokerReconciliationReviewStore(settings=settings)
    event_log = event_log or EventLog(echo=False)
    account_context = paper_account_shadow_context(settings)
    staged_reviews = StagedPaperOrderReviewStore(settings=settings).read(limit=limit)
    reviews = [
        build_broker_reconciliation_review(staged_review, account_context=account_context)
        for staged_review in staged_reviews
    ]
    for review in reviews:
        review_store.write(review, event_log=event_log)
    health = review_store.health()
    return {
        "status": "ok",
        "schema_version": BROKER_RECONCILIATION_SCHEMA_VERSION,
        "staged_paper_order_review_count": len(staged_reviews),
        "review_count": len(reviews),
        "blocked_before_broker_reconciliation_count": sum(
            1 for review in reviews if review.status == "blocked_before_broker_reconciliation"
        ),
        "broker_route_closed_count": sum(1 for review in reviews if review.status == "broker_route_closed"),
        "reconciliation_contract_hold_count": sum(
            1 for review in reviews if review.status == "reconciliation_contract_hold"
        ),
        "idempotency_key_allocated_count": sum(1 for review in reviews if review.idempotency_key_allocated),
        "event_log_prewrite_created_count": sum(1 for review in reviews if review.event_log_prewrite_created),
        "pre_trade_snapshot_created_count": sum(1 for review in reviews if review.pre_trade_snapshot_created),
        "duplicate_order_guard_ready_count": sum(1 for review in reviews if review.duplicate_order_guard_ready),
        "broker_echo_verified_count": sum(1 for review in reviews if review.broker_echo_verified),
        "post_submit_reconciliation_ready_count": sum(
            1 for review in reviews if review.post_submit_reconciliation_ready
        ),
        "postmortem_link_ready_count": sum(1 for review in reviews if review.postmortem_link_ready),
        "paper_order_submit_allowed_count": sum(1 for review in reviews if review.paper_order_submit_allowed),
        "broker_write_allowed_count": sum(1 for review in reviews if review.broker_write_allowed),
        "live_capital_enabled_count": sum(1 for review in reviews if review.live_capital_enabled),
        "store": health,
        "event_log": event_log.health(),
        "boundary": health["boundary"],
    }


def broker_reconciliation_summary(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    return BrokerReconciliationReviewStore(settings=settings).health()
