"""Rebuild read-only JSON projections from the canonical control-plane store."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_control_plane_store import ControlPlaneStore
from orchestrator.qadam_operator_ready_common import now_iso, runtime_dir, write_json_atomic

SCHEMA_VERSION = "qadam_projection_outbox.v1"
SUMMARY_ARTIFACT = "qadam_control_plane_projection_summary.json"

PROJECTIONS = {
    "decision_transactions": "qadam_control_plane_decisions.jsonl",
    "gate_decisions": "qadam_control_plane_gate_decisions.jsonl",
    "handoffs": "qadam_control_plane_handoffs.jsonl",
    "handoff_receipts": "qadam_control_plane_handoff_receipts.jsonl",
    "broker_events": "qadam_control_plane_broker_events.jsonl",
    "lifecycle_events": "qadam_control_plane_lifecycle_events.jsonl",
    "service_runs": "qadam_control_plane_service_runs.jsonl",
    "repair_requests": "qadam_control_plane_repair_requests.jsonl",
}


def rebuild_control_plane_projections(
    settings: Settings | None = None,
    *,
    destination: Path | None = None,
) -> dict[str, Any]:
    runtime = (destination or runtime_dir(settings)).resolve()
    runtime.mkdir(parents=True, exist_ok=True)
    store = ControlPlaneStore.from_settings(settings)
    counts = {
        table: store.rebuild_jsonl_projection(
            table=table,
            destination=runtime / filename,
            payload_only=True,
        )
        for table, filename in PROJECTIONS.items()
    }
    integrity = store.integrity_report()
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_control_plane_projection_summary",
        "generated_at": now_iso(),
        "status": "passed" if integrity.get("status") == "passed" else "blocked",
        "projection_counts": counts,
        "integrity": integrity,
        "authoritative_store": str(store.path),
        "json_is_rebuildable_projection": True,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "live_capital_enabled": False,
    }
    write_json_atomic(runtime / SUMMARY_ARTIFACT, payload)
    return payload


__all__ = ["PROJECTIONS", "rebuild_control_plane_projections"]
