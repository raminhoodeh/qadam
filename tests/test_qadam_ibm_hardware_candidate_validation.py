from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import math
from pathlib import Path

import orchestrator.qadam_ibm_hardware_candidate_validation as candidate_validation
from orchestrator.qadam_ibm_hardware_candidate_validation import (
    build_hardware_candidate_validation,
    validate_hardware_candidate_validation,
)


def _hardware_result() -> dict:
    return {
        "status": "completed",
        "provider_status": "SUCCESS",
        "experiment_id": "ibm-full-history-surprise-discovery-v1",
        "receipt_hash": "a" * 64,
        "hardware_manifest_hash": "b" * 64,
        "input_envelope": {
            "prototype_audit": {"labels_sent_to_quantum_circuit": False}
        },
        "research_candidates": [
            {
                "candidate_id": "discovery-candidate:test",
                "research_question": (
                    "Does causal evidence become more useful when market activity agrees?"
                ),
                "feature_pair": ["causal_mapping_strength", "market_flow"],
                "structural_score": 0.291437885662,
            }
        ],
    }


def _rows() -> list[dict]:
    start = datetime(2023, 1, 1, tzinfo=timezone.utc)
    rows = []
    for index in range(1_200):
        gross = math.sin(index * 0.071) * 0.012
        decision_at = (start + timedelta(days=index // 10)).isoformat()
        rows.append(
            {
                "score_id": f"score-{index:04d}",
                "decision_at": decision_at,
                "independent_sample": True,
                "score_created_before_label": True,
                "causal_mapping_strength": math.sin(index * 0.131),
                "volume_relative": math.cos(index * 0.173),
                "research_gross_return": gross,
                "execution_gross_return": gross,
                "long_net_return": gross - 0.001,
                "short_net_return": -gross - 0.001,
                "instrument": ["SPY", "GLD", "USO", "SMH"][index % 4],
                "horizon": ["1d", "5d", "10d"][index % 3],
                "regime": ["calm", "stress"][index % 2],
                "source_keys": ["kalshi", "stock_act"],
            }
        )
    return rows


def test_hardware_candidate_is_tested_without_creating_authority(monkeypatch) -> None:
    result = _hardware_result()

    def fake_read_json(path: Path) -> dict:
        if path.name == candidate_validation.RESULT_ARTIFACT:
            return result
        if path.name == candidate_validation.QBC_RESULTS_ARTIFACT:
            return {"current_registered_result_count": 3_012}
        return {}

    monkeypatch.setattr(candidate_validation, "read_json", fake_read_json)
    monkeypatch.setattr(
        candidate_validation,
        "load_empirical_backtest_dataset",
        lambda _runtime: (
            _rows(),
            {
                "provider_backed_row_count": 717_479,
                "paired_score_label_row_count": 40_126,
            },
        ),
    )

    payload = build_hardware_candidate_validation(
        Path("/unused"), generated_at="2026-07-20T12:30:00+00:00"
    )

    assert payload["status"] == "tested_rejected_no_predictive_value"
    assert payload["candidate_selected_without_outcome_labels"] is True
    assert payload["split"][
        "candidate_holdout_untouched_during_fit_and_threshold_selection"
    ] is True
    assert payload["comparison"]["correction_family_size"] == 3_013
    assert payload["verdict"]["validated_edge_created"] is False
    assert payload["verdict"]["strategy_change_created"] is False
    assert payload["verdict"]["trade_candidate_created"] is False
    assert validate_hardware_candidate_validation(payload) == []


def test_validation_fails_closed_if_rejection_is_promoted(monkeypatch) -> None:
    result = _hardware_result()

    monkeypatch.setattr(
        candidate_validation,
        "read_json",
        lambda path: (
            result
            if path.name == candidate_validation.RESULT_ARTIFACT
            else {"current_registered_result_count": 3_012}
        ),
    )
    monkeypatch.setattr(
        candidate_validation,
        "load_empirical_backtest_dataset",
        lambda _runtime: (_rows(), {}),
    )
    payload = build_hardware_candidate_validation(
        Path("/unused"), generated_at="2026-07-20T12:30:00+00:00"
    )
    unsafe = deepcopy(payload)
    unsafe["verdict"]["trade_candidate_created"] = True

    assert "authority_boundary_breached:trade_candidate_created" in (
        validate_hardware_candidate_validation(unsafe)
    )
