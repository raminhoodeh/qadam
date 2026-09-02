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
    code_defect_revalidation_available,
    FULL_HEAL_RECEIPT_ARTIFACT,
    LEASE_ARTIFACT,
    MAINTENANCE_ARTIFACT,
    OperatorMaintenanceLock,
    REPAIR_QUEUE_ARTIFACT,
    SERVICE_DEFINITIONS,
    STATUS_ARTIFACT as OPERATOR_STATUS_ARTIFACT,
    build_recovery_coverage,
    repair_operator_service_circuit,
    request_operator_full_heal,
    service_recovery_contract_errors,
)
from orchestrator.qadam_hedge_fund_team_health import (
    HEALTH_MAX_AGE_SECONDS as TEAM_HEALTH_MAX_AGE_SECONDS,
    STATUS_ARTIFACT as TEAM_HEALTH_STATUS_ARTIFACT,
    run_hedge_fund_team_cycle,
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
PROHIBITED_FAILURE_CLASSES = {
    "safety_violation",
    "credential_operator_action",
    "parser_schema_drift",
    "disk_resource_pressure",
    "research_integrity_hold",
    "code_defect",
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
    "request_operator_full_heal",
}
FULL_HEAL_BASELINE_SERVICES = (
    "source_ingestion",
    "market_price_refresh",
    "execution_context",
    "open_market_conversion",
    "pattern_scoring",
    "power_market_research",
    "research_evidence_validation",
    "akber_review",
    "qeg_evidence_cycle",
    "qualitative_evidence_cycle",
    "canonical_tradeability",
    "forward_shadow",
    "portfolio_router_review",
    "active_discovery_trial",
    "paper_lifecycle_poll",
    "guarded_paperops",
    "dashboard_refresh",
    "public_status_publication",
)
DEFERRED_RESEARCH_BLOCKER_CODES = {
    "trading_pipeline_service_degraded",
    "operator_service_stale",
    "operator_service_not_run",
}


CommandRunner = Callable[[tuple[str, ...], int], dict[str, Any]]
SnapshotReader = Callable[[], dict[str, Any]]
TeamCycleRunner = Callable[[], tuple[dict[str, Any], list[str]]]


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


def _service_definition(service_id: str) -> Any | None:
    return next(
        (definition for definition in SERVICE_DEFINITIONS if definition.service_id == service_id),
        None,
    )


def _operator_full_heal_allowed(
    service_id: str,
    *,
    failure_class: str | None = None,
    circuit: dict[str, Any] | None = None,
) -> bool:
    definition = _service_definition(service_id)
    if definition is None or service_recovery_contract_errors(definition):
        return False
    if failure_class == "code_defect":
        if not circuit or not code_defect_revalidation_available(service_id, circuit):
            return False
    elif failure_class and failure_class in PROHIBITED_FAILURE_CLASSES:
        return False
    if failure_class and failure_class not in {
        "concurrent_artifact_access",
        "transient_provider_network",
        "rate_limit",
        "stale_artifact",
        "interrupted_resumable_job",
        "optional_transport_unconfigured",
        "code_defect",
    }:
        return False
    return True


def _team_degraded_service_ids(team_health: dict[str, Any]) -> list[str]:
    pipeline = _safe_dict(team_health.get("trading_pipeline"))
    service_ids: set[str] = set()
    for stage in _safe_list(pipeline.get("stages")):
        stage = _safe_dict(stage)
        for service_id in _safe_list(stage.get("degraded_services")):
            if service_id:
                service_ids.add(str(service_id))
    return sorted(service_ids)


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
        "operator_full_heal_request_allowed": True,
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
            "SELECT phase,status,blocker_count,payload_json,created_at "
            "FROM reconciliation_runs "
            "ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        liveness = connection.execute(
            "SELECT status,setup_count,advanced_count,created_at FROM liveness_cycles "
            "ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        handoffs = connection.execute("SELECT COUNT(*) AS count FROM current_handoffs").fetchone()
        latest_reconciliation = dict(reconciliation) if reconciliation else {}
        if latest_reconciliation:
            try:
                reconciliation_payload = json.loads(
                    str(latest_reconciliation.pop("payload_json", "{}"))
                )
            except (TypeError, ValueError):
                reconciliation_payload = {}
            latest_reconciliation["blockers"] = _safe_list(
                reconciliation_payload.get("blockers")
            )
        return {
            "present": True,
            "unresolved_repair_request_count": int(unresolved["count"] if unresolved else 0),
            "latest_reconciliation": latest_reconciliation,
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


def _paperops_snapshot(
    runtime: Path,
    reference: datetime,
    *,
    owner_service: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary = read_json(runtime / "paperops_autonomous_pass_summary.json")
    summary_age_seconds = _age_seconds(reference, summary.get("generated_at"))
    summary_fresh = bool(
        summary_age_seconds is not None
        and summary_age_seconds <= PAPEROPS_MAX_AGE_SECONDS
    )
    paper_runtime = _safe_dict(summary.get("paper_runtime"))
    states = _safe_dict(summary.get("states"))
    control = _safe_dict(summary.get("canonical_paper_control"))
    handoff = _safe_dict(summary.get("router_v3_handoff_boundary"))
    owner = _safe_dict(owner_service)
    owner_freshness = _safe_dict(owner.get("freshness")).get("state")
    owner_circuit = _safe_dict(owner.get("circuit_breaker")).get("state")
    owner_receipt = _safe_dict(owner.get("last_receipt"))
    owner_state = owner.get("current_state")
    owner_liveness_current = bool(
        owner
        and owner.get("service_process_running") is True
        and owner_freshness == "fresh"
        and owner_circuit not in {"open", "half_open"}
        and owner_state in {"idle_no_eligible_work", "idle_market_closed", "supervised"}
        and owner_receipt.get("state") in {"completed", "skipped"}
    )
    return {
        "present": bool(summary),
        "generated_at": summary.get("generated_at"),
        "age_seconds": summary_age_seconds,
        "summary_fresh": summary_fresh,
        "status": summary.get("status"),
        "blockers": _safe_list(summary.get("blockers")),
        "paper_cycle_state": states.get("paper_ops_cycle_state"),
        "paper_live_certification_state": states.get("paper_live_certification_state"),
        "canonical_control_status": control.get("status"),
        "canonical_control_blockers": _safe_list(control.get("blockers")),
        "fresh_eligible_submit_count": int(paper_runtime.get("fresh_eligible_submit_count") or 0),
        "submitted_paper_order_count": int(paper_runtime.get("submitted_paper_order_count") or 0),
        "duplicate_submit_count": int(paper_runtime.get("duplicate_submit_count") or 0),
        "accepted_handoff_count": int(handoff.get("accepted_handoff_count") or 0),
        "new_paper_submission_allowed": handoff.get("new_paper_submission_allowed") is True,
        "pre_wrapper_persistence_status": handoff.get("pre_wrapper_persistence_status"),
        "post_wrapper_reconciliation_status": handoff.get("post_wrapper_reconciliation_status"),
        "owner_service_present": bool(owner),
        "owner_service_freshness": owner_freshness,
        "owner_service_circuit": owner_circuit,
        "owner_service_state": owner_state,
        "owner_receipt_state": owner_receipt.get("state"),
        "owner_skip_reason": owner_receipt.get("skip_reason"),
        "owner_liveness_current": owner_liveness_current,
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
    team_health = read_json(runtime / TEAM_HEALTH_STATUS_ARTIFACT)
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
            "provider_truth_age_seconds": _age_seconds(reference, market_truth.get("generated_at")),
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
            "committed_release": _safe_dict(operator.get("readiness")).get("committed_release")
            is True,
            "running_build_matches_current": _safe_dict(operator.get("readiness")).get(
                "running_build_matches_current"
            )
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
            "order_exposure_integrity": _safe_dict(operator.get("order_exposure_integrity")),
            "services": service_records,
            "launchd": operator_launchd,
        },
        "repair_queue": {
            "status": repair_queue.get("status"),
            "open_request_count": int(repair_queue.get("open_request_count") or 0),
            "critical_request_count": int(repair_queue.get("critical_request_count") or 0),
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
                _safe_dict(self_healing.get("repair_request_tier")).get("repair_request_count") or 0
            ),
        },
        "hedge_fund_team": {
            "present": bool(team_health),
            "generated_at": team_health.get("generated_at"),
            "age_seconds": _age_seconds(reference, team_health.get("generated_at")),
            "status": team_health.get("status"),
            "required_role_count": int(team_health.get("required_role_count") or 0),
            "healthy_required_role_count": int(team_health.get("healthy_required_role_count") or 0),
            "team": _safe_dict(team_health.get("team")),
            "trading_pipeline": _safe_dict(team_health.get("trading_pipeline")),
            "blockers": _safe_list(team_health.get("blockers")),
        },
        "paperops": _paperops_snapshot(
            runtime,
            reference,
            owner_service=service_records.get("guarded_paperops"),
        ),
        "router": {
            "status": router.get("status"),
            "generated_at": router.get("generated_at"),
            "age_seconds": _age_seconds(reference, router.get("generated_at")),
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
        "recovery_coverage": build_recovery_coverage(),
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
    team_health = _safe_dict(snapshot.get("hedge_fund_team"))
    market = _safe_dict(snapshot.get("market"))
    blockers: list[dict[str, Any]] = []

    recovery_coverage = _safe_dict(snapshot.get("recovery_coverage"))
    if recovery_coverage and recovery_coverage.get("status") != "passed":
        blockers.append(
            _blocker(
                "self_healing_recovery_coverage_incomplete",
                "critical",
                "At least one monitored operator service has no validated recovery path.",
                repairable=False,
            )
        )

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
    if not team_health.get("present"):
        blockers.append(
            _blocker(
                "hedge_fund_team_health_missing",
                "critical",
                "The hedge-fund team has no current analysis and health receipt.",
                repairable=True,
            )
        )
    elif (
        team_health.get("age_seconds") is None
        or float(team_health.get("age_seconds") or 0) > TEAM_HEALTH_MAX_AGE_SECONDS
    ):
        blockers.append(
            _blocker(
                "hedge_fund_team_health_stale",
                "critical",
                "The hedge-fund team has not completed its latest three-hour review.",
                repairable=True,
            )
        )
    else:
        pipeline = _safe_dict(team_health.get("trading_pipeline"))
        role_count = int(team_health.get("required_role_count") or 0)
        healthy_roles = int(team_health.get("healthy_required_role_count") or 0)
        if healthy_roles != role_count:
            blockers.append(
                _blocker(
                    "hedge_fund_team_role_degraded",
                    "critical",
                    "One or more hedge-fund team roles did not complete real work successfully.",
                    repairable=True,
                )
            )
        if (
            pipeline.get("status") != "healthy"
            or int(pipeline.get("healthy_stage_count") or 0) != 10
            or int(pipeline.get("stage_count") or 0) != 10
        ):
            degraded_services = _team_degraded_service_ids(team_health)
            if degraded_services:
                for service_id in degraded_services:
                    service_circuit = _safe_dict(
                        _safe_dict(circuits.get("services")).get(service_id)
                    )
                    blockers.append(
                        _blocker(
                            "trading_pipeline_service_degraded",
                            "critical",
                            f"The {service_id} service is degrading Qadam's ten-stage pipeline.",
                            repairable=_operator_full_heal_allowed(
                                service_id,
                                failure_class=str(
                                    service_circuit.get("failure_class") or ""
                                )
                                or None,
                                circuit=service_circuit,
                            ),
                            service_id=service_id,
                        )
                    )
            else:
                blockers.append(
                    _blocker(
                        "trading_pipeline_stage_degraded",
                        "critical",
                        "One or more stages in Qadam's ten-stage trading pipeline are degraded.",
                        repairable=True,
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
    service_records = _safe_dict(operator.get("services"))
    stale_service_ids = sorted(
        service_id
        for service_id, record in service_records.items()
        if _safe_dict(_safe_dict(record).get("freshness")).get("state") == "stale"
    )
    not_run_service_ids = sorted(
        service_id
        for service_id, record in service_records.items()
        if _safe_dict(_safe_dict(record).get("freshness")).get("state") == "not_run"
    )
    if int(operator.get("stale_service_count") or 0) > 0:
        if stale_service_ids:
            for service_id in stale_service_ids:
                blockers.append(
                    _blocker(
                        "operator_service_stale",
                        "critical",
                        f"The {service_id} service missed its freshness deadline.",
                        repairable=_operator_full_heal_allowed(service_id),
                        service_id=service_id,
                    )
                )
        else:
            blockers.append(
                _blocker(
                    "operator_services_stale",
                    "critical",
                    "One or more registered operator services missed their freshness deadline.",
                    repairable=False,
                )
            )
    if int(operator.get("not_run_service_count") or 0) > 0:
        if not_run_service_ids:
            for service_id in not_run_service_ids:
                blockers.append(
                    _blocker(
                        "operator_service_not_run",
                        "critical",
                        f"The {service_id} service has no verified operating receipt.",
                        repairable=_operator_full_heal_allowed(service_id),
                        service_id=service_id,
                    )
                )
        else:
            blockers.append(
                _blocker(
                    "operator_services_not_run",
                    "critical",
                    "One or more registered operator services have no verified operating receipt.",
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
        reconciliation_blockers = {
            str(blocker)
            for blocker in _safe_list(latest_reconciliation.get("blockers"))
            if str(blocker)
        }
        stale_mirror_only = bool(reconciliation_blockers) and reconciliation_blockers <= {
            "paper_account_mirror_stale"
        }
        blockers.append(
            _blocker(
                "canonical_reconciliation_failed",
                "critical",
                (
                    "The canonical ledger is waiting for a fresh Alpaca Paper mirror."
                    if stale_mirror_only
                    else "The canonical ledger and Alpaca Paper mirror disagree."
                ),
                repairable=bool(
                    stale_mirror_only
                    and operator.get("service_running")
                    and _operator_full_heal_allowed("guarded_paperops")
                ),
                service_id="guarded_paperops" if stale_mirror_only else None,
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
            and _operator_full_heal_allowed(
                service_id,
                failure_class=str(circuit.get("failure_class") or "") or None,
                circuit=circuit,
            )
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
                repairable=bool(
                    operator.get("service_running")
                    and _operator_full_heal_allowed("guarded_paperops")
                ),
            )
        )
    elif (
        paperops.get("age_seconds") is None
        or float(paperops.get("age_seconds") or 0) > PAPEROPS_MAX_AGE_SECONDS
    ):
        blockers.append(
            _blocker(
                "paperops_summary_stale",
                "critical",
                "The guarded PaperOps owner has not published within its allowed cadence.",
                repairable=bool(
                    operator.get("service_running")
                    and _operator_full_heal_allowed("guarded_paperops")
                ),
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

    summary_fresh = paperops.get("summary_fresh")
    if summary_fresh is None:
        summary_age = paperops.get("age_seconds")
        summary_fresh = bool(
            summary_age is not None
            and float(summary_age) <= PAPEROPS_MAX_AGE_SECONDS
        )
    fresh_eligible = (
        int(paperops.get("fresh_eligible_submit_count") or 0)
        if summary_fresh
        else 0
    )
    accepted = (
        int(paperops.get("accepted_handoff_count") or 0)
        if summary_fresh
        else 0
    )
    session_phase = market.get("expected_session_phase")
    router = _safe_dict(snapshot.get("router"))
    router_age = router.get("age_seconds")
    router_fresh = router_age is None or float(router_age) <= PAPEROPS_MAX_AGE_SECONDS
    router_reason = router.get("primary_reason") if router_fresh else None
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
    full_heal_service_ids: set[str] = set()
    full_heal_trigger_codes: set[str] = set()
    def blocks_safe_full_heal(value: Any) -> bool:
        blocker = _safe_dict(value)
        if blocker.get("safe_auto_repair_allowed") is True:
            return False
        service_id = str(blocker.get("service_id") or "")
        definition = _service_definition(service_id) if service_id else None
        is_deferred_research_worker = bool(
            blocker.get("code") in DEFERRED_RESEARCH_BLOCKER_CODES
            and definition
            and (definition.long_running or definition.provider_budget_required)
        )
        return not is_deferred_research_worker

    has_hard_stop_blocker = any(
        blocks_safe_full_heal(blocker)
        for blocker in _safe_list(classification.get("blockers"))
    )
    for blocker in _safe_list(classification.get("blockers")):
        blocker = _safe_dict(blocker)
        if blocker.get("safe_auto_repair_allowed") is not True:
            continue
        code = str(blocker.get("code") or "")
        service_id = str(blocker.get("service_id") or "") or None
        if code == "operator_owner_not_running":
            actions.append(
                {
                    "action_type": "restart_operator_owner",
                    "service_id": None,
                    "trigger_code": code,
                }
            )
        elif service_id and _operator_full_heal_allowed(service_id):
            full_heal_service_ids.add(service_id)
            full_heal_trigger_codes.add(code)
        elif code in {
            "operator_status_stale",
            "paperops_summary_missing",
            "paperops_summary_stale",
        }:
            full_heal_service_ids.update(FULL_HEAL_BASELINE_SERVICES)
            full_heal_trigger_codes.add(code)
    self_healing = _safe_dict(snapshot.get("self_healing"))
    if (
        int(self_healing.get("stale_or_missing_artifact_count") or 0) > 0
        and not has_hard_stop_blocker
    ):
        full_heal_service_ids.update(FULL_HEAL_BASELINE_SERVICES)
        full_heal_trigger_codes.add("known_projection_artifact_stale")
    if not has_hard_stop_blocker:
        full_heal_service_ids.update(FULL_HEAL_BASELINE_SERVICES)
        full_heal_trigger_codes.add(
            "scheduled_full_health_sweep"
            if classification.get("healthy") is True
            else "repairable_pipeline_degradation"
        )
    if full_heal_service_ids and not has_hard_stop_blocker:
        actions.append(
            {
                "action_type": "request_operator_full_heal",
                "service_id": None,
                "service_ids": sorted(full_heal_service_ids),
                "trigger_code": sorted(full_heal_trigger_codes)[0],
                "trigger_codes": sorted(full_heal_trigger_codes),
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
    operator_heal_wait_seconds: float = 900.0,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> list[dict[str, Any]]:
    if not actions:
        return []
    runtime = runtime_dir(settings)
    execute = command_runner or _default_command_runner
    results: list[dict[str, Any]] = []
    direct_actions = [
        action
        for action in actions
        if action.get("action_type") != "request_operator_full_heal"
    ]
    full_heal_actions = [
        action
        for action in actions
        if action.get("action_type") == "request_operator_full_heal"
    ]
    if direct_actions:
        _request_maintenance(runtime, "requested")
        lock = _acquire_maintenance_lock(
            runtime,
            wait_seconds=lock_wait_seconds,
            sleep_fn=sleep_fn,
        )
        if lock is None:
            _request_maintenance(runtime, "deferred_operator_busy")
            results.extend(
                {
                    "action_type": action.get("action_type"),
                    "service_id": action.get("service_id"),
                    "status": "deferred_operator_busy",
                    "verified": False,
                }
                for action in direct_actions
            )
        else:
            _request_maintenance(runtime, "active")
            try:
                for action in direct_actions:
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
                                OPERATOR_LAUNCHD_LABEL,
                                runner=command_runner,
                            )
                            command = (
                                (
                                    "launchctl",
                                    "kickstart",
                                    f"gui/{os.getuid()}/{OPERATOR_LAUNCHD_LABEL}",
                                )
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
                                "status": (
                                    "attempted" if result.get("returncode") == 0 else "failed"
                                ),
                                "verified": False,
                                "returncode": result.get("returncode"),
                                "error": result.get("stderr") or None,
                            }
                        )
                    elif action_type == "repair_safe_runtime_circuit":
                        definition = _service_definition(str(service_id))
                        if (
                            definition is None
                            or not _operator_full_heal_allowed(str(service_id))
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
                            result = repair_operator_service_circuit(str(service_id), settings)
                            results.append(
                                {
                                    **action,
                                    "status": result.get("status"),
                                    "verified": result.get("status")
                                    in {"repaired", "not_required"},
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
                            settings,
                            perform_refresh=True,
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

    for action in full_heal_actions:
        if action.get("action_type") not in ALLOWED_ACTIONS:
            results.append(
                {
                    **action,
                    "status": "blocked_action_not_allowlisted",
                    "verified": False,
                }
            )
            continue
        try:
            request = request_operator_full_heal(
                list(action.get("service_ids") or []),
                settings,
                trigger_codes=list(action.get("trigger_codes") or []),
            )
        except ValueError as error:
            results.append(
                {
                    **action,
                    "status": "blocked_invalid_full_heal_request",
                    "verified": False,
                    "error": str(error),
                }
            )
            continue
        deadline = time.monotonic() + max(0.0, operator_heal_wait_seconds)
        receipt: dict[str, Any] = {}
        while True:
            candidate = read_json(runtime / FULL_HEAL_RECEIPT_ARTIFACT)
            if (
                candidate.get("request_id") == request.get("request_id")
                and candidate.get("status") in {"completed", "blocked"}
            ):
                receipt = candidate
                break
            if time.monotonic() >= deadline:
                break
            sleep_fn(min(2.0, max(0.0, deadline - time.monotonic())))
        results.append(
            {
                **action,
                "request_id": request.get("request_id"),
                "status": (
                    "completed"
                    if receipt.get("status") == "completed"
                    else "blocked"
                    if receipt.get("status") == "blocked"
                    else "awaiting_singleton_operator"
                ),
                "verified": bool(
                    receipt.get("status") == "completed"
                    and receipt.get("all_requested_services_revalidated") is True
                    and receipt.get("single_operator_owner_used") is True
                    and receipt.get("guarded_paperops_wrapper_only") is True
                ),
                "receipt_status": receipt.get("status"),
                "all_requested_services_revalidated": receipt.get(
                    "all_requested_services_revalidated"
                )
                is True,
                "single_operator_owner_used": receipt.get("single_operator_owner_used") is True,
                "guarded_paperops_wrapper_only": receipt.get(
                    "guarded_paperops_wrapper_only"
                )
                is True,
                "canonical_paperops_status": receipt.get("canonical_paperops_status"),
                "canonical_paperops_submitted_order_count": int(
                    receipt.get("canonical_paperops_submitted_order_count") or 0
                ),
            }
        )
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
            "This packet may request review or ask the singleton operator to revalidate "
            "approved paper-only services. It cannot edit code, change policy or secrets, "
            "invoke PaperOps directly, write to a broker directly, approve a strategy, "
            "force a trade, or enable live capital."
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
        validate_authority(payload.get("authority") or {}, prefix="reliability_critic_authority")
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
        if action.get("action_type") == "request_operator_full_heal":
            service_ids = [str(item) for item in _safe_list(action.get("service_ids"))]
            if not service_ids:
                errors.append("reliability_critic_full_heal_service_list_empty")
            for selected_service_id in service_ids:
                if not _operator_full_heal_allowed(selected_service_id):
                    errors.append(
                        "reliability_critic_full_heal_service_forbidden:"
                        + selected_service_id
                    )
    if payload.get("status") == "passed":
        if payload.get("verification_passed") is not True:
            errors.append("reliability_critic_pass_without_verification")
        if int(payload.get("consecutive_healthy_verification_count") or 0) < 2:
            errors.append("reliability_critic_insufficient_independent_verification")
        if (
            payload.get("repair_enabled") is True
            and _safe_dict(payload.get("full_heal")).get("all_scopes_verified") is not True
        ):
            errors.append("reliability_critic_pass_without_full_heal_verification")
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
    operator_heal_wait_seconds: float = 900.0,
    command_runner: CommandRunner | None = None,
    snapshot_reader: SnapshotReader | None = None,
    team_cycle_runner: TeamCycleRunner | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    reader = snapshot_reader or (
        lambda: build_reliability_snapshot(settings, command_runner=command_runner)
    )
    generated_at = now_iso()
    initial_snapshot = reader()
    initial_classification = classify_reliability_snapshot(initial_snapshot)
    planned_actions = plan_safe_repairs(initial_snapshot, initial_classification) if repair else []
    action_results = execute_safe_repairs(
        planned_actions,
        settings,
        command_runner=command_runner,
        lock_wait_seconds=lock_wait_seconds,
        operator_heal_wait_seconds=operator_heal_wait_seconds,
        sleep_fn=sleep_fn,
    )
    post_heal_team_cycle_attempted = False
    post_heal_team_payload: dict[str, Any] = {}
    post_heal_team_errors: list[str] = []
    if repair:
        post_heal_team_cycle_attempted = True
        run_team_cycle = team_cycle_runner or (
            lambda: run_hedge_fund_team_cycle(
                settings,
                repair_local=True,
                force=True,
            )
        )
        try:
            post_heal_team_payload, post_heal_team_errors = run_team_cycle()
        except Exception as error:  # fail closed around provider and local-model faults
            post_heal_team_errors = [
                f"post_heal_team_cycle_failed:{error.__class__.__name__}"
            ]
    post_heal_team_cycle_verified = bool(
        not repair
        or (
            post_heal_team_cycle_attempted
            and post_heal_team_payload.get("status") == "passed"
            and not post_heal_team_errors
        )
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
    full_heal_results = [
        result
        for result in action_results
        if result.get("action_type") == "request_operator_full_heal"
    ]
    full_heal_requested = any(
        action.get("action_type") == "request_operator_full_heal"
        for action in planned_actions
    )
    full_heal_receipt_verified = bool(
        full_heal_results
        and all(result.get("verified") is True for result in full_heal_results)
    )
    final_snapshot = _safe_dict(samples[-1].get("snapshot"))
    final_team = _safe_dict(final_snapshot.get("hedge_fund_team"))
    final_pipeline = _safe_dict(final_team.get("trading_pipeline"))
    final_paperops = _safe_dict(final_snapshot.get("paperops"))
    all_scopes_verified = bool(
        (not repair or full_heal_receipt_verified)
        and post_heal_team_cycle_verified
        and final_classification.get("healthy") is True
        and final_team.get("status") == "passed"
        and int(final_team.get("healthy_required_role_count") or 0)
        == int(final_team.get("required_role_count") or 0)
        and int(final_pipeline.get("healthy_stage_count") or 0) == 10
        and int(final_pipeline.get("stage_count") or 0) == 10
        and final_paperops.get("summary_fresh") is True
    )
    verification_passed = consecutive_healthy >= 2 and all_scopes_verified
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
        "full_heal": {
            "scope": [
                "hedge_fund_team",
                "ten_stage_pipeline",
                "singleton_operator",
                "control_plane",
                "broker_reconciliation",
                "router",
                "guarded_paperops",
                "dashboard",
            ],
            "requested": full_heal_requested,
            "request_id": (
                full_heal_results[-1].get("request_id") if full_heal_results else None
            ),
            "receipt_verified": full_heal_receipt_verified,
            "post_heal_team_cycle_attempted": post_heal_team_cycle_attempted,
            "post_heal_team_cycle_verified": post_heal_team_cycle_verified,
            "post_heal_team_cycle_errors": post_heal_team_errors,
            "all_scopes_verified": all_scopes_verified,
        },
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
    errors = unique_errors(
        [
            *validate_reliability_critic_payload(payload),
            *post_heal_team_errors,
        ]
    )
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
        "full_heal_requested": full_heal_requested,
        "full_heal_receipt_verified": full_heal_receipt_verified,
        "all_full_heal_scopes_verified": all_scopes_verified,
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
        "full_heal_requested": full_heal_requested,
        "full_heal_receipt_verified": full_heal_receipt_verified,
        "all_full_heal_scopes_verified": all_scopes_verified,
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
