# Qadam Phase 5 Q5E-2 Paper Order Staging Audit - 2026-05-24

## Result

Q5E-2 is complete.

Q5E-2 lets Q5-6 create one staged paper-order record from the Q5E-1 eligible
setup. The staged order is for `crude_oil_energy_security_disruption`, routes
only to `alpaca_paper`, and is ready for the later Q5E-3/Q5-7 dry-run preview
stage.

## Implementation

- Updated `orchestrator/phase5_paper_order_staging.py` so an already eligible
  Alpaca-paper risk review can receive deterministic staged-order fields:
  `side=buy`, `quantity=1.0`, `order_type=market`, `time_in_force=day`,
  idempotency material, and an Event Log prewrite fingerprint.
- Kept Q5-6 submission separation intact: `submission_allowed=False`,
  `broker_write_allowed=False`, `broker_post_called=False`,
  `paper_order_submitted=False`, and `live_capital_enabled=False`.
- Updated `scripts/check_phase5_paper_order_staging_gate.py` so the base Q5-6
  validator accepts either the old all-blocked state or the new Q5E state with
  at least one staged order.
- Added `scripts/check_phase5_exit_paper_order_staging.py`.

## Verification

```text
.venv/bin/python scripts/check_phase5_exit_paper_order_staging.py

phase5_exit_paper_order_staging_status=ok
phase5_exit_paper_order_staging_paper_size_eligible_count=1
phase5_exit_paper_order_staging_staged_order_count=1
phase5_exit_paper_order_staging_blocked_count=4
phase5_exit_paper_order_staging_target_record_present=True
phase5_exit_paper_order_staging_target_selected_venue=alpaca_paper
phase5_exit_paper_order_staging_target_order_state=staged_ready_for_dry_run
phase5_exit_paper_order_staging_target_idempotency_key_present=True
phase5_exit_paper_order_staging_target_side=buy
phase5_exit_paper_order_staging_target_quantity=1.0
phase5_exit_paper_order_staging_target_order_type=market
phase5_exit_paper_order_staging_target_time_in_force=day
phase5_exit_paper_order_staging_event_log_total_events=5
phase5_exit_paper_order_staging_broker_write_allowed_count=0
phase5_exit_paper_order_staging_broker_post_called_count=0
phase5_exit_paper_order_staging_paper_order_submitted_count=0
phase5_exit_paper_order_staging_live_capital_enabled_count=0
phase5_exit_paper_order_staging_check=ok
```

Base validators passed after the update:

```text
.venv/bin/python scripts/check_phase5_kill_switch_ledger.py
phase5_kill_switch_q5_3_paper_size_eligible_count=1
phase5_kill_switch_blocking_switch_count=0
phase5_kill_switch_check=ok

.venv/bin/python scripts/check_phase5_execution_adapter_status.py
phase5_execution_adapter_alpaca_read_health=read_only_available
phase5_execution_adapter_alpaca_write_health=blocked_q5_5_status_contract
phase5_execution_adapter_broker_write_allowed_count=0
phase5_execution_adapter_live_capital_enabled_count=0
phase5_execution_adapter_check=ok

.venv/bin/python scripts/check_phase5_paper_order_staging_gate.py
phase5_paper_order_staging_paper_size_eligible_count=1
phase5_paper_order_staging_staged_order_count=1
phase5_paper_order_staging_blocked_count=4
phase5_paper_order_staging_validation_error_count=0
phase5_paper_order_staging_broker_post_called_count=0
phase5_paper_order_staging_paper_order_submitted_count=0
phase5_paper_order_staging_live_capital_enabled_count=0
phase5_paper_order_staging_check=ok
```

## Boundary

Q5E-2 creates a staged paper-order object only. It does not create a dry-run
receipt, submit a paper order, call Alpaca POST, write brokers, mirror a
submitted order, create an open position, close a trade, mark a postmortem due,
or enable live capital.

The next required stage is Q5E-3: let Q5-7 create a dry-run receipt/request
preview from the staged paper order.
