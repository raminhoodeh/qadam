# PaperOps-2 Explicit Alpaca Paper POST Gate Audit

Date: 2026-05-26

## Scope

PaperOps-2 adds the first explicit real Alpaca paper POST gate for Phase 7
guarded proof orders. It does not change Q7-7's local guarded submit contract.
Instead, it consumes eligible Q7 guarded submit records and keeps the actual
broker POST behind a separate PaperOps gate.

## Implemented

- Added `orchestrator/paperops_alpaca_paper_post.py`.
- Added `scripts/check_paperops_alpaca_paper_post.py`.
- Wired PaperOps readiness to read `data/runtime/paperops_alpaca_paper_post.json`.
- Wired the PaperOps cycle runner to execute the PaperOps-2 checker in
  non-submit mode.
- Exposed PaperOps-2 in the public-safe cockpit status and Mission Control
  system stack.
- Updated the master plan and paper operational plan.

## Gate Conditions

A real Alpaca paper order POST requires all of the following:

- `QADAM_MODE=paper`
- `QADAM_LIVE_CAPITAL_ENABLED=false`
- `QADAM_ALPACA_PAPER_SUBMIT_ENABLED=true`
- endpoint classified as `alpaca_paper_endpoint`
- Alpaca paper API key and secret configured
- eligible Q7 guarded submit record
- source Event Log prewrite reference
- source pre-trade snapshot
- `phase7_demo_proof` idempotency namespace
- Phase 7-scoped idempotency key
- explicit `--submit-paper-order` CLI flag

## Runtime Evidence

Default non-submit check:

- `paperops_alpaca_post_status=disabled_pending_enablement`
- `paperops_alpaca_post_path_available=False`
- `paperops_alpaca_post_eligible_record_count=0`
- `paperops_alpaca_post_called_count=0`
- `paperops_alpaca_post_succeeded_count=0`
- `paperops_alpaca_post_live_endpoint_called_count=0`
- `paperops_alpaca_paper_post_check=ok`

Enabled preview without submit:

- `paperops_alpaca_post_status=ready_no_eligible_order`
- `paperops_alpaca_post_path_available=True`
- `paperops_alpaca_post_endpoint_classification=alpaca_paper_endpoint`
- `paperops_alpaca_post_key_configured=True`
- `paperops_alpaca_post_secret_configured=True`
- `paperops_alpaca_post_execute_requested=False`
- `paperops_alpaca_post_called_count=0`
- `paperops_alpaca_paper_post_check=ok`

Full PaperOps cycle:

- `paper_ops_cycle_command_count=19`
- `paper_ops_cycle_command_passed_count=19`
- `paper_ops_cycle_status=paper_cycle_safe_blocked_pending_enablement`
- `paper_ops_cycle_alpaca_paper_post_gate_status=disabled_pending_enablement`
- `paper_ops_cycle_alpaca_paper_post_called_count=0`
- `paper_ops_cycle_alpaca_paper_post_succeeded_count=0`
- `paper_ops_cycle_alpaca_paper_post_live_endpoint_called_count=0`
- `paper_operational_cycle_check=ok`

Cockpit export:

- `cockpit_status_check=ok`
- public snapshot remains paper mode
- live capital remains disabled
- PaperOps-2 is included in Mission Control system stack

## Safety Result

No Alpaca POST was made during this stage. The current runtime has zero eligible
Q7 guarded submit records, and the explicit `--submit-paper-order` flag was not
used. Live endpoint calls, live capital, raw broker payloads, raw broker order
identifiers, authorization headers, and secrets remained blocked.

## Current Blockers

- `QADAM_PAPER_OPERATIONAL_ENABLED=false`
- `QADAM_ALPACA_PAPER_SUBMIT_ENABLED=false`
- no eligible Q7 guarded submit record
- PaperOps-Q provider consultation is still blocked by Q-CTRL account/product
  access

## Next Stage

PaperOps-3 should add a paper lifecycle poller for submitted Alpaca paper orders.
It should only poll specific PaperOps-2 submitted order references and must keep
live endpoints, live capital, cancellation/replace routes, and proof credit
blocked until later gates explicitly allow them.
