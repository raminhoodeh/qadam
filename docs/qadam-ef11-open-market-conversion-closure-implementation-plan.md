# Qadam EF-11 Open-Market Conversion Closure Implementation Plan

Date: 2026-08-09

Status: Engineering implemented; real provider canary and five-day evidence collection active

Plan ID: `qadam-ef11-open-market-conversion-closure-v1`

Short name: `EF-11`

Parent plan:

- `docs/qadam-evidence-fit-active-paper-trading-overhaul-implementation-plan.md`

Related plans:

- `docs/qadam-permanent-operator-reliability-repair-implementation-plan.md`
- `docs/qadam-operator-ready-edge-engine-implementation-plan.md`
- `docs/qadam-clean-paper-epoch-operational-readiness-implementation-plan.md`

Scope: Close the remaining gap between a current evidence-fit hypothesis and a
small, guarded Alpaca Paper experiment during a real open market session.

## 1. Executive Decision

The evidence-fit overhaul corrected much of Qadam's upstream problem. It now
has:

- a `discovery_micro` lane with a minimum research score of `0.45`;
- profile-specific event, regime, and market-dislocation triggers;
- directional strategy hypotheses;
- a current-evidence packet for Akber's 6-Stage Filter;
- a US$500 to US$1,000 discovery target;
- a US$5,000 absolute paper-trade ceiling;
- portfolio, duplicate-exposure, drawdown, Router, and guarded PaperOps
  controls.

The remaining defect is empirical conversion reliability. Qadam can form an
eligible-looking hypothesis, but it has not yet proved that a real trigger and
fresh open-market execution evidence can coexist in one immutable generation
and continue through:

`Akber -> decision-time shadow -> portfolio risk -> Router -> PaperOps`.

The current certification incorrectly permits a structural `passed` state
while:

- `empirical_trial_complete=false`;
- `eligible_market_days_observed=0`;
- `operational_integrity_passed=false`; and
- no current active-discovery handoff has been observed.

EF-11 fixes that truth gap. It does not lower Pattern Score merely to create
activity. A score such as `0.640` is a research-ranking score, not a 64 percent
win probability. It should qualify a complete setup for a small paper
experiment, but it cannot replace a current trigger, execution evidence,
positive net expectancy, invalidation, or portfolio controls.

The result of EF-11 should be a system that can be left running and trusted to
take more *bounded paper risk* whenever its own approved evidence contract is
actually complete. It cannot guarantee a trade every day, positive returns, or
future profitability.

## 2. Verified Baseline

The implementation must regenerate this baseline before modifying policy or
runtime behavior. The 2026-08-09 artifacts currently show:

| Area | Current state | Interpretation |
| --- | --- | --- |
| Watched instruments | 19 | The complete core universe is evaluated. |
| Current shortlist | 5 | Five relationships receive deeper review. |
| Current directional hypotheses | 2 | SMH and USO reached the discovery lane. |
| Current Akber decisions | 2 holds | Both are held for missing execution context. |
| Current primary blocker | `akber_hold` | Later shadow and risk fields are propagated consequences. |
| Eligible market days | 0 of 5 | The empirical trial has not begun counting valid conversion days. |
| Real session records | 3 | Session records exist but none had co-present trigger and actionable execution evidence. |
| Trial operational integrity | `false` | Empirical conversion is not certified. |
| EF-10 structural certificate | `passed` | This currently overstates completion. |
| EF-10 empirical completion | `false` | The certificate itself admits the trial is unfinished. |
| Live capital | Disabled | Must remain disabled. |

The current SMH and USO records demonstrate the intended use case. They have
directional hypotheses and provisional current expectancy, but the latest run
occurred outside a regular market session and therefore had no actionable
spread. Holding outside market hours is correct. Failing to re-evaluate and
convert an otherwise complete setup during the next valid open session would
be an engineering defect.

## 3. Root-Cause Model

EF-11 treats the current problem as seven distinct engineering issues.

### 3.1 Structural And Empirical Certification Are Conflated

The final checker currently accepts an implementation-ready active-trial
artifact without requiring the five eligible sessions or a current real
open-market conversion. Historical guarded handoff examples can satisfy a
check that should require current-version proof.

### 3.2 Market-Clock Freshness Is Not Enforced In Trial Accounting

The trial accepts `market_clock.is_open=true` without requiring the clock
timestamp to be current. A stale prior-session clock can cause a pre-market or
next-day run to be treated as part of the previous open session.

### 3.3 A Mutable Daily Session Record Can Destroy Better Evidence

The trial stores one record per market date and overwrites it on later runs.
A next-morning cycle using a stale open clock can replace an intraday record
that previously had fresher execution evidence.

### 3.4 Trigger And Execution Evidence Are Not Guaranteed To Coexist

The source, scoring, trigger, market-price, and Akber services run on separate
cadences and resource budgets. A trigger can be current when spread data is not,
or spread data can be current after the trigger has expired.

### 3.5 Decision Stages Are Asynchronous

When Akber does not pass, the shadow and risk stages correctly remain
unreached. The Router currently lists those downstream absences beside the
Akber hold, making one root blocker look like several independent failures.

### 3.6 Critical Market Work Can Be Starved By General Research Work

Open-session receipts contain `cycle_job_budget_exhausted` and resource-busy
states. Historical research and dashboard work must not consume the execution
context budget needed for the five-minute decision path.

### 3.7 The Existing Risk Envelope Is Not Tiered By Forward Evidence

The current discovery lane is appropriately small, but there is no explicit
automatic paper-only progression from first experiment to repeat-confirmed
experiment inside the already approved US$5,000 ceiling. Trade count and risk
size therefore do not clearly respond to accumulated evidence.

## 4. Constitutional Boundaries

Every EF-11 phase must preserve all of the following:

- Alpaca Paper only;
- the canonical PaperOps wrapper is the only broker-write route;
- no direct LLM, dashboard, Telegram, Router, or new coordinator broker call;
- no live-capital endpoint, key loading, authority, or setting;
- no forced trade, synthetic current trigger, or trade quota;
- no stale or closed-market quote represented as actionable;
- no Pattern Score represented as a win probability;
- no missing spread represented as a measured spread;
- no historical, backtest, shadow, or discovery result granted proof credit;
- no automatic mutation of risk ceilings, loss limits, authority, or live
  settings;
- no duplicate exposure or idempotency bypass;
- no removal of daily-loss, drawdown, gross-exposure, or correlated-cluster
  controls;
- no replacement or restructuring of the existing dashboard UX or routes.

The plan may automate selection and sizing *inside* a frozen, operator-reviewed
paper-risk envelope. It may not expand that envelope autonomously.

## 5. Target Operating Contract

The completed open-market flow must be:

1. Refresh source and pattern evidence.
2. Form a directional, profile-specific hypothesis.
3. Pre-stage it as `pending_market_open_confirmation` when execution evidence
   is not currently actionable.
4. Preserve its lineage, trigger expiry, direction, horizon, invalidation, and
   idempotency identity.
5. During the regular session, refresh the market clock and execution context.
6. Build one immutable same-generation decision packet.
7. Apply Akber's 6-Stage Filter.
8. On Akber pass, immediately create the decision-time shadow snapshot.
9. Apply portfolio risk and deterministic paper sizing.
10. Route exactly one final state.
11. Send only a clean paper-review handoff to canonical PaperOps.
12. Submit, reconcile, poll, close, and attribute the real paper lifecycle.
13. Compare the result with the no-order shadow outcome.
14. Use the result for proposal-first learning and future paper-risk tiering.

### 5.1 Canonical Setup States

Every setup must have exactly one current state:

- `research_only`
- `rejected_pattern`
- `pending_current_trigger`
- `pending_market_open_confirmation`
- `execution_context_refreshing`
- `akber_hold`
- `akber_veto`
- `risk_veto`
- `duplicate_exposure_hold`
- `route_repair_required`
- `experimental_paper_review_candidate`
- `paper_order_submitted`
- `paper_order_filled`
- `paper_position_open`
- `paper_trade_closed`
- `postmortem_pending`
- `learning_recorded`

Downstream fields that have not been reached must be labelled
`pending_upstream_pass`, not presented as independent blockers.

### 5.2 Bounded Paper-Risk Ladder

EF-11 must implement a frozen, deterministic sizing ladder. The ladder affects
paper notional only and never grants strategy validation.

| Tier | Minimum evidence | Target notional | Purpose |
| --- | --- | ---: | --- |
| `discovery_micro` | Complete current evidence-fit contract, score at least 0.45, positive net expectancy, Akber pass | US$500-US$1,000 | Acquire the first real outcome. |
| `repeat_confirmed_micro` | At least three independent matured shadow or paper outcomes, positive net result after costs, no material instability | US$1,000-US$2,500 | Test repeatability with modestly greater paper risk. |
| `validated_paper` | Canonical validated edge, stable holdout and forward evidence, approved strategy admission | Up to US$5,000 | Exercise the existing validated paper lane. |

Additional rules:

- a score alone cannot select a higher tier;
- the first `discovery_micro` order defaults to the lower end of its range;
- uncertainty, single-source support, proxy basis risk, or weak liquidity must
  reduce size rather than increase it;
- the US$5,000 absolute ceiling remains unchanged;
- maximum concurrent discovery positions remains three;
- maximum positions per correlated cluster remains one;
- maximum risk per position remains 0.5 percent;
- daily-loss, trailing-drawdown, and gross-exposure limits remain unchanged;
- tier advancement is automatic only inside these frozen rules;
- tier advancement never creates proof credit or live-capital readiness.

## 6. EF11-0 - Baseline Freeze And Contract Reconciliation

### Objective

Freeze the current evidence-fit behavior and establish one authoritative
before-state for the repair.

### Build

- Snapshot the current policy, current score records, hypotheses, Akber
  decisions, shadow state, risk state, Router decisions, PaperOps state,
  operator receipts, market mirror, active-trial sessions, and certifications.
- Record file hashes and generation IDs.
- Record the exact source and instrument counts without modifying either
  universe.
- Record current paper positions, account equity, open orders, drawdown, and
  duplicate-exposure state.
- Classify each existing certificate as structural, integration, empirical, or
  historical proof.
- Prevent historical route examples from being relabelled as current EF-11
  conversion evidence.

### Artifacts

- `data/runtime/qadam_ef11_baseline.json`
- `data/runtime/qadam_ef11_contract_reconciliation.json`
- `data/runtime/qadam_ef11_phase_status.json`

### Checks

- `scripts/check_qadam_ef11_baseline.py`

### Acceptance

- The baseline names the current zero-eligible-day state truthfully.
- Existing open positions and idempotency identities are preserved.
- No order, candidate, risk approval, or policy mutation is created.
- All later EF-11 artifacts reference the baseline ID.

## 7. EF11-1 - Market Clock And Session Truth

### Objective

Make market-session classification depend on a fresh provider clock rather
than a stale boolean.

### Build

- Introduce a canonical market-clock record with:
  - provider timestamp;
  - local receipt timestamp;
  - calculated age;
  - session date;
  - session phase;
  - `is_open`;
  - next open and close;
  - provider and provenance;
  - actionable status;
  - explicit stale reason.
- Require the Alpaca clock age to be within a frozen threshold before
  `is_open=true` is actionable.
- Use a local exchange calendar only to classify expected session windows; it
  must not convert a failed provider clock into provider-backed truth.
- Distinguish pre-market, regular, post-market, weekend, exchange holiday,
  provider stale, and provider unavailable states.
- Refuse to attach a cycle to a prior session when its clock is stale.
- Refresh the market clock before any open-session conversion cycle.

### Artifacts

- `data/runtime/qadam_market_clock_truth.json`
- `data/runtime/qadam_market_clock_history.jsonl`
- `data/runtime/qadam_market_session_checks.json`

### Checks

- `scripts/check_qadam_market_session_truth.py`

### Negative Probes

- Yesterday's `is_open=true` clock is rejected today.
- A weekend clock cannot create an eligible day.
- A missing provider clock cannot be replaced with a fixture.
- A local calendar disagreement creates a repair state, not an order.

### Acceptance

- Every eligible conversion cycle has a fresh provider-backed session clock.
- No session record can be attributed to the wrong market date.
- Closed-market holds remain safe and explicit.

## 8. EF11-2 - Immutable Intraday Conversion Ledger

### Objective

Stop later cycles from overwriting stronger or more complete intraday evidence.

### Build

- Replace mutable one-row-per-day trial evidence with append-only cycle records.
- Give every cycle a stable identity from:
  - trial version;
  - market session date;
  - generation ID;
  - decision timestamp;
  - setup identity.
- Store trigger, execution-context, Akber, shadow, risk, Router, and PaperOps
  reachability in each cycle record.
- Build a deterministic daily reducer that reports:
  - first valid trigger;
  - best evidence-complete cycle;
  - highest stage reached;
  - final cycle before close;
  - any handoff or order;
  - one true root cause per failed conversion.
- Permit corrections only as new append-only records referencing the superseded
  cycle.
- Preserve all records across restart and idempotent replay.

### Artifacts

- `data/runtime/qadam_open_market_conversion_cycles.jsonl`
- `data/runtime/qadam_open_market_conversion_daily_summary.jsonl`
- `data/runtime/qadam_open_market_conversion_status.json`

### Checks

- `scripts/check_qadam_open_market_conversion_ledger.py`

### Acceptance

- A pre-market run cannot overwrite a prior day's intraday evidence.
- Re-running a generation creates no duplicate logical cycle.
- The daily summary can be rebuilt exactly from the immutable ledger.
- Every failed conversion has one primary blocker and separate propagated
  consequences.

## 9. EF11-3 - Pre-Staged Setup Queue

### Objective

Preserve promising hypotheses until the market can supply actionable execution
evidence, instead of discarding or rebuilding them inconsistently.

### Build

- Add a read-only-to-execution pre-stage record for hypotheses that satisfy all
  non-session-dependent discovery requirements.
- Store:
  - Research Goal, score, relationship, and hypothesis lineage;
  - strategy family and evidence profile;
  - instrument, proxy, direction, and horizon;
  - current trigger identity and expiry;
  - support sources and trust;
  - provisional expectancy method;
  - invalidation concept;
  - correlated cluster;
  - idempotency identity material;
  - missing execution fields;
  - next eligible recheck time.
- Use exactly one of:
  - `pending_market_open_confirmation`;
  - `expired_before_market_open`;
  - `superseded_by_new_evidence`;
  - `rejected_before_execution_review`;
  - `ready_for_open_market_revalidation`.
- Revalidate source freshness, direction, trigger relevance, price gap, and
  hypothesis identity at market open.
- Never carry an expired trigger forward merely to create a trade.
- Deduplicate setups across equivalent proxies and correlated variants.

### Artifacts

- `data/runtime/qadam_prestaged_setups.jsonl`
- `data/runtime/qadam_prestaged_setup_status.json`
- `data/runtime/qadam_prestaged_setup_rejections.jsonl`

### Checks

- `scripts/check_qadam_prestaged_setup_queue.py`

### Acceptance

- A valid closed-market hypothesis receives a precise next action and recheck
  time.
- Open-market revalidation uses the same economic identity or explicitly
  supersedes it.
- The queue cannot create a candidate, approval, order, or broker write.

## 10. EF11-4 - Execution Evidence And Conservative Limit Fallback

### Objective

Make the execution gate fit data Qadam can genuinely obtain while preserving a
real cost and liquidity boundary.

### Build

- Use fresh Alpaca Paper market-data reads as the primary execution context.
- Record bid, ask, midpoint, last trade, quote age, trade age, spread in basis
  points, volume, dollar ADV, volatility, session state, and provider feed.
- Require a current bid and ask for ordinary marketable execution review.
- Estimate costs from measured spread, expected slippage, and proxy basis risk.
- Maintain instrument-specific spread histories from real provider-backed
  observations.
- Add a paper-only `fresh_trade_limit_only` fallback when all of the following
  hold:
  - regular session is open and provider clock is fresh;
  - a provider-backed last trade or midpoint is fresh;
  - the instrument is a mapped, highly liquid ETF or equity;
  - sufficient recent measured-spread history exists for that instrument and
    time-of-day bucket;
  - the conservative upper spread bound remains inside the frozen ceiling;
  - notional is capped at the lower `discovery_micro` size;
  - the order type is limit, never market;
  - the limit price includes the frozen conservative cost buffer;
  - an unfilled order expires or cancels under the existing lifecycle policy.
- If these requirements are not met, retain `execution_context_missing`.
- Calibrate the fallback from Qadam's real quote and paper-fill history before
  enabling it. Do not invent a spread estimate from one observation.

### Artifacts

- `data/runtime/qadam_execution_evidence_context.jsonl`
- `data/runtime/qadam_instrument_spread_profiles.json`
- `data/runtime/qadam_execution_fallback_policy.json`
- `data/runtime/qadam_execution_context_rejections.jsonl`

### Checks

- `scripts/check_qadam_execution_evidence_fit.py`

### Negative Probes

- No quote fallback outside regular hours.
- No fallback for prediction-market pseudo-symbols or context-only instruments.
- No market order when spread is missing.
- No fallback without enough measured history.
- No stale trade or quote used as current execution evidence.
- No notional above the applicable paper tier.

### Acceptance

- A genuinely liquid, current setup is not blocked solely because an optional
  data field is absent when a conservative approved limit path exists.
- Missing or unreliable cost evidence still fails closed.
- Execution uncertainty reduces size and order aggressiveness.

## 11. EF11-5 - Atomic Same-Generation Conversion Coordinator

### Objective

Run the latency-sensitive decision path in one ordered generation so upstream
evidence cannot expire between independently scheduled stages.

### Build

- Create `orchestrator/qadam_open_market_conversion.py`.
- Create `scripts/run_qadam_open_market_conversion.py`.
- The coordinator must acquire the existing resource locks and run, in order:
  1. market-clock refresh;
  2. current market-context refresh;
  3. pre-staged setup revalidation;
  4. decision evidence packet build;
  5. Akber evaluation;
  6. decision-time shadow snapshot creation after Akber pass;
  7. portfolio-risk proposal;
  8. Router decision;
  9. PaperOps handoff build;
  10. canonical PaperOps wrapper invocation only when a clean handoff exists.
- Bind every output to one conversion generation ID and decision timestamp.
- Recheck trigger expiry and market-data freshness before PaperOps invocation.
- Stop immediately on stale generation, lock conflict, duplicate exposure,
  drawdown breach, Q-CTRL hold, or route mismatch.
- Never retry an ambiguous broker write automatically.
- Resume safely from the last immutable pre-broker stage after interruption.
- Keep PaperOps as the only component able to submit the broker order.

### Artifacts

- `data/runtime/qadam_open_market_conversion_generation.json`
- `data/runtime/qadam_open_market_conversion_receipts.jsonl`
- `data/runtime/qadam_open_market_conversion_failures.jsonl`
- existing Router, handoff, PaperOps, and lifecycle artifacts

### Checks

- `scripts/check_qadam_open_market_conversion.py`

### Acceptance

- Akber pass deterministically creates a same-generation shadow snapshot before
  risk review.
- Risk and Router consume the same evidence generation.
- A clean handoff reaches the canonical wrapper without a parallel broker path.
- A repeated cycle cannot submit a duplicate order.
- An Akber hold reports downstream stages as not reached, not separately broken.

## 12. EF11-6 - Scheduler Priority And Market-Session Capacity

### Objective

Ensure general research workloads cannot starve the open-market conversion
path.

### Build

- Create a dedicated `market_conversion_critical` concurrency group.
- Reserve cycle budget for:
  - market clock and price refresh;
  - trigger and pre-stage refresh;
  - Akber;
  - shadow;
  - portfolio risk and Router;
  - guarded PaperOps;
  - lifecycle reconciliation.
- During regular US market hours:
  - refresh price and quote context at least every minute;
  - run setup revalidation and the conversion coordinator every five minutes;
  - scan all 19 watched instruments at least every 20 minutes;
  - prioritize a new current trigger immediately;
  - defer heavy backtests, historical acquisitions, and dashboard rebuilds when
    they would exhaust the critical path budget.
- Add a pre-market warm-up before 09:30 America/New_York.
- Add post-open and pre-close canaries.
- Recover after sleep, network loss, process restart, and provider throttling
  without backfilling elapsed market time.
- Classify `cycle_job_budget_exhausted` on the critical path as an operational
  defect, not a benign skip.

### Artifacts

- `data/runtime/qadam_market_session_scheduler_status.json`
- `data/runtime/qadam_market_session_capacity.json`
- existing operator receipts and circuit artifacts

### Checks

- `scripts/check_qadam_market_session_scheduler.py`

### Acceptance

- At least 95 percent of due critical-path jobs begin within their frozen
  session latency budget during the empirical trial.
- No eligible trigger expires because dashboard or historical research work
  consumed the execution budget.
- A missed critical cycle creates a repair request and visible degraded state.

## 13. EF11-7 - Root Blocker Semantics And Self-Healing

### Objective

Turn no-trade outcomes into one actionable diagnosis and safely repair
recoverable infrastructure failures.

### Build

- Publish exactly one primary root state per setup.
- Separate:
  - market/evidence hold;
  - risk veto;
  - safety stop;
  - provider outage;
  - stale clock;
  - scheduler starvation;
  - schema/conversion defect;
  - route failure;
  - downstream stage not reached.
- Retry safe GET-based refreshes with bounded exponential backoff.
- Rebuild stale deterministic artifacts from immutable inputs.
- Queue code defects for operator repair; never edit code silently.
- Close a circuit only after its real command and real artifact freshness pass.
- Escalate repeated open-market execution-context failures separately from a
  legitimate Akber hold.

### Artifacts

- `data/runtime/qadam_conversion_root_cause.json`
- `data/runtime/qadam_conversion_repair_queue.json`
- `data/runtime/qadam_conversion_recovery_history.jsonl`

### Checks

- `scripts/check_qadam_conversion_self_healing.py`

### Acceptance

- The dashboard and Telegram show one true blocker, its owner, its next recheck,
  and whether Qadam can repair it automatically.
- Safe refresh failures recover without policy or authority changes.
- Repeated implementation defects cannot be misreported as prudent selectivity.

## 14. EF11-8 - Paper-Risk Tiering And Automatic Bounded Admission

### Objective

Allow Qadam to take more paper risk as real evidence accumulates, without
silently changing the approved risk envelope.

### Build

- Encode the Section 5.2 sizing ladder in one frozen policy artifact.
- Calculate tier eligibility from immutable shadow and real paper outcomes.
- Require independent outcome identities and prevent repeated observations of
  one event from inflating sample size.
- Measure net return after spread, slippage, delay, and proxy basis risk.
- Require stability across at least two time or regime buckets before
  `repeat_confirmed_micro`.
- Automatically demote a tier after instability, adverse drawdown, source
  degradation, or failed cost assumptions.
- Permit automatic strategy admission only to the existing paper-only
  experimental route and only within the frozen envelope.
- Keep validated-edge admission and live-capital authority separate.
- Emit a proposal, not an automatic mutation, for any threshold, ceiling,
  universe, or authority change outside the frozen ladder.

### Artifacts

- `data/runtime/qadam_paper_risk_ladder.json`
- `data/runtime/qadam_paper_risk_tier_decisions.jsonl`
- `data/runtime/qadam_paper_risk_tier_status.json`

### Checks

- `scripts/check_qadam_paper_risk_tiering.py`

### Negative Probes

- One high score cannot increase size.
- One profitable trade cannot advance a tier.
- Correlated outcomes cannot count as independent evidence.
- No automatic increase above US$5,000.
- No paper result can enable live capital.

### Acceptance

- Complete first-time setups can receive small paper risk promptly.
- Repeatedly successful setups can receive more paper risk automatically
  inside the frozen bounds.
- Weak or unstable setups are demoted without waiting for operator action.

## 15. EF11-9 - Certification Truth Rewrite

### Objective

Make certification state exactly what has been proven.

### Build

- Replace the single overloaded certificate with three explicit layers:
  - `structural_ready`: schemas, policy, route, idempotency, and safety probes;
  - `provider_conversion_ready`: a fresh open-market provider canary reaches a
    handoff with broker writing disabled;
  - `empirically_conversion_proven`: the real five-eligible-session trial and
    current-version conversion acceptance have passed.
- Keep one public-safe aggregate that cannot report `complete` unless all
  required layers pass.
- Remove historical guarded handoffs as substitutes for current-version proof.
- Require current policy, trigger, market context, shadow, risk, Router, and
  PaperOps lineage versions to match.
- Fail empirical certification when:
  - eligible days are below five;
  - operational integrity is false;
  - a real valid trigger is blocked by schema, sequencing, stale-clock, or
    scheduler defects;
  - current-version provider canary evidence is missing;
  - the conversion path is starved during an eligible session.
- Permit `structural_ready=true` while empirical collection continues, but
  label the overall state `collecting_empirical_conversion_evidence`.

### Artifacts

- `data/runtime/qadam_ef11_structural_certification.json`
- `data/runtime/qadam_ef11_provider_conversion_certification.json`
- `data/runtime/qadam_ef11_empirical_conversion_certification.json`
- `data/runtime/qadam_ef11_open_market_conversion_certification.json`

### Checks

- `scripts/check_qadam_ef11_open_market_conversion.py`

### Acceptance

- Zero eligible days can never produce an empirically complete certificate.
- An old XAR or historical handoff cannot certify the current generation.
- A current provider-backed setup can reach a bounded handoff in a real open
  session before active conversion is certified.
- Certification itself creates no order.

## 16. EF11-10 - Five-Eligible-Market-Day Conversion Trial

### Objective

Prove that the repaired system converts genuine, evidence-complete setups in
real market time.

### Eligible Day Definition

A day counts only when:

- a real regular US market session occurs;
- the provider clock is fresh;
- operator and PaperOps health are current;
- all 19 instruments receive the required scans;
- at least one strategy has a genuine current trigger;
- its mapped instrument has actionable execution context or an approved
  conservative limit-only fallback;
- no account-level safety stop is active.

### Trial Rules

- Observe five eligible days without simulated or backfilled time.
- Target an average of one bounded paper experiment per eligible day.
- The target is a conversion-discipline metric, not an order quota.
- Permit multiple distinct setups only when each independently passes.
- Preserve cluster, duplicate, drawdown, loss, exposure, and Q-CTRL controls.
- Record every setup and every stage transition.
- Count a valid trigger blocked by missing internally producible context as an
  engineering failure.
- Count an Akber veto or risk veto as a legitimate no-trade outcome when its
  evidence is complete and adverse.
- Do not count days with no genuine trigger as evidence that the gates work or
  fail.

### Trial Metrics

- eligible trigger count;
- pre-staged setup count;
- current execution-context availability;
- trigger-to-Akber conversion rate;
- Akber pass, hold, and veto counts;
- Akber-pass-to-shadow latency;
- shadow-to-risk latency;
- Router handoff count;
- guarded paper order count;
- fill rate and time to fill;
- duplicate suppression count;
- spread, slippage, and proxy cost;
- net paper P&L;
- no-order shadow P&L;
- missed-opportunity and avoided-loss outcomes;
- infrastructure-defect conversion loss;
- tier advancement and demotion decisions.

### Acceptance

- Five eligible days are observed with fresh immutable records.
- Every eligible setup has exactly one final outcome.
- Schema, timing, stale-clock, and scheduler conversion failures are zero.
- At least one naturally eligible setup reaches current-version PaperOps
  handoff during the trial; otherwise empirical active-conversion certification
  remains incomplete.
- Any order is real Alpaca Paper, uniquely identified, and lifecycle reconciled.
- Paper results are reported honestly even if they lose money.

## 17. EF11-11 - Dashboard And Telegram Truth

### Objective

Explain increased activity and remaining holds without changing the existing
dashboard information architecture.

### Dashboard Enrichment

Preserve every current route, section order, and established UX. Add only
dashboard-safe fields within the existing relevant modules:

- current certification layer;
- eligible market days completed;
- pre-staged setup count;
- current setup state;
- current risk tier and proposed paper notional;
- true primary blocker;
- propagated stages not reached;
- next recheck time;
- market-clock freshness;
- execution-context freshness;
- conversion generation ID;
- latest handoff and paper lifecycle state;
- trial conversion rate;
- net paper outcomes versus no-order shadow outcomes.

### Telegram Rules

- Notify only on a material state change:
  - a setup is pre-staged;
  - a setup expires;
  - Akber passes or vetoes;
  - a paper order is submitted, filled, or closed;
  - an execution defect blocks a valid setup;
  - a risk tier advances or is demoted;
  - empirical certification changes.
- Keep messages short, specific, deduplicated, and public-safe.
- State the pattern, instrument, reason, blocker or action, and paper-only
  status.
- Telegram remains review-only and command-disabled.

### Checks

- `scripts/check_qadam_ef11_visibility.py`

### Acceptance

- The existing dashboard UX is retained.
- Structural readiness is not shown as empirical conversion proof.
- One root blocker is visible without internal blocker repetition.
- No dashboard or Telegram surface creates authority.

## 18. EF11-12 - Unattended Reliability Soak

### Objective

Prove the installed operator can maintain the repaired decision path without
manual intervention.

### Build

- Run the installed operator through:
  - pre-market transition;
  - market open;
  - regular session;
  - market close;
  - one restart;
  - one network interruption recovery;
  - one provider-throttle recovery;
  - laptop wake recovery where feasible.
- Confirm critical-path latency and artifact freshness.
- Confirm no stale clock or session overwrite recurrence.
- Confirm repair queues close only after real revalidation.
- Confirm PaperOps remains idempotent across restart.

### Artifacts

- `data/runtime/qadam_ef11_unattended_soak.json`
- `data/runtime/qadam_ef11_unattended_soak_sessions.jsonl`

### Checks

- `scripts/check_qadam_ef11_unattended_soak.py`

### Acceptance

- No open critical circuit or repair request remains.
- All critical services meet freshness and latency targets.
- No duplicate order or ambiguous lifecycle state appears.
- The system recovers or stops safely without operator intervention.

## 19. EF11-13 - Deployment And Operational Cutover

### Objective

Deploy the repaired system without replacing the existing dashboard UX and
start the real empirical trial.

### Procedure

1. Confirm unrelated worktree changes are preserved.
2. Run all EF-11 unit, integration, property, and negative-safety tests.
3. Run canonical PaperOps in ready-idle mode before any handoff.
4. Build fresh dashboard-safe view models.
5. Verify the existing dashboard locally.
6. Build and verify the production dashboard bundle.
7. Deploy only the current dashboard worktree and verified runtime snapshot.
8. Verify production aliases and served-bundle hashes.
9. Install or refresh the operator service definition.
10. Run one provider-backed open-market canary with broker writing disabled.
11. Start the real five-eligible-day trial.
12. Permit guarded paper submission only after provider-conversion readiness
    passes and a naturally eligible current setup exists.

### Acceptance

- Local, preview, and production dashboard parity passes.
- Existing dashboard UX remains intact.
- Operator status is fresh and accurately reflects the certification layer.
- Canonical PaperOps is the only broker writer.
- The empirical trial begins from the real calendar without backfill.

## 20. Test Matrix

The implementation must include at least the following tests.

### Unit Tests

- fresh and stale market clocks;
- session-date calculation;
- setup expiry and supersession;
- immutable cycle identity;
- primary blocker selection;
- propagated consequence labelling;
- spread-profile calculation;
- conservative limit fallback eligibility;
- risk-tier calculation;
- tier demotion;
- idempotency material.

### Integration Tests

- trigger plus closed market -> pre-stage;
- pre-stage plus fresh open quote -> Akber review;
- Akber pass -> same-generation shadow;
- shadow -> risk -> Router;
- Router candidate -> canonical PaperOps handoff;
- duplicate cycle -> no duplicate order;
- stale trigger at open -> expiry, no handoff;
- missing spread with qualified fallback -> bounded limit path;
- missing spread without qualified fallback -> hold;
- open-market provider failure -> repair request;
- restart before PaperOps -> safe resume;
- restart after ambiguous write -> reconciliation, no retry.

### Property Tests

- every setup has exactly one current state;
- every no-trade outcome has exactly one root blocker;
- every order has one distinct idempotency key;
- all generated notional values remain within the frozen tier and portfolio
  ceilings;
- immutable records never change after publication;
- reconstructed daily summaries are deterministic.

### Negative Safety Tests

- no live endpoint;
- no direct broker writer;
- no fixture labelled provider-backed;
- no stale quote or clock accepted;
- no closed-market order;
- no synthetic trigger;
- no score-only order;
- no negative-control order;
- no prediction pseudo-symbol sent to Alpaca;
- no duplicate exposure;
- no drawdown, daily-loss, or gross-exposure bypass;
- no Q-CTRL bypass;
- no policy or authority mutation;
- no proof credit;
- no Telegram or dashboard authority.

## 21. Canonical Certification Contract

The final checker is:

- `scripts/check_qadam_ef11_open_market_conversion.py`

It writes:

- `data/runtime/qadam_ef11_open_market_conversion_certification.json`

The aggregate state may be only one of:

- `blocked_structural_defect`
- `structurally_ready_collecting_provider_canary`
- `provider_ready_collecting_eligible_days`
- `empirically_conversion_proven_paper_only`
- `degraded_runtime_repairing`
- `safety_stop`

It may report `empirically_conversion_proven_paper_only` only when:

- structural checks pass;
- provider-backed open-market canary passes;
- five eligible market days are complete;
- operational integrity passes;
- no valid setup was lost to schema, sequencing, clock, scheduler, or route
  defects;
- at least one naturally eligible setup reached current-version PaperOps
  handoff;
- all orders and lifecycle records reconcile;
- live capital remains disabled;
- unauthorized proof credit is zero.

## 22. Success Metrics

EF-11 is successful when Qadam is more active for evidence-based reasons, not
because risk controls were bypassed.

### Operational Metrics

- 100 percent of eligible cycles use a fresh provider clock;
- 100 percent of setup states have one root blocker;
- zero session overwrite defects;
- zero mixed-generation conversion joins;
- zero eligible setup losses from scheduler starvation;
- at least 95 percent critical-service on-time rate;
- zero duplicate or unauthorized broker writes.

### Conversion Metrics

- all 19 instruments scanned at least every 20 minutes during regular sessions;
- every current trigger is revalidated before expiry;
- every Akber pass creates a same-generation shadow snapshot;
- every risk-approved setup receives exactly one Router state;
- every clean paper candidate reaches canonical PaperOps;
- average target of one bounded paper experiment per eligible market day,
  without a quota.

### Economic Metrics

- net return after measured spread and slippage;
- expected versus realized cost;
- paper outcome versus no-order shadow;
- hit rate and payoff ratio;
- maximum adverse and favorable excursion;
- drawdown contribution;
- performance by strategy, evidence profile, source combination, and regime;
- evidence that higher paper-risk tiers improve expected value rather than only
  increasing turnover.

No implementation metric can certify profitability. Positive paper results
must be earned in real forward time.

## 23. Stop, Demote, And Escalation Rules

The system must stop or demote automatically when:

- provider or clock evidence becomes stale;
- trigger identity changes materially;
- expected return becomes non-positive after costs;
- spread or slippage exceeds the approved bound;
- invalidation is missing;
- duplicate or correlated exposure conflicts;
- daily loss, drawdown, or gross exposure breaches;
- PaperOps route integrity fails;
- lifecycle reconciliation becomes ambiguous;
- a strategy's forward outcomes become unstable;
- a source degrades or loses provenance.

The system must request operator review when:

- a new risk tier or ceiling is proposed;
- a new provider or paid entitlement is needed;
- a new strategy family requires admission outside the frozen experimental
  contract;
- a code defect repeats after safe retries;
- live-capital readiness is considered.

## 24. Modular Implementation Sequence

Implement in this exact order:

1. EF11-0: Baseline Freeze And Contract Reconciliation
2. EF11-1: Market Clock And Session Truth
3. EF11-2: Immutable Intraday Conversion Ledger
4. EF11-3: Pre-Staged Setup Queue
5. EF11-4: Execution Evidence And Conservative Limit Fallback
6. EF11-5: Atomic Same-Generation Conversion Coordinator
7. EF11-6: Scheduler Priority And Market-Session Capacity
8. EF11-7: Root Blocker Semantics And Self-Healing
9. EF11-8: Paper-Risk Tiering And Automatic Bounded Admission
10. EF11-9: Certification Truth Rewrite
11. EF11-10: Five-Eligible-Market-Day Conversion Trial
12. EF11-11: Dashboard And Telegram Truth
13. EF11-12: Unattended Reliability Soak
14. EF11-13: Deployment And Operational Cutover

Do not begin the empirical trial until EF11-0 through EF11-9 pass. EF11-10 and
EF11-12 require genuine elapsed market time and cannot be backfilled.

## 25. Common Implementation Prompt

Use this prefix for each modular implementation request:

> Work in `/Users/raminhoodeh/Desktop/qadam`. Read
> `docs/qadam-ef11-open-market-conversion-closure-implementation-plan.md` and
> `docs/qadam-evidence-fit-active-paper-trading-overhaul-implementation-plan.md`
> first. Implement only the requested EF11 phase. Preserve unrelated worktree
> changes and the existing dashboard UX and routes. Keep all behavior
> paper-only, provider-truthful, idempotent, fail-closed, and compatible with
> the canonical PaperOps wrapper. Do not edit secrets or `.env` files, enable
> live capital, call live broker endpoints, create a parallel broker route,
> manufacture triggers, force trades, bypass Akber, bypass portfolio risk,
> bypass Q-CTRL, alter the US$5,000 ceiling, grant proof credit, or implement a
> later phase. Add the artifacts, checks, tests, dynamic phase status, and
> implementation log required by the plan. Run relevant real-data read-only
> checks where the phase requires them.

## 26. Final Completion Definition

Engineering implementation is complete only when:

- stale market clocks cannot create or overwrite session evidence;
- trial cycles are immutable and reconstructable;
- promising closed-market setups persist safely to open-market revalidation;
- trigger and execution evidence are refreshed in one decision generation;
- Akber pass creates the required shadow snapshot before portfolio risk;
- portfolio risk and Router consume that same generation;
- clean paper candidates reach canonical PaperOps without parallel execution;
- missing spread uses either measured evidence, a calibrated conservative
  limit-only fallback, or an honest hold;
- critical market work cannot be starved by research jobs;
- one true blocker and its next action are visible;
- paper size can progress automatically only inside the frozen evidence ladder;
- certification separates structural, provider, and empirical truth;
- the current dashboard UX and routes are preserved;
- live capital remains disabled.

Autonomous active-conversion readiness is complete only when:

- a current provider-backed open-market canary passes;
- five real eligible market days complete;
- the unattended soak passes;
- at least one naturally eligible current setup reaches the current-version
  guarded PaperOps handoff;
- no eligible setup is lost to a clock, schema, sequencing, scheduler, or route
  defect;
- any real paper orders reconcile through their full lifecycle.

At that point the operator can leave Qadam running with a justified expectation
that complete low-risk hypotheses will become small paper experiments and that
repeated evidence can earn greater paper risk. The system will be more active,
but it will still refuse incomplete or adverse setups. Whether that activity
makes money remains an empirical result that Qadam must demonstrate rather than
an implementation claim.
