"""Import current read-only PaperOps lifecycle facts into the durable store."""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_control_plane_store import ControlPlaneStore
from orchestrator.qadam_operator_ready_common import now_iso, read_json, runtime_dir, write_json_atomic

SCHEMA_VERSION = "qadam_lifecycle_control_plane.v1"
CHECK_ARTIFACT = "qadam_lifecycle_control_plane_checks.json"


def _stable(prefix: str, payload: dict[str, Any]) -> str:
    material = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return f"{prefix}:{sha256(material.encode('utf-8')).hexdigest()[:24]}"


def _state(record: dict[str, Any]) -> str:
    raw = str(record.get("lifecycle_state") or record.get("broker_order_status") or "")
    mapping = {
        "new": "accepted",
        "accepted": "accepted",
        "submitted": "submitted",
        "partially_filled": "partial_fill",
        "partial_fill": "partial_fill",
        "filled": "filled",
        "open_position": "open",
        "filled_without_open_position_echo": "filled",
        "cancelled": "cancelled",
        "canceled": "cancelled",
        "rejected": "rejected",
        "expired": "expired",
        "closed": "closed",
        "position_closed": "closed",
        "postmortem_complete": "postmortem_complete",
    }
    return mapping.get(raw, "filled" if record.get("filled_at") else "submitted")


def sync_lifecycle_control_plane(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    source = read_json(runtime / "paperops_paper_lifecycle_poller.json")
    store = ControlPlaneStore.from_settings(settings)
    known_handoffs = {str(row["handoff_id"]) for row in store.read_table("handoffs")}
    inserted = 0
    missing_lineage = 0
    errors: list[str] = []
    records = source.get("lifecycle_mirror_records") or []
    for record in records:
        if not isinstance(record, dict):
            continue
        handoff_id = str(record.get("paperops_handoff_id") or "")
        linked_handoff = handoff_id if handoff_id in known_handoffs else None
        if linked_handoff is None:
            missing_lineage += 1
        identity = {
            "broker_order_id_hash": record.get("broker_order_id_hash"),
            "client_order_id_hash": record.get("client_order_id_hash"),
            "state": _state(record),
            "submitted_at": record.get("submitted_at"),
            "filled_at": record.get("filled_at"),
            "canceled_at": record.get("canceled_at"),
            "filled_qty": record.get("filled_qty"),
        }
        event_id = _stable("lifecycle-event", identity)
        trade_id = str(
            record.get("source_proof_order_id")
            or record.get("client_order_id_hash")
            or record.get("broker_order_id_hash")
            or event_id
        )
        payload = {
            **record,
            "catc_lineage": {
                "handoff_linked": linked_handoff is not None,
                "missing_lineage_invented": False,
                "proof_eligible": False,
            },
        }
        try:
            inserted += int(
                store.record_lifecycle_event(
                    event_id=event_id,
                    trade_id=trade_id,
                    handoff_id=linked_handoff,
                    lifecycle_state=_state(record),
                    payload=payload,
                    created_at=str(
                        record.get("filled_at")
                        or record.get("submitted_at")
                        or source.get("generated_at")
                        or now_iso()
                    ),
                )
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{event_id}:{type(exc).__name__}:{str(exc)[:240]}")
    integrity = store.integrity_report()
    ambiguous = int(source.get("ambiguous_lifecycle_record_count") or 0)
    if ambiguous:
        errors.append(f"ambiguous_lifecycle_records:{ambiguous}")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_lifecycle_control_plane_checks",
        "generated_at": now_iso(),
        "status": "passed" if not errors and integrity.get("status") == "passed" else "blocked",
        "source_record_count": len(records),
        "inserted_event_count": inserted,
        "stored_lifecycle_event_count": integrity.get("counts", {}).get("lifecycle_events", 0),
        "missing_handoff_lineage_count": missing_lineage,
        "missing_lineage_invented_count": 0,
        "ambiguous_lifecycle_record_count": ambiguous,
        "proof_credit_created_count": 0,
        "validation_errors": errors,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
    }
    write_json_atomic(runtime / CHECK_ARTIFACT, payload)
    return payload


__all__ = ["sync_lifecycle_control_plane"]
