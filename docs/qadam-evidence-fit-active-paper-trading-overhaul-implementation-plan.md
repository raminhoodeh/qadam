# Qadam Evidence-Fit Active Paper Trading Overhaul

Date: 2026-08-08

Status: EF-0 through EF-10 implemented and certified; EF-7 empirical
five-eligible-day trial collecting in real market time

Scope: Paper-only evidence conversion, gate calibration, and guarded autonomous
paper experimentation

## 1. Executive Decision

Qadam already has most of the required architecture for active paper trading:

- 41 registered data sources across the research universe;
- 19 watched instruments;
- five configured strategy families;
- one emerging power-market strategy sleeve;
- Pattern Score V3;
- Strategy Foundry V3;
- Akber's 6-Stage Filter;
- forward-shadow, portfolio-risk, Router, and guarded PaperOps stages;
- a `discovery_micro` lane for bounded forward evidence collection;
- a US$100,000 Alpaca Paper account and a US$5,000 absolute trade ceiling.

The main remaining problem is not the absence of another trading system. It is
misalignment between the evidence Qadam can genuinely collect and the fields
that its gates expect. Current evidence often reaches Pattern Score and Strategy
Foundry, then stops because:

- current events are not converted into strategy-specific trigger records;
- macro observations are not converted into numeric regime states;
- prediction-market observations are not converted into measured dislocations;
- conditional research directions are not converted into `long`, `short`, or
  `abstain` decisions;
- legacy instrument metadata understates guarded paper-route availability;
- source concentration is measured in a way that conflicts with the lighter
  discovery contract;
- missing execution data can be interpreted as both missing and adverse;
- market-context freshness is not consistently session-aware;
- decision-time shadow records are sometimes required before the pipeline has
  synchronously created them.

This overhaul will repair those contracts. It will make Qadam materially more
likely to submit legitimate, small Alpaca Paper experiments when its available
evidence supports them. It will not guarantee one trade every day, manufacture
triggers, weaken drawdown controls, bypass Akber, or create live-capital
authority.

## 2. Current Verified Baseline

The implementation must regenerate this baseline before changing policy. The
dated 2026-08-08 artifacts currently report:

| Area | Current state | Interpretation |
| --- | --- | --- |
| Registered sources | 41 | Registry size, not 41 equally usable signals |
| Quorum-capable sources | 10 | Sources currently able to contribute to candidate quorum |
| Degraded sources | 10 | Unavailable or failing sources that must not count as evidence |
| Stale or unknown freshness | 26 | Sources requiring classification or refreshed observations |
| Supplemental sources | 9 | Context or confirmation, not automatic causal evidence |
| Watched instruments | 19 | Frozen core observation universe |
| Recorded guarded paper routes | 11 | Direct or approved proxy expressions currently mapped |
| Pattern Score V3 records | 50 | Current research ranking records |
| Score-ready records | 23 | Records with complete score-plane inputs |
| Validated edges | 0 | An honest research result, not an operational defect |
| Discovery hypotheses | 2 | SIL regime-state and XAR event-catalyst hypotheses |
| Current Router state | `watchlist` | Setups exist, but current triggers are inactive |

The runtime universe artifacts still contain legacy fields that report
historical coverage as deferred or zero. Those fields must not override the
provider-backed historical lake and canonical backtest artifacts.

### 2.1 Current Strategy-Informed Ranking

Research scores are ranking signals, not probabilities and not validated edge
claims.

| Strategy family | Current leading score | Current state |
| --- | ---: | --- |
| Semiconductor policy and options asymmetry | 0.72964 | Score-ready, rejected because direction is conditional |
| Silver macro liquidity stress | 0.69724 | SIL discovery hypothesis ready for Akber |
| Defence geopolitical repricing | 0.67852 | XAR discovery hypothesis ready for Akber |
| Crude-oil energy-security disruption | 0.45532 | Blocked by sparse fresh causal support |
| Prediction-market geopolitical dislocation | 0.21816 | Missing measured listed-market context and dislocation |

### 2.2 Existing Discovery Contract To Preserve

The current evidence-adaptive `discovery_micro` policy already permits a
bounded paper experiment without a validated edge when all current tradeability
evidence is complete. Its important terms are:

- minimum research score: 0.45;
- minimum fresh trusted support: one source;
- minimum support-source trust: 0.55;
- full quorum is not required;
- one trusted causal source must be paired with a strategy-specific current
  trigger and independent market confirmation;
- current price and volatility are required;
- at least one confirmation alternative is required;
- positive current expectancy after estimated costs is required;
- minimum reward-to-risk is 1.25;
- a decision-time shadow snapshot is required;
- a validated edge and completed forward outcome are not required;
- target notional is US$500 to US$1,000;
- US$500 is not a forced minimum;
- absolute per-trade ceiling is US$5,000;
- maximum concurrent discovery positions is three;
- maximum positions per correlated cluster is one.

This plan aligns upstream evidence and downstream enforcement with that policy.
It does not create a third execution lane.

## 3. Constitutional Boundaries

Every phase must preserve all of the following:

- paper trading only;
- guarded Alpaca Paper through canonical PaperOps only;
- no direct model-to-broker call;
- no live-capital endpoint or authority;
- no Telegram or dashboard command authority;
- no forced trade or synthetic current trigger;
- no historical or shadow result represented as a paper execution;
- no discovery trade represented as a validated edge;
- no missing value silently replaced by a neutral value;
- no stale, sample, fixture, configured-only, or unavailable provider state
  represented as live evidence;
- no automatic expansion of the US$5,000 trade ceiling or portfolio-risk
  envelope;
- no automatic proof credit;
- no duplicate exposure or ambiguous write retry;
- no backfilled 30-day paper growth trial time;
- no removal of daily-loss, drawdown, liquidity, spread, idempotency,
  correlation, duplicate-exposure, Q-CTRL, or route protections;
- no change to the existing dashboard route structure or established UX.

## 4. Target Operating Model

The completed flow will be:

1. Refresh and classify all 41 source states.
2. Refresh all 19 watched instruments and approved execution proxies.
3. Create strategy-specific current trigger observations.
4. Rank current source-price relationships.
5. Convert eligible relationships into directional hypotheses.
6. Build one immutable, same-generation decision evidence packet.
7. Apply Akber using the evidence profile appropriate to that strategy.
8. Create a decision-time shadow snapshot.
9. Apply portfolio risk and execution checks.
10. Route one clean state through canonical PaperOps.
11. Poll the real paper lifecycle and record the outcome.
12. Feed the outcome into backtesting, attribution, and proposal-first learning.

The validated-strategy lane remains strict. The discovery lane exists to gather
small real forward outcomes before an edge has been validated.

## 5. Canonical Evidence Profiles

### 5.1 Event-Catalyst Profile

Applies to:

- crude-oil energy-security disruption;
- defence geopolitical repricing;
- semiconductor policy and options asymmetry.

Required current evidence:

1. A provider-backed event with a real publication or availability timestamp.
2. A trusted source score at or above the frozen profile threshold.
3. Explicit event-to-market and event-to-instrument relevance.
4. A directional interpretation of the event and observed market response.
5. Current price and volatility.
6. At least one independent confirmation alternative.
7. Current regular-session liquidity and spread before submission.

Historical support and the current trigger may come from different providers.
For example, SEC EDGAR and STOCK Act can provide historical defence support
while a fresh, classified defence RSS event activates the current XAR setup.

### 5.2 Regime-State Profile

Applies to:

- silver macro liquidity stress;
- power scarcity and congestion.

Required current evidence:

1. One or more numeric, timestamped regime observations.
2. A versioned transformation into a regime score, z-score, percentile, change,
   or state classification.
3. A direction rule tied to the strategy's economic mechanism.
4. Current proxy price and volatility.
5. At least one independent market confirmation.
6. Current regular-session liquidity and spread before submission.

Provider availability, a generic macro headline, or an unlabeled market state
does not constitute a regime trigger.

### 5.3 Market-Dislocation Profile

Applies to:

- prediction-market geopolitical dislocation.

Required current evidence:

1. Point-in-time Kalshi and/or Polymarket contract identity and prices.
2. Event normalization and settlement-rule compatibility.
3. A measured probability gap, cross-venue divergence, or divergence from a
   listed-market implied state.
4. An explicit event-to-listed-instrument mapping.
5. A directional hypothesis for the listed execution proxy.
6. Current listed-proxy price, volatility, liquidity, and spread.

`KALSHI:EVENTS` and `POLYMARKET:EVENTS` remain research observations unless a
separate governed venue route is explicitly implemented. They must never be
sent to Alpaca as symbols.

## 6. Strategy And Instrument Contract

| Strategy | Primary usable evidence | Research instruments | Guarded paper expressions | Required repair |
| --- | --- | --- | --- | --- |
| Crude oil | Conflict Tracker, trusted oil RSS, available physical disruption sources | CL=F | BNO; verify USO and XLE | Event classifier and route-map reconciliation |
| Defence | SEC EDGAR, STOCK Act, trusted defence RSS, available conflict sources | Sector and constituent relationships | XAR, ITA, LMT, PPA | Decouple historical support from current trigger provider |
| Semiconductors | SEC EDGAR, RSS, STOCK Act, available patents/policy sources | Sector and constituent relationships | SMH, SOXX, NVDA, QQQ | Direction resolver |
| Silver | FRED, ECB, available BIS/USGS/trade context | SI=F, GLD, SPY relationships | SIL, SLV | Numeric regime builder |
| Prediction markets | Kalshi, Polymarket, supporting geopolitical context | Contract probabilities | Event-specific listed proxies | Dislocation measurement and proxy resolver |
| Power | CAISO and Alpaca power-proxy data | CAISO prices, load, renewable and congestion states | CEG, VST, NRG, TLN, XLU, GRID, UNG | Remain an emerging sleeve until admission |

The power sleeve is not silently added to the frozen 19-instrument universe.
Its separate strategy registry remains authoritative until its admission policy
passes and the universe is versioned explicitly.

## 7. Modular Phase Spine

| Phase | Name | Outcome |
| --- | --- | --- |
| EF-0 | Baseline Freeze And Contract Audit | Preserve current work and prove the exact mismatch |
| EF-1 | Canonical Source And Instrument Truth | One usable source/market contract for every downstream reader |
| EF-2 | Strategy-Specific Trigger Factory | Real events, regimes, and dislocations become typed triggers |
| EF-3 | Direction And Emerging-Strategy Resolution | Strong observations become actionable or explicit abstentions |
| EF-4 | Same-Generation Decision Evidence Packet | Akber receives complete, non-stale, provenance-backed packets |
| EF-5 | Akber Evidence-Fit Recalibration | Filter requirements match each evidence profile |
| EF-6 | Portfolio Risk And Router Alignment | Discovery setups are sized safely without contradictory vetoes |
| EF-7 | Guarded Active Discovery Trial | Five real market days measure actual paper conversion |
| EF-8 | Outcome Learning And Strategy Promotion | Real outcomes refine or reject strategies automatically within bounds |
| EF-9 | Dashboard And Notification Truth | The public surface explains the real conversion funnel |
| EF-10 | Certification, Deployment, And Observation | Release only after end-to-end and safety checks pass |

## 8. EF-0 - Baseline Freeze And Contract Audit

### Objective

Stabilize the current active-discovery implementation and establish a reproducible
before-state without overwriting unrelated worktree changes.

### Build

- Inventory current uncommitted changes in Foundry, Akber, forward shadow,
  portfolio risk, Router, active-discovery automation, and PaperOps.
- Preserve the current dashboard worktree and route structure.
- Record exact policy, schema, artifact, and code hashes.
- Re-run current unit tests and canonical read-only checks.
- Capture current conversion counts:
  - 50 Pattern Score rows;
  - 23 score-ready rows;
  - two discovery hypotheses;
  - two Akber holds;
  - zero Router handoffs;
  - zero new paper orders.
- Produce a field-level matrix showing which producer owns every Akber and risk
  input and where each current value becomes missing.
- Identify legacy readers that still use deferred historical coverage or older
  source-quorum assumptions.

### Runtime Artifacts

- `data/runtime/qadam_evidence_fit_baseline.json`
- `data/runtime/qadam_evidence_gate_ownership_matrix.json`
- `data/runtime/qadam_evidence_fit_contract_drift.json`
- `data/runtime/qadam_evidence_fit_phase_status.json`

### Acceptance

- Current active-discovery tests pass or every failure is documented.
- No current changes are lost or reverted.
- Every decision-critical field has one canonical producer and consumer.
- Baseline artifacts are immutable and checksummed.
- No order, candidate, approval, or proof record is created by the audit.

## 9. EF-1 - Canonical Source And Instrument Truth

### Objective

Replace universal assumptions about 41 sources and 19 instruments with a
strategy-aware, truthful availability contract.

### Build

- Classify every source as one of:
  - `live_fresh`;
  - `historical_only`;
  - `forward_only`;
  - `supplemental_current`;
  - `temporarily_degraded`;
  - `unavailable`;
  - `excluded`.
- Assign every source one or more permitted roles:
  - `historical_causal_support`;
  - `current_trigger`;
  - `market_confirmation`;
  - `supplemental_context`;
  - `negative_control`.
- Preserve source-specific freshness SLAs rather than one global TTL.
- Require provider observation timestamps and publication/availability times.
- Classify every instrument as:
  - `direct_paper_instrument`;
  - `approved_execution_proxy`;
  - `research_price_context`;
  - `prediction_contract_context`;
  - `emerging_sleeve_instrument`.
- Verify the guarded Alpaca route for GLD, SPY, USO, and XLE and update mappings
  only when local broker contracts confirm availability.
- Preserve CL=F and SI=F as research context unless a separately approved paper
  futures route exists.
- Prevent the legacy zero-history/deferred fields from overriding canonical
  historical-lake and backtest state.

### Runtime Artifacts

- `data/runtime/qadam_strategy_source_contract.json`
- `data/runtime/qadam_instrument_role_registry.json`
- `data/runtime/qadam_execution_proxy_registry.json`
- `data/runtime/qadam_source_freshness_sla.json`
- `data/runtime/qadam_universe_contract_checks.json`

### Acceptance

- All 41 sources have one truthful state and at least one allowed role.
- All 19 instruments have one observation role and one explicit route state.
- Context-only instruments cannot become Alpaca order symbols.
- Supplemental sources cannot claim causal quorum unless separately qualified.
- Unavailable and stale sources cannot satisfy a current trigger.
- Source and instrument counts agree across Pattern Score, Foundry, dashboard,
  Akber, Router, and PaperOps.

## 10. EF-2 - Strategy-Specific Trigger Factory

### Objective

Convert the evidence Qadam already gathers into the measured current-trigger
objects required by each strategy profile.

### Build

#### Event Trigger Builder

- Normalize provider events with event identity, publication time, availability
  time, source trust, affected market, affected instruments, catalyst strength,
  direction clues, invalidation clues, and expiry.
- Add strategy-specific classifiers for oil, defence, and semiconductors.
- Require explicit causal relevance instead of ticker-only or broad-category
  overlap.
- Reject irrelevant social packets even when a broad symbol list happens to
  overlap.
- Allow the current event source to differ from historical support sources.
- Deduplicate the same real event across RSS, Telegram, GDELT, filings, and
  other providers.

#### Regime Observation Builder

- Construct silver regime values from available FRED and ECB observations,
  relative SIL/SLV/GLD/SPY movement, volatility, and liquidity context.
- Construct power regime values from CAISO load, renewable shortfall,
  congestion, day-ahead/real-time spread, and proxy-market context.
- Store numeric values, transformations, versions, timestamps, and thresholds.
- Distinguish inactive regimes from missing regimes.

#### Market-Dislocation Builder

- Normalize Kalshi and Polymarket event identity and contract lifecycle.
- Preserve point-in-time odds, liquidity, settlement rules, and timestamps.
- Calculate cross-venue gaps only across compatible contracts.
- Calculate event probability versus listed-market response where defensible.
- Map each dislocation to an affected listed proxy and direction.

### Runtime Artifacts

- `data/runtime/qadam_current_event_triggers.jsonl`
- `data/runtime/qadam_current_regime_observations.jsonl`
- `data/runtime/qadam_current_market_dislocations.jsonl`
- `data/runtime/qadam_trigger_factory_summary.json`
- `data/runtime/qadam_trigger_factory_rejections.jsonl`

### Acceptance

- SIL receives a real numeric regime record or an explicit inactive/missing
  state.
- XAR receives only defence-relevant events with real timestamps and sources.
- Semiconductor setups receive policy, filing, innovation, or sector events
  with explicit relevance.
- Prediction-market gaps contain numeric measurements and compatible contract
  lineage.
- Provider availability and generic headlines cannot activate a trigger.
- Fixtures and synthetic controls cannot appear as current triggers.

## 11. EF-3 - Direction And Emerging-Strategy Resolution

### Objective

Turn strong research relationships into testable directions without guessing,
and allow novel patterns to form emerging strategies safely.

### Build

- Implement a deterministic direction contract with three outcomes:
  - `long`;
  - `short`;
  - `abstain_direction_unresolved`.
- Add a semiconductor direction resolver using event polarity, affected
  company/sector, observed relative response, and invalidation.
- Add event-direction rules for defence and crude oil.
- Add regime-direction rules for silver and power.
- Add event-specific direction and proxy resolution for prediction markets.
- Preserve the raw research direction separately from the actionable direction.
- Require any direction resolver to produce an explanation and evidence IDs.
- Route strategy-agnostic Pattern Score records into an emerging-strategy
  formation review when they contain:
  - a distinct economic mechanism;
  - a distinct source recipe;
  - a paperable instrument or approved proxy;
  - an actionable direction;
  - an invalidation condition;
  - no negative-control identity;
  - no duplicate of a configured family.
- Keep unsupported or directionless findings as research observations.

### Runtime Artifacts

- `data/runtime/qadam_direction_resolutions.jsonl`
- `data/runtime/qadam_direction_resolution_rejections.jsonl`
- `data/runtime/qadam_emerging_strategy_formations.jsonl`
- `data/runtime/qadam_strategy_translation_summary.json`

### Acceptance

- The current 0.72964 semiconductor records no longer fail merely because their
  configured wording is conditional.
- A semiconductor record becomes `long`, `short`, or `abstain`; it never
  defaults to a trade.
- Strategy-agnostic records cannot become paper candidates directly.
- Power remains an emerging strategy until its own frozen admission passes.
- Negative controls and shuffled signals remain ineligible.

## 12. EF-4 - Same-Generation Decision Evidence Packet

### Objective

Give Akber, shadow, risk, and Router one immutable decision-time packet built
from the same completed generation.

### Build

- Create a canonical packet containing:
  - Research Goal and hypothesis lineage;
  - strategy family and evidence profile;
  - historical support evidence;
  - current trigger evidence;
  - direction and horizon;
  - current price and volatility;
  - confirmation alternatives;
  - liquidity, spread, and ADV;
  - expected costs and provisional current expectancy;
  - invalidation and reward-to-risk;
  - source and evidence-channel concentration;
  - proxy and basis-risk state;
  - market session state;
  - expiry and freshness;
  - negative-control status.
- Bind all rows to one generation ID and decision timestamp.
- Separate `missing`, `inactive`, `stale`, `unavailable`, and `adverse` states.
- Rebuild the packet when a decision-critical input changes.
- Refuse mixed-generation joins.
- Make current spread actionable only during the appropriate market session.
- Preserve closed-market quote observations for context without treating them
  as actionable spreads.

### Runtime Artifacts

- `data/runtime/qadam_decision_evidence_packets.jsonl`
- `data/runtime/qadam_decision_evidence_packet_summary.json`
- `data/runtime/qadam_decision_evidence_packet_rejections.jsonl`
- `data/runtime/qadam_generation_integrity_checks.json`

### Acceptance

- Every Akber input references exactly one evidence packet.
- Mixed-generation join count is zero.
- Missing data is never converted into adverse data.
- A weekend or closed-market packet holds for market session rather than
  failing liquidity.
- Source evidence, trigger evidence, and market confirmation are visibly
  distinct.

## 13. EF-5 - Akber Evidence-Fit Recalibration

### Objective

Retain Akber's practical risk value while making each stage require evidence
that the relevant strategy can genuinely collect.

### Current Empirical Basis

Akber currently has 166 measurable historical replays:

- 76 passes;
- 58 holds;
- 32 vetoes;
- 27 false positives removed;
- 63 good observations filtered;
- better result-level mean net return and worst drawdown after filtering;
- negative aggregate selection effect from missed good observations.

These are diagnostic result-level metrics, not portfolio returns. They justify
stage-specific recalibration rather than wholesale removal of the filter.

### Build

- Make Stage 1 Context consume canonical historical support and current market
  context without re-demanding unavailable universal history.
- Make Stage 2 Catalyst profile-specific:
  - event catalyst for oil, defence, and semiconductors;
  - numeric regime state for silver and power;
  - measured market dislocation for prediction markets.
- Keep Stage 3 Confirmation as one of the existing alternatives rather than
  requiring every technical, volume, pricing-gap, and quantum field.
- Keep quantum review optional unless the hypothesis is explicitly
  quantum-dependent.
- Keep Stage 4 Risk focused on positive current expectancy, invalidation,
  reward-to-risk, and uncertainty.
- Keep Stage 5 Execution focused on current session, paperability, spread,
  liquidity, basis risk, and route availability.
- Keep Stage 6 Learning ready to record every pass, hold, veto, and outcome.
- Distinguish:
  - missing required context -> hold;
  - inactive trigger -> watchlist;
  - explicit adverse evidence -> veto;
  - all required evidence clean -> pass.
- Generate threshold proposals from replay and forward evidence, but require a
  versioned reviewed policy update before thresholds change.
- Preserve separate policies for validated strategies and discovery micro
  experiments.

### Runtime Artifacts

- `data/runtime/qadam_akber_evidence_profile_policy.json`
- `data/runtime/qadam_akber_profile_replay.jsonl`
- `data/runtime/qadam_akber_profile_ablation.jsonl`
- `data/runtime/qadam_akber_recalibration_proposals.jsonl`
- `data/runtime/qadam_akber_evidence_fit_checks.json`

### Acceptance

- Current SIL and XAR packets pass Context, Confirmation, and Risk when their
  existing evidence is complete.
- SIL waits only for a measured active regime and actionable execution data.
- XAR waits only for a relevant current event and actionable execution data.
- Missing evidence cannot become a veto.
- Execution ablation controls remain in place because historical removal
  worsened drawdown and expectancy diagnostics.
- Akber pass remains eligibility, not broker authority.

## 14. EF-6 - Portfolio Risk And Router Alignment

### Objective

Remove contradictions that re-block an admitted discovery setup while
preserving material portfolio and execution protections.

### Build

- Measure concentration separately across:
  - causal support sources;
  - current trigger sources;
  - independent market-confirmation channels;
  - open portfolio exposure.
- Do not claim one source plus price confirmation as two causal sources.
- For a valid single-source discovery setup, apply a sizing and uncertainty
  haircut instead of an automatic source-concentration veto.
- Continue to reject duplicated or highly correlated open exposure.
- Treat missing spread as `execution_context_missing`, not
  `spread_exceeds_maximum`.
- Evaluate spread ceilings only when a real actionable spread exists.
- Make market freshness session- and instrument-aware.
- Create the immutable decision-time shadow snapshot immediately after Akber
  pass and before portfolio sizing.
- Separate root blockers from propagated downstream consequences.
- Preserve the current risk envelope:
  - US$500 to US$1,000 discovery target;
  - US$5,000 absolute ceiling;
  - maximum three discovery positions;
  - maximum one per correlated cluster;
  - 0.5% maximum risk per position;
  - 2% daily-loss limit;
  - 8% trailing-drawdown limit;
  - 40% gross-exposure limit.
- Keep Router single-state and idempotent.
- Permit only a clean `experimental_paper_review_candidate` to generate a
  PaperOps handoff.

### Runtime Artifacts

- `data/runtime/qadam_evidence_channel_concentration.jsonl`
- `data/runtime/qadam_discovery_size_proposals.jsonl`
- `data/runtime/qadam_router_root_cause_summary.json`
- `data/runtime/qadam_risk_router_alignment_checks.json`

### Acceptance

- A single trusted causal source plus an independent market confirmation can be
  sized conservatively without a false concentration veto.
- Missing spread creates one hold reason and no contradictory spread veto.
- Closed-market observations cannot create orders.
- Shadow snapshot sequencing is deterministic and same-generation.
- Duplicate exposure, drawdown, daily loss, correlation, and route controls
  still fail closed.
- Router creates exactly one final state per setup.

## 15. EF-7 - Guarded Active Discovery Trial

### Objective

Run a version-bound five-real-market-day trial that measures whether repaired
evidence can reach bounded paper experiments.

### Eligible Market Day

A day is eligible for conversion measurement only when:

- the US market has a real regular trading session;
- the operator service and canonical PaperOps wrapper are healthy;
- Alpaca Paper and market-data reads are fresh;
- at least one strategy profile receives a real current trigger;
- a mapped paper instrument has actionable price, volatility, liquidity, and
  spread data;
- no account-level loss, drawdown, duplicate, or route stop is active.

Market-open days with no real trigger are recorded, but do not count as evidence
that the gates are over-restrictive.

### Build

- Evaluate all 19 watched instruments at least every 20 minutes during the
  regular session.
- Evaluate emerging power instruments on their separately versioned cadence.
- Rank and shortlist distinct setups without forcing a minimum candidate count.
- Target an average of one bounded paper experiment per eligible market day.
- Treat the target as a system-discipline metric, never an order quota.
- Continue allowing multiple distinct setups when each independently passes and
  portfolio limits permit.
- Preserve one position per correlated cluster.
- Record every no-trade cycle using exactly one primary root cause:
  - `market_closed`;
  - `no_real_trigger`;
  - `source_outage`;
  - `mapping_defect`;
  - `evidence_conversion_defect`;
  - `akber_hold`;
  - `akber_veto`;
  - `risk_veto`;
  - `duplicate_exposure`;
  - `route_failure`.
- Treat a real trigger blocked by a missing field that Qadam should have built
  as an implementation defect.
- Submit only through the canonical PaperOps wrapper.
- Poll orders through accepted, filled, open, closed, and postmortem states.

### Runtime Artifacts

- Existing `qadam_active_discovery_trial_*` artifacts, migrated to the new
  evidence packet and policy versions.
- `data/runtime/qadam_active_discovery_conversion_funnel.jsonl`
- `data/runtime/qadam_active_discovery_eligible_days.jsonl`
- `data/runtime/qadam_active_discovery_root_causes.jsonl`
- `data/runtime/qadam_active_discovery_trial_certification.json`

### Acceptance

- Five real eligible market sessions are observed without simulated time.
- Every scan accounts for all 19 core watched instruments.
- Every current trigger has one outcome: rejected, watchlist, Akber hold/veto,
  risk rejection, Router state, or paper handoff.
- If valid triggers occur but zero handoffs result from schema or sequencing
  defects, the trial fails.
- A paper trade is not required when no strategy receives a genuine trigger.
- Any submitted order uses distinct lineage and idempotency material.
- No direct broker call, live-capital route, or proof credit occurs.

## 16. EF-8 - Outcome Learning And Strategy Promotion

### Objective

Use every real decision and outcome to improve future conversion without
silently rewriting strategy or risk policy.

### Build

- Record outcomes for:
  - paper trades;
  - shadow trades;
  - holds;
  - vetoes;
  - inactive triggers;
  - missed opportunities;
  - implementation defects.
- Mature forward returns only after real horizons elapse.
- Attribute each outcome to source support, current trigger, confirmation,
  direction resolver, Akber stage, risk rule, Router, proxy basis, costs, and
  execution quality.
- Re-run focused programmes incrementally as outcomes mature:
  - prediction-market disagreement;
  - STOCK Act sector repricing;
  - Unusual Whales confirmation when provider-backed evidence exists.
- Use outcomes to update backtest challenger sets and calibration proposals.
- Permit automatic admission of a materially proven emerging paper strategy
  only inside the frozen paper-risk envelope and only after the versioned
  promotion checker passes.
- Never allow automatic risk-envelope expansion.
- Require a new strategy version whenever entry, exit, horizon, source recipe,
  proxy, or threshold changes materially.
- Continue negative-control and false-discovery testing.

### Promotion States

1. `research_observation`
2. `discovery_micro_eligible`
3. `forward_evidence_collecting`
4. `validated_edge_candidate`
5. `emerging_paper_strategy`
6. `validated_paper_strategy`

No state grants live-capital authority.

### Runtime Artifacts

- `data/runtime/qadam_active_discovery_outcomes.jsonl`
- `data/runtime/qadam_gate_attribution_ledger.jsonl`
- `data/runtime/qadam_strategy_promotion_proposals.jsonl`
- `data/runtime/qadam_strategy_admission_decisions.jsonl`
- `data/runtime/qadam_strategy_version_registry.json`

### Acceptance

- Every closed discovery trade has complete lineage and a postmortem.
- Holds and vetoes receive counterfactual outcomes when measurable.
- Backtest, shadow, and paper results remain distinguishable.
- Strategy changes remain versioned and reproducible.
- Automatic paper admission cannot mutate the risk envelope.
- Quantum review must beat a matched classical baseline before receiving a
  positive usefulness attribution.

## 17. EF-9 - Dashboard And Notification Truth

### Objective

Explain whether Qadam is inactive because no trigger exists or because a system
component failed, while preserving the current dashboard UX.

### Dashboard Enrichment

Preserve all existing routes, navigation, section order, imagery, typography,
and established interaction patterns. Enrich current modules only.

Add the following evidence-fit views:

- Data Sources:
  - 41 registered;
  - current usable counts by role;
  - profile-specific freshness;
  - sources currently able to trigger each strategy.
- Trading Universe:
  - 19 core instruments;
  - direct paper instruments;
  - execution proxies;
  - research-only futures and prediction contracts;
  - separate emerging power sleeve.
- Pattern Recognition:
  - research score;
  - direction state;
  - evidence profile;
  - current trigger state;
  - next handoff.
- Trading Strategies:
  - five configured families;
  - emerging power strategy;
  - new strategy formations;
  - current source and instrument recipes.
- Decision Room:
  - one conversion funnel from trigger through Akber, shadow, risk, and Router;
  - root blocker rather than repeated propagated blockers.
- Order Monitor:
  - only real guarded paper orders and lifecycle state.
- Learn & Improve:
  - what strengthened;
  - what weakened;
  - what matured;
  - what Qadam proposes to change next.

### Telegram

- Send only material research changes, paper lifecycle changes, or meaningful
  operational blockers.
- Explain the most interesting new pattern, current evidence, decision, and next
  question in plain language.
- Do not repeat unchanged next questions or unchanged IBM results.
- Keep Telegram review-only and command-disabled.

### Runtime Artifacts

- `data/runtime/qadam_evidence_fit_dashboard_summary.json`
- `data/runtime/qadam_strategy_conversion_funnel.json`
- `data/runtime/qadam_material_research_changes.jsonl`
- `data/runtime/qadam_evidence_fit_notification_candidates.jsonl`

### Acceptance

- The dashboard distinguishes registered sources from currently usable sources.
- It distinguishes watched instruments from paperable expressions.
- Each setup shows the first true blocker.
- No internal schema mismatch is presented as market discipline.
- Current UX and route structure remain intact.
- Telegram sends no duplicate or authority-creating message.

## 18. EF-10 - Certification, Deployment, And Observation

### Objective

Certify the complete evidence-to-paper path, deploy without replacing the
current dashboard, and release autonomous observation.

### Build

Create:

- `scripts/check_qadam_evidence_fit_active_paper_trading.py`
- `data/runtime/qadam_evidence_fit_active_paper_trading_certification.json`

The checker must validate:

- source and instrument contract parity;
- same-generation evidence packets;
- profile-specific current triggers;
- direction resolution;
- Akber profile requirements;
- shadow sequencing;
- source/channel concentration semantics;
- session-aware market freshness;
- missing-versus-adverse separation;
- portfolio limits;
- Router single-state behavior;
- idempotency and duplicate exposure;
- canonical PaperOps route;
- lifecycle and postmortem lineage;
- dashboard and Telegram truth;
- disabled live capital;
- zero unauthorized proof credit.

### Negative Safety Probes

Certification must fail when:

- a fixture is labeled live;
- a stale source becomes a trigger;
- a context-only symbol becomes an Alpaca order;
- a prediction contract is sent to Alpaca;
- a missing spread is treated as a valid spread;
- a negative control forms a hypothesis;
- mixed generations are joined;
- a duplicate setup creates a second order;
- a discovery trade claims a validated edge;
- a model or Telegram surface attempts broker authority;
- a live-capital endpoint is enabled.

### Deployment Procedure

1. Freeze and commit the passing root implementation.
2. Generate fresh runtime view models.
3. Verify local dashboard parity and current UX.
4. Build and test the dashboard bundle.
5. Deploy the current dashboard worktree, not a historical snapshot.
6. Verify production aliases and served-bundle hashes.
7. Start the supervised operator service.
8. Run one canonical PaperOps pass.
9. Begin the five-real-market-day calibration.

### Acceptance

- Certification passes with no critical blocker.
- Canonical PaperOps reports fresh guarded operation.
- A real trigger can reach a bounded handoff in an end-to-end test.
- No trade is manufactured when the trigger is inactive.
- The current production dashboard UX is preserved.
- The operator service resumes safely after restart or network interruption.
- The system is ready for autonomous paper observation.

## 19. Cross-Phase Testing Contract

Every phase must include:

- unit tests for new transformations and state transitions;
- schema tests for every new artifact;
- property tests for idempotency and deduplication where applicable;
- fixture tests clearly labeled as fixtures;
- immutable real-artifact replay tests;
- same-generation integration tests;
- negative safety probes;
- dashboard-safe summary checks;
- regression tests for existing validated behavior;
- no-network deterministic tests where practical;
- one real provider-backed read-only verification where required.

No phase may rely only on mocked tests to claim real runtime readiness.

## 20. Phase Status And Dynamic Plan Control

Implementation progress must be durable in:

- `data/runtime/qadam_evidence_fit_phase_status.json`
- `docs/qadam-evidence-fit-active-paper-trading-overhaul-implementation-log.md`

Each phase record must contain:

- phase ID and version;
- implementation state;
- code commit;
- input artifact hashes;
- output artifact hashes;
- checks run;
- pass/fail state;
- blockers;
- deferred work;
- schema migrations;
- dashboard impact;
- authority impact, which must remain none;
- next phase allowed or denied.

The plan may update implementation details as evidence is discovered, but it may
not silently change constitutional boundaries, risk ceilings, trade authority,
or completion criteria.

## 21. Success Metrics

### 21.1 Engineering Conversion Metrics

- Percentage of 19 instruments evaluated each scheduled scan: 100%.
- Mixed-generation decision packets: 0.
- Trigger packets missing an owned field because of an implementation defect: 0.
- Contradictory missing-and-adverse blocker pairs: 0.
- Duplicate order submissions: 0.
- Ambiguous lifecycle records: 0.
- Stale or fixture-backed triggers: 0.

### 21.2 Active Discovery Metrics

- Real profile triggers detected per eligible market day.
- Trigger-to-direction resolution rate.
- Direction-to-Akber review rate.
- Akber pass, hold, and veto rate by stage and profile.
- Akber-pass-to-risk-proposal rate.
- Risk-pass-to-Router-handoff rate.
- Handoff-to-filled-order rate.
- Target: an average of one bounded discovery experiment per eligible market
  day when valid triggers exist.
- Zero-trade days must have one evidence-backed primary root cause.

### 21.3 Research Quality Metrics

- Net-of-cost forward result by strategy and regime.
- Drawdown and tail behavior.
- Missed-opportunity rate caused by each gate.
- False-positive removal by each gate.
- Stability across independent outcomes.
- Classical versus quantum incremental usefulness.
- Core strategy refinements accepted or rejected.
- Emerging strategies formed, promoted, or killed.

Raw trade count is not the sole success metric. The overhaul succeeds when
valid low-risk hypotheses can convert reliably and every non-conversion is
explained by real evidence rather than broken plumbing.

## 22. Expected Trade-Activity Impact

This overhaul should increase paper-trade frequency for concrete reasons:

1. SIL can progress when FRED/ECB conditions produce a real active regime,
   instead of waiting for an event-style catalyst it cannot naturally provide.
2. XAR can use a fresh defence-specific event even when its historical support
   came from SEC EDGAR and STOCK Act.
3. Semiconductor observations can become directional hypotheses rather than
   being discarded because their configured strategy wording is conditional.
4. Kalshi and Polymarket can create measured dislocation hypotheses mapped to
   listed proxies rather than remaining generic source context.
5. Missing spreads and closed-market data will create accurate holds rather
   than contradictory risk vetoes.
6. A valid single-source discovery setup can receive a conservative size
   haircut rather than being blocked by a source-concentration rule designed
   for validated strategies.
7. Decision-time shadow sequencing will no longer block an otherwise complete
   setup because the required record has not yet been generated.

The likely first active lanes are SIL and XAR. Semiconductor should become the
next viable lane after direction resolution. Crude oil depends on improving
current event support and proxy mapping. Prediction markets depend on measured
contract dislocations. Power remains under-evidenced until more independent
outcomes mature.

The plan does not promise one trade on every calendar or market day. It makes
one small paper experiment per genuinely eligible market day a measurable
operating target and treats failure to convert an otherwise complete setup as
an engineering failure.

## 23. Modular Prompt Contract

Each implementation task should use this common prefix:

> Work in `/Users/raminhoodeh/Desktop/qadam`. Read
> `docs/qadam-evidence-fit-active-paper-trading-overhaul-implementation-plan.md`
> first and implement only the requested EF phase. Preserve unrelated worktree
> changes and the current dashboard UX. Keep all changes paper-only, fail-closed,
> and compatible with the canonical PaperOps wrapper. Do not edit secrets or
> `.env` files, enable live capital, call live broker endpoints, bypass Akber,
> bypass portfolio risk, manufacture triggers, force trades, or grant proof
> credit. Add the phase artifacts, checks, tests, status record, and implementation
> log required by the plan. Do not implement later phases.

Recommended sequence:

1. Implement EF-0 and stop for baseline review.
2. Implement EF-1 and stop for universe-contract verification.
3. Implement EF-2 and stop for trigger replay and live read-only verification.
4. Implement EF-3 and stop for direction and emerging-strategy review.
5. Implement EF-4 and stop for same-generation packet certification.
6. Implement EF-5 and stop for Akber replay/ablation review.
7. Implement EF-6 and stop for risk/Router negative probes.
8. Implement EF-7 and begin the five-real-market-day trial.
9. Implement EF-8 after real outcomes begin maturing.
10. Implement EF-9 without changing dashboard routes or established UX.
11. Implement EF-10, deploy, and start certified autonomous observation.

## 24. Final Completion Definition

The overhaul is complete only when:

- all 41 sources and 19 instruments have truthful canonical roles;
- five core strategies and the emerging power sleeve use the correct evidence
  profile;
- current events, regimes, and dislocations are measured rather than inferred
  from provider availability;
- strong semiconductor patterns can resolve direction or abstain;
- strategy-agnostic patterns can form governed emerging strategies;
- Akber requirements match the evidence each profile can collect;
- portfolio risk does not contradict the discovery contract;
- material risk and execution controls remain intact;
- the same-generation shadow, risk, Router, and PaperOps sequence is reliable;
- every no-trade outcome has a truthful root cause;
- valid low-risk setups can produce small guarded Alpaca Paper experiments;
- real outcomes feed back into backtesting, strategy refinement, and admission;
- the dashboard explains the complete funnel without changing its established
  structure;
- final certification and negative safety probes pass;
- live capital remains disabled.

At that point Qadam will be more active because its evidence can actually reach
the gates in the form those gates require. It will still be selective because
selection is necessary for the paper results to teach Qadam anything useful.
