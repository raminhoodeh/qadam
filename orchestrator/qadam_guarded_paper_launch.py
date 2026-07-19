"""Audited Phase 11 release into the canonical guarded PaperOps route.

The default path is diagnostic only.  An actual launch requires a clean epoch,
every pre-launch operating gate, explicit operator approval, and a paused
operator service.  This module never calls a broker directly; the only allowed
execution subprocess is the canonical PaperOps wrapper.
"""

from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

from orchestrator.config import Settings
from orchestrator.paper_account import ALPACA_PAPER_BASE_URL
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    append_jsonl_durable,
    authority_flags,
    file_sha256,
    now_iso,
    public_path,
    read_json,
    runtime_dir,
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


__all__ = [
    "APPROVAL_ARTIFACT",
    "CHECK_ARTIFACT",
    "DRY_RUN_ARTIFACT",
    "READINESS_ARTIFACT",
    "RECEIPT_ARTIFACT",
    "build_guarded_launch_checks",
    "build_guarded_launch_readiness",
    "build_release_approval",
    "execute_guarded_paper_launch",
]
