"""QSASE evidence quality engine.

This module connects the existing QSASE research stack into one fail-closed
tradeability assessment. It does not create trade candidates, approvals,
orders, broker writes, proof credit, live-capital authority, or Telegram
commands. Its job is to say whether the evidence is strong enough for the
existing Router and guarded PaperOps route to consider a setup.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qsase_governance_safety_contract import universal_authority_flags

SCHEMA_VERSION = "qsase_evidence_quality_engine.v1"
ARTIFACT_TYPE = "qsase_evidence_quality_engine"

PRIMARY_ARTIFACT = "qsase_evidence_quality_engine.json"
RECORDS_ARTIFACT = "qsase_evidence_quality_records.jsonl"
DASHBOARD_SUMMARY_ARTIFACT = "qsase_evidence_quality_dashboard_summary.json"
HISTORY_ARTIFACT = "qsase_evidence_quality_history.jsonl"
EVENTS_ARTIFACT = "qsase_evidence_quality_events.jsonl"

SOURCE_UNIVERSE_ARTIFACT = "qsase_source_universe.json"
SOURCE_NETWORK_ARTIFACT = "qsase_dashboard_source_network.json"
UNIVERSAL_MATRIX_ARTIFACT = "qsase_universal_source_price_matrix.json"
SOURCE_PRICE_EDGES_ARTIFACT = "qsase_source_price_edges.jsonl"
TRADING_UNIVERSE_ARTIFACT = "qsase_trading_universe.json"
HISTORICAL_MEMORY_ARTIFACT = "qsase_historical_source_price_memory.json"
HISTORICAL_MEMORY_JSONL_ARTIFACT = "qsase_historical_source_price_memory.jsonl"
HISTORICAL_COVERAGE_ARTIFACT = "qsase_historical_coverage_map.json"
HISTORICAL_MISSING_WINDOWS_ARTIFACT = "qsase_historical_missing_windows.jsonl"
PATTERN_ENGINE_ARTIFACT = "pattern_recognition_engine.json"
EDGE_PATTERN_LEDGER_ARTIFACT = "edge_pattern_ledger.json"
LINEAR_LAB_ARTIFACT = "qsase_linear_pattern_lab.json"
LINEAR_RESULTS_ARTIFACT = "qsase_linear_backtest_results.jsonl"
NONLINEAR_LAB_ARTIFACT = "qsase_nonlinear_quantum_pattern_lab.json"
NONLINEAR_RESULTS_ARTIFACT = "qsase_nonlinear_pattern_results.jsonl"
QUANTUM_REVIEWS_ARTIFACT = "qsase_quantum_pattern_reviews.jsonl"
STRATEGY_FOUNDRY_ARTIFACT = "qsase_strategy_hypotheses.json"
STRATEGY_HYPOTHESES_ARTIFACT = "qsase_strategy_hypotheses.jsonl"
REJECTED_STRATEGY_HYPOTHESES_ARTIFACT = "qsase_rejected_strategy_hypotheses.jsonl"
AKBER_FILTER_ARTIFACT = "qsase_akber_filter_integration.json"
AKBER_FILTER_RESULTS_ARTIFACT = "qsase_akber_filter_results.jsonl"
SHADOW_SIMULATOR_ARTIFACT = "qsase_shadow_strategy_simulator.json"
SHADOW_RESULTS_ARTIFACT = "qsase_shadow_strategy_results.jsonl"
ROUTER_ARTIFACT = "qsase_strategy_router_decisions.json"
ROUTER_DECISIONS_ARTIFACT = "qsase_strategy_router_decisions.jsonl"
WHY_NOT_TRADING_ARTIFACT = "qsase_why_not_trading_now.json"
PAPEROPS_GATE_ARTIFACT = "qsase_paperops_gate_interface.json"
PAPEROPS_GATE_RECORDS_ARTIFACT = "qsase_paperops_gate_interface.jsonl"
PAPEROPS_SUMMARY_ARTIFACT = "paperops_autonomous_pass_summary.json"
COMPONENT_ATTRIBUTION_ARTIFACT = "qsase_component_attribution_ledger.json"
COMPONENT_ATTRIBUTION_RECORDS_ARTIFACT = "qsase_component_attribution_ledger.jsonl"
TELEGRAM_MESSAGE_CANDIDATES_ARTIFACT = "qsase_telegram_message_candidates.json"
TELEGRAM_COMMUNICATIONS_MIRROR_ARTIFACT = "qsase_telegram_dashboard_communications_mirror.json"

TRADEABILITY_STATES = {
    "paper_review_candidate",
    "hold_missing_akber_inputs",
    "hold_missing_historical_forward_windows",
    "hold_unvalidated_edge",
    "shadow_only",
    "research_only",
    "repair_needed",
    "blocked_safety_boundary",
}

REQUIRED_RECORD_FIELDS = (
    "evidence_quality_id",
    "tradeability_state",
    "detected_signal",
    "market_affected",
    "evidence_chain",
    "what_qadam_thinks",
    "what_would_confirm",
    "what_blocks_trade",
    "next_action",
    "scores",
    "authority",
)

EVIDENCE_AUTHORITY_FLAGS = {
    "evidence_quality_review_only": True,
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
    "paper_order_created_count": 0,
    "broker_write_allowed": False,
    "broker_write_count": 0,
    "live_broker_endpoint_allowed": False,
    "paperops_direct_call_allowed": False,
    "paperops_handoff_created": False,
    "paperops_bypass_allowed": False,
    "qctrl_bypass_allowed": False,
    "proof_credit_allowed": False,
    "paper_proof_ledger_credit_allowed": False,
    "paper_growth_trial_calendar_advance_allowed": False,
    "simulated_elapsed_time_allowed": False,
    "strategy_mutation_allowed": False,
    "strategy_mutation_created": False,
    "source_trust_update_allowed": False,
    "source_trust_update_created": False,
    "model_weight_update_allowed": False,
    "model_weight_update_created": False,
    "filter_threshold_update_allowed": False,
    "filter_threshold_update_created": False,
    "telegram_command_path_enabled": False,
    "telegram_trade_command_enabled": False,
    "live_capital_enabled": False,
}

FALSE_AUTHORITY_FIELDS = {
    key for key, value in EVIDENCE_AUTHORITY_FLAGS.items() if value is False
}


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


def _artifact_ref(filename: str, fragment: str | None = None) -> str:
    ref = f"data/runtime/{filename}"
    return f"{ref}#{fragment}" if fragment else ref


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


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


def _int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return default
    return default


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _first_text(*values: Any, default: str = "") -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
        if value not in (None, "", [], {}):
            return str(value)
    return default


def _slug(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")


def _authority_block() -> dict[str, Any]:
    return {
        "review_only": True,
        "not_trade_candidate": True,
        "not_order": True,
        "not_proof_credit": True,
        **EVIDENCE_AUTHORITY_FLAGS,
    }


def _load_context(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "runtime_dir": runtime,
        "source_universe": _read_json(runtime / SOURCE_UNIVERSE_ARTIFACT),
        "source_network": _read_json(runtime / SOURCE_NETWORK_ARTIFACT),
        "universal_matrix": _read_json(runtime / UNIVERSAL_MATRIX_ARTIFACT),
        "source_price_edges": _read_jsonl(runtime / SOURCE_PRICE_EDGES_ARTIFACT, limit=5000),
        "trading_universe": _read_json(runtime / TRADING_UNIVERSE_ARTIFACT),
        "historical_memory": _read_json(runtime / HISTORICAL_MEMORY_ARTIFACT),
        "historical_records": _read_jsonl(runtime / HISTORICAL_MEMORY_JSONL_ARTIFACT, limit=8000),
        "historical_coverage": _read_json(runtime / HISTORICAL_COVERAGE_ARTIFACT),
        "historical_missing_windows": _read_jsonl(runtime / HISTORICAL_MISSING_WINDOWS_ARTIFACT, limit=8000),
        "pattern_engine": _read_json(runtime / PATTERN_ENGINE_ARTIFACT),
        "edge_pattern_ledger": _read_json(runtime / EDGE_PATTERN_LEDGER_ARTIFACT),
        "linear_lab": _read_json(runtime / LINEAR_LAB_ARTIFACT),
        "linear_results": _read_jsonl(runtime / LINEAR_RESULTS_ARTIFACT, limit=500),
        "nonlinear_lab": _read_json(runtime / NONLINEAR_LAB_ARTIFACT),
        "nonlinear_results": _read_jsonl(runtime / NONLINEAR_RESULTS_ARTIFACT, limit=500),
        "quantum_reviews": _read_jsonl(runtime / QUANTUM_REVIEWS_ARTIFACT, limit=500),
        "strategy_foundry": _read_json(runtime / STRATEGY_FOUNDRY_ARTIFACT),
        "strategy_hypotheses": _read_jsonl(runtime / STRATEGY_HYPOTHESES_ARTIFACT, limit=500),
        "rejected_strategy_hypotheses": _read_jsonl(runtime / REJECTED_STRATEGY_HYPOTHESES_ARTIFACT, limit=500),
        "akber_filter": _read_json(runtime / AKBER_FILTER_ARTIFACT),
        "akber_results": _read_jsonl(runtime / AKBER_FILTER_RESULTS_ARTIFACT, limit=500),
        "shadow_simulator": _read_json(runtime / SHADOW_SIMULATOR_ARTIFACT),
        "shadow_results": _read_jsonl(runtime / SHADOW_RESULTS_ARTIFACT, limit=1000),
        "router": _read_json(runtime / ROUTER_ARTIFACT),
        "router_decisions": _read_jsonl(runtime / ROUTER_DECISIONS_ARTIFACT, limit=1000),
        "why_not_trading": _read_json(runtime / WHY_NOT_TRADING_ARTIFACT),
        "paperops_gate": _read_json(runtime / PAPEROPS_GATE_ARTIFACT),
        "paperops_gate_records": _read_jsonl(runtime / PAPEROPS_GATE_RECORDS_ARTIFACT, limit=500),
        "paperops_summary": _read_json(runtime / PAPEROPS_SUMMARY_ARTIFACT),
        "learning_ledger": _read_json(runtime / COMPONENT_ATTRIBUTION_ARTIFACT),
        "learning_records": _read_jsonl(runtime / COMPONENT_ATTRIBUTION_RECORDS_ARTIFACT, limit=1000),
        "telegram_message_candidates": _read_json(runtime / TELEGRAM_MESSAGE_CANDIDATES_ARTIFACT),
        "telegram_mirror": _read_json(runtime / TELEGRAM_COMMUNICATIONS_MIRROR_ARTIFACT),
    }


def _source_rows(context: dict[str, Any]) -> list[dict[str, Any]]:
    source_rows = _safe_list(context.get("source_universe", {}).get("sources"))
    if source_rows:
        return [row for row in source_rows if isinstance(row, dict)]
    source_rows = _safe_list(context.get("source_network", {}).get("source_rows"))
    if source_rows:
        return [row for row in source_rows if isinstance(row, dict)]
    return [row for row in _safe_list(context.get("source_network", {}).get("sources")) if isinstance(row, dict)]


def _source_reliability(context: dict[str, Any]) -> dict[str, Any]:
    rows = _source_rows(context)
    by_family: dict[str, Counter[str]] = defaultdict(Counter)
    trust_scores: list[float] = []
    fresh_count = 0
    quorum_count = 0
    degraded_count = 0
    credential_gated_count = 0
    for row in rows:
        family = _first_text(row.get("source_family"), row.get("family"), row.get("source_pipeline"), default="unknown")
        freshness = _slug(row.get("freshness_status") or row.get("state"))
        state = _slug(row.get("state") or row.get("adapter_status"))
        by_family[family]["source_count"] += 1
        if freshness in {"fresh", "recent", "online"}:
            fresh_count += 1
            by_family[family]["fresh_count"] += 1
        if state in {"degraded", "offline", "blocked", "error"} or freshness in {"stale", "missing"}:
            degraded_count += 1
            by_family[family]["degraded_count"] += 1
        quorum = row.get("quorum_contribution")
        if quorum is None:
            quorum = row.get("source_quorum_contribution", {}).get("can_contribute")
        if quorum is True:
            quorum_count += 1
            by_family[family]["quorum_contributing_count"] += 1
        if row.get("credential_gated") is True:
            credential_gated_count += 1
            by_family[family]["credential_gated_count"] += 1
        trust_scores.append(_float(row.get("trust_score"), 0.0))
    source_count = len(rows)
    avg_trust = round(sum(trust_scores) / len(trust_scores), 4) if trust_scores else 0.0
    freshness_ratio = round(fresh_count / source_count, 4) if source_count else 0.0
    quorum_ratio = round(quorum_count / source_count, 4) if source_count else 0.0
    return {
        "status": "source_reliability_ready" if source_count else "source_reliability_missing",
        "source_count": source_count,
        "fresh_source_count": fresh_count,
        "degraded_source_count": degraded_count,
        "credential_gated_source_count": credential_gated_count,
        "source_quorum_contributing_count": quorum_count,
        "freshness_ratio": freshness_ratio,
        "quorum_ratio": quorum_ratio,
        "average_trust_score": avg_trust,
        "category_count": len(by_family),
        "category_rows": [
            {
                "family": family,
                "source_count": counts.get("source_count", 0),
                "fresh_count": counts.get("fresh_count", 0),
                "quorum_contributing_count": counts.get("quorum_contributing_count", 0),
                "degraded_count": counts.get("degraded_count", 0),
                "credential_gated_count": counts.get("credential_gated_count", 0),
            }
            for family, counts in sorted(by_family.items())
        ],
    }


def _forward_outcome_available(record: dict[str, Any]) -> bool:
    outcomes = _safe_dict(record.get("forward_outcomes"))
    if outcomes.get("outcome_available") is True:
        return True
    non_null_fields = (
        "price_after",
        "return_pre_event_baseline",
        "max_adverse_excursion",
        "max_favorable_excursion",
        "benchmark_relative_return",
        "sector_relative_return",
        "volatility_change",
        "volume_change",
    )
    return any(outcomes.get(field) is not None for field in non_null_fields)


def _historical_memory_health(context: dict[str, Any]) -> dict[str, Any]:
    coverage = context.get("historical_coverage", {})
    memory = context.get("historical_memory", {})
    records = context.get("historical_records", [])
    missing_windows = context.get("historical_missing_windows", [])
    memory_count = _int(
        coverage.get("memory_record_count"),
        _int(memory.get("memory_record_count"), len(records)),
    )
    complete_count = _int(coverage.get("window_complete_record_count"), -1)
    incomplete_count = _int(coverage.get("window_incomplete_record_count"), -1)
    if complete_count < 0:
        complete_count = sum(1 for record in records if _forward_outcome_available(record))
    if incomplete_count < 0:
        incomplete_count = max(0, memory_count - complete_count)
    missing_window_count = len(missing_windows)
    point_safe_count = _int(coverage.get("point_in_time_safe_record_count"), 0)
    leakage_rejected_count = _int(coverage.get("leakage_rejected_record_count"), 0)
    complete_ratio = round(complete_count / memory_count, 4) if memory_count else 0.0
    if leakage_rejected_count:
        state = "leakage_rejected_records_present"
    elif complete_ratio >= 0.7 and memory_count >= 50:
        state = "historical_memory_complete_enough"
    elif memory_count:
        state = "historical_memory_incomplete_forward_windows"
    else:
        state = "historical_memory_missing"
    return {
        "status": state,
        "memory_record_count": memory_count,
        "complete_forward_window_count": complete_count,
        "incomplete_forward_window_count": incomplete_count,
        "missing_window_count": missing_window_count,
        "point_in_time_safe_record_count": point_safe_count,
        "leakage_rejected_record_count": leakage_rejected_count,
        "complete_forward_window_ratio": complete_ratio,
        "point_in_time_safe": leakage_rejected_count == 0 and point_safe_count >= 0,
        "required_next_action": (
            "supply point-in-time historical source and price windows"
            if state in {"historical_memory_incomplete_forward_windows", "historical_memory_missing"}
            else "continue replay coverage monitoring"
        ),
        "artifact_refs": [
            _artifact_ref(HISTORICAL_MEMORY_ARTIFACT),
            _artifact_ref(HISTORICAL_COVERAGE_ARTIFACT),
            _artifact_ref(HISTORICAL_MISSING_WINDOWS_ARTIFACT),
        ],
    }


def _pattern_candidates(context: dict[str, Any]) -> list[dict[str, Any]]:
    engine = context.get("pattern_engine", {})
    candidates = _safe_list(engine.get("candidate_patterns")) or _safe_list(engine.get("patterns"))
    return [row for row in candidates if isinstance(row, dict)]


def _edge_by_sleeve(context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records = {}
    for pattern in _safe_list(context.get("edge_pattern_ledger", {}).get("patterns")):
        if not isinstance(pattern, dict):
            continue
        sleeve = _slug(_first_text(pattern.get("sleeve_key"), pattern.get("label"), pattern.get("market_sleeve")))
        if sleeve:
            records[sleeve] = pattern
    return records


def _row_text_blob(row: dict[str, Any]) -> str:
    chunks: list[str] = []
    for key in (
        "strategy_hypothesis_id",
        "source_pattern_id",
        "name",
        "status",
        "strategy_family",
        "strategy_logic",
        "candidate_identity",
        "market_expression",
        "lineage",
        "research_goal_lineage",
        "telegram_summary",
    ):
        value = row.get(key)
        if isinstance(value, str):
            chunks.append(value)
        elif isinstance(value, dict):
            chunks.append(json.dumps(value, sort_keys=True))
        elif isinstance(value, list):
            chunks.append(" ".join(str(item) for item in value))
    return " ".join(chunks).lower()


def _match_rows(pattern: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sleeve = _slug(_first_text(pattern.get("sleeve_key"), pattern.get("market_sleeve")))
    symbols = {_slug(symbol) for symbol in _safe_list(pattern.get("instrument_symbols"))}
    matches: list[dict[str, Any]] = []
    for row in rows:
        blob = _row_text_blob(row)
        score = 0
        if sleeve and sleeve in blob:
            score += 2
        if any(symbol and symbol in blob for symbol in symbols):
            score += 3
        if score:
            row_copy = copy.deepcopy(row)
            row_copy["_match_score"] = score
            matches.append(row_copy)
    matches.sort(key=lambda row: row.get("_match_score", 0), reverse=True)
    return matches


def _akber_input_state(akber_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not akber_rows:
        return {
            "state": "akber_inputs_missing",
            "passed_count": 0,
            "held_count": 0,
            "rejected_count": 0,
            "missing_input_count": 0,
            "required_inputs": ["volatility context", "pricing gap", "technical confirmation", "volume or flow confirmation", "catalyst strength"],
            "average_akber_score": 0.0,
        }
    passed = sum(1 for row in akber_rows if row.get("decision", {}).get("filter_decision") == "pass")
    held = sum(1 for row in akber_rows if str(row.get("decision", {}).get("filter_decision", "")).startswith("hold"))
    rejected = sum(1 for row in akber_rows if row.get("decision", {}).get("filter_decision") == "reject")
    required_inputs = Counter()
    scores = []
    for row in akber_rows:
        decision = _safe_dict(row.get("decision"))
        for item in _safe_list(decision.get("next_required_evidence")):
            required_inputs[str(item)] += 1
        stage = _safe_dict(row.get("stage_state"))
        for key, value in stage.items():
            if "missing" in str(value):
                required_inputs[key] += 1
        scores.append(_float(row.get("scores", {}).get("akber_filter_score"), 0.0))
    avg_score = round(sum(scores) / len(scores), 4) if scores else 0.0
    state = "akber_inputs_passed" if passed and held == 0 and rejected == 0 else "akber_inputs_incomplete"
    return {
        "state": state,
        "passed_count": passed,
        "held_count": held,
        "rejected_count": rejected,
        "missing_input_count": sum(required_inputs.values()),
        "required_inputs": [item for item, _count in required_inputs.most_common(6)],
        "average_akber_score": avg_score,
    }


def _shadow_state(shadow_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not shadow_rows:
        return {
            "state": "shadow_replay_missing",
            "historical_shadow_count": 0,
            "forward_shadow_count": 0,
            "candidate_for_paper_review_count": 0,
            "average_shadow_score": 0.0,
        }
    historical_count = sum(1 for row in shadow_rows if row.get("evidence_class") == "historical_shadow_research")
    forward_count = sum(1 for row in shadow_rows if row.get("evidence_class") == "forward_shadow_watch")
    candidate_count = sum(1 for row in shadow_rows if row.get("decision", {}).get("candidate_for_paper_review") is True)
    scores = [_float(row.get("scores", {}).get("shadow_variant_score"), 0.0) for row in shadow_rows]
    avg_score = round(sum(scores) / len(scores), 4) if scores else 0.0
    if candidate_count:
        state = "shadow_supports_paper_review"
    elif historical_count and forward_count:
        state = "shadow_replay_watch_only"
    else:
        state = "shadow_replay_partial"
    return {
        "state": state,
        "historical_shadow_count": historical_count,
        "forward_shadow_count": forward_count,
        "candidate_for_paper_review_count": candidate_count,
        "average_shadow_score": avg_score,
    }


def _router_state(router_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not router_rows:
        return {
            "state": "router_missing",
            "paper_review_candidate_count": 0,
            "hold_count": 0,
            "soft_blockers": [],
            "hard_vetoes": [],
            "reason": "Router has not exported a matching decision.",
        }
    paper_review = sum(1 for row in router_rows if row.get("decision", {}).get("paper_review_candidate") is True)
    holds = sum(1 for row in router_rows if row.get("decision", {}).get("router_output") == "hold_missing_evidence")
    soft = Counter()
    hard = Counter()
    for row in router_rows:
        for item in _safe_list(row.get("soft_blockers")):
            soft[str(item)] += 1
        for item in _safe_list(row.get("hard_vetoes")):
            hard[str(item)] += 1
    reason = _first_text(
        router_rows[0].get("decision", {}).get("reason"),
        router_rows[0].get("decision", {}).get("why_not_trading_now"),
        default="Router decision recorded.",
    )
    state = "router_paper_review_candidate" if paper_review else "router_holding_for_evidence"
    if hard:
        state = "router_blocked_by_hard_veto"
    return {
        "state": state,
        "paper_review_candidate_count": paper_review,
        "hold_count": holds,
        "soft_blockers": [item for item, _count in soft.most_common(8)],
        "hard_vetoes": [item for item, _count in hard.most_common(8)],
        "reason": reason,
    }


def _validated_edge_state(pattern: dict[str, Any], edge_record: dict[str, Any] | None) -> dict[str, Any]:
    edge_stage = _first_text((edge_record or {}).get("edge_stage"), default="")
    missing = _safe_list((edge_record or pattern).get("missing_criteria"))
    passed = _safe_list((edge_record or pattern).get("passed_criteria"))
    validated = "validated" in edge_stage and "not_validated" not in edge_stage
    if not edge_record and "thirty_day_persistence" in missing:
        state = "candidate_edge_under_observation"
    elif validated:
        state = "validated_edge"
    elif missing:
        state = "candidate_edge_missing_persistence"
    else:
        state = "candidate_edge_under_observation"
    return {
        "state": state,
        "validated": validated,
        "edge_stage": edge_stage or state,
        "passed_criteria": passed,
        "missing_criteria": missing,
    }


def _strategy_state(hypothesis_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not hypothesis_rows:
        return {
            "state": "strategy_hypothesis_missing",
            "hypothesis_count": 0,
            "paperability_state": "not_recorded",
            "research_goal_ids": [],
            "candidate_identity_keys": [],
        }
    paperability_states = Counter()
    research_goal_ids: list[str] = []
    candidate_keys: list[str] = []
    for row in hypothesis_rows:
        paperability_states[_first_text(row.get("paperability", {}).get("paperability_state"), default="not_recorded")] += 1
        research_goal_id = _first_text(row.get("research_goal_lineage", {}).get("research_goal_id"))
        if research_goal_id:
            research_goal_ids.append(research_goal_id)
        candidate_key = _first_text(row.get("candidate_identity", {}).get("candidate_identity_key"))
        if candidate_key:
            candidate_keys.append(candidate_key)
    top_state = paperability_states.most_common(1)[0][0] if paperability_states else "not_recorded"
    return {
        "state": "strategy_hypothesis_recorded",
        "hypothesis_count": len(hypothesis_rows),
        "paperability_state": top_state,
        "research_goal_ids": sorted(set(research_goal_ids))[:5],
        "candidate_identity_keys": sorted(set(candidate_keys))[:5],
    }


def _paperops_state(context: dict[str, Any]) -> dict[str, Any]:
    gate = context.get("paperops_gate", {})
    summary = context.get("paperops_summary", {})
    why_not = summary.get("why_not_trading_now", {}) if isinstance(summary.get("why_not_trading_now"), dict) else {}
    return {
        "state": _first_text(gate.get("status"), summary.get("status"), default="paperops_not_recorded"),
        "top_blocking_gate": gate.get("top_blocking_gate"),
        "guarded_alpaca_paper_route_state": gate.get("guarded_alpaca_paper_route_state"),
        "handoff_record_count": _int(gate.get("handoff_record_count"), 0),
        "paper_order_created_count": _int(gate.get("paper_order_created_count"), 0),
        "broker_write_count": _int(gate.get("broker_write_count"), 0),
        "why_not_trading_now": why_not or context.get("why_not_trading", {}),
    }


def _evidence_chain(pattern: dict[str, Any], akber: dict[str, Any], router: dict[str, Any]) -> list[str]:
    source_keys = [str(item) for item in _safe_list(pattern.get("primary_lens_source_keys"))[:5]]
    source_text = " + ".join(source_keys) if source_keys else "connected source packet"
    symbols = ", ".join(str(item) for item in _safe_list(pattern.get("instrument_symbols"))[:4]) or "watched market"
    chain = [
        f"{source_text} -> {symbols}",
        "linear and nonlinear labs reviewed the source-price relationship",
        f"Akber practical filter: {akber.get('state', 'not_recorded')}",
        f"Router state: {router.get('state', 'not_recorded')}",
    ]
    return chain


def _tradeability_state(
    *,
    edge: dict[str, Any],
    historical: dict[str, Any],
    akber: dict[str, Any],
    shadow: dict[str, Any],
    router: dict[str, Any],
    paperops: dict[str, Any],
) -> str:
    if router.get("hard_vetoes"):
        return "blocked_safety_boundary"
    if router.get("paper_review_candidate_count", 0) > 0 and paperops.get("paper_order_created_count", 0) == 0:
        return "paper_review_candidate"
    if not edge.get("validated"):
        return "hold_unvalidated_edge"
    if historical.get("status") in {"historical_memory_incomplete_forward_windows", "historical_memory_missing"}:
        return "hold_missing_historical_forward_windows"
    if akber.get("state") != "akber_inputs_passed":
        return "hold_missing_akber_inputs"
    if shadow.get("candidate_for_paper_review_count", 0) <= 0:
        return "shadow_only"
    return "research_only"


def _score_record(
    pattern: dict[str, Any],
    source_reliability: dict[str, Any],
    historical: dict[str, Any],
    edge: dict[str, Any],
    akber: dict[str, Any],
    shadow: dict[str, Any],
    router: dict[str, Any],
) -> dict[str, float]:
    source_score = _clamp(
        (source_reliability.get("freshness_ratio", 0.0) * 0.5)
        + (source_reliability.get("quorum_ratio", 0.0) * 0.3)
        + (source_reliability.get("average_trust_score", 0.0) * 0.2)
    )
    historical_score = _clamp(historical.get("complete_forward_window_ratio", 0.0))
    pattern_score = _clamp(_float(pattern.get("edge_readiness_score"), 0.0))
    validated_score = 1.0 if edge.get("validated") else 0.35
    akber_score = _clamp(_float(akber.get("average_akber_score"), 0.0))
    shadow_score = _clamp(_float(shadow.get("average_shadow_score"), 0.0))
    router_score = 1.0 if router.get("paper_review_candidate_count", 0) > 0 else 0.35
    quality_score = _clamp(
        source_score * 0.14
        + historical_score * 0.18
        + pattern_score * 0.16
        + validated_score * 0.12
        + akber_score * 0.16
        + shadow_score * 0.12
        + router_score * 0.12
    )
    return {
        "source_reliability_score": round(source_score, 4),
        "historical_completeness_score": round(historical_score, 4),
        "pattern_readiness_score": round(pattern_score, 4),
        "validated_edge_score": round(validated_score, 4),
        "akber_practical_confirmation_score": round(akber_score, 4),
        "shadow_replay_score": round(shadow_score, 4),
        "router_readiness_score": round(router_score, 4),
        "evidence_quality_score": round(quality_score, 4),
    }


def _record_explanation(
    pattern: dict[str, Any],
    tradeability_state: str,
    edge: dict[str, Any],
    historical: dict[str, Any],
    akber: dict[str, Any],
    shadow: dict[str, Any],
    router: dict[str, Any],
) -> dict[str, str]:
    sleeve = _first_text(pattern.get("market_sleeve"), pattern.get("sleeve_key"), default="Watched market")
    symbols = ", ".join(str(item) for item in _safe_list(pattern.get("instrument_symbols"))[:4]) or "mapped instruments"
    detected_signal = _first_text(pattern.get("pattern_question"), default=f"{sleeve} source-price relationship")
    secondary_blockers: list[str] = []
    if historical.get("status") in {"historical_memory_incomplete_forward_windows", "historical_memory_missing"}:
        secondary_blockers.append("historical forward windows are incomplete")
    if akber.get("state") != "akber_inputs_passed":
        missing = ", ".join(akber.get("required_inputs", [])[:3]) or "practical confirmation"
        secondary_blockers.append(f"Akber still needs {missing}")
    if shadow.get("candidate_for_paper_review_count", 0) <= 0:
        secondary_blockers.append("shadow replay has not produced paper-review support")
    secondary_text = f" Also: {'; '.join(secondary_blockers)}." if secondary_blockers else ""
    if tradeability_state == "paper_review_candidate":
        thinks = f"Qadam sees {sleeve} as eligible for guarded paper-trade review, not an order."
        blocks = "No evidence blocker is recorded at the evidence-quality layer; Router and PaperOps still enforce final paper-only gates."
        next_action = "send this setup to the existing guarded Router and PaperOps review path"
    elif tradeability_state == "hold_unvalidated_edge":
        thinks = f"Qadam has a {sleeve} pattern, but it is still an observed research edge rather than a validated edge."
        blocks = (
            "The pattern has not graduated from candidate edge to validated edge; "
            f"it still needs persistence over real elapsed time.{secondary_text}"
        )
        next_action = "continue observation until the edge ledger records validation"
    elif tradeability_state == "hold_missing_historical_forward_windows":
        thinks = f"Qadam sees a possible {sleeve} relationship, but the historical source-price memory is not complete enough."
        blocks = (
            "Point-in-time forward windows are incomplete, so Qadam cannot prove that "
            f"the signal led price often enough.{secondary_text}"
        )
        next_action = "backfill missing point-in-time source and price windows without leakage"
    elif tradeability_state == "hold_missing_akber_inputs":
        missing = ", ".join(akber.get("required_inputs", [])[:4]) or "practical confirmation"
        thinks = f"Qadam sees a possible {sleeve} setup, but Akber's practical filter still needs {missing}."
        blocks = f"Akber is holding for {missing}; this is a quality hold, not an execution failure.{secondary_text}"
        next_action = "collect volatility, technical, volume or flow, pricing-gap, and catalyst-strength confirmation"
    elif tradeability_state == "shadow_only":
        thinks = f"Qadam sees {sleeve} as useful for shadow replay, not paper review yet."
        blocks = f"Shadow replay has not shown enough support for a paper-review candidate.{secondary_text}"
        next_action = "run forward and historical shadow replay variants and attribute the no-order result"
    elif tradeability_state == "blocked_safety_boundary":
        thinks = f"Qadam is refusing to promote {sleeve} because a safety veto exists."
        blocks = ", ".join(router.get("hard_vetoes", [])[:4]) or "hard safety veto"
        next_action = "repair or clear the safety veto before any further promotion"
    else:
        thinks = f"Qadam is treating {sleeve} as research-only until more evidence arrives."
        blocks = router.get("reason") or "Evidence is incomplete."
        next_action = "continue research and attribution without creating an order"
    return {
        "detected_signal": detected_signal,
        "market_affected": f"{sleeve} ({symbols})",
        "what_qadam_thinks": thinks,
        "what_would_confirm": (
            "A validated edge, complete point-in-time forward windows, Akber practical confirmation, "
            "supportive shadow replay, and a Router paper-review decision."
        ),
        "what_blocks_trade": blocks,
        "next_action": next_action,
        "edge_blocker": ", ".join(edge.get("missing_criteria", [])[:4]) or "none",
        "historical_blocker": historical.get("required_next_action", "none"),
        "router_blocker": router.get("reason", "none"),
    }


def _build_records(
    context: dict[str, Any],
    generated_at: str,
    source_reliability: dict[str, Any],
    historical: dict[str, Any],
    paperops: dict[str, Any],
) -> list[dict[str, Any]]:
    edge_records = _edge_by_sleeve(context)
    patterns = _pattern_candidates(context)
    records: list[dict[str, Any]] = []
    for index, pattern in enumerate(patterns):
        sleeve_key = _slug(_first_text(pattern.get("sleeve_key"), pattern.get("market_sleeve")))
        edge = _validated_edge_state(pattern, edge_records.get(sleeve_key))
        hypothesis_rows = _match_rows(pattern, context.get("strategy_hypotheses", []))
        akber_rows = _match_rows(pattern, context.get("akber_results", []))
        shadow_rows = _match_rows(pattern, context.get("shadow_results", []))
        router_rows = _match_rows(pattern, context.get("router_decisions", []))
        strategy = _strategy_state(hypothesis_rows)
        akber = _akber_input_state(akber_rows or context.get("akber_results", [])[:3])
        shadow = _shadow_state(shadow_rows or context.get("shadow_results", [])[:3])
        router = _router_state(router_rows or context.get("router_decisions", [])[:3])
        tradeability_state = _tradeability_state(
            edge=edge,
            historical=historical,
            akber=akber,
            shadow=shadow,
            router=router,
            paperops=paperops,
        )
        scores = _score_record(pattern, source_reliability, historical, edge, akber, shadow, router)
        explanation = _record_explanation(pattern, tradeability_state, edge, historical, akber, shadow, router)
        record_id = _hash_id(
            [SCHEMA_VERSION, pattern.get("pattern_id"), sleeve_key, tradeability_state],
            "qsase-evidence",
        )
        records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qsase_evidence_quality_record",
                "evidence_quality_id": record_id,
                "generated_at": generated_at,
                "source_pattern_id": pattern.get("pattern_id"),
                "sleeve_key": sleeve_key,
                "market_sleeve": _first_text(pattern.get("market_sleeve"), pattern.get("sleeve_key"), default="Watched market"),
                "instrument_symbols": _safe_list(pattern.get("instrument_symbols")),
                "tradeability_state": tradeability_state,
                "paper_review_candidate": tradeability_state == "paper_review_candidate",
                "research_only": tradeability_state != "paper_review_candidate",
                "detected_signal": explanation["detected_signal"],
                "market_affected": explanation["market_affected"],
                "evidence_chain": _evidence_chain(pattern, akber, router),
                "what_qadam_thinks": explanation["what_qadam_thinks"],
                "what_would_confirm": explanation["what_would_confirm"],
                "what_blocks_trade": explanation["what_blocks_trade"],
                "next_action": explanation["next_action"],
                "source_reliability": source_reliability,
                "historical_memory": historical,
                "validated_edge_state": edge,
                "strategy_foundry_state": strategy,
                "akber_input_state": akber,
                "shadow_replay_state": shadow,
                "router_state": router,
                "paperops_state": paperops,
                "scores": scores,
                "quality_bar": {
                    "fresh_data": source_reliability.get("freshness_ratio", 0.0) >= 0.5,
                    "point_in_time_memory": historical.get("complete_forward_window_ratio", 0.0) >= 0.7,
                    "validated_edge": edge.get("validated") is True,
                    "akber_confirmation": akber.get("state") == "akber_inputs_passed",
                    "shadow_support": shadow.get("candidate_for_paper_review_count", 0) > 0,
                    "router_support": router.get("paper_review_candidate_count", 0) > 0,
                },
                "telegram_note": {
                    "review_only": True,
                    "command_disabled": True,
                    "live_send_allowed": False,
                    "text": (
                        f"Qadam pattern: {explanation['market_affected']}. "
                        f"State: {tradeability_state.replace('_', ' ')}. "
                        f"Blocker: {explanation['what_blocks_trade']}"
                    )[:420],
                },
                "authority": _authority_block(),
                **EVIDENCE_AUTHORITY_FLAGS,
                "artifact_refs": [
                    _artifact_ref(PRIMARY_ARTIFACT, f"records.{index}"),
                    _artifact_ref(PATTERN_ENGINE_ARTIFACT),
                    _artifact_ref(EDGE_PATTERN_LEDGER_ARTIFACT),
                    _artifact_ref(HISTORICAL_MEMORY_ARTIFACT),
                    _artifact_ref(AKBER_FILTER_ARTIFACT),
                    _artifact_ref(SHADOW_SIMULATOR_ARTIFACT),
                    _artifact_ref(ROUTER_ARTIFACT),
                    _artifact_ref(PAPEROPS_GATE_ARTIFACT),
                ],
            }
        )
    records.sort(
        key=lambda row: (
            row.get("tradeability_state") == "paper_review_candidate",
            row.get("scores", {}).get("evidence_quality_score", 0),
        ),
        reverse=True,
    )
    return records


def _summary_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(row.get("tradeability_state") for row in records)
    return {state: counts.get(state, 0) for state in sorted(TRADEABILITY_STATES)}


def _dashboard_summary(payload: dict[str, Any]) -> dict[str, Any]:
    top_record = payload.get("records", [{}])[0] if payload.get("records") else {}
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_evidence_quality_dashboard_summary",
        "generated_at": payload.get("generated_at"),
        "status": payload.get("status"),
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "evidence_record_count": payload.get("evidence_record_count"),
        "paper_review_candidate_count": payload.get("paper_review_candidate_count"),
        "held_for_evidence_count": payload.get("held_for_evidence_count"),
        "validated_edge_count": payload.get("validated_edge_count"),
        "akber_pass_count": payload.get("akber_pass_count"),
        "akber_hold_count": payload.get("akber_hold_count"),
        "historical_complete_forward_window_ratio": payload.get("historical_memory", {}).get("complete_forward_window_ratio"),
        "source_freshness_ratio": payload.get("source_reliability", {}).get("freshness_ratio"),
        "summary": payload.get("summary"),
        "top_pattern": {
            "market_affected": top_record.get("market_affected"),
            "tradeability_state": top_record.get("tradeability_state"),
            "evidence_quality_score": top_record.get("scores", {}).get("evidence_quality_score"),
            "what_blocks_trade": top_record.get("what_blocks_trade"),
            "next_action": top_record.get("next_action"),
        },
        "boundary": payload.get("boundary"),
        "artifact_refs": [_artifact_ref(PRIMARY_ARTIFACT), _artifact_ref(RECORDS_ARTIFACT)],
    }


def build_evidence_quality_engine(settings: Settings | None = None) -> dict[str, Any]:
    context = _load_context(settings)
    generated_at = _iso(_now())
    source_reliability = _source_reliability(context)
    historical = _historical_memory_health(context)
    paperops = _paperops_state(context)
    records = _build_records(context, generated_at, source_reliability, historical, paperops)
    counts = _summary_counts(records)
    paper_review_count = counts.get("paper_review_candidate", 0)
    held_count = sum(count for state, count in counts.items() if state != "paper_review_candidate")
    akber_filter = context.get("akber_filter", {})
    router = context.get("router", {})
    validated_edge_count = _int(context.get("edge_pattern_ledger", {}).get("validated_edge_count"), 0)
    if not records:
        status = "qsase_evidence_quality_missing_pattern_inputs"
    elif paper_review_count:
        status = "qsase_evidence_quality_ready_with_paper_review_candidates"
    else:
        status = "qsase_evidence_quality_ready_with_tradeability_holds"
    summary = (
        f"Qadam evaluated {len(records)} pattern setups for evidence quality. "
        f"{paper_review_count} are paper-review candidates and {held_count} are held for evidence. "
        "The main missing piece is evidence quality, not broker execution."
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": ARTIFACT_TYPE,
        "generated_at": generated_at,
        "status": status,
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "command_disabled": True,
        "proposal_first": True,
        "summary": summary,
        "source_reliability": source_reliability,
        "historical_memory": historical,
        "paperops_state": paperops,
        "router_status": router.get("status"),
        "router_paper_review_candidate_count": _int(router.get("paper_review_candidate_count"), 0),
        "router_hold_count": _int(router.get("hold_count"), 0),
        "akber_status": akber_filter.get("status"),
        "akber_input_record_count": _int(akber_filter.get("input_filter_record_count"), len(context.get("akber_results", []))),
        "akber_pass_count": _int(akber_filter.get("passed_filter_count"), 0),
        "akber_hold_count": _int(akber_filter.get("hold_filter_count"), 0),
        "akber_missing_context_count": _int(akber_filter.get("missing_context_count"), 0),
        "validated_edge_count": validated_edge_count,
        "candidate_pattern_count": len(_pattern_candidates(context)),
        "evidence_record_count": len(records),
        "paper_review_candidate_count": paper_review_count,
        "held_for_evidence_count": held_count,
        "tradeability_state_counts": counts,
        "records": records,
        "human_pipeline": [
            "detected signal",
            "market affected",
            "evidence",
            "what Qadam thinks",
            "what would confirm it",
            "what blocks the trade",
            "next action",
        ],
        "most_important_missing_piece": "fresh point-in-time source-price evidence strong enough for Akber and Router to call a setup tradeable now",
        "no_execution_boundary": {
            "creates_trade_candidates": False,
            "creates_orders": False,
            "writes_brokers": False,
            "grants_proof_credit": False,
            "enables_live_capital": False,
            "advances_30_day_paper_growth_trial": False,
        },
        "authority": universal_authority_flags(),
        "authority_flags": _authority_block(),
        **EVIDENCE_AUTHORITY_FLAGS,
        "boundary": (
            "Evidence quality is review-only. It can explain whether a setup is research-only, held, "
            "shadow-only, or a Router/PaperOps paper-review candidate, but it cannot create orders, "
            "approvals, broker writes, proof credit, Telegram commands, or live capital."
        ),
        "artifact_refs": [
            _artifact_ref(SOURCE_UNIVERSE_ARTIFACT),
            _artifact_ref(HISTORICAL_MEMORY_ARTIFACT),
            _artifact_ref(PATTERN_ENGINE_ARTIFACT),
            _artifact_ref(STRATEGY_FOUNDRY_ARTIFACT),
            _artifact_ref(AKBER_FILTER_ARTIFACT),
            _artifact_ref(SHADOW_SIMULATOR_ARTIFACT),
            _artifact_ref(ROUTER_ARTIFACT),
            _artifact_ref(PAPEROPS_GATE_ARTIFACT),
            _artifact_ref(COMPONENT_ATTRIBUTION_ARTIFACT),
        ],
    }
    payload["dashboard_summary"] = _dashboard_summary(payload)
    return payload


def validate_evidence_quality_engine(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("artifact_type") != ARTIFACT_TYPE:
        errors.append("artifact_type_invalid")
    for field in ("public_safe", "read_only", "paper_only", "command_disabled"):
        if payload.get(field) is not True:
            errors.append(f"{field}_must_be_true")
    for field in FALSE_AUTHORITY_FIELDS:
        if payload.get(field) is not False:
            errors.append(f"{field}_must_be_false")
    if _int(payload.get("paper_order_created_count"), 0) != 0:
        errors.append("paper_order_created_count_must_be_zero")
    if _int(payload.get("broker_write_count"), 0) != 0:
        errors.append("broker_write_count_must_be_zero")
    records = _safe_list(payload.get("records"))
    if payload.get("candidate_pattern_count") and not records:
        errors.append("records_missing_for_candidate_patterns")
    if _int(payload.get("evidence_record_count"), -1) != len(records):
        errors.append("evidence_record_count_mismatch")
    for index, record in enumerate(records):
        record_id = record.get("evidence_quality_id") or f"record_{index}"
        for field in REQUIRED_RECORD_FIELDS:
            if field not in record or record.get(field) in (None, ""):
                errors.append(f"{record_id}_missing_{field}")
        if record.get("tradeability_state") not in TRADEABILITY_STATES:
            errors.append(f"{record_id}_invalid_tradeability_state")
        for field in FALSE_AUTHORITY_FIELDS:
            if record.get(field) is not False:
                errors.append(f"{record_id}_{field}_must_be_false")
        if _safe_dict(record.get("authority")).get("paper_order_created") is not False:
            errors.append(f"{record_id}_authority_paper_order_created_must_be_false")
        if record.get("paper_review_candidate") is True and record.get("tradeability_state") != "paper_review_candidate":
            errors.append(f"{record_id}_paper_review_candidate_state_mismatch")
        telegram = _safe_dict(record.get("telegram_note"))
        if telegram.get("command_disabled") is not True or telegram.get("live_send_allowed") is not False:
            errors.append(f"{record_id}_telegram_boundary_invalid")
    if payload.get("paper_review_candidate_count", 0) and _int(payload.get("router_paper_review_candidate_count"), 0) <= 0:
        errors.append("paper_review_candidate_without_router_candidate")
    historical = _safe_dict(payload.get("historical_memory"))
    if historical.get("leakage_rejected_record_count", 0):
        errors.append("historical_leakage_rejected_records_present")
    return errors


def validate_negative_evidence_quality_probes() -> list[str]:
    base = build_evidence_quality_engine()
    errors: list[str] = []
    order_probe = copy.deepcopy(base)
    order_probe["paper_order_created"] = True
    if not any("paper_order_created" in error for error in validate_evidence_quality_engine(order_probe)):
        errors.append("negative_probe_failed_for_paper_order_created")
    broker_probe = copy.deepcopy(base)
    if broker_probe.get("records"):
        broker_probe["records"][0]["broker_write_allowed"] = True
    if not any("broker_write_allowed" in error for error in validate_evidence_quality_engine(broker_probe)):
        errors.append("negative_probe_failed_for_broker_write_allowed")
    state_probe = copy.deepcopy(base)
    if state_probe.get("records"):
        state_probe["records"][0]["tradeability_state"] = "send_order_now"
    if not any("invalid_tradeability_state" in error for error in validate_evidence_quality_engine(state_probe)):
        errors.append("negative_probe_failed_for_invalid_tradeability_state")
    return errors


def write_evidence_quality_engine(
    payload: dict[str, Any],
    settings: Settings | None = None,
    append_history: bool = True,
) -> dict[str, str]:
    runtime = _runtime_dir(settings)
    paths = {
        "primary": runtime / PRIMARY_ARTIFACT,
        "records": runtime / RECORDS_ARTIFACT,
        "dashboard_summary": runtime / DASHBOARD_SUMMARY_ARTIFACT,
    }
    _write_json(paths["primary"], payload)
    _write_jsonl(paths["records"], [row for row in _safe_list(payload.get("records")) if isinstance(row, dict)])
    _write_json(paths["dashboard_summary"], _dashboard_summary(payload))
    if append_history:
        _append_jsonl(
            runtime / HISTORY_ARTIFACT,
            {
                "generated_at": payload.get("generated_at"),
                "status": payload.get("status"),
                "evidence_record_count": payload.get("evidence_record_count"),
                "paper_review_candidate_count": payload.get("paper_review_candidate_count"),
                "held_for_evidence_count": payload.get("held_for_evidence_count"),
            },
        )
        _append_jsonl(
            runtime / EVENTS_ARTIFACT,
            {
                "generated_at": payload.get("generated_at"),
                "event_type": "qsase_evidence_quality_engine_written",
                "status": payload.get("status"),
                "paper_only": True,
                "paper_order_created_count": 0,
                "broker_write_count": 0,
            },
        )
        paths["history"] = runtime / HISTORY_ARTIFACT
        paths["events"] = runtime / EVENTS_ARTIFACT
    return {key: str(path) for key, path in paths.items()}


def build_and_write_evidence_quality_engine(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    payload = build_evidence_quality_engine(settings)
    errors = validate_evidence_quality_engine(payload)
    written = write_evidence_quality_engine(payload, settings)
    return payload, written, errors


def load_evidence_quality_engine(settings: Settings | None = None) -> dict[str, Any]:
    return _read_json(_runtime_dir(settings) / PRIMARY_ARTIFACT)


if __name__ == "__main__":
    artifact = build_evidence_quality_engine()
    print(_json_dump(artifact))
