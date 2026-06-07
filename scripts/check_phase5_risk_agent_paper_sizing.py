#!/usr/bin/env python3
"""Validate the Q5-3 Risk Agent paper-sizing contract."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.event_log import EventLog  # noqa: E402
from orchestrator.phase5_risk_sizing import (  # noqa: E402
    PHASE5_RISK_SIZING_SCHEMA_VERSION,
    build_phase5_risk_sizing_reviews,
    phase5_risk_sizing_paths,
    validate_phase5_risk_sizing_bundle,
    validate_phase5_risk_sizing_review,
    write_phase5_risk_sizing_reviews,
)


def _first_review(bundle: dict) -> dict:
    reviews = bundle.get("reviews", [])
    if not reviews:
        raise RuntimeError("no risk sizing reviews produced")
    return reviews[0]


def _eligible_probe(review: dict) -> dict:
    probe = deepcopy(review)
    probe["status"] = "eligible"
    probe["risk_decision"] = "paper_size_eligible"
    probe["paper_size_eligible"] = True
    probe["risk_blockers"] = []
    probe["risk_blocker_count"] = 0
    probe["proposed_risk_gbp"] = max(1.0, float(probe.get("max_risk_gbp", 10.0)) / 2)
    probe["proposed_risk_pct"] = max(0.1, float(probe.get("max_risk_pct", 1.0)) / 2)
    probe["approval_policy_status"] = "eligible"
    probe["approved_strategy_toggle_state"] = "approved_shadow"
    probe.setdefault("signal_evidence", {})["signal_integrity_passed"] = True
    probe["invalidation_condition_count"] = max(1, int(probe.get("invalidation_condition_count", 1) or 1))
    probe["pricing_gap_rollout_stage"] = "stage_a"
    probe["pricing_gap_relaxed_policy_enabled"] = False
    return probe


def _light_tier_eligible_probe(review: dict) -> dict:
    probe = _eligible_probe(review)
    probe["market_confirmation_policy"]["pricing_gap_policy_tier"] = "required_light"
    probe["pricing_gap_policy_tier"] = "required_light"
    probe["market_confirmation_policy"]["pricing_gap_satisfaction_rule"] = (
        "pricing-gap or transaction-cost evidence required"
    )
    probe["pricing_gap_policy_satisfaction_rule"] = (
        "pricing-gap or transaction-cost evidence required"
    )
    probe["signal_evidence"]["latest_market_confirmation_pricing_gap_status"] = (
        "pass_pricing_gap_transaction_cost_only"
    )
    probe["signal_evidence"]["latest_market_confirmation_pricing_gap_rollout_stage"] = "stage_b"
    probe["signal_evidence"]["latest_market_confirmation_pricing_gap_confirmation_source"] = (
        "structured_transaction_cost_event"
    )
    probe["pricing_gap_rollout_stage"] = "stage_b"
    probe["pricing_gap_relaxed_policy_enabled"] = True
    probe["pricing_gap_policy_satisfied"] = True
    probe["pricing_gap_relaxed_policy_path_used"] = True
    return probe


def _not_required_eligible_probe(review: dict) -> dict:
    probe = _eligible_probe(review)
    probe["market_confirmation_policy"]["pricing_gap_policy_tier"] = "not_required"
    probe["pricing_gap_policy_tier"] = "not_required"
    probe["market_confirmation_policy"]["pricing_gap_required"] = False
    probe["market_confirmation_policy"]["pricing_gap_satisfaction_rule"] = (
        "pricing-gap evidence optional after market confirmation"
    )
    probe["pricing_gap_policy_satisfaction_rule"] = (
        "pricing-gap evidence optional after market confirmation"
    )
    probe["signal_evidence"]["latest_market_confirmation_pricing_gap_status"] = (
        "pass_pricing_gap_not_required"
    )
    probe["signal_evidence"]["latest_market_confirmation_pricing_gap_rollout_stage"] = "stage_b"
    probe["signal_evidence"]["latest_market_confirmation_pricing_gap_confirmation_source"] = (
        "not_required_by_policy"
    )
    probe["pricing_gap_rollout_stage"] = "stage_b"
    probe["pricing_gap_relaxed_policy_enabled"] = True
    probe["pricing_gap_policy_satisfied"] = True
    probe["pricing_gap_relaxed_policy_path_used"] = True
    return probe


def main() -> int:
    errors: list[str] = []
    settings = Settings.from_env()
    output_path, history_path, event_log_path = phase5_risk_sizing_paths(settings)
    if event_log_path.exists():
        event_log_path.unlink()

    bundle = build_phase5_risk_sizing_reviews(settings=settings)
    output_path, history_path, event_log_path, written_bundle = (
        write_phase5_risk_sizing_reviews(
            bundle,
            settings=settings,
            record_event=True,
            event_log_path=event_log_path,
        )
    )
    validation_errors = validate_phase5_risk_sizing_bundle(written_bundle)
    event_replay = EventLog(event_log_path, echo=False).replay()
    first_review = _first_review(written_bundle)

    oversize_probe = _eligible_probe(first_review)
    oversize_probe["proposed_risk_gbp"] = float(oversize_probe["max_risk_gbp"]) + 1.0
    oversize_errors = validate_phase5_risk_sizing_review(oversize_probe)

    low_evidence_probe = _eligible_probe(first_review)
    low_evidence_probe["signal_evidence"]["signal_integrity_passed"] = False
    low_evidence_errors = validate_phase5_risk_sizing_review(low_evidence_probe)

    unapproved_probe = _eligible_probe(first_review)
    unapproved_probe["approval_policy_status"] = "blocked"
    unapproved_errors = validate_phase5_risk_sizing_review(unapproved_probe)

    missing_invalidation_probe = _eligible_probe(first_review)
    missing_invalidation_probe["invalidation_condition_count"] = 0
    missing_invalidation_probe["invalidation_conditions"] = []
    missing_invalidation_errors = validate_phase5_risk_sizing_review(missing_invalidation_probe)

    decision_source_coverage_probe = _eligible_probe(first_review)
    decision_source_coverage_probe["source_summary"][
        "decision_source_usage_complete"
    ] = False
    decision_source_coverage_probe["source_summary"][
        "decision_source_coverage"
    ]["decision_source_usage_complete"] = False
    decision_source_coverage_errors = validate_phase5_risk_sizing_review(
        decision_source_coverage_probe
    )

    drawdown_probe = _eligible_probe(first_review)
    drawdown_probe["drawdown_pct"] = float(drawdown_probe["max_drawdown_pct"]) + 1.0
    drawdown_errors = validate_phase5_risk_sizing_review(drawdown_probe)

    broker_probe = deepcopy(first_review)
    broker_probe["broker_write_allowed"] = True
    broker_errors = validate_phase5_risk_sizing_review(broker_probe)

    staged_order_probe = deepcopy(first_review)
    staged_order_probe["staged_order_created"] = True
    staged_order_errors = validate_phase5_risk_sizing_review(staged_order_probe)

    paper_order_probe = deepcopy(first_review)
    paper_order_probe["paper_order_allowed"] = True
    paper_order_errors = validate_phase5_risk_sizing_review(paper_order_probe)

    yahoo_probe = deepcopy(first_review)
    yahoo_probe["market_confirmation_policy"]["yahoo_finance_role"] = "canonical_source"
    yahoo_errors = validate_phase5_risk_sizing_review(yahoo_probe)

    preference_probe = deepcopy(first_review)
    preference_probe["preference_policy"]["source_quorum_credit_allowed"] = True
    preference_errors = validate_phase5_risk_sizing_review(preference_probe)

    light_tier_probe = _light_tier_eligible_probe(first_review)
    light_tier_errors = validate_phase5_risk_sizing_review(light_tier_probe)

    not_required_probe = _not_required_eligible_probe(first_review)
    not_required_errors = validate_phase5_risk_sizing_review(not_required_probe)

    stage_a_light_probe = _eligible_probe(first_review)
    stage_a_light_probe["market_confirmation_policy"]["pricing_gap_policy_tier"] = "required_light"
    stage_a_light_probe["pricing_gap_policy_tier"] = "required_light"
    stage_a_light_probe["signal_evidence"]["latest_market_confirmation_pricing_gap_status"] = (
        "pass_pricing_gap_transaction_cost_only"
    )
    stage_a_light_probe["signal_evidence"]["latest_market_confirmation_pricing_gap_rollout_stage"] = "stage_a"
    stage_a_light_probe["pricing_gap_policy_satisfied"] = False
    stage_a_light_probe["pricing_gap_relaxed_policy_path_used"] = False
    stage_a_light_errors = validate_phase5_risk_sizing_review(stage_a_light_probe)

    strict_tier_probe = _eligible_probe(first_review)
    strict_tier_probe["market_confirmation_policy"]["pricing_gap_policy_tier"] = "required_strict"
    strict_tier_probe["pricing_gap_policy_tier"] = "required_strict"
    strict_tier_probe["signal_evidence"]["latest_market_confirmation_pricing_gap_status"] = (
        "pass_pricing_gap_transaction_cost_only"
    )
    strict_tier_probe["signal_evidence"]["latest_market_confirmation_pricing_gap_rollout_stage"] = "stage_b"
    strict_tier_probe["pricing_gap_rollout_stage"] = "stage_b"
    strict_tier_probe["pricing_gap_relaxed_policy_enabled"] = True
    strict_tier_probe["pricing_gap_policy_satisfied"] = False
    strict_tier_probe["pricing_gap_relaxed_policy_path_used"] = False
    strict_tier_errors = validate_phase5_risk_sizing_review(strict_tier_probe)

    source_coverage_complete_count = sum(
        1
        for review in written_bundle.get("reviews", [])
        if isinstance(review, dict)
        and review.get("source_summary", {}).get("all_canonical_sources_considered") is True
        and review.get("source_summary", {}).get("decision_source_usage_complete") is True
        and review.get("source_summary", {}).get("source_quorum_bypass_allowed") is False
    )

    print("phase5_risk_sizing_status=" + written_bundle["status"])
    print(f"phase5_risk_sizing_schema_version={PHASE5_RISK_SIZING_SCHEMA_VERSION}")
    print(f"phase5_risk_sizing_artifact_path={output_path}")
    print(f"phase5_risk_sizing_history_path={history_path}")
    print(f"phase5_risk_sizing_event_log_path={event_log_path}")
    print(f"phase5_risk_sizing_review_count={written_bundle['risk_review_count']}")
    print(
        "phase5_risk_sizing_pricing_gap_rollout_stage="
        f"{written_bundle.get('pricing_gap_rollout_stage')}"
    )
    print(f"phase5_risk_sizing_eligible_count={written_bundle['eligible_count']}")
    print(f"phase5_risk_sizing_hold_count={written_bundle['hold_count']}")
    print(f"phase5_risk_sizing_blocked_count={written_bundle['blocked_count']}")
    print(
        "phase5_risk_sizing_paper_size_eligible_count="
        f"{written_bundle['paper_size_eligible_count']}"
    )
    print(
        "phase5_risk_sizing_stage_b_candidate_count="
        f"{written_bundle.get('pricing_gap_stage_b_candidate_count', 0)}"
    )
    print(
        "phase5_risk_sizing_approval_policy_eligible_count="
        f"{written_bundle['approval_policy_eligible_count']}"
    )
    print(
        "phase5_risk_sizing_source_coverage_complete_count="
        f"{source_coverage_complete_count}"
    )
    print(f"phase5_risk_sizing_event_log_written={written_bundle['event_log_written']}")
    print(f"phase5_risk_sizing_event_log_total_events={event_replay['total_events']}")
    print(f"phase5_risk_sizing_validation_error_count={len(validation_errors)}")
    print(f"phase5_risk_sizing_global_error_count={written_bundle['global_risk_error_count']}")
    print(
        "phase5_risk_sizing_risk_approval_allowed_count="
        f"{written_bundle['risk_approval_allowed_count']}"
    )
    print(
        "phase5_risk_sizing_trade_candidate_created_count="
        f"{written_bundle['trade_candidate_created_count']}"
    )
    print(
        "phase5_risk_sizing_execution_allowed_count="
        f"{written_bundle['execution_allowed_count']}"
    )
    print(
        "phase5_risk_sizing_paper_order_allowed_count="
        f"{written_bundle['paper_order_allowed_count']}"
    )
    print(
        "phase5_risk_sizing_broker_write_allowed_count="
        f"{written_bundle['broker_write_allowed_count']}"
    )
    print(
        "phase5_risk_sizing_position_created_count="
        f"{written_bundle['position_created_count']}"
    )
    print(f"phase5_risk_sizing_yahoo_role={written_bundle['yahoo_finance_role']}")
    print(
        "phase5_risk_sizing_preference_source36="
        f"{written_bundle['preference_mcp_source_36']}"
    )
    print(f"phase5_risk_sizing_oversize_probe_error_count={len(oversize_errors)}")
    print(f"phase5_risk_sizing_low_evidence_probe_error_count={len(low_evidence_errors)}")
    print(f"phase5_risk_sizing_unapproved_probe_error_count={len(unapproved_errors)}")
    print(
        "phase5_risk_sizing_missing_invalidation_probe_error_count="
        f"{len(missing_invalidation_errors)}"
    )
    print(
        "phase5_risk_sizing_decision_source_coverage_probe_error_count="
        f"{len(decision_source_coverage_errors)}"
    )
    print(f"phase5_risk_sizing_drawdown_probe_error_count={len(drawdown_errors)}")
    print(f"phase5_risk_sizing_broker_probe_error_count={len(broker_errors)}")
    print(f"phase5_risk_sizing_staged_order_probe_error_count={len(staged_order_errors)}")
    print(f"phase5_risk_sizing_paper_order_probe_error_count={len(paper_order_errors)}")
    print(f"phase5_risk_sizing_yahoo_probe_error_count={len(yahoo_errors)}")
    print(f"phase5_risk_sizing_preference_probe_error_count={len(preference_errors)}")
    print(f"phase5_risk_sizing_light_tier_probe_error_count={len(light_tier_errors)}")
    print(f"phase5_risk_sizing_not_required_probe_error_count={len(not_required_errors)}")
    print(f"phase5_risk_sizing_stage_a_light_probe_error_count={len(stage_a_light_errors)}")
    print(f"phase5_risk_sizing_strict_tier_probe_error_count={len(strict_tier_errors)}")
    print("phase5_risk_sizing_boundary=" + written_bundle["boundary"])

    if validation_errors:
        errors.extend(validation_errors)
    if written_bundle["status"] != "ok":
        errors.append("risk_sizing_bundle_not_ok")
    if written_bundle["risk_review_count"] != 5:
        errors.append("risk_sizing_review_count_not_five")
    if written_bundle["global_risk_error_count"] != 0:
        errors.append("risk_sizing_global_errors_present")
    if source_coverage_complete_count != written_bundle["risk_review_count"]:
        errors.append("risk_sizing_source_coverage_incomplete")
    if written_bundle["event_log_written"] is not True:
        errors.append("risk_sizing_event_log_not_written")
    if event_replay["total_events"] != written_bundle["risk_review_count"]:
        errors.append("risk_sizing_event_log_count_mismatch")
    if written_bundle["approval_policy_eligible_count"] == 0:
        if written_bundle["eligible_count"] != 0:
            errors.append("risk_sizing_eligible_without_policy")
        if written_bundle["paper_size_eligible_count"] != 0:
            errors.append("risk_sizing_paper_size_without_policy")
        if written_bundle["blocked_count"] != written_bundle["risk_review_count"]:
            errors.append("risk_sizing_blocked_count_mismatch_for_policy_hold")
    elif written_bundle["paper_size_eligible_count"] != written_bundle["eligible_count"]:
        errors.append("risk_sizing_paper_size_count_mismatch")
    for key in (
        "risk_approval_allowed_count",
        "trade_candidate_created_count",
        "execution_policy_handoff_allowed_count",
        "execution_allowed_count",
        "execution_intent_created_count",
        "paper_order_allowed_count",
        "staged_order_created_count",
        "paper_order_submitted_count",
        "broker_write_allowed_count",
        "broker_submit_receipt_created_count",
        "position_created_count",
        "live_capital_enabled_count",
    ):
        if written_bundle.get(key) != 0:
            errors.append(f"risk_sizing_boundary_count_not_zero:{key}")
    if "proposed_risk_above_cap" not in oversize_errors:
        errors.append("oversize_probe_not_rejected")
    if "eligible_without_signal_integrity_pass" not in low_evidence_errors:
        errors.append("low_evidence_probe_not_rejected")
    if "eligible_without_q5_2_policy" not in unapproved_errors:
        errors.append("unapproved_probe_not_rejected")
    if "eligible_without_invalidation_conditions" not in missing_invalidation_errors:
        errors.append("missing_invalidation_probe_not_rejected")
    if "source_summary_decision_source_usage_incomplete" not in decision_source_coverage_errors:
        errors.append("decision_source_coverage_probe_not_rejected")
    if "eligible_with_drawdown_above_cap" not in drawdown_errors:
        errors.append("drawdown_probe_not_rejected")
    if "risk_sizing_boundary_enabled:broker_write_allowed" not in broker_errors:
        errors.append("broker_probe_not_rejected")
    if "risk_sizing_boundary_enabled:staged_order_created" not in staged_order_errors:
        errors.append("staged_order_probe_not_rejected")
    if "risk_sizing_boundary_enabled:paper_order_allowed" not in paper_order_errors:
        errors.append("paper_order_probe_not_rejected")
    if "market_yahoo_role_not_supplemental" not in yahoo_errors:
        errors.append("yahoo_probe_not_rejected")
    if "preference_policy_source_quorum_credit_allowed" not in preference_errors:
        errors.append("preference_probe_not_rejected")
    if light_tier_errors:
        errors.append("light_tier_probe_not_accepted")
    if not_required_errors:
        errors.append("not_required_probe_not_accepted")
    if "eligible_without_policy_satisfied_pricing_gap" not in stage_a_light_errors:
        errors.append("stage_a_light_probe_not_rejected")
    if "eligible_without_policy_satisfied_pricing_gap" not in strict_tier_errors:
        errors.append("strict_tier_probe_not_rejected")

    if errors:
        for error in errors:
            print(f"phase5_risk_sizing_error={error}")
        print("phase5_risk_sizing_check=failed")
        return 1

    print("phase5_risk_sizing_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
