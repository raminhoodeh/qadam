# Qadam Phase 5 Q5-7 Alpaca Paper Adapter Dry-Run Audit - 2026-05-24

## Scope

Q5-7 builds the Alpaca paper adapter dry-run layer without enabling broker
writes. The stage converts Q5-6 staged-paper-order records into public-safe
`broker_submit_receipt` dry-run records with request-preview schemas,
deterministic idempotency previews, duplicate-order guard previews, pre-trade
snapshot schemas, and simulated submit receipt schemas.

## Result

Q5-7 is complete.

The runtime artifact is:

```text
data/runtime/phase5_alpaca_paper_dry_run.json
```

The history and Event Log artifacts are:

```text
data/runtime/phase5_alpaca_paper_dry_run_history.jsonl
data/runtime/phase5_alpaca_paper_dry_run_events.jsonl
```

Current verified state:

```text
phase5_alpaca_paper_dry_run_status=ok
phase5_alpaca_paper_dry_run_record_count=5
phase5_alpaca_paper_dry_run_source_staging_record_count=5
phase5_alpaca_paper_dry_run_source_staged_order_count=0
phase5_alpaca_paper_dry_run_request_preview_count=0
phase5_alpaca_paper_dry_run_receipt_count=0
phase5_alpaca_paper_dry_run_blocked_count=5
phase5_alpaca_paper_dry_run_event_log_written=True
phase5_alpaca_paper_dry_run_event_log_total_events=5
phase5_alpaca_paper_dry_run_validation_error_count=0
phase5_alpaca_paper_dry_run_idempotency_collision_count=0
phase5_alpaca_paper_dry_run_duplicate_guard_collision_count=0
phase5_alpaca_paper_dry_run_broker_post_called_count=0
phase5_alpaca_paper_dry_run_alpaca_post_called_count=0
phase5_alpaca_paper_dry_run_broker_write_allowed_count=0
phase5_alpaca_paper_dry_run_paper_order_submitted_count=0
phase5_alpaca_paper_dry_run_live_endpoint_allowed_count=0
phase5_alpaca_paper_dry_run_live_capital_enabled_count=0
```

Because Q5-6 currently has no staged paper orders, Q5-7 correctly blocks every
dry-run record before request preview or simulated receipt creation.

## Guard Probes

The dedicated check rejects dishonest payloads for:

- live Alpaca endpoint previews
- missing paper mode
- broker POST called
- broker write allowed
- paper order submitted
- live capital enabled
- mutated idempotency key
- duplicate preview-key collision
- request preview POST authority
- simulated receipt POST authority
- Authorization header exposure

## Public Visibility

Q5-7 is now exported through:

- `phase5_alpaca_paper_dry_run` in `data/runtime/cockpit-status.json`
- `phase5_alpaca_paper_dry_run` in
  `landing-page-repo/status/cockpit-status.json`
- Mission Control `system_stack.phase5_alpaca_paper_dry_run`
- Mission Control `phase5_layer_b.alpaca_paper_dry_run_*`
- dashboard Mission Control Q5-7 badge

## Verification

Passing checks:

```bash
.venv/bin/python scripts/check_phase5_alpaca_paper_dry_run.py
.venv/bin/python scripts/check_cockpit_status.py
node --check landing-page-repo/dashboard.js
node --check scripts/check_dashboard_mission_control.js
node --check scripts/check_dashboard_renderer.js
```

Full Phase 5 and dashboard regression checks were also run after the Q5-7
implementation.

## Boundary

Q5-7 does not submit paper orders. It does not call Alpaca POST routes, expose
Authorization headers, allocate broker-usable IDs, write brokers, create
positions, use live endpoints, or enable live capital.

The next stage is Q5-8 - Paper Submit Enablement Gate. Q5-8 still requires its
own explicit paper-submit approval gate before any guarded Alpaca paper POST
path can exist.
