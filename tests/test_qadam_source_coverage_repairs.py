import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import httpx
import pytest

from orchestrator.phase1_live_adapters import PHASE1_LIVE_ADAPTERS, Phase1ReadOnlyAdapter
from orchestrator.research.source_payloads import provider_records
from orchestrator.research.gpsjam import fetch_payload


def adapter(key):
    value = object.__new__(Phase1ReadOnlyAdapter)
    value.config = PHASE1_LIVE_ADAPTERS[key]
    value.settings = None
    return value


def test_bls_extracts_series_observations_not_envelope():
    payload = {"status": "REQUEST_SUCCEEDED", "Results": {"series": [
        {"seriesID": "CPI", "data": [{"year": "2026", "period": "M08", "value": "120.4"}]}]}}
    event, = adapter("bls").normalize_payload(payload)
    assert event.raw_payload["value"] == 120.4
    assert event.raw_payload["record_id"] == "CPI:2026-M08"
    assert event.raw_payload["event_timestamp_fallback_to_fetch_time"]


def test_ecb_extracts_sdmx_dates_and_values_without_inventing_publication():
    payload = {"structure": {"dimensions": {"observation": [
        {"id": "TIME_PERIOD", "values": [{"id": "2026-09-22"}, {"id": "2026-09-23"}]}]}},
        "dataSets": [{"series": {"0:0": {"observations": {"0": [1.1], "1": [1.2]}}}}]}
    events = adapter("ecb").normalize_payload(payload)
    assert [e.raw_payload["value"] for e in events] == [1.2, 1.1]
    assert events[0].raw_payload["publication_timestamp_known"] is False


def test_sec_uses_filing_acceptance_not_download_time():
    payload = {"name": "Example", "cik": 1, "filings": {"recent": {
        "accessionNumber": ["001-26-1"], "form": ["10-Q"],
        "acceptanceDateTime": ["2026-09-23T15:01:00Z"], "filingDate": ["2026-09-23"]}}}
    event, = adapter("sec_edgar").normalize_payload(payload)
    assert event.ingested_at.startswith("2026-09-23T15:01:00")
    assert event.raw_payload["form"] == "10-Q"
    assert not event.raw_payload["event_timestamp_fallback_to_fetch_time"]


def test_ioda_preserves_actual_measurement_and_country():
    payload = {"data": [{"entity": {"code": "UA", "name": "Ukraine"}, "datasource": "bgp",
                         "time": 1750000000, "value": 10, "historyValue": 20, "level": "critical"}]}
    event, = adapter("internet_outage").normalize_payload(payload)
    assert event.raw_payload["value"] == 10
    assert event.raw_payload["baseline_value"] == 20
    assert event.raw_payload["country_code"] == "UA"


def test_arcgis_requires_features_and_uses_measurement_date():
    payload = {"features": [{"attributes": {"OBJECTID": 1, "STORMNAME": "Example",
                   "BASIN": "AL", "STORMNUM": 2, "DTG": 1750000000000, "INTENSITY": 65}}]}
    event, = adapter("arcgis_usace").normalize_payload(payload)
    assert event.raw_payload["measurements"]["INTENSITY"] == 65
    assert event.raw_payload["provider_timestamp_present"]
    with pytest.raises(ValueError):
        adapter("arcgis_usace").normalize_payload({"services": [{"name": "metadata"}]})


def test_hyperliquid_joins_metadata_with_prices():
    rows = provider_records("hyperliquid", [{"universe": [{"name": "BTC"}]},
                                            [{"markPx": "100", "funding": "0.01", "openInterest": "23"}]])
    assert rows[0]["value"] == 100
    assert rows[0]["funding_rate"] == 0.01
    with pytest.raises(ValueError):
        provider_records("hyperliquid", [{"universe": []}])


@pytest.mark.parametrize("key", ["bls", "ecb", "sec_edgar", "internet_outage", "arcgis_usace"])
def test_html_or_metadata_cannot_become_provider_observations(key):
    with pytest.raises((ValueError, KeyError)):
        adapter(key).normalize_payload({"status": "ok", "metadata": "service directory"})


def test_ucdp_and_patents_are_key_gated(monkeypatch):
    monkeypatch.setattr("orchestrator.phase1_live_adapters.secret_value", lambda name, settings: "test-value")
    assert not adapter("ucdp").config.public_live
    assert not adapter("patents").config.public_live
    assert adapter("ucdp")._request_headers()["x-ucdp-access-token"] == "test-value"
    assert adapter("patents")._request_headers()["X-Api-Key"] == "test-value"
    assert adapter("telegram")._live_url().endswith("/getMe")


def test_gpsjam_reads_manifest_latest_safe_day_and_bounded_scope():
    paths = []
    def respond(request):
        paths.append(request.url.path)
        if request.url.path.endswith("manifest.csv"):
            text = "date,suspect,source\n2026-09-22,false,merged\n2026-09-23,true,merged\n"
        else:
            text = "hex,count_good_aircraft,count_bad_aircraft\nabc,8,2\ndef,0,1\n"
        return httpx.Response(200, text=text)
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await fetch_payload(client, now=datetime(2026, 9, 24, tzinfo=timezone.utc))
    payload = asyncio.run(run())
    assert paths[-1] == "/data/merged/2026-09-22-h3_4.csv"
    assert payload["records"][0]["navigation_accuracy_degraded_pct"] == 10
    assert payload["records"][0]["publication_timestamp_known"] is False
    assert payload["coverage_cell_count"] == 2


def test_yahoo_handles_both_multiindex_orientations():
    import pandas as pd
    from orchestrator.yahoo_finance_adapter import YahooFinanceAdapter
    frame = pd.DataFrame([[10, 100, 20, 200], [11, 110, 21, 210]],
                         columns=pd.MultiIndex.from_tuples([
                             ("Close", "AAA"), ("Volume", "AAA"), ("Close", "BBB"), ("Volume", "BBB")]),
                         index=pd.date_range("2026-09-22", periods=2))
    for data in (frame, frame.swaplevel(axis=1)):
        rows = YahooFinanceAdapter._records_from_dataframe(data, ("AAA", "BBB"))
        assert [row["last_close"] for row in rows] == [11, 21]
        assert rows[0]["reference_period"].startswith("2026-09-23")


def test_fetch_clock_and_status_cannot_count_as_provider_freshness():
    from scripts.check_phase1_live_source_hardening import _latest_event_at
    event = {"ingested_at": "2026-09-24T00:00:00Z", "raw_payload": {}}
    for flag in ("sample", "status_only", "derived", "event_timestamp_fallback_to_fetch_time",
                 "summary_fallback_to_source_description"):
        assert _latest_event_at({"events": [{**event, "raw_payload": {flag: True}}]}) is None
    assert _latest_event_at({"events": [event]}) == event["ingested_at"]


def test_acled_401_refresh_is_bounded_and_403_does_not_refresh(monkeypatch):
    import orchestrator.phase1_live_adapters as module
    import orchestrator.acled_auth as auth
    original = httpx.AsyncClient
    monkeypatch.setattr(module, "_secret_groups_status", lambda *a: {"credential_configured": True})
    monkeypatch.setattr(module, "_credential_binding_state", lambda *a: None)
    monkeypatch.setattr(module, "secret_value", lambda *a: "test-value")
    refreshes = []
    monkeypatch.setattr(auth, "refresh_acled_token", lambda **kwargs:
                        refreshes.append(kwargs) or SimpleNamespace(secret_file_updated=True))
    for status, expected in ((401, 2), (403, 1)):
        calls = []
        def respond(request):
            calls.append(request)
            return httpx.Response(status, json={"message": "denied"})
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs:
                            original(transport=httpx.MockTransport(respond), **kwargs))
        value = adapter("acled")
        value.envelope_from_payload = lambda payload, **kwargs: kwargs
        result = asyncio.run(value.fetch_live())
        assert len(calls) == expected
        assert result["degraded"]
    assert len(refreshes) == 1


def test_polymarket_excludes_closed_markets_and_retains_prices():
    market = {"id": "1", "question": "Example future outcome?", "active": True, "closed": False,
              "outcomes": '["Yes", "No"]', "outcomePrices": '["0.6", "0.4"]',
              "updatedAt": "2026-09-24T12:00:00Z", "liquidityNum": 100, "volume24hr": 1000}
    events = adapter("polymarket").normalize_payload({"provider_payload": [
        {**market, "id": "old", "closed": True}, market]})
    assert len(events) == 1
    assert events[0].raw_payload["outcome_prices"] == {"Yes": 0.6, "No": 0.4}
    assert events[0].raw_payload["price_role"] == "indicative_market_context_not_executable_quote"


def test_odds_comparisons_are_not_claimed_as_equivalent_arbitrage():
    event, = adapter("kalshi").normalize_payload({"items": [{"match_id": 1,
        "kalshi": {"title": "Wins election", "yes_price": 0.7},
        "polymarket": {"title": "Wins by 5-10%", "yes_price": 0.1},
        "spread": {"yes_diff": 0.6}}]})
    assert "not_verified_equivalent" in event.raw_payload["price_role"]
    assert event.raw_payload["market_comparison"]["spread"]["yes_diff"] == 0.6


def test_ais_reads_provider_metadata_coordinates():
    from orchestrator.phase1_live_adapters import _ais_position_record
    row = _ais_position_record({"MessageType": "PositionReport", "MetaData": {
        "MMSI": 123, "Latitude": 25, "Longitude": 57},
        "Message": {"PositionReport": {"Valid": True, "Sog": 5}}})
    assert row["latitude"] == 25
    assert row["observed_at"] is None


def test_nasa_error_text_is_not_an_empty_successful_csv():
    from orchestrator.adapters import NASAFIRMSAdapter
    with pytest.raises(ValueError):
        NASAFIRMSAdapter._parse_csv("Invalid MAP_KEY")
    assert NASAFIRMSAdapter._parse_csv("latitude,longitude,acq_date,acq_time,confidence,frp\n") == []


def test_supplemental_worker_times_out_without_claiming_observations(monkeypatch):
    from orchestrator.research import supplemental_worker
    import subprocess
    def timeout(*args, **kwargs):
        assert kwargs["timeout"] == 45
        raise subprocess.TimeoutExpired(args[0], 45)
    monkeypatch.setattr(subprocess, "run", timeout)
    result = supplemental_worker.collect("tradingview_mcp")
    assert result["degraded"] and not result["events"]


def test_old_validation_receipts_migrate_without_claiming_new_measurements():
    from scripts.check_phase1_live_source_hardening import LiveSourceValidation
    from scripts.run_qadam_live_source_refresh import _validation_from_dict
    from dataclasses import fields, MISSING
    payload = {f.name: None for f in fields(LiveSourceValidation) if f.default is MISSING}
    restored = _validation_from_dict(payload)
    assert restored.observation_count == 0
    assert restored.collection_evidence_state == "unverified"


def test_goal_batch_reuses_its_validated_snapshot(tmp_path, monkeypatch):
    from orchestrator.research_goal import ResearchGoalStore
    store = ResearchGoalStore(path=tmp_path / "goals.jsonl")
    monkeypatch.setattr(store, "latest_by_goal_id", lambda: pytest.fail("unbounded history rescan"))
    monkeypatch.setattr(store, "add", lambda goal, **kwargs: goal)
    latest = {}
    first = store.add_from_observation(summary="Oil supply disruption", source_event_refs=("source:1",),
                                       origin="live_source", latest_goals=latest)
    second = store.add_from_observation(summary="Oil supply disruption", source_event_refs=("source:1",),
                                        origin="live_source", latest_goals=latest)
    assert first.goal_id == second.goal_id
    assert len(latest) == 1
    assert latest[first.goal_id]["execution_allowed"] is False


def test_stock_disclosure_preserves_transaction_details_without_backdating():
    payload = {"records": [{"politician_name": "Example", "politician_link": "example",
        "traded_issuer_ticker": "TEST", "traded_issuer_link": "test", "traded": "22 Sept 2026",
        "published": "13:05 Yesterday", "type": "buy", "size": "1K-15K"}]}
    event, = adapter("stock_act").normalize_payload(payload)
    assert event.raw_payload["event_timestamp_fallback_to_fetch_time"]
    assert event.raw_payload["measurements"]["size"] == "1K-15K"


def test_celestrak_preserves_orbital_measurements_and_reference_epoch():
    event, = adapter("space_track_celestrak").normalize_payload({"records": [{
        "NORAD_CAT_ID": 1, "EPOCH": "2026-09-24T00:00:00Z", "OBJECT_NAME": "Example",
        "MEAN_MOTION": 15.4, "INCLINATION": 51.6}]})
    assert event.raw_payload["measurements"]["MEAN_MOTION"] == 15.4
    assert event.raw_payload["publication_timestamp_known"] is False
