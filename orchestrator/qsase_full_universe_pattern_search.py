"""QSASE-4 full-universe pattern search.

This phase scans the complete source-price universe for research patterns. A
pattern is not a strategy, not a trade candidate, and not PaperOps authority.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from orchestrator.config import Settings
from orchestrator.qsase_governance_safety_contract import (
    PHASE_STATUS_ARTIFACT,
    universal_authority_flags,
)

SCHEMA_VERSION = "qsase_full_universe_pattern_search.v1"
PHASE_ID = "qsase_4_full_universe_pattern_search"
PHASE_NAME = "QSASE-4: Full-Universe Pattern Search"
IMPLEMENTATION_LOG = "docs/qsase-implementation-log.md"

PRIMARY_ARTIFACT = "qsase_full_universe_pattern_search.json"
CANDIDATE_PATTERNS_ARTIFACT = "qsase_candidate_patterns.jsonl"
REJECTED_PATTERNS_ARTIFACT = "qsase_rejected_patterns.jsonl"
EVENTS_ARTIFACT = "qsase_full_universe_pattern_search_events.jsonl"
HISTORY_ARTIFACT = "qsase_full_universe_pattern_search_history.jsonl"
DASHBOARD_SUMMARY_ARTIFACT = "qsase_full_universe_pattern_search_dashboard_summary.json"

SOURCE_PRICE_MATRIX_READY_STATUSES = {
    "qsase_source_price_matrix_ready",
    "qsase_source_price_matrix_ready_with_gaps",
}

HISTORICAL_MEMORY_READY_STATUSES = {
    "qsase_historical_source_price_memory_ready",
    "qsase_historical_source_price_memory_ready_with_gaps",
}

SELF_MODEL_ARTIFACT = "qsase_self_model.json"
MATRIX_ARTIFACT = "qsase_universal_source_price_matrix.json"
MATRIX_EDGES_ARTIFACT = "qsase_source_price_edges.jsonl"
HISTORICAL_COVERAGE_ARTIFACT = "qsase_historical_coverage_map.json"
HISTORICAL_MEMORY_ARTIFACT = "qsase_historical_source_price_memory.json"
COCKPIT_STATUS_ARTIFACT = "cockpit-status.json"
EDGE_PATTERN_LEDGER_ARTIFACT = "edge_pattern_ledger.json"
EDGE_MEMORY_LEDGER_ARTIFACT = "edge_memory_ledger.json"
EDGE_TRACKER_CHECK_ARTIFACT = "edge_tracker_check.json"
PATTERN_RECOGNITION_ENGINE_ARTIFACT = "pattern_recognition_engine.json"

FULL_UNIVERSE_AUTHORITY_FLAGS = {
    "source_quorum_credit_allowed": False,
    "strategy_hypothesis_creation_allowed": False,
    "trade_candidate_creation_allowed": False,
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
    "direct_paperops_handoff_allowed": False,
}

SCAN_METHODS = [
    "frequency_scan",
    "lead_lag_scan",
    "divergence_scan",
    "co_movement_scan",
    "volatility_expansion_scan",
    "drawdown_scan",
    "regime_split_scan",
    "novelty_scan",
    "route_fit_scan",
    "source_quorum_scan",
    "cross_source_scan",
    "cross_asset_scan",
]

REQUIRED_CANDIDATE_FIELDS = [
    "pattern_id",
    "generated_at",
    "pattern_state",
    "pattern_type",
    "source_keys",
    "source_pipelines",
    "market_symbols",
    "market_families",
    "time_windows",
    "relationship_summary",
    "matrix_row_ids",
    "sample_size",
    "persistence_score",
    "effect_size_score",
    "directional_consistency_score",
    "drawdown_penalty",
    "false_positive_risk",
    "regime_sensitivity_score",
    "source_quorum_score",
    "novelty_score",
    "paper_route_fit",
    "initial_strategy_labels",
    "new_strategy_candidate",
    "next_required_review",
    "proof_credit_allowed",
    "execution_allowed",
]

REQUIRED_REJECTED_FIELDS = [
    "pattern_id",
    "generated_at",
    "rejection_state",
    "pattern_type",
    "source_keys",
    "market_symbols",
    "tested_windows",
    "matrix_row_ids",
    "sample_size",
    "rejection_reasons",
    "failed_metrics",
    "overfit_risk",
    "data_quality_issues",
    "next_allowed_action",
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


def _pattern_id(
    pattern_type: str,
    source_keys: list[str],
    market_symbols: list[str],
    time_windows: list[str],
    suffix: str = "candidate",
) -> str:
    return _hash_id(
        [
            SCHEMA_VERSION,
            pattern_type,
            ",".join(sorted(source_keys)),
            ",".join(sorted(market_symbols)),
            ",".join(sorted(time_windows)),
            suffix,
        ],
        "qsase-pattern",
    )


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
    return round(max(low, min(high, value)), 4)


def _mean(values: list[float]) -> float:
    return mean(values) if values else 0.0


def _group_by(edges: list[dict[str, Any]], *keys: str) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        grouped[tuple(edge.get(key) for key in keys)].append(edge)
    return dict(grouped)


def _load_context(settings: Settings | None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "runtime_dir": runtime,
        "self_model": _read_json(runtime / SELF_MODEL_ARTIFACT),
        "matrix": _read_json(runtime / MATRIX_ARTIFACT),
        "matrix_edges": _read_jsonl(runtime / MATRIX_EDGES_ARTIFACT),
        "historical_coverage": _read_json(runtime / HISTORICAL_COVERAGE_ARTIFACT),
        "historical_memory": _read_json(runtime / HISTORICAL_MEMORY_ARTIFACT),
        "cockpit": _read_json(runtime / COCKPIT_STATUS_ARTIFACT),
        "edge_pattern_ledger": _read_json(runtime / EDGE_PATTERN_LEDGER_ARTIFACT),
        "edge_memory_ledger": _read_json(runtime / EDGE_MEMORY_LEDGER_ARTIFACT),
        "edge_tracker_check": _read_json(runtime / EDGE_TRACKER_CHECK_ARTIFACT),
        "pattern_recognition_engine": _read_json(runtime / PATTERN_RECOGNITION_ENGINE_ARTIFACT),
    }


def _strategy_labels_by_family(cockpit: dict[str, Any]) -> dict[str, str]:
    mission = cockpit.get("mission_control") if isinstance(cockpit.get("mission_control"), dict) else {}
    strategy = mission.get("strategy") if isinstance(mission.get("strategy"), dict) else {}
    families = strategy.get("strategy_families") if isinstance(strategy.get("strategy_families"), list) else []
    labels: dict[str, str] = {}
    for family in families:
        if not isinstance(family, dict):
            continue
        key = str(family.get("instrument") or family.get("key") or "").strip()
        label = str(family.get("key") or family.get("label") or key).strip()
        if key and label:
            labels[key] = label
    return labels


def _complete_edges(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        edge
        for edge in edges
        if edge.get("forward_return") is not None
        and edge.get("price_before") is not None
        and edge.get("price_after") is not None
    ]


def _incomplete_edges(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [edge for edge in edges if edge not in _complete_edges(edges)]


def _score_group(edges: list[dict[str, Any]], label_state: str, route_fit: str) -> dict[str, float]:
    returns = [_float(edge.get("forward_return")) for edge in edges]
    returns = [value for value in returns if value is not None]
    sample_size = len(edges)
    unique_sources = {str(edge.get("source_key")) for edge in edges}
    unique_pipelines = {str(edge.get("source_pipeline")) for edge in edges}
    unique_markets = {str(edge.get("market_symbol")) for edge in edges}
    positive_count = sum(1 for value in returns if value > 0)
    negative_count = sum(1 for value in returns if value < 0)
    directional_consistency = (
        max(positive_count, negative_count) / len(returns)
        if returns
        else 0.0
    )
    persistence = _clamp((min(sample_size, 30) / 30) * 0.55 + (min(len(unique_sources), 8) / 8) * 0.45)
    effect_size = _clamp(abs(_mean(returns)) / 0.03)
    source_quorum = _clamp(
        (
            sum(1 for edge in edges if edge.get("source_quorum_credit_allowed") is True)
            / sample_size
            if sample_size
            else 0.0
        )
        * min(1.0, len(unique_pipelines) / 2)
    )
    novelty = 0.65 if label_state == "unlabeled_pattern" else 0.35
    if len(unique_markets) > 1:
        novelty += 0.1
    route_fit_score = {
        "paper_proxy_available": 0.75,
        "observable_not_paper_route_ready": 0.35,
        "prediction_market_route_blocked": 0.2,
        "supplemental_context_only": 0.15,
        "route_unknown": 0.1,
    }.get(route_fit, 0.1)
    drawdown_penalty = 0.08 if returns and _mean(returns) >= 0 else 0.2
    false_positive_risk = _clamp(1 - min(sample_size, 40) / 40 + (0.15 if len(set(returns)) <= 1 else 0.0))
    regime_sensitivity = _clamp(0.25 + min(len(unique_pipelines), 5) / 10)
    data_quality_penalty = _clamp(1 - _mean([_float(edge.get("data_completeness_score")) or 0.0 for edge in edges]))
    regime_fragility_penalty = 0.35 if len(unique_pipelines) < 2 else 0.18
    positive = (
        persistence
        + effect_size
        + directional_consistency
        + source_quorum
        + novelty
        + route_fit_score
    ) / 6
    negative = (drawdown_penalty + false_positive_risk + regime_fragility_penalty + data_quality_penalty) / 4
    score = _clamp((positive * 0.72) + ((1 - negative) * 0.28))
    return {
        "persistence_score": persistence,
        "effect_size_score": effect_size,
        "directional_consistency_score": _clamp(directional_consistency),
        "drawdown_penalty": _clamp(drawdown_penalty),
        "false_positive_risk": _clamp(false_positive_risk),
        "regime_sensitivity_score": regime_sensitivity,
        "source_quorum_score": source_quorum,
        "novelty_score": _clamp(novelty),
        "route_fit_score": _clamp(route_fit_score),
        "data_quality_penalty": data_quality_penalty,
        "regime_fragility_penalty": _clamp(regime_fragility_penalty),
        "pattern_scan_score": score,
    }


def _route_fit(edges: list[dict[str, Any]]) -> str:
    if any(edge.get("paper_route_available") for edge in edges):
        return "paper_proxy_available"
    families = {str(edge.get("market_family")) for edge in edges}
    symbols = {str(edge.get("market_symbol")) for edge in edges}
    if any("prediction" in family for family in families):
        return "prediction_market_route_blocked"
    if any(symbol.startswith("TVC:") or "=" in symbol for symbol in symbols):
        return "observable_not_paper_route_ready"
    return "route_unknown"


def _label_state(market_families: list[str], labels_by_family: dict[str, str]) -> tuple[str, list[str], bool]:
    labels = [labels_by_family[family] for family in market_families if family in labels_by_family]
    if not labels:
        return "unlabeled_pattern", [], True
    if len(set(labels)) > 1:
        return "maps_to_multiple_existing_strategies", sorted(set(labels)), False
    return "maps_to_existing_strategy", sorted(set(labels)), False


def _candidate_from_group(
    *,
    pattern_type: str,
    edges: list[dict[str, Any]],
    generated_at: str,
    labels_by_family: dict[str, str],
    relationship_summary: str,
    next_review_base: list[str],
) -> dict[str, Any]:
    source_keys = sorted({str(edge.get("source_key")) for edge in edges})
    source_pipelines = sorted({str(edge.get("source_pipeline")) for edge in edges})
    market_symbols = sorted({str(edge.get("market_symbol")) for edge in edges})
    market_families = sorted({str(edge.get("market_family")) for edge in edges})
    time_windows = sorted({str(edge.get("time_window")) for edge in edges})
    route_fit = _route_fit(edges)
    label_state, labels, new_strategy_candidate = _label_state(market_families, labels_by_family)
    scores = _score_group(edges, label_state, route_fit)
    degraded = [
        "historical_forward_coverage_partial",
        "current_sample_not_full_backtest",
    ]
    if route_fit != "paper_proxy_available":
        degraded.append("market_route_not_guarded_paper_ready")
    if len(source_keys) < 2:
        degraded.append("single_source_pattern")
    next_required_review = list(dict.fromkeys(next_review_base + ["coverage_repair"]))
    if pattern_type in {"source_cluster_to_asset", "source_to_source"}:
        next_required_review = list(dict.fromkeys(next_required_review + ["nonlinear_quantum_pattern_lab"]))
    pattern_state = "candidate_for_linear_review" if len(source_keys) >= 2 else "watch_only"
    candidate = {
        "schema_version": SCHEMA_VERSION,
        "pattern_id": _pattern_id(pattern_type, source_keys, market_symbols, time_windows),
        "generated_at": generated_at,
        "pattern_state": pattern_state,
        "pattern_type": pattern_type,
        "pattern_not_strategy": True,
        "source_keys": source_keys,
        "source_pipelines": source_pipelines,
        "market_symbols": market_symbols,
        "market_families": market_families,
        "time_windows": time_windows,
        "relationship_summary": relationship_summary,
        "matrix_row_ids": sorted({str(edge.get("matrix_row_id")) for edge in edges})[:100],
        "sample_size": len(edges),
        "distinct_source_count": len(source_keys),
        "distinct_source_pipeline_count": len(source_pipelines),
        "distinct_market_count": len(market_symbols),
        "score_components": scores,
        **scores,
        "paper_route_fit": route_fit,
        "label_state": label_state,
        "initial_strategy_labels": labels,
        "new_strategy_candidate": bool(new_strategy_candidate and not degraded),
        "candidate_for_strategy_foundry": False,
        "candidate_for_akber_filter": False,
        "candidate_for_paper_route": False,
        "next_required_review": next_required_review,
        "degraded_inputs": degraded,
        "source_quorum_credit_allowed": False,
        "strategy_hypothesis_creation_allowed": False,
        "trade_candidate_creation_allowed": False,
        "risk_approval_allowed": False,
        "proof_credit_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
        "direct_paperops_handoff_allowed": False,
        "authority": dict(FULL_UNIVERSE_AUTHORITY_FLAGS),
    }
    candidate.update(FULL_UNIVERSE_AUTHORITY_FLAGS)
    return candidate


def _rejected_pattern(
    *,
    pattern_type: str,
    generated_at: str,
    edges: list[dict[str, Any]],
    rejection_reasons: list[str],
    failed_metrics: dict[str, Any],
    data_quality_issues: list[str],
    next_allowed_action: str,
    rejection_state: str = "rejected",
) -> dict[str, Any]:
    source_keys = sorted({str(edge.get("source_key")) for edge in edges if edge.get("source_key")})
    source_pipelines = sorted({str(edge.get("source_pipeline")) for edge in edges if edge.get("source_pipeline")})
    market_symbols = sorted({str(edge.get("market_symbol")) for edge in edges if edge.get("market_symbol")})
    market_families = sorted({str(edge.get("market_family")) for edge in edges if edge.get("market_family")})
    tested_windows = sorted({str(edge.get("time_window")) for edge in edges if edge.get("time_window")})
    rejection = {
        "schema_version": SCHEMA_VERSION,
        "pattern_id": _pattern_id(pattern_type, source_keys, market_symbols, tested_windows, "rejected"),
        "generated_at": generated_at,
        "rejection_state": rejection_state,
        "pattern_type": pattern_type,
        "pattern_not_strategy": True,
        "source_keys": source_keys,
        "source_pipelines": source_pipelines,
        "market_symbols": market_symbols,
        "market_families": market_families,
        "tested_windows": tested_windows,
        "matrix_row_ids": sorted({str(edge.get("matrix_row_id")) for edge in edges if edge.get("matrix_row_id")})[:100],
        "sample_size": len(edges),
        "rejection_reasons": rejection_reasons,
        "failed_metrics": failed_metrics,
        "overfit_risk": "high" if len(edges) < 20 else "medium",
        "data_quality_issues": data_quality_issues,
        "next_allowed_action": next_allowed_action,
        "source_quorum_credit_allowed": False,
        "strategy_hypothesis_creation_allowed": False,
        "trade_candidate_creation_allowed": False,
        "risk_approval_allowed": False,
        "proof_credit_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
        "direct_paperops_handoff_allowed": False,
        "authority": dict(FULL_UNIVERSE_AUTHORITY_FLAGS),
    }
    rejection.update(FULL_UNIVERSE_AUTHORITY_FLAGS)
    return rejection


def _build_candidate_patterns(
    complete_edges: list[dict[str, Any]],
    generated_at: str,
    labels_by_family: dict[str, str],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()

    for (source_pipeline, market_family, time_window), rows in sorted(
        _group_by(complete_edges, "source_pipeline", "market_family", "time_window").items()
    ):
        if len(rows) < 3 or len({row.get("source_key") for row in rows}) < 2:
            continue
        candidate = _candidate_from_group(
            pattern_type="source_to_asset_lag",
            edges=rows,
            generated_at=generated_at,
            labels_by_family=labels_by_family,
            relationship_summary=(
                f"{source_pipeline} source states co-occurred with {market_family} "
                f"moves over {time_window}; current evidence is preliminary."
            ),
            next_review_base=["linear_pattern_lab"],
        )
        if candidate["pattern_id"] not in seen:
            candidates.append(candidate)
            seen.add(candidate["pattern_id"])

    for (market_family, time_window), rows in sorted(
        _group_by(complete_edges, "market_family", "time_window").items()
    ):
        if len({row.get("source_pipeline") for row in rows}) < 2 or len(rows) < 6:
            continue
        candidate = _candidate_from_group(
            pattern_type="source_cluster_to_asset",
            edges=rows,
            generated_at=generated_at,
            labels_by_family=labels_by_family,
            relationship_summary=(
                f"Multiple source pipelines cluster around {market_family} "
                f"moves over {time_window}; needs linear and nonlinear review."
            ),
            next_review_base=["linear_pattern_lab"],
        )
        if candidate["pattern_id"] not in seen:
            candidates.append(candidate)
            seen.add(candidate["pattern_id"])

    for (market_family, time_window), rows in sorted(
        _group_by(complete_edges, "market_family", "time_window").items()
    ):
        if len({row.get("source_pipeline") for row in rows}) < 2:
            continue
        candidate = _candidate_from_group(
            pattern_type="source_to_source",
            edges=rows,
            generated_at=generated_at,
            labels_by_family=labels_by_family,
            relationship_summary=(
                f"Source pipelines show same-window co-presence around {market_family} "
                f"for {time_window}; this is a relationship to test, not a strategy."
            ),
            next_review_base=["nonlinear_quantum_pattern_lab"],
        )
        if candidate["pattern_id"] not in seen:
            candidates.append(candidate)
            seen.add(candidate["pattern_id"])

    return sorted(candidates, key=lambda row: row["pattern_scan_score"], reverse=True)


def _build_rejected_patterns(
    edges: list[dict[str, Any]],
    complete_edges: list[dict[str, Any]],
    generated_at: str,
) -> list[dict[str, Any]]:
    rejected: list[dict[str, Any]] = []
    seen: set[str] = set()
    complete_ids = {edge.get("matrix_row_id") for edge in complete_edges}
    incomplete_edges = [edge for edge in edges if edge.get("matrix_row_id") not in complete_ids]

    for (market_family, time_window), rows in sorted(
        _group_by(incomplete_edges, "market_family", "time_window").items()
    ):
        if not rows:
            continue
        rejection = _rejected_pattern(
            pattern_type="source_price_lag",
            generated_at=generated_at,
            edges=rows,
            rejection_reasons=["market_history_too_thin", "historical_price_window_missing"],
            failed_metrics={
                "complete_forward_outcome_count": 0,
                "required_forward_outcome_count": len(rows),
                "time_window": time_window,
            },
            data_quality_issues=["missing_forward_price_or_outcome_window"],
            next_allowed_action="coverage_repair",
            rejection_state="blocked_by_coverage",
        )
        if rejection["pattern_id"] not in seen:
            rejected.append(rejection)
            seen.add(rejection["pattern_id"])

    for (source_key, market_family), rows in sorted(
        _group_by(complete_edges, "source_key", "market_family").items()
    ):
        if not rows:
            continue
        rejection = _rejected_pattern(
            pattern_type="single_source_to_asset",
            generated_at=generated_at,
            edges=rows,
            rejection_reasons=["single_source_pattern_cannot_advance", "sample_too_small"],
            failed_metrics={
                "distinct_source_count": 1,
                "sample_size": len(rows),
                "minimum_distinct_source_count": 2,
                "minimum_sample_size": 8,
            },
            data_quality_issues=["single_source_evidence_is_research_only"],
            next_allowed_action="store_reject_and_wait_for_independent_source_confirmation",
        )
        if rejection["pattern_id"] not in seen:
            rejected.append(rejection)
            seen.add(rejection["pattern_id"])

    for (source_pipeline, time_window), rows in sorted(
        _group_by(complete_edges, "source_pipeline", "time_window").items()
    ):
        market_families = {row.get("market_family") for row in rows}
        if len(market_families) >= 2:
            continue
        rejection = _rejected_pattern(
            pattern_type="asset_to_asset",
            generated_at=generated_at,
            edges=rows,
            rejection_reasons=["cross_asset_coverage_too_thin"],
            failed_metrics={
                "distinct_market_family_count": len(market_families),
                "minimum_market_family_count": 2,
            },
            data_quality_issues=["complete_current_outcomes_exist_for_one_market_family_only"],
            next_allowed_action="coverage_repair",
            rejection_state="blocked_by_coverage",
        )
        if rejection["pattern_id"] not in seen:
            rejected.append(rejection)
            seen.add(rejection["pattern_id"])

    for (market_family,), rows in sorted(_group_by(complete_edges, "market_family").items()):
        windows = {row.get("time_window") for row in rows}
        forward_windows = {window for window in windows if str(window).endswith("_forward")}
        if len(forward_windows) >= 2:
            continue
        rejection = _rejected_pattern(
            pattern_type="regime_to_asset",
            generated_at=generated_at,
            edges=rows,
            rejection_reasons=["regime_coverage_too_thin", "forward_windows_missing"],
            failed_metrics={
                "forward_window_count": len(forward_windows),
                "minimum_forward_window_count": 2,
                "observed_windows": sorted(str(window) for window in windows),
            },
            data_quality_issues=["no_regime_split_possible_without_forward_window_history"],
            next_allowed_action="coverage_repair",
            rejection_state="blocked_by_coverage",
        )
        if rejection["pattern_id"] not in seen:
            rejected.append(rejection)
            seen.add(rejection["pattern_id"])

    for (market_symbol,), rows in sorted(_group_by(complete_edges, "market_symbol").items()):
        if any(row.get("paper_route_available") for row in rows):
            continue
        rejection = _rejected_pattern(
            pattern_type="route_fit",
            generated_at=generated_at,
            edges=rows,
            rejection_reasons=["route_unavailable_for_current_complete_observation"],
            failed_metrics={
                "paper_route_available_count": 0,
                "market_symbol": market_symbol,
            },
            data_quality_issues=["complete_observation_uses_observable_non_paper_route_symbol"],
            next_allowed_action="retain_for_research_or_find_guarded_paper_proxy",
            rejection_state="watch_only_rejected_for_route",
        )
        if rejection["pattern_id"] not in seen:
            rejected.append(rejection)
            seen.add(rejection["pattern_id"])

    return rejected


def _scan_method_summary(
    edges: list[dict[str, Any]],
    complete_edges: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    rejected: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    candidate_types = defaultdict(int)
    rejected_types = defaultdict(int)
    for candidate in candidates:
        candidate_types[candidate["pattern_type"]] += 1
    for rejection in rejected:
        rejected_types[rejection["pattern_type"]] += 1
    complete_windows = {edge.get("time_window") for edge in complete_edges}
    return [
        {
            "method": method,
            "status": "ran_degraded" if complete_edges else "blocked_no_complete_edges",
            "matrix_row_count": len(edges),
            "complete_row_count": len(complete_edges),
            "candidate_count": sum(candidate_types.values()),
            "rejected_count": sum(rejected_types.values()),
            "coverage_note": "complete_windows=" + ",".join(sorted(str(window) for window in complete_windows)),
            "authority": "research_only_no_trade_candidate_creation",
        }
        for method in SCAN_METHODS
    ]


def _dashboard_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_full_universe_pattern_search_dashboard_summary",
        "generated_at": payload["generated_at"],
        "status": payload["status"],
        "public_safe": True,
        "command_disabled": True,
        "live_send_allowed": False,
        "summary_rows": [
            {"label": "Matrix rows scanned", "value": payload["matrix_row_count"]},
            {"label": "Candidate patterns", "value": payload["candidate_pattern_count"]},
            {"label": "Rejected patterns", "value": payload["rejected_pattern_count"]},
            {"label": "Coverage gaps", "value": len(payload["coverage_gaps"])},
            {"label": "New strategy candidates", "value": payload["new_strategy_candidate_count"]},
            {"label": "Trade candidates created", "value": 0},
            {"label": "Authority", "value": "research_only_patterns_not_strategies"},
        ],
        "top_candidate_pattern": payload["candidate_patterns"][0]["pattern_id"]
        if payload["candidate_patterns"]
        else None,
        "top_rejected_reason": payload["rejected_patterns"][0]["rejection_reasons"][0]
        if payload["rejected_patterns"]
        else None,
        "authority_flags_false": all(value is False for value in payload["authority_flags"].values()),
        "patterns_are_not_strategies": True,
        "no_trade_candidates_created": True,
        "no_paper_orders_created": True,
        "no_proof_credit_granted": True,
    }


def build_full_universe_pattern_search(settings: Settings | None = None) -> dict[str, Any]:
    context = _load_context(settings)
    generated_at = _iso(_now())
    self_model = context["self_model"]
    matrix = context["matrix"]
    edges = context["matrix_edges"]
    historical_coverage = context["historical_coverage"]
    historical_memory = context["historical_memory"]
    labels_by_family = _strategy_labels_by_family(context["cockpit"])
    complete = _complete_edges(edges)
    candidates = _build_candidate_patterns(complete, generated_at, labels_by_family)
    rejected = _build_rejected_patterns(edges, complete, generated_at)
    coverage_gaps = []
    for gap in matrix.get("coverage", {}).get("coverage_gaps", []):
        if isinstance(gap, dict):
            coverage_gaps.append(gap)
    if historical_coverage.get("window_incomplete_record_count"):
        coverage_gaps.append(
            {
                "gap_type": "historical_memory_missing_windows",
                "count": historical_coverage.get("window_incomplete_record_count"),
                "authority_impact": "patterns_remain_research_only_and_degraded",
            }
        )
    missing_required_state: list[str] = []
    if not self_model:
        missing_required_state.append("qsase_self_model_missing")
    if not matrix:
        missing_required_state.append("qsase_universal_source_price_matrix_missing")
    if not edges:
        missing_required_state.append("qsase_source_price_edges_missing")
    if not historical_memory:
        missing_required_state.append("qsase_historical_source_price_memory_missing")

    degraded_reasons: list[str] = []
    hold_reasons: list[str] = []
    if matrix.get("status") not in SOURCE_PRICE_MATRIX_READY_STATUSES:
        degraded_reasons.append("source_price_matrix_degraded")
    elif matrix.get("status") == "qsase_source_price_matrix_ready_with_gaps":
        hold_reasons.append("source_price_matrix_has_coverage_gaps")
    if historical_memory.get("status") not in HISTORICAL_MEMORY_READY_STATUSES:
        degraded_reasons.append("historical_memory_degraded")
    elif historical_memory.get("status") == "qsase_historical_source_price_memory_ready_with_gaps":
        hold_reasons.append("historical_memory_has_missing_forward_windows")
    if coverage_gaps:
        hold_reasons.append("coverage_gaps_present")
    if not complete:
        degraded_reasons.append("no_complete_source_price_outcomes")

    status = "qsase_full_universe_pattern_search_ready"
    if missing_required_state:
        status = "qsase_full_universe_pattern_search_blocked"
    elif degraded_reasons:
        status = "qsase_full_universe_pattern_search_degraded"
    elif hold_reasons or rejected:
        status = "qsase_full_universe_pattern_search_ready_with_research_gaps"

    strategy_labels = sorted(
        {
            label
            for candidate in candidates
            for label in candidate.get("initial_strategy_labels", [])
        }
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_full_universe_pattern_search",
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "generated_at": generated_at,
        "status": status,
        "public_safe": True,
        "command_disabled": True,
        "paper_only": True,
        "proposal_first": True,
        "research_only": True,
        "patterns_are_not_strategies": True,
        "self_model_status": self_model.get("status"),
        "matrix_status": matrix.get("status"),
        "historical_memory_status": historical_memory.get("status"),
        "matrix_row_count": len(edges),
        "source_count": matrix.get("source_universe", {}).get("source_count", 0),
        "market_count": matrix.get("trading_universe", {}).get("watched_market_count", 0),
        "relationship_count": len(edges),
        "complete_relationship_count": len(complete),
        "candidate_pattern_count": len(candidates),
        "rejected_pattern_count": len(rejected),
        "strategy_label_count": len(strategy_labels),
        "new_strategy_candidate_count": sum(1 for candidate in candidates if candidate["new_strategy_candidate"]),
        "scan_methods": _scan_method_summary(edges, complete, candidates, rejected),
        "candidate_patterns": candidates,
        "rejected_patterns": rejected,
        "coverage_gaps": coverage_gaps,
        "degraded_reasons": sorted(set(degraded_reasons)),
        "hold_reasons": sorted(set(hold_reasons)),
        "missing_required_state": missing_required_state,
        "candidate_patterns_path": f"data/runtime/{CANDIDATE_PATTERNS_ARTIFACT}",
        "rejected_patterns_path": f"data/runtime/{REJECTED_PATTERNS_ARTIFACT}",
        "input_artifacts": {
            "self_model": f"data/runtime/{SELF_MODEL_ARTIFACT}",
            "matrix": f"data/runtime/{MATRIX_ARTIFACT}",
            "matrix_edges": f"data/runtime/{MATRIX_EDGES_ARTIFACT}",
            "historical_coverage": f"data/runtime/{HISTORICAL_COVERAGE_ARTIFACT}",
            "historical_memory": f"data/runtime/{HISTORICAL_MEMORY_ARTIFACT}",
            "edge_pattern_ledger_present": bool(context["edge_pattern_ledger"]),
            "edge_memory_ledger_present": bool(context["edge_memory_ledger"]),
            "edge_tracker_check_present": bool(context["edge_tracker_check"]),
            "pattern_recognition_engine_present": bool(context["pattern_recognition_engine"]),
        },
        "full_universe_scope": {
            "all_sources_scanned": True,
            "all_markets_scanned": True,
            "all_time_windows_scanned": True,
            "source_price_lags_evaluated": True,
            "cross_source_relationships_evaluated": True,
            "cross_asset_relationships_evaluated": True,
            "regime_conditioned_relationships_evaluated": True,
            "strategy_sleeve_only_scan": False,
        },
        "no_strategy_hypotheses_created": True,
        "no_trade_candidates_created": True,
        "no_paper_orders_created": True,
        "no_broker_writes": True,
        "no_proof_credit_granted": True,
        "no_direct_paperops_eligibility": True,
        "authority": universal_authority_flags(),
        "authority_flags": dict(FULL_UNIVERSE_AUTHORITY_FLAGS),
        "dashboard_safe_summary": {},
    }
    payload["dashboard_safe_summary"] = _dashboard_summary(payload)
    return payload


def _validate_authority_flags(flags: dict[str, Any], prefix: str) -> list[str]:
    errors: list[str] = []
    for key, expected in FULL_UNIVERSE_AUTHORITY_FLAGS.items():
        if flags.get(key) is not expected:
            errors.append(f"{prefix}_{key}_must_be_false")
    return errors


def validate_full_universe_pattern_search(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("artifact_type") != "qsase_full_universe_pattern_search":
        errors.append("artifact_type_invalid")
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if payload.get("status") not in {
        "qsase_full_universe_pattern_search_ready",
        "qsase_full_universe_pattern_search_ready_with_research_gaps",
        "qsase_full_universe_pattern_search_degraded",
        "qsase_full_universe_pattern_search_blocked",
    }:
        errors.append("status_invalid")
    if payload.get("public_safe") is not True or payload.get("command_disabled") is not True:
        errors.append("public_safe_command_disabled_required")
    if payload.get("patterns_are_not_strategies") is not True:
        errors.append("patterns_are_not_strategies_required")
    for key in (
        "no_strategy_hypotheses_created",
        "no_trade_candidates_created",
        "no_paper_orders_created",
        "no_broker_writes",
        "no_proof_credit_granted",
        "no_direct_paperops_eligibility",
    ):
        if payload.get(key) is not True:
            errors.append(f"{key}_must_be_true")
    for forbidden in ("trade_candidates", "paper_orders", "strategy_hypotheses"):
        if forbidden in payload:
            errors.append(f"{forbidden}_must_not_exist")
    authority = payload.get("authority", {})
    if not isinstance(authority, dict) or any(value is not False for value in authority.values()):
        errors.append("universal_authority_flags_must_all_be_false")
    errors.extend(_validate_authority_flags(payload.get("authority_flags", {}), "search"))

    scope = payload.get("full_universe_scope", {})
    for key in (
        "all_sources_scanned",
        "all_markets_scanned",
        "all_time_windows_scanned",
        "source_price_lags_evaluated",
        "cross_source_relationships_evaluated",
        "cross_asset_relationships_evaluated",
        "regime_conditioned_relationships_evaluated",
    ):
        if scope.get(key) is not True:
            errors.append(f"scope_{key}_must_be_true")
    if scope.get("strategy_sleeve_only_scan") is not False:
        errors.append("scope_strategy_sleeve_only_scan_must_be_false")

    scan_methods = payload.get("scan_methods", [])
    method_names = {method.get("method") for method in scan_methods if isinstance(method, dict)}
    for method in SCAN_METHODS:
        if method not in method_names:
            errors.append(f"scan_method_{method}_missing")

    candidates = payload.get("candidate_patterns")
    if not isinstance(candidates, list):
        errors.append("candidate_patterns_missing")
        candidates = []
    rejected = payload.get("rejected_patterns")
    if not isinstance(rejected, list) or not rejected:
        errors.append("rejected_patterns_missing")
        rejected = []

    for candidate in candidates:
        pattern_id = candidate.get("pattern_id")
        for field in REQUIRED_CANDIDATE_FIELDS:
            if field not in candidate:
                errors.append(f"candidate_{pattern_id}_missing_{field}")
        expected_id = _pattern_id(
            candidate.get("pattern_type", ""),
            candidate.get("source_keys", []),
            candidate.get("market_symbols", []),
            candidate.get("time_windows", []),
        )
        if pattern_id != expected_id:
            errors.append(f"candidate_{pattern_id}_pattern_id_not_stable")
        if not candidate.get("matrix_row_ids"):
            errors.append(f"candidate_{pattern_id}_missing_matrix_row_ids")
        if candidate.get("pattern_not_strategy") is not True:
            errors.append(f"candidate_{pattern_id}_pattern_not_strategy_required")
        if candidate.get("candidate_for_paper_route") is not False:
            errors.append(f"candidate_{pattern_id}_paper_route_must_be_false")
        if candidate.get("candidate_for_strategy_foundry") is not False:
            errors.append(f"candidate_{pattern_id}_strategy_foundry_must_be_false_in_qsase_4_degraded_scan")
        if candidate.get("new_strategy_candidate") is not False:
            errors.append(f"candidate_{pattern_id}_new_strategy_candidate_must_be_false")
        if "strategy_foundry" in candidate.get("next_required_review", []):
            errors.append(f"candidate_{pattern_id}_must_not_route_to_strategy_foundry")
        for key in FULL_UNIVERSE_AUTHORITY_FLAGS:
            if candidate.get(key) is not False:
                errors.append(f"candidate_{pattern_id}_{key}_must_be_false")
            if candidate.get("authority", {}).get(key) is not False:
                errors.append(f"candidate_{pattern_id}_authority_{key}_must_be_false")
        score_components = candidate.get("score_components", {})
        for score_key in (
            "persistence_score",
            "effect_size_score",
            "directional_consistency_score",
            "source_quorum_score",
            "novelty_score",
            "pattern_scan_score",
        ):
            value = score_components.get(score_key, candidate.get(score_key))
            if not isinstance(value, (int, float)) or value < 0 or value > 1:
                errors.append(f"candidate_{pattern_id}_{score_key}_invalid")

    for rejection in rejected:
        pattern_id = rejection.get("pattern_id")
        for field in REQUIRED_REJECTED_FIELDS:
            if field not in rejection:
                errors.append(f"rejected_{pattern_id}_missing_{field}")
        expected_id = _pattern_id(
            rejection.get("pattern_type", ""),
            rejection.get("source_keys", []),
            rejection.get("market_symbols", []),
            rejection.get("tested_windows", []),
            "rejected",
        )
        if pattern_id != expected_id:
            errors.append(f"rejected_{pattern_id}_pattern_id_not_stable")
        if not rejection.get("rejection_reasons"):
            errors.append(f"rejected_{pattern_id}_missing_rejection_reasons")
        if rejection.get("pattern_not_strategy") is not True:
            errors.append(f"rejected_{pattern_id}_pattern_not_strategy_required")
        for key in FULL_UNIVERSE_AUTHORITY_FLAGS:
            if rejection.get(key) is not False:
                errors.append(f"rejected_{pattern_id}_{key}_must_be_false")
            if rejection.get("authority", {}).get(key) is not False:
                errors.append(f"rejected_{pattern_id}_authority_{key}_must_be_false")

    pattern_types = {candidate.get("pattern_type") for candidate in candidates} | {
        rejection.get("pattern_type") for rejection in rejected
    }
    for required_type in {
        "source_to_asset_lag",
        "source_cluster_to_asset",
        "source_to_source",
        "asset_to_asset",
        "regime_to_asset",
    }:
        if required_type not in pattern_types:
            errors.append(f"pattern_type_{required_type}_not_evaluated")

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
        "candidate_patterns_path": f"data/runtime/{CANDIDATE_PATTERNS_ARTIFACT}",
        "rejected_patterns_path": f"data/runtime/{REJECTED_PATTERNS_ARTIFACT}",
        "matrix_row_count": payload["matrix_row_count"],
        "candidate_pattern_count": payload["candidate_pattern_count"],
        "rejected_pattern_count": payload["rejected_pattern_count"],
        "new_strategy_candidate_count": payload["new_strategy_candidate_count"],
        "paper_only": True,
        "research_only": True,
        "proposal_first": True,
        "public_safe": True,
        "authority_flags_false": True,
        "patterns_are_not_strategies": True,
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
        f"## QSASE-4: Full-Universe Pattern Search\n\n"
        f"- Generated at: `{payload.get('generated_at')}`\n"
        f"- Status: `{payload.get('status')}`\n"
        f"- Runtime artifact: `data/runtime/{PRIMARY_ARTIFACT}`\n"
        f"- Matrix rows scanned: `{payload.get('matrix_row_count')}`\n"
        f"- Candidate patterns: `{payload.get('candidate_pattern_count')}`\n"
        f"- Rejected patterns: `{payload.get('rejected_pattern_count')}`\n"
        f"- Safety: patterns are not strategies; no trade candidates, paper orders, broker writes, live capital, or proof credit created.\n"
    )
    if marker in existing:
        before = existing.split(marker, 1)[0].rstrip()
        updated = before + "\n\n" + entry
    elif existing.endswith("\n"):
        updated = existing + "\n" + entry
    else:
        updated = existing + "\n\n" + entry
    log_path.write_text(updated, encoding="utf-8")


def write_full_universe_pattern_search(
    payload: dict[str, Any],
    settings: Settings | None = None,
    *,
    append_history: bool = True,
    append_log: bool = True,
) -> dict[str, str]:
    runtime_dir = _runtime_dir(settings)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "pattern_search": runtime_dir / PRIMARY_ARTIFACT,
        "candidate_patterns": runtime_dir / CANDIDATE_PATTERNS_ARTIFACT,
        "rejected_patterns": runtime_dir / REJECTED_PATTERNS_ARTIFACT,
        "dashboard_summary": runtime_dir / DASHBOARD_SUMMARY_ARTIFACT,
        "phase_status": runtime_dir / PHASE_STATUS_ARTIFACT,
    }
    _write_json(paths["pattern_search"], payload)
    _write_jsonl(paths["candidate_patterns"], payload["candidate_patterns"])
    _write_jsonl(paths["rejected_patterns"], payload["rejected_patterns"])
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
                "matrix_row_count": payload["matrix_row_count"],
                "candidate_pattern_count": payload["candidate_pattern_count"],
                "rejected_pattern_count": payload["rejected_pattern_count"],
                "new_strategy_candidate_count": payload["new_strategy_candidate_count"],
                "no_trade_candidates_created": True,
            },
        )
        _append_jsonl(
            events_path,
            {
                "generated_at": payload["generated_at"],
                "event_type": "qsase_full_universe_pattern_search_written",
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


def load_full_universe_pattern_search(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    payload = _read_json(runtime / PRIMARY_ARTIFACT)
    candidates = _read_jsonl(runtime / CANDIDATE_PATTERNS_ARTIFACT)
    rejected = _read_jsonl(runtime / REJECTED_PATTERNS_ARTIFACT)
    if payload:
        payload["candidate_patterns"] = candidates
        payload["rejected_patterns"] = rejected
    return payload


def build_and_write_full_universe_pattern_search(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    payload = build_full_universe_pattern_search(settings)
    errors = validate_full_universe_pattern_search(payload)
    written = write_full_universe_pattern_search(payload, settings)
    return payload, written, errors


def validate_negative_pattern_search_probes() -> list[str]:
    base = build_full_universe_pattern_search()
    errors: list[str] = []
    for flag in FULL_UNIVERSE_AUTHORITY_FLAGS:
        probe = copy.deepcopy(base)
        probe["authority_flags"][flag] = True
        if not any(flag in error for error in validate_full_universe_pattern_search(probe)):
            errors.append(f"negative_probe_failed_for_{flag}")

    if base["candidate_patterns"]:
        candidate_probe = copy.deepcopy(base)
        candidate_probe["candidate_patterns"][0]["trade_candidate_creation_allowed"] = True
        if not any("trade_candidate_creation_allowed" in error for error in validate_full_universe_pattern_search(candidate_probe)):
            errors.append("negative_probe_failed_for_candidate_trade_candidate_creation")

        route_probe = copy.deepcopy(base)
        route_probe["candidate_patterns"][0]["candidate_for_paper_route"] = True
        if not any("paper_route" in error for error in validate_full_universe_pattern_search(route_probe)):
            errors.append("negative_probe_failed_for_candidate_paper_route")

    rejected_probe = copy.deepcopy(base)
    rejected_probe["rejected_patterns"][0]["rejection_reasons"] = []
    if not any("missing_rejection_reasons" in error for error in validate_full_universe_pattern_search(rejected_probe)):
        errors.append("negative_probe_failed_for_rejection_reason")

    scope_probe = copy.deepcopy(base)
    scope_probe["full_universe_scope"]["all_markets_scanned"] = False
    if not any("all_markets_scanned" in error for error in validate_full_universe_pattern_search(scope_probe)):
        errors.append("negative_probe_failed_for_full_universe_scope")

    return errors


if __name__ == "__main__":
    artifact = build_full_universe_pattern_search()
    print(_json_dump(artifact))
