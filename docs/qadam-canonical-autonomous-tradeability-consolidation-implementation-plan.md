# Qadam Canonical Autonomous Tradeability Consolidation Implementation Plan

Date: 2026-08-19

Status: Implemented on 2026-08-19. CATC-0 through CATC-17 code and migration
acceptance checks pass. The installed build must still accumulate five distinct
real US market sessions before `observation_ready` can be certified; those
sessions are never simulated or backfilled.

Scope: Consolidate Qadam's evidence, decision, reliability, scheduling,
PaperOps, lifecycle, learning, and public-projection paths into one durable
paper-only operating system

## 1. Executive Decision

Qadam does not need another trading lane, another evidence adapter, another
Router version, or another dashboard status artifact. It needs one canonical
operating path and a controlled retirement of the overlapping paths that have
accumulated around it.

The current system has real strengths:

- provider-backed historical data;
- a broad source and instrument catalogue;
- pattern scoring and strategy research;
- a canonical tradeability compiler;
- Akber's 6-Stage Filter;
- forward shadow, portfolio risk, Router, and PaperOps components;
- a real guarded Alpaca Paper route;
- real paper orders and lifecycle records;
- a supervised operator service;
- a carefully designed read-only dashboard.

It also has one structural weakness: those capabilities are joined by a large,
stateful, file-based directed graph containing overlapping V2, V3, V4, QSASE,
QEG, evidence-fit, experimental, and legacy PaperOps contracts. A repair can
pass inside one path while a scheduled writer, checker, projection, or old
consumer continues to use another. That is why similar trade-stopping failures
have returned after apparently successful fixes.

This programme turns Qadam into one canonical transaction:

```text
current provider-backed trigger
  -> typed evidence envelope
  -> current execution context
  -> Akber decision
  -> decision-time shadow snapshot
  -> portfolio-risk decision
  -> one Router state
  -> immutable PaperOps handoff
  -> guarded Alpaca Paper submission
  -> order and position lifecycle
  -> postmortem and learning attribution
```

Every genuinely eligible setup must reach exactly one of two outcomes within
the latency budget:

1. one idempotent guarded paper order; or
2. one accurate, primary blocker grounded in current evidence or a hard safety
   rule.

Schema drift, scheduling starvation, artifact overwrites, stale generation
mixing, missing internal adapters, optional dashboard checks, and lost lineage
must never be accepted as ordinary reasons not to trade.

This plan can make Qadam substantially more reliable and more capable of taking
small paper experiments when its evidence supports them. It cannot guarantee a
trade every day, a profitable strategy, or a return. Zero trades remains the
correct result when there is no real trigger or a hard safety condition fails.

## 2. Why A Consolidation Is Required

### 2.1 Current Funnel Evidence

The latest codebase and runtime audit found 228 active-discovery evaluations:

| Root cause | Count | Meaning |
| --- | ---: | --- |
| `no_real_trigger` | 141 | A genuine market reason to remain idle |
| `evidence_conversion_defect` | 56 | Evidence existed but was not translated into the required contract |
| `risk_veto` | 13 | A genuine hard or portfolio-risk rejection |
| `mapping_defect` | 9 | Instrument, proxy, strategy, or route mapping failed |
| `akber_hold` | 6 | Evidence reached Akber but did not pass |
| `duplicate_exposure` | 2 | Correct idempotency or exposure protection |
| No classified cause | 1 | Classification defect to eliminate |

Of those evaluations, 206 stopped at Stage 2 and 209 never reached Akber.
Sixty-five evaluations, or 28.5%, were lost to conversion or mapping defects.
The recurring low trade count is therefore not explained by Akber alone.

### 2.2 Current Reliability Evidence

The operator receipt history contains 23,136 receipts:

- 7,848 completed;
- 13,561 skipped;
- 848 failed.

The largest failure groups were:

- `dashboard_refresh`: 527;
- `portfolio_router_review`: 213;
- `canonical_tradeability`: 101;
- `akber_review`: 5;
- `open_market_conversion`: 2.

The largest skip groups were:

- `not_due`: 7,481;
- `cycle_job_budget_exhausted`: 4,941;
- `resource_claim_busy`: 949;
- open circuit breaker: 103.

An optional quantum/dashboard checker generated hundreds of failures because a
local Qiskit Aer import was missing. Dashboard refresh still invokes a legacy
Router V2 checker and many unrelated certifications. Optional research and
publication work is therefore still coupled to operating health.

### 2.3 Current Complexity Evidence

The present checkout contains approximately:

- 391 Python files under `orchestrator/`;
- 505 `check_*.py` scripts;
- 4,572 runtime JSON or JSONL files;
- 51 implementation plans or implementation logs.

Complexity is not itself a defect. The defect is that too many of these files
can still participate in active truth, service health, or workflow ownership.

### 2.4 Current Data Reality

Qadam has 746,275 provider-backed historical rows, 223 acquired partitions,
137 honestly classified unavailable partitions, 41 registered sources, and 19
watched instruments. The canonical empirical score-label dataset has been much
narrower:

- five historically usable source signals: Kalshi, Polymarket, SEC EDGAR,
  STOCK Act, and USGS;
- 17 usable listed instruments in the empirical run;
- 40,198 score rows;
- 40,092 label rows;
- 11,921 independent pairs;
- 336 attempted hypotheses;
- 10 raw significant results;
- zero surviving multiple-testing correction;
- zero validated edges.

The 41-source label describes catalogue breadth. It must not be presented or
used internally as 41 independent, point-in-time alpha signals.

### 2.5 Current Tradeability Evidence

The current SMH discovery setup illustrates the desired and broken behavior:

- a 0.72964 research score ranked the relationship highly;
- the score was not a probability or proof of an edge;
- a fresh semiconductor catalyst existed;
- volatility and market-flow context existed;
- provisional positive expectancy existed but was not validated;
- SMH was a valid paper proxy;
- the remaining missing field was a current actionable spread outside regular
  market hours.

Akber correctly held the setup at execution outside market hours. Downstream
projections then presented several consequences as if they were independent
blockers: no Akber pass, no shadow snapshot, expected return not reached, and
incomplete risk. The correct primary answer was one blocker: current execution
context was unavailable because the market was closed.

During regular market hours, failure to obtain that context must become a
provider-recovery incident with bounded retries, not a permanent investment
hold.

### 2.6 Current Lineage Evidence

Qadam submitted real paper trades, including ITA and XLE orders on 18 August.
Some recent lifecycle records nevertheless report incomplete Qadam-origin
lineage even where generation and consumption identifiers exist.

The immediate defect is concrete: the current handoff consumer writes the
accepted-handoff and receipt JSONL files as current-snapshot replacements.
When a later generation contains no handoffs, the empty generation overwrites
the historical verification files. Learning and proof readers then lose the
evidence needed to attribute earlier trades.

This is a control-plane storage defect. Another reader-side fallback is not an
acceptable permanent repair.

## 3. Root-Cause Thesis

The repeated failure class is:

> Qadam evolved through additive patches on top of a mutable file-based DAG,
> without one transactional decision boundary, while release checks proved
> components and fixtures more often than sustained real-market journeys.

The consequences are:

1. Multiple modules can produce conceptually equivalent evidence in different
   schemas.
2. Multiple readers reconstruct tradeability from different artifact sets.
3. Current-snapshot JSONL files are sometimes mistaken for durable ledgers.
4. Empty generations can erase history.
5. One missing upstream field cascades into several misleading blockers.
6. The scheduler can spend its cycle budget on non-latency-sensitive work while
   market decisions wait.
7. Dashboard or optional quantum checks can open circuits that appear to affect
   the whole system.
8. Synthetic and broker-disabled tests can pass without proving that a real
   provider-backed market-hours setup survives the installed service.
9. Policy thresholds have been relaxed without consistently repairing the
   producer and consumer contracts needed to use them.
10. Plans and logs can disagree about whether the same capability is planned,
    implemented, active, superseded, or certified.

## 4. Programme Objectives

This plan must achieve all of the following:

1. Establish one authoritative runtime hierarchy and one active decision path.
2. Store control-plane events transactionally and preserve them append-only.
3. Keep large research data in immutable, versioned generations.
4. Compile all current evidence into one typed `TradeabilityEnvelope`.
5. Build execution context, Akber, shadow, risk, and Router decisions inside one
   decision transaction and generation.
6. Separate hard safety gates from soft evidence-strength gates.
7. Convert missing soft evidence into a bounded size haircut or research hold,
   rather than an automatic veto, where the frozen paper policy permits it.
8. Preserve hard risk, route, idempotency, duplicate-exposure, drawdown, and
   live-capital boundaries without exception.
9. Reserve market-hours scheduler capacity for current evidence, conversion,
   decision, handoff, PaperOps, and lifecycle work.
10. Isolate research, quantum, dashboard, Telegram, and publication failures
    from the execution control plane.
11. Preserve complete trade lineage through empty future generations.
12. Make every no-trade result identify one primary cause and its owner.
13. Remove superseded writers and checkers from active scheduling.
14. Preserve the existing dashboard UX and route structure.
15. Prove the installed system across five consecutive real market sessions.
16. Make strategy and gate calibration empirical, versioned, reversible, and
    paper-only.

## 5. Non-Negotiable Boundaries

Every phase must preserve these invariants:

| Boundary | Required state |
| --- | --- |
| Capital mode | Paper only |
| Broker route | Guarded Alpaca Paper through canonical PaperOps only |
| Live endpoint | Disabled and denied |
| Direct model-to-broker access | Forbidden |
| Dashboard and Telegram | Read-only and command-disabled |
| Quantum and LLM order authority | None |
| Maximum paper notional | Existing US$5,000 hard ceiling |
| Daily loss and drawdown protection | Binding |
| Duplicate exposure and idempotency | Binding |
| Missing current quote or spread | Never invented or silently neutralized |
| Historical or shadow result | Never represented as a real order |
| Experimental trade | Never represented as a validated edge |
| Proof credit | Real closed trade plus complete lineage and separate proof audit |
| Code self-repair | Repair request only; no silent code editing |
| Secrets and `.env` files | Never edited by this programme |
| Paper trial calendar | Real elapsed time only; no backfill |
| Dashboard UX and routes | Protected |

There is no daily trade quota. The discipline target is to evaluate every
distinct eligible setup promptly. Multiple distinct setups may trade on the
same day; zero setups may trade when none is genuinely eligible.

### 5.1 RCA-To-Phase Traceability

| Recurring failure class | Permanent repair owner | Production proof |
| --- | --- | --- |
| Parallel V2, V3, V4, QSASE, and QEG authority | CATC-1, CATC-4, CATC-15 | One-writer and supersession audits show one active path |
| Current-snapshot files used as historical ledgers | CATC-2, CATC-10, CATC-11 | Empty-generation and projection-rebuild tests preserve all prior events |
| Evidence conversion defects | CATC-5, CATC-6 | Zero conversion defects across the five-session soak |
| Strategy, instrument, or proxy mapping defects | CATC-5, CATC-6 | Every accepted trigger resolves to a versioned instrument and route |
| Missing actionable spread or liquidity context | CATC-7 | Market-hours provider canary returns context or one provider incident |
| Akber requirements exceeding collectable evidence | CATC-5, CATC-8 | Every hard field has a producer; soft fields apply declared haircuts |
| Shadow and risk generated too late or from another generation | CATC-9 | Same-generation decision integrity is 100% |
| Several downstream blockers caused by one upstream hold | CATC-4, CATC-9 | Every stopped transaction has one primary blocker |
| Scheduler budget and resource starvation | CATC-12 | Zero latency-sensitive starvation events in five sessions |
| Dashboard or quantum checks breaking operating health | CATC-12, CATC-14 | Domain-isolation fault tests pass |
| Synthetic tests passing while real market flow fails | CATC-16 | Installed provider-backed market-hours soak passes |
| Trade lineage disappearing after later empty cycles | CATC-2, CATC-10, CATC-11 | Append-only handoff-to-outcome audit passes |
| Catalogue breadth confused with usable alpha evidence | CATC-5, CATC-13 | Source capability and contribution reports reconcile |
| Plan, log, code, and installed-build status drift | CATC-0, CATC-1, Dynamic Plan Governance | Version-bound implementation status and release certification agree |

## 6. Authority And Supersession Hierarchy

### 6.1 New Authority Order

After cutover, authority will be resolved in this order:

1. constitutional paper-only and risk configuration;
2. transactional control-plane database;
3. immutable research-generation manifests;
4. canonical materialized JSON projections;
5. dashboard and Telegram summaries.

Lower layers may explain higher layers. They may not override them.

### 6.2 Existing Plans Retained As Inputs

| Existing programme | Treatment in this programme |
| --- | --- |
| Evidence-Fit Active Paper Trading | Retain evidence profiles and bounded `discovery_micro` policy |
| Canonical Tradeability Compiler | Retain strict envelope, critic, and same-generation concepts; reconcile plan status with implementation log |
| Permanent Operator Reliability Repair | Retain immutable research generations, resource ownership, and real revalidation |
| Compounding Evidence Graph | Keep as research memory and discovery input only |
| Autonomous Experimental Paper Epoch | Retain experimental versus validated evidence classes and US$5,000 ceiling |
| QSASE | Preserve historical research artifacts; remove active decision authority |
| Router V2 | Remove from active runtime and dashboard-health checks |
| Router V3 | Keep as the canonical Router implementation after transaction cutover |
| Legacy PaperOps internals | Keep behind one canonical adapter until safely migrated; forbid direct upstream consumers |

### 6.3 Required Supersession Register

Create a machine-readable register for every implementation family:

```json
{
  "component_family": "router_v2",
  "status": "retired_from_active_runtime",
  "replacement": "router_v3_transactional",
  "active_writers": [],
  "active_readers": [],
  "scheduled_checks": [],
  "historical_artifacts_retained": true,
  "rollback_adapter": "versioned_read_only_projection"
}
```

Certification must fail if a retired family still owns an active writer,
decision consumer, scheduler job, broker route, or health dependency.

## 7. Target Architecture

### 7.1 Storage Split

Use two storage classes rather than treating every JSON file as the same kind
of truth.

**Transactional control plane**

Use SQLite in WAL mode under the canonical `QADAM_STATE_ROOT` for:

- decision transactions;
- idempotency keys;
- generation state;
- gate decisions;
- accepted handoffs;
- handoff consumption receipts;
- broker submission references;
- order, fill, position, and close events;
- repair queue and circuit state;
- service-run receipts;
- outbox events for projections and notifications.

SQLite is appropriate for one supervised laptop operator, gives atomic local
transactions, uniqueness constraints, durable append-only records, crash
recovery, and consistent projections without introducing a remote database.

**Immutable research plane**

Keep large provider, source, price, feature, label, score, backtest, graph, and
quantum data in immutable generation files with:

- generation IDs;
- checksums;
- publication and availability timestamps;
- parser and schema versions;
- atomic manifest-pointer changes;
- reader leases;
- bounded retention and archive policy.

JSON dashboard files become rebuildable projections. They are not authoritative
ledgers.

### 7.2 Canonical Decision Transaction

One transaction must carry:

```json
{
  "decision_generation_id": "...",
  "research_goal_id": "...",
  "pattern_relationship_id": "...",
  "strategy_version_id": "...",
  "candidate_identity_id": "...",
  "evidence_class": "experimental_unvalidated",
  "trigger_id": "...",
  "source_evidence_ids": ["..."],
  "instrument": "...",
  "paper_proxy": "...",
  "direction": "long",
  "decision_timestamp": "...",
  "expires_at": "...",
  "tradeability_envelope_id": "...",
  "execution_context_id": "...",
  "akber_decision_id": "...",
  "shadow_snapshot_id": "...",
  "risk_decision_id": "...",
  "router_decision_id": "...",
  "handoff_id": "...",
  "idempotency_key": "...",
  "primary_blocker": null,
  "route": "guarded_alpaca_paper_via_paperops"
}
```

No downstream component may search unrelated runtime files to reconstruct a
missing field. It either reads the transaction or reports a producer defect.

### 7.3 Transaction State Machine

```text
observed
  -> trigger_qualified
  -> envelope_compiled
  -> execution_context_ready
  -> akber_passed | akber_held | akber_vetoed
  -> shadow_ready
  -> risk_approved | risk_rejected
  -> router_paper_review | router_hold | router_reject
  -> handoff_accepted
  -> paperops_consumed
  -> broker_submitted
  -> filled | cancelled | rejected | expired
  -> position_open
  -> position_closed
  -> postmortem_complete
```

Transitions are atomic, monotonic, timestamped, and versioned. An empty later
cycle cannot delete an earlier transition.

### 7.4 One-Blocker Model

Every stopped transaction records:

- one primary blocker;
- optional downstream consequences;
- blocker class: market, evidence, policy, risk, infrastructure, or defect;
- owning component;
- whether retry is safe;
- earliest retry condition;
- whether operator action is required.

For the SMH example:

```text
primary blocker: market_closed_execution_context_unavailable
consequences: Akber not passed, shadow not created, risk not evaluated
retry: next regular market session
owner: execution_context_service
```

The consequences must not appear as four independent failures.

## 8. Gate Model Recalibration

### 8.1 Hard Gates

The following remain fail-closed for every paper order:

1. paper account and paper endpoint verified;
2. live capital disabled;
3. paperable instrument or approved proxy;
4. real current trigger within its TTL;
5. current actionable price and spread during an open tradable session;
6. explicit direction, invalidation, expiry, and exit concept;
7. positive current net expectancy under the frozen cost model;
8. minimum reward-to-risk required by the active evidence profile;
9. position, strategy, cluster, gross-exposure, daily-loss, and drawdown limits;
10. duplicate-exposure and idempotency checks;
11. current broker/account reconciliation;
12. canonical PaperOps route;
13. no active kill switch, Q-CTRL hold, or safety-boundary violation.

### 8.2 Soft Gates

The following improve confidence but do not always need to veto a bounded
experimental paper trade:

- validated historical edge status;
- completed forward outcome history;
- source breadth beyond the profile minimum;
- optional technical indicators beyond one valid confirmation;
- optional volume or options-flow providers;
- quantum usefulness confirmation;
- high sample maturity;
- full strategy-family admission;
- additional critic agreement beyond the minimum accepted packet.

Missing soft evidence produces one of:

- a notional haircut;
- a shorter expiry;
- a tighter exposure cap;
- a `discovery_micro` classification;
- a forward-shadow-only state when current expectancy cannot be estimated.

It must not be relabelled as adverse evidence.

### 8.3 Evidence-Fit Profiles

Preserve and complete the existing profiles:

- event-catalyst: crude oil, defence, and semiconductors;
- regime-state: silver and power;
- market-dislocation: prediction markets;
- validated-strategy: promoted edges with stronger history requirements.

Each profile must declare:

- fields Qadam can collect now;
- provider and deterministic producer for each field;
- hard and soft fields;
- fallback provider order;
- maximum staleness by market session;
- size haircut for each missing soft field;
- minimum evidence class;
- allowed proxies;
- expiry and invalidation rules.

If a supposedly hard field has no real producer, certification fails before
Akber. It cannot become an indefinite runtime hold.

### 8.4 Empirical Akber Calibration

The historical Akber replay suggests both benefit and over-filtering: filtered
average returns and drawdown improved, but many good opportunities were also
removed and aggregate selection effect was negative in the recorded diagnostic
sample.

Run two paper-only profiles on the same eligible events:

- **control**: current Akber evidence profile;
- **challenger**: hard gates unchanged, soft evidence converted into bounded
  size haircuts.

Only the selected production profile may create an order. The other records a
counterfactual decision. Compare:

- opportunity capture;
- net return after costs;
- drawdown;
- false-positive rate;
- missed-opportunity rate;
- turnover and concentration;
- decision latency;
- outcome by strategy and evidence profile.

Automatic paper-profile promotion is allowed only within the frozen US$5,000
and portfolio-risk envelope after preregistered criteria pass. Expanding the
risk envelope or enabling live capital remains out of scope.

## 9. Modular Implementation Spine

| Phase | Name | Outcome |
| --- | --- | --- |
| CATC-0 | Quiescence, Evidence Freeze, And Worktree Protection | Reproducible baseline without losing current work |
| CATC-1 | Runtime Authority And Supersession Registry | One declared owner for every active truth |
| CATC-2 | Transactional Control-Plane Store | Durable atomic ledger and outbox |
| CATC-3 | Immutable Research Generation Contract | Stable evidence inputs for long-running readers |
| CATC-4 | Canonical Schemas And Decision Identity | One envelope, transaction, blocker, and lineage model |
| CATC-5 | Source Capability And Evidence-Usability Registry | Honest 41-source catalogue versus usable alpha inputs |
| CATC-6 | Trigger, Direction, Mapping, And Proxy Compiler | Eliminate conversion and mapping defects |
| CATC-7 | Market-Hours Execution Context Service | Reliable current price, spread, liquidity, and session truth |
| CATC-8 | Akber Evidence-Fit And Challenger Policy | Hard safety plus calibrated soft evidence |
| CATC-9 | Atomic Shadow, Risk, And Router Decision | One same-generation decision with one blocker |
| CATC-10 | Canonical Handoff And PaperOps Exactly-Once Path | One immutable handoff to one guarded wrapper |
| CATC-11 | Lifecycle, Exit, Postmortem, And Proof Lineage | Complete order-to-learning continuity |
| CATC-12 | Scheduler And Reliability Domain Separation | Market work cannot be starved by research or dashboard jobs |
| CATC-13 | Learning, Strategy Versioning, And Backtest Alignment | Outcomes refine strategies without silent authority changes |
| CATC-14 | Dashboard, Telegram, And Documentation Projections | Existing UX, current truth, no command authority |
| CATC-15 | Legacy Migration And Active-Runtime Retirement | Old paths archived and removed from scheduling |
| CATC-16 | Real-Market Verification And Five-Session Soak | Production journey proved under real timing and failures |
| CATC-17 | Certification, Deployment, And Empirical Paper Trial | One release gate and bounded observation programme |

## 10. CATC-0 - Quiescence, Evidence Freeze, And Worktree Protection

### Objective

Create a reproducible before-state and protect the current dirty worktree,
runtime evidence, dashboard UX, paper account, and broker state.

### Work

1. Pause scheduling without cancelling or mutating broker orders.
2. Poll and record the current Alpaca Paper account, orders, positions, and
   account fingerprint read-only.
3. Inventory every modified, untracked, generated, and deployed file.
4. Classify each dirty file as source change, test change, runtime mutation,
   public snapshot, secret, or unrelated user work.
5. Checksums the current decision, handoff, order, lifecycle, source, price,
   score, label, edge, and dashboard artifacts.
6. Export the active LaunchAgent and installed build identity.
7. Record current service receipts, circuits, repair requests, and scheduler
   budget behavior.
8. Record the currently deployed dashboard bundle and route-level screenshots.
9. Create a read-only incident archive; do not `git reset`, overwrite, or clean
   the user's worktree.

### Deliverables

- `data/runtime/qadam_catc_baseline.json`
- `data/runtime/qadam_catc_worktree_inventory.json`
- `data/runtime/qadam_catc_broker_read_only_snapshot.json`
- `data/runtime/qadam_catc_active_service_inventory.json`
- `docs/qadam-catc-implementation-log.md`

### Acceptance

- No order, cancellation, broker write, proof credit, or capital change occurs.
- Every dirty file is classified.
- The dashboard UX has a reproducible visual baseline.
- The programme can roll back to the pre-CATC installed build.

## 11. CATC-1 - Runtime Authority And Supersession Registry

### Objective

Identify every producer, consumer, scheduler job, checker, projection, and
broker-adjacent path, then assign one active owner or retire it.

### Work

1. Parse imports, artifact reads/writes, service definitions, and shell entry
   points into an executable dependency graph.
2. Identify all writers for hypotheses, envelopes, Akber results, shadows, risk
   decisions, Router decisions, handoffs, receipts, orders, lifecycle, and
   learning records.
3. Identify all V2, V3, V4, QSASE, QEG, PT, experimental, and compatibility
   readers.
4. Mark one canonical owner for each logical resource.
5. Mark every other path `research_only`, `read_only_compatibility`,
   `archive_only`, or `retired`.
6. Remove retired components from health dependencies before deleting code.
7. Reconcile every plan's declared status against its implementation log and
   active code.

### New Contracts

- `config/qadam_runtime_authority_registry.json`
- `config/qadam_supersession_registry.json`
- `scripts/check_qadam_runtime_authority.py`
- `scripts/check_qadam_supersession.py`

### Acceptance

- Exactly one active writer exists per control-plane resource.
- Exactly one broker-write route exists.
- Router V2 is absent from active scheduling and dashboard health.
- No plan can claim active authority without a registered code owner.

## 12. CATC-2 - Transactional Control-Plane Store

### Objective

Replace mutable JSON/JSONL control-plane truth with atomic, durable local
transactions while retaining JSON projections for compatibility.

### Work

1. Add `orchestrator/qadam_control_plane_store.py` with versioned migrations,
   WAL mode, foreign keys, busy timeout, integrity checks, and backups.
2. Create append-only tables for decision events, gate decisions, handoffs,
   receipts, submissions, broker events, lifecycle, service runs, repairs, and
   projection outbox events.
3. Add uniqueness constraints for decision generation, candidate identity,
   handoff identity, idempotency key, broker order ID, and lifecycle event ID.
4. Add current-state views derived from event history.
5. Implement atomic outbox publication to current JSON projections.
6. Make projection generation repeatable from an empty output directory.
7. Add backup, vacuum, retention, disk-ceiling, and corruption-recovery policy.

### Migration Rule

Existing accepted handoffs, receipts, orders, and lifecycle records are
imported with source checksums and `legacy_import` provenance. Missing lineage
is recorded honestly. It is not invented and does not receive proof credit.

### Acceptance

- An empty current generation cannot erase a prior handoff or receipt.
- Restarting during any transition produces no duplicate logical event.
- JSON projections can be deleted and rebuilt without losing authority.
- SQLite integrity and foreign-key checks pass.

## 13. CATC-3 - Immutable Research Generation Contract

### Objective

Ensure every decision reads one stable source, price, feature, score, label,
graph, and backtest generation.

### Work

1. Complete the existing immutable-generation and state-root abstractions.
2. Publish generation manifests only after checksum and schema validation.
3. Resolve one generation ID before a reader begins streaming.
4. Add reader leases and bounded retention.
5. Prevent dashboard, learning, backtest, and live decision jobs from reading
   partially published files.
6. Move mutable hot state outside Git-tracked and cloud-placeholder paths.
7. Preserve ignored bulk research history and disk safety limits.

### Acceptance

- Competing readers and writers never observe partial evidence.
- Sleep, restart, network loss, and retry preserve generation identity.
- A decision transaction cannot mix yesterday's score template with today's
  evidence tape.

## 14. CATC-4 - Canonical Schemas And Decision Identity

### Objective

Make one strict schema authoritative from observation through postmortem.

### Work

1. Retain the strict Pydantic `TradeabilityEnvelope` and generated JSON Schema.
2. Add strict models for `DecisionTransaction`, `ExecutionContext`,
   `GateDecision`, `PrimaryBlocker`, `PaperOpsHandoff`, `OrderEvent`, and
   `TradeOutcome`.
3. Reject undeclared fields and implicit defaults.
4. Generate schemas from executable models; compare hashes in CI.
5. Carry one content-addressed decision generation through every stage.
6. Require the evidence class and strategy version on every transaction.
7. Prohibit downstream reconstruction from ad hoc artifacts.

### Acceptance

- Every consumer reads the same typed transaction.
- A schema mismatch is classified as a code defect before Akber.
- Missing market evidence is distinct from missing internal contract fields.
- Golden fixtures cover all evidence profiles and blocker classes.

## 15. CATC-5 - Source Capability And Evidence-Usability Registry

### Objective

Make Qadam self-aware about what each source can actually contribute now,
historically, and at decision time.

### Work

1. Create one registry for all 41 sources with:
   - operating state;
   - live freshness;
   - historical coverage;
   - publication and availability timestamps;
   - trust and provenance;
   - feature producer;
   - label maturity;
   - strategy relevance;
   - quorum role;
   - confirmation role;
   - cost and subscription attribution;
   - forward-only or unavailable classification.
2. Distinguish catalogue sources, usable live triggers, usable confirmations,
   and empirically usable historical alpha inputs.
3. Add contribution and redundancy diagnostics.
4. Stop counting configured, sample, fixture, stale, or unavailable providers
   as usable evidence.
5. Define onboarding acceptance before a source can become a hard dependency.

### Acceptance

- The dashboard and gates use the same registry.
- Every hard evidence field maps to a real producer.
- The system never claims 41 independent tested signals.
- Subscription value can be assessed from actual evidence contribution.

## 16. CATC-6 - Trigger, Direction, Mapping, And Proxy Compiler

### Objective

Eliminate the 56 conversion and nine mapping defects observed in the discovery
funnel.

### Work

1. Build typed trigger compilers for event-catalyst, regime-state,
   market-dislocation, and validated-strategy profiles.
2. Resolve every accepted trigger to `long`, `short`, or explicit `abstain`.
3. Add deterministic event-to-market, strategy-to-instrument, and
   instrument-to-paper-proxy mappings.
4. Version mapping rules and economic mechanisms.
5. Validate symbol, venue, calendar, and corporate-action context.
6. Convert impossible or missing mappings into engineering repair requests,
   not Akber holds.
7. Add strategy-specific current trigger TTLs.
8. Require one independent current confirmation where the profile specifies it.

### Acceptance

- Zero eligible triggers are lost to unclassified direction.
- Zero accepted listed instruments fail because of stale route metadata.
- Every abstention states the economic reason.
- Conversion and mapping defects remain zero for five market sessions.

## 17. CATC-7 - Market-Hours Execution Context Service

### Objective

Provide the current measurements Akber and risk genuinely need at the moment of
decision.

### Work

1. Build one service for session state, bid, ask, midpoint, spread, price,
   volatility, liquidity proxy, volume/flow alternative, and timestamp.
2. Use provider fallbacks registered per instrument.
3. Run only when a qualified trigger exists or an open position needs
   monitoring.
4. Retry bounded transient failures during market hours with jitter.
5. Classify outcomes as:
   - `market_closed`;
   - `quote_ready`;
   - `provider_rate_limited`;
   - `provider_degraded`;
   - `instrument_not_tradable`;
   - `spread_adverse`;
   - `execution_context_expired`.
6. Treat market-hours provider failure as an infrastructure incident and open a
   provider-specific circuit, not the whole decision circuit.
7. Never synthesize or reuse a stale spread as current.

### Service Targets

- market-hours quote recovery p95 under 60 seconds;
- context age at Router under 120 seconds;
- bounded retry exhaustion produces one infrastructure blocker;
- outside-hours setup carries forward only until its trigger expiry.

### Acceptance

- A valid setup does not wait indefinitely for a spread measurement.
- Market closure is not reported as missing investment evidence.
- Quote-provider failure does not block unrelated instruments or dashboard
  refresh.

## 18. CATC-8 - Akber Evidence-Fit And Challenger Policy

### Objective

Make Akber rigorous but proportionate to evidence Qadam can genuinely collect.

### Work

1. Express all six stages as typed rules per evidence profile.
2. Mark every rule `hard`, `soft`, or `diagnostic`.
3. Preserve explicit adverse-evidence vetoes.
4. Convert missing soft evidence into declared size haircuts.
5. Generate plain-English explanations from rule results, not free-form text.
6. Run control and challenger decisions on the same event.
7. Freeze calibration windows and preregister promotion criteria.
8. Prevent models from changing thresholds or risk authority.

### Acceptance

- Every Akber decision identifies exactly which measured rule passed, held, or
  vetoed.
- No hard safety rule is weakened.
- Soft evidence absence cannot masquerade as adverse evidence.
- Challenger promotion is reversible and paper-only.

## 19. CATC-9 - Atomic Shadow, Risk, And Router Decision

### Objective

Create shadow, risk, and Router outputs from the same transaction before the
current evidence expires.

### Work

1. Create the decision-time shadow snapshot synchronously after Akber pass.
2. Estimate current net expectancy using the same price, spread, cost, and
   horizon context.
3. Produce a risk proposal and decision in the same transaction.
4. Assign exactly one Router state:
   - reject;
   - watchlist;
   - shadow-only;
   - hold;
   - repair-requested;
   - blocked-safety-boundary;
   - paper-review-candidate.
5. Persist one primary blocker and dependent consequences.
6. Recheck TTL, quote age, exposure, and idempotency immediately before handoff.

### Acceptance

- A passed Akber setup cannot fail because the service forgot to create its own
  shadow snapshot.
- Risk never reads a different generation.
- Every setup has exactly one final Router state.
- The Router cannot create an order.

## 20. CATC-10 - Canonical Handoff And PaperOps Exactly-Once Path

### Objective

Create one durable handoff and consume it exactly once through the existing
guarded wrapper.

### Work

1. Write accepted handoffs and receipts append-only in the control-plane store.
2. Make current JSONL files projections, not ledgers.
3. Replace snapshot overwrite behavior in
   `orchestrator/qadam_router_v3_paperops.py`.
4. Trigger PaperOps from an accepted-handoff outbox event, while preserving the
   canonical wrapper and broker-write owner.
5. Use the same candidate identity and idempotency key from trigger to broker.
6. Reconcile uncertain network outcomes read-only before any retry.
7. Prohibit automatic retry of an ambiguous broker write.
8. Keep multiple distinct qualified setups possible in one day.

### Acceptance

- One accepted handoff produces at most one broker order.
- Empty later cycles do not erase prior handoffs.
- A duplicate event is consumed once and recorded as duplicate thereafter.
- No other module imports or calls the broker write path.

## 21. CATC-11 - Lifecycle, Exit, Postmortem, And Proof Lineage

### Objective

Preserve complete lineage and make every submitted order reach an explained
terminal or open-position state.

### Work

1. Record submit, accepted, partial fill, fill, cancel, reject, expire, open,
   exit-planned, close, and postmortem events append-only.
2. Define stale accepted-order policy by order type and strategy.
3. Bind entry and exit actions to the original decision transaction.
4. Reconcile current Alpaca state against the local event store.
5. Back-reference historical trades where evidence exists; never fabricate
   missing IDs.
6. Separate broker fact, experimental outcome, and validated-edge credit.
7. Make learning consume closed outcomes only after reconciliation.

### Acceptance

- No paper order remains in an ambiguous lifecycle state.
- Every current Qadam-origin trade has verifiable handoff and order lineage.
- Proof eligibility fails honestly when lineage is incomplete.
- A later empty generation cannot invalidate a prior trade's origin.

## 22. CATC-12 - Scheduler And Reliability Domain Separation

### Objective

Ensure latency-sensitive trading work cannot be starved or broken by heavy
research, quantum, dashboard, or publication work.

### Runtime Domains

1. **Execution control plane**
   - trigger conversion;
   - execution context;
   - Akber;
   - shadow;
   - risk;
   - Router;
   - handoff;
   - PaperOps;
   - lifecycle.
2. **Research plane**
   - ingestion;
   - historical alignment;
   - backtests;
   - graph discovery;
   - model research;
   - quantum experiments.
3. **Projection plane**
   - dashboard;
   - Telegram candidates;
   - public status;
   - documentation snapshots.

### Work

1. Replace the global four-job cycle competition with domain queues and
   reserved execution capacity.
2. Use event-driven execution jobs and cadence-driven research jobs.
3. Give latency-sensitive jobs priority without preempting an active broker
   write.
4. Move heavy backtests and quantum work outside core market hours unless they
   are explicitly lightweight and noncontending.
5. Split `dashboard_refresh` into local projection and optional publication.
6. Remove Router V2, legacy certifications, and optional quantum checkers from
   dashboard health.
7. Use domain-specific circuit breakers and resource claims.
8. Self-heal only retryable reads and deterministic calculations.

### Acceptance

- `cycle_job_budget_exhausted` cannot skip an eligible execution transaction.
- Dashboard or quantum failure cannot open an execution circuit.
- Provider-specific failure does not stop unrelated strategies.
- Five market sessions contain zero latency-sensitive starvation events.

## 23. CATC-13 - Learning, Strategy Versioning, And Backtest Alignment

### Objective

Turn real outcomes into controlled strategy improvement without confusing
research breadth with proven edge.

### Work

1. Attribute every pass, hold, veto, order, no-order, missed opportunity, and
   closed trade to source, trigger, model, Akber rule, shadow, risk, Router,
   execution, and market regime.
2. Preserve negative results and avoid retesting identical failed hypotheses.
3. Compare strategy versions on frozen, point-in-time datasets.
4. Use walk-forward, holdout, costs, false-discovery, regime, and stability
   tests.
5. Align the five historically usable source signals first.
6. Admit additional sources to empirical testing only after feature,
   availability-time, label, and sample-size contracts pass.
7. Allow automatic bounded paper-version promotion within the frozen risk
   envelope after preregistered criteria pass.
8. Keep live-capital and risk-envelope expansion under separate future review.

### Acceptance

- Every strategy change cites the outcomes that motivated it.
- Rejected versions remain in experiment memory.
- Backtest and paper outcomes are never merged as the same evidence class.
- Strategy self-improvement cannot silently change constitutional limits.

## 24. CATC-14 - Dashboard, Telegram, And Documentation Projections

### Objective

Preserve the existing dashboard UX while making operating truth simpler and
more accurate.

### Dashboard Requirements

Do not change the route list, sidebar order, protected module structure,
10-stage lifecycle, or established visual design. Enrich existing surfaces
with projections from the canonical store:

- portfolio and trading history from reconciled broker events;
- catalogue source count versus usable live and historical evidence counts;
- ranked research score clearly distinguished from probability and validation;
- one setup state and one primary blocker;
- evidence-profile and size-haircut explanation;
- accepted handoff, PaperOps consumption, and order lineage;
- operational health separated from tradeability reachability;
- current projection freshness and source generation ID.

### Telegram Requirements

- remain review-only and command-disabled;
- report only material changes;
- avoid repeating static next questions;
- distinguish research finding, strategy proposal, eligible setup, paper order,
  and outcome;
- never imply that high activity or quantum hardware proves an edge.

### Acceptance

- Dashboard projections can be rebuilt from canonical truth.
- No dashboard checker can block execution.
- Public wording explains the real reason Qadam did or did not trade.
- Served production bundle matches the protected UX baseline.

## 25. CATC-15 - Legacy Migration And Active-Runtime Retirement

### Objective

Cut over safely and remove the recurring failure class rather than leaving old
paths active behind compatibility adapters.

### Procedure

1. Run old and new readers in shadow parity against the same immutable inputs.
2. Compare decisions without allowing the shadow path to create orders.
3. Import control-plane history with checksums.
4. Switch canonical reads to the transactional projections.
5. Remove legacy writers from service definitions.
6. Remove legacy checks from active health and certification.
7. Archive historical artifacts read-only.
8. Delete code only after no active import, write, scheduler, or rollback
   dependency remains.
9. Update every implementation plan status and authority reference.

### Mandatory Retirement Targets

- Router V2 active checker and projection path;
- legacy QSASE decision consumers;
- QEG direct Akber or Router consumers;
- competing Foundry downstream writers;
- snapshot JSONL accepted-handoff and receipt authority;
- optional quantum certification as dashboard health;
- old PaperOps handoff readers after the canonical adapter is proven.

### Acceptance

- Supersession checker reports zero retired active writers and consumers.
- Canonical route parity is documented.
- Rollback can restore the prior version without mixing stores.

## 26. CATC-16 - Real-Market Verification And Five-Session Soak

### Objective

Prove the installed service, real providers, real files, real market timing, and
paper route rather than only fixtures.

### Test Families

1. Unit and strict-schema tests.
2. Provider capability and availability-time tests.
3. Disk-backed golden journeys.
4. Broker-disabled market-hours reachability canary.
5. Real read-only Alpaca reconciliation.
6. One real paper micro-order only when a genuine setup passes all gates.
7. Restart, sleep, network-loss, rate-limit, partial-write, disk-pressure, and
   stale-quote fault injection.
8. Duplicate trigger and ambiguous broker-response tests.
9. Projection deletion and rebuild test.
10. Legacy-path negative tests.

### Five-Session Assertions

Across five distinct real US market sessions on one committed build:

- zero evidence conversion defects;
- zero mapping defects;
- zero generation-mixing defects;
- zero lineage-loss defects;
- zero duplicate broker writes;
- zero execution jobs skipped for scheduler budget;
- zero dashboard or quantum failures affecting execution health;
- every current qualified trigger reaches one terminal decision within one
  decision cycle;
- every accepted handoff is consumed exactly once;
- every no-trade decision has one truthful primary blocker.

The soak is not backfilled or simulated.

## 27. CATC-17 - Certification, Deployment, And Empirical Paper Trial

### Objective

Create one release decision and then measure whether the calibrated system
actually improves useful paper activity and outcomes.

### Create

- `scripts/check_qadam_canonical_autonomous_tradeability.py`
- `data/runtime/qadam_canonical_autonomous_tradeability_certification.json`
- `data/runtime/qadam_canonical_autonomous_tradeability_dashboard_summary.json`
- `docs/qadam-canonical-autonomous-tradeability-runbook.md`

### Certification Groups

1. safety and paper-only boundaries;
2. control-plane database integrity;
3. immutable research generation integrity;
4. one-writer and supersession audit;
5. source capability truth;
6. schema and transaction integrity;
7. market-hours execution context;
8. Akber hard/soft rule audit;
9. shadow, risk, and Router same-generation integrity;
10. exactly-once PaperOps handoff;
11. lifecycle and lineage completeness;
12. scheduler domain isolation;
13. dashboard and Telegram read-only quality;
14. five-session real-market soak;
15. dirty-worktree and deployed-build reproducibility.
16. installed operator ownership and protected dashboard release parity.

### Certification States

- `blocked`: a safety, authority, migration, or integrity requirement fails;
- `implementation_ready`: code and migration checks pass, soak incomplete;
- `observation_ready`: installed service and five-session soak pass;
- `paper_experiment_active`: observation-ready and the bounded trial is running;
- `degraded`: a domain is impaired, with unaffected domains identified;

### Deployment Procedure

1. Commit only reviewed source, tests, schemas, migrations, and documentation.
2. Never commit bulk research data, secrets, or mutable local databases.
3. Deploy dashboard projections without replacing the current UX.
4. Verify local, preview, and production bundle parity.
5. Install the version-bound operator service.
6. Re-run certification against the installed commit.
7. Keep rollback artifacts until the trial completes.

### Empirical Paper Trial

Run the control/challenger Akber comparison through real market time. Evaluate:

- eligible opportunities per session;
- trigger-to-decision latency;
- eligible-to-handoff conversion;
- handoff-to-order conversion;
- trades by evidence profile and strategy;
- net P&L after modeled costs;
- drawdown and concentration;
- false positives and missed opportunities;
- source and subscription contribution;
- learning proposals generated and accepted.

No trade quota is used. The objective is to eliminate artificial suppression,
not manufacture activity.

## 28. Required Code Change Map

### New Core Modules

- `orchestrator/qadam_control_plane_store.py`
- `orchestrator/qadam_control_plane_migrations.py`
- `orchestrator/qadam_decision_transaction.py`
- `orchestrator/qadam_execution_context.py`
- `orchestrator/qadam_gate_policy.py`
- `orchestrator/qadam_primary_blocker.py`
- `orchestrator/qadam_projection_outbox.py`
- `orchestrator/qadam_runtime_authority.py`
- `orchestrator/qadam_runtime_domains.py`
- `orchestrator/qadam_source_capability_registry.py`

### Primary Existing Modules To Change

- `orchestrator/qadam_operator_service.py`
- `orchestrator/qadam_tradeability_pipeline.py`
- `orchestrator/qadam_open_market_conversion.py`
- `orchestrator/qadam_forward_shadow.py`
- `orchestrator/qadam_portfolio_risk_engine.py`
- `orchestrator/qadam_router_v3_paperops.py`
- `orchestrator/qadam_paperops_runtime_owner.py`
- `orchestrator/qadam_tradeability_audits.py`
- `scripts/run_paperops_autonomous_pass.py`
- `scripts/run_qadam_operator_service.py`
- lifecycle, dashboard export, and learning readers that currently treat JSON
  snapshots as ledgers.

### Configuration

- runtime authority registry;
- supersession registry;
- source capability registry;
- evidence-profile policy;
- hard/soft gate policy;
- strategy and paper-proxy map;
- scheduler domain and priority policy;
- retention and disk policy.

## 29. Test Matrix

| Test | Required proof |
| --- | --- |
| Schema mutation | Unknown, missing, stale, and wrongly typed fields fail at the producer boundary |
| Transaction crash | Restart resumes without duplicate or lost transition |
| Empty generation | Historical handoffs and receipts remain intact |
| Provider outage | Only affected provider/instruments degrade |
| Market closed | One honest market-session blocker, no cascading fake blockers |
| Market-hours quote failure | Bounded retry then provider incident |
| Soft evidence missing | Declared haircut or shadow-only state, never silent default |
| Hard evidence missing | Fail closed before handoff |
| Duplicate trigger | Same identity and idempotency key, one consumption |
| Ambiguous broker response | Reconcile read-only; no blind retry |
| Scheduler pressure | Execution queue meets latency target |
| Dashboard failure | Execution domain remains healthy |
| Quantum dependency failure | Research domain degrades only |
| Projection loss | Rebuild from canonical store |
| Legacy invocation | Negative test rejects retired writer or consumer |
| Five-session soak | Real installed service passes all continuous assertions |

## 30. Operational Metrics And Service Objectives

### 30.1 Engineering Metrics

- eligible setup loss due to code or contract defect: 0;
- conversion defect rate: 0%;
- mapping defect rate: 0%;
- same-generation integrity: 100%;
- accepted-handoff retention: 100%;
- duplicate broker writes: 0;
- unexplained lifecycle states: 0;
- latency-sensitive scheduler starvation: 0;
- projection rebuild success: 100%.

### 30.2 Decision Metrics

- trigger-to-envelope p95: under 60 seconds;
- envelope-to-Router p95: under 180 seconds when providers are healthy;
- accepted-handoff-to-PaperOps invocation p95: under 120 seconds;
- eligible setup conversion: 100% to either order or genuine hard blocker;
- primary blocker classification: 100%;
- soft-evidence haircut attribution: 100%.

### 30.3 Trading And Research Metrics

- number of genuine triggers;
- setups reaching Akber;
- control versus challenger decisions;
- paper orders and distinct candidate identities;
- net outcomes after costs;
- drawdown and concentration;
- good opportunities filtered;
- bad opportunities admitted;
- source contribution and subscription cost per useful decision;
- strategy-version improvement out of sample.

Trade count alone is not a success metric. A higher trade count caused by lower
data integrity would be failure.

## 31. Rollback Strategy

Every phase must be reversible until CATC-15 retires active legacy paths.

1. Version every schema and database migration.
2. Backup the control-plane database before migration.
3. Preserve immutable import manifests and source checksums.
4. Keep old readers in read-only shadow mode during parity.
5. Never allow old and new writers simultaneously.
6. Bind the installed service to one commit and one database schema version.
7. Roll back code and state together.
8. Reconcile Alpaca read-only after rollback before allowing PaperOps.
9. Keep dashboard projection rollback independent of broker state.

If parity fails, Qadam returns to paper watch-only while research continues. It
does not bypass the failed phase.

## 32. Dynamic Plan Governance

Maintain:

- `data/runtime/qadam_catc_implementation_status.json`;
- `docs/qadam-catc-implementation-log.md`;
- phase-specific certification artifacts;
- a traceability matrix from every RCA failure to code, tests, migration, and
  production proof.

Rules:

- only one phase may be `in_progress`;
- a phase is complete only after its acceptance checker passes;
- implementation status must name the installed commit;
- discovered defects update the current phase before later phases continue;
- scope changes must state whether they replace or extend an existing owner;
- no later phase may create a parallel writer;
- plan and implementation-log status must agree.

## 33. Recommended Execution Waves

### Wave A - Establish Authority

Implement CATC-0 through CATC-4:

- freeze evidence;
- inventory and supersede paths;
- create the control-plane store;
- stabilize immutable research generations;
- establish strict canonical schemas.

Do not change trading thresholds in this wave.

### Wave B - Make Evidence Usable

Implement CATC-5 through CATC-7:

- truthful source capability;
- complete trigger and proxy conversion;
- real market-hours execution context.

This wave removes the largest observed engineering loss class.

### Wave C - Make Decisions Proportionate And Atomic

Implement CATC-8 through CATC-10:

- hard/soft Akber rules;
- synchronous shadow and risk;
- one Router state;
- exactly-once handoff and PaperOps invocation.

### Wave D - Preserve Outcomes And Runtime Health

Implement CATC-11 through CATC-14:

- lifecycle and proof lineage;
- scheduler domains;
- strategy learning;
- dashboard, Telegram, and documentation projections.

### Wave E - Remove The Old System And Prove The New One

Implement CATC-15 through CATC-17:

- retire active legacy paths;
- run real-market verification;
- complete the five-session soak;
- deploy and start the empirical paper trial.

## 34. Final Definition Of Done

The programme is complete only when all of the following are true:

1. One canonical decision transaction owns trigger-to-outcome state.
2. One active writer exists for every control-plane resource.
3. One guarded Alpaca Paper broker-write route exists.
4. Retired V2, QSASE, QEG, and legacy paths have no active decision authority.
5. Accepted handoffs, receipts, and order lineage are append-only and durable.
6. Empty generations cannot erase historical facts.
7. Every hard gate maps to evidence Qadam can actually collect.
8. Every soft gate has a declared haircut, shadow-only rule, or diagnostic role.
9. Missing internal contract fields are defects, not market holds.
10. Missing market-hours execution context invokes bounded provider recovery.
11. Akber, shadow, risk, and Router use one generation.
12. Every setup has exactly one final state and one primary blocker.
13. Execution jobs cannot be starved by research or dashboard work.
14. Dashboard and quantum failures cannot block the execution domain.
15. Every broker order has complete candidate, handoff, and lifecycle lineage.
16. The existing dashboard UX and route structure remain intact.
17. Local, preview, production, and installed-build checks pass.
18. Five consecutive real market sessions pass with zero conversion, mapping,
    generation, lineage, duplicate-write, or scheduler-starvation defects.
19. A genuine eligible setup produces exactly one small guarded paper order
    within the service objective, or one genuine hard blocker.
20. Live capital remains disabled.

## 35. Expected Operator Outcome

After this programme, leaving Qadam running will have a defensible operational
meaning:

- current evidence will be converted consistently;
- genuine setups will not disappear between incompatible modules;
- market-hours measurements will be obtained or fail with a precise provider
  incident;
- Akber will remain protective without treating every missing optional signal
  as a veto;
- eligible experimental setups will reach small guarded paper orders promptly;
- every order and outcome will remain attributable;
- no-trade states will be real investment conclusions rather than hidden
  engineering failures;
- Qadam's learning loop will compare strategy and filter versions using durable
  evidence;
- dashboard and Telegram views will explain the same canonical truth.

That is the strongest software guarantee Qadam should make. The system can
guarantee that eligible evidence is processed faithfully and safely. Markets,
profitability, edge discovery, and daily opportunity frequency remain empirical
outcomes that the paper trial must establish.
