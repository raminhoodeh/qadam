"""Append-only canonical event storage and rebuildable SQLite QEG index."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
from typing import Any, Iterable

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import file_sha256, now_iso, write_json_atomic
from orchestrator.qadam_qeg_common import (
    GRAPH_HEALTH_ARTIFACT,
    GRAPH_MANIFEST_ARTIFACT,
    qeg_authority,
    record_hash,
    research_root,
    runtime_dir,
)
from orchestrator.qadam_temporal_graph_contracts import validate_record

GRAPH_SOFT_LIMIT_BYTES = 10 * 1024**3
GRAPH_HARD_LIMIT_BYTES = 20 * 1024**3
GRAPH_MIN_FREE_BYTES = 64 * 1024**3


class TemporalGraphStore:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.from_env()
        self.root = research_root(self.settings)
        self.events_root = self.root / "events"
        self.index_root = self.root / "index"
        self.lock_path = self.root / ".append.lock"
        self.events_root.mkdir(parents=True, exist_ok=True)
        self.index_root.mkdir(parents=True, exist_ok=True)

    def _event_path(self, record: dict[str, Any]) -> Path:
        generated = str(record.get("generated_at") or now_iso())
        day = generated[:10] if len(generated) >= 10 else datetime.now(timezone.utc).date().isoformat()
        path = self.events_root / day / "events.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def append(self, records: Iterable[dict[str, Any]]) -> dict[str, int]:
        prepared = list(records)
        errors = [error for record in prepared for error in validate_record(record)]
        if errors:
            raise ValueError("invalid_graph_records:" + ",".join(sorted(set(errors))))
        existing_bytes = sum(path.stat().st_size for path in self.root.rglob("*") if path.is_file())
        incoming_bytes = sum(len(json.dumps(row, sort_keys=True).encode("utf-8")) + 1 for row in prepared)
        free_bytes = shutil.disk_usage(self.root).free
        if free_bytes < GRAPH_MIN_FREE_BYTES:
            raise RuntimeError("graph_storage_minimum_free_space_hold")
        if existing_bytes + incoming_bytes > GRAPH_HARD_LIMIT_BYTES:
            raise RuntimeError("graph_storage_hard_ceiling_hold")
        if existing_bytes > GRAPH_SOFT_LIMIT_BYTES:
            raise RuntimeError("graph_storage_soft_backpressure_hold")
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        written = 0
        duplicates = 0
        with self.lock_path.open("a+", encoding="utf-8") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                existing = self._existing_semantic_hashes()
                by_path: dict[Path, list[dict[str, Any]]] = {}
                for record in prepared:
                    semantic_hash = self._semantic_record_hash(record)
                    if semantic_hash in existing:
                        duplicates += 1
                        continue
                    existing.add(semantic_hash)
                    by_path.setdefault(self._event_path(record), []).append(record)
                for path, rows in by_path.items():
                    descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
                    try:
                        for row in rows:
                            os.write(descriptor, (json.dumps(row, sort_keys=True) + "\n").encode("utf-8"))
                            written += 1
                        os.fsync(descriptor)
                    finally:
                        os.close(descriptor)
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        return {"written": written, "duplicates": duplicates}

    def _event_files(self) -> list[Path]:
        return sorted(
            [*self.events_root.glob("*/events.jsonl"), *self.events_root.glob("*/events.jsonl.gz")]
        )

    @staticmethod
    def _semantic_record_hash(record: dict[str, Any]) -> str:
        """Ignore write time while retaining identity, state, payload and provenance.

        Provider observations carry their publication and availability times in
        their normalized payloads.  Excluding wrapper write timestamps prevents
        unchanged entities and research projections from growing the canonical
        event log on every unattended cycle.
        """

        return record_hash(record, omit=("record_hash", "generated_at", "available_at"))

    def _existing_semantic_hashes(self) -> set[str]:
        hashes: set[str] = set()
        for record in self.iter_events():
            hashes.add(self._semantic_record_hash(record))
        return hashes

    def repair_legacy_identity_aliases(self) -> dict[str, Any]:
        """Append aliases for pre-QEG node IDs referenced by legacy edges.

        The migration never edits or deletes an earlier event.  It supplies the
        missing endpoint node under the already-published external identity so
        every historical relationship remains reconstructable.
        """

        records = list(self.iter_events())
        node_ids = {
            str(row.get("node_id"))
            for row in records
            if row.get("record_kind") == "node" and row.get("node_id")
        }
        nodes_by_identity = {
            str(row.get("identity")): row
            for row in records
            if row.get("record_kind") == "node" and row.get("identity")
        }
        missing = sorted(
            {
                str(row.get(endpoint))
                for row in records
                if row.get("record_kind") == "edge"
                for endpoint in ("from_node_id", "to_node_id")
                if row.get(endpoint) and str(row.get(endpoint)) not in node_ids
            }
        )
        aliases: list[dict[str, Any]] = []
        unresolved: list[str] = []
        for endpoint_id in missing:
            source = nodes_by_identity.get(endpoint_id)
            if source is None:
                unresolved.append(endpoint_id)
                continue
            alias = dict(source)
            alias["node_id"] = endpoint_id
            alias["generated_at"] = now_iso()
            payload = dict(alias.get("payload") or {})
            payload["legacy_identity_alias"] = True
            payload["canonical_identity_node_id"] = source.get("node_id")
            alias["payload"] = payload
            alias["record_hash"] = record_hash(alias, omit=("record_hash",))
            aliases.append(alias)
        append_result = self.append(aliases) if aliases else {"written": 0, "duplicates": 0}
        return {
            "missing_endpoint_count": len(missing),
            "alias_record_count": len(aliases),
            "alias_records_written": append_result["written"],
            "unresolved_endpoint_ids": unresolved,
        }

    def iter_events(self) -> Iterable[dict[str, Any]]:
        for path in self._event_files():
            opener = gzip.open if path.suffix == ".gz" else Path.open
            with opener(path, "rt", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(payload, dict):
                        yield payload

    def compact_closed_event_partitions(self) -> dict[str, Any]:
        today = datetime.now(timezone.utc).date().isoformat()
        compacted: list[str] = []
        for path in sorted(self.events_root.glob("*/events.jsonl")):
            if path.parent.name >= today or not path.is_file():
                continue
            target = path.with_suffix(path.suffix + ".gz")
            temporary = target.with_suffix(target.suffix + ".tmp")
            with path.open("rb") as source, gzip.open(temporary, "wb", compresslevel=6) as destination:
                shutil.copyfileobj(source, destination)
            with gzip.open(temporary, "rt", encoding="utf-8") as verification:
                for line in verification:
                    if line.strip():
                        json.loads(line)
            os.replace(temporary, target)
            path.unlink()
            compacted.append(str(target.relative_to(self.root)))
        return {
            "compacted_partition_count": len(compacted),
            "compacted_partitions": compacted,
            "canonical_records_deleted": False,
        }

    def rebuild(self) -> dict[str, Any]:
        alias_repair = self.repair_legacy_identity_aliases()
        records = list(self.iter_events())
        logical_hash = hashlib.sha256(
            "\n".join(sorted(str(row.get("record_hash")) for row in records)).encode("utf-8")
        ).hexdigest()
        target = self.index_root / "graph.sqlite3"
        descriptor, temporary_name = tempfile.mkstemp(prefix=".graph.", suffix=".sqlite3", dir=self.index_root)
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            connection = sqlite3.connect(temporary)
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.executescript(
                """
                CREATE TABLE nodes (
                    node_id TEXT PRIMARY KEY, node_type TEXT NOT NULL, trust_layer TEXT NOT NULL,
                    evidence_state TEXT NOT NULL, available_at TEXT NOT NULL,
                    record_hash TEXT NOT NULL UNIQUE, payload_json TEXT NOT NULL
                );
                CREATE TABLE edges (
                    edge_id TEXT PRIMARY KEY, edge_type TEXT NOT NULL,
                    from_node_id TEXT NOT NULL, to_node_id TEXT NOT NULL,
                    trust_layer TEXT NOT NULL, evidence_state TEXT NOT NULL,
                    available_at TEXT NOT NULL, record_hash TEXT NOT NULL UNIQUE,
                    payload_json TEXT NOT NULL,
                    FOREIGN KEY(from_node_id) REFERENCES nodes(node_id),
                    FOREIGN KEY(to_node_id) REFERENCES nodes(node_id)
                );
                CREATE INDEX idx_nodes_type ON nodes(node_type);
                CREATE INDEX idx_nodes_available ON nodes(available_at);
                CREATE INDEX idx_edges_type ON edges(edge_type);
                CREATE INDEX idx_edges_from ON edges(from_node_id);
                CREATE INDEX idx_edges_to ON edges(to_node_id);
                CREATE INDEX idx_edges_available ON edges(available_at);
                """
            )
            def version_key(item: dict[str, Any]) -> tuple[str, str, str]:
                return (
                    str(item.get("available_at") or ""),
                    str(item.get("generated_at") or ""),
                    str(item.get("record_hash") or ""),
                )

            latest_nodes: dict[str, dict[str, Any]] = {}
            latest_edges: dict[str, dict[str, Any]] = {}
            for row in records:
                if row.get("record_kind") == "node" and row.get("node_id"):
                    identity = str(row["node_id"])
                    if identity not in latest_nodes or version_key(row) > version_key(latest_nodes[identity]):
                        latest_nodes[identity] = row
                elif row.get("record_kind") == "edge" and row.get("edge_id"):
                    identity = str(row["edge_id"])
                    if identity not in latest_edges or version_key(row) > version_key(latest_edges[identity]):
                        latest_edges[identity] = row

            for row in sorted(latest_nodes.values(), key=lambda item: str(item.get("node_id"))):
                connection.execute(
                    "INSERT INTO nodes VALUES (?,?,?,?,?,?,?)",
                    (
                        row.get("node_id"), row.get("node_type"), row.get("trust_layer"),
                        row.get("evidence_state"), row.get("available_at"), row.get("record_hash"),
                        json.dumps(row, sort_keys=True),
                    ),
                )
            for row in sorted(latest_edges.values(), key=lambda item: str(item.get("edge_id"))):
                connection.execute(
                    "INSERT INTO edges VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        row.get("edge_id"), row.get("edge_type"), row.get("from_node_id"),
                        row.get("to_node_id"), row.get("trust_layer"), row.get("evidence_state"),
                        row.get("available_at"), row.get("record_hash"), json.dumps(row, sort_keys=True),
                    ),
                )
            connection.commit()
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            counts = {
                "node_count": connection.execute("SELECT COUNT(*) FROM nodes").fetchone()[0],
                "edge_count": connection.execute("SELECT COUNT(*) FROM edges").fetchone()[0],
            }
            connection.close()
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
        by_type = Counter(
            str(row.get("node_type") or row.get("edge_type") or "unknown") for row in records
        )
        manifest = {
            "schema_version": "qadam_temporal_graph_store.v1",
            "artifact_type": "qadam_temporal_graph_manifest",
            "generated_at": now_iso(),
            "status": "complete",
            "generation_id": logical_hash[:24],
            "logical_record_set_hash": logical_hash,
            "event_file_count": len(self._event_files()),
            "event_record_count": len(records),
            **counts,
            "record_type_counts": dict(sorted(by_type.items())),
            "legacy_identity_alias_repair": alias_repair,
            "index_sha256": file_sha256(target),
            "index_size_bytes": target.stat().st_size,
            "authority": qeg_authority(),
        }
        runtime = runtime_dir(self.settings)
        write_json_atomic(runtime / GRAPH_MANIFEST_ARTIFACT, manifest)
        health = {
            "schema_version": "qadam_temporal_graph_store.v1",
            "artifact_type": "qadam_temporal_graph_health",
            "generated_at": now_iso(),
            "status": "healthy",
            "generation_id": manifest["generation_id"],
            "canonical_events_rebuildable": True,
            "sqlite_index_disposable": True,
            "event_validation_error_count": 0,
            "dangling_edge_endpoint_count": len(alias_repair["unresolved_endpoint_ids"]),
            "disk": {
                "graph_root_bytes": sum(path.stat().st_size for path in self.root.rglob("*") if path.is_file()),
                "filesystem_free_bytes": shutil.disk_usage(self.root).free,
            },
            "authority": qeg_authority(),
        }
        write_json_atomic(runtime / GRAPH_HEALTH_ARTIFACT, health)
        return manifest

    def query_nodes(self, *, node_type: str | None = None, cutoff: str | None = None) -> list[dict[str, Any]]:
        path = self.index_root / "graph.sqlite3"
        if not path.exists():
            self.rebuild()
        connection = sqlite3.connect(path)
        clauses: list[str] = []
        params: list[Any] = []
        if node_type:
            clauses.append("node_type = ?")
            params.append(node_type)
        if cutoff:
            clauses.append("available_at <= ?")
            params.append(cutoff)
        sql = "SELECT payload_json FROM nodes"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY available_at, node_id"
        rows = [json.loads(item[0]) for item in connection.execute(sql, params).fetchall()]
        connection.close()
        return rows


def validate_store(settings: Settings | None = None) -> list[str]:
    store = TemporalGraphStore(settings)
    first = store.rebuild()
    second = store.rebuild()
    errors: list[str] = []
    if first.get("logical_record_set_hash") != second.get("logical_record_set_hash"):
        errors.append("deterministic_rebuild_hash_mismatch")
    if first.get("node_count") != second.get("node_count") or first.get("edge_count") != second.get("edge_count"):
        errors.append("deterministic_rebuild_count_mismatch")
    if any(validate_record(row) for row in store.iter_events()):
        errors.append("canonical_event_validation_failed")
    records = list(store.iter_events())
    node_ids = {
        str(row.get("node_id")) for row in records if row.get("record_kind") == "node"
    }
    if any(
        str(row.get(endpoint)) not in node_ids
        for row in records
        if row.get("record_kind") == "edge"
        for endpoint in ("from_node_id", "to_node_id")
    ):
        errors.append("dangling_graph_edge_endpoint")
    return errors
