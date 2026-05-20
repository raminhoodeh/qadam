#!/usr/bin/env python3
"""Validate dry-run paper-submit receipt contract."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.broker_reconciliation import run_broker_reconciliation_contract  # noqa: E402
from orchestrator.config import Settings  # noqa: E402
from orchestrator.execution_policy import run_execution_policy_router  # noqa: E402
from orchestrator.paper_submit_receipt import (  # noqa: E402
    PAPER_SUBMIT_RECEIPT_STATUSES,
    PaperSubmitReceiptReviewStore,
    paper_submit_receipt_summary,
    run_paper_submit_receipt_contract,
)
from orchestrator.risk_agent import run_risk_policy_router  # noqa: E402
from orchestrator.signal_integrity import run_signal_integrity_gate  # noqa: E402
from orchestrator.staged_paper_order import run_staged_paper_order_contract  # noqa: E402
from orchestrator.trade_intent import ensure_d5_sample_trade_intents  # noqa: E402

REQUIRED_REVIEW_FIELDS = {
    "account_scope",
    "blocked_reasons",
    "boundary",
    "broker_echo",
    "broker_post_called",
    "broker_write_allowed",
    "dry_run_receipt_created",
    "hypothetical_order",
    "instrument",
    "live_capital_enabled",
    "paper_order_submitted",
    "receipt_checks",
    "required_next_steps",
    "review_id",
    "reviewed_at",
    "schema_version",
    "selected_venue",
    "simulated_receipt",
    "source_broker_reconciliation_review_id",
    "source_execution_policy_review_id",
    "source_staged_paper_order_review_id",
    "status",
    "submitted_at",
    "venue_mode",
}

REQUIRED_SIMULATED_RECEIPT_FIELDS = {
    "adapter",
    "broker_post_called",
    "client_order_id",
    "external_order_id",
    "mode",
    "paper_order_submitted",
    "raw_broker_payload_stored",
    "status",
    "venue",
}

REQUIRED_RECEIPT_CHECKS = {
    "broker_echo",
    "broker_post",
    "broker_reconciliation_contract",
    "broker_reconciliation_status",
    "broker_write",
    "duplicate_order_guard",
    "dry_run_receipt",
    "event_log_prewrite",
    "idempotency_key",
    "kill_switch",
    "live_capital",
    "paper_account_mirror",
    "paper_account_write_authority",
    "paper_order_submission",
    "paper_order_submit_permission",
    "post_submit_reconciliation",
    "postmortem_link",
    "pre_trade_snapshot",
    "venue_registry_write_health",
}

ZERO_AUTHORITY_KEYS = (
    "paper_order_submitted_count",
    "broker_post_called_count",
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
    run_broker_reconciliation_contract(settings=settings)
    result = run_paper_submit_receipt_contract(settings=settings)
    summary = paper_submit_receipt_summary(settings)
    reviews = PaperSubmitReceiptReviewStore(settings=settings).read(limit=10)

    print("paper_submit_receipt_status=" + result["status"])
    print(f"paper_submit_receipt_schema_version={result['schema_version']}")
    print(f"paper_submit_receipt_review_count={result['review_count']}")
    print(f"paper_submit_receipt_blocked_before_count={result['blocked_before_dry_run_submit_count']}")
    print(f"paper_submit_receipt_dry_run_blocked_count={result['dry_run_receipt_blocked_count']}")
    print(f"paper_submit_receipt_dry_run_ready_count={result['dry_run_receipt_ready_count']}")
    print(f"paper_submit_receipt_dry_run_created_count={result['dry_run_receipt_created_count']}")
    for count_key in ZERO_AUTHORITY_KEYS:
        print(f"paper_submit_receipt_{count_key}={result[count_key]}")
    print("paper_submit_receipt_store_status=" + summary["status"])
    print(f"paper_submit_receipt_total_store_reviews={summary['review_count']}")
    print(f"paper_submit_receipt_by_status={summary['by_status']}")
    print("paper_submit_receipt_boundary=" + summary["boundary"])

    if result["status"] != "ok" or summary["status"] != "ok":
        print("paper_submit_receipt_not_ok=true")
        return 1
    if result["review_count"] < 1 or not reviews:
        print("paper_submit_receipt_reviews_missing=true")
        return 1
    for count_key in ZERO_AUTHORITY_KEYS:
        if result[count_key] != 0:
            print(f"paper_submit_receipt_authority_not_zero={count_key}")
            return 1
    if "cannot call broker POST routes" not in summary["boundary"]:
        print("paper_submit_receipt_boundary_weak=true")
        return 1

    for review in reviews:
        missing = sorted(REQUIRED_REVIEW_FIELDS - set(review))
        if missing:
            print(
                "paper_submit_receipt_review_fields_missing="
                f"{review.get('review_id', 'unknown')}:{','.join(missing)}"
            )
            return 1
        if review.get("status") not in PAPER_SUBMIT_RECEIPT_STATUSES:
            print(f"paper_submit_receipt_review_invalid_status={review.get('review_id', 'unknown')}")
            return 1
        for flag in (
            "paper_order_submitted",
            "broker_post_called",
            "broker_write_allowed",
            "live_capital_enabled",
        ):
            if review.get(flag) is not False:
                print(f"paper_submit_receipt_review_flag_not_false={review.get('review_id', 'unknown')}:{flag}")
                return 1
        receipt = review.get("simulated_receipt", {})
        missing_receipt = sorted(REQUIRED_SIMULATED_RECEIPT_FIELDS - set(receipt))
        if missing_receipt:
            print(
                "paper_submit_receipt_simulated_receipt_fields_missing="
                f"{review.get('review_id', 'unknown')}:{','.join(missing_receipt)}"
            )
            return 1
        if receipt.get("mode") != "dry_run_only":
            print(f"paper_submit_receipt_not_dry_run={review.get('review_id', 'unknown')}")
            return 1
        if receipt.get("broker_post_called") is not False or receipt.get("paper_order_submitted") is not False:
            print(f"paper_submit_receipt_receipt_has_authority={review.get('review_id', 'unknown')}")
            return 1
        missing_checks = sorted(REQUIRED_RECEIPT_CHECKS - set(review.get("receipt_checks", {})))
        if missing_checks:
            print(
                "paper_submit_receipt_checks_missing="
                f"{review.get('review_id', 'unknown')}:{','.join(missing_checks)}"
            )
            return 1
        check_values = set(review.get("receipt_checks", {}).values())
        if "pass_not_called" not in check_values:
            print(f"paper_submit_receipt_broker_post_not_fail_closed={review.get('review_id', 'unknown')}")
            return 1
        if "pass_not_submitted" not in check_values:
            print(f"paper_submit_receipt_submission_not_fail_closed={review.get('review_id', 'unknown')}")
            return 1
        if "cannot call Alpaca POST routes" not in review.get("boundary", ""):
            print(f"paper_submit_receipt_review_boundary_weak={review.get('review_id', 'unknown')}")
            return 1

    print("paper_submit_receipt_contract_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
