"""Real, exact-build minute samples for broker position-care availability."""

from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from zoneinfo import ZoneInfo


def record_care_sample(ledger, runtime, *, reconciliation, care, errors):
    from orchestrator.qadam_operator_ready_common import read_json
    from orchestrator.qadam_catc_soak import _build_key
    from orchestrator.qadam_market_session_truth import build_market_clock_truth
    status = read_json(runtime / "qadam_operator_service_status.json")
    build = status.get("build_identity") or {}
    key = _build_key(build.get("running") or {}) if build.get("running_build_matches_current") is True else None
    clock = build_market_clock_truth(read_json(runtime / "alpaca_paper_mirror.json"))
    if not key or clock.get("session_phase") != "regular" or clock.get("provider_fresh") is not True:
        return
    now = datetime.now(timezone.utc)
    minute = now.replace(second=0, microsecond=0).isoformat()
    blockers = list(errors) + list(care.get("blockers") or [])
    if reconciliation.get("status") != "passed":
        blockers.append("broker_reconciliation_not_passed")
    ledger.assert_execution_owner()
    row = {"build_key": key, "minute": minute,
           "market_session_date": now.astimezone(ZoneInfo("America/New_York")).date().isoformat(),
           "available": not blockers, "blockers": sorted(set(blockers)),
           "scope": "broker_position_care_not_signal_or_profit_availability",
           "simulated": False, "backfilled": False}
    encoded = json.dumps(row, sort_keys=True, separators=(",", ":"))
    digest = sha256(encoded.encode()).hexdigest()
    with ledger.store.transaction() as connection:
        connection.execute("INSERT OR IGNORE INTO operating_events VALUES (?,?,?,?,?,?,?)",
            ("care-availability:"+digest, "care_availability", key, "minute_observed", encoded, digest, now.isoformat()))


def session_care_availability(store, build_key, date_key, opening, closing):
    unavailable = {"available": False, "meets_target": False, "reason": "real_minute_samples_unavailable"}
    if not build_key or not opening or not closing:
        return unavailable
    with store.connect() as connection:
        rows = [json.loads(row[0]) for row in connection.execute(
            "SELECT payload_json FROM operating_events WHERE aggregate_type='care_availability' AND aggregate_id=? "
            "AND json_extract(payload_json,'$.market_session_date')=? ORDER BY created_at LIMIT 10000", (build_key, date_key))]
    minutes = {}
    for row in rows:
        minute = datetime.fromisoformat(row["minute"])
        if opening <= minute < closing and row.get("simulated") is False and row.get("backfilled") is False:
            minutes[row["minute"]] = minutes.get(row["minute"], True) and row.get("available") is True
    expected = math.ceil((closing-opening).total_seconds()/60)
    healthy = sum(minutes.values())
    return {"available": bool(minutes), "expected_session_minutes": expected,
            "observed_minutes": len(minutes), "healthy_minutes": healthy,
            "unobserved_minutes": max(0, expected-len(minutes)),
            "availability_fraction": healthy/expected if expected else None,
            "meets_target": expected > 0 and healthy/expected >= .99,
            "scope": "broker_position_care_not_signal_or_profit_availability"}
