# Qadam Evidence-Fit Active Paper Trading Overhaul Implementation Log

## 2026-08-08 - EF-0 Through EF-4

Status: Completed and certified through EF-4. Later phases remain pending.

### EF-0 - Reproducible Baseline

- Froze a checksummed evidence-fit baseline with source, instrument, Pattern
  Score, Foundry, Akber, Router, historical-coverage, policy, and code lineage.
- Recorded one canonical producer and consumer for every decision-critical
  evidence field.
- Preserved all paper-only and no-authority boundaries.

### EF-1 - Canonical Source And Instrument Truth

- Classified all 41 registered sources by truthful availability and allowed
  evidence role.
- Classified all 19 frozen instruments by observation role and guarded route
  state.
- Kept futures and prediction contracts outside the Alpaca symbol route.
- Preserved source aliases without counting aliases as independent evidence.

### EF-2 - Strategy-Specific Trigger Factory

- Added provider-event normalization and causal classifiers for crude oil,
  defence, and semiconductors.
- Added numeric silver and power regime observations with explicit inactive or
  missing states.
- Added compatible-contract prediction-market dislocation measurement and an
  explicit no-dislocation outcome when compatible contracts are unavailable.
- The certification snapshot produced four event triggers, two regime
  observations, and zero fabricated market dislocations.

### EF-3 - Direction And Emerging-Strategy Resolution

- Added deterministic `long`, `short`, and
  `abstain_direction_unresolved` outcomes with evidence IDs and explanations.
- Preserved raw research direction language separately from actionable
  direction.
- Resolved current semiconductor event evidence without treating conditional
  wording as a rejection by itself.
- Converted incomplete or inactive silver and power regimes into explicit
  abstentions rather than guessed trades.
- Prevented negative controls and generic strategy-agnostic rows from forming
  strategies or candidates.
- Kept the power sleeve in its existing under-evidenced emerging state.

### EF-4 - Same-Generation Decision Evidence Packet

- Added one immutable decision packet contract per Akber-reviewable
  hypothesis, bound to a generation ID and decision timestamp.
- Separated available, inactive, missing, stale, unavailable, and adverse
  states.
- Made closed-market spreads inactive rather than adverse.
- Bound Akber inputs to exactly one packet when packet mode is active and
  rejected missing, duplicate, or mixed-generation packet lineage.
- The certification snapshot contained no current Foundry hypothesis, so zero
  packets and zero Akber inputs was the truthful current result.

### Verification

- `scripts/check_qadam_evidence_fit_phases_1_4.py`: passed.
- Durable status: `implemented_through_phase=EF-4`.
- Validation errors: 0.
- Targeted regression suite: 53 passed.
- Ruff: passed for all new EF-0 through EF-4 modules, scripts, and tests.
- Runtime authority audit: 44 generated records checked, 0 unsafe records.
- Dashboard source files changed: 0.
- Trade candidates, approvals, orders, broker writes, proof credit, and paper
  calendar progress created by EF-0 through EF-4: 0.

### Current Evidence Outcome

The implementation improves evidence conversion but does not claim a current
trade. At the certification snapshot, current event triggers existed, but the
market was outside an actionable session and complete current price,
volatility, and confirmation inputs had not produced a Foundry hypothesis.
EF-5 is the next planned phase and will recalibrate Akber against these typed
evidence profiles without bypassing risk controls.

## 2026-08-08 - EF-5 Through EF-8

Status: Implemented and certified through EF-8. The EF-7 empirical trial is
collecting real eligible market days and is not complete.

### EF-5 - Akber Evidence-Fit Recalibration

- Added event-catalyst, regime-state, and market-dislocation evidence profiles.
- Made inactive triggers a watchlist state, missing context a hold, measured
  adverse evidence a veto, and complete evidence a pass.
- Kept confirmation alternative-based and quantum optional unless a hypothesis
  is explicitly quantum-dependent.
- Preserved threshold changes as proposals only.
- Restored the complete EF-2 through EF-4 producer chain before every Akber
  review so current hypotheses cannot be evaluated against stale direction or
  packet lineage.
- Certified 166 measurable historical replays: 76 passes, 58 holds, and 32
  vetoes, plus 18 profile-stage ablations.

### EF-6 - Portfolio Risk And Router Alignment

- Separated causal-source concentration from independent market confirmation
  and portfolio exposure.
- Applied a 0.50 sizing haircut to valid single-source discovery setups instead
  of treating confirmation as a second causal source.
- Made missing spread a hold and evaluated spread ceilings only when a measured
  actionable spread exists.
- Preserved duplicate-exposure, correlation, drawdown, daily-loss, gross
  exposure, route, and idempotency controls.
- Added one primary Router root cause with downstream consequences recorded
  separately.
- Kept the frozen US$500 to US$1,000 discovery target and US$5,000 absolute
  ceiling unchanged.

### EF-7 - Guarded Active Discovery Trial

- Migrated the existing trial in place without resetting its identity or
  inventing elapsed market time.
- Added conversion-funnel, eligible-day, and one-root-cause-per-no-trade
  ledgers plus separate implementation and empirical certification.
- A day counts only when operator health, a real current trigger, actionable
  execution context, and account-level safety all pass during a real market
  session.
- Current truth: 3 market sessions recorded, 0 eligible under the new contract,
  and a target of 5 eligible days. The trial remains
  `collecting_real_eligible_days`.

### EF-8 - Outcome Learning And Strategy Promotion

- Added unified outcome records for shadow, hold, veto, inactive-trigger,
  missed-opportunity, implementation-defect, and lineage-complete paper states.
- Added attribution across sources, triggers, confirmation, direction, Akber,
  risk, Router, proxy basis, costs, execution, and quantum review.
- Added versioned promotion proposals and admission records.
- Automatic admission is limited to `emerging_paper_strategy` inside the frozen
  risk envelope and requires a validated edge plus at least five real positive
  forward outcomes under an unchanged strategy definition.
- Automatic validated-strategy admission, risk expansion, live authority,
  order creation, and proof credit remain disabled.
- Current truth: 123 outcome records, 21 mature real outcomes, 2 strategies
  collecting forward evidence, and 0 automatic admissions.

### Operator Integration And Verification

- Wired EF-2 through EF-5 into `akber_review`, EF-6 into
  `portfolio_router_review`, EF-7 into `active_discovery_trial`, and EF-8 into
  `learning_attribution`.
- Registered 82 autonomous artifact ownership records with 0 multi-writer
  conflicts.
- Revalidated and closed the Akber and portfolio/Router circuits through three
  successful real-service passes each.
- Safely drained and restarted the installed operator after state-root,
  ownership, resource-lock, generation, and storage preflights passed. The
  running daemon now matches the current EF-8 build, and the Akber, risk/Router,
  active-discovery, and learning services are fresh with closed circuits.
- The older guarded-PaperOps circuit remains separately open pending explicit
  canonical paper-route revalidation. No alternate route was used.
- Aggregate certification:
  `scripts/check_qadam_evidence_fit_phases_5_8.py` passed with
  `implemented_through_phase=EF-8` and 0 validation errors.
- Targeted regression suite: 145 distinct tests passed across the phase and
  ordered operator paths.
- Ruff and Python compilation passed.
- Trade candidates, approvals, paper orders, broker writes, live authority,
  proof credit, and simulated calendar progress created by EF-5 through EF-8:
  0.

### Next Phase Boundary

EF-9 is the next planned phase. No dashboard source, deployment configuration,
or public release was changed by EF-5 through EF-8.

## 2026-08-08 - EF-9 Through EF-10

Status: Implemented and certified through EF-10. The system is certified for
autonomous paper observation. The EF-7 empirical trial remains active and must
accumulate five eligible market days without simulated time.

### EF-9 - Dashboard And Notification Truth

- Added one public-safe evidence-fit projection across the existing Data
  Sources, Trading Universe, Pattern Recognition, Trading Strategies, Decision
  Room, Order Monitor, and Learn & Improve modules.
- Preserved all 13 dashboard routes, their order, navigation, and established
  visual structure. New detail remains additive and collapsed by default.
- Added profile-specific source freshness, paperability distinctions, current
  trigger and direction state, strategy conversion state, a nine-step decision
  funnel, and one first-root-blocker explanation.
- Added material-change notification candidates with deterministic deduplication.
  The projection is review-only and cannot send commands, create approval,
  place orders, write to a broker, or grant proof credit.
- Frontend acceptance passed with 13 protected routes and 7 enriched evidence
  areas.

### EF-10 - Certification And Autonomous Observation

- Added the fail-closed final checker and durable certification artifact.
- Passed 19 of 19 end-to-end checks and 11 of 11 negative safety probes.
- Revalidated the canonical PaperOps wrapper as `ready_idle` with no blockers,
  no submitted order, and no alternate broker route.
- Corrected active-discovery freshness so its immutable trial contract no
  longer makes healthy mutable trial outputs appear stale.
- Completed the supervised operator integration probe for all 11 required
  non-ordering services, then restarted the launch agent on the committed
  build.
- Current operator truth: 16 of 16 services fresh, 0 stale, 0 open circuits,
  0 repair requests, and `observation_ready=true`.
- Registered 89 autonomous artifact ownership records with 0 multi-writer
  conflicts.
- Targeted overhaul regression suite: 150 tests passed. The operator-specific
  regression suite passed 50 tests after the freshness correction.
- Ruff, Python compilation, JavaScript syntax, whitespace, authority, and
  governance safety checks passed.

### Empirical Boundary

Implementation completion does not manufacture a trade or claim a profitable
edge. Qadam can now convert evidence through the calibrated guarded path and
observe autonomously. A paper order still requires a real current trigger,
same-generation context, Akber, shadow, risk, Router, idempotency, duplicate
exposure, and canonical PaperOps checks. The five-day calibration advances only
on real eligible market days.
