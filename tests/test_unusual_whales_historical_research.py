from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone
import json
from pathlib import Path
from typing import Any

import pytest

from orchestrator.config import Settings
from orchestrator.qadam_statistical_backtest import (
    REQUIRED_UNUSUAL_WHALES_COMPARISONS,
    build_statistical_backtest_state,
    validate_statistical_backtest_state,
)
from orchestrator.unusual_whales_adapter import (
    CLIENT_API_ID,
    DEFAULT_ACCESS_EXPIRES_ON,
    UnusualWhalesResearchAdapter,
    UnusualWhalesResearchConfig,
    build_feature_manifest,
    build_headers,
    build_point_in_time_feature_snapshot,
    build_request_url,
    normalize_payload,
    select_point_in_time_features,
    validate_unusual_whales_contract,
)
from scripts.run_unusual_whales_historical_capture import build_capture_tasks


class MemoryStore:
    def __init__(self) -> None:
        self.reservations: list[dict[str, Any]] = []
        self.writes: list[dict[str, Any]] = []
        self.captures: dict[str, dict[str, Any]] = {}

    def reserve_request(self, *, local_date: str, daily_budget: int) -> int:
        self.reservations.append({"local_date": local_date, "daily_budget": daily_budget})
        return len(self.reservations)

    def write_capture(self, **kwargs: Any) -> dict[str, Any]:
        self.writes.append(kwargs)
        records = kwargs["records"]
        metadata = {
            "capture_id": kwargs["capture_id"],
            "endpoint_key": kwargs["endpoint_key"],
            "normalized_record_count": len(records),
            "backtest_eligible_record_count": sum(
                record["backtest_feature_eligible"] is True for record in records
            ),
            "point_in_time_safe_record_count": sum(
                record["point_in_time_safe"] is True for record in records
            ),
            "coverage_start": min(record["event_at"] for record in records),
            "coverage_end": max(record["event_at"] for record in records),
            "feature_names": sorted(
                {name for record in records for name in record["features"]}
            ),
            "instruments": sorted({record["instrument"] for record in records}),
            "normalized_path": "data/research/unusual_whales/normalized/test.jsonl",
        }
        self.captures[kwargs["capture_id"]] = metadata
        return metadata

    def load_manifest(self) -> dict[str, Any]:
        return {"captures": self.captures}


def _config(**overrides: Any) -> UnusualWhalesResearchConfig:
    base = UnusualWhalesResearchConfig(
        enabled=True,
        access_expires_on=DEFAULT_ACCESS_EXPIRES_ON,
        timezone_name="Asia/Dubai",
        client_api_id=CLIENT_API_ID,
        daily_request_budget=100,
        run_request_budget=20,
        symbol_allowlist=("NVDA", "SPY"),
        provider_terms_reviewed=True,
        raw_retention_allowed=False,
    )
    return replace(base, **overrides)


def test_request_boundary_is_allowlisted_and_uses_required_headers() -> None:
    headers = build_headers("test-token")
    assert headers["Authorization"] == "Bearer test-token"
    assert headers["UW-CLIENT-API-ID"] == "100001"
    assert build_request_url(
        "darkpool_ticker",
        symbol="NVDA",
        params={"date": "2026-07-10", "limit": 500},
        symbol_allowlist=("NVDA",),
    ).startswith("https://api.unusualwhales.com/api/darkpool/NVDA?")
    with pytest.raises(ValueError, match="endpoint_not_allowlisted"):
        build_request_url("full_tape")
    with pytest.raises(ValueError, match="query_param_not_allowlisted"):
        build_request_url("market_tide", params={"unsafe": True})
    with pytest.raises(ValueError, match="symbol_not_allowlisted"):
        build_request_url(
            "darkpool_ticker",
            symbol="TSLA",
            symbol_allowlist=("NVDA",),
        )


def test_normalization_enforces_point_in_time_availability() -> None:
    records = normalize_payload(
        "options_volume",
        {
            "data": [
                {"date": "2026-07-10", "call_volume": 200, "put_volume": 100},
                {"date": "2026-07-12", "call_volume": 100, "put_volume": 200},
            ]
        },
        fetched_at="2026-07-14T12:00:00+00:00",
        symbol="NVDA",
        capture_id="capture-test",
    )
    assert records[0]["available_at"] == "2026-07-11T00:00:00+00:00"
    assert records[0]["features"]["put_call_volume_ratio"] == 0.5
    before_release = select_point_in_time_features(
        records,
        instrument="NVDA",
        scoring_as_of="2026-07-10T23:59:59+00:00",
    )
    assert before_release == []
    snapshot = build_point_in_time_feature_snapshot(
        records,
        instrument="NVDA",
        scoring_as_of="2026-07-12T12:00:00+00:00",
    )
    assert snapshot["record_count"] == 1
    assert snapshot["records"][0]["event_at"] == "2026-07-10"
    assert snapshot["future_feature_access_allowed"] is False


def test_expired_access_blocks_before_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UNUSUAL_WHALES_API_KEY", "test-token")
    transport_calls: list[str] = []

    def transport(url: str, _headers: dict[str, str], _timeout: float) -> tuple[int, bytes]:
        transport_calls.append(url)
        return 200, b'{"data": []}'

    adapter = UnusualWhalesResearchAdapter(
        config=_config(),
        store=MemoryStore(),
        transport=transport,
        now_provider=lambda: datetime(2026, 7, 22, tzinfo=timezone.utc),
    )
    result = adapter.capture(
        "market_tide",
        params={"date": "2026-07-10"},
        allow_network=True,
        provider_terms_reviewed=True,
    )
    assert result["status"] == "blocked"
    assert result["reason"] == "expired_archive_only"
    assert transport_calls == []


def test_capture_never_persists_token_or_unapproved_raw_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("UNUSUAL_WHALES_API_KEY", "test-token")
    memory_store = MemoryStore()
    seen_headers: dict[str, str] = {}

    def transport(_url: str, headers: dict[str, str], _timeout: float) -> tuple[int, bytes]:
        seen_headers.update(headers)
        return 200, json.dumps(
            {
                "data": [
                    {
                        "timestamp": "2026-07-10T14:30:00+00:00",
                        "net_call_premium": "100",
                        "net_put_premium": "-25",
                    }
                ]
            }
        ).encode()

    settings = replace(Settings.from_env(), runtime_dir=str(tmp_path))
    adapter = UnusualWhalesResearchAdapter(
        settings=settings,
        config=_config(raw_retention_allowed=False),
        store=memory_store,
        transport=transport,
        now_provider=lambda: datetime(2026, 7, 14, 12, tzinfo=timezone.utc),
    )
    result = adapter.capture(
        "market_tide",
        params={"date": "2026-07-10"},
        allow_network=True,
        provider_terms_reviewed=True,
        retain_raw=True,
    )
    assert result["status"] == "captured"
    assert seen_headers["Authorization"] == "Bearer test-token"
    assert seen_headers["UW-CLIENT-API-ID"] == "100001"
    assert memory_store.writes[0]["retain_raw"] is False
    serialized = json.dumps(memory_store.writes[0], default=str)
    assert "test-token" not in serialized
    assert "test-token" not in "".join(
        path.read_text(encoding="utf-8") for path in tmp_path.glob("*.json")
    )


def test_feature_manifest_requires_provider_ablations() -> None:
    manifest = build_feature_manifest({}, config=_config())
    status = {
        "adapter_implemented": True,
        "access_expires_on": "2026-07-21",
        "source_quorum_allowed": False,
        "execution_allowed": False,
        "proof_credit_allowed": False,
    }
    assert validate_unusual_whales_contract(status, manifest) == []
    assert set(REQUIRED_UNUSUAL_WHALES_COMPARISONS) == set(
        manifest["required_backtest_comparisons"]
    )


def test_capture_plan_runs_alongside_supported_historical_features() -> None:
    tasks = build_capture_tasks(
        endpoints=("market_tide", "flow_alerts", "darkpool_ticker", "options_volume"),
        symbols=("NVDA", "SPY"),
        start_date=date(2026, 7, 13),
        end_date=date(2026, 7, 13),
    )
    assert len(tasks) == 6
    assert {task["endpoint"] for task in tasks} == {
        "market_tide",
        "flow_alerts",
        "darkpool_ticker",
        "options_volume",
    }
    assert len({task["task_id"] for task in tasks}) == len(tasks)


def test_backtest_protocol_registers_unusual_whales_without_claiming_an_edge(
    tmp_path: Path,
) -> None:
    (tmp_path / "qadam_pattern_score_tape_manifest.json").write_text(
        json.dumps({"partitions": [], "applied_learning_version_ids": []}),
        encoding="utf-8",
    )
    (tmp_path / "qadam_label_coverage.json").write_text(
        json.dumps({"label_count": 0}),
        encoding="utf-8",
    )
    (tmp_path / "qadam_label_quality_audit.json").write_text(
        json.dumps({"status": "not_measurable"}),
        encoding="utf-8",
    )
    (tmp_path / "qadam_backfill_coverage.json").write_text(
        json.dumps({"provider_row_count": 0}),
        encoding="utf-8",
    )
    (tmp_path / "unusual_whales_backtest_feature_manifest.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-07-14T00:00:00+00:00",
                "backtest_feature_ready": True,
                "backtest_eligible_record_count": 12,
                "coverage_start": "2026-07-01T00:00:00+00:00",
                "coverage_end": "2026-07-13T20:00:00+00:00",
                "access_expires_on": "2026-07-21",
            }
        ),
        encoding="utf-8",
    )
    state = build_statistical_backtest_state(
        replace(Settings.from_env(), runtime_dir=str(tmp_path))
    )
    assert validate_statistical_backtest_state(state) == []
    assert state["manifest"]["status"] == "blocked_insufficient_score_label_pairs"
    assert state["summary"]["validated_edge_count"] == 0
    assert state["walk_forward"]["unusual_whales_feature_row_count"] == 12
    assert {item["variant_id"] for item in state["manifest"]["feature_set_variants"]} == set(
        REQUIRED_UNUSUAL_WHALES_COMPARISONS
    )
