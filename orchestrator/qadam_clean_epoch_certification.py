"""Final fail-closed certification for the clean US$100,000 paper epoch."""

from __future__ import annotations

from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    runtime_dir,
    unique_errors,
    validate_authority,
)

SCHEMA_VERSION = "qadam_clean_epoch_certification.v1"
CERTIFICATION_ARTIFACT = "qadam_clean_epoch_operational_readiness_certification.json"
CHECK_ARTIFACT = "qadam_clean_epoch_operational_readiness_checks.json"
DYNAMIC_STATUS_ARTIFACT = "qadam_clean_epoch_dynamic_status.json"


def _phase(
    phase_id: str,
    name: str,
    implementation_complete: bool,
    operating_gate_passed: bool,
    blockers: list[str],
    artifacts: list[str],
) -> dict[str, Any]:
    return {
        "phase_id": phase_id,
        "name": name,
        "implementation_complete": implementation_complete,
        "operating_gate_passed": operating_gate_passed,
        "state": (
            "passed"
            if implementation_complete and operating_gate_passed
            else "implemented_waiting_for_real_evidence"
            if implementation_complete
            else "implementation_incomplete"
        ),
        "blockers": blockers,
        "artifact_refs": [f"data/runtime/{artifact}" for artifact in artifacts],
    }


def build_clean_epoch_certification(
    settings: Settings | None = None,
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    preflight = read_json(runtime / "qadam_clean_epoch_preflight_baseline.json")
    contracts = read_json(runtime / "qadam_certification_contract_audit.json")
    producers = read_json(runtime / "qadam_runtime_producer_registry.json")
    source_repair = read_json(runtime / "qadam_source_repair_closure.json")
    public_bridge = read_json(runtime / "qadam_public_status_bridge_checks.json")
    historical = read_json(runtime / "qadam_historical_gap_resolution_checks.json")
    recert = read_json(runtime / "qadam_backtest_recertification.json")
    edges = read_json(runtime / "qadam_edge_registry_v3.json")
    edge_audit = read_json(runtime / "qadam_edge_promotion_audit.json")
    operator_cert = read_json(runtime / "qadam_operator_ready_edge_engine_certification.json")
    shadow = read_json(runtime / "qadam_forward_shadow_checks.json")
    soak = read_json(runtime / "qadam_operator_soak_v2.json")
    broker = read_json(runtime / "qadam_clean_broker_account_preflight.json")
    cutover = read_json(runtime / "qadam_clean_epoch_cutover_readiness.json")
    cutover_receipt = read_json(runtime / "qadam_clean_epoch_cutover_receipt.json")
    epoch = read_json(runtime / "current_paper_epoch.json")
    dashboard_epoch = read_json(runtime / "qadam_dashboard_epoch_isolation.json")
    dashboard = read_json(runtime / "qadam_operator_dashboard_checks.json")
    lock = read_json(runtime / "qadam_long_backtest_lock.json")
    service = read_json(runtime / "qadam_operator_service_checks.json")
    launch_checks = read_json(runtime / "qadam_guarded_paper_launch_checks.json")
    operating_checks = read_json(runtime / "qadam_clean_epoch_operating_checks.json")
    operating_status = read_json(runtime / "qadam_clean_epoch_operating_status.json")

    phase0_gate = bool(
        (
            preflight.get("research_lock_active") is True
            and preflight.get("paperops_watch_only") is True
        )
        or (
            launch_checks.get("guarded_paper_operation_running") is True
            and lock.get("status") == "released"
            and lock.get("paperops_watch_only_mode") is False
        )
    )
    phase1_gate = contracts.get("status") == "passed"
    phase2_gate = bool(
        producers.get("stale_or_missing_artifact_count") == 0
        and source_repair.get("blocking_repair_request_count") == 0
    )
    phase3_gate = public_bridge.get("operating_ready") is True
    phase4_gate = bool(
        historical.get("acceptance_passed") is True
        and recert.get("research_protocol_valid") is True
    )
    phase5_gate = edges.get("paper_operator_edge_gate_passed") is True
    phase6_gate = bool(
        phase5_gate
        and shadow.get("promotion_ready") is True
        and operator_cert.get("paper_operator_ready") is True
    )
    phase7_gate = soak.get("soak_complete") is True
    phase8_gate = broker.get("preflight_passed") is True
    phase9_gate = bool(
        cutover_receipt.get("cutover_executed") is True
        and epoch.get("paper_epoch_kind") == "clean_operator_epoch"
    )
    phase10_gate = bool(
        phase9_gate
        and dashboard_epoch.get("status") == "passed"
        and dashboard.get("portfolio_values_agree") is True
        and public_bridge.get("operating_ready") is True
    )
    phase11_gate = bool(
        phase10_gate
        and launch_checks.get("guarded_paper_operation_running") is True
    )
    phase12_gate = bool(
        phase11_gate
        and operating_status.get("post_launch_monitoring_active") is True
    )
    phase11_implemented = launch_checks.get("implementation_ready") is True
    phase12_implemented = operating_checks.get("implementation_ready") is True

    phases = [
        _phase("Phase 0", "Freeze, snapshot, and rebaseline", True, phase0_gate, [] if phase0_gate else ["preflight_boundary_not_passed"], ["qadam_clean_epoch_preflight_baseline.json"]),
        _phase("Phase 1", "Repair certification truth", True, phase1_gate, [] if phase1_gate else ["certification_contracts_not_passed"], ["qadam_certification_contract_audit.json"]),
        _phase("Phase 2", "Fresh source and runtime production", True, phase2_gate, [] if phase2_gate else ["runtime_producer_or_source_repair_freshness_open"], ["qadam_runtime_producer_registry.json", "qadam_source_repair_closure.json"]),
        _phase("Phase 3", "One-way production dashboard freshness", True, phase3_gate, [] if phase3_gate else ["public_status_bridge_operator_setup_or_parity_open"], ["qadam_public_status_bridge_checks.json"]),
        _phase("Phase 4", "Historical evidence and backtest closure", True, phase4_gate, [] if phase4_gate else ["historical_gap_or_recertification_failed"], ["qadam_historical_gap_resolution.json", "qadam_backtest_recertification.json"]),
        _phase("Phase 5", "Validate an edge or remain in research", True, phase5_gate, [] if phase5_gate else ["no_validated_edge_survived_frozen_policy"], ["qadam_edge_registry_v3.json", "qadam_edge_promotion_audit.json"]),
        _phase("Phase 6", "Akber, shadow, risk, and Router readiness", True, phase6_gate, [] if phase6_gate else ["validated_edge_and_real_forward_shadow_required"], ["qadam_forward_shadow_checks.json", "qadam_operator_ready_edge_engine_certification.json"]),
        _phase("Phase 7", "Seven-session unattended soak", True, phase7_gate, [] if phase7_gate else [f"real_soak_incomplete:{soak.get('completed_real_session_count', 0)}/7"], ["qadam_operator_soak_v2.json"]),
        _phase("Phase 8", "Prepare clean Alpaca Paper account", True, phase8_gate, [] if phase8_gate else ["new_empty_100000_usd_paper_account_not_verified"], ["qadam_clean_broker_account_preflight.json"]),
        _phase("Phase 9", "Archive and transactional cutover", True, phase9_gate, [] if phase9_gate else ["cutover_correctly_not_executed"], ["qadam_clean_epoch_cutover_readiness.json", "qadam_clean_epoch_cutover_receipt.json"]),
        _phase("Phase 10", "Clean dashboard projection", True, phase10_gate, [] if phase10_gate else ["clean_epoch_dashboard_not_active_and_verified"], ["qadam_dashboard_epoch_isolation.json"]),
        _phase("Phase 11", "Guarded autonomous paper launch", phase11_implemented, phase11_gate, [] if phase11_gate else ["launch_forbidden_until_phases_0_to_10_pass"], ["qadam_guarded_paper_launch_receipt.json", "qadam_guarded_paper_launch_checks.json"]),
        _phase("Phase 12", "Post-launch evidence discipline", phase12_implemented, phase12_gate, [] if phase12_gate else ["post_launch_monitoring_not_applicable_before_launch"], ["qadam_clean_epoch_operating_status.json", "qadam_clean_epoch_operating_checks.json"]),
    ]
    implementation_complete = all(
        phase["implementation_complete"] for phase in phases
    )
    prelaunch_ready = all(
        phase["operating_gate_passed"] for phase in phases[:11]
    )
    fully_operating = all(
        phase["operating_gate_passed"] for phase in phases
    )
    blockers = [
        {"phase_id": phase["phase_id"], "reason": blocker}
        for phase in phases
        for blocker in phase["blockers"]
    ]
    first_waiting = next(
        (phase for phase in phases if not phase["operating_gate_passed"]), phases[-1]
    )
    certification = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_clean_epoch_operational_readiness_certification",
        "generated_at": now_iso(),
        "status": (
            "passed"
            if fully_operating
            else "ready_for_explicit_operator_release"
            if prelaunch_ready
            else "blocked"
        ),
        "implementation_complete": implementation_complete,
        "operational_launch_ready": prelaunch_ready,
        "fully_operating": fully_operating,
        "paper_trial_resume_allowed": prelaunch_ready,
        "current_waiting_phase": first_waiting["phase_id"],
        "current_waiting_reason": first_waiting["blockers"],
        "phase_count": len(phases),
        "implemented_phase_count": sum(
            phase["implementation_complete"] for phase in phases
        ),
        "operating_gate_pass_count": sum(
            phase["operating_gate_passed"] for phase in phases
        ),
        "phases": phases,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "testing_epoch_archived": phase9_gate,
        "clean_epoch_active": epoch.get("paper_epoch_kind") == "clean_operator_epoch",
        "starting_balance": 100000.0,
        "account_currency": "USD",
        "research_lock_active": lock.get("status") == "active",
        "paperops_watch_only": service.get("paperops_watch_only") is True,
        "validated_edge_count": int(edges.get("validated_edge_count") or 0),
        "thresholds_relaxed_to_force_edge": edge_audit.get(
            "thresholds_relaxed_to_force_edge"
        ),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "live_capital_enabled": False,
        "paper_calendar_advanced": False,
        "authority": authority_flags(),
    }
    dynamic = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_clean_epoch_dynamic_status",
        "generated_at": certification["generated_at"],
        "plan_state": (
            "fully_operating"
            if fully_operating
            else "operational_launch_ready"
            if prelaunch_ready
            else "implementation_complete_evidence_maturing"
        ),
        "current_phase": first_waiting["phase_id"],
        "current_phase_name": first_waiting["name"],
        "phase_states": {phase["phase_id"]: phase["state"] for phase in phases},
        "testing_epoch_archived": certification["testing_epoch_archived"],
        "clean_epoch_active": certification["clean_epoch_active"],
        "paperops_watch_only": certification["paperops_watch_only"],
        "research_lock_active": certification["research_lock_active"],
        "next_required_action": first_waiting["blockers"],
        "authority": authority_flags(),
    }
    return {"certification": certification, "dynamic_status": dynamic}


def validate_clean_epoch_certification(state: dict[str, Any]) -> list[str]:
    certification = state["certification"]
    dynamic = state["dynamic_status"]
    errors: list[str] = []
    if certification.get("operational_launch_ready") is True:
        if certification.get("validated_edge_count", 0) <= 0:
            errors.append("clean_epoch_certified_without_validated_edge")
        if certification.get("clean_epoch_active") is not True:
            errors.append("clean_epoch_certified_without_clean_epoch")
        if certification.get("testing_epoch_archived") is not True:
            errors.append("clean_epoch_certified_without_testing_archive")
    if certification.get("thresholds_relaxed_to_force_edge") is not False:
        errors.append("clean_epoch_thresholds_relaxed_to_force_edge")
    if certification.get("paper_calendar_advanced") is not False:
        errors.append("clean_epoch_certification_advanced_calendar")
    errors.extend(
        validate_authority(certification.get("authority", {}), prefix="clean_epoch_cert")
    )
    errors.extend(
        validate_authority(dynamic.get("authority", {}), prefix="clean_epoch_dynamic")
    )
    return unique_errors(errors)


def build_and_write_clean_epoch_certification(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    state = build_clean_epoch_certification(settings)
    errors = validate_clean_epoch_certification(state)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_clean_epoch_operational_readiness_checks",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "implementation_valid": not errors,
        "operational_launch_ready": state["certification"][
            "operational_launch_ready"
        ],
        "paper_trial_resume_allowed": state["certification"][
            "paper_trial_resume_allowed"
        ],
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    store.write_json(CERTIFICATION_ARTIFACT, state["certification"])
    store.write_json(DYNAMIC_STATUS_ARTIFACT, state["dynamic_status"])
    store.write_json(CHECK_ARTIFACT, checks)
    return state, checks, errors


__all__ = [
    "CERTIFICATION_ARTIFACT",
    "CHECK_ARTIFACT",
    "DYNAMIC_STATUS_ARTIFACT",
    "build_and_write_clean_epoch_certification",
    "validate_clean_epoch_certification",
]
