# Qadam Preference MCP - PREF-7 First Trading Universe Domain Packs Audit

Date: 2026-05-24
Stage: PREF-7 - First-Trading-Universe Domain Packs
Status: complete

## Objective

Map Preference/PREF MCP domain packs to Qadam's five first-trading-universe
strategy families without enabling live Preference domain calls or any trading
authority.

## Implementation Summary

PREF-7 added:

- `orchestrator/preference_mcp_domain_packs.py`
- `scripts/check_preference_domain_packs.py`
- local startup coverage in `scripts/run_pre_phase3_operational_routine.sh`
- runtime report at `data/runtime/preference_domain_packs.json`
- runtime history at `data/runtime/preference_domain_packs_history.jsonl`

PREF-7 updated:

- `docs/qadam-preference-mcp-integration-plan.md`
- `docs/qadam-master-implementation-plan.md`
- `docs/api-specs.md`

## Domain-Pack Mapping

The mapping covers all five active strategy families:

- `prediction_market_geopolitical_dislocation`
  - `prediction_markets`
  - `news_narrative`
- `crude_oil_energy_security_disruption`
  - `physical_movement`
  - `macro_commodities`
  - `prediction_markets`
- `defence_repricing_geopolitical_watch`
  - `filings_corporate`
  - `news_narrative`
  - `prediction_markets`
- `silver_macro_liquidity_stress`
  - `macro_commodities`
  - `news_narrative`
- `semiconductor_policy_options_asymmetry`
  - `filings_corporate`
  - `news_narrative`
  - `macro_commodities`
  - `crypto_wallets`

The `crypto_wallets` domain pack is explicitly limited to risk sentiment. It
cannot be used as company truth, filing truth, corporate disclosure truth, or
market confirmation truth.

## Runtime Outcome

Current local verification produced:

- `preference_domain_pack_status=validated`
- `preference_domain_pack_strategy_family_count=5`
- `preference_domain_pack_expected_strategy_family_count=5`
- `preference_domain_pack_strategy_family_with_allowed_pack_count=5`
- `preference_domain_pack_unique_domain_pack_count=6`
- `preference_domain_pack_unique_domain_packs=crypto_wallets,filings_corporate,macro_commodities,news_narrative,physical_movement,prediction_markets`
- `preference_domain_pack_catalog_status=blocked_pending_verified_identity`
- `preference_domain_pack_catalog_live_call_attempted=False`
- `preference_domain_pack_live_mcp_call_allowed=False`
- `preference_domain_pack_search_tools_allowed=False`
- `preference_domain_pack_domain_tool_calls_allowed=False`
- `preference_domain_pack_paid_tool_calls_allowed=False`
- `preference_domain_pack_source_quorum_credit_allowed=False`
- `preference_domain_pack_preference_only_confirmation_allowed=False`
- `preference_domain_pack_trade_candidate_creation_allowed=False`
- `preference_domain_pack_execution_allowed=False`
- `preference_domain_pack_paper_order_allowed=False`
- `preference_domain_pack_broker_write_allowed=False`
- `preference_domain_pack_live_capital_enabled=False`
- `preference_domain_pack_validation_error_count=0`
- `preference_domain_pack_check=ok`

## Safety Boundary

PREF-7 cannot:

- call the Preference MCP endpoint
- call `search_tools`
- call Preference domain tools
- consume paid tools
- satisfy source quorum
- allow Preference-only confirmation
- treat KOL or wallet activity as company truth
- map sports lines into Qadam's current strategy universe
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
.venv/bin/python -m compileall orchestrator/preference_mcp_domain_packs.py scripts/check_preference_domain_packs.py
.venv/bin/python scripts/check_preference_domain_packs.py
```

Results:

- compile check passed
- `preference_domain_pack_missing_family_probe_error_count=4`
- `preference_domain_pack_authority_probe_error_count=4`
- `preference_domain_pack_preference_only_probe_error_count=2`
- `preference_domain_pack_sports_pack_probe_error_count=4`
- `preference_domain_pack_wallet_company_truth_probe_error_count=2`
- `preference_domain_pack_source_quorum_probe_error_count=3`
- `preference_domain_pack_check=ok`

The probes prove that missing family mappings, authority overclaims,
Preference-only confirmation, sports-line leakage, wallet/company-truth
overclaims, and source-quorum overclaims fail validation.

## Acceptance

- All five first-trading-universe strategy families have allowed Preference
  domain-pack mappings.
- Every mapping has an explicit no-trade boundary.
- All mapped domain packs are from the current non-sports Preference catalog
  allowlist.
- `crypto_wallets` remains risk sentiment only.
- Live calls, `search_tools`, domain tools, paid tools, source-quorum credit,
  Preference-only confirmation, trade candidates, execution, broker writes, and
  live capital remain disabled.
- Phase 5 remains blocked until Q4-12 certification passes.

## Required Next Step

Proceed to PREF-8. Add Preference context to shadow-intelligence packets as
challenge-only, non-executable enrichment.
