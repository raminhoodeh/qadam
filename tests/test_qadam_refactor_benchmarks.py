from datetime import datetime, timedelta, timezone
import json

import pytest

from orchestrator.storage.benchmarks import record_observations, matched_fill_benchmark
from orchestrator.storage.control_plane import ControlPlaneStore


def _observation(at, identifier="one", price=100):
    return {"instrument": "SPY", "provider_backed": True, "provider": "alpaca_market_data",
            "origin_class": "live_read_only_provider_call", "observation_id": identifier,
            "price": price, "observed_at": at.isoformat(), "available_at": at.isoformat()}


def test_first_capture_time_is_preserved_across_replay(tmp_path):
    store = ControlPlaneStore(tmp_path / "state.sqlite3")
    observed = datetime.now(timezone.utc) - timedelta(seconds=30)
    row = _observation(observed)
    assert record_observations(store, [row]) == 1
    with store.connect() as connection:
        first = json.loads(connection.execute("SELECT payload_json FROM operating_events").fetchone()[0])
    assert record_observations(store, [row]) == 0
    with store.connect() as connection:
        second = json.loads(connection.execute("SELECT payload_json FROM operating_events").fetchone()[0])
    assert first == second
    assert datetime.fromisoformat(first["available_at"]) > observed


@pytest.mark.parametrize("changes", [
    {"price": True}, {"price": float("nan")}, {"provider_backed": False},
    {"origin_class": "runtime_market_context"}, {"fixture": True}, {"instrument": "NVDA"},
])
def test_nonprovider_or_invalid_observation_cannot_supply_benchmark(tmp_path, changes):
    store = ControlPlaneStore(tmp_path / "state.sqlite3")
    row = {**_observation(datetime.now(timezone.utc)), **changes}
    assert record_observations(store, [row]) == 0


def test_matched_benchmark_uses_only_information_available_before_each_fill(tmp_path):
    store = ControlPlaneStore(tmp_path / "state.sqlite3")
    opened = datetime.now(timezone.utc)
    closed = opened + timedelta(minutes=5)
    # These are isolated captured-provider fixtures, never live observations.
    with store.transaction() as connection:
        for target, identifier, price in ((opened, "entry", 100), (closed, "exit", 102)):
            row = _observation(target - timedelta(seconds=5), identifier, price)
            connection.execute("INSERT INTO operating_events VALUES (?,?,?,?,?,?,?)",
                (identifier, "paper_benchmark", "SPY", "provider_observed", json.dumps(row),
                 "fixture_digest:" + identifier, row["available_at"]))
        result = matched_fill_benchmark(connection, opened.isoformat(), closed.isoformat(), cost_bps=5)
        assert result["benchmark_net_return"] == pytest.approx(.0195)
        assert result["benchmark_costs_are_modelled"] is True
        missing = matched_fill_benchmark(connection, (opened-timedelta(seconds=6)).isoformat(),
                                         closed.isoformat(), cost_bps=5)
        assert missing["benchmark_comparison_available"] is False


def test_missing_required_output_is_not_successful_work(tmp_path):
    from orchestrator.runtime.operator import _publish_service_generations
    from orchestrator.runtime.services import SERVICE_DEFINITIONS
    from orchestrator.qadam_artifact_generations import GenerationError
    with pytest.raises(GenerationError, match="generation_required_artifact_missing"):
        _publish_service_generations(tmp_path, SERVICE_DEFINITIONS[0], [])


def test_provider_availability_is_response_time_not_request_or_injected_clock(monkeypatch):
    from io import BytesIO
    from orchestrator import qadam_forward_shadow as shadow
    monkeypatch.setattr(shadow, "secret_value", lambda *args: "fixture-secret-not-used-on-network")
    monkeypatch.setattr(shadow, "now_iso", lambda: "2026-09-06T12:00:05+00:00")
    monkeypatch.setattr(shadow, "urlopen", lambda *args, **kwargs: BytesIO(json.dumps({"bars": {
        "SPY": {"t": "2026-09-06T11:59:00+00:00", "c": 100, "v": 10}}}).encode()))
    rows, status = shadow.fetch_alpaca_latest_bar_observations(
        ["SPY"], None, generated_at="2026-09-06T12:00:00+00:00")
    assert status["status"] == "ok"
    assert rows[0]["available_at"] == "2026-09-06T12:00:05+00:00"
    assert rows[0]["observed_at"] == "2026-09-06T11:59:00+00:00"


def test_open_experiment_keeps_receiving_outcomes_when_current_trigger_disappears(tmp_path, monkeypatch):
    from dataclasses import replace
    from orchestrator import qadam_forward_shadow as shadow
    from orchestrator.config import Settings
    from orchestrator.storage import benchmarks
    decision = {"instrument": "SMH", "lifecycle_state": "open_awaiting_real_outcome"}
    terminal = {"instrument": "SPY", "lifecycle_state": "completed"}
    monkeypatch.setattr(shadow, "read_json", lambda *args: {})
    monkeypatch.setattr(shadow, "read_jsonl", lambda path: [decision, terminal] if path.name == shadow.DECISIONS_ARTIFACT else [])
    requested = []
    def fetch(instruments, *args, **kwargs):
        requested.extend(instruments)
        return [], {"status": "fixture_no_network"}
    monkeypatch.setattr(shadow, "fetch_alpaca_latest_bar_observations", fetch)
    monkeypatch.setattr(benchmarks, "record_observations", lambda *args: 0)
    monkeypatch.setattr(shadow, "build_forward_shadow_state_from_inputs", lambda *args, **kwargs: {"decisions": args[3]})
    state = shadow.build_forward_shadow_state(
        replace(Settings.from_env(), runtime_dir=str(tmp_path)), allow_network=True)
    assert requested == ["SMH"]
    assert state["decisions"] == [decision, terminal]
