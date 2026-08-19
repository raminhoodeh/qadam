"""Durable, append-only authority store for Qadam's paper control plane."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterator, Mapping, Sequence

from orchestrator.config import Settings
from orchestrator.qadam_control_plane_migrations import MIGRATIONS, SCHEMA_VERSION
from orchestrator.qadam_decision_transaction import DecisionTransaction
from orchestrator.qadam_operator_ready_common import atomic_write_text, runtime_dir

DATABASE_NAME = "qadam-control-plane.sqlite3"


class ControlPlaneError(RuntimeError):
    """Raised when canonical control-plane integrity cannot be guaranteed."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(payload: Mapping[str, Any] | Sequence[Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _sha(payload_text: str) -> str:
    return sha256(payload_text.encode("utf-8")).hexdigest()


class ControlPlaneStore:
    """SQLite/WAL authority store; JSON files are downstream projections only."""

    def __init__(
        self,
        path: Path,
        *,
        max_bytes: int = 512 * 1024 * 1024,
        initialize: bool = True,
    ) -> None:
        self.path = path.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_bytes = max_bytes
        if initialize:
            self.migrate()

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "ControlPlaneStore":
        runtime = runtime_dir(settings)
        return cls(runtime / DATABASE_NAME)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30.0, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA wal_autocheckpoint=1000")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            self._check_disk_ceiling(connection)
            connection.execute("COMMIT")
        except Exception:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        finally:
            connection.close()

    def migrate(self) -> None:
        connection = self.connect()
        try:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL, checksum TEXT NOT NULL)"
            )
            applied = {
                int(row["version"]): str(row["checksum"])
                for row in connection.execute("SELECT version, checksum FROM schema_migrations")
            }
            for version, sql in MIGRATIONS:
                checksum = sha256(sql.encode("utf-8")).hexdigest()
                if version in applied:
                    if applied[version] != checksum:
                        raise ControlPlaneError(f"migration_checksum_mismatch:{version}")
                    continue
                connection.executescript(sql)
                connection.execute(
                    "INSERT INTO schema_migrations(version, applied_at, checksum) VALUES (?, ?, ?)",
                    (version, _now_iso(), checksum),
                )
        finally:
            connection.close()

    def _check_disk_ceiling(self, connection: sqlite3.Connection) -> None:
        page_count = int(connection.execute("PRAGMA page_count").fetchone()[0])
        page_size = int(connection.execute("PRAGMA page_size").fetchone()[0])
        if page_count * page_size > self.max_bytes:
            raise ControlPlaneError("control_plane_disk_ceiling_exceeded")

    @staticmethod
    def _insert_immutable(
        connection: sqlite3.Connection,
        *,
        table: str,
        identity_column: str,
        identity: str,
        columns: Sequence[str],
        values: Sequence[Any],
        payload_sha256: str,
    ) -> bool:
        placeholders = ",".join("?" for _ in columns)
        try:
            connection.execute(
                f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})",
                tuple(values),
            )
            return True
        except sqlite3.IntegrityError:
            row = connection.execute(
                f"SELECT payload_sha256 FROM {table} WHERE {identity_column} = ?",
                (identity,),
            ).fetchone()
            if row is None or str(row["payload_sha256"]) != payload_sha256:
                raise ControlPlaneError(f"immutable_identity_collision:{table}:{identity}")
            return False

    def create_decision(self, transaction: DecisionTransaction) -> bool:
        payload = transaction.model_dump(mode="json")
        payload_text = _json(payload)
        payload_sha = _sha(payload_text)
        with self.transaction() as connection:
            inserted = self._insert_immutable(
                connection,
                table="decision_transactions",
                identity_column="decision_id",
                identity=transaction.decision_id,
                columns=(
                    "decision_id",
                    "generation_id",
                    "candidate_identity",
                    "idempotency_key",
                    "stage",
                    "terminal_state",
                    "payload_json",
                    "payload_sha256",
                    "created_at",
                    "updated_at",
                ),
                values=(
                    transaction.decision_id,
                    transaction.generation_id,
                    transaction.candidate_identity,
                    transaction.idempotency_key,
                    transaction.stage,
                    transaction.router_state.value if transaction.router_state else None,
                    payload_text,
                    payload_sha,
                    transaction.created_at,
                    transaction.updated_at,
                ),
                payload_sha256=payload_sha,
            )
            if inserted:
                event_payload = {
                    "decision_id": transaction.decision_id,
                    "stage": transaction.stage,
                    "transaction_sha256": payload_sha,
                }
                self._append_decision_event(
                    connection,
                    decision_id=transaction.decision_id,
                    sequence=0,
                    event_type="decision_created",
                    payload=event_payload,
                    created_at=transaction.created_at,
                )
            return inserted

    def _append_decision_event(
        self,
        connection: sqlite3.Connection,
        *,
        decision_id: str,
        sequence: int,
        event_type: str,
        payload: Mapping[str, Any],
        created_at: str,
    ) -> bool:
        payload_text = _json(payload)
        payload_sha = _sha(payload_text)
        event_id = sha256(
            f"{decision_id}:{sequence}:{event_type}:{payload_sha}".encode("utf-8")
        ).hexdigest()[:32]
        return self._insert_immutable(
            connection,
            table="decision_events",
            identity_column="event_id",
            identity=event_id,
            columns=(
                "event_id",
                "decision_id",
                "sequence",
                "event_type",
                "payload_json",
                "payload_sha256",
                "created_at",
            ),
            values=(
                event_id,
                decision_id,
                sequence,
                event_type,
                payload_text,
                payload_sha,
                created_at,
            ),
            payload_sha256=payload_sha,
        )

    def append_decision_event(
        self,
        *,
        decision_id: str,
        sequence: int,
        event_type: str,
        payload: Mapping[str, Any],
        created_at: str | None = None,
    ) -> bool:
        with self.transaction() as connection:
            return self._append_decision_event(
                connection,
                decision_id=decision_id,
                sequence=sequence,
                event_type=event_type,
                payload=payload,
                created_at=created_at or _now_iso(),
            )

    def record_gate_decision(
        self,
        *,
        gate_decision_id: str,
        decision_id: str,
        gate_name: str,
        sequence: int,
        state: str,
        severity: str,
        payload: Mapping[str, Any],
        created_at: str | None = None,
    ) -> bool:
        timestamp = created_at or _now_iso()
        payload_text = _json(payload)
        payload_sha = _sha(payload_text)
        with self.transaction() as connection:
            return self._insert_immutable(
                connection,
                table="gate_decisions",
                identity_column="gate_decision_id",
                identity=gate_decision_id,
                columns=(
                    "gate_decision_id",
                    "decision_id",
                    "gate_name",
                    "sequence",
                    "state",
                    "severity",
                    "payload_json",
                    "payload_sha256",
                    "created_at",
                ),
                values=(
                    gate_decision_id,
                    decision_id,
                    gate_name,
                    sequence,
                    state,
                    severity,
                    payload_text,
                    payload_sha,
                    timestamp,
                ),
                payload_sha256=payload_sha,
            )

    def accept_handoff(
        self,
        *,
        handoff_id: str,
        decision_id: str,
        candidate_identity: str,
        idempotency_key: str,
        payload: Mapping[str, Any],
        created_at: str | None = None,
    ) -> bool:
        """Persist a handoff and its PaperOps outbox event in one transaction."""

        timestamp = created_at or _now_iso()
        payload_text = _json(payload)
        payload_sha = _sha(payload_text)
        with self.transaction() as connection:
            inserted = self._insert_immutable(
                connection,
                table="handoffs",
                identity_column="handoff_id",
                identity=handoff_id,
                columns=(
                    "handoff_id",
                    "decision_id",
                    "candidate_identity",
                    "idempotency_key",
                    "state",
                    "payload_json",
                    "payload_sha256",
                    "created_at",
                    "updated_at",
                ),
                values=(
                    handoff_id,
                    decision_id,
                    candidate_identity,
                    idempotency_key,
                    "accepted_for_paperops_review",
                    payload_text,
                    payload_sha,
                    timestamp,
                    timestamp,
                ),
                payload_sha256=payload_sha,
            )
            if inserted:
                outbox_payload = {
                    "handoff_id": handoff_id,
                    "decision_id": decision_id,
                    "idempotency_key": idempotency_key,
                    "route": "guarded_alpaca_paper_only",
                }
                outbox_text = _json(outbox_payload)
                outbox_sha = _sha(outbox_text)
                outbox_id = sha256(f"paperops:{handoff_id}".encode("utf-8")).hexdigest()[:32]
                self._insert_immutable(
                    connection,
                    table="projection_outbox",
                    identity_column="event_id",
                    identity=outbox_id,
                    columns=(
                        "event_id",
                        "topic",
                        "aggregate_id",
                        "payload_json",
                        "payload_sha256",
                        "status",
                        "attempts",
                        "created_at",
                        "published_at",
                    ),
                    values=(
                        outbox_id,
                        "paperops_handoff_accepted",
                        handoff_id,
                        outbox_text,
                        outbox_sha,
                        "pending",
                        0,
                        timestamp,
                        None,
                    ),
                    payload_sha256=outbox_sha,
                )
            return inserted

    def record_handoff_receipt(
        self,
        *,
        receipt_id: str,
        handoff_id: str,
        receipt_type: str,
        payload: Mapping[str, Any],
        created_at: str | None = None,
    ) -> bool:
        timestamp = created_at or _now_iso()
        payload_text = _json(payload)
        payload_sha = _sha(payload_text)
        with self.transaction() as connection:
            inserted = self._insert_immutable(
                connection,
                table="handoff_receipts",
                identity_column="receipt_id",
                identity=receipt_id,
                columns=(
                    "receipt_id",
                    "handoff_id",
                    "receipt_type",
                    "payload_json",
                    "payload_sha256",
                    "created_at",
                ),
                values=(
                    receipt_id,
                    handoff_id,
                    receipt_type,
                    payload_text,
                    payload_sha,
                    timestamp,
                ),
                payload_sha256=payload_sha,
            )
            if inserted and receipt_type in {"consumed", "submitted", "duplicate", "rejected"}:
                new_state = {
                    "consumed": "consumed",
                    "submitted": "consumed",
                    "duplicate": "duplicate",
                    "rejected": "rejected",
                }[receipt_type]
                connection.execute(
                    "UPDATE handoffs SET state = ?, updated_at = ? WHERE handoff_id = ?",
                    (new_state, timestamp, handoff_id),
                )
            return inserted

    def reconcile_submitted_idempotency_keys(self, keys: set[str]) -> int:
        """Mark pending handoffs consumed after read-only submission-ledger reconciliation."""

        if not keys:
            return 0
        timestamp = _now_iso()
        updated = 0
        with self.transaction() as connection:
            for key in sorted(keys):
                cursor = connection.execute(
                    "UPDATE handoffs SET state = 'consumed', updated_at = ? "
                    "WHERE idempotency_key = ? AND state = 'accepted_for_paperops_review'",
                    (timestamp, key),
                )
                updated += int(cursor.rowcount)
                connection.execute(
                    "UPDATE projection_outbox SET status = 'published', attempts = attempts + 1, "
                    "published_at = ? WHERE topic = 'paperops_handoff_accepted' "
                    "AND aggregate_id IN (SELECT handoff_id FROM handoffs WHERE idempotency_key = ?)",
                    (timestamp, key),
                )
        return updated

    def write_paperops_projections(
        self,
        *,
        accepted_path: Path,
        receipts_path: Path,
    ) -> dict[str, int]:
        connection = self.connect()
        try:
            accepted_rows = [
                json.loads(str(row["payload_json"]))
                for row in connection.execute(
                    "SELECT payload_json FROM handoffs "
                    "WHERE state = 'accepted_for_paperops_review' ORDER BY created_at, handoff_id"
                )
            ]
            receipt_rows = [
                json.loads(str(row["payload_json"]))
                for row in connection.execute(
                    "SELECT payload_json FROM handoff_receipts ORDER BY created_at, receipt_id"
                )
            ]
        finally:
            connection.close()
        atomic_write_text(
            accepted_path,
            "".join(_json(record) + "\n" for record in accepted_rows),
        )
        atomic_write_text(
            receipts_path,
            "".join(_json(record) + "\n" for record in receipt_rows),
        )
        return {"accepted": len(accepted_rows), "receipts": len(receipt_rows)}

    def record_lifecycle_event(
        self,
        *,
        event_id: str,
        trade_id: str,
        handoff_id: str | None,
        lifecycle_state: str,
        payload: Mapping[str, Any],
        created_at: str | None = None,
    ) -> bool:
        timestamp = created_at or _now_iso()
        payload_text = _json(payload)
        payload_sha = _sha(payload_text)
        with self.transaction() as connection:
            return self._insert_immutable(
                connection,
                table="lifecycle_events",
                identity_column="event_id",
                identity=event_id,
                columns=(
                    "event_id",
                    "trade_id",
                    "handoff_id",
                    "lifecycle_state",
                    "payload_json",
                    "payload_sha256",
                    "created_at",
                ),
                values=(
                    event_id,
                    trade_id,
                    handoff_id,
                    lifecycle_state,
                    payload_text,
                    payload_sha,
                    timestamp,
                ),
                payload_sha256=payload_sha,
            )

    def record_broker_event(
        self,
        *,
        event_id: str,
        handoff_id: str | None,
        broker_order_id: str | None,
        event_type: str,
        payload: Mapping[str, Any],
        created_at: str | None = None,
    ) -> bool:
        timestamp = created_at or _now_iso()
        payload_text = _json(payload)
        payload_sha = _sha(payload_text)
        with self.transaction() as connection:
            return self._insert_immutable(
                connection,
                table="broker_events",
                identity_column="event_id",
                identity=event_id,
                columns=(
                    "event_id",
                    "handoff_id",
                    "broker_order_id",
                    "event_type",
                    "payload_json",
                    "payload_sha256",
                    "created_at",
                ),
                values=(
                    event_id,
                    handoff_id,
                    broker_order_id,
                    event_type,
                    payload_text,
                    payload_sha,
                    timestamp,
                ),
                payload_sha256=payload_sha,
            )

    def record_service_run(
        self,
        *,
        run_id: str,
        service_id: str,
        domain: str,
        status: str,
        payload: Mapping[str, Any],
        started_at: str,
        completed_at: str | None,
    ) -> bool:
        payload_text = _json(payload)
        payload_sha = _sha(payload_text)
        with self.transaction() as connection:
            return self._insert_immutable(
                connection,
                table="service_runs",
                identity_column="run_id",
                identity=run_id,
                columns=(
                    "run_id",
                    "service_id",
                    "domain",
                    "status",
                    "payload_json",
                    "payload_sha256",
                    "started_at",
                    "completed_at",
                ),
                values=(
                    run_id,
                    service_id,
                    domain,
                    status,
                    payload_text,
                    payload_sha,
                    started_at,
                    completed_at,
                ),
                payload_sha256=payload_sha,
            )

    def record_repair_request(
        self,
        *,
        request_id: str,
        domain: str,
        fingerprint: str,
        status: str,
        payload: Mapping[str, Any],
        created_at: str | None = None,
    ) -> bool:
        timestamp = created_at or _now_iso()
        payload_text = _json(payload)
        payload_sha = _sha(payload_text)
        with self.transaction() as connection:
            return self._insert_immutable(
                connection,
                table="repair_requests",
                identity_column="request_id",
                identity=request_id,
                columns=(
                    "request_id",
                    "domain",
                    "fingerprint",
                    "status",
                    "payload_json",
                    "payload_sha256",
                    "created_at",
                    "updated_at",
                ),
                values=(
                    request_id,
                    domain,
                    fingerprint,
                    status,
                    payload_text,
                    payload_sha,
                    timestamp,
                    timestamp,
                ),
                payload_sha256=payload_sha,
            )

    def set_repair_request_status(
        self,
        *,
        fingerprint: str,
        status: str,
    ) -> bool:
        """Close or reopen a known repair without deleting its evidence."""

        if status not in {"open", "resolved", "superseded"}:
            raise ValueError("repair_request_status_invalid")
        with self.transaction() as connection:
            cursor = connection.execute(
                "UPDATE repair_requests SET status = ?, updated_at = ? "
                "WHERE fingerprint = ? AND status != ?",
                (status, _now_iso(), fingerprint, status),
            )
            if cursor.rowcount not in {0, 1}:
                raise ControlPlaneError("repair_request_status_rowcount_invalid")
            return cursor.rowcount == 1

    def record_legacy_import(
        self,
        *,
        import_id: str,
        source_path: str,
        source_sha256: str,
        record_count: int,
        notes: str,
    ) -> bool:
        with self.transaction() as connection:
            try:
                connection.execute(
                    "INSERT INTO legacy_imports(import_id, source_path, source_sha256, "
                    "record_count, imported_at, notes) VALUES (?, ?, ?, ?, ?, ?)",
                    (import_id, source_path, source_sha256, record_count, _now_iso(), notes),
                )
                return True
            except sqlite3.IntegrityError:
                row = connection.execute(
                    "SELECT import_id, record_count FROM legacy_imports WHERE source_sha256 = ?",
                    (source_sha256,),
                ).fetchone()
                if row is None or int(row["record_count"]) != record_count:
                    raise ControlPlaneError(f"legacy_import_collision:{source_path}")
                return False

    def pending_outbox(self, topic: str | None = None) -> list[dict[str, Any]]:
        connection = self.connect()
        try:
            query = "SELECT * FROM projection_outbox WHERE status = 'pending'"
            params: tuple[Any, ...] = ()
            if topic:
                query += " AND topic = ?"
                params = (topic,)
            query += " ORDER BY created_at, event_id"
            return [self._decode_row(row) for row in connection.execute(query, params)]
        finally:
            connection.close()

    def mark_outbox_published(self, event_id: str) -> None:
        with self.transaction() as connection:
            cursor = connection.execute(
                "UPDATE projection_outbox SET status = 'published', attempts = attempts + 1, "
                "published_at = ? WHERE event_id = ? AND status = 'pending'",
                (_now_iso(), event_id),
            )
            if cursor.rowcount not in {0, 1}:
                raise ControlPlaneError("outbox_publish_rowcount_invalid")

    @staticmethod
    def _decode_row(row: sqlite3.Row) -> dict[str, Any]:
        payload = dict(row)
        if "payload_json" in payload:
            payload["payload"] = json.loads(str(payload.pop("payload_json")))
        return payload

    def read_table(self, table: str) -> list[dict[str, Any]]:
        allowed = {
            "decision_transactions",
            "decision_events",
            "gate_decisions",
            "handoffs",
            "handoff_receipts",
            "broker_events",
            "lifecycle_events",
            "service_runs",
            "repair_requests",
            "projection_outbox",
            "legacy_imports",
        }
        if table not in allowed:
            raise ValueError("control_plane_table_not_allowed")
        connection = self.connect()
        try:
            return [self._decode_row(row) for row in connection.execute(f"SELECT * FROM {table}")]
        finally:
            connection.close()

    def rebuild_jsonl_projection(
        self,
        *,
        table: str,
        destination: Path,
        payload_only: bool = True,
    ) -> int:
        rows = self.read_table(table)
        records = [row.get("payload", row) if payload_only else row for row in rows]
        text = "".join(_json(record) + "\n" for record in records)
        atomic_write_text(destination, text)
        return len(records)

    def integrity_report(self) -> dict[str, Any]:
        connection = self.connect()
        try:
            integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
            foreign_keys = [dict(row) for row in connection.execute("PRAGMA foreign_key_check")]
            migrations = [dict(row) for row in connection.execute("SELECT * FROM schema_migrations")]
            counts = {
                table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                for table in (
                    "decision_transactions",
                    "decision_events",
                    "gate_decisions",
                    "handoffs",
                    "handoff_receipts",
                    "broker_events",
                    "lifecycle_events",
                    "projection_outbox",
                    "service_runs",
                    "repair_requests",
                )
            }
            return {
                "schema_version": "qadam_control_plane_integrity.v1",
                "generated_at": _now_iso(),
                "database_path": str(self.path),
                "database_schema_version": SCHEMA_VERSION,
                "integrity_check": integrity,
                "foreign_key_error_count": len(foreign_keys),
                "foreign_key_errors": foreign_keys,
                "migrations": migrations,
                "counts": counts,
                "status": "passed" if integrity == "ok" and not foreign_keys else "blocked",
                "paper_order_created_count": 0,
                "broker_write_count": 0,
                "live_capital_enabled": False,
            }
        finally:
            connection.close()

    def backup(self, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        source = self.connect()
        target = sqlite3.connect(destination)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        return destination

    def checkpoint(self) -> None:
        connection = self.connect()
        try:
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        finally:
            connection.close()

    def compact(self, *, backup_dir: Path | None = None) -> None:
        if backup_dir is not None and self.path.exists():
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            self.backup(backup_dir / f"qadam-control-plane-{timestamp}.sqlite3")
        self.checkpoint()
        connection = self.connect()
        try:
            connection.execute("VACUUM")
        finally:
            connection.close()


__all__ = ["ControlPlaneError", "ControlPlaneStore", "DATABASE_NAME"]
