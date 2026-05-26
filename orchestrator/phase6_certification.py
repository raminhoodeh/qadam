"""Q6-17 Phase 6 certification gate.

This gate aggregates Q6-0 through Q6-16 and decides whether Phase 6 can hand
off to Phase 7 demo-proof planning. It is intentionally fail-closed: implemented
and safe Q6 stages are not enough to certify Phase 6 while postmortems and
learning actions are still pending review.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Callable

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.phase6_architect_learning import (
    PHASE6_ARCHITECT_LEARNING_RUNTIME_ARTIFACT,
    build_phase6_architect_learning,
    validate_phase6_architect_learning,
)
from orchestrator.phase6_artifacts import (
    PHASE6_ARTIFACT_SCHEMA_VERSION,
    PHASE6_AUTHORITY_FIELDS,
    PHASE6_UNSAFE_COUNT_FIELDS,
    build_phase6_sample_artifacts,
    phase6_artifact_bundle_summary,
    phase6_authority_defaults,
    phase6_authority_ledger,
    phase6_event_contract,
    phase6_provenance,
    phase6_source_posture,
    phase6_unsafe_counter_defaults,
    validate_phase6_artifact,
)
from orchestrator.phase6_closed_trade_outcome import (
    PHASE6_CLOSED_TRADE_OUTCOME_RUNTIME_ARTIFACT,
    build_phase6_closed_trade_outcome,
    validate_phase6_closed_trade_outcome,
)
from orchestrator.phase6_cockpit_visibility import (
    PHASE6_COCKPIT_VISIBILITY_RUNTIME_ARTIFACT,
    build_phase6_cockpit_visibility,
    validate_phase6_cockpit_visibility,
)
from orchestrator.phase6_knowledge_graph_read_path import (
    PHASE6_KNOWLEDGE_GRAPH_READ_PATH_RUNTIME_ARTIFACT,
    build_phase6_knowledge_graph_read_path,
    validate_phase6_knowledge_graph_read_path,
)
from orchestrator.phase6_knowledge_graph_staging import (
    PHASE6_KNOWLEDGE_GRAPH_STAGING_RUNTIME_ARTIFACT,
    build_phase6_knowledge_graph_staging,
    validate_phase6_knowledge_graph_staging,
)
from orchestrator.phase6_learning_approval import (
    PHASE6_LEARNING_APPROVAL_RUNTIME_ARTIFACT,
    build_phase6_learning_approval,
    validate_phase6_learning_approval,
)
from orchestrator.phase6_learning_source_intake import (
    PHASE6_LEARNING_SOURCE_INTAKE_RUNTIME_ARTIFACT,
    build_phase6_learning_source_intake,
    validate_phase6_learning_source_intake,
)
from orchestrator.phase6_model_weight_updates import (
    PHASE6_MODEL_WEIGHT_UPDATES_RUNTIME_ARTIFACT,
    build_phase6_model_weight_updates,
    validate_phase6_model_weight_updates,
)
from orchestrator.phase6_outcome_linker import (
    PHASE6_OUTCOME_LINKER_RUNTIME_ARTIFACT,
    build_phase6_outcome_linker,
    validate_phase6_outcome_linker,
)
from orchestrator.phase6_postmortem_agent import (
    PHASE6_POSTMORTEM_DRAFT_RUNTIME_ARTIFACT,
    build_phase6_postmortem_draft,
    validate_phase6_postmortem_draft,
)
from orchestrator.phase6_postmortem_analysis import (
    PHASE6_POSTMORTEM_ANALYSIS_RUNTIME_ARTIFACT,
    build_phase6_postmortem_analysis,
    validate_phase6_postmortem_analysis,
)
from orchestrator.phase6_postmortem_packets import (
    PHASE6_POSTMORTEM_PACKET_CONTRACT_RUNTIME_ARTIFACT,
    build_phase6_postmortem_packet_contract,
    validate_phase6_postmortem_packet_contract,
)
from orchestrator.phase6_postmortem_reducer import (
    PHASE6_POSTMORTEM_REDUCER_RUNTIME_ARTIFACT,
    build_phase6_postmortem_reducer,
    validate_phase6_postmortem_reducer,
)
from orchestrator.phase6_readiness import (
    PHASE6_READINESS_RUNTIME_ARTIFACT,
    build_phase6_readiness,
    validate_phase6_readiness,
)
from orchestrator.phase6_shadow_strategy_runner import (
    PHASE6_SHADOW_STRATEGY_RUNNER_RUNTIME_ARTIFACT,
    build_phase6_shadow_strategy_runner,
    validate_phase6_shadow_strategy_runner,
)
from orchestrator.phase6_trust_score_updates import (
    PHASE6_TRUST_SCORE_UPDATES_RUNTIME_ARTIFACT,
    build_phase6_trust_score_updates,
    validate_phase6_trust_score_updates,
)


PHASE6_CERTIFICATION_SCHEMA_VERSION = 1
PHASE6_CERTIFICATION_RUNTIME_ARTIFACT = "phase6_certification.json"
PHASE6_CERTIFICATION_HISTORY = "phase6_certification_history.jsonl"
PHASE6_CERTIFICATION_EVENT_LOG = "phase6_certification_events.jsonl"
PHASE6_CERTIFICATION_EVENT_TYPE = "phase6_certification_recorded"
PHASE6_CERTIFICATION_COMPONENT = "phase6_certification"

PHASE6_CERTIFICATION_REQUIRED_INPUT_STAGES: tuple[str, ...] = (
    "Q6-0",
    "Q6-1",
    "Q6-2",
    "Q6-3",
    "Q6-4",
    "Q6-5",
    "Q6-6",
    "Q6-7",
    "Q6-8",
    "Q6-9",
    "Q6-10",
    "Q6-11",
    "Q6-12",
    "Q6-13",
    "Q6-14",
    "Q6-15",
    "Q6-16",
)

PHASE6_CERTIFICATION_SOURCE_REFS: tuple[str, ...] = (
    f"data/runtime/{PHASE6_READINESS_RUNTIME_ARTIFACT}",
    "orchestrator/phase6_artifacts.py",
    f"data/runtime/{PHASE6_LEARNING_SOURCE_INTAKE_RUNTIME_ARTIFACT}",
    f"data/runtime/{PHASE6_CLOSED_TRADE_OUTCOME_RUNTIME_ARTIFACT}",
    f"data/runtime/{PHASE6_POSTMORTEM_PACKET_CONTRACT_RUNTIME_ARTIFACT}",
    f"data/runtime/{PHASE6_POSTMORTEM_DRAFT_RUNTIME_ARTIFACT}",
    f"data/runtime/{PHASE6_POSTMORTEM_ANALYSIS_RUNTIME_ARTIFACT}",
    f"data/runtime/{PHASE6_POSTMORTEM_REDUCER_RUNTIME_ARTIFACT}",
    f"data/runtime/{PHASE6_OUTCOME_LINKER_RUNTIME_ARTIFACT}",
    f"data/runtime/{PHASE6_LEARNING_APPROVAL_RUNTIME_ARTIFACT}",
    f"data/runtime/{PHASE6_KNOWLEDGE_GRAPH_STAGING_RUNTIME_ARTIFACT}",
    f"data/runtime/{PHASE6_KNOWLEDGE_GRAPH_READ_PATH_RUNTIME_ARTIFACT}",
    f"data/runtime/{PHASE6_MODEL_WEIGHT_UPDATES_RUNTIME_ARTIFACT}",
    f"data/runtime/{PHASE6_TRUST_SCORE_UPDATES_RUNTIME_ARTIFACT}",
    f"data/runtime/{PHASE6_SHADOW_STRATEGY_RUNNER_RUNTIME_ARTIFACT}",
    f"data/runtime/{PHASE6_ARCHITECT_LEARNING_RUNTIME_ARTIFACT}",
    f"data/runtime/{PHASE6_COCKPIT_VISIBILITY_RUNTIME_ARTIFACT}",
)

PHASE6_CERTIFICATION_BOUNDARY = (
    "Q6-17 is a certification gate only. It can certify Phase 6 only after "
    "all scoped postmortems are reviewed and all learning actions are approved "
    "or explicitly deferred. It cannot approve learning, cannot write learning "
    "data, cannot write or commit a Knowledge Graph, cannot apply model "
    "weights, cannot apply trust scores, cannot mutate policy or strategies, "
    "cannot call broker POST routes, cannot call live endpoints, cannot enable "
    "live capital, cannot grant Phase 7 proof credit, and cannot let Phase 5 "
    "test trades count toward Phase 7 proof."
)

PUBLIC_STATUS_FIELDS: tuple[str, ...] = (
    "schema_version",
    "phase6_certification_schema_version",
    "artifact_type",
    "artifact_id",
    "phase",
    "stage",
    "status",
    "stage_status",
    "certification_state",
    "generated_at",
    "public_safe",
    "recorded",
    "event_log_required",
    "event_log_written",
    "event_log_event_count",
    "validation_error_count",
    "phase6_certified",
    "phase6_complete",
    "phase6_exit_gate",
    "phase7_demo_proof_planning_allowed",
    "phase7_proof_credit_allowed",
    "phase5_test_trades_count_for_phase7",
    "required_input_stage_count",
    "input_gate_count",
    "input_gate_passed_count",
    "input_gate_blocked_count",
    "certification_blockers",
    "certification_blocker_count",
    "postmortem_due_count",
    "postmortem_resolved_count",
    "postmortem_explicitly_deferred_count",
    "unresolved_postmortem_count",
    "reviewed_postmortem_coverage_satisfied",
    "approval_state",
    "approval_logged",
    "proposed_action_count",
    "approved_action_count",
    "explicitly_deferred_action_count",
    "pending_review_action_count",
    "learning_actions_review_satisfied",
    "knowledge_graph_requirement_satisfied",
    "knowledge_graph_staged_entry_count",
    "knowledge_graph_candidate_action_count",
    "knowledge_graph_read_result_count",
    "model_weight_proposal_count",
    "trust_score_proposal_count",
    "shadow_replay_variant_count",
    "architect_recommendation_count",
    "cockpit_visibility_status",
    "cockpit_backend_derived",
    "cockpit_ui_inferred_readiness_count",
    "blocking_unsafe_count",
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
    "unsafe_write_counter_total",
    "gate_records",
    "recommended_next_stage",
    "boundary",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _repo_root(settings: Settings | None = None) -> Path:
    return _runtime_dir(settings).parent.parent


def _path(ref: str, settings: Settings | None = None) -> Path:
    return _repo_root(settings) / ref


def _read_json_ref(ref: str, settings: Settings | None = None) -> dict[str, Any] | None:
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


def _bool(value: Any) -> bool:
    return value is True


def _authority_ledger(phase7_demo_allowed: bool) -> dict[str, Any]:
    ledger = phase6_authority_ledger()
    ledger["stage"] = "Q6-17"
    ledger["boundary"] = PHASE6_CERTIFICATION_BOUNDARY
    if phase7_demo_allowed:
        ledger["phase7_demo_proof_planning_allowed"] = True
        ledger["explicit_authority_grant_count"] = 1
    return ledger


def _provenance() -> dict[str, Any]:
    output = phase6_provenance(PHASE6_CERTIFICATION_SOURCE_REFS)
    output["execution_evidence_refs"] = [
        f"data/runtime/{PHASE6_CLOSED_TRADE_OUTCOME_RUNTIME_ARTIFACT}",
        f"data/runtime/{PHASE6_OUTCOME_LINKER_RUNTIME_ARTIFACT}",
    ]
    output["market_context_refs"] = [
        f"data/runtime/{PHASE6_LEARNING_SOURCE_INTAKE_RUNTIME_ARTIFACT}",
        f"data/runtime/{PHASE6_COCKPIT_VISIBILITY_RUNTIME_ARTIFACT}",
    ]
    output["model_interpretation_refs"] = [
        f"data/runtime/{PHASE6_MODEL_WEIGHT_UPDATES_RUNTIME_ARTIFACT}",
        f"data/runtime/{PHASE6_TRUST_SCORE_UPDATES_RUNTIME_ARTIFACT}",
        f"data/runtime/{PHASE6_SHADOW_STRATEGY_RUNNER_RUNTIME_ARTIFACT}",
    ]
    output["governance_refs"] = [
        f"data/runtime/{PHASE6_POSTMORTEM_REDUCER_RUNTIME_ARTIFACT}",
        f"data/runtime/{PHASE6_LEARNING_APPROVAL_RUNTIME_ARTIFACT}",
        f"data/runtime/{PHASE6_ARCHITECT_LEARNING_RUNTIME_ARTIFACT}",
    ]
    return output


def phase6_certification_paths(settings: Settings | None = None) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE6_CERTIFICATION_RUNTIME_ARTIFACT,
        runtime / PHASE6_CERTIFICATION_HISTORY,
        runtime / PHASE6_CERTIFICATION_EVENT_LOG,
    )


def _runtime_or_build(
    settings: Settings,
    artifact_ref: str,
    builder: Callable[..., dict[str, Any]],
    validator: Callable[[dict[str, Any]], list[str]],
) -> tuple[dict[str, Any], bool, list[str]]:
    runtime = _read_json_ref(artifact_ref, settings)
    recorded = runtime is not None
    bundle = runtime or builder(settings=settings)
    return bundle, recorded, list(validator(bundle))


def _artifact_schema_gate() -> tuple[dict[str, Any], bool, list[str]]:
    summary = phase6_artifact_bundle_summary(build_phase6_sample_artifacts())
    return summary, True, list(summary.get("errors", []) or [])


def _gate_record(
    *,
    source_stage: str,
    label: str,
    artifact_key: str,
    source_ref: str,
    bundle: dict[str, Any],
    recorded: bool,
    validation_errors: list[str],
    pass_conditions: dict[str, bool],
) -> dict[str, Any]:
    failed_conditions = sorted(key for key, passed in pass_conditions.items() if not passed)
    unsafe_counts = {
        field: _int(bundle.get(field))
        for field in PHASE6_UNSAFE_COUNT_FIELDS
        if _int(bundle.get(field)) != 0
    }
    authority_enabled_fields = [
        field for field in PHASE6_AUTHORITY_FIELDS if bundle.get(field) is True
    ]
    backend_status = (
        "passed"
        if recorded
        and not validation_errors
        and not failed_conditions
        and not unsafe_counts
        and not authority_enabled_fields
        else "blocked"
    )
    return {
        "schema_version": PHASE6_ARTIFACT_SCHEMA_VERSION,
        "phase6_certification_schema_version": PHASE6_CERTIFICATION_SCHEMA_VERSION,
        "artifact_type": "phase6_certification_gate",
        "artifact_id": f"phase6:q6-17:gate:{source_stage.lower()}",
        "phase": "Q6",
        "stage": "Q6-17",
        "source_stage": source_stage,
        "label": label,
        "artifact_key": artifact_key,
        "source_ref": source_ref,
        "source_artifact_id": bundle.get("artifact_id"),
        "source_status": bundle.get("status", "unknown"),
        "backend_status": backend_status,
        "display_status": backend_status,
        "display_derived_from_backend": True,
        "ui_inferred_readiness": False,
        "gate_passed": backend_status == "passed",
        "recorded": recorded,
        "validation_error_count": len(validation_errors),
        "validation_errors": validation_errors,
        "pass_conditions": pass_conditions,
        "failed_conditions": failed_conditions,
        "unsafe_counts": unsafe_counts,
        "authority_enabled_fields": authority_enabled_fields,
        "event_log_required": True,
        "event_log_written": False,
        "event_log_correlation_id": None,
        "public_safe": True,
        "phase7_demo_proof_planning_allowed": False,
        "phase7_proof_credit_allowed": False,
        "phase5_test_trades_count_for_phase7": False,
        **phase6_authority_defaults(),
        **phase6_unsafe_counter_defaults(),
        "boundary": PHASE6_CERTIFICATION_BOUNDARY,
    }


def _source_gates(settings: Settings) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    artifacts: dict[str, dict[str, Any]] = {}

    readiness_ref = f"data/runtime/{PHASE6_READINESS_RUNTIME_ARTIFACT}"
    readiness, readiness_recorded, readiness_errors = _runtime_or_build(
        settings,
        readiness_ref,
        build_phase6_readiness,
        validate_phase6_readiness,
    )
    artifacts["readiness"] = readiness

    schema_summary, schema_recorded, schema_errors = _artifact_schema_gate()
    artifacts["artifact_schema"] = schema_summary

    source_ref = f"data/runtime/{PHASE6_LEARNING_SOURCE_INTAKE_RUNTIME_ARTIFACT}"
    source_intake, source_recorded, source_errors = _runtime_or_build(
        settings,
        source_ref,
        build_phase6_learning_source_intake,
        validate_phase6_learning_source_intake,
    )
    artifacts["source_intake"] = source_intake

    outcome_ref = f"data/runtime/{PHASE6_CLOSED_TRADE_OUTCOME_RUNTIME_ARTIFACT}"
    outcome, outcome_recorded, outcome_errors = _runtime_or_build(
        settings,
        outcome_ref,
        build_phase6_closed_trade_outcome,
        validate_phase6_closed_trade_outcome,
    )
    artifacts["closed_trade_outcome"] = outcome

    packet_ref = f"data/runtime/{PHASE6_POSTMORTEM_PACKET_CONTRACT_RUNTIME_ARTIFACT}"
    packet, packet_recorded, packet_errors = _runtime_or_build(
        settings,
        packet_ref,
        build_phase6_postmortem_packet_contract,
        validate_phase6_postmortem_packet_contract,
    )
    artifacts["postmortem_packet"] = packet

    draft_ref = f"data/runtime/{PHASE6_POSTMORTEM_DRAFT_RUNTIME_ARTIFACT}"
    draft, draft_recorded, draft_errors = _runtime_or_build(
        settings,
        draft_ref,
        build_phase6_postmortem_draft,
        validate_phase6_postmortem_draft,
    )
    artifacts["postmortem_draft"] = draft

    analysis_ref = f"data/runtime/{PHASE6_POSTMORTEM_ANALYSIS_RUNTIME_ARTIFACT}"
    analysis, analysis_recorded, analysis_errors = _runtime_or_build(
        settings,
        analysis_ref,
        build_phase6_postmortem_analysis,
        validate_phase6_postmortem_analysis,
    )
    artifacts["postmortem_analysis"] = analysis

    reducer_ref = f"data/runtime/{PHASE6_POSTMORTEM_REDUCER_RUNTIME_ARTIFACT}"
    reducer, reducer_recorded, reducer_errors = _runtime_or_build(
        settings,
        reducer_ref,
        build_phase6_postmortem_reducer,
        validate_phase6_postmortem_reducer,
    )
    artifacts["postmortem_reducer"] = reducer

    linker_ref = f"data/runtime/{PHASE6_OUTCOME_LINKER_RUNTIME_ARTIFACT}"
    linker, linker_recorded, linker_errors = _runtime_or_build(
        settings,
        linker_ref,
        build_phase6_outcome_linker,
        validate_phase6_outcome_linker,
    )
    artifacts["outcome_linker"] = linker

    approval_ref = f"data/runtime/{PHASE6_LEARNING_APPROVAL_RUNTIME_ARTIFACT}"
    approval, approval_recorded, approval_errors = _runtime_or_build(
        settings,
        approval_ref,
        build_phase6_learning_approval,
        validate_phase6_learning_approval,
    )
    artifacts["approval"] = approval

    kg_staging_ref = f"data/runtime/{PHASE6_KNOWLEDGE_GRAPH_STAGING_RUNTIME_ARTIFACT}"
    kg_staging, kg_staging_recorded, kg_staging_errors = _runtime_or_build(
        settings,
        kg_staging_ref,
        build_phase6_knowledge_graph_staging,
        validate_phase6_knowledge_graph_staging,
    )
    artifacts["knowledge_graph_staging"] = kg_staging

    kg_read_ref = f"data/runtime/{PHASE6_KNOWLEDGE_GRAPH_READ_PATH_RUNTIME_ARTIFACT}"
    kg_read, kg_read_recorded, kg_read_errors = _runtime_or_build(
        settings,
        kg_read_ref,
        build_phase6_knowledge_graph_read_path,
        validate_phase6_knowledge_graph_read_path,
    )
    artifacts["knowledge_graph_read"] = kg_read

    model_ref = f"data/runtime/{PHASE6_MODEL_WEIGHT_UPDATES_RUNTIME_ARTIFACT}"
    model_weight, model_recorded, model_errors = _runtime_or_build(
        settings,
        model_ref,
        build_phase6_model_weight_updates,
        validate_phase6_model_weight_updates,
    )
    artifacts["model_weight_updates"] = model_weight

    trust_ref = f"data/runtime/{PHASE6_TRUST_SCORE_UPDATES_RUNTIME_ARTIFACT}"
    trust_score, trust_recorded, trust_errors = _runtime_or_build(
        settings,
        trust_ref,
        build_phase6_trust_score_updates,
        validate_phase6_trust_score_updates,
    )
    artifacts["trust_score_updates"] = trust_score

    shadow_ref = f"data/runtime/{PHASE6_SHADOW_STRATEGY_RUNNER_RUNTIME_ARTIFACT}"
    shadow, shadow_recorded, shadow_errors = _runtime_or_build(
        settings,
        shadow_ref,
        build_phase6_shadow_strategy_runner,
        validate_phase6_shadow_strategy_runner,
    )
    artifacts["shadow_strategy_runner"] = shadow

    architect_ref = f"data/runtime/{PHASE6_ARCHITECT_LEARNING_RUNTIME_ARTIFACT}"
    architect, architect_recorded, architect_errors = _runtime_or_build(
        settings,
        architect_ref,
        build_phase6_architect_learning,
        validate_phase6_architect_learning,
    )
    artifacts["architect_learning"] = architect

    visibility_ref = f"data/runtime/{PHASE6_COCKPIT_VISIBILITY_RUNTIME_ARTIFACT}"
    visibility, visibility_recorded, visibility_errors = _runtime_or_build(
        settings,
        visibility_ref,
        build_phase6_cockpit_visibility,
        validate_phase6_cockpit_visibility,
    )
    artifacts["cockpit_visibility"] = visibility

    gates = [
        _gate_record(
            source_stage="Q6-0",
            label="Re-entry and plan gate",
            artifact_key="phase6_readiness",
            source_ref=readiness_ref,
            bundle=readiness,
            recorded=readiness_recorded,
            validation_errors=readiness_errors,
            pass_conditions={
                "re_entry_gate_passed": _bool(readiness.get("phase6_re_entry_gate_passed")),
                "q6_1_allowed": _bool(readiness.get("q6_1_artifact_schema_stage_allowed")),
                "learning_write_blocked": readiness.get("phase6_learning_write_allowed")
                is False,
                "knowledge_graph_write_blocked": readiness.get(
                    "phase6_knowledge_graph_write_allowed"
                )
                is False,
                "proof_credit_blocked": readiness.get("phase7_proof_credit_allowed")
                is False,
            },
        ),
        _gate_record(
            source_stage="Q6-1",
            label="Artifact schema and authority ledger",
            artifact_key="phase6_artifact_schema",
            source_ref="orchestrator/phase6_artifacts.py",
            bundle=schema_summary,
            recorded=schema_recorded,
            validation_errors=schema_errors,
            pass_conditions={
                "schema_valid": schema_summary.get("status") == "ok",
                "artifact_contracts_present": schema_summary.get("artifact_count")
                == schema_summary.get("artifact_type_count"),
                "authority_defaults_false": schema_summary.get("authority_enabled_count")
                == 0,
                "unsafe_counters_zero": schema_summary.get("unsafe_counter_total") == 0,
            },
        ),
        _gate_record(
            source_stage="Q6-2",
            label="Learning source intake",
            artifact_key="phase6_learning_source_intake",
            source_ref=source_ref,
            bundle=source_intake,
            recorded=source_recorded,
            validation_errors=source_errors,
            pass_conditions={
                "postmortem_due_discovered": _int(source_intake.get("postmortem_due_count"))
                > 0,
                "required_sources_present": _int(
                    source_intake.get("required_source_present_count")
                )
                == _int(source_intake.get("required_source_count")),
                "phase5_sources_not_mutated": source_intake.get(
                    "phase5_source_artifacts_mutated"
                )
                is False,
                "learning_write_absent": source_intake.get("learning_write_created")
                is False,
            },
        ),
        _gate_record(
            source_stage="Q6-3",
            label="Closed trade and outcome schema",
            artifact_key="phase6_closed_trade_outcome",
            source_ref=outcome_ref,
            bundle=outcome,
            recorded=outcome_recorded,
            validation_errors=outcome_errors,
            pass_conditions={
                "outcome_recorded": _int(outcome.get("outcome_record_count")) > 0,
                "broker_truth_separated": outcome.get("broker_truth_separated") is True,
                "learning_write_blocked": outcome.get("learning_write_allowed") is False,
                "source_hash_not_mutated": _int(outcome.get("source_hash_mutation_count"))
                == 0,
            },
        ),
        _gate_record(
            source_stage="Q6-4",
            label="Postmortem packet contract",
            artifact_key="phase6_postmortem_packet_contract",
            source_ref=packet_ref,
            bundle=packet,
            recorded=packet_recorded,
            validation_errors=packet_errors,
            pass_conditions={
                "packet_sections_present": _int(packet.get("packet_section_count")) >= 13,
                "assertion_refs_required": packet.get("assertion_source_refs_required")
                is True,
                "narrative_only_rejected": packet.get("narrative_only_allowed") is False,
                "learning_write_absent": packet.get("learning_write_created") is False,
            },
        ),
        _gate_record(
            source_stage="Q6-5",
            label="Postmortem agent draft",
            artifact_key="phase6_postmortem_draft",
            source_ref=draft_ref,
            bundle=draft,
            recorded=draft_recorded,
            validation_errors=draft_errors,
            pass_conditions={
                "draft_created": draft.get("postmortem_draft_created") is True,
                "not_approved": draft.get("postmortem_approved") is False,
                "source_assertions_present": _int(draft.get("source_assertion_count")) > 0,
                "learning_write_absent": draft.get("learning_write_created") is False,
            },
        ),
        _gate_record(
            source_stage="Q6-6",
            label="Analysis sub-agent packets",
            artifact_key="phase6_postmortem_analysis",
            source_ref=analysis_ref,
            bundle=analysis,
            recorded=analysis_recorded,
            validation_errors=analysis_errors,
            pass_conditions={
                "analysis_packets_created": _int(analysis.get("analysis_packet_count")) >= 5,
                "claims_cited": analysis.get("all_claims_cited") is True,
                "confidence_packets_present": _int(
                    analysis.get("confidence_packet_count")
                )
                >= 5,
                "learning_write_absent": analysis.get("learning_write_created") is False,
            },
        ),
        _gate_record(
            source_stage="Q6-7",
            label="Reducer and review gate",
            artifact_key="phase6_postmortem_reducer",
            source_ref=reducer_ref,
            bundle=reducer,
            recorded=reducer_recorded,
            validation_errors=reducer_errors,
            pass_conditions={
                "review_required": reducer.get("review_state") == "review_required",
                "reduced_postmortem_created": reducer.get("reduced_postmortem_created")
                is True,
                "review_queue_present": _int(reducer.get("review_queue_count")) > 0,
                "write_blocked": reducer.get("write_allowed") is False,
            },
        ),
        _gate_record(
            source_stage="Q6-8",
            label="Outcome linker",
            artifact_key="phase6_outcome_linker",
            source_ref=linker_ref,
            bundle=linker,
            recorded=linker_recorded,
            validation_errors=linker_errors,
            pass_conditions={
                "complete_links_created": linker.get("complete_outcome_link_created")
                is True,
                "required_links_present": _int(linker.get("missing_required_link_count"))
                == 0,
                "reference_only": _int(linker.get("reference_only_link_count")) > 0,
                "phase5_sources_not_mutated": linker.get("source_artifacts_mutated")
                is False,
            },
        ),
        _gate_record(
            source_stage="Q6-9",
            label="Learning approval ledger",
            artifact_key="phase6_learning_approval",
            source_ref=approval_ref,
            bundle=approval,
            recorded=approval_recorded,
            validation_errors=approval_errors,
            pass_conditions={
                "approval_state_recorded": approval.get("approval_state")
                in {"pending_review", "approved", "deferred", "rejected"},
                "proposed_actions_recorded": _int(approval.get("proposed_action_count"))
                > 0,
                "no_default_approval": approval.get("default_approval_exists") is False,
                "downstream_blocked_without_approval": approval.get(
                    "downstream_advance_allowed"
                )
                is False,
            },
        ),
        _gate_record(
            source_stage="Q6-10",
            label="Knowledge Graph staged writes",
            artifact_key="phase6_knowledge_graph_staging",
            source_ref=kg_staging_ref,
            bundle=kg_staging,
            recorded=kg_staging_recorded,
            validation_errors=kg_staging_errors,
            pass_conditions={
                "candidate_actions_recorded": _int(kg_staging.get("candidate_action_count"))
                > 0,
                "staging_blocked_without_approval": kg_staging.get(
                    "missing_approval_blocks_staging"
                )
                is True,
                "graph_commit_absent": kg_staging.get("actual_graph_commit_created")
                is False,
                "destructive_overwrite_blocked": kg_staging.get(
                    "destructive_overwrite_allowed"
                )
                is False,
            },
        ),
        _gate_record(
            source_stage="Q6-11",
            label="Knowledge Graph read path",
            artifact_key="phase6_knowledge_graph_read_path",
            source_ref=kg_read_ref,
            bundle=kg_read,
            recorded=kg_read_recorded,
            validation_errors=kg_read_errors,
            pass_conditions={
                "read_result_present": _int(kg_read.get("result_count")) > 0,
                "seed_result_present": _int(kg_read.get("seed_result_count")) > 0,
                "search_enabled": kg_read.get("search_enabled") is True,
                "write_blocked": kg_read.get("write_allowed") is False,
            },
        ),
        _gate_record(
            source_stage="Q6-12",
            label="Model weight update proposals",
            artifact_key="phase6_model_weight_updates",
            source_ref=model_ref,
            bundle=model_weight,
            recorded=model_recorded,
            validation_errors=model_errors,
            pass_conditions={
                "proposal_recorded": _int(model_weight.get("proposal_record_count")) > 0,
                "weights_normalized": model_weight.get("weights_normalized") is True,
                "apply_blocked": model_weight.get("apply_allowed") is False,
                "active_model_weight_not_mutated": model_weight.get(
                    "active_model_weight_mutated"
                )
                is False,
            },
        ),
        _gate_record(
            source_stage="Q6-13",
            label="Trust score update proposals",
            artifact_key="phase6_trust_score_updates",
            source_ref=trust_ref,
            bundle=trust_score,
            recorded=trust_recorded,
            validation_errors=trust_errors,
            pass_conditions={
                "proposal_records_present": _int(trust_score.get("proposal_record_count"))
                > 0,
                "apply_blocked": trust_score.get("apply_allowed") is False,
                "canonical_rank_not_mutated": trust_score.get("canonical_rank_mutated")
                is False,
                "supplemental_only_rejected": trust_score.get(
                    "supplemental_only_verdict_rejected"
                )
                is True,
            },
        ),
        _gate_record(
            source_stage="Q6-14",
            label="Shadow strategy runner",
            artifact_key="phase6_shadow_strategy_runner",
            source_ref=shadow_ref,
            bundle=shadow,
            recorded=shadow_recorded,
            validation_errors=shadow_errors,
            pass_conditions={
                "variants_recorded": _int(shadow.get("variant_record_count")) > 0,
                "trade_candidates_blocked": shadow.get(
                    "trade_candidate_creation_allowed"
                )
                is False,
                "orders_blocked": shadow.get("order_creation_allowed") is False,
                "broker_post_blocked": shadow.get("broker_post_allowed") is False,
            },
        ),
        _gate_record(
            source_stage="Q6-15",
            label="Architect learning summary",
            artifact_key="phase6_architect_learning",
            source_ref=architect_ref,
            bundle=architect,
            recorded=architect_recorded,
            validation_errors=architect_errors,
            pass_conditions={
                "summary_created": architect.get("architect_summary_created") is True,
                "recommendations_present": _int(architect.get("recommendation_count"))
                > 0,
                "policy_mutation_blocked": architect.get("policy_mutation_allowed")
                is False,
                "recommendation_apply_blocked": architect.get(
                    "recommendation_apply_allowed"
                )
                is False,
            },
        ),
        _gate_record(
            source_stage="Q6-16",
            label="Journal and cockpit visibility",
            artifact_key="phase6_cockpit_visibility",
            source_ref=visibility_ref,
            bundle=visibility,
            recorded=visibility_recorded,
            validation_errors=visibility_errors,
            pass_conditions={
                "status_visible": visibility.get("status") == "visible",
                "backend_derived": visibility.get("backend_derived") is True,
                "ui_inferred_zero": _int(visibility.get("ui_inferred_readiness_count"))
                == 0,
                "unsafe_total_zero": _int(visibility.get("unsafe_write_counter_total"))
                == 0,
            },
        ),
    ]
    return gates, artifacts


def _stage_gate(gates: list[dict[str, Any]], stage: str) -> dict[str, Any]:
    for gate in gates:
        if gate.get("source_stage") == stage:
            return gate
    return {}


def _aggregate_gate_unsafe_count(gates: list[dict[str, Any]]) -> int:
    total = 0
    for gate in gates:
        unsafe_counts = gate.get("unsafe_counts", {})
        if isinstance(unsafe_counts, dict):
            total += sum(_int(value) for value in unsafe_counts.values())
    return total


def _certification_inputs(artifacts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    approval = artifacts.get("approval", {})
    visibility = artifacts.get("cockpit_visibility", {})
    kg_staging = artifacts.get("knowledge_graph_staging", {})
    kg_read = artifacts.get("knowledge_graph_read", {})
    model_weight = artifacts.get("model_weight_updates", {})
    trust_score = artifacts.get("trust_score_updates", {})
    shadow = artifacts.get("shadow_strategy_runner", {})
    architect = artifacts.get("architect_learning", {})

    approval_state = str(approval.get("approval_state") or "not_requested")
    postmortem_due_count = _int(visibility.get("postmortem_due_count"))
    postmortem_resolved_count = _int(visibility.get("postmortem_resolved_count"))
    postmortem_explicitly_deferred_count = (
        postmortem_due_count if approval_state == "deferred" else 0
    )
    unresolved_postmortem_count = max(
        postmortem_due_count
        - postmortem_resolved_count
        - postmortem_explicitly_deferred_count,
        0,
    )
    proposed_action_count = _int(approval.get("proposed_action_count"))
    approved_action_count = _int(approval.get("approved_action_count"))
    explicitly_deferred_action_count = (
        _int(approval.get("deferred_action_count")) if approval_state == "deferred" else 0
    )
    pending_review_action_count = _int(approval.get("pending_review_action_count"))
    reviewed_action_count = approved_action_count + explicitly_deferred_action_count

    reviewed_postmortem_coverage_satisfied = (
        postmortem_due_count > 0 and unresolved_postmortem_count == 0
    )
    learning_actions_review_satisfied = (
        proposed_action_count > 0
        and pending_review_action_count == 0
        and reviewed_action_count >= proposed_action_count
        and approval_state in {"approved", "deferred"}
    )
    knowledge_graph_requirement_satisfied = (
        approval_state == "approved"
        and (
            _int(kg_staging.get("staged_entry_count")) > 0
            or _int(kg_read.get("approved_learning_entry_count")) > 0
        )
    ) or (
        approval_state == "deferred"
        and _int(kg_staging.get("candidate_action_count")) > 0
        and _int(kg_staging.get("staged_entry_count")) == 0
        and kg_staging.get("missing_approval_blocks_staging") is True
    )

    return {
        "approval_state": approval_state,
        "approval_logged": approval.get("approval_logged") is True,
        "postmortem_due_count": postmortem_due_count,
        "postmortem_resolved_count": postmortem_resolved_count,
        "postmortem_explicitly_deferred_count": postmortem_explicitly_deferred_count,
        "unresolved_postmortem_count": unresolved_postmortem_count,
        "reviewed_postmortem_coverage_satisfied": reviewed_postmortem_coverage_satisfied,
        "proposed_action_count": proposed_action_count,
        "approved_action_count": approved_action_count,
        "explicitly_deferred_action_count": explicitly_deferred_action_count,
        "pending_review_action_count": pending_review_action_count,
        "learning_actions_review_satisfied": learning_actions_review_satisfied,
        "knowledge_graph_requirement_satisfied": knowledge_graph_requirement_satisfied,
        "knowledge_graph_staged_entry_count": _int(kg_staging.get("staged_entry_count")),
        "knowledge_graph_candidate_action_count": _int(
            kg_staging.get("candidate_action_count")
        ),
        "knowledge_graph_read_result_count": _int(kg_read.get("result_count")),
        "model_weight_proposal_count": _int(model_weight.get("proposal_record_count")),
        "trust_score_proposal_count": _int(trust_score.get("proposal_record_count")),
        "shadow_replay_variant_count": _int(shadow.get("variant_record_count")),
        "architect_recommendation_count": _int(architect.get("recommendation_count")),
        "cockpit_visibility_status": visibility.get("status", "missing"),
        "cockpit_backend_derived": visibility.get("backend_derived") is True,
        "cockpit_ui_inferred_readiness_count": _int(
            visibility.get("ui_inferred_readiness_count")
        ),
    }


def _certification_blockers(
    gates: list[dict[str, Any]],
    inputs: dict[str, Any],
    blocking_unsafe_count: int,
) -> list[str]:
    blockers: list[str] = []
    for gate in gates:
        if gate.get("gate_passed") is not True:
            blockers.append(f"{str(gate.get('source_stage')).lower()}_gate_not_passed")
    if inputs["postmortem_due_count"] <= 0:
        blockers.append("postmortem_due_missing")
    if inputs["unresolved_postmortem_count"] > 0:
        blockers.append("postmortem_review_coverage_incomplete")
    if inputs["approval_state"] == "pending_review":
        blockers.append("learning_approval_pending_review")
    if not inputs["learning_actions_review_satisfied"]:
        blockers.append("learning_actions_not_approved_or_deferred")
    if not inputs["knowledge_graph_requirement_satisfied"]:
        blockers.append("knowledge_graph_entries_or_proposals_not_certifiable")
    for key in (
        "model_weight_proposal_count",
        "trust_score_proposal_count",
        "shadow_replay_variant_count",
        "architect_recommendation_count",
        "knowledge_graph_read_result_count",
    ):
        if inputs[key] <= 0:
            blockers.append(f"{key}_missing")
    if inputs["cockpit_visibility_status"] != "visible":
        blockers.append("cockpit_visibility_not_visible")
    if inputs["cockpit_backend_derived"] is not True:
        blockers.append("cockpit_visibility_not_backend_derived")
    if inputs["cockpit_ui_inferred_readiness_count"] != 0:
        blockers.append("cockpit_ui_inferred_readiness_present")
    if blocking_unsafe_count:
        blockers.append("blocking_unsafe_count_nonzero")
    return sorted(set(blockers))


def _public_status_from_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    output = {field: deepcopy(artifact.get(field)) for field in PUBLIC_STATUS_FIELDS if field in artifact}
    output["validation_error_count"] = len(artifact.get("validation_errors", []) or [])
    return output


def _refresh_validation(artifact: dict[str, Any]) -> dict[str, Any]:
    artifact.setdefault("validation_errors", [])
    artifact["public_status"] = _public_status_from_artifact(artifact)
    for _ in range(2):
        artifact["validation_errors"] = validate_phase6_certification(artifact)
        artifact["validation_error_count"] = len(artifact["validation_errors"])
        artifact["public_status"] = _public_status_from_artifact(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "blocked"
        artifact["stage_status"] = "certification_validation_error"
        artifact["public_status"] = _public_status_from_artifact(artifact)
    return artifact


def build_phase6_certification(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    gates, artifacts = _source_gates(settings)
    inputs = _certification_inputs(artifacts)
    blocking_unsafe_count = _aggregate_gate_unsafe_count(gates)
    certification_blockers = _certification_blockers(gates, inputs, blocking_unsafe_count)
    phase6_certified = not certification_blockers
    phase7_demo_allowed = phase6_certified
    blocked_authorities = [
        field
        for field in PHASE6_AUTHORITY_FIELDS
        if not (field == "phase7_demo_proof_planning_allowed" and phase7_demo_allowed)
    ]
    authority_defaults = phase6_authority_defaults()
    authority_defaults["phase7_demo_proof_planning_allowed"] = phase7_demo_allowed

    artifact = {
        "schema_version": PHASE6_ARTIFACT_SCHEMA_VERSION,
        "phase6_certification_schema_version": PHASE6_CERTIFICATION_SCHEMA_VERSION,
        "artifact_type": "phase6_certification",
        "artifact_id": "phase6:q6-17:certification",
        "phase": "Q6",
        "stage": "Q6-17",
        "status": "certified" if phase6_certified else "blocked",
        "stage_status": "phase6_certified" if phase6_certified else "blocked_pending_learning_review",
        "certification_state": "certified" if phase6_certified else "blocked_pending_learning_review",
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
        "event_contract": phase6_event_contract("certification"),
        "authority_ledger": _authority_ledger(phase7_demo_allowed),
        "source_posture": phase6_source_posture(),
        "provenance": _provenance(),
        "boundary": PHASE6_CERTIFICATION_BOUNDARY,
        **authority_defaults,
        **phase6_unsafe_counter_defaults(),
        "phase6_certified": phase6_certified,
        "phase6_complete": phase6_certified,
        "phase6_exit_gate": phase6_certified,
        "phase7_demo_proof_planning_allowed": phase7_demo_allowed,
        "phase7_proof_credit_allowed": False,
        "phase5_test_trades_count_for_phase7": False,
        "required_input_stages": list(PHASE6_CERTIFICATION_REQUIRED_INPUT_STAGES),
        "required_input_stage_count": len(PHASE6_CERTIFICATION_REQUIRED_INPUT_STAGES),
        "input_gate_count": len(gates),
        "input_gate_passed_count": sum(1 for gate in gates if gate.get("gate_passed") is True),
        "input_gate_blocked_count": sum(1 for gate in gates if gate.get("gate_passed") is not True),
        "gate_records": gates,
        "certification_blockers": certification_blockers,
        "certification_blocker_count": len(certification_blockers),
        "blocking_unsafe_count": blocking_unsafe_count,
        "blocked_authorities": blocked_authorities,
        "blocked_authority_count": len(blocked_authorities),
        **inputs,
        "broker_post_called_count": 0,
        "alpaca_post_called_count": 0,
        "broker_write_allowed_count": 0,
        "prediction_market_write_allowed_count": 0,
        "crypto_perps_write_allowed_count": 0,
        "live_endpoint_allowed_count": 0,
        "live_capital_enabled_count": 0,
        "phase7_proof_credit_allowed_count": 0,
        "phase6_postmortem_ingestion_allowed_count": 0,
        "phase6_learning_write_allowed_count": 0,
        "phase6_knowledge_graph_write_allowed_count": 0,
        "phase6_model_weight_update_allowed_count": 0,
        "phase6_trust_score_update_allowed_count": 0,
        "phase6_shadow_strategy_runner_allowed_count": 0,
        "phase6_policy_mutation_allowed_count": 0,
        "unsafe_write_counter_total": 0,
        "recommended_next_stage": (
            "Phase 7 Demo Proof planning"
            if phase6_certified
            else "Resolve or explicitly defer Q6 learning approval"
        ),
    }
    return _refresh_validation(artifact)


def _validate_gate_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("schema_version") != PHASE6_ARTIFACT_SCHEMA_VERSION:
        errors.append("gate_schema_version_mismatch")
    if record.get("phase6_certification_schema_version") != PHASE6_CERTIFICATION_SCHEMA_VERSION:
        errors.append("gate_certification_schema_version_mismatch")
    if record.get("artifact_type") != "phase6_certification_gate":
        errors.append("gate_artifact_type_mismatch")
    if record.get("phase") != "Q6" or record.get("stage") != "Q6-17":
        errors.append("gate_phase_stage_mismatch")
    if record.get("source_stage") not in PHASE6_CERTIFICATION_REQUIRED_INPUT_STAGES:
        errors.append("gate_source_stage_invalid")
    if record.get("public_safe") is not True:
        errors.append("gate_not_public_safe")
    if record.get("display_status") != record.get("backend_status"):
        errors.append("gate_display_backend_mismatch")
    if record.get("display_derived_from_backend") is not True:
        errors.append("gate_display_not_backend_derived")
    if record.get("ui_inferred_readiness") is not False:
        errors.append("gate_ui_inferred_readiness")
    if record.get("gate_passed") is True and record.get("backend_status") != "passed":
        errors.append("gate_passed_status_mismatch")
    if record.get("gate_passed") is not True and record.get("backend_status") != "blocked":
        errors.append("gate_blocked_status_mismatch")
    if record.get("phase7_demo_proof_planning_allowed") is not False:
        errors.append("gate_phase7_demo_planning_allowed")
    if record.get("phase7_proof_credit_allowed") is not False:
        errors.append("gate_phase7_credit_allowed")
    if record.get("phase5_test_trades_count_for_phase7") is not False:
        errors.append("gate_phase5_trade_counted_for_phase7")
    unsafe_counts = record.get("unsafe_counts", {})
    if not isinstance(unsafe_counts, dict):
        errors.append("gate_unsafe_counts_invalid")
    elif unsafe_counts:
        errors.append("gate_unsafe_counts_nonzero")
    authority_enabled = record.get("authority_enabled_fields", [])
    if authority_enabled:
        errors.append("gate_authority_enabled:" + ",".join(map(str, authority_enabled)))
    source_ref = str(record.get("source_ref") or "")
    if source_ref.startswith("/") or source_ref.startswith("~"):
        errors.append("gate_source_ref_local_path")
    if "api_key" in source_ref.lower() or "token" in source_ref.lower():
        errors.append("gate_source_ref_secret")
    boundary = str(record.get("boundary") or "")
    if "cannot approve learning" not in boundary or "cannot enable live capital" not in boundary:
        errors.append("gate_boundary_weak")
    return sorted(set(errors))


def validate_phase6_certification(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = set(PUBLIC_STATUS_FIELDS) | {
        "event_contract",
        "authority_ledger",
        "source_posture",
        "provenance",
        "public_status",
        "required_input_stages",
    }
    missing = sorted(required - set(artifact))
    if missing:
        errors.append("phase6_certification_missing_fields:" + ",".join(missing))

    allowed_authority = (
        ("phase7_demo_proof_planning_allowed",)
        if artifact.get("phase6_certified") is True
        and artifact.get("phase7_demo_proof_planning_allowed") is True
        else ()
    )
    errors.extend(
        validate_phase6_artifact(
            artifact,
            expected_stage="Q6-17",
            allowed_authority_fields=allowed_authority,
        )
    )
    if artifact.get("phase6_certification_schema_version") != PHASE6_CERTIFICATION_SCHEMA_VERSION:
        errors.append("phase6_certification_schema_version_mismatch")
    if artifact.get("artifact_type") != "phase6_certification":
        errors.append("phase6_certification_artifact_type_mismatch")

    gates = artifact.get("gate_records", [])
    if not isinstance(gates, list):
        errors.append("phase6_certification_gate_records_not_list")
        gates = []
    if artifact.get("input_gate_count") != len(gates):
        errors.append("phase6_certification_input_gate_count_mismatch")
    if artifact.get("input_gate_count") != len(PHASE6_CERTIFICATION_REQUIRED_INPUT_STAGES):
        errors.append("phase6_certification_input_gate_count_not_required")
    gate_stage_order = [gate.get("source_stage") for gate in gates if isinstance(gate, dict)]
    if gate_stage_order != list(PHASE6_CERTIFICATION_REQUIRED_INPUT_STAGES):
        errors.append("phase6_certification_gate_stage_order_mismatch")
    gate_passed_count = sum(1 for gate in gates if gate.get("gate_passed") is True)
    if artifact.get("input_gate_passed_count") != gate_passed_count:
        errors.append("phase6_certification_input_gate_passed_count_mismatch")
    if artifact.get("input_gate_blocked_count") != len(gates) - gate_passed_count:
        errors.append("phase6_certification_input_gate_blocked_count_mismatch")
    for gate in gates:
        if not isinstance(gate, dict):
            errors.append("phase6_certification_gate_record_invalid")
            continue
        errors.extend(_validate_gate_record(gate))

    blockers = artifact.get("certification_blockers", [])
    if not isinstance(blockers, list):
        errors.append("phase6_certification_blockers_not_list")
        blockers = []
    if artifact.get("certification_blocker_count") != len(blockers):
        errors.append("phase6_certification_blocker_count_mismatch")

    phase6_certified = artifact.get("phase6_certified") is True
    if phase6_certified:
        if blockers:
            errors.append("phase6_certified_with_blockers")
        if artifact.get("status") != "certified":
            errors.append("phase6_certified_status_not_certified")
        if artifact.get("phase6_complete") is not True:
            errors.append("phase6_certified_complete_false")
        if artifact.get("phase6_exit_gate") is not True:
            errors.append("phase6_certified_exit_gate_false")
        if artifact.get("phase7_demo_proof_planning_allowed") is not True:
            errors.append("phase6_certified_phase7_demo_not_allowed")
        if artifact.get("reviewed_postmortem_coverage_satisfied") is not True:
            errors.append("phase6_certified_postmortem_coverage_missing")
        if artifact.get("learning_actions_review_satisfied") is not True:
            errors.append("phase6_certified_learning_actions_unreviewed")
        if artifact.get("knowledge_graph_requirement_satisfied") is not True:
            errors.append("phase6_certified_kg_requirement_missing")
    else:
        if artifact.get("status") != "blocked":
            errors.append("blocked_phase6_certification_status_not_blocked")
        if artifact.get("phase6_complete") is not False:
            errors.append("blocked_phase6_certification_complete_true")
        if artifact.get("phase6_exit_gate") is not False:
            errors.append("blocked_phase6_certification_exit_gate_true")
        if artifact.get("phase7_demo_proof_planning_allowed") is not False:
            errors.append("blocked_phase6_certification_phase7_demo_allowed")
        if not blockers:
            errors.append("blocked_phase6_certification_without_blockers")
    if artifact.get("phase7_proof_credit_allowed") is not False:
        errors.append("phase7_proof_credit_allowed")
    if artifact.get("phase5_test_trades_count_for_phase7") is not False:
        errors.append("phase5_test_trades_count_for_phase7")
    if _int(artifact.get("phase7_proof_credit_allowed_count")) != 0:
        errors.append("phase7_proof_credit_allowed_count_nonzero")
    if artifact.get("live_capital_enabled") is not False:
        errors.append("phase6_certification_live_capital_enabled")
    if _int(artifact.get("live_capital_enabled_count")) != 0:
        errors.append("phase6_certification_live_capital_count_nonzero")
    if artifact.get("broker_write_allowed") is not False:
        errors.append("phase6_certification_broker_write_allowed")

    if artifact.get("postmortem_due_count", 0) < artifact.get("postmortem_resolved_count", 0):
        errors.append("phase6_certification_postmortem_count_mismatch")
    expected_unresolved = max(
        _int(artifact.get("postmortem_due_count"))
        - _int(artifact.get("postmortem_resolved_count"))
        - _int(artifact.get("postmortem_explicitly_deferred_count")),
        0,
    )
    if artifact.get("unresolved_postmortem_count") != expected_unresolved:
        errors.append("phase6_certification_unresolved_postmortem_count_mismatch")
    if artifact.get("unresolved_postmortem_count", 0) < 0:
        errors.append("phase6_certification_unresolved_postmortem_negative")
    if (
        artifact.get("reviewed_postmortem_coverage_satisfied") is True
        and expected_unresolved != 0
    ):
        errors.append("phase6_certification_false_postmortem_coverage")
    if (
        artifact.get("learning_actions_review_satisfied") is True
        and artifact.get("pending_review_action_count") != 0
    ):
        errors.append("phase6_certification_false_learning_review")
    if artifact.get("approval_state") == "pending_review" and artifact.get(
        "learning_actions_review_satisfied"
    ) is True:
        errors.append("phase6_certification_pending_learning_marked_reviewed")

    for key in (
        "knowledge_graph_read_result_count",
        "model_weight_proposal_count",
        "trust_score_proposal_count",
        "shadow_replay_variant_count",
        "architect_recommendation_count",
    ):
        if _int(artifact.get(key)) <= 0:
            errors.append(f"phase6_certification_required_count_missing:{key}")
    if artifact.get("cockpit_visibility_status") != "visible":
        errors.append("phase6_certification_cockpit_not_visible")
    if artifact.get("cockpit_backend_derived") is not True:
        errors.append("phase6_certification_cockpit_not_backend_derived")
    if artifact.get("cockpit_ui_inferred_readiness_count") != 0:
        errors.append("phase6_certification_cockpit_ui_inferred")

    blocked_authorities = artifact.get("blocked_authorities", [])
    if not isinstance(blocked_authorities, list):
        errors.append("phase6_certification_blocked_authorities_not_list")
        blocked_authorities = []
    if artifact.get("blocked_authority_count") != len(blocked_authorities):
        errors.append("phase6_certification_blocked_authority_count_mismatch")
    expected_blocked = [
        field
        for field in PHASE6_AUTHORITY_FIELDS
        if not (
            phase6_certified
            and artifact.get("phase7_demo_proof_planning_allowed") is True
            and field == "phase7_demo_proof_planning_allowed"
        )
    ]
    if sorted(blocked_authorities) != sorted(expected_blocked):
        errors.append("phase6_certification_blocked_authorities_mismatch")

    unsafe_total = 0
    for field in PHASE6_UNSAFE_COUNT_FIELDS:
        value = _int(artifact.get(field))
        unsafe_total += value
        if value != 0:
            errors.append(f"phase6_certification_unsafe_count_nonzero:{field}")
    if artifact.get("unsafe_write_counter_total") != unsafe_total:
        errors.append("phase6_certification_unsafe_total_mismatch")
    if artifact.get("blocking_unsafe_count") != 0:
        errors.append("phase6_certification_blocking_unsafe_count_nonzero")

    public_status = artifact.get("public_status")
    if not isinstance(public_status, dict):
        errors.append("phase6_certification_public_status_missing")
    else:
        extra = sorted(set(public_status) - set(PUBLIC_STATUS_FIELDS))
        if extra:
            errors.append("phase6_certification_public_status_extra_fields:" + ",".join(extra))
        for field in PUBLIC_STATUS_FIELDS:
            if field == "validation_error_count":
                continue
            if field in artifact and public_status.get(field) != artifact.get(field):
                errors.append(f"phase6_certification_public_status_mismatch:{field}")
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("phase6_certification_event_log_path_missing")
        if not str(artifact.get("event_log_correlation_id") or "").strip():
            errors.append("phase6_certification_event_log_correlation_missing")
        if artifact.get("event_log_event_count") != 1:
            errors.append("phase6_certification_event_log_count_mismatch")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "all scoped postmortems are reviewed",
        "learning actions are approved or explicitly deferred",
        "cannot approve learning",
        "cannot write learning data",
        "cannot write or commit a Knowledge Graph",
        "cannot apply model weights",
        "cannot apply trust scores",
        "cannot mutate policy",
        "cannot call broker POST routes",
        "cannot enable live capital",
        "cannot grant Phase 7 proof credit",
        "cannot let Phase 5 test trades count toward Phase 7 proof",
    ):
        if phrase not in boundary:
            errors.append("phase6_certification_boundary_weak")
            break
    return sorted(set(errors))


def attach_phase6_certification_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(event_log_path or (_runtime_dir(settings) / PHASE6_CERTIFICATION_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PHASE6_CERTIFICATION_EVENT_TYPE,
        PHASE6_CERTIFICATION_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "stage_status": output.get("stage_status"),
            "phase6_certified": output.get("phase6_certified"),
            "phase6_exit_gate": output.get("phase6_exit_gate"),
            "phase7_demo_proof_planning_allowed": output.get(
                "phase7_demo_proof_planning_allowed"
            ),
            "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
            "certification_blocker_count": output.get("certification_blocker_count"),
            "input_gate_passed_count": output.get("input_gate_passed_count"),
            "input_gate_blocked_count": output.get("input_gate_blocked_count"),
            "postmortem_due_count": output.get("postmortem_due_count"),
            "postmortem_resolved_count": output.get("postmortem_resolved_count"),
            "unresolved_postmortem_count": output.get("unresolved_postmortem_count"),
            "approval_state": output.get("approval_state"),
            "pending_review_action_count": output.get("pending_review_action_count"),
            "blocking_unsafe_count": output.get("blocking_unsafe_count"),
            "live_capital_enabled_count": output.get("live_capital_enabled_count"),
            "boundary": output.get("boundary"),
        },
    )
    output["recorded"] = True
    output["event_log_written"] = True
    output["event_log_path"] = str(log.path)
    output["event_log_event_count"] = 1
    output["event_log_correlation_id"] = entry.correlation_id
    output["event_log_created_at"] = entry.created_at
    return _refresh_validation(output), entry


def write_phase6_certification(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase6_certification_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase6_certification_event_log(
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
        "schema_version": PHASE6_CERTIFICATION_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "stage_status": output.get("stage_status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "phase6_certified": output.get("phase6_certified"),
        "phase6_exit_gate": output.get("phase6_exit_gate"),
        "phase7_demo_proof_planning_allowed": output.get(
            "phase7_demo_proof_planning_allowed"
        ),
        "certification_blocker_count": output.get("certification_blocker_count"),
        "input_gate_passed_count": output.get("input_gate_passed_count"),
        "input_gate_blocked_count": output.get("input_gate_blocked_count"),
        "postmortem_due_count": output.get("postmortem_due_count"),
        "postmortem_resolved_count": output.get("postmortem_resolved_count"),
        "unresolved_postmortem_count": output.get("unresolved_postmortem_count"),
        "approval_state": output.get("approval_state"),
        "event_log_written": output.get("event_log_written"),
        "event_log_event_count": output.get("event_log_event_count"),
        "validation_error_count": len(output.get("validation_errors", []) or []),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output


def phase6_certification_public_status(settings: Settings | None = None) -> dict[str, Any]:
    artifact = _read_json_ref(
        f"data/runtime/{PHASE6_CERTIFICATION_RUNTIME_ARTIFACT}",
        settings,
    )
    if not artifact:
        artifact = build_phase6_certification(settings=settings)
    artifact = _refresh_validation(artifact)
    return _public_status_from_artifact(artifact)
