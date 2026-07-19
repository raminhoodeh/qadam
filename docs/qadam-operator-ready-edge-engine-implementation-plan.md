# Qadam Operator-Ready Edge Engine Implementation Plan

Date: 2026-07-17

Status: Active operational re-entry and empirical edge-validation plan

Revision: `2.0-operational-reentry`

Experimental paper-operation successor:
`docs/qadam-autonomous-experimental-paper-epoch-implementation-plan.md`. That
plan permits a clean, bounded experimental paper epoch before edge validation;
this document remains authoritative for empirical edge validation, strategy
promotion, and all later live-capital evidence requirements.

Parent control document: `docs/qadam-master-implementation-plan.md`

Supporting predecessors:

- `docs/qadam-next-generation-flow-implementation-plan.md`
- `docs/qadam-whole-universe-historical-backfill-backtest-implementation-plan.md`
- `docs/qadam-trading-edge-realization-plan.md`
- `docs/qadam-qsase-implementation-plan.md`
- `docs/qadam-paper-operational-mode-plan.md`

## Dynamic Plan Status

The block below is the only part of this document that the implemented DP-0
mechanism may update automatically. This revision records an explicitly
reviewed manual rebaseline; later machine updates remain evidence-bound.

<!-- QADAM_OPERATOR_READY_DYNAMIC_STATUS_START -->

| Field | Current Value |
| --- | --- |
| Plan version | `2.0-operational-reentry` |
| Plan state | `wave_e_evidence_maturing` |
| Current stage | `OR-13` |
| Current stage state | `evidence_maturing` |
| Wave 0 phases passed | `8_of_8` |
| Last plan evidence refresh | `2026-07-18T09:55:23.497757+00:00` |
| Latest operator-ready certification | `evidence_maturing` |
| Current execution state | `paperops_watch_only_research_lock_active` |
| Current dashboard contract | `ten_stage_lifecycle_v4_13_routes` |
| Next required action | `implement_or_repair_or-13` |
| Research lock active | `True` |
| Live capital | `disabled` |
| Automatic normative plan edits | `forbidden` |

<!-- QADAM_OPERATOR_READY_DYNAMIC_STATUS_END -->

DP-0 may refresh only the delimited status block from validated machine-readable
phase evidence. It may not silently change the purpose, safety boundaries,
phase order, acceptance gates, trading authority, risk policy, or completion
definition in the normative body of this plan.

## 0. 2026-07-17 Operational Re-entry Amendment

This revision starts from the system that exists now. It does not ask future
implementation work to rebuild phases whose modules and safety checkers already
exist. It separates three states that earlier revisions could blur:

1. **implemented** - code, contracts, fixtures, checkers, and dashboard readers
   exist;
2. **operating** - the real provider, supervisor, scoring, shadow, and PaperOps
   jobs are running with fresh heartbeats;
3. **empirically validated** - provider-backed observations, labels, backtests,
   forward-shadow outcomes, and attributable paper outcomes satisfy frozen
   promotion policies.

The current codebase is substantially implemented but is not yet operating or
empirically validated end to end. An implementation prompt for this plan must
therefore inspect and extend current modules rather than replacing them with a
second parallel stack.

### 0.1 Current Critical Path

```text
truthful connection state
-> provider coverage and licensing matrix
-> small provider-backed acquisition pilot
-> OR-3 whole-universe historical acquisition
-> OR-4 point-in-time alignment
-> OR-5/OR-6 frozen historical scores
-> OR-7 labels
-> OR-8 walk-forward backtest
-> OR-9 nonlinear and quantum incremental-value review
-> OR-10 validated edge registry
-> OR-11 strategy formation
-> OR-12 Akber tradeability review
-> OR-13 real forward shadow
-> OR-14 portfolio risk
-> OR-15 guarded PaperOps handoff
-> OR-16 attributable paper lifecycle
-> OR-18 continuously running operator service
-> OR-19 certification and supervised paper-operation release
```

### 0.2 Immediate Re-entry Blockers

The 2026-07-17 certification snapshot records the following empirical and
operational blockers:

| Blocker | Current Evidence | Required Resolution |
| --- | --- | --- |
| Historical provider acquisition | `0 / 450` partitions and `0` provider rows | Pass OR-2R, then run resumable OR-3 acquisition |
| Forward-window coverage | `82 / 6,232` complete; `6,150` missing | Acquire price/source history and classify every impossible window honestly |
| Empirical score tape | `0` provider-backed rows | Run OR-4 through OR-6 only after provider data exists |
| Forward labels and backtest | `0` labels, folds, and negative controls | Run OR-7 and OR-8 with frozen point-in-time inputs |
| Validated edges | `0` | Promote only evidence passing the frozen statistical policy |
| Akber contribution | `0` replays and ablations | Complete historical Akber evaluation in OR-12 |
| Forward shadow | `0` real outcomes and `0` real elapsed days | Run the service over real future market time |
| Operator service | Not installed or running; heartbeat stale | Make OR-18 execute due jobs, install explicitly, and pass soak testing |
| Runtime freshness | `10` monitored artifacts stale or missing | Repair producers and freshness contracts, not dashboard wording |
| Dashboard certification drift | Current dashboard has `13` protected routes; old final checker still expects `19`, and the lifecycle checker expects obsolete `Filter Tradeability` copy instead of `Akber's 6-Stage Filter` | Update OR-17 and OR-19 to the V4 route and canonical lifecycle-copy contract |
| TradingView supplemental context | Live calls disabled; required libraries absent; sample records presented as connected | Pass the new OR-2R truth and dependency gate; do not buy a plan merely to satisfy it |

Counts are a dated baseline and must be refreshed by checkers when
implementation begins. They are not permanent product claims.

### 0.3 What “Autonomously Trading” Means In This Plan

Qadam may autonomously submit **paper orders only** after a strategy version,
portfolio-risk policy, and research-lock release have been explicitly approved
and each individual setup passes fresh evidence, Akber, shadow, risk, Router,
idempotency, duplicate-exposure, drawdown, Q-CTRL, and guarded PaperOps checks.

Autonomy does not mean continuous activity, forced trades, silent policy
changes, or live-capital authority. A correct autonomous decision may be to
wait. Live-capital activation, regulated distribution, and customer deployment
require a separate future program after paper performance is proven.

## 1. Purpose

This plan turns Qadam from a safe, richly instrumented research and PaperOps
control plane into an operator-ready, evidence-compounding paper fund that can:

1. stay running unattended on the operator's laptop;
2. keep its source and market data current;
3. generate point-in-time pattern scores across the data and trading universes;
4. test those scores against outcomes without lookahead leakage;
5. distinguish interesting patterns from statistically supported edges;
6. map supported edges into Qadam's core trading strategies or propose an
   emerging strategy when the evidence does not fit the core five;
7. decide whether an edge is tradeable now through Akber's filter;
8. validate decisions in forward shadow mode;
9. route only clean setups into guarded Alpaca Paper execution;
10. attribute real closed paper outcomes back to every contributing component;
11. improve through versioned, reviewable proposals rather than silent mutation;
12. explain the complete state plainly through the public-safe dashboard and
    short Telegram notes.
13. run the resulting research-to-paper loop continuously, with safe pause,
    resume, retry, repair escalation, and one current reason for acting or
    waiting.

This is not a promise of profit. It is the implementation path most likely to
give Qadam a defensible chance of finding positive-expectancy edges, protecting
capital when no edge exists, and measuring whether its paper returns are
actually attributable to its own decisions.

The end state remains paper-only. Live-capital activation is outside this plan.

## 2. Why A New Gap-Closure Plan Is Required

The earlier plans successfully created the architecture, schemas, safety
boundaries, dashboards, and phase artifacts. They did not yet create the full
provider-backed historical evidence or continuously running operating loop
required to validate and trade an edge.

The current implementation contains an especially important distinction:

- `orchestrator/qsase_whole_universe_backfill_backtest.py` builds a baseline
  from existing local runtime artifacts.
- Its runner defaults to network-disabled operation with zero provider calls.
- Its manifest contains six coarse artifact-building jobs, not provider/date/
  instrument acquisition batches.
- `orchestrator/historical_backfill.py` explicitly remains a sample-contract
  runner rather than a true provider historical pull.

Therefore, the existing baseline proves that contracts and guards work. It does
not prove that the historical universe has been acquired or that any score has
predictive power.

This plan preserves the implemented modules and replaces the missing execution
substrate beneath them.

## 3. Current Verified Baseline

The latest checked runtime snapshot, generated on 2026-07-17, reports:

| Area | Current State | Meaning |
| --- | --- | --- |
| Operator-ready certification | `blocked_evidence_maturing` with 16 explicit blockers | Safety and most contracts exist; empirical evidence and unattended operation do not. |
| Runtime | Research supervisor and operator service are not running; heartbeat is stale | Qadam is not currently operating as a continuous local fund service. |
| Research lock | Active; PaperOps watch-only | Correct posture while provider-backed research is incomplete. |
| Historical acquisition | `0 / 450` provider partitions complete; `0` provider rows | The existing backfill proves contracts, not real historical coverage. |
| Source readiness | 9 fresh scoring-eligible sources and 9 acquisition repair requests | Some current evidence is usable, but provider/adapter defects remain. |
| Source and market universe | 41 displayed sources across 6 categories; 19 watched instruments | The dashboard universe is broad enough for research, but connection does not imply historical coverage. |
| Historical relationship matrix | 6,232 structural source-price records | The search space exists as a manifest. |
| Complete forward windows | 82 | Only a narrow historical subset currently has an outcome. |
| Missing forward windows | 6,150 | Price/source history and typed unavailability classification remain the largest gap. |
| Typed evidence | 465 gaps; 0 complete eligible score inputs | Downstream systems are correctly failing closed. |
| Pattern engine | Ranked research relationships are visible | These are observations and engineering findings, not validated edges or probabilities. |
| Historical score tape | 0 empirical rows | Qadam has not yet replayed what it would have known at each historical cutoff. |
| Labels and backtest | 0 labels, 0 folds, 0 negative controls | No current claim of repeatable positive expectancy is justified. |
| Edge registry | 0 validated edges | No strategy is eligible for evidence-backed paper release yet. |
| Akber Filter V3 | 0 empirical replays or ablations | Its practical filtering value has not yet been measured historically. |
| Forward shadow | 0 outcomes; 0 real elapsed days | Current market generalization remains untested. |
| Router/PaperOps | Release not recommended; research lock blocks fresh submissions | Execution correctly waits on upstream evidence. |
| Broker mirror and proof | Existing closed broker records are reference-only; 0 Qadam-origin proof trades | Historical mirror activity cannot be claimed as edge proof. |
| TradingView context | Local checkout imports, live calls are disabled, required data libraries are absent, and three fallback sample rows can appear connected | The adapter needs a truth repair; a TradingView plan upgrade is not the remedy. |
| Dashboard | Current V4 structure has 13 routes and a 10-stage lifecycle; portfolio parity passes | The layout is now the protected operator experience. |
| Dashboard certification | Final checker still expects 19 routes and 10 upstream artifacts are stale/missing | Update checker expectations and producer freshness without restructuring the dashboard. |
| Unattended soak | 1 real session; 7 required | Safety probes exist, but leave-it-running reliability is not proven. |

These numbers are a baseline, not permanent product claims. Every phase must
read fresh artifacts and avoid copying stale counts into code or documentation.

## 4. Definition Of The Target Operator Experience

The operator should eventually perform four actions:

1. Keep the laptop powered, connected, and allowed to run the Qadam service.
2. Check one dashboard for health, evidence, portfolio state, and the current
   reason Qadam is trading or waiting.
3. Review strategy, threshold, and source-trust proposals on a scheduled basis.
4. Resolve explicit provider, credential, or code-repair requests when safe
   automation cannot recover.

Everything else should be automated within the paper-only boundary:

```text
source and price refresh
-> point-in-time evidence
-> pattern score
-> historical calibration
-> strategy hypothesis
-> Akber confirmation
-> forward shadow evidence
-> Router decision
-> guarded PaperOps
-> fill/open/close/postmortem
-> learning attribution
-> reviewable improvement proposal
```

Operator-ready does not mean Qadam trades continuously. It means:

- the service runs continuously;
- the data state is current or explicitly degraded;
- the decision state is always explainable;
- a valid setup can traverse the complete guarded paper route;
- an invalid or unsupported setup is stopped for a precise reason;
- no manual intervention is needed merely to keep ordinary cycles alive.

## 5. Success States

The program uses four certification levels so implementation progress is not
confused with investment performance.

### 5.1 Research-Operational

- The supervisor is active and restart-safe.
- Required source and price jobs run on schedule.
- Historical acquisition is resumable.
- Every source and instrument is classified.
- Runtime artifacts are internally consistent and fresh.

### 5.2 Edge-Validated

- Point-in-time score tapes exist.
- Outcome labels are generated separately from scores.
- Leakage, multiple-testing, and walk-forward checks pass.
- At least one edge has positive out-of-sample net expectancy under its frozen
  promotion policy.
- Quantum or nonlinear value is labelled honestly against a classical baseline.

### 5.3 Paper-Operator-Ready

- Akber receives complete current context.
- Forward shadow requirements pass.
- Router and portfolio-risk gates are complete.
- A real fresh setup can reach PaperOps without bypasses.
- The canonical autonomous pass consumes the same V3 handoff that the Router
  certifies; no parallel handoff path exists.
- Lifecycle, reconciliation, exit, and postmortem paths are unambiguous.
- Dashboard and Telegram read from fresh canonical artifacts.

### 5.4 Autonomous-Paper-Operating

- The operator service is installed explicitly and executes due provider,
  scoring, shadow, Router, PaperOps, lifecycle, attribution, and projection jobs
  rather than refreshing status alone.
- Safe interruption and resume behavior has passed the real-session soak gate.
- Clean setups can be submitted without per-order human prompting under the
  approved paper strategy and risk policies.
- Stale, incomplete, ambiguous, or unprofitable-after-cost setups remain held.
- The dashboard always explains the current action or reason for waiting.

### 5.5 Paper-Performance-Proven

- Qadam-origin paper trades close with complete lineage.
- Net P&L, costs, drawdown, calibration, and attribution are measurable.
- The paper proof ledger contains only real closed paper trades.
- Strategy improvements are supported by enough independent outcomes.

No certification level means guaranteed future returns.

## 6. Non-Negotiable Boundaries

Every phase must preserve all of the following:

- `live_capital_enabled=false`.
- No live broker endpoint may be called.
- No live credential may be loaded for execution.
- No secrets or `.env` files may be edited by implementation or automation.
- Alpaca Paper remains the only broker-write route in this plan.
- All paper writes must pass through guarded PaperOps.
- No pattern, backtest, LLM, quantum result, dashboard, Telegram message,
  Strategy Foundry record, Akber pass, or Router decision creates an order.
- Local and frontier LLMs cannot approve risk or execution.
- Quantum and Q-CTRL cannot create trades, approve risk, bypass holds, submit
  broker requests, or grant proof credit.
- Telegram inbound remains read-only and cannot create candidates or authority.
- The dashboard remains read-only and command-disabled.
- Backtests and shadow runs cannot advance the `30-day paper growth trial`.
- Backtests, shadows, fixtures, and mirrored broker records cannot receive paper
  proof ledger credit.
- No forced trades and no trade-count quota.
- Multiple distinct qualified paper setups may be submitted only through the
  same guarded route with distinct lineage, identity, and idempotency.
- Missing evidence fails closed.
- Self-healing may retry known safe refreshes; it may not silently edit code,
  secrets, policy, strategy weights, risk limits, or authority.
- Historical source limitations must be recorded, never fabricated.
- Historical and live data must be obtained through interfaces and licenses
  that permit Qadam's intended research use. Automation cannot accept terms,
  purchase subscriptions, or change subscriber classification.
- TradingView remains optional, supplemental technical context. Its account
  plan, UI replay depth, or exchange display entitlement cannot be presented as
  a provider-backed historical API.
- Sample, fixture, synthetic-control, simulator, delayed, proxy, and live
  provider records must remain visibly distinct in artifacts and the dashboard.
- Real elapsed market time cannot be backfilled or simulated for shadow or paper
  performance certification.
- Live-capital activation and commercial customer operation remain outside this
  plan and require a separately reviewed launch, legal, security, risk, and
  deployment program.

## 7. Architecture Decision

### 7.1 Storage Roles

Qadam should stop using `data/runtime/` as a bulk research warehouse.

| Storage | Role |
| --- | --- |
| Timescale/Postgres | Live and recent durable observations, prices, heartbeats, and replay. |
| `data/raw_payloads/` | Immutable provider responses and acquisition provenance. |
| Partitioned Parquet under an ignored research directory | Historical normalized source events, price bars, feature tapes, and outcome labels. |
| DuckDB or equivalent local analytical layer | Streaming and columnar historical joins and backtests on the laptop. |
| `data/runtime/` JSON/JSONL | Small canonical status, manifests, decisions, summaries, checks, and dashboard contracts. |
| Event Log | Append-only operational lineage and state transitions. |

If DuckDB/Parquet dependencies are not approved, the first implementation may
use chunked JSONL, but interfaces must remain storage-agnostic and streaming.
The 24 GB laptop must never require loading the entire universe into memory.

### 7.2 Compute And Cognition Roles

| Component | Best Use | Must Not Do |
| --- | --- | --- |
| Python COO | Deterministic acquisition, timestamps, joins, feature calculation, scoring, backtesting, risk, scheduling, and broker routing | Invent missing evidence or relax safety gates |
| Local Gemma Research Analyst | Cheap event extraction, entity normalization, topic classification, novelty compression, and qualitative summaries | Calculate final returns, approve risk, or submit orders |
| Frontier Gemini Strategy Lead | Sparse challenge, alternative explanations, causal critique, scenario review, and difficult synthesis | Process every historical row, become numerical ground truth, or hold broker credentials |
| Head of Quant | Nonlinear interaction review, entropy/regime ambiguity, classical comparison, and bounded quantum experiments | Claim quantum advantage without comparison or create execution authority |
| Risk/PaperOps | Deterministic portfolio controls, idempotency, broker paper submission, lifecycle, and reconciliation | Accept research artifacts as execution approval |
| Human operator | Risk-policy ownership, provider repair, proposal approval, strategy promotion/demotion, and later live-capital decisions | Force a trade merely because the system is quiet |

Qadam's self-awareness is operational, not sentient. Each decision records:

- which component produced it;
- model/provider version;
- latency and cost;
- source freshness and coverage;
- fallback state;
- confidence class;
- known limitations;
- permitted downstream uses.

### 7.3 Three Separate Search Tracks

Qadam must run three distinct research tracks:

1. **Strategy-informed search:** tests relationships relevant to the five core
   strategies.
2. **Strategy-agnostic discovery:** searches valid relationships across the
   entire source and trading universes without forcing a strategy label.
3. **Negative-control search:** tests shuffled timestamps, irrelevant markets,
   placebo events, and delayed features to estimate false discoveries.

This prevents the five known strategies from becoming confirmation bias while
also preventing unconstrained pattern mining from manufacturing significance.

## 8. Core Trading Strategies Preserved

The plan uses the existing five strategy families as hypotheses to test, not
truths to assume.

| Strategy | Primary Question | Example Instruments | Main Evidence Families |
| --- | --- | --- | --- |
| Crude Oil Energy Security Disruption | Do conflict, maritime, chokepoint, fire, or supply signals lead energy repricing? | `CL=F` for research context; `USO`, `BNO`, `XLE` where paperable | Conflict, AIS/maritime, FIRMS, macro, news, price/volume |
| Defence Geopolitical Repricing | Does escalation, policy, procurement, or conflict intensity lead defence repricing? | `ITA`, `XAR`, `LMT`, `PPA` | Conflict, policy, filings, procurement, patents, news |
| Prediction Market Geopolitical Dislocation | Do event probabilities diverge materially from corroborated evidence or related prices? | Kalshi/Polymarket contracts as context until a governed paper route exists | Prediction markets, conflict, news, Telegram, macro |
| Semiconductor Policy Asymmetry | Do export controls, industrial policy, filings, patents, or supply constraints create asymmetric repricing? | `SMH`, `SOXX`, `NVDA`, `QQQ` | Filings, policy, patents, Capitol trades, macro, news, price/volume |
| Silver Macro Liquidity Stress | Do liquidity, inflation, rates, commodity, or stress regimes create repeatable silver opportunities? | `SLV`, `SIL`; `SI=F`, `GLD`, `SPY` as context where appropriate | FRED, ECB, BIS, trade, commodity, volatility, flow |

The full-universe research process may propose a new strategy family only when:

- the relationship is not adequately represented by an existing family;
- it survives the same statistical and shadow gates;
- Strategy Foundry records a falsifiable mechanism and invalidation;
- the proposal remains inactive until reviewed;
- no authority or risk setting changes automatically.

## 9. The Score And Decision Ladder

Qadam must not collapse every question into one number.

```text
raw pattern score
-> strategy-fit vector
-> backtested edge score
-> Akber tradeability state
-> portfolio/risk state
-> Router final state
-> PaperOps decision
```

### 9.1 Raw Pattern Score

Question: Is there a meaningful, unusual, point-in-time source/market pattern?

Candidate components:

- source signal intensity;
- novelty versus recent history;
- independent-source quorum;
- source trust and freshness;
- source-price divergence;
- source-before-price lag fit;
- historical analog similarity;
- cross-source confirmation;
- cross-asset confirmation;
- regime fit;
- nonlinear interaction strength;
- entropy or path-dependence state;
- explicit missing-data and reliability penalties.

The score is computed only from information available at `scoring_as_of`.
It is not initially a probability and it is not a trade recommendation.

Recommended contract:

```json
{
  "score_id": "...",
  "scoring_as_of": "...",
  "source_packet_id": "...",
  "instrument": "USO",
  "direction_hypothesis": "up",
  "horizon": "3d",
  "feature_vector_version": "...",
  "feature_components": {},
  "raw_pattern_score": 0.45,
  "data_quality_score": 0.79,
  "missing_feature_ids": [],
  "strategy_fit_scores": {},
  "model_versions": {},
  "lookahead_safe": true,
  "research_only": true
}
```

### 9.2 Strategy-Fit Vector

Question: Which existing strategy, if any, best explains how the pattern could
be traded?

The output is a vector, not a forced single label. A pattern may fit more than
one family or remain `unmapped_discovery`.

### 9.3 Backtested Edge Score

Question: Did comparable point-in-time scores predict net returns reliably?

The edge score must incorporate:

- out-of-sample net expectancy;
- confidence interval or block-bootstrap distribution;
- independent sample sufficiency;
- hit rate and payoff asymmetry;
- maximum adverse excursion and drawdown;
- turnover, spread, slippage, and fees;
- stability across time and regimes;
- source and instrument concentration;
- false-discovery-adjusted significance;
- score calibration and monotonicity;
- decay since the most recent supporting sample;
- reproducibility across reruns.

### 9.4 Akber Tradeability State

Question: Even if the pattern has historical edge, is it tradeable now?

Akber preserves the six-stage plain-English method:

1. context;
2. catalyst;
3. confirmation;
4. risk;
5. execution;
6. postmortem learning.

Akber must expose every stage separately. A high aggregate score cannot hide a
failed critical stage.

### 9.5 Router And PaperOps

Router assigns one final research state. PaperOps independently decides whether
the complete paper-only execution chain passes. Neither inherits authority from
the score above it.

## 10. Statistical Research Protocol

The protocol must be frozen and versioned before each confirmatory run.

### 10.1 Point-In-Time Rules

Every observation must distinguish:

- `event_time`: when the external event occurred;
- `published_at`: when the provider published it;
- `available_at`: earliest time Qadam could have read it;
- `ingested_at`: when Qadam stored it;
- `revised_at`: later revision time, if any;
- `scoring_as_of`: the decision cutoff;
- `label_window_start` and `label_window_end`.

Only records with `available_at <= scoring_as_of` may enter features.
Revised macro data must use the vintage available at the historical cutoff.

### 10.2 Data Splits

- Chronological train, validation, and untouched holdout segments.
- Walk-forward evaluation rather than random row splitting.
- Purging around overlapping labels.
- Embargo between train and validation windows where leakage is possible.
- Nested tuning so threshold selection never sees the final holdout.
- Regime slices defined before outcome inspection.

### 10.3 Multiple Testing

The system must maintain a hypothesis/test registry containing every attempted
source, instrument, horizon, transformation, and model. It must apply false
discovery controls by research family and record rejected tests.

Exploratory significance cannot be relabelled as confirmatory evidence without
a new untouched period.

### 10.4 Costs And Tradability

All edge claims must report both gross and net results. The cost model includes:

- bid/ask spread;
- commission or venue fees where relevant;
- slippage by liquidity and volatility regime;
- delayed entry after signal availability;
- market-hours constraints;
- instrument-specific price increments;
- futures roll or proxy mismatch where relevant;
- rejected or unfilled order assumptions.

### 10.5 Promotion Classes

Recommended initial classes, subject to a frozen power-analysis policy:

| Class | Meaning | Execution Consequence |
| --- | --- | --- |
| `interesting_pattern` | Point-in-time relationship worth studying | Research only |
| `replicated_pattern` | Repeats across independent samples | Research only |
| `shadow_edge_candidate` | Positive out-of-sample evidence after costs, with acceptable false-discovery state | Forward shadow only |
| `paper_review_edge` | Historical and real-time shadow evidence agree within policy | Eligible for Strategy Foundry and Akber; still no order |
| `paper_validated_edge` | Sufficient Qadam-origin closed paper outcomes support it | May receive greater paper allocation by reviewed proposal |
| `degraded_or_retired_edge` | Edge decayed, drifted, concentrated, or failed controls | No new paper setups |

There must be no universal magic sample count. Sparse macro event strategies and
high-frequency price features have different dependence structures. The phase
implementing promotion policy must use power analysis, effective independent
sample size, and block bootstrap rather than raw row count alone.

### 10.6 Return Objective And Constraints

Qadam must optimize the economic objective the operator actually cares about,
not an attractive proxy metric.

Primary objective:

```text
maximize expected net geometric paper-portfolio growth
subject to drawdown, tail-loss, liquidity, concentration, uncertainty,
and operational-reliability constraints
```

Required evaluation measures include:

- net expectancy per trade and per unit of risk;
- geometric growth rather than arithmetic return alone;
- drawdown depth and recovery duration;
- downside deviation and tail loss;
- payoff ratio and profit factor;
- exposure-adjusted and turnover-adjusted return;
- calibration by raw-score and edge-score bucket;
- Brier/log-loss style diagnostics where probabilistic forecasts exist;
- strategy, source, instrument, and regime concentration;
- opportunity cost from holds and vetoes;
- sensitivity to spread, slippage, delayed entry, and missed fills.

Win rate, trade count, gross return, and in-sample Sharpe must never be treated
as sufficient evidence alone. Promotion thresholds are defined and frozen in
OR-8 before the untouched holdout is evaluated.

## 11. Dependency Graph

```text
RF-0 Refactor and dashboard baseline capture
  -> DP-0 Dynamic plan governance
    -> RF-1 No-change architecture and dependency audit
      -> RF-2 Characterization and safety regression harness
        -> RF-3 Canonical contracts and artifact ownership
          -> RF-4 Provider, storage, and research boundary refactor
            -> RF-5 Decision, risk, and execution boundary refactor
              -> RF-6 Legacy quarantine and post-refactor rebaseline
                -> OR-0 Canonical truth and safety baseline
                  -> OR-1 Research runtime supervisor and atomic state
                    -> OR-2 Source freshness and provider capability
                      -> OR-2R Connection truth and acquisition readiness
                        -> OR-3 Provider-backed historical data lake
                        -> OR-4 Point-in-time alignment and evidence completion
                          -> OR-5 Pattern Score V3
                            -> OR-6 Historical score tape
                              -> OR-7 Forward outcome labels and cost model
                                -> OR-8 Whole-universe statistical backtest
                                  -> OR-9 Nonlinear and quantum incremental-value lab
                                    -> OR-10 Edge registry and strategy evidence map
                                      -> OR-11 Strategy Foundry V3
                                        -> OR-12 Akber Filter V3
                                          -> OR-13 Continuous forward shadow validation
                                            -> OR-14 Portfolio construction and risk
                                              -> OR-15 Router and guarded PaperOps release
                                                -> OR-16 Lifecycle, proof, and attribution
                                                  -> OR-17 Operator dashboard and Telegram
                                                    -> OR-18 Unattended self-healing operations
                                                      -> OR-19 Final certification and trial resume
```

DP-0 remains active across every later phase. Each phase checker updates the
machine-readable plan state and generated status block, or emits a proposed
normative amendment when reality invalidates part of the plan.

OR-17 dashboard work may begin against fixtures after OR-5, but it cannot be
accepted until it renders fresh OR-16 lineage and OR-18 liveness state.

OR-13 and OR-19 contain real-elapsed-time gates. Code completion alone cannot
mark them evidence-complete.

## 12. Phase Summary

| Phase | Outcome | Primary Gate |
| --- | --- | --- |
| RF-0 | Refactor and rendered-dashboard baseline | Root/nested worktrees, behavior, routes, artifacts, and safety state captured |
| DP-0 | Controlled dynamic plan | Status self-updates; normative edits remain proposed and reviewed |
| RF-1 | Complete architecture and ownership map | Every edge-path module and artifact classified without code changes |
| RF-2 | Characterization harness | Existing PaperOps, safety, dashboard, and runtime behavior frozen in tests |
| RF-3 | Canonical contracts and artifact ownership | One canonical owner per domain record and status artifact |
| RF-4 | Clean data/research boundaries | Providers, storage, features, scores, labels, and backtests are separable |
| RF-5 | Clean decision/execution boundaries | Strategy, Akber, Router, risk, and PaperOps remain behaviorally equivalent and isolated |
| RF-6 | Post-refactor certified baseline | Legacy paths quarantined, consumers migrated, plan rebaselined |
| OR-0 | One canonical truth and safety contract | No control-document or runtime contradiction |
| OR-1 | Resumable supervised research service | One active process, fresh heartbeat, atomic state |
| OR-2 | Freshness and provider-history registry | Required sources fresh or explicitly quarantined |
| OR-2R | Connection truth and OR-3 acquisition readiness | Supplemental adapters are honest; 19-instrument and source-history provider matrix plus pilot pass |
| OR-3 | Real historical source and price lake | Provider/date jobs acquire and validate data |
| OR-4 | Point-in-time evidence substrate | No lookahead; missing evidence typed |
| OR-5 | Explainable Pattern Score V3 | Score generated before labels and without future data |
| OR-6 | Historical score tape | Every eligible decision point scored reproducibly |
| OR-7 | Outcome and cost labels | Gross/net outcomes remain separate from scoring |
| OR-8 | Statistical whole-universe backtest | Walk-forward, holdout, and false-discovery checks pass |
| OR-9 | Honest nonlinear/quantum attribution | Incremental value measured against classical baseline |
| OR-10 | Validated edge and strategy registry | Registry is honest; Edge-Validated status requires at least one qualifying edge |
| OR-11 | Trade-shaped hypotheses | Edge-to-hypothesis lineage complete |
| OR-12 | Complete Akber context | No Router-eligible setup has missing critical context |
| OR-13 | Real-time shadow proof | Shadow performance observed over real elapsed time |
| OR-14 | Portfolio-aware risk | Position and portfolio loss bounded deterministically |
| OR-15 | Safe paper route restored | Only clean paper-review candidates reach PaperOps |
| OR-16 | Attributable closed outcomes | Qadam-origin trades distinguished from broker mirror records |
| OR-17 | Operator control plane | Fresh, plain-English, non-authoritative dashboard and notes |
| OR-18 | Leave-it-running operation | Restart, retry, outage, and repair handling pass soak tests |
| OR-19 | Final operator-ready certification | Research, edge, operations, and paper boundaries all pass |

### 12.1 Required Phase Checkers

Each phase owns one narrow checker in addition to the final certification:

| Phase | Required Checker |
| --- | --- |
| RF-0 | `scripts/check_qadam_refactor_baseline.py` |
| DP-0 | `scripts/check_qadam_dynamic_plan.py` |
| RF-1 | `scripts/check_qadam_architecture_audit.py` |
| RF-2 | `scripts/check_qadam_characterization_harness.py` |
| RF-3 | `scripts/check_qadam_canonical_contracts.py` |
| RF-4 | `scripts/check_qadam_research_boundaries.py` |
| RF-5 | `scripts/check_qadam_decision_execution_boundaries.py` |
| RF-6 | `scripts/check_qadam_post_refactor_baseline.py` |
| OR-0 | `scripts/check_qadam_operator_ready_baseline.py` |
| OR-1 | `scripts/check_qadam_research_supervisor.py` |
| OR-2 | `scripts/check_qadam_source_provider_capabilities.py` |
| OR-2R | `scripts/check_qadam_or3_acquisition_readiness.py` |
| OR-3 | `scripts/check_qadam_provider_backfill.py` |
| OR-4 | `scripts/check_qadam_point_in_time_evidence.py` |
| OR-5 | `scripts/check_qadam_pattern_score_v3.py` |
| OR-6 | `scripts/check_qadam_pattern_score_tape.py` |
| OR-7 | `scripts/check_qadam_forward_labels.py` |
| OR-8 | `scripts/check_qadam_statistical_backtest.py` |
| OR-9 | `scripts/check_qadam_nonlinear_quantum_value.py` |
| OR-10 | `scripts/check_qadam_edge_registry.py` |
| OR-11 | `scripts/check_qadam_strategy_foundry_v3.py` |
| OR-12 | `scripts/check_qadam_akber_filter_v3.py` |
| OR-13 | `scripts/check_qadam_forward_shadow.py` |
| OR-14 | `scripts/check_qadam_portfolio_risk_engine.py` |
| OR-15 | `scripts/check_qadam_router_v3_paperops.py` |
| OR-16 | `scripts/check_qadam_paper_lineage_and_proof.py` |
| OR-17 | `scripts/check_qadam_operator_dashboard.py` |
| OR-18 | `scripts/check_qadam_operator_service.py` |
| OR-19 | `scripts/check_qadam_operator_ready_edge_engine.py` |

RF-0 must also create:

- `data/runtime/qadam_operator_ready_phase_status.json` as the durable phase
  status contract;
- `docs/qadam-operator-ready-edge-engine-implementation-log.md` as the
  append-only implementation evidence log.

Every later phase updates those two contracts only after its own checker and
required negative safety probes pass.

## 12.2 Pre-OR Refactor And Dynamic-Plan Program

The edge-engine program starts with a constrained refactor, not a broad rewrite.
The purpose is to make the edge path understandable, testable, and replaceable
without changing Qadam's current paper-only behavior. Audit and characterization
come before structural edits. Safety boundaries remain duplicated at critical
trust boundaries even after shared contracts are introduced.

OR-0 may not start until RF-0 through RF-6 pass and DP-0 records the accepted
post-refactor baseline. A passing refactor phase proves behavioral equivalence
and clearer ownership; it does not prove that an edge exists.

### RF-0 - Refactor And Dashboard Behavior Baseline

#### Objective

Capture the exact pre-refactor code, runtime, safety, and rendered-dashboard
behavior so later phases can prove what changed and what did not.

#### Build

- Add `orchestrator/qadam_refactor_baseline.py`.
- Add `scripts/check_qadam_refactor_baseline.py`.
- Record root and nested-repository commits and dirty-file inventories without
  cleaning, reverting, committing, or normalizing unrelated work.
- Record active processes, schedulers, research locks, PaperOps mode, broker
  route flags, proof boundaries, certification state, and current canonical
  runtime artifact freshness.
- Capture the current dashboard route matrix from the renderer rather than
  retyping it into a second source of truth.
- Inventory every dashboard navigation checker and record whether it targets
  the current routed contract or a superseded hash/five-view contract.
- Capture desktop and mobile behavioral baselines for:
  - default `fund/portfolio` landing route;
  - sidebar and mobile section navigation;
  - direct query-string routes;
  - route persistence during the 15-second status refresh;
  - previous/next decision-journey links;
  - portfolio value parity;
  - read-only controls and absence of command authority.
- Classify every proposed refactor target as edge-path, safety-critical,
  compatibility-only, generated runtime, dashboard renderer, or out of scope.

#### Runtime Artifacts

- `data/runtime/qadam_refactor_baseline.json`
- `data/runtime/qadam_dashboard_navigation_contract.json`
- `data/runtime/qadam_refactor_scope.json`
- `data/runtime/qadam_refactor_baseline_checks.json`
- `data/runtime/qadam_operator_ready_phase_status.json`

#### Acceptance

- No runtime, PaperOps, provider, dashboard, or trading behavior changes.
- No unrelated dirty worktree change is modified or claimed.
- The complete dashboard route/view contract is machine-readable and checked.
- All live-capital, broker-route, proof, Telegram, and calendar safety probes
  remain fail-closed.
- The baseline is fresh enough to compare with RF-6.

### DP-0 - Controlled Dynamic Plan Governance

#### Objective

Make this a living implementation plan that reports current evidence and plan
drift automatically without letting automation rewrite its own mandate.

#### Build

- Add `orchestrator/qadam_dynamic_plan.py`.
- Add `scripts/update_qadam_operator_ready_plan.py`.
- Add `scripts/check_qadam_dynamic_plan.py`.
- Divide plan state into three controlled zones:
  - the delimited `Dynamic Plan Status` block, which may be regenerated;
  - an append-only phase evidence log, which may receive validated evidence;
  - the normative plan body, which may change only through an explicit reviewed
    amendment.
- After every RF, DP, or OR phase checker:
  - read the phase check result and artifact freshness;
  - update current phase, completion state, blockers, and next required action;
  - append artifact hashes, checker results, relevant commits, and observed
    dashboard contract version to the evidence ledger;
  - compare actual modules, contracts, dependencies, and runtime assumptions
    with this plan;
  - emit a proposed amendment when reality invalidates a file target,
    dependency, acceptance gate, or implementation assumption.
- Support explicit operations equivalent to:
  - `--from-phase-status` for a safe status refresh;
  - `--propose-amendment` for a non-applied plan-drift proposal;
  - `--apply-amendment <proposal_id>` only after explicit operator invocation,
    proposal validation, and a clean safety check.
- Require atomic writes, document hashes, idempotent reruns, and a diff preview
  before any reviewed amendment is applied.

#### Update Protocol

| Event | Permitted Automatic Action | Required Human/Explicit Action |
| --- | --- | --- |
| Phase prerequisites pass | Set the requested phase to `in_progress` in runtime state and refresh the delimited status block | Invoke that phase implementation explicitly |
| Phase checker passes with fresh evidence | Mark the phase `passed`, append evidence, and identify the next prerequisite-satisfied phase | Decide when to begin the next phase |
| Phase checker fails | Mark the phase `blocked`, record exact blockers, and keep later phases blocked | Resolve the blocker or approve a scoped repair |
| Repository or runtime assumptions drift | Record drift and generate an unapplied amendment proposal | Review, accept, revise, or reject the proposal |
| Dashboard route contract changes | Freeze dashboard-dependent acceptance and propose a new contract version | Approve the structural change and refresh RF-0/RF-2 evidence |
| Safety, authority, proof, calendar, or broker boundary conflicts | Stop progression and emit a critical repair/amendment request | Resolve explicitly; no automatic override is allowed |

Phase states are limited to `not_started`, `in_progress`, `blocked`, `passed`,
`superseded_by_reviewed_amendment`, and `evidence_maturing`. Code completion
cannot convert `evidence_maturing` to `passed` when a gate requires provider
history, real elapsed market time, or a real closed paper outcome.

#### Runtime Artifacts

- `data/runtime/qadam_operator_ready_plan_state.json`
- `data/runtime/qadam_operator_ready_plan_phase_evidence.jsonl`
- `data/runtime/qadam_operator_ready_plan_amendments.jsonl`
- `data/runtime/qadam_operator_ready_plan_drift.json`
- `docs/qadam-operator-ready-edge-engine-implementation-log.md`

#### Non-Negotiable Boundary

The dynamic-plan system may never autonomously change safety boundaries,
authority, risk policy, broker routes, live-capital state, proof rules, the
actual `30-day paper growth trial`, phase evidence thresholds, or the meaning of
completion. It may not mark a phase complete from code presence, fixtures, or a
stale checker. A malformed status block or inconsistent evidence fails closed
and creates an amendment or repair request rather than editing the plan.

#### Acceptance

- Repeated status refreshes are idempotent.
- Automatic edits are confined to the delimited status block.
- Every phase state is traceable to a passing fresh checker and artifact hashes.
- Normative drift produces an unapplied, human-readable proposal.
- The checker rejects silent normative edits, stale evidence, malformed
  delimiters, unsafe field changes, and phase-order skips.

### RF-1 - No-Change Architecture And Dependency Audit

#### Objective

Understand the implemented Qadam, especially the edge-producing path, before
moving or consolidating code.

#### Build

- Add `orchestrator/qadam_architecture_audit.py`.
- Add `scripts/check_qadam_architecture_audit.py`.
- Inventory current modules, scripts, checks, runtime artifacts, generated
  mirrors, dashboard readers, background services, and nested-repository
  boundaries from the checkout at runtime; do not hard-code inventory counts.
- Map the full edge path:
  `source -> storage -> evidence -> feature -> score -> label -> backtest ->`
  `edge -> strategy -> Akber -> risk -> Router -> PaperOps -> lifecycle ->`
  `learning -> dashboard`.
- Build import, producer/consumer, artifact lineage, scheduler, and command-call
  graphs.
- Classify every component as canonical, safety-critical, compatibility,
  experimental, fixture-only, generated, superseded, or unrelated.
- Identify duplicate responsibilities, circular imports, script-owned business
  logic, live-versus-fixture ambiguity, direct JSON coupling, and paths that can
  influence authority or broker writes.
- Produce refactor decisions and unresolved questions without editing runtime
  code.

#### Runtime Artifacts

- `data/runtime/qadam_architecture_inventory.json`
- `data/runtime/qadam_edge_path_dependency_graph.json`
- `data/runtime/qadam_artifact_producer_consumer_map.json`
- `data/runtime/qadam_architecture_refactor_decisions.jsonl`

#### Acceptance

- Every edge-path artifact has known producers and consumers.
- Every execution-capable path is identified and boundary-labelled.
- Duplicate ownership and fixture ambiguity are explicit.
- The audit changes no runtime behavior or code structure.

### RF-2 - Characterization And Safety Regression Harness

#### Objective

Freeze intended current behavior before refactoring implementation details.

#### Build

- Add `scripts/check_qadam_characterization_harness.py` and narrowly scoped
  characterization fixtures.
- Characterize the canonical PaperOps wrapper, research lock behavior,
  authority flags, source-state taxonomy, artifact schemas, portfolio parity,
  Telegram review-only behavior, proof exclusions, and paper calendar.
- Characterize every dashboard module/view route, direct-link behavior,
  refresh persistence, journey navigation, responsive navigation, and read-only
  surface.
- Replace or explicitly retire superseded navigation assertions only after
  their intended coverage is mapped onto the current routed contract; do not
  leave contradictory dashboard checkers active.
- Label golden data by provenance so local samples and fixtures can never be
  mistaken for provider-backed history or real evidence.
- Add negative probes for direct broker calls, live routes, proof contamination,
  future-label leakage, malformed artifacts, missing lineage, and unauthorized
  plan mutation.

#### Runtime Artifacts

- `data/runtime/qadam_characterization_contract.json`
- `data/runtime/qadam_characterization_results.json`
- `data/runtime/qadam_safety_regression_results.json`
- `data/runtime/qadam_dashboard_route_characterization.json`

#### Acceptance

- Intended current behavior is reproducible before code movement starts.
- Every safety-negative probe fails closed.
- Dashboard route and portfolio-truth checks pass at desktop and mobile
  breakpoints.
- One canonical dashboard navigation checker family exists; no active checker
  requires the superseded five-view/hash shell.
- Test fixtures are visibly non-evidence and non-proof-bearing.

### RF-3 - Canonical Contracts And Artifact Ownership

#### Objective

Create one typed contract and one canonical owner for each edge-path domain
record while preserving compatibility readers during migration.

#### Build

- Add canonical contracts for `SourceEvent`, `PriceEvidence`, `FeatureVector`,
  `PatternScore`, `ForwardLabel`, `BacktestRun`, `EdgeRecord`,
  `StrategyHypothesis`, `AkberDecision`, `RiskDecision`, `RouterDecision`,
  `PaperOpsHandoff`, `TradeLifecycle`, `LearningAttribution`, and
  `RuntimeHealth`.
- Assign one canonical producer and schema version to every contract and status
  artifact.
- Add a shared atomic artifact store, status registry, provenance envelope,
  freshness policy, and explicit runtime/fixture/research/proof origin class.
- Move business rules out of command-line scripts into importable orchestrator
  services; keep scripts thin and observable.
- Add compatibility readers and migration warnings instead of breaking all
  consumers at once.
- Centralize immutable authority declarations while retaining local assertions
  at source, Router, PaperOps, broker, dashboard, Telegram, proof, and dynamic-
  plan boundaries.

#### Runtime Artifacts

- `data/runtime/qadam_contract_registry.json`
- `data/runtime/qadam_artifact_ownership_registry.json`
- `data/runtime/qadam_contract_migration_status.json`
- `data/runtime/qadam_compatibility_reader_audit.json`

#### Acceptance

- Every canonical record has one owner, schema, origin class, and validator.
- Compatibility readers preserve characterized behavior.
- Atomic writes prevent partial status publication.
- Safety assertions remain defense-in-depth rather than being deduplicated away.

### RF-4 - Provider, Storage, And Research Boundary Refactor

#### Objective

Separate data access from research logic so provider-backed acquisition can be
implemented and tested without rewriting the pattern engine.

#### Build

- Define provider protocols for current observations, historical observations,
  current prices, historical prices, capabilities, rate limits, and outages.
- Define storage interfaces for raw, normalized, point-in-time, research,
  generated-view, and proof-eligible domains.
- Introduce a resumable job contract with partition identity, checkpoint,
  checksum, attempt, retry class, and terminal-state semantics.
- Separate feature construction, scoring, labels, backtests, and edge promotion
  into explicit services with typed inputs and outputs.
- Rename and label the current local/sample baseline so no consumer can mistake
  it for provider-backed historical evidence.
- Preserve existing adapters through compatibility shims; do not perform OR-3
  provider acquisition in this refactor phase.

#### Runtime Artifacts

- `data/runtime/qadam_provider_protocol_registry.json`
- `data/runtime/qadam_storage_boundary_registry.json`
- `data/runtime/qadam_research_service_boundary_audit.json`
- `data/runtime/qadam_local_baseline_origin_audit.json`

#### Acceptance

- Research services can run against injected storage and provider interfaces.
- Network access is absent from pure feature, score, label, and backtest logic.
- Existing characterized research output remains equivalent.
- Sample/local artifacts are explicitly non-provider-backed and non-promotable.

### RF-5 - Decision, Risk, And Execution Boundary Refactor

#### Objective

Make the path from supported edge to guarded paper submission explicit without
changing any trading decision or execution behavior.

#### Build

- Define typed interfaces between Strategy Foundry, Akber, portfolio/risk,
  Router, PaperOps handoff, lifecycle, and learning attribution.
- Wrap the existing guarded PaperOps route rather than reimplementing its broker
  submission behavior.
- Preserve source quorum, distinct Research Goal lineage, candidate identity,
  idempotency, duplicate exposure, drawdown, risk budget, Q-CTRL consultation,
  guarded Alpaca Paper, and disabled-live-capital gates exactly.
- Separate Qadam-origin decisions from broker mirror, fixture, backtest, shadow,
  imported, and operator-origin records.
- Prohibit order calls in refactor tests; prove equivalence through contracts,
  recorded decisions, and negative probes.

#### Runtime Artifacts

- `data/runtime/qadam_decision_boundary_registry.json`
- `data/runtime/qadam_execution_boundary_registry.json`
- `data/runtime/qadam_paperops_equivalence_audit.json`
- `data/runtime/qadam_origin_classification_audit.json`

#### Acceptance

- Exactly one typed boundary exists between each decision stage.
- Existing guarded PaperOps behavior is unchanged.
- No new broker write path exists.
- Mirror, fixture, backtest, and shadow records remain ineligible for proof.

### RF-6 - Legacy Quarantine And Post-Refactor Rebaseline

#### Objective

Move edge-path consumers to canonical interfaces, quarantine obsolete paths,
and prove the refactor is behaviorally equivalent before edge work begins.

#### Build

- Migrate edge-path producers and consumers in dependency order.
- Mark legacy modules and artifacts with ownership, replacement, reader, and
  removal-readiness metadata.
- Quarantine superseded paths from new imports and new artifact production.
- Do not mass-delete legacy code. Delete only separately approved files whose
  references, compatibility windows, characterization checks, and rollback
  requirements are all clear.
- Re-run RF-0, architecture, characterization, safety, dashboard navigation,
  portfolio parity, and PaperOps equivalence checks.
- Ask DP-0 to detect plan drift and produce amendment proposals for invalid file
  targets, dependencies, or assumptions.
- Apply any normative plan update only through explicit review, then record the
  accepted post-refactor baseline and next OR-0 action.

#### Runtime Artifacts

- `data/runtime/qadam_legacy_quarantine_registry.json`
- `data/runtime/qadam_post_refactor_baseline.json`
- `data/runtime/qadam_post_refactor_behavior_diff.json`
- `data/runtime/qadam_post_refactor_plan_rebaseline.json`

#### Acceptance

- All edge-path consumers use canonical interfaces or declared compatibility
  readers.
- No unexpected behavioral, safety, route, or dashboard difference remains.
- Legacy producers cannot silently overwrite canonical artifacts.
- The dynamic plan is fresh, internally consistent, and explicitly rebaselined.
- OR-0 remains blocked unless RF-0 through RF-6 and DP-0 all pass.

## 13. OR-0 - Canonical Truth And Safety Baseline

### Objective

Create one authoritative runtime and documentation contract before changing
research or execution behavior.

### Gap Closed

- The master plan contains historical 60-day wording while the canonical
  runtime currently preserves a `30-day paper growth trial`.
- Public copy has claimed 500+ feeds while current runtime certification
  evaluates 41 source records and the dashboard separately tracks 35 canonical
  sources plus supplemental planes.
- Backfill state, manifest, and lock disagree about whether Phase 1 started or
  completed.

### Build

- Add `orchestrator/qadam_operator_ready_baseline.py`.
- Add `scripts/check_qadam_operator_ready_baseline.py`.
- Build a canonical truth contract that reads current artifacts rather than
  embedding counts.
- Define the difference between:
  - registered source;
  - configured adapter;
  - responding provider;
  - fresh observation;
  - historical-capable provider;
  - quorum-eligible evidence source;
  - supplemental context source.
- Reconcile the research lock, backfill state, and manifest through a read-only
  audit first.
- Record control-document contradictions as explicit blockers.
- Preserve the existing lock until OR-15 release criteria pass.

### Runtime Artifacts

- `data/runtime/qadam_operator_ready_baseline.json`
- `data/runtime/qadam_canonical_truth_contract.json`
- `data/runtime/qadam_runtime_state_reconciliation.json`
- `data/runtime/qadam_operator_ready_program_status.json`

### Acceptance

- Exactly one current paper-trial description is exported.
- Source counts include their taxonomy and cannot be compared as if equivalent.
- Lock, state, and manifest contradictions are visible.
- All unsafe authority flags remain false.
- No paper order, broker write, proof credit, calendar advance, or simulated time
  is created.

### Operator Outcome

The dashboard and checks agree on what Qadam is, what is running, and why it is
not trading.

## 14. OR-1 - Research Runtime Supervisor And Atomic State

### Objective

Make long-running research work real, single-instance, resumable, observable,
and safe across interruption.

### Extend

- `orchestrator/qadam_next_generation_safety_lock.py`
- `orchestrator/qsase_whole_universe_backfill_backtest.py`
- `orchestrator/qadam_self_healing_supervisor.py`
- `scripts/run_qsase_whole_universe_backfill_backtest.py`

### Build

- Replace six coarse manifest jobs with durable jobs that have:
  - stable job ID;
  - source/provider;
  - instrument where applicable;
  - date partition;
  - requested granularity;
  - retry class;
  - rate-limit class;
  - checksum and row count;
  - started/completed timestamps;
  - status and failure category;
  - resume cursor.
- Add atomic state writes using temporary files and rename.
- Add a single-instance PID/lease contract with stale-lease recovery.
- Add a heartbeat with current phase, current job, progress, throughput, disk
  usage, last successful provider call, and estimated remaining work.
- Resume only incomplete idempotent acquisition or calculation jobs.
- Never rerun a broker or execution action through this supervisor.
- Add target `launchd` templates and explicit install/uninstall/status scripts.
- Installation remains an operator action; merely implementing the templates
  must not start background services silently.
- Add clean SIGTERM handling and checkpoint before exit.
- Add disk-space and thermal/backpressure pauses.

### Runtime Artifacts

- `data/runtime/qadam_research_supervisor_status.json`
- `data/runtime/qadam_research_supervisor_heartbeat.json`
- `data/runtime/qadam_research_job_manifest.jsonl`
- `data/runtime/qadam_research_job_events.jsonl`
- `data/runtime/qadam_research_resume_state.json`

### Checks

- `scripts/check_qadam_research_supervisor.py`
- `scripts/check_qadam_research_state_atomicity.py`
- `scripts/check_qadam_research_resume.py`

### Acceptance

- Two launch attempts cannot create two active workers.
- Killing the worker mid-job leaves a valid resumable checkpoint.
- Restart resumes the same idempotent job without duplicate data.
- Heartbeat freshness is independently checked.
- Manifest, state, and lock agree.
- PaperOps stays watch-only.

### Operator Outcome

The operator can leave the laptop running and know whether research is active,
paused, complete, or needs intervention.

## 15. OR-2 - Source Freshness And Historical Provider Capability

### Objective

Turn the source registry from a connectivity catalogue into an operational
evidence-availability registry.

### Extend

- `orchestrator/qsase_source_reliability.py`
- `orchestrator/source_health.py`
- `orchestrator/phase1_live_adapters.py`
- `orchestrator/credential_bound_adapters.py`
- `docs/api-specs.md`

### Build

- Define per-category freshness budgets and trading-session expectations.
- Add provider capability fields:
  - current-data support;
  - historical API support;
  - earliest available date;
  - pagination/cursor model;
  - revision/vintage semantics;
  - rate limit;
  - credential requirement;
  - terms/licensing note;
  - native granularity;
  - expected data quality;
  - fallback or proxy;
  - forward-only state.
- Implement actual historical adapters only for providers whose terms and
  interfaces permit it.
- Separate provider outage from credential failure, parser defect, empty valid
  response, rate limiting, unsupported history, and market closure.
- Quarantine stale sources from live scoring.
- Allow context-only sources to remain visible without satisfying quorum.
- Produce safe repair requests rather than asking automation to edit secrets.
- Do not treat all 41 sources as equally required for every strategy.

### Runtime Artifacts

- `data/runtime/qadam_provider_capability_registry.jsonl`
- `data/runtime/qadam_source_freshness_policy.json`
- `data/runtime/qadam_source_operational_state.jsonl`
- `data/runtime/qadam_source_quarantine.jsonl`
- `data/runtime/qadam_provider_repair_requests.jsonl`

### Acceptance

- Every registered source has a current and historical capability class.
- Every required source is fresh, intentionally quarantined, or explicitly
  excluded from the affected strategy.
- No stale source contributes to a raw score or source quorum.
- Dashboard labels do not equate adapter readiness with fresh evidence.

### Operator Outcome

The operator sees which sources are merely connected and which are actually
usable now.

## 15A. OR-2R - Connection Truth And OR-3 Acquisition Readiness

### Objective

Repair misleading supplemental-adapter health, decide which licensed providers
will supply each historical dataset, and prove the acquisition path on a small
real slice before committing the laptop to the whole-universe OR-3 run.

OR-2R is a mandatory operational re-entry gate. Existing OR-2 implementation
credit remains valid, but OR-3 may not begin merely because a provider registry
file exists.

### Extend

- `orchestrator/tradingview_mcp_adapter.py`
- `scripts/check_tradingview_mcp_adapter.py`
- `orchestrator/qadam_source_provider_capabilities.py`
- `orchestrator/qadam_provider_backfill.py`
- `orchestrator/qadam_dynamic_plan.py`
- `orchestrator/qadam_operator_ready_certification.py`

Register OR-2R in the dynamic phase registry and final certification before the
next automatic status refresh so DP-0 cannot skip this new mandatory gate and
move directly from an implementation-level OR-2 pass to OR-3.

### TradingView Truth Repair

- Treat the bundled TradingView MCP as a third-party supplemental technical-
  analysis adapter, not an official TradingView market-data API.
- Replace the current binary `connected` state with explicit states:
  - `disabled`;
  - `sample_only`;
  - `dependency_missing`;
  - `live_supplemental`;
  - `provider_empty`;
  - `provider_rate_limited`;
  - `provider_error`;
  - `stale`.
- Require an actual read-only provider response containing fresh, provenance-
  backed records before reporting `live_supplemental`.
- Install and pin `tradingview-ta`, `tradingview-screener`, and the local MCP
  package in a dedicated environment or an explicitly approved project
  dependency set. Importing the local package alone is not a health check.
- Keep sample records in a fixture namespace. Never copy the hard-coded oil,
  silver, or semiconductor samples into canonical live context.
- Query Qadam's explicit symbol/venue allowlist. A generic NASDAQ scan does not
  prove coverage of `CL=F`, `SI=F`, ETFs, prediction markets, or the full
  watched universe.
- Record provider, venue, symbol mapping, delayed/live state, retrieval time,
  observed-market time, raw checksum, library version, and terms note.
- Do not request, scrape, store, or replay the operator's TradingView password,
  browser cookie, or session token.
- Keep TradingView in the confirmation lane only. It cannot independently
  satisfy source quorum, close OR-3 historical windows, create a candidate,
  or grant execution authority.
- A higher TradingView plan or exchange-display subscription is optional for
  the operator's manual charting. It is not an OR-2R acceptance condition.

### Historical Provider Coverage Decision

Create one reviewed acquisition matrix covering all 19 watched instruments and
all source histories intended for the initial edge search. Each row must state:

- canonical dataset and strategy/discovery roles;
- asset class, venue, symbol, contract identity, and paper proxy;
- target initial resolution, with daily/event resolution as the cost-controlled
  baseline unless a strategy requires intraday data;
- provider and official API/interface;
- earliest/latest supported timestamp and expected gaps;
- adjustment, futures-roll, revision/vintage, and timezone semantics;
- rate limits, pagination, retention, estimated rows, disk, time, and cost;
- credential class and manual setup required;
- research, redistribution, and commercial-use licensing posture;
- fallback provider or explicitly approved proxy;
- status: `pilot_ready`, `blocked_credentials`, `blocked_purchase_review`,
  `unsupported_history`, `proxy_proposed`, `forward_only`, or `excluded`.

At minimum, the price side must distinguish:

1. US equities and ETFs;
2. crude-oil and silver futures research context;
3. ETF execution proxies and basis risk;
4. prediction-market contract histories;
5. benchmark and macro-watchlist instruments.

The source side must distinguish historical archives from current-only feeds
across geopolitical/physical-world, macro/trade, market/technical, social/news/
filings, and prediction-market evidence. A provider purchase requires explicit
operator approval; self-healing and implementation code cannot purchase plans.

### Provider-Backed Pilot

- Run a small real-data pilot spanning at least two source categories, two
  market families, and both a source-event and price-bar acquisition path.
- Prefer a representative oil lane and one independent equity/ETF or macro
  lane so timestamps, calendars, proxies, and provider differences are tested.
- Exercise pagination, rate limiting, checksum validation, atomic partition
  commit, interruption, resume, duplicate handling, and point-in-time cutoff.
- Write raw and normalized rows to the ignored research store, not Git or large
  runtime JSON files.
- Verify that a rerun performs zero duplicate logical writes.
- Verify that disabling or losing one optional supplemental source does not
  manufacture evidence or silently substitute a sample.
- Estimate full-run duration, disk use, provider calls, and monetary cost from
  measured pilot throughput.

### Runtime Artifacts

- `data/runtime/qadam_connection_truth.json`
- `data/runtime/qadam_tradingview_supplemental_status.json`
- `data/runtime/qadam_historical_provider_purchase_matrix.json`
- `data/runtime/qadam_historical_source_coverage_matrix.json`
- `data/runtime/qadam_or3_provider_pilot_manifest.json`
- `data/runtime/qadam_or3_provider_pilot_results.json`
- `data/runtime/qadam_or3_acquisition_readiness.json`

### Acceptance

- TradingView never reports live merely because local modules import.
- Sample and live technical contexts cannot share the same canonical state.
- Every watched instrument and intended source history has a reviewed provider,
  proxy, explicit unavailability reason, or forward-only classification.
- The pilot writes real provider-backed rows and passes provenance, leakage,
  resume, idempotency, and storage checks.
- The projected full run fits configured disk, provider-call, time, and cost
  budgets.
- Missing credentials or purchases produce operator action requests without
  editing secrets or accepting terms automatically.
- `scripts/check_qadam_or3_acquisition_readiness.py` passes before OR-3 starts.
- No candidate, order, proof credit, or paper-calendar progress is created.

### Operator Outcome

The operator knows exactly what data must be purchased, what can be obtained
without purchase, what TradingView contributes, and whether the five-day
historical run is safe and likely to complete before starting it.

## 16. OR-3 - Provider-Backed Historical Source And Price Lake

### Objective

Acquire the historical evidence that the existing baseline only classified.

OR-3 implements the acquisition portions of
`docs/qadam-whole-universe-historical-backfill-backtest-implementation-plan.md`
only after OR-2R passes. The later scoring, labeling, statistical, nonlinear,
strategy, and decision phases remain owned by OR-4 through OR-16 here.

### Build

- Refuse to start when the OR-2R readiness artifact is stale, failed, or based
  only on fixtures.
- Create provider/date-partition acquisition jobs from OR-2 capabilities.
- Prioritize the price lake because every source event needs valid outcome
  windows.
- Acquire daily/event-resolution history first for every supported instrument;
  add intraday, options, order-flow, or tick depth only when a frozen strategy
  question requires it and the provider/license/cost budget permits it.
- Acquire adjusted OHLCV and, where available and justified, spread, volume,
  options, flow, volatility, and market-status context for the 19 watched
  instruments.
- Use licensed programmatic historical providers for the price lake. TradingView
  UI entitlements and the supplemental MCP must not be used to claim OR-3
  historical coverage.
- Keep instrument-specific acquisition lanes:
  - equities and ETFs;
  - futures plus explicit continuous-contract and roll construction;
  - prediction-market contracts and expiries;
  - macro benchmarks and approved research/execution proxies.
- Keep source-specific acquisition lanes so current-only, archive-supported,
  revised/vintage, and forward-only sources are not conflated.
- Handle:
  - equity splits and dividends;
  - ETF changes;
  - futures continuous-contract construction and roll metadata;
  - symbol changes;
  - prediction-market contract identity and expiry;
  - timezone and holiday calendars;
  - duplicate provider bars;
  - missing-session gaps.
- Acquire source histories using provider-native pagination and immutable raw
  response storage.
- Preserve raw payload checksum, request parameters, response timestamp,
  provider cursor, parser version, and normalized row count.
- Add bounded concurrency and per-provider rate-limit policies.
- Use exponential backoff only for safe, idempotent reads.
- Enforce daily provider-call and monetary cost ceilings. Reaching a ceiling
  checkpoints and pauses rather than silently switching providers or buying
  additional access.
- Continuously update heartbeat, throughput, partition coverage, estimated
  completion, disk use, provider errors, and operator-action requests.
- Resume from committed partitions after sleep, reboot, network loss, provider
  rate limiting, or process interruption.
- Never fabricate a historical proxy without recording the substitution and
  keeping it out of direct-source claims.
- Make the laptop run streaming and partitioned, not all-in-memory.

### Data Layout

Recommended ignored paths:

```text
data/research/raw/source=<source>/date=<date>/...
data/research/normalized/source=<source>/date=<date>/...
data/research/prices/symbol=<symbol>/interval=<interval>/year=<year>/...
data/research/manifests/...
```

Runtime summaries remain under `data/runtime/`.

OR-3 must add the bulk research directory to `.gitignore` before the first
provider-backed write and must include a preflight that refuses to run if the
target bulk path is Git-trackable.

### Runtime Artifacts

- `data/runtime/qadam_source_backfill_manifest.json`
- `data/runtime/qadam_price_backfill_manifest.json`
- `data/runtime/qadam_backfill_coverage.json`
- `data/runtime/qadam_backfill_errors.jsonl`
- `data/runtime/qadam_backfill_dashboard_summary.json`
- `data/runtime/qadam_backfill_cost_and_rate_limit_state.json`
- `data/runtime/qadam_backfill_unavailable_windows.jsonl`

### Acceptance

- Every source and instrument is acquired or explicitly classified unavailable,
  forward-only, excluded, or represented by an approved and visibly labelled
  proxy.
- Row counts, checksums, partition coverage, and gaps validate.
- A rerun is idempotent.
- Missing history is no longer represented as a successful provider call.
- The `6,150` missing-window baseline is reduced through real acquisition and
  every remainder has a typed reason. Completion does not require inventing a
  bar for a pre-inception instrument, closed market, expired contract, or
  unavailable archive.
- Daily-resolution whole-universe coverage is completed or classified before
  optional high-cost intraday expansion begins.
- Bulk data remains outside Git.
- Backfill creates no candidate, order, proof, or calendar progress.

### Operator Outcome

The long-running job visibly advances instead of rebuilding the same 82 local
windows.

## 17. OR-4 - Point-In-Time Alignment And Evidence Completion

### Objective

Create leakage-safe source-price relationships and complete typed evidence.

### Extend

- `orchestrator/qsase_historical_source_price_memory.py`
- `orchestrator/qsase_historical_memory_completion.py`
- `orchestrator/qsase_evidence_quality_engine.py`
- existing evidence-native contract builders.

### Build

- Normalize the timestamp semantics defined in Section 10.
- Construct an eligibility graph rather than an indiscriminate Cartesian
  product:
  - causal strategy mappings;
  - broad discovery mappings;
  - negative controls;
  - explicitly irrelevant pairs.
- Generate forward windows only when both source availability and market data
  satisfy the cutoff.
- Record unavailable windows by reason:
  - source published too late;
  - price history absent;
  - market closed;
  - insufficient horizon;
  - contract expired;
  - source revision leakage;
  - provider gap;
  - pair intentionally not meaningful.
- Complete the 465 typed evidence gaps where underlying data exists.
- Do not require all 6,232 relationships to become complete if the relationship
  is impossible or irrelevant. Require 100% classification and sufficient
  eligible evidence per promoted edge.
- Add duplicate-event clustering so syndicated reports do not masquerade as
  independent source quorum.

### Runtime Artifacts

- `data/runtime/qadam_point_in_time_alignment_summary.json`
- `data/runtime/qadam_relationship_eligibility_graph.jsonl`
- `data/runtime/qadam_forward_window_coverage.json`
- `data/runtime/qadam_typed_evidence_completion.json`
- `data/runtime/qadam_leakage_audit_v2.json`

### Acceptance

- Leakage violations are zero.
- Every missing window has a typed reason.
- Every eligible score input carries `available_at` and provenance.
- Source independence is measured after duplicate clustering.
- Router-eligible evidence cannot contain missing critical fields.

### Operator Outcome

Qadam can distinguish "not enough data," "not a valid relationship," and "the
market did not confirm it."

## 18. OR-5 - Pattern Score V3 And Feature Engine

### Objective

Implement the point-in-time signal that the backtest will evaluate.

### Extend

- `orchestrator/qadam_pattern_engine_v2.py`
- existing linear and nonlinear QSASE labs.

### Build

- Preserve V2 `rank_score` as a research-ranking field; do not present it as a
  probability or validated edge.
- Add a versioned feature registry with transformation, input provenance,
  availability rule, missing-value policy, expected range, and owner.
- Build strategy-informed feature packs for all five strategies.
- Build strategy-agnostic features that do not require an existing family.
- Build negative-control features.
- Calculate the raw pattern score before reading labels.
- Export component contributions and penalties.
- Add direction and horizon as explicit hypotheses rather than inferring them
  from future returns.
- Local Gemma may extract structured event features from unstructured text, but
  every extraction must be cached, versioned, and reproducible.
- Frontier Gemini may challenge a shortlisted pattern after scoring; its prose
  cannot enter historical labels or retroactively change the score tape.
- Missing critical features lower confidence or block the score according to a
  frozen policy.

### Runtime Artifacts

- `data/runtime/qadam_feature_registry.json`
- `data/runtime/qadam_pattern_score_v3.json`
- `data/runtime/qadam_pattern_score_v3_records.jsonl`
- `data/runtime/qadam_pattern_score_v3_rejections.jsonl`
- `data/runtime/qadam_pattern_score_v3_dashboard_summary.json`

Bulk feature matrices belong in the research store, not runtime JSONL.

### Checks

- Deterministic rerun test.
- Future-field denial test.
- Missing-feature test.
- Source-duplication penalty test.
- Score-bound and component-sum tests.
- Strategy-agnostic discovery test.

### Acceptance

- The same inputs and model version produce the same score.
- No label or forward return is available to the scorer.
- Every score explains its components, missing evidence, and permitted next
  action.
- Scores create no candidates or orders.

### Operator Outcome

The dashboard can explain what Qadam detected before claiming that it worked.

## 19. OR-6 - Historical Score Tape

### Objective

Replay history chronologically and record what Qadam would have believed at
each eligible decision point.

### Build

- Add a resumable score-tape runner partitioned by strategy, instrument,
  date, horizon, and model version.
- Freeze the feature snapshot at `scoring_as_of`.
- Cache local-LLM extraction results by content hash and prompt/model version.
- Do not call the frontier LLM for every historical row; use deterministic
  structured features and reserve frontier review for sampled qualitative
  audits or shortlisted patterns.
- Write a score first, then expose the record to the labeler in OR-7.
- Preserve rejected and unscorable decision points.
- Add score-distribution drift checks and duplicate score detection.

### Research Artifacts

- Partitioned `pattern_score_tape` dataset.
- `data/runtime/qadam_pattern_score_tape_manifest.json`
- `data/runtime/qadam_pattern_score_tape_progress.json`
- `data/runtime/qadam_pattern_score_tape_quality.json`

### Acceptance

- Every tape row is immutable, versioned, and lookahead-safe.
- Resume does not change completed partitions.
- The label columns do not exist in score partitions.
- Coverage is reported by source, strategy, instrument, horizon, and regime.

### Operator Outcome

Qadam now has a genuine record of historical decisions to test, rather than a
summary calculated after seeing returns.

## 20. OR-7 - Forward Outcome Labels And Cost Model

### Objective

Measure what happened after each frozen score without contaminating the score.

### Build

- Create separate label partitions keyed by `score_id`.
- Support strategy-appropriate horizons such as intraday, 1-day, 3-day, 5-day,
  and event-expiry where data allows.
- Record:
  - gross return;
  - net return;
  - benchmark-relative return;
  - maximum favourable excursion;
  - maximum adverse excursion;
  - realized volatility;
  - time to threshold;
  - gap risk;
  - liquidity/spread state;
  - unfilled or delayed-entry proxy;
  - market regime;
  - invalidation occurrence.
- Version the transaction-cost model by instrument and period.
- Model paperable proxy differences explicitly, for example `CL=F` research
  context versus `USO` execution proxy.
- Prevent overlapping labels from being counted as independent samples.

### Runtime Artifacts

- `data/runtime/qadam_forward_label_manifest.json`
- `data/runtime/qadam_transaction_cost_model.json`
- `data/runtime/qadam_label_coverage.json`
- `data/runtime/qadam_label_quality_audit.json`

### Acceptance

- Labels are joined only after score creation.
- Gross and net results are both retained.
- Unsupported liquidity assumptions fail closed.
- Label coverage and overlap are explicit.

### Operator Outcome

Qadam can ask whether a score would have made money after realistic friction.

## 21. OR-8 - Whole-Universe Statistical Backtest

### Objective

Determine which scores represent repeatable edge and which are noise.

### Build

- Add transparent baseline models:
  - unconditional market return;
  - simple momentum/reversal;
  - strategy-blind linear model;
  - random or shuffled-time negative controls.
- Test Qadam methods:
  - source-price historical occurrence;
  - lead-lag and event studies;
  - vector analog retrieval;
  - state-matrix probability;
  - cross-source divergence;
  - cross-asset confirmation;
  - regime-conditioned relationships.
- Run chronological walk-forward folds.
- Apply purging, embargo, and nested threshold tuning.
- Use block bootstrap or another dependence-aware uncertainty method.
- Track every attempted hypothesis and apply false-discovery correction.
- Report results by strategy, instrument, direction, horizon, regime, and
  source contribution.
- Include survivorship and availability-bias checks.
- Record rejected, unstable, overfit, cost-sensitive, and concentrated edges.

### Runtime Artifacts

- `data/runtime/qadam_backtest_protocol.json`
- `data/runtime/qadam_backtest_run_manifest.json`
- `data/runtime/qadam_backtest_results_summary.json`
- `data/runtime/qadam_backtest_rejections.jsonl`
- `data/runtime/qadam_multiple_testing_audit.json`
- `data/runtime/qadam_walk_forward_audit.json`
- `data/runtime/qadam_backtest_dashboard_summary.json`

Bulk fold results remain in the research store.

### Acceptance

- Untouched holdout results exist.
- Costs are included.
- Negative controls do not appear as validated edges.
- False-discovery-adjusted state is recorded.
- Results reproduce from manifests and dataset hashes.
- Backtest output creates no strategy mutation, candidate, order, or proof.

### Operator Outcome

The dashboard can say "this pattern historically had edge" with defensible
evidence, or reject it honestly.

## 22. OR-9 - Nonlinear And Quantum Incremental-Value Lab

### Objective

Use nonlinear and quantum capabilities where they add measurable value, not as
decoration.

### Build

- Establish matched classical baselines before every nonlinear or quantum
  experiment.
- Evaluate:
  - nonlinear feature interactions;
  - regime/path dependence;
  - permutation or ordinal entropy;
  - clustering and state transitions;
  - constrained combinatorial feature selection;
  - quantum-kernel or circuit-inspired experiments where technically valid.
- Use training/validation data only for model selection.
- Evaluate final incremental value on untouched holdout data.
- Record runtime, provider availability, cost, fallback, sensitivity, and
  reproducibility.
- Define `quantum_usefulness_score` from incremental predictive or decision
  value after complexity, latency, and reliability penalties.
- If classical performance is equal or better, label the quantum contribution
  `not_useful_for_this_edge`.
- Hardware access remains optional evidence generation and never a completion
  requirement when a faithful classical fallback is the actual path used.

### Runtime Artifacts

- `data/runtime/qadam_nonlinear_experiment_registry.jsonl`
- `data/runtime/qadam_quantum_classical_comparison.jsonl`
- `data/runtime/qadam_quantum_usefulness_summary.json`
- `data/runtime/qadam_nonlinear_overfit_audit.json`

### Acceptance

- Every nonlinear/quantum claim has a classical comparison.
- No holdout tuning occurs.
- Fallback is labelled.
- Quantum creates no approval or execution authority.

### Operator Outcome

The operator can see when Head of Quant genuinely helped and when it did not.

## 23. OR-10 - Edge Registry And Strategy Evidence Map V3

### Objective

Convert backtest evidence into a durable, versioned catalogue of edges.

### Extend

- `orchestrator/qadam_strategy_evidence_map.py`
- existing QSASE learning and pattern artifacts.

### Build

- Create one edge record per distinct source-feature/instrument/direction/
  horizon/regime relationship.
- Store:
  - raw score definition;
  - strategy-fit vector;
  - sample and effective sample size;
  - gross and net expectancy;
  - confidence distribution;
  - calibration diagnostics;
  - drawdown and tail loss;
  - turnover and cost sensitivity;
  - source/instrument concentration;
  - regime stability;
  - nonlinear/quantum incremental value;
  - decay and latest supporting sample;
  - promotion class;
  - falsifiers and retirement conditions.
- Update the five strategy evidence maps from edge records, not from strategy
  descriptions.
- Rank deployment priority by evidence quality, liquidity, paperability,
  operational reliability, and portfolio diversification.
- Keep crude-oil/energy security as the likely first validation sleeve only if
  the new evidence continues to support it.
- Create new-family proposals for unmapped validated discoveries.

### Runtime Artifacts

- `data/runtime/qadam_edge_registry.jsonl`
- `data/runtime/qadam_edge_registry_summary.json`
- `data/runtime/qadam_strategy_evidence_map_v3.json`
- `data/runtime/qadam_strategy_retirement_proposals.jsonl`
- `data/runtime/qadam_new_strategy_family_proposals.jsonl`

### Acceptance

- Every strategy is labelled evidence-backed, exploratory, under-evidenced,
  degraded, or retired.
- No strategy is promoted merely because it exists in the dashboard.
- Edge records link to score, label, fold, and dataset versions.
- A valid research outcome is "no validated edge yet," but that outcome blocks
  Edge-Validated and Paper-Operator-Ready certification rather than being
  treated as completion.

### Operator Outcome

The operator knows which strategy deserves paper attention and why.

## 24. OR-11 - Strategy Foundry V3

### Objective

Turn validated or explicitly exploratory edges into trade-shaped hypotheses
without creating trades.

### Extend

- `orchestrator/qadam_strategy_foundry_v2.py`
- existing Research Goal and Fresh Setup Identity contracts.

### Build

- Require an edge-registry reference for evidence-backed hypotheses.
- Permit exploratory hypotheses only in shadow-only state.
- Produce:
  - Research Goal lineage;
  - distinct candidate identity material;
  - strategy family and fit score;
  - instrument and execution-proxy mapping;
  - direction and horizon;
  - catalyst and confirmation requirements;
  - entry concept;
  - invalidation and exit conditions;
  - risk concept;
  - expected edge range;
  - known failure modes;
  - current blocker state;
  - paperability state;
  - freshness expiry.
- Reject weak, stale, unsupported, duplicate, non-paperable, or logically
  inconsistent hypotheses before Akber.
- Keep LLM reasoning as a cited qualitative contribution, not numerical proof.

### Runtime Artifacts

- `data/runtime/qadam_strategy_foundry_v3.json`
- `data/runtime/qadam_strategy_hypotheses_v3.jsonl`
- `data/runtime/qadam_strategy_hypothesis_rejections_v3.jsonl`
- `data/runtime/qadam_strategy_foundry_v3_dashboard_summary.json`

### Acceptance

- Every hypothesis has complete edge and Research Goal lineage.
- Every hypothesis has a unique identity and expiry.
- Exploratory hypotheses cannot leave shadow-only state.
- Foundry creates no qualified setup, approval, or order.

### Operator Outcome

Qadam explains not only what it found, but how the finding could become a
disciplined trade if current evidence confirms it.

## 25. OR-12 - Akber Filter V3

### Objective

Make Akber the calibrated practical trader rather than a permanent
missing-context hold.

### Extend

- `orchestrator/qadam_akber_filter_v2.py`
- market confirmation, Signal Integrity, Yahoo/Alpaca market context, and
  Bookmap/TradingView read-only adapters.

### Build

- Populate all current required context fields:
  - source-price context;
  - fresh catalyst;
  - technical confirmation;
  - volume or flow confirmation;
  - volatility context;
  - pricing-gap evidence;
  - risk-reward context;
  - invalidation clarity;
  - liquidity and spread;
  - paperability proxy;
  - nonlinear/quantum review.
- Assemble confirmation from canonical provider-backed market context first.
  TradingView or Bookmap may enrich confirmation only when their OR-2R-style
  origin, freshness, delay, and live/sample states are truthful. Their outage
  must produce a typed context gap or approved fallback, never a fixture.
- Map those fields into six user-facing stages: context, catalyst,
  confirmation, risk, execution, and postmortem learning.
- Replay historical hypotheses through Akber.
- Run stage-by-stage ablations and threshold sensitivity.
- Measure:
  - false positives removed;
  - good opportunities filtered out;
  - expectancy change;
  - drawdown change;
  - turnover change;
  - missed-opportunity cost;
  - regime dependence.
- Generate threshold proposals only from training/validation evidence.
- Apply threshold changes only through explicit versioned review.
- Produce a short explanation for pass, hold, or veto.

### Runtime Artifacts

- `data/runtime/qadam_akber_filter_v3_inputs.jsonl`
- `data/runtime/qadam_akber_filter_v3_results.jsonl`
- `data/runtime/qadam_akber_filter_v3_replay.jsonl`
- `data/runtime/qadam_akber_filter_v3_ablation.jsonl`
- `data/runtime/qadam_akber_filter_v3_threshold_proposals.jsonl`
- `data/runtime/qadam_akber_filter_v3_dashboard_summary.json`

### Acceptance

- No Router-eligible setup has missing critical Akber context.
- Akber pass, hold, and veto are evidence-based.
- Akber's net historical contribution is measurable.
- Akber pass is not execution approval.

### Operator Outcome

The operator sees whether an edge is tradeable now, not merely interesting.

## 26. OR-13 - Continuous Forward Shadow Validation

### Objective

Verify that historical edge survives fresh unseen market conditions before
paper allocation increases.

### Extend

- `orchestrator/qadam_shadow_simulator_v2.py`
- OR-1 supervisor.

### Build

- Run every eligible hypothesis forward in real time with no order.
- Freeze the exact hypothetical decision at the decision timestamp.
- Track:
  - predicted direction, horizon, and return range;
  - actual gross/net outcome;
  - Akber decision;
  - alternate threshold outcomes;
  - wait/hold/veto counterfactuals;
  - missed opportunities;
  - forecast calibration;
  - drift from historical confidence;
  - source outage and latency effects.
- Enforce real elapsed time. Historical replay cannot satisfy forward-shadow
  duration or signal-count requirements.
- Define promotion by independent signal count and power, not a fixed number of
  calendar days alone.
- Keep shadow results ineligible for paper proof credit.

### Runtime Artifacts

- `data/runtime/qadam_forward_shadow_state.json`
- `data/runtime/qadam_forward_shadow_decisions.jsonl`
- `data/runtime/qadam_forward_shadow_outcomes.jsonl`
- `data/runtime/qadam_shadow_calibration.json`
- `data/runtime/qadam_shadow_promotion_readiness.json`

### Acceptance

- Supervisor heartbeat proves the shadow service is running.
- Decisions are timestamped before outcomes.
- Every completed decision has an outcome or typed expiry.
- Promotion requires frozen policy and real elapsed evidence.
- No paper order or proof credit is created.

### Operator Outcome

The operator can watch Qadam make and score real-time predictions before money
is exposed even in paper mode.

## 27. OR-14 - Portfolio Construction And Risk Engine

### Objective

Turn individual edges into a portfolio that protects capital and avoids
concentrated versions of the same bet.

### Build

- Add deterministic portfolio construction using:
  - edge confidence class;
  - expected net return;
  - volatility targeting;
  - maximum loss at invalidation;
  - existing exposure;
  - cross-position correlation;
  - strategy and source concentration;
  - liquidity and spread;
  - current and trailing drawdown;
  - tail-risk stress scenarios;
  - uncertainty haircut;
  - paperability and venue constraints.
- Define hard caps by instrument, strategy, correlated cluster, and day.
- Add no-trade states for excessive uncertainty or unattractive expected return
  after costs.
- Add deterministic size rounding for broker-valid quantities.
- Run historical and shadow portfolio simulations.
- Keep risk policy versioned and human-governed.

### Runtime Artifacts

- `data/runtime/qadam_portfolio_policy.json`
- `data/runtime/qadam_portfolio_risk_state.json`
- `data/runtime/qadam_position_size_proposals.jsonl`
- `data/runtime/qadam_portfolio_stress_test.json`
- `data/runtime/qadam_risk_rejections.jsonl`

### Acceptance

- A setup cannot size without invalidation and liquidity context.
- Correlated setups do not bypass aggregate exposure limits.
- Drawdown and daily-loss gates fail closed.
- LLM and quantum components cannot approve or change size.
- Output remains a proposal until the existing Risk/PaperOps chain passes.

### Operator Outcome

Qadam seeks return without treating every edge as an unlimited bet.

## 28. OR-15 - Router V3 And Guarded PaperOps Release

### Objective

Restore paper operation only after the research and shadow evidence gates are
complete.

### Extend

- `orchestrator/qadam_router_v2_paperops_handoff.py`
- `orchestrator/qsase_paperops_gate_interface.py`
- guarded PaperOps-2, PaperOps-3, and PaperOps-4 components.
- `scripts/run_paperops_autonomous_pass.py` remains the canonical unattended
  PaperOps wrapper for one pass.

### Build

- Router V3 emits exactly one state:
  - reject;
  - watchlist;
  - shadow-only;
  - hold;
  - repair-requested;
  - blocked-safety-boundary;
  - paper-review-candidate.
- Require complete references to:
  - Research Goal;
  - score;
  - edge;
  - strategy hypothesis;
  - Akber result;
  - shadow evidence;
  - risk proposal;
  - source quorum;
  - duplicate exposure;
  - drawdown;
  - Q-CTRL state;
  - instrument paperability;
  - idempotency material.
- Add a research-lock release checker that may recommend release only when
  OR-0 through OR-14 pass.
- Lock release remains explicit and auditable; self-healing cannot release it.
- Replace the current split-brain boundary in which Router V3 can write a
  handoff that the canonical PaperOps wrapper does not consume. Define one
  versioned handoff reader used by
  `scripts/run_paperops_autonomous_pass.py`, with schema, freshness, lineage,
  authority, and idempotency validation before the older guarded PaperOps
  sequence can stage anything.
- Preserve the canonical autonomous wrapper as the only unattended paper pass.
  Do not create a second broker client, submitter, scheduler, or compatibility
  bypass for V3 records.
- Record a consumption receipt or typed rejection for every handoff so a
  paper-review candidate cannot disappear between Router and PaperOps.
- Once an operator has approved a strategy version and paper risk policy,
  individual clean paper setups should not require repeated human approval.
  The guarded PaperOps gates should submit them autonomously when every current
  condition passes.
- Keep multiple paper trades per day possible only for distinct qualified
  setups passing every gate.
- Keep prediction-market contracts context-only unless a separately governed
  paper route exists.

### Runtime Artifacts

- `data/runtime/qadam_router_v3_decisions.jsonl`
- `data/runtime/qadam_router_v3_scoreboard.json`
- `data/runtime/qadam_router_v3_why_not_trading_now.json`
- `data/runtime/qadam_paperops_handoff_v3.jsonl`
- `data/runtime/qadam_research_lock_release_readiness.json`

### Acceptance

- Every setup has exactly one Router state.
- Only clean paper-review candidates produce handoff records.
- Handoff records are not orders.
- The canonical PaperOps wrapper consumes the certified V3 handoff through the
  one guarded reader, or rejects it with a typed reason.
- No V3 handoff is submitted by an alternate route and no accepted handoff is
  silently ignored.
- The guarded Alpaca Paper route is the only submission route.
- Duplicate exposure, drawdown, source quorum, Q-CTRL, and idempotency probes
  fail closed.
- No live-capital path exists.

### Operator Outcome

When Qadam trades on paper, the operator can see the complete reason and proof
chain; when it waits, the reason is equally clear.

## 29. OR-16 - Paper Lifecycle, Proof, And Attribution

### Objective

Make every Qadam-origin paper outcome measurable and distinguish it from broker
mirror history.

### Extend

- PaperOps lifecycle poller, close path, close-to-ledger path, and postmortem.
- `orchestrator/qadam_learning_attribution_v2.py`.

### Build

- Require lifecycle states:
  - staged;
  - submitted;
  - accepted;
  - partially filled;
  - filled;
  - open;
  - exit requested;
  - closed;
  - cancelled;
  - rejected;
  - expired;
  - reconciliation required;
  - postmortem complete.
- Add stale accepted-order policy: wait, cancel/replace proposal, or no-action
  explanation according to frozen paper policy.
- Preserve source/edge/strategy/Akber/shadow/risk/router/idempotency lineage
  through every state.
- Classify broker records as:
  - Qadam-origin with complete lineage;
  - Qadam-origin with incomplete lineage;
  - external/manual paper record;
  - mirror-only historical record.
- Never backfill proof credit for the current 42 mirror records merely because
  they are closed.
- Compute realized net P&L, slippage, holding period, adverse/favourable
  excursion, exit reason, and edge calibration.
- Complete postmortems and component attribution.
- Attribute every outcome, hold, veto, miss, and operational defect to:
  - source evidence;
  - local/frontier model contribution;
  - nonlinear/quantum review;
  - strategy hypothesis;
  - Akber stages;
  - Router decision;
  - portfolio/risk decision;
  - PaperOps and broker execution quality;
  - exit decision;
  - provider or system reliability.
- Add champion/challenger proposal states: proposed, approved-for-research,
  backtested, shadowing, approved-for-paper, rejected, degraded, and retired.
- Detect calibration drift, edge decay, source drift, and execution drift.
- Never let attribution mutate source trust, strategy weights, thresholds,
  authority, or risk settings without an explicit versioned approval path.

### Runtime Artifacts

- `data/runtime/qadam_paper_lifecycle_v3.json`
- `data/runtime/qadam_paper_trade_lineage.jsonl`
- `data/runtime/qadam_paper_postmortems_v3.jsonl`
- `data/runtime/qadam_paper_proof_eligibility.json`
- `data/runtime/qadam_learning_attribution_v3.jsonl`
- `data/runtime/qadam_paper_performance_summary.json`

### Acceptance

- No order remains ambiguous.
- Every broker record has an origin class.
- Proof credit requires a real closed Qadam-origin paper trade with complete
  lineage.
- Backtests, shadows, fixtures, and mirror-only records receive zero proof.
- Learning outputs are proposals only.

### Operator Outcome

The portfolio chart and trading history reflect outcomes Qadam can honestly
claim and learn from.

## 30. OR-17 - Operator Dashboard And Telegram Control Plane

### Objective

Make the existing dashboard the single readable operating surface under the
explicitly approved DP-0 navigation amendment without creating authority.

### Protected Dashboard Navigation Contract

The following `qadam_protected_decision_flow.v4` contract supersedes V3 after
explicit operator review on 2026-07-12. It preserves the operating journey but
consolidates Learn & Improve around the two questions a reader actually asks:
what Qadam learned, and how that lesson is being tested.

| Navigation area | Views | Route IDs |
| --- | --- | --- |
| Pinned context | Qadam Team (orientation, not a journey stage) | `system/team` |
| Fund | Portfolio (performance, allocation, risk, and positions), Trading History | `fund/portfolio`, `fund/timeline` |
| Observe | Data Sources, Trading Universe | `observe/sources`, `observe/universe` |
| Find Patterns | Pattern Recognition, Quantum Edge | `patterns/findings`, `patterns/nonlinear` |
| Test & Decide | Trading Strategies, Decision Room (current outcome above trade intents) | `decide/strategies`, `decide/decision` |
| Trade | Order Monitor (current orders and positions, five recent broker events, then the learning handoff) | `trade/orders` |
| Learn & Improve | Results & Lessons, Tests & Improvements | `learn/outcomes`, `learn/improvements` |
| Standalone System destination | System Overview | `system/overview` |

Also preserve:

- `/dashboard/?module=<module>&view=<view>` as the deep-link contract;
- legacy `decide/intents` deep links redirect to the consolidated
  `decide/decision` route;
- legacy `fund/holdings` deep links resolve to the consolidated
  `fund/portfolio` route;
- legacy `system/activity` and `system/health` deep links resolve to the
  consolidated `system/overview` route;
- legacy `learn/replay` deep links resolve to `learn/improvements`;
- legacy `learn/briefs` deep links resolve to `learn/outcomes`;
- `fund/portfolio` as the default route;
- the left decision-flow sidebar on desktop and section control on mobile;
- Qadam Team pinned above Fund as orientation context;
- one standalone System link at the bottom of the sidebar, with no separate
  System category heading or nested System Overview link;
- route state, expanded navigation state, and scroll intent during the existing
  15-second status refresh;
- previous/next journey navigation through Fund, Observe, Find Patterns, Test &
  Decide, Trade, and Learn & Improve only;
- no previous/next links on Qadam Team or System Overview;
- the top paper-account context and portfolio timeline;
- exactly one compact 10-stage lifecycle on every route, with the route's
  primary, supporting, outcome-mirror, or cross-cutting relationship made
  explicit and the expanded explanation available through progressive
  disclosure;
- all read-only and command-disabled boundaries.

The current protected experience contains 13 routes total, including Qadam Team
and System Overview. `fund/timeline` keeps its stable route ID while its visible
label is Trading History. `patterns/nonlinear` keeps its stable route ID while
its visible label is Quantum Edge. Checkers must validate the current labels
and behavior rather than restoring older Timeline, Pattern Findings, Nonlinear
Review, 19-route, or five-view contracts.

The canonical Stage 6 long label is `Akber's 6-Stage Filter` and its compact
label is `Akber's Filter`. Older checker copy such as `Filter Tradeability` or
`six-stage filter` must not force the UI back to obsolete language.

### Dashboard-To-Engine Truth Map

| Dashboard surface | Engine truth it must render | Must never imply |
| --- | --- | --- |
| Qadam Team | Python COO, local Gemma, frontier Gemini, and IBM/Q-CTRL/Qiskit state, latency, fallback, and responsibility | Human-like sentience or independent capital authority |
| Portfolio | Canonical Alpaca Paper balance, exposure, positions, P&L, drawdown, and one timestamp | Backtest or mirror records are current Qadam returns |
| Trading History | Submitted, filled, closed, held, and rejected paper lifecycle with origin and lineage | Every broker record came from Qadam |
| Data Sources | Category, provider, freshness, trust, history capability, quarantine, and repair state | Configured means fresh or historically complete |
| Trading Universe | All 19 watched instruments, roles, proxies, provider coverage, and paperability | Every watched instrument is directly tradeable |
| Pattern Recognition | Ranked point-in-time findings, research scores, evidence, duration, lifecycle, and next destination | Research score is probability or validated edge |
| Quantum Edge | Classical/quantum comparison, hardware/simulator/fallback state, incremental value, and verdict | Quantum activity automatically improves a strategy |
| Trading Strategies | Five configured families, emerging pattern-sourced strategies, validated strategies, and self-refinement evidence | Core strategy descriptions are proven edges |
| Decision Room | Research approaching Akber, six-stage diagnostics, portfolio/Router state, and one committee verdict | Akber pass is an order or execution approval |
| Order Monitor | Live Alpaca Paper mirror, lifecycle, reconciliation, exceptions, and downstream learning handoff | Dashboard can submit, cancel, or alter orders |
| Results & Lessons | Attributable outcomes, expectation versus result, supported lesson, and next test | Mirror, fixture, or shadow rows are proof |
| Tests & Improvements | Proposal, historical test, forward observation, review, applied version, and return to Observe | Qadam silently changes itself |
| System Overview | Service/process truth, freshness, provider incidents, locks, retries, and repair queue | Research incompleteness is infrastructure success or failure without context |

Results & Lessons owns the chronological expectation, result, supported lesson,
and next-test record. Tests & Improvements owns the controlled pipeline from
proposal through historical testing, forward shadow observation, review,
versioned application, and the next Observe cycle. Mirror-only broker records
remain collapsed reference context and cannot count as Qadam performance,
postmortems, or paper proof ledger evidence.

System Overview replaces the fragmented Live Activity and System Health pages.
It must use the canonical operator projection as a progressive-disclosure
operating and reliability console. The infrastructure verdict, underlying
evidence timestamp, intentional operating mode, and deduplicated root incidents
remain visible. Infrastructure and connections, automations and scheduled
work, freshness and monitoring, lifecycle impact, typed operating events, and
technical evidence remain collapsed until requested. It must not restore the
synthetic matrix terminal, the equal-weight operational metric wall, or present
research incompleteness as an infrastructure incident.

Enrichment and redesign are allowed inside individual views. A route, module,
journey-order, or navigation-shell change requires a DP-0 amendment proposal,
an explicit operator review, updated characterization evidence, and a new
dashboard contract version. It must not arrive as an incidental OR-phase edit.

### Build

- Show one unambiguous runtime state: running, paused, degraded, blocked,
  research-only, shadowing, or paper-operational.
- Distinguish source configured/responding/fresh/quorum-eligible/historical.
- Show backfill progress, throughput, remaining work, and last heartbeat.
- Preserve the expandable Trading Strategies playbooks.
- For every pattern show:
  - detected signal;
  - market affected;
  - raw pattern score;
  - strategy fit;
  - historical edge state;
  - evidence and sample quality;
  - what Qadam thinks;
  - what confirms it;
  - what blocks it;
  - next action.
- Never display V2 `rank_score` as a probability.
- Show quantum contribution as incremental, neutral, fallback, or not useful.
- Show all six Akber stages with one plain-English decision.
- Show one Router/PaperOps answer per setup.
- Show Qadam-origin versus mirror-only trades.
- Ensure portfolio values agree across chart, cards, positions, and history.
- Show the self-refinement loop as proposals and version changes.
- Keep anti-slop, dedupe, harsh-language, freshness, and accessibility checks.
- Telegram notes remain short, specific, deduped, public-safe, and notify-only.

### Runtime Artifacts

- `data/runtime/qadam_operator_dashboard_view_model.json`
- `data/runtime/qadam_operator_dashboard_freshness.json`
- `data/runtime/qadam_operator_dashboard_truth_audit.json`
- `data/runtime/qadam_operator_communications_mirror.json`

### Acceptance

- The protected module/view route matrix and navigation behavior are unchanged
  unless an explicitly reviewed DP-0 amendment supersedes the contract.
- Exactly 13 protected routes and the canonical 10-stage lifecycle pass. A
  checker expecting 19 routes is stale and must fail as a checker defect, not
  force a dashboard regression.
- Lifecycle-copy checks use the canonical Stage 6 Akber labels while retaining
  the machine stage ID `filter_tradeability` for compatibility.
- Direct links, refresh persistence, desktop navigation, mobile navigation,
  and previous/next journey links pass characterization checks.
- All portfolio values agree.
- No stale artifact is shown as current without a stale label.
- No dashboard or Telegram authority exists.
- A non-technical reader can answer what Qadam found, whether it is tradeable,
  whether it traded, and what happens next.

### Operator Outcome

The operator can understand Qadam in minutes without reading JSON or logs.

## 31. OR-18 - Unattended Self-Healing Fund Operations

### Objective

Make "leave the laptop running" a robust operating mode rather than a hope.

### Extend

- `orchestrator/qadam_self_healing_supervisor.py`
- OR-1 research supervisor.
- PaperOps scheduler contracts.

### Build

- Replace the current projection-only control cycle with a due-job dispatcher
  that invokes approved runner entry points, captures structured receipts, and
  refreshes projections only after the underlying job completes or fails.
- The dispatcher must never import a broker client directly. Paper work is
  delegated only to `scripts/run_paperops_autonomous_pass.py` after OR-15
  release readiness and the explicit research-lock release.
- Keep long historical acquisition and backtests in resumable worker jobs so a
  15-second dashboard refresh or short control cycle cannot restart them.
- Separate services and cadences:
  - continuous or provider-safe source ingestion;
  - market-price refresh during relevant sessions;
  - pattern scoring after evidence refresh;
  - Akber/Router evaluation after score refresh;
  - guarded PaperOps pass on its existing controlled cadence;
  - lifecycle polling for open orders/positions;
  - daily attribution and dashboard refresh;
  - scheduled backtest/challenger research outside critical market work.
- Add launchd service templates with explicit operator installation.
- Add a service registry containing command, cadence, timeout, dependency,
  concurrency group, lock requirement, safety mode, last receipt, next due
  time, and permitted retry class for every runnable job.
- Record skipped work explicitly, including market closed, dependency not
  ready, research lock, stale prerequisite, cost budget exhausted, service
  already active, and no eligible work.
- Add liveness, readiness, and freshness probes.
- Add retry budgets and circuit breakers.
- Classify failures as:
  - transient provider/network;
  - rate limit;
  - credential/operator action;
  - parser/schema drift;
  - stale artifact;
  - disk/resource pressure;
  - interrupted resumable job;
  - code defect;
  - safety violation.
- Automatically retry only safe, idempotent refreshes.
- Queue precise repair requests for code or operator action.
- Add soak and interruption tests: network loss, sleep, SIGTERM, provider 429,
  malformed response, stale lock, disk threshold, local LLM unavailable,
  frontier provider unavailable, and quantum fallback.
- Keep local-LLM downtime degradable where deterministic processing can
  continue; block hypotheses that require missing semantic extraction.
- Keep PaperOps fail-closed whenever upstream evidence is stale or ambiguous.

### Runtime Artifacts

- `data/runtime/qadam_operator_service_status.json`
- `data/runtime/qadam_operator_service_heartbeats.json`
- `data/runtime/qadam_operator_repair_queue.json`
- `data/runtime/qadam_operator_retry_ledger.jsonl`
- `data/runtime/qadam_operator_soak_test.json`
- `data/runtime/qadam_operator_why_not_running.json`

### Acceptance

- Services restart after simulated interruption.
- Duplicate service instances are prevented.
- A real integration probe proves due acquisition, scoring, shadow, lifecycle,
  attribution, and dashboard jobs execute rather than only producing status
  projections.
- PaperOps is never invoked before OR-15 release readiness and explicit lock
  release; after release, one guarded no-order/eligible-order probe proves the
  canonical delegation path without a direct broker call from the supervisor.
- Safe retries do not duplicate data or orders.
- Code defects create repair requests rather than silent edits.
- Safety violations stop affected work.
- A minimum seven-real-session soak run keeps artifacts fresh and state
  consistent without simulated elapsed time.

### Operator Outcome

The operator can leave Qadam running and intervene only when the dashboard asks
for a specific action.

## 32. OR-19 - Final Certification And Paper Trial Resume

### Objective

Create one fail-closed checker that proves whether Qadam is ready for the
operator experience described in this plan.

### Build

Create:

```text
scripts/check_qadam_operator_ready_edge_engine.py
data/runtime/qadam_operator_ready_edge_engine_certification.json
```

The checker must evaluate separate certification groups.

### 32.1 Canonical Truth

- No source-count taxonomy contradiction.
- One paper-trial description.
- Lock, state, manifest, process, and dashboard agree.
- Required artifacts are fresh.
- Supplemental adapters distinguish live, sample, disabled, missing dependency,
  provider failure, and stale states.
- TradingView health cannot pass from local imports or fallback samples alone.

### 32.2 Research Operations

- Supervisor heartbeat fresh.
- OR-2R acquisition readiness and real provider pilot pass.
- Provider jobs active or complete.
- All sources and instruments classified.
- Historical data checksums and coverage pass.
- No unresolved critical acquisition defect.
- Provider licensing, cost, call, disk, and credential-action states are
  explicit and within the reviewed operating budget.

### 32.3 Evidence And Edge

- Point-in-time score tape exists.
- Score/label separation passes.
- Leakage violations equal zero.
- Walk-forward and holdout results exist.
- Multiple-testing audit exists.
- Strategy evidence maps derive from edge records.
- Any paper-review edge passes the frozen promotion policy.

### 32.4 Akber, Shadow, And Portfolio

- Critical Akber context missing count is zero for Router-eligible setups.
- Shadow evidence uses real elapsed time.
- Portfolio risk and concentration checks pass.
- Quantum state is honest and non-authoritative.

### 32.5 Router And PaperOps

- One Router state per setup.
- Only clean paper-review candidates reach handoff.
- The canonical autonomous PaperOps wrapper validates and consumes the same V3
  handoff, and every handoff has a consumption or rejection receipt.
- Research lock is released only through explicit audited readiness.
- Guarded Alpaca Paper is the only broker-write route.
- Idempotency, duplicate exposure, drawdown, source quorum, Q-CTRL, and
  reconciliation checks pass.

### 32.6 Lifecycle And Proof

- No ambiguous orders.
- Origin classification complete.
- Proof contains only Qadam-origin closed paper trades with full lineage.
- No backtest, shadow, fixture, mirror, or simulated record has proof credit.

### 32.7 Operator Experience

- Dashboard truth/freshness/portfolio parity pass against the protected V4
  13-route and 10-stage lifecycle contract.
- Telegram quality, dedupe, and safety pass.
- Self-healing soak test passes.
- Repair queue contains no unresolved critical item.
- The operator service has receipts proving due jobs execute; projection-only
  refreshes cannot satisfy unattended-operation readiness.

### 32.8 Universal Negative Safety Probes

- Live capital remains false.
- Live broker endpoints remain denied.
- Unauthorized broker write count is zero.
- LLM and quantum order authority remain false.
- Dashboard and Telegram command paths remain false.
- Simulated elapsed time remains false.
- Backtest/shadow proof credit remains zero.
- Forced-trade behavior remains absent.

### Release Procedure

1. Pass Research-Operational certification.
2. Pass OR-2R connection truth, provider matrix, and acquisition pilot.
3. Complete the real historical run.
4. Pass Edge-Validated certification.
5. Accumulate the required real-time shadow evidence.
6. Pass Paper-Operator-Ready certification.
7. Explicitly approve the strategy/risk versions and release the research lock.
8. Start the supervised autonomous paper operation.
9. Continue the actual `30-day paper growth trial` calendar without reset,
   backfill, or simulated elapsed time.
10. Accumulate Qadam-origin closed paper outcomes.
11. Evaluate Paper-Performance-Proven status separately.

If the current trial calendar expires while the research lock is active, record
the trial as research-interrupted or incomplete. Do not silently pause, extend,
backfill, or reset it. A new trial epoch requires an explicit operator decision
after Paper-Operator-Ready certification.

### Acceptance

- The checker reports pass, block, or degraded with explicit evidence.
- A pass never claims guaranteed profit.
- No phase is credited because files merely exist.
- Evidence-accrual phases require fresh records and real elapsed time.

## 33. Cross-Phase Engineering Requirements

### 33.1 Artifact Versioning

Every artifact must include:

- schema version;
- generated timestamp;
- source artifact references;
- code/model/prompt versions where relevant;
- dataset fingerprint;
- authority boundary;
- freshness state;
- validation state;
- permitted downstream consumers.

Breaking schema changes require a new version and migration or compatibility
reader. Do not silently reinterpret old records.

### 33.2 Idempotency

- Read/acquisition jobs use stable provider/partition IDs.
- Score jobs use stable dataset/feature/model/cutoff IDs.
- Label jobs use stable score/horizon/cost-model IDs.
- Backtests use stable protocol/dataset/model IDs.
- Paper handoffs use distinct Research Goal, candidate, setup, and idempotency
  identities.

### 33.3 Testing Pyramid

Each phase requires, where applicable:

- unit tests for transforms and policy;
- schema validation;
- deterministic fixture tests;
- property tests for score bounds and identity;
- negative safety probes;
- leakage tests;
- integration tests over a small end-to-end universe slice;
- resume/interruption tests;
- statistical sanity and negative-control tests;
- dashboard renderer and anti-slop tests;
- soak tests for unattended services.

### 33.4 Performance Budgets

- Stream partitions instead of loading full history.
- Bound local-LLM concurrency.
- Cache semantic extraction by content hash.
- Reserve frontier calls for high-value review.
- Pause bulk backtesting during latency-sensitive market work if resource
  contention appears.
- Maintain configurable CPU, memory, disk, provider-call, and daily-cost caps.
- Stop safely before disk exhaustion.

### 33.5 Security And Privacy

- Never print tokens or provider response secrets.
- Keep raw private payloads out of dashboard and Telegram.
- Sanitize exception messages.
- Keep bulk and runtime data ignored by Git.
- Do not move local secrets into manifests.
- Keep the public dashboard contract strictly sanitized and read-only.

### 33.6 Documentation Discipline

- Update the master plan when phase authority or sequence changes.
- Append implementation evidence to a dedicated implementation log.
- Distinguish implemented, operating, validated, and performance-proven.
- Never describe a scaffold or fixture as a live capability.

## 34. Operator Runbook After Implementation

The following are target commands and behavior. They do not all exist until the
corresponding phases are implemented.

### 34.1 Preflight

```bash
.venv/bin/python scripts/check_qadam_operator_ready_edge_engine.py --preflight
.venv/bin/python scripts/check_qadam_or3_acquisition_readiness.py
```

The second command must verify connection truth, reviewed provider coverage,
real pilot rows, ignored bulk storage, disk/cost limits, and resume safety. A
passing TradingView UI login or paid subscription is not a substitute.

### 34.2 Repair Supplemental TradingView Context

```bash
.venv/bin/python scripts/check_tradingview_mcp_adapter.py --live
```

This check may pass as intentionally disabled or unavailable when the rest of
the historical provider matrix is complete. It must not report connected from
sample data or imports alone. TradingView is not an OR-3 historical dependency.

### 34.3 Run The Provider Pilot

```bash
.venv/bin/python scripts/run_qadam_provider_backfill.py --pilot
```

Review measured coverage, licensing actions, projected provider calls, cost,
disk, and duration before starting the whole-universe run.

### 34.4 Start Or Resume OR-3 Acquisition

```bash
caffeinate -dimsu .venv/bin/python scripts/run_qadam_provider_backfill.py --resume
```

Keep PaperOps watch-only throughout acquisition. The runner checkpoints and may
take multiple days; do not restart completed partitions or fabricate elapsed
history.

### 34.5 Start Or Resume Continuous Research

```bash
caffeinate -dimsu .venv/bin/python scripts/run_qadam_research_supervisor.py --resume
```

Do this only after the provider pilot has passed and the long-running job
delegation path is implemented. Research may run while the research lock keeps
PaperOps watch-only.

### 34.6 Install The Explicit Local Service

```bash
./scripts/install_qadam_operator_launch_agent.sh
```

Installation must show the exact program, working directory, cadence, log
paths, and safety mode before loading the service.

### 34.7 Monitor

The dashboard should be sufficient. CLI fallback:

```bash
.venv/bin/python scripts/check_qadam_operator_service.py
```

### 34.8 Daily Operator Review

Check:

- service heartbeat;
- required source freshness;
- data and scoring lag;
- current strongest edge and confidence class;
- Akber and Router state;
- open orders and positions;
- daily and cumulative drawdown;
- unresolved repair requests;
- current "why not trading now" reason.

Do not change thresholds in response to one quiet day or one losing trade.

### 34.9 Weekly Review

- Compare historical, shadow, and paper performance.
- Review false positives and missed opportunities.
- Review source, model, Akber, quantum, Router, and execution attribution.
- Approve or reject challenger experiments.
- Review edge degradation and retirement proposals.
- Verify the paper proof ledger contains only eligible records.

### 34.10 Incident Response

- Provider outage: allow safe retry, then quarantine and review repair request.
- Credential issue: resolve manually without exposing or committing secrets.
- Parser/schema drift: stop affected source and create code-repair request.
- Stale market data: block scoring/trading for affected instruments.
- Supervisor crash: verify checkpoint, then resume.
- Broker ambiguity: stop paper writes and reconcile before retry.
- Safety violation: fail closed and require explicit review.

## 35. Modular Implementation Prompt Contract

Use one implementation prompt per phase. Every prompt should begin with:

```text
Work in /Users/raminhoodeh/Desktop/qadam. Read
docs/qadam-operator-ready-edge-engine-implementation-plan.md and the parent
docs/qadam-master-implementation-plan.md first. Implement only the requested
RF, DP, or OR phase. Preserve unrelated worktree changes and both repository
boundaries. Do not edit secrets, .env files, live credentials, broker live
endpoints, or live-capital settings. Preserve the actual 30-day paper growth
trial calendar without backfill or simulated elapsed time. Keep research,
backtest, shadow, dashboard, Telegram, LLM, and quantum outputs
non-authoritative. Keep all broker writes inside guarded Alpaca Paper PaperOps.
Preserve the current decision-flow dashboard navigation contract unless the
requested phase is an explicitly reviewed DP-0 amendment. Add the phase
artifacts, orchestrator code, checker, negative safety probes, tests,
implementation-log entry, dynamic-plan evidence update, and dashboard-safe
summary required by the plan. Run relevant checks. Do not implement later
phases. Do not claim evidence has accumulated merely because code or fixtures
exist.
```

Pre-OR phase-specific requests:

1. **RF-0:** Capture the root and nested worktree baseline, runtime and safety
   state, refactor scope, and current rendered dashboard route/navigation
   behavior. Do not refactor code or clean either worktree.
2. **DP-0:** Implement controlled dynamic-plan status, append-only phase
   evidence, drift detection, amendment proposals, idempotent status refresh,
   and explicit reviewed amendment application. Automatic normative edits must
   fail closed.
3. **RF-1:** Produce a no-change architecture, import, command, artifact
   producer/consumer, and end-to-end edge-path audit. Classify canonical,
   compatibility, experimental, fixture-only, superseded, and safety-critical
   components without moving code.
4. **RF-2:** Build characterization and negative-safety regression coverage for
   PaperOps, authority, provenance, proof, calendar, Telegram, portfolio truth,
   and every current dashboard route and navigation behavior.
5. **RF-3:** Introduce canonical typed edge-path contracts, artifact ownership,
   atomic storage/status services, provenance classes, and compatibility
   readers while preserving characterized behavior and defense-in-depth.
6. **RF-4:** Refactor provider, storage, job, feature, score, label, backtest,
   and edge-promotion boundaries behind interfaces. Do not perform provider-
   backed acquisition or claim the local sample baseline as historical proof.
7. **RF-5:** Refactor Strategy Foundry, Akber, risk, Router, PaperOps handoff,
   lifecycle, and attribution boundaries without changing decisions or making
   order calls. Preserve every existing guarded-paper gate.
8. **RF-6:** Migrate edge-path consumers, quarantine superseded producers,
   re-run the full baseline and safety harness, generate plan-drift proposals,
   and record an explicitly reviewed post-refactor rebaseline. Do not mass-
   delete legacy code.

Edge-engine phase-specific requests:

1. **OR-0:** Implement canonical truth, source-count taxonomy, paper-trial
   wording reconciliation, runtime state audit, and safety baseline.
2. **OR-1:** Implement the research supervisor, atomic state, single-instance
   lease, heartbeat, interruption-safe resume, and launchd templates without
   silently installing or starting services.
3. **OR-2:** Implement source freshness policy and historical provider
   capability registry, including quarantine and repair classifications.
4. **OR-2R:** Repair TradingView and supplemental connection truth, build the
   reviewed 19-instrument and source-history provider coverage/purchase matrix,
   execute a real provider-backed pilot, and certify OR-3 acquisition readiness.
   Do not purchase plans, edit credentials, or start the whole-universe run.
5. **OR-3:** Implement and run real provider-backed historical source and price
   acquisition with partitioned jobs, rate/cost/disk limits, checksums,
   idempotent resume, typed unavailable windows, and local bulk storage. Do not
   use TradingView UI entitlements as historical API coverage.
6. **OR-4:** Implement point-in-time alignment, relationship eligibility,
   duplicate-source clustering, typed missing-window reasons, and leakage audit.
7. **OR-5:** Implement Pattern Score V3 and its explainable feature registry,
   preserving V2 rank score as research ranking only.
8. **OR-6:** Implement the resumable historical point-in-time score-tape runner
   with score/label separation.
9. **OR-7:** Implement forward outcome labels, execution-proxy mapping, overlap
   controls, and versioned transaction-cost models.
10. **OR-8:** Implement walk-forward whole-universe backtesting, baselines,
   negative controls, holdout evaluation, and multiple-testing correction.
11. **OR-9:** Implement nonlinear and quantum/classical incremental-value
    experiments with honest fallback and overfit controls.
12. **OR-10:** Implement the edge registry, promotion classes, strategy evidence
    maps, retirement proposals, and new-family proposals.
13. **OR-11:** Implement Strategy Foundry V3 with complete edge/Research Goal
    lineage, identity, instrument mapping, invalidation, risk concept, expiry,
    and rejection records.
14. **OR-12:** Implement Akber Filter V3, complete context assembly, six-stage
    mapping, historical replay, ablation, threshold proposals, and explanations.
15. **OR-13:** Implement continuously supervised real-time shadow validation,
    decision freezing, outcomes, calibration, counterfactuals, and promotion
    readiness without orders or proof.
16. **OR-14:** Implement deterministic portfolio construction, correlation and
    concentration controls, volatility/risk sizing, stress tests, and risk
    rejection records.
17. **OR-15:** Implement Router V3, one canonical V3 handoff reader consumed by
    the autonomous PaperOps wrapper, lock-release readiness, consumption
    receipts, and all duplicate/drawdown/quorum/Q-CTRL/idempotency guards.
18. **OR-16:** Implement lifecycle V3, origin classification, complete lineage,
    postmortems, proof eligibility, performance, and attribution.
19. **OR-17:** Implement the operator dashboard and Telegram view models while
    preserving the V4 13-route/10-stage protected contract and all read-only
    boundaries.
20. **OR-18:** Implement an actual due-job operator service, safe retry/circuit
    breakers, repair queue, launchd integration, interruption tests, and real
    multi-session soak certification. Projection-only cycles do not pass.
21. **OR-19:** Implement the final multi-level certification checker and release
    procedure. Do not release the research lock or start a paper operation
    unless every required real-evidence gate passes.

## 36. Recommended Execution Rhythm

The original implementation waves have produced most architecture modules and
checkers. The current re-entry order is evidence-led:

1. refresh OR-0 through OR-2 structural checks without reimplementing them;
2. implement and pass OR-2R;
3. run OR-3 to real provider-backed completion/classification;
4. rerun OR-4 through OR-12 against empirical datasets, repairing modules that
   only passed fixture or implementation gates;
5. run OR-13 over real elapsed market time;
6. connect OR-15 handoffs to canonical PaperOps, then verify OR-14 through
   OR-16 on real paper candidates and outcomes;
7. keep the current dashboard structure while replacing stale projections with
   canonical empirical and liveness state;
8. make OR-18 execute due jobs, install it explicitly, and pass the soak;
9. pass OR-19 before releasing autonomous paper operation.

Do not repeat Wave 0 refactoring unless a current checker identifies a concrete
regression. “Passed implementation” phases must be re-evaluated against real
data but should not be cloned into new V4 modules by default.

### Build Wave 0 - Refactor, Protect, And Rebaseline

Implement RF-0, DP-0, and RF-1 through RF-6 before OR-0. This wave audits the
current system before changing it, freezes intended behavior, introduces
canonical contracts and ownership, separates research from execution, protects
the newly routed dashboard, quarantines legacy paths, and then asks the dynamic
plan to reconcile its assumptions with the refactored checkout. OR-0 remains
blocked until the post-refactor baseline and reviewed plan rebaseline pass.

### Build Wave A - Make Research Actually Run

Refresh OR-0 through OR-2, implement OR-2R, and then run OR-3 and OR-4. Let the
provider-backed acquisition run until the eligible historical substrate is
sufficient and all unavailable history is classified.

### Build Wave B - Define And Test The Signal

Implement OR-5 through OR-10. This is where Qadam learns whether any strategy
contains a defensible edge.

### Build Wave C - Make Edge Trade-Shaped

Implement OR-11 through OR-14. This turns validated research into complete,
current, portfolio-aware paper-review setups.

### Build Wave D - Restore Guarded Paper Operation

Implement OR-15 and OR-16. Release PaperOps only after evidence and safety gates
pass.

### Build Wave E - Become An Operator-Ready Fund

Implement OR-17 through OR-19, install the explicit supervisor, complete the
real-time soak, and continue the actual paper calendar.

## 37. Program Risk Register

| Risk | Failure Mode | Required Mitigation |
| --- | --- | --- |
| Historical availability bias | Only easy-to-download sources appear useful | Provider capability registry, unavailable-source labels, and forward validation |
| Subscription/API confusion | A charting-plan or exchange-display entitlement is mistaken for programmatic historical access | OR-2R provider matrix, official-interface verification, and pilot before purchase |
| Supplemental adapter false health | Imports or sample fixtures appear as a live TradingView connection | Explicit connection states, real-response probe, fixture isolation, and freshness checks |
| Data licensing mismatch | Research or later commercial use exceeds provider permissions | Per-dataset licensing metadata, operator review, and no automated purchases or terms acceptance |
| Lookahead leakage | Revised or future information enters a historical score | `available_at` enforcement, vintage data, score/label separation, and negative probes |
| Multiple testing | Thousands of combinations manufacture attractive results | Test registry, false-discovery correction, holdout, and negative controls |
| Dependent samples | Overlapping windows inflate apparent sample size | Purging, embargo, event clustering, and effective sample size |
| Survivorship bias | Current instruments/sources make history look cleaner | Delisted/changed-symbol audit and period-appropriate universe manifests |
| Regime overfit | Edge works only in one unusual period | Regime slices, walk-forward folds, concentration limits, and decay monitoring |
| Transaction-cost error | Gross edge disappears after spread and slippage | Versioned cost model, sensitivity analysis, and paper execution attribution |
| Proxy mismatch | Research instrument and paper instrument behave differently | Explicit research/execution proxy mapping and basis-risk measurement |
| Source dependence | Many apparent sources repeat one original report | Content clustering and independent-source quorum |
| Source timestamp ambiguity | Publication and event times are confused | Separate event/published/available/ingested/revised timestamps |
| LLM nondeterminism | Historical features change when a model or prompt changes | Structured schemas, caching, prompt/model versioning, and deterministic reruns |
| Frontier-model cost or outage | Research loop stalls or becomes uneconomic | Sparse challenge calls, caching, budget caps, and local/deterministic fallback |
| Quantum theatre | Complexity is mistaken for added predictive value | Matched classical baseline and incremental-value requirement |
| Edge crowding or decay | Previously valid relationship stops working | Drift monitors, challenger tests, allocation reduction, and retirement policy |
| Portfolio concentration | Different setups express the same underlying bet | Correlation clusters and aggregate strategy/source/instrument caps |
| Over-filtering | Akber removes both bad and good trades | Historical ablation, missed-opportunity tracking, and threshold sensitivity |
| Under-filtering | Weak current setups pass because history looked strong | Complete live context, freshness expiry, and critical-stage vetoes |
| Laptop interruption | Sleep, reboot, disk, network, or thermals stop the loop | launchd, heartbeat, checkpointing, disk guards, and safe resume |
| Projection-only automation | Status artifacts refresh while no acquisition, scoring, shadow, lifecycle, or PaperOps job runs | Due-job receipts, worker heartbeats, integration probes, and soak acceptance |
| Router/PaperOps split brain | A V3 handoff exists but the canonical autonomous wrapper never consumes it | One guarded handoff reader, consumption receipts, and no alternate submitter |
| State contradiction | Dashboard, lock, manifest, and runner disagree | Atomic writes, canonical truth contract, and consistency certification |
| Proof contamination | Mirror, fixture, backtest, or shadow records count as results | Origin classification and strict closed Qadam-origin lineage requirement |
| Operator overreaction | Thresholds change after a small win/loss sequence | Frozen policies, scheduled review, and champion/challenger process |
| No real edge exists | System is operational but cannot justify a trade | Report honestly, preserve capital, expand research carefully, and do not force trades |

## 38. Time And Evidence Reality

The program has three different kinds of duration.

### 38.1 Implementation Time

RF-0, DP-0, RF-1 through RF-6, and OR-0 through OR-19 are modular engineering
phases and can be implemented one prompt at a time. Each phase should end with
code, checks, artifacts, a dynamic-plan evidence update, and a log entry, but
that does not imply its empirical evidence gate has matured.

### 38.2 Compute And Acquisition Time

OR-2R, OR-3, OR-4, OR-6, OR-7, OR-8, and OR-9 require actual provider checks,
data acquisition, or computation. On the current M5 laptop with 24 GB RAM and
1 TB storage:

- the OR-2R pilot should complete before any multi-day run or data purchase;
- a narrow price and source slice should complete in minutes to hours;
- the initial provider-backed universe may require one to five days;
- rate-limited or archive-heavy sources may take longer;
- intraday, options, order-flow, or large semantic extraction runs may require
  separate staged passes;
- provider availability, not CPU speed, is likely to dominate elapsed time.

The runner must checkpoint rather than promise a fixed finish time.

### 38.3 Real Market Time

OR-13 forward shadow evidence, OR-16 Qadam-origin paper outcomes, and Paper-
Performance-Proven certification require future market events. They cannot be
completed overnight, generated from fixtures, or backfilled from a later
perspective.

The operator may reach Research-Operational before an edge is validated, and
Paper-Operator-Ready before enough closed paper trades exist for Paper-
Performance-Proven status. The dashboard must show those distinctions.

## 39. Final Completion Definition

Qadam is finalised for this paper-only operator stage only when all of the
following are true:

- The edge path has one audited canonical architecture, one owner per canonical
  artifact, clean research/decision/execution boundaries, and no active
  superseded producer that can overwrite canonical state.
- The post-refactor behavior diff, PaperOps equivalence checks, safety probes,
  portfolio truth checks, and dashboard route characterization all pass.
- The dynamic plan state is fresh and traceable to phase checkers; automatic
  edits remain confined to its status block; normative amendments are explicit,
  reviewed, and logged.
- One supervised service is active and restart-safe.
- The supervised service has fresh receipts proving it executes due jobs, not
  merely status and dashboard projections.
- Source and market freshness is continuously measured.
- TradingView and every other supplemental adapter report truthful origin,
  dependency, live/sample, delay, and freshness states. TradingView may remain
  intentionally unavailable without blocking OR-3 when licensed historical
  providers cover the required datasets.
- The reviewed provider matrix covers all 19 instruments and intended source
  histories; the provider-backed pilot has passed before the full run.
- Historical source and price acquisition is real, provider-backed where
  available, resumable, and complete enough for promoted edges.
- Point-in-time score tapes are separate from future labels.
- Backtests are walk-forward, cost-aware, leakage-safe, and false-discovery
  controlled.
- At least one edge reaches the validated promotion class required for forward
  shadow and paper review. If none qualifies, Qadam may be Research-Operational
  but is not finalised as Paper-Operator-Ready.
- The five core strategies are evidence-labelled rather than assumed.
- Strategy-agnostic discovery can propose emerging families when a validated
  relationship falls outside the five core strategies; the core families do
  not limit the search universe.
- Quantum/nonlinear value is incremental, measured, and non-authoritative.
- Strategy hypotheses have full lineage, invalidation, expiry, and paperability.
- Akber has complete practical context and calibrated thresholds.
- Forward shadow evidence uses real elapsed time.
- Portfolio risk controls concentration, drawdown, liquidity, and uncertainty.
- Router emits one state per setup.
- Only clean paper-review candidates reach guarded PaperOps.
- Router V3 and the canonical PaperOps wrapper share one validated handoff
  contract with a receipt for every consumption or rejection.
- Every paper order has distinct identity and idempotency.
- Every order and position has an unambiguous lifecycle.
- Only Qadam-origin closed paper trades with complete lineage enter the paper
  proof ledger.
- The dashboard preserves the current V4 13-route structure and one canonical
  10-stage lifecycle across Qadam Team, Fund, Observe, Find Patterns, Test &
  Decide, Trade, Learn & Improve, and System. Dashboard and Telegram outputs
  are fresh, clear, deduped, public-safe, and read-only.
- Self-healing safely retries ordinary failures and requests help for code,
  credential, policy, or safety defects.
- The actual `30-day paper growth trial` calendar is preserved.
- Live capital, live broker endpoints, forced trades, unauthorized proof, and
  command authority remain disabled.
- `scripts/check_qadam_operator_ready_edge_engine.py` passes the appropriate
  certification level from fresh evidence.

Completion of this plan authorizes guarded autonomous **paper** operation only.
It does not certify a commercially distributable product, regulated investment
service, unattended customer deployment, or live-capital system. Those require
a separate program after Paper-Performance-Proven evidence exists.

The honest final operator statement is:

```text
Qadam is running unattended in guarded paper mode. It is collecting fresh
evidence, scoring patterns point in time, validating edges against historical
and forward outcomes, filtering current tradeability, routing only complete
paper-review setups, and learning from attributable closed paper trades. It may
still choose not to trade when no positive-expectancy setup passes every gate,
and no future return is guaranteed.
```
