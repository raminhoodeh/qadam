from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from orchestrator.research.source_time import verified_timestamp, temporal_fields, retry_after_seconds
from orchestrator.research.source_context import capture_context, build_context_projection, context_for_instrument

NOW = datetime(2026, 10, 20, 19, tzinfo=timezone.utc)


def envelope(summary="Crude oil tanker disrupted in Hormuz", *, raw=None, stamp=None):
    return {"events": [{"normalised_summary": summary, "ingested_at": stamp or NOW.isoformat(),
            "raw_payload": {"record_id": "record-1", **(raw or {})}}],
            "raw_archive_path": "provider-archive.json", "degraded": False}


def capture(runtime, source="rss", result=None, *, now=NOW):
    return capture_context(runtime, {source: result or envelope()},
        {source: SimpleNamespace(validation_status="live", sample_fixture=False)}, now=now)


@pytest.mark.parametrize("value", ["nonsense", "2026-10-20", "2026-10-20T10:00:00", True, float("nan"), float("inf"), "tomorrow"])
def test_ambiguous_or_invalid_time_is_not_verified(value):
    assert verified_timestamp(value) is None


@pytest.mark.parametrize("value", ["20261020T180000Z", "2026-10-20T18:00:00Z", "2026-10-20 18:00:00.000000000 +0000 UTC"])
def test_explicit_provider_utc_formats_are_normalized(value):
    assert verified_timestamp(value) == "2026-10-20T18:00:00+00:00"


def test_transaction_date_and_nested_market_quote_do_not_become_publication():
    assert temporal_fields("stock_act", {"traded": "2026-10-20", "filedAt": "2026-10-20"}) == (None, None)
    assert temporal_fields("kalshi", {"kalshi": {"updated_at": NOW.isoformat()}}) == (None, None)
    assert temporal_fields("space_track_celestrak", {"observed_at": "2026-10-20T18:00:00"})[0].endswith("+00:00")


def test_retry_after_supports_http_dates_and_bounded_seconds():
    assert retry_after_seconds("120", now=NOW) == 120
    assert retry_after_seconds("Tue, 20 Oct 2026 20:00:00 GMT", now=NOW) == 3600
    assert retry_after_seconds("9999999", now=NOW) == 86400
    assert retry_after_seconds("NaN", now=NOW) is None


def test_first_seen_is_durable_and_cannot_be_backdated_by_reference_date(tmp_path):
    result = envelope("BLS inflation 120.5", raw={"value": 120.5, "reference_period": "2026-M09",
        "event_timestamp_fallback_to_fetch_time": True, "publication_timestamp_known": False})
    assert capture(tmp_path, "bls", result) == 1
    assert capture(tmp_path, "bls", result, now=NOW + timedelta(minutes=5)) == 0
    projection = build_context_projection(tmp_path, now=NOW + timedelta(minutes=5))
    row = projection["packets"][0]["evidence"][0]
    assert row["available_at"] == NOW.isoformat()
    assert row["provider_observed_at"] is None
    assert row["publication_timestamp_verified"] is False
    assert row["timestamp_role"] == "forward_only_first_seen"
    assert row["historical_backfill_eligible"] is False


def test_context_revision_creates_new_receipt_without_rewriting_old_value(tmp_path):
    capture(tmp_path, "bls", envelope("CPI", raw={"value": 1, "event_timestamp_fallback_to_fetch_time": True}))
    capture(tmp_path, "bls", envelope("CPI", raw={"value": 2, "event_timestamp_fallback_to_fetch_time": True}), now=NOW + timedelta(minutes=1))
    projection = build_context_projection(tmp_path, now=NOW + timedelta(minutes=1))
    assert projection["retained_receipt_count"] == 2
    assert projection["eligible_current_receipt_count"] == 1
    assert projection["packets"][0]["evidence"][0]["raw"]["value"] == 2


@pytest.mark.parametrize("flag", ["sample", "status_only", "derived", "summary_fallback_to_source_description"])
def test_fixture_and_status_material_cannot_enter_context(tmp_path, flag):
    assert capture(tmp_path, result=envelope(raw={flag: True})) == 0
    assert build_context_projection(tmp_path, now=NOW)["packet_count"] == 0


def test_future_and_secret_material_never_enters_database(tmp_path):
    assert capture(tmp_path, result=envelope(stamp=(NOW + timedelta(hours=1)).isoformat())) == 0
    assert capture(tmp_path, result=envelope(raw={"title": "ghp_" + "x" * 30})) == 0


def test_repeated_macro_values_remain_context_not_new_events(tmp_path):
    result = envelope("BLS CPI", raw={"reference_period": "2026-M09", "value": 3,
                                      "event_timestamp_fallback_to_fetch_time": True})
    capture(tmp_path, "bls", result)
    assert capture(tmp_path, "bls", result, now=NOW + timedelta(days=8)) == 0
    projection = build_context_projection(tmp_path, now=NOW + timedelta(days=8))
    assert projection["packet_count"] > 0
    assert projection["packets"][0]["evidence"][0]["available_at"] == NOW.isoformat()


def test_unrelated_sports_odds_do_not_support_oil_or_semiconductor_trades(tmp_path):
    capture(tmp_path, "polymarket", envelope("Dota 2: Team A versus Team B"))
    projection = build_context_projection(tmp_path, now=NOW)
    assert projection["packet_count"] == 0
    assert projection["unmapped_current_receipt_count"] == 1


def test_issuer_filing_is_joined_to_issuer_and_sector_not_every_symbol(tmp_path):
    capture(tmp_path, "sec_edgar", envelope("SEC NVDA 10-Q", raw={"issuer_symbols": ["NVDA"], "cik": "1045810"}))
    projection = build_context_projection(tmp_path, now=NOW)
    symbols = {row["instrument"] for row in projection["packets"]}
    assert "NVDA" in symbols and "SMH" in symbols
    assert "TSM" not in symbols and "USO" not in symbols and "SPY" not in symbols


def test_corridor_plus_news_creates_testable_packet_not_disruption_or_profit_claim(tmp_path):
    capture(tmp_path, "rss")
    capture(tmp_path, "ais_maritime", envelope("AIS vessel 123", raw={"latitude": 25.2, "longitude": 57.4, "speed_knots": 2}))
    projection = build_context_projection(tmp_path, now=NOW)
    packet = context_for_instrument(projection, "USO", as_of=NOW.isoformat())
    assert packet["state"] == "cross_source_testable_context"
    assert set(packet["source_keys"]) == {"rss", "ais_maritime"}
    assert "corridor_position_not_disruption_proof" in packet["roles"]
    assert packet["expected_return"] is None and packet["direction"] is None
    assert not packet["validated_edge"]
    assert packet["test_protocol"]["incremental_value_required_before_weight_or_size_increase"]


def test_stale_or_future_context_cannot_be_refreshed_by_relabelling_hypothesis_time(tmp_path):
    capture(tmp_path)
    projection = build_context_projection(tmp_path, now=NOW)
    projection["generated_at"] = (NOW + timedelta(hours=2)).isoformat()
    assert context_for_instrument(projection, "USO", as_of=projection["generated_at"]) is None
    projection["generated_at"] = NOW.isoformat()
    projection["packets"][0]["evidence"][0]["available_at"] = (NOW + timedelta(hours=1)).isoformat()
    symbol = projection["packets"][0]["instrument"]
    assert context_for_instrument(projection, symbol, as_of=NOW.isoformat()) is None


def test_reference_year_from_sample_layer_is_not_current_context(tmp_path):
    capture(tmp_path, "arcgis_usace", envelope("NOAA storm 2019", stamp="2019-09-09T00:00:00Z"))
    assert build_context_projection(tmp_path, now=NOW)["packet_count"] == 0


def test_empty_noaa_current_feed_is_valid_but_never_a_fake_event():
    from orchestrator.research.source_payloads import provider_records
    assert provider_records("arcgis_usace", {"activeStorms": []}) == []
    with pytest.raises(ValueError):
        provider_records("arcgis_usace", {"services": [{"name": "sampler"}]})


def test_provider_retry_after_is_respected_without_increasing_request_rate():
    from orchestrator.research.source_collection import collection_schedule
    row = collection_schedule({"degraded_reason": "HTTP_429", "retry_after_seconds": 7200}, {}, cadence_seconds=300, now=NOW)
    assert row["next_attempt_at"] == (NOW + timedelta(hours=2)).isoformat()


def test_gdelt_compact_timestamp_and_missing_date_flags_are_honest():
    from orchestrator.adapters import GDELTAdapter
    adapter = object.__new__(GDELTAdapter)
    rows = adapter.normalize_payload({"articles": [
        {"title": "Oil", "url": "https://example.com/a", "seendate": "20261020T180000Z"},
        {"title": "Chip", "url": "https://example.com/b"}]})
    assert rows[0].ingested_at == "2026-10-20T18:00:00+00:00"
    assert rows[0].raw_payload["timestamp_role"] == "provider_index_seen"
    assert rows[1].raw_payload["event_timestamp_fallback_to_fetch_time"]


def test_cross_source_packet_reaches_decision_without_bypassing_trigger_or_changing_size(tmp_path):
    from orchestrator.qadam_tradeability_reliability import _front_half, _load_fixture
    from orchestrator.qadam_strategy_decision import build_strategy_input, evaluate_strategy_input
    front = _front_half(_load_fixture("source-context"), "valid_pass", tmp_path)
    hypothesis = deepcopy(front["projection"])
    generated = front["akber_input"]["generated_at"]
    packet = {"packet_id": "cross-source:test", "instrument": "NVDA", "context_generated_at": generated,
              "source_keys": ["rss", "sec_edgar"], "evidence": [{"available_at": generated}]}
    hypothesis["cross_source_context"] = packet
    context = front["packet_state"]["packets"][0]["akber_context"]
    before = evaluate_strategy_input(build_strategy_input(front["projection"], context, generated_at=generated))
    after = evaluate_strategy_input(build_strategy_input(hypothesis, context, generated_at=generated))
    assert after["research_context_considered"] is True
    assert after["cross_source_context"]["packet_id"] == packet["packet_id"]
    assert after["decision"] == before["decision"]
    assert after["soft_evidence_size_multiplier"] == before["soft_evidence_size_multiplier"]


def test_new_artifacts_have_one_owner_and_a_declared_generation(tmp_path, monkeypatch):
    from orchestrator.qadam_artifact_ownership import build_artifact_ownership_audit
    from orchestrator.runtime.services import SERVICE_DEFINITIONS
    monkeypatch.setenv("QADAM_RUNTIME_DIR", str(tmp_path))
    audit = build_artifact_ownership_audit(tmp_path)
    assert not audit["undeclared_artifacts"]
    ingestion = next(row for row in SERVICE_DEFINITIONS if row.service_id == "source_ingestion")
    assert "qadam_cross_source_context.json" in ingestion.generation_artifacts


def test_fred_reference_date_is_context_not_release_time():
    from orchestrator.adapters import FREDAdapter
    adapter = object.__new__(FREDAdapter)
    events = adapter.normalize_payload(adapter.sample_payload(), alert_on_sigma=None)
    assert events
    assert all(row.raw_payload["timestamp_role"] == "reference_period_not_publication" for row in events)
    assert all(row.raw_payload["event_timestamp_fallback_to_fetch_time"] for row in events)


def test_matched_date_yield_curve_is_a_real_factor_not_a_research_score(tmp_path):
    result = envelope("US yield", raw={"record_id": "DGS10", "series_id": "DGS10", "value": 4.2,
        "reference_period": "2026-10-19", "event_timestamp_fallback_to_fetch_time": True})
    other = deepcopy(result["events"][0])
    other["raw_payload"].update(record_id="DGS2", series_id="DGS2", value=3.8)
    result["events"].append(other)
    capture(tmp_path, "fred", result)
    projection = build_context_projection(tmp_path, now=NOW)
    factors = context_for_instrument(projection, "SLV", as_of=NOW.isoformat())["factor_observations"]
    spread = next(row for row in factors if row["measurement"] == "matched_date_10y_minus_2y")
    assert spread["value"] == pytest.approx(0.4)
    assert len(spread["receipt_refs"]) == 2
    assert spread["measured_incremental_predictive_value"] is None


def test_geospatial_cells_require_actual_corridor_overlap(tmp_path):
    capture(tmp_path, "gps_jamming", envelope("Observed degraded GPS", raw={"latitude": 25.3, "longitude": 57.3,
        "reference_period": "2026-10-19", "navigation_accuracy_degraded_pct": 30,
        "event_timestamp_fallback_to_fetch_time": True}))
    projection = build_context_projection(tmp_path, now=NOW)
    packet = context_for_instrument(projection, "BNO", as_of=NOW.isoformat())
    assert "corridor_navigation_context_not_jamming_proof" in packet["roles"]
    assert context_for_instrument(projection, "NVDA", as_of=NOW.isoformat()) is None


def test_provider_cadence_prefers_six_hours_over_daily_alternative():
    from scripts.run_qadam_live_source_refresh import _cadence_seconds
    assert _cadence_seconds("6 hours or daily") == 21600


def test_noaa_request_does_not_query_the_demonstration_layer():
    from orchestrator.phase1_live_adapters import Phase1ReadOnlyAdapter, PHASE1_LIVE_ADAPTERS
    adapter = object.__new__(Phase1ReadOnlyAdapter)
    adapter.config = PHASE1_LIVE_ADAPTERS["arcgis_usace"]
    assert adapter._live_url() == "https://www.nhc.noaa.gov/CurrentStorms.json"
    assert adapter._request_params() == {}


def test_context_report_does_not_promote_first_seen_to_fresh_event(tmp_path):
    from orchestrator.research.source_collection import build_collection_coverage
    capture(tmp_path, "bls", envelope("CPI", raw={"value": 3, "event_timestamp_fallback_to_fetch_time": True}))
    context = build_context_projection(tmp_path, now=NOW)
    report = build_collection_coverage({}, [SimpleNamespace(key="bls")], {}, generated_at=NOW.isoformat(), context=context)
    row = report["sources"][0]
    assert row["forward_context_available"]
    assert row["evidence_freshness"] == "unknown"
    assert row["context_is_not_fresh_catalyst_or_execution_quote"]


def test_empty_current_snapshot_retires_old_events_without_erasing_history(tmp_path):
    capture(tmp_path)
    assert build_context_projection(tmp_path, now=NOW)["packet_count"]
    result = {"events": [], "raw_archive_path": "live-empty.json", "degraded": False}
    capture(tmp_path, result=result, now=NOW + timedelta(minutes=5))
    projection = build_context_projection(tmp_path, now=NOW + timedelta(minutes=5))
    assert projection["packet_count"] == 0
    assert projection["retained_receipt_count"] == 1


def test_failed_provider_probe_does_not_leave_old_context_claimed_current(tmp_path):
    capture(tmp_path)
    capture_context(tmp_path, {"rss": envelope()},
                    {"rss": SimpleNamespace(validation_status="degraded", sample_fixture=False)},
                    now=NOW + timedelta(minutes=5))
    assert build_context_projection(tmp_path, now=NOW + timedelta(minutes=5))["packet_count"] == 0
