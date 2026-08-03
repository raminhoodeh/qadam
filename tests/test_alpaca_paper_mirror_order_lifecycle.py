from __future__ import annotations

from orchestrator.paper_account import AlpacaReadOnlyPaperMirror


def _mirror() -> AlpacaReadOnlyPaperMirror:
    return object.__new__(AlpacaReadOnlyPaperMirror)


def test_bracket_entry_and_protective_legs_are_flattened_once() -> None:
    parent = {
        "id": "parent",
        "symbol": "SLV",
        "status": "filled",
        "position_intent": "buy_to_open",
        "legs": [
            {
                "id": "target",
                "symbol": "SLV",
                "status": "new",
                "position_intent": "sell_to_close",
                "limit_price": "53.26",
            },
            {
                "id": "stop",
                "symbol": "SLV",
                "status": "held",
                "position_intent": "sell_to_close",
                "stop_price": "50.27",
            },
        ],
    }

    flattened = _mirror()._flatten_order_payloads([parent, parent])

    assert [row["id"] for row in flattened] == ["parent", "target", "stop"]
    assert flattened[0]["_qadam_protective_exit_leg"] is False
    assert all(row["_qadam_protective_exit_leg"] is True for row in flattened[1:])
    assert flattened[1]["_qadam_parent_order_id"] == "parent"
    assert flattened[2]["_qadam_parent_order_id"] == "parent"

    target = _mirror()._order_from_alpaca(flattened[1])
    stop = _mirror()._order_from_alpaca(flattened[2])
    assert target.limit_price == 53.26
    assert target.parent_order_id == "parent"
    assert stop.stop_price == 50.27
    assert stop.parent_order_id == "parent"


def test_filled_entry_is_not_a_closed_trade() -> None:
    mirror = _mirror()

    assert mirror._is_filled_closing_order(
        {"status": "filled", "position_intent": "buy_to_open"}
    ) is False
    assert mirror._is_filled_closing_order(
        {"status": "filled", "position_intent": "sell_to_open"}
    ) is False


def test_only_filled_closing_intent_is_a_closed_trade() -> None:
    mirror = _mirror()

    assert mirror._is_filled_closing_order(
        {"status": "new", "position_intent": "sell_to_close"}
    ) is False
    assert mirror._is_filled_closing_order(
        {"status": "filled", "position_intent": "sell_to_close"}
    ) is True
    assert mirror._is_filled_closing_order(
        {"status": "filled", "position_intent": "buy_to_close"}
    ) is True
