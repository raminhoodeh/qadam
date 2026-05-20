#!/usr/bin/env python3
"""Validate read-only broker reconciliation contract."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.broker_reconciliation import (  # noqa: E402
    BROKER_RECONCILIATION_STATUSES,
    BrokerReconciliationReviewStore,
    broker_reconciliation_summary,
    run_broker_reconciliation_contract,
)
from orchestrator.config import Settings  # noqa: E402
from orchestrator.execution_policy import run_execution_policy_router  # noqa: E402
from orchestrator.risk_agent import run_risk_policy_router  # noqa: E402
from orchestrator.signal_integrity import run_signal_integrity_gate  # noqa: E402
from orchestrator.staged_paper_order import run_staged_paper_order_contract  # noqa: E402
from orchestrator.trade_intent import ensure_d5_sample_trade_intents  # noqa: E402

REQUIRED_REVIEW_FIELDS = {
    "account_scope",
    "blocked_reasons",
    "boundary",
    "broker_echo",
    "broker_echo_verified",
    "broker_write_allowed",
    "duplicate_order_guard_ready",
    "event_log_prewrite_created",
    "hypothetical_order",
    "idempotency_key_allocated",
    "instrument",
    "live_capital_enabled",
    "paper_order_submit_allowed",
    "post_submit_reconciliation_ready",
    "postmortem_link_ready",
    "pre_trade_snapshot_created",
    "reconciliation_checks",
    "required_next_steps",
    "review_id",
    "reviewed_at",
    "schema_version",
    "selected_venue",
    "source_execution_policy_review_id",
    "source_staged_paper_order_review_id",
    "status",
    "venue_mode",
}

REQUIRED_BROKER_ECHO_FIELDS = {
    "ack_status",
    "adapter",
    "client_order_id",
    "external_order_id",
    "fill_status",
    "raw_broker_payload_stored",
    "status",
    "submitted_at",
    "venue",
}

REQUIRED_RECONCILIATION_CHECKS = {
    "broker_adapter_mode",
    "broker_echo",
    "broker_route",
    "duplicate_order_guard",
    "event_log_prewrite",
    "idempotency_key",
    "kill_switch",
    "live_capital",
    "paper_account_mirror",
    "paper_account_write_authority",
    "paper_order_submittable",
    "post_submit_reconciliation",
    "postmortem_link",
    "pre_trade_snapshot",
    "source_staged_status",
    "staged_order_contract",
    "staged_order_created",
    "venue_registry_write_health",
}

ZERO_AUTHORITY_KEYS = (
    "idempotency_key_allocated_count",
    "event_log_prewrite_created_count",
    "pre_trade_snapshot_created_count",
    "duplicate_order_guard_ready_count",
    "broker_echo_verified_count",
    "post_submit_reconciliation_ready_count",
    "postmortem_link_ready_count",
    "paper_order_submit_allowed_count",
    "broker_write_allowed_count",
    "live_capital_enabled_count",
)


def main() -> int:
    settings = Settings.from_env()
    ensure_d5_sample_trade_intents(settings)
    run_signal_integrity_gate(settings=settings, seed_sample_if_empty=True)
    run_risk_policy_router(settings=settings)
    run_execution_policy_router(settings=settings)
    run_staged_paper_order_contract(settings=settings)
    result = run_broker_reconciliation_contract(settings=settings)
    summary = broker_reconciliation_summary(settings)
    reviews = BrokerReconciliationReviewStore(settings=settings).read(limit=10)

    print("broker_reconciliation_status=" + result["status"])
    print(f"broker_reconciliation_schema_version={result['schema_version']}")
    print(f"broker_reconciliation_review_count={result['review_count']}")
    print(
        "broker_reconciliation_blocked_before_count="
        f"{result['blocked_before_broker_reconciliation_count']}"
    )
    print(f"broker_reconciliation_route_closed_count={result['broker_route_closed_count']}")
    print(
        "broker_reconciliation_contract_hold_count="
        f"{result['reconciliation_contract_hold_count']}"
    )
    for count_key in ZERO_AUTHORITY_KEYS:
        print(f"broker_reconciliation_{count_key}={result[count_key]}")
    print("broker_reconciliation_store_status=" + summary["status"])
    print(f"broker_reconciliation_total_store_reviews={summary['review_count']}")
    print(f"broker_reconciliation_by_status={summary['by_status']}")
    print("broker_reconciliation_boundary=" + summary["boundary"])

    if result["status"] != "ok" or summary["status"] != "ok":
        print("broker_reconciliation_not_ok=true")
        return 1
    if result["review_count"] < 1 or not reviews:
        print("broker_reconciliation_reviews_missing=true")
        return 1
    for count_key in ZERO_AUTHORITY_KEYS:
        if result[count_key] != 0:
            print(f"broker_reconciliation_authority_not_zero={count_key}")
            return 1
    if "cannot submit paper orders" not in summary["boundary"]:
        print("broker_reconciliation_boundary_weak=true")
        return 1

    for review in reviews:
        missing = sorted(REQUIRED_REVIEW_FIELDS - set(review))
        if missing:
            print(
                "broker_reconciliation_review_fields_missing="
                f"{review.get('review_id', 'unknown')}:{','.join(missing)}"
            )
            return 1
        if review.get("status") not in BROKER_RECONCILIATION_STATUSES:
            print(f"broker_reconciliation_review_invalid_status={review.get('review_id', 'unknown')}")
            return 1
        for flag in (
            "idempotency_key_allocated",
            "event_log_prewrite_created",
            "pre_trade_snapshot_created",
            "duplicate_order_guard_ready",
            "broker_echo_verified",
            "post_submit_reconciliation_ready",
            "postmortem_link_ready",
            "paper_order_submit_allowed",
            "broker_write_allowed",
            "live_capital_enabled",
        ):
            if review.get(flag) is not False:
                print(f"broker_reconciliation_review_flag_not_false={review.get('review_id', 'unknown')}:{flag}")
                return 1
        broker_echo = review.get("broker_echo", {})
        missing_echo = sorted(REQUIRED_BROKER_ECHO_FIELDS - set(broker_echo))
        if missing_echo:
            print(
                "broker_reconciliation_echo_fields_missing="
                f"{review.get('review_id', 'unknown')}:{','.join(missing_echo)}"
            )
            return 1
        if broker_echo.get("status") != "not_requested":
            print(f"broker_reconciliation_echo_requested={review.get('review_id', 'unknown')}")
            return 1
        missing_checks = sorted(REQUIRED_RECONCILIATION_CHECKS - set(review.get("reconciliation_checks", {})))
        if missing_checks:
            print(
                "broker_reconciliation_checks_missing="
                f"{review.get('review_id', 'unknown')}:{','.join(missing_checks)}"
            )
            return 1
        check_values = set(review.get("reconciliation_checks", {}).values())
        if "fail_closed_no_broker_submit_route" not in check_values:
            print(f"broker_reconciliation_broker_route_not_fail_closed={review.get('review_id', 'unknown')}")
            return 1
        if "fail_not_allocated" not in check_values or "fail_not_written" not in check_values:
            print(f"broker_reconciliation_core_guards_missing={review.get('review_id', 'unknown')}")
            return 1
        if "cannot submit paper orders" not in review.get("boundary", ""):
            print(f"broker_reconciliation_review_boundary_weak={review.get('review_id', 'unknown')}")
            return 1

    print("broker_reconciliation_contract_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
