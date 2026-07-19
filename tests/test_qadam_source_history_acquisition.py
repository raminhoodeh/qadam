from __future__ import annotations

import inspect
import json
import os

from orchestrator import qadam_source_history_acquisition as acquisition


def test_epoch_millis_is_normalized_to_utc() -> None:
    assert acquisition._epoch_millis_iso(0) == "1970-01-01T00:00:00+00:00"  # noqa: SLF001


def test_all_network_fetchers_accept_runner_dispatch_keywords() -> None:
    for fetcher in acquisition.NETWORK_FETCHERS.values():
        parameters = inspect.signature(fetcher).parameters
        assert "settings" in parameters
        assert "timeout_seconds" in parameters


def test_retryable_failures_remain_resume_eligible() -> None:
    assert "pending_source_adapter" in acquisition.RETRYABLE_JOB_STATES
    assert "retryable_failure" in acquisition.RETRYABLE_JOB_STATES
    assert "complete" not in acquisition.RETRYABLE_JOB_STATES


def test_interrupted_job_is_recovered_without_overwriting_live_runner() -> None:
    jobs = [
        {"job_id": "stale", "status": "running", "runner_pid": None},
        {"job_id": "live", "status": "running", "runner_pid": os.getpid()},
    ]
    assert acquisition._recover_interrupted_jobs(jobs) == 1  # noqa: SLF001
    assert jobs[0]["status"] == "retryable_failure"
    assert jobs[0]["failure_category"] == "interrupted_previous_run"
    assert jobs[1]["status"] == "running"


def test_prediction_title_filter_rejects_false_oil_substrings() -> None:
    assert acquisition._prediction_title_is_relevant(  # noqa: SLF001
        "Will crude oil settle above 100?"
    )
    assert not acquisition._prediction_title_is_relevant(  # noqa: SLF001
        "Will Pierre Poilievre become prime minister?"
    )


def test_json_string_list_parses_provider_encoded_arrays() -> None:
    assert acquisition._json_string_list('["Yes", "No"]') == ["Yes", "No"]  # noqa: SLF001
    assert acquisition._json_string_list("not-json") == []  # noqa: SLF001


def test_sec_acceptance_timestamp_supports_current_iso_format() -> None:
    available_at, precision = acquisition._sec_available_at(  # noqa: SLF001
        "2026-07-15T21:03:12.000Z",
        filing_date="2026-07-15",
    )
    assert available_at == "2026-07-15T21:03:12+00:00"
    assert precision == "acceptance_datetime"


def test_sec_acceptance_timestamp_falls_back_conservatively() -> None:
    available_at, precision = acquisition._sec_available_at(  # noqa: SLF001
        "",
        filing_date="2018-02-03",
    )
    assert available_at == "2018-02-03T23:59:59+00:00"
    assert precision == "conservative_filing_day_end"


def test_alpaca_link_reuses_real_price_partition(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(acquisition, "ROOT", tmp_path)
    monkeypatch.setattr(acquisition, "RESEARCH_ROOT", tmp_path / "data" / "research")
    path = (
        acquisition.RESEARCH_ROOT
        / "prices"
        / "symbol=SPY"
        / "interval=1d"
        / "year=2025"
        / "bars.jsonl"
    )
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "observed_at": "2025-01-02T05:00:00+00:00",
                "available_at": "2025-01-03T05:00:00+00:00",
                "close": 100.0,
                "volume": 1000,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    raw, records, metadata = acquisition._alpaca_link_partition(  # noqa: SLF001
        2025,
        price_manifest={
            "jobs": [
                {
                    "provider": "alpaca_market_data_v2",
                    "instrument": "SPY",
                    "date_partition": "2025",
                    "status": "complete",
                }
            ]
        },
    )
    assert json.loads(raw)["references"][0]["symbol"] == "SPY"
    assert records[0]["point_in_time_safe"] is True
    assert records[0]["raw_ref"].endswith("bars.jsonl")
    assert metadata["credentials_recorded"] is False


def test_source_partition_separates_current_revision_rows(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(acquisition, "ROOT", tmp_path)
    monkeypatch.setattr(acquisition, "RESEARCH_ROOT", tmp_path / "data" / "research")
    metadata = acquisition._write_partition(  # noqa: SLF001
        {
            "job_id": "source:bls:2025",
            "source": "bls",
            "provider": "bls",
            "date_partition": "2025",
        },
        b"{}",
        [
            {
                "event_timestamp": "2025-01-01T00:00:00+00:00",
                "source_available_at": "2026-07-18T00:00:00+00:00",
                "point_in_time_safe": False,
            }
        ],
        {"credentials_recorded": False},
    )
    assert metadata["normalized_row_count"] == 1
    assert metadata["point_in_time_safe_row_count"] == 0
    assert metadata["current_revision_only_row_count"] == 1


def test_ucdp_record_is_current_revision_only() -> None:
    record = acquisition._ucdp_record(  # noqa: SLF001
        {
            "id": "42",
            "relid": "TEST-42",
            "year": "2025",
            "date_start": "2025-02-03 00:00:00.000",
            "date_end": "2025-02-04 00:00:00.000",
            "type_of_violence": "1",
            "latitude": "24.5",
            "longitude": "54.3",
            "best": "3",
        },
        dataset_version="26.1",
        dataset_state="ged_current_release_snapshot",
        fetched_at="2026-07-18T00:00:00+00:00",
    )
    assert record["event_timestamp"] == "2025-02-03T00:00:00+00:00"
    assert record["type_of_violence"] == 1
    assert record["best_death_estimate"] == 3
    assert record["point_in_time_safe"] is False
    assert record["source_available_at"] == "2026-07-18T00:00:00+00:00"


def test_ucdp_partition_uses_shared_archive_reference(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(acquisition, "ROOT", tmp_path)
    monkeypatch.setattr(acquisition, "RESEARCH_ROOT", tmp_path / "data" / "research")
    ged_path = tmp_path / "ged.zip"
    candidate_path = tmp_path / "candidate.csv"

    header = "id,relid,year,date_start,date_end,type_of_violence,best\n"
    rows = (
        header
        + "1,A,2016,2016-01-02 00:00:00.000,2016-01-02 00:00:00.000,1,2\n"
    )
    with acquisition.zipfile.ZipFile(ged_path, "w") as archive:
        archive.writestr("GEDEvent_v26_1.csv", rows)
    candidate_path.write_text(header, encoding="utf-8")
    monkeypatch.setattr(
        acquisition,
        "_ucdp_shared_archives",
        lambda **_kwargs: (
            ged_path,
            candidate_path,
            {
                "ged_sha256": "ged",
                "candidate_sha256": "candidate",
                "provider_call_count": 0,
            },
        ),
    )
    raw, records, metadata = acquisition._ucdp_partition(  # noqa: SLF001
        2016,
        settings=object(),
        timeout_seconds=5,
    )
    assert len(records) == 1
    assert records[0]["provider_event_id"] == "1"
    assert json.loads(raw)["ged_archive_sha256"] == "ged"
    assert metadata["shared_immutable_archive"] is True
    assert metadata["point_in_time_state"] == (
        "current_revision_only_not_backtest_eligible"
    )


def test_deferred_source_classification_is_explicit_and_non_evidentiary() -> None:
    jobs = [
        {
            "job_id": "source:gdelt:2025",
            "source": "gdelt",
            "status": "pending_source_adapter",
        },
        {
            "job_id": "source:nasa_firms:2025",
            "source": "nasa_firms",
            "status": "pending_source_adapter",
        },
    ]
    count, actions = acquisition._classify_deferred_source_jobs(  # noqa: SLF001
        jobs,
        source_keys=("gdelt",),
    )
    assert count == 1
    assert len(actions) == 1
    assert jobs[0]["status"] == "unavailable_classified"
    assert jobs[0]["operator_action_required"] is True
    assert jobs[0]["evidence_credit_allowed"] is False
    assert jobs[0]["proxy_credit_allowed"] is False
    assert jobs[1]["status"] == "pending_source_adapter"
