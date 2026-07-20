from __future__ import annotations

import json
from pathlib import Path

import pytest

import orchestrator.qadam_learning_backtest_gap_closure as closure


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "data" / "runtime"


def _read(name: str) -> dict:
    return json.loads((RUNTIME / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module", autouse=True)
def _build_gap_closure(tmp_path_factory: pytest.TempPathFactory):
    original_log = closure.IMPLEMENTATION_LOG
    closure.IMPLEMENTATION_LOG = tmp_path_factory.mktemp("plbg") / "implementation-log.md"
    try:
        yield closure.build_all()
    finally:
        closure.IMPLEMENTATION_LOG = original_log


def test_all_implementation_stages_and_evidence_certification_pass_honestly():
    certification = _read(
        "qadam_learning_and_backtest_gap_closure_certification.json"
    )

    assert certification["implementation_complete"] is True
    assert certification["evidence_program_complete"] is True
    assert certification["certification_level"] == "complete_no_edge_found"
    assert certification["blockers"] == []
    assert certification["profitability_certified"] is False
    assert all(
        stage["status"] == "passed"
        for stage in certification["stage_checks"].values()
    )


def test_current_universe_and_legacy_learning_are_reconciled_without_authority():
    contract = _read("qadam_daily_learning_contract_v2.json")
    inventory = _read("qadam_legacy_learning_inventory.json")
    memory = _read("qadam_learning_memory_manifest.json")

    assert contract["canonical_source_count"] == 41
    assert contract["canonical_watched_instrument_count"] == 19
    assert contract["canonical_validated_edge_count"] == 0
    assert contract["legacy_source_count_allowed"] is False
    assert contract["legacy_watched_instrument_count_allowed"] is False
    assert contract["legacy_edge_count_allowed"] is False
    assert contract["applied_learning_version_count"] == 0
    assert inventory["record_count"] > 0
    assert inventory["original_sources_mutated"] is False
    assert memory["observation_count"] > 0
    assert memory["historically_eligible_observation_count"] == 0
    assert memory["frequency_is_predictive_feature"] is False


def test_every_source_and_instrument_gap_has_a_typed_state():
    matrix = _read("qadam_full_universe_gap_closure_matrix.json")
    empirical = _read("qadam_full_universe_empirical_coverage.json")

    assert matrix["source_count"] == 41
    assert matrix["instrument_count"] == 19
    assert matrix["generic_missing_count"] == 0
    assert sum(matrix["source_state_counts"].values()) == 41
    assert sum(matrix["instrument_state_counts"].values()) == 19
    assert empirical["empirically_scored_source_count"] == 5
    assert empirical["empirically_tested_instrument_count"] == 17
    assert empirical[
        "historical_acquisition_complete_does_not_mean_empirical_complete"
    ] is True


def test_focus_provider_limits_remain_explicit():
    stock_act = _read("qadam_stock_act_detail_coverage.json")
    unusual_whales = _read("qadam_unusual_whales_history_coverage.json")
    backtest = _read("qadam_focus_provider_backtest_summary.json")
    credentials = _read("qadam_focus_provider_credential_truth.json")

    assert stock_act["filing_index_record_count"] > 0
    assert stock_act["parsed_transaction_detail_count"] == 0
    assert stock_act["fake_exact_notional_created_count"] == 0
    assert unusual_whales["backtest_eligible_record_count"] == 0
    assert unusual_whales["historical_backtest_allowed"] is False
    assert backtest["validated_edge_count"] == 0
    assert backtest["v4_focus_empirical_complete"] is True
    assert backtest["status"] == "complete_no_edge_found"
    assert backtest["focus_attempted_hypothesis_count"] > 0
    assert backtest["focus_false_discovery_adjusted_result_count"] == backtest[
        "focus_attempted_hypothesis_count"
    ]
    assert all(
        experiment["completed_lane_count"] == experiment["required_lane_count"]
        for experiment in backtest["focus_experiments"]
    )
    assert all(
        provider["secret_value_recorded"] is False
        for provider in credentials["providers"]
    )


def test_historical_work_did_not_touch_paper_or_execution_authority():
    certification = _read(
        "qadam_learning_and_backtest_gap_closure_certification.json"
    )

    assert certification["paper_epoch_unchanged"] is True
    assert certification["network_call_count"] == 0
    assert certification["trade_candidate_created_count"] == 0
    assert certification["paper_order_created_count"] == 0
    assert certification["broker_write_count"] == 0
    assert certification["proof_credit_created_count"] == 0
    assert certification["paper_calendar_advanced"] is False
    assert certification["live_capital_enabled"] is False
