import asyncio
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import io
import json
import sqlite3
from urllib.error import HTTPError

import httpx
import pytest

from orchestrator.config import Settings
from orchestrator.research.operational_diagnostics import (
    CURRENT_MONITORS, RETIRED_MONITORS, canonical_supervision_active, collection_diagnostics,
)
from orchestrator.research.provider_access import provider_failure_details
from orchestrator import qadam_self_healing_supervisor as supervisor


NOW = datetime(2026, 10, 22, 3, 30, tzinfo=timezone.utc)


def write(path, payload):
    path.write_text(json.dumps(payload))


def canonical_runtime(path):
    with sqlite3.connect(path / "qadam-control-plane.sqlite3") as db:
        db.execute("CREATE TABLE execution_runtime_policy (policy_id TEXT)")


def coverage(path, sources, generated=NOW):
    write(path / "qadam_source_collection_coverage.json",
          {"generated_at": generated.isoformat(), "sources": sources})


def test_aliases_disabled_and_unselected_are_not_provider_failures(tmp_path):
    coverage(tmp_path, [{"source_key": str(i), "collection_status": status}
                       for i, status in enumerate(("derived_alias", "intentionally_disabled", "not_selected"))])
    result = collection_diagnostics(tmp_path, NOW)
    assert result["provider_outage_count"] == 0
    assert result["excluded_collector_count"] == 3
    assert result["catalogue_count"] == 3


@pytest.mark.parametrize("evidence,freshness", [
    ("provider_context_timestamp_unverified", "unknown"),
    ("operational_only", "unknown"), ("no_observations", "unknown"),
    ("provider_observations", "stale"),
])
def test_collection_success_cannot_become_fresh_trade_evidence(tmp_path, evidence, freshness):
    coverage(tmp_path, [{"source_key": "source", "collection_status": "collected",
                         "collection_evidence_state": evidence, "evidence_freshness": freshness}])
    result = collection_diagnostics(tmp_path, NOW)
    assert result["provider_outage_count"] == 0
    assert result["evidence_limitation_count"] == 1
    assert result["evidence_limitations"][0]["fresh_catalyst_credit_allowed"] is False


def test_external_access_remains_visible_without_claiming_repair(tmp_path):
    coverage(tmp_path, [{"source_key": "acled", "collection_status": "needs_configuration",
                         "access_repair_action": "provider_permission_required"}])
    result = collection_diagnostics(tmp_path, NOW)
    assert result["external_action_count"] == 1
    assert result["actionable_repair_count"] == 0
    assert result["records"][0]["required_action"] == "provider_permission_required"


@pytest.mark.parametrize("offset,actionable", [(600, False), (-600, False), (-1801, True), (None, True)])
def test_retry_deadline_is_bounded_and_missing_deadline_is_a_fault(tmp_path, offset, actionable):
    coverage(tmp_path, [{"source_key": "gdelt", "collection_status": "retry_scheduled",
                         "next_attempt_at": (NOW + timedelta(seconds=offset)).isoformat() if offset is not None else None}])
    result = collection_diagnostics(tmp_path, NOW)
    assert bool(result["actionable_repair_count"]) is actionable


@pytest.mark.parametrize("offset", [-7201, 1])
def test_old_or_future_coverage_cannot_be_reported_current(tmp_path, offset):
    coverage(tmp_path, [{"source_key": "a", "collection_status": "collected"}], NOW + timedelta(seconds=offset))
    assert not collection_diagnostics(tmp_path, NOW)["coverage_current"]


def test_missing_or_empty_coverage_is_not_healthy(tmp_path):
    assert not collection_diagnostics(tmp_path, NOW)["coverage_current"]


@pytest.mark.parametrize("sources", [["invalid"], [{}], [{"source_key": "same"}, {"source_key": "same"}]])
def test_malformed_catalogue_is_not_current_coverage(tmp_path, sources):
    coverage(tmp_path, sources)
    assert not collection_diagnostics(tmp_path, NOW)["coverage_current"]
    coverage(tmp_path, [])
    assert not collection_diagnostics(tmp_path, NOW)["coverage_current"]


def test_canonical_read_does_not_create_a_database_and_corruption_does_not_fall_back(tmp_path):
    assert not canonical_supervision_active(tmp_path)
    assert not list(tmp_path.iterdir())
    (tmp_path / "qadam-control-plane.sqlite3").write_bytes(b"invalid database")
    assert canonical_supervision_active(tmp_path)


def test_current_supervisor_never_runs_retired_refresh_builders(tmp_path, monkeypatch):
    canonical_runtime(tmp_path)
    settings = replace(Settings.from_env(), runtime_dir=str(tmp_path))
    monkeypatch.setattr(supervisor, "_now", lambda: NOW)
    monkeypatch.setattr(supervisor, "read_operating_health", lambda _: {"status": "healthy", "blockers": []})
    monkeypatch.setattr(supervisor, "SAFE_REFRESH_HANDLERS", [("legacy", lambda _: pytest.fail("retired writer invoked"))])
    monkeypatch.setattr(supervisor, "_refresh_cockpit_status", lambda _: pytest.fail("second publication owner"))
    for name, _, _ in CURRENT_MONITORS:
        write(tmp_path / name, {"generated_at": NOW.isoformat()})
    coverage(tmp_path, [{"source_key": "rss", "collection_status": "collected",
                         "collection_evidence_state": "provider_observations", "evidence_freshness": "fresh"}])
    write(tmp_path / supervisor.AKBER_INPUT_COMPLETENESS_ARTIFACT, {"akber_missing_context_count": 100})
    write(tmp_path / supervisor.GIT_DEPLOY_ARTIFACT, {"deployment_closure_passed": False})
    result, _, errors = supervisor.build_and_write_self_healing_state(settings, perform_refresh=True)
    assert errors == []
    assert result["diagnostic_basis"] == "canonical_runtime_and_collection_coverage"
    assert result["repair_queue"]["entries"] == []
    assert result["backfill_resume"]["resume_executed"] is False
    monitored = {row["artifact"].split("/")[-1] for row in result["refresh_retry_policy"]["artifact_records"]}
    assert not monitored.intersection(RETIRED_MONITORS)
    assert result["refresh_records"] == []


def test_current_execution_failure_is_never_hidden_by_retirement(tmp_path, monkeypatch):
    canonical_runtime(tmp_path)
    monkeypatch.setattr(supervisor, "read_operating_health", lambda _: {
        "status": "degraded", "blockers": ["position_protection_missing"]})
    requests = supervisor._build_repair_requests(tmp_path, NOW.isoformat(), [], {})
    assert any(row["defect_type"] == "canonical_execution_health" and row["severity"] == "critical" for row in requests)
    assert any(row["defect_type"] == "collection_coverage_unavailable" for row in requests)


@pytest.mark.parametrize("payload", [{}, {"generated_at": (NOW + timedelta(days=1)).isoformat()}])
def test_current_artifact_cannot_use_filesystem_mtime_or_future_clock_as_freshness(tmp_path, payload):
    canonical_runtime(tmp_path)
    write(tmp_path / "qadam_position_care_status.json", payload)
    record = supervisor._artifact_freshness(tmp_path, "qadam_position_care_status.json", NOW.isoformat())
    assert record["freshness_state"] == "stale"
    assert record["timestamp_verified"] is False


@pytest.mark.parametrize("message,reason", [
    ("Your prepayment credits are depleted.", "prepayment_credits_depleted"),
    ("Your project is suspended.", "provider_suspension_reported"),
    ("Your API key was reported as leaked.", "provider_credential_exposure_reported"),
])
def test_provider_diagnostics_retain_categories_not_response_secrets(message, reason):
    body = {"error": {"message": message + " secret-value-do-not-retain", "status": "PERMISSION_DENIED"}}
    error = HTTPError("https://example.invalid?key=secret-value-do-not-retain", 402, "denied", {},
                      io.BytesIO(json.dumps(body).encode()))
    result = provider_failure_details(error)
    assert result["provider_error_reason"] == reason
    assert "secret-value" not in json.dumps(result)


def test_non_json_provider_error_remains_bounded_and_sanitized():
    error = HTTPError("https://example.invalid", 403, "denied", {}, io.BytesIO(b"<html>private text</html>"))
    result = provider_failure_details(error)
    assert result["provider_error_reason"] == "provider_account_or_request_error"
    assert "private text" not in json.dumps(result)


def test_fred_html_maintenance_is_not_an_observation_or_credential_claim(monkeypatch):
    from orchestrator.adapters import FREDAdapter
    adapter = object.__new__(FREDAdapter)
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(
            200, text="<html><title>Site Maintenance | St. Louis Fed</title></html>"))) as client:
            with pytest.raises(ValueError, match="fred_provider_maintenance"):
                await adapter._fetch_series_via_api(client, series_id="DGS10", api_key="test", observation_start="2026-10-01", limit=3)
            with pytest.raises(ValueError, match="fred_provider_maintenance"):
                await adapter._fetch_series_via_csv(client, series_id="DGS10", observation_start="2026-10-01", limit=3)
    asyncio.run(run())


def test_fred_non_csv_html_cannot_be_a_successful_empty_result():
    from orchestrator.adapters import FREDAdapter
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(200, text="<html>metadata</html>"))) as client:
            with pytest.raises(ValueError, match="fred_response_contract_invalid"):
                await object.__new__(FREDAdapter)._fetch_series_via_csv(client, series_id="DGS10", observation_start="2026-10-01", limit=3)
    asyncio.run(run())


def test_maintenance_retries_but_unknown_response_contract_requires_adapter_review():
    from orchestrator.research.source_collection import retry_class
    assert retry_class({"degraded_reason": "fred_provider_maintenance"}) == "transient_or_unclassified"
    assert retry_class({"degraded_reason": "fred_response_contract_invalid"}) == "provider_contract"


def test_health_message_explains_source_limits_without_claiming_all_feeds_healthy():
    from orchestrator.qadam_hedge_fund_team_health import _health_message
    message = _health_message({}, {"source_collection": {
        "diagnostic_basis": "canonical_runtime_and_collection_coverage", "coverage_current": True,
        "collection_state_counts": {"collected": 22}, "external_action_count": 7,
        "scheduled_retry_count": 3, "evidence_limitation_count": 16}})
    assert "22 collected" in message
    assert "7 need provider/operator access" in message
    assert "16 collected feeds have evidence limitations" in message
