"""Audit OR-19 inputs for schema drift and terminal-state correctness."""

from __future__ import annotations

from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    runtime_dir,
    write_json_atomic,
)

SCHEMA_VERSION = "qadam_certification_contract_audit.v1"
AUDIT_ARTIFACT = "qadam_certification_contract_audit.json"
BACKTEST_COMPATIBILITY_ARTIFACT = "qadam_backtest_field_compatibility_audit.json"


def evaluate_contracts(
    *,
    backfill: dict[str, Any],
    point_in_time: dict[str, Any],
    backtest: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    generated_at = now_iso()
    acquired = int(backfill.get("completed_partition_count") or 0)
    unavailable = int(backfill.get("unavailable_classified_partition_count") or 0)
    total = int(backfill.get("total_partition_count") or 0)
    remaining = int(backfill.get("remaining_partition_count") or 0)
    terminal = total > 0 and acquired + unavailable == total and remaining == 0
    fold_count = int(backtest.get("fold_result_count") or backtest.get("fold_count") or 0)
    holdout_count = int(backtest.get("untouched_holdout_result_count") or 0)
    negative_executed = int(backtest.get("negative_control_executed_count") or 0)
    negative_positive = int(
        backtest.get("negative_control_statistically_positive_count") or 0
    )
    negative_gate_breaches = int(
        backtest.get("negative_control_promotion_gate_breach_count") or 0
    )
    negative_validated = int(backtest.get("negative_control_validated_count") or 0)
    errors: list[str] = []
    if not terminal:
        errors.append("provider_partitions_not_terminal")
    if int(backfill.get("provider_row_count") or 0) <= 0:
        errors.append("provider_rows_missing")
    if int(point_in_time.get("eligible_forward_score_input_count") or 0) <= 0:
        errors.append("historical_score_inputs_missing")
    if int(point_in_time.get("eligible_leakage_violation_count") or 0) != 0:
        errors.append("point_in_time_leakage_violation")
    if backtest.get("empirical_backtest_complete") is not True:
        errors.append("empirical_backtest_incomplete")
    if fold_count <= 0:
        errors.append("walk_forward_folds_missing")
    if holdout_count <= 0:
        errors.append("untouched_holdout_missing")
    if negative_executed <= 0:
        errors.append("negative_controls_not_executed")
    if negative_gate_breaches != 0:
        errors.append("negative_control_promotion_gate_breach")
    if negative_validated != 0:
        errors.append("negative_control_improperly_validated")
    compatibility = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_backtest_field_compatibility_audit",
        "generated_at": generated_at,
        "status": "passed" if fold_count > 0 else "blocked",
        "canonical_fold_field": "fold_result_count",
        "legacy_fold_field": "fold_count",
        "canonical_fold_value": backtest.get("fold_result_count"),
        "legacy_fold_value": backtest.get("fold_count"),
        "resolved_fold_count": fold_count,
        "untouched_holdout_result_count": holdout_count,
        "negative_control_executed_count": negative_executed,
        "negative_control_statistically_positive_count": negative_positive,
        "negative_control_promotion_gate_breach_count": negative_gate_breaches,
        "negative_control_validated_count": negative_validated,
        "negative_control_pass_rule": (
            "executed > 0, promotion-gate breaches = 0, validated = 0; "
            "adjusted-significant rejected controls remain diagnostic"
        ),
        "authority": authority_flags(),
    }
    audit = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_certification_contract_audit",
        "generated_at": generated_at,
        "status": "passed" if not errors else "blocked",
        "provider_terminal_state": {
            "passed": terminal,
            "acquired_partitions": acquired,
            "classified_unavailable_partitions": unavailable,
            "remaining_partitions": remaining,
            "total_partitions": total,
            "classified_unavailable_is_not_evidence": True,
        },
        "point_in_time_historical_state": {
            "eligible_score_inputs": point_in_time.get(
                "eligible_forward_score_input_count"
            ),
            "provider_alignment_records": point_in_time.get(
                "provider_alignment_record_count"
            ),
            "leakage_violations": point_in_time.get(
                "eligible_leakage_violation_count"
            ),
            "current_trade_context_gaps": point_in_time.get(
                "typed_evidence_gap_count"
            ),
            "historical_scoring_separate_from_current_trade_context": True,
        },
        "backtest_compatibility": compatibility,
        "validated_edge_count": int(backtest.get("validated_edge_count") or 0),
        "validated_edge_required_for_paper_release": True,
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    return audit, compatibility


def run_certification_contract_audit(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    runtime = runtime_dir(settings)
    audit, compatibility = evaluate_contracts(
        backfill=read_json(runtime / "qadam_provider_backfill_checks.json"),
        point_in_time=read_json(runtime / "qadam_point_in_time_evidence_checks.json"),
        backtest=read_json(runtime / "qadam_statistical_backtest_checks.json"),
    )
    write_json_atomic(runtime / AUDIT_ARTIFACT, audit)
    write_json_atomic(runtime / BACKTEST_COMPATIBILITY_ARTIFACT, compatibility)
    return audit, compatibility


__all__ = [
    "AUDIT_ARTIFACT",
    "BACKTEST_COMPATIBILITY_ARTIFACT",
    "evaluate_contracts",
    "run_certification_contract_audit",
]
