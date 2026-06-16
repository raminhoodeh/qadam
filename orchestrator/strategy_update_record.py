"""Read-only strategy update record for Qadam.

This artifact converts edge memory into strategy-improvement proposals. It is a
recording layer only: it can document what Qadam would change after repeated
edge observations, but it cannot apply the change, size orders, approve risk,
submit paper trades, or write to a broker.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.edge_memory_ledger import (
    EDGE_MEMORY_LEDGER_AUTHORITY_FALSE_FIELDS,
    EDGE_MEMORY_LEDGER_REQUIRED_PATTERN_COUNT,
    validate_edge_memory_ledger,
)
from orchestrator.pattern_recognition_engine import validate_pattern_recognition_engine


STRATEGY_UPDATE_RECORD_SCHEMA_VERSION = 1
STRATEGY_UPDATE_RECORD_RUNTIME_ARTIFACT = "strategy_update_record.json"
STRATEGY_UPDATE_RECORD_HISTORY = "strategy_update_record_history.jsonl"
STRATEGY_UPDATE_RECORD_EVENT_LOG = "strategy_update_record_events.jsonl"
STRATEGY_UPDATE_RECORD_EVENT_TYPE = "strategy_update_record_recorded"
STRATEGY_UPDATE_RECORD_COMPONENT = "strategy_update_record"

STRATEGY_UPDATE_RECORD_AUTHORITY_FALSE_FIELDS: tuple[str, ...] = (
    *EDGE_MEMORY_LEDGER_AUTHORITY_FALSE_FIELDS,
    "strategy_update_applied",
    "autonomous_strategy_change_allowed",
    "threshold_mutation_allowed",
    "watchlist_mutation_allowed",
)

STRATEGY_UPDATE_RECORD_BOUNDARY = (
    "Strategy Update Record is a read-only strategy update record. It can "
    "document proposed strategy adjustments from edge memory, quantum review, "
    "and pattern-recognition evidence, but it cannot apply strategy changes, "
    "mutate thresholds, change model weights, approve risk, create trade "
    "candidates, size orders, submit paper orders, write to brokers, send live "
    "Telegram commands, enable live capital, or grant proof credit."
)

STRATEGY_UPDATE_RECORD_STATUSES = {
    "strategy_update_record_ready",
    "strategy_update_record_blocked_pending_edge_memory",
}

STRATEGY_COMPONENT_BY_SLEEVE = {
    "oil": "energy_event_mispricing_watchlist",
    "silver": "safe_haven_real_rates_watchlist",
    "semiconductors": "chip_supply_chain_momentum_watchlist",
    "prediction_markets": "event_probability_mispricing_watchlist",
    "defence": "defence_geopolitics_watchlist",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def strategy_update_record_paths(settings: Settings | None = None) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / STRATEGY_UPDATE_RECORD_RUNTIME_ARTIFACT,
        runtime / STRATEGY_UPDATE_RECORD_HISTORY,
        runtime / STRATEGY_UPDATE_RECORD_EVENT_LOG,
    )


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
    return round(max(0.0, min(1.0, value)), 3)


def _slug(value: Any) -> str:
    return str(value or "").strip().replace(" ", "_").lower() or "unknown"


def _proposal_adjustment(record: dict[str, Any]) -> tuple[str, str]:
    readiness = _float(record.get("latest_edge_readiness_score"))
    ambiguity = _float(record.get("latest_ambiguity_score"))
    observations = _int(record.get("observation_count"))
    consecutive = _int(record.get("consecutive_observation_count"))
    if readiness >= 0.68 and ambiguity <= 0.45 and consecutive >= 3:
        return (
            "raise_watch_priority_after_more_persistence",
            "Readiness is strong and ambiguity is low, but Qadam still needs durable persistence before any downstream guarded route can treat this as more than research priority.",
        )
    if readiness >= 0.58 and ambiguity <= 0.55:
        return (
            "maintain_high_watch_priority",
            "The pattern is useful enough to keep visible, but the memory ledger is still building calendar evidence.",
        )
    if ambiguity >= 0.62:
        return (
            "hold_or_lower_confidence_until_ambiguity_falls",
            "The pattern is too ambiguous for an upgrade. Qadam should demand more corroboration and quantum review before raising priority.",
        )
    if observations >= 30:
        return (
            "review_for_persistence_based_threshold_proposal",
            "The pattern has enough calendar observations to deserve a separate threshold review, still without automatic mutation.",
        )
    return (
        "maintain_watch_priority",
        "The pattern remains under observation and should not change trading behavior yet.",
    )


def _proposal_record(record: dict[str, Any], generated_at: str) -> dict[str, Any]:
    sleeve_key = _slug(record.get("sleeve_key"))
    proposed_adjustment, reason = _proposal_adjustment(record)
    update_id = "strategy-update:" + sha256(
        json.dumps(
            {
                "sleeve_key": sleeve_key,
                "memory_id": record.get("memory_id"),
                "memory_date": record.get("observation_dates", [])[-1:]
                if isinstance(record.get("observation_dates"), list)
                else [],
                "proposed_adjustment": proposed_adjustment,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:18]
    proposal = {
        "update_id": update_id,
        "status": "strategy_update_recorded_not_applied",
        "sleeve_key": sleeve_key,
        "market_sleeve": record.get("market_sleeve"),
        "edge_memory_id": record.get("memory_id"),
        "edge_memory_pattern_id": record.get("pattern_id"),
        "edge_memory_observation_count": record.get("observation_count"),
        "edge_memory_consecutive_observation_count": record.get(
            "consecutive_observation_count"
        ),
        "edge_memory_persistence_state": record.get("persistence_state"),
        "latest_edge_readiness_score": _clip(_float(record.get("latest_edge_readiness_score"))),
        "latest_ambiguity_score": _clip(_float(record.get("latest_ambiguity_score"))),
        "latest_signal_strength": _clip(_float(record.get("latest_signal_strength"))),
        "stability_assessment": record.get("stability_assessment"),
        "target_strategy_component": STRATEGY_COMPONENT_BY_SLEEVE.get(
            sleeve_key,
            "cross_asset_event_mispricing_watchlist",
        ),
        "proposal_type": "paper_strategy_research_priority_adjustment",
        "proposed_adjustment": proposed_adjustment,
        "reason": reason,
        "quantum_mandatory_review_required": True,
        "quantum_dependency_satisfied": record.get("quantum_gate_dependency_satisfied") is True,
        "quantum_gate_decision_status": record.get("quantum_gate_decision_status"),
        "quantum_oracle_input_contract_status": record.get(
            "quantum_oracle_input_contract_status"
        ),
        "optimized_for_quantum_oracle": record.get("optimized_for_quantum_oracle") is True,
        "paper_trade_effect": (
            "No direct paper-trade effect. This record may influence future "
            "research ranking only after Strategy Lead, Signal Integrity, "
            "risk, Q-CTRL consultation, and Alpaca Paper gates evaluate it."
        ),
        "recursive_improvement_action": (
            "Carry this proposal into the next daily edge review and compare it "
            "with later realized pattern persistence, postmortems, and blocked "
            "trade reasons before any threshold change is staged."
        ),
        "rollback_condition": (
            "Demote or discard if the edge memory weakens, ambiguity rises, "
            "quantum review fails, or the paper route rejects the thesis."
        ),
        "recorded_at": generated_at,
        "applied": False,
        "applied_at": None,
    }
    for field in STRATEGY_UPDATE_RECORD_AUTHORITY_FALSE_FIELDS:
        proposal[field] = False
    return proposal


def build_strategy_update_record(
    *,
    edge_memory_ledger: dict[str, Any],
    pattern_recognition_engine: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build Qadam's read-only strategy update proposal record."""

    generated_at = generated_at or _now()
    validate_edge_memory_ledger(edge_memory_ledger)
    validate_pattern_recognition_engine(pattern_recognition_engine)
    memory_active = edge_memory_ledger.get("status") == "edge_memory_active"
    engine_ready = pattern_recognition_engine.get("status") == "pattern_engine_ready_for_quantum_oracle"
    status = (
        "strategy_update_record_ready"
        if memory_active and engine_ready
        else "strategy_update_record_blocked_pending_edge_memory"
    )
    proposals = [
        _proposal_record(record, generated_at)
        for record in _as_list(edge_memory_ledger.get("memory_records"))
        if status == "strategy_update_record_ready" and isinstance(record, dict)
    ]
    update_record = {
        "schema_version": STRATEGY_UPDATE_RECORD_SCHEMA_VERSION,
        "artifact_type": "strategy_update_record",
        "artifact_id": "strategy-update-record:latest",
        "stage": "Stage 4 - Strategy Update Record",
        "generated_at": generated_at,
        "status": status,
        "public_safe": True,
        "purpose": (
            "Record how Qadam would recursively improve strategy research "
            "priority from remembered edge patterns, without applying changes."
        ),
        "edge_memory_ledger_status": edge_memory_ledger.get("status"),
        "pattern_engine_status": pattern_recognition_engine.get("status"),
        "quantum_gate_status": edge_memory_ledger.get("quantum_gate_status"),
        "quantum_dependency_satisfied": edge_memory_ledger.get(
            "quantum_dependency_satisfied"
        )
        is True,
        "memory_record_count": edge_memory_ledger.get("memory_record_count"),
        "strategy_update_proposal_count": len(proposals),
        "strategy_update_applied_count": 0,
        "proposals": proposals,
        "recursive_improvement_policy": {
            "status": "proposal_recording_active" if proposals else "blocked",
            "cadence": "daily_after_edge_memory_ledger",
            "uses_edge_memory": True,
            "uses_quantum_mandatory_review": True,
            "uses_pattern_recognition_engine": True,
            "updates_are_applied_automatically": False,
            "strategy_mutation_allowed": False,
            "threshold_mutation_allowed": False,
            "paper_order_allowed": False,
            "broker_write_allowed": False,
            "goal_alignment": (
                "Improve research ranking for the GBP 100,000 to GBP 200,000 "
                "60-day paper portfolio goal while keeping execution governed "
                "by the existing guarded paper route."
            ),
        },
        "blocked_reason": None
        if status == "strategy_update_record_ready"
        else "edge_memory_or_pattern_engine_not_ready",
        "documentation_routes": {
            "runtime_artifact": f"data/runtime/{STRATEGY_UPDATE_RECORD_RUNTIME_ARTIFACT}",
            "history": f"data/runtime/{STRATEGY_UPDATE_RECORD_HISTORY}",
            "event_log": f"data/runtime/{STRATEGY_UPDATE_RECORD_EVENT_LOG}",
            "source_edge_memory_ledger": "data/runtime/edge_memory_ledger.json",
            "source_pattern_engine": "data/runtime/pattern_recognition_engine.json",
        },
        "boundary": STRATEGY_UPDATE_RECORD_BOUNDARY,
    }
    for field in STRATEGY_UPDATE_RECORD_AUTHORITY_FALSE_FIELDS:
        update_record[field] = False
    return update_record


def validate_strategy_update_record(payload: dict[str, Any]) -> None:
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
        "pattern_engine_status",
        "quantum_gate_status",
        "quantum_dependency_satisfied",
        "memory_record_count",
        "strategy_update_proposal_count",
        "strategy_update_applied_count",
        "proposals",
        "recursive_improvement_policy",
        "blocked_reason",
        "documentation_routes",
        "boundary",
        *STRATEGY_UPDATE_RECORD_AUTHORITY_FALSE_FIELDS,
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"strategy update record missing fields: {missing}")
    if payload.get("schema_version") != STRATEGY_UPDATE_RECORD_SCHEMA_VERSION:
        raise ValueError("strategy update record schema mismatch")
    if payload.get("artifact_type") != "strategy_update_record":
        raise ValueError("strategy update record artifact type mismatch")
    if payload.get("status") not in STRATEGY_UPDATE_RECORD_STATUSES:
        raise ValueError("strategy update record status invalid")
    if payload.get("public_safe") is not True:
        raise ValueError("strategy update record must be public-safe")
    if "read-only strategy update record" not in str(payload.get("boundary", "")):
        raise ValueError("strategy update record boundary weak")
    for field in STRATEGY_UPDATE_RECORD_AUTHORITY_FALSE_FIELDS:
        if payload.get(field) is not False:
            raise ValueError(f"strategy update record authority leak: {field}")
    policy = _as_dict(payload.get("recursive_improvement_policy"))
    for field in (
        "strategy_mutation_allowed",
        "threshold_mutation_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
    ):
        if policy.get(field) is not False:
            raise ValueError(f"strategy update policy authority leak: {field}")
    if policy.get("updates_are_applied_automatically") is not False:
        raise ValueError("strategy updates cannot apply automatically")
    proposals = payload.get("proposals")
    if not isinstance(proposals, list):
        raise ValueError("strategy update proposals must be a list")
    ready = payload.get("status") == "strategy_update_record_ready"
    if ready:
        if payload.get("edge_memory_ledger_status") != "edge_memory_active":
            raise ValueError("strategy update record requires active edge memory")
        if payload.get("pattern_engine_status") != "pattern_engine_ready_for_quantum_oracle":
            raise ValueError("strategy update record requires ready pattern engine")
        if payload.get("quantum_gate_status") != "quantum_review_gate_passed":
            raise ValueError("strategy update record requires passed quantum gate")
        if payload.get("quantum_dependency_satisfied") is not True:
            raise ValueError("strategy update record quantum dependency not satisfied")
        if _int(payload.get("memory_record_count")) != EDGE_MEMORY_LEDGER_REQUIRED_PATTERN_COUNT:
            raise ValueError("strategy update record memory count mismatch")
        if _int(payload.get("strategy_update_proposal_count")) != EDGE_MEMORY_LEDGER_REQUIRED_PATTERN_COUNT:
            raise ValueError("strategy update record must expose five proposals")
        if payload.get("blocked_reason") is not None:
            raise ValueError("ready strategy update record cannot be blocked")
    else:
        if payload.get("blocked_reason") != "edge_memory_or_pattern_engine_not_ready":
            raise ValueError("blocked strategy update record needs blocked reason")
        if proposals:
            raise ValueError("blocked strategy update record cannot emit proposals")
    if _int(payload.get("strategy_update_proposal_count")) != len(proposals):
        raise ValueError("strategy update proposal count mismatch")
    if _int(payload.get("strategy_update_applied_count")) != 0:
        raise ValueError("strategy update record cannot apply updates")
    for proposal in proposals:
        if not isinstance(proposal, dict):
            raise ValueError("strategy update proposal must be a dict")
        if proposal.get("status") != "strategy_update_recorded_not_applied":
            raise ValueError("strategy update proposal status invalid")
        if proposal.get("applied") is not False:
            raise ValueError("strategy update proposal cannot be applied")
        if proposal.get("applied_at") is not None:
            raise ValueError("strategy update proposal applied_at must remain empty")
        if proposal.get("quantum_mandatory_review_required") is not True:
            raise ValueError("strategy update proposal must require quantum review")
        if proposal.get("quantum_dependency_satisfied") is not True:
            raise ValueError("strategy update proposal quantum dependency not satisfied")
        if proposal.get("quantum_oracle_input_contract_status") != "accepted":
            raise ValueError("strategy update proposal oracle contract not accepted")
        if proposal.get("optimized_for_quantum_oracle") is not True:
            raise ValueError("strategy update proposal not optimized for quantum oracle")
        if not proposal.get("edge_memory_id"):
            raise ValueError("strategy update proposal missing edge memory reference")
        if not proposal.get("target_strategy_component"):
            raise ValueError("strategy update proposal missing target strategy component")
        for field in STRATEGY_UPDATE_RECORD_AUTHORITY_FALSE_FIELDS:
            if proposal.get(field) is not False:
                raise ValueError(f"strategy update proposal authority leak: {field}")


def write_strategy_update_record(
    payload: dict[str, Any],
    settings: Settings | None = None,
) -> dict[str, Any]:
    validate_strategy_update_record(payload)
    output_path, history_path, event_path = strategy_update_record_paths(settings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    event = {
        "schema_version": STRATEGY_UPDATE_RECORD_SCHEMA_VERSION,
        "event_type": STRATEGY_UPDATE_RECORD_EVENT_TYPE,
        "component": STRATEGY_UPDATE_RECORD_COMPONENT,
        "created_at": payload.get("generated_at") or _now(),
        "status": payload.get("status"),
        "edge_memory_ledger_status": payload.get("edge_memory_ledger_status"),
        "pattern_engine_status": payload.get("pattern_engine_status"),
        "strategy_update_proposal_count": payload.get("strategy_update_proposal_count"),
        "strategy_update_applied_count": payload.get("strategy_update_applied_count"),
        "quantum_gate_status": payload.get("quantum_gate_status"),
        "authority_leak_count": sum(
            1
            for field in STRATEGY_UPDATE_RECORD_AUTHORITY_FALSE_FIELDS
            if payload.get(field) is not False
        ),
        "public_safe": True,
        "boundary": STRATEGY_UPDATE_RECORD_BOUNDARY,
    }
    with event_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    return {
        "output_path": str(output_path),
        "history_path": str(history_path),
        "event_log_path": str(event_path),
    }
