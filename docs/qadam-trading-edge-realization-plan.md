# Qadam Trading Edge Realization Implementation Plan

This appendix turns Qadam's stated trading edge into a staged implementation path.

It does not replace the master implementation plan or the remaining-slices plan. It is the practical bridge from "Qadam has an architectural edge" to "Qadam can repeatedly produce fresh, distinct, evidence-backed paper trades when the market gives it permission."

## 1. Objective

Qadam already has the important safety and architecture pieces:

- live and replayable data sources;
- Research Goals before trade candidates;
- Local Research Analyst compression;
- Strategy Lead challenge packets;
- Head of Quant shadow annotation;
- Signal Integrity, Risk Agent, Execution Policy, kill-switch, idempotency, broker-readiness, and Event Log gates;
- guarded Alpaca paper submission;
- dashboard and Telegram visibility;
- postmortem and learning-loop scaffolding.

The remaining edge problem is quality and throughput:

- Qadam should create more fresh, distinct candidate setups from its observations.
- Qadam should stop over-suppressing real differences as duplicates.
- Qadam should route each idea into the right strategy family.
- Qadam should require market confirmation before risk.
- Qadam should size, exit, and learn from paper trades more intelligently.
- Qadam should explain the whole chain clearly to Fund Managers.

Full potential means Qadam is not blocked by stale contradictions when a valid paper setup exists. It does not mean forced trading, live capital, dashboard execution, Telegram execution, LLM risk approval, or quantum-originated orders.

## 2. Non-Negotiable Boundary

This plan must preserve the first-release operating boundary:

- `live_capital_enabled=false`.
- Alpaca paper is the only first-release broker-write rail.
- Paper orders can only be submitted through guarded PaperOps.
- Dashboard and Telegram remain non-executable.
- Local LLM and Frontier LLM cannot approve risk.
- Head of Quant cannot create a trade, approve risk, submit hardware jobs, or call a broker route.
- Quantum output remains `shadow_annotation`.
- No forced trades when source quorum, market confirmation, risk, idempotency, or execution policy fails.
- A daily trade target is a discipline target, not a ceiling, and not permission to bypass gates.
- Paper-submit retries can only reuse the same idempotency key under the configured timeout/429/5xx policy.

## 3. Target Runtime Flow

```text
Live source observation / durable replay
  -> Research Goal
  -> Fresh setup identity
  -> Trade Candidate Factory
  -> Strategy Router
  -> Market Confirmation Layer
  -> Signal Integrity Gate
  -> Strategy Lead challenge
  -> Head of Quant shadow annotation
  -> Risk Agent sizing
  -> Execution Policy and kill-switch review
  -> Event Log prewrite and idempotency guard
  -> Guarded Alpaca paper submit
  -> Paper lifecycle mirror
  -> Exit Intelligence
  -> Postmortem
  -> Learning-loop proposal
  -> Dashboard and Telegram readout
```

No stage creates authority alone. Authority exists only when every downstream paper-only gate passes.

## 4. Current Bottleneck Class

The design target is not basic connectivity. The current bottleneck class is downstream quality:

- too few fresh eligible candidates compared with the number of observations and Research Goals;
- broad duplicate/idempotency holds that can suppress legitimately distinct setups;
- uneven mapping from Qadam's worldview and data sources into tradable strategy families;
- missing market-confirmation depth for price, volume, volatility, options, and positioning;
- weak dynamic sizing and exit intelligence relative to Qadam's paper-growth objective;
- learning-loop proposals that do not yet feed back into candidate quality quickly enough.

This plan fixes that without weakening the safety chain.

## 5. Stage TE-0 - Edge Contract And Baseline

Objective: define the contract for "better trading" before changing behavior.

Build:

- Add a Trading Edge contract that reports:
  - source observations seen;
  - Research Goals created;
  - fresh setup identities created;
  - candidate factory proposals;
  - candidates blocked by missing evidence;
  - candidates blocked by duplicate/idempotency;
  - candidates blocked by risk;
  - candidates eligible for paper;
  - paper orders submitted;
  - exits generated;
  - postmortems completed;
  - learning proposals created.
- Add a public-safe dashboard summary:
  - what Qadam is looking for;
  - why it is or is not trading;
  - what the next unlock is;
  - which constraints are safety constraints versus opportunity scarcity.
- Add a regression checker that fails if historical blockers are mixed with current blockers.

Likely files:

- `orchestrator/trading_edge_contract.py`
- `orchestrator/cockpit_status.py`
- `scripts/check_trading_edge_contract.py`
- `scripts/check_cockpit_status.py`
- `landing-page-repo/dashboard.js`

Acceptance:

- Fund Managers can see whether Qadam is blocked by safety, missing data, risk, duplicate identity, or no fresh setup.
- No paper authority changes.
- No live-capital path appears.

## 6. Stage TE-1 - Fresh Setup Identity v2

Objective: stop treating every similar idea as the same trade, while still blocking true duplicates.

Problem:

The current idempotency guard correctly prevents duplicate paper submits, but Qadam needs a richer identity model so two distinct catalysts in the same theme can both progress if their evidence, timing, instrument, or invalidation is different.

Build a `FreshSetupIdentity` with:

- `setup_id`;
- `research_goal_id`;
- `candidate_id`;
- `strategy_family`;
- `instrument`;
- `side`;
- `catalyst_type`;
- `catalyst_timestamp`;
- `catalyst_window`;
- `evidence_hash`;
- `source_quorum_hash`;
- `worldview_lens`;
- `akber_stage`;
- `market_regime`;
- `price_regime`;
- `entry_zone`;
- `invalidation_level`;
- `profit_target_zone`;
- `time_stop`;
- `portfolio_exposure_bucket`;
- `idempotency_namespace`;
- `duplicate_of`;
- `freshness_reason`.

Rules:

- Same instrument + same side + same catalyst window + same evidence hash + same entry zone = duplicate.
- Same broad theme but different catalyst, evidence hash, instrument, expiry, or invalidation = eligible for separate evaluation.
- A fresh identity can still be blocked by source quorum, market confirmation, risk, portfolio exposure, or execution policy.

Likely files:

- `orchestrator/fresh_setup_identity.py`
- `orchestrator/trade_intent.py`
- `orchestrator/paperops_active_paper_trading_automation.py`
- `scripts/check_fresh_setup_identity.py`

Acceptance:

- True duplicate orders remain blocked.
- Distinct candidates in the same theme are not collapsed accidentally.
- Every PaperOps paper-submit attempt has a stable setup identity and idempotency namespace.

## 7. Stage TE-2 - Trade Candidate Factory

Objective: increase the conversion rate from Research Goals to candidate proposals without creating orders prematurely.

Build:

- A candidate factory that consumes:
  - Research Goals;
  - source observations;
  - market context packets;
  - Strategy Lead challenge packets;
  - Head of Quant shadow annotations;
  - current portfolio exposure;
  - recent postmortem lessons.
- Candidate states:
  - `proposed`;
  - `needs_market_confirmation`;
  - `needs_strategy_challenge`;
  - `passed_to_signal_integrity`;
  - `blocked_missing_evidence`;
  - `blocked_contradiction`;
  - `blocked_duplicate_identity`;
  - `blocked_risk`;
  - `expired`;
  - `paper_eligible`.
- Required candidate fields:
  - `candidate_id`;
  - `research_goal_id`;
  - `fresh_setup_id`;
  - `strategy_family`;
  - `instrument`;
  - `side`;
  - `thesis`;
  - `evidence_refs`;
  - `source_quorum`;
  - `market_confirmation_refs`;
  - `worldview_prior`;
  - `akber_filter_state`;
  - `invalidation`;
  - `entry_condition`;
  - `exit_condition`;
  - `risk_hint`;
  - `blocked_reason`;
  - `paper_order_allowed=false` until downstream gates pass.

Likely files:

- `orchestrator/trade_candidate_factory.py`
- `orchestrator/research_goal.py`
- `orchestrator/market_context.py`
- `scripts/check_trade_candidate_factory.py`

Acceptance:

- Every candidate has Research Goal lineage.
- Every candidate has a fresh setup identity.
- Every blocked candidate gives a clear next unlock.
- Candidate creation does not create paper-order authority.

## 8. Stage TE-3 - Strategy Router

Objective: route each candidate into the right trading philosophy instead of scoring all ideas the same way.

Strategy families:

1. Akber catalyst/mispricing setup.
2. Second-order AI infrastructure beneficiary setup.
3. Energy and crude geopolitical setup.
4. Defence and security repricing setup.
5. Silver, rates, liquidity, and monetary stress setup.
6. Semiconductor supply-chain setup.
7. Prediction-market probability gap setup.
8. Earnings/post-earnings drift setup.
9. Opening-range breakout or volatility breakout setup.
10. Trend-following baseline control setup.
11. Options/flow dislocation setup.
12. Physical/logistics anomaly setup.

Build:

- A `strategy_family` registry with:
  - required sources;
  - allowed instruments;
  - confirmation rules;
  - expiry rules;
  - invalidation defaults;
  - max risk;
  - preferred holding period;
  - relevant Akber stages;
  - worldview priors;
  - postmortem weighting.
- Router output:
  - primary strategy family;
  - secondary strategy family;
  - why this family fits;
  - why other families were rejected;
  - minimum evidence still required.

Likely files:

- `orchestrator/strategy_router.py`
- `orchestrator/strategy_research_intake.py`
- `skills/akber-6-stage-filter/`
- `skills/private-edge-world-model-priors/`
- `scripts/check_strategy_router.py`

Acceptance:

- No candidate reaches Signal Integrity without a strategy family.
- Dashboard can explain the strategy Qadam is applying in plain language.
- Strategy choice is logged and replayable.

## 9. Stage TE-4 - Second-Order AI Infrastructure Universe

Objective: make the AI infrastructure beneficiary thesis tradable without turning it into a loose theme.

Worldview:

Qadam should treat obvious AI leaders as reference assets and look for bottleneck beneficiaries around the buildout: power generation, grid hardware, data-centre electrical infrastructure, cooling, semiconductor fabrication capacity, memory, connectivity, networking, fibre, copper, and strategic energy/security infrastructure.

Build:

- Create a tradable universe registry:
  - power generation;
  - grid equipment;
  - data-centre electrical infrastructure;
  - cooling and thermal management;
  - semiconductor fabrication equipment;
  - advanced packaging;
  - memory;
  - networking;
  - fibre/connectivity;
  - copper and electrical metals;
  - energy security;
  - defence-adjacent compute/security infrastructure.
- Map each bucket to:
  - example tickers;
  - sector/industry metadata;
  - relevant macro drivers;
  - source feeds;
  - confirmation rules;
  - risk limits;
  - stale thesis conditions.
- Add a candidate-generation rule:
  - "AI leader move is not a trade by itself; ask which constrained supplier or infrastructure layer is mispriced."

Likely files:

- `orchestrator/ai_infrastructure_universe.py`
- `orchestrator/strategy_router.py`
- `docs/qadam-trading-strategy-research-notes.md`
- `landing-page-repo/dashboard.js`

Acceptance:

- Dashboard shows the AI infrastructure lens as a strategy context, not as proof.
- Candidates from this thesis must name the specific bottleneck and instrument.
- The thesis cannot bypass source quorum, market confirmation, or risk.

## 10. Stage TE-5 - Market Confirmation Layer

Objective: make candidates price-aware before they reach risk.

Build:

- A market confirmation packet for each candidate:
  - current price;
  - recent return;
  - volume and relative volume;
  - volatility;
  - opening-range state where applicable;
  - trend state;
  - options/flow context where available;
  - spread/liquidity proxy;
  - sector/peer move;
  - news/catalyst timestamp;
  - prediction-market probability where relevant;
  - data freshness and provider health.
- Prioritize current sources:
  - Alpaca read-only mirror and market data where available;
  - Yahoo/yfinance supplemental market context;
  - TradingView MCP and paid alert receiver;
  - FRED and macro context;
  - Polymarket/Kalshi where available;
  - UnusualWhales once credentialed;
  - provider-specific adapters added later.

Likely files:

- `orchestrator/market_context.py`
- `orchestrator/yahoo_market_data.py`
- `orchestrator/tradingview_alerts.py`
- `orchestrator/signal_integrity.py`
- `scripts/check_market_confirmation_layer.py`

Acceptance:

- No candidate is treated as paper-eligible without market confirmation.
- Missing market data is a visible blocker, not a silent failure.
- Market confirmation is read-only and cannot submit orders.

## 11. Stage TE-6 - Dynamic Risk Sizing

Objective: size paper trades according to evidence, volatility, drawdown, conviction, and portfolio state.

Build:

- A risk-sizing model with:
  - base risk per trade;
  - max paper exposure per strategy family;
  - max paper exposure per instrument;
  - max correlated exposure;
  - drawdown throttle;
  - volatility scaling;
  - source-quality scaling;
  - market-confirmation scaling;
  - Strategy Lead disagreement penalty;
  - Head of Quant ambiguity penalty;
  - postmortem performance adjustment;
  - open-position crowding penalty.
- Sizing output:
  - risk amount;
  - quantity;
  - stop/invalidation;
  - expected loss if invalidated;
  - paper portfolio impact;
  - reason for size increase/decrease;
  - `live_capital_enabled=false`.

Likely files:

- `orchestrator/dynamic_risk_sizing.py`
- `orchestrator/risk_agent.py`
- `orchestrator/paper_account.py`
- `scripts/check_dynamic_risk_sizing.py`

Acceptance:

- Paper size is no longer a static placeholder when evidence is strong.
- Risk can increase only inside configured paper limits.
- Every size decision is explainable on the dashboard.

## 12. Stage TE-7 - Exit Intelligence

Objective: make Qadam as disciplined about exits as entries.

Exit triggers:

- invalidation level hit;
- catalyst window expired;
- target achieved;
- partial profit rule hit;
- source contradiction appears;
- market confirmation deteriorates;
- volatility compression after catalyst;
- Strategy Lead downgrade;
- Head of Quant ambiguity downgrade;
- portfolio drawdown throttle;
- time stop;
- stale position without live thesis.

Build:

- Exit review packet per open position.
- Link exits to:
  - original Research Goal;
  - original candidate;
  - original market context;
  - current market context;
  - current portfolio state;
  - postmortem readiness.
- Paper close route remains guarded and paper-only.

Likely files:

- `orchestrator/exit_intelligence.py`
- `orchestrator/paperops_paper_exit_path.py`
- `orchestrator/paper_lifecycle_portfolio_postmortem.py`
- `scripts/check_exit_intelligence.py`

Acceptance:

- Every open position has an exit state.
- Exit reviews are visible even when no close is allowed.
- Paper closes remain gated and idempotent.

## 13. Stage TE-8 - Postmortem-Driven Weight Updates

Objective: let Qadam learn from closed paper trades without silently mutating policy.

Build:

- Postmortem fields:
  - what Qadam believed;
  - what sources supported it;
  - what sources contradicted it;
  - strategy family;
  - Akber filter outcome;
  - market confirmation outcome;
  - risk sizing quality;
  - entry quality;
  - exit quality;
  - P&L;
  - missed opportunity;
  - avoidable error;
  - repeatable edge;
  - proposed changes.
- Learning proposal types:
  - trust-score adjustment;
  - strategy-family weight adjustment;
  - risk-sizing adjustment;
  - source-priority adjustment;
  - dashboard/operator warning;
  - no change.
- Require explicit review for any policy-changing learning proposal.

Likely files:

- `orchestrator/postmortem_learning.py`
- `orchestrator/rs9_learning_loop.py`
- `orchestrator/paper_lifecycle_portfolio_postmortem.py`
- `scripts/check_postmortem_learning.py`

Acceptance:

- Every closed paper trade has a postmortem queue state.
- Learning proposals are visible but not self-applied unless the current gate allows it.
- Failed trades improve future candidate filtering.

## 14. Stage TE-9 - Durable Replay Watchdog

Objective: stop durable replay from quietly falling offline.

Build:

- A watchdog that checks:
  - Postgres/Timescale reachable;
  - latest source observation timestamp;
  - replay coverage by canonical source;
  - JSONL fallback freshness;
  - dashboard public snapshot freshness;
  - paper-runner status;
  - automation heartbeat;
  - provider 429/degraded states.
- If Timescale is offline:
  - mark durable replay degraded;
  - keep JSONL fallback visible;
  - block any source-quality claim that depends on durable replay;
  - do not block paper trades if current source quorum and market confirmation are otherwise satisfied.

Likely files:

- `orchestrator/durable_replay_watchdog.py`
- `scripts/check_durable_replay_watchdog.py`
- `scripts/check_postgres_timescale_replay.py`
- `orchestrator/cockpit_status.py`

Acceptance:

- Dashboard says exactly whether durable replay is online, stale, partial, or offline.
- No hidden replay failure affects candidate quality without a visible reason.
- Durable replay is helpful context, not a global trade blocker by itself.

## 15. Stage TE-10 - Idle-State Diagnosis

Objective: make Qadam explain non-trading states like an operator, not a black box.

Build:

- A single `why_not_trading_now` tree:
  - no fresh observation;
  - Research Goal not candidate-ready;
  - missing source quorum;
  - missing market confirmation;
  - Strategy Lead hold;
  - Head of Quant ambiguity hold;
  - Signal Integrity block;
  - Risk Agent block;
  - portfolio exposure block;
  - duplicate idempotency block;
  - paper-submit route inactive;
  - broker/paper mirror degraded;
  - rate limit/backoff;
  - no current market session;
  - open order pending fill;
  - no exit candidate.
- Add dashboard copy:
  - "Qadam is allowed to trade paper, but it is idle because..."
  - "The next thing that would unlock a trade is..."
  - "This is a safety block / opportunity block / data block / duplicate block."

Likely files:

- `orchestrator/idle_state_diagnosis.py`
- `orchestrator/cockpit_status.py`
- `landing-page-repo/dashboard.js`
- `scripts/check_idle_state_diagnosis.py`

Acceptance:

- Fund Managers can understand why Qadam is not trading without reading logs.
- The diagnosis matches backend artifacts, not frontend inference.
- Idle state cannot hide a stale contradiction.

## 16. Stage TE-11 - Paper Autonomy Certification Refresh

Objective: certify the full edge loop after TE-1 through TE-10.

Build:

- A final check that verifies:
  - paper mode only;
  - live capital disabled;
  - fresh setup identity active;
  - candidate factory active;
  - strategy router active;
  - market confirmation active;
  - dynamic risk sizing active;
  - exit intelligence active;
  - postmortem learning active;
  - durable replay watchdog active;
  - idle-state diagnosis active;
  - dashboard public snapshot active;
  - Telegram readout safe;
  - multiple paper trades per day allowed when distinct qualified setups pass;
  - no forced trades when gates fail.

Likely files:

- `scripts/check_trading_edge_realization_certification.py`
- `orchestrator/cockpit_status.py`
- `docs/qadam-master-implementation-plan.md`

Acceptance:

- Qadam is certified as paper-autonomous for fresh, distinct, gated paper setups.
- Blockers are limited to real opportunity, data, provider, risk, market-session, or safety constraints.
- No contradiction remains where one layer says paper trading is allowed while another layer says all paper trading is globally disabled.

## 17. Dashboard Outcome

After this plan, Mission Control should answer five questions at the top of the dashboard:

1. What is Qadam watching?
2. What strategy family is Qadam currently applying, and why?
3. What fresh candidate setups exist?
4. Why is Qadam trading, waiting, or blocked?
5. What did Qadam learn from recent paper trades?

The detailed sections can remain segmented, but the first screen should show the operating truth.

## 18. Implementation Order

Recommended order:

1. TE-0 Edge Contract And Baseline.
2. TE-1 Fresh Setup Identity v2.
3. TE-2 Trade Candidate Factory.
4. TE-3 Strategy Router.
5. TE-5 Market Confirmation Layer.
6. TE-4 Second-Order AI Infrastructure Universe.
7. TE-6 Dynamic Risk Sizing.
8. TE-7 Exit Intelligence.
9. TE-8 Postmortem-Driven Weight Updates.
10. TE-9 Durable Replay Watchdog.
11. TE-10 Idle-State Diagnosis.
12. TE-11 Paper Autonomy Certification Refresh.

This order fixes the present bottleneck first: too few fresh, distinct, qualified candidates. It then improves confirmation, sizing, exits, and learning.

## 19. Success Criteria

Qadam is using its full first-release trading edge when:

- observations regularly become Research Goals;
- Research Goals regularly become distinct candidate proposals;
- candidates are routed into strategy families with clear reasons;
- second-order AI infrastructure candidates name the actual bottleneck and instrument;
- market confirmation explains whether the idea is early, late, or mispriced;
- paper risk size changes with evidence, volatility, and portfolio exposure;
- every open paper position has an exit state;
- every closed paper trade has a postmortem state;
- learning proposals feed back into candidate quality;
- idle states are precise and actionable;
- multiple paper trades per day are allowed when distinct qualified setups pass all gates;
- no module can bypass the paper-only boundary.

