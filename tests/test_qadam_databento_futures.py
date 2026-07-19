from __future__ import annotations

from orchestrator.qadam_databento_futures import (
    DatabentoFuturesRequest,
    _provider_checksum,
    _select_front_contract_rows,
    build_quote,
    validate_quote_authorization,
)


class FakeMetadata:
    def __init__(self, costs: dict[str, float]) -> None:
        self.costs = costs

    def get_cost(self, **kwargs: object) -> float:
        return self.costs[str(kwargs["schema"])]


class FakeClient:
    def __init__(self, costs: dict[str, float]) -> None:
        self.metadata = FakeMetadata(costs)


def test_databento_quote_combines_bars_and_definitions() -> None:
    request = DatabentoFuturesRequest(budget_usd=150, monthly_limit_usd=150)
    quote = build_quote(FakeClient({"ohlcv-1d": 4.25, "definition": 1.75}), request)
    assert quote["total_usd"] == 6.0
    assert quote["within_budget"] is True
    assert validate_quote_authorization(quote, request) == []


def test_databento_quote_fails_closed_over_budget() -> None:
    request = DatabentoFuturesRequest(budget_usd=150, monthly_limit_usd=150)
    quote = build_quote(FakeClient({"ohlcv-1d": 149, "definition": 2}), request)
    assert "databento_quote_exceeds_approved_budget" in validate_quote_authorization(
        quote, request
    )


def test_monthly_limit_cannot_exceed_operator_budget() -> None:
    request = DatabentoFuturesRequest(budget_usd=125, monthly_limit_usd=150)
    quote = build_quote(FakeClient({"ohlcv-1d": 1, "definition": 1}), request)
    assert "databento_monthly_limit_exceeds_approved_budget" in validate_quote_authorization(
        quote, request
    )


def test_provider_checksum_strips_algorithm_prefix() -> None:
    assert _provider_checksum("sha256:ABC123") == "abc123"
    assert _provider_checksum("ABC123") == "abc123"


def test_front_contract_selection_uses_liquid_outrights_only() -> None:
    selected = _select_front_contract_rows(
        [
            {
                "observed_at": "2025-01-02T00:00:00+00:00",
                "contract_symbol": "CLG5",
                "volume": 100,
            },
            {
                "observed_at": "2025-01-02T00:00:00+00:00",
                "contract_symbol": "CLH5",
                "volume": 200,
            },
            {
                "observed_at": "2025-01-02T00:00:00+00:00",
                "contract_symbol": "CLG5-CLH5",
                "volume": 9999,
            },
            {
                "observed_at": "2025-01-02T00:00:00+00:00",
                "contract_symbol": "SIH5",
                "volume": 50,
            },
        ]
    )
    assert [row["contract_symbol"] for row in selected] == ["CLH5", "SIH5"]
