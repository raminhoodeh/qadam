from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from orchestrator.qadam_edge_registry import (
    build_edge_record,
    build_edge_registry_state,
    edge_admission_errors,
    validate_edge_registry_state,
)


def _validated_backtest_result() -> dict[str, object]:
    return {
        "historical_edge_candidate": True,
        "status": "historical_edge_candidate_after_holdout",
        "false_discovery_adjusted_state": "validated",
        "adjusted_p_value": 0.02,
        "holdout_untouched_during_tuning": True,
        "cost_adjusted": True,
        "negative_control": False,
        "rejection_reasons": [],
        "holdout_metrics": {
            "trade_count": 30,
            "mean_net_return": 0.01,
        },
    }


def test_edge_admission_is_fail_closed_for_controls_and_unadjusted_results() -> None:
    valid = _validated_backtest_result()
    assert edge_admission_errors(valid) == []

    invalid = dict(valid)
    invalid["negative_control"] = True
    invalid["false_discovery_adjusted_state"] = "not_significant"
    errors = edge_admission_errors(invalid)
    assert "negative_control_cannot_be_edge" in errors
    assert "false_discovery_adjustment_not_validated" in errors


def test_durable_edge_record_retains_lineage_without_downstream_authority() -> None:
    edge = build_edge_record(
        {
            "false_discovery_adjusted_state": "validated",
            "untouched_holdout": True,
            "costs_included": True,
            "source_feature_definition": {"method_id": "lead_lag_event_study"},
            "instrument": "TEST",
            "direction": "long",
            "horizon": "3d_forward",
            "regime": "normal",
            "score_version": "score:v1",
            "label_version": "label:v1",
            "fold_ids": ["fold-001"],
            "dataset_hashes": {"scores": "abc", "labels": "def"},
            "backtest_run_id": "run:test",
            "strategy_fit_vector": {"strategy:test": 1.0},
            "net_expectancy": 0.01,
        }
    )
    assert edge["promotion_class"] == "validated_research_edge"
    assert edge["paper_candidate_created"] is False
    assert edge["qualified_setup_created"] is False
    assert edge["order_created"] is False
    assert edge["broker_write_allowed"] is False
    assert edge["proof_credit_allowed"] is False


def test_rejected_or10_results_are_empirical_complete_and_honestly_have_no_edge(rejected_edge_fixture) -> None:
    state = build_edge_registry_state(rejected_edge_fixture)
    summary = state["summary"]
    strategies = state["strategy_map"]["strategies"]
    classes = {row["strategy_family_id"]: row["evidence_class"] for row in strategies}

    assert summary["status"] == "edge_registry_complete_no_validated_edge"
    assert summary["backtest_result_count"] > 0
    assert summary["backtest_rejected_result_count"] == summary["backtest_result_count"]
    assert summary["edge_count"] == 0
    assert summary["edge_validated_certification_passed"] is False
    assert summary["paper_operator_ready_certification_passed"] is False
    assert summary["valid_no_edge_outcome"] is True
    assert summary["or9_input_matches_or8"] is True
    assert len(strategies) == 5
    assert classes["prediction_market_geopolitical_dislocation"] == "exploratory"
    assert list(classes.values()).count("under_evidenced") == 4
    assert all(row["paper_attention_allowed"] is False for row in strategies)
    assert all(row["configured_dashboard_state_is_not_evidence"] is True for row in strategies)
    assert validate_edge_registry_state(state) == []


def test_strategy_without_edge_cannot_be_given_paper_attention(rejected_edge_fixture) -> None:
    state = build_edge_registry_state(rejected_edge_fixture)
    unsafe = deepcopy(state)
    unsafe["strategy_map"]["strategies"][0]["paper_attention_allowed"] = True
    assert any(
        error.startswith("strategy_without_edge_allowed_paper_attention")
        for error in validate_edge_registry_state(unsafe)
    )


@pytest.mark.parametrize("change", ["hash", "count", "outside_path", "missing_file"])
def test_edge_registry_rejects_corrupt_bulk_evidence(rejected_edge_fixture, change):
    path = Path(rejected_edge_fixture.runtime_dir) / "qadam_backtest_run_manifest.json"
    manifest = json.loads(path.read_text())
    bulk = manifest["bulk_results"]
    if change == "hash":
        bulk["result_record_set_hash"] = "wrong"
    elif change == "count":
        bulk["result_count"] += 1
    elif change == "outside_path":
        bulk["result_path"] = "../../unrelated.jsonl"
    else:
        bulk["result_path"] = "data/research/statistical_backtests/missing.jsonl"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="edge_registry_bulk_"):
        build_edge_registry_state(rejected_edge_fixture)


@pytest.mark.parametrize("missing", [None, "", True])
def test_matching_absent_or_invalid_dataset_hashes_are_not_lineage(rejected_edge_fixture, missing):
    runtime = Path(rejected_edge_fixture.runtime_dir)
    for name, key in (("qadam_backtest_run_manifest.json", None),
                      ("qadam_quantum_usefulness_summary.json", "input_audit")):
        path = runtime / name
        payload = json.loads(path.read_text())
        target = payload if key is None else payload[key]
        target["score_dataset_hash"] = target["label_dataset_hash"] = missing
        path.write_text(json.dumps(payload), encoding="utf-8")
    state = build_edge_registry_state(rejected_edge_fixture)
    assert state["summary"]["or9_input_matches_or8"] is False
    assert "edge_registry_or9_input_does_not_match_or8" in validate_edge_registry_state(state)
