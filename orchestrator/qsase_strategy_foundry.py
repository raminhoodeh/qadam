"""QSASE-7 Strategy Foundry.

Strategy Foundry converts sufficiently vetted source-price patterns into
strategy hypotheses. It is not a PaperOps route: hypotheses are not trades,
qualified setups, risk approvals, execution approvals, or orders.
"""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qsase_governance_safety_contract import (
    PHASE_STATUS_ARTIFACT,
    universal_authority_flags,
)

SCHEMA_VERSION = "qsase_strategy_foundry.v1"
PHASE_ID = "qsase_7_strategy_foundry"
PHASE_NAME = "QSASE-7: Strategy Foundry"
IMPLEMENTATION_LOG = "docs/qsase-implementation-log.md"

PRIMARY_ARTIFACT = "qsase_strategy_hypotheses.json"
HYPOTHESES_ARTIFACT = "qsase_strategy_hypotheses.jsonl"
HISTORY_ARTIFACT = "qsase_strategy_hypotheses_history.jsonl"
EVENTS_ARTIFACT = "qsase_strategy_hypotheses_events.jsonl"
FAMILY_MAP_ARTIFACT = "qsase_strategy_family_map.json"
REJECTED_HYPOTHESES_ARTIFACT = "qsase_rejected_strategy_hypotheses.jsonl"
DASHBOARD_SUMMARY_ARTIFACT = "qsase_strategy_foundry_dashboard_summary.json"

NONLINEAR_LAB_ARTIFACT = "qsase_nonlinear_quantum_pattern_lab.json"
NONLINEAR_RESULTS_ARTIFACT = "qsase_nonlinear_pattern_results.jsonl"
QUANTUM_REVIEWS_ARTIFACT = "qsase_quantum_pattern_reviews.jsonl"
LINEAR_LAB_ARTIFACT = "qsase_linear_pattern_lab.json"
LINEAR_RESULTS_ARTIFACT = "qsase_linear_backtest_results.jsonl"
FULL_UNIVERSE_ARTIFACT = "qsase_full_universe_pattern_search.json"
PHASE4_STRATEGY_UNIVERSE_ARTIFACT = "phase4_candidate_strategy_universe.json"
STRATEGY_RESEARCH_INTAKE_ARTIFACT = "strategy_research_intake.json"
STRATEGY_UPDATE_RECORD_ARTIFACT = "strategy_update_record.json"
SHADOW_REPLAY_ARTIFACT = "phase6_shadow_strategy_replay.json"
PAPEROPS_SUMMARY_ARTIFACT = "paperops_autonomous_pass_summary.json"

KNOWN_STRATEGY_FAMILIES = {
    "prediction_market_geopolitical_dislocation": {
        "label": "Prediction Market Geopolitical Dislocation",
        "instrument_keywords": ["prediction", "kalshi", "polymarket"],
        "source_keywords": ["kalshi", "polymarket", "gdelt", "telegram", "acled"],
        "catalyst_class": "event_probability_dislocation",
        "allowed_proxy_set": ["prediction_markets", "event_contracts"],
    },
    "crude_oil_energy_security_disruption": {
        "label": "Crude Oil Energy Security Disruption",
        "instrument_keywords": ["CL", "USO", "XLE", "oil", "crude", "energy"],
        "source_keywords": ["acled", "ais_maritime", "nasa_firms", "conflict_tracker", "ucdp"],
        "catalyst_class": "energy_security_disruption",
        "allowed_proxy_set": ["USO", "XLE", "energy_equities", "crude_oil_proxy"],
    },
    "defence_repricing_geopolitical_watch": {
        "label": "Defence Repricing Geopolitical Watch",
        "instrument_keywords": ["ITA", "XAR", "defence", "defense"],
        "source_keywords": ["acled", "gdelt", "sec_edgar", "stock_act", "patents"],
        "catalyst_class": "defence_geopolitical_repricing",
        "allowed_proxy_set": ["ITA", "XAR", "defence_equities"],
    },
    "silver_macro_liquidity_stress": {
        "label": "Silver Macro Liquidity Stress",
        "instrument_keywords": ["SLV", "XAG", "silver"],
        "source_keywords": ["fred", "ecb", "bis", "usgs", "un_comtrade"],
        "catalyst_class": "macro_liquidity_stress",
        "allowed_proxy_set": ["SLV", "silver_proxy"],
    },
    "semiconductor_policy_options_asymmetry": {
        "label": "Semiconductor Policy Options Asymmetry",
        "instrument_keywords": ["SMH", "SOXX", "NVDA", "semiconductor", "chip"],
        "source_keywords": ["sec_edgar", "patents", "gdelt", "rss", "stock_act"],
        "catalyst_class": "semiconductor_policy_asymmetry",
        "allowed_proxy_set": ["SMH", "SOXX", "semiconductor_equities"],
    },
}

PAPERABLE_PROXY_EXPRESSIONS = {
    "CL=F": {
        "primary_proxy": "USO",
        "alternate_proxies": ["XLE"],
        "proxy_set": ["USO", "XLE", "crude_oil_proxy"],
        "reason": "CL=F is observed as crude-oil context; guarded paper review must express through paperable crude/energy proxies.",
    },
    "SI=F": {
        "primary_proxy": "SLV",
        "alternate_proxies": [],
        "proxy_set": ["SLV", "silver_proxy"],
        "reason": "SI=F is observed as silver context; guarded paper review must express through SLV.",
    },
    "GC=F": {
        "primary_proxy": "GLD",
        "alternate_proxies": [],
        "proxy_set": ["GLD", "gold_proxy"],
        "reason": "GC=F is observed as gold context; guarded paper review must express through GLD.",
    },
}

FOUNDRY_AUTHORITY_FLAGS = {
    "strategy_approved": False,
    "strategy_family_active": False,
    "strategy_mutation_allowed": False,
    "strategy_mutation_created": False,
    "source_weight_update_allowed": False,
    "source_weight_update_applied": False,
    "model_weight_update_allowed": False,
    "model_weight_update_created": False,
    "trade_candidate_created": False,
    "trade_candidate_creation_allowed": False,
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
    "prediction_market_write_allowed": False,
    "paperops_direct_handoff_allowed": False,
    "akber_filter_passed": False,
    "shadow_replay_executed": False,
    "live_capital_enabled": False,
    "proof_credit_allowed": False,
    "paper_proof_ledger_credit_allowed": False,
    "paper_growth_trial_calendar_advance_allowed": False,
    "telegram_command_path_enabled": False,
    "telegram_trade_command_enabled": False,
}

REQUIRED_HYPOTHESIS_FIELDS = [
    "strategy_hypothesis_id",
    "status",
    "name",
    "hypothesis_type",
    "lineage",
    "research_goal_lineage",
    "candidate_identity",
    "source_recipe",
    "market_expression",
    "strategy_logic",
    "evidence",
    "family_mapping",
    "paperability",
    "risk_concept",
    "route_readiness",
    "learning_value",
    "authority",
]

REQUIRED_REJECTION_FIELDS = [
    "rejected_hypothesis_id",
    "source_pattern_id",
    "strategy_family",
    "candidate_identity",
    "rejection_reasons",
    "evidence_summary",
    "paperability",
    "retest_allowed",
    "retest_condition",
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


def _strategy_hypothesis_id(nonlinear_pattern_id: str, family_key: str) -> str:
    return _hash_id([SCHEMA_VERSION, nonlinear_pattern_id, family_key, "hypothesis"], "qsase-strategy")


def _rejected_hypothesis_id(nonlinear_pattern_id: str, family_key: str) -> str:
    return _hash_id([SCHEMA_VERSION, nonlinear_pattern_id, family_key, "reject"], "qsase-rejected-strategy")


def _research_goal_id(nonlinear_pattern_id: str) -> str:
    return _hash_id([SCHEMA_VERSION, nonlinear_pattern_id, "research-goal"], "qsase-rg")


def _candidate_identity_key(parts: list[Any]) -> str:
    return _hash_id([SCHEMA_VERSION, *parts, "strategy-candidate-identity"], "qsase-strategy-identity")


def _float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _authority_block() -> dict[str, Any]:
    return {
        "strategy_hypothesis_only": True,
        "not_trade_candidate": True,
        "not_qualified_setup": True,
        "not_order": True,
        **FOUNDRY_AUTHORITY_FLAGS,
    }


def _load_context(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "runtime_dir": runtime,
        "nonlinear_lab": _read_json(runtime / NONLINEAR_LAB_ARTIFACT),
        "nonlinear_results": _read_jsonl(runtime / NONLINEAR_RESULTS_ARTIFACT),
        "quantum_reviews": _read_jsonl(runtime / QUANTUM_REVIEWS_ARTIFACT),
        "linear_lab": _read_json(runtime / LINEAR_LAB_ARTIFACT),
        "linear_results": _read_jsonl(runtime / LINEAR_RESULTS_ARTIFACT),
        "full_universe": _read_json(runtime / FULL_UNIVERSE_ARTIFACT),
        "phase4_strategy_universe": _read_json(runtime / PHASE4_STRATEGY_UNIVERSE_ARTIFACT),
        "strategy_research_intake": _read_json(runtime / STRATEGY_RESEARCH_INTAKE_ARTIFACT),
        "strategy_update_record": _read_json(runtime / STRATEGY_UPDATE_RECORD_ARTIFACT),
        "shadow_replay": _read_json(runtime / SHADOW_REPLAY_ARTIFACT),
        "paperops_summary": _read_json(runtime / PAPEROPS_SUMMARY_ARTIFACT),
    }


def _known_families_from_context(context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    families = copy.deepcopy(KNOWN_STRATEGY_FAMILIES)
    for candidate in context.get("phase4_strategy_universe", {}).get("candidates", []):
        key = candidate.get("candidate_key")
        if not key:
            continue
        families.setdefault(
            key,
            {
                "label": candidate.get("name", key.replace("_", " ").title()),
                "instrument_keywords": candidate.get("instrument_universe", []),
                "source_keywords": candidate.get("required_source_groups", []),
                "catalyst_class": (candidate.get("catalyst_classes") or ["strategy_family_candidate"])[0],
                "allowed_proxy_set": candidate.get("instrument_universe", []),
            },
        )
    return families


def _text_blob(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str).lower()


def map_patterns_to_strategy_families(
    patterns: list[dict[str, Any]],
    existing_families: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    mappings: list[dict[str, Any]] = []
    for pattern in patterns:
        blob = _text_blob(
            {
                "source_recipe": pattern.get("source_recipe", {}),
                "market_expression": pattern.get("market_expression", {}),
            }
        )
        scores: dict[str, float] = {}
        for family_key, family in existing_families.items():
            instrument_hits = sum(1 for keyword in family.get("instrument_keywords", []) if str(keyword).lower() in blob)
            source_hits = sum(1 for keyword in family.get("source_keywords", []) if str(keyword).lower() in blob)
            scores[family_key] = round(instrument_hits * 1.5 + source_hits, 6)
        best_family = max(scores, key=scores.get) if scores else "unmapped_new_family_candidate"
        best_score = scores.get(best_family, 0.0)
        if best_score <= 0:
            best_family = "unmapped_new_family_candidate"
        mapped_existing = best_family if best_family in existing_families else None
        mappings.append(
            {
                "source_pattern_id": pattern.get("nonlinear_pattern_id"),
                "source_linear_pattern_id": pattern.get("source_linear_pattern_id"),
                "mapped_existing_family": mapped_existing,
                "proposed_new_family": None if mapped_existing else _proposed_new_family_key(pattern),
                "mapping_score": best_score,
                "all_family_scores": scores,
                "strategy_collapse_review_required": True,
                "mapping_decision": "existing_family_match" if mapped_existing else "new_family_candidate_requires_review",
                "known_family_count": len(existing_families),
            }
        )
    return mappings


def _proposed_new_family_key(pattern: dict[str, Any]) -> str:
    instrument = str(pattern.get("market_expression", {}).get("instrument") or "unknown").lower()
    catalyst = _catalyst_class(pattern)
    clean_instrument = "".join(ch if ch.isalnum() else "_" for ch in instrument).strip("_")[:32] or "unknown"
    return f"qsase_{catalyst}_{clean_instrument}"


def _quantum_reviews_by_source(reviews: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(review.get("source_pattern_id")): review for review in reviews}


def _catalyst_class(pattern: dict[str, Any]) -> str:
    market = _text_blob(pattern.get("market_expression", {}))
    sources = _text_blob(pattern.get("source_recipe", {}))
    if any(token in market for token in ("cl=f", "oil", "energy")):
        return "energy_security_disruption"
    if "silver" in market or "slv" in market or "xag" in market:
        return "macro_liquidity_stress"
    if any(token in market for token in ("smh", "soxx", "nvda", "semiconductor")):
        return "semiconductor_policy_asymmetry"
    if "prediction" in market or "kalshi" in sources or "polymarket" in sources:
        return "event_probability_dislocation"
    if "defence" in market or "defense" in market:
        return "defence_geopolitical_repricing"
    return "cross_source_market_dislocation"


def _paperability(pattern: dict[str, Any], family_map: dict[str, Any]) -> dict[str, Any]:
    market = pattern.get("market_expression", {})
    instrument = str(market.get("instrument") or "")
    route_fit = str(market.get("paper_route_fit") or "")
    blockers: list[str] = []
    state = "paper_review_possible_after_router"
    allowed_proxy_set = []
    proxy_expression = PAPERABLE_PROXY_EXPRESSIONS.get(instrument)
    family_key = family_map.get("mapped_existing_family")
    if family_key and family_key in KNOWN_STRATEGY_FAMILIES:
        allowed_proxy_set = KNOWN_STRATEGY_FAMILIES[family_key]["allowed_proxy_set"]
    if proxy_expression:
        allowed_proxy_set = sorted(set(allowed_proxy_set + list(proxy_expression["proxy_set"])))
    elif "observable_not_paper_route_ready" in route_fit or instrument.endswith("=F"):
        state = "blocked_observable_only"
        blockers.append("instrument_is_observable_or_futures_symbol_not_guarded_paper_route")
    if not instrument:
        state = "blocked_missing_instrument"
        blockers.append("missing_instrument_mapping")
    if pattern.get("decision", {}).get("quantum_review_state") == "quantum_hold":
        state = "blocked_quantum_ambiguity_hold"
        blockers.append("quantum_ambiguity_hold")
    return {
        "paperability_state": state,
        "primary_instrument": instrument,
        "observed_market_expression": instrument,
        "paperable_execution_expression": proxy_expression.get("primary_proxy") if proxy_expression else instrument,
        "paperable_proxy_expression": proxy_expression,
        "proxy_review_required": bool(proxy_expression),
        "proxy_review_only_no_order_authority": True,
        "paper_route_required": True,
        "allowed_proxy_set": allowed_proxy_set,
        "paper_review_candidate": state == "paper_review_possible_after_router",
        "paper_order_allowed": False,
        "paperability_blockers": blockers,
    }


def _risk_concept(pattern: dict[str, Any]) -> dict[str, Any]:
    tests = pattern.get("nonlinear_tests", {})
    market = pattern.get("market_expression", {})
    return {
        "risk_shape": "event_lag_and_false_positive_risk",
        "primary_risks": [
            "source_quorum_failure",
            "market_already_repriced",
            "duplicate_exposure_conflict",
            "ambiguous_quantum_review",
            "paper_route_unavailable",
        ],
        "expected_holding_window": market.get("horizon") or "unknown",
        "max_loss_concept": "risk_budget_required_later_no_sizing_here",
        "stop_concept": "invalidate_on_source_reversal_or_opposite_market_confirmation",
        "overfit_risk_score": tests.get("overfit_risk_score"),
        "risk_budget_required": True,
        "risk_approval_created": False,
    }


def _invalidation_concept(pattern: dict[str, Any]) -> dict[str, Any]:
    return {
        "invalidation_id": _hash_id([pattern.get("nonlinear_pattern_id"), "invalidation"], "qsase-invalidation"),
        "summary": (
            "Invalidate if source quorum fails, source direction reverses, market reprices in the opposite "
            "direction, nonlinear evidence remains non-incremental, quantum ambiguity holds, or paper route state is unsafe."
        ),
        "hard_invalidators": [
            "source_quorum_missing",
            "point_in_time_or_leakage_failure",
            "quantum_ambiguity_hold",
            "paper_route_unavailable",
            "duplicate_exposure_conflict",
        ],
    }


def _candidate_identity(pattern: dict[str, Any], family_map: dict[str, Any]) -> dict[str, Any]:
    market = pattern.get("market_expression", {})
    source_recipe = pattern.get("source_recipe", {})
    family_key = family_map.get("mapped_existing_family") or family_map.get("proposed_new_family")
    catalyst = _catalyst_class(pattern)
    identity_key = _candidate_identity_key(
        [
            family_key,
            pattern.get("source_pattern_id"),
            pattern.get("source_linear_pattern_id"),
            pattern.get("nonlinear_pattern_id"),
            market.get("instrument"),
            market.get("horizon"),
            catalyst,
        ]
    )
    return {
        "candidate_identity_key": identity_key,
        "identity_type": "strategy_hypothesis_identity_not_trade_candidate",
        "thesis": f"{catalyst} in {market.get('instrument') or 'unknown instrument'} may produce a repeatable source-price lag.",
        "source_packet_id": _hash_id([pattern.get("nonlinear_pattern_id"), "source-packet"], "qsase-source-packet"),
        "instrument": market.get("instrument"),
        "time_window": market.get("horizon"),
        "source_recipe_fingerprint": _hash_id([source_recipe], "qsase-source-recipe"),
        "invalidation_id": _invalidation_concept(pattern)["invalidation_id"],
        "risk_concept_id": _hash_id([pattern.get("nonlinear_pattern_id"), "risk-concept"], "qsase-risk-concept"),
        "hypothesis_identity_seed": identity_key,
        "not_idempotency_key_for_orders": True,
    }


def _lineage(pattern: dict[str, Any], quantum_review: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "source_pattern_ids": [pattern.get("source_pattern_id")],
        "linear_pattern_ids": [pattern.get("source_linear_pattern_id")],
        "nonlinear_pattern_ids": [pattern.get("nonlinear_pattern_id")],
        "quantum_review_ids": [quantum_review.get("quantum_review_id")] if quantum_review else [],
        "historical_memory_refs": [
            f"qsase-memory-sample-count:{pattern.get('sample', {}).get('memory_record_count', 0)}"
        ],
        "source_price_evidence_artifacts": [
            f"data/runtime/{FULL_UNIVERSE_ARTIFACT}",
            f"data/runtime/{LINEAR_RESULTS_ARTIFACT}",
            f"data/runtime/{NONLINEAR_RESULTS_ARTIFACT}",
            f"data/runtime/{QUANTUM_REVIEWS_ARTIFACT}",
        ],
    }


def _research_goal_lineage(pattern: dict[str, Any], family_key: str) -> dict[str, Any]:
    research_goal_id = _research_goal_id(str(pattern.get("nonlinear_pattern_id")))
    return {
        "research_goal_id": research_goal_id,
        "origin_phase": "QSASE-4 full-universe pattern search",
        "evidence_chain": [
            "QSASE-4 source-price pattern",
            "QSASE-5 linear lab",
            "QSASE-6 nonlinear and quantum pattern lab",
            "QSASE-7 strategy foundry",
        ],
        "foundry_objective": "Map source-price evidence into a hypothesis or rejection record without execution authority.",
        "target_strategy_family": family_key,
        "paper_proof_ledger_credit_allowed": False,
        "paper_growth_trial_calendar_advance_allowed": False,
    }


def _hypothesis_rejection_reasons(
    pattern: dict[str, Any],
    quantum_review: dict[str, Any] | None,
    paperability: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    tests = pattern.get("nonlinear_tests", {})
    sample = pattern.get("sample", {})
    if sample.get("point_in_time_safe") is not True:
        reasons.append("point_in_time_leakage")
    if sample.get("complete_forward_outcome_count", 0) < 20:
        reasons.append("sample_too_small")
    if tests.get("linear_baseline_beaten") is not True:
        reasons.append("nonlinear_not_incremental")
    if _float(tests.get("overfit_risk_score")) > 0.45:
        reasons.append("overfit_pattern")
    if quantum_review:
        if quantum_review.get("review_state") == "quantum_hold":
            reasons.append("quantum_ambiguity_too_high")
        if quantum_review.get("recommendation") in {"hold", "downgrade_or_hold"}:
            reasons.append("quantum_did_not_upgrade_research_confidence")
    else:
        reasons.append("missing_required_quantum_review")
    if paperability["paper_review_candidate"] is not True:
        reasons.extend(paperability.get("paperability_blockers") or ["no_clean_paper_expression"])
    if not pattern.get("source_recipe", {}).get("source_names"):
        reasons.append("source_quorum_weak")
    return sorted(set(reasons or ["learning_value_too_low"]))


def _hypothesis_eligible(pattern: dict[str, Any], quantum_review: dict[str, Any] | None, paperability: dict[str, Any]) -> bool:
    tests = pattern.get("nonlinear_tests", {})
    sample = pattern.get("sample", {})
    if tests.get("linear_baseline_beaten") is not True:
        return False
    if sample.get("point_in_time_safe") is not True:
        return False
    if sample.get("complete_forward_outcome_count", 0) < 20:
        return False
    if _float(tests.get("overfit_risk_score")) > 0.45:
        return False
    if not quantum_review or quantum_review.get("review_state") == "quantum_hold":
        return False
    if quantum_review.get("recommendation") not in {"upgrade_shadow_confidence"}:
        return False
    if paperability["paper_review_candidate"] is not True:
        return False
    return True


def _strategy_logic(pattern: dict[str, Any], catalyst: str) -> dict[str, Any]:
    market = pattern.get("market_expression", {})
    return {
        "catalyst_class": catalyst,
        "entry_logic_summary": (
            "Watch for the source recipe leading market expression before price confirmation; "
            "later modules must verify source quorum, Akber quality, shadow replay, and router state."
        ),
        "exit_logic_summary": (
            "Exit concept would be catalyst resolution, failed confirmation, invalidation, "
            "time-window expiry, or later risk stop; no exit order is created here."
        ),
        "invalidation_logic_summary": _invalidation_concept(pattern)["summary"],
        "time_horizon": market.get("horizon") or "unknown",
        "no_trade_conditions": [
            "source quorum missing",
            "market already repriced",
            "duplicate exposure conflict",
            "quantum ambiguity hold",
            "paper route unavailable",
            "Akber filter not run",
            "shadow replay not run",
        ],
        "required_gates": [
            "source_quorum",
            "source_freshness",
            "strategy_lead_challenge",
            "akber_filter_review",
            "shadow_replay",
            "strategy_router",
            "risk_budget",
            "duplicate_exposure_check",
            "daily_drawdown_check",
            "paperops_gate_interface",
            "guarded_alpaca_paper_route",
        ],
    }


def _evidence(pattern: dict[str, Any], quantum_review: dict[str, Any] | None) -> dict[str, Any]:
    tests = pattern.get("nonlinear_tests", {})
    baseline = pattern.get("baseline", {})
    sample = pattern.get("sample", {})
    scores = quantum_review.get("scores", {}) if quantum_review else {}
    return {
        "historical_sample_size": sample.get("complete_forward_outcome_count", 0),
        "linear_score": baseline.get("linear_score"),
        "linear_status": baseline.get("linear_status"),
        "nonlinear_score": tests.get("nonlinear_score"),
        "nonlinear_baseline_beaten": tests.get("linear_baseline_beaten") is True,
        "quantum_ambiguity_score": scores.get("ambiguity_score"),
        "quantum_recommendation": quantum_review.get("recommendation") if quantum_review else None,
        "walk_forward_survival": tests.get("walk_forward_survival"),
        "factor_control_status": "inherited_from_qsase_5_linear_lab",
        "coverage_score": sample.get("coverage_score"),
        "overfit_risk_score": tests.get("overfit_risk_score"),
        "source_price_lineage_present": True,
    }


def _build_hypothesis(
    pattern: dict[str, Any],
    family_map: dict[str, Any],
    quantum_review: dict[str, Any] | None,
    generated_at: str,
) -> dict[str, Any]:
    family_key = family_map.get("mapped_existing_family") or family_map.get("proposed_new_family")
    hypothesis_type = "existing_family_modification" if family_map.get("mapped_existing_family") else "new_strategy_family_candidate"
    catalyst = _catalyst_class(pattern)
    paperability = _paperability(pattern, family_map)
    identity = _candidate_identity(pattern, family_map)
    hypothesis = {
        "schema_version": SCHEMA_VERSION,
        "strategy_hypothesis_id": _strategy_hypothesis_id(pattern["nonlinear_pattern_id"], family_key),
        "generated_at": generated_at,
        "status": "strategy_hypothesis_recorded_not_approved",
        "name": _hypothesis_name(family_key, catalyst),
        "hypothesis_type": hypothesis_type,
        "lineage": _lineage(pattern, quantum_review),
        "research_goal_lineage": _research_goal_lineage(pattern, family_key),
        "candidate_identity": identity,
        "source_recipe": {
            "source_families": pattern.get("source_recipe", {}).get("source_families", []),
            "source_names": pattern.get("source_recipe", {}).get("source_names", []),
            "required_source_groups": _required_source_groups(pattern, family_key),
            "minimum_source_quorum": 2,
        },
        "market_expression": {
            "primary_instrument": paperability.get("paperable_execution_expression")
            or pattern.get("market_expression", {}).get("instrument"),
            "observed_market_expression": pattern.get("market_expression", {}).get("instrument"),
            "asset_class": pattern.get("market_expression", {}).get("asset_class"),
            "allowed_proxy_set": paperability["allowed_proxy_set"],
            "paperable_execution_expression": paperability.get("paperable_execution_expression"),
            "proxy_review_required": paperability.get("proxy_review_required"),
            "excluded_instruments": [],
            "paper_route_required": True,
        },
        "strategy_logic": _strategy_logic(pattern, catalyst),
        "evidence": _evidence(pattern, quantum_review),
        "family_mapping": {
            "mapped_existing_family": family_map.get("mapped_existing_family"),
            "proposed_new_family": family_map.get("proposed_new_family"),
            "overlaps_existing_families": _overlapping_families(family_map),
            "strategy_collapse_review_required": True,
            "new_family_hypothesis_only": family_map.get("proposed_new_family") is not None,
            "new_family_active": False,
        },
        "paperability": paperability,
        "invalidation_concept": _invalidation_concept(pattern),
        "risk_concept": _risk_concept(pattern),
        "route_readiness": {
            "strategy_router_eligible": True,
            "akber_filter_required": True,
            "akber_filter_prepared": True,
            "akber_filter_passed": False,
            "shadow_replay_required": True,
            "shadow_replay_prepared": True,
            "shadow_replay_executed": False,
            "paperops_gate_required": True,
            "paperops_direct_handoff_allowed": False,
            "paper_review_candidate": paperability["paper_review_candidate"],
            "paper_order_allowed": False,
        },
        "learning_value": {
            "expected_learning_class": f"{catalyst}_hypothesis",
            "what_qadam_would_learn": "Whether this source-price recipe improves future shadow and paper-review selection after downstream gates.",
            "postmortem_questions": [
                "Did the source recipe lead the market?",
                "Did Akber's filter remove false positives?",
                "Did quantum ambiguity correctly hold weak cases?",
            ],
        },
        "authority": _authority_block(),
    }
    for key, value in FOUNDRY_AUTHORITY_FLAGS.items():
        hypothesis[key] = value
    return hypothesis


def _hypothesis_name(family_key: str, catalyst: str) -> str:
    clean = family_key.replace("qsase_", "").replace("_", " ").title()
    return f"{clean} Hypothesis ({catalyst.replace('_', ' ')})"


def _required_source_groups(pattern: dict[str, Any], family_key: str) -> list[str]:
    family = KNOWN_STRATEGY_FAMILIES.get(family_key, {})
    if family.get("source_keywords"):
        return list(family["source_keywords"][:6])
    names = pattern.get("source_recipe", {}).get("source_names", [])
    return list(names[:6])


def _overlapping_families(family_map: dict[str, Any]) -> list[str]:
    scores = family_map.get("all_family_scores", {})
    return [
        family
        for family, score in sorted(scores.items(), key=lambda item: item[1], reverse=True)
        if score > 0
    ][:3]


def _rejection_decision_type(pattern: dict[str, Any], quantum_review: dict[str, Any] | None) -> str:
    if quantum_review and quantum_review.get("review_state") == "quantum_review_passed_for_research":
        if pattern.get("nonlinear_tests", {}).get("linear_baseline_beaten") is not True:
            return "shadow_only_monitor"
    return "rejected_pattern"


def _build_rejection(
    pattern: dict[str, Any],
    family_map: dict[str, Any],
    quantum_review: dict[str, Any] | None,
    generated_at: str,
) -> dict[str, Any]:
    family_key = family_map.get("mapped_existing_family") or family_map.get("proposed_new_family")
    paperability = _paperability(pattern, family_map)
    identity = _candidate_identity(pattern, family_map)
    reasons = _hypothesis_rejection_reasons(pattern, quantum_review, paperability)
    record = {
        "schema_version": SCHEMA_VERSION,
        "rejected_hypothesis_id": _rejected_hypothesis_id(pattern["nonlinear_pattern_id"], family_key),
        "generated_at": generated_at,
        "decision_type": _rejection_decision_type(pattern, quantum_review),
        "source_pattern_id": pattern.get("nonlinear_pattern_id"),
        "source_price_pattern_lineage": _lineage(pattern, quantum_review),
        "research_goal_lineage": _research_goal_lineage(pattern, family_key),
        "strategy_family": {
            "mapped_existing_family": family_map.get("mapped_existing_family"),
            "proposed_new_family": family_map.get("proposed_new_family"),
            "hypothesis_only": True,
            "active_family_created": False,
        },
        "candidate_identity": identity,
        "proposed_hypothesis_type": "existing_family_modification"
        if family_map.get("mapped_existing_family")
        else "new_strategy_family_candidate",
        "rejection_reasons": reasons,
        "evidence_summary": _evidence(pattern, quantum_review),
        "paperability": paperability,
        "risk_concept": _risk_concept(pattern),
        "invalidation_concept": _invalidation_concept(pattern),
        "akber_filter_inputs_prepared": False,
        "akber_filter_passed": False,
        "shadow_replay_inputs_prepared": False,
        "shadow_replay_executed": False,
        "paperops_direct_handoff_allowed": False,
        "retest_allowed": True,
        "retest_condition": _retest_condition(reasons),
        "authority": _authority_block(),
    }
    for key, value in FOUNDRY_AUTHORITY_FLAGS.items():
        record[key] = value
    return record


def _retest_condition(reasons: list[str]) -> str:
    if "nonlinear_not_incremental" in reasons:
        return "Retest only after nonlinear or quantum review shows incremental value over QSASE-5 linear baseline."
    if "quantum_ambiguity_too_high" in reasons:
        return "Retest only after ambiguity falls and quantum review no longer holds the pattern."
    if "instrument_is_observable_or_futures_symbol_not_guarded_paper_route" in reasons:
        return "Retest only after a guarded paperable proxy expression exists."
    if "sample_too_small" in reasons:
        return "Retest only after historical memory adds enough point-in-time forward outcomes."
    return "Retest only after upstream evidence improves and all Foundry validation fields remain specific."


def reject_unfit_strategy_hypotheses(hypotheses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rejected: list[dict[str, Any]] = []
    for hypothesis in hypotheses:
        reasons: list[str] = []
        if hypothesis.get("evidence", {}).get("source_price_lineage_present") is not True:
            reasons.append("missing_source_price_evidence")
        if not hypothesis.get("strategy_logic", {}).get("invalidation_logic_summary"):
            reasons.append("no_clear_invalidation")
        if not hypothesis.get("paperability", {}).get("paper_review_candidate"):
            reasons.append("no_clean_paper_expression")
        if hypothesis.get("authority", {}).get("trade_candidate_created") is not False:
            reasons.append("authority_boundary_violation")
        if reasons:
            rejected.append(
                {
                    "source_pattern_id": hypothesis.get("lineage", {}).get("nonlinear_pattern_ids", [None])[0],
                    "strategy_family": hypothesis.get("family_mapping", {}),
                    "rejection_reasons": sorted(set(reasons)),
                }
            )
    return rejected


def build_strategy_hypotheses(settings: Settings | None = None) -> dict[str, Any]:
    context = _load_context(settings)
    generated_at = _iso(_now())
    patterns = context["nonlinear_results"]
    quantum_by_source = _quantum_reviews_by_source(context["quantum_reviews"])
    existing_families = _known_families_from_context(context)
    family_mappings = map_patterns_to_strategy_families(patterns, existing_families)
    family_by_pattern = {mapping["source_pattern_id"]: mapping for mapping in family_mappings}
    hypotheses: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for pattern in patterns:
        family_map = family_by_pattern.get(pattern.get("nonlinear_pattern_id"), {})
        quantum_review = quantum_by_source.get(str(pattern.get("nonlinear_pattern_id")))
        paperability = _paperability(pattern, family_map)
        if _hypothesis_eligible(pattern, quantum_review, paperability):
            hypotheses.append(_build_hypothesis(pattern, family_map, quantum_review, generated_at))
        else:
            rejected.append(_build_rejection(pattern, family_map, quantum_review, generated_at))
    rejected.extend(
        _rejection_from_unfit_hypothesis(hypothesis, generated_at)
        for hypothesis in reject_unfit_strategy_hypotheses(hypotheses)
    )
    existing_family_match_count = sum(
        1 for hypothesis in hypotheses if hypothesis.get("hypothesis_type") == "existing_family_modification"
    )
    new_family_proposal_count = sum(
        1 for hypothesis in hypotheses if hypothesis.get("hypothesis_type") == "new_strategy_family_candidate"
    )
    shadow_only_monitor_count = sum(1 for record in rejected if record.get("decision_type") == "shadow_only_monitor")
    rejected_pattern_count = len(rejected)
    missing_required_state: list[str] = []
    if not context["nonlinear_lab"]:
        missing_required_state.append("qsase_nonlinear_quantum_pattern_lab_missing")
    if not patterns:
        missing_required_state.append("qsase_nonlinear_pattern_results_missing")
    if not context["quantum_reviews"]:
        missing_required_state.append("qsase_quantum_pattern_reviews_missing")
    if not context["phase4_strategy_universe"]:
        missing_required_state.append("phase4_candidate_strategy_universe_missing")
    degraded_reasons: list[str] = []
    if context["nonlinear_lab"].get("status") != "qsase_nonlinear_quantum_pattern_lab_ready":
        degraded_reasons.append("nonlinear_quantum_lab_degraded")
    if not hypotheses:
        degraded_reasons.append("no_strategy_hypotheses_promoted_current_inputs")
    if rejected:
        degraded_reasons.append("rejected_or_shadow_only_hypotheses_present")
    status = "qsase_strategy_foundry_ready"
    if missing_required_state:
        status = "qsase_strategy_foundry_blocked"
    elif degraded_reasons:
        status = "qsase_strategy_foundry_degraded"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_strategy_foundry",
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "generated_at": generated_at,
        "status": status,
        "public_safe": True,
        "command_disabled": True,
        "paper_only": True,
        "proposal_first": True,
        "research_only": True,
        "input_pattern_count": len(patterns),
        "strategy_hypothesis_count": len(hypotheses),
        "existing_family_match_count": existing_family_match_count,
        "new_family_proposal_count": new_family_proposal_count,
        "strategy_modification_proposal_count": existing_family_match_count,
        "shadow_only_monitor_count": shadow_only_monitor_count,
        "rejected_pattern_count": rejected_pattern_count,
        "paper_review_candidate_count": sum(
            1 for hypothesis in hypotheses if hypothesis.get("route_readiness", {}).get("paper_review_candidate")
        ),
        "akber_filter_inputs_prepared_count": sum(
            1 for hypothesis in hypotheses if hypothesis.get("route_readiness", {}).get("akber_filter_prepared")
        ),
        "shadow_replay_inputs_prepared_count": sum(
            1 for hypothesis in hypotheses if hypothesis.get("route_readiness", {}).get("shadow_replay_prepared")
        ),
        "known_strategy_family_count": len(existing_families),
        "strategy_hypotheses": hypotheses,
        "rejected_strategy_hypotheses": rejected,
        "strategy_family_map": {
            "schema_version": SCHEMA_VERSION,
            "generated_at": generated_at,
            "known_families": existing_families,
            "pattern_family_mappings": family_mappings,
            "existing_family_mapping_count": sum(1 for mapping in family_mappings if mapping.get("mapped_existing_family")),
            "new_family_candidate_mapping_count": sum(1 for mapping in family_mappings if mapping.get("proposed_new_family")),
            "new_family_active_count": 0,
        },
        "input_artifacts": {
            "nonlinear_lab": f"data/runtime/{NONLINEAR_LAB_ARTIFACT}",
            "nonlinear_results": f"data/runtime/{NONLINEAR_RESULTS_ARTIFACT}",
            "quantum_reviews": f"data/runtime/{QUANTUM_REVIEWS_ARTIFACT}",
            "linear_lab": f"data/runtime/{LINEAR_LAB_ARTIFACT}",
            "linear_results": f"data/runtime/{LINEAR_RESULTS_ARTIFACT}",
            "full_universe_pattern_search": f"data/runtime/{FULL_UNIVERSE_ARTIFACT}",
            "phase4_strategy_universe": f"data/runtime/{PHASE4_STRATEGY_UNIVERSE_ARTIFACT}",
            "strategy_research_intake_present": bool(context["strategy_research_intake"]),
            "strategy_update_record_present": bool(context["strategy_update_record"]),
            "shadow_replay_present": bool(context["shadow_replay"]),
            "paperops_summary_present": bool(context["paperops_summary"]),
        },
        "missing_required_state": missing_required_state,
        "degraded_reasons": sorted(set(degraded_reasons)),
        "strategy_hypotheses_path": f"data/runtime/{HYPOTHESES_ARTIFACT}",
        "rejected_strategy_hypotheses_path": f"data/runtime/{REJECTED_HYPOTHESES_ARTIFACT}",
        "strategy_family_map_path": f"data/runtime/{FAMILY_MAP_ARTIFACT}",
        "strategy_hypotheses_are_not_trades": True,
        "strategy_hypotheses_are_not_qualified_setups": True,
        "strategy_hypotheses_are_not_orders": True,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "trade_candidate_created": False,
        "qualified_setup_created": False,
        "risk_handoff_allowed": False,
        "broker_write_allowed": False,
        "paper_growth_trial_calendar_advanced": False,
        "paper_proof_ledger_credit_granted": False,
        "authority": universal_authority_flags(),
        "authority_flags": dict(FOUNDRY_AUTHORITY_FLAGS),
    }
    payload["dashboard_safe_summary"] = _dashboard_summary(payload)
    return payload


def _rejection_from_unfit_hypothesis(hypothesis_rejection: dict[str, Any], generated_at: str) -> dict[str, Any]:
    source_pattern_id = hypothesis_rejection.get("source_pattern_id") or "unknown"
    family = hypothesis_rejection.get("strategy_family", {})
    family_key = family.get("mapped_existing_family") or family.get("proposed_new_family") or "unknown"
    record = {
        "schema_version": SCHEMA_VERSION,
        "rejected_hypothesis_id": _rejected_hypothesis_id(source_pattern_id, family_key),
        "generated_at": generated_at,
        "decision_type": "rejected_pattern",
        "source_pattern_id": source_pattern_id,
        "strategy_family": family,
        "candidate_identity": {
            "candidate_identity_key": _candidate_identity_key([source_pattern_id, family_key, "unfit"]),
            "identity_type": "strategy_hypothesis_identity_not_trade_candidate",
        },
        "rejection_reasons": hypothesis_rejection.get("rejection_reasons", ["unfit_hypothesis"]),
        "evidence_summary": {"source_price_lineage_present": False},
        "paperability": {"paper_review_candidate": False, "paper_order_allowed": False},
        "retest_allowed": True,
        "retest_condition": "Retest only after Foundry validation failures are repaired.",
        "authority": _authority_block(),
    }
    for key, value in FOUNDRY_AUTHORITY_FLAGS.items():
        record[key] = value
    return record


def load_strategy_hypotheses(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    payload = _read_json(runtime / PRIMARY_ARTIFACT)
    if payload:
        payload["strategy_hypotheses"] = _read_jsonl(runtime / HYPOTHESES_ARTIFACT)
        payload["rejected_strategy_hypotheses"] = _read_jsonl(runtime / REJECTED_HYPOTHESES_ARTIFACT)
        family_map = _read_json(runtime / FAMILY_MAP_ARTIFACT)
        if family_map:
            payload["strategy_family_map"] = family_map
    return payload


def _validate_authority(flags: dict[str, Any], prefix: str) -> list[str]:
    errors: list[str] = []
    for key, expected in FOUNDRY_AUTHORITY_FLAGS.items():
        if flags.get(key) is not expected:
            errors.append(f"{prefix}_{key}_must_be_false")
    return errors


def validate_strategy_hypotheses(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("artifact_type") != "qsase_strategy_foundry":
        errors.append("artifact_type_invalid")
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if payload.get("status") not in {
        "qsase_strategy_foundry_ready",
        "qsase_strategy_foundry_degraded",
        "qsase_strategy_foundry_blocked",
    }:
        errors.append("status_invalid")
    if payload.get("public_safe") is not True or payload.get("command_disabled") is not True:
        errors.append("public_safe_command_disabled_required")
    for key in (
        "strategy_hypotheses_are_not_trades",
        "strategy_hypotheses_are_not_qualified_setups",
        "strategy_hypotheses_are_not_orders",
    ):
        if payload.get(key) is not True:
            errors.append(f"{key}_must_be_true")
    for key in (
        "execution_allowed",
        "paper_order_allowed",
        "proof_credit_allowed",
        "live_capital_enabled",
        "trade_candidate_created",
        "qualified_setup_created",
        "risk_handoff_allowed",
        "broker_write_allowed",
        "paper_growth_trial_calendar_advanced",
        "paper_proof_ledger_credit_granted",
    ):
        if payload.get(key) is not False:
            errors.append(f"{key}_must_be_false")
    authority = payload.get("authority", {})
    if not isinstance(authority, dict) or any(value is not False for value in authority.values()):
        errors.append("universal_authority_flags_must_all_be_false")
    errors.extend(_validate_authority(payload.get("authority_flags", {}), "foundry"))
    hypotheses = payload.get("strategy_hypotheses")
    if not isinstance(hypotheses, list):
        errors.append("strategy_hypotheses_missing")
        hypotheses = []
    if payload.get("strategy_hypothesis_count") != len(hypotheses):
        errors.append("strategy_hypothesis_count_mismatch")
    seen_ids: set[str] = set()
    for hypothesis in hypotheses:
        hypothesis_id = hypothesis.get("strategy_hypothesis_id")
        for field in REQUIRED_HYPOTHESIS_FIELDS:
            if field not in hypothesis:
                errors.append(f"strategy_hypothesis_{hypothesis_id}_missing_{field}")
        if hypothesis_id in seen_ids:
            errors.append(f"duplicate_strategy_hypothesis_{hypothesis_id}")
        seen_ids.add(str(hypothesis_id))
        _validate_lineage(hypothesis, hypothesis_id, errors)
        _validate_hypothesis_specifics(hypothesis, hypothesis_id, errors)
        for key in FOUNDRY_AUTHORITY_FLAGS:
            if hypothesis.get(key) is not False:
                errors.append(f"strategy_hypothesis_{hypothesis_id}_{key}_must_be_false")
            if hypothesis.get("authority", {}).get(key) is not False:
                errors.append(f"strategy_hypothesis_{hypothesis_id}_authority_{key}_must_be_false")
    rejections = payload.get("rejected_strategy_hypotheses")
    if not isinstance(rejections, list):
        errors.append("rejected_strategy_hypotheses_missing")
        rejections = []
    if payload.get("rejected_pattern_count") != len(rejections):
        errors.append("rejected_pattern_count_mismatch")
    if payload.get("input_pattern_count", 0) > 0 and not hypotheses and not rejections:
        errors.append("foundry_inputs_without_hypotheses_or_rejections")
    for rejection in rejections:
        reject_id = rejection.get("rejected_hypothesis_id")
        for field in REQUIRED_REJECTION_FIELDS:
            if field not in rejection:
                errors.append(f"rejected_hypothesis_{reject_id}_missing_{field}")
        if not rejection.get("rejection_reasons"):
            errors.append(f"rejected_hypothesis_{reject_id}_missing_rejection_reason")
        if rejection.get("source_price_pattern_lineage", {}).get("source_price_evidence_artifacts") is None:
            errors.append(f"rejected_hypothesis_{reject_id}_missing_source_price_lineage")
        for key in FOUNDRY_AUTHORITY_FLAGS:
            if rejection.get(key) is not False:
                errors.append(f"rejected_hypothesis_{reject_id}_{key}_must_be_false")
            if rejection.get("authority", {}).get(key) is not False:
                errors.append(f"rejected_hypothesis_{reject_id}_authority_{key}_must_be_false")
    family_map = payload.get("strategy_family_map", {})
    if not family_map.get("known_families"):
        errors.append("strategy_family_map_known_families_missing")
    if family_map.get("new_family_active_count") != 0:
        errors.append("new_strategy_family_must_not_be_active")
    summary = payload.get("dashboard_safe_summary", {})
    if summary:
        if summary.get("public_safe") is not True or summary.get("command_disabled") is not True:
            errors.append("dashboard_summary_public_safe_required")
        if summary.get("live_send_allowed") is not False:
            errors.append("dashboard_summary_live_send_must_be_false")
        if summary.get("authority_state") != "strategy_hypothesis_only_no_execution":
            errors.append("dashboard_summary_authority_boundary_required")
    return sorted(set(errors))


def _validate_lineage(hypothesis: dict[str, Any], hypothesis_id: str, errors: list[str]) -> None:
    lineage = hypothesis.get("lineage", {})
    if not lineage.get("source_pattern_ids"):
        errors.append(f"strategy_hypothesis_{hypothesis_id}_source_pattern_lineage_missing")
    if not lineage.get("linear_pattern_ids"):
        errors.append(f"strategy_hypothesis_{hypothesis_id}_linear_lineage_missing")
    if not lineage.get("nonlinear_pattern_ids"):
        errors.append(f"strategy_hypothesis_{hypothesis_id}_nonlinear_lineage_missing")
    if "quantum_review_ids" not in lineage:
        errors.append(f"strategy_hypothesis_{hypothesis_id}_quantum_lineage_missing")
    research_goal = hypothesis.get("research_goal_lineage", {})
    if not research_goal.get("research_goal_id"):
        errors.append(f"strategy_hypothesis_{hypothesis_id}_research_goal_lineage_missing")
    identity = hypothesis.get("candidate_identity", {})
    if not identity.get("candidate_identity_key"):
        errors.append(f"strategy_hypothesis_{hypothesis_id}_candidate_identity_missing")


def _validate_hypothesis_specifics(hypothesis: dict[str, Any], hypothesis_id: str, errors: list[str]) -> None:
    logic = hypothesis.get("strategy_logic", {})
    for key in (
        "catalyst_class",
        "entry_logic_summary",
        "exit_logic_summary",
        "invalidation_logic_summary",
        "no_trade_conditions",
        "required_gates",
    ):
        if not logic.get(key):
            errors.append(f"strategy_hypothesis_{hypothesis_id}_strategy_logic_{key}_missing")
    if not hypothesis.get("market_expression", {}).get("primary_instrument"):
        errors.append(f"strategy_hypothesis_{hypothesis_id}_instrument_mapping_missing")
    if not hypothesis.get("paperability", {}).get("paperability_state"):
        errors.append(f"strategy_hypothesis_{hypothesis_id}_paperability_state_missing")
    if not hypothesis.get("risk_concept", {}).get("risk_shape"):
        errors.append(f"strategy_hypothesis_{hypothesis_id}_risk_concept_missing")
    if not hypothesis.get("invalidation_concept", {}).get("summary"):
        errors.append(f"strategy_hypothesis_{hypothesis_id}_invalidation_concept_missing")
    family = hypothesis.get("family_mapping", {})
    if not (family.get("mapped_existing_family") or family.get("proposed_new_family")):
        errors.append(f"strategy_hypothesis_{hypothesis_id}_strategy_family_missing")
    if family.get("proposed_new_family") and family.get("new_family_active") is not False:
        errors.append(f"strategy_hypothesis_{hypothesis_id}_new_family_must_be_hypothesis_only")
    route = hypothesis.get("route_readiness", {})
    if route.get("akber_filter_prepared") is not True or route.get("akber_filter_passed") is not False:
        errors.append(f"strategy_hypothesis_{hypothesis_id}_akber_filter_boundary_invalid")
    if route.get("shadow_replay_prepared") is not True or route.get("shadow_replay_executed") is not False:
        errors.append(f"strategy_hypothesis_{hypothesis_id}_shadow_replay_boundary_invalid")
    if route.get("paperops_direct_handoff_allowed") is not False:
        errors.append(f"strategy_hypothesis_{hypothesis_id}_direct_paperops_handoff_must_be_false")


def _dashboard_summary(payload: dict[str, Any]) -> dict[str, Any]:
    top_hypothesis = payload["strategy_hypotheses"][0] if payload["strategy_hypotheses"] else {}
    top_rejection = payload["rejected_strategy_hypotheses"][0] if payload["rejected_strategy_hypotheses"] else {}
    latest_blocker = "none"
    if payload.get("missing_required_state"):
        latest_blocker = ",".join(payload["missing_required_state"])
    elif payload.get("degraded_reasons"):
        latest_blocker = ",".join(payload["degraded_reasons"])
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_strategy_foundry_dashboard_summary",
        "generated_at": payload["generated_at"],
        "status": payload["status"],
        "public_safe": True,
        "command_disabled": True,
        "live_send_allowed": False,
        "summary_rows": [
            {"label": "Foundry status", "value": payload["status"]},
            {"label": "Hypotheses", "value": payload["strategy_hypothesis_count"]},
            {"label": "Existing-family matches", "value": payload["existing_family_match_count"]},
            {"label": "New-family proposals", "value": payload["new_family_proposal_count"]},
            {"label": "Rejected records", "value": payload["rejected_pattern_count"]},
            {"label": "Paper-review candidates", "value": payload["paper_review_candidate_count"]},
            {"label": "Authority", "value": "strategy_hypothesis_only_no_execution"},
        ],
        "top_hypothesis": top_hypothesis.get("strategy_hypothesis_id"),
        "top_hypothesis_type": top_hypothesis.get("hypothesis_type"),
        "top_rejection_reason": ",".join(top_rejection.get("rejection_reasons", [])[:3])
        if top_rejection
        else None,
        "required_next_gate": "Akber filter and shadow replay" if top_hypothesis else "upstream evidence repair",
        "latest_blocker": latest_blocker,
        "authority_state": "strategy_hypothesis_only_no_execution",
        "strategy_hypotheses_are_not_trades": True,
        "no_trade_candidates_created": True,
        "no_paper_orders_created": True,
        "no_proof_credit_granted": True,
        "authority_flags_false": all(value is False for value in payload["authority_flags"].values()),
    }


def build_qsase_phase_implementation_status(payload: dict[str, Any]) -> dict[str, Any]:
    runtime_dir = _runtime_dir()
    existing = _read_json(runtime_dir / PHASE_STATUS_ARTIFACT)
    phases = existing.get("phases") if isinstance(existing.get("phases"), dict) else {}
    phases[PHASE_ID] = {
        "name": PHASE_NAME,
        "status": payload["status"],
        "artifact_path": f"data/runtime/{PRIMARY_ARTIFACT}",
        "strategy_hypotheses_path": f"data/runtime/{HYPOTHESES_ARTIFACT}",
        "rejected_strategy_hypotheses_path": f"data/runtime/{REJECTED_HYPOTHESES_ARTIFACT}",
        "strategy_family_map_path": f"data/runtime/{FAMILY_MAP_ARTIFACT}",
        "input_pattern_count": payload["input_pattern_count"],
        "strategy_hypothesis_count": payload["strategy_hypothesis_count"],
        "existing_family_match_count": payload["existing_family_match_count"],
        "new_family_proposal_count": payload["new_family_proposal_count"],
        "strategy_modification_proposal_count": payload["strategy_modification_proposal_count"],
        "shadow_only_monitor_count": payload["shadow_only_monitor_count"],
        "rejected_pattern_count": payload["rejected_pattern_count"],
        "paper_review_candidate_count": payload["paper_review_candidate_count"],
        "paper_only": True,
        "research_only": True,
        "proposal_first": True,
        "public_safe": True,
        "authority_flags_false": True,
        "strategy_hypotheses_are_not_trades": True,
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
        f"## QSASE-7: Strategy Foundry\n\n"
        f"- Generated at: `{payload.get('generated_at')}`\n"
        f"- Status: `{payload.get('status')}`\n"
        f"- Runtime artifact: `data/runtime/{PRIMARY_ARTIFACT}`\n"
        f"- Input patterns: `{payload.get('input_pattern_count')}`\n"
        f"- Strategy hypotheses: `{payload.get('strategy_hypothesis_count')}`\n"
        f"- Shadow-only monitors: `{payload.get('shadow_only_monitor_count')}`\n"
        f"- Rejected hypothesis records: `{payload.get('rejected_pattern_count')}`\n"
        f"- Paper-review candidates: `{payload.get('paper_review_candidate_count')}`\n"
        f"- Safety: strategy hypotheses are not trades, qualified setups, paper orders, broker writes, live capital, or proof credit.\n"
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
    summary.pop("strategy_hypotheses", None)
    summary.pop("rejected_strategy_hypotheses", None)
    summary.pop("strategy_family_map", None)
    return summary


def write_strategy_hypotheses(
    payload: dict[str, Any],
    settings: Settings | None = None,
    *,
    append_history: bool = True,
    append_log: bool = True,
) -> dict[str, str]:
    runtime_dir = _runtime_dir(settings)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "strategy_foundry": runtime_dir / PRIMARY_ARTIFACT,
        "strategy_hypotheses": runtime_dir / HYPOTHESES_ARTIFACT,
        "rejected_strategy_hypotheses": runtime_dir / REJECTED_HYPOTHESES_ARTIFACT,
        "strategy_family_map": runtime_dir / FAMILY_MAP_ARTIFACT,
        "dashboard_summary": runtime_dir / DASHBOARD_SUMMARY_ARTIFACT,
        "phase_status": runtime_dir / PHASE_STATUS_ARTIFACT,
    }
    _write_json(paths["strategy_foundry"], _summary_without_records(payload))
    _write_jsonl(paths["strategy_hypotheses"], payload["strategy_hypotheses"])
    _write_jsonl(paths["rejected_strategy_hypotheses"], payload["rejected_strategy_hypotheses"])
    _write_json(paths["strategy_family_map"], payload["strategy_family_map"])
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
                "input_pattern_count": payload["input_pattern_count"],
                "strategy_hypothesis_count": payload["strategy_hypothesis_count"],
                "shadow_only_monitor_count": payload["shadow_only_monitor_count"],
                "rejected_pattern_count": payload["rejected_pattern_count"],
                "paper_review_candidate_count": payload["paper_review_candidate_count"],
                "no_trade_candidates_created": True,
            },
        )
        _append_jsonl(
            events_path,
            {
                "generated_at": payload["generated_at"],
                "event_type": "qsase_strategy_foundry_written",
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


def build_and_write_strategy_hypotheses(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    payload = build_strategy_hypotheses(settings)
    errors = validate_strategy_hypotheses(payload)
    written = write_strategy_hypotheses(payload, settings)
    return payload, written, errors


def validate_negative_strategy_foundry_probes() -> list[str]:
    base = build_strategy_hypotheses()
    errors: list[str] = []
    for flag in FOUNDRY_AUTHORITY_FLAGS:
        probe = copy.deepcopy(base)
        probe["authority_flags"][flag] = True
        if not any(flag in error for error in validate_strategy_hypotheses(probe)):
            errors.append(f"negative_probe_failed_for_{flag}")
    order_probe = copy.deepcopy(base)
    order_probe["paper_order_allowed"] = True
    if not any("paper_order_allowed" in error for error in validate_strategy_hypotheses(order_probe)):
        errors.append("negative_probe_failed_for_order_authority")
    if base["rejected_strategy_hypotheses"]:
        reject_probe = copy.deepcopy(base)
        reject_probe["rejected_strategy_hypotheses"][0]["rejection_reasons"] = []
        if not any("missing_rejection_reason" in error for error in validate_strategy_hypotheses(reject_probe)):
            errors.append("negative_probe_failed_for_rejection_reason")
    synthetic = copy.deepcopy(base)
    synthetic_hypothesis = _synthetic_invalid_hypothesis(base)
    synthetic["strategy_hypotheses"] = [synthetic_hypothesis]
    synthetic["strategy_hypothesis_count"] = 1
    if not any("source_pattern_lineage_missing" in error for error in validate_strategy_hypotheses(synthetic)):
        errors.append("negative_probe_failed_for_missing_source_lineage")
    return errors


def _synthetic_invalid_hypothesis(base: dict[str, Any]) -> dict[str, Any]:
    generated_at = base.get("generated_at", _iso(_now()))
    hypothesis = {
        "schema_version": SCHEMA_VERSION,
        "strategy_hypothesis_id": "synthetic-invalid-hypothesis",
        "generated_at": generated_at,
        "status": "strategy_hypothesis_recorded_not_approved",
        "name": "Synthetic Invalid Hypothesis",
        "hypothesis_type": "new_strategy_family_candidate",
        "lineage": {
            "source_pattern_ids": [],
            "linear_pattern_ids": [],
            "nonlinear_pattern_ids": [],
            "quantum_review_ids": [],
        },
        "research_goal_lineage": {"research_goal_id": "synthetic"},
        "candidate_identity": {"candidate_identity_key": "synthetic"},
        "source_recipe": {"source_families": [], "source_names": [], "required_source_groups": [], "minimum_source_quorum": 2},
        "market_expression": {"primary_instrument": None, "asset_class": None, "allowed_proxy_set": [], "paper_route_required": True},
        "strategy_logic": {},
        "evidence": {"source_price_lineage_present": False},
        "family_mapping": {"proposed_new_family": "synthetic", "new_family_active": True},
        "paperability": {"paperability_state": None, "paper_review_candidate": False, "paper_order_allowed": False},
        "invalidation_concept": {},
        "risk_concept": {},
        "route_readiness": {"akber_filter_prepared": False, "akber_filter_passed": False},
        "learning_value": {},
        "authority": _authority_block(),
    }
    for key, value in FOUNDRY_AUTHORITY_FLAGS.items():
        hypothesis[key] = value
    return hypothesis


if __name__ == "__main__":
    artifact = build_strategy_hypotheses()
    print(_json_dump(_summary_without_records(artifact)))
