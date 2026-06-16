"""Quantum-mandatory review gate for Qadam edge findings.

The gate makes quantum review a hard dependency for edge documentation and
edge-derived strategy updates. It is deliberately non-executing: passing this
gate can satisfy the quantum dependency for research ranking, but cannot create
trade candidates, approve risk, submit orders, call brokers, send Telegram
messages live, or grant proof credit.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.edge_pattern_ledger import EDGE_PATTERN_AUTHORITY_FALSE_FIELDS


QUANTUM_MANDATORY_REVIEW_GATE_SCHEMA_VERSION = 1
QUANTUM_MANDATORY_REVIEW_GATE_RUNTIME_ARTIFACT = "quantum_mandatory_review_gate.json"
QUANTUM_MANDATORY_REVIEW_GATE_HISTORY = "quantum_mandatory_review_gate_history.jsonl"
QUANTUM_MANDATORY_REVIEW_GATE_EVENT_LOG = "quantum_mandatory_review_gate_events.jsonl"
QUANTUM_MANDATORY_REVIEW_GATE_EVENT_TYPE = "quantum_mandatory_review_gate_recorded"
QUANTUM_MANDATORY_REVIEW_GATE_COMPONENT = "quantum_mandatory_review_gate"
QUANTUM_MANDATORY_REVIEW_GATE_REQUIRED_MIN_PATTERN_COUNT = 5

QUANTUM_MANDATORY_REVIEW_GATE_BOUNDARY = (
    "Quantum-Mandatory Review Gate is read-only dependency enforcement. It can "
    "confirm whether every edge finding has attached quantum non-linear review "
    "before research ranking or strategy-update proposals continue, but it "
    "cannot create source quorum, trade candidates, risk approval, paper orders, "
    "broker writes, Telegram commands, Telegram live sends, prediction-market "
    "writes, quantum jobs, live capital, or proof credit."
)

QUANTUM_REVIEW_GATE_BLOCKING_STATUSES = {
    "not_run",
    "missing",
    "blocked",
    "degraded",
    "failed",
    "provider_error",
    "provider_network_error",
    "blocked_provider_probe_failed",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def quantum_mandatory_review_gate_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / QUANTUM_MANDATORY_REVIEW_GATE_RUNTIME_ARTIFACT,
        runtime / QUANTUM_MANDATORY_REVIEW_GATE_HISTORY,
        runtime / QUANTUM_MANDATORY_REVIEW_GATE_EVENT_LOG,
    )


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _slug(value: Any) -> str:
    return str(value or "").strip().replace(" ", "_").lower() or "unknown"


def _quantum_review_complete(quantum_review: dict[str, Any]) -> tuple[bool, list[str]]:
    missing: list[str] = []
    status = str(quantum_review.get("status") or "not_run")
    mode = str(quantum_review.get("mode") or "")
    backend = str(quantum_review.get("backend") or "")
    if not quantum_review:
        missing.append("quantum_review_missing")
    if status != "ok" or status in QUANTUM_REVIEW_GATE_BLOCKING_STATUSES:
        missing.append(f"quantum_status_not_ok:{status}")
    if quantum_review.get("core_gate") is not True:
        missing.append("quantum_core_gate_not_true")
    if not mode or mode == "not_run":
        missing.append("quantum_mode_missing")
    if not backend or backend == "not_exported":
        missing.append("quantum_backend_missing")
    return not missing, missing


def _pattern_gate_decision(
    *,
    pattern: dict[str, Any],
    quantum_review: dict[str, Any],
) -> dict[str, Any]:
    complete, missing = _quantum_review_complete(quantum_review)
    passed_criteria = {str(item) for item in _as_list(pattern.get("passed_criteria"))}
    if "quantum_nonlinear_review" not in passed_criteria:
        missing.append("pattern_quantum_criterion_not_passed")
    decision_satisfied = complete and not missing
    decision = {
        "pattern_id": pattern.get("pattern_id") or f"quantum-gate:{_slug(pattern.get('sleeve_key'))}",
        "sleeve_key": _slug(pattern.get("sleeve_key")),
        "market_sleeve": str(pattern.get("label") or pattern.get("market_sleeve") or "unknown"),
        "status": "quantum_review_dependency_satisfied"
        if decision_satisfied
        else "blocked_pending_quantum_review",
        "quantum_required": True,
        "review_attached": bool(quantum_review),
        "review_complete": complete,
        "review_status": quantum_review.get("status", "not_run"),
        "review_mode": quantum_review.get("mode", "not_run"),
        "review_backend": quantum_review.get("backend", "not_exported"),
        "fire_opal_ibm_status": quantum_review.get("fire_opal_ibm_status", "not_exported"),
        "core_gate": quantum_review.get("core_gate") is True,
        "dependency_satisfied": decision_satisfied,
        "missing_requirements": sorted(set(missing)),
        "edge_validation_dependency_satisfied": decision_satisfied,
        "candidate_ranking_dependency_satisfied": decision_satisfied,
        "strategy_update_dependency_satisfied": decision_satisfied,
        "paper_trade_consideration_quantum_dependency_satisfied": decision_satisfied,
        "boundary": (
            "Pattern-level quantum review can satisfy a research dependency only. "
            "It cannot approve risk, create candidates, stage orders, submit "
            "paper trades, or write to brokers."
        ),
    }
    for field in EDGE_PATTERN_AUTHORITY_FALSE_FIELDS:
        decision[field] = False
    return decision


def build_quantum_mandatory_review_gate(
    *,
    edge_ledger: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at = generated_at or _now()
    quantum_review = _as_dict(edge_ledger.get("quantum_review"))
    patterns = [pattern for pattern in _as_list(edge_ledger.get("patterns")) if isinstance(pattern, dict)]
    pattern_decisions = [
        _pattern_gate_decision(pattern=pattern, quantum_review=quantum_review)
        for pattern in patterns
    ]
    complete, quantum_missing = _quantum_review_complete(quantum_review)
    candidate_count = _int(edge_ledger.get("candidate_pattern_count") or len(patterns))
    satisfied_count = sum(1 for decision in pattern_decisions if decision["dependency_satisfied"])
    blocked_count = len(pattern_decisions) - satisfied_count
    enough_patterns = len(pattern_decisions) >= QUANTUM_MANDATORY_REVIEW_GATE_REQUIRED_MIN_PATTERN_COUNT
    count_matches = candidate_count == len(pattern_decisions)
    gate_passed = complete and enough_patterns and count_matches and blocked_count == 0
    fail_closed_reasons: list[str] = []
    if quantum_missing:
        fail_closed_reasons.extend(quantum_missing)
    if not enough_patterns:
        fail_closed_reasons.append("candidate_pattern_count_below_contract")
    if not count_matches:
        fail_closed_reasons.append("candidate_pattern_count_mismatch")
    if blocked_count:
        fail_closed_reasons.append("one_or_more_patterns_missing_quantum_review")
    gate = {
        "schema_version": QUANTUM_MANDATORY_REVIEW_GATE_SCHEMA_VERSION,
        "artifact_type": "quantum_mandatory_review_gate",
        "artifact_id": "quantum-mandatory-review-gate:latest",
        "generated_at": generated_at,
        "status": "quantum_review_gate_passed" if gate_passed else "quantum_review_gate_blocked",
        "public_safe": True,
        "gate_name": "Quantum-Mandatory Review Gate",
        "gate_scope": "daily_edge_findings_and_edge_pattern_strategy_updates",
        "mandatory_before": [
            "validated_edge_count_increment",
            "candidate_pattern_ranking",
            "strategy_update_proposal",
            "telegram_edge_findings_review_body",
        ],
        "quantum_review_required": True,
        "quantum_review_present": bool(quantum_review),
        "quantum_review_complete": complete,
        "quantum_review_status": quantum_review.get("status", "not_run"),
        "quantum_review_mode": quantum_review.get("mode", "not_run"),
        "quantum_backend": quantum_review.get("backend", "not_exported"),
        "fire_opal_ibm_status": quantum_review.get("fire_opal_ibm_status", "not_exported"),
        "quantum_core_gate": quantum_review.get("core_gate") is True,
        "source_edge_ledger_status": edge_ledger.get("status", "not_exported"),
        "candidate_pattern_count": candidate_count,
        "pattern_review_count": len(pattern_decisions),
        "pattern_review_dependency_satisfied_count": satisfied_count,
        "pattern_review_dependency_blocked_count": blocked_count,
        "pattern_gate_decisions": pattern_decisions,
        "edge_validation_dependency_satisfied": gate_passed,
        "candidate_ranking_dependency_satisfied": gate_passed,
        "strategy_update_dependency_satisfied": gate_passed,
        "telegram_findings_dependency_satisfied": gate_passed,
        "fail_closed_reasons": sorted(set(fail_closed_reasons)),
        "downstream_effects": {
            "validated_edge_quantum_dependency_satisfied": gate_passed,
            "candidate_ranking_dependency_satisfied": gate_passed,
            "strategy_update_proposal_dependency_satisfied": gate_passed,
            "telegram_review_body_dependency_satisfied": gate_passed,
            "paper_order_allowed": False,
            "broker_write_allowed": False,
            "live_capital_enabled": False,
            "proof_credit_allowed": False,
        },
        "documentation_routes": {
            "runtime_artifact": f"data/runtime/{QUANTUM_MANDATORY_REVIEW_GATE_RUNTIME_ARTIFACT}",
            "history": f"data/runtime/{QUANTUM_MANDATORY_REVIEW_GATE_HISTORY}",
            "event_log": f"data/runtime/{QUANTUM_MANDATORY_REVIEW_GATE_EVENT_LOG}",
            "source_artifact": "data/runtime/edge_pattern_ledger.json",
            "daily_findings_surface": "data/runtime/daily_edge_findings_brief.json",
        },
        "boundary": QUANTUM_MANDATORY_REVIEW_GATE_BOUNDARY,
    }
    for field in EDGE_PATTERN_AUTHORITY_FALSE_FIELDS:
        gate[field] = False
    return gate


def validate_quantum_mandatory_review_gate(payload: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "artifact_type",
        "artifact_id",
        "generated_at",
        "status",
        "public_safe",
        "gate_name",
        "gate_scope",
        "mandatory_before",
        "quantum_review_required",
        "quantum_review_present",
        "quantum_review_complete",
        "quantum_review_status",
        "quantum_review_mode",
        "quantum_backend",
        "fire_opal_ibm_status",
        "quantum_core_gate",
        "source_edge_ledger_status",
        "candidate_pattern_count",
        "pattern_review_count",
        "pattern_review_dependency_satisfied_count",
        "pattern_review_dependency_blocked_count",
        "pattern_gate_decisions",
        "edge_validation_dependency_satisfied",
        "candidate_ranking_dependency_satisfied",
        "strategy_update_dependency_satisfied",
        "telegram_findings_dependency_satisfied",
        "fail_closed_reasons",
        "downstream_effects",
        "documentation_routes",
        "boundary",
        *EDGE_PATTERN_AUTHORITY_FALSE_FIELDS,
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"quantum mandatory review gate missing fields: {missing}")
    if payload.get("schema_version") != QUANTUM_MANDATORY_REVIEW_GATE_SCHEMA_VERSION:
        raise ValueError("quantum mandatory review gate schema mismatch")
    if payload.get("artifact_type") != "quantum_mandatory_review_gate":
        raise ValueError("quantum mandatory review gate artifact type mismatch")
    if payload.get("public_safe") is not True:
        raise ValueError("quantum mandatory review gate must be public-safe")
    if payload.get("status") not in {"quantum_review_gate_passed", "quantum_review_gate_blocked"}:
        raise ValueError("quantum mandatory review gate status invalid")
    if payload.get("quantum_review_required") is not True:
        raise ValueError("quantum mandatory review gate must require quantum review")
    for field in EDGE_PATTERN_AUTHORITY_FALSE_FIELDS:
        if payload.get(field) is not False:
            raise ValueError(f"quantum mandatory review gate authority leak: {field}")
    pattern_decisions = payload.get("pattern_gate_decisions")
    if not isinstance(pattern_decisions, list):
        raise ValueError("quantum mandatory review gate pattern decisions must be a list")
    candidate_count = _int(payload.get("candidate_pattern_count"))
    if candidate_count != len(pattern_decisions):
        raise ValueError("quantum mandatory review gate candidate count mismatch")
    if len(pattern_decisions) < QUANTUM_MANDATORY_REVIEW_GATE_REQUIRED_MIN_PATTERN_COUNT:
        raise ValueError("quantum mandatory review gate needs at least five pattern decisions")
    satisfied_count = sum(1 for decision in pattern_decisions if decision.get("dependency_satisfied") is True)
    blocked_count = len(pattern_decisions) - satisfied_count
    if _int(payload.get("pattern_review_dependency_satisfied_count")) != satisfied_count:
        raise ValueError("quantum mandatory review gate satisfied count mismatch")
    if _int(payload.get("pattern_review_dependency_blocked_count")) != blocked_count:
        raise ValueError("quantum mandatory review gate blocked count mismatch")
    for decision in pattern_decisions:
        if not isinstance(decision, dict):
            raise ValueError("quantum mandatory review gate decision must be a dict")
        if decision.get("quantum_required") is not True:
            raise ValueError("quantum mandatory review gate decision must require quantum")
        if decision.get("dependency_satisfied") is True:
            if decision.get("review_attached") is not True:
                raise ValueError("quantum mandatory review gate satisfied decision lacks review")
            if decision.get("review_complete") is not True:
                raise ValueError("quantum mandatory review gate satisfied decision incomplete")
            if decision.get("core_gate") is not True:
                raise ValueError("quantum mandatory review gate satisfied decision lacks core gate")
            if decision.get("review_status") != "ok":
                raise ValueError("quantum mandatory review gate satisfied decision status not ok")
            if decision.get("missing_requirements"):
                raise ValueError("quantum mandatory review gate satisfied decision has missing requirements")
        if decision.get("candidate_ranking_dependency_satisfied") is True and decision.get("dependency_satisfied") is not True:
            raise ValueError("quantum mandatory review gate decision lets ranking bypass quantum")
        if decision.get("strategy_update_dependency_satisfied") is True and decision.get("dependency_satisfied") is not True:
            raise ValueError("quantum mandatory review gate decision lets strategy bypass quantum")
        for field in EDGE_PATTERN_AUTHORITY_FALSE_FIELDS:
            if decision.get(field) is not False:
                raise ValueError(f"quantum mandatory review gate decision authority leak: {field}")
    gate_passed = payload.get("status") == "quantum_review_gate_passed"
    if gate_passed:
        if payload.get("quantum_review_present") is not True:
            raise ValueError("quantum mandatory review gate passed without review present")
        if payload.get("quantum_review_complete") is not True:
            raise ValueError("quantum mandatory review gate passed without complete review")
        if payload.get("quantum_review_status") != "ok":
            raise ValueError("quantum mandatory review gate passed with non-ok quantum status")
        if payload.get("quantum_core_gate") is not True:
            raise ValueError("quantum mandatory review gate passed without core gate")
        if blocked_count != 0:
            raise ValueError("quantum mandatory review gate passed with blocked patterns")
        for key in (
            "edge_validation_dependency_satisfied",
            "candidate_ranking_dependency_satisfied",
            "strategy_update_dependency_satisfied",
            "telegram_findings_dependency_satisfied",
        ):
            if payload.get(key) is not True:
                raise ValueError(f"quantum mandatory review gate passed but {key}=False")
    else:
        if not payload.get("fail_closed_reasons"):
            raise ValueError("quantum mandatory review gate blocked without fail-closed reason")
        for key in (
            "edge_validation_dependency_satisfied",
            "candidate_ranking_dependency_satisfied",
            "strategy_update_dependency_satisfied",
            "telegram_findings_dependency_satisfied",
        ):
            if payload.get(key) is True:
                raise ValueError(f"quantum mandatory review gate blocked but {key}=True")
    effects = _as_dict(payload.get("downstream_effects"))
    for key in (
        "paper_order_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
        "proof_credit_allowed",
    ):
        if effects.get(key) is not False:
            raise ValueError(f"quantum mandatory review gate downstream authority leak: {key}")
    if not gate_passed:
        for key in (
            "validated_edge_quantum_dependency_satisfied",
            "candidate_ranking_dependency_satisfied",
            "strategy_update_proposal_dependency_satisfied",
            "telegram_review_body_dependency_satisfied",
        ):
            if effects.get(key) is True:
                raise ValueError(f"quantum mandatory review gate blocked but downstream {key}=True")
    if "dependency enforcement" not in str(payload.get("boundary", "")):
        raise ValueError("quantum mandatory review gate boundary weak")


def write_quantum_mandatory_review_gate(
    payload: dict[str, Any],
    settings: Settings | None = None,
) -> dict[str, Any]:
    validate_quantum_mandatory_review_gate(payload)
    output_path, history_path, event_path = quantum_mandatory_review_gate_paths(settings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    event = {
        "schema_version": QUANTUM_MANDATORY_REVIEW_GATE_SCHEMA_VERSION,
        "event_type": QUANTUM_MANDATORY_REVIEW_GATE_EVENT_TYPE,
        "component": QUANTUM_MANDATORY_REVIEW_GATE_COMPONENT,
        "created_at": payload.get("generated_at") or _now(),
        "status": payload.get("status"),
        "quantum_review_status": payload.get("quantum_review_status"),
        "quantum_backend": payload.get("quantum_backend"),
        "quantum_core_gate": payload.get("quantum_core_gate") is True,
        "candidate_pattern_count": payload.get("candidate_pattern_count"),
        "pattern_review_dependency_satisfied_count": payload.get(
            "pattern_review_dependency_satisfied_count"
        ),
        "pattern_review_dependency_blocked_count": payload.get(
            "pattern_review_dependency_blocked_count"
        ),
        "authority_leak_count": sum(
            1 for field in EDGE_PATTERN_AUTHORITY_FALSE_FIELDS if payload.get(field) is not False
        ),
        "public_safe": True,
        "boundary": QUANTUM_MANDATORY_REVIEW_GATE_BOUNDARY,
    }
    with event_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    return {
        "output_path": str(output_path),
        "history_path": str(history_path),
        "event_log_path": str(event_path),
    }
