"""Phase 0 safety lock for the next-generation Qadam flow.

The lock is a local runtime contract for long historical research runs. When it
is active, PaperOps must remain watch-only: it can report existing state, but it
must not run order-producing work.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
from typing import Any

from orchestrator.config import Settings

SCHEMA_VERSION = 1
LOCK_ARTIFACT = "qadam_long_backtest_lock.json"
LOCK_HISTORY_ARTIFACT = "qadam_long_backtest_lock_history.jsonl"
PHASE0_ARTIFACT = "qadam_next_generation_phase0_safety_lock.json"
PHASE0_EVENTS_ARTIFACT = "qadam_next_generation_phase0_safety_lock_events.jsonl"
DASHBOARD_SUMMARY_ARTIFACT = "qadam_next_generation_backtest_dashboard_summary.json"

LOCK_TYPE = "qadam_next_generation_whole_universe_backfill_backtest"
WATCH_ONLY_REASON = "long historical backfill and backtest safety lock active"

PROCESS_PATTERNS: tuple[tuple[str, str], ...] = (
    ("paperops_autonomous_runner", "scripts/run_paperops_autonomous_pass.py"),
    ("active_paper_trading_runner", "scripts/run_active_paper_trading_automation.py"),
    ("daily_learning_live_runner", "scripts/run_daily_learning_automation.py --live"),
    ("dashboard_deploy_preflight", "scripts/preflight_dashboard_deployment.sh"),
)

FORBIDDEN_TRUE_FLAGS = (
    "paper_order_creation_allowed",
    "paper_order_allowed",
    "broker_write_allowed",
    "live_capital_enabled",
    "proof_credit_allowed",
    "paper_growth_trial_calendar_advance_allowed",
    "simulated_elapsed_time_allowed",
    "telegram_command_path_enabled",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _runtime_dir(settings: Settings | None = None) -> Path:
    active_settings = settings or Settings.from_env()
    path = Path(active_settings.runtime_dir)
    if not path.is_absolute():
        path = _repo_root() / path
    return path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _jsonl_line(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True) + "\n"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_dump(payload), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(_jsonl_line(payload))


def authority_flags() -> dict[str, bool]:
    return {
        "read_only": True,
        "paper_only": True,
        "proposal_first": True,
        "watch_only": True,
        "trade_candidate_creation_allowed": False,
        "risk_approval_allowed": False,
        "execution_allowed": False,
        "paper_order_creation_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
        "paper_growth_trial_calendar_advance_allowed": False,
        "simulated_elapsed_time_allowed": False,
        "telegram_command_path_enabled": False,
    }


def artifact_paths(settings: Settings | None = None) -> dict[str, Path]:
    runtime = _runtime_dir(settings)
    return {
        "lock": runtime / LOCK_ARTIFACT,
        "lock_history": runtime / LOCK_HISTORY_ARTIFACT,
        "phase0": runtime / PHASE0_ARTIFACT,
        "phase0_events": runtime / PHASE0_EVENTS_ARTIFACT,
        "dashboard_summary": runtime / DASHBOARD_SUMMARY_ARTIFACT,
    }


def read_long_backtest_lock(settings: Settings | None = None) -> dict[str, Any]:
    return _read_json(artifact_paths(settings)["lock"])


def is_long_backtest_lock_active(lock: dict[str, Any] | None = None) -> bool:
    payload = lock if isinstance(lock, dict) else read_long_backtest_lock()
    return (
        payload.get("lock_type") == LOCK_TYPE
        and payload.get("status") == "active"
        and payload.get("paperops_autonomous_runner_paused") is True
        and payload.get("paperops_watch_only_mode") is True
    )


def build_long_backtest_lock(
    *,
    settings: Settings | None = None,
    generated_at: str | None = None,
    max_runtime_hours: int = 120,
    reason: str = WATCH_ONLY_REASON,
) -> dict[str, Any]:
    generated = generated_at or _now()
    flags = authority_flags()
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_long_backtest_lock",
        "lock_type": LOCK_TYPE,
        "status": "active",
        "generated_at": generated,
        "started_at": generated,
        "max_runtime_hours": int(max_runtime_hours),
        "paperops_autonomous_runner_paused": True,
        "paperops_watch_only_mode": True,
        "dashboard_deploy_should_pause": True,
        "daily_learning_live_runner_should_pause": True,
        "reason": reason,
        "public_safe": True,
        "release_requires_explicit_operator_action": True,
        "release_log_artifact": f"data/runtime/{LOCK_HISTORY_ARTIFACT}",
        "phase_0_only": True,
        "phase_1_backfill_started": False,
        "next_allowed_action": (
            "Implement Phase 1 only after this lock is visible, PaperOps is "
            "watch-only, and safety probes pass."
        ),
        **flags,
        "authority": flags,
    }


def _process_probe() -> dict[str, Any]:
    try:
        completed = subprocess.run(
            ["ps", "-axo", "pid=,command="],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "status": "not_verified",
            "error": exc.__class__.__name__,
            "running_processes": [],
            "unsafe_running_process_count": 0,
        }
    if completed.returncode != 0:
        return {
            "status": "not_verified",
            "error": "ps_failed",
            "stderr_tail": completed.stderr.strip().splitlines()[-5:],
            "running_processes": [],
            "unsafe_running_process_count": 0,
        }
    current_pid = os.getpid()
    matches: list[dict[str, Any]] = []
    for line in completed.stdout.splitlines():
        text = line.strip()
        if not text:
            continue
        pid_text, _, command = text.partition(" ")
        try:
            pid = int(pid_text)
        except ValueError:
            continue
        if pid == current_pid:
            continue
        for label, pattern in PROCESS_PATTERNS:
            if pattern in command:
                matches.append({"label": label, "pid": pid, "command": command})
    return {
        "status": "ok",
        "running_processes": matches,
        "unsafe_running_process_count": len(matches),
    }


def build_dashboard_summary(lock: dict[str, Any], process_probe: dict[str, Any]) -> dict[str, Any]:
    active = is_long_backtest_lock_active(lock)
    status = "backtest_research_lock_active" if active else "backtest_research_lock_inactive"
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_next_generation_backtest_dashboard_summary",
        "generated_at": _now(),
        "status": status,
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "command_disabled": True,
        "backtest_running_state": status,
        "long_backtest_lock_active": active,
        "paperops_watch_only_mode": bool(lock.get("paperops_watch_only_mode")),
        "phase_1_backfill_started": bool(lock.get("phase_1_backfill_started")),
        "message": (
            "Qadam is paused for a long historical research/backtest lock. "
            "PaperOps can report existing state only; it cannot create orders."
            if active
            else "No long historical research/backtest lock is active."
        ),
        "process_probe_status": process_probe.get("status"),
        "unsafe_running_process_count": process_probe.get("unsafe_running_process_count", 0),
        "authority": authority_flags(),
        "artifact_refs": [
            f"data/runtime/{LOCK_ARTIFACT}",
            f"data/runtime/{PHASE0_ARTIFACT}",
        ],
    }


def validate_long_backtest_lock(lock: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if lock.get("schema_version") != SCHEMA_VERSION:
        errors.append("long_backtest_lock_schema_version_mismatch")
    if lock.get("lock_type") != LOCK_TYPE:
        errors.append("long_backtest_lock_type_mismatch")
    if lock.get("status") != "active":
        errors.append("long_backtest_lock_not_active")
    if lock.get("paperops_autonomous_runner_paused") is not True:
        errors.append("paperops_autonomous_runner_not_paused")
    if lock.get("paperops_watch_only_mode") is not True:
        errors.append("paperops_watch_only_mode_not_enabled")
    if lock.get("phase_1_backfill_started") is not False:
        errors.append("phase_1_backfill_started_during_phase0")
    if lock.get("release_requires_explicit_operator_action") is not True:
        errors.append("lock_release_not_explicit")
    if lock.get("public_safe") is not True:
        errors.append("long_backtest_lock_not_public_safe")
    for key in FORBIDDEN_TRUE_FLAGS:
        if lock.get(key) is not False:
            errors.append(f"long_backtest_lock_forbidden_true:{key}")
    authority = lock.get("authority")
    if not isinstance(authority, dict):
        errors.append("long_backtest_lock_authority_missing")
    else:
        for key in FORBIDDEN_TRUE_FLAGS:
            if authority.get(key) is not False:
                errors.append(f"long_backtest_lock_authority_forbidden_true:{key}")
    return sorted(set(errors))


def build_phase0_status(
    *,
    settings: Settings | None = None,
    max_runtime_hours: int = 120,
    write_lock: bool = True,
) -> dict[str, Any]:
    paths = artifact_paths(settings)
    lock = build_long_backtest_lock(
        settings=settings,
        max_runtime_hours=max_runtime_hours,
    )
    if write_lock:
        _write_json(paths["lock"], lock)
        _append_jsonl(
            paths["lock_history"],
            {
                "generated_at": lock["generated_at"],
                "event_type": "long_backtest_lock_activated",
                "status": lock["status"],
                "paperops_watch_only_mode": lock["paperops_watch_only_mode"],
                "phase_1_backfill_started": False,
                "release_requires_explicit_operator_action": True,
            },
        )
    process_probe = _process_probe()
    dashboard_summary = build_dashboard_summary(lock, process_probe)
    validation_errors = validate_long_backtest_lock(lock)
    if process_probe.get("status") == "ok" and process_probe.get("unsafe_running_process_count", 0):
        validation_errors.append("unsafe_qadam_process_running")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_next_generation_phase0_safety_lock",
        "generated_at": _now(),
        "status": "qadam_next_generation_phase0_ready" if not validation_errors else "qadam_next_generation_phase0_blocked",
        "public_safe": True,
        "read_only": True,
        "paper_only": True,
        "proposal_first": True,
        "phase_0_only": True,
        "phase_1_backfill_started": False,
        "long_backtest_lock_active": is_long_backtest_lock_active(lock),
        "paperops_watch_only_mode": bool(lock.get("paperops_watch_only_mode")),
        "dashboard_backtest_running_state": dashboard_summary["backtest_running_state"],
        "process_probe": process_probe,
        "validation_errors": sorted(set(validation_errors)),
        "validation_error_count": len(set(validation_errors)),
        "safety_probes": {
            "paperops_refuses_order_producing_work_while_locked": is_long_backtest_lock_active(lock),
            "dashboard_safe_backtest_state_exposed": dashboard_summary["public_safe"] is True,
            "lock_release_explicit_and_logged": lock.get("release_requires_explicit_operator_action") is True,
            "phase_1_not_started": lock.get("phase_1_backfill_started") is False,
            "authority_flags_fail_closed": not validate_long_backtest_lock(lock),
        },
        "authority": authority_flags(),
        "artifact_refs": {
            "lock": f"data/runtime/{LOCK_ARTIFACT}",
            "lock_history": f"data/runtime/{LOCK_HISTORY_ARTIFACT}",
            "dashboard_summary": f"data/runtime/{DASHBOARD_SUMMARY_ARTIFACT}",
        },
    }
    _write_json(paths["phase0"], payload)
    _write_json(paths["dashboard_summary"], dashboard_summary)
    _append_jsonl(
        paths["phase0_events"],
        {
            "generated_at": payload["generated_at"],
            "event_type": "qadam_next_generation_phase0_checked",
            "status": payload["status"],
            "long_backtest_lock_active": payload["long_backtest_lock_active"],
            "paperops_watch_only_mode": payload["paperops_watch_only_mode"],
            "validation_error_count": payload["validation_error_count"],
        },
    )
    return payload


def validate_phase0_status(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("phase0_schema_version_mismatch")
    if payload.get("public_safe") is not True:
        errors.append("phase0_not_public_safe")
    if payload.get("read_only") is not True or payload.get("paper_only") is not True:
        errors.append("phase0_boundary_flags_invalid")
    if payload.get("phase_0_only") is not True:
        errors.append("phase0_only_flag_missing")
    if payload.get("phase_1_backfill_started") is not False:
        errors.append("phase1_started_in_phase0")
    if payload.get("long_backtest_lock_active") is not True:
        errors.append("long_backtest_lock_not_active")
    if payload.get("paperops_watch_only_mode") is not True:
        errors.append("paperops_watch_only_mode_not_enabled")
    if payload.get("validation_error_count") != 0:
        errors.extend(str(error) for error in payload.get("validation_errors", []))
    authority = payload.get("authority")
    if not isinstance(authority, dict):
        errors.append("phase0_authority_missing")
    else:
        for key in FORBIDDEN_TRUE_FLAGS:
            if authority.get(key) is not False:
                errors.append(f"phase0_authority_forbidden_true:{key}")
    return sorted(set(errors))


def validate_negative_phase0_probes() -> list[str]:
    errors: list[str] = []
    base = build_long_backtest_lock()
    broker_probe = {**base, "broker_write_allowed": True}
    if not any("broker_write_allowed" in error for error in validate_long_backtest_lock(broker_probe)):
        errors.append("negative_probe_failed_for_broker_write_allowed")
    order_probe = {**base, "paper_order_allowed": True}
    if not any("paper_order_allowed" in error for error in validate_long_backtest_lock(order_probe)):
        errors.append("negative_probe_failed_for_paper_order_allowed")
    live_probe = {**base, "live_capital_enabled": True}
    if not any("live_capital_enabled" in error for error in validate_long_backtest_lock(live_probe)):
        errors.append("negative_probe_failed_for_live_capital_enabled")
    phase_probe = {**base, "phase_1_backfill_started": True}
    if "phase_1_backfill_started_during_phase0" not in validate_long_backtest_lock(phase_probe):
        errors.append("negative_probe_failed_for_phase1_started")
    return errors
