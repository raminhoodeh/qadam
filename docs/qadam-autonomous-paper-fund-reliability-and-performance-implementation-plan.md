# Qadam Autonomous Paper Fund: Reliability And Performance Plan

Originally drafted: 2026-09-06

Revised after repository and read-only runtime inspection: 2026-10-26

Status: Approved implementation sequence; delivery and verification are recorded
in `docs/qadam-autonomous-paper-fund-implementation-log.md`. This plan is not a
runtime certificate. Its dated baseline is retained below; current readiness
must come from the authoritative runtime and release evidence.

Scope: Consolidate and repair the existing autonomous Alpaca Paper operation,
increase useful independent experimentation, and connect measured outcomes to
bounded strategy allocation. Preserve the existing dashboard UX.

Implementation order: recover the execution/reconciliation deadlock; verify
position protection and accounting; make self-healing prove consumer recovery;
then improve opportunity conversion and measured strategy allocation. Do not
start by lowering thresholds, increasing size or rebuilding working modules.

## 1. The Objective And Its Limits

Qadam should operate without routine human intervention, convert obtainable
information into timely investment experiments, manage their complete lifecycle,
and allocate its approved paper risk budget according to measured results.

The objective is improved expected performance after realistic costs, subject to
drawdown, concentration, operational and research-budget limits. The objective is
not the highest hindsight return, a compulsory daily trade, or a profitable week
every week. Neither a perfect trade selector nor indefinite failure-free service
can be promised. Successful engineering and demonstrated investment value must
be certified separately.

The initial product remains an autonomous paper fund. Paper gains are simulated;
they do not pay subscriptions or establish readiness for live capital. No phase
enables a live account, leverage expansion, a new execution venue or outside
investor capital.

Here, autonomous means unattended operation inside an approved mandate, including
safe abstention, position management, bounded recovery and evidence-led changes.
It does not mean sentience, unlimited execution authority, autonomous production
code rewriting or freedom from intervention when credentials, hardware, an
unknown defect or a hard safety constraint requires an operator.

Continuous improvement means a continuous evaluation process. Its honest output
may be no change, a smaller allocation, retirement or shutdown of an uneconomic
programme. Neither strategy quality nor returns can be made monotonically better
by scheduling more model calls or trades.

Weekly reviews answer four questions:

- Did the operation complete its responsibilities without hidden failure?
- Did new, independent information become appropriately bounded experiments?
- Which strategies added value relative to matched alternatives after costs?
- What evidence justifies continuing, changing, scaling or retiring a version?

## 2. Why This Is A Consolidation, Not Another Architecture

Keep the SQLite/WAL control plane, canonical decision pipeline, guarded PaperOps
owner, two trading lanes, existing research engines and existing dashboard. Do
not create another executor, competing policy file, certification vocabulary or
parallel authoritative outcome ledger.

This plan supersedes its September 6 baseline with the October 26 inspection.
Earlier CATC, evidence-fit, layered-judgment, graph-learning, execution-core and
reliability plans remain design history. Their completion labels are not current
runtime proof. In P0, map overlapping requirements into one implementation
tracker; preserve working implementations and compatible safety contracts and
retire redundant writers. Repair a verified gap rather than reimplement a feature
because an old plan described it as missing. This document does not amend a signed
policy or grant execution authority.

Use three independent release claims:

| Claim | Evidence required | What it does not imply |
| --- | --- | --- |
| Implementation verified | Reviewed code, migrations, contract tests and incident replays pass | The deployed service is currently healthy |
| Unattended operation demonstrated | Exact deployed runtime passes real-session and recovery observations | A strategy is profitable |
| Economic evidence demonstrated | Attributed, independent, cost-aware forward results satisfy a preregistered evaluation | Every future week will be profitable or live capital is authorised |

## 3. Current Evidence Baseline And Root Cause

The observations below were inspected on October 26 around 11:38-11:43 UTC
(15:38-15:43 Asia/Dubai), against checkout
`5f7b9d55243d297b1ddbf00d807d1617c0442ee0`. They are a dated baseline, not a
claim about the state at implementation time. P0 must recapture them without
submitting an order. Runtime files can change while this document is being read.

| Finding | Evidence inspected | Required response |
| --- | --- | --- |
| Canonical execution is frozen, with broker reconciliation overdue | Read-only `execution_state` and `reconciliation_runs` in `data/runtime/qadam-control-plane.sqlite3`; `read_operating_health()` reports `paper_order_allowed: false` | Recover the actual incident before claiming entry readiness |
| The freeze began after immediate post-entry reconciliation on October 23 | `2026-10-23T15:21:53Z`: durable reconciliation blocker `position_entry_allocation_unresolved:SOXX` | Establish exact order/fill/allocation timing and preserve the original cause |
| Later reconciliation passed, but the freeze remained | Passed runs at `15:22:10Z` and `15:22:41Z`, with fresh broker observations, two positions, no open orders and matching protection digest | A passing read is insufficient if incident eligibility cannot progress |
| The submission wrapper loses the specific cause | `orchestrator/paperops_alpaca_paper_post.py` replaces detailed blockers with `immediate_post_entry_reconciliation_blocked` | Persist structured causes, reconciliation IDs and affected entities before raising |
| The recovery classifier does not recognise the resulting freeze | `orchestrator/execution/ledger.py`, `_recoverable_freeze()`; reason `immediate_post_entry_reconciliation_failed:immediate_post_entry_reconciliation_blocked` | Replace fragile reason-string recovery with reviewed typed recovery contracts; no blanket prefix exemption |
| Four service circuits are open, with no scheduled automatic retry | `guarded_paperops`, `execution_position_care`, `paper_lifecycle_poll`, `power_market_research`; circuit state classifies them as `code_defect` | Recover prerequisites, distinguish downstream safety holds from defects, and revalidate each service's real work |
| A running scheduler does not mean the four workers are advancing | Operator lists 22 services: 18 fresh, four not run; subsequent receipts say `circuit_breaker_open` | Preserve original failure receipts and measure completed work, deadlines and queue progress |
| A validator can pass while runtime is degraded | Service checks report `passed`; operational/observation readiness and the watchdog do not | One dimensional readiness projection; validator success cannot override execution truth |
| A fresh broker preflight coexists with stale canonical reconciliation | October 26 read-only preflight: active paper account, two positions, 104 historical orders; canonical reconciliation still October 23 | Route verified observations through canonical reconciliation; neither an empty-account test nor an unrelated fresh read is a readiness substitute |
| Recovery/notification assurance is incomplete | Repair queue contains critical execution and service incidents; watchdog reports no healthy soak credit and unconfirmed trade-delivery state | Verify recovery and acknowledged delivery; do not count artifacts or queued messages as success |
| The source catalogue is not 41 independently usable live feeds | Coverage: 23 collected, four derived aliases, two intentionally disabled, seven needing configuration, three not selected, two retry scheduled | Preserve distinct capability states; build strategies from genuinely obtainable evidence |
| Frontier analysis is intentionally paused | Dedicated Gemini key passed a small generation probe; provider/account hold remains | Keep the hold; resumption requires its reviewed release procedure, not a self-healer workaround |
| Local/quantum availability is not economic proof | Local model completed analysis; quantum review reported no incremental value on the tested edges | Track work freshness separately from demonstrated predictive/economic contribution |

The confirmed recovery design fault is a lost-cause and recovery-eligibility
deadlock: post-entry failure becomes an unrecognised generic freeze, and relevant
services then stop. Later passed reconciliations do not clear that freeze. This
does not prove the original SOXX discrepancy was harmless provider lag. Its exact
allocation cause must be reproduced; an unexplained position is still a blocker.
The power-market circuit needs its own original receipt diagnosis and must not
be presumed to have the same cause as execution.

This explains why adding looser strategy gates alone cannot solve the current
failure. It also explains how reassuring summaries can coexist with no trades:
processes and validators can be alive while accepted work cannot reach execution.

### Historical Findings Are Regression Obligations, Not Current Claims

The September inspection reported intermittent database access, unclassified
closes, symbol-based attribution, missing benchmarks and empty tournament
projections. Subsequent refactors added execution, storage, attribution,
benchmark and economics modules and tests. P0/P2/P3/P8 must establish which old
defects remain, which are fixed and which have never been proven in operation.
Do not assume the old counts, balances, thresholds or absent features are current.

The exact source count, instrument count, trade count, policy and balance must
come from current registries and broker-backed records. Catalogue membership,
research scores and one profitable period do not establish a tradeable edge.

## 4. Non-Negotiable Boundaries

- Preserve Alpaca Paper only, the existing account/epoch and the $5,000 absolute
  per-position ceiling unless a separate explicit policy amendment is approved.
- Preserve one broker-write owner for entries, exits, cancellations and
  replacements. Exit scheduling may be independent; write ownership may not.
- Models, quantum workers, source adapters, dashboard and Telegram never receive
  direct broker-write authority or broker secrets.
- Akber is decommissioned as an execution authority. Do not restore it as a gate
  or add another model veto. Historical labels and compatibility adapters may
  remain only where they cannot acquire decision or broker-write authority.
- Preserve Q-CTRL policy where applicable. Distinguish research availability from
  an explicit execution hold; do not silently waive the latter.
- No forced trades, invented evidence, synthetic current timestamps, retroactive
  preregistration, fabricated receipts or historical credit as forward results.
- No automatic increase of the parent risk envelope, paid subscription or quantum
  spend. Prior task-specific spending authorisation is not a recurring budget.
- Automatic strategy selection and parameter promotion operate only inside the
  versioned, approved paper mandate. Novel unsupported actions produce proposals.
- No production self-modification, arbitrary shell commands or model-written
  risk bypasses. Repairs use reviewed deterministic handlers and verified builds.
- Provider suspension, payment/credit exhaustion, revoked credentials and explicit
  operator holds are not transient faults to retry until they disappear. Do not
  rotate keys, change projects, buy credits or lift a hold automatically.
- Keep hypotheses, negative results and genuine market history. Storage cleanup
  removes only bounded, regenerable material under the retention policy.
- A dashboard refresh, passing test suite or Telegram message cannot create
  execution eligibility or proof credit.

## 5. Target Operating Contract

One durable chain links:

`provider observation -> economic event -> frozen hypothesis/version -> current
evidence envelope -> lane-specific judgment -> portfolio allocation -> canonical
decision/handoff -> guarded broker lifecycle -> attributed outcome -> cohort
evaluation -> approved strategy version/allocation`

Every material record must carry applicable account, epoch, strategy family,
strategy version, economic-event identity, hypothesis identity, evidence digest,
decision identity, policy version and observation time. Order and fill identities
extend this chain; they must not replace it with a symbol lookup.

Maintain two lanes:

| Lane | Purpose | Admission and progression |
| --- | --- | --- |
| Discovery | Small experiments with plausible but unproven hypotheses | Obtainable directional evidence, executable context, explicit falsifier, bounded risk and a frozen evaluation plan; uncertain expectancy is labelled, not invented |
| Validated | Allocate more within the approved envelope to better-supported strategies | Adequate independent, cost-aware historical/forward evidence under the applicable preregistered validation route, plus current tradeability |

Historical absence and historical rejection are different. A hypothesis with
clear negative evidence is not recycled unchanged into discovery merely to fill
a slot. A revised mechanism must explain the change and start a new version.
An engineering negative control remains non-trading evidence.

### 5.1 Ownership And Dependency Boundaries

| Responsibility | Existing owning modules to retain | Boundary |
| --- | --- | --- |
| Durable state and transactions | `orchestrator/storage/control_plane.py`, `orchestrator/execution/ledger.py` | SQLite authority; JSON is a projection or immutable evidence, not a second policy/position ledger |
| Execution mandate and fencing | `orchestrator/execution/contract.py`, `orchestrator/execution/ownership.py`, `orchestrator/contracts/execution_recovery.py` | One leased, fenced broker-write owner; reason strings are display text, not permission |
| Broker submission and readback | `orchestrator/paperops_alpaca_paper_post.py`, canonical PaperOps wrapper | Stable request identity and bounded post-submit reconciliation |
| Position care | `orchestrator/execution/care.py`, canonical exit engine | Independently scheduled, but shares the exclusive write owner and reviewed risk-reducing mandate |
| Evidence and strategies | `orchestrator/research/source_collection.py`, `source_time.py`, `economic_events.py`, `foundry.py`, `core_strategies.py`, `playbooks.py`, `focus.py` | Typed decision-time evidence; no direct orders and no independent admission authority |
| Benchmarks and economics | `orchestrator/storage/benchmarks.py`, `orchestrator/research/economics.py`, component studies and existing learning modules | Attributed outcomes and comparisons, not a second performance ledger |
| Operating truth and notifications | `orchestrator/presentation/operating_picture.py`, `generations.py`, `orchestrator/execution/incident_alert.py`, existing Telegram sender | Shared fresh read model and durable delivery state; no competing bot or execution permissions |
| Recovery orchestration | Existing operator, self-healing supervisor, watchdog and critic | One incident lifecycle with reviewed handlers, not independent repair authorities |

Keep `qadam_*` compatibility entry points only where consumers still need them;
test that they delegate to these owners. Ownership changes must reduce competing
writers and imports, not create another service for every historical plan.

### 5.2 Operation Permissions While Degraded

Persist the relevant permissions as a projection of the current incidents and
approved policy, not as four manually editable booleans:

| Operation | Required state | If execution entries are frozen |
| --- | --- | --- |
| Read broker truth | Valid paper endpoint/credentials and bounded request budget | Still allowed; no order POST, cancel or replace |
| Reconcile durable state | Valid readback, storage and correctly scoped reconciliation authority | Still allowed through the recovery route; appending verified reconciliation is not an order permission |
| Protect/reduce an existing position | Fresh exact quantity, known allocation, applicable exit contract and exclusive write owner | Allowed only if the specific hold and signed care policy permit it; no blanket bypass |
| Submit new exposure | Fresh canonical reconciliation, no relevant holds, complete decision, risk and exit contracts | Not allowed until incident-specific release is proven |

A manual stop must declare its scope, including whether position care remains
permitted. Broker disagreement must never be converted into an automatic sell or
blind retry. Read-only recovery must not depend on `require_execution_available()`
for new entries, nor claim a second broker-write lease.

## 6. Phases And Dependencies

Acceptance for every phase starts pending revalidation. Existing implementations
may satisfy individual tickets after inspection and proof. Each completion entry
must contain code SHA, schema and policy versions, tests, observed evidence,
residual limitations and rollback plan. Do not turn a pending real-market
milestone into a passed implementation test.

| Phase | Deliverable | Dependencies |
| --- | --- | --- |
| P0 | Reproducible baseline and ownership inventory | None |
| P1 | Broker-verified recovery and canonical operational truth | P0 |
| P2 | Exact lifecycle attribution and reconciled accounting | P0; production cutover after P1 |
| P3 | Independent outcome cohorts and durable experiment memory | P2 |
| P4 | Obtainable evidence converted into trade-shaped hypotheses | P0; consumption uses P2 identities |
| P5 | Empirically evaluated, lane-specific judgment | P3, P4 |
| P6 | Experiment capacity and portfolio allocation | P3, P5; activation requires P7 |
| P7 | Durable exits, reconciliation and churn prevention | P1, P2 |
| P8 | Real forward tournament and bounded automatic promotion | P3, P5, P6, P7 |
| P9 | Full-stack recovery coverage and sustainable operation | P1; certify against P2-P8 |
| P10 | Dashboard, Telegram and documentation parity | Canonical outputs from P1-P9 |
| P11 | Exact-build release, real-session soak and economic evaluation | P0-P10 |

P2/P4/P7 development can overlap after their input contracts are frozen. No phase
may enable new economic authority before its dependencies and exit controls pass.
Dependencies refer to implemented contracts, not to waiting for statistical
significance: a discovery experiment does not need its own future outcome to
exist before entry. Mature evidence is required for promotion, not for correctly
labelled small experiments already authorised by the discovery mandate.

### P0. Establish A Reproducible Baseline

**Owner:** control-plane/release workstream. **Output:** one sanitised baseline
manifest, incident fixture pack and requirement-to-test tracker.

**Work**

- Record the checkout SHA, dirty files, installed launchd arguments, runtime
  path, Python environment, policy digests, account/epoch IDs, leases, storage
  state and exact service build. Preserve unrelated user/runtime changes.
- Take a consistent SQLite backup using the supported backup mechanism, including
  WAL semantics, and verify restoration in an isolated directory. Do not copy a
  live database without its transactional context or delete its WAL to fix it.
- Recheck historical database-access regressions in isolation and inspect current
  integrity, WAL/checkpoint behaviour, permissions, volume and disk watermarks.
  Do not diagnose disk exhaustion from an old incident: the October 26 read
  showed approximately 251 GiB available, not a full disk.
- Obtain broker account, positions, orders and fills read-only. Reconcile them
  against the control plane and record discrepancies without resetting the epoch.
- Inventory every entry/exit writer, learner, policy builder, health checker and
  projection consumer. Classify it as canonical, compatibility-only or retired.
- Capture a sanitised incident fixture pack from the real failure shapes. A
  checker that writes artifacts must run in an isolated runtime until reviewed.
- Capture the original failed receipt, not just the later skipped receipt, for
  each of the four open circuits. Preserve stderr, exit status, dependency state,
  start/end time and build generation. Diagnose power research separately.
- Inventory pending, submitted, partially filled, cancelled and filled orders,
  every open allocation and exit obligation. Label whether the currently deployed
  code can protect each holding under its actual hold scope.
- Map historical plans into tickets under P0-P11: satisfied with evidence,
  regression/gap, superseded or externally blocked. List functions/services to
  retain, consolidate or retire; require one owner per mutable artifact.
- Record secret references and key suffix/fingerprint only, never secret values.
  Qadam uses its dedicated backend key; nsso and Dreamsea are out of scope. Shared
  Google-project quota/billing remains a shared dependency despite separate keys.

**Acceptance**

- A reproducible baseline identifies every live writer and authority source.
- A restored copy passes integrity and identity checks without touching Alpaca.
- Missing access remains an explicit blocker, never an empty healthy database.
- The October 23 SOXX failure and persistent-freeze sequence has a failing
  regression before repair. Previously fixed storage/attribution cases remain
  passing regressions. No trades are submitted by baseline collection.
- Each current circuit has an evidence-backed root cause or an explicit unknown
  with a diagnostic next action; four circuit names are not asserted to be four
  independent code defects.

**Rollback/containment:** baseline collection is read-only against production.
Backup restores and fault replays use separate paths, accounts are not reset,
and unrelated working-tree changes are not included in a release.

### P1. Repair Recovery And Operational Truth

**Owner:** execution/control-plane workstream. **Primary code:**
`orchestrator/execution/ledger.py`, `orchestrator/execution/contract.py`,
`orchestrator/execution/ownership.py`,
`orchestrator/contracts/execution_recovery.py`,
`orchestrator/paperops_alpaca_paper_post.py`,
`orchestrator/qadam_canonical_paper_control.py`,
`orchestrator/paperops_autonomous_pass.py`, the operator and watchdog.

**Work**

- Persist cause-specific incidents with state transitions: detected, repairing,
  recovery-verifying, resolved or escalated. Track the first failure, latest
  attempt, retry budget, next action and affected execution scope.
- Extend the existing control-plane schema transactionally rather than add a
  parallel incident database. Store incident ID/generation, typed cause, causal
  parent, affected order/decision/allocation, reconciliation ID, build, policy,
  hold scope and remediation contract. Preserve the original failure payload.
  An error wrapper may add context but must not replace a specific cause with
  `immediate_post_entry_reconciliation_blocked`.
- Reproduce SOXX order/fill/allocation arrival sequences. Distinguish an exactly
  identified pending canonical allocation from a genuinely unexplained position.
  Reserved and partially filled exposure consumes risk immediately. A bounded
  settling state must retain submission identity and a deadline; it cannot grant
  new entries or conceal quantity disagreement until final mapping is proven.
- Give post-entry observation convergence a bounded read-only revalidation path.
  Broker lag is a hypothesis to verify, not the default explanation. If exact
  lineage, quantity, protection or broker lookup cannot converge within the
  reviewed recovery budget, escalate and keep the affected execution hold.
- For a known transient mirror failure, refresh broker truth and verify account,
  positions, orders, fills, owner lease and unresolved writes before releasing its
  freeze. Compare-and-set the incident version so an older successful repair
  cannot clear a newer failure or an unrelated/manual risk hold.
- Recovery must run while entries are frozen; it cannot depend on the very
  submit gate it is repairing. Two successful independent refreshes are a
  proposed transient-recovery test, not a substitute for full reconciliation.
- Replace permission inferred from string prefixes with typed allowlisted
  recovery contracts. For this existing generic freeze, first perform a reviewed,
  receipt-backed migration linking the original SOXX reconciliation and order.
  Migration preserves the freeze; ordinary recovery must then acquire current
  authority and obtain new broker evidence. Never reinterpret every generic
  `ControlPlaneError` as transient or clear a hold directly in SQL/JSON.
- Resolve an incident only after post-incident, unexpired observations verify
  account/epoch, exact orders/fills/allocations, protected quantities, no unresolved
  write and current ownership. Two distinct broker reads must represent actual
  reads, not two regenerated projections of Friday's payload. A new fill or
  quantity change must be explained, not hidden to force matching digests.
- Resolve individual holds transactionally with compare-and-set incident/version
  checks. Clearing one incident cannot erase a simultaneous operator, risk,
  storage or unexplained-broker hold. Derive entry permission from all remaining
  relevant holds; retain the audit trail after resolution.
- Ambiguous submission goes to read-only broker lookup by stable client/order
  identity. Never retry merely because a timeout looks transient.
- Persist request identity before network I/O; reuse that identity across crash
  recovery, never a timestamp-based replacement ID. Renew and fence the sole
  owner for entries, exits and replacements. Test lease expiry during slow broker
  calls. Broker effects are reconciled from durable intents and lookup, not an
  assertion that a local database transaction makes an external API exactly-once.
- Separate recovery/reconciliation scheduling from the failing submit command.
  A frozen entry worker must not prevent lifecycle GETs or current canonical
  reconciliation. Recovery uses the same existing authority boundary and may not
  start a second live writer. Reopen downstream service circuits only after their
  own safe revalidation completes real work, not after resetting failure counters.
- Keep broker reconciliation freshness separate from session-aware market quote
  freshness. A closed exchange explains inactive entries, not a stale account or
  missing owner. Revalidate pending setups at the next genuine session.
- PT-3 qualification and PT-4 staging must consume the accepted decision
  generation before submission; stale projections fail visibly and are repaired
  through the canonical path. A legitimate empty queue remains explained idle.
- Publish health as execution, position protection, research and learning
  dimensions. A failed critical dimension cannot be averaged into overall green.
- Distinguish `ready_idle`, `market_closed`, `entry_held`, `care_degraded`,
  `dependency_unavailable` and `operational_failure` through existing public
  contracts where possible. Keep separate validator results and live work
  receipts; do not add another contradictory global readiness file.

**Acceptance**

- Injected refresh failure followed by verified recovery clears only its own hold
  without manual JSON changes or an order submission.
- Persistent broker disagreement, access loss, unknown write outcome and manual
  stops remain blocked with a precise recovery/escalation reason.
- Kill/restart at every handoff boundary produces no duplicate broker effect.
- All present-tense readiness claims reference fresh authoritative observations.
- Replay the complete October 23 sequence: the initial allocation failure is
  retained; later current matching broker reads can resolve an authorised
  transient cause; an unexplained allocation cannot. Recovery requires no forced
  entry, arbitrary shell action, JSON rewrite or relaxation of portfolio risk.
- Crash before/after incident resolution cannot lose an active hold; an older
  successful repair cannot clear a later failure. Recovery still works with the
  entry circuit open and the frontier model held.

**Rollback/containment:** keep new entries held if migration, readback or typed
classification is uncertain. A compatible application rollback preserves new
incidents and broker events. Never restore an old ledger over current fills.

### P2. Repair Lifecycle Attribution And Accounting

**Owner:** accounting/lifecycle workstream. **Primary code:**
`orchestrator/execution/ledger.py`, `orchestrator/storage/control_plane.py`,
`orchestrator/execution/order_projection.py`, migrations and lifecycle bridge.
Audit the existing refactor first; change only demonstrated gaps.

**Work**

- Replace latest-order-by-symbol attribution with exact entry/exit order, fill,
  lot/allocation, decision and strategy-version links. Cover partial fills,
  partial exits, replacements and multiple strategy allocations in one broker
  net position without creating multiple broker owners.
- Allocate shared-position quantities before submission. The sum of strategy
  allocations must equal broker quantity; unexplained excess freezes affected
  new exposure. Never retroactively assign a trade to whichever strategy won.
- Use explicit order/position lifecycle states rather than infer fill completion
  from a Telegram message or an order acknowledgement. Include partial fill,
  cancel requested, cancel confirmed, replace pending and late correction.
  Explain temporary in-flight differences without accepting unexplained exposure.
- Preserve immutable source events. Correct attribution and accounting through
  versioned correction events and rebuildable materialised views; do not use
  `INSERT OR IGNORE` to prevent later verified evidence from repairing a view.
- Reconstruct legacy lineage only from exact evidence. Mark unresolved history
  unassigned, retain it in account totals and exclude it from strategy promotion.
- Store gross and net dollar P&L, capital-normalised return, risk-normalised
  return, fees, currency, cost basis, actual timestamps and cost-model version.
  Missing P&L is unknown, not zero. Dollar P&L cannot be subtracted from a
  percentage benchmark return.
- Separate broker NAV from analytical cost-adjusted NAV. Reconcile cash flows,
  open-position marks, realised/unrealised results, splits, dividends and fees
  without rewriting the broker balance or treating deposits as profit.

**Acceptance**

- Two same-symbol trades from different versions remain correctly attributed
  after reversed arrival order, retries, partial closes and replay.
- Every new paper fill has exact account/epoch/strategy/decision lineage.
- All legacy closes identified by P0 are either evidence-reconstructed or
  explicitly unresolved; the September count is not reused as today's count.
  No attribution is guessed and no balance is reset.
- Fill quantities and account reconciliation pass documented precision rules;
  broker/model limitations are separately visible, not absorbed by wide tolerances.
- Re-running corrections is idempotent and preserves original evidence.
- Every post-entry failure retains a resolvable link to the order and allocation
  it concerns. Cash plus signed position value reconciles to broker equity within
  documented broker precision; short-sale proceeds are not additional profit.

**Rollback/containment:** corrected views are rebuildable from immutable events;
unknown attribution remains visible and excluded from promotion, not deleted.

### P3. Make Experimental Learning Statistically Meaningful

**Owner:** research measurement workstream. **Primary code:**
`orchestrator/execution/ledger.py`, `orchestrator/storage/benchmarks.py`,
`orchestrator/research/component_studies.py`,
`orchestrator/qadam_outcome_learning_promotion.py`,
`orchestrator/qadam_graph_outcome_learning.py` and
`orchestrator/qadam_learning_attribution_v2.py`.

**Work**

- Use one canonical outcome contract across broker outcomes, forward shadows,
  counterfactuals and research memory. Preserve their different evidence classes;
  a shadow record is never a filled trade or live proof.
- Preregister mechanism, event/instrument mapping, direction, horizon, entry and
  exit rules, cost assumptions, benchmark, falsifier and evaluation schedule.
- Group observations by strategy version, economic event, overlapping holding
  window and predefined regime. Report raw trades and effective independent
  blocks separately; three semiconductor ETFs on one event are not three proofs.
- Benchmark using the same information cutoff, entry/exit times, exposure basis
  and realistic cost convention. Compare cash/no-trade, a simple instrument
  baseline and the incumbent. Mark unavailable comparisons unknown.
- Record losers, blocked candidates and foregone opportunities without selecting
  only the eventual winners. Distinguish operationally missed opportunities from
  economic abstentions; counterfactual estimates remain estimates.
- Estimate uncertainty using a dependence-aware method, with thresholds and
  review dates frozen before the evaluation. Correct for multiple hypothesis
  selection and repeated peeking; do not promote on an arbitrary row count.
- Make prior failures retrievable before generating a new hypothesis. Require an
  explicit changed premise or new evidence when revisiting a rejected version.
- Preserve existing evidence-graph links for source, claim, event, hypothesis,
  version, decision and outcome. Shared citations identify dependence, not extra
  corroboration. A graph edge is a provenance-backed relationship, not proof of
  causality, predictive power or an executable strategy.
- Keep the evaluation denominator: attempted variants, eligible opportunities,
  blocked or missed decisions, censored/unmatured outcomes and completed outcomes.
  Publish survivorship and look-ahead checks before ranking strategy versions.

**Acceptance**

- Duplicate/replayed rows and overlapping signals cannot increase independent
  evidence credit. Missing results cannot improve expectancy.
- Strategy cohorts have matched benchmarks or an explicit evaluation hold.
- Outcomes spanning versions do not silently pool into a profitable aggregate.
- Learning changes a traceable proposal or allocation decision; merely writing a
  postmortem does not count as applied learning.
- Provider revisions recompute affected analytical views with a correction
  version without rewriting what the original decision could have known.

**Rollback/containment:** questionable cohorts lose promotion eligibility while
account history remains intact. Do not restore economic credit by filling nulls
with zero or pooling older strategy versions.

### P4. Convert Available Data Into Better Opportunities

**Owner:** evidence/strategy-conversion workstream. **Primary code:**
`orchestrator/research/source_collection.py`, `source_time.py`,
`feature_availability.py`, `economic_events.py`, `source_context.py`,
`foundry.py`, `core_strategies.py`, `playbooks.py`, `focus.py`,
`orchestrator/qadam_source_capability_registry.py`,
`orchestrator/qadam_trigger_factory.py`,
`orchestrator/qadam_pattern_score_v3.py`,
`orchestrator/qadam_strategy_foundry_v3.py`, qualitative and power-market modules.

**Work**

- Inventory actual provider entitlements, payload fields, publication frequency,
  latency, history, identity mapping and execution-data availability. Classify
  each source as trigger, confirmation, slow context, forward-only or unavailable.
- Start with the competency-led programmes already represented in the code:
  semiconductor/policy/options context and crude-oil/energy transmission. Confirm
  their current priority from actual source coverage and measurable information
  value, not a historical ranking. Defence, power scarcity, silver and prediction-
  market geopolitical hypotheses remain eligible research where coverage permits.
  Do not keep every programme execution-critical simply to justify 41 sources.
- Extract numeric changes and grounded claims: surprise relative to expectations,
  announced capacity and dates, contract value, load/renewable forecasts, prices,
  inventory or rate changes. Tone alone is not an economic directional signal.
- Preserve publication time, first availability, retrieval time and revisions.
  Backtests use the version actually knowable then; new information cannot
  rewrite an old feature snapshot.
- Give timestamp verification a source-specific contract: timezone, official
  publication/revision field, first-seen observation, uncertainty bounds and
  admissible research uses. A retrieval time alone cannot prove historical
  availability. Unverified old timestamps make evidence forward-only or excluded
  from the affected backtest, not newly published or globally execution-fatal.
- Trace World Monitor and other aggregation feeds back to available underlying
  sources and timestamps. Syndicated copies, derived aliases and cached summaries
  are not independent confirming feeds. Never promote an unsourced headline into
  a verified numerical release, company statement or earnings-call quotation.
- Test that score changes respond to economic feature changes, not just source
  presence or template metadata. Label unchanged/stale evidence honestly. A
  research-quality score remains distinct from calibrated return probabilities.
- Generate a falsifiable hypothesis, authorised tradable expression, timed entry
  condition and invalidation for each actionable event. Use abstain when the
  direction or instrument relevance cannot be supported.
- Distinguish automatically assembled template variants from newly discovered
  relationships. Allow supported new mechanisms as versioned research proposals;
  do not confine all research to the original five family names.
- Trigger incremental work on material evidence changes and real market windows.
  Deduplicate repeated stories and revised copies before counting novelty.
- Build small, falsifiable cross-source features rather than ask one model to
  interpret every API. Examples: capacity/backlog change plus options/price
  response for semiconductors; supply or geopolitical event plus inventories,
  price and instrument exposure for energy; load/weather/constraint surprise plus
  geographic exposure for power. Each feature needs a baseline, publication lag,
  mechanism, uncertainty and negative control before economic credit.
- Select the tradable instrument through the approved universe and evidence of
  economic exposure. Prediction-market probabilities can be research features;
  they do not authorise prediction-market order execution or prove a listed proxy
  moves in the same direction. Additional options/venues require separate mandate
  and lifecycle support, not a new informal trading lane.
- Produce an explicit executable-evidence envelope in one producer: event,
  instrument, direction, window/expiry, provider-backed quote and liquidity,
  invalidation, source provenance, estimated/unknown return state and version.
  Version the producer/consumer schema together. Reject schema drift in tests
  before a consumer can demand a field the foundry never emits.
- Distinguish usable execution feed coverage from unavailable ideal data. For
  example, verified limited-venue quotes must be labelled as such, not asserted
  to be a consolidated full-market order book. Review which liquidity tests the
  actual entitlement can support; do not fabricate spread from daily bars.

**Acceptance**

- Representative provider packets from each active programme traverse the same
  typed contracts used by live operation, without manual field completion.
- A changed claim/value updates the relevant hypothesis; a mere refetch does not
  create another economic event, trade opportunity or independent observation.
- Each intended execution proxy has verified data, calendar, currency, lot-size,
  venue and corporate-action handling; unsupported mappings stay research-only.
- Power tests do not assume a California wholesale signal automatically predicts
  a listed producer with different geographic exposure.
- At least one representative valid packet from every intended execution
  programme traverses source ingestion, frozen hypothesis and canonical review.
  Unsupported access produces a scoped configuration state, not endless retries.

**Rollback/containment:** disable a broken feature/programme and use the remaining
approved evidence path; preserve source packets and original availability times.
No feature rollback may silently widen the instrument universe.

### P5. Calibrate Gates To The Two Lanes

**Owner:** decision-contract workstream. **Primary code:** research foundry and
playbooks, `orchestrator/contracts/decision.py`,
`orchestrator/execution/contract.py`, `orchestrator/qadam_strategy_decision.py`,
`orchestrator/qadam_layered_market_judgment.py`, portfolio risk and Router.
Akber remains retired; old test names are not authority to restore it.

**Work**

- Publish a single gate register: required field, producer, consumer, freshness,
  lane applicability, missing-versus-adverse interpretation and repair owner.
  Eliminate redundant local copies of the same prerequisite.
- Keep account truth, executable quotes, liquidity, explicit direction, bounded
  sizing, invalidation, position protection and idempotency mandatory.
- Treat optional corroboration and immature historical certainty as uncertainty
  that can reduce size or defer entry within the discovery mandate. Stale quotes
  require refresh; they are never made acceptable by a confidence haircut.
- Replace arbitrary discounted best-rejected-backtest returns with a documented
  empirical estimator and uncertainty state. Reward-to-risk geometry alone does
  not establish a positive win probability or positive expected return.
- Verify the already implemented unknown-expectancy discovery route end to end.
  A plausible, preregistered hypothesis can buy bounded information with paper
  risk only under the current approved contract. The playbook has unestimated-
  return ceilings of $250 notional and $5 planned loss; reconcile these with the
  signed mandate and tighter portfolio constraints before use. They are not new
  spending authority or guaranteed loss bounds. Amend a missing authority
  explicitly rather than disguise an experiment as a validated edge.
- Build decision-time shadow/context snapshots before their consumers demand
  them. A matured outcome cannot be required before the first discovery experiment.
- Replay retained decision-time evidence against the current and proposed gates.
  Measure conversion, cost-adjusted results, drawdown, false positives and missed
  opportunities; reserve untouched time blocks for the challenger decision.
- Audit every entry point and retired adapter against the same lane contract.
  There must not be a second legacy requirement for a validated edge downstream
  of an admitted discovery candidate. Equally, a high research score cannot
  bypass the canonical execution freeze or create missing liquidity evidence.
- Define queue TTL, session revalidation, retry class and deterministic next
  action for each deferral. A queued setup is not a perpetual standing buy: reject
  expired evidence and require a current trigger before execution.

**Acceptance**

- Complete valid discovery candidates can reach portfolio evaluation without an
  OR-10 edge, completed forward trade or manual payload amendment.
- Adverse economics, invalid direction, missing liquidity and safety breaches
  still reject or defer. Negative controls never become tradable strategies.
- Each stop has one primary reason, supporting reasons and a responsible repair
  or research action. Gate counts are not represented as unique rejected trades.
- Frozen held-out comparisons justify each threshold change; an increase in
  submissions alone is insufficient evidence of improvement.
- A current, complete, low-risk discovery hypothesis can progress without a
  frontier-model response when no explicit binding consultation hold applies.
  A score of 0.6 or 0.7 is not relabelled as a 60% or 70% win probability.

**Rollback/containment:** keep the incumbent signed gate policy, run a challenger
in shadow and revert the challenger version if conversion or risk contracts
regress. Do not remove hard controls to manufacture a positive-path test.

### P6. Allocate Capacity And Size At Portfolio Level

**Owner:** portfolio/allocation workstream. **Primary code:**
`orchestrator/qadam_portfolio_risk_engine.py`, current policy
builder in `orchestrator/qadam_backtest_completion.py` and canonical allocation.

**Work**

- Reconcile strategy/lane classification of all open allocations before changing
  limits. A generic `canonical_discovery_micro` label must not erase family,
  correlation or source-concentration exposure.
- Size using the minimum of approved notional, remaining experiment risk budget,
  liquidity/capacity and risk at invalidation, with lot rounding and gap/stress
  allowances. A stop is not a guaranteed maximum loss.
- Evaluate replacing blanket pairwise-correlation rejection with incremental
  cluster exposure and stress-loss limits where justified. Keep same-event
  duplication checks and measure concentration across common drivers.
- Test current three-slot capacity against a proposed configuration allowing up
  to six smaller independent experiments without raising the parent discovery
  loss/exposure budget. This is a policy proposal, not an authorised live change.
- Preserve the $5,000 absolute ceiling and one effective allocation ladder.
  Inventory actual signed canary, unknown-return and validated tiers; do not reuse
  historical $500-$1,000 suggestions as current policy. Show each applied haircut
  once so sequential consumers cannot create accidental zero size or a mandatory
  minimum. The ceiling is not the recommended position size.
- Rank eligible allocations by conservative return evidence and incremental
  diversification; rank discovery experiments additionally by expected information
  value under a separately bounded budget. Log the allocation and rejected
  alternatives. Unknown return estimates cannot masquerade as profitable ones.
- Do not shorten horizons, churn positions or repeatedly buy a high-score symbol
  to meet a frequency target. Re-entry requires the frozen strategy condition and
  a demonstrably new decision episode.
- Include pending orders, reservations, partial fills and expected exits in
  atomic capacity accounting; never release risk because a worker timed out.
  Enforce daily loss, aggregate notional, cluster exposure, spread/slippage,
  turnover and strategy/feature concentration through one portfolio evaluation.
- Preregister any shorter-horizon challenger as a separate shadow version. It
  earns a paper trial through the same evidence and mandate rules, not by changing
  old exits to free slots. Report feasibility of the existing 5-10 independent
  weekly-entry aspiration before adopting it as an operating target.

**Acceptance**

- Portfolio scenarios prove every hard budget survives correlated shocks, stale
  marks, partial fills and simultaneous signals within the model's stated limits.
- Raising slot count does not silently raise aggregate approved risk or leverage.
- An affordable valid minimum lot can pass; an unaffordable one remains a clear
  sizing rejection rather than an implementation failure.
- Report opportunity supply, slot occupancy and average holding time. Three
  five-session positions imply roughly 0.6 new entries per session at full use;
  a higher frequency goal must have a feasible independent opportunity supply.

**Rollback/containment:** stop new allocations on breached budgets, but retain
original exit obligations. A slot/size experiment starts within the same approved
parent envelope and can revert without mass liquidation or resetting history.

### P7. Protect Positions And Avoid Artificial Trading Activity

**Owner:** execution/position-care workstream. **Primary code:**
`orchestrator/execution/care.py`, `orchestrator/qadam_canonical_exit_engine.py`,
the execution ledger, canonical PaperOps and existing exit compatibility adapter.

**Work**

- Before entry, persist stop/invalidation, profit-taking policy, maximum holding
  period, thesis reevaluation triggers, quantity ownership and strategy version.
- Validate which broker-native protective orders are supported for each
  instrument/lot/order type. Where protection is synthetic, expose dependence on
  host connectivity and do not describe the position as broker-protected.
- Verify partial-fill protection and exact covered quantity. Alpaca bracket exits
  do not become active until the entry is completely filled; fast markets can
  also produce a stop/target race. Test the supported order semantics, not an
  assumption that a bracket guarantees a maximum loss. Corporate actions and
  unsupported extended-hours behaviour require explicit handling. [Alpaca order
  documentation](https://docs.alpaca.markets/us/docs/orders-at-alpaca)
- Let position management run independently of expensive research, LLM and
  backtest jobs while using the same exclusive broker-write owner.
- Respect original position intent across deployments. A new strategy version or
  stale optional input must not liquidate unrelated holdings. Risk-reducing exits
  require their own current evidence and reconciled quantity.
- Define emergency policies for broker outages, data outages, drawdown and manual
  stops. Continue read-only reconciliation while new entries are frozen; no blind
  emergency sell retry when the broker result or position quantity is unknown.
- Exercise the current incident while a due exit exists: fresh readback and known
  allocation must reach the narrowly authorised care route even if entry review
  or optional research is down. If the hold forbids all writes or quantity is
  unresolved, preserve supported broker protection and escalate immediately.
- Attribute every exit and re-entry to thesis expiry, invalidation, target, risk
  event or explicit operator action. An order count must not reward churn.

**Acceptance**

- Every new open allocation has a complete durable exit plan.
- Restart, partial fill, gap, stop/target race and cancel/replace races produce no
  oversell, unexpected short exposure or second independent order writer.
- Research outages and deployment changes do not trigger mass liquidation.
- Real paper round trips reconcile through fills, position closure and attributed
  outcome; synthetic integration tests receive no real-market proof credit.
- Every scheduled care pass reports due obligations, attempted/completed work,
  fresh quantities, protection coverage and a precise no-action reason. A living
  wrapper or stale exit-summary file is insufficient evidence of protection.

**Rollback/containment:** entry activation stops if exit coverage cannot be
verified. Application rollback preserves live protective orders and original
position contracts; cancellations require the same exclusive broker owner.

### P8. Implement A Real Tournament And Bounded Promotion

**Owner:** strategy evaluation workstream. **Primary code:**
`orchestrator/research/core_strategies.py`, `playbooks.py`, `component_studies.py`,
`economics.py`, `orchestrator/qadam_outcome_learning_promotion.py`,
`orchestrator/qadam_backtest_completion.py`, strategy version registry and graph
outcome learning. Reuse these paths rather than add another promotion service.

**Work**

- Verify actual tournament/frontier candidate and cohort consumption, including
  the previously empty-input path. Retain working implementations. Builders must
  preserve durable candidates across idle generations and must not recreate
  default policy over approved policy.
- Give discovery candidates a real forward evaluation route even when there is
  no historical survivor. Keep historical validation separate; sufficient genuine
  forward evidence may support a reviewed forward-only promotion route without
  inventing a retrospective backtest or changing the frozen proof standard.
- Freeze evaluated strategy versions, cost assumptions and comparator rules.
  Compare incumbent, challenger, cash and simple benchmark on matched observations;
  capital-allocation effects are separated from signal quality.
- For a new parameter or gate comparison, record a prospective assignment rule
  before outcomes arrive. Use matched shadow comparisons or budget-equivalent
  paper cohorts where feasible. Correct for changes in market regime, notional
  and opportunity selection; a later profitable week is not by itself evidence
  that the newer software or model caused the improvement.
- Promotion decisions use uncertainty, sample dependence, regime concentration,
  adverse tails, turnover and net outcomes. Small fixed counts such as five wins
  are not sufficient by themselves. Set evidence requirements before the trial.
- Apply approved version/size changes atomically inside the parent paper mandate,
  with cooldown, a limited step and immediate downgrade conditions. Novel order
  types, new spending or wider risk require separate approval.
- Evaluate AI and quantum contributions through matched ablations on the same
  observations, folds, costs and decision deadlines. Report hardware execution,
  predictive contribution and economic contribution separately. Keep a method
  only when its information or cost benefit justifies it; never add a quantum
  confidence bonus simply because hardware ran.
- Bound model research budgets, repetitions and context size. Failed ideas carry
  forward their evidence, not an instruction to optimise until the curve improves.
- Operate a champion/challenger registry for each supported core family. Freeze
  the deployed version and its evaluation contract; refresh current evidence
  without resetting its version. Only a material rule/parameter change produces
  a challenger. No weekly rewrite or fine-tune is required to demonstrate work.
- Preregister a family-appropriate minimum effective sample, uncertainty method,
  net improvement threshold, adverse-tail constraints and review dates. Use
  exploratory evidence to propose a comparison, not to certify the same comparison.
  Publish false-discovery controls and regime coverage for all tried versions.
- Publish explicit continue, promote, reduce, retire and insufficient-evidence
  decisions. Auto-deployment is limited to preapproved parameter/size ranges and
  schemas; model-generated code or a novel mechanism remains a reviewed proposal.
  A decline in performance triggers bounded downgrade inside the mandate, not
  an automatic search until one retrospective variant looks profitable.
- A cost-aware allocator may prefer a simple classical strategy or cash. Keep
  local, frontier and quantum components only where matched evidence justifies
  their incremental benefit; a provider outage must not be solved by inventing
  an equivalent consultation result.

**Acceptance**

- A qualified discovery cohort enters evaluation with zero historical survivors.
- A sufficient held-out/forward candidate can progress under its approved route;
  an inadequate or negative cohort cannot. Empty input is legitimate only when
  there are actually no eligible records.
- Selection and promotion replay deterministically from the stored inputs.
- The next decision consumes the approved version; a promotion file unused by
  the executor does not count as completion.
- Quantum or model outages do not block unrelated classical strategies unless an
  explicit binding consultation policy requires a hold.
- A revised source packet updates the current opportunity but cannot rewrite a
  frozen trial's inputs, benchmark, assignment rule or evaluation date. Promotion
  and rollback are traceable to actual observations consumed by the next decision.

**Rollback/containment:** revert to a still-authorised incumbent or no new entries
when a challenger fails. Preserve its negative results and all open exit plans.
Do not increase risk merely because no strategy currently merits promotion.

### P9. Complete Recovery Coverage And Bound Operating Cost

**Owner:** reliability/resource workstream. **Primary code:**
`orchestrator/qadam_self_healing_supervisor.py`, operator, service contracts,
reliability watchdog/critic, source capability registry,
`orchestrator/storage/telemetry_retention.py`, recovery backup and
`orchestrator/research/economics.py`.

**Work**

- Extend one shared incident registry to Python, local Gemma, frontier Gemini,
  required quantum consultation, providers, strategy conversion, risk, execution,
  exits, attribution, publication and disk/database services.
- Monitor completed work and queue progress, not merely process presence or
  successful artifact regeneration. Critical runtime detection is frequent; the
  requested three-hour Telegram summary is not the repair scheduler.
- Give each recognised transient defect a bounded, idempotent handler with
  prerequisites, postconditions, backoff, cooldown and escalation. Quarantine the
  narrowest affected source/strategy; unknown defects are not auto-edited away.
- Use one typed fault catalogue across the worker, circuit breaker, repair queue,
  watchdog and Telegram. Separate dependency-held, legitimately idle, transient,
  code/schema defect, resource pressure, credentials/payment and manual/risk hold.
  A downstream `execution_frozen` result is not automatically another code defect.
- Give each circuit a causal incident reference, next permitted action and durable
  retry state. A verified dependency recovery may trigger a scoped half-open real
  work probe; it must not require an already healthy entry worker. Failed probes
  consume bounded budgets; a restart cannot erase the budget or failure history.
- For the four current circuits, define individual closure proof: guarded
  PaperOps completes an authorised current pass; care verifies due obligations;
  lifecycle polling consumes fresh broker events into canonical state; power
  research resumes a checkpoint and passes its consumer checks. Empty eligible
  work is allowed only with a current, evidenced no-action reason.
- Keep original failure and latest successful work receipts alongside the latest
  scheduler receipt. Repeated `skipped` receipts must not erase diagnosis, count as
  successful work or postpone the incident age indefinitely.
- Add dependency/capability tests to deployment CI: every critical detected fault
  must have a reachable repair or explicit escalation path while the dependent
  consumer is stopped. No cyclic recovery prerequisites or status-only handlers.
- Verify the frontier-account hold remains across restart, key changes and model-
  list success. Handle 402/suspension without billable retry storms. Other
  providers get per-provider timeouts, total attempt budgets, jitter/backoff and
  a request cache; nested retry layers share one budget. No fallback purchase,
  cross-app key use or automatic paid model substitution.
- Give recovery and exits reserved CPU/I/O/API capacity. Long historical scans
  cannot starve broker truth or execution deadlines on the laptop.
- Set tested free-space watermarks, per-job byte budgets, incremental checkpoints,
  log caps and retention. Preserve irreplaceable evidence and verified backups;
  do not repeat full-history materialisation on every refresh.
- Measure and bound batch size, memory, elapsed time and write volume. Incremental
  source ingestion and outcome updates must be restartable. Indexed queries and
  bounded projections replace repeated full-history scans; keep SQLite durability
  and test WAL/checkpoint/backup contention rather than disable safeguards.
- Maintain a bounded cost ledger with provider receipts, currency/conversion
  basis, period, actual versus estimated costs and reconciliation state. Missing
  receipts remain unknown. Attribute input/output/context-cache costs to the
  source/model job and strategy study where evidence permits. Compare operating
  expense to research contribution without treating simulated P&L as revenue.
- Compare optional provider/model components against a matched cheaper or absent
  component. Recommend cancellation or budget changes when evidence warrants it;
  do not cancel services or change approved paid budgets autonomously.
- Verify launchd startup, sleep/wake/network recovery and version binding. For
  off-host outage detection, propose a separate read-only heartbeat checker with
  no broker credentials. A laptop cannot report its own power loss while offline;
  hosting/spend changes require approval and are not prerequisites disguised as
  completed local work.
- Define the hosting promise explicitly. Local unattended operation requires the
  Mac awake, connected and the required runtime available. For a genuine 24/7
  service objective, prepare an approved always-on host/backup/off-host monitor
  cutover before claiming it. Transfer the sole writer by drained, reconciled
  handoff; never use two active hosts against one account as failover.

**Repair handler contract**

Each handler declares the typed fault and scope it can repair, policy/build
requirements, permitted effects, a durable attempt budget/deadline, idempotency
key, verification query, consumer-level success criterion and escalation route.
The incident remains open until verification succeeds. Verification failure
retains the original cause and adds the new failure; it does not write a green
health file. Unknown code defects produce a reproducible incident bundle for
reviewed engineering, not an unrestricted agent editing production.

**Proposed service objectives, subject to measured feasibility**

| Event | Objective | Failure treatment |
| --- | --- | --- |
| Critical execution/exit heartbeat loss during relevant sessions | Detect within 2 minutes | Freeze affected entries; preserve supported protection and alert |
| Accepted executable handoff with no progress | Classify within 2 minutes or earlier strategy expiry | Diagnose stale contract, unavailable broker, expiry or duplicate; never blind retry |
| Known transient fault after its dependency recovers | Verify repair within 5 minutes | Escalate after the bounded attempt budget; do not report repaired |
| Critical operator action required | Queue notification immediately; attempt within 2 minutes when transport works | Durable outbox and delivery-failure state |
| Critical incident remains unresolved or delivery is unconfirmed | Escalate on a bounded schedule with incident age and required action | Coalesce duplicates but never suppress a prolonged failure forever |
| Market closed, optional source stale or legitimate no-setup day | Explain on the normal reporting cadence | Do not open a global incident merely to create activity |

**Acceptance**

- A coverage matrix maps each monitored defect to detection, repair, verification,
  failure isolation and an escalation test. Unknown/unrepairable states are honest.
- Local model hang, frontier quota exhaustion, provider timeout/schema drift,
  storage pressure and process death are tested independently and in combination.
- A successful refresh that leaves the consumer blocked is not counted as healed.
- Fault-recovery and disk budgets pass a sustained-load test; all time targets
  report observed distributions and misses, not just configured intervals.
- A failed handler, exhausted budget, unavailable host or unresolved critical
  incident leaves sign-off blocked. Intentionally held optional providers are
  visibly held, not falsely green and not a reason to disable independent trading.

**Rollback/containment:** a faulty handler is disabled by version/scope; the
affected safety hold stays active. Recovery cannot broaden its own permissions,
erase incidents or deploy arbitrary repairs to keep the dashboard green.

### P10. Make Dashboard And Telegram Reflect One Truth

**Owner:** presentation/notification workstream. **Primary code:**
`orchestrator/presentation/operating_picture.py`, `generations.py`, dashboard and
trading-activity projections, `orchestrator/execution/incident_alert.py`, and the
existing Telegram learning, trade-delivery and health-summary paths.

**Work**

- Preserve the existing navigation, visual language and consolidated Portfolio
  Holdings view. Add concise status and attribution in existing components.
- Show broker observation time separately from page generation time. Show all
  current holdings and exited instruments without treating submissions as fills.
- Report actual account NAV, adjusted analytical performance and benchmark values
  distinctly. Label return windows, deployed capital and strategy contributions.
- Show opportunity funnel counts by distinct event/decision, allocation limits,
  unresolved primary blockers, trade/exit reasons and cohort maturity.
- Separate operational health, execution readiness, learning completeness and
  economic evidence. No average stage score may hide a frozen executor or missing
  attribution. Historical unassigned trades remain visible but not promotable.
- Keep twice-daily learning messages and three-hour health summaries on the user's
  existing schedule. Include changed evidence, actual activity and quantum status
  without repeating old findings as new learning. Critical incidents use the same
  durable notification channel with coalescing, not a competing bot scheduler.
- Use a durable outbox associated transactionally with the canonical event where
  feasible. Store event/incident generation, destination reference, attempt state
  and Telegram receipt. Deduplicate repeated observations of one incident while
  distinguishing its recovery and a genuinely new recurrence of the same cause.
  Reason-text-only deduplication must not suppress later incidents forever.
- Classify ambiguous notification delivery honestly and retry/coalesce within its
  transport budget; do not promise exactly-once Telegram delivery. Message retry
  can never replay an order or cause another broker side effect.
- For interesting patterns, report only material new evidence with provenance,
  direction/horizon, uncertainty and changed strategy implications. The daily
  strategy explanation distinguishes the incumbent from challengers, held or
  expired setups and actual fills; repeating a score is not new research.
- Verify Telegram's currency, epoch and broker event identity. A send is confirmed
  by its receipt; dashboard and Telegram receive the same canonical generation.
- Update the whitepaper and user guide to describe actual authority, uncertainty,
  recovery limits, paper limitations and the two lanes. Remove obsolete conflicting
  doctrine only through a reviewed documentation change.

**Acceptance**

- Desktop/mobile views retain the established UX and match canonical holdings,
  NAV, fills and health. Public routes expose no secrets or mutable authority.
- Telegram distinguishes submitted, filled, closed and rejected activity and
  links it to the same account facts the dashboard displays.
- A stale projection or failed notification is visible; neither fabricates a
  newer broker timestamp nor blocks otherwise safe execution.
- Across dashboard, Telegram and operator CLI, the same canonical generation
  reports the same entry hold and open holdings. Individual dimensions retain
  their own observation timestamps; a fresh page must not refresh stale facts.
- The recurring failure scenario produces a critical alert before the next
  three-hour summary when transport is available, and a verified recovery notice
  only after the actual consumer and incident-release predicates pass.

**Rollback/containment:** fall back to a clearly timestamped read-only view or
degraded status. Public publishing and delivery failure cannot grant execution
authority, hide the canonical incident or misstate submitted orders as holdings.

### P11. Release, Observe And Evaluate Honestly

**Owner:** release/assurance workstream; operator approval is required for mandate,
hosting, paid-service and authority changes outside the existing delegation.

**Work**

- Create tested migrations and immutable release manifests containing code,
  dependency, schema, policy, model/prompt and strategy-version identifiers.
- Reuse existing preflight, deployment and safe operator-restart tooling after
  inspecting it. Test from a clean isolated runtime/worktree; never deploy an
  unreviewed dirty mixture or run two live writers during comparison.
- Roll out read-only projections and shadow decisions first. Paper activation
  requires the full selected dependency chain, including exits and outcome capture.
- Publish a release-specific activation checklist: current reconciliation, no
  relevant unresolved hard holds, correct account/epoch and owner, known entry
  lineage, exit coverage, compatible contracts, risk headroom and notification
  path verification. Existing certification policy remains binding; if it prevents
  a necessary bounded canary, obtain an explicit reviewed canary amendment rather
  than silently bypass it or claim simulated sessions as observations.
- Deploy the exact tested SHA locally and to the public dashboard as applicable.
  Verify served assets/data and launchd's actual build, not merely a deploy exit
  code. Keep the one existing canonical PaperOps entry point.
- Roll back application changes only when schema compatibility is verified. After
  any broker activity, never restore an old database over newer orders/fills.
  Use compatible forward repairs and reconcile current broker truth first.
- First meet the existing 24-hour healthy-watchdog target under measured load,
  then demonstrate five distinct real US sessions for release reliability. Run
  a preregistered 20-session active-discovery evaluation for conversion and early
  economics, with an explicit start manifest. Runtime and scientific observation
  can overlap where their contracts allow; no session receives retrospective
  proof credit and 20 sessions do not automatically prove a durable edge.
  Existing legacy seven-real-date/session observation records remain separately
  visible where their contracts still apply; this plan does not shorten those
  gates or turn them into the five-session release check.
- Preserve strategy evidence across non-economic software changes with explicit
  lineage. Material strategy changes start a new evaluation version. Never
  silently reuse old evidence or reset every scientific clock for a CSS edit.
- Define which changes invalidate which proof: execution/lease/incident changes
  restart the affected reliability observation; strategy/feature/threshold changes
  start a new economic version; visual-only changes do neither unless their
  interface contract changes. Retain prior evidence with its actual release scope.
- Exercise recoveries in an isolated fault environment and verify the repaired
  production path with read-only/current receipts. Never inject destructive
  outages into the live paper account just to produce a certification result.

**Acceptance**

- Installed and served releases match the tested manifests; every schema/contract
  migration and rollback/recovery rehearsal has retained evidence.
- No unexplained canonical freeze, critical repair, missed care obligation or
  stale broker reconciliation remains. All four current circuits are resolved
  through verified work or explicitly isolated with demonstrated noncritical
  scope; a code-defect circuit is not closed by changing its label.
- Five real sessions demonstrate execution/exit liveness, recovery and truthful
  reporting. Zero naturally eligible signals means the positive paper execution
  path remains unobserved, not falsely certified and not forcibly exercised.
- Naturally eligible entries and exits complete end to end when they occur. No
  duplicate writes, unexplained allocations, new unassigned outcomes, silent
  critical stalls or unsupported health claims are tolerated as a pass.
- The 20-session report compares useful opportunities, independent completed
  experiments, deployed capital, turnover, cost-adjusted returns, drawdown,
  benchmark excess and human interventions against the frozen baseline.
- If conversion improves but economics do not, report that result and constrain
  allocation. If opportunity supply is inadequate, revise the research programme
  as a new experiment; do not lower gates repeatedly until trading appears.

**Release report:** distinguish `implemented/tested`, `deployed`, `runtime
verified`, `24-hour observation`, `five-session observation` and `economic
evaluation`. Include every unobserved positive path and external dependency.
Do not report the whole plan finished while a real-time milestone is pending.

**Rollback/containment:** retain the last compatible known-good application
manifest, reconcile before/after cutover, and prefer forward fixes when broker
events or schema changes make rollback unsafe. No database rewind over trades.

## 7. Fault And Acceptance Test Matrix

| Test | Required result | Phase |
| --- | --- | --- |
| Real SOXX post-entry failure, then the two later passed reconciliations | Original allocation cause retained; reviewed typed recovery can progress; old generic reason alone cannot authorise release | P0/P1 |
| Old successful reconciliation or two regenerated copies of one broker read | No recovery/freshness credit | P1 |
| Pending canonical allocation converges versus unexplained position persists | Exact known lifecycle can settle within a deadline; unknown quantity stays held | P1/P2 |
| Mirror timeout followed by recovery | Broker-verified cause-specific unfreeze; no order retry | P1 |
| New failure arrives during old repair | Older repair cannot clear newer incident | P1 |
| Manual/risk hold alongside provider failure | Provider recovery preserves unrelated hold | P1 |
| Entry circuit open while lifecycle and recovery are due | Read-only broker polling and reconciliation still complete through authorised paths | P1/P9 |
| Dependency hold is repeatedly returned by a stopped entry worker | Causal dependency state, not a fabricated new code defect or healthy skip | P1/P9 |
| Broker accepts order, client loses response | Lookup resolves one order by stable identity | P1/P7 |
| Lease expires or process dies during a slow submission/readback | No unfenced second writer; result remains ambiguous until exact broker lookup | P1/P7 |
| Restart after any decision/outbox/fill boundary | Deterministic replay without duplicate effects | P1/P2 |
| Two versions trade the same symbol | Exact lot/decision attribution, independent of arrival order | P2 |
| Provider revises an old fill, timestamp or financial value | Versioned correction; decision-time snapshot and original event remain intact | P2/P3/P4 |
| A short holding raises available cash | Signed market value, equity and P&L reconcile; cash is not all profit | P2/P10 |
| Missing P&L, benchmark or lineage | Unknown/ineligible for relevant evaluation, not zero or fabricated | P2/P3 |
| Identical event across assets or reruns | Independent observation count does not inflate | P3 |
| New evidence versus same payload refetch | Only material new evidence changes the hypothesis | P4 |
| An alias, syndicated article or aggregate feed repeats the same source | Provenance retained without independent-confirmation credit | P3/P4 |
| Retrieval succeeds but publication time cannot be verified | Forward-only/limited-use label, not fabricated historical availability | P4 |
| Producer schema changes or mandatory field is renamed | Consumer/contract tests fail before release; runtime defers precisely | P4/P5 |
| Valid discovery hypothesis has no historical edge | Can reach bounded paper review under its approved contract | P5 |
| Invalid quote or adverse known economics with high research score | No automatic override | P5 |
| Discovery admission reaches a retired adapter | No second validated-edge or Akber authority appears downstream | P5 |
| A queued high-score setup expires before the next session | Refresh/re-evaluate current trigger; no stale standing order | P5 |
| Multiple high-correlation small setups | Assess incremental portfolio risk without ignoring shared exposure | P6 |
| Slot increase, simultaneous fills, gap shock | Approved aggregate limits and model assumptions remain explicit | P6/P7 |
| Entry partially fills before native bracket protection activates | Exact covered quantity and approved fallback/hold are visible and tested | P7 |
| A due exit occurs with entries frozen and an optional model unavailable | Scoped care runs only if its hold, quantity and owner contracts allow it | P7/P9 |
| Stop/target/cancel/replace events race or arrive out of order | Reconcile actual quantities; no blind retry or oversell | P2/P7 |
| Local model hangs while position is open | Position monitoring continues; no independent broker writer | P7/P9 |
| No historical survivors, sufficient forward discovery evidence | Real tournament consumes records and evaluates correct route | P8 |
| Nightly backtest/projection refresh runs | Cannot erase approved strategies, cohorts or policy | P8 |
| Insufficient/negative challenger evidence or a newly selected lucky variant | No automatic promotion or higher risk; retain rejected variants and selection history | P3/P8 |
| Same strategy evidence is refreshed without a rule change | No version reset, fake novelty or restarted scientific clock | P4/P8 |
| Disk approaches watermark or DB becomes unavailable | Bounded writes, visible degradation, protected evidence | P9 |
| Historical scan saturates CPU/I/O, then the Mac sleeps or loses network | Deadlines/host outage detected; checkpointed recovery; no false uninterrupted-uptime claim | P9 |
| Healer crashes halfway through repair, then restarts | Durable attempt budget and incident state survive; consumer proof still required | P9 |
| Every current circuit is reset without real worker progress | Sign-off fails even if service validators pass | P9/P11 |
| Gemini lists models or a new key works while an account hold exists | Hold survives; no automatic analysis resumption, fallback spend or retry storm | P9 |
| Cost receipt is unavailable or currencies differ | Unknown/estimated costs remain labelled; no fabricated net profitability | P3/P9 |
| Telegram/downstream dashboard unavailable | Queued delivery/stale display; healthy execution not falsely blocked | P10 |
| Telegram response is lost or delivery receipt is not saved | Delivery stays ambiguous/unconfirmed; bounded notification retry never repeats a trade | P10 |
| Same failure recurs after a verified recovery | New incident generation alerts; old deduplication cannot suppress it forever | P9/P10 |
| Health refresh succeeds while canonical execution remains frozen | Dashboard/Telegram/CLI remain visibly entry-held or degraded | P1/P10 |
| Market holiday/weekend/DST transition | No synthetic trading session, matured label or soak credit | P11 |
| Deployment while orders are pending | Stable identities and original exit contracts survive | P11 |
| An old build or compatibility entry point attempts direct broker writes | Ownership/contract checks reject it; release inventory identifies the writer | P0/P11 |

Unit and deterministic integration tests belong in isolated runtimes. Fault
injection must not corrupt the production database, disable real protective
orders, consume paid quantum jobs or create synthetic broker activity.

Extend the existing test suites rather than create a parallel certification silo:

- `tests/test_qadam_operating_ledger.py`
- `tests/test_execution_runtime_contract.py`
- `tests/test_execution_owner_recovery.py`
- `tests/test_execution_lease_keeper.py`
- `tests/test_qadam_entry_contract_recovery.py`
- `tests/test_qadam_control_plane_store.py`
- `tests/test_qadam_control_plane_bridge.py`
- `tests/test_qadam_canonical_paper_control.py`
- `tests/test_paperops_autonomous_pass_summary.py`
- `tests/test_paperops_autonomous_pass_lock.py`
- `tests/test_paperops_alpaca_paper_post_reliability.py`
- `tests/test_qadam_paper_lifecycle_bracket_compatibility.py`
- `tests/test_lean_position_care.py`
- `tests/test_qadam_refactor_attribution.py`
- `tests/test_qadam_refactor_benchmarks.py`
- `tests/test_qadam_migration_replay.py`
- `tests/test_qadam_strategy_foundry_v3.py`
- `tests/test_qadam_core_strategy_continuity.py`
- `tests/test_qadam_decision_evidence_packets.py`
- `tests/test_qadam_source_collection.py`
- `tests/test_qadam_point_in_time_evidence.py`
- `tests/test_qadam_point_in_time_reliability.py`
- `tests/test_qadam_source_evidence_acceptance.py`
- `tests/test_qadam_portfolio_risk_engine.py`
- `tests/test_qadam_layered_market_judgment.py`
- `tests/test_qadam_canonical_exit_engine.py`
- `tests/test_qadam_outcome_learning_promotion.py`
- `tests/test_qadam_backtest_completion.py`
- `tests/test_qadam_operator_service_v2.py`
- `tests/test_qadam_service_receipts.py`
- `tests/test_qadam_bounded_recovery.py`
- `tests/test_qadam_reliability_watchdog.py`
- `tests/test_qadam_storage_retention.py`
- `tests/test_provider_account_hold.py`
- `tests/test_qadam_operating_picture.py`
- `tests/test_qadam_trade_delivery.py`
- `tests/test_qadam_research_economics.py`
- `tests/test_qadam_component_studies.py`
- `tests/test_daily_telegram_learning_brief.py`

Add missing coverage in the owning suite. Passing fixtures does not certify
provider access or the installed service; real verification remains separate.

**Verification commands after implementation, not executed by this plan**

Run from the exact reviewed release checkout, after confirming the runner still
isolates runtime paths and network access:

```sh
.venv/bin/python scripts/verify_isolated_python_tests.py -q \
  tests/test_qadam_operating_ledger.py \
  tests/test_execution_runtime_contract.py \
  tests/test_execution_owner_recovery.py \
  tests/test_paperops_alpaca_paper_post_reliability.py \
  tests/test_lean_position_care.py \
  tests/test_qadam_paper_lifecycle_bracket_compatibility.py \
  tests/test_qadam_operator_service_v2.py \
  tests/test_qadam_bounded_recovery.py \
  tests/test_qadam_operating_picture.py \
  tests/test_qadam_trade_delivery.py
.venv/bin/python scripts/verify_isolated_python_tests.py -q tests
git diff --check
```

Add the new incident regressions to these owning suites before relying on this
command set. Use the existing project lint command over changed Python files,
and run migration/restore/replay verification against isolated copies. Offline
success provides no live API, broker, notification or deployment proof. After
activation, collect current canonical read-only health, broker observation and
completed service/delivery receipts through reviewed tooling; do not run a submit
command merely because it was once used as a diagnostic.

For this documentation revision, no implementation tests or real-session gates
have been declared passed.

## 8. Release Batches And Stop Conditions

| Batch | Content | Allowed claim |
| --- | --- | --- |
| A: Recover operation | P0/P1, immediate P9/P10 incident/recovery truth, and verification of existing position protections | Known fault recovery and truthful reporting; new entries remain subject to P2/P7 acceptance and existing authority |
| B: Trustworthy learning | P2/P3/P7 plus read-only reporting changes | Exact attribution and verified lifecycle protection; no retroactive edge claim |
| C: More useful experiments | P4/P5/P6/P7/P8 after policy review and P9 safety coverage | Bounded autonomous discovery/allocation enabled on the exact build |
| D: Complete observation | P9/P10/P11 integration, deployment and real-session evidence | Precisely scoped operational/economic conclusions, with unobserved items pending |

Batch A does not bypass P2/P7 acceptance for new entry activation on the repaired
release. Recovery may verify the broker and repair projections while entries
remain held. Existing-position protection continues only through its reviewed
canonical route. Batch C's new mandate must not be activated by a Batch A repair.
Develop and verify P7 immediately after P1/P2; its numerical position in the plan
is not an instruction to leave positions unprotected until strategy research is
finished. Likewise, the P9 incident/recovery core is part of Batch A, not a final
optional self-healing add-on.

### 8.1 Concrete Implementation Tickets

Maintain these tickets in the existing implementation tracker, with links to
code, failing-before/passing-after tests and dated runtime evidence. A ticket
already satisfied by the refactor is closed with proof, not rewritten.

| Ticket | Required artifact or change | Completion proof |
| --- | --- | --- |
| R0: Capture | Exact build/policy/runtime manifest, original circuit receipts and isolated replay fixtures | Restored backup and read-only baseline; unknowns explicit |
| R1: Preserve cause | Structured post-entry failure and original reconciliation/order references | SOXX replay retains `position_entry_allocation_unresolved` |
| R2: Resolve safely | Typed incident contracts, receipt-backed legacy mapping and transactional scoped release | Fresh readback clears only its own reviewed incident; unsafe/manual holds survive |
| R3: Break the deadlock | Recovery/lifecycle route independent of entry availability, one fenced write owner | Recovery and permitted care progress with entry circuit open |
| R4: Repair the circuits | Individual diagnosis and bounded real-work revalidation for all four current services | Current consumer receipts, not reset counters or skipped validators |
| R5: Protect and account | Exact order/fill/allocation lineage, exit coverage and correction replay | Partial-fill/race tests and canonical broker/account reconciliation |
| R6: Contract the funnel | Producer/consumer evidence schema, gate register and queue expiry | Valid discovery packet traverses the real canonical path without invented fields |
| R7: Measure and allocate | Frozen cohorts, benchmarks, approved champion/challenger rules and one allocation ladder | Deterministic comparisons and demonstrably consumed policy versions |
| R8: Sustain and report | Resource/API budgets, verified repair handlers, shared operating picture and durable delivery | Fault/load tests plus real alert/recovery/delivery receipts |
| R9: Release and observe | Exact-build deployment, public parity, 24-hour/five-session/20-session records | Claims limited to completed technical and real-time evidence |

The immediate release priority is R0-R5 plus critical health/delivery truth from
R8. Do not delay the current execution repair while adding new research features,
and do not call R6-R9 complete merely because R1-R3 make a single pass succeed.

Stop the affected rollout for unexplained broker differences, duplicate write
risk, accounting mismatch, unsupported attribution, failed exit protection or
policy drift. Preserve known-safe management of existing positions and isolate
research faults; do not equate a stop in new entries with a mandatory liquidation.

Never mark the entire plan complete just because a token budget, market session
or implementation turn ends. Report implemented, deployed, observed and pending
items independently. Waiting for real evidence is not permission to fabricate it.

### 8.2 Release Quality And Legacy Retirement

- Run focused incident/contract tests, the existing isolated full test runner,
  changed-code lint, schema migration/restore checks, import boundaries and replay
  tests from the exact release checkout. Record actual commands and results.
- Use structural checks and reviewed call-site inventory to ensure broker writes
  remain in the canonical owner; compatibility modules cannot acquire hidden
  direct HTTP, SDK or alternative-account authority.
- Remove a legacy writer only after consumers use the canonical contract and
  replay parity is verified. Preserve historical evidence and necessary read
  adapters; do not delete broad modules because their names sound obsolete.
- Set one canonical document hierarchy. Old plans and static status blocks are
  historical unless their generation and timestamps match current authoritative
  evidence. A September sign-off cannot override an October execution freeze.
- Keep credentials backend-only, redact release evidence and logs, and verify
  public dashboard payloads expose no secrets, private account IDs or controls.
  Do not rotate/delete keys or modify other applications as part of this plan.

## 9. Weekly Operating Mandate

The autonomous schedule consumes material new evidence promptly, evaluates
current setups during their genuine execution windows, manages open positions,
matures labels on their real horizons and performs incremental learning. Weekly
reviews compare frozen versions; deeper governance reviews follow the existing
monthly cadence. Do not rerun all historical data every few minutes.

The weekly report includes:

- Broker NAV change and realised/unrealised contributions, with cash flows and
  analytical costs separate from investment returns.
- Return on total equity and deployed capital, exposure/time in market, drawdown,
  matched benchmark excess and the uncertainty of strategy results.
- Distinct observed events, complete hypotheses, eligible decisions, accepted
  handoffs, filled entries, exits and independent completed experiments.
- Primary reasons opportunities stopped, deadline misses and incidents, including
  whether any eligible paper action was lost to a software or provider defect.
- Strategy allocations increased/decreased/retired, their evidence and version;
  no weekly parameter change is mandatory when evidence is unchanged.
- Cost and attributable contribution of sources, local AI, frontier AI and quantum;
  prospective live break-even after subscriptions is separate from simulated P&L.
- Unresolved access, provider, hardware or research limits requiring human action.

### 9.1 Quantitative Scorecard

Freeze metric definitions and the pre-repair comparison window before judging
the release. Reconcile numerator/denominator identities; do not compare raw
counts from unrelated epochs or different market-session lengths.

| Dimension | Measures | Sign-off or interpretation |
| --- | --- | --- |
| Execution reliability | Fresh reconciliation coverage, completed care obligations, eligible-handoff age, critical stalls, unexplained broker differences, duplicate broker effects | No unexplained hard failure in the signed-off interval; publish every miss and observation scope |
| Recovery | Time to detect, dependency recovery, verified consumer recovery, failed attempts, manual interventions | Meet measured P9 objectives for recognised faults; unresolved/unknown faults remain explicit |
| Evidence | Fresh usable sources versus aliases/held/unconfigured feeds, verified timestamps, material events, feature coverage | Usable programme coverage, not a cosmetic all-41 green score |
| Conversion | Distinct complete hypotheses -> eligible decisions -> accepted handoffs -> submitted orders -> fills -> matured outcomes | Every stop/expiry attributable; lost eligible actions due to code are defects, not no-edge days |
| Frequency/capacity | Independent entries, exits, slot occupancy, hold duration, cluster concentration, turnover | Increase useful experiments when feasible, never duplicate entries or churn for a quota |
| Investment results | Broker return, analytical cost-adjusted return, benchmark excess, drawdown, tail loss, exposure/time at risk | Matched independent cohorts and uncertainty; paper profit does not establish live profitability |
| Learning | Mature independent outcomes, evaluable versions, changed decisions, challenger/ablation results | Credit applied, evidenced changes; no improvement claim from a model response or an updated file |
| Economics | Actual/estimated/unknown provider costs, incremental component value, human intervention burden | Maintain an affordable research mandate; simulated gains do not fund subscriptions |
| Reporting | Event-to-notification delay, acknowledged/unconfirmed delivery, projection lag and generation parity | No silent critical stall or stale fact labelled fresh |

At each relevant market-session close, every setup considered that session must
have a traceable state: not yet triggered, incomplete, expired, deferred with a
next action, rejected with its primary reason, allocated, submitted, filled or
closed. A session with no trades can be economically valid; a session with an
unexplained stalled eligible setup cannot be operationally green.

Aim for a higher rate of useful independent experiments when evidence and capacity
permit, potentially averaging at least one entry per eligible session. Freeze a
feasibility target only after P4/P6 measure actual supply. It is not a quota, a
reason to close good positions early or a guarantee of profitable weekly returns.

## 10. Completion Evidence And External Limits

Final delivery must include the exact deployed release IDs; migration and
restoration evidence; isolated test results; incident replay results; broker
reconciliation; all new-trade attribution and exit coverage; public dashboard
parity; notification verification; open risks; and separate real-session and
economic evaluation counters. Technical completion cannot be labelled a proven
money-making machine.

### 10.1 Unattended Sign-Off Checklist

Sign-off is for a named build, mandate, host and observation window, not an
indefinite guarantee. All applicable items must have linked evidence:

- One actual broker-write owner, correct paper endpoint/account/epoch and no
  undeclared legacy authority; no new live-capital permission.
- Current canonical broker reconciliation, no unresolved relevant hard hold,
  exact pending/open exposure and verified exit obligations.
- The October 23 recurrence class passes its replay, safe recovery and race tests;
  each present circuit and repair has a verified disposition.
- Completed work is fresh at the service-specific cadence; no status-only green
  receipts, overdue accepted handoffs or unreported critical failures.
- A valid discovery route and a validated route obey the same canonical safety
  contract with their different evidence/size rules. Lack of validated strategies
  is reported honestly and does not invent one for the checklist.
- Frozen strategy versions, usable source/timestamp provenance, exact outcomes,
  benchmarks and resource/cost limits reach their actual consumers.
- Telegram and dashboard match canonical events and freshness; critical detection,
  durable delivery and verified recovery notices have retained evidence.
- The installed and served build matches the tested manifest, backup/restore and
  compatible rollback are rehearsed, and host/sleep/network assumptions are stated.
- The 24-hour and five-real-session reliability evidence is completed, or sign-off
  remains explicitly provisional. Naturally eligible execution paths not yet seen
  remain unobserved rather than silently passed.
- The 20-session report and any subsequent strategy-specific evidence thresholds
  remain separate from reliability sign-off. Negative economics leads to smaller
  allocation, a revised frozen trial or retirement, not a promise of more profit.

### 10.2 Ongoing Assurance After Sign-Off

The watchdog continues to revoke current readiness when a critical predicate
fails; certification is not a permanent green badge. Recovery handlers continue
within their tested budgets, and material changes re-open only the affected
verification obligations. Keep scheduled backup restore tests, dependency
maintenance and periodic access/risk reviews under the existing approved
maintenance mandate. Novel repairs, revoked access and host failures may still
require human intervention.

The practical autonomy contract is: detect known problems, recover within tested
bounds, isolate what cannot safely recover, protect authorised positions as far
as the available broker/host permits, and communicate unresolved conditions.
Provider outages, laptop power loss, hardware failure and market losses remain
possible. A self-healer cannot guarantee continuous service or profit.

Alpaca describes its paper environment as simulated and lists differences such as
missing market impact, latency slippage, queue position, regulatory fees and
dividends. Use a separately labelled analytical adjustment layer and test fill
capacity; do not treat paper execution as a live-money guarantee. [Alpaca paper
trading documentation](https://docs.alpaca.markets/us/docs/paper-trading)

Searching many strategies and repeatedly selecting the best backtest creates
selection risk. Keep attempted variants and untouched evaluation evidence, and
use dependence-aware validation rather than assuming a good-looking backtest or
one favourable holdout proves an edge. [Bailey, Borwein, Lopez de Prado and Zhu,
The Probability of Backtest Overfitting](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf)

The desired outcome is a dependable autonomous paper research-and-trading
operation that can establish whether it has an investable edge, scale that edge
inside an approved mandate if evidence supports it, and conserve resources if it
does not. This plan does not promise the best possible trades or profit every week.
