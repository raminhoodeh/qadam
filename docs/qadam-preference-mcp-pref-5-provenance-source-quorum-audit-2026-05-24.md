# Qadam Preference MCP - PREF-5 Provenance Source-Quorum Audit

Date: 2026-05-24
Stage: PREF-5 - Provenance And Source-Quorum Contract
Status: complete

## Objective

Prevent source washing through the Preference/PREF MCP aggregator. Preference
can provide supplemental context, but Qadam must preserve explicit upstream
identity, provenance, query hashes, payload hashes, and source-quorum limits
before any later stage can use it.

## Implementation Summary

PREF-5 added:

- `orchestrator/preference_mcp_provenance.py`
- `scripts/check_preference_provenance.py`
- query and payload hash fields in PREF-3 normalized Preference events
- local startup coverage in `scripts/run_pre_phase3_operational_routine.sh`
- runtime report at `data/runtime/preference_provenance_source_quorum.json`
- runtime history at `data/runtime/preference_provenance_source_quorum_history.jsonl`

Each normalized Preference event now carries a `preference_provenance` block
with:

- `tool_ref`
- `pref_request_id`
- `response_id`
- `query`
- `query_hash`
- `payload_hash`
- `payload_hash_fields`
- `upstream_source_name`
- `upstream_source_identity`
- `upstream_provenance_url`
- `upstream_provenance_id`
- `provenance_path`
- `fetched_at`
- `observed_at`
- `freshness_seconds`
- `cadence`
- `credit_cost_metadata`

## Current Runtime Outcome

The current offline sample result is valid:

- `status`: `validated`
- `preference_observation_count`: `6`
- `valid_preference_observation_count`: `6`
- `quarantined_observation_count`: `0`
- `preference_distinct_upstream_source_count`: `6`
- `duplicate_upstream_identity_count`: `0`
- `preference_context_status`: `explicit_multi_upstream_context`
- `preference_multi_source_context_allowed`: `True`
- `preference_counts_as_canonical_source`: `False`
- `preference_only_source_quorum_allowed`: `False`
- `strategy_source_quorum_credit_allowed`: `False`
- `combined_context_status`: `distinct_preference_and_canonical_context`
- `combined_context_allowed`: `True`

This means the sample can demonstrate explicit upstream separation, but
Preference still cannot become a canonical source or satisfy strategy source
quorum by itself.

## Safety Boundary

PREF-5 cannot:

- promote Preference as source 36
- treat the Preference aggregator identity as an upstream source
- count missing-provenance observations
- count duplicate upstream identities as independent sources
- allow Preference-only evidence to satisfy strategy source quorum
- allow a canonical source and a Preference upstream source to count as two when
  they are actually the same upstream identity
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
.venv/bin/python scripts/check_preference_provenance.py
.venv/bin/python scripts/check_preference_mcp_adapter.py
.venv/bin/python -m compileall orchestrator/preference_mcp_provenance.py orchestrator/preference_mcp_adapter.py scripts/check_preference_provenance.py scripts/check_preference_mcp_adapter.py
```

Results:

- `preference_provenance_status=validated`
- `preference_provenance_observation_count=6`
- `preference_provenance_valid_observation_count=6`
- `preference_provenance_quarantined_observation_count=0`
- `preference_provenance_distinct_upstream_source_count=6`
- `preference_provenance_duplicate_upstream_identity_count=0`
- `preference_provenance_multi_source_context_allowed=True`
- `preference_provenance_counts_as_canonical_source=False`
- `preference_provenance_only_source_quorum_allowed=False`
- `preference_provenance_strategy_source_quorum_credit_allowed=False`
- `preference_provenance_validation_error_count=0`
- `preference_provenance_event_validation_error_count=0`
- `preference_provenance_missing_probe_error_count=1`
- `preference_provenance_duplicate_probe_error_count=1`
- `preference_provenance_overclaim_probe_error_count=2`
- `preference_provenance_payload_hash_probe_error_count=1`
- `preference_provenance_aggregator_identity_probe_error_count=1`
- `preference_provenance_canonical_distinct_probe_error_count=0`
- `preference_provenance_canonical_duplicate_probe_error_count=1`
- `preference_provenance_check=ok`

The probes prove that missing provenance, duplicate upstream identities,
source-quorum overclaims, payload hash tampering, aggregator-only identity, and
duplicate canonical overlap fail validation.

## Acceptance

- Every Preference sample event carries a `preference_provenance` block.
- Every Preference sample event carries a query hash and payload hash.
- Missing provenance is quarantined.
- Duplicate upstream identities fail validation.
- Source-quorum overclaims fail validation.
- Preference-only context cannot satisfy strategy source quorum.
- Preference plus canonical evidence can be treated as distinct context only
  when the upstream identities do not overlap.
- Preference remains supplemental and is not source 36.
- Phase 5 remains blocked until Q4-12 certification passes.

## Required Next Step

Proceed to PREF-6. Add Preference to the source inventory, Resource Registry,
Data Veracity, and Trust Score policy as a supplemental data plane without
canonical-source promotion.
