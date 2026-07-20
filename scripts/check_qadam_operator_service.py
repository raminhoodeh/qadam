#!/usr/bin/env python3
"""Build and validate the OR-18 unattended operator service."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.config import Settings  # noqa: E402
from orchestrator.qadam_operator_ready_common import runtime_dir  # noqa: E402
from orchestrator.qadam_operator_service import (  # noqa: E402
    CHECK_ARTIFACT,
    CIRCUIT_BREAKERS_ARTIFACT,
    HEARTBEATS_ARTIFACT,
    INTEGRATION_PROBE_ARTIFACT,
    REPAIR_QUEUE_ARTIFACT,
    RECEIPTS_ARTIFACT,
    RETRY_LEDGER_ARTIFACT,
    SESSION_LEDGER_ARTIFACT,
    SOAK_ARTIFACT,
    STATUS_ARTIFACT,
    WORKERS_ARTIFACT,
    WHY_NOT_RUNNING_ARTIFACT,
    build_and_write_operator_service,
)


def main() -> int:
    settings = Settings.from_env()
    runtime = runtime_dir(settings)
    _state, checks, errors = build_and_write_operator_service(settings)
    for name in (
        STATUS_ARTIFACT,
        HEARTBEATS_ARTIFACT,
        REPAIR_QUEUE_ARTIFACT,
        RETRY_LEDGER_ARTIFACT,
        SOAK_ARTIFACT,
        WHY_NOT_RUNNING_ARTIFACT,
        RECEIPTS_ARTIFACT,
        INTEGRATION_PROBE_ARTIFACT,
        CIRCUIT_BREAKERS_ARTIFACT,
        WORKERS_ARTIFACT,
        SESSION_LEDGER_ARTIFACT,
        CHECK_ARTIFACT,
    ):
        print(f"artifact={runtime / name}")
    for key in (
        "status",
        "implementation_ready",
        "operational_ready",
        "observation_ready",
        "service_installed",
        "service_running",
        "service_count",
        "due_job_dispatcher_enabled",
        "projection_only_control_cycle",
        "integration_probe_passed",
        "integration_probe_executed_service_count",
        "integration_probe_required_service_count",
        "service_receipt_count",
        "active_worker_count",
        "open_circuit_count",
        "fresh_service_count",
        "stale_service_count",
        "not_run_service_count",
        "paperops_delegation_probe_status",
        "failure_class_count",
        "interruption_probe_count",
        "interruption_probe_pass_count",
        "multi_session_soak_complete",
        "repair_request_count",
        "critical_repair_request_count",
        "paperops_watch_only",
        "paper_order_created_count",
        "broker_write_count",
    ):
        print(f"{key}={checks[key]}")
    print(f"validation_error_count={len(errors)}")
    for error in errors:
        print(f"error={error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
