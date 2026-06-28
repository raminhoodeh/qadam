"""QSASE-14 Telegram Summary Boundary.

QSASE Telegram output is a notification-candidate layer only. It can create
short, specific, deduped, dashboard-visible message candidates and read-only
inbound records. It cannot send live messages without an explicit future gate,
execute Telegram commands, create candidates, approvals, paper orders, broker
writes, proof credit, quantum jobs, or live-capital authority.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qsase_governance_safety_contract import (
    PHASE_STATUS_ARTIFACT,
    universal_authority_flags,
)

SCHEMA_VERSION = "qsase_telegram_notification_boundary.v1"
PHASE_ID = "qsase_14_telegram_summary_boundary"
PHASE_NAME = "QSASE-14: Telegram Summary Boundary"
IMPLEMENTATION_LOG = "docs/qsase-implementation-log.md"

PRIMARY_ARTIFACT = "qsase_telegram_notification_boundary.json"
MESSAGE_CANDIDATES_ARTIFACT = "qsase_telegram_message_candidates.json"
MESSAGE_QUEUE_ARTIFACT = "qsase_telegram_message_queue.json"
MESSAGE_QUALITY_ARTIFACT = "qsase_telegram_message_quality.json"
DEDUPE_LEDGER_ARTIFACT = "qsase_telegram_dedupe_ledger.jsonl"
DELIVERY_RECEIPTS_ARTIFACT = "qsase_telegram_delivery_receipts.jsonl"
INBOUND_READONLY_ARTIFACT = "qsase_telegram_inbound_readonly_intake.json"
NOTIFICATION_HISTORY_ARTIFACT = "qsase_telegram_notification_history.jsonl"
DASHBOARD_COMMUNICATIONS_ARTIFACT = "qsase_telegram_dashboard_communications_mirror.json"
EVENTS_ARTIFACT = "qsase_telegram_notification_boundary_events.jsonl"

QSASE_DASHBOARD_STATUS_ARTIFACT = "qsase_dashboard_status.json"
QSASE_DASHBOARD_DECISION_RECORDS_ARTIFACT = "qsase_dashboard_decision_records.json"
QSASE_DASHBOARD_REPAIR_QUEUE_ARTIFACT = "qsase_dashboard_repair_queue.json"
QSASE_DASHBOARD_LEARNING_LEDGER_ARTIFACT = "qsase_dashboard_learning_ledger.json"
QSASE_PAPEROPS_GATE_ARTIFACT = "qsase_paperops_gate_interface.json"
QSASE_STRATEGY_ROUTER_ARTIFACT = "qsase_strategy_router_decisions.json"
PAPEROPS_SUMMARY_ARTIFACT = "paperops_autonomous_pass_summary.json"
TELEGRAM_INBOUND_ARTIFACT = "telegram_inbound_intake.jsonl"
TELEGRAM_WORLD_EVENTS_ARTIFACT = "telegram_world_event_datapoints.jsonl"
TELEGRAM_STRATEGY_CONSIDERATIONS_ARTIFACT = "telegram_strategy_considerations.jsonl"

MESSAGE_STATUSES = {
    "message_candidate_created",
    "message_rejected_generic",
    "message_rejected_duplicate",
    "message_rejected_unsafe",
    "message_ready_for_dashboard_only",
    "message_ready_to_send",
    "message_sent",
    "message_already_sent",
    "message_delivery_failed",
    "message_send_not_allowed",
}

TELEGRAM_AUTHORITY_FLAGS = {
    "telegram_review_only": True,
    "telegram_command_path_enabled": False,
    "telegram_trade_command_enabled": False,
    "telegram_live_send_allowed": False,
    "live_send_attempted": False,
    "trade_candidate_created": False,
    "qualified_setup_created": False,
    "risk_approval_created": False,
    "execution_approval_created": False,
    "paper_order_allowed": False,
    "paper_order_created": False,
    "broker_write_allowed": False,
    "broker_write_created": False,
    "qctrl_job_submitted": False,
    "quantum_provider_call_allowed": False,
    "proof_credit_allowed": False,
    "paper_proof_ledger_credit_allowed": False,
    "paper_growth_trial_calendar_advance_allowed": False,
    "simulated_elapsed_time_allowed": False,
    "live_capital_enabled": False,
    "secret_read_allowed": False,
    "secret_write_allowed": False,
}

FALSE_AUTHORITY_FIELDS = {
    key for key, value in TELEGRAM_AUTHORITY_FLAGS.items() if value is False
}

GENERIC_PHRASES = (
    "qadam codebase upgrade",
    "what changed:",
    "why it matters:",
    "what to check:",
    "detected update areas:",
    "ai-powered",
    "advanced ai",
    "cutting edge",
    "seamless",
    "synergy",
    "robust insights",
    "dynamic insights",
    "system update",
    "status update",
    "everything is running",
    "backend state changed",
)

UNSAFE_TEXT_PATTERNS = (
    re.compile(r"^/\w+", re.MULTILINE),
    re.compile(r"\b(?:buy|sell|short|long|close|cancel|replace|submit|approve)\s+[A-Z]{1,6}\b", re.IGNORECASE),
    re.compile(r"\b(?:quantum confirmed|trade approved|risk approved|execution approved|live capital enabled)\b", re.IGNORECASE),
    re.compile(r"\b(?:broker command|place order|submit order|grant proof)\b", re.IGNORECASE),
)

COMMAND_PATTERNS = (
    re.compile(r"^\s*/\w+", re.IGNORECASE),
    re.compile(r"\b(?:buy|sell|short|close|cancel|replace|approve|reject|resize)\b", re.IGNORECASE),
    re.compile(r"\b(?:place order|submit order|enable live|use live capital)\b", re.IGNORECASE),
)

REQUIRED_CANDIDATE_FIELDS = (
    "message_candidate_id",
    "message_class",
    "status",
    "title",
    "body",
    "decision_record_ref",
    "source_artifact_refs",
    "fingerprint",
    "quality",
    "delivery",
    "authority",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _runtime_dir(settings: Settings | None = None) -> Path:
    active_settings = settings or Settings.from_env()
    path = Path(active_settings.runtime_dir)
    if not path.is_absolute():
        path = _repo_root() / path
    return path


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _json_dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _jsonl_line(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True) + "\n"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    if limit is not None:
        lines = lines[-limit:]
    records: list[dict[str, Any]] = []
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
    path.write_text(_json_dump(payload), encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(_jsonl_line(record) for record in records), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(_jsonl_line(payload))


def _hash_id(parts: list[Any], prefix: str) -> str:
    raw = "|".join(str(part) for part in parts)
    return f"{prefix}:{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]}"


def _fingerprint_payload(payload: dict[str, Any]) -> str:
    raw = "|".join(
        str(payload.get(key) or "")
        for key in (
            "message_class",
            "state",
            "strategy_family",
            "candidate_id",
            "blocker",
            "next_allowed_action",
            "order_state",
            "proof_state",
        )
    )
    return hashlib.sha256(raw.lower().encode("utf-8")).hexdigest()


def _short(value: Any, fallback: str = "not recorded", limit: int = 86) -> str:
    text = " ".join(str(value or "").split()).strip()
    return (text[:limit] or fallback).strip()


def _artifact_ref(filename: str, pointer: str | None = None) -> str:
    base = f"data/runtime/{filename}"
    return f"{base}#{pointer}" if pointer else base


def _authority_block() -> dict[str, Any]:
    return dict(TELEGRAM_AUTHORITY_FLAGS)


def _load_context(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "runtime_dir": runtime,
        "dashboard_status": _read_json(runtime / QSASE_DASHBOARD_STATUS_ARTIFACT),
        "dashboard_decision_records": _read_json(runtime / QSASE_DASHBOARD_DECISION_RECORDS_ARTIFACT),
        "dashboard_repair_queue": _read_json(runtime / QSASE_DASHBOARD_REPAIR_QUEUE_ARTIFACT),
        "dashboard_learning_ledger": _read_json(runtime / QSASE_DASHBOARD_LEARNING_LEDGER_ARTIFACT),
        "paperops_gate": _read_json(runtime / QSASE_PAPEROPS_GATE_ARTIFACT),
        "strategy_router": _read_json(runtime / QSASE_STRATEGY_ROUTER_ARTIFACT),
        "paperops_summary": _read_json(runtime / PAPEROPS_SUMMARY_ARTIFACT),
        "inbound_records": _read_jsonl(runtime / TELEGRAM_INBOUND_ARTIFACT, limit=200),
        "world_event_records": _read_jsonl(runtime / TELEGRAM_WORLD_EVENTS_ARTIFACT, limit=200),
        "strategy_considerations": _read_jsonl(runtime / TELEGRAM_STRATEGY_CONSIDERATIONS_ARTIFACT, limit=200),
        "dedupe_history": _read_jsonl(runtime / DEDUPE_LEDGER_ARTIFACT, limit=500),
        "delivery_history": _read_jsonl(runtime / DELIVERY_RECEIPTS_ARTIFACT, limit=500),
    }


def _decision_records(context: dict[str, Any]) -> list[dict[str, Any]]:
    return context.get("dashboard_decision_records", {}).get("records", []) if isinstance(context.get("dashboard_decision_records"), dict) else []


def _find_decision(context: dict[str, Any], module: str) -> dict[str, Any]:
    for record in _decision_records(context):
        if record.get("module") == module:
            return record
    return {}


def _candidate_template(
    *,
    message_class: str,
    title: str,
    state: str,
    reason: str,
    next_action: str,
    order_line: str,
    strategy_family: str,
    candidate_id: str,
    blocker: str,
    decision_record_ref: str,
    source_artifact_refs: list[str],
) -> dict[str, Any]:
    state = _short(state, "not recorded", 54)
    reason = _short(reason, "not recorded", 88)
    next_action = _short(next_action, "watch dashboard", 74)
    order_line = _short(order_line, "none submitted", 62)
    body = (
        f"{title}\n"
        f"State: {state}\n"
        f"Reason: {reason}\n"
        f"Next: {next_action}\n"
        f"Order: {order_line}"
    )
    fingerprint_input = {
        "message_class": message_class,
        "state": state,
        "strategy_family": strategy_family,
        "candidate_id": candidate_id,
        "blocker": blocker,
        "next_allowed_action": next_action,
        "order_state": order_line,
        "proof_state": "no proof credit",
    }
    fingerprint = _fingerprint_payload(fingerprint_input)
    candidate_id_hash = _hash_id([message_class, fingerprint], "qsase-telegram-candidate")
    return {
        "schema_version": SCHEMA_VERSION,
        "message_candidate_id": candidate_id_hash,
        "message_class": message_class,
        "status": "message_candidate_created",
        "title": title,
        "body": body,
        "state": state,
        "reason": reason,
        "next_allowed_action": next_action,
        "order_state": order_line,
        "strategy_family": strategy_family,
        "candidate_id": candidate_id,
        "blocker": blocker,
        "proof_state": "no proof credit",
        "fingerprint": fingerprint,
        "fingerprint_input": fingerprint_input,
        "decision_record_ref": decision_record_ref,
        "source_artifact_refs": source_artifact_refs,
        "quality": {},
        "delivery": {},
        "authority": _authority_block(),
        **{key: False for key in FALSE_AUTHORITY_FIELDS},
        "telegram_review_only": True,
    }


def build_qsase_telegram_message_candidates(context: dict[str, Any]) -> list[dict[str, Any]]:
    snapshot = _find_decision(context, "qsase_snapshot")
    paperops = _find_decision(context, "router_paperops")
    learning = _find_decision(context, "learning_ledger")
    repair = _find_decision(context, "repair_queue")
    dashboard = context.get("dashboard_status", {})
    repair_rows = context.get("dashboard_repair_queue", {}).get("rows", [])
    latest_repair = repair_rows[0] if repair_rows else {}
    candidates = [
        _candidate_template(
            message_class="qsase_why_not_trading_now",
            title="Qadam no-trade note",
            state=snapshot.get("state") or dashboard.get("status"),
            reason=snapshot.get("reason") or context.get("strategy_router", {}).get("why_not_trading_now", {}).get("reason"),
            next_action=snapshot.get("next_allowed_action") or "wait for a distinct paperable setup",
            order_line="none submitted",
            strategy_family=snapshot.get("strategy_family") or "aggregate",
            candidate_id=snapshot.get("decision_record_id") or "qsase_snapshot",
            blocker=snapshot.get("blocker") or "none",
            decision_record_ref=_artifact_ref(QSASE_DASHBOARD_DECISION_RECORDS_ARTIFACT, "qsase_snapshot"),
            source_artifact_refs=[
                _artifact_ref(QSASE_DASHBOARD_STATUS_ARTIFACT),
                _artifact_ref(QSASE_STRATEGY_ROUTER_ARTIFACT),
                _artifact_ref(QSASE_PAPEROPS_GATE_ARTIFACT),
            ],
        ),
        _candidate_template(
            message_class="qsase_paperops_gate",
            title="Qadam PaperOps note",
            state=paperops.get("state") or context.get("paperops_gate", {}).get("status"),
            reason=paperops.get("reason") or context.get("paperops_gate", {}).get("top_blocking_gate"),
            next_action=paperops.get("next_allowed_action") or "rerun guarded PaperOps checks",
            order_line="none submitted",
            strategy_family=paperops.get("strategy_family") or "aggregate",
            candidate_id=paperops.get("decision_record_id") or "paperops_gate",
            blocker=paperops.get("blocker") or context.get("paperops_gate", {}).get("top_blocking_gate") or "none",
            decision_record_ref=_artifact_ref(QSASE_DASHBOARD_DECISION_RECORDS_ARTIFACT, "router_paperops"),
            source_artifact_refs=[
                _artifact_ref(QSASE_PAPEROPS_GATE_ARTIFACT),
                _artifact_ref(QSASE_STRATEGY_ROUTER_ARTIFACT),
            ],
        ),
        _candidate_template(
            message_class="qsase_learning_note",
            title="Qadam learning note",
            state=learning.get("state") or context.get("dashboard_learning_ledger", {}).get("status"),
            reason=learning.get("reason") or "learning proposals require review",
            next_action=learning.get("next_allowed_action") or "review proposals before any change",
            order_line="none submitted",
            strategy_family=learning.get("strategy_family") or "aggregate",
            candidate_id=learning.get("decision_record_id") or "learning_ledger",
            blocker=learning.get("blocker") or "approval_required",
            decision_record_ref=_artifact_ref(QSASE_DASHBOARD_DECISION_RECORDS_ARTIFACT, "learning_ledger"),
            source_artifact_refs=[
                _artifact_ref(QSASE_DASHBOARD_LEARNING_LEDGER_ARTIFACT),
                _artifact_ref(QSASE_DASHBOARD_STATUS_ARTIFACT),
            ],
        ),
        _candidate_template(
            message_class="qsase_repair_note",
            title="Qadam repair note",
            state=repair.get("state") or context.get("dashboard_repair_queue", {}).get("status"),
            reason=latest_repair.get("reason") or repair.get("reason") or "repair queue visible",
            next_action=latest_repair.get("next_allowed_action") or repair.get("next_allowed_action") or "repair runtime gap",
            order_line="none submitted",
            strategy_family=repair.get("strategy_family") or "system_repair",
            candidate_id=latest_repair.get("repair_queue_id") or repair.get("decision_record_id") or "repair_queue",
            blocker=latest_repair.get("component") or repair.get("blocker") or "repair_or_review_needed",
            decision_record_ref=_artifact_ref(QSASE_DASHBOARD_DECISION_RECORDS_ARTIFACT, "repair_queue"),
            source_artifact_refs=[
                _artifact_ref(QSASE_DASHBOARD_REPAIR_QUEUE_ARTIFACT),
                _artifact_ref(QSASE_DASHBOARD_STATUS_ARTIFACT),
            ],
        ),
        _candidate_template(
            message_class="qsase_dashboard_visibility",
            title="Qadam dashboard note",
            state=dashboard.get("status"),
            reason=f"{dashboard.get('source_row_count')} sources and {dashboard.get('trade_intent_count')} intents visible",
            next_action="review dashboard decision records",
            order_line="none submitted",
            strategy_family="dashboard_visibility",
            candidate_id="qsase_dashboard_status",
            blocker="none",
            decision_record_ref=_artifact_ref(QSASE_DASHBOARD_DECISION_RECORDS_ARTIFACT, "dashboard_visibility"),
            source_artifact_refs=[
                _artifact_ref(QSASE_DASHBOARD_STATUS_ARTIFACT),
                _artifact_ref(QSASE_DASHBOARD_DECISION_RECORDS_ARTIFACT),
            ],
        ),
    ]
    return candidates


def _lines(body: str) -> list[str]:
    return [line.strip() for line in str(body or "").splitlines() if line.strip()]


def _has_required_lines(body: str) -> dict[str, bool]:
    lines = _lines(body)
    return {
        "state_line": any(line.startswith("State:") and len(line.split(":", 1)[1].strip()) >= 4 for line in lines),
        "reason_line": any(line.startswith("Reason:") and len(line.split(":", 1)[1].strip()) >= 8 for line in lines),
        "next_line": any(line.startswith("Next:") and len(line.split(":", 1)[1].strip()) >= 6 for line in lines),
        "order_or_authority_line": any(
            line.startswith("Order:") or line.startswith("Authority:") or line.startswith("Trading:")
            for line in lines
        ),
    }


def score_qsase_telegram_message(candidate: dict[str, Any]) -> dict[str, Any]:
    body = str(candidate.get("body") or "")
    title = str(candidate.get("title") or "")
    combined = f"{title}\n{body}".lower()
    lines = _lines(body)
    required = _has_required_lines(body)
    generic_hits = [phrase for phrase in GENERIC_PHRASES if phrase in combined]
    unsafe_hits = [pattern.pattern for pattern in UNSAFE_TEXT_PATTERNS if pattern.search(body)]
    score = 20
    score += sum(15 for ok in required.values() if ok)
    if candidate.get("source_artifact_refs"):
        score += 10
    if len(lines) <= 5:
        score += 5
    if len(body) <= 360:
        score += 5
    if candidate.get("strategy_family") and candidate.get("strategy_family") != "not recorded":
        score += 5
    score -= len(generic_hits) * 25
    score -= len(unsafe_hits) * 40
    score = max(0, min(100, score))
    errors: list[str] = []
    for key, ok in required.items():
        if not ok:
            errors.append(f"missing_{key}")
    if not candidate.get("source_artifact_refs"):
        errors.append("missing_artifact_refs")
    if len(body) > 360:
        errors.append("message_too_long")
    if len(lines) > 5:
        errors.append("too_many_lines")
    if generic_hits:
        errors.append("generic_text_present")
    if unsafe_hits:
        errors.append("unsafe_command_or_authority_text")
    specificity_status = "specific" if score >= 80 and not errors else "not_specific"
    human_style_status = "human" if len(lines) <= 5 and len(body) <= 360 and not generic_hits else "not_human_style"
    return {
        "schema_version": SCHEMA_VERSION,
        "specificity_status": specificity_status,
        "specificity_score": score,
        "human_style_status": human_style_status,
        "generic_rejected": bool(generic_hits),
        "unsafe_rejected": bool(unsafe_hits),
        "duplicate_rejected": False,
        "line_count": len(lines),
        "character_count": len(body),
        "required_lines": required,
        "generic_hits": generic_hits,
        "unsafe_hits": unsafe_hits,
        "errors": sorted(set(errors)),
    }


def dedupe_qsase_telegram_message(candidate: dict[str, Any], history: list[dict[str, Any]]) -> dict[str, Any]:
    fingerprint = candidate.get("fingerprint")
    matches = [record for record in history if record.get("fingerprint") == fingerprint]
    return {
        "fingerprint": fingerprint,
        "duplicate": bool(matches),
        "prior_count": len(matches),
        "status": "duplicate_suppressed" if matches else "new_fingerprint",
        "material_change_required_for_repeat": True,
    }


def build_qsase_telegram_delivery_record(candidate: dict[str, Any], delivery_result: dict[str, Any] | None = None) -> dict[str, Any]:
    result = delivery_result or {}
    status = candidate.get("status")
    live_allowed = candidate.get("delivery", {}).get("telegram_live_send_allowed") is True
    attempted = bool(result.get("live_send_attempted", False))
    succeeded = bool(result.get("live_send_succeeded", False))
    return {
        "schema_version": SCHEMA_VERSION,
        "delivery_receipt_id": _hash_id([candidate.get("message_candidate_id"), candidate.get("fingerprint"), status], "qsase-telegram-delivery"),
        "generated_at": _iso(_now()),
        "message_candidate_id": candidate.get("message_candidate_id"),
        "message_class": candidate.get("message_class"),
        "message_status": status,
        "fingerprint": candidate.get("fingerprint"),
        "telegram_live_send_allowed": live_allowed,
        "live_send_attempted": attempted,
        "live_send_succeeded": succeeded,
        "already_sent": status == "message_already_sent",
        "delivery_failure_category": result.get("delivery_failure_category"),
        "strategy_failure": False,
        "paper_order_created": False,
        "broker_write_created": False,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "authority": _authority_block(),
    }


def build_qsase_inbound_readonly_record(inbound_message: dict[str, Any]) -> dict[str, Any]:
    text = str(inbound_message.get("text_excerpt") or inbound_message.get("normalized_summary") or "")
    command_detected = any(pattern.search(text) for pattern in COMMAND_PATTERNS)
    return {
        "schema_version": SCHEMA_VERSION,
        "inbound_record_id": inbound_message.get("intake_id") or _hash_id([text, inbound_message.get("received_at")], "qsase-inbound"),
        "received_at": inbound_message.get("received_at") or inbound_message.get("observed_at"),
        "source_chat_safe_label": inbound_message.get("chat_ref_hash") or "telegram_chat_hash_only",
        "message_fingerprint": inbound_message.get("dedupe_key") or hashlib.sha256(text.lower().encode("utf-8")).hexdigest(),
        "content_class": inbound_message.get("intake_type") or inbound_message.get("content_class") or "unknown",
        "world_event_datapoint_created": bool(inbound_message.get("world_event_datapoint_written", False)),
        "research_analyst_review_queued": bool(inbound_message.get("research_triage_packet_id")),
        "strategy_lead_consideration_created": bool(inbound_message.get("strategy_consideration_written", False)),
        "command_detected": command_detected,
        "command_ignored": command_detected,
        "trade_authority_created": False,
        "trade_candidate_created": False,
        "risk_approval_created": False,
        "execution_approval_created": False,
        "paper_order_created": False,
        "broker_write_created": False,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "authority": _authority_block(),
    }


def validate_qsase_telegram_message_candidate(candidate: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    candidate_id = candidate.get("message_candidate_id", "unknown")
    for field in REQUIRED_CANDIDATE_FIELDS:
        if field not in candidate:
            errors.append(f"candidate_{candidate_id}_missing_{field}")
    if candidate.get("status") not in MESSAGE_STATUSES:
        errors.append(f"candidate_{candidate_id}_status_invalid")
    body = str(candidate.get("body") or "")
    quality = candidate.get("quality", {})
    if len(body) > 360:
        errors.append(f"candidate_{candidate_id}_too_long")
    if len(_lines(body)) > 5:
        errors.append(f"candidate_{candidate_id}_too_many_lines")
    for line_name, present in _has_required_lines(body).items():
        if not present:
            errors.append(f"candidate_{candidate_id}_missing_{line_name}")
    if not candidate.get("source_artifact_refs"):
        errors.append(f"candidate_{candidate_id}_missing_artifact_refs")
    if candidate.get("status") in {"message_ready_for_dashboard_only", "message_ready_to_send"}:
        if quality.get("specificity_status") != "specific":
            errors.append(f"candidate_{candidate_id}_not_specific")
        if quality.get("human_style_status") != "human":
            errors.append(f"candidate_{candidate_id}_not_human_style")
    if quality.get("generic_rejected") and candidate.get("status") != "message_rejected_generic":
        errors.append(f"candidate_{candidate_id}_generic_not_rejected")
    if quality.get("unsafe_rejected") and candidate.get("status") != "message_rejected_unsafe":
        errors.append(f"candidate_{candidate_id}_unsafe_not_rejected")
    delivery = candidate.get("delivery", {})
    if delivery.get("telegram_live_send_allowed") is not False:
        errors.append(f"candidate_{candidate_id}_live_send_allowed_must_be_false")
    if delivery.get("live_send_attempted") is not False or delivery.get("live_send_succeeded") is not False:
        errors.append(f"candidate_{candidate_id}_live_send_attempted_or_succeeded")
    for field in FALSE_AUTHORITY_FIELDS:
        if candidate.get("authority", {}).get(field) is not False:
            errors.append(f"candidate_{candidate_id}_authority_{field}_must_be_false")
        if candidate.get(field) is not False:
            errors.append(f"candidate_{candidate_id}_{field}_must_be_false")
    return sorted(set(errors))


def _apply_quality_dedupe_and_delivery(candidates: list[dict[str, Any]], history: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    processed: list[dict[str, Any]] = []
    dedupe_records: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    in_run_fingerprints: set[str] = set()
    effective_history = list(history)
    for candidate in candidates:
        quality = score_qsase_telegram_message(candidate)
        candidate["quality"] = quality
        dedupe = dedupe_qsase_telegram_message(candidate, effective_history)
        if candidate["fingerprint"] in in_run_fingerprints:
            dedupe["duplicate"] = True
            dedupe["status"] = "duplicate_suppressed"
            dedupe["prior_count"] += 1
        if quality["unsafe_rejected"]:
            status = "message_rejected_unsafe"
        elif quality["generic_rejected"] or quality["specificity_status"] != "specific" or quality["human_style_status"] != "human":
            status = "message_rejected_generic"
        elif dedupe["duplicate"]:
            status = "message_rejected_duplicate"
            quality["duplicate_rejected"] = True
        else:
            status = "message_ready_for_dashboard_only"
        candidate["status"] = status
        candidate["delivery"] = {
            "telegram_live_send_allowed": False,
            "live_send_attempted": False,
            "live_send_succeeded": False,
            "already_sent": False,
            "delivery_failure_category": None,
            "send_state": "dashboard_only_no_live_send" if status == "message_ready_for_dashboard_only" else status,
        }
        dedupe_record = {
            "schema_version": SCHEMA_VERSION,
            "generated_at": _iso(_now()),
            "message_candidate_id": candidate["message_candidate_id"],
            "message_class": candidate["message_class"],
            "fingerprint": candidate["fingerprint"],
            "dedupe_status": dedupe["status"],
            "duplicate_suppressed": status == "message_rejected_duplicate",
            "message_status": status,
            "material_change_required_for_repeat": True,
        }
        receipt = build_qsase_telegram_delivery_record(candidate)
        processed.append(candidate)
        dedupe_records.append(dedupe_record)
        receipts.append(receipt)
        in_run_fingerprints.add(candidate["fingerprint"])
        effective_history.append(dedupe_record)
    return processed, dedupe_records, receipts


def _message_queue(candidates: list[dict[str, Any]], generated_at: str) -> dict[str, Any]:
    queued = [
        {
            "message_candidate_id": candidate["message_candidate_id"],
            "message_class": candidate["message_class"],
            "status": candidate["status"],
            "fingerprint": candidate["fingerprint"],
            "ready_for_dashboard": candidate["status"] == "message_ready_for_dashboard_only",
            "ready_to_send": False,
            "send_allowed": False,
            "artifact_refs": candidate["source_artifact_refs"],
        }
        for candidate in candidates
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_telegram_message_queue",
        "generated_at": generated_at,
        "status": "dashboard_only_queue_recorded",
        "queue_count": len(queued),
        "ready_to_send_count": 0,
        "queued_messages": queued,
        "telegram_live_send_allowed": False,
        "authority": _authority_block(),
    }


def _message_quality_summary(candidates: list[dict[str, Any]], generated_at: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_telegram_message_quality",
        "generated_at": generated_at,
        "status": "message_quality_passed"
        if all(candidate.get("quality", {}).get("specificity_status") == "specific" for candidate in candidates)
        else "message_quality_degraded",
        "candidate_count": len(candidates),
        "specific_count": sum(1 for candidate in candidates if candidate.get("quality", {}).get("specificity_status") == "specific"),
        "human_style_count": sum(1 for candidate in candidates if candidate.get("quality", {}).get("human_style_status") == "human"),
        "generic_rejected_count": sum(1 for candidate in candidates if candidate.get("status") == "message_rejected_generic"),
        "unsafe_rejected_count": sum(1 for candidate in candidates if candidate.get("status") == "message_rejected_unsafe"),
        "quality_rows": [
            {
                "message_candidate_id": candidate["message_candidate_id"],
                "message_class": candidate["message_class"],
                "status": candidate["status"],
                "specificity_status": candidate.get("quality", {}).get("specificity_status"),
                "specificity_score": candidate.get("quality", {}).get("specificity_score"),
                "human_style_status": candidate.get("quality", {}).get("human_style_status"),
                "generic_rejected": candidate.get("quality", {}).get("generic_rejected"),
                "unsafe_rejected": candidate.get("quality", {}).get("unsafe_rejected"),
                "duplicate_rejected": candidate.get("quality", {}).get("duplicate_rejected"),
            }
            for candidate in candidates
        ],
        "authority": _authority_block(),
    }


def _inbound_readonly_summary(context: dict[str, Any], generated_at: str) -> dict[str, Any]:
    records = [build_qsase_inbound_readonly_record(record) for record in context.get("inbound_records", [])]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_telegram_inbound_readonly_intake",
        "generated_at": generated_at,
        "status": "inbound_readonly_intake_recorded",
        "record_count": len(records),
        "command_detected_count": sum(1 for record in records if record.get("command_detected")),
        "command_ignored_count": sum(1 for record in records if record.get("command_ignored")),
        "world_event_datapoint_count": sum(1 for record in records if record.get("world_event_datapoint_created")),
        "strategy_consideration_count": sum(1 for record in records if record.get("strategy_lead_consideration_created")),
        "records": records,
        "trade_candidate_created": False,
        "risk_approval_created": False,
        "execution_approval_created": False,
        "paper_order_created": False,
        "broker_write_created": False,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "authority": _authority_block(),
    }


def _dashboard_communications_mirror(
    candidates: list[dict[str, Any]],
    receipts: list[dict[str, Any]],
    inbound: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    latest = candidates[0] if candidates else {}
    latest_receipt = receipts[0] if receipts else {}
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_telegram_dashboard_communications_mirror",
        "generated_at": generated_at,
        "status": "dashboard_communications_mirror_ready",
        "public_safe": True,
        "command_disabled": True,
        "latest_message_class": latest.get("message_class"),
        "latest_message_status": latest.get("status"),
        "latest_message_preview": latest.get("body"),
        "telegram_live_send_allowed": False,
        "send_attempted": latest_receipt.get("live_send_attempted", False),
        "send_succeeded": latest_receipt.get("live_send_succeeded", False),
        "failure_category": latest_receipt.get("delivery_failure_category"),
        "duplicate_suppression_count": sum(1 for candidate in candidates if candidate.get("status") == "message_rejected_duplicate"),
        "rejected_generic_count": sum(1 for candidate in candidates if candidate.get("status") == "message_rejected_generic"),
        "inbound_record_count": inbound.get("record_count", 0),
        "inbound_command_ignored_count": inbound.get("command_ignored_count", 0),
        "authority_boundary": "Telegram review-only: no commands, orders, approvals, broker writes, proof credit, or live capital.",
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "authority": _authority_block(),
    }


def build_qsase_telegram_notification_boundary(settings: Settings | None = None) -> dict[str, Any]:
    context = _load_context(settings)
    generated_at = _iso(_now())
    raw_candidates = build_qsase_telegram_message_candidates(context)
    candidates, dedupe_records, receipts = _apply_quality_dedupe_and_delivery(raw_candidates, context.get("dedupe_history", []))
    inbound = _inbound_readonly_summary(context, generated_at)
    queue = _message_queue(candidates, generated_at)
    quality = _message_quality_summary(candidates, generated_at)
    communications = _dashboard_communications_mirror(candidates, receipts, inbound, generated_at)
    status_counts = Counter(candidate["status"] for candidate in candidates)
    status = "qsase_telegram_notification_boundary_ready"
    if status_counts.get("message_rejected_unsafe"):
        status = "qsase_telegram_notification_boundary_blocked"
    elif status_counts.get("message_rejected_generic") or status_counts.get("message_rejected_duplicate"):
        status = "qsase_telegram_notification_boundary_degraded"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_telegram_notification_boundary",
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "generated_at": generated_at,
        "status": status,
        "public_safe": True,
        "command_disabled": True,
        "review_only": True,
        "paper_only": True,
        "message_candidate_count": len(candidates),
        "message_ready_count": status_counts.get("message_ready_for_dashboard_only", 0) + status_counts.get("message_ready_to_send", 0),
        "message_sent_count": status_counts.get("message_sent", 0),
        "message_rejected_generic_count": status_counts.get("message_rejected_generic", 0),
        "message_rejected_duplicate_count": status_counts.get("message_rejected_duplicate", 0),
        "message_rejected_unsafe_count": status_counts.get("message_rejected_unsafe", 0),
        "delivery_failure_count": sum(1 for receipt in receipts if receipt.get("message_status") == "message_delivery_failed"),
        "duplicate_suppressed_count": status_counts.get("message_rejected_duplicate", 0),
        "inbound_record_count": inbound["record_count"],
        "inbound_command_detected_count": inbound["command_detected_count"],
        "inbound_command_ignored_count": inbound["command_ignored_count"],
        "telegram_live_send_allowed": False,
        "telegram_command_path_enabled": False,
        "telegram_trade_command_enabled": False,
        "trade_candidate_created": False,
        "qualified_setup_created": False,
        "risk_approval_created": False,
        "execution_approval_created": False,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_allowed": False,
        "paper_proof_ledger_credit_allowed": False,
        "live_capital_enabled": False,
        "message_candidates": candidates,
        "message_queue": queue,
        "message_quality": quality,
        "dedupe_records": dedupe_records,
        "delivery_receipts": receipts,
        "inbound_readonly_intake": inbound,
        "dashboard_communications_mirror": communications,
        "artifact_refs": {
            "message_candidates": _artifact_ref(MESSAGE_CANDIDATES_ARTIFACT),
            "message_queue": _artifact_ref(MESSAGE_QUEUE_ARTIFACT),
            "message_quality": _artifact_ref(MESSAGE_QUALITY_ARTIFACT),
            "dedupe_ledger": _artifact_ref(DEDUPE_LEDGER_ARTIFACT),
            "delivery_receipts": _artifact_ref(DELIVERY_RECEIPTS_ARTIFACT),
            "inbound_readonly_intake": _artifact_ref(INBOUND_READONLY_ARTIFACT),
            "dashboard_communications_mirror": _artifact_ref(DASHBOARD_COMMUNICATIONS_ARTIFACT),
        },
        "authority": universal_authority_flags(),
        "authority_flags": _authority_block(),
    }
    return payload


def load_qsase_telegram_notification_boundary(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    payload = _read_json(runtime / PRIMARY_ARTIFACT)
    if payload:
        payload["message_candidates"] = _read_json(runtime / MESSAGE_CANDIDATES_ARTIFACT).get("candidates", [])
        payload["message_queue"] = _read_json(runtime / MESSAGE_QUEUE_ARTIFACT)
        payload["message_quality"] = _read_json(runtime / MESSAGE_QUALITY_ARTIFACT)
        payload["dedupe_records"] = _read_jsonl(runtime / DEDUPE_LEDGER_ARTIFACT, limit=500)
        payload["delivery_receipts"] = _read_jsonl(runtime / DELIVERY_RECEIPTS_ARTIFACT, limit=500)
        payload["inbound_readonly_intake"] = _read_json(runtime / INBOUND_READONLY_ARTIFACT)
        payload["dashboard_communications_mirror"] = _read_json(runtime / DASHBOARD_COMMUNICATIONS_ARTIFACT)
    return payload


def validate_qsase_telegram_notification_boundary(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("artifact_type") != "qsase_telegram_notification_boundary":
        errors.append("artifact_type_invalid")
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if payload.get("status") not in {
        "qsase_telegram_notification_boundary_ready",
        "qsase_telegram_notification_boundary_degraded",
        "qsase_telegram_notification_boundary_blocked",
    }:
        errors.append("status_invalid")
    for key in ("public_safe", "command_disabled", "review_only", "paper_only"):
        if payload.get(key) is not True:
            errors.append(f"{key}_must_be_true")
    for key in (
        "telegram_live_send_allowed",
        "telegram_command_path_enabled",
        "telegram_trade_command_enabled",
        "trade_candidate_created",
        "qualified_setup_created",
        "risk_approval_created",
        "execution_approval_created",
        "proof_credit_allowed",
        "paper_proof_ledger_credit_allowed",
        "live_capital_enabled",
    ):
        if payload.get(key) is not False:
            errors.append(f"{key}_must_be_false")
    for key in ("message_sent_count", "paper_order_created_count", "broker_write_count"):
        if int(payload.get(key, -1) or 0) != 0:
            errors.append(f"{key}_must_be_zero")
    if payload.get("inbound_command_detected_count") != payload.get("inbound_command_ignored_count"):
        errors.append("inbound_commands_must_be_ignored")
    if any(value is not False for value in payload.get("authority", {}).values()):
        errors.append("universal_authority_flags_must_all_be_false")
    for field in FALSE_AUTHORITY_FIELDS:
        if payload.get("authority_flags", {}).get(field) is not False:
            errors.append(f"authority_{field}_must_be_false")
    candidates = payload.get("message_candidates")
    if not isinstance(candidates, list):
        errors.append("message_candidates_missing")
        candidates = []
    if payload.get("message_candidate_count") != len(candidates):
        errors.append("message_candidate_count_mismatch")
    for candidate in candidates:
        errors.extend(validate_qsase_telegram_message_candidate(candidate))
    quality = payload.get("message_quality", {})
    if quality.get("candidate_count") != len(candidates):
        errors.append("message_quality_candidate_count_mismatch")
    if quality.get("generic_rejected_count") != payload.get("message_rejected_generic_count"):
        errors.append("generic_rejected_count_mismatch")
    if quality.get("unsafe_rejected_count") != payload.get("message_rejected_unsafe_count"):
        errors.append("unsafe_rejected_count_mismatch")
    queue = payload.get("message_queue", {})
    if queue.get("ready_to_send_count") != 0:
        errors.append("message_queue_ready_to_send_must_be_zero")
    if queue.get("telegram_live_send_allowed") is not False:
        errors.append("message_queue_live_send_must_be_false")
    inbound = payload.get("inbound_readonly_intake", {})
    for field in (
        "trade_candidate_created",
        "risk_approval_created",
        "execution_approval_created",
        "paper_order_created",
        "broker_write_created",
        "proof_credit_allowed",
        "live_capital_enabled",
    ):
        if inbound.get(field) is not False:
            errors.append(f"inbound_{field}_must_be_false")
    for record in inbound.get("records", []):
        if record.get("command_detected") is True and record.get("command_ignored") is not True:
            errors.append(f"inbound_record_{record.get('inbound_record_id')}_command_not_ignored")
        for field in (
            "trade_authority_created",
            "trade_candidate_created",
            "risk_approval_created",
            "execution_approval_created",
            "paper_order_created",
            "broker_write_created",
            "proof_credit_allowed",
            "live_capital_enabled",
        ):
            if record.get(field) is not False:
                errors.append(f"inbound_record_{record.get('inbound_record_id')}_{field}_must_be_false")
    communications = payload.get("dashboard_communications_mirror", {})
    if communications.get("status") != "dashboard_communications_mirror_ready":
        errors.append("dashboard_communications_mirror_missing")
    if communications.get("command_disabled") is not True or communications.get("public_safe") is not True:
        errors.append("dashboard_communications_mirror_boundary_missing")
    if communications.get("telegram_live_send_allowed") is not False:
        errors.append("dashboard_communications_mirror_live_send_must_be_false")
    for field in FALSE_AUTHORITY_FIELDS:
        if communications.get("authority", {}).get(field) is not False:
            errors.append(f"dashboard_communications_authority_{field}_must_be_false")
    return sorted(set(errors))


def _summary_without_records(payload: dict[str, Any]) -> dict[str, Any]:
    summary = dict(payload)
    for key in (
        "message_candidates",
        "dedupe_records",
        "delivery_receipts",
        "message_queue",
        "message_quality",
        "inbound_readonly_intake",
        "dashboard_communications_mirror",
    ):
        summary.pop(key, None)
    return summary


def build_qsase_phase_implementation_status(payload: dict[str, Any]) -> dict[str, Any]:
    runtime_dir = _runtime_dir()
    existing = _read_json(runtime_dir / PHASE_STATUS_ARTIFACT)
    phases = existing.get("phases") if isinstance(existing.get("phases"), dict) else {}
    phases[PHASE_ID] = {
        "name": PHASE_NAME,
        "status": payload["status"],
        "artifact_path": f"data/runtime/{PRIMARY_ARTIFACT}",
        "message_candidates_path": f"data/runtime/{MESSAGE_CANDIDATES_ARTIFACT}",
        "message_quality_path": f"data/runtime/{MESSAGE_QUALITY_ARTIFACT}",
        "dedupe_ledger_path": f"data/runtime/{DEDUPE_LEDGER_ARTIFACT}",
        "delivery_receipts_path": f"data/runtime/{DELIVERY_RECEIPTS_ARTIFACT}",
        "dashboard_communications_mirror_path": f"data/runtime/{DASHBOARD_COMMUNICATIONS_ARTIFACT}",
        "message_candidate_count": payload["message_candidate_count"],
        "message_ready_count": payload["message_ready_count"],
        "message_rejected_duplicate_count": payload["message_rejected_duplicate_count"],
        "message_rejected_generic_count": payload["message_rejected_generic_count"],
        "message_rejected_unsafe_count": payload["message_rejected_unsafe_count"],
        "inbound_record_count": payload["inbound_record_count"],
        "inbound_command_ignored_count": payload["inbound_command_ignored_count"],
        "paper_only": True,
        "review_only": True,
        "public_safe": True,
        "command_disabled": True,
        "no_commands_created": True,
        "no_orders_created": True,
        "no_broker_writes": True,
        "no_proof_credit_granted": True,
        "later_qsase_phases_implemented": False,
    }
    return {
        "schema_version": 1,
        "generated_at": payload["generated_at"],
        "active_phase": PHASE_ID,
        "phases": phases,
        "safety": payload["authority"],
    }


def _append_implementation_log(payload: dict[str, Any]) -> None:
    log_path = _repo_root() / IMPLEMENTATION_LOG
    log_path.parent.mkdir(parents=True, exist_ok=True)
    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else "# QSASE Implementation Log\n"
    marker = f"<!-- {PHASE_ID} -->"
    entry = (
        f"{marker}\n"
        f"## QSASE-14: Telegram Summary Boundary\n\n"
        f"- Generated at: `{payload.get('generated_at')}`\n"
        f"- Status: `{payload.get('status')}`\n"
        f"- Runtime artifact: `data/runtime/{PRIMARY_ARTIFACT}`\n"
        f"- Candidates ready / duplicate / generic / unsafe: `{payload.get('message_ready_count')}` / `{payload.get('message_rejected_duplicate_count')}` / `{payload.get('message_rejected_generic_count')}` / `{payload.get('message_rejected_unsafe_count')}`\n"
        f"- Inbound records / commands ignored: `{payload.get('inbound_record_count')}` / `{payload.get('inbound_command_ignored_count')}`\n"
        f"- Delivery failures / sent: `{payload.get('delivery_failure_count')}` / `{payload.get('message_sent_count')}`\n"
        f"- Safety: Telegram candidates are dashboard-visible, review-only, command-disabled, deduped, and unable to create candidates, approvals, paper orders, broker writes, live capital, or paper proof ledger credit.\n"
    )
    if marker in existing:
        before = existing.split(marker, 1)[0].rstrip()
        updated = before + "\n\n" + entry
    elif existing.endswith("\n"):
        updated = existing + "\n" + entry
    else:
        updated = existing + "\n\n" + entry
    log_path.write_text(updated, encoding="utf-8")


def write_qsase_telegram_notification_boundary(
    payload: dict[str, Any],
    settings: Settings | None = None,
    *,
    append_history: bool = True,
    append_log: bool = True,
) -> dict[str, str]:
    runtime = _runtime_dir(settings)
    runtime.mkdir(parents=True, exist_ok=True)
    paths = {
        "notification_boundary": runtime / PRIMARY_ARTIFACT,
        "message_candidates": runtime / MESSAGE_CANDIDATES_ARTIFACT,
        "message_queue": runtime / MESSAGE_QUEUE_ARTIFACT,
        "message_quality": runtime / MESSAGE_QUALITY_ARTIFACT,
        "inbound_readonly": runtime / INBOUND_READONLY_ARTIFACT,
        "dashboard_communications": runtime / DASHBOARD_COMMUNICATIONS_ARTIFACT,
        "phase_status": runtime / PHASE_STATUS_ARTIFACT,
    }
    _write_json(paths["notification_boundary"], _summary_without_records(payload))
    _write_json(
        paths["message_candidates"],
        {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qsase_telegram_message_candidates",
            "generated_at": payload["generated_at"],
            "status": "message_candidates_recorded",
            "candidate_count": len(payload["message_candidates"]),
            "candidates": payload["message_candidates"],
            "authority": _authority_block(),
        },
    )
    _write_json(paths["message_queue"], payload["message_queue"])
    _write_json(paths["message_quality"], payload["message_quality"])
    _write_json(paths["inbound_readonly"], payload["inbound_readonly_intake"])
    _write_json(paths["dashboard_communications"], payload["dashboard_communications_mirror"])
    _write_json(paths["phase_status"], build_qsase_phase_implementation_status(payload))
    written = {key: str(path) for key, path in paths.items()}
    if append_history:
        for record in payload["dedupe_records"]:
            _append_jsonl(runtime / DEDUPE_LEDGER_ARTIFACT, record)
        for receipt in payload["delivery_receipts"]:
            _append_jsonl(runtime / DELIVERY_RECEIPTS_ARTIFACT, receipt)
        _append_jsonl(
            runtime / NOTIFICATION_HISTORY_ARTIFACT,
            {
                "generated_at": payload["generated_at"],
                "status": payload["status"],
                "message_candidate_count": payload["message_candidate_count"],
                "message_ready_count": payload["message_ready_count"],
                "message_rejected_duplicate_count": payload["message_rejected_duplicate_count"],
                "message_rejected_generic_count": payload["message_rejected_generic_count"],
                "delivery_failure_count": payload["delivery_failure_count"],
                "message_sent_count": payload["message_sent_count"],
                "no_authority_created": True,
            },
        )
        _append_jsonl(
            runtime / EVENTS_ARTIFACT,
            {
                "generated_at": payload["generated_at"],
                "event_type": "qsase_telegram_notification_boundary_written",
                "status": payload["status"],
                "review_only": True,
                "command_disabled": True,
                "no_authority_created": True,
            },
        )
        written["dedupe_ledger"] = str(runtime / DEDUPE_LEDGER_ARTIFACT)
        written["delivery_receipts"] = str(runtime / DELIVERY_RECEIPTS_ARTIFACT)
        written["notification_history"] = str(runtime / NOTIFICATION_HISTORY_ARTIFACT)
        written["events"] = str(runtime / EVENTS_ARTIFACT)
    if append_log:
        _append_implementation_log(payload)
        written["implementation_log"] = str(_repo_root() / IMPLEMENTATION_LOG)
    return written


def build_and_write_qsase_telegram_notification_boundary(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    payload = build_qsase_telegram_notification_boundary(settings)
    errors = validate_qsase_telegram_notification_boundary(payload)
    written = write_qsase_telegram_notification_boundary(payload, settings)
    return payload, written, errors


def validate_negative_qsase_telegram_notification_boundary_probes() -> list[str]:
    base = build_qsase_telegram_notification_boundary()
    errors: list[str] = []
    if base["message_candidates"]:
        generic_probe = copy.deepcopy(base)
        generic_probe["message_candidates"][0]["body"] = "Qadam Codebase Upgrade\nWhat changed:\nWhy it matters:\nWhat to check:"
        generic_probe["message_candidates"][0]["quality"] = score_qsase_telegram_message(generic_probe["message_candidates"][0])
        generic_probe["message_candidates"][0]["status"] = "message_ready_for_dashboard_only"
        if not any("generic" in error for error in validate_qsase_telegram_notification_boundary(generic_probe)):
            errors.append("negative_probe_failed_for_generic_message")
        command_probe = copy.deepcopy(base)
        command_probe["message_candidates"][0]["body"] = "/buy SMH\nState: command\nReason: operator asked\nNext: submit\nOrder: buy SMH"
        command_probe["message_candidates"][0]["quality"] = score_qsase_telegram_message(command_probe["message_candidates"][0])
        command_probe["message_candidates"][0]["status"] = "message_ready_for_dashboard_only"
        if not any("unsafe" in error or "must_be_false" in error for error in validate_qsase_telegram_notification_boundary(command_probe)):
            errors.append("negative_probe_failed_for_command_message")
        live_probe = copy.deepcopy(base)
        live_probe["message_candidates"][0]["delivery"]["telegram_live_send_allowed"] = True
        if not any("live_send_allowed" in error for error in validate_qsase_telegram_notification_boundary(live_probe)):
            errors.append("negative_probe_failed_for_live_send")
    command_inbound = build_qsase_inbound_readonly_record({"text_excerpt": "/buy SMH", "received_at": _iso(_now())})
    if command_inbound["command_detected"] is not True or command_inbound["command_ignored"] is not True:
        errors.append("negative_probe_failed_for_inbound_command_ignore")
    proof_probe = copy.deepcopy(base)
    proof_probe["proof_credit_allowed"] = True
    if not any("proof_credit_allowed" in error for error in validate_qsase_telegram_notification_boundary(proof_probe)):
        errors.append("negative_probe_failed_for_proof_credit")
    return errors


if __name__ == "__main__":
    artifact = build_qsase_telegram_notification_boundary()
    print(_json_dump(_summary_without_records(artifact)))
