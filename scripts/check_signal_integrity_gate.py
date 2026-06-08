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
    "technical_context_policy",
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
    "pricing_gap_confirmation_source",
    "pricing_gap_event_present",
    "pricing_gap_failure_reason",
    "pricing_gap_legacy_marker_fallback_used",
    "pricing_gap_marker_present",
    "pricing_gap_policy_tier",
    "pricing_gap_relaxed_candidate",
    "pricing_gap_relaxed_policy_enabled",
    "pricing_gap_result",
    "pricing_gap_rollout_stage",
    "pricing_gap_signal_invalid",
    "pricing_gap_status",
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

REQUIRED_TECHNICAL_POLICY_FIELDS = {
    "boundary",
    "broker_write_authority",
    "context_stale_hold",
    "live_capital_authority",
    "order_authority",
    "paper_order_authority",
    "risk_handoff_allowed",
    "signal_authority",
    "source_quorum_credit_allowed",
    "status",
    "technical_context_only_confirmation_allowed",
    "technical_context_present",
    "technical_item_count",
    "trade_candidate_creation_allowed",
    "tradingview_mcp_context_only_hold",
}


def _synthetic_signal(
    signal_id: str,
    evidence_items: tuple[EvidenceItem, ...],
    *,
    confidence: float = 0.74,
    instrument_focus: str = "semiconductors",
    pricing_gap_rollout_stage: str | None = None,
) -> dict[str, Any]:
    payload = {
        "schema_version": 1,
        "signal_id": signal_id,
        "status": "shadow_only",
        "title": f"Safety probe: {signal_id}",
        "instrument_focus": instrument_focus,
        "thesis": "Synthetic Safety Chain probe; no execution path exists.",
        "confidence": confidence,
        "invalidation": "Synthetic probe only.",
        "evidence_trail": build_evidence_trail(evidence_items).to_dict(),
        "generated_by": "p3_6_safety_chain_probe",
        "execution_allowed": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if pricing_gap_rollout_stage:
        payload["pricing_gap_rollout_stage"] = pricing_gap_rollout_stage
    return payload


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
    legacy_pricing_gap_marker = EvidenceItem(
        evidence_id="synthetic:rss:legacy-pricing-gap",
        source="news.rss",
        event_type="news_observation",
        summary="Legacy evidence text says pass_pricing_gap_confirmed for backward compatibility only.",
        trust_score=0.77,
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
        build_signal_integrity_review(
            _synthetic_signal("synthetic_legacy_pricing_gap_fallback", (yahoo_current, legacy_pricing_gap_marker))
        ).to_dict(),
        build_signal_integrity_review(
            _synthetic_signal(
                "synthetic_light_tier_transaction_cost_only",
                (
                    yahoo_current,
                    independent,
                    EvidenceItem(
                        evidence_id="synthetic:tx-cost:light-tier",
                        source="market.alpaca_readonly",
                        event_type="transaction_cost_assumption",
                        summary="Transaction-cost envelope recorded for a light-tier directional setup.",
                        trust_score=0.74,
                        observed_at=now.isoformat(),
                        raw_ref="synthetic",
                    ),
                ),
                instrument_focus="silver",
                pricing_gap_rollout_stage="stage_b",
            )
        ).to_dict(),
        build_signal_integrity_review(
            _synthetic_signal(
                "synthetic_not_required_market_only",
                (yahoo_current, independent),
                instrument_focus="prediction_markets",
                pricing_gap_rollout_stage="stage_b",
            )
        ).to_dict(),
        build_signal_integrity_review(
            _synthetic_signal(
                "synthetic_stage_a_light_tier_transaction_cost_only",
                (
                    yahoo_current,
                    independent,
                    EvidenceItem(
                        evidence_id="synthetic:tx-cost:stage-a-light-tier",
                        source="market.alpaca_readonly",
                        event_type="transaction_cost_assumption",
                        summary="Transaction-cost envelope present while Stage A strict rollout remains active.",
                        trust_score=0.74,
                        observed_at=now.isoformat(),
                        raw_ref="synthetic",
                    ),
                ),
                instrument_focus="silver",
                pricing_gap_rollout_stage="stage_a",
            )
        ).to_dict(),
        build_signal_integrity_review(
            _synthetic_signal(
                "synthetic_stage_a_not_required_market_only",
                (yahoo_current, independent),
                instrument_focus="prediction_markets",
                pricing_gap_rollout_stage="stage_a",
            )
        ).to_dict(),
        build_signal_integrity_review(
            _synthetic_signal(
                "synthetic_strict_tier_transaction_cost_only",
                (
                    yahoo_current,
                    independent,
                    EvidenceItem(
                        evidence_id="synthetic:tx-cost:strict-tier",
                        source="market.alpaca_readonly",
                        event_type="transaction_cost_assumption",
                        summary="Transaction-cost envelope attached without explicit pricing-gap evidence.",
                        trust_score=0.74,
                        observed_at=now.isoformat(),
                        raw_ref="synthetic",
                    ),
                ),
                instrument_focus="semiconductors",
                pricing_gap_rollout_stage="stage_b",
            )
        ).to_dict(),
        build_signal_integrity_review(
            _synthetic_signal(
                "synthetic_light_tier_stale_market_with_transaction_cost",
                (
                    yahoo_stale,
                    independent,
                    EvidenceItem(
                        evidence_id="synthetic:tx-cost:stale-light-tier",
                        source="market.alpaca_readonly",
                        event_type="transaction_cost_assumption",
                        summary="Transaction-cost envelope recorded but market confirmation is stale.",
                        trust_score=0.74,
                        observed_at=now.isoformat(),
                        raw_ref="synthetic",
                    ),
                ),
                instrument_focus="silver",
                pricing_gap_rollout_stage="stage_b",
            )
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


def _technical_policy_contract_probes() -> tuple[dict[str, Any], ...]:
    now = datetime.now(timezone.utc)
    tradingview_context = EvidenceItem(
        evidence_id="synthetic:tradingview_mcp:technical",
        source="market.tradingview_mcp",
        event_type="technical_analysis_context",
        summary=(
            "TradingView MCP read-only technical context attached. Technical context is "
            "supplemental only and cannot create source quorum, trade candidates, paper "
            "orders, or broker writes."
        ),
        trust_score=0.57,
        observed_at=now.isoformat(),
        raw_ref="synthetic",
    )
    canonical = EvidenceItem(
        evidence_id="synthetic:rss:technical_catalyst",
        source="news.rss",
        event_type="news_observation",
        summary="Canonical catalyst context for a technical setup; still needs market confirmation.",
        trust_score=0.74,
        observed_at=now.isoformat(),
        raw_ref="synthetic",
    )
    tradingview_stale = EvidenceItem(
        evidence_id="synthetic:tradingview_mcp:stale",
        source="market.tradingview_mcp",
        event_type="technical_analysis_context",
        summary="TradingView MCP stale technical context.",
        trust_score=0.57,
        observed_at=(now - timedelta(days=5)).isoformat(),
        raw_ref="synthetic",
    )
    return (
        build_signal_integrity_review(
            _synthetic_signal("synthetic_tradingview_mcp_only", (tradingview_context,))
        ).to_dict(),
        build_signal_integrity_review(
            _synthetic_signal("synthetic_tradingview_mcp_with_canonical", (tradingview_context, canonical))
        ).to_dict(),
        build_signal_integrity_review(
            _synthetic_signal("synthetic_tradingview_mcp_stale", (tradingview_stale, canonical))
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
    if policy.get("pricing_gap_signal_invalid") is not False:
        return "pricing_gap_invalid_enabled"
    if policy.get("pricing_gap_rollout_stage") not in {"stage_a", "stage_b"}:
        return "pricing_gap_rollout_stage_invalid"
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


def _check_technical_policy(review: dict[str, Any]) -> str | None:
    policy = review.get("technical_context_policy")
    if not isinstance(policy, dict):
        return "missing_policy"
    missing = sorted(REQUIRED_TECHNICAL_POLICY_FIELDS - set(policy))
    if missing:
        return "missing_fields:" + ",".join(missing)
    for key in (
        "source_quorum_credit_allowed",
        "technical_context_only_confirmation_allowed",
        "signal_authority",
        "trade_candidate_creation_allowed",
        "risk_handoff_allowed",
        "order_authority",
        "paper_order_authority",
        "broker_write_authority",
        "live_capital_authority",
    ):
        if policy.get(key) is not False:
            return f"authority_enabled:{key}"
    boundary = str(policy.get("boundary") or "")
    for phrase in (
        "TradingView MCP technical context can corroborate technical setup only",
        "cannot satisfy source quorum",
        "create trade candidates",
        "create paper orders",
        "write to brokers",
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
    print(
        "signal_integrity_gate_pricing_gap_rollout_stage="
        f"{summary.get('pricing_gap_rollout_stage', 'stage_a')}"
    )
    print(
        "signal_integrity_gate_signals_with_market_confirmation_count="
        f"{summary.get('signals_with_market_confirmation_count', 0)}"
    )
    print(
        "signal_integrity_gate_signals_with_pricing_gap_evidence_count="
        f"{summary.get('signals_with_pricing_gap_evidence_count', 0)}"
    )
    print(
        "signal_integrity_gate_signals_blocked_only_by_missing_pricing_gap_count="
        f"{summary.get('signals_blocked_only_by_missing_pricing_gap_count', 0)}"
    )
    print(
        "signal_integrity_gate_signals_passed_to_risk_count="
        f"{summary.get('signals_passed_to_risk_count', 0)}"
    )
    print(
        "signal_integrity_gate_risk_reviews_blocked_only_by_pricing_gap_policy_count="
        f"{summary.get('risk_reviews_blocked_only_by_pricing_gap_policy_count', 0)}"
    )
    print(
        "signal_integrity_gate_stage_b_candidate_signal_count="
        f"{summary.get('stage_b_candidate_signal_count', 0)}"
    )
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
    technical_policy_probes = _technical_policy_contract_probes()
    technical_policy_statuses = {
        review["source_signal_id"]: review["technical_context_policy"]["status"]
        for review in technical_policy_probes
    }
    print(f"signal_integrity_gate_technical_policy_probe_statuses={technical_policy_statuses}")

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
    if summary.get("pricing_gap_rollout_stage") not in {"stage_a", "stage_b"}:
        print("signal_integrity_gate_rollout_stage_invalid=true")
        return 1
    for key in (
        "signals_with_market_confirmation_count",
        "signals_with_pricing_gap_evidence_count",
        "signals_blocked_only_by_missing_pricing_gap_count",
        "signals_passed_to_risk_count",
        "risk_reviews_blocked_only_by_pricing_gap_policy_count",
        "stage_b_candidate_signal_count",
    ):
        if int(summary.get(key, 0) or 0) < 0:
            print(f"signal_integrity_gate_summary_count_negative={key}")
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
        technical_policy_error = _check_technical_policy(review)
        if technical_policy_error:
            print(
                "signal_integrity_gate_technical_policy_invalid="
                f"{review.get('review_id', 'unknown')}:{technical_policy_error}"
            )
            return 1
        if "cannot approve" not in review["boundary"] or "create trade candidates" not in review["boundary"]:
            print("signal_integrity_gate_boundary_weak=true")
            return 1

    expected_probe_statuses = {
        "synthetic_yahoo_single_source": "market_confirmation_single_source_hold",
        "synthetic_yahoo_stale": "market_confirmation_stale",
        "synthetic_market_unavailable": "market_confirmation_unavailable",
        "synthetic_legacy_pricing_gap_fallback": "market_confirmation_corroboration_available",
        "synthetic_light_tier_transaction_cost_only": "market_confirmation_corroboration_available",
        "synthetic_not_required_market_only": "market_confirmation_corroboration_available",
        "synthetic_stage_a_light_tier_transaction_cost_only": "market_confirmation_corroboration_available",
        "synthetic_stage_a_not_required_market_only": "market_confirmation_corroboration_available",
        "synthetic_strict_tier_transaction_cost_only": "market_confirmation_corroboration_available",
        "synthetic_light_tier_stale_market_with_transaction_cost": "market_confirmation_stale",
    }
    if policy_statuses != expected_probe_statuses:
        print("signal_integrity_gate_market_policy_probe_mismatch=true")
        return 1
    for probe in policy_probes:
        policy_error = _check_market_policy(probe)
        if policy_error:
            print(f"signal_integrity_gate_market_policy_probe_invalid={probe['source_signal_id']}:{policy_error}")
            return 1
        expected_review_status = (
            "passed_to_risk_shadow"
            if probe["source_signal_id"]
            in {
                "synthetic_legacy_pricing_gap_fallback",
                "synthetic_light_tier_transaction_cost_only",
                "synthetic_not_required_market_only",
            }
            else "hold_for_corroboration"
        )
        if probe["status"] != expected_review_status:
            print(f"signal_integrity_gate_market_policy_probe_not_held={probe['source_signal_id']}")
            return 1
        if probe["execution_allowed"] is not False or probe["paper_order_allowed"] is not False:
            print(f"signal_integrity_gate_market_policy_probe_authority_enabled={probe['source_signal_id']}")
            return 1
        if probe["trade_candidate_created"] is not False:
            print(f"signal_integrity_gate_market_policy_probe_trade_candidate={probe['source_signal_id']}")
            return 1
        pricing_gap_policy = probe["market_confirmation_policy"]
        expected_pricing_gap_status = {
            "synthetic_yahoo_single_source": "pricing_gap_unavailable_single_source_hold",
            "synthetic_yahoo_stale": "pricing_gap_unavailable_market_confirmation_stale",
            "synthetic_market_unavailable": "pricing_gap_unavailable_market_confirmation_unavailable",
            "synthetic_legacy_pricing_gap_fallback": "pass_pricing_gap_confirmed",
            "synthetic_light_tier_transaction_cost_only": "pass_pricing_gap_transaction_cost_only",
            "synthetic_not_required_market_only": "pass_pricing_gap_not_required",
            "synthetic_stage_a_light_tier_transaction_cost_only": "pricing_gap_rollout_stage_a_strict_hold",
            "synthetic_stage_a_not_required_market_only": "pricing_gap_rollout_stage_a_strict_hold",
            "synthetic_strict_tier_transaction_cost_only": "pricing_gap_unavailable_not_modeled",
            "synthetic_light_tier_stale_market_with_transaction_cost": "pass_pricing_gap_transaction_cost_only",
        }[probe["source_signal_id"]]
        if pricing_gap_policy["pricing_gap_status"] != expected_pricing_gap_status:
            print(f"signal_integrity_gate_market_policy_probe_pricing_gap_status_invalid={probe['source_signal_id']}")
            return 1
        expected_pricing_gap_result = (
            "confirmed"
            if probe["source_signal_id"] == "synthetic_legacy_pricing_gap_fallback"
            else "confirmed_light"
            if probe["source_signal_id"] == "synthetic_light_tier_transaction_cost_only"
            else "not_required"
            if probe["source_signal_id"] == "synthetic_not_required_market_only"
            else "held_pending_stage_b"
            if probe["source_signal_id"]
            in {
                "synthetic_stage_a_light_tier_transaction_cost_only",
                "synthetic_stage_a_not_required_market_only",
            }
            else "confirmed_light"
            if probe["source_signal_id"] == "synthetic_light_tier_stale_market_with_transaction_cost"
            else "unavailable"
        )
        if pricing_gap_policy["pricing_gap_result"] != expected_pricing_gap_result:
            print(f"signal_integrity_gate_market_policy_probe_pricing_gap_result_invalid={probe['source_signal_id']}")
            return 1
        expected_confirmation_source = (
            "legacy_summary_marker"
            if probe["source_signal_id"] == "synthetic_legacy_pricing_gap_fallback"
            else "structured_transaction_cost_event"
            if probe["source_signal_id"] == "synthetic_light_tier_transaction_cost_only"
            else "not_required_by_policy"
            if probe["source_signal_id"] == "synthetic_not_required_market_only"
            else "rollout_stage_a_strict"
            if probe["source_signal_id"]
            in {
                "synthetic_stage_a_light_tier_transaction_cost_only",
                "synthetic_stage_a_not_required_market_only",
            }
            else "structured_transaction_cost_event"
            if probe["source_signal_id"] == "synthetic_light_tier_stale_market_with_transaction_cost"
            else "missing"
        )
        if pricing_gap_policy["pricing_gap_confirmation_source"] != expected_confirmation_source:
            print(f"signal_integrity_gate_market_policy_probe_pricing_gap_source_invalid={probe['source_signal_id']}")
            return 1
        if (
            probe["source_signal_id"] == "synthetic_legacy_pricing_gap_fallback"
            and pricing_gap_policy["pricing_gap_legacy_marker_fallback_used"] is not True
        ):
            print("signal_integrity_gate_market_policy_probe_legacy_fallback_unused=true")
            return 1
        if (
            probe["source_signal_id"] != "synthetic_legacy_pricing_gap_fallback"
            and pricing_gap_policy["pricing_gap_legacy_marker_fallback_used"] is not False
        ):
            print(f"signal_integrity_gate_market_policy_probe_legacy_fallback_invalid={probe['source_signal_id']}")
            return 1
        if (
            probe["source_signal_id"] != "synthetic_legacy_pricing_gap_fallback"
            and probe["source_signal_id"] != "synthetic_light_tier_transaction_cost_only"
            and probe["source_signal_id"] != "synthetic_not_required_market_only"
            and probe["source_signal_id"] != "synthetic_stage_a_light_tier_transaction_cost_only"
            and probe["source_signal_id"] != "synthetic_stage_a_not_required_market_only"
            and probe["source_signal_id"] != "synthetic_light_tier_stale_market_with_transaction_cost"
            and "missing_pricing_gap" not in probe["failure_reasons"]
        ):
            print(f"signal_integrity_gate_market_policy_probe_pricing_gap_missing={probe['source_signal_id']}")
            return 1
        if (
            pricing_gap_policy["pricing_gap_failure_reason"]
            and pricing_gap_policy["pricing_gap_failure_reason"] not in probe["failure_reasons"]
        ):
            print(f"signal_integrity_gate_market_policy_probe_pricing_gap_reason_missing={probe['source_signal_id']}")
            return 1
        expected_tier = {
            "synthetic_yahoo_single_source": "required_strict",
            "synthetic_yahoo_stale": "required_strict",
            "synthetic_market_unavailable": "required_strict",
            "synthetic_legacy_pricing_gap_fallback": "required_strict",
            "synthetic_light_tier_transaction_cost_only": "required_light",
            "synthetic_not_required_market_only": "not_required",
            "synthetic_stage_a_light_tier_transaction_cost_only": "required_light",
            "synthetic_stage_a_not_required_market_only": "not_required",
            "synthetic_strict_tier_transaction_cost_only": "required_strict",
            "synthetic_light_tier_stale_market_with_transaction_cost": "required_light",
        }[probe["source_signal_id"]]
        if pricing_gap_policy["pricing_gap_policy_tier"] != expected_tier:
            print(f"signal_integrity_gate_market_policy_probe_pricing_gap_tier_invalid={probe['source_signal_id']}")
            return 1
        if probe["source_signal_id"] == "synthetic_strict_tier_transaction_cost_only":
            if probe["status"] != "hold_for_corroboration":
                print("signal_integrity_gate_strict_tx_cost_probe_not_held=true")
                return 1
            if "pricing_gap_unavailable_not_modeled" not in probe["failure_reasons"]:
                print("signal_integrity_gate_strict_tx_cost_probe_reason_missing=true")
                return 1
        if probe["source_signal_id"] == "synthetic_light_tier_stale_market_with_transaction_cost":
            if probe["status"] != "hold_for_corroboration":
                print("signal_integrity_gate_light_stale_probe_not_held=true")
                return 1
            if "market_confirmation_stale" not in probe["failure_reasons"]:
                print("signal_integrity_gate_light_stale_probe_market_reason_missing=true")
                return 1
        if probe["source_signal_id"] in {
            "synthetic_stage_a_light_tier_transaction_cost_only",
            "synthetic_stage_a_not_required_market_only",
        }:
            if probe["status"] != "hold_for_corroboration":
                print("signal_integrity_gate_stage_a_rollout_probe_not_held=true")
                return 1
            if "pricing_gap_rollout_stage_a_strict_hold" not in probe["failure_reasons"]:
                print("signal_integrity_gate_stage_a_rollout_probe_reason_missing=true")
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
            print(
                "signal_integrity_gate_preference_policy_probe_status_invalid="
                f"{probe['source_signal_id']}:{probe['status']}"
            )
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

    expected_technical_statuses = {
        "synthetic_tradingview_mcp_only": "tradingview_mcp_context_only_hold",
        "synthetic_tradingview_mcp_with_canonical": "supplemental_technical_confirmation_available",
        "synthetic_tradingview_mcp_stale": "technical_context_stale_hold",
    }
    if technical_policy_statuses != expected_technical_statuses:
        print("signal_integrity_gate_technical_policy_probe_mismatch=true")
        return 1
    for probe in technical_policy_probes:
        policy_error = _check_technical_policy(probe)
        if policy_error:
            print(f"signal_integrity_gate_technical_policy_probe_invalid={probe['source_signal_id']}:{policy_error}")
            return 1
        if probe["status"] != "hold_for_corroboration":
            print(f"signal_integrity_gate_technical_policy_probe_not_held={probe['source_signal_id']}")
            return 1
        if probe["execution_allowed"] is not False or probe["paper_order_allowed"] is not False:
            print(f"signal_integrity_gate_technical_policy_probe_authority_enabled={probe['source_signal_id']}")
            return 1
        if probe["trade_candidate_created"] is not False:
            print(f"signal_integrity_gate_technical_policy_probe_trade_candidate={probe['source_signal_id']}")
            return 1
        if probe["source_signal_id"] == "synthetic_tradingview_mcp_only":
            if "tradingview_mcp_context_only_hold" not in probe["failure_reasons"]:
                print("signal_integrity_gate_tradingview_only_probe_failure_missing=true")
                return 1

    print("signal_integrity_gate_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
