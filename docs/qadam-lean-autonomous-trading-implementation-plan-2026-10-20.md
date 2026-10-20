# Qadam Lean Autonomous Trading Implementation Plan

Date: 20 October 2026, Asia/Dubai.

Status: Code implemented and production dashboard released. Final runtime verification is recorded in the release record. Real-session reliability, whole-operator performance and economic acceptance remain prospective, not completed by deployment.

Purpose: Simplify the existing codebase, restore dependable execution, convert
obtainable evidence into small autonomous paper trades, and measure whether the
resulting strategies deserve continued or increased allocation.

## 1. Outcome And Definition Of Success

Qadam should run a short, understandable operating loop:

`collect -> recognise -> form a trade -> decide and size -> execute and protect -> attribute -> learn`

Every live component must either improve that loop, protect the account, or
explain its state. Historical research, optional models and presentation work
must have bounded resources and must not delay an otherwise complete trade.

The initial activity objective is 5-10 distinct new paper entries per five US
market sessions, with capacity for 10-15 when independent opportunities and
strategy holding periods support it. These are design and evaluation targets,
not minimum-order instructions or promises of opportunity. Measure entries,
exits, fills and independent economic events separately. A buy followed by its
sell is one completed experiment, not two independent trading ideas.

Successful implementation must demonstrate all of the following:

- Complete, admissible setups reach the execution owner promptly and reliably.
- Missing optional context usually reduces priority or size; it has one defined
  effect rather than accumulating repeated penalties across modules.
- Open positions receive timely exit management through the same execution owner.
- Every new order and fill has exact strategy, decision, account and epoch lineage.
- The account, dashboard, learning records and Telegram agree about what happened.
- Strategies can continue collecting small paper outcomes while validation matures.
- Net results, benchmark-relative results and operating expenses are measurable.
- The runtime is smaller and easier to maintain, with fewer active writers,
  repeated scans, subprocess launches and unnecessary artifact generations.

Engineering acceptance does not establish profitability. Economic acceptance
requires independent forward evidence after realistic costs. Paper account gains
remain simulated and do not pay subscriptions.

## 2. Starting Evidence

Baseline checkout: `5d85ce1b19d148ebe1d0060d9f003b3248beee7b` on
`codex/weekend-engine-preservation-20260719`.

The following observations were inspected on 20 October before implementation.
They must be captured again at Phase 0, especially after a laptop restart.
The working tree also contains unrelated generated artifacts and documentation
changes; preserve them and keep them out of implementation commits.

| Observation | Evidence | Required response |
| --- | --- | --- |
| Operator running, 19/21 services fresh, two open circuits, not operationally ready | `data/runtime/qadam_operator_service_status.json`, 13:20 UTC | Repair execution and publication; do not infer health from process presence |
| Entries and due exits reported frozen following `post_paperops_submission_reconciliation_owner_lease_expired` | `data/runtime/qadam_reliability_critic_status.json`, 20 October | Reproduce the lease/reconciliation failure and verify a cause-specific recovery |
| 23 catalogue entries collected; four sources labelled fresh in the inspected coverage snapshot | `data/runtime/qadam_source_collection_coverage.json`, 12:57 UTC | Design strategies around actual usable evidence and provider cadence |
| Five core families; highest semiconductor score approximately 0.640; zero currently eligible core hypotheses | `data/runtime/qadam_core_strategy_status.json`, 12:54 UTC | Resolve the actual direction, trigger and admission stops instead of treating rank as expectancy |
| 360 backtest results, no validated historical edge | `data/runtime/qadam_edge_registry_summary.json` | Preserve negative findings and use bounded discovery where justified |
| 33 strategy versions in forward evaluation, zero forward-validated | `data/runtime/qadam_forward_strategy_tournament.json` | Consolidate active experiments and preserve stable versions |
| 51 Qadam-origin records with incomplete lineage, zero complete attributable outcomes | `data/runtime/qadam_paper_performance_summary.json` | Repair attribution without inventing missing evidence |
| Latest inspected broker mirror: USD 100,268.97, one open position, 36 reported closed trades | `data/runtime/alpaca_paper_mirror.json`, observed 19 October 19:44 UTC | Keep broker accounting separate from strategy attribution and refresh at implementation |
| Tested quantum comparison reports no incremental value; that particular comparison used a local simulator | `data/runtime/qadam_quantum_usefulness_summary.json` | Keep optional research off the execution dependency path; report backend truth |
| Existing canonical packages and import-only compatibility adapters already exist | `config/qadam_refactor_boundaries.json` | Continue the existing migration instead of introducing a replacement architecture |

Two implementation details need an explicit audit:

1. `qadam_experimental_paper_policy.json` contains a bounded unknown-expectancy
   allowance, while its micro-admission section and validator still require
   positive current expectancy. Trace the effective producer-to-executor path
   before changing any rule; an exception in portfolio risk alone cannot prove
   the foundry and compiler can produce such a trade.
2. `build_current_expectancy_v2` derives an estimate partly from volatility,
   research rank and a fixed capture-rate formula. That output must retain its
   heuristic provenance. A positive calculated number is not a calibrated
   prediction or evidence that a strategy has positive expected profit.

The forward evaluator also includes a multiplicity-adjusted sign test of positive
trade and benchmark-relative returns. That tests win consistency rather than
expected profit and may reject a positive-expectancy strategy with infrequent
large wins. Review this separately from execution admission in P7. Neither a
high hit rate nor a low hit rate alone establishes an edge.

## 3. Scope And Existing Authority

This is a consolidation of the current implementation and the compatible
requirements in the September reliability/performance plan. Earlier plans remain
design history. This document supplies the next implementation sequence; their
old completion labels are not release evidence.

Retain:

- The existing SQLite control plane, account identity, paper epoch and data lakes.
- One leased PaperOps owner for all entries, exits, cancellations and replacements.
- Discovery and validated lanes, with automatic decisions inside the existing
  mandate rather than a new manual approval for every trade.
- The existing portfolio risk envelope and USD 5,000 absolute position ceiling.
- The current unknown-expectancy discovery bounds: at most USD 250 notional and
  USD 5 planned loss at invalidation. Stops do not guarantee that maximum loss.
- Three concurrent discovery slots and one position per correlated cluster until
  a separately versioned policy change is justified and authorised.
- Existing dashboard navigation and visual design. Add truthful information in
  the current views rather than designing another dashboard.
- Existing Telegram sender ownership and research/reporting boundaries.

This plan does not enable real capital, a new broker, leveraged products,
unsupported options execution, paid subscriptions or arbitrary self-editing code.
It does not restore the retired Akber filter as a separate authority. Any legacy
Akber-named compatibility fields must map to the current canonical decision and
must not introduce another veto or approval stage.

## 4. Architecture To Converge On

| Responsibility | Existing implementation to retain and simplify |
| --- | --- |
| Pure record and policy contracts | `orchestrator/contracts/` |
| Transactions, migrations, durable records and bounded history | `orchestrator/storage/` |
| Source collection, pattern formation and frozen strategy definitions | `orchestrator/research/` |
| One admission, sizing and decision path | `orchestrator/decisions/` and the existing portfolio-risk engine |
| Order intents, owner lease, broker effects, reconciliation and exits | `orchestrator/execution/`, current PaperOps wrapper and canonical exit engine |
| Exact attribution, forward evaluation and bounded promotion | `orchestrator/learning/` |
| Dispatch, resource budgets, watchdog and deterministic recovery | `orchestrator/runtime/` |
| Dashboard and communications projections | `orchestrator/presentation/` and existing senders |

Keep raw/history datasets in their existing immutable storage. Store canonical
operational records and references in SQLite. JSON is a versioned read projection
or transport envelope, never an alternative source of execution authority.

The initial refactor targets are the 4,672-line runtime operator, 2,392-line
execution ledger, 2,060-line foundry and 2,011-line PaperOps wrapper inspected in
this checkout. Split them by cohesive responsibility and measurable complexity,
not by an arbitrary file-length rule. Moving a function without removing a
duplicate decision or unnecessary dependency does not complete a phase.

### 4.1 One Decision Contract

Extend the existing contract rather than creating a parallel schema. Each proposed
trade contains, as applicable:

- Account, epoch, strategy family and frozen strategy version.
- Economic event and signal identities, instrument mapping and direction.
- Source provenance, event time, first availability time and decision time.
- Entry conditions, expiry, invalidation, exit policy and intended holding horizon.
- Current executable quote, spread, liquidity observation and volatility context.
- Return class: `unestimated_discovery`, `estimated_unvalidated` or `validated`.
- Estimate provenance and uncertainty; missing estimates remain missing.
- Planned notional, planned stop risk, cluster exposure and applied size modifiers.
- Policy and evidence digests, decision identity, risk allocation and handoff state.

The return classes describe evidence quality; they do not create a third trading
lane. A single pipeline applies the relevant rules and records one primary
disposition plus any supporting reasons.

### 4.2 Admission Rules

| Evidence or condition | Required behaviour |
| --- | --- |
| Missing executable instrument or direction | Hold with a specific producer repair or abstention reason |
| Stale/missing broker truth, ownership conflict or unresolved write | Freeze affected execution and reconcile |
| Unusable quote/spread/liquidity observation | Wait for an obtainable measurement; expire if not obtained in time |
| Missing exit/invalidation or portfolio capacity | Do not submit; fix the contract or queue until capacity exists |
| No validated edge, insufficient historical samples or unknown expectancy | Permit the bounded discovery class if its complete entry contract passes |
| Optional transcript, alternative source, order-flow or model result absent | Apply the registered confidence/size effect once, or no effect if the strategy does not require it |
| Missing strategy-defining event or feature | Hold that strategy; do not substitute an unrelated observation |
| Known negative economics for the unchanged setup | Reject; do not relabel it unknown to qualify for discovery |
| Provider available but no new event | No event-triggered trade; a separate registered price-based strategy can still evaluate |
| Optional LLM or quantum worker fails | Continue independent strategies whose required inputs remain complete |

Breakout and continuation strategies may require agreement with price direction.
A reversion strategy has different confirmation rules. Do not impose one generic
momentum confirmation on every strategy or count two transformations of the same
price as independent evidence. A favourable reward-to-risk ratio alone is not
positive expectancy.

### 4.3 Capacity And Weekly Activity

Estimate sustained entry capacity before assigning activity targets:

`entries per five sessions ~= usable independent slots * 5 / average holding sessions`

This is a planning estimate with full utilisation, not a signal forecast. With
three usable slots and five-session holds, sustained capacity is approximately
three entries per week. At one-session holds it is approximately fifteen.
Fewer independent clusters, missing signals and execution friction reduce it.

For 5-10 weekly entries, test strategies with justified one-to-three-session
horizons alongside the existing longer-horizon research. A shorter horizon is a
new economic definition with its own results. Never shorten an open position's
hold just to release capacity or retrospectively relabel five-day outcomes.

Ten-to-fifteen weekly entries remain conditional on the capacity calculation,
provider cadence, actual independent triggers and transaction costs. If the
current mandate cannot support that frequency, report the binding constraint.
Do not make correlated copies or reopen an unchanged signal to inflate activity.

## 5. Implementation Sequence

Keep a single progress record in this document. Each
phase closes with its commit, tests, runtime evidence, remaining limitations and
rollback instructions. Do not create another family of phase-certification JSON
files or update completion merely because functions and filenames exist.

| Phase | Deliverable | Depends on | State |
| --- | --- | --- | --- |
| P0 | Baseline, ownership map and incident replay fixtures | None | Captured and replayed |
| P1 | Execution-owner recovery and dependable position protection | P0 | Implemented; initial repair live |
| P2 | Exact attribution and reconciled accounting | P0; live verification uses P1 | Implemented; historical gaps retained |
| P3 | Lean runtime and removal of redundant authority paths | P1, P2 | Implemented; whole-process performance acceptance pending soak |
| P4 | Small dependable evidence set and complete feature production | P0; integration uses P3 | Implemented; provider availability acceptance pending soak |
| P5 | Stable executable playbooks and realistic experiment capacity | P2, P4 | Implemented; prospective challengers shadow-only |
| P6 | Evidence-fit admission and portfolio allocation | P1, P2, P3, P5 | Implemented; integration regression tested |
| P7 | Outcome learning, benchmarks and measured strategy selection | P2, P5, P6 | Implemented prospectively; economic evidence not established |
| P8 | Truthful health, communications and operating economics | P1-P7 | Implemented; hosted publication verification in release record |
| P9 | Legacy retirement, deployment and unattended acceptance | P0-P8 | Released and regression tested; five-session sign-off and twenty-session value review remain pending real observations |

P1 is a small incident-repair release and must not wait for the full refactor.
P2 and P4 development may overlap after their input contracts are fixed.
Changed trading behaviour activates only after P6 and exit acceptance pass.
Release subsequent phases in small slices instead of keeping the operator paused
for a long all-at-once migration.

### P0. Capture The Actual System And Freeze The Migration Boundary

**Primary locations:** `orchestrator/runtime/`, `orchestrator/storage/control_plane.py`,
`config/qadam_refactor_boundaries.json`, current launchd and policy configuration.

Work:

1. Capture the current build, actual running process, launchd arguments, resolved
   state directory, database version, account/epoch, leases, policy versions,
   disk headroom, source coverage and queue ages. Timestamp every observation.
2. Take a consistent SQLite backup using the supported backup API; restore and
   validate it in an isolated directory. Preserve WAL semantics and broker IDs.
3. Inventory scheduled and manually callable entry/exit writers, policy builders,
   cohort builders, health producers and presentation writers. Trace imports and
   actual command dispatch, including compatibility adapters.
4. Map each active output to exactly one owner using the existing registry. Mark
   canonical, compatibility-only, offline research and retired code explicitly.
5. Capture sanitised incident fixtures for lease expiry, accepted-order timeout,
   missing fill history, source authentication failure and stale publication.
6. Profile one ordinary market-session cycle and one no-change cycle: wall time,
   CPU, peak memory, file writes, database lock time, subprocesses and scans.

Acceptance:

- Every broker write route has an identified owner and reachable call path.
- Backup restoration, current account binding and isolated replay work.
- The current execution freeze reproduces as a failing regression case.
- The dependency/ownership inventory distinguishes code existence from live use.
- Baseline and inspection scripts do not submit trades or send Telegram messages.

### P1. Recover The Execution Owner And Protect Positions

**Primary locations:** `orchestrator/execution/ledger.py`,
`orchestrator/paperops_autonomous_pass.py`, `orchestrator/qadam_canonical_exit_engine.py`,
`orchestrator/qadam_canonical_paper_control.py`, `orchestrator/contracts/execution_recovery.py`,
`orchestrator/runtime/recovery.py` and `orchestrator/qadam_paperops_runtime_owner.py`.

Work:

1. Trace why the lease expired across reconciliation and why the existing recovery
   handler did not clear the verified incident. Distinguish owner, database,
   network, scheduling and code failures from their downstream symptoms.
2. Make owner renewal independent of long research, model calls, dashboard builds
   and subprocess sequences. Renew before bounded broker operations and while
   legitimate long operations are in progress, with a documented lease budget.
3. Persist a lease generation and verify it before every write. A stale process
   cannot regain authority through environment variables or an old receipt.
4. Recover by acquiring valid ownership, querying broker truth and resolving all
   pending intents by stable client/order identity. An ambiguous submit is a
   reconciliation task; it must never become a blind second submission.
5. Clear only the incident generation that recovery proved resolved. Preserve
   independent manual, risk and reconciliation holds. If the prior owner may
   still have a request in flight, block takeover writes until that ambiguity is
   resolved. The broker does not provide an atomic transaction with SQLite.
6. Give due exits and protective-order reconciliation priority within the same
   owner. A research admission failure must not prevent a safe risk-reducing exit.
   Broker or ownership ambiguity still requires reconciliation before a write.
7. Evaluate exits independently of new-signal discovery. Require an explicit
   reduce-only quantity or equivalent broker-position check so an exit cannot
   reverse a position or close another strategy's allocation accidentally.
8. Verify protective broker orders where the existing instrument/route supports
   them. Unsupported protection must remain a visible operational dependency,
   with an honest gap-risk statement and no fictitious guaranteed stop.
9. Give recovery a short supervised cadence and bounded retries. The three-hour
   health message is reporting; it cannot be the deadline for repairing an
   execution freeze or overdue exit.

Acceptance:

- The actual lease-expiry fixture recovers with broker and ledger agreement.
- Restart, process death and timeout at each broker boundary produce at most one
  resolved economic order effect for the same intent.
- Two concurrent owners cannot submit; PID reuse or an old lease cannot authorise.
- A blocked research worker does not delay exit evaluation.
- Every open position is protected or explicitly classified for urgent repair.
- Safe transient recovery completes within five minutes under working broker and
  database conditions. Persistent failures escalate without a retry storm.

### P2. Repair Attribution Before Claiming Learning Or Profit

**Primary locations:** `orchestrator/learning/attribution.py`,
`orchestrator/execution/ledger.py`, `orchestrator/storage/control_plane.py`,
`orchestrator/contracts/broker_history.py`, `orchestrator/storage/benchmarks.py` and migrations.

Work:

1. Recover paginated broker orders and execution activities where access permits.
   Join exact broker/client order IDs, fill IDs, entry lots, exit allocations,
   decision IDs, strategy versions and the original account/epoch.
2. Diagnose the 51 incomplete Qadam-origin records and the mismatch with broker
   closed-trade counts. Classify each missing field and its recoverability.
   Existing historical records must not be assigned to the latest order in the
   same symbol or to a strategy inferred from today's narrative.
3. Support long and short positions, partial fills/exits, replacements, cancelled
   remainders and multiple internal allocations sharing one broker symbol.
   Reconcile signed quantities and cash; deduplicate fills by broker identity.
4. Append evidence corrections and recompute projections deterministically.
   Preserve original records and audit revisions instead of hiding conflicts.
5. Separate broker account P&L, gross reconstructed trade P&L, modelled net return,
   actual attributable net P&L and subscription-adjusted research economics.
   Missing cost or entry data stays unknown rather than becoming zero.
6. Capture matched benchmark observations at decision/entry and exit, with the
   same horizon, capital convention and availability rules. Missing benchmarks
   exclude benchmark claims without deleting the trade or blocking an otherwise
   permitted small discovery experiment.
7. Require complete identifiers for all new entries before the broker call.
   Unrecoverable old trades stay in an explicit legacy/unresolved cohort.

Acceptance:

- Every recoverable historical record has a documented reconciliation result;
  irrecoverable records have exact reasons and never count toward promotion.
- All newly created orders and fills resolve to their original decision/version.
- Fixture replay produces identical positions, outcomes and accounting totals.
- Partial exits and shorts reconcile against broker fixtures within documented
  rounding tolerances, with all residual differences disclosed.
- The performance report either gives attributable results with coverage or
  clearly identifies what remains unmeasurable.

### P3. Make The Runtime Smaller And Remove Duplicate Work

**Primary locations:** `orchestrator/runtime/operator.py`, `orchestrator/runtime/services.py`,
`orchestrator/runtime/scheduling.py`, `orchestrator/research/foundry.py`,
`orchestrator/decisions/pipeline.py`, `orchestrator/execution/ledger.py`,
`orchestrator/paperops_autonomous_pass.py` and `config/qadam_refactor_boundaries.json`.

Work:

1. Extract cohesive lease/reconciliation, order-state, exit and accounting code
   behind existing public interfaces. Keep pure admission/risk calculations free
   of filesystem refreshes, network calls and model invocations.
2. Turn the PaperOps wrapper into a short composition of already-owned services.
   Do not retain a second private implementation in the old wrapper or shim.
3. Replace repeated checker/build subprocess chains in the hot path with bounded
   calls to canonical implementations and shared, immutable input generations.
   Keep heavy certification and historical replay in CI or scheduled research.
4. Use dependency digests and durable cursors to process changed observations.
   Separate source/decision progress from a five-minute heartbeat or JSON rewrite.
5. Reserve scheduling and resource capacity for broker reconciliation, quotes,
   due exits and accepted handoffs. Historical research, broad matrices and UI
   generation cannot exhaust that budget or hold their locks.
6. Consolidate operation into seven scheduling domains: broker/position care,
   market data, source collection, research, decisions, learning and presentation.
   These are responsibility groups, not seven new daemons. Preserve existing
   service IDs until their health, recovery and ownership consumers migrate.
7. Ensure a new qualifying event wakes its downstream decision work without
   waiting for a full universe rebuild. Quote or broker changes still require
   their own immediate freshness checks before submission.
8. Remove redundant active policy builders and gate interpretations only after
   old/new decision replay explains every changed outcome. Maintain import-only
   compatibility adapters temporarily, with named consumers and removal criteria.
9. Prune abandoned scripts, dead configuration and unused dependencies only after
   static references, dynamic use, tests and rollback needs have been checked.
   Respect the separate Git boundary of `landing-page-repo`.
10. Bound logs, history scans, materialised projections, caches and backups using
    existing retention code. Preserve economic records and research evidence.

Acceptance:

- One canonical implementation remains for each decision, policy and write owner.
- No live trading cycle invokes a retired writer or full historical certification.
- Tests enforce contract import boundaries and import-only adapter behaviour.
- No-change cycles create no new decision or experiment identity.
- Measured no-change CPU and write volume fall at least 30% from P0 on equivalent
  workloads; explain any exception before acceptance, without weakening evidence.
- Normal complete setups meet the two-minute decision-to-submission service
  objective below; exit work meets its separate priority objective.

### P4. Build Strategies On Evidence Qadam Can Obtain Reliably

**Primary locations:** `orchestrator/research/source_collection.py`,
`orchestrator/research/source_payloads.py`, existing provider adapters,
`orchestrator/qadam_source_capability_registry.py`, `orchestrator/qadam_execution_context.py`
and the existing source/price manifests.

Work:

1. Give each strategy input an explicit provider, entitlement, feature producer,
   first-available timestamp, cadence, freshness rule and fallback behaviour.
   An internal alias or repeated RSS copy is not another independent provider.
2. Prioritise usable quotes, spread/liquidity, price history, volume and volatility
   for the tradable instruments. Daily bars cannot substitute for a current
   executable quote; a recent fetch does not make delayed data current.
3. Repair selected providers with available access. Distinguish credentials,
   entitlement, rate limits, endpoint defects, empty valid responses and transport
   failures. Avoid retrying a known 402/403 or absent local bridge every minute.
4. Keep disabled/unsupported sources visible as research coverage gaps. New paid
   access is an explicit budget decision, not an automatic dependency repair.
5. Apply publication-aware freshness to slow macro data and event-aware freshness
   to news/shipping evidence. Polling a static article again does not create a
   new trigger. Preserve provider corrections as new revisions.
6. Produce complete typed event, regime and dislocation features. A source health
   flag, geographic mention or rising research score cannot substitute for a
   signed, instrument-relevant economic mechanism.
7. Add a feature-availability view to existing source/strategy projections.
   Identify fields missing because collection failed separately from features
   the current provider contract cannot supply.
8. Remove optional providers from the required-input set of strategies that do
   not use them. A failed unrelated provider cannot freeze all other strategies.

Acceptance:

- Every mandatory feature of each activated playbook has a verified producer.
- Live selected-provider samples preserve trustworthy availability timestamps.
- Delayed, empty, stale, aliased and corrected observations pass the right tests.
- Decision-critical market data is available during at least 99% of sampled
  relevant session minutes in the release soak, or the playbook stays inactive.
- Source coverage reports collection, content freshness and trading relevance
  separately; it never describes the catalogue as 41 working independent APIs.

### P5. Define A Small Set Of Stable, Executable Playbooks

**Primary locations:** `orchestrator/research/foundry.py`,
`orchestrator/research/core_strategies.py`, `orchestrator/qadam_strategy_definition.py`,
`orchestrator/qadam_trigger_factory.py` and the existing event/regime/direction
producers.

Work:

1. Keep all five core families visible, but initially activate at most two new or
   revised paper playbooks with dependable data, liquid supported instruments,
   a clear mechanism and complete exits. Preserve and manage existing positions.
2. Evaluate a simple price/volatility baseline and a version with event evidence
   on matched instruments, dates, costs and risk. The baseline is an explicit
   comparator; it receives trading authority only if separately admitted.
3. Start selection with the existing semiconductor and energy research because
   they have stronger observed ranks and some available evidence, then verify
   current capability. Those facts alone do not choose a side or justify a trade.
   If either lacks a usable trigger, select another complete playbook or report
   that none qualifies; do not manufacture an event to fill the shortlist.
4. Express each playbook as code/data with a bounded input contract, direction,
   entry condition, horizon, stop/invalidation, profit/exit policy, expiry,
   cluster, liquidity limits and evidence class. Models may explain or propose;
   deterministic software resolves and bounds the executable action.
5. Evaluate one-to-three-session challenger horizons only where the mechanism
   supports them. Retain longer-horizon versions as distinct research cohorts.
   Do not add intraday strategies if the data and execution cadence cannot test
   them honestly. Horizon selection is frozen before forward observation.
6. Define the signal identity from new economic information, not score refresh,
   model wording, observation ID or wall-clock tick. Re-entry requires a
   registered reset/new-trigger rule after accounting for existing exposure.
7. Separate strategy version from signal identity and input generation. Fresh
   data does not reset the strategy cohort. Rule changes create new versions.
8. Record existing adverse backtests. Unknown evidence can support bounded
   discovery, but unchanged strategies with demonstrated negative economics
   require a substantive new thesis before re-entry into that lane.
9. Admit a third independent playbook only after the same contracts pass and
   the existing portfolio/cluster budget supports it. Do not force the five core
   families to have equal allocation or rewrite their meaning to fit a signal.
10. Keep new pattern research open across the retained source universe. A new
    relationship can propose a typed strategy using supported actions and enter
    the same bounded discovery process. It need not be forced into a core family
    or earn a validated-edge label first. Unsupported actions or new risk mandates
    remain explicit proposals; arbitrary generated code cannot become an executor.

Acceptance:

- Every activated playbook can generate a complete trade from real obtainable
  evidence in an isolated replay, including an explicit hold and expiry case.
- Repeated polling of one event produces one economic experiment opportunity.
- Reversion and continuation examples receive their own valid confirmations.
- Entry, exit and learning use the same frozen definition and horizon semantics.
- Capacity calculations show the supported weekly range and its binding limits.

### P6. Unify Evidence-Fit Admission And Portfolio Allocation

**Primary locations:** `orchestrator/decisions/pipeline.py`,
`orchestrator/qadam_tradeability_envelope.py`, `orchestrator/contracts/decision.py`,
`orchestrator/qadam_discovery_micro_conversion.py`, `orchestrator/qadam_experimental_paper_policy.py`,
`orchestrator/qadam_portfolio_risk_engine.py` and their effective policy projections.

Work:

1. Trace one complete example through draft selection, foundry, envelope,
   canonical decision, risk, Router, durable handoff and actual PaperOps input.
   Fix missing producer fields and incompatible names/units at their source.
2. Make one executable policy define mandatory fields, optional evidence effects,
   lane requirements and size bounds. Generate compatible projections from it.
   Keep final broker/ownership and portfolio-state rechecks at execution time.
3. Carry the bounded unknown-expectancy return class through every stage. Remove
   circular requirements for a positive estimate or completed validation where
   that class is already authorised. Preserve its USD 250 / USD 5 planned-risk
   bounds, invalidation, current market data and portfolio limits.
4. Replace rank-derived profit claims with typed estimates: heuristic, historical,
   matched-forward or unavailable. Test heuristic calibration offline. Unavailable
   expectancy must never become a fabricated positive value to satisfy a gate.
5. For estimated trades, use consistent return/cost units, uncertainty and a
   registered economic test. Keep an adverse observed estimate distinct from
   an unestimated thesis. A target-to-stop ratio does not supply a win probability.
6. Apply optional-evidence haircuts once. Consolidate overlapping confidence,
   uncertainty and source penalties so the same absence is not multiplied into
   a zero-sized order in several different modules.
7. Derive executable quantity from planned stop risk, current price, actual share
   constraints, liquidity, remaining account/cluster budget and policy ceiling.
   Respect minimum supported quantities without rounding above authorised risk.
8. Rank complete opportunities by registered economic rationale, data quality,
   novelty, friction and portfolio fit. Research score contributes to priority;
   it is not an account-profit probability or sole approval threshold.
9. Queue acceptable setups when market hours or capacity prevent execution.
   Persist expiry and refresh conditions. Revalidate before submission; an old
   queued setup has no unconditional right to a later trade.
10. Keep one exposure reservation per accepted intent. Release it on verified
    rejection/cancellation or expiry; partial fills retain only the appropriate
    remaining reservation. Prevent two simultaneous candidates overspending it.
11. Separate maintenance eligibility, new-entry permission and risk-reducing exit
    permission. Optional model reviews and discovery evidence cannot impose an
    unrelated global veto. Explicit current account risk or ownership holds remain.

Acceptance:

- A complete positive-estimate hypothesis and a complete bounded unestimated
  hypothesis each reach the existing PaperOps boundary in integration replay.
- Missing optional evidence reduces the permitted amount exactly once; missing
  direction, broker truth or invalidation stops execution with a precise reason.
- Known-negative, negative-control and unsupported-instrument examples cannot
  become discovery orders by changing labels.
- No high research score is needed to bypass a broken contract; the contract is
  repaired and replayed. No quota or repeated order satisfies the activity target.
- The unchanged portfolio envelope bounds simultaneous orders and every lane.

### P7. Learn From Independent Outcomes And Allocate Within The Mandate

**Primary locations:** `orchestrator/learning/forward_evaluation.py`,
`orchestrator/learning/tournament.py`, `orchestrator/learning/attribution.py`,
`orchestrator/research/component_studies.py`, `orchestrator/research/economics.py`
and the existing promotion consumer in the foundry.

Work:

1. Build cohorts from exact frozen versions and independent economic events.
   Multiple symbols or repeated entries responding to one event do not create
   independent statistical samples. Portfolio accounting still includes every fill.
2. Report all observed outcomes, exclusions, missing benchmarks and pending
   maturities. Separate gross result, modelled costs and measured net evidence.
3. Keep cash, a suitable instrument/sector benchmark and the simple registered
   strategy as comparators at matched exposure, direction and holding horizon.
   Document short benchmark and unused cash conventions explicitly.
4. Publish a timetable for each review, including independent samples, required
   events and earliest plausible completion. Audit calendar-day versus trading-
   session semantics. Preserve old definitions; corrected definitions start new
   versions rather than rewriting historical labels.
5. Permit continued bounded discovery before promotion review. Keep the existing
   20/40/80 review schedule for existing cohorts, while auditing its fitness for
   each payoff distribution. Review return magnitude, transaction costs,
   uncertainty, drawdown and concentration of profits together. Do not make
   winning more than half of trades a universal condition for promotion or call
   the existing fixed-multiplier bound a calibrated confidence interval.
   Register any revised evaluation protocol prospectively, account for strategy
   selection and repeated looks, and retain results under the old protocol.
   Neither old nor new promotion checkpoints prevent a complete micro experiment
   from starting. Show interim estimates without promoting on them; twenty
   observations alone do not establish a durable edge.
6. Register challenger rules and component comparisons before their outcomes.
   Compare market-only versus event-assisted decisions to discover whether a
   provider or model adds incremental value. Keep negative results queryable.
7. Let measured results influence priority and allocation only within the fixed
   parent envelope. Preserve a bounded exploration allocation for viable uncertain
   theses. No noisy early win can expand the USD 250 unestimated class or promote
   it to validated size; evidence-class transition uses its registered review.
8. Retire or revise persistently poor versions at scheduled reviews. Entry-policy
   changes do not automatically liquidate holdings; existing exit plans and
   portfolio risk determine how those positions are managed.
9. Record learning proposals, accepted changes, exact version inputs and observed
   consequences. A nonzero update count is not success if the change has no
   demonstrated benefit. Avoid continuous parameter search on the same holdout.

Acceptance:

- Every new complete outcome enters the correct cohort exactly once.
- The same event across several instruments is not counted repeatedly as proof.
- Baseline/enriched comparisons use identical opportunity and risk conventions.
- Test profitable low-hit-rate and unprofitable high-hit-rate payoff fixtures.
  The evaluator distinguishes their economics without treating either fixture
  as enough evidence by itself to grant validated allocation.
- A frozen strategy retains its cohort across polling cycles and restarts.
- Promotion, continuation, revision and retirement can each be explained from
  the registered evidence, with no automatic increase of the parent risk budget.

### P8. Make Health, Communications And Costs Truthful

**Primary locations:** `orchestrator/presentation/`, the current reliability
critic/watchdog, existing Telegram brief/trade senders, and
`orchestrator/research/economics.py`.

Work:

1. Present execution ownership, broker reconciliation, position protection,
   market/source evidence, strategy conversion and learning as separate health
   dimensions. A critical failure cannot be averaged into an overall green score.
2. Every observed setup gets one durable primary disposition: missing feature,
   no trigger, direction unresolved, queued, expired, risk/capacity rejected,
   accepted, submitting, broker-acknowledged, filled or reconciliation required.
   Retain its progression instead of replacing yesterday's reason with today's.
3. Report opportunities, complete hypotheses, accepted decisions, new entries,
   partial fills, exits and independent completed outcomes separately each day
   and week. Keep raw and qualified denominators visible to prevent metric gaming.
4. Investigate no-progress sessions automatically: identify the first blocked
   stage, classify abstention versus infrastructure failure, run the reviewed
   bounded handler, verify downstream progress, and escalate unresolved incidents.
5. Use the existing Telegram outbox and sender. Alert promptly on an execution
   freeze or unprotected position; do not wait three hours. Publish the scheduled
   health summary after recovery attempts, stating fixes and unresolved causes.
6. Send trade notifications from broker-confirmed lifecycle events, with stable
   event identities and delivery receipts. A submitted order is not a fill.
   Provide interesting pattern and daily strategy explanations only from fresh
   evidence; unchanged evidence should produce a short, explicit unchanged update.
7. Resolve the public-status publication fault, verify signature/digest/freshness,
   and preserve the latest valid projection with a visible stale indicator if
   publication fails. A local successful refresh is not a public deployment.
8. Import actual subscription/model/provider expenses through the existing receipt
   path. Report unknown bills as unknown. Measure provider contribution with
   registered paired comparisons, and recommend reducing unproductive spending
   rather than purchasing more services by default.
9. Keep optional LLM and quantum status accurate: inference completed, evidence
   produced, useful contribution tested, backend used and failure impact. A model
   being reachable is not proof it improved a trade.
10. Report budget or pause recommendations for repeated operational failure or
    unproductive research. A learning/economic pause blocks new allocation while
    preserving position care and broker reconciliation.
11. At five real sessions, review opportunity conversion and the weekly capacity
    target. At twenty real sessions, review independent outcome accumulation,
    benchmark-relative evidence and component expense. Persistent lack of usable
    outcomes requires a concrete data/strategy/capacity change or a recommendation
    to pause optional spending. Calendar time cannot validate a strategy, but it
    must not permit indefinite operation without a resource-value review.

Acceptance:

- Injected execution failure becomes visibly degraded locally and publicly and
  produces one deduplicated alert with its recovery state.
- Exactly one execution incident has one lifecycle across watchdog, operator,
  dashboard and Telegram; no competing restart loops or duplicate senders.
- Every trade notification reconciles with broker status and canonical identity.
- Daily no-trade reports identify whether Qadam had no setup, no capacity, missing
  evidence or broken execution. Quiet research cannot masquerade as trade health.
- Economic reports separate simulated P&L, attributable strategy evidence and
  actual operating expense; useful quantum/model value is never assumed.

### P9. Retire Legacy Paths And Release With Real Operating Evidence

**Primary locations:** the existing release scripts and launchd installer,
`config/qadam_refactor_boundaries.json`, `scripts/preflight_dashboard_deployment.sh`,
`landing-page-repo/scripts/deploy-vercel-production.sh` and current runbooks.

Work:

1. Finalise a consumer map for each retired module, command, gate and JSON writer.
   Migrate callers, prove legacy write paths unreachable, and remove code in
   reviewable commits. Keep compatibility only for named consumers during a
   documented window; historical design docs remain available without governing
   the runtime. Remove unused dependency groups only after compatibility checks.
2. Run offline replays, migration checks, security/authority boundary tests and
   targeted regression suites in isolated state. Production preflight must not
   run mutating checkers against the live account or starve the exit owner.
3. Apply additive schema migrations and roll out the exact reviewed build.
   During any entry-maintenance window, retain position care and reconciliation.
   Do not switch versions in the middle of an unresolved broker write.
4. Compare old/new pure decisions against the same frozen input set without
   letting the shadow comparator submit. Explain changed admission and sizing.
5. Enable revised trading only through the existing mandate, owner and account.
   Canary entries must come from current complete signals, with their existing
   small bounds, exits and attribution. A synthetic forced order is not acceptance.
6. Deploy presentation changes separately, verify production readiness and actual
   public route/signature responses, and compare holdings/value with broker truth.
   Keep existing desktop and mobile layout intact.
7. Observe five distinct real US market sessions on the accepted build. Include
   a supervised restart/reconnect exercise and a genuine session boundary.
   Never simulate elapsed time or backfill an operational soak.
8. Report implementation, unattended operation, trading activity and economic
   evidence as separate outcomes. If no admissible real signal occurs, report
   the observation as inconclusive for live conversion instead of certifying it.
9. Finish runbooks for restart, network loss, broker ambiguity, stale publication,
   disk pressure, provider access loss and rollback. A sleeping or disconnected
   laptop cannot provide continuous local operation; validate sleep/wake recovery
   and state the actual host-availability requirement. An always-on host is a
   separate deployment choice if continuous operation is needed.

Acceptance:

- The process runs the reviewed commit and the expected policy/schema versions.
- No duplicate write owner, legacy decision authority or unexplained open order.
- New entries, due exits, lineage and communications meet the acceptance matrix.
- Five real sessions show the required reliability and complete opportunity logs.
- Weekly trade activity and economic results are reported honestly, including
  shortfall causes and statistical uncertainty. No profit claim is a release gate.

## 6. Acceptance Matrix And Service Objectives

Targets below are engineering objectives under the provider/account conditions
specified in each test. External outage time remains visible rather than being
silently removed from the operational report.

| Scenario or metric | Required result |
| --- | --- |
| Owner expires before submit | New valid owner reconciles; no stale owner writes |
| Submit accepted but acknowledgement lost | Stable identity lookup resolves the order; no blind resubmit |
| Owner dies after submit, before ledger update | Restart reconstructs broker outcome before another write |
| Owner expires during post-submit reconciliation | Original incident resolved only after verified ownership and broker agreement |
| Competing process or reused PID | Old credentials/lease cannot authorise a broker effect |
| Research worker hangs or local model fails | Complete independent strategies and exit scheduling continue |
| Market closed | No unauthorised entry; setup is queued/expired with real timestamps |
| Optional data missing | Single registered priority/size effect; no repeated veto |
| Mandatory quote or liquidity unavailable | Explicit wait/expiry and scheduled recovery |
| Unknown expectancy, otherwise complete | Existing USD 250 / USD 5 bounded discovery contract can reach PaperOps |
| Known negative estimate or engineering control | No relabelling into discovery permission |
| Two simultaneous accepted candidates | Atomic reservations keep total and cluster exposure within policy |
| Partial fill, cancellation or replace | Quantity, reservations, protection and attribution reconcile |
| Entry freeze with a safely reducible position | Exit path remains available when broker ownership/truth permit |
| Duplicate provider story or repeated polling | Same economic identity; no new position from timestamp churn |
| Changed rule/horizon | New version; old outcomes retain original definition |
| Missing historical attribution | Unknown legacy result, never zero profit or invented strategy credit |
| Slow/missing benchmark | Trade preserved; benchmark claim delayed or unavailable |
| Expired market setup | Fresh revalidation or expiry, never automatic stale execution |
| Disk/DB contention | Bounded maintenance, critical reserved resources, no deletion of canonical evidence |
| Public publication failure | Visible degraded/stale state, bounded repair and one alert |
| Local/public/Telegram disagreement | Detected and explained from event/generation identity |
| Complete admissible opportunity to submit attempt | p95 <= 120 seconds during regular session with capacity and working provider; all exceptions explained |
| Due-exit evaluation and safe submit attempt | Evaluation cadence <= 30 seconds; attempt <= 60 seconds after detection under actionable market/broker conditions |
| Known transient execution incident | Verified recovery <= 5 minutes under working dependencies; unresolved incident alerted within 60 seconds of detection |
| Newly created order lineage | 100% decision/version/account/epoch binding; fills attributed as received |
| Opportunity disposition | 100% retained through its terminal state or visible current wait |
| Unattended session operation | >= 99% sampled entry-service availability across the five-session soak; 100% periods of degraded position protection disclosed immediately |
| Weekly activity objective | 5-10 independent new paper entries when signals/capacity permit; 10-15 only where measured capacity supports it |
| No-change processing cost | >= 30% less CPU and write volume versus equivalent P0 workload, without lost evidence |

Failure of an operational target is a release defect or a documented external
limitation. Missing market opportunity is an activity shortfall to investigate,
not permission to manufacture a trade. A release with no current valid signals
may prove recovery and offline conversion, but cannot claim observed live entry
conversion until an admissible signal actually progresses.

## 7. Verification Work And Concrete Test Locations

Extend meaningful incident and contract tests in the existing suites. Do not add
hundreds of tests that merely restate getters or inflate a completion count.
Tests that start workers, build artifacts or replay migrations use isolated state
and explicit fake brokers; they never inherit production credentials or senders.

| Work | Existing starting tests |
| --- | --- |
| Owner, broker ambiguity and recovery | `tests/test_execution_owner_recovery.py`, `tests/test_paperops_alpaca_paper_post_reliability.py`, `tests/test_qadam_canonical_paper_control.py` |
| Due exits and exposure safety | `tests/test_qadam_canonical_exit_engine.py`, `tests/test_qadam_paper_lifecycle_bracket_compatibility.py` |
| Exact accounting and lineage | `tests/test_broker_history_recovery.py`, `tests/test_qadam_refactor_attribution.py`, `tests/test_qadam_refactor_migrations.py` |
| Package and writer retirement | `tests/test_qadam_refactor_boundaries.py`, `tests/test_qadam_refactor_compatibility.py`, `tests/test_qadam_runtime_producers.py` |
| Resource use and bounded reads | `tests/test_qadam_refactor_benchmarks.py`, `tests/test_qadam_refactor_storage.py`, `tests/test_qadam_storage_capacity_recovery.py` |
| Source capability and timestamps | `tests/test_qadam_source_collection.py`, `tests/test_qadam_source_capability_registry.py`, `tests/test_qadam_point_in_time_reliability.py` |
| Foundry and decision agreement | `tests/test_qadam_strategy_foundry_v3.py`, `tests/test_qadam_decision_evidence_packets.py`, `tests/test_qadam_evidence_gate_alignment.py` |
| Sizing, policy and bounded unknowns | `tests/test_qadam_portfolio_risk_engine.py`, `tests/test_qadam_discovery_micro_conversion.py`, `tests/test_qadam_risk_router_alignment.py` |
| Frozen cohorts and component value | `tests/test_qadam_forward_shadow.py`, `tests/test_qadam_component_studies.py`, `tests/test_qadam_research_economics.py` |
| Recovery coverage and communications | `tests/test_qadam_reliability_critic.py`, `tests/test_qadam_reliability_watchdog.py`, `tests/test_qadam_trade_delivery.py` |

Add scenario coverage only where the existing suites lack the acceptance case.
After targeted tests pass, run the required broader compatibility/release checks
once for the final candidate. Real provider and broker read-only verification
then establishes which external assumptions actually hold.

## 8. Migration, Rollback And Change Control

- Each slice changes one primary responsibility and has an isolated replay before
  rollout. Do not mix a major risk-policy change with an unmeasured code migration.
- Capture the schema, policy and code version together. Additive migrations must
  preserve old record identity and remain readable by the rollback-compatible
  release during its compatibility window.
- Before code rollback, stop new entries, reconcile pending broker effects and
  preserve current exits. Never restore an old database over fills that occurred
  after its backup. Recover by forward repair or a broker-reconciled migration.
- Preserve current signed policy and manual holds. A reviewed policy transition
  replaces contradictory interpretations explicitly; a generated report cannot
  broaden authority. Existing autonomous mandate avoids daily trade approvals.
- Maintain one progress ledger here with phase, commit, tests, runtime evidence,
  residual limitations and rollback. Keep large logs in their existing bounded
  storage; do not proliferate implementation histories or certification layers.
- Keep releases small enough to diagnose. Delete compatibility code only after
  caller migration and the rollback window, not merely because CI is green.
- No service may declare itself operational by successfully reading its own last
  green report. Health must observe the current owner, broker/quote timestamps,
  actual completed work and downstream progress.

## 9. Final Deliverables And Sign-Off

Implementation is complete only when the following are reviewable:

1. A short active-call-path and ownership map with redundant writers retired.
2. A reproducible fix for the observed execution freeze and tested restart recovery.
3. Reconciled historical attribution coverage and complete lineage for new trades.
4. A dependable feature/provider contract for every active playbook.
5. Initially two executable stable playbooks, their matched comparators, their
   honest evidence classes, and their capacity/observation timetable; activation
   remains conditional on actual data and complete admission.
6. One evidence-fit admission/sizing path that admits permitted small experiments
   and retains account, liquidity, ownership and exit protections.
7. A measured learning loop showing what outcomes changed, what remained unknown,
   and how any allocation/version change was justified.
8. A daily and weekly report covering opportunity conversion, new independent
   entries, exits, failed dependencies, net performance, benchmarks and expenses.
9. Production and local state agreement, retained dashboard UX and broker-confirmed
   deduplicated Telegram trade notifications.
10. Exact-build deployment, five real-session reliability evidence, declared
    host-availability requirements, rollback procedure and unresolved limitations.

Economic success is assessed separately from installation. Look for positive
net expectancy and benchmark-relative value with uncertainty, controlled losses,
and enough independent outcomes to judge the particular strategy. Five operating
sessions can demonstrate a functioning trading loop; they cannot establish a
durable investment edge. If the activity target is missed, the report must expose
whether opportunity arrival, data, admission, portfolio capacity or execution was
responsible and what concrete action follows.

The implementation should leave Qadam with fewer things capable of stopping a
complete trade, a dependable way to manage the resulting position, and a clear
record of whether each strategy is earning its place.
