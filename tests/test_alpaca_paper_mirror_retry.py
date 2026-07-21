from __future__ import annotations

import httpx
import pytest

from orchestrator.paper_account import AlpacaReadOnlyPaperMirror


class _Response:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self.payload


def _mirror() -> AlpacaReadOnlyPaperMirror:
    mirror = object.__new__(AlpacaReadOnlyPaperMirror)
    mirror.base_url = "https://paper-api.alpaca.markets/v2"
    mirror.read_retry_count = 0
    mirror._headers = lambda: {}  # type: ignore[method-assign]
    return mirror


def test_readonly_mirror_retries_transient_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    outcomes: list[object] = [
        httpx.ReadTimeout(
            "temporary timeout",
            request=httpx.Request("GET", "https://paper-api.alpaca.markets/v2/account"),
        ),
        _Response({"equity": "100000"}),
    ]
    sleeps: list[float] = []

    class _Client:
        def __init__(self, **_: object) -> None:
            pass

        def __enter__(self) -> _Client:
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def get(self, *_: object, **__: object) -> object:
            outcome = outcomes.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

    monkeypatch.setattr(httpx, "Client", _Client)
    monkeypatch.setattr("orchestrator.paper_account.time.sleep", sleeps.append)
    monkeypatch.setenv("ALPACA_READ_RETRY_ATTEMPTS", "3")
    monkeypatch.setenv("ALPACA_READ_RETRY_DELAY_SECONDS", "0.25")

    mirror = _mirror()
    assert mirror._get("/account") == {"equity": "100000"}
    assert mirror.read_retry_count == 1
    assert sleeps == [0.25]


def test_readonly_mirror_does_not_retry_authentication_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = httpx.Request("GET", "https://paper-api.alpaca.markets/v2/account")
    response = httpx.Response(401, request=request)
    call_count = 0

    class _Client:
        def __init__(self, **_: object) -> None:
            pass

        def __enter__(self) -> _Client:
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def get(self, *_: object, **__: object) -> object:
            nonlocal call_count
            call_count += 1
            return response

    monkeypatch.setattr(httpx, "Client", _Client)
    monkeypatch.setattr(
        "orchestrator.paper_account.time.sleep",
        lambda _: pytest.fail("authentication failures must not be retried"),
    )

    mirror = _mirror()
    with pytest.raises(httpx.HTTPStatusError):
        mirror._get("/account")
    assert call_count == 1
    assert mirror.read_retry_count == 0
