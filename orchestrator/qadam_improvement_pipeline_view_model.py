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

IMPROVEMENTS_PRESENTATION_VERSION = "qadam_tests_improvements.v2"
IMPROVEMENTS_PAGE_COPY = {
    "eyebrow": "Tests & Improvements",
    "title": "What Will Change in Qadam",
    "subtitle": (
        "See which improvements are approved for integration, which are still being "
        "evaluated, and which changes are already in use."
    ),
}


def _integer_or_none(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _has_real_value(value: Any) -> bool:
    token = str(value or "").strip().lower()
    return bool(token) and token not in {
        "none",
        "null",
        "unknown",
        "not recorded",
        "not_recorded",
        "current_behavior_unchanged",
        "placeholder",
        "tbd",
    } and not token.startswith("proposal:")


def _valid_public_authority(authority: Any) -> bool:
    return isinstance(authority, dict) and not validate_authority(
        authority,
        prefix="scheduled_improvement",
    )


def is_scheduled_improvement(proposal: dict[str, Any]) -> bool:
    state = str(proposal.get("decision_state") or "").lower()
    if state in TERMINAL_STATES or state == "applied":
        return False
    approval = proposal.get("approval") if isinstance(proposal.get("approval"), dict) else {}
    release = proposal.get("release_record") if isinstance(proposal.get("release_record"), dict) else {}
    activation_recorded = _has_real_value(release.get("effective_from")) or _has_real_value(
        release.get("activation_condition")
    )
    destination_recorded = _has_real_value(release.get("affected_component")) or _has_real_value(
        release.get("destination")
    )
    return all(
        (
            approval.get("approved") is True,
            _has_real_value(approval.get("approved_by")),
            _has_real_value(approval.get("approved_at")),
            _has_real_value(release.get("target_version")),
            destination_recorded,
            activation_recorded,
            _has_real_value(release.get("expected_behavior")),
            _has_real_value(release.get("monitoring_window")),
            _has_real_value(release.get("rollback_condition")),
            _valid_public_authority(proposal.get("authority")),
        )
    )


def _valid_integrated_version(record: dict[str, Any]) -> bool:
    approval = record.get("approval") if isinstance(record.get("approval"), dict) else {}
    version = record.get("applied_version") or record.get("target_version") or record.get("version")
    return all(
        (
            str(record.get("decision_state") or "").lower() == "applied",
            approval.get("approved") is True,
            _has_real_value(approval.get("approved_by")),
            _has_real_value(approval.get("approved_at")),
            _has_real_value(version),
            _has_real_value(record.get("effective_from")),
            _has_real_value(record.get("expected_behavior")),
            _has_real_value(record.get("monitoring_window")),
            _has_real_value(record.get("rollback_condition")),
        )
    )


def classify_improvement_proposal(
    proposal: dict[str, Any],
    *,
    projection_available: bool = True,
    projection_stale: bool = False,
) -> str:
    if not projection_available or projection_stale:
        return "status_unavailable"
    state = str(proposal.get("decision_state") or "").lower()
    if state in TERMINAL_STATES:
        return "not_proceeding"
    if state == "applied":
        return "integrated" if _valid_integrated_version(proposal) else "status_unavailable"
    if is_scheduled_improvement(proposal):
        return "scheduled"
    return "under_evaluation"


def _proposal_title(proposal: dict[str, Any]) -> str:
    labels = {
        "operations": "Operational evidence readiness",
        "data_repair": "Data repair proposal",
        "source_trust": "Source evidence quality",
        "feature": "Research feature definition",
        "pattern_routing": "Pattern routing reliability",
        "strategy": "Strategy rule proposal",
        "akber": "Akber filter proposal",
        "risk": "Risk control proposal",
    }
    return labels.get(str(proposal.get("change_type") or ""), "Qadam improvement proposal")


def _improvement_type(proposal: dict[str, Any]) -> str:
    labels = {
        "operations": "Operational evidence improvement",
        "data_repair": "Data improvement",
        "source_trust": "Source evidence improvement",
        "feature": "Research feature improvement",
        "pattern_routing": "System improvement",
        "strategy": "Strategy improvement",
        "akber": "Decision-filter improvement",
        "risk": "Risk-control improvement",
    }
    return labels.get(str(proposal.get("change_type") or ""), "Research improvement")


def _affected_component(proposal: dict[str, Any]) -> str:
    release = proposal.get("release_record") if isinstance(proposal.get("release_record"), dict) else {}
    if _has_real_value(release.get("affected_component")):
        return str(release["affected_component"])
    labels = {
        "operations": "Operational evidence and release readiness",
        "data_repair": "Historical data quality",
        "source_trust": "Source evidence quality",
        "feature": "Pattern research inputs",
        "pattern_routing": "Pattern research routing",
        "strategy": "Trading strategy rules",
        "akber": "Akber's 6-Stage Filter",
        "risk": "Paper portfolio risk controls",
    }
    return labels.get(str(proposal.get("change_type") or ""), "Qadam research operations")


def _evidence_public_state(value: Any) -> str:
    state = str(value or "").lower()
    if state in {"complete", "passed", "validated"}:
        return "Complete"
    if state in {"testing", "running", "shadowing", "in_progress"}:
        return "Underway"
    if state in {"failed", "rejected", "blocked"}:
        return "Failed"
    return "Not started"


def _under_evaluation_projection(proposal: dict[str, Any]) -> dict[str, Any]:
    historical = proposal.get("historical_test") if isinstance(proposal.get("historical_test"), dict) else {}
    forward = proposal.get("forward_shadow_test") if isinstance(proposal.get("forward_shadow_test"), dict) else {}
    review = proposal.get("review") if isinstance(proposal.get("review"), dict) else {}
    historical_state = _evidence_public_state(historical.get("status"))
    forward_state = _evidence_public_state(forward.get("status"))
    if historical_state == "Not started":
        blocker = "Historical evidence testing has not started."
    elif historical_state != "Complete":
        blocker = "Historical evidence is not yet complete enough for review."
    elif forward_state == "Not started":
        blocker = "Real-time no-order observation has not started."
    elif forward_state != "Complete":
        blocker = "Real-time no-order evidence is still incomplete."
    elif review.get("ready") is not True:
        blocker = "Governed review has not confirmed that the change is ready."
    else:
        blocker = "Approval, version, activation, monitoring, or rollback details are incomplete."
    source_ids = proposal.get("lesson_ids") if isinstance(proposal.get("lesson_ids"), list) else []
    return {
        "proposal_id": str(proposal.get("proposal_id") or "unknown"),
        "occurred_at": proposal.get("generated_at"),
        "public_state": "under_evaluation",
        "title": _proposal_title(proposal),
        "improvement_type": _improvement_type(proposal),
        "affected_component": _affected_component(proposal),
        "source_lesson_id": source_ids[0] if source_ids else None,
        "source_lesson_summary": proposal.get("supported_lesson"),
        "proposed_change": proposal.get("change_hypothesis"),
        "expected_benefit": proposal.get("expected_benefit"),
        "expected_benefit_is_measured": False,
        "historical_evidence_state": historical_state,
        "forward_observation_state": forward_state,
        "current_conclusion": "Continue testing" if review.get("ready") is not True else "Ready for review",
        "blocker": blocker,
        "next_action": proposal.get("next_action") or "Complete the next missing evidence gate.",
        "current_behavior": "Qadam's current behavior remains unchanged.",
        "gate_progress": [
            {"label": "Change defined", "state": "complete"},
            {"label": "Historical evidence", "state": historical_state.lower().replace(" ", "_")},
            {"label": "Forward observation", "state": forward_state.lower().replace(" ", "_")},
            {
                "label": "Review",
                "state": "complete" if review.get("status") == "approved" else ("ready" if review.get("ready") is True else "not_started"),
            },
        ],
    }


def _scheduled_projection(proposal: dict[str, Any]) -> dict[str, Any]:
    release = proposal.get("release_record") if isinstance(proposal.get("release_record"), dict) else {}
    approval = proposal.get("approval") if isinstance(proposal.get("approval"), dict) else {}
    return {
        "proposal_id": str(proposal.get("proposal_id") or "unknown"),
        "occurred_at": proposal.get("generated_at"),
        "public_state": "scheduled",
        "title": _proposal_title(proposal),
        "what_will_change": release.get("expected_behavior"),
        "affected_component": release.get("affected_component") or release.get("destination"),
        "justification": proposal.get("supported_lesson"),
        "evidence_summary": "Historical and forward evidence passed the required review gates.",
        "target_version": release.get("target_version"),
        "approved_by": approval.get("approved_by"),
        "approved_at": approval.get("approved_at"),
        "effective_from": release.get("effective_from"),
        "activation_condition": release.get("activation_condition"),
        "monitoring_window": release.get("monitoring_window"),
        "rollback_condition": release.get("rollback_condition"),
        "destination": release.get("destination"),
    }


def _terminal_decision_projection(proposal: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_id": str(proposal.get("proposal_id") or "unknown"),
        "occurred_at": proposal.get("generated_at"),
        "title": _proposal_title(proposal),
        "public_state": "not_proceeding",
        "decision_reason": proposal.get("supported_lesson") or "The proposal did not pass evidence review.",
        "qadam_changed": False,
        "change_summary": "Nothing changed",
        "affected_component": _affected_component(proposal),
        "version": None,
        "effective_from": None,
        "monitoring_result": None,
        "rollback_reason": proposal.get("rollback_reason"),
    }


def _integrated_decision_projection(record: dict[str, Any]) -> dict[str, Any]:
    approval = record.get("approval") if isinstance(record.get("approval"), dict) else {}
    return {
        "record_id": str(record.get("applied_version") or record.get("version") or record.get("proposal_id") or "unknown"),
        "occurred_at": record.get("effective_from") or record.get("generated_at"),
        "title": str(record.get("title") or record.get("change_hypothesis") or "Approved Qadam improvement"),
        "public_state": "integrated",
        "decision_reason": record.get("justification") or "The complete release record was approved for use.",
        "qadam_changed": True,
        "change_summary": record.get("expected_behavior"),
        "affected_component": record.get("affected_component") or record.get("target_stage") or "Qadam system",
        "version": record.get("applied_version") or record.get("version"),
        "effective_from": record.get("effective_from"),
        "monitoring_result": record.get("monitoring_result"),
        "monitoring_window": record.get("monitoring_window"),
        "rollback_condition": record.get("rollback_condition"),
        "approved_by": approval.get("approved_by"),
    }


def build_improvement_presentation(
    *,
    proposals: list[dict[str, Any]],
    applied_versions: list[dict[str, Any]],
    projection_available: bool = True,
    projection_stale: bool = False,
) -> dict[str, Any]:
    classified = [
        (
            classify_improvement_proposal(
                proposal,
                projection_available=projection_available,
                projection_stale=projection_stale,
            ),
            proposal,
        )
        for proposal in proposals
    ]
    scheduled = [_scheduled_projection(row) for state, row in classified if state == "scheduled"]
    under_evaluation = [
        _under_evaluation_projection(row)
        for state, row in classified
        if state == "under_evaluation"
    ]
    terminal = [
        _terminal_decision_projection(row)
        for state, row in classified
        if state == "not_proceeding"
    ]
    integrated = [
        _integrated_decision_projection(row)
        for row in applied_versions
        if _valid_integrated_version(row)
    ]
    rolled_back = [
        {
            **_terminal_decision_projection(row),
            "record_id": str(row.get("applied_version") or row.get("version") or row.get("proposal_id") or "unknown"),
            "title": str(row.get("title") or row.get("change_hypothesis") or "Rolled-back Qadam improvement"),
            "rollback_reason": row.get("rollback_reason") or row.get("decision_reason"),
            "version": row.get("applied_version") or row.get("version"),
        }
        for row in applied_versions
        if str(row.get("decision_state") or "").lower() == "rolled_back"
    ]
    decisions = sorted(
        [*terminal, *integrated, *rolled_back],
        key=lambda row: str(row.get("occurred_at") or ""),
        reverse=True,
    )
    counts = {
        "scheduled_integration_count": len(scheduled),
        "under_evaluation_count": len(under_evaluation),
        "integrated_count": len(integrated),
        "decision_history_count": len(decisions),
    }
    if not projection_available or projection_stale:
        state = "status_unavailable"
        tone = "unavailable"
        headline = "Improvement status is temporarily unavailable"
        summary = (
            "Qadam cannot confirm the current improvement roadmap because the public projection is missing or outside its freshness policy. "
            "Last known records remain read-only, and no scheduled, integrated, or unchanged-system conclusion should be inferred until the projection refreshes."
        )
    elif scheduled:
        state = "version_scheduled"
        tone = "scheduled"
        headline = "A new Qadam version is scheduled"
        summary = (
            "Qadam has a fully approved, versioned improvement with a recorded destination, activation rule, monitoring window, and rollback condition. "
            "Other proposals remain separate until their evidence and release records are complete. "
            "The scheduled change is not treated as successful until its monitoring period confirms the expected behavior."
        )
    elif under_evaluation:
        state = "nothing_scheduled_evidence_gathering"
        tone = "pending"
        headline = "Nothing is currently scheduled to change"
        summary = (
            "Qadam is still gathering evidence for an operational improvement, while any earlier closed proposal remains part of the decision history. "
            "Nothing is ready to enter Qadam or approved for use, and no integrated version is currently exported. "
            "Historical testing and real-time no-order observation must be completed before review, so Qadam will continue using its current behavior."
        )
    elif integrated:
        state = "no_further_change_scheduled"
        tone = "integrated"
        headline = "No further change is scheduled"
        summary = (
            "Qadam has an approved version already in use, but no additional change is scheduled. "
            "The integrated behavior remains subject to its recorded monitoring and rollback rules. "
            "New lessons must still complete the same historical, forward-observation, and approval process before another version can be prepared."
        )
    else:
        state = "no_active_proposal"
        tone = "neutral"
        headline = "No improvement proposal is currently active"
        summary = (
            "Qadam has no active proposal and no approved future change in the current projection. "
            "Previous decisions remain available for audit, while current strategy and system behavior remain unchanged. "
            "A new proposal can begin only when Results & Lessons supplies a supported, attributable lesson."
        )
    next_version = {
        "state": "scheduled_changes" if scheduled else "no_scheduled_changes",
        "headline": "A new Qadam version is scheduled" if scheduled else "No approved changes are scheduled",
        "summary": (
            "The approved release records below define the next operating version."
            if scheduled
            else "Qadam's next operating cycle will continue using the current version."
        ),
        "scheduled_changes": scheduled,
    }
    next_cycle = {
        "state": "scheduled_change" if scheduled else ("integrated_version" if integrated else "unchanged"),
        "headline": (
            "Next cycle: Scheduled change"
            if scheduled
            else ("Next cycle: Continue the integrated version" if integrated else "Next cycle: No change")
        ),
        "summary": (
            "The next cycle will activate only the approved release record shown above and monitor its rollback conditions."
            if scheduled
            else (
                "The next cycle will continue using the approved version already in use and keep monitoring it."
                if integrated
                else "No approved improvement exists, so Qadam will continue using its current strategy and system versions."
            )
        ),
        "destination": {"module_id": "fund", "view_id": "portfolio"},
    }
    return {
        "presentation_contract_version": IMPROVEMENTS_PRESENTATION_VERSION,
        "page_copy": dict(IMPROVEMENTS_PAGE_COPY),
        "immediate_answer": {
            "state": state,
            "tone": tone,
            "eyebrow": "Integration status",
            "headline": headline,
            "summary": summary,
            "projection_available": projection_available,
            "projection_stale": projection_stale,
            "generated_from": dict(counts),
        },
        "presentation_counts": counts,
        "metric_groups": [
            {
                "id": "scheduled",
                "label": "Scheduled for integration",
                "subtitle": "Approved future changes",
                "binding": "scheduled_integration_count",
                "value": counts["scheduled_integration_count"] if projection_available and not projection_stale else None,
            },
            {
                "id": "under_evaluation",
                "label": "Still under evaluation",
                "subtitle": "Possible future improvements",
                "binding": "under_evaluation_count",
                "value": counts["under_evaluation_count"] if projection_available and not projection_stale else None,
            },
            {
                "id": "integrated",
                "label": "Already integrated",
                "subtitle": "Approved versions now in use",
                "binding": "integrated_count",
                "value": counts["integrated_count"] if projection_available and not projection_stale else None,
            },
        ],
        "next_version": next_version,
        "repositories": {
            "possible_future_improvements": {
                "label": "Possible Future Improvements",
                "summary": "Changes Qadam is investigating but has not approved or scheduled.",
                "count": len(under_evaluation),
                "records": under_evaluation,
            },
            "previous_decisions": {
                "label": "Previous Improvement Decisions",
                "summary": "Changes Qadam integrated, rejected, retired, held closed, or rolled back.",
                "count": len(decisions),
                "records": decisions,
            },
        },
        "next_cycle": next_cycle,
    }


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
    release_record = {
        "target_version": champion.get("target_version") or champion.get("release_version"),
        "affected_component": champion.get("affected_component"),
        "destination": champion.get("destination"),
        "effective_from": champion.get("effective_from"),
        "activation_condition": champion.get("activation_condition"),
        "expected_behavior": champion.get("expected_behavior"),
        "monitoring_window": champion.get("monitoring_window"),
        "rollback_condition": champion.get("rollback_condition"),
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
        "release_record": release_record,
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
    learning_backtest_gap = read_json(
        runtime / "qadam_learning_backtest_dashboard_summary.json"
    )
    applied_version_records = read_jsonl(runtime / APPLIED_VERSIONS_ARTIFACT)
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
    applied = [
        record
        for record in applied_version_records
        if str(record.get("decision_state") or "").lower() == "applied"
    ]
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
    required_projection_paths = (
        runtime / ATTRIBUTION_ARTIFACT,
        runtime / BACKFILL_ARTIFACT,
        runtime / BACKTEST_SUMMARY_ARTIFACT,
        runtime / SHADOW_STATE_ARTIFACT,
    )
    projection_available = all(path.exists() for path in required_projection_paths)
    presentation = build_improvement_presentation(
        proposals=proposals,
        applied_versions=applied_version_records,
        projection_available=projection_available,
        projection_stale=False,
    )
    counts = {
        "attribution_record_count": len(attribution),
        "excluded_mirror_record_count": excluded_mirror_count,
        "proposal_record_count": len(proposals),
        "active_candidate_count": len(active),
        "ready_for_review_count": len(ready),
        "applied_version_count": len(applied),
        "decision_state_counts": dict(sorted(state_counts.items())),
        "validated_edge_count": len([edge for edge in edges if edge.get("edge_state") == "validated"]),
        **presentation["presentation_counts"],
    }
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
        "counts": counts,
        "pipeline_steps": [step["label"] for step in LEARNING_LOOP_STEPS],
        "proposals": proposals,
        "active_candidates": active,
        "rejected_or_held": [proposal for proposal in proposals if proposal["decision_state"] in TERMINAL_STATES],
        "applied_versions": applied,
        "projection_state": {
            "available": projection_available,
            "stale": False,
            "required_source_count": len(required_projection_paths),
            "available_source_count": len([path for path in required_projection_paths if path.exists()]),
        },
        **presentation,
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
        "historical_research_program": learning_backtest_gap,
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
    if model.get("presentation_contract_version") != IMPROVEMENTS_PRESENTATION_VERSION:
        errors.append("improvement_presentation_contract_missing")
    presentation_counts = model.get("presentation_counts")
    presentation_counts = presentation_counts if isinstance(presentation_counts, dict) else {}
    for key in (
        "scheduled_integration_count",
        "under_evaluation_count",
        "integrated_count",
        "decision_history_count",
    ):
        if counts.get(key) != presentation_counts.get(key):
            errors.append(f"improvement_presentation_count_mismatch:{key}")
    metric_groups = model.get("metric_groups")
    metric_groups = metric_groups if isinstance(metric_groups, list) else []
    expected_metrics = (
        ("scheduled", "scheduled_integration_count"),
        ("under_evaluation", "under_evaluation_count"),
        ("integrated", "integrated_count"),
    )
    if len(metric_groups) != len(expected_metrics):
        errors.append("improvement_primary_metric_count_invalid")
    if [(row.get("id"), row.get("binding")) for row in metric_groups] != list(expected_metrics):
        errors.append("improvement_primary_metric_binding_invalid")
    projection = model.get("projection_state")
    projection = projection if isinstance(projection, dict) else {}
    available = projection.get("available") is True and projection.get("stale") is not True
    for row in metric_groups:
        binding = row.get("binding")
        expected_value = _integer_or_none(counts.get(binding)) if available else None
        if row.get("value") != expected_value:
            errors.append("improvement_primary_metric_value_mismatch")
    repositories = model.get("repositories")
    repositories = repositories if isinstance(repositories, dict) else {}
    if set(repositories) != {"possible_future_improvements", "previous_decisions"}:
        errors.append("improvement_repository_contract_invalid")
    future_repository = repositories.get("possible_future_improvements")
    future_repository = future_repository if isinstance(future_repository, dict) else {}
    future_records = future_repository.get("records")
    future_records = future_records if isinstance(future_records, list) else []
    if future_repository.get("count") != len(future_records):
        errors.append("improvement_future_repository_count_mismatch")
    if counts.get("under_evaluation_count") != len(future_records):
        errors.append("improvement_future_metric_repository_mismatch")
    if any(record.get("public_state") != "under_evaluation" for record in future_records):
        errors.append("improvement_future_repository_contains_wrong_state")
    if any(not record.get("source_lesson_id") for record in future_records):
        errors.append("improvement_future_record_missing_lesson_lineage")
    if any(record.get("expected_benefit_is_measured") is not False for record in future_records):
        errors.append("improvement_expected_benefit_presented_as_measured")
    decision_repository = repositories.get("previous_decisions")
    decision_repository = decision_repository if isinstance(decision_repository, dict) else {}
    decision_records = decision_repository.get("records")
    decision_records = decision_records if isinstance(decision_records, list) else []
    if decision_repository.get("count") != len(decision_records):
        errors.append("improvement_decision_repository_count_mismatch")
    if counts.get("decision_history_count") != len(decision_records):
        errors.append("improvement_decision_metric_repository_mismatch")
    scheduled_records = model.get("next_version", {}).get("scheduled_changes", [])
    scheduled_records = scheduled_records if isinstance(scheduled_records, list) else []
    if counts.get("scheduled_integration_count") != len(scheduled_records):
        errors.append("improvement_scheduled_count_mismatch")
    proposal_index = {
        str(proposal.get("proposal_id")): proposal
        for proposal in proposals
        if proposal.get("proposal_id")
    }
    for record in scheduled_records:
        proposal = proposal_index.get(str(record.get("proposal_id")))
        if proposal is None or not is_scheduled_improvement(proposal):
            errors.append("improvement_scheduled_without_complete_release_record")
        if str(proposal.get("decision_state") if proposal else "") == "ready_for_review":
            errors.append("improvement_ready_for_review_presented_as_scheduled")
    valid_integrated = [record for record in model.get("applied_versions", []) if _valid_integrated_version(record)]
    if counts.get("integrated_count") != len(valid_integrated):
        errors.append("improvement_integrated_count_mismatch")
    answer = model.get("immediate_answer")
    answer = answer if isinstance(answer, dict) else {}
    if not available:
        expected_answer_state = "status_unavailable"
    elif counts.get("scheduled_integration_count", 0) > 0:
        expected_answer_state = "version_scheduled"
    elif counts.get("under_evaluation_count", 0) > 0:
        expected_answer_state = "nothing_scheduled_evidence_gathering"
    elif counts.get("integrated_count", 0) > 0:
        expected_answer_state = "no_further_change_scheduled"
    else:
        expected_answer_state = "no_active_proposal"
    if answer.get("state") != expected_answer_state:
        errors.append("improvement_immediate_answer_contradicts_records")
    next_cycle = model.get("next_cycle")
    next_cycle = next_cycle if isinstance(next_cycle, dict) else {}
    expected_next_cycle = (
        "scheduled_change"
        if counts.get("scheduled_integration_count", 0) > 0
        else ("integrated_version" if counts.get("integrated_count", 0) > 0 else "unchanged")
    )
    if next_cycle.get("state") != expected_next_cycle:
        errors.append("improvement_next_cycle_contradicts_records")
    destination = next_cycle.get("destination") if isinstance(next_cycle.get("destination"), dict) else {}
    if (destination.get("module_id"), destination.get("view_id")) != ("fund", "portfolio"):
        errors.append("improvement_next_cycle_destination_invalid")
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
