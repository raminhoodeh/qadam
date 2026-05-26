# Qadam Manifested Strategy Draft

Date: 2026-05-24

Status: Draft for Phase 4 strategy manifestation, amended for PREF-10. Approval has not been requested.

No execution. This document is a strategy-governance draft only. It does not create trade candidates, approve risk, stage or submit paper orders, write to brokers, call quantum providers, enable schedulers, or enable live capital.

Verification terms: active instruments, catalyst classes, source weights, model weights, market-confirmation requirements, Preference/PREF MCP, domain packs, source-quorum rule, quota/freshness degradation rule, Preference-only context, quantum role, risk assumptions, no-trade conditions, No execution.

## 1. Active Instruments

The active instruments for the first manifested strategy draft are the five lanes already certified in the Q4-7 Candidate Strategy Universe:

- prediction_markets
- crude_oil
- defence
- silver
- semiconductors

These are strategy-review lanes, not executable instruments. Each lane remains blocked until a later approval event, Signal Integrity review, Risk Agent policy review, Execution Policy review, reconciliation contract, and paper/live capital boundary explicitly allow later phases to proceed.

## 2. Excluded Instruments

Excluded instruments remain outside this draft:

- single-name equities outside approved exposure maps
- crypto perpetuals
- leveraged ETFs
- private placements
- illiquid OTC products
- any instrument supported only by Yahoo Finance confirmation
- any instrument supported only by Preference/PREF MCP context
- any instrument that depends on degraded, quarantined, or missing source evidence

## 3. Strategy Families

The draft strategy universe contains five strategy_family_candidate objects. They are draft strategic hypotheses and cannot be passed to Risk Agent or Execution Policy as executable objects.

### prediction_market_geopolitical_dislocation

Instrument universe: prediction_markets.

Catalyst classes:

- conflict_escalation
- narrative_coordination
- policy_shock

Source weights:

- acled: 0.2166
- conflict_tracker: 0.1267
- gdelt: 0.1613
- polymarket: 0.1889
- rss: 0.1613
- telegram: 0.1452

Risk assumptions:

- Binary-event probability can move before official confirmation.
- Prediction-market pricing must be independently corroborated before any later risk review.

Invalidation conditions:

- Polymarket or narrative sources are stale, unavailable, or single-source only.
- Conflict source posture contradicts the event narrative.
- Required source weight is zero because the source is quarantined or missing.
- Any downstream component requests risk, execution, paper-order, broker-write, or live-capital authority.

No-trade conditions:

- No non-Yahoo independent market confirmation is present.
- Signal Integrity remains blocked or hold-only for missing second-source evidence.
- Candidate remains outside an approved Manifested Strategy Document.
- Risk Agent or Execution Policy handoff is requested before Phase 4 approval.

### crude_oil_energy_security_disruption

Instrument universe: crude_oil.

Catalyst classes:

- energy_security
- shipping_chokepoint
- conflict_fire

Source weights:

- acled: 0.2196
- bis: 0.1379
- conflict_tracker: 0.1285
- fred: 0.1636
- gdelt: 0.1636
- nasa_firms: 0.1868

Risk assumptions:

- Energy-security shocks can reprice crude before policy confirmation.
- Macro liquidity context can amplify or dampen commodity shock transmission.

Invalidation conditions:

- Physical or conflict evidence fails to confirm the claimed disruption.
- Macro source posture contradicts the commodity-risk narrative.
- Required source weight is zero because the source is quarantined or missing.
- Any downstream component requests risk, execution, paper-order, broker-write, or live-capital authority.

No-trade conditions:

- Physical evidence is degraded or unavailable.
- Crude market confirmation is stale, unavailable, or Yahoo-only.
- Candidate remains outside an approved Manifested Strategy Document.
- Risk Agent or Execution Policy handoff is requested before Phase 4 approval.

### defence_repricing_geopolitical_watch

Instrument universe: defence.

Catalyst classes:

- defence_posture_shift
- conflict_escalation
- procurement_or_policy_signal

Source weights:

- acled: 0.2040
- conflict_tracker: 0.1193
- gdelt: 0.1518
- nasa_firms: 0.1735
- rss: 0.1518
- sec_edgar: 0.1996

Risk assumptions:

- Defence instruments can reprice around conflict posture and procurement narratives.
- Company-level exposure requires filing or market confirmation before future strategy approval.

Invalidation conditions:

- Conflict escalation is not corroborated across independent sources.
- Company-level filings or market confirmation do not support the exposure thesis.
- Required source weight is zero because the source is quarantined or missing.
- Any downstream component requests risk, execution, paper-order, broker-write, or live-capital authority.

No-trade conditions:

- No company-level exposure map exists.
- Options or equity market confirmation is absent, stale, or Yahoo-only.
- Candidate remains outside an approved Manifested Strategy Document.
- Risk Agent or Execution Policy handoff is requested before Phase 4 approval.

### silver_macro_liquidity_stress

Instrument universe: silver.

Catalyst classes:

- liquidity_stress
- rates_shock
- currency_confidence_shift

Source weights:

- bis: 0.1229
- bls: 0.1979
- ecb: 0.1958
- fred: 0.1459
- rss: 0.1458
- sec_edgar: 0.1917

Risk assumptions:

- Silver can act as a stress-sensitive macro proxy during liquidity or confidence breaks.
- Rates and institutional-policy data must dominate private world-model priors.

Invalidation conditions:

- Rates, liquidity, or institutional-source posture contradicts the stress thesis.
- Silver market confirmation is unavailable or fails to show a pricing gap.
- Required source weight is zero because the source is quarantined or missing.
- Any downstream component requests risk, execution, paper-order, broker-write, or live-capital authority.

No-trade conditions:

- Macro source quorum is below threshold.
- No non-Yahoo market confirmation or transaction-cost assumption exists.
- Candidate remains outside an approved Manifested Strategy Document.
- Risk Agent or Execution Policy handoff is requested before Phase 4 approval.

### semiconductor_policy_options_asymmetry

Instrument universe: semiconductors.

Catalyst classes:

- export_control_shift
- ai_chip_supply_constraint
- policy_bargain

Source weights:

- alpaca: 0.2032
- fred: 0.1580
- gdelt: 0.1580
- patents: 0.1151
- rss: 0.1580
- sec_edgar: 0.2077

Risk assumptions:

- Semiconductor catalysts are asymmetric when policy timing and options distribution diverge.
- Head of Quant output can annotate ambiguity only after Signal Integrity context exists.

Invalidation conditions:

- Policy, filing, or patent evidence fails to support the catalyst.
- Options or equity market confirmation is stale, unavailable, or single-source.
- Required source weight is zero because the source is quarantined or missing.
- Any downstream component requests risk, execution, paper-order, broker-write, or live-capital authority.

No-trade conditions:

- Signal Integrity flags missing price confirmation or second-source evidence.
- Head of Quant recommendation is missing, rejected, or treated as execution authority.
- Candidate remains outside an approved Manifested Strategy Document.
- Risk Agent or Execution Policy handoff is requested before Phase 4 approval.

## 4. Catalyst Classes

The catalyst classes in this draft are:

- conflict_escalation
- narrative_coordination
- policy_shock
- energy_security
- shipping_chokepoint
- conflict_fire
- defence_posture_shift
- procurement_or_policy_signal
- liquidity_stress
- rates_shock
- currency_confidence_shift
- export_control_shift
- ai_chip_supply_constraint
- policy_bargain

Every catalyst class requires live-source or durable replay support before it can influence a later approved-shadow strategy.

## 5. Source Weights

Source weights are normalized inside each strategy_family_candidate from Q4-7 Trust Score recalculation. They are review weights only. They do not create signal authority.

Source weights are capped by the following rules:

- Quarantined sources receive zero candidate weight.
- Missing sources receive zero candidate weight.
- Durable replay context can support review weight, but it cannot create orders.
- Yahoo Finance can provide supplemental market-confirmation context only and cannot be the sole source for any candidate.
- Preference/PREF MCP receives no canonical source weight and cannot satisfy source quorum.
- Preference-backed upstream sources can receive canonical source weight only after a separate source-registry promotion decision for that upstream source.

## 6. Model Weights

Model weights are shared across this draft:

- data_veracity: 0.24
- trust_score: 0.22
- signal_integrity_patterns: 0.16
- strategy_lead_challenges: 0.16
- resource_registry: 0.10
- world_model_lens: 0.08
- head_of_quant_shadow_annotation: 0.04

Model weights are strategy-review weights only. They cannot approve risk, create paper orders, write to brokers, or enable live capital.

## 7. Market-Confirmation Requirements

Market-confirmation requirements apply to every strategy family:

- Non-Yahoo independent market confirmation is required.
- Yahoo Finance is supplemental market confirmation only.
- Yahoo-only confirmation is not allowed.
- A pricing gap is required.
- Stale confirmation is not allowed.
- Single-source confirmation is not allowed.
- Market confirmation cannot provide order, fill, receipt, or reconciliation truth.

## 8. Preference/PREF MCP Role

Preference/PREF MCP is a supplemental_multi_source_data_plane. It can enrich Phase 4 strategy manifestation with read-only context across prediction markets, physical movement, filings, macro commodities, crypto wallets, and news or narrative sources. It is not source 36, not a canonical source, not a market-confirmation pass by itself, not a broker, not a fill or receipt source, and not reconciliation truth.

Approved domain packs for this draft:

- prediction_markets
- physical_movement
- filings_corporate
- macro_commodities
- crypto_wallets
- news_narrative

Preference domain packs by strategy family:

| Strategy family | Preference domain packs | Role |
| --- | --- | --- |
| prediction_market_geopolitical_dislocation | prediction_markets, news_narrative | event probability, liquidity, and narrative context only |
| crude_oil_energy_security_disruption | physical_movement, macro_commodities, prediction_markets | vessel chokepoint, weather, commodity, and oil-linked market context only |
| defence_repricing_geopolitical_watch | filings_corporate, news_narrative, prediction_markets | filing metadata, procurement narrative, and conflict-market context only |
| silver_macro_liquidity_stress | macro_commodities, news_narrative | macro, commodities, weather, and liquidity-stress narrative context only |
| semiconductor_policy_options_asymmetry | filings_corporate, news_narrative, macro_commodities, crypto_wallets | filing, policy, macro, and wallet risk-sentiment context only |

Source-quorum rule: Preference/PREF MCP cannot satisfy source quorum. Qadam may inspect explicit upstream identities from Preference for context, but only an individually promoted upstream source with its own registry decision can count toward canonical quorum.

Quota/freshness degradation rule: if Preference identity is unverified, quota metadata is missing, context is stale, provenance is missing, or an approved domain pack is unavailable, Preference becomes hold-only context and cannot increase confidence or advance strategy state.

Preference-only context is a hold condition, not corroboration. A strategy family may use Preference to ask sharper questions or challenge a thesis, but it cannot use Preference-only context to pass Signal Integrity, market confirmation, source quorum, Risk Agent handoff, Execution Policy handoff, paper orders, broker writes, quantum provider calls, schedulers, or live capital.

No-trade conditions added by Preference:

- Preference-only context is present without independent canonical evidence.
- Preference provenance is missing, invalid, quarantined, or source-washed through the aggregator.
- Preference quota, identity, freshness, or domain-pack posture is degraded.
- A domain tool would require paid-tool approval that has not been explicitly granted.
- Any component treats Preference orderbook depth as venue permission, execution permission, fill truth, receipt truth, or broker truth.
- Any component treats wallet or KOL flow as company truth instead of risk-sentiment context.

No execution authority:

- live_mcp_call_allowed: false
- paid_tool_calls_allowed: false
- source_quorum_credit_allowed: false
- preference_only_confirmation_allowed: false
- trade_candidate_creation_allowed: false
- risk_handoff_allowed: false
- execution_allowed: false
- paper_order_allowed: false
- broker_write_allowed: false
- live_capital_enabled: false

## 9. Quantum Role

The quantum role in this draft is shadow annotation only.

Allowed Head of Quant jobs:

- pattern_recognition
- strategy_collapse

Quantum restrictions:

- provider_call_allowed: false
- hardware_submission_allowed: false
- scheduler_enabled: false
- confidence_delta_allowed: false
- trade creation allowed: false

Head of Quant output may annotate ambiguity after Signal Integrity context exists, but it cannot route risk, execution, paper orders, hardware, or live capital.

## 10. World-Model Role

Private world-model frames are hypothesis lenses only. Q4-6 classified all five frames as provisional. They can help generate uncomfortable questions and red-team prompts, but they cannot count as factual evidence, increase confidence, or trigger trades.

## 11. Resource Registry Role

Resource Registry entries are non-live references. They can shape strategy language and risk framing, but they are not observations. Rejected or provisional references cannot be promoted into factual evidence. Private foundational priors remain separate from live data sources.

Preference/PREF MCP is listed in the Resource Registry as a supplemental data-plane reference. That registry presence does not make it active strategy provenance, source quorum, canonical rank input, or execution authority.

## 12. Approval State

Approval state: not_requested.

Approval is required before any strategy can become approved-shadow. This amended draft does not log an approval event, persist a strategy toggle, or certify Phase 4. The existing Q4-10 approval posture remains amendments_required until a Fund Manager explicitly approves this Preference-aware document.

## 13. Execution Boundary

No execution. This draft cannot:

- create trade candidates
- approve risk
- hand off to Risk Agent
- hand off to Execution Policy
- stage paper orders
- submit paper orders
- write to brokers
- call quantum providers
- submit quantum hardware jobs
- enable schedulers
- enable live capital

The next required step is Q4-9 Strategy Toggle Contract, after Q4-8 validation is complete.
