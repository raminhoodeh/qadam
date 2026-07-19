"""Version-bound unattended reliability evidence for the experimental epoch."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    sha256_json,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_operator_service import SERVICE_DEFINITIONS

SCHEMA_VERSION = "qadam_operator_soak_v3.v1"
SOAK_ARTIFACT = "qadam_operator_soak_v3.json"
RESILIENCE_ARTIFACT = "qadam_operator_resilience_probes.json"
CHECK_ARTIFACT = "qadam_operator_soak_v3_checks.json"
REQUIRED_REAL_SESSIONS = 7


def operator_service_contract_hash() -> str:
    return sha256_json([definition.to_dict() for definition in SERVICE_DEFINITIONS])


def _parse(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _release_binding(runtime: Any) -> dict[str, Any]:
    release = read_json(runtime / "qadam_experimental_paper_release_readiness.json")
    epoch = read_json(runtime / "current_paper_epoch.json")
    return {
        "release_effective": release.get("experimental_paper_release_effective") is True,
        "release_started_at": release.get("release_started_at"),
        "release_binding_digest": release.get("binding_digest"),
        "paper_epoch_id": epoch.get("paper_epoch_id"),
        "paper_epoch_kind": epoch.get("paper_epoch_kind"),
        "policy_version": release.get("policy_version"),
        "risk_policy_version": release.get("risk_policy_version"),
        "operator_service_contract_hash": operator_service_contract_hash(),
    }


def build_operator_soak_v3(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    binding = _release_binding(runtime)
    release_started = _parse(binding["release_started_at"])
    sessions = read_jsonl(runtime / "qadam_operator_session_ledger.jsonl")
    eligible_sessions = [
        row
        for row in sessions
        if binding["release_effective"]
        and release_started is not None
        and (_parse(row.get("generated_at")) or datetime.min.replace(tzinfo=timezone.utc))
        >= release_started
        and row.get("real_elapsed_time") is True
        and row.get("simulated_elapsed_time_used") is False
        and row.get("paper_epoch_id") == binding["paper_epoch_id"]
        and row.get("release_binding_digest") == binding["release_binding_digest"]
        and row.get("policy_version") == binding["policy_version"]
        and row.get("risk_policy_version") == binding["risk_policy_version"]
        and row.get("operator_service_contract_hash")
        == binding["operator_service_contract_hash"]
    ]
    dates = sorted(
        {
            str(row.get("real_calendar_date"))
            for row in eligible_sessions
            if row.get("real_calendar_date")
        }
    )
    probe_source = read_json(runtime / "qadam_operator_soak_test.json")
    scenarios = probe_source.get("scenarios")
    scenarios = scenarios if isinstance(scenarios, list) else []
    required = {
        "network_loss",
        "laptop_sleep",
        "sigterm",
        "provider_429",
        "malformed_response",
        "stale_lock",
        "disk_threshold",
        "unsafe_route",
    }
    scenario_state = {
        str(row.get("scenario")): bool(
            row.get("classification_passed") is True
            and row.get("safe_response_passed") is True
            and row.get("paper_order_created") is False
            and int(row.get("broker_write_count") or 0) == 0
        )
        for row in scenarios
        if isinstance(row, dict) and row.get("scenario")
    }
    all_probes_passed = all(scenario_state.get(name) is True for name in required)
    service = read_json(runtime / "qadam_operator_service_checks.json")
    bridge = read_json(runtime / "qadam_public_status_bridge_checks.json")
    repairs = read_json(runtime / "qadam_operator_repair_queue.json")
    completed = len(dates)
    critical_repairs = int(repairs.get("critical_request_count") or 0)
    certified = bool(
        binding["release_effective"]
        and completed >= REQUIRED_REAL_SESSIONS
        and all_probes_passed
        and service.get("service_running") is True
        and bridge.get("operating_ready") is True
        and critical_repairs == 0
    )
    blockers: list[str] = []
    if not binding["release_effective"]:
        blockers.append("experimental_paper_release_not_effective")
    if completed < REQUIRED_REAL_SESSIONS:
        blockers.append(f"version_bound_real_sessions_incomplete:{completed}/7")
    if not all_probes_passed:
        blockers.append("required_resilience_probe_failed_or_missing")
    if service.get("service_running") is not True:
        blockers.append("operator_service_not_running")
    if bridge.get("operating_ready") is not True:
        blockers.append("public_status_bridge_not_current")
    if critical_repairs:
        blockers.append("critical_operator_repair_request_open")
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_soak_v3",
        "generated_at": now_iso(),
        "status": (
            "passed"
            if certified
            else "waiting_for_experimental_release"
            if not binding["release_effective"]
            else "in_progress"
        ),
        "unattended_reliability_certified": certified,
        "soak_complete": certified,
        "required_real_session_count": REQUIRED_REAL_SESSIONS,
        "completed_real_session_count": completed,
        "real_session_dates": dates,
        "eligible_session_record_count": len(eligible_sessions),
        "pre_release_or_version_mismatched_session_count": len(sessions)
        - len(eligible_sessions),
        "one_session_credit_per_real_utc_date": True,
        "simulated_elapsed_time_used": False,
        "binding": binding,
        "all_required_resilience_probes_passed": all_probes_passed,
        "operator_service_running": service.get("service_running") is True,
        "public_status_bridge_current": bridge.get("operating_ready") is True,
        "critical_repair_count": critical_repairs,
        "blocker_count": len(blockers),
        "blockers": unique_errors(blockers),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "paper_calendar_advanced": False,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }


def _resilience_projection(soak: dict[str, Any], settings: Settings | None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    source = read_json(runtime / "qadam_operator_soak_test.json")
    scenarios = source.get("scenarios")
    scenarios = scenarios if isinstance(scenarios, list) else []
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_resilience_probes",
        "generated_at": soak["generated_at"],
        "status": (
            "passed"
            if soak["all_required_resilience_probes_passed"]
            else "blocked"
        ),
        "release_binding": soak["binding"],
        "probe_count": len(scenarios),
        "passed_probe_count": sum(
            row.get("safe_response_passed") is True for row in scenarios
        ),
        "probes": scenarios,
        "probe_success_does_not_create_session_credit": True,
        "automatic_paperops_retry_allowed": False,
        "automatic_code_edit_allowed": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }


def validate_operator_soak_v3(soak: dict[str, Any], probes: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if soak.get("simulated_elapsed_time_used") is not False:
        errors.append("operator_soak_v3_simulated_elapsed_time")
    if soak.get("soak_complete") is True and int(
        soak.get("completed_real_session_count") or 0
    ) < REQUIRED_REAL_SESSIONS:
        errors.append("operator_soak_v3_passed_without_seven_real_sessions")
    if soak.get("soak_complete") is True and soak.get("binding", {}).get(
        "release_effective"
    ) is not True:
        errors.append("operator_soak_v3_passed_without_effective_release")
    if probes.get("automatic_paperops_retry_allowed") is not False:
        errors.append("operator_soak_v3_allows_paperops_retry")
    for payload, prefix in ((soak, "operator_soak_v3"), (probes, "resilience_probes")):
        if int(payload.get("broker_write_count") or 0) != 0:
            errors.append(f"{prefix}_broker_write_count_nonzero")
        if payload.get("live_capital_enabled") is not False:
            errors.append(f"{prefix}_live_capital_enabled")
        errors.extend(validate_authority(payload.get("authority", {}), prefix=prefix))
    return unique_errors(errors)


def build_and_write_operator_soak_v3(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[str]]:
    soak = build_operator_soak_v3(settings)
    probes = _resilience_projection(soak, settings)
    errors = validate_operator_soak_v3(soak, probes)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_soak_v3_checks",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "implementation_ready": not errors,
        "unattended_reliability_certified": soak["soak_complete"],
        "completed_real_session_count": soak["completed_real_session_count"],
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    store = AtomicArtifactStore(runtime_dir(settings))
    store.write_json(SOAK_ARTIFACT, soak)
    store.write_json(RESILIENCE_ARTIFACT, probes)
    store.write_json(CHECK_ARTIFACT, checks)
    return soak, probes, checks, errors


__all__ = [
    "CHECK_ARTIFACT",
    "REQUIRED_REAL_SESSIONS",
    "RESILIENCE_ARTIFACT",
    "SOAK_ARTIFACT",
    "build_and_write_operator_soak_v3",
    "build_operator_soak_v3",
    "operator_service_contract_hash",
    "validate_operator_soak_v3",
]
