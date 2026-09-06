from __future__ import annotations

import json

import orchestrator.qadam_stage1_learning_input as stage1
from orchestrator.qadam_pattern_score_v3 import build_pattern_score_bundle


def _applied_version(version: str, *, approved: bool = True) -> dict:
    return {
        "proposal_id": f"proposal:{version}",
        "decision_state": "applied",
        "applied_version": version,
        "effective_from": "2026-07-12T00:00:00+00:00",
        "target_stage": "observe",
        "target": "source_trust_review",
        "expected_behavior": "Record the approved source review version in the next cycle.",
        "monitoring_window": "30_real_calendar_days",
        "rollback_condition": "Rollback if evidence quality deteriorates.",
        "approval": {
            "approved": approved,
            "approved_by": "operator:test",
            "approved_at": "2026-07-12T00:00:00+00:00",
        },
    }


def test_stage1_consumes_only_approved_applied_versions(tmp_path, monkeypatch) -> None:
    records = [
        _applied_version("learning:v1"),
        _applied_version("learning:unapproved", approved=False),
        {"decision_state": "needs_data", "proposed_version": "learning:proposal"},
    ]
    (tmp_path / stage1.APPLIED_VERSIONS_ARTIFACT).write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )
    monkeypatch.setattr(stage1, "runtime_dir", lambda _settings=None: tmp_path)
    model = stage1.build_stage1_learning_input(
        generated_at="2026-07-12T01:00:00+00:00",
        pipeline_override={"status": "improvement_evidence_maturing"},
    )
    assert stage1.validate_stage1_learning_input(model) == []
    assert model["applied_learning_version_ids"] == ["learning:v1"]
    assert model["applied_handoff_count"] == 1
    assert model["rejected_non_applied_record_count"] == 2
    assert model["handoffs"][0]["state"] == "applied_stage1_input"
    assert model["authority"]["policy_mutation_allowed"] is False


def test_stage1_rejects_unapproved_or_unversioned_handoff() -> None:
    model = stage1.build_stage1_learning_input(
        generated_at="2026-07-12T01:00:00+00:00",
        pipeline_override={"status": "improvement_evidence_maturing"},
    )
    model["handoffs"] = [
        {
            "applied_version": "learning:unsafe",
            "state": "applied_stage1_input",
            "target_stage": "observe",
            "effective_from": "2026-07-12T00:00:00+00:00",
            "approval": {"approved": False},
            "authority": stage1.authority_flags(),
        }
    ]
    model["applied_handoff_count"] = 1
    model["applied_learning_version_ids"] = ["learning:unsafe"]
    errors = stage1.validate_stage1_learning_input(model)
    assert "stage1_learning_unapproved_handoff" in errors


def test_pattern_score_records_stage1_learning_version_lineage(monkeypatch) -> None:
    from orchestrator import qadam_pattern_score_v3 as pattern
    stage1_input = stage1.build_stage1_learning_input(
        generated_at="2026-07-12T01:00:00+00:00"
    )
    read = pattern.read_json
    monkeypatch.setattr(pattern, "read_json", lambda path: stage1_input
                        if path.name == pattern.STAGE1_LEARNING_INPUT_ARTIFACT else read(path))
    bundle = build_pattern_score_bundle(generated_at="2026-07-12T01:00:00+00:00")
    assert bundle.records
    assert bundle.primary["applied_learning_version_ids"] == stage1_input[
        "applied_learning_version_ids"
    ]
    assert all(
        record["applied_learning_version_ids"]
        == stage1_input["applied_learning_version_ids"]
        for record in bundle.records
    )
    assert all(record["stage1_learning_input_version"] for record in bundle.records)
