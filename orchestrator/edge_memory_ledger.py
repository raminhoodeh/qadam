"""Read-only edge memory ledger for Qadam.

The ledger preserves daily memory for recurring source/price patterns. It is a
research memory layer only: it can remember pattern persistence and provide
inputs to strategy update records, but it cannot mutate strategy weights,
approve trades, submit paper orders, or write to a broker.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.pattern_recognition_engine import (
    PATTERN_RECOGNITION_ENGINE_REQUIRED_MIN_SOURCE_COUNT,
    PATTERN_RECOGNITION_ENGINE_REQUIRED_PATTERN_COUNT,
    validate_pattern_recognition_engine,
)


EDGE_MEMORY_LEDGER_SCHEMA_VERSION = 1
EDGE_MEMORY_LEDGER_RUNTIME_ARTIFACT = "edge_memory_ledger.json"
EDGE_MEMORY_LEDGER_HISTORY = "edge_memory_ledger_history.jsonl"
EDGE_MEMORY_LEDGER_EVENT_LOG = "edge_memory_ledger_events.jsonl"
EDGE_MEMORY_LEDGER_EVENT_TYPE = "edge_memory_ledger_recorded"
EDGE_MEMORY_LEDGER_COMPONENT = "edge_memory_ledger"

EDGE_MEMORY_LEDGER_REQUIRED_MIN_SOURCE_COUNT = PATTERN_RECOGNITION_ENGINE_REQUIRED_MIN_SOURCE_COUNT
EDGE_MEMORY_LEDGER_REQUIRED_PATTERN_COUNT = PATTERN_RECOGNITION_ENGINE_REQUIRED_PATTERN_COUNT

EDGE_MEMORY_LEDGER_AUTHORITY_FALSE_FIELDS: tuple[str, ...] = (
    "source_quorum_credit_allowed",
    "trade_candidate_creation_allowed",
    "risk_approval_allowed",
    "execution_allowed",
    "paper_order_allowed",
    "broker_write_allowed",
    "prediction_market_write_allowed",
    "telegram_command_path_enabled",
    "telegram_trade_command_enabled",
    "telegram_live_send_allowed",
    "quantum_job_authority",
    "quantum_hardware_submission_allowed",
    "quantum_provider_call_allowed",
    "strategy_mutation_allowed",
    "strategy_weight_update_allowed",
    "model_weight_mutation_allowed",
    "source_registry_mutation_allowed",
    "portfolio_allocation_allowed",
    "order_sizing_allowed",
    "live_capital_enabled",
    "proof_credit_allowed",
)

EDGE_MEMORY_LEDGER_BOUNDARY = (
    "Edge Memory Ledger is read-only edge memory. It can remember daily "
    "source/price pattern observations, persistence, quantum-oracle readiness, "
    "and strategy-record inputs, but it cannot create source quorum, trade "
    "candidates, risk approval, strategy mutations, model-weight mutations, "
    "portfolio allocation, order sizing, paper orders, broker writes, Telegram "
    "commands, Telegram live sends, quantum provider calls, hardware "
    "submissions, live capital, or proof credit."
)

EDGE_MEMORY_LEDGER_STATUSES = {
    "edge_memory_active",
    "edge_memory_blocked_pending_pattern_engine",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def edge_memory_ledger_paths(settings: Settings | None = None) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / EDGE_MEMORY_LEDGER_RUNTIME_ARTIFACT,
        runtime / EDGE_MEMORY_LEDGER_HISTORY,
        runtime / EDGE_MEMORY_LEDGER_EVENT_LOG,
    )


def read_edge_memory_ledger(settings: Settings | None = None) -> dict[str, Any]:
    output_path, _, _ = edge_memory_ledger_paths(settings)
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
    return round(max(0.0, min(1.0, value)), 3)


def _slug(value: Any) -> str:
    return str(value or "").strip().replace(" ", "_").lower() or "unknown"


def _parse_datetime(value: Any) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _previous_records_by_sleeve(previous_ledger: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for record in _as_list(_as_dict(previous_ledger).get("memory_records")):
        if isinstance(record, dict):
            records[_slug(record.get("sleeve_key"))] = record
    return records


def _unique_dates(values: list[Any], current_date: str) -> list[str]:
    dates = {current_date}
    for value in values:
        parsed = _parse_date(value)
        if parsed is not None:
            dates.add(parsed.isoformat())
    return sorted(dates)


def _consecutive_count(dates: list[str], current_date: str) -> int:
    parsed_dates = {_parse_date(value) for value in dates}
    parsed_dates.discard(None)
    cursor = _parse_date(current_date)
    if cursor is None:
        return 0
    count = 0
    while cursor in parsed_dates:
        count += 1
        cursor = cursor - timedelta(days=1)
    return count


def _upsert_history_tail(
    *,
    previous_record: dict[str, Any],
    pattern: dict[str, Any],
    current_date: str,
    generated_at: str,
) -> list[dict[str, Any]]:
    by_date: dict[str, dict[str, Any]] = {}
    for entry in _as_list(previous_record.get("readiness_history_tail")):
        if not isinstance(entry, dict):
            continue
        entry_date = str(entry.get("date") or "")
        if _parse_date(entry_date) is not None:
            by_date[entry_date] = entry
    by_date[current_date] = {
        "date": current_date,
        "observed_at": generated_at,
        "pattern_id": pattern.get("pattern_id"),
        "edge_readiness_score": _clip(_float(pattern.get("edge_readiness_score"))),
        "ambiguity_score": _clip(_float(pattern.get("ambiguity_score"))),
        "signal_strength": _clip(
            _float(
                _as_dict(pattern.get("compressed_oracle_register")).get("q0_signal_strength")
            )
        ),
        "quantum_oracle_input_contract_status": pattern.get(
            "quantum_oracle_input_contract_status"
        ),
    }
    return [by_date[key] for key in sorted(by_date)[-10:]]


def _stability_assessment(history_tail: list[dict[str, Any]]) -> dict[str, Any]:
    if len(history_tail) < 2:
        return {
            "status": "new_observation",
            "readiness_delta": 0.0,
            "direction": "insufficient_history",
        }
    previous = history_tail[-2]
    latest = history_tail[-1]
    delta = round(
        _float(latest.get("edge_readiness_score")) - _float(previous.get("edge_readiness_score")),
        3,
    )
    if delta > 0.02:
        direction = "strengthening"
    elif delta < -0.02:
        direction = "weakening"
    else:
        direction = "stable"
    return {
        "status": "tracked",
        "readiness_delta": delta,
        "direction": direction,
        "previous_date": previous.get("date"),
        "latest_date": latest.get("date"),
    }


def _memory_record(
    *,
    pattern: dict[str, Any],
    previous_record: dict[str, Any],
    current_date: str,
    generated_at: str,
) -> dict[str, Any]:
    sleeve_key = _slug(pattern.get("sleeve_key"))
    observation_dates = _unique_dates(_as_list(previous_record.get("observation_dates")), current_date)
    first_seen_at = previous_record.get("first_seen_at") or generated_at
    history_tail = _upsert_history_tail(
        previous_record=previous_record,
        pattern=pattern,
        current_date=current_date,
        generated_at=generated_at,
    )
    record = {
        "memory_id": f"edge-memory:{sleeve_key}",
        "sleeve_key": sleeve_key,
        "market_sleeve": pattern.get("market_sleeve"),
        "pattern_id": pattern.get("pattern_id"),
        "status": "remembered_candidate_edge",
        "source_application": "all_qadam_sources_cross_scanned_for_this_memory",
        "source_count": _int(pattern.get("source_count")),
        "watched_symbols": _as_list(pattern.get("instrument_symbols")),
        "first_seen_at": first_seen_at,
        "last_seen_at": generated_at,
        "observation_dates": observation_dates,
        "observation_count": len(observation_dates),
        "consecutive_observation_count": _consecutive_count(observation_dates, current_date),
        "readiness_history_tail": history_tail,
        "latest_edge_readiness_score": _clip(_float(pattern.get("edge_readiness_score"))),
        "latest_ambiguity_score": _clip(_float(pattern.get("ambiguity_score"))),
        "latest_signal_strength": _clip(
            _float(
                _as_dict(pattern.get("compressed_oracle_register")).get("q0_signal_strength")
            )
        ),
        "stability_assessment": _stability_assessment(history_tail),
        "persistence_state": (
            "thirty_day_persistence_observed"
            if len(observation_dates) >= 30
            else "persistence_building"
        ),
        "quantum_mandatory_review_required": True,
        "quantum_gate_dependency_satisfied": (
            pattern.get("quantum_gate_dependency_satisfied") is True
        ),
        "quantum_gate_decision_status": pattern.get("quantum_gate_decision_status"),
        "quantum_oracle_input_contract_status": pattern.get(
            "quantum_oracle_input_contract_status"
        ),
        "optimized_for_quantum_oracle": pattern.get("optimized_for_quantum_oracle") is True,
        "allowed_strategy_memory_uses": [
            "rank_research_watch_priority",
            "document_threshold_calibration_input",
            "prepare_strategy_update_record",
            "inform_llm_adversarial_review",
        ],
        "disallowed_strategy_memory_uses": [
            "approve_trade_candidate",
            "mutate_live_strategy",
            "change_model_weights_directly",
            "size_or_submit_order",
            "grant_proof_credit",
        ],
        "strategy_update_record_input_allowed": True,
        "paper_trade_effect": (
            "Research-memory input only. Paper trading still requires Strategy "
            "Lead, Signal Integrity, risk, idempotency, Q-CTRL consultation, "
            "and Alpaca Paper gates."
        ),
        "recursive_improvement_note": (
            "If this memory persists across actual calendar observations and "
            "survives quantum and LLM review, Qadam may record a future strategy "
            "proposal. The ledger does not apply the proposal itself."
        ),
    }
    for field in EDGE_MEMORY_LEDGER_AUTHORITY_FALSE_FIELDS:
        record[field] = False
    return record


def build_edge_memory_ledger(
    *,
    pattern_recognition_engine: dict[str, Any],
    edge_pattern_ledger: dict[str, Any] | None = None,
    previous_ledger: dict[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build Qadam's read-only memory ledger for recurring edge observations."""

    generated_at = generated_at or _now()
    generated_date = _parse_datetime(generated_at).date().isoformat()
    validate_pattern_recognition_engine(pattern_recognition_engine)
    engine_status = pattern_recognition_engine.get("status")
    candidate_patterns = _as_list(pattern_recognition_engine.get("candidate_patterns"))
    status = (
        "edge_memory_active"
        if engine_status == "pattern_engine_ready_for_quantum_oracle"
        and len(candidate_patterns) >= EDGE_MEMORY_LEDGER_REQUIRED_PATTERN_COUNT
        else "edge_memory_blocked_pending_pattern_engine"
    )
    previous_by_sleeve = _previous_records_by_sleeve(previous_ledger)
    memory_records = [
        _memory_record(
            pattern=pattern,
            previous_record=previous_by_sleeve.get(_slug(pattern.get("sleeve_key")), {}),
            current_date=generated_date,
            generated_at=generated_at,
        )
        for pattern in candidate_patterns
        if status == "edge_memory_active" and isinstance(pattern, dict)
    ]
    observation_counts = [
        _int(record.get("observation_count")) for record in memory_records
    ]
    ledger = {
        "schema_version": EDGE_MEMORY_LEDGER_SCHEMA_VERSION,
        "artifact_type": "edge_memory_ledger",
        "artifact_id": "edge-memory-ledger:latest",
        "stage": "Stage 4A - Edge Memory Ledger",
        "generated_at": generated_at,
        "memory_date": generated_date,
        "status": status,
        "public_safe": True,
        "purpose": (
            "Remember daily candidate-edge observations so Qadam can compare "
            "today's source/price pattern recognition with prior calendar days."
        ),
        "pattern_engine_status": engine_status,
        "edge_pattern_ledger_status": _as_dict(edge_pattern_ledger).get("status"),
        "source_count": _as_dict(pattern_recognition_engine.get("source_scan")).get("source_count"),
        "candidate_pattern_count": pattern_recognition_engine.get("candidate_pattern_count"),
        "memory_record_count": len(memory_records),
        "minimum_observation_count": min(observation_counts) if observation_counts else 0,
        "maximum_observation_count": max(observation_counts) if observation_counts else 0,
        "quantum_gate_status": _as_dict(pattern_recognition_engine.get("quantum_gate")).get(
            "status"
        ),
        "quantum_dependency_satisfied": (
            _as_dict(pattern_recognition_engine.get("quantum_gate")).get("status")
            == "quantum_review_gate_passed"
        ),
        "memory_records": memory_records,
        "recursive_improvement_contract": {
            "status": "memory_ready" if status == "edge_memory_active" else "blocked",
            "uses_actual_calendar_dates": True,
            "same_day_runs_deduped": True,
            "strategy_update_record_input_allowed": status == "edge_memory_active",
            "strategy_mutation_allowed": False,
            "model_weight_mutation_allowed": False,
            "paper_order_allowed": False,
            "broker_write_allowed": False,
            "boundary": (
                "The memory contract may feed read-only strategy update records "
                "only. It cannot apply strategy changes or create orders."
            ),
        },
        "blocked_reason": None
        if status == "edge_memory_active"
        else "pattern_recognition_engine_not_ready_for_memory",
        "documentation_routes": {
            "runtime_artifact": f"data/runtime/{EDGE_MEMORY_LEDGER_RUNTIME_ARTIFACT}",
            "history": f"data/runtime/{EDGE_MEMORY_LEDGER_HISTORY}",
            "event_log": f"data/runtime/{EDGE_MEMORY_LEDGER_EVENT_LOG}",
            "source_pattern_engine": "data/runtime/pattern_recognition_engine.json",
            "source_edge_pattern_ledger": "data/runtime/edge_pattern_ledger.json",
        },
        "boundary": EDGE_MEMORY_LEDGER_BOUNDARY,
    }
    for field in EDGE_MEMORY_LEDGER_AUTHORITY_FALSE_FIELDS:
        ledger[field] = False
    return ledger


def validate_edge_memory_ledger(payload: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "artifact_type",
        "artifact_id",
        "stage",
        "generated_at",
        "memory_date",
        "status",
        "public_safe",
        "purpose",
        "pattern_engine_status",
        "source_count",
        "candidate_pattern_count",
        "memory_record_count",
        "minimum_observation_count",
        "maximum_observation_count",
        "quantum_gate_status",
        "quantum_dependency_satisfied",
        "memory_records",
        "recursive_improvement_contract",
        "blocked_reason",
        "documentation_routes",
        "boundary",
        *EDGE_MEMORY_LEDGER_AUTHORITY_FALSE_FIELDS,
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"edge memory ledger missing fields: {missing}")
    if payload.get("schema_version") != EDGE_MEMORY_LEDGER_SCHEMA_VERSION:
        raise ValueError("edge memory ledger schema mismatch")
    if payload.get("artifact_type") != "edge_memory_ledger":
        raise ValueError("edge memory ledger artifact type mismatch")
    if payload.get("status") not in EDGE_MEMORY_LEDGER_STATUSES:
        raise ValueError("edge memory ledger status invalid")
    if payload.get("public_safe") is not True:
        raise ValueError("edge memory ledger must be public-safe")
    if "read-only edge memory" not in str(payload.get("boundary", "")):
        raise ValueError("edge memory ledger boundary weak")
    for field in EDGE_MEMORY_LEDGER_AUTHORITY_FALSE_FIELDS:
        if payload.get(field) is not False:
            raise ValueError(f"edge memory ledger authority leak: {field}")
    recursive_contract = _as_dict(payload.get("recursive_improvement_contract"))
    for field in (
        "strategy_mutation_allowed",
        "model_weight_mutation_allowed",
        "paper_order_allowed",
        "broker_write_allowed",
    ):
        if recursive_contract.get(field) is not False:
            raise ValueError(f"edge memory recursive contract authority leak: {field}")
    memory_records = payload.get("memory_records")
    if not isinstance(memory_records, list):
        raise ValueError("edge memory records must be a list")
    active = payload.get("status") == "edge_memory_active"
    if active:
        if payload.get("pattern_engine_status") != "pattern_engine_ready_for_quantum_oracle":
            raise ValueError("active edge memory requires ready pattern engine")
        if _int(payload.get("source_count")) < EDGE_MEMORY_LEDGER_REQUIRED_MIN_SOURCE_COUNT:
            raise ValueError("edge memory source count below contract")
        if _int(payload.get("candidate_pattern_count")) < EDGE_MEMORY_LEDGER_REQUIRED_PATTERN_COUNT:
            raise ValueError("edge memory candidate pattern count below contract")
        if _int(payload.get("memory_record_count")) != EDGE_MEMORY_LEDGER_REQUIRED_PATTERN_COUNT:
            raise ValueError("edge memory must expose five records")
        if payload.get("quantum_gate_status") != "quantum_review_gate_passed":
            raise ValueError("edge memory requires passed quantum gate")
        if payload.get("quantum_dependency_satisfied") is not True:
            raise ValueError("edge memory quantum dependency not satisfied")
    else:
        if payload.get("blocked_reason") != "pattern_recognition_engine_not_ready_for_memory":
            raise ValueError("blocked edge memory needs blocked reason")
        if memory_records:
            raise ValueError("blocked edge memory cannot emit memory records")
    if _int(payload.get("memory_record_count")) != len(memory_records):
        raise ValueError("edge memory record count mismatch")
    for record in memory_records:
        if not isinstance(record, dict):
            raise ValueError("edge memory record must be a dict")
        if record.get("source_application") != "all_qadam_sources_cross_scanned_for_this_memory":
            raise ValueError("edge memory record must use all sources")
        if record.get("status") != "remembered_candidate_edge":
            raise ValueError("edge memory record status invalid")
        if record.get("quantum_mandatory_review_required") is not True:
            raise ValueError("edge memory record must require quantum review")
        if record.get("quantum_gate_dependency_satisfied") is not True:
            raise ValueError("edge memory record lacks quantum dependency")
        if record.get("quantum_oracle_input_contract_status") != "accepted":
            raise ValueError("edge memory record oracle contract not accepted")
        if record.get("optimized_for_quantum_oracle") is not True:
            raise ValueError("edge memory record not optimized for quantum oracle")
        dates = record.get("observation_dates")
        if not isinstance(dates, list) or not dates:
            raise ValueError("edge memory record needs observation dates")
        if len(dates) != len(set(dates)):
            raise ValueError("edge memory observation dates must be deduped")
        if payload.get("memory_date") not in dates:
            raise ValueError("edge memory record missing current memory date")
        if _int(record.get("observation_count")) != len(dates):
            raise ValueError("edge memory observation count mismatch")
        if _int(record.get("consecutive_observation_count")) < 1:
            raise ValueError("edge memory consecutive observation count invalid")
        history_tail = record.get("readiness_history_tail")
        if not isinstance(history_tail, list) or not history_tail:
            raise ValueError("edge memory readiness history tail missing")
        if history_tail[-1].get("date") != payload.get("memory_date"):
            raise ValueError("edge memory readiness history tail missing latest date")
        if record.get("strategy_update_record_input_allowed") is not True:
            raise ValueError("edge memory record must feed strategy update record")
        for field in EDGE_MEMORY_LEDGER_AUTHORITY_FALSE_FIELDS:
            if record.get(field) is not False:
                raise ValueError(f"edge memory record authority leak: {field}")


def write_edge_memory_ledger(
    payload: dict[str, Any],
    settings: Settings | None = None,
) -> dict[str, Any]:
    validate_edge_memory_ledger(payload)
    output_path, history_path, event_path = edge_memory_ledger_paths(settings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    event = {
        "schema_version": EDGE_MEMORY_LEDGER_SCHEMA_VERSION,
        "event_type": EDGE_MEMORY_LEDGER_EVENT_TYPE,
        "component": EDGE_MEMORY_LEDGER_COMPONENT,
        "created_at": payload.get("generated_at") or _now(),
        "memory_date": payload.get("memory_date"),
        "status": payload.get("status"),
        "pattern_engine_status": payload.get("pattern_engine_status"),
        "memory_record_count": payload.get("memory_record_count"),
        "minimum_observation_count": payload.get("minimum_observation_count"),
        "maximum_observation_count": payload.get("maximum_observation_count"),
        "quantum_gate_status": payload.get("quantum_gate_status"),
        "authority_leak_count": sum(
            1 for field in EDGE_MEMORY_LEDGER_AUTHORITY_FALSE_FIELDS if payload.get(field) is not False
        ),
        "public_safe": True,
        "boundary": EDGE_MEMORY_LEDGER_BOUNDARY,
    }
    with event_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    return {
        "output_path": str(output_path),
        "history_path": str(history_path),
        "event_log_path": str(event_path),
    }
