from __future__ import annotations

import json
from datetime import datetime, timezone

from orchestrator import qadam_point_in_time_evidence as evidence


def _write_json(path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def test_provider_alignment_is_point_in_time_and_label_free(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(evidence, "ROOT", tmp_path)
    source_path = tmp_path / "data/research/normalized/source=stock_act/date=2025/records.jsonl"
    _write_json(
        source_path,
        {
            "source_key": "stock_act",
            "record_type": "house_financial_disclosure_index",
            "event_timestamp": "2025-01-01T00:00:00+00:00",
            "source_available_at": "2025-01-01T23:59:59+00:00",
            "point_in_time_safe": True,
        },
    )
    price_path = tmp_path / "data/research/prices/symbol=SPY/interval=1d/year=2025/bars.jsonl"
    price_path.parent.mkdir(parents=True, exist_ok=True)
    price_path.write_text(
        "\n".join(
            json.dumps(
                {
                    "symbol": "SPY",
                    "observed_at": observed,
                    "available_at": "2026-01-01T00:00:00+00:00",
                    "close": close,
                    "volume": 100,
                }
            )
            for observed, close in (
                ("2025-01-02T04:00:00+00:00", 100),
                ("2025-01-03T04:00:00+00:00", 101),
                ("2025-01-06T04:00:00+00:00", 102),
            )
        )
        + "\n",
        encoding="utf-8",
    )
    runtime = tmp_path / "data/runtime"
    runtime.mkdir(parents=True)
    (runtime / evidence.SOURCE_BACKFILL_MANIFEST_ARTIFACT).write_text(
        json.dumps(
            {
                "jobs": [
                    {
                        "source": "stock_act",
                        "status": "complete",
                        "row_count": 1,
                        "point_in_time_safe_row_count": 1,
                        "normalized_path": str(source_path.relative_to(tmp_path)),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (runtime / evidence.PRICE_BACKFILL_MANIFEST_ARTIFACT).write_text(
        json.dumps(
            {
                "jobs": [
                    {
                        "instrument": "SPY",
                        "provider": "alpaca_market_data_v2",
                        "date_partition": "2025",
                        "status": "complete",
                        "normalized_path": str(price_path.relative_to(tmp_path)),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (runtime / evidence.BACKFILL_COVERAGE_ARTIFACT).write_text(
        json.dumps(
            {
                "provider_history_acquisition_contract_complete": True,
                "provider_history_certified_complete": False,
            }
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "data/research/aligned/or4/provider_alignment.jsonl"
    summary = evidence.build_provider_lake_alignment(
        runtime,
        [
            {
                "relationship_id": "relationship:test",
                "source_key": "stock_act",
                "instrument": "SPY",
                "mapping_class": "broad_discovery_mapping",
                "historical_research_eligible": True,
                "negative_control": False,
            }
        ],
        output_path=output_path,
    )
    rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert summary["status"] == "provider_alignment_ready"
    assert summary["alignment_record_count"] == 1
    assert summary["eligible_forward_window_count"] == 1
    assert summary["future_label_value_count"] == 0
    assert rows[0]["decision_at"] == "2025-01-03T04:00:00+00:00"
    assert rows[0]["future_label_values_included"] is False
    assert "forward_return" not in output_path.read_text(encoding="utf-8")


def test_current_revision_source_rows_are_not_aligned(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(evidence, "ROOT", tmp_path)
    runtime = tmp_path / "data/runtime"
    runtime.mkdir(parents=True)
    (runtime / evidence.SOURCE_BACKFILL_MANIFEST_ARTIFACT).write_text(
        json.dumps(
            {
                "jobs": [
                    {
                        "source": "ucdp",
                        "status": "complete",
                        "row_count": 100,
                        "point_in_time_safe_row_count": 0,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (runtime / evidence.PRICE_BACKFILL_MANIFEST_ARTIFACT).write_text(
        json.dumps({"jobs": []}), encoding="utf-8"
    )
    (runtime / evidence.BACKFILL_COVERAGE_ARTIFACT).write_text(
        json.dumps({"provider_history_acquisition_contract_complete": True}),
        encoding="utf-8",
    )
    summary = evidence.build_provider_lake_alignment(
        runtime,
        [],
        output_path=tmp_path / "data/research/aligned/or4/provider_alignment.jsonl",
    )
    assert summary["alignment_record_count"] == 0
    assert summary["source_counters"]["current_revision_source_rows_excluded"] == 100


def test_stale_source_revision_is_not_treated_as_fresh_signal(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(evidence, "ROOT", tmp_path)
    source_path = tmp_path / "data/research/normalized/source=usgs/date=2016/records.jsonl"
    _write_json(
        source_path,
        {
            "source_key": "usgs",
            "event_timestamp": "2016-01-01T00:00:00+00:00",
            "source_available_at": "2022-05-03T00:00:00+00:00",
            "point_in_time_safe": True,
        },
    )
    features, counters = evidence._build_source_day_features(  # noqa: SLF001
        {
            "jobs": [
                {
                    "source": "usgs",
                    "status": "complete",
                    "row_count": 1,
                    "point_in_time_safe_row_count": 1,
                    "normalized_path": str(source_path.relative_to(tmp_path)),
                }
            ]
        }
    )
    assert features == []
    assert counters["stale_or_invalid_source_revision_rows_excluded"] == 1


def test_market_alignment_rejects_pre_inception_gap() -> None:
    source_at = datetime(2016, 1, 1, tzinfo=timezone.utc)
    assert evidence._market_alignment_is_timely(  # noqa: SLF001
        source_at,
        datetime(2016, 1, 5, tzinfo=timezone.utc),
    )
    assert not evidence._market_alignment_is_timely(  # noqa: SLF001
        source_at,
        datetime(2020, 1, 1, tzinfo=timezone.utc),
    )
