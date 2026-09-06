import json
import sqlite3

import pytest

from orchestrator.learning.attribution import attributed_outcome, cohort_metrics, reconstruct_closed_orders
from orchestrator.learning.forward_evaluation import evaluate_forward_version


def order(identity, side, quantity, price, hour):
    return {"order_id": identity, "client_order_id": identity, "instrument": "SPY", "direction": side,
            "filled_quantity": quantity, "filled_avg_price": price, "filled_at": f"2026-09-01T{hour}:00:00Z",
            "paper_epoch_id": "epoch", "broker_account_fingerprint": "account", "account_currency": "USD"}


def test_multiple_entry_decisions_keep_exact_lots_and_prospective_modelled_costs():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    try:
        connection.executescript("""
            CREATE TABLE canonical_orders (decision_id TEXT, broker_order_id_hash TEXT, order_key TEXT, trading_lane TEXT);
            CREATE TABLE decision_transactions (decision_id TEXT, payload_json TEXT);
            CREATE TABLE operating_events (aggregate_type TEXT, aggregate_id TEXT, event_type TEXT, payload_json TEXT, created_at TEXT);
        """)
        for index in (1, 2):
            connection.execute("INSERT INTO canonical_orders VALUES (?,NULL,?,'discovery')", (f"d{index}", f"entry-{index}"))
            connection.execute("INSERT INTO decision_transactions VALUES (?,?)", (f"d{index}", json.dumps({
                "strategy_id": "power", "strategy_version": f"v{index}", "economic_signal_identity_id": f"event-{index}",
                "created_at": "2026-09-01T09:00:00Z"})))
            connection.execute("INSERT INTO operating_events VALUES ('strategy_version',?,'strategy_definition_registered',?,?)",
                               (f"v{index}", json.dumps({"evaluation_contract": {"version": "matched-forward.1", "cost_bps": 5.0}}),
                                "2026-09-01T08:00:00Z" if index == 1 else "2026-09-01T12:00:00Z"))
        history = reconstruct_closed_orders([order("entry-1", "buy", 2, 100, "10"),
                                              order("entry-2", "buy", 1, 110, "11"),
                                              order("exit", "sell", 3, 120, "13")])["exit"]
        result = attributed_outcome(connection, {"trade_id": "exit"}, history)
    finally:
        connection.close()
    assert result["realized_pnl"] == 50
    assert result["attribution_status"] == "exact_entry_allocations"
    lots = result["attributed_lots"]
    assert [row["decision_id"] for row in lots] == ["d1", "d2"]
    assert sum(row["realized_pnl"] for row in lots) == 50
    assert lots[0]["net_return"] == pytest.approx(0.1995)
    assert lots[0]["costs_measured"] is False
    assert lots[1]["net_return"] is None  # Registration after entry is not retrospective proof.
    assert cohort_metrics([result])["independent_outcome_count"] == 1
    assert cohort_metrics([result])["modelled_event_count"] == 1
    assert cohort_metrics([result])["measured_event_count"] == 0
    assert cohort_metrics([result])["benchmark_comparison_available"] is False


def test_forward_review_explains_exclusions_without_blocking_discovery():
    row = {"strategy_version_id": "v1", "outcome_id": "missing", "simulated_elapsed_time": False,
           "decision_at": "2026-09-01T00:00:00Z", "outcome_available_at": "2026-09-02T00:00:00Z",
           "evaluation_contract": {"version": "matched-forward.1"}, "economic_signal_identity_id": "event",
           "net_return": .02, "benchmark_net_return": None}
    result = evaluate_forward_version("v1", [row], as_of="2026-09-03T00:00:00Z")
    assert result["independent_outcome_count"] == 0
    assert "matched_benchmark_unavailable" in result["exclusions"][0]["reasons"]
    assert result["discovery_permission_requires_review_completion"] is False
