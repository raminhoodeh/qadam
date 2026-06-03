#!/usr/bin/env python3
"""Validate D5 Trade Intent Store without creating broker authority."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.trade_intent import (  # noqa: E402
    TradeIntentStore,
    ensure_d5_sample_trade_intents,
    trade_intent_summary,
)

D5_SAMPLE_IDS = {
    "d5-sample-candidate-crude-oil",
    "d5-sample-blocked-semiconductor",
}

REQUIRED_AKBER_FIELDS = {
    "approval_policy",
    "catalyst_identification",
    "low_volatility",
    "obv_volume",
    "options_distribution_gap",
    "technical_setup",
}

REQUIRED_RISK_FIELDS = {
    "broker_heartbeat",
    "event_log",
    "hard_caps",
    "kill_switch",
    "signal_approval",
}


def main() -> int:
    settings = Settings.from_env()
    seed_result = ensure_d5_sample_trade_intents(settings)
    store = TradeIntentStore(settings=settings)
    intents = store.read_intents()
    summary = trade_intent_summary(settings)

    candidate_count = sum(1 for intent in intents if intent.status in {"candidate", "risk_review"})
    blocked_count = sum(1 for intent in intents if intent.status == "blocked")
    execution_allowed_count = sum(1 for intent in intents if intent.execution_allowed)
    paper_order_allowed_count = sum(1 for intent in intents if intent.paper_order_allowed)
    intent_ids = {intent.intent_id for intent in intents}

    print("trade_intent_status=" + summary["status"])
    print(f"trade_intent_created_count={seed_result['created_count']}")
    print(f"trade_intent_store_count={len(intents)}")
    print(f"trade_intent_candidate_count={candidate_count}")
    print(f"trade_intent_blocked_count={blocked_count}")
    print(f"trade_intent_execution_allowed_count={execution_allowed_count}")
    print(f"trade_intent_paper_order_allowed_count={paper_order_allowed_count}")
    print("trade_intent_boundary=" + summary["boundary"])

    if summary["status"] != "ok":
        print("trade_intent_store_not_ok=true")
        return 1
    if candidate_count < 1:
        print("trade_intent_no_candidate=true")
        return 1
    if blocked_count < 1:
        print("trade_intent_no_blocked_trade=true")
        return 1
    if execution_allowed_count != 0:
        print("trade_intent_execution_allowed_not_zero=true")
        return 1
    if paper_order_allowed_count != 0:
        print("trade_intent_paper_order_allowed_not_zero=true")
        return 1
    if not D5_SAMPLE_IDS.issubset(intent_ids):
        print("trade_intent_sample_records_missing=true")
        return 1
    if "No broker order path exists" not in summary["boundary"]:
        print("trade_intent_boundary_weak=true")
        return 1
    for intent in intents:
        if intent.status in {"candidate", "blocked"}:
            if intent.risk_size_gbp != 0 or intent.risk_size_pct != 0:
                print(f"trade_intent_risk_size_nonzero={intent.intent_id}")
                return 1
            if "no broker route exists" not in intent.boundary.lower():
                print(f"trade_intent_record_boundary_weak={intent.intent_id}")
                return 1
            if not str(intent.research_goal_id or "").strip():
                print(f"trade_intent_research_goal_id_missing={intent.intent_id}")
                return 1
            if not REQUIRED_AKBER_FIELDS.issubset(intent.akber_filter):
                print(f"trade_intent_akber_filter_incomplete={intent.intent_id}")
                return 1
            if not REQUIRED_RISK_FIELDS.issubset(intent.risk_checks):
                print(f"trade_intent_risk_checks_incomplete={intent.intent_id}")
                return 1
        if intent.status == "blocked" and not intent.blocked_reason:
            print(f"trade_intent_blocked_reason_missing={intent.intent_id}")
            return 1
        if intent.status == "candidate" and intent.blocked_reason:
            print(f"trade_intent_candidate_has_blocked_reason={intent.intent_id}")
            return 1

    print("trade_intent_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
