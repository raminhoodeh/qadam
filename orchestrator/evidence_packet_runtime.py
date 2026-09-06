"""Durable local runtime for normalized evidence packets.

The runtime is intentionally local and read-only from a trading perspective. It
persists the normalized evidence packet surface into JSON/JSONL so Qadam can
replay what the dashboard showed without treating evidence as source quorum,
risk approval, order authority, broker writes, quantum authority, performance
credit, or live capital.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from orchestrator.config import Settings
from orchestrator.event_log import EventLog
from orchestrator.evidence_packet_normalization import (
    EVIDENCE_PACKET_NORMALIZATION_VERSION,
    validate_normalized_evidence_packet,
)

EVIDENCE_PACKET_RUNTIME_SCHEMA_VERSION = 1
EVIDENCE_PACKET_RUNTIME_VERSION = "epr_2026_06_14"
EVIDENCE_PACKET_RUNTIME_ARTIFACT = "evidence_packet_runtime.json"
EVIDENCE_PACKET_RUNTIME_HISTORY = "evidence_packet_runtime_history.jsonl"
EVIDENCE_PACKET_RUNTIME_EVENTS = "evidence_packet_runtime_events.jsonl"
EVIDENCE_PACKET_RUNTIME_BOUNDARY = (
    "Durable evidence packet runtime is replay-only. It can persist normalized "
    "public-safe evidence packets, but it cannot create source quorum, trade "
    "ideas, risk approval, orders, broker writes, quantum jobs, performance "
    "credit, or live capital."
)

AUTHORITY_FALSE_FIELDS: tuple[str, ...] = (
    "source_quorum_credit_allowed",
    "risk_handoff_allowed",
    "trade_candidate_creation_allowed",
    "execution_allowed",
    "paper_order_allowed",
    "broker_write_allowed",
    "performance_credit_allowed",
    "quantum_job_authority",
    "live_capital_enabled",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir(settings: Settings | None = None) -> Path:
    return Path((settings or Settings.from_env()).runtime_dir)


def evidence_packet_runtime_paths(
    settings: Settings | None = None,
) -> tuple[Path, Path, Path]:
    runtime = _runtime_dir(settings)
    return (
        runtime / EVIDENCE_PACKET_RUNTIME_ARTIFACT,
        runtime / EVIDENCE_PACKET_RUNTIME_HISTORY,
        runtime / EVIDENCE_PACKET_RUNTIME_EVENTS,
    )


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temp_path.replace(path)


def _packet_authority_leak_count(packet: dict[str, Any]) -> int:
    return sum(1 for field in AUTHORITY_FALSE_FIELDS if packet.get(field) is not False)


def _item_authority_leak_count(packet: dict[str, Any]) -> int:
    return sum(
        1
        for item in packet.get("items", [])
        if isinstance(item, dict)
        for field in (
            "source_quorum_credit_allowed",
            "trade_candidate_creation_allowed",
            "execution_allowed",
            "paper_order_allowed",
            "broker_write_allowed",
            "live_capital_enabled",
        )
        if item.get(field) is not False
    )


def _raw_ref_leak_count(packet: dict[str, Any]) -> int:
    return sum(
        1
        for item in packet.get("items", [])
        if isinstance(item, dict) and "raw_ref" in item
    )


def _history_line_count(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    except OSError:
        return 0


def build_evidence_packet_runtime(
    packets: Iterable[dict[str, Any]],
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    packet_list = [packet for packet in packets if isinstance(packet, dict)]
    validation_errors = [
        f"{packet.get('packet_id', packet.get('trail_id', 'unknown'))}:{error}"
        for packet in packet_list
        for error in validate_normalized_evidence_packet(packet)
    ]
    authority_leak_count = sum(
        _packet_authority_leak_count(packet) + _item_authority_leak_count(packet)
        for packet in packet_list
    )
    raw_ref_leak_count = sum(_raw_ref_leak_count(packet) for packet in packet_list)
    packet_ids = [
        str(packet.get("packet_id") or packet.get("trail_id") or "")
        for packet in packet_list
        if packet.get("packet_id") or packet.get("trail_id")
    ]
    sources = sorted(
        {
            str(source)
            for packet in packet_list
            for source in packet.get("sources", [])
            if source
        }
    )
    packet_types = sorted(
        {
            str(packet.get("packet_type") or "unknown")
            for packet in packet_list
            if packet.get("packet_type")
        }
    )
    created_values = [
        str(packet.get("created_at"))
        for packet in packet_list
        if packet.get("created_at")
    ]
    status = "ok" if not validation_errors and not authority_leak_count and not raw_ref_leak_count else "degraded"
    return {
        "schema_version": EVIDENCE_PACKET_RUNTIME_SCHEMA_VERSION,
        "runtime_version": EVIDENCE_PACKET_RUNTIME_VERSION,
        "normalization_version": EVIDENCE_PACKET_NORMALIZATION_VERSION,
        "status": status,
        "replay_status": "local_jsonl_replay_ready" if status == "ok" else "local_jsonl_replay_degraded",
        "contract_status": "durable_evidence_packet_runtime_ready"
        if status == "ok"
        else "durable_evidence_packet_runtime_degraded",
        "storage_backend": "local_jsonl",
        "generated_at": generated_at or _now(),
        "packet_count": len(packet_list),
        "item_count": sum(len(packet.get("items", [])) for packet in packet_list),
        "source_count": len(sources),
        "sources": sources[:24],
        "packet_types": packet_types,
        "packet_ids": packet_ids[:24],
        "latest_packet_created_at": max(created_values) if created_values else None,
        "validation_error_count": len(validation_errors),
        "validation_errors": validation_errors[:20],
        "authority_leak_count": authority_leak_count,
        "raw_ref_leak_count": raw_ref_leak_count,
        "write_authority": False,
        "signal_authority": False,
        "risk_handoff_allowed": False,
        "trade_candidate_creation_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "quantum_job_authority": False,
        "performance_credit_allowed": False,
        "live_capital_enabled": False,
        "public_safe": True,
        "packets": packet_list,
        "boundary": EVIDENCE_PACKET_RUNTIME_BOUNDARY,
    }


def write_evidence_packet_runtime(
    packets: Iterable[dict[str, Any]],
    *,
    settings: Settings | None = None,
    generated_at: str | None = None,
    record_event: bool = True,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    artifact_path, history_path, event_path = evidence_packet_runtime_paths(settings)
    artifact = build_evidence_packet_runtime(packets, generated_at=generated_at)
    artifact["snapshot_written"] = False
    artifact["history_appended"] = False
    artifact["history_record_count"] = _history_line_count(history_path)
    artifact["event_log_written"] = False
    artifact["event_log_event_count"] = 0
    artifact["event_log_correlation_id"] = None
    artifact["event_log_created_at"] = None

    _atomic_write_json(artifact_path, artifact)
    artifact["snapshot_written"] = True
    artifact["artifact"] = EVIDENCE_PACKET_RUNTIME_ARTIFACT

    from orchestrator.qadam_operator_ready_common import append_jsonl_durable
    append_jsonl_durable(history_path, artifact)
    artifact["history_appended"] = True
    artifact["history"] = EVIDENCE_PACKET_RUNTIME_HISTORY
    artifact["history_record_count"] = _history_line_count(history_path)

    if record_event:
        event_log = EventLog(event_path, echo=False)
        event = event_log.write(
            "evidence_packet_runtime_snapshot_recorded",
            "evidence_packet_runtime",
            {
                "runtime_version": artifact["runtime_version"],
                "status": artifact["status"],
                "packet_count": artifact["packet_count"],
                "item_count": artifact["item_count"],
                "authority_leak_count": artifact["authority_leak_count"],
                "raw_ref_leak_count": artifact["raw_ref_leak_count"],
                "public_safe": True,
            },
        )
        artifact["event_log_written"] = True
        artifact["event_log"] = EVIDENCE_PACKET_RUNTIME_EVENTS
        artifact["event_log_event_count"] = 1
        artifact["event_log_correlation_id"] = event.correlation_id
        artifact["event_log_created_at"] = event.created_at
        _atomic_write_json(artifact_path, artifact)

    return artifact


def read_evidence_packet_runtime(settings: Settings | None = None) -> dict[str, Any]:
    artifact_path, _, _ = evidence_packet_runtime_paths(settings)
    if not artifact_path.exists():
        return {
            "schema_version": EVIDENCE_PACKET_RUNTIME_SCHEMA_VERSION,
            "runtime_version": EVIDENCE_PACKET_RUNTIME_VERSION,
            "normalization_version": EVIDENCE_PACKET_NORMALIZATION_VERSION,
            "status": "not_initialized",
            "replay_status": "not_initialized",
            "contract_status": "durable_evidence_packet_runtime_not_initialized",
            "storage_backend": "local_jsonl",
            "packet_count": 0,
            "item_count": 0,
            "source_count": 0,
            "validation_error_count": 0,
            "authority_leak_count": 0,
            "raw_ref_leak_count": 0,
            "write_authority": False,
            "signal_authority": False,
            "risk_handoff_allowed": False,
            "trade_candidate_creation_allowed": False,
            "execution_allowed": False,
            "paper_order_allowed": False,
            "broker_write_allowed": False,
            "quantum_job_authority": False,
            "performance_credit_allowed": False,
            "live_capital_enabled": False,
            "public_safe": True,
            "boundary": EVIDENCE_PACKET_RUNTIME_BOUNDARY,
        }
    try:
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "schema_version": EVIDENCE_PACKET_RUNTIME_SCHEMA_VERSION,
            "runtime_version": EVIDENCE_PACKET_RUNTIME_VERSION,
            "normalization_version": EVIDENCE_PACKET_NORMALIZATION_VERSION,
            "status": "degraded",
            "replay_status": "local_jsonl_replay_failed",
            "contract_status": "durable_evidence_packet_runtime_unreadable",
            "storage_backend": "local_jsonl",
            "packet_count": 0,
            "item_count": 0,
            "source_count": 0,
            "validation_error_count": 1,
            "authority_leak_count": 0,
            "raw_ref_leak_count": 0,
            "write_authority": False,
            "signal_authority": False,
            "risk_handoff_allowed": False,
            "trade_candidate_creation_allowed": False,
            "execution_allowed": False,
            "paper_order_allowed": False,
            "broker_write_allowed": False,
            "quantum_job_authority": False,
            "performance_credit_allowed": False,
            "live_capital_enabled": False,
            "public_safe": True,
            "boundary": EVIDENCE_PACKET_RUNTIME_BOUNDARY,
        }
    return payload if isinstance(payload, dict) else {}


def evidence_packet_runtime_public_status(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": int(artifact.get("schema_version", EVIDENCE_PACKET_RUNTIME_SCHEMA_VERSION) or 1),
        "runtime_version": str(artifact.get("runtime_version") or EVIDENCE_PACKET_RUNTIME_VERSION),
        "normalization_version": str(
            artifact.get("normalization_version") or EVIDENCE_PACKET_NORMALIZATION_VERSION
        ),
        "status": str(artifact.get("status") or "unknown"),
        "replay_status": str(artifact.get("replay_status") or "unknown"),
        "contract_status": str(artifact.get("contract_status") or "unknown"),
        "storage_backend": str(artifact.get("storage_backend") or "local_jsonl"),
        "generated_at": artifact.get("generated_at"),
        "packet_count": int(artifact.get("packet_count", 0) or 0),
        "item_count": int(artifact.get("item_count", 0) or 0),
        "source_count": int(artifact.get("source_count", 0) or 0),
        "packet_types": list(artifact.get("packet_types", []))[:12],
        "latest_packet_created_at": artifact.get("latest_packet_created_at"),
        "validation_error_count": int(artifact.get("validation_error_count", 0) or 0),
        "authority_leak_count": int(artifact.get("authority_leak_count", 0) or 0),
        "raw_ref_leak_count": int(artifact.get("raw_ref_leak_count", 0) or 0),
        "snapshot_written": bool(artifact.get("snapshot_written")),
        "history_appended": bool(artifact.get("history_appended")),
        "history_record_count": int(artifact.get("history_record_count", 0) or 0),
        "event_log_written": bool(artifact.get("event_log_written")),
        "event_log_event_count": int(artifact.get("event_log_event_count", 0) or 0),
        "write_authority": False,
        "signal_authority": False,
        "risk_handoff_allowed": False,
        "trade_candidate_creation_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "broker_write_allowed": False,
        "quantum_job_authority": False,
        "performance_credit_allowed": False,
        "live_capital_enabled": False,
        "public_safe": True,
        "boundary": EVIDENCE_PACKET_RUNTIME_BOUNDARY,
    }
