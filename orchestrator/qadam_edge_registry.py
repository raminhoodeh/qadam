"""OR-10 durable empirical edge registry and Strategy Evidence Map V3."""

from __future__ import annotations

from collections import Counter, defaultdict
from statistics import fmean
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_backtest_engine import (
    BASELINE_METHODS,
    MINIMUM_HOLDOUT_TRADES,
    NEGATIVE_CONTROL_METHODS,
    QADAM_METHODS,
)
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_wave_b_common import record_set_hash, stable_id

SCHEMA_VERSION = "qadam_edge_registry.v2"
PHASE_ID = "OR-10"

EDGE_REGISTRY_ARTIFACT = "qadam_edge_registry.jsonl"
EDGE_REGISTRY_V3_ARTIFACT = "qadam_edge_registry_v3.json"
PROMOTION_AUDIT_ARTIFACT = "qadam_edge_promotion_audit.json"
SUMMARY_ARTIFACT = "qadam_edge_registry_summary.json"
STRATEGY_MAP_ARTIFACT = "qadam_strategy_evidence_map_v3.json"
RETIREMENT_ARTIFACT = "qadam_strategy_retirement_proposals.jsonl"
NEW_FAMILY_ARTIFACT = "qadam_new_strategy_family_proposals.jsonl"
CHECK_ARTIFACT = "qadam_edge_registry_checks.json"

BACKTEST_SUMMARY_ARTIFACT = "qadam_backtest_results_summary.json"
BACKTEST_MANIFEST_ARTIFACT = "qadam_backtest_run_manifest.json"
QUANTUM_SUMMARY_ARTIFACT = "qadam_quantum_usefulness_summary.json"
QUANTUM_COMPARISONS_ARTIFACT = "qadam_quantum_classical_comparison.jsonl"
STRATEGY_UNIVERSE_ARTIFACT = "qsase_dashboard_strategy_universe.json"
SOURCE_OPERATIONAL_ARTIFACT = "qadam_source_operational_state.jsonl"
TRADING_UNIVERSE_ARTIFACT = "qsase_trading_universe.json"
SCORE_MANIFEST_ARTIFACT = "qadam_pattern_score_tape_manifest.json"
LABEL_MANIFEST_ARTIFACT = "qadam_forward_label_manifest.json"

ALLOWED_STRATEGY_CLASSES = {
    "evidence_backed",
    "exploratory",
    "under_evidenced",
    "degraded",
    "retired",
}
REQUIRED_EDGE_LINEAGE_FIELDS = (
    "score_version",
    "label_version",
    "fold_ids",
    "dataset_hashes",
    "backtest_run_id",
)


def _number(value: Any, default: float = 0.0) -> float:
    if value is None or isinstance(value, bool):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _mean(values: list[float]) -> float | None:
    return fmean(values) if values else None


def _strategy_rows(strategy_universe: dict[str, Any]) -> list[dict[str, Any]]:
    rows = strategy_universe.get("all_strategy_rows")
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _strategy_symbols(strategy: dict[str, Any]) -> set[str]:
    return {
        str(row.get("symbol"))
        for row in strategy.get("watched_markets", [])
        if isinstance(row, dict) and row.get("symbol")
    }


def _strategy_fit_vector(
    result: dict[str, Any], strategies: list[dict[str, Any]]
) -> dict[str, float]:
    explicit = str(result.get("strategy_family_id") or "")
    known = {
        str(strategy.get("strategy_family_id"))
        for strategy in strategies
        if strategy.get("strategy_family_id")
    }
    if explicit in known:
        return {explicit: 1.0}
    instrument = str(result.get("instrument") or "")
    matches = [
        str(strategy.get("strategy_family_id"))
        for strategy in strategies
        if instrument in _strategy_symbols(strategy)
    ]
    if not matches:
        return {}
    fit = round(1.0 / len(matches), 6)
    return {strategy_id: fit for strategy_id in sorted(matches)}


def _load_bulk_backtest_records(
    manifest: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    bulk = manifest.get("bulk_results")
    if not isinstance(bulk, dict) or bulk.get("written") is not True:
        raise ValueError("edge_registry_backtest_bulk_manifest_incomplete")
    research_root = (ROOT / "data" / "research" / "statistical_backtests").resolve()
    loaded: dict[str, list[dict[str, Any]]] = {}
    for kind, path_key, count_key, hash_key in (
        ("results", "result_path", "result_count", "result_record_set_hash"),
        ("folds", "fold_path", "fold_count", "fold_record_set_hash"),
    ):
        path = (ROOT / str(bulk.get(path_key) or "")).resolve()
        if not path.is_relative_to(research_root):
            raise ValueError(f"edge_registry_bulk_path_outside_research_store:{kind}")
        if not path.is_file():
            raise ValueError(f"edge_registry_bulk_path_missing:{kind}")
        records = read_jsonl(path)
        if len(records) != int(bulk.get(count_key) or 0):
            raise ValueError(f"edge_registry_bulk_count_mismatch:{kind}")
        if record_set_hash(records) != bulk.get(hash_key):
            raise ValueError(f"edge_registry_bulk_hash_mismatch:{kind}")
        loaded[kind] = records
    return loaded["results"], loaded["folds"]


def edge_admission_errors(result: dict[str, Any]) -> list[str]:
    """Return every fail-closed reason an OR-8 result cannot become an edge."""

    metrics = result.get("holdout_metrics")
    metrics = metrics if isinstance(metrics, dict) else {}
    errors: list[str] = []
    if result.get("historical_edge_candidate") is not True:
        errors.append("not_historical_edge_candidate")
    if result.get("status") != "historical_edge_candidate_after_holdout":
        errors.append("candidate_status_not_validated")
    if result.get("false_discovery_adjusted_state") != "validated":
        errors.append("false_discovery_adjustment_not_validated")
    if _number(result.get("adjusted_p_value"), 1.0) > 0.05:
        errors.append("adjusted_p_value_above_threshold")
    if result.get("holdout_untouched_during_tuning") is not True:
        errors.append("untouched_holdout_not_proven")
    if result.get("cost_adjusted") is not True:
        errors.append("cost_adjustment_missing")
    if result.get("negative_control") is True:
        errors.append("negative_control_cannot_be_edge")
    if int(metrics.get("trade_count") or 0) < MINIMUM_HOLDOUT_TRADES:
        errors.append("insufficient_holdout_trades")
    if _number(metrics.get("mean_net_return"), -1.0) <= 0:
        errors.append("nonpositive_holdout_net_expectancy")
    if result.get("rejection_reasons"):
        errors.append("backtest_rejection_reasons_present")
    return unique_errors(errors)


def _dominant_direction(metrics: dict[str, Any]) -> tuple[str, float]:
    counts = metrics.get("direction_counts")
    counts = counts if isinstance(counts, dict) else {}
    long_count = int(counts.get("long") or 0)
    short_count = int(counts.get("short") or 0)
    total = long_count + short_count
    if total == 0:
        return "undetermined", 0.0
    direction = "long" if long_count >= short_count else "short"
    return direction, round(max(long_count, short_count) / total, 6)


def _dominant_regime(metrics: dict[str, Any]) -> str:
    regimes = metrics.get("regime_mean_net_returns")
    if not isinstance(regimes, dict) or not regimes:
        return "all_observed_regimes"
    return max(
        ((str(regime), _number(value)) for regime, value in regimes.items()),
        key=lambda item: (item[1], item[0]),
    )[0]


def _source_concentration(metrics: dict[str, Any]) -> dict[str, Any]:
    counts = metrics.get("source_selected_counts")
    counts = counts if isinstance(counts, dict) else {}
    trade_count = max(1, int(metrics.get("trade_count") or 0))
    ratios = {
        str(source): round(int(count) / trade_count, 6) for source, count in sorted(counts.items())
    }
    return {
        "selected_trade_ratios": ratios,
        "maximum_selected_trade_ratio": max(ratios.values()) if ratios else None,
        "metric_is_selection_frequency_not_causal_credit": True,
    }


def _regime_stability(metrics: dict[str, Any]) -> dict[str, Any]:
    values = metrics.get("regime_mean_net_returns")
    values = values if isinstance(values, dict) else {}
    measured = {str(key): _number(value) for key, value in values.items()}
    return {
        "regime_mean_net_returns": measured,
        "positive_regime_count": sum(value > 0 for value in measured.values()),
        "measured_regime_count": len(measured),
        "positive_regime_ratio": (
            round(sum(value > 0 for value in measured.values()) / len(measured), 6)
            if measured
            else None
        ),
    }


def _tail_loss_proxy(metrics: dict[str, Any]) -> dict[str, Any]:
    regimes = metrics.get("regime_mean_net_returns")
    regimes = regimes if isinstance(regimes, dict) else {}
    return {
        "value": min((_number(value) for value in regimes.values()), default=None),
        "measure": "worst_observed_regime_mean_net_return_proxy",
        "var_or_cvar_materialized": False,
        "typed_limitation": "or8_result_does_not_materialize_per_trade_tail_distribution",
    }


def _incremental_context(
    comparisons: list[dict[str, Any]],
    *,
    instrument: str,
    horizon: str,
) -> dict[str, Any]:
    matched = [
        row
        for row in comparisons
        if row.get("instrument") == instrument
        and row.get("horizon") == horizon
        and row.get("method") != "time_shifted_target_negative_control"
    ]
    nonlinear = [row for row in matched if row.get("experiment_lane") == "classical_nonlinear"]
    quantum = [row for row in matched if row.get("experiment_lane") == "quantum_simulator"]
    best_nonlinear = max(
        nonlinear,
        key=lambda row: _number(row.get("incremental_holdout_value"), -1.0),
        default=None,
    )
    best_quantum = max(
        quantum,
        key=lambda row: _number(row.get("quantum_usefulness_score"), -1.0),
        default=None,
    )
    return {
        "best_nonlinear_method": None if best_nonlinear is None else best_nonlinear.get("method"),
        "best_nonlinear_incremental_holdout_value": (
            None if best_nonlinear is None else best_nonlinear.get("incremental_holdout_value")
        ),
        "best_nonlinear_verdict": None if best_nonlinear is None else best_nonlinear.get("verdict"),
        "quantum_usefulness_score": (
            None if best_quantum is None else best_quantum.get("quantum_usefulness_score")
        ),
        "quantum_incremental_holdout_value": (
            None if best_quantum is None else best_quantum.get("incremental_holdout_value")
        ),
        "quantum_verdict": None if best_quantum is None else best_quantum.get("verdict"),
        "physical_quantum_hardware_used": False,
    }


def build_edge_record(
    result: dict[str, Any],
    *,
    nonlinear_comparison: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one durable edge from a normalized, fully validated result."""

    required_state = result.get("false_discovery_adjusted_state") == "validated"
    holdout = result.get("untouched_holdout") is True
    costs = result.get("costs_included") is True
    if not (required_state and holdout and costs):
        raise ValueError("edge_result_missing_validation_gates")
    identity = {
        "source_feature_definition": result.get("source_feature_definition"),
        "instrument": result.get("instrument"),
        "direction": result.get("direction"),
        "horizon": result.get("horizon"),
        "regime": result.get("regime"),
    }
    if not all(identity.values()):
        raise ValueError("edge_identity_incomplete")
    edge_id = stable_id("edge-v3", identity)
    comparison = nonlinear_comparison or {}
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_edge_record",
        "edge_id": edge_id,
        **identity,
        "strategy_family_id": result.get("strategy_family_id"),
        "raw_score_definition": result.get("raw_score_definition"),
        "strategy_fit_vector": result.get("strategy_fit_vector", {}),
        "sample_size": result.get("sample_size"),
        "effective_sample_size": result.get("effective_sample_size"),
        "gross_expectancy": result.get("gross_expectancy"),
        "net_expectancy": result.get("net_expectancy"),
        "confidence_distribution": result.get("confidence_distribution"),
        "calibration_diagnostics": result.get("calibration_diagnostics"),
        "drawdown": result.get("drawdown"),
        "tail_loss": result.get("tail_loss"),
        "turnover": result.get("turnover"),
        "cost_sensitivity": result.get("cost_sensitivity"),
        "source_concentration": result.get("source_concentration"),
        "instrument_concentration": result.get("instrument_concentration"),
        "regime_stability": result.get("regime_stability"),
        "nonlinear_quantum_incremental_value": comparison,
        "decay_state": result.get("decay_state"),
        "latest_supporting_sample": result.get("latest_supporting_sample"),
        "promotion_class": "validated_research_edge",
        "falsifiers": result.get("falsifiers", []),
        "retirement_conditions": result.get("retirement_conditions", []),
        "score_version": result.get("score_version"),
        "label_version": result.get("label_version"),
        "fold_ids": result.get("fold_ids", []),
        "dataset_hashes": result.get("dataset_hashes", {}),
        "backtest_run_id": result.get("backtest_run_id"),
        "backtest_hypothesis_id": result.get("backtest_hypothesis_id"),
        "applied_learning_version_ids": result.get("applied_learning_version_ids", []),
        "stage1_learning_input_version": result.get("stage1_learning_input_version"),
        "paper_candidate_created": False,
        "qualified_setup_created": False,
        "order_created": False,
        "broker_write_allowed": False,
        "proof_credit_allowed": False,
        "strategy_mutation_allowed": False,
        "authority": authority_flags(),
    }


def _normalize_validated_result(
    result: dict[str, Any],
    *,
    strategies: list[dict[str, Any]],
    folds: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    backtest_manifest: dict[str, Any],
    score_manifest: dict[str, Any],
    label_manifest: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    admission_errors = edge_admission_errors(result)
    if admission_errors:
        raise ValueError("edge_result_missing_validation_gates:" + ",".join(admission_errors))
    metrics = result.get("holdout_metrics")
    metrics = metrics if isinstance(metrics, dict) else {}
    direction, direction_share = _dominant_direction(metrics)
    fit_vector = _strategy_fit_vector(result, strategies)
    best_strategy = max(fit_vector, key=fit_vector.get) if fit_vector else None
    fold_ids = [
        str(row.get("fold", {}).get("fold_id"))
        for row in folds
        if row.get("hypothesis_id") == result.get("hypothesis_id")
        and row.get("fold", {}).get("fold_id")
    ]
    incremental = _incremental_context(
        comparisons,
        instrument=str(result.get("instrument")),
        horizon=str(result.get("horizon")),
    )
    source_keys = sorted(str(value) for value in result.get("source_keys", []))
    normalized = {
        "false_discovery_adjusted_state": "validated",
        "untouched_holdout": True,
        "costs_included": True,
        "source_feature_definition": {
            "method_id": result.get("method_id"),
            "source_keys": source_keys,
            "definition": "point_in_time_source_price_features_to_forward_net_return",
        },
        "instrument": result.get("instrument"),
        "direction": direction,
        "direction_share": direction_share,
        "horizon": result.get("horizon"),
        "regime": _dominant_regime(metrics),
        "strategy_family_id": best_strategy,
        "raw_score_definition": {
            "model_version": score_manifest.get("model_version"),
            "feature_set_version": score_manifest.get("feature_set_version"),
            "method_id": result.get("method_id"),
            "score_is_probability": False,
        },
        "strategy_fit_vector": fit_vector,
        "sample_size": int(result.get("independent_row_count") or 0),
        "effective_sample_size": int(metrics.get("effective_block_count") or 0),
        "gross_expectancy": metrics.get("mean_gross_return"),
        "net_expectancy": metrics.get("mean_net_return"),
        "confidence_distribution": {
            "raw_p_value": result.get("raw_p_value"),
            "adjusted_p_value": result.get("adjusted_p_value"),
            "standard_error": metrics.get("standard_error"),
            "hit_rate": metrics.get("hit_rate"),
            "effective_block_count": metrics.get("effective_block_count"),
        },
        "calibration_diagnostics": {
            "prediction_is_probability": False,
            "probability_calibration_not_applicable": True,
            "incremental_mean_net_return_vs_unconditional": result.get(
                "incremental_mean_net_return_vs_unconditional"
            ),
            "unconditional_baseline_mean_net_return": result.get(
                "unconditional_baseline_mean_net_return"
            ),
        },
        "drawdown": metrics.get("maximum_drawdown"),
        "tail_loss": _tail_loss_proxy(metrics),
        "turnover": (
            round(
                int(metrics.get("trade_count") or 0) / int(metrics.get("eligible_row_count") or 1),
                6,
            )
        ),
        "cost_sensitivity": {
            "mean_cost_drag": metrics.get("mean_cost_drag"),
            "mean_gross_return": metrics.get("mean_gross_return"),
            "mean_net_return": metrics.get("mean_net_return"),
            "cost_model_version": label_manifest.get("cost_model_version"),
            "cost_model_hash": label_manifest.get("cost_model_hash"),
        },
        "source_concentration": _source_concentration(metrics),
        "instrument_concentration": 1.0,
        "regime_stability": _regime_stability(metrics),
        "decay_state": "current_as_of_latest_holdout_sample",
        "latest_supporting_sample": result.get("holdout_end_at"),
        "falsifiers": [
            "adjusted holdout significance no longer passes",
            "net expectancy becomes non-positive after current costs",
            "the relationship disappears outside its supporting regime",
            "source concentration rises beyond the reviewed limit",
        ],
        "retirement_conditions": [
            "two reviewed refreshes fail validation",
            "current paper proxy no longer represents the researched instrument",
            "operational source reliability invalidates the feature definition",
        ],
        "score_version": score_manifest.get("model_version"),
        "label_version": label_manifest.get("schema_version"),
        "fold_ids": fold_ids,
        "dataset_hashes": {
            "score_dataset_hash": backtest_manifest.get("score_dataset_hash"),
            "label_dataset_hash": backtest_manifest.get("label_dataset_hash"),
            "backtest_result_record_set_hash": backtest_manifest.get("bulk_results", {}).get(
                "result_record_set_hash"
            ),
            "backtest_fold_record_set_hash": backtest_manifest.get("bulk_results", {}).get(
                "fold_record_set_hash"
            ),
        },
        "backtest_run_id": backtest_manifest.get("run_id"),
        "backtest_hypothesis_id": result.get("hypothesis_id"),
        "applied_learning_version_ids": score_manifest.get("applied_learning_version_ids", []),
        "stage1_learning_input_version": score_manifest.get("stage1_learning_input_version"),
    }
    return normalized, incremental


def _result_is_relevant(result: dict[str, Any], strategy: dict[str, Any]) -> bool:
    strategy_id = str(strategy.get("strategy_family_id") or "")
    return result.get("strategy_family_id") == strategy_id or str(
        result.get("instrument") or ""
    ) in _strategy_symbols(strategy)


def _best_rejected_result(results: list[dict[str, Any]]) -> dict[str, Any] | None:
    measured = [
        row
        for row in results
        if row.get("method_id") in QADAM_METHODS and isinstance(row.get("holdout_metrics"), dict)
    ]
    if not measured:
        return None
    return min(
        measured,
        key=lambda row: (
            _number(row.get("adjusted_p_value"), 1.0),
            -_number(row.get("holdout_metrics", {}).get("mean_net_return"), -1.0),
            str(row.get("hypothesis_id")),
        ),
    )


def _effective_observation_count(results: list[dict[str, Any]]) -> int:
    by_group: dict[tuple[str, str], int] = {}
    for row in results:
        if row.get("method_id") not in QADAM_METHODS:
            continue
        key = (str(row.get("instrument")), str(row.get("horizon")))
        by_group[key] = max(by_group.get(key, 0), int(row.get("independent_row_count") or 0))
    return sum(by_group.values())


def _operational_sources(
    strategy: dict[str, Any], operational_by_key: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    keys = [str(value) for value in strategy.get("source_keywords", [])]
    rows = [operational_by_key.get(key, {}) for key in keys]
    return {
        "configured_source_count": len(keys),
        "fresh_source_count": sum(row.get("freshness_state") == "fresh" for row in rows),
        "stale_source_count": sum(row.get("freshness_state") == "stale" for row in rows),
        "offline_source_count": sum(row.get("freshness_state") == "offline" for row in rows),
        "quorum_eligible_source_count": sum(
            row.get("source_quorum_eligible") is True for row in rows
        ),
        "sources": [
            {
                "source_key": key,
                "freshness_state": operational_by_key.get(key, {}).get("freshness_state"),
                "failure_class": operational_by_key.get(key, {}).get("failure_class"),
                "source_quorum_eligible": operational_by_key.get(key, {}).get(
                    "source_quorum_eligible"
                ),
            }
            for key in keys
        ],
        "current_operational_state_is_not_historical_edge_proof": True,
    }


def _strategy_evidence_record(
    strategy: dict[str, Any],
    *,
    all_results: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    operational_by_key: dict[str, dict[str, Any]],
    trading_by_symbol: dict[str, dict[str, Any]],
    backtest_manifest: dict[str, Any],
    score_manifest: dict[str, Any],
    quantum_summary: dict[str, Any],
) -> dict[str, Any]:
    strategy_id = str(strategy.get("strategy_family_id") or "unknown")
    symbols = sorted(_strategy_symbols(strategy))
    results = [row for row in all_results if _result_is_relevant(row, strategy)]
    qadam_results = [row for row in results if row.get("method_id") in QADAM_METHODS]
    baseline_results = [row for row in results if row.get("method_id") in BASELINE_METHODS]
    controls = [row for row in results if row.get("method_id") in NEGATIVE_CONTROL_METHODS]
    edge_rows = [
        edge for edge in edges if _number(edge.get("strategy_fit_vector", {}).get(strategy_id)) > 0
    ]
    comparison_rows = [
        row
        for row in comparisons
        if str(row.get("instrument") or "") in symbols
        and row.get("method") != "time_shifted_target_negative_control"
    ]
    tested_symbols = sorted(
        {str(row.get("instrument")) for row in qadam_results if row.get("instrument")}
    )
    best = _best_rejected_result(qadam_results)
    best_metrics = best.get("holdout_metrics", {}) if best else {}
    best_nonlinear = max(
        (row for row in comparison_rows if row.get("experiment_lane") == "classical_nonlinear"),
        key=lambda row: _number(row.get("incremental_holdout_value"), -1.0),
        default=None,
    )
    best_quantum = max(
        (row for row in comparison_rows if row.get("experiment_lane") == "quantum_simulator"),
        key=lambda row: _number(row.get("quantum_usefulness_score"), -1.0),
        default=None,
    )
    if edge_rows:
        evidence_class = "evidence_backed"
        classification_reason = (
            f"{len(edge_rows)} relationship(s) survived the complete OR-8 and OR-9 evidence chain."
        )
        next_requirement = "refresh current-market evidence before Strategy Foundry review"
    elif qadam_results:
        evidence_class = "under_evidenced"
        classification_reason = (
            f"{len(qadam_results)} empirical method results were reviewed, but none became a "
            "false-discovery-controlled validated edge."
        )
        next_requirement = (
            "collect more independent point-in-time outcomes or improve the score definition, "
            "then rerun OR-8"
        )
    else:
        evidence_class = "exploratory"
        classification_reason = (
            "This configured strategy has no eligible provider-backed source-price result in the "
            "current OR-8 run."
        )
        next_requirement = (
            "acquire eligible historical instruments and source archives before testing"
        )

    source_operational = _operational_sources(strategy, operational_by_key)
    empirical_sources = sorted(
        {str(source) for row in qadam_results for source in row.get("source_keys", []) if source}
    )
    configured_sources = [str(value) for value in strategy.get("source_keywords", [])]
    paperable_symbols = [
        symbol
        for symbol in symbols
        if trading_by_symbol.get(symbol, {}).get("paper_route_available") is True
    ]
    failure_counts = Counter(
        reason for row in qadam_results for reason in row.get("rejection_reasons", [])
    )
    edge_net_values = [
        _number(edge.get("net_expectancy"))
        for edge in edge_rows
        if edge.get("net_expectancy") is not None
    ]
    edge_gross_values = [
        _number(edge.get("gross_expectancy"))
        for edge in edge_rows
        if edge.get("gross_expectancy") is not None
    ]
    return {
        "strategy_family_id": strategy_id,
        "label": strategy.get("label") or strategy_id,
        "evidence_class": evidence_class,
        "classification_reason": classification_reason,
        "next_evidence_requirement": next_requirement,
        "configured_dashboard_state": strategy.get("current_state"),
        "configured_dashboard_state_is_not_evidence": True,
        "edge_count": len(edge_rows),
        "edge_ids": [edge["edge_id"] for edge in edge_rows],
        "empirical_evidence": {
            "backtest_run_id": backtest_manifest.get("run_id"),
            "qadam_method_result_count": len(qadam_results),
            "baseline_result_count": len(baseline_results),
            "negative_control_result_count": len(controls),
            "adjusted_significant_result_count": sum(
                row.get("false_discovery_adjusted_state") == "validated" for row in qadam_results
            ),
            "historical_edge_candidate_count": sum(
                row.get("historical_edge_candidate") is True for row in qadam_results
            ),
            "effective_observation_count": _effective_observation_count(qadam_results),
            "tested_instruments": tested_symbols,
            "untested_configured_instruments": sorted(set(symbols) - set(tested_symbols)),
            "tested_methods": sorted(
                {str(row.get("method_id")) for row in qadam_results if row.get("method_id")}
            ),
            "result_record_set_hash": backtest_manifest.get("bulk_results", {}).get(
                "result_record_set_hash"
            ),
        },
        "raw_score_definitions": [
            {
                "method_id": method,
                "score_model_version": score_manifest.get("model_version"),
                "feature_set_version": score_manifest.get("feature_set_version"),
                "score_is_probability": False,
            }
            for method in sorted(
                {str(row.get("method_id")) for row in qadam_results if row.get("method_id")}
            )
        ],
        "source_contribution": {
            **source_operational,
            "configured_sources": configured_sources,
            "empirically_present_sources": empirical_sources,
            "configured_sources_present_in_backtest": sorted(
                set(configured_sources) & set(empirical_sources)
            ),
            "selection_frequency_is_not_causal_credit": True,
        },
        "instrument_contribution": {
            "configured_instrument_count": len(symbols),
            "tested_instrument_count": len(tested_symbols),
            "paperable_proxy_count": len(paperable_symbols),
            "paperable_proxy_symbols": paperable_symbols,
            "instruments": [
                {
                    "symbol": symbol,
                    "tested_in_or8": symbol in tested_symbols,
                    "market_family": trading_by_symbol.get(symbol, {}).get("market_family"),
                    "paper_route_available": trading_by_symbol.get(symbol, {}).get(
                        "paper_route_available"
                    ),
                    "paperability_state": trading_by_symbol.get(symbol, {}).get(
                        "paperability_state"
                    ),
                }
                for symbol in symbols
            ],
        },
        "sample_size": (sum(int(edge.get("sample_size") or 0) for edge in edge_rows) or None),
        "effective_sample_size": (
            sum(int(edge.get("effective_sample_size") or 0) for edge in edge_rows) or None
        ),
        "gross_expectancy": _mean(edge_gross_values),
        "net_expectancy": _mean(edge_net_values),
        "confidence_distribution": (
            None if not edge_rows else [edge.get("confidence_distribution") for edge in edge_rows]
        ),
        "best_observed_rejected_result": (
            None
            if best is None
            else {
                "hypothesis_id": best.get("hypothesis_id"),
                "method_id": best.get("method_id"),
                "instrument": best.get("instrument"),
                "horizon": best.get("horizon"),
                "mean_gross_return": best_metrics.get("mean_gross_return"),
                "mean_net_return": best_metrics.get("mean_net_return"),
                "adjusted_p_value": best.get("adjusted_p_value"),
                "rejection_reasons": best.get("rejection_reasons", []),
                "not_a_validated_expectancy": True,
            }
        ),
        "calibration_diagnostics": {
            "probability_calibration_applicable": False,
            "smallest_adjusted_p_value": min(
                (_number(row.get("adjusted_p_value"), 1.0) for row in qadam_results),
                default=None,
            ),
            "adjusted_significant_result_count": sum(
                row.get("false_discovery_adjusted_state") == "validated" for row in qadam_results
            ),
        },
        "drawdown_tail_loss": (
            None
            if not edge_rows
            else [
                {"drawdown": edge.get("drawdown"), "tail_loss": edge.get("tail_loss")}
                for edge in edge_rows
            ]
        ),
        "turnover_cost_sensitivity": (
            None
            if not edge_rows
            else [
                {"turnover": edge.get("turnover"), "cost_sensitivity": edge.get("cost_sensitivity")}
                for edge in edge_rows
            ]
        ),
        "failure_modes": [
            {"reason": reason, "result_count": count}
            for reason, count in failure_counts.most_common()
        ],
        "stale_data_sensitivity": {
            "current_stale_or_offline_configured_source_count": (
                source_operational["stale_source_count"]
                + source_operational["offline_source_count"]
            ),
            "historical_source_coverage_gap": sorted(
                set(configured_sources) - set(empirical_sources)
            ),
            "current_source_state_does_not_rewrite_historical_result": True,
        },
        "akber_sensitivity": {
            "akber_review_allowed": bool(edge_rows),
            "akber_pass_assumed": False,
            "reason": (
                "validated edge available for later current-context review"
                if edge_rows
                else "Akber cannot evaluate a deployment hypothesis before an edge exists"
            ),
        },
        "quantum_nonlinear_usefulness": {
            "or9_run_id": quantum_summary.get("run_id"),
            "best_nonlinear_method": (
                None if best_nonlinear is None else best_nonlinear.get("method")
            ),
            "best_nonlinear_incremental_holdout_value": (
                None if best_nonlinear is None else best_nonlinear.get("incremental_holdout_value")
            ),
            "best_nonlinear_verdict": (
                None if best_nonlinear is None else best_nonlinear.get("verdict")
            ),
            "quantum_usefulness_score": (
                None if best_quantum is None else best_quantum.get("quantum_usefulness_score")
            ),
            "quantum_verdict": (None if best_quantum is None else best_quantum.get("verdict")),
            "physical_hardware_used": False,
        },
        "paperability_limits": {
            "paper_attention_allowed": bool(edge_rows),
            "paper_order_allowed": False,
            "paperable_proxy_symbols": paperable_symbols,
            "guarded_paperops_route_required": True,
            "edge_registry_cannot_create_order": True,
        },
        "confidence_class": evidence_class,
        "decay_state": (
            "not_measurable_no_validated_edge" if not edge_rows else "measured_per_edge"
        ),
        "latest_supporting_sample": max(
            (str(edge.get("latest_supporting_sample")) for edge in edge_rows),
            default=None,
        ),
        "promotion_class": (
            "validated_research_edge_available" if edge_rows else "not_promoted_no_validated_edge"
        ),
        "deployment_priority": None,
        "paper_attention_allowed": bool(edge_rows),
        "strategy_mutation_allowed": False,
        "candidate_creation_allowed": False,
        "order_creation_allowed": False,
        "authority": authority_flags(),
    }


def _rank_deployment_priorities(strategy_records: list[dict[str, Any]]) -> None:
    eligible = [row for row in strategy_records if row.get("edge_count", 0) > 0]
    scored: list[tuple[float, str, dict[str, Any]]] = []
    for row in eligible:
        confidence = row.get("confidence_distribution") or []
        p_values = [
            _number(item.get("adjusted_p_value"), 1.0)
            for item in confidence
            if isinstance(item, dict)
        ]
        evidence_quality = 1.0 - min(p_values, default=1.0)
        instruments = row.get("instrument_contribution", {})
        paperability = _number(instruments.get("paperable_proxy_count")) / max(
            1.0, _number(instruments.get("configured_instrument_count"), 1.0)
        )
        sources = row.get("source_contribution", {})
        reliability = _number(sources.get("fresh_source_count")) / max(
            1.0, _number(sources.get("configured_source_count"), 1.0)
        )
        diversification = 1.0 / max(1.0, _number(row.get("edge_count"), 1.0))
        score = (
            0.40 * evidence_quality
            + 0.20 * paperability
            + 0.20 * reliability
            + 0.20 * diversification
        )
        scored.append((score, str(row.get("strategy_family_id")), row))
    for rank, (score, _strategy_id, row) in enumerate(
        sorted(scored, key=lambda item: (-item[0], item[1])), start=1
    ):
        row["deployment_priority"] = {
            "rank": rank,
            "score": round(score, 6),
            "components": [
                "evidence_quality",
                "paperability",
                "operational_reliability",
                "portfolio_diversification",
            ],
            "research_ranking_only_not_capital_allocation": True,
        }


def _proposal_for_unmapped_edge(edge: dict[str, Any], generated_at: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_new_strategy_family_proposal",
        "generated_at": generated_at,
        "proposal_id": stable_id("new-strategy-family-proposal", edge.get("edge_id")),
        "origin_edge_id": edge.get("edge_id"),
        "instrument": edge.get("instrument"),
        "direction": edge.get("direction"),
        "horizon": edge.get("horizon"),
        "reason": "validated edge does not map to a configured core strategy family",
        "operator_review_required": True,
        "strategy_created": False,
        "strategy_mutation_allowed": False,
        "candidate_creation_allowed": False,
        "order_creation_allowed": False,
        "authority": authority_flags(),
    }


def _promotion_audit_record(result: dict[str, Any]) -> dict[str, Any]:
    metrics = result.get("holdout_metrics")
    metrics = metrics if isinstance(metrics, dict) else {}
    admission_errors = edge_admission_errors(result)
    promoted = not admission_errors
    return {
        "hypothesis_id": result.get("hypothesis_id"),
        "method_id": result.get("method_id"),
        "instrument": result.get("instrument"),
        "horizon": result.get("horizon"),
        "source_keys": sorted(str(value) for value in result.get("source_keys", [])),
        "promotion_state": "promoted_validated_research_edge" if promoted else "rejected",
        "promotion_allowed": promoted,
        "historical_edge_candidate": result.get("historical_edge_candidate") is True,
        "false_discovery_adjusted_state": result.get("false_discovery_adjusted_state"),
        "raw_p_value": result.get("raw_p_value"),
        "adjusted_p_value": result.get("adjusted_p_value"),
        "independent_row_count": int(result.get("independent_row_count") or 0),
        "holdout_trade_count": int(metrics.get("trade_count") or 0),
        "holdout_mean_net_return": metrics.get("mean_net_return"),
        "holdout_maximum_drawdown": metrics.get("maximum_drawdown"),
        "admission_errors": admission_errors,
        "statistical_rejection_reasons": result.get("rejection_reasons", []),
        "dashboard_presence_used_as_evidence": False,
        "quantum_activity_used_as_substitute_for_evidence": False,
        "paper_candidate_created": False,
        "order_created": False,
    }


def build_edge_registry_state(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    backtest = read_json(runtime / BACKTEST_SUMMARY_ARTIFACT)
    backtest_manifest = read_json(runtime / BACKTEST_MANIFEST_ARTIFACT)
    quantum = read_json(runtime / QUANTUM_SUMMARY_ARTIFACT)
    comparisons = read_jsonl(runtime / QUANTUM_COMPARISONS_ARTIFACT)
    strategy_universe = read_json(runtime / STRATEGY_UNIVERSE_ARTIFACT)
    operational = read_jsonl(runtime / SOURCE_OPERATIONAL_ARTIFACT)
    trading = read_json(runtime / TRADING_UNIVERSE_ARTIFACT)
    score_manifest = read_json(runtime / SCORE_MANIFEST_ARTIFACT)
    label_manifest = read_json(runtime / LABEL_MANIFEST_ARTIFACT)
    results, folds = _load_bulk_backtest_records(backtest_manifest)
    strategies = _strategy_rows(strategy_universe)
    generated_at = now_iso()

    folds_by_hypothesis: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for fold in folds:
        folds_by_hypothesis[str(fold.get("hypothesis_id") or "")].append(fold)
    validated_results = [row for row in results if not edge_admission_errors(row)]
    edges: list[dict[str, Any]] = []
    for result in validated_results:
        normalized, incremental = _normalize_validated_result(
            result,
            strategies=strategies,
            folds=folds_by_hypothesis.get(str(result.get("hypothesis_id") or ""), []),
            comparisons=comparisons,
            backtest_manifest=backtest_manifest,
            score_manifest=score_manifest,
            label_manifest=label_manifest,
        )
        edges.append(build_edge_record(normalized, nonlinear_comparison=incremental))

    operational_by_key = {
        str(record.get("source_key")): record for record in operational if record.get("source_key")
    }
    trading_by_symbol = {
        str(record.get("symbol")): record
        for record in trading.get("instruments", [])
        if isinstance(record, dict) and record.get("symbol")
    }
    strategy_records = [
        _strategy_evidence_record(
            strategy,
            all_results=results,
            comparisons=comparisons,
            edges=edges,
            operational_by_key=operational_by_key,
            trading_by_symbol=trading_by_symbol,
            backtest_manifest=backtest_manifest,
            score_manifest=score_manifest,
            quantum_summary=quantum,
        )
        for strategy in strategies
    ]
    _rank_deployment_priorities(strategy_records)
    class_counts = Counter(record["evidence_class"] for record in strategy_records)
    unmapped_edges = [edge for edge in edges if not edge.get("strategy_fit_vector")]
    new_family_proposals = [
        _proposal_for_unmapped_edge(edge, generated_at) for edge in unmapped_edges
    ]
    retirement_proposals: list[dict[str, Any]] = []
    edge_count = len(edges)
    no_edge = edge_count == 0
    promotion_records = [_promotion_audit_record(result) for result in results]
    promotion_audit = {
        "schema_version": "qadam_edge_promotion_audit.v1",
        "artifact_type": "qadam_edge_promotion_audit",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "complete_with_promotions" if edges else "complete_no_edge_promoted",
        "backtest_run_id": backtest_manifest.get("run_id"),
        "reviewed_result_count": len(promotion_records),
        "promoted_result_count": sum(
            record["promotion_allowed"] for record in promotion_records
        ),
        "rejected_result_count": sum(
            not record["promotion_allowed"] for record in promotion_records
        ),
        "promotion_policy_frozen": True,
        "thresholds_relaxed_to_force_edge": False,
        "dashboard_presence_used_as_evidence_count": 0,
        "quantum_substitution_count": 0,
        "records": promotion_records,
        "authority": authority_flags(),
    }
    registry_v3 = {
        "schema_version": "qadam_edge_registry_v3.v1",
        "artifact_type": "qadam_edge_registry_v3",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": (
            "validated_research_edges_available"
            if edges
            else "empty_no_relationship_survived_promotion"
        ),
        "edge_count": edge_count,
        "validated_edge_count": edge_count,
        "paper_operator_edge_gate_passed": edge_count > 0,
        "valid_no_edge_outcome": no_edge,
        "backtest_run_id": backtest_manifest.get("run_id"),
        "edge_record_set_hash": record_set_hash(edges),
        "edges": edges,
        "boundary": (
            "Research edge registry only. An edge does not grant Akber pass, Router "
            "eligibility, PaperOps approval, an order, broker write, or proof credit."
        ),
        "authority": authority_flags(),
    }
    summary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_edge_registry_summary",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": (
            "edge_registry_complete_with_validated_edges"
            if edges
            else "edge_registry_complete_no_validated_edge"
        ),
        "implementation_complete": True,
        "edge_count": edge_count,
        "validated_edge_count": edge_count,
        "edge_validated_certification_passed": edge_count > 0,
        "paper_operator_ready_certification_passed": False,
        "valid_no_edge_outcome": no_edge,
        "research_outcome": (
            "No tested relationship currently qualifies as a validated edge."
            if no_edge
            else f"{edge_count} tested relationship(s) qualify as validated research edges."
        ),
        "backtest_status": backtest.get("status"),
        "backtest_result_count": len(results),
        "backtest_rejected_result_count": len(results) - len(validated_results),
        "backtest_validated_edge_count": int(backtest.get("validated_edge_count") or 0),
        "backtest_historical_candidate_count": int(
            backtest.get("historical_edge_candidate_count") or 0
        ),
        "backtest_run_id": backtest_manifest.get("run_id"),
        "backtest_result_record_set_hash": record_set_hash(results),
        "backtest_fold_record_set_hash": record_set_hash(folds),
        "quantum_incremental_value_state": quantum.get("status"),
        "quantum_run_id": quantum.get("run_id"),
        "quantum_comparison_count": len(comparisons),
        "or9_input_matches_or8": (
            quantum.get("input_audit", {}).get("score_dataset_hash")
            == backtest_manifest.get("score_dataset_hash")
            and quantum.get("input_audit", {}).get("label_dataset_hash")
            == backtest_manifest.get("label_dataset_hash")
        ),
        "strategy_count": len(strategy_records),
        "strategy_class_counts": dict(sorted(class_counts.items())),
        "paper_attention_strategy_count": sum(
            record["paper_attention_allowed"] for record in strategy_records
        ),
        "strategy_promoted_because_dashboard_exists_count": 0,
        "retirement_proposal_count": len(retirement_proposals),
        "new_family_proposal_count": len(new_family_proposals),
        "unmapped_validated_edge_count": len(unmapped_edges),
        "candidate_created_count": 0,
        "qualified_setup_created_count": 0,
        "order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "paper_calendar_advanced": False,
        "paperops_watch_only_mode": True,
        "authority": authority_flags(),
    }
    strategy_map = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_strategy_evidence_map_v3",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": (
            "strategy_map_complete_with_evidence_backed_families"
            if edges
            else "strategy_map_complete_no_evidence_backed_family"
        ),
        "strategy_count": len(strategy_records),
        "strategies": strategy_records,
        "evidence_contract": {
            "source_of_strategy_maturity": "or8_backtest_results_and_or9_matched_comparisons",
            "dashboard_configuration_is_not_evidence": True,
            "rejected_results_may_explain_maturity_but_cannot_create_edges": True,
            "only_validated_edge_records_may_enable_paper_attention": True,
        },
        "deployment_priority_policy": [
            "evidence_quality",
            "liquidity",
            "paperability",
            "operational_reliability",
            "portfolio_diversification",
        ],
        "deployment_priority_ranked_strategy_count": sum(
            record.get("deployment_priority") is not None for record in strategy_records
        ),
        "crude_oil_first_validation_sleeve_assumed": False,
        "crude_oil_first_validation_requires_new_evidence": not any(
            record.get("strategy_family_id") == "crude_oil_energy_security_disruption"
            and record.get("edge_count", 0) > 0
            for record in strategy_records
        ),
        "trading_universe_instrument_count": len(trading.get("instruments", [])),
        "strategy_mutation_allowed": False,
        "candidate_creation_allowed": False,
        "order_creation_allowed": False,
        "authority": authority_flags(),
    }
    return {
        "edges": edges,
        "summary": summary,
        "strategy_map": strategy_map,
        "retirement_proposals": retirement_proposals,
        "new_family_proposals": new_family_proposals,
        "registry_v3": registry_v3,
        "promotion_audit": promotion_audit,
    }


def validate_edge_registry_state(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    edges = state["edges"]
    summary = state["summary"]
    strategy_map = state["strategy_map"]
    strategies = strategy_map.get("strategies", [])
    retirement = state["retirement_proposals"]
    new_families = state["new_family_proposals"]
    registry_v3 = state["registry_v3"]
    promotion_audit = state["promotion_audit"]
    if len(strategies) != 5:
        errors.append("strategy_evidence_map_not_five_core_strategies")
    if sum(summary.get("strategy_class_counts", {}).values()) != len(strategies):
        errors.append("strategy_class_counts_incomplete")
    edge_ids = [str(edge.get("edge_id") or "") for edge in edges]
    if any(not edge_id for edge_id in edge_ids) or len(edge_ids) != len(set(edge_ids)):
        errors.append("edge_id_missing_or_duplicate")
    for record in strategies:
        strategy_id = record.get("strategy_family_id")
        if record.get("evidence_class") not in ALLOWED_STRATEGY_CLASSES:
            errors.append(f"strategy_evidence_class_invalid:{strategy_id}")
        if record.get("configured_dashboard_state_is_not_evidence") is not True:
            errors.append(f"strategy_dashboard_state_used_as_evidence:{strategy_id}")
        empirical = record.get("empirical_evidence")
        if not isinstance(empirical, dict) or not empirical.get("backtest_run_id"):
            errors.append(f"strategy_empirical_lineage_missing:{strategy_id}")
        if not record.get("edge_ids") and record.get("paper_attention_allowed") is not False:
            errors.append(f"strategy_without_edge_allowed_paper_attention:{strategy_id}")
        if record.get("evidence_class") == "evidence_backed" and not record.get("edge_ids"):
            errors.append(f"strategy_evidence_backed_without_edge:{strategy_id}")
        if record.get("edge_ids") and record.get("evidence_class") != "evidence_backed":
            errors.append(f"strategy_with_edge_not_evidence_backed:{strategy_id}")
        for key in (
            "strategy_mutation_allowed",
            "candidate_creation_allowed",
            "order_creation_allowed",
        ):
            if record.get(key) is not False:
                errors.append(f"strategy_map_unsafe_flag:{strategy_id}:{key}")
        errors.extend(validate_authority(record.get("authority", {}), prefix="strategy_map"))
    if not edges and summary.get("edge_validated_certification_passed") is not False:
        errors.append("empty_edge_registry_falsely_certified")
    if not edges and summary.get("paper_operator_ready_certification_passed") is not False:
        errors.append("empty_edge_registry_falsely_paper_ready")
    if summary.get("strategy_promoted_because_dashboard_exists_count") != 0:
        errors.append("strategy_promoted_from_dashboard_presence")
    if int(promotion_audit.get("reviewed_result_count") or 0) != int(
        summary.get("backtest_result_count") or 0
    ):
        errors.append("edge_promotion_audit_result_count_mismatch")
    if int(promotion_audit.get("promoted_result_count") or 0) != len(edges):
        errors.append("edge_promotion_audit_promoted_count_mismatch")
    if promotion_audit.get("thresholds_relaxed_to_force_edge") is not False:
        errors.append("edge_promotion_thresholds_relaxed")
    if int(registry_v3.get("edge_count") or 0) != len(edges):
        errors.append("edge_registry_v3_count_mismatch")
    if registry_v3.get("paper_operator_edge_gate_passed") is not bool(edges):
        errors.append("edge_registry_v3_paper_gate_mismatch")
    for key in (
        "candidate_created_count",
        "qualified_setup_created_count",
        "order_created_count",
        "broker_write_count",
        "proof_credit_created_count",
    ):
        if int(summary.get(key) or 0) != 0:
            errors.append(f"edge_registry_created_forbidden_output:{key}")
    if summary.get("paper_calendar_advanced") is not False:
        errors.append("edge_registry_advanced_paper_calendar")
    if int(summary.get("backtest_validated_edge_count") or 0) != len(edges):
        errors.append("edge_registry_backtest_validated_count_mismatch")
    if summary.get("or9_input_matches_or8") is not True:
        errors.append("edge_registry_or9_input_does_not_match_or8")
    for edge in edges:
        for field in REQUIRED_EDGE_LINEAGE_FIELDS:
            if not edge.get(field):
                errors.append(f"edge_lineage_missing:{edge.get('edge_id')}:{field}")
        if edge.get("promotion_class") != "validated_research_edge":
            errors.append(f"edge_promotion_class_invalid:{edge.get('edge_id')}")
        for key in (
            "paper_candidate_created",
            "qualified_setup_created",
            "order_created",
            "broker_write_allowed",
            "proof_credit_allowed",
            "strategy_mutation_allowed",
        ):
            if edge.get(key) is not False:
                errors.append(f"edge_unsafe_flag:{edge.get('edge_id')}:{key}")
        errors.extend(validate_authority(edge.get("authority", {}), prefix="edge"))
    for proposal in [*retirement, *new_families]:
        if proposal.get("strategy_mutation_allowed") is not False:
            errors.append("strategy_proposal_mutation_allowed")
        if proposal.get("candidate_creation_allowed") is not False:
            errors.append("strategy_proposal_candidate_allowed")
        if proposal.get("order_creation_allowed") is not False:
            errors.append("strategy_proposal_order_allowed")
        errors.extend(validate_authority(proposal.get("authority", {}), prefix="strategy_proposal"))
    unmapped = [edge for edge in edges if not edge.get("strategy_fit_vector")]
    proposed_edge_ids = {proposal.get("origin_edge_id") for proposal in new_families}
    if any(edge.get("edge_id") not in proposed_edge_ids for edge in unmapped):
        errors.append("unmapped_validated_edge_missing_new_family_proposal")
    if (
        strategy_map.get("evidence_contract", {}).get("dashboard_configuration_is_not_evidence")
        is not True
    ):
        errors.append("strategy_map_dashboard_configuration_evidence_boundary_missing")
    for key in (
        "strategy_mutation_allowed",
        "candidate_creation_allowed",
        "order_creation_allowed",
    ):
        if strategy_map.get(key) is not False:
            errors.append(f"strategy_map_primary_unsafe_flag:{key}")
    errors.extend(validate_authority(summary.get("authority", {}), prefix="edge_summary"))
    errors.extend(
        validate_authority(strategy_map.get("authority", {}), prefix="strategy_map_primary")
    )
    errors.extend(
        validate_authority(registry_v3.get("authority", {}), prefix="edge_registry_v3")
    )
    errors.extend(
        validate_authority(
            promotion_audit.get("authority", {}), prefix="edge_promotion_audit"
        )
    )
    return unique_errors(errors)


def build_and_write_edge_registry(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    state = build_edge_registry_state(settings)
    store.write_jsonl(EDGE_REGISTRY_ARTIFACT, state["edges"])
    store.write_json(SUMMARY_ARTIFACT, state["summary"])
    store.write_json(STRATEGY_MAP_ARTIFACT, state["strategy_map"])
    store.write_jsonl(RETIREMENT_ARTIFACT, state["retirement_proposals"])
    store.write_jsonl(NEW_FAMILY_ARTIFACT, state["new_family_proposals"])
    store.write_json(EDGE_REGISTRY_V3_ARTIFACT, state["registry_v3"])
    store.write_json(PROMOTION_AUDIT_ARTIFACT, state["promotion_audit"])
    errors = validate_edge_registry_state(state)
    acceptance_passed = not errors and state["summary"].get("implementation_complete") is True
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_edge_registry_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if acceptance_passed else "blocked",
        "implementation_ready": acceptance_passed,
        "acceptance_passed": acceptance_passed,
        "edge_count": state["summary"]["edge_count"],
        "edge_validated_certification_passed": state["summary"][
            "edge_validated_certification_passed"
        ],
        "paper_operator_ready_certification_passed": state["summary"][
            "paper_operator_ready_certification_passed"
        ],
        "valid_no_edge_outcome": state["summary"]["valid_no_edge_outcome"],
        "backtest_result_count": state["summary"]["backtest_result_count"],
        "backtest_rejected_result_count": state["summary"]["backtest_rejected_result_count"],
        "or9_input_matches_or8": state["summary"]["or9_input_matches_or8"],
        "strategy_count": state["summary"]["strategy_count"],
        "strategy_class_counts": state["summary"]["strategy_class_counts"],
        "paper_attention_strategy_count": state["summary"]["paper_attention_strategy_count"],
        "evidence_backed_strategy_count": sum(
            record["evidence_class"] == "evidence_backed"
            for record in state["strategy_map"]["strategies"]
        ),
        "exploratory_strategy_count": sum(
            record["evidence_class"] == "exploratory"
            for record in state["strategy_map"]["strategies"]
        ),
        "under_evidenced_strategy_count": sum(
            record["evidence_class"] == "under_evidenced"
            for record in state["strategy_map"]["strategies"]
        ),
        "retirement_proposal_count": state["summary"]["retirement_proposal_count"],
        "new_family_proposal_count": state["summary"]["new_family_proposal_count"],
        "candidate_created_count": state["summary"]["candidate_created_count"],
        "qualified_setup_created_count": state["summary"]["qualified_setup_created_count"],
        "order_created_count": state["summary"]["order_created_count"],
        "broker_write_count": state["summary"]["broker_write_count"],
        "proof_credit_created_count": state["summary"]["proof_credit_created_count"],
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    store.write_json(CHECK_ARTIFACT, checks)
    return state, checks, errors
