# Qadam Preference MCP PREF-12 Source Promotion Decisions Audit

Date: 2026-05-24
Stage: PREF-12 - Optional Later Source Promotion
Status: Complete

## Scope

PREF-12 evaluates Preference-backed upstream feeds one at a time for possible
canonical-source promotion. It does not promote the Preference aggregator as
source 36 and does not change the canonical source count without a named
upstream source passing provenance, freshness, terms/usage, deterministic test,
durable replay, independent corroboration, and explicit registry-approval gates.

## Implemented

- Added `orchestrator/preference_mcp_source_promotion.py`.
- Added `scripts/check_preference_source_promotion.py`.
- Added a runtime artifact:
  `data/runtime/preference_source_promotion_decisions.json`.
- Wired the source-promotion summary into Phase 4 Data Veracity, Trust Score,
  and public-safe cockpit Preference status.
- Preserved `EXPECTED_SOURCE_COUNT=35`.

## Decisions

| Preference upstream | Registry decision | Promotion status |
| --- | --- | --- |
| `polymarket` | Use existing `polymarket` registry entry; no new count | Not promoted |
| `kalshi` | Use existing `kalshi` registry entry; no new count | Not promoted |
| `sec_edgar` | Use existing `sec_edgar` registry entry; no new count | Not promoted |
| `vessel_tracking` | Map to existing combined `ais_maritime` registry entry; no new count | Not promoted |
| `noaa` | Defer pending direct endpoint, terms, replay, and corroboration review | Not promoted |
| `kol_wallets` | Defer pending wallet identity, terms, replay, and company-truth policy review | Not promoted |

## Current Local Result

- Source-promotion status: `validated`
- Decision count: `6`
- Promoted decision count: `0`
- Existing registry decision count: `4`
- New source deferred count: `2`
- Canonical source count before: `35`
- Canonical source count after: `35`
- Preference aggregator promoted: `False`
- Preference source 36: `False`
- Source-quorum credit allowed: `False`
- Canonical rank impact allowed: `False`
- Trade candidates, execution, paper orders, broker writes, and live capital:
  `False`

## Verification

```bash
.venv/bin/python -m compileall orchestrator/preference_mcp_source_promotion.py orchestrator/phase4_data_veracity.py orchestrator/phase4_trust_scores.py orchestrator/cockpit_status.py scripts/check_preference_source_promotion.py scripts/check_phase4_data_veracity_audit.py scripts/check_phase4_trust_score_recalculation.py scripts/check_cockpit_status.py
.venv/bin/python -m ruff check orchestrator/preference_mcp_source_promotion.py orchestrator/phase4_data_veracity.py orchestrator/phase4_trust_scores.py orchestrator/cockpit_status.py scripts/check_preference_source_promotion.py scripts/check_phase4_data_veracity_audit.py scripts/check_phase4_trust_score_recalculation.py scripts/check_cockpit_status.py
.venv/bin/python scripts/check_preference_source_promotion.py
.venv/bin/python scripts/check_phase1_data_spine.py
.venv/bin/python scripts/check_source_heartbeat.py
.venv/bin/python scripts/check_phase4_data_veracity_audit.py
.venv/bin/python scripts/check_phase4_trust_score_recalculation.py
.venv/bin/python scripts/check_cockpit_status.py
```

Observed checks:

- `preference_source_promotion_check=ok`
- `preference_source_promotion_decision_count=6`
- `preference_source_promotion_promoted_decision_count=0`
- `preference_source_promotion_source_count_after=35`
- `phase1_data_spine_source_count=35`
- `source_heartbeat_source_count=35`
- `phase4_data_veracity_preference_source_promotion=status=validated,decisions=6,promoted=0,source_count_after=35`
- `phase4_trust_score_preference_source_promotion=status=validated,decisions=6,promoted=0,source_count_after=35`
- `cockpit_status_preference_mcp_source_promotion_status=validated`
- `cockpit_status_preference_mcp_source_promotion_promoted_count=0`

## Residual Blockers

No Preference-backed upstream source is canonical. Future promotion requires a
specific upstream source, a direct endpoint or provider contract, terms/usage
review, deterministic and live read-only tests, durable replay behavior,
independent corroboration, source-registry update, Data Veracity and Trust Score
updates, cockpit updates, and explicit Fund Manager approval.
