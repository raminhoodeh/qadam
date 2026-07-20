from __future__ import annotations

from copy import deepcopy

import orchestrator.qadam_learning_cycle_view_model as learning_cycle_module
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


def test_learning_cycle_rejects_reference_record_as_learning_or_proof(monkeypatch) -> None:
    original_read_jsonl = learning_cycle_module.read_jsonl

    def read_jsonl_with_reference(path, *args, **kwargs):
        if path.name == learning_cycle_module.ATTRIBUTION_ARTIFACT:
            return [
                {
                    "attribution_id": "reference-only:test",
                    "generated_at": "2026-07-12T00:00:00+00:00",
                    "origin_class": "mirror_only_historical_record",
                    "outcome_type": "mirror_trade_closed",
                    "proof_credit_granted": False,
                }
            ]
        return original_read_jsonl(path, *args, **kwargs)

    monkeypatch.setattr(learning_cycle_module, "read_jsonl", read_jsonl_with_reference)
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
