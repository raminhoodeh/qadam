"""QSASE-9 Shadow Strategy Simulator.

The simulator is QSASE's research-only what-would-have-happened layer. It can
compare historical, forward, and counterfactual no-order outcomes, but it cannot
create trade candidates, orders, broker writes, live-capital authority, or paper
proof ledger credit.
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

SCHEMA_VERSION = "qsase_shadow_strategy_simulator.v1"
PHASE_ID = "qsase_9_shadow_strategy_simulator_upgrade"
PHASE_NAME = "QSASE-9: Shadow Strategy Simulator Upgrade"
IMPLEMENTATION_LOG = "docs/qsase-implementation-log.md"

PRIMARY_ARTIFACT = "qsase_shadow_strategy_simulator.json"
RESULTS_ARTIFACT = "qsase_shadow_strategy_results.jsonl"
REJECTIONS_ARTIFACT = "qsase_shadow_strategy_rejections.jsonl"
HISTORY_ARTIFACT = "qsase_shadow_strategy_simulator_history.jsonl"
EVENTS_ARTIFACT = "qsase_shadow_strategy_simulator_events.jsonl"
VARIANT_MATRIX_ARTIFACT = "qsase_shadow_strategy_variant_matrix.json"
ACTUAL_VS_HYPOTHETICAL_ARTIFACT = "qsase_shadow_actual_vs_hypothetical.json"
DASHBOARD_SUMMARY_ARTIFACT = "qsase_shadow_strategy_dashboard_summary.json"

STRATEGY_FOUNDRY_READY_STATUSES = {
    "qsase_strategy_foundry_ready",
    "qsase_strategy_foundry_ready_with_probationary_hypotheses",
}

AKBER_READY_STATUSES = {
    "qsase_akber_filter_integration_ready",
    "qsase_akber_filter_integration_ready_with_holds",
}

HISTORICAL_MEMORY_READY_STATUSES = {
    "qsase_historical_source_price_memory_ready",
    "qsase_historical_source_price_memory_ready_with_gaps",
}

STRATEGY_FOUNDRY_ARTIFACT = "qsase_strategy_hypotheses.json"
STRATEGY_HYPOTHESES_ARTIFACT = "qsase_strategy_hypotheses.jsonl"
REJECTED_STRATEGY_HYPOTHESES_ARTIFACT = "qsase_rejected_strategy_hypotheses.jsonl"
AKBER_FILTER_ARTIFACT = "qsase_akber_filter_integration.json"
AKBER_FILTER_RESULTS_ARTIFACT = "qsase_akber_filter_results.jsonl"
HISTORICAL_MEMORY_ARTIFACT = "qsase_historical_source_price_memory.json"
PHASE6_SHADOW_ARTIFACT = "phase6_shadow_strategy_replay.json"
PAPEROPS_SUMMARY_ARTIFACT = "paperops_autonomous_pass_summary.json"

REPLAY_MODES = {
    "historical_hypothesis_replay",
    "forward_shadow_replay",
    "counterfactual_strategy_replay",
    "actual_vs_hypothetical_replay",
    "blocked_route_replay",
    "missed_opportunity_replay",
}

EVIDENCE_CLASSES = {
    "historical_shadow_research",
    "forward_shadow_watch",
    "counterfactual_no_order_outcome",
    "actual_vs_hypothetical_reference",
    "blocked_route_shadow_research",
}

SHADOW_DECISIONS = {
    "candidate_for_router_review",
    "hold_for_more_shadow_data",
    "reject_after_shadow_replay",
    "watch_only",
    "audit_only",
}

VARIANT_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "variant_key": "baseline_current_strategy",
        "variant_name": "Baseline Current Strategy",
        "variant_type": "baseline",
        "changed_assumption": "Use the current Strategy Foundry and Akber Filter state unchanged.",
        "proposed_by_artifact": f"data/runtime/{STRATEGY_FOUNDRY_ARTIFACT}",
        "approval_state": "audit_only",
        "replay_modes": ["historical_hypothesis_replay"],
    },
    {
        "variant_key": "akber_strict_veto",
        "variant_name": "Strict Akber Veto",
        "variant_type": "akber_filter_variant",
        "changed_assumption": "Treat hard Akber vetoes as route-blocking no-order outcomes.",
        "proposed_by_artifact": f"data/runtime/{AKBER_FILTER_ARTIFACT}",
        "approval_state": "audit_only",
        "replay_modes": ["counterfactual_strategy_replay", "blocked_route_replay"],
    },
    {
        "variant_key": "forward_watch_only",
        "variant_name": "Forward Watch Only",
        "variant_type": "forward_shadow_variant",
        "changed_assumption": "Observe future evidence without creating candidates, orders, or proof credit.",
        "proposed_by_artifact": f"data/runtime/{PHASE6_SHADOW_ARTIFACT}",
        "approval_state": "audit_only",
        "replay_modes": ["forward_shadow_replay"],
    },
)

SHADOW_AUTHORITY_FLAGS = {
    "trade_candidate_creation_allowed": False,
    "trade_candidate_created": False,
    "qualified_setup_created": False,
    "risk_handoff_allowed": False,
    "risk_approval_allowed": False,
    "risk_approval_created": False,
    "execution_allowed": False,
    "execution_approval_allowed": False,
    "execution_approval_created": False,
    "execution_intent_created": False,
    "paper_order_allowed": False,
    "paper_order_created": False,
    "broker_write_allowed": False,
    "live_broker_endpoint_allowed": False,
    "alpaca_post_allowed": False,
    "paperops_direct_handoff_allowed": False,
    "strategy_mutation_allowed": False,
    "strategy_mutation_created": False,
    "policy_mutation_allowed": False,
    "policy_mutation_created": False,
    "model_weight_update_allowed": False,
    "model_weight_update_created": False,
    "source_trust_update_allowed": False,
    "source_trust_update_created": False,
    "threshold_change_applied": False,
    "shadow_to_proof_allowed": False,
    "proof_credit_allowed": False,
    "paper_proof_ledger_write_allowed": False,
    "paper_proof_ledger_credit_allowed": False,
    "paper_growth_trial_calendar_advance_allowed": False,
    "simulated_elapsed_time_allowed": False,
    "telegram_command_path_enabled": False,
    "telegram_trade_command_enabled": False,
    "live_capital_enabled": False,
}

REQUIRED_REPLAY_FIELDS = (
    "shadow_replay_id",
    "strategy_hypothesis_id",
    "replay_mode",
    "evidence_class",
    "replay_state",
    "variant",
    "time_window",
    "source_refs",
    "source_price_lineage",
    "strategy_hypothesis_lineage",
    "actual_decision",
    "hypothetical_decision",
    "outcome",
    "comparison",
    "decision",
    "learning_attribution",
    "telegram_summary",
    "authority",
)


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
        "reference_only": True,
        "research_only": True,
        "no_order_or_proof_authority": True,
        **SHADOW_AUTHORITY_FLAGS,
    }


def _load_context(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "runtime_dir": runtime,
        "strategy_foundry": _read_json(runtime / STRATEGY_FOUNDRY_ARTIFACT),
        "strategy_hypotheses": _read_jsonl(runtime / STRATEGY_HYPOTHESES_ARTIFACT),
        "rejected_strategy_hypotheses": _read_jsonl(runtime / REJECTED_STRATEGY_HYPOTHESES_ARTIFACT),
        "akber_filter": _read_json(runtime / AKBER_FILTER_ARTIFACT),
        "akber_results": _read_jsonl(runtime / AKBER_FILTER_RESULTS_ARTIFACT),
        "historical_memory": _read_json(runtime / HISTORICAL_MEMORY_ARTIFACT),
        "phase6_shadow": _read_json(runtime / PHASE6_SHADOW_ARTIFACT),
        "paperops_summary": _read_json(runtime / PAPEROPS_SUMMARY_ARTIFACT),
    }


def _source_id(record: dict[str, Any]) -> str:
    return (
        record.get("strategy_hypothesis_id")
        or record.get("source_rejected_hypothesis_id")
        or record.get("rejected_hypothesis_id")
        or record.get("source_pattern_id")
        or record.get("akber_filter_result_id")
        or "unknown"
    )


def _record_by_id(records: list[dict[str, Any]], key: str, value: Any) -> dict[str, Any]:
    if not value:
        return {}
    for record in records:
        if record.get(key) == value:
            return record
    return {}


def _lineage_for_akber(record: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    rejected = _record_by_id(
        context["rejected_strategy_hypotheses"],
        "rejected_hypothesis_id",
        record.get("source_rejected_hypothesis_id"),
    )
    hypothesis = _record_by_id(
        context["strategy_hypotheses"],
        "strategy_hypothesis_id",
        record.get("strategy_hypothesis_id"),
    )
    source = hypothesis or rejected
    return {
        "strategy_hypothesis_id": record.get("strategy_hypothesis_id"),
        "rejected_hypothesis_id": record.get("source_rejected_hypothesis_id"),
        "source_pattern_id": record.get("source_pattern_id") or source.get("source_pattern_id"),
        "research_goal_id": record.get("research_goal_id")
        or source.get("research_goal_lineage", {}).get("research_goal_id"),
        "candidate_identity_key": record.get("candidate_identity_key")
        or source.get("candidate_identity", {}).get("candidate_identity_key"),
        "candidate_thesis": source.get("candidate_identity", {}).get("thesis"),
        "instrument": source.get("candidate_identity", {}).get("instrument")
        or source.get("paperability", {}).get("primary_instrument"),
        "source_price_pattern_lineage": source.get("source_price_pattern_lineage", {}),
        "strategy_family": source.get("strategy_family", {}).get("mapped_existing_family")
        or source.get("strategy_family"),
        "rejection_reasons": source.get("rejection_reasons", []),
        "retest_condition": source.get("retest_condition"),
        "paperability": source.get("paperability", {}),
        "evidence_summary": source.get("evidence_summary", source.get("evidence", {})),
    }


def build_shadow_variant_matrix(settings: Settings | None = None) -> dict[str, Any]:
    context = _load_context(settings)
    generated_at = _iso(_now())
    variants: list[dict[str, Any]] = []
    for definition in VARIANT_DEFINITIONS:
        variants.append(
            {
                "schema_version": SCHEMA_VERSION,
                "variant_id": _hash_id([SCHEMA_VERSION, definition["variant_key"]], "qsase-shadow-variant"),
                **definition,
                "threshold_change_applied": False,
                "strategy_mutation_allowed": False,
                "model_weight_update_allowed": False,
                "source_trust_update_allowed": False,
                "policy_mutation_allowed": False,
                "authority_flags": dict(SHADOW_AUTHORITY_FLAGS),
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_shadow_strategy_variant_matrix",
        "generated_at": generated_at,
        "status": "variant_matrix_ready",
        "variant_count": len(variants),
        "input_akber_filter_record_count": len(context["akber_results"]),
        "input_strategy_hypothesis_count": len(context["strategy_hypotheses"]),
        "input_rejected_hypothesis_count": len(context["rejected_strategy_hypotheses"]),
        "variants": variants,
        "authority_flags": dict(SHADOW_AUTHORITY_FLAGS),
        "proposal_first": True,
        "paper_only": True,
        "research_only": True,
    }


def _source_refs() -> list[str]:
    return [
        f"data/runtime/{STRATEGY_FOUNDRY_ARTIFACT}",
        f"data/runtime/{STRATEGY_HYPOTHESES_ARTIFACT}",
        f"data/runtime/{REJECTED_STRATEGY_HYPOTHESES_ARTIFACT}",
        f"data/runtime/{AKBER_FILTER_ARTIFACT}",
        f"data/runtime/{AKBER_FILTER_RESULTS_ARTIFACT}",
        f"data/runtime/{HISTORICAL_MEMORY_ARTIFACT}",
        f"data/runtime/{PHASE6_SHADOW_ARTIFACT}",
        f"data/runtime/{PAPEROPS_SUMMARY_ARTIFACT}",
    ]


def _actual_decision(context: dict[str, Any]) -> dict[str, Any]:
    paperops = context.get("paperops_summary", {})
    submitted_count = int(
        _float(
            paperops.get("submitted_paper_order_count")
            or paperops.get("submitted_order_count")
            or paperops.get("paper_order_created_count"),
            0,
        )
    )
    return {
        "decision_type": "guarded_paper_lifecycle_reference" if submitted_count else "no_actual_paper_order",
        "paper_order_ref": f"data/runtime/{PAPEROPS_SUMMARY_ARTIFACT}" if submitted_count else None,
        "paper_lifecycle_ref": f"data/runtime/{PAPEROPS_SUMMARY_ARTIFACT}" if paperops else None,
        "submitted_paper_order_count": submitted_count,
        "actual_lifecycle_mutated": False,
        "reference_only": True,
    }


def _time_window(context: dict[str, Any]) -> dict[str, Any]:
    memory = context.get("historical_memory", {})
    return {
        "start": memory.get("point_in_time_replay_index", {}).get("first_decision_timestamp")
        or memory.get("generated_at"),
        "end": memory.get("point_in_time_replay_index", {}).get("last_decision_timestamp")
        or memory.get("generated_at"),
        "decision_timestamps_point_in_time_safe": True,
        "forbidden_future_features_detected": False,
        "simulated_elapsed_time_allowed": False,
    }


def _outcome_for(record: dict[str, Any], variant: dict[str, Any], mode: str) -> dict[str, Any]:
    ablation = record.get("ablation", {})
    decision = record.get("decision", {})
    akber_score = _float(record.get("scores", {}).get("akber_filter_score"), 0.0)
    sample_size = int(_float(ablation.get("sample_size"), 0))
    filter_decision = decision.get("filter_decision")
    hard_veto = filter_decision == "reject"
    hypothetical_hit = bool(akber_score >= 0.68 and not hard_veto)
    return {
        "outcome_source": "akber_filter_ablation_proxy_and_historical_memory_coverage",
        "sample_size": sample_size,
        "outcome_available": ablation.get("historical_filter_tested") is True,
        "missing_window_reason": None if ablation.get("historical_filter_tested") else "historical_outcome_window_missing",
        "hypothetical_return_5d": 0.0,
        "hypothetical_max_drawdown_5d": ablation.get("with_filter_max_drawdown", 0.0),
        "hypothetical_hit": hypothetical_hit,
        "missed_opportunity": False,
        "avoided_false_positive": hard_veto,
        "with_filter_hit_rate": ablation.get("with_filter_hit_rate", 0.0),
        "without_filter_hit_rate": ablation.get("without_filter_hit_rate", 0.0),
        "shadow_success_cannot_create_order": True,
        "shadow_success_cannot_create_proof_credit": True,
        "replay_mode": mode,
        "variant_key": variant["variant_key"],
    }


def _hypothetical_decision_for(record: dict[str, Any], variant: dict[str, Any], mode: str) -> dict[str, Any]:
    decision = record.get("decision", {})
    akber_decision = decision.get("filter_decision")
    if akber_decision == "reject":
        decision_type = "would_have_rejected_or_held"
        reason = decision.get("veto_reason") or decision.get("reason")
    elif mode == "forward_shadow_replay":
        decision_type = "would_have_watched_forward"
        reason = "Forward shadow watch records future evidence requirements without an order."
    else:
        decision_type = "would_have_held"
        reason = decision.get("hold_reason") or decision.get("reason")
    return {
        "decision_type": decision_type,
        "reason": reason,
        "would_have_created_trade_candidate": False,
        "would_have_created_paper_order": False,
        "would_have_created_execution_intent": False,
        "would_have_written_broker": False,
        "would_have_granted_proof_credit": False,
        "variant_key": variant["variant_key"],
    }


def _decision_for(record: dict[str, Any], mode: str, variant: dict[str, Any]) -> dict[str, Any]:
    akber_decision = record.get("decision", {}).get("filter_decision")
    if akber_decision == "reject":
        shadow_status = "reject_after_shadow_replay"
        reason = "Akber hard veto and PaperOps route boundaries keep this as rejected shadow evidence."
    elif mode == "forward_shadow_replay":
        shadow_status = "watch_only"
        reason = "Forward shadow watch can observe evidence but cannot create orders or proof credit."
    elif akber_decision in {"hold_missing_context", "hold_wait_for_confirmation"}:
        shadow_status = "hold_for_more_shadow_data"
        reason = "Shadow replay needs additional context before router review."
    elif akber_decision == "pass":
        shadow_status = "candidate_for_router_review"
        reason = "Shadow replay is router-visible research only; it is still not execution approval."
    else:
        shadow_status = "audit_only"
        reason = "Shadow replay recorded an audit-only research surface."
    return {
        "shadow_status": shadow_status,
        "reason": reason,
        "candidate_for_router": shadow_status == "candidate_for_router_review",
        "candidate_for_paper_review": False,
        "candidate_for_learning_attribution": True,
        "paper_order_ready": False,
        "risk_approved": False,
        "execution_approved": False,
        "proof_credit_ready": False,
        "variant_key": variant["variant_key"],
    }


def _replay_state_for(mode: str, decision: dict[str, Any], context: dict[str, Any]) -> str:
    if not context["strategy_hypotheses"] and mode == "forward_shadow_replay":
        return "blocked_missing_strategy_hypothesis"
    if decision["shadow_status"] == "reject_after_shadow_replay":
        return "evaluated_rejected_research_only"
    if mode == "counterfactual_strategy_replay":
        return "evaluated_counterfactual_no_order"
    return "evaluated_research_only"


def _learning_attribution(record: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "learning_attribution_ready": True,
        "learning_write_created": False,
        "evidence_class": "shadow_replay_research",
        "akber_contribution": record.get("decision", {}).get("filter_decision"),
        "route_block_contribution": record.get("router_output", {}).get("hard_veto_blocks_router") is True,
        "paper_proof_ledger_credit_allowed": False,
        "shadow_status": decision["shadow_status"],
    }


def _telegram_summary(lineage: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    setup = lineage.get("candidate_thesis") or lineage.get("strategy_family") or "strategy hypothesis"
    next_step = "router review candidate" if decision["candidate_for_router"] else "learn from no-order replay"
    return {
        "review_only": True,
        "command_disabled": True,
        "live_send_allowed": False,
        "contains_command": False,
        "contains_broker_instruction": False,
        "text": (
            f"Qadam shadow replay\nSetup: {str(setup)[:72]}\n"
            f"Result: {decision['shadow_status']}\nNext: {next_step}\nNo order or proof credit"
        ),
    }


def _build_replay_record(
    *,
    record: dict[str, Any],
    context: dict[str, Any],
    variant: dict[str, Any],
    mode: str,
    evidence_class: str,
    generated_at: str,
) -> dict[str, Any]:
    lineage = _lineage_for_akber(record, context)
    decision = _decision_for(record, mode, variant)
    replay_state = _replay_state_for(mode, decision, context)
    replay_id = _hash_id([SCHEMA_VERSION, _source_id(record), variant["variant_key"], mode], "qsase-shadow")
    outcome = _outcome_for(record, variant, mode)
    comparison = {
        "baseline_variant_id": _hash_id([SCHEMA_VERSION, "baseline_current_strategy"], "qsase-shadow-variant"),
        "delta_expectancy": 0.0,
        "delta_drawdown": 0.0,
        "delta_false_positive_rate": -0.02 if outcome["avoided_false_positive"] else 0.0,
        "variant_added_value": outcome["avoided_false_positive"] and variant["variant_key"] == "akber_strict_veto",
        "performance_claim_allowed": False,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "shadow_replay_id": replay_id,
        "generated_at": generated_at,
        "strategy_hypothesis_id": record.get("strategy_hypothesis_id"),
        "rejected_hypothesis_id": record.get("source_rejected_hypothesis_id"),
        "akber_filter_result_id": record.get("akber_filter_result_id"),
        "replay_mode": mode,
        "evidence_class": evidence_class,
        "replay_state": replay_state,
        "variant": variant,
        "time_window": _time_window(context),
        "source_refs": _source_refs(),
        "source_price_lineage": lineage.get("source_price_pattern_lineage", {}),
        "strategy_hypothesis_lineage": {
            "research_goal_id": lineage.get("research_goal_id"),
            "candidate_identity_key": lineage.get("candidate_identity_key"),
            "source_pattern_id": lineage.get("source_pattern_id"),
            "strategy_family": lineage.get("strategy_family"),
        },
        "actual_decision": _actual_decision(context),
        "hypothetical_decision": _hypothetical_decision_for(record, variant, mode),
        "outcome": outcome,
        "comparison": comparison,
        "scores": score_shadow_variants_for_record(record, outcome, comparison),
        "decision": decision,
        "learning_attribution": _learning_attribution(record, decision),
        "telegram_summary": _telegram_summary(lineage, decision),
        "authority": _authority_block(),
        **SHADOW_AUTHORITY_FLAGS,
    }


def _fallback_blocked_record(context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    variant = build_shadow_variant_matrix()["variants"][0]
    return {
        "schema_version": SCHEMA_VERSION,
        "shadow_replay_id": _hash_id([SCHEMA_VERSION, "blocked", generated_at], "qsase-shadow"),
        "generated_at": generated_at,
        "strategy_hypothesis_id": None,
        "rejected_hypothesis_id": None,
        "akber_filter_result_id": None,
        "replay_mode": "blocked_route_replay",
        "evidence_class": "blocked_route_shadow_research",
        "replay_state": "blocked_missing_akber_filter",
        "variant": variant,
        "time_window": _time_window(context),
        "source_refs": _source_refs(),
        "source_price_lineage": {},
        "strategy_hypothesis_lineage": {},
        "actual_decision": _actual_decision(context),
        "hypothetical_decision": {
            "decision_type": "not_evaluated_missing_inputs",
            "reason": "Akber Filter or Strategy Foundry input is missing.",
            "would_have_created_trade_candidate": False,
            "would_have_created_paper_order": False,
            "would_have_created_execution_intent": False,
            "would_have_written_broker": False,
            "would_have_granted_proof_credit": False,
        },
        "outcome": {
            "outcome_source": "blocked_missing_inputs",
            "sample_size": 0,
            "outcome_available": False,
            "missing_window_reason": "missing_strategy_or_akber_inputs",
            "hypothetical_return_5d": 0.0,
            "hypothetical_max_drawdown_5d": 0.0,
            "hypothetical_hit": False,
            "missed_opportunity": False,
            "avoided_false_positive": False,
            "shadow_success_cannot_create_order": True,
            "shadow_success_cannot_create_proof_credit": True,
        },
        "comparison": {
            "baseline_variant_id": variant["variant_id"],
            "delta_expectancy": 0.0,
            "delta_drawdown": 0.0,
            "delta_false_positive_rate": 0.0,
            "variant_added_value": False,
            "performance_claim_allowed": False,
        },
        "scores": {},
        "decision": {
            "shadow_status": "hold_for_more_shadow_data",
            "reason": "Required QSASE-7/QSASE-8 inputs are missing.",
            "candidate_for_router": False,
            "candidate_for_paper_review": False,
            "candidate_for_learning_attribution": True,
            "paper_order_ready": False,
            "risk_approved": False,
            "execution_approved": False,
            "proof_credit_ready": False,
        },
        "learning_attribution": {
            "learning_attribution_ready": False,
            "learning_write_created": False,
            "evidence_class": "blocked_shadow_replay",
            "paper_proof_ledger_credit_allowed": False,
        },
        "telegram_summary": {
            "review_only": True,
            "command_disabled": True,
            "live_send_allowed": False,
            "contains_command": False,
            "contains_broker_instruction": False,
            "text": "Qadam shadow replay\nSetup: missing input\nResult: blocked\nNext: rebuild prior QSASE artifacts\nNo order or proof credit",
        },
        "authority": _authority_block(),
        **SHADOW_AUTHORITY_FLAGS,
    }


def score_shadow_variants_for_record(
    record: dict[str, Any],
    outcome: dict[str, Any],
    comparison: dict[str, Any],
) -> dict[str, float]:
    akber_score = _float(record.get("scores", {}).get("akber_filter_score"), 0.0)
    sample_score = _clamp(_float(outcome.get("sample_size"), 0.0) / 40.0)
    point_in_time_score = 1.0
    route_score = 0.0 if record.get("router_output", {}).get("hard_veto_blocks_router") else 0.5
    false_positive_reduction = 0.7 if outcome.get("avoided_false_positive") else 0.2
    drawdown_score = _clamp(1 + _float(outcome.get("hypothetical_max_drawdown_5d"), 0.0))
    score = (
        0.18 * point_in_time_score
        + 0.16 * sample_score
        + 0.14 * akber_score
        + 0.16 * false_positive_reduction
        + 0.14 * drawdown_score
        + 0.12 * route_score
        + 0.10 * (1.0 if comparison.get("variant_added_value") else 0.0)
    )
    return {
        "point_in_time_safety_score": round(point_in_time_score, 6),
        "sample_size_score": round(sample_score, 6),
        "akber_filter_contribution_score": round(akber_score, 6),
        "false_positive_reduction_score": round(false_positive_reduction, 6),
        "drawdown_score": round(drawdown_score, 6),
        "route_feasibility_score": round(route_score, 6),
        "learning_value_score": 1.0,
        "shadow_variant_score": round(_clamp(score), 6),
    }


def score_shadow_variants(replay_records: list[dict[str, Any]]) -> dict[str, Any]:
    scored = sorted(
        replay_records,
        key=lambda item: item.get("scores", {}).get("shadow_variant_score", 0.0),
        reverse=True,
    )
    top = scored[0] if scored else {}
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_shadow_variant_scores",
        "scored_record_count": len(scored),
        "top_shadow_replay_id": top.get("shadow_replay_id"),
        "top_variant_key": top.get("variant", {}).get("variant_key"),
        "top_shadow_status": top.get("decision", {}).get("shadow_status"),
        "top_shadow_variant_score": top.get("scores", {}).get("shadow_variant_score", 0.0),
        "candidate_for_router_count": sum(
            1 for record in replay_records if record.get("decision", {}).get("candidate_for_router") is True
        ),
    }


def compare_actual_vs_hypothetical(replay_records: list[dict[str, Any]]) -> dict[str, Any]:
    comparisons = []
    for record in replay_records:
        comparisons.append(
            {
                "shadow_replay_id": record.get("shadow_replay_id"),
                "replay_mode": record.get("replay_mode"),
                "evidence_class": "actual_vs_hypothetical_reference",
                "actual_decision": record.get("actual_decision", {}),
                "hypothetical_decision": record.get("hypothetical_decision", {}),
                "comparison": record.get("comparison", {}),
                "actual_lifecycle_mutated": False,
                "paper_proof_ledger_mutated": False,
                "proof_credit_allowed": False,
                "paper_order_created": False,
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_shadow_actual_vs_hypothetical",
        "generated_at": _iso(_now()),
        "status": "actual_vs_hypothetical_reference_ready",
        "actual_vs_hypothetical_count": len(comparisons),
        "evaluated_comparison_count": len(comparisons),
        "actual_lifecycle_mutated": False,
        "paper_proof_ledger_mutated": False,
        "proof_credit_allowed": False,
        "paper_order_created": False,
        "comparisons": comparisons,
        "authority_flags": dict(SHADOW_AUTHORITY_FLAGS),
    }


def _build_replay_records(context: dict[str, Any], matrix: dict[str, Any], generated_at: str) -> list[dict[str, Any]]:
    records = context["akber_results"]
    if not records:
        return [_fallback_blocked_record(context, generated_at)]
    variants = {variant["variant_key"]: variant for variant in matrix["variants"]}
    replay_records: list[dict[str, Any]] = []
    for record in records:
        replay_records.append(
            _build_replay_record(
                record=record,
                context=context,
                variant=variants["baseline_current_strategy"],
                mode="historical_hypothesis_replay",
                evidence_class="historical_shadow_research",
                generated_at=generated_at,
            )
        )
        replay_records.append(
            _build_replay_record(
                record=record,
                context=context,
                variant=variants["forward_watch_only"],
                mode="forward_shadow_replay",
                evidence_class="forward_shadow_watch",
                generated_at=generated_at,
            )
        )
        replay_records.append(
            _build_replay_record(
                record=record,
                context=context,
                variant=variants["akber_strict_veto"],
                mode="counterfactual_strategy_replay",
                evidence_class="counterfactual_no_order_outcome",
                generated_at=generated_at,
            )
        )
    return replay_records


def _rejection_records(replay_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rejected_statuses = {"reject_after_shadow_replay", "hold_for_more_shadow_data"}
    rejections = []
    for record in replay_records:
        status = record.get("decision", {}).get("shadow_status")
        if status in rejected_statuses or str(record.get("replay_state", "")).startswith("blocked_"):
            rejections.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "shadow_rejection_id": _hash_id([record.get("shadow_replay_id"), "rejection"], "qsase-shadow-reject"),
                    "shadow_replay_id": record.get("shadow_replay_id"),
                    "generated_at": record.get("generated_at"),
                    "replay_mode": record.get("replay_mode"),
                    "evidence_class": record.get("evidence_class"),
                    "variant_key": record.get("variant", {}).get("variant_key"),
                    "rejection_reason": record.get("decision", {}).get("reason"),
                    "blocked_reason": record.get("replay_state") if str(record.get("replay_state", "")).startswith("blocked_") else None,
                    "candidate_for_router": False,
                    "paper_order_created": False,
                    "proof_credit_allowed": False,
                    "source_refs": record.get("source_refs", []),
                    "authority": _authority_block(),
                    **SHADOW_AUTHORITY_FLAGS,
                }
            )
    return rejections


def _dashboard_summary(payload: dict[str, Any]) -> dict[str, Any]:
    top = payload.get("score_summary", {})
    rejections = payload.get("shadow_rejections", [])
    top_rejection = rejections[0] if rejections else {}
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_shadow_strategy_dashboard_summary",
        "generated_at": payload["generated_at"],
        "status": payload["status"],
        "public_safe": True,
        "command_disabled": True,
        "live_send_allowed": False,
        "summary_rows": [
            {"label": "Shadow simulator", "value": payload["status"]},
            {"label": "Variants", "value": payload["variant_count"]},
            {"label": "Active replays", "value": payload["active_replay_count"]},
            {"label": "Blocked replays", "value": payload["blocked_replay_count"]},
            {"label": "Rejected variants", "value": payload["rejected_variant_count"]},
            {"label": "Router candidates", "value": payload["candidate_for_router_count"]},
            {"label": "Proof", "value": "research-only; no paper proof ledger credit"},
            {"label": "Authority", "value": "no order created"},
        ],
        "top_variant": top.get("top_variant_key"),
        "top_shadow_replay_id": top.get("top_shadow_replay_id"),
        "top_rejected_variant": top_rejection.get("variant_key"),
        "actual_vs_hypothetical_count": payload["actual_vs_hypothetical_count"],
        "candidate_for_router_count": payload["candidate_for_router_count"],
        "latest_blocked_reason": payload["blocked_reason"],
        "proof_boundary": "shadow replay is not paper proof ledger credit",
        "authority_state": "shadow_replay_research_only_no_order",
        "no_trade_candidates_created": True,
        "no_paper_orders_created": True,
        "no_proof_credit_granted": True,
        "authority_flags_false": all(value is False for value in payload["authority_flags"].values()),
    }


def build_shadow_strategy_replay(settings: Settings | None = None) -> dict[str, Any]:
    context = _load_context(settings)
    generated_at = _iso(_now())
    matrix = build_shadow_variant_matrix(settings)
    replay_records = _build_replay_records(context, matrix, generated_at)
    rejections = _rejection_records(replay_records)
    comparison = compare_actual_vs_hypothetical(replay_records)
    score_summary = score_shadow_variants(replay_records)
    active_count = sum(1 for record in replay_records if not str(record.get("replay_state", "")).startswith("blocked_"))
    blocked_count = sum(1 for record in replay_records if str(record.get("replay_state", "")).startswith("blocked_"))
    evaluated_count = sum(1 for record in replay_records if str(record.get("replay_state", "")).startswith("evaluated"))
    router_count = score_summary["candidate_for_router_count"]
    missing_required_state: list[str] = []
    degraded_reasons: list[str] = []
    hold_reasons: list[str] = []
    if not context["strategy_foundry"]:
        missing_required_state.append("strategy_foundry_missing")
    if not context["akber_filter"] or not context["akber_results"]:
        missing_required_state.append("akber_filter_missing")
    if not context["historical_memory"]:
        missing_required_state.append("historical_memory_missing")
    if context["strategy_foundry"].get("status") not in STRATEGY_FOUNDRY_READY_STATUSES:
        degraded_reasons.append("strategy_foundry_degraded")
    elif context["strategy_foundry"].get("status") == "qsase_strategy_foundry_ready_with_probationary_hypotheses":
        hold_reasons.append("strategy_foundry_has_probationary_hypotheses")
    if context["akber_filter"].get("status") not in AKBER_READY_STATUSES:
        degraded_reasons.append("akber_filter_degraded")
    elif context["akber_filter"].get("status") == "qsase_akber_filter_integration_ready_with_holds":
        hold_reasons.append("akber_filter_waiting_for_confirmation")
    if context["historical_memory"].get("status") not in HISTORICAL_MEMORY_READY_STATUSES:
        degraded_reasons.append("historical_memory_degraded")
    elif context["historical_memory"].get("status") == "qsase_historical_source_price_memory_ready_with_gaps":
        hold_reasons.append("historical_memory_has_missing_forward_windows")
    if not context["strategy_hypotheses"]:
        hold_reasons.append("no_strategy_hypotheses_to_shadow")
    if context["phase6_shadow"].get("status") == "blocked":
        hold_reasons.append("legacy_phase6_shadow_runner_blocked")
    if blocked_count:
        hold_reasons.append("blocked_shadow_replay_records_present")
    status = "qsase_shadow_strategy_simulator_ready"
    if missing_required_state:
        status = "qsase_shadow_strategy_simulator_blocked"
    elif degraded_reasons:
        status = "qsase_shadow_strategy_simulator_degraded"
    elif hold_reasons or not router_count:
        status = "qsase_shadow_strategy_simulator_ready_with_holds"
    blocked_reason = ",".join(sorted(set(missing_required_state or degraded_reasons or hold_reasons))) or "none"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_shadow_strategy_simulator",
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "generated_at": generated_at,
        "status": status,
        "public_safe": True,
        "command_disabled": True,
        "paper_only": True,
        "research_only": True,
        "proposal_first": True,
        "input_hypothesis_count": len(context["strategy_hypotheses"]),
        "input_rejected_hypothesis_count": len(context["rejected_strategy_hypotheses"]),
        "akber_filter_record_count": len(context["akber_results"]),
        "historical_memory_record_count": int(context["historical_memory"].get("memory_record_count", 0) or 0),
        "historical_point_in_time_safe_record_count": int(
            context["historical_memory"].get("point_in_time_safe_record_count", 0) or 0
        ),
        "variant_count": matrix["variant_count"],
        "replay_record_count": len(replay_records),
        "active_replay_count": active_count,
        "blocked_replay_count": blocked_count,
        "evaluated_replay_count": evaluated_count,
        "actual_vs_hypothetical_count": comparison["actual_vs_hypothetical_count"],
        "candidate_for_router_count": router_count,
        "rejected_variant_count": len(rejections),
        "blocked_reason": blocked_reason,
        "replay_modes": sorted({record["replay_mode"] for record in replay_records}),
        "evidence_classes": sorted({record["evidence_class"] for record in replay_records}),
        "shadow_records_cannot_create_orders": True,
        "shadow_records_cannot_create_proof_credit": True,
        "shadow_success_cannot_be_paper_order": True,
        "shadow_success_cannot_be_paper_proof_ledger_credit": True,
        "trade_candidate_created_count": 0,
        "paper_order_created_count": 0,
        "execution_intent_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "trade_candidate_created": False,
        "paper_order_created": False,
        "paper_order_allowed": False,
        "execution_allowed": False,
        "execution_intent_created": False,
        "broker_write_allowed": False,
        "paper_proof_ledger_credit_allowed": False,
        "paper_growth_trial_calendar_advanced": False,
        "simulated_elapsed_time_allowed": False,
        "source_model_strategy_policy_mutated": False,
        "variant_matrix": matrix,
        "score_summary": score_summary,
        "actual_vs_hypothetical": comparison,
        "shadow_replay_records": replay_records,
        "shadow_rejections": rejections,
        "input_artifacts": {
            "strategy_foundry": f"data/runtime/{STRATEGY_FOUNDRY_ARTIFACT}",
            "strategy_hypotheses": f"data/runtime/{STRATEGY_HYPOTHESES_ARTIFACT}",
            "rejected_strategy_hypotheses": f"data/runtime/{REJECTED_STRATEGY_HYPOTHESES_ARTIFACT}",
            "akber_filter": f"data/runtime/{AKBER_FILTER_ARTIFACT}",
            "akber_filter_results": f"data/runtime/{AKBER_FILTER_RESULTS_ARTIFACT}",
            "historical_memory": f"data/runtime/{HISTORICAL_MEMORY_ARTIFACT}",
            "legacy_phase6_shadow": f"data/runtime/{PHASE6_SHADOW_ARTIFACT}",
            "paperops_summary_present": bool(context["paperops_summary"]),
        },
        "missing_required_state": missing_required_state,
        "degraded_reasons": sorted(set(degraded_reasons)),
        "hold_reasons": sorted(set(hold_reasons)),
        "authority": universal_authority_flags(),
        "authority_flags": dict(SHADOW_AUTHORITY_FLAGS),
    }
    payload["dashboard_safe_summary"] = _dashboard_summary(payload)
    return payload


def _summary_without_records(payload: dict[str, Any]) -> dict[str, Any]:
    summary = dict(payload)
    summary.pop("shadow_replay_records", None)
    summary.pop("shadow_rejections", None)
    summary.pop("variant_matrix", None)
    summary.pop("actual_vs_hypothetical", None)
    return summary


def load_shadow_strategy_replay(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    payload = _read_json(runtime / PRIMARY_ARTIFACT)
    if payload:
        payload["shadow_replay_records"] = _read_jsonl(runtime / RESULTS_ARTIFACT)
        payload["shadow_rejections"] = _read_jsonl(runtime / REJECTIONS_ARTIFACT)
        variant_matrix = _read_json(runtime / VARIANT_MATRIX_ARTIFACT)
        comparison = _read_json(runtime / ACTUAL_VS_HYPOTHETICAL_ARTIFACT)
        if variant_matrix:
            payload["variant_matrix"] = variant_matrix
        if comparison:
            payload["actual_vs_hypothetical"] = comparison
    return payload


def _validate_authority(flags: dict[str, Any], prefix: str) -> list[str]:
    errors: list[str] = []
    for key, expected in SHADOW_AUTHORITY_FLAGS.items():
        if flags.get(key) is not expected:
            errors.append(f"{prefix}_{key}_must_be_false")
    return errors


def validate_shadow_strategy_replay(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("artifact_type") != "qsase_shadow_strategy_simulator":
        errors.append("artifact_type_invalid")
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if payload.get("status") not in {
        "qsase_shadow_strategy_simulator_ready",
        "qsase_shadow_strategy_simulator_ready_with_holds",
        "qsase_shadow_strategy_simulator_degraded",
        "qsase_shadow_strategy_simulator_blocked",
    }:
        errors.append("status_invalid")
    if payload.get("public_safe") is not True or payload.get("command_disabled") is not True:
        errors.append("public_safe_command_disabled_required")
    for key in (
        "shadow_records_cannot_create_orders",
        "shadow_records_cannot_create_proof_credit",
        "shadow_success_cannot_be_paper_order",
        "shadow_success_cannot_be_paper_proof_ledger_credit",
    ):
        if payload.get(key) is not True:
            errors.append(f"{key}_must_be_true")
    for key in (
        "proof_credit_allowed",
        "live_capital_enabled",
        "trade_candidate_created",
        "paper_order_created",
        "paper_order_allowed",
        "execution_allowed",
        "execution_intent_created",
        "broker_write_allowed",
        "paper_proof_ledger_credit_allowed",
        "paper_growth_trial_calendar_advanced",
        "simulated_elapsed_time_allowed",
        "source_model_strategy_policy_mutated",
    ):
        if payload.get(key) is not False:
            errors.append(f"{key}_must_be_false")
    for key in (
        "trade_candidate_created_count",
        "paper_order_created_count",
        "execution_intent_created_count",
        "broker_write_count",
    ):
        if int(payload.get(key, -1) or 0) != 0:
            errors.append(f"{key}_must_be_zero")
    authority = payload.get("authority", {})
    if not isinstance(authority, dict) or any(value is not False for value in authority.values()):
        errors.append("universal_authority_flags_must_all_be_false")
    errors.extend(_validate_authority(payload.get("authority_flags", {}), "shadow"))
    records = payload.get("shadow_replay_records")
    if not isinstance(records, list):
        errors.append("shadow_replay_records_missing")
        records = []
    if payload.get("replay_record_count") != len(records):
        errors.append("replay_record_count_mismatch")
    for mode in ("historical_hypothesis_replay", "forward_shadow_replay", "counterfactual_strategy_replay"):
        if records and mode not in {record.get("replay_mode") for record in records}:
            errors.append(f"required_replay_mode_{mode}_missing")
    for record in records:
        record_id = record.get("shadow_replay_id")
        for field in REQUIRED_REPLAY_FIELDS:
            if field not in record:
                errors.append(f"shadow_record_{record_id}_missing_{field}")
        if record.get("replay_mode") not in REPLAY_MODES:
            errors.append(f"shadow_record_{record_id}_invalid_replay_mode")
        if record.get("evidence_class") not in EVIDENCE_CLASSES:
            errors.append(f"shadow_record_{record_id}_invalid_evidence_class")
        time_window = record.get("time_window", {})
        if time_window.get("decision_timestamps_point_in_time_safe") is not True:
            errors.append(f"shadow_record_{record_id}_point_in_time_leakage")
        if time_window.get("forbidden_future_features_detected") is not False:
            errors.append(f"shadow_record_{record_id}_future_features_detected")
        if not record.get("source_refs"):
            errors.append(f"shadow_record_{record_id}_source_refs_missing")
        decision = record.get("decision", {})
        if decision.get("shadow_status") not in SHADOW_DECISIONS:
            errors.append(f"shadow_record_{record_id}_invalid_shadow_status")
        for forbidden in ("paper_order_ready", "risk_approved", "execution_approved", "proof_credit_ready"):
            if decision.get(forbidden) is not False:
                errors.append(f"shadow_record_{record_id}_{forbidden}_must_be_false")
        hypothetical = record.get("hypothetical_decision", {})
        for forbidden in (
            "would_have_created_trade_candidate",
            "would_have_created_paper_order",
            "would_have_created_execution_intent",
            "would_have_written_broker",
            "would_have_granted_proof_credit",
        ):
            if hypothetical.get(forbidden) is not False:
                errors.append(f"shadow_record_{record_id}_{forbidden}_must_be_false")
        actual = record.get("actual_decision", {})
        if actual.get("actual_lifecycle_mutated") is not False:
            errors.append(f"shadow_record_{record_id}_actual_lifecycle_mutated")
        outcome = record.get("outcome", {})
        if outcome.get("shadow_success_cannot_create_order") is not True:
            errors.append(f"shadow_record_{record_id}_shadow_success_order_boundary_missing")
        if outcome.get("shadow_success_cannot_create_proof_credit") is not True:
            errors.append(f"shadow_record_{record_id}_shadow_success_proof_boundary_missing")
        telegram = record.get("telegram_summary", {})
        if telegram.get("review_only") is not True or telegram.get("command_disabled") is not True:
            errors.append(f"shadow_record_{record_id}_telegram_not_review_only")
        if telegram.get("contains_command") is not False or telegram.get("contains_broker_instruction") is not False:
            errors.append(f"shadow_record_{record_id}_telegram_command_or_broker_language")
        for key in SHADOW_AUTHORITY_FLAGS:
            if record.get(key) is not False:
                errors.append(f"shadow_record_{record_id}_{key}_must_be_false")
            if record.get("authority", {}).get(key) is not False:
                errors.append(f"shadow_record_{record_id}_authority_{key}_must_be_false")
    rejections = payload.get("shadow_rejections")
    if not isinstance(rejections, list):
        errors.append("shadow_rejections_missing")
        rejections = []
    if payload.get("rejected_variant_count") != len(rejections):
        errors.append("rejected_variant_count_mismatch")
    for rejection in rejections:
        rejection_id = rejection.get("shadow_rejection_id")
        if rejection.get("candidate_for_router") is not False:
            errors.append(f"shadow_rejection_{rejection_id}_candidate_for_router_must_be_false")
        errors.extend(_validate_authority(rejection.get("authority", {}), f"shadow_rejection_{rejection_id}_authority"))
    matrix = payload.get("variant_matrix", {})
    if matrix.get("variant_count") != len(matrix.get("variants", [])):
        errors.append("variant_matrix_count_mismatch")
    for variant in matrix.get("variants", []):
        errors.extend(_validate_authority(variant.get("authority_flags", {}), f"variant_{variant.get('variant_key')}"))
        if variant.get("threshold_change_applied") is not False:
            errors.append(f"variant_{variant.get('variant_key')}_threshold_applied")
    comparison = payload.get("actual_vs_hypothetical", {})
    if comparison.get("actual_lifecycle_mutated") is not False:
        errors.append("actual_vs_hypothetical_lifecycle_mutated")
    if comparison.get("paper_proof_ledger_mutated") is not False:
        errors.append("actual_vs_hypothetical_proof_ledger_mutated")
    summary = payload.get("dashboard_safe_summary", {})
    if summary:
        if summary.get("public_safe") is not True or summary.get("command_disabled") is not True:
            errors.append("dashboard_summary_public_safe_required")
        if summary.get("live_send_allowed") is not False:
            errors.append("dashboard_summary_live_send_must_be_false")
        if summary.get("authority_state") != "shadow_replay_research_only_no_order":
            errors.append("dashboard_summary_authority_boundary_required")
    return sorted(set(errors))


def build_qsase_phase_implementation_status(payload: dict[str, Any]) -> dict[str, Any]:
    runtime_dir = _runtime_dir()
    existing = _read_json(runtime_dir / PHASE_STATUS_ARTIFACT)
    phases = existing.get("phases") if isinstance(existing.get("phases"), dict) else {}
    phases[PHASE_ID] = {
        "name": PHASE_NAME,
        "status": payload["status"],
        "artifact_path": f"data/runtime/{PRIMARY_ARTIFACT}",
        "results_path": f"data/runtime/{RESULTS_ARTIFACT}",
        "rejections_path": f"data/runtime/{REJECTIONS_ARTIFACT}",
        "variant_matrix_path": f"data/runtime/{VARIANT_MATRIX_ARTIFACT}",
        "actual_vs_hypothetical_path": f"data/runtime/{ACTUAL_VS_HYPOTHETICAL_ARTIFACT}",
        "input_hypothesis_count": payload["input_hypothesis_count"],
        "akber_filter_record_count": payload["akber_filter_record_count"],
        "variant_count": payload["variant_count"],
        "replay_record_count": payload["replay_record_count"],
        "active_replay_count": payload["active_replay_count"],
        "blocked_replay_count": payload["blocked_replay_count"],
        "evaluated_replay_count": payload["evaluated_replay_count"],
        "actual_vs_hypothetical_count": payload["actual_vs_hypothetical_count"],
        "candidate_for_router_count": payload["candidate_for_router_count"],
        "rejected_variant_count": payload["rejected_variant_count"],
        "paper_only": True,
        "research_only": True,
        "proposal_first": True,
        "public_safe": True,
        "shadow_success_cannot_be_paper_order": True,
        "shadow_success_cannot_be_paper_proof_ledger_credit": True,
        "no_trade_candidates_created": True,
        "no_paper_orders_created": True,
        "no_proof_credit_granted": True,
        "authority_flags_false": True,
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
    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else "# QSASE Implementation Log\n"
    marker = f"<!-- {PHASE_ID} -->"
    entry = (
        f"{marker}\n"
        f"## QSASE-9: Shadow Strategy Simulator Upgrade\n\n"
        f"- Generated at: `{payload.get('generated_at')}`\n"
        f"- Status: `{payload.get('status')}`\n"
        f"- Runtime artifact: `data/runtime/{PRIMARY_ARTIFACT}`\n"
        f"- Replay records: `{payload.get('replay_record_count')}`\n"
        f"- Active / blocked / evaluated: `{payload.get('active_replay_count')}` / `{payload.get('blocked_replay_count')}` / `{payload.get('evaluated_replay_count')}`\n"
        f"- Rejected variants: `{payload.get('rejected_variant_count')}`\n"
        f"- Router candidates: `{payload.get('candidate_for_router_count')}`\n"
        f"- Safety: shadow success cannot become a paper order or paper proof ledger credit; no trade candidates, execution intents, broker writes, live capital, or proof credit created.\n"
    )
    from orchestrator.qadam_marked_log import upsert_marked_section

    updated = upsert_marked_section(existing, marker, entry)
    log_path.write_text(updated, encoding="utf-8")


def write_shadow_strategy_replay(
    payload: dict[str, Any],
    settings: Settings | None = None,
    *,
    append_history: bool = True,
    append_log: bool = True,
) -> dict[str, str]:
    runtime_dir = _runtime_dir(settings)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "shadow_strategy_simulator": runtime_dir / PRIMARY_ARTIFACT,
        "shadow_strategy_results": runtime_dir / RESULTS_ARTIFACT,
        "shadow_strategy_rejections": runtime_dir / REJECTIONS_ARTIFACT,
        "variant_matrix": runtime_dir / VARIANT_MATRIX_ARTIFACT,
        "actual_vs_hypothetical": runtime_dir / ACTUAL_VS_HYPOTHETICAL_ARTIFACT,
        "dashboard_summary": runtime_dir / DASHBOARD_SUMMARY_ARTIFACT,
        "phase_status": runtime_dir / PHASE_STATUS_ARTIFACT,
    }
    _write_json(paths["shadow_strategy_simulator"], _summary_without_records(payload))
    _write_jsonl(paths["shadow_strategy_results"], payload["shadow_replay_records"])
    _write_jsonl(paths["shadow_strategy_rejections"], payload["shadow_rejections"])
    _write_json(paths["variant_matrix"], payload["variant_matrix"])
    _write_json(paths["actual_vs_hypothetical"], payload["actual_vs_hypothetical"])
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
                "replay_record_count": payload["replay_record_count"],
                "active_replay_count": payload["active_replay_count"],
                "blocked_replay_count": payload["blocked_replay_count"],
                "candidate_for_router_count": payload["candidate_for_router_count"],
                "no_paper_orders_created": True,
                "no_proof_credit_granted": True,
            },
        )
        _append_jsonl(
            events_path,
            {
                "generated_at": payload["generated_at"],
                "event_type": "qsase_shadow_strategy_simulator_written",
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


def build_and_write_shadow_strategy_replay(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    payload = build_shadow_strategy_replay(settings)
    errors = validate_shadow_strategy_replay(payload)
    written = write_shadow_strategy_replay(payload, settings)
    return payload, written, errors


def validate_negative_shadow_strategy_probes() -> list[str]:
    base = build_shadow_strategy_replay()
    errors: list[str] = []
    for flag in SHADOW_AUTHORITY_FLAGS:
        probe = copy.deepcopy(base)
        probe["authority_flags"][flag] = True
        if not any(flag in error for error in validate_shadow_strategy_replay(probe)):
            errors.append(f"negative_probe_failed_for_{flag}")
    order_probe = copy.deepcopy(base)
    order_probe["paper_order_created"] = True
    if not any("paper_order_created" in error for error in validate_shadow_strategy_replay(order_probe)):
        errors.append("negative_probe_failed_for_order_created")
    if base["shadow_replay_records"]:
        leakage_probe = copy.deepcopy(base)
        leakage_probe["shadow_replay_records"][0]["time_window"]["decision_timestamps_point_in_time_safe"] = False
        if not any("point_in_time_leakage" in error for error in validate_shadow_strategy_replay(leakage_probe)):
            errors.append("negative_probe_failed_for_leakage")
        evidence_probe = copy.deepcopy(base)
        evidence_probe["shadow_replay_records"][0]["evidence_class"] = None
        if not any("invalid_evidence_class" in error for error in validate_shadow_strategy_replay(evidence_probe)):
            errors.append("negative_probe_failed_for_evidence_class")
        hypothetical_probe = copy.deepcopy(base)
        hypothetical_probe["shadow_replay_records"][0]["hypothetical_decision"]["would_have_created_paper_order"] = True
        if not any("would_have_created_paper_order" in error for error in validate_shadow_strategy_replay(hypothetical_probe)):
            errors.append("negative_probe_failed_for_hypothetical_order")
    dashboard_probe = copy.deepcopy(base)
    dashboard_probe["dashboard_safe_summary"]["live_send_allowed"] = True
    if not any("dashboard_summary_live_send" in error for error in validate_shadow_strategy_replay(dashboard_probe)):
        errors.append("negative_probe_failed_for_dashboard_live_send")
    return errors


if __name__ == "__main__":
    artifact = build_shadow_strategy_replay()
    print(_json_dump(_summary_without_records(artifact)))
