# Qadam PaperOps Opportunity Scan Cadence Audit

Date: 2026-05-28

## Purpose

This pass adds a separate opportunity-scan cadence so Qadam can look for new or changing paper-trade opportunities more often without increasing broker-submit frequency.

The decision is:

- Opportunity discovery: every 20 minutes.
- Local/frontier model review: hourly or event-gated.
- Paper submission: existing guarded hourly PaperOps runner only.
- Paper lifecycle polling: active only after submitted/open paper-order evidence exists.
- Phase 7 proof/certification: actual calendar preserved; no backfill and no forced trades.

## Implementation

Added `orchestrator/paperops_opportunity_scan_cadence.py`.

Added `scripts/check_paperops_opportunity_scan_cadence.py`.

Wired the public-safe cockpit status contract so `paperops_opportunity_scan_cadence` appears in `cockpit-status.json` and Mission Control.

Updated the dashboard model so Overview shows:

- 20-minute opportunity scan cadence.
- Read-only scanner state.
- Fresh eligible submit count.
- Duplicate submit protection.
- The fact that the scanner cannot submit.
- The hourly guarded PaperOps runner remains the submission transport.

Updated `docs/qadam-master-implementation-plan.md` so the cadence split is retained as an architectural rule.

## Current Runtime Result

Latest local check:

- `paperops_opportunity_scan_cadence_status=scan_ready_candidate_monitoring`
- `opportunity_scan_interval_minutes=20`
- `opportunity_scan_frequency_per_hour=3`
- `model_review_interval_minutes=60`
- `paper_submit_runner_interval_minutes=60`
- `twenty_minute_scan_ready=True`
- `twenty_minute_recurring_scheduler_active=False`
- `recurring_scheduler_status=local_or_external_scheduler_required`
- `codex_cron_minute_interval_supported=False`
- `hourly_paperops_runner_active=True`
- `fresh_eligible_submit_count=0`
- `duplicate_submit_count=1`
- `production_qualified_setup_count=1`
- `observed_trade_candidate_count=5`
- `submitted_paper_order_count=1`
- `trade_submission_allowed_by_scan=False`
- `forced_trades_allowed=False`
- `unsafe_write_counter_total=0`

## Boundary

The 20-minute scanner is not a trading loop. It is a read-only candidate refresh loop. It cannot submit broker orders, close or resize positions, force trades, bypass Signal Integrity, Risk, Execution Policy, Q-CTRL, idempotency, or receipt gates, call live endpoints, enable live capital, or grant Phase 7 proof credit.

## Next Step

If Qadam needs the 20-minute cadence to run automatically on the Mac, install a local scheduler later and audit it separately. The Codex cron automation remains hourly because it is the guarded PaperOps submission runner.
