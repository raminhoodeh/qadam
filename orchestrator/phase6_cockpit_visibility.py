"""Q6-16 cockpit and dashboard visibility for the Phase 6 Learning Loop.

This stage creates a public-safe, backend-derived visibility record for the
Learning Loop. It summarizes journal/postmortem state, approval state, staged
graph entries, model/trust proposals, shadow replay, and Architect
recommendations without exposing raw payloads, local paths, broker identifiers,
or granting any authority.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.phase6_artifacts import (
    PHASE6_ARTIFACT_SCHEMA_VERSION,
    PHASE6_AUTHORITY_FIELDS,
    PHASE6_UNSAFE_COUNT_FIELDS,
    phase6_authority_defaults,
    phase6_authority_ledger,
    phase6_event_contract,
    phase6_provenance,
    phase6_source_posture,
    phase6_unsafe_counter_defaults,
    validate_phase6_artifact,
)


PHASE6_COCKPIT_VISIBILITY_SCHEMA_VERSION = 1
PHASE6_COCKPIT_VISIBILITY_RUNTIME_ARTIFACT = "phase6_cockpit_learning_visibility.json"
PHASE6_COCKPIT_VISIBILITY_HISTORY = "phase6_cockpit_learning_visibility_history.jsonl"
PHASE6_COCKPIT_VISIBILITY_EVENT_LOG = "phase6_cockpit_learning_visibility_events.jsonl"
PHASE6_COCKPIT_VISIBILITY_EVENT_TYPE = "phase6_artifact_schema_recorded"
PHASE6_COCKPIT_VISIBILITY_COMPONENT = "phase6_cockpit_visibility"

SOURCE_REFS: dict[str, str] = {
    "readiness": "data/runtime/phase6_readiness.json",
    "source_intake": "data/runtime/phase6_learning_source_intake.json",
    "closed_trade_outcome": "data/runtime/phase6_closed_trade_outcome.json",
    "postmortem_review": "data/runtime/phase6_postmortem_reduced_review.json",
    "approval": "data/runtime/phase6_learning_approval_ledger.json",
    "knowledge_graph_staging": "data/runtime/phase6_knowledge_graph_staged_writes.json",
    "knowledge_graph_read_view": "data/runtime/phase6_knowledge_graph_read_view.json",
    "model_weight_updates": "data/runtime/phase6_model_weight_update_proposals.json",
    "trust_score_updates": "data/runtime/phase6_trust_score_update_proposals.json",
    "shadow_strategy_replay": "data/runtime/phase6_shadow_strategy_replay.json",
    "architect_learning": "data/runtime/phase6_architect_learning_summary.json",
}

PHASE6_COCKPIT_VISIBILITY_BOUNDARY = (
    "Q6-16 exposes a public-safe Learning Loop readout derived from backend "
    "artifacts only. It cannot infer readiness from the UI, cannot expose raw "
    "payloads, local paths, secrets, broker identifiers, or private source "
    "payloads, cannot write learning data, cannot write or commit a Knowledge "
    "Graph, cannot apply model weights, cannot apply trust scores, cannot "
    "mutate policy or strategies, cannot call broker POST routes, cannot call "
    "live endpoints, cannot enable live capital, and cannot grant Phase 7 "
    "proof credit."
)

PUBLIC_STATUS_FIELDS: tuple[str, ...] = (
    "schema_version",
    "phase6_cockpit_visibility_schema_version",
    "artifact_type",
    "artifact_id",
    "phase",
    "stage",
    "status",
    "visibility_state",
    "learning_state",
    "generated_at",
    "public_safe",
    "recorded",
    "backend_derived",
    "display_derived_from_backend",
    "ui_inferred_readiness_count",
    "backend_parity_error_count",
    "dashboard_panel_enabled",
    "dashboard_uses_backend_status",
    "event_log_required",
    "event_log_written",
    "event_log_event_count",
    "validation_error_count",
    "source_artifact_count",
    "source_validation_error_count",
    "source_missing_count",
    "postmortem_due_count",
    "postmortem_resolved_count",
    "closed_trade_outcome_count",
    "approval_state",
    "approval_logged",
    "postmortem_approved",
    "approved_action_count",
    "deferred_action_count",
    "explicitly_deferred_action_count",
    "pending_review_action_count",
    "learning_actions_review_satisfied",
    "staged_graph_entry_count",
    "knowledge_graph_read_result_count",
    "knowledge_graph_seed_result_count",
    "knowledge_graph_staged_result_count",
    "model_weight_proposal_count",
    "model_weight_active_proposal_count",
    "model_weight_blocked_proposal_count",
    "trust_score_proposal_count",
    "trust_score_active_proposal_count",
    "trust_score_blocked_proposal_count",
    "shadow_replay_variant_count",
    "shadow_replay_active_count",
    "shadow_replay_blocked_count",
    "architect_recommendation_count",
    "architect_active_recommendation_count",
    "architect_blocked_recommendation_count",
    "governance_pending_count",
    "blocked_authorities",
    "blocked_authority_count",
    "phase6_learning_write_allowed",
    "phase6_knowledge_graph_write_allowed",
    "phase6_model_weight_update_allowed",
    "phase6_trust_score_update_allowed",
    "phase6_shadow_strategy_runner_allowed",
    "phase6_architect_policy_mutation_allowed",
    "phase6_policy_mutation_allowed",
    "broker_write_allowed",
    "prediction_market_write_allowed",
    "live_capital_enabled",
    "phase7_proof_credit_allowed",
    "broker_post_called_count",
    "alpaca_post_called_count",
    "broker_write_allowed_count",
    "prediction_market_write_allowed_count",
    "crypto_perps_write_allowed_count",
    "live_endpoint_allowed_count",
    "live_capital_enabled_count",
    "phase7_proof_credit_allowed_count",
    "phase6_learning_write_allowed_count",
    "phase6_knowledge_graph_write_allowed_count",
    "phase6_model_weight_update_allowed_count",
    "phase6_trust_score_update_allowed_count",
    "phase6_policy_mutation_allowed_count",
    "raw_payload_exposed_count",
    "private_payload_exposed_count",
    "local_path_exposed_count",
    "secret_ref_exposed_count",
    "broker_identifier_exposed_count",
    "unsafe_write_counter_total",
    "source_status_records",
    "blockers",
    "blocker_count",
    "recommended_next_stage",
    "boundary",
)

SOURCE_STATUS_REQUIRED_FIELDS: tuple[str, ...] = (
    "source_key",
    "source_stage",
    "source_status",
    "backend_status",
    "display_status",
    "display_derived_from_backend",
    "ui_inferred_readiness",
    "source_ref",
    "public_safe",
    "recorded",
    "event_log_written",
    "validation_error_count",
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
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _has_local_path(ref: str) -> bool:
    if ref.startswith("/") or ref.startswith("~"):
        return True
    return len(ref) > 2 and ref[1:3] == ":\\"


def _source_status_record(source_key: str, source_ref: str, artifact: dict[str, Any] | None) -> dict[str, Any]:
    source_status = (artifact or {}).get("status", "missing")
    return {
        "source_key": source_key,
        "source_stage": (artifact or {}).get("stage", "missing"),
        "source_status": source_status,
        "backend_status": source_status,
        "display_status": source_status,
        "display_derived_from_backend": True,
        "ui_inferred_readiness": False,
        "source_ref": source_ref,
        "public_safe": (artifact or {}).get("public_safe") is True,
        "recorded": artifact is not None and (artifact or {}).get("recorded") is True,
        "event_log_written": (artifact or {}).get("event_log_written") is True,
        "validation_error_count": len((artifact or {}).get("validation_errors", []) or []),
    }


def _provenance(source_refs: tuple[str, ...]) -> dict[str, Any]:
    output = phase6_provenance(source_refs)
    output["execution_evidence_refs"] = [
        ref for ref in source_refs if any(marker in ref for marker in ("closed_trade", "outcome"))
    ]
    output["market_context_refs"] = [
        ref for ref in source_refs if any(marker in ref for marker in ("source_intake", "readiness"))
    ]
    output["model_interpretation_refs"] = [
        ref
        for ref in source_refs
        if any(marker in ref for marker in ("model_weight", "trust_score", "shadow_strategy"))
    ]
    output["governance_refs"] = [
        ref
        for ref in source_refs
        if any(marker in ref for marker in ("approval", "postmortem_reduced", "architect"))
    ]
    return output


def _learning_state(approval_state: str, due_count: int, resolved_count: int) -> str:
    if approval_state == "approved" and due_count > 0 and resolved_count >= due_count:
        return "approved_learning_visible"
    if approval_state in {"deferred", "rejected"}:
        return f"{approval_state}_learning_visible"
    return "blocked_pending_learning_approval"


def _public_status_from_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    output = {field: deepcopy(artifact.get(field)) for field in PUBLIC_STATUS_FIELDS if field in artifact}
    output["validation_error_count"] = len(artifact.get("validation_errors", []) or [])
    return output


def _refresh_validation(artifact: dict[str, Any]) -> dict[str, Any]:
    artifact.setdefault("validation_errors", [])
    artifact["public_status"] = _public_status_from_artifact(artifact)
    for _ in range(2):
        artifact["validation_errors"] = validate_phase6_cockpit_visibility(artifact)
        artifact["validation_error_count"] = len(artifact["validation_errors"])
        artifact["public_status"] = _public_status_from_artifact(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "blocked"
        artifact["public_status"] = _public_status_from_artifact(artifact)
    return artifact


def phase6_cockpit_visibility_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE6_COCKPIT_VISIBILITY_RUNTIME_ARTIFACT,
        runtime / PHASE6_COCKPIT_VISIBILITY_HISTORY,
        runtime / PHASE6_COCKPIT_VISIBILITY_EVENT_LOG,
    )


def build_phase6_cockpit_visibility(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    sources = {key: _read_json(ref, settings) for key, ref in SOURCE_REFS.items()}
    source_status_records = [
        _source_status_record(key, SOURCE_REFS[key], sources[key]) for key in SOURCE_REFS
    ]
    missing_source_count = len([record for record in source_status_records if record["source_status"] == "missing"])
    source_validation_error_count = sum(record["validation_error_count"] for record in source_status_records)
    source_refs = tuple(SOURCE_REFS.values())

    source_intake = sources["source_intake"] or {}
    closed_trade = sources["closed_trade_outcome"] or {}
    postmortem_review = sources["postmortem_review"] or {}
    approval = sources["approval"] or {}
    kg_staging = sources["knowledge_graph_staging"] or {}
    kg_read = sources["knowledge_graph_read_view"] or {}
    model_weight = sources["model_weight_updates"] or {}
    trust_score = sources["trust_score_updates"] or {}
    shadow_replay = sources["shadow_strategy_replay"] or {}
    architect = sources["architect_learning"] or {}

    postmortem_due_count = _int(source_intake.get("postmortem_due_count"))
    approval_state = str(approval.get("approval_state") or postmortem_review.get("approval_state") or "not_requested")
    postmortem_resolved_count = (
        postmortem_due_count
        if approval_state == "approved" and approval.get("postmortem_approved") is True
        else 0
    )
    learning_state = _learning_state(approval_state, postmortem_due_count, postmortem_resolved_count)
    visibility_state = f"backend_derived_{learning_state}"
    pending_review_action_count = approval.get("pending_review_action_count")
    if pending_review_action_count is None:
        pending_review_action_count = postmortem_review.get("pending_review_action_count")
    deferred_action_count = _int(approval.get("deferred_action_count"))
    blockers = []
    if missing_source_count:
        blockers.append("phase6_visibility_source_missing")
    if source_validation_error_count:
        blockers.append("phase6_visibility_source_validation_errors")

    authority = phase6_authority_ledger()
    authority["stage"] = "Q6-16"
    authority["boundary"] = PHASE6_COCKPIT_VISIBILITY_BOUNDARY
    blocked_authorities = list(PHASE6_AUTHORITY_FIELDS)
    artifact = {
        "schema_version": PHASE6_ARTIFACT_SCHEMA_VERSION,
        "phase6_cockpit_visibility_schema_version": PHASE6_COCKPIT_VISIBILITY_SCHEMA_VERSION,
        "artifact_type": "cockpit_learning_visibility",
        "artifact_id": "phase6:q6-16:cockpit-learning-visibility",
        "phase": "Q6",
        "stage": "Q6-16",
        "status": "visible" if not blockers else "blocked",
        "generated_at": generated_at,
        "public_safe": True,
        "recorded": False,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_event_count": 0,
        "validation_error_count": 0,
        "event_log_correlation_id": None,
        "event_log_created_at": None,
        "runtime_artifact_path": None,
        "history_log_path": None,
        "event_contract": phase6_event_contract("artifact_schema"),
        "authority_ledger": authority,
        "source_posture": phase6_source_posture(),
        "provenance": _provenance(source_refs),
        "boundary": PHASE6_COCKPIT_VISIBILITY_BOUNDARY,
        **phase6_authority_defaults(),
        **phase6_unsafe_counter_defaults(),
        "visibility_state": visibility_state,
        "learning_state": learning_state,
        "backend_derived": True,
        "display_derived_from_backend": True,
        "ui_inferred_readiness_count": 0,
        "backend_parity_error_count": 0,
        "dashboard_panel_enabled": True,
        "dashboard_uses_backend_status": True,
        "source_artifact_count": len(source_status_records),
        "source_validation_error_count": source_validation_error_count,
        "source_missing_count": missing_source_count,
        "source_status_records": source_status_records,
        "postmortem_due_count": postmortem_due_count,
        "postmortem_resolved_count": postmortem_resolved_count,
        "closed_trade_outcome_count": _int(closed_trade.get("outcome_record_count")),
        "approval_state": approval_state,
        "approval_logged": approval.get("approval_logged") is True,
        "postmortem_approved": approval.get("postmortem_approved") is True,
        "approved_action_count": _int(approval.get("approved_action_count")),
        "deferred_action_count": deferred_action_count,
        "explicitly_deferred_action_count": deferred_action_count,
        "pending_review_action_count": _int(pending_review_action_count),
        "learning_actions_review_satisfied": approval_state in {"approved", "deferred", "rejected"}
        and _int(pending_review_action_count) == 0,
        "staged_graph_entry_count": _int(kg_staging.get("staged_entry_count")),
        "knowledge_graph_read_result_count": _int(kg_read.get("result_count")),
        "knowledge_graph_seed_result_count": _int(kg_read.get("seed_result_count")),
        "knowledge_graph_staged_result_count": _int(kg_read.get("staged_result_count")),
        "model_weight_proposal_count": _int(model_weight.get("proposal_record_count")),
        "model_weight_active_proposal_count": _int(model_weight.get("active_proposal_count")),
        "model_weight_blocked_proposal_count": _int(model_weight.get("blocked_proposal_count")),
        "trust_score_proposal_count": _int(trust_score.get("proposal_record_count")),
        "trust_score_active_proposal_count": _int(trust_score.get("active_proposal_count")),
        "trust_score_blocked_proposal_count": _int(trust_score.get("blocked_proposal_count")),
        "shadow_replay_variant_count": _int(shadow_replay.get("variant_record_count")),
        "shadow_replay_active_count": _int(shadow_replay.get("active_replay_count")),
        "shadow_replay_blocked_count": _int(shadow_replay.get("blocked_replay_count")),
        "architect_recommendation_count": _int(architect.get("recommendation_count")),
        "architect_active_recommendation_count": _int(architect.get("active_recommendation_count")),
        "architect_blocked_recommendation_count": _int(architect.get("blocked_recommendation_count")),
        "governance_pending_count": _int(architect.get("governance_pending_count")),
        "blocked_authorities": blocked_authorities,
        "blocked_authority_count": len(blocked_authorities),
        "raw_payload_exposed_count": 0,
        "private_payload_exposed_count": 0,
        "local_path_exposed_count": 0,
        "secret_ref_exposed_count": 0,
        "broker_identifier_exposed_count": 0,
        "unsafe_write_counter_total": 0,
        "blockers": sorted(set(blockers)),
        "blocker_count": len(set(blockers)),
        "recommended_next_stage": "Q6-17 Phase 6 Certification",
    }
    return _refresh_validation(artifact)


def _public_safety_errors(payload: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            lowered = str(key).lower()
            if lowered in {"raw_payload", "private_payload", "broker_order_id", "external_order_id"}:
                errors.append(f"public_forbidden_key:{path}.{key}")
            errors.extend(_public_safety_errors(value, f"{path}.{key}"))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            errors.extend(_public_safety_errors(value, f"{path}[{index}]"))
    elif isinstance(payload, str):
        lowered = payload.lower()
        if _has_local_path(payload):
            errors.append(f"public_local_path:{path}")
        if (
            "api_key" in lowered
            or "bearer " in lowered
            or "secret_" in lowered
            or "token_" in lowered
            or "token=" in lowered
            or "secret=" in lowered
        ):
            errors.append(f"public_secret_ref:{path}")
        if any(marker in lowered for marker in ("broker_order_id", "external_order_id", "fill_id")):
            errors.append(f"public_broker_identifier:{path}")
    return errors


def validate_phase6_cockpit_visibility(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = set(PUBLIC_STATUS_FIELDS) | {
        "event_contract",
        "authority_ledger",
        "source_posture",
        "provenance",
        "public_status",
    }
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("cockpit_visibility_missing_fields:" + ",".join(missing))
    if artifact.get("phase6_cockpit_visibility_schema_version") != (
        PHASE6_COCKPIT_VISIBILITY_SCHEMA_VERSION
    ):
        errors.append("cockpit_visibility_schema_version_mismatch")
    errors.extend(validate_phase6_artifact(artifact, expected_stage="Q6-16"))
    if artifact.get("artifact_type") != "cockpit_learning_visibility":
        errors.append("cockpit_visibility_artifact_type_mismatch")
    if artifact.get("status") not in {"visible", "blocked"}:
        errors.append("cockpit_visibility_status_invalid")
    if artifact.get("backend_derived") is not True:
        errors.append("cockpit_visibility_not_backend_derived")
    if artifact.get("display_derived_from_backend") is not True:
        errors.append("cockpit_visibility_display_not_backend_derived")
    if artifact.get("dashboard_uses_backend_status") is not True:
        errors.append("cockpit_visibility_dashboard_not_backend_derived")
    if artifact.get("ui_inferred_readiness_count") != 0:
        errors.append("cockpit_visibility_ui_inferred_readiness")
    if artifact.get("backend_parity_error_count") != 0:
        errors.append("cockpit_visibility_backend_parity_error")
    if artifact.get("learning_state") not in {
        "blocked_pending_learning_approval",
        "approved_learning_visible",
        "deferred_learning_visible",
        "rejected_learning_visible",
    }:
        errors.append("cockpit_visibility_learning_state_invalid")
    if not str(artifact.get("visibility_state", "")).startswith("backend_derived_"):
        errors.append("cockpit_visibility_state_not_backend_derived")

    source_records = artifact.get("source_status_records", [])
    if not isinstance(source_records, list) or not source_records:
        errors.append("cockpit_visibility_source_records_missing")
        source_records = []
    if artifact.get("source_artifact_count") != len(source_records):
        errors.append("cockpit_visibility_source_count_mismatch")
    source_validation_error_count = 0
    source_missing_count = 0
    for record in source_records:
        if not isinstance(record, dict):
            errors.append("cockpit_visibility_source_record_invalid")
            continue
        missing_record = sorted(set(SOURCE_STATUS_REQUIRED_FIELDS) - set(record))
        if missing_record:
            errors.append("cockpit_visibility_source_record_missing:" + ",".join(missing_record))
        if record.get("display_status") != record.get("backend_status"):
            errors.append("cockpit_visibility_source_display_backend_mismatch")
        if record.get("display_derived_from_backend") is not True:
            errors.append("cockpit_visibility_source_display_not_backend_derived")
        if record.get("ui_inferred_readiness") is not False:
            errors.append("cockpit_visibility_source_ui_inferred")
        if str(record.get("source_ref", "")).startswith("data/runtime/") is False:
            errors.append("cockpit_visibility_source_ref_invalid")
        if _has_local_path(str(record.get("source_ref", ""))):
            errors.append("cockpit_visibility_source_ref_local_path")
        source_validation_error_count += _int(record.get("validation_error_count"))
        if record.get("source_status") == "missing":
            source_missing_count += 1
    if artifact.get("source_validation_error_count") != source_validation_error_count:
        errors.append("cockpit_visibility_source_validation_count_mismatch")
    if artifact.get("source_missing_count") != source_missing_count:
        errors.append("cockpit_visibility_source_missing_count_mismatch")

    if artifact.get("postmortem_due_count", 0) < artifact.get("postmortem_resolved_count", 0):
        errors.append("cockpit_visibility_postmortem_count_mismatch")
    if artifact.get("approval_state") != "approved" and artifact.get("postmortem_resolved_count") != 0:
        errors.append("cockpit_visibility_unapproved_resolved_postmortem")
    if artifact.get("approval_state") not in {"not_requested", "pending_review", "approved", "deferred", "rejected"}:
        errors.append("cockpit_visibility_approval_state_invalid")

    for field in PHASE6_AUTHORITY_FIELDS:
        if artifact.get(field) is not False:
            errors.append(f"cockpit_visibility_authority_enabled:{field}")
    if artifact.get("blocked_authority_count") != len(artifact.get("blocked_authorities", [])):
        errors.append("cockpit_visibility_blocked_authority_count_mismatch")
    if sorted(artifact.get("blocked_authorities", [])) != sorted(PHASE6_AUTHORITY_FIELDS):
        errors.append("cockpit_visibility_blocked_authorities_incomplete")

    unsafe_total = 0
    for field in PHASE6_UNSAFE_COUNT_FIELDS:
        value = _int(artifact.get(field))
        unsafe_total += value
        if value != 0:
            errors.append(f"cockpit_visibility_unsafe_count_nonzero:{field}")
    if artifact.get("unsafe_write_counter_total") != unsafe_total:
        errors.append("cockpit_visibility_unsafe_total_mismatch")
    for key in (
        "raw_payload_exposed_count",
        "private_payload_exposed_count",
        "local_path_exposed_count",
        "secret_ref_exposed_count",
        "broker_identifier_exposed_count",
    ):
        if artifact.get(key) != 0:
            errors.append(f"cockpit_visibility_exposure_count_nonzero:{key}")

    public_status = artifact.get("public_status")
    if not isinstance(public_status, dict):
        errors.append("cockpit_visibility_public_status_missing")
    else:
        extra = sorted(set(public_status) - set(PUBLIC_STATUS_FIELDS))
        if extra:
            errors.append("cockpit_visibility_public_status_extra_fields:" + ",".join(extra))
        for field in PUBLIC_STATUS_FIELDS:
            if field == "validation_error_count":
                continue
            if field in artifact and public_status.get(field) != artifact.get(field):
                errors.append(f"cockpit_visibility_public_status_mismatch:{field}")
        errors.extend(_public_safety_errors(public_status))
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "cannot infer readiness from the UI",
        "cannot expose raw payloads",
        "cannot write learning data",
        "cannot apply model weights",
        "cannot apply trust scores",
        "cannot mutate policy",
        "cannot call broker POST routes",
        "cannot enable live capital",
        "cannot grant Phase 7 proof credit",
    ):
        if phrase not in boundary:
            errors.append("cockpit_visibility_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not artifact.get("event_log_path"):
            errors.append("cockpit_visibility_event_log_path_missing")
        if not artifact.get("event_log_correlation_id"):
            errors.append("cockpit_visibility_event_correlation_missing")
        if artifact.get("event_log_event_count") != 1:
            errors.append("cockpit_visibility_event_log_count_mismatch")
    return sorted(set(errors))


def attach_phase6_cockpit_visibility_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(event_log_path or (_runtime_dir(settings) / PHASE6_COCKPIT_VISIBILITY_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PHASE6_COCKPIT_VISIBILITY_EVENT_TYPE,
        PHASE6_COCKPIT_VISIBILITY_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "visibility_state": output.get("visibility_state"),
            "learning_state": output.get("learning_state"),
            "backend_derived": output.get("backend_derived"),
            "ui_inferred_readiness_count": output.get("ui_inferred_readiness_count"),
            "postmortem_due_count": output.get("postmortem_due_count"),
            "postmortem_resolved_count": output.get("postmortem_resolved_count"),
            "approval_state": output.get("approval_state"),
            "staged_graph_entry_count": output.get("staged_graph_entry_count"),
            "model_weight_proposal_count": output.get("model_weight_proposal_count"),
            "trust_score_proposal_count": output.get("trust_score_proposal_count"),
            "architect_recommendation_count": output.get("architect_recommendation_count"),
            "blocked_authority_count": output.get("blocked_authority_count"),
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
    output = _refresh_validation(output)
    return output, entry


def write_phase6_cockpit_visibility(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase6_cockpit_visibility_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase6_cockpit_visibility_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output = _refresh_validation(output)
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output = _refresh_validation(output)
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE6_COCKPIT_VISIBILITY_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "visibility_state": output.get("visibility_state"),
        "learning_state": output.get("learning_state"),
        "backend_derived": output.get("backend_derived"),
        "ui_inferred_readiness_count": output.get("ui_inferred_readiness_count"),
        "postmortem_due_count": output.get("postmortem_due_count"),
        "postmortem_resolved_count": output.get("postmortem_resolved_count"),
        "approval_state": output.get("approval_state"),
        "staged_graph_entry_count": output.get("staged_graph_entry_count"),
        "model_weight_proposal_count": output.get("model_weight_proposal_count"),
        "trust_score_proposal_count": output.get("trust_score_proposal_count"),
        "architect_recommendation_count": output.get("architect_recommendation_count"),
        "blocked_authority_count": output.get("blocked_authority_count"),
        "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
        "blocker_count": output.get("blocker_count"),
        "event_log_written": output.get("event_log_written"),
        "event_log_event_count": output.get("event_log_event_count"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output


def phase6_cockpit_visibility_public_status(settings: Settings | None = None) -> dict[str, Any]:
    output_path, _, _ = phase6_cockpit_visibility_paths(settings)
    artifact = None
    if output_path.exists():
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        artifact = payload if isinstance(payload, dict) else None
    artifact = artifact or build_phase6_cockpit_visibility(settings=settings)
    validation_errors = validate_phase6_cockpit_visibility(artifact)
    public_status = _public_status_from_artifact(artifact)
    public_status["validation_error_count"] = len(validation_errors)
    return public_status
