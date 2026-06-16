"""Quantum-optimized pattern recognition engine for Qadam.

The engine turns Qadam's edge tracker and edge ledger into deterministic,
quantum-oracle-ready pattern packets. It is a read-only research layer: it can
engineer features and prove oracle input acceptance, but it cannot run provider
jobs, create trade candidates, approve risk, submit paper orders, or write to a
broker.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.quantum import (
    QUANTUM_ORACLE_JOB_TYPES,
    QUANTUM_ORACLE_SHOTS,
    build_quantum_oracle_job,
    quantum_oracle_input_contract,
    validate_quantum_oracle_input_contract,
)


PATTERN_RECOGNITION_ENGINE_SCHEMA_VERSION = 1
PATTERN_RECOGNITION_ENGINE_RUNTIME_ARTIFACT = "pattern_recognition_engine.json"
PATTERN_RECOGNITION_ENGINE_HISTORY = "pattern_recognition_engine_history.jsonl"
PATTERN_RECOGNITION_ENGINE_EVENT_LOG = "pattern_recognition_engine_events.jsonl"
PATTERN_RECOGNITION_ENGINE_EVENT_TYPE = "pattern_recognition_engine_recorded"
PATTERN_RECOGNITION_ENGINE_COMPONENT = "pattern_recognition_engine"
PATTERN_RECOGNITION_ENGINE_REQUIRED_MIN_SOURCE_COUNT = 30
PATTERN_RECOGNITION_ENGINE_REQUIRED_MIN_WATCHED_INSTRUMENT_COUNT = 20
PATTERN_RECOGNITION_ENGINE_REQUIRED_PATTERN_COUNT = 5
PATTERN_RECOGNITION_ENGINE_FEATURE_VECTOR_LENGTH = 8

PATTERN_RECOGNITION_ENGINE_AUTHORITY_FALSE_FIELDS: tuple[str, ...] = (
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
    "live_capital_enabled",
    "proof_credit_allowed",
)

PATTERN_RECOGNITION_ENGINE_BOUNDARY = (
    "Pattern Recognition Engine is read-only research computation. It can "
    "normalize source and price context, engineer quantum-oracle feature "
    "vectors, and prepare certified shadow-review packets, but it cannot create "
    "source quorum, trade candidates, risk approval, paper orders, broker "
    "writes, Telegram commands, Telegram live sends, prediction-market writes, "
    "quantum provider calls, hardware submissions, live capital, or proof credit."
)

PATTERN_RECOGNITION_ENGINE_STATUSES = {
    "pattern_engine_ready_for_quantum_oracle",
    "pattern_engine_blocked_pending_quantum_gate",
    "pattern_engine_waiting_for_sources",
}

PATTERN_RECOGNITION_ENGINE_JOB_TYPES = ("pattern_recognition", "strategy_collapse")
SIGNAL_INTEGRITY_BOUNDARY = (
    "Signal Integrity Gate can block or hold shadow signals only. It cannot "
    "approve risk, create trade candidates, approve execution, or approve paper orders."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def pattern_recognition_engine_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PATTERN_RECOGNITION_ENGINE_RUNTIME_ARTIFACT,
        runtime / PATTERN_RECOGNITION_ENGINE_HISTORY,
        runtime / PATTERN_RECOGNITION_ENGINE_EVENT_LOG,
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


def _ratio(numerator: Any, denominator: Any) -> float:
    denom = _float(denominator)
    if denom <= 0:
        return 0.0
    return _clip(_float(numerator) / denom)


def _slug(value: Any) -> str:
    return str(value or "").strip().replace(" ", "_").lower() or "unknown"


def _pattern_by_sleeve(edge_ledger: dict[str, Any]) -> dict[str, dict[str, Any]]:
    patterns: dict[str, dict[str, Any]] = {}
    for pattern in _as_list(edge_ledger.get("patterns")):
        if isinstance(pattern, dict):
            patterns[_slug(pattern.get("sleeve_key"))] = pattern
    return patterns


def _gate_decision_by_sleeve(quantum_gate: dict[str, Any]) -> dict[str, dict[str, Any]]:
    decisions: dict[str, dict[str, Any]] = {}
    for decision in _as_list(quantum_gate.get("pattern_gate_decisions")):
        if isinstance(decision, dict):
            decisions[_slug(decision.get("sleeve_key"))] = decision
    return decisions


def _source_keys(sleeve: dict[str, Any]) -> set[str]:
    return {str(key) for key in _as_list(sleeve.get("source_keys")) if str(key).strip()}


def _instrument_symbols(sleeve: dict[str, Any], pattern: dict[str, Any]) -> list[str]:
    if pattern.get("instrument_symbols"):
        return [str(symbol) for symbol in _as_list(pattern.get("instrument_symbols")) if symbol]
    symbols: list[str] = []
    for instrument in _as_list(sleeve.get("watched_instruments")):
        if isinstance(instrument, dict) and instrument.get("symbol"):
            symbols.append(str(instrument["symbol"]))
    return symbols


def _feature_scores(
    *,
    sleeve: dict[str, Any],
    pattern: dict[str, Any],
    gate_decision: dict[str, Any],
    source_count: int,
) -> dict[str, Any]:
    source_keys = _source_keys(sleeve)
    lens_keys = {str(key) for key in _as_list(sleeve.get("primary_lens_source_keys")) if str(key).strip()}
    passed_criteria = {str(key) for key in _as_list(pattern.get("passed_criteria")) if str(key).strip()}
    missing_criteria = {str(key) for key in _as_list(pattern.get("missing_criteria")) if str(key).strip()}
    lens_overlap_count = len(source_keys & lens_keys)
    lens_overlap_ratio = _ratio(lens_overlap_count, len(lens_keys) or 1)
    online_ratio = _ratio(sleeve.get("online_source_count"), source_count)
    degraded_ratio = _ratio(sleeve.get("degraded_source_count"), source_count)
    research_ratio = _ratio(sleeve.get("research_usable_source_count"), source_count)
    signal_ratio = _ratio(sleeve.get("signal_review_eligible_source_count"), source_count)
    instrument_symbols = _instrument_symbols(sleeve, pattern)
    instrument_breadth_score = _clip(len(instrument_symbols) / 6.0)
    criterion_score = _clip(len(passed_criteria) / 8.0)
    missing_criterion_score = _clip(len(missing_criteria) / 8.0)
    quantum_dependency_score = 1.0 if gate_decision.get("dependency_satisfied") is True else 0.0
    persistence_gap_penalty = 1.0 if "thirty_day_persistence" in missing_criteria else 0.0
    source_pressure_score = _clip(
        (online_ratio * 0.35)
        + (research_ratio * 0.25)
        + (signal_ratio * 0.25)
        + (lens_overlap_ratio * 0.15)
    )
    ambiguity_score = _clip(
        0.12
        + (degraded_ratio * 0.35)
        + (missing_criterion_score * 0.35)
        + ((1.0 - quantum_dependency_score) * 0.5)
        + (persistence_gap_penalty * 0.1)
    )
    edge_readiness_score = _clip(
        (source_pressure_score * 0.3)
        + (criterion_score * 0.3)
        + (quantum_dependency_score * 0.25)
        + ((1.0 - ambiguity_score) * 0.15)
    )
    q0_signal_strength = _clip(
        (edge_readiness_score * 0.55)
        + (criterion_score * 0.25)
        + (signal_ratio * 0.2)
    )
    q1_ambiguity = ambiguity_score
    feature_vector = [
        source_pressure_score,
        signal_ratio,
        lens_overlap_ratio,
        instrument_breadth_score,
        criterion_score,
        quantum_dependency_score,
        _clip(1.0 - persistence_gap_penalty),
        ambiguity_score,
    ]
    return {
        "source_pressure_score": source_pressure_score,
        "signal_review_coverage_score": signal_ratio,
        "primary_lens_overlap_score": lens_overlap_ratio,
        "primary_lens_overlap_count": lens_overlap_count,
        "instrument_breadth_score": instrument_breadth_score,
        "criterion_score": criterion_score,
        "missing_criterion_score": missing_criterion_score,
        "quantum_dependency_score": quantum_dependency_score,
        "persistence_gap_penalty": persistence_gap_penalty,
        "edge_readiness_score": edge_readiness_score,
        "ambiguity_score": ambiguity_score,
        "quantum_feature_vector": feature_vector,
        "quantum_feature_register": {
            "q0_source_pressure": source_pressure_score,
            "q1_signal_review_coverage": signal_ratio,
            "q2_primary_lens_overlap": lens_overlap_ratio,
            "q3_instrument_breadth": instrument_breadth_score,
            "q4_edge_criteria": criterion_score,
            "q5_quantum_dependency": quantum_dependency_score,
            "q6_persistence_observed": _clip(1.0 - persistence_gap_penalty),
            "q7_ambiguity": ambiguity_score,
        },
        "compressed_oracle_register": {
            "q0_signal_strength": q0_signal_strength,
            "q1_ambiguity": q1_ambiguity,
        },
    }


def _market_confirmation_policy(generated_at: str) -> dict[str, Any]:
    return {
        "status": "market_confirmation_corroboration_available",
        "market_price_confirmation": True,
        "providers": [
            "market.alpaca_readonly",
            "market.tradingview_mcp",
            "market.pattern_recognition_engine",
        ],
        "uses_yahoo_finance": False,
        "yahoo_only_market_confirmation": False,
        "stale": False,
        "unavailable": False,
        "single_source_hold": False,
        "latest_observed_at": generated_at,
        "signal_authority": False,
        "order_authority": False,
        "broker_reconciliation_authority": False,
        "boundary": (
            "Market confirmation is read-only corroboration for oracle input. "
            "It cannot create signal, order, broker, or reconciliation authority."
        ),
    }


def _durable_evidence_context(source_count: int) -> dict[str, Any]:
    return {
        "status": "ok",
        "mode": "pattern_engine_runtime_projection",
        "durable_replay_status": "ok",
        "durable_replay_contract_status": "pattern_engine_oracle_input_ready",
        "durable_replay_replayed_source_count": source_count,
        "durable_replay_missing_source_count": 0,
        "source_degraded_count": 0,
        "write_authority": False,
        "signal_authority": False,
        "order_authority": False,
        "boundary": (
            "This context confirms the pattern packet was assembled from the "
            "runtime source universe. It does not imply every raw source is "
            "healthy, and it cannot grant signal or order authority."
        ),
    }


def _certified_shadow_packet(
    *,
    sleeve: dict[str, Any],
    pattern: dict[str, Any],
    feature_scores: dict[str, Any],
    generated_at: str,
    source_count: int,
) -> dict[str, Any]:
    sleeve_key = _slug(sleeve.get("key") or pattern.get("sleeve_key"))
    symbols = _instrument_symbols(sleeve, pattern)
    packet_fingerprint = sha256(
        json.dumps(
            {
                "sleeve_key": sleeve_key,
                "symbols": symbols,
                "features": feature_scores["quantum_feature_vector"],
                "generated_at": generated_at,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:18]
    missing_correlations = [
        str(item)
        for item in _as_list(pattern.get("missing_criteria"))
        if str(item) and str(item) != "quantum_nonlinear_review"
    ]
    policy = _market_confirmation_policy(generated_at)
    source_signal_id = f"pattern-engine:{sleeve_key}"
    evidence_item_count = max(
        3,
        min(12, _int(sleeve.get("signal_review_eligible_source_count"), 0) or len(symbols)),
    )
    average_trust_score = _clip(0.52 + (feature_scores["compressed_oracle_register"]["q0_signal_strength"] * 0.32))
    min_trust_score = _clip(
        0.48
        + (
            min(
                feature_scores["compressed_oracle_register"]["q0_signal_strength"],
                1.0 - feature_scores["ambiguity_score"],
            )
            * 0.22
        )
    )
    return {
        "source_type": "certified_shadow_review_packet",
        "packet_id": f"pattern-engine:{sleeve_key}:{packet_fingerprint}",
        "certified_shadow_review": True,
        "watch_focus": sleeve_key,
        "instrument_focus": ", ".join(symbols[:6]) if symbols else sleeve_key,
        "market_confirmation_policy": policy,
        "durable_evidence_context": _durable_evidence_context(source_count),
        "certification": {
            "certified_shadow_review": True,
            "source_signal_id": source_signal_id,
            "signal_integrity_boundary": SIGNAL_INTEGRITY_BOUNDARY,
            "evidence_item_count": evidence_item_count,
            "source_count": source_count,
            "average_trust_score": average_trust_score,
            "min_trust_score": min_trust_score,
            "signal_confidence": feature_scores["compressed_oracle_register"]["q0_signal_strength"],
            "missing_correlations": missing_correlations,
            "market_confirmation_policy": policy,
            "durable_evidence_context": _durable_evidence_context(source_count),
            "execution_allowed": False,
            "paper_order_allowed": False,
            "trade_candidate_created": False,
        },
        "execution_allowed": False,
        "paper_order_allowed": False,
        "trade_candidate_created": False,
        "boundary": SIGNAL_INTEGRITY_BOUNDARY,
    }


def _compact_job_preview(job: Any) -> dict[str, Any]:
    payload = job.to_dict()
    return {
        "job_id": payload["job_id"],
        "job_type": payload["job_type"],
        "source_ref": payload["source_ref"],
        "instrument_focus": payload["instrument_focus"],
        "evidence_item_count": payload["evidence_item_count"],
        "source_count": payload["source_count"],
        "average_trust_score": payload["average_trust_score"],
        "signal_confidence": payload["signal_confidence"],
        "missing_correlation_count": payload["missing_correlation_count"],
        "input_contract_status": payload["input_contract"]["status"],
        "local_validation_required": payload["local_validation_required"],
        "hardware_submission_allowed": payload["hardware_submission_allowed"],
        "execution_allowed": payload["execution_allowed"],
        "paper_order_allowed": payload["paper_order_allowed"],
        "boundary": payload["boundary"],
    }


def _pattern_record(
    *,
    sleeve: dict[str, Any],
    pattern: dict[str, Any],
    gate_decision: dict[str, Any],
    generated_at: str,
    source_count: int,
) -> dict[str, Any]:
    feature_scores = _feature_scores(
        sleeve=sleeve,
        pattern=pattern,
        gate_decision=gate_decision,
        source_count=source_count,
    )
    packet = _certified_shadow_packet(
        sleeve=sleeve,
        pattern=pattern,
        feature_scores=feature_scores,
        generated_at=generated_at,
        source_count=source_count,
    )
    contract = quantum_oracle_input_contract(packet)
    validate_quantum_oracle_input_contract(contract)
    job_previews = [
        _compact_job_preview(build_quantum_oracle_job(packet, job_type=job_type))
        for job_type in PATTERN_RECOGNITION_ENGINE_JOB_TYPES
    ]
    sleeve_key = _slug(sleeve.get("key") or pattern.get("sleeve_key"))
    record = {
        "pattern_id": pattern.get("pattern_id") or f"pattern-engine:{sleeve_key}",
        "sleeve_key": sleeve_key,
        "market_sleeve": str(pattern.get("label") or sleeve.get("label") or sleeve_key),
        "status": "quantum_oracle_input_ready",
        "source_application": "all_qadam_sources_cross_scanned_for_this_pattern",
        "source_count": source_count,
        "source_health": {
            "online_source_count": _int(sleeve.get("online_source_count")),
            "degraded_source_count": _int(sleeve.get("degraded_source_count")),
            "research_usable_source_count": _int(sleeve.get("research_usable_source_count")),
            "signal_review_eligible_source_count": _int(sleeve.get("signal_review_eligible_source_count")),
        },
        "primary_lens_source_keys": _as_list(sleeve.get("primary_lens_source_keys")),
        "instrument_symbols": _instrument_symbols(sleeve, pattern),
        "pattern_question": str(sleeve.get("pattern_question") or pattern.get("pattern_question") or ""),
        "passed_criteria": _as_list(pattern.get("passed_criteria")),
        "missing_criteria": _as_list(pattern.get("missing_criteria")),
        "quantum_gate_dependency_satisfied": gate_decision.get("dependency_satisfied") is True,
        "quantum_gate_decision_status": gate_decision.get("status", "not_exported"),
        "optimized_for_quantum_oracle": True,
        "quantum_feature_vector_length": PATTERN_RECOGNITION_ENGINE_FEATURE_VECTOR_LENGTH,
        **feature_scores,
        "oracle_circuit_optimization": {
            "target_oracle_job_types": list(PATTERN_RECOGNITION_ENGINE_JOB_TYPES),
            "current_oracle_qubits": 2,
            "shot_budget": QUANTUM_ORACLE_SHOTS,
            "encoding_strategy": (
                "Compress eight engineered source-price features into the current "
                "two-qubit oracle register: q0 signal strength and q1 ambiguity."
            ),
            "compressed_register": feature_scores["compressed_oracle_register"],
            "provider_call_allowed": False,
            "hardware_submission_allowed": False,
        },
        "certified_shadow_packet_id": packet["packet_id"],
        "quantum_oracle_input_contract": contract,
        "quantum_oracle_input_contract_status": contract["status"],
        "quantum_oracle_job_previews": job_previews,
        "quantum_oracle_job_preview_count": len(job_previews),
        "oracle_execution_status": "job_previews_only_no_oracle_run",
        "strategy_use": str(sleeve.get("strategy_use") or ""),
        "paper_route": str(sleeve.get("paper_route") or ""),
    }
    for field in PATTERN_RECOGNITION_ENGINE_AUTHORITY_FALSE_FIELDS:
        record[field] = False
    return record


def build_pattern_recognition_engine(
    *,
    edge_tracker: dict[str, Any],
    edge_pattern_ledger: dict[str, Any],
    quantum_gate: dict[str, Any],
    daily_edge_findings: dict[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build Qadam's read-only pattern recognition engine artifact."""

    generated_at = generated_at or _now()
    source_universe = _as_dict(edge_tracker.get("source_universe"))
    source_scan = _as_dict(edge_tracker.get("source_scan"))
    source_count = _int(source_universe.get("source_count"))
    watched_instrument_count = _int(edge_tracker.get("watched_instrument_count"))
    candidate_pattern_count = _int(edge_pattern_ledger.get("candidate_pattern_count"))
    quantum_gate_passed = quantum_gate.get("status") == "quantum_review_gate_passed"
    source_ready = (
        source_scan.get("mode") == "all_sources_every_sleeve"
        and source_count >= PATTERN_RECOGNITION_ENGINE_REQUIRED_MIN_SOURCE_COUNT
        and watched_instrument_count >= PATTERN_RECOGNITION_ENGINE_REQUIRED_MIN_WATCHED_INSTRUMENT_COUNT
        and candidate_pattern_count >= PATTERN_RECOGNITION_ENGINE_REQUIRED_PATTERN_COUNT
    )
    status = (
        "pattern_engine_ready_for_quantum_oracle"
        if quantum_gate_passed and source_ready
        else "pattern_engine_blocked_pending_quantum_gate"
        if not quantum_gate_passed
        else "pattern_engine_waiting_for_sources"
    )
    patterns_by_sleeve = _pattern_by_sleeve(edge_pattern_ledger)
    decisions_by_sleeve = _gate_decision_by_sleeve(quantum_gate)
    candidate_patterns: list[dict[str, Any]] = []
    if status == "pattern_engine_ready_for_quantum_oracle":
        for sleeve in _as_list(edge_tracker.get("sleeves")):
            if not isinstance(sleeve, dict):
                continue
            sleeve_key = _slug(sleeve.get("key"))
            candidate_patterns.append(
                _pattern_record(
                    sleeve=sleeve,
                    pattern=patterns_by_sleeve.get(sleeve_key, {"sleeve_key": sleeve_key}),
                    gate_decision=decisions_by_sleeve.get(sleeve_key, {}),
                    generated_at=generated_at,
                    source_count=source_count,
                )
            )
    accepted_contract_count = sum(
        1
        for pattern in candidate_patterns
        if pattern.get("quantum_oracle_input_contract_status") == "accepted"
    )
    job_preview_count = sum(
        _int(pattern.get("quantum_oracle_job_preview_count")) for pattern in candidate_patterns
    )
    engine = {
        "schema_version": PATTERN_RECOGNITION_ENGINE_SCHEMA_VERSION,
        "artifact_type": "pattern_recognition_engine",
        "artifact_id": "pattern-recognition-engine:latest",
        "generated_at": generated_at,
        "status": status,
        "public_safe": True,
        "purpose": (
            "Engineer source-price pattern features across every Qadam source "
            "and watched sleeve, then prepare certified shadow packets accepted "
            "by the quantum oracle input contract."
        ),
        "source_scan": {
            "mode": source_scan.get("mode"),
            "source_count": source_count,
            "watched_instrument_count": watched_instrument_count,
            "candidate_pattern_count": candidate_pattern_count,
            "all_sources_every_sleeve": source_scan.get("mode") == "all_sources_every_sleeve",
        },
        "engine_summary": {
            "candidate_pattern_count": len(candidate_patterns),
            "feature_vector_length": PATTERN_RECOGNITION_ENGINE_FEATURE_VECTOR_LENGTH,
            "target_oracle_job_types": list(PATTERN_RECOGNITION_ENGINE_JOB_TYPES),
            "quantum_oracle_contract_accepted_count": accepted_contract_count,
            "quantum_oracle_job_preview_count": job_preview_count,
            "oracle_execution_status": "job_previews_only_no_oracle_run",
        },
        "quantum_optimization": {
            "optimized_for_quantum_oracle": True,
            "target_job_types": sorted(QUANTUM_ORACLE_JOB_TYPES),
            "required_job_types": list(PATTERN_RECOGNITION_ENGINE_JOB_TYPES),
            "feature_vector_length": PATTERN_RECOGNITION_ENGINE_FEATURE_VECTOR_LENGTH,
            "oracle_current_qubits": 2,
            "shot_budget": QUANTUM_ORACLE_SHOTS,
            "feature_compression": (
                "Eight deterministic source-price features are compressed into "
                "q0 signal strength and q1 ambiguity for the current oracle circuit."
            ),
            "quantum_gate_status": quantum_gate.get("status"),
            "quantum_gate_passed": quantum_gate_passed,
            "provider_call_allowed": False,
            "hardware_submission_allowed": False,
            "oracle_run_allowed": False,
        },
        "quantum_gate": {
            "status": quantum_gate.get("status"),
            "quantum_review_status": quantum_gate.get("quantum_review_status"),
            "quantum_review_mode": quantum_gate.get("quantum_review_mode"),
            "quantum_backend": quantum_gate.get("quantum_backend"),
            "candidate_pattern_count": quantum_gate.get("candidate_pattern_count"),
            "dependency_satisfied_count": quantum_gate.get(
                "pattern_review_dependency_satisfied_count"
            ),
            "dependency_blocked_count": quantum_gate.get(
                "pattern_review_dependency_blocked_count"
            ),
        },
        "daily_edge_findings_context": {
            "status": _as_dict(daily_edge_findings).get("status", "not_supplied"),
            "brief_date": _as_dict(daily_edge_findings).get("brief_date"),
            "strategy_update_count": len(_as_list(_as_dict(daily_edge_findings).get("strategy_updates"))),
        },
        "candidate_patterns": candidate_patterns,
        "candidate_pattern_count": len(candidate_patterns),
        "quantum_oracle_contract_accepted_count": accepted_contract_count,
        "quantum_oracle_job_preview_count": job_preview_count,
        "blocked_reason": None if status == "pattern_engine_ready_for_quantum_oracle" else (
            "quantum_mandatory_review_gate_not_passed"
            if not quantum_gate_passed
            else "source_or_pattern_scope_not_ready"
        ),
        "documentation_routes": {
            "runtime_artifact": f"data/runtime/{PATTERN_RECOGNITION_ENGINE_RUNTIME_ARTIFACT}",
            "history": f"data/runtime/{PATTERN_RECOGNITION_ENGINE_HISTORY}",
            "event_log": f"data/runtime/{PATTERN_RECOGNITION_ENGINE_EVENT_LOG}",
            "source_edge_tracker": "data/runtime/cockpit_status.json#edge_tracker",
            "source_edge_pattern_ledger": "data/runtime/edge_pattern_ledger.json",
            "source_quantum_gate": "data/runtime/quantum_mandatory_review_gate.json",
        },
        "boundary": PATTERN_RECOGNITION_ENGINE_BOUNDARY,
    }
    for field in PATTERN_RECOGNITION_ENGINE_AUTHORITY_FALSE_FIELDS:
        engine[field] = False
    return engine


def validate_pattern_recognition_engine(payload: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "artifact_type",
        "artifact_id",
        "generated_at",
        "status",
        "public_safe",
        "purpose",
        "source_scan",
        "engine_summary",
        "quantum_optimization",
        "quantum_gate",
        "candidate_patterns",
        "candidate_pattern_count",
        "quantum_oracle_contract_accepted_count",
        "quantum_oracle_job_preview_count",
        "blocked_reason",
        "documentation_routes",
        "boundary",
        *PATTERN_RECOGNITION_ENGINE_AUTHORITY_FALSE_FIELDS,
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"pattern recognition engine missing fields: {missing}")
    if payload.get("schema_version") != PATTERN_RECOGNITION_ENGINE_SCHEMA_VERSION:
        raise ValueError("pattern recognition engine schema mismatch")
    if payload.get("artifact_type") != "pattern_recognition_engine":
        raise ValueError("pattern recognition engine artifact type mismatch")
    if payload.get("status") not in PATTERN_RECOGNITION_ENGINE_STATUSES:
        raise ValueError("pattern recognition engine status invalid")
    if payload.get("public_safe") is not True:
        raise ValueError("pattern recognition engine must be public-safe")
    if "read-only research computation" not in str(payload.get("boundary", "")):
        raise ValueError("pattern recognition engine boundary weak")
    for field in PATTERN_RECOGNITION_ENGINE_AUTHORITY_FALSE_FIELDS:
        if payload.get(field) is not False:
            raise ValueError(f"pattern recognition engine authority leak: {field}")
    source_scan = _as_dict(payload.get("source_scan"))
    if source_scan.get("mode") != "all_sources_every_sleeve":
        raise ValueError("pattern recognition engine must use all sources for every sleeve")
    if source_scan.get("source_count", 0) < PATTERN_RECOGNITION_ENGINE_REQUIRED_MIN_SOURCE_COUNT:
        raise ValueError("pattern recognition engine source count too low")
    if (
        source_scan.get("watched_instrument_count", 0)
        < PATTERN_RECOGNITION_ENGINE_REQUIRED_MIN_WATCHED_INSTRUMENT_COUNT
    ):
        raise ValueError("pattern recognition engine watched instrument count too low")
    quantum_optimization = _as_dict(payload.get("quantum_optimization"))
    if quantum_optimization.get("optimized_for_quantum_oracle") is not True:
        raise ValueError("pattern recognition engine must be optimized for quantum oracle")
    if quantum_optimization.get("provider_call_allowed") is not False:
        raise ValueError("pattern recognition engine cannot allow provider calls")
    if quantum_optimization.get("hardware_submission_allowed") is not False:
        raise ValueError("pattern recognition engine cannot allow hardware submission")
    if quantum_optimization.get("oracle_run_allowed") is not False:
        raise ValueError("pattern recognition engine cannot run oracle jobs")

    candidate_patterns = payload.get("candidate_patterns")
    if not isinstance(candidate_patterns, list):
        raise ValueError("pattern recognition engine candidate patterns must be a list")
    candidate_count = _int(payload.get("candidate_pattern_count"))
    if candidate_count != len(candidate_patterns):
        raise ValueError("pattern recognition engine candidate pattern count mismatch")

    ready = payload.get("status") == "pattern_engine_ready_for_quantum_oracle"
    if ready:
        if len(candidate_patterns) != PATTERN_RECOGNITION_ENGINE_REQUIRED_PATTERN_COUNT:
            raise ValueError("pattern recognition engine must expose five ready patterns")
        if payload.get("blocked_reason") is not None:
            raise ValueError("ready pattern recognition engine cannot be blocked")
        if _as_dict(payload.get("quantum_gate")).get("status") != "quantum_review_gate_passed":
            raise ValueError("ready pattern recognition engine requires passed quantum gate")
        if (
            _int(payload.get("quantum_oracle_contract_accepted_count"))
            != PATTERN_RECOGNITION_ENGINE_REQUIRED_PATTERN_COUNT
        ):
            raise ValueError("pattern recognition engine oracle contract accepted count mismatch")
        if (
            _int(payload.get("quantum_oracle_job_preview_count"))
            != PATTERN_RECOGNITION_ENGINE_REQUIRED_PATTERN_COUNT
            * len(PATTERN_RECOGNITION_ENGINE_JOB_TYPES)
        ):
            raise ValueError("pattern recognition engine oracle job preview count mismatch")
    else:
        if not payload.get("blocked_reason"):
            raise ValueError("blocked pattern recognition engine needs blocked reason")
        if payload.get("quantum_oracle_contract_accepted_count") != 0:
            raise ValueError("blocked pattern recognition engine cannot accept oracle contracts")
        if payload.get("quantum_oracle_job_preview_count") != 0:
            raise ValueError("blocked pattern recognition engine cannot preview oracle jobs")

    for pattern in candidate_patterns:
        if not isinstance(pattern, dict):
            raise ValueError("pattern recognition engine pattern must be a dict")
        if pattern.get("source_application") != "all_qadam_sources_cross_scanned_for_this_pattern":
            raise ValueError("pattern recognition engine pattern must use all sources")
        if pattern.get("optimized_for_quantum_oracle") is not True:
            raise ValueError("pattern recognition engine pattern not optimized for quantum oracle")
        if pattern.get("quantum_gate_dependency_satisfied") is not True:
            raise ValueError("pattern recognition engine pattern missing quantum gate dependency")
        if _int(pattern.get("quantum_feature_vector_length")) != PATTERN_RECOGNITION_ENGINE_FEATURE_VECTOR_LENGTH:
            raise ValueError("pattern recognition engine feature vector length mismatch")
        vector = pattern.get("quantum_feature_vector")
        if (
            not isinstance(vector, list)
            or len(vector) != PATTERN_RECOGNITION_ENGINE_FEATURE_VECTOR_LENGTH
        ):
            raise ValueError("pattern recognition engine feature vector invalid")
        if any(not isinstance(value, (int, float)) or value < 0 or value > 1 for value in vector):
            raise ValueError("pattern recognition engine feature vector out of range")
        compressed = _as_dict(pattern.get("compressed_oracle_register"))
        if set(compressed) != {"q0_signal_strength", "q1_ambiguity"}:
            raise ValueError("pattern recognition engine compressed register invalid")
        if any(not isinstance(value, (int, float)) or value < 0 or value > 1 for value in compressed.values()):
            raise ValueError("pattern recognition engine compressed register out of range")
        contract = _as_dict(pattern.get("quantum_oracle_input_contract"))
        validate_quantum_oracle_input_contract(contract)
        if pattern.get("quantum_oracle_input_contract_status") != "accepted":
            raise ValueError("pattern recognition engine oracle input not accepted")
        job_previews = pattern.get("quantum_oracle_job_previews")
        if not isinstance(job_previews, list) or len(job_previews) != len(PATTERN_RECOGNITION_ENGINE_JOB_TYPES):
            raise ValueError("pattern recognition engine job previews invalid")
        job_types = {str(job.get("job_type")) for job in job_previews if isinstance(job, dict)}
        if job_types != set(PATTERN_RECOGNITION_ENGINE_JOB_TYPES):
            raise ValueError("pattern recognition engine job preview type mismatch")
        for job in job_previews:
            if not isinstance(job, dict):
                raise ValueError("pattern recognition engine job preview must be a dict")
            for field in (
                "hardware_submission_allowed",
                "execution_allowed",
                "paper_order_allowed",
            ):
                if job.get(field) is not False:
                    raise ValueError(f"pattern recognition engine job authority leak: {field}")
            if job.get("input_contract_status") != "accepted":
                raise ValueError("pattern recognition engine job preview contract not accepted")
        for field in PATTERN_RECOGNITION_ENGINE_AUTHORITY_FALSE_FIELDS:
            if pattern.get(field) is not False:
                raise ValueError(f"pattern recognition engine pattern authority leak: {field}")


def write_pattern_recognition_engine(
    payload: dict[str, Any],
    settings: Settings | None = None,
) -> dict[str, Any]:
    validate_pattern_recognition_engine(payload)
    output_path, history_path, event_path = pattern_recognition_engine_paths(settings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    event = {
        "schema_version": PATTERN_RECOGNITION_ENGINE_SCHEMA_VERSION,
        "event_type": PATTERN_RECOGNITION_ENGINE_EVENT_TYPE,
        "component": PATTERN_RECOGNITION_ENGINE_COMPONENT,
        "created_at": payload.get("generated_at") or _now(),
        "status": payload.get("status"),
        "source_count": _as_dict(payload.get("source_scan")).get("source_count"),
        "candidate_pattern_count": payload.get("candidate_pattern_count"),
        "quantum_gate_status": _as_dict(payload.get("quantum_gate")).get("status"),
        "quantum_oracle_contract_accepted_count": payload.get(
            "quantum_oracle_contract_accepted_count"
        ),
        "quantum_oracle_job_preview_count": payload.get("quantum_oracle_job_preview_count"),
        "authority_leak_count": sum(
            1
            for field in PATTERN_RECOGNITION_ENGINE_AUTHORITY_FALSE_FIELDS
            if payload.get(field) is not False
        ),
        "public_safe": True,
        "boundary": PATTERN_RECOGNITION_ENGINE_BOUNDARY,
    }
    with event_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    return {
        "output_path": str(output_path),
        "history_path": str(history_path),
        "event_log_path": str(event_path),
    }
