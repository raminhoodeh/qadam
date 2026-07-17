from __future__ import annotations

from copy import deepcopy

from orchestrator.qadam_improvement_pipeline_view_model import (
    IMPROVEMENTS_PRESENTATION_VERSION,
    build_improvement_presentation,
    classify_improvement_proposal,
    is_scheduled_improvement,
    validate_improvement_pipeline_view_model,
)
from orchestrator.qadam_learning_loop_contract import build_learning_loop_overview
from orchestrator.qadam_operator_ready_common import authority_flags, validate_authority


def _proposal(
    proposal_id: str = "proposal-1",
    *,
    state: str = "needs_data",
    change_type: str = "operations",
    historical_state: str = "not_started",
    forward_state: str = "not_started_no_eligible_hypothesis",
    release_record: dict | None = None,
    approval: dict | None = None,
) -> dict:
    return {
        "proposal_id": proposal_id,
        "generated_at": "2026-07-17T08:00:00+00:00",
        "lesson_ids": [f"lesson-{proposal_id}"],
        "change_type": change_type,
        "target_stage": "system" if change_type == "operations" else "observe",
        "supported_lesson": "Required operating evidence remained incomplete.",
        "change_hypothesis": "Complete the missing evidence before reassessing the guarded release.",
        "expected_benefit": "Improve evidence quality without weakening the safety boundary.",
        "historical_test": {
            "status": historical_state,
            "empirical_claim_allowed": historical_state == "complete",
        },
        "forward_shadow_test": {
            "status": forward_state,
            "promotion_ready": forward_state == "complete",
        },
        "decision_state": state,
        "next_action": "Complete historical testing and real-time no-order observation.",
        "review": {
            "status": "ready_for_review" if state == "ready_for_review" else "waiting_for_evidence",
            "ready": state == "ready_for_review",
        },
        "approval": approval or {"approved": False, "approved_by": None, "approved_at": None},
        "release_record": release_record or {
            "target_version": None,
            "affected_component": None,
            "destination": None,
            "effective_from": None,
            "activation_condition": None,
            "expected_behavior": None,
            "monitoring_window": None,
            "rollback_condition": None,
        },
        "applied_version_state": {"status": "not_applied", "version": None, "effective_from": None},
        "stage1_handoff": {"state": "inert_until_applied", "target_stage": "system", "applied_version": None},
        "source_record": {"origin_class": "qadam_runtime", "outcome_type": "operational_release_blocked"},
        "authority": authority_flags(),
    }


def _complete_release() -> dict:
    return {
        "target_version": "qadam-ops-v2",
        "affected_component": "Operational evidence readiness",
        "destination": {"module_id": "system", "view_id": "overview"},
        "effective_from": "2026-07-20T00:00:00+00:00",
        "activation_condition": None,
        "expected_behavior": "Require complete provider evidence before release review.",
        "monitoring_window": "30 real calendar days",
        "rollback_condition": "Revert if evidence completeness deteriorates.",
    }


def _approval() -> dict:
    return {
        "approved": True,
        "approved_by": "Fund Manager",
        "approved_at": "2026-07-17T09:00:00+00:00",
    }


def _applied_version(*, state: str = "applied") -> dict:
    return {
        "decision_state": state,
        "applied_version": "qadam-ops-v1",
        "generated_at": "2026-07-16T08:00:00+00:00",
        "effective_from": "2026-07-16T09:00:00+00:00",
        "expected_behavior": "Require a complete operating evidence record.",
        "monitoring_window": "30 real calendar days",
        "rollback_condition": "Revert if evidence quality deteriorates.",
        "rollback_reason": "Evidence quality deteriorated." if state == "rolled_back" else None,
        "approval": _approval(),
        "affected_component": "Operational evidence readiness",
    }


def _model(
    proposals: list[dict],
    applied_versions: list[dict] | None = None,
    *,
    available: bool = True,
    stale: bool = False,
) -> dict:
    versions = applied_versions or []
    presentation = build_improvement_presentation(
        proposals=proposals,
        applied_versions=versions,
        projection_available=available,
        projection_stale=stale,
    )
    active = [row for row in proposals if row["decision_state"] not in {"rejected", "retired", "rolled_back"}]
    applied = [row for row in versions if row.get("decision_state") == "applied"]
    counts = {
        "attribution_record_count": len(proposals),
        "excluded_mirror_record_count": 42,
        "proposal_record_count": len(proposals),
        "active_candidate_count": len(active),
        "ready_for_review_count": len([row for row in proposals if row["decision_state"] == "ready_for_review"]),
        "applied_version_count": len(applied),
        "decision_state_counts": {},
        "validated_edge_count": 0,
        **presentation["presentation_counts"],
    }
    return {
        "schema_version": "qadam_improvement_pipeline_dashboard.v2",
        "artifact_type": "qadam_improvement_pipeline_dashboard",
        "generated_at": "2026-07-17T10:00:00+00:00",
        "counts": counts,
        "proposals": proposals,
        "active_candidates": active,
        "rejected_or_held": [row for row in proposals if row["decision_state"] in {"rejected", "retired", "rolled_back"}],
        "applied_versions": applied,
        "projection_state": {"available": available, "stale": stale},
        "loop_overview": build_learning_loop_overview("improvements"),
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "paper_only": True,
        "authority": authority_flags(),
        **presentation,
    }


def test_current_state_is_zero_scheduled_one_under_evaluation_zero_integrated() -> None:
    model = _model([_proposal(), _proposal("rejected", state="rejected", change_type="data_repair")])
    assert validate_improvement_pipeline_view_model(model) == []
    assert model["presentation_contract_version"] == IMPROVEMENTS_PRESENTATION_VERSION
    assert model["immediate_answer"]["headline"] == "Nothing is currently scheduled to change"
    assert [row["value"] for row in model["metric_groups"]] == [0, 1, 0]
    assert model["repositories"]["possible_future_improvements"]["count"] == 1
    assert model["repositories"]["previous_decisions"]["count"] == 1


def test_no_proposals_and_no_versions_has_no_active_proposal() -> None:
    presentation = build_improvement_presentation(proposals=[], applied_versions=[])
    assert presentation["immediate_answer"]["state"] == "no_active_proposal"


def test_needs_data_and_testing_remain_under_evaluation() -> None:
    assert classify_improvement_proposal(_proposal(state="needs_data")) == "under_evaluation"
    assert classify_improvement_proposal(_proposal(state="testing", historical_state="testing")) == "under_evaluation"


def test_ready_for_review_is_not_scheduled() -> None:
    proposal = _proposal(
        state="ready_for_review",
        historical_state="complete",
        forward_state="complete",
    )
    assert is_scheduled_improvement(proposal) is False
    assert classify_improvement_proposal(proposal) == "under_evaluation"


def test_approved_but_incomplete_release_record_fails_closed() -> None:
    proposal = _proposal(state="approved", approval=_approval())
    assert is_scheduled_improvement(proposal) is False
    assert classify_improvement_proposal(proposal) == "under_evaluation"


def test_complete_approved_release_is_scheduled() -> None:
    proposal = _proposal(
        state="approved",
        historical_state="complete",
        forward_state="complete",
        release_record=_complete_release(),
        approval=_approval(),
    )
    model = _model([proposal])
    assert validate_improvement_pipeline_view_model(model) == []
    assert is_scheduled_improvement(proposal) is True
    assert model["counts"]["scheduled_integration_count"] == 1
    assert model["next_version"]["scheduled_changes"][0]["target_version"] == "qadam-ops-v2"
    assert model["next_cycle"]["state"] == "scheduled_change"


def test_applied_version_is_integrated_not_scheduled() -> None:
    model = _model([], [_applied_version()])
    assert validate_improvement_pipeline_view_model(model) == []
    assert model["counts"]["scheduled_integration_count"] == 0
    assert model["counts"]["integrated_count"] == 1
    assert model["immediate_answer"]["headline"] == "No further change is scheduled"
    assert model["next_cycle"]["state"] == "integrated_version"


def test_rejected_proposal_appears_only_in_decision_history() -> None:
    model = _model([_proposal(state="rejected")])
    assert model["repositories"]["possible_future_improvements"]["records"] == []
    decision = model["repositories"]["previous_decisions"]["records"][0]
    assert decision["public_state"] == "not_proceeding"
    assert decision["change_summary"] == "Nothing changed"


def test_rolled_back_version_is_not_proceeding_with_reason() -> None:
    presentation = build_improvement_presentation(
        proposals=[],
        applied_versions=[_applied_version(state="rolled_back")],
    )
    decision = presentation["repositories"]["previous_decisions"]["records"][0]
    assert decision["public_state"] == "not_proceeding"
    assert decision["rollback_reason"] == "Evidence quality deteriorated."


def test_stale_projection_does_not_publish_false_zero_metrics() -> None:
    presentation = build_improvement_presentation(
        proposals=[_proposal()],
        applied_versions=[],
        projection_stale=True,
    )
    assert presentation["immediate_answer"]["state"] == "status_unavailable"
    assert [row["value"] for row in presentation["metric_groups"]] == [None, None, None]


def test_expected_benefit_is_never_presented_as_measured() -> None:
    model = _model([_proposal()])
    future = model["repositories"]["possible_future_improvements"]["records"][0]
    assert future["expected_benefit_is_measured"] is False
    unsafe = deepcopy(model)
    unsafe["repositories"]["possible_future_improvements"]["records"][0]["expected_benefit_is_measured"] = True
    assert "improvement_expected_benefit_presented_as_measured" in validate_improvement_pipeline_view_model(unsafe)


def test_every_active_proposal_retains_results_and_lessons_lineage() -> None:
    model = _model([_proposal()])
    assert model["repositories"]["possible_future_improvements"]["records"][0]["source_lesson_id"]
    unsafe = deepcopy(model)
    unsafe["repositories"]["possible_future_improvements"]["records"][0]["source_lesson_id"] = None
    assert "improvement_future_record_missing_lesson_lineage" in validate_improvement_pipeline_view_model(unsafe)


def test_next_cycle_matches_records_and_returns_to_fund_overview() -> None:
    model = _model([_proposal()])
    assert model["next_cycle"]["state"] == "unchanged"
    assert model["next_cycle"]["destination"] == {"module_id": "fund", "view_id": "portfolio"}


def test_public_authority_remains_inert() -> None:
    model = _model([_proposal()])
    assert validate_authority(model["authority"], prefix="test") == []
    assert model["read_only"] is True
    assert model["command_disabled"] is True
    assert all(row["stage1_handoff"]["state"] == "inert_until_applied" for row in model["proposals"])


def test_scheduling_rejects_unsafe_authority() -> None:
    proposal = _proposal(
        state="approved",
        historical_state="complete",
        forward_state="complete",
        release_record=_complete_release(),
        approval=_approval(),
    )
    proposal["authority"] = authority_flags(paper_order_allowed=True)
    assert is_scheduled_improvement(proposal) is False
