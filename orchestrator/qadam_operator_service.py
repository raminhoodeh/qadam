"""OR-18 unattended operator-service contract and safety probes.

The service coordinates existing research and status components. It never owns
broker credentials or bypasses guarded PaperOps, and installation remains an
explicit operator action.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import fcntl
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Callable
from zoneinfo import ZoneInfo

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    append_jsonl_durable,
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    sha256_json,
    unique_errors,
    validate_authority,
)

SCHEMA_VERSION = "qadam_operator_service.v2"
PHASE_ID = "OR-18"

STATUS_ARTIFACT = "qadam_operator_service_status.json"
HEARTBEATS_ARTIFACT = "qadam_operator_service_heartbeats.json"
REPAIR_QUEUE_ARTIFACT = "qadam_operator_repair_queue.json"
RETRY_LEDGER_ARTIFACT = "qadam_operator_retry_ledger.jsonl"
SOAK_ARTIFACT = "qadam_operator_soak_test.json"
WHY_NOT_RUNNING_ARTIFACT = "qadam_operator_why_not_running.json"
LEASE_ARTIFACT = "qadam_operator_service_lease.json"
CHECK_ARTIFACT = "qadam_operator_service_checks.json"
RECEIPTS_ARTIFACT = "qadam_operator_service_receipts.jsonl"
INTEGRATION_PROBE_ARTIFACT = "qadam_operator_integration_probe.json"
CIRCUIT_BREAKERS_ARTIFACT = "qadam_operator_circuit_breakers.json"
WORKERS_ARTIFACT = "qadam_operator_workers.json"
SESSION_LEDGER_ARTIFACT = "qadam_operator_session_ledger.jsonl"

LOCK_ARTIFACT = "qadam_long_backtest_lock.json"
RELEASE_ARTIFACT = "qadam_research_lock_release_readiness.json"
EXPERIMENTAL_RELEASE_ARTIFACT = "qadam_experimental_paper_release_readiness.json"
RESEARCH_STATUS_ARTIFACT = "qadam_research_supervisor_status.json"
RESEARCH_HEARTBEAT_ARTIFACT = "qadam_research_supervisor_heartbeat.json"
DASHBOARD_FRESHNESS_ARTIFACT = "qadam_operator_dashboard_freshness.json"
SELF_HEALING_STATUS_ARTIFACT = "qadam_self_healing_status.json"
LEGACY_SOAK_ARTIFACT = "qadam_operational_soak_run.json"

LAUNCHD_LABEL = "com.qadam.operator"
LAUNCHD_TEMPLATE = ROOT / "ops" / "launchd" / f"{LAUNCHD_LABEL}.plist.template"
LAUNCHD_TARGET = Path.home() / "Library" / "LaunchAgents" / f"{LAUNCHD_LABEL}.plist"
INSTALLER = ROOT / "scripts" / "install_qadam_operator_launch_agent.sh"
RUNNER = ROOT / "scripts" / "run_qadam_operator_service.py"
WORKER_RUNNER = ROOT / "scripts" / "run_qadam_operator_worker.py"

FAILURE_CLASSES = (
    "transient_provider_network",
    "rate_limit",
    "credential_operator_action",
    "parser_schema_drift",
    "stale_artifact",
    "disk_resource_pressure",
    "interrupted_resumable_job",
    "code_defect",
    "safety_violation",
)


@dataclass(frozen=True, kw_only=True)
class ServiceDefinition:
    service_id: str
    purpose: str
    cadence_seconds: int
    trigger: str
    ownership: str
    safe_retry_class: str
    command_sequence: tuple[tuple[str, ...], ...]
    timeout_seconds: int
    dependencies: tuple[str, ...]
    concurrency_group: str
    lock_requirement: str
    safety_mode: str
    prerequisite_artifacts: tuple[str, ...] = ()
    prerequisite_max_age_seconds: int = 21600
    long_running: bool = False
    market_session_only: bool = False
    provider_budget_required: bool = False
    integration_probe_command_sequence: tuple[tuple[str, ...], ...] = ()
    paperops_dependency: bool = False
    latency_sensitive: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


SERVICE_DEFINITIONS = (
    ServiceDefinition(
        service_id="source_ingestion",
        purpose="Refresh configured source evidence on provider-safe schedules.",
        cadence_seconds=300,
        trigger="provider_schedule_and_freshness",
        ownership="source_heartbeat_runner",
        safe_retry_class="idempotent_read",
        command_sequence=(
            ("scripts/run_source_heartbeat.py", "--once"),
            ("scripts/run_qadam_live_source_refresh.py", "--max-sources", "10"),
            ("scripts/check_qsase_universal_source_price_matrix.py",),
            ("scripts/check_qsase_source_reliability.py",),
            ("scripts/check_qadam_source_provider_capabilities.py",),
            ("scripts/check_qadam_point_in_time_evidence.py",),
        ),
        timeout_seconds=900,
        dependencies=(),
        concurrency_group="provider_read",
        lock_requirement="research_read_allowed",
        safety_mode="read_only_provider_refresh",
    ),
    ServiceDefinition(
        service_id="historical_source_worker",
        purpose="Resume bounded source-history acquisition from reviewed providers.",
        cadence_seconds=900,
        trigger="incomplete_source_partitions_and_budget",
        ownership="or3_source_history_runner",
        safe_retry_class="interrupted_resumable_job",
        command_sequence=(
            (
                "scripts/run_qadam_source_history_acquisition.py",
                "--allow-network",
                "--provider-terms-reviewed",
                "--max-jobs",
                "10",
                "--classify-deferred",
            ),
        ),
        integration_probe_command_sequence=(
            (
                "scripts/run_qadam_source_history_acquisition.py",
                "--provider-terms-reviewed",
                "--max-jobs",
                "1",
                "--classify-deferred",
            ),
        ),
        timeout_seconds=1800,
        dependencies=(),
        concurrency_group="historical_research",
        lock_requirement="research_read_allowed",
        safety_mode="resumable_provider_acquisition",
        long_running=True,
        provider_budget_required=True,
    ),
    ServiceDefinition(
        service_id="market_price_refresh",
        purpose="Refresh paper-market prices during relevant sessions.",
        cadence_seconds=60,
        trigger="market_session_and_instrument_schedule",
        ownership="existing_market_data_adapters",
        safe_retry_class="idempotent_read",
        command_sequence=(("scripts/check_alpaca_paper_mirror.py", "--live"),),
        integration_probe_command_sequence=(("scripts/check_alpaca_paper_mirror.py",),),
        timeout_seconds=120,
        dependencies=(),
        concurrency_group="provider_read",
        lock_requirement="paper_read_only_allowed",
        safety_mode="alpaca_paper_get_only",
        market_session_only=True,
        latency_sensitive=True,
    ),
    ServiceDefinition(
        service_id="pattern_scoring",
        purpose="Score only after point-in-time evidence refresh completes.",
        cadence_seconds=300,
        trigger="new_evidence_cutoff",
        ownership="pattern_score_v3",
        safe_retry_class="deterministic_calculation",
        command_sequence=(
            ("scripts/run_qadam_pattern_score_tape.py", "--resume"),
            ("scripts/check_qadam_pattern_score_v3.py",),
        ),
        timeout_seconds=600,
        dependencies=("source_ingestion",),
        concurrency_group="research_cpu",
        lock_requirement="research_read_allowed",
        safety_mode="deterministic_research_only",
        prerequisite_artifacts=("qadam_point_in_time_evidence_checks.json",),
    ),
    ServiceDefinition(
        service_id="research_evidence_validation",
        purpose=(
            "Rebuild forward labels, statistical tests, nonlinear review, and the "
            "edge registry in strict dependency order after pattern scoring."
        ),
        cadence_seconds=300,
        trigger="new_pattern_score_or_validation_deadline",
        ownership="research_evidence_validation",
        safe_retry_class="deterministic_calculation",
        command_sequence=(
            ("scripts/check_qadam_forward_labels.py",),
            ("scripts/check_qadam_statistical_backtest.py",),
            ("scripts/check_qadam_nonlinear_quantum_value.py",),
            ("scripts/check_qadam_edge_registry.py",),
        ),
        timeout_seconds=1800,
        dependencies=("pattern_scoring",),
        concurrency_group="research_cpu",
        lock_requirement="research_read_allowed",
        safety_mode="ordered_research_validation_only",
        prerequisite_artifacts=("qadam_pattern_score_v3_checks.json",),
    ),
    ServiceDefinition(
        service_id="akber_review",
        purpose="Form current hypotheses, then re-evaluate tradeability without creating approval.",
        cadence_seconds=300,
        trigger="new_score_and_context",
        ownership="akber_filter_v3",
        safe_retry_class="deterministic_calculation",
        command_sequence=(
            ("scripts/check_qadam_strategy_foundry_v3.py",),
            ("scripts/check_qadam_akber_filter_v3.py",),
        ),
        timeout_seconds=300,
        dependencies=("research_evidence_validation",),
        concurrency_group="research_cpu",
        lock_requirement="research_read_allowed",
        safety_mode="research_eligibility_only",
        prerequisite_artifacts=("qadam_edge_registry_checks.json",),
    ),
    ServiceDefinition(
        service_id="forward_shadow",
        purpose="Observe eligible hypotheses without orders or proof credit.",
        cadence_seconds=300,
        trigger="new_akber_result_or_due_observation",
        ownership="forward_shadow_runner",
        safe_retry_class="idempotent_read",
        command_sequence=(("scripts/run_qadam_forward_shadow.py", "--once"),),
        timeout_seconds=300,
        dependencies=("akber_review",),
        concurrency_group="research_cpu",
        lock_requirement="research_read_allowed",
        safety_mode="counterfactual_no_order",
        prerequisite_artifacts=("qadam_akber_filter_v3_checks.json",),
    ),
    ServiceDefinition(
        service_id="portfolio_router_review",
        purpose="Refresh portfolio risk and assign exactly one final Router state.",
        cadence_seconds=300,
        trigger="new_shadow_or_market_context",
        ownership="portfolio_risk_and_router_v3",
        safe_retry_class="deterministic_calculation",
        command_sequence=(
            ("scripts/check_qadam_portfolio_risk_engine.py",),
            ("scripts/check_qadam_router_v3_paperops.py",),
            ("scripts/check_qadam_experimental_paper_eligibility.py",),
        ),
        timeout_seconds=300,
        dependencies=("forward_shadow",),
        concurrency_group="research_cpu",
        lock_requirement="research_read_allowed",
        safety_mode="single_state_router_no_order",
    ),
    ServiceDefinition(
        service_id="guarded_paperops",
        purpose="Delegate clean handoffs to the existing guarded Alpaca Paper wrapper.",
        cadence_seconds=1200,
        trigger="explicit_release_and_clean_handoff",
        ownership="canonical_paperops_wrapper_only",
        safe_retry_class="no_automatic_retry",
        command_sequence=(("scripts/run_paperops_autonomous_pass.py",),),
        timeout_seconds=1200,
        dependencies=("portfolio_router_review",),
        concurrency_group="paperops",
        lock_requirement="explicit_research_lock_release_required",
        safety_mode="guarded_alpaca_paper_wrapper_only",
        paperops_dependency=True,
        latency_sensitive=True,
    ),
    ServiceDefinition(
        service_id="paper_lifecycle_poll",
        purpose="Poll mirrored paper orders and positions without creating new orders.",
        cadence_seconds=300,
        trigger="open_or_pending_paper_lifecycle",
        ownership="paper_lifecycle_poller",
        safe_retry_class="idempotent_read",
        command_sequence=(
            ("scripts/check_paperops_paper_lifecycle_poller.py", "--poll-paper-orders"),
            ("scripts/check_qadam_paper_lineage_and_proof.py",),
        ),
        integration_probe_command_sequence=(
            ("scripts/check_paperops_paper_lifecycle_poller.py",),
            ("scripts/check_qadam_paper_lineage_and_proof.py",),
        ),
        timeout_seconds=300,
        dependencies=(),
        concurrency_group="paper_read",
        lock_requirement="paper_read_only_allowed",
        safety_mode="alpaca_paper_get_only_no_mutation",
    ),
    ServiceDefinition(
        service_id="learning_attribution",
        purpose="Refresh outcome attribution and learning records without applying proposals.",
        cadence_seconds=86400,
        trigger="new_outcome_or_daily_deadline",
        ownership="paper_lineage_and_learning_cycle",
        safe_retry_class="deterministic_calculation",
        command_sequence=(
            ("scripts/check_qadam_paper_lineage_and_proof.py",),
            ("scripts/check_qadam_experimental_paper_trial.py",),
            ("scripts/check_qadam_learning_cycle_view_model.py",),
            ("scripts/check_qadam_improvement_pipeline_view_model.py",),
        ),
        timeout_seconds=600,
        dependencies=(),
        concurrency_group="research_cpu",
        lock_requirement="research_read_allowed",
        safety_mode="proposal_only_learning",
    ),
    ServiceDefinition(
        service_id="dashboard_refresh",
        purpose="Refresh operator and public-safe dashboard projections.",
        cadence_seconds=240,
        trigger="freshness_deadline_or_upstream_receipt",
        ownership="operator_dashboard_projection",
        safe_retry_class="deterministic_calculation",
        command_sequence=(
            ("scripts/check_qsase_dashboard_view_model.py",),
            ("scripts/check_qadam_certification_contracts.py",),
            ("scripts/check_qadam_operator_soak_v2.py",),
            ("scripts/check_qadam_operator_soak_v3.py",),
            ("scripts/check_qadam_experimental_paper_trial.py",),
            ("scripts/check_qadam_operator_ready_edge_engine.py",),
            ("scripts/check_qadam_operator_dashboard.py",),
            ("scripts/check_qadam_dashboard_epoch_isolation.py",),
            ("scripts/check_qadam_guarded_paper_launch.py",),
            ("scripts/check_qadam_experimental_paper_release.py",),
            ("scripts/check_qadam_clean_epoch_operating.py",),
            ("scripts/check_qadam_autonomous_experimental_paper_epoch.py",),
            ("scripts/export_cockpit_status.py", "--no-landing-copy"),
            ("scripts/publish_qadam_public_status.py",),
            ("scripts/check_qadam_public_status_bridge.py", "--report-only"),
            ("scripts/check_qadam_clean_epoch_operational_readiness.py",),
        ),
        timeout_seconds=600,
        dependencies=(),
        concurrency_group="projection",
        lock_requirement="research_read_allowed",
        safety_mode="read_only_public_safe_projection",
    ),
    ServiceDefinition(
        service_id="challenger_research",
        purpose="Re-run the complete ordered evidence-validation chain off peak.",
        cadence_seconds=86400,
        trigger="off_peak_resource_budget",
        ownership="research_supervisor",
        safe_retry_class="interrupted_resumable_job",
        command_sequence=(
            ("scripts/check_qadam_forward_labels.py",),
            ("scripts/check_qadam_statistical_backtest.py",),
            ("scripts/check_qadam_nonlinear_quantum_value.py",),
            ("scripts/check_qadam_edge_registry.py",),
        ),
        timeout_seconds=7200,
        dependencies=("pattern_scoring",),
        concurrency_group="historical_research",
        lock_requirement="research_read_allowed",
        safety_mode="resumable_challenger_research",
        long_running=True,
    ),
)


def operator_service_contract_hash() -> str:
    """Bind reliability evidence to the exact scheduled service contract."""

    return sha256_json([definition.to_dict() for definition in SERVICE_DEFINITIONS])


INTEGRATION_PROBE_SERVICES = (
    "historical_source_worker",
    "source_ingestion",
    "pattern_scoring",
    "research_evidence_validation",
    "akber_review",
    "forward_shadow",
    "portfolio_router_review",
    "paper_lifecycle_poll",
    "learning_attribution",
    "dashboard_refresh",
)


SOAK_SCENARIOS = (
    ("network_loss", "provider network timeout", "transient_provider_network"),
    ("laptop_sleep", "interrupted after laptop sleep", "interrupted_resumable_job"),
    ("sigterm", "SIGTERM interrupted resumable job", "interrupted_resumable_job"),
    ("provider_429", "HTTP 429 rate limit", "rate_limit"),
    ("malformed_response", "malformed JSON schema response", "parser_schema_drift"),
    ("stale_lock", "stale lock interrupted job", "interrupted_resumable_job"),
    ("disk_threshold", "disk free space below threshold", "disk_resource_pressure"),
    ("local_llm_down", "local LLM provider unavailable", "transient_provider_network"),
    ("frontier_down", "frontier provider unavailable", "transient_provider_network"),
    ("quantum_fallback", "quantum provider unavailable fallback", "transient_provider_network"),
    ("unsafe_route", "live broker endpoint requested", "safety_violation"),
)


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


class OperatorServiceLease:
    """Process-scoped non-blocking file lock with a public-safe lease mirror."""

    def __init__(self, runtime: Path, *, lease_ttl_seconds: int = 180):
        self.runtime = runtime.resolve()
        self.lease_ttl_seconds = lease_ttl_seconds
        self.store = AtomicArtifactStore(self.runtime)
        self._handle: Any = None

    def acquire(self, *, owner_pid: int | None = None) -> tuple[bool, str]:
        pid = owner_pid or os.getpid()
        lock_path = self.runtime / ".qadam_operator_service.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = lock_path.open("a+", encoding="utf-8")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            handle.close()
            return False, "active_operator_service_lease_exists"
        self._handle = handle
        generated_at = now_iso()
        existing = read_json(self.runtime / LEASE_ARTIFACT)
        lease = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_operator_service_lease",
            "generated_at": generated_at,
            "status": "active",
            "owner_pid": pid,
            "acquired_at": generated_at,
            "expires_at": (
                datetime.now(timezone.utc) + timedelta(seconds=self.lease_ttl_seconds)
            ).isoformat(),
            "stale_lease_recovered": bool(existing)
            and existing.get("status") == "active"
            and not _pid_alive(int(existing.get("owner_pid") or 0)),
            "authority": authority_flags(),
        }
        self.store.write_json(LEASE_ARTIFACT, lease)
        return True, "operator_service_lease_acquired"

    def renew(self, *, owner_pid: int | None = None) -> bool:
        if self._handle is None:
            return False
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

    def release(self, *, owner_pid: int | None = None, reason: str = "clean_exit") -> bool:
        if self._handle is None:
            return False
        pid = owner_pid or os.getpid()
        lease = read_json(self.runtime / LEASE_ARTIFACT)
        released = int(lease.get("owner_pid") or 0) == pid
        if released:
            lease.update(
                {
                    "generated_at": now_iso(),
                    "status": "released",
                    "release_reason": reason,
                }
            )
            self.store.write_json(LEASE_ARTIFACT, lease)
        fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        self._handle.close()
        self._handle = None
        return released


def classify_failure(message: str, *, status_code: int | None = None) -> str:
    text = str(message or "").lower()
    if any(
        token in text
        for token in ("live broker", "live capital", "unauthorized write", "safety violation")
    ):
        return "safety_violation"
    if status_code == 429 or "429" in text or "rate limit" in text:
        return "rate_limit"
    if any(
        token in text
        for token in ("credential", "unauthorized", "forbidden", "401", "403", "token expired")
    ):
        return "credential_operator_action"
    if any(
        token in text for token in ("malformed", "schema", "parse", "invalid json", "jsondecode")
    ):
        return "parser_schema_drift"
    if any(token in text for token in ("disk", "no space", "resource pressure", "memory pressure")):
        return "disk_resource_pressure"
    if any(token in text for token in ("stale artifact", "freshness deadline", "artifact missing")):
        return "stale_artifact"
    if any(
        token in text
        for token in ("sigterm", "sleep", "interrupted", "stale lock", "resume cursor")
    ):
        return "interrupted_resumable_job"
    if any(
        token in text
        for token in ("network", "timeout", "connection", "provider unavailable", "dns")
    ):
        return "transient_provider_network"
    return "code_defect"


def retry_policy(failure_class: str, *, attempt_count: int = 0) -> dict[str, Any]:
    policies: dict[str, dict[str, Any]] = {
        "transient_provider_network": {
            "automatic_retry_allowed": attempt_count < 3,
            "maximum_attempts": 3,
            "backoff_seconds": min(30 * (2**attempt_count), 300),
            "circuit_breaker_after_attempts": 3,
            "next_action": "retry_idempotent_read_then_open_circuit",
        },
        "rate_limit": {
            "automatic_retry_allowed": attempt_count < 5,
            "maximum_attempts": 5,
            "backoff_seconds": min(60 * (2**attempt_count), 3600),
            "circuit_breaker_after_attempts": 5,
            "next_action": "respect_provider_retry_after",
        },
        "stale_artifact": {
            "automatic_retry_allowed": attempt_count < 1,
            "maximum_attempts": 1,
            "backoff_seconds": 0,
            "circuit_breaker_after_attempts": 1,
            "next_action": "run_known_safe_refresh_then_validate",
        },
        "interrupted_resumable_job": {
            "automatic_retry_allowed": attempt_count < 1,
            "maximum_attempts": 1,
            "backoff_seconds": 0,
            "circuit_breaker_after_attempts": 1,
            "next_action": "resume_incomplete_idempotent_job_from_checkpoint",
        },
    }
    policy = policies.get(
        failure_class,
        {
            "automatic_retry_allowed": False,
            "maximum_attempts": 0,
            "backoff_seconds": None,
            "circuit_breaker_after_attempts": 0,
            "next_action": (
                "stop_affected_work_and_require_safety_review"
                if failure_class == "safety_violation"
                else "write_specific_repair_request"
            ),
        },
    )
    return {
        "failure_class": failure_class,
        "attempt_count": attempt_count,
        "safe_idempotent_operations_only": True,
        "paperops_retry_allowed": False,
        "broker_write_retry_allowed": False,
        "code_edit_allowed": False,
        "secret_change_allowed": False,
        "authority_change_allowed": False,
        **policy,
    }


CommandExecutor = Callable[[tuple[str, ...], int], dict[str, Any]]


def _service_definition(service_id: str) -> ServiceDefinition:
    for definition in SERVICE_DEFINITIONS:
        if definition.service_id == service_id:
            return definition
    raise ValueError(f"unknown_operator_service:{service_id}")


def _command_sequence(
    definition: ServiceDefinition,
    *,
    integration_probe: bool,
) -> tuple[tuple[str, ...], ...]:
    if integration_probe and definition.integration_probe_command_sequence:
        return definition.integration_probe_command_sequence
    return definition.command_sequence


def _display_command(command: tuple[str, ...]) -> list[str]:
    return [".venv/bin/python", *command]


def _sanitize_process_output(value: str, *, limit: int = 2400) -> str:
    text = str(value or "")[-limit:]
    patterns = (
        (r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s]+", r"\1[REDACTED]"),
        (r"(?i)((?:api[_-]?key|api[_-]?secret|token)\s*[:=]\s*)[^\s]+", r"\1[REDACTED]"),
        (r"\b(?:db-[A-Za-z0-9]{12,}|ghp_[A-Za-z0-9]{20,})\b", "[REDACTED]"),
    )
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text


def _default_command_executor(command: tuple[str, ...], timeout_seconds: int) -> dict[str, Any]:
    started = time.monotonic()
    environment = os.environ.copy()
    environment.update(
        {
            "QADAM_OPERATOR_DISPATCH": "1",
            "QADAM_OPERATOR_SAFETY_MODE": "paper_only",
            "QADAM_LIVE_CAPITAL_ENABLED": "false",
        }
    )
    try:
        completed = subprocess.run(
            [sys.executable, *command],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        return {
            "returncode": completed.returncode,
            "stdout": _sanitize_process_output(completed.stdout),
            "stderr": _sanitize_process_output(completed.stderr),
            "duration_seconds": round(time.monotonic() - started, 6),
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "returncode": 124,
            "stdout": _sanitize_process_output(str(exc.stdout or "")),
            "stderr": _sanitize_process_output(f"timeout after {timeout_seconds}s"),
            "duration_seconds": round(time.monotonic() - started, 6),
            "timed_out": True,
        }


def _result_is_evidence_hold(result: dict[str, Any]) -> bool:
    output = f"{result.get('stdout', '')}\n{result.get('stderr', '')}".lower()
    hold_states = (
        "status=evidence_maturing",
        "status=hold",
        "status=blocked_evidence_maturing",
        "status=complete_for_supported_sources",
        "status=running_idle_no_eligible_hypothesis",
    )
    return (
        int(result.get("returncode") or 0) != 0
        and "validation_error_count=0" in output
        and any(state in output for state in hold_states)
    )


def _execute_service_synchronously(
    definition: ServiceDefinition,
    *,
    executor: CommandExecutor | None = None,
    integration_probe: bool = False,
) -> dict[str, Any]:
    execute = executor or _default_command_executor
    command_results: list[dict[str, Any]] = []
    state = "completed"
    for command in _command_sequence(definition, integration_probe=integration_probe):
        if not command or not (ROOT / command[0]).is_file():
            result = {
                "returncode": 127,
                "stdout": "",
                "stderr": f"approved runner missing: {command[0] if command else 'empty'}",
                "duration_seconds": 0.0,
                "timed_out": False,
            }
        else:
            result = execute(command, definition.timeout_seconds)
        accepted_hold = _result_is_evidence_hold(result)
        command_results.append(
            {
                "command": _display_command(command),
                "returncode": int(result.get("returncode") or 0),
                "duration_seconds": float(result.get("duration_seconds") or 0.0),
                "timed_out": result.get("timed_out") is True,
                "stdout_tail": _sanitize_process_output(str(result.get("stdout") or "")),
                "stderr_tail": _sanitize_process_output(str(result.get("stderr") or "")),
                "evidence_hold_accepted": accepted_hold,
            }
        )
        if int(result.get("returncode") or 0) != 0 and not accepted_hold:
            state = "failed"
            break
        if accepted_hold:
            state = "completed_with_evidence_hold"
    return {
        "state": state,
        "command_results": command_results,
        "duration_seconds": round(
            sum(float(record.get("duration_seconds") or 0.0) for record in command_results),
            6,
        ),
    }


def _last_receipts(runtime: Path) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for record in read_jsonl(runtime / RECEIPTS_ARTIFACT):
        service_id = str(record.get("service_id") or "")
        if service_id:
            latest[service_id] = record
    return latest


def _last_successful_receipts(runtime: Path) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    successful = {"completed", "completed_with_evidence_hold", "worker_completed"}
    for record in read_jsonl(runtime / RECEIPTS_ARTIFACT):
        if record.get("state") not in successful:
            continue
        service_id = str(record.get("service_id") or "")
        if service_id:
            latest[service_id] = record
    return latest


def _append_receipt(runtime: Path, receipt: dict[str, Any]) -> None:
    append_jsonl_durable(runtime / RECEIPTS_ARTIFACT, receipt)


def _next_due_at(definition: ServiceDefinition, receipt: dict[str, Any] | None) -> str:
    completed = _parse_timestamp((receipt or {}).get("completed_at"))
    if completed is None:
        return now_iso()
    return (completed + timedelta(seconds=definition.cadence_seconds)).isoformat()


def _is_due(
    definition: ServiceDefinition,
    receipt: dict[str, Any] | None,
    *,
    timestamp: datetime,
) -> bool:
    if not receipt:
        return True
    due_at = _parse_timestamp(_next_due_at(definition, receipt))
    return due_at is None or due_at <= timestamp


def _market_is_open(timestamp: datetime) -> bool:
    local = timestamp.astimezone(ZoneInfo("America/New_York"))
    if local.weekday() >= 5:
        return False
    minute = local.hour * 60 + local.minute
    return (9 * 60 + 30) <= minute < 16 * 60


def _provider_budget_available(runtime: Path) -> bool:
    budget = read_json(runtime / "qadam_backfill_cost_and_rate_limit_state.json")
    remaining = budget.get("historical_data_budget_remaining_usd")
    disk_free = int(budget.get("disk_free_bytes") or 0)
    if remaining is not None and float(remaining) <= 0:
        return False
    return not disk_free or disk_free >= 5 * 1024**3


def _prerequisites_fresh(
    runtime: Path,
    definition: ServiceDefinition,
    *,
    timestamp: datetime,
) -> tuple[bool, list[str]]:
    stale: list[str] = []
    for filename in definition.prerequisite_artifacts:
        path = runtime / filename
        payload = read_json(path)
        generated = _parse_timestamp(payload.get("generated_at")) if payload else None
        if not path.is_file() or generated is None:
            stale.append(filename)
            continue
        if (timestamp - generated).total_seconds() > definition.prerequisite_max_age_seconds:
            stale.append(filename)
    return not stale, stale


def _paper_lifecycle_work_exists(runtime: Path) -> bool:
    mirror = read_json(runtime / "alpaca_paper_mirror.json")
    snapshot = mirror.get("snapshot") if isinstance(mirror.get("snapshot"), dict) else {}
    open_positions = int(
        snapshot.get("open_position_count")
        if snapshot.get("open_position_count") is not None
        else mirror.get("position_count") or 0
    )
    open_states = {"new", "accepted", "pending_new", "partially_filled", "held"}
    open_orders = sum(
        str(record.get("status") or record.get("order_status") or "").lower() in open_states
        for record in read_jsonl(runtime / "paper_orders.jsonl")
    )
    return open_orders > 0 or open_positions > 0


def _clean_paperops_handoff_exists(runtime: Path) -> bool:
    return bool(read_jsonl(runtime / "qadam_paperops_handoff_v3_accepted.jsonl"))


def _paper_release_state(runtime: Path) -> tuple[dict[str, Any], bool]:
    validated = read_json(runtime / RELEASE_ARTIFACT)
    experimental = read_json(runtime / EXPERIMENTAL_RELEASE_ARTIFACT)
    effective = bool(
        validated.get("release_effective") is True
        or experimental.get("experimental_paper_release_effective") is True
    )
    return (
        experimental
        if experimental.get("experimental_paper_release_effective") is True
        else validated,
        effective,
    )


def _workers(runtime: Path) -> dict[str, Any]:
    payload = read_json(runtime / WORKERS_ARTIFACT)
    records = payload.get("workers") if isinstance(payload.get("workers"), dict) else {}
    changed = False
    for service_id, record in records.items():
        if record.get("state") != "running":
            continue
        if not _pid_alive(int(record.get("pid") or 0)):
            record.update(
                {
                    "state": "interrupted",
                    "completed_at": now_iso(),
                    "failure_class": "interrupted_resumable_job",
                    "why": "worker_pid_no_longer_active_before_terminal_receipt",
                }
            )
            changed = True
    if changed:
        AtomicArtifactStore(runtime).write_json(
            WORKERS_ARTIFACT,
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_operator_workers",
                "generated_at": now_iso(),
                "workers": records,
                "authority": authority_flags(),
            },
        )
    return records


def _write_workers(runtime: Path, records: dict[str, Any]) -> None:
    AtomicArtifactStore(runtime).write_json(
        WORKERS_ARTIFACT,
        {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_operator_workers",
            "generated_at": now_iso(),
            "workers": records,
            "authority": authority_flags(),
        },
    )


def _active_concurrency_groups(runtime: Path) -> set[str]:
    return {
        str(record.get("concurrency_group"))
        for record in _workers(runtime).values()
        if record.get("state") == "running" and _pid_alive(int(record.get("pid") or 0))
    }


def _launch_resumable_worker(
    runtime: Path,
    definition: ServiceDefinition,
    *,
    receipt_id: str,
) -> dict[str, Any]:
    log_path = runtime / f"qadam-operator-worker-{definition.service_id}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started_at = now_iso()
    records = _workers(runtime)
    records[definition.service_id] = {
        "service_id": definition.service_id,
        "receipt_id": receipt_id,
        "pid": None,
        "state": "launching",
        "started_at": started_at,
        "concurrency_group": definition.concurrency_group,
        "resume_required": True,
        "command": [
            ".venv/bin/python",
            "scripts/run_qadam_operator_worker.py",
            "--service-id",
            definition.service_id,
        ],
        "log_path": str(log_path.relative_to(ROOT)),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
    }
    _write_workers(runtime, records)
    with log_path.open("a", encoding="utf-8") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                str(WORKER_RUNNER),
                "--service-id",
                definition.service_id,
                "--receipt-id",
                receipt_id,
            ],
            cwd=ROOT,
            env={
                **os.environ,
                "QADAM_OPERATOR_DISPATCH": "1",
                "QADAM_OPERATOR_SAFETY_MODE": "paper_only",
                "QADAM_LIVE_CAPITAL_ENABLED": "false",
            },
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            start_new_session=True,
        )
    records = _workers(runtime)
    current = records.get(definition.service_id, {})
    if current.get("receipt_id") == receipt_id and current.get("state") not in {
        "worker_completed",
        "failed",
    }:
        current.update({"pid": process.pid, "state": "running"})
        records[definition.service_id] = current
    _write_workers(runtime, records)
    return records[definition.service_id]


def _circuit_breaker_state(runtime: Path) -> dict[str, Any]:
    payload = read_json(runtime / CIRCUIT_BREAKERS_ARTIFACT)
    return payload.get("services") if isinstance(payload.get("services"), dict) else {}


def _write_circuit_breakers(runtime: Path, services: dict[str, Any]) -> None:
    AtomicArtifactStore(runtime).write_json(
        CIRCUIT_BREAKERS_ARTIFACT,
        {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_operator_circuit_breakers",
            "generated_at": now_iso(),
            "services": services,
            "open_circuit_count": sum(
                record.get("state") == "open" for record in services.values()
            ),
            "authority": authority_flags(),
        },
    )


def _record_failure(
    runtime: Path,
    definition: ServiceDefinition,
    receipt: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    command_results = receipt.get("command_results") or []
    output = "\n".join(
        f"{record.get('stdout_tail', '')}\n{record.get('stderr_tail', '')}"
        for record in command_results
    )
    failure_class = classify_failure(output)
    circuits = _circuit_breaker_state(runtime)
    prior = circuits.get(definition.service_id, {})
    attempt_count = int(prior.get("consecutive_failure_count") or 0) + 1
    policy = retry_policy(failure_class, attempt_count=attempt_count - 1)
    automatic_retry = (
        policy.get("automatic_retry_allowed") is True
        and definition.safe_retry_class
        in {
            "idempotent_read",
            "deterministic_calculation",
            "interrupted_resumable_job",
        }
        and definition.paperops_dependency is False
    )
    threshold = int(policy.get("circuit_breaker_after_attempts") or 0)
    circuit_open = (
        failure_class == "safety_violation"
        or (threshold > 0 and attempt_count >= threshold)
        or not automatic_retry
    )
    circuits[definition.service_id] = {
        "state": "open" if circuit_open else "closed_retry_scheduled",
        "failure_class": failure_class,
        "consecutive_failure_count": attempt_count,
        "automatic_retry_allowed": automatic_retry and not circuit_open,
        "backoff_seconds": policy.get("backoff_seconds"),
        "last_failure_at": receipt.get("completed_at"),
        "next_retry_at": (
            datetime.now(timezone.utc) + timedelta(seconds=int(policy.get("backoff_seconds") or 0))
        ).isoformat()
        if automatic_retry and not circuit_open
        else None,
    }
    _write_circuit_breakers(runtime, circuits)
    retry_record = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_retry_event",
        "retry_event_id": "retry:"
        + sha256_json({"receipt_id": receipt["receipt_id"], "failure_class": failure_class})[:24],
        "generated_at": now_iso(),
        "service_id": definition.service_id,
        "failure_class": failure_class,
        "policy": {**policy, "automatic_retry_allowed": automatic_retry and not circuit_open},
        "retry_attempted": False,
        "retry_scheduled": automatic_retry and not circuit_open,
        "paper_order_created": False,
        "broker_write_count": 0,
        "authority": authority_flags(),
    }
    append_jsonl_durable(runtime / RETRY_LEDGER_ARTIFACT, retry_record)
    return failure_class, retry_record


def _clear_circuit_after_success(runtime: Path, service_id: str) -> None:
    circuits = _circuit_breaker_state(runtime)
    if service_id not in circuits:
        return
    circuits[service_id] = {
        "state": "closed",
        "failure_class": None,
        "consecutive_failure_count": 0,
        "automatic_retry_allowed": False,
        "backoff_seconds": None,
        "last_success_at": now_iso(),
        "next_retry_at": None,
    }
    _write_circuit_breakers(runtime, circuits)


def _skip_receipt(
    definition: ServiceDefinition,
    *,
    reason: str,
    generated_at: str,
    integration_probe: bool,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    material = {
        "service_id": definition.service_id,
        "reason": reason,
        "generated_at": generated_at,
        "integration_probe": integration_probe,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_service_receipt",
        "receipt_id": "operator-receipt:" + sha256_json(material)[:24],
        "generated_at": generated_at,
        "service_id": definition.service_id,
        "state": "skipped",
        "skip_reason": reason,
        "detail": detail or {},
        "integration_probe": integration_probe,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }


def dispatch_due_jobs(
    settings: Settings | None = None,
    *,
    force_due: bool = False,
    integration_probe: bool = False,
    service_ids: tuple[str, ...] | None = None,
    executor: CommandExecutor | None = None,
    max_jobs: int = 0,
) -> dict[str, Any]:
    """Run only allowlisted due jobs and record every execution or skip."""

    runtime = runtime_dir(settings)
    generated_at = now_iso()
    timestamp = _parse_timestamp(generated_at) or datetime.now(timezone.utc)
    selected = set(service_ids or (definition.service_id for definition in SERVICE_DEFINITIONS))
    lock = read_json(runtime / LOCK_ARTIFACT)
    release, release_effective = _paper_release_state(runtime)
    research_lock_active = lock.get("status") == "active"
    successful = _last_successful_receipts(runtime)
    circuits = _circuit_breaker_state(runtime)
    active_groups = _active_concurrency_groups(runtime)
    cycle_successes: set[str] = set()
    receipts: list[dict[str, Any]] = []
    executed_count = 0

    for definition in SERVICE_DEFINITIONS:
        if definition.service_id not in selected:
            continue
        if max_jobs and executed_count >= max_jobs:
            receipt = _skip_receipt(
                definition,
                reason="cycle_job_budget_exhausted",
                generated_at=generated_at,
                integration_probe=integration_probe,
            )
            _append_receipt(runtime, receipt)
            receipts.append(receipt)
            continue
        if definition.paperops_dependency and (research_lock_active or not release_effective):
            receipt = _skip_receipt(
                definition,
                reason="research_lock",
                generated_at=generated_at,
                integration_probe=integration_probe,
                detail={"release_effective": release_effective},
            )
        elif definition.service_id == "guarded_paperops" and not _clean_paperops_handoff_exists(
            runtime
        ):
            receipt = _skip_receipt(
                definition,
                reason="no_eligible_work",
                generated_at=generated_at,
                integration_probe=integration_probe,
            )
        elif (
            definition.market_session_only
            and not _market_is_open(timestamp)
            and not integration_probe
        ):
            receipt = _skip_receipt(
                definition,
                reason="market_closed",
                generated_at=generated_at,
                integration_probe=integration_probe,
            )
        elif (
            definition.service_id == "paper_lifecycle_poll"
            and not _paper_lifecycle_work_exists(runtime)
            and not integration_probe
        ):
            receipt = _skip_receipt(
                definition,
                reason="no_eligible_work",
                generated_at=generated_at,
                integration_probe=integration_probe,
            )
        elif definition.provider_budget_required and not _provider_budget_available(runtime):
            receipt = _skip_receipt(
                definition,
                reason="cost_budget_exhausted",
                generated_at=generated_at,
                integration_probe=integration_probe,
            )
        elif definition.long_running and definition.concurrency_group in active_groups:
            receipt = _skip_receipt(
                definition,
                reason="service_already_active",
                generated_at=generated_at,
                integration_probe=integration_probe,
            )
        elif (
            circuits.get(definition.service_id, {}).get("state") == "open"
            and not integration_probe
        ):
            receipt = _skip_receipt(
                definition,
                reason="circuit_breaker_open",
                generated_at=generated_at,
                integration_probe=integration_probe,
                detail={"failure_class": circuits[definition.service_id].get("failure_class")},
            )
        elif (
            circuits.get(definition.service_id, {}).get("state") == "closed_retry_scheduled"
            and (
                _parse_timestamp(circuits[definition.service_id].get("next_retry_at")) or timestamp
            )
            > timestamp
            and not force_due
        ):
            receipt = _skip_receipt(
                definition,
                reason="retry_backoff",
                generated_at=generated_at,
                integration_probe=integration_probe,
                detail={"next_retry_at": circuits[definition.service_id].get("next_retry_at")},
            )
        elif not force_due and not _is_due(
            definition, successful.get(definition.service_id), timestamp=timestamp
        ):
            receipt = _skip_receipt(
                definition,
                reason="not_due",
                generated_at=generated_at,
                integration_probe=integration_probe,
                detail={
                    "next_due_at": _next_due_at(definition, successful.get(definition.service_id))
                },
            )
        else:
            missing_dependencies = [
                dependency
                for dependency in definition.dependencies
                if dependency not in cycle_successes and dependency not in successful
            ]
            prerequisites_ok, stale_prerequisites = _prerequisites_fresh(
                runtime, definition, timestamp=timestamp
            )
            if missing_dependencies:
                receipt = _skip_receipt(
                    definition,
                    reason="dependency_not_ready",
                    generated_at=generated_at,
                    integration_probe=integration_probe,
                    detail={"dependencies": missing_dependencies},
                )
            elif not prerequisites_ok:
                receipt = _skip_receipt(
                    definition,
                    reason="stale_prerequisite",
                    generated_at=generated_at,
                    integration_probe=integration_probe,
                    detail={"artifacts": stale_prerequisites},
                )
            else:
                receipt_id = (
                    "operator-receipt:"
                    + sha256_json(
                        {
                            "service_id": definition.service_id,
                            "generated_at": generated_at,
                            "integration_probe": integration_probe,
                        }
                    )[:24]
                )
                if definition.long_running and not integration_probe and executor is None:
                    worker = _launch_resumable_worker(runtime, definition, receipt_id=receipt_id)
                    receipt = {
                        "schema_version": SCHEMA_VERSION,
                        "artifact_type": "qadam_operator_service_receipt",
                        "receipt_id": receipt_id,
                        "generated_at": generated_at,
                        "service_id": definition.service_id,
                        "state": (
                            "worker_started"
                            if worker.get("state") in {"launching", "running"}
                            else worker.get("state")
                        ),
                        "started_at": worker["started_at"],
                        "worker_pid": worker.get("pid"),
                        "integration_probe": False,
                        "paper_order_created_count": 0,
                        "broker_write_count": 0,
                        "proof_credit_created_count": 0,
                        "live_capital_enabled": False,
                        "authority": authority_flags(),
                    }
                    active_groups.add(definition.concurrency_group)
                else:
                    result = _execute_service_synchronously(
                        definition,
                        executor=executor,
                        integration_probe=integration_probe,
                    )
                    completed_at = now_iso()
                    receipt = {
                        "schema_version": SCHEMA_VERSION,
                        "artifact_type": "qadam_operator_service_receipt",
                        "receipt_id": receipt_id,
                        "generated_at": generated_at,
                        "service_id": definition.service_id,
                        "state": result["state"],
                        "started_at": generated_at,
                        "completed_at": completed_at,
                        "duration_seconds": result["duration_seconds"],
                        "command_results": result["command_results"],
                        "integration_probe": integration_probe,
                        "paper_order_created_count": 0,
                        "broker_write_count": 0,
                        "proof_credit_created_count": 0,
                        "live_capital_enabled": False,
                        "authority": authority_flags(),
                    }
                    if result["state"] == "failed":
                        failure_class, retry = _record_failure(runtime, definition, receipt)
                        receipt["failure_class"] = failure_class
                        receipt["retry_scheduled"] = retry["retry_scheduled"]
                    else:
                        cycle_successes.add(definition.service_id)
                        _clear_circuit_after_success(runtime, definition.service_id)
                executed_count += 1
        _append_receipt(runtime, receipt)
        receipts.append(receipt)

    completed_states = {
        "completed",
        "completed_with_evidence_hold",
        "worker_started",
        "worker_completed",
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_dispatch_cycle",
        "generated_at": generated_at,
        "status": "passed"
        if all(
            receipt.get("state") in completed_states or receipt.get("state") == "skipped"
            for receipt in receipts
        )
        else "completed_with_failures",
        "integration_probe": integration_probe,
        "selected_service_count": len(selected),
        "receipt_count": len(receipts),
        "executed_count": executed_count,
        "completed_count": sum(receipt.get("state") in completed_states for receipt in receipts),
        "failed_count": sum(receipt.get("state") == "failed" for receipt in receipts),
        "skipped_count": sum(receipt.get("state") == "skipped" for receipt in receipts),
        "skip_reasons": sorted(
            {str(receipt.get("skip_reason")) for receipt in receipts if receipt.get("skip_reason")}
        ),
        "receipts": receipts,
        "paperops_invoked": any(
            receipt.get("service_id") == "guarded_paperops"
            and receipt.get("state") in completed_states
            for receipt in receipts
        ),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }


def run_operator_integration_probe(
    settings: Settings | None = None,
    *,
    executor: CommandExecutor | None = None,
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    cycle = dispatch_due_jobs(
        settings,
        force_due=True,
        integration_probe=True,
        service_ids=INTEGRATION_PROBE_SERVICES,
        executor=executor,
    )
    terminal = {"completed", "completed_with_evidence_hold"}
    states = {
        receipt["service_id"]: receipt.get("state")
        for receipt in cycle["receipts"]
        if receipt.get("service_id") in INTEGRATION_PROBE_SERVICES
    }
    all_executed = all(
        states.get(service_id) in terminal for service_id in INTEGRATION_PROBE_SERVICES
    )
    probe = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_integration_probe",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if all_executed and cycle["failed_count"] == 0 else "blocked",
        "required_services": list(INTEGRATION_PROBE_SERVICES),
        "required_service_count": len(INTEGRATION_PROBE_SERVICES),
        "executed_service_count": sum(state in terminal for state in states.values()),
        "executed_count": cycle["executed_count"],
        "completed_count": cycle["completed_count"],
        "failed_count": cycle["failed_count"],
        "skipped_count": cycle["skipped_count"],
        "skip_reasons": cycle["skip_reasons"],
        "service_states": states,
        "all_required_jobs_executed": all_executed,
        "projection_only_cycle": False,
        "paperops_invoked": cycle["paperops_invoked"],
        "research_lock_bypassed": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "live_capital_enabled": False,
        "cycle_receipt_ids": [receipt["receipt_id"] for receipt in cycle["receipts"]],
        "authority": authority_flags(),
    }
    AtomicArtifactStore(runtime).write_json(INTEGRATION_PROBE_ARTIFACT, probe)
    return probe


def execute_registered_worker(
    service_id: str,
    receipt_id: str,
    settings: Settings | None = None,
) -> int:
    runtime = runtime_dir(settings)
    definition = _service_definition(service_id)
    if not definition.long_running or definition.paperops_dependency:
        raise ValueError("operator_worker_service_not_permitted")
    result = _execute_service_synchronously(definition)
    completed_at = now_iso()
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_service_receipt",
        "receipt_id": receipt_id,
        "generated_at": completed_at,
        "service_id": service_id,
        "state": "worker_completed" if result["state"] != "failed" else "failed",
        "completed_at": completed_at,
        "duration_seconds": result["duration_seconds"],
        "command_results": result["command_results"],
        "worker_pid": os.getpid(),
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    if result["state"] == "failed":
        failure_class, retry = _record_failure(runtime, definition, receipt)
        receipt["failure_class"] = failure_class
        receipt["retry_scheduled"] = retry["retry_scheduled"]
    else:
        _clear_circuit_after_success(runtime, service_id)
    _append_receipt(runtime, receipt)
    records = _workers(runtime)
    records[service_id] = {
        **records.get(service_id, {}),
        "state": receipt["state"],
        "completed_at": completed_at,
        "exit_code": 0 if result["state"] != "failed" else 1,
    }
    _write_workers(runtime, records)
    return 0 if result["state"] != "failed" else 1


def repair_operator_service_circuit(
    service_id: str,
    settings: Settings | None = None,
    *,
    executor: CommandExecutor | None = None,
) -> dict[str, Any]:
    """Re-run one safe service and close its circuit only after success."""
    runtime = runtime_dir(settings)
    definition = _service_definition(service_id)
    if definition.paperops_dependency or definition.safe_retry_class not in {
        "idempotent_read",
        "deterministic_calculation",
    }:
        raise ValueError("operator_circuit_repair_service_not_permitted")
    prior = _circuit_breaker_state(runtime).get(service_id, {})
    if prior.get("state") != "open":
        return {
            "status": "not_required",
            "service_id": service_id,
            "prior_circuit_state": prior.get("state", "closed"),
            "paper_order_created_count": 0,
            "broker_write_count": 0,
            "live_capital_enabled": False,
            "authority": authority_flags(),
        }

    result = _execute_service_synchronously(definition, executor=executor)
    completed_at = now_iso()
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_service_receipt",
        "receipt_id": "operator-receipt:"
        + sha256_json(
            {
                "service_id": service_id,
                "completed_at": completed_at,
                "repair_attempt": True,
            }
        )[:24],
        "generated_at": completed_at,
        "completed_at": completed_at,
        "service_id": service_id,
        "state": result["state"],
        "repair_attempt": True,
        "prior_circuit_state": "open",
        "duration_seconds": result["duration_seconds"],
        "command_results": result["command_results"],
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    if result["state"] == "failed":
        failure_class, retry = _record_failure(runtime, definition, receipt)
        receipt["failure_class"] = failure_class
        receipt["retry_scheduled"] = retry["retry_scheduled"]
        receipt["status"] = "failed"
    else:
        _clear_circuit_after_success(runtime, service_id)
        receipt["status"] = "repaired"
    _append_receipt(runtime, receipt)
    return receipt


def _record_real_operator_session(runtime: Path, cycle: dict[str, Any]) -> None:
    generated_at = str(cycle.get("generated_at") or now_iso())
    parsed = _parse_timestamp(generated_at) or datetime.now(timezone.utc)
    release, release_effective = _paper_release_state(runtime)
    epoch = read_json(runtime / "current_paper_epoch.json")
    record = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_real_session_observation",
        "session_id": "operator-session:"
        + sha256_json({"generated_at": generated_at, "pid": os.getpid()})[:24],
        "generated_at": generated_at,
        "real_calendar_date": parsed.date().isoformat(),
        "real_elapsed_time": True,
        "simulated_elapsed_time_used": False,
        "dispatch_executed_count": int(cycle.get("executed_count") or 0),
        "dispatch_failed_count": int(cycle.get("failed_count") or 0),
        "paperops_invoked": cycle.get("paperops_invoked") is True,
        "paper_epoch_id": epoch.get("paper_epoch_id"),
        "paper_epoch_kind": epoch.get("paper_epoch_kind") or "legacy_test",
        "experimental_paper_release_effective": bool(
            release_effective
            and release.get("experimental_paper_release_effective") is True
        ),
        "release_binding_digest": release.get("binding_digest"),
        "policy_version": release.get("policy_version"),
        "risk_policy_version": release.get("risk_policy_version"),
        "operator_service_contract_hash": operator_service_contract_hash(),
        "paper_growth_trial_calendar_advanced": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "authority": authority_flags(),
    }
    append_jsonl_durable(runtime / SESSION_LEDGER_ARTIFACT, record)


def _real_soak_evidence(runtime: Path) -> dict[str, Any]:
    sessions = [
        record
        for record in read_jsonl(runtime / SESSION_LEDGER_ARTIFACT)
        if record.get("real_elapsed_time") is True
        and record.get("simulated_elapsed_time_used") is False
    ]
    observed_dates = sorted(
        {
            str(record.get("real_calendar_date"))
            for record in sessions
            if record.get("real_calendar_date")
        }
    )
    legacy = read_json(runtime / LEGACY_SOAK_ARTIFACT)
    legacy_count = (
        int(legacy.get("observed_soak_day_count") or 0)
        if legacy.get("simulated_elapsed_time_used") is not True
        else 0
    )
    observed_count = max(len(observed_dates), legacy_count)
    return {
        "observed_session_count": observed_count,
        "observed_calendar_dates": observed_dates,
        "required_session_count": 7,
        "complete": observed_count >= 7
        and (len(observed_dates) >= 7 or legacy.get("soak_complete") is True),
        "session_ledger_record_count": len(sessions),
        "simulated_elapsed_time_used": False,
    }


def _service_runtime_record(
    definition: ServiceDefinition,
    *,
    generated_at: str,
    research_lock_active: bool,
    release_effective: bool,
    process_running: bool,
    last_receipt: dict[str, Any] | None = None,
    last_successful_receipt: dict[str, Any] | None = None,
    circuit: dict[str, Any] | None = None,
    worker: dict[str, Any] | None = None,
) -> dict[str, Any]:
    paperops_blocked = definition.paperops_dependency and (
        research_lock_active or not release_effective
    )
    definition_record = definition.to_dict()
    definition_record["command_sequence"] = [
        _display_command(command) for command in definition.command_sequence
    ]
    definition_record["integration_probe_command_sequence"] = [
        _display_command(command) for command in definition.integration_probe_command_sequence
    ]
    receipt = last_receipt or {}
    successful_receipt = last_successful_receipt or {}
    worker_state = worker or {}
    generated_dt = _parse_timestamp(generated_at) or datetime.now(timezone.utc)
    idle_current = receipt.get("skip_reason") == "no_eligible_work"
    receipt_dt = _parse_timestamp(
        (
            receipt.get("completed_at") or receipt.get("generated_at")
            if idle_current
            else successful_receipt.get("completed_at")
            or successful_receipt.get("generated_at")
        )
    )
    receipt_age_seconds = (
        max(0.0, (generated_dt - receipt_dt).total_seconds()) if receipt_dt else None
    )
    freshness_state = (
        "not_run"
        if receipt_dt is None
        else "fresh"
        if receipt_age_seconds <= max(definition.cadence_seconds * 3, 900)
        else "stale"
    )
    return {
        **definition_record,
        "generated_at": generated_at,
        "service_process_running": process_running,
        "current_state": (
            "watch_only_research_lock"
            if paperops_blocked
            else "idle_no_eligible_work"
            if idle_current
            else "worker_running"
            if worker_state.get("state") == "running"
            else "monitor_ready"
            if not process_running
            else "supervised"
        ),
        "current_execution_allowed": process_running and not paperops_blocked,
        "paperops_watch_only": paperops_blocked,
        "last_receipt": {
            "receipt_id": receipt.get("receipt_id"),
            "state": receipt.get("state") or "not_run",
            "completed_at": receipt.get("completed_at"),
            "skip_reason": receipt.get("skip_reason"),
            "failure_class": receipt.get("failure_class"),
        },
        "next_due_at": _next_due_at(
            definition, receipt if idle_current else last_successful_receipt
        ),
        "freshness": {
            "state": freshness_state,
            "age_seconds": receipt_age_seconds,
            "stale_after_seconds": max(definition.cadence_seconds * 3, 900),
        },
        "circuit_breaker": circuit or {"state": "closed"},
        "worker": {
            "state": worker_state.get("state") or "not_running",
            "pid": worker_state.get("pid") if worker_state.get("state") == "running" else None,
            "resume_required": worker_state.get("resume_required") is True,
        },
        "live_capital_enabled": False,
        "broker_write_count": 0,
    }


def _lease_runtime_state(runtime: Path) -> dict[str, Any]:
    lease = read_json(runtime / LEASE_ARTIFACT)
    pid = int(lease.get("owner_pid") or 0)
    expires_at = _parse_timestamp(lease.get("expires_at"))
    active = (
        lease.get("status") == "active"
        and _pid_alive(pid)
        and (expires_at is None or expires_at > datetime.now(timezone.utc))
    )
    return {
        "lease_present": bool(lease),
        "lease_status": lease.get("status") or "not_acquired",
        "owner_pid": pid if active else None,
        "owner_process_alive": active,
        "single_instance_active": active,
        "duplicate_instance_prevention": "non_blocking_flock",
    }


def _repair_entry(
    *,
    category: str,
    summary: str,
    action: str,
    severity: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    material = {"category": category, "summary": summary, "evidence": evidence}
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_repair_request",
        "repair_request_id": f"operator-repair:{sha256_json(material)[:24]}",
        "category": category,
        "severity": severity,
        "summary": summary,
        "required_action": action,
        "evidence": evidence,
        "state": "operator_action_required"
        if category == "operator_action"
        else "repair_requested",
        "automatic_retry_allowed": False,
        "autonomous_code_edit_allowed": False,
        "secret_change_allowed": False,
        "authority_change_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
    }


def _build_repair_queue(
    runtime: Path,
    *,
    service_installed: bool,
    process_running: bool,
    generated_at: str,
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    if not service_installed:
        entries.append(
            _repair_entry(
                category="operator_action",
                severity="medium",
                summary="Operator service is prepared but not installed.",
                action="Review and run scripts/install_qadam_operator_launch_agent.sh, then bootstrap explicitly.",
                evidence={"launchd_label": LAUNCHD_LABEL, "target_exists": False},
            )
        )
    elif not process_running:
        entries.append(
            _repair_entry(
                category="operator_action",
                severity="high",
                summary="Operator service is installed but no active lease is visible.",
                action="Inspect launchctl status and logs before an explicit restart.",
                evidence={"launchd_label": LAUNCHD_LABEL, "target_exists": True},
            )
        )
    freshness = read_json(runtime / DASHBOARD_FRESHNESS_ARTIFACT)
    records = freshness.get("records") if isinstance(freshness.get("records"), list) else []
    stale = [record for record in records if record.get("freshness_state") in {"stale", "missing"}]
    if stale:
        entries.append(
            _repair_entry(
                category="stale_artifact",
                severity="medium",
                summary=f"{len(stale)} monitored operator artifacts need refresh or evidence repair.",
                action="Retry only known safe refreshes; keep affected decisions fail-closed until revalidated.",
                evidence={
                    "artifact_count": len(stale),
                    "artifacts": [record.get("artifact") for record in stale[:20]],
                },
            )
        )
    circuits = _circuit_breaker_state(runtime)
    for service_id, circuit in circuits.items():
        if circuit.get("state") != "open":
            continue
        failure_class = str(circuit.get("failure_class") or "code_defect")
        entries.append(
            _repair_entry(
                category=(
                    "operator_action"
                    if failure_class in {"credential_operator_action", "disk_resource_pressure"}
                    else failure_class
                ),
                severity="critical" if failure_class == "safety_violation" else "high",
                summary=f"{service_id} stopped after a {failure_class.replace('_', ' ')} failure.",
                action=(
                    "Review the safety violation before resetting this circuit."
                    if failure_class == "safety_violation"
                    else "Inspect the latest receipt, correct the stated cause, and explicitly reset the service circuit."
                ),
                evidence={
                    "service_id": service_id,
                    "failure_class": failure_class,
                    "last_failure_at": circuit.get("last_failure_at"),
                    "consecutive_failure_count": circuit.get("consecutive_failure_count"),
                },
            )
        )
    for service_id, worker in _workers(runtime).items():
        if worker.get("state") != "interrupted":
            continue
        entries.append(
            _repair_entry(
                category="interrupted_resumable_job",
                severity="medium",
                summary=f"{service_id} was interrupted before writing a terminal receipt.",
                action="Resume from the durable checkpoint through the operator dispatcher; do not restart completed partitions.",
                evidence={
                    "service_id": service_id,
                    "receipt_id": worker.get("receipt_id"),
                    "failure_class": worker.get("failure_class"),
                },
            )
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_repair_queue",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "status": "repair_queue_open" if entries else "repair_queue_clear",
        "open_request_count": len(entries),
        "critical_request_count": sum(entry["severity"] == "critical" for entry in entries),
        "requests": entries,
        "autonomous_code_edit_allowed": False,
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "authority": authority_flags(),
    }


def _build_interruption_probes(generated_at: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    retry_records: list[dict[str, Any]] = []
    for scenario, message, expected in SOAK_SCENARIOS:
        observed = classify_failure(
            message, status_code=429 if scenario == "provider_429" else None
        )
        policy = retry_policy(observed)
        safe = observed == expected and policy["paperops_retry_allowed"] is False
        record = {
            "scenario": scenario,
            "expected_failure_class": expected,
            "observed_failure_class": observed,
            "classification_passed": observed == expected,
            "safe_response_passed": safe,
            "retry_policy": policy,
            "checkpoint_required": scenario in {"laptop_sleep", "sigterm", "stale_lock"},
            "semantic_hypotheses_blocked": scenario == "local_llm_down",
            "frontier_review_deferred": scenario == "frontier_down",
            "classical_fallback_must_be_labelled": scenario == "quantum_fallback",
            "affected_work_stopped": scenario == "unsafe_route",
            "probe_only": True,
            "external_call_performed": False,
            "paper_order_created": False,
            "broker_write_count": 0,
        }
        records.append(record)
        retry_records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_operator_retry_probe",
                "retry_event_id": f"retry-probe:{sha256_json({'scenario': scenario, 'class': observed})[:24]}",
                "generated_at": generated_at,
                "service_id": "probe_suite",
                "scenario": scenario,
                "failure_class": observed,
                "probe_only": True,
                "retry_attempted": False,
                "policy": policy,
                "paper_order_created": False,
                "broker_write_count": 0,
                "authority": authority_flags(),
            }
        )
    passed = all(record["safe_response_passed"] for record in records)
    return (
        {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_operator_soak_test",
            "phase_id": PHASE_ID,
            "generated_at": generated_at,
            "status": "interruption_probes_passed" if passed else "interruption_probes_failed",
            "interruption_probe_count": len(records),
            "interruption_probe_pass_count": sum(
                record["safe_response_passed"] for record in records
            ),
            "all_interruption_probes_passed": passed,
            "scenarios": records,
            "multi_session_soak_complete": False,
            "real_elapsed_session_count": 0,
            "simulated_elapsed_time_used": False,
            "paper_growth_trial_calendar_advanced": False,
            "boundary": "Deterministic interruption probes validate response policy only. They do not simulate or satisfy the required real multi-session soak.",
            "public_safe": True,
            "read_only": True,
            "command_disabled": True,
            "authority": authority_flags(),
        },
        retry_records,
    )


def build_operator_service_state(
    settings: Settings | None = None,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    timestamp = generated_at or now_iso()
    lock = read_json(runtime / LOCK_ARTIFACT)
    release, release_effective = _paper_release_state(runtime)
    research = read_json(runtime / RESEARCH_STATUS_ARTIFACT)
    research_heartbeat = read_json(runtime / RESEARCH_HEARTBEAT_ARTIFACT)
    lease = _lease_runtime_state(runtime)
    process_running = lease["single_instance_active"]
    service_installed = LAUNCHD_TARGET.exists()
    research_lock_active = lock.get("status") == "active"
    latest_receipts = _last_receipts(runtime)
    successful_receipts = _last_successful_receipts(runtime)
    circuits = _circuit_breaker_state(runtime)
    worker_records = _workers(runtime)
    integration_probe = read_json(runtime / INTEGRATION_PROBE_ARTIFACT)
    service_records = [
        _service_runtime_record(
            definition,
            generated_at=timestamp,
            research_lock_active=research_lock_active,
            release_effective=release_effective,
            process_running=process_running,
            last_receipt=latest_receipts.get(definition.service_id),
            last_successful_receipt=successful_receipts.get(definition.service_id),
            circuit=circuits.get(definition.service_id),
            worker=worker_records.get(definition.service_id),
        )
        for definition in SERVICE_DEFINITIONS
    ]
    heartbeats = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_service_heartbeats",
        "phase_id": PHASE_ID,
        "generated_at": timestamp,
        "status": "running" if process_running else "ready_not_running",
        "operator_service": {
            "running": process_running,
            "lease": lease,
        },
        "research_supervisor": {
            "status": research.get("status") or "not_reported",
            "heartbeat_status": research_heartbeat.get("status") or "not_reported",
            "heartbeat_generated_at": research_heartbeat.get("generated_at"),
        },
        "services": service_records,
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "authority": authority_flags(),
    }
    repair_queue = _build_repair_queue(
        runtime,
        service_installed=service_installed,
        process_running=process_running,
        generated_at=timestamp,
    )
    soak, retry_records = _build_interruption_probes(timestamp)
    real_soak = _real_soak_evidence(runtime)
    soak["real_elapsed_session_count"] = real_soak["observed_session_count"]
    soak["real_elapsed_calendar_dates"] = real_soak["observed_calendar_dates"]
    soak["real_session_ledger_record_count"] = real_soak["session_ledger_record_count"]
    soak["multi_session_soak_complete"] = process_running and real_soak["complete"]
    soak["integration_probe_passed"] = integration_probe.get("status") == "passed"
    blockers: list[dict[str, Any]] = []
    if not service_installed:
        blockers.append(
            {
                "code": "operator_service_not_installed",
                "plain_english": "The unattended operator service has not been installed by the operator.",
                "next_action": "Review the generated launchd configuration, then install and bootstrap it explicitly.",
            }
        )
    if not process_running:
        blockers.append(
            {
                "code": "operator_service_not_running",
                "plain_english": "No active single-instance operator service lease is visible.",
                "next_action": "Install or inspect the service; do not infer operation from files alone.",
            }
        )
    if research_lock_active:
        blockers.append(
            {
                "code": "research_lock_active",
                "plain_english": "Research remains in watch-only mode while empirical evidence matures.",
                "next_action": "Complete the evidence and shadow gates before explicit lock release review.",
            }
        )
    if not soak["multi_session_soak_complete"]:
        blockers.append(
            {
                "code": "real_multi_session_soak_incomplete",
                "plain_english": "Interruption probes pass, but the real multi-session unattended soak is incomplete.",
                "next_action": "Run the installed service across real sessions without simulating elapsed time.",
            }
        )
    if integration_probe.get("status") != "passed":
        blockers.append(
            {
                "code": "real_due_job_integration_probe_incomplete",
                "plain_english": "The dispatcher has not yet proved the required research jobs execute through their approved runners.",
                "next_action": "Run scripts/run_qadam_operator_service.py --integration-probe and inspect the structured receipts.",
            }
        )
    why_not = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_why_not_running",
        "phase_id": PHASE_ID,
        "generated_at": timestamp,
        "status": "not_running" if not process_running else "running_with_blocks",
        "headline": (
            "Operator service is ready to install, but is not running."
            if not process_running
            else "Operator service is running with evidence or safety holds."
        ),
        "blocker_count": len(blockers),
        "blockers": blockers,
        "paperops_watch_only": research_lock_active or not release_effective,
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "authority": authority_flags(),
    }
    status = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_service_status",
        "phase_id": PHASE_ID,
        "generated_at": timestamp,
        "status": (
            "operator_service_running_research_only"
            if process_running
            else (
                "ready_installed_not_running_research_only"
                if service_installed
                else "ready_not_installed_research_only"
            )
        ),
        "implementation_ready": True,
        "operational_ready": process_running
        and service_installed
        and soak["multi_session_soak_complete"]
        and integration_probe.get("status") == "passed"
        and not repair_queue["critical_request_count"],
        "service_installed": service_installed,
        "service_running": process_running,
        "installation_is_explicit_operator_action": True,
        "automatic_install_or_bootstrap_allowed": False,
        "launchd": {
            "label": LAUNCHD_LABEL,
            "template": str(LAUNCHD_TEMPLATE.relative_to(ROOT)),
            "target": f"~/Library/LaunchAgents/{LAUNCHD_LABEL}.plist",
            "runner": str(RUNNER.relative_to(ROOT)),
            "worker_runner": str(WORKER_RUNNER.relative_to(ROOT)),
        },
        "single_instance": lease,
        "cadence_separation_enabled": True,
        "due_job_dispatcher_enabled": True,
        "projection_only_control_cycle": False,
        "approved_subprocess_entrypoints_only": True,
        "direct_broker_client_import_allowed": False,
        "service_count": len(service_records),
        "services": service_records,
        "liveness": {
            "process_running": process_running,
            "lease_active": lease["single_instance_active"],
        },
        "readiness": {
            "implementation_ready": True,
            "research_supervisor_contract_present": bool(research),
            "operator_installation_complete": service_installed,
            "real_soak_complete": soak["multi_session_soak_complete"],
            "integration_probe_passed": integration_probe.get("status") == "passed",
        },
        "freshness": {
            "fresh_service_count": sum(
                record.get("freshness", {}).get("state") == "fresh" for record in service_records
            ),
            "stale_service_count": sum(
                record.get("freshness", {}).get("state") == "stale" for record in service_records
            ),
            "not_run_service_count": sum(
                record.get("freshness", {}).get("state") == "not_run" for record in service_records
            ),
        },
        "research_lock_active": research_lock_active,
        "release_effective": release_effective,
        "paperops_watch_only": research_lock_active or not release_effective,
        "safe_retry_classes": [
            "transient_provider_network",
            "rate_limit",
            "stale_artifact",
            "interrupted_resumable_job",
        ],
        "failure_classes": list(FAILURE_CLASSES),
        "repair_queue": {
            "open_request_count": repair_queue["open_request_count"],
            "critical_request_count": repair_queue["critical_request_count"],
        },
        "interruption_probes_passed": soak["all_interruption_probes_passed"],
        "integration_probe": {
            "status": integration_probe.get("status") or "not_run",
            "all_required_jobs_executed": integration_probe.get("all_required_jobs_executed")
            is True,
            "executed_service_count": int(integration_probe.get("executed_service_count") or 0),
            "required_service_count": len(INTEGRATION_PROBE_SERVICES),
            "paperops_invoked": integration_probe.get("paperops_invoked") is True,
        },
        "paperops_delegation_probe": {
            "status": (
                "deferred_research_lock"
                if research_lock_active or not release_effective
                else "required_before_operational_ready"
            ),
            "canonical_wrapper": "scripts/run_paperops_autonomous_pass.py",
            "direct_broker_call_allowed": False,
            "automatic_retry_allowed": False,
        },
        "worker_count": len(worker_records),
        "active_worker_count": sum(
            record.get("state") == "running" for record in worker_records.values()
        ),
        "open_circuit_count": sum(record.get("state") == "open" for record in circuits.values()),
        "multi_session_soak_complete": soak["multi_session_soak_complete"],
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "public_safe": True,
        "read_only": True,
        "command_disabled": True,
        "authority": authority_flags(),
    }
    return {
        "status": status,
        "heartbeats": heartbeats,
        "repair_queue": repair_queue,
        "retry_records": retry_records,
        "soak": soak,
        "why_not_running": why_not,
    }


def validate_operator_service_state(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    status = state["status"]
    heartbeats = state["heartbeats"]
    repair_queue = state["repair_queue"]
    retry_records = state["retry_records"]
    soak = state["soak"]
    why_not = state["why_not_running"]
    if set(status.get("failure_classes", [])) != set(FAILURE_CLASSES):
        errors.append("operator_service_failure_taxonomy_incomplete")
    if status.get("service_count") != len(SERVICE_DEFINITIONS):
        errors.append("operator_service_registry_incomplete")
    if status.get("cadence_separation_enabled") is not True:
        errors.append("operator_service_cadence_separation_missing")
    if status.get("due_job_dispatcher_enabled") is not True:
        errors.append("operator_service_due_job_dispatcher_missing")
    if status.get("projection_only_control_cycle") is not False:
        errors.append("operator_service_still_projection_only")
    if status.get("direct_broker_client_import_allowed") is not False:
        errors.append("operator_service_direct_broker_client_allowed")
    required_registry_fields = {
        "command_sequence",
        "cadence_seconds",
        "timeout_seconds",
        "dependencies",
        "concurrency_group",
        "lock_requirement",
        "safety_mode",
        "last_receipt",
        "next_due_at",
        "freshness",
        "safe_retry_class",
    }
    for service in status.get("services", []):
        if not required_registry_fields.issubset(service):
            errors.append(f"operator_service_registry_fields_missing:{service.get('service_id')}")
        for command in service.get("command_sequence", []):
            if not isinstance(command, list) or len(command) < 2:
                errors.append(f"operator_service_command_invalid:{service.get('service_id')}")
                continue
            script_path = ROOT / str(command[1])
            if not script_path.is_file():
                errors.append(f"operator_service_runner_missing:{service.get('service_id')}")
    paperops = next(
        (
            record
            for record in status.get("services", [])
            if record.get("service_id") == "guarded_paperops"
        ),
        {},
    )
    if (
        status.get("research_lock_active") is True
        and paperops.get("current_execution_allowed") is not False
    ):
        errors.append("operator_service_paperops_not_fail_closed")
    if paperops.get("command_sequence") != [
        [".venv/bin/python", "scripts/run_paperops_autonomous_pass.py"]
    ]:
        errors.append("operator_service_paperops_not_exact_guarded_wrapper")
    paperops_probe = status.get("paperops_delegation_probe", {})
    if paperops_probe.get("direct_broker_call_allowed") is not False:
        errors.append("operator_service_paperops_probe_direct_broker_allowed")
    if paperops_probe.get("automatic_retry_allowed") is not False:
        errors.append("operator_service_paperops_probe_retry_allowed")
    lifecycle = next(
        (
            record
            for record in status.get("services", [])
            if record.get("service_id") == "paper_lifecycle_poll"
        ),
        {},
    )
    if lifecycle.get("paperops_dependency") is not False:
        errors.append("operator_service_readonly_lifecycle_blocked_by_research_lock")
    if (
        status.get("single_instance", {}).get("duplicate_instance_prevention")
        != "non_blocking_flock"
    ):
        errors.append("operator_service_duplicate_prevention_missing")
    if (
        not LAUNCHD_TEMPLATE.is_file()
        or not INSTALLER.is_file()
        or not RUNNER.is_file()
        or not WORKER_RUNNER.is_file()
    ):
        errors.append("operator_service_installation_assets_missing")
    if soak.get("all_interruption_probes_passed") is not True:
        errors.append("operator_service_interruption_probe_failed")
    if soak.get("simulated_elapsed_time_used") is not False:
        errors.append("operator_service_simulated_elapsed_time_used")
    if (
        soak.get("multi_session_soak_complete") is True
        and soak.get("real_elapsed_session_count", 0) < 7
    ):
        errors.append("operator_service_soak_completed_without_real_sessions")
    integration = status.get("integration_probe", {})
    if integration.get("status") != "passed":
        errors.append("operator_service_integration_probe_not_passed")
    else:
        if integration.get("all_required_jobs_executed") is not True:
            errors.append("operator_service_integration_probe_false_pass")
        if integration.get("executed_service_count") != len(INTEGRATION_PROBE_SERVICES):
            errors.append("operator_service_integration_probe_service_count_mismatch")
        if integration.get("paperops_invoked") is not False:
            errors.append("operator_service_integration_probe_invoked_paperops")
    for record in retry_records:
        policy = record.get("policy", {})
        if policy.get("paperops_retry_allowed") is not False:
            errors.append("operator_service_retry_can_repeat_paperops")
        if policy.get("broker_write_retry_allowed") is not False:
            errors.append("operator_service_retry_can_write_broker")
        if record.get("retry_attempted") is not False or record.get("probe_only") is not True:
            errors.append("operator_service_probe_executed_external_retry")
    for request in repair_queue.get("requests", []):
        if request.get("autonomous_code_edit_allowed") is not False:
            errors.append("operator_service_repair_can_edit_code")
        if not request.get("summary") or not request.get("required_action"):
            errors.append("operator_service_repair_not_specific")
    for payload, prefix in (
        (status, "operator_service"),
        (heartbeats, "operator_heartbeats"),
        (repair_queue, "operator_repair_queue"),
        (soak, "operator_soak"),
        (why_not, "operator_why_not_running"),
    ):
        errors.extend(validate_authority(payload.get("authority", {}), prefix=prefix))
    if status.get("paper_order_created_count") != 0 or status.get("broker_write_count") != 0:
        errors.append("operator_service_unauthorized_execution_side_effect")
    return unique_errors(errors)


def build_and_write_operator_service(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    state = build_operator_service_state(settings)
    errors = validate_operator_service_state(state)
    store = AtomicArtifactStore(runtime)
    store.write_json(STATUS_ARTIFACT, state["status"])
    store.write_json(HEARTBEATS_ARTIFACT, state["heartbeats"])
    store.write_json(REPAIR_QUEUE_ARTIFACT, state["repair_queue"])
    existing_retry_records = read_jsonl(runtime / RETRY_LEDGER_ARTIFACT)
    retry_ids = {record.get("retry_event_id") for record in existing_retry_records}
    merged_retry_records = [*existing_retry_records]
    merged_retry_records.extend(
        record for record in state["retry_records"] if record.get("retry_event_id") not in retry_ids
    )
    store.write_jsonl(RETRY_LEDGER_ARTIFACT, merged_retry_records)
    store.write_json(SOAK_ARTIFACT, state["soak"])
    store.write_json(WHY_NOT_RUNNING_ARTIFACT, state["why_not_running"])
    if not (runtime / RECEIPTS_ARTIFACT).exists():
        store.write_jsonl(RECEIPTS_ARTIFACT, [])
    if not (runtime / SESSION_LEDGER_ARTIFACT).exists():
        store.write_jsonl(SESSION_LEDGER_ARTIFACT, [])
    if not (runtime / CIRCUIT_BREAKERS_ARTIFACT).exists():
        _write_circuit_breakers(runtime, {})
    if not (runtime / WORKERS_ARTIFACT).exists():
        _write_workers(runtime, {})
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_operator_service_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "implementation_ready": not errors,
        "operational_ready": state["status"]["operational_ready"],
        "service_installed": state["status"]["service_installed"],
        "service_running": state["status"]["service_running"],
        "service_count": state["status"]["service_count"],
        "due_job_dispatcher_enabled": state["status"]["due_job_dispatcher_enabled"],
        "projection_only_control_cycle": state["status"]["projection_only_control_cycle"],
        "integration_probe_passed": state["status"]["integration_probe"]["status"] == "passed",
        "integration_probe_executed_service_count": state["status"]["integration_probe"][
            "executed_service_count"
        ],
        "integration_probe_required_service_count": len(INTEGRATION_PROBE_SERVICES),
        "service_receipt_count": len(read_jsonl(runtime / RECEIPTS_ARTIFACT)),
        "active_worker_count": state["status"]["active_worker_count"],
        "open_circuit_count": state["status"]["open_circuit_count"],
        "fresh_service_count": state["status"]["freshness"]["fresh_service_count"],
        "stale_service_count": state["status"]["freshness"]["stale_service_count"],
        "not_run_service_count": state["status"]["freshness"]["not_run_service_count"],
        "paperops_delegation_probe_status": state["status"]["paperops_delegation_probe"]["status"],
        "failure_class_count": len(state["status"]["failure_classes"]),
        "interruption_probe_count": state["soak"]["interruption_probe_count"],
        "interruption_probe_pass_count": state["soak"]["interruption_probe_pass_count"],
        "multi_session_soak_complete": state["soak"]["multi_session_soak_complete"],
        "repair_request_count": state["repair_queue"]["open_request_count"],
        "critical_repair_request_count": state["repair_queue"]["critical_request_count"],
        "paperops_watch_only": state["status"]["paperops_watch_only"],
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    store.write_json(CHECK_ARTIFACT, checks)
    return state, checks, errors


def run_safe_operator_control_cycle(
    settings: Settings | None = None,
    *,
    integration_probe: bool = False,
    force_due: bool = False,
    service_ids: tuple[str, ...] | None = None,
    executor: CommandExecutor | None = None,
    max_jobs: int = 4,
) -> dict[str, Any]:
    """Dispatch approved due jobs, then refresh read-only status projections."""

    from orchestrator.qadam_operator_dashboard import build_and_write_operator_dashboard
    from orchestrator.qadam_research_supervisor import build_and_write_research_supervisor
    from orchestrator.qadam_self_healing_supervisor import build_and_write_self_healing_state

    dispatch = (
        run_operator_integration_probe(settings, executor=executor)
        if integration_probe
        else dispatch_due_jobs(
            settings,
            force_due=force_due,
            service_ids=service_ids,
            executor=executor,
            max_jobs=max_jobs,
        )
    )
    research = build_and_write_research_supervisor(settings)
    self_healing = build_and_write_self_healing_state(settings, perform_refresh=False)
    dashboard = build_and_write_operator_dashboard(settings)
    state, checks, errors = build_and_write_operator_service(settings)
    dispatch_failed_count = int(dispatch.get("failed_count") or 0)
    if integration_probe and dispatch.get("status") != "passed":
        dispatch_failed_count += 1
    error_count = (
        len(research[2])
        + len(self_healing[2])
        + len(dashboard[2])
        + len(errors)
        + dispatch_failed_count
    )
    if not integration_probe:
        _record_real_operator_session(runtime_dir(settings), dispatch)
    return {
        "generated_at": now_iso(),
        "status": "passed" if error_count == 0 else "blocked",
        "dispatch_status": dispatch.get("status"),
        "dispatch_executed_count": int(dispatch.get("executed_count") or 0),
        "dispatch_completed_count": int(dispatch.get("completed_count") or 0),
        "dispatch_failed_count": dispatch_failed_count,
        "dispatch_skipped_count": int(dispatch.get("skipped_count") or 0),
        "dispatch_skip_reasons": dispatch.get("skip_reasons") or [],
        "integration_probe": integration_probe,
        "projection_only_cycle": False,
        "validation_error_count": error_count,
        "research_validation_error_count": len(research[2]),
        "self_healing_validation_error_count": len(self_healing[2]),
        "dashboard_validation_error_count": len(dashboard[2]),
        "operator_service_validation_error_count": len(errors),
        "service_running": state["status"]["service_running"],
        "integration_probe_passed": checks["integration_probe_passed"],
        "paper_order_created_count": checks["paper_order_created_count"],
        "broker_write_count": checks["broker_write_count"],
        "authority": authority_flags(),
    }
