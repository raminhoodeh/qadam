from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from orchestrator.config import Settings
from orchestrator.qadam_control_plane_bridge import persist_router_state
from orchestrator.qadam_control_plane_store import ControlPlaneError, ControlPlaneStore
from orchestrator.qadam_operating_ledger import (
    EXECUTION_OWNER_ID_ENV,
    EXECUTION_OWNER_TOKEN_ENV,
    ExecutionOwnerError,
    OperatingLedger,
)
import orchestrator.qadam_operating_ledger as ledger_module


def _settings(tmp_path: Path) -> Settings:
    return replace(
        Settings.from_env(),
        runtime_dir=str(tmp_path),
        state_root=str(tmp_path),
        mode="paper",
        live_capital_enabled=False,
    )


def _router_state() -> dict:
    generated = "2026-08-25T14:00:00+00:00"
    setup = {
        "setup_id": "setup-1",
        "evidence_class": "experimental_unvalidated",
        "strategy_family_id": "defence_repricing_geopolitical_watch",
        "execution_symbol": "XAR",
        "instrument": "XAR",
        "direction": "long",
        "proposed_notional_usd": 500.0,
        "maximum_loss_at_invalidation": 10.0,
        "lineage": {
            "hypothesis_id": "hypothesis-1",
            "research_goal_id": "goal-1",
            "strategy_version_id": "v1",
            "risk_proposal_id": "risk-1",
        },
    }
    decision = {
        "router_decision_id": "decision-1",
        "router_execution_generation_id": "generation-1",
        "setup_id": "setup-1",
        "hypothesis_id": "hypothesis-1",
        "evidence_class": "experimental_unvalidated",
        "candidate_identity_id": "candidate-1",
        "decision_generation_id": "generation-1",
        "lineage": setup["lineage"],
        "instrument": "XAR",
        "execution_symbol": "XAR",
        "direction": "long",
        "final_state": "experimental-paper-review-candidate",
        "final_reason": "Every hard requirement passed.",
        "primary_root_cause": None,
        "repair_reasons": [],
        "hard_vetoes": [],
        "hold_reasons": [],
        "gate_snapshot": {
            "source_quorum_passed": True,
            "duplicate_exposure_conflict": False,
            "drawdown_context_complete": True,
            "drawdown_breached": False,
            "qctrl_state": "pass",
            "instrument_paperable": True,
            "route": "guarded_alpaca_paper_via_paperops",
            "shadow_promotion_ready": True,
            "risk_proposal_complete": True,
            "decision_time_shadow_snapshot_ready": True,
            "research_lock_release_effective": True,
        },
        "idempotency_material": {"idempotency_key": "key-1"},
        "generated_at": generated,
    }
    return {"generated_at": generated, "setups": [setup], "decisions": [decision]}


def _candidate() -> dict:
    return {
        "paperops_handoff_id": "handoff-1",
        "router_decision_id": "decision-1",
        "evidence_class": "experimental_unvalidated",
        "notional_usd": 500.0,
        "risk_usd": 10.0,
        "invalidation": "Exit if the catalyst is disproven.",
        "horizon": "3d_forward",
        "request_preview": {
            "client_order_id": "key-1",
            "symbol": "XAR",
            "side": "buy",
            "qty": 2,
        },
    }


def _persist_ready_lineage(settings: Settings) -> dict:
    state = _router_state()
    assert persist_router_state(state, settings)["status"] == "passed"
    inserted = ControlPlaneStore.from_settings(settings).accept_handoff(
        handoff_id="handoff-1",
        decision_id="decision-1",
        candidate_identity="candidate-1",
        idempotency_key="key-1",
        payload={
            "paperops_handoff_id": "handoff-1",
            "router_decision_id": "decision-1",
            "candidate_identity_id": "candidate-1",
            "proposed_notional_usd": 500.0,
            "maximum_loss_at_invalidation": 10.0,
            "invalidation": "Exit if the catalyst is disproven.",
            "horizon": "3d_forward",
            "idempotency_material": {"idempotency_key": "key-1"},
        },
        created_at="2026-08-25T14:00:01+00:00",
    )
    assert inserted is True
    return state


def _activate(monkeypatch: pytest.MonkeyPatch, ledger: OperatingLedger):
    lease = ledger.acquire_execution_owner("test-owner")
    monkeypatch.setenv(EXECUTION_OWNER_ID_ENV, lease.owner_id)
    monkeypatch.setenv(EXECUTION_OWNER_TOKEN_ENV, lease.token)
    return lease


def test_single_owner_and_complete_research_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    state = _persist_ready_lineage(settings)
    ledger = OperatingLedger(settings)
    imported = ledger.record_research_generation(state)
    assert imported == {"hypothesis_count": 1, "risk_decision_inserted_count": 1}
    lease = _activate(monkeypatch, ledger)
    with pytest.raises(ExecutionOwnerError, match="execution_owner_busy"):
        ledger.acquire_execution_owner("second-owner")
    assert len(ledger.store.read_table("hypotheses")) == 1
    assert len(ledger.store.read_table("risk_decisions")) == 1
    ledger.release_execution_owner(lease)


def test_order_and_exit_plan_are_one_atomic_prewrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    state = _persist_ready_lineage(settings)
    ledger = OperatingLedger(settings)
    ledger.record_research_generation(state)
    _activate(monkeypatch, ledger)

    prepared = ledger.prepare_order(_candidate())

    assert prepared["trading_lane"] == "discovery"
    assert prepared["exit_plan"]["stop_price"] > 0
    assert prepared["exit_plan"]["take_profit_price"] > prepared["exit_plan"]["stop_price"]
    integrity = ledger.store.integrity_report()
    assert integrity["status"] == "passed"
    assert integrity["consistency_counts"]["canonical_order_without_exit_plan"] == 0


def test_missing_optional_evidence_does_not_block_but_hard_evidence_does(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    state = _persist_ready_lineage(settings)
    ledger = OperatingLedger(settings)
    ledger.record_research_generation(state)
    _activate(monkeypatch, ledger)
    candidate = _candidate()
    candidate["optional_volume_context"] = None
    assert ledger.prepare_order(candidate)["order_key"] == "key-1"

    second = _candidate()
    second["request_preview"] = {
        **second["request_preview"],
        "client_order_id": "key-2",
        "symbol": "SMH",
        "side": "",
    }
    second["router_decision_id"] = None
    with pytest.raises(ControlPlaneError, match="direction_missing"):
        ledger.prepare_order(second)


def test_duplicate_open_position_is_a_hard_ledger_block(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    state = _persist_ready_lineage(settings)
    ledger = OperatingLedger(settings)
    ledger.record_research_generation(state)
    _activate(monkeypatch, ledger)
    prepared = ledger.prepare_order(_candidate())
    with ledger.store.transaction() as connection:
        connection.execute(
            "UPDATE canonical_orders SET state='filled' WHERE order_key='key-1'"
        )
        connection.execute(
            "INSERT INTO positions (position_key,instrument,decision_id,handoff_id,"
            "exit_plan_id,trading_lane,quantity,average_entry_price,current_price,"
            "unrealized_pnl,state,payload_json,payload_sha256,opened_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "paper:XAR",
                "XAR",
                "decision-1",
                None,
                prepared["exit_plan"]["exit_plan_id"],
                "discovery",
                2.0,
                250.0,
                250.0,
                0.0,
                "open",
                "{}",
                "payload-sha",
                "2026-08-25T14:00:00+00:00",
                "2026-08-25T14:00:00+00:00",
            ),
        )
    duplicate = _candidate()
    duplicate["request_preview"] = {
        **duplicate["request_preview"],
        "client_order_id": "key-2",
    }
    with pytest.raises(ControlPlaneError, match="duplicate_open_position"):
        ledger.prepare_order(duplicate)


def test_only_passed_reconciliation_can_unfreeze_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = OperatingLedger(_settings(tmp_path))
    _activate(monkeypatch, ledger)
    failed = ledger.record_direct_reconciliation(
        phase="pre_submit",
        expected={"order": "known"},
        observed={"order": "missing"},
        blockers=["order_missing"],
    )
    assert failed["status"] == "blocked"
    assert ledger.execution_state()["frozen"] == 1
    passed = ledger.record_direct_reconciliation(
        phase="recovery",
        expected={"broker": "truth"},
        observed={"broker": "truth"},
        blockers=[],
    )
    assert passed["status"] == "passed"
    assert ledger.execution_state()["frozen"] == 0


def test_unexplained_broker_activity_freezes_after_bootstrap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class UnknownOrder(SimpleNamespace):
        def to_dict(self) -> dict:
            return dict(self.__dict__)

    class FakeMirror:
        def __init__(self, **_kwargs) -> None:
            pass

        def latest_snapshot(self):
            now = datetime.now(timezone.utc).isoformat()
            return SimpleNamespace(
                observed_at=now,
                equity=100_000.0,
                cash=100_000.0,
            )

        def read_orders(self):
            return (
                UnknownOrder(
                    client_order_id="outside-ledger-order",
                    order_id="raw-broker-order-id",
                    instrument="SMH",
                    direction="long",
                    status="accepted",
                    quantity=1.0,
                    filled_quantity=0.0,
                    filled_avg_price=None,
                    filled_at=None,
                    submitted_at=datetime.now(timezone.utc).isoformat(),
                ),
            )

        def read_positions(self):
            return ()

        def read_closed_trades(self):
            return ()

    monkeypatch.setattr(ledger_module, "PaperAccountMirrorStore", FakeMirror)
    ledger = OperatingLedger(_settings(tmp_path))
    _activate(monkeypatch, ledger)
    result = ledger.sync_paper_mirror(phase="continuous", bootstrap=False)
    assert result["status"] == "blocked"
    assert "unexplained_broker_order:outside-ledger-order" in result["blockers"]
    assert ledger.execution_state()["frozen"] == 1


def test_bootstrap_import_arms_actionable_exit_for_existing_position(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class ExistingPosition(SimpleNamespace):
        def to_dict(self) -> dict:
            return dict(self.__dict__)

    class FakeMirror:
        def __init__(self, **_kwargs) -> None:
            pass

        def latest_snapshot(self):
            now = datetime.now(timezone.utc).isoformat()
            return SimpleNamespace(observed_at=now, equity=100_000.0, cash=99_500.0)

        def read_orders(self):
            return ()

        def read_positions(self):
            return (
                ExistingPosition(
                    paper_epoch_id="epoch-1",
                    instrument="BNO",
                    direction="long",
                    quantity=2.0,
                    entry_price=50.0,
                    current_price=51.0,
                    unrealized_pnl=2.0,
                    opened_at="2026-08-24T14:30:00+00:00",
                ),
            )

        def read_closed_trades(self):
            return ()

    monkeypatch.setattr(ledger_module, "PaperAccountMirrorStore", FakeMirror)
    ledger = OperatingLedger(_settings(tmp_path))
    _activate(monkeypatch, ledger)

    result = ledger.sync_paper_mirror(phase="bootstrap", bootstrap=True)

    assert result["status"] == "passed"
    position = ledger.store.read_table("positions")[0]
    exit_plan = ledger.store.read_table("exit_plans")[0]
    assert position["exit_plan_id"] == exit_plan["exit_plan_id"]
    assert exit_plan["state"] == "monitoring"
    assert exit_plan["stop_price"] == pytest.approx(49.98)
    assert exit_plan["take_profit_price"] == pytest.approx(53.04)
    assert exit_plan["maximum_holding_sessions"] == 3
    assert exit_plan["invalidation"]


def test_liveness_never_hides_where_a_setup_stopped(tmp_path: Path) -> None:
    ledger = OperatingLedger(_settings(tmp_path))
    result = ledger.record_liveness_cycle(
        generation_id="generation-1",
        decisions=[
            {
                "setup_id": "setup-1",
                "execution_symbol": "SMH",
                "evidence_class": "experimental_unvalidated",
                "final_state": "hold",
                "primary_root_cause": "liquidity_measurement_missing",
                "final_reason": "A current tradable quote was unavailable.",
            }
        ],
        submitted_order_count=0,
        market_session_date="2026-08-25",
    )
    assert result["status"] == "idle_explained"
    assert result["setup_outcomes"][0]["stopped_at"] == "liquidity_measurement_missing"
    assert result["silence_can_indicate_health"] is False


def test_risk_decision_identity_is_immutable(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    state = _persist_ready_lineage(settings)
    ledger = OperatingLedger(settings)
    ledger.record_research_generation(state)

    with pytest.raises(
        ControlPlaneError,
        match="immutable_identity_collision:risk_decisions:risk-1",
    ):
        ledger.record_risk_decision(
            risk_decision_id="risk-1",
            decision_id="decision-1",
            trading_lane="discovery",
            state="experimental-paper-review-candidate",
            proposed_notional=500.0,
            approved_notional=250.0,
            payload={"changed": True},
        )


def test_order_requires_handoff_decision_and_approved_risk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    state = _persist_ready_lineage(settings)
    ledger = OperatingLedger(settings)
    ledger.record_research_generation(state)
    _activate(monkeypatch, ledger)

    missing_lineage = _candidate()
    missing_lineage["paperops_handoff_id"] = None
    missing_lineage["router_decision_id"] = None
    with pytest.raises(ControlPlaneError, match="canonical_decision_id_missing"):
        ledger.prepare_order(missing_lineage)

    with ledger.store.transaction() as connection:
        connection.execute("DELETE FROM risk_decisions WHERE decision_id='decision-1'")
    with pytest.raises(ControlPlaneError, match="canonical_risk_decision_missing"):
        ledger.prepare_order(_candidate())


def test_old_order_does_not_explain_a_new_broker_position(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Position(SimpleNamespace):
        def to_dict(self) -> dict:
            return dict(self.__dict__)

    class FakeMirror:
        def __init__(self, **_kwargs) -> None:
            pass

        def latest_snapshot(self):
            now = datetime.now(timezone.utc).isoformat()
            return SimpleNamespace(observed_at=now, equity=100_000.0, cash=99_000.0)

        def read_orders(self):
            return ()

        def read_positions(self):
            return (
                Position(
                    paper_epoch_id="paper",
                    instrument="SMH",
                    quantity=1.0,
                    entry_price=250.0,
                    current_price=251.0,
                    unrealized_pnl=1.0,
                    opened_at="2026-08-25T14:00:00+00:00",
                ),
            )

        def read_closed_trades(self):
            return ()

    monkeypatch.setattr(ledger_module, "PaperAccountMirrorStore", FakeMirror)
    ledger = OperatingLedger(_settings(tmp_path))
    _activate(monkeypatch, ledger)
    with ledger.store.transaction() as connection:
        connection.execute(
            "INSERT INTO exit_plans (exit_plan_id,decision_id,handoff_id,instrument,side,"
            "stop_price,take_profit_price,maximum_holding_sessions,invalidation,state,"
            "payload_json,payload_sha256,created_at,updated_at) VALUES "
            "('old-plan',NULL,NULL,'SMH','buy',240,270,3,'old','mirror_import','{}','sha',"
            "'2026-01-01T00:00:00+00:00','2026-01-01T00:00:00+00:00')"
        )
        connection.execute(
            "INSERT INTO canonical_orders (order_key,handoff_id,decision_id,exit_plan_id,"
            "instrument,side,quantity,trading_lane,state,broker_order_id_hash,payload_json,"
            "payload_sha256,created_at,updated_at) VALUES "
            "('old-order',NULL,NULL,'old-plan','SMH','buy',1,'discovery','filled',NULL,"
            "'{}','sha','2026-01-01T00:00:00+00:00','2026-01-01T00:00:00+00:00')"
        )

    result = ledger.sync_paper_mirror(phase="continuous", bootstrap=False)

    assert result["status"] == "blocked"
    assert "unexplained_broker_position:SMH" in result["blockers"]


def test_exit_order_is_precommitted_and_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = _settings(tmp_path)
    state = _persist_ready_lineage(settings)
    ledger = OperatingLedger(settings)
    ledger.record_research_generation(state)
    _activate(monkeypatch, ledger)
    entry = ledger.prepare_order(_candidate())
    with ledger.store.transaction() as connection:
        connection.execute(
            "UPDATE canonical_orders SET state='filled' WHERE order_key='key-1'"
        )
        connection.execute(
            "INSERT INTO positions (position_key,instrument,decision_id,handoff_id,"
            "exit_plan_id,trading_lane,quantity,average_entry_price,current_price,"
            "unrealized_pnl,state,payload_json,payload_sha256,opened_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "paper:XAR",
                "XAR",
                "decision-1",
                "handoff-1",
                entry["exit_plan"]["exit_plan_id"],
                "discovery",
                2.0,
                250.0,
                260.0,
                20.0,
                "open",
                "{}",
                "sha",
                "2026-08-25T14:00:00+00:00",
                "2026-08-25T14:00:00+00:00",
            ),
        )
    exit_candidate = {
        "position_key": "paper:XAR",
        "exit_plan_id": entry["exit_plan"]["exit_plan_id"],
        "symbol": "XAR",
        "quantity": 2.0,
        "exit_side": "sell",
        "trading_lane": "discovery",
        "trigger": "take_profit",
    }

    first = ledger.prepare_exit_order(exit_candidate)
    second = ledger.prepare_exit_order(exit_candidate)

    assert first["order_key"] == second["order_key"]
    assert first["already_prepared"] is False
    assert second["already_prepared"] is True
    assert len(ledger.store.read_table("canonical_orders")) == 2


def test_integrity_detects_no_missing_exit_or_multiple_owner(tmp_path: Path) -> None:
    store = ControlPlaneStore.from_settings(_settings(tmp_path))
    report = store.integrity_report()
    assert report["consistency_counts"]["canonical_order_without_exit_plan"] == 0
    assert report["consistency_counts"]["multiple_active_execution_leases"] == 0
