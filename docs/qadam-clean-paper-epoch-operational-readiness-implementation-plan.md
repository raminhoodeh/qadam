# Qadam Clean Paper Epoch And Operational Readiness Implementation Plan

Date: 2026-07-18

Status: Implementation complete; operational cutover remains gated by real evidence and operator setup

Parent plan: `docs/qadam-operator-ready-edge-engine-implementation-plan.md`

Supporting plans:

- `docs/qadam-whole-universe-historical-backfill-backtest-implementation-plan.md`
- `docs/qadam-next-generation-flow-implementation-plan.md`
- `docs/qadam-dashboard-ten-stage-lifecycle-implementation-plan.md`

## 1. Purpose

This plan closes the remaining gap between the implemented Qadam research
architecture and a clean, continuously operating paper fund.

It has four linked outcomes:

1. make the existing dashboard continuously fresh without changing its current
   routes, navigation, information architecture, or visual hierarchy;
2. close the remaining evidence, source-freshness, backtest-certification,
   forward-shadow, and unattended-operation blockers;
3. archive the current testing epoch immutably while removing it from every
   public dashboard calculation and list;
4. start one new auditable Alpaca Paper epoch at exactly **US$100,000**, then
   allow guarded autonomous paper operation only after all release gates pass.

This is a paper-only operational-reentry plan. It does not enable live capital,
promise profit, force trades, delete audit evidence, or grant the dashboard,
Telegram, an LLM, or a quantum process execution authority.

## 2. Required End State

At completion:

- Qadam's current dashboard structure is unchanged.
- Production dashboard data is refreshed from the running laptop without a
  Vercel redeploy for each status update.
- Every decision-critical artifact is fresh or explicitly blocked and labelled.
- The statistical backtest is represented truthfully as completed, while zero
  validated edges remains a valid result.
- Classified unavailable history is not treated as unfinished acquisition.
- Real missing evidence is distinguishable from impossible or intentionally
  excluded source-price relationships.
- At least one edge has passed the frozen historical promotion policy before it
  can advance toward paper review.
- Required forward-shadow evidence and the real-session operational soak have
  completed without simulated elapsed time.
- The old testing epoch remains available in an immutable local audit archive.
- No record from the old testing epoch appears in Portfolio, Trading History,
  Order Monitor, Results & Lessons, performance, drawdown, or the paper proof
  ledger for the new epoch.
- The new Alpaca Paper account and the new local Qadam paper epoch both start at
  US$100,000 with zero positions, zero orders, zero closed trades, and zero P&L.
- Qadam runs continuously under guarded paper authority and may submit a paper
  order only when a distinct setup passes every evidence, Akber, shadow, risk,
  Router, idempotency, duplicate-exposure, drawdown, Q-CTRL, and PaperOps gate.
- A correct outcome may still be no trade.

## 3. Current Verified Baseline

This baseline is dated and must be regenerated before implementation begins.

| Area | Current state | Meaning |
| --- | --- | --- |
| Operator service | Installed and running | The local service exists, but operating presence alone is not readiness. |
| Execution mode | PaperOps watch-only with research lock active | No new paper-trading epoch should start yet. |
| Final certification | `blocked_evidence_maturing` | `paper_trial_resume_allowed` is false. |
| Production dashboard | Frontend live, production snapshot stale | The page exists, but its displayed portfolio and runtime state are not current. |
| Current broker mirror | Approximately US$99,891, 42 closed testing trades, no open positions | These records belong to the testing epoch and must be archived at cutover. |
| Source operations | Some sources fresh; unresolved source repair requests remain | Configured or responding does not automatically mean fresh or quorum-eligible. |
| Provider history | 223 of 360 partitions acquired; 137 terminally classified unavailable | The checker currently confuses classified terminal gaps with unfinished work. |
| Statistical backtest | Completed with 360 hypotheses, 1,332 fold results, and 300 holdout results | The final checker incorrectly reads a legacy `fold_count` field. |
| Negative controls | No validated negative-control result | This is a real research blocker, unlike the fold-field mismatch. |
| Validated edges | 0 | Qadam has research findings but no promoted edge. |
| Forward shadow | 0 real outcomes and 0 elapsed evidence days for an eligible promoted setup | Real future market time is still required. |
| Operational soak | 1 of 7 real sessions recorded in the dated baseline | The unattended service has not completed its required soak. |

The implementation must refresh these facts from canonical artifacts rather
than embedding the values above as permanent acceptance thresholds.

## 4. Scope Separation

The cutover must distinguish research memory from paper-account history.

### 4.1 Research Memory That Persists

The following must survive the paper-epoch cutover unchanged:

- immutable provider-backed raw historical data;
- normalized source and price history;
- point-in-time alignment records;
- source-price comparisons;
- pattern score tapes;
- forward labels that have already matured legitimately;
- walk-forward, holdout, ablation, negative-control, and nonlinear results;
- edge registry records;
- strategy hypotheses and rejected hypotheses;
- source reliability history;
- repair history;
- model, Akber, Router, and quantum research attribution;
- strategy and risk policy versions.

### 4.2 Testing-Epoch State That Is Archived

The following execution-layer state belongs to the testing epoch:

- broker account identity fingerprint;
- paper account snapshots;
- paper orders and fills;
- open and closed position records;
- trade-history rows;
- lifecycle and reconciliation records;
- paper postmortems;
- proof-eligibility audits;
- paper performance, P&L, drawdown, and trial-calendar state;
- execution idempotency entries that are scoped to the testing account;
- dashboard portfolio and order projections derived from those records.

These records must be copied into an immutable archive, checksummed, and removed
from active projections. They must not be deleted or silently rewritten.

### 4.3 New-Epoch State That Starts Empty

The new epoch begins with:

- account currency `USD`;
- starting equity US$100,000;
- cash US$100,000;
- zero realized P&L;
- zero unrealized P&L;
- zero drawdown;
- zero positions;
- zero active or historical orders;
- zero closed Qadam-origin paper trades;
- zero postmortems;
- zero paper proof ledger entries;
- a real start timestamp and calendar day 1 only when cutover is completed.

## 5. Non-Negotiable Boundaries

- Keep live capital disabled.
- Keep live broker endpoints denied.
- Use only Alpaca Paper for broker writes.
- Do not create a paper order during readiness, archive, account setup, or
  dashboard deployment.
- Do not begin the new 30-day paper growth trial before the cutover timestamp.
- Do not backfill, simulate, pause, or extend elapsed trial time.
- Do not fabricate unavailable provider history.
- Do not make all 41 sources appear fresh merely to pass a count.
- Do not require economically irrelevant source-instrument pairs to become
  artificial evidence.
- Do not promote an edge because the system needs a trade.
- Do not include testing, mirror-only, fixture, backtest, or shadow records in
  the new epoch's paper proof ledger.
- Do not expose broker credentials, provider credentials, signing keys, or full
  broker account IDs in runtime or public artifacts.
- Do not let a dashboard, Telegram message, local LLM, frontier LLM, quantum
  process, or backtest create authority.
- Preserve unrelated worktree changes throughout implementation.

## 6. Architecture Decisions

### 6.1 One Canonical Paper Epoch Identity

Create a schema-versioned epoch contract owned by one module, proposed as:

```text
orchestrator/qadam_paper_epoch.py
```

Every active paper execution record must carry:

```json
{
  "paper_epoch_id": "paper-epoch-...",
  "paper_epoch_kind": "clean_operator_epoch",
  "paper_epoch_started_at": "...",
  "account_currency": "USD",
  "starting_equity": 100000.0,
  "broker_account_fingerprint": "sha256:...",
  "record_origin": "qadam_origin | broker_mirror | legacy_test",
  "eligible_for_current_dashboard": true,
  "eligible_for_paper_proof_ledger": false
}
```

The full broker account ID must not be written to public artifacts. A one-way
fingerprint is sufficient to prove that the new account differs from the
archived testing account.

### 6.2 Currency-Native Paper Account Contract

The current paper account model uses legacy `*_gbp` field names while the
connected Alpaca account reports and the dashboard displays US dollars. The
implementation must add canonical currency-native fields:

```text
starting_balance
current_balance
cash
equity
peak_equity
realized_pnl
unrealized_pnl
notional
risk_size
account_currency
display_currency
```

For the new epoch, both currency fields must be `USD`.

Legacy `*_gbp` fields may remain as deprecated read aliases during migration,
but new writers must not use them as the canonical source. The dashboard must
prefer the currency-native values and must never relabel a GBP value as USD.

### 6.3 Epoch-Aware Dashboard Projection

All portfolio, order, history, postmortem, and learning view-model producers
must filter by the active `paper_epoch_id` before writing a public-safe
snapshot. Timestamp-only filtering may remain as a defensive fallback for old
broker payloads, but it cannot be the sole identity boundary for new records.

The testing archive must not appear as a selectable dashboard epoch, hidden
row, aggregate count, chart point, learning result, or proof record. It remains
available through local audit files and explicit CLI checks only.

### 6.4 One-Way Fresh Production Status Bridge

The current Vercel API reads a JSON file bundled at deployment time. That is a
static release snapshot, not a continuously fresh bridge.

Implement a one-way publisher with these boundaries:

- the laptop produces an allowlisted public-safe snapshot;
- the snapshot is signed and uploaded through an authenticated write-only
  publisher path;
- the hosted dashboard API reads only the newest validated snapshot;
- public GET and HEAD requests remain read-only;
- no hosted endpoint can send a command back to the laptop;
- no snapshot contains secrets, broker authority, or raw private research;
- stale snapshots remain available only with an explicit stale state;
- the static bundled file remains a visibly degraded fallback, not a source
  that can appear live.

The preferred implementation should use the existing Supabase footprint or a
comparably small append-only snapshot store. The decision must be recorded
before implementation. Only a service credential may publish; the browser may
read only the latest sanitized snapshot under an explicit row-level policy.

### 6.5 Release Is A State Machine, Not A Single Boolean

Use the following canonical states:

```text
readiness_blocked
-> research_operational
-> edge_validated
-> forward_shadow_observing
-> paper_operator_ready
-> operator_account_action_required
-> clean_epoch_prepared
-> clean_epoch_reconciled
-> dashboard_current
-> guarded_paper_operating
-> paper_performance_accumulating
```

No state may be skipped because an artifact file exists.

## 7. Implementation Phases

### Phase 0 - Freeze, Snapshot, And Rebaseline

#### Objective

Create a trustworthy pre-change record and prevent the current testing epoch
from being confused with the future clean epoch.

#### Build

- Keep the research lock active and PaperOps watch-only.
- Capture current Git status without cleaning unrelated changes.
- Capture current operator service, supervisor, source, dashboard, broker,
  backfill, backtest, edge, Akber, Router, shadow, lifecycle, and certification
  artifacts.
- Hash the current testing-epoch paper artifacts without moving them yet.
- Record the current broker account fingerprint, balance, positions, orders,
  closed-trade count, and latest mirror timestamp.
- Record current production dashboard release, API snapshot timestamp, static
  fallback timestamp, and both production aliases.
- Add a dynamic plan status entry for this plan.

#### Artifacts

```text
data/runtime/qadam_clean_epoch_preflight_baseline.json
data/runtime/qadam_clean_epoch_dynamic_status.json
data/runtime/qadam_testing_epoch_inventory.json
```

#### Acceptance

- Research lock is active.
- Paper order and broker-write counts remain zero for this phase.
- Testing records are inventoried but still untouched.
- Every baseline claim has an artifact path and timestamp.
- No test history has been hidden before an auditable archive exists.

### Phase 1 - Repair Certification Truth

#### Objective

Make the final checker distinguish implementation defects, real evidence
blockers, and terminally classified data gaps.

#### Build

- Replace the obsolete `fold_count` read with the canonical
  `fold_result_count`, with a versioned compatibility adapter for older
  artifacts.
- Validate the existing 1,332 fold results and 300 holdout results rather than
  claiming the backtest did not run.
- Keep the absence of validated negative controls as a real blocker.
- Treat `complete` and approved `unavailable_classified` provider partitions as
  terminal, while keeping only acquired rows eligible as evidence.
- Do not require 360 acquired partitions when 137 have an approved typed
  unavailable state.
- Require all unclassified, retryable, or critical provider failures to be
  resolved.
- Reconcile `typed_evidence_completed_count` with
  `eligible_forward_score_input_count`; define exactly what constitutes one
  complete promotable evidence row.
- Make blocker messages describe the real condition rather than a generic
  "backtest has not run" statement.
- Add regression fixtures for completed, classified-unavailable, partially
  acquired, and fabricated-coverage cases.

#### Artifacts

```text
data/runtime/qadam_certification_contract_audit.json
data/runtime/qadam_backtest_field_compatibility_audit.json
```

#### Checks

```text
scripts/check_qadam_certification_contracts.py
scripts/check_qadam_operator_ready_edge_engine.py
```

#### Acceptance

- A completed backtest is recognized as completed.
- Zero validated edges still blocks paper release.
- Classified unavailable history cannot become evidence.
- Unclassified missing history still blocks the affected relationship.
- The checker cannot pass from fixtures or key presence alone.

### Phase 2 - Restore Fresh Source And Runtime Production

#### Objective

Make every decision-critical producer run on its intended cadence and remove
stale-state drift at the source rather than masking it in the dashboard.

#### Build

- Inventory every artifact monitored by
  `qadam_operator_dashboard_freshness.json`.
- Map each artifact to one owning producer, cadence, stale threshold, safe retry
  rule, and repair escalation.
- Remove duplicate or superseded producers that overwrite canonical state.
- Refresh live-capable source adapters and classify each source as configured,
  responding, fresh, quorum-eligible, historical-only, forward-only,
  intentionally disabled, rate-limited, provider-error, or quarantined.
- Resolve the current source repair queue where credentials, terms, or provider
  support already permit safe operation.
- Keep unsupported sources classified instead of fabricating freshness.
- Require zero stale decision-critical producers before paper release.
- Require zero unresolved critical source repair requests.
- Permit non-critical unavailable sources only when they are excluded from
  quorum and affected setups.
- Add per-producer run receipts proving work was performed, not merely that a
  status projection was refreshed.

#### Artifacts

```text
data/runtime/qadam_runtime_producer_registry.json
data/runtime/qadam_runtime_freshness_closure.json
data/runtime/qadam_source_repair_closure.json
data/runtime/qadam_operator_job_receipts.jsonl
```

#### Checks

```text
scripts/check_qadam_runtime_producers.py
scripts/check_qadam_source_freshness_release.py
scripts/check_qadam_operator_service.py
```

#### Acceptance

- Every monitored artifact has one owner and a fresh receipt.
- No decision-critical artifact is stale.
- No source counts toward quorum while stale, disabled, fixture-backed, or
  quarantined.
- PaperOps remains watch-only.

### Phase 3 - Make The Production Dashboard Continuously Fresh

#### Objective

Keep the current dashboard intact while replacing deployment-time data with a
safe current-status pipeline.

#### Build

- Preserve all 13 protected routes and the current 10-stage lifecycle.
- Preserve page names, sidebar order, cards, collapsible sections, responsive
  behavior, and existing visual design.
- Add an allowlist serializer that strips secrets, raw credentials, broker
  account IDs, internal paths, and non-public payloads.
- Sign every public-safe snapshot and include `generated_at`, `published_at`,
  schema version, epoch ID, source digest, and freshness state.
- Add an authenticated one-way publisher from the operator service.
- Change `/api/cockpit-status` to retrieve the latest valid hosted snapshot
  rather than reading only the deployed filesystem copy.
- Keep `/status/cockpit-status.json` as a static emergency fallback.
- Make the dashboard reject malformed, future-dated, unsigned where signing is
  required, or schema-incompatible snapshots.
- Preserve expanded-card and scroll state during the existing refresh loop.
- Surface stale data honestly without replacing the page with technical noise.
- Add source-to-hosted and hosted-to-browser latency metrics to System
  Overview without changing its route or structure.
- Add a production parity checker comparing local canonical digest, hosted
  digest, and rendered browser timestamp.

#### Artifacts

```text
data/runtime/qadam_public_status_publish_receipt.json
data/runtime/qadam_public_status_parity.json
data/runtime/qadam_public_status_security_audit.json
```

#### Checks

```text
scripts/check_qadam_public_status_publisher.py
scripts/check_dashboard_live_bridge.js
scripts/check_dashboard_ten_stage_lifecycle.js
scripts/check_dashboard_portfolio_consistency.py
scripts/verify-dashboard-production-release.js
```

#### Acceptance

- The dashboard route matrix and appearance remain unchanged.
- A fresh local snapshot reaches production without a Vercel redeploy.
- Production freshness stays within the approved status SLA while the laptop is
  online.
- If the laptop or publisher stops, the dashboard says stale and never presents
  the static fallback as current.
- GET and HEAD are the only public status methods.
- No browser-to-laptop or browser-to-broker command path exists.

### Phase 4 - Close Historical Evidence And Backtest Gaps Honestly

#### Objective

Finish the research baseline without treating unavailable data as acquired or
forcing a positive result.

#### Build

- Preserve the 223 acquired and 137 classified-unavailable provider partition
  outcomes.
- Revalidate checksums, point-in-time timestamps, parser versions, calendars,
  futures rolls, contract identities, and provider provenance.
- Reclassify the legacy 6,150 missing windows under a versioned taxonomy.
- Keep the existing high-level classes visible in research artifacts:
  `price_history_absent`, `pair_intentionally_not_meaningful`, and
  `contract_expired_or_identity_history_missing`.
- Distinguish a window that is unavailable from one that is incomplete but
  repairable.
- Revisit excluded providers only when written terms, credentials, and data
  availability permit it.
- Keep Unusual Whales out of historical scoring until provider-backed history
  produces validated rows; current zero-row state must remain explicit.
- Complete proper negative controls, shuffled-label controls, placebo lags,
  regime controls, and holdout integrity checks.
- Rerun the frozen statistical protocol after any material data repair.
- Preserve zero validated edges if no relationship survives.

#### Artifacts

```text
data/runtime/qadam_historical_gap_resolution.json
data/runtime/qadam_negative_control_results.json
data/runtime/qadam_backtest_recertification.json
data/runtime/qadam_unavailable_history_registry.json
```

#### Checks

```text
scripts/check_qadam_provider_backfill.py
scripts/check_qadam_point_in_time_evidence.py
scripts/check_qadam_statistical_backtest.py
scripts/check_qadam_historical_gap_resolution.py
```

#### Acceptance

- Every planned partition has one terminal typed state.
- Every eligible score row has real provider lineage.
- Leakage violations are zero.
- Negative controls execute and are interpretable.
- Holdout tuning violations are zero.
- Missing data is not converted into neutral or zero-valued evidence.
- No edge is promoted merely to unblock the next phase.

### Phase 5 - Validate An Edge Or Remain In Research

#### Objective

Require Qadam to demonstrate at least one statistically supported edge before
paper-operation release.

#### Build

- Rank relationships under the frozen out-of-sample promotion policy.
- Require sufficient sample size, cost-adjusted expectancy, stability across
  folds, false-discovery control, holdout survival, drawdown tolerance, and
  regime robustness.
- Record source contribution and single-source dependence.
- Record classical versus nonlinear incremental value.
- Record quantum execution mode honestly as hardware, simulator, classical
  fallback, not run, or not useful.
- Map a surviving relationship to a configured strategy or form an emerging
  strategy without changing the dashboard route structure.
- Reject weak, overfit, unpaperable, stale, or concentrated relationships.
- Keep the edge registry empty when no candidate qualifies.

#### Artifacts

```text
data/runtime/qadam_edge_registry_v3.json
data/runtime/qadam_edge_promotion_audit.json
data/runtime/qadam_strategy_evidence_map_v3.json
```

#### Acceptance

- At least one edge is required for paper-operator readiness.
- Every promoted edge has immutable source-price, score, label, fold, holdout,
  cost, and rejection-policy lineage.
- Quantum activity cannot substitute for statistical evidence.
- If no edge qualifies, the program returns to Phases 2 through 5 and does not
  reset or start the new paper epoch.

### Phase 6 - Akber, Forward Shadow, Portfolio Risk, And Router Readiness

#### Objective

Prove that a validated historical edge can become a complete, trade-shaped
paper-review setup under current market conditions.

#### Build

- Generate a full strategy hypothesis with Research Goal lineage, candidate
  identity, instrument mapping, invalidation, expiry, and risk concept.
- Supply all required Akber context: current source-price state, fresh catalyst,
  technical confirmation, volume/flow, volatility, pricing gap, liquidity,
  risk/reward, invalidation, and quantum/nonlinear review state.
- Run historical Akber replay and ablation before accepting threshold value.
- Accumulate real forward-shadow observations and outcomes over real market
  time.
- Compare pass, hold, veto, wait, and no-order counterfactuals.
- Construct portfolio risk using the US$100,000 mandate without creating an
  order.
- Require one final Router state for every setup.
- Exercise the V3-to-PaperOps handoff in non-writing validation mode.

#### Artifacts

```text
data/runtime/qadam_paper_operator_candidate_readiness.json
data/runtime/qadam_forward_shadow_v3.json
data/runtime/qadam_portfolio_risk_v3.json
data/runtime/qadam_router_v3_scoreboard.json
data/runtime/qadam_paperops_handoff_dry_run.json
```

#### Acceptance

- Required Akber context is complete for the eligible setup.
- Akber pass remains research eligibility, not execution approval.
- Forward-shadow evidence uses real elapsed time.
- Portfolio drawdown, concentration, liquidity, and correlation checks pass.
- Router produces exactly one state.
- Dry-run handoff creates zero orders and zero broker writes.

### Phase 7 - Seven-Session Unattended Soak And Final Release Review

#### Objective

Prove the laptop service can operate safely before opening the clean epoch.

#### Build

- Run at least seven real unattended sessions with no simulated time.
- Exercise restart after sleep, network loss, provider rate limiting, stale
  artifacts, and recoverable process failure.
- Verify safe retries, idempotency, checkpoint resume, and repair requests.
- Verify the service runs due research jobs rather than only refreshing status.
- Verify the public dashboard stays fresh during normal operation and becomes
  explicitly stale during an induced publisher interruption.
- Verify no PaperOps write occurs while the research lock is active.
- Re-run final operator-ready certification.

#### Artifacts

```text
data/runtime/qadam_operator_soak_v2.json
data/runtime/qadam_paper_trial_release_candidate.json
```

#### Acceptance

- Seven real sessions complete.
- No simulated elapsed time appears.
- No unresolved critical repair request remains.
- Production dashboard parity passes.
- `paper_trial_resume_allowed` becomes true only from fresh evidence.
- A human release decision is still required.

### Phase 8 - Prepare The Clean Alpaca Paper Account

#### Objective

Create a genuinely empty broker account boundary without exposing credentials
or mutating live capital.

#### Operator Action

The operator creates a new Alpaca Paper account with US$100,000 starting equity
and generates new paper API credentials. The operator stores those credentials
through the existing local secret mechanism. Implementation code must not print,
commit, transmit, or edit the credential values.

#### Build

- Add a read-only new-account preflight.
- Verify Alpaca Paper base URL and account mode.
- Verify account currency is USD.
- Verify equity and cash are exactly US$100,000 within a documented tolerance.
- Verify zero positions and zero orders.
- Verify the new broker account fingerprint differs from the testing account.
- Verify no live-capital or live-endpoint setting changed.
- Keep the research lock active through this phase.

#### Artifacts

```text
data/runtime/qadam_clean_broker_account_preflight.json
```

#### Acceptance

- New account is Alpaca Paper.
- Account fingerprint is new.
- Currency and starting balance are correct.
- Positions, orders, and broker exceptions are zero.
- No broker write has occurred.
- Secrets are absent from logs and artifacts.

### Phase 9 - Transactional Testing-Epoch Archive And Clean-Epoch Cutover

#### Objective

Archive the test history, activate the clean epoch, and make the operation
restart-safe without deleting evidence.

#### Build

- Replace the legacy reset script internals with the canonical epoch module
  while retaining a compatibility command.
- Add `--currency USD` and `--starting-balance 100000` as canonical arguments.
- Deprecate `--balance-gbp` without breaking old archived manifests.
- Refuse to cut over unless Phase 7 and Phase 8 pass from fresh evidence.
- Pause the operator service at a checkpoint.
- Acquire a single cutover lock.
- Re-read the broker account and assert zero exposure.
- Copy all testing-epoch execution artifacts into a timestamped archive.
- Write per-file SHA-256 checksums and an archive Merkle or aggregate digest.
- Mark archived records `legacy_test` and proof-ineligible.
- Write the new epoch registry entry and atomic current-epoch pointer.
- Initialize the active paper mirror at US$100,000 and empty history.
- Preserve research artifacts and historical datasets.
- Rebuild every active execution, dashboard, lifecycle, and proof projection.
- Resume the service in watch-only mode for reconciliation.
- Roll back the active epoch pointer if any post-write invariant fails.

#### Artifacts

```text
data/runtime/paper_epochs.jsonl
data/runtime/current_paper_epoch.json
data/runtime/archive/<testing_epoch_id>/manifest.json
data/runtime/archive/<testing_epoch_id>/checksums.json
data/runtime/qadam_clean_epoch_cutover_receipt.json
data/runtime/qadam_clean_epoch_rollback_receipt.json
```

#### Checks

```text
scripts/check_qadam_clean_epoch_readiness.py
scripts/prepare_qadam_clean_paper_epoch.py
scripts/check_qadam_clean_epoch_cutover.py
```

#### Acceptance

- Archive digest verifies.
- Old records remain locally auditable.
- Active epoch pointer references only the new epoch.
- New account starts at US$100,000 and USD everywhere.
- Current positions, orders, closed trades, P&L, drawdown, postmortems, and proof
  records are zero.
- Old test records are absent from all active view models.
- The real 30-day paper growth trial begins at the cutover timestamp and not
  before it.

### Phase 10 - Clean Dashboard Projection And Production Verification

#### Objective

Show the new epoch cleanly on the unchanged live dashboard.

#### Required Page Outcomes

| Existing page | Clean-epoch projection |
| --- | --- |
| Qadam Team | Current team and service status; no structural change. |
| Portfolio | US$100,000 starting/current value, 100% cash, zero P&L, zero drawdown, and a chart beginning at the cutover timestamp. |
| Trading History | Existing design with a clean current-epoch empty state; no testing rows or testing counts. |
| Data Sources | Current source freshness and classifications; research history remains intact. |
| Trading Universe | Existing 19-instrument structure and current provider/paperability details. |
| Pattern Recognition | Current research findings and evidence maturity; not reset with the account. |
| Quantum Edge | Current classical/quantum evidence state; not reset with the account. |
| Trading Strategies | Existing configured, emerging, and validated structure; current evidence only. |
| Decision Room | Current Akber, candidate, Router, and wait/trade verdict. |
| Order Monitor | Idle broker mirror with zero active orders, zero positions, and zero exceptions. |
| Results & Lessons | No current-epoch paper lessons until a Qadam-origin trade closes; research lessons may remain if clearly non-paper. |
| Tests & Improvements | Existing research proposals and tests; no old test-trade performance attribution. |
| System Overview | Fresh service, publisher, epoch, source, repair, lock, and paper-route state. |

#### Build

- Require `paper_epoch_id` in every execution-derived dashboard record.
- Filter chart, cards, history, order monitor, lifecycle, postmortem, and proof
  calculations to the current epoch.
- Ensure the header balance, Portfolio value, chart endpoint, composition total,
  cash, and broker mirror use one canonical snapshot and timestamp.
- Add an internal checker that searches the rendered DOM for archived trade IDs
  and rejects the release if any appear.
- Publish the clean snapshot through the one-way status bridge.
- Deploy frontend code only if code changed; do not redeploy merely to refresh
  current data.
- Verify both `qadam.trade` and `www.qadam.trade` with fresh browser requests.

#### Checks

```text
scripts/check_dashboard_portfolio_consistency.py
scripts/check_dashboard_order_monitor.js
scripts/check_dashboard_ten_stage_lifecycle.js
scripts/check_qadam_dashboard_epoch_isolation.py
scripts/verify-dashboard-production-release.js
```

#### Acceptance

- The dashboard structure and design are unchanged.
- US$100,000 agrees on every visible surface.
- All dashboard timestamps refer to the same current snapshot or clearly state
  their independent source timestamp.
- No testing-epoch order, trade, P&L, chart point, lesson, or proof count is
  visible.
- Research and backtest evidence remains visible where it belongs.
- Production data is fresh and digest-matched to the local public snapshot.

### Phase 11 - Guarded Autonomous Paper Launch

#### Objective

Release the clean epoch into continuously supervised guarded paper operation.

#### Build

- Record explicit operator approval of the strategy version, risk-policy
  version, clean epoch, and paper-only release.
- Release the research lock through the audited release command only.
- Keep live capital false and the broker base URL fixed to Alpaca Paper.
- Run one canonical PaperOps pass before unattended scheduling.
- Confirm zero forced-trade behavior when no setup qualifies.
- Enable the operator service's guarded PaperOps cadence.
- Require a receipt for every handoff consumption, rejection, order submission,
  lifecycle transition, and repair request.
- Keep the dashboard and Telegram notify-only and command-disabled.
- Monitor the first eligible setup through Router, PaperOps, broker mirror,
  lifecycle, closeout, postmortem, and paper proof ledger eligibility.

#### Artifacts

```text
data/runtime/qadam_clean_epoch_release_approval.json
data/runtime/qadam_guarded_paper_launch_receipt.json
data/runtime/qadam_clean_epoch_operating_status.json
```

#### Acceptance

- The release approval references exact strategy, risk, Router, PaperOps, and
  epoch versions.
- The canonical wrapper is the only paper-order route.
- Every submitted order has distinct Research Goal lineage, candidate identity,
  and idempotency key.
- Duplicate exposure, drawdown, source quorum, Q-CTRL, and broker reconciliation
  checks remain active.
- No trade is submitted unless a setup qualifies.
- The dashboard remains current during operation.

### Phase 12 - Post-Launch Evidence And Performance Discipline

#### Objective

Measure whether the new system works without rewriting history or overstating
early returns.

#### Build

- Review service and dashboard freshness daily.
- Review edge, Akber, shadow, Router, and portfolio state daily.
- Attribute every hold, veto, miss, paper order, fill, close, and failure.
- Admit only real closed Qadam-origin trades with complete lineage to the paper
  proof ledger.
- Keep testing-epoch trades permanently ineligible.
- Compare realized paper performance with backtest and shadow expectations.
- Apply strategy changes only through versioned improvement proposals.
- Evaluate the actual 30-day paper growth trial only after its real calendar
  closes.
- Keep profitability claims separate from operational readiness.

#### Acceptance

- No proof leakage exists.
- Every current-epoch paper trade has complete lifecycle and attribution.
- Performance is reproducible from current-epoch records.
- Strategy changes remain proposal-first and reviewable.
- Qadam may remain in cash when expected value is not positive.

## 8. Dashboard Preservation Contract

Implementation must retain exactly these 13 routes:

```text
system/team
fund/portfolio
fund/timeline
observe/sources
observe/universe
patterns/findings
patterns/nonlinear
decide/strategies
decide/decision
trade/orders
learn/outcomes
learn/improvements
system/overview
```

It must also preserve:

- `fund/portfolio` as the default route;
- Qadam Team pinned above the journey;
- System Overview as the standalone bottom destination;
- the current sidebar and mobile navigation order;
- one 10-stage lifecycle on every route;
- existing route aliases;
- current collapse, tooltip, scroll, responsive, keyboard, screen-reader,
  reduced-motion, and print behavior;
- the existing page-level visual language and information hierarchy.

This plan changes data provenance, freshness, currency correctness, and epoch
isolation. It does not authorize a dashboard redesign.

## 9. Historical Data Completion Policy

The historical program is complete enough for a particular relationship only
when all required evidence for that relationship is available and point-in-time
safe. It is not necessary or honest to force every source-instrument pair to
exist.

Use these terminal classes:

| State | Eligible as evidence | Blocks affected relationship | Blocks entire system |
| --- | --- | --- | --- |
| `acquired_verified` | Yes | No | No |
| `approved_proxy_with_basis_risk` | Conditionally | No when policy passes | No |
| `pair_intentionally_not_meaningful` | No | Relationship excluded | No |
| `pre_inception` | No | Relationship excluded or shortened | No |
| `contract_expired_identity_unavailable` | No | Yes for that contract | No unless required by promoted edge |
| `provider_archive_unavailable` | No | Yes for that source-history lane | No unless required by promoted edge |
| `forward_only` | No for historical backtest | Yes historically | No |
| `repairable_provider_gap` | No | Yes | Yes when required by the release candidate |
| `unclassified` | No | Yes | Yes |
| `fabricated_or_fixture` | Never | Yes | Yes |

The backtest may complete with classified gaps. Edge promotion may not use a
gap as evidence.

## 10. Operator Actions

Only three actions require the operator rather than unattended code:

1. approve the final evidence-backed strategy and risk-policy versions;
2. create the new US$100,000 Alpaca Paper account and store its new paper API
   credentials through the existing secret mechanism;
3. approve the clean-epoch cutover and guarded paper release after the final
   checker passes.

No implementation step should ask the operator to paste credentials into a
prompt, runtime JSON file, dashboard, Git commit, or Telegram message.

## 11. Transaction And Rollback Rules

- Archive creation occurs before the active epoch pointer changes.
- The archive is valid only after all file checksums verify.
- The current epoch pointer is written atomically.
- Derived dashboard artifacts are rebuilt only after the pointer changes.
- PaperOps remains locked until broker and dashboard reconciliation pass.
- If reconciliation fails, restore the previous active pointer and keep the new
  broker account unused.
- Never merge records from two broker account fingerprints into one epoch.
- Never roll the trial start timestamp backward.
- Never reuse an idempotency key across epochs.
- Never delete the testing archive during rollback.

## 12. Testing Strategy

### Unit Tests

- currency-native money serialization;
- legacy GBP field compatibility;
- epoch-ID filtering;
- broker account fingerprinting;
- archive checksums;
- atomic pointer writes;
- status signing and verification;
- freshness classification;
- terminal provider-state classification;
- fold-field compatibility;
- proof eligibility.

### Integration Tests

- old account plus new account isolation;
- testing archive plus empty clean epoch;
- broker read-only reconciliation;
- dashboard model regeneration;
- public snapshot publish and retrieval;
- stale publisher fallback;
- service restart during cutover preparation;
- Router-to-PaperOps dry-run handoff;
- current-epoch lifecycle and postmortem attribution.

### Negative Safety Tests

- reject live Alpaca base URL;
- reject non-USD clean account;
- reject non-US$100,000 starting balance outside tolerance;
- reject any open position or existing order on the new account;
- reject same broker fingerprint as the testing epoch;
- reject stale readiness evidence;
- reject incomplete archive checksum set;
- reject archived trade leakage into dashboard or proof;
- reject simulated forward-shadow time;
- reject fixture-backed edge promotion;
- reject dashboard POST, PUT, PATCH, or DELETE authority;
- reject any LLM or quantum broker authority;
- reject paper release when validated edge count is zero.

### Production Tests

- both live aliases serve the expected release;
- local, hosted, and rendered snapshot digests agree;
- Portfolio values agree across header, chart, cards, cash, and composition;
- Trading History contains only current-epoch records;
- Order Monitor matches the new Alpaca Paper account;
- dashboard freshness remains within SLA while the operator service runs;
- stale mode appears when publishing is intentionally interrupted;
- route, accessibility, responsive, and lifecycle tests remain unchanged.

## 13. Canonical Checkers

The program should culminate in:

```text
scripts/check_qadam_clean_epoch_readiness.py
scripts/check_qadam_clean_epoch_cutover.py
scripts/check_qadam_public_status_publisher.py
scripts/check_qadam_dashboard_epoch_isolation.py
scripts/check_qadam_operator_ready_edge_engine.py
```

The final operator-ready checker must consume the first four rather than
duplicating their logic.

## 14. Implementation Order And Stop Conditions

| Order | Phase | May continue when | Must stop when |
| --- | --- | --- | --- |
| 1 | Phase 0 | Baseline and locks are verified | Any unauthorized write or untracked testing artifact appears |
| 2 | Phase 1 | Certification truth is corrected | Checker still contradicts canonical backtest artifacts |
| 3 | Phase 2 | Required producers and sources are fresh | Critical freshness or provider repair remains |
| 4 | Phase 3 | Production snapshot parity passes | Public bridge exposes secrets or command capability |
| 5 | Phase 4 | Research gaps are typed and tests are valid | Leakage, fabricated coverage, or unclassified required data remains |
| 6 | Phase 5 | At least one edge qualifies | Validated edge count remains zero |
| 7 | Phase 6 | Akber, shadow, risk, and Router evidence pass | Missing current context or real-time shadow evidence remains |
| 8 | Phase 7 | Seven-session soak and final certification pass | Service, freshness, or safety soak fails |
| 9 | Phase 8 | New empty US$100,000 Alpaca Paper account verifies | Account, currency, exposure, or credential boundary is wrong |
| 10 | Phase 9 | Archive and cutover invariants pass | Any old record leaks or archive verification fails |
| 11 | Phase 10 | Both production aliases show the clean current epoch | Balance, timestamp, epoch, or history parity fails |
| 12 | Phase 11 | Explicit operator release is recorded | Any paper-only guard is absent |
| 13 | Phase 12 | Real outcomes accumulate | Never force a trade to create evidence |

## 15. Definition Of Done

This plan is complete only when:

1. the operator-ready certification passes from fresh evidence;
2. the production dashboard continuously receives current public-safe data;
3. the current 13-route dashboard structure is unchanged;
4. all decision-critical runtime artifacts are fresh;
5. the backtest is represented truthfully and all negative controls pass;
6. at least one edge satisfies the frozen promotion policy;
7. Akber has complete current context for the eligible setup;
8. real forward-shadow evidence and the seven-session soak pass;
9. the testing epoch is archived with verified checksums;
10. the testing epoch is absent from all public dashboard and proof surfaces;
11. the new Alpaca Paper account and Qadam epoch both begin at US$100,000 USD;
12. all current-epoch positions, orders, closed trades, P&L, drawdown,
    postmortems, and proof records begin at zero;
13. the 30-day paper growth trial starts only at the real cutover timestamp;
14. the canonical PaperOps wrapper is the only paper-order route;
15. live capital, live endpoints, forced trades, unauthorized proof, and
    dashboard or Telegram command authority remain disabled;
16. Qadam runs continuously and can safely choose either trade or wait based on
    evidence rather than an activity target.

The correct completion statement is:

```text
Qadam's testing epoch is preserved in an immutable local archive and excluded
from the public dashboard. The current dashboard structure is unchanged and is
fed by fresh, signed, public-safe operating data. A new US$100,000 Alpaca Paper
epoch is running under the guarded PaperOps route. Qadam may autonomously place
paper trades only when a validated edge and current setup pass every evidence,
Akber, shadow, risk, Router, idempotency, duplicate-exposure, drawdown, Q-CTRL,
and broker-reconciliation gate. It may remain in cash when no setup qualifies.
```
