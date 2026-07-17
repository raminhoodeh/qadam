from __future__ import annotations

from copy import deepcopy

from orchestrator.qadam_learning_cycle_view_model import (
    RESULTS_HANDOFF,
    RESULTS_PRESENTATION_VERSION,
    build_learning_immediate_answer,
    build_learning_presentation,
    validate_learning_cycle_view_model,
)
from orchestrator.qadam_learning_loop_contract import build_learning_loop_overview
from orchestrator.qadam_operator_ready_common import authority_flags, validate_authority


def _event(
    record_id: str,
    *,
    outcome_type: str,
    origin_class: str = "qadam_runtime",
    qadam_origin: bool = False,
    learnable: bool = True,
    reference_only: bool = False,
    proof_eligible: bool = False,
    generated_at: str = "2026-07-17T08:00:00+00:00",
    next_state: str = "needs_data",
) -> dict:
    return {
        "record_id": record_id,
        "generated_at": generated_at,
        "record_kind": "paper_outcome" if qadam_origin or reference_only else "system_defect",
        "outcome_type": outcome_type,
        "origin_class": origin_class,
        "qadam_origin": qadam_origin,
        "learnable": learnable,
        "reference_only": reference_only,
        "actual_outcome": {"summary": outcome_type.replace("_", " ").capitalize()},
        "lesson": {
            "summary": "Required evidence remains incomplete.",
            "supported": learnable,
        },
        "next_test": {"state": next_state, "route": {"module_id": "learn", "view_id": "improvements"}},
        "proof_eligible": proof_eligible,
        "authority": authority_flags(),
    }


def _counts(
    *,
    learning: int = 2,
    qadam_outcomes: int = 0,
    proof: int = 0,
    references: int = 42,
    awaiting: int = 1,
) -> dict:
    return {
        "attribution_record_count": learning + references,
        "qadam_origin_outcome_count": qadam_outcomes,
        "learnable_postmortem_count": qadam_outcomes,
        "learnable_event_count": learning,
        "mirror_reference_count": references,
        "proof_eligible_count": proof,
        "lesson_awaiting_test_count": awaiting,
        "record_kind_counts": {},
    }


def _current_fixture() -> dict:
    learning_events = [
        _event("research-stop", outcome_type="strategy_hypothesis_rejected", next_state="rejected"),
        _event(
            "operating-hold",
            outcome_type="operational_release_blocked",
            generated_at="2026-07-17T09:00:00+00:00",
        ),
    ]
    references = [
        _event(
            f"reference-{index}",
            outcome_type="mirror_only_historical_record",
            origin_class="mirror_only_historical_record",
            learnable=False,
            reference_only=True,
            generated_at=f"2026-07-16T{index % 24:02d}:00:00+00:00",
        )
        for index in range(42)
    ]
    counts = _counts()
    presentation = build_learning_presentation(
        counts=counts,
        learnable_outcomes=[],
        learning_events=learning_events,
        reference_records=references,
    )
    return {
        "schema_version": "qadam_learning_cycle_dashboard.v2",
        "artifact_type": "qadam_learning_cycle_dashboard",
        "generated_at": "2026-07-17T10:00:00+00:00",
        "counts": counts,
        "events": [*learning_events, *references],
        "learnable_outcomes": [],
        "learning_events": learning_events,
        "reference_records": references,
        "loop_overview": build_learning_loop_overview("results"),
        "projection_state": {"available": True, "stale": False},
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "paper_only": True,
        "authority": authority_flags(),
        **presentation,
    }


def test_current_state_exports_simple_truthful_contract() -> None:
    model = _current_fixture()
    assert validate_learning_cycle_view_model(model) == []
    assert model["presentation_contract_version"] == RESULTS_PRESENTATION_VERSION
    assert model["immediate_answer"]["headline"] == "Waiting for the first complete Qadam paper outcome"
    assert [metric["value"] for metric in model["metric_groups"]] == [2, 0, 42]
    assert len(model["metric_groups"]) == 3
    assert set(model["repositories"]) == {"learning_reviews", "reference_history"}
    assert model["repositories"]["learning_reviews"]["count"] == 2
    assert model["repositories"]["reference_history"]["count"] == 42


def test_no_learning_events_still_waits_for_attributable_outcome() -> None:
    answer = build_learning_immediate_answer(_counts(learning=0, references=0, awaiting=0))
    assert answer["state"] == "waiting_for_attributable_paper_outcome"


def test_attributable_outcome_without_proof_remains_under_review() -> None:
    answer = build_learning_immediate_answer(_counts(qadam_outcomes=1, proof=0))
    assert answer["headline"] == "Paper outcomes recorded; lessons still under review"


def test_verified_lesson_waiting_for_test_is_ready_for_testing() -> None:
    answer = build_learning_immediate_answer(_counts(qadam_outcomes=1, proof=1, awaiting=1))
    assert answer["headline"] == "Verified lessons are ready for testing"


def test_verified_lesson_without_pending_test_is_recorded() -> None:
    answer = build_learning_immediate_answer(_counts(qadam_outcomes=1, proof=1, awaiting=0))
    assert answer["headline"] == "Verified lessons recorded"


def test_unavailable_or_stale_projection_never_infers_zero() -> None:
    unavailable = build_learning_immediate_answer({}, projection_available=False)
    stale = build_learning_immediate_answer(_counts(), projection_stale=True)
    assert unavailable["state"] == "status_unavailable"
    assert stale["state"] == "status_unavailable"
    assert unavailable["generated_from"]["proof_eligible_count"] is None


def test_reference_history_remains_non_learnable_and_non_proof() -> None:
    model = _current_fixture()
    unsafe = deepcopy(model)
    unsafe["reference_records"][0]["learnable"] = True
    unsafe["reference_records"][0]["proof_eligible"] = True
    errors = validate_learning_cycle_view_model(unsafe)
    assert "learning_cycle_reference_record_marked_learnable" in errors
    assert "learning_cycle_reference_record_granted_proof" in errors


def test_projected_reference_history_cannot_gain_learning_authority() -> None:
    model = _current_fixture()
    unsafe = deepcopy(model)
    unsafe["repositories"]["reference_history"]["records"][0]["learnable"] = True
    unsafe["repositories"]["reference_history"]["records"][0]["proof_eligible"] = True
    errors = validate_learning_cycle_view_model(unsafe)
    assert "learning_cycle_projected_reference_marked_learnable" in errors
    assert "learning_cycle_projected_reference_granted_proof" in errors


def test_immediate_answer_cannot_contradict_counts() -> None:
    model = _current_fixture()
    unsafe = deepcopy(model)
    unsafe["immediate_answer"]["state"] = "verified_lessons_recorded"
    errors = validate_learning_cycle_view_model(unsafe)
    assert "learning_cycle_immediate_answer_contradicts_counts" in errors


def test_metric_bindings_are_exact_and_unique() -> None:
    model = _current_fixture()
    assert [(row["id"], row["binding"]) for row in model["metric_groups"]] == [
        ("learning_reviews", "learnable_event_count"),
        ("verified_lessons", "proof_eligible_count"),
        ("reference_history", "mirror_reference_count"),
    ]
    unsafe = deepcopy(model)
    unsafe["metric_groups"][0]["binding"] = "attribution_record_count"
    assert "learning_cycle_primary_metric_binding_invalid" in validate_learning_cycle_view_model(unsafe)


def test_public_authority_is_read_only_and_command_disabled() -> None:
    model = _current_fixture()
    assert validate_authority(model["authority"], prefix="test") == []
    assert model["read_only"] is True
    assert model["command_disabled"] is True
    assert model["paper_only"] is True


def test_handoff_is_locked_to_tests_and_improvements() -> None:
    model = _current_fixture()
    assert model["handoff"] == RESULTS_HANDOFF
    unsafe = deepcopy(model)
    unsafe["handoff"]["view_id"] = "orders"
    assert "learning_cycle_handoff_target_invalid" in validate_learning_cycle_view_model(unsafe)
