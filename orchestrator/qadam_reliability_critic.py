"""Independent, bounded reliability critic for Qadam's unattended operator.

The critic observes the running system from outside the operator process. It can
repeat known-safe runtime work, but it cannot write trading decisions, call
PaperOps, change policy, edit code, touch secrets, or enable live capital.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import time
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_market_session_truth import expected_market_session_phase
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    append_jsonl_durable,
    authority_flags,
    now_iso,
    read_json,
    runtime_dir,
    sha256_json,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_operator_service import (
    CIRCUIT_BREAKERS_ARTIFACT,
    LEASE_ARTIFACT,
    MAINTENANCE_ARTIFACT,
    OperatorMaintenanceLock,
    REPAIR_QUEUE_ARTIFACT,
    SERVICE_DEFINITIONS,
    STATUS_ARTIFACT as OPERATOR_STATUS_ARTIFACT,
    repair_operator_service_circuit,
)
from orchestrator.qadam_self_healing_supervisor import (
    STATUS_ARTIFACT as SELF_HEALING_STATUS_ARTIFACT,
    build_and_write_self_healing_state,
)

SCHEMA_VERSION = "qadam_reliability_critic.v1"
STATUS_ARTIFACT = "qadam_reliability_critic_status.json"
HISTORY_ARTIFACT = "qadam_reliability_critic_history.jsonl"
REPAIR_PACKET_ARTIFACT = "qadam_reliability_critic_repair_packet.json"
CHECK_ARTIFACT = "qadam_reliability_critic_checks.json"
EVENTS_ARTIFACT = "qadam_reliability_critic_events.jsonl"

LAUNCHD_LABEL = "com.qadam.reliability-critic"
LAUNCHD_TEMPLATE = ROOT / "ops" / "launchd" / f"{LAUNCHD_LABEL}.plist.template"
LAUNCHD_TARGET = Path.home() / "Library" / "LaunchAgents" / f"{LAUNCHD_LABEL}.plist"
OPERATOR_LAUNCHD_LABEL = "com.qadam.operator"
OPERATOR_LAUNCHD_TARGET = (
    Path.home() / "Library" / "LaunchAgents" / f"{OPERATOR_LAUNCHD_LABEL}.plist"
)

CADENCE_SECONDS = 3 * 60 * 60
STATUS_MAX_AGE_SECONDS = 30 * 60
LEASE_MAX_AGE_SECONDS = 3 * 60
PAPEROPS_MAX_AGE_SECONDS = 60 * 60
CRITIC_MAX_AGE_SECONDS = CADENCE_SECONDS + 30 * 60
SAFE_RETRY_CLASSES = {
    "idempotent_read",
    "deterministic_calculation",
    "interrupted_resumable_job",
}
PROHIBITED_FAILURE_CLASSES = {
    "safety_violation",
    "credential_operator_action",
    "disk_resource_pressure",
    "research_integrity_hold",
}
HEALTHY_STATES = {
    "healthy_idle_explained",
    "healthy_observing",
    "healthy_actionable",
    "healthy_actionable_waiting_market_session",
}
ALLOWED_ACTIONS = {
    "restart_operator_owner",
    "repair_safe_runtime_circuit",
    "refresh_read_only_projections",
}


CommandRunner = Callable[[tuple[str, ...], int], dict[str, Any]]
SnapshotReader = Callable[[], dict[str, Any]]


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


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


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


def _critic_authority() -> dict[str, bool | int]:
    return {
        **authority_flags(),
        "autonomous_code_edit_allowed": False,
        "risk_threshold_mutation_allowed": False,
        "strategy_admission_allowed": False,
        "paperops_invocation_allowed": False,
        "operator_restart_allowed": True,
        "safe_runtime_revalidation_allowed": True,
    }


def _default_command_runner(command: tuple[str, ...], timeout: int) -> dict[str, Any]:
    started = time.monotonic()
    environment = os.environ.copy()
    environment.update(
        {
            "QADAM_RELIABILITY_CRITIC": "1",
            "QADAM_OPERATOR_SAFETY_MODE": "paper_only",
            "QADAM_LIVE_CAPITAL_ENABLED": "false",
        }
    )
    try:
        completed = subprocess.run(
            list(command),
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "returncode": int(completed.returncode),
            "stdout": completed.stdout[-1200:],
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


def launchd_job_state(
    label: str,
    *,
    runner: CommandRunner | None = None,
) -> dict[str, Any]:
    execute = runner or _default_command_runner
    result = execute(("launchctl", "print", f"gui/{os.getuid()}/{label}"), 15)
    return {
        "label": label,
        "loaded": result.get("returncode") == 0,
        "probe_returncode": result.get("returncode"),
    }


def installed_template_matches(template: Path, target: Path) -> bool:
    if not template.exists() or not target.exists():
        return False
    expected = template.read_text(encoding="utf-8").replace("__QADAM_ROOT__", str(ROOT))
    try:
        actual = target.read_text(encoding="utf-8")
    except OSError:
        return False
    return actual == expected


def _database_snapshot(runtime: Path) -> dict[str, Any]:
    database = runtime / "qadam-control-plane.sqlite3"
    if not database.exists():
        return {
            "present": False,
            "unresolved_repair_request_count": 0,
            "latest_reconciliation": {},
            "latest_liveness": {},
            "current_handoff_count": 0,
        }
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True, timeout=10.0)
    connection.row_factory = sqlite3.Row
    try:
        unresolved = connection.execute(
            "SELECT COUNT(*) AS count FROM repair_requests "
            "WHERE lower(status) NOT IN ('closed','completed','resolved','dismissed')"
        ).fetchone()
        reconciliation = connection.execute(
            "SELECT phase,status,blocker_count,created_at FROM reconciliation_runs "
            "ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        liveness = connection.execute(
            "SELECT status,setup_count,advanced_count,created_at FROM liveness_cycles "
            "ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        handoffs = connection.execute(
            "SELECT COUNT(*) AS count FROM current_handoffs"
        ).fetchone()
        return {
            "present": True,
            "unresolved_repair_request_count": int(unresolved["count"] if unresolved else 0),
            "latest_reconciliation": dict(reconciliation) if reconciliation else {},
            "latest_liveness": dict(liveness) if liveness else {},
            "current_handoff_count": int(handoffs["count"] if handoffs else 0),
        }
    except sqlite3.Error as error:
        return {
            "present": True,
            "read_error": error.__class__.__name__,
            "unresolved_repair_request_count": 0,
            "latest_reconciliation": {},
            "latest_liveness": {},
            "current_handoff_count": 0,
        }
    finally:
        connection.close()


def _paperops_snapshot(runtime: Path, reference: datetime) -> dict[str, Any]:
    summary = read_json(runtime / "paperops_autonomous_pass_summary.json")
    paper_runtime = _safe_dict(summary.get("paper_runtime"))
    states = _safe_dict(summary.get("states"))
    control = _safe_dict(summary.get("canonical_paper_control"))
    handoff = _safe_dict(summary.get("router_v3_handoff_boundary"))
    return {
        "present": bool(summary),
        "generated_at": summary.get("generated_at"),
        "age_seconds": _age_seconds(reference, summary.get("generated_at")),
        "status": summary.get("status"),
        "blockers": _safe_list(summary.get("blockers")),
        "paper_cycle_state": states.get("paper_ops_cycle_state"),
        "paper_live_certification_state": states.get("paper_live_certification_state"),
        "canonical_control_status": control.get("status"),
        "canonical_control_blockers": _safe_list(control.get("blockers")),
        "fresh_eligible_submit_count": int(
            paper_runtime.get("fresh_eligible_submit_count") or 0
        ),
        "submitted_paper_order_count": int(
            paper_runtime.get("submitted_paper_order_count") or 0
        ),
        "duplicate_submit_count": int(paper_runtime.get("duplicate_submit_count") or 0),
        "accepted_handoff_count": int(handoff.get("accepted_handoff_count") or 0),
        "new_paper_submission_allowed": handoff.get("new_paper_submission_allowed") is True,
        "pre_wrapper_persistence_status": handoff.get("pre_wrapper_persistence_status"),
        "post_wrapper_reconciliation_status": handoff.get(
            "post_wrapper_reconciliation_status"
        ),
    }


def build_reliability_snapshot(
    settings: Settings | None = None,
    *,
    observed_at: str | None = None,
    command_runner: CommandRunner | None = None,
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    observed_at = observed_at or now_iso()
    reference = _parse_timestamp(observed_at) or datetime.now(timezone.utc)
    operator = read_json(runtime / OPERATOR_STATUS_ARTIFACT)
    lease = read_json(runtime / LEASE_ARTIFACT)
    repair_queue = read_json(runtime / REPAIR_QUEUE_ARTIFACT)
    circuits = read_json(runtime / CIRCUIT_BREAKERS_ARTIFACT)
    self_healing = read_json(runtime / SELF_HEALING_STATUS_ARTIFACT)
    router = read_json(runtime / "qadam_router_v3_why_not_trading_now.json")
    market_truth = read_json(runtime / "qadam_market_clock_truth.json")
    critic_launchd = launchd_job_state(LAUNCHD_LABEL, runner=command_runner)
    operator_launchd = launchd_job_state(OPERATOR_LAUNCHD_LABEL, runner=command_runner)
    service_records = {
        str(item.get("service_id")): item
        for item in _safe_list(operator.get("services"))
        if isinstance(item, dict) and item.get("service_id")
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_reliability_critic_telemetry_snapshot",
        "observed_at": observed_at,
        "market": {
            "expected_session_phase": expected_market_session_phase(reference),
            "provider_session_phase": market_truth.get("session_phase"),
            "provider_actionable": market_truth.get("actionable") is True,
            "provider_truth_age_seconds": _age_seconds(
                reference, market_truth.get("generated_at")
            ),
        },
        "operator": {
            "present": bool(operator),
            "generated_at": operator.get("generated_at"),
            "age_seconds": _age_seconds(reference, operator.get("generated_at")),
            "lease_generated_at": lease.get("generated_at"),
            "lease_age_seconds": _age_seconds(reference, lease.get("generated_at")),
            "lease_owner_pid": lease.get("owner_pid"),
            "lease_process_alive": _process_alive(lease.get("owner_pid")),
            "status": operator.get("status"),
            "service_running": operator.get("service_running") is True,
            "service_installed": operator.get("service_installed") is True,
            "operational_ready": operator.get("operational_ready") is True,
            "observation_ready": operator.get("observation_ready") is True,
            "committed_release": _safe_dict(operator.get("readiness")).get(
                "committed_release"
            )
            is True,
            "running_build_matches_current": _safe_dict(
                operator.get("readiness")
            ).get("running_build_matches_current")
            is True,
            "launchd_template_matches": _safe_dict(operator.get("readiness")).get(
                "launchd_template_matches"
            )
            is True,
            "fresh_service_count": int(
                _safe_dict(operator.get("freshness")).get("fresh_service_count") or 0
            ),
            "stale_service_count": int(
                _safe_dict(operator.get("freshness")).get("stale_service_count") or 0
            ),
            "not_run_service_count": int(
                _safe_dict(operator.get("freshness")).get("not_run_service_count") or 0
            ),
            "open_circuit_count": int(operator.get("open_circuit_count") or 0),
            "paperops_watch_only": operator.get("paperops_watch_only") is True,
            "order_exposure_integrity": _safe_dict(
                operator.get("order_exposure_integrity")
            ),
            "services": service_records,
            "launchd": operator_launchd,
        },
        "repair_queue": {
            "status": repair_queue.get("status"),
            "open_request_count": int(repair_queue.get("open_request_count") or 0),
            "critical_request_count": int(
                repair_queue.get("critical_request_count") or 0
            ),
        },
        "circuits": {
            "open_circuit_count": int(circuits.get("open_circuit_count") or 0),
            "services": _safe_dict(circuits.get("services")),
        },
        "self_healing": {
            "status": self_healing.get("status"),
            "generated_at": self_healing.get("generated_at"),
            "age_seconds": _age_seconds(reference, self_healing.get("generated_at")),
            "stale_or_missing_artifact_count": int(
                _safe_dict(self_healing.get("stale_artifact_recovery")).get(
                    "stale_or_missing_artifact_count"
                )
                or 0
            ),
            "repair_request_count": int(
                _safe_dict(self_healing.get("repair_request_tier")).get(
                    "repair_request_count"
                )
                or 0
            ),
        },
        "paperops": _paperops_snapshot(runtime, reference),
        "router": {
            "status": router.get("status"),
            "generated_at": router.get("generated_at"),
            "primary_reason": router.get("primary_reason")
            or router.get("reason")
            or router.get("why_not_trading_now"),
        },
        "control_plane": _database_snapshot(runtime),
        "automation": {
            "label": LAUNCHD_LABEL,
            "cadence_seconds": CADENCE_SECONDS,
            "installed": LAUNCHD_TARGET.exists(),
            "installed_template_matches": installed_template_matches(
                LAUNCHD_TEMPLATE, LAUNCHD_TARGET
            ),
            **critic_launchd,
        },
        "authority": _critic_authority(),
    }


def _blocker(
    code: str,
    severity: str,
    plain_english: str,
    *,
    repairable: bool,
    service_id: str | None = None,
) -> dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "plain_english": plain_english,
        "safe_auto_repair_allowed": repairable,
        "service_id": service_id,
    }


def classify_reliability_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    operator = _safe_dict(snapshot.get("operator"))
    paperops = _safe_dict(snapshot.get("paperops"))
    control = _safe_dict(snapshot.get("control_plane"))
    repair_queue = _safe_dict(snapshot.get("repair_queue"))
    circuits = _safe_dict(snapshot.get("circuits"))
    market = _safe_dict(snapshot.get("market"))
    blockers: list[dict[str, Any]] = []

    authority_errors = validate_authority(
        snapshot.get("authority") or {}, prefix="reliability_critic_authority"
    )
    if authority_errors:
        blockers.append(
            _blocker(
                "critic_authority_boundary_invalid",
                "critical",
                "The critic's own safety boundary is invalid.",
                repairable=False,
            )
        )
    if not operator.get("present"):
        blockers.append(
            _blocker(
                "operator_status_missing",
                "critical",
                "The canonical operator status artifact is missing.",
                repairable=False,
            )
        )
    elif not operator.get("service_running"):
        restart_safe = bool(
            operator.get("service_installed")
            and operator.get("committed_release")
            and operator.get("launchd_template_matches")
        )
        blockers.append(
            _blocker(
                "operator_owner_not_running",
                "critical",
                "The single guarded operator owner is not running.",
                repairable=restart_safe,
            )
        )
    lease_fresh = bool(
        operator.get("lease_process_alive")
        and operator.get("lease_age_seconds") is not None
        and float(operator.get("lease_age_seconds") or 0) <= LEASE_MAX_AGE_SECONDS
    )
    if (
        operator.get("age_seconds") is None
        or float(operator.get("age_seconds") or 0) > STATUS_MAX_AGE_SECONDS
    ) and not lease_fresh:
        blockers.append(
            _blocker(
                "operator_status_stale",
                "critical",
                "The operator has stopped publishing a fresh health view.",
                repairable=bool(operator.get("service_running")),
            )
        )
    if operator.get("service_running") and not operator.get("running_build_matches_current"):
        blockers.append(
            _blocker(
                "operator_build_mismatch",
                "critical",
                "The running operator does not match the reviewed local build.",
                repairable=False,
            )
        )
    if int(operator.get("stale_service_count") or 0) > 0:
        blockers.append(
            _blocker(
                "operator_services_stale",
                "critical",
                "One or more registered operator services missed their freshness deadline.",
                repairable=False,
            )
        )
    if int(repair_queue.get("critical_request_count") or 0) > 0:
        blockers.append(
            _blocker(
                "critical_operator_repair_request",
                "critical",
                "The canonical operator has an unresolved critical repair request.",
                repairable=False,
            )
        )
    order_integrity = _safe_dict(operator.get("order_exposure_integrity"))
    if order_integrity and order_integrity.get("status") != "passed":
        blockers.append(
            _blocker(
                "broker_order_exposure_disagreement",
                "critical",
                "Order or exposure truth does not reconcile cleanly.",
                repairable=False,
            )
        )
    if not control.get("present") or control.get("read_error"):
        blockers.append(
            _blocker(
                "control_plane_unreadable",
                "critical",
                "The canonical transactional control plane cannot be read safely.",
                repairable=False,
            )
        )
    latest_reconciliation = _safe_dict(control.get("latest_reconciliation"))
    if latest_reconciliation and (
        latest_reconciliation.get("status") not in {"passed", "in_agreement", "ready"}
        or int(latest_reconciliation.get("blocker_count") or 0) > 0
    ):
        blockers.append(
            _blocker(
                "canonical_reconciliation_failed",
                "critical",
                "The canonical ledger and Alpaca Paper mirror disagree.",
                repairable=False,
            )
        )
    if int(control.get("unresolved_repair_request_count") or 0) > 0:
        blockers.append(
            _blocker(
                "control_plane_repair_request_open",
                "critical",
                "The transactional control plane contains an unresolved repair request.",
                repairable=False,
            )
        )
    for service_id, circuit in _safe_dict(circuits.get("services")).items():
        circuit = _safe_dict(circuit)
        if circuit.get("state") not in {"open", "half_open"}:
            continue
        definition = next(
            (item for item in SERVICE_DEFINITIONS if item.service_id == service_id), None
        )
        repairable = bool(
            definition
            and not definition.paperops_dependency
            and definition.safe_retry_class in SAFE_RETRY_CLASSES
            and circuit.get("failure_class") not in PROHIBITED_FAILURE_CLASSES
        )
        blockers.append(
            _blocker(
                "operator_service_circuit_open",
                "critical",
                f"The {service_id} circuit is {circuit.get('state')}.",
                repairable=repairable,
                service_id=service_id,
            )
        )
    if not paperops.get("present"):
        blockers.append(
            _blocker(
                "paperops_summary_missing",
                "critical",
                "The canonical PaperOps owner has no summary artifact.",
                repairable=False,
            )
        )
    elif paperops.get("age_seconds") is None or float(paperops.get("age_seconds") or 0) > (
        PAPEROPS_MAX_AGE_SECONDS
    ):
        blockers.append(
            _blocker(
                "paperops_summary_stale",
                "critical",
                "The guarded PaperOps owner has not published within its allowed cadence.",
                repairable=False,
            )
        )
    if paperops.get("canonical_control_status") not in {
        None,
        "canonical_paper_control_ready",
    } or paperops.get("canonical_control_blockers"):
        blockers.append(
            _blocker(
                "canonical_paper_control_degraded",
                "critical",
                "The guarded paper-control boundary is degraded.",
                repairable=False,
            )
        )

    if blockers:
        state = (
            "pipeline_degraded_repairable"
            if all(item.get("safe_auto_repair_allowed") for item in blockers)
            else "pipeline_degraded_escalation_required"
        )
        return {
            "state": state,
            "healthy": False,
            "blockers": blockers,
            "primary_reason": blockers[0]["plain_english"],
            "safe_auto_repair_count": sum(
                item.get("safe_auto_repair_allowed") is True for item in blockers
            ),
        }

    fresh_eligible = int(paperops.get("fresh_eligible_submit_count") or 0)
    accepted = int(paperops.get("accepted_handoff_count") or 0)
    session_phase = market.get("expected_session_phase")
    router_reason = _safe_dict(snapshot.get("router")).get("primary_reason")
    if fresh_eligible > 0 or accepted > 0:
        state = (
            "healthy_actionable"
            if session_phase == "regular"
            else "healthy_actionable_waiting_market_session"
        )
        reason = (
            "A guarded paper setup is actionable during the current market session."
            if session_phase == "regular"
            else "A guarded paper setup is ready and is waiting for a real market session."
        )
    elif router_reason:
        state = "healthy_idle_explained"
        reason = str(router_reason)
    else:
        state = "healthy_observing"
        reason = "The pipeline is healthy and observing, with no unexplained execution stall."
    return {
        "state": state,
        "healthy": True,
        "blockers": [],
        "primary_reason": reason,
        "safe_auto_repair_count": 0,
    }


def plan_safe_repairs(
    snapshot: dict[str, Any],
    classification: dict[str, Any],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    seen: set[tuple[str, str | None]] = set()
    for blocker in _safe_list(classification.get("blockers")):
        blocker = _safe_dict(blocker)
        if blocker.get("safe_auto_repair_allowed") is not True:
            continue
        code = blocker.get("code")
        service_id = blocker.get("service_id")
        if code == "operator_owner_not_running":
            action_type = "restart_operator_owner"
        elif code == "operator_service_circuit_open" and service_id:
            action_type = "repair_safe_runtime_circuit"
        elif code == "operator_status_stale":
            action_type = "refresh_read_only_projections"
        else:
            continue
        identity = (action_type, str(service_id) if service_id else None)
        if identity in seen:
            continue
        seen.add(identity)
        actions.append(
            {
                "action_type": action_type,
                "service_id": service_id,
                "trigger_code": code,
            }
        )
    self_healing = _safe_dict(snapshot.get("self_healing"))
    if int(self_healing.get("stale_or_missing_artifact_count") or 0) > 0:
        identity = ("refresh_read_only_projections", None)
        if identity not in seen:
            actions.append(
                {
                    "action_type": "refresh_read_only_projections",
                    "service_id": None,
                    "trigger_code": "known_projection_artifact_stale",
                }
            )
    return actions


def _request_maintenance(runtime: Path, status: str) -> None:
    AtomicArtifactStore(runtime).write_json(
        MAINTENANCE_ARTIFACT,
        {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_operator_maintenance_window",
            "generated_at": now_iso(),
            "status": status,
            "owner_pid": os.getpid(),
            "purpose": "bounded_reliability_critic_safe_runtime_repair",
            "paper_order_created_count": 0,
            "broker_write_count": 0,
            "authority": _critic_authority(),
        },
    )


def _acquire_maintenance_lock(
    runtime: Path,
    *,
    wait_seconds: float,
    sleep_fn: Callable[[float], None],
) -> OperatorMaintenanceLock | None:
    deadline = time.monotonic() + max(0.0, wait_seconds)
    while True:
        lock = OperatorMaintenanceLock(runtime)
        acquired, _reason = lock.acquire(blocking=False)
        if acquired:
            return lock
        if time.monotonic() >= deadline:
            return None
        sleep_fn(min(2.0, max(0.0, deadline - time.monotonic())))


def execute_safe_repairs(
    actions: list[dict[str, Any]],
    settings: Settings | None = None,
    *,
    command_runner: CommandRunner | None = None,
    lock_wait_seconds: float = 60.0,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> list[dict[str, Any]]:
    if not actions:
        return []
    runtime = runtime_dir(settings)
    execute = command_runner or _default_command_runner
    _request_maintenance(runtime, "requested")
    lock = _acquire_maintenance_lock(
        runtime, wait_seconds=lock_wait_seconds, sleep_fn=sleep_fn
    )
    if lock is None:
        _request_maintenance(runtime, "deferred_operator_busy")
        return [
            {
                "action_type": action.get("action_type"),
                "service_id": action.get("service_id"),
                "status": "deferred_operator_busy",
                "verified": False,
            }
            for action in actions
        ]
    _request_maintenance(runtime, "active")
    results: list[dict[str, Any]] = []
    try:
        for action in actions:
            action_type = str(action.get("action_type") or "")
            service_id = action.get("service_id")
            if action_type not in ALLOWED_ACTIONS:
                results.append(
                    {
                        **action,
                        "status": "blocked_action_not_allowlisted",
                        "verified": False,
                    }
                )
                continue
            if action_type == "restart_operator_owner":
                if not OPERATOR_LAUNCHD_TARGET.exists():
                    result = {"returncode": 1, "stderr": "operator_launchd_target_missing"}
                else:
                    launchd = launchd_job_state(
                        OPERATOR_LAUNCHD_LABEL, runner=command_runner
                    )
                    command = (
                        ("launchctl", "kickstart", f"gui/{os.getuid()}/{OPERATOR_LAUNCHD_LABEL}")
                        if launchd.get("loaded")
                        else (
                            "launchctl",
                            "bootstrap",
                            f"gui/{os.getuid()}",
                            str(OPERATOR_LAUNCHD_TARGET),
                        )
                    )
                    result = execute(command, 30)
                results.append(
                    {
                        **action,
                        "status": "attempted" if result.get("returncode") == 0 else "failed",
                        "verified": False,
                        "returncode": result.get("returncode"),
                        "error": result.get("stderr") or None,
                    }
                )
            elif action_type == "repair_safe_runtime_circuit":
                definition = next(
                    (
                        item
                        for item in SERVICE_DEFINITIONS
                        if item.service_id == str(service_id)
                    ),
                    None,
                )
                if (
                    definition is None
                    or definition.paperops_dependency
                    or definition.safe_retry_class not in SAFE_RETRY_CLASSES
                ):
                    results.append(
                        {
                            **action,
                            "status": "blocked_service_not_safe",
                            "verified": False,
                        }
                    )
                    continue
                try:
                    result = repair_operator_service_circuit(
                        str(service_id), settings
                    )
                    results.append(
                        {
                            **action,
                            "status": result.get("status"),
                            "verified": result.get("status") in {"repaired", "not_required"},
                            "verification_pass_count": result.get(
                                "verification_pass_count", 0
                            ),
                        }
                    )
                except (RuntimeError, ValueError) as error:
                    results.append(
                        {
                            **action,
                            "status": "failed",
                            "verified": False,
                            "error": error.__class__.__name__,
                        }
                    )
            elif action_type == "refresh_read_only_projections":
                _payload, _written, errors = build_and_write_self_healing_state(
                    settings, perform_refresh=True
                )
                results.append(
                    {
                        **action,
                        "status": "refreshed" if not errors else "failed",
                        "verified": not errors,
                        "error_count": len(errors),
                    }
                )
    finally:
        _request_maintenance(runtime, "released")
        lock.release()
    return results


def _repair_packet(
    classification: dict[str, Any],
    *,
    generated_at: str,
    history_path: Path,
) -> dict[str, Any]:
    blockers = _safe_list(classification.get("blockers"))
    fingerprint = sha256_json(
        sorted(
            (str(item.get("code")), str(item.get("service_id") or ""))
            for item in blockers
            if isinstance(item, dict)
        )
    )
    recurrence_count = 1
    if history_path.exists():
        for line in history_path.read_text(encoding="utf-8").splitlines():
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("failure_fingerprint") == fingerprint:
                recurrence_count += 1
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_reliability_critic_repair_packet",
        "generated_at": generated_at,
        "status": "operator_review_required" if blockers else "no_repair_required",
        "failure_fingerprint": fingerprint if blockers else None,
        "recurrence_count": recurrence_count if blockers else 0,
        "blockers": blockers,
        "boundary": (
            "This packet may request review. It cannot edit code, change policy or secrets, "
            "invoke PaperOps, write to a broker, approve a strategy, or enable live capital."
        ),
        "authority": _critic_authority(),
    }


def validate_reliability_critic_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("reliability_critic_schema_invalid")
    if payload.get("artifact_type") != "qadam_reliability_critic_status":
        errors.append("reliability_critic_artifact_type_invalid")
    errors.extend(
        validate_authority(
            payload.get("authority") or {}, prefix="reliability_critic_authority"
        )
    )
    authority = _safe_dict(payload.get("authority"))
    for field in (
        "autonomous_code_edit_allowed",
        "risk_threshold_mutation_allowed",
        "strategy_admission_allowed",
        "paperops_invocation_allowed",
        "broker_write_allowed",
        "live_capital_enabled",
    ):
        if authority.get(field) is not False:
            errors.append(f"reliability_critic_unsafe_authority:{field}")
    for action in _safe_list(payload.get("actions")):
        action = _safe_dict(action)
        if action.get("action_type") not in ALLOWED_ACTIONS:
            errors.append("reliability_critic_action_not_allowlisted")
        service_id = action.get("service_id")
        if service_id in {"guarded_paperops", "open_market_conversion"}:
            errors.append("reliability_critic_paper_service_repair_forbidden")
    if payload.get("status") == "passed":
        if payload.get("verification_passed") is not True:
            errors.append("reliability_critic_pass_without_verification")
        if int(payload.get("consecutive_healthy_verification_count") or 0) < 2:
            errors.append("reliability_critic_insufficient_independent_verification")
    if int(payload.get("paper_order_created_count") or 0) != 0:
        errors.append("reliability_critic_created_paper_order")
    if int(payload.get("broker_write_count") or 0) != 0:
        errors.append("reliability_critic_created_broker_write")
    return unique_errors(errors)


def run_reliability_critic(
    settings: Settings | None = None,
    *,
    repair: bool = False,
    verification_wait_seconds: float = 70.0,
    lock_wait_seconds: float = 60.0,
    command_runner: CommandRunner | None = None,
    snapshot_reader: SnapshotReader | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    reader = snapshot_reader or (
        lambda: build_reliability_snapshot(
            settings, command_runner=command_runner
        )
    )
    generated_at = now_iso()
    initial_snapshot = reader()
    initial_classification = classify_reliability_snapshot(initial_snapshot)
    planned_actions = (
        plan_safe_repairs(initial_snapshot, initial_classification) if repair else []
    )
    action_results = execute_safe_repairs(
        planned_actions,
        settings,
        command_runner=command_runner,
        lock_wait_seconds=lock_wait_seconds,
        sleep_fn=sleep_fn,
    )
    samples: list[dict[str, Any]] = []
    if not planned_actions:
        samples.append(
            {
                "snapshot": initial_snapshot,
                "classification": initial_classification,
            }
        )
    required_post_samples = 2 if planned_actions else 1
    for _index in range(required_post_samples):
        if verification_wait_seconds > 0:
            sleep_fn(verification_wait_seconds)
        snapshot = reader()
        samples.append(
            {
                "snapshot": snapshot,
                "classification": classify_reliability_snapshot(snapshot),
            }
        )
    final_classification = _safe_dict(samples[-1].get("classification"))
    consecutive_healthy = 0
    for sample in reversed(samples):
        if _safe_dict(sample.get("classification")).get("healthy") is True:
            consecutive_healthy += 1
        else:
            break
    verification_passed = consecutive_healthy >= 2
    repair_packet = _repair_packet(
        final_classification,
        generated_at=generated_at,
        history_path=runtime / HISTORY_ARTIFACT,
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_reliability_critic_status",
        "generated_at": generated_at,
        "status": "passed" if verification_passed else "degraded",
        "operating_state": final_classification.get("state"),
        "primary_reason": final_classification.get("primary_reason"),
        "healthy": final_classification.get("healthy") is True,
        "repair_enabled": repair,
        "planned_action_count": len(planned_actions),
        "actions": action_results,
        "verification_sample_count": len(samples),
        "consecutive_healthy_verification_count": consecutive_healthy,
        "verification_passed": verification_passed,
        "verification_samples": [
            {
                "observed_at": _safe_dict(item.get("snapshot")).get("observed_at"),
                "state": _safe_dict(item.get("classification")).get("state"),
                "healthy": _safe_dict(item.get("classification")).get("healthy") is True,
                "blocker_codes": [
                    blocker.get("code")
                    for blocker in _safe_list(
                        _safe_dict(item.get("classification")).get("blockers")
                    )
                    if isinstance(blocker, dict)
                ],
            }
            for item in samples
        ],
        "initial_classification": initial_classification,
        "final_classification": final_classification,
        "automation": _safe_dict(samples[-1].get("snapshot")).get("automation"),
        "repair_packet": {
            "status": repair_packet.get("status"),
            "failure_fingerprint": repair_packet.get("failure_fingerprint"),
            "recurrence_count": repair_packet.get("recurrence_count"),
        },
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "public_safe": True,
        "command_disabled": True,
        "authority": _critic_authority(),
    }
    errors = validate_reliability_critic_payload(payload)
    payload["validation_error_count"] = len(errors)
    payload["validation_errors"] = errors
    if errors:
        payload["status"] = "degraded"
        payload["verification_passed"] = False
    store = AtomicArtifactStore(runtime)
    store.write_json(STATUS_ARTIFACT, payload)
    store.write_json(REPAIR_PACKET_ARTIFACT, repair_packet)
    check = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_reliability_critic_checks",
        "generated_at": now_iso(),
        "status": "passed" if not errors and verification_passed else "blocked",
        "verification_passed": verification_passed,
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "authority": _critic_authority(),
    }
    store.write_json(CHECK_ARTIFACT, check)
    event = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_reliability_critic_event",
        "generated_at": generated_at,
        "status": payload["status"],
        "operating_state": payload["operating_state"],
        "planned_action_count": len(planned_actions),
        "verification_passed": payload["verification_passed"],
        "failure_fingerprint": repair_packet.get("failure_fingerprint"),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "authority": _critic_authority(),
    }
    append_jsonl_durable(runtime / HISTORY_ARTIFACT, event)
    append_jsonl_durable(runtime / EVENTS_ARTIFACT, event)
    return payload, errors


__all__ = [
    "CADENCE_SECONDS",
    "CHECK_ARTIFACT",
    "CRITIC_MAX_AGE_SECONDS",
    "EVENTS_ARTIFACT",
    "HISTORY_ARTIFACT",
    "LAUNCHD_LABEL",
    "LAUNCHD_TARGET",
    "LAUNCHD_TEMPLATE",
    "REPAIR_PACKET_ARTIFACT",
    "SCHEMA_VERSION",
    "STATUS_ARTIFACT",
    "build_reliability_snapshot",
    "classify_reliability_snapshot",
    "execute_safe_repairs",
    "installed_template_matches",
    "launchd_job_state",
    "plan_safe_repairs",
    "run_reliability_critic",
    "validate_reliability_critic_payload",
]
