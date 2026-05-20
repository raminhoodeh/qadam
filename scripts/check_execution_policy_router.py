#!/usr/bin/env python3
"""Validate read-only execution policy and kill-switch contracts."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.execution_policy import (  # noqa: E402
    EXECUTION_POLICY_STATUSES,
    ExecutionPolicyReviewStore,
    execution_policy_summary,
    run_execution_policy_router,
)
from orchestrator.risk_agent import run_risk_policy_router  # noqa: E402
from orchestrator.signal_integrity import run_signal_integrity_gate  # noqa: E402
from orchestrator.trade_intent import ensure_d5_sample_trade_intents  # noqa: E402

REQUIRED_REVIEW_FIELDS = {
    "blocked_reasons",
    "boundary",
    "broker_write_allowed",
    "checks",
    "execution_allowed",
    "instrument",
    "kill_switches",
    "live_capital_enabled",
    "paper_order_created",
    "policy_score",
    "required_next_steps",
    "review_id",
    "reviewed_at",
    "schema_version",
    "selected_venue",
    "source_risk_review_id",
    "staged_paper_order_allowed",
    "status",
    "venue_mode",
}

REQUIRED_CHECKS = {
    "broker_order_route",
    "closed_trade_maturity",
    "event_log",
    "execution_policy_registry",
    "global_kill_switch",
    "live_capital",
    "operating_mode",
    "paper_order_contract",
    "risk_agent",
    "risk_agent_authority",
    "strategy_kill_switch",
    "venue_kill_switch",
    "venue_registry",
}

REQUIRED_KILL_SWITCHES = {"data", "global", "model", "strategy", "venue"}


def main() -> int:
    settings = Settings.from_env()
    ensure_d5_sample_trade_intents(settings)
    run_signal_integrity_gate(settings=settings, seed_sample_if_empty=True)
    run_risk_policy_router(settings=settings)
    result = run_execution_policy_router(settings=settings)
    summary = execution_policy_summary(settings)
    reviews = ExecutionPolicyReviewStore(settings=settings).read(limit=10)

    print("execution_policy_status=" + result["status"])
    print(f"execution_policy_schema_version={result['schema_version']}")
    print(f"execution_policy_review_count={result['review_count']}")
    print(f"execution_policy_blocked_by_policy_count={result['blocked_by_policy_count']}")
    print(f"execution_policy_kill_switch_hold_count={result['kill_switch_hold_count']}")
    print(f"execution_policy_paper_order_shadow_ready_count={result['paper_order_shadow_ready_count']}")
    print(f"execution_policy_execution_allowed_count={result['execution_allowed_count']}")
    print(f"execution_policy_staged_paper_order_allowed_count={result['staged_paper_order_allowed_count']}")
    print(f"execution_policy_paper_order_created_count={result['paper_order_created_count']}")
    print(f"execution_policy_broker_write_allowed_count={result['broker_write_allowed_count']}")
    print(f"execution_policy_live_capital_enabled_count={result['live_capital_enabled_count']}")
    print("execution_policy_store_status=" + summary["status"])
    print(f"execution_policy_total_store_reviews={summary['review_count']}")
    print(f"execution_policy_by_status={summary['by_status']}")
    print("execution_policy_boundary=" + summary["boundary"])

    if result["status"] != "ok" or summary["status"] != "ok":
        print("execution_policy_not_ok=true")
        return 1
    if result["review_count"] < 1 or not reviews:
        print("execution_policy_reviews_missing=true")
        return 1
    if result["execution_allowed_count"] != 0:
        print("execution_policy_execution_allowed_not_zero=true")
        return 1
    if result["staged_paper_order_allowed_count"] != 0:
        print("execution_policy_staged_paper_order_allowed_not_zero=true")
        return 1
    if result["paper_order_created_count"] != 0:
        print("execution_policy_paper_order_created_not_zero=true")
        return 1
    if result["broker_write_allowed_count"] != 0:
        print("execution_policy_broker_write_allowed_not_zero=true")
        return 1
    if result["live_capital_enabled_count"] != 0:
        print("execution_policy_live_capital_enabled_not_zero=true")
        return 1
    if "cannot stage paper orders" not in summary["boundary"]:
        print("execution_policy_boundary_weak=true")
        return 1

    for review in reviews:
        missing = sorted(REQUIRED_REVIEW_FIELDS - set(review))
        if missing:
            print(f"execution_policy_review_fields_missing={review.get('review_id', 'unknown')}:{','.join(missing)}")
            return 1
        if review.get("status") not in EXECUTION_POLICY_STATUSES:
            print(f"execution_policy_review_invalid_status={review.get('review_id', 'unknown')}")
            return 1
        if review.get("execution_allowed") is not False:
            print(f"execution_policy_review_execution_allowed={review.get('review_id', 'unknown')}")
            return 1
        if review.get("staged_paper_order_allowed") is not False:
            print(f"execution_policy_review_staged_order_allowed={review.get('review_id', 'unknown')}")
            return 1
        if review.get("paper_order_created") is not False:
            print(f"execution_policy_review_paper_order_created={review.get('review_id', 'unknown')}")
            return 1
        if review.get("broker_write_allowed") is not False:
            print(f"execution_policy_review_broker_write_allowed={review.get('review_id', 'unknown')}")
            return 1
        if review.get("live_capital_enabled") is not False:
            print(f"execution_policy_review_live_capital_enabled={review.get('review_id', 'unknown')}")
            return 1
        if not 0 <= float(review.get("policy_score", -1)) <= 1:
            print(f"execution_policy_review_bad_score={review.get('review_id', 'unknown')}")
            return 1
        missing_checks = sorted(REQUIRED_CHECKS - set(review.get("checks", {})))
        if missing_checks:
            print(f"execution_policy_checks_missing={review.get('review_id', 'unknown')}:{','.join(missing_checks)}")
            return 1
        missing_switches = sorted(REQUIRED_KILL_SWITCHES - set(review.get("kill_switches", {})))
        if missing_switches:
            print(f"execution_policy_kill_switches_missing={review.get('review_id', 'unknown')}:{','.join(missing_switches)}")
            return 1
        if "fail_closed_no_broker_order_route" not in review.get("checks", {}).values():
            print(f"execution_policy_broker_route_not_fail_closed={review.get('review_id', 'unknown')}")
            return 1
        if "cannot stage orders" not in review.get("boundary", ""):
            print(f"execution_policy_review_boundary_weak={review.get('review_id', 'unknown')}")
            return 1

    print("execution_policy_router_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
