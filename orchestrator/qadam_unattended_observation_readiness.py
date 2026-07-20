"""Certify that Qadam can be left running safely while real evidence matures."""

from __future__ import annotations

from pathlib import Path
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
from orchestrator.qadam_paperops_runtime_owner import paperops_runtime_owner_status


SCHEMA_VERSION = "qadam_unattended_observation_readiness.v1"
STATUS_ARTIFACT = "qadam_unattended_observation_readiness.json"
CHECK_ARTIFACT = "qadam_unattended_observation_readiness_checks.json"
OPERATOR_PLIST = Path.home() / "Library" / "LaunchAgents" / "com.qadam.operator.plist"


def _sleep_prevention_configured(path: Path = OPERATOR_PLIST) -> bool:
    if not path.is_file():
        return False
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return "/usr/bin/caffeinate" in content and "<string>-s</string>" in content


def build_unattended_observation_readiness(
    settings: Settings | None = None,
    *,
    operator_plist: Path | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    runtime = runtime_dir(settings)
    operator = read_json(runtime / "qadam_operator_service_status.json")
    operator_checks = read_json(runtime / "qadam_operator_service_checks.json")
    release = read_json(runtime / "qadam_experimental_paper_release_readiness.json")
    lock = read_json(runtime / "qadam_long_backtest_lock.json")
    epoch = read_json(runtime / "current_paper_epoch.json")
    forward = read_json(runtime / "qadam_forward_shadow_checks.json")
    legacy = read_json(runtime / "qadam_research_supervisor_checks.json")
    bridge = read_json(runtime / "qadam_public_status_bridge_checks.json")
    soak = read_json(runtime / "qadam_operator_soak_v3.json")
    edge_registry = read_json(runtime / "qadam_edge_registry.json")
    owner = paperops_runtime_owner_status(settings)
    sleep_safe = _sleep_prevention_configured(operator_plist or OPERATOR_PLIST)

    engineering_checks = {
        "paper_mode": settings.mode == "paper",
        "live_capital_disabled": settings.live_capital_enabled is False,
        "experimental_release_effective": (
            release.get("experimental_paper_release_effective") is True
            and not (release.get("blockers") or [])
        ),
        "clean_epoch_active": (
            epoch.get("paper_epoch_kind") == "clean_experimental_operator_epoch"
            and epoch.get("paper_growth_trial_calendar_started") is True
            and epoch.get("simulated_elapsed_time") is False
        ),
        "research_lock_narrowly_released": (
            lock.get("status") == "released"
            and lock.get("paperops_watch_only_mode") is False
        ),
        "operator_service_running": (
            operator.get("service_running") is True
            and operator.get("liveness", {}).get("process_running") is True
        ),
        "operator_checks_passed": operator_checks.get("status") == "passed",
        "operator_circuits_closed": int(operator.get("open_circuit_count") or 0) == 0,
        "operator_observation_ready": operator.get("observation_ready") is True,
        "forward_shadow_continuous": (
            forward.get("implementation_ready") is True
            and forward.get("continuous_scheduler_installed") is True
            and forward.get("shadow_service_running") is True
            and forward.get("shadow_service_cycle_fresh") is True
        ),
        "legacy_supervisor_safely_superseded": (
            legacy.get("status") == "passed"
            and legacy.get("superseded_by_operator_service") is True
            and legacy.get("scheduler_owner") == "qadam_operator_service"
        ),
        "guarded_paperops_owner_active": owner.get("active") is True,
        "public_dashboard_bridge_current": bridge.get("operating_ready") is True,
        "ac_power_sleep_prevention_configured": sleep_safe,
    }
    blockers = sorted(key for key, passed in engineering_checks.items() if not passed)
    ready = not blockers
    completed_sessions = int(soak.get("completed_real_session_count") or 0)
    required_sessions = int(soak.get("required_real_session_count") or 7)
    validated_edges = int(
        edge_registry.get("validated_edge_count")
        or edge_registry.get("summary", {}).get("validated_edge_count")
        or 0
    )
    shadow_outcomes = int(forward.get("outcome_count") or 0)
    maturity = [
        {
            "requirement": "version_bound_unattended_soak",
            "state": "complete" if completed_sessions >= required_sessions else "accruing_real_time",
            "progress": f"{completed_sessions}/{required_sessions} real UTC dates",
            "automatic": True,
            "can_be_backfilled": False,
        },
        {
            "requirement": "validated_market_edge",
            "state": "observed" if validated_edges else "evidence_maturing",
            "progress": f"{validated_edges} canonical validated edges",
            "automatic": True,
            "can_be_forced": False,
        },
        {
            "requirement": "real_forward_shadow_outcomes",
            "state": "observed" if shadow_outcomes else "waiting_for_eligible_signals_and_time",
            "progress": f"{shadow_outcomes} real outcomes",
            "automatic": True,
            "can_be_simulated": False,
        },
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_unattended_observation_readiness",
        "generated_at": now_iso(),
        "status": "passed_ready_to_observe" if ready else "blocked_engineering_work_remaining",
        "safe_to_leave_running_and_observe": ready,
        "autonomous_runtime_enabled": ready,
        "healthy_idle_is_valid": True,
        "paper_epoch_id": epoch.get("paper_epoch_id"),
        "paper_account_starting_equity": epoch.get("starting_equity"),
        "engineering_check_count": len(engineering_checks),
        "engineering_checks": engineering_checks,
        "engineering_blocker_count": len(blockers),
        "engineering_blockers": blockers,
        "real_time_maturity": maturity,
        "real_time_maturity_complete": all(row["state"] in {"complete", "observed"} for row in maturity),
        "operator_service_status": operator.get("status"),
        "forward_shadow_status": forward.get("service_state"),
        "paperops_runtime_owner": owner,
        "public_status_bridge_status": bridge.get("status"),
        "remaining_operator_actions": [
            "Keep the Mac connected to power and network.",
            "Source the optional missing historical datasets listed in the sourcing brief.",
            "Review alerts only when Qadam records a provider, credential, safety, or code repair request.",
        ],
        "boundary": (
            "This certifies unattended paper-only observation, not profitability, a validated edge, "
            "completion of the real-calendar soak, live-capital readiness, or proof credit."
        ),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "simulated_elapsed_time_used": False,
        "authority": authority_flags(),
    }


def validate_unattended_observation_readiness(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("safe_to_leave_running_and_observe") is True and payload.get(
        "engineering_blockers"
    ):
        errors.append("observation_readiness_passed_with_engineering_blockers")
    if payload.get("safe_to_leave_running_and_observe") is True and payload.get(
        "engineering_checks", {}
    ).get("live_capital_disabled") is not True:
        errors.append("observation_readiness_passed_with_live_capital")
    if payload.get("simulated_elapsed_time_used") is not False:
        errors.append("observation_readiness_simulated_elapsed_time")
    if payload.get("paper_order_created_count") != 0 or payload.get("broker_write_count") != 0:
        errors.append("observation_readiness_checker_created_execution_side_effect")
    errors.extend(validate_authority(payload.get("authority", {}), prefix="observation_readiness"))
    return unique_errors(errors)


def build_and_write_unattended_observation_readiness(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    payload = build_unattended_observation_readiness(settings)
    errors = validate_unattended_observation_readiness(payload)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_unattended_observation_readiness_checks",
        "generated_at": now_iso(),
        "status": "passed" if not errors and payload["safe_to_leave_running_and_observe"] else "blocked",
        "safe_to_leave_running_and_observe": payload["safe_to_leave_running_and_observe"],
        "engineering_blocker_count": payload["engineering_blocker_count"],
        "engineering_blockers": payload["engineering_blockers"],
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    store = AtomicArtifactStore(runtime)
    store.write_json(STATUS_ARTIFACT, payload)
    store.write_json(CHECK_ARTIFACT, checks)
    return payload, checks, errors


__all__ = [
    "build_and_write_unattended_observation_readiness",
    "build_unattended_observation_readiness",
    "validate_unattended_observation_readiness",
]
