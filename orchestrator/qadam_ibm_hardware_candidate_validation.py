"""Historical validation for research relationships surfaced by IBM hardware.

The hardware experiment is label-blind discovery. This module performs the
separate predictive test: a frozen interaction model is compared with an
additive classical model on chronological, cost-adjusted outcomes. A result can
close or advance the research programme, but it cannot create an edge, mutate a
strategy, pass Akber, or authorize an order.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import math
from pathlib import Path
from statistics import fmean
from typing import Any

import numpy as np

from orchestrator.config import Settings
from orchestrator.qadam_backtest_engine import (
    MINIMUM_EFFECTIVE_HOLDOUT_BLOCKS,
    MINIMUM_HOLDOUT_TRADES,
    dependence_aware_mean_uncertainty,
    evaluate_predictions,
    tune_threshold,
)
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    runtime_dir,
    write_json_atomic,
)
from orchestrator.qadam_quantum_discovery_evidence import stable_hash
from orchestrator.qadam_statistical_backtest import load_empirical_backtest_dataset


SCHEMA_VERSION = "qadam.IbmHardwareCandidateValidation.v1"
CHECK_SCHEMA_VERSION = "qadam.IbmHardwareCandidateValidationChecks.v1"
VALIDATION_ARTIFACT = "qadam_ibm_hardware_candidate_validation.json"
CHECK_ARTIFACT = "qadam_ibm_hardware_candidate_validation_checks.json"
RESULT_ARTIFACT = "qadam_ibm_full_history_experiment_result.json"
QBC_RESULTS_ARTIFACT = "qadam_backtest_completion_results_summary.json"

FEATURE_MAP = {
    "causal_mapping_strength": "causal_mapping_strength",
    "market_flow": "volume_relative",
}


def _zero_authority() -> dict[str, Any]:
    return {
        **authority_flags(),
        "validated_edge_creation_allowed": False,
        "strategy_hypothesis_creation_allowed": False,
        "trade_candidate_creation_allowed": False,
        "hardware_scheduler_enabled": False,
        "automatic_paid_hardware_rerun_allowed": False,
    }


def _content_hash(payload: dict[str, Any]) -> str:
    return stable_hash(
        {key: value for key, value in payload.items() if key != "content_hash"}
    )


def _number(value: Any, default: float = 0.0) -> float:
    if value is None or isinstance(value, bool):
        return default
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def _clean_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in metrics.items() if key != "returns"}


def _eligible_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    eligible: list[dict[str, Any]] = []
    for row in rows:
        if row.get("independent_sample") is not True:
            continue
        if row.get("score_created_before_label") is not True:
            continue
        if row.get("long_net_return") is None or row.get("short_net_return") is None:
            continue
        if row.get("execution_gross_return") is None:
            continue
        if any(
            not math.isfinite(_number(row.get(field), float("nan")))
            for field in FEATURE_MAP.values()
        ):
            continue
        eligible.append(dict(row))
    return sorted(
        eligible,
        key=lambda row: (str(row.get("decision_at") or ""), str(row.get("score_id") or "")),
    )


def _chronological_split(rows: list[dict[str, Any]]) -> dict[str, Any]:
    dates = sorted({str(row["decision_at"]) for row in rows})
    if len(dates) < 20:
        raise ValueError("ibm_candidate_insufficient_distinct_decision_times")
    train_boundary = max(2, int(len(dates) * 0.70))
    validation_boundary = max(train_boundary + 3, int(len(dates) * 0.80))
    if validation_boundary + 2 >= len(dates):
        raise ValueError("ibm_candidate_chronological_split_too_short")

    train_dates = set(dates[:train_boundary])
    purge_date = dates[train_boundary]
    validation_dates = set(dates[train_boundary + 1 : validation_boundary])
    embargo_date = dates[validation_boundary]
    holdout_dates = set(dates[validation_boundary + 1 :])

    split = {
        "train": [row for row in rows if row["decision_at"] in train_dates],
        "validation": [
            row for row in rows if row["decision_at"] in validation_dates
        ],
        "holdout": [row for row in rows if row["decision_at"] in holdout_dates],
    }
    if any(not split[key] for key in split):
        raise ValueError("ibm_candidate_empty_chronological_partition")
    return {
        **split,
        "audit": {
            "distinct_decision_time_count": len(dates),
            "train_row_count": len(split["train"]),
            "validation_row_count": len(split["validation"]),
            "holdout_row_count": len(split["holdout"]),
            "train_start_at": split["train"][0]["decision_at"],
            "train_end_at": split["train"][-1]["decision_at"],
            "purge_decision_at": purge_date,
            "validation_start_at": split["validation"][0]["decision_at"],
            "validation_end_at": split["validation"][-1]["decision_at"],
            "embargo_decision_at": embargo_date,
            "holdout_start_at": split["holdout"][0]["decision_at"],
            "holdout_end_at": split["holdout"][-1]["decision_at"],
            "same_timestamp_cross_partition_count": 0,
            "candidate_holdout_untouched_during_fit_and_threshold_selection": True,
            "programme_level_holdout_status": (
                "historical_period_previously_used_by_the_wider_qadam_programme; "
                "forward_shadow_still_required"
            ),
        },
    }


def _fit_design_contract(
    train: list[dict[str, Any]], *, include_interaction: bool
) -> dict[str, Any]:
    feature_names = tuple(FEATURE_MAP.values())
    means = {
        name: fmean(_number(row.get(name)) for row in train) for name in feature_names
    }
    scales: dict[str, float] = {}
    for name in feature_names:
        values = np.asarray([_number(row.get(name)) for row in train], dtype=float)
        scales[name] = max(1e-9, float(values.std()))
    instruments = sorted({str(row.get("instrument") or "") for row in train})
    horizons = sorted({str(row.get("horizon") or "") for row in train})
    contract = {
        "feature_names": feature_names,
        "means": means,
        "scales": scales,
        "instruments": instruments,
        "horizons": horizons,
        "include_interaction": include_interaction,
    }
    matrix = _design_matrix(train, contract)
    targets = np.asarray(
        [_number(row.get("research_gross_return")) for row in train], dtype=float
    )
    alpha = 1e-3 * max(1, len(train))
    gram = matrix.T @ matrix
    penalty = np.eye(gram.shape[0], dtype=float) * alpha
    penalty[0, 0] = 0.0
    coefficients = np.linalg.pinv(gram + penalty) @ matrix.T @ targets
    return {
        **contract,
        "alpha": alpha,
        "coefficients": coefficients,
        "parameter_count": int(matrix.shape[1]),
        "coefficient_hash": stable_hash(
            [round(float(value), 14) for value in coefficients.tolist()]
        ),
        "interaction_coefficient": (
            float(coefficients[3]) if include_interaction else None
        ),
    }


def _design_matrix(rows: list[dict[str, Any]], model: dict[str, Any]) -> np.ndarray:
    instruments = list(model["instruments"])
    horizons = list(model["horizons"])
    instrument_columns = instruments[1:]
    horizon_columns = horizons[1:]
    vectors: list[list[float]] = []
    for row in rows:
        first = (
            _number(row.get("causal_mapping_strength"))
            - _number(model["means"].get("causal_mapping_strength"))
        ) / max(1e-9, _number(model["scales"].get("causal_mapping_strength"), 1.0))
        second = (
            _number(row.get("volume_relative"))
            - _number(model["means"].get("volume_relative"))
        ) / max(1e-9, _number(model["scales"].get("volume_relative"), 1.0))
        vector = [1.0, first, second]
        if model.get("include_interaction") is True:
            vector.append(first * second)
        instrument = str(row.get("instrument") or "")
        horizon = str(row.get("horizon") or "")
        vector.extend(1.0 if instrument == item else 0.0 for item in instrument_columns)
        vector.extend(1.0 if horizon == item else 0.0 for item in horizon_columns)
        vectors.append(vector)
    return np.asarray(vectors, dtype=float)


def _predict(model: dict[str, Any], rows: list[dict[str, Any]]) -> list[float]:
    matrix = _design_matrix(rows, model)
    return (matrix @ model["coefficients"]).tolist()


def _opportunity_returns(
    rows: list[dict[str, Any]], predictions: list[float], threshold: float
) -> list[float]:
    returns: list[float] = []
    for row, prediction in zip(rows, predictions, strict=True):
        if prediction == 0.0 or abs(prediction) < threshold:
            returns.append(0.0)
            continue
        direction = "long" if prediction > 0 else "short"
        returns.append(_number(row.get(f"{direction}_net_return")))
    return returns


def _one_sided_p_value(values: list[float]) -> tuple[float, dict[str, Any]]:
    uncertainty = dependence_aware_mean_uncertainty(values)
    mean = uncertainty.get("mean")
    standard_error = uncertainty.get("standard_error")
    if mean is None or standard_error is None or float(standard_error) <= 0:
        return 1.0, uncertainty
    statistic = float(mean) / float(standard_error)
    return (
        min(1.0, max(0.0, 0.5 * math.erfc(statistic / math.sqrt(2.0)))),
        uncertainty,
    )


def _instrument_stability(
    rows: list[dict[str, Any]], predictions: list[float], threshold: float
) -> dict[str, Any]:
    grouped_rows: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    grouped_predictions: defaultdict[str, list[float]] = defaultdict(list)
    for row, prediction in zip(rows, predictions, strict=True):
        instrument = str(row.get("instrument") or "unclassified")
        grouped_rows[instrument].append(row)
        grouped_predictions[instrument].append(prediction)
    records = []
    for instrument in sorted(grouped_rows):
        metrics = evaluate_predictions(
            grouped_rows[instrument], grouped_predictions[instrument], threshold
        )
        records.append(
            {
                "instrument": instrument,
                "eligible_row_count": metrics.get("eligible_row_count"),
                "trade_count": metrics.get("trade_count"),
                "mean_net_return": metrics.get("mean_net_return"),
                "hit_rate": metrics.get("hit_rate"),
            }
        )
    measured = [row for row in records if int(row.get("trade_count") or 0) >= 10]
    return {
        "instruments": records,
        "measured_instrument_count": len(measured),
        "positive_measured_instrument_count": sum(
            _number(row.get("mean_net_return"), -1.0) > 0 for row in measured
        ),
        "positive_measured_instrument_ratio": (
            sum(_number(row.get("mean_net_return"), -1.0) > 0 for row in measured)
            / len(measured)
            if measured
            else 0.0
        ),
    }


def build_hardware_candidate_validation(
    runtime: Path,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated = generated_at or now_iso()
    result = read_json(runtime / RESULT_ARTIFACT)
    if result.get("status") != "completed" or result.get("provider_status") != "SUCCESS":
        raise ValueError("ibm_hardware_completed_result_required")
    candidates = result.get("research_candidates") or []
    if len(candidates) != 1:
        raise ValueError("ibm_hardware_single_candidate_required")
    candidate = candidates[0]
    feature_pair = [str(value) for value in candidate.get("feature_pair") or []]
    if feature_pair != ["causal_mapping_strength", "market_flow"]:
        raise ValueError("ibm_hardware_candidate_feature_pair_unsupported")
    if (result.get("input_envelope") or {}).get("prototype_audit", {}).get(
        "labels_sent_to_quantum_circuit"
    ) is not False:
        raise ValueError("ibm_hardware_candidate_not_label_blind")

    rows, input_audit = load_empirical_backtest_dataset(runtime)
    eligible = _eligible_rows(rows)
    if len(eligible) < 500:
        raise ValueError("ibm_hardware_candidate_insufficient_eligible_rows")
    split = _chronological_split(eligible)
    train = split["train"]
    validation = split["validation"]
    holdout = split["holdout"]

    baseline_model = _fit_design_contract(train, include_interaction=False)
    interaction_model = _fit_design_contract(train, include_interaction=True)
    baseline_train_predictions = _predict(baseline_model, train)
    baseline_validation_predictions = _predict(baseline_model, validation)
    baseline_threshold, baseline_tuning = tune_threshold(
        baseline_train_predictions, validation, baseline_validation_predictions
    )
    interaction_train_predictions = _predict(interaction_model, train)
    interaction_validation_predictions = _predict(interaction_model, validation)
    interaction_threshold, interaction_tuning = tune_threshold(
        interaction_train_predictions, validation, interaction_validation_predictions
    )

    baseline_holdout_predictions = _predict(baseline_model, holdout)
    interaction_holdout_predictions = _predict(interaction_model, holdout)
    baseline_metrics = evaluate_predictions(
        holdout, baseline_holdout_predictions, baseline_threshold
    )
    interaction_metrics = evaluate_predictions(
        holdout, interaction_holdout_predictions, interaction_threshold
    )
    baseline_opportunities = _opportunity_returns(
        holdout, baseline_holdout_predictions, baseline_threshold
    )
    interaction_opportunities = _opportunity_returns(
        holdout, interaction_holdout_predictions, interaction_threshold
    )
    incremental_returns = [
        interaction - baseline
        for interaction, baseline in zip(
            interaction_opportunities, baseline_opportunities, strict=True
        )
    ]
    raw_incremental_p_value, incremental_uncertainty = _one_sided_p_value(
        incremental_returns
    )
    prior_results = read_json(runtime / QBC_RESULTS_ARTIFACT)
    correction_family_size = max(
        1, int(prior_results.get("current_registered_result_count") or 0) + 1
    )
    corrected_p_value = min(1.0, raw_incremental_p_value * correction_family_size)
    stability = _instrument_stability(
        holdout, interaction_holdout_predictions, interaction_threshold
    )

    rejection_reasons: list[str] = []
    if int(interaction_metrics.get("trade_count") or 0) < MINIMUM_HOLDOUT_TRADES:
        rejection_reasons.append("insufficient_cost_eligible_holdout_decisions")
    if int(interaction_metrics.get("effective_block_count") or 0) < MINIMUM_EFFECTIVE_HOLDOUT_BLOCKS:
        rejection_reasons.append("insufficient_effectively_independent_holdout_blocks")
    if _number(interaction_metrics.get("mean_net_return"), -1.0) <= 0:
        rejection_reasons.append("nonpositive_cost_adjusted_holdout_return")
    if _number(incremental_uncertainty.get("mean"), -1.0) <= 0:
        rejection_reasons.append("interaction_did_not_beat_additive_classical_baseline")
    if corrected_p_value > 0.05:
        rejection_reasons.append("incremental_value_not_multiple_testing_significant")
    if stability.get("positive_measured_instrument_ratio", 0.0) < 0.60:
        rejection_reasons.append("cross_instrument_instability")
    if (
        interaction_metrics.get("maximum_drawdown") is not None
        and _number(interaction_metrics.get("maximum_drawdown")) < -0.25
    ):
        rejection_reasons.append("holdout_drawdown_exceeded")

    survived = not rejection_reasons
    status = (
        "tested_historical_survivor_requires_forward_shadow"
        if survived
        else "tested_rejected_no_predictive_value"
    )
    verdict = (
        "Historical test passed; real forward observation is still required."
        if survived
        else "The IBM finding did not survive the historical predictive test."
    )
    next_action = (
        "freeze_for_untouched_forward_shadow"
        if survived
        else "retain_as_rejected_research_evidence_no_strategy_change"
    )
    models = {
        "additive_classical": {
            "model": "ridge_with_instrument_and_horizon_controls",
            "parameter_count": baseline_model["parameter_count"],
            "coefficient_hash": baseline_model["coefficient_hash"],
            "selected_threshold": baseline_threshold,
            "selection_audit": baseline_tuning,
            "holdout_metrics": _clean_metrics(baseline_metrics),
        },
        "hardware_originated_interaction": {
            "model": "ridge_plus_frozen_causal_mapping_x_market_flow_interaction",
            "parameter_count": interaction_model["parameter_count"],
            "coefficient_hash": interaction_model["coefficient_hash"],
            "interaction_coefficient": interaction_model["interaction_coefficient"],
            "selected_threshold": interaction_threshold,
            "selection_audit": interaction_tuning,
            "holdout_metrics": _clean_metrics(interaction_metrics),
        },
    }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_ibm_hardware_candidate_validation",
        "generated_at": generated,
        "status": status,
        "experiment_id": result.get("experiment_id"),
        "hardware_receipt_hash": result.get("receipt_hash"),
        "hardware_manifest_hash": result.get("hardware_manifest_hash"),
        "candidate_id": candidate.get("candidate_id"),
        "research_question": candidate.get("research_question"),
        "feature_pair": feature_pair,
        "structural_score": candidate.get("structural_score"),
        "structural_score_is_probability": False,
        "structural_score_is_predictive_evidence": False,
        "candidate_selected_without_outcome_labels": True,
        "validation_protocol": {
            "protocol_version": "ibm_hardware_candidate_validation.v1.frozen",
            "target": "provider_backed_forward_price_return",
            "decision_metric": "cost_adjusted_long_or_short_counterfactual",
            "candidate_model": (
                "additive_ridge_plus_frozen_causal_mapping_strength_x_market_flow_interaction"
            ),
            "matched_baseline": "additive_ridge_without_interaction",
            "instrument_fixed_effects": True,
            "horizon_fixed_effects": True,
            "chronological_train_validation_holdout": True,
            "purge_and_embargo": True,
            "threshold_selected_without_holdout": True,
            "multiple_testing_control": "bonferroni_over_prior_registered_results_plus_this_test",
            "forward_shadow_required_even_if_historical_test_survives": True,
        },
        "input_audit": {
            **input_audit,
            "eligible_independent_cost_labeled_row_count": len(eligible),
            "input_score_id_set_hash": stable_hash(
                [str(row.get("score_id") or "") for row in eligible]
            ),
        },
        "split": split["audit"],
        "models": models,
        "comparison": {
            "opportunity_count": len(holdout),
            "interaction_minus_baseline_mean_net_return_per_opportunity": (
                incremental_uncertainty.get("mean")
            ),
            "incremental_standard_error": incremental_uncertainty.get(
                "standard_error"
            ),
            "effective_block_count": incremental_uncertainty.get(
                "effective_block_count"
            ),
            "raw_incremental_p_value": raw_incremental_p_value,
            "correction_family_size": correction_family_size,
            "multiple_testing_adjusted_p_value": corrected_p_value,
            "interaction_beats_additive_baseline": (
                _number(incremental_uncertainty.get("mean"), -1.0) > 0
            ),
            "multiple_testing_significant": corrected_p_value <= 0.05,
        },
        "stability": stability,
        "verdict": {
            "label": verdict,
            "historical_survivor": survived,
            "rejection_reasons": rejection_reasons,
            "validated_edge_created": False,
            "strategy_change_created": False,
            "akber_pass_created": False,
            "trade_candidate_created": False,
            "paper_order_created": False,
            "proof_credit_created": False,
            "next_action": next_action,
            "plain_english": (
                "Qadam tested the exact interaction surfaced by IBM hardware against "
                "future price moves that the circuit never saw. It compared the result "
                "with a simpler additive model, included trading costs, and kept the "
                "final candidate-specific period out of fitting and threshold selection. "
                + (
                    "The result is promising historical research, not a validated edge; "
                    "the frozen rule must now survive new market data."
                    if survived
                    else "The interaction did not clear every gate, so it will not change "
                    "a strategy or reach Akber."
                )
            ),
        },
        "research_only": True,
        "authority": _zero_authority(),
    }
    payload["content_hash"] = _content_hash(payload)
    errors = validate_hardware_candidate_validation(payload)
    if errors:
        raise ValueError("ibm_hardware_candidate_validation_invalid:" + ",".join(errors))
    return payload


def validate_hardware_candidate_validation(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_invalid")
    if payload.get("artifact_type") != "qadam_ibm_hardware_candidate_validation":
        errors.append("artifact_type_invalid")
    if payload.get("status") not in {
        "tested_historical_survivor_requires_forward_shadow",
        "tested_rejected_no_predictive_value",
    }:
        errors.append("status_invalid")
    if not payload.get("hardware_receipt_hash"):
        errors.append("hardware_receipt_hash_missing")
    if payload.get("feature_pair") != ["causal_mapping_strength", "market_flow"]:
        errors.append("feature_pair_invalid")
    if payload.get("candidate_selected_without_outcome_labels") is not True:
        errors.append("candidate_label_blindness_missing")
    split = payload.get("split") or {}
    if split.get("same_timestamp_cross_partition_count") != 0:
        errors.append("split_timestamp_overlap")
    if split.get("candidate_holdout_untouched_during_fit_and_threshold_selection") is not True:
        errors.append("candidate_holdout_not_untouched")
    comparison = payload.get("comparison") or {}
    if int(comparison.get("correction_family_size") or 0) <= 0:
        errors.append("multiple_testing_family_missing")
    verdict = payload.get("verdict") or {}
    for key in (
        "validated_edge_created",
        "strategy_change_created",
        "akber_pass_created",
        "trade_candidate_created",
        "paper_order_created",
        "proof_credit_created",
    ):
        if verdict.get(key) is not False:
            errors.append(f"authority_boundary_breached:{key}")
    authority = payload.get("authority") or {}
    for key in (
        "validated_edge_creation_allowed",
        "strategy_hypothesis_creation_allowed",
        "trade_candidate_creation_allowed",
        "risk_approval_allowed",
        "execution_approval_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
        "proof_credit_allowed",
        "live_capital_enabled",
        "hardware_scheduler_enabled",
        "automatic_paid_hardware_rerun_allowed",
    ):
        if authority.get(key) is not False:
            errors.append(f"authority_escalated:{key}")
    for key in ("paper_only", "proposal_first", "read_only"):
        if authority.get(key) is not True:
            errors.append(f"safety_posture_missing:{key}")
    if payload.get("content_hash") != _content_hash(payload):
        errors.append("content_hash_invalid")
    return errors


def build_and_write_hardware_candidate_validation(
    settings: Settings | None = None,
    *,
    generated_at: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    try:
        payload = build_hardware_candidate_validation(
            runtime, generated_at=generated_at
        )
        errors = validate_hardware_candidate_validation(payload)
    except (OSError, TypeError, ValueError) as exc:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_ibm_hardware_candidate_validation",
            "generated_at": generated_at or now_iso(),
            "status": "blocked",
            "error": str(exc),
            "research_only": True,
            "authority": _zero_authority(),
        }
        payload["content_hash"] = _content_hash(payload)
        errors = [str(exc)]
    write_json_atomic(runtime / VALIDATION_ARTIFACT, payload)
    checks = {
        "schema_version": CHECK_SCHEMA_VERSION,
        "artifact_type": "qadam_ibm_hardware_candidate_validation_checks",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if not errors else "failed",
        "acceptance_passed": not errors,
        "validation_status": payload.get("status"),
        "historical_survivor": (payload.get("verdict") or {}).get(
            "historical_survivor"
        ),
        "validated_edge_count": 0,
        "strategy_change_count": 0,
        "trade_candidate_count": 0,
        "paper_order_count": 0,
        "proof_credit_count": 0,
        "errors": errors,
        "authority": _zero_authority(),
    }
    write_json_atomic(runtime / CHECK_ARTIFACT, checks)
    return payload, checks, errors
