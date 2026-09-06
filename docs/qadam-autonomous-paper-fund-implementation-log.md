# Autonomous Paper Fund: Implementation And Verification

Updated: 7 September 2026 (Dubai). This is an engineering record, not a claim of
profitability, a completed market-session soak, or failure-free operation.

## Unified Refactor: R0-R11 Delivery Tracker

Approved plan: `docs/qadam-evidence-to-performance-gap-closure-implementation-plan.md`.
Baseline: `032f48188f7544c95edab5ee560ac78ab06dbc12`.

**The full R0-R11 refactor is NOT complete or deployed.** The independent live
repairs below are released. The remaining refactor is committed on
`codex/unified-refactor-20260906`; its latest implementation code is
`044aa2db7ffed97d32f9dd9dbc5a484a150eb316`. Subsequent tracker-only commits do not
constitute a production release. The older records below this tracker are dated
history, not current all-phase acceptance.

### Released And Observed

Live core: `390a3085a178db96f114b61e1ca9e56962e988ee`, pushed to
`codex/weekend-engine-preservation-20260719`, installed with the maintenance guard
and safe single-owner restart. Production SQLite remains schema 4. Site source
remains `7b33d14d32991494033c7721656cd1687fc064c6`; its four principal served
assets matched that checkout byte-for-byte. No dashboard redesign was deployed.

- Watchdog parses the complete launchd response. Unknown diagnostic state does
  not justify a blind restart; recovery actions have independent cooldowns.
- Execution-context compilation no longer falsely depends on market-hours
  price-refresh work. Each selected job rechecks the actual clock immediately
  before dispatch, including freshness expiry, backoff and market-close changes.
- Provider events enter a durable pending queue before consumption. An event is
  acknowledged only after durable goal creation; crash replay avoids duplicates.
  Unconsumed events are no longer silently discarded by the two-per-source limit.
- The existing 20-goal cycle budget is shared fairly, then unused source shares
  are reassigned to busy queues. This increases useful throughput without raising
  that ceiling or adding provider/model/broker calls.
- Frozen, nonterminal forward experiments keep receiving observations after an
  entry trigger disappears. Provider availability is recorded at response time,
  not request time or an injected operational timestamp.
- The isolated release suite passed 1,074 tests with the same 39 failed identities
  as the unchanged baseline. The latest targeted scheduler/ingestion group passed
  114 tests. This is not a claim that the repository-wide release suite is green.

Actual observations on 6 September UTC:

| Time | Evidence |
|---|---|
| 20:14:35 | Owner request `operator-full-heal:d95655e1f2e57e198c593af2` completed source, shadow, attribution, dashboard and public-publication revalidation without a failed service. |
| 20:48:26 | Source ingestion had 29 pending events before the spare-capacity repair. |
| 20:56:12 | The released repair created 20 research goals and retained nine pending events. |
| 21:12:56 | Operator reported 21/21 fresh services, zero open circuits, zero repair requests, on the committed live build. |
| 21:14:43 | Canonical PaperOps returned `ready_idle`, no blockers, zero duplicate submissions, five open positions and no open orders. This pass submitted no new order. |
| 21:16:03 | Ingestion reported `caught_up`, zero pending events and `provider_replay_required=false`. |
| 21:16:05 | Reliability watchdog passed with no blockers. |

The public bridge's final report-only check passed freshness, publication and
digest parity with zero broker writes. These are dated operational checks, not
a guarantee of future health. The queue repair does not recover events discarded
by older software. Newly received provider data can legitimately create another
bounded backlog.

### Prepared Refactor Verification

- Full suite: **1,213 passed, 15 failed, zero errors, zero skips**. All 15 failures
  are remaining baseline identities; 24 of the original 39 failures are resolved.
  They have not been skipped or waived. All 146 changed Python files pass Ruff.
- Ten old import paths delegate to one implementation across eight packages.
  Installed-package testing outside the checkout passed all ten import identities
  and a real structured terminal-receipt process with a sibling CLI import.
- All 21 scheduled terminal checkers require semantic work receipts. Exit zero
  without verified work is not success. Owner-busy results do not publish stale
  generations, and orphaned child processes cannot retain resource authority.
- Actual SQLite migration replay used a private, read-only-source backup of the
  336 MiB operating ledger. Schema 4 to 5 preserved every pre-existing table row,
  payload and migration receipt; integrity and foreign-key checks passed. No
  production write, broker call, notification or outbox consumer was involved.
- Cohort calculations now run outside the broker write transaction. A concurrent
  outcome change prevents stale publication and preserves the last valid cohort.
  Replay on the isolated real-ledger copy preserved all four cohorts' metrics and
  identities. Summary accounting streams records rather than retaining the
  entire outcome history. Full incremental cohort aggregation remains unfinished.
- The canonical compiler is read-only during calculation; publication consumes
  the exact capability input rather than rebuilding another generation.
- Missing score/label hashes cannot falsely establish quantum/backtest lineage.
  Positive and negative edge-registry tests now use actual builders with isolated,
  explicit result manifests, including invalid hash/count/path tests.
- Latest research-score selection does not resurrect an older peak when the
  newest observation is invalid or ambiguous. Provider/model/prompt-sensitive
  caches and single-flight protection are prepared.
- Modelled paper costs are not presented as observed live execution costs.
  Component economics and immutable expense/correction APIs are prepared, but
  actual bills and canonical paired component-ablation production are not wired.
- The history-read benchmark exercised actual 1x/2x/10x files (10,000, 20,000 and
  100,000 records), five samples each. The 100-row tail used 64 KiB of I/O and
  about 190 KiB of Python allocation at every size, with identical returned rows.
  This is not a whole-application speedup or process-RSS claim.

Installed wheel for implementation code `044aa2db`:
`/tmp/qadam-refactor-package-044aa2db-20260907/qadam-0.1.0-py3-none-any.whl`.
SHA-256: `be5d9b8065cbeada4aebfecfc6fd691336aa500b0cbb77dd84dac3a780556f71`.
Its 479 members contain no runtime database, provider data, tests, secret file or
obsolete `orchestrator/execution.py` module.

### Captured Producer Replays

All comparisons used the same private capture and five samples. The processes
strip inherited authority/credential environment variables, deny credential-file
reads, network/process creation and file mutations, and open the isolated exit
ledger read-only. Frozen time is fixture-only. No replay executed an order.

| Producer | Result |
|---|---|
| Dashboard | Equal equity, holdings/history and lifecycle digest: `34bd4d0c62701467a31f0d0262930c3f8fb7455e32102a60fbda0d0da4da8c14`. |
| Canonical compiler | Equal digest `d59848c690adf8e9dc5f66c0856195bc21415f69ee22f3d4f0bd09a786e16d08`; one draft, one envelope, one rejection, zero validation errors. |
| Strategy builder | Equal digest `c06c65650b1881fa86d4a5a2024e4ddf198d41b11d9a5f21e127993d4bfd544b`; this captured input produced zero hypotheses. It is not positive trade-conversion proof. |
| Exit selection | Equal digest `36d356f3c965f0f83240a2d3f466f305e62d09f1d78c9431b69a64fee89f7b3a`; one due exit candidate with matching quantity and original policy, not a submitted exit. |

All four producer validators reported zero errors. Dynamic call inventories cover
only functions exercised by those captures, not every caller in production.
The last dashboard median was approximately 0.189 seconds on baseline and 0.217
seconds on the refactor. No overall latency improvement is claimed. Remaining
load, resource-budget and live workload acceptance cannot be inferred from small
captured replays.

### Phase Acceptance And Remaining Work

| Phase | Current state / remaining acceptance |
|---|---|
| R0 | Baseline, four real-producer replay types, bounded I/O measurements and exercised call inventories exist. Whole-workload budgets and complete dynamic consumer coverage remain. |
| R1 | The independent diagnostic, dependency, dispatch-clock and ingestion repairs above are live and verified. This is not arbitrary self-healing or indefinite fault tolerance. |
| R2 | Package/contracts/import/receipt tests pass. Final integrated production activation remains gated by R10. |
| R3 | Backup/migration, bounded tail reads, atomic generations and retention concurrency pass. Cohort writer contention is repaired; incremental outcome aggregation and its scaling acceptance remain. |
| R4 | Structured completion, process cleanup, source-generation checks and dispatch-time clock tests pass. Integrated saturation/recovery/progress-deadline acceptance remains. |
| R5 | Durable pending events, fair budget reuse and continued forward observations are live. Material provider corrections, syndicated-event handling, completeness audits and provider-overflow replay integration remain. |
| R6 | Exact lot/cost contracts and real-ledger cohort equivalence pass. Prospective benchmark capture still needs cadence/integration repair: a five-minute observer cannot reliably provide a pre-fill observation within a two-minute matching window. Do not backdate observations or relax evidence truth to hide that gap. |
| R7 | The actual canonical compiler replay matches, and single-owner/Q-CTRL/exit/risk contracts are retained. Final integrated positive conversion, restart and submission acceptance remains. |
| R8 | Financial projection parity, atomic read models and current deployed asset identity pass. Final desktop/mobile visual verification was not completed: browser automation timed out. New economics fields are not yet rendered in the frontend. |
| R9 | Read-only economics, unknown-cost semantics and expense APIs exist. Canonical preregistered paired ablations, actual bill reconciliation and complete user-facing reporting remain. No automatic spend/risk expansion is authorized. |
| R10 | Not accepted: 15 remaining historical/certification failures, full legacy writer/caller retirement and integrated load checks remain. Legacy QBC negative-probe rows still contain unconditional pass labels and must be replaced with actual probes or explicitly retired, not counted as evidence. |
| R11 | Broad refactor NOT deployed. Only the independent repairs are live. After engineering acceptance/cutover, five distinct real US sessions and the prospective 20-session economic review are still required. These are not the only outstanding tasks. |

The 15 failing checks comprise six backtest-completion checks, four learning-gap
checks, one operator-readiness negative-safety snapshot, one hardware-public-view
snapshot, one default portfolio graph check and two QSASE end-to-end checks.
Several depend on missing untracked historical/runtime artifacts. They still
require reproducible positive/negative inputs and appropriate retirement decisions;
being pre-existing is not release acceptance.

Primary private reports:
`/tmp/qadam-refactor-final-continuation-20260907.xml`,
`/tmp/qadam-ingestion-capacity-release-20260907.xml`,
`/tmp/qadam-refactor-actual-migration-20260907.json`,
`/tmp/qadam-refactor-history-load-20260907.json`, and the paired
`/tmp/qadam-{dashboard,canonical,foundry,exit}-{baseline,refactor}-replay-20260907.json`
reports. Temporary reports are local engineering evidence; committed code/tests
and this tracker are retained in the refactor branch.

The paper-only account, existing exits, USD 250 notional / USD 5 planned-stop-risk
micro bound, USD 5,000 parent ceiling, slot/cluster limits and Q-CTRL holds are
unchanged. No paid model/QPU job, forced trade, risk expansion or real-capital
permission was used as a verification shortcut.

## Historical Release Contents

| Plan | Implementation in this release | Verification / remaining evidence |
|---|---|---|
| P0 | Isolated baseline checkout, SQLite backup through the backup API, integrity and foreign-key checks, real broker read | Baseline: 961 passing tests, 39 pre-existing failures. Production database was not replaced. |
| P1 | Cause-specific mirror recovery, two distinct fresh observations, preservation of unrelated freezes, typed database/maintenance failures, canonical health in team and dashboard | Timeout, stale-read, manual-hold and incident recovery tests. Production recovery must be verified after installation. |
| P2 | Account/epoch FIFO entry allocation, exact decision linkage, corrected position-to-original-exit association, idempotent cumulative-fill projection | Real-history replay twice: 68 filled orders / 68 cumulative fill projections; five original position exit plans reconciled. Unresolved history stays unknown. |
| P3 | Stable strategy versions, event-level cohorts, unknown-cost exclusion, immutable corrections and registered forward evaluations | 31 historical outcomes: 30 gross reconstructions, five exact decision attributions, 26 unresolved attributions, zero measured-cost outcomes. These are not net strategy profit. |
| P4 | Reuse the existing capability registry, numeric/qualitative trigger producers, typed evidence packets and proxy contracts; bind hypotheses to stable definitions | No new provider entitlement is claimed. Existing real-packet checks must be run against the release; unavailable history and unsupported proxies remain research-only. |
| P5 | Explicit unknown-expectancy discovery contract across foundry, Akber, layered judgment, risk and Router; remove discounted winner-selected return from discovery-micro | Full typed positive/negative path tests. Maximum $250 notional / $5 planned loss at the stop. Known-negative economics cannot use this route. Untouched forward comparison remains pending. |
| P6 | Budget-neutral three-versus-six-slot comparison in risk output; preserve current slot, aggregate, cluster and $5,000 absolute limits | Six slots are not activated by this release. Prospective supply, turnover and risk comparison must precede that amendment. |
| P7 | Original durable exits, provider exchange calendar, terminal partial-exit retry identities, unresolved-order no-retry protection, quantity-bounded close requests | Cancel/partial/ambiguous/repeated-submission tests. Price protection continues without inventing a holiday/session. Broker-hosted stop protection is not claimed. |
| P8 | Learner-owned real tournament, non-overlapping version-matched shadow outcomes, matched SPY/cost comparison, scheduled multiplicity-adjusted review, exact-version foundry consumer | Historical backtest refresh can no longer erase the tournament. No historical survivor is required for emerging forward review. Twenty independent outcomes are not fabricated. |
| P9 | Explicit SQLite connection closing, bounded connection retries only, unleased-generation collection between deep maintenance, one-minute external watchdog, canonical health | No retry of an ambiguous broker write. No automatic code rewrite, disk deletion, risk expansion or arbitrary unfreeze. Real repair latency must still be measured. |
| P10 | Existing dashboard layout retained; canonical execution health and outcome eligibility exposed; guide and whitepaper updated | Telegram team health consumes the same canonical health. Production route, digest and delivery checks are release acceptance, not assumed results. |
| P11 | Exact-commit promotion, maintained paper policy amendment, guarded restart, exact-build exchange-calendar soak, automatic prospective economic report inside the existing active-trial owner | Five distinct real market sessions then 20 observed evaluation sessions remain prospective milestones. No retrospective session credit. |

## Canonical Evidence/Gate Register

This is the index of existing producers and consumers, not another execution
authority. Runtime decisions retain their typed evidence and primary stop reason.

| Field / condition | Producer | Consumer / missing treatment |
|---|---|---|
| Account, positions, orders, fills | `paper_account.py` read-only broker mirror and `qadam_operating_ledger.py` reconciliation | Canonical PaperOps; missing or disagreement freezes execution, never a size haircut |
| Direction and executable proxy | trigger factory, qualitative/power mechanisms, strategy foundry | Akber and Router; unsupported direction or mapping remains research-only |
| Fresh quote, spread and liquidity | market-data evidence and tradeability envelope | Akber / risk / Router; stale or unavailable execution data requires refresh |
| Invalidation, stop, target, horizon | frozen hypothesis plus fresh numeric market geometry | Canonical exit prewrite; no entry without a durable exit plan |
| Unknown expected return | foundry explicitly emits `None`, never zero or an invented positive estimate | Only typed discovery-micro may proceed, with the amended $250/$5 bounds and a size reduction |
| Known non-positive expected return | matched historical or forward evidence | Cannot be relabelled unknown to obtain discovery authority |
| Optional corroboration | source capability registry and evidence profiles | Reduced confidence/size or deferred entry; no fabricated provider field |
| Version, event and decision-time snapshot | stable strategy definition, canonical decision, frozen forward shadow | Learning and promotion; absent lineage is ineligible for proof |
| Aggregate/cluster risk and affordable minimum lot | portfolio risk engine and broker reconciliation | Hard existing budget; rounding cannot raise the approved budget |
| Real market session | Alpaca clock and cached provider calendar | Entry/exit session checks; no weekday-only holiday credit |
| Matured outcome, matched benchmark and costs | registered forward tournament / outcome accounting | Emerging review after scheduled independent checkpoints; not required before the first bounded unknown-return experiment |

## Verification Record

The final clean-checkout regression suite reports 1,018 passed and 39 failed.
The same 39 tests fail on the unchanged baseline; most use absent untracked
runtime/site fixtures. No new failing test was introduced in the comparison.
The failed-test identities were compared against the baseline XML and are
identical. This is not a claim that the repository-wide suite is green. All changed Python
files pass Ruff. Additional release-only checks and deployment receipts must be
reported separately from unit tests.

The foundry now registers each valid immutable strategy definition before
publishing its draft. Registration uses the actual write time, not a backdated
research timestamp, and rejects a mismatched definition hash. Invalid foundry
generations cannot replace the last valid drafts. Registration is research
metadata only and grants no broker or portfolio authority.

Live recovery on 6 September passed three guarded PaperOps revalidations and
separate portfolio-review, lifecycle-poll and dashboard revalidations. At
07:52:55 UTC, the operator reported 21/21 fresh services, zero open circuits and
zero repair requests. Canonical broker reconciliation removed the recoverable
mirror freeze without clearing an unrelated hold or submitting an order. A
further exact-build verification is required after the preregistration patch.

Real read-only Alpaca verification on 6 September returned five positions, no
open orders, 31 closed-trade records and USD 100,123.80 equity. Those are a dated
snapshot, not permanent operating figures. The provider clock reported the next
regular session as 8 September 2026 at 09:30 America/New_York. No Sunday trade is
required or manufactured for acceptance.

## Limits And Next Evidence

- Cumulative order fill snapshots are labelled as aggregates, not individual
  exchange executions. Incomplete history, corporate-action ambiguity and missing
  costs must remain excluded from net-performance attribution.
- Gross reconstructed closed-order P&L is not interchangeable with broker account
  return. Legacy starting balances, residual positions and unresolved attribution
  must not be filled in with zero-valued estimates.
- The old bounded-experimental tier still labels its rejected historical result
  as provisional. It is not promoted to validated status by this amendment.
- Existing source access is not proof of a useful numeric trigger. Programme
  supply, unchanged-event suppression and untouched performance require continued
  real-packet and forward checks.
- The six-slot allocation challenger, threshold superiority, regime robustness,
  five-session operational soak and 20-session economics review remain pending.
- Stops describe planned risk, not guaranteed maximum loss. The laptop and network
  must remain available for synthetic exits. Paper fills do not establish live
  market impact, queue priority or real-money profitability.
- Self-healing may retry known, bounded recoverable failures and then escalate.
  It cannot promise to repair arbitrary defects, provider outages or hardware
  failure without intervention. A manual/risk hold remains authoritative.

Primary broker references: [Alpaca paper trading](https://docs.alpaca.markets/us/docs/paper-trading),
[order lifecycle](https://docs.alpaca.markets/us/docs/orders-at-alpaca),
[exchange calendar](https://docs.alpaca.markets/us/reference/legacycalendar).

## Final Integration Repairs

Real Gemma verification identified a provider grammar failure: nested string
length limits exceeded llama.cpp grammar expansion limits. The transport schema
now omits string repetition bounds while the canonical output schema and critic
still enforce them. The local task uses a compact 900-token output budget,
180-second request timeout and disabled optional reasoning. On 6 September at
08:54:42 UTC, an actual research packet returned `live_local_llm`,
`raw_response_status=ok`, with one packet processed. Endpoint availability alone
is not considered successful analysis.

Local inference and configured-model reloads now share a nonblocking process
lock. A failed live inference can trigger only a localhost, configured-model
reload, with a persisted 15-minute cooldown. Active requests cannot be interrupted
by another Qadam reload; remote endpoints cannot trigger local model operations.

The 20-session report is embedded in the existing active-trial status and public
summary. It freezes the policy/account/epoch binding and start-state baseline,
waits for the corrected five-session soak, then samples actual provider sessions.
Repeated polls, closed dates and holidays cannot create session credit. Software
changes alone do not reset this economic record; policy/account changes require
a separate evaluation. Reports include distinct canonical opportunities,
independent completed experiments, deployed capital, filled turnover, sampled
account return and drawdown, and measured net/benchmark outcomes where available.
Missing cost, cash-flow and human-intervention measurements remain explicitly
unknown. Completion creates a review, never capital expansion or proof credit.

The final runtime handover also exposed a duplicate full-database integrity scan
in the PaperOps summary/publication path. The wrapper now builds and publishes one
checked snapshot instead of immediately rebuilding it. The integrity scan itself,
freeze handling and pre/post broker reconciliation are retained; no cached report
is used to authorise an order. Both healthy and frozen-state publication are tested.

A deployment can also supersede an in-flight critic request. The singleton
correctly refuses a different build's request; the critic now ends that obsolete
wait explicitly instead of waiting up to two hours for an impossible receipt.
It reports `replan_required`, not success. The existing watchdog can then wake a
fresh critic; neither a newer request nor an execution hold is overwritten.

A subsequent real cycle at 10:30 UTC exposed a shadow identity mismatch: creation
used economic event plus strategy version, but reconciliation and validation used
only the event. A newly versioned XAR observation therefore opened the shadow
circuit and its portfolio dependency circuit. All three operations now use the
same event/version key. Aggregate calibration and promotion still deduplicate
economic events, and frozen version identities cannot be changed externally.
Superseded historical records remain excluded rather than receiving retrospective
evidence credit. Five regression cases cover legacy-to-versioned transitions,
two-version comparisons, repeat polls, genuine duplicates and frozen identity.
Three read-only replays at 10:43 UTC preserved all 336 frozen decisions, 202
existing outcomes and two superseded records with zero errors or writes. These
checks precede installation; live circuit revalidation is reported separately.
