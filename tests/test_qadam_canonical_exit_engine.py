from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from orchestrator.config import Settings
from orchestrator.qadam_control_plane_store import ControlPlaneError
from orchestrator.qadam_operating_ledger import (
    EXECUTION_OWNER_ID_ENV,
    EXECUTION_OWNER_TOKEN_ENV,
    ExecutionOwnerError,
    OperatingLedger,
)
import orchestrator.qadam_canonical_exit_engine as exit_engine
from orchestrator.paperops_paper_exit_path import _close_alpaca_paper_position


def _settings(tmp_path: Path) -> Settings:
    return replace(
        Settings.from_env(),
        runtime_dir=str(tmp_path),
        state_root=str(tmp_path),
        mode="paper",
        live_capital_enabled=False,
    )


def _seed_due_position(ledger: OperatingLedger) -> None:
    timestamp = "2026-08-20T14:30:00+00:00"
    with ledger.store.transaction() as connection:
        connection.execute(
            "INSERT INTO exit_plans (exit_plan_id,decision_id,handoff_id,instrument,side,"
            "stop_price,take_profit_price,maximum_holding_sessions,invalidation,state,"
            "payload_json,payload_sha256,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "exit-plan-1",
                None,
                None,
                "BNO",
                "buy",
                49.0,
                54.0,
                3,
                "Exit if the disruption thesis is invalidated.",
                "monitoring",
                "{}",
                "exit-sha",
                timestamp,
                timestamp,
            ),
        )
        connection.execute(
            "INSERT INTO positions (position_key,instrument,decision_id,handoff_id,"
            "exit_plan_id,trading_lane,quantity,average_entry_price,current_price,"
            "unrealized_pnl,state,payload_json,payload_sha256,opened_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "epoch:BNO",
                "BNO",
                None,
                None,
                "exit-plan-1",
                "discovery",
                2.0,
                50.0,
                48.5,
                -3.0,
                "open",
                "{}",
                "position-sha",
                timestamp,
                timestamp,
            ),
        )


def _activate(monkeypatch: pytest.MonkeyPatch, ledger: OperatingLedger) -> None:
    lease = ledger.acquire_execution_owner("canonical-exit-test")
    monkeypatch.setenv(EXECUTION_OWNER_ID_ENV, lease.owner_id)
    monkeypatch.setenv(EXECUTION_OWNER_TOKEN_ENV, lease.token)


def test_execute_mode_requires_canonical_owner(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    ledger = OperatingLedger(settings)
    _seed_due_position(ledger)

    with pytest.raises(ExecutionOwnerError, match="execution_owner_lease_missing"):
        exit_engine.build_canonical_exit_engine(settings, execute_due_exits=True)


def test_low_level_close_refuses_missing_canonical_prewrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    ledger = OperatingLedger(settings)
    _seed_due_position(ledger)
    _activate(monkeypatch, ledger)

    result = _close_alpaca_paper_position(
        settings=settings,
        candidate=ledger.due_exit_candidates(
            current_time=datetime(2026, 8, 25, 15, 0, tzinfo=timezone.utc)
        )[0],
    )

    assert result["close_attempted"] is False
    assert result["failure_class"] == "canonical_exit_prewrite_missing"


def test_canonical_exit_prewrite_must_match_exact_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    ledger = OperatingLedger(settings)
    _seed_due_position(ledger)
    _activate(monkeypatch, ledger)
    candidate = ledger.due_exit_candidates(
        current_time=datetime(2026, 8, 25, 15, 0, tzinfo=timezone.utc)
    )[0]
    prepared = ledger.prepare_exit_order(candidate)
    ledger.mark_order_submitting(prepared["order_key"])

    verified = ledger.assert_canonical_exit_submission(
        order_key=prepared["order_key"],
        candidate=candidate,
    )
    assert verified["order_key"] == prepared["order_key"]

    wrong_candidate = {**candidate, "quantity": candidate["quantity"] + 1}
    with pytest.raises(ControlPlaneError, match="canonical_exit_prewrite_invalid"):
        ledger.assert_canonical_exit_submission(
            order_key=prepared["order_key"],
            candidate=wrong_candidate,
        )


def test_due_exit_is_precommitted_then_reconciled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    ledger = OperatingLedger(settings)
    _seed_due_position(ledger)
    _activate(monkeypatch, ledger)
    reconciliation_phases: list[str] = []

    monkeypatch.setattr(
        exit_engine,
        "_live_paper_order_exposure_guard",
        lambda **_kwargs: {
            "status": "passed",
            "checks": {"regular_session_open": True},
        },
    )
    monkeypatch.setattr(
        exit_engine,
        "sync_alpaca_paper_account_readonly",
        lambda _settings: {"status": "ok"},
    )

    def _sync(self, *, phase: str, bootstrap: bool = False):
        reconciliation_phases.append(phase)
        return {"status": "passed", "blockers": [], "bootstrap": bootstrap}

    monkeypatch.setattr(OperatingLedger, "sync_paper_mirror", _sync)
    monkeypatch.setattr(
        exit_engine,
        "_close_alpaca_paper_position",
        lambda **_kwargs: {
            "close_attempted": True,
            "close_succeeded": True,
            "failure_class": None,
            "receipt": {"broker_order_id_hash": "broker-hash"},
        },
    )

    artifact = exit_engine.build_canonical_exit_engine(
        settings,
        execute_due_exits=True,
        current_time=datetime(2026, 8, 25, 15, 0, tzinfo=timezone.utc),
    )

    assert artifact["status"] == "close_requested"
    assert artifact["close_requested_count"] == 1
    assert reconciliation_phases == ["pre_exit:BNO", "post_exit:BNO"]
    order = ledger.store.read_table("canonical_orders")[0]
    assert order["state"] == "submitted"
    assert order["broker_order_id_hash"] == "broker-hash"
    assert ledger.store.read_table("exit_plans")[0]["state"] == "close_requested"
