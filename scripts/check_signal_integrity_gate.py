#!/usr/bin/env python3
"""Check the Signal Integrity Gate contract."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.intelligence import EvidenceItem, build_evidence_trail  # noqa: E402
from orchestrator.signal_integrity import (  # noqa: E402
    SIGNAL_INTEGRITY_STATUSES,
    SignalIntegrityReviewStore,
    build_signal_integrity_review,
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
    "market_confirmation_policy",
    "min_trust_score",
    "missing_correlations",
    "paper_order_allowed",
    "preference_context_policy",
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

REQUIRED_MARKET_POLICY_FIELDS = {
    "boundary",
    "broker_reconciliation_authority",
    "latest_observed_at",
    "market_price_confirmation",
    "max_age_seconds",
    "order_authority",
    "pricing_gap",
    "providers",
    "signal_authority",
    "single_source_hold",
    "stale",
    "status",
    "unavailable",
    "uses_yahoo_finance",
}

REQUIRED_PREFERENCE_POLICY_FIELDS = {
    "boundary",
    "broker_reconciliation_authority",
    "context_stale_hold",
    "missing_provenance_hold",
    "order_authority",
    "orderbook_depth_execution_or_venue_permission",
    "orderbook_depth_role",
    "preference_context_present",
    "preference_item_count",
    "preference_only_confirmation_allowed",
    "preference_only_confirmation_hold",
    "quota_degraded_hold",
    "risk_handoff_allowed",
    "signal_authority",
    "source_quorum_credit_allowed",
    "status",
    "trade_candidate_creation_allowed",
    "wallet_kol_company_truth_allowed",
    "wallet_kol_role",
}


def _synthetic_signal(
    signal_id: str,
    evidence_items: tuple[EvidenceItem, ...],
    *,
    confidence: float = 0.74,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "signal_id": signal_id,
        "status": "shadow_only",
        "title": f"Safety probe: {signal_id}",
        "instrument_focus": "semiconductors",
        "thesis": "Synthetic Safety Chain probe; no execution path exists.",
        "confidence": confidence,
        "invalidation": "Synthetic probe only.",
        "evidence_trail": build_evidence_trail(evidence_items).to_dict(),
        "generated_by": "p3_6_safety_chain_probe",
        "execution_allowed": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _market_policy_contract_probes() -> tuple[dict[str, Any], ...]:
    now = datetime.now(timezone.utc)
    stale = now - timedelta(days=5)
    yahoo_current = EvidenceItem(
        evidence_id="synthetic:yahoo:current",
        source="market.yahoo_finance",
        event_type="market_price_confirmation",
        summary="SMH market confirmation from Yahoo Finance sample context.",
        trust_score=0.72,
        observed_at=now.isoformat(),
        raw_ref="synthetic",
    )
    yahoo_stale = EvidenceItem(
        evidence_id="synthetic:yahoo:stale",
        source="market.yahoo_finance",
        event_type="market_price_confirmation",
        summary="SMH stale market confirmation from Yahoo Finance sample context.",
        trust_score=0.72,
        observed_at=stale.isoformat(),
        raw_ref="synthetic",
    )
    independent = EvidenceItem(
        evidence_id="synthetic:rss:semiconductors",
        source="news.rss",
        event_type="news_observation",
        summary="Semiconductor supply chain catalyst requires market confirmation before risk review.",
        trust_score=0.74,
        observed_at=now.isoformat(),
        raw_ref="synthetic",
    )
    non_market = EvidenceItem(
        evidence_id="synthetic:fred:macro",
        source="macro.fred",
        event_type="macro_observation",
        summary="Macro observation for semiconductors without market confirmation.",
        trust_score=0.76,
        observed_at=now.isoformat(),
        raw_ref="synthetic",
    )
    return (
        build_signal_integrity_review(_synthetic_signal("synthetic_yahoo_single_source", (yahoo_current,))).to_dict(),
        build_signal_integrity_review(
            _synthetic_signal("synthetic_yahoo_stale", (yahoo_stale, independent))
        ).to_dict(),
        build_signal_integrity_review(
            _synthetic_signal("synthetic_market_unavailable", (independent, non_market))
        ).to_dict(),
    )


def _preference_policy_contract_probes() -> tuple[dict[str, Any], ...]:
    now = datetime.now(timezone.utc)
    preference_orderbook = EvidenceItem(
        evidence_id="synthetic:preference:orderbook",
        source="supplemental.preference_mcp",
        event_type="preference_shadow_context",
        summary=(
            "Preference MCP orderbook depth context. Preference-only confirmation is a hold "
            "condition; orderbook depth is market context only."
        ),
        trust_score=0.72,
        observed_at=now.isoformat(),
        raw_ref="synthetic",
    )
    preference_wallet = EvidenceItem(
        evidence_id="synthetic:preference:wallet",
        source="supplemental.preference_mcp",
        event_type="preference_shadow_context",
        summary=(
            "Preference MCP wallet/KOL movement is risk sentiment only and not factual "
            "corporate evidence."
        ),
        trust_score=0.7,
        observed_at=now.isoformat(),
        raw_ref="synthetic",
    )
    canonical = EvidenceItem(
        evidence_id="synthetic:canonical:filing",
        source="filings.sec_edgar",
        event_type="filing_metadata_context",
        summary="Canonical filing metadata context; still needs market confirmation.",
        trust_score=0.76,
        observed_at=now.isoformat(),
        raw_ref="synthetic",
    )
    preference_stale = EvidenceItem(
        evidence_id="synthetic:preference:stale",
        source="supplemental.preference_mcp",
        event_type="preference_shadow_context",
        summary="Preference MCP stale context with quota challenge.",
        trust_score=0.72,
        observed_at=(now - timedelta(days=5)).isoformat(),
        raw_ref="synthetic",
    )
    return (
        build_signal_integrity_review(
            _synthetic_signal("synthetic_preference_only_orderbook", (preference_orderbook,))
        ).to_dict(),
        build_signal_integrity_review(
            _synthetic_signal("synthetic_preference_wallet_context", (preference_wallet, canonical))
        ).to_dict(),
        build_signal_integrity_review(
            _synthetic_signal("synthetic_preference_stale_quota", (preference_stale, canonical))
        ).to_dict(),
    )


def _check_market_policy(review: dict[str, Any]) -> str | None:
    policy = review.get("market_confirmation_policy")
    if not isinstance(policy, dict):
        return "missing_policy"
    missing = sorted(REQUIRED_MARKET_POLICY_FIELDS - set(policy))
    if missing:
        return "missing_fields:" + ",".join(missing)
    if policy.get("signal_authority") is not False:
        return "signal_authority_enabled"
    if policy.get("order_authority") is not False:
        return "order_authority_enabled"
    if policy.get("broker_reconciliation_authority") is not False:
        return "broker_reconciliation_authority_enabled"
    if "Yahoo Finance can inform price context" not in str(policy.get("boundary", "")):
        return "boundary_weak"
    return None


def _check_preference_policy(review: dict[str, Any]) -> str | None:
    policy = review.get("preference_context_policy")
    if not isinstance(policy, dict):
        return "missing_policy"
    missing = sorted(REQUIRED_PREFERENCE_POLICY_FIELDS - set(policy))
    if missing:
        return "missing_fields:" + ",".join(missing)
    for key in (
        "source_quorum_credit_allowed",
        "preference_only_confirmation_allowed",
        "orderbook_depth_execution_or_venue_permission",
        "wallet_kol_company_truth_allowed",
        "signal_authority",
        "trade_candidate_creation_allowed",
        "risk_handoff_allowed",
        "order_authority",
        "broker_reconciliation_authority",
    ):
        if policy.get(key) is not False:
            return f"authority_enabled:{key}"
    if policy.get("orderbook_depth_role") != "market_context_only":
        return "orderbook_depth_role_invalid"
    if policy.get("wallet_kol_role") != "risk_sentiment_only":
        return "wallet_kol_role_invalid"
    boundary = str(policy.get("boundary") or "")
    for phrase in (
        "Preference-only confirmation is a hold condition",
        "orderbook depth is not execution",
        "wallet/KOL movement is not factual corporate evidence",
    ):
        if phrase not in boundary:
            return "boundary_weak"
    return None


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

    policy_probes = _market_policy_contract_probes()
    policy_statuses = {
        review["source_signal_id"]: review["market_confirmation_policy"]["status"]
        for review in policy_probes
    }
    print(f"signal_integrity_gate_market_policy_probe_statuses={policy_statuses}")
    preference_policy_probes = _preference_policy_contract_probes()
    preference_policy_statuses = {
        review["source_signal_id"]: review["preference_context_policy"]["status"]
        for review in preference_policy_probes
    }
    print(f"signal_integrity_gate_preference_policy_probe_statuses={preference_policy_statuses}")

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
        policy_error = _check_market_policy(review)
        if policy_error:
            print(f"signal_integrity_gate_market_policy_invalid={review.get('review_id', 'unknown')}:{policy_error}")
            return 1
        preference_policy_error = _check_preference_policy(review)
        if preference_policy_error:
            print(
                "signal_integrity_gate_preference_policy_invalid="
                f"{review.get('review_id', 'unknown')}:{preference_policy_error}"
            )
            return 1
        if "cannot approve" not in review["boundary"] or "create trade candidates" not in review["boundary"]:
            print("signal_integrity_gate_boundary_weak=true")
            return 1

    expected_probe_statuses = {
        "synthetic_yahoo_single_source": "market_confirmation_single_source_hold",
        "synthetic_yahoo_stale": "market_confirmation_stale",
        "synthetic_market_unavailable": "market_confirmation_unavailable",
    }
    if policy_statuses != expected_probe_statuses:
        print("signal_integrity_gate_market_policy_probe_mismatch=true")
        return 1
    for probe in policy_probes:
        policy_error = _check_market_policy(probe)
        if policy_error:
            print(f"signal_integrity_gate_market_policy_probe_invalid={probe['source_signal_id']}:{policy_error}")
            return 1
        if probe["status"] != "hold_for_corroboration":
            print(f"signal_integrity_gate_market_policy_probe_not_held={probe['source_signal_id']}")
            return 1
        if probe["execution_allowed"] is not False or probe["paper_order_allowed"] is not False:
            print(f"signal_integrity_gate_market_policy_probe_authority_enabled={probe['source_signal_id']}")
            return 1
        if probe["trade_candidate_created"] is not False:
            print(f"signal_integrity_gate_market_policy_probe_trade_candidate={probe['source_signal_id']}")
            return 1
        if "missing_pricing_gap" not in probe["failure_reasons"]:
            print(f"signal_integrity_gate_market_policy_probe_pricing_gap_missing={probe['source_signal_id']}")
            return 1

    expected_preference_statuses = {
        "synthetic_preference_only_orderbook": "preference_only_confirmation_hold",
        "synthetic_preference_wallet_context": "preference_context_challenge_only",
        "synthetic_preference_stale_quota": "preference_context_stale_hold",
    }
    if preference_policy_statuses != expected_preference_statuses:
        print("signal_integrity_gate_preference_policy_probe_mismatch=true")
        return 1
    for probe in preference_policy_probes:
        policy_error = _check_preference_policy(probe)
        if policy_error:
            print(f"signal_integrity_gate_preference_policy_probe_invalid={probe['source_signal_id']}:{policy_error}")
            return 1
        if probe["status"] != "hold_for_corroboration":
            print(f"signal_integrity_gate_preference_policy_probe_not_held={probe['source_signal_id']}")
            return 1
        if probe["execution_allowed"] is not False or probe["paper_order_allowed"] is not False:
            print(f"signal_integrity_gate_preference_policy_probe_authority_enabled={probe['source_signal_id']}")
            return 1
        if probe["trade_candidate_created"] is not False:
            print(f"signal_integrity_gate_preference_policy_probe_trade_candidate={probe['source_signal_id']}")
            return 1
        if probe["source_signal_id"] == "synthetic_preference_only_orderbook":
            if "preference_only_confirmation_hold" not in probe["failure_reasons"]:
                print("signal_integrity_gate_preference_only_probe_failure_missing=true")
                return 1

    print("signal_integrity_gate_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
