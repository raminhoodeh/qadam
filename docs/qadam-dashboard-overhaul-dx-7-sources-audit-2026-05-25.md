# Qadam Dashboard Overhaul DX-7 Sources Audit

Date: 2026-05-25
Stage: DX-7 - Sources Workspace
Status: complete

## Result

dx7_sources_workspace_added=True
dashboard_sources_pipeline_health_visible=True
dashboard_sources_reliability_states_visible=True
dashboard_sources_supplemental_inputs_visible=True
dashboard_source_to_setup_links_visible=True
dashboard_sources_public_safe=True
dashboard_source_authority_unchanged=True
dx8_implementation_allowed=True

## Implementation

- Added a Sources workspace at the top of the Sources view in
  `landing-page-repo/dashboard.js`.
- Expanded `sources_model` with pipeline records, reliability states,
  supplemental source capability records, source quorum, and source-linked
  observed/candidate/setup records.
- Added reliability cards for online, degraded, missing credential, stale
  heartbeat, pending adapter, and supplemental-only states.
- Added capability-aware supplemental cards for Yahoo Finance and
  Preference/PREF MCP.
- Added source-to-setup links for observed signals, trade candidates, and the
  Phase 7 setup pool.
- Preserved the detailed watched-source registry below the workspace.

## Model Changes

- `sources_model.pipelines` now summarizes each intelligence pipeline by online,
  degraded, pending, local-only, missing credential, pending adapter, and signal
  influence counts.
- `sources_model.reliability` exposes the six high-level health buckets used by
  the workspace.
- `sources_model.supplemental` labels Yahoo Finance and Preference/PREF as
  supplemental capability sources with explicit no-source-quorum/no-trade
  authority boundaries.
- `sources_model.source_setup_links` links source evidence to observed signals,
  candidates, and setup-pool state without implying execution authority.

## Safety Review

- The Sources workspace remains read-only.
- No approval, order placement, order close, broker-write, funding, Telegram
  send, learning-write, policy-mutation, source-promotion, paid-tool call, or
  live-capital route was added.
- Supplemental Yahoo Finance and Preference/PREF records are explicitly marked
  as not source quorum and not sole proof.
- Source-linked candidate/setup cards route to review surfaces only.
- The rendered source workspace does not expose secrets, API keys, local paths,
  raw payload markers, private payload markers, broker identifiers, or request
  bodies.

## Verification

Expected checks:

```bash
node --check landing-page-repo/dashboard.js
node --check scripts/check_dashboard_overhaul_sources.js
node scripts/check_dashboard_overhaul_sources.js
node scripts/check_dashboard_watching_view.js
node scripts/check_dashboard_renderer.js
node scripts/check_dashboard_overhaul_view_models.js
node scripts/check_dashboard_overhaul_trades.js
./scripts/preflight_dashboard_deployment.sh
```

The DX-7 checker verifies:

- Sources workspace static shell exists.
- Sources CSS supports reliability cards, supplemental cards, source-to-setup
  links, and pipeline cards.
- The renderer exports the Sources workspace helpers and model fields.
- The model exposes five pipeline groups and six reliability states.
- Missing credentials, pending adapters, and supplemental-only sources are
  visible.
- Yahoo Finance and Preference/PREF are treated as supplemental, not source
  quorum.
- Source-to-setup links route only to review surfaces.
- Rendered source workspace stays public-safe.

## Next Stage

DX-8 - Reasoning Workspace may proceed next.
