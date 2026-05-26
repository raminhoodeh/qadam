"""Q6-11 Knowledge Graph read path.

This stage exposes a read-only, cockpit-safe view over Q6-10 staged-write
state. Because Q6-10 is currently blocked pending explicit learning approval,
the read path returns the guarded Q5E seed context but no approved learning
memory and no staged Knowledge Graph entries.
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
from orchestrator.phase6_knowledge_graph_staging import (
    PHASE6_KNOWLEDGE_GRAPH_STAGING_RUNTIME_ARTIFACT,
    TARGET_GRAPH_NAMESPACE,
    TARGET_STRATEGY_FAMILY_KEY,
    validate_phase6_knowledge_graph_staging,
)


PHASE6_KNOWLEDGE_GRAPH_READ_PATH_SCHEMA_VERSION = 1
PHASE6_KNOWLEDGE_GRAPH_READ_PATH_RUNTIME_ARTIFACT = "phase6_knowledge_graph_read_view.json"
PHASE6_KNOWLEDGE_GRAPH_READ_PATH_HISTORY = "phase6_knowledge_graph_read_view_history.jsonl"
PHASE6_KNOWLEDGE_GRAPH_READ_PATH_EVENT_LOG = "phase6_knowledge_graph_read_view_events.jsonl"
PHASE6_KNOWLEDGE_GRAPH_READ_PATH_EVENT_TYPE = "phase6_learning_write_staged"
PHASE6_KNOWLEDGE_GRAPH_READ_PATH_COMPONENT = "phase6_knowledge_graph_read_path"

SOURCE_STAGING_REF = f"data/runtime/{PHASE6_KNOWLEDGE_GRAPH_STAGING_RUNTIME_ARTIFACT}"

PHASE6_KNOWLEDGE_GRAPH_READ_PATH_BOUNDARY = (
    "Q6-11 creates a read-only Knowledge Graph view only. It can expose "
    "searchable staged-entry metadata and guarded Q5E seed context with source "
    "refs, approval state, supersession state, and confidence state, but it "
    "cannot create staged entries, cannot approve learning, cannot write "
    "learning data, cannot commit a Knowledge Graph write, cannot write Chroma "
    "or graph backend state, cannot update model weights, cannot update trust "
    "scores, cannot mutate policy, cannot mutate strategies, cannot mutate "
    "Phase 5 source artifacts, cannot call broker POST routes, cannot call "
    "Alpaca POST routes, cannot call live endpoints, cannot enable live "
    "capital, and cannot count Phase 5 test trades toward Phase 7 proof."
)

WRITE_DISABLED_FIELDS: tuple[str, ...] = (
    "write_allowed",
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

READ_RESULT_REQUIRED_FIELDS: tuple[str, ...] = (
    "result_id",
    "result_type",
    "graph_namespace",
    "graph_subject",
    "source_staging_ref",
    "source_staged_entry_id",
    "approval_ref",
    "approval_state",
    "supersession_state",
    "supersedes_ref",
    "supersession_id",
    "rollback_available",
    "confidence",
    "confidence_state",
    "source_refs",
    "search_terms",
    "summary",
    "approved_learning_entry",
    "staged_entry_available",
    "seed_context",
    "reference_only",
    "raw_payload_copied",
    "private_payload_copied",
    "write_allowed",
    "mutation_allowed",
    "commit_allowed",
)

COCKPIT_SAFE_STATUS_FIELDS: tuple[str, ...] = (
    "status",
    "read_view_state",
    "result_count",
    "seed_result_count",
    "staged_result_count",
    "approved_learning_entry_count",
    "source_staging_status",
    "source_approval_state",
    "source_staged_entry_count",
    "source_blocked_action_count",
    "write_allowed",
    "knowledge_graph_write_created",
    "phase7_proof_credit_allowed",
    "unsafe_write_counter_total",
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


def phase6_knowledge_graph_read_path_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE6_KNOWLEDGE_GRAPH_READ_PATH_RUNTIME_ARTIFACT,
        runtime / PHASE6_KNOWLEDGE_GRAPH_READ_PATH_HISTORY,
        runtime / PHASE6_KNOWLEDGE_GRAPH_READ_PATH_EVENT_LOG,
    )


def _safe_source_refs(refs: list[Any]) -> list[str]:
    safe_refs: list[str] = [SOURCE_STAGING_REF]
    for ref in refs:
        if isinstance(ref, str) and ref.startswith("data/") and ref not in safe_refs:
            safe_refs.append(ref)
    return safe_refs


def _staged_result(entry: dict[str, Any], staging: dict[str, Any]) -> dict[str, Any]:
    packet_type = str(entry.get("analysis_packet_type") or "unknown")
    source_refs = _safe_source_refs(_list(entry.get("source_refs")))
    return {
        "result_id": f"q6-11-read:{entry.get('staged_entry_id')}",
        "result_type": "staged_knowledge_graph_entry",
        "graph_namespace": entry.get("graph_namespace") or TARGET_GRAPH_NAMESPACE,
        "graph_subject": entry.get("graph_subject") or TARGET_STRATEGY_FAMILY_KEY,
        "source_staging_ref": SOURCE_STAGING_REF,
        "source_staged_entry_id": entry.get("staged_entry_id"),
        "source_action_id": entry.get("source_action_id"),
        "analysis_packet_type": packet_type,
        "approval_ref": entry.get("approval_ref") or staging.get("approval_ref"),
        "approval_state": staging.get("source_approval_state"),
        "supersession_state": "staged_pending_commit_validation",
        "supersedes_ref": entry.get("supersedes_ref"),
        "supersession_id": entry.get("supersession_id"),
        "rollback_available": True,
        "confidence": entry.get("confidence"),
        "confidence_state": "source_entry_confidence",
        "source_refs": source_refs,
        "search_terms": [
            TARGET_STRATEGY_FAMILY_KEY,
            packet_type,
            str(entry.get("outcome_classification") or ""),
            "q6-10",
            "staged",
        ],
        "summary": (
            f"Staged {packet_type} Knowledge Graph entry for "
            f"{TARGET_STRATEGY_FAMILY_KEY}; commit remains disabled."
        ),
        "approved_learning_entry": True,
        "staged_entry_available": True,
        "seed_context": False,
        "reference_only": True,
        "raw_payload_copied": False,
        "private_payload_copied": False,
        "write_allowed": False,
        "mutation_allowed": False,
        "commit_allowed": False,
    }


def _seed_result(staging: dict[str, Any]) -> dict[str, Any]:
    provenance = staging.get("provenance", {})
    refs = _list(provenance.get("source_refs")) if isinstance(provenance, dict) else []
    source_refs = _safe_source_refs(refs)
    return {
        "result_id": "q6-11-read:q5e-seed-context:crude_oil_energy_security_disruption",
        "result_type": "q5e_seed_learning_context",
        "graph_namespace": TARGET_GRAPH_NAMESPACE,
        "graph_subject": TARGET_STRATEGY_FAMILY_KEY,
        "source_staging_ref": SOURCE_STAGING_REF,
        "source_staged_entry_id": None,
        "source_action_id": None,
        "analysis_packet_type": "seed_context",
        "approval_ref": staging.get("approval_ref"),
        "approval_state": staging.get("source_approval_state"),
        "supersession_state": "not_staged_pending_approval",
        "supersedes_ref": None,
        "supersession_id": None,
        "rollback_available": staging.get("rollback_available") is True,
        "confidence": None,
        "confidence_state": "not_available_pending_approval",
        "source_refs": source_refs,
        "search_terms": [
            TARGET_STRATEGY_FAMILY_KEY,
            "q5e",
            "seed",
            "paper lifecycle",
            "crude oil",
            "energy security",
            "approval pending",
        ],
        "summary": (
            "Guarded Q5E seed context is visible for review, but it is not an "
            "approved learning-memory entry and cannot be used for proof credit."
        ),
        "approved_learning_entry": False,
        "staged_entry_available": False,
        "seed_context": True,
        "reference_only": True,
        "raw_payload_copied": False,
        "private_payload_copied": False,
        "write_allowed": False,
        "mutation_allowed": False,
        "commit_allowed": False,
    }


def _read_results(staging: dict[str, Any]) -> list[dict[str, Any]]:
    staged_entries = [
        entry for entry in _list(staging.get("staged_entries")) if isinstance(entry, dict)
    ]
    if staged_entries:
        return [_staged_result(entry, staging) for entry in staged_entries]
    if staging.get("candidate_action_count", 0):
        return [_seed_result(staging)]
    return []


def search_phase6_knowledge_graph_read_path(
    artifact: dict[str, Any],
    query: str,
) -> list[dict[str, Any]]:
    normalized = query.casefold().strip()
    results = [result for result in _list(artifact.get("read_results")) if isinstance(result, dict)]
    if not normalized:
        return deepcopy(results)
    tokens = [token for token in normalized.replace("_", " ").split() if token]
    matches: list[dict[str, Any]] = []
    for result in results:
        haystack = " ".join(
            [
                str(result.get("summary") or ""),
                " ".join(str(term) for term in _list(result.get("search_terms"))),
                str(result.get("graph_subject") or ""),
                str(result.get("analysis_packet_type") or ""),
            ]
        ).casefold()
        if all(token in haystack for token in tokens):
            matches.append(deepcopy(result))
    return matches


def _provenance(staging: dict[str, Any], results: list[dict[str, Any]]) -> dict[str, Any]:
    refs: list[str] = [SOURCE_STAGING_REF]
    provenance = staging.get("provenance", {})
    if isinstance(provenance, dict):
        for ref in provenance.get("source_refs", []):
            if isinstance(ref, str) and ref not in refs:
                refs.append(ref)
    for result in results:
        for ref in _list(result.get("source_refs")):
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


def _cockpit_safe_status(
    *,
    status: str,
    read_view_state: str,
    staging: dict[str, Any],
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "status": status,
        "read_view_state": read_view_state,
        "result_count": len(results),
        "seed_result_count": len([result for result in results if result.get("seed_context") is True]),
        "staged_result_count": len(
            [result for result in results if result.get("staged_entry_available") is True]
        ),
        "approved_learning_entry_count": len(
            [result for result in results if result.get("approved_learning_entry") is True]
        ),
        "source_staging_status": staging.get("status"),
        "source_approval_state": staging.get("source_approval_state"),
        "source_staged_entry_count": int(staging.get("staged_entry_count", 0) or 0),
        "source_blocked_action_count": int(staging.get("blocked_action_count", 0) or 0),
        "write_allowed": False,
        "knowledge_graph_write_created": False,
        "phase7_proof_credit_allowed": False,
        "unsafe_write_counter_total": 0,
    }


def build_phase6_knowledge_graph_read_path(
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    staging = _read_json(SOURCE_STAGING_REF, settings) or {}
    staging_errors = validate_phase6_knowledge_graph_staging(staging) if staging else []
    blockers: list[str] = []
    if not staging:
        blockers.append("knowledge_graph_staging_missing")
    elif staging.get("status") not in {"blocked", "staged"}:
        blockers.append("knowledge_graph_staging_status_invalid")
    if staging_errors:
        blockers.append("knowledge_graph_staging_validation_errors")
    results = _read_results(staging) if not blockers else []
    if not results:
        blockers.append("read_results_missing")
    status = "read_only" if not blockers else "blocked"
    read_view_state = (
        "read_only_staged_entries_available"
        if [result for result in results if result.get("staged_entry_available") is True]
        else "read_only_seed_context_available"
        if results
        else "blocked_no_readable_context"
    )
    authority = phase6_authority_ledger()
    authority["stage"] = "Q6-11"
    authority["boundary"] = PHASE6_KNOWLEDGE_GRAPH_READ_PATH_BOUNDARY
    search_queries = ("crude oil", "energy security", "paper lifecycle", "approval pending")
    query_results = {
        query: len(
            [
                result
                for result in results
                if result in search_phase6_knowledge_graph_read_path(
                    {"read_results": results},
                    query,
                )
            ]
        )
        for query in search_queries
    }
    artifact = {
        "schema_version": PHASE6_ARTIFACT_SCHEMA_VERSION,
        "phase6_knowledge_graph_read_path_schema_version": (
            PHASE6_KNOWLEDGE_GRAPH_READ_PATH_SCHEMA_VERSION
        ),
        "artifact_type": "knowledge_graph_read_view",
        "artifact_id": "phase6:q6-11:knowledge-graph-read-view:crude_oil_energy_security_disruption",
        "phase": "Q6",
        "stage": "Q6-11",
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
        "provenance": _provenance(staging, results),
        "boundary": PHASE6_KNOWLEDGE_GRAPH_READ_PATH_BOUNDARY,
        **phase6_authority_defaults(),
        **phase6_unsafe_counter_defaults(),
        **_disabled_write_fields(),
        "read_view_state": read_view_state,
        "source_staging_ref": SOURCE_STAGING_REF,
        "source_staging_status": staging.get("status"),
        "source_kg_write_state": staging.get("kg_write_state"),
        "source_approval_state": staging.get("source_approval_state"),
        "source_staged_entry_count": int(staging.get("staged_entry_count", 0) or 0),
        "source_blocked_action_count": int(staging.get("blocked_action_count", 0) or 0),
        "source_candidate_action_count": int(staging.get("candidate_action_count", 0) or 0),
        "source_missing_approval_blocks_staging": (
            staging.get("missing_approval_blocks_staging") is True
        ),
        "read_results": results,
        "result_count": len(results),
        "seed_result_count": len([result for result in results if result.get("seed_context") is True]),
        "staged_result_count": len(
            [result for result in results if result.get("staged_entry_available") is True]
        ),
        "approved_learning_entry_count": len(
            [result for result in results if result.get("approved_learning_entry") is True]
        ),
        "search_enabled": True,
        "search_query_count": len(search_queries),
        "search_queries": list(search_queries),
        "search_result_count_by_query": query_results,
        "cockpit_safe_status": _cockpit_safe_status(
            status=status,
            read_view_state=read_view_state,
            staging=staging,
            results=results,
        ),
        "write_allowed": False,
        "learning_write_allowed": False,
        "learning_write_created": False,
        "knowledge_graph_write_created": False,
        "knowledge_graph_commit_created": False,
        "chroma_write_created": False,
        "graph_backend_write_created": False,
        "raw_payload_copied_count": 0,
        "private_payload_copied_count": 0,
        "local_path_exposed_count": 0,
        "secret_ref_exposed_count": 0,
        "phase5_source_artifacts_mutated": False,
        "phase5_test_trades_count_for_phase7": False,
        "phase7_proof_credit_allowed": False,
        "unsafe_write_counter_total": 0,
        "blockers": sorted(set(blockers)),
        "blocker_count": len(set(blockers)),
        "recommended_next_stage": "Q6-12 Model Weight Update Proposals",
    }
    artifact["validation_errors"] = validate_phase6_knowledge_graph_read_path(artifact)
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


def validate_phase6_knowledge_graph_read_path(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schema_version",
        "phase6_knowledge_graph_read_path_schema_version",
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
        "read_view_state",
        "source_staging_ref",
        "source_staging_status",
        "source_kg_write_state",
        "source_approval_state",
        "source_staged_entry_count",
        "source_blocked_action_count",
        "source_candidate_action_count",
        "source_missing_approval_blocks_staging",
        "read_results",
        "result_count",
        "seed_result_count",
        "staged_result_count",
        "approved_learning_entry_count",
        "search_enabled",
        "search_query_count",
        "search_queries",
        "search_result_count_by_query",
        "cockpit_safe_status",
        "write_allowed",
        "learning_write_allowed",
        "learning_write_created",
        "knowledge_graph_write_created",
        "knowledge_graph_commit_created",
        "chroma_write_created",
        "graph_backend_write_created",
        "raw_payload_copied_count",
        "private_payload_copied_count",
        "local_path_exposed_count",
        "secret_ref_exposed_count",
        "phase5_source_artifacts_mutated",
        "phase5_test_trades_count_for_phase7",
        "phase7_proof_credit_allowed",
        "unsafe_write_counter_total",
        "blockers",
        "blocker_count",
    }
    missing = sorted(required_fields - set(artifact))
    if missing:
        errors.append("knowledge_graph_read_path_missing_fields:" + ",".join(missing))
    if artifact.get("phase6_knowledge_graph_read_path_schema_version") != (
        PHASE6_KNOWLEDGE_GRAPH_READ_PATH_SCHEMA_VERSION
    ):
        errors.append("knowledge_graph_read_path_schema_version_mismatch")
    errors.extend(validate_phase6_artifact(artifact, expected_stage="Q6-11"))
    if artifact.get("artifact_type") != "knowledge_graph_read_view":
        errors.append("knowledge_graph_read_path_artifact_type_mismatch")
    if artifact.get("status") not in {"read_only", "blocked", "error"}:
        errors.append("knowledge_graph_read_path_status_invalid")
    if artifact.get("source_staging_ref") != SOURCE_STAGING_REF:
        errors.append("source_staging_ref_invalid")
    if artifact.get("source_staging_status") not in {"blocked", "staged"}:
        errors.append("source_staging_status_invalid")
    if artifact.get("source_approval_state") not in {"pending_review", "approved", "deferred"}:
        errors.append("source_approval_state_invalid")
    if artifact.get("write_allowed") is not False:
        errors.append("write_allowed")
    if artifact.get("learning_write_allowed") is not False:
        errors.append("learning_write_allowed")
    errors.extend(_write_disabled_errors("knowledge_graph_read_path", artifact))

    results = _list(artifact.get("read_results"))
    if artifact.get("result_count") != len(results):
        errors.append("result_count_mismatch")
    if artifact.get("result_count", 0) < 1 and artifact.get("status") == "read_only":
        errors.append("read_only_without_results")
    seed_count = 0
    staged_count = 0
    approved_count = 0
    raw_payload_count = 0
    private_payload_count = 0
    local_path_count = 0
    secret_ref_count = 0
    seen_result_ids: set[str] = set()
    for result in results:
        if not isinstance(result, dict):
            errors.append("read_result_invalid")
            continue
        result_id = str(result.get("result_id") or "")
        if result_id in seen_result_ids:
            errors.append(f"read_result_duplicate:{result_id}")
        seen_result_ids.add(result_id)
        missing_result_fields = sorted(set(READ_RESULT_REQUIRED_FIELDS) - set(result))
        if missing_result_fields:
            errors.append(
                f"read_result_missing_fields:{result_id}:{','.join(missing_result_fields)}"
            )
        if result.get("graph_namespace") != TARGET_GRAPH_NAMESPACE:
            errors.append(f"read_result_namespace_invalid:{result_id}")
        if result.get("graph_subject") != TARGET_STRATEGY_FAMILY_KEY:
            errors.append(f"read_result_subject_invalid:{result_id}")
        if result.get("source_staging_ref") != SOURCE_STAGING_REF:
            errors.append(f"read_result_source_staging_ref_invalid:{result_id}")
        if result.get("seed_context") is True:
            seed_count += 1
            if result.get("approved_learning_entry") is not False:
                errors.append(f"seed_result_marked_approved:{result_id}")
            if result.get("staged_entry_available") is not False:
                errors.append(f"seed_result_marked_staged:{result_id}")
            if result.get("confidence") is not None:
                errors.append(f"seed_result_confidence_present:{result_id}")
        if result.get("staged_entry_available") is True:
            staged_count += 1
        if result.get("approved_learning_entry") is True:
            approved_count += 1
        if result.get("reference_only") is not True:
            errors.append(f"read_result_not_reference_only:{result_id}")
        if result.get("raw_payload_copied") is not False:
            errors.append(f"read_result_raw_payload_copied:{result_id}")
            raw_payload_count += 1
        if result.get("private_payload_copied") is not False:
            errors.append(f"read_result_private_payload_copied:{result_id}")
            private_payload_count += 1
        for forbidden in ("payload", "raw_payload", "private_payload", "secret_value"):
            if forbidden in result:
                errors.append(f"read_result_payload_field_forbidden:{result_id}:{forbidden}")
        ref_errors = _source_ref_errors(f"read_result:{result_id}", result.get("source_refs"))
        errors.extend(ref_errors)
        if any(error.endswith("_local_source_ref") for error in ref_errors):
            local_path_count += 1
        if any(error.endswith("_secret_source_ref") for error in ref_errors):
            secret_ref_count += 1
        for field in ("write_allowed", "mutation_allowed", "commit_allowed"):
            if result.get(field) is not False:
                errors.append(f"read_result_write_or_mutation_allowed:{result_id}:{field}")
    if artifact.get("seed_result_count") != seed_count:
        errors.append("seed_result_count_mismatch")
    if artifact.get("staged_result_count") != staged_count:
        errors.append("staged_result_count_mismatch")
    if artifact.get("approved_learning_entry_count") != approved_count:
        errors.append("approved_learning_entry_count_mismatch")
    if artifact.get("source_staging_status") == "blocked":
        if artifact.get("seed_result_count") < 1:
            errors.append("blocked_staging_seed_result_missing")
        if artifact.get("staged_result_count") != 0:
            errors.append("blocked_staging_staged_results_present")
        if artifact.get("approved_learning_entry_count") != 0:
            errors.append("blocked_staging_approved_results_present")
    if artifact.get("source_staging_status") == "staged":
        if artifact.get("staged_result_count") != artifact.get("source_staged_entry_count"):
            errors.append("staged_result_count_does_not_match_source")
    if artifact.get("search_enabled") is not True:
        errors.append("search_not_enabled")
    search_queries = _list(artifact.get("search_queries"))
    if artifact.get("search_query_count") != len(search_queries):
        errors.append("search_query_count_mismatch")
    query_counts = artifact.get("search_result_count_by_query", {})
    if not isinstance(query_counts, dict):
        errors.append("search_result_count_by_query_invalid")
        query_counts = {}
    for query in search_queries:
        if not isinstance(query, str):
            errors.append("search_query_invalid")
            continue
        actual = len(search_phase6_knowledge_graph_read_path(artifact, query))
        if query_counts.get(query) != actual:
            errors.append(f"search_query_count_invalid:{query}")
    if len(search_phase6_knowledge_graph_read_path(artifact, "crude oil")) < 1:
        errors.append("crude_oil_search_result_missing")
    if len(search_phase6_knowledge_graph_read_path(artifact, "paper lifecycle")) < 1:
        errors.append("paper_lifecycle_search_result_missing")

    cockpit_status = artifact.get("cockpit_safe_status")
    if not isinstance(cockpit_status, dict):
        errors.append("cockpit_safe_status_invalid")
        cockpit_status = {}
    unexpected_cockpit_fields = sorted(set(cockpit_status) - set(COCKPIT_SAFE_STATUS_FIELDS))
    if unexpected_cockpit_fields:
        errors.append("cockpit_safe_status_unexpected_fields:" + ",".join(unexpected_cockpit_fields))
    for forbidden in (
        "source_refs",
        "raw_payload",
        "private_payload",
        "local_path",
        "secret",
        "token",
        "api_key",
    ):
        if forbidden in cockpit_status:
            errors.append(f"cockpit_safe_status_forbidden_field:{forbidden}")
    for field in COCKPIT_SAFE_STATUS_FIELDS:
        if field not in cockpit_status:
            errors.append(f"cockpit_safe_status_field_missing:{field}")
    for field in (
        "status",
        "read_view_state",
        "result_count",
        "seed_result_count",
        "staged_result_count",
        "approved_learning_entry_count",
        "source_staging_status",
        "source_approval_state",
        "source_staged_entry_count",
        "source_blocked_action_count",
        "write_allowed",
        "knowledge_graph_write_created",
        "phase7_proof_credit_allowed",
        "unsafe_write_counter_total",
    ):
        if cockpit_status.get(field) != artifact.get(field) and field in artifact:
            errors.append(f"cockpit_safe_status_mismatch:{field}")
    if cockpit_status.get("source_staged_entry_count") != artifact.get("source_staged_entry_count"):
        errors.append("cockpit_safe_status_mismatch:source_staged_entry_count")
    if cockpit_status.get("source_blocked_action_count") != artifact.get("source_blocked_action_count"):
        errors.append("cockpit_safe_status_mismatch:source_blocked_action_count")

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
            errors.append(f"knowledge_graph_read_path_unsafe_count_nonzero:{field}")
    unsafe_total = sum(int(artifact.get(field, 0) or 0) for field in PHASE6_UNSAFE_COUNT_FIELDS)
    if artifact.get("unsafe_write_counter_total") != unsafe_total:
        errors.append("knowledge_graph_read_path_unsafe_total_mismatch")
    if artifact.get("unsafe_write_counter_total") != 0:
        errors.append("knowledge_graph_read_path_unsafe_total_nonzero")
    blockers = artifact.get("blockers", [])
    if not isinstance(blockers, list):
        errors.append("blockers_invalid")
        blockers = []
    if artifact.get("blocker_count") != len(blockers):
        errors.append("blocker_count_mismatch")
    if artifact.get("status") == "read_only" and blockers:
        errors.append("read_only_with_blockers")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "read-only Knowledge Graph view only",
        "cannot create staged entries",
        "cannot approve learning",
        "cannot write learning data",
        "cannot commit a Knowledge Graph write",
        "cannot write Chroma or graph backend state",
        "cannot mutate Phase 5 source artifacts",
        "cannot count Phase 5 test trades toward Phase 7 proof",
    ):
        if phrase not in boundary:
            errors.append("knowledge_graph_read_path_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("knowledge_graph_read_path_event_log_path_missing")
        if not str(artifact.get("event_log_correlation_id") or "").strip():
            errors.append("knowledge_graph_read_path_event_correlation_missing")
        if artifact.get("event_log_event_count") != 1:
            errors.append("knowledge_graph_read_path_event_log_count_mismatch")
    return sorted(set(errors))


def attach_phase6_knowledge_graph_read_path_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(
        event_log_path or (_runtime_dir(settings) / PHASE6_KNOWLEDGE_GRAPH_READ_PATH_EVENT_LOG)
    )
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PHASE6_KNOWLEDGE_GRAPH_READ_PATH_EVENT_TYPE,
        PHASE6_KNOWLEDGE_GRAPH_READ_PATH_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "read_view_state": output.get("read_view_state"),
            "source_staging_status": output.get("source_staging_status"),
            "source_approval_state": output.get("source_approval_state"),
            "result_count": output.get("result_count"),
            "seed_result_count": output.get("seed_result_count"),
            "staged_result_count": output.get("staged_result_count"),
            "approved_learning_entry_count": output.get("approved_learning_entry_count"),
            "write_allowed": output.get("write_allowed"),
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
    output["validation_errors"] = validate_phase6_knowledge_graph_read_path(output)
    if output["validation_errors"]:
        output["status"] = "error"
    return output, entry


def write_phase6_knowledge_graph_read_path(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase6_knowledge_graph_read_path_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase6_knowledge_graph_read_path_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase6_knowledge_graph_read_path(output)
        if output["validation_errors"]:
            output["status"] = "error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase6_knowledge_graph_read_path(output)
    if output["validation_errors"]:
        output["status"] = "error"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE6_KNOWLEDGE_GRAPH_READ_PATH_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "read_view_state": output.get("read_view_state"),
        "source_staging_status": output.get("source_staging_status"),
        "source_approval_state": output.get("source_approval_state"),
        "result_count": output.get("result_count"),
        "seed_result_count": output.get("seed_result_count"),
        "staged_result_count": output.get("staged_result_count"),
        "approved_learning_entry_count": output.get("approved_learning_entry_count"),
        "write_allowed": output.get("write_allowed"),
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
