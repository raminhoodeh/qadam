"""Deterministic empirical engine for OR-8 whole-universe backtesting."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import hashlib
import math
from statistics import fmean, median, pstdev
from typing import Any, Callable


BASELINE_METHODS = (
    "unconditional_market_return",
    "simple_momentum",
    "simple_reversal",
    "strategy_blind_linear_model",
    "shuffled_time_negative_control",
)
QADAM_METHODS = (
    "source_price_historical_occurrence",
    "lead_lag_event_study",
    "vector_analog_retrieval",
    "state_matrix_probability",
    "cross_source_divergence",
    "cross_asset_confirmation",
    "regime_conditioned_relationship",
)
ALL_METHODS = (*BASELINE_METHODS, *QADAM_METHODS)
NEGATIVE_CONTROL_METHODS = {"shuffled_time_negative_control"}
NEGATIVE_CONTROL_POLICY_REASONS = {
    "negative_control_cannot_validate",
    "comparator_method_not_edge_candidate",
}

MINIMUM_INDEPENDENT_ROWS = 150
MINIMUM_HOLDOUT_TRADES = 20
MINIMUM_EFFECTIVE_HOLDOUT_BLOCKS = 10
FALSE_DISCOVERY_ALPHA = 0.05

LINEAR_FEATURES = (
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
)
ANALOG_FEATURES = (
    "raw_pattern_score",
    "source_trust",
    "source_independence",
    "log_source_event_count",
    "rolling_volatility",
    "prior_return_5",
    "cross_asset_score",
)


@dataclass(frozen=True)
class WalkForwardFold:
    fold_id: str
    train_start: int
    train_end: int
    validation_start: int
    validation_end: int
    test_start: int
    test_end: int
    purge_size: int
    embargo_size: int


def chronological_walk_forward_folds(
    row_count: int,
    *,
    minimum_train_rows: int = 60,
    validation_rows: int = 20,
    test_rows: int = 20,
    purge_rows: int = 2,
    embargo_rows: int = 2,
) -> list[WalkForwardFold]:
    folds: list[WalkForwardFold] = []
    train_end = minimum_train_rows
    fold_index = 0
    while True:
        validation_start = train_end + purge_rows
        validation_end = validation_start + validation_rows
        test_start = validation_end + embargo_rows
        test_end = test_start + test_rows
        if test_end > row_count:
            break
        folds.append(
            WalkForwardFold(
                fold_id=f"fold-{fold_index:03d}",
                train_start=0,
                train_end=train_end,
                validation_start=validation_start,
                validation_end=validation_end,
                test_start=test_start,
                test_end=test_end,
                purge_size=purge_rows,
                embargo_size=embargo_rows,
            )
        )
        train_end += test_rows
        fold_index += 1
    return folds


def benjamini_hochberg(
    p_values: list[float], *, alpha: float = FALSE_DISCOVERY_ALPHA
) -> list[dict[str, Any]]:
    if not p_values:
        return []
    indexed = sorted(enumerate(p_values), key=lambda item: item[1])
    count = len(indexed)
    adjusted = [1.0] * count
    running_min = 1.0
    for rank_from_end, (original_index, p_value) in enumerate(
        reversed(indexed), start=1
    ):
        rank = count - rank_from_end + 1
        candidate = min(1.0, float(p_value) * count / rank)
        running_min = min(running_min, candidate)
        adjusted[original_index] = running_min
    return [
        {
            "index": index,
            "raw_p_value": float(p_value),
            "adjusted_p_value": adjusted[index],
            "significant": adjusted[index] <= alpha,
        }
        for index, p_value in enumerate(p_values)
    ]


def dependence_aware_mean_uncertainty(
    values: list[float], *, block_size: int = 5
) -> dict[str, Any]:
    if not values:
        return {
            "mean": None,
            "effective_block_count": 0,
            "standard_error": None,
            "state": "insufficient_sample",
        }
    blocks = [
        values[index : index + block_size]
        for index in range(0, len(values), block_size)
    ]
    block_means = [fmean(block) for block in blocks if block]
    mean_value = fmean(values)
    if len(block_means) < 2:
        standard_error = None
    else:
        block_mean = fmean(block_means)
        variance = sum((value - block_mean) ** 2 for value in block_means) / (
            len(block_means) - 1
        )
        standard_error = math.sqrt(variance / len(block_means))
    return {
        "mean": mean_value,
        "effective_block_count": len(block_means),
        "standard_error": standard_error,
        "state": (
            "measured"
            if standard_error is not None
            else "insufficient_independent_blocks"
        ),
    }


def _number(value: Any, default: float = 0.0) -> float:
    if value is None or isinstance(value, bool):
        return default
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def _quantile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * min(1.0, max(0.0, quantile))
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _mean(values: list[float], default: float = 0.0) -> float:
    return fmean(values) if values else default


def _feature(row: dict[str, Any], name: str) -> float:
    return _number(row.get(name))


def enrich_backtest_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add backward-looking momentum and same-time cross-asset context."""
    enriched = [dict(row) for row in rows]
    price_by_instrument: defaultdict[str, dict[str, float]] = defaultdict(dict)
    for row in enriched:
        price_by_instrument[str(row["instrument"])][str(row["decision_at"])] = _number(
            row.get("price_before")
        )
    prior_return: dict[tuple[str, str], float] = {}
    for instrument, dated_prices in price_by_instrument.items():
        ordered = sorted(dated_prices.items())
        for index, (decision_at, price) in enumerate(ordered):
            if index < 5 or ordered[index - 5][1] <= 0:
                value = 0.0
            else:
                value = (price / ordered[index - 5][1]) - 1.0
            prior_return[(instrument, decision_at)] = value
    scores_by_time: defaultdict[str, list[tuple[str, float]]] = defaultdict(list)
    for row in enriched:
        scores_by_time[str(row["decision_at"])].append(
            (str(row["instrument"]), _number(row.get("raw_pattern_score")))
        )
    for row in enriched:
        decision_at = str(row["decision_at"])
        instrument = str(row["instrument"])
        peers = [
            score
            for peer_instrument, score in scores_by_time[decision_at]
            if peer_instrument != instrument
        ]
        row["prior_return_5"] = prior_return.get((instrument, decision_at), 0.0)
        row["cross_asset_score"] = _mean(peers)
        row["log_source_event_count"] = math.log1p(
            max(0.0, _number(row.get("source_event_count")))
        )
        distinct_sources = max(1.0, _number(row.get("distinct_source_count"), 1.0))
        independent_sources = min(
            distinct_sources,
            max(0.0, _number(row.get("independent_source_cluster_count"))),
        )
        row["source_divergence"] = 1.0 - (
            independent_sources / distinct_sources
        )
    return enriched


def _target(row: dict[str, Any]) -> float:
    return _number(row.get("research_gross_return"))


def _fit_univariate(
    rows: list[dict[str, Any]], feature_name: str
) -> dict[str, Any]:
    xs = [_feature(row, feature_name) for row in rows]
    ys = [_target(row) for row in rows]
    x_mean = _mean(xs)
    y_mean = _mean(ys)
    variance = sum((value - x_mean) ** 2 for value in xs)
    slope = (
        sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys)) / variance
        if variance > 1e-15
        else 0.0
    )
    return {
        "kind": "univariate",
        "feature_name": feature_name,
        "intercept": y_mean - slope * x_mean,
        "slope": slope,
    }


def _solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float]:
    size = len(vector)
    augmented = [matrix[index][:] + [vector[index]] for index in range(size)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            continue
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        pivot_value = augmented[column][column]
        augmented[column] = [value / pivot_value for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            if abs(factor) < 1e-15:
                continue
            augmented[row] = [
                current - factor * pivot_current
                for current, pivot_current in zip(
                    augmented[row], augmented[column]
                )
            ]
    return [augmented[index][-1] for index in range(size)]


def _fit_ridge(rows: list[dict[str, Any]]) -> dict[str, Any]:
    means = {
        name: _mean([_feature(row, name) for row in rows])
        for name in LINEAR_FEATURES
    }
    scales = {
        name: max(
            1e-9,
            pstdev([_feature(row, name) for row in rows]) if len(rows) > 1 else 1.0,
        )
        for name in LINEAR_FEATURES
    }
    vectors = [
        [1.0]
        + [(_feature(row, name) - means[name]) / scales[name] for name in LINEAR_FEATURES]
        for row in rows
    ]
    targets = [_target(row) for row in rows]
    width = len(LINEAR_FEATURES) + 1
    gram = [[0.0] * width for _ in range(width)]
    rhs = [0.0] * width
    for vector, target in zip(vectors, targets):
        for left in range(width):
            rhs[left] += vector[left] * target
            for right in range(width):
                gram[left][right] += vector[left] * vector[right]
    ridge = 1e-3 * max(1, len(rows))
    for index in range(1, width):
        gram[index][index] += ridge
    return {
        "kind": "ridge",
        "feature_names": list(LINEAR_FEATURES),
        "means": means,
        "scales": scales,
        "coefficients": _solve_linear_system(gram, rhs),
    }


def _score_bins(rows: list[dict[str, Any]]) -> list[float]:
    scores = [_feature(row, "raw_pattern_score") for row in rows]
    return [_quantile(scores, 1 / 3), _quantile(scores, 2 / 3)]


def _bin(value: float, boundaries: list[float]) -> int:
    return sum(value > boundary for boundary in boundaries)


def _fit_group_means(
    rows: list[dict[str, Any]],
    key_builder: Callable[[dict[str, Any], list[float]], tuple[Any, ...]],
) -> dict[str, Any]:
    boundaries = _score_bins(rows)
    grouped: defaultdict[tuple[Any, ...], list[float]] = defaultdict(list)
    for row in rows:
        grouped[key_builder(row, boundaries)].append(_target(row))
    return {
        "kind": "group_means",
        "boundaries": boundaries,
        "means": {repr(key): _mean(values) for key, values in grouped.items()},
        "fallback": _mean([_target(row) for row in rows]),
        "key_builder": key_builder,
    }


def _fit_analog(rows: list[dict[str, Any]]) -> dict[str, Any]:
    means = {
        name: _mean([_feature(row, name) for row in rows])
        for name in ANALOG_FEATURES
    }
    scales = {
        name: max(
            1e-9,
            pstdev([_feature(row, name) for row in rows]) if len(rows) > 1 else 1.0,
        )
        for name in ANALOG_FEATURES
    }
    return {
        "kind": "analog",
        "feature_names": list(ANALOG_FEATURES),
        "means": means,
        "scales": scales,
        "vectors": [
            [(_feature(row, name) - means[name]) / scales[name] for name in ANALOG_FEATURES]
            for row in rows
        ],
        "targets": [_target(row) for row in rows],
        "neighbors": min(15, max(3, int(math.sqrt(len(rows))))),
    }


def _source_occurrence_key(
    row: dict[str, Any], boundaries: list[float]
) -> tuple[Any, ...]:
    return (
        tuple(row.get("source_keys", [])),
        _bin(_feature(row, "raw_pattern_score"), boundaries),
    )


def _state_matrix_key(
    row: dict[str, Any], boundaries: list[float]
) -> tuple[Any, ...]:
    return (
        _bin(_feature(row, "raw_pattern_score"), boundaries),
        str(row.get("regime") or "unclassified"),
        int(_feature(row, "distinct_source_count") >= 2.0),
    )


def _regime_key(row: dict[str, Any], boundaries: list[float]) -> tuple[Any, ...]:
    return (
        str(row.get("regime") or "unclassified"),
        _bin(_feature(row, "raw_pattern_score"), boundaries),
    )


def fit_method(method: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"kind": "empty", "method": method}
    if method == "unconditional_market_return":
        return {"kind": "constant", "value": _mean([_target(row) for row in rows])}
    if method == "simple_momentum":
        return {"kind": "direct", "feature_name": "prior_return_5", "scale": 1.0}
    if method == "simple_reversal":
        return {"kind": "direct", "feature_name": "prior_return_5", "scale": -1.0}
    if method == "strategy_blind_linear_model":
        return _fit_ridge(rows)
    if method == "shuffled_time_negative_control":
        return {
            "kind": "deterministic_noise",
            "scale": max(1e-9, pstdev([_target(row) for row in rows])),
        }
    if method == "source_price_historical_occurrence":
        return _fit_group_means(rows, _source_occurrence_key)
    if method == "lead_lag_event_study":
        return _fit_univariate(rows, "log_source_event_count")
    if method == "vector_analog_retrieval":
        return _fit_analog(rows)
    if method == "state_matrix_probability":
        return _fit_group_means(rows, _state_matrix_key)
    if method == "cross_source_divergence":
        return _fit_univariate(rows, "source_divergence")
    if method == "cross_asset_confirmation":
        return _fit_univariate(rows, "cross_asset_score")
    if method == "regime_conditioned_relationship":
        return _fit_group_means(rows, _regime_key)
    raise ValueError(f"unknown_backtest_method:{method}")


def _noise_prediction(score_id: str, scale: float) -> float:
    digest = hashlib.sha256(f"or8-negative-control:{score_id}".encode()).digest()
    unit = int.from_bytes(digest[:8], "big") / float(2**64 - 1)
    return (unit * 2.0 - 1.0) * scale


def predict_method(model: dict[str, Any], rows: list[dict[str, Any]]) -> list[float]:
    kind = model.get("kind")
    if kind == "empty":
        return [0.0] * len(rows)
    if kind == "constant":
        return [_number(model.get("value"))] * len(rows)
    if kind == "direct":
        return [
            _feature(row, str(model["feature_name"])) * _number(model.get("scale"), 1.0)
            for row in rows
        ]
    if kind == "deterministic_noise":
        return [
            _noise_prediction(str(row["score_id"]), _number(model.get("scale"), 1.0))
            for row in rows
        ]
    if kind == "univariate":
        return [
            _number(model.get("intercept"))
            + _number(model.get("slope"))
            * _feature(row, str(model["feature_name"]))
            for row in rows
        ]
    if kind == "ridge":
        coefficients = list(model["coefficients"])
        output: list[float] = []
        for row in rows:
            vector = [1.0] + [
                (_feature(row, name) - _number(model["means"].get(name)))
                / max(1e-9, _number(model["scales"].get(name), 1.0))
                for name in model["feature_names"]
            ]
            output.append(sum(left * right for left, right in zip(coefficients, vector)))
        return output
    if kind == "group_means":
        builder = model["key_builder"]
        boundaries = list(model["boundaries"])
        means = model["means"]
        fallback = _number(model.get("fallback"))
        return [
            _number(means.get(repr(builder(row, boundaries))), fallback) for row in rows
        ]
    if kind == "analog":
        output = []
        for row in rows:
            vector = [
                (_feature(row, name) - _number(model["means"].get(name)))
                / max(1e-9, _number(model["scales"].get(name), 1.0))
                for name in model["feature_names"]
            ]
            distances = sorted(
                (
                    sum((left - right) ** 2 for left, right in zip(vector, candidate)),
                    target,
                )
                for candidate, target in zip(model["vectors"], model["targets"])
            )[: int(model["neighbors"])]
            weighted = [
                (1.0 / (math.sqrt(distance) + 1e-6), target)
                for distance, target in distances
            ]
            weight_total = sum(weight for weight, _target_value in weighted)
            output.append(
                sum(weight * target for weight, target in weighted) / weight_total
                if weight_total > 0
                else 0.0
            )
        return output
    raise ValueError(f"unknown_backtest_model_kind:{kind}")


def _maximum_drawdown(returns: list[float]) -> float | None:
    if not returns:
        return None
    equity = 1.0
    peak = 1.0
    maximum = 0.0
    for value in returns:
        equity *= max(0.0, 1.0 + value)
        peak = max(peak, equity)
        drawdown = (equity / peak) - 1.0 if peak > 0 else -1.0
        maximum = min(maximum, drawdown)
    return maximum


def _one_sided_positive_p_value(returns: list[float]) -> float:
    uncertainty = dependence_aware_mean_uncertainty(returns)
    mean_value = uncertainty.get("mean")
    standard_error = uncertainty.get("standard_error")
    if mean_value is None or standard_error is None or standard_error <= 0:
        return 1.0
    statistic = float(mean_value) / float(standard_error)
    return min(1.0, max(0.0, 0.5 * math.erfc(statistic / math.sqrt(2.0))))


def _one_sided_mean_difference_p_value(
    mean_value: float | None,
    standard_error: float | None,
    baseline_mean: float | None,
    baseline_standard_error: float | None,
) -> tuple[float, float | None, float | None]:
    if mean_value is None or baseline_mean is None:
        return 1.0, None, None
    difference = float(mean_value) - float(baseline_mean)
    if (
        standard_error is None
        or baseline_standard_error is None
        or standard_error < 0
        or baseline_standard_error < 0
    ):
        return 1.0, difference, None
    difference_standard_error = math.sqrt(
        float(standard_error) ** 2 + float(baseline_standard_error) ** 2
    )
    if difference_standard_error <= 0:
        return 1.0, difference, difference_standard_error
    statistic = difference / difference_standard_error
    p_value = 0.5 * math.erfc(statistic / math.sqrt(2.0))
    return (
        min(1.0, max(0.0, p_value)),
        difference,
        difference_standard_error,
    )


def evaluate_predictions(
    rows: list[dict[str, Any]], predictions: list[float], threshold: float
) -> dict[str, Any]:
    selected_returns: list[float] = []
    selected_gross: list[float] = []
    selected_rows: list[dict[str, Any]] = []
    direction_counts: Counter[str] = Counter()
    missing_cost_count = 0
    for row, prediction in zip(rows, predictions):
        if abs(prediction) < threshold or prediction == 0.0:
            continue
        direction = "long" if prediction > 0 else "short"
        net_value = row.get(f"{direction}_net_return")
        execution_gross = row.get("execution_gross_return")
        if net_value is None or execution_gross is None:
            missing_cost_count += 1
            continue
        net_return = _number(net_value)
        gross_return = _number(execution_gross) * (1.0 if direction == "long" else -1.0)
        selected_returns.append(net_return)
        selected_gross.append(gross_return)
        selected_rows.append(row)
        direction_counts[direction] += 1
    uncertainty = dependence_aware_mean_uncertainty(selected_returns)
    year_counts = Counter(str(row["decision_at"])[:4] for row in selected_rows)
    regime_values: defaultdict[str, list[float]] = defaultdict(list)
    source_counts: Counter[str] = Counter()
    for row, net_return in zip(selected_rows, selected_returns):
        regime_values[str(row.get("regime") or "unclassified")].append(net_return)
        source_counts.update(row.get("source_keys", []))
    total_return = 1.0
    for value in selected_returns:
        total_return *= max(0.0, 1.0 + value)
    trade_count = len(selected_returns)
    return {
        "state": "measured" if trade_count else "no_cost_eligible_decisions",
        "threshold": threshold,
        "eligible_row_count": len(rows),
        "trade_count": trade_count,
        "missing_cost_outcome_count": missing_cost_count,
        "mean_net_return": uncertainty.get("mean"),
        "mean_gross_return": _mean(selected_gross) if selected_gross else None,
        "mean_cost_drag": (
            _mean(
                [gross - net for gross, net in zip(selected_gross, selected_returns)]
            )
            if selected_returns
            else None
        ),
        "hit_rate": (
            sum(value > 0 for value in selected_returns) / trade_count
            if trade_count
            else None
        ),
        "cumulative_net_return": total_return - 1.0 if trade_count else None,
        "maximum_drawdown": _maximum_drawdown(selected_returns),
        "standard_error": uncertainty.get("standard_error"),
        "effective_block_count": uncertainty.get("effective_block_count"),
        "raw_p_value": _one_sided_positive_p_value(selected_returns),
        "direction_counts": dict(sorted(direction_counts.items())),
        "year_counts": dict(sorted(year_counts.items())),
        "maximum_year_concentration": (
            max(year_counts.values()) / trade_count if trade_count else None
        ),
        "regime_mean_net_returns": {
            regime: _mean(values) for regime, values in sorted(regime_values.items())
        },
        "source_selected_counts": dict(sorted(source_counts.items())),
        "selected_score_id_hash": hashlib.sha256(
            "\n".join(str(row["score_id"]) for row in selected_rows).encode()
        ).hexdigest(),
        "returns": selected_returns,
    }


def tune_threshold(
    train_predictions: list[float],
    validation_rows: list[dict[str, Any]],
    validation_predictions: list[float],
) -> tuple[float, dict[str, Any]]:
    magnitudes = [abs(value) for value in train_predictions if value != 0.0]
    candidates = sorted(
        {
            0.0,
            _quantile(magnitudes, 0.50),
            _quantile(magnitudes, 0.70),
            _quantile(magnitudes, 0.85),
        }
    )
    minimum_trades = max(5, int(len(validation_rows) * 0.10))
    ranked: list[tuple[float, float, dict[str, Any]]] = []
    for threshold in candidates:
        metrics = evaluate_predictions(
            validation_rows, validation_predictions, threshold
        )
        if int(metrics["trade_count"]) < minimum_trades:
            objective = -1e9
        else:
            mean_return = _number(metrics.get("mean_net_return"), -1.0)
            objective = mean_return * math.sqrt(int(metrics["trade_count"]))
        ranked.append((objective, -threshold, metrics))
    objective, negative_threshold, selected = max(ranked, key=lambda item: item[:2])
    return -negative_threshold, {
        "candidate_threshold_count": len(candidates),
        "minimum_validation_trades": minimum_trades,
        "selected_objective": objective,
        "selected_validation_metrics": {
            key: value for key, value in selected.items() if key != "returns"
        },
    }


def _group_id(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row["strategy_family_id"]),
        str(row["instrument"]),
        str(row["horizon"]),
    )


def _fold_parameters(pre_holdout_count: int) -> dict[str, int]:
    return {
        "minimum_train_rows": max(60, int(pre_holdout_count * 0.40)),
        "validation_rows": max(20, int(pre_holdout_count * 0.10)),
        "test_rows": max(20, int(pre_holdout_count * 0.10)),
        "purge_rows": 1,
        "embargo_rows": 1,
    }


def _fold_result(
    *,
    hypothesis_id: str,
    method: str,
    fold: WalkForwardFold,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    train_rows = rows[fold.train_start : fold.train_end]
    validation_rows = rows[fold.validation_start : fold.validation_end]
    test_rows = rows[fold.test_start : fold.test_end]
    model = fit_method(method, train_rows)
    train_predictions = predict_method(model, train_rows)
    validation_predictions = predict_method(model, validation_rows)
    threshold, tuning = tune_threshold(
        train_predictions, validation_rows, validation_predictions
    )
    test_predictions = predict_method(model, test_rows)
    test_metrics = evaluate_predictions(test_rows, test_predictions, threshold)
    return {
        "artifact_type": "qadam_backtest_fold_result",
        "hypothesis_id": hypothesis_id,
        "method_id": method,
        "fold": asdict(fold),
        "train_start_at": train_rows[0]["decision_at"],
        "train_end_at": train_rows[-1]["decision_at"],
        "validation_start_at": validation_rows[0]["decision_at"],
        "validation_end_at": validation_rows[-1]["decision_at"],
        "test_start_at": test_rows[0]["decision_at"],
        "test_end_at": test_rows[-1]["decision_at"],
        "selected_threshold": threshold,
        "threshold_tuning": tuning,
        "test_metrics": {
            key: value for key, value in test_metrics.items() if key != "returns"
        },
        "holdout_accessed": False,
        "strategy_mutation_allowed": False,
        "edge_created": False,
    }


def _hypothesis_result(
    method: str,
    group_key: tuple[str, str, str],
    rows: list[dict[str, Any]],
    *,
    stable_id_builder: Callable[..., str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    strategy, instrument, horizon = group_key
    hypothesis_id = stable_id_builder(
        "backtest-hypothesis", method, strategy, instrument, horizon
    )
    rows = sorted(rows, key=lambda row: (row["decision_at"], row["score_id"]))
    source_keys = sorted(
        {source for row in rows for source in row.get("source_keys", [])}
    )
    base = {
        "artifact_type": "qadam_backtest_hypothesis_result",
        "hypothesis_id": hypothesis_id,
        "method_id": method,
        "method_class": (
            "qadam" if method in QADAM_METHODS else "baseline"
        ),
        "negative_control": method in NEGATIVE_CONTROL_METHODS,
        "strategy_family_id": strategy,
        "instrument": instrument,
        "horizon": horizon,
        "source_keys": source_keys,
        "independent_row_count": len(rows),
        "first_decision_at": rows[0]["decision_at"] if rows else None,
        "last_decision_at": rows[-1]["decision_at"] if rows else None,
        "cost_adjusted": True,
        "chronological": True,
        "holdout_untouched_during_tuning": True,
        "false_discovery_adjusted_state": "pending",
        "historical_edge_candidate": False,
        "edge_created": False,
        "strategy_mutation_allowed": False,
        "candidate_creation_allowed": False,
        "order_creation_allowed": False,
        "proof_credit_allowed": False,
    }
    if len(rows) < MINIMUM_INDEPENDENT_ROWS:
        return (
            {
                **base,
                "status": "rejected_insufficient_independent_history",
                "fold_count": 0,
                "holdout_metrics": None,
                "walk_forward_metrics": None,
                "raw_p_value": 1.0,
                "rejection_reasons": ["insufficient_independent_history"],
            },
            [],
        )
    holdout_count = max(40, int(len(rows) * 0.20))
    pre_holdout = rows[:-holdout_count]
    holdout = rows[-holdout_count:]
    fold_parameters = _fold_parameters(len(pre_holdout))
    folds = chronological_walk_forward_folds(len(pre_holdout), **fold_parameters)
    if not folds:
        return (
            {
                **base,
                "status": "rejected_no_walk_forward_fold",
                "pre_holdout_row_count": len(pre_holdout),
                "holdout_row_count": len(holdout),
                "fold_count": 0,
                "fold_parameters": fold_parameters,
                "holdout_metrics": None,
                "walk_forward_metrics": None,
                "raw_p_value": 1.0,
                "rejection_reasons": ["no_valid_walk_forward_fold"],
            },
            [],
        )
    fold_results = [
        _fold_result(
            hypothesis_id=hypothesis_id,
            method=method,
            fold=fold,
            rows=pre_holdout,
        )
        for fold in folds
    ]
    fold_returns = [
        _number(result["test_metrics"].get("mean_net_return"))
        for result in fold_results
        if int(result["test_metrics"].get("trade_count") or 0) > 0
    ]
    fold_trade_count = sum(
        int(result["test_metrics"].get("trade_count") or 0)
        for result in fold_results
    )
    selected_thresholds = [float(result["selected_threshold"]) for result in fold_results]
    final_threshold = median(selected_thresholds) if selected_thresholds else 0.0
    final_model = fit_method(method, pre_holdout)
    holdout_predictions = predict_method(final_model, holdout)
    holdout_metrics = evaluate_predictions(holdout, holdout_predictions, final_threshold)
    holdout_returns = list(holdout_metrics.pop("returns"))
    walk_forward_uncertainty = dependence_aware_mean_uncertainty(fold_returns)
    walk_forward = {
        "fold_count": len(folds),
        "fold_trade_count": fold_trade_count,
        "positive_fold_ratio": (
            sum(value > 0 for value in fold_returns) / len(fold_returns)
            if fold_returns
            else 0.0
        ),
        "mean_fold_net_return": (
            _mean(fold_returns) if fold_returns else None
        ),
        "fold_return_standard_error": walk_forward_uncertainty.get(
            "standard_error"
        ),
        "selected_threshold_median": final_threshold,
        "selected_threshold_min": min(selected_thresholds),
        "selected_threshold_max": max(selected_thresholds),
    }
    rejection_reasons: list[str] = []
    if int(holdout_metrics["trade_count"]) < MINIMUM_HOLDOUT_TRADES:
        rejection_reasons.append("insufficient_untouched_holdout_trades")
    if int(holdout_metrics.get("effective_block_count") or 0) < MINIMUM_EFFECTIVE_HOLDOUT_BLOCKS:
        rejection_reasons.append("insufficient_effectively_independent_holdout_blocks")
    if _number(holdout_metrics.get("mean_net_return"), -1.0) <= 0:
        rejection_reasons.append("nonpositive_cost_adjusted_holdout_return")
    if walk_forward["positive_fold_ratio"] < 0.60:
        rejection_reasons.append("walk_forward_instability")
    if (
        holdout_metrics.get("maximum_year_concentration") is not None
        and float(holdout_metrics["maximum_year_concentration"]) > 0.70
    ):
        rejection_reasons.append("holdout_year_concentration")
    if (
        holdout_metrics.get("maximum_drawdown") is not None
        and float(holdout_metrics["maximum_drawdown"]) < -0.25
    ):
        rejection_reasons.append("holdout_drawdown_exceeded")
    if (
        holdout_metrics.get("mean_gross_return") is not None
        and float(holdout_metrics["mean_gross_return"]) > 0
        and _number(holdout_metrics.get("mean_net_return"), -1.0) <= 0
    ):
        rejection_reasons.append("cost_sensitive_edge_disappears_after_friction")
    return (
        {
            **base,
            "status": "tested_pending_multiple_testing",
            "pre_holdout_row_count": len(pre_holdout),
            "holdout_row_count": len(holdout),
            "holdout_start_at": holdout[0]["decision_at"],
            "holdout_end_at": holdout[-1]["decision_at"],
            "fold_count": len(folds),
            "fold_parameters": fold_parameters,
            "walk_forward_metrics": walk_forward,
            "holdout_metrics": holdout_metrics,
            "raw_p_value": _one_sided_positive_p_value(holdout_returns),
            "rejection_reasons": rejection_reasons,
        },
        fold_results,
    )


def _aggregate_dimension(
    results: list[dict[str, Any]], key: str
) -> list[dict[str, Any]]:
    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        grouped[str(result.get(key) or "unclassified")].append(result)
    output = []
    for value, records in sorted(grouped.items()):
        measured = [
            _number(record.get("holdout_metrics", {}).get("mean_net_return"))
            for record in records
            if isinstance(record.get("holdout_metrics"), dict)
            and record["holdout_metrics"].get("mean_net_return") is not None
        ]
        output.append(
            {
                key: value,
                "attempted_hypothesis_count": len(records),
                "measured_result_count": len(measured),
                "mean_holdout_net_return": _mean(measured) if measured else None,
                "historical_edge_candidate_count": sum(
                    record.get("historical_edge_candidate") is True
                    for record in records
                ),
            }
        )
    return output


def _source_contributions(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    source_results: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        for source in result.get("source_keys", []):
            source_results[str(source)].append(result)
    output = []
    for source, records in sorted(source_results.items()):
        measured = [
            _number(record.get("holdout_metrics", {}).get("mean_net_return"))
            for record in records
            if isinstance(record.get("holdout_metrics"), dict)
            and record["holdout_metrics"].get("mean_net_return") is not None
        ]
        output.append(
            {
                "source_key": source,
                "attempted_hypothesis_count": len(records),
                "measured_result_count": len(measured),
                "mean_holdout_net_return": _mean(measured) if measured else None,
                "historical_edge_candidate_count": sum(
                    record.get("historical_edge_candidate") is True
                    for record in records
                ),
                "causal_credit_claimed": False,
            }
        )
    return output


def run_whole_universe_backtest(
    rows: list[dict[str, Any]], *, stable_id_builder: Callable[..., str]
) -> dict[str, Any]:
    enriched = enrich_backtest_rows(rows)
    groups: defaultdict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in enriched:
        if row.get("independent_sample") is True:
            groups[_group_id(row)].append(row)
    results: list[dict[str, Any]] = []
    folds: list[dict[str, Any]] = []
    for group_key, group_rows in sorted(groups.items()):
        for method in ALL_METHODS:
            result, method_folds = _hypothesis_result(
                method,
                group_key,
                group_rows,
                stable_id_builder=stable_id_builder,
            )
            results.append(result)
            folds.extend(method_folds)
    unconditional_by_group = {
        (
            result["strategy_family_id"],
            result["instrument"],
            result["horizon"],
        ): result
        for result in results
        if result["method_id"] == "unconditional_market_return"
        and isinstance(result.get("holdout_metrics"), dict)
    }
    for result in results:
        result["raw_p_value_vs_zero"] = result.get("raw_p_value")
        if (
            result["method_id"] in (*QADAM_METHODS, *NEGATIVE_CONTROL_METHODS)
            and isinstance(result.get("holdout_metrics"), dict)
        ):
            group_key = (
                result["strategy_family_id"],
                result["instrument"],
                result["horizon"],
            )
            baseline = unconditional_by_group.get(group_key)
            baseline_metrics = (
                baseline.get("holdout_metrics", {}) if baseline else {}
            )
            p_value, difference, difference_standard_error = (
                _one_sided_mean_difference_p_value(
                    result["holdout_metrics"].get("mean_net_return"),
                    result["holdout_metrics"].get("standard_error"),
                    baseline_metrics.get("mean_net_return"),
                    baseline_metrics.get("standard_error"),
                )
            )
            result["raw_p_value_vs_unconditional"] = p_value
            result["incremental_mean_net_return_vs_unconditional"] = difference
            result["incremental_standard_error"] = difference_standard_error
            if result["method_id"] in QADAM_METHODS:
                result["raw_p_value"] = p_value
    adjustments = benjamini_hochberg(
        [_number(result.get("raw_p_value"), 1.0) for result in results]
    )
    for result, adjustment in zip(results, adjustments):
        result["adjusted_p_value"] = adjustment["adjusted_p_value"]
        result["false_discovery_adjusted_state"] = (
            "significant" if adjustment["significant"] else "not_significant"
        )
        reasons = list(result.get("rejection_reasons", []))
        method = str(result["method_id"])
        if result.get("status") == "tested_pending_multiple_testing":
            if not adjustment["significant"]:
                reasons.append("false_discovery_adjusted_result_not_significant")
            if method in NEGATIVE_CONTROL_METHODS:
                reasons.append("negative_control_cannot_validate")
            if method in BASELINE_METHODS:
                reasons.append("comparator_method_not_edge_candidate")
            if method in (*QADAM_METHODS, *NEGATIVE_CONTROL_METHODS):
                group_key = (
                    result["strategy_family_id"],
                    result["instrument"],
                    result["horizon"],
                )
                baseline = unconditional_by_group.get(group_key)
                baseline_mean = (
                    _number(
                        baseline.get("holdout_metrics", {}).get("mean_net_return")
                    )
                    if baseline
                    else None
                )
                holdout_mean = _number(
                    result.get("holdout_metrics", {}).get("mean_net_return"), -1.0
                )
                result["unconditional_baseline_mean_net_return"] = baseline_mean
                if baseline_mean is None or holdout_mean <= baseline_mean:
                    reasons.append("does_not_beat_unconditional_baseline")
            result["historical_edge_candidate"] = not reasons and method in QADAM_METHODS
            result["status"] = (
                "historical_edge_candidate_after_holdout"
                if result["historical_edge_candidate"]
                else "rejected_after_holdout"
            )
        result["rejection_reasons"] = sorted(set(reasons))
        result["negative_control_promotion_gate_breach"] = (
            method in NEGATIVE_CONTROL_METHODS
            and result.get("false_discovery_adjusted_state") == "significant"
            and not (
                set(result["rejection_reasons"])
                - NEGATIVE_CONTROL_POLICY_REASONS
            )
        )
    results.sort(key=lambda row: row["hypothesis_id"])
    folds.sort(key=lambda row: (row["hypothesis_id"], row["fold"]["fold_id"]))
    candidates = [row for row in results if row["historical_edge_candidate"]]
    rejections = [row for row in results if not row["historical_edge_candidate"]]
    return {
        "results": results,
        "folds": folds,
        "rejections": rejections,
        "historical_edge_candidates": candidates,
        "attempted_hypothesis_count": len(results),
        "completed_method_count": len(
            {
                result["method_id"]
                for result in results
                if result.get("holdout_metrics") is not None
            }
        ),
        "untouched_holdout_result_count": sum(
            result.get("holdout_metrics") is not None for result in results
        ),
        "cost_adjusted_result_count": sum(
            isinstance(result.get("holdout_metrics"), dict)
            and int(result["holdout_metrics"].get("trade_count") or 0) > 0
            for result in results
        ),
        "raw_significant_result_count": sum(
            _number(result.get("raw_p_value"), 1.0) <= FALSE_DISCOVERY_ALPHA
            for result in results
        ),
        "false_discovery_adjusted_result_count": len(results),
        "adjusted_significant_result_count": sum(
            result.get("false_discovery_adjusted_state") == "significant"
            for result in results
        ),
        "negative_control_statistically_positive_count": sum(
            result["method_id"] in NEGATIVE_CONTROL_METHODS
            and result.get("false_discovery_adjusted_state") == "significant"
            for result in results
        ),
        "negative_control_promotion_gate_breach_count": sum(
            result.get("negative_control_promotion_gate_breach") is True
            for result in results
        ),
        "negative_control_executed_count": sum(
            result["method_id"] in NEGATIVE_CONTROL_METHODS
            and result.get("holdout_metrics") is not None
            for result in results
        ),
        "negative_control_validated_count": 0,
        "results_by_strategy": _aggregate_dimension(results, "strategy_family_id"),
        "results_by_instrument": _aggregate_dimension(results, "instrument"),
        "results_by_horizon": _aggregate_dimension(results, "horizon"),
        "results_by_method": _aggregate_dimension(results, "method_id"),
        "source_contributions": _source_contributions(results),
        "independent_group_count": len(
            {row["overlap_group_id"] for row in enriched if row.get("independent_sample")}
        ),
        "eligible_strategy_instrument_horizon_group_count": sum(
            len(group_rows) >= MINIMUM_INDEPENDENT_ROWS
            for group_rows in groups.values()
        ),
        "insufficient_group_count": sum(
            len(group_rows) < MINIMUM_INDEPENDENT_ROWS for group_rows in groups.values()
        ),
    }
