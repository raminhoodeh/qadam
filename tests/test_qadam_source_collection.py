from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from orchestrator.research.source_collection import build_collection_coverage, collection_schedule

NOW = datetime(2026, 9, 24, tzinfo=timezone.utc)


def test_weekly_network_failure_retries_in_minutes_not_next_week():
    result = collection_schedule({"degraded_reason": "ConnectTimeout", "degraded": True}, {},
                                 cadence_seconds=7 * 86400, now=NOW)
    assert result["next_attempt_at"] == (NOW + timedelta(minutes=5)).isoformat()
    assert result["last_success_at"] is None
    assert result["collection_status"] == "retry_scheduled"


def test_repeated_failure_backs_off_without_inventing_success():
    previous = {"consecutive_failures": 2, "last_success_at": "2026-09-20T00:00:00Z"}
    result = collection_schedule({"degraded": True}, previous, cadence_seconds=86400, now=NOW)
    assert result["consecutive_failures"] == 3
    assert result["next_attempt_at"] == (NOW + timedelta(minutes=20)).isoformat()
    assert result["last_success_at"] == previous["last_success_at"]


def test_success_resets_backoff_and_restores_publication_cadence():
    result = collection_schedule({"validation_status": "live", "event_count": 0},
                                 {"consecutive_failures": 8}, cadence_seconds=86400, now=NOW)
    assert result["consecutive_failures"] == 0
    assert result["last_success_at"] == NOW.isoformat()
    assert result["event_count"] == 0
    assert result["next_attempt_at"] == (NOW + timedelta(days=1)).isoformat()


def test_credentials_and_throttling_are_not_hammered():
    for reason, status in [("HTTP_401", "needs_configuration"), ("HTTP_402", "needs_configuration"),
                           ("HTTP_400", "needs_adapter_repair"), ("HTTP_404", "needs_adapter_repair"),
                           ("HTTP_429", "retry_scheduled")]:
        row = collection_schedule({"degraded_reason": reason}, {}, cadence_seconds=300, now=NOW)
        assert row["collection_status"] == status
        assert datetime.fromisoformat(row["next_attempt_at"]) >= NOW + timedelta(hours=1)


def test_catalog_has_explicit_alias_disabled_and_missing_collector_states():
    specs = [SimpleNamespace(key="rss", status="adapter_live_optional"),
             SimpleNamespace(key="paid", status="intentionally_disabled"),
             SimpleNamespace(key="missing", status="needs_adapter")]
    coverage = build_collection_coverage({"sources": [{"source_key": "social.rss"},
                                                       {"source_key": "yahoo_finance"}]}, specs,
        {"rss": collection_schedule({"validation_status": "live"}, {}, cadence_seconds=300, now=NOW)},
        generated_at=NOW.isoformat())
    rows = {row["source_key"]: row for row in coverage["sources"]}
    assert coverage["catalogue_count"] == 5
    assert rows["social.rss"]["collection_status"] == "derived_alias"
    assert rows["paid"]["collection_status"] == "intentionally_disabled"
    assert rows["missing"]["collection_status"] == "not_scheduled"
    assert rows["yahoo_finance"]["collection_status"] == "external_collector"
    assert not coverage["all_sources_collecting"]


def test_overdue_collector_is_not_reported_collected():
    schedule = collection_schedule({"validation_status": "live"}, {}, cadence_seconds=300, now=NOW)
    result = build_collection_coverage({}, [SimpleNamespace(key="rss")], {"rss": schedule},
                                       generated_at=(NOW + timedelta(hours=1)).isoformat())
    assert result["sources"][0]["collection_status"] == "overdue"


def test_bis_parser_preserves_values_without_backdating_publication():
    from orchestrator.phase1_live_adapters import _bis_sdmx_payload, Phase1ReadOnlyAdapter, PHASE1_LIVE_ADAPTERS
    payload = _bis_sdmx_payload('<Data xmlns="urn:sdmx"><Series><Obs TIME_PERIOD="2026-08" OBS_VALUE="4.5"/></Series></Data>')
    adapter = object.__new__(Phase1ReadOnlyAdapter)
    adapter.config = PHASE1_LIVE_ADAPTERS["bis"]
    events = adapter.normalize_payload(payload)
    assert len(events) == 1
    raw = events[0].raw_payload
    assert raw["value"] == 4.5
    assert raw["reference_period"] == "2026-08"
    assert raw["publication_timestamp_known"] is False
    assert raw["event_timestamp_fallback_to_fetch_time"] is True


def test_comtrade_request_is_bounded_and_uses_header_auth(monkeypatch):
    import orchestrator.phase1_live_adapters as adapters
    adapter = object.__new__(adapters.Phase1ReadOnlyAdapter)
    adapter.config = adapters.PHASE1_LIVE_ADAPTERS["un_comtrade"]
    adapter.settings = None
    monkeypatch.setattr(adapters, "secret_value", lambda *args: "test-key-not-a-secret")
    assert adapter.config.primary_endpoint.endswith("/get/C/A/HS")
    assert adapter._request_headers()["Ocp-Apim-Subscription-Key"] == "test-key-not-a-secret"
    params = adapter._request_params()
    assert params["maxrecords"] == 25
    assert "subscription-key" not in params
    events = adapter.normalize_payload({"data": [{"primaryValue": 100, "period": 2025,
                                                "cmdCode": "8542", "reporterCode": "842"}]})
    assert events[0].raw_payload["primaryValue"] == 100
    assert events[0].raw_payload["event_timestamp_fallback_to_fetch_time"] is True


def test_ais_uses_bounded_websocket_subscription_without_archiving_key(monkeypatch):
    import asyncio
    import json
    import websockets
    from orchestrator.phase1_live_adapters import _aisstream_payload

    sent = []
    frames = [{"MessageType": "SubscriptionConfirmation"}] + [
        {"MessageType": "PositionReport", "MetaData": {"MMSI": 123456789},
         "Message": {"PositionReport": {"Valid": True, "Latitude": 25, "Longitude": 57, "Sog": 5}}}
    ] * 25

    class Socket:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def send(self, value):
            sent.append(json.loads(value))

        async def recv(self):
            return json.dumps(frames.pop(0)).encode()

    def connect(url, **kwargs):
        assert url.startswith("wss://")
        assert kwargs["compression"] == "deflate"
        return Socket()

    monkeypatch.setattr(websockets, "connect", connect)
    payload = asyncio.run(_aisstream_payload("test-credential", timeout_seconds=12))
    assert len(payload["records"]) == 25
    assert payload["subscription_confirmed"]
    assert sent[0]["FilterMessageTypes"] == ["PositionReport"]
    assert "test-credential" not in json.dumps(payload)


def test_ais_control_frames_and_invalid_positions_are_not_observations():
    from orchestrator.phase1_live_adapters import _ais_position_record
    assert _ais_position_record({"MessageType": "SubscriptionConfirmation"}) is None
    assert _ais_position_record({"MessageType": "PositionReport", "MetaData": {"MMSI": 1},
                                 "Message": {"PositionReport": {"Valid": False}}}) is None
