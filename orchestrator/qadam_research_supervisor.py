"""OR-1 single-instance, resumable supervisor for research-only jobs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import os
from pathlib import Path
import shutil
import signal
import subprocess
from typing import Any, Iterable

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    append_jsonl_durable,
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    unique_errors,
    validate_authority,
)

SCHEMA_VERSION = "qadam_research_supervisor.v1"
PHASE_ID = "OR-1"

STATUS_ARTIFACT = "qadam_research_supervisor_status.json"
HEARTBEAT_ARTIFACT = "qadam_research_supervisor_heartbeat.json"
MANIFEST_ARTIFACT = "qadam_research_job_manifest.jsonl"
EVENTS_ARTIFACT = "qadam_research_job_events.jsonl"
RESUME_ARTIFACT = "qadam_research_resume_state.json"
LEASE_ARTIFACT = "qadam_research_supervisor_lease.json"
CHECK_ARTIFACT = "qadam_research_supervisor_checks.json"
ATOMICITY_CHECK_ARTIFACT = "qadam_research_state_atomicity_checks.json"
RESUME_CHECK_ARTIFACT = "qadam_research_resume_checks.json"
OPERATOR_STATUS_ARTIFACT = "qadam_operator_service_status.json"

LAUNCHD_LABEL = "com.qadam.research-supervisor"
LAUNCHD_TARGET = Path.home() / "Library" / "LaunchAgents" / f"{LAUNCHD_LABEL}.plist"

LONG_LOCK_ARTIFACT = "qadam_long_backtest_lock.json"
LEGACY_STATE_ARTIFACT = "qsase_whole_universe_backfill_backtest_state.json"
LEGACY_MANIFEST_ARTIFACT = "qsase_whole_universe_backfill_backtest_manifest.json"

RESEARCH_JOB_TYPES = {
    "source_acquisition",
    "price_acquisition",
    "normalization",
    "point_in_time_alignment",
    "feature_calculation",
    "backtest_calculation",
    "summary_calculation",
}
FORBIDDEN_JOB_TOKENS = {"broker", "order", "submit", "execution", "paperops"}
TERMINAL_JOB_STATES = {"complete", "unavailable", "cancelled"}
RESUMABLE_JOB_STATES = {"pending", "running", "interrupted", "retryable_failure", "paused"}


def _launchd_schedule_state() -> dict[str, Any]:
    """Inspect the operator-installed schedule without changing OS state."""

    installed = LAUNCHD_TARGET.exists()
    loaded = False
    process_running = False
    if installed:
        try:
            result = subprocess.run(
                ["launchctl", "print", f"gui/{os.getuid()}/{LAUNCHD_LABEL}"],
                check=False,
                capture_output=True,
                text=True,
                timeout=3,
            )
            loaded = result.returncode == 0
            process_running = loaded and "state = running" in result.stdout
        except (FileNotFoundError, subprocess.SubprocessError):
            loaded = False
    return {
        "launchd_label": LAUNCHD_LABEL,
        "target_path": str(LAUNCHD_TARGET),
        "template_installed": installed,
        "schedule_loaded": loaded,
        "worker_process_running_at_probe": process_running,
        "inspection_only": True,
    }


@dataclass(frozen=True, kw_only=True)
class ResearchJob:
    job_id: str
    job_type: str
    source: str | None = None
    provider: str | None = None
    instrument: str | None = None
    date_partition: str
    requested_granularity: str
    retry_class: str = "idempotent_read"
    rate_limit_class: str = "provider_default"
    checksum: str | None = None
    row_count: int = 0
    started_at: str | None = None
    completed_at: str | None = None
    status: str = "pending"
    failure_category: str | None = None
    resume_cursor: str | None = None
    attempt_count: int = 0
    origin: str = "operator_ready_supervisor"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_research_job",
            **asdict(self),
            "authority": authority_flags(),
        }


def stable_job_id(
    *,
    job_type: str,
    source: str | None,
    provider: str | None,
    instrument: str | None,
    date_partition: str,
    requested_granularity: str,
) -> str:
    material = "|".join(
        value or "-"
        for value in (
            job_type,
            source,
            provider,
            instrument,
            date_partition,
            requested_granularity,
        )
    )
    return f"research-job:{hashlib.sha256(material.encode('utf-8')).hexdigest()[:24]}"


def build_job(
    *,
    job_type: str,
    date_partition: str,
    requested_granularity: str,
    source: str | None = None,
    provider: str | None = None,
    instrument: str | None = None,
    status: str = "pending",
) -> ResearchJob:
    return ResearchJob(
        job_id=stable_job_id(
            job_type=job_type,
            source=source,
            provider=provider,
            instrument=instrument,
            date_partition=date_partition,
            requested_granularity=requested_granularity,
        ),
        job_type=job_type,
        source=source,
        provider=provider,
        instrument=instrument,
        date_partition=date_partition,
        requested_granularity=requested_granularity,
        status=status,
    )


def validate_job(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    job_type = str(record.get("job_type") or "")
    if job_type not in RESEARCH_JOB_TYPES:
        errors.append(f"research_job_type_forbidden:{job_type or 'missing'}")
    searchable = " ".join(
        str(record.get(key) or "").lower()
        for key in ("job_type", "source", "provider", "instrument")
    )
    for token in FORBIDDEN_JOB_TOKENS:
        if token in searchable:
            errors.append(f"research_job_execution_token_forbidden:{token}")
    for field in (
        "job_id",
        "date_partition",
        "requested_granularity",
        "retry_class",
        "rate_limit_class",
    ):
        if not str(record.get(field) or "").strip():
            errors.append(f"research_job_field_missing:{field}")
    errors.extend(validate_authority(record.get("authority", {}), prefix="research_job"))
    return unique_errors(errors)


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


class ResearchSupervisor:
    """Owns research job state without owning provider or execution logic."""

    def __init__(self, runtime: Path, *, lease_ttl_seconds: int = 120):
        self.runtime = runtime.resolve()
        self.store = AtomicArtifactStore(self.runtime)
        self.lease_ttl_seconds = lease_ttl_seconds
        self.stop_requested = False
        self._previous_handlers: dict[int, Any] = {}

    def load_jobs(self) -> list[dict[str, Any]]:
        records = read_jsonl(self.runtime / MANIFEST_ARTIFACT)
        deduped: dict[str, dict[str, Any]] = {}
        for record in records:
            if record.get("job_id"):
                deduped[str(record["job_id"])] = record
        return list(deduped.values())

    def write_jobs(self, jobs: Iterable[dict[str, Any]]) -> None:
        records = list(jobs)
        errors = [error for record in records for error in validate_job(record)]
        if errors:
            raise ValueError(",".join(unique_errors(errors)))
        self.store.write_jsonl(MANIFEST_ARTIFACT, records)

    def acquire_lease(self, *, owner_pid: int | None = None) -> tuple[bool, str]:
        pid = owner_pid or os.getpid()
        existing = read_json(self.runtime / LEASE_ARTIFACT)
        existing_pid = int(existing.get("owner_pid") or 0)
        expires_at = _parse_timestamp(existing.get("expires_at"))
        now = datetime.now(timezone.utc)
        if existing.get("status") == "active" and existing_pid != pid:
            if _pid_alive(existing_pid) or (expires_at is not None and expires_at > now):
                return False, "active_lease_exists"
        generated_at = now_iso()
        lease = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_research_supervisor_lease",
            "generated_at": generated_at,
            "status": "active",
            "owner_pid": pid,
            "acquired_at": generated_at,
            "expires_at": (now + timedelta(seconds=self.lease_ttl_seconds)).isoformat(),
            "stale_lease_recovered": bool(existing),
            "authority": authority_flags(),
        }
        self.store.write_json(LEASE_ARTIFACT, lease)
        return True, "lease_acquired"

    def renew_lease(self, *, owner_pid: int | None = None) -> bool:
        pid = owner_pid or os.getpid()
        lease = read_json(self.runtime / LEASE_ARTIFACT)
        if lease.get("status") != "active" or int(lease.get("owner_pid") or 0) != pid:
            return False
        lease["generated_at"] = now_iso()
        lease["expires_at"] = (
            datetime.now(timezone.utc) + timedelta(seconds=self.lease_ttl_seconds)
        ).isoformat()
        self.store.write_json(LEASE_ARTIFACT, lease)
        return True

    def release_lease(self, *, owner_pid: int | None = None, reason: str = "clean_exit") -> bool:
        pid = owner_pid or os.getpid()
        lease = read_json(self.runtime / LEASE_ARTIFACT)
        if int(lease.get("owner_pid") or 0) != pid:
            return False
        lease.update({"generated_at": now_iso(), "status": "released", "release_reason": reason})
        self.store.write_json(LEASE_ARTIFACT, lease)
        return True

    def resource_state(self, *, minimum_free_gb: float = 5.0) -> dict[str, Any]:
        usage = shutil.disk_usage(self.runtime)
        free_gb = usage.free / (1024**3)
        return {
            "disk_total_bytes": usage.total,
            "disk_used_bytes": usage.used,
            "disk_free_bytes": usage.free,
            "disk_free_gb": round(free_gb, 3),
            "disk_pause_required": free_gb < minimum_free_gb,
            "minimum_free_gb": minimum_free_gb,
            "thermal_state": "not_verified",
            "thermal_pause_required": False,
            "backpressure_state": "paused_low_disk" if free_gb < minimum_free_gb else "clear",
        }

    def write_checkpoint(
        self,
        *,
        current_job_id: str | None,
        resume_cursor: str | None,
        reason: str,
    ) -> dict[str, Any]:
        jobs = self.load_jobs()
        completed = sum(record.get("status") in TERMINAL_JOB_STATES for record in jobs)
        state = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_research_resume_state",
            "generated_at": now_iso(),
            "status": "resumable" if current_job_id else "idle_checkpoint",
            "current_job_id": current_job_id,
            "resume_cursor": resume_cursor,
            "checkpoint_reason": reason,
            "completed_job_count": completed,
            "remaining_job_count": len(jobs) - completed,
            "resume_only_incomplete_idempotent_jobs": True,
            "execution_jobs_allowed": False,
            "authority": authority_flags(),
        }
        self.store.write_json(RESUME_ARTIFACT, state)
        return state

    def resumable_jobs(self) -> list[dict[str, Any]]:
        return [
            record
            for record in self.load_jobs()
            if record.get("status") in RESUMABLE_JOB_STATES
            and record.get("retry_class") in {"idempotent_read", "deterministic_calculation"}
            and not validate_job(record)
        ]

    def write_heartbeat(
        self,
        *,
        state: str,
        current_job_id: str | None = None,
        current_phase: str = PHASE_ID,
        service_id: str | None = None,
        processed_units: int = 0,
        elapsed_seconds: float = 0.0,
        last_successful_provider_call_at: str | None = None,
        paperops_watch_only_mode: bool = True,
    ) -> dict[str, Any]:
        jobs = self.load_jobs()
        complete = sum(record.get("status") in TERMINAL_JOB_STATES for record in jobs)
        total = len(jobs)
        throughput = processed_units / elapsed_seconds if elapsed_seconds > 0 else 0.0
        resource = self.resource_state()
        heartbeat = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_research_supervisor_heartbeat",
            "generated_at": now_iso(),
            "status": state,
            "current_phase": current_phase,
            "service_id": service_id,
            "current_job_id": current_job_id,
            "progress": {
                "completed_jobs": complete,
                "total_jobs": total,
                "remaining_jobs": max(total - complete, 0),
                "progress_fraction": round(complete / total, 6) if total else 0.0,
            },
            "throughput_units_per_second": round(throughput, 6),
            "estimated_remaining_seconds": (
                round(max(total - complete, 0) / throughput, 3) if throughput > 0 else None
            ),
            "last_successful_provider_call_at": last_successful_provider_call_at,
            "resource_state": resource,
            "paperops_watch_only_mode": paperops_watch_only_mode,
            "authority": authority_flags(),
        }
        self.store.write_json(HEARTBEAT_ARTIFACT, heartbeat)
        return heartbeat

    def install_signal_handlers(self) -> None:
        def handler(signum: int, _frame: Any) -> None:
            self.stop_requested = True
            self.write_checkpoint(
                current_job_id=read_json(self.runtime / RESUME_ARTIFACT).get("current_job_id"),
                resume_cursor=read_json(self.runtime / RESUME_ARTIFACT).get("resume_cursor"),
                reason=f"signal_{signum}",
            )

        for signum in (signal.SIGTERM, signal.SIGINT):
            self._previous_handlers[signum] = signal.getsignal(signum)
            signal.signal(signum, handler)

    def restore_signal_handlers(self) -> None:
        for signum, previous in self._previous_handlers.items():
            signal.signal(signum, previous)
        self._previous_handlers.clear()


def _bootstrap_jobs(runtime: Path) -> list[dict[str, Any]]:
    existing = read_jsonl(runtime / MANIFEST_ARTIFACT)
    if existing:
        return existing
    legacy = read_json(runtime / LEGACY_MANIFEST_ARTIFACT)
    legacy_jobs = legacy.get("jobs") if isinstance(legacy.get("jobs"), list) else []
    jobs: list[dict[str, Any]] = []
    for record in legacy_jobs:
        label = str(record.get("job_id") or "legacy-calculation")
        job = build_job(
            job_type="summary_calculation",
            source=label,
            provider="local_runtime",
            date_partition="legacy-baseline",
            requested_granularity="artifact",
            status="complete" if record.get("status") == "complete" else "pending",
        ).to_dict()
        job["origin"] = "legacy_manifest_reconciled"
        jobs.append(job)
    if not jobs:
        jobs.append(
            build_job(
                job_type="summary_calculation",
                source="operator-ready-baseline",
                provider="local_runtime",
                date_partition="current",
                requested_granularity="artifact",
            ).to_dict()
        )
    return jobs


def build_and_write_research_supervisor(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    supervisor = ResearchSupervisor(runtime)
    jobs = _bootstrap_jobs(runtime)
    supervisor.write_jobs(jobs)
    launchd = _launchd_schedule_state()
    lock = read_json(runtime / LONG_LOCK_ARTIFACT)
    operator = read_json(runtime / OPERATOR_STATUS_ARTIFACT)
    forward_shadow_service = next(
        (
            row
            for row in operator.get("services", [])
            if isinstance(row, dict) and row.get("service_id") == "forward_shadow"
        ),
        {},
    )
    operator_owns_research = bool(
        lock.get("status") != "active"
        and operator.get("service_running") is True
        and operator.get("release_effective") is True
        and operator.get("liveness", {}).get("process_running") is True
        and forward_shadow_service.get("current_execution_allowed") is True
    )
    readiness_state = (
        "superseded_by_operator_service"
        if operator_owns_research
        else "ready_schedule_loaded"
        if launchd["schedule_loaded"]
        else "ready_not_installed"
    )
    paperops_watch_only_mode = lock.get("status") == "active"
    heartbeat = supervisor.write_heartbeat(
        state=readiness_state,
        paperops_watch_only_mode=paperops_watch_only_mode,
    )
    resume = supervisor.write_checkpoint(
        current_job_id=None,
        resume_cursor=None,
        reason="or1_readiness_check",
    )
    legacy_state = read_json(runtime / LEGACY_STATE_ARTIFACT)
    status = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_research_supervisor_status",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": readiness_state,
        "supervisor_installed": launchd["template_installed"],
        "supervisor_schedule_loaded": launchd["schedule_loaded"],
        "supervisor_running": launchd["worker_process_running_at_probe"],
        "scheduler_owner": (
            "qadam_operator_service" if operator_owns_research else "legacy_research_supervisor"
        ),
        "superseded_by_operator_service": operator_owns_research,
        "launchd_state": launchd,
        "installation_is_operator_action": True,
        "single_instance_lease_enabled": True,
        "atomic_state_enabled": True,
        "sigterm_checkpoint_enabled": True,
        "disk_backpressure_enabled": True,
        "thermal_probe_state": "not_verified",
        "manifest_job_count": len(jobs),
        "resumable_job_count": len(supervisor.resumable_jobs()),
        "lock_state": {
            "active": lock.get("status") == "active",
            "paperops_watch_only_mode": lock.get("paperops_watch_only_mode") is True,
        },
        "reconciled_research_state": {
            "research_lock_active": lock.get("status") == "active",
            "historical_baseline_attempted": bool(legacy_state.get("phase_1_backfill_started")),
            "provider_backfill_complete": False,
            "state_contradiction_hidden": False,
            "interpretation": (
                "The consolidated Qadam operator service owns continuous research and forward-shadow scheduling. "
                "This legacy supervisor remains as a compatibility artifact and cannot launch duplicate work."
                if operator_owns_research
                else "The safety lock remains active. The legacy supervisor may run research-only jobs while PaperOps stays watch-only."
            ),
        },
        "paperops_watch_only_mode": paperops_watch_only_mode,
        "execution_job_types_allowed": False,
        "artifacts": {
            "heartbeat": f"data/runtime/{HEARTBEAT_ARTIFACT}",
            "manifest": f"data/runtime/{MANIFEST_ARTIFACT}",
            "resume": f"data/runtime/{RESUME_ARTIFACT}",
        },
        "authority": authority_flags(),
    }
    AtomicArtifactStore(runtime).write_json(STATUS_ARTIFACT, status)
    errors: list[str] = []
    if not operator_owns_research and status["lock_state"]["active"] is not True:
        errors.append("research_supervisor_without_active_lock_or_operator_owner")
    if not operator_owns_research and status["paperops_watch_only_mode"] is not True:
        errors.append("paperops_not_watch_only_for_legacy_supervisor")
    if heartbeat.get("status") != readiness_state:
        errors.append("supervisor_heartbeat_missing")
    if resume.get("resume_only_incomplete_idempotent_jobs") is not True:
        errors.append("resume_policy_unsafe")
    auxiliary_checks = {
        "atomicity": read_json(runtime / ATOMICITY_CHECK_ARTIFACT),
        "resume": read_json(runtime / RESUME_CHECK_ARTIFACT),
    }
    for label, payload in auxiliary_checks.items():
        if payload.get("status") != "passed":
            errors.append(f"research_supervisor_auxiliary_check_not_passed:{label}")
    errors.extend(error for job in jobs for error in validate_job(job))
    errors.extend(validate_authority(status["authority"], prefix="research_supervisor"))
    errors = unique_errors(errors)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_research_supervisor_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "heartbeat_fresh": _parse_timestamp(heartbeat.get("generated_at")) is not None,
        "manifest_job_count": len(jobs),
        "auxiliary_checks": {
            label: payload.get("status") for label, payload in auxiliary_checks.items()
        },
        "paperops_watch_only_mode": status["paperops_watch_only_mode"],
        "scheduler_owner": status["scheduler_owner"],
        "superseded_by_operator_service": operator_owns_research,
        "broker_write_count": 0,
        "authority": authority_flags(),
    }
    AtomicArtifactStore(runtime).write_json(CHECK_ARTIFACT, checks)
    return status, checks, errors


def append_job_event(runtime: Path, *, event: str, job_id: str | None, detail: str) -> None:
    append_jsonl_durable(
        runtime / EVENTS_ARTIFACT,
        {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_research_job_event",
            "generated_at": now_iso(),
            "event": event,
            "job_id": job_id,
            "detail": detail,
            "authority": authority_flags(),
        },
    )
