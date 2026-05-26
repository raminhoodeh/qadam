# Qadam Preference MCP - PREF-3 Offline Sample Adapter Audit

Date: 2026-05-24
Stage: PREF-3 - Adapter Skeleton With Deterministic Sample Fixtures
Status: complete

## Objective

Make Preference/PREF MCP look like a normal Qadam adapter before live calls by
adding deterministic sample records, `UnifiedEvent` normalization, raw sample
archival, and no-authority Event Log records.

## Implementation Summary

PREF-3 added:

- `orchestrator/preference_mcp_adapter.py`
- `scripts/check_preference_mcp_adapter.py`
- local startup coverage in `scripts/run_pre_phase3_operational_routine.sh`

The adapter emits six deterministic sample records:

- Polymarket orderbook depth context
- Kalshi market summary context
- vessel movement near the Strait of Hormuz
- NOAA/weather commodity context
- SEC filing metadata context
- smart-wallet movement context

Each sample record normalizes into a Qadam `UnifiedEvent` with:

- source: `supplemental.preference_mcp`
- classification: `supplemental_offline_sample_pending_identity_catalog_provenance`
- deterministic sample provenance
- no live-discovered tool reference
- no source-quorum credit
- no trade-candidate, broker-write, paper-order, fill, receipt, reconciliation,
  quantum, scheduler, hardware, or live-capital authority

Raw sample payloads are archived under `data/raw_payloads/preference_mcp/`.

## Current Runtime Outcome

The current local state is sample-ready and live-blocked:

- `status`: `ok`
- `mode`: `offline_sample_only`
- `event_count`: `6`
- `sample_fixture_count`: `6`
- `identity_gate_status`: `blocked`
- `catalog_gate_status`: `blocked_pending_verified_identity`
- `catalog_validation_error_count`: `0`
- `canonical_source_count`: `35`
- `live_mcp_call_allowed`: `False`
- `search_tools_allowed`: `False`
- `domain_tool_calls_allowed`: `False`
- `paid_tool_calls_allowed`: `False`
- `source_quorum_credit_allowed`: `False`
- `trade_candidate_creation_allowed`: `False`
- `broker_write_authority`: `False`
- `live_capital_authority`: `False`

## Safety Boundary

PREF-3 cannot:

- call the Preference MCP endpoint
- call `search_tools`
- call market, orderbook, wallet, filing, weather, vessel, satellite, sports, or
  other Preference domain tools
- consume paid tools or credits
- grant source-quorum credit
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
.venv/bin/python scripts/check_preference_mcp_adapter.py
.venv/bin/python -m compileall orchestrator/preference_mcp_adapter.py scripts/check_preference_mcp_adapter.py
```

Results:

- `preference_mcp_adapter_status=ok`
- `preference_mcp_adapter_stage=PREF-3`
- `preference_mcp_adapter_event_count=6`
- `preference_mcp_adapter_sample_fixture_count=6`
- `preference_mcp_adapter_identity_gate_status=blocked`
- `preference_mcp_adapter_catalog_gate_status=blocked_pending_verified_identity`
- `preference_mcp_adapter_catalog_validation_error_count=0`
- `preference_mcp_adapter_live_mcp_call_allowed=False`
- `preference_mcp_adapter_search_tools_allowed=False`
- `preference_mcp_adapter_domain_tool_calls_allowed=False`
- `preference_mcp_adapter_paid_tool_calls_allowed=False`
- `preference_mcp_adapter_source_quorum_credit_allowed=False`
- `preference_mcp_adapter_trade_candidate_creation_allowed=False`
- `preference_mcp_adapter_broker_write_authority=False`
- `preference_mcp_adapter_live_capital_authority=False`
- `preference_mcp_adapter_validation_error_count=0`
- `preference_mcp_adapter_authority_probe_error_count=1`
- `preference_mcp_adapter_live_call_probe_error_count=2`
- `preference_mcp_adapter_source_quorum_probe_error_count=1`
- `preference_mcp_adapter_missing_provenance_probe_error_count=1`
- `preference_mcp_adapter_secret_probe_error_count=1`
- `preference_mcp_adapter_check=ok`

The probes prove the adapter rejects broker-write authority, live MCP/search
call markers, source-quorum credit, missing Preference provenance, and
secret-shaped values.

## Acceptance

- Deterministic sample records exist for the planned PREF-3 domains.
- Sample records normalize into `UnifiedEvent` records.
- Raw sample payloads archive locally under `data/raw_payloads/preference_mcp/`.
- Event Log records include the no-authority boundary.
- Identity and catalog gates remain visible and blocked.
- No live MCP call was attempted.
- No `search_tools` call was attempted.
- No domain tool call was attempted.
- No Preference sample can satisfy source quorum or create a trade candidate.
- Local startup now checks PREF-1 identity, PREF-2 catalog, and PREF-3 adapter
  posture.
- Phase 5 remains blocked until Q4-12 certification passes.

## Required Next Step

PREF-4 is the next planned stage, but it should only run as a live read-only
smoke gate after a valid non-anonymous Preference identity is configured
locally. If identity remains unavailable, the safe alternative is to continue
with offline provenance and source-quorum policy scaffolding.
