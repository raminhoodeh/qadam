"""Read-only hypothesis lifecycle for Qadam.

The lifecycle layer deduplicates shadow hypotheses into durable hypothesis
threads and records whether each one is held, retained, or ready for further
review. It is research documentation only: it cannot promote a hypothesis into
a trade candidate, override Signal Integrity, apply refutations, mutate
strategy, size orders, or submit paper trades.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.edge_memory_ledger import validate_edge_memory_ledger
from orchestrator.strategy_update_record import (
    STRATEGY_UPDATE_RECORD_AUTHORITY_FALSE_FIELDS,
    validate_strategy_update_record,
)


HYPOTHESIS_LIFECYCLE_SCHEMA_VERSION = 1
HYPOTHESIS_LIFECYCLE_RUNTIME_ARTIFACT = "hypothesis_lifecycle.json"
HYPOTHESIS_LIFECYCLE_HISTORY = "hypothesis_lifecycle_history.jsonl"
HYPOTHESIS_LIFECYCLE_EVENT_LOG = "hypothesis_lifecycle_events.jsonl"
HYPOTHESIS_LIFECYCLE_EVENT_TYPE = "hypothesis_lifecycle_recorded"
HYPOTHESIS_LIFECYCLE_COMPONENT = "hypothesis_lifecycle"

HYPOTHESIS_LIFECYCLE_AUTHORITY_FALSE_FIELDS: tuple[str, ...] = tuple(
    dict.fromkeys(
        (
            *STRATEGY_UPDATE_RECORD_AUTHORITY_FALSE_FIELDS,
            "hypothesis_mutation_allowed",
            "hypothesis_promotion_allowed",
            "hypothesis_refutation_applied",
            "hypothesis_retention_applied",
            "candidate_promotion_allowed",
            "signal_integrity_override_allowed",
            "evidence_requirement_override_allowed",
            "lifecycle_transition_applied",
        )
    )
)

HYPOTHESIS_LIFECYCLE_BOUNDARY = (
    "Hypothesis Lifecycle is read-only research documentation. It can "
    "deduplicate shadow hypotheses, remember lifecycle dates, document whether "
    "a hypothesis is held, retained, or ready for further review, and connect "
    "it to edge memory plus quantum-reviewed strategy records, but it cannot "
    "mutate hypotheses, promote candidates, override Signal Integrity, apply "
    "refutations or retentions, create source quorum, approve risk, size "
    "orders, submit paper orders, write to brokers, send live Telegram "
    "commands, call quantum providers, enable live capital, or grant proof "
    "credit."
)

HYPOTHESIS_LIFECYCLE_STATUSES = {
    "hypothesis_lifecycle_active",
    "hypothesis_lifecycle_waiting_for_hypotheses",
    "hypothesis_lifecycle_blocked_pending_strategy_update_record",
}

HYPOTHESIS_LIFECYCLE_STATES = {
    "held_for_independent_corroboration",
    "held_for_quantum_or_edge_mapping",
    "ready_for_signal_integrity_review",
    "retained_for_shadow_review",
    "refutation_candidate_not_applied",
    "blocked_source_execution_authority_present",
}

SLEEVE_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("oil", ("oil", "crude", "energy", "transport", "shipping", "hormuz")),
    ("silver", ("silver", "safe haven", "real rates", "slv", "xag")),
    ("semiconductors", ("semiconductor", "chip", "chips", "taiwan", "nvidia", "asml")),
    ("prediction_markets", ("prediction", "probability", "polymarket", "kalshi")),
    ("defence", ("defence", "defense", "aerospace", "missile", "drone", "lockheed")),
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def hypothesis_lifecycle_paths(settings: Settings | None = None) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / HYPOTHESIS_LIFECYCLE_RUNTIME_ARTIFACT,
        runtime / HYPOTHESIS_LIFECYCLE_HISTORY,
        runtime / HYPOTHESIS_LIFECYCLE_EVENT_LOG,
    )


def read_hypothesis_lifecycle(settings: Settings | None = None) -> dict[str, Any]:
    output_path, _, _ = hypothesis_lifecycle_paths(settings)
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


def _normalize_text(value: Any) -> str:
    text = str(value or "").lower()
    text = re.sub(r"\b[0-9a-f]{8,}\b", " ", text)
    text = re.sub(r"[^a-z0-9:=./ _-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:320]


def _slug(value: Any) -> str:
    return str(value or "").strip().replace(" ", "_").lower() or "unknown"


def _hypothesis_key(hypothesis: dict[str, Any]) -> str:
    raw = {
        "instrument_focus": _normalize_text(hypothesis.get("instrument_focus")),
        "title": _normalize_text(hypothesis.get("title")),
        "thesis": _normalize_text(hypothesis.get("thesis")),
    }
    return sha256(json.dumps(raw, sort_keys=True).encode("utf-8")).hexdigest()[:18]


def _sleeve_for_hypothesis(hypothesis: dict[str, Any]) -> str:
    haystack = " ".join(
        _normalize_text(hypothesis.get(key))
        for key in ("instrument_focus", "title", "thesis")
    )
    for sleeve_key, needles in SLEEVE_PATTERNS:
        if any(needle in haystack for needle in needles):
            return sleeve_key
    return "unknown"


def _group_hypotheses(hypotheses: list[Any]) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for hypothesis in hypotheses:
        if not isinstance(hypothesis, dict):
            continue
        key = _hypothesis_key(hypothesis)
        group = groups.setdefault(
            key,
            {
                "hypothesis_key": key,
                "hypotheses": [],
                "sleeve_key": _sleeve_for_hypothesis(hypothesis),
            },
        )
        group["hypotheses"].append(hypothesis)
        if group["sleeve_key"] == "unknown":
            group["sleeve_key"] = _sleeve_for_hypothesis(hypothesis)
    return [groups[key] for key in sorted(groups)]


def _previous_threads_by_key(previous_lifecycle: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    threads: dict[str, dict[str, Any]] = {}
    for thread in _as_list(_as_dict(previous_lifecycle).get("hypothesis_threads")):
        if isinstance(thread, dict):
            threads[str(thread.get("hypothesis_key") or "")] = thread
    return {key: value for key, value in threads.items() if key}


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


def _records_by_sleeve(records: list[Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for record in records:
        if isinstance(record, dict):
            result[_slug(record.get("sleeve_key"))] = record
    return result


def _union_list(hypotheses: list[dict[str, Any]], key: str) -> list[str]:
    values: set[str] = set()
    for hypothesis in hypotheses:
        for value in _as_list(hypothesis.get(key)):
            text = str(value).strip()
            if text:
                values.add(text)
    return sorted(values)


def _max_confidence(hypotheses: list[dict[str, Any]]) -> float:
    return _clip(max((_float(hypothesis.get("confidence")) for hypothesis in hypotheses), default=0.0))


def _source_signal_ids(hypotheses: list[dict[str, Any]]) -> list[str]:
    return sorted(
        {
            str(hypothesis.get("signal_id"))
            for hypothesis in hypotheses
            if str(hypothesis.get("signal_id") or "").strip()
        }
    )


def _source_evidence_packet_ids(hypotheses: list[dict[str, Any]]) -> list[str]:
    return sorted(
        {
            str(hypothesis.get("evidence_packet_id"))
            for hypothesis in hypotheses
            if str(hypothesis.get("evidence_packet_id") or "").strip()
        }
    )


def _source_execution_allowed_count(hypotheses: list[dict[str, Any]]) -> int:
    return sum(1 for hypothesis in hypotheses if hypothesis.get("execution_allowed") is True)


def _lifecycle_state(
    *,
    hypotheses: list[dict[str, Any]],
    edge_memory: dict[str, Any],
    strategy_proposal: dict[str, Any],
) -> tuple[str, str, str]:
    evidence_source_count = max(
        (_int(hypothesis.get("evidence_source_count")) for hypothesis in hypotheses),
        default=0,
    )
    missing_correlations = _union_list(hypotheses, "missing_correlations")
    confidence = _max_confidence(hypotheses)
    integrity_statuses = {
        str(hypothesis.get("integrity_review_status") or "not_reviewed")
        for hypothesis in hypotheses
    }
    if _source_execution_allowed_count(hypotheses):
        return (
            "blocked_source_execution_authority_present",
            "block_lifecycle_promotion",
            "The source hypothesis unexpectedly carries execution authority, so lifecycle review must hold and surface the authority mismatch.",
        )
    if not edge_memory or not strategy_proposal:
        return (
            "held_for_quantum_or_edge_mapping",
            "map_to_edge_memory_before_review",
            "The hypothesis cannot advance until it maps to a quantum-reviewed edge memory and read-only strategy update proposal.",
        )
    if (
        "second_independent_source" in missing_correlations
        or evidence_source_count < 2
    ):
        return (
            "held_for_independent_corroboration",
            "wait_for_independent_corroboration",
            "The hypothesis has not yet earned enough independent source corroboration for Signal Integrity review.",
        )
    if integrity_statuses == {"not_reviewed"}:
        return (
            "ready_for_signal_integrity_review",
            "route_to_signal_integrity_when_guarded",
            "The hypothesis has enough basic corroboration to be reviewed, but this lifecycle layer cannot route or approve it.",
        )
    if confidence < 0.35:
        return (
            "refutation_candidate_not_applied",
            "record_refutation_candidate_without_applying",
            "The hypothesis confidence is low enough to document a refutation candidate, but no refutation is applied here.",
        )
    return (
        "retained_for_shadow_review",
        "retain_for_shadow_review_without_promotion",
        "The hypothesis remains useful research context, but it is still not a trade candidate.",
    )


def _thread_record(
    *,
    group: dict[str, Any],
    previous_thread: dict[str, Any],
    edge_memory_by_sleeve: dict[str, dict[str, Any]],
    strategy_proposal_by_sleeve: dict[str, dict[str, Any]],
    lifecycle_date: str,
    generated_at: str,
) -> dict[str, Any]:
    hypotheses = [
        hypothesis
        for hypothesis in _as_list(group.get("hypotheses"))
        if isinstance(hypothesis, dict)
    ]
    representative = max(
        hypotheses,
        key=lambda hypothesis: _parse_datetime(hypothesis.get("created_at")),
    )
    sleeve_key = _slug(group.get("sleeve_key"))
    edge_memory = edge_memory_by_sleeve.get(sleeve_key, {})
    strategy_proposal = strategy_proposal_by_sleeve.get(sleeve_key, {})
    state, next_action, reason = _lifecycle_state(
        hypotheses=hypotheses,
        edge_memory=edge_memory,
        strategy_proposal=strategy_proposal,
    )
    observation_dates = _unique_dates(
        _as_list(previous_thread.get("observation_dates")),
        lifecycle_date,
    )
    confidence = _max_confidence(hypotheses)
    evidence_source_count = max(
        (_int(hypothesis.get("evidence_source_count")) for hypothesis in hypotheses),
        default=0,
    )
    source_execution_count = _source_execution_allowed_count(hypotheses)
    thread = {
        "lifecycle_id": f"hypothesis-lifecycle:{group['hypothesis_key']}",
        "hypothesis_key": group["hypothesis_key"],
        "status": "hypothesis_lifecycle_recorded",
        "lifecycle_state": state,
        "decision_status": "recorded_not_applied",
        "decision": next_action,
        "decision_reason": reason,
        "sleeve_key": sleeve_key,
        "market_sleeve": edge_memory.get("market_sleeve") or strategy_proposal.get("market_sleeve"),
        "source_hypothesis_count": len(hypotheses),
        "source_signal_ids": _source_signal_ids(hypotheses),
        "source_evidence_packet_ids": _source_evidence_packet_ids(hypotheses),
        "source_hypothesis_statuses": sorted(
            {str(hypothesis.get("status") or "unknown") for hypothesis in hypotheses}
        ),
        "source_hypothesis_execution_allowed_count": source_execution_count,
        "representative_signal_id": representative.get("signal_id"),
        "representative_title": representative.get("title"),
        "representative_thesis": representative.get("thesis"),
        "instrument_focus": representative.get("instrument_focus"),
        "confidence": confidence,
        "evidence_source_count": evidence_source_count,
        "missing_correlations": _union_list(hypotheses, "missing_correlations"),
        "integrity_review_statuses": sorted(
            {
                str(hypothesis.get("integrity_review_status") or "not_reviewed")
                for hypothesis in hypotheses
            }
        ),
        "integrity_scores": [
            hypothesis.get("integrity_score")
            for hypothesis in hypotheses
            if hypothesis.get("integrity_score") is not None
        ],
        "invalidation": representative.get("invalidation"),
        "first_seen_at": previous_thread.get("first_seen_at") or representative.get("created_at") or generated_at,
        "last_seen_at": generated_at,
        "observation_dates": observation_dates,
        "observation_count": len(observation_dates),
        "consecutive_observation_count": _consecutive_count(observation_dates, lifecycle_date),
        "edge_memory_id": edge_memory.get("memory_id"),
        "edge_memory_observation_count": edge_memory.get("observation_count"),
        "edge_memory_persistence_state": edge_memory.get("persistence_state"),
        "strategy_update_id": strategy_proposal.get("update_id"),
        "strategy_update_status": strategy_proposal.get("status"),
        "strategy_update_proposed_adjustment": strategy_proposal.get("proposed_adjustment"),
        "strategy_update_applied": strategy_proposal.get("applied") is True,
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
        "allowed_lifecycle_uses": [
            "deduplicate_shadow_hypotheses",
            "document_missing_corroboration",
            "feed_daily_edge_review",
            "inform_signal_integrity_queue_when_guarded",
        ],
        "disallowed_lifecycle_uses": [
            "promote_trade_candidate",
            "override_signal_integrity",
            "apply_refutation",
            "apply_retention",
            "submit_order",
        ],
        "paper_trade_effect": (
            "None. Hypothesis lifecycle records cannot promote candidates or "
            "change paper trading behavior without downstream guarded review."
        ),
    }
    for field in HYPOTHESIS_LIFECYCLE_AUTHORITY_FALSE_FIELDS:
        thread[field] = False
    return thread


def build_hypothesis_lifecycle(
    *,
    cognition: dict[str, Any],
    edge_memory_ledger: dict[str, Any],
    strategy_update_record: dict[str, Any],
    previous_lifecycle: dict[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build Qadam's read-only hypothesis lifecycle artifact."""

    generated_at = generated_at or _now()
    lifecycle_date = _parse_datetime(generated_at).date().isoformat()
    validate_edge_memory_ledger(edge_memory_ledger)
    validate_strategy_update_record(strategy_update_record)
    hypotheses = [
        hypothesis
        for hypothesis in _as_list(_as_dict(cognition).get("hypotheses"))
        if isinstance(hypothesis, dict)
    ]
    dependency_ready = (
        edge_memory_ledger.get("status") == "edge_memory_active"
        and strategy_update_record.get("status") == "strategy_update_record_ready"
    )
    if not dependency_ready:
        status = "hypothesis_lifecycle_blocked_pending_strategy_update_record"
    elif not hypotheses:
        status = "hypothesis_lifecycle_waiting_for_hypotheses"
    else:
        status = "hypothesis_lifecycle_active"
    previous_by_key = _previous_threads_by_key(previous_lifecycle)
    edge_memory_by_sleeve = _records_by_sleeve(edge_memory_ledger.get("memory_records", []))
    proposal_by_sleeve = _records_by_sleeve(strategy_update_record.get("proposals", []))
    groups = _group_hypotheses(hypotheses)
    threads = [
        _thread_record(
            group=group,
            previous_thread=previous_by_key.get(str(group.get("hypothesis_key")), {}),
            edge_memory_by_sleeve=edge_memory_by_sleeve,
            strategy_proposal_by_sleeve=proposal_by_sleeve,
            lifecycle_date=lifecycle_date,
            generated_at=generated_at,
        )
        for group in groups
        if status == "hypothesis_lifecycle_active"
    ]
    lifecycle_states = [str(thread.get("lifecycle_state")) for thread in threads]
    source_execution_count = sum(
        _int(thread.get("source_hypothesis_execution_allowed_count"))
        for thread in threads
    )
    lifecycle = {
        "schema_version": HYPOTHESIS_LIFECYCLE_SCHEMA_VERSION,
        "artifact_type": "hypothesis_lifecycle",
        "artifact_id": "hypothesis-lifecycle:latest",
        "stage": "Stage 4B - Hypothesis Lifecycle",
        "generated_at": generated_at,
        "lifecycle_date": lifecycle_date,
        "status": status,
        "public_safe": True,
        "purpose": (
            "Deduplicate Qadam's shadow hypotheses into lifecycle threads and "
            "record whether each one is held, retained, or ready for further "
            "guarded review."
        ),
        "edge_memory_ledger_status": edge_memory_ledger.get("status"),
        "strategy_update_record_status": strategy_update_record.get("status"),
        "quantum_gate_status": strategy_update_record.get("quantum_gate_status"),
        "source_hypothesis_count": len(hypotheses),
        "unique_hypothesis_thread_count": len(threads),
        "duplicate_source_hypothesis_count": max(0, len(hypotheses) - len(threads)),
        "source_hypothesis_execution_allowed_count": source_execution_count,
        "held_for_corroboration_count": lifecycle_states.count(
            "held_for_independent_corroboration"
        ),
        "ready_for_signal_integrity_review_count": lifecycle_states.count(
            "ready_for_signal_integrity_review"
        ),
        "retained_shadow_count": lifecycle_states.count("retained_for_shadow_review"),
        "refutation_candidate_count": lifecycle_states.count(
            "refutation_candidate_not_applied"
        ),
        "blocked_authority_mismatch_count": lifecycle_states.count(
            "blocked_source_execution_authority_present"
        ),
        "quantum_dependency_satisfied_count": sum(
            1 for thread in threads if thread.get("quantum_dependency_satisfied") is True
        ),
        "strategy_update_linked_count": sum(
            1 for thread in threads if thread.get("strategy_update_id")
        ),
        "candidate_promotion_count": 0,
        "applied_lifecycle_transition_count": 0,
        "hypothesis_threads": threads,
        "recursive_improvement_contract": {
            "status": "lifecycle_recording_active" if threads else "blocked",
            "deduplicates_shadow_hypotheses": True,
            "uses_actual_calendar_dates": True,
            "same_day_runs_deduped": True,
            "uses_edge_memory": True,
            "uses_strategy_update_record": True,
            "uses_quantum_mandatory_review": True,
            "promotes_candidates": False,
            "applies_lifecycle_transitions": False,
            "overrides_signal_integrity": False,
            "paper_order_allowed": False,
            "broker_write_allowed": False,
            "boundary": (
                "Lifecycle memory can inform future review queues only. It "
                "cannot apply transitions or promote hypotheses into trades."
            ),
        },
        "blocked_reason": None
        if status == "hypothesis_lifecycle_active"
        else "strategy_update_record_not_ready"
        if not dependency_ready
        else "no_source_hypotheses_available",
        "documentation_routes": {
            "runtime_artifact": f"data/runtime/{HYPOTHESIS_LIFECYCLE_RUNTIME_ARTIFACT}",
            "history": f"data/runtime/{HYPOTHESIS_LIFECYCLE_HISTORY}",
            "event_log": f"data/runtime/{HYPOTHESIS_LIFECYCLE_EVENT_LOG}",
            "source_edge_memory_ledger": "data/runtime/edge_memory_ledger.json",
            "source_strategy_update_record": "data/runtime/strategy_update_record.json",
            "source_cognition": "data/runtime/cockpit-status.json#cognition.hypotheses",
        },
        "boundary": HYPOTHESIS_LIFECYCLE_BOUNDARY,
    }
    for field in HYPOTHESIS_LIFECYCLE_AUTHORITY_FALSE_FIELDS:
        lifecycle[field] = False
    return lifecycle


def validate_hypothesis_lifecycle(payload: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "artifact_type",
        "artifact_id",
        "stage",
        "generated_at",
        "lifecycle_date",
        "status",
        "public_safe",
        "purpose",
        "edge_memory_ledger_status",
        "strategy_update_record_status",
        "quantum_gate_status",
        "source_hypothesis_count",
        "unique_hypothesis_thread_count",
        "duplicate_source_hypothesis_count",
        "source_hypothesis_execution_allowed_count",
        "held_for_corroboration_count",
        "ready_for_signal_integrity_review_count",
        "retained_shadow_count",
        "refutation_candidate_count",
        "blocked_authority_mismatch_count",
        "quantum_dependency_satisfied_count",
        "strategy_update_linked_count",
        "candidate_promotion_count",
        "applied_lifecycle_transition_count",
        "hypothesis_threads",
        "recursive_improvement_contract",
        "blocked_reason",
        "documentation_routes",
        "boundary",
        *HYPOTHESIS_LIFECYCLE_AUTHORITY_FALSE_FIELDS,
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"hypothesis lifecycle missing fields: {missing}")
    if payload.get("schema_version") != HYPOTHESIS_LIFECYCLE_SCHEMA_VERSION:
        raise ValueError("hypothesis lifecycle schema mismatch")
    if payload.get("artifact_type") != "hypothesis_lifecycle":
        raise ValueError("hypothesis lifecycle artifact type mismatch")
    if payload.get("status") not in HYPOTHESIS_LIFECYCLE_STATUSES:
        raise ValueError("hypothesis lifecycle status invalid")
    if payload.get("public_safe") is not True:
        raise ValueError("hypothesis lifecycle must be public-safe")
    if "read-only research documentation" not in str(payload.get("boundary", "")):
        raise ValueError("hypothesis lifecycle boundary weak")
    for field in HYPOTHESIS_LIFECYCLE_AUTHORITY_FALSE_FIELDS:
        if payload.get(field) is not False:
            raise ValueError(f"hypothesis lifecycle authority leak: {field}")
    contract = _as_dict(payload.get("recursive_improvement_contract"))
    for field in (
        "promotes_candidates",
        "applies_lifecycle_transitions",
        "overrides_signal_integrity",
        "paper_order_allowed",
        "broker_write_allowed",
    ):
        if contract.get(field) is not False:
            raise ValueError(f"hypothesis lifecycle contract authority leak: {field}")
    threads = payload.get("hypothesis_threads")
    if not isinstance(threads, list):
        raise ValueError("hypothesis lifecycle threads must be a list")
    if _int(payload.get("unique_hypothesis_thread_count")) != len(threads):
        raise ValueError("hypothesis lifecycle thread count mismatch")
    if _int(payload.get("candidate_promotion_count")) != 0:
        raise ValueError("hypothesis lifecycle cannot promote candidates")
    if _int(payload.get("applied_lifecycle_transition_count")) != 0:
        raise ValueError("hypothesis lifecycle cannot apply transitions")
    active = payload.get("status") == "hypothesis_lifecycle_active"
    if active:
        if payload.get("edge_memory_ledger_status") != "edge_memory_active":
            raise ValueError("active hypothesis lifecycle requires active edge memory")
        if payload.get("strategy_update_record_status") != "strategy_update_record_ready":
            raise ValueError("active hypothesis lifecycle requires strategy update record")
        if payload.get("quantum_gate_status") != "quantum_review_gate_passed":
            raise ValueError("active hypothesis lifecycle requires passed quantum gate")
        if _int(payload.get("source_hypothesis_count")) < 1:
            raise ValueError("active hypothesis lifecycle needs source hypotheses")
        if not threads:
            raise ValueError("active hypothesis lifecycle needs lifecycle threads")
        if _int(payload.get("source_hypothesis_count")) < len(threads):
            raise ValueError("hypothesis lifecycle cannot have more threads than source hypotheses")
        if payload.get("blocked_reason") is not None:
            raise ValueError("active hypothesis lifecycle cannot be blocked")
    else:
        if payload.get("blocked_reason") not in {
            "strategy_update_record_not_ready",
            "no_source_hypotheses_available",
        }:
            raise ValueError("blocked hypothesis lifecycle needs blocked reason")
        if threads:
            raise ValueError("blocked hypothesis lifecycle cannot emit threads")
    lifecycle_ids: set[str] = set()
    source_execution_sum = 0
    quantum_dependency_sum = 0
    strategy_link_sum = 0
    for thread in threads:
        if not isinstance(thread, dict):
            raise ValueError("hypothesis lifecycle thread must be a dict")
        lifecycle_id = str(thread.get("lifecycle_id") or "")
        if not lifecycle_id:
            raise ValueError("hypothesis lifecycle thread missing lifecycle id")
        if lifecycle_id in lifecycle_ids:
            raise ValueError("hypothesis lifecycle duplicate lifecycle id")
        lifecycle_ids.add(lifecycle_id)
        if thread.get("status") != "hypothesis_lifecycle_recorded":
            raise ValueError("hypothesis lifecycle thread status invalid")
        if thread.get("lifecycle_state") not in HYPOTHESIS_LIFECYCLE_STATES:
            raise ValueError("hypothesis lifecycle thread state invalid")
        if thread.get("decision_status") != "recorded_not_applied":
            raise ValueError("hypothesis lifecycle decision must be recorded only")
        if thread.get("quantum_mandatory_review_required") is not True:
            raise ValueError("hypothesis lifecycle thread must require quantum review")
        if thread.get("strategy_update_applied") is not False:
            raise ValueError("hypothesis lifecycle thread cannot use applied strategy update")
        if not isinstance(thread.get("source_signal_ids"), list) or not thread["source_signal_ids"]:
            raise ValueError("hypothesis lifecycle thread needs source signal ids")
        if not isinstance(thread.get("source_evidence_packet_ids"), list):
            raise ValueError("hypothesis lifecycle thread evidence ids invalid")
        if _int(thread.get("source_hypothesis_count")) != len(thread["source_signal_ids"]):
            raise ValueError("hypothesis lifecycle source signal count mismatch")
        dates = thread.get("observation_dates")
        if not isinstance(dates, list) or not dates:
            raise ValueError("hypothesis lifecycle thread needs observation dates")
        if len(dates) != len(set(dates)):
            raise ValueError("hypothesis lifecycle observation dates must be deduped")
        if payload.get("lifecycle_date") not in dates:
            raise ValueError("hypothesis lifecycle thread missing current lifecycle date")
        if _int(thread.get("observation_count")) != len(dates):
            raise ValueError("hypothesis lifecycle observation count mismatch")
        if _int(thread.get("consecutive_observation_count")) < 1:
            raise ValueError("hypothesis lifecycle consecutive count invalid")
        if thread.get("quantum_dependency_satisfied") is True:
            quantum_dependency_sum += 1
        if thread.get("strategy_update_id"):
            strategy_link_sum += 1
        source_execution_sum += _int(thread.get("source_hypothesis_execution_allowed_count"))
        for field in HYPOTHESIS_LIFECYCLE_AUTHORITY_FALSE_FIELDS:
            if thread.get(field) is not False:
                raise ValueError(f"hypothesis lifecycle thread authority leak: {field}")
    if _int(payload.get("source_hypothesis_execution_allowed_count")) != source_execution_sum:
        raise ValueError("hypothesis lifecycle source execution count mismatch")
    if _int(payload.get("quantum_dependency_satisfied_count")) != quantum_dependency_sum:
        raise ValueError("hypothesis lifecycle quantum dependency count mismatch")
    if _int(payload.get("strategy_update_linked_count")) != strategy_link_sum:
        raise ValueError("hypothesis lifecycle strategy link count mismatch")
    if active and quantum_dependency_sum < 1:
        raise ValueError("hypothesis lifecycle needs at least one quantum-linked thread")


def write_hypothesis_lifecycle(
    payload: dict[str, Any],
    settings: Settings | None = None,
) -> dict[str, Any]:
    validate_hypothesis_lifecycle(payload)
    output_path, history_path, event_path = hypothesis_lifecycle_paths(settings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    event = {
        "schema_version": HYPOTHESIS_LIFECYCLE_SCHEMA_VERSION,
        "event_type": HYPOTHESIS_LIFECYCLE_EVENT_TYPE,
        "component": HYPOTHESIS_LIFECYCLE_COMPONENT,
        "created_at": payload.get("generated_at") or _now(),
        "lifecycle_date": payload.get("lifecycle_date"),
        "status": payload.get("status"),
        "source_hypothesis_count": payload.get("source_hypothesis_count"),
        "unique_hypothesis_thread_count": payload.get("unique_hypothesis_thread_count"),
        "duplicate_source_hypothesis_count": payload.get("duplicate_source_hypothesis_count"),
        "held_for_corroboration_count": payload.get("held_for_corroboration_count"),
        "quantum_dependency_satisfied_count": payload.get("quantum_dependency_satisfied_count"),
        "candidate_promotion_count": payload.get("candidate_promotion_count"),
        "applied_lifecycle_transition_count": payload.get("applied_lifecycle_transition_count"),
        "authority_leak_count": sum(
            1
            for field in HYPOTHESIS_LIFECYCLE_AUTHORITY_FALSE_FIELDS
            if payload.get(field) is not False
        ),
        "public_safe": True,
        "boundary": HYPOTHESIS_LIFECYCLE_BOUNDARY,
    }
    with event_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    return {
        "output_path": str(output_path),
        "history_path": str(history_path),
        "event_log_path": str(event_path),
    }
