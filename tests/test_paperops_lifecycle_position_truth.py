from __future__ import annotations

from orchestrator.paperops_paper_lifecycle_poller import _unique_open_position_count


def test_current_position_count_deduplicates_historical_fills() -> None:
    lifecycle_records = [
        {
            "lifecycle_state": "open_position",
            "broker_order_status": "filled",
            "symbol": "BNO",
        },
        {
            "lifecycle_state": "open_position",
            "broker_order_status": "filled",
            "symbol": "bno",
        },
        {
            "lifecycle_state": "open_position",
            "broker_order_status": "filled",
            "symbol": "ITA",
        },
        {
            "lifecycle_state": "closed_trade",
            "broker_order_status": "filled",
            "symbol": "XLE",
        },
    ]

    assert _unique_open_position_count(lifecycle_records) == 2
