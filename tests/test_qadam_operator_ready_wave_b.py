from __future__ import annotations

import pytest

from orchestrator.qadam_dynamic_plan import PHASE_ORDER, program_status
from orchestrator.qadam_edge_registry import build_edge_record, build_edge_registry_state
from orchestrator.qadam_forward_labels import build_forward_label
from orchestrator.qadam_nonlinear_quantum_value import quantum_usefulness_score
from orchestrator.qadam_pattern_score_tape import build_score_tape_row
from orchestrator.qadam_pattern_score_v3 import (
    FORBIDDEN_LABEL_KEYS,
    _record_set_material_hash,
    build_pattern_score_bundle,
)
from orchestrator.qadam_statistical_backtest import (
    benjamini_hochberg,
    chronological_walk_forward_folds,
)
from orchestrator.qadam_wave_b_common import contains_forbidden_key, record_set_hash


def test_pattern_score_v3_is_deterministic_and_label_blind() -> None:
    generated_at = "2000-01-01T00:00:00+00:00"
    first = build_pattern_score_bundle(generated_at=generated_at)
    second = build_pattern_score_bundle(generated_at=generated_at)
    assert record_set_hash(first.records) == record_set_hash(second.records)
    assert first.records
    assert not any(contains_forbidden_key(record, FORBIDDEN_LABEL_KEYS) for record in first.records)
    assert all(record["score_is_probability"] is False for record in first.records)


def test_pattern_material_hash_ignores_refresh_timestamp() -> None:
    base = {
        "score_id": "score:test",
        "input_fingerprint": "input:test",
        "raw_pattern_score": 0.64,
        "confidence_state": "score_ready_for_tape",
        "missing_critical_features": [],
        "permitted_next_action": "append_to_historical_score_tape_research_only",
        "generated_at": "2026-01-01T00:00:00+00:00",
    }
    refreshed = {**base, "generated_at": "2026-01-01T00:05:00+00:00"}
    assert _record_set_material_hash([base]) == _record_set_material_hash([refreshed])


def test_score_tape_row_rejects_label_contamination() -> None:
    score = {
        "score_id": "score:test",
        "model_version": "model:test",
        "feature_set_version": "features:test",
        "strategy_family_id": "strategy:test",
        "instrument": "TEST",
        "direction_hypothesis": "up",
        "horizon_hypothesis": "1d_forward",
    }
    row = build_score_tape_row(
        score,
        {"source_trust": 0.8, "available_at": "2025-01-01T00:00:00+00:00"},
        scoring_as_of="2025-01-01T00:00:00+00:00",
    )
    assert row["label_columns_present"] is False
    with pytest.raises(ValueError, match="label"):
        build_score_tape_row(
            score,
            {"source_trust": 0.8, "forward_return": 0.2},
            scoring_as_of="2025-01-01T00:00:00+00:00",
        )


def test_forward_label_requires_time_after_score_and_retains_net_cost() -> None:
    score = {
        "score_id": "score:test",
        "scoring_as_of": "2025-01-01T00:00:00+00:00",
        "horizon_hypothesis": "1d_forward",
        "instrument": "TEST",
    }
    with pytest.raises(ValueError, match="outcome_not_after_score"):
        build_forward_label(
            score,
            price_before=100.0,
            price_after=101.0,
            outcome_available_at="2025-01-01T00:00:00+00:00",
            cost_bps=10.0,
        )
    label = build_forward_label(
        score,
        price_before=100.0,
        price_after=101.0,
        outcome_available_at="2025-01-02T00:00:00+00:00",
        cost_bps=10.0,
    )
    assert label["gross_return"] == 0.01
    assert label["net_return"] == 0.009
    assert label["score_created_before_label"] is True


def test_walk_forward_folds_are_chronological_purged_and_embargoed() -> None:
    folds = chronological_walk_forward_folds(160)
    assert folds
    for fold in folds:
        assert fold.train_end + fold.purge_size == fold.validation_start
        assert fold.validation_end + fold.embargo_size == fold.test_start
        assert fold.train_end < fold.validation_start < fold.test_start < fold.test_end


def test_false_discovery_adjustment_and_quantum_value_are_conservative() -> None:
    adjusted = benjamini_hochberg([0.001, 0.02, 0.8], alpha=0.05)
    assert adjusted[0]["significant"] is True
    assert adjusted[2]["significant"] is False
    assert quantum_usefulness_score(
        classical_holdout_metric=0.6,
        quantum_holdout_metric=0.6,
        complexity_penalty=0.1,
        latency_penalty=0.1,
        reliability=0.9,
    ) == 0.0
    assert quantum_usefulness_score(
        classical_holdout_metric=None,
        quantum_holdout_metric=0.7,
        complexity_penalty=0.0,
        latency_penalty=0.0,
        reliability=1.0,
    ) is None


def test_edge_creation_requires_adjusted_holdout_and_cost_gates() -> None:
    with pytest.raises(ValueError, match="validation_gates"):
        build_edge_record({"false_discovery_adjusted_state": "raw_positive"})
    result = {
        "false_discovery_adjusted_state": "validated",
        "untouched_holdout": True,
        "costs_included": True,
        "source_feature_definition": "source:test",
        "instrument": "TEST",
        "direction": "up",
        "horizon": "1d_forward",
        "regime": "all",
        "score_version": "score:v1",
        "label_version": "label:v1",
        "fold_ids": ["fold-001"],
        "dataset_hashes": {"scores": "abc", "labels": "def"},
        "backtest_run_id": "run:test",
    }
    edge = build_edge_record(result)
    assert edge["promotion_class"] == "validated_research_edge"
    assert edge["paper_candidate_created"] is False
    assert edge["order_created"] is False


def test_rejected_registry_has_no_fabricated_edge_and_wave_b_is_maturing(rejected_edge_fixture) -> None:
    state = build_edge_registry_state(rejected_edge_fixture)
    assert state["summary"]["edge_count"] == 0
    assert state["summary"]["edge_validated_certification_passed"] is False
    assert len(state["strategy_map"]["strategies"]) == 5
    phases = {phase: {"state": "not_started"} for phase in PHASE_ORDER}
    for phase in PHASE_ORDER[:8]:
        phases[phase]["state"] = "passed"
    for index in range(0, 11):
        phases[f"OR-{index}"]["state"] = "passed"
    phases["OR-3"]["state"] = "evidence_maturing"
    phases["OR-6"]["state"] = "evidence_maturing"
    phases["OR-7"]["state"] = "evidence_maturing"
    phases["OR-8"]["state"] = "evidence_maturing"
    phases["OR-9"]["state"] = "evidence_maturing"
    assert program_status(phases) == "wave_b_evidence_maturing"
