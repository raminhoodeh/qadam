# Qadam Autonomous Experimental Paper Epoch Implementation Plan

Date: 2026-07-19

Status: Proposed authoritative plan for clean autonomous experimental paper operation

Parent plans:

- `docs/qadam-operator-ready-edge-engine-implementation-plan.md`
- `docs/qadam-clean-paper-epoch-operational-readiness-implementation-plan.md`

## 1. Executive Decision

Qadam does not need to prove a statistically validated edge before it can begin
a controlled paper-trading experiment. The clean paper epoch is the environment
in which Qadam can collect real forward decisions, holds, vetoes, orders,
outcomes, and postmortems that may eventually prove or reject an edge.

This plan therefore separates two permissions that the current release sequence
incorrectly couples:

1. **Experimental paper permission** allows a complete, current, risk-bounded
   hypothesis to enter the guarded Alpaca Paper route for evidence collection.
2. **Validated-strategy promotion** requires the stricter historical,
   out-of-sample, forward-shadow, cost, drawdown, and governance evidence needed
   to call a relationship an edge or increase its standing in the fund.

An experimental paper trade is not a validated edge. A validated edge is not
live-capital permission. Live capital remains disabled and out of scope.

## 2. Document Authority And Precedence

This document supersedes only the **release ordering** in the clean-paper-epoch
plan that requires a validated edge, completed forward-shadow promotion, and a
seven-session soak before a clean experimental paper epoch may begin.

It does not supersede:

- the immutable archive and rollback design;
- the new-account Alpaca Paper preflight;
- source provenance and point-in-time controls;
- the frozen edge-promotion policy;
- Akber's 6-Stage Filter;
- portfolio-risk limits;
- Router, idempotency, duplicate-exposure, drawdown, Q-CTRL, and PaperOps gates;
- the guarded Alpaca Paper route;
- proof-lineage requirements;
- the proposal-first learning boundary;
- any live-capital prohibition.

The operator-ready edge-engine plan remains authoritative for historical edge
research and validated-strategy promotion. This plan is authoritative for the
clean experimental paper-account cutover and autonomous paper operation.

No second Router, PaperOps route, dashboard application, or competing runtime
contract may be created. Existing canonical modules must be extended in place.

## 3. Required End State

The plan is operationally complete when all of the following are true:

- A genuinely new Alpaca Paper account starts with exactly US$100,000 USD cash
  and equity, zero positions, and zero current or historical orders.
- Its non-reversible account fingerprint differs from the testing account.
- The testing epoch is checksummed, archived, proof-ineligible, and absent from
  every active portfolio, history, performance, lifecycle, and proof view.
- Historical data, pattern research, backtests, strategy research, source
  reliability, and learning memory survive the cutover.
- The current dashboard design and route structure remain unchanged.
- Every source in the canonical universe has one truthful operating class:
  live and fresh, historical-only, forward-only, temporarily degraded,
  unavailable, or explicitly excluded.
- Fixture, sample, local-import, or configured-only states never count as live.
- Every source required by an eligible setup is fresh and independently
  quorum-eligible at its decision timestamp.
- The provider-backed historical acquisition and point-in-time backtest remain
  certified, with zero validated edges accepted as an honest result.
- Portfolio starts at US$100,000, 100% cash, zero P&L, and zero drawdown.
- Trading History and Order Monitor start empty for the current epoch.
- Qadam runs continuously under the supervised local operator service.
- Source ingestion, prices, scoring, evidence validation, hypothesis review,
  Akber, risk, Router, PaperOps, lifecycle, postmortem, learning, dashboard, and
  notification jobs execute on audited cadences.
- Qadam may submit an experimental paper order without a validated edge only
  when every experimental eligibility and safety gate passes.
- Qadam may correctly remain `ready_idle` with zero trades when no setup passes.
- Every paper order uses the canonical guarded Alpaca Paper wrapper. No model,
  dashboard, Telegram surface, or quantum component calls a broker directly.
- The real 30-day paper growth trial starts only when the clean epoch is active
  and guarded autonomous paper operation is successfully released.
- Trial time is never backfilled, simulated, paused, or manufactured.
- The paper proof ledger distinguishes a real paper-trade fact from validated
  edge credit.
- Live endpoints and live capital remain disabled.

Strong returns, a validated edge, or measurable quantum advantage are desired
outcomes, not implementation acceptance criteria. They must emerge from data.

## 4. Current Dated Baseline

The implementation must regenerate this baseline before changing state. Current
artifacts indicate:

| Area | Current state | Required transition |
| --- | --- | --- |
| Historical lake | 746,275 provider-backed rows | Preserve and continue evidence work |
| Research universe | 41 sources and 19 watched instruments | Keep one canonical classified universe |
| Validated edges | 0 | Remain honest; do not manufacture promotion |
| Forward-shadow promotion | Not ready | Continue in real time after launch |
| Operator soak | 2 of 7 real sessions | Continue under the version-bound post-cutover service |
| Broker account | Legacy testing account | Replace with a new empty US$100,000 Alpaca Paper account |
| Testing history | 42 closed testing trades | Archive and exclude from active views |
| Execution mode | Research lock active; PaperOps watch-only | Release experimental paper writes only |
| Live capital | Disabled | Keep disabled |

These counts are evidence, not hardcoded product copy. The preflight must read
the latest canonical artifacts and record any changed values.

## 5. Non-Negotiable Boundaries

- Paper trading only.
- Alpaca Paper is the only broker-write destination.
- Live broker endpoints and live capital remain denied.
- No cosmetic local reset may contradict the real broker account.
- No old trade may be deleted, rewritten, or passed off as new-epoch history.
- No trade is forced to satisfy a daily target or demonstrate activity.
- No historical, fixture, shadow, or synthetic event is represented as a real
  paper trade.
- No experimental paper trade is represented as a validated edge.
- No single source can satisfy quorum by itself.
- A stale or unavailable decision-critical source holds the affected setup.
- Missing evidence is never replaced with a neutral value or invented record.
- Akber pass remains research eligibility, not execution authority.
- LLM and quantum outputs remain structured recommendations or reviews.
- Python remains the only orchestration actor allowed to invoke PaperOps.
- Q-CTRL consultation holds remain binding where the policy requires them.
- Idempotency, duplicate exposure, daily loss, trailing drawdown, concentration,
  liquidity, spread, paperability, and route checks remain fail-closed.
- Self-healing may retry safe reads and resumable calculations, but may not edit
  code, secrets, risk policy, authority, or broker state silently.
- Dashboard and Telegram remain read-only and command-disabled.
- No paper proof ledger entry automatically authorizes strategy promotion.
- No implementation step enables live capital.

## 6. Canonical Dual-Lane Policy

### 6.1 Research And Execution Classes

| Class | Purpose | Edge required | Paper order possible | Edge claim allowed |
| --- | --- | --- | --- | --- |
| `research_only` | Observe, score, backtest, and form hypotheses | No | No | No |
| `experimental_unvalidated` | Collect a real paper outcome from a complete current setup | No | Yes, after all experimental gates | No |
| `validated_paper_strategy` | Exercise a promoted edge under the paper mandate | Yes | Yes, after all normal gates | Yes, with qualified wording |
| `live_capital_candidate` | Separate future review state | Yes plus additional evidence | No in this plan | No automatic claim |

Every hypothesis, Router decision, PaperOps handoff, order, fill, position,
close, postmortem, and learning record must carry its class unchanged.

### 6.2 Experimental Candidate Contract

An experimental candidate must include at least:

```json
{
  "evidence_class": "experimental_unvalidated",
  "paper_trade_purpose": "real_forward_evidence_collection",
  "edge_id": null,
  "edge_validation_status": "not_yet_validated",
  "edge_claim_allowed": false,
  "research_goal_id": "...",
  "pattern_relationship_id": "...",
  "strategy_hypothesis_id": "...",
  "candidate_identity_id": "...",
  "source_evidence_ids": ["..."],
  "instrument": "...",
  "direction": "...",
  "thesis": "...",
  "invalidation": "...",
  "expires_at": "...",
  "akber_result_id": "...",
  "risk_proposal_id": "...",
  "router_decision_id": "...",
  "idempotency_key": "...",
  "route": "guarded_alpaca_paper_via_paperops"
}
```

The absence of `edge_id` is intentional for this class. Missing Research Goal,
pattern, hypothesis, Akber, risk, Router, identity, invalidation, expiry, source,
or route lineage is not allowed.

### 6.3 Proof Tiers

Proof must be split into four explicit tiers:

1. `broker_execution_fact`: a real order/fill/close occurred in Alpaca Paper.
2. `experimental_forward_outcome`: the real closed trade has complete
   experimental lineage and a completed postmortem.
3. `validated_edge_evidence`: the outcome is eligible for statistical review
   under a frozen edge policy; this is not granted merely by closing a trade.
4. `validated_edge_credit`: a separate promotion process has passed historical,
   out-of-sample, cost, robustness, and forward-evidence requirements.

The paper proof ledger may record tiers 1 and 2. Only the edge registry may
grant tiers 3 and 4. No backtest or synthetic record may enter tiers 1 or 2.

### 6.4 Frozen Initial Risk Policy

The existing canonical USD policy remains the starting policy:

- maximum position notional: US$5,000;
- maximum instrument exposure: 5% of equity;
- maximum strategy exposure: 15% of equity;
- maximum correlated-cluster exposure: 20% of equity;
- maximum high-correlation exposure: 10% of equity;
- maximum gross exposure: 40% of equity;
- maximum new notional per day: 20% of equity;
- maximum risk per position: 0.5% of equity;
- maximum daily loss: 2% of equity;
- maximum trailing drawdown: 8% of equity;
- maximum tail-stress loss: 4% of equity.

Sizing must use the smallest applicable limit. These values are read from the
versioned portfolio policy rather than duplicated across modules. Any future
change remains a reviewed proposal and cannot be made autonomously.

### 6.5 Source-Readiness Contract

The target is not a misleading `41 of 41 live` badge. Every canonical source
must have one evidence-backed state:

| State | Meaning | Candidate use |
| --- | --- | --- |
| `live_fresh` | A real provider observation is within its source-specific SLA | Eligible according to trust and quorum policy |
| `historical_only` | Licensed historical evidence exists but no current feed is used | Backtest and context only |
| `forward_only` | Current collection is available but historical archive is not | Current evidence after enough real observations |
| `temporarily_degraded` | A normally usable provider is stale, rate-limited, or failing | Hold affected setups |
| `unavailable` | No approved usable interface or history exists | Never treated as evidence |
| `excluded` | Intentionally omitted for licensing, quality, relevance, or safety | Never treated as evidence |

Live-capable sources should be activated wherever credentials, licensing,
quality, and cost allow. A source that cannot be live must be classified rather
than simulated. Experimental eligibility uses only real provider-backed current
observations and cannot rely on a historical-only or sample source as if it were
fresh.

### 6.6 Historical And Backtest Baseline

Before clean release, Qadam must re-certify that:

- every planned provider partition has an acquired or typed terminal state;
- immutable raw and normalized records retain provider provenance;
- point-in-time publication and availability timestamps prevent leakage;
- corporate actions, futures rolls, prediction-contract identity, calendars,
  time zones, costs, spreads, slippage, and proxy basis risk are represented;
- walk-forward, holdout, negative-control, placebo-lag, regime, drawdown, and
  false-discovery checks execute under the frozen protocol;
- zero validated edges remains a passing research result when no relationship
  survives promotion.

Backtest certification is required as research infrastructure. A positive edge
result is not required to begin the experimental paper epoch.

## 7. Implementation Foundation - Build Before State Change

This foundation is not one of the ten operational steps. It prepares and tests
the code before the broker account or active epoch changes.

### Objective

Make the dual-lane policy explicit and migratable without weakening validated
strategy or live-capital controls.

### Build

- Add `orchestrator/qadam_experimental_paper_policy.py` as the schema and policy
  owner.
- Add a versioned execution-mode artifact with separate booleans for research,
  experimental paper, validated paper, and live capital.
- Extend existing epoch, strategy hypothesis, Akber, risk, Router, handoff,
  lifecycle, proof, learning, and dashboard contracts with `evidence_class`.
- Add schema migration readers for existing records. Legacy rows default to
  `legacy_test`, never `experimental_unvalidated`.
- Keep the current edge-first certification intact as the validated-strategy
  certification.
- Add a separate experimental-release certification. Do not redefine an old
  `paper_trial_resume_allowed` field in a way that changes historical meaning.
- Make every policy transition explicit, versioned, and operator-approved.
- Preserve the current dashboard routes, sidebar, ten-stage lifecycle, copy,
  imagery, expandable behavior, and page structure.
- Re-run source capability, provenance, historical acquisition, point-in-time,
  and statistical backtest certification before any state change.
- Add an append-only implementation log and machine-readable phase status. The
  status generator may update progress fields but may not rewrite this plan's
  normative policy, authority, risk, or acceptance criteria.

### Artifacts

```text
data/runtime/qadam_experimental_paper_policy.json
data/runtime/qadam_execution_mode.json
data/runtime/qadam_experimental_contract_migration.json
data/runtime/qadam_autonomous_experimental_epoch_status.json
docs/qadam-autonomous-experimental-paper-epoch-implementation-log.md
```

### Checks

```text
scripts/check_qadam_experimental_paper_policy.py
scripts/check_qadam_experimental_contract_migration.py
```

### Acceptance

- Zero existing validated-edge checks are silently removed.
- Zero legacy rows are upgraded to experimental or validated evidence.
- Every canonical source has one truthful operating class.
- Sample or fixture evidence contributes zero live freshness or quorum credit.
- Provider, point-in-time, and statistical backtest checks pass, including an
  honest `passed_no_validated_edge` result.
- Live-capital flags remain false.
- The dashboard route and UX regression suites pass unchanged.
- All unsafe or unknown execution modes fail closed.

## 8. Step 1 - Provision A New US$100,000 Alpaca Paper Account

### Objective

Create a real broker-side clean starting point rather than a local visual reset.

### Operator Action

The operator creates a new Alpaca Paper account with US$100,000 starting equity
and generates new paper API credentials. Credentials are stored through the
existing local secret mechanism and are never pasted into logs, committed,
exported to the dashboard, or written by implementation code.

### Build

- Retain and extend the GET-only clean broker preflight.
- Verify `https://paper-api.alpaca.markets` and paper mode.
- Verify USD currency.
- Verify cash and equity are exactly US$100,000 within one cent.
- Verify zero positions and zero order history across all relevant order
  statuses and available history windows.
- Verify the new fingerprint differs from the testing account.
- Verify account status is active and the read-only market/account calls work.
- Record only hashes and public-safe metadata.

### Artifact

```text
data/runtime/qadam_clean_broker_account_preflight.json
```

### Acceptance

- `preflight_passed=true` from a fresh provider response.
- No broker write was attempted.
- No credential or complete account identifier appears in an artifact.
- Failure leaves the legacy epoch active and PaperOps watch-only.

## 9. Step 2 - Pause At A Safe Operating Checkpoint

### Objective

Quiesce the execution and projection layers before changing epoch identity.

### Build

- Add an audited pause-at-checkpoint operation to the local operator service.
- Stop dispatching new scoring, Router, and PaperOps work after the current safe
  unit finishes.
- Continue GET-only broker reconciliation until the quiescence snapshot is
  written.
- Require zero open testing-account positions and zero unresolved orders.
- Refuse to auto-close, cancel, or replace an old order merely to make cutover
  pass. Any exposure becomes an explicit operator action.
- Acquire a single cutover lease and reject concurrent cutovers.
- Record running worker state, in-flight jobs, locks, and last successful
  checkpoints.

### Artifacts

```text
data/runtime/qadam_clean_epoch_quiescence.json
data/runtime/qadam_clean_epoch_pause_receipt.json
```

### Checks

```text
scripts/check_qadam_clean_epoch_quiescence.py
```

### Acceptance

- Operator service is paused at a checkpoint, not killed mid-write.
- No worker remains in a critical write section.
- Broker exposure and unresolved-order counts are zero.
- Research lock and paper watch-only state remain active.
- No paper-calendar time has started.

## 10. Step 3 - Archive The Testing Epoch Immutably

### Objective

Preserve every testing record while preventing it from contaminating the clean
epoch.

### Build

- Inventory every execution-derived testing artifact and record count.
- Copy the inventory into `data/runtime/archive/<testing_epoch_id>/`.
- Write per-file SHA-256 checksums and one aggregate digest.
- Mark all archived execution rows `legacy_test` and proof-ineligible in the
  archive manifest without rewriting their original payloads.
- Preserve provider data, source memory, patterns, backtests, edge audits,
  strategy research, model reviews, and repair history outside the execution
  archive.
- Write the previous-epoch record but do not switch the active pointer until
  final broker verification succeeds.
- Make the archive operation idempotent and restart-safe.

### Artifacts

```text
data/runtime/archive/<testing_epoch_id>/manifest.json
data/runtime/archive/<testing_epoch_id>/checksums.json
data/runtime/archive/<testing_epoch_id>/archive_receipt.json
data/runtime/previous_paper_epoch.json
```

### Acceptance

- Every inventoried execution artifact is archived or explicitly classified.
- The aggregate digest verifies.
- No research artifact entered the execution archive.
- Re-running archive preparation creates no duplicate logical epoch.
- Failure restores the previous state and keeps the old dashboard truthful.

## 11. Step 4 - Perform Final Broker And Cutover Verification

### Objective

Re-read all decision-critical state after pause and immediately before changing
the active epoch.

### Build

- Repeat the new-account GET-only preflight after the service is paused.
- Verify account fingerprint, balance, currency, positions, orders, endpoint,
  and credential boundary again.
- Verify the testing archive digest and current-epoch pointer.
- Verify the old account has no unresolved lifecycle obligation.
- Verify the configured risk policy is the approved US$100,000 USD policy.
- Verify live-capital settings and live endpoints remain denied.
- Create a single-use, short-lived cutover-readiness receipt bound to the broker
  fingerprint, archive digest, policy hash, code commit, and dashboard release.

### Artifacts

```text
data/runtime/qadam_experimental_epoch_cutover_readiness.json
data/runtime/qadam_experimental_epoch_cutover_approval.json
```

### Acceptance

- Readiness has no critical blocker and is fresh at execution time.
- Readiness does not require a validated edge or completed forward outcome.
- Readiness does require clean broker truth, archive integrity, safe pause,
  paper-only authority, risk policy, and explicit human approval.
- The approval expires unused if any bound input changes.

## 12. Step 5 - Activate The Clean Epoch And Dashboard Atomically

### Objective

Make the new broker account, local epoch, and public dashboard agree from one
transactional cutover.

### Build

- Extend `orchestrator/qadam_clean_epoch_cutover.py` to consume the new
  experimental cutover readiness rather than edge-promotion readiness.
- Use epoch kind `clean_experimental_operator_epoch`.
- Write the new active epoch pointer atomically.
- Populate the first mirror from the verified Alpaca response, not a fabricated
  local balance.
- Clear only active execution projections after archive verification.
- Rebuild portfolio, history, orders, lifecycle, learning, cockpit, QSASE, and
  operator dashboard view models for the new epoch.
- Keep research findings, backtests, patterns, strategy families, source state,
  and quantum research visible.
- Keep the operator service paused and PaperOps watch-only until all projections
  pass.
- Roll back the active pointer and restore archived active files if any write or
  projection check fails.

### Trial Clock Correction

Creating the clean epoch does not yet start the 30-day paper growth trial. The
trial starts only after Step 7 successfully releases guarded autonomous paper
operation. This prevents watch-only setup time from consuming trial days.

### Required Dashboard Outcomes

| Existing surface | Required current-epoch state |
| --- | --- |
| Header and Portfolio | US$100,000, 100% cash, zero P&L, zero drawdown |
| Portfolio chart | First point from the verified cutover snapshot |
| Trading History | Empty current-epoch state; no testing rows or counts |
| Order Monitor | Zero orders, positions, and broker exceptions |
| Data Sources | Current truth and classifications preserved |
| Trading Universe | Existing 19-instrument structure preserved |
| Pattern Recognition | Existing research memory preserved |
| Quantum Edge | Existing evidence state preserved and honestly labelled |
| Trading Strategies | Core, emerging, and validated structure preserved |
| Decision Room | Experimental eligibility distinguished from validation |
| Results & Lessons | No new paper lessons until a clean-epoch trade closes |
| Tests & Improvements | Research proposals preserved; no legacy P&L attribution |
| System | Clean epoch, watch-only, service pause, and paper route visible |

### Artifacts

```text
data/runtime/current_paper_epoch.json
data/runtime/paper_epochs.jsonl
data/runtime/qadam_clean_epoch_cutover_receipt.json
data/runtime/qadam_dashboard_epoch_isolation.json
```

### Acceptance

- Broker, local runtime, static fallback, and live dashboard agree on US$100,000.
- Active positions, orders, closed trades, postmortems, P&L, drawdown, and paper
  proof entries are zero.
- The testing archive remains verifiable but is absent from current views.
- Trial state is `not_started_waiting_for_guarded_release`.
- PaperOps remains watch-only.

## 13. Step 6 - Enable Experimental Paper Eligibility

### Objective

Allow complete current hypotheses to become experimental paper-review
candidates without calling them validated edges.

### Eligibility Gates

Every setup must have:

- a current Research Goal;
- a distinct pattern or source-price relationship;
- a configured or emerging strategy hypothesis;
- a distinct candidate identity and idempotency material;
- at least two independent source families where the strategy requires quorum;
- fresh decision-critical sources and price context;
- instrument identity, direction, thesis, expiry, and invalidation;
- a paperable Alpaca proxy with explicit proxy or basis risk;
- complete Akber context and an Akber pass;
- current technical, volume/flow, volatility, pricing-gap, liquidity, and spread
  evidence where required by the setup;
- nonlinear or quantum review state honestly labelled as hardware, simulator,
  classical fallback, not run, or not useful;
- a passing portfolio-risk proposal under the frozen policy;
- no duplicate exposure or correlated-cluster conflict;
- no daily-loss or trailing-drawdown breach;
- one final Router state;
- no Q-CTRL consultation hold;
- the guarded Alpaca Paper route and no live route.

Historical edge validation is not required for
`experimental_unvalidated`. Missing current tradeability evidence remains a
hold; the experimental lane is not a shortcut around Akber or risk.

### Build

- Extend the canonical strategy-hypothesis schema with evidence class and paper
  experiment purpose.
- Extend Akber outputs to preserve the evidence class without changing its
  deterministic veto, hold, and pass precedence.
- Extend the portfolio-risk engine to size experimental setups using the same
  or stricter policy as validated setups.
- Extend the V3 Router with exactly one new terminal state:
  `experimental_paper_review_candidate`.
- Keep `validated_paper_review_candidate` distinct.
- Extend the canonical V3 PaperOps handoff schema. Do not create a second
  handoff file or alternate broker route.
- Make handoff lineage validation class-specific:
  `experimental_unvalidated` requires a pattern relationship and decision-time
  shadow snapshot but intentionally has no `edge_id`; `validated_paper_strategy`
  continues to require the promoted edge and completed shadow evidence.
- Require a decision-time counterfactual shadow snapshot, while allowing the
  real paper outcome to become the forward evidence being collected.
- Update why-not-trading-now output to identify the first actionable blocker in
  plain language.

### Artifacts

```text
data/runtime/qadam_experimental_paper_eligibility.json
data/runtime/qadam_experimental_paper_candidates.jsonl
data/runtime/qadam_router_v3_decisions.jsonl
data/runtime/qadam_paperops_handoff_v3.jsonl
data/runtime/qadam_why_not_trading_now.json
```

### Checks

```text
scripts/check_qadam_experimental_paper_eligibility.py
scripts/check_qadam_akber_filter_v3.py
scripts/check_qadam_portfolio_risk_engine.py
scripts/check_qadam_router_v3_paperops.py
```

### Acceptance

- Zero-edge input can produce an experimental candidate only when every listed
  current-evidence and safety gate passes.
- An experimental candidate cannot be labelled validated.
- Akber pass alone cannot create a candidate or order.
- Missing invalidation, stale evidence, failed quorum, excessive notional,
  duplicate exposure, drawdown breach, or Q-CTRL hold blocks handoff.
- The absence of an eligible setup correctly results in `ready_idle`, not a
  forced trade.

## 14. Step 7 - Release The Canonical Guarded PaperOps Route

### Objective

Release only experimental paper writes for the active clean epoch while keeping
validated-strategy and live-capital authority separate.

### Build

- Add `experimental_paper_release_ready` as a distinct release flag.
- Keep `validated_strategy_promotion_ready` false when no edge exists.
- Keep `live_capital_release_allowed` permanently false in this plan.
- Refactor `orchestrator/qadam_guarded_paper_launch.py` so the experimental mode
  consumes the new release certification and accepted experimental handoff.
- Extend the existing V3 handoff consumer and
  `paperops_qualified_setup_production.py` bridge so an accepted experimental
  handoff becomes a qualified setup only under the class-specific lineage
  contract. Preserve the current consumption receipt from Router through
  staging, submission, fill, close, and postmortem.
- Prove the wrapper rejects an experimental handoff if it still expects a
  validated `edge_id`, and rejects a validated handoff if its edge or completed
  shadow lineage is missing.
- Preserve the exact canonical wrapper:

```text
.venv/bin/python scripts/run_paperops_autonomous_pass.py
```

- Keep Python as the only actor allowed to invoke that wrapper.
- Require explicit one-time human approval for the bounded experimental paper
  mandate and policy version. Individual trades remain autonomous only inside
  that approved mandate.
- Release the research lock narrowly: research work stays allowed; PaperOps may
  write only for the active epoch and accepted handoff class.
- Keep direct broker calls outside PaperOps prohibited.
- Do not automatically retry a PaperOps write after ambiguous transport state.
  Reconcile idempotency and broker state first.
- Start the real 30-day paper growth trial atomically with the successful launch
  receipt and operator-service resume.

### Artifacts

```text
data/runtime/qadam_experimental_paper_release_readiness.json
data/runtime/qadam_experimental_paper_release_approval.json
data/runtime/qadam_guarded_paper_launch_receipt.json
data/runtime/qadam_paper_trial_calendar.json
```

### Acceptance

- Active epoch fingerprint matches the new broker account.
- Paper endpoint is exact and live endpoint is denied.
- Experimental paper writes are enabled only for the approved policy version.
- Validated-edge count may remain zero without blocking experimental launch.
- The canonical wrapper is the only broker-writing process.
- Trial day 1 starts from the real release timestamp.
- A launch with no eligible handoff becomes healthy `ready_idle`.

## 15. Step 8 - Run The Full Autonomous Learning Loop

### Objective

Operate Qadam continuously as a bounded experimental paper fund and evidence
engine.

### Canonical Loop

```text
Observe fresh sources and prices
-> align point-in-time evidence
-> score relationships
-> update labels and backtests when windows mature
-> run classical, nonlinear, and quantum review
-> form or refine a strategy hypothesis
-> apply Akber's 6-Stage Filter
-> size through portfolio risk
-> issue one Router decision
-> hand off only eligible paper-review candidates
-> submit through guarded Alpaca Paper
-> reconcile order, fill, position, and close lifecycle
-> write a postmortem and attribution record
-> propose an improvement
-> test before any reviewed version returns to Observe
```

### Build

- Make the launchd-supervised operator service the single cadence owner.
- Preserve source refresh, market-price refresh, pattern scoring, ordered
  research validation, Akber, shadow, risk, Router, PaperOps, lifecycle,
  learning, dashboard, and notification jobs.
- Keep the five configured strategy families active as research frameworks,
  while allowing source-price patterns outside them to form emerging strategy
  hypotheses through the same evidence and governance path.
- Ensure every surfaced pattern explains its source signal, affected market,
  evidence, confidence, historical result, current blocker, and next action.
- Compare classical and quantum-assisted work on matched inputs and evaluation
  windows; preserve an honest `unproven` conclusion when incremental quantum
  value is not measurable.
- Run the opportunity and eligibility refresh frequently enough for current
  evidence while keeping guarded PaperOps submission at its audited cadence.
- Let multiple distinct qualified setups proceed in one day only when each has
  unique lineage, idempotency, risk budget, and no exposure conflict.
- Keep the daily trading target a discipline target, never a forced quota or
  hard ceiling.
- Poll accepted orders through unambiguous lifecycle states and apply the
  versioned stale-order policy.
- Keep exits, cancellation, replacement, and reconciliation inside their
  existing guarded paths.
- Feed real outcomes and non-trades into attribution and learning.
- Let Gemma, the configured frontier model, and the quantum review layer produce
  structured research contributions only. Their availability and fallback mode
  must be visible and never implied.
- Refresh Qadam's machine-readable self-model on every operating cycle with
  source quality, model availability, model latency, quantum mode, compute
  pressure, disk state, broker route, open risk, degraded components, and the
  current why-not-trading reason. Self-model awareness may change scheduling or
  hold a decision, but it cannot create authority or silently change policy.
- Require the laptop to remain powered, networked, and awake for uninterrupted
  operation. If it sleeps, record the outage honestly, resume from checkpoints
  after wake, and never backfill missed observations or trial time.
- Publish dashboard-safe status through the one-way public bridge.
- Send only short, specific, deduplicated Telegram summaries when their
  notification gate permits it.

### Operational Artifacts

```text
data/runtime/qadam_operator_service_status.json
data/runtime/qadam_operator_service_heartbeats.json
data/runtime/qadam_operator_service_receipts.jsonl
data/runtime/paperops_autonomous_pass_summary.json
data/runtime/qadam_clean_epoch_operating_status.json
data/runtime/qadam_operator_dashboard_view_model.json
data/runtime/cockpit-status.json
```

### Acceptance

- The operator service restarts after process exit and laptop restart.
- Every due job has an owner, cadence, receipt, timeout, and circuit state.
- Source or model degradation holds affected decisions without falsifying global
  system health.
- PaperOps runs only when an accepted current-epoch handoff exists.
- No candidate yields healthy `ready_idle` rather than an error.
- Dashboard and broker mirrors remain fresh and reconciled.
- No autonomous code, policy, secret, or authority mutation occurs.

## 16. Step 9 - Complete The Seven-Session Reliability Soak In Parallel

### Objective

Earn confidence that the released experimental paper service can operate
unattended across real failures without delaying the beginning of the paper
experiment.

### Policy

The soak no longer blocks clean experimental launch. It does block the stronger
claim `unattended_reliability_certified` and remains mandatory before any future
live-capital review.

Because the release policy changes materially, the post-cutover soak is bound
to the new code, policy, epoch, and service hashes. Pre-cutover sessions remain
historical evidence but do not silently certify changed code.

### Build

- Count at most one session per real UTC calendar date.
- Require seven real sessions with no simulated or backfilled time.
- Exercise normal restart, laptop sleep/wake, transient network loss, provider
  rate limiting, stale artifact recovery, interrupted resumable work, disk
  pressure warning, and dashboard publisher interruption.
- Confirm safe reads may retry, while PaperOps writes never retry blindly.
- Confirm new entries freeze on safety defects while read-only reconciliation
  and existing-position lifecycle monitoring continue.
- Record repair requests for code defects rather than editing code silently.

### Artifacts

```text
data/runtime/qadam_operator_soak_v3.json
data/runtime/qadam_operator_resilience_probes.json
data/runtime/qadam_operator_repair_queue.json
```

### Acceptance

- Seven real sessions complete for the same version-bound release.
- No simulated time is present.
- No duplicate order results from restart or retry.
- No critical repair request remains unresolved.
- Public status becomes explicitly stale during publisher interruption and
  recovers without accepting inbound commands.
- Failure before completion does not erase paper history; it freezes new entries
  until repaired.

## 17. Step 10 - Run The 30-Day Paper Growth Trial And Build Proof

### Objective

Use real market time and real Alpaca Paper outcomes to determine whether Qadam's
research, filters, strategies, and operating system add value.

### Build

- Derive trial day only from the immutable launch timestamp and real calendar.
- Preserve the actual calendar through sleep, outage, restart, and no-trade days.
- Record every considered setup, Akber pass/hold/veto, Router decision, order,
  fill, close, missed opportunity, and no-order counterfactual.
- Calculate net paper return, benchmark-relative return, realized and unrealized
  P&L, drawdown, Sharpe, Sortino, hit rate, expectancy, turnover, concentration,
  slippage, spread cost, proxy basis risk, and regime dependence.
- Attribute outcomes to sources, pattern methods, models, quantum review, Akber,
  risk, Router, PaperOps, and execution quality.
- Compare experimental decisions with wait, veto, and no-order alternatives.
- Continue historical and walk-forward testing as new labels mature.
- Allow a paper outcome to inform edge promotion, but never auto-promote on one
  trade or one profitable period.
- Keep every improvement proposal-first, tested, reviewed, versioned, and
  reversible.

### Artifacts

```text
data/runtime/qadam_paper_trial_calendar.json
data/runtime/qadam_experimental_paper_outcomes.jsonl
data/runtime/qadam_paper_proof_eligibility.json
data/runtime/qadam_learning_attribution_v3.jsonl
data/runtime/qadam_paper_performance_summary.json
data/runtime/qadam_30_day_paper_growth_trial_summary.json
```

### Acceptance

- Only real closed current-epoch Alpaca Paper trades can become paper-trade
  facts in the paper proof ledger.
- Experimental outcomes are clearly distinct from validated-edge credit.
- No trial day is manufactured or backfilled.
- A correct day may contain zero trades.
- A poor result is retained and explained, not hidden or reset.
- Day 30 produces an evidence-based continue, revise, or stop recommendation.
- Completion never enables live capital automatically.

## 18. Dashboard And Communication Contract

The current dashboard information architecture and visual design are protected.
This implementation enriches data and labels only where needed.

### Required Truth Changes

- Portfolio and Trading History are scoped strictly to the active epoch.
- Decision Room distinguishes `experimental paper review` from `validated
  strategy`.
- Trading Strategies shows experimental evidence without moving a strategy into
  the validated section.
- Pattern Recognition preserves research scores and evidence maturity.
- Quantum Edge reports hardware, simulator, fallback, or not-run truth.
- Order Monitor shows only the clean account and current epoch.
- Results & Lessons distinguishes research lessons, experimental paper outcomes,
  and validated strategy evidence.
- Tests & Improvements shows proposals and their review state, never silent
  production mutation.
- System shows service, epoch, release mode, trial day, soak progress, source
  degradation, repair queue, and paper-only route.

### Public-Safe Wording

The dashboard may say:

- `Experimental paper operation running`;
- `No eligible setup right now`;
- `Paper trade submitted for forward evidence collection`;
- `Validated edge count: 0`;
- `Quantum advantage remains unproven`.

It must not say:

- `proven edge` for an experimental setup;
- `live trading` for Alpaca Paper;
- `all sources live` when some are historical-only or unavailable;
- `quantum advantage` without matched out-of-sample evidence;
- `profit guaranteed` or equivalent language.

## 19. Final Certification

### Build

Create:

```text
scripts/check_qadam_autonomous_experimental_paper_epoch.py
data/runtime/qadam_autonomous_experimental_paper_epoch_certification.json
```

The certification must expose three separate outcomes:

1. `implementation_complete`: code, schemas, migrations, tests, and negative
   probes pass.
2. `autonomous_experimental_paper_operation_running`: clean account, epoch,
   dashboard, service, release, and guarded paper route are operating now.
3. `unattended_reliability_certified`: seven version-bound real soak sessions
   have completed.

It must also report, without turning them into implementation blockers:

- current trial day and days remaining;
- submitted, open, and closed paper-trade counts;
- validated-edge count;
- real forward outcomes;
- current P&L and drawdown;
- quantum review and advantage state;
- why-not-trading-now;
- active repair requests.

### Operational Pass Conditions

`autonomous_experimental_paper_operation_running` may pass with zero trades and
zero validated edges when:

- the clean US$100,000 broker account is fresh and reconciled;
- the clean epoch and dashboard are isolated from testing history;
- the operator service is running;
- experimental paper release is active;
- live capital is disabled;
- there is no eligible candidate and the canonical state is `ready_idle`; or
- an eligible candidate has progressed only through the guarded route.

It must fail if any old history leaks, the broker balance disagrees, the account
is not paper, the service is stale, the route is bypassed, an unsafe candidate
passes, trial time is fabricated, or proof is overstated.

## 20. Required Negative Tests

The implementation is incomplete until tests prove Qadam rejects:

- live broker URLs or live-capital flags;
- the old broker-account fingerprint;
- a non-US$100,000 or non-USD clean account;
- any position or order history at cutover;
- an expired cutover approval;
- archive checksum mismatch;
- legacy history in current dashboard projections;
- experimental records labelled validated;
- a candidate without Research Goal, pattern, hypothesis, invalidation, or
  expiry;
- one-source quorum masquerading as independent confirmation;
- stale decision-critical evidence;
- missing Akber context;
- Akber hold or veto routed as eligible;
- an order over the US$5,000 absolute ceiling;
- instrument, strategy, source-family, correlation, gross, daily-loss, or
  drawdown limit breaches;
- duplicate candidate, exposure, or idempotency keys;
- an active Q-CTRL consultation hold;
- an unsupported or non-paperable instrument;
- direct LLM, quantum, dashboard, Telegram, or alternate-script broker writes;
- blind PaperOps retry after ambiguous transport state;
- synthetic, historical, fixture, or shadow proof credit;
- simulated or backfilled 30-day trial time;
- silent code, secret, risk-policy, or authority mutation;
- a failed cutover that does not restore the previous pointer and files.

## 21. Operator Runbook

The implementation must support this audited operational order:

1. Freeze and record code, policy, broker, epoch, dashboard, and runtime hashes.
2. Run all implementation and negative tests while the current system remains
   watch-only.
3. The operator creates a new US$100,000 Alpaca Paper account and stores its new
   paper credentials securely.
4. Run the fresh GET-only broker preflight.
5. Pause the operator service at a safe checkpoint.
6. Verify zero unresolved testing-account exposure.
7. Prepare and verify the immutable testing archive.
8. Run the final bound cutover readiness check.
9. Request explicit operator cutover approval.
10. Execute the atomic clean-epoch cutover.
11. Verify local, static, preview, and production dashboard epoch isolation.
12. Run experimental eligibility and route negative probes.
13. Request explicit experimental paper-mandate approval.
14. Release only the guarded experimental PaperOps route.
15. Start the real 30-day trial and resume the launchd operator service.
16. Run one canonical autonomous pass and report only its canonical summary.
17. Verify the system is either safely trading an eligible setup or correctly
    `ready_idle`.
18. Continue the seven-session soak and 30-day trial over real time.

No step may be skipped because a dashboard looks correct.

## 22. Expected Code Change Map

| Area | Required change |
| --- | --- |
| `qadam_paper_epoch.py` | Add experimental epoch class and explicit trial-start state |
| `qadam_clean_broker_preflight.py` | Strengthen new-account and empty-history verification |
| `qadam_clean_epoch_cutover.py` | Consume experimental cutover certification; use provider-backed initial mirror |
| `qadam_guarded_paper_launch.py` | Add experimental release mode without weakening validated or live gates |
| Strategy Foundry V3 | Carry experimental evidence class and complete hypothesis lineage |
| Akber V3 | Preserve class; retain veto/hold/pass semantics |
| Portfolio risk engine | Apply frozen US$100,000 policy and US$5,000 absolute ceiling |
| Router V3 | Add one experimental paper-review state and preserve single-state output |
| PaperOps V3 handoff consumer | Accept only canonical current-epoch experimental or validated handoffs |
| PaperOps qualified-setup bridge | Validate class-specific lineage and preserve the V3 consumption receipt |
| Lifecycle and proof | Add tiered execution fact, experimental outcome, and edge-credit separation |
| Learning attribution | Attribute experimental outcomes without automatic policy mutation |
| Operator service | Release exact PaperOps wrapper only after experimental approval |
| Dashboard view models | Scope execution data to current epoch and expose evidence class |
| Telegram | Summarize experimental status briefly without commands or edge claims |
| Certification | Add one final experimental-epoch checker and artifact |

## 23. Implementation Order And Commit Boundaries

Use small, reversible commits:

1. policy, schemas, and migrations;
2. cutover and broker preflight;
3. dashboard epoch isolation;
4. experimental eligibility through Akber, risk, and Router;
5. canonical PaperOps handoff and release;
6. lifecycle, proof tiers, and learning;
7. operator service, soak, and self-healing;
8. final certification, production verification, and runbook evidence.

Do not combine broker-account cutover with untested schema changes. Do not
deploy a dashboard that advertises the clean epoch before broker and local
runtime truth agree.

## 24. Final Acceptance Criteria

The plan is implemented only when all of the following are true:

1. The dual-lane policy exists and fails closed.
2. The new Alpaca account is paper-only, USD, exactly US$100,000 cash/equity,
   and empty.
3. The testing epoch is immutable, checksummed, locally auditable, and absent
   from active views.
4. Research memory survives unchanged.
5. Every source has a truthful class, and only live provider-backed evidence
   contributes current freshness or quorum.
6. Historical acquisition, point-in-time safety, and backtest recertification
   pass without requiring a positive edge.
7. The clean experimental epoch is the only active execution epoch.
8. The current dashboard design and route structure remain intact.
9. Portfolio, Trading History, and Order Monitor agree with the clean broker.
10. Zero validated edges is displayed honestly and does not block experimental
   paper operation.
11. An experimental candidate requires complete current evidence, Akber, risk,
   Router, idempotency, exposure, drawdown, Q-CTRL, and paper-route gates.
12. The frozen US$5,000 and portfolio-risk limits apply to every experimental
    setup.
13. No trade is forced.
14. Every broker write uses the exact canonical PaperOps wrapper and Alpaca
    Paper endpoint.
15. The operator service runs the end-to-end audited loop continuously.
16. A no-setup state is healthy `ready_idle`.
17. Paper lifecycle records are unambiguous and current-epoch scoped.
18. Real closed experimental trades enter the paper proof ledger only at the
    correct proof tier.
19. Experimental outcomes do not create automatic validated-edge credit.
20. Learning remains proposal-first and human-governed.
21. The 30-day paper growth trial starts from the real release timestamp only.
22. Soak and trial calendars contain no simulated or backfilled time.
23. Dashboard and Telegram remain read-only and command-disabled.
24. Live capital and live broker endpoints remain disabled.
25. Every required negative probe passes.
26. The final experimental-epoch certification reports autonomous operation
    running, even if the current outcome is zero trades and zero validated
    edges.

## 25. Honest Completion Statement

When the operational certification passes, Qadam may be described as:

> Qadam is running autonomously as a guarded experimental paper fund from a
> clean US$100,000 Alpaca Paper account. It continuously observes, researches,
> tests, filters, risk-sizes, routes, paper trades when qualified, reconciles,
> and learns. Its experimental trades collect forward evidence; they are not
> represented as validated edges. Live capital remains disabled.

It may not yet be described as profitable, edge-proven, quantum-advantaged, or
live-capital ready. Those claims remain evidence outcomes that must be earned
over real time.
