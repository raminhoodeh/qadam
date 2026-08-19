"""Versioned SQLite migrations for Qadam's canonical control plane."""

from __future__ import annotations

SCHEMA_VERSION = 1

MIGRATIONS: tuple[tuple[int, str], ...] = (
    (
        1,
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL,
            checksum TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS decision_transactions (
            decision_id TEXT PRIMARY KEY,
            generation_id TEXT NOT NULL,
            candidate_identity TEXT NOT NULL,
            idempotency_key TEXT NOT NULL,
            stage TEXT NOT NULL,
            terminal_state TEXT,
            payload_json TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (generation_id, candidate_identity),
            UNIQUE (idempotency_key)
        );

        CREATE TABLE IF NOT EXISTS decision_events (
            event_id TEXT PRIMARY KEY,
            decision_id TEXT NOT NULL,
            sequence INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (decision_id) REFERENCES decision_transactions(decision_id),
            UNIQUE (decision_id, sequence)
        );

        CREATE TABLE IF NOT EXISTS gate_decisions (
            gate_decision_id TEXT PRIMARY KEY,
            decision_id TEXT NOT NULL,
            gate_name TEXT NOT NULL,
            sequence INTEGER NOT NULL,
            state TEXT NOT NULL,
            severity TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (decision_id) REFERENCES decision_transactions(decision_id),
            UNIQUE (decision_id, gate_name, sequence)
        );

        CREATE TABLE IF NOT EXISTS handoffs (
            handoff_id TEXT PRIMARY KEY,
            decision_id TEXT NOT NULL,
            candidate_identity TEXT NOT NULL,
            idempotency_key TEXT NOT NULL UNIQUE,
            state TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (decision_id) REFERENCES decision_transactions(decision_id)
        );

        CREATE TABLE IF NOT EXISTS handoff_receipts (
            receipt_id TEXT PRIMARY KEY,
            handoff_id TEXT NOT NULL,
            receipt_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (handoff_id) REFERENCES handoffs(handoff_id)
        );

        CREATE TABLE IF NOT EXISTS broker_events (
            event_id TEXT PRIMARY KEY,
            handoff_id TEXT,
            broker_order_id TEXT,
            event_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (handoff_id) REFERENCES handoffs(handoff_id)
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uq_broker_event_identity
            ON broker_events (broker_order_id, event_type, payload_sha256)
            WHERE broker_order_id IS NOT NULL;

        CREATE TABLE IF NOT EXISTS lifecycle_events (
            event_id TEXT PRIMARY KEY,
            trade_id TEXT NOT NULL,
            handoff_id TEXT,
            lifecycle_state TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (handoff_id) REFERENCES handoffs(handoff_id)
        );

        CREATE TABLE IF NOT EXISTS service_runs (
            run_id TEXT PRIMARY KEY,
            service_id TEXT NOT NULL,
            domain TEXT NOT NULL,
            status TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS repair_requests (
            request_id TEXT PRIMARY KEY,
            domain TEXT NOT NULL,
            fingerprint TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS projection_outbox (
            event_id TEXT PRIMARY KEY,
            topic TEXT NOT NULL,
            aggregate_id TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            attempts INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            published_at TEXT
        );

        CREATE TABLE IF NOT EXISTS legacy_imports (
            import_id TEXT PRIMARY KEY,
            source_path TEXT NOT NULL,
            source_sha256 TEXT NOT NULL UNIQUE,
            record_count INTEGER NOT NULL,
            imported_at TEXT NOT NULL,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS projection_offsets (
            projection_name TEXT PRIMARY KEY,
            last_outbox_event_id TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE VIEW IF NOT EXISTS current_handoffs AS
        SELECT h.* FROM handoffs h;

        CREATE VIEW IF NOT EXISTS current_decisions AS
        SELECT d.* FROM decision_transactions d;
        """,
    ),
)
