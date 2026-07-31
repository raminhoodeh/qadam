from __future__ import annotations

from datetime import date, timedelta

import orchestrator.qadam_power_market_edge_engine as power_engine
from orchestrator.qadam_power_market_edge_engine import (
    CAISO_NODES,
    _aggregate_caiso_rows,
    acquire_historical_partitions,
    build_acquisition_manifest,
    build_power_market_backtest,
    build_strategy_and_current_context,
    validate_power_market_state,
)

NOW = "2026-07-31T12:00:00+00:00"


def _daily_rows(count: int = 180) -> list[dict]:
    start = date(2025, 1, 1)
    rows = []
    for index in range(count):
        day = start + timedelta(days=index)
        rows.append(
            {
                "operating_date": day.isoformat(),
                "decision_available_at": (
                    f"{(day - timedelta(days=1)).isoformat()}T23:59:00+00:00"
                ),
                "dam_system_max_lmp": 10.0 + index,
                "dam_cross_zone_spread_p95": 2.0 + index / 10.0,
                "net_load_peak_mw": 20_000.0 + index * 10.0,
                "maximum_hourly_ramp_mw": 500.0 + index,
                "renewable_to_peak_demand_ratio": max(0.05, 0.50 - index / 1000.0),
                "provider_backed": True,
                "point_in_time_safe": True,
            }
        )
    return rows


def _proxy_bars(count: int = 180) -> list[dict]:
    start = date(2025, 1, 1)
    rows = []
    for index in range(count):
        day = start + timedelta(days=index)
        close = 102.0 if index >= 80 else 99.0
        rows.append(
            {
                "symbol": "CEG",
                "date": day.isoformat(),
                "observed_at": f"{day.isoformat()}T20:00:00+00:00",
                "open": 100.0,
                "high": max(100.0, close),
                "low": min(100.0, close),
                "close": close,
                "volume": 2_000_000.0 + index,
                "provider": "Alpaca Market Data IEX",
                "provider_backed": True,
            }
        )
    return rows


def test_caiso_lmp_rows_are_collapsed_with_zone_spread_lineage() -> None:
    rows = []
    for node_index, node in enumerate(CAISO_NODES):
        for hour in ("2026-07-30T08:00:00-00:00", "2026-07-30T09:00:00-00:00"):
            rows.append(
                {
                    "OPR_DT": "2026-07-30",
                    "NODE": node,
                    "LMP_TYPE": "LMP",
                    "INTERVALSTARTTIME_GMT": hour,
                    "MW": str(30 + node_index * 10),
                }
            )
    output = _aggregate_caiso_rows("dam_lmp", rows)
    assert len(output) == 1
    assert output[0]["provider_backed"] is True
    assert output[0]["cross_zone_spread_mean"] == 20.0
    assert output[0]["source_row_count"] == 6


def test_manifest_interleaves_power_and_proxy_jobs_and_preserves_completion() -> None:
    manifest = build_acquisition_manifest(
        None,
        generated_at=NOW,
        start=date(2025, 1, 1),
        today=date(2026, 7, 31),
    )
    providers = [row["provider"] for row in manifest["jobs"][:10]]
    assert providers[:3] == ["caiso_oasis"] * 3
    assert providers[3:] == ["alpaca_iex"] * 7
    assert manifest["jobs"][0]["period"] == "2026-07"
    assert manifest["jobs"][3]["period"] == "2026"
    assert manifest["jobs"][3]["end_exclusive"] == "2026-08-01"
    first = dict(manifest["jobs"][0], status="complete", raw_sha256="abc")
    refreshed = build_acquisition_manifest(
        {"jobs": [first]},
        generated_at=NOW,
        start=date(2025, 1, 1),
        today=date(2026, 7, 31),
    )
    assert refreshed["jobs"][0]["status"] == "complete"
    assert refreshed["jobs"][0]["raw_sha256"] == "abc"


def test_pending_partition_advances_before_deferred_provider_retry(monkeypatch) -> None:
    retry = {
        "job_id": "retry",
        "provider": "caiso_oasis",
        "dataset": "dam_lmp",
        "period": "2026-06",
        "start": "2026-06-01",
        "end_exclusive": "2026-07-01",
        "status": "retryable_error",
        "attempt_count": 2,
        "next_retry_at": "2099-01-01T00:00:00+00:00",
    }
    pending = {
        "job_id": "pending",
        "provider": "caiso_oasis",
        "dataset": "dam_lmp",
        "period": "2026-05",
        "start": "2026-05-01",
        "end_exclusive": "2026-06-01",
        "status": "pending",
        "attempt_count": 0,
    }
    manifest = {
        "jobs": [retry, pending],
        "resumable": True,
        "idempotent": True,
        "provider_writes_allowed": False,
    }
    attempted: list[str] = []
    monkeypatch.setattr(power_engine, "secret_value", lambda *_args: "unused")
    monkeypatch.setattr(
        power_engine,
        "fetch_caiso_partition",
        lambda dataset, start, end: attempted.append(start.isoformat()) or object(),
    )
    monkeypatch.setattr(
        power_engine,
        "_write_caiso_job",
        lambda job, _result: {**job, "status": "complete"},
    )
    monkeypatch.setattr(power_engine.time, "sleep", lambda _seconds: None)

    updated = acquire_historical_partitions(
        manifest,
        max_partitions=1,
        allow_network=True,
        settings=object(),
    )

    assert attempted == ["2026-05-01"]
    assert updated["jobs"][0]["status"] == "retryable_error"
    assert updated["jobs"][1]["status"] == "complete"


def test_alpaca_null_bars_page_is_a_valid_empty_partition(monkeypatch) -> None:
    monkeypatch.setattr(
        power_engine,
        "_fetch_bytes",
        lambda *_args, **_kwargs: b'{"bars":null,"next_page_token":null}',
    )

    result = power_engine.fetch_alpaca_bars(
        "CEG",
        date(2020, 1, 1),
        date(2021, 1, 1),
        api_key="test-key",
        api_secret="test-secret",
    )

    assert result.rows == []
    assert result.metadata["row_count"] == 0


def test_provider_backed_backtest_can_admit_only_a_bounded_experimental_score() -> None:
    daily = _daily_rows()
    bars = _proxy_bars()
    backtest = build_power_market_backtest(daily, bars, generated_at=NOW)
    assert backtest["point_in_time_safe"] is True
    assert backtest["cost_adjusted"] is True
    assert backtest["hypothesis_count"] > 0
    assert backtest["provisional_positive_count"] > 0
    strategy, scores, context = build_strategy_and_current_context(
        daily,
        bars,
        [{"symbol": "CEG", "observed_at": NOW, "spread_bps": 5.0}],
        backtest,
        generated_at=NOW,
    )
    assert strategy["automatic_strategy_admission_enabled"] is True
    assert strategy["automatic_risk_envelope_expansion_enabled"] is False
    assert scores
    assert scores[0]["paper_order_allowed"] is False
    assert strategy["strategies"][0]["best_observed_rejected_result"][
        "not_a_validated_expectancy"
    ] is True
    assert context["recent_packets"][0]["paper_order_allowed"] is False


def test_validation_rejects_any_automatic_risk_expansion() -> None:
    manifest = build_acquisition_manifest(
        None,
        generated_at=NOW,
        start=date(2025, 1, 1),
        today=date(2026, 7, 31),
    )
    state = {
        "research_store_bytes": 0,
        "authority": manifest["authority"],
    }
    backtest = {
        "point_in_time_safe": True,
        "cost_adjusted": True,
        "authority": manifest["authority"],
    }
    strategy = {
        "automatic_risk_envelope_expansion_enabled": True,
        "live_capital_enabled": False,
        "authority": manifest["authority"],
    }
    context = {"authority": manifest["authority"]}
    errors = validate_power_market_state(
        state, manifest, backtest, strategy, [], context
    )
    assert "power_market_automatic_risk_expansion_enabled" in errors
