"""Canonical Tests & Improvements projection for Qadam.

The pipeline connects supported lessons to concrete change hypotheses and their
historical, shadow, nonlinear, approval, and Stage 1 handoff states. It never
applies a change or creates trading authority.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_learning_loop_contract import (
    LEARNING_LOOP_STEPS,
    build_learning_loop_overview,
    validate_learning_loop_overview,
)
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_wave_b_common import stable_id

SCHEMA_VERSION = "qadam_improvement_pipeline_dashboard.v2"
PHASE_ID = "LI-2"

IMPROVEMENT_PIPELINE_ARTIFACT = "qadam_improvement_pipeline_dashboard.json"
IMPROVEMENT_PROPOSALS_ARTIFACT = "qadam_improvement_proposals_v3.jsonl"
APPLIED_VERSIONS_ARTIFACT = "qadam_applied_learning_versions.jsonl"
CHECK_ARTIFACT = "qadam_improvement_pipeline_checks.json"

ATTRIBUTION_ARTIFACT = "qadam_learning_attribution_v3.jsonl"
BACKFILL_ARTIFACT = "qadam_backfill_coverage.json"
BACKTEST_SUMMARY_ARTIFACT = "qadam_backtest_results_summary.json"
BACKTEST_REJECTIONS_ARTIFACT = "qadam_backtest_rejections.jsonl"
SHADOW_STATE_ARTIFACT = "qadam_forward_shadow_state.json"
SHADOW_DECISIONS_ARTIFACT = "qadam_forward_shadow_decisions.jsonl"
SHADOW_OUTCOMES_ARTIFACT = "qadam_forward_shadow_outcomes.jsonl"
SHADOW_CALIBRATION_ARTIFACT = "qadam_shadow_calibration.json"
SHADOW_PROMOTION_ARTIFACT = "qadam_shadow_promotion_readiness.json"
QUANTUM_SUMMARY_ARTIFACT = "qadam_quantum_usefulness_summary.json"
EDGE_REGISTRY_ARTIFACT = "qadam_edge_registry.jsonl"
HISTORICAL_MEMORY_ARTIFACT = "qsase_historical_memory_completion.json"

TERMINAL_STATES = {"rejected", "retired", "rolled_back"}
ACTIVE_STATES = {"needs_data", "testing", "shadowing", "ready_for_review", "approved", "applied"}


def _change_type(record: dict[str, Any]) -> str:
    champion = record.get("champion_challenger")
    champion = champion if isinstance(champion, dict) else {}
    token = str(champion.get("proposal_type") or "research_repair_proposal")
    if "source" in token or "trust" in token:
        return "source_trust"
    if "strategy" in token:
        return "strategy"
    if "akber" in token or "threshold" in token:
        return "akber"
    if "risk" in token:
        return "risk"
    if "model" in token or "routing" in token:
        return "pattern_routing"
    if "feature" in token:
        return "feature"
    if "operational" in str(record.get("outcome_type") or ""):
        return "operations"
    return "data_repair"


def _target_stage(change_type: str) -> str:
    return {
        "source_trust": "observe",
        "data_repair": "observe",
        "feature": "patterns",
        "pattern_routing": "patterns",
        "strategy": "decide",
        "akber": "decide",
        "risk": "trade",
        "operations": "system",
    }.get(change_type, "observe")


def _decision_state(record: dict[str, Any]) -> str:
    champion = record.get("champion_challenger")
    champion = champion if isinstance(champion, dict) else {}
    state = str(champion.get("state") or "needs_data").lower()
    if state in {"rejected", "retired"}:
        return state
    if state in {"backtested"}:
        return "testing"
    if state in {"shadowing"}:
        return "shadowing"
    if state in {"approved-for-research", "proposed"}:
        return "testing"
    if state in {"approved-for-paper"}:
        return "ready_for_review"
    if state in {"approved"}:
        return "approved"
    if state in {"applied"}:
        return "applied"
    if state in {"degraded", "blocked", "hold"}:
        return "needs_data"
    return "needs_data"


def _historical_test(
    backfill: dict[str, Any],
    backtest: dict[str, Any],
    rejections: list[dict[str, Any]],
) -> dict[str, Any]:
    attempted = int(backtest.get("attempted_hypothesis_count", 0) or 0)
    completed = int(backtest.get("completed_method_count", 0) or 0)
    holdout = int(backtest.get("untouched_holdout_result_count", 0) or 0)
    status = "not_started" if attempted == 0 else ("complete" if completed and holdout else "testing")
    return {
        "status": status,
        "provider_partitions_complete": int(backfill.get("completed_partition_count", 0) or 0),
        "provider_partitions_total": int(backfill.get("total_partition_count", 0) or 0),
        "provider_rows": int(backfill.get("provider_row_count", 0) or 0),
        "attempted_hypothesis_count": attempted,
        "completed_method_count": completed,
        "untouched_holdout_result_count": holdout,
        "cost_adjusted_result_count": int(backtest.get("cost_adjusted_result_count", 0) or 0),
        "false_discovery_adjusted_result_count": int(
            backtest.get("false_discovery_adjusted_result_count", 0) or 0
        ),
        "empirical_claim_allowed": backtest.get("empirical_claim_allowed") is True,
        "rejection_count": len(rejections),
    }


def _shadow_test(
    state: dict[str, Any],
    decisions: list[dict[str, Any]],
    outcomes: list[dict[str, Any]],
    calibration: dict[str, Any],
    promotion: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": state.get("status") or "not_started",
        "decision_count": len(decisions),
        "outcome_count": len(outcomes),
        "completed_outcome_count": int(calibration.get("completed_outcome_count", 0) or 0),
        "directional_hit_rate": calibration.get("directional_hit_rate"),
        "mean_net_return": calibration.get("mean_net_return"),
        "calibration_claim_allowed": calibration.get("calibration_claim_allowed") is True,
        "promotion_ready": promotion.get("promotion_ready") is True,
        "blockers": promotion.get("blockers") or [],
    }


def _proposal_from_record(
    record: dict[str, Any],
    *,
    historical_test: dict[str, Any],
    shadow_test: dict[str, Any],
    quantum: dict[str, Any],
) -> dict[str, Any]:
    champion = record.get("champion_challenger")
    champion = champion if isinstance(champion, dict) else {}
    attribution_id = str(record.get("attribution_id") or record.get("source_record_id") or "unknown")
    change_type = _change_type(record)
    state = _decision_state(record)
    reason = str(champion.get("reason") or "Evidence is incomplete.")
    proposal_id = stable_id("learning-improvement-v3", attribution_id, change_type)
    ready = (
        historical_test["empirical_claim_allowed"]
        and shadow_test["promotion_ready"]
        and state not in TERMINAL_STATES
    )
    if ready:
        state = "ready_for_review"
    approval = {
        "approved": champion.get("approved") is True,
        "approved_by": champion.get("approved_by"),
        "approved_at": champion.get("approved_at"),
    }
    review_status = (
        "approved"
        if approval["approved"]
        else ("ready_for_review" if state == "ready_for_review" else "waiting_for_evidence")
    )
    return {
        "proposal_id": proposal_id,
        "generated_at": record.get("generated_at"),
        "lesson_ids": [attribution_id],
        "change_type": change_type,
        "target_stage": _target_stage(change_type),
        "current_version": "current_behavior_unchanged",
        "proposed_version": f"proposal:{proposal_id}",
        "supported_lesson": reason,
        "change_hypothesis": (
            "Complete the missing evidence and approval inputs, then reassess the guarded handoff without weakening safety checks."
            if change_type == "operations"
            else "Repair the identified evidence gap, retest the relationship, and keep the current behavior until the result is reviewed."
        ),
        "expected_benefit": (
            "Improve evidence quality or decision reliability without weakening the existing safety boundary."
        ),
        "failure_risk": (
            "The change may overfit limited evidence, reduce useful selectivity, or create false confidence."
        ),
        "historical_test": historical_test,
        "forward_shadow_test": shadow_test,
        "nonlinear_quantum_test": {
            "status": quantum.get("status") or "not_measurable",
            "incremental_value_measured": quantum.get("incremental_value_measured") is True,
            "incremental_value": quantum.get("incremental_value"),
        },
        "decision_state": state,
        "next_action": (
            "Keep this record rejected unless new independent evidence justifies a new proposal."
            if state in TERMINAL_STATES
            else "Complete provider-backed history, statistical testing, and real-time no-order observation."
        ),
        "review": {
            "status": review_status,
            "ready": state == "ready_for_review",
            "decision_state": state,
            "reason": "Review can begin only after historical and forward evidence are complete.",
        },
        "approval": approval,
        "applied_version_state": {
            "status": "applied" if state == "applied" else "not_applied",
            "version": champion.get("applied_version"),
            "effective_from": champion.get("effective_from"),
        },
        "rollback_condition": (
            "Reject or roll back if holdout, cost-adjusted, regime, or forward-shadow evidence deteriorates."
        ),
        "stage1_handoff": {
            "state": "inert_until_applied",
            "target_stage": _target_stage(change_type),
            "applied_version": None,
        },
        "source_record": {
            "outcome_type": record.get("outcome_type"),
            "origin_class": record.get("origin_class"),
            "champion_challenger_state": champion.get("state"),
        },
        "authority": authority_flags(),
    }


def build_improvement_pipeline_view_model(
    settings: Settings | None = None,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    generated = generated_at or now_iso()
    attribution = read_jsonl(runtime / ATTRIBUTION_ARTIFACT)
    backfill = read_json(runtime / BACKFILL_ARTIFACT)
    backtest = read_json(runtime / BACKTEST_SUMMARY_ARTIFACT)
    rejections = read_jsonl(runtime / BACKTEST_REJECTIONS_ARTIFACT)
    shadow_state = read_json(runtime / SHADOW_STATE_ARTIFACT)
    shadow_decisions = read_jsonl(runtime / SHADOW_DECISIONS_ARTIFACT)
    shadow_outcomes = read_jsonl(runtime / SHADOW_OUTCOMES_ARTIFACT)
    calibration = read_json(runtime / SHADOW_CALIBRATION_ARTIFACT)
    promotion = read_json(runtime / SHADOW_PROMOTION_ARTIFACT)
    quantum = read_json(runtime / QUANTUM_SUMMARY_ARTIFACT)
    edges = read_jsonl(runtime / EDGE_REGISTRY_ARTIFACT)
    historical_memory = read_json(runtime / HISTORICAL_MEMORY_ARTIFACT)
    applied_versions = read_jsonl(runtime / APPLIED_VERSIONS_ARTIFACT)
    historical_test = _historical_test(backfill, backtest, rejections)
    shadow_test = _shadow_test(
        shadow_state,
        shadow_decisions,
        shadow_outcomes,
        calibration,
        promotion,
    )
    eligible_attribution = [
        record for record in attribution if record.get("origin_class") != "mirror_only_historical_record"
    ]
    excluded_mirror_count = len(attribution) - len(eligible_attribution)
    proposals = [
        _proposal_from_record(
            record,
            historical_test=historical_test,
            shadow_test=shadow_test,
            quantum=quantum,
        )
        for record in eligible_attribution
    ]
    state_counts = Counter(str(proposal.get("decision_state")) for proposal in proposals)
    active = [proposal for proposal in proposals if proposal["decision_state"] in ACTIVE_STATES]
    ready = [proposal for proposal in proposals if proposal["decision_state"] == "ready_for_review"]
    applied = [record for record in applied_versions if record.get("decision_state") == "applied"]
    complete_partitions = int(backfill.get("completed_partition_count", 0) or 0)
    total_partitions = int(backfill.get("total_partition_count", 0) or 0)
    attempted = int(backtest.get("attempted_hypothesis_count", 0) or 0)
    shadow_count = len(shadow_decisions)
    current_answer = (
        "No improvement is ready to apply. "
        f"Provider-backed history covers {complete_partitions} of {total_partitions} required data slices, "
        f"{attempted} relationship tests have run, and "
        f"{shadow_count} eligible ideas have been watched in real time without an order."
    )
    structural = historical_memory.get("dashboard_summary")
    structural = structural if isinstance(structural, dict) else {}
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_improvement_pipeline_dashboard",
        "phase_id": PHASE_ID,
        "generated_at": generated,
        "status": "improvement_ready_for_review" if ready else "improvement_evidence_maturing",
        "headline": "How Qadam Improves",
        "plain_english": (
            "A lesson becomes a proposed change, then must survive historical tests, real-time no-order observation, "
            "and governed review before the next observation cycle can use it."
        ),
        "loop_overview": build_learning_loop_overview("improvements"),
        "current_answer": current_answer,
        "counts": {
            "attribution_record_count": len(attribution),
            "excluded_mirror_record_count": excluded_mirror_count,
            "proposal_record_count": len(proposals),
            "active_candidate_count": len(active),
            "ready_for_review_count": len(ready),
            "applied_version_count": len(applied),
            "decision_state_counts": dict(sorted(state_counts.items())),
            "validated_edge_count": len([edge for edge in edges if edge.get("edge_state") == "validated"]),
        },
        "pipeline_steps": [step["label"] for step in LEARNING_LOOP_STEPS],
        "proposals": proposals,
        "active_candidates": active,
        "rejected_or_held": [proposal for proposal in proposals if proposal["decision_state"] in TERMINAL_STATES],
        "applied_versions": applied,
        "test_readiness": {
            "historical": historical_test,
            "forward_shadow": shadow_test,
            "structural_baseline": {
                "memory_record_count": historical_memory.get("memory_record_count", 0),
                "complete_forward_window_count": historical_memory.get("complete_forward_window_count", 0),
                "missing_forward_window_count": historical_memory.get("missing_forward_window_count", 0),
                "raw_complete_forward_window_ratio": historical_memory.get("raw_complete_forward_window_ratio", 0),
                "instrument_completion": historical_memory.get("instrument_completion") or [],
                "headline": structural.get("headline"),
            },
        },
        "feedback_destinations": [
            {"target_stage": "observe", "label": "Data Sources", "route": {"module_id": "observe", "view_id": "sources"}},
            {"target_stage": "observe", "label": "Trading Universe", "route": {"module_id": "observe", "view_id": "universe"}},
            {"target_stage": "patterns", "label": "Pattern Discovery", "route": {"module_id": "patterns", "view_id": "findings"}},
            {"target_stage": "decide", "label": "Trading Strategies", "route": {"module_id": "decide", "view_id": "strategies"}},
            {"target_stage": "decide", "label": "Decision Filter", "route": {"module_id": "decide", "view_id": "decision"}},
            {"target_stage": "trade", "label": "Trade & Risk", "route": {"module_id": "trade", "view_id": "orders"}},
        ],
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "paper_only": True,
        "authority": authority_flags(),
        "boundary": (
            "Tests and improvements are proposal-first. Only a separately approved applied version may feed Stage 1; "
            "this projection cannot mutate policy, approve risk, create orders, or grant proof credit."
        ),
    }


def validate_improvement_pipeline_view_model(model: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    proposals = model.get("proposals") if isinstance(model.get("proposals"), list) else []
    counts = model.get("counts") if isinstance(model.get("counts"), dict) else {}
    if counts.get("proposal_record_count") != len(proposals):
        errors.append("improvement_pipeline_proposal_count_mismatch")
    if any(proposal.get("source_record", {}).get("origin_class") == "mirror_only_historical_record" for proposal in proposals):
        errors.append("improvement_pipeline_mirror_record_became_proposal")
    for proposal in proposals:
        if proposal.get("decision_state") == "ready_for_review":
            if proposal.get("historical_test", {}).get("empirical_claim_allowed") is not True:
                errors.append("improvement_ready_without_historical_evidence")
            if proposal.get("forward_shadow_test", {}).get("promotion_ready") is not True:
                errors.append("improvement_ready_without_forward_shadow")
        if proposal.get("stage1_handoff", {}).get("state") != "inert_until_applied":
            errors.append("improvement_proposal_stage1_handoff_not_inert")
    for applied in model.get("applied_versions", []):
        approval = applied.get("approval") if isinstance(applied.get("approval"), dict) else {}
        if approval.get("approved") is not True:
            errors.append("improvement_applied_without_approval")
        if not applied.get("effective_from"):
            errors.append("improvement_applied_without_effective_timestamp")
        if not applied.get("expected_behavior"):
            errors.append("improvement_applied_without_expected_behavior")
        if not applied.get("monitoring_window"):
            errors.append("improvement_applied_without_monitoring_window")
        if not applied.get("rollback_condition"):
            errors.append("improvement_applied_without_rollback_condition")
    if model.get("public_safe") is not True or model.get("read_only") is not True:
        errors.append("improvement_pipeline_not_public_read_only")
    if model.get("command_disabled") is not True:
        errors.append("improvement_pipeline_command_path_enabled")
    errors.extend(
        validate_learning_loop_overview(model.get("loop_overview"), expected_page="improvements")
    )
    errors.extend(validate_authority(model.get("authority", {}), prefix="improvement_pipeline"))
    return unique_errors(errors)


def build_and_write_improvement_pipeline_view_model(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    model = build_improvement_pipeline_view_model(settings)
    errors = validate_improvement_pipeline_view_model(model)
    store.write_json(IMPROVEMENT_PIPELINE_ARTIFACT, model)
    store.write_jsonl(IMPROVEMENT_PROPOSALS_ARTIFACT, model["proposals"])
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_improvement_pipeline_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "implementation_ready": not errors,
        **model["counts"],
        "mirror_records_excluded_from_proposals": all(
            proposal.get("source_record", {}).get("origin_class") != "mirror_only_historical_record"
            for proposal in model["proposals"]
        ),
        "non_applied_stage1_handoffs_are_inert": all(
            proposal.get("stage1_handoff", {}).get("state") == "inert_until_applied"
            for proposal in model["proposals"]
        ),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    store.write_json(CHECK_ARTIFACT, checks)
    return model, checks, errors
