CREATE TABLE IF NOT EXISTS reference_registry (
    key TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    source TEXT NOT NULL,
    role TEXT NOT NULL,
    mapped_modules TEXT[] NOT NULL DEFAULT '{}',
    validation_status TEXT NOT NULL DEFAULT 'provisional_reference',
    production_active BOOLEAN NOT NULL DEFAULT false,
    decision_notes TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS reference_registry_category_idx
    ON reference_registry (category);

CREATE INDEX IF NOT EXISTS reference_registry_validation_status_idx
    ON reference_registry (validation_status);

CREATE TABLE IF NOT EXISTS world_model_claim (
    key TEXT PRIMARY KEY,
    source_path TEXT NOT NULL,
    claim TEXT NOT NULL,
    claim_type TEXT NOT NULL,
    actors TEXT[] NOT NULL DEFAULT '{}',
    mechanism TEXT NOT NULL,
    observable_signatures TEXT[] NOT NULL DEFAULT '{}',
    live_sources_to_check TEXT[] NOT NULL DEFAULT '{}',
    market_channels TEXT[] NOT NULL DEFAULT '{}',
    corroboration_status TEXT NOT NULL DEFAULT 'foundational_prior',
    postmortem_score NUMERIC,
    evidence_boundary TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS world_model_claim_type_idx
    ON world_model_claim (claim_type);

CREATE INDEX IF NOT EXISTS world_model_claim_corroboration_status_idx
    ON world_model_claim (corroboration_status);

CREATE TABLE IF NOT EXISTS governance_comment (
    comment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    author_email TEXT NOT NULL,
    author_name TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_key TEXT NOT NULL,
    body TEXT NOT NULL,
    tags TEXT[] NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'open',
    visibility TEXT NOT NULL DEFAULT 'founding_fund_managers',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS governance_comment_target_idx
    ON governance_comment (target_type, target_key);

CREATE INDEX IF NOT EXISTS governance_comment_created_at_idx
    ON governance_comment (created_at DESC);
