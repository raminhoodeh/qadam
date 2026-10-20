from dataclasses import replace
from datetime import datetime, timedelta, timezone
from threading import Event

import pytest

from orchestrator.config import Settings
from orchestrator.execution.ledger import ExecutionOwnerError, OperatingLedger
from orchestrator.execution.ownership import ExecutionLeaseKeeper


def test_renewal_runs_while_owner_work_is_blocked():
    renewed = Event()

    class Ledger:
        calls = 0

        def heartbeat_execution_owner(self, lease):
            self.calls += 1
            if self.calls > 1:
                renewed.set()

    ledger = Ledger()
    keeper = ExecutionLeaseKeeper(ledger, object(), interval_seconds=.01).start()
    try:
        assert renewed.wait(1)
    finally:
        keeper.stop()


def test_renewal_failure_cannot_reacquire_or_disappear():
    failed = Event()

    class Ledger:
        calls = 0

        def heartbeat_execution_owner(self, lease):
            self.calls += 1
            if self.calls > 1:
                failed.set()
                raise ExecutionOwnerError("token_matches")

    ledger = Ledger()
    keeper = ExecutionLeaseKeeper(ledger, object(), interval_seconds=.01).start()
    assert failed.wait(1)
    keeper.thread.join(timeout=1)
    with pytest.raises(ExecutionOwnerError, match="renewal_failed"):
        keeper.stop()
    assert ledger.calls == 2


def test_expired_but_live_owner_cannot_be_replaced(tmp_path, monkeypatch):
    import orchestrator.execution.ledger as module

    now = datetime(2026, 10, 20, tzinfo=timezone.utc)
    monkeypatch.setattr(module, "_now", lambda: now)
    settings = replace(Settings.from_env(), runtime_dir=str(tmp_path), state_root=str(tmp_path))
    ledger = OperatingLedger(settings)
    ledger.acquire_execution_owner("paperops-autonomous-pass:123:original", ttl_seconds=60)
    now += timedelta(seconds=61)
    monkeypatch.setattr(module, "execution_owner_process_state", lambda owner: "alive")
    with pytest.raises(ExecutionOwnerError, match="execution_owner_busy"):
        ledger.acquire_execution_owner("replacement")
