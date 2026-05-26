# Qadam Preference MCP - PREF-6 Source Inventory Registry Trust Policy Audit

Date: 2026-05-24
Stage: PREF-6 - Source Inventory, Resource Registry, And Trust Policy
Status: complete

## Objective

Make Preference/PREF MCP visible to Qadam's planning system without promoting
the Preference aggregator into the canonical 35-source registry.

## Implementation Summary

PREF-6 added or amended:

- `orchestrator/resource_registry.py`
- `orchestrator/phase4_resource_validation.py`
- `orchestrator/phase4_data_veracity.py`
- `orchestrator/phase4_trust_scores.py`
- `scripts/check_phase4_resource_validation.py`
- `scripts/check_phase4_data_veracity_audit.py`
- `scripts/check_phase4_trust_score_recalculation.py`
- `docs/api-source-inventory.md`
- `docs/api-specs.md`
- `docs/qadam-phase-4-implementation-plan.md`
- `docs/qadam-preference-mcp-integration-plan.md`
- `docs/qadam-master-implementation-plan.md`

## Policy Result

Preference/PREF MCP is now registered as:

- Resource Registry key: `preference_mcp`
- category: `supplemental_data_plane`
- Phase 4 resource status: `architecture_reference`
- canonical source: `false`
- source 36: `false`
- score included: `false`
- source-quorum credit allowed: `false`
- canonical rank impact allowed: `false`
- active strategy provenance allowed: `false`

The Resource Registry entry exists so future stages can reason about
Preference as a capability, but it remains a non-live reference. Individual
upstream sources discovered through Preference still require a separate source
registry promotion decision before they can influence canonical source rank.

## Runtime Outcome

Current local verification produced:

- Resource Registry validation:
  - `phase4_resource_count=30`
  - `phase4_resource_preference=present=True,category=supplemental_data_plane,status=architecture_reference,strategy_provenance_allowed=False`
  - `phase4_resource_preference_capability=registry_entry=True,canonical_rank_impact_allowed=False,source_quorum_credit_allowed=False`
  - `phase4_resource_preference_active_probe_error_count=1`
  - `phase4_resource_preference_capability_probe_error_count=2`
  - `phase4_resource_validation_check=ok`
- Data Veracity:
  - `phase4_data_veracity_canonical_source_count=35`
  - `phase4_data_veracity_supplemental_source_count=2`
  - `phase4_data_veracity_preference=supplemental_sample_provenance_validated,supplemental_explicit_upstream_context_not_canonical,canonical=False`
  - `phase4_data_veracity_preference_probe_error_count=3`
  - `phase4_data_veracity_check=ok`
- Trust Score recalculation:
  - `phase4_trust_score_count=35`
  - `phase4_trust_score_preference=score_included=False,canonical_rank_impact_allowed=False,source_quorum_credit_allowed=False,role=supplemental_multi_source_data_plane`
  - `phase4_trust_score_preference_probe_error_count=3`
  - `phase4_trust_score_recalculation_check=ok`

## Safety Boundary

PREF-6 cannot:

- promote Preference as source 36
- treat the Preference aggregator identity as an upstream source
- increase or decrease canonical source count
- increase canonical trust rank
- satisfy source quorum
- create strategy source provenance
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
.venv/bin/python -m compileall orchestrator/resource_registry.py orchestrator/phase4_resource_validation.py orchestrator/phase4_data_veracity.py orchestrator/phase4_trust_scores.py scripts/check_phase4_resource_validation.py scripts/check_phase4_data_veracity_audit.py scripts/check_phase4_trust_score_recalculation.py
.venv/bin/python scripts/check_phase4_resource_validation.py
.venv/bin/python scripts/check_phase4_data_veracity_audit.py
.venv/bin/python scripts/check_phase4_trust_score_recalculation.py
```

Results:

- compile check passed
- `phase4_resource_validation_check=ok`
- `phase4_data_veracity_check=ok`
- `phase4_trust_score_recalculation_check=ok`

## Acceptance

- Preference appears in the source inventory as a registered supplemental
  data-plane reference, not as source 36.
- Preference appears in the Resource Registry as `supplemental_data_plane`.
- Resource validation rejects active strategy provenance for Preference.
- Data Veracity includes Preference as a supplemental row while preserving
  `canonical_source_count=35`.
- Trust Score recalculation includes Preference only in supplemental policy and
  keeps `score_included=false`.
- Probes reject canonical-rank-impact, source-quorum-credit, and active
  strategy-provenance overclaims.
- Phase 5 remains blocked until Q4-12 certification passes.

## Required Next Step

Proceed to PREF-7. Map Preference domain packs to Qadam's first trading
universe without enabling live domain calls.
