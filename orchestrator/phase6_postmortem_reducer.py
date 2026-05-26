"""Q6-7 postmortem reducer and review gate.

This stage reduces the deterministic Q6-6 analysis packets into a single
human-reviewable postmortem record. It computes proposed classifications and
opens a review gate, but it does not approve the postmortem, write learning
state, mutate policy, update scores, or create any downstream learning write.
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.phase6_artifacts import (
    PHASE6_ARTIFACT_SCHEMA_VERSION,
    PHASE6_UNSAFE_COUNT_FIELDS,
    phase6_authority_defaults,
    phase6_authority_ledger,
    phase6_event_contract,
    phase6_provenance,
    phase6_source_posture,
    phase6_unsafe_counter_defaults,
    validate_phase6_artifact,
)
from orchestrator.phase6_postmortem_analysis import (
    ANALYSIS_PACKET_TYPES,
    PHASE6_POSTMORTEM_ANALYSIS_RUNTIME_ARTIFACT,
    validate_phase6_postmortem_analysis,
)


PHASE6_POSTMORTEM_REDUCER_SCHEMA_VERSION = 1
PHASE6_POSTMORTEM_REDUCER_RUNTIME_ARTIFACT = "phase6_postmortem_reduced_review.json"
PHASE6_POSTMORTEM_REDUCER_HISTORY = "phase6_postmortem_reduced_review_history.jsonl"
PHASE6_POSTMORTEM_REDUCER_EVENT_LOG = "phase6_postmortem_reduced_review_events.jsonl"
PHASE6_POSTMORTEM_REDUCER_EVENT_TYPE = "phase6_postmortem_review_recorded"
PHASE6_POSTMORTEM_REDUCER_COMPONENT = "phase6_postmortem_reducer"

SOURCE_ANALYSIS_REF = f"data/runtime/{PHASE6_POSTMORTEM_ANALYSIS_RUNTIME_ARTIFACT}"

CLASSIFICATION_OPTIONS: tuple[str, ...] = ("useful", "harmful", "neutral", "untestable")
GOVERNANCE_STATES: tuple[str, ...] = (
    "draft",
    "review_required",
    "approved",
    "rejected",
    "deferred",
)

PHASE6_POSTMORTEM_REDUCER_BOUNDARY = (
    "Q6-7 reduces analysis packets into a human-reviewable postmortem and "
    "opens a review gate only. It can compute proposed classifications and "
    "queue review items, but it cannot approve a postmortem, cannot approve "
    "learning actions, cannot write learning data, cannot write a Knowledge "
    "Graph, cannot update model weights, cannot update trust scores, cannot "
    "mutate policy, cannot mutate strategies, cannot call broker POST routes, "
    "cannot call Alpaca POST routes, cannot call live endpoints, cannot enable "
    "live capital, and cannot count Phase 5 test trades toward Phase 7 proof."
)

WRITE_DISABLED_FIELDS: tuple[str, ...] = (
    "postmortem_approved",
    "learning_write_allowed",
    "learning_write_created",
    "knowledge_graph_write_created",
    "model_weight_update_created",
    "trust_score_update_created",
    "policy_mutation_created",
    "strategy_mutation_created",
    "phase5_source_artifacts_mutated",
    "phase7_proof_credit_allowed",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _repo_root(settings: Settings | None = None) -> Path:
    return _runtime_dir(settings).parent.parent


def _path(ref: str, settings: Settings | None = None) -> Path:
    return _repo_root(settings) / ref


def _read_json(ref: str, settings: Settings | None = None) -> dict[str, Any] | None:
    path = _path(ref, settings)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _disabled_write_fields() -> dict[str, bool]:
    return {field: False for field in WRITE_DISABLED_FIELDS}


def _has_local_path(ref: str) -> bool:
    if ref.startswith("/") or ref.startswith("~"):
        return True
    return len(ref) > 2 and ref[1:3] == ":\\"


def phase6_postmortem_reducer_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE6_POSTMORTEM_REDUCER_RUNTIME_ARTIFACT,
        runtime / PHASE6_POSTMORTEM_REDUCER_HISTORY,
        runtime / PHASE6_POSTMORTEM_REDUCER_EVENT_LOG,
    )


def _source_refs(analysis: dict[str, Any]) -> list[str]:
    refs = [SOURCE_ANALYSIS_REF]
    provenance = analysis.get("provenance", {})
    if isinstance(provenance, dict):
        for ref in provenance.get("source_refs", []):
            if isinstance(ref, str) and ref not in refs:
                refs.append(ref)
    for ref in (
        analysis.get("source_postmortem_draft_ref"),
        analysis.get("postmortem_draft_ref"),
    ):
        if isinstance(ref, str) and ref not in refs:
            refs.append(ref)
    return refs


def _provenance(analysis: dict[str, Any]) -> dict[str, Any]:
    provenance = phase6_provenance(tuple(_source_refs(analysis)))
    analysis_provenance = analysis.get("provenance", {})
    if isinstance(analysis_provenance, dict):
        for bucket in (
            "execution_evidence_refs",
            "market_context_refs",
            "model_interpretation_refs",
            "governance_refs",
        ):
            provenance[bucket] = [
                ref for ref in analysis_provenance.get(bucket, []) if isinstance(ref, str)
            ]
    return provenance


def _packet_map(analysis: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(packet.get("analysis_packet_type")): packet
        for packet in _list(analysis.get("packets"))
        if isinstance(packet, dict) and packet.get("analysis_packet_type")
    }


def _classification_for_packet(packet: dict[str, Any]) -> str:
    packet_type = str(packet.get("analysis_packet_type") or "")
    if packet_type in {"catalyst_analysis", "regime_analysis"}:
        return "untestable"
    if packet_type == "pricing_analysis":
        return "neutral"
    if packet_type in {"execution_analysis", "override_analysis"}:
        return "useful"
    return "untestable"


def _classification_rationale(packet: dict[str, Any], classification: str) -> str:
    packet_type = str(packet.get("analysis_packet_type") or "")
    if classification == "useful":
        return f"{packet_type} provides actionable review evidence while preserving authority limits."
    if classification == "neutral":
        return f"{packet_type} records relevant context, but the flat local outcome limits inference."
    if classification == "harmful":
        return f"{packet_type} would be harmful only if it encouraged uncited learning writes."
    return f"{packet_type} lacks enough reviewed evidence for a testable learning conclusion."


def _classification_record(packet: dict[str, Any]) -> dict[str, Any]:
    packet_type = str(packet.get("analysis_packet_type") or "")
    classification = _classification_for_packet(packet)
    source_refs = [
        ref for ref in _list(packet.get("source_refs")) if isinstance(ref, str) and ref
    ]
    return {
        "classification_id": f"q6-7:{packet_type}",
        "analysis_packet_type": packet_type,
        "classification": classification,
        "classification_options": list(CLASSIFICATION_OPTIONS),
        "confidence": packet.get("confidence"),
        "confidence_label": packet.get("confidence_label"),
        "claim_count": packet.get("claim_count"),
        "uncertainty_count": packet.get("uncertainty_count"),
        "missing_evidence_count": packet.get("missing_evidence_count"),
        "source_refs": source_refs,
        "rationale": _classification_rationale(packet, classification),
        "review_required": True,
        "learning_action_approved": False,
    }


def _classification_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    return {
        classification: len(
            [
                record
                for record in records
                if record.get("classification") == classification
            ]
        )
        for classification in CLASSIFICATION_OPTIONS
    }


def _review_queue(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    queue: list[dict[str, Any]] = []
    for record in records:
        queue.append(
            {
                "review_item_id": f"q6-7-review:{record.get('analysis_packet_type')}",
                "analysis_packet_type": record.get("analysis_packet_type"),
                "proposed_classification": record.get("classification"),
                "review_state": "review_required",
                "reviewer_label": None,
                "source_refs": record.get("source_refs", []),
                "learning_action_approved": False,
            }
        )
    return queue


def build_phase6_postmortem_reducer(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    analysis = _read_json(SOURCE_ANALYSIS_REF, settings) or {}
    analysis_errors = validate_phase6_postmortem_analysis(analysis) if analysis else []
    blockers: list[str] = []
    if not analysis:
        blockers.append("postmortem_analysis_missing")
    elif analysis.get("status") != "draft":
        blockers.append("postmortem_analysis_not_draft")
    if analysis_errors:
        blockers.append("postmortem_analysis_validation_errors")

    packet_by_type = _packet_map(analysis)
    missing_packet_types = sorted(set(ANALYSIS_PACKET_TYPES) - set(packet_by_type))
    if missing_packet_types:
        blockers.append("analysis_packet_types_missing")
    classification_records = (
        [_classification_record(packet_by_type[packet_type]) for packet_type in ANALYSIS_PACKET_TYPES]
        if not blockers
        else []
    )
    classification_counts = _classification_counts(classification_records)
    review_queue = _review_queue(classification_records)
    status = "pending_review" if not blockers else "blocked"
    authority = phase6_authority_ledger()
    authority["stage"] = "Q6-7"
    authority["boundary"] = PHASE6_POSTMORTEM_REDUCER_BOUNDARY
    artifact = {
        "schema_version": PHASE6_ARTIFACT_SCHEMA_VERSION,
        "phase6_postmortem_reducer_schema_version": PHASE6_POSTMORTEM_REDUCER_SCHEMA_VERSION,
        "artifact_type": "postmortem_review",
        "artifact_id": "phase6:q6-7:postmortem-review:crude_oil_energy_security_disruption",
        "phase": "Q6",
        "stage": "Q6-7",
        "status": status,
        "generated_at": generated_at,
        "public_safe": True,
        "recorded": False,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_event_count": 0,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "runtime_artifact_path": None,
        "history_log_path": None,
        "event_contract": phase6_event_contract("postmortem_review"),
        "authority_ledger": authority,
        "source_posture": phase6_source_posture(),
        "provenance": _provenance(analysis),
        "boundary": PHASE6_POSTMORTEM_REDUCER_BOUNDARY,
        **phase6_authority_defaults(),
        **phase6_unsafe_counter_defaults(),
        **_disabled_write_fields(),
        "review_state": "review_required" if not blockers else "blocked",
        "governance_state": "review_required" if not blockers else "blocked",
        "governance_states": list(GOVERNANCE_STATES),
        "reviewer_label": None,
        "reviewer_required": True,
        "approval_state": "not_requested",
        "approval_logged": False,
        "postmortem_approved": False,
        "write_allowed": False,
        "learning_write_allowed": False,
        "learning_action_count": 0,
        "learning_action_approved_count": 0,
        "proposed_learning_action_count": len(classification_records),
        "pending_review_action_count": len(review_queue),
        "source_analysis_ref": SOURCE_ANALYSIS_REF,
        "source_analysis_status": analysis.get("status"),
        "source_outcome_ref": analysis.get("source_outcome_ref"),
        "source_closed_trade_ref": analysis.get("source_closed_trade_ref"),
        "source_postmortem_draft_ref": analysis.get("source_postmortem_draft_ref"),
        "reduced_postmortem_created": bool(classification_records),
        "reduced_postmortem": {
            "source_analysis_ref": SOURCE_ANALYSIS_REF,
            "source_outcome_ref": analysis.get("source_outcome_ref"),
            "source_closed_trade_ref": analysis.get("source_closed_trade_ref"),
            "classification_records": classification_records,
            "classification_counts": classification_counts,
            "review_queue": review_queue,
            "review_state": "review_required" if not blockers else "blocked",
            "approval_state": "not_requested",
            "postmortem_approved": False,
            "learning_action_approved_count": 0,
        },
        "classification_options": list(CLASSIFICATION_OPTIONS),
        "classification_records": classification_records,
        "classification_record_count": len(classification_records),
        "classification_counts": classification_counts,
        "useful_classification_count": classification_counts["useful"],
        "harmful_classification_count": classification_counts["harmful"],
        "neutral_classification_count": classification_counts["neutral"],
        "untestable_classification_count": classification_counts["untestable"],
        "review_queue": review_queue,
        "review_queue_count": len(review_queue),
        "llm_required": False,
        "llm_used": False,
        "deterministic_reduction": True,
        "phase5_test_trades_count_for_phase7": False,
        "phase7_proof_credit_allowed": False,
        "unsafe_write_counter_total": 0,
        "blockers": sorted(set(blockers)),
        "blocker_count": len(set(blockers)),
        "recommended_next_stage": "Q6-8 Outcome Linker",
    }
    artifact["validation_errors"] = validate_phase6_postmortem_reducer(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "error"
    return artifact


def _write_disabled_errors(prefix: str, payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in WRITE_DISABLED_FIELDS:
        if payload.get(field) is not False:
            errors.append(f"{prefix}_write_enabled:{field}")
    return errors


def _source_ref_errors(prefix: str, refs: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(refs, list) or not refs:
        return [f"{prefix}_source_refs_missing"]
    for ref in refs:
        if not isinstance(ref, str) or not ref.strip():
            errors.append(f"{prefix}_source_ref_invalid")
            continue
        if _has_local_path(ref):
            errors.append(f"{prefix}_local_source_ref")
        if any(secret_word in ref.lower() for secret_word in ("api_key", "secret", "token")):
            errors.append(f"{prefix}_secret_source_ref")
    return errors


def validate_phase6_postmortem_reducer(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schema_version",
        "phase6_postmortem_reducer_schema_version",
        "artifact_type",
        "artifact_id",
        "phase",
        "stage",
        "status",
        "generated_at",
        "public_safe",
        "event_log_required",
        "event_log_written",
        "event_contract",
        "authority_ledger",
        "source_posture",
        "provenance",
        "boundary",
        "review_state",
        "governance_state",
        "governance_states",
        "reviewer_label",
        "reviewer_required",
        "approval_state",
        "approval_logged",
        "postmortem_approved",
        "write_allowed",
        "learning_action_count",
        "learning_action_approved_count",
        "proposed_learning_action_count",
        "pending_review_action_count",
        "learning_write_allowed",
        "source_analysis_ref",
        "source_outcome_ref",
        "source_closed_trade_ref",
        "reduced_postmortem_created",
        "reduced_postmortem",
        "classification_options",
        "classification_records",
        "classification_record_count",
        "classification_counts",
        "review_queue",
        "review_queue_count",
        "llm_used",
        "deterministic_reduction",
        "phase5_test_trades_count_for_phase7",
        "phase7_proof_credit_allowed",
        "unsafe_write_counter_total",
        "blockers",
        "blocker_count",
    }
    missing = sorted(required_fields - set(artifact))
    if missing:
        errors.append("postmortem_reducer_missing_fields:" + ",".join(missing))
    if artifact.get("phase6_postmortem_reducer_schema_version") != (
        PHASE6_POSTMORTEM_REDUCER_SCHEMA_VERSION
    ):
        errors.append("postmortem_reducer_schema_version_mismatch")
    errors.extend(validate_phase6_artifact(artifact, expected_stage="Q6-7"))
    if artifact.get("artifact_type") != "postmortem_review":
        errors.append("postmortem_reducer_artifact_type_mismatch")
    if artifact.get("status") not in {"pending_review", "blocked", "error"}:
        errors.append("postmortem_reducer_status_invalid")
    if artifact.get("review_state") != "review_required":
        errors.append("review_state_invalid")
    if artifact.get("governance_state") != "review_required":
        errors.append("governance_state_invalid")
    if set(_list(artifact.get("governance_states"))) != set(GOVERNANCE_STATES):
        errors.append("governance_states_invalid")
    if artifact.get("approval_state") != "not_requested":
        errors.append("approval_state_invalid")
    if artifact.get("approval_logged") is not False:
        errors.append("approval_logged")
    if artifact.get("postmortem_approved") is True:
        errors.append("postmortem_approved_before_review")
        if not artifact.get("reviewer_label"):
            errors.append("approved_without_reviewer")
        if (
            artifact.get("event_log_written") is not True
            or not artifact.get("event_log_correlation_id")
        ):
            errors.append("approved_without_event_log")
    elif artifact.get("postmortem_approved") is not False:
        errors.append("postmortem_approved_invalid")
    if artifact.get("reviewer_label") is not None:
        errors.append("reviewer_label_set_before_review")
    if artifact.get("reviewer_required") is not True:
        errors.append("reviewer_not_required")
    if artifact.get("write_allowed") is not False:
        errors.append("write_allowed")
    if artifact.get("learning_write_allowed") is not False:
        errors.append("learning_write_allowed")
    errors.extend(_write_disabled_errors("postmortem_reducer", artifact))
    for field in PHASE6_UNSAFE_COUNT_FIELDS:
        if int(artifact.get(field, 0) or 0) != 0:
            errors.append(f"postmortem_reducer_unsafe_count_nonzero:{field}")
    unsafe_total = sum(int(artifact.get(field, 0) or 0) for field in PHASE6_UNSAFE_COUNT_FIELDS)
    if artifact.get("unsafe_write_counter_total") != unsafe_total:
        errors.append("postmortem_reducer_unsafe_total_mismatch")
    if artifact.get("unsafe_write_counter_total") != 0:
        errors.append("postmortem_reducer_unsafe_total_nonzero")
    if artifact.get("learning_action_count") != 0:
        errors.append("learning_action_count_nonzero")
    if artifact.get("learning_action_approved_count") != 0:
        errors.append("learning_action_approved_count_nonzero")
    if int(artifact.get("proposed_learning_action_count", 0) or 0) < 1:
        errors.append("proposed_learning_action_count_missing")
    if artifact.get("source_analysis_ref") != SOURCE_ANALYSIS_REF:
        errors.append("source_analysis_ref_invalid")
    if not artifact.get("source_outcome_ref"):
        errors.append("source_outcome_ref_missing")
    if not artifact.get("source_closed_trade_ref"):
        errors.append("source_closed_trade_ref_missing")
    if artifact.get("reduced_postmortem_created") is not True:
        errors.append("reduced_postmortem_not_created")
    if artifact.get("llm_used") is not False:
        errors.append("llm_used")
    if artifact.get("deterministic_reduction") is not True:
        errors.append("deterministic_reduction_not_true")
    if artifact.get("phase7_proof_credit_allowed") is not False:
        errors.append("phase7_proof_credit_allowed")
    if artifact.get("phase5_test_trades_count_for_phase7") is not False:
        errors.append("phase5_test_trades_count_for_phase7")

    classification_options = artifact.get("classification_options", [])
    if not isinstance(classification_options, list) or set(classification_options) != set(
        CLASSIFICATION_OPTIONS
    ):
        errors.append("classification_options_invalid")
    records = artifact.get("classification_records", [])
    if not isinstance(records, list):
        errors.append("classification_records_invalid")
        records = []
    if artifact.get("classification_record_count") != len(records):
        errors.append("classification_record_count_mismatch")
    if artifact.get("classification_record_count") != len(ANALYSIS_PACKET_TYPES):
        errors.append("classification_record_count_invalid")
    seen_packet_types: set[str] = set()
    computed_counts = {classification: 0 for classification in CLASSIFICATION_OPTIONS}
    for record in records:
        if not isinstance(record, dict):
            errors.append("classification_record_invalid")
            continue
        packet_type = str(record.get("analysis_packet_type") or "")
        seen_packet_types.add(packet_type)
        classification = str(record.get("classification") or "")
        if packet_type not in ANALYSIS_PACKET_TYPES:
            errors.append(f"classification_packet_type_invalid:{packet_type}")
        if classification not in CLASSIFICATION_OPTIONS:
            errors.append(f"classification_invalid:{classification}")
        else:
            computed_counts[classification] += 1
        if not record.get("rationale"):
            errors.append(f"classification_rationale_missing:{packet_type}")
        if record.get("review_required") is not True:
            errors.append(f"classification_review_not_required:{packet_type}")
        if record.get("learning_action_approved") is not False:
            errors.append(f"classification_learning_action_approved:{packet_type}")
        confidence = record.get("confidence")
        if not isinstance(confidence, int | float) or not 0 <= float(confidence) <= 1:
            errors.append(f"classification_confidence_invalid:{packet_type}")
        errors.extend(
            _source_ref_errors(
                f"classification_record:{packet_type}",
                record.get("source_refs"),
            )
        )
    if seen_packet_types != set(ANALYSIS_PACKET_TYPES):
        errors.append("classification_packet_type_set_mismatch")
    counts = artifact.get("classification_counts", {})
    if not isinstance(counts, dict):
        errors.append("classification_counts_invalid")
        counts = {}
    for classification, expected_count in computed_counts.items():
        if counts.get(classification) != expected_count:
            errors.append(f"classification_count_mismatch:{classification}")
        field_name = f"{classification}_classification_count"
        if artifact.get(field_name) != expected_count:
            errors.append(f"{field_name}_mismatch")

    review_queue = artifact.get("review_queue", [])
    if not isinstance(review_queue, list):
        errors.append("review_queue_invalid")
        review_queue = []
    if artifact.get("review_queue_count") != len(review_queue):
        errors.append("review_queue_count_mismatch")
    if artifact.get("review_queue_count") != len(records):
        errors.append("review_queue_count_invalid")
    for item in review_queue:
        if not isinstance(item, dict):
            errors.append("review_queue_item_invalid")
            continue
        if item.get("review_state") != "review_required":
            errors.append("review_queue_item_state_invalid")
        if item.get("reviewer_label") is not None:
            errors.append("review_queue_reviewer_set_before_review")
        if item.get("learning_action_approved") is not False:
            errors.append("review_queue_learning_action_approved")
        errors.extend(
            _source_ref_errors(
                f"review_queue:{item.get('analysis_packet_type')}",
                item.get("source_refs"),
            )
        )
    reduced = artifact.get("reduced_postmortem")
    if not isinstance(reduced, dict):
        errors.append("reduced_postmortem_invalid")
    else:
        if reduced.get("review_state") != "review_required":
            errors.append("reduced_postmortem_review_state_invalid")
        if reduced.get("approval_state") != "not_requested":
            errors.append("reduced_postmortem_approval_state_invalid")
        if reduced.get("postmortem_approved") is not False:
            errors.append("reduced_postmortem_approved")
        if reduced.get("learning_action_approved_count") != 0:
            errors.append("reduced_postmortem_learning_action_approved")
        if reduced.get("classification_records") != records:
            errors.append("reduced_postmortem_classification_records_mismatch")
        if reduced.get("review_queue") != review_queue:
            errors.append("reduced_postmortem_review_queue_mismatch")
    blockers = artifact.get("blockers", [])
    if not isinstance(blockers, list):
        errors.append("blockers_invalid")
        blockers = []
    if artifact.get("blocker_count") != len(blockers):
        errors.append("blocker_count_mismatch")
    if artifact.get("status") == "pending_review" and blockers:
        errors.append("pending_review_with_blockers")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "reduces analysis packets into a human-reviewable postmortem",
        "opens a review gate only",
        "cannot approve a postmortem",
        "cannot approve learning actions",
        "cannot write learning data",
        "cannot write a Knowledge Graph",
        "cannot mutate policy",
        "cannot mutate strategies",
        "cannot count Phase 5 test trades toward Phase 7 proof",
    ):
        if phrase not in boundary:
            errors.append("postmortem_reducer_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("postmortem_reducer_event_log_path_missing")
        if not str(artifact.get("event_log_correlation_id") or "").strip():
            errors.append("postmortem_reducer_event_correlation_missing")
        if artifact.get("event_log_event_count") != 1:
            errors.append("postmortem_reducer_event_log_count_mismatch")
    return sorted(set(errors))


def attach_phase6_postmortem_reducer_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(
        event_log_path or (_runtime_dir(settings) / PHASE6_POSTMORTEM_REDUCER_EVENT_LOG)
    )
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PHASE6_POSTMORTEM_REDUCER_EVENT_TYPE,
        PHASE6_POSTMORTEM_REDUCER_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "review_state": output.get("review_state"),
            "governance_state": output.get("governance_state"),
            "approval_state": output.get("approval_state"),
            "reviewer_label": output.get("reviewer_label"),
            "reduced_postmortem_created": output.get("reduced_postmortem_created"),
            "classification_record_count": output.get("classification_record_count"),
            "classification_counts": output.get("classification_counts"),
            "review_queue_count": output.get("review_queue_count"),
            "learning_action_count": output.get("learning_action_count"),
            "proposed_learning_action_count": output.get("proposed_learning_action_count"),
            "postmortem_approved": output.get("postmortem_approved"),
            "write_allowed": output.get("write_allowed"),
            "learning_write_created": output.get("learning_write_created"),
            "knowledge_graph_write_created": output.get("knowledge_graph_write_created"),
            "policy_mutation_created": output.get("policy_mutation_created"),
            "strategy_mutation_created": output.get("strategy_mutation_created"),
            "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
            "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
            "boundary": output.get("boundary"),
        },
    )
    output["recorded"] = True
    output["event_log_written"] = True
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = 1
    output["event_log_correlation_id"] = entry.correlation_id
    output["event_log_created_at"] = entry.created_at
    output["validation_errors"] = validate_phase6_postmortem_reducer(output)
    if output["validation_errors"]:
        output["status"] = "error"
    return output, entry


def write_phase6_postmortem_reducer(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase6_postmortem_reducer_paths(
        settings
    )
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase6_postmortem_reducer_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase6_postmortem_reducer(output)
        if output["validation_errors"]:
            output["status"] = "error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase6_postmortem_reducer(output)
    if output["validation_errors"]:
        output["status"] = "error"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE6_POSTMORTEM_REDUCER_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "review_state": output.get("review_state"),
        "governance_state": output.get("governance_state"),
        "approval_state": output.get("approval_state"),
        "reduced_postmortem_created": output.get("reduced_postmortem_created"),
        "classification_record_count": output.get("classification_record_count"),
        "classification_counts": output.get("classification_counts"),
        "review_queue_count": output.get("review_queue_count"),
        "learning_action_count": output.get("learning_action_count"),
        "postmortem_approved": output.get("postmortem_approved"),
        "write_allowed": output.get("write_allowed"),
        "learning_write_created": output.get("learning_write_created"),
        "knowledge_graph_write_created": output.get("knowledge_graph_write_created"),
        "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
        "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
        "blocker_count": output.get("blocker_count"),
        "event_log_written": output.get("event_log_written"),
        "event_log_event_count": output.get("event_log_event_count"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output
