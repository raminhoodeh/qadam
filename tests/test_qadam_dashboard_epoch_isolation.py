from __future__ import annotations

from orchestrator.qadam_dashboard_epoch_isolation import _collect_identifiers


def test_placeholder_identifiers_do_not_count_as_execution_records() -> None:
    found: set[str] = set()

    _collect_identifiers(
        {
            "client_order_id": "not_allocated",
            "order_id": "order-real-1",
            "nested": {"trade_id": "missing"},
        },
        found,
    )

    assert found == {"order-real-1"}
