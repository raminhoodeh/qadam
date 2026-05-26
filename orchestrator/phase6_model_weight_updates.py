"""Q6-12 model-weight update proposals.

This stage prepares the proposal surface for Bayesian model-weight changes, but
the current Q6-9 approval ledger has not approved any learning actions. The
artifact therefore records a blocked, no-op proposal record with before/after
weights and an audit trail while preserving active strategy weights unchanged.
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
from orchestrator.phase6_knowledge_graph_read_path import (
    PHASE6_KNOWLEDGE_GRAPH_READ_PATH_RUNTIME_ARTIFACT,
    validate_phase6_knowledge_graph_read_path,
)
from orchestrator.phase6_knowledge_graph_staging import TARGET_STRATEGY_FAMILY_KEY


PHASE6_MODEL_WEIGHT_UPDATES_SCHEMA_VERSION = 1
PHASE6_MODEL_WEIGHT_UPDATES_RUNTIME_ARTIFACT = "phase6_model_weight_update_proposals.json"
PHASE6_MODEL_WEIGHT_UPDATES_HISTORY = "phase6_model_weight_update_proposals_history.jsonl"
PHASE6_MODEL_WEIGHT_UPDATES_EVENT_LOG = "phase6_model_weight_update_proposals_events.jsonl"
PHASE6_MODEL_WEIGHT_UPDATES_EVENT_TYPE = "phase6_model_weight_update_proposed"
PHASE6_MODEL_WEIGHT_UPDATES_COMPONENT = "phase6_model_weight_updates"

SOURCE_READ_PATH_REF = f"data/runtime/{PHASE6_KNOWLEDGE_GRAPH_READ_PATH_RUNTIME_ARTIFACT}"
SOURCE_STRATEGY_UNIVERSE_REF = "data/runtime/phase4_candidate_strategy_universe.json"

PHASE6_MODEL_WEIGHT_UPDATES_BOUNDARY = (
    "Q6-12 creates model-weight update proposals only. It can compute a "
    "source-cited before/after proposal from explicitly approved postmortem "
    "learning evidence, or record a blocked no-op proposal when approval is "
    "missing, but it cannot apply model weights, cannot mutate active strategy "
    "artifacts, cannot write learning data, cannot write or commit a Knowledge "
    "Graph, cannot write Chroma or graph backend state, cannot update trust "
    "scores, cannot mutate policy, cannot mutate strategies, cannot mutate "
    "Phase 5 source artifacts, cannot call broker POST routes, cannot call "
    "Alpaca POST routes, cannot call live endpoints, cannot enable live "
    "capital, and cannot count Phase 5 test trades toward Phase 7 proof."
)

MODEL_WEIGHT_EVIDENCE_MAP: dict[str, str] = {
    "catalyst_analysis": "signal_integrity_patterns",
    "pricing_analysis": "data_veracity",
    "regime_analysis": "world_model_lens",
    "execution_analysis": "resource_registry",
    "override_analysis": "strategy_lead_challenges",
}

WRITE_DISABLED_FIELDS: tuple[str, ...] = (
    "apply_allowed",
    "model_weight_update_allowed",
    "model_weight_update_proposal_allowed",
    "model_weight_update_proposed",
    "model_weight_update_applied",
    "active_model_weight_mutated",
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

PROPOSAL_RECORD_REQUIRED_FIELDS: tuple[str, ...] = (
    "proposal_id",
    "proposal_state",
    "strategy_family_key",
    "model_weight_key",
    "source_result_id",
    "source_analysis_packet_type",
    "source_approval_state",
    "source_refs",
    "before_weight",
    "after_weight",
    "weight_delta",
    "bayesian_prior",
    "evidence_likelihood",
    "posterior_multiplier",
    "approved_learning_entry",
    "model_weight_update_proposal_allowed",
    "apply_allowed",
    "model_weight_update_applied",
    "active_model_weight_mutated",
    "reference_only",
    "raw_payload_copied",
    "private_payload_copied",
    "rationale",
)

COCKPIT_SAFE_STATUS_FIELDS: tuple[str, ...] = (
    "status",
    "proposal_state",
    "source_read_path_status",
    "source_approval_state",
    "proposal_record_count",
    "active_proposal_count",
    "blocked_proposal_count",
    "approved_evidence_count",
    "bayesian_update_count",
    "apply_allowed",
    "model_weight_update_applied",
    "active_model_weight_mutated",
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


def phase6_model_weight_updates_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE6_MODEL_WEIGHT_UPDATES_RUNTIME_ARTIFACT,
        runtime / PHASE6_MODEL_WEIGHT_UPDATES_HISTORY,
        runtime / PHASE6_MODEL_WEIGHT_UPDATES_EVENT_LOG,
    )


def _strategy_candidate(strategy_universe: dict[str, Any]) -> dict[str, Any]:
    for candidate in _list(strategy_universe.get("candidates")):
        if not isinstance(candidate, dict):
            continue
        if candidate.get("candidate_key") == TARGET_STRATEGY_FAMILY_KEY:
            return candidate
    return {}


def _weights(strategy_universe: dict[str, Any]) -> dict[str, float]:
    candidate = _strategy_candidate(strategy_universe)
    model_weights = candidate.get("model_weights") if isinstance(candidate, dict) else {}
    if not isinstance(model_weights, dict):
        return {}
    output: dict[str, float] = {}
    for key, value in model_weights.items():
        if isinstance(key, str) and isinstance(value, int | float):
            output[key] = round(float(value), 6)
    return dict(sorted(output.items()))


def _zero_delta(weights: dict[str, float]) -> dict[str, float]:
    return {key: 0.0 for key in weights}


def _weight_sum(weights: dict[str, float]) -> float:
    return round(sum(float(value) for value in weights.values()), 6)


def _normalised(weights: dict[str, float]) -> dict[str, float]:
    total = sum(max(0.0, float(value)) for value in weights.values())
    if total <= 0:
        return dict(weights)
    return {key: round(max(0.0, float(value)) / total, 6) for key, value in weights.items()}


def _safe_source_refs(refs: list[Any]) -> list[str]:
    safe_refs = [SOURCE_READ_PATH_REF, SOURCE_STRATEGY_UNIVERSE_REF]
    for ref in refs:
        if isinstance(ref, str) and ref.startswith("data/") and ref not in safe_refs:
            safe_refs.append(ref)
    return safe_refs


def _source_refs(read_view: dict[str, Any]) -> list[str]:
    refs: list[Any] = [SOURCE_READ_PATH_REF, SOURCE_STRATEGY_UNIVERSE_REF]
    provenance = read_view.get("provenance")
    if isinstance(provenance, dict):
        refs.extend(_list(provenance.get("source_refs")))
    for result in _list(read_view.get("read_results")):
        if isinstance(result, dict):
            refs.extend(_list(result.get("source_refs")))
    return _safe_source_refs(refs)


def _proposal_gate_open(read_view: dict[str, Any]) -> bool:
    if read_view.get("status") != "read_only":
        return False
    if read_view.get("source_approval_state") != "approved":
        return False
    if int(read_view.get("approved_learning_entry_count", 0) or 0) <= 0:
        return False
    if int(read_view.get("staged_result_count", 0) or 0) <= 0:
        return False
    return True


def _approved_results(read_view: dict[str, Any]) -> list[dict[str, Any]]:
    if not _proposal_gate_open(read_view):
        return []
    return [
        result
        for result in _list(read_view.get("read_results"))
        if isinstance(result, dict)
        and result.get("approved_learning_entry") is True
        and result.get("staged_entry_available") is True
    ]


def _blocked_record(
    *,
    before_weight: dict[str, float],
    read_view: dict[str, Any],
    source_refs: list[str],
) -> dict[str, Any]:
    return {
        "proposal_id": "q6-12-model-weight-proposal:blocked-pending-learning-approval",
        "proposal_state": "blocked_pending_learning_approval",
        "strategy_family_key": TARGET_STRATEGY_FAMILY_KEY,
        "model_weight_key": "all_model_weights",
        "source_result_id": "q6-11-read:q5e-seed-context:crude_oil_energy_security_disruption",
        "source_analysis_packet_type": "seed_context",
        "source_approval_state": read_view.get("source_approval_state"),
        "source_refs": source_refs,
        "before_weight": before_weight,
        "after_weight": before_weight,
        "weight_delta": _zero_delta(before_weight),
        "bayesian_prior": None,
        "evidence_likelihood": None,
        "posterior_multiplier": 1.0,
        "approved_learning_entry": False,
        "model_weight_update_proposal_allowed": False,
        "apply_allowed": False,
        "model_weight_update_applied": False,
        "active_model_weight_mutated": False,
        "reference_only": True,
        "raw_payload_copied": False,
        "private_payload_copied": False,
        "rationale": (
            "Q6-9 approval is still pending, so Q6-12 records before/after "
            "weights with zero delta and blocks Bayesian model-weight proposal "
            "generation."
        ),
    }


def _classification_direction(result: dict[str, Any]) -> float:
    classification = str(result.get("outcome_classification") or "").lower()
    if classification == "useful":
        return 1.0
    if classification == "harmful":
        return -1.0
    return 0.0


def _confidence(result: dict[str, Any]) -> float:
    value = result.get("confidence")
    if isinstance(value, int | float):
        return max(0.0, min(1.0, float(value)))
    return 0.0


def _active_records(
    *,
    before_weight: dict[str, float],
    read_view: dict[str, Any],
    source_refs: list[str],
) -> tuple[list[dict[str, Any]], dict[str, float], dict[str, float]]:
    working = dict(before_weight)
    records: list[dict[str, Any]] = []
    for result in _approved_results(read_view):
        packet_type = str(result.get("analysis_packet_type") or "unknown")
        weight_key = MODEL_WEIGHT_EVIDENCE_MAP.get(packet_type)
        if weight_key not in working:
            continue
        prior = float(working[weight_key])
        confidence = _confidence(result)
        direction = _classification_direction(result)
        likelihood = round(1.0 + (direction * confidence * 0.08), 6)
        proposed_unscaled = max(0.0, prior * likelihood)
        working[weight_key] = proposed_unscaled
        records.append(
            {
                "proposal_id": f"q6-12-model-weight-proposal:{packet_type}",
                "proposal_state": "proposal_ready_pending_apply_approval",
                "strategy_family_key": TARGET_STRATEGY_FAMILY_KEY,
                "model_weight_key": weight_key,
                "source_result_id": result.get("result_id"),
                "source_analysis_packet_type": packet_type,
                "source_approval_state": read_view.get("source_approval_state"),
                "source_refs": _safe_source_refs(_list(result.get("source_refs")) + source_refs),
                "before_weight": round(prior, 6),
                "after_weight": None,
                "weight_delta": None,
                "bayesian_prior": round(prior, 6),
                "evidence_likelihood": likelihood,
                "posterior_multiplier": likelihood,
                "approved_learning_entry": True,
                "model_weight_update_proposal_allowed": True,
                "apply_allowed": False,
                "model_weight_update_applied": False,
                "active_model_weight_mutated": False,
                "reference_only": True,
                "raw_payload_copied": False,
                "private_payload_copied": False,
                "rationale": (
                    f"{packet_type} has approved evidence, so Q6-12 can propose "
                    f"a Bayesian delta for {weight_key}; application remains "
                    "disabled."
                ),
            }
        )
    after_weight = _normalised(working)
    delta = {
        key: round(float(after_weight.get(key, 0.0)) - float(before_weight.get(key, 0.0)), 6)
        for key in before_weight
    }
    for record in records:
        key = str(record["model_weight_key"])
        record["after_weight"] = after_weight.get(key)
        record["weight_delta"] = delta.get(key)
    return records, after_weight, delta


def _provenance(read_view: dict[str, Any], source_refs: list[str]) -> dict[str, Any]:
    output = phase6_provenance(source_refs)
    output["execution_evidence_refs"] = [
        ref
        for ref in source_refs
        if any(marker in ref for marker in ("paper", "closed_trade", "outcome_links"))
    ]
    output["market_context_refs"] = [
        ref for ref in source_refs if any(marker in ref for marker in ("cockpit-status", "preference_"))
    ]
    output["model_interpretation_refs"] = [
        ref for ref in source_refs if "quantum_oracle_results" in ref
    ]
    output["governance_refs"] = [
        ref
        for ref in source_refs
        if any(marker in ref for marker in ("approval", "reduced_review", "read_view"))
    ]
    if read_view.get("event_log_path"):
        output["governance_refs"] = sorted(
            set(output["governance_refs"] + [str(read_view["event_log_path"])])
        )
    return output


def _cockpit_safe_status(
    *,
    status: str,
    proposal_state: str,
    read_view: dict[str, Any],
    records: list[dict[str, Any]],
    bayesian_update_count: int,
) -> dict[str, Any]:
    return {
        "status": status,
        "proposal_state": proposal_state,
        "source_read_path_status": read_view.get("status"),
        "source_approval_state": read_view.get("source_approval_state"),
        "proposal_record_count": len(records),
        "active_proposal_count": len(
            [record for record in records if record.get("model_weight_update_proposal_allowed") is True]
        ),
        "blocked_proposal_count": len(
            [record for record in records if record.get("proposal_state") == "blocked_pending_learning_approval"]
        ),
        "approved_evidence_count": int(read_view.get("approved_learning_entry_count", 0) or 0),
        "bayesian_update_count": bayesian_update_count,
        "apply_allowed": False,
        "model_weight_update_applied": False,
        "active_model_weight_mutated": False,
        "phase7_proof_credit_allowed": False,
        "unsafe_write_counter_total": 0,
    }


def build_phase6_model_weight_updates(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    read_view = _read_json(SOURCE_READ_PATH_REF, settings) or {}
    strategy_universe = _read_json(SOURCE_STRATEGY_UNIVERSE_REF, settings) or {}
    read_view_errors = validate_phase6_knowledge_graph_read_path(read_view) if read_view else []
    before_weight = _weights(strategy_universe)
    blockers: list[str] = []
    if not read_view:
        blockers.append("knowledge_graph_read_path_missing")
    elif read_view.get("status") != "read_only":
        blockers.append("knowledge_graph_read_path_not_read_only")
    if read_view_errors:
        blockers.append("knowledge_graph_read_path_validation_errors")
    if not before_weight:
        blockers.append("strategy_model_weights_missing")
    source_refs = _source_refs(read_view)
    gate_open = not blockers and _proposal_gate_open(read_view)
    if gate_open:
        records, after_weight, weight_delta = _active_records(
            before_weight=before_weight,
            read_view=read_view,
            source_refs=source_refs,
        )
        if not records:
            blockers.append("approved_learning_evidence_missing")
            gate_open = False
    if not gate_open:
        after_weight = dict(before_weight)
        weight_delta = _zero_delta(before_weight)
        records = [
            _blocked_record(
                before_weight=before_weight,
                read_view=read_view,
                source_refs=source_refs,
            )
        ]
        if read_view.get("source_approval_state") != "approved":
            blockers.append("learning_approval_pending")
        if int(read_view.get("approved_learning_entry_count", 0) or 0) == 0:
            blockers.append("approved_learning_entries_missing")
    proposal_state = (
        "proposal_ready_pending_apply_approval"
        if gate_open
        else "blocked_pending_learning_approval"
    )
    status = "proposal" if gate_open else "blocked"
    active_proposal_count = len(
        [record for record in records if record.get("model_weight_update_proposal_allowed") is True]
    )
    blocked_proposal_count = len(
        [record for record in records if record.get("proposal_state") == "blocked_pending_learning_approval"]
    )
    bayesian_update_count = active_proposal_count if gate_open else 0
    authority = phase6_authority_ledger()
    authority["stage"] = "Q6-12"
    authority["boundary"] = PHASE6_MODEL_WEIGHT_UPDATES_BOUNDARY
    artifact = {
        "schema_version": PHASE6_ARTIFACT_SCHEMA_VERSION,
        "phase6_model_weight_updates_schema_version": PHASE6_MODEL_WEIGHT_UPDATES_SCHEMA_VERSION,
        "artifact_type": "model_weight_update_proposal",
        "artifact_id": (
            "phase6:q6-12:model-weight-update-proposals:"
            "crude_oil_energy_security_disruption"
        ),
        "phase": "Q6",
        "stage": "Q6-12",
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
        "event_contract": phase6_event_contract("model_update_proposal"),
        "authority_ledger": authority,
        "source_posture": phase6_source_posture(),
        "provenance": _provenance(read_view, source_refs),
        "boundary": PHASE6_MODEL_WEIGHT_UPDATES_BOUNDARY,
        **phase6_authority_defaults(),
        **phase6_unsafe_counter_defaults(),
        **_disabled_write_fields(),
        "proposal_state": proposal_state,
        "strategy_family_key": TARGET_STRATEGY_FAMILY_KEY,
        "source_read_path_ref": SOURCE_READ_PATH_REF,
        "source_read_path_status": read_view.get("status"),
        "source_read_view_state": read_view.get("read_view_state"),
        "source_approval_state": read_view.get("source_approval_state"),
        "source_approved_learning_entry_count": int(
            read_view.get("approved_learning_entry_count", 0) or 0
        ),
        "source_staged_result_count": int(read_view.get("staged_result_count", 0) or 0),
        "source_seed_result_count": int(read_view.get("seed_result_count", 0) or 0),
        "source_result_count": int(read_view.get("result_count", 0) or 0),
        "source_strategy_universe_ref": SOURCE_STRATEGY_UNIVERSE_REF,
        "source_model_weight_count": len(before_weight),
        "before_weight": before_weight,
        "after_weight": after_weight,
        "weight_delta": weight_delta,
        "before_weight_sum": _weight_sum(before_weight),
        "after_weight_sum": _weight_sum(after_weight),
        "weight_delta_total_abs": round(sum(abs(float(value)) for value in weight_delta.values()), 6),
        "weights_normalized": 0.995 <= _weight_sum(before_weight) <= 1.005
        and 0.995 <= _weight_sum(after_weight) <= 1.005,
        "proposal_records": records,
        "proposal_record_count": len(records),
        "active_proposal_count": active_proposal_count,
        "blocked_proposal_count": blocked_proposal_count,
        "approved_evidence_count": int(read_view.get("approved_learning_entry_count", 0) or 0),
        "candidate_evidence_count": int(read_view.get("result_count", 0) or 0),
        "bayesian_update_count": bayesian_update_count,
        "model_weight_update_proposal_allowed": gate_open,
        "model_weight_update_proposed": gate_open,
        "apply_allowed": False,
        "model_weight_update_allowed": False,
        "model_weight_update_applied": False,
        "active_model_weight_mutated": False,
        "learning_write_created": False,
        "knowledge_graph_write_created": False,
        "knowledge_graph_commit_created": False,
        "chroma_write_created": False,
        "graph_backend_write_created": False,
        "model_weight_update_created": False,
        "trust_score_update_created": False,
        "policy_mutation_created": False,
        "strategy_mutation_created": False,
        "raw_payload_copied_count": 0,
        "private_payload_copied_count": 0,
        "local_path_exposed_count": 0,
        "secret_ref_exposed_count": 0,
        "source_hash_mutation_count": 0,
        "phase5_source_artifacts_mutated": False,
        "phase5_test_trades_count_for_phase7": False,
        "phase7_proof_credit_allowed": False,
        "unsafe_write_counter_total": 0,
        "cockpit_safe_status": _cockpit_safe_status(
            status=status,
            proposal_state=proposal_state,
            read_view=read_view,
            records=records,
            bayesian_update_count=bayesian_update_count,
        ),
        "blockers": sorted(set(blockers)),
        "blocker_count": len(set(blockers)),
        "recommended_next_stage": "Q6-13 Trust Score Update Proposals",
    }
    artifact["validation_errors"] = validate_phase6_model_weight_updates(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "blocked"
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


def _weights_are_dict(prefix: str, value: Any) -> tuple[dict[str, float], list[str]]:
    errors: list[str] = []
    if not isinstance(value, dict) or not value:
        return {}, [f"{prefix}_missing"]
    output: dict[str, float] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not isinstance(item, int | float):
            errors.append(f"{prefix}_invalid")
            continue
        output[key] = round(float(item), 6)
    return output, errors


def validate_phase6_model_weight_updates(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schema_version",
        "phase6_model_weight_updates_schema_version",
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
        "proposal_state",
        "strategy_family_key",
        "source_read_path_ref",
        "source_read_path_status",
        "source_read_view_state",
        "source_approval_state",
        "source_approved_learning_entry_count",
        "source_staged_result_count",
        "source_seed_result_count",
        "source_result_count",
        "source_strategy_universe_ref",
        "source_model_weight_count",
        "before_weight",
        "after_weight",
        "weight_delta",
        "before_weight_sum",
        "after_weight_sum",
        "weight_delta_total_abs",
        "weights_normalized",
        "proposal_records",
        "proposal_record_count",
        "active_proposal_count",
        "blocked_proposal_count",
        "approved_evidence_count",
        "candidate_evidence_count",
        "bayesian_update_count",
        "model_weight_update_proposal_allowed",
        "model_weight_update_proposed",
        "apply_allowed",
        "model_weight_update_allowed",
        "model_weight_update_applied",
        "active_model_weight_mutated",
        "learning_write_created",
        "knowledge_graph_write_created",
        "knowledge_graph_commit_created",
        "chroma_write_created",
        "graph_backend_write_created",
        "model_weight_update_created",
        "trust_score_update_created",
        "policy_mutation_created",
        "strategy_mutation_created",
        "raw_payload_copied_count",
        "private_payload_copied_count",
        "local_path_exposed_count",
        "secret_ref_exposed_count",
        "source_hash_mutation_count",
        "phase5_source_artifacts_mutated",
        "phase5_test_trades_count_for_phase7",
        "phase7_proof_credit_allowed",
        "unsafe_write_counter_total",
        "cockpit_safe_status",
        "blockers",
        "blocker_count",
    }
    missing = sorted(required_fields - set(artifact))
    if missing:
        errors.append("model_weight_updates_missing_fields:" + ",".join(missing))
    if artifact.get("phase6_model_weight_updates_schema_version") != (
        PHASE6_MODEL_WEIGHT_UPDATES_SCHEMA_VERSION
    ):
        errors.append("model_weight_updates_schema_version_mismatch")
    errors.extend(validate_phase6_artifact(artifact, expected_stage="Q6-12"))
    if artifact.get("artifact_type") != "model_weight_update_proposal":
        errors.append("model_weight_updates_artifact_type_mismatch")
    if artifact.get("status") not in {"blocked", "proposal"}:
        errors.append("model_weight_updates_status_invalid")
    if artifact.get("strategy_family_key") != TARGET_STRATEGY_FAMILY_KEY:
        errors.append("model_weight_updates_strategy_family_mismatch")
    if artifact.get("source_read_path_ref") != SOURCE_READ_PATH_REF:
        errors.append("source_read_path_ref_invalid")
    if artifact.get("source_strategy_universe_ref") != SOURCE_STRATEGY_UNIVERSE_REF:
        errors.append("source_strategy_universe_ref_invalid")
    if artifact.get("source_read_path_status") not in {"read_only", "blocked"}:
        errors.append("source_read_path_status_invalid")
    if artifact.get("source_approval_state") not in {"pending_review", "approved", "deferred"}:
        errors.append("source_approval_state_invalid")
    errors.extend(_write_disabled_errors("model_weight_updates", artifact))

    before_weight, before_errors = _weights_are_dict("before_weight", artifact.get("before_weight"))
    after_weight, after_errors = _weights_are_dict("after_weight", artifact.get("after_weight"))
    errors.extend(before_errors)
    errors.extend(after_errors)
    if before_weight and after_weight and set(before_weight) != set(after_weight):
        errors.append("model_weight_updates_weight_keys_mismatch")
    if before_weight and artifact.get("source_model_weight_count") != len(before_weight):
        errors.append("source_model_weight_count_mismatch")
    before_sum = _weight_sum(before_weight)
    after_sum = _weight_sum(after_weight)
    if artifact.get("before_weight_sum") != before_sum:
        errors.append("before_weight_sum_mismatch")
    if artifact.get("after_weight_sum") != after_sum:
        errors.append("after_weight_sum_mismatch")
    if not (0.995 <= before_sum <= 1.005 and 0.995 <= after_sum <= 1.005):
        errors.append("model_weight_updates_weights_not_normalized")
    if artifact.get("weights_normalized") is not True:
        errors.append("model_weight_updates_weights_normalized_false")
    delta = artifact.get("weight_delta")
    if not isinstance(delta, dict):
        errors.append("weight_delta_invalid")
        delta_values: dict[str, float] = {}
    else:
        delta_values = {
            str(key): round(float(value), 6)
            for key, value in delta.items()
            if isinstance(value, int | float)
        }
    expected_delta = {
        key: round(float(after_weight.get(key, 0.0)) - float(before_weight.get(key, 0.0)), 6)
        for key in before_weight
    }
    if before_weight and after_weight and delta_values != expected_delta:
        errors.append("weight_delta_mismatch")
    delta_total_abs = round(sum(abs(float(value)) for value in expected_delta.values()), 6)
    if artifact.get("weight_delta_total_abs") != delta_total_abs:
        errors.append("weight_delta_total_abs_mismatch")

    records = _list(artifact.get("proposal_records"))
    if artifact.get("proposal_record_count") != len(records):
        errors.append("proposal_record_count_mismatch")
    if len(records) < 1:
        errors.append("proposal_records_missing")
    active_count = 0
    blocked_count = 0
    raw_payload_count = 0
    private_payload_count = 0
    local_path_count = 0
    secret_ref_count = 0
    for record in records:
        if not isinstance(record, dict):
            errors.append("proposal_record_invalid")
            continue
        missing_record_fields = sorted(set(PROPOSAL_RECORD_REQUIRED_FIELDS) - set(record))
        if missing_record_fields:
            errors.append("proposal_record_missing_fields:" + ",".join(missing_record_fields))
        if record.get("strategy_family_key") != TARGET_STRATEGY_FAMILY_KEY:
            errors.append("proposal_record_strategy_family_mismatch")
        if record.get("model_weight_update_proposal_allowed") is True:
            active_count += 1
        if record.get("proposal_state") == "blocked_pending_learning_approval":
            blocked_count += 1
        if record.get("apply_allowed") is not False:
            errors.append("proposal_record_apply_allowed")
        if record.get("model_weight_update_applied") is not False:
            errors.append("proposal_record_model_weight_update_applied")
        if record.get("active_model_weight_mutated") is not False:
            errors.append("proposal_record_active_weight_mutated")
        if record.get("reference_only") is not True:
            errors.append("proposal_record_not_reference_only")
        if record.get("raw_payload_copied") is not False:
            raw_payload_count += 1
        if record.get("private_payload_copied") is not False:
            private_payload_count += 1
        if "raw_payload" in record or "private_payload" in record:
            errors.append("proposal_record_forbidden_payload")
        ref_errors = _source_ref_errors("proposal_record", record.get("source_refs"))
        errors.extend(ref_errors)
        local_path_count += len([error for error in ref_errors if error == "proposal_record_local_source_ref"])
        secret_ref_count += len([error for error in ref_errors if error == "proposal_record_secret_source_ref"])
    if artifact.get("active_proposal_count") != active_count:
        errors.append("active_proposal_count_mismatch")
    if artifact.get("blocked_proposal_count") != blocked_count:
        errors.append("blocked_proposal_count_mismatch")
    if artifact.get("raw_payload_copied_count") != raw_payload_count:
        errors.append("raw_payload_copied_count_mismatch")
    if artifact.get("private_payload_copied_count") != private_payload_count:
        errors.append("private_payload_copied_count_mismatch")
    if artifact.get("local_path_exposed_count") != local_path_count:
        errors.append("local_path_exposed_count_mismatch")
    if artifact.get("secret_ref_exposed_count") != secret_ref_count:
        errors.append("secret_ref_exposed_count_mismatch")
    if raw_payload_count or private_payload_count or local_path_count or secret_ref_count:
        errors.append("model_weight_updates_private_or_local_payload_exposed")

    if artifact.get("source_approval_state") != "approved":
        if artifact.get("status") != "blocked":
            errors.append("model_weight_updates_unapproved_status_not_blocked")
        if artifact.get("proposal_state") != "blocked_pending_learning_approval":
            errors.append("model_weight_updates_unapproved_state_not_blocked")
        if artifact.get("model_weight_update_proposal_allowed") is not False:
            errors.append("model_weight_updates_unapproved_proposal_allowed")
        if artifact.get("model_weight_update_proposed") is not False:
            errors.append("model_weight_updates_unapproved_proposed")
        if artifact.get("active_proposal_count") != 0:
            errors.append("model_weight_updates_unapproved_active_proposals")
        if artifact.get("bayesian_update_count") != 0:
            errors.append("model_weight_updates_unapproved_bayesian_updates")
        if before_weight and after_weight and before_weight != after_weight:
            errors.append("model_weight_updates_unapproved_after_changed")
        if artifact.get("weight_delta_total_abs") != 0.0:
            errors.append("model_weight_updates_unapproved_delta_nonzero")
    if artifact.get("status") == "proposal":
        if artifact.get("source_approval_state") != "approved":
            errors.append("model_weight_updates_proposal_without_approval")
        if artifact.get("active_proposal_count", 0) < 1:
            errors.append("model_weight_updates_proposal_without_active_records")
        if artifact.get("model_weight_update_proposal_allowed") is not True:
            errors.append("model_weight_updates_proposal_allowed_missing")
    if artifact.get("apply_allowed") is not False:
        errors.append("apply_allowed")
    if artifact.get("model_weight_update_applied") is not False:
        errors.append("model_weight_update_applied")
    if artifact.get("active_model_weight_mutated") is not False:
        errors.append("active_model_weight_mutated")
    if artifact.get("phase5_test_trades_count_for_phase7") is not False:
        errors.append("phase5_test_trades_count_for_phase7")
    errors.extend(_source_ref_errors("model_weight_updates", artifact.get("provenance", {}).get("source_refs")))

    cockpit = artifact.get("cockpit_safe_status")
    if not isinstance(cockpit, dict):
        errors.append("cockpit_safe_status_missing")
    else:
        extra = sorted(set(cockpit) - set(COCKPIT_SAFE_STATUS_FIELDS))
        if extra:
            errors.append("cockpit_safe_status_forbidden_fields:" + ",".join(extra))
        for forbidden in ("source_refs", "before_weight", "after_weight", "weight_delta", "raw_payload"):
            if forbidden in cockpit:
                errors.append(f"cockpit_safe_status_exposes:{forbidden}")
        for field in COCKPIT_SAFE_STATUS_FIELDS:
            if field in cockpit and field in artifact and cockpit[field] != artifact[field]:
                errors.append(f"cockpit_safe_status_mismatch:{field}")
    unsafe_total = 0
    for field in PHASE6_UNSAFE_COUNT_FIELDS:
        value = int(artifact.get(field, 0) or 0)
        unsafe_total += value
        if value != 0:
            errors.append(f"model_weight_updates_unsafe_count_nonzero:{field}")
    if artifact.get("unsafe_write_counter_total") != unsafe_total:
        errors.append("model_weight_updates_unsafe_total_mismatch")
    if artifact.get("unsafe_write_counter_total") != 0:
        errors.append("model_weight_updates_unsafe_total_nonzero")

    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "cannot apply model weights",
        "cannot mutate active strategy artifacts",
        "cannot write learning data",
        "cannot write or commit a Knowledge Graph",
        "cannot count Phase 5 test trades toward Phase 7 proof",
    ):
        if phrase not in boundary:
            errors.append("model_weight_updates_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not artifact.get("event_log_path"):
            errors.append("model_weight_updates_event_log_path_missing")
        if not artifact.get("event_log_correlation_id"):
            errors.append("model_weight_updates_event_correlation_missing")
        if artifact.get("event_log_event_count") != 1:
            errors.append("model_weight_updates_event_log_count_mismatch")
    return sorted(set(errors))


def attach_phase6_model_weight_updates_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(event_log_path or (_runtime_dir(settings) / PHASE6_MODEL_WEIGHT_UPDATES_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PHASE6_MODEL_WEIGHT_UPDATES_EVENT_TYPE,
        PHASE6_MODEL_WEIGHT_UPDATES_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "proposal_state": output.get("proposal_state"),
            "source_approval_state": output.get("source_approval_state"),
            "proposal_record_count": output.get("proposal_record_count"),
            "active_proposal_count": output.get("active_proposal_count"),
            "blocked_proposal_count": output.get("blocked_proposal_count"),
            "approved_evidence_count": output.get("approved_evidence_count"),
            "bayesian_update_count": output.get("bayesian_update_count"),
            "apply_allowed": output.get("apply_allowed"),
            "model_weight_update_applied": output.get("model_weight_update_applied"),
            "active_model_weight_mutated": output.get("active_model_weight_mutated"),
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
    output["validation_errors"] = validate_phase6_model_weight_updates(output)
    if output["validation_errors"]:
        output["status"] = "blocked"
    return output, entry


def write_phase6_model_weight_updates(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase6_model_weight_updates_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase6_model_weight_updates_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase6_model_weight_updates(output)
        if output["validation_errors"]:
            output["status"] = "blocked"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase6_model_weight_updates(output)
    if output["validation_errors"]:
        output["status"] = "blocked"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE6_MODEL_WEIGHT_UPDATES_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "proposal_state": output.get("proposal_state"),
        "source_approval_state": output.get("source_approval_state"),
        "proposal_record_count": output.get("proposal_record_count"),
        "active_proposal_count": output.get("active_proposal_count"),
        "blocked_proposal_count": output.get("blocked_proposal_count"),
        "approved_evidence_count": output.get("approved_evidence_count"),
        "bayesian_update_count": output.get("bayesian_update_count"),
        "apply_allowed": output.get("apply_allowed"),
        "model_weight_update_applied": output.get("model_weight_update_applied"),
        "active_model_weight_mutated": output.get("active_model_weight_mutated"),
        "weight_delta_total_abs": output.get("weight_delta_total_abs"),
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
