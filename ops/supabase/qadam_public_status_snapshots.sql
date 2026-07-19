-- Private server-side storage for Qadam's signed public-safe status snapshots.
-- There are intentionally no browser insert/update/delete policies.
create table if not exists public.qadam_public_status_snapshots (
    id bigint generated always as identity primary key,
    generated_at timestamptz not null,
    payload_digest text not null unique,
    signature text not null,
    canonical_payload text not null,
    payload jsonb not null,
    stored_at timestamptz not null default now()
);

create index if not exists qadam_public_status_snapshots_stored_at_idx
    on public.qadam_public_status_snapshots (stored_at desc);

alter table public.qadam_public_status_snapshots enable row level security;

alter table public.qadam_public_status_snapshots
    add column if not exists canonical_payload text;

revoke all on table public.qadam_public_status_snapshots from anon, authenticated;
