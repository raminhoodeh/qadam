"""Q6-9 learning approval ledger.

This stage creates the governance ledger that downstream learning stages must
consult before any Knowledge Graph write, model update, trust-score update, or
strategy-learning proposal can advance. It records proposed actions and defers
them pending explicit review; it does not grant approval or write authority.
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone
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
from orchestrator.phase6_outcome_linker import (
    PHASE6_OUTCOME_LINKER_RUNTIME_ARTIFACT,
    validate_phase6_outcome_linker,
)
from orchestrator.phase6_postmortem_reducer import (
    PHASE6_POSTMORTEM_REDUCER_RUNTIME_ARTIFACT,
    validate_phase6_postmortem_reducer,
)


PHASE6_LEARNING_APPROVAL_SCHEMA_VERSION = 1
PHASE6_LEARNING_APPROVAL_RUNTIME_ARTIFACT = "phase6_learning_approval_ledger.json"
PHASE6_LEARNING_APPROVAL_HISTORY = "phase6_learning_approval_ledger_history.jsonl"
PHASE6_LEARNING_APPROVAL_EVENT_LOG = "phase6_learning_approval_ledger_events.jsonl"
PHASE6_LEARNING_APPROVAL_EVENT_TYPE = "phase6_postmortem_review_recorded"
PHASE6_LEARNING_APPROVAL_COMPONENT = "phase6_learning_approval"

SOURCE_REVIEW_REF = f"data/runtime/{PHASE6_POSTMORTEM_REDUCER_RUNTIME_ARTIFACT}"
SOURCE_OUTCOME_LINK_REF = f"data/runtime/{PHASE6_OUTCOME_LINKER_RUNTIME_ARTIFACT}"

APPROVAL_DECISIONS: tuple[str, ...] = ("approved", "rejected", "deferred")
DOWNSTREAM_GATES: tuple[str, ...] = (
    "knowledge_graph_staged_write",
    "model_weight_update_proposal",
    "trust_score_update_proposal",
    "strategy_learning_proposal",
)
SAFE_APPROVAL_EVENT_LOG_REF = f"data/runtime/{PHASE6_LEARNING_APPROVAL_EVENT_LOG}"

PHASE6_LEARNING_APPROVAL_BOUNDARY = (
    "Q6-9 creates a governance approval ledger only. It can record proposed "
    "postmortem learning actions, explicit approval requirements, deferred "
    "actions, rejected actions, reviewer scope, and review expiry, but it "
    "cannot default-approve learning, cannot approve without reviewer and Event "
    "Log evidence, cannot write learning data, cannot write a Knowledge Graph, "
    "cannot stage Knowledge Graph writes, cannot propose model-weight updates, "
    "cannot propose trust-score updates, cannot propose strategy learning, "
    "cannot mutate policy, cannot mutate strategies, cannot mutate Phase 5 "
    "source artifacts, cannot call broker POST routes, cannot call Alpaca POST "
    "routes, cannot call live endpoints, cannot enable live capital, and cannot "
    "count Phase 5 test trades toward Phase 7 proof."
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


def _review_expiry(generated_at: str) -> str:
    return (datetime.fromisoformat(generated_at) + timedelta(days=14)).isoformat()


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


def phase6_learning_approval_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE6_LEARNING_APPROVAL_RUNTIME_ARTIFACT,
        runtime / PHASE6_LEARNING_APPROVAL_HISTORY,
        runtime / PHASE6_LEARNING_APPROVAL_EVENT_LOG,
    )


def _action_source_refs(record: dict[str, Any], outcome_link: dict[str, Any]) -> list[str]:
    refs: list[str] = [SOURCE_REVIEW_REF, SOURCE_OUTCOME_LINK_REF]
    for ref in _list(record.get("source_refs")):
        if isinstance(ref, str) and ref not in refs:
            refs.append(ref)
    outcome_ref = outcome_link.get("source_outcome_artifact_ref")
    if isinstance(outcome_ref, str) and outcome_ref not in refs:
        refs.append(outcome_ref)
    return refs


def _proposed_action(
    record: dict[str, Any],
    *,
    outcome_link: dict[str, Any],
    decision: str = "deferred",
) -> dict[str, Any]:
    packet_type = str(record.get("analysis_packet_type") or "")
    return {
        "action_id": f"q6-9-action:{packet_type}",
        "source_classification_id": record.get("classification_id"),
        "analysis_packet_type": packet_type,
        "proposed_classification": record.get("classification"),
        "approval_decision": decision,
        "approval_state": f"{decision}_pending_explicit_review",
        "review_required": True,
        "reviewer_label": None,
        "approval_logged": False,
        "source_refs": _action_source_refs(record, outcome_link),
        "scope": {
            "postmortem_review_ref": SOURCE_REVIEW_REF,
            "outcome_link_ref": SOURCE_OUTCOME_LINK_REF,
            "source_trade_ref": outcome_link.get("source_trade_ref"),
            "source_outcome_ref": outcome_link.get("source_outcome_ref"),
        },
        "downstream_gates": list(DOWNSTREAM_GATES),
        "knowledge_graph_staged_write_allowed": False,
        "model_weight_update_proposal_allowed": False,
        "trust_score_update_proposal_allowed": False,
        "strategy_learning_proposal_allowed": False,
        "learning_write_allowed": False,
        "learning_action_approved": False,
        "defer_reason": "explicit_governance_reviewer_and_event_log_required",
        "raw_payload_copied": False,
        "private_payload_copied": False,
        "reference_only": True,
    }


def explicitly_defer_phase6_learning_approval(
    artifact: dict[str, Any],
    *,
    reviewer_label: str,
    review_instruction: str,
) -> dict[str, Any]:
    """Record an explicit human deferral without opening downstream authority."""
    output = deepcopy(artifact)
    reviewed_at = _now()
    actions: list[dict[str, Any]] = []
    for action in _list(output.get("proposed_actions")):
        if not isinstance(action, dict):
            continue
        deferred_action = deepcopy(action)
        deferred_action["approval_decision"] = "deferred"
        deferred_action["approval_state"] = "deferred"
        deferred_action["review_required"] = True
        deferred_action["review_completed"] = True
        deferred_action["reviewed_at"] = reviewed_at
        deferred_action["reviewer_label"] = reviewer_label
        deferred_action["approval_logged"] = True
        deferred_action["approval_event_log_ref"] = SAFE_APPROVAL_EVENT_LOG_REF
        deferred_action["learning_action_approved"] = False
        deferred_action["defer_reason"] = "explicit_fund_manager_deferral"
        deferred_action["review_instruction"] = review_instruction
        for gate in (
            "knowledge_graph_staged_write_allowed",
            "model_weight_update_proposal_allowed",
            "trust_score_update_proposal_allowed",
            "strategy_learning_proposal_allowed",
            "learning_write_allowed",
        ):
            deferred_action[gate] = False
        deferred_action["reference_only"] = True
        deferred_action["raw_payload_copied"] = False
        deferred_action["private_payload_copied"] = False
        actions.append(deferred_action)

    output["status"] = "deferred"
    output["approval_state"] = "deferred"
    output["approval_logged"] = True
    output["approval_event_log_ref"] = SAFE_APPROVAL_EVENT_LOG_REF
    output["reviewer_label"] = reviewer_label
    output["reviewed_at"] = reviewed_at
    output["review_instruction"] = review_instruction
    output["review_decision"] = "deferred"
    output["explicit_deferral_logged"] = True
    output["default_approval_exists"] = False
    output["missing_approval_blocks_downstream"] = True
    output["proposed_actions"] = actions
    output["approved_actions"] = []
    output["approved_action_count"] = 0
    output["rejected_actions"] = []
    output["rejected_action_count"] = 0
    output["deferred_actions"] = actions
    output["deferred_action_count"] = len(actions)
    output["pending_review_action_count"] = 0
    output["learning_action_count"] = 0
    output["learning_action_approved_count"] = 0
    output["knowledge_graph_staged_write_allowed"] = False
    output["model_weight_update_proposal_allowed"] = False
    output["trust_score_update_proposal_allowed"] = False
    output["strategy_learning_proposal_allowed"] = False
    output["downstream_advance_allowed"] = False
    output["downstream_blocked_gate_count"] = len(DOWNSTREAM_GATES)
    output["downstream_blocked_gates"] = list(DOWNSTREAM_GATES)
    output["postmortem_approved"] = False
    output["learning_write_allowed"] = False
    output["learning_write_created"] = False
    output["knowledge_graph_write_created"] = False
    output["blockers"] = []
    output["blocker_count"] = 0
    output["validation_errors"] = validate_phase6_learning_approval(output)
    if output["validation_errors"]:
        output["status"] = "error"
    return output


def _proposed_actions(review: dict[str, Any], outcome_link: dict[str, Any]) -> list[dict[str, Any]]:
    records = [
        record
        for record in _list(review.get("classification_records"))
        if isinstance(record, dict)
    ]
    return [_proposed_action(record, outcome_link=outcome_link) for record in records]


def _provenance(
    review: dict[str, Any],
    outcome_link: dict[str, Any],
    actions: list[dict[str, Any]],
) -> dict[str, Any]:
    refs: list[str] = [SOURCE_REVIEW_REF, SOURCE_OUTCOME_LINK_REF]
    for source in (review, outcome_link):
        provenance = source.get("provenance", {})
        if isinstance(provenance, dict):
            for ref in provenance.get("source_refs", []):
                if isinstance(ref, str) and ref not in refs:
                    refs.append(ref)
    for action in actions:
        for ref in action.get("source_refs", []):
            if isinstance(ref, str) and ref not in refs:
                refs.append(ref)
    provenance = phase6_provenance(tuple(refs))
    provenance["execution_evidence_refs"] = [
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
    provenance["market_context_refs"] = [
        ref for ref in refs if any(marker in ref for marker in ("cockpit-status", "preference_"))
    ]
    provenance["model_interpretation_refs"] = [
        ref for ref in refs if "quantum_oracle_results" in ref
    ]
    provenance["governance_refs"] = [
        ref for ref in refs if any(marker in ref for marker in ("reduced_review", "approval"))
    ]
    return provenance


def build_phase6_learning_approval(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    review = _read_json(SOURCE_REVIEW_REF, settings) or {}
    outcome_link = _read_json(SOURCE_OUTCOME_LINK_REF, settings) or {}
    review_errors = validate_phase6_postmortem_reducer(review) if review else []
    outcome_link_errors = validate_phase6_outcome_linker(outcome_link) if outcome_link else []
    blockers: list[str] = []
    if not review:
        blockers.append("postmortem_review_missing")
    elif review.get("status") != "pending_review":
        blockers.append("postmortem_review_not_pending")
    if not outcome_link:
        blockers.append("outcome_link_missing")
    elif outcome_link.get("status") != "linked":
        blockers.append("outcome_link_not_linked")
    if review_errors:
        blockers.append("postmortem_review_validation_errors")
    if outcome_link_errors:
        blockers.append("outcome_link_validation_errors")
    actions = _proposed_actions(review, outcome_link) if not blockers else []
    if not actions:
        blockers.append("approval_actions_missing")

    authority = phase6_authority_ledger()
    authority["stage"] = "Q6-9"
    authority["boundary"] = PHASE6_LEARNING_APPROVAL_BOUNDARY
    status = "pending_review" if not blockers else "blocked"
    deferred_actions = actions
    artifact = {
        "schema_version": PHASE6_ARTIFACT_SCHEMA_VERSION,
        "phase6_learning_approval_schema_version": PHASE6_LEARNING_APPROVAL_SCHEMA_VERSION,
        "artifact_type": "learning_approval_record",
        "artifact_id": "phase6:q6-9:learning-approval:crude_oil_energy_security_disruption",
        "phase": "Q6",
        "stage": "Q6-9",
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
        "provenance": _provenance(review, outcome_link, actions),
        "boundary": PHASE6_LEARNING_APPROVAL_BOUNDARY,
        **phase6_authority_defaults(),
        **phase6_unsafe_counter_defaults(),
        **_disabled_write_fields(),
        "approval_state": "pending_review" if not blockers else "blocked",
        "approval_logged": False,
        "approval_event_log_ref": None,
        "reviewer_label": None,
        "review_scope": "postmortem_learning_actions",
        "review_due_at": _review_expiry(generated_at),
        "explicit_reviewer_required": True,
        "explicit_event_log_approval_required": True,
        "default_approval_exists": False,
        "missing_approval_blocks_downstream": True,
        "source_review_ref": SOURCE_REVIEW_REF,
        "source_review_status": review.get("status"),
        "source_review_state": review.get("review_state"),
        "source_outcome_link_ref": SOURCE_OUTCOME_LINK_REF,
        "source_outcome_link_status": outcome_link.get("status"),
        "source_trade_ref": outcome_link.get("source_trade_ref"),
        "source_outcome_ref": outcome_link.get("source_outcome_ref"),
        "proposed_actions": actions,
        "proposed_action_count": len(actions),
        "approved_actions": [],
        "approved_action_count": 0,
        "rejected_actions": [],
        "rejected_action_count": 0,
        "deferred_actions": deferred_actions,
        "deferred_action_count": len(deferred_actions),
        "pending_review_action_count": len(deferred_actions),
        "learning_action_count": 0,
        "learning_action_approved_count": 0,
        "knowledge_graph_staged_write_allowed": False,
        "model_weight_update_proposal_allowed": False,
        "trust_score_update_proposal_allowed": False,
        "strategy_learning_proposal_allowed": False,
        "downstream_advance_allowed": False,
        "downstream_blocked_gate_count": len(DOWNSTREAM_GATES),
        "downstream_blocked_gates": list(DOWNSTREAM_GATES),
        "postmortem_approved": False,
        "learning_write_allowed": False,
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
        "recommended_next_stage": "Q6-10 Knowledge Graph Staged Writes",
    }
    artifact["validation_errors"] = validate_phase6_learning_approval(artifact)
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


def validate_phase6_learning_approval(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schema_version",
        "phase6_learning_approval_schema_version",
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
        "approval_state",
        "approval_logged",
        "approval_event_log_ref",
        "reviewer_label",
        "review_scope",
        "review_due_at",
        "explicit_reviewer_required",
        "explicit_event_log_approval_required",
        "default_approval_exists",
        "missing_approval_blocks_downstream",
        "source_review_ref",
        "source_review_status",
        "source_review_state",
        "source_outcome_link_ref",
        "source_outcome_link_status",
        "source_trade_ref",
        "source_outcome_ref",
        "proposed_actions",
        "proposed_action_count",
        "approved_actions",
        "approved_action_count",
        "rejected_actions",
        "rejected_action_count",
        "deferred_actions",
        "deferred_action_count",
        "pending_review_action_count",
        "learning_action_count",
        "learning_action_approved_count",
        "learning_write_allowed",
        "knowledge_graph_staged_write_allowed",
        "model_weight_update_proposal_allowed",
        "trust_score_update_proposal_allowed",
        "strategy_learning_proposal_allowed",
        "downstream_advance_allowed",
        "downstream_blocked_gate_count",
        "downstream_blocked_gates",
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
        errors.append("learning_approval_missing_fields:" + ",".join(missing))
    if artifact.get("phase6_learning_approval_schema_version") != (
        PHASE6_LEARNING_APPROVAL_SCHEMA_VERSION
    ):
        errors.append("learning_approval_schema_version_mismatch")
    errors.extend(validate_phase6_artifact(artifact, expected_stage="Q6-9"))
    if artifact.get("artifact_type") != "learning_approval_record":
        errors.append("learning_approval_artifact_type_mismatch")
    if artifact.get("status") not in {"pending_review", "approved", "deferred", "rejected", "blocked", "error"}:
        errors.append("learning_approval_status_invalid")
    if artifact.get("approval_state") not in {"pending_review", "approved", "deferred", "rejected", "blocked"}:
        errors.append("approval_state_invalid")
    approval_state = artifact.get("approval_state")
    if approval_state == "approved":
        if artifact.get("approval_logged") is not True:
            errors.append("approval_without_event_log")
        if not artifact.get("reviewer_label"):
            errors.append("approval_without_reviewer")
        if not artifact.get("approval_event_log_ref"):
            errors.append("approval_event_log_ref_missing")
        if int(artifact.get("approved_action_count", 0) or 0) < 1:
            errors.append("approved_without_actions")
    elif approval_state == "deferred":
        if artifact.get("approval_logged") is not True:
            errors.append("deferred_without_event_log")
        if not artifact.get("reviewer_label"):
            errors.append("deferred_without_reviewer")
        if artifact.get("approval_event_log_ref") != SAFE_APPROVAL_EVENT_LOG_REF:
            errors.append("deferred_event_log_ref_missing")
        if artifact.get("approved_action_count") != 0:
            errors.append("deferred_approved_action_count_nonzero")
        if artifact.get("pending_review_action_count") != 0:
            errors.append("deferred_pending_review_action_count_nonzero")
        if artifact.get("deferred_action_count") != artifact.get("proposed_action_count"):
            errors.append("deferred_action_count_not_all_actions")
    else:
        if artifact.get("approval_logged") is not False:
            errors.append("approval_logged_without_approval")
        if artifact.get("reviewer_label") is not None:
            errors.append("reviewer_label_set_before_approval")
        if artifact.get("approval_event_log_ref") is not None:
            errors.append("approval_event_log_ref_set_before_approval")
    if artifact.get("default_approval_exists") is not False:
        errors.append("default_approval_exists")
    if artifact.get("explicit_reviewer_required") is not True:
        errors.append("explicit_reviewer_not_required")
    if artifact.get("explicit_event_log_approval_required") is not True:
        errors.append("explicit_event_log_approval_not_required")
    if artifact.get("missing_approval_blocks_downstream") is not True:
        errors.append("missing_approval_not_blocking_downstream")
    if artifact.get("source_review_ref") != SOURCE_REVIEW_REF:
        errors.append("source_review_ref_invalid")
    if artifact.get("source_review_status") != "pending_review":
        errors.append("source_review_status_invalid")
    if artifact.get("source_review_state") != "review_required":
        errors.append("source_review_state_invalid")
    if artifact.get("source_outcome_link_ref") != SOURCE_OUTCOME_LINK_REF:
        errors.append("source_outcome_link_ref_invalid")
    if artifact.get("source_outcome_link_status") != "linked":
        errors.append("source_outcome_link_status_invalid")
    if not artifact.get("source_trade_ref"):
        errors.append("source_trade_ref_missing")
    if not artifact.get("source_outcome_ref"):
        errors.append("source_outcome_ref_missing")
    if artifact.get("learning_write_allowed") is not False:
        errors.append("learning_write_allowed")
    if artifact.get("learning_write_created") is not False:
        errors.append("learning_write_created")
    errors.extend(_write_disabled_errors("learning_approval", artifact))
    if artifact.get("postmortem_approved") is not False:
        errors.append("postmortem_approved")
    if artifact.get("knowledge_graph_staged_write_allowed") is not False:
        errors.append("knowledge_graph_staged_write_allowed")
    if artifact.get("model_weight_update_proposal_allowed") is not False:
        errors.append("model_weight_update_proposal_allowed")
    if artifact.get("trust_score_update_proposal_allowed") is not False:
        errors.append("trust_score_update_proposal_allowed")
    if artifact.get("strategy_learning_proposal_allowed") is not False:
        errors.append("strategy_learning_proposal_allowed")
    if artifact.get("downstream_advance_allowed") is not False:
        errors.append("downstream_advance_allowed")
    if set(_list(artifact.get("downstream_blocked_gates"))) != set(DOWNSTREAM_GATES):
        errors.append("downstream_blocked_gates_invalid")
    if artifact.get("downstream_blocked_gate_count") != len(DOWNSTREAM_GATES):
        errors.append("downstream_blocked_gate_count_invalid")
    if artifact.get("learning_action_count") != 0:
        errors.append("learning_action_count_nonzero")
    if artifact.get("learning_action_approved_count") != 0:
        errors.append("learning_action_approved_count_nonzero")
    if artifact.get("approved_action_count") != len(_list(artifact.get("approved_actions"))):
        errors.append("approved_action_count_mismatch")
    if artifact.get("rejected_action_count") != len(_list(artifact.get("rejected_actions"))):
        errors.append("rejected_action_count_mismatch")
    if artifact.get("deferred_action_count") != len(_list(artifact.get("deferred_actions"))):
        errors.append("deferred_action_count_mismatch")
    actions = _list(artifact.get("proposed_actions"))
    approved_actions = _list(artifact.get("approved_actions"))
    rejected_actions = _list(artifact.get("rejected_actions"))
    deferred_actions = _list(artifact.get("deferred_actions"))
    if artifact.get("proposed_action_count") != len(actions):
        errors.append("proposed_action_count_mismatch")
    if artifact.get("proposed_action_count") < 1:
        errors.append("proposed_actions_missing")
    if artifact.get("approved_action_count") != 0:
        errors.append("approved_action_count_nonzero")
    if approved_actions:
        errors.append("approved_actions_present_without_explicit_approval")
    if artifact.get("rejected_action_count") != 0:
        errors.append("rejected_action_count_nonzero")
    if rejected_actions and artifact.get("approval_state") != "rejected":
        errors.append("rejected_actions_without_rejected_state")
    if artifact.get("deferred_action_count") != len(actions):
        errors.append("deferred_action_count_invalid")
    expected_pending_count = 0 if approval_state == "deferred" else len(deferred_actions)
    if artifact.get("pending_review_action_count") != expected_pending_count:
        errors.append("pending_review_action_count_mismatch")
    if {action.get("action_id") for action in actions} != {
        action.get("action_id") for action in deferred_actions
    }:
        errors.append("deferred_actions_do_not_match_proposed")
    raw_payload_count = 0
    private_payload_count = 0
    local_path_count = 0
    secret_ref_count = 0
    for action in actions:
        if not isinstance(action, dict):
            errors.append("proposed_action_invalid")
            continue
        action_id = str(action.get("action_id") or "")
        decision = action.get("approval_decision")
        if decision not in APPROVAL_DECISIONS:
            errors.append(f"approval_decision_invalid:{action_id}")
        if decision == "approved":
            errors.append(f"action_default_approved:{action_id}")
        if action.get("review_required") is not True:
            errors.append(f"action_review_not_required:{action_id}")
        if approval_state == "deferred":
            if action.get("approval_state") != "deferred":
                errors.append(f"action_deferred_state_missing:{action_id}")
            if action.get("reviewer_label") != artifact.get("reviewer_label"):
                errors.append(f"action_deferred_reviewer_mismatch:{action_id}")
            if action.get("approval_logged") is not True:
                errors.append(f"action_deferred_not_logged:{action_id}")
            if action.get("approval_event_log_ref") != SAFE_APPROVAL_EVENT_LOG_REF:
                errors.append(f"action_deferred_event_ref_missing:{action_id}")
        else:
            if action.get("reviewer_label") is not None:
                errors.append(f"action_reviewer_set_before_approval:{action_id}")
            if action.get("approval_logged") is not False:
                errors.append(f"action_approval_logged_before_approval:{action_id}")
        if action.get("learning_action_approved") is not False:
            errors.append(f"action_learning_approved:{action_id}")
        if action.get("learning_write_allowed") is not False:
            errors.append(f"action_learning_write_allowed:{action_id}")
        for gate in (
            "knowledge_graph_staged_write_allowed",
            "model_weight_update_proposal_allowed",
            "trust_score_update_proposal_allowed",
            "strategy_learning_proposal_allowed",
        ):
            if action.get(gate) is not False:
                errors.append(f"action_downstream_gate_allowed:{action_id}:{gate}")
        if set(_list(action.get("downstream_gates"))) != set(DOWNSTREAM_GATES):
            errors.append(f"action_downstream_gates_invalid:{action_id}")
        if action.get("reference_only") is not True:
            errors.append(f"action_not_reference_only:{action_id}")
        if action.get("raw_payload_copied") is not False:
            errors.append(f"action_raw_payload_copied:{action_id}")
            raw_payload_count += 1
        if action.get("private_payload_copied") is not False:
            errors.append(f"action_private_payload_copied:{action_id}")
            private_payload_count += 1
        for forbidden in ("payload", "raw_payload", "private_payload", "secret_value"):
            if forbidden in action:
                errors.append(f"action_payload_field_forbidden:{action_id}:{forbidden}")
        ref_errors = _source_ref_errors(f"action:{action_id}", action.get("source_refs"))
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
    if artifact.get("phase5_test_trades_count_for_phase7") is not False:
        errors.append("phase5_test_trades_count_for_phase7")
    if artifact.get("phase7_proof_credit_allowed") is not False:
        errors.append("phase7_proof_credit_allowed")
    for field in PHASE6_UNSAFE_COUNT_FIELDS:
        if int(artifact.get(field, 0) or 0) != 0:
            errors.append(f"learning_approval_unsafe_count_nonzero:{field}")
    unsafe_total = sum(int(artifact.get(field, 0) or 0) for field in PHASE6_UNSAFE_COUNT_FIELDS)
    if artifact.get("unsafe_write_counter_total") != unsafe_total:
        errors.append("learning_approval_unsafe_total_mismatch")
    if artifact.get("unsafe_write_counter_total") != 0:
        errors.append("learning_approval_unsafe_total_nonzero")
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
        "governance approval ledger only",
        "cannot default-approve learning",
        "cannot approve without reviewer and Event Log evidence",
        "cannot write learning data",
        "cannot write a Knowledge Graph",
        "cannot stage Knowledge Graph writes",
        "cannot propose model-weight updates",
        "cannot propose trust-score updates",
        "cannot propose strategy learning",
        "cannot count Phase 5 test trades toward Phase 7 proof",
    ):
        if phrase not in boundary:
            errors.append("learning_approval_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("learning_approval_event_log_path_missing")
        if not str(artifact.get("event_log_correlation_id") or "").strip():
            errors.append("learning_approval_event_correlation_missing")
        if artifact.get("event_log_event_count") != 1:
            errors.append("learning_approval_event_log_count_mismatch")
    return sorted(set(errors))


def attach_phase6_learning_approval_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(event_log_path or (_runtime_dir(settings) / PHASE6_LEARNING_APPROVAL_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PHASE6_LEARNING_APPROVAL_EVENT_TYPE,
        PHASE6_LEARNING_APPROVAL_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "approval_state": output.get("approval_state"),
            "approval_logged": output.get("approval_logged"),
            "reviewer_label": output.get("reviewer_label"),
            "source_review_state": output.get("source_review_state"),
            "source_outcome_link_status": output.get("source_outcome_link_status"),
            "proposed_action_count": output.get("proposed_action_count"),
            "approved_action_count": output.get("approved_action_count"),
            "rejected_action_count": output.get("rejected_action_count"),
            "deferred_action_count": output.get("deferred_action_count"),
            "downstream_advance_allowed": output.get("downstream_advance_allowed"),
            "downstream_blocked_gate_count": output.get("downstream_blocked_gate_count"),
            "learning_write_created": output.get("learning_write_created"),
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
    output["validation_errors"] = validate_phase6_learning_approval(output)
    if output["validation_errors"]:
        output["status"] = "error"
    return output, entry


def write_phase6_learning_approval(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase6_learning_approval_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase6_learning_approval_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase6_learning_approval(output)
        if output["validation_errors"]:
            output["status"] = "error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase6_learning_approval(output)
    if output["validation_errors"]:
        output["status"] = "error"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE6_LEARNING_APPROVAL_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "approval_state": output.get("approval_state"),
        "approval_logged": output.get("approval_logged"),
        "reviewer_label": output.get("reviewer_label"),
        "proposed_action_count": output.get("proposed_action_count"),
        "approved_action_count": output.get("approved_action_count"),
        "rejected_action_count": output.get("rejected_action_count"),
        "deferred_action_count": output.get("deferred_action_count"),
        "downstream_advance_allowed": output.get("downstream_advance_allowed"),
        "downstream_blocked_gate_count": output.get("downstream_blocked_gate_count"),
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
