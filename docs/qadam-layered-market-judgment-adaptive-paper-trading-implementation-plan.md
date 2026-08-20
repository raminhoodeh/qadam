# Qadam Layered Market Judgment And Adaptive Paper Trading Implementation Plan

Date: 2026-08-20

Status: Implemented; five-session real-market canary pending

Scope: Consolidate Akber's qualitative market judgment into Qadam's existing
canonical decision transaction so bounded uncertainty more often changes paper
trade size, timing, or entry conditions instead of terminating an otherwise
usable setup.

## 1. Executive Decision

Qadam does not need another execution lane, another pattern score, or a looser
copy of Akber's Filter. It needs one better translation layer between research
and the existing guarded paper route.

Akber's feedback identifies the missing capability precisely. A trader can hold
several apparently conflicting truths at once:

- a theme may be structurally overcrowded or expensive;
- geopolitical risk may remain elevated;
- an index can continue rising even while participation narrows;
- low trading volume can mean weak participation rather than an immediate sell
  signal;
- low implied volatility can indicate a quiet expected range without predicting
  direction;
- the most likely path may be sideways movement or a modest decline before a
  later catalyst resumes the trend.

Qadam currently represents too much of this nuance as binary field completion.
When a required field is absent, stale, supplied under a different strategy
alias, or available only when the market opens, a potentially usable idea can
be held as though it had failed. At the same time, simply deleting those checks
would create activity without judgment.

This implementation will replace that false choice with a typed action policy:

1. Explicitly adverse evidence or a hard safety failure stops the setup.
2. Refreshable execution uncertainty delays entry and schedules a bounded retry.
3. Missing optional confirmation reduces size.
4. Conflicting but bounded evidence can produce a smaller discovery experiment.
5. An inactive trigger remains on the watchlist.
6. Unknown or unclassified evidence fails closed until its contract is repaired.

The result should be more frequent, smaller and better-explained paper
experiments whenever Qadam has enough evidence to take bounded risk. It must not
create a trade quota, treat a research score as a probability, manufacture
expected return, or bypass hard portfolio and execution controls.

## 2. Current Verified Baseline

The implementation must regenerate this baseline before changing policy. The
following facts were inspected from the current code and runtime on 20 August
2026.

| Area | Current state | Consequence |
| --- | --- | --- |
| Source universe | 41 registered sources | Broad observation capacity, but not 41 equally fresh causal signals |
| Trading universe | 19 watched instruments | The frozen core universe and approved proxy mappings remain authoritative |
| Strategy architecture | Five core families plus emerging research sleeves | New evidence should refine these or form an emerging strategy, not bypass them |
| Discovery policy | `discovery_micro` exists | Small paper experiments can proceed without a validated edge when current tradeability is complete |
| Trade ceiling | US$5,000 per paper trade | This remains an absolute ceiling, not a target |
| Soft evidence handling | Akber computes size multipliers | The multiplier is not currently carried through the risk proposal as a canonical sizing input |
| Missing execution context | Usually becomes a hold | Some cases should instead enter a persistent market-hours refresh queue |
| Signal identity | Economic signal identity exists in forward shadow | A trade-level evidence-change and re-entry cooldown contract is not obvious |
| Strategy naming | `semiconductor_policy_asymmetry` and `semiconductor_policy_options_asymmetry` both occur | The same strategy can receive inconsistent profile treatment |
| Recent paper activity | 19 filled orders in the trailing window ending 2026-08-20T07:03:46Z | The route is active, but raw order count must be separated into entries, exits and repeat round trips |
| Recent order composition | 10 entries, 9 exits across BNO, NVDA, USO and XLE | Activity is a useful health signal, but not proof of 19 independent decisions or profitable behavior |

The recent order activity is important. It proves that Qadam can reach guarded
Alpaca Paper and manage entries and exits. It does not by itself prove that the
decision system is healthy. Repeated entries and exits from an unchanged thesis
could be churn, while zero orders on a day with no eligible setup could be
correct behavior.

The new health model must therefore measure both activity and quality.

## 3. Problem Statement

The current implementation has four linked problems.

### 3.1 Binary Interpretation Of Incomplete Evidence

The system often asks whether a field is present rather than what the missing
field means. Missing implied volatility, a closed-market spread, a delayed
provider response and a missing invalidation point are not equivalent:

- missing implied volatility may be optional for an equity event setup;
- a closed-market spread should be refreshed at the next market open;
- a provider failure should trigger a bounded retry or repair record;
- missing invalidation means the risk cannot be bounded and must remain a hold.

### 3.2 Akber's Soft Multiplier Does Not Control Final Size End To End

`qadam_akber_filter_v3.py` already calculates a
`soft_evidence_size_multiplier`. The portfolio-risk engine independently sizes
from confidence, uncertainty, concentration and portfolio limits, but does not
consume that Akber multiplier. The intended behavior therefore exists in one
artifact without deterministically affecting the proposed quantity.

### 3.3 Market Judgment Is Compressed Into One Direction

A high research score only says that a relationship deserves attention. It
does not distinguish:

- a strong structural thesis from a weak entry today;
- a long-term bearish valuation view from short-term positive price behavior;
- expected volatility magnitude from direction;
- a likely path from the final destination;
- a long trigger from a short trigger.

This can make a conditional idea look incomplete or contradictory when it
should instead carry separate long, short and wait branches.

### 3.4 Order Count Is Not Yet An Activity-Quality Contract

The dashboard can show orders and fills, but the operating system does not yet
make the following distinction a first-class health judgment:

- a new entry from a distinct economic hypothesis;
- a protective or planned exit;
- a same-signal re-entry after material evidence changed;
- an accidental duplicate;
- rapid churn after no evidence change;
- a missed eligible setup caused by an internal contract failure;
- a legitimate no-trade day because no trigger qualified.

## 4. Constitutional Boundaries

Every phase must preserve all of the following:

- paper trading only;
- guarded Alpaca Paper through canonical PaperOps only;
- no direct model-to-broker call;
- no live-capital endpoint or authority;
- no dashboard or Telegram command authority;
- no forced trade and no daily trade quota;
- no research score treated as probability, expected return or approval;
- no stale, sample, fixture, fallback or configured-only record represented as
  live evidence;
- no missing expected return invented from a research score;
- no automatic expansion of the US$5,000 per-trade ceiling;
- no removal of daily-loss, drawdown, exposure, duplicate, idempotency,
  liquidity, route or Q-CTRL protections;
- no automatic admission of a materially new strategy or expanded risk
  envelope;
- no automatic proof credit;
- no historical, shadow or engineering-control result presented as a paper
  trade;
- no backfilled paper trial time;
- no new parallel Router, risk engine, Akber implementation or broker route;
- no change to the established dashboard routes or overall dashboard UX.

This plan relaxes treatment of uncertainty. It does not relax treatment of
danger.

## 5. Target Operating Model

The completed canonical flow will be:

1. Observe current source and market evidence.
2. Build a point-in-time market-state packet.
3. Rank relationships without treating ranking as tradeability.
4. Express a structural thesis and its economic mechanism.
5. Build separate long, short and wait activation paths.
6. Resolve each missing or conflicting field into one typed action.
7. Apply Akber's six stages using the correct evidence profile.
8. Convert bounded uncertainty into one auditable size multiplier.
9. Refresh execution-only evidence at the correct market time.
10. Create the decision-time shadow snapshot synchronously.
11. Apply portfolio risk and one canonical Router decision.
12. Submit exactly once through guarded Alpaca Paper when eligible.
13. Manage exits, cooldowns and evidence-based re-entry.
14. Attribute the outcome and recalibrate only through versioned proposals.

The canonical transaction must be the source of truth. Dashboard, Telegram and
health artifacts are projections of it and must not independently decide or
authorize anything.

## 6. Layered Market Judgment Model

Qadam will keep Akber's existing six external stages. It will enrich the
evidence inside those stages rather than add another public filter.

| Akber stage | Internal judgment layers | Question answered |
| --- | --- | --- |
| Context | Structural thesis, economic mechanism, macro regime, geopolitical regime | Why should this market relationship exist at all? |
| Catalyst | Fresh event, earnings statement, policy change, supply constraint or regime transition | Why might the relationship matter now? |
| Confirmation | Breadth, participation, volume, relative strength, realised volatility, implied volatility, skew and nonlinear review | Is the market beginning to behave in a way consistent with the thesis? |
| Risk | Expected net return class, uncertainty, invalidation, time horizon, correlation and loss budget | How much can Qadam risk if the thesis is wrong? |
| Execution | Session, quote, spread, liquidity, paperability and order lifecycle | Can the idea be expressed safely now? |
| Postmortem Learning | Intended path, actual path, entry quality, exit quality and counterfactual | Did the filter, size and timing improve the result? |

### 6.1 Structural Thesis Layer

This layer records the durable claim without turning it into immediate timing.
Examples include AI-capacity constraints, energy-security disruption, policy
pressure, geopolitical repricing and liquidity stress.

Required fields:

- thesis ID and version;
- strategy family or emerging-strategy lineage;
- economic mechanism;
- affected markets and approved paper proxies;
- expected horizon;
- confirming observations;
- falsifiers;
- regime assumptions;
- source requirements;
- author type: provider evidence, model inference or trader prior.

### 6.2 Macro And Regime Layer

This layer measures the surrounding environment, including:

- geopolitical escalation or de-escalation;
- rates, liquidity and currency pressure;
- sector and index trend;
- volatility regime;
- risk-on, risk-off or mixed state;
- concentration and correlation regime.

A regime label must be generated from timestamped observations. Narrative copy
alone cannot satisfy it.

### 6.3 Participation, Breadth And Concentration Layer

This layer translates Akber's observation that a market can continue higher on
low participation even when the structural story looks overheated.

It should measure, where provider-backed data permits:

- current volume versus a rolling and seasonal baseline;
- advance-decline or equivalent breadth;
- equal-weight versus cap-weight index performance;
- top-constituent contribution;
- sector relative strength;
- price movement with expanding or contracting participation;
- divergence between the index and the instruments Qadam actually trades.

Low volume must be labelled as weak participation, not as proof that there are
no sellers.

### 6.4 Options And Volatility Layer

This layer should use approved, provider-backed options evidence where it is
available:

- implied volatility level and percentile;
- realised versus implied volatility;
- term structure;
- skew;
- put-call or flow context;
- event-specific volatility changes.

Implied volatility estimates expected movement, not direction. Missing implied
volatility may reduce confidence for an equity setup, but it can be a hard
requirement only for a strategy whose mechanism explicitly depends on options
pricing.

Provider states must be explicit: `live`, `stale`, `rate_limited`,
`unavailable`, `historical_only`, `supplemental` or `not_entitled`. Existing
Unusual Whales and Alpaca options capabilities should be inspected before any
new subscription is proposed. TradingView remains supplemental and cannot
satisfy a hard execution requirement by itself.

### 6.5 Tactical Path Layer

This layer represents the path, not just the eventual destination.

For each setup it must define:

- long activation condition;
- short activation condition;
- wait or range-bound condition;
- price level or state that invalidates each branch;
- confirmation window;
- expected holding horizon;
- evidence expiry;
- entry style: immediate, limit, delayed confirmation or watchlist;
- planned exit and review conditions.

For the semiconductor example, an "overheated but not breaking" state must not
automatically become a short. A bearish branch can require breakdown, worsening
breadth and expanding downside participation. A bullish branch can require a
pullback to stabilize, relative strength to improve and capacity evidence to
remain supportive.

### 6.6 Strategy-Specific Layering

The policy must be calibrated to the strategy mechanism rather than applied as
one generic checklist.

| Current strategy | Evidence profile | Structural and causal evidence | Tactical evidence that may change timing or size | Evidence that remains hard |
| --- | --- | --- | --- | --- |
| Crude-oil energy-security disruption | Event catalyst | Conflict, maritime disruption, physical supply and energy-security observations | CL=F, USO, BNO and XLE response, participation, volatility and current spread | Current catalyst, deterministic direction, paperable proxy, positive after-cost estimate, invalidation and current execution context |
| Defence geopolitical repricing | Event catalyst | Conflict, policy, contracts, filings, STOCK Act, earnings calls, backlog and capacity statements | ITA, XAR, PPA and LMT relative strength, breadth, volume and sector participation | Current catalyst, instrument mapping, bounded risk and executable quote |
| Semiconductor policy and options asymmetry | Event catalyst | Policy, filings, patents, earnings transcripts, supply constraints and capacity commentary | SMH, SOXX, NVDA and QQQ relative strength, index breadth, volume, realised volatility, IV and skew | Current catalyst and risk remain hard; IV is hard only for an options-dependent mechanism and otherwise adjusts timing or size |
| Silver macro liquidity stress | Regime state | Rates, dollar, liquidity, trade and commodity-regime observations | SI=F, SLV, SIL, GLD and SPY relative behavior, volatility and flow confirmation | Numeric current regime, directional rule, invalidation and executable proxy context |
| Prediction-market geopolitical dislocation | Market dislocation | Normalized Kalshi or Polymarket contracts, settlement rules and point-in-time probabilities | Cross-venue disagreement, liquidity, repricing speed and listed-proxy response | Contract identity, comparable event definition, measured dislocation, listed paper proxy and current execution evidence |
| Power scarcity and congestion | Regime state, emerging | Grid, load, weather, fuel, outage and congestion observations from approved providers | Current power or utility proxy reaction, seasonality, participation and spread | Point-in-time grid state, approved proxy, current trigger, bounded economics and execution context |

The market and social source families may confirm or challenge these mechanisms,
but source count alone cannot make a setup tradeable. The current 19-instrument
universe remains frozen unless a separately governed instrument change is
approved.

## 7. Canonical Data Contracts

The implementation must extend the existing `DecisionTransaction` rather than
create a second decision ledger.

### 7.1 `MarketJudgmentEnvelope`

Required fields:

- `judgment_id`;
- `decision_id` and `generation_id`;
- `economic_signal_identity_id`;
- `strategy_family_id` and version;
- `research_goal_id`;
- `structural_thesis`;
- `regime_state`;
- `participation_state`;
- `volatility_state`;
- `long_path`, `short_path` and `wait_path`;
- `selected_path` and reason;
- `evidence_ids`;
- `observed_at`, `available_at`, `expires_at`;
- `provider_states`;
- `missingness_assessment`;
- `authority` showing no broker authority.

### 7.2 `TraderPrior`

Akber's observations must be preserved as versioned hypotheses, not silently
converted into market facts.

Required fields:

- prior ID and author;
- natural-language claim;
- economic mechanism;
- applicable instruments and regimes;
- expected path;
- observable confirmations;
- falsifiers;
- expiry and review date;
- confidence as a qualitative prior, not probability;
- evidence required before the prior can influence size or timing;
- explicit `cannot_satisfy_source_quorum_alone=true`;
- explicit `cannot_create_order=true`.

### 7.3 `UncertaintyAction`

Every missing or conflicting item must resolve to exactly one action:

- `hard_stop`;
- `adverse_veto`;
- `refresh_and_retry`;
- `delay_until_market_window`;
- `soft_size_haircut`;
- `two_sided_shadow`;
- `watchlist_inactive`;
- `repair_required`.

The action includes the owner, reason, retry time, expiry, applied multiplier and
whether it can veto.

### 7.4 `AdaptiveSizeDecision`

Required fields:

- base risk notional;
- each independent multiplier and its source;
- combined multiplier;
- proposed notional before and after broker rounding;
- binding limit;
- expected loss at invalidation;
- portfolio effect;
- reason a smaller experiment is preferable to a hold;
- hard limits proving the size cannot exceed the frozen policy.

### 7.5 `ActivityQualitySnapshot`

Required rolling windows: 24 hours, current market day, five market days and 30
calendar days.

Required measures:

- raw order records;
- submitted orders;
- filled orders;
- entries and exits;
- distinct economic hypotheses;
- distinct instruments and correlated clusters;
- completed round trips;
- same-signal re-entries;
- duplicate or rejected writes;
- average and median holding time;
- realised and unrealised paper P&L;
- spread and slippage where measurable;
- eligible setups seen;
- eligible setups submitted;
- eligible setups missed due to internal defects;
- legitimate hard stops;
- delayed-entry queue state;
- churn warnings.

## 8. Missingness And Action Policy

This policy is the centre of the overhaul.

| Evidence state | Default action | Example |
| --- | --- | --- |
| Hard safety failure | Stop | Drawdown breach, live route, duplicate exposure, unsupported instrument |
| Explicit adverse evidence | Veto | Non-positive after-cost expectation, spread above hard maximum, thesis invalidated |
| Required but refreshable | Refresh and retry | Quote provider temporary failure during an otherwise active market session |
| Required only at execution time | Delay until valid window | Regular-session spread unavailable while the market is closed |
| Optional confirmation missing | Reduce size | IV unavailable for an equity event setup that does not depend on options |
| Conflicting but bounded | Reduce size or shadow both paths | Strong structural thesis but weak breadth and neutral price action |
| Trigger inactive | Watchlist | Thesis remains valid but no current activation |
| Provider permanently unavailable | Use an approved substitute or typed hold | No entitled options history and no equivalent profile measurement |
| Unknown or unowned field | Repair required | A producer emits a field with no policy classification |

Rules:

1. A soft field may not enter `missing_critical_context`.
2. A hard field may never be converted to a size haircut.
3. A refreshable field may not become a permanent hold without exhausting its
   retry policy or reaching expiry.
4. The same missing item may not be represented as both absent and adverse.
5. A strategy-specific profile may promote a normally soft field to hard only
   when the economic mechanism requires it.
6. All aliases must resolve before profile lookup.
7. An unclassified field fails closed and creates one repair request.

## 9. Adaptive Sizing Policy

### 9.1 Principle

Sizing must express uncertainty once. The current Akber soft multiplier must be
propagated into the risk setup and applied exactly once after the base
risk-capacity calculation.

The conceptual calculation is:

```text
base capacity = minimum of risk, exposure, liquidity, volatility, tail and policy caps
evidence multiplier = product of approved independent uncertainty adjustments
final notional = round down(base capacity x evidence multiplier)
```

The implementation must prevent double-counting between:

- confidence-class multiplier;
- model uncertainty;
- source-concentration haircut;
- Akber soft-evidence multiplier;
- regime-conflict multiplier;
- execution-quality multiplier.

### 9.2 Seed Behavior To Calibrate

Exact values must be frozen only after replay and ablation testing. The initial
policy should test bounded ranges rather than assume a missing confirmation is
worth a specific percentage.

| State | Candidate multiplier range |
| --- | ---: |
| Complete current evidence | 1.00 |
| One optional confirmation missing | 0.75 to 0.90 |
| Two optional confirmations missing | 0.40 to 0.70 |
| Structural thesis strong, tactical evidence mixed | 0.25 to 0.50 |
| Single causal source plus independent market confirmation | At or below 0.50 |
| Hard evidence or safety requirement absent | No size permitted |

The existing US$500 to US$1,000 discovery target remains a target, not a forced
minimum. A smaller whole-share position may be valid when the risk calculation
rounds down safely. No multiplier can increase notional above base capacity or
the US$5,000 hard ceiling.

## 10. Expected Return Policy

Qadam must not require validated-edge certainty from an experimental setup, but
it must retain a defensible reason to expect positive economics.

The expected-return estimator will support three labelled classes:

1. `validated_estimate` - untouched and forward evidence supports a positive
   lower bound after costs.
2. `provisional_empirical_estimate` - event- or regime-conditioned observations
   support a positive point estimate after conservative costs, with uncertainty
   explicitly reducing size.
3. `scenario_bound_estimate` - a defined entry, target, invalidation and
   probability range produce positive expected value under conservative
   assumptions, but the estimate remains experimental.

Rules:

- validated strategies require the stricter positive lower-bound standard;
- discovery-micro experiments may use a positive conservative point estimate
  when downside is bounded, source lineage is complete and uncertainty reduces
  size;
- a research score cannot be converted into return;
- negative estimated return is an adverse veto, not uncertainty;
- missing costs, price, spread, invalidation or outcome horizon remains a hard
  hold;
- each estimate records its sample size, method, confidence interval or
  scenario range, cost model and expiry.

## 11. Phased Implementation

### LMJ-0: Baseline, Ownership And Alias Reconciliation

Build:

- regenerate current source, instrument, strategy, candidate, Akber, risk,
  Router, PaperOps and order-lifecycle baselines;
- produce a 24-hour activity-quality baseline instead of a raw order count;
- create one canonical strategy alias registry;
- map every required field to one producer, one owner and one freshness rule;
- identify all legacy readers that can still override canonical decisions.

Required repair:

- resolve `semiconductor_policy_asymmetry` to the canonical
  `semiconductor_policy_options_asymmetry` before evidence-profile lookup.

Artifacts:

- `data/runtime/qadam_layered_judgment_baseline.json`;
- `data/runtime/qadam_strategy_alias_registry.json`;
- `data/runtime/qadam_activity_quality_baseline.json`;
- `data/runtime/qadam_decision_field_ownership.json`.

Acceptance:

- every configured strategy resolves to exactly one evidence profile;
- every decision field has exactly one canonical owner;
- trailing activity separates entries, exits, distinct signals and repeat
  round trips;
- no runtime artifact is promoted merely because it is newer than the canonical
  transaction.

### LMJ-1: Decision Transaction V2

Build:

- extend `DecisionTransaction` with the layered judgment, uncertainty action,
  adaptive-size and signal-lifecycle fields;
- retain backward readers through an explicit migration adapter;
- require same-generation IDs across trigger, market state, Akber, shadow, risk
  and Router;
- hash evidence digests and policy versions into idempotency material;
- reject unknown schema versions rather than guessing.

Acceptance:

- one transaction can reconstruct why a setup was sized, delayed, watched,
  vetoed or submitted;
- no downstream stage reads ad hoc fragments when the canonical field exists;
- a partial write cannot advance Router state.

### LMJ-2: Layered Market-State Builder

Build:

- create the six internal judgment layers described in Section 6;
- preserve point-in-time `observed_at`, `published_at`, `available_at` and
  `expires_at` timestamps;
- derive numeric regime, breadth, participation, relative-strength and
  volatility features where provider data exists;
- label inferences separately from provider facts;
- create plain-English explanations without replacing numeric evidence.

Acceptance:

- every selected path cites provider-backed measurements and an economic
  mechanism;
- low volume is not interpreted as a directional signal by itself;
- implied volatility is not interpreted as direction;
- no stale or unavailable provider can silently contribute a passing value.

### LMJ-3: Provider Capability And Feature Completion

Build:

- audit current capabilities for earnings transcripts, market volume, breadth,
  constituent contribution, relative strength, realised volatility, implied
  volatility, skew and options flow;
- use existing providers before proposing new subscriptions;
- classify Unusual Whales, Alpaca options, market-price and transcript adapters
  by live, historical and entitlement state;
- add bounded refresh, rate-limit and stale-data behavior;
- create approved substitutes only where the evidence profile permits them;
- keep TradingView supplemental.

Acceptance:

- every feature says whether it is live, historical-only, stale, unavailable or
  supplemental;
- a missing optional provider creates a haircut, not a false hard failure;
- a strategy that explicitly depends on an unavailable feature remains held;
- no fixture or local sample is represented as a live provider call.

### LMJ-4: Trader Prior Registry

Build:

- encode Akber's current observations as the first versioned trader-prior
  record;
- add an intake schema for future qualitative trader observations;
- require mechanism, scope, falsifiers, expiry and supporting evidence;
- run local and frontier model extraction as proposal-only structured parsing;
- preserve the original text and review history.

Acceptance:

- a trader prior can change research priority, branch definitions or a soft
  multiplier only through a versioned approved policy;
- it cannot satisfy source quorum, expected return, execution quality or risk;
- it cannot directly create a candidate or order.

### LMJ-5: Direction And Path Resolver

Build:

- produce explicit long, short and wait branches for each eligible hypothesis;
- distinguish structural, regime and tactical horizons;
- add path-dependent activation and invalidation;
- support relative-strength and breadth divergence;
- emit one selected path or an explicit no-path result;
- preserve alternative branches for shadow comparison.

Acceptance:

- no research score directly chooses direction;
- contradictory long-term and short-term evidence is represented rather than
  flattened;
- every selected direction has a current trigger, invalidation and expiry;
- two opposing live orders cannot be created from one unresolved signal.

### LMJ-6: Missingness Classifier And Action Resolver

Build:

- implement the taxonomy in Section 8;
- make strategy profiles declare hard, soft, refreshable and diagnostic fields;
- add explicit treatment for closed market, rate limit, stale quote, absent IV,
  missing transcript, mixed breadth and provider outage;
- emit exactly one primary action and optional subordinate diagnostics;
- create repair records only for actual contract or provider defects.

Acceptance:

- every missing field resolves to exactly one action;
- soft evidence never becomes a veto;
- hard safety evidence never becomes a haircut;
- refreshable evidence enters a retry queue instead of disappearing;
- unknown classifications fail closed.

### LMJ-7: Akber V4 Layered Evaluation

Build:

- keep the six public stages and enrich their internal evidence;
- consume the canonical alias registry and layered state;
- move optional confirmations out of `missing_critical_context`;
- include the full soft multiplier and each component in the result;
- distinguish `pass_full`, `pass_reduced_size`, `watchlist_inactive`,
  `delay_for_execution_refresh`, `hold_hard_context` and `veto_adverse` as
  internal outcomes while retaining compatible public states;
- produce one plain-English explanation of the consequence.

Acceptance:

- a missing optional field changes size, not Router eligibility;
- a market-closed spread schedules a refresh;
- an explicit excessive spread vetoes;
- the result cannot create risk or execution approval;
- older Akber readers receive a deterministic compatibility projection.

### LMJ-8: Adaptive Risk And Sizing

Build:

- carry `soft_evidence_size_multiplier` into the risk setup;
- apply it exactly once and expose it in the proposal;
- separate all multipliers and identify the binding cap;
- implement the expected-return classes from Section 10;
- retain portfolio, correlation, liquidity, tail, drawdown and absolute trade
  ceilings;
- reject a quantity that becomes zero after safe rounding with a precise reason;
- allow valid sub-target discovery sizes where the broker permits them.

Acceptance:

- reducing evidence cannot increase position size;
- complete evidence never receives a missingness haircut;
- every quantity can be reproduced from the transaction;
- no proposal exceeds US$5,000;
- validated and experimental estimates cannot be confused;
- negative after-cost economics remains a veto.

### LMJ-9: Persistent Delayed-Entry Queue

Build:

- persist refreshable setups by economic signal identity;
- schedule quote, spread, session and provider retries;
- use bounded exponential backoff for provider faults;
- retry at the next valid market window when the market is closed;
- expire setups when the catalyst, thesis or evidence window expires;
- cancel queued setups when new adverse evidence appears;
- prevent queue records from creating broker authority.

Acceptance:

- restart, sleep and network loss preserve the queue safely;
- the same queued setup cannot create duplicate writes;
- a recovered quote rejoins the same transaction generation or creates a
  traceable successor generation;
- expired ideas never submit later merely because the provider recovered.

### LMJ-10: Decision-Time Shadow And Challenger Policy

Build:

- create the decision-time shadow snapshot synchronously before Router review;
- preserve the current alternative branches;
- compare three frozen policies in research only: literal Akber, layered Akber
  and no-Akber baseline;
- record trade-now, reduced-size, delayed-entry, watch and veto counterfactuals;
- mature outcomes at the intended horizon.

Acceptance:

- Router never waits for a shadow snapshot that the same cycle failed to
  create;
- shadow success cannot create an order or proof credit;
- only the canonical approved policy can reach PaperOps;
- challenger results remain attribution evidence.

### LMJ-11: Router And PaperOps Atomic Alignment

Build:

- add one final state for full-size, reduced-size and delayed-entry outcomes;
- carry the canonical decision generation, evidence multiplier and economic
  signal identity into handoff and idempotency material;
- preserve one guarded Alpaca Paper route;
- make retry behavior exactly once;
- reject direct or stale handoffs;
- ensure multiple distinct qualified setups can be submitted in one day.

Acceptance:

- every setup has exactly one final Router state;
- reduced size is not misreported as reduced confidence in the strategy itself;
- delayed entry is not counted as rejection;
- duplicate exposure and idempotency protections remain hard;
- no model, dashboard, Telegram or alternate sleeve can write to the broker.

### LMJ-12: Lifecycle, Exit And Anti-Churn Control

Build:

- carry economic signal identity from research through entry, exit and
  postmortem;
- add strategy-horizon-aware re-entry cooldowns;
- permit re-entry only after material evidence change, cooldown completion or a
  declared lifecycle transition;
- block immediate same-signal re-entry after a stop unless the evidence digest
  changed materially;
- retain hard stops and invalidations during any minimum holding window;
- support versioned target, partial-trim and stop-adjustment policies where the
  broker and quantity permit them;
- avoid applying Akber's informal 30 to 40 percent target universally.

Acceptance:

- repeated round trips from unchanged evidence raise `churn_warning` and cannot
  continue automatically;
- planned exits are separated from new decisions;
- every open position has an active lifecycle state and next action;
- no order remains ambiguous after submission;
- exit logic cannot increase exposure accidentally.

### LMJ-13: Learning, Attribution And Empirical Recalibration

Build:

- attribute outcome to structural thesis, regime, path, optional confirmations,
  size multiplier, execution quality, Akber state, Router and exit rule;
- compare full-size, reduced-size, delayed-entry and no-order counterfactuals;
- measure whether missing IV, weak breadth, low participation or delayed entry
  actually changed outcomes;
- run walk-forward, holdout, multiple-testing and cost sensitivity checks;
- generate threshold and multiplier proposals only;
- freeze each approved policy version for a real evaluation window.

Acceptance:

- Qadam cannot silently tune a losing strategy until it looks profitable;
- negative results remain durable memory;
- a policy change has preregistered acceptance and failure conditions;
- no learning record changes risk or authority directly;
- the next Observe cycle records which approved version it used.

### LMJ-14: Activity Health, Dashboard And Telegram

Build:

- create a canonical 24-hour activity-quality projection;
- classify health as:
  - `active_healthy`;
  - `healthy_idle_no_qualified_trigger`;
  - `conversion_degraded`;
  - `execution_degraded`;
  - `churn_warning`;
  - `risk_paused`;
- preserve the current dashboard structure and visual design;
- enrich Pattern Recognition with long, short and wait activation paths;
- enrich Trading Strategies with the evidence layers currently modifying each
  playbook;
- enrich Decision Room with the exact consequence of uncertainty: full size,
  reduced size, delayed entry, watch, hard hold or veto;
- enrich Order Monitor with entries, exits, distinct setups, round trips,
  re-entry warnings and eligible-opportunity conversion;
- enrich Results & Lessons with layered versus literal Akber attribution;
- make Telegram report only material changes and concise trade lifecycle events.

Acceptance:

- raw order count is never labelled as independent trades;
- a zero-order day with no eligible trigger can be healthy idle;
- a zero-order day with an eligible setup lost to an internal defect is
  degraded;
- repeated unchanged-signal round trips cannot make health look green;
- dashboard and Telegram remain read-only and public-safe;
- no existing dashboard route or sidebar structure changes.

### LMJ-15: Certification And Real-Market Rollout

Build:

- create `scripts/check_qadam_layered_market_judgment.py`;
- write `data/runtime/qadam_layered_market_judgment_certification.json`;
- run deterministic replays and negative probes;
- canary the new policy on one strategy family, then expand by profile;
- complete five distinct real US market sessions on the exact committed build;
- compare activity quality and conversion with the pre-change baseline;
- verify local, production and served-bundle dashboard parity before deployment
  is declared complete.

Acceptance:

- all certification groups pass with zero blockers;
- no open repair request or circuit remains;
- every eligible setup is submitted, deliberately delayed, or stopped for one
  explicit hard reason;
- internal evidence-format defects cause zero missed eligible setups;
- duplicate broker writes are zero;
- same-signal re-entry without material change is zero;
- eligible-opportunity capture is at least 90 percent across the five-session
  canary, excluding legitimate hard stops and expired setups;
- median eligible-setup-to-decision latency is no more than one scheduled
  market-hours cycle;
- live capital remains disabled;
- the canonical PaperOps wrapper remains the only broker-write path.

## 12. Phase Dependencies

| Phase | Depends on | May begin when |
| --- | --- | --- |
| LMJ-0 | Current canonical build | Immediately |
| LMJ-1 | LMJ-0 | Ownership and aliases are frozen |
| LMJ-2 | LMJ-1 | Transaction schema is available |
| LMJ-3 | LMJ-0 | Provider capability baseline exists |
| LMJ-4 | LMJ-1 | Trader-prior schema is validated |
| LMJ-5 | LMJ-2 and LMJ-4 | Layered evidence and prior are available |
| LMJ-6 | LMJ-1 to LMJ-3 | Every field has a policy owner |
| LMJ-7 | LMJ-5 and LMJ-6 | Paths and actions are deterministic |
| LMJ-8 | LMJ-7 | Akber emits a canonical multiplier |
| LMJ-9 | LMJ-6 | Refreshable states are typed |
| LMJ-10 | LMJ-5 to LMJ-8 | Canonical policy can be replayed |
| LMJ-11 | LMJ-8 to LMJ-10 | Risk, queue and shadow contracts pass |
| LMJ-12 | LMJ-11 | End-to-end signal lineage is intact |
| LMJ-13 | LMJ-10 to LMJ-12 | Outcomes can be attributed |
| LMJ-14 | LMJ-1 to LMJ-13 | Canonical projections are stable |
| LMJ-15 | All prior phases | Full negative and real-market testing can begin |

Later phases must not be implemented early by creating temporary parallel
artifacts that become accidental authorities.

## 13. Test Strategy

### 13.1 Contract Tests

- every strategy alias resolves identically;
- every field has one owner;
- every evidence record has point-in-time timestamps and provenance;
- every missing field receives one action;
- soft and hard fields cannot swap severity silently;
- the Akber multiplier reaches risk and appears exactly once.

### 13.2 Decision Journey Tests

Required journeys:

1. Full evidence produces a normal bounded proposal.
2. Missing optional IV produces a smaller equity proposal.
3. Missing IV for an IV-dependent strategy produces a hard hold.
4. Closed-market spread produces delayed entry and a next-open retry.
5. Excessive live spread produces a veto.
6. Rate-limited quote provider retries without duplication.
7. Strong structural thesis plus mixed breadth produces a reduced-size or wait
   outcome according to the frozen profile.
8. Inactive trigger remains watchlist.
9. Negative expected return vetoes.
10. Same economic signal cannot re-enter after an unchanged stop-out.
11. Materially changed evidence can create a successor generation.
12. Two distinct qualified setups can submit in the same market day.

### 13.3 Safety Probes

- attempt a live endpoint;
- attempt direct broker access outside PaperOps;
- attempt a duplicate idempotency key;
- attempt duplicate correlated exposure;
- attempt submission after drawdown breach;
- attempt stale or fixture-backed evidence;
- attempt to derive return from research score;
- attempt to let a trader prior satisfy quorum;
- attempt to let shadow success grant proof;
- attempt a re-entry without evidence change;
- attempt to exceed US$5,000 after multiplier composition;
- interrupt the queue between decision and broker write.

Every probe must fail closed without corrupting the transaction.

### 13.4 Empirical Tests

- replay the existing source-price history under literal and layered Akber;
- compare trade count, distinct setup count, net expectancy, drawdown and churn;
- run cost multipliers at 1x, 1.5x and 2x;
- compare immediate versus delayed entry;
- ablate breadth, volume, IV, relative strength and trader prior separately;
- test different market regimes and holding horizons;
- preserve untouched holdouts;
- measure whether additional trades add independent return or merely correlated
  exposure.

## 14. Operating Metrics

The primary metric is not orders per day. It is eligible opportunity conversion
with bounded risk.

### 14.1 Conversion Metrics

- eligible setups per market day;
- full-size versus reduced-size proposals;
- delayed-entry setups recovered;
- eligible setups submitted;
- legitimate hard stops;
- internal-defect misses;
- median conversion latency;
- percentage of missed fields resolved by size or delay rather than hard hold.

The desired activity discipline is at least one distinct paper entry on a
market day when one or more setups were already classified as fully eligible.
If that day ends with zero submissions, Qadam must report
`conversion_degraded` unless a later hard limit, expiry or duplicate-exposure
condition is recorded. Eligibility must be frozen before the outcome and cannot
be redefined afterward to make the metric pass.

### 14.2 Activity Metrics

- entry orders;
- exit orders;
- distinct economic hypotheses;
- completed round trips;
- re-entries after material evidence change;
- churn warnings;
- open positions and gross exposure.

### 14.3 Economic Metrics

- realised and unrealised paper P&L;
- after-cost expectancy at entry;
- slippage and spread;
- drawdown;
- hit rate and payoff ratio;
- performance by evidence profile;
- performance by size multiplier;
- immediate versus delayed-entry outcome;
- literal versus layered Akber counterfactual.

### 14.4 Reliability Metrics

- source freshness;
- provider retry success;
- stale artifact count;
- decision-generation consistency;
- queue recovery after restart;
- duplicate writes;
- ambiguous lifecycle records;
- open circuits and repair requests.

## 15. Rollout And Rollback

### 15.1 Rollout Sequence

1. Capture and sign the old-policy baseline.
2. Implement contracts and projections without changing decisions.
3. Run layered judgment in shadow beside the current policy.
4. Verify that differences are explainable and reproducible.
5. Enable soft multiplier propagation for one canary strategy family.
6. Enable delayed-entry recovery for that family.
7. Enable anti-churn and lifecycle controls.
8. Complete one real market session with no broker writes if certification is
   incomplete.
9. Enable bounded paper submissions for the canary.
10. Expand one evidence profile at a time.
11. Complete five real market sessions on the same build.
12. Certify and deploy the dashboard projections.

### 15.2 Automatic Rollback Triggers

Return to the last certified policy if any of the following occurs:

- duplicate broker write;
- order without complete lineage;
- size above the frozen ceiling;
- live-capital route observed;
- soft multiplier applied more than once;
- stale evidence reaches PaperOps;
- same-signal churn exceeds the frozen threshold;
- lifecycle ambiguity persists beyond one poll cycle;
- activity rises while after-cost results or drawdown violate the canary limits;
- source or decision-generation mismatch.

Rollback must preserve the audit record and must not delete the failed
transactions.

## 16. Dashboard Presentation

The existing dashboard structure must remain unchanged. Enrichment should make
the new behavior legible inside the current pages.

### Pattern Recognition

Show:

- research score as ranking only;
- structural thesis;
- current regime;
- long activation;
- short activation;
- wait condition;
- evidence that would move the idea forward.

### Trading Strategies

Show:

- which evidence layers currently refine each strategy;
- which instruments are core and secondary;
- how the current regime changes entry or sizing;
- whether a trader prior is active;
- the frozen strategy version.

### Decision Room

Show one consequence per setup:

- full-size paper review;
- reduced-size paper review;
- delayed until market-hours refresh;
- watchlist because the trigger is inactive;
- hard hold because risk cannot be bounded;
- veto because evidence is adverse.

The user should see the exact missing item and why it changed size, timing or
eligibility.

### Order Monitor

Add an activity-quality summary:

- entries;
- exits;
- distinct setups;
- completed round trips;
- repeat-signal re-entries;
- churn warning;
- conversion health;
- next lifecycle action.

The existing broker mirror remains authoritative for orders and positions.

### Results And Lessons

Show whether full size, reduced size, delayed entry, watch or veto improved the
actual outcome. Keep policy changes as proposals until accepted through the
existing governance contract.

## 17. Telegram Behavior

Telegram should communicate decisions, not system theatre.

Examples:

```text
Qadam opened a reduced-size XLE paper position. The energy thesis and current
trigger passed, but weak market participation reduced the proposed size by 40%.
Entry, invalidation and expected holding window are recorded in the dashboard.
```

```text
Qadam delayed an SMH setup until the US market opened. The thesis remains under
review, but a current spread was required before sizing. The setup will expire
if the trigger is no longer valid at the next quote.
```

```text
No new paper entry today. Two ideas stayed on the watchlist because their
triggers were inactive; no eligible setup was lost to a system or provider
failure.
```

Messages must be deduplicated, public-safe and sent only for material evidence,
decision, order, exit or health changes.

## 18. Completion Criteria

The implementation is complete only when all of the following are true:

1. The strategy alias mismatch is eliminated.
2. One canonical transaction owns the full decision path.
3. Akber's soft multiplier reaches final risk sizing exactly once.
4. Every missing field has one typed consequence.
5. Optional missing evidence can reduce size without becoming a veto.
6. Refreshable execution evidence persists and retries safely.
7. Hard safety and adverse evidence still stop the setup.
8. Long, short and wait paths are explicit.
9. Implied volatility is never treated as directional by itself.
10. A research score is never treated as probability or expected return.
11. Discovery-micro expected return is conservative, labelled and reproducible.
12. Every paper quantity is reproducible from the transaction.
13. Every paper order uses guarded Alpaca Paper through PaperOps.
14. Duplicate writes and duplicate exposure conflicts remain impossible.
15. Same-signal churn is detected and blocked.
16. Every open paper position has an unambiguous next lifecycle action.
17. Activity health separates entries, exits, distinct setups and round trips.
18. Eligible setup capture reaches the canary target without a trade quota.
19. Internal contract failures cause zero missed eligible setups during the
    five-session certification window.
20. Dashboard and Telegram remain read-only and preserve the existing UX.
21. Live capital remains disabled.
22. All unit, integration, replay, failure-injection, safety and production
    checks pass.
23. The exact committed build completes five real market sessions without an
    open circuit, repair request, stale decision or lifecycle ambiguity.

## 19. Expected Outcome

After implementation, Qadam should no longer confuse incomplete certainty with
unacceptable risk.

An otherwise viable setup will be able to progress as a smaller paper
experiment when optional confirmation is missing, wait for a current quote when
execution evidence is temporarily unavailable, or remain on a two-sided
watchlist when direction has not activated. It will still stop when expected
economics are negative, risk cannot be bounded, liquidity is genuinely adverse,
the portfolio is already exposed, or the paper-only safety boundary fails.

This should increase the frequency with which legitimate low-risk hypotheses
reach paper execution. It cannot guarantee a trade every day or profitable
returns. Its success is demonstrated when Qadam captures a higher share of the
setups its own evidence genuinely qualifies, does so at sizes proportionate to
uncertainty, avoids churn, and learns whether those additional experiments add
economic value.

## 20. Implementation Record

Implemented on 20 August 2026.

The software phases LMJ-0 through LMJ-15 are installed and implementation
certification passes. The release includes canonical aliases, Decision
Transaction V2 migration, layered market judgments, truthful provider-feature
capabilities, proposal-only trader priors, long/short/wait paths, typed
missingness actions, Akber V4 consequences, adaptive sizing, delayed-entry
recovery, synchronous shadow evidence, signal-aware Router idempotency,
anti-churn lifecycle controls, challenger attribution, activity-quality health,
dashboard projections and concise Telegram projections.

Verification at implementation time:

- `868` repository tests passed;
- changed-code Ruff and Python compilation passed;
- the layered judgment, Akber, portfolio-risk, Router, artifact-ownership,
  dashboard and operator-service checks passed;
- open operator circuits: `0`;
- open operator repair requests: `0`;
- paper-only boundary preserved and live capital disabled;
- approved dashboard UX frozen at dashboard commit
  `2966eb72eb862b247306d176028ea03741ac8d45`.

The implementation is ready, but observation certification remains pending
until the exact committed core build records five distinct real US market
sessions. Those sessions cannot be simulated, backfilled or inferred from an
older build. Until that canary reaches `5/5`, Qadam must report
`observation_ready=false` even when the service is healthy.
