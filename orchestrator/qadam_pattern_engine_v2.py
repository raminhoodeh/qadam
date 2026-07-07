"""Pattern Engine V2 for Qadam next-generation flow Phase 4.

This module converts baseline source-price evidence into ranked research
patterns. It is deliberately non-executable from a trading perspective:
patterns can inform later strategy evidence, but they cannot create trade
candidates, approvals, orders, broker writes, proof credit, or live authority.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from orchestrator.config import Settings

SCHEMA_VERSION = "qadam_pattern_engine_v2.v1"
PHASE_ID = "qadam_next_generation_phase_4_pattern_engine_v2"

PRIMARY_ARTIFACT = "qadam_pattern_engine_v2.json"
PATTERN_RECORDS_ARTIFACT = "qadam_pattern_engine_v2_records.jsonl"
REJECTIONS_ARTIFACT = "qadam_pattern_engine_v2_rejections.jsonl"
DASHBOARD_SUMMARY_ARTIFACT = "qadam_pattern_engine_v2_dashboard_summary.json"
EVENTS_ARTIFACT = "qadam_pattern_engine_v2_events.jsonl"

BASELINE_RESULTS_ARTIFACT = "qsase_baseline_backtest_results.jsonl"
BASELINE_REJECTIONS_ARTIFACT = "qsase_baseline_backtest_rejections.jsonl"
SOURCE_PRICE_CONTRACTS_ARTIFACT = "qadam_source_price_relationship_evidence_contracts.jsonl"
EVIDENCE_CONTRACTS_SUMMARY_ARTIFACT = "qadam_evidence_contracts_summary.json"
WORLD_MODEL_HYPOTHESES_ARTIFACT = "qadam_world_model_hypotheses.jsonl"
WORLD_MODEL_RESEARCH_QUESTIONS_ARTIFACT = "qadam_world_model_research_questions.jsonl"
WORLD_MODEL_MARKET_MAPPINGS_ARTIFACT = "qadam_world_model_market_mappings.jsonl"
WHOLE_UNIVERSE_BACKFILL_BACKTEST_SUMMARY_ARTIFACT = "qsase_whole_universe_backfill_backtest_dashboard_summary.json"

REQUIRED_METHOD_BLOCKS = (
    "linear_tests",
    "vector_analog_retrieval",
    "state_matrix_probability",
    "nonlinear_interaction_review",
    "entropy_review",
    "quantum_classical_review",
)

ALLOWED_LIFECYCLE_STATES = {
    "ranked_research_pattern",
    "held_for_more_evidence",
    "rejected_low_sample",
    "rejected_duplicate",
    "rejected_non_research_authority",
}

AUTHORITY_FLAGS = {
    "read_only": True,
    "paper_only": True,
    "proposal_first": True,
    "research_only": True,
    "pattern_research_only": True,
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

MIN_RANKED_SAMPLE_COUNT = 10
MAX_ACCEPTED_PATTERNS = 24


@dataclass(frozen=True)
class PatternEngineBundle:
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


def _hash_id(prefix: str, parts: list[Any]) -> str:
    payload = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]
    return f"{prefix}:{digest}"


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


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _authority() -> dict[str, Any]:
    return dict(AUTHORITY_FLAGS)


def _load_context(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "runtime_dir": runtime,
        "baseline_results": _read_jsonl(runtime / BASELINE_RESULTS_ARTIFACT),
        "baseline_rejections": _read_jsonl(runtime / BASELINE_REJECTIONS_ARTIFACT),
        "source_price_contracts": _read_jsonl(runtime / SOURCE_PRICE_CONTRACTS_ARTIFACT),
        "evidence_contracts_summary": _read_json(runtime / EVIDENCE_CONTRACTS_SUMMARY_ARTIFACT),
        "world_model_hypotheses": _read_jsonl(runtime / WORLD_MODEL_HYPOTHESES_ARTIFACT),
        "world_model_research_questions": _read_jsonl(runtime / WORLD_MODEL_RESEARCH_QUESTIONS_ARTIFACT),
        "world_model_market_mappings": _read_jsonl(runtime / WORLD_MODEL_MARKET_MAPPINGS_ARTIFACT),
        "whole_universe_backfill_backtest_summary": _read_json(
            runtime / WHOLE_UNIVERSE_BACKFILL_BACKTEST_SUMMARY_ARTIFACT
        ),
    }


def _contract_index(contracts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for contract in contracts:
        source_record_id = str(contract.get("source_record_id") or "")
        if source_record_id:
            indexed[source_record_id] = contract
    return indexed


def _world_questions_by_market(questions: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_market: dict[str, list[dict[str, Any]]] = {}
    for question in questions:
        market = str(question.get("affected_market") or "").lower()
        if market:
            by_market.setdefault(market, []).append(question)
    return by_market


def _market_aliases(value: str) -> set[str]:
    normalized = value.lower().replace("-", "_").replace(" ", "_")
    aliases = {normalized}
    if normalized in {"cl=f", "uso", "xle", "bno", "crude_oil", "energy"}:
        aliases.update({"crude_oil", "energy", "energy_security"})
    if normalized in {"slv", "si=f", "sil", "gld", "silver", "macro_liquidity"}:
        aliases.update({"silver", "macro_watchlist", "liquidity"})
    if normalized in {"smh", "soxx", "nvda", "qqq", "semiconductors"}:
        aliases.update({"semiconductors", "technology_policy"})
    if normalized in {"ita", "xar", "lmt", "ppa", "defence", "defense"}:
        aliases.update({"defence", "defense", "geopolitical_security"})
    if "kalshi" in normalized or "polymarket" in normalized or "prediction" in normalized:
        aliases.update({"prediction_markets", "event_contracts"})
    return aliases


def _matching_world_questions(
    record: dict[str, Any],
    questions_by_market: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    markets = _market_aliases(str(record.get("market_or_symbol") or ""))
    markets.update(_market_aliases(str(record.get("source_or_family") or "")))
    matches: list[dict[str, Any]] = []
    for market in markets:
        matches.extend(questions_by_market.get(market, []))
    deduped: dict[str, dict[str, Any]] = {}
    for question in matches:
        question_id = str(question.get("research_question_id") or "")
        if question_id:
            deduped[question_id] = question
    return list(deduped.values())[:5]


def _binary_entropy(probability: float) -> float:
    p = min(1.0, max(0.0, probability))
    if p in {0.0, 1.0}:
        return 0.0
    return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))


def _entropy_label(entropy: float) -> str:
    if entropy < 0.35:
        return "low_ambiguity"
    if entropy < 0.75:
        return "medium_ambiguity"
    return "high_ambiguity"


def _confidence_bucket(sample_count: int, hit_rate: float, overfit_warning: bool) -> str:
    if overfit_warning:
        return "low_overfit_risk_flagged"
    if sample_count >= 30 and (hit_rate >= 0.58 or hit_rate <= 0.42):
        return "medium_research_confidence"
    if sample_count >= MIN_RANKED_SAMPLE_COUNT:
        return "early_research_confidence"
    return "insufficient_sample"


def _relationship_signature(record: dict[str, Any]) -> str:
    return "|".join(
        [
            str(record.get("relationship_type") or "unknown"),
            str(record.get("source_or_family") or "unknown"),
            str(record.get("market_or_symbol") or "unknown"),
            str(record.get("time_window") or "unknown"),
        ]
    ).lower()


def _direction_label(expectancy: float) -> str:
    if expectancy > 0:
        return "positive_forward_bias"
    if expectancy < 0:
        return "negative_forward_bias"
    return "flat_or_unmeasured_forward_bias"


def _linear_tests(record: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    metrics = _safe_dict(contract.get("metrics"))
    sample_count = _safe_int(record.get("sample_count") or metrics.get("sample_count"))
    hit_rate = _safe_float(record.get("hit_rate") if record.get("hit_rate") is not None else metrics.get("hit_rate"))
    expectancy = _safe_float(
        record.get("expectancy") if record.get("expectancy") is not None else metrics.get("expectancy")
    )
    false_positive_rate = _safe_float(
        record.get("false_positive_rate")
        if record.get("false_positive_rate") is not None
        else metrics.get("false_positive_rate")
    )
    average_forward_return = _safe_float(
        record.get("average_forward_return")
        if record.get("average_forward_return") is not None
        else metrics.get("average_forward_return")
    )
    drawdown_proxy = _safe_float(
        record.get("drawdown_proxy") if record.get("drawdown_proxy") is not None else metrics.get("drawdown_proxy")
    )
    return {
        "test_role": "transparent_linear_relationship_test",
        "sample_count": sample_count,
        "minimum_sample_count": MIN_RANKED_SAMPLE_COUNT,
        "hit_rate": round(hit_rate, 6),
        "expectancy": round(expectancy, 8),
        "average_forward_return": round(average_forward_return, 8),
        "median_forward_return": record.get("median_forward_return"),
        "confidence_interval": record.get("confidence_interval"),
        "p_value_or_non_parametric_equivalent": record.get("p_value_or_non_parametric_equivalent"),
        "false_positive_rate": round(false_positive_rate, 6),
        "drawdown_proxy": round(drawdown_proxy, 8),
        "overfit_warning": bool(record.get("overfit_warning") or metrics.get("overfit_warning")),
        "direction_label": _direction_label(expectancy),
        "linear_success_is_research_evidence_only": True,
    }


def _vector_analogs(
    record: dict[str, Any],
    all_records: list[dict[str, Any]],
    contract: dict[str, Any],
) -> dict[str, Any]:
    source_family = str(record.get("source_or_family") or "")
    market_symbol = str(record.get("market_or_symbol") or "")
    time_window = str(record.get("time_window") or "")
    relationship_type = str(record.get("relationship_type") or "")
    analogs = []
    for candidate in all_records:
        candidate_id = candidate.get("baseline_result_id")
        if candidate_id == record.get("baseline_result_id"):
            continue
        score = 0.0
        if candidate.get("source_or_family") == source_family:
            score += 0.34
        if candidate.get("market_or_symbol") == market_symbol:
            score += 0.34
        if candidate.get("time_window") == time_window:
            score += 0.16
        if candidate.get("relationship_type") == relationship_type:
            score += 0.16
        if score <= 0:
            continue
        analogs.append(
            {
                "baseline_result_id": candidate_id,
                "source_or_family": candidate.get("source_or_family"),
                "market_or_symbol": candidate.get("market_or_symbol"),
                "time_window": candidate.get("time_window"),
                "similarity_score": round(min(score, 1.0), 3),
            }
        )
    analogs.sort(key=lambda item: item["similarity_score"], reverse=True)
    lineage_ids = [
        str(item)
        for item in _safe_list(record.get("source_record_ids"))
        if item
    ]
    if contract.get("contract_id"):
        lineage_ids.append(str(contract["contract_id"]))
    return {
        "retrieval_role": "pattern_agnostic_vector_analog_retrieval",
        "feature_space": [
            "source_or_family",
            "market_or_symbol",
            "time_window",
            "relationship_type",
            "source_price_contract_lineage",
        ],
        "lineage_refs": lineage_ids[:8],
        "analog_count": len(analogs[:5]),
        "nearest_analogs": analogs[:5],
        "retrieval_is_research_context_only": True,
    }


def _state_matrix(record: dict[str, Any], linear_tests: dict[str, Any]) -> dict[str, Any]:
    hit_rate = _safe_float(linear_tests.get("hit_rate"))
    sample_count = _safe_int(linear_tests.get("sample_count"))
    overfit_warning = bool(linear_tests.get("overfit_warning"))
    probability_up = round(hit_rate, 6)
    probability_down_or_flat = round(max(0.0, 1.0 - hit_rate), 6)
    state_key = "|".join(
        [
            str(record.get("source_or_family") or "unknown"),
            str(record.get("market_or_symbol") or "unknown"),
            str(record.get("time_window") or "unknown"),
        ]
    ).lower()
    return {
        "model_role": "state_matrix_probability_model",
        "state_key": state_key,
        "source_state": record.get("source_or_family"),
        "market_state": record.get("market_or_symbol"),
        "time_window_state": record.get("time_window"),
        "probability_up_or_positive": probability_up,
        "probability_down_or_flat": probability_down_or_flat,
        "sample_count": sample_count,
        "confidence_bucket": _confidence_bucket(sample_count, hit_rate, overfit_warning),
        "state_matrix_output_is_not_trade_approval": True,
    }


def _nonlinear_review(
    record: dict[str, Any],
    world_questions: list[dict[str, Any]],
    linear_tests: dict[str, Any],
) -> dict[str, Any]:
    sample_count = _safe_int(linear_tests.get("sample_count"))
    false_positive_rate = _safe_float(linear_tests.get("false_positive_rate"))
    source_family = str(record.get("source_or_family") or "unknown")
    market_symbol = str(record.get("market_or_symbol") or "unknown")
    interaction_terms = [
        f"{source_family}_x_{market_symbol}",
        f"{market_symbol}_x_{record.get('time_window') or 'time_window'}",
    ]
    for question in world_questions[:3]:
        if question.get("affected_market"):
            interaction_terms.append(f"{source_family}_x_{question['affected_market']}")
    if bool(linear_tests.get("overfit_warning")):
        review_state = "downgraded_overfit_warning"
    elif sample_count < MIN_RANKED_SAMPLE_COUNT:
        review_state = "held_for_more_sample"
    elif false_positive_rate > 0.35:
        review_state = "held_for_false_positive_review"
    elif world_questions:
        review_state = "macro_context_interaction_available"
    else:
        review_state = "linear_only_until_more_context"
    return {
        "review_role": "nonlinear_interaction_review",
        "review_state": review_state,
        "interaction_terms": sorted(set(interaction_terms))[:8],
        "world_model_question_refs": [
            question.get("research_question_id") for question in world_questions if question.get("research_question_id")
        ],
        "cross_source_relationship_state": "mapped_if_world_questions_or_source_contracts_overlap"
        if world_questions
        else "not_enough_cross_source_context",
        "cross_asset_relationship_state": "mapped_by_market_symbol_and_family",
        "nonlinear_review_is_research_only": True,
    }


def _entropy_review(linear_tests: dict[str, Any]) -> dict[str, Any]:
    hit_rate = _safe_float(linear_tests.get("hit_rate"))
    entropy = _binary_entropy(hit_rate)
    return {
        "review_role": "ordinal_entropy_regime_review",
        "binary_outcome_entropy": round(entropy, 6),
        "ambiguity_label": _entropy_label(entropy),
        "regime_complexity_label": "directionally_clear" if entropy < 0.35 else "mixed_or_path_dependent",
        "entropy_review_is_not_strategy_or_order": True,
    }


def _quantum_classical_review(
    entropy_review: dict[str, Any],
    nonlinear_review: dict[str, Any],
    linear_tests: dict[str, Any],
) -> dict[str, Any]:
    entropy = _safe_float(entropy_review.get("binary_outcome_entropy"))
    sample_count = _safe_int(linear_tests.get("sample_count"))
    overfit_warning = bool(linear_tests.get("overfit_warning"))
    if overfit_warning:
        verdict = "downgrade_overfit"
    elif sample_count < MIN_RANKED_SAMPLE_COUNT:
        verdict = "hold_low_sample"
    elif entropy < 0.35 and nonlinear_review.get("review_state") != "linear_only_until_more_context":
        verdict = "classical_research_upgrade"
    elif entropy < 0.75:
        verdict = "classical_research_hold"
    else:
        verdict = "hold_high_ambiguity"
    return {
        "review_role": "quantum_classical_review_annotation",
        "quantum_hardware_used": False,
        "quantum_state": "not_consulted_phase_4_research_annotation_only",
        "classical_fallback_used": True,
        "classical_review_basis": [
            "linear_backtest_metrics",
            "state_matrix_probability",
            "entropy_review",
            "nonlinear_interaction_review",
        ],
        "quantum_usefulness_score": round(max(0.0, min(1.0, entropy)), 3),
        "review_verdict": verdict,
        "review_cannot_create_trade_authority": True,
    }


def _rank_score(
    linear_tests: dict[str, Any],
    state_matrix: dict[str, Any],
    nonlinear_review: dict[str, Any],
    entropy_review: dict[str, Any],
) -> float:
    sample_count = _safe_int(linear_tests.get("sample_count"))
    hit_rate = _safe_float(linear_tests.get("hit_rate"))
    expectancy = abs(_safe_float(linear_tests.get("expectancy")))
    false_positive_rate = _safe_float(linear_tests.get("false_positive_rate"))
    entropy = _safe_float(entropy_review.get("binary_outcome_entropy"))
    score = 0.0
    score += min(sample_count, 60) / 60 * 35
    score += min(expectancy * 1000, 30)
    score += abs(hit_rate - 0.5) * 40
    score -= false_positive_rate * 15
    score -= entropy * 8
    if state_matrix.get("confidence_bucket") == "medium_research_confidence":
        score += 8
    elif state_matrix.get("confidence_bucket") == "early_research_confidence":
        score += 4
    if nonlinear_review.get("world_model_question_refs"):
        score += 5
    if linear_tests.get("overfit_warning"):
        score -= 30
    return round(max(0.0, score), 4)


def _lifecycle_state(linear_tests: dict[str, Any], quantum_review: dict[str, Any]) -> str:
    sample_count = _safe_int(linear_tests.get("sample_count"))
    if sample_count < MIN_RANKED_SAMPLE_COUNT:
        return "held_for_more_evidence"
    if quantum_review.get("review_verdict") in {"downgrade_overfit", "hold_high_ambiguity"}:
        return "held_for_more_evidence"
    return "ranked_research_pattern"


def _human_summary(record: dict[str, Any], linear_tests: dict[str, Any], lifecycle_state: str) -> str:
    source = record.get("source_or_family") or "source signal"
    market = record.get("market_or_symbol") or "market"
    time_window = record.get("time_window") or "the tested window"
    direction = _direction_label(_safe_float(linear_tests.get("expectancy"))).replace("_", " ")
    if lifecycle_state == "ranked_research_pattern":
        prefix = "Qadam has ranked a research pattern"
    else:
        prefix = "Qadam is holding a research pattern for more evidence"
    return f"{prefix}: {source} -> {market} over {time_window}, with {direction}."


def _build_pattern_record(
    record: dict[str, Any],
    all_records: list[dict[str, Any]],
    contract: dict[str, Any],
    world_questions: list[dict[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    linear_tests = _linear_tests(record, contract)
    vector_analog_retrieval = _vector_analogs(record, all_records, contract)
    state_matrix_probability = _state_matrix(record, linear_tests)
    nonlinear_interaction_review = _nonlinear_review(record, world_questions, linear_tests)
    entropy_review = _entropy_review(linear_tests)
    quantum_classical_review = _quantum_classical_review(
        entropy_review,
        nonlinear_interaction_review,
        linear_tests,
    )
    lifecycle_state = _lifecycle_state(linear_tests, quantum_classical_review)
    signature = _relationship_signature(record)
    pattern_id = _hash_id(
        "qadam-pattern-v2",
        [
            signature,
            record.get("baseline_result_id"),
            linear_tests.get("sample_count"),
            linear_tests.get("expectancy"),
        ],
    )
    rank_score = _rank_score(
        linear_tests,
        state_matrix_probability,
        nonlinear_interaction_review,
        entropy_review,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "pattern_id": pattern_id,
        "source_baseline_result_id": record.get("baseline_result_id"),
        "source_price_contract_id": contract.get("contract_id"),
        "pattern_status": lifecycle_state,
        "lifecycle_state": lifecycle_state,
        "lifecycle_stage": "research_pattern_ranked_or_held",
        "research_only": True,
        "non_repetitive": True,
        "distinctness_signature": signature,
        "duplicate_of": None,
        "rank": None,
        "rank_score": rank_score,
        "relationship_type": record.get("relationship_type"),
        "source_or_family": record.get("source_or_family"),
        "market_or_symbol": record.get("market_or_symbol"),
        "time_window": record.get("time_window"),
        "source_record_ids": _safe_list(record.get("source_record_ids")),
        "world_model_question_refs": [
            question.get("research_question_id") for question in world_questions if question.get("research_question_id")
        ],
        "detected_signal": record.get("source_or_family"),
        "market_affected": record.get("market_or_symbol"),
        "what_qadam_thinks": _human_summary(record, linear_tests, lifecycle_state),
        "what_would_confirm_it": [
            "More complete forward windows with the same source-price direction.",
            "Independent source confirmation across the mapped source universe.",
            "Later Akber practical confirmation if this ever becomes a strategy input.",
        ],
        "what_blocks_trade": [
            "Phase 4 patterns are research-only.",
            "No strategy hypothesis, Akber pass, router decision, or PaperOps handoff is created here.",
        ],
        "next_allowed_action": "Use this record as evidence input for Phase 5 Strategy Evidence Map only.",
        "linear_tests": linear_tests,
        "vector_analog_retrieval": vector_analog_retrieval,
        "state_matrix_probability": state_matrix_probability,
        "nonlinear_interaction_review": nonlinear_interaction_review,
        "entropy_review": entropy_review,
        "quantum_classical_review": quantum_classical_review,
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


def _rejection_from_baseline(record: dict[str, Any], generated_at: str) -> dict[str, Any]:
    signature = _relationship_signature(record)
    return {
        "schema_version": SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "rejection_id": _hash_id("qadam-pattern-v2-reject", [signature, record.get("rejection_reason")]),
        "source_baseline_result_id": record.get("baseline_result_id"),
        "lifecycle_state": "rejected_low_sample",
        "rejection_reason": record.get("rejection_reason") or "baseline_relationship_rejected",
        "distinctness_signature": signature,
        "relationship_type": record.get("relationship_type"),
        "source_or_family": record.get("source_or_family"),
        "market_or_symbol": record.get("market_or_symbol"),
        "time_window": record.get("time_window"),
        "sample_count": record.get("sample_count"),
        "minimum_sample_count": record.get("minimum_sample_count"),
        "research_only": True,
        "trade_candidate_creation_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
        "authority": _authority(),
        "generated_at": generated_at,
    }


def _duplicate_rejection(record: dict[str, Any], duplicate_of: str, generated_at: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "rejection_id": _hash_id("qadam-pattern-v2-duplicate", [record.get("pattern_id"), duplicate_of]),
        "source_pattern_id": record.get("pattern_id"),
        "duplicate_of": duplicate_of,
        "lifecycle_state": "rejected_duplicate",
        "rejection_reason": "duplicate_distinctness_signature",
        "distinctness_signature": record.get("distinctness_signature"),
        "relationship_type": record.get("relationship_type"),
        "source_or_family": record.get("source_or_family"),
        "market_or_symbol": record.get("market_or_symbol"),
        "time_window": record.get("time_window"),
        "research_only": True,
        "trade_candidate_creation_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
        "authority": _authority(),
        "generated_at": generated_at,
    }


def _build_dashboard_summary(
    primary: dict[str, Any],
    records: list[dict[str, Any]],
    rejections: list[dict[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    lifecycle_counts = Counter(str(record.get("lifecycle_state") or "unknown") for record in records)
    method_counts = {
        method: sum(1 for record in records if isinstance(record.get(method), dict))
        for method in REQUIRED_METHOD_BLOCKS
    }
    top_patterns = []
    for record in records[:8]:
        top_patterns.append(
            {
                "rank": record.get("rank"),
                "pattern_id": record.get("pattern_id"),
                "rank_score": record.get("rank_score"),
                "lifecycle_state": record.get("lifecycle_state"),
                "source_or_family": record.get("source_or_family"),
                "market_or_symbol": record.get("market_or_symbol"),
                "time_window": record.get("time_window"),
                "what_qadam_thinks": record.get("what_qadam_thinks"),
                "what_blocks_trade": record.get("what_blocks_trade"),
                "quantum_classical_review": record.get("quantum_classical_review", {}).get("review_verdict"),
                "entropy_label": record.get("entropy_review", {}).get("ambiguity_label"),
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_pattern_engine_v2_dashboard_summary",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": primary.get("status"),
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "proposal_first": True,
        "research_only": True,
        "pattern_count": len(records),
        "ranked_pattern_count": lifecycle_counts.get("ranked_research_pattern", 0),
        "held_for_more_evidence_count": lifecycle_counts.get("held_for_more_evidence", 0),
        "rejected_pattern_count": len(rejections),
        "duplicate_rejection_count": sum(
            1 for rejection in rejections if rejection.get("lifecycle_state") == "rejected_duplicate"
        ),
        "distinct_pattern_count": len({record.get("distinctness_signature") for record in records}),
        "method_coverage": method_counts,
        "top_patterns": top_patterns,
        "message": (
            "Pattern Engine V2 ranks research-only source-price patterns. "
            "It does not create trade candidates, approvals, paper orders, broker writes, or proof credit."
        ),
        "next_allowed_action": "Feed ranked research evidence into Phase 5 Strategy Evidence Map.",
        "trade_candidate_creation_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
        "authority": _authority(),
        "artifact_refs": {
            "primary": PRIMARY_ARTIFACT,
            "records": PATTERN_RECORDS_ARTIFACT,
            "rejections": REJECTIONS_ARTIFACT,
        },
    }


def build_pattern_engine_v2(settings: Settings | None = None) -> PatternEngineBundle:
    generated_at = _iso()
    context = _load_context(settings)
    baseline_results = context["baseline_results"]
    contract_by_baseline = _contract_index(context["source_price_contracts"])
    questions_by_market = _world_questions_by_market(context["world_model_research_questions"])

    built_records: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = [
        _rejection_from_baseline(record, generated_at)
        for record in context["baseline_rejections"][:200]
    ]

    for result in baseline_results:
        contract = contract_by_baseline.get(str(result.get("baseline_result_id") or ""), {})
        world_questions = _matching_world_questions(result, questions_by_market)
        built_records.append(
            _build_pattern_record(result, baseline_results, contract, world_questions, generated_at)
        )

    # Distinctness is enforced before final ranking so repeated source-price
    # shapes do not crowd out meaningful alternatives.
    deduped: dict[str, dict[str, Any]] = {}
    for record in built_records:
        signature = str(record.get("distinctness_signature") or "")
        existing = deduped.get(signature)
        if existing is None:
            deduped[signature] = record
            continue
        if _safe_float(record.get("rank_score")) > _safe_float(existing.get("rank_score")):
            rejections.append(_duplicate_rejection(existing, str(record.get("pattern_id")), generated_at))
            deduped[signature] = record
        else:
            rejections.append(_duplicate_rejection(record, str(existing.get("pattern_id")), generated_at))

    records = sorted(
        deduped.values(),
        key=lambda item: (
            _safe_float(item.get("rank_score")),
            _safe_int(item.get("linear_tests", {}).get("sample_count")),
            str(item.get("pattern_id")),
        ),
        reverse=True,
    )[:MAX_ACCEPTED_PATTERNS]
    for rank, record in enumerate(records, start=1):
        record["rank"] = rank

    lifecycle_counts = Counter(str(record.get("lifecycle_state") or "unknown") for record in records)
    relationship_counts = Counter(str(record.get("relationship_type") or "unknown") for record in records)
    source_counts = Counter(str(record.get("source_or_family") or "unknown") for record in records)
    market_counts = Counter(str(record.get("market_or_symbol") or "unknown") for record in records)
    status = (
        "pattern_engine_v2_ready"
        if records
        else "pattern_engine_v2_blocked_no_baseline_patterns"
    )
    primary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_pattern_engine_v2",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": status,
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "proposal_first": True,
        "research_only": True,
        "input_artifacts": {
            "baseline_results": BASELINE_RESULTS_ARTIFACT,
            "baseline_rejections": BASELINE_REJECTIONS_ARTIFACT,
            "source_price_contracts": SOURCE_PRICE_CONTRACTS_ARTIFACT,
            "world_model_research_questions": WORLD_MODEL_RESEARCH_QUESTIONS_ARTIFACT,
        },
        "pattern_count": len(records),
        "ranked_pattern_count": lifecycle_counts.get("ranked_research_pattern", 0),
        "held_for_more_evidence_count": lifecycle_counts.get("held_for_more_evidence", 0),
        "rejected_pattern_count": len(rejections),
        "duplicate_rejection_count": sum(
            1 for rejection in rejections if rejection.get("lifecycle_state") == "rejected_duplicate"
        ),
        "distinct_pattern_count": len({record.get("distinctness_signature") for record in records}),
        "lifecycle_counts": dict(sorted(lifecycle_counts.items())),
        "relationship_counts": dict(sorted(relationship_counts.items())),
        "source_counts": dict(source_counts.most_common(12)),
        "market_counts": dict(market_counts.most_common(12)),
        "method_blocks_required": list(REQUIRED_METHOD_BLOCKS),
        "method_coverage": {
            method: sum(1 for record in records if isinstance(record.get(method), dict))
            for method in REQUIRED_METHOD_BLOCKS
        },
        "top_pattern_ids": [record.get("pattern_id") for record in records[:5]],
        "trade_candidate_creation_allowed": False,
        "trade_candidate_created": False,
        "qualified_setup_created": False,
        "risk_approval_created": False,
        "execution_approval_created": False,
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
            "records": PATTERN_RECORDS_ARTIFACT,
            "rejections": REJECTIONS_ARTIFACT,
            "dashboard_summary": DASHBOARD_SUMMARY_ARTIFACT,
        },
    }
    dashboard_summary = _build_dashboard_summary(primary, records, rejections, generated_at)
    return PatternEngineBundle(
        primary=primary,
        records=records,
        rejections=rejections,
        dashboard_summary=dashboard_summary,
    )


def write_pattern_engine_v2(bundle: PatternEngineBundle, settings: Settings | None = None) -> dict[str, str]:
    runtime = _runtime_dir(settings)
    paths = {
        "primary": runtime / PRIMARY_ARTIFACT,
        "records": runtime / PATTERN_RECORDS_ARTIFACT,
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
            "event_type": "pattern_engine_v2_written",
            "generated_at": bundle.primary.get("generated_at"),
            "status": bundle.primary.get("status"),
            "pattern_count": len(bundle.records),
            "rejected_pattern_count": len(bundle.rejections),
            "research_only": True,
            "paper_order_created": False,
            "broker_write_count": 0,
            "live_capital_enabled": False,
            "proof_credit_allowed": False,
            "authority": _authority(),
        },
    )
    return {key: str(path) for key, path in paths.items()}


def build_and_write_pattern_engine_v2(settings: Settings | None = None) -> tuple[PatternEngineBundle, dict[str, str]]:
    bundle = build_pattern_engine_v2(settings)
    written = write_pattern_engine_v2(bundle, settings)
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


def validate_pattern_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("schema_version") != SCHEMA_VERSION:
        errors.append("record_schema_version_invalid")
    if record.get("phase_id") != PHASE_ID:
        errors.append("record_phase_id_invalid")
    if not record.get("pattern_id"):
        errors.append("record_pattern_id_missing")
    if record.get("research_only") is not True:
        errors.append("record_research_only_must_be_true")
    if record.get("non_repetitive") is not True:
        errors.append("record_non_repetitive_must_be_true")
    if not record.get("distinctness_signature"):
        errors.append("record_distinctness_signature_missing")
    if record.get("lifecycle_state") not in ALLOWED_LIFECYCLE_STATES:
        errors.append("record_lifecycle_state_invalid")
    if not isinstance(record.get("rank"), int) or record.get("rank", 0) <= 0:
        errors.append("record_rank_invalid")
    for method in REQUIRED_METHOD_BLOCKS:
        if not isinstance(record.get(method), dict):
            errors.append(f"record_{method}_missing")
    errors.extend(_validate_authority(record, "record"))
    return errors


def validate_rejection_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("schema_version") != SCHEMA_VERSION:
        errors.append("rejection_schema_version_invalid")
    if record.get("phase_id") != PHASE_ID:
        errors.append("rejection_phase_id_invalid")
    if record.get("lifecycle_state") not in ALLOWED_LIFECYCLE_STATES:
        errors.append("rejection_lifecycle_state_invalid")
    if record.get("research_only") is not True:
        errors.append("rejection_research_only_must_be_true")
    if not record.get("rejection_reason"):
        errors.append("rejection_reason_missing")
    errors.extend(_validate_authority(record, "rejection"))
    return errors


def validate_pattern_engine_v2_bundle(bundle: PatternEngineBundle | dict[str, Any]) -> list[str]:
    if isinstance(bundle, PatternEngineBundle):
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
    if primary.get("artifact_type") != "qadam_pattern_engine_v2":
        errors.append("primary_artifact_type_invalid")
    if primary.get("status") != "pattern_engine_v2_ready":
        errors.append("primary_status_not_ready")
    for key in ("public_safe", "read_only", "paper_only", "proposal_first", "research_only"):
        if primary.get(key) is not True:
            errors.append(f"primary_{key}_must_be_true")
    errors.extend(_validate_authority(primary, "primary"))
    if not records:
        errors.append("pattern_records_missing")
    signatures = [record.get("distinctness_signature") for record in records]
    if len(signatures) != len(set(signatures)):
        errors.append("pattern_records_duplicate_signatures")
    ranks = [record.get("rank") for record in records]
    if ranks != list(range(1, len(records) + 1)):
        errors.append("pattern_ranks_not_consecutive")
    for index, record in enumerate(records, start=1):
        for error in validate_pattern_record(record):
            errors.append(f"record_{index}_{error}")
    for index, record in enumerate(rejections[:200], start=1):
        for error in validate_rejection_record(record):
            errors.append(f"rejection_{index}_{error}")
    for method in REQUIRED_METHOD_BLOCKS:
        if primary.get("method_coverage", {}).get(method) != len(records):
            errors.append(f"primary_method_coverage_{method}_incomplete")
    if primary.get("trade_candidate_created") is not False:
        errors.append("primary_trade_candidate_created_must_be_false")
    if primary.get("paper_order_created") is not False:
        errors.append("primary_paper_order_created_must_be_false")
    if _safe_int(primary.get("broker_write_count")) != 0:
        errors.append("primary_broker_write_count_must_be_zero")
    if dashboard_summary.get("artifact_type") != "qadam_pattern_engine_v2_dashboard_summary":
        errors.append("dashboard_summary_artifact_type_invalid")
    if dashboard_summary.get("research_only") is not True:
        errors.append("dashboard_summary_research_only_must_be_true")
    if dashboard_summary.get("pattern_count") != len(records):
        errors.append("dashboard_summary_pattern_count_mismatch")
    if dashboard_summary.get("trade_candidate_creation_allowed") is not False:
        errors.append("dashboard_summary_trade_candidate_creation_allowed_must_be_false")
    if dashboard_summary.get("paper_order_allowed") is not False:
        errors.append("dashboard_summary_paper_order_allowed_must_be_false")
    if dashboard_summary.get("live_capital_enabled") is not False:
        errors.append("dashboard_summary_live_capital_enabled_must_be_false")
    return errors


def validate_negative_pattern_engine_v2_probes(settings: Settings | None = None) -> list[str]:
    bundle = build_pattern_engine_v2(settings)
    if not bundle.records:
        return ["negative_probe_skipped_missing_pattern_records"]
    errors: list[str] = []

    unsafe_record = json.loads(json.dumps(bundle.records[0]))
    unsafe_record["paper_order_allowed"] = True
    unsafe_record["authority"]["paper_order_allowed"] = True
    if not validate_pattern_record(unsafe_record):
        errors.append("negative_probe_failed_for_paper_order_authority")

    duplicate_payload = {
        "primary": bundle.primary,
        "records": bundle.records + [json.loads(json.dumps(bundle.records[0]))],
        "rejections": bundle.rejections,
        "dashboard_summary": bundle.dashboard_summary,
    }
    if "pattern_records_duplicate_signatures" not in validate_pattern_engine_v2_bundle(duplicate_payload):
        errors.append("negative_probe_failed_for_duplicate_signature")

    non_research_record = json.loads(json.dumps(bundle.records[0]))
    non_research_record["research_only"] = False
    if not validate_pattern_record(non_research_record):
        errors.append("negative_probe_failed_for_research_only_boundary")

    missing_method_record = json.loads(json.dumps(bundle.records[0]))
    missing_method_record.pop("entropy_review", None)
    if not validate_pattern_record(missing_method_record):
        errors.append("negative_probe_failed_for_missing_method_block")

    candidate_record = json.loads(json.dumps(bundle.records[0]))
    candidate_record["trade_candidate_created"] = True
    candidate_record["authority"]["trade_candidate_created"] = True
    if not validate_pattern_record(candidate_record):
        errors.append("negative_probe_failed_for_trade_candidate_boundary")

    return errors


def load_pattern_engine_v2(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "primary": _read_json(runtime / PRIMARY_ARTIFACT),
        "records": _read_jsonl(runtime / PATTERN_RECORDS_ARTIFACT),
        "rejections": _read_jsonl(runtime / REJECTIONS_ARTIFACT),
        "dashboard_summary": _read_json(runtime / DASHBOARD_SUMMARY_ARTIFACT),
    }
