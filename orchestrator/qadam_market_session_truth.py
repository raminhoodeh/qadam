"""Provider-backed market-clock truth for latency-sensitive paper decisions.

The Alpaca mirror exposes a read-only market clock.  This module turns that
clock into an actionable session record only while both the provider timestamp
and the local broker-mirror receipt are fresh.  A local calendar is used as a
disagreement check, never as a substitute for provider evidence.
"""

from __future__ import annotations

from datetime import datetime, time, timezone
from typing import Any
from zoneinfo import ZoneInfo

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    sha256_json,
    unique_errors,
    validate_authority,
)

SCHEMA_VERSION = "qadam_market_session_truth.v1"
POLICY_VERSION = "qadam-market-session-truth.1"
MAX_PROVIDER_CLOCK_AGE_SECONDS = 180
MAX_MIRROR_RECEIPT_AGE_SECONDS = 300
NEW_YORK = ZoneInfo("America/New_York")

TRUTH_ARTIFACT = "qadam_market_clock_truth.json"
HISTORY_ARTIFACT = "qadam_market_clock_history.jsonl"
CHECK_ARTIFACT = "qadam_market_session_checks.json"
MIRROR_ARTIFACT = "alpaca_paper_mirror.json"


def parse_timestamp(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _age_seconds(reference: datetime, value: Any) -> float | None:
    parsed = parse_timestamp(value)
    if parsed is None:
        return None
    return max(0.0, (reference - parsed).total_seconds())


def _expected_phase(reference: datetime) -> str:
    local = reference.astimezone(NEW_YORK)
    if local.weekday() >= 5:
        return "weekend"
    local_time = local.timetz().replace(tzinfo=None)
    if local_time < time(4, 0):
        return "overnight"
    if local_time < time(9, 30):
        return "pre_market"
    if local_time < time(16, 0):
        return "regular"
    if local_time < time(20, 0):
        return "post_market"
    return "overnight"


def build_market_clock_truth(
    mirror: dict[str, Any],
    *,
    generated_at: str | None = None,
    mirror_mtime: float | None = None,
) -> dict[str, Any]:
    generated_at = generated_at or now_iso()
    reference = parse_timestamp(generated_at) or datetime.now(timezone.utc)
    clock = mirror.get("market_clock")
    clock = clock if isinstance(clock, dict) else {}
    snapshot = mirror.get("snapshot")
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    provider_timestamp = clock.get("timestamp")
    provider_age = _age_seconds(reference, provider_timestamp)
    receipt_timestamp = snapshot.get("observed_at")
    receipt_age = _age_seconds(reference, receipt_timestamp)
    if receipt_age is None and mirror_mtime is not None:
        receipt_age = max(0.0, reference.timestamp() - mirror_mtime)
        receipt_timestamp = datetime.fromtimestamp(
            mirror_mtime, tz=timezone.utc
        ).isoformat()
    expected_phase = _expected_phase(reference)
    provider_is_open = clock.get("is_open") is True
    provider_fresh = (
        provider_age is not None
        and provider_age <= MAX_PROVIDER_CLOCK_AGE_SECONDS
        and receipt_age is not None
        and receipt_age <= MAX_MIRROR_RECEIPT_AGE_SECONDS
    )
    expected_open = expected_phase == "regular"
    calendar_disagreement = provider_fresh and provider_is_open != expected_open
    if not clock:
        session_phase = "provider_unavailable"
        stale_reason = "provider_clock_missing"
    elif not provider_fresh:
        session_phase = "provider_stale"
        stale_reason = (
            "provider_clock_stale"
            if provider_age is None or provider_age > MAX_PROVIDER_CLOCK_AGE_SECONDS
            else "mirror_receipt_stale"
        )
    elif calendar_disagreement:
        session_phase = "calendar_disagreement"
        stale_reason = "provider_calendar_disagreement"
    else:
        session_phase = "regular" if provider_is_open else expected_phase
        stale_reason = None
    actionable = bool(
        provider_fresh
        and provider_is_open
        and expected_open
        and not calendar_disagreement
    )
    provider_dt = parse_timestamp(provider_timestamp)
    session_date = (
        provider_dt.astimezone(NEW_YORK).date().isoformat()
        if provider_dt is not None and provider_fresh
        else None
    )
    material = {
        "provider_timestamp": provider_timestamp,
        "receipt_timestamp": receipt_timestamp,
        "provider_is_open": provider_is_open,
        "session_phase": session_phase,
        "session_date": session_date,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_market_clock_truth",
        "policy_version": POLICY_VERSION,
        "truth_id": "market-clock-truth:" + sha256_json(material)[:24],
        "generated_at": generated_at,
        "provider": "alpaca_paper_clock_v2",
        "provenance": "provider_backed_read_only_broker_clock",
        "provider_backed": bool(clock),
        "sample_or_fixture": False,
        "provider_timestamp": provider_timestamp,
        "local_receipt_timestamp": receipt_timestamp,
        "provider_clock_age_seconds": round(provider_age, 3)
        if provider_age is not None
        else None,
        "mirror_receipt_age_seconds": round(receipt_age, 3)
        if receipt_age is not None
        else None,
        "maximum_provider_clock_age_seconds": MAX_PROVIDER_CLOCK_AGE_SECONDS,
        "maximum_mirror_receipt_age_seconds": MAX_MIRROR_RECEIPT_AGE_SECONDS,
        "session_date": session_date,
        "session_phase": session_phase,
        "expected_session_phase": expected_phase,
        "is_open": provider_is_open,
        "next_open": clock.get("next_open"),
        "next_close": clock.get("next_close"),
        "provider_fresh": provider_fresh,
        "calendar_disagreement": calendar_disagreement,
        "actionable_for_conversion": actionable,
        "stale_reason": stale_reason,
        "paper_only": True,
        "read_only": True,
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "authority": authority_flags(),
    }


def validate_market_clock_truth(truth: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if truth.get("sample_or_fixture") is not False:
        errors.append("market_clock_fixture_or_sample")
    if truth.get("actionable_for_conversion") is True:
        if truth.get("provider_backed") is not True:
            errors.append("actionable_market_clock_not_provider_backed")
        if truth.get("provider_fresh") is not True:
            errors.append("actionable_market_clock_not_fresh")
        if truth.get("session_phase") != "regular":
            errors.append("actionable_market_clock_not_regular_session")
        if truth.get("session_date") is None:
            errors.append("actionable_market_clock_session_date_missing")
        if truth.get("calendar_disagreement") is True:
            errors.append("actionable_market_clock_calendar_disagreement")
    if int(truth.get("broker_write_count") or 0) != 0:
        errors.append("market_clock_broker_write_detected")
    if truth.get("live_capital_enabled") is not False:
        errors.append("market_clock_live_capital_enabled")
    errors.extend(validate_authority(truth.get("authority", {}), prefix="market_clock"))
    return unique_errors(errors)


def build_and_write_market_clock_truth(
    settings: Settings | None = None,
    *,
    generated_at: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    mirror_path = runtime / MIRROR_ARTIFACT
    mirror = read_json(mirror_path)
    truth = build_market_clock_truth(
        mirror,
        generated_at=generated_at,
        mirror_mtime=mirror_path.stat().st_mtime if mirror_path.is_file() else None,
    )
    errors = validate_market_clock_truth(truth)
    history = read_jsonl(runtime / HISTORY_ARTIFACT)
    by_id = {
        str(row.get("truth_id")): row for row in history if row.get("truth_id")
    }
    by_id[str(truth["truth_id"])] = truth
    history = sorted(by_id.values(), key=lambda row: str(row.get("generated_at") or ""))
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_market_session_checks",
        "generated_at": truth["generated_at"],
        "status": "passed" if not errors else "blocked",
        "provider_clock_present": bool(mirror.get("market_clock")),
        "provider_fresh": truth["provider_fresh"],
        "actionable_for_conversion": truth["actionable_for_conversion"],
        "session_phase": truth["session_phase"],
        "session_date": truth["session_date"],
        "history_record_count": len(history),
        "broker_write_count": 0,
        "live_capital_enabled": False,
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    store = AtomicArtifactStore(runtime)
    store.write_json(TRUTH_ARTIFACT, truth)
    store.write_jsonl(HISTORY_ARTIFACT, history)
    store.write_json(CHECK_ARTIFACT, checks)
    return truth, checks, errors


__all__ = [
    "CHECK_ARTIFACT",
    "HISTORY_ARTIFACT",
    "MAX_PROVIDER_CLOCK_AGE_SECONDS",
    "POLICY_VERSION",
    "TRUTH_ARTIFACT",
    "build_and_write_market_clock_truth",
    "build_market_clock_truth",
    "parse_timestamp",
    "validate_market_clock_truth",
]
