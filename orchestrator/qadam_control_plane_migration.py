"""Idempotent import of legacy paper facts into the CATC control plane."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_control_plane_store import ControlPlaneStore
from orchestrator.qadam_operator_ready_common import now_iso, runtime_dir, write_json_atomic

SCHEMA_VERSION = "qadam_control_plane_legacy_import.v1"
IMPORT_ARTIFACT = "qadam_control_plane_legacy_import.json"

IMPORT_SOURCES = (
    ("paper_orders.jsonl", "broker_order"),
    ("qadam_paper_lifecycle_v2_records.jsonl", "lifecycle"),
    ("qadam_paper_lifecycle_v2_events.jsonl", "lifecycle"),
    ("qadam_paperops_handoff_v3.jsonl", "handoff"),
    ("qadam_paperops_handoff_v3_accepted.jsonl", "handoff"),
    ("qadam_paperops_handoff_v3_consumption_receipts.jsonl", "receipt"),
)


def _file_sha(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _stable(prefix: str, payload: dict[str, Any]) -> str:
    material = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return f"{prefix}:{sha256(material.encode('utf-8')).hexdigest()[:24]}"


def _timestamp(row: dict[str, Any]) -> str:
    for key in (
        "generated_at",
        "observed_at",
        "submitted_at",
        "filled_at",
        "created_at",
    ):
        if row.get(key):
            return str(row[key])
    return now_iso()


def import_legacy_control_plane(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    store = ControlPlaneStore.from_settings(settings)
    source_results: list[dict[str, Any]] = []
    errors: list[str] = []
    inserted_counts = {"broker_order": 0, "lifecycle": 0, "handoff": 0, "receipt": 0}

    for name, source_type in IMPORT_SOURCES:
        path = runtime / name
        if not path.is_file():
            source_results.append(
                {"source": name, "source_type": source_type, "state": "missing", "record_count": 0}
            )
            continue
        rows = _read_jsonl(path)
        source_sha = _file_sha(path)
        import_id = f"legacy-import:{source_sha[:24]}"
        try:
            first_import = store.record_legacy_import(
                import_id=import_id,
                source_path=name,
                source_sha256=source_sha,
                record_count=len(rows),
                notes="legacy_import provenance; missing decision lineage is not inferred",
            )
            for row in rows:
                legacy_payload = {
                    **row,
                    "catc_provenance": {
                        "origin": "legacy_import",
                        "source_path": name,
                        "source_sha256": source_sha,
                        "lineage_complete": False,
                        "proof_eligible": False,
                    },
                }
                if source_type == "broker_order":
                    order_id = str(row.get("order_id") or row.get("client_order_id") or "")
                    event_id = _stable("legacy-broker-event", legacy_payload)
                    inserted = store.record_broker_event(
                        event_id=event_id,
                        handoff_id=None,
                        broker_order_id=order_id or None,
                        event_type=str(row.get("status") or "mirrored"),
                        payload=legacy_payload,
                        created_at=_timestamp(row),
                    )
                elif source_type == "lifecycle":
                    trade_id = str(
                        row.get("source_record_id")
                        or row.get("trade_id")
                        or row.get("lifecycle_record_id")
                        or _stable("legacy-trade", row)
                    )
                    event_id = str(row.get("event_id") or row.get("lifecycle_record_id") or "")
                    event_id = event_id or _stable("legacy-lifecycle-event", legacy_payload)
                    inserted = store.record_lifecycle_event(
                        event_id=event_id,
                        trade_id=trade_id,
                        handoff_id=None,
                        lifecycle_state=str(
                            row.get("lifecycle_state") or row.get("state") or "legacy_unknown"
                        ),
                        payload=legacy_payload,
                        created_at=_timestamp(row),
                    )
                else:
                    # Historical handoff snapshots are imported only when their
                    # decision lineage exists. Empty current snapshots are
                    # recorded in the import manifest but cannot create facts.
                    inserted = False
                inserted_counts[source_type] += int(inserted)
            source_results.append(
                {
                    "source": name,
                    "source_type": source_type,
                    "state": "imported" if first_import else "already_imported",
                    "record_count": len(rows),
                    "source_sha256": source_sha,
                }
            )
        except Exception as exc:  # noqa: BLE001 - migration records exact source failure
            errors.append(f"{name}:{type(exc).__name__}:{str(exc)[:300]}")

    integrity = store.integrity_report()
    if integrity.get("status") != "passed":
        errors.append("control_plane_integrity_failed_after_import")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_control_plane_legacy_import",
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "sources": source_results,
        "inserted_counts": inserted_counts,
        "integrity": integrity,
        "validation_errors": errors,
        "missing_lineage_invented_count": 0,
        "proof_credit_created_count": 0,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "live_capital_enabled": False,
    }
    write_json_atomic(runtime / IMPORT_ARTIFACT, payload)
    write_json_atomic(runtime / "qadam_control_plane_integrity.json", integrity)
    return payload


__all__ = ["import_legacy_control_plane"]
