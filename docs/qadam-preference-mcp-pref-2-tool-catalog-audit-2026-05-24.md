# Qadam Preference MCP - PREF-2 Tool Catalog Audit

Date: 2026-05-24
Stage: PREF-2 - Tool Catalog Discovery Snapshot
Status: complete

## Objective

Add a replayable Preference/PREF MCP tool-catalog contract without calling
`search_tools`, invoking domain tools, consuming paid tools, or changing Qadam's
trading authority.

## Implementation Summary

PREF-2 added:

- `orchestrator/preference_mcp_catalog.py`
- `scripts/check_preference_tool_catalog.py`
- runtime catalog snapshot at `data/runtime/preference_tool_catalog.json`
- runtime catalog history at `data/runtime/preference_tool_catalog_history.jsonl`
- a local-startup check in `scripts/run_pre_phase3_operational_routine.sh`

The catalog defines planned discovery rows for these domain packs:

- `prediction_markets`
- `physical_movement`
- `filings_corporate`
- `macro_commodities`
- `crypto_wallets`
- `news_narrative`
- `sports_lines`

The first six packs are approved only for catalog planning. `sports_lines` is
blocked as outside the current Qadam strategy universe.

## Current Runtime Outcome

The current local state is fail-closed:

- `status`: `blocked_pending_verified_identity`
- `identity_gate_status`: `blocked`
- `identity_status`: `not_verified`
- `identity_quota_metadata_present`: `False`
- `live_catalog_call_attempted`: `False`
- `search_tools_call_attempted`: `False`
- `search_tools_allowed`: `False`
- `domain_tool_calls_allowed`: `False`
- `paid_tool_calls_allowed`: `False`
- `domain_pack_count`: `7`
- `catalog_entry_count`: `20`
- `approved_for_catalog_only_count`: `18`
- `candidate_read_only_count`: `0`
- `blocked_outside_scope_count`: `2`
- `blocked_paid_tool_count`: `0`
- `blocked_no_provenance_count`: `0`

Blocked reasons:

- `domain_tool_calls_disabled_in_pref_2`
- `live_catalog_not_requested_in_pref_2`
- `paid_tools_disabled_in_pref_2`
- `search_tools_call_disabled_in_pref_2`
- `verified_identity_required_for_live_catalog`

## Safety Boundary

PREF-2 cannot:

- call `search_tools`
- call market, orderbook, wallet, filing, weather, vessel, satellite, sports, or
  other Preference domain tools
- request callable templates for unverified tools
- consume paid tools or credits
- create observations
- satisfy source quorum
- create trade candidates
- approve risk
- stage or submit paper orders
- write to brokers
- call quantum providers
- submit hardware jobs
- enable schedulers
- provide fills, receipts, broker echo, or reconciliation truth
- enable live capital

## Verification

```bash
.venv/bin/python scripts/check_preference_tool_catalog.py
.venv/bin/python -m compileall orchestrator/preference_mcp_catalog.py scripts/check_preference_tool_catalog.py
```

Results:

- `preference_tool_catalog_status=blocked_pending_verified_identity`
- `preference_tool_catalog_identity_gate_status=blocked`
- `preference_tool_catalog_live_catalog_call_attempted=False`
- `preference_tool_catalog_search_tools_call_attempted=False`
- `preference_tool_catalog_search_tools_allowed=False`
- `preference_tool_catalog_domain_tool_calls_allowed=False`
- `preference_tool_catalog_paid_tool_calls_allowed=False`
- `preference_tool_catalog_entry_count=20`
- `preference_tool_catalog_validation_error_count=0`
- `preference_tool_catalog_authority_probe_error_count=2`
- `preference_tool_catalog_live_without_identity_probe_error_count=3`
- `preference_tool_catalog_outside_scope_probe_error_count=3`
- `preference_tool_catalog_candidate_without_live_probe_error_count=2`
- `preference_tool_catalog_secret_probe_error_count=2`
- `preference_tool_catalog_check=ok`

The probes prove the catalog rejects authority escalation, live discovery without
verified identity, outside-scope promotion, candidate-read-only status before
live discovery, and secret-shaped values.

## Acceptance

- Catalog schema exists and is replayable from a runtime JSON artifact.
- Catalog history is append-only JSONL.
- Planned discovery rows are domain-pack scoped and public-safe.
- No live Preference call was attempted.
- No discovered tool is marked read-only executable.
- No Preference row can count toward source quorum or create observations.
- No Preference row can create trade candidates, orders, receipts, broker echo,
  reconciliation truth, or live capital authority.
- Local startup now checks both PREF-1 identity gating and PREF-2 catalog
  gating.
- Phase 5 remains blocked until Q4-12 certification passes.

## Required Next Step

Proceed to PREF-3. Add deterministic offline Preference sample fixtures and a
normal Qadam adapter skeleton, still with no live MCP calls and no authority.
