"""Q6-15 Architect learning summary.

This stage summarizes the Phase 6 postmortem, read path, update proposals, and
shadow replay output for Architect review. The current approval ledger is still
pending, so the artifact records blocked recommendation records and keeps every
policy, strategy, risk-limit, source-weight, model-weight, and trust-score
mutation disabled.
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
from orchestrator.phase6_knowledge_graph_staging import TARGET_STRATEGY_FAMILY_KEY
from orchestrator.phase6_shadow_strategy_runner import (
    PHASE6_SHADOW_STRATEGY_RUNNER_RUNTIME_ARTIFACT,
    validate_phase6_shadow_strategy_runner,
)


PHASE6_ARCHITECT_LEARNING_SCHEMA_VERSION = 1
PHASE6_ARCHITECT_LEARNING_RUNTIME_ARTIFACT = "phase6_architect_learning_summary.json"
PHASE6_ARCHITECT_LEARNING_HISTORY = "phase6_architect_learning_summary_history.jsonl"
PHASE6_ARCHITECT_LEARNING_EVENT_LOG = "phase6_architect_learning_summary_events.jsonl"
PHASE6_ARCHITECT_LEARNING_EVENT_TYPE = "phase6_trust_score_update_proposed"
PHASE6_ARCHITECT_LEARNING_COMPONENT = "phase6_architect_learning"

SOURCE_SHADOW_REPLAY_REF = f"data/runtime/{PHASE6_SHADOW_STRATEGY_RUNNER_RUNTIME_ARTIFACT}"
SOURCE_APPROVAL_REF = "data/runtime/phase6_learning_approval_ledger.json"
SOURCE_KG_READ_VIEW_REF = "data/runtime/phase6_knowledge_graph_read_view.json"
SOURCE_MODEL_WEIGHT_UPDATES_REF = "data/runtime/phase6_model_weight_update_proposals.json"
SOURCE_TRUST_SCORE_UPDATES_REF = "data/runtime/phase6_trust_score_update_proposals.json"
SOURCE_POSTMORTEM_REVIEW_REF = "data/runtime/phase6_postmortem_reduced_review.json"
SOURCE_STRATEGY_UNIVERSE_REF = "data/runtime/phase4_candidate_strategy_universe.json"

PHASE6_ARCHITECT_LEARNING_BOUNDARY = (
    "Q6-15 creates an Architect learning summary and recommendation surface "
    "only. It can summarize approved postmortem facts, Knowledge Graph read "
    "results, model-weight proposals, trust-score proposals, and shadow replay "
    "outputs for explicit governance review, or record blocked recommendations "
    "while approval is missing, but it cannot mutate policy, cannot mutate "
    "strategies, cannot update source weights, cannot update model weights, "
    "cannot update trust scores, cannot change risk limits, cannot write "
    "learning data, cannot write or commit a Knowledge Graph, cannot call "
    "broker POST routes, cannot call Alpaca POST routes, cannot mutate Phase 5 "
    "source artifacts, cannot call live endpoints, cannot enable live capital, "
    "and cannot count Phase 5 test trades toward Phase 7 proof."
)

WRITE_DISABLED_FIELDS: tuple[str, ...] = (
    "recommendation_apply_allowed",
    "policy_mutation_allowed",
    "policy_mutation_created",
    "strategy_mutation_allowed",
    "strategy_mutation_created",
    "risk_limit_update_allowed",
    "risk_limit_update_created",
    "source_weight_update_allowed",
    "source_weight_update_created",
    "model_weight_update_allowed",
    "model_weight_update_created",
    "trust_score_update_allowed",
    "trust_score_update_created",
    "learning_write_created",
    "knowledge_graph_write_created",
    "knowledge_graph_commit_created",
    "chroma_write_created",
    "graph_backend_write_created",
    "phase5_source_artifacts_mutated",
    "phase7_proof_credit_allowed",
)

RECOMMENDATION_RECORD_REQUIRED_FIELDS: tuple[str, ...] = (
    "recommendation_id",
    "recommendation_state",
    "recommendation_type",
    "target_surface",
    "strategy_family_key",
    "source_refs",
    "source_approval_state",
    "approved_learning_entry",
    "governance_required",
    "governance_state",
    "recommendation_allowed",
    "apply_allowed",
    "policy_mutation_allowed",
    "strategy_mutation_allowed",
    "risk_limit_update_allowed",
    "source_weight_update_allowed",
    "model_weight_update_allowed",
    "trust_score_update_allowed",
    "reference_only",
    "raw_payload_copied",
    "private_payload_copied",
    "rationale",
)

COCKPIT_SAFE_STATUS_FIELDS: tuple[str, ...] = (
    "status",
    "summary_state",
    "source_shadow_replay_status",
    "source_approval_state",
    "recommendation_count",
    "recommendation_record_count",
    "active_recommendation_count",
    "blocked_recommendation_count",
    "approved_fact_count",
    "governance_pending_count",
    "policy_mutation_allowed",
    "strategy_mutation_allowed",
    "risk_limit_update_allowed",
    "phase7_proof_credit_allowed",
    "unsafe_write_counter_total",
)

RECOMMENDATION_TEMPLATES: tuple[dict[str, str], ...] = (
    {
        "recommendation_type": "policy_guardrail_review",
        "target_surface": "learning_governance_policy",
        "text": "Keep learning approval gates closed until explicit reviewer and Event Log approval exist.",
    },
    {
        "recommendation_type": "strategy_review",
        "target_surface": "crude_oil_energy_security_disruption_strategy",
        "text": "Keep the crude-oil energy-security strategy in hold/review posture until learning is approved.",
    },
    {
        "recommendation_type": "risk_limit_review",
        "target_surface": "paper_lifecycle_risk_limits",
        "text": "Keep risk limits unchanged because the Phase 5 lifecycle remains test data only.",
    },
    {
        "recommendation_type": "source_model_trust_review",
        "target_surface": "source_and_model_weight_surfaces",
        "text": "Keep source weights, model weights, and trust scores unchanged until approved evidence exists.",
    },
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


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _disabled_write_fields() -> dict[str, bool]:
    return {field: False for field in WRITE_DISABLED_FIELDS}


def _has_local_path(ref: str) -> bool:
    if ref.startswith("/") or ref.startswith("~"):
        return True
    return len(ref) > 2 and ref[1:3] == ":\\"


def phase6_architect_learning_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE6_ARCHITECT_LEARNING_RUNTIME_ARTIFACT,
        runtime / PHASE6_ARCHITECT_LEARNING_HISTORY,
        runtime / PHASE6_ARCHITECT_LEARNING_EVENT_LOG,
    )


def _safe_source_refs(refs: list[Any]) -> list[str]:
    safe_refs = [
        SOURCE_SHADOW_REPLAY_REF,
        SOURCE_APPROVAL_REF,
        SOURCE_KG_READ_VIEW_REF,
        SOURCE_MODEL_WEIGHT_UPDATES_REF,
        SOURCE_TRUST_SCORE_UPDATES_REF,
        SOURCE_POSTMORTEM_REVIEW_REF,
        SOURCE_STRATEGY_UNIVERSE_REF,
    ]
    for ref in refs:
        if isinstance(ref, str) and ref.startswith("data/") and ref not in safe_refs:
            safe_refs.append(ref)
    return safe_refs


def _source_refs(shadow_replay: dict[str, Any]) -> list[str]:
    refs: list[Any] = [
        SOURCE_SHADOW_REPLAY_REF,
        SOURCE_APPROVAL_REF,
        SOURCE_KG_READ_VIEW_REF,
        SOURCE_MODEL_WEIGHT_UPDATES_REF,
        SOURCE_TRUST_SCORE_UPDATES_REF,
        SOURCE_POSTMORTEM_REVIEW_REF,
        SOURCE_STRATEGY_UNIVERSE_REF,
    ]
    provenance = shadow_replay.get("provenance")
    if isinstance(provenance, dict):
        refs.extend(_list(provenance.get("source_refs")))
    for record in _list(shadow_replay.get("replay_records")):
        if isinstance(record, dict):
            refs.extend(_list(record.get("source_refs")))
    return _safe_source_refs(refs)


def _summary_state(gate_open: bool) -> str:
    return "architect_recommendations_ready_pending_governance" if gate_open else (
        "blocked_pending_learning_approval"
    )


def _recommendation_records(
    *,
    gate_open: bool,
    source_refs: list[str],
    source_approval_state: str | None,
) -> list[dict[str, Any]]:
    state = _summary_state(gate_open)
    records: list[dict[str, Any]] = []
    for template in RECOMMENDATION_TEMPLATES:
        recommendation_type = template["recommendation_type"]
        records.append(
            {
                "recommendation_id": f"q6-15-architect-recommendation:{recommendation_type}",
                "recommendation_state": state,
                "recommendation_type": recommendation_type,
                "target_surface": template["target_surface"],
                "strategy_family_key": TARGET_STRATEGY_FAMILY_KEY,
                "recommendation_text": template["text"],
                "source_refs": source_refs,
                "source_approval_state": source_approval_state,
                "approved_learning_entry": gate_open,
                "governance_required": True,
                "governance_state": (
                    "pending_explicit_governance"
                    if gate_open
                    else "blocked_pending_learning_approval"
                ),
                "recommendation_allowed": gate_open,
                "apply_allowed": False,
                "policy_mutation_allowed": False,
                "strategy_mutation_allowed": False,
                "risk_limit_update_allowed": False,
                "source_weight_update_allowed": False,
                "model_weight_update_allowed": False,
                "trust_score_update_allowed": False,
                "reference_only": True,
                "raw_payload_copied": False,
                "private_payload_copied": False,
                "rationale": (
                    "Approved learning evidence permits an Architect recommendation, "
                    "but application remains blocked pending explicit governance."
                    if gate_open
                    else "Q6-9 approval is still pending, so Q6-15 records this "
                    "Architect recommendation as blocked and non-applicable."
                ),
            }
        )
    return records


def _approved_postmortem_summary(
    approval: dict[str, Any],
    review: dict[str, Any],
    shadow_replay: dict[str, Any],
) -> dict[str, Any]:
    return {
        "source_approval_ref": SOURCE_APPROVAL_REF,
        "source_review_ref": SOURCE_POSTMORTEM_REVIEW_REF,
        "approval_state": approval.get("approval_state") or shadow_replay.get("source_approval_state"),
        "approval_logged": approval.get("approval_logged") is True,
        "review_state": review.get("review_state"),
        "postmortem_approved": approval.get("postmortem_approved") is True,
        "approved_action_count": int(approval.get("approved_action_count", 0) or 0),
        "approved_learning_entry_count": int(shadow_replay.get("approved_fact_count", 0) or 0),
        "approved_learning_available": int(shadow_replay.get("approved_fact_count", 0) or 0) > 0,
        "reference_only": True,
    }


def _graph_entry_summary(kg_read_view: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_kg_read_view_ref": SOURCE_KG_READ_VIEW_REF,
        "read_view_state": kg_read_view.get("read_view_state"),
        "result_count": int(kg_read_view.get("result_count", 0) or 0),
        "seed_result_count": int(kg_read_view.get("seed_result_count", 0) or 0),
        "staged_result_count": int(kg_read_view.get("staged_result_count", 0) or 0),
        "approved_learning_entry_count": int(
            kg_read_view.get("approved_learning_entry_count", 0) or 0
        ),
        "write_allowed": kg_read_view.get("write_allowed") is True,
        "reference_only": True,
    }


def _update_proposal_summary(
    model_weight: dict[str, Any],
    trust_score: dict[str, Any],
) -> dict[str, Any]:
    return {
        "source_model_weight_ref": SOURCE_MODEL_WEIGHT_UPDATES_REF,
        "source_trust_score_ref": SOURCE_TRUST_SCORE_UPDATES_REF,
        "model_weight_status": model_weight.get("status"),
        "model_weight_proposal_state": model_weight.get("proposal_state"),
        "active_model_weight_proposal_count": int(model_weight.get("active_proposal_count", 0) or 0),
        "model_weight_delta_total_abs": float(model_weight.get("weight_delta_total_abs", 0.0) or 0.0),
        "trust_score_status": trust_score.get("status"),
        "trust_score_proposal_state": trust_score.get("proposal_state"),
        "active_trust_score_proposal_count": int(trust_score.get("active_proposal_count", 0) or 0),
        "trust_score_delta_total_abs": float(trust_score.get("score_delta_total_abs", 0.0) or 0.0),
        "apply_allowed": False,
        "reference_only": True,
    }


def _replay_summary(shadow_replay: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_shadow_replay_ref": SOURCE_SHADOW_REPLAY_REF,
        "status": shadow_replay.get("status"),
        "replay_state": shadow_replay.get("replay_state"),
        "variant_record_count": int(shadow_replay.get("variant_record_count", 0) or 0),
        "active_replay_count": int(shadow_replay.get("active_replay_count", 0) or 0),
        "blocked_replay_count": int(shadow_replay.get("blocked_replay_count", 0) or 0),
        "evaluated_variant_count": int(shadow_replay.get("evaluated_variant_count", 0) or 0),
        "actual_vs_hypothetical_comparison_count": int(
            shadow_replay.get("actual_vs_hypothetical_comparison_count", 0) or 0
        ),
        "trade_candidate_created_count": int(shadow_replay.get("trade_candidate_created_count", 0) or 0),
        "paper_order_allowed_count": int(shadow_replay.get("paper_order_allowed_count", 0) or 0),
        "execution_allowed_count": int(shadow_replay.get("execution_allowed_count", 0) or 0),
        "reference_only": True,
    }


def _provenance(source_refs: list[str]) -> dict[str, Any]:
    output = phase6_provenance(source_refs)
    output["execution_evidence_refs"] = [
        ref
        for ref in source_refs
        if any(marker in ref for marker in ("position_monitor", "closed_trade", "outcome_links"))
    ]
    output["market_context_refs"] = [
        ref
        for ref in source_refs
        if any(marker in ref for marker in ("cockpit-status", "preference_", "yahoo"))
    ]
    output["model_interpretation_refs"] = [
        ref
        for ref in source_refs
        if any(marker in ref for marker in ("model_weight", "trust_score", "shadow_strategy"))
    ]
    output["governance_refs"] = [
        ref
        for ref in source_refs
        if any(marker in ref for marker in ("approval", "reduced_review", "read_view"))
    ]
    return output


def _cockpit_safe_status(
    *,
    status: str,
    summary_state: str,
    shadow_replay: dict[str, Any],
    records: list[dict[str, Any]],
    approved_fact_count: int,
) -> dict[str, Any]:
    active_count = len([record for record in records if record.get("recommendation_allowed") is True])
    blocked_count = len(
        [record for record in records if record.get("recommendation_state") == "blocked_pending_learning_approval"]
    )
    return {
        "status": status,
        "summary_state": summary_state,
        "source_shadow_replay_status": shadow_replay.get("status"),
        "source_approval_state": shadow_replay.get("source_approval_state"),
        "recommendation_count": len(records),
        "recommendation_record_count": len(records),
        "active_recommendation_count": active_count,
        "blocked_recommendation_count": blocked_count,
        "approved_fact_count": approved_fact_count,
        "governance_pending_count": len(records),
        "policy_mutation_allowed": False,
        "strategy_mutation_allowed": False,
        "risk_limit_update_allowed": False,
        "phase7_proof_credit_allowed": False,
        "unsafe_write_counter_total": 0,
    }


def _gate_open(shadow_replay: dict[str, Any], blockers: list[str]) -> bool:
    if blockers:
        return False
    if shadow_replay.get("source_approval_state") != "approved":
        return False
    if int(shadow_replay.get("approved_fact_count", 0) or 0) <= 0:
        return False
    return True


def build_phase6_architect_learning(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    shadow_replay = _read_json(SOURCE_SHADOW_REPLAY_REF, settings) or {}
    approval = _read_json(SOURCE_APPROVAL_REF, settings) or {}
    kg_read_view = _read_json(SOURCE_KG_READ_VIEW_REF, settings) or {}
    model_weight = _read_json(SOURCE_MODEL_WEIGHT_UPDATES_REF, settings) or {}
    trust_score = _read_json(SOURCE_TRUST_SCORE_UPDATES_REF, settings) or {}
    review = _read_json(SOURCE_POSTMORTEM_REVIEW_REF, settings) or {}
    shadow_errors = validate_phase6_shadow_strategy_runner(shadow_replay) if shadow_replay else []
    source_refs = _source_refs(shadow_replay)
    blockers: list[str] = []
    if not shadow_replay:
        blockers.append("shadow_strategy_replay_missing")
    if shadow_errors:
        blockers.append("shadow_strategy_replay_validation_errors")
    if not approval:
        blockers.append("learning_approval_ledger_missing")
    if not kg_read_view:
        blockers.append("knowledge_graph_read_view_missing")
    if not model_weight:
        blockers.append("model_weight_update_proposals_missing")
    if not trust_score:
        blockers.append("trust_score_update_proposals_missing")
    gate_open = _gate_open(shadow_replay, blockers)
    if not gate_open:
        if shadow_replay.get("source_approval_state") != "approved":
            blockers.append("learning_approval_pending")
        if int(shadow_replay.get("approved_fact_count", 0) or 0) == 0:
            blockers.append("approved_learning_entries_missing")

    summary_state = _summary_state(gate_open)
    records = _recommendation_records(
        gate_open=gate_open,
        source_refs=source_refs,
        source_approval_state=shadow_replay.get("source_approval_state"),
    )
    active_recommendation_count = len(
        [record for record in records if record.get("recommendation_allowed") is True]
    )
    blocked_recommendation_count = len(
        [record for record in records if record.get("recommendation_state") == "blocked_pending_learning_approval"]
    )
    approved_fact_count = int(shadow_replay.get("approved_fact_count", 0) or 0)
    status = "proposal" if gate_open else "blocked"
    authority = phase6_authority_ledger()
    authority["stage"] = "Q6-15"
    authority["boundary"] = PHASE6_ARCHITECT_LEARNING_BOUNDARY
    artifact = {
        "schema_version": PHASE6_ARTIFACT_SCHEMA_VERSION,
        "phase6_architect_learning_schema_version": PHASE6_ARCHITECT_LEARNING_SCHEMA_VERSION,
        "artifact_type": "architect_learning_summary",
        "artifact_id": "phase6:q6-15:architect-learning-summary:crude_oil_energy_security_disruption",
        "phase": "Q6",
        "stage": "Q6-15",
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
        "event_contract": phase6_event_contract("trust_update_proposal"),
        "authority_ledger": authority,
        "source_posture": phase6_source_posture(),
        "provenance": _provenance(source_refs),
        "boundary": PHASE6_ARCHITECT_LEARNING_BOUNDARY,
        **phase6_authority_defaults(),
        **phase6_unsafe_counter_defaults(),
        **_disabled_write_fields(),
        "summary_state": summary_state,
        "strategy_family_key": TARGET_STRATEGY_FAMILY_KEY,
        "source_shadow_replay_ref": SOURCE_SHADOW_REPLAY_REF,
        "source_shadow_replay_status": shadow_replay.get("status"),
        "source_replay_state": shadow_replay.get("replay_state"),
        "source_approval_state": shadow_replay.get("source_approval_state"),
        "source_approved_fact_count": approved_fact_count,
        "source_kg_read_view_ref": SOURCE_KG_READ_VIEW_REF,
        "source_model_weight_ref": SOURCE_MODEL_WEIGHT_UPDATES_REF,
        "source_trust_score_ref": SOURCE_TRUST_SCORE_UPDATES_REF,
        "source_approval_ref": SOURCE_APPROVAL_REF,
        "source_postmortem_review_ref": SOURCE_POSTMORTEM_REVIEW_REF,
        "approved_postmortem_summary": _approved_postmortem_summary(
            approval,
            review,
            shadow_replay,
        ),
        "graph_entry_summary": _graph_entry_summary(kg_read_view),
        "update_proposal_summary": _update_proposal_summary(model_weight, trust_score),
        "replay_summary": _replay_summary(shadow_replay),
        "architect_summary_created": True,
        "recommendation_records": records,
        "recommendation_count": len(records),
        "recommendation_record_count": len(records),
        "active_recommendation_count": active_recommendation_count,
        "blocked_recommendation_count": blocked_recommendation_count,
        "governance_pending_count": len(records),
        "policy_recommendation_count": len(
            [record for record in records if record.get("recommendation_type") == "policy_guardrail_review"]
        ),
        "strategy_recommendation_count": len(
            [record for record in records if record.get("recommendation_type") == "strategy_review"]
        ),
        "risk_limit_recommendation_count": len(
            [record for record in records if record.get("recommendation_type") == "risk_limit_review"]
        ),
        "source_model_trust_recommendation_count": len(
            [
                record
                for record in records
                if record.get("recommendation_type") == "source_model_trust_review"
            ]
        ),
        "approved_fact_count": approved_fact_count,
        "recommendation_apply_allowed": False,
        "policy_mutation_allowed": False,
        "policy_mutation_created": False,
        "strategy_mutation_allowed": False,
        "strategy_mutation_created": False,
        "risk_limit_update_allowed": False,
        "risk_limit_update_created": False,
        "source_weight_update_allowed": False,
        "source_weight_update_created": False,
        "model_weight_update_allowed": False,
        "model_weight_update_created": False,
        "trust_score_update_allowed": False,
        "trust_score_update_created": False,
        "learning_write_created": False,
        "knowledge_graph_write_created": False,
        "knowledge_graph_commit_created": False,
        "chroma_write_created": False,
        "graph_backend_write_created": False,
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
            summary_state=summary_state,
            shadow_replay=shadow_replay,
            records=records,
            approved_fact_count=approved_fact_count,
        ),
        "blockers": sorted(set(blockers)),
        "blocker_count": len(set(blockers)),
        "recommended_next_stage": "Q6-16 Journal And Cockpit Visibility",
    }
    artifact["validation_errors"] = validate_phase6_architect_learning(artifact)
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


def validate_phase6_architect_learning(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schema_version",
        "phase6_architect_learning_schema_version",
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
        "summary_state",
        "strategy_family_key",
        "source_shadow_replay_ref",
        "source_shadow_replay_status",
        "source_replay_state",
        "source_approval_state",
        "source_approved_fact_count",
        "source_kg_read_view_ref",
        "source_model_weight_ref",
        "source_trust_score_ref",
        "source_approval_ref",
        "source_postmortem_review_ref",
        "approved_postmortem_summary",
        "graph_entry_summary",
        "update_proposal_summary",
        "replay_summary",
        "architect_summary_created",
        "recommendation_records",
        "recommendation_count",
        "recommendation_record_count",
        "active_recommendation_count",
        "blocked_recommendation_count",
        "governance_pending_count",
        "policy_recommendation_count",
        "strategy_recommendation_count",
        "risk_limit_recommendation_count",
        "source_model_trust_recommendation_count",
        "approved_fact_count",
        "recommendation_apply_allowed",
        "policy_mutation_allowed",
        "policy_mutation_created",
        "strategy_mutation_allowed",
        "strategy_mutation_created",
        "risk_limit_update_allowed",
        "risk_limit_update_created",
        "source_weight_update_allowed",
        "source_weight_update_created",
        "model_weight_update_allowed",
        "model_weight_update_created",
        "trust_score_update_allowed",
        "trust_score_update_created",
        "learning_write_created",
        "knowledge_graph_write_created",
        "knowledge_graph_commit_created",
        "chroma_write_created",
        "graph_backend_write_created",
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
        errors.append("architect_learning_missing_fields:" + ",".join(missing))
    if artifact.get("phase6_architect_learning_schema_version") != (
        PHASE6_ARCHITECT_LEARNING_SCHEMA_VERSION
    ):
        errors.append("architect_learning_schema_version_mismatch")
    errors.extend(validate_phase6_artifact(artifact, expected_stage="Q6-15"))
    if artifact.get("artifact_type") != "architect_learning_summary":
        errors.append("architect_learning_artifact_type_mismatch")
    if artifact.get("status") not in {"blocked", "proposal"}:
        errors.append("architect_learning_status_invalid")
    if artifact.get("strategy_family_key") != TARGET_STRATEGY_FAMILY_KEY:
        errors.append("strategy_family_key_mismatch")
    if artifact.get("source_shadow_replay_ref") != SOURCE_SHADOW_REPLAY_REF:
        errors.append("source_shadow_replay_ref_invalid")
    if artifact.get("source_kg_read_view_ref") != SOURCE_KG_READ_VIEW_REF:
        errors.append("source_kg_read_view_ref_invalid")
    if artifact.get("source_model_weight_ref") != SOURCE_MODEL_WEIGHT_UPDATES_REF:
        errors.append("source_model_weight_ref_invalid")
    if artifact.get("source_trust_score_ref") != SOURCE_TRUST_SCORE_UPDATES_REF:
        errors.append("source_trust_score_ref_invalid")
    if artifact.get("source_approval_ref") != SOURCE_APPROVAL_REF:
        errors.append("source_approval_ref_invalid")
    if artifact.get("source_postmortem_review_ref") != SOURCE_POSTMORTEM_REVIEW_REF:
        errors.append("source_postmortem_review_ref_invalid")
    if artifact.get("source_shadow_replay_status") not in {"blocked", "replay"}:
        errors.append("source_shadow_replay_status_invalid")
    if artifact.get("source_approval_state") not in {"pending_review", "approved", "deferred"}:
        errors.append("source_approval_state_invalid")
    errors.extend(_write_disabled_errors("architect_learning", artifact))

    records = _list(artifact.get("recommendation_records"))
    if artifact.get("recommendation_record_count") != len(records):
        errors.append("recommendation_record_count_mismatch")
    if artifact.get("recommendation_count") != len(records):
        errors.append("recommendation_count_mismatch")
    if len(records) < 1:
        errors.append("recommendation_records_missing")
    active_count = 0
    blocked_count = 0
    raw_payload_count = 0
    private_payload_count = 0
    local_path_count = 0
    secret_ref_count = 0
    governance_pending_count = 0
    for record in records:
        if not isinstance(record, dict):
            errors.append("recommendation_record_invalid")
            continue
        missing_record_fields = sorted(set(RECOMMENDATION_RECORD_REQUIRED_FIELDS) - set(record))
        if missing_record_fields:
            errors.append("recommendation_record_missing_fields:" + ",".join(missing_record_fields))
        if record.get("strategy_family_key") != TARGET_STRATEGY_FAMILY_KEY:
            errors.append("recommendation_record_strategy_family_mismatch")
        if record.get("governance_required") is not True:
            errors.append("recommendation_record_governance_not_required")
        if record.get("governance_state") in {
            "pending_explicit_governance",
            "blocked_pending_learning_approval",
        }:
            governance_pending_count += 1
        if record.get("recommendation_allowed") is True:
            active_count += 1
        if record.get("recommendation_state") == "blocked_pending_learning_approval":
            blocked_count += 1
        for field in (
            "apply_allowed",
            "policy_mutation_allowed",
            "strategy_mutation_allowed",
            "risk_limit_update_allowed",
            "source_weight_update_allowed",
            "model_weight_update_allowed",
            "trust_score_update_allowed",
        ):
            if record.get(field) is not False:
                errors.append(f"recommendation_record_action_enabled:{field}")
        if record.get("reference_only") is not True:
            errors.append("recommendation_record_not_reference_only")
        if record.get("raw_payload_copied") is not False:
            raw_payload_count += 1
        if record.get("private_payload_copied") is not False:
            private_payload_count += 1
        if "raw_payload" in record or "private_payload" in record:
            errors.append("recommendation_record_forbidden_payload")
        ref_errors = _source_ref_errors("recommendation_record", record.get("source_refs"))
        errors.extend(ref_errors)
        local_path_count += len(
            [error for error in ref_errors if error == "recommendation_record_local_source_ref"]
        )
        secret_ref_count += len(
            [error for error in ref_errors if error == "recommendation_record_secret_source_ref"]
        )
    if artifact.get("active_recommendation_count") != active_count:
        errors.append("active_recommendation_count_mismatch")
    if artifact.get("blocked_recommendation_count") != blocked_count:
        errors.append("blocked_recommendation_count_mismatch")
    if artifact.get("governance_pending_count") != governance_pending_count:
        errors.append("governance_pending_count_mismatch")
    if artifact.get("raw_payload_copied_count") != raw_payload_count:
        errors.append("raw_payload_copied_count_mismatch")
    if artifact.get("private_payload_copied_count") != private_payload_count:
        errors.append("private_payload_copied_count_mismatch")
    if artifact.get("local_path_exposed_count") != local_path_count:
        errors.append("local_path_exposed_count_mismatch")
    if artifact.get("secret_ref_exposed_count") != secret_ref_count:
        errors.append("secret_ref_exposed_count_mismatch")
    if raw_payload_count or private_payload_count or local_path_count or secret_ref_count:
        errors.append("architect_learning_private_or_local_payload_exposed")
    if artifact.get("approved_fact_count") != artifact.get("source_approved_fact_count"):
        errors.append("approved_fact_count_mismatch")

    if artifact.get("source_approval_state") != "approved":
        if artifact.get("status") != "blocked":
            errors.append("architect_learning_unapproved_status_not_blocked")
        if artifact.get("summary_state") != "blocked_pending_learning_approval":
            errors.append("architect_learning_unapproved_state_not_blocked")
        if artifact.get("active_recommendation_count") != 0:
            errors.append("architect_learning_unapproved_active_recommendations")
    else:
        if artifact.get("status") != "proposal":
            errors.append("architect_learning_approved_status_not_proposal")
        if artifact.get("active_recommendation_count", 0) < 1:
            errors.append("architect_learning_approved_without_recommendations")
    if artifact.get("architect_summary_created") is not True:
        errors.append("architect_summary_not_created")
    for field in (
        "policy_mutation_created",
        "strategy_mutation_created",
        "risk_limit_update_created",
        "source_weight_update_created",
        "model_weight_update_created",
        "trust_score_update_created",
    ):
        if artifact.get(field) is not False:
            errors.append(f"architect_learning_mutation_created:{field}")
    if artifact.get("phase5_test_trades_count_for_phase7") is not False:
        errors.append("phase5_test_trades_count_for_phase7")
    errors.extend(_source_ref_errors("architect_learning", artifact.get("provenance", {}).get("source_refs")))

    cockpit = artifact.get("cockpit_safe_status")
    if not isinstance(cockpit, dict):
        errors.append("cockpit_safe_status_missing")
    else:
        extra = sorted(set(cockpit) - set(COCKPIT_SAFE_STATUS_FIELDS))
        if extra:
            errors.append("cockpit_safe_status_forbidden_fields:" + ",".join(extra))
        for forbidden in (
            "source_refs",
            "recommendation_records",
            "approved_postmortem_summary",
            "raw_payload",
        ):
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
            errors.append(f"architect_learning_unsafe_count_nonzero:{field}")
    if artifact.get("unsafe_write_counter_total") != unsafe_total:
        errors.append("architect_learning_unsafe_total_mismatch")
    if artifact.get("unsafe_write_counter_total") != 0:
        errors.append("architect_learning_unsafe_total_nonzero")

    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "cannot mutate policy",
        "cannot mutate strategies",
        "cannot update source weights",
        "cannot update model weights",
        "cannot update trust scores",
        "cannot change risk limits",
        "cannot count Phase 5 test trades toward Phase 7 proof",
    ):
        if phrase not in boundary:
            errors.append("architect_learning_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not artifact.get("event_log_path"):
            errors.append("architect_learning_event_log_path_missing")
        if not artifact.get("event_log_correlation_id"):
            errors.append("architect_learning_event_correlation_missing")
        if artifact.get("event_log_event_count") != 1:
            errors.append("architect_learning_event_log_count_mismatch")
    return sorted(set(errors))


def attach_phase6_architect_learning_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(event_log_path or (_runtime_dir(settings) / PHASE6_ARCHITECT_LEARNING_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PHASE6_ARCHITECT_LEARNING_EVENT_TYPE,
        PHASE6_ARCHITECT_LEARNING_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "summary_state": output.get("summary_state"),
            "source_approval_state": output.get("source_approval_state"),
            "recommendation_count": output.get("recommendation_count"),
            "active_recommendation_count": output.get("active_recommendation_count"),
            "blocked_recommendation_count": output.get("blocked_recommendation_count"),
            "approved_fact_count": output.get("approved_fact_count"),
            "policy_mutation_allowed": output.get("policy_mutation_allowed"),
            "strategy_mutation_allowed": output.get("strategy_mutation_allowed"),
            "risk_limit_update_allowed": output.get("risk_limit_update_allowed"),
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
    output["validation_errors"] = validate_phase6_architect_learning(output)
    if output["validation_errors"]:
        output["status"] = "blocked"
    return output, entry


def write_phase6_architect_learning(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase6_architect_learning_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase6_architect_learning_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase6_architect_learning(output)
        if output["validation_errors"]:
            output["status"] = "blocked"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase6_architect_learning(output)
    if output["validation_errors"]:
        output["status"] = "blocked"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE6_ARCHITECT_LEARNING_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "summary_state": output.get("summary_state"),
        "source_approval_state": output.get("source_approval_state"),
        "recommendation_count": output.get("recommendation_count"),
        "active_recommendation_count": output.get("active_recommendation_count"),
        "blocked_recommendation_count": output.get("blocked_recommendation_count"),
        "approved_fact_count": output.get("approved_fact_count"),
        "policy_mutation_allowed": output.get("policy_mutation_allowed"),
        "strategy_mutation_allowed": output.get("strategy_mutation_allowed"),
        "risk_limit_update_allowed": output.get("risk_limit_update_allowed"),
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
