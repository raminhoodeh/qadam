#!/usr/bin/env python3
"""Validate the read-only Risk Agent policy router."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.risk_agent import (  # noqa: E402
    RISK_AGENT_STATUSES,
    RiskPolicyReviewStore,
    risk_agent_summary,
    run_risk_policy_router,
)
from orchestrator.signal_integrity import run_signal_integrity_gate  # noqa: E402
from orchestrator.trade_intent import ensure_d5_sample_trade_intents  # noqa: E402

REQUIRED_REVIEW_FIELDS = {
    "blocked_reasons",
    "boundary",
    "broker_write_allowed",
    "checks",
    "execution_allowed",
    "instrument",
    "max_risk_gbp",
    "max_risk_pct",
    "order_created",
    "paper_account_status",
    "paper_order_allowed",
    "policy_score",
    "proposed_risk_gbp",
    "proposed_risk_pct",
    "required_next_steps",
    "review_id",
    "reviewed_at",
    "schema_version",
    "signal_integrity_status",
    "source_ref",
    "source_type",
    "status",
}

REQUIRED_CHECKS = {
    "broker_order_route",
    "broker_write",
    "drawdown",
    "execution_policy",
    "kill_switch",
    "live_capital",
    "mode",
    "paper_order_authority",
}


def main() -> int:
    settings = Settings.from_env()
    ensure_d5_sample_trade_intents(settings)
    run_signal_integrity_gate(settings=settings, seed_sample_if_empty=True)
    result = run_risk_policy_router(settings=settings)
    summary = risk_agent_summary(settings)
    store = RiskPolicyReviewStore(settings=settings)
    reviews = store.read(limit=10)

    print("risk_agent_policy_status=" + result["status"])
    print(f"risk_agent_policy_schema_version={result['schema_version']}")
    print(f"risk_agent_policy_review_count={result['review_count']}")
    print(f"risk_agent_policy_blocked_count={result['blocked_count']}")
    print(f"risk_agent_policy_hold_count={result['policy_hold_count']}")
    print(f"risk_agent_policy_shadow_ready_count={result['risk_shadow_ready_count']}")
    print(f"risk_agent_policy_execution_allowed_count={result['execution_allowed_count']}")
    print(f"risk_agent_policy_paper_order_allowed_count={result['paper_order_allowed_count']}")
    print(f"risk_agent_policy_order_created_count={result['order_created_count']}")
    print(f"risk_agent_policy_broker_write_allowed_count={result['broker_write_allowed_count']}")
    print("risk_agent_policy_store_status=" + summary["status"])
    print(f"risk_agent_policy_total_store_reviews={summary['review_count']}")
    print(f"risk_agent_policy_by_status={summary['by_status']}")
    print("risk_agent_policy_boundary=" + summary["boundary"])

    if result["status"] != "ok" or summary["status"] != "ok":
        print("risk_agent_policy_not_ok=true")
        return 1
    if result["review_count"] < 1 or not reviews:
        print("risk_agent_policy_reviews_missing=true")
        return 1
    if result["execution_allowed_count"] != 0:
        print("risk_agent_policy_execution_allowed_not_zero=true")
        return 1
    if result["paper_order_allowed_count"] != 0:
        print("risk_agent_policy_paper_order_allowed_not_zero=true")
        return 1
    if result["order_created_count"] != 0:
        print("risk_agent_policy_order_created_not_zero=true")
        return 1
    if result["broker_write_allowed_count"] != 0:
        print("risk_agent_policy_broker_write_allowed_not_zero=true")
        return 1
    if "cannot approve risk" not in summary["boundary"]:
        print("risk_agent_policy_boundary_weak=true")
        return 1

    for review in reviews:
        missing = sorted(REQUIRED_REVIEW_FIELDS - set(review))
        if missing:
            print(f"risk_agent_policy_review_fields_missing={review.get('review_id', 'unknown')}:{','.join(missing)}")
            return 1
        if review.get("status") not in RISK_AGENT_STATUSES:
            print(f"risk_agent_policy_review_invalid_status={review.get('review_id', 'unknown')}")
            return 1
        if review.get("execution_allowed") is not False:
            print(f"risk_agent_policy_review_execution_allowed={review.get('review_id', 'unknown')}")
            return 1
        if review.get("paper_order_allowed") is not False:
            print(f"risk_agent_policy_review_paper_order_allowed={review.get('review_id', 'unknown')}")
            return 1
        if review.get("order_created") is not False:
            print(f"risk_agent_policy_review_order_created={review.get('review_id', 'unknown')}")
            return 1
        if review.get("broker_write_allowed") is not False:
            print(f"risk_agent_policy_review_broker_write_allowed={review.get('review_id', 'unknown')}")
            return 1
        if not 0 <= float(review.get("policy_score", -1)) <= 1:
            print(f"risk_agent_policy_review_bad_score={review.get('review_id', 'unknown')}")
            return 1
        checks = review.get("checks", {})
        missing_checks = sorted(REQUIRED_CHECKS - set(checks))
        if missing_checks:
            print(f"risk_agent_policy_checks_missing={review.get('review_id', 'unknown')}:{','.join(missing_checks)}")
            return 1
        if "fail_closed_no_order_route" not in checks.values():
            print(f"risk_agent_policy_order_route_not_fail_closed={review.get('review_id', 'unknown')}")
            return 1
        if "cannot approve risk" not in review.get("boundary", ""):
            print(f"risk_agent_policy_review_boundary_weak={review.get('review_id', 'unknown')}")
            return 1

    print("risk_agent_policy_router_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
