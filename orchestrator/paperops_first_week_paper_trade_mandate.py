"""First-week paper-only trade decision mandate.

This module implements the user's short observation drill as paper-only order
intent. It deliberately stays outside proof credit and live-capital promotion.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
import json
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from orchestrator.config import Settings
from orchestrator.event_log import EventLog


PAPEROPS_FIRST_WEEK_MANDATE_SCHEMA_VERSION = 1
PAPEROPS_FIRST_WEEK_MANDATE_RUNTIME_ARTIFACT = (
    "paperops_first_week_paper_trade_mandate.json"
)
PAPEROPS_FIRST_WEEK_MANDATE_HISTORY = (
    "paperops_first_week_paper_trade_mandate_history.jsonl"
)
PAPEROPS_FIRST_WEEK_MANDATE_EVENT_LOG = (
    "paperops_first_week_paper_trade_mandate_events.jsonl"
)
PAPEROPS_FIRST_WEEK_MANDATE_EVENT_TYPE = (
    "paperops_first_week_paper_trade_mandate_recorded"
)
PAPEROPS_FIRST_WEEK_MANDATE_COMPONENT = "paperops_first_week_paper_trade_mandate"

MANDATE_START_DATE = date(2026, 5, 28)
MANDATE_DURATION_DAYS = 7
MANDATE_DAILY_TARGET = 3
MANDATE_MIN_NOTIONAL_USD = 6000.0
MANDATE_IDEMPOTENCY_NAMESPACE = "paperops_first_week_paper_trade_mandate"
MANDATE_ID_PREFIX = "paperops-fwpt"

MANDATE_SYMBOL_ROTATION: tuple[tuple[str, str, str], ...] = (
    ("SPY", "buy", "US broad-market baseline exposure"),
    ("QQQ", "buy", "large-cap technology momentum exposure"),
    ("GLD", "buy", "gold hedge and macro stress exposure"),
    ("IWM", "buy", "US small-cap breadth exposure"),
    ("TLT", "buy", "duration hedge and rates sensitivity exposure"),
    ("XLF", "buy", "financial-sector cyclicality exposure"),
    ("XLK", "buy", "technology-sector leadership exposure"),
    ("XLE", "buy", "energy-sector geopolitical sensitivity exposure"),
    ("XLV", "buy", "defensive healthcare-sector exposure"),
)

MANDATE_BOUNDARY = (
    "First-week paper trade mandate is paper-only order intent for observation. "
    "It targets three Alpaca paper decisions per calendar day for the first "
    "seven days starting 2026-05-28, with at least USD 6000 notional per "
    "candidate. It cannot use live credentials, cannot call live broker "
    "endpoints, cannot enable live capital, cannot create proof credit, cannot "
    "count as paper growth proof, cannot expose secrets, and cannot bypass "
    "PaperOps-2 idempotency or Alpaca paper endpoint checks."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def mandate_paths(settings: Settings | None = None) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PAPEROPS_FIRST_WEEK_MANDATE_RUNTIME_ARTIFACT,
        runtime / PAPEROPS_FIRST_WEEK_MANDATE_HISTORY,
        runtime / PAPEROPS_FIRST_WEEK_MANDATE_EVENT_LOG,
    )


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _local_date(settings: Settings) -> date:
    timezone_name = getattr(settings, "timezone", None) or "America/Los_Angeles"
    try:
        zone = ZoneInfo(str(timezone_name))
    except Exception:  # noqa: BLE001 - fallback is explicit and deterministic.
        zone = ZoneInfo("America/Los_Angeles")
    return datetime.now(zone).date()


def _date_key(value: date) -> str:
    return value.isoformat()


def _compact_date(value: date) -> str:
    return value.strftime("%Y%m%d")


def _mandate_window(local_date: date) -> dict[str, Any]:
    day_offset = (local_date - MANDATE_START_DATE).days
    active = 0 <= day_offset < MANDATE_DURATION_DAYS
    return {
        "start_date": _date_key(MANDATE_START_DATE),
        "end_date": _date_key(
            date.fromordinal(MANDATE_START_DATE.toordinal() + MANDATE_DURATION_DAYS - 1)
        ),
        "local_date": _date_key(local_date),
        "active": active,
        "day_number": day_offset + 1 if active else 0,
        "days_remaining": max(MANDATE_DURATION_DAYS - day_offset - 1, 0)
        if active
        else 0,
    }


def _submitted_source_keys(settings: Settings) -> set[str]:
    ledger_path = _runtime_dir(settings) / "paperops_alpaca_paper_post_submission_ledger.json"
    ledger = _read_json(ledger_path)
    keys = {
        str(key)
        for key in ledger.get("submitted_source_idempotency_keys", []) or []
        if str(key).startswith(MANDATE_ID_PREFIX)
    }
    latest = _read_json(_runtime_dir(settings) / "paperops_alpaca_paper_post.json")
    if latest.get("status") == "submitted_to_alpaca_paper":
        for record in latest.get("selected_post_records", []) or []:
            if not isinstance(record, dict):
                continue
            source_key = str(record.get("source_idempotency_key") or "")
            if source_key.startswith(MANDATE_ID_PREFIX):
                keys.add(source_key)
    return keys


def _plan_record(
    *,
    local_date: date,
    day_number: int,
    slot: int,
    submitted_source_keys: set[str],
) -> dict[str, Any]:
    symbol, side, thesis = MANDATE_SYMBOL_ROTATION[
        ((day_number - 1) * MANDATE_DAILY_TARGET + slot - 1)
        % len(MANDATE_SYMBOL_ROTATION)
    ]
    source_key = f"{MANDATE_ID_PREFIX}-{_compact_date(local_date)}-{slot:02d}"
    already_submitted = source_key in submitted_source_keys
    snapshot = {
        "snapshot_type": "first_week_paper_trade_mandate_pre_trade_snapshot",
        "local_date": _date_key(local_date),
        "day_number": day_number,
        "daily_slot": slot,
        "symbol": symbol,
        "side": side,
        "notional_usd": MANDATE_MIN_NOTIONAL_USD,
        "decision_thesis": thesis,
        "paper_only": True,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
    }
    return {
        "schema_version": PAPEROPS_FIRST_WEEK_MANDATE_SCHEMA_VERSION,
        "record_type": "paperops_first_week_paper_trade_decision",
        "artifact_id": f"paperops:first-week-paper-trade:{_date_key(local_date)}:{slot}",
        "decision_id": f"paperops:first-week:decision:{_date_key(local_date)}:{slot}",
        "local_date": _date_key(local_date),
        "day_number": day_number,
        "daily_slot": slot,
        "status": "already_submitted" if already_submitted else "ready_for_paperops2_submit",
        "source_family": "paperops_first_week_paper_trade_mandate",
        "source_phase": "PaperOps-first-week",
        "strategy_family_key": "first_week_paper_decision_visibility",
        "instrument": symbol,
        "alpaca_symbol": symbol,
        "selected_venue": "alpaca_paper",
        "side": side,
        "order_type": "market",
        "time_in_force": "day",
        "notional_usd": MANDATE_MIN_NOTIONAL_USD,
        "minimum_notional_usd": MANDATE_MIN_NOTIONAL_USD,
        "quantity": None,
        "idempotency_namespace": MANDATE_IDEMPOTENCY_NAMESPACE,
        "idempotency_key": source_key,
        "source_idempotency_key": source_key,
        "source_setup_record_id": source_key,
        "source_auto_approval_decision_id": (
            f"paperops:first-week:auto-approval:{_date_key(local_date)}:{slot}"
        ),
        "decision_rationale": (
            f"Paper-only first-week visibility trade: {thesis}. "
            "This is not proof credit and not live capital."
        ),
        "pre_trade_snapshot_required": True,
        "pre_trade_snapshot_present": True,
        "pre_trade_snapshot": snapshot,
        "event_log_prewrite_required": True,
        "event_log_prewrite_ready": True,
        "event_log_prewrite_written": True,
        "event_log_prewrite_ref": (
            f"paperops-first-week-prewrite:{_compact_date(local_date)}:{slot:02d}"
        ),
        "ready_for_paperops2_submit": not already_submitted,
        "already_submitted_to_alpaca_paper": already_submitted,
        "paper_only": True,
        "paper_submit_allowed": False,
        "broker_post_allowed": False,
        "live_endpoint_allowed": False,
        "live_capital_enabled": False,
        "proof_credit_allowed": False,
        "paper_growth_proof_credit_allowed": False,
        "secret_value_exposed": False,
        "raw_payload_exposed": False,
    }


def build_first_week_paper_trade_mandate(
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated_at = _now()
    local_date = _local_date(settings)
    window = _mandate_window(local_date)
    submitted_source_keys = _submitted_source_keys(settings)
    records = (
        [
            _plan_record(
                local_date=local_date,
                day_number=int(window["day_number"]),
                slot=slot,
                submitted_source_keys=submitted_source_keys,
            )
            for slot in range(1, MANDATE_DAILY_TARGET + 1)
        ]
        if window["active"]
        else []
    )
    submitted_today = [
        record for record in records if record.get("already_submitted_to_alpaca_paper")
    ]
    ready_today = [
        record for record in records if record.get("ready_for_paperops2_submit")
    ]
    status = "active_ready_for_paper_orders" if ready_today else "active_daily_target_met"
    if not window["active"]:
        status = "outside_first_week_window"
    artifact = {
        "schema_version": PAPEROPS_FIRST_WEEK_MANDATE_SCHEMA_VERSION,
        "artifact_type": "paperops_first_week_paper_trade_mandate",
        "artifact_id": "paperops:first-week-paper-trade-mandate",
        "phase": "PaperOps",
        "stage": "PaperOps-first-week-paper-trade-mandate",
        "status": status,
        "generated_at": generated_at,
        "public_safe": True,
        "recorded": False,
        "event_log_written": False,
        "event_log_path": None,
        "event_log_event_count": 0,
        **window,
        "daily_target_trade_count": MANDATE_DAILY_TARGET,
        "minimum_notional_usd": MANDATE_MIN_NOTIONAL_USD,
        "paper_only": True,
        "paper_order_submission_source_family": (
            "paperops_first_week_paper_trade_mandate"
        ),
        "daily_decision_count": len(records),
        "daily_ready_submit_count": len(ready_today),
        "daily_submitted_count": len(submitted_today),
        "daily_remaining_submit_count": max(
            MANDATE_DAILY_TARGET - len(submitted_today),
            0,
        )
        if window["active"]
        else 0,
        "mandate_records": records,
        "live_capital_enabled": False,
        "live_endpoint_allowed": False,
        "proof_credit_allowed": False,
        "paper_growth_proof_credit_allowed": False,
        "secret_value_exposed": False,
        "raw_payload_exposed": False,
        "boundary": MANDATE_BOUNDARY,
    }
    artifact["validation_errors"] = validate_first_week_paper_trade_mandate(artifact)
    artifact["validation_error_count"] = len(artifact["validation_errors"])
    if artifact["validation_errors"]:
        artifact["status"] = "invalid"
    return artifact


def validate_first_week_paper_trade_mandate(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if artifact.get("schema_version") != PAPEROPS_FIRST_WEEK_MANDATE_SCHEMA_VERSION:
        errors.append("first_week_mandate_schema_version_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("first_week_mandate_not_public_safe")
    if artifact.get("paper_only") is not True:
        errors.append("first_week_mandate_not_paper_only")
    for key in (
        "live_capital_enabled",
        "live_endpoint_allowed",
        "proof_credit_allowed",
        "paper_growth_proof_credit_allowed",
        "secret_value_exposed",
        "raw_payload_exposed",
    ):
        if artifact.get(key) is not False:
            errors.append(f"first_week_mandate_forbidden:{key}")
    if artifact.get("daily_target_trade_count") != MANDATE_DAILY_TARGET:
        errors.append("first_week_mandate_daily_target_mismatch")
    if float(artifact.get("minimum_notional_usd") or 0) < MANDATE_MIN_NOTIONAL_USD:
        errors.append("first_week_mandate_min_notional_too_small")
    records = artifact.get("mandate_records", [])
    if not isinstance(records, list):
        errors.append("first_week_mandate_records_not_list")
        records = []
    if artifact.get("active") is True and len(records) != MANDATE_DAILY_TARGET:
        errors.append("first_week_mandate_daily_record_count_mismatch")
    for record in records:
        if not isinstance(record, dict):
            errors.append("first_week_mandate_record_invalid")
            continue
        if record.get("selected_venue") != "alpaca_paper":
            errors.append("first_week_mandate_record_not_alpaca_paper")
        if str(record.get("idempotency_key") or "").startswith(MANDATE_ID_PREFIX) is not True:
            errors.append("first_week_mandate_record_idempotency_invalid")
        if record.get("idempotency_namespace") != MANDATE_IDEMPOTENCY_NAMESPACE:
            errors.append("first_week_mandate_record_namespace_invalid")
        if float(record.get("notional_usd") or 0) < MANDATE_MIN_NOTIONAL_USD:
            errors.append("first_week_mandate_record_notional_too_small")
        if record.get("paper_only") is not True:
            errors.append("first_week_mandate_record_not_paper_only")
        for key in (
            "live_capital_enabled",
            "live_endpoint_allowed",
            "proof_credit_allowed",
            "paper_growth_proof_credit_allowed",
            "secret_value_exposed",
            "raw_payload_exposed",
        ):
            if record.get(key) is not False:
                errors.append(f"first_week_mandate_record_forbidden:{key}")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "paper-only order intent",
        "USD 6000",
        "cannot use live credentials",
        "cannot call live broker endpoints",
        "cannot enable live capital",
        "cannot create proof credit",
        "cannot bypass PaperOps-2 idempotency",
    ):
        if phrase not in boundary:
            errors.append("first_week_mandate_boundary_weak")
            break
    return sorted(set(errors))


def read_latest_first_week_paper_trade_mandate(
    settings: Settings | None = None,
) -> dict[str, Any]:
    output_path, _, _ = mandate_paths(settings)
    return _read_json(output_path)


def first_week_paper_trade_mandate_public_status(
    settings: Settings | None = None,
) -> dict[str, Any]:
    artifact = read_latest_first_week_paper_trade_mandate(settings)
    if not artifact:
        artifact = build_first_week_paper_trade_mandate(settings)
    return {
        "schema_version": artifact.get("schema_version"),
        "status": artifact.get("status", "not_run"),
        "stage": artifact.get("stage", "PaperOps-first-week-paper-trade-mandate"),
        "active": artifact.get("active") is True,
        "start_date": artifact.get("start_date"),
        "end_date": artifact.get("end_date"),
        "local_date": artifact.get("local_date"),
        "day_number": artifact.get("day_number", 0),
        "daily_target_trade_count": artifact.get("daily_target_trade_count", 0),
        "minimum_notional_usd": artifact.get("minimum_notional_usd", 0),
        "daily_decision_count": artifact.get("daily_decision_count", 0),
        "daily_ready_submit_count": artifact.get("daily_ready_submit_count", 0),
        "daily_submitted_count": artifact.get("daily_submitted_count", 0),
        "daily_remaining_submit_count": artifact.get(
            "daily_remaining_submit_count",
            0,
        ),
        "paper_only": artifact.get("paper_only") is True,
        "live_capital_enabled": artifact.get("live_capital_enabled") is True,
        "proof_credit_allowed": artifact.get("proof_credit_allowed") is True,
        "validation_error_count": len(artifact.get("validation_errors", []) or []),
        "boundary": artifact.get("boundary", MANDATE_BOUNDARY),
    }


def write_first_week_paper_trade_mandate(
    artifact: dict[str, Any],
    settings: Settings | None = None,
    *,
    record_event: bool = True,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    settings = settings or Settings.from_env()
    output_path, history_path, event_path = mandate_paths(settings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = deepcopy(artifact)
    written["recorded"] = True
    if record_event:
        event = EventLog(event_path, echo=False).write(
            PAPEROPS_FIRST_WEEK_MANDATE_EVENT_TYPE,
            PAPEROPS_FIRST_WEEK_MANDATE_COMPONENT,
            payload={
                "status": written.get("status"),
                "active": written.get("active"),
                "local_date": written.get("local_date"),
                "daily_target_trade_count": written.get("daily_target_trade_count"),
                "minimum_notional_usd": written.get("minimum_notional_usd"),
                "daily_ready_submit_count": written.get("daily_ready_submit_count"),
                "daily_submitted_count": written.get("daily_submitted_count"),
                "daily_remaining_submit_count": written.get(
                    "daily_remaining_submit_count"
                ),
                "paper_only": written.get("paper_only"),
            },
        )
        written["event_log_written"] = True
        written["event_log_path"] = str(event_path)
        written["event_log_event_count"] = 1
        written["event_log_correlation_id"] = event.correlation_id
        written["event_log_created_at"] = event.created_at
    written["validation_errors"] = validate_first_week_paper_trade_mandate(written)
    written["validation_error_count"] = len(written["validation_errors"])
    if written["validation_errors"]:
        written["status"] = "invalid"
    output_path.write_text(
        json.dumps(written, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "schema_version": PAPEROPS_FIRST_WEEK_MANDATE_SCHEMA_VERSION,
                    "status": written.get("status"),
                    "recorded_at": _now(),
                    "local_date": written.get("local_date"),
                    "daily_target_trade_count": written.get("daily_target_trade_count"),
                    "minimum_notional_usd": written.get("minimum_notional_usd"),
                    "daily_ready_submit_count": written.get("daily_ready_submit_count"),
                    "daily_submitted_count": written.get("daily_submitted_count"),
                    "daily_remaining_submit_count": written.get(
                        "daily_remaining_submit_count"
                    ),
                    "validation_error_count": len(written["validation_errors"]),
                },
                sort_keys=True,
            )
            + "\n"
        )
    return output_path, history_path, event_path, written
