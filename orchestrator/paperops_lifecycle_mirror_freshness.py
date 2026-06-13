"""PaperOps lifecycle and mirror freshness diagnostics."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.paper_account import PaperAccountMirrorStore


PAPEROPS_LIFECYCLE_MIRROR_FRESHNESS_SCHEMA_VERSION = 1
PAPEROPS_LIFECYCLE_MIRROR_FRESHNESS_BOUNDARY = (
    "Public-safe PaperOps lifecycle and paper-account mirror freshness diagnostic. "
    "It can require newer read-only lifecycle and mirror observations after a "
    "guarded paper close receipt, but it cannot submit, close, cancel, resize, "
    "approve, write broker state, call live endpoints, or grant paper proof ledger credit."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings) -> Path:
    return Path(settings.runtime_dir)


def _read_runtime_json(settings: Settings, name: str) -> dict[str, Any]:
    path = _runtime_dir(settings) / name
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _parse_time(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _close_requested_at(record: dict[str, Any]) -> datetime | None:
    receipt = record.get("broker_close_receipt")
    if not isinstance(receipt, dict):
        receipt = {}
    for key in ("closed_at", "paper_position_close_requested_at", "close_requested_at"):
        parsed = _parse_time(receipt.get(key) or record.get(key))
        if parsed:
            return parsed
    return None


def _is_successful_close_record(record: dict[str, Any]) -> bool:
    if not isinstance(record, dict):
        return False
    status_code = _int(record.get("sanitized_http_status"))
    return (
        record.get("status") == "paper_exit_close_recorded"
        and (
            record.get("paper_position_close_succeeded") is True
            or record.get("paper_position_close_succeeded") is None
        )
        and (status_code == 0 or 200 <= status_code < 300)
    )


def _successful_close_records(exit_path: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for key in ("selected_exit_records", "pending_close_request_exit_candidates"):
        for record in exit_path.get(key, []) or []:
            if isinstance(record, dict) and _is_successful_close_record(record):
                records.append(record)
    latest_at = _parse_time(exit_path.get("latest_successful_close_requested_at"))
    if latest_at:
        records.append(
            {
                "status": "paper_exit_close_recorded",
                "paper_position_close_succeeded": True,
                "paper_position_close_requested_at": latest_at.isoformat(),
                "symbol": exit_path.get("latest_successful_close_symbol"),
            }
        )
    return records


def _latest_successful_close(exit_path: dict[str, Any]) -> dict[str, Any]:
    latest_record: dict[str, Any] | None = None
    latest_at: datetime | None = None
    for record in _successful_close_records(exit_path):
        closed_at = _close_requested_at(record)
        if closed_at and (latest_at is None or closed_at > latest_at):
            latest_at = closed_at
            latest_record = record
    return {
        "present": latest_at is not None,
        "requested_at": _iso(latest_at),
        "symbol": latest_record.get("symbol") if latest_record else None,
        "request_fingerprint": (
            latest_record.get("request_fingerprint") if latest_record else None
        ),
    }


def _poll_observed_at(lifecycle_poller: dict[str, Any]) -> datetime | None:
    observed: list[datetime] = []
    for result in lifecycle_poller.get("poll_result_records", []) or []:
        if not isinstance(result, dict):
            continue
        for section_key in ("order_readback", "position_readback"):
            section = result.get(section_key)
            if isinstance(section, dict):
                parsed = _parse_time(section.get("polled_at"))
                if parsed:
                    observed.append(parsed)
    return max(observed) if observed else None


def _paper_mirror_observed_at(settings: Settings) -> tuple[datetime | None, str]:
    try:
        latest = PaperAccountMirrorStore(settings=settings).latest_snapshot()
    except Exception:  # noqa: BLE001 - diagnostic must degrade safely.
        return None, "unavailable"
    if latest is None:
        return None, "missing"
    return _parse_time(latest.observed_at), latest.connection_status


def build_paperops_lifecycle_mirror_freshness(
    *,
    settings: Settings | None = None,
    exit_path: dict[str, Any] | None = None,
    lifecycle_poller: dict[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    exit_path = exit_path if exit_path is not None else _read_runtime_json(
        settings,
        "paperops_paper_exit_path.json",
    )
    lifecycle_poller = (
        lifecycle_poller
        if lifecycle_poller is not None
        else _read_runtime_json(settings, "paperops_paper_lifecycle_poller.json")
    )
    latest_close = _latest_successful_close(exit_path)
    close_at = _parse_time(latest_close.get("requested_at"))
    lifecycle_observed_at = _poll_observed_at(lifecycle_poller)
    mirror_observed_at, mirror_status = _paper_mirror_observed_at(settings)
    freshness_required = close_at is not None
    lifecycle_fresh = (
        not freshness_required
        or (
            lifecycle_observed_at is not None
            and lifecycle_observed_at > close_at
            and _int(lifecycle_poller.get("broker_get_called_count")) > 0
        )
    )
    mirror_fresh = (
        not freshness_required
        or (mirror_observed_at is not None and mirror_observed_at > close_at)
    )
    fresh = lifecycle_fresh and mirror_fresh
    if not freshness_required:
        status = "freshness_not_required"
    elif fresh:
        status = "fresh_after_latest_close"
    elif not lifecycle_fresh and not mirror_fresh:
        status = "waiting_lifecycle_and_mirror_refresh"
    elif not lifecycle_fresh:
        status = "waiting_lifecycle_refresh"
    else:
        status = "waiting_mirror_refresh"
    return {
        "schema_version": PAPEROPS_LIFECYCLE_MIRROR_FRESHNESS_SCHEMA_VERSION,
        "artifact_type": "paperops_lifecycle_mirror_freshness",
        "artifact_id": "paperops:lifecycle-mirror-freshness:latest",
        "generated_at": generated_at or _now(),
        "status": status,
        "public_safe": True,
        "freshness_required": freshness_required,
        "fresh_after_latest_close": fresh,
        "lifecycle_fresh_after_latest_close": lifecycle_fresh,
        "paper_mirror_fresh_after_latest_close": mirror_fresh,
        "latest_successful_close_requested_at": latest_close.get("requested_at"),
        "latest_successful_close_symbol": latest_close.get("symbol"),
        "latest_successful_close_request_fingerprint": latest_close.get(
            "request_fingerprint"
        ),
        "paperops_lifecycle_poll_observed_at": _iso(lifecycle_observed_at),
        "paperops_lifecycle_event_log_created_at": lifecycle_poller.get(
            "event_log_created_at"
        ),
        "paperops_lifecycle_broker_get_called_count": _int(
            lifecycle_poller.get("broker_get_called_count")
        ),
        "paper_mirror_observed_at": _iso(mirror_observed_at),
        "paper_mirror_connection_status": mirror_status,
        "live_capital_enabled": False,
        "broker_post_called_count": 0,
        "live_endpoint_called_count": 0,
        "phase7_proof_credit_allowed": False,
        "boundary": PAPEROPS_LIFECYCLE_MIRROR_FRESHNESS_BOUNDARY,
    }
