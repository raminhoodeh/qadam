# Qadam Unified Refactor And Evidence-To-Performance Implementation Plan

Date: 6 September 2026

Revision: 2. Comprehensive refactoring is the engineering approach for the existing
functional plan, not a separate rewrite or a second operating architecture.

Status: Approved for implementation; in progress. The existing implementation log
records actual phase acceptance and deployed versions. Approval is not completion.

## 1. The Next Best Action

Make the existing operation trustworthy at three boundaries: service health,
evidence-to-experiment conversion, and experiment-to-learning attribution. Then
use measured results to improve selection and allocation within the approved
paper mandate. Do not build another trading architecture or add more providers
before showing where the current ones contribute.

Do this through incremental, measured replacement of the implementation. Extract
coherent modules, eliminate redundant work and retire superseded paths. Preserve
the externally meaningful behaviour unless a separately identified repair or
approved research-policy change intentionally alters it. A file split without
less coupling, fewer competing interfaces or measured efficiency is not enough.

The intended result is more useful, independent paper experiments, fewer missed
eligible opportunities, and an auditable answer to whether Qadam adds value after
costs. More orders alone, larger positions alone, a high research score or a
positive account balance cannot establish that result. Paper profits are not
income and cannot pay operating subscriptions.

This is a targeted follow-on to
[the autonomous paper fund plan](qadam-autonomous-paper-fund-reliability-and-performance-implementation-plan.md)
and its [implementation log](qadam-autonomous-paper-fund-implementation-log.md).
Reuse their SQLite control plane, execution owner, attribution repair, forward
tournament, two lanes, exit engine, recovery handlers and reporting. Compatible
earlier controls remain in force. The older plan's incident baseline is historical,
not a list of defects that necessarily remain unfixed.

Maintain one implementation tracker in the existing implementation log. R0-R11
below are the single delivery sequence. G0-G6 remain traceable functional
acceptance contracts, not a second sequence to execute afterwards. Compatible
P0-P11 requirements from the original plan are mapped below and remain covered.
Do not create a second runtime authority or a new certification framework.

## 2. Verified Baseline And Open Questions

Inspection checkout: `032f48188f7544c95edab5ee560ac78ab06dbc12`.
These are dated, read-only observations. Refresh them before implementation;
portfolio and service figures below are not immutable operating targets.

| Observation | Evidence and interpretation |
| --- | --- |
| Automatic recovery did occur during this inspection | Operator snapshot at 15:56:36 UTC reported 21/21 fresh services, zero open circuits and zero repair requests. Watchdog at 15:58:09 UTC reported `passed`, with no blockers. The earlier 6/21 snapshot is no longer current. This does not establish a multi-session reliability record. |
| A concrete health parser defect remains in code | The watchdog retains only the last 1,200 stdout characters before parsing launchd state. A read-only `launchctl print` returned 2,088 characters: full output contained the job's running state; the retained tail did not. This proves a diagnostic defect, not that it caused every interruption. |
| Canonical paper outcomes still have limited research attribution | Of 31 outcome records inspected, five had exact entry-decision attribution and 26 remained unresolved. None contained the canonical cost-measured/net-return/matched-benchmark bundle. Existing gross-accounting reconstruction is a separate achievement. |
| Cost meanings differ between learning paths | Canonical cohort eligibility requires `costs_measured=True`. Forward shadow explicitly produces modelled-cost returns. Another attribution view labels a present `cost_bps` field as measured, regardless of provenance. This is an accounting/evaluation contract defect; it is not evidence that this field directly vetoed every trade. |
| The forward tournament exists, but its consumer freshness needs investigation | Its 10:23 UTC projection contained one registered version and zero independent outcomes. The later foundry version differed. Establish producer/registration/learner ownership and cadence before diagnosing a missing registration. Do not assume the tournament is still an empty stub. |
| Current research does not demonstrate a validated edge | The inspected 13:27 UTC backtest summary reported 336 hypotheses, 12 methods and zero historical survivors. The quantum review reported no reliable incremental value. Those findings do not prohibit the approved discovery lane. |
| Paper exposure and gains remain small | The 15:43:57 UTC mirror reported USD 100,123.80 equity, five open positions and 31 closed outcomes. This is a stored broker-backed snapshot, not a new direct broker audit. |
| Some repeated candidates are already represented in the portfolio | The inspected XAR setup encountered existing-exposure restrictions. Repeated processing of the same event is not a new independent opportunity and should not create duplicate exposure. |

Key baseline artifacts are `data/runtime/qadam_operator_service_status.json`,
`qadam_reliability_watchdog_status.json`, `qadam-control-plane.sqlite3`,
`qadam_forward_strategy_tournament.json`, `qadam_backtest_results_summary.json`,
`qadam_quantum_review_dashboard.json` and `alpaca_paper_mirror.json`.

Unresolved incident causes include host sleep/unavailability, scheduler delays,
worker progress, filesystem conditions and provider failure. Attribute each gap
using contemporary evidence. An old disk-error log is not proof of a new incident.

Additional structural observations from the same checkout:

- `orchestrator/qadam_operator_service.py` is 5,645 lines and combines service
  definitions, dispatch, leases, worker supervision, recovery and projections.
- `orchestrator/qsase_dashboard_view_model.py` is 4,606 lines; `_read_jsonl`
  reads the complete file before selecting its final records. Its writer emits
  numerous projection files on each invocation.
- `run_safe_operator_control_cycle` rebuilds several supervisory projections
  and builds operator state both before and after dispatch. Startup publication
  serves a real ownership purpose; optimize it without removing that guarantee.
- Canonical dataclasses, artifact generations, scheduler domains, resource locks,
  SQLite transactions/outbox and retention already exist. They are migration
  foundations, not missing features to recreate.
- `pyproject.toml` explicitly packages only `orchestrator` and `world_monitor`;
  nested packages need deliberate inclusion. `_service_code_state` currently
  fingerprints `orchestrator/*.py`, not nested files. Package extraction without
  packaging and build-identity changes would create a deployment/verification gap.

These are code observations, not measured CPU, memory or latency results. R0 must
establish their actual cost before any speedup claim.

## 3. Boundaries And Success Measures

- Preserve Alpaca Paper only, the existing account/epoch, single broker-write
  owner, Q-CTRL holds, idempotency, reconciliation and live-capital prohibition.
- Preserve approved position, aggregate, cluster and daily-loss limits. The
  current bounded-uncertainty micro experiment is capped at USD 250 notional and
  USD 5 planned stop risk, subject to stricter constraints and the parent USD
  5,000 per-position ceiling. Planned stop risk is not a guaranteed maximum loss.
- Preserve exits and reconciliation while research or new-entry selection is
  paused. Do not liquidate holdings or shorten valid holds to meet an entry quota.
- Automatic progression is permitted only within the approved versioned mandate.
  This plan does not authorize a larger risk envelope, new venue, live account,
  additional subscriptions or recurring quantum spending.
- Models remain research contributors, not credential holders or arbitrary
  self-modifying production repair agents. Unknown faults require explicit
  degraded status and escalation; no software can guarantee perpetual recovery.

Measure distinct things separately:

| Measure | Definition / target |
| --- | --- |
| Operational availability | Service-specific obligations completed while the host is available; separately disclose total host/network downtime. A laptop outage must not disappear from the user-facing availability report. |
| Opportunity conversion | Every fresh candidate has a terminal decision or a scheduled next check with an expiry. Every eligible, unblocked setup reaches the canonical owner by its configured execution deadline. |
| Useful experimentation | Count independent events and completed experiment lifecycles, not refreshes, partial fills or round trips manufactured to increase activity. |
| Learning completeness | Every new managed fill maps to its decision, version, event and exit policy; matured observations either have explicit cost/benchmark semantics or an explained unavailable field. |
| Economic usefulness | Preregistered forward results compared with matched alternatives, concentration, drawdown and modelled costs; operating expenses disclosed separately. |

One trade per day is an aspiration conditional on opportunity and capacity, not
a health predicate. Zero trades must have an evidence-backed explanation, but
the explanation must distinguish market inactivity from an engineering defect.

## 4. Target Structure And Engineering Rules

Keep one Python application and the existing bounded process isolation for
provider/LLM/long-running work. Do not add Kafka, Redis, Kubernetes, a graph
database, another broker gateway or a new deployment platform for this refactor.
Python and SQLite remain suitable starting points unless profiling establishes
a concrete constraint they cannot satisfy within the approved operating budget.

The following package destinations are proposed boundaries, not new services.
Existing public import paths and CLI entrypoints initially delegate to them.

| Module boundary | Existing implementation to consolidate | Intended responsibility |
| --- | --- | --- |
| `orchestrator/contracts/` | `qadam_canonical_contracts.py`, evidence/decision contracts, identity helpers | Versioned records, enums, units, provenance and boundary validation; no I/O or broker imports |
| `orchestrator/storage/` | `qadam_control_plane_store.py`, operating-ledger persistence, artifact generations and retention | Transactional repositories, indexes, bounded reads, migrations, backup and derived publication |
| `orchestrator/runtime/` | `qadam_operator_service.py`, runtime domains, locks, watchdog and recovery supervisors | Registry, dispatch, process lifecycle, durable progress, recovery and health observations |
| `orchestrator/research/` | Source adapters, feature extraction, foundry and quant/forward research | Provider evidence, deduplicated events and frozen hypotheses; no broker writes |
| `orchestrator/decisions/` | Decision transaction, experimental eligibility, Akber/risk/Router integration | Deterministic policy evaluation and canonical handoff through existing transaction boundaries |
| `orchestrator/execution/` | Canonical PaperOps, execution lease, reconciliation and canonical exit engine | Sole broker-write ownership and complete order/position lifecycle |
| `orchestrator/learning/` | Outcome attribution, forward evaluation/tournament and allocation review | Version-matched independent outcomes, comparisons and bounded proposals |
| `orchestrator/presentation/` | QSASE/operator view models and Telegram reporting | Public-safe read models and delivery; no execution approval authority |

Use dependency inversion through small interfaces where I/O is needed. Domain
contracts and calculations must not import scheduling, presentation or broker
implementations. Execution consumes accepted transactions rather than calling
dashboard builders. CI must test forbidden imports and authority boundaries.
Avoid a generic plugin framework, dependency-injection framework or new abstraction
for every function; extract only cohesive responsibilities with actual consumers.

### Authority And Storage

Keep the existing SQLite database authoritative for control-plane decisions,
handoffs, orders, fills, positions, outcomes and registered policy/version state.
Bulk historical/provider datasets remain in their existing immutable stores with
checksummed manifests. Do not move the entire research lake into SQLite.

Inventory remaining JSON operational state individually. Give each item one owner
and a justified destination: canonical table, process-local lease/checkpoint, or
read-only export. A dashboard JSON file never becomes a fallback execution source.
An unavailable canonical read is an explicit failure, not an empty healthy object.

Reuse the existing outbox and generation machinery; add transactions or indexes
only where the consumer path needs them. Multiple bounded research writers are
not multiple broker owners. Preserve short database transactions and existing
durability settings; performance work must not disable `synchronous=FULL`, foreign
keys, reconciliation or evidence checks to make a benchmark look faster.

### Change Classification

Every change set is labelled as one of: behaviour-preserving refactor, specified
correctness repair, measured optimization, or research/policy amendment. Commit
and test them separately where feasible. Replay equivalence applies to unchanged
behaviour; repaired defects have explicit expected differences. Never demand
preservation of a known bug merely to obtain matching outputs.

Preserve IDs, account/epoch boundaries, rounding rules, event ordering, policy
versions, entry/exit semantics and idempotency keys during mechanical extraction.
Freeze injectable clocks/IDs only in isolated tests, never in operational receipts.
Do not silently change Python/model versions or add dependencies during a move.

## 5. Single Delivery Sequence

The implementation log records current phase states. Development may overlap where indicated; activation
must respect dependencies and the existing execution boundaries.

Do not suspend an otherwise safe existing paper operation for the duration of
the refactor. Keep the current owner managing positions while replacements are
developed offline. Use short controlled handovers only where needed; an actual
integrity or broker-truth failure still justifies stopping new entries.

| Phase | Deliverable | Functional / original coverage | Dependency |
| --- | --- | --- | --- |
| R0 | Baseline, dependency/authority map, replays and performance budgets | G0; P0/P11 | None |
| R1 | Repair reproduced recovery/correctness faults in place | G1; P1/P9 | R0; urgent fixes need not await a long profiling window |
| R2 | Consolidate typed contracts and compatibility boundaries | G0/G2/G4; P0/P2/P4/P5 | R0/R1 |
| R3 | Extract storage, bounded queries and safe incremental publication | G2/G6; P2/P3/P9/P10 | R2 |
| R4 | Extract scheduler, worker lifecycle and verified recovery | G1/G6; P1/P9 | R2/R3 |
| R5 | Make evidence ingestion and research incremental | G4/G5; P4 | R2/R3 |
| R6 | Complete attribution, cost semantics and forward evaluation | G2/G3; P2/P3/P8 | R2/R3; parallel with R4/R5 |
| R7 | Consolidate discovery decisions and the guarded execution path | G4; P5/P7 | R4/R5/R6 prospective contracts; no wait for statistical promotion |
| R8 | Decouple and incrementally publish dashboard/Telegram views | G6; P10 | R3/R4/R6/R7 contracts |
| R9 | Integrate bounded allocation and marginal research economics | G5; P6/P8 | R6/R7; actual promotion awaits outcomes |
| R10 | Retire old implementations and run integrated regression/load tests | All G contracts; P0/P11 | R1-R9 |
| R11 | Exact production cutover, real-session observation and economic review | G6; P9/P10/P11 | R10; each earlier deployment uses the same release safeguards |

### R0. Measure And Specify Before Moving Code

Deliver a producer/consumer and authority map, a module dependency map, a
retirement register and reproducible fixtures from sanitized captured inputs.
Mark dynamic imports, CLI callers, launchd definitions, automation entrypoints,
public API/export consumers and old tests; textual import search alone is not
proof that an adapter has no consumers.

Baseline one bounded representative research cycle, a no-material-change cycle,
an execution/reconciliation replay, and dashboard publication. Collect available
existing market-session receipts now; gather missing real-session measurements
when the calendar permits. Do not execute an extra order or paid model/QPU call
solely to establish a benchmark. Profiles of historical replays are engineering
measurements, not forward trading evidence.

Record p50/p95 timings with sample counts, CPU time, peak RSS, bytes read/written,
process launches, DB connection/lock/transaction durations, queue age, provider
calls, LLM tokens/cost and dataset growth. Preserve workload size, exact code,
dependencies and host conditions. Separate provider latency from local overhead.

Acceptance: freeze numeric budgets and comparison methodology before optimizing.
No unmeasured "twice as fast" target or arbitrary trade quota becomes a release
claim. Profiling overhead is bounded and cannot delay exits or expose secrets.
Use Python's existing profiling facilities and project test tooling first.

### R1. Fix Known Faults Before Preserving Behaviour

Implement G1's full-output launchd parsing, unknown-state semantics, action-specific
cooldowns and post-repair verification as small isolated fixes. Audit the analogous
material-change detection that reads subprocess stdout tails; structured results
will replace that path in R2/R4. Preserve safe process and broker ownership during
the transition. Diagnose unexplained service gaps from matching timestamps rather
than attaching every outage to the first error found in an old log.

Acceptance: incident reproductions and genuine negative cases pass. Publish a
receipt distinguishing code verified, repair requested and recovery observed.
These fixes can ship before broad extraction; do not leave an identified defect
running merely because the comprehensive refactor has not finished.

### R2. Establish One Contract At Each Boundary

Extract/reuse the canonical records and identity helpers. Add explicit boundary
validation for schema version, UTC availability/decision times, finite numeric
values, quantities, currency, units, cost basis, account/epoch, source digest,
strategy/evaluation version, event identity and authority. Missing values remain
missing; never use truthiness to replace a legitimate zero or invent a default
direction, price or approval.

Standardize service completion as a versioned structured receipt with run/job ID,
input/output generations, success/idle/deferred/retryable/blocked status, typed
reason, progress cursor, next due time and relevant timestamps. Logs explain the
receipt; log strings do not control execution or health. A zero process exit code
without the expected validated receipt is not completed work.

Keep existing modules as thin adapters temporarily. Record each adapter's users,
replacement, tests and removal condition. Models produce schema-validated research
records with citations, not commands or executable repair instructions.

Before moving files, update explicit package discovery to include the intended
subpackages and retain `world_monitor`; allowlist package data and exclude runtime
databases, raw provider data and credentials. Build/install the distribution in
an isolated environment and smoke-test imports/entrypoints outside the checkout.
Centralize repository/state/resource resolution instead of copying depth-sensitive
`Path(__file__).parents[...]` assumptions into deeper packages.

Extend reviewed build manifests and service revalidation coverage to nested
modules, relevant scripts/configuration and dependencies. Reuse a validated
manifest per build rather than repeatedly hashing the entire tree per service.
An edited nested module must change the relevant revalidation identity; an
unrelated generated artifact must not. Preserve economic strategy identity
separately so this packaging change cannot reset valid forward observations.

Acceptance: cross-boundary round trips and malformed/missing-field tests pass;
the known foundry-to-filter shapes are covered by real producer fixtures. No
mechanical move changes stable IDs or gains broker authority. Installed-package
imports, alternate working directories and nested-file fingerprint tests pass.

### R3. Make Storage Work Proportional To The Data Needed

Split repositories, connection lifecycle, migration/backup and presentation export
from orchestration. Prefer indexed, bounded queries for recent canonical records.
For remaining JSONL readers use bounded reverse reads, an append cursor or a
validated index; a bounded-memory scan of the entire file is not an I/O solution.
Handle a partial final line, rotation, truncation, malformed records and process
restart explicitly. Limit both row count and payload bytes.

Replace timestamp-only full rewrites with generation/content-aware projection
updates. Cache keys must include relevant input generations, schema/policy version
and configuration. Cache market data only within its actual validity window;
quote freshness, session changes, expiry and time-driven exits still wake work
even when source content is unchanged. Reading a cache never refreshes evidence
`observed_at` or `available_at`.

Publish related files as a validated generation with an atomic pointer/manifest
switch using existing artifact machinery. A reader must see a consistent old or
new generation, never half of each. Maintain downstream export compatibility
through cutover; do not replace database authority with a cached view.

Use additive, resumable migrations and verified SQLite backups. Backfills use
bounded batches outside submission transactions; never hold a DB write lock
across network or model work. Exercise live-writer contention on disposable data.
Preserve existing connection-close guarantees and do not retry uncertain commits.

Make retention cooperate with appenders via the same lock/ownership protocol.
Verify archives before removing their live prefix, reconcile cursors after
rotation, and test a concurrent append/crash. Protect broker receipts, registered
hypotheses and referenced research generations. Enforce disk high-water limits
that throttle optional research before exhausting the reserve for control-plane
and exit records. Do not run broad cleanup or hydrate cloud placeholders blindly.

Acceptance: fixed-size UI reads do not load full histories; unchanged inputs do
not rewrite every business projection; migration/replay preserves row identities,
balances and receipts. 1x/2x/10x isolated history benchmarks demonstrate bounded
working memory and the agreed I/O budgets without generating production evidence.

### R4. Separate Dispatch, Recovery And Presentation

Extract registry, scheduling, leases, worker supervision, progress storage,
recovery handlers and health projection into cohesive runtime modules. Retain
existing CLI/import facades until their callers migrate. Keep the existing
execution/research/projection domains and reservations; do not invent another
scheduler or treat a refactor as permission to merge failure-isolated workers.

Dispatch on durable input-generation changes plus explicit calendar/freshness
deadlines. Use the existing transactional outbox where applicable; acknowledge
only after an idempotent consumer commits its result. Replay pending events after
restart without losing a wakeup or creating duplicate side effects. Coalesce
redundant research refreshes, but never coalesce away fills, exits or risk events.

Keep startup owner/lease publication immediate. Build heavy status views only
when relevant state changes or their reporting deadline is due. Use one validated
policy snapshot per cycle rather than repeatedly parsing the same configuration;
reload atomically when the approved version changes. Add bounded queues, provider
budgets and backpressure; reserve capacity for reconciliation and exits under
research bursts. Reuse workers only when profiling justifies it and isolation,
memory reclamation and timeouts remain testable.

Acceptance: saturation, stale-input, restart, hung-worker and clock/session cases
meet R0 budgets without starvation or false health. Scheduled reconciliation and
exit checks still occur on unchanged data. Three-hour healing remains a broad
review, not the first time a failed execution dependency is noticed.

### R5. Make Research Incremental And Focused

Implement G4's two-or-three-programme selection against actual provider capability.
Persist source cursors and economic-event identities; compute changed features
and affected hypotheses only, retaining periodic completeness audits. Distinguish
late corrections from new events and retain publication/availability provenance.
One provider outage affects dependent programmes, not every unrelated candidate.

Deduplicate syndicated stories and cache identical research analysis by evidence,
model, prompt/schema version and validity interval. Re-run when relevant evidence
changes; never reuse stale economic conclusions merely because text matches.
Gemma handles bounded extraction, Gemini selected challenges, classical methods
the baseline comparisons, and quantum work only its approved incremental question.
Apply provider terms, rate limits, source-content prompt-injection boundaries and
budget controls. Do not add paid access to conceal a capability mismatch.

Acceptance: captured no-change batches trigger no duplicate hypothesis or
unnecessary model invocation; a material new event reaches the affected research
path within its deadline. Provider/schema/LLM failures remain attributable and
resumable without granting false evidence or broker permission.

### R6. Repair The Experiment-To-Learning Contract

Implement G2/G3 using the existing ledger, attribution engine and forward
tournament. Extract pure lot attribution, return/cost calculation, independent
cohort grouping and version evaluation from their I/O adapters. Preserve original
receipts and explain permitted recomputation through versioned derived outputs.

Register each economic strategy version once, give new entries the complete
prospective outcome contract, and ingest only matured provider-backed observations
into forward review. Classify unresolved legacy attribution rather than guessing.
Keep gross paper accounting, modelled costs and observed fees distinct; provide
matched benchmarks or explicit unavailable reasons. Publish registration/consumer
lag and the real sample/horizon timetable.

Acceptance: split-fill and multi-lot examples reconcile; prospective new outcomes
can progress even when old records are irreparable. Mechanical deployments retain
economic identity. Modelled paper evaluation does not require unavailable live
measurements or pretend to establish live-capital readiness. No real trade needs
to mature before the prospective schema and accounting tests can pass.

### R7. Consolidate Decisions Without Rebuilding Execution Authority

Extract the foundry-to-discovery/Akber/risk/Router boundary behind the canonical
decision transaction. Separate pure policy evaluation from persistence and broker
I/O. Implement G4's mandatory-versus-optional evidence rules with one owner per
decision; do not create a replacement series of duplicative approval files.

Keep existing PaperOps submission, owner lease, pre/post reconciliation, exposure
checks, exit policies and idempotency semantics. Correct their adapters where
needed rather than building a second executor. Revalidate market/session state,
quotes, evidence expiry and portfolio capacity at execution time, not only at
hypothesis creation. Current scheduled exits must survive every migration.

For read-only comparison, old and refactored calculations consume the same frozen
input snapshot in isolated stores. Neither comparison process receives broker
credentials, a live authority token, the production outbox or notification-send
permission. Compare decisions, quantities, reasons, identities and exit plans;
only a reviewed canonical implementation may execute after cutover.

Acceptance: eligible discovery can progress without validated-edge status; missing
mandatory context and existing XAR/event exposure still block. Every expected
decision difference is tied to a specified repair or separately approved policy
change. Broker timeout/restart/partial-fill tests produce no duplicate submission
and no lost exit obligation. Do not demand a trade quota as proof of correctness.

### R8. Make Dashboard And Telegram Consistent Readers

Implement G6 presentation requirements as generation-based read models with
bounded queries. Preserve routes, visual design, holdings/history semantics and
public-safe fields. Publish one coherent source generation to both surfaces;
separate evidence observation time, last successful check and publication time.
Retain scheduled health summaries and meaningful pattern/daily-strategy messages,
not new schedules or duplicate "still unchanged" announcements.

Classify presentation-only failures separately from canonical execution failures.
A failed webpage or Telegram delivery cannot itself veto an otherwise authorized
paper order; an unreadable canonical store, missing evidence or active policy
hold still can. Trace and remove presentation round trips from critical execution
dependencies only after proving they do not carry a genuine safety check.

Acceptance: partial publication, slow/offline website, stale input, notification
retry and ambiguous delivery tests are truthful and deduplicated. Old/new view
models agree on account equity, open positions, exits and trade lifecycle; desktop
and mobile visual checks confirm the established dashboard UX remains intact.

### R9. Link Allocation To Measured Value

Implement G5's bounded allocation, benchmark and cost attribution reporting.
Continue under-evidenced discovery within its approved envelope; promotion and
parameter changes remain versioned decisions under the current mandate. Do not
automatically increase slots, notional limits or spend because refactoring made
the system faster. Counterfactual capacity studies run at equal aggregate risk.

Acceptance: programme-level contributions, independent event counts, running cost,
drawdown and uncertainty are visible. Negative ablations and rejected quantum
results remain in memory. Any economic policy change has separate approval,
preregistration and tests, rather than being hidden in a performance commit.
Approval already delegated within the versioned paper mandate remains automatic;
this does not introduce a new human gate for each discovery trade or permitted
promotion. Expanding that mandate or its spending/risk limits is a separate
operator decision.

### R10. Remove The Scaffolding And Prove Integration

For each retired implementation, prove replacement coverage, static/dynamic caller
migration, CLI/automation compatibility and the end of its rollback requirement.
Remove or reduce old facades to a single delegate, remove duplicate registrations
and disable superseded writers before deleting their code. A thin supported CLI
adapter may remain; two active implementations or authorities may not.

Run characterization, boundary, accounting, incident, security, performance and
end-to-end tests. Classify the full-suite baseline and resolve relevant failures.
Replay representative recorded incidents and long histories in disposable stores.
Enforce package import boundaries and prevent new stdout parsing or unbounded
history reads on migrated paths. Runtime generation must not edit source/docs
or create uncontrolled tracked-file churn; migrate exporters deliberately rather
than bulk-untracking files still required by deployment.

Acceptance: the retirement register has no unowned/deadline-free adapters. Each
migrated behaviour has one implementation, one authority and evidence of its
measured cost. Any retained legacy path has a narrow documented purpose. File
count and line count are diagnostic metrics, not the definition of success.

### R11. Release And Observe Without Rewriting History

Use the release procedure below for each independently deployable slice, followed
by final integrated release verification. New code does not remain merely a
parallel prototype while the old defective route continues indefinitely.

Record three distinct milestones: implementation accepted, production release
verified, and real-session observation completed. Five real US sessions on the
final release and the 20-session economic review remain required; do not label
them complete during an off-market refactor. Preserve economic strategy evidence
across non-economic code changes while tracking operational build changes honestly.

Acceptance: exact core/site versions, migration receipts, broker reconciliation,
live route checks and all relevant G contracts pass. Pending real-time observations
have their next automatic check and owner. Unattended failure-free operation or
future profit is not promised by a passing software release.

## 6. Functional Acceptance Contracts Retained From Revision 1

G0-G6 below specify what the integrated phases must deliver. They are not another
implementation run after R11. Existing implementation credit is retained only
where current code and evidence support it.

### G0. Establish A Reproducible Starting Point

Capture the exact code and policy versions, database schema, active account/epoch,
leases, broker reconciliation, open exit obligations, service timestamps, current
candidate/version identities and all unresolved outcome categories. Use a
consistent SQLite read transaction for linked counts and a supported backup
method for migrations; never copy only the main file of a live WAL database.

Inventory each producer, authoritative owner and consuming projection. In
particular trace the runner shared by launchd checks, the strategy registration
event owner, forward tournament owner, canonical outcome owner and portfolio
views. Preserve the dirty checkout's generated files and existing plan/log changes.

Record defects as either reproduced, suspected, already repaired, or awaiting
real-market evidence. Establish an explicit baseline for the previously reported
39 unrelated test failures, re-running them before calling them unchanged.

Acceptance: each gap has a reproduction, owner, targeted test, affected contract,
rollback procedure and evidence location. No phase can pass merely because a
status JSON was regenerated.

### G1. Make Self-Healing Depend On Reliable Observations

Primary targets: `orchestrator/qadam_reliability_watchdog.py`, its existing tests,
the reliability snapshot consumers and `orchestrator/qadam_operator_service.py`.

Parse the full command result before truncating/redacting diagnostic logs. Extract
the actual launchd job state and PID rather than matching unrelated coalition
states. Audit all callers of the shared command runner for the same tail-only
parsing problem. A timeout, malformed result or permissions failure means unknown,
not stopped. Cross-check process identity, exact build, lease and recent progress.

Use independent action cooldowns for operator restart, critic wake and worker
recovery. A recent operator restart must not accidentally prohibit a necessary
critic action, while a genuine in-flight critic must not be repeatedly launched.
Respect startup grace and measured service completion budgets. Detect a missed
watchdog interval within two normal ticks once the host resumes; do not invent
successful checks during sleep. Capture sleep/wake and heartbeat gaps explicitly.

Separate command acceptance, process presence, service freshness, broker
reconciliation and completed recovery. Retry bounded, known transient causes;
do not reset circuits without passing the affected real check. Exhausted retries
produce a specific incident with last progress, attempted repairs and next action.
Keep execution ambiguity frozen until the singleton reconciles outstanding orders.

Acceptance: long-output, unknown-state, startup, active-lease, network-loss and
sleep/wake tests do not produce false stopped/healthy states, restart storms or
duplicate broker writes. A disposable end-to-end recovery exercise demonstrates
the expected receipts; a live market soak remains a separate requirement.

### G2. Make Paper Results Usable Without Pretending Costs Were Measured

Primary targets: `orchestrator/qadam_outcome_attribution.py`,
`qadam_operating_ledger.py`, `qadam_forward_shadow.py` and
`qadam_outcome_learning_promotion.py` under the same directory.

Extend the existing versioned outcome contract rather than adding another ledger:

- Carry cost provenance per component: broker-reported, modelled or unavailable;
  include units, cost-model version, observation time and supporting receipt.
- Distinguish gross broker-paper P&L, return after observed fees, and return under
  a specified cost model. Presence of `cost_bps` must never imply measured costs.
- Keep fees, spread, latency, borrowing and market-impact assumptions separate.
  Do not subtract spread already represented in entry/exit fill prices a second
  time. Counterfactual stress costs remain a separate scenario, not broker cash.
- Pin matched benchmark identity, entry/exit timestamps, provider observations,
  direction/exposure convention and corporate-action treatment. Missing data is
  unavailable, not zero return. No-trade incremental P&L and interest-bearing
  cash opportunity cost are different comparisons and must be labelled.
- Permit discovery continuation and explicitly modelled-cost paper evaluation
  under their approved contracts. Do not require live-only measurements to learn
  from paper trades; do not grant live-readiness credit for modelled results.

Repair historical mappings only when order/fill evidence supports them. Allocate
partial exits across actual entry lots and preserve account/epoch boundaries.
Keep the 26 unresolved outcomes in account accounting and an explicit unresolved
research cohort; never assign a convenient current strategy retrospectively.
Unrepairable historical data must not prevent complete new experiments.

Use existing broker activity ingestion with bounded pagination, durable cursors,
overlap/deduplication and reconciliation. Version derived corrections with their
inputs; preserve original receipts. A migration must be restartable and must not
rewrite broker history or change the actual portfolio balance.

Acceptance: new prospective outcomes satisfy one documented paper evaluation
contract; modelled costs are never labelled measured; missing fees/benchmarks
remain explicit; partial-fill replay yields the same exposure and P&L. Existing
and new records remain queryable without fabricated strategy credit.

### G3. Reconcile Strategy Versions And The Time Needed To Learn

Primary targets: `orchestrator/qadam_forward_tournament.py`,
`qadam_forward_evaluation.py`, the registration producer and existing view models.

Verify every active economic strategy version is registered once, with its actual
registration time, frozen hypothesis, evaluation policy and cost assumptions.
Each version must appear in the next due learner projection, or have an explicit
reason for exclusion. Detect producer/consumer lag rather than silently displaying
an older version. Retire or visibly scope legacy projections that contradict the
current portfolio or tournament; no old "remain cash" artifact gains authority.

Keep economic strategy identity distinct from application build identity. A
reporting-only deployment must not discard valid strategy observations. A change
to economic rules, horizon, selection, exits or cost assumptions creates a new
preregistered version; do not inherit proof from the old rule set. Operational
release observation still tracks the exact deployed build separately.

The current evaluator admits only non-overlapping outcomes and reviews at
20/40/80/... observations. Publish the implied observation timetable for each
actual hypothesis. If a holding/evaluation window is five market days, 20
non-overlapping windows require roughly 100 market days at minimum, before gaps
in event arrivals. Do not promise validation in a few weeks under that contract.

Evaluate whether that conservative sampling design fits each programme. Retain
it initially, or preregister a reviewed dependence-aware alternative using event
clusters and time blocks. Overlapping events, syndicated reports and correlated
instruments must not simply become extra independent samples. Select shorter
horizons only for a different economically justified hypothesis, not to game N.

Maintain separate states for permission to start/continue small discovery
experiments, eligibility for emerging review, and validated allocation. Twenty
observations is a review checkpoint, not automatic proof or a prerequisite for
the first discovery trade. Repeated looks and strategy variants retain the
existing multiple-testing discipline.

Acceptance: exact-version tests, registration lag tests and real-calendar horizon
tests pass; every excluded outcome has a reason; the dashboard reports sample
count and plausible time-to-review without implying a promised completion date.

### G4. Concentrate On Obtainable Evidence And Complete The Trading Path

Primary targets: the existing capability registry, source adapters,
`orchestrator/qadam_strategy_foundry_v3.py`, experimental eligibility, Akber/risk
adapters, `paperops_autonomous_pass.py` and the existing exit owner.

Rank the actual 41-source/19-instrument capability inventory by usable published
evidence, provider freshness, historical availability, executable mapping,
independent event arrivals and running cost. Catalogue membership is not coverage.
Choose two or three programmes initially; keep other valid research running at
its appropriate low-cost cadence rather than deleting it.

| Programme candidate | Required evidence before selection |
| --- | --- |
| Semiconductor earnings/capacity versus sector-relative repricing | Available transcripts or primary statements, exact publication times, instrument mapping, current provider-backed price/volume context and a falsifiable mechanism |
| Defence/geopolitical events versus defence-sector repricing | Deduplicated material events, direction and horizon, sector-relative market response and existing-position/cluster checks |
| Power constraints or prediction-market-to-listed-proxy research | Select only if existing provider access actually supports the frozen hypothesis; unavailable history, missing executable proxy or contract comparability keeps the affected programme in research/shadow |

These are programme candidates, not current buy recommendations or assertions
that their relationships are profitable. Do not invent a sixth core strategy or
expand the instrument universe just to fill activity metrics.

Gemma extracts structured claims and contradictions; Gemini challenges selected
economic mechanisms; classical quant methods test them against simple baselines.
Retain useful quantum results, including negative results. Further IBM jobs need
a specific incremental question, matched classical comparison and an approved
budget; quantum availability does not mandate another paid run.

Compile each fresh event into one typed trade hypothesis: direction, executable
instrument, trigger, horizon, source/availability lineage, invalidation, entry
policy, exit policy, benchmark and bounded uncertainty. Freeze the decision-time
snapshot before routing. Test the actual foundry-to-Akber-to-risk-to-Router
contracts, not only mocked standalone gate objects.

Use the existing discovery lane's soft uncertainty policy. Optional missing
evidence may reduce size or schedule a final market-hours check. Missing direction,
usable current liquidity/quote evidence, invalidation, broker truth, budget or
execution authority still blocks. Unknown expectancy must not be relabelled
positive; a known-negative unchanged strategy must not be recycled as discovery.

Every stopped idea gets a primary reason, owning component, evidence needed,
retry time and expiry. Capacity-blocked ideas may enter independent forward
shadow evaluation, explicitly counterfactual and without paper-fill credit.
Repeated XAR/event observations must neither add duplicate exposure nor count as
new discoveries. Preserve max-hold, stop and exit lineage across restarts.

Acceptance: a genuine eligible discovery setup with no validated historical edge
can traverse the existing guarded route within its approved micro mandate. A
synthetic contract fixture proves wiring only; operational execution requires a
fresh real setup. Missing mandatory evidence and duplicate exposure still stop
execution with the correct reason. There is no compulsory daily trade count.

### G5. Allocate According To Evidence And Account For Running Costs

Reuse the existing portfolio allocation and cohort machinery. Keep present
discovery slot and cluster limits initially. Analyse the existing three-versus-six
slot proposal offline at equal aggregate risk; do not silently enable six slots
or increase the USD 5,000 ceiling. Additional slots are not additional independent
evidence if they express the same underlying event.

At preregistered reviews, compare frozen versions against no trade, a matched
simple benchmark and relevant simpler models. Report net modelled returns,
dispersion, dependence, concentration, drawdown and behaviour across available
regimes. Use positive and negative findings; do not tune repeatedly against an
already revealed holdout until it turns profitable.

Continue promising under-evidenced versions inside existing discovery bounds;
pause operationally unsafe or materially invalidated ones; promote only under the
approved evidence route. Approved allocation changes need a durable decision and
rollback condition, never direct model authority. Larger size is an output of
this process, not a substitute for evidence.

Add marginal-value reporting for each selected source/model: attributable new
events, decision changes, forecast improvement and cost. Run ablations without
leaking later information or altering live hypotheses. Reduce redundant polling
before proposing any provider cancellation; user subscriptions require explicit
approval to cancel. Keep bounded retention so research does not refill the disk.

Record actual subscription/API/quantum expenses separately from broker P&L.
The user's previously reported USD 120/month is an estimate until reconciled to
current bills. Report paper performance and research operating cost separately;
do not describe simulated profit as cash earnings after expenses.

Acceptance: allocation has an event-level evidence trail and respects every
parent limit. Reports show which components help, which are unproven and what
they cost. A negative or inconclusive result remains a valid review outcome.

### G6. Report Coherently, Release Exactly And Observe Real Sessions

Extend the existing dashboard view models and Telegram reporting, including
`orchestrator/qadam_research_telegram.py` and `qadam_hedge_fund_team_health.py`.
Preserve navigation and UX. Do not create another scheduler or duplicate brief.

Report four separate states: system operational health, fresh evidence supply,
eligible experiment progression, and economic evidence. Health must not imply
profitability, and an idle market must not imply a broken service. Show blocked
counts and owners, actual sample progress, cost basis and last successful work.

Retain the existing interesting-pattern alerts and daily strategy explanation.
Changes in timestamps or stale template scores are not new insights. Explain
material evidence changes, resulting action or hold, current allocation and
invalidation. An unchanged quantum result is unchanged, not a new daily discovery.
Report recovery attempts and confirmed recovery separately, preserving delivery
deduplication and ambiguous-send handling.

Release from a clean worktree with a reviewed migration, targeted regressions,
changed-code lint and a classified full-suite baseline. No new failures are
acceptable; any baseline failure touching these contracts must be resolved or
explicitly block release. Do not count an unrelated failure list as a blanket
waiver. Promote the exact tested core SHA through the established deployment
path; deploy the site only if its code changes and verify its served version.

Use a safe, reconciled owner handover. Do not restart in the middle of an ambiguous
broker submission or overwrite concurrent runtime state. Retain original exits,
stop new entries on migration/reconciliation failure, and use a schema-compatible
rollback. Never roll back by deleting real fills or restoring an old portfolio.

Verify the canonical PaperOps summary, broker lifecycle receipts, mirror and
duplicate counters together. A staged order is not a submission; a submission
is not necessarily a fill. Synthetic broker tests remain explicitly synthetic.

Complete five distinct real US market sessions on the release for operational
acceptance, followed by a 20-session economic progress review. The latter is an
assessment of evidence accumulated, not a promise that a 20-outcome cohort has
matured. Existing valid economic observations survive non-economic deployments.
No backfill, fake elapsed time or weekend certification credit is permitted.

Acceptance: release verification passes immediately where testable; real-session
milestones remain pending until observed. At review, decide continue, revise,
reduce cost or pause based on evidence, rather than promise weekly profit.

## 7. Mandatory Regression Matrix

| Case | Required outcome |
| --- | --- |
| Launchd output exceeds 1,200 characters; unrelated states also appear | Correct job/PID extracted before log truncation; no false stopped state |
| Diagnostic timeout while valid owner lease/progress exists | Unknown diagnostic, bounded retry, no blind owner replacement |
| Operator restart followed by critic requirement | Independent cooldowns; one appropriate recovery action, no storm |
| Sleep/wake or provider outage with existing positions | Visible availability gap; fresh reconciliation; exit obligations preserved |
| Process fails around an ambiguous broker response | Existing idempotency key reconciled before retry; no duplicate order |
| Partial fills, partial exits and multiple entry decisions | Exact lot/decision allocation; reproducible accounting across replay |
| Modelled costs supplied with no live cost measurement | Explicit modelled paper evaluation; no measured/live proof claim |
| Missing benchmark or fees | Explicit unavailable basis, not invented zero or fabricated completeness |
| Irrecoverable legacy attribution plus valid new outcome | Legacy quarantined from strategy proof; new learning progresses |
| Current strategy version absent from a due tournament projection | Detected owner/consumer lag with reason, not silent stale success |
| Reporting deployment versus economic rule change | Preserve economic evidence for the former; preregister the latter |
| Multiple reports/symbols reflect one event; windows overlap | Dependence retained; no inflated independent observation count |
| No validated edge, but complete approved discovery setup | Bounded discovery route remains available without waiting for 20 outcomes |
| Optional missing evidence versus mandatory missing execution context | Existing soft haircut/recheck versus explicit hard block |
| Existing XAR/event exposure or occupied cluster slot | No duplicate exposure, quota-driven exit or disguised new experiment |
| Critical source expires during recovery | No trade on stale evidence; service-specific degraded state remains visible |
| No eligible idea during a real session | Explained idle state with candidate stops, not fake health or fake activity |
| Message retry, unchanged research or stale quantum result | No duplicate delivery or invented insight |
| Older CLI/import or automation invokes a migrated component | Supported single delegate or explicit migration error, never an unnoticed legacy writer |
| Service exits successfully but omits/mismatches its result receipt | Work not certified complete; explicit contract failure |
| No content changes but quote/session/exit deadline expires | Time-driven work still runs; cached evidence cannot extend its validity |
| Research queue saturates or a model hangs | Reserved execution/exit capacity and bounded worker resources remain available |
| Consumer crashes between committing a result and acknowledging an event | Durable replay and deduplication, no lost work or duplicate side effect |
| UI requests the newest records from a growing history | Bounded bytes/memory, correct ordering and explicit oversized/corrupt-record handling |
| Retention races a writer or archive verification fails | No lost append; original recoverable data retained until verified safe replacement |
| Projection publication crashes halfway through a generation | Readers see one complete old or new generation, never mixed portfolio truth |
| Database migration is interrupted or new code must roll back | Compatible old/new reads or explicit safe stop; broker history and exits preserved |
| Read-only comparison accidentally attempts an external write | Blocked by absent credentials/lease/network permission, not merely by a prompt |
| Presentation is unavailable but execution dependencies are healthy | Visible presentation degradation without an invented trading veto |
| Refactor changes event IDs, rounding, sizing or exit rules unexpectedly | Equivalence test fails; release blocked pending an intentional change specification |
| New nested module omitted from package or reviewed build fingerprint | Installed-build smoke test or identity test fails before cutover |
| Extracted module runs from a different working directory | Correct configured resources/state root, no accidental new ledger or writes to the checkout |

## 8. Verification, Migration And Release Protocol

### Performance Acceptance

R0 records the baseline values and numeric budgets in the existing implementation
tracker. Freeze the workloads and targets before accepting an optimization; an
unmeasured dimension is marked unavailable, not reported as a saving. Use warm
and cold runs with sample counts and comparable host conditions. Keep timing
benchmarks separate from deterministic functional CI to avoid flaky tests.

| Dimension | Required acceptance approach |
| --- | --- |
| Local runtime | Compare cycle CPU, wall time and p95 local dispatch latency separately from external waits; a speedup in reporting cannot excuse an execution regression |
| Memory and disk I/O | Bounded history readers at 1x/2x/10x selected fixture sizes; record peak RSS and bytes processed, not only output row count |
| Projection efficiency | Identical input generations do not cause repeated full business-output writes; small independent health heartbeats may continue |
| Database health | Monitor connection lifetime, busy waits, WAL size and write transaction duration under concurrent disposable workloads; preserve durability and correctness |
| Work scheduling | Measure due-to-start delay, completion deadline misses, backlog and exit/reconciliation service under research bursts |
| Model/provider economy | Compare calls/tokens/expenses per independent event and completed experiment; cached identical work must not create duplicate calls |
| Storage stability | Enforce validated retention and protected-data reserves; distinguish legitimate new evidence growth from repeated derived copies |
| Economic conversion | Report candidate-to-decision and decision-to-handoff reasons; broker fills depend on market conditions and are not a software benchmark target |

Every optimization needs a predeclared budget plus a non-regression check on
execution correctness, freshness and protected-data retention. If measurements
show an extraction has no material performance benefit, retain it only for a
documented reduction in coupling or ownership ambiguity; do not advertise it as
an efficiency win. No blanket percentage saving is promised before measurement.

### Test Layers

Use the project's `.venv/bin/python`, pytest and Ruff configuration. The unit,
contract and replay suites run with isolated temporary state, deterministic test
clocks and no broker/Telegram/paid-provider credentials. Imports themselves must
not migrate or modify production state. Test clocks and historical replays never
write real-calendar certification or forward-performance credit.

Cover pure calculations; old/new serialization and identity; actual producer to
consumer contracts; SQLite migration, crash and concurrency; worker supervision;
broker lifecycle via a deterministic fake transport; source/model failures;
view-model/Telegram delivery contracts; installed-package/build-identity tests;
and full captured-cycle replay. Use
selected immutable research fixtures rather than copying the entire data lake.
Sensitive receipts are redacted without changing identifiers needed for matching.

Run live provider/broker read-only verification separately with its scope declared.
A genuine paper order may occur only through the active guarded owner when the
real setup and approved policy permit it. No direct broker-write probe, synthetic trade,
forced delivery or additional paid quantum job is part of refactor acceptance.

### Migration Pattern For Each Subsystem

1. Specify the boundary, preserved semantics, intentional repairs and acceptance
   data. Identify all consumers and record the old/new schema support matrix.
2. Add the compatible interface and additive storage changes behind the current
   implementation. Verify backup restoration against a disposable database.
3. Extract/refactor behind that interface and replay against captured inputs.
   Store comparisons outside production state; normalize only known incidental
   differences such as test run IDs, never meaningful decisions or missing data.
4. Switch a read-only consumer first where possible and verify observed behaviour.
   Switch a stateful owner only through its existing lease/maintenance mechanism;
   never dual-write competing authoritative decisions or orders.
5. Publish one active implementation selection in the reviewed release manifest.
   If flags are temporarily necessary, give them one owner, a version and a
   removal date. Do not scatter fallback environment switches across modules.
6. Verify the live receipt chain and resource budgets. Roll back code only when
   schema/receipt compatibility is proven; otherwise pause new entries and repair
   forward while continuing safe reconciliation/exit responsibilities.
7. Remove superseded code, registrations and adapters once their consumers and
   rollback needs are satisfied. Destructive schema contraction waits until the
   rollback window closes; retain old fields if removal has no material benefit.

### Production Release Checklist

- Re-read active state and user changes. Use a clean `codex/` worktree for tested
  changes, preserve existing generated data and never blanket-stage the checkout.
- Record reviewed core SHA, dependency versions, migration IDs, policy hashes,
  input-generation support and the selected implementation for each boundary.
- Run targeted regressions, changed-code lint, document/schema checks and the
  classified full suite. A passing test count is not proof of deployed readiness.
- Take and verify an appropriate consistent backup. Check free space and migration
  cost before starting; never copy a live SQLite main file without its WAL context.
- Drain or reconcile in-flight writes before an owner handover. Preserve pending
  client IDs, accepted orders, fills, holdings and the original exit obligations.
- Activate the exact tested build through the established launchd/core release
  path. Confirm executable/build identity, one owner, fresh service obligations,
  current policy and broker reconciliation before allowing new entries.
- If site code changes, deploy the corresponding reviewed site SHA and inspect
  served routes/content and desktop/mobile UX. A static site deployment is not a
  core-runtime deployment; verify both when both changed.
- Confirm the canonical PaperOps summary, order lifecycle, mirror and idempotency
  counters together. Report actual outcomes, including healthy idle or deferred
  market session, without manufacturing a submission to pass the release.
- Let the existing health/reporting schedule collect the real-session evidence.
  No new duplicate automation or forced Telegram test message is needed.

For an incident, display the affected subsystem, last successful work, exact stop,
repair attempted, verification result and next action. Deterministic repairs may
run unattended within reviewed bounds; unknown code changes, credentials, new
spend or policy expansion require an explicit operator decision. Do not pretend
an on-laptop supervisor can run while the laptop itself is unavailable.

## 9. What Completion Would Mean

Engineering completion means the gaps are repaired, tested and deployed with
specific receipts. Operational completion means the deployed release demonstrates
its obligations and recovery behaviour through the required real sessions.
Economic progress means Qadam accumulates attributable independent evidence and
uses it to make bounded decisions; profitable repeatability may remain unproven.

The implementation order is R0-R11 with the dependencies in Section 5. R1 repairs
known faults first. R2/R3 provide the shared contracts and storage boundaries;
R4/R5/R6 may then progress in parallel without sharing competing authorities.
R7 activates the complete experiment path, R8/R9 expose and use its evidence,
R10 removes the old scaffolding, and R11 establishes production and observed
acceptance. G0-G6 are the acceptance coverage for this same work, not extra phases.

The final handover must include the tested/deployed SHA(s), completed migrations,
new module/authority map, retired-path register, before/after performance report,
functional regression results, current broker reconciliation, remaining incidents
and real-session milestone status. Every deferred item needs an owner, reason and
next check. If a required engineering item remains, do not call the refactor
complete merely because a production release was made.

The core engineering work can be completed without waiting for a profitable
trade. Real market outcomes cannot be completed in a coding session. No additional
subscriptions, capital or user-supplied dataset are prerequisites for beginning
the engineering phases; provider gaps discovered later must be named explicitly.

## 10. External Design References

Alpaca documents limitations of its simulated fills, including omitted impact,
latency slippage, queue effects, regulatory fees and dividends. That supports
separating broker-paper accounting from modelled economic results; it does not
justify opening a live account to satisfy a paper-learning field.
[Alpaca: Paper Trading](https://docs.alpaca.markets/us/docs/paper-trading).

Alpaca's activity schema provides activity/order identifiers, fill quantities,
prices, timestamps and pagination. Use available receipts for reconciliation and
exact allocation, without assuming every live-only cost appears in paper records.
[Alpaca: Account Activities](https://docs.alpaca.markets/us/docs/account-activities).

Incremental replacement reduces the size of each cutover and lets individual
changes demonstrate value before the old implementation is retired. The proposed
module boundaries are specific to Qadam, not a requirement to introduce services.
[Martin Fowler: Strangler Fig](https://martinfowler.com/bliki/StranglerFigApplication.html).

SQLite's backup API supports consistent online snapshots; WAL imposes specific
concurrency and checkpoint considerations. Use the existing verified backup and
connection lifecycle rather than copying live database files or weakening
durability for speed.
[SQLite: Online Backup](https://www.sqlite.org/backup.html),
[SQLite: Write-Ahead Logging](https://www.sqlite.org/wal.html).
