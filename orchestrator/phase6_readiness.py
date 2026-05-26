"""Q6-0 Phase 6 re-entry and readiness gate.

This stage validates that Phase 6 can begin controlled, stage-by-stage work
after the Q5E handoff. It does not open learning writes, Knowledge Graph writes,
model-weight updates, trust-score updates, policy mutation, broker writes, live
endpoints, or Phase 7 proof credit.
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.phase5_phase6_handoff import (
    PHASE5_PHASE6_HANDOFF_RUNTIME_ARTIFACT,
    phase5_phase6_handoff_paths,
    validate_phase5_phase6_handoff,
)
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT


PHASE6_READINESS_SCHEMA_VERSION = 1
PHASE6_READINESS_RUNTIME_ARTIFACT = "phase6_readiness.json"
PHASE6_READINESS_HISTORY = "phase6_readiness_history.jsonl"
PHASE6_READINESS_EVENT_LOG = "phase6_readiness_events.jsonl"
PHASE6_READINESS_EVENT_TYPE = "phase6_readiness_recorded"
PHASE6_READINESS_COMPONENT = "phase6_readiness"

PHASE6_READINESS_SOURCE_REFS: tuple[str, ...] = (
    f"data/runtime/{PHASE5_PHASE6_HANDOFF_RUNTIME_ARTIFACT}",
    "data/runtime/phase5_certification.json",
    "data/runtime/phase5_paper_trade_drill.json",
    "data/runtime/phase5_execution_adapter_status.json",
    "data/runtime/phase5_position_monitor.json",
    "data/runtime/phase5_guarded_postmortem_due.json",
    "docs/qadam-phase-6-learning-loop-implementation-plan.md",
)

PHASE6_STAGE_SCOPE: tuple[dict[str, str], ...] = (
    {
        "stage": "Q6-1",
        "name": "Artifact Schema And Authority Ledger",
        "authority": "schema_only",
    },
    {
        "stage": "Q6-2",
        "name": "Learning Source Intake",
        "authority": "read_only",
    },
    {
        "stage": "Q6-3",
        "name": "Closed Trade And Outcome Schema",
        "authority": "read_only",
    },
    {
        "stage": "Q6-4",
        "name": "Postmortem Packet Contract",
        "authority": "draft_only",
    },
    {
        "stage": "Q6-5",
        "name": "Postmortem Agent Drafting",
        "authority": "draft_only",
    },
    {
        "stage": "Q6-6",
        "name": "Analysis Sub-Agent Packets",
        "authority": "draft_only",
    },
    {
        "stage": "Q6-7",
        "name": "Reducer And Review Gate",
        "authority": "approval_gate_only",
    },
    {
        "stage": "Q6-8",
        "name": "Outcome Linker",
        "authority": "link_only",
    },
    {
        "stage": "Q6-9",
        "name": "Learning Approval Ledger",
        "authority": "governance_only",
    },
    {
        "stage": "Q6-10",
        "name": "Knowledge Graph Staged Writes",
        "authority": "staged_write_only_after_approval",
    },
    {
        "stage": "Q6-11",
        "name": "Knowledge Graph Read Path",
        "authority": "read_path",
    },
    {
        "stage": "Q6-12",
        "name": "Model Weight Update Proposals",
        "authority": "proposal_only",
    },
    {
        "stage": "Q6-13",
        "name": "Trust Score Update Proposals",
        "authority": "proposal_only",
    },
    {
        "stage": "Q6-14",
        "name": "Shadow Strategy Runner",
        "authority": "replay_only",
    },
    {
        "stage": "Q6-15",
        "name": "Architect Learning Summary",
        "authority": "recommendation_only",
    },
    {
        "stage": "Q6-16",
        "name": "Journal And Cockpit Visibility",
        "authority": "visibility_only",
    },
    {
        "stage": "Q6-17",
        "name": "Phase 6 Certification",
        "authority": "certification_only",
    },
)

PHASE6_AUTHORITY_FLAGS: tuple[str, ...] = (
    "phase6_learning_loop_implementation_allowed",
    "phase6_postmortem_ingestion_allowed",
    "phase6_learning_write_allowed",
    "phase6_knowledge_graph_write_allowed",
    "phase6_model_weight_update_allowed",
    "phase6_trust_score_update_allowed",
    "phase6_shadow_strategy_runner_allowed",
    "phase6_architect_policy_mutation_allowed",
    "phase6_policy_mutation_allowed",
)

PHASE6_UNSAFE_COUNT_FIELDS: tuple[str, ...] = (
    "broker_post_called_count",
    "alpaca_post_called_count",
    "broker_write_allowed_count",
    "prediction_market_write_allowed_count",
    "crypto_perps_write_allowed_count",
    "live_endpoint_allowed_count",
    "live_capital_enabled_count",
    "phase7_proof_credit_allowed_count",
    "phase6_postmortem_ingestion_allowed_count",
    "phase6_learning_write_allowed_count",
    "phase6_knowledge_graph_write_allowed_count",
    "phase6_model_weight_update_allowed_count",
    "phase6_trust_score_update_allowed_count",
    "phase6_shadow_strategy_runner_allowed_count",
    "phase6_policy_mutation_allowed_count",
)

PHASE6_READINESS_BOUNDARY = (
    "Q6-0 is a Phase 6 re-entry gate only. It can confirm that Phase 5 is "
    "certified and that Q6-1 schema work may begin, but it cannot ingest "
    "postmortems, cannot write learning data, cannot write a Knowledge Graph, "
    "cannot update model weights, cannot update trust scores, cannot mutate "
    "policy, cannot call broker POST routes, cannot call Alpaca POST routes, "
    "cannot call live endpoints, cannot enable live capital, and cannot count "
    "Phase 5 test trades toward Phase 7 proof."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def phase6_readiness_paths(settings: Settings | None = None) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE6_READINESS_RUNTIME_ARTIFACT,
        runtime / PHASE6_READINESS_HISTORY,
        runtime / PHASE6_READINESS_EVENT_LOG,
    )


def phase6_authority_defaults() -> dict[str, bool]:
    return {field: False for field in PHASE6_AUTHORITY_FLAGS}


def _authority_ledger() -> dict[str, Any]:
    defaults = phase6_authority_defaults()
    return {
        "authority_schema_version": PHASE6_READINESS_SCHEMA_VERSION,
        "stage": "Q6-0",
        "authority_field_count": len(PHASE6_AUTHORITY_FLAGS),
        "explicit_authority_grant_count": 0,
        "q6_1_schema_stage_allowed": True,
        **defaults,
        "boundary": PHASE6_READINESS_BOUNDARY,
    }


def _source_posture() -> dict[str, Any]:
    return {
        "canonical_source_required": True,
        "canonical_source_count": EXPECTED_SOURCE_COUNT,
        "supplemental_source_bypass_allowed": False,
        "yahoo_finance_role": "supplemental_market_confirmation_only",
        "preference_mcp_role": "supplemental_multi_source_data_plane",
        "preference_mcp_source_36": False,
        "preference_paid_tools_allowed": False,
        "qctrl_role": "shadow_annotation_only",
        "source_quorum_bypass_allowed": False,
        "boundary": (
            "Phase 6 may use Yahoo Finance, Preference/PREF MCP, and Q-CTRL only "
            "as bounded supplemental context unless a later gate explicitly "
            "promotes a specific source role."
        ),
    }


def _provenance() -> dict[str, Any]:
    return {
        "source_refs": list(PHASE6_READINESS_SOURCE_REFS),
        "event_log_required": True,
        "raw_secret_exposed": False,
        "raw_payload_exposed": False,
        "local_path_exposed": False,
        "boundary": (
            "Q6-0 must be replayable from public-safe source refs and must not "
            "expose secrets, raw private payloads, or local-only absolute paths."
        ),
    }


def _count(artifact: dict[str, Any], field: str) -> int:
    return int(artifact.get(field, 0) or 0)


def _unsafe_counts(handoff: dict[str, Any]) -> dict[str, int]:
    return {field: _count(handoff, field) for field in PHASE6_UNSAFE_COUNT_FIELDS}


def _read_handoff(settings: Settings) -> tuple[dict[str, Any], bool, list[str]]:
    handoff_path, _, _ = phase5_phase6_handoff_paths(settings)
    handoff = _read_json(handoff_path) or {}
    recorded = bool(handoff)
    errors = validate_phase5_phase6_handoff(handoff) if recorded else ["handoff_missing"]
    return handoff, recorded, errors


def _blockers(
    *,
    handoff: dict[str, Any],
    handoff_recorded: bool,
    handoff_errors: list[str],
    unsafe_counts: dict[str, int],
) -> list[str]:
    blockers: list[str] = []
    if not handoff_recorded:
        blockers.append("phase5_phase6_handoff_artifact_missing")
    if handoff_errors:
        blockers.append("phase5_phase6_handoff_validation_errors")
    if handoff.get("status") != "eligible":
        blockers.append("phase5_phase6_handoff_not_eligible")
    if handoff.get("handoff_state") != "phase6_learning_loop_plan_ready":
        blockers.append("phase5_phase6_handoff_state_not_plan_ready")
    if handoff.get("phase5_certified") is not True:
        blockers.append("phase5_not_certified")
    if handoff.get("phase5_exit_gate") is not True:
        blockers.append("phase5_exit_gate_not_passed")
    if handoff.get("phase6_handoff_allowed") is not True:
        blockers.append("phase6_handoff_not_allowed")
    if handoff.get("phase6_learning_loop_plan_allowed") is not True:
        blockers.append("phase6_learning_loop_plan_not_allowed")
    if handoff.get("phase6_learning_loop_implementation_allowed") is not False:
        blockers.append("phase6_learning_loop_implementation_already_allowed")
    for flag in PHASE6_AUTHORITY_FLAGS:
        if handoff.get(flag, False) is not False:
            blockers.append(f"phase6_authority_already_enabled:{flag}")
    if handoff.get("phase7_proof_credit_allowed") is not False:
        blockers.append("phase7_proof_credit_allowed")
    if handoff.get("phase5_test_trades_count_for_phase7") is not False:
        blockers.append("phase5_test_trades_count_for_phase7")
    if handoff.get("paper_trade_drill_complete") is not True:
        blockers.append("paper_trade_drill_not_complete")
    if handoff.get("paper_trade_drill_exit_gate_passed") is not True:
        blockers.append("paper_trade_drill_exit_gate_not_passed")
    if _count(handoff, "paper_trade_drill_blocker_count") != 0:
        blockers.append("paper_trade_drill_blockers_present")
    for field in (
        "downstream_staging_allowed_count",
        "submitted_order_count",
        "mirrored_order_count",
        "closed_trade_count",
        "postmortem_due_count",
    ):
        if _count(handoff, field) < 1:
            blockers.append(f"handoff_missing_count:{field}")
    if _count(handoff, "failed_reconciliation_count") != 0:
        blockers.append("failed_reconciliation_present")
    if handoff.get("guarded_postmortem_due_ready") is not True:
        blockers.append("guarded_postmortem_due_not_ready")
    if _count(handoff, "blocker_count") != 0:
        blockers.append("phase5_phase6_handoff_blockers_present")
    for field, value in unsafe_counts.items():
        if value != 0:
            blockers.append(f"unsafe_count_nonzero:{field}")
    return sorted(set(blockers))


def build_phase6_readiness(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    handoff, handoff_recorded, handoff_errors = _read_handoff(settings)
    unsafe_counts = _unsafe_counts(handoff)
    blockers = _blockers(
        handoff=handoff,
        handoff_recorded=handoff_recorded,
        handoff_errors=handoff_errors,
        unsafe_counts=unsafe_counts,
    )
    re_entry_gate_passed = not blockers
    artifact = {
        "schema_version": PHASE6_READINESS_SCHEMA_VERSION,
        "artifact_type": "phase6_readiness",
        "artifact_id": "phase6:q6-0:re-entry-gate",
        "phase": "Q6",
        "stage": "Q6-0",
        "status": (
            "ready_for_q6_1_artifact_schema"
            if re_entry_gate_passed
            else "blocked_pending_phase5_phase6_handoff"
        ),
        "readiness_state": (
            "phase6_re_entry_gate_passed"
            if re_entry_gate_passed
            else "phase6_re_entry_gate_blocked"
        ),
        "generated_at": _now(),
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
        "authority_ledger": _authority_ledger(),
        "source_posture": _source_posture(),
        "provenance": _provenance(),
        "boundary": PHASE6_READINESS_BOUNDARY,
        **phase6_authority_defaults(),
        "canonical_source_count": EXPECTED_SOURCE_COUNT,
        "q5e_handoff_artifact_recorded": handoff_recorded,
        "q5e_handoff_validation_error_count": len(handoff_errors),
        "q5e_handoff_status": str(handoff.get("status") or "missing"),
        "q5e_handoff_state": str(handoff.get("handoff_state") or "missing"),
        "phase5_certified": handoff.get("phase5_certified") is True,
        "phase5_exit_gate": handoff.get("phase5_exit_gate") is True,
        "phase6_handoff_allowed": handoff.get("phase6_handoff_allowed") is True,
        "phase6_learning_loop_plan_allowed": (
            handoff.get("phase6_learning_loop_plan_allowed") is True
        ),
        "phase7_planning_allowed": handoff.get("phase7_planning_allowed") is True,
        "phase7_proof_credit_allowed": handoff.get("phase7_proof_credit_allowed") is True,
        "phase5_test_trades_count_for_phase7": (
            handoff.get("phase5_test_trades_count_for_phase7") is True
        ),
        "paper_trade_drill_complete": handoff.get("paper_trade_drill_complete") is True,
        "paper_trade_drill_exit_gate_passed": (
            handoff.get("paper_trade_drill_exit_gate_passed") is True
        ),
        "paper_trade_drill_blocker_count": _count(handoff, "paper_trade_drill_blocker_count"),
        "downstream_staging_allowed_count": _count(handoff, "downstream_staging_allowed_count"),
        "submitted_order_count": _count(handoff, "submitted_order_count"),
        "mirrored_order_count": _count(handoff, "mirrored_order_count"),
        "open_position_count": _count(handoff, "open_position_count"),
        "closed_trade_count": _count(handoff, "closed_trade_count"),
        "postmortem_due_count": _count(handoff, "postmortem_due_count"),
        "failed_reconciliation_count": _count(handoff, "failed_reconciliation_count"),
        "guarded_postmortem_due_ready": handoff.get("guarded_postmortem_due_ready") is True,
        "guarded_postmortem_due_ref": handoff.get("guarded_postmortem_due_ref"),
        "phase6_frozen_scope": deepcopy(list(PHASE6_STAGE_SCOPE)),
        "phase6_frozen_scope_count": len(PHASE6_STAGE_SCOPE),
        "phase6_re_entry_gate_passed": re_entry_gate_passed,
        "q6_1_artifact_schema_stage_allowed": re_entry_gate_passed,
        "phase6_controlled_stage_work_allowed": re_entry_gate_passed,
        "unsafe_write_counter_total": sum(unsafe_counts.values()),
        "blockers": blockers,
        "blocker_count": len(blockers),
        "recommended_next_stage": "Q6-1 Artifact Schema And Authority Ledger",
        **unsafe_counts,
    }
    artifact["validation_errors"] = validate_phase6_readiness(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "error"
    return artifact


def validate_phase6_readiness(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schema_version",
        "artifact_type",
        "artifact_id",
        "phase",
        "stage",
        "status",
        "readiness_state",
        "generated_at",
        "public_safe",
        "event_log_required",
        "event_log_written",
        "authority_ledger",
        "source_posture",
        "provenance",
        "boundary",
        "q5e_handoff_artifact_recorded",
        "q5e_handoff_validation_error_count",
        "q5e_handoff_status",
        "q5e_handoff_state",
        "phase5_certified",
        "phase5_exit_gate",
        "phase6_handoff_allowed",
        "phase6_learning_loop_plan_allowed",
        "phase6_learning_loop_implementation_allowed",
        "phase6_learning_write_allowed",
        "phase6_knowledge_graph_write_allowed",
        "phase7_proof_credit_allowed",
        "paper_trade_drill_complete",
        "paper_trade_drill_exit_gate_passed",
        "closed_trade_count",
        "postmortem_due_count",
        "phase6_frozen_scope",
        "phase6_frozen_scope_count",
        "phase6_re_entry_gate_passed",
        "q6_1_artifact_schema_stage_allowed",
        "phase6_controlled_stage_work_allowed",
        "unsafe_write_counter_total",
        "blockers",
        "blocker_count",
        "recommended_next_stage",
    }
    missing = sorted(required_fields - set(artifact))
    if missing:
        errors.append("phase6_readiness_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PHASE6_READINESS_SCHEMA_VERSION:
        errors.append("phase6_readiness_schema_version_mismatch")
    if artifact.get("artifact_type") != "phase6_readiness":
        errors.append("phase6_readiness_artifact_type_mismatch")
    if artifact.get("phase") != "Q6" or artifact.get("stage") != "Q6-0":
        errors.append("phase6_readiness_phase_stage_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("phase6_readiness_not_public_safe")
    if artifact.get("event_log_required") is not True:
        errors.append("phase6_readiness_event_log_not_required")
    blockers = artifact.get("blockers", [])
    if not isinstance(blockers, list):
        errors.append("phase6_readiness_blockers_not_list")
        blockers = []
    if artifact.get("blocker_count") != len(blockers):
        errors.append("phase6_readiness_blocker_count_mismatch")
    if artifact.get("phase6_frozen_scope_count") != len(
        artifact.get("phase6_frozen_scope", [])
    ):
        errors.append("phase6_readiness_scope_count_mismatch")
    if artifact.get("phase6_frozen_scope_count") != len(PHASE6_STAGE_SCOPE):
        errors.append("phase6_readiness_scope_incomplete")
    stage_names = {
        record.get("stage")
        for record in artifact.get("phase6_frozen_scope", [])
        if isinstance(record, dict)
    }
    if stage_names != {record["stage"] for record in PHASE6_STAGE_SCOPE}:
        errors.append("phase6_readiness_scope_stage_mismatch")
    for field in PHASE6_AUTHORITY_FLAGS:
        if artifact.get(field) is not False:
            errors.append(f"phase6_readiness_authority_enabled:{field}")
    if artifact.get("phase7_proof_credit_allowed") is not False:
        errors.append("phase7_proof_credit_allowed")
    if artifact.get("phase5_test_trades_count_for_phase7") is not False:
        errors.append("phase5_test_trades_count_for_phase7")
    for field in PHASE6_UNSAFE_COUNT_FIELDS:
        if int(artifact.get(field, 0) or 0) != 0:
            errors.append(f"phase6_readiness_unsafe_count_nonzero:{field}")
    unsafe_total = sum(int(artifact.get(field, 0) or 0) for field in PHASE6_UNSAFE_COUNT_FIELDS)
    if artifact.get("unsafe_write_counter_total") != unsafe_total:
        errors.append("phase6_readiness_unsafe_total_mismatch")
    if artifact.get("unsafe_write_counter_total") != 0:
        errors.append("phase6_readiness_unsafe_total_nonzero")
    provenance = artifact.get("provenance", {})
    if not isinstance(provenance, dict):
        errors.append("phase6_readiness_provenance_missing")
        provenance = {}
    for ref in provenance.get("source_refs", []) or []:
        if str(ref).startswith("/"):
            errors.append("phase6_readiness_local_path_leak")
            break
    for field in ("raw_secret_exposed", "raw_payload_exposed", "local_path_exposed"):
        if provenance.get(field) is not False:
            errors.append(f"phase6_readiness_provenance_unsafe:{field}")
    source_posture = artifact.get("source_posture", {})
    if not isinstance(source_posture, dict):
        errors.append("phase6_readiness_source_posture_missing")
        source_posture = {}
    if source_posture.get("canonical_source_count") != EXPECTED_SOURCE_COUNT:
        errors.append("phase6_readiness_canonical_source_count_mismatch")
    if source_posture.get("yahoo_finance_role") != "supplemental_market_confirmation_only":
        errors.append("phase6_readiness_yahoo_role_invalid")
    if source_posture.get("preference_mcp_role") != "supplemental_multi_source_data_plane":
        errors.append("phase6_readiness_preference_role_invalid")
    if source_posture.get("preference_mcp_source_36") is not False:
        errors.append("phase6_readiness_preference_source36_enabled")
    if source_posture.get("qctrl_role") != "shadow_annotation_only":
        errors.append("phase6_readiness_qctrl_role_invalid")
    if source_posture.get("source_quorum_bypass_allowed") is not False:
        errors.append("phase6_readiness_source_quorum_bypass")
    gate_passed = artifact.get("phase6_re_entry_gate_passed") is True
    if gate_passed:
        if artifact.get("status") != "ready_for_q6_1_artifact_schema":
            errors.append("phase6_readiness_status_not_ready")
        if artifact.get("readiness_state") != "phase6_re_entry_gate_passed":
            errors.append("phase6_readiness_state_not_passed")
        if blockers:
            errors.append("phase6_readiness_passed_with_blockers")
        for field in (
            "q5e_handoff_artifact_recorded",
            "phase5_certified",
            "phase5_exit_gate",
            "phase6_handoff_allowed",
            "phase6_learning_loop_plan_allowed",
            "phase7_planning_allowed",
            "paper_trade_drill_complete",
            "paper_trade_drill_exit_gate_passed",
            "guarded_postmortem_due_ready",
            "q6_1_artifact_schema_stage_allowed",
            "phase6_controlled_stage_work_allowed",
        ):
            if artifact.get(field) is not True:
                errors.append(f"phase6_readiness_passed_missing_true:{field}")
        if artifact.get("q5e_handoff_status") != "eligible":
            errors.append("phase6_readiness_handoff_status_not_eligible")
        if artifact.get("q5e_handoff_state") != "phase6_learning_loop_plan_ready":
            errors.append("phase6_readiness_handoff_state_invalid")
        if int(artifact.get("q5e_handoff_validation_error_count", 0) or 0) != 0:
            errors.append("phase6_readiness_handoff_validation_errors")
        if int(artifact.get("paper_trade_drill_blocker_count", 0) or 0) != 0:
            errors.append("phase6_readiness_drill_blockers")
        for field in (
            "downstream_staging_allowed_count",
            "submitted_order_count",
            "mirrored_order_count",
            "closed_trade_count",
            "postmortem_due_count",
        ):
            if int(artifact.get(field, 0) or 0) < 1:
                errors.append(f"phase6_readiness_missing_count:{field}")
        if int(artifact.get("failed_reconciliation_count", 0) or 0) != 0:
            errors.append("phase6_readiness_failed_reconciliation")
    else:
        if artifact.get("status") != "blocked_pending_phase5_phase6_handoff":
            errors.append("phase6_readiness_blocked_status_mismatch")
        if artifact.get("readiness_state") != "phase6_re_entry_gate_blocked":
            errors.append("phase6_readiness_blocked_state_mismatch")
        if not blockers:
            errors.append("phase6_readiness_blocked_without_blockers")
        if artifact.get("q6_1_artifact_schema_stage_allowed") is not False:
            errors.append("phase6_readiness_q6_1_allowed_while_blocked")
        if artifact.get("phase6_controlled_stage_work_allowed") is not False:
            errors.append("phase6_readiness_controlled_work_allowed_while_blocked")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "cannot ingest postmortems",
        "cannot write learning data",
        "cannot write a Knowledge Graph",
        "cannot call broker POST routes",
        "cannot enable live capital",
        "cannot count Phase 5 test trades toward Phase 7 proof",
    ):
        if phrase not in boundary:
            errors.append("phase6_readiness_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("phase6_readiness_event_log_path_missing")
        if not str(artifact.get("event_log_correlation_id") or "").strip():
            errors.append("phase6_readiness_event_correlation_missing")
        if artifact.get("event_log_event_count") != 1:
            errors.append("phase6_readiness_event_log_count_mismatch")
    return sorted(set(errors))


def attach_phase6_readiness_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(event_log_path or (_runtime_dir(settings) / PHASE6_READINESS_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PHASE6_READINESS_EVENT_TYPE,
        PHASE6_READINESS_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "readiness_state": output.get("readiness_state"),
            "phase6_re_entry_gate_passed": output.get("phase6_re_entry_gate_passed"),
            "phase6_learning_loop_plan_allowed": output.get(
                "phase6_learning_loop_plan_allowed"
            ),
            "phase6_learning_loop_implementation_allowed": output.get(
                "phase6_learning_loop_implementation_allowed"
            ),
            "phase6_learning_write_allowed": output.get("phase6_learning_write_allowed"),
            "phase6_knowledge_graph_write_allowed": output.get(
                "phase6_knowledge_graph_write_allowed"
            ),
            "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
            "unsafe_write_counter_total": output.get("unsafe_write_counter_total"),
            "recommended_next_stage": output.get("recommended_next_stage"),
            "boundary": output.get("boundary"),
        },
    )
    output["recorded"] = True
    output["event_log_written"] = True
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = 1
    output["event_log_correlation_id"] = entry.correlation_id
    output["event_log_created_at"] = entry.created_at
    output["validation_errors"] = validate_phase6_readiness(output)
    if output["validation_errors"]:
        output["status"] = "error"
    return output, entry


def write_phase6_readiness(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase6_readiness_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase6_readiness_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase6_readiness(output)
        if output["validation_errors"]:
            output["status"] = "error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase6_readiness(output)
    if output["validation_errors"]:
        output["status"] = "error"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE6_READINESS_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "readiness_state": output.get("readiness_state"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "phase6_re_entry_gate_passed": output.get("phase6_re_entry_gate_passed"),
        "phase6_learning_loop_plan_allowed": output.get(
            "phase6_learning_loop_plan_allowed"
        ),
        "phase6_learning_loop_implementation_allowed": output.get(
            "phase6_learning_loop_implementation_allowed"
        ),
        "phase6_learning_write_allowed": output.get("phase6_learning_write_allowed"),
        "phase6_knowledge_graph_write_allowed": output.get(
            "phase6_knowledge_graph_write_allowed"
        ),
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
