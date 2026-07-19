"""Conservative real-session soak and clean-paper release-candidate audit."""

from __future__ import annotations

from collections import Counter
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    unique_errors,
    validate_authority,
)

SCHEMA_VERSION = "qadam_operator_soak_v2.v1"
SOAK_ARTIFACT = "qadam_operator_soak_v2.json"
RELEASE_CANDIDATE_ARTIFACT = "qadam_paper_trial_release_candidate.json"
CHECK_ARTIFACT = "qadam_operator_soak_v2_checks.json"
REQUIRED_REAL_SESSIONS = 7


def build_operator_soak_v2(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    legacy = read_json(runtime / "qadam_operator_soak_test.json")
    sessions = [
        row
        for row in read_jsonl(runtime / "qadam_operator_session_ledger.jsonl")
        if row.get("real_elapsed_time") is True
        and row.get("simulated_elapsed_time_used") is False
    ]
    dates = sorted(
        {
            str(row.get("real_calendar_date"))
            for row in sessions
            if row.get("real_calendar_date")
        }
    )
    scenarios = legacy.get("scenarios") if isinstance(legacy.get("scenarios"), list) else []
    scenario_state = {
        str(row.get("scenario")): bool(
            row.get("classification_passed") is True
            and row.get("safe_response_passed") is True
            and int(row.get("broker_write_count") or 0) == 0
            and row.get("paper_order_created") is False
        )
        for row in scenarios
        if isinstance(row, dict) and row.get("scenario")
    }
    required_scenarios = {
        "network_loss",
        "laptop_sleep",
        "sigterm",
        "provider_429",
        "malformed_response",
        "stale_lock",
        "disk_threshold",
        "unsafe_route",
    }
    scenario_passed = all(scenario_state.get(name) is True for name in required_scenarios)
    service = read_json(runtime / "qadam_operator_service_checks.json")
    publisher = read_json(runtime / "qadam_public_status_publication_receipt.json")
    bridge = read_json(runtime / "qadam_public_status_bridge_security.json")
    parity = read_json(runtime / "qadam_public_status_parity.json")
    repair = read_json(runtime / "qadam_operator_repair_queue.json")
    source = read_json(runtime / "qadam_source_provider_capabilities_checks.json")
    completed_sessions = len(dates)
    service_running = service.get("service_running") is True
    publisher_configured = publisher.get("status") in {
        "published",
        "published_and_verified",
    }
    dashboard_parity_passed = parity.get("status") in {
        "passed",
        "digest_match",
        "published_and_verified",
    }
    critical_repairs = int(
        repair.get("critical_open_count")
        or repair.get("blocking_repair_request_count")
        or 0
    )
    safe = bool(
        completed_sessions >= REQUIRED_REAL_SESSIONS
        and service_running
        and scenario_passed
        and publisher_configured
        and dashboard_parity_passed
        and critical_repairs == 0
        and int(source.get("blocking_repair_request_count") or 0) == 0
    )
    blockers = []
    if completed_sessions < REQUIRED_REAL_SESSIONS:
        blockers.append(
            f"real_unattended_sessions_incomplete:{completed_sessions}/{REQUIRED_REAL_SESSIONS}"
        )
    if not service_running:
        blockers.append("operator_service_not_running")
    if not scenario_passed:
        blockers.append("required_interruption_probe_failed_or_missing")
    if not publisher_configured:
        blockers.append("one_way_public_status_publisher_not_configured_or_verified")
    if not dashboard_parity_passed:
        blockers.append("production_dashboard_digest_parity_not_verified")
    if critical_repairs:
        blockers.append("critical_operator_repair_request_open")
    if int(source.get("blocking_repair_request_count") or 0):
        blockers.append("blocking_source_repair_request_open")
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_soak_v2",
        "generated_at": now_iso(),
        "status": "passed" if safe else "in_progress",
        "soak_complete": safe,
        "required_real_session_count": REQUIRED_REAL_SESSIONS,
        "completed_real_session_count": completed_sessions,
        "real_session_dates": dates,
        "raw_session_observation_count": len(sessions),
        "session_counting_policy": (
            "At most one credit per real UTC calendar date. Repeated scheduler cycles "
            "cannot manufacture soak credit."
        ),
        "simulated_elapsed_time_used": False,
        "interruption_probe_count": len(scenarios),
        "interruption_probe_pass_count": sum(scenario_state.values()),
        "required_interruption_scenarios": sorted(required_scenarios),
        "interruption_scenario_state": dict(sorted(scenario_state.items())),
        "all_required_interruption_probes_passed": scenario_passed,
        "operator_service_running": service_running,
        "public_status_publisher_verified": publisher_configured,
        "public_status_bridge_security_state": bridge.get("status"),
        "production_dashboard_parity_passed": dashboard_parity_passed,
        "critical_repair_count": critical_repairs,
        "blocking_source_repair_count": int(
            source.get("blocking_repair_request_count") or 0
        ),
        "paperops_watch_only": service.get("paperops_watch_only") is True,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "paper_calendar_advanced": False,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "authority": authority_flags(),
    }


def _release_candidate(soak: dict[str, Any], runtime: Any) -> dict[str, Any]:
    certification = read_json(
        runtime / "qadam_operator_ready_edge_engine_certification.json"
    )
    broker = read_json(runtime / "qadam_clean_broker_account_preflight.json")
    edge = read_json(runtime / "qadam_edge_registry_v3.json")
    ready = bool(
        soak.get("soak_complete") is True
        and certification.get("certification_passed") is True
        and certification.get("paper_trial_resume_allowed") is True
        and broker.get("preflight_passed") is True
        and edge.get("paper_operator_edge_gate_passed") is True
    )
    blockers = []
    if soak.get("soak_complete") is not True:
        blockers.append("operator_soak_not_complete")
    if certification.get("certification_passed") is not True:
        blockers.append("operator_ready_certification_not_passed")
    if certification.get("paper_trial_resume_allowed") is not True:
        blockers.append("paper_trial_resume_not_allowed")
    if broker.get("preflight_passed") is not True:
        blockers.append("clean_broker_preflight_not_passed")
    if edge.get("paper_operator_edge_gate_passed") is not True:
        blockers.append("validated_edge_gate_not_passed")
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_paper_trial_release_candidate",
        "generated_at": now_iso(),
        "status": "ready_for_human_release_review" if ready else "blocked",
        "release_candidate": ready,
        "human_release_decision_required": True,
        "release_automatically_applied": False,
        "paper_trial_resume_allowed": ready,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "paper_calendar_advanced": False,
        "authority": authority_flags(),
    }


def validate_operator_soak_v2(
    soak: dict[str, Any], release: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    if soak.get("simulated_elapsed_time_used") is not False:
        errors.append("operator_soak_uses_simulated_elapsed_time")
    if soak.get("soak_complete") is True and int(
        soak.get("completed_real_session_count") or 0
    ) < REQUIRED_REAL_SESSIONS:
        errors.append("operator_soak_passed_without_seven_real_sessions")
    if release.get("release_candidate") is True and soak.get("soak_complete") is not True:
        errors.append("paper_release_candidate_without_soak")
    if release.get("release_automatically_applied") is not False:
        errors.append("paper_release_was_automatically_applied")
    errors.extend(validate_authority(soak.get("authority", {}), prefix="operator_soak_v2"))
    errors.extend(
        validate_authority(release.get("authority", {}), prefix="paper_release_candidate")
    )
    return unique_errors(errors)


def build_and_write_operator_soak_v2(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    soak = build_operator_soak_v2(settings)
    release = _release_candidate(soak, runtime)
    errors = validate_operator_soak_v2(soak, release)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_soak_v2_checks",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "implementation_valid": not errors,
        "soak_complete": soak["soak_complete"],
        "completed_real_session_count": soak["completed_real_session_count"],
        "release_candidate": release["release_candidate"],
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    store.write_json(SOAK_ARTIFACT, soak)
    store.write_json(RELEASE_CANDIDATE_ARTIFACT, release)
    store.write_json(CHECK_ARTIFACT, checks)
    return soak, release, checks, errors


__all__ = [
    "CHECK_ARTIFACT",
    "RELEASE_CANDIDATE_ARTIFACT",
    "SOAK_ARTIFACT",
    "build_and_write_operator_soak_v2",
    "build_operator_soak_v2",
    "validate_operator_soak_v2",
]
