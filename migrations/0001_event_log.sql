-- Qadam Event Log schema v1.
-- Target runtime: TimescaleDB/PostgreSQL.

CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS event_log (
    id BIGSERIAL,
    schema_version INTEGER NOT NULL DEFAULT 1,
    event_type TEXT NOT NULL,
    component TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('debug', 'info', 'warning', 'error', 'critical')),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    correlation_id UUID NOT NULL DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id, created_at)
);

SELECT create_hypertable('event_log', 'created_at', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_event_log_created_at_desc
    ON event_log (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_event_log_component_created_at
    ON event_log (component, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_event_log_event_type_created_at
    ON event_log (event_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_event_log_correlation_id
    ON event_log (correlation_id);

CREATE INDEX IF NOT EXISTS idx_event_log_payload_gin
    ON event_log USING GIN (payload);
