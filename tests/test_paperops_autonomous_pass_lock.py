from __future__ import annotations

from dataclasses import replace
import subprocess

from orchestrator.config import Settings
from scripts import run_paperops_autonomous_pass as paperops_runner
from scripts.run_paperops_autonomous_pass import (
    _acquire_pass_lock,
    _refresh_and_reconcile_paper_mirror,
)


def test_canonical_pass_lock_rejects_overlapping_runner(tmp_path) -> None:
    settings = replace(Settings.from_env(), runtime_dir=str(tmp_path))
    first = _acquire_pass_lock(settings)
    assert first is not None
    try:
        assert _acquire_pass_lock(settings) is None
    finally:
        first.close()

    second = _acquire_pass_lock(settings)
    assert second is not None
    second.close()


class _Ledger:
    def __init__(self, *, fail_sync: bool = False) -> None:
        self.fail_sync = fail_sync
        self.sync_calls: list[tuple[str, bool]] = []
        self.freeze_reasons: list[str] = []

    def sync_paper_mirror(self, *, phase: str, bootstrap: bool):
        self.sync_calls.append((phase, bootstrap))
        if self.fail_sync:
            raise RuntimeError("provider detail must not escape")
        return {"status": "passed", "phase": phase}

    def set_execution_frozen(self, *, reason: str) -> None:
        self.freeze_reasons.append(reason)

    def execution_state(self):
        return {"frozen": bool(self.freeze_reasons),
                "reason": self.freeze_reasons[-1] if self.freeze_reasons else None}


def test_final_control_check_follows_post_run_broker_reconciliation(monkeypatch):
    ledger = _Ledger()
    events = []

    def run_sequence(**kwargs):
        labels = [label for label, _ in kwargs["command_sequence"]]
        events.extend(labels)
        if "canonical_paper_control" in labels:
            assert labels == ["canonical_paper_control"]
            assert ledger.sync_calls == [("post_paperops_submission", False)]
            assert kwargs["allow_new_paper_submission"] is False
        return [{"label": label, "returncode": 0} for label in labels]

    def broker_read(command, **kwargs):
        assert command[1:] == ["scripts/check_alpaca_paper_mirror.py", "--live"]
        events.append("final_broker_read")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(paperops_runner, "run_command_sequence", run_sequence)
    monkeypatch.setattr(paperops_runner.subprocess, "run", broker_read)
    results, refresh, reconciliation = paperops_runner._run_reconciled_command_sequence(
        ledger, allow_new_paper_submission=False, execution_owner_env={},
    )
    assert refresh.returncode == 0
    assert reconciliation["status"] == "passed"
    assert events[-2:] == ["final_broker_read", "canonical_paper_control"]
    assert len(results) == len(paperops_runner.COMMAND_SEQUENCE)


def test_failed_final_broker_refresh_remains_frozen_for_final_control(monkeypatch):
    ledger = _Ledger()

    def run_sequence(**kwargs):
        labels = [label for label, _ in kwargs["command_sequence"]]
        if labels == ["canonical_paper_control"]:
            assert ledger.execution_state()["frozen"] is True
            assert ledger.sync_calls == []
        return []

    monkeypatch.setattr(paperops_runner, "run_command_sequence", run_sequence)
    monkeypatch.setattr(paperops_runner.subprocess, "run", lambda command, **kwargs:
                        subprocess.CompletedProcess(command, 1, "", ""))
    _, refresh, reconciliation = paperops_runner._run_reconciled_command_sequence(
        ledger, allow_new_paper_submission=False, execution_owner_env={},
    )
    assert refresh.returncode == 1
    assert reconciliation["status"] == "blocked"


def test_reconciliation_requires_a_successful_fresh_mirror(monkeypatch) -> None:
    ledger = _Ledger()
    monkeypatch.setattr(
        paperops_runner.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "", ""),
    )

    refresh, reconciliation = _refresh_and_reconcile_paper_mirror(
        ledger,
        phase="post_paperops_submission",
        bootstrap=False,
    )

    assert refresh.returncode == 0
    assert reconciliation["status"] == "passed"
    assert ledger.sync_calls == [("post_paperops_submission", False)]
    assert ledger.freeze_reasons == []


def test_history_recovery_refreshes_twice_without_a_broker_write_command(monkeypatch):
    ledger = _Ledger()
    ledger.freeze_reasons.append("broker_reconciliation_disagreement:position_entry_allocation_unresolved:ITA")
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(paperops_runner.subprocess, "run", run)
    _refresh_and_reconcile_paper_mirror(ledger, phase="pre_paperops_submission", bootstrap=False)
    assert len(calls) == 2
    assert all(command[1:] == ["scripts/check_alpaca_paper_mirror.py", "--live"] for command in calls)


def test_failed_post_run_mirror_refresh_freezes_without_reconciling(monkeypatch) -> None:
    ledger = _Ledger()
    monkeypatch.setattr(
        paperops_runner.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, "", ""),
    )

    _refresh, reconciliation = _refresh_and_reconcile_paper_mirror(
        ledger,
        phase="post_paperops_submission",
        bootstrap=False,
    )

    assert reconciliation == {
        "status": "blocked",
        "blockers": ["post_paperops_submission_paper_mirror_refresh_failed"],
    }
    assert ledger.sync_calls == []
    assert ledger.freeze_reasons == [
        "post_paperops_submission_paper_mirror_refresh_failed"
    ]


def test_mirror_timeout_is_a_durable_freeze_not_an_uncaught_exception(monkeypatch):
    ledger = _Ledger()
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 90)
    monkeypatch.setattr(paperops_runner.subprocess, "run", timeout)
    refresh, result = _refresh_and_reconcile_paper_mirror(ledger, phase="pre_submit", bootstrap=False)
    assert refresh.returncode == 124
    assert result["status"] == "blocked"
    assert ledger.freeze_reasons == ["pre_submit_paper_mirror_refresh_failed"]


def test_owner_expiry_recovery_refreshes_twice(monkeypatch):
    ledger = _Ledger()
    ledger.freeze_reasons.append("post_paperops_submission_reconciliation_owner_lease_expired")
    calls = []
    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")
    monkeypatch.setattr(paperops_runner.subprocess, "run", run)
    _refresh_and_reconcile_paper_mirror(ledger, phase="pre_paperops_submission", bootstrap=False)
    assert len(calls) == 2
    assert all(command[1:] == ["scripts/check_alpaca_paper_mirror.py", "--live"] for command in calls)
