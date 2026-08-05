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
        "starting_balance_gbp": 100_000.0,
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


def test_market_closed_snapshot_is_not_reported_as_stale() -> None:
    capital = _capital(
        observed_at="2026-08-04T20:16:13+00:00",
        value=100_135.33,
    )
    capital.update(
        {
            "last_broker_sync_age_seconds": 45_000,
            "stale_after_seconds": 2_700,
            "mirror_freshness_status": "market_closed",
            "mirror_freshness_label": (
                "Market closed; displaying the latest completed broker snapshot"
            ),
            "market_clock": {
                "status": "closed",
                "is_open": False,
                "next_open": "2026-08-05T09:30:00-04:00",
            },
        }
    )

    result = _dashboard_portfolio_public_status(
        capital,
        "2026-08-05T08:46:53+00:00",
        _qsase(
            observed_at="2026-08-04T20:16:13+00:00",
            value=100_135.33,
        ),
    )

    assert result["broker_mirror_freshness"]["status"] == "market_closed"
    assert result["broker_mirror_freshness"]["market_is_open"] is False
    assert result["broker_mirror_freshness"]["next_open"] == "2026-08-05T09:30:00-04:00"


def test_epoch_scoped_curve_replaces_compact_recent_window() -> None:
    capital = _capital(
        observed_at="2026-08-04T20:16:13+00:00",
        value=100_135.33,
    )
    capital["equity_curve"] = [
        {"equity_gbp": 100_136.02 + (index / 100)} for index in range(19)
    ] + [{"equity_gbp": 100_135.33}]
    qsase = _qsase(
        observed_at="2026-08-04T20:16:13+00:00",
        value=100_135.33,
    )
    qsase["dashboard_portfolio"]["equity_curve"] = [
        {"portfolio_value": 100_000.0, "timestamp": "2026-08-02T09:45:15+00:00"}
    ] + [
        {"portfolio_value": 100_100.0 + index, "timestamp": f"2026-08-03T{index % 24:02d}:00:00+00:00"}
        for index in range(118)
    ] + [
        {"portfolio_value": 100_135.33, "timestamp": "2026-08-04T20:16:13+00:00"}
    ]

    result = _dashboard_portfolio_public_status(
        capital,
        "2026-08-05T08:46:53+00:00",
        qsase,
    )

    assert result["equity_curve_count"] == 120
    assert result["equity_curve"][0]["portfolio_value"] == 100_000.0
    assert result["latest_curve_point"]["portfolio_value"] == 100_135.33
