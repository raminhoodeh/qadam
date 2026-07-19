from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_certification_contracts import evaluate_contracts


def _backfill() -> dict:
    return {
        "completed_partition_count": 223,
        "unavailable_classified_partition_count": 137,
        "remaining_partition_count": 0,
        "total_partition_count": 360,
        "provider_row_count": 746_275,
    }


def _point_in_time() -> dict:
    return {
        "eligible_forward_score_input_count": 553_428,
        "provider_alignment_record_count": 93_094,
        "eligible_leakage_violation_count": 0,
        "typed_evidence_gap_count": 465,
    }


def _backtest() -> dict:
    return {
        "empirical_backtest_complete": True,
        "fold_result_count": 1_332,
        "untouched_holdout_result_count": 300,
        "negative_control_executed_count": 25,
        "negative_control_statistically_positive_count": 0,
        "negative_control_validated_count": 0,
        "validated_edge_count": 0,
    }


def test_classified_unavailable_partitions_are_terminal_but_not_evidence() -> None:
    audit, compatibility = evaluate_contracts(
        backfill=_backfill(),
        point_in_time=_point_in_time(),
        backtest=_backtest(),
    )
    assert audit["status"] == "passed"
    assert audit["provider_terminal_state"]["passed"] is True
    assert audit["provider_terminal_state"]["classified_unavailable_is_not_evidence"] is True
    assert compatibility["resolved_fold_count"] == 1_332


def test_negative_control_false_positive_blocks_contract() -> None:
    backtest = _backtest()
    backtest["negative_control_statistically_positive_count"] = 1
    audit, _ = evaluate_contracts(
        backfill=_backfill(),
        point_in_time=_point_in_time(),
        backtest=backtest,
    )
    assert audit["status"] == "blocked"
    assert "negative_control_false_positive" in audit["validation_errors"]


def test_unclassified_partition_blocks_contract() -> None:
    backfill = _backfill()
    backfill["unavailable_classified_partition_count"] = 136
    backfill["remaining_partition_count"] = 1
    audit, _ = evaluate_contracts(
        backfill=backfill,
        point_in_time=_point_in_time(),
        backtest=_backtest(),
    )
    assert "provider_partitions_not_terminal" in audit["validation_errors"]
