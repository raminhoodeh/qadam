"""Q5E-10 Phase 5 to Phase 6 handoff closeout.

This stage records that Phase 5 is certified enough to plan Phase 6 - Learning
Loop. It does not implement the learning loop, write a knowledge graph, update
weights, mutate trust scores, or grant any broker/live authority.
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog, EventLogEntry
from orchestrator.phase5_artifacts import (
    PHASE5_ARTIFACT_SCHEMA_VERSION,
    PHASE5_AUTHORITY_FIELDS,
    phase5_authority_defaults,
    phase5_authority_ledger,
    phase5_provenance,
    phase5_source_posture,
)
from orchestrator.phase5_certification import (
    PHASE5_CERTIFICATION_RUNTIME_ARTIFACT,
    build_phase5_certification,
    validate_phase5_certification,
)
from orchestrator.phase5_execution_adapter_status import (
    EXECUTION_ADAPTER_RUNTIME_ARTIFACT,
    build_phase5_execution_adapter_status,
    validate_phase5_execution_adapter_status_bundle,
)
from orchestrator.phase5_paper_trade_drill import (
    PAPER_TRADE_DRILL_RUNTIME_ARTIFACT,
    build_phase5_paper_trade_drill,
    validate_phase5_paper_trade_drill_bundle,
)
from orchestrator.phase5_position_monitor import (
    GUARDED_POSTMORTEM_DUE_RUNTIME_ARTIFACT,
    POSITION_MONITOR_RUNTIME_ARTIFACT,
    build_phase5_position_monitor,
    validate_phase5_position_monitor_bundle,
)
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT


PHASE5_PHASE6_HANDOFF_SCHEMA_VERSION = 1
PHASE5_PHASE6_HANDOFF_RUNTIME_ARTIFACT = "phase5_phase6_handoff.json"
PHASE5_PHASE6_HANDOFF_HISTORY = "phase5_phase6_handoff_history.jsonl"
PHASE5_PHASE6_HANDOFF_EVENT_LOG = "phase5_phase6_handoff_events.jsonl"
PHASE5_PHASE6_HANDOFF_EVENT_TYPE = "phase5_phase6_handoff_recorded"
PHASE5_PHASE6_HANDOFF_COMPONENT = "phase5_phase6_handoff"

PHASE5_PHASE6_HANDOFF_SOURCE_REFS: tuple[str, ...] = (
    f"data/runtime/{PHASE5_CERTIFICATION_RUNTIME_ARTIFACT}",
    f"data/runtime/{PAPER_TRADE_DRILL_RUNTIME_ARTIFACT}",
    f"data/runtime/{EXECUTION_ADAPTER_RUNTIME_ARTIFACT}",
    f"data/runtime/{POSITION_MONITOR_RUNTIME_ARTIFACT}",
    f"data/runtime/{GUARDED_POSTMORTEM_DUE_RUNTIME_ARTIFACT}",
)

PHASE5_PHASE6_HANDOFF_UNSAFE_COUNT_FIELDS: tuple[str, ...] = (
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
)

PHASE5_PHASE6_HANDOFF_BOUNDARY = (
    "Q5E-10 is a closeout and handoff-planning gate only. It can record that "
    "Phase 5 is certified and that a Phase 6 implementation plan may be "
    "drafted, but it cannot implement Phase 6, cannot write learning data, "
    "cannot write a knowledge graph, cannot update model weights or trust "
    "scores, cannot mutate policy, cannot call broker POST routes, cannot call "
    "live endpoints, cannot enable live capital, and cannot count Phase 5 test "
    "trades toward Phase 7 proof."
)

PHASE6_REQUIRED_MODULES: tuple[str, ...] = (
    "postmortem_agent",
    "postmortem_packet_schema",
    "outcome_linker",
    "knowledge_graph_write_read_path",
    "bayesian_model_weight_updates",
    "trust_score_updates",
    "shadow_strategy_runner",
    "architect_agent_summaries",
    "trade_journal_and_postmortems_cockpit",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def phase5_phase6_handoff_paths(settings: Settings | None = None) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PHASE5_PHASE6_HANDOFF_RUNTIME_ARTIFACT,
        runtime / PHASE5_PHASE6_HANDOFF_HISTORY,
        runtime / PHASE5_PHASE6_HANDOFF_EVENT_LOG,
    )


def _authority_ledger() -> dict[str, Any]:
    ledger = phase5_authority_ledger()
    ledger["stage"] = "Q5E-10"
    ledger["boundary"] = PHASE5_PHASE6_HANDOFF_BOUNDARY
    return ledger


def _runtime_or_build(
    settings: Settings,
    artifact_name: str,
    builder: Any,
    validator: Any,
) -> tuple[dict[str, Any], bool, list[str]]:
    runtime = _read_json(_runtime_dir(settings) / artifact_name)
    recorded = runtime is not None
    artifact = runtime or builder(settings=settings)
    return artifact, recorded, list(validator(artifact))


def _venue_record(bundle: dict[str, Any], venue_key: str) -> dict[str, Any]:
    for record in bundle.get("statuses", []):
        if isinstance(record, dict) and record.get("venue_key") == venue_key:
            return record
    return {}


def _count(bundle: dict[str, Any], field: str) -> int:
    return int(bundle.get(field, 0) or 0)


def _unsafe_count_total(*bundles: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for field in PHASE5_PHASE6_HANDOFF_UNSAFE_COUNT_FIELDS:
        counts[field] = sum(_count(bundle, field) for bundle in bundles)
    return counts


def _blockers(
    *,
    certification: dict[str, Any],
    certification_recorded: bool,
    certification_errors: list[str],
    drill: dict[str, Any],
    drill_recorded: bool,
    drill_errors: list[str],
    adapter: dict[str, Any],
    adapter_recorded: bool,
    adapter_errors: list[str],
    position: dict[str, Any],
    position_recorded: bool,
    position_errors: list[str],
    postmortem_due: dict[str, Any],
    unsafe_counts: dict[str, int],
) -> list[str]:
    blockers: list[str] = []
    for key, recorded, errors in (
        ("phase5_certification", certification_recorded, certification_errors),
        ("phase5_paper_trade_drill", drill_recorded, drill_errors),
        ("phase5_execution_adapter", adapter_recorded, adapter_errors),
        ("phase5_position_monitor", position_recorded, position_errors),
    ):
        if not recorded:
            blockers.append(f"{key}_artifact_missing")
        if errors:
            blockers.append(f"{key}_validation_errors")
    if certification.get("phase5_certified") is not True:
        blockers.append("phase5_not_certified")
    if certification.get("phase6_handoff_allowed") is not True:
        blockers.append("phase6_handoff_not_allowed")
    if certification.get("phase7_proof_credit_allowed") is not False:
        blockers.append("phase7_proof_credit_allowed")
    if drill.get("paper_trade_drill_complete") is not True:
        blockers.append("paper_trade_drill_not_complete")
    if drill.get("phase5_paper_trade_drill_exit_gate_passed") is not True:
        blockers.append("q5_14_exit_gate_not_passed")
    if _count(drill, "blocker_count") != 0:
        blockers.append("q5_14_blockers_present")
    alpaca = _venue_record(adapter, "alpaca_paper")
    if adapter.get("downstream_staging_allowed_count") != 1:
        blockers.append("guarded_adapter_staging_readiness_missing")
    if alpaca.get("staging_readiness_scope") != "guarded_q5e_lifecycle_readiness":
        blockers.append("guarded_adapter_scope_invalid")
    if alpaca.get("guarded_postmortem_due_ready") is not True:
        blockers.append("guarded_postmortem_due_not_ready")
    if _count(position, "submitted_order_count") < 1:
        blockers.append("submitted_order_not_mirrored")
    if _count(position, "mirrored_order_count") < 1:
        blockers.append("mirrored_order_missing")
    if _count(position, "closed_trade_count") < 1:
        blockers.append("closed_trade_missing")
    if _count(position, "postmortem_due_count") < 1:
        blockers.append("postmortem_due_missing")
    if _count(position, "failed_reconciliation_count") != 0:
        blockers.append("position_reconciliation_failed")
    if postmortem_due.get("status") != "postmortem_due":
        blockers.append("guarded_postmortem_due_artifact_missing")
    if postmortem_due.get("postmortem_due_marker_created") is not True:
        blockers.append("guarded_postmortem_due_marker_missing")
    for field, value in unsafe_counts.items():
        if value != 0:
            blockers.append(f"unsafe_count_nonzero:{field}")
    return sorted(set(blockers))


def build_phase5_phase6_handoff(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    certification, certification_recorded, certification_errors = _runtime_or_build(
        settings,
        PHASE5_CERTIFICATION_RUNTIME_ARTIFACT,
        build_phase5_certification,
        validate_phase5_certification,
    )
    drill, drill_recorded, drill_errors = _runtime_or_build(
        settings,
        PAPER_TRADE_DRILL_RUNTIME_ARTIFACT,
        build_phase5_paper_trade_drill,
        validate_phase5_paper_trade_drill_bundle,
    )
    adapter, adapter_recorded, adapter_errors = _runtime_or_build(
        settings,
        EXECUTION_ADAPTER_RUNTIME_ARTIFACT,
        build_phase5_execution_adapter_status,
        validate_phase5_execution_adapter_status_bundle,
    )
    position, position_recorded, position_errors = _runtime_or_build(
        settings,
        POSITION_MONITOR_RUNTIME_ARTIFACT,
        build_phase5_position_monitor,
        validate_phase5_position_monitor_bundle,
    )
    postmortem_due = _read_json(
        _runtime_dir(settings) / GUARDED_POSTMORTEM_DUE_RUNTIME_ARTIFACT
    ) or {}
    unsafe_counts = _unsafe_count_total(certification, drill, adapter, position)
    blockers = _blockers(
        certification=certification,
        certification_recorded=certification_recorded,
        certification_errors=certification_errors,
        drill=drill,
        drill_recorded=drill_recorded,
        drill_errors=drill_errors,
        adapter=adapter,
        adapter_recorded=adapter_recorded,
        adapter_errors=adapter_errors,
        position=position,
        position_recorded=position_recorded,
        position_errors=position_errors,
        postmortem_due=postmortem_due,
        unsafe_counts=unsafe_counts,
    )
    phase6_plan_allowed = not blockers
    artifact = {
        "schema_version": PHASE5_ARTIFACT_SCHEMA_VERSION,
        "phase5_phase6_handoff_schema_version": PHASE5_PHASE6_HANDOFF_SCHEMA_VERSION,
        "artifact_type": "phase5_phase6_handoff",
        "artifact_id": "phase5:q5e-10:phase6-handoff",
        "phase": "Q5",
        "stage": "Q5E-10",
        "status": "eligible" if phase6_plan_allowed else "blocked",
        "handoff_state": (
            "phase6_learning_loop_plan_ready"
            if phase6_plan_allowed
            else "blocked_pending_phase5_closeout"
        ),
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
        "authority_ledger": _authority_ledger(),
        "source_posture": phase5_source_posture(),
        "provenance": phase5_provenance(PHASE5_PHASE6_HANDOFF_SOURCE_REFS),
        "boundary": PHASE5_PHASE6_HANDOFF_BOUNDARY,
        **phase5_authority_defaults(),
        "canonical_source_count": EXPECTED_SOURCE_COUNT,
        "phase5_certified": certification.get("phase5_certified") is True,
        "phase5_exit_gate": certification.get("phase5_exit_gate") is True,
        "phase6_handoff_allowed": certification.get("phase6_handoff_allowed") is True,
        "phase7_planning_allowed": certification.get("phase7_planning_allowed") is True,
        "phase7_proof_credit_allowed": certification.get("phase7_proof_credit_allowed") is True,
        "phase5_test_trades_count_for_phase7": False,
        "paper_trade_drill_complete": drill.get("paper_trade_drill_complete") is True,
        "paper_trade_drill_exit_gate_passed": (
            drill.get("phase5_paper_trade_drill_exit_gate_passed") is True
        ),
        "paper_trade_drill_blocker_count": _count(drill, "blocker_count"),
        "downstream_staging_allowed_count": _count(adapter, "downstream_staging_allowed_count"),
        "submitted_order_count": _count(position, "submitted_order_count"),
        "mirrored_order_count": _count(position, "mirrored_order_count"),
        "open_position_count": _count(position, "open_position_count"),
        "closed_trade_count": _count(position, "closed_trade_count"),
        "postmortem_due_count": _count(position, "postmortem_due_count"),
        "failed_reconciliation_count": _count(position, "failed_reconciliation_count"),
        "guarded_postmortem_due_ready": postmortem_due.get("status") == "postmortem_due"
        and postmortem_due.get("postmortem_due_marker_created") is True,
        "guarded_postmortem_due_ref": postmortem_due.get("postmortem_due_ref"),
        "source_validation_error_count": sum(
            len(errors)
            for errors in (
                certification_errors,
                drill_errors,
                adapter_errors,
                position_errors,
            )
        ),
        "source_recorded_count": sum(
            1
            for recorded in (
                certification_recorded,
                drill_recorded,
                adapter_recorded,
                position_recorded,
                bool(postmortem_due),
            )
            if recorded
        ),
        "required_source_count": 5,
        "blockers": blockers,
        "blocker_count": len(blockers),
        "phase6_learning_loop_plan_allowed": phase6_plan_allowed,
        "phase6_learning_loop_implementation_allowed": False,
        "phase6_postmortem_ingestion_allowed": False,
        "phase6_learning_write_allowed": False,
        "phase6_knowledge_graph_write_allowed": False,
        "phase6_model_weight_update_allowed": False,
        "phase6_trust_score_update_allowed": False,
        "phase6_shadow_strategy_runner_allowed": False,
        "phase6_architect_policy_mutation_allowed": False,
        "phase6_required_modules": list(PHASE6_REQUIRED_MODULES),
        "phase6_required_module_count": len(PHASE6_REQUIRED_MODULES),
        "recommended_next_stage": "Q6-0 Phase 6 re-entry and learning-loop implementation plan",
        **unsafe_counts,
    }
    artifact["validation_errors"] = validate_phase5_phase6_handoff(artifact)
    if artifact["validation_errors"]:
        artifact["status"] = "error"
    return artifact


def validate_phase5_phase6_handoff(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schema_version",
        "phase5_phase6_handoff_schema_version",
        "artifact_type",
        "artifact_id",
        "phase",
        "stage",
        "status",
        "handoff_state",
        "generated_at",
        "public_safe",
        "event_log_required",
        "event_log_written",
        "authority_ledger",
        "source_posture",
        "provenance",
        "boundary",
        "phase5_certified",
        "phase5_exit_gate",
        "phase6_handoff_allowed",
        "phase7_planning_allowed",
        "phase7_proof_credit_allowed",
        "paper_trade_drill_complete",
        "paper_trade_drill_exit_gate_passed",
        "paper_trade_drill_blocker_count",
        "downstream_staging_allowed_count",
        "submitted_order_count",
        "mirrored_order_count",
        "closed_trade_count",
        "postmortem_due_count",
        "guarded_postmortem_due_ready",
        "source_validation_error_count",
        "source_recorded_count",
        "required_source_count",
        "blockers",
        "blocker_count",
        "phase6_learning_loop_plan_allowed",
        "phase6_learning_loop_implementation_allowed",
        "phase6_required_modules",
        "phase6_required_module_count",
        "recommended_next_stage",
    }
    missing = sorted(required_fields - set(artifact))
    if missing:
        errors.append("handoff_missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PHASE5_ARTIFACT_SCHEMA_VERSION:
        errors.append("handoff_schema_version_mismatch")
    if artifact.get("phase5_phase6_handoff_schema_version") != PHASE5_PHASE6_HANDOFF_SCHEMA_VERSION:
        errors.append("handoff_schema_version_mismatch")
    if artifact.get("artifact_type") != "phase5_phase6_handoff":
        errors.append("handoff_artifact_type_mismatch")
    if artifact.get("phase") != "Q5" or artifact.get("stage") != "Q5E-10":
        errors.append("handoff_phase_stage_mismatch")
    if artifact.get("status") not in {"eligible", "blocked", "error"}:
        errors.append("handoff_status_invalid")
    if artifact.get("public_safe") is not True:
        errors.append("handoff_not_public_safe")
    if artifact.get("event_log_required") is not True:
        errors.append("handoff_event_log_not_required")
    blockers = artifact.get("blockers", [])
    if not isinstance(blockers, list):
        errors.append("handoff_blockers_not_list")
        blockers = []
    if artifact.get("blocker_count") != len(blockers):
        errors.append("handoff_blocker_count_mismatch")
    for field in PHASE5_AUTHORITY_FIELDS:
        if artifact.get(field) is not False:
            errors.append(f"handoff_phase5_authority_enabled:{field}")
    if artifact.get("phase7_proof_credit_allowed") is not False:
        errors.append("phase7_proof_credit_allowed")
    if artifact.get("phase5_test_trades_count_for_phase7") is not False:
        errors.append("phase5_test_trades_count_for_phase7")
    for field in PHASE5_PHASE6_HANDOFF_UNSAFE_COUNT_FIELDS:
        if int(artifact.get(field, 0) or 0) != 0:
            errors.append(f"handoff_unsafe_count_nonzero:{field}")
    for field in (
        "phase6_learning_loop_implementation_allowed",
        "phase6_postmortem_ingestion_allowed",
        "phase6_learning_write_allowed",
        "phase6_knowledge_graph_write_allowed",
        "phase6_model_weight_update_allowed",
        "phase6_trust_score_update_allowed",
        "phase6_shadow_strategy_runner_allowed",
        "phase6_architect_policy_mutation_allowed",
    ):
        if artifact.get(field) is not False:
            errors.append(f"phase6_authority_enabled_before_q6_0:{field}")
    plan_allowed = artifact.get("phase6_learning_loop_plan_allowed") is True
    if plan_allowed:
        if artifact.get("status") != "eligible":
            errors.append("handoff_plan_allowed_not_eligible")
        if blockers:
            errors.append("handoff_plan_allowed_with_blockers")
        for field in (
            "phase5_certified",
            "phase5_exit_gate",
            "phase6_handoff_allowed",
            "phase7_planning_allowed",
            "paper_trade_drill_complete",
            "paper_trade_drill_exit_gate_passed",
            "guarded_postmortem_due_ready",
        ):
            if artifact.get(field) is not True:
                errors.append(f"handoff_plan_allowed_missing_true:{field}")
        if int(artifact.get("paper_trade_drill_blocker_count", 0) or 0) != 0:
            errors.append("handoff_plan_allowed_drill_blockers")
        for field in (
            "downstream_staging_allowed_count",
            "submitted_order_count",
            "mirrored_order_count",
            "closed_trade_count",
            "postmortem_due_count",
        ):
            if int(artifact.get(field, 0) or 0) < 1:
                errors.append(f"handoff_plan_allowed_missing_count:{field}")
        if int(artifact.get("failed_reconciliation_count", 0) or 0) != 0:
            errors.append("handoff_plan_allowed_failed_reconciliation")
        if artifact.get("source_validation_error_count") != 0:
            errors.append("handoff_plan_allowed_source_validation_errors")
        if artifact.get("source_recorded_count") != artifact.get("required_source_count"):
            errors.append("handoff_plan_allowed_missing_sources")
    else:
        if artifact.get("status") != "blocked":
            errors.append("handoff_blocked_status_mismatch")
        if not blockers:
            errors.append("handoff_blocked_without_blockers")
    if artifact.get("phase6_required_module_count") != len(
        artifact.get("phase6_required_modules", [])
    ):
        errors.append("phase6_required_module_count_mismatch")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "cannot implement Phase 6",
        "cannot write learning data",
        "cannot call broker POST routes",
        "cannot enable live capital",
        "cannot count Phase 5 test trades toward Phase 7 proof",
    ):
        if phrase not in boundary:
            errors.append("handoff_boundary_weak")
            break
    if artifact.get("event_log_written") is True:
        if not str(artifact.get("event_log_path") or "").strip():
            errors.append("handoff_event_log_path_missing")
        if not str(artifact.get("event_log_correlation_id") or "").strip():
            errors.append("handoff_event_correlation_missing")
        if artifact.get("event_log_event_count") != 1:
            errors.append("handoff_event_log_count_mismatch")
    return sorted(set(errors))


def attach_phase5_phase6_handoff_event_log(
    artifact: dict[str, Any],
    *,
    event_log: EventLog | None = None,
    event_log_path: str | Path | None = None,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], EventLogEntry]:
    output = deepcopy(artifact)
    log_path = Path(event_log_path or (_runtime_dir(settings) / PHASE5_PHASE6_HANDOFF_EVENT_LOG))
    log = event_log or EventLog(log_path, echo=False)
    entry = log.write(
        PHASE5_PHASE6_HANDOFF_EVENT_TYPE,
        PHASE5_PHASE6_HANDOFF_COMPONENT,
        {
            "artifact_id": output.get("artifact_id"),
            "status": output.get("status"),
            "handoff_state": output.get("handoff_state"),
            "phase5_certified": output.get("phase5_certified"),
            "phase6_handoff_allowed": output.get("phase6_handoff_allowed"),
            "phase6_learning_loop_plan_allowed": output.get(
                "phase6_learning_loop_plan_allowed"
            ),
            "phase6_learning_loop_implementation_allowed": output.get(
                "phase6_learning_loop_implementation_allowed"
            ),
            "paper_trade_drill_complete": output.get("paper_trade_drill_complete"),
            "closed_trade_count": output.get("closed_trade_count"),
            "postmortem_due_count": output.get("postmortem_due_count"),
            "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
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
    output["validation_errors"] = validate_phase5_phase6_handoff(output)
    if output["validation_errors"]:
        output["status"] = "error"
    return output, entry


def write_phase5_phase6_handoff(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
    record_event: bool = True,
    event_log_path: str | Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    output = deepcopy(artifact)
    output_path, history_path, default_event_path = phase5_phase6_handoff_paths(settings)
    event_path = Path(event_log_path or default_event_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if record_event:
        output, _ = attach_phase5_phase6_handoff_event_log(
            output,
            event_log_path=event_path,
            settings=settings,
        )
    else:
        output["validation_errors"] = validate_phase5_phase6_handoff(output)
        if output["validation_errors"]:
            output["status"] = "error"
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase5_phase6_handoff(output)
    if output["validation_errors"]:
        output["status"] = "error"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE5_PHASE6_HANDOFF_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "handoff_state": output.get("handoff_state"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "phase5_certified": output.get("phase5_certified"),
        "phase6_handoff_allowed": output.get("phase6_handoff_allowed"),
        "phase6_learning_loop_plan_allowed": output.get(
            "phase6_learning_loop_plan_allowed"
        ),
        "phase6_learning_loop_implementation_allowed": output.get(
            "phase6_learning_loop_implementation_allowed"
        ),
        "phase7_proof_credit_allowed": output.get("phase7_proof_credit_allowed"),
        "closed_trade_count": output.get("closed_trade_count"),
        "postmortem_due_count": output.get("postmortem_due_count"),
        "blocker_count": output.get("blocker_count"),
        "event_log_written": output.get("event_log_written"),
        "event_log_event_count": output.get("event_log_event_count"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path, event_path, output
