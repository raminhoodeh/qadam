# Qadam Preference MCP - PREF-4 Live Read-Only Smoke Gate Audit

Date: 2026-05-24
Stage: PREF-4 - Live Read-Only Smoke Gate
Status: complete, blocked before network calls in current local config

## Objective

Permit the smallest possible live Preference/PREF MCP checks while preserving
fail-closed behavior and preventing any domain data call.

## Implementation Summary

PREF-4 added status/catalog-only live smoke support to:

- `orchestrator/preference_mcp_adapter.py`
- `scripts/check_preference_mcp_adapter.py`

New check modes:

- `--live-status-only`
  - may call only `preference_account_status`
  - current local result: blocked before network calls
- `--live-catalog-only`
  - may call only `search_tools`
  - requires a verified non-anonymous identity first
  - current local result: blocked before network calls

Runtime artifacts:

- `data/runtime/preference_mcp_live_smoke.json`
- `data/runtime/preference_mcp_live_smoke_history.jsonl`

## Current Runtime Outcome

The current local state is fail-closed because:

- `PREFERENCE_MCP_ENABLED=false`
- `PREFERENCE_API_KEY` is not configured
- Preference identity is not verified

`--live-status-only` result:

- `status`: `blocked_preflight`
- `enabled`: `False`
- `credential_configured`: `False`
- `identity_gate_status`: `blocked`
- `live_status_call_attempted`: `False`
- `live_catalog_call_attempted`: `False`
- `search_tools_call_attempted`: `False`
- `domain_tool_call_attempted`: `False`
- `paid_tool_call_attempted`: `False`
- `domain_data_requested`: `False`
- `source_quorum_credit_allowed`: `False`
- `live_call_attempt_count`: `0`
- `blocked_reasons`:
  - `preference_api_key_missing`
  - `preference_mcp_disabled`

`--live-catalog-only` result:

- `status`: `blocked_pending_verified_identity`
- `enabled`: `False`
- `credential_configured`: `False`
- `identity_gate_status`: `blocked`
- `live_status_call_attempted`: `False`
- `live_catalog_call_attempted`: `False`
- `search_tools_call_attempted`: `False`
- `domain_tool_call_attempted`: `False`
- `paid_tool_call_attempted`: `False`
- `domain_data_requested`: `False`
- `source_quorum_credit_allowed`: `False`
- `live_call_attempt_count`: `0`
- `blocked_reasons`:
  - `preference_api_key_missing`
  - `preference_mcp_disabled`
  - `verified_identity_required_for_live_catalog`

## Safety Boundary

PREF-4 can only ever attempt:

- `preference_account_status`
- `search_tools`, after verified non-anonymous identity

PREF-4 cannot:

- call Preference domain tools
- request market, orderbook, wallet, filing, weather, vessel, satellite, sports,
  or other domain data
- consume paid tools
- grant source-quorum credit
- create observations for strategy use
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
.venv/bin/python scripts/check_preference_mcp_adapter.py --live-status-only
.venv/bin/python scripts/check_preference_mcp_adapter.py --live-catalog-only
.venv/bin/python -m compileall orchestrator/preference_mcp_adapter.py scripts/check_preference_mcp_adapter.py
```

Results:

- `preference_mcp_live_smoke_validation_error_count=0`
- `preference_mcp_live_smoke_authority_probe_error_count=2`
- `preference_mcp_live_smoke_catalog_without_identity_probe_error_count=1`
- `preference_mcp_live_smoke_domain_tool_probe_error_count=3`
- `preference_mcp_live_smoke_paid_tool_probe_error_count=3`
- `preference_mcp_live_smoke_secret_probe_error_count=2`
- `preference_mcp_live_smoke_check=ok`

The probes prove the gate rejects authority escalation, catalog calls without
verified identity, domain-tool calls, paid-tool calls, and secret-shaped values.

## Acceptance

- Live smoke modes exist and write public-safe runtime artifacts.
- Missing key and disabled MCP block before network calls.
- Catalog smoke cannot call `search_tools` until identity is verified.
- Domain tool calls remain impossible in PREF-4.
- Paid tool calls remain impossible in PREF-4.
- Source-quorum credit remains false.
- No trade-candidate, broker-write, paper-order, fill, receipt,
  reconciliation, quantum, scheduler, hardware, or live-capital authority
  exists.
- Phase 5 remains blocked until Q4-12 certification passes.

## Required Next Step

Proceed to PREF-5. Add the provenance and source-quorum contract so Preference
cannot wash multiple upstream claims through a single aggregator identity.
