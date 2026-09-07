"""Prospective provider observations for matching actual paper-fill windows."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import math


def capture_execution_benchmark(settings, *, context: str) -> dict:
    """Read-only, bounded, best-effort capture before broker reconciliation.

    Failure is an attribution gap, never a reason to prevent a protective exit.
    The original two-minute matching rule and first-availability time remain.
    """
    from orchestrator.qadam_operator_ready_common import runtime_dir, write_json_atomic
    from orchestrator.storage.control_plane import ControlPlaneStore
    from orchestrator.qadam_forward_shadow import fetch_alpaca_latest_bar_observations

    captured = datetime.now(timezone.utc)
    report = {"generated_at": captured.isoformat(), "context": context,
              "status": "unavailable", "broker_write_count": 0,
              "benchmark_matching_max_age_seconds": 120, "blocks_execution": False}
    try:
        store = ControlPlaneStore.from_settings(settings)
        with store.connect() as connection:
            latest = connection.execute(
                "SELECT payload_json FROM operating_events WHERE aggregate_type='paper_benchmark' "
                "ORDER BY created_at DESC LIMIT 1").fetchone()
        row = json.loads(latest[0]) if latest else {}
        observed, available = _time(row.get("observed_at")), _time(row.get("available_at"))
        if (observed and available and observed <= available <= captured and (captured-observed).total_seconds() <= 60
                and row.get("provider_backed") is True and not row.get("sample") and not row.get("fixture")
                and row.get("origin_class") == "live_read_only_provider_call" and row.get("instrument") == "SPY"
                and type(row.get("price")) in (int, float) and math.isfinite(row["price"]) and row["price"] > 0):
            report.update(status="fresh_existing_observation", observation_id=row.get("observation_id"))
        else:
            observations, provider = fetch_alpaca_latest_bar_observations(
                ["SPY"], settings, generated_at=captured.isoformat(), timeout_seconds=3)
            written = record_observations(store, observations)
            report.update(status="captured" if written else "no_new_observation",
                          observation_count=written, provider_status=provider.get("status"))
    except Exception as exc:  # Attribution cannot disable a guarded exit.
        report.update(status="unavailable", failure_class=type(exc).__name__)
    try:
        write_json_atomic(runtime_dir(settings) / "qadam_execution_benchmark_capture.json", report)
    except OSError:
        pass  # The execution outcome still exposes missing benchmark attribution.
    return report


def _time(value):
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return stamp if stamp.tzinfo else None
    except ValueError:
        return None


def record_observations(store, observations: list[dict]) -> int:
    captured = datetime.now(timezone.utc)
    accepted = []
    for source in observations:
        observed, available = _time(source.get("observed_at")), _time(source.get("available_at"))
        price = source.get("price")
        if (source.get("instrument") != "SPY" or source.get("provider_backed") is not True
            or source.get("origin_class") != "live_read_only_provider_call"
            or source.get("sample") or source.get("fixture") or not source.get("observation_id")
            or not observed or not available or not observed <= available <= captured
            or isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0):
            continue
        row = {**source, "producer_available_at": source["available_at"], "available_at": captured.isoformat()}
        accepted.append(row)
    if not accepted:
        return 0
    written = 0
    with store.transaction() as connection:
        for row in accepted:
            encoded = json.dumps(row, sort_keys=True, separators=(",", ":"))
            event_id = "paper-benchmark:" + sha256(row["observation_id"].encode()).hexdigest()
            written += connection.execute(
                "INSERT OR IGNORE INTO operating_events (event_id,aggregate_type,aggregate_id,event_type,"
                "payload_json,payload_sha256,created_at) VALUES (?,'paper_benchmark','SPY','provider_observed',?,?,?)",
                (event_id, encoded, sha256(encoded.encode()).hexdigest(), row["available_at"])).rowcount
    return written


def matched_fill_benchmark(connection, opened_at: str, closed_at: str, *, cost_bps: float) -> dict:
    opened, closed = _time(opened_at), _time(closed_at)
    if not opened or not closed or closed <= opened:
        return {"benchmark_comparison_available": False, "benchmark_unavailable_reason": "invalid_fill_window"}
    matched = []
    for target in (opened, closed):
        start = (target - timedelta(seconds=120)).astimezone(timezone.utc).isoformat()
        end = target.astimezone(timezone.utc).isoformat()
        rows = connection.execute(
            "SELECT payload_json FROM operating_events WHERE aggregate_type='paper_benchmark' "
            "AND created_at>=? AND created_at<=? ORDER BY created_at DESC LIMIT 128", (start, end))
        valid = []
        for record in rows:
            row = json.loads(record[0])
            stamp, available = _time(row.get("observed_at")), _time(row.get("available_at"))
            price = row.get("price")
            if (stamp and available and stamp <= available <= target and 0 <= (target-stamp).total_seconds() <= 120
                and row.get("provider_backed") is True and isinstance(price, (int, float))
                and not isinstance(price, bool) and math.isfinite(price) and price > 0):
                valid.append(row)
        if not valid:
            return {"benchmark_comparison_available": False, "benchmark_unavailable_reason": "no_provider_matched_fill_window_benchmark"}
        matched.append(max(valid, key=lambda row: _time(row["observed_at"])))
    value = matched[1]["price"] / matched[0]["price"] - 1 - cost_bps / 10000
    return {"benchmark_comparison_available": True, "benchmark_net_return": value,
            "benchmark_unavailable_reason": None, "benchmark_costs_are_modelled": True,
            "benchmark_entry_observation": matched[0], "benchmark_exit_observation": matched[1]}
