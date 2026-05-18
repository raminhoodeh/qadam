CREATE TABLE IF NOT EXISTS fund_manager_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id UUID,
    author_email TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_key TEXT NOT NULL,
    body TEXT NOT NULL,
    tags TEXT[] NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'suggestion',
    visibility TEXT NOT NULL DEFAULT 'founding_fund_managers',
    event_log_export_status TEXT NOT NULL DEFAULT 'not_required',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS fund_manager_comments_target_idx
    ON fund_manager_comments (target_type, target_key);

CREATE INDEX IF NOT EXISTS fund_manager_comments_status_idx
    ON fund_manager_comments (status);

CREATE INDEX IF NOT EXISTS fund_manager_comments_created_at_idx
    ON fund_manager_comments (created_at DESC);

ALTER TABLE governance_comment
    ALTER COLUMN status SET DEFAULT 'suggestion';

ALTER TABLE governance_comment
    ADD COLUMN IF NOT EXISTS event_log_export_status TEXT NOT NULL DEFAULT 'not_required';
