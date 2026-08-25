from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from orchestrator.config import Settings
from orchestrator.qadam_pending_order_quarantine import quarantine_pending_paper_orders


class FakeClient:
    def __init__(self, orders: list[dict[str, object]]) -> None:
        self.orders = orders
        self.cancelled: list[str] = []

    def list_open_orders(self) -> list[dict[str, object]]:
        return self.orders

    def cancel_order(self, order_id: str) -> None:
        self.cancelled.append(order_id)


def _settings(tmp_path: Path) -> Settings:
    settings = Settings.from_env()
    return replace(
        settings,
        mode="paper",
        live_capital_enabled=False,
        runtime_dir=str(tmp_path),
    )


def test_quarantine_is_cutoff_bounded_and_dry_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "orchestrator.qadam_pending_order_quarantine._endpoint_context",
        lambda settings: {
            "paper_endpoint_confirmed": True,
            "alpaca_api_key_configured": True,
            "alpaca_api_secret_configured": True,
        },
    )
    client = FakeClient(
        [
            {
                "id": "new-order",
                "status": "new",
                "created_at": "2026-08-24T22:00:00+00:00",
                "symbol": "NVDA",
                "side": "sell",
                "type": "market",
                "time_in_force": "day",
            },
            {
                "id": "old-order",
                "status": "new",
                "created_at": "2026-08-24T20:00:00+00:00",
                "symbol": "BNO",
            },
        ]
    )
    result = quarantine_pending_paper_orders(
        _settings(tmp_path),
        incident_id="incident-1",
        incident_started_at="2026-08-24T21:00:00+00:00",
        client=client,
    )
    assert result["status"] == "dry_run_ready"
    assert result["selected_open_order_count"] == 1
    assert client.cancelled == []
    assert "new-order" not in str(result)


def test_quarantine_requires_paper_boundary(tmp_path: Path) -> None:
    settings = replace(_settings(tmp_path), live_capital_enabled=True)
    with pytest.raises(PermissionError, match="paper_order_quarantine_boundary_failed"):
        quarantine_pending_paper_orders(
            settings,
            incident_id="incident-1",
            incident_started_at="2026-08-24T21:00:00+00:00",
            client=FakeClient([]),
        )


def test_quarantine_cancels_every_selected_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "orchestrator.qadam_pending_order_quarantine._endpoint_context",
        lambda settings: {
            "paper_endpoint_confirmed": True,
            "alpaca_api_key_configured": True,
            "alpaca_api_secret_configured": True,
        },
    )
    client = FakeClient(
        [
            {
                "id": f"order-{index}",
                "status": "accepted",
                "created_at": "2026-08-24T23:00:00+00:00",
                "symbol": "NVDA" if index < 2 else "ITA",
                "side": "sell",
                "type": "market",
                "time_in_force": "day",
            }
            for index in range(3)
        ]
    )
    result = quarantine_pending_paper_orders(
        _settings(tmp_path),
        incident_id="incident-1",
        incident_started_at="2026-08-24T21:00:00+00:00",
        execute=True,
        client=client,
    )
    assert result["status"] == "cancel_requests_submitted"
    assert result["cancel_requested_count"] == 3
    assert set(client.cancelled) == {"order-0", "order-1", "order-2"}
