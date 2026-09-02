"""Append-only canonical event storage and rebuildable SQLite QEG index."""

from __future__ import annotations

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
        self.rebuild_lock_path = self.root / ".rebuild.lock"
        self.semantic_index_path = self.index_root / "semantic_hashes.sqlite3"
        self.events_root.mkdir(parents=True, exist_ok=True)
        self.index_root.mkdir(parents=True, exist_ok=True)

    def _event_path(self, record: dict[str, Any]) -> Path:
        generated = str(record.get("generated_at") or now_iso())
        day = generated[:10] if len(generated) >= 10 else datetime.now(timezone.utc).date().isoformat()
        path = self.events_root / day / "events.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _event_snapshot(self) -> dict[str, Any]:
        entries = [
            {
                "path": str(path.relative_to(self.root)),
                "size_bytes": path.stat().st_size,
                "mtime_ns": path.stat().st_mtime_ns,
            }
            for path in self._event_files()
        ]
        encoded = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return {
            "digest": hashlib.sha256(encoded).hexdigest(),
            "file_count": len(entries),
            "total_bytes": sum(int(row["size_bytes"]) for row in entries),
            "entries": entries,
        }

    @staticmethod
    def _record_type(record: dict[str, Any]) -> str:
        return str(record.get("node_type") or record.get("edge_type") or "unknown")

    @staticmethod
    def _version_key(record: dict[str, Any]) -> tuple[str, str, str]:
        return (
            str(record.get("available_at") or ""),
            str(record.get("generated_at") or ""),
            str(record.get("record_hash") or ""),
        )

    def _semantic_index_matches(self, snapshot: dict[str, Any]) -> bool:
        if not self.semantic_index_path.exists():
            return False
        try:
            connection = sqlite3.connect(
                f"file:{self.semantic_index_path}?mode=ro",
                uri=True,
                timeout=30.0,
            )
            row = connection.execute(
                "SELECT value FROM metadata WHERE key = 'event_snapshot_digest'"
            ).fetchone()
            connection.close()
        except sqlite3.Error:
            return False
        return bool(row and row[0] == snapshot.get("digest"))

    def _rebuild_semantic_index(
        self,
        records: list[dict[str, Any]],
        snapshot: dict[str, Any],
    ) -> None:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".semantic.", suffix=".sqlite3", dir=self.index_root
        )
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            connection = sqlite3.connect(temporary)
            connection.execute("PRAGMA journal_mode=OFF")
            connection.execute("PRAGMA synchronous=OFF")
            connection.executescript(
                """
                CREATE TABLE physical_records (
                    record_hash TEXT PRIMARY KEY,
                    semantic_hash TEXT NOT NULL,
                    record_kind TEXT NOT NULL,
                    record_type TEXT NOT NULL
                );
                CREATE TABLE semantic_hashes (
                    semantic_hash TEXT PRIMARY KEY
                );
                CREATE TABLE metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE INDEX idx_physical_semantic
                    ON physical_records(semantic_hash);
                CREATE INDEX idx_physical_type
                    ON physical_records(record_type);
                """
            )
            physical_rows = [
                (
                    str(record.get("record_hash")),
                    self._semantic_record_hash(record),
                    str(record.get("record_kind") or "unknown"),
                    self._record_type(record),
                )
                for record in records
            ]
            connection.executemany(
                "INSERT OR IGNORE INTO physical_records VALUES (?,?,?,?)",
                physical_rows,
            )
            connection.executemany(
                "INSERT OR IGNORE INTO semantic_hashes VALUES (?)",
                ((row[1],) for row in physical_rows),
            )
            connection.executemany(
                "INSERT INTO metadata VALUES (?,?)",
                (
                    ("event_snapshot_digest", str(snapshot["digest"])),
                    ("physical_record_count", str(len(records))),
                ),
            )
            connection.commit()
            connection.close()
            os.replace(temporary, self.semantic_index_path)
        finally:
            temporary.unlink(missing_ok=True)

    def _ensure_semantic_index(self, snapshot: dict[str, Any]) -> None:
        if self._semantic_index_matches(snapshot):
            return
        records = list(self.iter_events())
        self._rebuild_semantic_index(records, snapshot)

    def _existing_semantic_hashes_from_index(
        self,
        semantic_hashes: list[str] | None = None,
    ) -> set[str]:
        connection = sqlite3.connect(self.semantic_index_path, timeout=30.0)
        try:
            if semantic_hashes is None:
                return {
                    str(row[0])
                    for row in connection.execute(
                        "SELECT semantic_hash FROM semantic_hashes"
                    )
                }
            existing: set[str] = set()
            for offset in range(0, len(semantic_hashes), 500):
                chunk = semantic_hashes[offset : offset + 500]
                placeholders = ",".join("?" for _value in chunk)
                existing.update(
                    str(row[0])
                    for row in connection.execute(
                        "SELECT semantic_hash FROM semantic_hashes "
                        f"WHERE semantic_hash IN ({placeholders})",
                        chunk,
                    )
                )
            return existing
        finally:
            connection.close()

    def _append_event_rows_locked(self, records: list[dict[str, Any]]) -> int:
        by_path: dict[Path, list[dict[str, Any]]] = {}
        for record in records:
            by_path.setdefault(self._event_path(record), []).append(record)
        written = 0
        for path, rows in by_path.items():
            descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
            try:
                for row in rows:
                    os.write(
                        descriptor,
                        (json.dumps(row, sort_keys=True) + "\n").encode("utf-8"),
                    )
                    written += 1
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        return written

    @staticmethod
    def _current_versions(
        connection: sqlite3.Connection,
        table: str,
        identity_column: str,
        identities: list[str],
    ) -> dict[str, dict[str, Any]]:
        current: dict[str, dict[str, Any]] = {}
        for offset in range(0, len(identities), 500):
            chunk = identities[offset : offset + 500]
            placeholders = ",".join("?" for _value in chunk)
            rows = connection.execute(
                f"SELECT {identity_column}, payload_json FROM {table} "
                f"WHERE {identity_column} IN ({placeholders})",
                chunk,
            ).fetchall()
            for identity, payload_json in rows:
                current[str(identity)] = json.loads(payload_json)
        return current

    def _incremental_index_update(self, records: list[dict[str, Any]]) -> None:
        target = self.index_root / "graph.sqlite3"
        if not target.exists() or not records:
            return
        connection = sqlite3.connect(target, timeout=120.0)
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            latest_nodes: dict[str, dict[str, Any]] = {}
            latest_edges: dict[str, dict[str, Any]] = {}
            for row in records:
                if row.get("record_kind") == "node" and row.get("node_id"):
                    identity = str(row["node_id"])
                    if identity not in latest_nodes or self._version_key(row) > self._version_key(
                        latest_nodes[identity]
                    ):
                        latest_nodes[identity] = row
                elif row.get("record_kind") == "edge" and row.get("edge_id"):
                    identity = str(row["edge_id"])
                    if identity not in latest_edges or self._version_key(row) > self._version_key(
                        latest_edges[identity]
                    ):
                        latest_edges[identity] = row

            current_nodes = self._current_versions(
                connection, "nodes", "node_id", list(latest_nodes)
            )
            current_edges = self._current_versions(
                connection, "edges", "edge_id", list(latest_edges)
            )
            for identity, row in sorted(latest_nodes.items()):
                if identity in current_nodes and self._version_key(row) <= self._version_key(
                    current_nodes[identity]
                ):
                    continue
                connection.execute(
                    """
                    INSERT INTO nodes VALUES (?,?,?,?,?,?,?)
                    ON CONFLICT(node_id) DO UPDATE SET
                        node_type=excluded.node_type,
                        trust_layer=excluded.trust_layer,
                        evidence_state=excluded.evidence_state,
                        available_at=excluded.available_at,
                        record_hash=excluded.record_hash,
                        payload_json=excluded.payload_json
                    """,
                    (
                        row.get("node_id"),
                        row.get("node_type"),
                        row.get("trust_layer"),
                        row.get("evidence_state"),
                        row.get("available_at"),
                        row.get("record_hash"),
                        json.dumps(row, sort_keys=True),
                    ),
                )
            for identity, row in sorted(latest_edges.items()):
                if identity in current_edges and self._version_key(row) <= self._version_key(
                    current_edges[identity]
                ):
                    continue
                connection.execute(
                    """
                    INSERT INTO edges VALUES (?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(edge_id) DO UPDATE SET
                        edge_type=excluded.edge_type,
                        from_node_id=excluded.from_node_id,
                        to_node_id=excluded.to_node_id,
                        trust_layer=excluded.trust_layer,
                        evidence_state=excluded.evidence_state,
                        available_at=excluded.available_at,
                        record_hash=excluded.record_hash,
                        payload_json=excluded.payload_json
                    """,
                    (
                        row.get("edge_id"),
                        row.get("edge_type"),
                        row.get("from_node_id"),
                        row.get("to_node_id"),
                        row.get("trust_layer"),
                        row.get("evidence_state"),
                        row.get("available_at"),
                        row.get("record_hash"),
                        json.dumps(row, sort_keys=True),
                    ),
                )
            connection.commit()
        finally:
            connection.close()

    def _record_semantic_index_append(
        self,
        records: list[dict[str, Any]],
        snapshot: dict[str, Any],
    ) -> None:
        connection = sqlite3.connect(self.semantic_index_path, timeout=120.0)
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.executemany(
                "INSERT OR IGNORE INTO physical_records VALUES (?,?,?,?)",
                (
                    (
                        str(record.get("record_hash")),
                        self._semantic_record_hash(record),
                        str(record.get("record_kind") or "unknown"),
                        self._record_type(record),
                    )
                    for record in records
                ),
            )
            connection.executemany(
                "INSERT OR IGNORE INTO semantic_hashes VALUES (?)",
                ((self._semantic_record_hash(record),) for record in records),
            )
            current_count_row = connection.execute(
                "SELECT value FROM metadata WHERE key = 'physical_record_count'"
            ).fetchone()
            current_count = int(current_count_row[0]) if current_count_row else 0
            connection.execute(
                "INSERT OR REPLACE INTO metadata VALUES (?,?)",
                ("event_snapshot_digest", str(snapshot["digest"])),
            )
            connection.execute(
                "INSERT OR REPLACE INTO metadata VALUES (?,?)",
                ("physical_record_count", str(current_count + len(records))),
            )
            connection.commit()
        finally:
            connection.close()

    def append(self, records: Iterable[dict[str, Any]]) -> dict[str, int]:
        prepared = list(records)
        if not prepared:
            return {"written": 0, "duplicates": 0}
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
                before_snapshot = self._event_snapshot()
                self._ensure_semantic_index(before_snapshot)
                prepared_hashes = [self._semantic_record_hash(record) for record in prepared]
                existing = self._existing_semantic_hashes_from_index(prepared_hashes)
                accepted: list[dict[str, Any]] = []
                for record in prepared:
                    semantic_hash = self._semantic_record_hash(record)
                    if semantic_hash in existing:
                        duplicates += 1
                        continue
                    existing.add(semantic_hash)
                    accepted.append(record)
                if accepted:
                    written = self._append_event_rows_locked(accepted)
                    self._incremental_index_update(accepted)
                    self._record_semantic_index_append(accepted, self._event_snapshot())
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
        snapshot = self._event_snapshot()
        self._ensure_semantic_index(snapshot)
        return self._existing_semantic_hashes_from_index()

    def _legacy_identity_aliases(
        self,
        records: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[str], list[str]]:
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
        return aliases, unresolved, missing

    def repair_legacy_identity_aliases(self) -> dict[str, Any]:
        """Append aliases for pre-QEG node IDs referenced by legacy edges.

        The migration never edits or deletes an earlier event. It supplies the
        missing endpoint node under the already-published external identity so
        every historical relationship remains reconstructable.
        """

        records = list(self.iter_events())
        aliases, unresolved, missing = self._legacy_identity_aliases(records)
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

    def _cleanup_disposable_indexes(self) -> list[str]:
        removed: list[str] = []
        candidates = [
            *self.index_root.glob(".graph.*.sqlite3*"),
            *self.index_root.glob(".semantic.*.sqlite3*"),
            *self.index_root.glob("graph 2.sqlite3*"),
        ]
        for path in sorted(set(candidates)):
            if not path.is_file():
                continue
            path.unlink(missing_ok=True)
            removed.append(path.name)
        return removed

    def _build_graph_index(self, records: list[dict[str, Any]], target: Path) -> None:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".graph.", suffix=".sqlite3", dir=self.index_root
        )
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            connection = sqlite3.connect(temporary)
            connection.execute("PRAGMA journal_mode=OFF")
            connection.execute("PRAGMA synchronous=OFF")
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
            latest_nodes: dict[str, dict[str, Any]] = {}
            latest_edges: dict[str, dict[str, Any]] = {}
            for row in records:
                if row.get("record_kind") == "node" and row.get("node_id"):
                    identity = str(row["node_id"])
                    if identity not in latest_nodes or self._version_key(row) > self._version_key(
                        latest_nodes[identity]
                    ):
                        latest_nodes[identity] = row
                elif row.get("record_kind") == "edge" and row.get("edge_id"):
                    identity = str(row["edge_id"])
                    if identity not in latest_edges or self._version_key(row) > self._version_key(
                        latest_edges[identity]
                    ):
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
            connection.close()
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)

    def _semantic_index_statistics(self) -> tuple[str, int, dict[str, int]]:
        connection = sqlite3.connect(self.semantic_index_path, timeout=120.0)
        try:
            hasher = hashlib.sha256()
            first = True
            for (record_hash_value,) in connection.execute(
                "SELECT record_hash FROM physical_records ORDER BY record_hash"
            ):
                if not first:
                    hasher.update(b"\n")
                hasher.update(str(record_hash_value).encode("utf-8"))
                first = False
            count_row = connection.execute(
                "SELECT value FROM metadata WHERE key = 'physical_record_count'"
            ).fetchone()
            by_type = {
                str(record_type): int(count)
                for record_type, count in connection.execute(
                    "SELECT record_type, COUNT(*) FROM physical_records GROUP BY record_type"
                )
            }
            return hasher.hexdigest(), int(count_row[0]) if count_row else 0, by_type
        finally:
            connection.close()

    def _write_manifest_and_health(
        self,
        *,
        alias_repair: dict[str, Any],
        event_snapshot: dict[str, Any],
        rebuild_skipped: bool,
        removed_disposable_indexes: list[str],
    ) -> dict[str, Any]:
        target = self.index_root / "graph.sqlite3"
        connection = sqlite3.connect(target, timeout=120.0)
        try:
            counts = {
                "node_count": connection.execute("SELECT COUNT(*) FROM nodes").fetchone()[0],
                "edge_count": connection.execute("SELECT COUNT(*) FROM edges").fetchone()[0],
            }
        finally:
            connection.close()
        logical_hash, event_record_count, by_type = self._semantic_index_statistics()
        manifest = {
            "schema_version": "qadam_temporal_graph_store.v2",
            "artifact_type": "qadam_temporal_graph_manifest",
            "generated_at": now_iso(),
            "status": "complete",
            "generation_id": logical_hash[:24],
            "logical_record_set_hash": logical_hash,
            "event_file_count": event_snapshot["file_count"],
            "event_record_count": event_record_count,
            "event_snapshot": event_snapshot,
            **counts,
            "record_type_counts": dict(sorted(by_type.items())),
            "legacy_identity_alias_repair": alias_repair,
            "index_sha256": file_sha256(target),
            "index_size_bytes": target.stat().st_size,
            "incremental_index_enabled": True,
            "semantic_hash_index_enabled": True,
            "rebuild_skipped": rebuild_skipped,
            "removed_disposable_indexes": removed_disposable_indexes,
            "authority": qeg_authority(),
        }
        runtime = runtime_dir(self.settings)
        write_json_atomic(runtime / GRAPH_MANIFEST_ARTIFACT, manifest)
        health = {
            "schema_version": "qadam_temporal_graph_store.v2",
            "artifact_type": "qadam_temporal_graph_health",
            "generated_at": now_iso(),
            "status": "healthy",
            "generation_id": manifest["generation_id"],
            "canonical_events_rebuildable": True,
            "sqlite_index_disposable": True,
            "incremental_index_enabled": True,
            "semantic_hash_index_enabled": True,
            "rebuild_skipped": rebuild_skipped,
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

    def rebuild(self, *, force: bool = False) -> dict[str, Any]:
        """Refresh the index once, or verify it in O(files) when already current."""

        self.rebuild_lock_path.parent.mkdir(parents=True, exist_ok=True)
        with self.rebuild_lock_path.open("a+", encoding="utf-8") as rebuild_lock:
            fcntl.flock(rebuild_lock.fileno(), fcntl.LOCK_EX)
            with self.lock_path.open("a+", encoding="utf-8") as append_lock:
                fcntl.flock(append_lock.fileno(), fcntl.LOCK_EX)
                try:
                    removed = self._cleanup_disposable_indexes()
                    target = self.index_root / "graph.sqlite3"
                    snapshot = self._event_snapshot()
                    if (
                        not force
                        and target.exists()
                        and self._semantic_index_matches(snapshot)
                    ):
                        previous = {}
                        manifest_path = runtime_dir(self.settings) / GRAPH_MANIFEST_ARTIFACT
                        if manifest_path.exists():
                            try:
                                previous = json.loads(
                                    manifest_path.read_text(encoding="utf-8")
                                )
                            except (OSError, json.JSONDecodeError):
                                previous = {}
                        alias_repair = previous.get(
                            "legacy_identity_alias_repair"
                        ) or {
                            "missing_endpoint_count": 0,
                            "alias_record_count": 0,
                            "alias_records_written": 0,
                            "unresolved_endpoint_ids": [],
                        }
                        return self._write_manifest_and_health(
                            alias_repair=alias_repair,
                            event_snapshot=snapshot,
                            rebuild_skipped=True,
                            removed_disposable_indexes=removed,
                        )

                    records = list(self.iter_events())
                    aliases, unresolved, missing = self._legacy_identity_aliases(records)
                    if aliases:
                        self._append_event_rows_locked(aliases)
                        records.extend(aliases)
                    alias_repair = {
                        "missing_endpoint_count": len(missing),
                        "alias_record_count": len(aliases),
                        "alias_records_written": len(aliases),
                        "unresolved_endpoint_ids": unresolved,
                    }
                    snapshot = self._event_snapshot()
                    self._build_graph_index(records, target)
                    self._rebuild_semantic_index(records, snapshot)
                    return self._write_manifest_and_health(
                        alias_repair=alias_repair,
                        event_snapshot=snapshot,
                        rebuild_skipped=False,
                        removed_disposable_indexes=removed,
                    )
                finally:
                    fcntl.flock(append_lock.fileno(), fcntl.LOCK_UN)

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
    records = list(store.iter_events())
    if any(validate_record(row) for row in records):
        errors.append("canonical_event_validation_failed")
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
