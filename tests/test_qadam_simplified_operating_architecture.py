from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from orchestrator.config import Settings
from orchestrator.qadam_operating_ledger import OperatingLedger
from orchestrator.qadam_simplified_operating_architecture import (
    build_simplified_operating_architecture_certification,
)


def _settings(tmp_path: Path) -> Settings:
    return replace(
        Settings.from_env(),
        runtime_dir=str(tmp_path),
        state_root=str(tmp_path),
        mode="paper",
        live_capital_enabled=False,
    )


def _services() -> dict[str, bool]:
    return {
        "canonical_operator_installed": True,
        "canonical_operator_running": True,
        "auxiliary_operator_installed": False,
        "auxiliary_operator_running": False,
    }


def test_architecture_passes_with_fresh_explained_runtime(tmp_path: Path, monkeypatch) -> None:
    settings = _settings(tmp_path)
    ledger = OperatingLedger(settings)
    lease = ledger.acquire_execution_owner("certification-test")
    monkeypatch.setenv("QADAM_EXECUTION_OWNER_ID", lease.owner_id)
    monkeypatch.setenv("QADAM_EXECUTION_OWNER_TOKEN", lease.token)
    ledger.record_direct_reconciliation(
        phase="test",
        expected={"broker": "paper"},
        observed={"broker": "paper"},
        blockers=[],
    )
    ledger.record_liveness_cycle(
        generation_id="test-generation",
        decisions=[],
        submitted_order_count=0,
    )
    ledger.release_execution_owner(lease)

    artifact = build_simplified_operating_architecture_certification(
        settings,
        service_state=_services(),
        current_time=datetime.now(timezone.utc),
    )

    assert artifact["status"] == "passed"
    assert artifact["blockers"] == []
    assert artifact["profit_guaranteed"] is False


def test_architecture_fails_closed_when_reconciliation_freezes_execution(
    tmp_path: Path, monkeypatch
) -> None:
    settings = _settings(tmp_path)
    ledger = OperatingLedger(settings)
    lease = ledger.acquire_execution_owner("certification-test")
    monkeypatch.setenv("QADAM_EXECUTION_OWNER_ID", lease.owner_id)
    monkeypatch.setenv("QADAM_EXECUTION_OWNER_TOKEN", lease.token)
    ledger.record_direct_reconciliation(
        phase="test",
        expected={"position": "known"},
        observed={"position": "unexpected"},
        blockers=["unexplained_broker_position:XAR"],
    )
    ledger.record_liveness_cycle(
        generation_id="test-generation",
        decisions=[],
        submitted_order_count=0,
    )
    ledger.release_execution_owner(lease)

    artifact = build_simplified_operating_architecture_certification(
        settings,
        service_state=_services(),
    )

    assert artifact["status"] == "blocked"
    assert "continuous_reconciliation_passed" in artifact["blockers"]
    assert "execution_not_frozen" in artifact["blockers"]
