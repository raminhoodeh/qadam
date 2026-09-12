"""Verified cold storage for service telemetry, never trading authority rows."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile

HOT_RUN_LIMIT = 10_000
RETAIN_RUNS = 5_000
BATCH_ROWS = 1_000
MAX_BATCHES = 100


def capacity(connection: sqlite3.Connection, max_bytes: int) -> dict:
    pages = int(connection.execute("PRAGMA page_count").fetchone()[0])
    free = int(connection.execute("PRAGMA freelist_count").fetchone()[0])
    page_size = int(connection.execute("PRAGMA page_size").fetchone()[0])
    used = (pages - free) * page_size
    return {"allocated_bytes": pages * page_size, "live_bytes": used,
            "reusable_bytes": free * page_size, "limit_bytes": max_bytes,
            "utilization": used / max_bytes, "write_capacity_available": used < max_bytes}


def _line(row: sqlite3.Row) -> bytes:
    return (json.dumps(dict(row), sort_keys=True, separators=(",", ":")) + "\n").encode()


def _verify(path: Path, digest: str, count: int) -> None:
    actual = hashlib.sha256()
    rows = 0
    with gzip.open(path, "rb") as stream:
        for line in stream:
            actual.update(line)
            rows += 1
    if actual.hexdigest() != digest or rows != count:
        raise RuntimeError("control_plane_telemetry_archive_verification_failed")


def archive_batch(root: Path, rows: list[sqlite3.Row]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(b"".join(_line(row) for row in rows)).hexdigest()
    path = root / f"{digest}.jsonl.gz"
    if not path.exists():
        fd, temporary = tempfile.mkstemp(prefix=".pending-", dir=root)
        try:
            with os.fdopen(fd, "wb") as raw:
                with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as stream:
                    for row in rows:
                        stream.write(_line(row))
                raw.flush()
                os.fsync(raw.fileno())
            _verify(Path(temporary), digest, len(rows))
            os.replace(temporary, path)
            directory = os.open(root, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            Path(temporary).unlink(missing_ok=True)
    _verify(path, digest, len(rows))
    return path


def maintain_service_runs(store, *, apply: bool = True, retain: int = RETAIN_RUNS,
                          trigger: int = HOT_RUN_LIMIT, batch_rows: int = BATCH_ROWS,
                          max_batches: int = MAX_BATCHES) -> dict:
    """Archive then delete under one writer transaction per bounded batch.

    A crash before commit leaves the authoritative rows intact and a reusable
    content-addressed archive. A crash after commit leaves the verified archive.
    Recent runs and the last run of every service stay online. No other table is
    pruned, including trading, research, idempotency and execution-owner records.
    """
    if min(retain, trigger, batch_rows, max_batches) < 1 or retain >= trigger:
        raise ValueError("invalid_control_plane_telemetry_retention")
    connection = store.connect()
    archived = 0
    archives = []
    try:
        before = capacity(connection, store.max_bytes)
        count = connection.execute("SELECT COUNT(*) FROM service_runs").fetchone()[0]
        due = count > trigger or before["utilization"] >= 0.7
        if due and apply:
            for _ in range(max_batches):
                connection.execute("BEGIN IMMEDIATE")
                try:
                    rows = connection.execute(
                        "SELECT * FROM service_runs WHERE rowid NOT IN "
                        "(SELECT rowid FROM service_runs ORDER BY rowid DESC LIMIT ?) "
                        "AND rowid NOT IN (SELECT MAX(rowid) FROM service_runs GROUP BY service_id) "
                        "ORDER BY rowid LIMIT ?", (retain, batch_rows),
                    ).fetchall()
                    if not rows:
                        connection.execute("COMMIT")
                        break
                    for row in rows:
                        if hashlib.sha256(row["payload_json"].encode()).hexdigest() != row["payload_sha256"]:
                            raise RuntimeError("control_plane_telemetry_payload_integrity_failed")
                    path = archive_batch(store.path.parent / "archive" / "control-plane-service-runs", rows)
                    removed = connection.executemany(
                        "DELETE FROM service_runs WHERE run_id=? AND payload_sha256=?",
                        [(row["run_id"], row["payload_sha256"]) for row in rows],
                    ).rowcount
                    if removed != len(rows):
                        raise RuntimeError("control_plane_telemetry_delete_count_mismatch")
                    connection.execute("COMMIT")
                    archived += removed
                    archives.append(path.name)
                except BaseException:
                    if connection.in_transaction:
                        connection.execute("ROLLBACK")
                    raise
            connection.execute("PRAGMA wal_checkpoint(PASSIVE)")
        after = capacity(connection, store.max_bytes)
        remaining = connection.execute("SELECT COUNT(*) FROM service_runs").fetchone()[0]
        return {"status": "blocked" if not after["write_capacity_available"] else (
                    "capacity_warning" if after["utilization"] >= 0.7 else "healthy"),
                "before": before, **after, "maintenance_due": due,
                "hot_service_run_count": remaining, "archived_run_count": archived,
                "archives": archives, "protected_tables_deleted_from": [],
                "broker_write_count": 0}
    finally:
        connection.close()
