"""Durable, append-only authority store for Qadam's paper control plane."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterator, Mapping, Sequence

from orchestrator.config import Settings
from orchestrator.qadam_control_plane_identity import (
    IDENTITY_VERSION,
    canonical_risk_decision_id,
    decision_semantic_sha256,
    handoff_receipt_id,
    handoff_semantic_sha256,
    receipt_semantic_sha256,
)
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


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value if value not in {None, ""} else default)
    except (TypeError, ValueError):
        return default


def _trading_lane(evidence_class: Any) -> str:
    value = str(evidence_class or "").lower()
    if "validated" in value and "unvalidated" not in value:
        return "validated"
    return "discovery"


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
        semantic_sha = decision_semantic_sha256(payload)
        with self.transaction() as connection:
            try:
                connection.execute(
                    "INSERT INTO decision_transactions ("
                    "decision_id,generation_id,candidate_identity,idempotency_key,stage,"
                    "terminal_state,payload_json,payload_sha256,created_at,updated_at,"
                    "identity_version,semantic_sha256) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
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
                        IDENTITY_VERSION,
                        semantic_sha,
                    ),
                )
                inserted = True
            except sqlite3.IntegrityError as exc:
                row = connection.execute(
                    "SELECT decision_id,payload_json,semantic_sha256 FROM decision_transactions "
                    "WHERE decision_id = ? OR (generation_id = ? AND candidate_identity = ?) "
                    "OR idempotency_key = ? ORDER BY CASE WHEN decision_id = ? THEN 0 ELSE 1 END "
                    "LIMIT 1",
                    (
                        transaction.decision_id,
                        transaction.generation_id,
                        transaction.candidate_identity,
                        transaction.idempotency_key,
                        transaction.decision_id,
                    ),
                ).fetchone()
                if row is None:
                    raise ControlPlaneError(
                        f"decision_unique_collision:{transaction.decision_id}"
                    ) from exc
                existing_payload = json.loads(str(row["payload_json"]))
                existing_semantic = str(row["semantic_sha256"] or "") or (
                    decision_semantic_sha256(existing_payload)
                )
                if existing_semantic != semantic_sha:
                    raise ControlPlaneError(
                        "immutable_identity_collision:decision_transactions:"
                        f"{transaction.decision_id}"
                    ) from exc
                connection.execute(
                    "UPDATE decision_transactions SET semantic_sha256 = COALESCE(semantic_sha256, ?) "
                    "WHERE decision_id = ?",
                    (existing_semantic, str(row["decision_id"])),
                )
                inserted = False
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
            self._supersede_pending_handoffs(
                connection,
                candidate_identity=transaction.candidate_identity,
                superseded_by_decision_id=transaction.decision_id,
                keep_handoff_id=None,
                keep_decision_id=transaction.decision_id,
                timestamp=transaction.updated_at,
            )
            return inserted

    def consumed_signal_history(self, *, limit: int = 500) -> list[dict[str, Any]]:
        """Return bounded immutable decision lineage for anti-churn checks."""

        with self.connect() as connection:
            rows = connection.execute(
                "SELECT d.payload_json AS decision_payload, h.payload_json AS handoff_payload, "
                "h.updated_at AS consumed_at FROM handoffs h "
                "JOIN decision_transactions d ON d.decision_id = h.decision_id "
                "WHERE h.state = 'consumed' ORDER BY h.updated_at DESC LIMIT ?",
                (max(1, min(int(limit), 5_000)),),
            ).fetchall()
        records: list[dict[str, Any]] = []
        for row in rows:
            decision = json.loads(str(row["decision_payload"]))
            handoff = json.loads(str(row["handoff_payload"]))
            records.append(
                {
                    "economic_signal_identity_id": decision.get(
                        "economic_signal_identity_id"
                    )
                    or handoff.get("economic_signal_identity_id"),
                    "evidence_digest": decision.get("evidence_digest")
                    or handoff.get("evidence_digest"),
                    "decision_id": decision.get("decision_id"),
                    "instrument": decision.get("instrument"),
                    "horizon": (decision.get("trigger") or {}).get("horizon")
                    or handoff.get("horizon"),
                    "consumed_at": row["consumed_at"],
                }
            )
        return records

    def _record_superseded_handoff(
        self,
        connection: sqlite3.Connection,
        *,
        handoff: sqlite3.Row,
        superseded_by_decision_id: str,
        reason: str,
        timestamp: str,
    ) -> bool:
        handoff_id = str(handoff["handoff_id"])
        source_sha = str(handoff["payload_sha256"])
        receipt_id = handoff_receipt_id(
            handoff_id=handoff_id,
            source_handoff_sha256=source_sha,
            receipt_type="superseded",
        )
        payload = {
            "paperops_handoff_id": handoff_id,
            "status": "superseded_before_paper_submission",
            "reason": reason,
            "superseded_by_decision_id": superseded_by_decision_id,
            "source_handoff_sha256": source_sha,
        }
        payload_text = _json(payload)
        payload_sha = _sha(payload_text)
        semantic_sha = receipt_semantic_sha256(payload)
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
                "semantic_sha256",
            ),
            values=(
                receipt_id,
                handoff_id,
                "superseded",
                payload_text,
                payload_sha,
                timestamp,
                semantic_sha,
            ),
            payload_sha256=payload_sha,
        )
        connection.execute(
            "UPDATE handoffs SET state = 'superseded', updated_at = ? "
            "WHERE handoff_id = ? AND state = 'accepted_for_paperops_review'",
            (timestamp, handoff_id),
        )
        connection.execute(
            "UPDATE projection_outbox SET status = 'published', published_at = ?, "
            "claimed_by = NULL, claimed_at = NULL, lease_expires_at = NULL, "
            "last_error = ? WHERE topic = 'paperops_handoff_accepted' "
            "AND aggregate_id = ? AND status = 'pending'",
            (
                timestamp,
                f"superseded_by_newer_decision:{superseded_by_decision_id}"[:500],
                handoff_id,
            ),
        )
        return inserted

    def _supersede_pending_handoffs(
        self,
        connection: sqlite3.Connection,
        *,
        candidate_identity: str,
        superseded_by_decision_id: str,
        keep_handoff_id: str | None,
        keep_decision_id: str | None,
        timestamp: str,
    ) -> int:
        latest = connection.execute(
            "SELECT decision_id FROM decision_transactions "
            "WHERE candidate_identity = ? ORDER BY rowid DESC LIMIT 1",
            (candidate_identity,),
        ).fetchone()
        if latest is not None and str(latest["decision_id"]) != superseded_by_decision_id:
            return 0
        params: list[Any] = [candidate_identity]
        keep_clause = ""
        if keep_handoff_id:
            keep_clause = "AND h.handoff_id != ? "
            params.append(keep_handoff_id)
        if keep_decision_id:
            keep_clause += "AND h.decision_id != ? "
            params.append(keep_decision_id)
        rows = list(
            connection.execute(
                "SELECT DISTINCT h.* FROM handoffs h LEFT JOIN projection_outbox o "
                "ON o.topic = 'paperops_handoff_accepted' "
                "AND o.aggregate_id = h.handoff_id "
                "WHERE h.candidate_identity = ? "
                "AND h.state = 'accepted_for_paperops_review' "
                f"{keep_clause}"
                "AND NOT EXISTS (SELECT 1 FROM projection_outbox active "
                "WHERE active.topic = 'paperops_handoff_accepted' "
                "AND active.aggregate_id = h.handoff_id "
                "AND active.status = 'processing') "
                "ORDER BY h.created_at,h.handoff_id",
                tuple(params),
            )
        )
        for row in rows:
            self._record_superseded_handoff(
                connection,
                handoff=row,
                superseded_by_decision_id=superseded_by_decision_id,
                reason="newer_decision_generation_replaced_pending_handoff",
                timestamp=timestamp,
            )
        return len(rows)

    def _supersede_noncurrent_pending_handoffs(
        self,
        connection: sqlite3.Connection,
        *,
        timestamp: str,
    ) -> int:
        candidates = [
            str(row["candidate_identity"])
            for row in connection.execute(
                "SELECT DISTINCT h.candidate_identity FROM handoffs h "
                "JOIN projection_outbox o ON o.aggregate_id = h.handoff_id "
                "WHERE o.topic = 'paperops_handoff_accepted' "
                "AND o.status = 'pending' "
                "AND h.state = 'accepted_for_paperops_review'"
            )
        ]
        superseded = 0
        for candidate_identity in candidates:
            latest = connection.execute(
                "SELECT decision_id FROM decision_transactions "
                "WHERE candidate_identity = ? ORDER BY rowid DESC LIMIT 1",
                (candidate_identity,),
            ).fetchone()
            if latest is None:
                continue
            latest_decision_id = str(latest["decision_id"])
            superseded += self._supersede_pending_handoffs(
                connection,
                candidate_identity=candidate_identity,
                superseded_by_decision_id=latest_decision_id,
                keep_handoff_id=None,
                keep_decision_id=latest_decision_id,
                timestamp=timestamp,
            )
        return superseded

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
        semantic_sha = handoff_semantic_sha256(payload)
        with self.transaction() as connection:
            latest = connection.execute(
                "SELECT decision_id FROM decision_transactions "
                "WHERE candidate_identity = ? ORDER BY rowid DESC LIMIT 1",
                (candidate_identity,),
            ).fetchone()
            if latest is not None and str(latest["decision_id"]) == decision_id:
                inflight = connection.execute(
                    "SELECT h.handoff_id FROM handoffs h JOIN projection_outbox o "
                    "ON o.topic = 'paperops_handoff_accepted' "
                    "AND o.aggregate_id = h.handoff_id "
                    "WHERE h.candidate_identity = ? "
                    "AND h.handoff_id != ? "
                    "AND h.state = 'accepted_for_paperops_review' "
                    "AND o.status = 'processing' LIMIT 1",
                    (candidate_identity, handoff_id),
                ).fetchone()
                if inflight is not None:
                    # Do not terminally persist the newer handoff while an older
                    # worker owns this candidate. Once that lease finishes, the
                    # same immutable generation can be accepted on its next retry.
                    return False
            try:
                connection.execute(
                    "INSERT INTO handoffs (handoff_id,decision_id,candidate_identity,"
                    "idempotency_key,state,payload_json,payload_sha256,created_at,updated_at,"
                    "identity_version,semantic_sha256) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        handoff_id,
                        decision_id,
                        candidate_identity,
                        idempotency_key,
                        "accepted_for_paperops_review",
                        payload_text,
                        payload_sha,
                        timestamp,
                        timestamp,
                        IDENTITY_VERSION,
                        semantic_sha,
                    ),
                )
                inserted = True
            except sqlite3.IntegrityError as exc:
                row = connection.execute(
                    "SELECT handoff_id,payload_json,semantic_sha256 FROM handoffs "
                    "WHERE handoff_id = ? OR idempotency_key = ? "
                    "ORDER BY CASE WHEN handoff_id = ? THEN 0 ELSE 1 END LIMIT 1",
                    (handoff_id, idempotency_key, handoff_id),
                ).fetchone()
                if row is None:
                    raise ControlPlaneError(f"handoff_unique_collision:{handoff_id}") from exc
                existing_payload = json.loads(str(row["payload_json"]))
                existing_semantic = str(row["semantic_sha256"] or "") or (
                    handoff_semantic_sha256(existing_payload)
                )
                if existing_semantic != semantic_sha:
                    raise ControlPlaneError(
                        f"immutable_identity_collision:handoffs:{handoff_id}"
                    ) from exc
                connection.execute(
                    "UPDATE handoffs SET semantic_sha256 = COALESCE(semantic_sha256, ?) "
                    "WHERE handoff_id = ?",
                    (existing_semantic, str(row["handoff_id"])),
                )
                inserted = False
            persisted_handoff_id = handoff_id
            if not inserted:
                persisted_handoff_id = str(row["handoff_id"])
            if latest is None or str(latest["decision_id"]) != decision_id:
                current = connection.execute(
                    "SELECT * FROM handoffs WHERE handoff_id = ?",
                    (persisted_handoff_id,),
                ).fetchone()
                processing = connection.execute(
                    "SELECT 1 FROM projection_outbox WHERE topic = 'paperops_handoff_accepted' "
                    "AND aggregate_id = ? AND status = 'processing'",
                    (persisted_handoff_id,),
                ).fetchone()
                if (
                    current is not None
                    and str(current["state"]) == "accepted_for_paperops_review"
                    and processing is None
                ):
                    self._record_superseded_handoff(
                        connection,
                        handoff=current,
                        superseded_by_decision_id=(
                            str(latest["decision_id"]) if latest is not None else decision_id
                        ),
                        reason="handoff_does_not_match_latest_decision_generation",
                        timestamp=timestamp,
                    )
                return inserted
            self._supersede_pending_handoffs(
                connection,
                candidate_identity=candidate_identity,
                superseded_by_decision_id=decision_id,
                keep_handoff_id=persisted_handoff_id,
                keep_decision_id=decision_id,
                timestamp=timestamp,
            )
            active = connection.execute(
                "SELECT state FROM handoffs WHERE handoff_id = ?",
                (persisted_handoff_id,),
            ).fetchone()
            if active is None or str(active["state"]) != "accepted_for_paperops_review":
                return inserted
            self._persist_handoff_risk_decision(
                connection,
                handoff_id=persisted_handoff_id,
                decision_id=decision_id,
                payload=payload,
                created_at=timestamp,
            )
            persisted = connection.execute(
                "SELECT decision_id,idempotency_key FROM handoffs WHERE handoff_id = ?",
                (persisted_handoff_id,),
            ).fetchone()
            if persisted is None:
                raise ControlPlaneError("active_handoff_missing_before_outbox")
            outbox_payload = {
                "handoff_id": persisted_handoff_id,
                "decision_id": str(persisted["decision_id"]),
                "idempotency_key": str(persisted["idempotency_key"]),
                "route": "guarded_alpaca_paper_only",
            }
            outbox_text = _json(outbox_payload)
            outbox_sha = _sha(outbox_text)
            outbox_id = sha256(
                f"paperops:{persisted_handoff_id}".encode("utf-8")
            ).hexdigest()[:32]
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
                    persisted_handoff_id,
                    outbox_text,
                    outbox_sha,
                    "pending",
                    0,
                    timestamp,
                    None,
                ),
                payload_sha256=outbox_sha,
            )
            terminal_receipt = connection.execute(
                "SELECT 1 FROM handoff_receipts WHERE handoff_id = ? "
                "AND receipt_type IN "
                "('submitted','duplicate','rejected','expired','cancelled','superseded') "
                "LIMIT 1",
                (persisted_handoff_id,),
            ).fetchone()
            if terminal_receipt is None:
                connection.execute(
                    "UPDATE projection_outbox SET status = 'pending', published_at = NULL, "
                    "claimed_by = NULL, claimed_at = NULL, lease_expires_at = NULL, "
                    "last_error = 'recovered_active_handoff_projection' "
                    "WHERE event_id = ? AND status = 'published'",
                    (outbox_id,),
                )
            return inserted

    @staticmethod
    def _persist_handoff_risk_decision(
        connection: sqlite3.Connection,
        *,
        handoff_id: str,
        decision_id: str,
        payload: Mapping[str, Any],
        created_at: str,
    ) -> bool:
        """Persist the Router-approved paper risk envelope with its handoff.

        Generic control-plane handoffs predate the operating ledger and do not
        carry a risk proposal. Current PaperOps handoffs do; accepting one
        without its risk row would leave a durable order queue that can never
        be executed after the originating Router generation rotates away.
        """

        lineage = payload.get("lineage")
        lineage = lineage if isinstance(lineage, Mapping) else {}
        source_risk_proposal_id = str(lineage.get("risk_proposal_id") or "").strip()
        is_current_paperops_handoff = (
            str(payload.get("schema_version") or "")
            == "qadam_router_v3_paperops.v1"
        )
        if not source_risk_proposal_id:
            if is_current_paperops_handoff:
                raise ControlPlaneError(
                    f"accepted_handoff_risk_proposal_missing:{handoff_id}"
                )
            return False
        risk_decision_id = canonical_risk_decision_id(
            source_risk_proposal_id=source_risk_proposal_id,
            decision_id=decision_id,
        )

        proposed_notional = _float(payload.get("proposed_notional_usd"))
        maximum_loss = _float(payload.get("maximum_loss_at_invalidation"))
        source_quorum = payload.get("source_quorum")
        source_quorum = source_quorum if isinstance(source_quorum, Mapping) else {}
        hard_errors: list[str] = []
        if proposed_notional <= 0 or proposed_notional > 5_000:
            hard_errors.append("approved_notional_outside_paper_risk_envelope")
        if maximum_loss <= 0:
            hard_errors.append("maximum_loss_at_invalidation_missing")
        if payload.get("duplicate_exposure_conflict") is not False:
            hard_errors.append("duplicate_exposure_not_cleared")
        if payload.get("drawdown_context_complete") is not True:
            hard_errors.append("drawdown_context_incomplete")
        if payload.get("drawdown_breached") is not False:
            hard_errors.append("drawdown_limit_breached")
        if payload.get("source_quorum_passed") is not True and source_quorum.get(
            "passed"
        ) is not True:
            hard_errors.append("source_quorum_not_passed")
        if payload.get("instrument_paperable") is not True:
            hard_errors.append("instrument_not_paperable")
        if payload.get("qctrl_state") not in {"pass", "passed", "not_required"}:
            hard_errors.append("qctrl_not_passed")
        if payload.get("route") != "guarded_alpaca_paper_via_paperops":
            hard_errors.append("guarded_paper_route_missing")
        if payload.get("live_capital_enabled") is not False:
            hard_errors.append("live_capital_boundary_invalid")
        if hard_errors:
            raise ControlPlaneError(
                "accepted_handoff_risk_invalid:"
                + handoff_id
                + ":"
                + ",".join(hard_errors)
            )

        evidence_class = str(payload.get("evidence_class") or "unclassified")
        trading_lane = _trading_lane(evidence_class)
        state = (
            "validated_paper_review_candidate"
            if trading_lane == "validated"
            else "experimental_paper_review_candidate"
        )
        risk_payload = {
            "risk_decision_id": risk_decision_id,
            "risk_proposal_id": source_risk_proposal_id,
            "source_risk_proposal_id": source_risk_proposal_id,
            "decision_id": decision_id,
            "hypothesis_id": payload.get("hypothesis_id")
            or lineage.get("hypothesis_id"),
            "proposed_notional_usd": proposed_notional,
            "approved_notional_usd": proposed_notional,
            "maximum_loss_at_invalidation": maximum_loss,
            "portfolio_level_controls": {
                "duplicate_exposure_conflict": payload.get(
                    "duplicate_exposure_conflict"
                ),
                "drawdown_context_complete": payload.get(
                    "drawdown_context_complete"
                ),
                "drawdown_breached": payload.get("drawdown_breached"),
                "hard_ceiling_usd": 5_000.0,
            },
            "paper_only": True,
            "live_capital_enabled": False,
        }
        payload_text = _json(risk_payload)
        payload_sha = _sha(payload_text)
        existing = connection.execute(
            "SELECT decision_id,payload_sha256 FROM risk_decisions "
            "WHERE risk_decision_id = ?",
            (risk_decision_id,),
        ).fetchone()
        if existing is not None:
            if (
                str(existing["decision_id"]) != decision_id
                or str(existing["payload_sha256"]) != payload_sha
            ):
                raise ControlPlaneError(
                    f"immutable_identity_collision:risk_decisions:{risk_decision_id}"
                )
            return False
        connection.execute(
            "INSERT INTO risk_decisions (risk_decision_id,decision_id,trading_lane,"
            "state,proposed_notional,approved_notional,payload_json,payload_sha256,"
            "created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                risk_decision_id,
                decision_id,
                trading_lane,
                state,
                proposed_notional,
                proposed_notional,
                payload_text,
                payload_sha,
                created_at,
            ),
        )
        return True

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
        semantic_sha = receipt_semantic_sha256(payload)
        with self.transaction() as connection:
            try:
                connection.execute(
                    "INSERT INTO handoff_receipts (receipt_id,handoff_id,receipt_type,"
                    "payload_json,payload_sha256,created_at,semantic_sha256) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (
                        receipt_id,
                        handoff_id,
                        receipt_type,
                        payload_text,
                        payload_sha,
                        timestamp,
                        semantic_sha,
                    ),
                )
                inserted = True
            except sqlite3.IntegrityError as exc:
                row = connection.execute(
                    "SELECT payload_json,semantic_sha256 FROM handoff_receipts "
                    "WHERE receipt_id = ?",
                    (receipt_id,),
                ).fetchone()
                if row is None:
                    raise ControlPlaneError(f"handoff_receipt_collision:{receipt_id}") from exc
                existing_payload = json.loads(str(row["payload_json"]))
                existing_semantic = str(row["semantic_sha256"] or "") or (
                    receipt_semantic_sha256(existing_payload)
                )
                if existing_semantic != semantic_sha:
                    raise ControlPlaneError(
                        f"immutable_identity_collision:handoff_receipts:{receipt_id}"
                    ) from exc
                connection.execute(
                    "UPDATE handoff_receipts SET semantic_sha256 = COALESCE(semantic_sha256, ?) "
                    "WHERE receipt_id = ?",
                    (existing_semantic, receipt_id),
                )
                inserted = False
            if inserted and receipt_type in {
                "consumed",
                "submitted",
                "duplicate",
                "rejected",
                "expired",
                "cancelled",
                "superseded",
            }:
                new_state = {
                    "consumed": "consumed",
                    "submitted": "consumed",
                    "duplicate": "duplicate",
                    "rejected": "rejected",
                    "expired": "expired",
                    "cancelled": "cancelled",
                    "superseded": "superseded",
                }[receipt_type]
                connection.execute(
                    "UPDATE handoffs SET state = ?, updated_at = ? WHERE handoff_id = ?",
                    (new_state, timestamp, handoff_id),
                )
                if receipt_type in {
                    "submitted",
                    "duplicate",
                    "rejected",
                    "expired",
                    "cancelled",
                    "superseded",
                }:
                    connection.execute(
                        "UPDATE projection_outbox SET status = 'published', "
                        "published_at = ?, claimed_by = NULL, claimed_at = NULL, "
                        "lease_expires_at = NULL WHERE topic = 'paperops_handoff_accepted' "
                        "AND aggregate_id = ? AND status != 'published'",
                        (timestamp, handoff_id),
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

    def expire_stale_handoffs(self, *, max_age_seconds: int = 900) -> int:
        """Close unsubmitted handoffs whose decision-time context is no longer fresh."""

        if max_age_seconds < 1:
            raise ValueError("handoff_max_age_seconds_invalid")
        now = datetime.now(timezone.utc)
        expired_count = 0
        with self.transaction() as connection:
            rows = list(
                connection.execute(
                    "SELECT handoff_id,payload_json,payload_sha256,created_at FROM handoffs "
                    "WHERE state = 'accepted_for_paperops_review'"
                )
            )
            for row in rows:
                source_payload = json.loads(str(row["payload_json"]))
                source_timestamp = source_payload.get("expires_at") or source_payload.get(
                    "generated_at"
                )
                if not source_timestamp:
                    # Legacy records without decision-time metadata remain visible for
                    # explicit reconciliation rather than being guessed stale.
                    continue
                try:
                    created = datetime.fromisoformat(
                        str(source_timestamp).replace("Z", "+00:00")
                    )
                    if created.tzinfo is None:
                        created = created.replace(tzinfo=timezone.utc)
                except ValueError:
                    created = datetime.min.replace(tzinfo=timezone.utc)
                expires_at = source_payload.get("expires_at")
                if expires_at:
                    is_expired = now >= created.astimezone(timezone.utc)
                else:
                    is_expired = (
                        now - created.astimezone(timezone.utc)
                    ).total_seconds() > max_age_seconds
                if not is_expired:
                    continue
                handoff_id = str(row["handoff_id"])
                source_sha = str(row["payload_sha256"])
                receipt_id = handoff_receipt_id(
                    handoff_id=handoff_id,
                    source_handoff_sha256=source_sha,
                    receipt_type="expired",
                )
                receipt_payload = {
                    "paperops_handoff_id": handoff_id,
                    "status": "expired_before_paper_submission",
                    "reason": "decision_time_context_expired",
                    "source_handoff_sha256": source_sha,
                }
                receipt_text = _json(receipt_payload)
                receipt_sha = _sha(receipt_text)
                receipt_semantic = receipt_semantic_sha256(receipt_payload)
                connection.execute(
                    "INSERT OR IGNORE INTO handoff_receipts "
                    "(receipt_id,handoff_id,receipt_type,payload_json,payload_sha256,created_at,"
                    "semantic_sha256) VALUES (?,?,?,?,?,?,?)",
                    (
                        receipt_id,
                        handoff_id,
                        "expired",
                        receipt_text,
                        receipt_sha,
                        now.isoformat(),
                        receipt_semantic,
                    ),
                )
                connection.execute(
                    "UPDATE handoffs SET state = 'expired', updated_at = ? WHERE handoff_id = ?",
                    (now.isoformat(), handoff_id),
                )
                connection.execute(
                    "UPDATE projection_outbox SET status = 'published', published_at = ?, "
                    "claimed_by = NULL, claimed_at = NULL, lease_expires_at = NULL "
                    "WHERE topic = 'paperops_handoff_accepted' AND aggregate_id = ? "
                    "AND status != 'published'",
                    (now.isoformat(), handoff_id),
                )
                expired_count += 1
        return expired_count

    def write_paperops_projections(
        self,
        *,
        accepted_path: Path,
        receipts_path: Path,
    ) -> dict[str, Any]:
        connection = self.connect()
        try:
            handoff_rows = list(
                connection.execute(
                    "SELECT handoff_id,payload_json,created_at FROM handoffs "
                    "WHERE state = 'accepted_for_paperops_review' ORDER BY created_at, handoff_id"
                )
            )
            accepted_rows = []
            for row in handoff_rows:
                source = json.loads(str(row["payload_json"]))
                receipt = connection.execute(
                    "SELECT receipt_id,created_at FROM handoff_receipts WHERE handoff_id = ? "
                    "AND receipt_type = 'accepted_for_guarded_paperops_sequence' "
                    "ORDER BY created_at DESC, receipt_id DESC LIMIT 1",
                    (str(row["handoff_id"]),),
                ).fetchone()
                accepted_rows.append(
                    {
                        "schema_version": source.get(
                            "schema_version", "qadam_router_v3_paperops.v1"
                        ),
                        "artifact_type": "qadam_paperops_handoff_v3_accepted",
                        "phase_id": source.get("phase_id", "OR-15"),
                        "generated_at": (
                            str(receipt["created_at"])
                            if receipt is not None
                            else str(row["created_at"])
                        ),
                        "consumption_receipt_id": (
                            str(receipt["receipt_id"]) if receipt is not None else None
                        ),
                        "source_handoff_sha256": _sha(_json(source)),
                        "source_handoff": source,
                        "paper_order_created": False,
                        "broker_write_count": 0,
                        "proof_credit_allowed": False,
                        "authority": source.get("authority", {}),
                    }
                )
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
        return {
            "accepted": len(accepted_rows),
            "receipts": len(receipt_rows),
            "accepted_handoff_ids": [
                str(record.get("source_handoff", {}).get("paperops_handoff_id") or "")
                for record in accepted_rows
                if str(record.get("source_handoff", {}).get("paperops_handoff_id") or "")
            ],
        }

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

    def record_broker_submission(
        self,
        *,
        receipt_id: str,
        handoff_id: str,
        receipt_payload: Mapping[str, Any],
        broker_event_id: str,
        broker_order_id: str | None,
        broker_event_payload: Mapping[str, Any],
        created_at: str | None = None,
    ) -> dict[str, bool]:
        """Commit a successful paper submission and close its outbox atomically."""

        timestamp = created_at or _now_iso()
        receipt_text = _json(receipt_payload)
        receipt_sha = _sha(receipt_text)
        receipt_semantic = receipt_semantic_sha256(receipt_payload)
        broker_text = _json(broker_event_payload)
        broker_sha = _sha(broker_text)
        with self.transaction() as connection:
            handoff = connection.execute(
                "SELECT state FROM handoffs WHERE handoff_id = ?",
                (handoff_id,),
            ).fetchone()
            if handoff is None:
                raise ControlPlaneError(f"submitted_handoff_missing:{handoff_id}")
            try:
                connection.execute(
                    "INSERT INTO handoff_receipts (receipt_id,handoff_id,receipt_type,"
                    "payload_json,payload_sha256,created_at,semantic_sha256) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (
                        receipt_id,
                        handoff_id,
                        "submitted",
                        receipt_text,
                        receipt_sha,
                        timestamp,
                        receipt_semantic,
                    ),
                )
                receipt_inserted = True
            except sqlite3.IntegrityError as exc:
                existing = connection.execute(
                    "SELECT payload_json,semantic_sha256 FROM handoff_receipts "
                    "WHERE receipt_id = ?",
                    (receipt_id,),
                ).fetchone()
                if existing is None:
                    raise ControlPlaneError(
                        f"handoff_receipt_collision:{receipt_id}"
                    ) from exc
                existing_payload = json.loads(str(existing["payload_json"]))
                existing_semantic = str(existing["semantic_sha256"] or "") or (
                    receipt_semantic_sha256(existing_payload)
                )
                if existing_semantic != receipt_semantic:
                    raise ControlPlaneError(
                        f"immutable_identity_collision:handoff_receipts:{receipt_id}"
                    ) from exc
                receipt_inserted = False
            broker_inserted = self._insert_immutable(
                connection,
                table="broker_events",
                identity_column="event_id",
                identity=broker_event_id,
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
                    broker_event_id,
                    handoff_id,
                    broker_order_id,
                    "submitted",
                    broker_text,
                    broker_sha,
                    timestamp,
                ),
                payload_sha256=broker_sha,
            )
            connection.execute(
                "UPDATE handoffs SET state = 'consumed', updated_at = ? "
                "WHERE handoff_id = ?",
                (timestamp, handoff_id),
            )
            connection.execute(
                "UPDATE projection_outbox SET status = 'published', published_at = ?, "
                "claimed_by = NULL, claimed_at = NULL, lease_expires_at = NULL "
                "WHERE topic = 'paperops_handoff_accepted' AND aggregate_id = ? "
                "AND status != 'published'",
                (timestamp, handoff_id),
            )
            return {
                "receipt_inserted": receipt_inserted,
                "broker_event_inserted": broker_inserted,
            }

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
        self.recover_expired_outbox_leases()
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

    def pending_handoffs(self) -> list[dict[str, Any]]:
        """Return the authoritative unsubmitted handoff queue."""

        connection = self.connect()
        try:
            return [
                self._decode_row(row)
                for row in connection.execute(
                    "SELECT h.* FROM handoffs h JOIN projection_outbox o "
                    "ON o.aggregate_id = h.handoff_id "
                    "WHERE o.topic = 'paperops_handoff_accepted' "
                    "AND o.status IN ('pending','processing') "
                    "AND h.state = 'accepted_for_paperops_review' "
                    "ORDER BY h.created_at,h.handoff_id"
                )
            ]
        finally:
            connection.close()

    def ensure_pending_handoff_risk_decisions(self) -> dict[str, int]:
        """Repair risk lineage for every durable, unsubmitted paper handoff.

        This is intentionally driven by the SQLite outbox rather than the
        current Router projection. A handoff can remain valid after its source
        generation rotates, and restart recovery must not depend on replaying
        that older in-memory generation.
        """

        checked = 0
        inserted = 0
        with self.transaction() as connection:
            rows = connection.execute(
                "SELECT h.handoff_id,h.decision_id,h.payload_json "
                "FROM handoffs h JOIN projection_outbox o "
                "ON o.aggregate_id = h.handoff_id "
                "WHERE o.topic = 'paperops_handoff_accepted' "
                "AND o.status IN ('pending','processing') "
                "AND h.state = 'accepted_for_paperops_review' "
                "ORDER BY h.created_at,h.handoff_id"
            ).fetchall()
            for row in rows:
                payload = json.loads(str(row["payload_json"]))
                if not isinstance(payload, dict):
                    raise ControlPlaneError(
                        f"accepted_handoff_payload_invalid:{row['handoff_id']}"
                    )
                checked += 1
                inserted += int(
                    self._persist_handoff_risk_decision(
                        connection,
                        handoff_id=str(row["handoff_id"]),
                        decision_id=str(row["decision_id"]),
                        payload=payload,
                        created_at=str(payload.get("generated_at") or _now_iso()),
                    )
                )
        return {
            "checked_handoff_count": checked,
            "inserted_risk_decision_count": inserted,
        }

    def get_handoff(self, handoff_id: str) -> dict[str, Any] | None:
        connection = self.connect()
        try:
            row = connection.execute(
                "SELECT * FROM handoffs WHERE handoff_id = ?",
                (handoff_id,),
            ).fetchone()
            return self._decode_row(row) if row is not None else None
        finally:
            connection.close()

    def recover_expired_outbox_leases(self) -> int:
        """Return abandoned PaperOps work to the queue after its bounded lease."""

        timestamp = _now_iso()
        with self.transaction() as connection:
            cursor = connection.execute(
                "UPDATE projection_outbox SET status = 'pending', claimed_by = NULL, "
                "claimed_at = NULL, lease_expires_at = NULL, "
                "last_error = COALESCE(last_error, 'expired_worker_lease_recovered') "
                "WHERE status = 'processing' AND lease_expires_at IS NOT NULL "
                "AND lease_expires_at <= ?",
                (timestamp,),
            )
            self._supersede_noncurrent_pending_handoffs(
                connection,
                timestamp=timestamp,
            )
            return int(cursor.rowcount)

    def claim_outbox(
        self,
        *,
        topic: str,
        worker_id: str,
        aggregate_id: str | None = None,
        lease_seconds: int = 300,
    ) -> dict[str, Any] | None:
        """Lease one handoff atomically so concurrent workers cannot double-submit it."""

        if not worker_id:
            raise ValueError("outbox_worker_id_missing")
        if lease_seconds < 1:
            raise ValueError("outbox_lease_seconds_invalid")
        now = datetime.now(timezone.utc)
        claimed_at = now.isoformat()
        lease_expires_at = (now + timedelta(seconds=lease_seconds)).isoformat()
        with self.transaction() as connection:
            connection.execute(
                "UPDATE projection_outbox SET status = 'pending', claimed_by = NULL, "
                "claimed_at = NULL, lease_expires_at = NULL, "
                "last_error = COALESCE(last_error, 'expired_worker_lease_recovered') "
                "WHERE status = 'processing' AND lease_expires_at IS NOT NULL "
                "AND lease_expires_at <= ?",
                (claimed_at,),
            )
            query = "SELECT o.* FROM projection_outbox o"
            if topic == "paperops_handoff_accepted":
                query += (
                    " JOIN handoffs h ON h.handoff_id = o.aggregate_id "
                    "AND h.state = 'accepted_for_paperops_review'"
                )
            query += " WHERE o.topic = ? AND o.status = 'pending'"
            params: list[Any] = [topic]
            if aggregate_id:
                query += " AND o.aggregate_id = ?"
                params.append(aggregate_id)
            query += " ORDER BY o.created_at,o.event_id LIMIT 1"
            row = connection.execute(query, tuple(params)).fetchone()
            if row is None:
                return None
            cursor = connection.execute(
                "UPDATE projection_outbox SET status = 'processing', attempts = attempts + 1, "
                "claimed_by = ?, claimed_at = ?, lease_expires_at = ?, last_error = NULL "
                "WHERE event_id = ? AND status = 'pending'",
                (worker_id, claimed_at, lease_expires_at, str(row["event_id"])),
            )
            if cursor.rowcount != 1:
                return None
            claimed = connection.execute(
                "SELECT * FROM projection_outbox WHERE event_id = ?",
                (str(row["event_id"]),),
            ).fetchone()
            return self._decode_row(claimed) if claimed is not None else None

    def release_outbox_claim(self, event_id: str, *, error: str) -> bool:
        """Release failed work for a later safe retry without losing its identity."""

        with self.transaction() as connection:
            cursor = connection.execute(
                "UPDATE projection_outbox SET status = 'pending', claimed_by = NULL, "
                "claimed_at = NULL, lease_expires_at = NULL, last_error = ? "
                "WHERE event_id = ? AND status = 'processing'",
                (str(error)[:500], event_id),
            )
            if cursor.rowcount not in {0, 1}:
                raise ControlPlaneError("outbox_release_rowcount_invalid")
            self._supersede_noncurrent_pending_handoffs(
                connection,
                timestamp=_now_iso(),
            )
            return cursor.rowcount == 1

    def mark_outbox_published(self, event_id: str) -> None:
        with self.transaction() as connection:
            cursor = connection.execute(
                "UPDATE projection_outbox SET status = 'published', "
                "published_at = ?, claimed_by = NULL, claimed_at = NULL, "
                "lease_expires_at = NULL WHERE event_id = ? "
                "AND status IN ('pending','processing')",
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
            "hypotheses",
            "risk_decisions",
            "exit_plans",
            "canonical_orders",
            "fills",
            "positions",
            "outcomes",
            "strategy_cohorts",
            "reconciliation_runs",
            "liveness_cycles",
            "execution_owner_leases",
            "execution_state",
            "operating_events",
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
            applied_schema_version = max(
                (int(row["version"]) for row in migrations),
                default=0,
            )
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
                    "hypotheses",
                    "risk_decisions",
                    "exit_plans",
                    "canonical_orders",
                    "fills",
                    "positions",
                    "outcomes",
                    "strategy_cohorts",
                    "reconciliation_runs",
                    "liveness_cycles",
                    "execution_owner_leases",
                    "operating_events",
                )
            }
            consistency_counts = {
                "v2_decision_semantic_hash_missing": int(
                    connection.execute(
                        "SELECT COUNT(*) FROM decision_transactions "
                        "WHERE identity_version = ? AND "
                        "(semantic_sha256 IS NULL OR semantic_sha256 = '')",
                        (IDENTITY_VERSION,),
                    ).fetchone()[0]
                ),
                "v2_handoff_semantic_hash_missing": int(
                    connection.execute(
                        "SELECT COUNT(*) FROM handoffs WHERE identity_version = ? AND "
                        "(semantic_sha256 IS NULL OR semantic_sha256 = '')",
                        (IDENTITY_VERSION,),
                    ).fetchone()[0]
                ),
                "accepted_handoff_without_active_outbox": int(
                    connection.execute(
                        "SELECT COUNT(*) FROM handoffs h LEFT JOIN projection_outbox o "
                        "ON o.topic = 'paperops_handoff_accepted' "
                        "AND o.aggregate_id = h.handoff_id "
                        "AND o.status IN ('pending','processing') "
                        "WHERE h.state = 'accepted_for_paperops_review' "
                        "AND o.event_id IS NULL"
                    ).fetchone()[0]
                ),
                "active_outbox_without_accepted_handoff": int(
                    connection.execute(
                        "SELECT COUNT(*) FROM projection_outbox o LEFT JOIN handoffs h "
                        "ON h.handoff_id = o.aggregate_id "
                        "WHERE o.topic = 'paperops_handoff_accepted' "
                        "AND o.status IN ('pending','processing') "
                        "AND (h.handoff_id IS NULL OR "
                        "h.state != 'accepted_for_paperops_review')"
                    ).fetchone()[0]
                ),
                "expired_processing_lease": int(
                    connection.execute(
                        "SELECT COUNT(*) FROM projection_outbox WHERE status = 'processing' "
                        "AND lease_expires_at IS NOT NULL AND lease_expires_at <= ?",
                        (_now_iso(),),
                    ).fetchone()[0]
                ),
                "submitted_receipt_without_broker_event": int(
                    connection.execute(
                        "SELECT COUNT(*) FROM handoff_receipts r "
                        "LEFT JOIN broker_events b ON b.handoff_id = r.handoff_id "
                        "AND b.event_type = 'submitted' "
                        "WHERE r.receipt_type = 'submitted' AND b.event_id IS NULL"
                    ).fetchone()[0]
                ),
                "multiple_submitted_receipts_per_handoff": int(
                    connection.execute(
                        "SELECT COUNT(*) FROM (SELECT handoff_id FROM handoff_receipts "
                        "WHERE receipt_type = 'submitted' GROUP BY handoff_id HAVING COUNT(*) > 1)"
                    ).fetchone()[0]
                ),
                "multiple_active_handoffs_per_candidate": int(
                    connection.execute(
                        "SELECT COUNT(*) FROM (SELECT candidate_identity FROM handoffs "
                        "WHERE state = 'accepted_for_paperops_review' "
                        "GROUP BY candidate_identity HAVING COUNT(*) > 1)"
                    ).fetchone()[0]
                ),
                "multiple_active_outboxes_per_candidate": int(
                    connection.execute(
                        "SELECT COUNT(*) FROM (SELECT h.candidate_identity FROM handoffs h "
                        "JOIN projection_outbox o ON o.aggregate_id = h.handoff_id "
                        "WHERE o.topic = 'paperops_handoff_accepted' "
                        "AND o.status IN ('pending','processing') "
                        "GROUP BY h.candidate_identity HAVING COUNT(*) > 1)"
                    ).fetchone()[0]
                ),
                "canonical_order_without_exit_plan": int(
                    connection.execute(
                        "SELECT COUNT(*) FROM canonical_orders o "
                        "LEFT JOIN exit_plans e ON e.exit_plan_id=o.exit_plan_id "
                        "WHERE e.exit_plan_id IS NULL"
                    ).fetchone()[0]
                ),
                "active_position_without_exit_plan": int(
                    connection.execute(
                        "SELECT COUNT(*) FROM positions p "
                        "LEFT JOIN exit_plans e ON e.exit_plan_id=p.exit_plan_id "
                        "WHERE p.state='open' AND e.exit_plan_id IS NULL"
                    ).fetchone()[0]
                ),
                "multiple_active_orders_per_instrument": int(
                    connection.execute(
                        "SELECT COUNT(*) FROM (SELECT instrument FROM canonical_orders "
                        "WHERE state IN ('prepared','submitting','submitted','accepted',"
                        "'partially_filled') GROUP BY instrument HAVING COUNT(*) > 1)"
                    ).fetchone()[0]
                ),
                "multiple_canonical_orders_per_broker_identity": int(
                    connection.execute(
                        "SELECT COUNT(*) FROM (SELECT broker_order_id_hash "
                        "FROM canonical_orders WHERE broker_order_id_hash IS NOT NULL "
                        "AND broker_order_id_hash != '' GROUP BY broker_order_id_hash "
                        "HAVING COUNT(*) > 1)"
                    ).fetchone()[0]
                ),
                "multiple_active_execution_leases": int(
                    connection.execute(
                        "SELECT CASE WHEN COUNT(*) > 1 THEN COUNT(*) ELSE 0 END "
                        "FROM execution_owner_leases WHERE state='active' "
                        "AND expires_at > ?",
                        (_now_iso(),),
                    ).fetchone()[0]
                ),
                "execution_state_missing": int(
                    connection.execute(
                        "SELECT CASE WHEN COUNT(*)=1 THEN 0 ELSE 1 END FROM execution_state "
                        "WHERE state_id='canonical_paper_execution'"
                    ).fetchone()[0]
                ),
            }
            blockers: list[str] = []
            if integrity != "ok":
                blockers.append("sqlite_integrity_check_failed")
            if foreign_keys:
                blockers.append("foreign_key_integrity_failed")
            if applied_schema_version != SCHEMA_VERSION:
                blockers.append("database_schema_version_not_current")
            blockers.extend(
                key for key, value in consistency_counts.items() if int(value) > 0
            )
            return {
                "schema_version": "qadam_control_plane_integrity.v1",
                "generated_at": _now_iso(),
                "database_path": str(self.path),
                "database_schema_version": SCHEMA_VERSION,
                "applied_database_schema_version": applied_schema_version,
                "integrity_check": integrity,
                "foreign_key_error_count": len(foreign_keys),
                "foreign_key_errors": foreign_keys,
                "migrations": migrations,
                "counts": counts,
                "consistency_counts": consistency_counts,
                "blockers": sorted(set(blockers)),
                "blocker_count": len(set(blockers)),
                "status": "passed" if not blockers else "blocked",
                "execution_frozen": bool(
                    connection.execute(
                        "SELECT frozen FROM execution_state "
                        "WHERE state_id='canonical_paper_execution'"
                    ).fetchone()[0]
                ),
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
