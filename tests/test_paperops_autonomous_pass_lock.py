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
