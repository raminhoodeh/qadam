"""Deterministic matched-comparison engine for OR-9 research experiments."""

from __future__ import annotations

from collections import Counter, defaultdict
from importlib.metadata import PackageNotFoundError, version
import importlib.util
import math
from statistics import fmean
from time import perf_counter
from typing import Any

import numpy as np

from orchestrator.qadam_backtest_engine import (
    FALSE_DISCOVERY_ALPHA,
    MINIMUM_HOLDOUT_TRADES,
    MINIMUM_INDEPENDENT_ROWS,
    benjamini_hochberg,
    dependence_aware_mean_uncertainty,
    enrich_backtest_rows,
    evaluate_predictions,
    fit_method,
    predict_method,
    tune_threshold,
)


NONLINEAR_METHODS = (
    "nonlinear_feature_interactions",
    "regime_path_dependence",
    "ordinal_permutation_entropy",
    "clustering_state_transitions",
    "constrained_combinatorial_feature_selection",
)
QUANTUM_METHOD = "quantum_kernel_or_circuit_inspired"
EXPERIMENT_METHODS = (*NONLINEAR_METHODS, QUANTUM_METHOD)
NEGATIVE_CONTROL_METHOD = "time_shifted_target_negative_control"

BASE_FEATURES = (
    "raw_pattern_score",
    "source_trust",
    "source_freshness",
    "source_independence",
    "causal_mapping_strength",
    "strategy_fit",
    "log_source_event_count",
    "distinct_source_count",
    "rolling_volatility",
    "volume_relative",
    "prior_return_5",
    "cross_asset_score",
    "source_divergence",
    "ordinal_entropy",
    "regime_duration",
    "score_change",
)
POLYNOMIAL_FEATURES = (
    "raw_pattern_score",
    "source_independence",
    "log_source_event_count",
    "rolling_volatility",
    "prior_return_5",
    "cross_asset_score",
    "ordinal_entropy",
    "regime_duration",
)
QUANTUM_FEATURES = (
    "raw_pattern_score",
    "source_independence",
    "log_source_event_count",
    "rolling_volatility",
    "prior_return_5",
    "cross_asset_score",
)


def _number(value: Any, default: float = 0.0) -> float:
    if value is None or isinstance(value, bool):
        return default
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def _mean(values: list[float], default: float = 0.0) -> float:
    return fmean(values) if values else default


def _package_version(package: str) -> str | None:
    try:
        return version(package)
    except PackageNotFoundError:
        return None


def quantum_dependency_truth() -> dict[str, Any]:
    qiskit = importlib.util.find_spec("qiskit") is not None
    aer = importlib.util.find_spec("qiskit_aer") is not None
    return {
        "qiskit_importable": qiskit,
        "qiskit_version": _package_version("qiskit") if qiskit else None,
        "qiskit_aer_importable": aer,
        "qiskit_aer_version": _package_version("qiskit-aer") if aer else None,
        "local_statevector_simulation_available": qiskit,
        "local_aer_simulation_available": qiskit and aer,
        "physical_hardware_used": False,
    }


def quantum_usefulness_score(
    *,
    classical_holdout_metric: float | None,
    quantum_holdout_metric: float | None,
    complexity_penalty: float,
    latency_penalty: float,
    reliability: float,
) -> float | None:
    if classical_holdout_metric is None or quantum_holdout_metric is None:
        return None
    incremental_value = quantum_holdout_metric - classical_holdout_metric
    return max(
        0.0,
        min(
            1.0,
            incremental_value
            - (0.20 * max(0.0, min(1.0, complexity_penalty)))
            - (0.10 * max(0.0, min(1.0, latency_penalty)))
            - (0.20 * (1.0 - max(0.0, min(1.0, reliability)))),
        ),
    )


def _ordinal_entropy(values: list[float], order: int = 3) -> float:
    if len(values) < order + 1:
        return 0.0
    counts: Counter[tuple[int, ...]] = Counter()
    for index in range(order - 1, len(values)):
        window = values[index - order + 1 : index + 1]
        permutation = tuple(sorted(range(order), key=lambda item: (window[item], item)))
        counts[permutation] += 1
    total = sum(counts.values())
    if total <= 0 or len(counts) <= 1:
        return 0.0
    entropy = -sum((count / total) * math.log(count / total) for count in counts.values())
    return entropy / math.log(math.factorial(order))


def enrich_or9_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add point-in-time path and entropy features without using outcomes."""

    enriched = sorted(
        enrich_backtest_rows(rows), key=lambda row: (str(row["decision_at"]), str(row["score_id"]))
    )
    score_history: list[float] = []
    previous_score = 0.0
    previous_regime = "none"
    regime_duration = 0
    for row in enriched:
        score = _number(row.get("raw_pattern_score"))
        regime = str(row.get("regime") or "unclassified")
        regime_duration = regime_duration + 1 if regime == previous_regime else 1
        score_history.append(score)
        row["ordinal_entropy"] = _ordinal_entropy(score_history[-12:])
        row["score_change"] = score - previous_score if len(score_history) > 1 else 0.0
        row["previous_regime"] = previous_regime
        row["regime_duration"] = float(regime_duration)
        previous_score = score
        previous_regime = regime
    return enriched


def _standardization(
    rows: list[dict[str, Any]], feature_names: tuple[str, ...]
) -> tuple[dict[str, float], dict[str, float]]:
    means = {name: _mean([_number(row.get(name)) for row in rows]) for name in feature_names}
    scales: dict[str, float] = {}
    for name in feature_names:
        values = [_number(row.get(name)) for row in rows]
        variance = _mean([(value - means[name]) ** 2 for value in values])
        scales[name] = max(1e-9, math.sqrt(variance))
    return means, scales


def _standardized_matrix(
    rows: list[dict[str, Any]],
    feature_names: tuple[str, ...],
    means: dict[str, float],
    scales: dict[str, float],
) -> np.ndarray:
    return np.asarray(
        [
            [(_number(row.get(name)) - means[name]) / scales[name] for name in feature_names]
            for row in rows
        ],
        dtype=float,
    )


def _ridge_coefficients(matrix: np.ndarray, targets: np.ndarray, alpha: float) -> np.ndarray:
    design = np.column_stack([np.ones(len(matrix), dtype=float), matrix])
    gram = design.T @ design
    penalty = np.eye(gram.shape[0], dtype=float) * float(alpha)
    penalty[0, 0] = 0.0
    return np.linalg.pinv(gram + penalty) @ design.T @ targets


def _ridge_predict(matrix: np.ndarray, coefficients: np.ndarray) -> np.ndarray:
    design = np.column_stack([np.ones(len(matrix), dtype=float), matrix])
    return design @ coefficients


def _polynomial_matrix(base: np.ndarray) -> np.ndarray:
    columns = [base, base * base]
    interactions = [
        (base[:, left] * base[:, right]).reshape(-1, 1)
        for left in range(base.shape[1])
        for right in range(left + 1, base.shape[1])
    ]
    if interactions:
        columns.append(np.column_stack(interactions))
    return np.column_stack(columns)


def _fit_polynomial(
    rows: list[dict[str, Any]], *, alpha: float, target_shift: int = 0
) -> dict[str, Any]:
    means, scales = _standardization(rows, POLYNOMIAL_FEATURES)
    base = _standardized_matrix(rows, POLYNOMIAL_FEATURES, means, scales)
    targets = np.asarray([_number(row.get("research_gross_return")) for row in rows])
    if target_shift:
        targets = np.roll(targets, int(target_shift))
    matrix = _polynomial_matrix(base)
    return {
        "kind": "polynomial_ridge",
        "feature_names": POLYNOMIAL_FEATURES,
        "means": means,
        "scales": scales,
        "alpha": alpha,
        "coefficients": _ridge_coefficients(matrix, targets, alpha),
        "parameter_count": matrix.shape[1] + 1,
    }


def _predict_polynomial(model: dict[str, Any], rows: list[dict[str, Any]]) -> list[float]:
    base = _standardized_matrix(
        rows,
        tuple(model["feature_names"]),
        model["means"],
        model["scales"],
    )
    return _ridge_predict(_polynomial_matrix(base), model["coefficients"]).tolist()


def _quantile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * max(0.0, min(1.0, fraction))
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _score_bin(value: float, boundaries: list[float]) -> int:
    return sum(value > boundary for boundary in boundaries)


def _path_key(row: dict[str, Any], boundaries: list[float]) -> tuple[Any, ...]:
    return (
        str(row.get("regime") or "unclassified"),
        str(row.get("previous_regime") or "none"),
        _score_bin(_number(row.get("raw_pattern_score")), boundaries),
        int(_number(row.get("prior_return_5")) >= 0.0),
        int(_number(row.get("regime_duration")) >= 3.0),
    )


def _fit_regime_path(rows: list[dict[str, Any]], *, minimum_group: int) -> dict[str, Any]:
    scores = [_number(row.get("raw_pattern_score")) for row in rows]
    boundaries = [_quantile(scores, 1 / 3), _quantile(scores, 2 / 3)]
    grouped: defaultdict[tuple[Any, ...], list[float]] = defaultdict(list)
    regime_values: defaultdict[str, list[float]] = defaultdict(list)
    for row in rows:
        target = _number(row.get("research_gross_return"))
        grouped[_path_key(row, boundaries)].append(target)
        regime_values[str(row.get("regime") or "unclassified")].append(target)
    return {
        "kind": "regime_path",
        "boundaries": boundaries,
        "means": {
            repr(key): _mean(values)
            for key, values in grouped.items()
            if len(values) >= minimum_group
        },
        "regime_means": {key: _mean(values) for key, values in regime_values.items()},
        "fallback": _mean([_number(row.get("research_gross_return")) for row in rows]),
        "minimum_group": minimum_group,
        "parameter_count": len(grouped) + len(regime_values),
    }


def _predict_regime_path(model: dict[str, Any], rows: list[dict[str, Any]]) -> list[float]:
    output: list[float] = []
    for row in rows:
        regime = str(row.get("regime") or "unclassified")
        fallback = _number(model["regime_means"].get(regime), _number(model["fallback"]))
        output.append(
            _number(
                model["means"].get(repr(_path_key(row, model["boundaries"]))),
                fallback,
            )
        )
    return output


def _entropy_matrix(base: np.ndarray, feature_names: tuple[str, ...]) -> np.ndarray:
    entropy_index = feature_names.index("ordinal_entropy")
    score_index = feature_names.index("raw_pattern_score")
    entropy = base[:, entropy_index]
    score = base[:, score_index]
    return np.column_stack([base, entropy * score, entropy * entropy, np.tanh(score) * entropy])


def _fit_entropy(rows: list[dict[str, Any]], *, alpha: float) -> dict[str, Any]:
    feature_names = (
        "raw_pattern_score",
        "ordinal_entropy",
        "score_change",
        "rolling_volatility",
        "source_independence",
        "prior_return_5",
    )
    means, scales = _standardization(rows, feature_names)
    base = _standardized_matrix(rows, feature_names, means, scales)
    matrix = _entropy_matrix(base, feature_names)
    targets = np.asarray([_number(row.get("research_gross_return")) for row in rows])
    return {
        "kind": "entropy_ridge",
        "feature_names": feature_names,
        "means": means,
        "scales": scales,
        "alpha": alpha,
        "coefficients": _ridge_coefficients(matrix, targets, alpha),
        "parameter_count": matrix.shape[1] + 1,
    }


def _predict_entropy(model: dict[str, Any], rows: list[dict[str, Any]]) -> list[float]:
    feature_names = tuple(model["feature_names"])
    base = _standardized_matrix(rows, feature_names, model["means"], model["scales"])
    return _ridge_predict(_entropy_matrix(base, feature_names), model["coefficients"]).tolist()


def _kmeans(matrix: np.ndarray, cluster_count: int) -> np.ndarray:
    ordered = np.argsort(matrix[:, 0], kind="stable")
    positions = np.linspace(0, len(ordered) - 1, cluster_count).astype(int)
    centers = matrix[ordered[positions]].copy()
    for _ in range(25):
        distances = np.sum((matrix[:, None, :] - centers[None, :, :]) ** 2, axis=2)
        assignments = np.argmin(distances, axis=1)
        updated = centers.copy()
        for cluster in range(cluster_count):
            members = matrix[assignments == cluster]
            if len(members):
                updated[cluster] = np.mean(members, axis=0)
        if np.allclose(updated, centers, rtol=0.0, atol=1e-10):
            break
        centers = updated
    return centers


def _cluster_assignments(matrix: np.ndarray, centers: np.ndarray) -> np.ndarray:
    distances = np.sum((matrix[:, None, :] - centers[None, :, :]) ** 2, axis=2)
    return np.argmin(distances, axis=1)


def _fit_cluster_transition(rows: list[dict[str, Any]], *, cluster_count: int) -> dict[str, Any]:
    feature_names = (
        "raw_pattern_score",
        "source_independence",
        "rolling_volatility",
        "prior_return_5",
        "cross_asset_score",
        "ordinal_entropy",
    )
    means, scales = _standardization(rows, feature_names)
    matrix = _standardized_matrix(rows, feature_names, means, scales)
    centers = _kmeans(matrix, cluster_count)
    assignments = _cluster_assignments(matrix, centers)
    cluster_targets: defaultdict[int, list[float]] = defaultdict(list)
    transition_targets: defaultdict[tuple[int, int], list[float]] = defaultdict(list)
    previous: int | None = None
    for assignment, row in zip(assignments.tolist(), rows):
        target = _number(row.get("research_gross_return"))
        cluster_targets[assignment].append(target)
        if previous is not None:
            transition_targets[(previous, assignment)].append(target)
        previous = assignment
    return {
        "kind": "cluster_transition",
        "feature_names": feature_names,
        "means": means,
        "scales": scales,
        "centers": centers,
        "cluster_means": {str(key): _mean(values) for key, values in cluster_targets.items()},
        "transition_means": {
            repr(key): _mean(values) for key, values in transition_targets.items()
        },
        "fallback": _mean([_number(row.get("research_gross_return")) for row in rows]),
        "cluster_count": cluster_count,
        "parameter_count": len(cluster_targets) + len(transition_targets),
    }


def _predict_cluster_transition(model: dict[str, Any], rows: list[dict[str, Any]]) -> list[float]:
    matrix = _standardized_matrix(
        rows, tuple(model["feature_names"]), model["means"], model["scales"]
    )
    assignments = _cluster_assignments(matrix, model["centers"]).tolist()
    output: list[float] = []
    previous: int | None = None
    for assignment in assignments:
        cluster_fallback = _number(
            model["cluster_means"].get(str(assignment)), _number(model["fallback"])
        )
        value = (
            model["transition_means"].get(repr((previous, assignment)))
            if previous is not None
            else None
        )
        output.append(_number(value, cluster_fallback))
        previous = assignment
    return output


def _feature_correlation(rows: list[dict[str, Any]], feature_name: str) -> float:
    values = [_number(row.get(feature_name)) for row in rows]
    targets = [_number(row.get("research_gross_return")) for row in rows]
    value_mean = _mean(values)
    target_mean = _mean(targets)
    numerator = sum(
        (value - value_mean) * (target - target_mean) for value, target in zip(values, targets)
    )
    denominator = math.sqrt(
        sum((value - value_mean) ** 2 for value in values)
        * sum((target - target_mean) ** 2 for target in targets)
    )
    return abs(numerator / denominator) if denominator > 1e-15 else 0.0


def _fit_selected_features(rows: list[dict[str, Any]], *, feature_count: int) -> dict[str, Any]:
    ranked = sorted(
        BASE_FEATURES,
        key=lambda name: (-_feature_correlation(rows, name), name),
    )
    selected = tuple(ranked[:feature_count])
    means, scales = _standardization(rows, selected)
    base = _standardized_matrix(rows, selected, means, scales)
    interactions = [
        (base[:, left] * base[:, right]).reshape(-1, 1)
        for left in range(base.shape[1])
        for right in range(left + 1, base.shape[1])
    ]
    matrix = np.column_stack([base, *interactions]) if interactions else base
    targets = np.asarray([_number(row.get("research_gross_return")) for row in rows])
    alpha = 0.1
    return {
        "kind": "selected_interaction_ridge",
        "feature_names": selected,
        "means": means,
        "scales": scales,
        "coefficients": _ridge_coefficients(matrix, targets, alpha),
        "alpha": alpha,
        "parameter_count": matrix.shape[1] + 1,
    }


def _predict_selected_features(model: dict[str, Any], rows: list[dict[str, Any]]) -> list[float]:
    selected = tuple(model["feature_names"])
    base = _standardized_matrix(rows, selected, model["means"], model["scales"])
    interactions = [
        (base[:, left] * base[:, right]).reshape(-1, 1)
        for left in range(base.shape[1])
        for right in range(left + 1, base.shape[1])
    ]
    matrix = np.column_stack([base, *interactions]) if interactions else base
    return _ridge_predict(matrix, model["coefficients"]).tolist()


def _landmark_indices(row_count: int, maximum: int = 8) -> tuple[int, ...]:
    count = min(maximum, row_count)
    return tuple(sorted(set(np.linspace(0, row_count - 1, count).astype(int).tolist())))


def _rbf_features(matrix: np.ndarray, landmarks: np.ndarray, gamma: float) -> np.ndarray:
    squared = np.sum((matrix[:, None, :] - landmarks[None, :, :]) ** 2, axis=2)
    return np.exp(-gamma * squared)


def _fit_rbf_kernel(rows: list[dict[str, Any]], *, alpha: float) -> dict[str, Any]:
    means, scales = _standardization(rows, QUANTUM_FEATURES)
    matrix = _standardized_matrix(rows, QUANTUM_FEATURES, means, scales)
    indices = _landmark_indices(len(rows))
    landmarks = matrix[list(indices)]
    gamma = 1.0 / len(QUANTUM_FEATURES)
    features = _rbf_features(matrix, landmarks, gamma)
    targets = np.asarray([_number(row.get("research_gross_return")) for row in rows])
    return {
        "kind": "rbf_nystrom_ridge",
        "feature_names": QUANTUM_FEATURES,
        "means": means,
        "scales": scales,
        "landmarks": landmarks,
        "gamma": gamma,
        "alpha": alpha,
        "coefficients": _ridge_coefficients(features, targets, alpha),
        "parameter_count": features.shape[1] + 1,
    }


def _predict_rbf_kernel(model: dict[str, Any], rows: list[dict[str, Any]]) -> list[float]:
    matrix = _standardized_matrix(
        rows, tuple(model["feature_names"]), model["means"], model["scales"]
    )
    features = _rbf_features(matrix, model["landmarks"], _number(model["gamma"]))
    return _ridge_predict(features, model["coefficients"]).tolist()


def _quantum_states(matrix: np.ndarray) -> np.ndarray:
    from qiskit.quantum_info import Statevector

    from orchestrator.qadam_local_quantum_discovery import build_feature_map_circuit

    qubit_count = min(8, max(4, matrix.shape[1]))
    return np.asarray(
        [
            np.asarray(
                Statevector.from_instruction(build_feature_map_circuit(vector, qubit_count)).data
            )
            for vector in matrix
        ],
        dtype=complex,
    )


def _fidelity_features(states: np.ndarray, landmarks: np.ndarray) -> np.ndarray:
    overlaps = states @ np.conjugate(landmarks.T)
    return np.abs(overlaps) ** 2


def _fit_quantum_kernel(rows: list[dict[str, Any]], *, alpha: float) -> dict[str, Any]:
    means, scales = _standardization(rows, QUANTUM_FEATURES)
    matrix = _standardized_matrix(rows, QUANTUM_FEATURES, means, scales)
    indices = _landmark_indices(len(rows))
    landmark_vectors = matrix[list(indices)]
    states = _quantum_states(matrix)
    landmark_states = states[list(indices)]
    features = _fidelity_features(states, landmark_states)
    targets = np.asarray([_number(row.get("research_gross_return")) for row in rows])
    return {
        "kind": "qiskit_statevector_fidelity_nystrom_ridge",
        "feature_names": QUANTUM_FEATURES,
        "means": means,
        "scales": scales,
        "landmark_vectors": landmark_vectors,
        "alpha": alpha,
        "coefficients": _ridge_coefficients(features, targets, alpha),
        "parameter_count": features.shape[1] + 1,
        "qubit_count": min(8, max(4, len(QUANTUM_FEATURES))),
        "circuit_evaluation_count": len(rows) + len(indices),
    }


def _predict_quantum_kernel(model: dict[str, Any], rows: list[dict[str, Any]]) -> list[float]:
    matrix = _standardized_matrix(
        rows, tuple(model["feature_names"]), model["means"], model["scales"]
    )
    states = _quantum_states(matrix)
    landmark_states = _quantum_states(model["landmark_vectors"])
    features = _fidelity_features(states, landmark_states)
    return _ridge_predict(features, model["coefficients"]).tolist()


def _fit_model(method: str, rows: list[dict[str, Any]], parameter: float) -> dict[str, Any]:
    if method == "nonlinear_feature_interactions":
        return _fit_polynomial(rows, alpha=parameter)
    if method == "regime_path_dependence":
        return _fit_regime_path(rows, minimum_group=int(parameter))
    if method == "ordinal_permutation_entropy":
        return _fit_entropy(rows, alpha=parameter)
    if method == "clustering_state_transitions":
        return _fit_cluster_transition(rows, cluster_count=int(parameter))
    if method == "constrained_combinatorial_feature_selection":
        return _fit_selected_features(rows, feature_count=int(parameter))
    if method == QUANTUM_METHOD:
        return _fit_quantum_kernel(rows, alpha=parameter)
    if method == NEGATIVE_CONTROL_METHOD:
        return _fit_polynomial(rows, alpha=parameter, target_shift=17)
    raise ValueError(f"unknown_or9_method:{method}")


def _predict_model(model: dict[str, Any], rows: list[dict[str, Any]]) -> list[float]:
    kind = model.get("kind")
    if kind == "polynomial_ridge":
        return _predict_polynomial(model, rows)
    if kind == "regime_path":
        return _predict_regime_path(model, rows)
    if kind == "entropy_ridge":
        return _predict_entropy(model, rows)
    if kind == "cluster_transition":
        return _predict_cluster_transition(model, rows)
    if kind == "selected_interaction_ridge":
        return _predict_selected_features(model, rows)
    if kind == "qiskit_statevector_fidelity_nystrom_ridge":
        return _predict_quantum_kernel(model, rows)
    raise ValueError(f"unknown_or9_model_kind:{kind}")


def _parameter_grid(method: str) -> tuple[float, ...]:
    if method in {
        "nonlinear_feature_interactions",
        "ordinal_permutation_entropy",
        QUANTUM_METHOD,
        NEGATIVE_CONTROL_METHOD,
    }:
        return (0.01, 0.1, 1.0)
    if method == "regime_path_dependence":
        return (5.0, 10.0, 20.0)
    if method == "clustering_state_transitions":
        return (3.0, 4.0, 5.0)
    if method == "constrained_combinatorial_feature_selection":
        return (3.0, 5.0, 7.0)
    raise ValueError(f"unknown_or9_parameter_grid:{method}")


def _decision_returns(
    rows: list[dict[str, Any]], predictions: list[float], threshold: float
) -> list[float]:
    output: list[float] = []
    for row, prediction in zip(rows, predictions):
        if prediction == 0.0 or abs(prediction) < threshold:
            output.append(0.0)
            continue
        direction = "long" if prediction > 0 else "short"
        net_return = row.get(f"{direction}_net_return")
        output.append(_number(net_return) if net_return is not None else 0.0)
    return output


def _incremental_test(method_returns: list[float], baseline_returns: list[float]) -> dict[str, Any]:
    differences = [method - baseline for method, baseline in zip(method_returns, baseline_returns)]
    uncertainty = dependence_aware_mean_uncertainty(differences)
    mean_value = uncertainty.get("mean")
    standard_error = uncertainty.get("standard_error")
    if mean_value is None or standard_error is None or standard_error <= 0:
        p_value = 1.0
    else:
        statistic = float(mean_value) / float(standard_error)
        p_value = 0.5 * math.erfc(statistic / math.sqrt(2.0))
    return {
        "incremental_mean_decision_return": mean_value,
        "incremental_standard_error": standard_error,
        "effective_block_count": uncertainty.get("effective_block_count"),
        "raw_p_value": max(0.0, min(1.0, p_value)),
        "method_mean_decision_return": _mean(method_returns),
        "baseline_mean_decision_return": _mean(baseline_returns),
    }


def _validation_objective(
    rows: list[dict[str, Any]], predictions: list[float], threshold: float
) -> float:
    metrics = evaluate_predictions(rows, predictions, threshold)
    if int(metrics.get("trade_count") or 0) < max(5, int(len(rows) * 0.10)):
        return -1e9
    return _number(metrics.get("mean_net_return"), -1.0) * math.sqrt(
        int(metrics.get("trade_count") or 0)
    )


def _select_model(
    method: str,
    train: list[dict[str, Any]],
    validation: list[dict[str, Any]],
) -> tuple[float, float, dict[str, Any]]:
    candidates: list[tuple[float, float, float, dict[str, Any]]] = []
    for parameter in _parameter_grid(method):
        model = _fit_model(method, train, parameter)
        train_predictions = _predict_model(model, train)
        validation_predictions = _predict_model(model, validation)
        threshold, threshold_audit = tune_threshold(
            train_predictions, validation, validation_predictions
        )
        candidates.append(
            (
                _validation_objective(validation, validation_predictions, threshold),
                -parameter,
                threshold,
                {
                    "parameter": parameter,
                    "threshold_audit": threshold_audit,
                    "validation_metrics": {
                        key: value
                        for key, value in evaluate_predictions(
                            validation, validation_predictions, threshold
                        ).items()
                        if key != "returns"
                    },
                },
            )
        )
    _objective, negative_parameter, threshold, audit = max(
        candidates, key=lambda item: (item[0], item[1])
    )
    return -negative_parameter, threshold, audit


def _select_linear_baseline(
    train: list[dict[str, Any]], validation: list[dict[str, Any]]
) -> tuple[float, dict[str, Any]]:
    model = fit_method("strategy_blind_linear_model", train)
    train_predictions = predict_method(model, train)
    validation_predictions = predict_method(model, validation)
    return tune_threshold(train_predictions, validation, validation_predictions)


def _select_rbf_baseline(
    train: list[dict[str, Any]], validation: list[dict[str, Any]]
) -> tuple[float, float, dict[str, Any]]:
    candidates: list[tuple[float, float, float, dict[str, Any]]] = []
    for alpha in (0.01, 0.1, 1.0):
        model = _fit_rbf_kernel(train, alpha=alpha)
        train_predictions = _predict_rbf_kernel(model, train)
        validation_predictions = _predict_rbf_kernel(model, validation)
        threshold, threshold_audit = tune_threshold(
            train_predictions, validation, validation_predictions
        )
        candidates.append(
            (
                _validation_objective(validation, validation_predictions, threshold),
                -alpha,
                threshold,
                {"alpha": alpha, "threshold_audit": threshold_audit},
            )
        )
    _objective, negative_alpha, threshold, audit = max(
        candidates, key=lambda item: (item[0], item[1])
    )
    return -negative_alpha, threshold, audit


def _experiment_group_id(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("strategy_family_id") or "unclassified"),
        str(row["instrument"]),
        str(row["horizon"]),
    )


def _clean_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in metrics.items() if key != "returns"}


def _run_group_method(
    *,
    group: tuple[str, str, str],
    rows: list[dict[str, Any]],
    method: str,
    quantum_available: bool,
) -> dict[str, Any]:
    holdout_count = max(40, int(len(rows) * 0.20))
    pre_holdout = rows[:-holdout_count]
    holdout = rows[-holdout_count:]
    validation_count = max(30, int(len(pre_holdout) * 0.20))
    train = pre_holdout[:-validation_count]
    validation = pre_holdout[-validation_count:]
    if method == QUANTUM_METHOD and not quantum_available:
        return {
            "strategy_family_id": group[0],
            "instrument": group[1],
            "horizon": group[2],
            "method": method,
            "status": "fallback_only_qiskit_unavailable",
            "fallback_used": True,
            "matched_classical_baseline": "rbf_nystrom_kernel_ridge",
            "holdout_untouched_during_tuning": True,
            "raw_p_value": 1.0,
        }

    baseline_start = perf_counter()
    if method == QUANTUM_METHOD:
        baseline_parameter, baseline_threshold, baseline_selection = _select_rbf_baseline(
            train, validation
        )
        baseline_model = _fit_rbf_kernel(pre_holdout, alpha=baseline_parameter)
        baseline_predictions = _predict_rbf_kernel(baseline_model, holdout)
        baseline_name = "rbf_nystrom_kernel_ridge"
    else:
        baseline_threshold, baseline_selection = _select_linear_baseline(train, validation)
        baseline_model = fit_method("strategy_blind_linear_model", pre_holdout)
        baseline_predictions = predict_method(baseline_model, holdout)
        baseline_name = "strategy_blind_linear_model"
    baseline_runtime = perf_counter() - baseline_start
    baseline_metrics_full = evaluate_predictions(holdout, baseline_predictions, baseline_threshold)
    baseline_returns = _decision_returns(holdout, baseline_predictions, baseline_threshold)

    method_start = perf_counter()
    parameter, threshold, selection_audit = _select_model(method, train, validation)
    final_model = _fit_model(method, pre_holdout, parameter)
    method_predictions = _predict_model(final_model, holdout)
    method_runtime = perf_counter() - method_start
    method_metrics_full = evaluate_predictions(holdout, method_predictions, threshold)
    method_returns = _decision_returns(holdout, method_predictions, threshold)
    incremental = _incremental_test(method_returns, baseline_returns)
    complexity_penalty = max(
        0.0,
        min(
            1.0,
            (int(final_model.get("parameter_count") or 1) - 13)
            / max(1, int(final_model.get("parameter_count") or 1) + 13),
        ),
    )
    latency_penalty = max(
        0.0,
        min(1.0, (method_runtime - baseline_runtime) / max(method_runtime, 1e-9)),
    )
    return {
        "strategy_family_id": group[0],
        "instrument": group[1],
        "horizon": group[2],
        "method": method,
        "status": "measured",
        "negative_control": method == NEGATIVE_CONTROL_METHOD,
        "matched_classical_baseline": baseline_name,
        "training_row_count": len(train),
        "validation_row_count": len(validation),
        "pre_holdout_row_count": len(pre_holdout),
        "holdout_row_count": len(holdout),
        "holdout_start_at": holdout[0]["decision_at"],
        "holdout_end_at": holdout[-1]["decision_at"],
        "holdout_untouched_during_tuning": True,
        "selected_parameter": parameter,
        "selected_threshold": threshold,
        "selection_audit": selection_audit,
        "baseline_selection_audit": baseline_selection,
        "method_holdout_metrics": _clean_metrics(method_metrics_full),
        "classical_holdout_metrics": _clean_metrics(baseline_metrics_full),
        **incremental,
        "raw_p_value": incremental["raw_p_value"],
        "method_runtime_seconds": round(method_runtime, 6),
        "classical_runtime_seconds": round(baseline_runtime, 6),
        "complexity_penalty": round(complexity_penalty, 6),
        "latency_penalty": round(latency_penalty, 6),
        "reliability": 1.0,
        "fallback_used": False,
        "model_kind": final_model.get("kind"),
        "model_parameter_count": int(final_model.get("parameter_count") or 0),
        "qubit_count": final_model.get("qubit_count"),
        "circuit_evaluation_count": final_model.get("circuit_evaluation_count"),
        "provider_cost_usd": 0.0,
    }


def run_nonlinear_quantum_experiments(
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    independent = [row for row in rows if row.get("independent_sample") is True]
    grouped: defaultdict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in independent:
        grouped[_experiment_group_id(row)].append(row)
    eligible = {
        key: enrich_or9_rows(group_rows)
        for key, group_rows in grouped.items()
        if len(group_rows) >= MINIMUM_INDEPENDENT_ROWS
    }
    dependency = quantum_dependency_truth()
    quantum_available = dependency["local_statevector_simulation_available"] is True
    records: list[dict[str, Any]] = []
    for group, group_rows in sorted(eligible.items()):
        for method in EXPERIMENT_METHODS:
            records.append(
                _run_group_method(
                    group=group,
                    rows=group_rows,
                    method=method,
                    quantum_available=quantum_available,
                )
            )
        records.append(
            _run_group_method(
                group=group,
                rows=group_rows,
                method=NEGATIVE_CONTROL_METHOD,
                quantum_available=quantum_available,
            )
        )

    measured = [record for record in records if record.get("status") == "measured"]
    adjustments = benjamini_hochberg(
        [_number(record.get("raw_p_value"), 1.0) for record in measured],
        alpha=FALSE_DISCOVERY_ALPHA,
    )
    for record, adjustment in zip(measured, adjustments):
        record["adjusted_p_value"] = adjustment["adjusted_p_value"]
        record["false_discovery_adjusted_significant"] = adjustment["significant"]
        method_metrics = record.get("method_holdout_metrics") or {}
        reasons: list[str] = []
        if record.get("negative_control") is True:
            reasons.append("negative_control_never_incremental_value_candidate")
        if _number(record.get("incremental_mean_decision_return"), -1.0) <= 0:
            reasons.append("nonpositive_incremental_holdout_value")
        if adjustment["significant"] is not True:
            reasons.append("false_discovery_adjusted_result_not_significant")
        if int(method_metrics.get("trade_count") or 0) < MINIMUM_HOLDOUT_TRADES:
            reasons.append("insufficient_untouched_holdout_trades")
        if _number(method_metrics.get("mean_net_return"), -1.0) <= 0:
            reasons.append("nonpositive_cost_adjusted_method_return")
        if record.get("holdout_untouched_during_tuning") is not True:
            reasons.append("holdout_tuning_violation")
        record["incremental_value_candidate"] = not reasons
        record["rejection_reasons"] = reasons

    for record in records:
        if record.get("status") != "measured":
            record["adjusted_p_value"] = None
            record["false_discovery_adjusted_significant"] = False
            record["incremental_value_candidate"] = False
            record["rejection_reasons"] = ["experiment_not_measured"]

    return {
        "records": records,
        "dependency_truth": dependency,
        "independent_row_count": len(independent),
        "eligible_group_count": len(eligible),
        "measured_experiment_count": len(measured),
        "negative_control_experiment_count": sum(
            record.get("negative_control") is True for record in records
        ),
        "negative_control_false_positive_count": sum(
            record.get("negative_control") is True
            and record.get("incremental_value_candidate") is True
            for record in records
        ),
        "incremental_value_candidate_count": sum(
            record.get("incremental_value_candidate") is True
            for record in records
            if record.get("negative_control") is not True
        ),
    }
