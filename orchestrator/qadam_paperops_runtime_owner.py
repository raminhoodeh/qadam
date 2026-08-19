"""Resolve the active owner of Qadam's canonical PaperOps cadence.

Legacy PaperOps contracts expected a Codex hourly automation. The current
runtime delegates the same canonical wrapper through the local operator
service. This adapter recognizes that owner only when the released clean paper
epoch and every paper-only boundary agree; otherwise it fails closed.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from orchestrator.config import Settings


CANONICAL_WRAPPER = "scripts/run_paperops_autonomous_pass.py"
OPERATOR_COMMAND = [".venv/bin/python", CANONICAL_WRAPPER]
EXPERIMENTAL_RELEASE_STATUS = "experimental_paper_release_effective"
EXPERIMENTAL_EPOCH_KIND = "clean_experimental_operator_epoch"
EXPERIMENTAL_LOCK_RELEASE_MODE = (
    "explicit_operator_approved_experimental_paper_epoch"
)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _guarded_service(status: dict[str, Any]) -> dict[str, Any]:
    for service in status.get("services") or []:
        if isinstance(service, dict) and service.get("service_id") == "guarded_paperops":
            return service
    return {}


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def paperops_runtime_owner_status(
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    runtime = Path(settings.runtime_dir)
    release = _read_json(runtime / "qadam_experimental_paper_release_readiness.json")
    epoch = _read_json(runtime / "current_paper_epoch.json")
    lock = _read_json(runtime / "qadam_long_backtest_lock.json")
    service_status = _read_json(runtime / "qadam_operator_service_status.json")
    service_lease = _read_json(runtime / "qadam_operator_service_lease.json")
    guarded = _guarded_service(service_status)

    lease_pid = int(service_lease.get("owner_pid") or 0)
    projected_pid = int(
        service_status.get("single_instance", {}).get("owner_pid") or 0
    )
    lease_expires_at = _parse_timestamp(service_lease.get("expires_at"))
    lease_acquired_at = _parse_timestamp(service_lease.get("acquired_at"))
    status_generated_at = _parse_timestamp(service_status.get("generated_at"))
    lease_current = bool(
        service_lease.get("status") == "active"
        and lease_pid == projected_pid
        and lease_pid > 0
        and _pid_alive(lease_pid)
        and lease_expires_at is not None
        and lease_expires_at > datetime.now(timezone.utc)
        and lease_acquired_at is not None
        and status_generated_at is not None
        and status_generated_at >= lease_acquired_at
    )

    release_epoch_id = str(release.get("paper_epoch_id") or "")
    current_epoch_id = str(epoch.get("paper_epoch_id") or "")
    checks = {
        "paper_mode": settings.mode == "paper",
        "live_capital_disabled": settings.live_capital_enabled is False,
        "release_effective": (
            release.get("status") == EXPERIMENTAL_RELEASE_STATUS
            and release.get("experimental_paper_release_effective") is True
            and release.get("experimental_paper_release_ready") is True
            and not (release.get("blockers") or [])
        ),
        "release_wrapper_exact": release.get("canonical_wrapper") == CANONICAL_WRAPPER,
        "clean_epoch_active": (
            epoch.get("paper_epoch_kind") == EXPERIMENTAL_EPOCH_KIND
            and epoch.get("paper_growth_trial_calendar_started") is True
            and epoch.get("paper_growth_trial_state") == "active_real_calendar"
            and epoch.get("simulated_elapsed_time") is False
            and epoch.get("paper_growth_trial_calendar_backfilled") is False
        ),
        "epoch_binding_exact": bool(current_epoch_id)
        and current_epoch_id == release_epoch_id,
        "research_lock_released": (
            lock.get("status") == "released"
            and lock.get("paperops_watch_only_mode") is False
            and lock.get("release_mode") == EXPERIMENTAL_LOCK_RELEASE_MODE
            and lock.get("release_approval_epoch_id") == current_epoch_id
        ),
        "operator_service_running": (
            service_status.get("service_installed") is True
            and service_status.get("service_running") is True
            and service_status.get("release_effective") is True
            and service_status.get("paperops_watch_only") is False
            and service_status.get("liveness", {}).get("process_running") is True
        ),
        "operator_lease_current": lease_current,
        "operator_wrapper_exact": guarded.get("command_sequence") == [OPERATOR_COMMAND],
        "operator_route_guarded": (
            guarded.get("ownership") == "canonical_paperops_wrapper_only"
            and guarded.get("safety_mode") == "guarded_alpaca_paper_wrapper_only"
            and guarded.get("paperops_dependency") is True
            and guarded.get("paperops_watch_only") is False
            and guarded.get("current_execution_allowed") is True
            and guarded.get("live_capital_enabled") is False
        ),
        "operator_authority_safe": (
            service_status.get("authority", {}).get("paper_only") is True
            and service_status.get("authority", {}).get("live_capital_enabled") is False
            and service_status.get("authority", {}).get("live_broker_endpoint_allowed")
            is False
            and service_status.get("direct_broker_client_import_allowed") is False
        ),
    }
    blockers = sorted(key for key, passed in checks.items() if not passed)
    active = not blockers
    command_text = " ".join(OPERATOR_COMMAND)
    return {
        "owner": "qadam_operator_service" if active else "none",
        "status": "active" if active else "blocked",
        "active": active,
        "cadence_compatible": active,
        "cwd_bound": active,
        "guardrails_bound": active,
        "canonical_wrapper": CANONICAL_WRAPPER,
        "command": OPERATOR_COMMAND,
        "command_digest": hashlib.sha256(command_text.encode("utf-8")).hexdigest(),
        "cadence_seconds": guarded.get("cadence_seconds"),
        "current_state": guarded.get("current_state", "missing"),
        "checks": checks,
        "blockers": blockers,
    }


def operator_service_automation_projection(
    settings: Settings | None = None,
) -> dict[str, Any] | None:
    owner = paperops_runtime_owner_status(settings)
    if owner.get("active") is not True:
        return None
    cadence_seconds = int(owner.get("cadence_seconds") or 3600)
    return {
        "automation_id": "qadam-operator-service",
        "automation_name": "Qadam Operator Service",
        "automation_status": "ACTIVE",
        "automation_rrule": f"EVENT_DRIVEN;MAX_INTERVAL={cadence_seconds}S",
        "automation_kind": "operator_service",
        "automation_transport": "launchd",
        "automation_active": True,
        # Legacy consumers interpret this as an at-least-hourly cadence check.
        "automation_hourly": cadence_seconds <= 3600,
        "automation_cwd_bound": True,
        "automation_prompt_active_trade_bound": True,
        "automation_prompt_paperops_bound": True,
        "automation_prompt_digest": owner["command_digest"],
        "automation_required_command_count": 1,
        "automation_present_command_count": 1,
        "automation_missing_commands": [],
        "automation_required_guardrail_count": 1,
        "automation_present_guardrail_count": 1,
        "automation_missing_guardrails": [],
    }
