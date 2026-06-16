"""Read-only strategy weight update proposals for Qadam.

Stage 4C converts edge memory, strategy update records, and hypothesis
lifecycle state into strategy-family weight proposals. It is a proposal layer
only: it can recommend how Qadam should bias future research attention, but it
cannot mutate active strategy weights, change order sizing, approve risk, or
submit paper trades.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.edge_memory_ledger import validate_edge_memory_ledger
from orchestrator.hypothesis_lifecycle import (
    HYPOTHESIS_LIFECYCLE_AUTHORITY_FALSE_FIELDS,
    validate_hypothesis_lifecycle,
)
from orchestrator.strategy_update_record import validate_strategy_update_record


STRATEGY_WEIGHT_UPDATES_SCHEMA_VERSION = 1
STRATEGY_WEIGHT_UPDATES_RUNTIME_ARTIFACT = "strategy_weight_updates.json"
STRATEGY_WEIGHT_UPDATES_HISTORY = "strategy_weight_updates_history.jsonl"
STRATEGY_WEIGHT_UPDATES_EVENT_LOG = "strategy_weight_updates_events.jsonl"
STRATEGY_WEIGHT_UPDATES_EVENT_TYPE = "strategy_weight_updates_recorded"
STRATEGY_WEIGHT_UPDATES_COMPONENT = "strategy_weight_updates"

STRATEGY_WEIGHT_UPDATES_AUTHORITY_FALSE_FIELDS: tuple[str, ...] = tuple(
    dict.fromkeys(
        (
            *HYPOTHESIS_LIFECYCLE_AUTHORITY_FALSE_FIELDS,
            "strategy_weight_update_allowed",
            "strategy_weight_update_applied",
            "active_strategy_weight_mutated",
            "model_weight_mutation_allowed",
            "portfolio_allocation_mutation_allowed",
            "paper_order_sizing_allowed",
            "autonomous_rebalance_allowed",
            "learning_write_created",
            "strategy_artifact_write_created",
        )
    )
)

STRATEGY_WEIGHT_UPDATES_BOUNDARY = (
    "Strategy Weight Updates is a read-only strategy weight update proposal. "
    "It can recommend future research-priority weights from edge memory, "
    "hypothesis lifecycle state, strategy update records, and mandatory "
    "quantum review, but it cannot apply strategy weights, mutate active "
    "strategy artifacts, change model weights, change portfolio allocation, "
    "size orders, approve risk, submit paper orders, write brokers, send live "
    "Telegram commands, call quantum providers, enable live capital, or grant "
    "proof credit."
)

STRATEGY_WEIGHT_UPDATES_STATUSES = {
    "strategy_weight_updates_ready",
    "strategy_weight_updates_blocked_pending_hypothesis_lifecycle",
}

STRATEGY_FAMILIES: tuple[dict[str, str], ...] = (
    {
        "sleeve_key": "prediction_markets",
        "strategy_family_key": "prediction_market_geopolitical_dislocation",
        "strategy_family_name": "Prediction Market Geopolitical Dislocation",
        "instrument_key": "prediction_markets",
    },
    {
        "sleeve_key": "oil",
        "strategy_family_key": "crude_oil_energy_security_disruption",
        "strategy_family_name": "Crude Oil Energy Security Disruption",
        "instrument_key": "crude_oil",
    },
    {
        "sleeve_key": "defence",
        "strategy_family_key": "defence_repricing_geopolitical_watch",
        "strategy_family_name": "Defence Repricing Geopolitical Watch",
        "instrument_key": "defence",
    },
    {
        "sleeve_key": "silver",
        "strategy_family_key": "silver_macro_liquidity_stress",
        "strategy_family_name": "Silver Macro Liquidity Stress",
        "instrument_key": "silver",
    },
    {
        "sleeve_key": "semiconductors",
        "strategy_family_key": "semiconductor_policy_options_asymmetry",
        "strategy_family_name": "Semiconductor Policy Options Asymmetry",
        "instrument_key": "semiconductors",
    },
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def strategy_weight_updates_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / STRATEGY_WEIGHT_UPDATES_RUNTIME_ARTIFACT,
        runtime / STRATEGY_WEIGHT_UPDATES_HISTORY,
        runtime / STRATEGY_WEIGHT_UPDATES_EVENT_LOG,
    )


def read_strategy_weight_updates(settings: Settings | None = None) -> dict[str, Any]:
    output_path, _, _ = strategy_weight_updates_paths(settings)
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


def _clip(value: float, *, lower: float = 0.0, upper: float = 1.0) -> float:
    return round(max(lower, min(upper, value)), 6)


def _weight_key(family: dict[str, str]) -> str:
    return family["strategy_family_key"]


def _baseline_weights() -> dict[str, float]:
    weight = round(1.0 / len(STRATEGY_FAMILIES), 6)
    weights = {_weight_key(family): weight for family in STRATEGY_FAMILIES}
    delta = round(1.0 - sum(weights.values()), 6)
    first_key = _weight_key(STRATEGY_FAMILIES[0])
    weights[first_key] = round(weights[first_key] + delta, 6)
    return weights


def _normalise(weights: dict[str, float]) -> dict[str, float]:
    total = sum(max(0.0, float(value)) for value in weights.values())
    if total <= 0:
        return _baseline_weights()
    output = {
        key: round(max(0.0, float(value)) / total, 6)
        for key, value in sorted(weights.items())
    }
    delta = round(1.0 - sum(output.values()), 6)
    if output:
        first_key = next(iter(output))
        output[first_key] = round(output[first_key] + delta, 6)
    return output


def _weight_sum(weights: dict[str, Any]) -> float:
    return round(sum(float(value) for value in weights.values()), 6)


def _weights_delta(after: dict[str, float], before: dict[str, float]) -> dict[str, float]:
    return {
        key: round(float(after.get(key, 0.0)) - float(before.get(key, 0.0)), 6)
        for key in sorted(before)
    }


def _records_by_sleeve(records: list[Any]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for record in records:
        if isinstance(record, dict):
            sleeve = str(record.get("sleeve_key") or "").strip().lower()
            if sleeve:
                output[sleeve] = record
    return output


def _threads_by_sleeve(threads: list[Any]) -> dict[str, list[dict[str, Any]]]:
    output: dict[str, list[dict[str, Any]]] = {}
    for thread in threads:
        if not isinstance(thread, dict):
            continue
        sleeve = str(thread.get("sleeve_key") or "").strip().lower()
        if sleeve:
            output.setdefault(sleeve, []).append(thread)
    return output


def _strategy_adjustment_factor(proposal: dict[str, Any]) -> float:
    adjustment = str(proposal.get("proposed_adjustment") or "")
    if adjustment == "raise_watch_priority_after_more_persistence":
        return 0.06
    if adjustment == "maintain_high_watch_priority":
        return 0.035
    if adjustment == "review_for_persistence_based_threshold_proposal":
        return 0.025
    if adjustment == "hold_or_lower_confidence_until_ambiguity_falls":
        return -0.05
    return 0.0


def _hypothesis_factor(threads: list[dict[str, Any]]) -> float:
    if not threads:
        return -0.015
    factor = 0.0
    for thread in threads:
        state = str(thread.get("lifecycle_state") or "")
        if state == "ready_for_signal_integrity_review":
            factor += 0.06
        elif state == "retained_for_shadow_review":
            factor += 0.035
        elif state == "held_for_independent_corroboration":
            factor += 0.005
        elif state == "held_for_quantum_or_edge_mapping":
            factor -= 0.025
        elif state == "refutation_candidate_not_applied":
            factor -= 0.06
        elif state == "blocked_source_execution_authority_present":
            factor -= 0.18
        if thread.get("quantum_dependency_satisfied") is True:
            factor += 0.01
    return max(-0.18, min(0.12, factor))


def _proposal_score(
    *,
    edge_memory: dict[str, Any],
    strategy_proposal: dict[str, Any],
    hypothesis_threads: list[dict[str, Any]],
) -> float:
    readiness = _float(edge_memory.get("latest_edge_readiness_score"))
    signal_strength = _float(edge_memory.get("latest_signal_strength"))
    ambiguity = _float(edge_memory.get("latest_ambiguity_score"))
    observations = _int(edge_memory.get("observation_count"))
    consecutive = _int(edge_memory.get("consecutive_observation_count"))
    score = 1.0
    score += (readiness - 0.5) * 0.26
    score += signal_strength * 0.08
    score -= ambiguity * 0.09
    score += min(observations, 30) / 30.0 * 0.045
    score += min(consecutive, 7) / 7.0 * 0.035
    score += _strategy_adjustment_factor(strategy_proposal)
    score += _hypothesis_factor(hypothesis_threads)
    quantum_dependency_satisfied = (
        edge_memory.get("quantum_gate_dependency_satisfied") is True
        and strategy_proposal.get("quantum_dependency_satisfied") is True
    )
    score += 0.035 if quantum_dependency_satisfied else -0.25
    return round(max(0.25, min(1.75, score)), 6)


def _update_record(
    *,
    family: dict[str, str],
    active_before_weight: float,
    proposed_after_weight: float,
    edge_memory: dict[str, Any],
    strategy_proposal: dict[str, Any],
    hypothesis_threads: list[dict[str, Any]],
    proposal_score: float,
    generated_at: str,
) -> dict[str, Any]:
    strategy_family_key = family["strategy_family_key"]
    proposed_delta = round(proposed_after_weight - active_before_weight, 6)
    update_id = "strategy-weight-update:" + sha256(
        json.dumps(
            {
                "strategy_family_key": strategy_family_key,
                "edge_memory_id": edge_memory.get("memory_id"),
                "strategy_update_id": strategy_proposal.get("update_id"),
                "proposed_after_weight": proposed_after_weight,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:18]
    record = {
        "weight_update_id": update_id,
        "status": "strategy_weight_update_proposed_not_applied",
        "decision_status": "recorded_not_applied",
        "sleeve_key": family["sleeve_key"],
        "instrument_key": family["instrument_key"],
        "strategy_family_key": strategy_family_key,
        "strategy_family_name": family["strategy_family_name"],
        "target_weight_surface": "strategy_family_research_priority",
        "active_before_weight": round(active_before_weight, 6),
        "active_after_weight": round(active_before_weight, 6),
        "proposed_after_weight": round(proposed_after_weight, 6),
        "proposed_weight_delta": proposed_delta,
        "applied_weight_delta": 0.0,
        "proposal_strength_score": _clip(proposal_score),
        "edge_memory_id": edge_memory.get("memory_id"),
        "edge_memory_observation_count": edge_memory.get("observation_count"),
        "edge_memory_consecutive_observation_count": edge_memory.get(
            "consecutive_observation_count"
        ),
        "edge_memory_persistence_state": edge_memory.get("persistence_state"),
        "latest_edge_readiness_score": _clip(
            _float(edge_memory.get("latest_edge_readiness_score"))
        ),
        "latest_ambiguity_score": _clip(
            _float(edge_memory.get("latest_ambiguity_score"))
        ),
        "latest_signal_strength": _clip(_float(edge_memory.get("latest_signal_strength"))),
        "strategy_update_id": strategy_proposal.get("update_id"),
        "strategy_update_proposed_adjustment": strategy_proposal.get(
            "proposed_adjustment"
        ),
        "strategy_update_applied": strategy_proposal.get("applied") is True,
        "hypothesis_lifecycle_thread_count": len(hypothesis_threads),
        "hypothesis_lifecycle_states": sorted(
            {str(thread.get("lifecycle_state") or "unknown") for thread in hypothesis_threads}
        ),
        "hypothesis_lifecycle_ids": sorted(
            str(thread.get("lifecycle_id"))
            for thread in hypothesis_threads
            if thread.get("lifecycle_id")
        ),
        "held_for_corroboration": any(
            thread.get("lifecycle_state") == "held_for_independent_corroboration"
            for thread in hypothesis_threads
        ),
        "ready_for_signal_integrity_review": any(
            thread.get("lifecycle_state") == "ready_for_signal_integrity_review"
            for thread in hypothesis_threads
        ),
        "quantum_mandatory_review_required": True,
        "quantum_dependency_satisfied": (
            edge_memory.get("quantum_gate_dependency_satisfied") is True
            and strategy_proposal.get("quantum_dependency_satisfied") is True
        ),
        "quantum_gate_decision_status": edge_memory.get("quantum_gate_decision_status")
        or strategy_proposal.get("quantum_gate_decision_status"),
        "quantum_oracle_input_contract_status": edge_memory.get(
            "quantum_oracle_input_contract_status"
        )
        or strategy_proposal.get("quantum_oracle_input_contract_status"),
        "optimized_for_quantum_oracle": (
            edge_memory.get("optimized_for_quantum_oracle") is True
            and strategy_proposal.get("optimized_for_quantum_oracle") is True
        ),
        "rationale": (
            "Propose a future research-priority weight from edge persistence, "
            "hypothesis lifecycle state, and quantum-reviewed strategy update "
            "records. Active strategy weights remain unchanged."
        ),
        "apply_condition": (
            "A later explicit approval path must compare this proposal against "
            "paper postmortems, Signal Integrity, Risk, and Q-CTRL consultation "
            "before any weight can be applied."
        ),
        "rollback_condition": (
            "Discard or reduce if the edge memory weakens, ambiguity rises, "
            "hypothesis lifecycle state regresses, or paper outcomes reject the "
            "strategy family."
        ),
        "recorded_at": generated_at,
        "applied": False,
        "applied_at": None,
    }
    for field in STRATEGY_WEIGHT_UPDATES_AUTHORITY_FALSE_FIELDS:
        record[field] = False
    return record


def build_strategy_weight_updates(
    *,
    edge_memory_ledger: dict[str, Any],
    strategy_update_record: dict[str, Any],
    hypothesis_lifecycle: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build Qadam's Stage 4C strategy weight update proposal artifact."""

    generated_at = generated_at or _now()
    validate_edge_memory_ledger(edge_memory_ledger)
    validate_strategy_update_record(strategy_update_record)
    validate_hypothesis_lifecycle(hypothesis_lifecycle)
    dependency_ready = (
        edge_memory_ledger.get("status") == "edge_memory_active"
        and strategy_update_record.get("status") == "strategy_update_record_ready"
        and hypothesis_lifecycle.get("status") == "hypothesis_lifecycle_active"
    )
    status = (
        "strategy_weight_updates_ready"
        if dependency_ready
        else "strategy_weight_updates_blocked_pending_hypothesis_lifecycle"
    )
    active_before_weights = _baseline_weights()
    active_after_weights = dict(active_before_weights)
    edge_by_sleeve = _records_by_sleeve(edge_memory_ledger.get("memory_records", []))
    strategy_by_sleeve = _records_by_sleeve(strategy_update_record.get("proposals", []))
    threads_by_sleeve = _threads_by_sleeve(hypothesis_lifecycle.get("hypothesis_threads", []))
    scores: dict[str, float] = {}
    for family in STRATEGY_FAMILIES:
        key = _weight_key(family)
        sleeve = family["sleeve_key"]
        edge_memory = edge_by_sleeve.get(sleeve, {})
        strategy_proposal = strategy_by_sleeve.get(sleeve, {})
        hypothesis_threads = threads_by_sleeve.get(sleeve, [])
        scores[key] = _proposal_score(
            edge_memory=edge_memory,
            strategy_proposal=strategy_proposal,
            hypothesis_threads=hypothesis_threads,
        )
    proposed_raw = {
        key: round(active_before_weights[key] * scores[key], 6)
        for key in active_before_weights
    }
    proposed_after_weights = _normalise(proposed_raw)
    proposed_weight_delta = _weights_delta(proposed_after_weights, active_before_weights)
    applied_weight_delta = {key: 0.0 for key in active_before_weights}
    records = [
        _update_record(
            family=family,
            active_before_weight=active_before_weights[_weight_key(family)],
            proposed_after_weight=proposed_after_weights[_weight_key(family)],
            edge_memory=edge_by_sleeve.get(family["sleeve_key"], {}),
            strategy_proposal=strategy_by_sleeve.get(family["sleeve_key"], {}),
            hypothesis_threads=threads_by_sleeve.get(family["sleeve_key"], []),
            proposal_score=scores[_weight_key(family)],
            generated_at=generated_at,
        )
        for family in STRATEGY_FAMILIES
        if status == "strategy_weight_updates_ready"
    ]
    artifact = {
        "schema_version": STRATEGY_WEIGHT_UPDATES_SCHEMA_VERSION,
        "artifact_type": "strategy_weight_updates",
        "artifact_id": "strategy-weight-updates:latest",
        "stage": "Stage 4C - Strategy Weight Updates",
        "generated_at": generated_at,
        "status": status,
        "public_safe": True,
        "purpose": (
            "Record proposed strategy-family research-priority weight changes "
            "from edge memory and hypothesis lifecycle evidence without "
            "applying them to Qadam's active paper-trading strategy."
        ),
        "edge_memory_ledger_status": edge_memory_ledger.get("status"),
        "strategy_update_record_status": strategy_update_record.get("status"),
        "hypothesis_lifecycle_status": hypothesis_lifecycle.get("status"),
        "quantum_gate_status": strategy_update_record.get("quantum_gate_status"),
        "strategy_family_count": len(STRATEGY_FAMILIES),
        "strategy_weight_update_proposal_count": len(records),
        "strategy_weight_update_applied_count": 0,
        "active_strategy_weight_mutation_count": 0,
        "quantum_dependency_satisfied_count": sum(
            1 for record in records if record.get("quantum_dependency_satisfied") is True
        ),
        "hypothesis_lifecycle_linked_count": sum(
            1 for record in records if _int(record.get("hypothesis_lifecycle_thread_count")) > 0
        ),
        "active_before_weights": active_before_weights,
        "active_after_weights": active_after_weights,
        "proposed_after_weights": proposed_after_weights if records else active_before_weights,
        "proposed_weight_delta": proposed_weight_delta if records else applied_weight_delta,
        "applied_weight_delta": applied_weight_delta,
        "active_before_weight_sum": _weight_sum(active_before_weights),
        "active_after_weight_sum": _weight_sum(active_after_weights),
        "proposed_after_weight_sum": _weight_sum(
            proposed_after_weights if records else active_before_weights
        ),
        "proposed_weight_delta_total_abs": round(
            sum(abs(float(value)) for value in (proposed_weight_delta if records else {}).values()),
            6,
        ),
        "applied_weight_delta_total_abs": 0.0,
        "weight_update_records": records,
        "recursive_improvement_contract": {
            "status": "weight_proposal_recording_active" if records else "blocked",
            "uses_edge_memory": True,
            "uses_strategy_update_record": True,
            "uses_hypothesis_lifecycle": True,
            "uses_quantum_mandatory_review": True,
            "proposal_only": True,
            "active_weights_unchanged": True,
            "applies_weight_updates": False,
            "mutates_active_strategy": False,
            "changes_order_sizing": False,
            "paper_order_allowed": False,
            "broker_write_allowed": False,
            "boundary": (
                "Stage 4C can propose research-priority deltas only. Active "
                "strategy weights and paper execution behavior remain unchanged."
            ),
        },
        "blocked_reason": None
        if status == "strategy_weight_updates_ready"
        else "edge_memory_strategy_record_or_hypothesis_lifecycle_not_ready",
        "documentation_routes": {
            "runtime_artifact": f"data/runtime/{STRATEGY_WEIGHT_UPDATES_RUNTIME_ARTIFACT}",
            "history": f"data/runtime/{STRATEGY_WEIGHT_UPDATES_HISTORY}",
            "event_log": f"data/runtime/{STRATEGY_WEIGHT_UPDATES_EVENT_LOG}",
            "source_edge_memory_ledger": "data/runtime/edge_memory_ledger.json",
            "source_strategy_update_record": "data/runtime/strategy_update_record.json",
            "source_hypothesis_lifecycle": "data/runtime/hypothesis_lifecycle.json",
        },
        "boundary": STRATEGY_WEIGHT_UPDATES_BOUNDARY,
    }
    for field in STRATEGY_WEIGHT_UPDATES_AUTHORITY_FALSE_FIELDS:
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


def _validate_delta(
    prefix: str,
    delta: Any,
    *,
    before: dict[str, float],
    after: dict[str, float],
) -> dict[str, float]:
    if not isinstance(delta, dict):
        raise ValueError(f"{prefix} invalid")
    expected = _weights_delta(after, before)
    observed = {
        str(key): round(float(value), 6)
        for key, value in delta.items()
        if isinstance(value, int | float)
    }
    if observed != expected:
        raise ValueError(f"{prefix} mismatch")
    return observed


def validate_strategy_weight_updates(payload: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "artifact_type",
        "artifact_id",
        "stage",
        "generated_at",
        "status",
        "public_safe",
        "purpose",
        "edge_memory_ledger_status",
        "strategy_update_record_status",
        "hypothesis_lifecycle_status",
        "quantum_gate_status",
        "strategy_family_count",
        "strategy_weight_update_proposal_count",
        "strategy_weight_update_applied_count",
        "active_strategy_weight_mutation_count",
        "quantum_dependency_satisfied_count",
        "hypothesis_lifecycle_linked_count",
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
        "weight_update_records",
        "recursive_improvement_contract",
        "blocked_reason",
        "documentation_routes",
        "boundary",
        *STRATEGY_WEIGHT_UPDATES_AUTHORITY_FALSE_FIELDS,
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"strategy weight updates missing fields: {missing}")
    if payload.get("schema_version") != STRATEGY_WEIGHT_UPDATES_SCHEMA_VERSION:
        raise ValueError("strategy weight updates schema mismatch")
    if payload.get("artifact_type") != "strategy_weight_updates":
        raise ValueError("strategy weight updates artifact type mismatch")
    if payload.get("status") not in STRATEGY_WEIGHT_UPDATES_STATUSES:
        raise ValueError("strategy weight updates status invalid")
    if payload.get("public_safe") is not True:
        raise ValueError("strategy weight updates must be public-safe")
    if "read-only strategy weight update proposal" not in str(payload.get("boundary", "")):
        raise ValueError("strategy weight updates boundary weak")
    for field in STRATEGY_WEIGHT_UPDATES_AUTHORITY_FALSE_FIELDS:
        if payload.get(field) is not False:
            raise ValueError(f"strategy weight updates authority leak: {field}")
    contract = _as_dict(payload.get("recursive_improvement_contract"))
    for field in (
        "applies_weight_updates",
        "mutates_active_strategy",
        "changes_order_sizing",
        "paper_order_allowed",
        "broker_write_allowed",
    ):
        if contract.get(field) is not False:
            raise ValueError(f"strategy weight contract authority leak: {field}")
    if contract.get("proposal_only") is not True:
        raise ValueError("strategy weight contract must stay proposal-only")
    if contract.get("active_weights_unchanged") is not True:
        raise ValueError("strategy weight contract must preserve active weights")
    active_before = _validate_weights("active_before_weights", payload.get("active_before_weights"))
    active_after = _validate_weights("active_after_weights", payload.get("active_after_weights"))
    proposed_after = _validate_weights("proposed_after_weights", payload.get("proposed_after_weights"))
    if active_before != active_after:
        raise ValueError("active strategy weights mutated")
    if payload.get("active_before_weight_sum") != _weight_sum(active_before):
        raise ValueError("active before weight sum mismatch")
    if payload.get("active_after_weight_sum") != _weight_sum(active_after):
        raise ValueError("active after weight sum mismatch")
    if payload.get("proposed_after_weight_sum") != _weight_sum(proposed_after):
        raise ValueError("proposed after weight sum mismatch")
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
    proposed_total_abs = round(sum(abs(float(value)) for value in proposed_delta.values()), 6)
    if payload.get("proposed_weight_delta_total_abs") != proposed_total_abs:
        raise ValueError("proposed weight delta total mismatch")
    if any(float(value) != 0.0 for value in applied_delta.values()):
        raise ValueError("applied weight delta must stay zero")
    if payload.get("applied_weight_delta_total_abs") != 0.0:
        raise ValueError("applied weight delta total must stay zero")
    records = payload.get("weight_update_records")
    if not isinstance(records, list):
        raise ValueError("strategy weight update records must be a list")
    if _int(payload.get("strategy_family_count")) != len(STRATEGY_FAMILIES):
        raise ValueError("strategy family count mismatch")
    if _int(payload.get("strategy_weight_update_proposal_count")) != len(records):
        raise ValueError("strategy weight proposal count mismatch")
    if _int(payload.get("strategy_weight_update_applied_count")) != 0:
        raise ValueError("strategy weight updates cannot be applied")
    if _int(payload.get("active_strategy_weight_mutation_count")) != 0:
        raise ValueError("active strategy weight mutation count must stay zero")
    active = payload.get("status") == "strategy_weight_updates_ready"
    if active:
        if payload.get("edge_memory_ledger_status") != "edge_memory_active":
            raise ValueError("strategy weight updates require active edge memory")
        if payload.get("strategy_update_record_status") != "strategy_update_record_ready":
            raise ValueError("strategy weight updates require strategy update record")
        if payload.get("hypothesis_lifecycle_status") != "hypothesis_lifecycle_active":
            raise ValueError("strategy weight updates require active hypothesis lifecycle")
        if payload.get("quantum_gate_status") != "quantum_review_gate_passed":
            raise ValueError("strategy weight updates require passed quantum gate")
        if len(records) != len(STRATEGY_FAMILIES):
            raise ValueError("strategy weight updates must expose all strategy families")
        if payload.get("blocked_reason") is not None:
            raise ValueError("ready strategy weight updates cannot be blocked")
    else:
        if payload.get("blocked_reason") != (
            "edge_memory_strategy_record_or_hypothesis_lifecycle_not_ready"
        ):
            raise ValueError("blocked strategy weight updates need blocked reason")
        if records:
            raise ValueError("blocked strategy weight updates cannot emit records")
    seen_families: set[str] = set()
    quantum_dependency_count = 0
    lifecycle_linked_count = 0
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("strategy weight update record must be a dict")
        family_key = str(record.get("strategy_family_key") or "")
        if family_key in seen_families:
            raise ValueError("duplicate strategy weight update family")
        seen_families.add(family_key)
        if family_key not in active_before:
            raise ValueError("strategy weight update family unknown")
        if record.get("status") != "strategy_weight_update_proposed_not_applied":
            raise ValueError("strategy weight update record status invalid")
        if record.get("decision_status") != "recorded_not_applied":
            raise ValueError("strategy weight update record decision must not apply")
        if record.get("active_before_weight") != active_before[family_key]:
            raise ValueError("strategy weight record before mismatch")
        if record.get("active_after_weight") != active_before[family_key]:
            raise ValueError("strategy weight record active after mismatch")
        if record.get("proposed_after_weight") != proposed_after[family_key]:
            raise ValueError("strategy weight record proposed after mismatch")
        if record.get("proposed_weight_delta") != proposed_delta[family_key]:
            raise ValueError("strategy weight record proposed delta mismatch")
        if record.get("applied_weight_delta") != 0.0:
            raise ValueError("strategy weight record applied delta must be zero")
        if record.get("applied") is not False:
            raise ValueError("strategy weight update record cannot be applied")
        if record.get("applied_at") is not None:
            raise ValueError("strategy weight update applied_at must be empty")
        if record.get("strategy_update_applied") is not False:
            raise ValueError("strategy weight update cannot use applied strategy update")
        if record.get("quantum_mandatory_review_required") is not True:
            raise ValueError("strategy weight update must require quantum review")
        if record.get("quantum_dependency_satisfied") is not True:
            raise ValueError("strategy weight update quantum dependency not satisfied")
        if record.get("quantum_oracle_input_contract_status") != "accepted":
            raise ValueError("strategy weight update oracle contract not accepted")
        if record.get("optimized_for_quantum_oracle") is not True:
            raise ValueError("strategy weight update not optimized for quantum oracle")
        if not record.get("edge_memory_id") or not record.get("strategy_update_id"):
            raise ValueError("strategy weight update missing source linkage")
        if record.get("quantum_dependency_satisfied") is True:
            quantum_dependency_count += 1
        if _int(record.get("hypothesis_lifecycle_thread_count")) > 0:
            lifecycle_linked_count += 1
        for field in STRATEGY_WEIGHT_UPDATES_AUTHORITY_FALSE_FIELDS:
            if record.get(field) is not False:
                raise ValueError(f"strategy weight update record authority leak: {field}")
    if _int(payload.get("quantum_dependency_satisfied_count")) != quantum_dependency_count:
        raise ValueError("strategy weight quantum dependency count mismatch")
    if _int(payload.get("hypothesis_lifecycle_linked_count")) != lifecycle_linked_count:
        raise ValueError("strategy weight lifecycle linked count mismatch")
    if active and quantum_dependency_count != len(STRATEGY_FAMILIES):
        raise ValueError("strategy weight updates require all families quantum-linked")


def write_strategy_weight_updates(
    payload: dict[str, Any],
    settings: Settings | None = None,
) -> dict[str, Any]:
    validate_strategy_weight_updates(payload)
    output_path, history_path, event_path = strategy_weight_updates_paths(settings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    event = {
        "schema_version": STRATEGY_WEIGHT_UPDATES_SCHEMA_VERSION,
        "event_type": STRATEGY_WEIGHT_UPDATES_EVENT_TYPE,
        "component": STRATEGY_WEIGHT_UPDATES_COMPONENT,
        "created_at": payload.get("generated_at") or _now(),
        "status": payload.get("status"),
        "strategy_weight_update_proposal_count": payload.get(
            "strategy_weight_update_proposal_count"
        ),
        "strategy_weight_update_applied_count": payload.get(
            "strategy_weight_update_applied_count"
        ),
        "active_strategy_weight_mutation_count": payload.get(
            "active_strategy_weight_mutation_count"
        ),
        "proposed_weight_delta_total_abs": payload.get("proposed_weight_delta_total_abs"),
        "applied_weight_delta_total_abs": payload.get("applied_weight_delta_total_abs"),
        "quantum_dependency_satisfied_count": payload.get(
            "quantum_dependency_satisfied_count"
        ),
        "hypothesis_lifecycle_linked_count": payload.get(
            "hypothesis_lifecycle_linked_count"
        ),
        "authority_leak_count": sum(
            1
            for field in STRATEGY_WEIGHT_UPDATES_AUTHORITY_FALSE_FIELDS
            if payload.get(field) is not False
        ),
        "public_safe": True,
        "boundary": STRATEGY_WEIGHT_UPDATES_BOUNDARY,
    }
    with event_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    return {
        "output_path": str(output_path),
        "history_path": str(history_path),
        "event_log_path": str(event_path),
    }
