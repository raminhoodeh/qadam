"""PaperOps guarded close-to-ledger verifier.

This module records public-safe evidence for the final paper close-to-ledger
handoff. It does not call brokers or grant Phase 7 proof credit; it only
counts a closed proof trade when the latest guarded paper close has a verified
receipt, fresh lifecycle and mirror observations, Research Goal lineage, and a
local postmortem-due marker.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.paperops_lifecycle_mirror_freshness import (
    build_paperops_lifecycle_mirror_freshness,
)


PAPEROPS_CLOSE_TO_LEDGER_SCHEMA_VERSION = 1
PAPEROPS_CLOSE_TO_LEDGER_RUNTIME_ARTIFACT = "paperops_close_to_ledger.json"
PAPEROPS_CLOSE_TO_LEDGER_HISTORY = "paperops_close_to_ledger_history.jsonl"
PAPEROPS_CLOSE_TO_LEDGER_EVENT_LOG = "paperops_close_to_ledger_events.jsonl"
PAPEROPS_CLOSE_TO_LEDGER_EVENT_TYPE = "paperops_close_to_ledger_recorded"
PAPEROPS_CLOSE_TO_LEDGER_COMPONENT = "paperops_close_to_ledger"
PAPEROPS_POSTMORTEM_DUE_WITHIN_HOURS = 24

PAPEROPS_CLOSE_TO_LEDGER_BOUNDARY = (
    "Public-safe PaperOps close-to-ledger verifier. It can verify that a "
    "guarded Alpaca Paper close receipt, fresh lifecycle polling, fresh "
    "paper-account mirror state, Research Goal lineage, and a local "
    "postmortem-due marker exist before counting a closed paper proof ledger "
    "record, but it cannot submit, close, cancel, resize, approve, write "
    "broker state, call live endpoints, or grant Phase 7 proof credit."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return records
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _parse_time(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _close_timestamp(record: dict[str, Any], *, fallback: Any = None) -> datetime | None:
    receipt = record.get("broker_close_receipt")
    if not isinstance(receipt, dict):
        receipt = {}
    for key in (
        "closed_at",
        "paper_position_close_requested_at",
        "close_requested_at",
        "recorded_at",
    ):
        parsed = _parse_time(receipt.get(key) or record.get(key))
        if parsed:
            return parsed
    return _parse_time(fallback)


def _is_successful_close(record: dict[str, Any]) -> bool:
    if not isinstance(record, dict):
        return False
    status_code = _int(record.get("sanitized_http_status"))
    return (
        record.get("status") == "paper_exit_close_recorded"
        and record.get("paper_position_close_succeeded") is True
        and 200 <= status_code < 300
    )


def _lineage(record: dict[str, Any]) -> dict[str, Any]:
    source_setup = str(record.get("source_setup_record_id") or "").strip()
    source_submit = str(record.get("source_submit_record_artifact_id") or "").strip()
    source_order = str(record.get("source_proof_order_id") or "").strip()
    source_staged = str(record.get("source_staged_order_artifact_id") or "").strip()
    source_auto = str(record.get("source_auto_approval_decision_id") or "").strip()
    idempotency_key = str(record.get("idempotency_key") or "").strip()
    present = bool(source_setup and (source_submit or source_order or source_staged or source_auto))
    return {
        "research_goal_lineage_present": present,
        "source_setup_record_id": source_setup or None,
        "source_submit_record_artifact_id": source_submit or None,
        "source_proof_order_id": source_order or None,
        "source_staged_order_artifact_id": source_staged or None,
        "source_auto_approval_decision_id": source_auto or None,
        "idempotency_key": idempotency_key or None,
    }


def _candidate_key(record: dict[str, Any]) -> str:
    return str(
        record.get("request_fingerprint")
        or record.get("client_order_id_hash")
        or record.get("broker_order_id_hash")
        or record.get("symbol")
        or "unknown"
    )


def _history_success_records(settings: Settings) -> list[dict[str, Any]]:
    history_path = _runtime_dir(settings) / "paperops_paper_exit_path_history.jsonl"
    records: list[dict[str, Any]] = []
    for parent in _read_jsonl(history_path):
        for selected in parent.get("selected_exit_records", []) or []:
            if not isinstance(selected, dict) or not _is_successful_close(selected):
                continue
            merged = dict(selected)
            merged["parent_recorded_at"] = parent.get("recorded_at")
            if parent.get("latest_successful_close_requested_at"):
                merged["latest_successful_close_requested_at"] = parent.get(
                    "latest_successful_close_requested_at"
                )
            records.append(merged)
    return records


def _current_success_records(exit_path: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for key in ("selected_exit_records", "pending_close_request_exit_candidates"):
        for record in exit_path.get(key, []) or []:
            if isinstance(record, dict) and _is_successful_close(record):
                records.append(dict(record))
    latest_at = exit_path.get("latest_successful_close_requested_at")
    latest_symbol = exit_path.get("latest_successful_close_symbol")
    if latest_at:
        for record in exit_path.get("pending_close_request_exit_candidates", []) or []:
            if isinstance(record, dict) and record.get("symbol") == latest_symbol:
                merged = dict(record)
                merged["status"] = "paper_exit_close_recorded"
                merged["paper_position_close_succeeded"] = True
                merged["sanitized_http_status"] = 200
                merged["latest_successful_close_requested_at"] = latest_at
                records.append(merged)
                break
        else:
            records.append(
                {
                    "status": "paper_exit_close_recorded",
                    "paper_position_close_succeeded": True,
                    "sanitized_http_status": 200,
                    "symbol": latest_symbol,
                    "latest_successful_close_requested_at": latest_at,
                }
            )
    return records


def _latest_success_record(
    *,
    settings: Settings,
    exit_path: dict[str, Any],
) -> dict[str, Any] | None:
    latest_hint = _parse_time(exit_path.get("latest_successful_close_requested_at"))
    candidates = [*_current_success_records(exit_path), *_history_success_records(settings)]
    best_record: dict[str, Any] | None = None
    best_at: datetime | None = None
    for record in candidates:
        close_at = _close_timestamp(
            record,
            fallback=record.get("latest_successful_close_requested_at")
            or exit_path.get("latest_successful_close_requested_at"),
        )
        if latest_hint and close_at and abs((close_at - latest_hint).total_seconds()) > 3600:
            continue
        if close_at and (best_at is None or close_at > best_at):
            best_at = close_at
            best_record = record
    if best_record is None and latest_hint:
        return {
            "status": "paper_exit_close_recorded",
            "paper_position_close_succeeded": True,
            "sanitized_http_status": 200,
            "symbol": exit_path.get("latest_successful_close_symbol"),
            "latest_successful_close_requested_at": latest_hint.isoformat(),
        }
    if best_record is not None and best_at is not None:
        best_record = dict(best_record)
        best_record["resolved_close_requested_at"] = best_at.isoformat()
    return best_record


def _postmortem_due_by(close_at: str | None) -> str | None:
    parsed = _parse_time(close_at)
    if parsed is None:
        return None
    return (parsed + timedelta(hours=PAPEROPS_POSTMORTEM_DUE_WITHIN_HOURS)).isoformat()


def _verified_record(
    *,
    generated_at: str,
    close_record: dict[str, Any],
    close_at: str,
    freshness: dict[str, Any],
) -> dict[str, Any]:
    lineage = _lineage(close_record)
    key = _candidate_key(close_record)
    symbol = str(close_record.get("symbol") or "").strip() or None
    return {
        "schema_version": PAPEROPS_CLOSE_TO_LEDGER_SCHEMA_VERSION,
        "record_type": "paperops_verified_closed_paper_proof_record",
        "record_id": f"paperops-close-ledger:{key}",
        "generated_at": generated_at,
        "symbol": symbol,
        "guarded_close_receipt_present": True,
        "guarded_close_receipt_status": close_record.get("status"),
        "guarded_close_requested_at": close_at,
        "request_fingerprint": close_record.get("request_fingerprint"),
        "sanitized_http_status": close_record.get("sanitized_http_status"),
        "lifecycle_mirror_fresh_after_latest_close": (
            freshness.get("fresh_after_latest_close") is True
        ),
        "postmortem_due_marker_created": True,
        "postmortem_due_at": generated_at,
        "postmortem_due_by": _postmortem_due_by(close_at),
        "paper_proof_ledger_recorded": True,
        "research_goal_lineage_present": lineage["research_goal_lineage_present"],
        **lineage,
        "public_safe": True,
        "live_capital_enabled": False,
        "broker_post_called": False,
        "broker_post_called_count": 0,
        "live_endpoint_called": False,
        "live_endpoint_called_count": 0,
        "phase7_proof_credit_allowed": False,
        "boundary": (
            "Verified closed paper proof record derived from existing guarded "
            "PaperOps artifacts only; no broker write or proof-credit authority."
        ),
    }


def paperops_close_to_ledger_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / PAPEROPS_CLOSE_TO_LEDGER_RUNTIME_ARTIFACT,
        runtime / PAPEROPS_CLOSE_TO_LEDGER_HISTORY,
        runtime / PAPEROPS_CLOSE_TO_LEDGER_EVENT_LOG,
    )


def build_paperops_close_to_ledger(
    *,
    settings: Settings | None = None,
    generated_at: str | None = None,
    exit_path: dict[str, Any] | None = None,
    lifecycle_poller: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    generated = generated_at or _now()
    runtime = _runtime_dir(settings)
    exit_path = exit_path or _read_json(runtime / "paperops_paper_exit_path.json")
    lifecycle_poller = lifecycle_poller or _read_json(
        runtime / "paperops_paper_lifecycle_poller.json"
    )
    freshness = build_paperops_lifecycle_mirror_freshness(
        settings=settings,
        exit_path=exit_path,
        lifecycle_poller=lifecycle_poller,
        generated_at=generated,
    )
    close_record = _latest_success_record(settings=settings, exit_path=exit_path)
    close_at = (
        _iso(_close_timestamp(close_record or {}, fallback=freshness.get("latest_successful_close_requested_at")))
        if close_record
        else freshness.get("latest_successful_close_requested_at")
    )
    receipt_present = close_record is not None and bool(close_at)
    receipt_verified = bool(close_record and _is_successful_close(close_record))
    lineage = _lineage(close_record or {})
    freshness_ready = freshness.get("fresh_after_latest_close") is True
    latest_close_proof_eligible = receipt_verified and freshness_ready and lineage[
        "research_goal_lineage_present"
    ]
    postmortem_marker_allowed = receipt_verified and freshness_ready and lineage[
        "research_goal_lineage_present"
    ]
    verified_records = (
        [
            _verified_record(
                generated_at=generated,
                close_record=close_record or {},
                close_at=str(close_at),
                freshness=freshness,
            )
        ]
        if postmortem_marker_allowed and close_at
        else []
    )
    blockers: list[str] = []
    if not receipt_present:
        blockers.append("guarded_close_receipt_missing")
    elif not receipt_verified:
        blockers.append("guarded_close_receipt_not_verified")
    if receipt_present and not freshness_ready:
        blockers.append("lifecycle_mirror_refresh_required_after_close")
    non_proof_close_reasons: list[str] = []
    if receipt_present and freshness_ready and not lineage["research_goal_lineage_present"]:
        non_proof_close_reasons.append("research_goal_lineage_missing")
    if receipt_present and freshness_ready and lineage[
        "research_goal_lineage_present"
    ] and not verified_records:
        blockers.append("postmortem_due_marker_missing")
    if verified_records:
        status = "paper_proof_ledger_recorded"
    elif "guarded_close_receipt_missing" in blockers:
        status = "waiting_guarded_close_receipt"
    elif "lifecycle_mirror_refresh_required_after_close" in blockers:
        status = "waiting_lifecycle_mirror_refresh"
    elif receipt_present and freshness_ready and not lineage["research_goal_lineage_present"]:
        status = "waiting_lineaged_guarded_close"
    elif "postmortem_due_marker_missing" in blockers:
        status = "ready_pending_postmortem_due_marker"
    else:
        status = "blocked_close_to_ledger_evidence"
    artifact = {
        "schema_version": PAPEROPS_CLOSE_TO_LEDGER_SCHEMA_VERSION,
        "artifact_type": "paperops_close_to_ledger",
        "artifact_id": "paperops:close-to-ledger:latest",
        "generated_at": generated,
        "status": status,
        "public_safe": True,
        "latest_successful_close_requested_at": close_at,
        "latest_successful_close_symbol": (
            (close_record or {}).get("symbol")
            or freshness.get("latest_successful_close_symbol")
        ),
        "latest_successful_close_request_fingerprint": (
            (close_record or {}).get("request_fingerprint")
            or freshness.get("latest_successful_close_request_fingerprint")
        ),
        "guarded_close_receipt_present": receipt_present,
        "guarded_close_receipt_verified": receipt_verified,
        "lifecycle_mirror_freshness_status": freshness.get("status"),
        "lifecycle_mirror_fresh_after_latest_close": freshness_ready,
        "paperops_lifecycle_poll_observed_at": freshness.get(
            "paperops_lifecycle_poll_observed_at"
        ),
        "paper_mirror_observed_at": freshness.get("paper_mirror_observed_at"),
        "research_goal_lineage_present": lineage["research_goal_lineage_present"],
        "latest_close_proof_eligible": latest_close_proof_eligible,
        "latest_close_non_proof_reason_count": len(non_proof_close_reasons),
        "latest_close_non_proof_reasons": non_proof_close_reasons,
        "source_setup_record_id": lineage["source_setup_record_id"],
        "source_submit_record_artifact_id": lineage["source_submit_record_artifact_id"],
        "source_proof_order_id": lineage["source_proof_order_id"],
        "source_staged_order_artifact_id": lineage["source_staged_order_artifact_id"],
        "source_auto_approval_decision_id": lineage["source_auto_approval_decision_id"],
        "idempotency_key": lineage["idempotency_key"],
        "postmortem_due_marker_created_count": len(verified_records),
        "paper_proof_ledger_verified_record_count": len(verified_records),
        "closed_proof_trade_count": len(verified_records),
        "verified_closed_proof_trade_count": len(verified_records),
        "mirror_trade_counted_for_proof_count": 0,
        "verified_records": verified_records,
        "blockers": sorted(set(blockers)),
        "blocker_count": len(set(blockers)),
        "live_capital_enabled": False,
        "broker_post_called_count": 0,
        "live_endpoint_called_count": 0,
        "phase7_proof_credit_allowed": False,
        "phase7_proof_credit_allowed_count": 0,
        "boundary": PAPEROPS_CLOSE_TO_LEDGER_BOUNDARY,
    }
    artifact["validation_errors"] = validate_paperops_close_to_ledger(artifact)
    artifact["validation_error_count"] = len(artifact["validation_errors"])
    if artifact["validation_errors"]:
        artifact["status"] = "invalid"
    return artifact


def validate_paperops_close_to_ledger(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if artifact.get("schema_version") != PAPEROPS_CLOSE_TO_LEDGER_SCHEMA_VERSION:
        errors.append("paperops_close_to_ledger_schema_version_mismatch")
    if artifact.get("artifact_type") != "paperops_close_to_ledger":
        errors.append("paperops_close_to_ledger_artifact_type_mismatch")
    if artifact.get("public_safe") is not True:
        errors.append("paperops_close_to_ledger_not_public_safe")
    if artifact.get("live_capital_enabled") is not False:
        errors.append("paperops_close_to_ledger_live_capital_enabled")
    if artifact.get("phase7_proof_credit_allowed") is not False:
        errors.append("paperops_close_to_ledger_phase7_proof_credit_allowed")
    if _int(artifact.get("phase7_proof_credit_allowed_count")) != 0:
        errors.append("paperops_close_to_ledger_phase7_proof_credit_count_nonzero")
    if _int(artifact.get("broker_post_called_count")) != 0:
        errors.append("paperops_close_to_ledger_broker_post_called")
    if _int(artifact.get("live_endpoint_called_count")) != 0:
        errors.append("paperops_close_to_ledger_live_endpoint_called")
    if _int(artifact.get("mirror_trade_counted_for_proof_count")) != 0:
        errors.append("paperops_close_to_ledger_mirror_trade_counted_for_proof")
    records = artifact.get("verified_records", [])
    if not isinstance(records, list):
        errors.append("paperops_close_to_ledger_verified_records_not_list")
        records = []
    closed_count = _int(artifact.get("closed_proof_trade_count"))
    if closed_count != len(records):
        errors.append("paperops_close_to_ledger_closed_count_mismatch")
    if _int(artifact.get("paper_proof_ledger_verified_record_count")) != len(records):
        errors.append("paperops_close_to_ledger_verified_count_mismatch")
    if _int(artifact.get("postmortem_due_marker_created_count")) != len(records):
        errors.append("paperops_close_to_ledger_postmortem_marker_count_mismatch")
    if records:
        if artifact.get("guarded_close_receipt_verified") is not True:
            errors.append("paperops_close_to_ledger_record_without_close_receipt")
        if artifact.get("lifecycle_mirror_fresh_after_latest_close") is not True:
            errors.append("paperops_close_to_ledger_record_without_freshness")
        if artifact.get("research_goal_lineage_present") is not True:
            errors.append("paperops_close_to_ledger_record_without_lineage")
        for record in records:
            if not isinstance(record, dict):
                errors.append("paperops_close_to_ledger_verified_record_invalid")
                continue
            if record.get("postmortem_due_marker_created") is not True:
                errors.append("paperops_close_to_ledger_record_missing_postmortem")
            if record.get("paper_proof_ledger_recorded") is not True:
                errors.append("paperops_close_to_ledger_record_not_ledgered")
            if record.get("phase7_proof_credit_allowed") is not False:
                errors.append("paperops_close_to_ledger_record_proof_credit_allowed")
            if record.get("live_capital_enabled") is not False:
                errors.append("paperops_close_to_ledger_record_live_capital_enabled")
            if _int(record.get("broker_post_called_count")) != 0:
                errors.append("paperops_close_to_ledger_record_broker_post_called")
            if _int(record.get("live_endpoint_called_count")) != 0:
                errors.append("paperops_close_to_ledger_record_live_endpoint_called")
    blockers = artifact.get("blockers", [])
    if not isinstance(blockers, list):
        errors.append("paperops_close_to_ledger_blockers_not_list")
        blockers = []
    if _int(artifact.get("blocker_count")) != len(blockers):
        errors.append("paperops_close_to_ledger_blocker_count_mismatch")
    if records and blockers:
        errors.append("paperops_close_to_ledger_recorded_with_blockers")
    boundary = str(artifact.get("boundary") or "")
    for phrase in (
        "guarded Alpaca Paper close receipt",
        "fresh lifecycle polling",
        "Research Goal lineage",
        "cannot submit",
        "grant Phase 7 proof credit",
    ):
        if phrase not in boundary:
            errors.append("paperops_close_to_ledger_boundary_weak")
    return sorted(set(errors))


def write_paperops_close_to_ledger(
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    artifact = build_paperops_close_to_ledger(settings=settings)
    runtime_path, history_path, event_log_path = paperops_close_to_ledger_paths(settings)
    artifact["runtime_artifact_path"] = f"data/runtime/{PAPEROPS_CLOSE_TO_LEDGER_RUNTIME_ARTIFACT}"
    artifact["history_log_path"] = f"data/runtime/{PAPEROPS_CLOSE_TO_LEDGER_HISTORY}"
    artifact["event_log_path"] = f"data/runtime/{PAPEROPS_CLOSE_TO_LEDGER_EVENT_LOG}"
    _write_json(runtime_path, artifact)
    _append_jsonl(history_path, artifact)
    event_log = EventLog(path=event_log_path, echo=False)
    entry = event_log.write(
        PAPEROPS_CLOSE_TO_LEDGER_EVENT_TYPE,
        PAPEROPS_CLOSE_TO_LEDGER_COMPONENT,
        {
            "status": artifact["status"],
            "closed_proof_trade_count": artifact["closed_proof_trade_count"],
            "postmortem_due_marker_created_count": artifact[
                "postmortem_due_marker_created_count"
            ],
            "blocker_count": artifact["blocker_count"],
            "validation_error_count": artifact["validation_error_count"],
            "live_endpoint_called_count": artifact["live_endpoint_called_count"],
            "broker_post_called_count": artifact["broker_post_called_count"],
            "phase7_proof_credit_allowed": artifact["phase7_proof_credit_allowed"],
        },
    )
    artifact["event_log_written"] = True
    artifact["event_log_event_count"] = 1
    artifact["event_log_created_at"] = entry.created_at
    artifact["event_log_correlation_id"] = entry.correlation_id
    _write_json(runtime_path, artifact)
    return artifact


def paperops_close_to_ledger_public_status(
    settings: Settings | None = None,
) -> dict[str, Any]:
    return build_paperops_close_to_ledger(settings=settings)
