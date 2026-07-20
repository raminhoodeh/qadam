from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
import time

from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_service import (
    MAINTENANCE_ARTIFACT,
    OperatorMaintenanceLock,
    OperatorServiceLease,
    OperatorServiceLeaseHeartbeat,
    maintenance_request_active,
)


def test_maintenance_lock_excludes_operator_cycle(tmp_path) -> None:
    maintenance = OperatorMaintenanceLock(tmp_path)
    operator = OperatorMaintenanceLock(tmp_path)

    acquired, reason = maintenance.acquire(blocking=False)
    assert acquired is True
    assert reason == "runtime_maintenance_lock_acquired"

    acquired, reason = operator.acquire(blocking=False)
    assert acquired is False
    assert reason == "runtime_maintenance_window_active"

    assert maintenance.release() is True
    acquired, reason = operator.acquire(blocking=False)
    assert acquired is True
    assert reason == "runtime_maintenance_lock_acquired"
    assert operator.release() is True


def test_fresh_live_maintenance_request_yields_operator_cycle(tmp_path) -> None:
    now = datetime.now(timezone.utc)
    AtomicArtifactStore(tmp_path).write_json(
        MAINTENANCE_ARTIFACT,
        {
            "generated_at": now.isoformat(),
            "status": "requested",
            "owner_pid": os.getpid(),
        },
    )

    assert maintenance_request_active(tmp_path, now=now) is True


def test_stale_or_dead_maintenance_request_does_not_pause_operator(tmp_path) -> None:
    now = datetime.now(timezone.utc)
    store = AtomicArtifactStore(tmp_path)
    store.write_json(
        MAINTENANCE_ARTIFACT,
        {
            "generated_at": (now - timedelta(hours=1)).isoformat(),
            "status": "requested",
            "owner_pid": os.getpid(),
        },
    )
    assert maintenance_request_active(tmp_path, now=now) is False

    store.write_json(
        MAINTENANCE_ARTIFACT,
        {
            "generated_at": now.isoformat(),
            "status": "requested",
            "owner_pid": 999_999_999,
        },
    )
    assert maintenance_request_active(tmp_path, now=now) is False


def test_operator_lease_heartbeat_keeps_long_job_publicly_alive(tmp_path) -> None:
    lease = OperatorServiceLease(tmp_path, lease_ttl_seconds=1)
    acquired, _reason = lease.acquire()
    assert acquired is True
    heartbeat = OperatorServiceLeaseHeartbeat(lease, interval_seconds=0.01)
    heartbeat.start()
    try:
        first = AtomicArtifactStore(tmp_path).read_json(
            "qadam_operator_service_lease.json"
        )["generated_at"]
        time.sleep(0.04)
        second = AtomicArtifactStore(tmp_path).read_json(
            "qadam_operator_service_lease.json"
        )["generated_at"]
        assert second > first
    finally:
        heartbeat.stop()
        assert lease.release() is True
