from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

import orchestrator.qadam_forward_labels as forward_labels
from orchestrator.qadam_forward_labels import (
    _assign_overlap_groups,
    _instrument_cost_record,
    _label_score,
    _write_partition,
)


UTC = timezone.utc


def _bar(day: int, close: float, *, symbol: str) -> dict[str, object]:
    available_at = datetime(2025, 1, day, tzinfo=UTC)
    return {
        "symbol": symbol,
        "observed_at": available_at - timedelta(days=1),
        "available_at": available_at,
        "open": close,
        "high": close * 1.01,
        "low": close * 0.99,
        "close": close,
        "volume": 1_000.0,
        "provider": "test_provider",
        "availability_policy": "test_point_in_time",
        "roll_event": False,
        "roll_gap_ratio": None,
        "corporate_action_policy": None,
    }


def _series(symbol: str, closes: list[float]) -> dict[str, object]:
    bars = [_bar(index, close, symbol=symbol) for index, close in enumerate(closes, 1)]
    return {
        "bars": bars,
        "available_times": [bar["available_at"] for bar in bars],
    }


def _score(*, instrument: str = "CL=F", horizon: str = "1d_forward") -> dict[str, object]:
    return {
        "score_id": f"score:{instrument}:{horizon}",
        "scoring_as_of": "2025-01-01T00:00:00+00:00",
        "instrument": instrument,
        "horizon_hypothesis": horizon,
        "direction_hypothesis": "upside_under_confirmed_repricing",
        "strategy_family_id": "test_strategy",
        "regime_state": "normal",
    }


def _cost(instrument: str, *, paper_route_available: bool = False) -> dict[str, object]:
    return _instrument_cost_record(
        {
            "symbol": instrument,
            "market_family": "test",
            "paper_route_available": paper_route_available,
        }
    )


def test_futures_label_preserves_research_return_and_fails_closed_without_proxy() -> None:
    score = _score()
    label, missing = _label_score(
        score,
        source_score_partition_id="partition:test",
        series_by_symbol={"CL=F": _series("CL=F", [100.0, 110.0])},
        cost_by_instrument={"CL=F": _cost("CL=F")},
        price_lake_sha256="prices:test",
        cost_model_hash="costs:test",
    )
    assert missing is None
    assert label is not None
    assert label["gross_return"] == 0.1
    assert label["execution_instrument"] == "USO"
    assert label["net_return"] is None
    assert label["net_return_state"] == "execution_proxy_history_missing_fail_closed"
    assert label["research_execution_basis_return"] is None
    assert label["candidate_creation_allowed"] is False
    assert label["order_creation_allowed"] is False


def test_futures_proxy_label_records_basis_risk_and_cost_adjusted_return() -> None:
    score = _score()
    label, missing = _label_score(
        score,
        source_score_partition_id="partition:test",
        series_by_symbol={
            "CL=F": _series("CL=F", [100.0, 110.0]),
            "USO": _series("USO", [50.0, 51.0]),
        },
        cost_by_instrument={"CL=F": _cost("CL=F")},
        price_lake_sha256="prices:test",
        cost_model_hash="costs:test",
    )
    assert missing is None
    assert label is not None
    assert label["execution_proxy_used"] is True
    assert label["execution_gross_return"] == 0.02
    assert label["research_execution_basis_return"] == -0.08
    assert label["net_return"] == 0.0192
    assert (
        label["net_return_state"]
        == "proxy_adjusted_directional_research_estimate"
    )


def test_unsupported_contract_cost_model_never_invents_net_return() -> None:
    instrument = "KALSHI:EVENTS"
    label, missing = _label_score(
        _score(instrument=instrument),
        source_score_partition_id="partition:test",
        series_by_symbol={instrument: _series(instrument, [0.5, 0.6])},
        cost_by_instrument={instrument: _cost(instrument)},
        price_lake_sha256="prices:test",
        cost_model_hash="costs:test",
    )
    assert missing is None
    assert label is not None
    assert label["gross_return"] == 0.2
    assert label["net_return"] is None
    assert label["net_return_state"] == "unsupported_cost_model_fail_closed"


def test_incomplete_forward_window_is_typed_instead_of_fabricated() -> None:
    label, missing = _label_score(
        _score(horizon="5d_forward"),
        source_score_partition_id="partition:test",
        series_by_symbol={"CL=F": _series("CL=F", [100.0, 101.0])},
        cost_by_instrument={"CL=F": _cost("CL=F")},
        price_lake_sha256="prices:test",
        cost_model_hash="costs:test",
    )
    assert label is None
    assert missing is not None
    assert missing["classified"] is True
    assert missing["reason"] == "forward_window_not_yet_complete"


def test_unresolved_direction_keeps_both_counterfactuals_without_inventing_pnl() -> None:
    score = _score(instrument="SPY")
    score["direction_hypothesis"] = "undetermined_before_evidence"
    label, missing = _label_score(
        score,
        source_score_partition_id="partition:test",
        series_by_symbol={"SPY": _series("SPY", [100.0, 102.0])},
        cost_by_instrument={"SPY": _cost("SPY")},
        price_lake_sha256="prices:test",
        cost_model_hash="costs:test",
    )
    assert missing is None
    assert label is not None
    assert label["gross_return"] == 0.02
    assert label["direction_adjusted_gross_return"] is None
    assert label["long_net_return"] == 0.019
    assert label["short_net_return"] == -0.021
    assert label["net_return"] is None
    assert label["net_return_state"] == "direction_unresolved_counterfactuals_only"


def test_overlap_groups_use_anchored_non_overlapping_effective_samples() -> None:
    labels: list[dict[str, object]] = []
    for day in range(1, 6):
        decision = datetime(2025, 1, day, tzinfo=UTC)
        labels.append(
            {
                "score_id": f"score:{day}",
                "instrument": "SPY",
                "horizon": "3d_forward",
                "decision_at": decision.isoformat(),
                "research_outcome_available_at": (
                    decision + timedelta(days=3)
                ).isoformat(),
                "outcome_available_at": (decision + timedelta(days=3)).isoformat(),
            }
        )
    _assign_overlap_groups(labels)
    independent = [row for row in labels if row["independent_sample"] is True]
    assert [row["score_id"] for row in independent] == ["score:1", "score:4"]
    assert len({row["overlap_group_id"] for row in labels}) == 2
    assert [row["overlap_group_size"] for row in labels] == [3, 3, 3, 2, 2]


def test_completed_label_partition_is_idempotent_and_immutable(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(forward_labels, "RESEARCH_LABEL_ROOT", tmp_path)
    path = tmp_path / "partition" / "labels.jsonl"
    row = {"label_id": "label:test", "score_id": "score:test"}
    first_hash, first_reused = _write_partition(path, [row])
    second_hash, second_reused = _write_partition(path, [row])
    assert first_hash == second_hash
    assert first_reused is False
    assert second_reused is True
    with pytest.raises(ValueError, match="immutable"):
        _write_partition(path, [{**row, "label_id": "label:changed"}])
