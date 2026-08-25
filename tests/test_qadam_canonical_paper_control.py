from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace

from orchestrator.config import Settings
from orchestrator.qadam_canonical_paper_control import (
    build_canonical_paper_control,
    validate_canonical_paper_control,
)
from orchestrator.qadam_operating_ledger import ExecutionLease, OperatingLedger


def _settings(tmp_path: Path) -> Settings:
    return replace(
        Settings.from_env(),
        runtime_dir=str(tmp_path),
        state_root=str(tmp_path),
        mode="paper",
        live_capital_enabled=False,
    )


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_epoch_contract(tmp_path: Path, now: datetime) -> None:
    epoch_id = "paper-epoch:canonical-control-test"
    _write(
        tmp_path / "qadam_experimental_paper_release_readiness.json",
        {
            "status": "experimental_paper_release_effective",
            "experimental_paper_release_effective": True,
            "experimental_paper_release_ready": True,
            "canonical_wrapper": "scripts/run_paperops_autonomous_pass.py",
            "paper_epoch_id": epoch_id,
            "blockers": [],
        },
    )
    _write(
        tmp_path / "current_paper_epoch.json",
        {
            "paper_epoch_id": epoch_id,
            "paper_epoch_kind": "clean_experimental_operator_epoch",
            "paper_growth_trial_calendar_started": True,
            "paper_growth_trial_state": "active_real_calendar",
            "paper_growth_trial_calendar_backfilled": False,
            "simulated_elapsed_time": False,
            "paper_epoch_started_at": now.isoformat(),
        },
    )
    _write(
        tmp_path / "qadam_long_backtest_lock.json",
        {
            "status": "released",
            "paperops_watch_only_mode": False,
            "release_mode": "explicit_operator_approved_experimental_paper_epoch",
            "release_approval_epoch_id": epoch_id,
        },
    )


def _prepare_ready_ledger(
    tmp_path: Path, monkeypatch, now: datetime
) -> tuple[Settings, OperatingLedger, ExecutionLease]:
    settings = _settings(tmp_path)
    _write_epoch_contract(tmp_path, now)
    ledger = OperatingLedger(settings)
    lease = ledger.acquire_execution_owner("canonical-control-test")
    monkeypatch.setenv("QADAM_EXECUTION_OWNER_ID", lease.owner_id)
    monkeypatch.setenv("QADAM_EXECUTION_OWNER_TOKEN", lease.token)
    ledger.record_direct_reconciliation(
        phase="canonical-control-test",
        expected={"broker": "alpaca-paper"},
        observed={"broker": "alpaca-paper"},
        blockers=[],
    )
    monkeypatch.setattr(
        "orchestrator.qadam_canonical_paper_control."
        "PaperAccountMirrorStore.latest_snapshot",
        lambda _self: SimpleNamespace(observed_at=now.isoformat()),
    )
    return settings, ledger, lease


def test_canonical_paper_control_is_ready_from_durable_authority(
    tmp_path: Path, monkeypatch
) -> None:
    now = datetime.now(timezone.utc)
    settings, _ledger, _lease = _prepare_ready_ledger(tmp_path, monkeypatch, now)

    artifact = build_canonical_paper_control(settings, current_time=now)

    assert artifact["status"] == "canonical_paper_control_ready"
    assert artifact["blockers"] == []
    assert artifact["authoritative_store"] == "qadam-control-plane.sqlite3"
    assert artifact["paper_only"] is True
    assert artifact["live_capital_enabled"] is False
    assert artifact["proof_credit_allowed"] is False
    assert validate_canonical_paper_control(artifact) == []


def test_canonical_paper_control_fails_without_execution_owner(
    tmp_path: Path, monkeypatch
) -> None:
    now = datetime.now(timezone.utc)
    settings, ledger, lease = _prepare_ready_ledger(tmp_path, monkeypatch, now)
    ledger.release_execution_owner(lease)

    artifact = build_canonical_paper_control(settings, current_time=now)

    assert artifact["status"] == "blocked"
    assert "execution_owner_active" in artifact["blockers"]


def test_canonical_paper_control_fails_when_reconciliation_is_stale(
    tmp_path: Path, monkeypatch
) -> None:
    now = datetime.now(timezone.utc)
    settings, _ledger, _lease = _prepare_ready_ledger(tmp_path, monkeypatch, now)

    artifact = build_canonical_paper_control(
        settings,
        current_time=datetime(2099, 1, 1, tzinfo=timezone.utc),
    )

    assert artifact["status"] == "blocked"
    assert "reconciliation_fresh" in artifact["blockers"]
    assert "paper_mirror_fresh" in artifact["blockers"]
