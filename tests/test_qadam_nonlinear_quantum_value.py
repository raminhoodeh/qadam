from __future__ import annotations

import math

from orchestrator.qadam_nonlinear_quantum_engine import (
    EXPERIMENT_METHODS,
    NEGATIVE_CONTROL_METHOD,
    QUANTUM_METHOD,
    enrich_or9_rows,
    run_nonlinear_quantum_experiments,
)
from orchestrator.qadam_nonlinear_quantum_value import quantum_usefulness_score


def _row(index: int) -> dict[str, object]:
    score = 0.45 + 0.15 * math.sin(index / 9.0)
    gross = 0.004 * math.sin((index + 3) / 7.0)
    cost = 0.0005
    return {
        "score_id": f"score:{index:04d}",
        "decision_at": f"2025-{1 + index // 28:02d}-{1 + index % 28:02d}T00:00:00+00:00",
        "strategy_family_id": "strategy:test",
        "instrument": "TEST",
        "horizon": "1d_forward",
        "regime": "risk_on" if index % 11 < 6 else "risk_off",
        "source_keys": ["source:a", "source:b"],
        "raw_pattern_score": score,
        "source_trust": 0.8,
        "source_freshness": 0.9,
        "source_independence": 0.7 + 0.1 * math.cos(index / 5.0),
        "causal_mapping_strength": 0.6,
        "strategy_fit": 0.65,
        "source_event_count": 2 + index % 5,
        "distinct_source_count": 2 + index % 3,
        "independent_source_cluster_count": 2,
        "rolling_volatility": 0.15 + 0.03 * math.cos(index / 13.0),
        "volume_relative": 0.9 + 0.1 * math.sin(index / 4.0),
        "price_before": 100.0 + index * 0.1,
        "research_gross_return": gross,
        "execution_gross_return": gross,
        "long_net_return": gross - cost,
        "short_net_return": -gross - cost,
        "transaction_cost_bps": 5.0,
        "independent_sample": True,
        "score_created_before_label": True,
    }


def test_or9_entropy_features_do_not_change_when_only_future_input_changes() -> None:
    rows = [_row(index) for index in range(30)]
    first = enrich_or9_rows(rows)
    changed = [dict(row) for row in rows]
    changed[-1]["raw_pattern_score"] = 0.99
    second = enrich_or9_rows(changed)
    assert [row["ordinal_entropy"] for row in first[:-1]] == [
        row["ordinal_entropy"] for row in second[:-1]
    ]


def test_or9_runs_every_method_against_a_matched_untouched_baseline() -> None:
    engine = run_nonlinear_quantum_experiments([_row(index) for index in range(180)])
    methods = {record["method"] for record in engine["records"]}
    assert set(EXPERIMENT_METHODS).issubset(methods)
    assert NEGATIVE_CONTROL_METHOD in methods
    assert engine["eligible_group_count"] == 1
    assert all(record.get("matched_classical_baseline") for record in engine["records"])
    assert all(
        record.get("holdout_untouched_during_tuning") is True for record in engine["records"]
    )
    quantum = next(record for record in engine["records"] if record["method"] == QUANTUM_METHOD)
    assert quantum["status"] == "measured"
    assert quantum["model_kind"] == "qiskit_statevector_fidelity_nystrom_ridge"
    assert quantum["fallback_used"] is False


def test_quantum_usefulness_requires_incremental_value_after_all_penalties() -> None:
    assert (
        quantum_usefulness_score(
            classical_holdout_metric=0.01,
            quantum_holdout_metric=0.011,
            complexity_penalty=0.25,
            latency_penalty=0.25,
            reliability=1.0,
        )
        == 0.0
    )
    assert (
        quantum_usefulness_score(
            classical_holdout_metric=None,
            quantum_holdout_metric=0.02,
            complexity_penalty=0.0,
            latency_penalty=0.0,
            reliability=1.0,
        )
        is None
    )
