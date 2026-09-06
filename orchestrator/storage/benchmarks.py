"""Prospective provider observations for matching actual paper-fill windows."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import math


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
