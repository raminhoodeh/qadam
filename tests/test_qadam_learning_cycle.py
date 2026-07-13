from __future__ import annotations

from copy import deepcopy

from orchestrator.qadam_learning_cycle_view_model import (
    build_learning_cycle_view_model,
    validate_learning_cycle_view_model,
)


def test_learning_cycle_separates_reference_history_from_qadam_learning() -> None:
    model = build_learning_cycle_view_model(generated_at="2026-07-12T00:00:00+00:00")
    assert validate_learning_cycle_view_model(model) == []
    assert model["read_only"] is True
    assert model["command_disabled"] is True
    assert all(record["learnable"] is False for record in model["reference_records"])
    assert all(record["proof_eligible"] is False for record in model["reference_records"])
    assert model["counts"]["mirror_reference_count"] == len(model["reference_records"])
    overview = model["loop_overview"]
    assert overview["page"] == "results"
    assert overview["page_stage_ids"] == [
        "outcome_or_research_event",
        "supported_lesson",
    ]
    assert [step["label"] for step in overview["steps"]] == [
        "Outcome or research event",
        "Supported lesson",
        "Proposed improvement",
        "Historical test",
        "Forward observation",
        "Review",
        "Applied version",
        "Next Observe cycle",
    ]


def test_learning_cycle_rejects_reference_record_as_learning_or_proof() -> None:
    model = build_learning_cycle_view_model(generated_at="2026-07-12T00:00:00+00:00")
    assert model["reference_records"]
    unsafe = deepcopy(model)
    reference_id = unsafe["reference_records"][0]["record_id"]
    for record in unsafe["events"]:
        if record["record_id"] == reference_id:
            record["learnable"] = True
            record["proof_eligible"] = True
            break
    errors = validate_learning_cycle_view_model(unsafe)
    assert "learning_cycle_reference_record_marked_learnable" in errors
    assert "learning_cycle_reference_record_granted_proof" in errors
