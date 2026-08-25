"""Versioned SQLite migrations for Qadam's canonical control plane."""

from __future__ import annotations

SCHEMA_VERSION = 4

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
    (
        2,
        """
        ALTER TABLE decision_transactions
            ADD COLUMN identity_version TEXT NOT NULL DEFAULT 'legacy-v1';
        ALTER TABLE decision_transactions
            ADD COLUMN semantic_sha256 TEXT;

        ALTER TABLE handoffs
            ADD COLUMN identity_version TEXT NOT NULL DEFAULT 'legacy-v1';
        ALTER TABLE handoffs
            ADD COLUMN semantic_sha256 TEXT;

        ALTER TABLE handoff_receipts
            ADD COLUMN semantic_sha256 TEXT;

        ALTER TABLE projection_outbox
            ADD COLUMN claimed_by TEXT;
        ALTER TABLE projection_outbox
            ADD COLUMN claimed_at TEXT;
        ALTER TABLE projection_outbox
            ADD COLUMN lease_expires_at TEXT;
        ALTER TABLE projection_outbox
            ADD COLUMN last_error TEXT;

        CREATE INDEX IF NOT EXISTS ix_projection_outbox_dispatch
            ON projection_outbox (topic, status, created_at, event_id);
        CREATE INDEX IF NOT EXISTS ix_handoffs_state
            ON handoffs (state, created_at, handoff_id);
        """,
    ),
    (
        3,
        """
        CREATE TABLE IF NOT EXISTS hypotheses (
            hypothesis_id TEXT PRIMARY KEY,
            generation_id TEXT NOT NULL,
            research_goal_id TEXT NOT NULL,
            strategy_id TEXT NOT NULL,
            strategy_version TEXT NOT NULL,
            instrument TEXT NOT NULL,
            direction TEXT NOT NULL,
            trading_lane TEXT NOT NULL,
            state TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (generation_id, hypothesis_id)
        );

        CREATE TABLE IF NOT EXISTS risk_decisions (
            risk_decision_id TEXT PRIMARY KEY,
            decision_id TEXT NOT NULL,
            trading_lane TEXT NOT NULL,
            state TEXT NOT NULL,
            proposed_notional REAL NOT NULL,
            approved_notional REAL NOT NULL,
            payload_json TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (decision_id) REFERENCES decision_transactions(decision_id)
        );

        CREATE TABLE IF NOT EXISTS exit_plans (
            exit_plan_id TEXT PRIMARY KEY,
            decision_id TEXT,
            handoff_id TEXT,
            instrument TEXT NOT NULL,
            side TEXT NOT NULL,
            stop_price REAL NOT NULL,
            take_profit_price REAL NOT NULL,
            maximum_holding_sessions INTEGER NOT NULL,
            invalidation TEXT NOT NULL,
            state TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (decision_id) REFERENCES decision_transactions(decision_id),
            FOREIGN KEY (handoff_id) REFERENCES handoffs(handoff_id)
        );

        CREATE TABLE IF NOT EXISTS canonical_orders (
            order_key TEXT PRIMARY KEY,
            handoff_id TEXT,
            decision_id TEXT,
            exit_plan_id TEXT NOT NULL,
            instrument TEXT NOT NULL,
            side TEXT NOT NULL,
            quantity REAL NOT NULL,
            trading_lane TEXT NOT NULL,
            state TEXT NOT NULL,
            broker_order_id_hash TEXT,
            payload_json TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (handoff_id) REFERENCES handoffs(handoff_id),
            FOREIGN KEY (decision_id) REFERENCES decision_transactions(decision_id),
            FOREIGN KEY (exit_plan_id) REFERENCES exit_plans(exit_plan_id)
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uq_canonical_active_entry_exposure
            ON canonical_orders (instrument)
            WHERE state IN ('prepared', 'submitting', 'submitted', 'accepted', 'partially_filled');

        CREATE TABLE IF NOT EXISTS fills (
            fill_id TEXT PRIMARY KEY,
            order_key TEXT NOT NULL,
            quantity REAL NOT NULL,
            price REAL NOT NULL,
            occurred_at TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (order_key) REFERENCES canonical_orders(order_key)
        );

        CREATE TABLE IF NOT EXISTS positions (
            position_key TEXT PRIMARY KEY,
            instrument TEXT NOT NULL,
            decision_id TEXT,
            handoff_id TEXT,
            exit_plan_id TEXT,
            trading_lane TEXT NOT NULL,
            quantity REAL NOT NULL,
            average_entry_price REAL,
            current_price REAL,
            unrealized_pnl REAL NOT NULL,
            state TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            opened_at TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (decision_id) REFERENCES decision_transactions(decision_id),
            FOREIGN KEY (handoff_id) REFERENCES handoffs(handoff_id),
            FOREIGN KEY (exit_plan_id) REFERENCES exit_plans(exit_plan_id)
        );

        CREATE TABLE IF NOT EXISTS outcomes (
            outcome_id TEXT PRIMARY KEY,
            position_key TEXT,
            decision_id TEXT,
            strategy_id TEXT NOT NULL,
            strategy_version TEXT NOT NULL,
            trading_lane TEXT NOT NULL,
            state TEXT NOT NULL,
            realized_pnl REAL,
            no_trade_return REAL,
            benchmark_return REAL,
            payload_json TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            FOREIGN KEY (position_key) REFERENCES positions(position_key),
            FOREIGN KEY (decision_id) REFERENCES decision_transactions(decision_id)
        );

        CREATE TABLE IF NOT EXISTS strategy_cohorts (
            cohort_id TEXT PRIMARY KEY,
            strategy_id TEXT NOT NULL,
            strategy_version TEXT NOT NULL,
            trading_lane TEXT NOT NULL,
            regime TEXT NOT NULL,
            state TEXT NOT NULL,
            independent_outcome_count INTEGER NOT NULL,
            net_expectancy REAL,
            no_trade_delta REAL,
            benchmark_delta REAL,
            payload_json TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS reconciliation_runs (
            reconciliation_id TEXT PRIMARY KEY,
            execution_owner_id TEXT NOT NULL,
            phase TEXT NOT NULL,
            status TEXT NOT NULL,
            expected_digest TEXT NOT NULL,
            observed_digest TEXT NOT NULL,
            blocker_count INTEGER NOT NULL,
            payload_json TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS liveness_cycles (
            cycle_id TEXT PRIMARY KEY,
            market_session_date TEXT NOT NULL,
            generation_id TEXT NOT NULL,
            status TEXT NOT NULL,
            setup_count INTEGER NOT NULL,
            advanced_count INTEGER NOT NULL,
            payload_json TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS execution_owner_leases (
            lease_name TEXT PRIMARY KEY,
            owner_id TEXT NOT NULL,
            token_sha256 TEXT NOT NULL,
            state TEXT NOT NULL,
            acquired_at TEXT NOT NULL,
            heartbeat_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS execution_state (
            state_id TEXT PRIMARY KEY,
            frozen INTEGER NOT NULL,
            reason TEXT,
            reconciliation_id TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (reconciliation_id) REFERENCES reconciliation_runs(reconciliation_id)
        );
        INSERT OR IGNORE INTO execution_state (
            state_id, frozen, reason, reconciliation_id, updated_at
        ) VALUES (
            'canonical_paper_execution', 0, NULL, NULL, '1970-01-01T00:00:00+00:00'
        );

        CREATE TABLE IF NOT EXISTS operating_events (
            event_id TEXT PRIMARY KEY,
            aggregate_type TEXT NOT NULL,
            aggregate_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uq_operating_event_payload
            ON operating_events (aggregate_type, aggregate_id, event_type, payload_sha256);
        CREATE INDEX IF NOT EXISTS ix_canonical_orders_state
            ON canonical_orders (state, updated_at, order_key);
        CREATE INDEX IF NOT EXISTS ix_positions_state
            ON positions (state, instrument, updated_at);
        CREATE INDEX IF NOT EXISTS ix_reconciliation_runs_created
            ON reconciliation_runs (created_at, status);
        CREATE INDEX IF NOT EXISTS ix_liveness_cycles_session
            ON liveness_cycles (market_session_date, created_at);
        """,
    ),
    (
        4,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_canonical_orders_broker_order_id_hash
            ON canonical_orders (broker_order_id_hash)
            WHERE broker_order_id_hash IS NOT NULL AND broker_order_id_hash != '';
        """,
    ),
)
