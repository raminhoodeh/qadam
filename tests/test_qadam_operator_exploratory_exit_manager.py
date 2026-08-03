from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path

from orchestrator.config import Settings
import orchestrator.qadam_operator_exploratory_exit_manager as manager


def _write(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _sleeve() -> dict[str, object]:
    return {
        "schema_version": "qadam_operator_exploratory_sleeve.v1",
        "artifact_type": "qadam_operator_exploratory_sleeve",
        "status": "ready_for_guarded_paper_submission",
        "sleeve_id": "operator-exploratory-sleeve:test",
        "request_id": "operator-request:test",
        "explicit_operator_approval": True,
        "paper_only": True,
        "live_capital_enabled": False,
        "legs": [
            {
                "leg_id": "operator-exploratory-leg:test",
                "execution_symbol": "SLV",
                "client_order_id": "q7-operator-sleeve-test",
                "side": "buy",
                "quantity": 10,
                "take_profit_price": 53.0,
                "stop_loss_price": 50.0,
                "maximum_holding_sessions": 5,
            }
        ],
    }


def _submission() -> dict[str, object]:
    return {
        "schema_version": "qadam_operator_exploratory_sleeve_submission.v1",
        "artifact_type": "qadam_operator_exploratory_sleeve_submission",
        "generated_at": "2026-08-03T13:45:00+00:00",
        "status": "submitted_to_alpaca_paper",
        "sleeve_id": "operator-exploratory-sleeve:test",
        "post_succeeded_count": 1,
    }


def _calendar() -> list[dict[str, str]]:
    return [
        {"date": day, "open": "09:30", "close": "16:00"}
        for day in ("2026-08-03", "2026-08-04", "2026-08-05", "2026-08-06", "2026-08-07")
    ]


def _orders() -> list[dict[str, object]]:
    return [
        {
            "id": "parent-raw-id",
            "client_order_id": "q7-operator-sleeve-test",
            "symbol": "SLV",
            "side": "buy",
            "type": "market",
            "status": "filled",
            "qty": "10",
            "filled_at": "2026-08-03T13:46:00Z",
            "time_in_force": "gtc",
            "legs": [
                {
                    "id": "target-raw-id",
                    "symbol": "SLV",
                    "side": "sell",
                    "type": "limit",
                    "status": "new",
                    "qty": "10",
                    "limit_price": "53.00",
                    "time_in_force": "gtc",
                },
                {
                    "id": "stop-raw-id",
                    "symbol": "SLV",
                    "side": "sell",
                    "type": "stop",
                    "status": "held",
                    "qty": "10",
                    "stop_price": "50.00",
                    "time_in_force": "gtc",
                },
            ],
        }
    ]


class FakeBroker:
    def __init__(self) -> None:
        self.orders = _orders()
        self.positions = [{"symbol": "SLV", "side": "long", "qty": "10"}]
        self.cancel_calls: list[str] = []
        self.oco_calls: list[dict[str, object]] = []
        self.close_calls: list[tuple[str, float]] = []

    def snapshot(self, *, start: str, end: str, after: str) -> dict[str, object]:
        assert start == "2026-08-01"
        assert end == "2026-09-17"
        assert after.startswith("2026-08-02")
        return {
            "positions": deepcopy(self.positions),
            "orders": deepcopy(self.orders),
            "clock": {"is_open": True},
            "calendar": _calendar(),
        }

    def cancel_order(self, order_id: str) -> dict[str, object]:
        self.cancel_calls.append(order_id)
        for child in self.orders[0]["legs"]:
            child["status"] = "canceled"
        return {"requested": True, "http_status": 204}

    def submit_oco(
        self,
        *,
        symbol: str,
        side: str,
        quantity: float,
        take_profit_price: float,
        stop_loss_price: float,
        client_order_id: str,
    ) -> dict[str, object]:
        self.oco_calls.append(
            {
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "take_profit_price": take_profit_price,
                "stop_loss_price": stop_loss_price,
                "client_order_id": client_order_id,
            }
        )
        self.orders.append(
            {
                "id": "oco-parent-raw-id",
                "client_order_id": client_order_id,
                "symbol": symbol,
                "side": side,
                "type": "limit",
                "status": "new",
                "qty": str(quantity),
                "time_in_force": "gtc",
                "legs": [
                    {
                        "id": "oco-stop-raw-id",
                        "symbol": symbol,
                        "side": side,
                        "type": "stop",
                        "status": "held",
                        "qty": str(quantity),
                        "time_in_force": "gtc",
                    }
                ],
            }
        )
        return {
            "requested": True,
            "http_status": 200,
            "broker_order_id_hash": "oco-hash",
            "broker_order_status": "new",
        }

    def close_position(self, symbol: str, quantity: float) -> dict[str, object]:
        self.close_calls.append((symbol, quantity))
        self.positions = []
        return {
            "requested": True,
            "http_status": 200,
            "broker_order_id_hash": "close-hash",
            "broker_order_status": "accepted",
        }


def _settings(tmp_path: Path) -> Settings:
    return replace(
        Settings.from_env(),
        runtime_dir=str(tmp_path),
        mode="paper",
        live_capital_enabled=False,
    )


def _ready_runtime(tmp_path: Path) -> tuple[dict[str, object], dict[str, object]]:
    sleeve = _sleeve()
    submission = _submission()
    _write(tmp_path / manager.SLEEVE_ARTIFACT, sleeve)
    _write(tmp_path / manager.SUBMISSION_ARTIFACT, submission)
    approval = manager.build_exit_approval(
        sleeve=sleeve,
        submission=submission,
        explicit_operator_approval=True,
    )
    _write(tmp_path / manager.APPROVAL_ARTIFACT, approval)
    return sleeve, submission


def _paper_endpoint(_settings: Settings) -> dict[str, object]:
    return {
        "paper_endpoint_confirmed": True,
        "alpaca_api_key_configured": True,
        "alpaca_api_secret_configured": True,
    }


def test_price_exits_remain_primary_before_fifth_session(
    tmp_path: Path, monkeypatch
) -> None:
    _ready_runtime(tmp_path)
    monkeypatch.setattr(manager, "_endpoint_context", _paper_endpoint)
    broker = FakeBroker()

    artifact = manager.build_operator_exploratory_exit_manager(
        _settings(tmp_path),
        execute_due_exits=True,
        broker_client=broker,
        current_time=datetime(2026, 8, 4, 16, 0, tzinfo=timezone.utc),
        event_log_path=tmp_path / "events.jsonl",
    )

    assert artifact["status"] == "monitoring_price_and_time_exits"
    assert artifact["protected_open_position_count"] == 1
    assert artifact["time_exit_due_count"] == 0
    assert artifact["broker_write_called_count"] == 0
    assert broker.cancel_calls == []
    assert broker.close_calls == []
    assert artifact["validation_errors"] == []


def test_fifth_session_cancels_protection_then_closes_exact_position_once(
    tmp_path: Path, monkeypatch
) -> None:
    _ready_runtime(tmp_path)
    monkeypatch.setattr(manager, "_endpoint_context", _paper_endpoint)
    broker = FakeBroker()
    due = datetime(2026, 8, 7, 19, 30, tzinfo=timezone.utc)

    cancel_cycle = manager.build_operator_exploratory_exit_manager(
        _settings(tmp_path),
        execute_due_exits=True,
        broker_client=broker,
        current_time=due,
        event_log_path=tmp_path / "events.jsonl",
    )
    assert cancel_cycle["status"] == "risk_reduction_actions_requested"
    assert cancel_cycle["protective_cancel_called_count"] == 1
    assert cancel_cycle["position_close_called_count"] == 0
    assert broker.cancel_calls == ["target-raw-id"]

    close_cycle = manager.build_operator_exploratory_exit_manager(
        _settings(tmp_path),
        execute_due_exits=True,
        broker_client=broker,
        current_time=due,
        event_log_path=tmp_path / "events.jsonl",
    )
    assert close_cycle["position_close_called_count"] == 1
    assert broker.close_calls == [("SLV", 10.0)]

    settled_cycle = manager.build_operator_exploratory_exit_manager(
        _settings(tmp_path),
        execute_due_exits=True,
        broker_client=broker,
        current_time=due,
        event_log_path=tmp_path / "events.jsonl",
    )
    assert settled_cycle["status"] == "complete_all_legs_closed"
    assert settled_cycle["broker_write_called_count"] == 0
    assert broker.close_calls == [("SLV", 10.0)]


def test_position_scope_mismatch_fails_closed(tmp_path: Path, monkeypatch) -> None:
    _ready_runtime(tmp_path)
    monkeypatch.setattr(manager, "_endpoint_context", _paper_endpoint)
    broker = FakeBroker()
    broker.positions[0]["qty"] = "12"

    artifact = manager.build_operator_exploratory_exit_manager(
        _settings(tmp_path),
        execute_due_exits=True,
        broker_client=broker,
        current_time=datetime(2026, 8, 7, 19, 30, tzinfo=timezone.utc),
        event_log_path=tmp_path / "events.jsonl",
    )

    assert artifact["status"] == "repair_required"
    assert artifact["broker_write_called_count"] == 0
    assert artifact["legs"][0]["repair_reasons"] == [
        "position_no_longer_matches_exact_sleeve_scope"
    ]


def test_unapproved_or_nonpaper_context_never_reads_or_writes(
    tmp_path: Path, monkeypatch
) -> None:
    _ready_runtime(tmp_path)
    approval = json.loads((tmp_path / manager.APPROVAL_ARTIFACT).read_text(encoding="utf-8"))
    approval["explicit_operator_exit_approval"] = False
    _write(tmp_path / manager.APPROVAL_ARTIFACT, approval)
    monkeypatch.setattr(
        manager,
        "_endpoint_context",
        lambda _settings: {
            "paper_endpoint_confirmed": False,
            "alpaca_api_key_configured": True,
            "alpaca_api_secret_configured": True,
        },
    )
    broker = FakeBroker()

    artifact = manager.build_operator_exploratory_exit_manager(
        _settings(tmp_path),
        execute_due_exits=True,
        broker_client=broker,
        current_time=datetime(2026, 8, 7, 19, 30, tzinfo=timezone.utc),
    )

    assert artifact["status"] == "blocked"
    assert "approval_not_explicit" in artifact["blockers"]
    assert "paper_endpoint_not_confirmed" in artifact["blockers"]
    assert artifact["broker_write_called_count"] == 0
    assert broker.cancel_calls == []
    assert broker.close_calls == []


def test_manager_artifact_never_contains_raw_broker_identifiers(
    tmp_path: Path, monkeypatch
) -> None:
    _ready_runtime(tmp_path)
    monkeypatch.setattr(manager, "_endpoint_context", _paper_endpoint)
    artifact = manager.build_operator_exploratory_exit_manager(
        _settings(tmp_path),
        execute_due_exits=False,
        broker_client=FakeBroker(),
        current_time=datetime(2026, 8, 4, 16, 0, tzinfo=timezone.utc),
    )
    encoded = json.dumps(artifact)
    assert "parent-raw-id" not in encoded
    assert "target-raw-id" not in encoded
    assert "stop-raw-id" not in encoded
    assert manager.validate_operator_exploratory_exit_manager(artifact) == []


def test_day_protection_is_rearmed_as_closing_only_gtc_oco(
    tmp_path: Path, monkeypatch
) -> None:
    _ready_runtime(tmp_path)
    monkeypatch.setattr(manager, "_endpoint_context", _paper_endpoint)
    broker = FakeBroker()
    broker.orders[0]["time_in_force"] = "day"
    for child in broker.orders[0]["legs"]:
        child["time_in_force"] = "day"
    before_due = datetime(2026, 8, 4, 16, 0, tzinfo=timezone.utc)

    cancel_cycle = manager.build_operator_exploratory_exit_manager(
        _settings(tmp_path),
        execute_due_exits=True,
        broker_client=broker,
        current_time=before_due,
        event_log_path=tmp_path / "events.jsonl",
    )
    assert cancel_cycle["status"] == "risk_reduction_actions_requested"
    assert cancel_cycle["protective_cancel_called_count"] == 1
    assert broker.cancel_calls == ["target-raw-id"]

    submit_cycle = manager.build_operator_exploratory_exit_manager(
        _settings(tmp_path),
        execute_due_exits=True,
        broker_client=broker,
        current_time=before_due,
        event_log_path=tmp_path / "events.jsonl",
    )
    assert submit_cycle["persistent_protection_submit_called_count"] == 1
    assert broker.oco_calls[0]["side"] == "sell"
    assert broker.oco_calls[0]["quantity"] == 10.0
    assert broker.oco_calls[0]["take_profit_price"] == 53.0
    assert broker.oco_calls[0]["stop_loss_price"] == 50.0

    protected_cycle = manager.build_operator_exploratory_exit_manager(
        _settings(tmp_path),
        execute_due_exits=True,
        broker_client=broker,
        current_time=before_due,
        event_log_path=tmp_path / "events.jsonl",
    )
    assert protected_cycle["status"] == "monitoring_price_and_time_exits"
    assert protected_cycle["legs"][0]["persistent_price_exit_protection"] is True
    assert len(broker.oco_calls) == 1
