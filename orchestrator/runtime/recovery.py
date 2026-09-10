"""Checkpointed recovery through the normal singleton scheduler, not a second queue runner."""

import os
from datetime import datetime, timezone

from orchestrator.contracts.timestamps import _parse_timestamp
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    runtime_dir,
)


SUCCESS_STATES = {
    "completed",
    "completed_with_evidence_hold",
    "completed_with_transport_hold",
    "worker_completed",
}
IDLE_REASONS = {"market_closed", "terminal_no_work", "no_eligible_work"}


def verified_recovery_receipt(receipt, request, service_id):
    """Only actual work on this release, after this incident, can finish a repair."""
    after = _parse_timestamp(
        request.get("requested_after_by_service", {}).get(service_id) or request.get("generated_at")
    )
    completed = _parse_timestamp(receipt.get("completed_at") or receipt.get("generated_at"))
    identity = receipt.get("operator_build_identity") or {}
    return bool(
        after
        and completed
        and after <= completed <= datetime.now(timezone.utc)
        and identity.get("git_commit") == request.get("git_commit")
        and identity.get("service_contract_hash") == request.get("operator_service_contract_hash")
        and identity.get("dirty_worktree") is False
        and (
            receipt.get("state") in SUCCESS_STATES
            or (receipt.get("state") == "skipped" and receipt.get("skip_reason") in IDLE_REASONS)
        )
    )


def advance_recovery(
    request, settings=None, *, executor=None, max_jobs=None, max_elapsed_seconds=120
):
    from orchestrator.runtime import operator as op

    runtime = runtime_dir(settings)
    current = op.pending_operator_full_heal_request(settings)
    request_id = request.get("request_id")
    if not request_id or current.get("request_id") != request_id:
        raise ValueError("operator_full_heal_request_not_current")
    # Scope may have grown while the critic was checking another failing service.
    selected = op._full_heal_service_ids(current.get("service_ids") or [])
    checks = dict(current.get("dispatch_service_checks") or {})
    failures = dict(current.get("failed_attempts_by_service") or {})
    latest = op._last_receipts(runtime)
    successful = op._last_successful_receipts(runtime)
    circuits = op._circuit_breaker_state(runtime)
    for service_id in selected:
        if circuits.get(service_id, {}).get("state", "closed") != "closed":
            checks.pop(service_id, None)
            continue
        for receipt in (latest.get(service_id, {}), successful.get(service_id, {})):
            if verified_recovery_receipt(receipt, current, service_id):
                checks[service_id] = {
                    "verified": True,
                    "receipt_id": receipt.get("receipt_id"),
                    "state": receipt.get("state"),
                    "skip_reason": receipt.get("skip_reason"),
                    "completed_at": receipt.get("completed_at") or receipt.get("generated_at"),
                }
                break
    remaining = tuple(
        service_id for service_id in selected if not checks.get(service_id, {}).get("verified")
    )
    op._update_full_heal_request_state(
        runtime,
        request_id,
        status="in_progress",
        owner_pid=os.getpid(),
        accepted_at=current.get("accepted_at") or now_iso(),
        phase="bounded_scheduler_recovery",
        current_service_ids=[],
        completed_service_ids=sorted(checks),
        dispatch_service_checks=checks,
        remaining_service_ids=list(remaining),
        current_step_timeout_seconds=0,
    )

    def progress(service_id, receipt):
        if receipt is None:
            definition = op._service_definition(service_id)
            op._update_full_heal_request_state(
                runtime,
                request_id,
                current_service_ids=[service_id],
                current_step_timeout_seconds=definition.timeout_seconds,
            )
            return
        if service_id in selected and receipt.get("state") == "failed":
            failures[service_id] = int(failures.get(service_id) or 0) + 1
            checks.pop(service_id, None)
        if service_id in selected and verified_recovery_receipt(receipt, current, service_id):
            checks[service_id] = {
                "verified": True,
                "receipt_id": receipt.get("receipt_id"),
                "state": receipt.get("state"),
                "skip_reason": receipt.get("skip_reason"),
                "completed_at": receipt.get("completed_at") or receipt.get("generated_at"),
            }
        if receipt.get("state") != "skipped" or service_id in checks:
            op._update_full_heal_request_state(
                runtime,
                request_id,
                completed_service_ids=sorted(checks),
                dispatch_service_checks=checks,
                failed_attempts_by_service=failures,
                remaining_service_ids=[item for item in selected if item not in checks],
                current_service_ids=[],
                current_step_timeout_seconds=0,
            )

    cycle = op.run_safe_operator_control_cycle(
        settings,
        executor=executor,
        max_jobs=max_jobs,
        max_elapsed_seconds=max_elapsed_seconds,
        recovery_service_ids=tuple(
            service_id for service_id in remaining if failures.get(service_id, 0) < 3
        ),
        progress_callback=progress,
    )
    current = op.pending_operator_full_heal_request(settings)
    selected = op._full_heal_service_ids(current.get("service_ids") or selected)
    circuits = op._circuit_breaker_state(runtime)
    # A service can pass and fail again within one recovery cycle. Earlier
    # success is not permission to certify its now-open circuit as healed.
    for service_id in selected:
        if circuits.get(service_id, {}).get("state", "closed") != "closed":
            checks.pop(service_id, None)
    remaining = [
        service_id for service_id in selected if not checks.get(service_id, {}).get("verified")
    ]
    nonrepairable = [
        service_id
        for service_id in remaining
        if failures.get(service_id, 0) >= 3
        or (
            circuits.get(service_id, {}).get("state") in {"open", "half_open"}
            and circuits[service_id].get("failure_class")
            not in op.FULL_HEAL_SAFE_CIRCUIT_FAILURE_CLASSES
            and not op.code_defect_revalidation_available(service_id, circuits[service_id])
        )
    ]
    status = (
        "completed"
        if not remaining
        else "blocked"
        if len(nonrepairable) == len(remaining)
        else "in_progress"
    )
    observed = read_json(runtime / op.STATUS_ARTIFACT)
    receipt = {
        "schema_version": op.SCHEMA_VERSION,
        "artifact_type": "qadam_operator_full_heal_receipt",
        "generated_at": now_iso(),
        "request_id": request_id,
        "status": status,
        "git_commit": current.get("git_commit") or request.get("git_commit"),
        "operator_service_contract_hash": request.get("operator_service_contract_hash"),
        "service_ids": list(selected),
        "completed_service_ids": sorted(checks),
        "remaining_service_ids": remaining,
        "failed_service_ids": nonrepairable,
        "failed_attempts_by_service": failures,
        "dispatch_service_checks": checks,
        "operator_cycle": cycle,
        "all_requested_services_revalidated": not remaining,
        "all_services_currently_fresh": bool(
            not remaining
            and observed.get("service_count")
            and observed.get("freshness", {}).get("fresh_service_count")
            == observed.get("service_count")
        ),
        "single_operator_owner_used": True,
        "guarded_paperops_wrapper_only": True,
        "paper_only": True,
        "live_capital_enabled": False,
        "autonomous_code_edit_allowed": False,
        "policy_mutation_allowed": False,
        "forced_trade_allowed": False,
        "canonical_paperops_status": read_json(
            runtime / "paperops_autonomous_pass_summary.json"
        ).get("status"),
        # A cumulative PaperOps summary is not the order count for this repair.
        "canonical_paperops_submitted_order_count": sum(
            int((result.get("work_result") or {}).get("submitted_paper_order_count") or 0)
            for item in cycle.get("dispatch_receipts", [])
            if item.get("service_id") == "guarded_paperops"
            for result in item.get("command_results", [])
        ),
        "authority": authority_flags(),
    }
    # Finalisation shares the request lock with coalescing, so added scope cannot
    # be lost in the gap between reading the request and marking it complete.
    with op._operator_state_transaction(runtime, op.CONTROL_STATE_LOCK_FILENAME):
        latest_request = read_json(runtime / op.FULL_HEAL_REQUEST_ARTIFACT)
        if latest_request.get("request_id") != request_id:
            return {**receipt, "status": "in_progress"}
        added = set(latest_request.get("service_ids") or []).difference(selected)
        if added:
            receipt.update(status="in_progress", all_requested_services_revalidated=False)
            receipt["remaining_service_ids"] = sorted(set(remaining).union(added))
        op.AtomicArtifactStore(runtime).write_json(op.FULL_HEAL_RECEIPT_ARTIFACT, receipt)
        op.AtomicArtifactStore(runtime).write_json(
            op.FULL_HEAL_REQUEST_ARTIFACT,
            {
                **latest_request,
                "status": receipt["status"],
                "progress_at": now_iso(),
                "completed_service_ids": sorted(checks),
                "dispatch_service_checks": checks,
                "failed_attempts_by_service": failures,
                "remaining_service_ids": receipt["remaining_service_ids"],
                "current_service_ids": [],
                "current_step_timeout_seconds": 0,
                "completed_at": now_iso() if receipt["status"] == "completed" else None,
            },
        )
    return receipt
