#!/usr/bin/env python3
"""Validate disabled staged paper-order contract."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.execution_policy import run_execution_policy_router  # noqa: E402
from orchestrator.risk_agent import run_risk_policy_router  # noqa: E402
from orchestrator.signal_integrity import run_signal_integrity_gate  # noqa: E402
from orchestrator.staged_paper_order import (  # noqa: E402
    STAGED_PAPER_ORDER_STATUSES,
    StagedPaperOrderReviewStore,
    run_staged_paper_order_contract,
    staged_paper_order_summary,
)
from orchestrator.trade_intent import ensure_d5_sample_trade_intents  # noqa: E402

REQUIRED_REVIEW_FIELDS = {
    "account_scope",
    "blocked_reasons",
    "boundary",
    "broker_write_allowed",
    "execution_allowed",
    "hypothetical_order",
    "instrument",
    "live_capital_enabled",
    "paper_order_submittable",
    "reconciliation_checks",
    "required_next_steps",
    "review_id",
    "reviewed_at",
    "schema_version",
    "selected_venue",
    "source_execution_policy_review_id",
    "staged_paper_order_created",
    "status",
    "venue_mode",
}

REQUIRED_HYPOTHETICAL_ORDER_FIELDS = {
    "direction",
    "event_log_ref",
    "idempotency_key",
    "instrument",
    "invalidation",
    "notional_gbp",
    "order_type",
    "quantity",
    "risk_gbp",
    "status",
    "venue",
}

REQUIRED_RECONCILIATION_CHECKS = {
    "broker_route",
    "duplicate_order_guard",
    "event_log_prewrite",
    "execution_policy",
    "idempotency_key",
    "live_capital",
    "paper_account_mirror",
    "paper_account_write_authority",
    "post_submit_reconciliation",
    "postmortem_link",
    "pre_trade_snapshot",
    "staging_contract",
}


def main() -> int:
    settings = Settings.from_env()
    ensure_d5_sample_trade_intents(settings)
    run_signal_integrity_gate(settings=settings, seed_sample_if_empty=True)
    run_risk_policy_router(settings=settings)
    run_execution_policy_router(settings=settings)
    result = run_staged_paper_order_contract(settings=settings)
    summary = staged_paper_order_summary(settings)
    reviews = StagedPaperOrderReviewStore(settings=settings).read(limit=10)

    print("staged_paper_order_status=" + result["status"])
    print(f"staged_paper_order_schema_version={result['schema_version']}")
    print(f"staged_paper_order_review_count={result['review_count']}")
    print(f"staged_paper_order_blocked_before_staging_count={result['blocked_before_staging_count']}")
    print(f"staged_paper_order_reconciliation_hold_count={result['reconciliation_hold_count']}")
    print(f"staged_paper_order_disabled_contract_hold_count={result['disabled_contract_hold_count']}")
    print(f"staged_paper_order_execution_allowed_count={result['execution_allowed_count']}")
    print(f"staged_paper_order_created_count={result['staged_paper_order_created_count']}")
    print(f"staged_paper_order_submittable_count={result['paper_order_submittable_count']}")
    print(f"staged_paper_order_broker_write_allowed_count={result['broker_write_allowed_count']}")
    print(f"staged_paper_order_live_capital_enabled_count={result['live_capital_enabled_count']}")
    print("staged_paper_order_store_status=" + summary["status"])
    print(f"staged_paper_order_total_store_reviews={summary['review_count']}")
    print(f"staged_paper_order_by_status={summary['by_status']}")
    print("staged_paper_order_boundary=" + summary["boundary"])

    if result["status"] != "ok" or summary["status"] != "ok":
        print("staged_paper_order_not_ok=true")
        return 1
    if result["review_count"] < 1 or not reviews:
        print("staged_paper_order_reviews_missing=true")
        return 1
    for count_key in (
        "execution_allowed_count",
        "staged_paper_order_created_count",
        "paper_order_submittable_count",
        "broker_write_allowed_count",
        "live_capital_enabled_count",
    ):
        if result[count_key] != 0:
            print(f"staged_paper_order_authority_not_zero={count_key}")
            return 1
    if "cannot create staged orders" not in summary["boundary"]:
        print("staged_paper_order_boundary_weak=true")
        return 1

    for review in reviews:
        missing = sorted(REQUIRED_REVIEW_FIELDS - set(review))
        if missing:
            print(f"staged_paper_order_review_fields_missing={review.get('review_id', 'unknown')}:{','.join(missing)}")
            return 1
        if review.get("status") not in STAGED_PAPER_ORDER_STATUSES:
            print(f"staged_paper_order_review_invalid_status={review.get('review_id', 'unknown')}")
            return 1
        if review.get("execution_allowed") is not False:
            print(f"staged_paper_order_review_execution_allowed={review.get('review_id', 'unknown')}")
            return 1
        if review.get("staged_paper_order_created") is not False:
            print(f"staged_paper_order_review_created_order={review.get('review_id', 'unknown')}")
            return 1
        if review.get("paper_order_submittable") is not False:
            print(f"staged_paper_order_review_submittable={review.get('review_id', 'unknown')}")
            return 1
        if review.get("broker_write_allowed") is not False:
            print(f"staged_paper_order_review_broker_write_allowed={review.get('review_id', 'unknown')}")
            return 1
        if review.get("live_capital_enabled") is not False:
            print(f"staged_paper_order_review_live_capital_enabled={review.get('review_id', 'unknown')}")
            return 1
        hypothetical = review.get("hypothetical_order", {})
        missing_hypothetical = sorted(REQUIRED_HYPOTHETICAL_ORDER_FIELDS - set(hypothetical))
        if missing_hypothetical:
            print(
                "staged_paper_order_hypothetical_fields_missing="
                f"{review.get('review_id', 'unknown')}:{','.join(missing_hypothetical)}"
            )
            return 1
        if hypothetical.get("status") != "not_created":
            print(f"staged_paper_order_hypothetical_created={review.get('review_id', 'unknown')}")
            return 1
        missing_checks = sorted(REQUIRED_RECONCILIATION_CHECKS - set(review.get("reconciliation_checks", {})))
        if missing_checks:
            print(f"staged_paper_order_checks_missing={review.get('review_id', 'unknown')}:{','.join(missing_checks)}")
            return 1
        if "fail_closed_no_broker_write_route" not in review.get("reconciliation_checks", {}).values():
            print(f"staged_paper_order_broker_route_not_fail_closed={review.get('review_id', 'unknown')}")
            return 1
        if "cannot create a staged order" not in review.get("boundary", ""):
            print(f"staged_paper_order_review_boundary_weak={review.get('review_id', 'unknown')}")
            return 1

    print("staged_paper_order_contract_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
