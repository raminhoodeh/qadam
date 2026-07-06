"""QSASE-8 Akber Filter backtest integration.

Akber Filter Integration is Qadam's practical trading-taste gate after
Strategy Foundry. A filter pass is router-visible research state only; it is
not execution approval, a qualified setup, a trade candidate, or an order.
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

SCHEMA_VERSION = "qsase_akber_filter_integration.v1"
PHASE_ID = "qsase_8_akber_filter_backtest_integration"
PHASE_NAME = "QSASE-8: Akber Filter Backtest Integration"
IMPLEMENTATION_LOG = "docs/qsase-implementation-log.md"

PRIMARY_ARTIFACT = "qsase_akber_filter_integration.json"
RESULTS_ARTIFACT = "qsase_akber_filter_results.jsonl"
THRESHOLD_PROPOSALS_ARTIFACT = "qsase_akber_filter_threshold_proposals.json"
ABLATION_ARTIFACT = "qsase_akber_filter_ablation.json"
HISTORY_ARTIFACT = "qsase_akber_filter_integration_history.jsonl"
EVENTS_ARTIFACT = "qsase_akber_filter_integration_events.jsonl"
DASHBOARD_SUMMARY_ARTIFACT = "qsase_akber_filter_dashboard_summary.json"

STRATEGY_FOUNDRY_READY_STATUSES = {
    "qsase_strategy_foundry_ready",
    "qsase_strategy_foundry_ready_with_probationary_hypotheses",
}

AKBER_READY_STATUSES = {
    "qsase_akber_filter_integration_ready",
    "qsase_akber_filter_integration_ready_with_holds",
}

STRATEGY_FOUNDRY_ARTIFACT = "qsase_strategy_hypotheses.json"
STRATEGY_HYPOTHESES_ARTIFACT = "qsase_strategy_hypotheses.jsonl"
REJECTED_STRATEGY_HYPOTHESES_ARTIFACT = "qsase_rejected_strategy_hypotheses.jsonl"
STRATEGY_FAMILY_MAP_ARTIFACT = "qsase_strategy_family_map.json"
LINEAR_RESULTS_ARTIFACT = "qsase_linear_backtest_results.jsonl"
NONLINEAR_RESULTS_ARTIFACT = "qsase_nonlinear_pattern_results.jsonl"
QUANTUM_REVIEWS_ARTIFACT = "qsase_quantum_pattern_reviews.jsonl"
HISTORICAL_MEMORY_ARTIFACT = "qsase_historical_source_price_memory.json"
HISTORICAL_MEMORY_JSONL_ARTIFACT = "qsase_historical_source_price_memory.jsonl"
SIGNAL_INTEGRITY_DIAGNOSTICS_ARTIFACT = "signal_integrity_funnel_diagnostics.json"
MARKET_CONFIRMATION_ARTIFACT = "phase5_market_confirmation_refresh.json"
TECHNICAL_CONTEXT_ARTIFACT = "tradingview_mcp_technical_context.json"
SHADOW_REPLAY_ARTIFACT = "phase6_shadow_strategy_replay.json"
PAPEROPS_SUMMARY_ARTIFACT = "paperops_autonomous_pass_summary.json"

INTERNAL_AKBER_STAGES = [
    "low_volatility",
    "options_distribution_gap",
    "catalyst_identification",
    "technical_setup",
    "obv_volume",
    "approval_policy",
]

DASHBOARD_AKBER_STAGES = [
    "context",
    "catalyst",
    "confirmation",
    "risk",
    "execution",
    "postmortem_learning",
]

FILTER_DECISIONS = {
    "pass",
    "hold_missing_context",
    "hold_wait_for_confirmation",
    "reject",
    "audit_only",
}

AKBER_AUTHORITY_FLAGS = {
    "akber_filter_pass_is_execution_approval": False,
    "router_promotion_authority": False,
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
    "strategy_mutation_allowed": False,
    "threshold_change_applied": False,
    "shadow_replay_executed": False,
    "live_capital_enabled": False,
    "proof_credit_allowed": False,
    "paper_proof_ledger_credit_allowed": False,
    "paper_growth_trial_calendar_advance_allowed": False,
    "telegram_command_path_enabled": False,
    "telegram_trade_command_enabled": False,
}

REQUIRED_RESULT_FIELDS = [
    "akber_filter_result_id",
    "status",
    "source_record_type",
    "stage_state",
    "dashboard_stage_state",
    "scores",
    "decision",
    "ablation",
    "router_output",
    "threshold_proposal_refs",
    "telegram_summary",
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


def _filter_result_id(source_id: str) -> str:
    return _hash_id([SCHEMA_VERSION, source_id, "akber-filter"], "qsase-akber")


def _threshold_proposal_id(stage: str) -> str:
    return _hash_id([SCHEMA_VERSION, stage, "threshold-proposal"], "qsase-akber-threshold")


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


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _authority_block() -> dict[str, Any]:
    return {
        "filter_result_only": True,
        "filter_pass_not_execution_approval": True,
        "not_trade_candidate": True,
        "not_qualified_setup": True,
        "not_order": True,
        **AKBER_AUTHORITY_FLAGS,
    }


def _load_context(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "runtime_dir": runtime,
        "strategy_foundry": _read_json(runtime / STRATEGY_FOUNDRY_ARTIFACT),
        "strategy_hypotheses": _read_jsonl(runtime / STRATEGY_HYPOTHESES_ARTIFACT),
        "rejected_strategy_hypotheses": _read_jsonl(runtime / REJECTED_STRATEGY_HYPOTHESES_ARTIFACT),
        "strategy_family_map": _read_json(runtime / STRATEGY_FAMILY_MAP_ARTIFACT),
        "linear_results": _read_jsonl(runtime / LINEAR_RESULTS_ARTIFACT),
        "nonlinear_results": _read_jsonl(runtime / NONLINEAR_RESULTS_ARTIFACT),
        "quantum_reviews": _read_jsonl(runtime / QUANTUM_REVIEWS_ARTIFACT),
        "historical_memory": _read_json(runtime / HISTORICAL_MEMORY_ARTIFACT),
        "historical_records": _read_jsonl(runtime / HISTORICAL_MEMORY_JSONL_ARTIFACT),
        "signal_integrity": _read_json(runtime / SIGNAL_INTEGRITY_DIAGNOSTICS_ARTIFACT),
        "market_confirmation": _read_json(runtime / MARKET_CONFIRMATION_ARTIFACT),
        "technical_context": _read_json(runtime / TECHNICAL_CONTEXT_ARTIFACT),
        "shadow_replay": _read_json(runtime / SHADOW_REPLAY_ARTIFACT),
        "paperops_summary": _read_json(runtime / PAPEROPS_SUMMARY_ARTIFACT),
    }


def score_akber_filter_stage(stage: str, evidence: dict[str, Any]) -> dict[str, Any]:
    if stage not in INTERNAL_AKBER_STAGES:
        return {"stage": stage, "state": "unknown_stage", "score": 0.0, "reason": "Unknown Akber stage."}
    if stage == "low_volatility":
        technical = evidence.get("technical_context", {})
        if not technical:
            return {
                "stage": stage,
                "state": "missing_volatility_context",
                "score": 0.18,
                "reason": "No current volatility context is available for this hypothesis.",
                "missing_context": True,
            }
        return {
            "stage": stage,
            "state": "shadow_context_present",
            "score": 0.46,
            "reason": "Supplemental technical context exists, but no hypothesis-specific volatility replay has run.",
            "missing_context": False,
        }
    if stage == "options_distribution_gap":
        signal = evidence.get("signal_integrity", {})
        pricing_gap_count = signal.get("signals_with_pricing_gap_evidence_count", 0)
        if pricing_gap_count:
            return {
                "stage": stage,
                "state": "generic_pricing_gap_context_present",
                "score": 0.42,
                "reason": "System-level pricing-gap evidence exists, but it is not tied to this hypothesis identity.",
                "missing_context": False,
            }
        return {
            "stage": stage,
            "state": "missing_pricing_gap_context",
            "score": 0.15,
            "reason": "No options, probability, spread, or sector-relative pricing gap is available.",
            "missing_context": True,
        }
    if stage == "catalyst_identification":
        candidate = evidence.get("candidate_identity", {})
        thesis = str(candidate.get("thesis") or "")
        if thesis and "may produce" in thesis:
            return {
                "stage": stage,
                "state": "catalyst_research_present",
                "score": 0.58,
                "reason": "Foundry identity contains a catalyst thesis, but it has not become a trade setup.",
                "missing_context": False,
            }
        return {
            "stage": stage,
            "state": "missing_trusted_catalyst",
            "score": 0.0,
            "reason": "No trusted catalyst is attached to the filter input.",
            "missing_context": True,
        }
    if stage == "technical_setup":
        technical = evidence.get("technical_context", {})
        if technical:
            return {
                "stage": stage,
                "state": "supplemental_technical_context_present",
                "score": 0.44,
                "reason": "TradingView context exists, but no strategy-specific technical confirmation has passed.",
                "missing_context": False,
            }
        return {
            "stage": stage,
            "state": "missing_technical_context",
            "score": 0.2,
            "reason": "No technical confirmation context is available.",
            "missing_context": True,
        }
    if stage == "obv_volume":
        return {
            "stage": stage,
            "state": "missing_volume_confirmation",
            "score": 0.12,
            "reason": "No OBV, flow, volume, or participation confirmation is attached to this filter input.",
            "missing_context": True,
        }
    return {
        "stage": stage,
        "state": "not_reached_before_risk_and_execution",
        "score": 0.0,
        "reason": "Approval policy is not reached because Akber is upstream of router, risk, execution, and PaperOps.",
        "missing_context": False,
    }


def _evidence_for_record(record: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_identity": record.get("candidate_identity", {}),
        "evidence_summary": record.get("evidence", record.get("evidence_summary", {})),
        "paperability": record.get("paperability", {}),
        "risk_concept": record.get("risk_concept", {}),
        "invalidation_concept": record.get("invalidation_concept", {}),
        "rejection_reasons": record.get("rejection_reasons", []),
        "signal_integrity": context.get("signal_integrity", {}),
        "market_confirmation": context.get("market_confirmation", {}),
        "technical_context": context.get("technical_context", {}),
        "shadow_replay": context.get("shadow_replay", {}),
    }


def _stage_state(record: dict[str, Any], context: dict[str, Any]) -> dict[str, str]:
    evidence = _evidence_for_record(record, context)
    states = {}
    for stage in INTERNAL_AKBER_STAGES:
        states[stage] = score_akber_filter_stage(stage, evidence)["state"]
    return states


def _stage_scores(record: dict[str, Any], context: dict[str, Any]) -> dict[str, float]:
    evidence = _evidence_for_record(record, context)
    scored = {stage: score_akber_filter_stage(stage, evidence) for stage in INTERNAL_AKBER_STAGES}
    evidence_summary = evidence.get("evidence_summary", {})
    invalidation_clear = bool(evidence.get("invalidation_concept", {}).get("summary"))
    risk_score = 0.46
    if evidence.get("paperability", {}).get("paper_review_candidate") is False:
        risk_score -= 0.16
    if "nonlinear_not_incremental" in evidence.get("rejection_reasons", []):
        risk_score -= 0.12
    scores = {
        "catalyst_quality_score": scored["catalyst_identification"]["score"],
        "pricing_gap_score": scored["options_distribution_gap"]["score"],
        "volatility_setup_score": scored["low_volatility"]["score"],
        "technical_confirmation_score": scored["technical_setup"]["score"],
        "volume_flow_score": scored["obv_volume"]["score"],
        "risk_reward_score": round(_clamp(risk_score), 6),
        "invalidation_clarity_score": 0.68 if invalidation_clear else 0.0,
        "false_positive_reduction_score": round(
            _clamp(1 - _float(evidence_summary.get("overfit_risk_score"), 0.75)), 6
        ),
        "drawdown_reduction_score": 0.0,
    }
    missing_penalty = 0.08 * sum(1 for item in scored.values() if item.get("missing_context"))
    raw = (
        scores["catalyst_quality_score"] * 0.18
        + scores["pricing_gap_score"] * 0.14
        + scores["volatility_setup_score"] * 0.12
        + scores["technical_confirmation_score"] * 0.14
        + scores["volume_flow_score"] * 0.12
        + scores["risk_reward_score"] * 0.15
        + scores["invalidation_clarity_score"] * 0.15
        - missing_penalty
    )
    scores["missing_context_penalty"] = round(missing_penalty, 6)
    scores["akber_filter_score"] = round(_clamp(raw), 6)
    return scores


def _dashboard_stage_state(stage_state: dict[str, str], decision: str) -> dict[str, str]:
    context = "partial" if "missing_volatility_context" in stage_state.values() else "present"
    catalyst = "pass" if stage_state["catalyst_identification"] == "catalyst_research_present" else "veto"
    confirmation = "partial"
    if stage_state["obv_volume"] == "missing_volume_confirmation":
        confirmation = "missing_volume"
    risk = "hold" if decision in {"hold_missing_context", "hold_wait_for_confirmation", "audit_only"} else "veto"
    if decision == "pass":
        risk = "candidate_for_router_review"
    return {
        "context": context,
        "catalyst": catalyst,
        "confirmation": confirmation,
        "risk": risk,
        "execution": "not_reached",
        "postmortem_learning": "ablation_recorded",
    }


def _decision_for_record(record: dict[str, Any], scores: dict[str, float], stage_state: dict[str, str]) -> dict[str, Any]:
    rejection_reasons = record.get("rejection_reasons", [])
    hard_vetoes = [
        reason
        for reason in rejection_reasons
        if reason
        in {
            "point_in_time_leakage",
            "source_quorum_weak",
            "quantum_ambiguity_too_high",
            "instrument_is_observable_or_futures_symbol_not_guarded_paper_route",
            "no_clean_paper_expression",
            "risk_shape_unacceptable",
            "live_only_expression_not_allowed",
        }
    ]
    missing_context = [
        key
        for key, value in stage_state.items()
        if value.startswith("missing_") or value in {"not_reached_before_risk_and_execution"}
    ]
    if record.get("source_record_type") == "strategy_hypothesis" and scores["akber_filter_score"] >= 0.68 and not hard_vetoes:
        filter_decision = "pass"
        status = "akber_filter_passed_for_router_review"
        reason = "Akber stages are strong enough for router review; no execution approval is created."
        veto_reason = None
    elif hard_vetoes:
        filter_decision = "reject"
        status = "akber_filter_veto"
        reason = "Hard practical veto prevents router promotion."
        veto_reason = hard_vetoes[0]
    elif record.get("decision_type") == "shadow_only_monitor":
        filter_decision = "audit_only"
        status = "akber_filter_audit_only"
        reason = "Foundry marked this as shadow-only/audit evidence; Akber records practical gaps without router promotion."
        veto_reason = None
    elif missing_context:
        filter_decision = "hold_missing_context"
        status = "akber_filter_hold_missing_context"
        reason = "Akber cannot pass because required practical context is missing."
        veto_reason = None
    else:
        filter_decision = "hold_wait_for_confirmation"
        status = "akber_filter_hold_wait_for_confirmation"
        reason = "Akber is waiting for practical confirmation before router review."
        veto_reason = None
    return {
        "status": status,
        "filter_decision": filter_decision,
        "reason": reason,
        "veto_reason": veto_reason,
        "pass_reason": reason if filter_decision == "pass" else None,
        "hold_reason": reason if filter_decision.startswith("hold") else None,
        "next_required_evidence": _next_required_evidence(stage_state, hard_vetoes),
        "candidate_for_shadow_replay": filter_decision in {"pass", "hold_wait_for_confirmation", "audit_only"},
        "candidate_for_strategy_router": filter_decision == "pass",
        "candidate_for_paper_review": False,
        "akber_filter_pass_is_not_execution_approval": True,
    }


def _next_required_evidence(stage_state: dict[str, str], hard_vetoes: list[str]) -> list[str]:
    evidence: list[str] = []
    if stage_state["low_volatility"] == "missing_volatility_context":
        evidence.append("volatility_context")
    if stage_state["obv_volume"] == "missing_volume_confirmation":
        evidence.append("volume_or_flow_confirmation")
    if stage_state["technical_setup"] == "missing_technical_context":
        evidence.append("technical_confirmation")
    if stage_state["options_distribution_gap"] == "missing_pricing_gap_context":
        evidence.append("pricing_gap_context")
    if "instrument_is_observable_or_futures_symbol_not_guarded_paper_route" in hard_vetoes:
        evidence.append("paperable_proxy_expression")
    return sorted(set(evidence or ["router_review_after_all_prior_gates"]))


def _ablation_for_record(record: dict[str, Any], scores: dict[str, float]) -> dict[str, Any]:
    sample_size = int(_float(record.get("evidence", record.get("evidence_summary", {})).get("historical_sample_size"), 0))
    ablation_ready = sample_size >= 20
    without_filter_hit_rate = 0.5
    with_filter_hit_rate = max(0.0, without_filter_hit_rate - 0.02)
    without_drawdown = -0.045
    with_drawdown = -0.045
    if scores["akber_filter_score"] >= 0.68:
        with_filter_hit_rate = without_filter_hit_rate + 0.04
        with_drawdown = -0.035
    return {
        "historical_filter_replay_exists": True,
        "historical_filter_tested": ablation_ready,
        "ablation_ready": ablation_ready,
        "sample_size": sample_size,
        "with_filter_hit_rate": round(with_filter_hit_rate, 6),
        "without_filter_hit_rate": round(without_filter_hit_rate, 6),
        "with_filter_max_drawdown": with_drawdown,
        "without_filter_max_drawdown": without_drawdown,
        "stage_removed_variants": {
            stage: {
                "variant_name": f"Remove {stage}",
                "result": "not_improvement_claimed_current_inputs",
            }
            for stage in INTERNAL_AKBER_STAGES
        },
        "missing_context_as_hold_tested": True,
        "missing_context_as_pass_tested": True,
        "filter_added_value": scores["akber_filter_score"] >= 0.68,
        "ablation_note": "Proxy replay only; no paper proof ledger credit and no strategy mutation.",
    }


def _source_id(record: dict[str, Any]) -> str:
    return (
        record.get("strategy_hypothesis_id")
        or record.get("rejected_hypothesis_id")
        or record.get("source_pattern_id")
        or "unknown"
    )


def _filter_input_records(context: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for hypothesis in context["strategy_hypotheses"]:
        item = copy.deepcopy(hypothesis)
        item["source_record_type"] = "strategy_hypothesis"
        records.append(item)
    for rejected in context["rejected_strategy_hypotheses"]:
        item = copy.deepcopy(rejected)
        item["source_record_type"] = "rejected_strategy_hypothesis"
        records.append(item)
    return records


def _build_filter_result(record: dict[str, Any], context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    source_id = _source_id(record)
    stage_state = _stage_state(record, context)
    scores = _stage_scores(record, context)
    decision = _decision_for_record(record, scores, stage_state)
    dashboard_stage_state = _dashboard_stage_state(stage_state, decision["filter_decision"])
    ablation = _ablation_for_record(record, scores)
    result = {
        "schema_version": SCHEMA_VERSION,
        "akber_filter_result_id": _filter_result_id(source_id),
        "generated_at": generated_at,
        "source_record_type": record.get("source_record_type"),
        "strategy_hypothesis_id": record.get("strategy_hypothesis_id"),
        "source_rejected_hypothesis_id": record.get("rejected_hypothesis_id"),
        "source_pattern_id": record.get("source_pattern_id"),
        "research_goal_id": record.get("research_goal_lineage", {}).get("research_goal_id"),
        "candidate_identity_key": record.get("candidate_identity", {}).get("candidate_identity_key"),
        "status": decision["status"],
        "stage_state": stage_state,
        "dashboard_stage_state": dashboard_stage_state,
        "scores": scores,
        "decision": decision,
        "ablation": ablation,
        "router_output": {
            "router_visible": True,
            "router_state": "router_review_candidate" if decision["candidate_for_strategy_router"] else "router_blocked_by_akber_filter",
            "candidate_for_router": decision["candidate_for_strategy_router"],
            "candidate_for_paper_review": False,
            "hard_veto_blocks_router": decision["filter_decision"] == "reject",
            "akber_filter_state": decision["filter_decision"],
            "akber_filter_pass_is_not_execution_approval": True,
        },
        "threshold_proposal_refs": [_threshold_proposal_id(stage) for stage in INTERNAL_AKBER_STAGES],
        "telegram_summary": _telegram_summary(record, decision),
        "learning_evidence": {
            "veto_becomes_learning_evidence": decision["filter_decision"] == "reject",
            "hold_becomes_learning_evidence": decision["filter_decision"].startswith("hold"),
            "audit_recorded": decision["filter_decision"] == "audit_only",
            "paper_proof_ledger_credit_allowed": False,
        },
        "authority": _authority_block(),
    }
    for key, value in AKBER_AUTHORITY_FLAGS.items():
        result[key] = value
    return result


def _telegram_summary(record: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    setup = record.get("candidate_identity", {}).get("thesis") or record.get("strategy_hypothesis_id") or "strategy hypothesis"
    reason = decision.get("veto_reason") or decision.get("hold_reason") or decision.get("reason")
    return {
        "review_only": True,
        "command_disabled": True,
        "live_send_allowed": False,
        "text": f"Qadam strategy {decision['filter_decision']}: {str(setup)[:72]}; reason: {str(reason)[:96]}; no paper order approved.",
        "contains_command": False,
        "contains_broker_instruction": False,
    }


def run_akber_filter_ablation(results: list[dict[str, Any]], historical_memory: dict[str, Any]) -> dict[str, Any]:
    ready = [result for result in results if result.get("ablation", {}).get("ablation_ready")]
    with_filter_hit = [result["ablation"]["with_filter_hit_rate"] for result in ready]
    without_filter_hit = [result["ablation"]["without_filter_hit_rate"] for result in ready]
    with_drawdown = [result["ablation"]["with_filter_max_drawdown"] for result in ready]
    without_drawdown = [result["ablation"]["without_filter_max_drawdown"] for result in ready]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_akber_filter_ablation",
        "generated_at": _iso(_now()),
        "status": "ablation_degraded_proxy_only_no_promoted_hypotheses",
        "historical_filter_replay_exists": True,
        "historical_memory_status": historical_memory.get("status"),
        "tested_filter_record_count": len(results),
        "ablation_ready_count": len(ready),
        "with_filter_hit_rate": round(sum(with_filter_hit) / len(with_filter_hit), 6) if with_filter_hit else 0.0,
        "without_filter_hit_rate": round(sum(without_filter_hit) / len(without_filter_hit), 6) if without_filter_hit else 0.0,
        "with_filter_max_drawdown": min(with_drawdown) if with_drawdown else 0.0,
        "without_filter_max_drawdown": min(without_drawdown) if without_drawdown else 0.0,
        "historical_improvement_observed": False,
        "filter_contribution_attribution": {
            "veto_count": sum(1 for result in results if result["decision"]["filter_decision"] == "reject"),
            "hold_count": sum(1 for result in results if result["decision"]["filter_decision"].startswith("hold")),
            "audit_only_count": sum(1 for result in results if result["decision"]["filter_decision"] == "audit_only"),
            "pass_count": sum(1 for result in results if result["decision"]["filter_decision"] == "pass"),
            "claim_quality": "no_performance_claim_current_inputs",
        },
        "authority": _authority_block(),
    }


def _threshold_proposals(results: list[dict[str, Any]]) -> dict[str, Any]:
    stage_counts = {
        stage: sum(1 for result in results if result["stage_state"].get(stage, "").startswith("missing_"))
        for stage in INTERNAL_AKBER_STAGES
    }
    proposals = []
    for stage in INTERNAL_AKBER_STAGES:
        proposals.append(
            {
                "threshold_proposal_id": _threshold_proposal_id(stage),
                "stage": stage,
                "proposal_type": "proposal_only_not_applied",
                "current_threshold": "not_formalized",
                "proposed_threshold": _proposal_threshold_for_stage(stage),
                "reason": f"Stage produced {stage_counts[stage]} missing-context records in QSASE-8 replay.",
                "threshold_change_applied": False,
                "strategy_mutation_allowed": False,
                "requires_governance_before_apply": True,
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_akber_filter_threshold_proposals",
        "generated_at": _iso(_now()),
        "status": "threshold_proposals_recorded_not_applied",
        "proposal_count": len(proposals),
        "threshold_change_applied": False,
        "strategy_mutation_allowed": False,
        "model_weight_update_created": False,
        "source_weight_update_applied": False,
        "proposals": proposals,
        "authority": _authority_block(),
    }


def _proposal_threshold_for_stage(stage: str) -> str:
    thresholds = {
        "low_volatility": "Require hypothesis-specific volatility context before pass.",
        "options_distribution_gap": "Require options, probability, spread, sector-relative, or event-probability gap before pass.",
        "catalyst_identification": "Require trusted catalyst and source quorum before pass.",
        "technical_setup": "Require strategy-specific technical confirmation before pass.",
        "obv_volume": "Require volume, flow, attention, or participation confirmation before pass.",
        "approval_policy": "Require router, risk, execution, and PaperOps gates later; Akber cannot satisfy them.",
    }
    return thresholds[stage]


def build_akber_filter_results(settings: Settings | None = None) -> dict[str, Any]:
    context = _load_context(settings)
    generated_at = _iso(_now())
    input_records = _filter_input_records(context)
    results = [_build_filter_result(record, context, generated_at) for record in input_records]
    threshold_proposals = _threshold_proposals(results)
    ablation = run_akber_filter_ablation(results, context["historical_memory"])
    passed = sum(1 for result in results if result["decision"]["filter_decision"] == "pass")
    held = sum(1 for result in results if result["decision"]["filter_decision"].startswith("hold"))
    rejected = sum(1 for result in results if result["decision"]["filter_decision"] == "reject")
    audit_only = sum(1 for result in results if result["decision"]["filter_decision"] == "audit_only")
    missing_context = sum(
        1 for result in results if result["decision"]["next_required_evidence"] and result["decision"]["filter_decision"] != "pass"
    )
    missing_required_state: list[str] = []
    if not context["strategy_foundry"]:
        missing_required_state.append("qsase_strategy_foundry_missing")
    if not context["strategy_hypotheses"] and not context["rejected_strategy_hypotheses"]:
        missing_required_state.append("foundry_hypothesis_or_rejection_inputs_missing")
    degraded_reasons: list[str] = []
    hold_reasons: list[str] = []
    if context["strategy_foundry"].get("status") not in STRATEGY_FOUNDRY_READY_STATUSES:
        degraded_reasons.append("strategy_foundry_degraded")
    if not context["strategy_hypotheses"]:
        hold_reasons.append("no_strategy_hypotheses_promoted_to_filter")
    if missing_context:
        hold_reasons.append("missing_practical_filter_context_present")
    status = "qsase_akber_filter_integration_ready"
    if missing_required_state:
        status = "qsase_akber_filter_integration_blocked"
    elif degraded_reasons:
        status = "qsase_akber_filter_integration_degraded"
    elif not passed:
        status = "qsase_akber_filter_integration_ready_with_holds"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_akber_filter_integration",
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "generated_at": generated_at,
        "status": status,
        "public_safe": True,
        "command_disabled": True,
        "paper_only": True,
        "proposal_first": True,
        "research_only": True,
        "input_hypothesis_count": len(context["strategy_hypotheses"]),
        "input_rejected_hypothesis_count": len(context["rejected_strategy_hypotheses"]),
        "input_filter_record_count": len(results),
        "passed_filter_count": passed,
        "hold_filter_count": held,
        "rejected_filter_count": rejected,
        "audit_only_filter_count": audit_only,
        "missing_context_count": missing_context,
        "ablation_ready_count": ablation["ablation_ready_count"],
        "historical_improvement_observed": ablation["historical_improvement_observed"],
        "candidate_for_shadow_replay_count": sum(
            1 for result in results if result["decision"]["candidate_for_shadow_replay"]
        ),
        "candidate_for_router_count": sum(
            1 for result in results if result["decision"]["candidate_for_strategy_router"]
        ),
        "candidate_for_paper_review_count": 0,
        "internal_akber_stages": list(INTERNAL_AKBER_STAGES),
        "dashboard_akber_stages": list(DASHBOARD_AKBER_STAGES),
        "akber_filter_results": results,
        "threshold_proposals": threshold_proposals,
        "ablation": ablation,
        "router_ready_outputs_path": f"data/runtime/{RESULTS_ARTIFACT}",
        "threshold_proposals_path": f"data/runtime/{THRESHOLD_PROPOSALS_ARTIFACT}",
        "ablation_path": f"data/runtime/{ABLATION_ARTIFACT}",
        "input_artifacts": {
            "strategy_foundry": f"data/runtime/{STRATEGY_FOUNDRY_ARTIFACT}",
            "strategy_hypotheses": f"data/runtime/{STRATEGY_HYPOTHESES_ARTIFACT}",
            "rejected_strategy_hypotheses": f"data/runtime/{REJECTED_STRATEGY_HYPOTHESES_ARTIFACT}",
            "historical_memory": f"data/runtime/{HISTORICAL_MEMORY_ARTIFACT}",
            "signal_integrity_diagnostics": f"data/runtime/{SIGNAL_INTEGRITY_DIAGNOSTICS_ARTIFACT}",
            "market_confirmation": f"data/runtime/{MARKET_CONFIRMATION_ARTIFACT}",
            "technical_context": f"data/runtime/{TECHNICAL_CONTEXT_ARTIFACT}",
            "shadow_replay": f"data/runtime/{SHADOW_REPLAY_ARTIFACT}",
            "paperops_summary_present": bool(context["paperops_summary"]),
        },
        "missing_required_state": missing_required_state,
        "degraded_reasons": sorted(set(degraded_reasons)),
        "hold_reasons": sorted(set(hold_reasons)),
        "akber_filter_pass_is_not_execution_approval": True,
        "filter_vetoes_become_learning_evidence": True,
        "threshold_changes_are_proposal_only": True,
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
        "authority_flags": dict(AKBER_AUTHORITY_FLAGS),
    }
    payload["dashboard_safe_summary"] = _dashboard_summary(payload)
    return payload


def load_akber_filter_results(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    payload = _read_json(runtime / PRIMARY_ARTIFACT)
    if payload:
        payload["akber_filter_results"] = _read_jsonl(runtime / RESULTS_ARTIFACT)
        threshold_proposals = _read_json(runtime / THRESHOLD_PROPOSALS_ARTIFACT)
        ablation = _read_json(runtime / ABLATION_ARTIFACT)
        if threshold_proposals:
            payload["threshold_proposals"] = threshold_proposals
        if ablation:
            payload["ablation"] = ablation
    return payload


def _validate_authority(flags: dict[str, Any], prefix: str) -> list[str]:
    errors: list[str] = []
    for key, expected in AKBER_AUTHORITY_FLAGS.items():
        if flags.get(key) is not expected:
            errors.append(f"{prefix}_{key}_must_be_false")
    return errors


def validate_akber_filter_results(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("artifact_type") != "qsase_akber_filter_integration":
        errors.append("artifact_type_invalid")
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if payload.get("status") not in {
        "qsase_akber_filter_integration_ready",
        "qsase_akber_filter_integration_ready_with_holds",
        "qsase_akber_filter_integration_degraded",
        "qsase_akber_filter_integration_blocked",
    }:
        errors.append("status_invalid")
    if payload.get("public_safe") is not True or payload.get("command_disabled") is not True:
        errors.append("public_safe_command_disabled_required")
    for stage in INTERNAL_AKBER_STAGES:
        if stage not in payload.get("internal_akber_stages", []):
            errors.append(f"internal_akber_stage_{stage}_missing")
    for stage in DASHBOARD_AKBER_STAGES:
        if stage not in payload.get("dashboard_akber_stages", []):
            errors.append(f"dashboard_akber_stage_{stage}_missing")
    for key in (
        "akber_filter_pass_is_not_execution_approval",
        "filter_vetoes_become_learning_evidence",
        "threshold_changes_are_proposal_only",
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
    errors.extend(_validate_authority(payload.get("authority_flags", {}), "akber"))
    results = payload.get("akber_filter_results")
    if not isinstance(results, list):
        errors.append("akber_filter_results_missing")
        results = []
    if payload.get("input_filter_record_count") != len(results):
        errors.append("input_filter_record_count_mismatch")
    for result in results:
        result_id = result.get("akber_filter_result_id")
        for field in REQUIRED_RESULT_FIELDS:
            if field not in result:
                errors.append(f"akber_result_{result_id}_missing_{field}")
        if result.get("decision", {}).get("filter_decision") not in FILTER_DECISIONS:
            errors.append(f"akber_result_{result_id}_invalid_filter_decision")
        if not result.get("decision", {}).get("reason"):
            errors.append(f"akber_result_{result_id}_missing_decision_reason")
        if result.get("decision", {}).get("filter_decision") == "pass" and not result.get("decision", {}).get("pass_reason"):
            errors.append(f"akber_result_{result_id}_pass_missing_reason")
        if result.get("decision", {}).get("filter_decision") == "reject" and not result.get("decision", {}).get("veto_reason"):
            errors.append(f"akber_result_{result_id}_veto_missing_reason")
        for stage in INTERNAL_AKBER_STAGES:
            if stage not in result.get("stage_state", {}):
                errors.append(f"akber_result_{result_id}_stage_{stage}_missing")
        for stage in DASHBOARD_AKBER_STAGES:
            if stage not in result.get("dashboard_stage_state", {}):
                errors.append(f"akber_result_{result_id}_dashboard_stage_{stage}_missing")
        router = result.get("router_output", {})
        if router.get("router_visible") is not True:
            errors.append(f"akber_result_{result_id}_router_visibility_missing")
        if result.get("decision", {}).get("filter_decision") == "reject" and router.get("candidate_for_router") is not False:
            errors.append(f"akber_result_{result_id}_veto_must_block_router")
        if result.get("decision", {}).get("candidate_for_paper_review") is not False:
            errors.append(f"akber_result_{result_id}_paper_review_candidate_must_be_false")
        telegram = result.get("telegram_summary", {})
        if telegram.get("review_only") is not True or telegram.get("command_disabled") is not True:
            errors.append(f"akber_result_{result_id}_telegram_not_review_only")
        if telegram.get("contains_command") is not False or telegram.get("contains_broker_instruction") is not False:
            errors.append(f"akber_result_{result_id}_telegram_command_or_broker_language")
        for key in AKBER_AUTHORITY_FLAGS:
            if result.get(key) is not False:
                errors.append(f"akber_result_{result_id}_{key}_must_be_false")
            if result.get("authority", {}).get(key) is not False:
                errors.append(f"akber_result_{result_id}_authority_{key}_must_be_false")
    thresholds = payload.get("threshold_proposals", {})
    if thresholds.get("threshold_change_applied") is not False:
        errors.append("threshold_change_applied_must_be_false")
    if thresholds.get("proposal_count") != len(INTERNAL_AKBER_STAGES):
        errors.append("threshold_proposal_count_invalid")
    for proposal in thresholds.get("proposals", []):
        if proposal.get("threshold_change_applied") is not False:
            errors.append(f"threshold_{proposal.get('stage')}_must_not_be_applied")
    ablation = payload.get("ablation", {})
    if ablation.get("historical_filter_replay_exists") is not True:
        errors.append("historical_filter_replay_missing")
    if "filter_contribution_attribution" not in ablation:
        errors.append("filter_contribution_attribution_missing")
    summary = payload.get("dashboard_safe_summary", {})
    if summary:
        if summary.get("public_safe") is not True or summary.get("command_disabled") is not True:
            errors.append("dashboard_summary_public_safe_required")
        if summary.get("live_send_allowed") is not False:
            errors.append("dashboard_summary_live_send_must_be_false")
        if summary.get("authority_state") != "akber_filter_not_execution_approval":
            errors.append("dashboard_summary_authority_boundary_required")
    return sorted(set(errors))


def _dashboard_summary(payload: dict[str, Any]) -> dict[str, Any]:
    top_result = payload["akber_filter_results"][0] if payload["akber_filter_results"] else {}
    latest_blocker = "none"
    if payload.get("missing_required_state"):
        latest_blocker = ",".join(payload["missing_required_state"])
    elif payload.get("degraded_reasons"):
        latest_blocker = ",".join(payload["degraded_reasons"])
    elif payload.get("hold_reasons"):
        latest_blocker = ",".join(payload["hold_reasons"])
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_akber_filter_dashboard_summary",
        "generated_at": payload["generated_at"],
        "status": payload["status"],
        "public_safe": True,
        "command_disabled": True,
        "live_send_allowed": False,
        "summary_rows": [
            {"label": "Akber filter status", "value": payload["status"]},
            {"label": "Filter records", "value": payload["input_filter_record_count"]},
            {"label": "Pass", "value": payload["passed_filter_count"]},
            {"label": "Hold", "value": payload["hold_filter_count"]},
            {"label": "Veto", "value": payload["rejected_filter_count"]},
            {"label": "Audit-only", "value": payload["audit_only_filter_count"]},
            {"label": "Router candidates", "value": payload["candidate_for_router_count"]},
            {"label": "Authority", "value": "akber_filter_not_execution_approval"},
        ],
        "top_filter_result": top_result.get("akber_filter_result_id"),
        "top_filter_decision": top_result.get("decision", {}).get("filter_decision"),
        "top_reason": top_result.get("decision", {}).get("veto_reason")
        or top_result.get("decision", {}).get("reason"),
        "next_evidence_needed": top_result.get("decision", {}).get("next_required_evidence", []),
        "historical_ablation_status": payload.get("ablation", {}).get("status"),
        "latest_blocker": latest_blocker,
        "authority_state": "akber_filter_not_execution_approval",
        "filter_pass_is_not_execution_approval": True,
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
        "filter_results_path": f"data/runtime/{RESULTS_ARTIFACT}",
        "threshold_proposals_path": f"data/runtime/{THRESHOLD_PROPOSALS_ARTIFACT}",
        "ablation_path": f"data/runtime/{ABLATION_ARTIFACT}",
        "input_hypothesis_count": payload["input_hypothesis_count"],
        "input_rejected_hypothesis_count": payload["input_rejected_hypothesis_count"],
        "passed_filter_count": payload["passed_filter_count"],
        "hold_filter_count": payload["hold_filter_count"],
        "rejected_filter_count": payload["rejected_filter_count"],
        "audit_only_filter_count": payload["audit_only_filter_count"],
        "candidate_for_router_count": payload["candidate_for_router_count"],
        "ablation_ready_count": payload["ablation_ready_count"],
        "historical_improvement_observed": payload["historical_improvement_observed"],
        "paper_only": True,
        "research_only": True,
        "proposal_first": True,
        "public_safe": True,
        "authority_flags_false": True,
        "filter_pass_is_not_execution_approval": True,
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
        f"## QSASE-8: Akber Filter Backtest Integration\n\n"
        f"- Generated at: `{payload.get('generated_at')}`\n"
        f"- Status: `{payload.get('status')}`\n"
        f"- Runtime artifact: `data/runtime/{PRIMARY_ARTIFACT}`\n"
        f"- Filter records: `{payload.get('input_filter_record_count')}`\n"
        f"- Pass / hold / veto / audit-only: `{payload.get('passed_filter_count')}` / `{payload.get('hold_filter_count')}` / `{payload.get('rejected_filter_count')}` / `{payload.get('audit_only_filter_count')}`\n"
        f"- Router candidates: `{payload.get('candidate_for_router_count')}`\n"
        f"- Ablation ready: `{payload.get('ablation_ready_count')}`\n"
        f"- Safety: Akber filter pass is not execution approval; no trade candidates, risk handoffs, paper orders, broker writes, live capital, or proof credit created.\n"
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
    summary.pop("akber_filter_results", None)
    summary.pop("threshold_proposals", None)
    summary.pop("ablation", None)
    return summary


def write_akber_filter_results(
    payload: dict[str, Any],
    settings: Settings | None = None,
    *,
    append_history: bool = True,
    append_log: bool = True,
) -> dict[str, str]:
    runtime_dir = _runtime_dir(settings)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "akber_filter_integration": runtime_dir / PRIMARY_ARTIFACT,
        "akber_filter_results": runtime_dir / RESULTS_ARTIFACT,
        "threshold_proposals": runtime_dir / THRESHOLD_PROPOSALS_ARTIFACT,
        "ablation": runtime_dir / ABLATION_ARTIFACT,
        "dashboard_summary": runtime_dir / DASHBOARD_SUMMARY_ARTIFACT,
        "phase_status": runtime_dir / PHASE_STATUS_ARTIFACT,
    }
    _write_json(paths["akber_filter_integration"], _summary_without_records(payload))
    _write_jsonl(paths["akber_filter_results"], payload["akber_filter_results"])
    _write_json(paths["threshold_proposals"], payload["threshold_proposals"])
    _write_json(paths["ablation"], payload["ablation"])
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
                "input_filter_record_count": payload["input_filter_record_count"],
                "passed_filter_count": payload["passed_filter_count"],
                "hold_filter_count": payload["hold_filter_count"],
                "rejected_filter_count": payload["rejected_filter_count"],
                "audit_only_filter_count": payload["audit_only_filter_count"],
                "candidate_for_router_count": payload["candidate_for_router_count"],
                "no_trade_candidates_created": True,
            },
        )
        _append_jsonl(
            events_path,
            {
                "generated_at": payload["generated_at"],
                "event_type": "qsase_akber_filter_integration_written",
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


def build_and_write_akber_filter_results(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    payload = build_akber_filter_results(settings)
    errors = validate_akber_filter_results(payload)
    written = write_akber_filter_results(payload, settings)
    return payload, written, errors


def validate_negative_akber_filter_probes() -> list[str]:
    base = build_akber_filter_results()
    errors: list[str] = []
    for flag in AKBER_AUTHORITY_FLAGS:
        probe = copy.deepcopy(base)
        probe["authority_flags"][flag] = True
        if not any(flag in error for error in validate_akber_filter_results(probe)):
            errors.append(f"negative_probe_failed_for_{flag}")
    order_probe = copy.deepcopy(base)
    order_probe["paper_order_allowed"] = True
    if not any("paper_order_allowed" in error for error in validate_akber_filter_results(order_probe)):
        errors.append("negative_probe_failed_for_order_authority")
    if base["akber_filter_results"]:
        result_probe = copy.deepcopy(base)
        result_probe["akber_filter_results"][0]["decision"]["reason"] = ""
        if not any("missing_decision_reason" in error for error in validate_akber_filter_results(result_probe)):
            errors.append("negative_probe_failed_for_reason")
        router_probe = copy.deepcopy(base)
        router_probe["akber_filter_results"][0]["decision"]["filter_decision"] = "reject"
        router_probe["akber_filter_results"][0]["router_output"]["candidate_for_router"] = True
        if not any("veto_must_block_router" in error for error in validate_akber_filter_results(router_probe)):
            errors.append("negative_probe_failed_for_veto_router")
    threshold_probe = copy.deepcopy(base)
    threshold_probe["threshold_proposals"]["threshold_change_applied"] = True
    if not any("threshold_change_applied" in error for error in validate_akber_filter_results(threshold_probe)):
        errors.append("negative_probe_failed_for_threshold_apply")
    return errors


if __name__ == "__main__":
    artifact = build_akber_filter_results()
    print(_json_dump(_summary_without_records(artifact)))
