# Qadam Cockpit Contract

The cockpit is the Founding Fund Manager view of Qadam. It should be useful even when the local Python COO is offline, and richer when the COO health endpoint is running.

## Health Flow

1. The Python COO serves the canonical health payload on `QADAM_HEALTH_HOST:QADAM_HEALTH_PORT`.
2. The Next.js cockpit reads `QADAM_ORCHESTRATOR_URL` or `NEXT_PUBLIC_QADAM_ORCHESTRATOR_URL`.
3. `cockpit/app/api/health/route.ts` proxies the health payload and falls back to local degraded state if the COO is offline.
4. `cockpit/app/page.tsx` renders the System Map from the same health contract.

## Required Health Fields

- `status`, `mode`, `trial_balance_gbp`
- `source_count`, `expected_source_count`, `pipeline_counts`, `unresolved_sources`
- `modules`
- `adapters`
- `fund_managers`
- `resource_registry`
- `world_model`
- `governance_forum`
- `ingestion_spine`
- `source_heartbeat`
- `local_stores`
- `event_log`
- `execution_venues`, `execution_summary`

## UI Rules

- Show paper/test mode before any trading state.
- Show degraded/offline storage clearly.
- Show promoted adapters separately from the generic 35-source registry.
- Never show secret values, tokens, broker keys, or raw payload contents.
- Keep execution venues visible but disabled until Phase 5 gates are passed.
- Keep private world-model claims visibly separate from evidence.

## Current Routes

- `/` renders the System Map.
- `/api/health` returns cockpit health with COO fallback.
- `/settings` shows runtime settings.

Clerk login, protected `/dashboard`, and the comments/forum UI remain next cockpit work.
