# PaperOps-4 Paper Exit Path Audit

Date: 2026-05-26

## Scope

PaperOps-4 adds the guarded Alpaca paper-only exit path after PaperOps-3. It is
not an autonomous close engine. It consumes PaperOps-3 open-position readbacks
and keeps any paper position close behind a separate env flag, explicit CLI
flag, paper endpoint checks, credential checks, and Event Log prewrite.

## Implemented

- Added `orchestrator/paperops_paper_exit_path.py`.
- Added `scripts/check_paperops_paper_exit_path.py`.
- Added `QADAM_ALPACA_PAPER_EXIT_ENABLED=false` to runtime config and
  `.env.example`.
- Wired PaperOps readiness to read `data/runtime/paperops_paper_exit_path.json`.
- Wired the PaperOps cycle runner to execute the PaperOps-4 checker in non-exit
  mode.
- Exposed PaperOps-4 in public-safe cockpit status and Mission Control system
  stack.
- Updated the paper operational plan and master plan.

## Gate Conditions

A real Alpaca paper position close requires all of the following:

- `QADAM_MODE=paper`
- `QADAM_LIVE_CAPITAL_ENABLED=false`
- `QADAM_ALPACA_PAPER_EXIT_ENABLED=true`
- endpoint classified as `alpaca_paper_endpoint`
- Alpaca paper API key and secret configured
- valid PaperOps-3 lifecycle poller artifact
- PaperOps-3 open-position readback
- source broker identifiers stored only as hashes
- Event Log prewrite
- explicit `--execute-paper-exit` CLI flag

## Runtime Evidence

Default non-exit check:

- `paperops_exit_status=disabled_pending_enablement`
- `paperops_exit_enabled=False`
- `paperops_exit_open_position_readback_count=0`
- `paperops_exit_eligible_record_count=0`
- `paperops_exit_close_called_count=0`
- `paperops_exit_broker_write_called_count=0`
- `paperops_exit_broker_post_called_count=0`
- `paperops_exit_live_endpoint_called_count=0`
- `paperops_paper_exit_path_check=ok`

Enabled preview without execution:

- `paperops_exit_enabled_preview_status=ready_no_exit_candidate`
- `paperops_exit_enabled_preview_execute_requested=False`
- `paperops_exit_enabled_preview_close_called_count=0`

Full PaperOps cycle:

- `paper_ops_cycle_check_command_count=21`
- `paper_ops_cycle_check_command_passed_count=21`
- `paper_ops_cycle_check_status=paper_cycle_safe_blocked_pending_enablement`
- `paper_ops_cycle_check_exit_path_status=disabled_pending_enablement`
- `paper_ops_cycle_check_exit_path_open_position_readback_count=0`
- `paper_ops_cycle_check_exit_path_close_called_count=0`
- `paper_ops_cycle_check_exit_path_broker_write_called_count=0`
- `paper_ops_cycle_check_exit_path_broker_post_called_count=0`
- `paper_ops_cycle_check_exit_path_live_endpoint_called_count=0`
- `paper_operational_cycle_contract_check=ok`

Cockpit export:

- `cockpit_status_check=ok`
- `cockpit_status_paperops_exit_path_status=disabled_pending_enablement`
- `cockpit_status_paperops_exit_path_open_position_readback_count=0`
- `cockpit_status_paperops_exit_path_close_called_count=0`
- `cockpit_status_paperops_exit_path_live_endpoint_called_count=0`

## Safety Result

No Alpaca paper close call was made during this stage. No Alpaca POST, broker
POST, order cancel, position resize, live endpoint call, Q7 lifecycle mutation,
postmortem marker, or Phase 7 proof credit occurred. Raw broker payloads, raw
broker order identifiers, base URLs, authorization headers, and secrets remained
blocked.

## Current Blockers

- `QADAM_PAPER_OPERATIONAL_ENABLED=false`
- `QADAM_ALPACA_PAPER_SUBMIT_ENABLED=false`
- `QADAM_ALPACA_PAPER_EXIT_ENABLED=false`
- no eligible Q7 guarded submit record
- no successful PaperOps-2 submitted paper order
- no PaperOps-3 open-position readback
- PaperOps-Q provider consultation is still blocked by Q-CTRL account/product
  access

## Next Stage

PaperOps-5 should add notification and review wiring for paper lifecycle events.
Telegram may become live-send for paper lifecycle notifications only after a
separate send-test approval, and it must remain unable to approve, reject,
modify, close, resize, or submit trades.
