"""Audited Phase 11 release into the canonical guarded PaperOps route.

The default path is diagnostic only.  An actual launch requires a clean epoch,
every pre-launch operating gate, explicit operator approval, and a paused
operator service.  This module never calls a broker directly; the only allowed
execution subprocess is the canonical PaperOps wrapper.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

from orchestrator.config import Settings
from orchestrator.paper_account import ALPACA_PAPER_BASE_URL
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_experimental_paper_policy import (
    POLICY_ARTIFACT as EXPERIMENTAL_POLICY_ARTIFACT,
    POLICY_VERSION as EXPERIMENTAL_POLICY_VERSION,
)
from orchestrator.qadam_experimental_policy_amendment import (
    AMENDMENT_ARTIFACT as EXPERIMENTAL_POLICY_AMENDMENT_ARTIFACT,
    validate_policy_amendment,
)
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    append_jsonl_durable,
    authority_flags,
    file_sha256,
    now_iso,
    public_path,
    read_json,
    runtime_dir,
    sha256_json,
    unique_errors,
    validate_authority,
    write_json_atomic,
)
from orchestrator.secrets import secret_value

SCHEMA_VERSION = "qadam_guarded_paper_launch.v1"
APPROVAL_ARTIFACT = "qadam_clean_epoch_release_approval.json"
READINESS_ARTIFACT = "qadam_guarded_paper_launch_readiness.json"
RECEIPT_ARTIFACT = "qadam_guarded_paper_launch_receipt.json"
CHECK_ARTIFACT = "qadam_guarded_paper_launch_checks.json"
DRY_RUN_ARTIFACT = "qadam_guarded_paper_launch_dry_run.json"
EXPERIMENTAL_APPROVAL_ARTIFACT = "qadam_experimental_paper_release_approval.json"
EXPERIMENTAL_READINESS_ARTIFACT = "qadam_experimental_paper_release_readiness.json"
EXPERIMENTAL_CHECK_ARTIFACT = "qadam_experimental_paper_release_checks.json"
TRIAL_CALENDAR_ARTIFACT = "qadam_paper_trial_calendar.json"

FINAL_CERTIFICATION_ARTIFACT = (
    "qadam_clean_epoch_operational_readiness_certification.json"
)
EPOCH_ARTIFACT = "current_paper_epoch.json"
CUTOVER_RECEIPT_ARTIFACT = "qadam_clean_epoch_cutover_receipt.json"
DASHBOARD_EPOCH_ARTIFACT = "qadam_dashboard_epoch_isolation.json"
EDGE_ARTIFACT = "qadam_edge_registry_v3.json"
SHADOW_ARTIFACT = "qadam_forward_shadow_checks.json"
SOAK_ARTIFACT = "qadam_operator_soak_v2.json"
ROUTER_ARTIFACT = "qadam_router_v3_paperops_checks.json"
RISK_ARTIFACT = "qadam_portfolio_risk_state.json"
PAPEROPS_ARTIFACT = "paperops_autonomous_pass_summary.json"
SERVICE_ARTIFACT = "qadam_operator_service_checks.json"
LOCK_ARTIFACT = "qadam_long_backtest_lock.json"
LOCK_HISTORY_ARTIFACT = "qadam_long_backtest_lock_history.jsonl"

CANONICAL_WRAPPER = "scripts/run_paperops_autonomous_pass.py"
PAPER_BASE_URL = ALPACA_PAPER_BASE_URL
EXPERIMENTAL_APPROVAL_TTL_SECONDS = 15 * 60


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


def _fresh(payload: dict[str, Any], *, seconds: int) -> bool:
    generated = _parse_timestamp(payload.get("generated_at"))
    if generated is None:
        return False
    age_seconds = (datetime.now(timezone.utc) - generated).total_seconds()
    return 0 <= age_seconds <= seconds


def _version_ref(runtime: Path, filename: str) -> dict[str, Any]:
    path = runtime / filename
    payload = read_json(path)
    return {
        "artifact": public_path(path),
        "schema_version": payload.get("schema_version"),
        "policy_version": payload.get("policy_version"),
        "status": payload.get("status"),
        "sha256": file_sha256(path),
    }


def build_guarded_launch_readiness(
    settings: Settings | None = None,
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    active_settings = settings or Settings.from_env()
    cert = read_json(runtime / FINAL_CERTIFICATION_ARTIFACT)
    epoch = read_json(runtime / EPOCH_ARTIFACT)
    cutover = read_json(runtime / CUTOVER_RECEIPT_ARTIFACT)
    dashboard = read_json(runtime / DASHBOARD_EPOCH_ARTIFACT)
    edge = read_json(runtime / EDGE_ARTIFACT)
    shadow = read_json(runtime / SHADOW_ARTIFACT)
    soak = read_json(runtime / SOAK_ARTIFACT)
    router = read_json(runtime / ROUTER_ARTIFACT)
    service = read_json(runtime / SERVICE_ARTIFACT)
    lock = read_json(runtime / LOCK_ARTIFACT)
    configured_broker_url = str(
        secret_value("ALPACA_BASE_URL", active_settings) or PAPER_BASE_URL
    ).rstrip("/")
    paper_broker_url_valid = configured_broker_url == PAPER_BASE_URL.rstrip("/")
    blockers: list[str] = []
    if cert.get("operational_launch_ready") is not True:
        blockers.append("clean_epoch_prelaunch_certification_not_passed")
    if epoch.get("paper_epoch_kind") != "clean_operator_epoch":
        blockers.append("clean_operator_epoch_not_active")
    if abs(float(epoch.get("starting_balance") or 0) - 100000.0) > 0.01:
        blockers.append("clean_epoch_starting_balance_not_100000_usd")
    if epoch.get("account_currency") != "USD":
        blockers.append("clean_epoch_currency_not_usd")
    if cutover.get("cutover_executed") is not True:
        blockers.append("transactional_cutover_not_executed")
    if dashboard.get("status") != "passed":
        blockers.append("clean_epoch_dashboard_isolation_not_passed")
    if int(edge.get("validated_edge_count") or 0) <= 0:
        blockers.append("no_validated_edge_available")
    if shadow.get("promotion_ready") is not True:
        blockers.append("real_forward_shadow_not_promotion_ready")
    if soak.get("soak_complete") is not True:
        blockers.append("seven_real_session_soak_incomplete")
    if router.get("status") != "passed":
        blockers.append("router_v3_checks_not_passed")
    if not paper_broker_url_valid:
        blockers.append("alpaca_base_url_is_not_guarded_paper_endpoint")
    if not (
        lock.get("status") == "active"
        and lock.get("paperops_watch_only_mode") is True
    ):
        blockers.append("research_lock_not_active_before_release")
    blockers = unique_errors(blockers)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_guarded_paper_launch_readiness",
        "generated_at": now_iso(),
        "status": "ready_for_explicit_operator_release" if not blockers else "blocked",
        "launch_ready": not blockers,
        "operator_service_running": service.get("service_running") is True,
        "operator_service_pause_required": service.get("service_running") is True,
        "canonical_wrapper": CANONICAL_WRAPPER,
        "direct_broker_call_allowed": False,
        "paper_broker_base_url_required": PAPER_BASE_URL,
        "paper_broker_base_url_verified": paper_broker_url_valid,
        "live_capital_enabled": False,
        "validated_edge_count": int(edge.get("validated_edge_count") or 0),
        "paper_epoch_id": epoch.get("paper_epoch_id"),
        "paper_epoch_kind": epoch.get("paper_epoch_kind"),
        "starting_balance": epoch.get("starting_balance"),
        "account_currency": epoch.get("account_currency"),
        "blocker_count": len(blockers),
        "blockers": blockers,
        "version_refs": {
            "strategy": _version_ref(runtime, "qadam_strategy_foundry_v3.json"),
            "risk_policy": _version_ref(runtime, RISK_ARTIFACT),
            "router": _version_ref(runtime, ROUTER_ARTIFACT),
            "paperops": _version_ref(runtime, PAPEROPS_ARTIFACT),
            "paper_epoch": _version_ref(runtime, EPOCH_ARTIFACT),
        },
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "authority": authority_flags(),
    }


def build_release_approval(
    readiness: dict[str, Any],
    *,
    approval_requested: bool,
) -> dict[str, Any]:
    approved = bool(approval_requested and readiness.get("launch_ready") is True)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_clean_epoch_release_approval",
        "generated_at": now_iso(),
        "status": "approved" if approved else "not_approved",
        "operator_approval_requested": approval_requested,
        "operator_approved": approved,
        "approval_rejected_by_safety_gates": bool(
            approval_requested and readiness.get("launch_ready") is not True
        ),
        "paper_only_release": approved,
        "live_capital_release": False,
        "paper_epoch_id": readiness.get("paper_epoch_id"),
        "starting_balance": readiness.get("starting_balance"),
        "account_currency": readiness.get("account_currency"),
        "version_refs": readiness.get("version_refs", {}),
        "blockers": readiness.get("blockers", []),
        "canonical_wrapper": CANONICAL_WRAPPER,
        "direct_broker_call_allowed": False,
        "authority": authority_flags(),
    }


def _released_lock(lock: dict[str, Any], approval: dict[str, Any]) -> dict[str, Any]:
    released = dict(lock)
    released.update(
        {
            "status": "released",
            "released_at": now_iso(),
            "release_mode": "explicit_operator_approved_clean_paper_epoch",
            "release_approval_artifact": f"data/runtime/{APPROVAL_ARTIFACT}",
            "release_approval_epoch_id": approval.get("paper_epoch_id"),
            "paperops_autonomous_runner_paused": False,
            "paperops_watch_only_mode": False,
            "dashboard_deploy_should_pause": False,
            "daily_learning_live_runner_should_pause": False,
            "release_requires_explicit_operator_action": True,
        }
    )
    return released


def _lock_history_event(
    *,
    state: str,
    approval: dict[str, Any],
    detail: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_long_backtest_lock_release_event",
        "generated_at": now_iso(),
        "state": state,
        "paper_epoch_id": approval.get("paper_epoch_id"),
        "approval_artifact": f"data/runtime/{APPROVAL_ARTIFACT}",
        "detail": detail,
        "live_capital_enabled": False,
    }


def execute_guarded_paper_launch(
    settings: Settings | None = None,
    *,
    explicit_operator_approval: bool = False,
    execute: bool = False,
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    readiness = build_guarded_launch_readiness(settings)
    approval = build_release_approval(
        readiness, approval_requested=explicit_operator_approval
    )
    store.write_json(READINESS_ARTIFACT, readiness)
    receipt: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_guarded_paper_launch_receipt",
        "generated_at": now_iso(),
        "status": "not_executed",
        "launch_executed": False,
        "canonical_wrapper": CANONICAL_WRAPPER,
        "canonical_wrapper_invoked": False,
        "direct_broker_call_count": 0,
        "paper_epoch_id": readiness.get("paper_epoch_id"),
        "operator_service_resume_required": False,
        "live_capital_enabled": False,
        "blockers": list(readiness.get("blockers", [])),
        "authority": authority_flags(),
    }
    if not execute:
        receipt["status"] = "dry_run_ready" if readiness["launch_ready"] else "blocked"
        receipt["dry_run_only"] = True
        store.write_json(DRY_RUN_ARTIFACT, receipt)
        return receipt
    store.write_json(APPROVAL_ARTIFACT, approval)
    execution_blockers = list(readiness.get("blockers", []))
    if approval.get("operator_approved") is not True:
        execution_blockers.append("explicit_operator_release_approval_missing")
    if readiness.get("operator_service_running") is True:
        execution_blockers.append("operator_service_must_be_paused_before_lock_release")
    execution_blockers = unique_errors(execution_blockers)
    if execution_blockers:
        receipt.update({"status": "blocked", "blockers": execution_blockers})
        store.write_json(RECEIPT_ARTIFACT, receipt)
        return receipt

    lock_path = runtime / LOCK_ARTIFACT
    lock_history_path = runtime / LOCK_HISTORY_ARTIFACT
    original_lock = read_json(lock_path)
    released_lock = _released_lock(original_lock, approval)
    write_json_atomic(lock_path, released_lock)
    append_jsonl_durable(
        lock_history_path,
        _lock_history_event(
            state="released",
            approval=approval,
            detail="Research lock released for the clean paper epoch before one canonical PaperOps pass.",
        ),
    )
    try:
        completed = subprocess.run(
            [sys.executable, str(ROOT / CANONICAL_WRAPPER)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=1800,
            env=os.environ.copy(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        write_json_atomic(lock_path, original_lock)
        append_jsonl_durable(
            lock_history_path,
            _lock_history_event(
                state="release_rolled_back",
                approval=approval,
                detail="The initial canonical PaperOps pass could not complete; watch-only research lock restored.",
            ),
        )
        receipt.update(
            {
                "status": "launch_failed_relocked",
                "canonical_wrapper_invoked": True,
                "canonical_wrapper_returncode": None,
                "execution_error_class": exc.__class__.__name__,
                "blockers": ["initial_canonical_paperops_pass_did_not_complete"],
            }
        )
        store.write_json(RECEIPT_ARTIFACT, receipt)
        return receipt
    if completed.returncode != 0:
        write_json_atomic(lock_path, original_lock)
        append_jsonl_durable(
            lock_history_path,
            _lock_history_event(
                state="release_rolled_back",
                approval=approval,
                detail="The initial canonical PaperOps pass failed; watch-only research lock restored.",
            ),
        )
        receipt.update(
            {
                "status": "launch_failed_relocked",
                "canonical_wrapper_invoked": True,
                "canonical_wrapper_returncode": completed.returncode,
                "stdout_tail": completed.stdout.splitlines()[-20:],
                "stderr_tail": completed.stderr.splitlines()[-20:],
                "blockers": ["initial_canonical_paperops_pass_failed"],
            }
        )
    else:
        receipt.update(
            {
                "status": "initial_canonical_pass_complete",
                "launch_executed": True,
                "canonical_wrapper_invoked": True,
                "canonical_wrapper_returncode": 0,
                "operator_service_resume_required": True,
                "blockers": [],
            }
        )
    store.write_json(RECEIPT_ARTIFACT, receipt)
    return receipt


def build_guarded_launch_checks(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    readiness = build_guarded_launch_readiness(settings)
    approval = read_json(runtime / APPROVAL_ARTIFACT)
    receipt = read_json(runtime / RECEIPT_ARTIFACT)
    service = read_json(runtime / SERVICE_ARTIFACT)
    lock = read_json(runtime / LOCK_ARTIFACT)
    initial_complete = bool(
        receipt.get("launch_executed") is True
        and receipt.get("canonical_wrapper_invoked") is True
        and receipt.get("canonical_wrapper_returncode") == 0
    )
    continuously_running = bool(
        initial_complete
        and lock.get("status") == "released"
        and lock.get("paperops_watch_only_mode") is False
        and service.get("service_running") is True
    )
    errors: list[str] = []
    if receipt.get("canonical_wrapper_invoked") is True and receipt.get(
        "canonical_wrapper"
    ) != CANONICAL_WRAPPER:
        errors.append("noncanonical_paperops_wrapper_invoked")
    if receipt.get("direct_broker_call_count", 0) != 0:
        errors.append("guarded_launch_direct_broker_call_detected")
    if approval.get("operator_approved") is True and not approval.get(
        "paper_only_release"
    ):
        errors.append("release_approval_not_paper_only")
    if approval.get("live_capital_release") is True:
        errors.append("release_approval_enabled_live_capital")
    errors.extend(validate_authority(readiness.get("authority", {}), prefix="launch_readiness"))
    if approval:
        errors.extend(validate_authority(approval.get("authority", {}), prefix="launch_approval"))
    if receipt:
        errors.extend(validate_authority(receipt.get("authority", {}), prefix="launch_receipt"))
    errors = unique_errors(errors)
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_guarded_paper_launch_checks",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "implementation_ready": not errors,
        "launch_readiness_state": readiness.get("status"),
        "operator_approved": approval.get("operator_approved") is True,
        "initial_canonical_pass_complete": initial_complete,
        "guarded_paper_operation_running": continuously_running,
        "launch_state": (
            "launched_guarded_paper_only"
            if continuously_running
            else "initial_pass_complete_service_resume_required"
            if initial_complete
            else "waiting_for_release_gates"
        ),
        "canonical_wrapper_only": True,
        "direct_broker_call_count": 0,
        "paper_order_created_by_launch_module_count": 0,
        "broker_write_created_by_launch_module_count": 0,
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    AtomicArtifactStore(runtime).write_json(READINESS_ARTIFACT, readiness)
    AtomicArtifactStore(runtime).write_json(CHECK_ARTIFACT, checks)
    return checks, errors


def build_experimental_guarded_launch_readiness(
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Return the narrow release gate for the clean experimental epoch."""

    runtime = runtime_dir(settings)
    active_settings = settings or Settings.from_env()
    epoch = read_json(runtime / EPOCH_ARTIFACT)
    cutover = read_json(runtime / CUTOVER_RECEIPT_ARTIFACT)
    dashboard = read_json(runtime / DASHBOARD_EPOCH_ARTIFACT)
    broker = read_json(runtime / "qadam_clean_broker_account_preflight.json")
    policy = read_json(runtime / "qadam_experimental_paper_policy.json")
    eligibility = read_json(runtime / "qadam_experimental_paper_eligibility_checks.json")
    router = read_json(runtime / ROUTER_ARTIFACT)
    risk_policy = read_json(runtime / "qadam_portfolio_policy.json")
    soak = read_json(runtime / SOAK_ARTIFACT)
    service = read_json(runtime / SERVICE_ARTIFACT)
    lock = read_json(runtime / LOCK_ARTIFACT)
    configured_broker_url = str(
        secret_value("ALPACA_BASE_URL", active_settings) or PAPER_BASE_URL
    ).rstrip("/")
    paper_broker_url_valid = configured_broker_url == PAPER_BASE_URL.rstrip("/")
    blockers: list[str] = []
    if epoch.get("paper_epoch_kind") != "clean_experimental_operator_epoch":
        blockers.append("clean_experimental_epoch_not_active")
    if abs(float(epoch.get("starting_balance") or 0) - 100000.0) > 0.01:
        blockers.append("clean_epoch_starting_balance_not_100000_usd")
    if epoch.get("account_currency") != "USD":
        blockers.append("clean_epoch_currency_not_usd")
    if cutover.get("cutover_executed") is not True or cutover.get(
        "cutover_mode"
    ) != "experimental_unvalidated":
        blockers.append("experimental_cutover_not_executed")
    if cutover.get("paper_epoch_id") != epoch.get("paper_epoch_id"):
        blockers.append("cutover_epoch_identity_mismatch")
    if broker.get("preflight_passed") is not True or not _fresh(broker, seconds=300):
        blockers.append("fresh_clean_broker_preflight_not_passed")
    if broker.get("broker_account_fingerprint") != epoch.get(
        "broker_account_fingerprint"
    ):
        blockers.append("clean_broker_fingerprint_mismatch")
    if dashboard.get("status") != "passed":
        blockers.append("clean_epoch_dashboard_isolation_not_passed")
    if policy.get("policy_version") != EXPERIMENTAL_POLICY_VERSION:
        blockers.append("experimental_policy_version_not_frozen")
    if eligibility.get("status") != "passed":
        blockers.append("experimental_eligibility_checks_not_passed")
    if router.get("status") != "passed":
        blockers.append("router_v3_checks_not_passed")
    if risk_policy.get("policy_version") != "qadam-paper-portfolio-risk.2-frozen":
        blockers.append("risk_policy_version_not_frozen")
    if float(
        risk_policy.get("risk_budget", {}).get("max_position_notional_usd") or 0
    ) != 5000.0:
        blockers.append("risk_policy_absolute_trade_ceiling_not_5000_usd")
    if not paper_broker_url_valid:
        blockers.append("alpaca_base_url_is_not_guarded_paper_endpoint")
    if not (
        lock.get("status") == "active"
        and lock.get("paperops_watch_only_mode") is True
    ):
        blockers.append("research_lock_not_active_before_experimental_release")
    if epoch.get("paper_growth_trial_calendar_started") is True:
        blockers.append("paper_trial_already_started_before_release")
    blockers = unique_errors(blockers)
    version_refs = {
        "experimental_policy": _version_ref(
            runtime, "qadam_experimental_paper_policy.json"
        ),
        "risk_policy": _version_ref(runtime, "qadam_portfolio_policy.json"),
        "router": _version_ref(runtime, ROUTER_ARTIFACT),
        "eligibility": _version_ref(
            runtime, "qadam_experimental_paper_eligibility_checks.json"
        ),
        "paper_epoch": _version_ref(runtime, EPOCH_ARTIFACT),
        "broker_preflight": _version_ref(
            runtime, "qadam_clean_broker_account_preflight.json"
        ),
    }
    return {
        "schema_version": "qadam_experimental_paper_release.v1",
        "artifact_type": "qadam_experimental_paper_release_readiness",
        "generated_at": now_iso(),
        "status": "ready_for_explicit_operator_release" if not blockers else "blocked",
        "experimental_paper_release_ready": not blockers,
        "experimental_paper_release_effective": False,
        "experimental_policy_operator_approved": False,
        "experimental_risk_policy_operator_approved": False,
        "validated_strategy_promotion_ready": False,
        "live_capital_release_allowed": False,
        "validated_edge_required": False,
        "completed_forward_shadow_required_for_launch": False,
        "seven_session_soak_required_for_launch": False,
        "unattended_reliability_certified": soak.get("soak_complete") is True,
        "operator_service_running": service.get("service_running") is True,
        "operator_service_pause_required": service.get("service_running") is True,
        "paper_epoch_id": epoch.get("paper_epoch_id"),
        "broker_account_fingerprint": epoch.get("broker_account_fingerprint"),
        "policy_version": policy.get("policy_version"),
        "risk_policy_version": risk_policy.get("policy_version"),
        "canonical_wrapper": CANONICAL_WRAPPER,
        "paper_broker_base_url_verified": paper_broker_url_valid,
        "version_refs": version_refs,
        "binding_digest": sha256_json(
            {
                "paper_epoch_id": epoch.get("paper_epoch_id"),
                "broker_account_fingerprint": epoch.get("broker_account_fingerprint"),
                "policy_version": policy.get("policy_version"),
                "risk_policy_version": risk_policy.get("policy_version"),
                "version_refs": version_refs,
            }
        ),
        "blocker_count": len(blockers),
        "blockers": blockers,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }


def build_current_experimental_release_state(
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Return pre-launch readiness or the durable state of an executed release.

    The pre-launch gate intentionally requires an active research lock and an
    unstarted trial calendar. Once a release has completed, rerunning a status
    checker must not reinterpret those expected post-launch changes as a failed
    release. The immutable launch receipt and current epoch bindings become the
    authority for that transition.
    """

    runtime = runtime_dir(settings)
    receipt = read_json(runtime / RECEIPT_ARTIFACT)
    if receipt.get("launch_executed") is not True or receipt.get("experimental_mode") is not True:
        return build_experimental_guarded_launch_readiness(settings)

    current = read_json(runtime / EXPERIMENTAL_READINESS_ARTIFACT)
    approval = read_json(runtime / EXPERIMENTAL_APPROVAL_ARTIFACT)
    epoch = read_json(runtime / EPOCH_ARTIFACT)
    lock = read_json(runtime / LOCK_ARTIFACT)
    calendar = read_json(runtime / TRIAL_CALENDAR_ARTIFACT)
    policy = read_json(runtime / EXPERIMENTAL_POLICY_ARTIFACT)
    amendment = read_json(runtime / EXPERIMENTAL_POLICY_AMENDMENT_ARTIFACT)
    blockers: list[str] = []
    epoch_id = epoch.get("paper_epoch_id")

    if receipt.get("canonical_wrapper") != CANONICAL_WRAPPER:
        blockers.append("experimental_release_noncanonical_wrapper")
    if receipt.get("canonical_wrapper_returncode") != 0:
        blockers.append("experimental_release_canonical_wrapper_failed")
    if receipt.get("direct_broker_call_count", 0) != 0:
        blockers.append("experimental_release_direct_broker_call_detected")
    if receipt.get("paper_epoch_id") != epoch_id:
        blockers.append("experimental_release_receipt_epoch_mismatch")
    if approval.get("experimental_paper_mandate_approved") is not True:
        blockers.append("experimental_release_mandate_not_approved")
    if approval.get("paper_epoch_id") != epoch_id:
        blockers.append("experimental_release_approval_epoch_mismatch")
    original_policy_version = approval.get("policy_version")
    if approval.get("live_capital_release") is not False:
        blockers.append("experimental_release_live_capital_enabled")
    if epoch.get("paper_epoch_kind") != "clean_experimental_operator_epoch":
        blockers.append("clean_experimental_epoch_not_active")
    if epoch.get("paper_growth_trial_calendar_started") is not True:
        blockers.append("experimental_release_trial_calendar_not_started")
    epoch_policy_version = epoch.get("experimental_paper_release_policy_version")
    policy_amendment_errors: list[str] = []
    if not (
        original_policy_version == EXPERIMENTAL_POLICY_VERSION
        and epoch_policy_version == EXPERIMENTAL_POLICY_VERSION
    ):
        policy_amendment_errors = validate_policy_amendment(
            amendment,
            policy=policy,
            release_approval=approval,
            paper_epoch=epoch,
            trial_calendar=calendar,
            previous_approval_sha256=file_sha256(
                runtime / EXPERIMENTAL_APPROVAL_ARTIFACT
            ),
        )
        blockers.extend(policy_amendment_errors)
    if lock.get("status") != "released" or lock.get("paperops_watch_only_mode") is not False:
        blockers.append("experimental_release_lock_not_narrowly_released")
    if lock.get("release_mode") != "explicit_operator_approved_experimental_paper_epoch":
        blockers.append("experimental_release_lock_mode_mismatch")
    if calendar.get("paper_epoch_id") != epoch_id:
        blockers.append("experimental_release_calendar_epoch_mismatch")
    if calendar.get("status") not in {"active_real_calendar", "complete_real_calendar"}:
        blockers.append("experimental_release_calendar_not_active")
    if calendar.get("backfill_used") is not False or calendar.get(
        "simulated_elapsed_time_used"
    ) is not False:
        blockers.append("experimental_release_calendar_fabricated")

    blockers = unique_errors(blockers)
    effective = not blockers
    release_started_at = (
        current.get("release_started_at")
        or receipt.get("trial_started_at")
        or epoch.get("paper_growth_trial_started_at")
        or calendar.get("trial_started_at")
    )
    state = dict(current)
    state.update(
        {
            "schema_version": "qadam_experimental_paper_release.v1",
            "artifact_type": "qadam_experimental_paper_release_readiness",
            "generated_at": now_iso(),
            "status": "experimental_paper_release_effective" if effective else "blocked",
            "experimental_paper_release_ready": effective,
            "experimental_paper_release_effective": effective,
            "experimental_policy_operator_approved": (
                approval.get("experimental_policy_operator_approved") is True
            ),
            "experimental_risk_policy_operator_approved": (
                approval.get("experimental_risk_policy_operator_approved") is True
            ),
            "paper_epoch_id": epoch_id,
            "policy_version": EXPERIMENTAL_POLICY_VERSION,
            "launch_policy_version": original_policy_version,
            "policy_amendment_effective": not policy_amendment_errors,
            "policy_amendment_artifact": (
                f"data/runtime/{EXPERIMENTAL_POLICY_AMENDMENT_ARTIFACT}"
                if original_policy_version != EXPERIMENTAL_POLICY_VERSION
                else None
            ),
            "release_started_at": release_started_at,
            "blocker_count": len(blockers),
            "blockers": blockers,
            "paper_order_created_count": 0,
            "broker_write_count": 0,
            "live_capital_enabled": False,
            "authority": authority_flags(),
        }
    )
    return state


def build_experimental_release_approval(
    readiness: dict[str, Any],
    *,
    approval_requested: bool,
    approved_at: str | None = None,
) -> dict[str, Any]:
    approved_time = datetime.fromisoformat(
        (approved_at or now_iso()).replace("Z", "+00:00")
    ).astimezone(timezone.utc)
    approved = bool(
        approval_requested
        and readiness.get("experimental_paper_release_ready") is True
    )
    return {
        "schema_version": "qadam_experimental_paper_release.v1",
        "artifact_type": "qadam_experimental_paper_release_approval",
        "generated_at": approved_time.isoformat(),
        "status": "approved" if approved else "not_approved",
        "operator_approval_requested": approval_requested,
        "operator_approved": approved,
        "experimental_paper_mandate_approved": approved,
        "experimental_policy_operator_approved": approved,
        "experimental_risk_policy_operator_approved": approved,
        "validated_strategy_promotion_approved": False,
        "live_capital_release": False,
        "paper_epoch_id": readiness.get("paper_epoch_id"),
        "policy_version": readiness.get("policy_version"),
        "risk_policy_version": readiness.get("risk_policy_version"),
        "readiness_binding_digest": readiness.get("binding_digest"),
        "expires_at": (
            approved_time + timedelta(seconds=EXPERIMENTAL_APPROVAL_TTL_SECONDS)
        ).isoformat(),
        "canonical_wrapper": CANONICAL_WRAPPER,
        "direct_broker_call_allowed": False,
        "blockers": readiness.get("blockers", []),
        "authority": authority_flags(),
    }


def validate_experimental_release_approval(
    approval: dict[str, Any],
    readiness: dict[str, Any],
    *,
    observed_at: str | None = None,
) -> list[str]:
    """Reject stale, rebound, unsafe, or incomplete experimental approvals."""

    observed = _parse_timestamp(observed_at or now_iso())
    expires = _parse_timestamp(approval.get("expires_at"))
    errors: list[str] = []
    if approval.get("operator_approved") is not True:
        errors.append("explicit_experimental_paper_mandate_approval_missing")
    if observed is None or expires is None or expires <= observed:
        errors.append("experimental_paper_release_approval_expired")
    if approval.get("readiness_binding_digest") != readiness.get("binding_digest"):
        errors.append("experimental_paper_release_approval_binding_changed")
    if approval.get("paper_epoch_id") != readiness.get("paper_epoch_id"):
        errors.append("experimental_paper_release_approval_epoch_changed")
    if approval.get("policy_version") != EXPERIMENTAL_POLICY_VERSION:
        errors.append("experimental_paper_release_approval_policy_changed")
    if approval.get("risk_policy_version") != readiness.get("risk_policy_version"):
        errors.append("experimental_paper_release_approval_risk_policy_changed")
    if approval.get("canonical_wrapper") != CANONICAL_WRAPPER:
        errors.append("experimental_paper_release_approval_wrapper_changed")
    if approval.get("live_capital_release") is not False:
        errors.append("experimental_paper_release_approval_enabled_live_capital")
    errors.extend(
        validate_authority(
            approval.get("authority", {}),
            prefix="experimental_release_approval",
        )
    )
    return unique_errors(errors)


def _experimental_trial_calendar(
    epoch: dict[str, Any],
    *,
    release_timestamp: str,
) -> dict[str, Any]:
    released = datetime.fromisoformat(release_timestamp.replace("Z", "+00:00")).astimezone(
        timezone.utc
    )
    return {
        "schema_version": "qadam_paper_trial_calendar.v1",
        "artifact_type": "qadam_paper_trial_calendar",
        "generated_at": release_timestamp,
        "status": "active_real_calendar",
        "paper_epoch_id": epoch.get("paper_epoch_id"),
        "trial_started_at": release_timestamp,
        "trial_start_date_utc": released.date().isoformat(),
        "trial_day": 1,
        "completed_calendar_day_count": 0,
        "calendar_days_remaining": 29,
        "trial_length_days": 30,
        "backfill_used": False,
        "simulated_elapsed_time_used": False,
        "calendar_pause_allowed": False,
        "no_forced_trades": True,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }


def refresh_experimental_trial_calendar(
    settings: Settings | None = None,
    *,
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Refresh elapsed real calendar time without pausing or backfilling it."""

    runtime = runtime_dir(settings)
    path = runtime / TRIAL_CALENDAR_ARTIFACT
    calendar = read_json(path)
    if not calendar or not calendar.get("trial_started_at"):
        return calendar
    observed = datetime.fromisoformat(
        (observed_at or now_iso()).replace("Z", "+00:00")
    ).astimezone(timezone.utc)
    started = datetime.fromisoformat(
        str(calendar["trial_started_at"]).replace("Z", "+00:00")
    ).astimezone(timezone.utc)
    elapsed = max(0, (observed.date() - started.date()).days)
    calendar.update(
        {
            "generated_at": observed.isoformat(),
            "status": "complete_real_calendar" if elapsed >= 29 else "active_real_calendar",
            "trial_day": min(30, elapsed + 1),
            "completed_calendar_day_count": min(30, elapsed),
            "calendar_days_remaining": max(0, 29 - elapsed),
            "backfill_used": False,
            "simulated_elapsed_time_used": False,
        }
    )
    write_json_atomic(path, calendar)
    return calendar


def execute_experimental_guarded_paper_launch(
    settings: Settings | None = None,
    *,
    explicit_operator_approval: bool = False,
    execute: bool = False,
) -> dict[str, Any]:
    """Release only the experimental class through the canonical wrapper."""

    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    readiness = build_experimental_guarded_launch_readiness(settings)
    approval = build_experimental_release_approval(
        readiness, approval_requested=explicit_operator_approval
    )
    store.write_json(EXPERIMENTAL_READINESS_ARTIFACT, readiness)
    if not execute:
        return {
            "schema_version": "qadam_experimental_paper_release.v1",
            "artifact_type": "qadam_guarded_paper_launch_dry_run",
            "generated_at": now_iso(),
            "status": (
                "dry_run_ready"
                if readiness.get("experimental_paper_release_ready") is True
                else "blocked"
            ),
            "launch_executed": False,
            "experimental_mode": True,
            "blockers": readiness.get("blockers", []),
            "live_capital_enabled": False,
            "authority": authority_flags(),
        }
    store.write_json(EXPERIMENTAL_APPROVAL_ARTIFACT, approval)
    # Re-read every bound input immediately before releasing the lock. The
    # approval is invalid if broker, epoch, policy, or evidence state changed.
    confirmed_readiness = build_experimental_guarded_launch_readiness(settings)
    store.write_json(EXPERIMENTAL_READINESS_ARTIFACT, confirmed_readiness)
    blockers = list(confirmed_readiness.get("blockers", []))
    blockers.extend(
        validate_experimental_release_approval(approval, confirmed_readiness)
    )
    readiness = confirmed_readiness
    if readiness.get("operator_service_running") is True:
        blockers.append("operator_service_must_be_paused_before_lock_release")
    blockers = unique_errors(blockers)
    receipt: dict[str, Any] = {
        "schema_version": "qadam_experimental_paper_release.v1",
        "artifact_type": "qadam_guarded_paper_launch_receipt",
        "generated_at": now_iso(),
        "status": "blocked" if blockers else "launch_pending",
        "launch_executed": False,
        "experimental_mode": True,
        "canonical_wrapper": CANONICAL_WRAPPER,
        "canonical_wrapper_invoked": False,
        "direct_broker_call_count": 0,
        "paper_epoch_id": readiness.get("paper_epoch_id"),
        "trial_calendar_started": False,
        "operator_service_resume_required": False,
        "blockers": blockers,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }
    if blockers:
        store.write_json(RECEIPT_ARTIFACT, receipt)
        return receipt

    lock_path = runtime / LOCK_ARTIFACT
    epoch_path = runtime / EPOCH_ARTIFACT
    calendar_path = runtime / TRIAL_CALENDAR_ARTIFACT
    phase7_path = runtime / "phase7_demo_proof_run.json"
    original_lock = read_json(lock_path)
    original_epoch = read_json(epoch_path)
    original_calendar = read_json(calendar_path)
    original_phase7 = read_json(phase7_path)
    released_at = now_iso()
    released_lock = _released_lock(original_lock, approval)
    released_lock["release_mode"] = (
        "explicit_operator_approved_experimental_paper_epoch"
    )
    released_lock["release_approval_artifact"] = (
        f"data/runtime/{EXPERIMENTAL_APPROVAL_ARTIFACT}"
    )
    epoch = dict(original_epoch)
    epoch.update(
        {
            "paper_growth_trial_calendar_started": True,
            "paper_growth_trial_state": "active_real_calendar",
            "paper_growth_trial_started_at": released_at,
            "experimental_paper_release_policy_version": EXPERIMENTAL_POLICY_VERSION,
        }
    )
    epoch["epoch_digest"] = sha256_json(
        {key: value for key, value in epoch.items() if key != "epoch_digest"}
    )
    calendar = _experimental_trial_calendar(epoch, release_timestamp=released_at)
    write_json_atomic(lock_path, released_lock)
    write_json_atomic(epoch_path, epoch)
    write_json_atomic(calendar_path, calendar)
    from orchestrator.phase7_demo_proof_run import (  # local import avoids launch-time cycles
        build_phase7_demo_proof_run,
        write_phase7_demo_proof_run,
    )

    phase7 = build_phase7_demo_proof_run(settings=settings, reset=True)
    write_phase7_demo_proof_run(phase7, settings=settings)
    append_jsonl_durable(
        runtime / LOCK_HISTORY_ARTIFACT,
        _lock_history_event(
            state="released_experimental_paper",
            approval=approval,
            detail=(
                "Research lock narrowly released for the clean experimental paper "
                "epoch and real trial calendar before one canonical PaperOps pass."
            ),
        ),
    )
    try:
        completed = subprocess.run(
            [sys.executable, str(ROOT / CANONICAL_WRAPPER)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=1800,
            env=os.environ.copy(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        completed = None
        failure_detail = exc.__class__.__name__
    else:
        failure_detail = None
    if completed is None or completed.returncode != 0:
        write_json_atomic(lock_path, original_lock)
        write_json_atomic(epoch_path, original_epoch)
        if original_calendar:
            write_json_atomic(calendar_path, original_calendar)
        else:
            calendar_path.unlink(missing_ok=True)
        if original_phase7:
            write_json_atomic(phase7_path, original_phase7)
        else:
            phase7_path.unlink(missing_ok=True)
        append_jsonl_durable(
            runtime / LOCK_HISTORY_ARTIFACT,
            _lock_history_event(
                state="experimental_release_rolled_back",
                approval=approval,
                detail=(
                    "The initial canonical PaperOps pass did not complete; watch-only "
                    "state and the unstarted trial calendar were restored."
                ),
            ),
        )
        receipt.update(
            {
                "status": "launch_failed_relocked",
                "canonical_wrapper_invoked": True,
                "canonical_wrapper_returncode": (
                    None if completed is None else completed.returncode
                ),
                "execution_error_class": failure_detail,
                "blockers": ["initial_canonical_paperops_pass_failed"],
            }
        )
    else:
        effective_readiness = dict(readiness)
        effective_readiness.update(
            {
                "generated_at": released_at,
                "status": "experimental_paper_release_effective",
                "experimental_paper_release_ready": True,
                "experimental_paper_release_effective": True,
                "experimental_policy_operator_approved": True,
                "experimental_risk_policy_operator_approved": True,
                "approval_artifact": f"data/runtime/{EXPERIMENTAL_APPROVAL_ARTIFACT}",
                "release_started_at": released_at,
            }
        )
        store.write_json(EXPERIMENTAL_READINESS_ARTIFACT, effective_readiness)
        receipt.update(
            {
                "status": "initial_canonical_pass_complete_ready_idle_or_operating",
                "launch_executed": True,
                "canonical_wrapper_invoked": True,
                "canonical_wrapper_returncode": 0,
                "trial_calendar_started": True,
                "trial_started_at": released_at,
                "operator_service_resume_required": True,
                "blockers": [],
            }
        )
    store.write_json(RECEIPT_ARTIFACT, receipt)
    return receipt


def build_experimental_guarded_launch_checks(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    readiness = read_json(runtime / EXPERIMENTAL_READINESS_ARTIFACT)
    approval = read_json(runtime / EXPERIMENTAL_APPROVAL_ARTIFACT)
    receipt = read_json(runtime / RECEIPT_ARTIFACT)
    lock = read_json(runtime / LOCK_ARTIFACT)
    service = read_json(runtime / SERVICE_ARTIFACT)
    calendar = refresh_experimental_trial_calendar(settings)
    launched = bool(
        receipt.get("launch_executed") is True
        and receipt.get("experimental_mode") is True
        and readiness.get("experimental_paper_release_effective") is True
        and approval.get("experimental_paper_mandate_approved") is True
        and lock.get("status") == "released"
        and lock.get("paperops_watch_only_mode") is False
        and calendar.get("status") in {"active_real_calendar", "complete_real_calendar"}
    )
    running = launched and service.get("service_running") is True
    errors: list[str] = []
    if receipt.get("canonical_wrapper_invoked") is True and receipt.get(
        "canonical_wrapper"
    ) != CANONICAL_WRAPPER:
        errors.append("experimental_launch_noncanonical_wrapper")
    if receipt.get("direct_broker_call_count", 0) != 0:
        errors.append("experimental_launch_direct_broker_call_detected")
    if approval.get("live_capital_release") is True:
        errors.append("experimental_launch_live_capital_approved")
    if calendar and (
        calendar.get("backfill_used") is not False
        or calendar.get("simulated_elapsed_time_used") is not False
    ):
        errors.append("experimental_trial_calendar_fabricated")
    for payload, prefix in (
        (readiness, "experimental_launch_readiness"),
        (approval, "experimental_launch_approval"),
        (receipt, "experimental_launch_receipt"),
        (calendar, "experimental_trial_calendar"),
    ):
        if payload:
            errors.extend(validate_authority(payload.get("authority", {}), prefix=prefix))
    errors = unique_errors(errors)
    checks = {
        "schema_version": "qadam_experimental_paper_release.v1",
        "artifact_type": "qadam_experimental_paper_release_checks",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "implementation_ready": not errors,
        "experimental_paper_launch_complete": launched,
        "autonomous_experimental_paper_operation_running": running,
        "healthy_ready_idle_allowed": True,
        "validated_edge_required": False,
        "trial_calendar_started": calendar.get("status")
        in {"active_real_calendar", "complete_real_calendar"},
        "canonical_wrapper_only": True,
        "direct_broker_call_count": 0,
        "live_capital_enabled": False,
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    AtomicArtifactStore(runtime).write_json(EXPERIMENTAL_CHECK_ARTIFACT, checks)
    return checks, errors


__all__ = [
    "APPROVAL_ARTIFACT",
    "CHECK_ARTIFACT",
    "DRY_RUN_ARTIFACT",
    "EXPERIMENTAL_APPROVAL_ARTIFACT",
    "EXPERIMENTAL_CHECK_ARTIFACT",
    "EXPERIMENTAL_READINESS_ARTIFACT",
    "READINESS_ARTIFACT",
    "RECEIPT_ARTIFACT",
    "build_guarded_launch_checks",
    "build_guarded_launch_readiness",
    "build_experimental_guarded_launch_checks",
    "build_experimental_guarded_launch_readiness",
    "build_current_experimental_release_state",
    "build_experimental_release_approval",
    "build_release_approval",
    "execute_guarded_paper_launch",
    "execute_experimental_guarded_paper_launch",
    "refresh_experimental_trial_calendar",
    "validate_experimental_release_approval",
]
