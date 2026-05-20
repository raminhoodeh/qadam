"""Dry-run paper-submit receipt contract.

This layer sits after read-only broker reconciliation. It can describe the
receipt that a future paper-submit adapter would need to produce, but it cannot
call Alpaca, submit a paper order, create broker records, enable live capital,
or write to brokers.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from orchestrator.broker_reconciliation import BrokerReconciliationReviewStore
from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.execution import execution_registry
from orchestrator.paper_account import paper_account_shadow_context

PAPER_SUBMIT_RECEIPT_SCHEMA_VERSION = 1
PAPER_SUBMIT_RECEIPT_STATUSES = {
    "blocked_before_dry_run_submit",
    "dry_run_receipt_blocked",
    "dry_run_receipt_ready",
}


@dataclass(frozen=True)
class PaperSubmitReceiptReview:
    schema_version: int
    review_id: str
    source_broker_reconciliation_review_id: str
    source_staged_paper_order_review_id: str
    source_execution_policy_review_id: str
    status: str
    instrument: str
    selected_venue: str
    venue_mode: str
    account_scope: str
    hypothetical_order: dict[str, Any]
    broker_echo: dict[str, Any]
    simulated_receipt: dict[str, Any]
    receipt_checks: dict[str, str]
    blocked_reasons: tuple[str, ...]
    required_next_steps: tuple[str, ...]
    dry_run_receipt_created: bool
    paper_order_submitted: bool
    broker_post_called: bool
    broker_write_allowed: bool
    live_capital_enabled: bool
    submitted_at: str
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


def _receipt_ready(
    broker_review: dict[str, Any],
    *,
    account_context: dict[str, Any],
    venue: dict[str, Any],
) -> bool:
    required_true_flags = (
        "idempotency_key_allocated",
        "event_log_prewrite_created",
        "pre_trade_snapshot_created",
        "duplicate_order_guard_ready",
        "broker_echo_verified",
        "post_submit_reconciliation_ready",
        "postmortem_link_ready",
        "paper_order_submit_allowed",
    )
    required_false_flags = ("broker_write_allowed", "live_capital_enabled")
    return (
        broker_review.get("status") == "reconciliation_contract_hold"
        and all(broker_review.get(flag) is True for flag in required_true_flags)
        and all(broker_review.get(flag) is False for flag in required_false_flags)
        and account_context.get("write_authority") is False
        and account_context.get("live_capital_enabled") is False
        and str(venue.get("kill_switch_status") or "") == "armed"
    )


def _simulated_receipt(
    broker_review: dict[str, Any],
    *,
    venue: dict[str, Any],
    dry_run_receipt_created: bool,
) -> dict[str, Any]:
    broker_echo = broker_review.get("broker_echo", {})
    if dry_run_receipt_created:
        return {
            "status": "simulated_created",
            "mode": "dry_run_only",
            "adapter": str(venue.get("adapter") or broker_echo.get("adapter") or "none"),
            "venue": str(broker_review.get("selected_venue") or venue.get("key") or "none"),
            "client_order_id": "simulated_only_not_allocated_for_broker",
            "external_order_id": "simulated_only_not_created_at_broker",
            "broker_post_called": False,
            "paper_order_submitted": False,
            "raw_broker_payload_stored": False,
        }
    return {
        "status": "not_created",
        "mode": "dry_run_only",
        "adapter": str(venue.get("adapter") or broker_echo.get("adapter") or "none"),
        "venue": str(broker_review.get("selected_venue") or venue.get("key") or "none"),
        "client_order_id": "not_allocated",
        "external_order_id": "not_created",
        "broker_post_called": False,
        "paper_order_submitted": False,
        "raw_broker_payload_stored": False,
    }


def _checks(
    broker_review: dict[str, Any],
    *,
    account_context: dict[str, Any],
    venue: dict[str, Any],
    dry_run_receipt_created: bool,
) -> dict[str, str]:
    broker_status = str(broker_review.get("status") or "unknown")
    write_health = str(venue.get("write_health") or "unknown")
    return {
        "broker_reconciliation_contract": "pass_reviewed"
        if broker_review.get("review_id")
        else "fail_missing_broker_reconciliation_review",
        "broker_reconciliation_status": "pass_reconciliation_contract_hold"
        if broker_status == "reconciliation_contract_hold"
        else f"fail_{broker_status}",
        "idempotency_key": "pass_allocated"
        if broker_review.get("idempotency_key_allocated") is True
        else "fail_not_allocated",
        "event_log_prewrite": "pass_written"
        if broker_review.get("event_log_prewrite_created") is True
        else "fail_not_written",
        "pre_trade_snapshot": "pass_created"
        if broker_review.get("pre_trade_snapshot_created") is True
        else "fail_not_created",
        "duplicate_order_guard": "pass_ready"
        if broker_review.get("duplicate_order_guard_ready") is True
        else "fail_not_ready",
        "broker_echo": "pass_verified"
        if broker_review.get("broker_echo_verified") is True
        else "fail_not_verified",
        "post_submit_reconciliation": "pass_ready"
        if broker_review.get("post_submit_reconciliation_ready") is True
        else "fail_not_ready",
        "postmortem_link": "pass_ready"
        if broker_review.get("postmortem_link_ready") is True
        else "fail_not_ready",
        "paper_order_submit_permission": "pass_shadow_permission"
        if broker_review.get("paper_order_submit_allowed") is True
        else "fail_submit_not_allowed",
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
        "dry_run_receipt": "pass_simulated_created"
        if dry_run_receipt_created
        else "fail_not_created_until_prerequisites_pass",
        "broker_post": "pass_not_called",
        "paper_order_submission": "pass_not_submitted",
        "broker_write": "pass_disabled",
    }


def _blocked_reasons(checks: dict[str, str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(key for key, value in checks.items() if value.startswith("fail_")))


def _status(blocked_reasons: tuple[str, ...]) -> str:
    if "broker_reconciliation_status" in blocked_reasons:
        return "blocked_before_dry_run_submit"
    if "dry_run_receipt" in blocked_reasons:
        return "dry_run_receipt_blocked"
    return "dry_run_receipt_ready"


def _next_steps(blocked_reasons: tuple[str, ...]) -> tuple[str, ...]:
    steps: list[str] = []
    if "broker_reconciliation_status" in blocked_reasons:
        steps.append("Wait for broker reconciliation to reach reconciliation-contract hold.")
    if "idempotency_key" in blocked_reasons:
        steps.append("Define deterministic client-order idempotency before simulated receipt creation.")
    if "event_log_prewrite" in blocked_reasons:
        steps.append("Require Event Log prewrite before any simulated submit receipt.")
    if "pre_trade_snapshot" in blocked_reasons:
        steps.append("Capture pre-trade paper-account snapshot before dry-run receipt creation.")
    if "duplicate_order_guard" in blocked_reasons:
        steps.append("Require duplicate-order guard before dry-run receipt creation.")
    if "broker_echo" in blocked_reasons or "post_submit_reconciliation" in blocked_reasons:
        steps.append("Define broker echo and post-submit reconciliation before dry-run receipt creation.")
    if "dry_run_receipt" in blocked_reasons:
        steps.append("Create simulated receipt only after all reconciliation prerequisites pass.")
    steps.append("Keep Alpaca POST, broker writes, paper-order submission, and live capital disabled.")
    return tuple(dict.fromkeys(steps))[:8]


def validate_paper_submit_receipt_review(review: PaperSubmitReceiptReview) -> None:
    if review.schema_version != PAPER_SUBMIT_RECEIPT_SCHEMA_VERSION:
        raise ValueError("paper-submit receipt review schema version mismatch")
    if review.status not in PAPER_SUBMIT_RECEIPT_STATUSES:
        raise ValueError(f"invalid paper-submit receipt status: {review.status}")
    if review.paper_order_submitted:
        raise ValueError("paper-submit receipt contract cannot submit paper orders")
    if review.broker_post_called:
        raise ValueError("paper-submit receipt contract cannot call broker POST routes")
    if review.broker_write_allowed:
        raise ValueError("paper-submit receipt contract cannot allow broker writes")
    if review.live_capital_enabled:
        raise ValueError("paper-submit receipt contract cannot enable live capital")
    if review.submitted_at != "not_submitted":
        raise ValueError("paper-submit receipt submitted_at must remain not_submitted")
    if review.simulated_receipt.get("broker_post_called") is not False:
        raise ValueError("simulated receipt must not call broker POST")
    if review.simulated_receipt.get("paper_order_submitted") is not False:
        raise ValueError("simulated receipt must not submit paper orders")
    if review.simulated_receipt.get("raw_broker_payload_stored") is not False:
        raise ValueError("simulated receipt must not store raw broker payloads")


def build_paper_submit_receipt_review(
    broker_review: dict[str, Any],
    *,
    account_context: dict[str, Any],
) -> PaperSubmitReceiptReview:
    venue = _venue(str(broker_review.get("selected_venue") or "none"))
    dry_run_receipt_created = _receipt_ready(broker_review, account_context=account_context, venue=venue)
    checks = _checks(
        broker_review,
        account_context=account_context,
        venue=venue,
        dry_run_receipt_created=dry_run_receipt_created,
    )
    blocked = _blocked_reasons(checks)
    review = PaperSubmitReceiptReview(
        schema_version=PAPER_SUBMIT_RECEIPT_SCHEMA_VERSION,
        review_id=str(uuid4()),
        source_broker_reconciliation_review_id=str(
            broker_review.get("review_id") or "unknown_broker_reconciliation_review"
        ),
        source_staged_paper_order_review_id=str(
            broker_review.get("source_staged_paper_order_review_id") or "unknown_staged_review"
        ),
        source_execution_policy_review_id=str(
            broker_review.get("source_execution_policy_review_id") or "unknown_execution_review"
        ),
        status=_status(blocked),
        instrument=str(broker_review.get("instrument") or "unknown")[:120],
        selected_venue=str(broker_review.get("selected_venue") or venue.get("key") or "none"),
        venue_mode=str(broker_review.get("venue_mode") or venue.get("mode") or "disabled"),
        account_scope=str(broker_review.get("account_scope") or account_context.get("account_scope") or "paper"),
        hypothetical_order=broker_review.get("hypothetical_order", {}),
        broker_echo=broker_review.get("broker_echo", {}),
        simulated_receipt=_simulated_receipt(
            broker_review,
            venue=venue,
            dry_run_receipt_created=dry_run_receipt_created,
        ),
        receipt_checks=checks,
        blocked_reasons=blocked,
        required_next_steps=_next_steps(blocked),
        dry_run_receipt_created=dry_run_receipt_created,
        paper_order_submitted=False,
        broker_post_called=False,
        broker_write_allowed=False,
        live_capital_enabled=False,
        submitted_at="not_submitted",
        reviewed_at=_now(),
        boundary=(
            "Paper-submit receipt contract is dry-run only. It can create a simulated "
            "receipt only after broker reconciliation prerequisites pass, but it cannot "
            "call Alpaca POST routes, submit paper orders, enable live capital, or write "
            "to brokers."
        ),
    )
    validate_paper_submit_receipt_review(review)
    return review


class PaperSubmitReceiptReviewStore:
    def __init__(self, path: str | Path | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self.path = Path(path or Path(self.settings.runtime_dir) / "paper_submit_receipt_reviews.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(
        self,
        review: PaperSubmitReceiptReview,
        *,
        event_log: EventLog | None = None,
    ) -> PaperSubmitReceiptReview:
        validate_paper_submit_receipt_review(review)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(review.to_dict(), sort_keys=True) + "\n")
        (event_log or EventLog(echo=False)).write(
            "paper_submit_receipt_review_recorded",
            "paper_submit_receipt",
            {
                "review_id": review.review_id,
                "source_broker_reconciliation_review_id": review.source_broker_reconciliation_review_id,
                "status": review.status,
                "selected_venue": review.selected_venue,
                "dry_run_receipt_created": review.dry_run_receipt_created,
                "paper_order_submitted": review.paper_order_submitted,
                "broker_post_called": review.broker_post_called,
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
                    raise ValueError(f"invalid paper-submit receipt review line {line_number} in {self.path}") from exc
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
                "schema_version": PAPER_SUBMIT_RECEIPT_SCHEMA_VERSION,
                "error": str(exc),
            }
        counts = Counter(str(review.get("status", "unknown")) for review in reviews)
        return {
            "status": "ok",
            "schema_version": PAPER_SUBMIT_RECEIPT_SCHEMA_VERSION,
            "review_count": len(reviews),
            "by_status": dict(sorted(counts.items())),
            "dry_run_receipt_created_count": sum(
                1 for review in reviews if review.get("dry_run_receipt_created") is True
            ),
            "paper_order_submitted_count": sum(
                1 for review in reviews if review.get("paper_order_submitted") is True
            ),
            "broker_post_called_count": sum(1 for review in reviews if review.get("broker_post_called") is True),
            "broker_write_allowed_count": sum(1 for review in reviews if review.get("broker_write_allowed") is True),
            "live_capital_enabled_count": sum(1 for review in reviews if review.get("live_capital_enabled") is True),
            "boundary": (
                "Paper-submit receipt reviews are dry-run only. They can create a simulated "
                "receipt only after broker reconciliation prerequisites pass, but cannot call "
                "broker POST routes, submit paper orders, enable live capital, or write to brokers."
            ),
        }


def run_paper_submit_receipt_contract(
    *,
    settings: Settings | None = None,
    store: PaperSubmitReceiptReviewStore | None = None,
    event_log: EventLog | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    review_store = store or PaperSubmitReceiptReviewStore(settings=settings)
    event_log = event_log or EventLog(echo=False)
    account_context = paper_account_shadow_context(settings)
    broker_reviews = BrokerReconciliationReviewStore(settings=settings).read(limit=limit)
    reviews = [
        build_paper_submit_receipt_review(broker_review, account_context=account_context)
        for broker_review in broker_reviews
    ]
    for review in reviews:
        review_store.write(review, event_log=event_log)
    health = review_store.health()
    return {
        "status": "ok",
        "schema_version": PAPER_SUBMIT_RECEIPT_SCHEMA_VERSION,
        "broker_reconciliation_review_count": len(broker_reviews),
        "review_count": len(reviews),
        "blocked_before_dry_run_submit_count": sum(
            1 for review in reviews if review.status == "blocked_before_dry_run_submit"
        ),
        "dry_run_receipt_blocked_count": sum(1 for review in reviews if review.status == "dry_run_receipt_blocked"),
        "dry_run_receipt_ready_count": sum(1 for review in reviews if review.status == "dry_run_receipt_ready"),
        "dry_run_receipt_created_count": sum(1 for review in reviews if review.dry_run_receipt_created),
        "paper_order_submitted_count": sum(1 for review in reviews if review.paper_order_submitted),
        "broker_post_called_count": sum(1 for review in reviews if review.broker_post_called),
        "broker_write_allowed_count": sum(1 for review in reviews if review.broker_write_allowed),
        "live_capital_enabled_count": sum(1 for review in reviews if review.live_capital_enabled),
        "store": health,
        "event_log": event_log.health(),
        "boundary": health["boundary"],
    }


def paper_submit_receipt_summary(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    return PaperSubmitReceiptReviewStore(settings=settings).health()
