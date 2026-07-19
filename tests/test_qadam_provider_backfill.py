from __future__ import annotations

import json

from orchestrator import qadam_provider_backfill as backfill


class _Response:
    status = 200

    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._payload


def test_price_jobs_keep_provider_lanes_separate() -> None:
    jobs = backfill._price_jobs(  # noqa: SLF001 - contract-level unit test
        [
            {"symbol": "SPY"},
            {"symbol": "CL=F"},
            {"symbol": "KALSHI:EVENTS"},
        ],
        backfill.BackfillOptions(start_year=2025, end_year=2025),
    )
    by_symbol = {job["instrument"]: job for job in jobs}
    assert by_symbol["SPY"]["provider"] == "alpaca_market_data_v2"
    assert by_symbol["SPY"]["status"] == "pending"
    assert by_symbol["CL=F"]["provider"] == "databento_glbx_mdp3"
    assert by_symbol["CL=F"]["status"] == "pending_external_import"
    assert by_symbol["KALSHI:EVENTS"]["status"] == "unavailable_classified"


def test_source_jobs_turn_reviewed_states_into_typed_work_or_classification() -> None:
    jobs = backfill._source_jobs(  # noqa: SLF001 - contract-level unit test
        [
            {
                "source_key": "bls",
                "provider": "BLS API",
                "status": "pilot_ready",
                "granularity": "monthly",
                "rate_limits": "bounded",
                "operator_approval_complete": True,
            },
            {
                "source_key": "rss",
                "provider": "RSS",
                "status": "forward_only",
                "granularity": "event",
                "operator_approval_complete": True,
            },
            {
                "source_key": "bookmap",
                "provider": "Bookmap",
                "status": "excluded",
                "granularity": "event",
                "operator_approval_complete": True,
            },
        ],
        [],
        backfill.BackfillOptions(start_year=2025, end_year=2026),
    )
    bls = [job for job in jobs if job["source"] == "bls"]
    rss = next(job for job in jobs if job["source"] == "rss")
    bookmap = next(job for job in jobs if job["source"] == "bookmap")
    assert len(bls) == 2
    assert {job["status"] for job in bls} == {"pending_source_adapter"}
    assert rss["status"] == "unavailable_classified"
    assert rss["typed_unavailable_reason"] == "forward_only"
    assert bookmap["failure_category"] == "excluded_by_reviewed_provider_terms"


def test_alpaca_partition_is_normalized_without_recording_credentials(monkeypatch) -> None:
    payload = {
        "bars": [
            {
                "t": "2025-01-02T05:00:00Z",
                "o": 100.0,
                "h": 102.0,
                "l": 99.0,
                "c": 101.0,
                "v": 12345,
                "n": 456,
                "vw": 100.5,
            }
        ],
        "next_page_token": None,
        "symbol": "SPY",
    }
    monkeypatch.setattr(backfill, "urlopen", lambda *_args, **_kwargs: _Response(payload))
    raw, bars, metadata = backfill._fetch_alpaca_price_partition(  # noqa: SLF001
        {
            "instrument": "SPY",
            "date_partition": "2025",
            "provider": backfill.ALPACA_PRICE_PROVIDER,
        },
        api_key="key-id-not-recorded",
        api_secret="secret-not-recorded",
        timeout_seconds=5,
    )
    assert len(bars) == 1
    assert bars[0]["provider"] == "alpaca_market_data_v2"
    assert bars[0]["provider_adjustment"] == "all"
    assert bars[0]["close"] == 101.0
    assert metadata["credentials_recorded"] is False
    serialized = raw.decode("utf-8") + json.dumps(metadata)
    assert "key-id-not-recorded" not in serialized
    assert "secret-not-recorded" not in serialized


def test_alpaca_partition_writes_immutable_raw_and_normalized_checksums(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(backfill, "ROOT", tmp_path)
    monkeypatch.setattr(backfill, "RESEARCH_ROOT", tmp_path / "data" / "research")
    raw = b'{"pages":[{"bars":[]}]}'
    metadata = backfill._write_price_partition(  # noqa: SLF001
        {
            "job_id": "job:test",
            "instrument": "SPY",
            "date_partition": "2025",
            "provider": backfill.ALPACA_PRICE_PROVIDER,
        },
        raw,
        [
            {
                "symbol": "SPY",
                "observed_at": "2025-01-02T05:00:00Z",
                "close": 101.0,
            }
        ],
        {"credentials_recorded": False},
    )
    assert metadata["provider"] == "alpaca_market_data_v2"
    assert metadata["parser_version"] == "alpaca_stock_bars_daily.v1"
    assert metadata["normalized_row_count"] == 1
    assert (tmp_path / metadata["raw_payload_path"]).read_bytes() == raw
    assert (tmp_path / metadata["normalized_path"]).is_file()


def test_databento_normalization_updates_only_futures_jobs(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        backfill,
        "read_json",
        lambda _path: {
            "status": "complete",
            "partitions": [
                {
                    "symbol": "CL=F",
                    "date_partition": "2025",
                    "status": "complete",
                    "generated_at": "2026-07-18T00:00:00+00:00",
                    "normalized_row_count": 250,
                    "normalized_sha256": "abc123",
                    "normalized_path": "data/research/prices/cl/2025.jsonl",
                    "roll_metadata_path": "data/research/prices/cl/rolls.jsonl",
                    "roll_count": 12,
                    "continuous_contract_policy": "highest_same_session_volume_outright",
                    "back_adjusted": False,
                    "definition_job_verified": True,
                }
            ],
        },
    )
    manifest = {
        "jobs": [
            {
                "provider": backfill.DATABENTO_PRICE_PROVIDER,
                "instrument": "CL=F",
                "date_partition": "2025",
                "status": "pending_external_import",
            },
            {
                "provider": backfill.ALPACA_PRICE_PROVIDER,
                "instrument": "SPY",
                "date_partition": "2025",
                "status": "complete",
            },
        ]
    }
    backfill._apply_databento_import(manifest, runtime=tmp_path)  # noqa: SLF001
    assert manifest["jobs"][0]["status"] == "complete"
    assert manifest["jobs"][0]["row_count"] == 250
    assert manifest["jobs"][0]["definition_job_verified"] is True
    assert manifest["jobs"][1]["status"] == "complete"


def test_every_legacy_missing_window_gets_a_typed_reason(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        backfill,
        "read_jsonl",
        lambda _path: [
            {
                "missing_window_record_id": "missing:1",
                "source_key": "bls",
                "market_symbol": "SPY",
                "reason": "historical_price_window_missing",
            }
        ],
    )
    source_manifest = {
        "jobs": [
            {
                "job_id": "source:bls:2025",
                "source": "bls",
                "status": "pending_source_adapter",
            }
        ]
    }
    price_manifest = {
        "jobs": [
            {
                "job_id": "price:spy:2025",
                "instrument": "SPY",
                "status": "complete",
            }
        ]
    }
    records = backfill._build_unavailable_window_records(  # noqa: SLF001
        source_manifest,
        price_manifest,
        runtime=tmp_path,
    )
    assert len(records) == 1
    assert records[0]["typed_reason"] == "source_history_acquisition_pending"
    assert records[0]["interpolation_allowed"] is False


def test_classified_gaps_close_or3_without_claiming_empirical_completeness() -> None:
    coverage = backfill._coverage(  # noqa: SLF001
        {
            "source_count": 2,
            "jobs": [
                {
                    "status": "complete",
                    "row_count": 10,
                    "supplemental_feature_source": False,
                },
                {
                    "status": "unavailable_classified",
                    "row_count": 0,
                    "supplemental_feature_source": False,
                },
            ],
        },
        {"instrument_count": 0, "jobs": []},
        preflight={"status": "passed"},
    )
    assert coverage["status"] == "complete_with_classified_gaps"
    assert coverage["all_partitions_terminal"] is True
    assert coverage["all_partitions_acquired"] is False
    assert coverage["provider_history_acquisition_contract_complete"] is True
    assert coverage["provider_history_certified_complete"] is False
