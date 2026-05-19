#!/usr/bin/env python3
"""Check the Signal Integrity Gate contract."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.signal_integrity import (  # noqa: E402
    SIGNAL_INTEGRITY_STATUSES,
    SignalIntegrityReviewStore,
    run_signal_integrity_gate,
    signal_integrity_summary,
)

REQUIRED_REVIEW_FIELDS = {
    "akber_filter",
    "average_trust_score",
    "boundary",
    "evidence_item_count",
    "execution_allowed",
    "failure_reasons",
    "instrument_focus",
    "integrity_score",
    "min_trust_score",
    "missing_correlations",
    "paper_order_allowed",
    "required_next_steps",
    "review_id",
    "reviewed_at",
    "schema_version",
    "signal_confidence",
    "source_count",
    "source_signal_id",
    "status",
    "trade_candidate_created",
    "worldview_prior_status",
}

REQUIRED_AKBER_STAGES = {
    "low_volatility",
    "options_distribution_gap",
    "catalyst_identification",
    "technical_setup",
    "obv_volume",
    "approval_policy",
}


def main() -> int:
    settings = Settings.from_env()
    result = run_signal_integrity_gate(settings=settings, seed_sample_if_empty=True)
    summary = signal_integrity_summary(settings)
    reviews = SignalIntegrityReviewStore(settings=settings).read(limit=max(1, result["review_count"]))

    print("signal_integrity_gate_status=" + result["status"])
    print(f"signal_integrity_gate_schema_version={result['schema_version']}")
    print(f"signal_integrity_gate_signal_count={result['signal_count']}")
    print(f"signal_integrity_gate_processed_signal_count={result['processed_signal_count']}")
    print(f"signal_integrity_gate_review_count={result['review_count']}")
    print(f"signal_integrity_gate_blocked_count={result['blocked_count']}")
    print(f"signal_integrity_gate_hold_count={result['hold_count']}")
    print(f"signal_integrity_gate_passed_to_risk_shadow_count={result['passed_to_risk_shadow_count']}")
    print(f"signal_integrity_gate_execution_allowed_count={result['execution_allowed_count']}")
    print(f"signal_integrity_gate_paper_order_allowed_count={result['paper_order_allowed_count']}")
    print(f"signal_integrity_gate_trade_candidate_created_count={result['trade_candidate_created_count']}")
    print(f"signal_integrity_gate_store_status={summary['status']}")
    print(f"signal_integrity_gate_total_store_reviews={summary['review_count']}")
    print(f"signal_integrity_gate_by_status={summary.get('by_status', {})}")
    print(f"signal_integrity_gate_boundary={result['boundary']}")

    if result["status"] != "ok":
        return 1
    if result["review_count"] < 1:
        print("signal_integrity_gate_no_reviews=true")
        return 1
    if result["execution_allowed_count"] != 0:
        print("signal_integrity_gate_execution_allowed_not_zero=true")
        return 1
    if result["paper_order_allowed_count"] != 0:
        print("signal_integrity_gate_paper_order_allowed_not_zero=true")
        return 1
    if result["trade_candidate_created_count"] != 0:
        print("signal_integrity_gate_trade_candidate_created=true")
        return 1
    if summary["status"] != "ok":
        print("signal_integrity_gate_store_not_ok=true")
        return 1

    for review in reviews:
        missing = sorted(REQUIRED_REVIEW_FIELDS - set(review))
        if missing:
            print(f"signal_integrity_gate_review_fields_missing={review.get('review_id', 'unknown')}:{','.join(missing)}")
            return 1
        if review["status"] not in SIGNAL_INTEGRITY_STATUSES:
            print(f"signal_integrity_gate_invalid_status={review['status']}")
            return 1
        if review["execution_allowed"] is not False or review["paper_order_allowed"] is not False:
            print("signal_integrity_gate_review_authority_enabled=true")
            return 1
        if review["trade_candidate_created"] is not False:
            print("signal_integrity_gate_review_created_trade_candidate=true")
            return 1
        if not 0 <= float(review["integrity_score"]) <= 1:
            print("signal_integrity_gate_score_out_of_range=true")
            return 1
        if sorted(REQUIRED_AKBER_STAGES - set(review.get("akber_filter", {}))):
            print("signal_integrity_gate_akber_stages_missing=true")
            return 1
        if "cannot approve" not in review["boundary"] or "create trade candidates" not in review["boundary"]:
            print("signal_integrity_gate_boundary_weak=true")
            return 1

    print("signal_integrity_gate_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
