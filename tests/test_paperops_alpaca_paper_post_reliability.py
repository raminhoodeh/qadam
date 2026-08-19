from __future__ import annotations

import sys
from types import SimpleNamespace

from orchestrator.config import Settings
from orchestrator.paperops_alpaca_paper_post import _post_to_alpaca_paper


class _Response:
    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload


class _Client:
    post_count = 0
    get_count = 0

    def __init__(self, **_kwargs) -> None:
        pass

    def __enter__(self) -> "_Client":
        return self

    def __exit__(self, *_args) -> None:
        return None

    def post(self, *_args, **_kwargs) -> _Response:
        type(self).post_count += 1
        return _Response(422, {"message": "client_order_id must be unique"})

    def get(self, *_args, **_kwargs) -> _Response:
        type(self).get_count += 1
        return _Response(
            200,
            {
                "id": "broker-order-1",
                "client_order_id": "paper-client-1",
                "status": "accepted",
            },
        )


def test_duplicate_broker_post_recovers_by_client_order_id(monkeypatch) -> None:
    _Client.post_count = 0
    _Client.get_count = 0
    monkeypatch.setitem(sys.modules, "httpx", SimpleNamespace(Client=_Client))
    monkeypatch.setattr(
        "orchestrator.paperops_alpaca_paper_post._orders_url",
        lambda _settings: "https://paper-api.alpaca.markets/v2/orders",
    )
    monkeypatch.setattr(
        "orchestrator.paperops_alpaca_paper_post._headers",
        lambda _settings: {"redacted": "true"},
    )

    result = _post_to_alpaca_paper(
        settings=Settings.from_env(),
        request_preview={
            "symbol": "XAR",
            "side": "buy",
            "type": "market",
            "time_in_force": "day",
            "qty": "2",
            "client_order_id": "paper-client-1",
        },
    )

    assert result["post_attempted"] is True
    assert result["post_succeeded"] is True
    assert result["receipt"]["recovered_after_idempotent_retry"] is True
    assert result["receipt"]["broker_order_identifier_exposed"] is False
    assert _Client.post_count == 1
    assert _Client.get_count == 1
