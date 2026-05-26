"""Phase 5 Layer B readiness gate.

This pre-handoff artifact exists so Qadam can prepare a Phase 5 implementation
plan without silently starting Layer B orchestration. The gate is fail-closed:
Phase 5 implementation remains blocked until Q4-12 certification is actually
approved and the Phase 5 handoff flag is true.
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.phase4_certification import (
    build_phase4_certification,
    validate_phase4_certification,
)
from world_monitor.source_registry import EXPECTED_SOURCE_COUNT


PHASE5_READINESS_SCHEMA_VERSION = 1
PHASE5_READINESS_ARTIFACT = "phase5_layer_b_readiness.json"
PHASE5_READINESS_HISTORY = "phase5_layer_b_readiness_history.jsonl"
PHASE5_LAYER_B_SCOPE: tuple[str, ...] = (
    "approval_policy_router",
    "risk_agent",
    "global_strategy_and_venue_kill_switches",
    "execution_adapter_contract",
    "alpaca_paper_adapter",
    "prediction_market_adapter_read_only_then_guarded",
    "telegram_notifier",
    "position_monitor",
    "signal_review_ui",
    "functional_system_map_dashboard",
    "test_live_mode_guardrail",
)
PHASE5_READINESS_AUTHORITY_FLAGS: tuple[str, ...] = (
    "phase5_layer_b_implementation_allowed",
    "phase5_orchestration_start_allowed",
    "approval_policy_router_enabled",
    "risk_agent_approval_authority",
    "kill_switch_mutation_authority",
    "execution_adapter_write_authority",
    "paper_execution_allowed",
    "paper_order_allowed",
    "broker_write_allowed",
    "prediction_market_write_allowed",
    "telegram_live_notifications_allowed",
    "position_monitor_write_authority",
    "live_capital_enabled",
)
APPROVAL_ONLY_BLOCKERS: tuple[str, ...] = (
    "explicit_fund_manager_approval_required",
    "phase4_not_certified",
    "phase5_handoff_not_allowed",
)
PHASE5_READINESS_BOUNDARY = (
    "Phase 5 readiness is a pre-handoff planning gate only. It can allow a "
    "Phase 5 implementation plan to be drafted, but it cannot start Layer B "
    "orchestration, enable Risk Agent approval authority, mutate kill switches, "
    "stage or submit paper orders, write brokers, send live Telegram execution "
    "alerts, call prediction-market write endpoints, or enable live capital."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _phase4_certification(settings: Settings | None = None) -> dict[str, Any]:
    path = _runtime_dir(settings) / "phase4_certification.json"
    return _read_json(path) or build_phase4_certification(settings=settings)


def _authority_flags(enabled: bool = False) -> dict[str, bool]:
    return {field: enabled for field in PHASE5_READINESS_AUTHORITY_FLAGS}


def _phase4_authority_violation_count(certification: dict[str, Any]) -> int:
    authority_count_keys = (
        "trade_candidate_count",
        "execution_allowed_count",
        "paper_order_allowed_count",
        "staged_paper_order_allowed_count",
        "broker_write_allowed_count",
        "live_capital_enabled_count",
        "provider_call_allowed_count",
        "hardware_submission_allowed_count",
        "hardware_submitted_count",
        "hardware_scheduler_enabled_count",
        "scheduler_enabled_count",
        "authority_violation_count",
    )
    authority_flag_keys = (
        "trade_candidate_creation_allowed",
        "risk_approval_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "staged_paper_order_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
        "quantum_provider_call_allowed",
        "hardware_submission_allowed",
        "hardware_submitted",
        "hardware_scheduler_enabled",
        "scheduler_enabled",
    )
    count_violations = sum(
        1 for key in authority_count_keys if certification.get(key) not in (0, False, None)
    )
    flag_violations = sum(
        1 for key in authority_flag_keys if certification.get(key) is not False
    )
    return count_violations + flag_violations


def _readiness_blockers(
    certification: dict[str, Any],
    certification_errors: list[str],
) -> list[str]:
    blockers: list[str] = []
    approval_state = str(certification.get("approval_state") or "missing")
    preference_gate = certification.get("preference_mcp_certification_gate", {})
    market_policy = certification.get("market_confirmation_policy", {})

    if certification_errors:
        blockers.append("phase4_certification_validation_failed")
    if certification.get("phase4_certified") is not True:
        blockers.append("phase4_not_certified")
    if certification.get("phase5_handoff_allowed") is not True:
        blockers.append("phase5_handoff_not_allowed")
    if approval_state != "approved":
        blockers.append("explicit_fund_manager_approval_required")
    for blocker in certification.get("certification_blockers", []) or []:
        blockers.append(str(blocker))
    if _phase4_authority_violation_count(certification) != 0:
        blockers.append("phase4_authority_violation")
    if not isinstance(preference_gate, dict) or preference_gate.get("status") != "validated":
        blockers.append("preference_certification_gate_not_validated")
    else:
        if preference_gate.get("certification_blocker_count", 0) != 0:
            blockers.append("preference_certification_gate_blocked")
        if preference_gate.get("source_promotion_status") != "validated":
            blockers.append("preference_source_promotion_policy_invalid")
        if preference_gate.get("source_promotion_promoted_decision_count", 0) != 0:
            blockers.append("preference_source_promotion_policy_invalid")
        if preference_gate.get("source_promotion_canonical_source_count_after") != EXPECTED_SOURCE_COUNT:
            blockers.append("preference_source_promotion_policy_invalid")
        if preference_gate.get("preference_mcp_source_36") is not False:
            blockers.append("preference_source_promotion_policy_invalid")
    if market_policy.get("yahoo_finance_role") != "supplemental_market_confirmation_only":
        blockers.append("yahoo_finance_policy_not_supplemental")
    return sorted(dict.fromkeys(blockers))


def build_phase5_layer_b_readiness(
    settings: Settings | None = None,
    *,
    phase4_certification: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    certification = phase4_certification or _phase4_certification(settings)
    certification_errors = validate_phase4_certification(certification)
    preference_gate = certification.get("preference_mcp_certification_gate", {})
    market_policy = certification.get("market_confirmation_policy", {})
    blockers = _readiness_blockers(certification, certification_errors)
    nonapproval_blockers = [
        blocker for blocker in blockers if blocker not in APPROVAL_ONLY_BLOCKERS
    ]
    implementation_allowed = not blockers
    implementation_plan_allowed = not nonapproval_blockers
    authority_flags = _authority_flags(False)

    artifact = {
        "schema_version": PHASE5_READINESS_SCHEMA_VERSION,
        "artifact_type": "phase5_layer_b_readiness",
        "artifact_id": "phase5:pre-handoff:layer-b-readiness",
        "phase": "Q5",
        "layer": "Layer B",
        "stage": "P5-PRE",
        "status": (
            "ready_for_phase5_layer_b_implementation"
            if implementation_allowed
            else "blocked_pending_phase4_certification"
        ),
        "generated_at": _now(),
        "public_safe": True,
        **authority_flags,
        "phase5_layer_b_scope": list(PHASE5_LAYER_B_SCOPE),
        "phase5_layer_b_scope_count": len(PHASE5_LAYER_B_SCOPE),
        "phase5_layer_b_implementation_plan_allowed": implementation_plan_allowed,
        "phase5_layer_b_implementation_allowed": implementation_allowed,
        "phase5_orchestration_start_allowed": False,
        "phase5_handoff_allowed": certification.get("phase5_handoff_allowed") is True,
        "phase4_certification_status": str(certification.get("status") or "not_run"),
        "phase4_stage_status": str(certification.get("stage_status") or "not_run"),
        "phase4_certified": certification.get("phase4_certified") is True,
        "phase4_complete": certification.get("phase4_complete") is True,
        "phase4_certification_validation_error_count": len(certification_errors),
        "phase4_certification_blockers": list(
            certification.get("certification_blockers", []) or []
        ),
        "approval_state": str(certification.get("approval_state") or "missing"),
        "approval_logged": certification.get("approval_logged") is True,
        "approval_required_before_implementation": (
            certification.get("approval_state") != "approved"
        ),
        "preference_gate_status": str(preference_gate.get("status") or "not_run"),
        "preference_gate_blocker_count": int(
            preference_gate.get("certification_blocker_count", 0) or 0
        ),
        "preference_source_promotion_status": str(
            preference_gate.get("source_promotion_status") or "not_run"
        ),
        "preference_source_promotion_promoted_decision_count": int(
            preference_gate.get("source_promotion_promoted_decision_count", 0) or 0
        ),
        "preference_source_promotion_canonical_source_count_after": int(
            preference_gate.get("source_promotion_canonical_source_count_after", 0) or 0
        ),
        "preference_mcp_source_36": preference_gate.get("preference_mcp_source_36") is True,
        "yahoo_finance_role": str(market_policy.get("yahoo_finance_role") or "missing"),
        "nonapproval_blockers": nonapproval_blockers,
        "nonapproval_blocker_count": len(nonapproval_blockers),
        "readiness_blockers": blockers,
        "readiness_blocker_count": len(blockers),
        "only_explicit_approval_blocks_phase5_plan": (
            implementation_plan_allowed and not implementation_allowed
        ),
        "next_required_human_action": (
            "Log explicit Fund Manager approval for the amended Phase 4 strategy, "
            "then rerun Q4-10, Q4-12, and this pre-Phase-5 readiness gate."
            if not implementation_allowed
            else "Phase 5 Layer B implementation may be planned and started under its own gates."
        ),
        "authority_flags": authority_flags,
        "boundary": PHASE5_READINESS_BOUNDARY,
    }
    artifact["validation_errors"] = validate_phase5_layer_b_readiness(artifact)
    return artifact


def validate_phase5_layer_b_readiness(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "schema_version",
        "artifact_type",
        "artifact_id",
        "phase",
        "layer",
        "stage",
        "status",
        "generated_at",
        "public_safe",
        "phase5_layer_b_scope",
        "phase5_layer_b_scope_count",
        "phase5_layer_b_implementation_plan_allowed",
        "phase5_layer_b_implementation_allowed",
        "phase5_orchestration_start_allowed",
        "phase5_handoff_allowed",
        "phase4_certification_status",
        "phase4_stage_status",
        "phase4_certified",
        "phase4_complete",
        "phase4_certification_validation_error_count",
        "approval_state",
        "approval_logged",
        "preference_gate_status",
        "preference_source_promotion_status",
        "preference_source_promotion_promoted_decision_count",
        "preference_source_promotion_canonical_source_count_after",
        "preference_mcp_source_36",
        "yahoo_finance_role",
        "nonapproval_blocker_count",
        "readiness_blockers",
        "readiness_blocker_count",
        "authority_flags",
        "boundary",
    }
    missing = sorted(required_fields - set(artifact))
    if missing:
        errors.append("missing_fields:" + ",".join(missing))
    if artifact.get("schema_version") != PHASE5_READINESS_SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if artifact.get("artifact_type") != "phase5_layer_b_readiness":
        errors.append("artifact_type_mismatch")
    if artifact.get("phase") != "Q5" or artifact.get("layer") != "Layer B":
        errors.append("phase_or_layer_mismatch")
    if artifact.get("stage") != "P5-PRE":
        errors.append("stage_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("public_safe_not_true")
    if artifact.get("phase5_layer_b_scope_count") != len(
        artifact.get("phase5_layer_b_scope", [])
    ):
        errors.append("phase5_scope_count_mismatch")

    blockers = artifact.get("readiness_blockers", [])
    if not isinstance(blockers, list):
        errors.append("readiness_blockers_not_list")
        blockers = []
    if artifact.get("readiness_blocker_count") != len(blockers):
        errors.append("readiness_blocker_count_mismatch")
    nonapproval_blockers = artifact.get("nonapproval_blockers", [])
    if not isinstance(nonapproval_blockers, list):
        errors.append("nonapproval_blockers_not_list")
        nonapproval_blockers = []
    if artifact.get("nonapproval_blocker_count") != len(nonapproval_blockers):
        errors.append("nonapproval_blocker_count_mismatch")
    if artifact.get("phase4_certification_validation_error_count", 0) != 0:
        errors.append("phase4_certification_validation_failed")

    certified = artifact.get("phase4_certified") is True
    handoff_allowed = artifact.get("phase5_handoff_allowed") is True
    implementation_allowed = artifact.get("phase5_layer_b_implementation_allowed") is True
    if implementation_allowed and (not certified or not handoff_allowed or blockers):
        errors.append("phase5_layer_b_implementation_allowed_without_certified_phase4")
    if not implementation_allowed and artifact.get("status") != "blocked_pending_phase4_certification":
        errors.append("blocked_readiness_status_mismatch")
    if implementation_allowed and artifact.get("status") != "ready_for_phase5_layer_b_implementation":
        errors.append("implementation_ready_status_mismatch")
    if artifact.get("phase5_orchestration_start_allowed") is not False:
        errors.append("phase5_orchestration_start_allowed")
    if not certified and "phase4_not_certified" not in blockers:
        errors.append("phase4_not_certified_blocker_missing")
    if not handoff_allowed and "phase5_handoff_not_allowed" not in blockers:
        errors.append("phase5_handoff_blocker_missing")
    if artifact.get("approval_state") != "approved":
        if "explicit_fund_manager_approval_required" not in blockers:
            errors.append("explicit_approval_blocker_missing")
    if (
        artifact.get("phase5_layer_b_implementation_plan_allowed") is True
        and nonapproval_blockers
    ):
        errors.append("phase5_plan_allowed_with_nonapproval_blockers")

    if artifact.get("preference_gate_status") != "validated":
        errors.append("preference_gate_not_validated")
    if artifact.get("preference_source_promotion_status") != "validated":
        errors.append("preference_source_promotion_not_validated")
    if artifact.get("preference_source_promotion_promoted_decision_count") != 0:
        errors.append("preference_source_promotion_promoted")
    if (
        artifact.get("preference_source_promotion_canonical_source_count_after")
        != EXPECTED_SOURCE_COUNT
    ):
        errors.append("preference_source_promotion_source_count_mismatch")
    if artifact.get("preference_mcp_source_36") is not False:
        errors.append("preference_mcp_source_36")
    if artifact.get("yahoo_finance_role") != "supplemental_market_confirmation_only":
        errors.append("yahoo_finance_role_not_supplemental")

    flags = artifact.get("authority_flags", {})
    if not isinstance(flags, dict):
        errors.append("authority_flags_not_object")
    else:
        for key in PHASE5_READINESS_AUTHORITY_FLAGS:
            if flags.get(key) is not False:
                errors.append(f"phase5_readiness_authority_flag_enabled:{key}")
    for key in PHASE5_READINESS_AUTHORITY_FLAGS:
        if key == "phase5_layer_b_implementation_allowed":
            if artifact.get(key) is not implementation_allowed:
                errors.append("phase5_implementation_flag_mismatch")
            continue
        if artifact.get(key) is not False:
            errors.append(f"phase5_readiness_authority_enabled:{key}")
    if "cannot start Layer B orchestration" not in str(artifact.get("boundary") or ""):
        errors.append("boundary_missing_layer_b_start_block")
    return sorted(set(errors))


def phase5_readiness_paths(settings: Settings | None = None) -> tuple[Path, Path]:
    runtime = _runtime_dir(settings)
    return runtime / PHASE5_READINESS_ARTIFACT, runtime / PHASE5_READINESS_HISTORY


def write_phase5_layer_b_readiness(
    artifact: dict[str, Any],
    *,
    settings: Settings | None = None,
) -> tuple[Path, Path]:
    output = deepcopy(artifact)
    output_path, history_path = phase5_readiness_paths(settings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output["runtime_artifact_path"] = str(output_path)
    output["history_log_path"] = str(history_path)
    output["validation_errors"] = validate_phase5_layer_b_readiness(output)
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    history_record = {
        "schema_version": PHASE5_READINESS_SCHEMA_VERSION,
        "artifact_id": output.get("artifact_id"),
        "status": output.get("status"),
        "generated_at": output.get("generated_at"),
        "recorded_at": _now(),
        "phase5_layer_b_implementation_plan_allowed": output.get(
            "phase5_layer_b_implementation_plan_allowed"
        ),
        "phase5_layer_b_implementation_allowed": output.get(
            "phase5_layer_b_implementation_allowed"
        ),
        "phase5_orchestration_start_allowed": output.get(
            "phase5_orchestration_start_allowed"
        ),
        "readiness_blocker_count": output.get("readiness_blocker_count"),
        "nonapproval_blocker_count": output.get("nonapproval_blocker_count"),
        "validation_error_count": len(output.get("validation_errors", [])),
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record, sort_keys=True) + "\n")
    return output_path, history_path
