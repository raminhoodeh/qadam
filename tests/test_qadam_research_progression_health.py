from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from orchestrator.config import Settings
from orchestrator.qadam_research_progression_health import (
    build_research_progression_health,
)


def _settings(tmp_path: Path) -> Settings:
    return replace(Settings.from_env(), runtime_dir=str(tmp_path))


def _write(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def test_research_progression_separates_waiting_from_failure(tmp_path: Path) -> None:
    _write(
        tmp_path / "qadam_source_capability_registry.json",
        {
            "material_fingerprint": "sources:1",
            "counts": {
                "catalogue": 41,
                "fresh_current_confirmation": 15,
                "classified_limit": 10,
                "active_strategy_source_failure": 2,
            },
            "strategy_source_coverage": [],
        },
    )
    _write(
        tmp_path / "qadam_pattern_score_v3.json",
        {
            "record_count": 1,
            "input_material_fingerprint": "scores:1",
            "confidence_state_counts": {"score_ready_for_tape": 1},
        },
    )
    _write(
        tmp_path / "qadam_pattern_score_v3_checks.json",
        {
            "material_change_detected": False,
            "last_material_change_at": "2026-01-01T00:00:00+00:00",
        },
    )
    _write(
        tmp_path / "qadam_pattern_score_v3_records.jsonl",
        {
            "score_id": "score:1",
            "strategy_label": "Test relationship",
            "instrument": "SPY",
            "raw_pattern_score": 0.64,
            "confidence_state": "score_ready_for_tape",
            "permitted_next_action": "append_to_historical_score_tape_research_only",
            "negative_control": False,
        },
    )
    _write(
        tmp_path / "qadam_pattern_score_tape_checks.json",
        {"score_tape_row_count": 100},
    )
    _write(tmp_path / "qadam_forward_labels_checks.json", {"label_count": 90})
    _write(
        tmp_path / "qadam_forward_shadow_checks.json",
        {"decision_count": 3, "outcome_count": 2},
    )
    _write(
        tmp_path / "qadam_edge_registry_summary.json",
        {"validated_edge_count": 0},
    )
    _write(
        tmp_path / "qadam_unattended_observation_readiness.json",
        {"observation_ready": True},
    )

    payload = build_research_progression_health(
        _settings(tmp_path), generated_at="2026-01-02T00:00:00+00:00"
    )

    assert payload["status"] == "progressed_materially"
    assert payload["source_truth"]["catalogue_count"] == 41
    assert payload["pattern_truth"]["material_change_detected"] is False
    reasons = {row["reason"] for row in payload["exact_stop_reasons"]}
    assert "no_new_material_evidence" in reasons
    assert "no_relationship_survived_holdout_costs_and_stability" in reasons
    assert payload["paper_order_created_count"] == 0


def test_current_operator_health_overrides_stale_legacy_readiness(tmp_path: Path) -> None:
    _write(
        tmp_path / "qadam_unattended_observation_readiness.json",
        {
            "generated_at": "2025-01-01T00:00:00+00:00",
            "observation_ready": False,
        },
    )
    _write(
        tmp_path / "qadam_operator_service_status.json",
        {
            "generated_at": "2026-01-02T00:00:00+00:00",
            "operational_ready": True,
            "observation_ready": True,
            "liveness": {"process_running": True},
        },
    )
    _write(tmp_path / "qadam_operator_circuit_breakers.json", {"open_circuit_count": 0})
    _write(tmp_path / "qadam_operator_repair_queue.json", {"open_request_count": 0})

    payload = build_research_progression_health(
        _settings(tmp_path), generated_at="2026-01-02T00:01:00+00:00"
    )

    assert payload["status"] == "progressed_materially"
    assert payload["observation_ready"] is True
    assert payload["operator_truth"]["blockers"] == []


def test_current_open_circuit_is_an_operational_blocker(tmp_path: Path) -> None:
    _write(
        tmp_path / "qadam_operator_service_status.json",
        {
            "generated_at": "2026-01-02T00:00:00+00:00",
            "operational_ready": True,
            "observation_ready": False,
            "liveness": {"process_running": True},
        },
    )
    _write(tmp_path / "qadam_operator_circuit_breakers.json", {"open_circuit_count": 1})
    _write(tmp_path / "qadam_operator_repair_queue.json", {"open_request_count": 1})

    payload = build_research_progression_health(
        _settings(tmp_path), generated_at="2026-01-02T00:01:00+00:00"
    )

    assert payload["status"] == "blocked_operationally"
    assert "operator_circuit_open" in payload["operator_truth"]["blockers"]
    assert "operator_repair_open" in payload["operator_truth"]["blockers"]
