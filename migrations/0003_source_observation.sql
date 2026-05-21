CREATE TABLE IF NOT EXISTS source_observation (
    observation_id UUID DEFAULT gen_random_uuid(),
    schema_version INTEGER NOT NULL,
    source_key TEXT NOT NULL,
    source_name TEXT NOT NULL,
    pipeline TEXT NOT NULL,
    tier INTEGER NOT NULL,
    mode TEXT NOT NULL,
    adapter_status TEXT NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    latency_ms INTEGER NOT NULL,
    trust_score NUMERIC NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (observation_id, observed_at)
);

SELECT create_hypertable('source_observation', 'observed_at', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS source_observation_source_observed_idx
    ON source_observation (source_key, observed_at DESC);

CREATE INDEX IF NOT EXISTS source_observation_pipeline_idx
    ON source_observation (pipeline, observed_at DESC);

CREATE INDEX IF NOT EXISTS source_observation_payload_gin_idx
    ON source_observation USING GIN (payload);
