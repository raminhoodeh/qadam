from __future__ import annotations

from orchestrator.qadam_operator_service import OperatorMaintenanceLock


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
