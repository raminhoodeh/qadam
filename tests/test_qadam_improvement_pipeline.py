from __future__ import annotations

from copy import deepcopy

from orchestrator.qadam_improvement_pipeline_view_model import (
    build_improvement_pipeline_view_model,
    exclude_mirror_only_attribution_records,
    validate_improvement_pipeline_view_model,
)


def test_improvement_pipeline_excludes_mirrors_and_keeps_proposals_inert() -> None:
    model = build_improvement_pipeline_view_model(
        generated_at="2026-07-12T00:00:00+00:00"
    )
    assert validate_improvement_pipeline_view_model(model) == []
    assert model["counts"]["excluded_mirror_record_count"] >= 0
    assert all(
        proposal["source_record"]["origin_class"]
        != "mirror_only_historical_record"
        for proposal in model["proposals"]
    )
    assert all(
        proposal["stage1_handoff"]["state"] == "inert_until_applied"
        for proposal in model["proposals"]
    )
    assert model["loop_overview"]["page"] == "improvements"
    assert model["loop_overview"]["page_stage_ids"] == [
        "proposed_improvement",
        "historical_test",
        "forward_observation",
        "review",
        "applied_version",
        "next_observe_cycle",
    ]
    assert model["pipeline_steps"][0] == "Outcome or research event"
    assert model["pipeline_steps"][-1] == "Next Observe cycle"
    assert all(proposal["supported_lesson"] for proposal in model["proposals"])
    assert all(proposal["review"]["status"] for proposal in model["proposals"])
    assert all(proposal["applied_version_state"]["status"] for proposal in model["proposals"])


def test_improvement_pipeline_explicitly_excludes_mirror_only_records() -> None:
    eligible, excluded_count = exclude_mirror_only_attribution_records(
        [
            {"attribution_id": "current", "origin_class": "qadam_runtime"},
            {
                "attribution_id": "mirror",
                "origin_class": "mirror_only_historical_record",
            },
        ]
    )

    assert [record["attribution_id"] for record in eligible] == ["current"]
    assert excluded_count == 1


def test_improvement_cannot_be_ready_without_history_and_shadow(monkeypatch) -> None:
    from orchestrator import qadam_improvement_pipeline_view_model as module
    # This negative contract is independent of whether production currently has proposals.
    monkeypatch.setattr(module, "read_jsonl", lambda path: [
        {"attribution_id": "fixture:lesson", "origin_class": "qadam_runtime"}
    ] if path.name == module.ATTRIBUTION_ARTIFACT else [])
    monkeypatch.setattr(module, "read_json", lambda path: {})
    model = build_improvement_pipeline_view_model(
        generated_at="2026-07-12T00:00:00+00:00"
    )
    assert model["proposals"]
    unsafe = deepcopy(model)
    unsafe["proposals"][0]["decision_state"] = "ready_for_review"
    unsafe["proposals"][0]["historical_test"]["empirical_claim_allowed"] = False
    unsafe["proposals"][0]["forward_shadow_test"]["promotion_ready"] = False
    errors = validate_improvement_pipeline_view_model(unsafe)
    assert "improvement_ready_without_historical_evidence" in errors
    assert "improvement_ready_without_forward_shadow" in errors
