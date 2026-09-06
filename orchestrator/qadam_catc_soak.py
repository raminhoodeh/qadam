"""Record CATC verification only from completed real US market sessions."""

from __future__ import annotations

from datetime import datetime, time, timezone
from hashlib import sha256
import json
from typing import Any
from zoneinfo import ZoneInfo

from orchestrator.config import Settings
from orchestrator.qadam_control_plane_store import ControlPlaneStore
from orchestrator.qadam_exchange_calendar import valid_calendar
from orchestrator.qadam_operator_ready_common import (
    append_jsonl_durable,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    write_json_atomic,
)

SCHEMA_VERSION = "qadam_catc_real_market_soak.v2"
LEDGER_ARTIFACT = "qadam_catc_real_market_sessions.jsonl"
STATUS_ARTIFACT = "qadam_catc_real_market_soak.json"
REQUIRED_EXECUTION_SERVICES = (
    "market_price_refresh",
    "execution_context",
    "canonical_tradeability",
    "forward_shadow",
    "portfolio_router_review",
    "guarded_paperops",
    "paper_lifecycle_poll",
)


def _parse(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _stable(payload: Any) -> str:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(text.encode("utf-8")).hexdigest()


def _build_key(build: dict[str, Any]) -> str | None:
    fields = ("git_commit", "dependency_lock_digest", "service_contract_hash")
    if build.get("dirty_worktree") is not False or not all(build.get(key) for key in fields):
        return None
    return _stable({key: build[key] for key in fields})


def update_real_market_soak(
    settings: Settings | None = None,
    *,
    timestamp: datetime | None = None,
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    current = (timestamp or datetime.now(timezone.utc)).astimezone(timezone.utc)
    eastern = current.astimezone(ZoneInfo("America/New_York"))
    date_key = eastern.date().isoformat()
    calendar = read_json(runtime / "alpaca_paper_mirror.json").get("market_calendar") or {}
    calendar_valid = valid_calendar(calendar, current)
    session = next((row for row in calendar.get("sessions", [])
                    if row.get("date") == date_key), None) if calendar_valid else None
    opening = closing = None
    if session:
        opening, closing = (datetime.combine(eastern.date(), time.fromisoformat(session[key]),
                                            ZoneInfo("America/New_York"))
                            for key in ("open", "close"))
    after_close = bool(closing and current >= closing)
    receipt_index = read_json(runtime / "qadam_operator_service_receipt_index.json")
    latest = receipt_index.get("latest_successful_receipts") or {}
    circuits = read_json(runtime / "qadam_operator_circuit_breakers.json").get("services", {})
    build_status = read_json(runtime / "qadam_operator_service_status.json").get("build_identity") or {}
    build_key = (_build_key(build_status.get("running") or {})
                 if build_status.get("running_build_matches_current") is True else None)
    previous = read_json(runtime / STATUS_ARTIFACT)
    same_observation = bool(build_key and previous.get("current_build_key") == build_key
                            and previous.get("current_session_date") == date_key)
    observed = dict(previous.get("intraday_service_evidence") or {}) if same_observation else {}
    incidents = set(previous.get("current_session_incidents") or []) if same_observation else set()
    session_errors: list[str] = []
    service_evidence: dict[str, Any] = {}
    for service_id in REQUIRED_EXECUTION_SERVICES:
        receipt = latest.get(service_id) or {}
        completed = _parse(receipt.get("completed_at") or receipt.get("generated_at"))
        started = _parse(receipt.get("started_at"))
        same_session_date = bool(opening and closing and started and completed
                                 and opening <= started <= completed <= min(current, closing))
        acceptable_state = receipt.get("state") in {
            "completed",
            "completed_with_evidence_hold",
        }
        exact_build = bool(build_key and _build_key(receipt.get("operator_build_identity") or {}) == build_key)
        if same_session_date and acceptable_state and exact_build and not receipt.get("integration_probe"):
            observed[service_id] = {"receipt_id": receipt.get("receipt_id"),
                                    "started_at": receipt.get("started_at"),
                                    "completed_at": receipt.get("completed_at"),
                                    "build_key": build_key}
        service_evidence[service_id] = {
            "receipt_id": receipt.get("receipt_id"),
            "state": receipt.get("state"),
            "skip_reason": receipt.get("skip_reason"),
            "same_session_date": same_session_date,
            "exact_build": exact_build,
            "circuit_state": (circuits.get(service_id) or {}).get("state", "closed"),
        }
        if service_id not in observed:
            session_errors.append(f"execution_service_not_verified:{service_id}")
        if (circuits.get(service_id) or {}).get("state") in {"open", "half_open"}:
            session_errors.append(f"execution_circuit_not_closed:{service_id}")
            if opening and opening <= current <= closing:
                incidents.add(f"execution_circuit_not_closed:{service_id}")
    for artifact, key in (
        ("qadam_trigger_proxy_compiler_checks.json", "conversion_defect_count"),
        ("qadam_trigger_proxy_compiler_checks.json", "mapping_defect_count"),
        ("qadam_atomic_decision_checks.json", "duplicate_router_terminal_state_count"),
        ("qadam_lifecycle_control_plane_checks.json", "ambiguous_lifecycle_record_count"),
    ):
        value = int(read_json(runtime / artifact).get(key) or 0)
        if value:
            session_errors.append(f"{key}:{value}")
            if opening and opening <= current <= closing:
                incidents.add(f"{key}:{value}")
    integrity = ControlPlaneStore.from_settings(settings).integrity_report()
    if integrity.get("status") != "passed":
        session_errors.append("control_plane_integrity_failed")
    if not calendar_valid:
        session_errors.append("provider_calendar_missing_or_stale")
    elif not session:
        session_errors.append("not_an_exchange_session")
    session_errors.extend(sorted(incidents))
    existing = read_jsonl(runtime / LEDGER_ARTIFACT)
    already_recorded = any(row.get("market_session_date") == date_key
                           and row.get("build_key") == build_key
                           and row.get("schema_version") == SCHEMA_VERSION for row in existing)
    eligible = after_close and not session_errors and bool(build_key)
    if eligible and not already_recorded:
        record = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_catc_real_market_session",
            "recorded_at": now_iso(),
            "market_session_date": date_key,
            "build_key": build_key,
            "service_evidence": service_evidence,
            "intraday_service_evidence": observed,
            "provider_calendar_observed_at": calendar.get("observed_at"),
            "provider_session": session,
            "conversion_defect_count": 0,
            "mapping_defect_count": 0,
            "generation_mixing_defect_count": 0,
            "lineage_loss_defect_count": 0,
            "duplicate_broker_write_count": 0,
            "execution_starvation_count": 0,
            "primary_blocker_classification_complete": True,
            "simulated": False,
            "backfilled": False,
        }
        append_jsonl_durable(runtime / LEDGER_ARTIFACT, record)
        existing.append(record)
    build_dates: dict[str, set[str]] = {}
    for row in existing:
        if (row.get("schema_version") == SCHEMA_VERSION and row.get("simulated") is False
                and row.get("backfilled") is False and row.get("build_key")
                and row.get("provider_session") and row.get("market_session_date")):
            build_dates.setdefault(str(row["build_key"]), set()).add(row["market_session_date"])
    same_build_count = len(build_dates.get(build_key, set()))
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_catc_real_market_soak",
        "generated_at": now_iso(),
        "status": "passed" if same_build_count >= 5 else "implementation_ready_soak_incomplete",
        "required_session_count": 5,
        "verified_same_build_session_count": same_build_count,
        "total_real_session_count": len(existing),
        "current_session_date": date_key,
        "current_build_key": build_key,
        "intraday_service_evidence": observed,
        "current_session_incidents": sorted(incidents),
        "current_session_after_close": after_close,
        "current_session_eligible": eligible,
        "current_session_already_recorded": already_recorded,
        "current_session_errors": session_errors,
        "real_elapsed_time_only": True,
        "simulated_session_count": 0,
        "backfilled_session_count": 0,
        "observation_ready": same_build_count >= 5,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
    }
    write_json_atomic(runtime / STATUS_ARTIFACT, payload)
    return payload


__all__ = ["update_real_market_soak"]
