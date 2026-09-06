"""Fast, independent watchdog for Qadam's bounded self-healing loop.

The watchdog does not run research or trading work. It verifies recovery
coverage, distinguishes queued or active healing from a stall, and wakes the
existing singleton operator or reliability critic when a safe repair is due.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any, Callable

from orchestrator.config import Settings
from orchestrator.runtime.launchd import launchd_state
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    append_jsonl_durable,
    atomic_write_text,
    authority_flags,
    now_iso,
    read_json,
    runtime_dir,
    validate_authority,
)
from orchestrator.qadam_operator_service import (
    FULL_HEAL_REQUEST_ARTIFACT,
    FULL_HEAL_REQUEST_MAX_AGE_SECONDS,
    LAUNCHD_LABEL as OPERATOR_LAUNCHD_LABEL,
    LAUNCHD_TARGET as OPERATOR_LAUNCHD_TARGET,
    LAUNCHD_TEMPLATE as OPERATOR_LAUNCHD_TEMPLATE,
    SERVICE_DEFINITIONS,
    WORKERS_ARTIFACT,
    build_and_write_recovery_coverage,
    operator_service_contract_hash,
)
from orchestrator.qadam_reliability_critic import (
    LAUNCHD_LABEL as CRITIC_LAUNCHD_LABEL,
    LAUNCHD_TARGET as CRITIC_LAUNCHD_TARGET,
    LAUNCHD_TEMPLATE as CRITIC_LAUNCHD_TEMPLATE,
    build_reliability_snapshot,
    classify_reliability_snapshot,
    installed_template_matches,
)

SCHEMA_VERSION = "qadam_reliability_watchdog.v1"
STATUS_ARTIFACT = "qadam_reliability_watchdog_status.json"
HISTORY_ARTIFACT = "qadam_reliability_watchdog_history.jsonl"
CHECK_ARTIFACT = "qadam_reliability_watchdog_checks.json"
LAUNCHD_LABEL = "com.qadam.reliability-watchdog"
LAUNCHD_TEMPLATE = ROOT / "ops" / "launchd" / f"{LAUNCHD_LABEL}.plist.template"
LAUNCHD_TARGET = Path.home() / "Library" / "LaunchAgents" / f"{LAUNCHD_LABEL}.plist"
CADENCE_SECONDS = 60
STATUS_MAX_AGE_SECONDS = 3 * CADENCE_SECONDS
REQUEST_QUEUE_MAX_AGE_SECONDS = 45 * 60
REQUEST_PROGRESS_GRACE_SECONDS = 10 * 60
ACTION_COOLDOWN_SECONDS = 10 * 60
MAX_HISTORY_BYTES = 8_000_000
RETAINED_HISTORY_RECORDS = 1_000

CommandRunner = Callable[[tuple[str, ...], int], dict[str, Any]]


def _parse_timestamp(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _age_seconds(reference: datetime, value: Any) -> float | None:
    parsed = _parse_timestamp(value)
    if parsed is None:
        return None
    return max(0.0, (reference - parsed).total_seconds())


def _process_alive(value: Any) -> bool:
    try:
        pid = int(value or 0)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except (OSError, ValueError):
        return False
    return True


def _default_command_runner(command: tuple[str, ...], timeout: int) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            list(command),
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env={
                **os.environ,
                "QADAM_OPERATOR_SAFETY_MODE": "paper_only",
                "QADAM_LIVE_CAPITAL_ENABLED": "false",
            },
        )
        return {
            "returncode": int(completed.returncode),
            "stdout": completed.stdout,
            "stderr": completed.stderr[-1200:],
            "duration_seconds": round(time.monotonic() - started, 6),
        }
    except (OSError, subprocess.TimeoutExpired) as error:
        return {
            "returncode": 124 if isinstance(error, subprocess.TimeoutExpired) else 127,
            "stdout": "",
            "stderr": error.__class__.__name__,
            "duration_seconds": round(time.monotonic() - started, 6),
        }


def _launchd_state(label: str, runner: CommandRunner) -> dict[str, Any]:
    result = runner(("launchctl", "print", f"gui/{os.getuid()}/{label}"), 15)
    return launchd_state(label, result)


def _active_workers(runtime: Path) -> list[dict[str, Any]]:
    payload = read_json(runtime / WORKERS_ARTIFACT)
    workers = payload.get("workers") if isinstance(payload.get("workers"), dict) else {}
    return [
        {
            "service_id": str(service_id),
            "pid": record.get("pid"),
            "started_at": record.get("started_at"),
        }
        for service_id, record in workers.items()
        if isinstance(record, dict)
        and record.get("state") == "running"
        and _process_alive(record.get("pid"))
    ]


def _request_progress_state(runtime: Path, reference: datetime) -> dict[str, Any]:
    request = read_json(runtime / FULL_HEAL_REQUEST_ARTIFACT)
    status = str(request.get("status") or "none")
    requested_state = status in {"requested", "in_progress"}
    age = _age_seconds(reference, request.get("generated_at")) if requested_state else None
    contract_matches = bool(
        request.get("operator_service_contract_hash") == operator_service_contract_hash()
    )
    active = bool(
        requested_state
        and contract_matches
        and age is not None
        and age <= FULL_HEAL_REQUEST_MAX_AGE_SECONDS
    )
    progress_age = _age_seconds(
        reference,
        request.get("progress_at") or request.get("accepted_at") or request.get("generated_at"),
    ) if active else None
    current_service_ids = [str(value) for value in list(request.get("current_service_ids") or [])]
    definitions = {definition.service_id: definition for definition in SERVICE_DEFINITIONS}
    try:
        declared_step_timeout = max(0, int(request.get("current_step_timeout_seconds") or 0))
    except (TypeError, ValueError):
        declared_step_timeout = 0
    current_timeout = declared_step_timeout or sum(
        definitions[service_id].timeout_seconds
        * max(1, len(definitions[service_id].command_sequence))
        for service_id in current_service_ids
        if service_id in definitions
    )
    allowed_progress_age = max(
        REQUEST_QUEUE_MAX_AGE_SECONDS,
        current_timeout + REQUEST_PROGRESS_GRACE_SECONDS,
    )
    stalled = bool(
        active
        and (
            (status == "requested" and age is not None and age > REQUEST_QUEUE_MAX_AGE_SECONDS)
            or (
                status == "in_progress"
                and progress_age is not None
                and progress_age > allowed_progress_age
            )
        )
    )
    return {
        "request_id": request.get("request_id"),
        "status": status,
        "active": active,
        "requested_state": requested_state,
        "contract_matches": contract_matches,
        "obsolete": requested_state and not active,
        "age_seconds": age,
        "progress_age_seconds": progress_age,
        "allowed_progress_age_seconds": allowed_progress_age,
        "current_step_timeout_seconds": current_timeout,
        "phase": request.get("phase"),
        "current_service_ids": current_service_ids,
        "completed_service_ids": list(request.get("completed_service_ids") or []),
        "owner_pid": request.get("owner_pid"),
        "owner_process_alive": _process_alive(request.get("owner_pid")),
        "stalled": stalled,
    }


def _cooldown_active(
    prior: dict[str, Any], reference: datetime, action_type: str
) -> bool:
    action_times = prior.get("last_action_at_by_type")
    if isinstance(action_times, dict):
        timestamp = action_times.get(action_type)
    else:
        # Preserve old cooldowns conservatively until the first typed observation.
        timestamp = prior.get("last_action_at")
    age = _age_seconds(reference, timestamp)
    return age is not None and age < ACTION_COOLDOWN_SECONDS


def _bounded_history_append(path: Path, payload: dict[str, Any]) -> None:
    append_jsonl_durable(path, payload)
    try:
        if path.stat().st_size <= MAX_HISTORY_BYTES:
            return
    except OSError:
        return
    rows = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()[-RETAINED_HISTORY_RECORDS:]
    except OSError:
        return
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    atomic_write_text(
        path,
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
    )


def _kickstart(
    label: str,
    *,
    replace_running: bool,
    runner: CommandRunner,
) -> dict[str, Any]:
    command = (
        ("launchctl", "kickstart", "-k", f"gui/{os.getuid()}/{label}")
        if replace_running
        else ("launchctl", "kickstart", f"gui/{os.getuid()}/{label}")
    )
    result = runner(command, 30)
    return {
        "action_type": "restart_operator_owner"
        if label == OPERATOR_LAUNCHD_LABEL
        else "wake_reliability_critic",
        "label": label,
        "status": "completed" if result.get("returncode") == 0 else "failed",
        "returncode": result.get("returncode"),
        "stderr": str(result.get("stderr") or "")[-400:],
    }


def validate_reliability_watchdog_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("watchdog_schema_invalid")
    if payload.get("artifact_type") != "qadam_reliability_watchdog_status":
        errors.append("watchdog_artifact_type_invalid")
    if payload.get("status") not in {"passed", "recovering", "blocked"}:
        errors.append("watchdog_status_invalid")
    if int(payload.get("paper_order_created_count") or 0) != 0:
        errors.append("watchdog_paper_order_forbidden")
    if int(payload.get("broker_write_count") or 0) != 0:
        errors.append("watchdog_broker_write_forbidden")
    for action in list(payload.get("actions") or []):
        if not isinstance(action, dict) or action.get("action_type") not in {
            "restart_operator_owner",
            "wake_reliability_critic",
        }:
            errors.append("watchdog_action_forbidden")
    errors.extend(
        validate_authority(payload.get("authority") or {}, prefix="watchdog_authority")
    )
    return sorted(set(errors))


def run_reliability_watchdog(
    settings: Settings | None = None,
    *,
    repair: bool = True,
    observed_at: str | None = None,
    command_runner: CommandRunner | None = None,
) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    execute = command_runner or _default_command_runner
    observed_at = observed_at or now_iso()
    reference = _parse_timestamp(observed_at) or datetime.now(timezone.utc)
    coverage = build_and_write_recovery_coverage(settings)
    snapshot = build_reliability_snapshot(
        settings,
        observed_at=observed_at,
        command_runner=execute,
    )
    classification = classify_reliability_snapshot(snapshot)
    operator_job = _launchd_state(OPERATOR_LAUNCHD_LABEL, execute)
    critic_job = _launchd_state(CRITIC_LAUNCHD_LABEL, execute)
    watchdog_job = _launchd_state(LAUNCHD_LABEL, execute)
    request = _request_progress_state(runtime, reference)
    workers = _active_workers(runtime)
    prior = read_json(runtime / STATUS_ARTIFACT)
    cooldown = _cooldown_active(prior, reference, "restart_operator_owner")
    critic_cooldown = _cooldown_active(prior, reference, "wake_reliability_critic")
    operator = snapshot.get("operator") if isinstance(snapshot.get("operator"), dict) else {}
    operator_available = bool(
        operator_job.get("loaded")
        and operator.get("service_running") is True
        and operator.get("lease_process_alive") is True
        and operator.get("lease_age_seconds") is not None
        and float(operator.get("lease_age_seconds")) <= 3 * 60
    )
    actions: list[dict[str, Any]] = []
    blockers: list[str] = []
    operating_state = "monitoring"

    installation_valid = bool(
        OPERATOR_LAUNCHD_TARGET.exists()
        and CRITIC_LAUNCHD_TARGET.exists()
        and LAUNCHD_TARGET.exists()
        and installed_template_matches(OPERATOR_LAUNCHD_TEMPLATE, OPERATOR_LAUNCHD_TARGET)
        and installed_template_matches(CRITIC_LAUNCHD_TEMPLATE, CRITIC_LAUNCHD_TARGET)
        and installed_template_matches(LAUNCHD_TEMPLATE, LAUNCHD_TARGET)
    )
    if coverage.get("status") != "passed":
        blockers.append("recovery_coverage_incomplete")
        operating_state = "recovery_contract_blocked"
    elif not installation_valid:
        blockers.append("operator_or_critic_launchd_contract_invalid")
        operating_state = "installation_review_required"
    elif not all(job.get("state_known") for job in (operator_job, critic_job, watchdog_job)):
        blockers.append("launchd_process_state_unknown")
        operating_state = "diagnostic_retry_required"
    elif request.get("active"):
        worker_active = bool(workers)
        owner_alive = request.get("owner_process_alive") is True
        queued_without_owner = request.get("status") == "requested" and not operator_available
        stopped_or_stalled_owner = bool(
            request.get("status") == "in_progress"
            and not worker_active
            and (not owner_alive or request.get("stalled"))
        )
        stalled_queue = bool(
            request.get("status") == "requested" and request.get("stalled")
        )
        if (queued_without_owner or stopped_or_stalled_owner or stalled_queue) and not worker_active:
            operating_state = "full_heal_restart_required"
            if not cooldown and repair:
                actions.append(
                    _kickstart(
                        OPERATOR_LAUNCHD_LABEL,
                        replace_running=True,
                        runner=execute,
                    )
                )
            elif cooldown:
                operating_state = "full_heal_restart_cooldown"
        elif worker_active and (request.get("stalled") or not owner_alive):
            operating_state = "full_heal_waiting_for_active_worker"
        elif request.get("status") == "requested":
            operating_state = "full_heal_queued"
        else:
            operating_state = "full_heal_in_progress"
    elif not operator_available:
        operating_state = "operator_restart_required"
        if not cooldown and repair:
            actions.append(
                _kickstart(
                    OPERATOR_LAUNCHD_LABEL,
                    replace_running=True,
                    runner=execute,
                )
            )
        elif cooldown:
            operating_state = "operator_restart_cooldown"
    elif classification.get("healthy") is not True:
        if classification.get("state") == "pipeline_degraded_repairable":
            operating_state = "critic_wake_required"
            if not critic_job.get("running") and not critic_cooldown and repair:
                actions.append(
                    _kickstart(
                        CRITIC_LAUNCHD_LABEL,
                        replace_running=False,
                        runner=execute,
                    )
                )
            elif critic_job.get("running"):
                operating_state = "critic_repair_in_progress"
            elif critic_cooldown:
                operating_state = "critic_wake_cooldown"
        else:
            operating_state = "operator_review_required"
            blockers.extend(
                str(row.get("code"))
                for row in list(classification.get("blockers") or [])
                if isinstance(row, dict) and row.get("code")
            )

    action_failures = [action for action in actions if action.get("status") != "completed"]
    if action_failures:
        blockers.append("watchdog_runtime_action_failed")
    recovering = bool(
        actions
        or request.get("active")
        or operating_state
        in {
            "critic_repair_in_progress",
            "critic_wake_required",
            "full_heal_waiting_for_active_worker",
            "full_heal_restart_required",
            "operator_restart_required",
            "operator_restart_cooldown",
            "full_heal_restart_cooldown",
            "critic_wake_cooldown",
        }
    )
    status = "blocked" if blockers or coverage.get("status") != "passed" else (
        "recovering" if recovering else "passed"
    )
    last_action_at = observed_at if actions else prior.get("last_action_at")
    prior_times = prior.get("last_action_at_by_type")
    action_times = dict(prior_times) if isinstance(prior_times, dict) else {
        key: prior.get("last_action_at")
        for key in ("restart_operator_owner", "wake_reliability_critic")
    }
    for action in actions:
        action_times[action["action_type"]] = observed_at
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_reliability_watchdog_status",
        "generated_at": observed_at,
        "status": status,
        "operating_state": operating_state,
        "repair_enabled": repair,
        "recovery_coverage_status": coverage.get("status"),
        "registered_service_count": coverage.get("registered_service_count"),
        "covered_service_count": coverage.get("covered_service_count"),
        "operator": {
            "available": operator_available,
            "launchd": operator_job,
            "lease_age_seconds": operator.get("lease_age_seconds"),
            "lease_process_alive": operator.get("lease_process_alive"),
        },
        "critic": {
            "launchd": critic_job,
            "runtime_classification": classification.get("state"),
            "runtime_healthy": classification.get("healthy") is True,
        },
        "automation": {
            "cadence_seconds": CADENCE_SECONDS,
            "launchd": watchdog_job,
            "installed": LAUNCHD_TARGET.exists(),
            "installed_template_matches": installed_template_matches(
                LAUNCHD_TEMPLATE,
                LAUNCHD_TARGET,
            ),
        },
        "full_heal_request": request,
        "active_workers": workers,
        "actions": actions,
        "last_action_at": last_action_at,
        "last_action_at_by_type": action_times,
        "action_cooldown_seconds": ACTION_COOLDOWN_SECONDS,
        "blockers": sorted(set(blockers)),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    errors = validate_reliability_watchdog_payload(payload)
    if errors:
        payload["status"] = "blocked"
        payload["blockers"] = sorted(set(payload["blockers"] + errors))
    store = AtomicArtifactStore(runtime)
    store.write_json(STATUS_ARTIFACT, payload)
    _bounded_history_append(runtime / HISTORY_ARTIFACT, payload)
    return payload, errors
