"""Router V2 and PaperOps handoff for Qadam next-generation Phase 9.

Router V2 is the boundary between research evidence and the existing guarded
PaperOps route. It assigns one final state per setup and can create PaperOps
handoff context only for clean paper-review candidates. It cannot create
qualified setups, risk approvals, execution approvals, paper orders, broker
writes, live-capital authority, or paper proof ledger credit.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings

SCHEMA_VERSION = "qadam_router_v2_paperops_handoff.v1"
PHASE_ID = "qadam_next_generation_phase_9_router_v2_paperops_handoff"

PRIMARY_ARTIFACT = "qadam_router_v2_paperops_handoff.json"
DECISIONS_ARTIFACT = "qadam_router_v2_decisions.jsonl"
HANDOFF_RECORDS_ARTIFACT = "qadam_paperops_handoff_v2_records.jsonl"
REJECTED_HANDOFFS_ARTIFACT = "qadam_paperops_handoff_v2_rejections.jsonl"
WHY_NOT_TRADING_NOW_ARTIFACT = "qadam_router_v2_why_not_trading_now.json"
SCOREBOARD_ARTIFACT = "qadam_router_v2_scoreboard.json"
DASHBOARD_SUMMARY_ARTIFACT = "qadam_router_v2_dashboard_summary.json"
EVENTS_ARTIFACT = "qadam_router_v2_events.jsonl"

STRATEGY_FOUNDRY_V2_ARTIFACT = "qadam_strategy_foundry_v2.json"
STRATEGY_FOUNDRY_V2_HYPOTHESES_ARTIFACT = "qadam_strategy_foundry_v2_hypotheses.jsonl"
AKBER_FILTER_V2_ARTIFACT = "qadam_akber_filter_v2.json"
AKBER_FILTER_V2_RESULTS_ARTIFACT = "qadam_akber_filter_v2_results.jsonl"
SHADOW_SIMULATOR_V2_ARTIFACT = "qadam_shadow_simulator_v2.json"
SHADOW_HISTORICAL_REPLAY_ARTIFACT = "qadam_shadow_simulator_v2_historical_replay.jsonl"
SHADOW_FORWARD_TRACKING_ARTIFACT = "qadam_shadow_simulator_v2_forward_tracking.jsonl"
SHADOW_COUNTERFACTUAL_NO_ORDER_ARTIFACT = "qadam_shadow_simulator_v2_counterfactual_no_order.jsonl"
LONG_BACKTEST_LOCK_ARTIFACT = "qadam_long_backtest_lock.json"
PAPEROPS_SUMMARY_ARTIFACT = "paperops_autonomous_pass_summary.json"
PAPER_POSITIONS_ARTIFACT = "paper_positions.jsonl"
PAPER_ORDERS_ARTIFACT = "paper_orders.jsonl"

FINAL_STATES = {
    "reject",
    "watchlist",
    "shadow_only",
    "hold",
    "repair_requested",
    "blocked_safety_boundary",
    "paper_review_candidate",
}

OPEN_ORDER_STATUSES = {
    "accepted",
    "new",
    "open",
    "pending_new",
    "partially_filled",
    "submitted",
}

AUTHORITY_FLAGS = {
    "read_only": True,
    "paper_only": True,
    "proposal_first": True,
    "router_decision_only": True,
    "handoff_context_only": True,
    "paper_review_candidate_is_not_order": True,
    "trade_candidate_creation_allowed": False,
    "trade_candidate_created": False,
    "qualified_setup_creation_allowed": False,
    "qualified_setup_created": False,
    "risk_handoff_allowed": False,
    "risk_approval_allowed": False,
    "risk_approval_created": False,
    "execution_allowed": False,
    "execution_approval_allowed": False,
    "execution_approval_created": False,
    "paperops_direct_call_allowed": False,
    "paperops_bypass_allowed": False,
    "paper_order_allowed": False,
    "paper_order_created": False,
    "paper_order_created_count": 0,
    "broker_write_allowed": False,
    "broker_write_count": 0,
    "live_broker_endpoint_allowed": False,
    "live_capital_enabled": False,
    "qctrl_bypass_allowed": False,
    "idempotency_bypass_allowed": False,
    "duplicate_exposure_bypass_allowed": False,
    "daily_drawdown_bypass_allowed": False,
    "source_quorum_bypass_allowed": False,
    "proof_credit_allowed": False,
    "paper_proof_ledger_write_allowed": False,
    "paper_proof_ledger_credit_allowed": False,
    "paper_growth_trial_calendar_advance_allowed": False,
    "paper_growth_trial_calendar_advanced": False,
    "simulated_elapsed_time_allowed": False,
    "strategy_mutation_allowed": False,
    "strategy_mutation_created": False,
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
class RouterV2Bundle:
    primary: dict[str, Any]
    decisions: list[dict[str, Any]]
    handoff_records: list[dict[str, Any]]
    rejected_handoffs: list[dict[str, Any]]
    why_not_trading_now: dict[str, Any]
    scoreboard: dict[str, Any]
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


def _safe_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    try:
        return float(value)
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
        "foundry": _read_json(runtime / STRATEGY_FOUNDRY_V2_ARTIFACT),
        "hypotheses": _read_jsonl(runtime / STRATEGY_FOUNDRY_V2_HYPOTHESES_ARTIFACT),
        "akber": _read_json(runtime / AKBER_FILTER_V2_ARTIFACT),
        "akber_results": _read_jsonl(runtime / AKBER_FILTER_V2_RESULTS_ARTIFACT),
        "shadow": _read_json(runtime / SHADOW_SIMULATOR_V2_ARTIFACT),
        "shadow_historical": _read_jsonl(runtime / SHADOW_HISTORICAL_REPLAY_ARTIFACT),
        "shadow_forward": _read_jsonl(runtime / SHADOW_FORWARD_TRACKING_ARTIFACT),
        "shadow_counterfactual": _read_jsonl(runtime / SHADOW_COUNTERFACTUAL_NO_ORDER_ARTIFACT),
        "lock": _read_json(runtime / LONG_BACKTEST_LOCK_ARTIFACT),
        "paperops": _read_json(runtime / PAPEROPS_SUMMARY_ARTIFACT),
        "paper_positions": _read_jsonl(runtime / PAPER_POSITIONS_ARTIFACT),
        "paper_orders": _read_jsonl(runtime / PAPER_ORDERS_ARTIFACT),
    }


def _index_by(records: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    indexed = {}
    for record in records:
        value = record.get(key)
        if value:
            indexed[str(value)] = record
    return indexed


def _open_exposure_symbols(context: dict[str, Any]) -> set[str]:
    symbols: set[str] = set()
    for position in context.get("paper_positions", []):
        symbol = str(position.get("symbol") or position.get("instrument") or "").upper()
        quantity = _safe_float(position.get("qty") or position.get("quantity") or position.get("position_qty"))
        if symbol and quantity != 0:
            symbols.add(symbol)
    for order in context.get("paper_orders", []):
        status = str(order.get("status") or "").lower()
        symbol = str(order.get("symbol") or order.get("instrument") or "").upper()
        if symbol and status in OPEN_ORDER_STATUSES:
            symbols.add(symbol)
    return symbols


def _long_research_lock_active(lock: dict[str, Any]) -> bool:
    return (
        lock.get("lock_type") == "qadam_next_generation_whole_universe_backfill_backtest"
        and lock.get("status") == "active"
        and lock.get("paperops_watch_only_mode") is True
    )


def _paperops_cycle_state(paperops: dict[str, Any]) -> str:
    states = _safe_dict(paperops.get("states"))
    return str(states.get("paper_ops_cycle_state") or paperops.get("status") or "not_recorded")


def _idempotency_material(hypothesis: dict[str, Any]) -> dict[str, Any]:
    identity = _safe_dict(hypothesis.get("candidate_identity_material"))
    lineage = _safe_dict(hypothesis.get("research_goal_lineage"))
    mapping = _safe_dict(hypothesis.get("instrument_proxy_mapping"))
    key = _hash_id(
        "qadam-paperops-review-v2",
        [
            lineage.get("research_goal_id"),
            hypothesis.get("strategy_hypothesis_id"),
            identity.get("candidate_identity_id"),
            hypothesis.get("strategy_family_id"),
            mapping.get("primary_proxy"),
            identity.get("time_window"),
        ],
    )
    return {
        "idempotency_namespace": "qadam_router_v2_paperops_review",
        "idempotency_key": key,
        "source_idempotency_key": key,
        "candidate_identity_id": identity.get("candidate_identity_id"),
        "research_goal_id": lineage.get("research_goal_id"),
        "not_broker_order_idempotency_key": True,
        "idempotency_material_created_for_handoff_review_only": True,
        "idempotency_override_allowed": False,
    }


def _duplicate_idempotency_counts(materials: list[dict[str, Any]]) -> Counter[str]:
    return Counter(str(item.get("idempotency_key")) for item in materials if item.get("idempotency_key"))


def _source_price_evidence(hypothesis: dict[str, Any]) -> dict[str, Any]:
    evidence = _safe_dict(hypothesis.get("evidence_summary"))
    return {
        "pattern_id": evidence.get("pattern_id"),
        "pattern_rank": evidence.get("pattern_rank"),
        "pattern_lifecycle_state": evidence.get("pattern_lifecycle_state"),
        "expectancy": evidence.get("expectancy"),
        "hit_rate": evidence.get("hit_rate"),
        "sample_count": evidence.get("sample_count"),
        "source_contribution_score": evidence.get("source_contribution_score"),
        "instrument_contribution_score": evidence.get("instrument_contribution_score"),
        "confidence_class": evidence.get("confidence_class"),
        "source_price_evidence_is_research_only": True,
    }


def _global_safety_state(context: dict[str, Any]) -> dict[str, Any]:
    paperops = _safe_dict(context.get("paperops"))
    runtime = _safe_dict(paperops.get("paper_runtime"))
    lock = _safe_dict(context.get("lock"))
    lock_active = _long_research_lock_active(lock)
    return {
        "long_backtest_research_lock_active": lock_active,
        "paperops_watch_only_mode": lock.get("paperops_watch_only_mode") is True,
        "paperops_cycle_state": _paperops_cycle_state(paperops),
        "paperops_idle_reason": runtime.get("idle_reason"),
        "guarded_alpaca_paper_route_state": (
            "watch_only_research_lock_active"
            if lock_active
            else "available_for_existing_paperops_review_only"
        ),
        "qctrl_hold_active": bool(runtime.get("qctrl_consultation_hold_active")),
        "daily_drawdown_breached": bool(runtime.get("daily_drawdown_breached")),
    }


def _router_decision(
    *,
    hypothesis: dict[str, Any],
    akber_result: dict[str, Any],
    shadow_record: dict[str, Any],
    idempotency: dict[str, Any],
    duplicate_idempotency: bool,
    duplicate_exposure: bool,
    open_exposure_symbols: set[str],
    global_safety: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    hypothesis_id = str(hypothesis.get("strategy_hypothesis_id") or "")
    mapping = _safe_dict(hypothesis.get("instrument_proxy_mapping"))
    primary_proxy = str(mapping.get("primary_proxy") or "").upper()
    evidence = _safe_dict(hypothesis.get("evidence_summary"))
    akber_decision = _safe_dict(akber_result.get("decision"))
    akber_filter_decision = str(akber_decision.get("filter_decision") or akber_result.get("status") or "missing")
    missing_akber_context = _safe_int(akber_result.get("critical_missing_context_count") or akber_result.get("missing_context_count"))
    akber_router_eligible = akber_result.get("router_eligible") is True and missing_akber_context == 0
    shadow_present = shadow_record.get("shadow_evidence_present") is True
    shadow_score = _safe_float(shadow_record.get("shadow_score"))
    source_score = _safe_float(evidence.get("source_contribution_score"))
    paperable_proxy_present = bool(primary_proxy)

    hard_vetoes: list[str] = []
    soft_blockers: list[str] = []
    repair_requests: list[str] = []
    if not hypothesis_id:
        repair_requests.append("missing_strategy_hypothesis_id")
    if not shadow_present:
        repair_requests.append("missing_shadow_evidence")
    if not akber_result:
        repair_requests.append("missing_akber_result")
    if akber_filter_decision in {"veto", "akber_v2_veto"}:
        hard_vetoes.append("akber_veto")
    if missing_akber_context:
        soft_blockers.append("akber_practical_confirmation_missing")
    if not akber_router_eligible:
        soft_blockers.append("akber_not_router_eligible")
    if not paperable_proxy_present:
        soft_blockers.append("paperable_proxy_missing")
    if source_score < 0.7:
        soft_blockers.append("source_quorum_research_score_below_review_threshold")
    if shadow_present and shadow_score < 0.45:
        soft_blockers.append("shadow_score_below_router_review_threshold")
    if duplicate_idempotency:
        hard_vetoes.append("duplicate_idempotency_material")
    if duplicate_exposure:
        hard_vetoes.append("duplicate_exposure_conflict")
    if global_safety.get("daily_drawdown_breached"):
        hard_vetoes.append("daily_drawdown_breach")
    if global_safety.get("qctrl_hold_active"):
        hard_vetoes.append("qctrl_paper_consultation_hold")
    if global_safety.get("long_backtest_research_lock_active"):
        soft_blockers.append("long_backtest_research_lock_active")

    if repair_requests:
        final_state = "repair_requested"
    elif "akber_veto" in hard_vetoes:
        final_state = "reject"
    elif hard_vetoes:
        final_state = "blocked_safety_boundary"
    elif missing_akber_context or not akber_router_eligible:
        final_state = "hold"
    elif shadow_present and shadow_score < 0.65:
        final_state = "shadow_only"
    elif global_safety.get("long_backtest_research_lock_active"):
        final_state = "blocked_safety_boundary"
    elif not paperable_proxy_present or source_score < 0.7:
        final_state = "watchlist"
    else:
        final_state = "paper_review_candidate"

    clean_paper_review_candidate = (
        final_state == "paper_review_candidate"
        and not hard_vetoes
        and not soft_blockers
        and not repair_requests
        and akber_router_eligible
        and shadow_present
        and paperable_proxy_present
        and not global_safety.get("long_backtest_research_lock_active")
    )
    final_state_reason = _final_state_reason(final_state, hard_vetoes, soft_blockers, repair_requests)
    router_score = max(
        0.0,
        min(
            1.0,
            0.35 * _safe_float(akber_result.get("scores", {}).get("akber_filter_score"))
            + 0.25 * shadow_score
            + 0.25 * min(source_score, 1.0)
            + 0.15 * _safe_float(evidence.get("hit_rate")),
        ),
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "router_decision_id": _hash_id("qadam-router-v2", [hypothesis_id, idempotency.get("idempotency_key")]),
        "strategy_hypothesis_id": hypothesis_id,
        "generated_at": generated_at,
        "setup_has_exactly_one_final_state": True,
        "final_state": final_state,
        "final_state_reason": final_state_reason,
        "clean_paper_review_candidate": clean_paper_review_candidate,
        "paperops_handoff_allowed": clean_paper_review_candidate,
        "paper_review_candidate_boundary": (
            "clean_candidate_for_existing_guarded_paperops_review_only"
            if clean_paper_review_candidate
            else "not_clean_for_paperops_handoff"
        ),
        "scores": {
            "router_score": round(router_score, 4),
            "akber_filter_score": akber_result.get("scores", {}).get("akber_filter_score"),
            "shadow_score": shadow_score,
            "source_contribution_score": source_score,
        },
        "hard_vetoes": hard_vetoes,
        "soft_blockers": soft_blockers,
        "repair_requests": repair_requests,
        "research_goal_lineage": _safe_dict(hypothesis.get("research_goal_lineage")),
        "candidate_identity": _safe_dict(hypothesis.get("candidate_identity_material")),
        "idempotency_material": idempotency,
        "source_quorum": {
            "state": "research_source_score_available" if source_score >= 0.7 else "source_score_below_review_threshold",
            "source_contribution_score": source_score,
            "source_quorum_bypass_allowed": False,
            "source_quorum_alone_can_create_handoff": False,
        },
        "source_freshness": {
            "state": "requires_fresh_confirmation_before_paperops_submit",
            "missing_akber_context_count": missing_akber_context,
        },
        "source_price_evidence": _source_price_evidence(hypothesis),
        "akber_state": {
            "status": akber_result.get("status"),
            "filter_decision": akber_filter_decision,
            "router_eligible": akber_result.get("router_eligible") is True,
            "critical_missing_context_count": missing_akber_context,
            "akber_pass_is_execution_approval": akber_result.get("akber_filter_pass_is_execution_approval") is True,
        },
        "quantum_classical_state": {
            "verdict": evidence.get("quantum_classical_verdict"),
            "nonlinear_state": evidence.get("nonlinear_state"),
            "qctrl_bypass_allowed": False,
        },
        "risk_state": {
            "risk_budget_required_later": _safe_dict(hypothesis.get("risk_concept_fields")).get("risk_budget_required_later", True),
            "risk_approval_created": False,
            "drawdown_proxy": evidence.get("drawdown_proxy"),
            "daily_drawdown_breached": global_safety.get("daily_drawdown_breached"),
        },
        "duplicate_exposure": {
            "state": "duplicate_exposure_conflict" if duplicate_exposure else "no_duplicate_exposure_conflict_detected",
            "primary_proxy": primary_proxy,
            "open_exposure_symbols": sorted(open_exposure_symbols),
            "duplicate_exposure_override_allowed": False,
        },
        "drawdown_state": {
            "daily_drawdown_breached": global_safety.get("daily_drawdown_breached"),
            "daily_drawdown_bypass_allowed": False,
        },
        "qctrl_hold": {
            "qctrl_hold_active": global_safety.get("qctrl_hold_active"),
            "qctrl_bypass_allowed": False,
        },
        "guarded_alpaca_paper_route": {
            "state": global_safety.get("guarded_alpaca_paper_route_state"),
            "paperops_cycle_state": global_safety.get("paperops_cycle_state"),
            "paperops_watch_only_mode": global_safety.get("paperops_watch_only_mode"),
            "paperops_bypass_allowed": False,
        },
        "paper_order_created": False,
        "qualified_setup_created": False,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "authority": _authority(),
    }


def _final_state_reason(
    final_state: str,
    hard_vetoes: list[str],
    soft_blockers: list[str],
    repair_requests: list[str],
) -> str:
    if repair_requests:
        return "Repair is required before the setup can be routed."
    if hard_vetoes:
        return f"Safety veto blocks routing: {', '.join(hard_vetoes[:3])}."
    if final_state == "hold":
        return "The setup is held because practical confirmation is incomplete."
    if final_state == "shadow_only":
        return "The setup remains in shadow observation because shadow evidence is not strong enough for review."
    if final_state == "watchlist":
        return "The setup is watchlisted until source, proxy, or freshness evidence improves."
    if final_state == "paper_review_candidate":
        return "The setup is clean enough for existing guarded PaperOps review, but this is not an order."
    if soft_blockers:
        return f"Soft blockers remain: {', '.join(soft_blockers[:3])}."
    return "The setup is not ready for PaperOps."


def _handoff_record(decision: dict[str, Any], generated_at: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "paperops_handoff_id": _hash_id("qadam-paperops-handoff-v2", [decision.get("router_decision_id")]),
        "generated_at": generated_at,
        "status": "paperops_handoff_context_only_ready_for_existing_guarded_review",
        "router_decision_id": decision.get("router_decision_id"),
        "strategy_hypothesis_id": decision.get("strategy_hypothesis_id"),
        "research_goal_lineage": decision.get("research_goal_lineage"),
        "candidate_identity": decision.get("candidate_identity"),
        "idempotency_material": decision.get("idempotency_material"),
        "source_quorum": decision.get("source_quorum"),
        "source_freshness": decision.get("source_freshness"),
        "source_price_evidence": decision.get("source_price_evidence"),
        "akber_state": decision.get("akber_state"),
        "quantum_classical_state": decision.get("quantum_classical_state"),
        "risk_state": decision.get("risk_state"),
        "duplicate_exposure": decision.get("duplicate_exposure"),
        "drawdown_state": decision.get("drawdown_state"),
        "qctrl_hold": decision.get("qctrl_hold"),
        "guarded_alpaca_paper_route": decision.get("guarded_alpaca_paper_route"),
        "paper_review_candidate_boundary": decision.get("paper_review_candidate_boundary"),
        "handoff_is_not_qualified_setup": True,
        "handoff_is_not_order": True,
        "paper_order_created": False,
        "qualified_setup_created": False,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "authority": _authority(),
    }


def _rejected_handoff(decision: dict[str, Any], generated_at: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "phase_id": PHASE_ID,
        "rejected_handoff_id": _hash_id("qadam-paperops-handoff-reject-v2", [decision.get("router_decision_id")]),
        "generated_at": generated_at,
        "status": "not_sent_to_paperops",
        "router_decision_id": decision.get("router_decision_id"),
        "strategy_hypothesis_id": decision.get("strategy_hypothesis_id"),
        "final_state": decision.get("final_state"),
        "reason": decision.get("final_state_reason"),
        "hard_vetoes": decision.get("hard_vetoes", []),
        "soft_blockers": decision.get("soft_blockers", []),
        "repair_requests": decision.get("repair_requests", []),
        "paperops_handoff_allowed": False,
        "paper_order_created": False,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "authority": _authority(),
    }


def _why_not(decisions: list[dict[str, Any]], context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    counts = Counter(str(decision.get("final_state") or "unknown") for decision in decisions)
    lock = _safe_dict(context.get("lock"))
    lock_active = _long_research_lock_active(lock)
    all_hold_for_akber = bool(decisions) and all(
        "akber_practical_confirmation_missing" in _safe_list(decision.get("soft_blockers"))
        for decision in decisions
    )
    if counts.get("paper_review_candidate", 0):
        reason = "paper_review_candidates_available_for_existing_guarded_review"
        plain = "Qadam has clean paper-review candidates for the existing guarded PaperOps route."
    elif all_hold_for_akber and lock_active:
        reason = "akber_practical_confirmation_missing_and_research_lock_active"
        plain = "Akber practical confirmation is missing for all setups; the long backtest research lock also keeps PaperOps watch-only."
    elif all_hold_for_akber:
        reason = "akber_practical_confirmation_missing"
        plain = "Akber practical confirmation is missing for all setups."
    elif lock_active:
        reason = "long_backtest_research_lock_active"
        plain = "The long backtest research lock keeps PaperOps watch-only."
    elif not decisions:
        reason = "no_strategy_hypotheses_available"
        plain = "No Strategy Foundry V2 hypotheses are available for Router V2."
    else:
        reason = "no_clean_paper_review_candidate"
        plain = "No setup passed every Router V2 boundary for PaperOps review."
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_router_v2_why_not_trading_now",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "why_not_trading_now_ready",
        "reason": reason,
        "plain_english": plain,
        "final_state_counts": dict(counts),
        "paper_review_candidate_count": counts.get("paper_review_candidate", 0),
        "paperops_watch_only_mode": lock.get("paperops_watch_only_mode") is True,
        "paper_order_created": False,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "authority": _authority(),
    }


def _scoreboard(decisions: list[dict[str, Any]], generated_at: str) -> dict[str, Any]:
    ranked = sorted(decisions, key=lambda item: _safe_float(item.get("scores", {}).get("router_score")), reverse=True)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_router_v2_scoreboard",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "router_v2_scoreboard_ready",
        "ranked_count": len(ranked),
        "rows": [
            {
                "rank": index,
                "router_decision_id": decision.get("router_decision_id"),
                "strategy_hypothesis_id": decision.get("strategy_hypothesis_id"),
                "final_state": decision.get("final_state"),
                "router_score": decision.get("scores", {}).get("router_score"),
                "paperops_handoff_allowed": decision.get("paperops_handoff_allowed"),
                "top_blockers": (decision.get("hard_vetoes") or decision.get("soft_blockers") or decision.get("repair_requests") or [])[:3],
            }
            for index, decision in enumerate(ranked, start=1)
        ],
        "paper_order_created": False,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "authority": _authority(),
    }


def _dashboard_summary(primary: dict[str, Any], decisions: list[dict[str, Any]], why_not: dict[str, Any], generated_at: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_router_v2_dashboard_summary",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": primary.get("status"),
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "setup_count": primary.get("setup_count"),
        "decision_count": primary.get("decision_count"),
        "all_setups_have_exactly_one_final_state": primary.get("all_setups_have_exactly_one_final_state"),
        "paper_review_candidate_count": primary.get("paper_review_candidate_count"),
        "clean_paper_review_candidate_count": primary.get("clean_paper_review_candidate_count"),
        "handoff_record_count": primary.get("handoff_record_count"),
        "rejected_handoff_count": primary.get("rejected_handoff_count"),
        "only_clean_paper_review_candidates_reach_paperops": primary.get("only_clean_paper_review_candidates_reach_paperops"),
        "duplicate_idempotency_count": primary.get("duplicate_idempotency_count"),
        "duplicate_exposure_count": primary.get("duplicate_exposure_count"),
        "why_not_trading_now_reason": why_not.get("reason"),
        "why_not_trading_now_plain_english": why_not.get("plain_english"),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "cards": [
            {
                "strategy_hypothesis_id": decision.get("strategy_hypothesis_id"),
                "final_state": decision.get("final_state"),
                "router_score": decision.get("scores", {}).get("router_score"),
                "reason": decision.get("final_state_reason"),
                "paperops_handoff_allowed": decision.get("paperops_handoff_allowed"),
                "top_blockers": (decision.get("hard_vetoes") or decision.get("soft_blockers") or decision.get("repair_requests") or [])[:3],
            }
            for decision in decisions
        ],
        "authority": _authority(),
    }


def build_router_v2_paperops_handoff(settings: Settings | None = None) -> RouterV2Bundle:
    generated_at = _iso()
    context = _load_context(settings)
    akber_by_hypothesis = _index_by(context["akber_results"], "strategy_hypothesis_id")
    shadow_by_hypothesis = _index_by(context["shadow_historical"], "strategy_hypothesis_id")
    open_symbols = _open_exposure_symbols(context)
    global_safety = _global_safety_state(context)

    materials = [_idempotency_material(hypothesis) for hypothesis in context["hypotheses"]]
    material_by_hypothesis = {
        str(hypothesis.get("strategy_hypothesis_id")): material
        for hypothesis, material in zip(context["hypotheses"], materials)
    }
    idempotency_counts = _duplicate_idempotency_counts(materials)

    decisions: list[dict[str, Any]] = []
    for hypothesis in context["hypotheses"]:
        hypothesis_id = str(hypothesis.get("strategy_hypothesis_id") or "")
        material = material_by_hypothesis.get(hypothesis_id, _idempotency_material(hypothesis))
        primary_proxy = str(_safe_dict(hypothesis.get("instrument_proxy_mapping")).get("primary_proxy") or "").upper()
        duplicate_idempotency = idempotency_counts.get(str(material.get("idempotency_key")), 0) > 1
        duplicate_exposure = bool(primary_proxy and primary_proxy in open_symbols)
        decisions.append(
            _router_decision(
                hypothesis=hypothesis,
                akber_result=akber_by_hypothesis.get(hypothesis_id, {}),
                shadow_record=shadow_by_hypothesis.get(hypothesis_id, {}),
                idempotency=material,
                duplicate_idempotency=duplicate_idempotency,
                duplicate_exposure=duplicate_exposure,
                open_exposure_symbols=open_symbols,
                global_safety=global_safety,
                generated_at=generated_at,
            )
        )

    handoffs = [_handoff_record(decision, generated_at) for decision in decisions if decision.get("clean_paper_review_candidate") is True]
    rejected_handoffs = [_rejected_handoff(decision, generated_at) for decision in decisions if decision.get("clean_paper_review_candidate") is not True]
    state_counts = Counter(str(decision.get("final_state") or "unknown") for decision in decisions)
    setup_ids = {str(item.get("strategy_hypothesis_id")) for item in context["hypotheses"] if item.get("strategy_hypothesis_id")}
    decision_ids = {str(item.get("strategy_hypothesis_id")) for item in decisions if item.get("strategy_hypothesis_id")}
    duplicate_decision_count = len(decisions) - len(decision_ids)
    invalid_state_count = sum(1 for decision in decisions if decision.get("final_state") not in FINAL_STATES)
    duplicate_idempotency_count = sum(1 for count in idempotency_counts.values() if count > 1)
    duplicate_exposure_count = sum(1 for decision in decisions if decision.get("duplicate_exposure", {}).get("state") == "duplicate_exposure_conflict")
    why_not = _why_not(decisions, context, generated_at)
    scoreboard = _scoreboard(decisions, generated_at)
    only_clean = all(
        any(decision.get("router_decision_id") == handoff.get("router_decision_id") and decision.get("clean_paper_review_candidate") is True for decision in decisions)
        for handoff in handoffs
    )
    primary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_router_v2_paperops_handoff",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "router_v2_ready",
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "proposal_first": True,
        "setup_count": len(context["hypotheses"]),
        "decision_count": len(decisions),
        "setup_without_decision_count": len(setup_ids - decision_ids),
        "duplicate_decision_count": duplicate_decision_count,
        "invalid_final_state_count": invalid_state_count,
        "final_state_counts": dict(state_counts),
        "all_setups_have_exactly_one_final_state": len(setup_ids - decision_ids) == 0 and duplicate_decision_count == 0 and invalid_state_count == 0,
        "paper_review_candidate_count": state_counts.get("paper_review_candidate", 0),
        "clean_paper_review_candidate_count": sum(1 for decision in decisions if decision.get("clean_paper_review_candidate") is True),
        "handoff_record_count": len(handoffs),
        "rejected_handoff_count": len(rejected_handoffs),
        "only_clean_paper_review_candidates_reach_paperops": only_clean,
        "duplicate_idempotency_count": duplicate_idempotency_count,
        "duplicate_exposure_count": duplicate_exposure_count,
        "idempotency_material_count": len(materials),
        "why_not_trading_now_reason": why_not.get("reason"),
        "why_not_trading_now_plain_english": why_not.get("plain_english"),
        "paper_order_created": False,
        "paper_order_created_count": 0,
        "qualified_setup_created": False,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
        "paper_proof_ledger_credit_allowed": False,
        "paper_growth_trial_calendar_advanced": False,
        "simulated_elapsed_time_allowed": False,
        "input_artifacts": {
            "strategy_foundry_v2": STRATEGY_FOUNDRY_V2_ARTIFACT,
            "strategy_foundry_v2_hypotheses": STRATEGY_FOUNDRY_V2_HYPOTHESES_ARTIFACT,
            "akber_filter_v2": AKBER_FILTER_V2_ARTIFACT,
            "akber_filter_v2_results": AKBER_FILTER_V2_RESULTS_ARTIFACT,
            "shadow_simulator_v2": SHADOW_SIMULATOR_V2_ARTIFACT,
            "shadow_historical_replay": SHADOW_HISTORICAL_REPLAY_ARTIFACT,
        },
        "artifact_refs": {
            "decisions": DECISIONS_ARTIFACT,
            "handoff_records": HANDOFF_RECORDS_ARTIFACT,
            "rejected_handoffs": REJECTED_HANDOFFS_ARTIFACT,
            "why_not_trading_now": WHY_NOT_TRADING_NOW_ARTIFACT,
            "scoreboard": SCOREBOARD_ARTIFACT,
            "dashboard_summary": DASHBOARD_SUMMARY_ARTIFACT,
        },
        "authority": _authority(),
    }
    return RouterV2Bundle(
        primary=primary,
        decisions=decisions,
        handoff_records=handoffs,
        rejected_handoffs=rejected_handoffs,
        why_not_trading_now=why_not,
        scoreboard=scoreboard,
        dashboard_summary=_dashboard_summary(primary, decisions, why_not, generated_at),
    )


def write_router_v2_paperops_handoff(bundle: RouterV2Bundle, settings: Settings | None = None) -> dict[str, str]:
    runtime = _runtime_dir(settings)
    paths = {
        "primary": runtime / PRIMARY_ARTIFACT,
        "decisions": runtime / DECISIONS_ARTIFACT,
        "handoff_records": runtime / HANDOFF_RECORDS_ARTIFACT,
        "rejected_handoffs": runtime / REJECTED_HANDOFFS_ARTIFACT,
        "why_not_trading_now": runtime / WHY_NOT_TRADING_NOW_ARTIFACT,
        "scoreboard": runtime / SCOREBOARD_ARTIFACT,
        "dashboard_summary": runtime / DASHBOARD_SUMMARY_ARTIFACT,
        "events": runtime / EVENTS_ARTIFACT,
    }
    _write_json(paths["primary"], bundle.primary)
    _write_jsonl(paths["decisions"], bundle.decisions)
    _write_jsonl(paths["handoff_records"], bundle.handoff_records)
    _write_jsonl(paths["rejected_handoffs"], bundle.rejected_handoffs)
    _write_json(paths["why_not_trading_now"], bundle.why_not_trading_now)
    _write_json(paths["scoreboard"], bundle.scoreboard)
    _write_json(paths["dashboard_summary"], bundle.dashboard_summary)
    _append_jsonl(
        paths["events"],
        {
            "schema_version": SCHEMA_VERSION,
            "phase_id": PHASE_ID,
            "event_type": "router_v2_paperops_handoff_written",
            "generated_at": bundle.primary.get("generated_at"),
            "status": bundle.primary.get("status"),
            "setup_count": bundle.primary.get("setup_count"),
            "paper_review_candidate_count": bundle.primary.get("paper_review_candidate_count"),
            "handoff_record_count": bundle.primary.get("handoff_record_count"),
            "paper_order_created": False,
            "broker_write_count": 0,
            "proof_credit_allowed": False,
            "authority": _authority(),
        },
    )
    return {key: str(path) for key, path in paths.items()}


def build_and_write_router_v2_paperops_handoff(settings: Settings | None = None) -> tuple[RouterV2Bundle, dict[str, str]]:
    bundle = build_router_v2_paperops_handoff(settings)
    written = write_router_v2_paperops_handoff(bundle, settings)
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


def validate_router_decision(decision: dict[str, Any], prefix: str) -> list[str]:
    errors: list[str] = []
    if decision.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"{prefix}_schema_version_invalid")
    if decision.get("phase_id") != PHASE_ID:
        errors.append(f"{prefix}_phase_id_invalid")
    if decision.get("final_state") not in FINAL_STATES:
        errors.append(f"{prefix}_final_state_invalid")
    if decision.get("setup_has_exactly_one_final_state") is not True:
        errors.append(f"{prefix}_single_final_state_missing")
    if decision.get("paper_order_created") is not False:
        errors.append(f"{prefix}_paper_order_created_must_be_false")
    if decision.get("qualified_setup_created") is not False:
        errors.append(f"{prefix}_qualified_setup_created_must_be_false")
    if decision.get("proof_credit_allowed") is not False:
        errors.append(f"{prefix}_proof_credit_allowed_must_be_false")
    if decision.get("paperops_handoff_allowed") is True and decision.get("clean_paper_review_candidate") is not True:
        errors.append(f"{prefix}_handoff_allowed_without_clean_candidate")
    if decision.get("clean_paper_review_candidate") is True and decision.get("final_state") != "paper_review_candidate":
        errors.append(f"{prefix}_clean_candidate_final_state_invalid")
    errors.extend(_validate_authority(decision, prefix))
    return errors


def validate_handoff_record(record: dict[str, Any], decisions_by_id: dict[str, dict[str, Any]], prefix: str) -> list[str]:
    errors: list[str] = []
    if record.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"{prefix}_schema_version_invalid")
    if record.get("phase_id") != PHASE_ID:
        errors.append(f"{prefix}_phase_id_invalid")
    decision = decisions_by_id.get(str(record.get("router_decision_id")))
    if not decision:
        errors.append(f"{prefix}_router_decision_missing")
    elif decision.get("clean_paper_review_candidate") is not True or decision.get("final_state") != "paper_review_candidate":
        errors.append(f"{prefix}_handoff_without_clean_paper_review_candidate")
    if record.get("handoff_is_not_order") is not True:
        errors.append(f"{prefix}_handoff_not_order_boundary_missing")
    if record.get("handoff_is_not_qualified_setup") is not True:
        errors.append(f"{prefix}_handoff_not_qualified_setup_boundary_missing")
    if record.get("paper_order_created") is not False:
        errors.append(f"{prefix}_paper_order_created_must_be_false")
    if record.get("qualified_setup_created") is not False:
        errors.append(f"{prefix}_qualified_setup_created_must_be_false")
    if record.get("proof_credit_allowed") is not False:
        errors.append(f"{prefix}_proof_credit_allowed_must_be_false")
    errors.extend(_validate_authority(record, prefix))
    return errors


def validate_router_v2_paperops_handoff_bundle(bundle: RouterV2Bundle | dict[str, Any]) -> list[str]:
    if isinstance(bundle, RouterV2Bundle):
        primary = bundle.primary
        decisions = bundle.decisions
        handoffs = bundle.handoff_records
        rejected = bundle.rejected_handoffs
        why_not = bundle.why_not_trading_now
        scoreboard = bundle.scoreboard
        dashboard = bundle.dashboard_summary
    else:
        primary = _safe_dict(bundle.get("primary"))
        decisions = _safe_list(bundle.get("decisions"))
        handoffs = _safe_list(bundle.get("handoff_records"))
        rejected = _safe_list(bundle.get("rejected_handoffs"))
        why_not = _safe_dict(bundle.get("why_not_trading_now"))
        scoreboard = _safe_dict(bundle.get("scoreboard"))
        dashboard = _safe_dict(bundle.get("dashboard_summary"))
    errors: list[str] = []
    if primary.get("schema_version") != SCHEMA_VERSION:
        errors.append("primary_schema_version_invalid")
    if primary.get("phase_id") != PHASE_ID:
        errors.append("primary_phase_id_invalid")
    if primary.get("artifact_type") != "qadam_router_v2_paperops_handoff":
        errors.append("primary_artifact_type_invalid")
    if primary.get("status") != "router_v2_ready":
        errors.append("primary_status_not_ready")
    if primary.get("all_setups_have_exactly_one_final_state") is not True:
        errors.append("not_all_setups_have_exactly_one_final_state")
    if _safe_int(primary.get("setup_without_decision_count")) != 0:
        errors.append("setup_without_decision_count_nonzero")
    if _safe_int(primary.get("duplicate_decision_count")) != 0:
        errors.append("duplicate_decision_count_nonzero")
    if _safe_int(primary.get("invalid_final_state_count")) != 0:
        errors.append("invalid_final_state_count_nonzero")
    if len(decisions) != _safe_int(primary.get("setup_count")):
        errors.append("decision_count_setup_count_mismatch")
    if len(decisions) != _safe_int(primary.get("decision_count")):
        errors.append("decision_count_primary_mismatch")
    decisions_by_id = {str(decision.get("router_decision_id")): decision for decision in decisions if decision.get("router_decision_id")}
    for index, decision in enumerate(decisions, start=1):
        errors.extend(validate_router_decision(decision, f"decision_{index}"))
    for index, handoff in enumerate(handoffs, start=1):
        errors.extend(validate_handoff_record(handoff, decisions_by_id, f"handoff_{index}"))
    if len(handoffs) != _safe_int(primary.get("handoff_record_count")):
        errors.append("handoff_count_primary_mismatch")
    if len(rejected) != _safe_int(primary.get("rejected_handoff_count")):
        errors.append("rejected_handoff_count_primary_mismatch")
    clean_count = sum(1 for decision in decisions if decision.get("clean_paper_review_candidate") is True)
    if clean_count != len(handoffs):
        errors.append("clean_candidate_handoff_count_mismatch")
    if primary.get("only_clean_paper_review_candidates_reach_paperops") is not True:
        errors.append("only_clean_candidate_boundary_missing")
    if why_not.get("artifact_type") != "qadam_router_v2_why_not_trading_now":
        errors.append("why_not_artifact_type_invalid")
    if scoreboard.get("artifact_type") != "qadam_router_v2_scoreboard":
        errors.append("scoreboard_artifact_type_invalid")
    if dashboard.get("artifact_type") != "qadam_router_v2_dashboard_summary":
        errors.append("dashboard_artifact_type_invalid")
    for payload, prefix in (
        (primary, "primary"),
        (why_not, "why_not"),
        (scoreboard, "scoreboard"),
        (dashboard, "dashboard"),
    ):
        errors.extend(_validate_authority(payload, prefix))
    return errors


def validate_negative_router_v2_paperops_handoff_probes(settings: Settings | None = None) -> list[str]:
    bundle = build_router_v2_paperops_handoff(settings)
    if not bundle.decisions:
        return ["negative_probe_skipped_missing_router_decisions"]
    errors: list[str] = []
    unsafe_order = json.loads(json.dumps(bundle.decisions[0]))
    unsafe_order["paper_order_created"] = True
    unsafe_order["authority"]["paper_order_created"] = True
    if not validate_router_decision(unsafe_order, "negative_order"):
        errors.append("negative_probe_failed_for_paper_order_boundary")

    unsafe_state = json.loads(json.dumps(bundle.decisions[0]))
    unsafe_state["final_state"] = "paper_order"
    if not validate_router_decision(unsafe_state, "negative_state"):
        errors.append("negative_probe_failed_for_invalid_final_state")

    fake_handoff = _handoff_record(bundle.decisions[0], _iso())
    fake_handoff["router_decision_id"] = bundle.decisions[0].get("router_decision_id")
    decisions_by_id = {str(decision.get("router_decision_id")): decision for decision in bundle.decisions}
    if not validate_handoff_record(fake_handoff, decisions_by_id, "negative_handoff"):
        errors.append("negative_probe_failed_for_unclean_handoff_boundary")

    missing_decision_payload = {
        "primary": {**bundle.primary, "setup_without_decision_count": 1, "all_setups_have_exactly_one_final_state": False},
        "decisions": bundle.decisions[:-1],
        "handoff_records": bundle.handoff_records,
        "rejected_handoffs": bundle.rejected_handoffs,
        "why_not_trading_now": bundle.why_not_trading_now,
        "scoreboard": bundle.scoreboard,
        "dashboard_summary": bundle.dashboard_summary,
    }
    if not validate_router_v2_paperops_handoff_bundle(missing_decision_payload):
        errors.append("negative_probe_failed_for_missing_decision_boundary")
    return errors


def load_router_v2_paperops_handoff(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "primary": _read_json(runtime / PRIMARY_ARTIFACT),
        "decisions": _read_jsonl(runtime / DECISIONS_ARTIFACT),
        "handoff_records": _read_jsonl(runtime / HANDOFF_RECORDS_ARTIFACT),
        "rejected_handoffs": _read_jsonl(runtime / REJECTED_HANDOFFS_ARTIFACT),
        "why_not_trading_now": _read_json(runtime / WHY_NOT_TRADING_NOW_ARTIFACT),
        "scoreboard": _read_json(runtime / SCOREBOARD_ARTIFACT),
        "dashboard_summary": _read_json(runtime / DASHBOARD_SUMMARY_ARTIFACT),
    }
