# Qadam Preference MCP - PREF-1 Identity Status Gate Audit

Date: 2026-05-24
Stage: PREF-1 - Secret, MCP Identity, And Anonymous-Fail-Closed Contract
Status: complete

## Objective

Add local Preference/PREF MCP configuration and an identity/status gate without
registering a key, installing the MCP, calling domain tools, consuming credits,
or changing Qadam's execution posture.

## Implementation Summary

PREF-1 added:

- `orchestrator/preference_mcp_identity.py`
- `scripts/check_preference_mcp_identity.py`
- Preference runtime controls in `orchestrator/config.py`
- Preference placeholders in `.env.example`
- `PREFERENCE_API_KEY` masked status in `orchestrator/mcp_server.py`
- Preference key-pattern coverage in the pre-Phase-3 secret scan
- A local startup check in `scripts/run_pre_phase3_operational_routine.sh`

Runtime controls:

- `PREFERENCE_MCP_ENABLED=false`
- `PREFERENCE_API_KEY`
- `PREFERENCE_MCP_ENDPOINT=https://pref.trade/mcp`
- `PREFERENCE_MCP_TRANSPORT=streamable-http`
- `PREFERENCE_DAILY_CALL_BUDGET=250`
- `PREFERENCE_RUN_CALL_BUDGET=10`
- `PREFERENCE_PAID_TOOLS_ALLOWED=false`
- `PREFERENCE_TOOL_ALLOWLIST`
- `PREFERENCE_DOMAIN_ALLOWLIST`
- `PREFERENCE_MCP_TIMEOUT_SECONDS=15`

## Current Runtime Outcome

The current local state is fail-closed:

- `status`: `blocked`
- `enabled`: `False`
- `credential_configured`: `False`
- `credential_source`: `missing`
- `key_format_status`: `missing`
- `live_status_check_requested`: `False`
- `live_status_call_attempted`: `False`
- `identity_status`: `not_verified`
- `quota_metadata_present`: `False`
- `blocked_reasons`:
  - `live_status_check_not_requested`
  - `preference_api_key_missing`
  - `preference_mcp_disabled`

This is the expected PREF-1 result without a local `PREFERENCE_API_KEY`.

## Safety Boundary

PREF-1 cannot:

- call Preference domain tools
- call `search_tools`
- consume paid tools or credits
- create observations
- create trade candidates
- approve risk
- stage or submit paper orders
- write to brokers
- call quantum providers
- submit hardware jobs
- enable schedulers
- provide fills, receipts, broker echo, or reconciliation truth
- enable live capital

The only live call PREF-1 can ever attempt is `preference_account_status`, and
only when explicitly requested and local config is enabled with a configured
key.

## Verification

```bash
.venv/bin/python scripts/check_preference_mcp_identity.py --no-event
.venv/bin/python -m compileall orchestrator/preference_mcp_identity.py scripts/check_preference_mcp_identity.py orchestrator/config.py orchestrator/mcp_server.py
```

Results:

- `preference_mcp_identity_status=blocked`
- `preference_mcp_identity_credential_configured=False`
- `preference_mcp_identity_live_status_call_attempted=False`
- `preference_mcp_identity_identity_status=not_verified`
- `preference_mcp_identity_domain_tool_calls_allowed=False`
- `preference_mcp_identity_paid_tool_calls_allowed=False`
- `preference_mcp_identity_trade_candidate_creation_allowed=False`
- `preference_mcp_identity_broker_write_authority=False`
- `preference_mcp_identity_live_capital_authority=False`
- `preference_mcp_identity_validation_error_count=0`
- `preference_mcp_identity_positive_probe_error_count=0`
- `preference_mcp_identity_anonymous_probe_error_count=1`
- `preference_mcp_identity_quota_probe_error_count=1`
- `preference_mcp_identity_authority_probe_error_count=2`
- `preference_mcp_identity_secret_probe_error_count=2`
- `preference_mcp_identity_check=ok`

The positive probe proves that a non-anonymous identity with quota metadata can
validate. The anonymous, missing-quota, authority, and secret probes prove the
gate rejects unsafe states.

## Acceptance

- Preference config exists with live disabled by default.
- Key status can be reported without exposing the key.
- Missing key and disabled MCP produce a blocked, valid, public-safe status.
- Anonymous identity cannot be treated as verified.
- Missing quota metadata cannot be treated as verified.
- Domain tool calls and paid tool calls remain false.
- The secret scan now detects committed `pref_agent_*`-shaped values.
- Phase 5 remains blocked until Q4-12 certification passes.

## Required Next Step

Proceed to PREF-2 and PREF-3 next. Those stages should add a tool-catalog
contract and deterministic offline adapter samples. Live catalog calls should
wait until PREF-1 is rerun with a valid non-anonymous identity.
