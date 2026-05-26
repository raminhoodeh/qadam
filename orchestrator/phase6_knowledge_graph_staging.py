"""Q6-10 Knowledge Graph staged writes.

This stage prepares the Knowledge Graph write contract that later approved
postmortem learning actions must pass through. With the current Q6-9 ledger,
there are no approved actions, so the artifact records a blocked staging gate
and creates no graph entries or graph commits.
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
from orchestrator.phase6_learning_approval import (
    PHASE6_LEARNING_APPROVAL_RUNTIME_ARTIFACT,
    validate_phase6_learning_approval,
)


PHASE6_KNOWLEDGE_GRAPH_STAGING_SCHEMA_VERSION = 1
PHASE6_KNOWLEDGE_GRAPH_STAGING_RUNTIME_ARTIFACT = (
    "phase6_knowledge_graph_staged_writes.json"
)
PHASE6_KNOWLEDGE_GRAPH_STAGING_HISTORY = (
    "phase6_knowledge_graph_staged_writes_history.jsonl"
)
PHASE6_KNOWLEDGE_GRAPH_STAGING_EVENT_LOG = (
    "phase6_knowledge_graph_staged_writes_events.jsonl"
)
PHASE6_KNOWLEDGE_GRAPH_STAGING_EVENT_TYPE = "phase6_learning_write_staged"
PHASE6_KNOWLEDGE_GRAPH_STAGING_COMPONENT = "phase6_knowledge_graph_staging"

SOURCE_APPROVAL_REF = f"data/runtime/{PHASE6_LEARNING_APPROVAL_RUNTIME_ARTIFACT}"
TARGET_GRAPH_NAMESPACE = "phase6_learning_memory"
TARGET_STRATEGY_FAMILY_KEY = "crude_oil_energy_security_disruption"

PHASE6_KNOWLEDGE_GRAPH_STAGING_BOUNDARY = (
    "Q6-10 creates a Knowledge Graph staging gate only. It can prepare "
    "reference-only staged entry shapes, supersession metadata, and rollback "
    "metadata for explicitly approved postmortem learning actions, but it "
    "cannot create staged entries without approval, cannot commit a Knowledge "
    "Graph write, cannot write Chroma or graph backend state, cannot update "
    "model weights, cannot update trust scores, cannot mutate policy, cannot "
    "mutate strategies, cannot mutate Phase 5 source artifacts, cannot call "
    "broker POST routes, cannot call Alpaca POST routes, cannot call live "
    "endpoints, cannot enable live capital, and cannot count Phase 5 test "
    "trades toward Phase 7 proof."
)

WRITE_DISABLED_FIELDS: tuple[str, ...] = (
    "learning_write_allowed",
    "learning_write_created",
    "knowledge_graph_write_created",
    "knowledge_graph_commit_created",
    "chroma_write_created",
    "graph_backend_write_created",
    "model_weight_update_created",
    "trust_score_update_created",
    "policy_mutation_created",
    "strategy_mutation_created",
    "phase5_source_artifacts_mutated",
    "phase7_proof_credit_allowed",
)

ENTRY_REQUIRED_FIELDS: tuple[str, ...] = (
    "staged_entry_id",
    "entry_state",
    "source_action_id",
    "analysis_packet_type",
    "graph_namespace",
    "graph_subject",
    "catalyst_taxonomy",
    "outcome_classification",
    "confidence",
    "approval_ref",
    "approval_event_log_ref",
    "source_refs",
    "supersedes_ref",
    "supersession_id",
    "rollback_ref",
    "destructive_overwrite_allowed",
    "commit_allowed",
    "reference_only",
    "raw_payload_copied",
    "private_payload_copied",
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


def phase6_knowledge_graph_staging_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE6_KNOWLEDGE_GRAPH_STAGING_RUNTIME_ARTIFACT,
        runtime / PHASE6_KNOWLEDGE_GRAPH_STAGING_HISTORY,
        runtime / PHASE6_KNOWLEDGE_GRAPH_STAGING_EVENT_LOG,
    )


def _stage_gate_open(approval: dict[str, Any]) -> bool:
    if approval.get("approval_state") != "approved":
        return False
    if approval.get("approval_logged") is not True:
        return False
    if not approval.get("reviewer_label"):
        return False
    if not approval.get("approval_event_log_ref"):
        return False
    if approval.get("missing_approval_blocks_downstream") is not False:
        return False
    if approval.get("knowledge_graph_staged_write_allowed") is not True:
        return False
    return int(approval.get("approved_action_count", 0) or 0) > 0


def _taxonomy_for_packet(packet_type: str) -> dict[str, str]:
    taxonomy = {
        "catalyst_analysis": ("catalyst_memory", "energy_security"),
        "pricing_analysis": ("pricing_context", "oil_linked_market_context"),
        "regime_analysis": ("regime_context", "macro_regime"),
        "execution_analysis": ("execution_memory", "paper_lifecycle_integrity"),
        "override_analysis": ("governance_memory", "authority_boundary"),
    }
    node_type, category = taxonomy.get(packet_type, ("postmortem_learning", "uncategorized"))
    return {
        "taxonomy_version": "q6-10-v1",
        "node_type": node_type,
        "category": category,
        "strategy_family_key": TARGET_STRATEGY_FAMILY_KEY,
    }


def _classification_confidence(
    source_classification_id: str | None,
    approval: dict[str, Any],
) -> float | None:
    for action in _list(approval.get("proposed_actions")):
        if not isinstance(action, dict):
            continue
        if action.get("source_classification_id") == source_classification_id:
            confidence = action.get("confidence")
            return float(confidence) if isinstance(confidence, int | float) else None
    return None


def _source_refs(action: dict[str, Any]) -> list[str]:
    refs: list[str] = [SOURCE_APPROVAL_REF]
    for ref in _list(action.get("source_refs")):
        if isinstance(ref, str) and ref not in refs:
            refs.append(ref)
    return refs


def _staged_entry(
    action: dict[str, Any],
    *,
    approval: dict[str, Any],
) -> dict[str, Any]:
    packet_type = str(action.get("analysis_packet_type") or "unknown")
    source_classification_id = (
        action.get("source_classification_id")
        if isinstance(action.get("source_classification_id"), str)
        else None
    )
    return {
        "staged_entry_id": f"q6-10-kg-entry:{packet_type}",
        "entry_state": "staged_pending_commit_validation",
        "source_action_id": action.get("action_id"),
        "source_classification_id": source_classification_id,
        "analysis_packet_type": packet_type,
        "graph_namespace": TARGET_GRAPH_NAMESPACE,
        "graph_subject": TARGET_STRATEGY_FAMILY_KEY,
        "catalyst_taxonomy": _taxonomy_for_packet(packet_type),
        "outcome_classification": action.get("proposed_classification"),
        "confidence": _classification_confidence(source_classification_id, approval),
        "approval_ref": SOURCE_APPROVAL_REF,
        "approval_event_log_ref": approval.get("approval_event_log_ref"),
        "reviewer_label": approval.get("reviewer_label"),
        "source_refs": _source_refs(action),
        "supersedes_ref": None,
        "supersession_id": f"q6-10-supersession:{packet_type}:v1",
        "rollback_ref": f"q6-10-rollback:{packet_type}:v1",
        "rollback_strategy": "drop_staged_entry_before_commit",
        "destructive_overwrite_allowed": False,
        "commit_allowed": False,
        "reference_only": True,
        "raw_payload_copied": False,
        "private_payload_copied": False,
        "learning_write_created": False,
        "knowledge_graph_write_created": False,
        "chroma_write_created": False,
        "graph_backend_write_created": False,
    }


def _blocked_action_records(approval: dict[str, Any], reason: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for action in _list(approval.get("proposed_actions")):
        if not isinstance(action, dict):
            continue
        records.append(
            {
                "action_id": action.get("action_id"),
                "source_classification_id": action.get("source_classification_id"),
                "analysis_packet_type": action.get("analysis_packet_type"),
                "approval_decision": action.get("approval_decision"),
                "learning_action_approved": action.get("learning_action_approved"),
                "knowledge_graph_staged_write_allowed": action.get(
                    "knowledge_graph_staged_write_allowed"
                ),
                "blocked_reason": reason,
                "source_refs": _source_refs(action),
                "reference_only": True,
                "raw_payload_copied": False,
                "private_payload_copied": False,
            }
        )
    return records


def _provenance(
    approval: dict[str, Any],
    staged_entries: list[dict[str, Any]],
    blocked_actions: list[dict[str, Any]],
) -> dict[str, Any]:
    refs: list[str] = [SOURCE_APPROVAL_REF]
    provenance = approval.get("provenance", {})
    if isinstance(provenance, dict):
        for ref in provenance.get("source_refs", []):
            if isinstance(ref, str) and ref not in refs:
                refs.append(ref)
    for record in staged_entries + blocked_actions:
        for ref in _list(record.get("source_refs")):
            if isinstance(ref, str) and ref not in refs:
                refs.append(ref)
    output = phase6_provenance(tuple(refs))
    output["execution_evidence_refs"] = [
        ref
        for ref in refs
        if any(
            marker in ref
            for marker in (
                "paper_order",
                "paper_submit",
                "position_monitor",
                "closed_trade",
                "postmortem_due",
                "outcome_links",
            )
        )
    ]
    output["market_context_refs"] = [
        ref for ref in refs if any(marker in ref for marker in ("cockpit-status", "preference_"))
    ]
    output["model_interpretation_refs"] = [
        ref for ref in refs if "quantum_oracle_results" in ref
    ]
    output["governance_refs"] = [
        ref for ref in refs if any(marker in ref for marker in ("approval", "reduced_review"))
    ]
    return output


def build_phase6_knowledge_graph_staging(
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    approval = _read_json(SOURCE_APPROVAL_REF, settings) or {}
    approval_errors = validate_phase6_learning_approval(approval) if approval else []
    blockers: list[str] = []
    if not approval:
        blockers.append("learning_approval_missing")
    elif approval.get("status") not in {"pending_review", "approved", "deferred"}:
        blockers.append("learning_approval_status_invalid")
    if approval_errors:
        blockers.append("learning_approval_validation_errors")
    if not _stage_gate_open(approval):
        blockers.append("learning_approval_not_approved_for_kg_staging")
    if int(approval.get("approved_action_count", 0) or 0) < 1:
        blockers.append("approved_actions_missing")
    if approval.get("missing_approval_blocks_downstream") is True:
        blockers.append("missing_approval_blocks_staging")

    stage_gate_open = not blockers
    approved_actions = [
        action
        for action in _list(approval.get("approved_actions"))
        if isinstance(action, dict)
        and action.get("learning_action_approved") is True
        and action.get("knowledge_graph_staged_write_allowed") is True
    ]
    staged_entries = (
        [_staged_entry(action, approval=approval) for action in approved_actions]
        if stage_gate_open
        else []
    )
    if stage_gate_open and not staged_entries:
        blockers.append("approved_kg_actions_missing")
        stage_gate_open = False

    blocked_reason = (
        "explicit_learning_deferral_recorded"
        if approval.get("approval_state") == "deferred"
        else "explicit_learning_approval_required"
    )
    blocked_actions = [] if stage_gate_open else _blocked_action_records(approval, blocked_reason)
    status = "staged" if stage_gate_open else "blocked"
    kg_write_state = (
        "staged_entries_pending_commit_validation"
        if stage_gate_open
        else "blocked_pending_learning_approval"
    )
    authority = phase6_authority_ledger()
    authority["stage"] = "Q6-10"
    authority["boundary"] = PHASE6_KNOWLEDGE_GRAPH_STAGING_BOUNDARY
    artifact = {
        "schema_version": PHASE6_ARTIFACT_SCHEMA_VERSION,
        "phase6_knowledge_graph_staging_schema_version": (
            PHASE6_KNOWLEDGE_GRAPH_STAGING_SCHEMA_VERSION
        ),
        "artifact_type": "knowledge_graph_staged_write",
        "artifact_id": "phase6:q6-10:knowledge-graph-staging:crude_oil_energy_security_disruption",
        "phase": "Q6",
        "stage": "Q6-10",
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
        "event_contract": phase6_event_contract("staged_learning_write"),
        "authority_ledger": authority,
        "source_posture": phase6_source_posture(),
        "provenance": _provenance(approval, staged_entries, blocked_actions),
        "boundary": PHASE6_KNOWLEDGE_GRAPH_STAGING_BOUNDARY,
        **phase6_authority_defaults(),
        **phase6_unsafe_counter_defaults(),
        **_disabled_write_fields(),
        "kg_write_state": kg_write_state,
        "staged_write_allowed": stage_gate_open,
        "knowledge_graph_staged_write_allowed": stage_gate_open,
        "approval_ref": SOURCE_APPROVAL_REF,
        "approval_state": approval.get("approval_state"),
        "approval_logged": approval.get("approval_logged"),
        "approval_event_log_ref": approval.get("approval_event_log_ref"),
        "reviewer_label": approval.get("reviewer_label"),
        "source_approval_status": approval.get("status"),
        "source_approval_state": approval.get("approval_state"),
        "source_approved_action_count": int(approval.get("approved_action_count", 0) or 0),
        "source_deferred_action_count": int(approval.get("deferred_action_count", 0) or 0),
        "source_pending_review_action_count": int(
            approval.get("pending_review_action_count", 0) or 0
        ),
        "candidate_action_count": len(_list(approval.get("proposed_actions"))),
        "approved_kg_action_count": len(approved_actions) if stage_gate_open else 0,
        "blocked_action_records": blocked_actions,
        "blocked_action_count": len(blocked_actions),
        "missing_approval_blocks_staging": not stage_gate_open,
        "staged_entries": staged_entries,
        "staged_entry_count": len(staged_entries),
        "supersedes_ref": None,
        "supersession_required": True,
        "supersession_id": (
            "q6-10-supersession-bundle:v1" if staged_entries else None
        ),
        "rollback_path": (
            "data/runtime/phase6_knowledge_graph_staged_writes_history.jsonl"
        ),
        "rollback_available": True,
        "destructive_overwrite_allowed": False,
        "knowledge_graph_commit_allowed": False,
        "chroma_write_allowed": False,
        "graph_backend_write_allowed": False,
        "actual_graph_commit_created": False,
        "knowledge_graph_commit_created": False,
        "chroma_write_created": False,
        "graph_backend_write_created": False,
        "learning_write_created": False,
        "knowledge_graph_write_created": False,
        "raw_payload_copied_count": 0,
        "private_payload_copied_count": 0,
        "local_path_exposed_count": 0,
        "secret_ref_exposed_count": 0,
        "phase5_test_trades_count_for_phase7": False,
        "phase7_proof_credit_allowed": False,
        "unsafe_write_counter_total": 0,
        "blockers": sorted(set(blockers)),
        "blocker_count": len(set(blockers)),
        "recommended_next_stage": "Q6-11 Knowledge Graph Read Path",
    }
    artifact["validation_errors"] = validate_phase6_knowledge_graph_staging(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "error"
    return artifact


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


def _write_disabled_errors(prefix: str, payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in WRITE_DISABLED_FIELDS:
        if payload.get(field) is not False:
            errors.append(f"{prefix}_write_enabled:{field}")
    return errors


def validate_phase6_knowledge_graph_staging(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schema_version",
        "phase6_knowledge_graph_staging_schema_version",
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
        "kg_write_state",
        "staged_write_allowed",
        "knowledge_graph_staged_write_allowed",
        "approval_ref",
        "approval_state",
        "approval_logged",
        "approval_event_log_ref",
        "reviewer_label",
        "source_approval_status",
        "source_approval_state",
        "source_approved_action_count",
        "source_deferred_action_count",
        "source_pending_review_action_count",
        "candidate_action_count",
        "approved_kg_action_count",
        "blocked_action_records",
        "blocked_action_count",
        "missing_approval_blocks_staging",
        "staged_entries",
        "staged_entry_count",
        "supersedes_ref",
        "supersession_required",
        "supersession_id",
        "rollback_path",
        "rollback_available",
        "destructive_overwrite_allowed",
        "knowledge_graph_commit_allowed",
        "chroma_write_allowed",
        "graph_backend_write_allowed",
        "actual_graph_commit_created",
        "knowledge_graph_commit_created",
        "chroma_write_created",
        "graph_backend_write_created",
        "learning_write_created",
        "knowledge_graph_write_created",
        "raw_payload_copied_count",
        "private_payload_copied_count",
        "local_path_exposed_count",
        "secret_ref_exposed_count",
        "phase5_test_trades_count_for_phase7",
        "phase7_proof_credit_allowed",
        "unsafe_write_counter_total",
        "blockers",
        "blocker_count",
    }
    missing = sorted(required_fields - set(artifact))
    if missing:
        errors.append("knowledge_graph_staging_missing_fields:" + ",".join(missing))
    if artifact.get("phase6_knowledge_graph_staging_schema_version") != (
        PHASE6_KNOWLEDGE_GRAPH_STAGING_SCHEMA_VERSION
    ):
        errors.append("knowledge_graph_staging_schema_version_mismatch")
    errors.extend(validate_phase6_artifact(artifact, expected_stage="Q6-10"))
    if artifact.get("artifact_type") != "knowledge_graph_staged_write":
        errors.append("knowledge_graph_staging_artifact_type_mismatch")
    if artifact.get("status") not in {"blocked", "staged", "error"}:
        errors.append("knowledge_graph_staging_status_invalid")
    if artifact.get("approval_ref") != SOURCE_APPROVAL_REF:
        errors.append("approval_ref_invalid")
    if artifact.get("source_approval_status") not in {"pending_review", "approved", "deferred"}:
        errors.append("source_approval_status_invalid")
    if artifact.get("source_approval_state") not in {"pending_review", "approved", "deferred"}:
        errors.append("source_approval_state_invalid")
    if artifact.get("source_approval_state") == "approved":
        if artifact.get("approval_logged") is not True:
            errors.append("staging_approval_without_event_log")
        if not artifact.get("reviewer_label"):
            errors.append("staging_approval_without_reviewer")
        if not artifact.get("approval_event_log_ref"):
            errors.append("staging_approval_event_ref_missing")
    elif artifact.get("source_approval_state") == "deferred":
        if artifact.get("approval_logged") is not True:
            errors.append("staging_deferral_without_event_log")
        if not artifact.get("reviewer_label"):
            errors.append("staging_deferral_without_reviewer")
        if not artifact.get("approval_event_log_ref"):
            errors.append("staging_deferral_event_ref_missing")
    else:
        if artifact.get("approval_logged") is not False:
            errors.append("approval_logged_before_approval")
        if artifact.get("approval_event_log_ref") is not None:
            errors.append("approval_event_log_ref_before_approval")
        if artifact.get("reviewer_label") is not None:
            errors.append("reviewer_label_before_approval")

    entries = _list(artifact.get("staged_entries"))
    blocked_actions = _list(artifact.get("blocked_action_records"))
    if artifact.get("staged_entry_count") != len(entries):
        errors.append("staged_entry_count_mismatch")
    if artifact.get("blocked_action_count") != len(blocked_actions):
        errors.append("blocked_action_count_mismatch")
    if artifact.get("status") == "blocked":
        if artifact.get("staged_write_allowed") is not False:
            errors.append("blocked_staged_write_allowed")
        if artifact.get("knowledge_graph_staged_write_allowed") is not False:
            errors.append("blocked_kg_staged_write_allowed")
        if artifact.get("staged_entry_count") != 0:
            errors.append("blocked_staged_entries_present")
        if artifact.get("missing_approval_blocks_staging") is not True:
            errors.append("missing_approval_not_blocking_staging")
        if not artifact.get("blockers"):
            errors.append("blocked_without_blockers")
    if artifact.get("status") == "staged":
        if artifact.get("staged_write_allowed") is not True:
            errors.append("staged_write_not_allowed")
        if artifact.get("knowledge_graph_staged_write_allowed") is not True:
            errors.append("kg_staged_write_not_allowed")
        if artifact.get("source_approval_state") != "approved":
            errors.append("staged_without_approved_source")
        if artifact.get("source_approved_action_count", 0) < 1:
            errors.append("staged_without_approved_actions")
        if artifact.get("staged_entry_count", 0) < 1:
            errors.append("staged_entry_count_invalid")
        if artifact.get("missing_approval_blocks_staging") is not False:
            errors.append("staged_missing_approval_still_blocks")
        if artifact.get("blockers"):
            errors.append("staged_with_blockers")
    if artifact.get("staged_entry_count", 0) > 0 and artifact.get("source_approval_state") != "approved":
        errors.append("staged_entries_without_approval")
    if artifact.get("approved_kg_action_count") != artifact.get("staged_entry_count"):
        errors.append("approved_kg_action_count_mismatch")
    if artifact.get("supersession_required") is not True:
        errors.append("supersession_not_required")
    if artifact.get("rollback_available") is not True:
        errors.append("rollback_not_available")
    if not str(artifact.get("rollback_path") or "").startswith("data/runtime/"):
        errors.append("rollback_path_invalid")
    if artifact.get("destructive_overwrite_allowed") is not False:
        errors.append("destructive_overwrite_allowed")
    for field in (
        "knowledge_graph_commit_allowed",
        "chroma_write_allowed",
        "graph_backend_write_allowed",
        "actual_graph_commit_created",
        "knowledge_graph_commit_created",
        "chroma_write_created",
        "graph_backend_write_created",
        "learning_write_created",
        "knowledge_graph_write_created",
    ):
        if artifact.get(field) is not False:
            errors.append(f"kg_staging_commit_or_write_enabled:{field}")
    if artifact.get("phase6_knowledge_graph_write_allowed") is not False:
        errors.append("phase6_knowledge_graph_write_allowed")
    if artifact.get("phase6_knowledge_graph_write_allowed_count") != 0:
        errors.append("phase6_knowledge_graph_write_allowed_count")
    if artifact.get("phase6_learning_write_allowed") is not False:
        errors.append("phase6_learning_write_allowed")
    if artifact.get("phase6_learning_write_allowed_count") != 0:
        errors.append("phase6_learning_write_allowed_count")
    errors.extend(_write_disabled_errors("knowledge_graph_staging", artifact))

    raw_payload_count = 0
    private_payload_count = 0
    local_path_count = 0
    secret_ref_count = 0
    seen_entry_ids: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append("staged_entry_invalid")
            continue
        entry_id = str(entry.get("staged_entry_id") or "")
        if entry_id in seen_entry_ids:
            errors.append(f"staged_entry_duplicate:{entry_id}")
        seen_entry_ids.add(entry_id)
        missing_entry_fields = sorted(set(ENTRY_REQUIRED_FIELDS) - set(entry))
        if missing_entry_fields:
            errors.append(
                f"staged_entry_missing_fields:{entry_id}:{','.join(missing_entry_fields)}"
            )
        if entry.get("graph_namespace") != TARGET_GRAPH_NAMESPACE:
            errors.append(f"staged_entry_namespace_invalid:{entry_id}")
        if entry.get("graph_subject") != TARGET_STRATEGY_FAMILY_KEY:
            errors.append(f"staged_entry_subject_invalid:{entry_id}")
        if entry.get("approval_ref") != SOURCE_APPROVAL_REF:
            errors.append(f"staged_entry_approval_ref_invalid:{entry_id}")
        if not entry.get("supersession_id"):
            errors.append(f"staged_entry_supersession_missing:{entry_id}")
        if not entry.get("rollback_ref"):
            errors.append(f"staged_entry_rollback_missing:{entry_id}")
        if entry.get("destructive_overwrite_allowed") is not False:
            errors.append(f"staged_entry_destructive_overwrite_allowed:{entry_id}")
        if entry.get("commit_allowed") is not False:
            errors.append(f"staged_entry_commit_allowed:{entry_id}")
        if entry.get("reference_only") is not True:
            errors.append(f"staged_entry_not_reference_only:{entry_id}")
        if entry.get("raw_payload_copied") is not False:
            errors.append(f"staged_entry_raw_payload_copied:{entry_id}")
            raw_payload_count += 1
        if entry.get("private_payload_copied") is not False:
            errors.append(f"staged_entry_private_payload_copied:{entry_id}")
            private_payload_count += 1
        for forbidden in ("payload", "raw_payload", "private_payload", "secret_value"):
            if forbidden in entry:
                errors.append(f"staged_entry_payload_field_forbidden:{entry_id}:{forbidden}")
        ref_errors = _source_ref_errors(f"staged_entry:{entry_id}", entry.get("source_refs"))
        errors.extend(ref_errors)
        if any(error.endswith("_local_source_ref") for error in ref_errors):
            local_path_count += 1
        if any(error.endswith("_secret_source_ref") for error in ref_errors):
            secret_ref_count += 1
        for field in (
            "learning_write_created",
            "knowledge_graph_write_created",
            "chroma_write_created",
            "graph_backend_write_created",
        ):
            if entry.get(field) is not False:
                errors.append(f"staged_entry_write_created:{entry_id}:{field}")

    for action in blocked_actions:
        if not isinstance(action, dict):
            errors.append("blocked_action_invalid")
            continue
        action_id = str(action.get("action_id") or "")
        if action.get("reference_only") is not True:
            errors.append(f"blocked_action_not_reference_only:{action_id}")
        if action.get("raw_payload_copied") is not False:
            errors.append(f"blocked_action_raw_payload_copied:{action_id}")
            raw_payload_count += 1
        if action.get("private_payload_copied") is not False:
            errors.append(f"blocked_action_private_payload_copied:{action_id}")
            private_payload_count += 1
        ref_errors = _source_ref_errors(f"blocked_action:{action_id}", action.get("source_refs"))
        errors.extend(ref_errors)
        if any(error.endswith("_local_source_ref") for error in ref_errors):
            local_path_count += 1
        if any(error.endswith("_secret_source_ref") for error in ref_errors):
            secret_ref_count += 1

    if artifact.get("raw_payload_copied_count") != raw_payload_count:
        errors.append("raw_payload_copied_count_mismatch")
    if artifact.get("raw_payload_copied_count") != 0:
        errors.append("raw_payload_copied_count_nonzero")
    if artifact.get("private_payload_copied_count") != private_payload_count:
        errors.append("private_payload_copied_count_mismatch")
    if artifact.get("private_payload_copied_count") != 0:
        errors.append("private_payload_copied_count_nonzero")
    if artifact.get("local_path_exposed_count") != local_path_count:
        errors.append("local_path_exposed_count_mismatch")
    if artifact.get("local_path_exposed_count") != 0:
        errors.append("local_path_exposed_count_nonzero")
    if artifact.get("secret_ref_exposed_count") != secret_ref_count:
        errors.append("secret_ref_exposed_count_mismatch")
    if artifact.get("secret_ref_exposed_count") != 0:
        errors.append("secret_ref_exposed_count_nonzero")
    if artifact.get("phase5_source_artifacts_mutated") is not False:
        errors.append("phase5_source_artifacts_mutated")
    if artifact.get("phase5_test_trades_count_for_phase7") is not False:
        errors.append("phase5_test_trades_count_for_phase7")
    if artifact.get("phase7_proof_credit_allowed") is not False:
        errors.append("phase7_proof_credit_allowed")
    for field in PHASE6_UNSAFE_COUNT_FIELDS:
        if int(artifact.get(field, 0) or 0) != 0:
            errors.append(f"knowledge_graph_staging_unsafe_count_nonzero:{field}")
    unsafe_total = sum(int(artifact.get(field, 0) or 0) for field in PHASE6_UNSAFE_COUNT_FIELDS)
    if artifact.get("unsafe_write_counter_total") != unsafe_total:
        errors.append("knowledge_graph_staging_unsafe_total_mismatch")
    if artifact.get("unsafe_write_counter_total") != 0:
        errors.append("knowledge_graph_staging_unsafe_total_nonzero")
    blockers = artifact.get("blockers", [])
    if not isinstance(blockers, list):
        errors.append("blockers_invalid")
        blockers = []
    if artifact.get("blocker_count") != len(blockers):
        errors.append("blocker_count_mismatch")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "Knowledge Graph staging gate only",
        "cannot create staged entries without approval",
        "cannot commit a Knowledge Graph write",
        "cannot write Chroma or graph backend state",
        "cannot mutate Phase 5 source artifacts",
        "cannot count Phase 5 test trades toward Phase 7 proof",
    ):
        if phrase not in boundary:
            errors.append("knowledge_graph_staging_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("knowledge_graph_staging_event_log_path_missing")
        if not str(artifact.get("event_log_correlation_id") or "").strip():
            errors.append("knowledge_graph_staging_event_correlation_missing")
        if artifact.get("event_log_event_count") != 1:
            errors.append("knowledge_graph_staging_event_log_count_mismatch")
    return sorted(set(errors))


def attach_phase6_knowledge_graph_staging_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(
        event_log_path or (_runtime_dir(settings) / PHASE6_KNOWLEDGE_GRAPH_STAGING_EVENT_LOG)
    )
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PHASE6_KNOWLEDGE_GRAPH_STAGING_EVENT_TYPE,
        PHASE6_KNOWLEDGE_GRAPH_STAGING_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "kg_write_state": output.get("kg_write_state"),
            "approval_state": output.get("approval_state"),
            "source_approved_action_count": output.get("source_approved_action_count"),
            "candidate_action_count": output.get("candidate_action_count"),
            "approved_kg_action_count": output.get("approved_kg_action_count"),
            "blocked_action_count": output.get("blocked_action_count"),
            "staged_entry_count": output.get("staged_entry_count"),
            "staged_write_allowed": output.get("staged_write_allowed"),
            "knowledge_graph_commit_allowed": output.get("knowledge_graph_commit_allowed"),
            "knowledge_graph_write_created": output.get("knowledge_graph_write_created"),
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
    output["validation_errors"] = validate_phase6_knowledge_graph_staging(output)
    if output["validation_errors"]:
        output["status"] = "error"
    return output, entry


def write_phase6_knowledge_graph_staging(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase6_knowledge_graph_staging_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase6_knowledge_graph_staging_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase6_knowledge_graph_staging(output)
        if output["validation_errors"]:
            output["status"] = "error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase6_knowledge_graph_staging(output)
    if output["validation_errors"]:
        output["status"] = "error"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE6_KNOWLEDGE_GRAPH_STAGING_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "kg_write_state": output.get("kg_write_state"),
        "approval_state": output.get("approval_state"),
        "candidate_action_count": output.get("candidate_action_count"),
        "approved_kg_action_count": output.get("approved_kg_action_count"),
        "blocked_action_count": output.get("blocked_action_count"),
        "staged_entry_count": output.get("staged_entry_count"),
        "staged_write_allowed": output.get("staged_write_allowed"),
        "knowledge_graph_commit_allowed": output.get("knowledge_graph_commit_allowed"),
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
