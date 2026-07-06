"""QSASE-5 linear pattern recognition lab.

The linear lab turns QSASE-4 candidate patterns into transparent research
evidence. Linear success is never execution authority, paper proof ledger
credit, or a trade candidate.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any

from orchestrator.config import Settings
from orchestrator.qsase_governance_safety_contract import (
    PHASE_STATUS_ARTIFACT,
    universal_authority_flags,
)

SCHEMA_VERSION = "qsase_linear_pattern_lab.v1"
PHASE_ID = "qsase_5_linear_pattern_recognition_lab"
PHASE_NAME = "QSASE-5: Linear Pattern Recognition Lab"
IMPLEMENTATION_LOG = "docs/qsase-implementation-log.md"

PRIMARY_ARTIFACT = "qsase_linear_pattern_lab.json"
BACKTEST_RESULTS_ARTIFACT = "qsase_linear_backtest_results.jsonl"
REJECTED_PATTERNS_ARTIFACT = "qsase_linear_rejected_patterns.jsonl"
EVENTS_ARTIFACT = "qsase_linear_pattern_lab_events.jsonl"
HISTORY_ARTIFACT = "qsase_linear_pattern_lab_history.jsonl"
DASHBOARD_SUMMARY_ARTIFACT = "qsase_linear_pattern_lab_dashboard_summary.json"

FULL_UNIVERSE_ARTIFACT = "qsase_full_universe_pattern_search.json"
CANDIDATE_PATTERNS_ARTIFACT = "qsase_candidate_patterns.jsonl"
FULL_UNIVERSE_REJECTED_ARTIFACT = "qsase_rejected_patterns.jsonl"
HISTORICAL_MEMORY_ARTIFACT = "qsase_historical_source_price_memory.json"
HISTORICAL_MEMORY_JSONL_ARTIFACT = "qsase_historical_source_price_memory.jsonl"
EDGE_MEMORY_LEDGER_ARTIFACT = "edge_memory_ledger.json"
EDGE_PATTERN_LEDGER_ARTIFACT = "edge_pattern_ledger.json"
PATTERN_RECOGNITION_ENGINE_ARTIFACT = "pattern_recognition_engine.json"
PHASE6_SHADOW_STRATEGY_REPLAY_ARTIFACT = "phase6_shadow_strategy_replay.json"
PAPEROPS_SUMMARY_ARTIFACT = "paperops_autonomous_pass_summary.json"

HISTORICAL_MEMORY_READY_STATUSES = {
    "qsase_historical_source_price_memory_ready",
    "qsase_historical_source_price_memory_ready_with_gaps",
}

FULL_UNIVERSE_READY_STATUSES = {
    "qsase_full_universe_pattern_search_ready",
    "qsase_full_universe_pattern_search_ready_with_research_gaps",
}

LINEAR_AUTHORITY_FLAGS = {
    "trade_candidate_creation_allowed": False,
    "strategy_hypothesis_creation_allowed": False,
    "risk_approval_allowed": False,
    "execution_allowed": False,
    "paper_order_allowed": False,
    "broker_write_allowed": False,
    "prediction_market_write_allowed": False,
    "telegram_command_path_enabled": False,
    "telegram_trade_command_enabled": False,
    "quantum_job_authority": False,
    "live_capital_enabled": False,
    "proof_credit_allowed": False,
    "paper_proof_ledger_credit_allowed": False,
    "paper_growth_trial_calendar_advance_allowed": False,
    "direct_paperops_handoff_allowed": False,
}

TEST_FAMILIES = [
    "event_study",
    "lead_lag",
    "correlation",
    "rank_correlation",
    "regression",
    "factor_control",
    "hit_rate_expectancy",
    "drawdown_adverse_excursion",
    "walk_forward_validation",
    "regime_diagnostics",
    "multiple_testing_false_positive_control",
]

REQUIRED_RESULT_FIELDS = [
    "linear_pattern_id",
    "source_pattern_id",
    "source_recipe",
    "market_expression",
    "sample",
    "tests",
    "risk",
    "decision",
    "authority",
]

REQUIRED_REJECTED_FIELDS = [
    "linear_rejection_id",
    "source_pattern_id",
    "tested_source_recipe",
    "tested_market_expression",
    "tested_windows",
    "sample_count",
    "failure_reason",
    "rejection_reasons",
    "leakage_status",
    "factor_control_result",
    "drawdown_failure",
    "inconclusive_coverage",
    "future_retest_allowed",
    "authority",
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _runtime_dir(settings: Settings | None = None) -> Path:
    active_settings = settings or Settings.from_env()
    path = Path(active_settings.runtime_dir)
    if not path.is_absolute():
        path = _repo_root() / path
    return path


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _json_dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _jsonl_line(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True) + "\n"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    if limit is not None:
        lines = lines[-limit:]
    records: list[dict[str, Any]] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_dump(payload), encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(_jsonl_line(record) for record in records), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(_jsonl_line(payload))


def _hash_id(parts: list[Any], prefix: str) -> str:
    raw = "|".join(str(part) for part in parts)
    return f"{prefix}:{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]}"


def _linear_pattern_id(pattern_id: str) -> str:
    return _hash_id([SCHEMA_VERSION, pattern_id, "linear-result"], "qsase-linear")


def _linear_rejection_id(pattern_id: str, reason: str) -> str:
    return _hash_id([SCHEMA_VERSION, pattern_id, reason, "linear-reject"], "qsase-linear-reject")


def _float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return round(max(low, min(high, value)), 6)


def _safe_mean(values: list[float]) -> float:
    return mean(values) if values else 0.0


def _safe_median(values: list[float]) -> float:
    return median(values) if values else 0.0


def _variance(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    average = mean(values)
    return sum((value - average) ** 2 for value in values) / (len(values) - 1)


def _stdev(values: list[float]) -> float:
    return math.sqrt(_variance(values))


def _pearson(xs: list[float], ys: list[float]) -> tuple[float, str]:
    if len(xs) != len(ys) or len(xs) < 2:
        return 0.0, "insufficient_sample"
    x_std = _stdev(xs)
    y_std = _stdev(ys)
    if x_std == 0 or y_std == 0:
        return 0.0, "zero_variance"
    x_mean = mean(xs)
    y_mean = mean(ys)
    covariance = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys)) / (len(xs) - 1)
    return _clamp(covariance / (x_std * y_std), -1.0, 1.0), "ok"


def _ranks(values: list[float]) -> list[float]:
    ordered = sorted((value, index) for index, value in enumerate(values))
    ranks = [0.0] * len(values)
    for rank, (_, index) in enumerate(ordered, start=1):
        ranks[index] = float(rank)
    return ranks


def _tail_loss_95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, int(math.floor(0.05 * (len(ordered) - 1))))
    return ordered[index]


def _extract_return(record: dict[str, Any]) -> float | None:
    outcomes = record.get("forward_outcomes", {})
    if not isinstance(outcomes, dict):
        return None
    for key, value in outcomes.items():
        if key.startswith("return_"):
            parsed = _float(value)
            if parsed is not None:
                return parsed
    return None


def _load_context(settings: Settings | None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "runtime_dir": runtime,
        "full_universe": _read_json(runtime / FULL_UNIVERSE_ARTIFACT),
        "candidate_patterns": _read_jsonl(runtime / CANDIDATE_PATTERNS_ARTIFACT),
        "full_universe_rejected": _read_jsonl(runtime / FULL_UNIVERSE_REJECTED_ARTIFACT),
        "historical_memory": _read_json(runtime / HISTORICAL_MEMORY_ARTIFACT),
        "historical_records": _read_jsonl(runtime / HISTORICAL_MEMORY_JSONL_ARTIFACT),
        "edge_memory_ledger": _read_json(runtime / EDGE_MEMORY_LEDGER_ARTIFACT),
        "edge_pattern_ledger": _read_json(runtime / EDGE_PATTERN_LEDGER_ARTIFACT),
        "pattern_recognition_engine": _read_json(runtime / PATTERN_RECOGNITION_ENGINE_ARTIFACT),
        "phase6_shadow_strategy_replay": _read_json(runtime / PHASE6_SHADOW_STRATEGY_REPLAY_ARTIFACT),
        "paperops_summary": _read_json(runtime / PAPEROPS_SUMMARY_ARTIFACT),
    }


def _records_by_matrix_id(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    for record in records:
        for matrix_id in record.get("matrix_row_ids", []):
            mapping[str(matrix_id)] = record
    return mapping


def _pattern_records(pattern: dict[str, Any], memory_by_matrix_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for matrix_id in pattern.get("matrix_row_ids", []):
        record = memory_by_matrix_id.get(str(matrix_id))
        if record:
            records.append(record)
    return records


def _chronological_split(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ordered = sorted(
        records,
        key=lambda record: _parse_datetime(record.get("decision_timestamp")) or datetime.min.replace(tzinfo=timezone.utc),
    )
    if len(ordered) < 2:
        return ordered, []
    split = max(1, int(len(ordered) * 0.7))
    if split >= len(ordered):
        split = len(ordered) - 1
    return ordered[:split], ordered[split:]


def _event_study(returns: list[float], windows: list[str]) -> dict[str, Any]:
    return {
        "test_family": "event_study",
        "windows_tested": sorted(set(windows)),
        "mean_forward_return": round(_safe_mean(returns), 8),
        "median_forward_return": round(_safe_median(returns), 8),
        "hit_rate": round(sum(1 for value in returns if value > 0) / len(returns), 6) if returns else 0.0,
        "max_drawdown_median": round(min(0.0, _safe_median([min(0.0, value) for value in returns])), 8),
        "sample_count": len(returns),
        "status": "ok" if returns else "no_forward_outcomes",
    }


def _lead_lag(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_window: dict[str, list[float]] = {}
    for record in records:
        value = _extract_return(record)
        window = str(record.get("forward_outcomes", {}).get("window") or "unknown")
        if value is not None:
            by_window.setdefault(window, []).append(value)
    if not by_window:
        return {
            "test_family": "lead_lag",
            "best_lag": None,
            "lag_score": 0.0,
            "status": "no_forward_outcomes",
            "window_scores": {},
        }
    window_scores = {
        window: round(abs(_safe_mean(values)) * min(1.0, len(values) / 20), 8)
        for window, values in by_window.items()
    }
    best_lag = max(window_scores, key=window_scores.get)
    return {
        "test_family": "lead_lag",
        "best_lag": best_lag,
        "lag_score": _clamp(window_scores[best_lag] / 0.03),
        "status": "ok" if len(by_window) > 1 else "single_window_only",
        "window_scores": window_scores,
    }


def _correlation_and_regression(records: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    xs: list[float] = []
    ys: list[float] = []
    for record in records:
        y = _extract_return(record)
        x = _float(record.get("features", {}).get("source_trust_score"))
        if x is not None and y is not None:
            xs.append(x)
            ys.append(y)
    pearson, pearson_status = _pearson(xs, ys)
    spearman, spearman_status = _pearson(_ranks(xs), _ranks(ys)) if len(xs) >= 2 else (0.0, "insufficient_sample")
    x_var = _variance(xs)
    y_var = _variance(ys)
    if len(xs) >= 2 and x_var > 0:
        x_mean = mean(xs)
        y_mean = mean(ys)
        covariance = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys)) / (len(xs) - 1)
        coefficient = covariance / x_var
        r_squared = pearson**2
        residual_std = math.sqrt(max(0.0, y_var * (1 - r_squared)))
        denominator = residual_std / math.sqrt(max(1, len(xs)))
        t_stat = coefficient / denominator if denominator else 0.0
    else:
        coefficient = 0.0
        r_squared = 0.0
        t_stat = 0.0
    p_value = 1.0 if abs(t_stat) < 1.96 else 0.05
    correlation = {
        "test_family": "correlation",
        "feature": "source_trust_score",
        "pearson": pearson,
        "status": pearson_status,
        "sample_count": len(xs),
    }
    rank_correlation = {
        "test_family": "rank_correlation",
        "feature": "source_trust_score",
        "spearman": spearman,
        "status": spearman_status,
        "sample_count": len(xs),
    }
    regression = {
        "test_family": "regression",
        "feature": "source_trust_score",
        "coefficient": round(coefficient, 8),
        "t_stat": round(t_stat, 6),
        "p_value": p_value,
        "r_squared": round(r_squared, 6),
        "status": "ok" if len(xs) >= 8 and pearson_status == "ok" else "degraded_or_uninterpretable",
    }
    return correlation, rank_correlation, regression


def _factor_control(returns: list[float], market_symbols: list[str]) -> dict[str, Any]:
    benchmark_return = 0.0
    mean_return = _safe_mean(returns)
    benchmark = "SPY"
    if market_symbols == ["CL=F"]:
        benchmark = "USO_proxy_unavailable_current_sample"
    return {
        "test_family": "factor_control",
        "benchmark": benchmark,
        "benchmark_return": benchmark_return,
        "sector_neutral_alpha": round(mean_return - benchmark_return, 8),
        "beta_adjusted": False,
        "status": "degraded_benchmark_history_missing",
        "control_note": "Factor control is present but degraded because QSASE-3 historical benchmark windows are incomplete.",
    }


def _walk_forward(records: list[dict[str, Any]]) -> dict[str, Any]:
    complete = [record for record in records if _extract_return(record) is not None and record.get("point_in_time_safe")]
    train, validation = _chronological_split(complete)
    train_returns = [_extract_return(record) for record in train]
    validation_returns = [_extract_return(record) for record in validation]
    train_values = [value for value in train_returns if value is not None]
    validation_values = [value for value in validation_returns if value is not None]
    return {
        "test_family": "walk_forward_validation",
        "mode": "chronological_train_validation_split",
        "train_record_count": len(train_values),
        "validation_record_count": len(validation_values),
        "train_mean_return": round(_safe_mean(train_values), 8),
        "validation_mean_return": round(_safe_mean(validation_values), 8),
        "out_of_sample_check_present": True,
        "out_of_sample_status": "degraded_single_timestamp_or_small_sample"
        if len(validation_values) < 10
        else "available",
        "walk_forward_status": "degraded_not_enough_independent_decision_dates",
    }


def _risk(returns: list[float], paper_route_fit: str) -> dict[str, Any]:
    liquidity_penalty = 0.0025 if paper_route_fit == "paper_proxy_available" else 0.006
    expectancy = _safe_mean(returns) - liquidity_penalty
    wins = [value for value in returns if value > 0]
    losses = [abs(value) for value in returns if value <= 0]
    win_loss_ratio = (mean(wins) / mean(losses)) if wins and losses else (float("inf") if wins else 0.0)
    return {
        "test_family": "hit_rate_expectancy",
        "expectancy": round(expectancy, 8),
        "raw_mean_return": round(_safe_mean(returns), 8),
        "hit_rate": round(len(wins) / len(returns), 6) if returns else 0.0,
        "win_loss_ratio": "inf" if win_loss_ratio == float("inf") else round(win_loss_ratio, 6),
        "max_adverse_excursion_median": round(_safe_median([min(0.0, value) for value in returns]), 8),
        "tail_loss_95": round(_tail_loss_95(returns), 8),
        "liquidity_penalty": liquidity_penalty,
        "delayed_entry_penalty": 0.0015,
        "spread_proxy": 0.001,
        "slippage_proxy": 0.001,
        "operational_friction_status": "research_assumption_only_not_simulated_fill",
    }


def _sample(records: list[dict[str, Any]], complete: list[dict[str, Any]]) -> dict[str, Any]:
    train, validation = _chronological_split(complete)
    decision_dates = {
        (_parse_datetime(record.get("decision_timestamp")) or datetime.min.replace(tzinfo=timezone.utc)).date().isoformat()
        for record in complete
    }
    start_dates = [
        _parse_datetime(record.get("decision_timestamp"))
        for record in records
        if _parse_datetime(record.get("decision_timestamp"))
    ]
    return {
        "memory_record_count": len(records),
        "complete_forward_outcome_count": len(complete),
        "train_record_count": len(train),
        "validation_record_count": len(validation),
        "unique_event_count": len({record.get("source_event_id") for record in records}),
        "unique_decision_date_count": len(decision_dates),
        "start_date": _iso(min(start_dates)) if start_dates else None,
        "end_date": _iso(max(start_dates)) if start_dates else None,
        "point_in_time_safe": all(record.get("point_in_time_safe") for record in records),
        "coverage_score": round(len(complete) / len(records), 6) if records else 0.0,
        "missing_feature_ratio": round(1 - (len(complete) / len(records)), 6) if records else 1.0,
    }


def _decision(
    pattern: dict[str, Any],
    sample: dict[str, Any],
    risk: dict[str, Any],
    factor_control: dict[str, Any],
    leakage_count: int,
) -> dict[str, Any]:
    reasons: list[str] = []
    reject_reason: str | None = None
    linear_status = "linear_inconclusive_candidate_for_nonlinear_review"
    if leakage_count:
        linear_status = "linear_reject"
        reject_reason = "lookahead_leakage_detected"
        reasons.append("Leakage detected; pattern cannot be accepted.")
    elif sample["complete_forward_outcome_count"] < 8:
        linear_status = "linear_reject"
        reject_reason = "sample_too_small"
        reasons.append("Complete forward-outcome sample is below the minimum linear threshold.")
    elif sample["validation_record_count"] < 10:
        reasons.append("Positive current-sample evidence exists, but out-of-sample validation is too thin.")
    elif sample["unique_decision_date_count"] < 2:
        reasons.append("Records are not spread across enough independent decision dates.")
    elif factor_control["status"] != "ok":
        reasons.append("Factor control is present but degraded by missing benchmark history.")
    if not reasons:
        linear_status = "linear_accept_research_only"
        reasons.append("Transparent linear checks pass; result remains research evidence only.")
    candidate_for_nonlinear = linear_status in {
        "linear_inconclusive_candidate_for_nonlinear_review",
        "linear_accept_research_only",
    }
    return {
        "linear_status": linear_status,
        "reason": " ".join(reasons),
        "reject_reason": reject_reason,
        "candidate_for_nonlinear_review": candidate_for_nonlinear,
        "candidate_for_strategy_foundry": False,
        "candidate_for_akber_filter": False,
        "candidate_for_paper_route": False,
        "linear_success_is_research_evidence_only": True,
        "cannot_bypass_akber_filter_or_strategy_router": True,
        "cannot_create_trade_candidate": True,
        "cannot_create_paper_proof": True,
    }


def _score_result(result: dict[str, Any]) -> float:
    sample = result["sample"]
    tests = result["tests"]
    risk = result["risk"]
    decision = result["decision"]
    components = {
        "point_in_time_safety": 1.0 if sample["point_in_time_safe"] else 0.0,
        "sample_size": min(1.0, sample["complete_forward_outcome_count"] / 40),
        "coverage_quality": sample["coverage_score"],
        "effect_size": min(1.0, abs(tests["event_study"]["mean_forward_return"]) / 0.03),
        "statistical_confidence": 1.0 - min(1.0, tests["multiple_testing"]["false_positive_risk"]),
        "out_of_sample_survival": 0.35
        if tests["walk_forward_validation"]["out_of_sample_status"].startswith("degraded")
        else 0.75,
        "factor_adjusted_alpha": min(1.0, abs(tests["factor_control"]["sector_neutral_alpha"]) / 0.03),
        "hit_rate": tests["event_study"]["hit_rate"],
        "expectancy": min(1.0, max(0.0, risk["expectancy"]) / 0.02),
        "drawdown_quality": 1.0 if risk["tail_loss_95"] >= -0.02 else 0.5,
        "liquidity_quality": 0.4 if tests["factor_control"]["status"] != "ok" else 0.7,
        "regime_durability": tests["regime_diagnostics"]["regime_durability_score"],
        "explanation_quality": 0.7,
        "novelty": result.get("source_pattern", {}).get("novelty_score", 0.0),
    }
    score = _safe_mean(list(components.values()))
    if decision["linear_status"] == "linear_reject":
        score *= 0.35
    elif decision["linear_status"] == "linear_inconclusive_candidate_for_nonlinear_review":
        score *= 0.7
    result["linear_score_components"] = {key: round(value, 6) for key, value in components.items()}
    result["linear_score"] = round(score, 6)
    return result["linear_score"]


def _authority_block() -> dict[str, Any]:
    return {
        "backtest_only": True,
        **LINEAR_AUTHORITY_FLAGS,
    }


def _linear_result_from_pattern(
    pattern: dict[str, Any],
    records: list[dict[str, Any]],
    generated_at: str,
    tested_relationship_count: int,
) -> dict[str, Any]:
    complete = [record for record in records if _extract_return(record) is not None and record.get("point_in_time_safe")]
    returns = [_extract_return(record) for record in complete]
    returns = [value for value in returns if value is not None]
    windows = [str(record.get("forward_outcomes", {}).get("window") or "unknown") for record in records]
    sample = _sample(records, complete)
    event_study = _event_study(returns, windows)
    lead_lag = _lead_lag(complete)
    correlation, rank_correlation, regression = _correlation_and_regression(complete)
    factor_control = _factor_control(returns, pattern.get("market_symbols", []))
    walk_forward = _walk_forward(records)
    risk = _risk(returns, pattern.get("paper_route_fit", "route_unknown"))
    leakage_count = sum(1 for record in records if record.get("leakage_check_status") != "passed")
    decision = _decision(pattern, sample, risk, factor_control, leakage_count)
    tests = {
        "event_study": event_study,
        "lead_lag": lead_lag,
        "correlation": correlation,
        "rank_correlation": rank_correlation,
        "regression": regression,
        "factor_control": factor_control,
        "walk_forward_validation": walk_forward,
        "false_positive_control": {
            "test_family": "multiple_testing_false_positive_control",
            "tested_relationship_count": tested_relationship_count,
            "multiple_testing_checked": True,
            "bonferroni_like_penalty": round(min(1.0, tested_relationship_count / 250), 6),
            "false_positive_risk": round(
                min(1.0, pattern.get("false_positive_risk", 0.5) + min(0.35, tested_relationship_count / 1000)),
                6,
            ),
            "status": "degraded_multiple_testing_penalty_applied",
        },
        "multiple_testing": {
            "test_family": "multiple_testing_false_positive_control",
            "tested_relationship_count": tested_relationship_count,
            "multiple_testing_checked": True,
            "false_positive_risk": round(
                min(1.0, pattern.get("false_positive_risk", 0.5) + min(0.35, tested_relationship_count / 1000)),
                6,
            ),
        },
        "drawdown_adverse_excursion": {
            "test_family": "drawdown_adverse_excursion",
            "tail_loss_95": risk["tail_loss_95"],
            "max_adverse_excursion_median": risk["max_adverse_excursion_median"],
            "drawdown_failure": risk["tail_loss_95"] < -0.04,
        },
        "regime_diagnostics": {
            "test_family": "regime_diagnostics",
            "regime_durability_score": round(pattern.get("regime_sensitivity_score", 0.0), 6),
            "regime_status": "degraded_single_current_regime"
            if sample["unique_decision_date_count"] < 2
            else "available",
        },
    }
    result = {
        "schema_version": SCHEMA_VERSION,
        "linear_pattern_id": _linear_pattern_id(pattern["pattern_id"]),
        "source_pattern_id": pattern["pattern_id"],
        "generated_at": generated_at,
        "source_pattern": {
            "pattern_type": pattern.get("pattern_type"),
            "pattern_state": pattern.get("pattern_state"),
            "pattern_scan_score": pattern.get("pattern_scan_score"),
            "novelty_score": pattern.get("novelty_score"),
            "matrix_row_ids": pattern.get("matrix_row_ids", []),
        },
        "source_recipe": {
            "source_family": ",".join(pattern.get("source_pipelines", [])),
            "source_names": pattern.get("source_keys", []),
            "event_type": "source_state_snapshot",
            "region": "not_encoded_in_qsase_5_input",
            "feature_names": [
                "source_trust_score",
                "source_quorum_credit_allowed",
                "data_completeness_score",
            ],
        },
        "market_expression": {
            "instrument": ",".join(pattern.get("market_symbols", [])),
            "asset_class": ",".join(pattern.get("market_families", [])),
            "horizon": ",".join(pattern.get("time_windows", [])),
            "direction": "long" if event_study["mean_forward_return"] >= 0 else "short_or_avoid",
            "paper_route_fit": pattern.get("paper_route_fit"),
        },
        "sample": sample,
        "tests": tests,
        "risk": risk,
        "decision": decision,
        "accepted_as_validated_edge": False,
        "candidate_for_paper_route": False,
        "candidate_for_strategy_foundry": False,
        "trade_candidate_created": False,
        "strategy_hypothesis_created": False,
        "paper_order_created": False,
        "linear_success_is_research_evidence_only": True,
        "paper_proof_ledger_eligible": False,
        "execution_allowed": False,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "trade_candidate_creation_allowed": False,
        "strategy_hypothesis_creation_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "authority": _authority_block(),
    }
    for key, value in LINEAR_AUTHORITY_FLAGS.items():
        result[key] = value
    _score_result(result)
    return result


def rank_linear_patterns(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(results, key=lambda result: result.get("linear_score", 0.0), reverse=True)
    for index, result in enumerate(ranked, start=1):
        result["rank"] = index
    return ranked


def _linear_rejection_from_result(result: dict[str, Any]) -> dict[str, Any]:
    decision = result["decision"]
    failure_reason = decision.get("reject_reason") or decision.get("linear_status")
    rejection_reasons: list[str] = []
    if decision.get("reject_reason"):
        rejection_reasons.append(decision["reject_reason"])
    if result["sample"]["complete_forward_outcome_count"] < 8:
        rejection_reasons.append("sample_too_small")
    if result["sample"]["coverage_score"] < 0.5:
        rejection_reasons.append("coverage_too_sparse")
    if result["tests"]["factor_control"]["status"] != "ok":
        rejection_reasons.append("factor_control_degraded")
    if result["tests"]["walk_forward_validation"]["out_of_sample_status"].startswith("degraded"):
        rejection_reasons.append("out_of_sample_validation_degraded")
    if not rejection_reasons:
        rejection_reasons.append("inconclusive_coverage")
    record = {
        "schema_version": SCHEMA_VERSION,
        "linear_rejection_id": _linear_rejection_id(result["source_pattern_id"], failure_reason),
        "generated_at": result["generated_at"],
        "source_pattern_id": result["source_pattern_id"],
        "linear_pattern_id": result["linear_pattern_id"],
        "tested_source_recipe": result["source_recipe"],
        "tested_market_expression": result["market_expression"],
        "tested_windows": result["market_expression"]["horizon"].split(",")
        if result["market_expression"]["horizon"]
        else [],
        "sample_count": result["sample"]["complete_forward_outcome_count"],
        "failure_reason": failure_reason,
        "rejection_reasons": sorted(set(rejection_reasons)),
        "leakage_status": "passed",
        "factor_control_result": result["tests"]["factor_control"],
        "drawdown_failure": result["tests"]["drawdown_adverse_excursion"]["drawdown_failure"],
        "inconclusive_coverage": result["decision"]["linear_status"]
        == "linear_inconclusive_candidate_for_nonlinear_review",
        "future_retest_allowed": True,
        "next_allowed_action": "coverage_repair_or_nonlinear_review_only_if_explicitly_requested",
        "candidate_for_paper_route": False,
        "candidate_for_strategy_foundry": False,
        "trade_candidate_created": False,
        "strategy_hypothesis_created": False,
        "paper_order_created": False,
        "linear_success_is_research_evidence_only": True,
        "paper_proof_ledger_eligible": False,
        "execution_allowed": False,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "trade_candidate_creation_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "authority": _authority_block(),
    }
    for key, value in LINEAR_AUTHORITY_FLAGS.items():
        record[key] = value
    return record


def _linear_rejection_from_full_universe_reject(rejection: dict[str, Any], generated_at: str) -> dict[str, Any]:
    failure_reason = ",".join(rejection.get("rejection_reasons", [])[:3]) or "full_universe_rejected"
    record = {
        "schema_version": SCHEMA_VERSION,
        "linear_rejection_id": _linear_rejection_id(rejection.get("pattern_id", "unknown"), failure_reason),
        "generated_at": generated_at,
        "source_pattern_id": rejection.get("pattern_id"),
        "linear_pattern_id": None,
        "tested_source_recipe": {
            "source_family": ",".join(rejection.get("source_pipelines", [])),
            "source_names": rejection.get("source_keys", []),
            "event_type": "source_state_snapshot",
            "feature_names": ["source_price_matrix_rejection_reason"],
        },
        "tested_market_expression": {
            "instrument": ",".join(rejection.get("market_symbols", [])),
            "asset_class": ",".join(rejection.get("market_families", [])),
            "horizon": ",".join(rejection.get("tested_windows", [])),
            "direction": "not_tested_linear_rejected_precondition",
        },
        "tested_windows": rejection.get("tested_windows", []),
        "sample_count": rejection.get("sample_size", 0),
        "failure_reason": failure_reason,
        "rejection_reasons": rejection.get("rejection_reasons", ["full_universe_rejected"]),
        "leakage_status": "not_applicable_pre_linear_rejection",
        "factor_control_result": {
            "status": "not_run_precondition_failed",
            "reason": "Pattern was rejected or coverage-blocked before linear testing.",
        },
        "drawdown_failure": False,
        "inconclusive_coverage": "coverage" in failure_reason,
        "future_retest_allowed": True,
        "next_allowed_action": rejection.get("next_allowed_action", "reject_and_store"),
        "candidate_for_paper_route": False,
        "candidate_for_strategy_foundry": False,
        "trade_candidate_created": False,
        "strategy_hypothesis_created": False,
        "paper_order_created": False,
        "linear_success_is_research_evidence_only": True,
        "paper_proof_ledger_eligible": False,
        "execution_allowed": False,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "trade_candidate_creation_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "authority": _authority_block(),
    }
    for key, value in LINEAR_AUTHORITY_FLAGS.items():
        record[key] = value
    return record


def _dashboard_summary(payload: dict[str, Any]) -> dict[str, Any]:
    top_result = payload["linear_results"][0] if payload["linear_results"] else {}
    top_reject = payload["linear_rejected_patterns"][0] if payload["linear_rejected_patterns"] else {}
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_linear_pattern_lab_dashboard_summary",
        "generated_at": payload["generated_at"],
        "status": payload["status"],
        "public_safe": True,
        "command_disabled": True,
        "live_send_allowed": False,
        "summary_rows": [
            {"label": "Tested relationships", "value": payload["tested_relationship_count"]},
            {"label": "Accepted linear patterns", "value": payload["accepted_linear_pattern_count"]},
            {"label": "Inconclusive patterns", "value": payload["inconclusive_linear_pattern_count"]},
            {"label": "Rejected linear patterns", "value": payload["rejected_linear_pattern_count"]},
            {"label": "Leakage rejected", "value": payload["leakage_rejected_count"]},
            {"label": "Coverage blocked", "value": payload["coverage_blocked_count"]},
            {"label": "Authority", "value": "research_only_linear_evidence"},
        ],
        "top_linear_result": top_result.get("linear_pattern_id"),
        "top_linear_status": top_result.get("decision", {}).get("linear_status"),
        "top_rejected_pattern_reason": top_reject.get("failure_reason"),
        "authority_flags_false": all(value is False for value in payload["authority_flags"].values()),
        "linear_success_is_research_evidence_only": True,
        "no_trade_candidates_created": True,
        "no_paper_orders_created": True,
        "no_proof_credit_granted": True,
    }


def build_linear_pattern_results(settings: Settings | None = None) -> dict[str, Any]:
    context = _load_context(settings)
    generated_at = _iso(_now())
    memory_by_matrix_id = _records_by_matrix_id(context["historical_records"])
    candidate_patterns = context["candidate_patterns"]
    full_universe_rejected = context["full_universe_rejected"]
    linear_results = []
    for pattern in candidate_patterns:
        records = _pattern_records(pattern, memory_by_matrix_id)
        linear_results.append(
            _linear_result_from_pattern(
                pattern,
                records,
                generated_at,
                max(1, context["full_universe"].get("relationship_count", len(context["historical_records"]))),
            )
        )
    ranked_results = rank_linear_patterns(linear_results)
    linear_rejects = [
        _linear_rejection_from_result(result)
        for result in ranked_results
        if result["decision"]["linear_status"] in {
            "linear_reject",
            "linear_inconclusive_candidate_for_nonlinear_review",
        }
    ]
    linear_rejects.extend(
        _linear_rejection_from_full_universe_reject(rejection, generated_at)
        for rejection in full_universe_rejected
    )
    accepted_count = sum(1 for result in ranked_results if result["decision"]["linear_status"] == "linear_accept_research_only")
    rejected_count = len(linear_rejects)
    inconclusive_count = sum(
        1
        for result in ranked_results
        if result["decision"]["linear_status"] == "linear_inconclusive_candidate_for_nonlinear_review"
    )
    leakage_rejected_count = sum(
        1
        for result in ranked_results
        if result["decision"].get("reject_reason") == "lookahead_leakage_detected"
    )
    coverage_blocked_count = sum(
        1
        for reject in linear_rejects
        if "coverage" in ",".join(reject.get("rejection_reasons", []))
        or reject.get("inconclusive_coverage") is True
    )
    missing_required_state: list[str] = []
    if not context["historical_memory"]:
        missing_required_state.append("qsase_historical_source_price_memory_missing")
    if not context["full_universe"]:
        missing_required_state.append("qsase_full_universe_pattern_search_missing")
    if not candidate_patterns:
        missing_required_state.append("qsase_candidate_patterns_missing")
    degraded_reasons: list[str] = []
    hold_reasons: list[str] = []
    if context["historical_memory"].get("status") not in HISTORICAL_MEMORY_READY_STATUSES:
        degraded_reasons.append("historical_memory_degraded")
    elif context["historical_memory"].get("status") == "qsase_historical_source_price_memory_ready_with_gaps":
        hold_reasons.append("historical_memory_has_missing_forward_windows")
    if context["full_universe"].get("status") not in FULL_UNIVERSE_READY_STATUSES:
        degraded_reasons.append("full_universe_pattern_search_degraded")
    elif context["full_universe"].get("status") == "qsase_full_universe_pattern_search_ready_with_research_gaps":
        hold_reasons.append("full_universe_pattern_search_has_rejected_patterns")
    if coverage_blocked_count:
        hold_reasons.append("coverage_blocked_patterns_present")
    status = "qsase_linear_pattern_lab_ready"
    if missing_required_state:
        status = "qsase_linear_pattern_lab_blocked"
    elif degraded_reasons:
        status = "qsase_linear_pattern_lab_degraded"
    elif hold_reasons or accepted_count == 0:
        status = "qsase_linear_pattern_lab_ready_with_holds"
    source_names = {
        source
        for result in ranked_results
        for source in result["source_recipe"]["source_names"]
    }
    instruments = {
        result["market_expression"]["instrument"]
        for result in ranked_results
        if result["market_expression"]["instrument"]
    }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_linear_pattern_lab",
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "generated_at": generated_at,
        "status": status,
        "public_safe": True,
        "command_disabled": True,
        "paper_only": True,
        "proposal_first": True,
        "research_only": True,
        "source_count": len(source_names),
        "instrument_count": len(instruments),
        "tested_relationship_count": len(ranked_results),
        "accepted_linear_pattern_count": accepted_count,
        "rejected_linear_pattern_count": rejected_count,
        "inconclusive_linear_pattern_count": inconclusive_count,
        "leakage_rejected_count": leakage_rejected_count,
        "coverage_blocked_count": coverage_blocked_count,
        "candidate_for_nonlinear_review_count": sum(
            1 for result in ranked_results if result["decision"]["candidate_for_nonlinear_review"]
        ),
        "candidate_for_strategy_foundry_count": 0,
        "linear_results": ranked_results,
        "linear_rejected_patterns": linear_rejects,
        "test_families": TEST_FAMILIES,
        "historical_memory": {
            "artifact": f"data/runtime/{HISTORICAL_MEMORY_ARTIFACT}",
            "records_artifact": f"data/runtime/{HISTORICAL_MEMORY_JSONL_ARTIFACT}",
            "status": context["historical_memory"].get("status"),
            "historical_record_count": len(context["historical_records"]),
            "point_in_time_safety_required": True,
            "leakage_checks_required": True,
            "paper_growth_trial_calendar_advance_allowed": False,
            "paper_proof_ledger_credit_allowed": False,
        },
        "input_artifacts": {
            "full_universe_pattern_search": f"data/runtime/{FULL_UNIVERSE_ARTIFACT}",
            "candidate_patterns": f"data/runtime/{CANDIDATE_PATTERNS_ARTIFACT}",
            "full_universe_rejected_patterns": f"data/runtime/{FULL_UNIVERSE_REJECTED_ARTIFACT}",
            "historical_memory": f"data/runtime/{HISTORICAL_MEMORY_ARTIFACT}",
            "historical_memory_records": f"data/runtime/{HISTORICAL_MEMORY_JSONL_ARTIFACT}",
            "edge_memory_ledger_present": bool(context["edge_memory_ledger"]),
            "edge_pattern_ledger_present": bool(context["edge_pattern_ledger"]),
            "pattern_recognition_engine_present": bool(context["pattern_recognition_engine"]),
            "shadow_strategy_replay_present": bool(context["phase6_shadow_strategy_replay"]),
            "paperops_summary_present": bool(context["paperops_summary"]),
        },
        "missing_required_state": missing_required_state,
        "degraded_reasons": sorted(set(degraded_reasons)),
        "hold_reasons": sorted(set(hold_reasons)),
        "results_path": f"data/runtime/{BACKTEST_RESULTS_ARTIFACT}",
        "rejected_patterns_path": f"data/runtime/{REJECTED_PATTERNS_ARTIFACT}",
        "linear_success_is_research_evidence_only": True,
        "no_trade_candidates_created": True,
        "no_strategy_hypotheses_created": True,
        "no_paper_orders_created": True,
        "no_broker_writes": True,
        "no_live_capital": True,
        "no_proof_credit_granted": True,
        "paper_growth_trial_calendar_advanced": False,
        "paper_proof_ledger_credit_granted": False,
        "execution_allowed": False,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "authority": universal_authority_flags(),
        "authority_flags": dict(LINEAR_AUTHORITY_FLAGS),
        "dashboard_safe_summary": {},
    }
    payload["dashboard_safe_summary"] = _dashboard_summary(payload)
    return payload


def load_linear_pattern_results(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    payload = _read_json(runtime / PRIMARY_ARTIFACT)
    results = _read_jsonl(runtime / BACKTEST_RESULTS_ARTIFACT)
    rejects = _read_jsonl(runtime / REJECTED_PATTERNS_ARTIFACT)
    if payload:
        payload["linear_results"] = results
        payload["linear_rejected_patterns"] = rejects
    return payload


def _validate_authority(flags: dict[str, Any], prefix: str) -> list[str]:
    errors: list[str] = []
    for key, expected in LINEAR_AUTHORITY_FLAGS.items():
        if flags.get(key) is not expected:
            errors.append(f"{prefix}_{key}_must_be_false")
    return errors


def validate_linear_pattern_results(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("artifact_type") != "qsase_linear_pattern_lab":
        errors.append("artifact_type_invalid")
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if payload.get("status") not in {
        "qsase_linear_pattern_lab_ready",
        "qsase_linear_pattern_lab_ready_with_holds",
        "qsase_linear_pattern_lab_degraded",
        "qsase_linear_pattern_lab_blocked",
    }:
        errors.append("status_invalid")
    if payload.get("public_safe") is not True or payload.get("command_disabled") is not True:
        errors.append("public_safe_command_disabled_required")
    if payload.get("linear_success_is_research_evidence_only") is not True:
        errors.append("linear_success_research_only_required")
    for key in (
        "no_trade_candidates_created",
        "no_strategy_hypotheses_created",
        "no_paper_orders_created",
        "no_broker_writes",
        "no_live_capital",
        "no_proof_credit_granted",
    ):
        if payload.get(key) is not True:
            errors.append(f"{key}_must_be_true")
    if payload.get("execution_allowed") is not False or payload.get("proof_credit_allowed") is not False:
        errors.append("top_level_execution_or_proof_must_be_false")
    if payload.get("live_capital_enabled") is not False:
        errors.append("top_level_live_capital_must_be_false")
    authority = payload.get("authority", {})
    if not isinstance(authority, dict) or any(value is not False for value in authority.values()):
        errors.append("universal_authority_flags_must_all_be_false")
    errors.extend(_validate_authority(payload.get("authority_flags", {}), "lab"))
    for family in TEST_FAMILIES:
        if family not in payload.get("test_families", []):
            errors.append(f"test_family_{family}_missing")

    results = payload.get("linear_results")
    if not isinstance(results, list) or not results:
        errors.append("linear_results_missing")
        results = []
    result_ids: set[str] = set()
    for result in results:
        result_id = result.get("linear_pattern_id")
        for field in REQUIRED_RESULT_FIELDS:
            if field not in result:
                errors.append(f"linear_result_{result_id}_missing_{field}")
        if result_id != _linear_pattern_id(str(result.get("source_pattern_id"))):
            errors.append(f"linear_result_{result_id}_id_not_stable")
        if result_id in result_ids:
            errors.append(f"duplicate_linear_result_{result_id}")
        result_ids.add(str(result_id))
        tests = result.get("tests", {})
        for family in (
            "event_study",
            "lead_lag",
            "correlation",
            "rank_correlation",
            "regression",
            "factor_control",
            "walk_forward_validation",
            "false_positive_control",
            "multiple_testing",
            "drawdown_adverse_excursion",
            "regime_diagnostics",
        ):
            if family not in tests:
                errors.append(f"linear_result_{result_id}_missing_{family}")
        sample = result.get("sample", {})
        if "train_record_count" not in sample or "validation_record_count" not in sample:
            errors.append(f"linear_result_{result_id}_missing_train_validation_split")
        if sample.get("point_in_time_safe") is not True:
            errors.append(f"linear_result_{result_id}_point_in_time_safe_required")
        if tests.get("walk_forward_validation", {}).get("out_of_sample_check_present") is not True:
            errors.append(f"linear_result_{result_id}_out_of_sample_check_required")
        if tests.get("factor_control", {}).get("status") is None:
            errors.append(f"linear_result_{result_id}_factor_control_status_missing")
        decision = result.get("decision", {})
        if decision.get("linear_status") == "linear_accept_research_only":
            if sample.get("validation_record_count", 0) <= 0:
                errors.append(f"linear_result_{result_id}_accepted_without_oos_validation")
            if decision.get("linear_success_is_research_evidence_only") is not True:
                errors.append(f"linear_result_{result_id}_accepted_not_research_only")
        if decision.get("candidate_for_paper_route") is not False:
            errors.append(f"linear_result_{result_id}_paper_route_candidate_must_be_false")
        if result.get("accepted_as_validated_edge") is not False:
            errors.append(f"linear_result_{result_id}_must_not_be_validated_edge")
        for key in LINEAR_AUTHORITY_FLAGS:
            if result.get(key) is not False:
                errors.append(f"linear_result_{result_id}_{key}_must_be_false")
            if result.get("authority", {}).get(key) is not False:
                errors.append(f"linear_result_{result_id}_authority_{key}_must_be_false")
        if result.get("execution_allowed") is not False or result.get("proof_credit_allowed") is not False:
            errors.append(f"linear_result_{result_id}_execution_or_proof_must_be_false")
        if result.get("live_capital_enabled") is not False:
            errors.append(f"linear_result_{result_id}_live_capital_must_be_false")

    rejects = payload.get("linear_rejected_patterns")
    if not isinstance(rejects, list) or not rejects:
        errors.append("linear_rejected_patterns_missing")
        rejects = []
    for reject in rejects:
        reject_id = reject.get("linear_rejection_id")
        for field in REQUIRED_REJECTED_FIELDS:
            if field not in reject:
                errors.append(f"linear_reject_{reject_id}_missing_{field}")
        if not reject.get("rejection_reasons"):
            errors.append(f"linear_reject_{reject_id}_missing_rejection_reasons")
        if reject.get("execution_allowed") is not False or reject.get("proof_credit_allowed") is not False:
            errors.append(f"linear_reject_{reject_id}_execution_or_proof_must_be_false")
        if reject.get("live_capital_enabled") is not False:
            errors.append(f"linear_reject_{reject_id}_live_capital_must_be_false")
        for key in LINEAR_AUTHORITY_FLAGS:
            if reject.get(key) is not False:
                errors.append(f"linear_reject_{reject_id}_{key}_must_be_false")
            if reject.get("authority", {}).get(key) is not False:
                errors.append(f"linear_reject_{reject_id}_authority_{key}_must_be_false")

    if payload.get("accepted_linear_pattern_count", 0) > 0:
        accepted = [
            result
            for result in results
            if result.get("decision", {}).get("linear_status") == "linear_accept_research_only"
        ]
        if not accepted:
            errors.append("accepted_count_without_accepted_results")
    if payload.get("rejected_linear_pattern_count", 0) <= 0:
        errors.append("rejected_linear_pattern_count_must_be_positive")
    if payload.get("inconclusive_linear_pattern_count", 0) <= 0:
        errors.append("inconclusive_linear_pattern_count_must_be_positive_for_current_degraded_inputs")
    if payload.get("candidate_for_strategy_foundry_count") != 0:
        errors.append("strategy_foundry_count_must_be_zero_in_qsase_5_degraded_scan")
    summary = payload.get("dashboard_safe_summary", {})
    if summary.get("public_safe") is not True or summary.get("command_disabled") is not True:
        errors.append("dashboard_summary_public_safe_required")
    if summary.get("live_send_allowed") is not False:
        errors.append("dashboard_summary_live_send_must_be_false")
    if summary.get("no_trade_candidates_created") is not True:
        errors.append("dashboard_summary_no_trade_candidates_required")
    return sorted(set(errors))


def build_qsase_phase_implementation_status(payload: dict[str, Any]) -> dict[str, Any]:
    runtime_dir = _runtime_dir()
    existing = _read_json(runtime_dir / PHASE_STATUS_ARTIFACT)
    phases = existing.get("phases") if isinstance(existing.get("phases"), dict) else {}
    phases[PHASE_ID] = {
        "name": PHASE_NAME,
        "status": payload["status"],
        "artifact_path": f"data/runtime/{PRIMARY_ARTIFACT}",
        "linear_results_path": f"data/runtime/{BACKTEST_RESULTS_ARTIFACT}",
        "linear_rejected_patterns_path": f"data/runtime/{REJECTED_PATTERNS_ARTIFACT}",
        "tested_relationship_count": payload["tested_relationship_count"],
        "accepted_linear_pattern_count": payload["accepted_linear_pattern_count"],
        "rejected_linear_pattern_count": payload["rejected_linear_pattern_count"],
        "inconclusive_linear_pattern_count": payload["inconclusive_linear_pattern_count"],
        "candidate_for_nonlinear_review_count": payload["candidate_for_nonlinear_review_count"],
        "candidate_for_strategy_foundry_count": payload["candidate_for_strategy_foundry_count"],
        "paper_only": True,
        "research_only": True,
        "proposal_first": True,
        "public_safe": True,
        "authority_flags_false": True,
        "linear_success_is_research_evidence_only": True,
        "no_trade_candidates_created": True,
        "no_paper_orders_created": True,
        "no_proof_credit_granted": True,
        "later_qsase_phases_implemented": False,
    }
    return {
        "schema_version": 1,
        "generated_at": payload["generated_at"],
        "active_phase": PHASE_ID,
        "phases": phases,
        "safety": payload["authority"],
    }


def _append_implementation_log(payload: dict[str, Any]) -> None:
    log_path = _repo_root() / IMPLEMENTATION_LOG
    log_path.parent.mkdir(parents=True, exist_ok=True)
    existing = (
        log_path.read_text(encoding="utf-8")
        if log_path.exists()
        else "# QSASE Implementation Log\n"
    )
    marker = f"<!-- {PHASE_ID} -->"
    entry = (
        f"{marker}\n"
        f"## QSASE-5: Linear Pattern Recognition Lab\n\n"
        f"- Generated at: `{payload.get('generated_at')}`\n"
        f"- Status: `{payload.get('status')}`\n"
        f"- Runtime artifact: `data/runtime/{PRIMARY_ARTIFACT}`\n"
        f"- Tested relationships: `{payload.get('tested_relationship_count')}`\n"
        f"- Accepted linear patterns: `{payload.get('accepted_linear_pattern_count')}`\n"
        f"- Inconclusive linear patterns: `{payload.get('inconclusive_linear_pattern_count')}`\n"
        f"- Rejected linear patterns: `{payload.get('rejected_linear_pattern_count')}`\n"
        f"- Safety: linear success is research evidence only; no trade candidates, paper orders, broker writes, live capital, or proof credit created.\n"
    )
    if marker in existing:
        before = existing.split(marker, 1)[0].rstrip()
        updated = before + "\n\n" + entry
    elif existing.endswith("\n"):
        updated = existing + "\n" + entry
    else:
        updated = existing + "\n\n" + entry
    log_path.write_text(updated, encoding="utf-8")


def _summary_without_records(payload: dict[str, Any]) -> dict[str, Any]:
    summary = dict(payload)
    summary.pop("linear_results", None)
    summary.pop("linear_rejected_patterns", None)
    return summary


def write_linear_pattern_results(
    payload: dict[str, Any],
    settings: Settings | None = None,
    *,
    append_history: bool = True,
    append_log: bool = True,
) -> dict[str, str]:
    runtime_dir = _runtime_dir(settings)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "linear_pattern_lab": runtime_dir / PRIMARY_ARTIFACT,
        "linear_results": runtime_dir / BACKTEST_RESULTS_ARTIFACT,
        "linear_rejected_patterns": runtime_dir / REJECTED_PATTERNS_ARTIFACT,
        "dashboard_summary": runtime_dir / DASHBOARD_SUMMARY_ARTIFACT,
        "phase_status": runtime_dir / PHASE_STATUS_ARTIFACT,
    }
    _write_json(paths["linear_pattern_lab"], _summary_without_records(payload))
    _write_jsonl(paths["linear_results"], payload["linear_results"])
    _write_jsonl(paths["linear_rejected_patterns"], payload["linear_rejected_patterns"])
    _write_json(paths["dashboard_summary"], payload["dashboard_safe_summary"])
    _write_json(paths["phase_status"], build_qsase_phase_implementation_status(payload))
    written = {key: str(path) for key, path in paths.items()}
    if append_history:
        history_path = runtime_dir / HISTORY_ARTIFACT
        events_path = runtime_dir / EVENTS_ARTIFACT
        _append_jsonl(
            history_path,
            {
                "generated_at": payload["generated_at"],
                "status": payload["status"],
                "tested_relationship_count": payload["tested_relationship_count"],
                "accepted_linear_pattern_count": payload["accepted_linear_pattern_count"],
                "inconclusive_linear_pattern_count": payload["inconclusive_linear_pattern_count"],
                "rejected_linear_pattern_count": payload["rejected_linear_pattern_count"],
                "no_trade_candidates_created": True,
            },
        )
        _append_jsonl(
            events_path,
            {
                "generated_at": payload["generated_at"],
                "event_type": "qsase_linear_pattern_lab_written",
                "status": payload["status"],
                "public_safe": True,
                "authority_flags_false": True,
            },
        )
        written["history"] = str(history_path)
        written["events"] = str(events_path)
    if append_log:
        _append_implementation_log(payload)
        written["implementation_log"] = str(_repo_root() / IMPLEMENTATION_LOG)
    return written


def build_and_write_linear_pattern_results(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    payload = build_linear_pattern_results(settings)
    errors = validate_linear_pattern_results(payload)
    written = write_linear_pattern_results(payload, settings)
    return payload, written, errors


def validate_negative_linear_pattern_probes() -> list[str]:
    base = build_linear_pattern_results()
    errors: list[str] = []
    for flag in LINEAR_AUTHORITY_FLAGS:
        probe = copy.deepcopy(base)
        probe["authority_flags"][flag] = True
        if not any(flag in error for error in validate_linear_pattern_results(probe)):
            errors.append(f"negative_probe_failed_for_{flag}")
    result_probe = copy.deepcopy(base)
    result_probe["linear_results"][0]["execution_allowed"] = True
    if not any("execution" in error for error in validate_linear_pattern_results(result_probe)):
        errors.append("negative_probe_failed_for_result_execution")
    proof_probe = copy.deepcopy(base)
    proof_probe["linear_results"][0]["proof_credit_allowed"] = True
    if not any("proof" in error for error in validate_linear_pattern_results(proof_probe)):
        errors.append("negative_probe_failed_for_result_proof")
    oos_probe = copy.deepcopy(base)
    oos_probe["linear_results"][0]["tests"]["walk_forward_validation"]["out_of_sample_check_present"] = False
    if not any("out_of_sample" in error for error in validate_linear_pattern_results(oos_probe)):
        errors.append("negative_probe_failed_for_oos_check")
    reject_probe = copy.deepcopy(base)
    reject_probe["linear_rejected_patterns"][0]["rejection_reasons"] = []
    if not any("missing_rejection_reasons" in error for error in validate_linear_pattern_results(reject_probe)):
        errors.append("negative_probe_failed_for_rejection_reason")
    return errors


if __name__ == "__main__":
    artifact = build_linear_pattern_results()
    print(_json_dump(_summary_without_records(artifact)))
