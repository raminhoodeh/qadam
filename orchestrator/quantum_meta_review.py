"""Read-only quantum meta-review for Qadam.

Stage 4D reviews whether Qadam's recursive edge-learning chain is internally
coherent: quantum gate, pattern engine, edge memory, strategy updates,
hypothesis lifecycle, and strategy weight proposals. It is a meta-review layer
only. It can document whether the learning loop is ready for further human or
guarded review, but it cannot apply weights, mutate strategy, size orders, call
providers, approve risk, or submit paper trades.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.edge_memory_ledger import validate_edge_memory_ledger
from orchestrator.hypothesis_lifecycle import validate_hypothesis_lifecycle
from orchestrator.pattern_recognition_engine import validate_pattern_recognition_engine
from orchestrator.quantum_mandatory_review_gate import (
    validate_quantum_mandatory_review_gate,
)
from orchestrator.strategy_update_record import validate_strategy_update_record
from orchestrator.strategy_weight_updates import (
    STRATEGY_FAMILIES,
    STRATEGY_WEIGHT_UPDATES_AUTHORITY_FALSE_FIELDS,
    validate_strategy_weight_updates,
)


QUANTUM_META_REVIEW_SCHEMA_VERSION = 1
QUANTUM_META_REVIEW_RUNTIME_ARTIFACT = "quantum_meta_review.json"
QUANTUM_META_REVIEW_HISTORY = "quantum_meta_review_history.jsonl"
QUANTUM_META_REVIEW_EVENT_LOG = "quantum_meta_review_events.jsonl"
QUANTUM_META_REVIEW_EVENT_TYPE = "quantum_meta_review_recorded"
QUANTUM_META_REVIEW_COMPONENT = "quantum_meta_review"

QUANTUM_META_REVIEW_AUTHORITY_FALSE_FIELDS: tuple[str, ...] = tuple(
    dict.fromkeys(
        (
            *STRATEGY_WEIGHT_UPDATES_AUTHORITY_FALSE_FIELDS,
            "quantum_meta_review_apply_allowed",
            "quantum_meta_review_applied",
            "recursive_strategy_mutation_allowed",
            "strategy_weight_application_allowed",
            "active_strategy_weight_mutation_allowed",
            "portfolio_rebalance_allowed",
            "paper_trading_decision_allowed",
            "paper_trade_submission_allowed",
            "broker_order_authority",
            "risk_override_allowed",
            "quantum_provider_call_allowed",
            "quantum_hardware_submission_allowed",
            "telegram_live_send_allowed",
        )
    )
)

QUANTUM_META_REVIEW_STATUSES = {
    "quantum_meta_review_ready",
    "quantum_meta_review_blocked_pending_strategy_weight_updates",
}

QUANTUM_META_REVIEW_BOUNDARY = (
    "Quantum Meta-Review is a read-only recursive-improvement audit. It can "
    "compare the quantum gate, pattern engine, edge memory, strategy updates, "
    "hypothesis lifecycle, and strategy weight proposals for coherence, but it "
    "cannot apply strategy weights, mutate active strategy, rebalance a "
    "portfolio, size orders, approve risk, submit paper orders, write brokers, "
    "send live Telegram commands, call quantum providers, submit hardware jobs, "
    "enable live capital, or grant proof credit."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def quantum_meta_review_paths(settings: Settings | None = None) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / QUANTUM_META_REVIEW_RUNTIME_ARTIFACT,
        runtime / QUANTUM_META_REVIEW_HISTORY,
        runtime / QUANTUM_META_REVIEW_EVENT_LOG,
    )


def read_quantum_meta_review(settings: Settings | None = None) -> dict[str, Any]:
    output_path, _, _ = quantum_meta_review_paths(settings)
    if not output_path.exists():
        return {}
    try:
        payload = json.loads(output_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clip(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 6)


def _slug(value: Any) -> str:
    return str(value or "").strip().replace(" ", "_").lower() or "unknown"


def _weight_key(family: dict[str, str]) -> str:
    return family["strategy_family_key"]


def _weight_sum(weights: dict[str, Any]) -> float:
    return round(sum(float(value) for value in weights.values()), 6)


def _records_by_sleeve(records: list[Any]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for record in records:
        if isinstance(record, dict):
            sleeve = _slug(record.get("sleeve_key"))
            if sleeve != "unknown":
                output[sleeve] = record
    return output


def _threads_by_sleeve(threads: list[Any]) -> dict[str, list[dict[str, Any]]]:
    output: dict[str, list[dict[str, Any]]] = {}
    for thread in threads:
        if not isinstance(thread, dict):
            continue
        sleeve = _slug(thread.get("sleeve_key"))
        if sleeve != "unknown":
            output.setdefault(sleeve, []).append(thread)
    return output


def _gate_decisions_by_sleeve(quantum_gate: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return _records_by_sleeve(_as_list(quantum_gate.get("pattern_gate_decisions")))


def _lifecycle_score(threads: list[dict[str, Any]]) -> float:
    if not threads:
        return 0.2
    score = 0.0
    for thread in threads:
        state = str(thread.get("lifecycle_state") or "")
        if state == "ready_for_signal_integrity_review":
            score += 0.95
        elif state == "retained_for_shadow_review":
            score += 0.75
        elif state == "held_for_independent_corroboration":
            score += 0.56
        elif state == "held_for_quantum_or_edge_mapping":
            score += 0.42
        elif state == "refutation_candidate_not_applied":
            score += 0.22
        elif state == "blocked_source_execution_authority_present":
            score += 0.05
        else:
            score += 0.25
    return _clip(score / len(threads))


def _strategy_alignment(
    strategy_proposal: dict[str, Any],
    weight_record: dict[str, Any],
) -> tuple[bool, str]:
    adjustment = str(strategy_proposal.get("proposed_adjustment") or "")
    proposed_delta = _float(weight_record.get("proposed_weight_delta"))
    if adjustment in {
        "raise_watch_priority_after_more_persistence",
        "maintain_high_watch_priority",
    }:
        return proposed_delta >= -0.003, "raise_or_maintain_consistent_with_weight_delta"
    if adjustment == "review_for_persistence_based_threshold_proposal":
        return abs(proposed_delta) <= 0.035 or proposed_delta >= -0.005, (
            "threshold_review_kept_within_small_delta"
        )
    if adjustment == "hold_or_lower_confidence_until_ambiguity_falls":
        return proposed_delta <= 0.001, "hold_or_lower_consistent_with_weight_delta"
    return abs(proposed_delta) <= 0.02, "unknown_adjustment_kept_near_neutral"


def _meta_score(
    *,
    pattern: dict[str, Any],
    edge_memory: dict[str, Any],
    strategy_proposal: dict[str, Any],
    hypothesis_threads: list[dict[str, Any]],
    weight_record: dict[str, Any],
    gate_decision: dict[str, Any],
) -> float:
    alignment_ok, _ = _strategy_alignment(strategy_proposal, weight_record)
    signal_strength = _float(pattern.get("compressed_oracle_register", {}).get("q0_signal_strength"))
    if not signal_strength:
        signal_strength = _float(edge_memory.get("latest_signal_strength"))
    ambiguity = _float(pattern.get("ambiguity_score"), _float(edge_memory.get("latest_ambiguity_score")))
    readiness = _float(edge_memory.get("latest_edge_readiness_score"))
    weight_strength = _float(weight_record.get("proposal_strength_score"))
    lifecycle = _lifecycle_score(hypothesis_threads)
    quantum = 1.0 if gate_decision.get("dependency_satisfied") is True else 0.0
    oracle_contract = (
        1.0
        if pattern.get("quantum_oracle_input_contract_status") == "accepted"
        and weight_record.get("quantum_oracle_input_contract_status") == "accepted"
        else 0.0
    )
    alignment = 1.0 if alignment_ok else 0.0
    score = (
        0.18 * quantum
        + 0.16 * oracle_contract
        + 0.16 * readiness
        + 0.14 * signal_strength
        + 0.14 * weight_strength
        + 0.12 * lifecycle
        + 0.10 * alignment
        - 0.10 * ambiguity
    )
    return _clip(score)


def _review_record(
    *,
    family: dict[str, str],
    pattern: dict[str, Any],
    edge_memory: dict[str, Any],
    strategy_proposal: dict[str, Any],
    hypothesis_threads: list[dict[str, Any]],
    weight_record: dict[str, Any],
    gate_decision: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    sleeve_key = family["sleeve_key"]
    family_key = family["strategy_family_key"]
    alignment_ok, alignment_reason = _strategy_alignment(strategy_proposal, weight_record)
    meta_score = _meta_score(
        pattern=pattern,
        edge_memory=edge_memory,
        strategy_proposal=strategy_proposal,
        hypothesis_threads=hypothesis_threads,
        weight_record=weight_record,
        gate_decision=gate_decision,
    )
    quantum_dependency_satisfied = (
        gate_decision.get("dependency_satisfied") is True
        and pattern.get("quantum_gate_dependency_satisfied") is True
        and edge_memory.get("quantum_gate_dependency_satisfied") is True
        and strategy_proposal.get("quantum_dependency_satisfied") is True
        and weight_record.get("quantum_dependency_satisfied") is True
    )
    oracle_contract_accepted = (
        pattern.get("quantum_oracle_input_contract_status") == "accepted"
        and edge_memory.get("quantum_oracle_input_contract_status") == "accepted"
        and strategy_proposal.get("quantum_oracle_input_contract_status") == "accepted"
        and weight_record.get("quantum_oracle_input_contract_status") == "accepted"
    )
    optimized_for_quantum_oracle = (
        pattern.get("optimized_for_quantum_oracle") is True
        and edge_memory.get("optimized_for_quantum_oracle") is True
        and strategy_proposal.get("optimized_for_quantum_oracle") is True
        and weight_record.get("optimized_for_quantum_oracle") is True
    )
    hypothesis_lifecycle_linked = len(hypothesis_threads) > 0
    hold_reasons: list[str] = []
    if not quantum_dependency_satisfied:
        hold_reasons.append("quantum_dependency_not_satisfied")
    if not oracle_contract_accepted:
        hold_reasons.append("oracle_contract_not_accepted")
    if not optimized_for_quantum_oracle:
        hold_reasons.append("not_optimized_for_quantum_oracle")
    if not alignment_ok:
        hold_reasons.append("strategy_update_weight_delta_alignment_missing")
    if not hypothesis_lifecycle_linked:
        hold_reasons.append("hypothesis_lifecycle_thread_missing")
    if meta_score < 0.45:
        hold_reasons.append("meta_review_score_below_threshold")
    meta_review_passed = (
        quantum_dependency_satisfied
        and oracle_contract_accepted
        and optimized_for_quantum_oracle
        and alignment_ok
        and hypothesis_lifecycle_linked
        and meta_score >= 0.45
    )
    delta = _float(weight_record.get("proposed_weight_delta"))
    if delta > 0.002:
        recommendation = "observe_research_priority_raise_without_applying"
    elif delta < -0.002:
        recommendation = "observe_research_priority_reduction_without_applying"
    else:
        recommendation = "maintain_research_priority_without_applying"
    review_id = "quantum-meta-review:" + sha256(
        json.dumps(
            {
                "sleeve_key": sleeve_key,
                "strategy_family_key": family_key,
                "pattern_id": pattern.get("pattern_id"),
                "edge_memory_id": edge_memory.get("memory_id"),
                "strategy_update_id": strategy_proposal.get("update_id"),
                "weight_update_id": weight_record.get("weight_update_id"),
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:18]
    record = {
        "meta_review_id": review_id,
        "status": "quantum_meta_review_coherent_not_applied"
        if meta_review_passed
        else "quantum_meta_review_holds_for_more_evidence",
        "decision_status": "reviewed_not_applied",
        "sleeve_key": sleeve_key,
        "instrument_key": family["instrument_key"],
        "strategy_family_key": family_key,
        "strategy_family_name": family["strategy_family_name"],
        "meta_review_passed": meta_review_passed,
        "meta_review_score": meta_score,
        "alignment_ok": alignment_ok,
        "alignment_reason": alignment_reason,
        "hold_reasons": sorted(set(hold_reasons)),
        "recommendation": recommendation,
        "recommendation_scope": "research_priority_only",
        "quantum_required": True,
        "quantum_dependency_satisfied": quantum_dependency_satisfied,
        "quantum_gate_decision_status": gate_decision.get("status", "not_exported"),
        "quantum_review_status": gate_decision.get("review_status", "not_exported"),
        "quantum_backend": gate_decision.get("review_backend", "not_exported"),
        "fire_opal_ibm_status": gate_decision.get("fire_opal_ibm_status", "not_exported"),
        "oracle_contract_accepted": oracle_contract_accepted,
        "optimized_for_quantum_oracle": optimized_for_quantum_oracle,
        "pattern_id": pattern.get("pattern_id"),
        "edge_memory_id": edge_memory.get("memory_id"),
        "strategy_update_id": strategy_proposal.get("update_id"),
        "strategy_weight_update_id": weight_record.get("weight_update_id"),
        "hypothesis_lifecycle_ids": sorted(
            str(thread.get("lifecycle_id"))
            for thread in hypothesis_threads
            if thread.get("lifecycle_id")
        ),
        "hypothesis_lifecycle_linked": hypothesis_lifecycle_linked,
        "hypothesis_lifecycle_thread_count": len(hypothesis_threads),
        "hypothesis_lifecycle_states": sorted(
            {str(thread.get("lifecycle_state") or "unknown") for thread in hypothesis_threads}
        ),
        "latest_edge_readiness_score": _clip(
            _float(edge_memory.get("latest_edge_readiness_score"))
        ),
        "latest_signal_strength": _clip(_float(edge_memory.get("latest_signal_strength"))),
        "latest_ambiguity_score": _clip(_float(edge_memory.get("latest_ambiguity_score"))),
        "proposal_strength_score": _clip(_float(weight_record.get("proposal_strength_score"))),
        "active_before_weight": weight_record.get("active_before_weight"),
        "active_after_weight": weight_record.get("active_after_weight"),
        "proposed_after_weight": weight_record.get("proposed_after_weight"),
        "proposed_weight_delta": weight_record.get("proposed_weight_delta"),
        "applied_weight_delta": 0.0,
        "active_weights_unchanged": (
            weight_record.get("active_before_weight") == weight_record.get("active_after_weight")
        ),
        "meta_review_rationale": (
            "Quantum meta-review checks whether the recursive learning chain is "
            "coherent enough to keep observing this strategy-family weight "
            "proposal. It does not apply the proposal."
        ),
        "apply_condition": (
            "A later explicit approval path must compare this review against "
            "paper outcomes, Signal Integrity, Risk, Q-CTRL consultation, and "
            "human governance before any strategy or sizing mutation."
        ),
        "rollback_condition": (
            "Hold or reduce if quantum dependency breaks, oracle contracts stop "
            "being accepted, ambiguity rises, or the hypothesis lifecycle "
            "regresses."
        ),
        "reviewed_at": generated_at,
        "applied": False,
        "applied_at": None,
    }
    for field in QUANTUM_META_REVIEW_AUTHORITY_FALSE_FIELDS:
        record[field] = False
    return record


def build_quantum_meta_review(
    *,
    quantum_gate: dict[str, Any],
    pattern_recognition_engine: dict[str, Any],
    edge_memory_ledger: dict[str, Any],
    strategy_update_record: dict[str, Any],
    hypothesis_lifecycle: dict[str, Any],
    strategy_weight_updates: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build Qadam's Stage 4D quantum meta-review artifact."""

    generated_at = generated_at or _now()
    validate_quantum_mandatory_review_gate(quantum_gate)
    validate_pattern_recognition_engine(pattern_recognition_engine)
    validate_edge_memory_ledger(edge_memory_ledger)
    validate_strategy_update_record(strategy_update_record)
    validate_hypothesis_lifecycle(hypothesis_lifecycle)
    validate_strategy_weight_updates(strategy_weight_updates)
    dependency_ready = (
        quantum_gate.get("status") == "quantum_review_gate_passed"
        and pattern_recognition_engine.get("status") == "pattern_engine_ready_for_quantum_oracle"
        and edge_memory_ledger.get("status") == "edge_memory_active"
        and strategy_update_record.get("status") == "strategy_update_record_ready"
        and hypothesis_lifecycle.get("status") == "hypothesis_lifecycle_active"
        and strategy_weight_updates.get("status") == "strategy_weight_updates_ready"
    )
    status = (
        "quantum_meta_review_ready"
        if dependency_ready
        else "quantum_meta_review_blocked_pending_strategy_weight_updates"
    )
    pattern_by_sleeve = _records_by_sleeve(
        _as_list(pattern_recognition_engine.get("candidate_patterns"))
    )
    edge_by_sleeve = _records_by_sleeve(_as_list(edge_memory_ledger.get("memory_records")))
    strategy_by_sleeve = _records_by_sleeve(_as_list(strategy_update_record.get("proposals")))
    threads_by_sleeve = _threads_by_sleeve(
        _as_list(hypothesis_lifecycle.get("hypothesis_threads"))
    )
    weight_by_sleeve = _records_by_sleeve(
        _as_list(strategy_weight_updates.get("weight_update_records"))
    )
    gate_by_sleeve = _gate_decisions_by_sleeve(quantum_gate)
    records = [
        _review_record(
            family=family,
            pattern=pattern_by_sleeve.get(family["sleeve_key"], {}),
            edge_memory=edge_by_sleeve.get(family["sleeve_key"], {}),
            strategy_proposal=strategy_by_sleeve.get(family["sleeve_key"], {}),
            hypothesis_threads=threads_by_sleeve.get(family["sleeve_key"], []),
            weight_record=weight_by_sleeve.get(family["sleeve_key"], {}),
            gate_decision=gate_by_sleeve.get(family["sleeve_key"], {}),
            generated_at=generated_at,
        )
        for family in STRATEGY_FAMILIES
        if status == "quantum_meta_review_ready"
    ]
    passed_count = sum(1 for record in records if record["meta_review_passed"] is True)
    blocked_count = len(records) - passed_count
    oracle_contract_accepted_count = sum(
        1 for record in records if record["oracle_contract_accepted"] is True
    )
    hypothesis_lifecycle_linked_count = sum(
        1 for record in records if record["hypothesis_lifecycle_linked"] is True
    )
    quantum_dependency_satisfied_count = sum(
        1 for record in records if record["quantum_dependency_satisfied"] is True
    )
    active_before_weights = dict(strategy_weight_updates.get("active_before_weights") or {})
    active_after_weights = dict(strategy_weight_updates.get("active_after_weights") or {})
    proposed_after_weights = dict(strategy_weight_updates.get("proposed_after_weights") or {})
    loop_passed = dependency_ready and len(records) == len(STRATEGY_FAMILIES) and blocked_count == 0
    artifact = {
        "schema_version": QUANTUM_META_REVIEW_SCHEMA_VERSION,
        "artifact_type": "quantum_meta_review",
        "artifact_id": "quantum-meta-review:latest",
        "stage": "Stage 4D - Quantum Meta-Review",
        "generated_at": generated_at,
        "status": status,
        "public_safe": True,
        "purpose": (
            "Review whether Qadam's quantum-reviewed pattern recognition, edge "
            "memory, hypothesis lifecycle, strategy updates, and strategy "
            "weight proposals form a coherent recursive-improvement record "
            "without applying the proposals."
        ),
        "quantum_gate_status": quantum_gate.get("status"),
        "pattern_engine_status": pattern_recognition_engine.get("status"),
        "edge_memory_ledger_status": edge_memory_ledger.get("status"),
        "strategy_update_record_status": strategy_update_record.get("status"),
        "hypothesis_lifecycle_status": hypothesis_lifecycle.get("status"),
        "strategy_weight_updates_status": strategy_weight_updates.get("status"),
        "strategy_family_count": len(STRATEGY_FAMILIES),
        "quantum_meta_review_count": len(records),
        "quantum_meta_review_passed_count": passed_count,
        "quantum_meta_review_blocked_count": blocked_count,
        "quantum_meta_review_hold_count": blocked_count,
        "quantum_dependency_satisfied_count": quantum_dependency_satisfied_count,
        "oracle_contract_accepted_count": oracle_contract_accepted_count,
        "hypothesis_lifecycle_linked_count": hypothesis_lifecycle_linked_count,
        "strategy_weight_update_proposal_count": strategy_weight_updates.get(
            "strategy_weight_update_proposal_count",
            0,
        ),
        "strategy_weight_update_applied_count": strategy_weight_updates.get(
            "strategy_weight_update_applied_count",
            0,
        ),
        "meta_review_applied_count": 0,
        "active_strategy_weight_mutation_count": strategy_weight_updates.get(
            "active_strategy_weight_mutation_count",
            0,
        ),
        "active_before_weights": active_before_weights,
        "active_after_weights": active_after_weights,
        "proposed_after_weights": proposed_after_weights,
        "proposed_weight_delta": dict(strategy_weight_updates.get("proposed_weight_delta") or {}),
        "applied_weight_delta": dict(strategy_weight_updates.get("applied_weight_delta") or {}),
        "active_before_weight_sum": _weight_sum(active_before_weights),
        "active_after_weight_sum": _weight_sum(active_after_weights),
        "proposed_after_weight_sum": _weight_sum(proposed_after_weights),
        "proposed_weight_delta_total_abs": strategy_weight_updates.get(
            "proposed_weight_delta_total_abs",
            0.0,
        ),
        "applied_weight_delta_total_abs": strategy_weight_updates.get(
            "applied_weight_delta_total_abs",
            0.0,
        ),
        "loop_level_decision": {
            "status": "quantum_meta_review_coherent"
            if loop_passed
            else "quantum_meta_review_completed_with_holds"
            if dependency_ready
            else "quantum_meta_review_blocked",
            "review_scope": "recursive_edge_learning_chain",
            "meta_review_passed": loop_passed,
            "recommendation_only": True,
            "active_weights_unchanged": active_before_weights == active_after_weights,
            "can_update_strategy_weights": False,
            "can_mutate_strategy": False,
            "can_change_order_sizing": False,
            "can_submit_paper_orders": False,
            "can_call_brokers": False,
            "can_call_quantum_providers": False,
            "can_send_live_telegram": False,
            "boundary": (
                "Loop-level coherence can support later review only. It cannot "
                "apply strategy changes or create execution authority."
            ),
        },
        "meta_review_records": records,
        "recursive_improvement_contract": {
            "status": "quantum_meta_review_observation_active" if dependency_ready else "blocked",
            "uses_quantum_gate": True,
            "uses_pattern_recognition_engine": True,
            "uses_edge_memory": True,
            "uses_strategy_update_record": True,
            "uses_hypothesis_lifecycle": True,
            "uses_strategy_weight_updates": True,
            "meta_review_only": True,
            "recommendation_only": True,
            "active_weights_unchanged": active_before_weights == active_after_weights,
            "holds_recorded": dependency_ready and blocked_count > 0,
            "applies_weight_updates": False,
            "mutates_active_strategy": False,
            "changes_order_sizing": False,
            "paper_order_allowed": False,
            "broker_write_allowed": False,
            "quantum_provider_call_allowed": False,
            "boundary": (
                "Stage 4D can audit recursive learning coherence only. Active "
                "strategy weights, paper execution behavior, brokers, quantum "
                "providers, and Telegram sends remain unchanged."
            ),
        },
        "blocked_reason": None
        if status == "quantum_meta_review_ready"
        else "strategy_weight_updates_or_quantum_dependencies_not_ready",
        "documentation_routes": {
            "runtime_artifact": f"data/runtime/{QUANTUM_META_REVIEW_RUNTIME_ARTIFACT}",
            "history": f"data/runtime/{QUANTUM_META_REVIEW_HISTORY}",
            "event_log": f"data/runtime/{QUANTUM_META_REVIEW_EVENT_LOG}",
            "source_quantum_gate": "data/runtime/quantum_mandatory_review_gate.json",
            "source_pattern_engine": "data/runtime/pattern_recognition_engine.json",
            "source_edge_memory_ledger": "data/runtime/edge_memory_ledger.json",
            "source_strategy_update_record": "data/runtime/strategy_update_record.json",
            "source_hypothesis_lifecycle": "data/runtime/hypothesis_lifecycle.json",
            "source_strategy_weight_updates": "data/runtime/strategy_weight_updates.json",
        },
        "boundary": QUANTUM_META_REVIEW_BOUNDARY,
    }
    for field in QUANTUM_META_REVIEW_AUTHORITY_FALSE_FIELDS:
        artifact[field] = False
    return artifact


def _validate_weights(prefix: str, value: Any) -> dict[str, float]:
    if not isinstance(value, dict) or not value:
        raise ValueError(f"{prefix} missing")
    expected_keys = {_weight_key(family) for family in STRATEGY_FAMILIES}
    if set(value) != expected_keys:
        raise ValueError(f"{prefix} keys mismatch")
    weights: dict[str, float] = {}
    for key, item in value.items():
        if not isinstance(item, int | float):
            raise ValueError(f"{prefix} value invalid")
        weights[str(key)] = round(float(item), 6)
    if not 0.999 <= _weight_sum(weights) <= 1.001:
        raise ValueError(f"{prefix} not normalized")
    return weights


def _expected_delta(after: dict[str, float], before: dict[str, float]) -> dict[str, float]:
    return {
        key: round(float(after.get(key, 0.0)) - float(before.get(key, 0.0)), 6)
        for key in sorted(before)
    }


def _validate_delta(
    prefix: str,
    delta: Any,
    *,
    before: dict[str, float],
    after: dict[str, float],
) -> dict[str, float]:
    if not isinstance(delta, dict):
        raise ValueError(f"{prefix} invalid")
    observed = {
        str(key): round(float(value), 6)
        for key, value in delta.items()
        if isinstance(value, int | float)
    }
    expected = _expected_delta(after, before)
    if observed != expected:
        raise ValueError(f"{prefix} mismatch")
    return observed


def validate_quantum_meta_review(payload: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "artifact_type",
        "artifact_id",
        "stage",
        "generated_at",
        "status",
        "public_safe",
        "purpose",
        "quantum_gate_status",
        "pattern_engine_status",
        "edge_memory_ledger_status",
        "strategy_update_record_status",
        "hypothesis_lifecycle_status",
        "strategy_weight_updates_status",
        "strategy_family_count",
        "quantum_meta_review_count",
        "quantum_meta_review_passed_count",
        "quantum_meta_review_blocked_count",
        "quantum_meta_review_hold_count",
        "quantum_dependency_satisfied_count",
        "oracle_contract_accepted_count",
        "hypothesis_lifecycle_linked_count",
        "strategy_weight_update_proposal_count",
        "strategy_weight_update_applied_count",
        "meta_review_applied_count",
        "active_strategy_weight_mutation_count",
        "active_before_weights",
        "active_after_weights",
        "proposed_after_weights",
        "proposed_weight_delta",
        "applied_weight_delta",
        "active_before_weight_sum",
        "active_after_weight_sum",
        "proposed_after_weight_sum",
        "proposed_weight_delta_total_abs",
        "applied_weight_delta_total_abs",
        "loop_level_decision",
        "meta_review_records",
        "recursive_improvement_contract",
        "blocked_reason",
        "documentation_routes",
        "boundary",
        *QUANTUM_META_REVIEW_AUTHORITY_FALSE_FIELDS,
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"quantum meta-review missing fields: {missing}")
    if payload.get("schema_version") != QUANTUM_META_REVIEW_SCHEMA_VERSION:
        raise ValueError("quantum meta-review schema mismatch")
    if payload.get("artifact_type") != "quantum_meta_review":
        raise ValueError("quantum meta-review artifact type mismatch")
    if payload.get("status") not in QUANTUM_META_REVIEW_STATUSES:
        raise ValueError("quantum meta-review status invalid")
    if payload.get("public_safe") is not True:
        raise ValueError("quantum meta-review must be public-safe")
    if "read-only recursive-improvement audit" not in str(payload.get("boundary", "")):
        raise ValueError("quantum meta-review boundary weak")
    for field in QUANTUM_META_REVIEW_AUTHORITY_FALSE_FIELDS:
        if payload.get(field) is not False:
            raise ValueError(f"quantum meta-review authority leak: {field}")
    active_before = _validate_weights("active_before_weights", payload.get("active_before_weights"))
    active_after = _validate_weights("active_after_weights", payload.get("active_after_weights"))
    proposed_after = _validate_weights("proposed_after_weights", payload.get("proposed_after_weights"))
    if active_before != active_after:
        raise ValueError("quantum meta-review active weights mutated")
    if payload.get("active_before_weight_sum") != _weight_sum(active_before):
        raise ValueError("quantum meta-review active before weight sum mismatch")
    if payload.get("active_after_weight_sum") != _weight_sum(active_after):
        raise ValueError("quantum meta-review active after weight sum mismatch")
    if payload.get("proposed_after_weight_sum") != _weight_sum(proposed_after):
        raise ValueError("quantum meta-review proposed after weight sum mismatch")
    proposed_delta = _validate_delta(
        "proposed_weight_delta",
        payload.get("proposed_weight_delta"),
        before=active_before,
        after=proposed_after,
    )
    applied_delta = _validate_delta(
        "applied_weight_delta",
        payload.get("applied_weight_delta"),
        before=active_before,
        after=active_after,
    )
    if any(float(value) != 0.0 for value in applied_delta.values()):
        raise ValueError("quantum meta-review applied delta must stay zero")
    if payload.get("applied_weight_delta_total_abs") != 0.0:
        raise ValueError("quantum meta-review applied delta total must stay zero")
    if payload.get("proposed_weight_delta_total_abs") != round(
        sum(abs(float(value)) for value in proposed_delta.values()),
        6,
    ):
        raise ValueError("quantum meta-review proposed delta total mismatch")
    records = payload.get("meta_review_records")
    if not isinstance(records, list):
        raise ValueError("quantum meta-review records must be a list")
    if _int(payload.get("strategy_family_count")) != len(STRATEGY_FAMILIES):
        raise ValueError("quantum meta-review strategy family count mismatch")
    if _int(payload.get("quantum_meta_review_count")) != len(records):
        raise ValueError("quantum meta-review count mismatch")
    if _int(payload.get("strategy_weight_update_applied_count")) != 0:
        raise ValueError("quantum meta-review cannot use applied strategy weights")
    if _int(payload.get("meta_review_applied_count")) != 0:
        raise ValueError("quantum meta-review cannot be applied")
    if _int(payload.get("active_strategy_weight_mutation_count")) != 0:
        raise ValueError("quantum meta-review cannot mutate active weights")
    loop = _as_dict(payload.get("loop_level_decision"))
    contract = _as_dict(payload.get("recursive_improvement_contract"))
    for field in (
        "can_update_strategy_weights",
        "can_mutate_strategy",
        "can_change_order_sizing",
        "can_submit_paper_orders",
        "can_call_brokers",
        "can_call_quantum_providers",
        "can_send_live_telegram",
    ):
        if loop.get(field) is not False:
            raise ValueError(f"quantum meta-review loop authority leak: {field}")
    for field in (
        "applies_weight_updates",
        "mutates_active_strategy",
        "changes_order_sizing",
        "paper_order_allowed",
        "broker_write_allowed",
        "quantum_provider_call_allowed",
    ):
        if contract.get(field) is not False:
            raise ValueError(f"quantum meta-review contract authority leak: {field}")
    if loop.get("recommendation_only") is not True or contract.get("recommendation_only") is not True:
        raise ValueError("quantum meta-review must stay recommendation-only")
    ready = payload.get("status") == "quantum_meta_review_ready"
    if ready:
        expected_statuses = {
            "quantum_gate_status": "quantum_review_gate_passed",
            "pattern_engine_status": "pattern_engine_ready_for_quantum_oracle",
            "edge_memory_ledger_status": "edge_memory_active",
            "strategy_update_record_status": "strategy_update_record_ready",
            "hypothesis_lifecycle_status": "hypothesis_lifecycle_active",
            "strategy_weight_updates_status": "strategy_weight_updates_ready",
        }
        for key, expected in expected_statuses.items():
            if payload.get(key) != expected:
                raise ValueError(f"quantum meta-review dependency not ready: {key}")
        if len(records) != len(STRATEGY_FAMILIES):
            raise ValueError("quantum meta-review must expose all strategy families")
        if payload.get("blocked_reason") is not None:
            raise ValueError("ready quantum meta-review cannot be blocked")
        if loop.get("status") not in {
            "quantum_meta_review_coherent",
            "quantum_meta_review_completed_with_holds",
        }:
            raise ValueError("ready quantum meta-review loop decision invalid")
    else:
        if payload.get("blocked_reason") != "strategy_weight_updates_or_quantum_dependencies_not_ready":
            raise ValueError("blocked quantum meta-review needs blocked reason")
        if records:
            raise ValueError("blocked quantum meta-review cannot emit records")
        if loop.get("status") != "quantum_meta_review_blocked":
            raise ValueError("blocked quantum meta-review loop decision invalid")
    seen_families: set[str] = set()
    passed_count = 0
    blocked_count = 0
    quantum_count = 0
    oracle_count = 0
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("quantum meta-review record must be a dict")
        family_key = str(record.get("strategy_family_key") or "")
        if family_key in seen_families:
            raise ValueError("duplicate quantum meta-review family")
        seen_families.add(family_key)
        if family_key not in active_before:
            raise ValueError("quantum meta-review family unknown")
        if record.get("decision_status") != "reviewed_not_applied":
            raise ValueError("quantum meta-review record decision must not apply")
        if record.get("recommendation_scope") != "research_priority_only":
            raise ValueError("quantum meta-review recommendation scope invalid")
        if record.get("applied") is not False:
            raise ValueError("quantum meta-review record cannot be applied")
        if record.get("applied_at") is not None:
            raise ValueError("quantum meta-review applied_at must be empty")
        if record.get("applied_weight_delta") != 0.0:
            raise ValueError("quantum meta-review record applied delta must be zero")
        if record.get("active_before_weight") != active_before[family_key]:
            raise ValueError("quantum meta-review record active before mismatch")
        if record.get("active_after_weight") != active_after[family_key]:
            raise ValueError("quantum meta-review record active after mismatch")
        if record.get("proposed_after_weight") != proposed_after[family_key]:
            raise ValueError("quantum meta-review record proposed after mismatch")
        if record.get("proposed_weight_delta") != proposed_delta[family_key]:
            raise ValueError("quantum meta-review record proposed delta mismatch")
        if record.get("active_weights_unchanged") is not True:
            raise ValueError("quantum meta-review record active weights changed")
        if record.get("quantum_required") is not True:
            raise ValueError("quantum meta-review record must require quantum")
        if record.get("quantum_dependency_satisfied") is True:
            quantum_count += 1
        if record.get("oracle_contract_accepted") is True:
            oracle_count += 1
        if record.get("meta_review_passed") is True:
            passed_count += 1
        else:
            blocked_count += 1
        if record.get("meta_review_passed") is True:
            if record.get("quantum_dependency_satisfied") is not True:
                raise ValueError("quantum meta-review passed without quantum dependency")
            if record.get("oracle_contract_accepted") is not True:
                raise ValueError("quantum meta-review passed without oracle contract")
            if record.get("optimized_for_quantum_oracle") is not True:
                raise ValueError("quantum meta-review passed without quantum optimization")
            if record.get("alignment_ok") is not True:
                raise ValueError("quantum meta-review passed without strategy alignment")
            if record.get("hypothesis_lifecycle_linked") is not True:
                raise ValueError("quantum meta-review passed without hypothesis lifecycle")
            if not 0.45 <= _float(record.get("meta_review_score")) <= 1.0:
                raise ValueError("quantum meta-review score invalid for passed record")
        else:
            if not record.get("hold_reasons"):
                raise ValueError("held quantum meta-review record needs hold reasons")
        for field in QUANTUM_META_REVIEW_AUTHORITY_FALSE_FIELDS:
            if record.get(field) is not False:
                raise ValueError(f"quantum meta-review record authority leak: {field}")
    if _int(payload.get("quantum_meta_review_passed_count")) != passed_count:
        raise ValueError("quantum meta-review passed count mismatch")
    if _int(payload.get("quantum_meta_review_blocked_count")) != blocked_count:
        raise ValueError("quantum meta-review blocked count mismatch")
    if _int(payload.get("quantum_meta_review_hold_count")) != blocked_count:
        raise ValueError("quantum meta-review hold count mismatch")
    if _int(payload.get("quantum_dependency_satisfied_count")) != quantum_count:
        raise ValueError("quantum meta-review quantum dependency count mismatch")
    if _int(payload.get("oracle_contract_accepted_count")) != oracle_count:
        raise ValueError("quantum meta-review oracle contract count mismatch")
    if _int(payload.get("hypothesis_lifecycle_linked_count")) != sum(
        1 for record in records if record.get("hypothesis_lifecycle_linked") is True
    ):
        raise ValueError("quantum meta-review lifecycle linked count mismatch")
    if ready:
        loop_status = loop.get("status")
        if loop_status == "quantum_meta_review_coherent" and passed_count != len(STRATEGY_FAMILIES):
            raise ValueError("coherent quantum meta-review requires all families to pass")
        if loop_status == "quantum_meta_review_completed_with_holds" and blocked_count < 1:
            raise ValueError("quantum meta-review completed-with-holds requires a hold")


def write_quantum_meta_review(
    payload: dict[str, Any],
    settings: Settings | None = None,
) -> dict[str, Any]:
    validate_quantum_meta_review(payload)
    output_path, history_path, event_path = quantum_meta_review_paths(settings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    event = {
        "schema_version": QUANTUM_META_REVIEW_SCHEMA_VERSION,
        "event_type": QUANTUM_META_REVIEW_EVENT_TYPE,
        "component": QUANTUM_META_REVIEW_COMPONENT,
        "created_at": payload.get("generated_at") or _now(),
        "status": payload.get("status"),
        "quantum_meta_review_count": payload.get("quantum_meta_review_count"),
        "quantum_meta_review_passed_count": payload.get("quantum_meta_review_passed_count"),
        "quantum_meta_review_blocked_count": payload.get("quantum_meta_review_blocked_count"),
        "quantum_dependency_satisfied_count": payload.get("quantum_dependency_satisfied_count"),
        "oracle_contract_accepted_count": payload.get("oracle_contract_accepted_count"),
        "strategy_weight_update_applied_count": payload.get(
            "strategy_weight_update_applied_count"
        ),
        "meta_review_applied_count": payload.get("meta_review_applied_count"),
        "active_strategy_weight_mutation_count": payload.get(
            "active_strategy_weight_mutation_count"
        ),
        "authority_leak_count": sum(
            1
            for field in QUANTUM_META_REVIEW_AUTHORITY_FALSE_FIELDS
            if payload.get(field) is not False
        ),
        "public_safe": True,
        "boundary": QUANTUM_META_REVIEW_BOUNDARY,
    }
    with event_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    return {
        "output_path": str(output_path),
        "history_path": str(history_path),
        "event_log_path": str(event_path),
    }
