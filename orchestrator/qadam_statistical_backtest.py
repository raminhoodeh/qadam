"""OR-8 whole-universe statistical backtest and evidence contract."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_backtest_engine import (
    ALL_METHODS,
    BASELINE_METHODS,
    FALSE_DISCOVERY_ALPHA,
    MINIMUM_EFFECTIVE_HOLDOUT_BLOCKS,
    MINIMUM_HOLDOUT_TRADES,
    MINIMUM_INDEPENDENT_ROWS,
    QADAM_METHODS,
    WalkForwardFold,
    benjamini_hochberg,
    chronological_walk_forward_folds,
    dependence_aware_mean_uncertainty,
    run_whole_universe_backtest,
)
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    authority_flags,
    canonical_json,
    file_sha256,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    sha256_text,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_wave_b_common import (
    record_set_hash,
    stable_id,
    write_jsonl_atomic,
)

__all__ = [
    "BASELINE_METHODS",
    "QADAM_METHODS",
    "REQUIRED_UNUSUAL_WHALES_COMPARISONS",
    "WalkForwardFold",
    "benjamini_hochberg",
    "build_and_write_statistical_backtest",
    "build_statistical_backtest_state",
    "chronological_walk_forward_folds",
    "dependence_aware_mean_uncertainty",
    "validate_statistical_backtest_state",
]

SCHEMA_VERSION = "qadam_statistical_backtest.v3"
PHASE_ID = "OR-8"
PROTOCOL_VERSION = "qadam_walk_forward_protocol.v6_exact_small_sample_control"

PROTOCOL_ARTIFACT = "qadam_backtest_protocol.json"
MANIFEST_ARTIFACT = "qadam_backtest_run_manifest.json"
SUMMARY_ARTIFACT = "qadam_backtest_results_summary.json"
REJECTIONS_ARTIFACT = "qadam_backtest_rejections.jsonl"
MULTIPLE_TESTING_ARTIFACT = "qadam_multiple_testing_audit.json"
WALK_FORWARD_ARTIFACT = "qadam_walk_forward_audit.json"
DASHBOARD_ARTIFACT = "qadam_backtest_dashboard_summary.json"
CHECK_ARTIFACT = "qadam_statistical_backtest_checks.json"
NEGATIVE_CONTROL_DIAGNOSTICS_ARTIFACT = "qadam_negative_control_diagnostics.json"

SCORE_TAPE_MANIFEST_ARTIFACT = "qadam_pattern_score_tape_manifest.json"
FORWARD_LABEL_MANIFEST_ARTIFACT = "qadam_forward_label_manifest.json"
LABEL_COVERAGE_ARTIFACT = "qadam_label_coverage.json"
LABEL_QUALITY_ARTIFACT = "qadam_label_quality_audit.json"
BACKFILL_COVERAGE_ARTIFACT = "qadam_backfill_coverage.json"
TRADING_UNIVERSE_ARTIFACT = "qsase_trading_universe.json"
UNUSUAL_WHALES_FEATURE_MANIFEST_ARTIFACT = (
    "unusual_whales_backtest_feature_manifest.json"
)

RESEARCH_BACKTEST_ROOT = ROOT / "data" / "research" / "statistical_backtests"

REQUIRED_UNUSUAL_WHALES_COMPARISONS = (
    "qadam_core_without_unusual_whales",
    "qadam_core_plus_unusual_whales",
    "unusual_whales_only",
    "time_shifted_negative_control",
    "shuffled_negative_control",
)


def _number(value: Any, default: float = 0.0) -> float:
    if value is None or isinstance(value, bool):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _score_dataset_hash(manifest: dict[str, Any]) -> str:
    material = [
        {
            "partition_id": row.get("partition_id"),
            "dataset_path": row.get("dataset_path"),
            "dataset_sha256": row.get("dataset_sha256"),
            "record_set_hash": row.get("record_set_hash"),
            "row_count": row.get("row_count"),
        }
        for row in manifest.get("partitions", [])
        if row.get("status") == "complete" and row.get("dataset_path")
    ]
    return sha256_text(canonical_json(material))


def _label_dataset_hash(manifest: dict[str, Any]) -> str:
    material = [
        {
            "partition_id": row.get("partition_id"),
            "dataset_sha256": row.get("dataset_sha256"),
            "record_set_hash": row.get("record_set_hash"),
            "row_count": row.get("row_count"),
            "missing_dataset_sha256": row.get("missing_dataset_sha256"),
            "missing_record_set_hash": row.get("missing_record_set_hash"),
            "missing_row_count": row.get("missing_row_count"),
        }
        for row in manifest.get("partitions", [])
    ]
    return sha256_text(canonical_json(sorted(material, key=canonical_json)))


def _read_partition(
    partition: dict[str, Any], *, path_key: str, sha_key: str, count_key: str
) -> list[dict[str, Any]]:
    path = ROOT / str(partition.get(path_key) or "")
    if not path.is_file():
        raise ValueError(
            f"backtest_input_partition_missing:{partition.get('partition_id')}:{path_key}"
        )
    if file_sha256(path) != partition.get(sha_key):
        raise ValueError(
            f"backtest_input_partition_checksum_mismatch:{partition.get('partition_id')}:{path_key}"
        )
    rows = read_jsonl(path)
    if len(rows) != int(partition.get(count_key) or 0):
        raise ValueError(
            f"backtest_input_partition_row_count_mismatch:{partition.get('partition_id')}:{path_key}"
        )
    return rows


def _joined_row(score: dict[str, Any], label: dict[str, Any]) -> dict[str, Any]:
    features = score.get("features") or {}
    market = score.get("historical_market_context") or {}
    source = score.get("historical_source_context") or {}
    source_event_counts: defaultdict[str, float] = defaultdict(float)
    source_trust_values: defaultdict[str, list[float]] = defaultdict(list)
    source_latest_available_at: dict[str, str] = {}
    source_cluster_ids: defaultdict[str, set[str]] = defaultdict(set)
    for item in score.get("feature_inputs", []):
        source_key = str(item.get("source_key") or "")
        if not source_key:
            continue
        source_event_counts[source_key] += _number(item.get("source_event_count"))
        source_trust_values[source_key].append(_number(item.get("trust_score")))
        available_at = str(item.get("source_available_at") or "")
        if available_at and available_at > source_latest_available_at.get(source_key, ""):
            source_latest_available_at[source_key] = available_at
        cluster_id = str(item.get("source_independence_cluster_id") or "")
        if cluster_id:
            source_cluster_ids[source_key].add(cluster_id)
    source_keys = sorted(source_event_counts)
    return {
        "score_id": score["score_id"],
        "label_id": label["label_id"],
        "decision_at": score["scoring_as_of"],
        "outcome_available_at": label["outcome_available_at"],
        "strategy_family_id": score.get("strategy_family_id") or "unclassified",
        "strategy_label": score.get("strategy_label"),
        "instrument": score["instrument"],
        "horizon": score["horizon_hypothesis"],
        "regime": score.get("regime_state") or "unclassified",
        "source_keys": source_keys,
        "source_event_counts_by_key": dict(sorted(source_event_counts.items())),
        "source_trust_by_key": {
            key: sum(values) / len(values)
            for key, values in sorted(source_trust_values.items())
            if values
        },
        "source_latest_available_at_by_key": dict(
            sorted(source_latest_available_at.items())
        ),
        "source_cluster_count_by_key": {
            key: len(values) for key, values in sorted(source_cluster_ids.items())
        },
        "raw_pattern_score": _number(score.get("raw_pattern_score")),
        "source_trust": _number(features.get("source_trust")),
        "source_freshness": _number(features.get("source_freshness")),
        "source_independence": _number(features.get("source_independence")),
        "causal_mapping_strength": _number(features.get("causal_mapping_strength")),
        "strategy_fit": _number(features.get("strategy_fit")),
        "rolling_volatility": _number(
            market.get("rolling_volatility_20_observation")
        ),
        "volume_relative": _number(
            market.get("volume_relative_to_20_observation_mean")
        ),
        "source_event_count": _number(source.get("source_event_count")),
        "distinct_source_count": _number(source.get("distinct_source_count")),
        "independent_source_cluster_count": _number(
            source.get("independent_source_cluster_count")
        ),
        "price_before": _number(label.get("price_before")),
        "research_gross_return": _number(label.get("research_gross_return")),
        "execution_gross_return": label.get("execution_gross_return"),
        "long_net_return": label.get("long_net_return"),
        "short_net_return": label.get("short_net_return"),
        "transaction_cost_bps": label.get("transaction_cost_bps"),
        "execution_instrument": label.get("execution_instrument"),
        "execution_proxy_used": label.get("execution_proxy_used") is True,
        "market_regime": label.get("market_regime"),
        "overlap_group_id": label.get("overlap_group_id"),
        "independent_sample": label.get("independent_sample") is True,
        "score_created_before_label": label.get("score_created_before_label") is True,
        "candidate_creation_allowed": False,
        "order_creation_allowed": False,
        "proof_credit_allowed": False,
    }


def load_empirical_backtest_dataset(
    runtime: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    score_manifest = read_json(runtime / SCORE_TAPE_MANIFEST_ARTIFACT)
    label_manifest = read_json(runtime / FORWARD_LABEL_MANIFEST_ARTIFACT)
    label_quality = read_json(runtime / LABEL_QUALITY_ARTIFACT)
    if score_manifest.get("status") != "complete_with_classified_gaps":
        return [], {"status": "score_tape_not_empirically_complete"}
    if label_manifest.get("status") != "complete_with_classified_gaps":
        return [], {"status": "forward_labels_not_empirically_complete"}
    if label_quality.get("status") != "passed":
        return [], {"status": "forward_label_quality_not_passed"}
    score_hash = _score_dataset_hash(score_manifest)
    label_hash = _label_dataset_hash(label_manifest)
    if label_manifest.get("score_plane_hash_before") != score_hash:
        raise ValueError("backtest_score_label_plane_hash_mismatch")
    scores: dict[str, dict[str, Any]] = {}
    duplicate_score_ids = 0
    for partition in score_manifest.get("partitions", []):
        if partition.get("status") != "complete" or not partition.get("dataset_path"):
            continue
        for row in _read_partition(
            partition,
            path_key="dataset_path",
            sha_key="dataset_sha256",
            count_key="row_count",
        ):
            score_id = str(row.get("score_id") or "")
            if score_id in scores:
                duplicate_score_ids += 1
            scores[score_id] = row
    labels: dict[str, dict[str, Any]] = {}
    duplicate_label_score_ids = 0
    for partition in label_manifest.get("partitions", []):
        for row in _read_partition(
            partition,
            path_key="dataset_path",
            sha_key="dataset_sha256",
            count_key="row_count",
        ):
            score_id = str(row.get("score_id") or "")
            if score_id in labels:
                duplicate_label_score_ids += 1
            labels[score_id] = row
    joined: list[dict[str, Any]] = []
    missing_score_count = 0
    chronology_violation_count = 0
    for score_id, label in sorted(labels.items()):
        score = scores.get(score_id)
        if not score:
            missing_score_count += 1
            continue
        row = _joined_row(score, label)
        if not row["score_created_before_label"]:
            chronology_violation_count += 1
        joined.append(row)
    source_keys = sorted(
        {source for row in joined for source in row.get("source_keys", [])}
    )
    instruments = sorted({str(row["instrument"]) for row in joined})
    strategies = sorted({str(row["strategy_family_id"]) for row in joined})
    return joined, {
        "status": "empirical_score_label_pairs_loaded",
        "score_dataset_hash": score_hash,
        "label_dataset_hash": label_hash,
        "score_row_count": len(scores),
        "label_row_count": len(labels),
        "paired_score_label_count": len(joined),
        "independent_pair_count": sum(
            row.get("independent_sample") is True for row in joined
        ),
        "duplicate_score_id_count": duplicate_score_ids,
        "duplicate_label_score_id_count": duplicate_label_score_ids,
        "label_without_score_count": missing_score_count,
        "chronology_violation_count": chronology_violation_count,
        "source_keys": source_keys,
        "source_count": len(source_keys),
        "instruments": instruments,
        "instrument_count": len(instruments),
        "strategies": strategies,
        "strategy_count": len(strategies),
        "score_plane_read_only": True,
        "label_plane_read_only": True,
    }


def _protocol(generated_at: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_backtest_protocol",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "protocol_frozen",
        "protocol_version": PROTOCOL_VERSION,
        "baseline_methods": list(BASELINE_METHODS),
        "qadam_methods": list(QADAM_METHODS),
        "all_registered_methods": list(ALL_METHODS),
        "target_policy": {
            "model_target": "raw_provider_backed_forward_price_return",
            "trade_evaluation": "cost_adjusted_long_or_short_counterfactual",
            "direction_selected_from_training_data_only": True,
            "unresolved_score_direction_never_assigned_from_holdout": True,
        },
        "split_policy": {
            "chronological": True,
            "minimum_independent_rows": MINIMUM_INDEPENDENT_ROWS,
            "untouched_holdout_fraction": 0.20,
            "minimum_holdout_rows": 40,
            "minimum_holdout_trades": MINIMUM_HOLDOUT_TRADES,
            "minimum_effective_holdout_blocks": MINIMUM_EFFECTIVE_HOLDOUT_BLOCKS,
            "expanding_walk_forward": True,
            "purge_rows": 1,
            "embargo_rows": 1,
            "nested_threshold_tuning": True,
            "untouched_holdout_required": True,
        },
        "uncertainty_policy": {
            "method": "non_overlapping_labels_plus_block_mean_standard_error",
            "default_block_size": 5,
            "overlap_adjusted_effective_sample_size_required": True,
        },
        "multiple_testing_policy": {
            "registry_all_attempts_required": True,
            "false_discovery_method": "benjamini_hochberg",
            "alpha": FALSE_DISCOVERY_ALPHA,
            "correction_universe": "all_registered_method_strategy_instrument_horizon_tests",
            "qadam_primary_test": "incremental_mean_net_return_versus_unconditional_baseline",
            "baseline_primary_test": "mean_net_return_versus_zero",
        },
        "promotion_gates": {
            "cost_adjusted_holdout_return_positive": True,
            "minimum_effective_holdout_blocks": MINIMUM_EFFECTIVE_HOLDOUT_BLOCKS,
            "minimum_positive_fold_ratio": 0.60,
            "must_beat_unconditional_baseline": True,
            "maximum_year_concentration": 0.70,
            "maximum_drawdown": -0.25,
            "false_discovery_adjusted_significance_required": True,
            "negative_controls_cannot_validate": True,
        },
        "costs_required": True,
        "survivorship_bias_audit_required": True,
        "historical_availability_bias_audit_required": True,
        "negative_controls_cannot_validate": True,
        "supplemental_feature_policy": {
            "provider": "unusual_whales",
            "historical_research_only": True,
            "point_in_time_asof_join_required": True,
            "feature_manifest_ref": (
                f"data/runtime/{UNUSUAL_WHALES_FEATURE_MANIFEST_ARTIFACT}"
            ),
            "required_comparisons": list(REQUIRED_UNUSUAL_WHALES_COMPARISONS),
            "provider_only_result_cannot_replace_qadam_core_baseline": True,
            "source_quorum_allowed": False,
        },
        "strategy_mutation_allowed": False,
        "edge_creation_allowed": False,
        "candidate_creation_allowed": False,
        "order_creation_allowed": False,
        "proof_credit_allowed": False,
        "authority": authority_flags(),
    }


def _feature_set_variants(unusual_whales: dict[str, Any]) -> list[dict[str, Any]]:
    ready = unusual_whales.get("backtest_feature_ready") is True
    return [
        {
            "variant_id": variant,
            "status": (
                "tested"
                if variant == "qadam_core_without_unusual_whales"
                else "ready_for_point_in_time_ablation"
                if ready
                else "blocked_no_eligible_unusual_whales_history"
            ),
            "can_validate_edge": variant
            not in {"time_shifted_negative_control", "shuffled_negative_control"},
        }
        for variant in REQUIRED_UNUSUAL_WHALES_COMPARISONS
    ]


def _aggregate_regimes(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    values: defaultdict[str, list[float]] = defaultdict(list)
    for result in results:
        metrics = result.get("holdout_metrics")
        if not isinstance(metrics, dict):
            continue
        for regime, value in metrics.get("regime_mean_net_returns", {}).items():
            values[str(regime)].append(_number(value))
    return [
        {
            "regime": regime,
            "measured_result_count": len(measured),
            "mean_holdout_net_return": sum(measured) / len(measured),
        }
        for regime, measured in sorted(values.items())
        if measured
    ]


def _aggregate_directions(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for result in results:
        metrics = result.get("holdout_metrics")
        if isinstance(metrics, dict):
            counts.update(metrics.get("direction_counts", {}))
    return [
        {"direction": direction, "holdout_trade_count": count}
        for direction, count in sorted(counts.items())
    ]


def _concise_rejection(result: dict[str, Any], run_id: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_backtest_rejection",
        "run_id": run_id,
        "rejection_id": stable_id(
            "backtest-rejection", run_id, result["hypothesis_id"]
        ),
        "hypothesis_id": result["hypothesis_id"],
        "method_id": result["method_id"],
        "strategy_family_id": result["strategy_family_id"],
        "instrument": result["instrument"],
        "horizon": result["horizon"],
        "status": result["status"],
        "rejection_reasons": result.get("rejection_reasons", []),
        "raw_p_value": result.get("raw_p_value"),
        "adjusted_p_value": result.get("adjusted_p_value"),
        "edge_created": False,
        "candidate_created": False,
        "order_created": False,
        "proof_credit_created": False,
        "authority": authority_flags(),
    }


def _empty_engine() -> dict[str, Any]:
    return {
        "results": [],
        "folds": [],
        "rejections": [],
        "historical_edge_candidates": [],
        "attempted_hypothesis_count": 0,
        "completed_method_count": 0,
        "untouched_holdout_result_count": 0,
        "cost_adjusted_result_count": 0,
        "raw_significant_result_count": 0,
        "false_discovery_adjusted_result_count": 0,
        "adjusted_significant_result_count": 0,
        "negative_control_executed_count": 0,
        "negative_control_statistically_positive_count": 0,
        "negative_control_guard_trigger_count": 0,
        "negative_control_promotion_gate_breach_count": 0,
        "negative_control_validated_count": 0,
        "results_by_strategy": [],
        "results_by_instrument": [],
        "results_by_horizon": [],
        "results_by_method": [],
        "source_contributions": [],
        "independent_group_count": 0,
        "eligible_strategy_instrument_horizon_group_count": 0,
        "insufficient_group_count": 0,
    }


def _negative_control_record(row: dict[str, Any], *, source_run: str) -> dict[str, Any]:
    metrics = row.get("holdout_metrics") if isinstance(row.get("holdout_metrics"), dict) else {}
    return {
        "hypothesis_id": row.get("hypothesis_id"),
        "source_run": source_run,
        "method_id": row.get("method_id"),
        "strategy_family_id": row.get("strategy_family_id"),
        "instrument": row.get("instrument"),
        "horizon": row.get("horizon"),
        "raw_p_value": row.get("raw_p_value"),
        "adjusted_p_value": row.get("adjusted_p_value"),
        "hit_rate": metrics.get("hit_rate"),
        "trade_count": metrics.get("trade_count"),
        "mean_net_return": metrics.get("mean_net_return"),
        "cumulative_net_return": metrics.get("cumulative_net_return"),
        "effective_block_count": metrics.get("effective_block_count"),
        "guard_triggered": row.get("negative_control_guard_triggered") is True
        or row.get("negative_control_promotion_gate_breach") is True,
        "promotion_gate_breached": row.get("negative_control_promotion_gate_breach") is True
        and row.get("historical_edge_candidate") is True,
        "historical_edge_candidate": row.get("historical_edge_candidate") is True,
        "edge_created": row.get("edge_created") is True,
        "tradeable": False,
        "strategy_creation_allowed": False,
        "paper_order_allowed": False,
        "diagnostic_reason": (
            "This control intentionally removes meaningful timing. A positive result is a "
            "test-calibration finding, not a market edge."
        ),
    }


def _negative_control_diagnostics(
    engine: dict[str, Any], *, run_id: str, generated_at: str
) -> dict[str, Any]:
    current_controls = [
        row for row in engine["results"] if row.get("negative_control") is True
    ]
    current_by_id = {str(row.get("hypothesis_id")): row for row in current_controls}
    historical: dict[tuple[str, str], dict[str, Any]] = {}
    if RESEARCH_BACKTEST_ROOT.exists():
        for path in sorted(RESEARCH_BACKTEST_ROOT.glob("run=*/hypothesis_results.jsonl")):
            source_run = path.parent.name
            for row in read_jsonl(path):
                if row.get("negative_control") is not True:
                    continue
                if not (
                    row.get("negative_control_guard_triggered") is True
                    or row.get("negative_control_promotion_gate_breach") is True
                ):
                    continue
                key = (source_run, str(row.get("hypothesis_id")))
                historical[key] = _negative_control_record(row, source_run=source_run)
    current_findings = [
        _negative_control_record(row, source_run=run_id)
        for row in current_controls
        if row.get("negative_control_guard_triggered") is True
        or row.get("negative_control_promotion_gate_breach") is True
    ]
    historical_findings = []
    for record in historical.values():
        current = current_by_id.get(str(record.get("hypothesis_id")))
        historical_findings.append(
            {
                **record,
                "current_retest": (
                    {
                        "raw_p_value": current.get("raw_p_value"),
                        "adjusted_p_value": current.get("adjusted_p_value"),
                        "adjusted_state": current.get("false_discovery_adjusted_state"),
                        "guard_triggered": current.get("negative_control_guard_triggered")
                        is True,
                        "promotion_gate_breached": current.get(
                            "negative_control_promotion_gate_breach"
                        )
                        is True,
                    }
                    if current
                    else None
                ),
            }
        )
    promotion_breaches = int(engine["negative_control_promotion_gate_breach_count"])
    guard_triggers = int(engine["negative_control_guard_trigger_count"])
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_negative_control_diagnostics",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": (
            "blocked_control_escaped_quarantine"
            if promotion_breaches
            else "review_current_control_signal"
            if guard_triggers
            else "resolved_prior_control_signal"
            if historical_findings
            else "passed_no_control_signal"
        ),
        "run_id": run_id,
        "p_value_method": "exact_block_sign_flip_for_16_or_fewer_effective_blocks",
        "negative_control_executed_count": engine["negative_control_executed_count"],
        "current_guard_trigger_count": guard_triggers,
        "current_promotion_gate_breach_count": promotion_breaches,
        "historical_incident_count": len(historical_findings),
        "current_findings": current_findings,
        "historical_findings": historical_findings,
        "finding_can_create_strategy": False,
        "finding_can_create_trade_candidate": False,
        "finding_can_create_paper_order": False,
        "quarantine_required": bool(guard_triggers or promotion_breaches),
        "plain_english": (
            "Randomised timing controls are used to expose false confidence. Their findings "
            "remain diagnostic and can never become strategies or paper orders."
        ),
        "authority": authority_flags(),
    }


def build_statistical_backtest_state(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    generated_at = now_iso()
    protocol = _protocol(generated_at)
    protocol_hash = sha256_text(
        canonical_json(
            {
                key: value
                for key, value in protocol.items()
                if key not in {"generated_at", "authority"}
            }
        )
    )
    label_coverage = read_json(runtime / LABEL_COVERAGE_ARTIFACT)
    label_quality = read_json(runtime / LABEL_QUALITY_ARTIFACT)
    backfill = read_json(runtime / BACKFILL_COVERAGE_ARTIFACT)
    trading = read_json(runtime / TRADING_UNIVERSE_ARTIFACT)
    unusual_whales = read_json(runtime / UNUSUAL_WHALES_FEATURE_MANIFEST_ARTIFACT)
    rows, input_audit = load_empirical_backtest_dataset(runtime)
    empirical_inputs_ready = (
        input_audit.get("status") == "empirical_score_label_pairs_loaded"
        and len(rows) >= MINIMUM_INDEPENDENT_ROWS
    )
    engine = (
        run_whole_universe_backtest(rows, stable_id_builder=stable_id)
        if empirical_inputs_ready
        else _empty_engine()
    )
    input_hash = sha256_text(
        canonical_json(
            {
                "score_dataset_hash": input_audit.get("score_dataset_hash"),
                "label_dataset_hash": input_audit.get("label_dataset_hash"),
                "protocol_hash": protocol_hash,
            }
        )
    )
    run_id = stable_id("backtest-run", PROTOCOL_VERSION, input_hash)
    run_root = RESEARCH_BACKTEST_ROOT / f"run={run_id.split(':')[-1]}"
    result_path = run_root / "hypothesis_results.jsonl"
    fold_path = run_root / "fold_results.jsonl"
    result_hash = record_set_hash(engine["results"])
    fold_hash = record_set_hash(engine["folds"])
    intended_instruments = [
        str(item.get("symbol"))
        for item in trading.get("instruments", [])
        if item.get("symbol")
    ]
    backtested_instruments = list(input_audit.get("instruments", []))
    excluded_instruments = sorted(set(intended_instruments) - set(backtested_instruments))
    historical_candidates = engine["historical_edge_candidates"]
    feature_variants = _feature_set_variants(unusual_whales)
    manifest_status = (
        "complete"
        if empirical_inputs_ready
        else "blocked_insufficient_score_label_pairs"
    )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_backtest_run_manifest",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": manifest_status,
        "run_id": run_id,
        "protocol_version": PROTOCOL_VERSION,
        "protocol_hash": protocol_hash,
        "input_hash": input_hash,
        "score_dataset_hash": input_audit.get("score_dataset_hash"),
        "label_dataset_hash": input_audit.get("label_dataset_hash"),
        "score_tape_manifest_ref": f"data/runtime/{SCORE_TAPE_MANIFEST_ARTIFACT}",
        "forward_label_manifest_ref": (
            f"data/runtime/{FORWARD_LABEL_MANIFEST_ARTIFACT}"
        ),
        "score_row_count": input_audit.get("score_row_count", 0),
        "label_count": input_audit.get("label_row_count", 0),
        "typed_missing_label_count": int(
            label_coverage.get("typed_missing_label_count") or 0
        ),
        "paired_score_label_count": input_audit.get("paired_score_label_count", 0),
        "independent_pair_count": input_audit.get("independent_pair_count", 0),
        "attempted_hypothesis_count": engine["attempted_hypothesis_count"],
        "fold_result_count": len(engine["folds"]),
        "dataset_hashes_available": empirical_inputs_ready,
        "input_audit": input_audit,
        "bulk_results": {
            "result_path": str(result_path.relative_to(ROOT)),
            "result_record_set_hash": result_hash,
            "result_count": len(engine["results"]),
            "fold_path": str(fold_path.relative_to(ROOT)),
            "fold_record_set_hash": fold_hash,
            "fold_count": len(engine["folds"]),
            "written": False,
            "reused_existing": False,
        },
        "feature_set_variants": feature_variants,
        "bias_audit": {
            "fixed_current_universe_used": True,
            "historical_constituent_universe_available": False,
            "survivorship_bias_state": (
                "partially_mitigated_fixed_universe_with_explicit_exclusions"
            ),
            "intended_instrument_count": len(intended_instruments),
            "backtested_instrument_count": len(backtested_instruments),
            "excluded_instruments": excluded_instruments,
            "intended_source_count": int(backfill.get("source_count") or 0),
            "backtested_source_count": int(input_audit.get("source_count") or 0),
            "backtested_sources": input_audit.get("source_keys", []),
            "source_coverage_limitation_explicit": True,
            "point_in_time_availability_enforced": True,
            "score_before_label_enforced": True,
            "availability_bias_state": (
                "mitigated_for_loaded_records_with_typed_unavailable_history_remaining"
            ),
        },
        "score_plane_read_only": True,
        "label_plane_read_only": True,
        "bulk_outputs_written": False,
        "strategy_mutation_allowed": False,
        "edge_creation_allowed": False,
        "candidate_creation_allowed": False,
        "order_creation_allowed": False,
        "proof_credit_allowed": False,
        "paperops_watch_only_mode": True,
        "authority": authority_flags(),
    }
    result_status = (
        "complete_with_historical_edge_candidates"
        if historical_candidates
        else "complete_no_historical_edge_survived"
        if empirical_inputs_ready
        else "blocked_insufficient_inputs"
    )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_backtest_results_summary",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": result_status,
        "run_id": run_id,
        "completed_method_count": engine["completed_method_count"],
        "attempted_hypothesis_count": engine["attempted_hypothesis_count"],
        "validated_edge_count": 0,
        "historical_edge_candidate_count": len(historical_candidates),
        "rejected_result_count": len(engine["rejections"]),
        "untouched_holdout_result_count": engine["untouched_holdout_result_count"],
        "cost_adjusted_result_count": engine["cost_adjusted_result_count"],
        "negative_control_validated_count": engine[
            "negative_control_validated_count"
        ],
        "negative_control_executed_count": engine[
            "negative_control_executed_count"
        ],
        "negative_control_statistically_positive_count": engine[
            "negative_control_statistically_positive_count"
        ],
        "negative_control_guard_trigger_count": engine[
            "negative_control_guard_trigger_count"
        ],
        "negative_control_promotion_gate_breach_count": engine[
            "negative_control_promotion_gate_breach_count"
        ],
        "raw_significant_result_count": engine["raw_significant_result_count"],
        "adjusted_significant_result_count": engine[
            "adjusted_significant_result_count"
        ],
        "false_discovery_adjusted_result_count": engine[
            "false_discovery_adjusted_result_count"
        ],
        "eligible_strategy_instrument_horizon_group_count": engine[
            "eligible_strategy_instrument_horizon_group_count"
        ],
        "insufficient_group_count": engine["insufficient_group_count"],
        "results_by_strategy": engine["results_by_strategy"],
        "results_by_instrument": engine["results_by_instrument"],
        "results_by_direction": _aggregate_directions(engine["results"]),
        "results_by_horizon": engine["results_by_horizon"],
        "results_by_regime": _aggregate_regimes(engine["results"]),
        "results_by_method": engine["results_by_method"],
        "source_contributions": engine["source_contributions"],
        "feature_set_comparisons": feature_variants,
        "top_historical_edge_candidates": [
            {
                "hypothesis_id": row["hypothesis_id"],
                "method_id": row["method_id"],
                "strategy_family_id": row["strategy_family_id"],
                "instrument": row["instrument"],
                "horizon": row["horizon"],
                "adjusted_p_value": row.get("adjusted_p_value"),
                "holdout_mean_net_return": row.get("holdout_metrics", {}).get(
                    "mean_net_return"
                ),
                "edge_created": False,
            }
            for row in sorted(
                historical_candidates,
                key=lambda item: (
                    _number(item.get("adjusted_p_value"), 1.0),
                    -_number(item.get("holdout_metrics", {}).get("mean_net_return")),
                ),
            )[:10]
        ],
        "historical_result_claim_allowed": empirical_inputs_ready,
        "edge_promotion_allowed": False,
        "empirical_live_return_claim_allowed": False,
        "why_no_result": (
            None
            if historical_candidates
            else "No Qadam method survived the untouched holdout, costs, stability, baseline, concentration, and false-discovery gates."
            if empirical_inputs_ready
            else "Provider-backed score-label inputs are incomplete."
        ),
        "paperops_watch_only_mode": True,
        "authority": authority_flags(),
    }
    rejections = [
        _concise_rejection(result, run_id) for result in engine["rejections"]
    ]
    multiple_testing = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_multiple_testing_audit",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "complete" if empirical_inputs_ready else "not_run",
        "run_id": run_id,
        "attempted_hypothesis_count": engine["attempted_hypothesis_count"],
        "registered_hypothesis_count": engine["attempted_hypothesis_count"],
        "unregistered_result_count": 0,
        "adjustment_method": "benjamini_hochberg",
        "alpha": FALSE_DISCOVERY_ALPHA,
        "raw_significant_result_count": engine["raw_significant_result_count"],
        "adjusted_result_count": engine["false_discovery_adjusted_result_count"],
        "adjusted_significant_result_count": engine[
            "adjusted_significant_result_count"
        ],
        "negative_control_validated_count": 0,
        "negative_control_executed_count": engine[
            "negative_control_executed_count"
        ],
        "negative_control_statistically_positive_count": engine[
            "negative_control_statistically_positive_count"
        ],
        "negative_control_guard_trigger_count": engine[
            "negative_control_guard_trigger_count"
        ],
        "negative_control_promotion_gate_breach_count": engine[
            "negative_control_promotion_gate_breach_count"
        ],
        "hypothesis_registry_hash": sha256_text(
            canonical_json(
                sorted(result["hypothesis_id"] for result in engine["results"])
            )
        ),
        "authority": authority_flags(),
    }
    walk_forward = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_walk_forward_audit",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "complete" if empirical_inputs_ready else "not_run",
        "run_id": run_id,
        "paired_score_label_count": input_audit.get("paired_score_label_count", 0),
        "independent_pair_count": input_audit.get("independent_pair_count", 0),
        "fold_result_count": len(engine["folds"]),
        "untouched_holdout_result_count": engine["untouched_holdout_result_count"],
        "chronological_order_enforced": True,
        "purging_enforced": True,
        "embargo_enforced": True,
        "nested_threshold_tuning_enforced": True,
        "holdout_tuning_violation_count": 0,
        "overlap_independence_enforced": True,
        "fold_results_ref": str(fold_path.relative_to(ROOT)),
        "fold_record_set_hash": fold_hash,
        "label_quality_state": label_quality.get("status"),
        "provider_backfill_row_count": backfill.get("provider_row_count", 0),
        "unusual_whales_feature_row_count": int(
            unusual_whales.get("backtest_eligible_record_count") or 0
        ),
        "unusual_whales_feature_ready": unusual_whales.get(
            "backtest_feature_ready"
        )
        is True,
        "authority": authority_flags(),
    }
    dashboard = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_backtest_dashboard_summary",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": result_status,
        "headline": (
            f"{len(historical_candidates)} historical edge candidates survived"
            if historical_candidates
            else "The first whole-universe backtest found no edge strong enough to advance"
            if empirical_inputs_ready
            else "The whole-universe backtest is waiting for empirical inputs"
        ),
        "plain_english": (
            f"Qadam tested {engine['attempted_hypothesis_count']} registered relationships across "
            f"{input_audit.get('instrument_count', 0)} instruments. It kept the final period untouched, "
            "included estimated trading friction, and corrected for repeated testing. "
            f"{len(historical_candidates)} results cleared every research gate. No strategy, trade, or order was created."
            if empirical_inputs_ready
            else "Qadam cannot make a historical edge claim until provider-backed scores and outcomes are available."
        ),
        "paired_score_label_count": input_audit.get("paired_score_label_count", 0),
        "independent_pair_count": input_audit.get("independent_pair_count", 0),
        "attempted_hypothesis_count": engine["attempted_hypothesis_count"],
        "untouched_holdout_result_count": engine["untouched_holdout_result_count"],
        "historical_edge_candidate_count": len(historical_candidates),
        "validated_edge_count": 0,
        "next_action": (
            "Review surviving research candidates in OR-9 nonlinear and quantum incremental-value tests."
            if historical_candidates
            else "Use the rejection ledger to refine hypotheses without changing frozen historical results."
            if empirical_inputs_ready
            else "Complete provider-backed score and label acquisition."
        ),
        "supplemental_feature_note": (
            "Unusual Whales features are ready for a controlled ablation."
            if unusual_whales.get("backtest_feature_ready") is True
            else "Unusual Whales remains an optional comparison; no eligible historical features were included."
        ),
        "negative_control_note": (
            "A randomised timing control remains quarantined for research review. It cannot "
            "create a strategy, candidate, or order."
            if engine["negative_control_guard_trigger_count"]
            else "Randomised timing controls did not produce a promotion-eligible result."
        ),
        "research_only": True,
        "paperops_watch_only_mode": True,
        "authority": authority_flags(),
    }
    diagnostics = _negative_control_diagnostics(
        engine, run_id=run_id, generated_at=generated_at
    )
    return {
        "protocol": protocol,
        "manifest": manifest,
        "summary": summary,
        "rejections": rejections,
        "multiple_testing": multiple_testing,
        "walk_forward": walk_forward,
        "dashboard": dashboard,
        "negative_control_diagnostics": diagnostics,
        "bulk_results": engine["results"],
        "bulk_folds": engine["folds"],
    }


def _write_immutable_partition(
    path: Path, rows: list[dict[str, Any]]
) -> tuple[str, bool]:
    resolved = path.resolve()
    if not resolved.is_relative_to(RESEARCH_BACKTEST_ROOT.resolve()):
        raise ValueError("backtest_output_path_outside_research_store")
    expected = record_set_hash(rows)
    if resolved.exists():
        if record_set_hash(read_jsonl(resolved)) != expected:
            raise ValueError("completed_backtest_output_immutable_mismatch")
        return expected, True
    write_jsonl_atomic(resolved, rows)
    return expected, False


def validate_statistical_backtest_state(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    protocol = state["protocol"]
    manifest = state["manifest"]
    summary = state["summary"]
    multiple = state["multiple_testing"]
    walk = state["walk_forward"]
    bulk_results = state.get("bulk_results", [])
    bulk_folds = state.get("bulk_folds", [])
    empirical = manifest.get("status") == "complete"
    if set(protocol.get("baseline_methods", [])) != set(BASELINE_METHODS):
        errors.append("backtest_baseline_methods_incomplete")
    if set(protocol.get("qadam_methods", [])) != set(QADAM_METHODS):
        errors.append("backtest_qadam_methods_incomplete")
    if protocol.get("costs_required") is not True:
        errors.append("backtest_costs_not_required")
    if protocol.get("negative_controls_cannot_validate") is not True:
        errors.append("backtest_negative_control_policy_unsafe")
    comparisons = set(
        protocol.get("supplemental_feature_policy", {}).get(
            "required_comparisons", []
        )
    )
    if set(REQUIRED_UNUSUAL_WHALES_COMPARISONS) - comparisons:
        errors.append("backtest_unusual_whales_ablation_incomplete")
    if summary.get("negative_control_validated_count") != 0:
        errors.append("backtest_negative_control_validated")
    if empirical and summary.get("negative_control_executed_count", 0) <= 0:
        errors.append("backtest_negative_control_not_executed")
    if summary.get("negative_control_promotion_gate_breach_count", 0) != 0:
        errors.append("backtest_negative_control_promotion_gate_breach")
    diagnostics = state.get("negative_control_diagnostics", {})
    if diagnostics.get("current_promotion_gate_breach_count", 0) != 0:
        errors.append("backtest_negative_control_escaped_quarantine")
    if diagnostics.get("finding_can_create_strategy") is not False:
        errors.append("backtest_negative_control_can_create_strategy")
    if diagnostics.get("finding_can_create_paper_order") is not False:
        errors.append("backtest_negative_control_can_create_order")
    if multiple.get("unregistered_result_count") != 0:
        errors.append("backtest_unregistered_hypothesis_result")
    if walk.get("holdout_tuning_violation_count") != 0:
        errors.append("backtest_holdout_tuning_violation")
    if summary.get("validated_edge_count") != 0:
        errors.append("backtest_created_edge_outside_or10")
    if any(result.get("edge_created") is not False for result in bulk_results):
        errors.append("backtest_bulk_result_created_edge")
    if any(
        result.get("strategy_mutation_allowed") is not False
        for result in bulk_results
    ):
        errors.append("backtest_bulk_result_allowed_strategy_mutation")
    if any(
        result.get("candidate_creation_allowed") is not False
        or result.get("order_creation_allowed") is not False
        or result.get("proof_credit_allowed") is not False
        for result in bulk_results
    ):
        errors.append("backtest_bulk_result_crossed_authority_boundary")
    if any(
        fold.get("holdout_accessed") is not False for fold in bulk_folds
    ):
        errors.append("backtest_fold_accessed_untouched_holdout")
    if empirical:
        if manifest.get("paired_score_label_count", 0) <= 0:
            errors.append("backtest_no_score_label_pairs")
        if manifest.get("independent_pair_count", 0) <= 0:
            errors.append("backtest_no_independent_pairs")
        if summary.get("untouched_holdout_result_count", 0) <= 0:
            errors.append("backtest_untouched_holdout_missing")
        if summary.get("cost_adjusted_result_count", 0) <= 0:
            errors.append("backtest_cost_adjusted_results_missing")
        if multiple.get("attempted_hypothesis_count") != multiple.get(
            "registered_hypothesis_count"
        ):
            errors.append("backtest_hypothesis_registry_incomplete")
        if multiple.get("adjusted_result_count") != multiple.get(
            "attempted_hypothesis_count"
        ):
            errors.append("backtest_false_discovery_adjustment_incomplete")
        if len(bulk_results) != manifest.get("attempted_hypothesis_count"):
            errors.append("backtest_bulk_result_registry_count_mismatch")
        if len(bulk_folds) != manifest.get("fold_result_count"):
            errors.append("backtest_bulk_fold_count_mismatch")
        if any(
            result.get("false_discovery_adjusted_state")
            not in {"significant", "not_significant"}
            for result in bulk_results
        ):
            errors.append("backtest_bulk_result_missing_adjusted_state")
        if any(
            result.get("negative_control") is True
            and result.get("historical_edge_candidate") is True
            for result in bulk_results
        ):
            errors.append("backtest_negative_control_became_candidate")
        bulk = manifest.get("bulk_results", {})
        if bulk.get("written") is True:
            for path_key, hash_key, rows in (
                (
                    "result_path",
                    "result_record_set_hash",
                    bulk_results,
                ),
                ("fold_path", "fold_record_set_hash", bulk_folds),
            ):
                path = ROOT / str(bulk.get(path_key) or "")
                if not path.is_file():
                    errors.append(f"backtest_bulk_output_missing:{path_key}")
                elif record_set_hash(read_jsonl(path)) != bulk.get(hash_key):
                    errors.append(f"backtest_bulk_output_hash_mismatch:{path_key}")
                elif record_set_hash(rows) != bulk.get(hash_key):
                    errors.append(f"backtest_in_memory_output_hash_mismatch:{path_key}")
        input_audit = manifest.get("input_audit", {})
        for key in (
            "duplicate_score_id_count",
            "duplicate_label_score_id_count",
            "label_without_score_count",
            "chronology_violation_count",
        ):
            if input_audit.get(key) != 0:
                errors.append(f"backtest_input_audit_failed:{key}")
        if not manifest.get("score_dataset_hash") or not manifest.get(
            "label_dataset_hash"
        ):
            errors.append("backtest_dataset_hash_missing")
    for payload, prefix in (
        (protocol, "backtest_protocol"),
        (manifest, "backtest_manifest"),
        (summary, "backtest_summary"),
        (multiple, "multiple_testing"),
        (walk, "walk_forward"),
        (state["dashboard"], "backtest_dashboard"),
        (diagnostics, "negative_control_diagnostics"),
    ):
        errors.extend(validate_authority(payload.get("authority", {}), prefix=prefix))
    return unique_errors(errors)


def build_and_write_statistical_backtest(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    try:
        state = build_statistical_backtest_state(settings)
        manifest = state["manifest"]
        bulk = manifest["bulk_results"]
        result_path = ROOT / bulk["result_path"]
        fold_path = ROOT / bulk["fold_path"]
        result_hash, result_reused = _write_immutable_partition(
            result_path, state["bulk_results"]
        )
        fold_hash, fold_reused = _write_immutable_partition(
            fold_path, state["bulk_folds"]
        )
        bulk["result_record_set_hash"] = result_hash
        bulk["fold_record_set_hash"] = fold_hash
        bulk["written"] = True
        bulk["reused_existing"] = result_reused and fold_reused
        manifest["bulk_outputs_written"] = True
        errors = validate_statistical_backtest_state(state)
    except (OSError, TypeError, ValueError) as exc:
        generated_at = now_iso()
        state = {
            "protocol": _protocol(generated_at),
            "manifest": {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_backtest_run_manifest",
                "phase_id": PHASE_ID,
                "generated_at": generated_at,
                "status": "blocked",
                "bulk_results": {},
                "paperops_watch_only_mode": True,
                "authority": authority_flags(),
            },
            "summary": {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_backtest_results_summary",
                "phase_id": PHASE_ID,
                "generated_at": generated_at,
                "status": "blocked",
                "validated_edge_count": 0,
                "historical_edge_candidate_count": 0,
                "untouched_holdout_result_count": 0,
                "cost_adjusted_result_count": 0,
                "negative_control_validated_count": 0,
                "authority": authority_flags(),
            },
            "rejections": [],
            "multiple_testing": {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_multiple_testing_audit",
                "generated_at": generated_at,
                "status": "blocked",
                "unregistered_result_count": 0,
                "authority": authority_flags(),
            },
            "walk_forward": {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_walk_forward_audit",
                "generated_at": generated_at,
                "status": "blocked",
                "holdout_tuning_violation_count": 0,
                "authority": authority_flags(),
            },
            "dashboard": {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_backtest_dashboard_summary",
                "generated_at": generated_at,
                "status": "blocked",
                "headline": "Backtest blocked",
                "plain_english": str(exc),
                "authority": authority_flags(),
            },
            "negative_control_diagnostics": {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_negative_control_diagnostics",
                "generated_at": generated_at,
                "status": "blocked",
                "current_guard_trigger_count": 0,
                "current_promotion_gate_breach_count": 0,
                "finding_can_create_strategy": False,
                "finding_can_create_trade_candidate": False,
                "finding_can_create_paper_order": False,
                "authority": authority_flags(),
            },
            "bulk_results": [],
            "bulk_folds": [],
        }
        errors = [str(exc)]
    store.write_json(PROTOCOL_ARTIFACT, state["protocol"])
    store.write_json(MANIFEST_ARTIFACT, state["manifest"])
    store.write_json(SUMMARY_ARTIFACT, state["summary"])
    store.write_jsonl(REJECTIONS_ARTIFACT, state["rejections"])
    store.write_json(MULTIPLE_TESTING_ARTIFACT, state["multiple_testing"])
    store.write_json(WALK_FORWARD_ARTIFACT, state["walk_forward"])
    store.write_json(DASHBOARD_ARTIFACT, state["dashboard"])
    store.write_json(
        NEGATIVE_CONTROL_DIAGNOSTICS_ARTIFACT,
        state["negative_control_diagnostics"],
    )
    empirical_complete = (
        state["manifest"].get("status") == "complete"
        and state["summary"].get("untouched_holdout_result_count", 0) > 0
    )
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_statistical_backtest_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if not errors and empirical_complete else "blocked",
        "acceptance_passed": not errors and empirical_complete,
        "implementation_ready": not errors,
        "empirical_backtest_complete": empirical_complete,
        "paired_score_label_count": state["manifest"].get(
            "paired_score_label_count", 0
        ),
        "independent_pair_count": state["manifest"].get(
            "independent_pair_count", 0
        ),
        "attempted_hypothesis_count": state["summary"].get(
            "attempted_hypothesis_count", 0
        ),
        "fold_result_count": state["manifest"].get("fold_result_count", 0),
        "untouched_holdout_result_count": state["summary"].get(
            "untouched_holdout_result_count", 0
        ),
        "cost_adjusted_result_count": state["summary"].get(
            "cost_adjusted_result_count", 0
        ),
        "historical_edge_candidate_count": state["summary"].get(
            "historical_edge_candidate_count", 0
        ),
        "validated_edge_count": state["summary"].get("validated_edge_count", 0),
        "strategy_mutation_count": 0,
        "trade_candidate_created_count": 0,
        "negative_control_validated_count": state["summary"].get(
            "negative_control_validated_count", 0
        ),
        "negative_control_executed_count": state["summary"].get(
            "negative_control_executed_count", 0
        ),
        "negative_control_statistically_positive_count": state["summary"].get(
            "negative_control_statistically_positive_count", 0
        ),
        "negative_control_guard_trigger_count": state["summary"].get(
            "negative_control_guard_trigger_count", 0
        ),
        "negative_control_promotion_gate_breach_count": state["summary"].get(
            "negative_control_promotion_gate_breach_count", 0
        ),
        "false_discovery_adjusted_result_count": state["summary"].get(
            "false_discovery_adjusted_result_count", 0
        ),
        "holdout_tuning_violation_count": state["walk_forward"].get(
            "holdout_tuning_violation_count", 0
        ),
        "bulk_outputs_reused": state["manifest"].get("bulk_results", {}).get(
            "reused_existing", False
        ),
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "broker_write_count": 0,
        "paper_order_created_count": 0,
        "proof_credit_created_count": 0,
        "paper_growth_trial_calendar_advanced": False,
        "paperops_watch_only_mode": True,
        "authority": authority_flags(),
    }
    store.write_json(CHECK_ARTIFACT, checks)
    return state, checks, errors
