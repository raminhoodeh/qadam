"""Strategy Evidence Map for Qadam next-generation flow Phase 5.

The map attaches evidence quality to Qadam's core strategy families. It does
not create strategy hypotheses, trade candidates, approvals, orders, broker
writes, proof credit, or live-capital authority.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from statistics import mean
from typing import Any

from orchestrator.config import Settings

SCHEMA_VERSION = "qadam_strategy_evidence_map.v1"
PHASE_ID = "qadam_next_generation_phase_5_strategy_evidence_map"

PRIMARY_ARTIFACT = "qadam_strategy_evidence_map.json"
RECORDS_ARTIFACT = "qadam_strategy_evidence_map_records.jsonl"
REJECTIONS_ARTIFACT = "qadam_strategy_evidence_map_rejections.jsonl"
DASHBOARD_SUMMARY_ARTIFACT = "qadam_strategy_evidence_map_dashboard_summary.json"
EVENTS_ARTIFACT = "qadam_strategy_evidence_map_events.jsonl"

STRATEGY_UNIVERSE_ARTIFACT = "qsase_dashboard_strategy_universe.json"
TRADING_UNIVERSE_ARTIFACT = "qsase_trading_universe.json"
PATTERN_ENGINE_V2_ARTIFACT = "qadam_pattern_engine_v2.json"
PATTERN_ENGINE_V2_RECORDS_ARTIFACT = "qadam_pattern_engine_v2_records.jsonl"
PATTERN_ENGINE_V2_REJECTIONS_ARTIFACT = "qadam_pattern_engine_v2_rejections.jsonl"
SOURCE_EVIDENCE_CONTRACTS_ARTIFACT = "qadam_source_evidence_contracts.jsonl"
PRICE_EVIDENCE_CONTRACTS_ARTIFACT = "qadam_price_evidence_contracts.jsonl"
STRATEGY_EVIDENCE_CONTRACTS_ARTIFACT = "qadam_strategy_evidence_contracts.jsonl"
AKBER_EVIDENCE_CONTRACTS_ARTIFACT = "qadam_akber_evidence_contracts.jsonl"
HYPOTHESIS_EVIDENCE_CONTRACTS_ARTIFACT = "qadam_hypothesis_evidence_contracts.jsonl"
BASELINE_STRATEGY_EVIDENCE_MAP_ARTIFACT = "qsase_baseline_strategy_evidence_map.json"
EVIDENCE_CONTRACTS_SUMMARY_ARTIFACT = "qadam_evidence_contracts_summary.json"

REQUIRED_RECORD_SECTIONS = (
    "source_contribution",
    "instrument_contribution",
    "expectancy_profile",
    "drawdown_profile",
    "failure_modes",
    "stale_data_sensitivity",
    "akber_sensitivity",
    "quantum_nonlinear_usefulness",
    "paperability_limits",
    "confidence_class",
)

AUTHORITY_FLAGS = {
    "read_only": True,
    "paper_only": True,
    "proposal_first": True,
    "research_only": True,
    "strategy_evidence_only": True,
    "strategy_hypothesis_creation_allowed": False,
    "strategy_hypothesis_created": False,
    "source_quorum_credit_granted": False,
    "trade_candidate_creation_allowed": False,
    "trade_candidate_created": False,
    "qualified_setup_created": False,
    "risk_handoff_allowed": False,
    "risk_approval_allowed": False,
    "risk_approval_created": False,
    "execution_allowed": False,
    "execution_approval_allowed": False,
    "execution_approval_created": False,
    "paper_order_allowed": False,
    "paper_order_created": False,
    "broker_write_allowed": False,
    "broker_write_count": 0,
    "live_broker_endpoint_allowed": False,
    "live_capital_enabled": False,
    "proof_credit_allowed": False,
    "paper_proof_ledger_credit_allowed": False,
    "paper_growth_trial_calendar_advance_allowed": False,
    "paper_growth_trial_calendar_advanced": False,
    "simulated_elapsed_time_allowed": False,
    "strategy_mutation_allowed": False,
    "filter_threshold_update_allowed": False,
    "telegram_command_path_enabled": False,
    "telegram_trade_command_enabled": False,
}

FORBIDDEN_TRUE_FIELDS = tuple(
    key for key, value in AUTHORITY_FLAGS.items() if value is False
)
FORBIDDEN_NONZERO_FIELDS = tuple(
    key for key, value in AUTHORITY_FLAGS.items() if isinstance(value, int) and value == 0
)


@dataclass(frozen=True)
class StrategyEvidenceBundle:
    primary: dict[str, Any]
    records: list[dict[str, Any]]
    rejections: list[dict[str, Any]]
    dashboard_summary: dict[str, Any]


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


def _iso(dt: datetime | None = None) -> str:
    return (dt or _now()).astimezone(timezone.utc).isoformat()


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


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _hash_id(prefix: str, parts: list[Any]) -> str:
    payload = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]
    return f"{prefix}:{digest}"


def _authority() -> dict[str, Any]:
    return dict(AUTHORITY_FLAGS)


def _load_context(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "runtime_dir": runtime,
        "strategy_universe": _read_json(runtime / STRATEGY_UNIVERSE_ARTIFACT),
        "trading_universe": _read_json(runtime / TRADING_UNIVERSE_ARTIFACT),
        "pattern_engine_v2": _read_json(runtime / PATTERN_ENGINE_V2_ARTIFACT),
        "pattern_records": _read_jsonl(runtime / PATTERN_ENGINE_V2_RECORDS_ARTIFACT),
        "pattern_rejections": _read_jsonl(runtime / PATTERN_ENGINE_V2_REJECTIONS_ARTIFACT),
        "source_contracts": _read_jsonl(runtime / SOURCE_EVIDENCE_CONTRACTS_ARTIFACT),
        "price_contracts": _read_jsonl(runtime / PRICE_EVIDENCE_CONTRACTS_ARTIFACT),
        "strategy_contracts": _read_jsonl(runtime / STRATEGY_EVIDENCE_CONTRACTS_ARTIFACT),
        "akber_contracts": _read_jsonl(runtime / AKBER_EVIDENCE_CONTRACTS_ARTIFACT),
        "hypothesis_contracts": _read_jsonl(runtime / HYPOTHESIS_EVIDENCE_CONTRACTS_ARTIFACT),
        "baseline_strategy_map": _read_json(runtime / BASELINE_STRATEGY_EVIDENCE_MAP_ARTIFACT),
        "evidence_contracts_summary": _read_json(runtime / EVIDENCE_CONTRACTS_SUMMARY_ARTIFACT),
    }


def _tokens(*values: Any) -> set[str]:
    token_set: set[str] = set()
    for value in values:
        if isinstance(value, list):
            token_set.update(_tokens(*value))
            continue
        if isinstance(value, dict):
            token_set.update(_tokens(*value.values()))
            continue
        raw = str(value or "").lower()
        if not raw:
            continue
        cleaned = raw.replace("=", "").replace(":", "_").replace("-", "_").replace("/", "_")
        token_set.add(cleaned)
        for part in cleaned.replace(".", "_").split("_"):
            if part:
                token_set.add(part)
    aliases = set(token_set)
    if {"cl", "uso", "xle", "bno", "oil", "crude", "energy"} & token_set:
        aliases.update({"crude_oil", "energy_security", "energy"})
    if {"ita", "xar", "lmt", "ppa", "defence", "defense"} & token_set:
        aliases.update({"defence", "defense", "geopolitical_security"})
    if {"kalshi", "polymarket", "prediction"} & token_set:
        aliases.update({"prediction_markets", "event_contracts"})
    if {"smh", "soxx", "nvda", "semiconductor", "chip"} & token_set:
        aliases.update({"semiconductors", "technology_policy"})
    if {"slv", "silver", "xag", "si", "sil", "gld"} & token_set:
        aliases.update({"silver", "macro_liquidity", "macro_watchlist"})
    return aliases


def _strategy_tokens(strategy: dict[str, Any]) -> set[str]:
    return _tokens(
        strategy.get("strategy_family_id"),
        strategy.get("label"),
        strategy.get("allowed_proxy_set"),
        strategy.get("instrument_keywords"),
        strategy.get("source_keywords"),
        strategy.get("watched_markets"),
    )


def _strategy_market_tokens(strategy: dict[str, Any]) -> set[str]:
    tokens = _tokens(
        strategy.get("allowed_proxy_set"),
        strategy.get("instrument_keywords"),
        strategy.get("watched_markets"),
    )
    generic = {
        "market",
        "markets",
        "proxy",
        "proxies",
        "equities",
        "events",
        "event",
        "watch",
        "currently",
        "blocked",
        "available",
        "strategy",
        "family",
        "mapped",
        "universe",
        "paper",
        "paperable",
        "guarded",
        "route",
        "context",
        "research",
        "only",
    }
    return tokens - generic


def _pattern_market_tokens(pattern: dict[str, Any]) -> set[str]:
    tokens = _tokens(pattern.get("market_or_symbol"), pattern.get("market_affected"))
    source_family = str(pattern.get("source_or_family") or "")
    if source_family in {
        "crude_oil",
        "silver",
        "semiconductors",
        "defence",
        "defense",
        "prediction_markets",
        "macro_watchlist",
    }:
        tokens.update(_tokens(source_family))
    return tokens


def _pattern_tokens(pattern: dict[str, Any]) -> set[str]:
    return _tokens(
        pattern.get("source_or_family"),
        pattern.get("market_or_symbol"),
        pattern.get("relationship_type"),
        pattern.get("detected_signal"),
        pattern.get("market_affected"),
    )


def _is_broad_pattern(pattern: dict[str, Any]) -> bool:
    return str(pattern.get("source_or_family") or "") in {"all_sources", "all_markets"} or str(
        pattern.get("market_or_symbol") or ""
    ) in {"all_sources", "all_markets"}


def _matching_patterns(strategy: dict[str, Any], patterns: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    market_tokens = _strategy_market_tokens(strategy)
    direct: list[dict[str, Any]] = []
    broad: list[dict[str, Any]] = []
    for pattern in patterns:
        if _is_broad_pattern(pattern):
            broad.append(pattern)
            continue
        if market_tokens & _pattern_market_tokens(pattern):
            direct.append(pattern)
    direct.sort(key=lambda item: _safe_int(item.get("rank"), 999999))
    broad.sort(key=lambda item: _safe_int(item.get("rank"), 999999))
    return direct, broad


def _index_by_source_key(contracts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for contract in contracts:
        subject = _safe_dict(contract.get("subject"))
        source_key = str(subject.get("source_key") or contract.get("source_record_id") or "").lower()
        if source_key:
            indexed[source_key] = contract
    return indexed


def _index_price_by_symbol(contracts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for contract in contracts:
        subject = _safe_dict(contract.get("subject"))
        symbol = str(subject.get("symbol") or contract.get("source_record_id") or "").upper()
        if symbol:
            indexed[symbol] = contract
    return indexed


def _baseline_by_strategy(baseline_map: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(record.get("strategy_family_id")): record
        for record in _safe_list(baseline_map.get("records"))
        if record.get("strategy_family_id")
    }


def _strategy_contract_by_id(contracts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed = {}
    for contract in contracts:
        subject = _safe_dict(contract.get("subject"))
        family_id = subject.get("strategy_family_id")
        if family_id:
            indexed[str(family_id)] = contract
    return indexed


def _hypothesis_strategy_lookup(
    strategies: list[dict[str, Any]],
    hypothesis_contracts: list[dict[str, Any]],
) -> dict[str, str]:
    lookup: dict[str, str] = {}
    strategy_labels = [
        (str(strategy.get("strategy_family_id")), _tokens(strategy.get("label"), strategy.get("strategy_family_id")))
        for strategy in strategies
    ]
    for contract in hypothesis_contracts:
        subject = _safe_dict(contract.get("subject"))
        hypothesis_id = str(subject.get("strategy_hypothesis_id") or "")
        name_tokens = _tokens(subject.get("name"), subject.get("primary_instrument"), subject.get("paperable_execution_expression"))
        best_family = None
        best_overlap = 0
        for family_id, tokens in strategy_labels:
            overlap = len(tokens & name_tokens)
            if overlap > best_overlap:
                best_overlap = overlap
                best_family = family_id
        if hypothesis_id and best_family and best_overlap:
            lookup[hypothesis_id] = best_family
    return lookup


def _akber_contracts_by_strategy(
    strategies: list[dict[str, Any]],
    akber_contracts: list[dict[str, Any]],
    hypothesis_contracts: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    hypothesis_to_strategy = _hypothesis_strategy_lookup(strategies, hypothesis_contracts)
    by_strategy: dict[str, list[dict[str, Any]]] = {str(strategy.get("strategy_family_id")): [] for strategy in strategies}
    for contract in akber_contracts:
        subject = _safe_dict(contract.get("subject"))
        hypothesis_id = str(subject.get("strategy_hypothesis_id") or "")
        family_id = hypothesis_to_strategy.get(hypothesis_id)
        if family_id:
            by_strategy.setdefault(family_id, []).append(contract)
    return by_strategy


def _source_contribution(strategy: dict[str, Any], source_index: dict[str, dict[str, Any]], patterns: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    source_keywords = [str(item).lower() for item in _safe_list(strategy.get("source_keywords"))]
    pattern_sources = Counter(str(pattern.get("source_or_family") or "unknown") for pattern in patterns)
    for keyword in source_keywords:
        contract = source_index.get(keyword, {})
        subject = _safe_dict(contract.get("subject"))
        trust_score = _safe_float(subject.get("trust_score"), 0.0)
        freshness_status = str(subject.get("freshness_status") or "missing")
        evidence_state = str(contract.get("evidence_state") or "missing_contract")
        pattern_support_count = pattern_sources.get(keyword, 0) + pattern_sources.get(subject.get("source_family"), 0)
        freshness_multiplier = 1.0 if freshness_status in {"fresh", "recent"} else 0.45
        missing_penalty = 0.25 * _safe_int(contract.get("missing_evidence_count"))
        contribution_score = max(0.0, min(1.0, trust_score * freshness_multiplier + 0.08 * pattern_support_count - missing_penalty))
        rows.append(
            {
                "source_key": keyword,
                "contract_id": contract.get("contract_id"),
                "evidence_state": evidence_state,
                "source_family": subject.get("source_family"),
                "freshness_status": freshness_status,
                "trust_score": round(trust_score, 4),
                "pattern_support_count": pattern_support_count,
                "missing_evidence_count": _safe_int(contract.get("missing_evidence_count")),
                "contribution_score": round(contribution_score, 4),
            }
        )
    average_score = mean([row["contribution_score"] for row in rows]) if rows else 0.0
    stale_or_missing_count = sum(1 for row in rows if row["freshness_status"] not in {"fresh", "recent"} or row["evidence_state"] == "missing_contract")
    return {
        "rows": rows,
        "source_count": len(rows),
        "average_contribution_score": round(average_score, 4),
        "stale_or_missing_source_count": stale_or_missing_count,
        "strongest_sources": sorted(rows, key=lambda item: item["contribution_score"], reverse=True)[:4],
    }


def _instrument_contribution(strategy: dict[str, Any], price_index: dict[str, dict[str, Any]], patterns: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    pattern_markets = Counter(str(pattern.get("market_or_symbol") or "unknown").upper() for pattern in patterns)
    pattern_families = Counter(str(pattern.get("market_or_symbol") or "unknown").lower() for pattern in patterns)
    for market in _safe_list(strategy.get("watched_markets")):
        symbol = str(market.get("symbol") or "").upper()
        contract = price_index.get(symbol, {})
        subject = _safe_dict(contract.get("subject"))
        metrics = _safe_dict(contract.get("metrics"))
        market_family = str(subject.get("market_family") or market.get("market_family") or "").lower()
        pattern_support_count = pattern_markets.get(symbol, 0) + pattern_families.get(market_family, 0)
        paper_route_available = subject.get("paper_route_available")
        if paper_route_available is None:
            paper_route_available = "alpaca_paper_proxy_available" in str(market.get("paperability_state") or "")
        has_price = metrics.get("price_or_odds_value") is not None
        contribution_score = 0.15
        contribution_score += 0.2 if paper_route_available else 0.0
        contribution_score += 0.25 if has_price else 0.0
        contribution_score += min(pattern_support_count * 0.2, 0.4)
        contribution_score -= 0.08 * _safe_int(contract.get("missing_evidence_count"))
        rows.append(
            {
                "symbol": symbol,
                "market_family": market_family,
                "contract_id": contract.get("contract_id"),
                "evidence_state": contract.get("evidence_state", "missing_contract"),
                "paper_route_available": bool(paper_route_available),
                "paperability_state": subject.get("paperability_state") or market.get("paperability_state"),
                "price_data_state": subject.get("price_data_state"),
                "volatility_context": "available" if metrics.get("rolling_volatility_20d") is not None else "missing",
                "pattern_support_count": pattern_support_count,
                "missing_evidence_count": _safe_int(contract.get("missing_evidence_count")),
                "contribution_score": round(max(0.0, min(1.0, contribution_score)), 4),
            }
        )
    average_score = mean([row["contribution_score"] for row in rows]) if rows else 0.0
    return {
        "rows": rows,
        "instrument_count": len(rows),
        "paper_route_available_count": sum(1 for row in rows if row["paper_route_available"]),
        "price_gap_count": sum(1 for row in rows if row["price_data_state"] in {None, "price_history_gap_explicit"}),
        "average_contribution_score": round(average_score, 4),
        "strongest_instruments": sorted(rows, key=lambda item: item["contribution_score"], reverse=True)[:5],
    }


def _expectancy_profile(strategy_baseline: dict[str, Any], patterns: list[dict[str, Any]]) -> dict[str, Any]:
    pattern_expectancies = [
        _safe_float(pattern.get("linear_tests", {}).get("expectancy"))
        for pattern in patterns
        if pattern.get("linear_tests", {}).get("expectancy") is not None
    ]
    pattern_sample_counts = [
        _safe_int(pattern.get("linear_tests", {}).get("sample_count"))
        for pattern in patterns
        if pattern.get("linear_tests", {}).get("sample_count") is not None
    ]
    weighted_expectancy = None
    if pattern_expectancies and sum(pattern_sample_counts) > 0:
        weighted_expectancy = sum(
            expectancy * sample for expectancy, sample in zip(pattern_expectancies, pattern_sample_counts, strict=False)
        ) / sum(pattern_sample_counts)
    baseline_expectancy = strategy_baseline.get("expectancy")
    effective_expectancy = weighted_expectancy if weighted_expectancy is not None else baseline_expectancy
    return {
        "baseline_expectancy": baseline_expectancy,
        "pattern_weighted_expectancy": round(weighted_expectancy, 8) if weighted_expectancy is not None else None,
        "effective_expectancy": round(_safe_float(effective_expectancy), 8) if effective_expectancy is not None else None,
        "supporting_pattern_count": len(patterns),
        "total_pattern_sample_count": sum(pattern_sample_counts),
        "expectancy_state": "measured_from_pattern_engine_v2" if pattern_expectancies else "not_measured_for_strategy",
    }


def _drawdown_profile(strategy_baseline: dict[str, Any], patterns: list[dict[str, Any]]) -> dict[str, Any]:
    drawdowns = [
        _safe_float(pattern.get("linear_tests", {}).get("drawdown_proxy"))
        for pattern in patterns
        if pattern.get("linear_tests", {}).get("drawdown_proxy") is not None
    ]
    baseline_drawdown = strategy_baseline.get("drawdown_proxy")
    max_drawdown = max(drawdowns) if drawdowns else baseline_drawdown
    return {
        "baseline_drawdown_proxy": baseline_drawdown,
        "max_pattern_drawdown_proxy": round(max_drawdown, 8) if max_drawdown is not None else None,
        "average_pattern_drawdown_proxy": round(mean(drawdowns), 8) if drawdowns else None,
        "drawdown_state": "measured_from_pattern_engine_v2" if drawdowns else "not_measured_for_strategy",
        "drawdown_limit": "requires_later_risk_model_before_paper_review",
    }


def _stale_data_sensitivity(
    source_contribution: dict[str, Any],
    instrument_contribution: dict[str, Any],
    strategy_contract: dict[str, Any],
) -> dict[str, Any]:
    source_stale = _safe_int(source_contribution.get("stale_or_missing_source_count"))
    price_gaps = _safe_int(instrument_contribution.get("price_gap_count"))
    strategy_missing = _safe_int(strategy_contract.get("missing_evidence_count"))
    total = source_stale + price_gaps + strategy_missing
    if total >= 6:
        sensitivity = "high"
    elif total >= 2:
        sensitivity = "medium"
    else:
        sensitivity = "low"
    return {
        "sensitivity": sensitivity,
        "stale_or_missing_source_count": source_stale,
        "price_gap_count": price_gaps,
        "strategy_missing_evidence_count": strategy_missing,
        "failure_if_stale": "strategy evidence must remain research-only or held if fresh source/price context is missing",
    }


def _akber_sensitivity(strategy_baseline: dict[str, Any], akber_contracts: list[dict[str, Any]]) -> dict[str, Any]:
    requirements = _safe_list(strategy_baseline.get("akber_confirmation_requirements")) or [
        "volatility_context",
        "technical_confirmation",
        "volume_or_flow_confirmation",
        "pricing_gap_evidence",
        "risk_reward_and_invalidation",
    ]
    scores: dict[str, list[float]] = {}
    missing_types: Counter[str] = Counter()
    for contract in akber_contracts:
        metrics = _safe_dict(contract.get("metrics"))
        for key, value in metrics.items():
            if key.endswith("_score") or key == "akber_filter_score":
                scores.setdefault(key, []).append(_safe_float(value))
        for missing in _safe_list(contract.get("missing_evidence")):
            missing_types[str(missing.get("missing_evidence_type") or "unknown")] += 1
    aggregate_scores = {key: round(mean(values), 4) for key, values in scores.items() if values}
    if not akber_contracts:
        state = "not_measured_for_strategy_yet"
    elif missing_types:
        state = "sensitive_to_missing_practical_confirmation"
    else:
        state = "akber_inputs_available_for_research_review"
    return {
        "state": state,
        "akber_contract_count": len(akber_contracts),
        "required_practical_inputs": requirements,
        "average_scores": aggregate_scores,
        "dominant_missing_inputs": dict(missing_types.most_common(6)),
        "akber_pass_is_not_execution_approval": True,
    }


def _quantum_nonlinear_usefulness(patterns: list[dict[str, Any]]) -> dict[str, Any]:
    verdicts = Counter(str(pattern.get("quantum_classical_review", {}).get("review_verdict") or "not_measured") for pattern in patterns)
    nonlinear_states = Counter(str(pattern.get("nonlinear_interaction_review", {}).get("review_state") or "not_measured") for pattern in patterns)
    entropy_labels = Counter(str(pattern.get("entropy_review", {}).get("ambiguity_label") or "not_measured") for pattern in patterns)
    useful_count = sum(verdicts.get(key, 0) for key in ("classical_research_upgrade", "classical_research_hold"))
    downgraded_count = sum(verdicts.get(key, 0) for key in ("downgrade_overfit", "hold_high_ambiguity", "hold_low_sample"))
    if useful_count and useful_count >= downgraded_count:
        usefulness = "useful_as_research_annotation"
    elif downgraded_count:
        usefulness = "mainly_useful_for_downgrading_noise"
    else:
        usefulness = "not_measured_for_strategy"
    return {
        "usefulness": usefulness,
        "quantum_hardware_used": False,
        "classical_fallback_used": True,
        "verdict_counts": dict(verdicts),
        "nonlinear_state_counts": dict(nonlinear_states),
        "entropy_label_counts": dict(entropy_labels),
        "cannot_create_trade_authority": True,
    }


def _paperability_limits(instrument_contribution: dict[str, Any]) -> dict[str, Any]:
    rows = _safe_list(instrument_contribution.get("rows"))
    context_only = [
        row["symbol"]
        for row in rows
        if "context_only" in str(row.get("paperability_state") or "")
        or "research_only" in str(row.get("paperability_state") or "")
    ]
    paperable = [row["symbol"] for row in rows if row.get("paper_route_available")]
    limits = []
    if context_only:
        limits.append("Some mapped instruments are context-only or research-only and cannot be directly paper traded.")
    if not paperable:
        limits.append("No guarded Alpaca Paper proxy is currently available for this strategy family.")
    if instrument_contribution.get("price_gap_count"):
        limits.append("Some instruments lack complete price history or volatility context.")
    return {
        "paperable_proxy_symbols": paperable,
        "context_or_research_only_symbols": context_only,
        "paperability_limit_count": len(limits),
        "limits": limits,
        "paper_order_allowed": False,
        "guarded_route_required_if_later_promoted": "Alpaca Paper route only after later phases pass",
    }


def _failure_modes(
    patterns: list[dict[str, Any]],
    source_contribution: dict[str, Any],
    instrument_contribution: dict[str, Any],
    akber_sensitivity: dict[str, Any],
    stale_data_sensitivity: dict[str, Any],
    baseline: dict[str, Any],
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    if not patterns:
        failures.append(
            {
                "failure_mode": "under_evidenced_strategy_family",
                "severity": "high",
                "reason": "No direct Pattern Engine V2 record currently supports this strategy family.",
            }
        )
    if stale_data_sensitivity.get("sensitivity") in {"medium", "high"}:
        failures.append(
            {
                "failure_mode": "stale_or_missing_data_sensitivity",
                "severity": stale_data_sensitivity.get("sensitivity"),
                "reason": "Source freshness, price history, or strategy evidence gaps can make the strategy look stronger than it is.",
            }
        )
    if akber_sensitivity.get("state") != "akber_inputs_available_for_research_review":
        failures.append(
            {
                "failure_mode": "akber_practical_confirmation_gap",
                "severity": "high",
                "reason": "Akber still needs practical trading context before this evidence could support paper review.",
            }
        )
    if instrument_contribution.get("paper_route_available_count", 0) == 0:
        failures.append(
            {
                "failure_mode": "paperability_gap",
                "severity": "high",
                "reason": "No mapped instrument currently has a guarded paper route available.",
            }
        )
    downgraded = [
        pattern
        for pattern in patterns
        if pattern.get("quantum_classical_review", {}).get("review_verdict") == "downgrade_overfit"
    ]
    if downgraded:
        failures.append(
            {
                "failure_mode": "overfit_or_low_sample_pattern_risk",
                "severity": "medium",
                "reason": f"{len(downgraded)} pattern records were downgraded by the nonlinear/classical review.",
            }
        )
    for assumption in _safe_list(baseline.get("unsupported_assumptions")):
        failures.append(
            {
                "failure_mode": "unsupported_baseline_assumption",
                "severity": "medium",
                "reason": assumption,
            }
        )
    return failures


def _confidence_class(
    patterns: list[dict[str, Any]],
    expectancy_profile: dict[str, Any],
    source_contribution: dict[str, Any],
    instrument_contribution: dict[str, Any],
    stale_data_sensitivity: dict[str, Any],
    akber_sensitivity: dict[str, Any],
) -> dict[str, Any]:
    ranked_count = sum(1 for pattern in patterns if pattern.get("lifecycle_state") == "ranked_research_pattern")
    held_count = sum(1 for pattern in patterns if pattern.get("lifecycle_state") == "held_for_more_evidence")
    sample_count = _safe_int(expectancy_profile.get("total_pattern_sample_count"))
    score = 0.0
    score += min(ranked_count, 4) * 0.15
    score += min(sample_count / 100, 0.25)
    score += min(_safe_float(source_contribution.get("average_contribution_score")), 1.0) * 0.15
    score += min(_safe_float(instrument_contribution.get("average_contribution_score")), 1.0) * 0.15
    if stale_data_sensitivity.get("sensitivity") == "low":
        score += 0.12
    elif stale_data_sensitivity.get("sensitivity") == "medium":
        score += 0.04
    if akber_sensitivity.get("state") == "akber_inputs_available_for_research_review":
        score += 0.08
    score -= held_count * 0.03
    score = round(max(0.0, min(1.0, score)), 4)
    if ranked_count and sample_count >= 40:
        label = "medium_research_confidence"
    elif patterns:
        label = "early_research_confidence"
    else:
        label = "under_evidenced"
    if stale_data_sensitivity.get("sensitivity") == "high" and label != "under_evidenced":
        label = "low_due_to_stale_data_sensitivity"
    return {
        "label": label,
        "confidence_score": score,
        "ranked_pattern_count": ranked_count,
        "held_pattern_count": held_count,
        "total_pattern_sample_count": sample_count,
        "dashboard_label": "evidence-backed" if patterns else "under-evidenced",
        "confidence_is_research_only": True,
    }


def _strategy_record(
    strategy: dict[str, Any],
    context: dict[str, Any],
    source_index: dict[str, dict[str, Any]],
    price_index: dict[str, dict[str, Any]],
    baseline_by_id: dict[str, dict[str, Any]],
    strategy_contracts_by_id: dict[str, dict[str, Any]],
    akber_by_strategy: dict[str, list[dict[str, Any]]],
    generated_at: str,
) -> dict[str, Any]:
    strategy_family_id = str(strategy.get("strategy_family_id"))
    direct_patterns, broad_patterns = _matching_patterns(strategy, context["pattern_records"])
    baseline = baseline_by_id.get(strategy_family_id, {})
    strategy_contract = strategy_contracts_by_id.get(strategy_family_id, {})
    source_contribution = _source_contribution(strategy, source_index, direct_patterns)
    instrument_contribution = _instrument_contribution(strategy, price_index, direct_patterns)
    expectancy_profile = _expectancy_profile(baseline, direct_patterns)
    drawdown_profile = _drawdown_profile(baseline, direct_patterns)
    stale_data_sensitivity = _stale_data_sensitivity(source_contribution, instrument_contribution, strategy_contract)
    akber_sensitivity = _akber_sensitivity(baseline, akber_by_strategy.get(strategy_family_id, []))
    quantum_nonlinear_usefulness = _quantum_nonlinear_usefulness(direct_patterns)
    paperability_limits = _paperability_limits(instrument_contribution)
    failure_modes = _failure_modes(
        direct_patterns,
        source_contribution,
        instrument_contribution,
        akber_sensitivity,
        stale_data_sensitivity,
        baseline,
    )
    confidence_class = _confidence_class(
        direct_patterns,
        expectancy_profile,
        source_contribution,
        instrument_contribution,
        stale_data_sensitivity,
        akber_sensitivity,
    )
    evidence_state = (
        "evidence_backed_research_map"
        if direct_patterns and confidence_class["label"] != "under_evidenced"
        else "under_evidenced_research_map"
    )
    record = {
        "schema_version": SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "strategy_evidence_map_id": _hash_id("qadam-strategy-evidence-map", [strategy_family_id, generated_at[:10]]),
        "strategy_family_id": strategy_family_id,
        "label": strategy.get("label"),
        "current_state": strategy.get("current_state"),
        "currently_in_play": bool(strategy.get("currently_in_play")),
        "evidence_state": evidence_state,
        "supporting_pattern_ids": [pattern.get("pattern_id") for pattern in direct_patterns],
        "supporting_pattern_count": len(direct_patterns),
        "broad_context_pattern_count": len(broad_patterns),
        "baseline_strategy_contract_id": strategy_contract.get("contract_id"),
        "baseline_strategy_evidence_state": baseline.get("strategy_evidence_state"),
        "source_contribution": source_contribution,
        "instrument_contribution": instrument_contribution,
        "expectancy_profile": expectancy_profile,
        "drawdown_profile": drawdown_profile,
        "failure_modes": failure_modes,
        "stale_data_sensitivity": stale_data_sensitivity,
        "akber_sensitivity": akber_sensitivity,
        "quantum_nonlinear_usefulness": quantum_nonlinear_usefulness,
        "paperability_limits": paperability_limits,
        "confidence_class": confidence_class,
        "dashboard_card_status": confidence_class["dashboard_label"],
        "what_this_means": (
            f"{strategy.get('label')} has direct research evidence from Pattern Engine V2."
            if direct_patterns
            else f"{strategy.get('label')} is mapped, but currently under-evidenced by local source-price history."
        ),
        "next_allowed_action": "Use as input for Phase 6 Strategy Foundry V2; do not create trades from this map.",
        "research_only": True,
        "strategy_hypothesis_creation_allowed": False,
        "strategy_hypothesis_created": False,
        "trade_candidate_creation_allowed": False,
        "trade_candidate_created": False,
        "paper_order_allowed": False,
        "paper_order_created": False,
        "broker_write_allowed": False,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
        "authority": _authority(),
        "generated_at": generated_at,
    }
    return record


def _rejection_for_missing_strategy(strategy: dict[str, Any], generated_at: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "rejection_id": _hash_id("qadam-strategy-evidence-map-reject", [strategy.get("strategy_family_id"), "missing_id"]),
        "strategy_family_id": strategy.get("strategy_family_id"),
        "label": strategy.get("label"),
        "rejection_reason": "strategy_family_id_missing",
        "research_only": True,
        "strategy_hypothesis_creation_allowed": False,
        "trade_candidate_creation_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
        "authority": _authority(),
        "generated_at": generated_at,
    }


def _dashboard_summary(primary: dict[str, Any], records: list[dict[str, Any]], rejections: list[dict[str, Any]], generated_at: str) -> dict[str, Any]:
    confidence_counts = Counter(str(record.get("confidence_class", {}).get("label") or "unknown") for record in records)
    evidence_backed = [record for record in records if record.get("evidence_state") == "evidence_backed_research_map"]
    under_evidenced = [record for record in records if record.get("evidence_state") == "under_evidenced_research_map"]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_strategy_evidence_map_dashboard_summary",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": primary.get("status"),
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "proposal_first": True,
        "research_only": True,
        "strategy_count": len(records),
        "evidence_backed_strategy_count": len(evidence_backed),
        "under_evidenced_strategy_count": len(under_evidenced),
        "rejection_count": len(rejections),
        "confidence_counts": dict(confidence_counts),
        "cards": [
            {
                "strategy_family_id": record.get("strategy_family_id"),
                "label": record.get("label"),
                "evidence_state": record.get("evidence_state"),
                "confidence_class": record.get("confidence_class", {}).get("label"),
                "supporting_pattern_count": record.get("supporting_pattern_count"),
                "effective_expectancy": record.get("expectancy_profile", {}).get("effective_expectancy"),
                "stale_data_sensitivity": record.get("stale_data_sensitivity", {}).get("sensitivity"),
                "akber_state": record.get("akber_sensitivity", {}).get("state"),
                "paperable_proxy_symbols": record.get("paperability_limits", {}).get("paperable_proxy_symbols"),
                "what_this_means": record.get("what_this_means"),
            }
            for record in records
        ],
        "message": (
            "Strategy Evidence Map backs each core strategy with evidence or marks it under-evidenced. "
            "It does not create strategy hypotheses, trade candidates, approvals, paper orders, or proof credit."
        ),
        "next_allowed_action": "Use evidence-backed or under-evidenced labels as input for Phase 6 Strategy Foundry V2.",
        "strategy_hypothesis_creation_allowed": False,
        "trade_candidate_creation_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
        "authority": _authority(),
        "artifact_refs": {
            "primary": PRIMARY_ARTIFACT,
            "records": RECORDS_ARTIFACT,
            "rejections": REJECTIONS_ARTIFACT,
        },
    }


def build_strategy_evidence_map(settings: Settings | None = None) -> StrategyEvidenceBundle:
    generated_at = _iso()
    context = _load_context(settings)
    strategies = _safe_list(context.get("strategy_universe", {}).get("all_strategy_rows"))
    source_index = _index_by_source_key(context["source_contracts"])
    price_index = _index_price_by_symbol(context["price_contracts"])
    baseline_by_id = _baseline_by_strategy(context["baseline_strategy_map"])
    strategy_contracts_by_id = _strategy_contract_by_id(context["strategy_contracts"])
    akber_by_strategy = _akber_contracts_by_strategy(
        strategies,
        context["akber_contracts"],
        context["hypothesis_contracts"],
    )
    records: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []
    for strategy in strategies:
        if not strategy.get("strategy_family_id"):
            rejections.append(_rejection_for_missing_strategy(strategy, generated_at))
            continue
        records.append(
            _strategy_record(
                strategy,
                context,
                source_index,
                price_index,
                baseline_by_id,
                strategy_contracts_by_id,
                akber_by_strategy,
                generated_at,
            )
        )
    evidence_backed_count = sum(1 for record in records if record.get("evidence_state") == "evidence_backed_research_map")
    under_evidenced_count = sum(1 for record in records if record.get("evidence_state") == "under_evidenced_research_map")
    status = "strategy_evidence_map_ready" if records else "strategy_evidence_map_blocked_no_strategy_universe"
    primary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_strategy_evidence_map",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": status,
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "proposal_first": True,
        "research_only": True,
        "strategy_count": len(records),
        "evidence_backed_strategy_count": evidence_backed_count,
        "under_evidenced_strategy_count": under_evidenced_count,
        "rejection_count": len(rejections),
        "all_strategy_cards_backed_or_labeled": len(records) == len(strategies),
        "pattern_engine_v2_state": context.get("pattern_engine_v2", {}).get("status"),
        "input_artifacts": {
            "strategy_universe": STRATEGY_UNIVERSE_ARTIFACT,
            "pattern_engine_v2": PATTERN_ENGINE_V2_ARTIFACT,
            "pattern_engine_v2_records": PATTERN_ENGINE_V2_RECORDS_ARTIFACT,
            "source_evidence_contracts": SOURCE_EVIDENCE_CONTRACTS_ARTIFACT,
            "price_evidence_contracts": PRICE_EVIDENCE_CONTRACTS_ARTIFACT,
            "strategy_evidence_contracts": STRATEGY_EVIDENCE_CONTRACTS_ARTIFACT,
            "akber_evidence_contracts": AKBER_EVIDENCE_CONTRACTS_ARTIFACT,
        },
        "strategy_hypothesis_creation_allowed": False,
        "strategy_hypothesis_created": False,
        "trade_candidate_creation_allowed": False,
        "trade_candidate_created": False,
        "paper_order_allowed": False,
        "paper_order_created": False,
        "broker_write_allowed": False,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
        "paper_growth_trial_calendar_advanced": False,
        "simulated_elapsed_time_allowed": False,
        "authority": _authority(),
        "artifact_refs": {
            "records": RECORDS_ARTIFACT,
            "rejections": REJECTIONS_ARTIFACT,
            "dashboard_summary": DASHBOARD_SUMMARY_ARTIFACT,
        },
    }
    dashboard_summary = _dashboard_summary(primary, records, rejections, generated_at)
    return StrategyEvidenceBundle(
        primary=primary,
        records=records,
        rejections=rejections,
        dashboard_summary=dashboard_summary,
    )


def write_strategy_evidence_map(bundle: StrategyEvidenceBundle, settings: Settings | None = None) -> dict[str, str]:
    runtime = _runtime_dir(settings)
    paths = {
        "primary": runtime / PRIMARY_ARTIFACT,
        "records": runtime / RECORDS_ARTIFACT,
        "rejections": runtime / REJECTIONS_ARTIFACT,
        "dashboard_summary": runtime / DASHBOARD_SUMMARY_ARTIFACT,
        "events": runtime / EVENTS_ARTIFACT,
    }
    _write_json(paths["primary"], bundle.primary)
    _write_jsonl(paths["records"], bundle.records)
    _write_jsonl(paths["rejections"], bundle.rejections)
    _write_json(paths["dashboard_summary"], bundle.dashboard_summary)
    _append_jsonl(
        paths["events"],
        {
            "schema_version": SCHEMA_VERSION,
            "phase_id": PHASE_ID,
            "event_type": "strategy_evidence_map_written",
            "generated_at": bundle.primary.get("generated_at"),
            "status": bundle.primary.get("status"),
            "strategy_count": len(bundle.records),
            "evidence_backed_strategy_count": bundle.primary.get("evidence_backed_strategy_count"),
            "under_evidenced_strategy_count": bundle.primary.get("under_evidenced_strategy_count"),
            "strategy_hypothesis_created": False,
            "trade_candidate_created": False,
            "paper_order_created": False,
            "broker_write_count": 0,
            "live_capital_enabled": False,
            "proof_credit_allowed": False,
            "authority": _authority(),
        },
    )
    return {key: str(path) for key, path in paths.items()}


def build_and_write_strategy_evidence_map(settings: Settings | None = None) -> tuple[StrategyEvidenceBundle, dict[str, str]]:
    bundle = build_strategy_evidence_map(settings)
    written = write_strategy_evidence_map(bundle, settings)
    return bundle, written


def _validate_authority(payload: dict[str, Any], prefix: str) -> list[str]:
    errors: list[str] = []
    authority = _safe_dict(payload.get("authority"))
    for key, expected in AUTHORITY_FLAGS.items():
        if authority.get(key) != expected:
            errors.append(f"{prefix}_{key}_authority_invalid")
    for field in FORBIDDEN_TRUE_FIELDS:
        if payload.get(field) is True:
            errors.append(f"{prefix}_{field}_must_not_be_true")
    for field in FORBIDDEN_NONZERO_FIELDS:
        if _safe_int(payload.get(field), 0) != 0:
            errors.append(f"{prefix}_{field}_must_be_zero")
    return errors


def validate_strategy_evidence_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("schema_version") != SCHEMA_VERSION:
        errors.append("record_schema_version_invalid")
    if record.get("phase_id") != PHASE_ID:
        errors.append("record_phase_id_invalid")
    if not record.get("strategy_family_id"):
        errors.append("record_strategy_family_id_missing")
    if record.get("research_only") is not True:
        errors.append("record_research_only_must_be_true")
    if record.get("evidence_state") not in {"evidence_backed_research_map", "under_evidenced_research_map"}:
        errors.append("record_evidence_state_invalid")
    for section in REQUIRED_RECORD_SECTIONS:
        if section not in record:
            errors.append(f"record_{section}_missing")
    if record.get("dashboard_card_status") not in {"evidence-backed", "under-evidenced"}:
        errors.append("record_dashboard_card_status_invalid")
    if not record.get("failure_modes"):
        errors.append("record_failure_modes_missing")
    errors.extend(_validate_authority(record, "record"))
    return errors


def validate_strategy_evidence_rejection(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("schema_version") != SCHEMA_VERSION:
        errors.append("rejection_schema_version_invalid")
    if record.get("phase_id") != PHASE_ID:
        errors.append("rejection_phase_id_invalid")
    if not record.get("rejection_reason"):
        errors.append("rejection_reason_missing")
    errors.extend(_validate_authority(record, "rejection"))
    return errors


def validate_strategy_evidence_map_bundle(bundle: StrategyEvidenceBundle | dict[str, Any]) -> list[str]:
    if isinstance(bundle, StrategyEvidenceBundle):
        primary = bundle.primary
        records = bundle.records
        rejections = bundle.rejections
        dashboard_summary = bundle.dashboard_summary
    else:
        primary = _safe_dict(bundle.get("primary"))
        records = _safe_list(bundle.get("records"))
        rejections = _safe_list(bundle.get("rejections"))
        dashboard_summary = _safe_dict(bundle.get("dashboard_summary"))
    errors: list[str] = []
    if primary.get("schema_version") != SCHEMA_VERSION:
        errors.append("primary_schema_version_invalid")
    if primary.get("phase_id") != PHASE_ID:
        errors.append("primary_phase_id_invalid")
    if primary.get("artifact_type") != "qadam_strategy_evidence_map":
        errors.append("primary_artifact_type_invalid")
    if primary.get("status") != "strategy_evidence_map_ready":
        errors.append("primary_status_not_ready")
    for key in ("public_safe", "read_only", "paper_only", "proposal_first", "research_only"):
        if primary.get(key) is not True:
            errors.append(f"primary_{key}_must_be_true")
    errors.extend(_validate_authority(primary, "primary"))
    if not records:
        errors.append("records_missing")
    family_ids = [record.get("strategy_family_id") for record in records]
    if len(family_ids) != len(set(family_ids)):
        errors.append("duplicate_strategy_family_records")
    if primary.get("strategy_count") != len(records):
        errors.append("primary_strategy_count_mismatch")
    if primary.get("all_strategy_cards_backed_or_labeled") is not True:
        errors.append("not_all_strategy_cards_backed_or_labeled")
    for index, record in enumerate(records, start=1):
        for error in validate_strategy_evidence_record(record):
            errors.append(f"record_{index}_{error}")
    for index, record in enumerate(rejections[:200], start=1):
        for error in validate_strategy_evidence_rejection(record):
            errors.append(f"rejection_{index}_{error}")
    if dashboard_summary.get("artifact_type") != "qadam_strategy_evidence_map_dashboard_summary":
        errors.append("dashboard_summary_artifact_type_invalid")
    if dashboard_summary.get("strategy_count") != len(records):
        errors.append("dashboard_summary_strategy_count_mismatch")
    if dashboard_summary.get("research_only") is not True:
        errors.append("dashboard_summary_research_only_must_be_true")
    if dashboard_summary.get("strategy_hypothesis_creation_allowed") is not False:
        errors.append("dashboard_summary_strategy_hypothesis_creation_allowed_must_be_false")
    if dashboard_summary.get("trade_candidate_creation_allowed") is not False:
        errors.append("dashboard_summary_trade_candidate_creation_allowed_must_be_false")
    if dashboard_summary.get("paper_order_allowed") is not False:
        errors.append("dashboard_summary_paper_order_allowed_must_be_false")
    return errors


def validate_negative_strategy_evidence_map_probes(settings: Settings | None = None) -> list[str]:
    bundle = build_strategy_evidence_map(settings)
    if not bundle.records:
        return ["negative_probe_skipped_missing_strategy_records"]
    errors: list[str] = []
    unsafe_record = json.loads(json.dumps(bundle.records[0]))
    unsafe_record["trade_candidate_created"] = True
    unsafe_record["authority"]["trade_candidate_created"] = True
    if not validate_strategy_evidence_record(unsafe_record):
        errors.append("negative_probe_failed_for_trade_candidate_boundary")

    unsafe_hypothesis_record = json.loads(json.dumps(bundle.records[0]))
    unsafe_hypothesis_record["strategy_hypothesis_created"] = True
    unsafe_hypothesis_record["authority"]["strategy_hypothesis_created"] = True
    if not validate_strategy_evidence_record(unsafe_hypothesis_record):
        errors.append("negative_probe_failed_for_strategy_hypothesis_boundary")

    missing_section_record = json.loads(json.dumps(bundle.records[0]))
    missing_section_record.pop("akber_sensitivity", None)
    if not validate_strategy_evidence_record(missing_section_record):
        errors.append("negative_probe_failed_for_missing_required_section")

    duplicate_payload = {
        "primary": bundle.primary,
        "records": bundle.records + [json.loads(json.dumps(bundle.records[0]))],
        "rejections": bundle.rejections,
        "dashboard_summary": bundle.dashboard_summary,
    }
    if "duplicate_strategy_family_records" not in validate_strategy_evidence_map_bundle(duplicate_payload):
        errors.append("negative_probe_failed_for_duplicate_strategy_family")
    return errors


def load_strategy_evidence_map(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "primary": _read_json(runtime / PRIMARY_ARTIFACT),
        "records": _read_jsonl(runtime / RECORDS_ARTIFACT),
        "rejections": _read_jsonl(runtime / REJECTIONS_ARTIFACT),
        "dashboard_summary": _read_json(runtime / DASHBOARD_SUMMARY_ARTIFACT),
    }
