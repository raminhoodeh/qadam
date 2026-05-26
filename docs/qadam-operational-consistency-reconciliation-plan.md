# Qadam Operational Consistency Reconciliation Plan

Date: 2026-05-26

## Purpose

Bring the Qadam whitepaper, protected user guide, dashboard implementation
plans, dashboard rendering/tests, and backend runtime into one coherent
operational story.

The immediate high-priority correction is the paper-account balance. Qadam must
present the paper account as GBP 100,000 available. Older text and contracts
that describe a GBP 1,000 paper/test account must be removed or recast as a
separate risk cap only where that is actually intended.

## Current Runtime Truth

Verified on 2026-05-26:

- `scripts/check_paper_account.py` reports
  `paper_account_current_balance_gbp=100000.0`.
- `scripts/check_cockpit_status.py` reports
  `cockpit_status_paper_current_balance_gbp=100000.0`.
- Qadam is in paper mode.
- Live capital is disabled.
- The cockpit is a read-only operating mirror.
- PaperOps cycle currently passes 34/34 guarded commands.
- PT-10 reports `paper_live_control_plane_certified=True` but
  `paper_live_certified=False`.
- Full paper-live certification is blocked by Q-CTRL product access, the active
  Q-CTRL submit hold, full PaperOps readiness, 30-day Phase 7 completion, and
  Phase 7 demo-proof certification.
- Current Phase 7/PaperOps run is active day 2 of the actual 30-day window,
  with no forced trades and no Phase 7 proof credit.

## Discrepancy Inventory

### Capital And Paper Account

Runtime and deployed status now expose GBP 100,000 as the connected paper
account value, but multiple files still describe GBP 1,000 as the account:

- `cockpit/public/whitepaper/index.html` and
  `landing-page-repo/whitepaper/index.html` say Qadam proves itself in a
  GBP 1,000 paper/test account.
- `docs/qadam-dashboard-implementation-plan.md` repeatedly specifies a
  GBP 1,000 test account and a `first_release_gbp_1000_trial` scope.
- `docs/qadam-dashboard-overhaul-master-implementation-plan.md` still lists
  `GBP 1000 paper account state`.
- `docs/qadam-master-implementation-plan.md` has older historical/current text
  that still says the first-month trade layer and D6 mirror use GBP 1,000.
- `orchestrator/config.py` defaults `QADAM_TRIAL_BALANCE_GBP` to `1000`.
- `orchestrator/paper_account.py` hardcodes
  `first_release_gbp_1000_trial` and explains the policy allocation as
  GBP 1,000 even when Alpaca reports a larger paper balance.
- `scripts/check_paper_account.py` and
  `scripts/check_dashboard_money_panel.js` assert the old GBP 1,000 scope and
  balance.
- `orchestrator/phase7_readiness.py`,
  `orchestrator/phase7_performance_evaluator.py`,
  `orchestrator/phase7_drawdown_risk_sentinel.py`, and related check fixtures
  still use `PHASE7_PAPER_ACCOUNT_STARTING_GBP = 1000.0`.

### Paper-Live State

Some product-facing copy says or implies Qadam paper trades autonomously now.
The operational truth is narrower:

- The active PaperOps runner exists and is scheduled.
- A guarded PT-4 staged paper order exists.
- Paper submit is held by Q-CTRL product-access/consultation state.
- Full paper-live certification is not yet granted.

Marketing/user-facing copy should say "paper-live control plane is ready and
guarded; actual paper submission remains gate-held" until PT-10 certifies full
paper-live operation.

### Phase 7 Window

The current operating rule is 30 consecutive calendar days with 3 proof trades
per week where qualified setups exist. Some older whitepaper text still mentions
the old 90-day framing. That should be removed from current-facing surfaces or
explicitly marked historical.

### Q-CTRL And Quantum Language

The runtime currently reports a classical fallback Head-of-Quant path and a
Q-CTRL product/subscription blocker. User-facing language should not imply
active quantum-hardware execution or successful Q-CTRL consultation. It should
say:

- Head of Quant is a quantum/classical modelling layer.
- Q-CTRL is configured as the required advisory consultation path for
  paper-reality parity.
- Product access is currently blocking successful Q-CTRL consultation.
- Q-CTRL has no broker, risk, execution, or order authority.

### Guide Copy Quality

The markdown user guide has duplicate/stray safety sentences in the Telegram,
member-permissions, and red-flags sections. These are not operationally unsafe,
but they reduce clarity and should be cleaned while reconciling the public copy.

## Reconciliation Principles

1. Backend-derived runtime state wins over static copy.
2. The paper account balance is GBP 100,000.
3. The paper account balance and per-trade/max-notional risk cap must be named
   separately.
4. GBP 1,000 may remain only if it is explicitly a per-order or risk cap, never
   the account balance, available trading capital, paper-account scope, or trial
   allocation.
5. Full paper-live operation must not be described as certified until PT-10 says
   `paper_live_certified=True`.
6. The dashboard must not infer readiness from UI text. It must render backend
   state.
7. Historical audit files can retain old facts, but current plans, current
   guides, active static pages, active checkers, and active runtime defaults
   must align.

## Staged Implementation Plan

### QCR-0 - Source-Of-Truth Contract

Define one current operating truth contract.

Work:

- Add or update a small constants/contract module for active release facts:
  - `PAPER_ACCOUNT_BALANCE_GBP = 100000`
  - `PAPER_ACCOUNT_SCOPE = "first_release_gbp_100000_paper"`
  - `PHASE7_HARNESS_DAY_COUNT = 30`
  - `PHASE7_WEEKLY_PROOF_TRADE_TARGET = 3`
  - `PHASE7_MATURE_CLOSED_TRADE_BENCHMARK = 100`
  - `LIVE_CAPITAL_ENABLED = False`
- Keep `QADAM_PAPER_OPERATIONAL_MAX_NOTIONAL_GBP` separate from available
  paper capital. If it remains GBP 1,000, label it as "single-order/notional
  cap", not account balance.
- Document the current PT-10 state in a short canonical "current operating
  facts" section in the master plan.

Acceptance:

- There is one canonical active balance constant/scope.
- The source-of-truth contract distinguishes paper account balance from
  per-trade cap.

### QCR-1 - Capital Runtime Model Cleanup

Make backend paper-account runtime state agree with GBP 100,000.

Work:

- Change `QADAM_TRIAL_BALANCE_GBP` default from `1000` to `100000`.
- Rename account scope from `first_release_gbp_1000_trial` to
  `first_release_gbp_100000_paper`.
- Update `orchestrator/paper_account.py`:
  - initial snapshot balance
  - Alpaca read-only sync starting balance
  - shadow context `trial_allocation_gbp`
  - `capital_policy`
  - fallback account scope
- Add a non-destructive migration/refresher command that appends a corrected
  latest paper-account snapshot with GBP 100,000 starting/current/equity values
  when no live Alpaca refresh is being run.
- Keep historical JSONL rows intact; the latest snapshot becomes authoritative.

Acceptance:

- `scripts/check_paper_account.py` passes with GBP 100,000.
- Latest `capital.starting_balance_gbp`, `capital.current_balance_gbp`,
  `capital.cash_gbp`, `capital.equity_gbp`, and `capital.peak_equity_gbp`
  are GBP 100,000 when local mirror state is used.
- Connected Alpaca paper mirror remains read-only and may refresh current
  balance from broker data.

### QCR-2 - Phase 7 And Risk Accounting Cleanup

Make Phase 7 proof, drawdown, performance, and staging math use the same
starting paper account balance.

Work:

- Update `PHASE7_PAPER_ACCOUNT_STARTING_GBP` to GBP 100,000.
- Update Phase 7 performance and drawdown calculations to use the central
  balance constant.
- Update Q7 staging pre-trade snapshot fields and all checker fixtures that
  assert `paper_account_starting_gbp`.
- Update drawdown sentinel expectations from GBP 1,000 equity to GBP 100,000
  equity.
- Audit any percentage/risk calculations so a GBP 1,000 max notional cap is
  either retained as a deliberate 1% cap or replaced by a derived cap.

Acceptance:

- `scripts/check_phase7_readiness.py` passes.
- `scripts/check_phase7_proof_order_staging.py` passes.
- `scripts/check_phase7_guarded_alpaca_paper_submit.py` passes.
- `scripts/check_phase7_performance_evaluator.py` passes.
- `scripts/check_phase7_drawdown_risk_sentinel.py` passes.
- No Q7 checker treats GBP 1,000 as the account balance.

### QCR-3 - Dashboard Contract And Renderer Cleanup

Make the dashboard and dashboard tests render the backend paper account state
without old hardcoded labels.

Work:

- Update `landing-page-repo/dashboard.js` fallbacks:
  - account scope
  - capital policy copy
  - Money panel labels
  - Cognition paper-account context fallback
- Update `cockpit/lib/health.ts` fallback `trial_balance_gbp`.
- Update `cockpit/app/dashboard/page.tsx` copy if it still says "GBP X trial".
- Update `scripts/check_dashboard_money_panel.js` and related dashboard checks
  to assert GBP 100,000 and the new scope.
- Refresh `landing-page-repo/status/cockpit-status.json` from the backend after
  runtime checks pass.
- Ensure the line graph/equity timeline uses actual `capital.equity_curve`
  values and not a hidden GBP 1,000 fallback.

Acceptance:

- Dashboard Money panel shows GBP 100,000 current/equity when the backend says
  GBP 100,000.
- Dashboard tests fail if old GBP 1,000 account language returns.
- No dashboard-visible text presents GBP 1,000 as available paper capital.

### QCR-4 - Whitepaper, User Guide, And Static Page Copy Cleanup

Align all current-facing human docs and static pages.

Work:

- Update both whitepaper copies:
  - `cockpit/public/whitepaper/index.html`
  - `landing-page-repo/whitepaper/index.html`
- Replace all GBP 1,000 account references with GBP 100,000 paper account.
- Replace the old 90-day sentence with the active 30-day Phase 7 demo-proof
  rule.
- Reword autonomous paper-trading claims to match PT-10:
  - paper-live control plane is guarded and visible
  - paper submission is held until Q-CTRL and proof gates pass
  - no forced trades
- Update `docs/qadam-user-guide.md` and `landing-page-repo/guide/index.html`
  with:
  - GBP 100,000 paper account wording
  - current PT-10 blocked/full-certification distinction
  - Q-CTRL product-access blocker
  - cleaned duplicate Telegram/member/red-flag copy
- Update current dashboard/master plans that still say GBP 1,000 account.

Acceptance:

- Current-facing docs and pages all say GBP 100,000 paper account.
- They do not imply Qadam is fully paper-live certified while PT-10 is blocked.
- They retain the live-capital-disabled and no-forced-trades boundaries.

### QCR-5 - Operational Status And Certification Language Cleanup

Make "ready", "active", "certified", and "blocked" mean the same thing across
docs, cockpit, and runtime.

Work:

- Add a status vocabulary table to the user guide and dashboard plan:
  - `paper mode`
  - `paper-live control plane certified`
  - `paper-live certified`
  - `paper order staged`
  - `paper order submitted`
  - `Q-CTRL hold`
  - `Phase 7 proof credit`
- Update plan text so "Qadam complete" and "operational" are not used as
  synonyms for "actively submitting paper orders".
- Ensure PT-10, PaperOps-6, and Phase 7 dashboard readouts use the same labels.

Acceptance:

- A new user can tell that the system is running, but paper submission is held.
- "Certified" always identifies a specific backend certification artifact.

### QCR-6 - Consistency Checker

Add a repo-level consistency checker to prevent this drift from returning.

Work:

- Add `scripts/check_qadam_operational_consistency.py`.
- The checker should scan current-facing files and fail on:
  - `£1000 paper account`
  - `GBP 1000 paper account`
  - `first_release_gbp_1000_trial`
  - `PHASE7_PAPER_ACCOUNT_STARTING_GBP = 1000`
  - `QADAM_TRIAL_BALANCE_GBP` defaulting to `1000`
  - current-facing `90-day` demo-proof language
- The checker should allow GBP 1,000 only when the nearby text names it as
  `max notional`, `single-order cap`, or another explicit risk cap.
- Print a clear list of offending file/line pairs.

Acceptance:

- `scripts/check_qadam_operational_consistency.py` passes.
- It fails on a deliberate reintroduction of old account wording.

### QCR-7 - Full Verification And Export

Run the operational and dashboard checks after cleanup.

Required validation:

```bash
.venv/bin/python scripts/check_foundation.py
.venv/bin/python scripts/check_paper_account.py
.venv/bin/python scripts/check_cockpit_status.py
.venv/bin/python scripts/check_paper_live_certification.py
.venv/bin/python scripts/check_paper_operational_cycle.py
.venv/bin/python scripts/check_paperops_30_day_operations.py
.venv/bin/python scripts/check_phase7_readiness.py
.venv/bin/python scripts/check_phase7_drawdown_risk_sentinel.py
node scripts/check_dashboard_money_panel.js
node scripts/check_dashboard_phase7_demo_proof.js
node scripts/check_dashboard_acceptance.js
.venv/bin/python scripts/check_qadam_operational_consistency.py
.venv/bin/python -m compileall orchestrator scripts
git diff --check
```

Then refresh public artifacts:

- export cockpit status
- copy/update `landing-page-repo/status/cockpit-status.json`
- rerun dashboard preflight
- deploy only after the static pages, guide, status JSON, and checkers all
  agree

## Implementation Order

1. QCR-0: source-of-truth contract.
2. QCR-1: capital runtime model.
3. QCR-2: Phase 7/risk accounting.
4. QCR-3: dashboard contract and renderer.
5. QCR-4: whitepaper, guide, and plans.
6. QCR-5: vocabulary/status language.
7. QCR-6: drift-prevention checker.
8. QCR-7: verification, export, and deploy.

This order keeps the backend truth stable before copy and UI are updated. It
also ensures the final static pages cannot pass unless they agree with the
runtime.
