from __future__ import annotations

from orchestrator.qadam_ibm_full_history_experiment import (
    _chronological_prototypes,
    validate_full_history_result,
)


def _rows(count: int = 96) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index in range(count):
        rows.append(
            {
                "score_id": f"score:{index:04d}",
                "decision_at": f"2026-01-{(index % 28) + 1:02d}T00:00:00+00:00",
                "instrument": ("SPY", "GLD", "USO")[index % 3],
                "source_keys": ["kalshi", "stock_act"][: (index % 2) + 1],
                "raw_pattern_score": index / count,
                "source_trust": 0.6 + (index % 10) / 100,
                "source_freshness": 0.9 - (index % 7) / 100,
                "source_independence": 0.5 + (index % 5) / 10,
                "causal_mapping_strength": 0.4 + (index % 4) / 10,
                "strategy_fit": (index % 6) / 5,
                "rolling_volatility": 0.01 + index / 100_000,
                "volume_relative": 0.8 + (index % 8) / 10,
                "long_net_return": 0.02 if index % 2 else -0.01,
            }
        )
    return rows


def test_every_history_row_contributes_once_and_labels_are_excluded():
    matrix, lineage, audit = _chronological_prototypes(_rows(), prototype_count=12)

    assert matrix.shape == (12, 8)
    assert len(lineage) == 12
    assert sum(row["row_count"] for row in lineage) == 96
    assert audit["represented_row_count"] == 96
    assert audit["all_rows_represented_once"] is True
    assert audit["labels_sent_to_quantum_circuit"] is False


def test_history_prototypes_are_deterministic():
    first = _chronological_prototypes(_rows(), prototype_count=12)
    second = _chronological_prototypes(list(reversed(_rows())), prototype_count=12)

    assert first[0].tolist() == second[0].tolist()
    assert first[1] == second[1]
    assert first[2] == second[2]


def test_completed_result_keeps_every_downstream_boundary_closed():
    result = {
        "schema_version": "qadam.IbmFullHistoryExperiment.v1",
        "hardware_experiment_completed": True,
        "input_envelope": {
            "provider_backed_historical_row_lineage_count": 717_479,
            "paired_score_label_row_count": 40_126,
            "paired_rows_numerically_represented": 40_126,
            "prototype_audit": {
                "all_rows_represented_once": True,
                "labels_sent_to_quantum_circuit": False,
            },
        },
        "validated_edge_created": False,
        "strategy_hypothesis_created": False,
        "trade_candidate_created": False,
        "risk_approval_created": False,
        "execution_approval_created": False,
        "paper_order_created": False,
        "broker_write_count": 0,
        "proof_credit_created": False,
        "profitability_certified": False,
    }

    assert validate_full_history_result(result, require_completed=True) == []
