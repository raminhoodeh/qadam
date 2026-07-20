# Qadam Backtest Completion Implementation Plan

**Plan ID:** `qadam-backtest-completion-v4-final-autonomous-governance`

**Prepared:** 20 July 2026

**Status:** Final implementation plan - ready for modular implementation

**Revision focus:** Convert Qadam from a broad research factory into a focused
information-advantage programme, apply the recommended pattern methods to every
eligible core strategy, translate evidence into versioned strategy decisions,
automatically admit qualifying paper strategies, adapt their risk through a
pre-authorized tier ladder, and define the only safe path from a completed
backtest to guarded paper execution.

**Scope:** Complete the empirical use of Qadam's existing historical lake,
acquire the most decision-relevant missing histories, begin honest forward
capture where history cannot be recovered, rerun the frozen research protocol,
translate results into core-strategy refinements or emerging-strategy
proposals, and conditionally graduate only forward-confirmed survivors into the
existing guarded Alpaca Paper route.

**Predecessor:**
`docs/qadam-past-learning-and-backtest-gap-closure-implementation-plan.md`

**Canonical architecture owner:**
`docs/qadam-operator-ready-edge-engine-implementation-plan.md`

## 1. Executive Decision

Qadam's historical acquisition and backtest machinery are implemented, but the
current result is not an empirical test of every one of the 41 data sources.
It is a certified test of every lane that was eligible under the evidence
available at the time.

The verified baseline is:

| Measure | Current state |
| --- | ---: |
| Canonical data sources | 41 |
| Canonical watched instruments | 19 |
| Provider-backed historical rows | 746,275 |
| Sources with acquired history | 10 |
| Sources actually used as scored signals | 5 |
| Sources classified forward-only | 15 |
| Sources classified unavailable or excluded | 16 |
| Instruments with daily price history | 17 |
| Direct prediction instruments excluded | 2 |
| Focus-provider input rows | 72,875 |
| Focus-provider hypotheses | 2,652 |
| Focus-provider untouched-holdout results | 2,532 |
| Focus-provider negative controls | 211 |
| Historical edge candidates | 0 |
| Validated edges | 0 |

The 2,652 historical hypotheses and zero surviving candidates are a substantive
negative result. They show that the current combination of scored signals,
features, horizons, strategy mappings, and costs has not demonstrated reliable
predictive value. Repeating the same experiment family more frequently would
compound activity records, not evidence or returns.

Qadam's main blind spot is therefore not missing orchestration. It is the lack
of a demonstrated information advantage. The implementation must distinguish a
system that can manufacture research objects from a system that can identify a
small, economically defensible relationship before it is absorbed by price.

The `41 sources` figure describes registry breadth, not 41 independent
historical signals. Only five sources entered the current canonical score-label
plane. Other sources are price/context planes, forward-only, unavailable,
duplicative, correlated, or still unparsed. Every public and internal summary
must show those denominators separately.

This plan converts that honest but incomplete empirical state into the fullest
defensible backtest Qadam can run. It prioritizes three different forms of
work:

1. **Use history Qadam already owns.** BIS, BLS, ECB, and UCDP contain real
   provider-backed records but are not yet represented as scored features.
2. **Acquire or parse high-value missing evidence.** The priority gaps are
   STOCK Act transaction details, Unusual Whales history, complete Kalshi and
   Polymarket contract histories, and selected geopolitical/public archives.
3. **Start the clock where history cannot be recovered.** Forward-only sources
   must accumulate real observations and outcomes. They cannot be backfilled
   with fixtures, synthetic time, or retrospective prose.

The target is not to force Qadam to find an edge. The target is to remove
avoidable evidence gaps so that an edge, if present, has a fair opportunity to
survive the statistical protocol. Every completed result must then have a
strategy consequence: preserve an incumbent, propose a refinement, demote or
reject a rule, create a provisional emerging strategy, or record that no
strategy should change.

## 2. Relationship To Existing Qadam

This is a completion overlay, not a new engine and not a replacement for
QSASE, the operator-ready edge engine, or the PLBG implementation.

| Responsibility | Existing canonical owner | This plan's role |
| --- | --- | --- |
| Provider acquisition | OR-2R / OR-3 | Add missing approved provider lanes and parsers |
| Point-in-time evidence | OR-4 | Expand source coverage and identity resolution |
| Feature engineering | OR-5 | Add source-specific versioned features |
| Historical score tape | OR-6 | Rebuild from a frozen expanded feature registry |
| Forward labels and costs | OR-7 | Add direct-contract and selective intraday labels |
| Statistical testing | OR-8 | Run the expanded pre-registered experiment family |
| Nonlinear/quantum review | OR-9 | Test incremental value against matched classical baselines |
| Edge registry | OR-10 | Admit only surviving historical candidates |
| Strategy translation | Strategy Foundry V3 | Compare incumbents with evidence-backed refinements and create provisional emerging strategies |
| Forward validation | OR-13 | Accumulate real outcomes after historical testing |
| Strategy admission | Autonomous Strategy Governor | Admit a qualifying paper strategy under an immutable signed policy without a per-strategy click |
| Practical tradeability | Akber V3 | Evaluate a current setup after strategy and forward evidence exist |
| Portfolio governance | Adaptive Paper Risk Governor and Router | Select compatible paper candidates and move them through pre-authorized risk tiers |
| Paper execution | Canonical PaperOps | Run conditional paper canaries through the guarded Alpaca Paper route only |
| Dashboard visibility | OR-17 | Explain coverage, gaps, results, and next actions |
| Self-healing | OR-18 | Resume safe jobs and classify provider failures |
| Certification | OR-19 | Consume the new completion certification without weakening gates |

The existing public dashboard structure must remain unchanged. This plan may
enrich Data Sources, Trading Universe, Pattern Recognition, Quantum Edge,
Trading Strategies, Decision Room, and Learn & Improve, but it must not reorder
or replace the protected navigation and page structure.

## 3. What Backtest Completion Means

Backtest completion has four separate dimensions. They must never be collapsed
into one optimistic percentage.

### 3.1 Coverage Completion

Every source and instrument has exactly one current state:

- `provider_backed_acquired`
- `approved_proxy_with_basis_risk`
- `price_plane_only`
- `context_only_not_predictive`
- `forward_only_capture_active`
- `terminally_unavailable`
- `excluded_duplicate`
- `excluded_not_material`

There may be no generic `missing`, `unknown`, or silently ignored state.

### 3.2 Scoreability Completion

Every acquired source has an explicit empirical role:

- scored signal;
- outcome or price plane;
- regime/context feature;
- execution-cost input;
- identity/provenance support; or
- deliberately excluded with a typed reason.

Acquired data must not remain accidentally unused.

### 3.3 Empirical Completion

Every eligible source, strategy, instrument mapping, horizon, ablation, and
negative control is either:

- tested under the frozen protocol;
- rejected as statistically insufficient;
- excluded before testing by a documented economic or data-quality rule; or
- waiting for real forward evidence.

### 3.4 Temporal Completion

Forward-only sources cannot become historically mature through code. They earn
temporal completion only after enough real observations and forward outcomes
exist. The certification must therefore distinguish:

| Certification state | Meaning |
| --- | --- |
| `available_history_complete` | Every obtainable and approved historical lane has been acquired and tested |
| `forward_evidence_maturing` | Available history is complete but one or more forward-only lanes lack real elapsed evidence |
| `full_empirical_completion` | Historical and required forward-only lanes meet their frozen observation thresholds |
| `complete_no_edge_found` | The complete eligible programme found no surviving edge |
| `historical_candidate_found_forward_validation_required` | A candidate survived history but has not earned forward promotion |
| `strategy_proposal_forward_validation_required` | Evidence produced a core refinement or emerging strategy proposal that remains inactive |
| `forward_validated_paper_canary_eligible` | A frozen strategy survived forward evidence but still requires a current setup and every execution gate |
| `guarded_paper_canary_operating` | A current setup passed all gates and is being observed through the canonical paper route |

`available_history_complete` is a valid engineering success. It is not proof
that every source has history and is not a profitability claim.

## 4. Constitutional Boundaries

Every phase must preserve these constraints:

- Historical data cannot advance the real 30-day paper growth trial.
- No backtest, replay, shadow result, or old paper trade receives paper proof
  ledger credit.
- Historical work cannot directly create a qualified setup, risk approval,
  execution approval, paper order, broker write, or live-capital authority.
- A later real-time paper canary is permitted only after historical survival,
  frozen forward confirmation, Akber review, portfolio-risk approval, Router
  eligibility, and the canonical PaperOps checks independently pass.
- Real paper canaries use real market time and may advance the real paper trial
  only through actual broker-mirrored fills and closes with complete lineage.
- No phase may enable live capital or call a broker live endpoint.
- Provider APIs are read-only research inputs.
- No source can satisfy source quorum by itself.
- Prediction-market research cannot route orders to Kalshi or Polymarket.
- Unusual Whales is supplemental and cannot replace the core evidence baseline.
- Model prose and quantum review cannot alter historical observations, labels,
  or availability timestamps.
- Outcome, resolution, revised macro data, and transaction dates cannot leak
  into a score produced before those values were publicly available.
- Missing history cannot be fabricated, synthesized, or inferred from current
  snapshots.
- Provider purchases, terms acceptance, and license changes require explicit
  operator review.
- Credentials remain in the strict local secret store and never enter Git,
  logs, runtime JSON, dashboard payloads, Telegram, or command arguments.
- Raw and normalized research datasets remain under ignored `data/research/`
  paths.
- Strategy, feature-weight, model-routing, Akber-threshold, and risk changes
  remain immutable versioned proposals until the signed autonomous governance
  policy or an operator decision admits them.
- Core-strategy refinements and new strategy families remain inactive proposals
  until their historical, forward, novelty, admission, and risk gates pass.
- The Autonomous Strategy Governor may admit them for paper use without a human
  click only when every machine-verifiable gate in its immutable policy passes.
- The Adaptive Paper Risk Governor may increase or decrease strategy allocation
  only through pre-authorized tiers and can never exceed the absolute strategy,
  portfolio, or operator parent ceilings.
- Local or frontier LLM prose and quantum conclusions are evidence inputs only;
  they cannot sign an admission or risk-expansion decision.
- No trade, candidate, or strategy quota may force a promotion or order.
- Zero surviving edges is an acceptable final result.

## 5. Canonical Target Flow

```text
Frozen source and instrument universe
  -> empirical-role registry
  -> information-advantage admission gate
  -> provider and licensing gate
  -> resumable raw acquisition or document parsing
  -> immutable normalized evidence
  -> identity and point-in-time availability audit
  -> economic source-to-market mapping
  -> frozen feature registry
  -> score tape written before outcomes
  -> separate forward labels and cost model
  -> pre-registered walk-forward backtest
  -> ablations, negative controls, and false-discovery correction
  -> matched nonlinear and quantum/classical review
  -> historical candidate or honest rejection
  -> strategy impact decision
  -> incumbent refinement proposal or emerging strategy proposal
  -> frozen real forward strategy tournament
  -> autonomous paper-strategy admission
  -> current setup and Akber evaluation
  -> adaptive paper risk and Router review
  -> guarded PaperOps canary or continued cash
  -> real paper outcome and attribution
  -> proposal-only learning or value-of-information research queue
```

### 5.1 Research Factory Versus Edge Engine

Qadam must preserve its broad evidence library while deliberately narrowing
the hypotheses that consume statistical, provider, model, and human-review
budget. Source count, model count, quantum runs, hypothesis count, and
automation uptime are operational measures. None is an edge measure.

The completed system must maintain two separate lanes:

| Lane | Purpose | Default resource posture | Promotion power |
| --- | --- | --- | --- |
| Focused edge programmes | Test a small number of economically specified relationships | At least 80% of new backtest and forward-observation capacity | May produce historical candidates after every gate passes |
| Whole-universe challengers | Search for genuinely different questions and monitor regime changes | At most 20% of capacity until reviewed | Research-only until separately pre-registered |

The allocation is an initial governance default, not an optimization target.
Changing it requires a reviewed proposal. The whole-universe lane may not
silently create thousands of variants that dilute the multiple-testing family.

### 5.2 Information-Advantage Admission Contract

Before Qadam spends a holdout, quantum run, paid provider call, or forward
observation slot on a hypothesis, it must answer six questions:

| Test | Required answer |
| --- | --- |
| Unique information | What raw fact, timing advantage, cross-source alignment, or rarely compared combination could remain absent from the current price? |
| Correct timing | What is the conservative `available_at`, and could Qadam have observed and acted on it before the measured return began? |
| Economic mechanism | Why should source or event X affect instrument Y within horizon Z rather than merely correlate with it? |
| Sufficient observations | How many independent event clusters exist, what minimum effect is detectable, and what sample is required by the frozen power analysis? |
| Execution fit | Is the expected effect large enough to survive spread, fees, slippage, delay, liquidity, roll cost, and proxy basis risk? |
| Forward confirmation | Can the unchanged rule be observed for 60-90 real market days and enough independent events after freezing? |

Each assessment receives one information state:

- `potential_raw_information_advantage`
- `potential_timing_advantage`
- `potential_cross_source_synthesis_advantage`
- `public_context_likely_absorbed`
- `duplicate_or_correlated_evidence`
- `mechanism_unsupported`
- `insufficient_independent_observations`
- `execution_effect_too_small`
- `forward_evidence_required`

Passing this admission contract means only that a question deserves testing.
It is not evidence of an edge and cannot contribute to source quorum, Akber,
Router, or PaperOps.

### 5.3 Frozen Hypothesis Contract

Every admitted hypothesis must be written before its evaluation window and
contain:

| Field | Requirement |
| --- | --- |
| Hypothesis identity | Stable ID and immutable version |
| Information claim | Exact reason the signal may not yet be reflected in price |
| Economic mechanism | Causal pathway expressed as a falsifiable research claim |
| Source event | Canonical source records and conservative availability rule |
| Market mapping | Fixed instrument, approved proxy, and basis-risk statement |
| Direction | Signed expectation or an explicitly two-sided rule |
| Horizons | Predefined evaluation and execution horizons |
| Event independence | Clustering rule preventing duplicate news, filings, or contracts from inflating sample size |
| Baselines | Unconditional, simple strategy, time-shifted, shuffled, and source-removed comparisons |
| Costs | Fees, spread, slippage, delay, liquidity, roll, and proxy assumptions |
| Minimum evidence | Power-based event and time requirements |
| Success criteria | Net-of-cost holdout and stability thresholds fixed before results |
| Failure condition | Exact kill, pause, or insufficiency rule |
| Forward protocol | Freeze date, 60-day minimum review, 90-day planned review, and independent-event minimum |
| Attempt lineage | Every threshold, feature, and model version previously tried |

Time passing alone is not forward confirmation. A programme with too few
independent events remains `forward_evidence_maturing` after 90 market days.
Qadam may not loosen a rule after seeing its outcome and keep the same
hypothesis identity.

### 5.4 Three Flagship Research Programmes

The first completion cycle must prioritize three programmes. Other questions
remain challengers until these programmes are terminal or a reviewed repriority
proposal is approved.

#### Programme A - Prediction-Market Disagreement And Market Repricing

| Contract element | Initial specification |
| --- | --- |
| Research question | Does a fresh, liquidity-qualified disagreement between Kalshi, Polymarket, and conventional event evidence precede repricing in the economically affected ETF or futures proxy? |
| Potential advantage | Prediction venues may aggregate dispersed beliefs at a different speed than the related listed market; cross-venue disagreement may reveal uncertainty rather than consensus information already priced in |
| Required inputs | Kalshi and Polymarket contract prices, tradable lifecycle, liquidity, spread, settlement identity, event clustering, and corroborating event evidence |
| Market mapping | Pre-registered event-to-sleeve mapping across energy, defence, semiconductors, silver/macro, or an approved benchmark; no post-outcome instrument switching |
| Initial horizons | Daily baseline at 1, 3, and 5 market days; intraday horizons only after timestamp and quote coverage pass admission |
| Core comparisons | Kalshi only, Polymarket only, agreement, disagreement, conventional evidence only, combined evidence, time-shifted, and shuffled controls |
| Execution test | Net effect after listed-market costs and, for direct contracts, contract liquidity, spread, fees, and fill assumptions |
| Failure condition | No incremental untouched-holdout value, dependence on illiquid contracts, outcome leakage, unstable event mapping, or net effect erased by costs |

The programme must separate prediction markets as information sources from
prediction markets as direct research instruments. Neither venue receives
execution authority.

#### Programme B - STOCK Act Disclosure And Sector-Basket Repricing

| Contract element | Initial specification |
| --- | --- |
| Research question | Do newly public STOCK Act transaction disclosures contain delayed information about defence or semiconductor baskets after controlling for market and sector movement? |
| Potential advantage | Structured disclosure details, filer clusters, amount ranges, and sector mappings may be compared more systematically and promptly than narrative coverage |
| Required inputs | Official disclosure documents, filing availability, transaction type, amount range, amendment state, asset/issuer mapping, filer identity, and contemporaneous market data |
| Market mapping | Defence: `ITA`, `PPA`, `XAR`, `LMT`; semiconductors: `SMH`, `SOXX`, `NVDA`; `SPY` and `QQQ` as controls where appropriate |
| Initial horizons | 1, 5, 10, and 20 trading days from public filing availability, not private transaction date |
| Core comparisons | Filing index only, parsed transaction detail, buy/sell, amount band, filer cluster, sector cluster, market-neutral residual, transaction-date leakage control, and same-date placebo |
| Execution test | Basket or liquid proxy return after costs, delay, concentration, disclosure lag, and capacity assumptions |
| Failure condition | Effect disappears after sector/market controls, relies on transaction-date hindsight, concentrates in one filer or issuer, fails untouched holdout, or is too small after costs |

The parser must preserve disclosed ranges and uncertainty. It must never infer
an exact transaction value or treat the private transaction date as Qadam's
information date.

#### Programme C - Unusual Whales As Macro Confirmation

| Contract element | Initial specification |
| --- | --- |
| Research question | Does options-flow, dark-pool, market-tide, or positioning evidence strengthen or correctly reject an independently formed Qadam macro signal? |
| Potential advantage | Derivatives and off-exchange activity may reveal positioning that confirms whether a public macro narrative is becoming tradeable |
| Required inputs | Official historical export or real forward records, instrument identity, event and availability timestamps, premium, volume, open interest, put/call state, dark-pool context, and approved derived fields |
| Market mapping | Only instruments already named by the underlying macro hypothesis; Unusual Whales cannot choose a new instrument retrospectively |
| Initial horizons | Event/session-close, 1-day, and 3-day where timestamp coverage supports them; daily-only otherwise |
| Core comparisons | Core Qadam signal, core plus Unusual Whales, Unusual Whales only, reject/confirm split, time-shifted control, and shuffled control |
| Execution test | Incremental net-of-cost improvement in timing, calibration, drawdown, or false-positive rejection |
| Failure condition | No incremental value over the core signal, value exists only standalone, timestamp ambiguity, unstable ticker mapping, or effect disappears after costs |

Unusual Whales is a confirmation and rejection layer in this programme. A flow
record cannot originate a qualified setup by itself.

### 5.5 Kill Fast, Preserve Every Attempt

Every hypothesis version must finish in exactly one state:

- `rejected_no_information_claim`
- `rejected_no_economic_mechanism`
- `rejected_insufficient_independent_events`
- `rejected_no_incremental_value`
- `rejected_after_costs`
- `rejected_holdout_failure`
- `rejected_regime_instability`
- `rejected_forward_failure`
- `paused_evidence_maturing`
- `historical_candidate_forward_validation_required`

Rejected versions remain in an immutable attempt ledger. Re-running a rejected
idea requires a materially new source, mechanism, feature contract, market,
or regime hypothesis and a new version. Cosmetic threshold tuning is not a new
hypothesis.

### 5.6 Quantum And Nonlinear Role

Quantum and nonlinear methods enter only after a hypothesis has sufficient
point-in-time information and independent observations. They may test whether
an interaction, regime, path, or similarity structure improves prediction, but
they cannot create information absent from the inputs.

Every quantum-assisted result must use the same evidence, labels, costs,
folds, holdout, and evaluation metrics as a matched classical comparator. It
must demonstrate incremental out-of-sample value after runtime and provider
costs. Otherwise its conclusion is `not_proven`, `negative`, or
`not_measurable`.

### 5.7 Recommended Methods Applied To Core Trading Strategies

Qadam must distinguish pattern-recognition methods from trading strategies.
Historical occurrence, lead-lag analysis, vector analog retrieval, state
matrices, entropy, nonlinear models, and quantum-assisted comparisons are ways
to test evidence. A trading strategy additionally defines an economic
mechanism, instrument, direction, entry, exit, invalidation, costs, risk, and
the conditions under which it must remain inactive.

The five configured strategy families are priors to test, not validated truths.
Each receives the applicable recommended method suite:

| Core strategy family | Economic question | Required backtest methods | Practical confirmation |
| --- | --- | --- | --- |
| Crude Oil Energy Security Disruption | Do conflict, shipping, chokepoint, fire, or supply events lead oil or energy repricing? | Event occurrence and lead-lag, vector analogs, conflict/supply state matrix, cross-asset confirmation, entropy/nonlinear interaction review | Oil/energy volume, volatility, spread, trend, Unusual Whales when mapped, and proxy basis risk |
| Defence Geopolitical Repricing | Do escalation, policy, procurement, filing, or conflict signals lead defence-basket repricing? | Event studies, actor/regime state matrix, historical analogs, filing/patent interactions, market-neutral factor controls | Basket liquidity, market/sector residual, volume or flow, concentration, and catalyst freshness |
| Prediction Market Geopolitical Dislocation | Does liquidity-qualified prediction-market disagreement lead affected listed-market or contract repricing? | Cross-venue divergence, event-time lead-lag, agreement/disagreement state matrix, analog retrieval, nonlinear interaction review | Contract lifecycle, liquidity, spread, settlement, listed-market confirmation, and event identity |
| Semiconductor Policy Asymmetry | Do export controls, industrial policy, patents, filings, or disclosure clusters lead asymmetric semiconductor repricing? | Policy/filing event studies, vector analogs, state matrix, cross-sectional factor controls, nonlinear interactions | Sector-relative price action, options/flow confirmation, liquidity, and invalidation around policy reversal |
| Silver Macro Liquidity Stress | Do inflation, rates, liquidity, funding stress, or commodity regimes lead silver opportunities? | Revision-safe macro lead-lag, macro state matrix, historical analogs, cross-asset confirmation, entropy/regime-transition review | Volatility, dollar/rates context, volume/flow, trend, spread, and futures-to-ETF basis risk |

Every strategy backtest must begin with transparent linear, event-study, and
simple-rule baselines. Vector, state, nonlinear, entropy, and quantum-assisted
methods are admitted only when their sample and data type support them. Missing
method eligibility is recorded explicitly rather than replaced with synthetic
evidence.

Results must be reported by:

- strategy family and immutable version;
- method and model version;
- source contribution and source-removal ablation;
- instrument, proxy, direction, horizon, and regime;
- independent event count and concentration;
- gross and net-of-cost outcome;
- walk-forward and untouched-holdout outcome;
- classical versus nonlinear or quantum increment; and
- practical confirmation contribution.

The strategy-agnostic lane remains mandatory. It ensures that the five core
families do not prevent Qadam from detecting a valid relationship outside its
existing playbooks.

### 5.8 Backtest-To-Strategy Translation Contract

Every terminal backtest result must produce exactly one strategy-impact state:

| Strategy-impact state | Meaning |
| --- | --- |
| `preserve_core_strategy` | Evidence does not justify changing the incumbent definition |
| `refine_core_strategy_proposal` | Evidence supports a versioned change to an existing family |
| `demote_core_strategy_proposal` | Evidence shows that an incumbent rule, source, instrument, or regime should receive less weight or remain inactive |
| `retire_rule_proposal` | A specific rule repeatedly fails and should be removed after review |
| `emerging_strategy_proposal` | A surviving relationship has a distinct mechanism that does not fit the core five |
| `reject_without_strategy_change` | The tested relationship failed and creates no strategy change |
| `insufficient_evidence_no_change` | The question remains unresolved and no strategy may change |

A core-strategy refinement may propose changes to:

- eligible source families and minimum evidence;
- instrument or proxy mappings and basis-risk limits;
- regime eligibility;
- entry timing and confirmation requirements;
- invalidation and exit logic;
- holding horizon;
- cost, liquidity, and stale-data blockers; or
- portfolio compatibility and exposure limits.

The backtest may write a proposed `vNext` strategy but cannot overwrite the
incumbent. The incumbent and challenger must be evaluated on identical folds,
holdouts, costs, and forward periods. The challenger replaces or supplements
the incumbent only after a signed Autonomous Strategy Governor decision or an
explicit operator decision and must preserve full version lineage.

A result may create an emerging strategy proposal only when:

- its mechanism is not adequately represented by an existing family;
- its source-to-market pathway, instruments, horizon, and failure mode are
  explicit;
- it is not a renamed threshold variant or duplicate exposure;
- it survives the same false-discovery, cost, concentration, and holdout gates;
- it has enough independent observations to be tested prospectively;
- Strategy Foundry records Research Goal lineage, candidate identity,
  invalidation, paperability, and risk concept; and
- it remains inactive until forward and governance gates pass.

Backtest results therefore influence strategies through auditable proposals,
not silent self-modification. Automatic admission is a separate deterministic
decision over those proposals.

### 5.9 The Most Intelligent Post-Backtest Decision

The intelligent use of a completed backtest is not to trade the row with the
highest historical return. That would maximize winner's curse and selection
bias. Qadam must convert the result set into a robustness frontier and choose
the next action that creates the most reliable new information per unit of
time, cost, and risk.

#### Post-backtest decision sequence

1. Freeze the result manifest, dataset hashes, attempt ledger, and untouched
   holdout. No result may be reinterpreted after seeing later outcomes.
2. Classify every result by strategy impact and terminal research state.
3. Build a robustness frontier using net expectancy, uncertainty, drawdown,
   turnover, liquidity, event independence, regime stability, source fragility,
   capacity, and correlation with other candidates.
4. Select a small, diversified forward tournament. Do not choose several
   variants of the same event, source, instrument, or economic mechanism.
5. Freeze each candidate and observe it for 60-90 real market days plus its
   required independent event count.
6. Compare the candidate with its incumbent, simple baseline, no-trade outcome,
   and alternate Akber hold/veto outcomes.
7. If forward evidence fails, archive or redesign the research question. If it
   remains insufficient, keep observing without changing rules.
8. If forward evidence survives, submit the strategy to the Autonomous Strategy
   Governor, then submit each current setup to Akber, adaptive portfolio risk,
   and Router in that order.
9. If every gate passes, begin a small guarded paper canary through canonical
   PaperOps at the lowest pre-authorized risk tier; historical strength alone
   cannot skip or enlarge a tier.
10. Scale only inside paper trading and only when real fills, closes, costs,
    drawdown, and attribution remain within frozen promotion limits.

The robustness frontier is Pareto-based. A candidate should not be selected
merely because one headline metric is highest. Preference goes to evidence that
is net positive, stable, independently repeated, executable, simple enough to
audit, and diversifying relative to other candidates.

If no strategy survives, Qadam must remain in cash and produce a
value-of-information queue. That queue ranks the next research question or data
purchase by:

- expected reduction in uncertainty;
- economic plausibility;
- number of new independent observations;
- ability to resolve a specific failed assumption;
- provider, compute, storage, and elapsed-time cost;
- execution relevance; and
- risk of creating another correlated or redundant signal.

This is how a failed backtest improves Qadam: it narrows what should be tested
next instead of generating more variants of the same weak idea.

### 5.10 Conditional Paper Canary And Sequential Promotion

No historical result can submit an order. A paper canary becomes eligible only
after all of these independent states exist:

```text
positive net-of-cost historical holdout
  -> frozen forward-shadow survival
  -> autonomous paper-strategy admission
  -> current evidence freshness and source quorum
  -> Akber pass for the current setup
  -> adaptive paper-risk approval
  -> Router paper-review-candidate state
  -> duplicate, drawdown, idempotency, and Q-CTRL checks
  -> guarded Alpaca Paper submission
```

The canary must use the lower of its current autonomous risk tier, the portfolio
risk budget, and the immutable operator parent ceiling. Backtest strength
cannot skip a tier or change the parent ceiling. Promotion states are:

- `shadow_only`
- `paper_canary`
- `paper_probation`
- `paper_active_within_limits`
- `paper_paused`
- `paper_retired`

Promotion depends on real broker-mirrored orders, fills, costs, closes,
drawdown, calibration, and strategy attribution. A stale source, broken
lineage, adverse drawdown, execution deterioration, regime break, or invalidated
mechanism pauses the strategy fail-closed. Live capital remains outside this
plan.

### 5.11 Autonomous Strategy Admission And Adaptive Risk Governor

The user should not need to click to approve each qualifying strategy or each
paper-risk increase. Qadam must instead execute a signed, deterministic
governance policy whose outer limits were approved in advance.

#### Autonomous strategy-admission requirements

A core challenger or emerging strategy may be admitted automatically for paper
use only when all of these are true:

- its immutable version has a distinct economic mechanism, instruments,
  direction, timing, invalidation, cost model, and failure policy;
- its historical result passes the registered holdout, cost, concentration,
  baseline, negative-control, and false-discovery gates;
- its unchanged forward result passes the 60-90 market-day and independent-
  event requirements;
- its net expectancy lower confidence bound and other frozen admission metrics
  meet the policy threshold;
- its exposure is not a disguised duplicate of an admitted strategy;
- its instruments and proxies are already in the approved paper universe and
  have a canonical Alpaca Paper route;
- its required sources, models, and runtime dependencies are fresh and healthy;
- it has complete Research Goal, strategy, candidate, risk, and invalidation
  lineage; and
- every admission condition is machine-verifiable without discretionary LLM
  prose.

The Python governance engine signs the decision with the strategy version,
policy version, evidence hashes, reason codes, timestamp, and expiry. Gemma,
Gemini, nonlinear models, and quantum review may challenge or downgrade the
evidence, but none may sign its own admission.

#### Pre-authorized paper-risk ladder

The initial parent policy uses the existing US$100,000 paper account and the
operator-specified US$5,000 absolute per-trade paper notional ceiling. The
implementation must reconcile that ceiling with canonical risk configuration
before enabling automatic promotion. If they disagree, Qadam fails closed.

| Risk tier | Maximum fraction of absolute per-trade ceiling | Initial maximum notional | Admission meaning |
| --- | ---: | ---: | --- |
| `R0_shadow` | 0% | US$0 | Research and forward observation only |
| `R1_canary` | 10% | US$500 | First guarded paper observations |
| `R2_probation` | 25% | US$1,250 | Early evidence remains within limits |
| `R3_established` | 50% | US$2,500 | Repeated independent paper outcomes remain sound |
| `R4_full_paper_limit` | 100% | US$5,000 | Maximum permitted paper tier, never a sizing target |

Each amount is an upper bound. Stop-based risk, liquidity, concentration,
portfolio correlation, drawdown, and current PaperOps controls may require a
smaller size or no trade.

#### Automatic risk-promotion requirements

Qadam may move up only one tier at a time when:

- the frozen minimum number of independent closed paper outcomes has matured;
- net expectancy remains positive after realized spread, slippage, and fees;
- the lower confidence bound, drawdown, tail loss, and calibration meet the
  tier's pre-registered policy;
- no source, model, route, lifecycle, reconciliation, or authority incident is
  unresolved;
- realized exposure and correlation remain inside portfolio limits;
- the strategy's mechanism and eligible regime remain valid; and
- the tier cooldown and minimum elapsed market-time requirements have passed.

Qadam automatically steps down or pauses faster than it steps up. A daily-loss
breach, strategy drawdown breach, stale critical source, unexpected slippage,
broken lineage, duplicate exposure, regime invalidation, or negative sequential
evidence causes an immediate downgrade, pause, or retirement according to the
frozen policy.

The governors may never autonomously:

- raise the US$5,000 absolute per-trade ceiling;
- widen aggregate gross, net, sector, correlation, drawdown, or daily-loss
  parent limits;
- add a new broker, venue, asset class, or live-capital route;
- admit an instrument outside the approved paper universe;
- alter their own policy, thresholds, signatures, or authority flags;
- accept provider terms, purchase data, or rotate credentials; or
- convert paper evidence into live-capital authority.

Those are constitutional changes, not strategy decisions. Within the frozen
parent policy, admission and tier progression require no user click.

## 6. Source Completion Matrix

### 6.1 Sources Already Scored

| Source | Current evidence | Completion action |
| --- | --- | --- |
| Kalshi | 5,034 signal rows | Preserve signal tests; complete contract lifecycle and direct-instrument cost history |
| Polymarket | 28,275 signal rows | Preserve signal tests; complete condition, token, liquidity, fee, and resolution history |
| SEC EDGAR | 2,475 rows | Expand filing taxonomy and issuer/sector mappings where point-in-time safe |
| STOCK Act | 29,824 filing-index rows | Parse underlying transaction disclosures and preserve filing-availability timing |
| USGS | 18,590 rows | Preserve as physical-world evidence and expand economically mapped event features |

### 6.2 Acquired But Not Yet Scored

| Source | Current evidence | Required empirical role |
| --- | ---: | --- |
| Alpaca | 22,244 rows | Reclassify primarily as price, portfolio, and execution-observation plane; do not force it into source quorum |
| BIS | 409,819 rows | Build point-in-time monetary, credit, liquidity, and cross-border regime features |
| BLS | 378 rows | Build release-surprise, revision-safe inflation and labour features |
| ECB | 2,698 rows | Build policy, rate, liquidity, and euro-area regime features |
| UCDP | 198,142 rows | Build conflict-intensity, geography, actor, escalation, and persistence features |

QBC must either make these rows empirically usable or explicitly prove why a
given dataset belongs only in context, provenance, or outcome planes.

### 6.3 Forward-Only Sources

| Source | Required action |
| --- | --- |
| AIS maritime | Obtain a licensed historical quote or start immutable route/chokepoint forward capture |
| ArcGIS/USACE | Review feature-service archive depth; otherwise capture waterway and infrastructure observations forward |
| Aviationstack | Review historical entitlement and begin bounded forward aviation-disruption capture |
| GPS jamming | Start timestamped geographic interference capture with source-availability evidence |
| Hyperliquid | Keep only if mapped to a strategy; capture market state forward under reviewed terms |
| Internet outage | Select an approved provider and capture region/event state forward |
| OREF | Preserve read-only event capture with publication timestamps |
| Reddit | Continue the narrative proxy forward; never treat aggregate popularity as historical ground truth |
| RSS | Archive selected feeds prospectively with content hash and retrieval time |
| Space-Track/Celestrak | Review legitimate archive coverage; otherwise capture orbital/TLE changes forward |
| Telegram | Preserve inbound observations as read-only, non-authoritative research events |
| TradingView MCP | Supplemental current technical context only; never count local samples as provider history |
| TradingView paid alerts | Capture future alerts only after entitlement and retention review |
| Twitter/X | Capture only through an approved interface and reviewed retention policy |
| Unusual Whales | Obtain an official historical export or rotate access and begin bounded forward capture immediately |

### 6.4 Currently Unavailable Or Excluded Sources

These states must be re-reviewed once, then either reopened through a valid
provider contract or deliberately remain excluded.

| Source | Completion decision |
| --- | --- |
| ACLED | Confirm research, retention, and model-use license; acquire if approved, otherwise remain unavailable |
| AIS or shipping composite | Remove as a duplicate alias once the canonical AIS source is selected |
| Bookmap | Add only for shortlisted microstructure experiments with verified historical rights |
| Chainlink | Retain only if a mapped crypto/macro hypothesis justifies it; otherwise exclude as not material |
| Coinglass | Retain only for mapped derivatives/liquidity hypotheses under reviewed history rights |
| Conflict Tracker | Resolve identity and independence versus UCDP/ACLED; exclude duplicate evidence |
| FRED | Perform a formal current terms and endpoint review, then acquire revision-aware series if approved |
| GDELT | Implement official bulk-archive acquisition and event/news identity normalization |
| GitHub | Exclude as non-material unless a pre-registered technology-supply hypothesis requires it |
| NASA FIRMS | Acquire official historical fire/thermal anomaly archives and map to affected regions/commodities |
| Patents | Acquire approved patent/publication history and map assignees to semiconductor/defence instruments |
| RapidAPI | Treat as an aggregator, not an independent source; register the underlying provider instead |
| Social RSS composite | Remove as a duplicate alias of canonical RSS/social sources |
| UN Comtrade | Confirm bulk retention and automated-use terms, then acquire mapped trade-flow series if approved |
| Yahoo Finance | Keep excluded from provider-backed evidence unless retention and provenance become contractually adequate |
| Yahoo Finance or TradingView composite | Remove as a duplicate/fallback alias, never as an independent signal |

## 7. Instrument And Resolution Completion

### 7.1 Existing Price Plane

The 17 conventional instruments have provider-backed daily history:

`BNO`, `CL=F`, `GLD`, `ITA`, `LMT`, `NVDA`, `PPA`, `QQQ`, `SI=F`, `SIL`,
`SLV`, `SMH`, `SOXX`, `SPY`, `USO`, `XAR`, and `XLE`.

These daily series remain the mandatory first-pass baseline. Futures require
explicit roll metadata; ETF proxies require basis-risk measurement.

### 7.2 Direct Prediction Instruments

`KALSHI:EVENTS` and `POLYMARKET:EVENTS` remain ineligible as direct instruments
until their selected contracts have:

- stable event, market, condition, token, and outcome identity;
- open, close, resolution, and settlement state;
- timestamped price or quote history while tradable;
- volume, open interest, liquidity, and spread evidence where available;
- fee and realistic fill assumptions;
- contract-rule and resolution provenance;
- an explicit research-only status if no guarded paper route exists.

Signal use and direct-instrument use must remain separate.

### 7.3 Intraday And Microstructure

Intraday, options, dark-pool, and order-book history must not be acquired across
the whole universe by default. It is expensive, storage-heavy, and increases
multiple-testing risk.

It may be added only for a pre-registered shortlist that survived daily/event
testing. Candidate datasets include:

- minute bars and historical spreads;
- consolidated volume and relative volume;
- Unusual Whales options flow and dark-pool records;
- Bookmap/order-book data under reviewed rights;
- futures microstructure from an approved provider; and
- direct prediction-market quotes or trades.

## 8. Canonical Data Contracts

Every normalized record must include:

```json
{
  "record_id": "stable immutable id",
  "source_key": "canonical source",
  "provider": "actual provider",
  "provider_record_id": "provider identity",
  "event_at": "when the underlying event occurred",
  "published_at": "when the provider published it",
  "available_at": "earliest conservative time Qadam could know it",
  "retrieved_at": "actual acquisition time",
  "instrument_or_market_map": [],
  "parser_version": "versioned parser",
  "raw_payload_hash": "sha256",
  "point_in_time_safe": true,
  "revision_state": "initial | revised | final | not_applicable",
  "license_state": "reviewed local research state",
  "provenance_complete": true
}
```

No normalized source may overload `event_at` as `available_at` without
provider-specific evidence.

Every terminal backtest result must also emit a strategy-impact record:

```json
{
  "strategy_impact_id": "stable immutable id",
  "backtest_result_id": "terminal result lineage",
  "hypothesis_version": "frozen hypothesis version",
  "strategy_family_id": "core id or no_core_family_fit",
  "incumbent_strategy_version": "current immutable version or null",
  "recommended_method_id": "occurrence | analog | state | entropy | nonlinear | quantum_challenge | flow_confirmation",
  "method_eligibility": "eligible | ineligible_typed_reason",
  "strategy_impact_state": "preserve | refine | demote | retire_rule | emerging_proposal | reject | insufficient_no_change",
  "net_holdout_result": "measured result reference",
  "robustness_frontier_state": "dominated | pareto_candidate | insufficient",
  "proposed_strategy_version": "new proposal version or null",
  "forward_validation_required": true,
  "paper_canary_eligible": false,
  "authority": "proposal_only"
}
```

The result object cannot change `authority`, mark itself forward-validated, or
set paper-canary eligibility from historical evidence.

Every autonomous admission or risk-tier decision must use this signed envelope:

```json
{
  "governance_decision_id": "stable immutable id",
  "decision_type": "strategy_admission | risk_tier_change",
  "subject_id": "exact strategy and policy version",
  "prior_state": "inactive or prior risk tier",
  "next_state": "admitted, denied, R0-R4, paused, or retired",
  "policy_version": "immutable signed policy hash",
  "evidence_hashes": [],
  "passed_conditions": [],
  "failed_conditions": [],
  "parent_ceiling_snapshot": {
    "paper_account_base": 100000,
    "absolute_per_trade_notional": 5000
  },
  "signature_actor": "python_autonomous_governance_engine",
  "llm_or_quantum_signature_allowed": false,
  "effective_at": "real timestamp",
  "expires_at": "mandatory reevaluation timestamp",
  "reversible": true
}
```

A missing policy hash, stale evidence, invalid signature, ceiling mismatch, or
expired decision denies admission or risk expansion fail-closed.

The programme must create these canonical artifacts:

- `data/runtime/qadam_backtest_completion_status.json`
- `data/runtime/qadam_source_empirical_role_registry.json`
- `data/runtime/qadam_backtest_completion_coverage.json`
- `data/runtime/qadam_backtest_completion_provider_gate.json`
- `data/runtime/qadam_backtest_completion_forward_maturity.json`
- `data/runtime/qadam_information_advantage_assessments.jsonl`
- `data/runtime/qadam_focused_edge_programmes.json`
- `data/runtime/qadam_frozen_hypothesis_registry.jsonl`
- `data/runtime/qadam_hypothesis_attempt_ledger.jsonl`
- `data/runtime/qadam_forward_research_freeze_registry.json`
- `data/runtime/qadam_material_learning_delta.json`
- `data/runtime/qadam_strategy_backtest_application_matrix.json`
- `data/runtime/qadam_backtest_strategy_impact.jsonl`
- `data/runtime/qadam_core_strategy_refinement_proposals.jsonl`
- `data/runtime/qadam_emerging_strategy_proposals.jsonl`
- `data/runtime/qadam_strategy_robustness_frontier.json`
- `data/runtime/qadam_forward_strategy_tournament.json`
- `data/runtime/qadam_strategy_portfolio_proposal.json`
- `data/runtime/qadam_post_backtest_decision.json`
- `data/runtime/qadam_value_of_information_queue.json`
- `data/runtime/qadam_autonomous_strategy_admission_policy.json`
- `data/runtime/qadam_autonomous_strategy_admission_decisions.jsonl`
- `data/runtime/qadam_adaptive_paper_risk_policy.json`
- `data/runtime/qadam_adaptive_paper_risk_decisions.jsonl`
- `data/runtime/qadam_autonomous_governance_audit.json`
- `data/runtime/qadam_paper_canary_registry.json`
- `data/runtime/qadam_backtest_completion_experiment_registry.json`
- `data/runtime/qadam_backtest_completion_results_summary.json`
- `data/runtime/qadam_backtest_completion_certification.json`
- `docs/qadam-backtest-completion-implementation-log.md`

Large raw, normalized, score, label, fold, and result partitions remain under
ignored `data/research/` paths.

## 9. Implementation Phases

## QBC-0 - Baseline Freeze And Non-Interference Contract

### Objective

Freeze the current evidence, code, paper epoch, provider state, and safety
boundary before any acquisition or recomputation.

### Build

- Snapshot hashes for the 41-source registry, 19-instrument universe,
  acquisition coverage, score tape, labels, backtest protocol, and paper epoch.
- Register the 2,652 prior hypotheses and zero survivors as the immutable
  starting result; an unchanged rerun may not be reported as new research.
- Freeze Programme A, Programme B, and Programme C identities before acquiring
  evidence specifically for them.
- Record free disk, memory, provider-call, monetary, and runtime ceilings.
- Freeze and sign the Autonomous Strategy Admission Policy, Adaptive Paper Risk
  Policy, US$100,000 paper base, US$5,000 per-trade ceiling, and all lower
  portfolio parent limits before any automatic decision is allowed.
- Keep the historical research lock distinct from PaperOps authority.
- Add a single programme status artifact and implementation log.
- Prove that no phase can invoke a broker-write entrypoint.

### Acceptance

- Baseline hashes are reproducible.
- The prior attempt family is present in the attempt ledger.
- The US$100,000 paper epoch is unchanged.
- Governance policies and parent ceilings are immutable, hash-addressed, and
  fail closed on any mismatch.
- Live capital is false.
- No raw research path is Git-trackable.
- No acquisition starts during preflight.

### Checker

`scripts/check_qadam_backtest_completion_baseline.py`

## QBC-1 - Empirical Role Registry And Gap Ledger V2

### Objective

Replace the coarse acquired/forward/unavailable matrix with an operational
decision for every source and instrument.

### Build

- Assign each source an empirical role and priority tier.
- Assign each source an information-advantage state rather than assuming that
  connection or freshness implies uniqueness.
- Separate price-plane, context, predictive-signal, cost, identity, and
  duplicate roles.
- Record historical depth, resolution, current scoreability, intended feature
  family, mapped strategies, mapped instruments, and required operator action.
- Reconcile all aliases and composite sources.
- Generate a machine-actionable queue for acquisition, parsing, feature work,
  forward capture, and exclusion.
- Create the three focused programme contracts and enforce the initial 80/20
  focused-versus-challenger resource budget.
- Require every proposed experiment to pass or fail the six-part information-
  advantage assessment before it can consume a holdout.

### Acceptance

- Exactly 41 source decisions and 19 instrument decisions exist.
- Generic missing count is zero.
- Every acquired-but-unscored source has an owner and disposition.
- Exactly three initial focused programmes exist with immutable first-version
  mechanism, instrument, horizon, baseline, cost, and failure contracts.
- No challenger bypasses the information-advantage admission gate.
- Counts reconcile across provider, dashboard, score, and backtest artifacts.

### Checker

`scripts/check_qadam_backtest_completion_roles.py`

## QBC-2 - Existing Acquired Data Scoreability

### Objective

Extract value from BIS, BLS, ECB, and UCDP before purchasing more data.

### Build

- BIS: credit growth, cross-border liquidity, leverage, dollar funding, and
  monetary-regime features.
- BLS: initial-release inflation/labour values, surprise versus prior
  expectation where available, and revision-safe vintages.
- ECB: policy decisions, rates, balance-sheet/liquidity, and euro regime state.
- UCDP: actor, geography, event intensity, fatalities, escalation, persistence,
  and distance-to-asset/chokepoint features.
- Document why Alpaca belongs primarily in price, fill, spread, and portfolio
  planes rather than being counted as an independent predictive source.
- Add source-only, core-plus-source, and time-shifted ablations.

### Acceptance

- Every acquired source has a tested or deliberately non-predictive role.
- Initial-release values are used instead of revised hindsight values.
- UCDP event timing is publication-safe.
- No source gains causal credit from correlation alone.

### Checker

`scripts/check_qadam_acquired_source_scoreability.py`

## QBC-3 - STOCK Act Transaction Detail Lake

### Objective

Convert filing-index history into structured, point-in-time transaction
evidence.

### Build

- Retrieve the underlying official disclosure documents by document ID.
- Support PDF, HTML, table extraction, and bounded OCR fallback.
- Parse filer, owner, asset description, ticker where disclosed, transaction
  type, transaction date, filing date, amount range, amendment, and comment.
- Preserve amount ranges; never fabricate exact notionals.
- Resolve assets to issuers, sectors, ETFs, and Qadam instruments with confidence
  and unresolved-state records.
- Deduplicate amendments and repeated documents without erasing lineage.
- Score only from public filing availability, never private transaction date.
- Register filing-only, transaction-detail, buy/sell, amount-sensitivity,
  sector-cluster, filer-concentration, and leakage-control experiments.

### Acceptance

- Filing index and transaction details remain separate planes.
- Parser coverage and field completeness are reported by year and document
  type.
- Unresolved assets remain explicit.
- Transaction-date leakage control cannot validate.
- Exact notional fabrication count is zero.

### Checker

`scripts/check_qadam_stock_act_transaction_detail_completion.py`

## QBC-4 - Kalshi Contract History Completion

### Objective

Complete Kalshi history as both a research signal and, where defensible, a
direct research instrument.

### Build

- Acquire selected event and market metadata, lifecycle states, rules,
  candlesticks or quote/trade history, volume, open interest, settlement, and
  fees through approved official interfaces.
- Preserve event ticker to market ticker identity and contract-version changes.
- Cluster equivalent events across time and across prediction venues.
- Separate probability features from eventual outcomes.
- Build realistic direct-contract cost and fill models.
- Keep direct instrument testing disabled when paperability or historical
  liquidity is incomplete.

### Acceptance

- Every selected contract has a complete or typed-incomplete lifecycle.
- Resolution is unavailable to pre-resolution scores.
- Kalshi-only, cross-venue, and direct-instrument tests are independently
  identifiable.
- No API write route exists.

### Checker

`scripts/check_qadam_kalshi_contract_history_completion.py`

## QBC-5 - Polymarket Contract History Completion

### Objective

Complete Polymarket condition, token, outcome, liquidity, and resolution
history without treating it as an execution venue.

### Build

- Acquire condition, market, token, and outcome identity.
- Capture point-in-time price history, trades or quotes where approved,
  liquidity, spread, fees, lifecycle, and resolution provenance.
- Handle token replacements, multi-outcome markets, archived markets, and
  question edits.
- Cluster equivalent Kalshi/Polymarket events without double-counting source
  independence.
- Register probability, change, coherence, disagreement, liquidity, and direct
  research-instrument tests.

### Acceptance

- Condition-to-token-to-outcome lineage is complete or explicitly typed.
- Outcome leakage is zero.
- Cross-venue agreement does not count as two independent sources when the
  contracts represent the same underlying event.
- Polymarket remains research-only.

### Checker

`scripts/check_qadam_polymarket_contract_history_completion.py`

## QBC-6 - Unusual Whales Historical And Forward Feature Plane

### Objective

Measure whether options positioning and dark-pool evidence add incremental
value to Qadam's macro signals.

### Build

- Prefer an official historical export with documented research retention.
- Otherwise rotate credentials and start bounded forward capture immediately.
- Capture market tide, unusual flow alerts, ticker dark-pool prints, options
  volume, put/call state, premium, open interest, and approved derived Greeks.
- Record endpoint, instrument, event time, conservative availability time,
  retrieval time, parser version, and payload hash.
- Run mandatory comparisons:
  1. core Qadam without Unusual Whales;
  2. core plus Unusual Whales;
  3. Unusual Whales only;
  4. time-shifted control; and
  5. shuffled control.

### Acceptance

- A single current API call never counts as historical coverage.
- Provider-only performance cannot replace the core baseline.
- Missing official history becomes real forward-maturity work, not fabricated
  backfill.
- Credentials and raw payloads remain unexposed.

### Checker

`scripts/check_qadam_unusual_whales_completion.py`

## QBC-7 - Geopolitical, Physical-World, And Public Archive Expansion

### Objective

Acquire the most strategy-relevant recoverable archives currently classified
unavailable.

### Priority order

1. GDELT event/news bulk history.
2. NASA FIRMS fire and thermal-anomaly history.
3. Patent/publication history mapped to semiconductor and defence actors.
4. Formally approved ACLED history.
5. UN Comtrade flows mapped to selected commodities and supply chains.
6. Formally approved FRED vintages and release calendars.

### Build

- Add one provider adapter per canonical source, never a generic aggregator as
  provenance.
- Run bounded pilots before bulk acquisition.
- Record archive coverage, publication semantics, revisions, geospatial
  identity, parser version, and license state.
- Map each archive to economic hypotheses before scoring it.
- Exclude low-value or duplicative sources instead of maximizing source count.

### Acceptance

- Each priority source is acquired, formally blocked, or excluded with a
  current reviewed reason.
- Event/news duplicates are clustered.
- Geospatial and entity mappings have confidence and unresolved states.
- Current revisions do not overwrite historical vintages.

### Checker

`scripts/check_qadam_public_archive_completion.py`

## QBC-8 - Forward-Only Capture And Maturity Clock

### Objective

Start reliable prospective evidence collection for sources without recoverable
history.

### Build

- Register source-specific cadences, session windows, rate limits, retention,
  and freshness thresholds.
- Store immutable observations with real `retrieved_at` and conservative
  `available_at`.
- Track uptime, missing intervals, provider outages, duplicate events, and
  observation density.
- Calculate required future label dates for each horizon.
- Prevent laptop sleep, network interruption, or process restart from creating
  silent holes.
- Display real elapsed days and mature outcomes; never simulate progress.

### Acceptance

- Every retained forward-only source has an active capture or explicit operator
  blocker.
- Forward coverage gaps are visible by source and date.
- No future label is generated before its real horizon closes.
- Capture cannot create candidates or trades.

### Checker

`scripts/check_qadam_forward_source_maturity.py`

## QBC-9 - Selective Intraday And Microstructure Completion

### Objective

Add execution-relevant evidence only where a daily/event hypothesis justifies
the cost and complexity.

### Build

- Create an admission gate requiring a pre-registered surviving daily/event
  relationship.
- Acquire bounded minute, spread, volume, options, or order-book history for
  admitted instruments only.
- Model market hours, auctions, halts, futures sessions, stale quotes,
  liquidity, slippage, and proxy basis risk.
- Keep provider and storage cost ledgers.
- Deny whole-universe tick acquisition by default.

### Acceptance

- Every microstructure dataset maps to a named experiment.
- Cost and disk ceilings are enforced before network calls.
- Intraday evidence is aligned without bar-close or quote lookahead.
- Execution confirmation is measured separately from predictive discovery.

### Checker

`scripts/check_qadam_selective_microstructure_completion.py`

## QBC-10 - Point-In-Time Evidence Rebuild V3

### Objective

Rebuild the source-price matrix from the expanded evidence without leakage or
double counting.

### Build

- Join only records with `available_at <= decision_at`.
- Preserve source identity, event cluster, market mapping, regime, and parser
  version.
- Separate source features, prices, costs, outcomes, and revisions.
- Add independence clustering for equivalent news, prediction contracts,
  filings, and provider mirrors.
- Recalculate missing forward windows with typed reasons.
- Produce source, instrument, year, regime, and horizon coverage.

### Acceptance

- Leakage violations are zero.
- Duplicate logical writes are zero.
- Every missing label has a typed reason.
- Coverage denominators include unavailable and excluded lanes.
- The paper epoch remains unchanged.

### Checker

`scripts/check_qadam_backtest_completion_point_in_time.py`

## QBC-11 - Feature Registry V5 And Frozen Score Tape

### Objective

Create one deterministic score plane that uses all eligible evidence without
embedding future outcomes.

### Build

- Version every feature definition, transform, missingness rule, and penalty.
- Add feature families for macro regimes, conflict escalation, filings and
  transactions, prediction probabilities, physical-world events, narrative
  state, options/flow confirmation, and approved microstructure.
- Keep raw feature values and model-ready transforms separately.
- Write source-only, source-removed, strategy-blind, and matched-control score
  variants.
- Freeze the score tape before labels are read.

### Acceptance

- Identical inputs and protocol produce identical scores and hashes.
- Future returns, outcomes, settlements, and revised values do not exist in
  score partitions.
- Every score explains contributions, missing evidence, and penalties.
- Removing one provider cannot mutate unrelated features.

### Checker

`scripts/check_qadam_backtest_completion_score_tape.py`

## QBC-12 - Expanded Experiment Registry And Statistical Backtest

### Objective

Test the three focused edge programmes first, then admit bounded whole-universe
challengers under separately pre-registered false-discovery families.

### Build

- Register hypotheses before evaluating untouched holdouts.
- Write every version and terminal result to the immutable attempt ledger so a
  rejected idea cannot return under a cosmetic name.
- Require an economic mechanism, mapped market, horizon, baseline, cost model,
  invalidation, and expected failure mode.
- Require a frozen information-advantage assessment and pre-run power or
  minimum-detectable-effect analysis.
- Run chronological walk-forward folds with purge and embargo.
- Reserve a final untouched holdout.
- Apply fees, spread, slippage, liquidity, futures-roll cost, and proxy basis
  risk.
- Compare against unconditional return, momentum, reversal, strategy-blind
  linear, time-shifted, and shuffled baselines.
- Report source-only, source-added, source-removed, and interaction results.
- Apply the eligible occurrence, lead-lag, vector-analog, state-matrix,
  cross-asset, entropy, nonlinear, quantum-challenge, and practical-confirmation
  methods to every core strategy under the method-to-strategy matrix.
- Emit a strategy application record even when a method is ineligible because
  sample size, timestamp quality, or data type is insufficient.
- Control repeated discovery with Benjamini-Hochberg or a stricter registered
  family policy where appropriate.
- Enforce the focused-versus-challenger compute, provider-call, and statistical
  attempt budget.
- Stop a programme version immediately when a frozen kill condition becomes
  terminal; do not spend later model tiers trying to rescue it.

### Priority experiment groups

| Priority | Experiment family | Required role |
| --- | --- | --- |
| 1 | Prediction-market disagreement preceding listed-market repricing | Focused Programme A |
| 2 | STOCK Act disclosure detail preceding defence or semiconductor basket repricing | Focused Programme B |
| 3 | Unusual Whales strengthening or rejecting an existing macro signal | Focused Programme C |
| 4 | Existing five scored-source baselines and BIS/BLS/ECB/UCDP increments | Required attribution and benchmark family |
| 5 | Direct prediction instruments when eligible | Separate research-instrument family |
| 6 | GDELT/ACLED/UCDP independence, NASA FIRMS disruption, and patent-policy interactions | Mechanism-backed challenger family |
| 7 | Source divergence, cross-asset relationships, core strategy families, and strategy-agnostic discovery | Bounded whole-universe challengers |

Priority does not permit weak evidence to advance. It determines where Qadam
spends scarce acquisition, model, and review capacity.

### Acceptance

- Every eligible experiment is tested or explicitly insufficient.
- Every experiment has a completed information-advantage assessment, frozen
  contract, attempt lineage, and terminal state.
- Results report independent event count and statistical power, not only raw
  row count.
- The three focused programmes are distinguishable from whole-universe
  challengers in every artifact and dashboard summary.
- All five core strategies have complete method-eligibility and result matrices
  with net-of-cost holdout outcomes or typed insufficiency reasons.
- Strategy-agnostic discoveries remain visible and are not forced into a core
  family.
- Adjusted-significant negative controls remain diagnostic and can never
  validate; certification blocks only if a control survives all ordinary
  promotion gates.
- Every result has one terminal research state.
- No result mutates a strategy or creates a trade.

### Checker

`scripts/check_qadam_backtest_completion_statistical.py`

## QBC-13 - Nonlinear, Entropy, And Quantum Incremental Value

### Objective

Determine whether nonlinear or quantum-assisted methods add measurable value
beyond matched classical methods.

### Build

- Shortlist only hypotheses with adequate independent observations.
- Require the classical linear or simple-rule baseline to be complete before
  nonlinear or quantum-assisted work starts.
- Test vector analogs, state matrices, tree/interaction models, regime-path
  dependence, ordinal/permutation entropy, and approved nonlinear models.
- Run each quantum-assisted experiment with identical features, splits, costs,
  labels, and holdouts as its classical comparator.
- Label Qiskit Aer simulation, IBM hardware execution, Q-CTRL mitigation, and
  classical fallback honestly.
- Measure incremental out-of-sample return, calibration, stability, runtime,
  and cost.
- Charge every nonlinear and quantum variant to the same registered attempt
  family so model proliferation cannot evade false-discovery accounting.

### Acceptance

- Quantum execution cannot create evidence unavailable to the classical lane.
- No quantum job runs merely because a provider lane exists or a classical
  result failed.
- Simulator results are not called hardware results.
- Quantum value is `proven`, `not_proven`, `negative`, or `not_measurable`.
- Quantum review creates no approval or authority.

### Checker

`scripts/check_qadam_backtest_completion_nonlinear_quantum.py`

## QBC-14 - Backtest-To-Strategy Translation And Foundry

### Objective

Make every backtest result influence Qadam's strategy knowledge without
silently mutating an active strategy or creating execution authority.

### Build

- Join every terminal result to one or more core strategy families through an
  explicit fit vector, while preserving a valid `no_core_family_fit` state.
- Create one strategy-impact decision for every result: preserve, refine,
  demote, retire rule, emerging proposal, reject, or insufficient/no change.
- Build the strategy application matrix across all five core families and all
  eligible recommended methods.
- Produce incumbent-versus-challenger evidence maps on identical data, folds,
  holdouts, costs, and regimes.
- Generate immutable `vNext` core-strategy refinement proposals without
  overwriting current definitions.
- Send genuinely distinct surviving relationships to Strategy Foundry V3 as
  provisional emerging strategies with Research Goal lineage, mechanism,
  instruments, timing, invalidation, paperability, and risk concept.
- Build an autonomous-admission packet containing every machine-verifiable
  historical, forward, novelty, paperability, dependency, and exposure gate.
- Record source, feature, model, regime, instrument, cost, and ablation
  attribution for every proposed change.
- Convert rejections into typed lessons and value-of-information questions
  without claiming causal truth.

### Acceptance

- Every terminal result has exactly one strategy-impact state.
- All five core strategies have method-application and evidence maps.
- An incumbent remains unchanged unless a signed Autonomous Strategy Governor
  or explicit operator decision admits the challenger.
- A new strategy cannot be a renamed threshold variant or duplicate exposure.
- Historical candidates, strategy proposals, validated strategies, and current
  trade setups remain separate objects.
- No strategy translation creates an Akber pass, Router decision, order, broker
  write, or proof credit.

### Checker

`scripts/check_qadam_backtest_strategy_translation.py`

## QBC-15 - Forward Strategy Tournament And Portfolio Governance

### Objective

Select the most robust and diversifying historical survivors for frozen real-
time evaluation rather than promoting the highest-return backtest.

### Build

- Build the Pareto robustness frontier across net expectancy, uncertainty,
  drawdown, turnover, liquidity, independent events, regime stability, source
  fragility, capacity, and candidate correlation.
- Select a small diversified tournament slate without duplicating the same
  source, event, market, or mechanism.
- Freeze candidate source, feature, instrument, direction, threshold, horizon,
  cost, entry, exit, and invalidation rules.
- Start real forward shadow observation for at least 60 market days, schedule
  the principal review at 90 market days, and require the pre-registered
  independent-event minimum even when 90 days have elapsed.
- Compare each candidate with its incumbent, simple baseline, no-trade outcome,
  and counterfactual Akber holds and vetoes.
- Measure missed opportunities, false positives, filter value, drawdown,
  turnover, cost, and portfolio correlation.
- Produce a proposal-only portfolio of compatible forward survivors; do not
  optimize allocation against the final forward window.
- Evaluate every qualifying survivor under the immutable Autonomous Strategy
  Admission Policy and write a signed admit or deny decision automatically.
- Route failed or insufficient results to the value-of-information queue.

### Acceptance

- Historical candidate remains distinct from validated strategy.
- Forward evidence uses only information arriving after the strategy version
  froze.
- Any parameter change creates a new version and restarts the forward clock.
- A 90-day period with insufficient independent events remains evidence
  maturing.
- Selection cannot be based on one headline return, Sharpe ratio, or confidence
  score.
- Akber attribution measures whether pass, hold, or veto improved decisions but
  creates no execution approval.
- A qualifying strategy can become paper-admitted without a user click, while a
  denied or incomplete strategy remains inactive with exact reasons.
- Every automatic admission carries policy, evidence, strategy-version, expiry,
  and signature lineage.
- No paper order or proof credit is created.

### Checker

`scripts/check_qadam_forward_strategy_tournament.py`

## QBC-16 - Guarded Paper Canary And Sequential Promotion

### Objective

Conditionally turn a forward-confirmed current setup into the smallest safe
paper experiment through Qadam's existing authority chain.

### Build

- Require positive net-of-cost historical holdout evidence and frozen forward-
  shadow survival before a strategy can generate a current review setup.
- Require a fresh signed Autonomous Strategy Governor admission for the exact
  strategy version.
- Require complete current evidence, source freshness, source quorum, Akber
  pass, portfolio-risk approval, and Router `paper_review_candidate` state.
- Preserve Research Goal lineage, strategy version, candidate identity,
  idempotency, duplicate exposure, daily drawdown, Q-CTRL, and guarded Alpaca
  Paper route checks.
- Implement the `R0` through `R4` adaptive paper-risk ladder and reconcile its
  US$5,000 parent ceiling with canonical risk configuration.
- Size each setup using the lowest of the strategy's current tier, stop-based
  risk, liquidity allowance, portfolio risk budget, and absolute parent cap.
- Evaluate tier promotion automatically after eligible independent closed
  paper outcomes; historical performance alone cannot promote a tier.
- Sign every promotion, denial, downgrade, pause, and retirement decision with
  policy version, evidence hashes, metrics, reason codes, and expiry.
- Track submit, accept, fill, open, close, postmortem, and real paper proof
  eligibility with no ambiguous lifecycle state.
- Promote only through `shadow_only`, `paper_canary`, `paper_probation`, and
  `paper_active_within_limits` under frozen sequential evidence thresholds.
- Pause or retire on stale inputs, broken lineage, adverse drawdown, execution
  deterioration, regime failure, or invalidated mechanism.
- Keep the account in cash when no candidate passes every gate.

### Acceptance

- There is no direct path from a backtest result to an order.
- Every broker write uses canonical PaperOps and Alpaca Paper only.
- Multiple distinct canaries remain subject to independent lineage,
  idempotency, exposure, drawdown, and risk checks.
- A qualifying strategy may advance one paper-risk tier automatically without
  a user click.
- No autonomous decision exceeds US$5,000 per trade or any lower strategy,
  liquidity, correlation, drawdown, daily-loss, or portfolio limit.
- Adverse evidence causes automatic downgrade or pause without waiting for an
  operator.
- Real paper trial progress and proof eligibility come only from actual market-
  time paper fills and closes.
- No trade quota forces a canary.
- `no_eligible_paper_canary_cash_preserved` is a passing state when no setup
  clears every gate.
- Live capital remains disabled.

### Checker

`scripts/check_qadam_guarded_paper_canary.py`

## QBC-17 - Automation, Dashboard, And Telegram Integration

### Objective

Make completion progress and future evidence compounding understandable without
turning the dashboard into a technical console.

### Automation changes

- Provider capture runs on source-specific cadences.
- Label jobs run only when real horizons mature.
- Incremental backtests run when enough new independent labels exist.
- Every terminal backtest automatically receives a proposal-only strategy-
  impact decision; no result is left disconnected from strategy knowledge.
- A full challenger backtest runs weekly or after a material dataset/version
  change, not on every operator poll.
- The Daily Learning Brief sends only for a material evidence delta, matured
  outcome, changed hypothesis state, provider blocker, or reviewed proposal.
- The Daily Learning Brief's primary contract is: what new evidence arrived,
  which hypothesis became stronger or weaker, which outcome matured, what was
  rejected, and what Qadam will test next.
- Activity counts may appear as secondary provenance only. They may not be the
  headline or imply progress when no research state changed.
- A canonical material-delta comparator decides whether a brief exists. If no
  material state changed, the correct result is `quiet_no_material_change` and
  no Telegram send is attempted.
- Safe network failures retry with bounded backoff; optional notification
  transport cannot stop local research.
- Self-healing may resume idempotent jobs but cannot edit code, buy data,
  accept terms, rotate secrets, change authority, or bypass tests.
- Monthly strategy governance reviews incumbent refinements, emerging strategy
  proposals, automatic admission decisions, risk-tier changes, forward
  tournament state, and paper-canary evidence without requiring routine clicks.
- The guarded paper operator continues at its existing cadence and remains idle
  in cash when no setup clears every gate.

### Dashboard enrichment

- Data Sources: historical depth, empirical role, scoreability, freshness,
  forward maturity, and exact blocker.
- Trading Universe: daily/intraday/direct-contract evidence coverage and proxy
  basis risk.
- Pattern Recognition: source-price evidence used, observation count, holdout
  state, information-advantage claim, independent event count, and next
  maturation date.
- Quantum Edge: matched classical comparison and honest conclusion.
- Trading Strategies: core incumbent versus proposed refinement, emerging
  strategy proposals, autonomous admission decision, current risk tier, method
  evidence, rejected rules, and forward/paper state.
- Decision Room: only current setups from strategies that survived historical
  and forward gates, with Akber, portfolio-risk, and Router consequences.
- Portfolio and Trading History: real paper canary lineage, strategy version,
  lifecycle, outcome, and paper proof status without showing historical
  backtests as trades.
- Learn & Improve: the five-part material learning answer, rejected versions,
  strategy impact, forward progress, canary outcome, and next frozen test.

### Acceptance

- Existing dashboard structure and navigation are unchanged.
- Counts reconcile with canonical artifacts.
- A no-change day produces no celebratory activity brief and no duplicate
  notification.
- Each material brief identifies the exact hypothesis version and evidence or
  outcome that changed its state.
- The dashboard distinguishes configured core families, provisional emerging
  strategies, forward candidates, and real paper-active strategies.
- A completed backtest visibly states what changed in each core strategy and
  whether any new strategy was proposed.
- Every automatic admission or risk-tier change is visible with evidence,
  policy version, reason, expiry, and rollback condition.
- No dashboard or Telegram interaction creates authority.
- Quiet/no-material-change is a valid automation result.

### Checker

`scripts/check_qadam_backtest_completion_visibility.py`

## QBC-18 - End-To-End Certification

### Objective

Certify completion without certifying profitability.

### Build

- Add `scripts/check_qadam_backtest_completion.py`.
- Write
  `data/runtime/qadam_backtest_completion_certification.json`.
- Validate all phase checks, artifact hashes, source/instrument roles,
  provider states, information-advantage assessments, focused programme
  contracts, point-in-time safety, experiment registration, attempt lineage,
  strategy application matrices, strategy-impact decisions, refinement and
  emerging proposals, robustness frontier, forward freezes, portfolio
  proposal, autonomous-admission policy and signatures, adaptive-risk policy
  and tier decisions, paper-canary lineage, negative controls, dashboard truth,
  and authority boundaries.
- Add negative probes for fixture promotion, current-revision leakage,
  transaction-date leakage, prediction resolution leakage, source duplication,
  fake exact STOCK Act values, unregistered hypotheses, holdout tuning,
  provider sample promotion, secret leakage, historical or simulated paper-
  calendar mutation, unauthorized broker writes, historical/replay/shadow proof
  credit, unchanged-hypothesis relabelling, post-outcome parameter changes,
  quantum-without-classical comparison, activity-only learning briefs,
  duplicate Telegram sends, trade quotas, forced promotion, silent incumbent
  mutation, duplicate emerging strategy, direct backtest-to-order routing,
  backtest-driven risk-limit widening, final-window portfolio optimization, and
  unguarded paper submission, unsigned automatic admission, LLM-signed
  admission, risk-tier skipping, parent-ceiling breach, self-modified governance
  policy, and delayed adverse-evidence downgrade.

### Passing outcomes

The checker may pass with:

- `complete_no_edge_found`;
- `historical_candidate_found_forward_validation_required`;
- `strategy_proposal_forward_validation_required`;
- `forward_validated_paper_canary_eligible`;
- `autonomously_admitted_paper_canary_eligible`;
- `guarded_paper_canary_operating`;
- `adaptive_paper_risk_tier_operating`.

It must not require an edge to pass and must not call a historical candidate a
validated edge.

### Acceptance

- Every QBC phase passes or has an explicitly permitted temporal hold.
- All three focused programmes are terminally classified or honestly remain in
  real forward-evidence maturation under frozen rules.
- Whole-universe challenger attempts remain within the registered budget.
- All five core strategy families have complete strategy-method result maps.
- Every terminal result has exactly one strategy-impact decision.
- Every emerging strategy is provisional until independently admitted.
- Every automatic strategy admission and risk-tier change is deterministic,
  signed, policy-versioned, reproducible, and reversible.
- Available-history completion is independently reported from forward maturity.
- The paper epoch is unchanged before QBC-16; any later difference reconciles
  exactly to guarded PaperOps receipts from an eligible real-time canary.
- Certification itself creates zero broker writes, paper orders, proof credits,
  or live-capital changes.
- Historical, replay, and shadow records receive zero paper proof credit.
- Live capital remains disabled in every passing outcome.

## 10. Dependency And Parallelism Plan

```text
QBC-0 baseline
  -> QBC-1 role registry
      -> QBC-2 acquired-source features
      -> QBC-3 STOCK Act details
      -> QBC-4 Kalshi completion
      -> QBC-5 Polymarket completion
      -> QBC-6 Unusual Whales
      -> QBC-7 public archives
      -> QBC-8 forward capture
          -> QBC-9 selective intraday only when admitted

QBC-2 through QBC-9
  -> QBC-10 point-in-time rebuild
  -> QBC-11 frozen score tape
  -> QBC-12 statistical backtest
  -> QBC-13 nonlinear/quantum review
  -> QBC-14 strategy translation and foundry
  -> QBC-15 forward strategy tournament
  -> QBC-16 conditional guarded paper canary
  -> QBC-17 visibility and automation
  -> QBC-18 certification
```

QBC-2 through QBC-8 may run in parallel after QBC-1. QBC-10 must wait until
the selected historical acquisition lanes are terminal. QBC-8 continues after
the available-history certification because real forward time cannot be
compressed.

QBC-14 runs immediately after terminal historical results. QBC-15 consumes only
surviving frozen candidates and requires real elapsed market time. QBC-16
remains safely idle in cash unless a current setup clears every existing gate.
QBC-17 may expose honest progress while QBC-15 is maturing. QBC-18 reports the
actual terminal or temporal state rather than requiring a trade.

## 11. Statistical Promotion Policy

A result may become a historical candidate only when it:

- has adequate independent observations;
- passed a frozen information-advantage assessment before testing;
- has a pre-registered economic mechanism;
- has conservative publication and availability timing that precedes the
  outcome window;
- survives chronological walk-forward validation;
- remains positive on an untouched holdout;
- remains positive after realistic costs and proxy basis risk;
- beats a simple matched baseline;
- survives false-discovery adjustment;
- is not concentrated in one date, contract, filer, event, source, regime, or
  instrument;
- remains sufficiently stable across relevant regimes;
- passes source ablation and negative-control review;
- has complete source-price-experiment lineage; and
- can be observed prospectively without changing its rules.

Historical success is insufficient for paper execution. It must later earn
at least 60-90 real market days and the required number of independent forward
events under frozen rules. Before forward observation, it must create either a
versioned core-strategy challenger or a provisional emerging strategy through
Strategy Foundry. After forward survival, a current setup must pass Akber,
portfolio risk, Router, and PaperOps independently. Portfolio selection uses the
robustness frontier and correlation constraints, not the highest historical
return. No trade quota or minimum candidate count may weaken those
requirements.

## 12. Laptop Runtime And Cost Design

The programme must remain viable on the M5 laptop with 24 GB RAM and 1 TB SSD.

### Resource policy

- Stream provider pages and document partitions; never load the full lake into
  memory.
- Use Parquet/JSONL partitions and DuckDB or equivalent bounded scans.
- Cap CPU workers by workload, normally two to four.
- Keep memory below a frozen safe ceiling and expose current peak use.
- Establish a free-disk floor before starting bulk work.
- Estimate bytes, requests, duration, and provider cost before each lane.
- Pause safely before crossing any disk, request, time, or monetary ceiling.
- Store resumable cursors and atomic completion manifests.
- Reuse immutable completed partitions after hash verification.

### Acquisition tiers

| Tier | Scope | Default decision |
| --- | --- | --- |
| 1 | Existing acquired data and public daily/event archives | Implement first |
| 2 | Priority provider exports and contract histories | Operator-reviewed bounded acquisition |
| 3 | Forward-only capture | Start early and run continuously |
| 4 | Intraday/options/order-book history | Shortlist only; separate cost approval |

Automation may estimate costs but may not purchase data or accept provider
terms.

## 13. Testing Strategy

Every phase requires the relevant subset of:

- schema and authority validation;
- deterministic IDs and hashes;
- provider pagination and cursor tests;
- interrupted-resume equivalence;
- duplicate logical write denial;
- immutable completed partition checks;
- rate-limit and backoff behavior;
- storage and monetary ceiling probes;
- timezone and market-calendar handling;
- publication and availability timestamp tests;
- revision-vintage preservation;
- corporate-action and futures-roll handling;
- prediction-contract identity and resolution leakage tests;
- STOCK Act amendment, amount-range, and transaction-date leakage tests;
- source-independence clustering;
- score-before-label separation;
- cost and slippage application;
- walk-forward, purge, embargo, and untouched-holdout isolation;
- multiple-testing accounting;
- negative-control rejection;
- source-only, source-added, and source-removed ablations;
- classical versus quantum parity;
- five-core-strategy method-application completeness;
- exactly-one strategy-impact decision per terminal result;
- incumbent-versus-challenger fold, cost, and holdout parity;
- emerging-strategy novelty and duplicate-exposure rejection;
- robustness-frontier determinism and final-window isolation;
- forward-version freeze and clock-reset behavior;
- autonomous-admission determinism, signature, expiry, and stale-evidence
  denial;
- adaptive risk-tier progression, one-tier-only promotion, immediate downgrade,
  and US$5,000 parent-ceiling enforcement;
- LLM/quantum admission-signature denial and governance-policy self-mutation
  denial;
- direct backtest-to-order denial;
- guarded paper-canary authority, idempotency, exposure, drawdown, and route
  probes;
- cash/no-order behavior when no candidate survives;
- no trade candidate, risk approval, execution approval, order, broker-write,
  proof-credit, or calendar-change probes for QBC-0 through QBC-15;
- dashboard denominator and wording checks; and
- secret scans over tracked files and public artifacts.

## 14. Operator Actions

Qadam must pause with an exact action request when it needs the operator to:

- approve current provider research and retention terms;
- rotate and securely install an exposed credential;
- request an official historical export;
- approve a paid provider quote or higher storage ceiling;
- approve an instrument proxy and basis-risk threshold;
- decide whether a low-value source should remain excluded;
- approve a direct prediction-market research contract universe;
- approve an intraday or microstructure shortlist;
- raise the US$5,000 absolute per-trade paper ceiling;
- widen aggregate exposure, drawdown, daily-loss, sector, or correlation parent
  limits;
- add an instrument outside the approved paper universe;
- add a broker, venue, or asset class; or
- change live-capital or constitutional authority.

Provider requests must state the dataset, intended use, expected coverage, cost,
storage, consequence of declining, and safe fallback. Constitutional policy
requests must state the exact proposed boundary, evidence, expected risk,
failure conditions, consequence, and safe no-action fallback. No request may
ask for a secret to be committed or pasted into a tracked file.

Admission of an eligible core refinement or emerging strategy and movement
through `R0` to `R4` do not require operator action. The signed paper-only
policy is the standing authorization. Qadam pauses only when a proposed action
would change an outer boundary listed above.

## 15. Automation Rhythm After Implementation

| Automation | Recommended trigger | Purpose |
| --- | --- | --- |
| Kalshi, Polymarket, STOCK Act, and Unusual Whales capture | Provider-specific and continuous while the laptop service is active | Preserve the focused programme events and exact availability times |
| Other source capture | Provider-specific, normally 5-60 minutes | Preserve fresh observations and publication times |
| Historical acquisition | Resumable bounded job | Fill approved partitions without affecting live research |
| Forward-label maturation | Hourly/daily horizon check | Create outcomes only after real time closes |
| Incremental focused-programme test | Material new independent labels | Update a frozen programme without rerunning unchanged evidence |
| Full challenger backtest | Weekly schedule, skipping quietly when no eligible evidence or version changed | Re-evaluate the registered challenger family without manufacturing activity |
| Quantum review | Only for shortlisted nonlinear hypotheses | Measure incremental value efficiently |
| Strategy-impact translation | Every terminal backtest result | Preserve, refine, demote, retire, reject, or propose an emerging strategy |
| Forward strategy tournament | On each matured independent event and daily state reconciliation | Compare frozen challengers, incumbents, no-trade outcomes, and Akber consequences |
| Autonomous strategy admission | Every qualifying forward-tournament decision and dependency refresh | Admit or deny the exact strategy version under the signed policy without a user click |
| Paper canary evaluation | Existing guarded PaperOps cadence | Submit only a current setup that independently clears every paper gate |
| Adaptive paper-risk evaluation | Every eligible closed paper outcome and daily risk reconciliation | Promote one tier, hold, downgrade, pause, or retire inside immutable parent limits |
| Strategy degradation monitor | Every new forward or paper outcome | Pause a strategy when costs, drawdown, regime, data, or mechanism deteriorate |
| Daily Learning Brief | Material evidence delta after the real daily window | Report new evidence, stronger/weaker hypotheses, matured outcomes, rejections, and next test; otherwise remain quiet |
| Strategy-governance audit | Monthly | Summarize automatic admissions, denials, tier changes, and policy integrity; no click required |
| Monthly provider review | Calendar month | Recheck terms, outages, costs, and archive opportunities |

## 16. Risks And Mitigations

| Risk | Mitigation |
| --- | --- |
| Research throughput is mistaken for informational advantage | Six-part information-advantage admission, three focused programmes, and material-state reporting |
| Re-running the same 2,652-family search creates false confidence | Immutable attempt ledger and no-new-evidence skip state |
| More data creates more false positives | Pre-registration, economic mappings, one attempt ledger, false-discovery correction |
| Highest-return backtest wins through selection bias | Pareto robustness frontier, untouched holdout, concentration penalties, and frozen forward tournament |
| Core strategies become confirmation bias | Strategy-agnostic search plus explicit preserve, demote, retire, and no-change outcomes |
| Every pattern becomes a new strategy | Foundry novelty, mechanism, duplicate-exposure, and full-gate requirements |
| A backtest silently rewrites active behavior | Immutable incumbent, versioned challenger, and signed deterministic admission only |
| Public data is already priced in | Test lead time, incremental value, and execution survivability rather than narrative plausibility |
| Revised macro data leaks hindsight | Preserve vintage and initial-release values |
| STOCK Act transaction dates leak private history | Score from public filing availability only |
| Prediction resolutions leak into signals | Separate feature and outcome planes |
| Equivalent sources inflate quorum | Cluster shared events and provider mirrors |
| Unusual Whales becomes a story rather than evidence | Require official history/forward rows and mandatory ablations |
| Intraday data overwhelms the laptop | Admit only shortlisted experiments and enforce hard resource ceilings |
| Quantum methods overfit small samples | Matched classical baselines, identical holdouts, and incremental-value reporting |
| Quantum presentation implies new information | State explicitly that quantum tests structure only and cannot manufacture absent evidence |
| Forward rules are tuned after outcomes | Immutable freeze registry; any change creates a new version and restarts the clock |
| Activity-heavy learning briefs obscure negative results | Material-delta gate, five-part learning contract, and quiet no-change state |
| Historical confidence expands paper risk | Historical results enter at `R0` or `R1`; only real independent paper outcomes can move one pre-authorized tier |
| Backtest results bypass current tradeability | Mandatory frozen forward evidence, Akber, portfolio risk, Router, and PaperOps |
| Autonomous governance becomes self-authorizing | Immutable signed policy, Python-only signatures, policy hash checks, and no self-edit authority |
| A winning strategy grows without bound | Hard US$5,000 per-trade ceiling plus lower portfolio, liquidity, drawdown, correlation, and daily-loss limits |
| Forward-only evidence is backfilled artificially | Real-time maturity ledger and simulated-time prohibition |
| Dashboard implies all sources were tested | Separate source count, acquired count, scored count, tested count, and validated count |
| Backtesting interferes with paper operation | Separate locks, bounded workers, non-interference checks, and paper-epoch hash audit |

## 17. Final Acceptance Criteria

The plan is complete only when:

1. All 41 sources and 19 instruments have one canonical empirical role and
   closure state.
2. Generic missing count is zero.
3. Every currently acquired dataset is scoreable, assigned to a non-predictive
   plane, or explicitly excluded.
4. BIS, BLS, ECB, and UCDP have point-in-time-safe feature manifests and
   completed ablations.
5. STOCK Act transaction documents are parsed to the maximum approved extent,
   with all residual failures typed and no fake exact values.
6. Kalshi signal and direct-instrument eligibility are independently audited.
7. Polymarket signal and direct-instrument eligibility are independently
   audited.
8. Unusual Whales has an official historical feature plane or an active honest
   forward-only maturity state.
9. Priority public archives are acquired, formally blocked, or deliberately
   excluded with current reasons.
10. Every retained forward-only source has an active capture or exact operator
    blocker.
11. Intraday/microstructure data is limited to admitted experiments.
12. All normalized evidence has provider, event, publication, availability,
    retrieval, parser, and hash lineage.
13. Leakage violations are zero.
14. Score tape hashes are deterministic and written before labels.
15. Every missing forward outcome has a typed reason.
16. Every eligible experiment is pre-registered and terminally classified.
17. Costs, spreads, slippage, liquidity, roll cost, and proxy basis risk are
    included where relevant.
18. Multiple-testing and negative-control audits pass without promoting a
    control.
19. Nonlinear and quantum-assisted results use matched classical evidence and
    holdouts.
20. Any historical candidate remains separate from a validated edge and paper
    execution.
21. Learning outputs remain proposals until the signed Autonomous Strategy
    Governor or an explicit operator decision admits the exact version.
22. Dashboard and Telegram report honest denominators and material changes.
23. The US$100,000 paper epoch remains unchanged through QBC-15; any QBC-16
    difference reconciles exactly to eligible real-time PaperOps canary
    receipts.
24. QBC-0 through QBC-15 create zero broker writes or paper orders. QBC-16 uses
    only guarded Alpaca Paper, historical evidence gets zero proof credit, and
    live-capital changes remain zero.
25. `scripts/check_qadam_backtest_completion.py` passes with an honest no-edge,
    forward-maturing, strategy-proposal, paper-canary-eligible, or guarded-
    paper-canary-operating state without requiring a trade.
26. Every new experiment has a frozen six-part information-advantage
    assessment before consuming a holdout or quantum run.
27. Prediction-market disagreement, STOCK Act sector repricing, and Unusual
    Whales macro confirmation exist as the three immutable first-version
    focused programme contracts.
28. Focused and challenger research budgets are separately measured and the
    initial 80/20 capacity boundary cannot be bypassed silently.
29. The attempt ledger contains the prior 2,652 hypotheses and every later
    version, including negative and insufficient results.
30. Experiment results report independent event clusters, power or detectable
    effect, net-of-cost performance, and concentration rather than raw row
    count alone.
31. A historical survivor enters a frozen 60-90 market-day forward protocol
    and cannot pass on elapsed time without the required independent events.
32. Any post-freeze rule change creates a new version and restarts forward
    observation.
33. Quantum-assisted results have identical evidence, labels, folds, costs,
    and holdouts to a completed classical comparator.
34. The Daily Learning Brief answers what evidence arrived, what strengthened
    or weakened, what matured, what was rejected, and what is tested next.
35. No-material-change produces a quiet state with no duplicate Telegram send.
36. Positive net-of-cost holdout evidence, forward shadow, Akber review,
    portfolio-risk approval, Router eligibility, and PaperOps checks remain
    mandatory before any paper promotion.
37. Trade quotas, forced candidates, and forced promotions are absent.
38. Every one of the five core strategy families has an application record for
    every eligible recommended method and a typed reason for every ineligible
    method.
39. Every terminal backtest result has exactly one strategy-impact state.
40. Core-strategy changes exist as incumbent-versus-challenger versioned
    proposals and activate only through a signed admission decision.
41. A new strategy is created only as a provisional emerging strategy with a
    distinct mechanism, non-duplicate exposure, full lineage, and the same
    historical and forward requirements as a core challenger.
42. Forward tournament selection uses a reproducible robustness frontier and
    portfolio correlation constraints rather than the highest historical
    return.
43. There is no direct backtest-to-order path.
44. A paper strategy may advance only one `R0`-to-`R4` tier at a time and can
    never exceed any strategy, portfolio, or operator parent limit.
45. If no setup passes every gate, the paper account remains in cash without
    degrading certification.
46. When no strategy survives, a value-of-information queue identifies the
    next research question rather than generating unbounded variants.
47. A qualifying core refinement or emerging strategy is admitted for paper use
    automatically without a user click.
48. The initial autonomous risk ladder reconciles to the US$100,000 paper
    account and US$5,000 absolute per-trade ceiling before activation.
49. Every automatic admission, tier promotion, downgrade, pause, and retirement
    is deterministic, signed, policy-versioned, reproducible, and visible.
50. Gemma, Gemini, nonlinear models, and quantum review cannot sign strategy
    admission or risk expansion.
51. Risk promotion depends on independent closed paper outcomes and cannot be
    earned by historical or shadow performance alone.
52. Adverse evidence triggers automatic downgrade or pause faster than positive
    evidence can trigger promotion.
53. Qadam requests operator action only for provider/secrets work or an outer
    constitutional boundary change, not routine strategy admission, tier
    progression, or individual paper orders.

## 18. Modular Implementation Order

The recommended operator prompts should implement one phase at a time:

1. QBC-0 and QBC-1 together: freeze the negative baseline, classify every
   source, and register the three focused information-advantage programmes.
2. QBC-2: use already-acquired data.
3. QBC-3: STOCK Act transaction detail.
4. QBC-4 and QBC-5: prediction-market completion.
5. QBC-6: Unusual Whales historical/forward plane.
6. QBC-7: priority public archives.
7. QBC-8: forward-only capture.
8. QBC-9: selective microstructure only after admission.
9. QBC-10 and QBC-11: rebuild evidence and scores.
10. QBC-12: focused-programme backtests first, then bounded whole-universe
    challengers.
11. QBC-13: nonlinear and quantum incremental value.
12. QBC-14: translate every result into a core-strategy consequence or
    provisional emerging-strategy decision.
13. QBC-15: run the frozen forward strategy tournament through real market
    time and automatically admit qualifying strategy versions under the signed
    policy.
14. QBC-16: conditionally enable guarded paper canaries and automatic `R0` to
    `R4` risk progression for current setups that clear every independent gate.
15. QBC-17: automate strategy translation, visibility, material learning, and
    degradation monitoring.
16. QBC-18: certify the actual no-edge, maturing, proposal, or guarded-canary
    state.

Later phases must not be implemented early merely to produce visible results.
Provider-dependent phases may pause honestly for operator action while other
independent lanes continue. QBC-17 implementation may proceed while QBC-15 is
maturing, but QBC-16 cannot submit anything until the real forward criteria are
met.

## 19. What Success Looks Like

After implementation, Qadam can truthfully say:

> Qadam used every approved historical dataset that was economically relevant
> and technically scoreable, converted previously unused macro and conflict
> archives into point-in-time evidence, expanded priority provider histories,
> and started real forward capture where no trustworthy archive existed. It
> treated the prior 2,652 tests and zero survivors as a useful negative result,
> then concentrated research on prediction-market disagreement, STOCK Act
> disclosure repricing, and Unusual Whales confirmation. Every eligible
> relationship stated its information claim and economic mechanism before it
> was tested against costs, simple baselines, negative controls, untouched
> holdouts, and matched nonlinear or quantum-assisted alternatives. Historical
> occurrence, vector analog, state-matrix, entropy, nonlinear, quantum-
> challenge, and flow-confirmation methods were applied to each eligible core
> strategy. Every result either preserved, refined, demoted, or rejected a core
> rule, proposed a genuinely distinct emerging strategy, or explicitly changed
> nothing. Unavailable history remained visible. Historical survivors entered
> a frozen 60-90 market-day strategy tournament and were selected for robustness
> and diversification rather than headline return. The signed Autonomous
> Strategy Governor admitted qualifying paper strategies without a user click.
> Only a current setup that later passed Akber, adaptive portfolio risk, Router,
> and PaperOps could begin a guarded paper canary; otherwise the account remained
> in cash. Real closed paper outcomes then moved the strategy up, down, or out of
> the pre-authorized `R0`-to-`R4` risk ladder without exceeding US$5,000 per
> trade or any lower portfolio limit.

That is a completed backtest programme. Finding an edge remains an empirical
outcome, not an implementation acceptance criterion. If all three focused
programmes fail, Qadam must preserve that result and change the research
question rather than force a trade. If a strategy survives, the intelligent
next step is a small observable paper experiment inside existing limits, not a
large allocation or live-capital leap. Routine paper admission and tier changes
are autonomous; only a constitutional boundary change returns to the operator.
