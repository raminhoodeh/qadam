from __future__ import annotations

from copy import deepcopy
import json

import pytest

import orchestrator.qadam_pattern_score_tape as score_tape
from orchestrator.qadam_pattern_score_tape import (
    FORBIDDEN_TAPE_KEYS,
    _build_historical_score_row,
    historical_template_id,
    historical_scoring_input,
    pinned_score_tape_inputs,
    write_score_tape_partition,
)
from orchestrator.qadam_wave_b_common import contains_forbidden_key


def _alignment() -> dict[str, object]:
    return {
        "alignment_record_id": "alignment:test",
        "relationship_id": "relationship:test",
        "source_key": "stock_act",
        "instrument": "LMT",
        "mapping_class": "causal_strategy_mapping",
        "negative_control": False,
        "source_available_at": "2025-01-02T00:00:00+00:00",
        "decision_at": "2025-01-03T00:00:00+00:00",
        "point_in_time_safe": True,
        "score_before_label_boundary": True,
        "future_label_values_included": False,
        "available_horizons": ["1d_forward", "5d_forward"],
        "future_horizon_availability": {
            "1d_forward": "2025-01-04T00:00:00+00:00",
            "5d_forward": "2025-01-10T00:00:00+00:00",
        },
        "feature_snapshot": {
            "source_event_count": 2,
            "source_numeric_feature_means": {"filing_count": 2.0},
            "source_record_type_counts": {"filing": 2},
            "first_event_at": "2025-01-02T00:00:00+00:00",
            "last_event_at": "2025-01-02T00:00:00+00:00",
            "baseline_price_observed_at": "2025-01-02T00:00:00+00:00",
            "baseline_price_available_at": "2025-01-03T00:00:00+00:00",
            "baseline_close": 100.0,
            "baseline_volume": 1000.0,
        },
        "provenance": {
            "source_partition_paths": ["data/research/source.jsonl"],
            "price_partition_path": "data/research/price.jsonl",
            "price_provider": "test_provider",
            "price_availability_policy": "after_close",
        },
    }


def _template() -> dict[str, object]:
    return {
        "score_id": "score-template:test",
        "model_version": "pattern_score_v3.test",
        "feature_set_version": "feature-set.test",
        "strategy_family_id": "defence_repricing_geopolitical_watch",
        "strategy_label": "Defence repricing",
        "strategy_agnostic": False,
        "negative_control": False,
        "instrument": "LMT",
        "market_family": "defence",
        "direction_hypothesis": "upside_under_confirmed_repricing",
        "horizon_hypothesis": "5d_forward",
        "feature_inputs": [{"source_key": "stock_act"}],
        "applied_learning_version_ids": [],
        "stage1_learning_input_version": "learning:test",
    }


def test_future_horizon_metadata_cannot_change_scoring_input() -> None:
    first = _alignment()
    second = deepcopy(first)
    second["available_horizons"] = ["30d_forward"]
    second["future_horizon_availability"] = {"30d_forward": "2099-01-01T00:00:00+00:00"}
    assert historical_scoring_input(first) == historical_scoring_input(second)
    assert "available_horizons" not in historical_scoring_input(first)
    assert "future_horizon_availability" not in historical_scoring_input(first)


def test_historical_input_fails_closed_on_label_or_timing_contamination() -> None:
    contaminated = _alignment()
    contaminated["feature_snapshot"]["forward_return"] = 0.5  # type: ignore[index]
    with pytest.raises(ValueError, match="label"):
        historical_scoring_input(contaminated)

    late = _alignment()
    late["source_available_at"] = "2025-01-04T00:00:00+00:00"
    with pytest.raises(ValueError, match="after_decision"):
        historical_scoring_input(late)


def test_historical_score_is_deterministic_explainable_and_non_authoritative() -> None:
    safe_input = historical_scoring_input(_alignment())
    kwargs = {
        "source_trust": {"stock_act": 0.72},
        "relationship_by_id": {
            "relationship:test": {"source_independence_cluster_id": "cluster:test"}
        },
        "market_context": {
            "baseline_close": 100.0,
            "baseline_volume": 1000.0,
            "rolling_volatility_20_observation": 0.02,
            "volume_relative_to_20_observation_mean": 1.1,
            "regime_state": "normal",
            "context_is_event_aligned_and_backward_looking": True,
        },
        "paperability": {"LMT": True},
        "alignment_sha256": "a" * 64,
    }
    first = _build_historical_score_row(_template(), [safe_input], **kwargs)
    second = _build_historical_score_row(_template(), [safe_input], **kwargs)
    assert first == second
    assert first["score_is_probability"] is False
    assert first["score_is_validated_edge"] is False
    assert first["candidate_creation_allowed"] is False
    assert first["order_creation_allowed"] is False
    assert first["future_horizon_metadata_accessed"] is False
    assert not contains_forbidden_key(first, FORBIDDEN_TAPE_KEYS)
    assert first["component_contributions"]
    assert first["missing_critical_features"] == ["fresh_source_quorum"]


def test_historical_score_ignores_mutable_live_template_identity() -> None:
    safe_input = historical_scoring_input(_alignment())
    kwargs = {
        "source_trust": {"stock_act": 0.72},
        "relationship_by_id": {
            "relationship:test": {"source_independence_cluster_id": "cluster:test"}
        },
        "market_context": {
            "baseline_close": 100.0,
            "baseline_volume": 1000.0,
            "rolling_volatility_20_observation": 0.02,
            "volume_relative_to_20_observation_mean": 1.1,
            "regime_state": "normal",
            "context_is_event_aligned_and_backward_looking": True,
        },
        "paperability": {"LMT": True},
        "alignment_sha256": "a" * 64,
    }
    first_template = _template()
    second_template = deepcopy(first_template)
    second_template["score_id"] = "score-template:next-live-observation"
    second_template["generated_at"] = "2099-01-01T00:00:00+00:00"
    second_template["raw_pattern_score"] = 0.99

    first = _build_historical_score_row(first_template, [safe_input], **kwargs)
    second = _build_historical_score_row(second_template, [safe_input], **kwargs)

    assert historical_template_id(first_template) == historical_template_id(second_template)
    assert first == second


def test_historical_template_identity_changes_for_research_contract_change() -> None:
    original = _template()
    changed = deepcopy(original)
    changed["horizon_hypothesis"] = "10d_forward"

    assert historical_template_id(original) != historical_template_id(changed)


def test_completed_partition_resume_is_idempotent_and_immutable(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(score_tape, "RESEARCH_TAPE_ROOT", tmp_path)
    path = tmp_path / "partition" / "scores.jsonl"
    row = {
        "score_id": "score:test",
        "label_columns_present": False,
        "immutable": True,
    }
    first_hash = write_score_tape_partition(path, [row])
    second_hash = write_score_tape_partition(path, [row])
    assert first_hash == second_hash
    with pytest.raises(ValueError, match="immutable"):
        write_score_tape_partition(path, [{**row, "score_id": "score:changed"}])


def _snapshot_runtime(tmp_path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "root"
    runtime = root / "data" / "runtime"
    research = root / "data" / "research" / "aligned" / "or4"
    runtime.mkdir(parents=True)
    research.mkdir(parents=True)
    alignment = research / "provider_alignment.jsonl"
    alignment.write_text(json.dumps(_alignment(), sort_keys=True) + "\n", encoding="utf-8")
    alignment_sha = score_tape.file_sha256(alignment)
    payloads = {
        score_tape.SCORE_RECORDS_ARTIFACT: json.dumps(_template()) + "\n",
        score_tape.SCORE_PRIMARY_ARTIFACT: json.dumps(
            {
                "model_version": "test",
                "record_count": 1,
                "record_set_hash": score_tape.record_set_hash([_template()]),
            }
        ),
        score_tape.PROVIDER_ALIGNMENT_ARTIFACT: json.dumps(
            {
                "status": "provider_alignment_ready",
                "alignment_records_path": str(alignment.relative_to(root)),
                "alignment_records_sha256": alignment_sha,
            }
        ),
        score_tape.SOURCE_UNIVERSE_ARTIFACT: json.dumps({"sources": []}),
        score_tape.TRADING_UNIVERSE_ARTIFACT: json.dumps({"instruments": []}),
        score_tape.ELIGIBILITY_ARTIFACT: "",
    }
    for name, text in payloads.items():
        (runtime / name).write_text(text, encoding="utf-8")
    monkeypatch.setattr(
        score_tape,
        "RESEARCH_TAPE_ROOT",
        root / "data" / "research" / "pattern_score_tape",
    )
    return root, runtime, alignment


def test_score_tape_inputs_remain_pinned_when_alignment_pointer_advances(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, runtime, alignment = _snapshot_runtime(tmp_path, monkeypatch)
    original = alignment.read_text(encoding="utf-8")
    with pinned_score_tape_inputs(runtime, root=root) as snapshot:
        pinned = snapshot["paths"]["provider_alignment_records"]
        replacement = alignment.with_suffix(".next")
        replacement.write_text('{"new_generation":true}\n', encoding="utf-8")
        replacement.replace(alignment)

        assert pinned.read_text(encoding="utf-8") == original
        assert snapshot["pinned_during_execution"] is True
        assert snapshot["template_generation_verified"] is True
        assert snapshot["alignment_generation_verified"] is True
        assert snapshot["source_changed_during_capture"] is False
        assert snapshot["snapshot_id"].startswith("score-input-snapshot:")


def test_score_tape_snapshot_capture_retries_one_transient_race(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, runtime, _alignment_path = _snapshot_runtime(tmp_path, monkeypatch)
    original = score_tape._capture_score_tape_input_snapshot_once
    calls = 0

    def flaky_capture(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise score_tape.ScoreTapeInputSnapshotRace("score_tape_input_snapshot_unstable:test")
        return original(*args, **kwargs)

    monkeypatch.setattr(
        score_tape,
        "_capture_score_tape_input_snapshot_once",
        flaky_capture,
    )
    with pinned_score_tape_inputs(runtime, root=root, capture_attempts=2) as snapshot:
        assert snapshot["capture_attempt"] == 2
    assert calls == 2


def test_score_tape_snapshot_holds_on_stable_template_lineage_mismatch(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, runtime, _alignment_path = _snapshot_runtime(tmp_path, monkeypatch)
    primary = json.loads((runtime / score_tape.SCORE_PRIMARY_ARTIFACT).read_text(encoding="utf-8"))
    primary["record_set_hash"] = "0" * 64
    (runtime / score_tape.SCORE_PRIMARY_ARTIFACT).write_text(
        json.dumps(primary),
        encoding="utf-8",
    )

    with pytest.raises(
        score_tape.ScoreTapeInputIntegrityHold,
        match="pattern_score_template_generation",
    ):
        with pinned_score_tape_inputs(runtime, root=root, capture_attempts=2):
            pass
