#!/usr/bin/env python3
"""Validate the Phase 3 quantum scheduler dry-run contract."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.quantum import (  # noqa: E402
    QUANTUM_ORACLE_CADENCE_DAYS,
    QUANTUM_ORACLE_JOB_TYPES,
    QUANTUM_SCHEDULER_DRY_RUN_SCHEMA_VERSION,
    quantum_scheduler_dry_run,
    validate_quantum_scheduler_dry_run,
)

REQUIRED_SCHEDULER_FIELDS = {
    "autonomous_scheduler_enabled",
    "background_automation_created",
    "boundary",
    "bypass_broker_reconciliation_allowed",
    "bypass_execution_policy_allowed",
    "bypass_paper_submit_receipt_allowed",
    "bypass_risk_agent_allowed",
    "bypass_signal_integrity_allowed",
    "bypass_strategy_lead_allowed",
    "cadence",
    "cadence_days",
    "dry_run_only",
    "due",
    "due_reason",
    "execution_allowed",
    "hardware_jobs_submitted_count",
    "hardware_scheduler_enabled",
    "hardware_scheduler_enabled_count",
    "hardware_submission_allowed",
    "hardware_submission_allowed_count",
    "intended_job_count",
    "intended_jobs",
    "job_submission_allowed",
    "jobs_queued_count",
    "jobs_submitted_count",
    "last_run_at",
    "next_due_at",
    "paper_order_allowed",
    "provider_call_allowed",
    "public_safe",
    "queue_write_allowed",
    "recurring_job_created",
    "scheduler_enabled",
    "schema_version",
    "status",
    "trade_candidate_authority",
    "would_queue_job_count",
    "would_queue_jobs",
}

REQUIRED_JOB_FIELDS = {
    "boundary",
    "dry_run_only",
    "execution_allowed",
    "hardware_submission_allowed",
    "job_submission_allowed",
    "job_type",
    "local_validation_required",
    "paper_order_allowed",
    "provider_call_allowed",
    "queue_write_allowed",
    "required_gates",
    "schema_version",
    "source",
    "trade_candidate_authority",
}


def main() -> int:
    state = quantum_scheduler_dry_run(Settings.from_env())
    validate_quantum_scheduler_dry_run(state)
    no_prior_state = quantum_scheduler_dry_run(Settings.from_env(), rows=())
    validate_quantum_scheduler_dry_run(no_prior_state)
    intended_jobs = state.get("intended_jobs", [])
    would_queue_jobs = state.get("would_queue_jobs", [])

    print("quantum_scheduler_dry_run_status=" + str(state.get("status")))
    print(f"quantum_scheduler_schema_version={state.get('schema_version')}")
    print(f"quantum_scheduler_cadence={state.get('cadence')}")
    print(f"quantum_scheduler_cadence_days={state.get('cadence_days')}")
    print(f"quantum_scheduler_last_run_at={state.get('last_run_at')}")
    print(f"quantum_scheduler_next_due_at={state.get('next_due_at')}")
    print(f"quantum_scheduler_due={state.get('due')}")
    print(f"quantum_scheduler_due_reason={state.get('due_reason')}")
    print(f"quantum_scheduler_enabled={state.get('scheduler_enabled')}")
    print(f"quantum_scheduler_autonomous_enabled={state.get('autonomous_scheduler_enabled')}")
    print(f"quantum_scheduler_background_automation_created={state.get('background_automation_created')}")
    print(f"quantum_scheduler_recurring_job_created={state.get('recurring_job_created')}")
    print(f"quantum_scheduler_intended_job_count={state.get('intended_job_count')}")
    print(f"quantum_scheduler_would_queue_job_count={state.get('would_queue_job_count')}")
    print(f"quantum_scheduler_jobs_queued_count={state.get('jobs_queued_count')}")
    print(f"quantum_scheduler_jobs_submitted_count={state.get('jobs_submitted_count')}")
    print(f"quantum_scheduler_hardware_jobs_submitted_count={state.get('hardware_jobs_submitted_count')}")
    print(f"quantum_scheduler_hardware_scheduler_enabled_count={state.get('hardware_scheduler_enabled_count')}")
    print(f"quantum_scheduler_hardware_submission_allowed_count={state.get('hardware_submission_allowed_count')}")
    print(f"quantum_scheduler_no_prior_due={no_prior_state.get('due')}")
    print(f"quantum_scheduler_no_prior_would_queue_job_count={no_prior_state.get('would_queue_job_count')}")

    missing_fields = sorted(REQUIRED_SCHEDULER_FIELDS - set(state))
    if missing_fields:
        print("quantum_scheduler_fields_missing=" + ",".join(missing_fields))
        return 1
    if state.get("schema_version") != QUANTUM_SCHEDULER_DRY_RUN_SCHEMA_VERSION:
        print("quantum_scheduler_schema_mismatch=true")
        return 1
    if state.get("cadence") != "weekly_shadow_oracle":
        print("quantum_scheduler_cadence_mismatch=true")
        return 1
    if state.get("cadence_days") != QUANTUM_ORACLE_CADENCE_DAYS:
        print("quantum_scheduler_cadence_days_mismatch=true")
        return 1
    if state.get("dry_run_only") is not True:
        print("quantum_scheduler_not_dry_run=true")
        return 1
    if state.get("public_safe") is not True:
        print("quantum_scheduler_not_public_safe=true")
        return 1
    if state.get("intended_job_count") != len(QUANTUM_ORACLE_JOB_TYPES):
        print("quantum_scheduler_intended_job_count_mismatch=true")
        return 1
    if not isinstance(intended_jobs, list) or not isinstance(would_queue_jobs, list):
        print("quantum_scheduler_job_lists_invalid=true")
        return 1
    intended_job_types = {str(job.get("job_type")) for job in intended_jobs if isinstance(job, dict)}
    if intended_job_types != QUANTUM_ORACLE_JOB_TYPES:
        print("quantum_scheduler_intended_job_types_mismatch=true")
        return 1
    if state.get("due") is True and state.get("would_queue_job_count") != len(QUANTUM_ORACLE_JOB_TYPES):
        print("quantum_scheduler_due_queue_count_mismatch=true")
        return 1
    if state.get("due") is False and state.get("would_queue_job_count") != 0:
        print("quantum_scheduler_not_due_queue_count_nonzero=true")
        return 1
    if no_prior_state.get("due") is not True:
        print("quantum_scheduler_no_prior_not_due=true")
        return 1
    if no_prior_state.get("would_queue_job_count") != len(QUANTUM_ORACLE_JOB_TYPES):
        print("quantum_scheduler_no_prior_queue_count_mismatch=true")
        return 1
    for key in (
        "scheduler_enabled",
        "autonomous_scheduler_enabled",
        "background_automation_created",
        "recurring_job_created",
        "queue_write_allowed",
        "job_submission_allowed",
        "hardware_scheduler_enabled",
        "hardware_submission_allowed",
        "provider_call_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "trade_candidate_authority",
        "bypass_signal_integrity_allowed",
        "bypass_strategy_lead_allowed",
        "bypass_risk_agent_allowed",
        "bypass_execution_policy_allowed",
        "bypass_broker_reconciliation_allowed",
        "bypass_paper_submit_receipt_allowed",
    ):
        if state.get(key) is not False:
            print(f"quantum_scheduler_flag_not_false={key}")
            return 1
    for key in (
        "jobs_queued_count",
        "jobs_submitted_count",
        "hardware_jobs_submitted_count",
        "hardware_scheduler_enabled_count",
        "hardware_submission_allowed_count",
    ):
        if state.get(key) != 0:
            print(f"quantum_scheduler_nonzero={key}")
            return 1
    for job in intended_jobs + would_queue_jobs:
        if not isinstance(job, dict):
            print("quantum_scheduler_job_invalid=true")
            return 1
        print(
            "quantum_scheduler_intended_job="
            f"{job.get('job_type')},queue_write_allowed={job.get('queue_write_allowed')},"
            f"job_submission_allowed={job.get('job_submission_allowed')},"
            f"hardware_submission_allowed={job.get('hardware_submission_allowed')}"
        )
        missing_job_fields = sorted(REQUIRED_JOB_FIELDS - set(job))
        if missing_job_fields:
            print(f"quantum_scheduler_job_fields_missing={job.get('job_type')}:{','.join(missing_job_fields)}")
            return 1
        if job.get("job_type") not in QUANTUM_ORACLE_JOB_TYPES:
            print("quantum_scheduler_job_type_invalid=true")
            return 1
        for key in (
            "queue_write_allowed",
            "job_submission_allowed",
            "hardware_submission_allowed",
            "provider_call_allowed",
            "execution_allowed",
            "paper_order_allowed",
            "trade_candidate_authority",
        ):
            if job.get(key) is not False:
                print(f"quantum_scheduler_job_flag_not_false={job.get('job_type')}:{key}")
                return 1
    if "metadata only" not in state.get("boundary", ""):
        print("quantum_scheduler_boundary_weak=true")
        return 1

    print("quantum_scheduler_dry_run_check=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
