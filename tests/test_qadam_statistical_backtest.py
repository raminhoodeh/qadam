from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

import orchestrator.qadam_statistical_backtest as statistical
from orchestrator.qadam_backtest_engine import (
    ALL_METHODS,
    NEGATIVE_CONTROL_METHODS,
    QADAM_METHODS,
    evaluate_predictions,
    run_whole_universe_backtest,
)
from orchestrator.qadam_statistical_backtest import _write_immutable_partition
from orchestrator.qadam_wave_b_common import record_set_hash, stable_id


UTC = timezone.utc


def _synthetic_rows(count: int = 240) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    start = datetime(2020, 1, 1, tzinfo=UTC)
    for index in range(count):
        score = ((index % 21) - 10) / 10.0
        raw_return = score * 0.012 + (0.0005 if index % 2 == 0 else -0.0005)
        rows.append(
            {
                "score_id": f"score:{index:04d}",
                "label_id": f"label:{index:04d}",
                "decision_at": (start + timedelta(days=index * 3)).isoformat(),
                "outcome_available_at": (
                    start + timedelta(days=index * 3 + 3)
                ).isoformat(),
                "strategy_family_id": "strategy:test",
                "strategy_label": "Synthetic strategy",
                "instrument": "TEST",
                "horizon": "3d_forward",
                "regime": "normal" if index % 3 else "calm",
                "source_keys": ["source_a", "source_b"],
                "raw_pattern_score": score,
                "source_trust": 0.8,
                "source_freshness": 0.9,
                "source_independence": 1.0,
                "causal_mapping_strength": 0.7,
                "strategy_fit": 0.8,
                "rolling_volatility": 0.02,
                "volume_relative": 1.1,
                "source_event_count": 2 + index % 4,
                "distinct_source_count": 2,
                "independent_source_cluster_count": 2,
                "price_before": 100.0 + index * 0.1,
                "research_gross_return": raw_return,
                "execution_gross_return": raw_return,
                "long_net_return": raw_return - 0.0006,
                "short_net_return": -raw_return - 0.0006,
                "transaction_cost_bps": 6.0,
                "execution_instrument": "TEST",
                "execution_proxy_used": False,
                "overlap_group_id": f"overlap:{index:04d}",
                "independent_sample": True,
                "score_created_before_label": True,
                "candidate_creation_allowed": False,
                "order_creation_allowed": False,
                "proof_credit_allowed": False,
            }
        )
    return rows


def test_cost_adjusted_prediction_selects_direction_without_mutating_rows() -> None:
    rows = _synthetic_rows(4)
    before = [dict(row) for row in rows]
    metrics = evaluate_predictions(rows, [1.0, -1.0, 1.0, -1.0], 0.0)
    assert metrics["trade_count"] == 4
    assert metrics["direction_counts"] == {"long": 2, "short": 2}
    assert rows == before


def test_whole_universe_run_is_deterministic_and_keeps_holdout_untouched() -> None:
    rows = _synthetic_rows()
    first = run_whole_universe_backtest(rows, stable_id_builder=stable_id)
    second = run_whole_universe_backtest(rows, stable_id_builder=stable_id)
    assert record_set_hash(first["results"]) == record_set_hash(second["results"])
    assert record_set_hash(first["folds"]) == record_set_hash(second["folds"])
    assert first["attempted_hypothesis_count"] == len(ALL_METHODS)
    assert first["false_discovery_adjusted_result_count"] == len(ALL_METHODS)
    assert first["untouched_holdout_result_count"] == len(ALL_METHODS)
    result_by_id = {row["hypothesis_id"]: row for row in first["results"]}
    for fold in first["folds"]:
        assert fold["holdout_accessed"] is False
        assert fold["test_end_at"] < result_by_id[fold["hypothesis_id"]]["holdout_start_at"]


def test_negative_controls_and_comparators_cannot_become_edge_candidates() -> None:
    result = run_whole_universe_backtest(
        _synthetic_rows(), stable_id_builder=stable_id
    )
    candidates = result["historical_edge_candidates"]
    assert all(row["method_id"] in QADAM_METHODS for row in candidates)
    assert not any(
        row["method_id"] in NEGATIVE_CONTROL_METHODS
        and row["historical_edge_candidate"]
        for row in result["results"]
    )
    assert result["negative_control_validated_count"] == 0
    assert all(row["edge_created"] is False for row in result["results"])


def test_insufficient_independent_history_is_registered_and_rejected() -> None:
    result = run_whole_universe_backtest(
        _synthetic_rows(20), stable_id_builder=stable_id
    )
    assert result["attempted_hypothesis_count"] == len(ALL_METHODS)
    assert result["untouched_holdout_result_count"] == 0
    assert result["historical_edge_candidates"] == []
    assert all(
        row["rejection_reasons"] == ["insufficient_independent_history"]
        for row in result["results"]
    )


def test_completed_bulk_results_are_idempotent_and_immutable(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(statistical, "RESEARCH_BACKTEST_ROOT", tmp_path)
    path = tmp_path / "run=test" / "results.jsonl"
    rows = [{"hypothesis_id": "hypothesis:test", "edge_created": False}]
    first_hash, first_reused = _write_immutable_partition(path, rows)
    second_hash, second_reused = _write_immutable_partition(path, rows)
    assert first_hash == second_hash
    assert first_reused is False
    assert second_reused is True
    with pytest.raises(ValueError, match="immutable"):
        _write_immutable_partition(
            path, [{"hypothesis_id": "hypothesis:changed", "edge_created": False}]
        )
