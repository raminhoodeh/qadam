from orchestrator.cockpit_status import _dashboard_portfolio_public_status


def _capital(*, observed_at: str, value: float, positions: int = 1) -> dict:
    return {
        "observed_at": observed_at,
        "equity_gbp": value,
        "current_balance_gbp": value,
        "realized_pnl_gbp": 0.0,
        "unrealized_pnl_gbp": value - 100_000.0,
        "total_pnl_gbp": value - 100_000.0,
        "open_position_count": positions,
        "open_positions": [{} for _ in range(positions)],
        "equity_curve": [{"equity_gbp": value}],
    }


def _qsase(*, observed_at: str, value: float, positions: int = 1) -> dict:
    return {
        "dashboard_portfolio": {
            "observed_at": observed_at,
            "current_value_gbp": value,
            "open_position_count": positions,
            "broker_mirror_freshness": {"status": "fresh"},
        }
    }


def test_fresh_different_snapshot_generations_allow_market_value_movement() -> None:
    result = _dashboard_portfolio_public_status(
        _capital(observed_at="2026-08-03T15:40:38+00:00", value=100_010.0),
        "2026-08-03T15:40:39+00:00",
        _qsase(observed_at="2026-08-03T15:40:37+00:00", value=100_000.0),
    )

    assert result["status"] == "dashboard_portfolio_consistent"
    assert result["portfolio_consistency"]["qsase_value_delta"] == 10.0
    assert (
        result["portfolio_consistency"]["qsase_snapshot_generation_matches"]
        is False
    )


def test_same_snapshot_generation_still_rejects_value_mismatch() -> None:
    observed_at = "2026-08-03T15:40:37+00:00"
    result = _dashboard_portfolio_public_status(
        _capital(observed_at=observed_at, value=100_010.0),
        "2026-08-03T15:40:39+00:00",
        _qsase(observed_at=observed_at, value=100_000.0),
    )

    assert result["status"] == "dashboard_portfolio_mismatch"
    assert "qsase_dashboard_portfolio_value_mismatch" in (
        result["portfolio_consistency"]["errors"]
    )
