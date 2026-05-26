# Qadam Preference MCP PREF-9 Cockpit And Mission Control Visibility Audit

Date: 2026-05-24
Stage: PREF-9
Status: complete

## Objective

Expose Preference/PREF MCP posture to Fund Managers through the public-safe
cockpit and Mission Control without implying trading readiness, source-quorum
credit, broker authority, live MCP authority, paid-tool permission, or live
capital readiness.

## Implemented

- Added a sanitized top-level `preference_mcp` object to the cockpit status
  contract in `orchestrator/cockpit_status.py`.
- Added cockpit validation for public-safe Preference fields, hidden raw keys,
  hidden raw prompts, hidden raw payloads, hidden private source payloads, and
  all no-authority flags.
- Added Mission Control source and system-stack summaries for Preference status,
  identity status, quota status, catalog status, domain-pack count, provenance
  status, shadow-context status, and degraded reason.
- Updated `landing-page-repo/dashboard.js` to render Preference visibility in
  the data-source panel and watched-source surface:
  - data-plane status
  - domain-pack coverage
  - provenance health
  - quota/credit health
  - blocked paid tools
  - no trade, broker, source-quorum, paid-tool, or live-capital authority
- Updated dashboard and cockpit checks to enforce the new contract.

## Current Local Outcome

- `preference_mcp.status`: `challenge_only_ready`
- `preference_mcp.enabled`: `False`
- `preference_mcp.identity_status`: `not_verified`
- `preference_mcp.quota_status`: `disabled_live_mode`
- `preference_mcp.catalog_status`: `blocked_pending_verified_identity`
- `preference_mcp.approved_domain_pack_count`: `6`
- `preference_mcp.provenance_status`: `validated`
- `preference_mcp.shadow_context_status`: `challenge_only_ready`
- `preference_mcp.degraded_reason`:
  `live_mcp_disabled,identity_not_verified,quota_metadata_missing`

This is the intended local posture: deterministic Preference context is visible
as read-only challenge context, while live Preference MCP use remains blocked
until a valid non-anonymous identity and quota metadata are verified locally.

## Boundary

Preference remains a supplemental data plane, not source 36. The cockpit export
does not expose real keys, Authorization headers, full prompts, raw provider
payloads, raw archive paths, private source payloads, local absolute paths, or
provider internals.

The following remain false:

- live MCP call authority
- `search_tools` authority
- domain-tool call authority
- paid-tool call authority
- source-quorum credit
- Preference-only confirmation
- trade-candidate creation
- risk handoff
- execution
- paper orders
- broker writes
- quantum provider calls
- scheduler enablement
- live capital

## Verification

```bash
.venv/bin/python -m compileall orchestrator/cockpit_status.py scripts/check_cockpit_status.py
.venv/bin/python -m ruff check orchestrator/cockpit_status.py scripts/check_cockpit_status.py
node --check landing-page-repo/dashboard.js
node --check scripts/check_dashboard_renderer.js
node --check scripts/check_dashboard_mission_control.js
node --check scripts/check_dashboard_watching_view.js
.venv/bin/python scripts/check_preference_shadow_context.py
.venv/bin/python scripts/check_cockpit_status.py
node scripts/check_dashboard_renderer.js
node scripts/check_dashboard_mission_control.js
node scripts/check_dashboard_watching_view.js
```

Result: all checks passed.

## Next Step

Proceed to PREF-10: Phase 4 Re-Manifestation. Re-run the Phase 4 strategy
manifestation path with Preference-aware source-role, domain-pack, freshness,
quota, source-quorum, and no-trade rules before Phase 4 certification is
reconsidered.
