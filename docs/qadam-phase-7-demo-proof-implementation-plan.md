# Qadam Phase 7 - Demo Proof Implementation Plan

Date: 2026-05-25

This document breaks Phase 7 - Demo Proof into modular stages that can be
implemented one at a time after Q6-17 certification.

## 1. Entry State

Phase 7 planning is allowed because Q6-17 reports:

- `phase6_certified=True`
- `phase6_exit_gate=True`
- `phase7_demo_proof_planning_allowed=True`
- `phase7_proof_credit_allowed=False`
- `phase5_test_trades_count_for_phase7=False`
- `certification_blocker_count=0`

Q6-17 allows Phase 7 planning only. It does not grant Phase 7 proof credit,
does not let Phase 5 test trades count as proof, does not enable live capital,
and does not enable live broker or prediction-market writes.

## 2. Updated Phase 7 Operating Rules

The Phase 7 proof run is now a 30-day demo-proof harness rather than the older
90-day harness.

Operating rules:

- 30 consecutive calendar days.
- GBP 1000 Alpaca paper/test proof surface.
- Three proof trades per proof week where qualified setups exist.
- No forced trades.
- A no-trade week is valid only when the qualified-setup ledger shows fewer
  than three qualified setups, or all qualified setups are blocked by explicit
  policy/risk/venue/killswitch gates.
- Zero manual trade-level approvals, rejections, sizing edits, exits, or
  overrides.
- Max drawdown remains capped at 20%.
- Every proof trade must have pre-trade evidence, policy/risk approval,
  lifecycle records, broker/paper receipt, position monitoring, exit record,
  and postmortem.
- Phase 5 lifecycle test trades are excluded from Phase 7 proof.
- Q6 deferred learning artifacts are context only and do not count as proof.
- The 100 closed-trade benchmark remains the mature statistical benchmark.
  If the 30-day run finishes with fewer than 100 closed proof trades, the run
  can be operationally complete but must be marked statistically immature.
- All saved proof data remains local-first on the MacBook unless a later
  explicit export gate is approved.

## 3. Adjustments From Prior Work

Phase 7 should reuse the proven Phase 5 and Phase 6 contracts instead of
inventing a parallel system:

- Use Phase 5 Layer B as the execution/lifecycle template, but start a new
  Phase 7 proof namespace so Phase 5 test trades cannot become proof.
- Use Q6-17 certification as the entry gate.
- Use Q6 postmortem/review fields as evidence requirements, while preserving
  the Q6 deferral boundary: no Q6 learning action is approved or applied.
- Keep Yahoo Finance and Preference/PREF supplemental-only unless a Phase 7
  source gate explicitly promotes a role for a specific proof decision.
- Keep Q-CTRL/quantum output as shadow annotation unless a future hardware gate
  explicitly permits provider calls or quantum-gated proof setups.
- Track qualified setups separately from executed proof trades so the weekly
  target cannot create forced trades.
- Make dashboard/cockpit state backend-derived only, with no UI-inferred proof
  readiness.

## 4. Stage Map

| Stage | Name | Objective | Authority |
| --- | --- | --- | --- |
| Q7-0 | Re-Entry And Operating Rules Gate | Validate Q6-17 and freeze the 30-day/3-qualified-trades-per-week proof contract. | Planning gate only |
| Q7-1 | Artifact Schema And Proof Authority Ledger | Define Phase 7 artifact contracts, authority flags, unsafe counters, source refs, and Event Log categories. | Schema only |
| Q7-2 | 30-Day Calendar Harness | Create the 30 consecutive calendar day run ledger, proof-week indexing, start/end policy, and pause/invalid-run handling. | Harness scheduling only |
| Q7-3 | Qualified Setup Ledger | Define what counts as a qualified setup and log every eligible, blocked, and no-trade setup with source/provenance refs. | Read-only eligibility |
| Q7-4 | Weekly Proof Cadence Tracker | Enforce three proof trades per proof week only where qualified setups exist; document no-forced-trade exceptions. | Cadence accounting |
| Q7-5 | Test-Mode Auto-Approval Router | Let qualifying setups pass after all policy/risk/source/kill-switch gates without manual trade-level approval. | Test-mode approval only |
| Q7-6 | Proof Order Staging And Idempotency | Convert auto-approved setups into Phase 7 proof paper-order objects with deterministic idempotency. | Staging only |
| Q7-7 | Guarded Alpaca Paper Submit Path | Submit only eligible Phase 7 proof paper orders through the guarded paper path; keep live capital disabled. | Paper submit only |
| Q7-8 | Proof Lifecycle Monitor | Mirror submitted orders, open positions, exits, and closed trades into a Phase 7 proof lifecycle ledger. | Read/write proof lifecycle |
| Q7-9 | Proof Postmortem Contract | Require a postmortem due marker and postmortem packet for every closed proof trade. | Postmortem required |
| Q7-10 | Performance Evaluator | Calculate expectancy after costs, R-multiples, win rate, Sharpe/Sortino where meaningful, and drawdown. | Evaluation only |
| Q7-11 | Drawdown And Risk Sentinel | Enforce the 20% max drawdown cap and freeze new proof trades when breached. | Risk halt only |
| Q7-12 | Override Detector | Detect manual approvals, trade edits, exits, broker-side intervention, or missing autonomy evidence. | Clean-sample guard |
| Q7-13 | Source And Signal Funnel Evidence | Report source quorum, Akber filter passage, Signal Integrity, Risk Agent, Execution Policy, and kill-switch chain per proof trade. | Evidence only |
| Q7-14 | 100-Trade Maturity Tracker | Track closed proof trades against the mature 100-trade benchmark and mark statistical immaturity when needed. | Maturity accounting |
| Q7-15 | Cockpit And Mission Control Visibility | Expose Phase 7 day count, weekly target, qualified setups, proof trades, drawdown, overrides, and maturity state from backend artifacts. | Visibility only |
| Q7-16 | Weekly Review Pack | Generate weekly proof review packets without allowing Fund Managers to modify individual proof trades. | Review packet only |
| Q7-17 | 30-Day Demo Proof Certification | Certify the 30-day run, proof integrity, drawdown, postmortems, clean-sample status, and maturity classification. | Certification only |
| Q7-18 | Live Promotion Review Flow | Prepare Ramin's structured live-promotion review and cooling-off workflow; keep live credentials disabled until later approval. | Review only |

## 5. Stage Details

### Q7-0 - Re-Entry And Operating Rules Gate

Objective: prove Phase 7 can start with the updated 30-day operating contract
without opening proof credit or live capital.

Work:

- Read Q6-17 certification.
- Require `phase7_demo_proof_planning_allowed=True`.
- Require `phase7_proof_credit_allowed=False`.
- Require `phase5_test_trades_count_for_phase7=False`.
- Freeze 30 consecutive calendar days.
- Freeze three proof trades per week where qualified setups exist.
- Freeze no-forced-trades and local-first proof storage.
- Keep all proof execution, proof credit, broker write, prediction-market
  write, crypto-perps write, and live-capital authority disabled.

Acceptance:

- Q7-0 reports `phase7_re_entry_gate_passed=True`.
- Q7-0 reports `phase7_harness_day_count=30`.
- Q7-0 reports `phase7_weekly_proof_trade_target=3`.
- Q7-0 reports `phase7_no_forced_trades=True`.
- Q7-0 reports `phase7_proof_credit_allowed=False`.
- Q7-0 allows only Q7-1 schema/authority work.

Expected files:

- `orchestrator/phase7_readiness.py`
- `scripts/check_phase7_readiness.py`
- `docs/qadam-phase-7-q7-0-re-entry-operating-rules-audit-YYYY-MM-DD.md`

### Q7-1 - Artifact Schema And Proof Authority Ledger

Objective: define the common Phase 7 contract before any proof harness logic
can run.

Work:

- Define Phase 7 schema versioning.
- Define proof artifact types: calendar day, proof week, qualified setup,
  proof candidate, auto-approval decision, staged proof order, broker receipt,
  proof lifecycle event, postmortem marker, performance metric, drawdown halt,
  override event, maturity snapshot, weekly review, and certification.
- Define authority flags and unsafe counters.
- Define Event Log categories.
- Define source/provenance requirements.
- Add dishonest-payload probes for false proof credit, Phase 5 proof reuse,
  hidden live capital, manual override masking, and UI-inferred readiness.

Acceptance:

- All authority defaults are false.
- Source refs are relative and public-safe.
- No proof trade, proof credit, broker POST, or live-capital authority exists.

Expected files:

- `orchestrator/phase7_artifacts.py`
- `scripts/check_phase7_artifact_schema.py`
- `docs/qadam-phase-7-q7-1-artifact-schema-authority-ledger-audit-YYYY-MM-DD.md`

Status after implementation:

- Q7-1 is complete in
  `docs/qadam-phase-7-q7-1-artifact-schema-authority-ledger-audit-2026-05-25.md`.
- Q7-1 defines 19 Phase 7 proof artifact contracts, 19 statuses, 20
  authority flags, 14 unsafe counters, and 18 Event Log categories.
- All sample authority defaults remain false and all unsafe counters remain
  zero.
- Yahoo Finance and Preference/PREF MCP remain supplemental data sources for
  Phase 7 proof. They cannot satisfy source quorum alone, cannot grant proof
  credit, and cannot replace broker/lifecycle truth.
- Q-CTRL remains shadow annotation only, Phase 5 lifecycle records remain
  excluded from Phase 7 proof, and Q6 deferred-learning records remain context
  only.
- No proof trade, proof credit, broker POST, live endpoint, manual trade-level
  override, or live capital authority is granted by Q7-1.
- The current explicit build target is Q7-2 - 30-Day Calendar Harness.

### Q7-2 - 30-Day Calendar Harness

Objective: create the proof calendar before any proof trades can count.

Work:

- Create a 30-day run ledger with day numbers 1-30.
- Define proof weeks as day 1-7, 8-14, 15-21, 22-28, and 29-30.
- Mark week 5 as a partial proof week with prorated observation, not forced
  trade pressure.
- Define run start, run end, invalidation, restart, pause, and outage rules.
- Require all calendar days to be represented, including no-trade days.

Acceptance:

- 30 calendar-day records exist.
- Consecutive-day coverage is validated.
- No trade is created by the calendar harness.

Expected files:

- `orchestrator/phase7_calendar_harness.py`
- `scripts/check_phase7_calendar_harness.py`
- `docs/qadam-phase-7-q7-2-calendar-harness-audit-YYYY-MM-DD.md`

Status after implementation:

- Q7-2 is complete in
  `docs/qadam-phase-7-q7-2-calendar-harness-audit-2026-05-25.md`.
- Q7-2 writes `data/runtime/phase7_calendar_harness.json` with 30 scheduled
  calendar-day records from 2026-05-25 through 2026-06-23.
- Q7-2 defines five proof weeks: days 1-7, 8-14, 15-21, 22-28, and partial
  observation week 29-30.
- Consecutive calendar coverage is validated, week 5 is marked partial
  observation only, and partial-week trade pressure is disabled.
- Q7-2 keeps `calendar_harness_started=False`, `phase7_demo_day_count=0`,
  `qualified_setup_count=0`, `proof_trade_count=0`,
  `closed_proof_trade_count=0`, and `unsafe_write_counter_total=0`.
- No proof trade, proof credit, broker POST, live endpoint, manual trade-level
  override, or live capital authority is granted by Q7-2.
- The current explicit build target is Q7-3 - Qualified Setup Ledger.

### Q7-3 - Qualified Setup Ledger

Objective: separate qualified setup availability from actual proof trades.

Work:

- Define a qualified setup as one that passes source quorum, Akber filter,
  Signal Integrity, Risk Agent paper sizing, Execution Policy, kill-switches,
  venue availability, and broker-paper readiness.
- Record all eligible, blocked, expired, and no-trade setup decisions.
- Carry supplemental source roles forward: Yahoo Finance and Preference/PREF
  can corroborate but not satisfy source quorum alone.
- Reject Phase 5 test lifecycle records as proof setups.

Acceptance:

- Every proof trade links to a qualified setup.
- Every no-trade week has a setup ledger explanation.
- No setup can qualify from one supplemental source only.

Expected files:

- `orchestrator/phase7_qualified_setup_ledger.py`
- `scripts/check_phase7_qualified_setup_ledger.py`
- `docs/qadam-phase-7-q7-3-qualified-setup-ledger-audit-YYYY-MM-DD.md`

Status after implementation:

- Q7-3 is complete in
  `docs/qadam-phase-7-q7-3-qualified-setup-ledger-audit-2026-05-25.md`.
- Q7-3 writes `data/runtime/phase7_qualified_setup_ledger.json`.
- Q7-3 records 30 daily setup decisions and five weekly setup summaries against
  the Q7-2 calendar.
- Because the harness is scheduled but not started, Q7-3 records
  `qualified_setup_count=0`, `eligible_setup_count=0`, `proof_trade_count=0`,
  and no-trade explanations for all 30 calendar days and all five proof weeks.
- Q7-3 explicitly rejects Phase 5 lifecycle evidence as Phase 7 proof by
  recording `rejected_phase5_lifecycle_count=1` and
  `phase5_test_trades_count_for_phase7=False`.
- Yahoo Finance and Preference/PREF MCP remain supplemental-only; no setup can
  qualify from supplemental-only evidence.
- No qualified setup creation, auto-approval, proof order, proof trade, proof
  credit, broker POST, live endpoint, manual trade-level override, or live
  capital authority is granted by Q7-3.
- The current explicit build target is Q7-4 - Weekly Proof Cadence Tracker.

### Q7-4 - Weekly Proof Cadence Tracker

Objective: enforce the three-qualified-trades-per-week discipline without
forcing trades.

Work:

- Track each proof week target as `min(3, qualified_setup_count)`.
- Track executed proof trades, policy-blocked qualified setups, expired
  qualified setups, and no-trade rationale.
- Flag missed qualified setups when qualified setups exist but proof action did
  not occur and no blocker explains it.

Acceptance:

- Weekly cadence is satisfied when three proof trades occur, or when fewer than
  three qualified setups exist and all are accounted for.
- Weekly cadence fails if qualified setups are ignored without a backend blocker.

Expected files:

- `orchestrator/phase7_weekly_cadence.py`
- `scripts/check_phase7_weekly_cadence_tracker.py`
- `docs/qadam-phase-7-q7-4-weekly-cadence-tracker-audit-YYYY-MM-DD.md`

Status after implementation:

- Q7-4 is complete in
  `docs/qadam-phase-7-q7-4-weekly-cadence-tracker-audit-2026-05-25.md`.
- Q7-4 writes `data/runtime/phase7_weekly_cadence_tracker.json`.
- Q7-4 records five weekly cadence records from the Q7-3 setup ledger.
- Because Q7-3 has zero qualified setups, every weekly target is
  `min(3, 0)=0`.
- Q7-4 reports `weekly_cadence_satisfied_count=5`,
  `weekly_cadence_failed_count=0`, `weekly_target_total=0`,
  `proof_trade_count=0`, `missed_qualified_setup_count=0`, and
  `no_forced_trade_exception_count=5`.
- Q7-4 does not force trades and does not create proof trades. It records that
  the cadence is satisfied because no qualified setup exists and every week has
  an explicit no-trade explanation.
- No auto-approval, proof order, proof trade, proof credit, broker POST, live
  endpoint, manual trade-level override, or live capital authority is granted
  by Q7-4.
- The current explicit build target is Q7-5 - Test-Mode Auto-Approval Router.

### Q7-5 - Test-Mode Auto-Approval Router

Objective: remove manual trade-level approval while preserving policy controls.

Work:

- Create test-mode auto-approval records for qualified setups.
- Require all prior gates to pass.
- Allow kill-switches, strategy toggles, and governance comments to affect
  future policy, but not individual trade approval.
- Record why any setup is rejected, deferred, or expired.

Acceptance:

- Fund Manager trade-level approval count is zero.
- Manual approval/rejection/resize/exit attempts mark the sample contaminated.
- Auto-approval cannot bypass risk or kill switches.

Expected files:

- `orchestrator/phase7_test_mode_auto_approval.py`
- `scripts/check_phase7_test_mode_auto_approval_router.py`
- `docs/qadam-phase-7-q7-5-test-mode-auto-approval-router-audit-YYYY-MM-DD.md`

Status after implementation:

- Q7-5 is complete in
  `docs/qadam-phase-7-q7-5-test-mode-auto-approval-router-audit-2026-05-25.md`.
- Q7-5 writes `data/runtime/phase7_test_mode_auto_approval_router.json`.
- Q7-5 grants only the narrow
  `phase7_test_mode_auto_approval_allowed=True` authority and leaves proof
  order staging, broker POST, proof trade execution, proof credit, manual
  trade-level override, and live capital authority disabled.
- Because Q7-3 has zero qualified setups, Q7-5 records one rejected Phase 5
  carryover candidate, zero qualified setup decisions, and zero auto-approved
  setups.
- Q7-5 reports `fund_manager_trade_level_approval_count=0`,
  `manual_trade_level_override_attempt_count=0`, `sample_contaminated=False`,
  `risk_or_kill_switch_bypass_count=0`, `proof_order_staged_count=0`,
  `proof_trade_count=0`, `unsafe_write_counter_total=0`, and
  `blocker_count=0`.
- Q7-5 permits strategy toggles, kill-switch changes, and governance comments
  to affect future policy only; they cannot approve, reject, resize, or exit an
  individual proof trade.
- The current explicit build target is Q7-6 - Proof Order Staging And
  Idempotency.

### Q7-6 - Proof Order Staging And Idempotency

Objective: create Phase 7 proof paper-order records without reusing Phase 5
IDs or proof state.

Work:

- Convert auto-approved setups into staged proof paper orders.
- Create Phase 7 idempotency keys.
- Require pre-trade snapshot and Event Log prewrite.
- Keep prediction-market, crypto-perps, and live endpoint writes disabled.

Acceptance:

- Staged proof order exists only for auto-approved qualified setups.
- Duplicate order probes are rejected.
- Phase 5 order IDs cannot be reused.

Expected files:

- `orchestrator/phase7_proof_order_staging.py`
- `scripts/check_phase7_proof_order_staging.py`
- `docs/qadam-phase-7-q7-6-proof-order-staging-audit-YYYY-MM-DD.md`

Status after implementation:

- Q7-6 is complete in
  `docs/qadam-phase-7-q7-6-proof-order-staging-audit-2026-05-25.md`.
- Q7-6 writes `data/runtime/phase7_proof_order_staging.json`.
- Q7-6 grants only Phase 7 test-mode auto-approval continuity and narrow proof
  order staging authority. Broker POST, Alpaca POST, proof trade submission,
  proof trade execution, proof credit, prediction-market writes, crypto-perps
  writes, live endpoints, manual trade-level overrides, and live capital remain
  disabled.
- Because Q7-5 has zero auto-approved setups, Q7-6 records one blocked staging
  decision and zero staged proof orders.
- Q7-6 reports `proof_order_staging_allowed=True`,
  `phase7_proof_order_staging_allowed=True`,
  `q7_7_guarded_alpaca_paper_submit_path_stage_allowed=True`,
  `staging_decision_record_count=1`, `staged_order_count=0`,
  `blocked_staging_decision_count=1`, `auto_approved_setup_count=0`,
  `idempotency_key_count=0`, `duplicate_idempotency_key_count=0`,
  `phase5_order_id_reuse_count=0`, `event_log_prewrite_ready_count=0`,
  `event_log_prewrite_written_count=0`,
  `pre_trade_snapshot_present_count=0`, `proof_trade_count=0`,
  `unsafe_write_counter_total=0`, and `blocker_count=0`.
- Q7-6 validates the positive staged-order contract with a synthetic Q7
  auto-approved setup, then rejects duplicate idempotency keys, non-approved
  staged orders, Phase 5 idempotency/order ID reuse, missing Event Log
  prewrite, missing pre-trade snapshot, submit authority, broker authority,
  live-capital authority, market-write authority, proof credit, and manual
  override probes.
- The current explicit build target is Q7-7 - Guarded Alpaca Paper Submit Path.

### Q7-7 - Guarded Alpaca Paper Submit Path

Objective: submit eligible Phase 7 proof orders to the Alpaca paper route while
keeping live capital disabled.

Work:

- Reuse the guarded submit pattern from Phase 5, but require Phase 7 proof
  namespace and Q7 auto-approval.
- Record broker paper request and broker paper receipt.
- Preserve broker POST counters and endpoint class in the artifact.
- Reject live endpoint URLs and live-account credentials.

Acceptance:

- Paper submit can occur only from Phase 7 staged proof orders.
- Live capital remains false.
- Broker receipt is linked to idempotency, setup, source refs, and Event Log.

Expected files:

- `orchestrator/phase7_guarded_alpaca_paper_submit.py`
- `scripts/check_phase7_guarded_alpaca_paper_submit.py`
- `docs/qadam-phase-7-q7-7-guarded-alpaca-paper-submit-audit-YYYY-MM-DD.md`

Status after implementation:

- Q7-7 is complete in
  `docs/qadam-phase-7-q7-7-guarded-alpaca-paper-submit-audit-2026-05-25.md`.
- Q7-7 writes `data/runtime/phase7_guarded_alpaca_paper_submit_path.json`.
- Q7-7 exposes the guarded Alpaca paper submit path for Phase 7 staged proof
  orders only. It requires the `phase7_demo_proof` idempotency namespace,
  Event Log prewrite, pre-trade snapshot, paper endpoint classification, and
  paper account mode.
- Q7-7 grants only narrow Phase 7 proof trade submission-path authority.
  Broker POST, Alpaca POST, proof trade execution, proof lifecycle writes,
  proof credit, prediction-market writes, crypto-perps writes, live endpoints,
  manual trade-level overrides, and live capital remain disabled.
- Because Q7-6 has zero staged proof orders, Q7-7 records zero submit records,
  zero submitted paper orders, and zero broker receipts.
- Q7-7 reports `phase7_guarded_submit_status=ready_no_submit_candidates`,
  `phase7_guarded_submit_stage_status=guarded_alpaca_submit_path_ready_no_staged_orders`,
  `phase7_guarded_submit_path_available=True`,
  `phase7_guarded_submit_phase7_proof_trade_submission_allowed=True`,
  `phase7_guarded_submit_q7_8_lifecycle_stage_allowed=True`,
  `phase7_guarded_submit_source_staged_order_count=0`,
  `phase7_guarded_submit_submit_record_count=0`,
  `phase7_guarded_submit_submitted_paper_order_count=0`,
  `phase7_guarded_submit_broker_receipt_record_count=0`,
  `phase7_guarded_submit_broker_post_called_count=0`,
  `phase7_guarded_submit_alpaca_post_called_count=0`,
  `phase7_guarded_submit_proof_trade_count=0`,
  `phase7_guarded_submit_phase7_proof_credit_allowed=False`,
  `phase7_guarded_submit_live_capital_enabled=False`,
  `phase7_guarded_submit_unsafe_write_counter_total=0`, and
  `phase7_guarded_submit_blocker_count=0`.
- Q7-7 validates a positive synthetic local paper-submit receipt, then rejects
  duplicate idempotency keys, Phase 5 idempotency/order ID reuse, live
  endpoints, exposed live credentials, broker POST counters, missing broker
  receipt links, proof credit, live capital, market-write authority, manual
  override authority, Preference/PREF or Q-CTRL source-role inflation, local
  path leakage, and disabled stage gates.
- The current explicit build target is Q7-8 - Proof Lifecycle Monitor.

### Q7-8 - Proof Lifecycle Monitor

Objective: mirror the full proof trade lifecycle.

Work:

- Record submitted order, filled/open position, exit intent, closed trade, and
  reconciliation status.
- Detect missing broker echo, duplicate fills, stale positions, and failed
  reconciliation.
- Keep autonomous position mutation bounded by paper proof policy.

Acceptance:

- Every proof order has lifecycle state.
- Every closed proof trade is linked to setup, approval, order, receipt, and
  position records.
- Failed reconciliation blocks proof certification.

Expected files:

- `orchestrator/phase7_proof_lifecycle_monitor.py`
- `scripts/check_phase7_proof_lifecycle_monitor.py`
- `docs/qadam-phase-7-q7-8-proof-lifecycle-monitor-audit-YYYY-MM-DD.md`

Status after implementation:

- Q7-8 is complete in
  `docs/qadam-phase-7-q7-8-proof-lifecycle-monitor-audit-2026-05-25.md`.
- Q7-8 writes `data/runtime/phase7_proof_lifecycle_monitor.json`.
- Q7-8 mirrors only local Phase 7 proof lifecycle state from Q7-7 guarded
  Alpaca paper-submit receipts. It can record submitted order, open position,
  exit intent, and closed proof trade lifecycle records, and it blocks
  certification when reconciliation fails.
- Q7-8 grants only narrow Phase 7 proof lifecycle write authority. Broker
  POST, Alpaca POST, proof trade execution authority, postmortem writes, proof
  credit, prediction-market writes, crypto-perps writes, live endpoints,
  manual trade-level overrides, and live capital remain disabled.
- Because Q7-7 has zero submitted paper orders, Q7-8 records zero lifecycle
  events, zero mirrored submitted orders, zero open positions, zero exit
  intents, and zero closed proof trades.
- Q7-8 reports `phase7_lifecycle_status=ready_no_lifecycle_events`,
  `phase7_lifecycle_stage_status=proof_lifecycle_monitor_ready_no_submitted_orders`,
  `phase7_lifecycle_q7_9_postmortem_stage_allowed=True`,
  `phase7_lifecycle_write_allowed=True`,
  `phase7_lifecycle_source_submitted_paper_order_count=0`,
  `phase7_lifecycle_event_count=0`,
  `phase7_lifecycle_mirrored_submitted_order_count=0`,
  `phase7_lifecycle_open_position_count=0`,
  `phase7_lifecycle_exit_intent_count=0`,
  `phase7_lifecycle_closed_proof_trade_count=0`,
  `phase7_lifecycle_proof_trade_count=0`,
  `phase7_lifecycle_postmortem_due_count=0`,
  `phase7_lifecycle_missing_broker_echo_count=0`,
  `phase7_lifecycle_duplicate_fill_count=0`,
  `phase7_lifecycle_stale_position_count=0`,
  `phase7_lifecycle_failed_reconciliation_count=0`,
  `phase7_lifecycle_phase7_proof_credit_allowed=False`,
  `phase7_lifecycle_live_capital_enabled=False`,
  `phase7_lifecycle_broker_post_called_count=0`,
  `phase7_lifecycle_alpaca_post_called_count=0`,
  `phase7_lifecycle_unsafe_write_counter_total=0`, and
  `phase7_lifecycle_blocker_count=0`.
- Q7-8 validates positive synthetic submitted-order and closed-trade lifecycle
  records, then rejects missing broker echo, duplicate fill accounting
  mismatches, stale-position accounting mismatches, failed reconciliation that
  does not block, premature postmortem-due markers, proof credit, broker POST,
  live capital, market-write authority, manual override authority, Phase 5
  idempotency reuse, Preference/PREF or Q-CTRL source-role inflation, local
  path leakage, and disabled stage gates.
- The current explicit build target is Q7-9 - Proof Postmortem Contract.

### Q7-9 - Proof Postmortem Contract

Objective: require postmortems for every closed proof trade.

Work:

- Create postmortem due marker on close.
- Reuse Q6 postmortem packet contracts, with Phase 7 proof refs.
- Require postmortem packet within 24 hours.
- Track missing, late, reviewed, and explicitly deferred postmortems.

Acceptance:

- `postmortem_due_count` equals closed proof trade count.
- Certification fails if a closed proof trade lacks postmortem coverage.

Expected files:

- `orchestrator/phase7_proof_postmortem_contract.py`
- `scripts/check_phase7_proof_postmortem_contract.py`
- `docs/qadam-phase-7-q7-9-proof-postmortem-contract-audit-YYYY-MM-DD.md`

Status after implementation:

- Q7-9 is complete in
  `docs/qadam-phase-7-q7-9-proof-postmortem-contract-audit-2026-05-25.md`.
- Q7-9 writes `data/runtime/phase7_proof_postmortem_contract.json`.
- Q7-9 creates postmortem-due coverage only from Q7-8 closed proof trades and
  attaches the Q6 13-section source-cited packet contract to every due marker.
- Q7-9 grants only narrow Phase 7 postmortem write authority for due markers
  and packet templates. Postmortem approval, learning writes, Knowledge Graph
  writes, model/trust updates, policy/strategy mutation, proof credit, broker
  POST, Alpaca POST, prediction-market writes, crypto-perps writes, live
  endpoints, manual trade-level overrides, and live capital remain disabled.
- Because Q7-8 has zero closed proof trades, Q7-9 records zero postmortem
  records, zero due markers, zero packet templates, zero reviewed packets, zero
  explicit deferrals, zero late packets, and zero missing coverage.
- Q7-9 reports `phase7_postmortem_status=ready_no_closed_trades`,
  `phase7_postmortem_stage_status=proof_postmortem_contract_ready_no_closed_trades`,
  `phase7_postmortem_source_lifecycle_status=ready_no_lifecycle_events`,
  `phase7_postmortem_q7_10_performance_stage_allowed=True`,
  `phase7_postmortem_write_allowed=True`,
  `phase7_postmortem_source_closed_proof_trade_count=0`,
  `phase7_postmortem_record_count=0`,
  `phase7_postmortem_due_count=0`,
  `phase7_postmortem_due_marker_created_count=0`,
  `phase7_postmortem_packet_required_count=0`,
  `phase7_postmortem_packet_template_count=0`,
  `phase7_postmortem_packet_submitted_count=0`,
  `phase7_postmortem_reviewed_count=0`,
  `phase7_postmortem_explicitly_deferred_count=0`,
  `phase7_postmortem_late_count=0`,
  `phase7_postmortem_missing_count=0`,
  `phase7_postmortem_missing_coverage_count=0`,
  `phase7_postmortem_phase7_proof_credit_allowed=False`,
  `phase7_postmortem_live_capital_enabled=False`,
  `phase7_postmortem_broker_post_called_count=0`,
  `phase7_postmortem_alpaca_post_called_count=0`,
  `phase7_postmortem_unsafe_write_counter_total=0`, and
  `phase7_postmortem_blocker_count=0`.
- Q7-9 validates positive synthetic due-marker, reviewed-packet, and
  explicitly deferred packet contracts, then rejects missing due markers, late
  tracking mismatches, narrative-only packets, uncited assertions, postmortem
  approval, learning/Knowledge Graph writes, proof credit, broker POST, live
  capital, market-write authority, manual override authority, Preference/PREF
  or Q-CTRL source-role inflation, local path leakage, disabled stage gates,
  and assertion-field drift.
- The current explicit build target is Q7-10 - Performance Evaluator.

### Q7-10 - Performance Evaluator

Objective: evaluate the proof sample without overstating maturity.

Work:

- Compute expectancy after estimated costs.
- Compute R-multiple distribution, win rate, average win/loss, max drawdown,
  Sharpe/Sortino where sample size permits, and rolling seven-day/30-day
  expectancy.
- Classify metrics as mature or statistically immature.

Acceptance:

- Expectancy is positive after costs for certification.
- Drawdown is within 20%.
- Sample maturity is explicitly labelled.

Implementation status:

- Q7-10 is complete in
  `docs/qadam-phase-7-q7-10-performance-evaluator-audit-2026-05-25.md`.
- Q7-10 writes `data/runtime/phase7_performance_evaluator.json`.
- Q7-10 consumes the Q7-9 postmortem contract and evaluates only
  postmortem-covered closed Q7 proof trades.
- Because Q7-9 currently has zero closed proof trades, Q7-10 records zero
  evaluated trades and labels the sample as `no_sample` rather than mature.
- Q7-10 reports `phase7_performance_status=ready_no_closed_trades`,
  `phase7_performance_stage_status=performance_evaluator_ready_no_closed_trades`,
  `phase7_performance_q7_11_drawdown_stage_allowed=True`,
  `phase7_performance_write_allowed=True`,
  `phase7_performance_closed_proof_trade_count=0`,
  `phase7_performance_evaluated_trade_count=0`,
  `phase7_performance_metric_record_count=0`,
  `phase7_performance_expectancy_after_costs_gbp=None`,
  `phase7_performance_expectancy_after_costs_positive=False`,
  `phase7_performance_win_rate=None`,
  `phase7_performance_loss_rate=None`,
  `phase7_performance_max_drawdown_fraction_observed=0.0`,
  `phase7_performance_drawdown_within_cap=True`,
  `phase7_performance_statistical_maturity_state=no_sample`,
  `phase7_performance_phase7_proof_credit_allowed=False`,
  `phase7_performance_live_capital_enabled=False`,
  `phase7_performance_broker_post_called_count=0`,
  `phase7_performance_alpaca_post_called_count=0`,
  `phase7_performance_unsafe_write_counter_total=0`, and
  `phase7_performance_blocker_count=0`.
- Q7-10 validates positive synthetic performance samples and rejects missing
  R-multiples, net-P&L mismatches, negative expectancy blocker drift, drawdown
  blocker drift, maturity-label drift, cost-count drift, proof credit, broker
  POST, live capital, market writes, manual overrides, supplemental source
  credit drift, local path leakage, and disabled Q7-10/Q7-11 gates.
- The current explicit build target is Q7-11 - Drawdown And Risk Sentinel.

### Q7-11 - Drawdown And Risk Sentinel

Objective: enforce the 20% drawdown cap.

Work:

- Track peak equity, current equity, realized/unrealized drawdown, and breach
  state.
- Freeze new proof trades when drawdown exceeds 20%.
- Record risk-halt event and review requirement.

Acceptance:

- Drawdown breach blocks new proof trades.
- Certification fails if drawdown cap is breached and unresolved.

Implementation status:

- Q7-11 is complete in
  `docs/qadam-phase-7-q7-11-drawdown-risk-sentinel-audit-2026-05-25.md`.
- Q7-11 writes `data/runtime/phase7_drawdown_risk_sentinel.json`.
- Q7-11 consumes the Q7-10 performance evaluator and records the drawdown
  sentinel separately from the performance metrics.
- Because Q7-10 currently has zero closed proof trades, Q7-11 records zero
  drawdown, no active risk halt, and no proof-trade freeze.
- Q7-11 reports `phase7_drawdown_status=ready_no_drawdown_sample`,
  `phase7_drawdown_stage_status=drawdown_sentinel_ready_no_closed_trades`,
  `phase7_drawdown_q7_12_override_stage_allowed=True`,
  `phase7_drawdown_risk_halt_write_allowed=True`,
  `phase7_drawdown_risk_halt_active=False`,
  `phase7_drawdown_new_proof_trades_frozen=False`,
  `phase7_drawdown_new_proof_order_staging_allowed=True`,
  `phase7_drawdown_new_proof_trade_submission_allowed=True`,
  `phase7_drawdown_source_closed_proof_trade_count=0`,
  `phase7_drawdown_source_evaluated_trade_count=0`,
  `phase7_drawdown_current_equity_gbp=1000.0`,
  `phase7_drawdown_peak_equity_gbp=1000.0`,
  `phase7_drawdown_realized_drawdown_fraction_observed=0.0`,
  `phase7_drawdown_unrealized_drawdown_fraction_observed=0.0`,
  `phase7_drawdown_max_drawdown_fraction_observed=0.0`,
  `phase7_drawdown_drawdown_within_cap=True`,
  `phase7_drawdown_drawdown_state=no_sample_within_cap`,
  `phase7_drawdown_phase7_certification_blocked_by_drawdown=False`,
  `phase7_drawdown_phase7_proof_credit_allowed=False`,
  `phase7_drawdown_live_capital_enabled=False`,
  `phase7_drawdown_broker_post_called_count=0`,
  `phase7_drawdown_alpaca_post_called_count=0`,
  `phase7_drawdown_unsafe_write_counter_total=0`, and
  `phase7_drawdown_blocker_count=0`.
- Q7-11 validates synthetic within-cap and breach samples and rejects breaches
  that do not freeze new proof trades, no-breach false freezes, certification
  blocker drift, drawdown-cap drift, proof credit, broker POST, live capital,
  market writes, manual overrides, supplemental source-credit drift, local path
  leakage, disabled Q7-11/Q7-12 gates, and missing unrealized mark-to-market
  coverage for open positions.
- The current explicit build target is Q7-12 - Override Detector.

### Q7-12 - Override Detector

Objective: protect the clean proof sample.

Work:

- Detect manual trade-level approvals, rejects, quantity edits, price edits,
  exits, broker-side changes, and unlinked lifecycle records.
- Separate allowed governance comments/strategy toggles from trade-level
  intervention.
- Mark sample as contaminated when intervention occurs.

Acceptance:

- `manual_trade_level_override_count=0` is required.
- Contamination blocks certification unless run is restarted.

Implementation status:

- Q7-12 is complete in
  `docs/qadam-phase-7-q7-12-override-detector-audit-2026-05-25.md`.
- Q7-12 writes `data/runtime/phase7_override_detector.json`.
- Q7-12 consumes Q7-11 drawdown state plus Q7 auto-approval and lifecycle
  evidence to detect manual trade-level intervention and sample contamination.
- Q7-12 separates allowed governance comments, strategy toggles, and
  kill-switch feedback from trade-level approvals, rejects, edits, exits, and
  broker-side or unlinked lifecycle intervention.
- Because the current Phase 7 runtime has no trade-level interventions, Q7-12
  reports `phase7_override_status=clean_no_overrides`,
  `phase7_override_stage_status=override_detector_clean_no_interventions`,
  `phase7_override_q7_13_signal_stage_allowed=True`,
  `phase7_override_detection_write_allowed=True`,
  `phase7_override_sample_contaminated=False`,
  `phase7_override_clean_sample=True`,
  `phase7_override_count=0`,
  `phase7_override_record_count=0`,
  `phase7_override_manual_trade_level_override_count=0`,
  `phase7_override_broker_side_intervention_count=0`,
  `phase7_override_unlinked_lifecycle_record_count=0`,
  `phase7_override_governance_feedback_record_count=3`,
  `phase7_override_governance_feedback_trade_level_intervention_count=0`,
  `phase7_override_new_proof_trades_frozen=False`,
  `phase7_override_new_proof_order_staging_allowed=True`,
  `phase7_override_new_proof_trade_submission_allowed=True`,
  `phase7_override_phase7_certification_blocked_by_override=False`,
  `phase7_override_run_restart_required=False`,
  `phase7_override_phase7_proof_credit_allowed=False`,
  `phase7_override_live_capital_enabled=False`,
  `phase7_override_broker_post_called_count=0`,
  `phase7_override_alpaca_post_called_count=0`,
  `phase7_override_unsafe_write_counter_total=0`, and
  `phase7_override_blocker_count=0`.
- Q7-12 validates governance-only records, manual-override contamination,
  broker-side intervention contamination, unlinked-lifecycle contamination, and
  inherited drawdown freezes, and rejects contamination that does not block
  certification or freeze new proof trades, governance feedback that
  contaminates the sample, count drift, proof credit, broker POST, live
  capital, market writes, manual override authority, supplemental source-credit
  drift, local path leakage, and disabled Q7-12/Q7-13 gates.
- The current explicit build target is Q7-13 - Source And Signal Funnel
  Evidence.

### Q7-13 - Source And Signal Funnel Evidence

Objective: prove each trade came from the intended Qadam chain.

Work:

- Link each proof setup to source quorum, source trust, Akber filter, Signal
  Integrity, Risk Agent, Execution Policy, kill-switch state, paper sizing,
  and broker readiness.
- Record missing corroboration, challenge-only Preference/PREF context, Yahoo
  supplemental-only context, and quantum shadow annotations when present.

Acceptance:

- Each proof trade has a complete decision chain.
- No proof trade can be certified from private priors alone.

Implementation status:

- Q7-13 is complete in
  `docs/qadam-phase-7-q7-13-source-signal-funnel-evidence-audit-2026-05-25.md`.
- Q7-13 adds `orchestrator/phase7_signal_funnel_evidence.py` and
  `scripts/check_phase7_signal_funnel_evidence.py`.
- Q7-13 writes `data/runtime/phase7_signal_funnel_evidence.json`.
- Q7-13 links every Phase 7 proof trade, when present, back to source quorum,
  source trust, Akber filter, Signal Integrity, Risk Agent, Execution Policy,
  kill-switch state, paper sizing, and broker readiness evidence.
- Q7-13 keeps Preference/PREF as challenge-only context, Yahoo Finance as
  supplemental-only market context, and Q-CTRL as shadow annotation only.
  None of those contexts can satisfy source quorum or count as proof.
- Because the current Phase 7 runtime has no proof trades, Q7-13 reports
  `phase7_signal_evidence_status=ready_no_proof_trades`,
  `phase7_signal_evidence_stage_status=signal_funnel_evidence_ready_no_proof_trades`,
  `phase7_signal_evidence_source_override_status=clean_no_overrides`,
  `phase7_signal_evidence_source_override_sample_contaminated=False`,
  `phase7_signal_evidence_q7_14_maturity_stage_allowed=True`,
  `phase7_signal_evidence_write_allowed=True`,
  `phase7_signal_evidence_record_count=0`,
  `phase7_signal_evidence_complete_decision_chain_count=0`,
  `phase7_signal_evidence_missing_decision_chain_count=0`,
  `phase7_signal_evidence_private_priors_only_proof_trade_count=0`,
  `phase7_signal_evidence_phase7_certification_blocked_by_signal_evidence=False`,
  `phase7_signal_evidence_private_prior_counts_as_proof=False`,
  `phase7_signal_evidence_phase7_proof_credit_allowed=False`,
  `phase7_signal_evidence_live_capital_enabled=False`,
  `phase7_signal_evidence_broker_post_called_count=0`,
  `phase7_signal_evidence_alpaca_post_called_count=0`,
  `phase7_signal_evidence_unsafe_write_counter_total=0`, and
  `phase7_signal_evidence_blocker_count=0`.
- Q7-13 validates complete-chain proof records, valid certification-blocked
  missing-chain records, valid certification-blocked private-prior records, and
  rejects missing/private evidence that does not block certification,
  Preference/PREF proof credit, Yahoo source-quorum or proof credit, Q-CTRL
  execution-truth or proof credit, proof credit, broker POST, live capital,
  market writes, manual override authority, source-posture drift, local path
  leakage, and disabled Q7-13/Q7-14 gates.
- Q7-14 and Q7-15 have since completed; the current explicit build target is
  Q7-16 - Weekly Review Pack.

### Q7-14 - 100-Trade Maturity Tracker

Objective: preserve the mature benchmark without forcing trades into a 30-day
window.

Work:

- Count closed proof trades.
- Track mature benchmark progress toward 100.
- Mark run as statistically immature if 30 days complete but fewer than 100
  closed proof trades exist.
- Prevent statistical immaturity from being hidden by dashboard language.

Acceptance:

- 100-trade benchmark is visible.
- Fewer than 100 closed proof trades blocks "mature" status but does not erase
  the 30-day operational result.

Implementation status:

- Q7-14 is complete in
  `docs/qadam-phase-7-q7-14-maturity-tracker-audit-2026-05-25.md`.
- Q7-14 adds `orchestrator/phase7_maturity_tracker.py` and
  `scripts/check_phase7_maturity_tracker.py`.
- Q7-14 writes `data/runtime/phase7_maturity_tracker.json`.
- Q7-14 consumes Q7-13 source/signal evidence and the Q7 calendar harness to
  count closed proof trades, expose the 100-trade maturity benchmark, compute
  maturity progress, and keep 30-day operational proof separate from
  mature-sample status.
- Because the current Phase 7 runtime has no closed proof trades and the
  30-day proof run has not completed, Q7-14 reports
  `phase7_maturity_status=ready_no_closed_trades`,
  `phase7_maturity_stage_status=maturity_tracker_ready_no_closed_trades`,
  `phase7_maturity_source_signal_status=ready_no_proof_trades`,
  `phase7_maturity_q7_15_cockpit_visibility_stage_allowed=True`,
  `phase7_maturity_write_allowed=True`,
  `phase7_maturity_closed_proof_trade_count=0`,
  `phase7_maturity_mature_benchmark=100`,
  `phase7_maturity_progress_fraction=0.0`,
  `phase7_maturity_closed_trades_remaining_to_mature=100`,
  `phase7_maturity_phase7_mature_benchmark_met=False`,
  `phase7_maturity_phase7_mature_status_blocked=True`,
  `phase7_maturity_phase7_statistically_immature=False`,
  `phase7_maturity_phase7_statistical_immaturity_hidden=False`,
  `phase7_maturity_phase7_30_day_run_complete=False`,
  `phase7_maturity_completed_calendar_day_count=0`,
  `phase7_maturity_phase7_30_day_operational_result_erased_by_immaturity=False`,
  `phase7_maturity_phase7_certification_blocked_by_maturity=True`,
  `phase7_maturity_phase7_proof_credit_allowed=False`,
  `phase7_maturity_live_capital_enabled=False`,
  `phase7_maturity_broker_post_called_count=0`,
  `phase7_maturity_alpaca_post_called_count=0`,
  `phase7_maturity_unsafe_write_counter_total=0`, and
  `phase7_maturity_blocker_count=0`.
- Q7-14 validates no-sample, in-progress immature, 30-day immature, and
  100-trade mature probes, and rejects hidden immaturity, under-100 mature
  claims, 30-day under-100 maturity that does not block certification, erased
  operational results, forced trades, proof credit, broker POST, live capital,
  market writes, manual override authority, source-posture drift, local path
  leakage, and disabled Q7-14/Q7-15 gates.
- Q7-16 has since completed; the current explicit build target is Q7-17 -
  30-Day Demo Proof Certification.

### Q7-15 - Cockpit And Mission Control Visibility

Objective: expose Phase 7 proof state from backend artifacts only.

Work:

- Add public-safe Phase 7 cockpit status.
- Show day count, proof week, qualified setups, proof trades, missed qualified
  setups, drawdown, overrides, postmortems, expectancy, and maturity.
- Show live capital disabled and Phase 5 proof reuse blocked.
- Add dashboard parity checks and XSS/public-safety checks.

Acceptance:

- Dashboard cannot infer readiness from frontend state.
- Public status contains no raw payloads, local paths, secrets, or broker ids.

Implementation status:

- Q7-15 is complete in
  `docs/qadam-phase-7-q7-15-cockpit-mission-control-visibility-audit-2026-05-25.md`.
- Q7-15 adds `orchestrator/phase7_cockpit_visibility.py`,
  `scripts/check_phase7_cockpit_visibility.py`, and
  `scripts/check_dashboard_phase7_demo_proof.js`, then wires the public status
  into `orchestrator/cockpit_status.py`, `landing-page-repo/dashboard.js`, and
  `scripts/check_dashboard_renderer.js`.
- Q7-15 writes `data/runtime/phase7_cockpit_visibility.json` and exports
  `phase7_demo_proof` into the public cockpit snapshot and static dashboard
  status.
- Q7-15 consumes the Q7-0 through Q7-14 runtime artifacts to expose day count,
  proof week, qualified setups, missed qualified setups, staged/submitted
  paper orders, broker receipts, mirrored submitted orders, open/closed proof
  trades, postmortems, expectancy, drawdown, overrides, source/signal evidence,
  and 100-trade maturity state from backend artifacts only.
- Current state is
  `phase7_cockpit_visibility_status=visible`,
  `phase7_cockpit_visibility_stage_status=phase7_demo_proof_visible`,
  `phase7_cockpit_visibility_backend_derived=True`,
  `phase7_cockpit_visibility_display_derived_from_backend=True`,
  `phase7_cockpit_visibility_dashboard_uses_backend_status=True`,
  `phase7_cockpit_visibility_ui_inferred_readiness_count=0`,
  `phase7_cockpit_visibility_source_artifact_count=14`,
  `phase7_cockpit_visibility_source_missing_count=0`,
  `phase7_cockpit_visibility_source_validation_error_count=0`,
  `phase7_cockpit_visibility_completed_calendar_day_count=0`,
  `phase7_cockpit_visibility_phase7_harness_day_count=30`,
  `phase7_cockpit_visibility_proof_week_count=5`,
  `phase7_cockpit_visibility_qualified_setup_count=0`,
  `phase7_cockpit_visibility_missed_qualified_setup_count=0`,
  `phase7_cockpit_visibility_submitted_paper_order_count=0`,
  `phase7_cockpit_visibility_broker_receipt_count=0`,
  `phase7_cockpit_visibility_open_position_count=0`,
  `phase7_cockpit_visibility_closed_proof_trade_count=0`,
  `phase7_cockpit_visibility_postmortem_due_count=0`,
  `phase7_cockpit_visibility_drawdown_within_cap=True`,
  `phase7_cockpit_visibility_override_count=0`,
  `phase7_cockpit_visibility_sample_contaminated=False`,
  `phase7_cockpit_visibility_complete_decision_chain_count=0`,
  `phase7_cockpit_visibility_maturity_state=no_sample`,
  `phase7_cockpit_visibility_mature_benchmark=100`,
  `phase7_cockpit_visibility_maturity_progress_fraction=0.0`,
  `phase7_cockpit_visibility_phase7_mature_benchmark_met=False`,
  `phase7_cockpit_visibility_phase7_mature_status_blocked=True`,
  `phase7_cockpit_visibility_phase7_statistical_immaturity_hidden=False`,
  `phase7_cockpit_visibility_phase5_test_trades_count_for_phase7=False`,
  `phase7_cockpit_visibility_phase7_proof_credit_allowed=False`,
  `phase7_cockpit_visibility_live_capital_enabled=False`,
  `phase7_cockpit_visibility_broker_post_called_count=0`,
  `phase7_cockpit_visibility_alpaca_post_called_count=0`,
  `phase7_cockpit_visibility_unsafe_write_counter_total=0`, and
  `phase7_cockpit_visibility_q7_16_weekly_review_pack_stage_allowed=True`.
- Q7-15 validates a future valid paper lifecycle visibility probe with paper
  broker POST counts present, and rejects UI-inferred readiness,
  display/backend mismatches, local path refs, hidden immaturity, proof credit,
  live capital, Phase 5 proof reuse, raw public payload leakage, and a disabled
  Q7-16 gate.

### Q7-16 - Weekly Review Pack

Objective: create review packets without contaminating proof trades.

Work:

- Generate weekly summaries for Fund Managers.
- Include missed setups, no-trade rationale, drawdown, postmortems, overrides,
  source health, and funnel conversion.
- Allow comments about future policy changes only.

Acceptance:

- Weekly review exists for each proof week.
- Trade-level intervention remains zero.

Implementation status:

- Q7-16 is complete in
  `docs/qadam-phase-7-q7-16-weekly-review-pack-audit-2026-05-25.md`.
- Q7-16 adds `orchestrator/phase7_weekly_review_pack.py` and
  `scripts/check_phase7_weekly_review_pack.py`.
- Q7-16 writes `data/runtime/phase7_weekly_review_pack.json`,
  `data/runtime/phase7_weekly_review_pack_history.jsonl`, and
  `data/runtime/phase7_weekly_review_pack_events.jsonl`.
- Q7-16 creates one read-only review packet for each of the five proof weeks
  in the 30-day harness. Each packet includes cadence, missed setup/no-trade
  rationale, drawdown, postmortem, override, source-health, funnel-conversion,
  signal-evidence, and maturity summaries from backend artifacts only.
- Fund Manager comments are explicitly limited to future-policy review. Q7-16
  rejects current-trade comment scope, individual trade approval/rejection,
  order or position edits, Phase 7 proof credit, live capital, broker/market
  writes, UI-inferred readiness, and raw/private payload exposure.
- Current state is `phase7_weekly_review_status=read_only`,
  `phase7_weekly_review_stage_status=weekly_review_pack_created`,
  `phase7_weekly_review_source_visibility_status=visible`,
  `phase7_weekly_review_source_visibility_backend_derived=True`,
  `phase7_weekly_review_source_visibility_ui_inferred_readiness_count=0`,
  `phase7_weekly_review_source_artifact_count=11`,
  `phase7_weekly_review_source_missing_count=0`,
  `phase7_weekly_review_source_validation_error_count=0`,
  `phase7_weekly_review_proof_week_count=5`,
  `phase7_weekly_review_review_pack_record_count=5`,
  `phase7_weekly_review_packet_created=True`,
  `phase7_weekly_review_packet_created_count=5`,
  `phase7_weekly_review_all_proof_weeks_have_review_packet=True`,
  `phase7_weekly_review_future_policy_comment_allowed=True`,
  `phase7_weekly_review_trade_level_intervention_allowed=False`,
  `phase7_weekly_review_trade_level_intervention_count=0`,
  `phase7_weekly_review_no_trade_rationale_count=5`,
  `phase7_weekly_review_phase7_proof_credit_allowed=False`,
  `phase7_weekly_review_live_capital_enabled=False`,
  `phase7_weekly_review_broker_post_called_count=0`,
  `phase7_weekly_review_alpaca_post_called_count=0`,
  `phase7_weekly_review_unsafe_write_counter_total=0`, and
  `phase7_weekly_review_q7_17_certification_stage_allowed=True`.

### Q7-17 - 30-Day Demo Proof Certification

Objective: decide whether the 30-day proof run is operationally clean.

Work:

- Require all 30 calendar days.
- Require weekly cadence satisfaction under the qualified-setup rule.
- Require positive expectancy after costs.
- Require drawdown within 20%.
- Require zero manual trade-level overrides.
- Require postmortems for all closed proof trades.
- Require source/signal chain completeness.
- Require explicit maturity classification.

Acceptance:

- `phase7_demo_proof_certified=True` only when all conditions pass.
- `phase7_mature_benchmark_met=True` only at 100 closed proof trades.
- `phase7_statistically_immature=True` when 30 days pass with fewer than 100
  closed proof trades.
- Live capital remains disabled after certification.

Implementation status:

- Q7-17 is complete in
  `docs/qadam-phase-7-q7-17-demo-proof-certification-audit-2026-05-25.md`.
- Q7-17 adds `orchestrator/phase7_certification.py` and
  `scripts/check_phase7_certification.py`.
- Q7-17 writes `data/runtime/phase7_certification.json`,
  `data/runtime/phase7_certification_history.jsonl`, and
  `data/runtime/phase7_certification_events.jsonl`.
- After the actual demo-proof run start, Q7-17 treats
  `data/runtime/phase7_demo_proof_run.json` as authoritative for the live
  `completed_calendar_day_count` and `phase7_30_day_run_complete` state.
- Q7-17 is fail-closed and preserves the 30-day operational result separately
  from the 100 closed proof-trade maturity benchmark. A clean 30-day run below
  100 closed proof trades can be labelled operationally clean and statistically
  immature, but `phase7_demo_proof_certified=True` remains blocked until the
  maturity benchmark is met.
- Current state is `phase7_certification_status=blocked`,
  `phase7_certification_stage_status=phase7_certification_blocked_run_incomplete`,
  `phase7_certification_phase7_demo_proof_certified=False`,
  `phase7_certification_phase7_demo_proof_exit_gate=False`,
  `phase7_certification_30_day_operational_result_clean=False`,
  `phase7_certification_30_day_operational_result_preserved=True`,
  `phase7_certification_phase7_30_day_run_complete=False`,
  `phase7_certification_completed_calendar_day_count=0`,
  `phase7_certification_proof_week_count=5`,
  `phase7_certification_weekly_cadence_satisfied_count=5`,
  `phase7_certification_weekly_cadence_failed_count=0`,
  `phase7_certification_weekly_review_packet_created_count=5`,
  `phase7_certification_evaluated_trade_count=0`,
  `phase7_certification_expectancy_after_costs_positive=False`,
  `phase7_certification_drawdown_within_cap=True`,
  `phase7_certification_manual_trade_level_override_count=0`,
  `phase7_certification_closed_proof_trade_count=0`,
  `phase7_certification_postmortem_missing_count=0`,
  `phase7_certification_source_signal_chains_complete=True`,
  `phase7_certification_maturity_state=no_sample`,
  `phase7_certification_phase7_mature_benchmark_met=False`,
  `phase7_certification_phase7_statistically_immature=False`,
  `phase7_certification_phase7_statistical_immaturity_hidden=False`,
  `phase7_certification_phase5_test_trades_count_for_phase7=False`,
  `phase7_certification_phase7_proof_credit_allowed=False`,
  `phase7_certification_live_capital_enabled=False`,
  `phase7_certification_broker_post_called_count=0`,
  `phase7_certification_alpaca_post_called_count=0`,
  `phase7_certification_unsafe_write_counter_total=0`,
  `phase7_certification_gate_count=9`,
  `phase7_certification_gate_passed_count=6`,
  `phase7_certification_gate_blocked_count=3`,
  `phase7_certification_blocker_count=3`, and
  `phase7_certification_q7_18_live_promotion_review_stage_allowed=False`.
- Current blockers are `phase7_30_day_run_incomplete`,
  `positive_expectancy_after_costs_missing`, and
  `phase7_maturity_benchmark_not_met`.

### Q7-18 - Live Promotion Review Flow

Objective: prepare, but not execute, a live-promotion decision.

Work:

- Create Ramin's structured live-promotion review packet.
- Include full Phase 7 evidence, maturity state, drawdown, overrides,
  postmortems, source health, and operational incidents.
- Enforce cooling-off period.
- Keep live credentials disabled until a later explicit approval gate.

Acceptance:

- Live-promotion review can be drafted after Phase 7 certification.
- Live credentials, live broker writes, and live capital remain disabled.

Implementation status:

- Q7-18 is complete in
  `docs/qadam-phase-7-q7-18-live-promotion-review-flow-audit-2026-05-25.md`.
- Q7-18 adds `orchestrator/phase7_live_promotion_review.py` and
  `scripts/check_phase7_live_promotion_review.py`.
- Q7-18 writes `data/runtime/phase7_live_promotion_review.json`,
  `data/runtime/phase7_live_promotion_review_history.jsonl`, and
  `data/runtime/phase7_live_promotion_review_events.jsonl`.
- Q7-18 prepares Ramin's live-promotion review packet only after Q7-17 reports
  `phase7_demo_proof_certified=True` and
  `q7_18_live_promotion_review_stage_allowed=True`.
- Current state is `phase7_live_promotion_status=blocked`,
  `phase7_live_promotion_stage_status=live_promotion_review_blocked_phase7_not_certified`,
  `phase7_live_promotion_source_certification_status=blocked`,
  `phase7_live_promotion_phase7_demo_proof_certified=False`,
  `phase7_live_promotion_q7_18_live_promotion_review_stage_allowed=False`,
  `phase7_live_promotion_review_packet_draft_allowed=False`,
  `phase7_live_promotion_review_packet_created=False`,
  `phase7_live_promotion_review_state=blocked_pending_phase7_certification`,
  `phase7_live_promotion_cooling_off_required=True`,
  `phase7_live_promotion_cooling_off_complete=False`,
  `phase7_live_promotion_live_promotion_approval_state=not_requested`,
  `phase7_live_promotion_live_credentials_enabled=False`,
  `phase7_live_promotion_live_credentials_loaded=False`,
  `phase7_live_promotion_live_capital_enabled=False`,
  `phase7_live_promotion_live_broker_write_allowed=False`,
  `phase7_live_promotion_phase7_proof_credit_allowed=False`,
  `phase7_live_promotion_broker_post_called_count=0`,
  `phase7_live_promotion_alpaca_post_called_count=0`,
  `phase7_live_promotion_unsafe_write_counter_total=0`,
  `phase7_live_promotion_blocker_count=2`.
- Current Q7-18 blockers are `phase7_certification_not_certified` and
  `q7_18_live_promotion_review_not_allowed`.
- Q7-18 validates a future post-certification read-only review packet probe,
  then rejects early Q7-18 handoff, packet creation while blocked, live
  credential loading, live capital, broker/market writes, proof credit,
  cooling-off bypass, approval-before-later-gate, public payload leakage, and
  source display/backend drift.
- Q7-18 is review-only. It grants no live-promotion approval, live
  credentials, live capital, broker POST, Alpaca POST, prediction-market
  write, crypto-perps write, proof credit, Phase 5 proof reuse, or UI-inferred
  readiness authority.

## 6. Verification Baseline

Each stage should run its own checker plus the active safety baseline:

```bash
.venv/bin/python scripts/check_phase6_certification.py
.venv/bin/python scripts/check_phase7_readiness.py
.venv/bin/python scripts/check_phase7_cockpit_visibility.py
.venv/bin/python scripts/check_phase7_weekly_review_pack.py
.venv/bin/python scripts/check_phase7_certification.py
.venv/bin/python scripts/check_phase7_live_promotion_review.py
.venv/bin/python scripts/check_phase7_demo_proof_run.py
.venv/bin/python scripts/check_cockpit_status.py
node scripts/check_dashboard_phase6_certification.js
node scripts/check_dashboard_phase6_learning_loop.js
node scripts/check_dashboard_phase7_demo_proof.js
```

As later Phase 7 stages add certification or promotion visibility, add their
dashboard checks to this baseline.

## 7. Current Next Step

Phase 7 staged implementation through Q7-18 is structurally complete.

Operational update after demo-proof run start:

- The actual 30 consecutive calendar day run is active in
  `data/runtime/phase7_demo_proof_run.json`.
- The run started on 2026-05-25 America/Chicago and is scheduled to end after
  2026-06-23.
- `scripts/run_phase7_demo_proof_harness.py` records one operational pass
  without backfilling, simulating elapsed time, forcing trades, granting proof
  credit, or enabling live capital.
- Q7-17 certification now consumes
  `data/runtime/phase7_demo_proof_run.json` as the authoritative future
  certification clock, so the eventual 30-day closeout must come from the
  actual run ledger.
- Current state is `phase7_demo_run_status=running`,
  `phase7_demo_run_state=active`,
  `phase7_demo_run_active_day_number=1`,
  `phase7_demo_run_completed_calendar_day_count=0`,
  `phase7_demo_run_phase7_30_day_run_complete=False`,
  `phase7_demo_run_qualified_setups_exist=False`,
  `phase7_demo_run_qualified_setup_count=0`,
  `phase7_demo_run_submitted_paper_order_count=0`,
  `phase7_demo_run_closed_proof_trade_count=0`,
  `phase7_demo_run_collection_state=active_no_qualified_setups`,
  `phase7_demo_run_phase7_proof_credit_allowed=False`,
  `phase7_demo_run_live_capital_enabled=False`,
  `phase7_demo_run_broker_post_called_count=0`,
  `phase7_demo_run_alpaca_post_called_count=0`, and
  `phase7_demo_run_unsafe_write_counter_total=0`.
- Today has no Q7-qualified setup at the time of the first operational pass, so
  the no-trade rationale is
  `no_q7_qualified_setups_detected_for_active_observation`.

The next operational step is to keep the recurring runner active through the
30-day window, collect proof trades only where qualified setups exist, and
rerun Q7-17 and Q7-18 as evidence accrues. Phase 8 or live-capital work remains
blocked in the current runtime.
