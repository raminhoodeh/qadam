# Qadam Phase 5 Q5E-6 Open Position Audit - 2026-05-24

Q5E-6 is complete.

Q5E-6 creates one guarded local open-position lifecycle state from the Q5E-5
submitted paper order and local broker receipt. The target remains
`crude_oil_energy_security_disruption`.

This stage does not call Alpaca POST or any broker POST route. It records a
filled mirrored paper order and one local open position for reconciliation, then
keeps close, resize, cancel, replace, live endpoints, live capital,
prediction-market writes, and Phase 7 proof credit disabled.

## Runtime State

The guarded open-position artifact now reports:

```text
status=open_position
source_order_ref=q5e5-paper-order-crude_oil_energy_security_disruption
source_broker_receipt_ref=q5e5-local-broker-receipt-crude_oil_energy_security_disruption
position_ref=q5e6-open-position-crude_oil_energy_security_disruption
order_status_for_mirror=filled
position_status_for_mirror=open_position
instrument=crude_oil
side=buy
quantity=1.0
notional_gbp=5.0
```

Q5-11 now reports:

```text
submitted_order_count=1
mirrored_order_count=1
open_order_count=0
open_position_count=1
closed_trade_count=0
postmortem_due_count=0
```

## Safety Boundary

Q5E-6 preserves the core boundary:

```text
broker_post_called=False
alpaca_post_called=False
external_broker_post_performed=False
live_endpoint_allowed=False
live_capital_enabled=False
position_close_allowed=False
position_resize_allowed=False
order_cancel_allowed=False
order_replace_allowed=False
phase7_proof_credit_allowed=False
```

Q5-14 now advances past submitted-order, mirrored-order, and open-position
missing state, but it still remains blocked:

```text
paper_trade_drill_state=blocked_prerequisites_missing
phase5_paper_trade_drill_exit_gate_passed=False
blockers=closed_trade_missing,execution_adapter_not_staging_ready,postmortem_due_missing
submitted_paper_order_count=1
open_position_count=1
closed_trade_count=0
postmortem_due_count=0
broker_post_called_count=0
live_capital_enabled_count=0
```

Q5-15 remains blocked:

```text
phase5_certified=False
phase5_exit_gate=False
phase6_handoff_allowed=False
phase7_planning_allowed=False
submitted_paper_order_count=1
open_position_count=1
closed_trade_count=0
postmortem_due_count=0
live_capital_enabled_count=0
```

## Implementation

- Added `scripts/check_phase5_exit_open_position.py`.
- Added the guarded local open-position artifact in
  `orchestrator/phase5_position_monitor.py`.
- Updated Q5-8/Q5E-5 idempotency so a previously recorded local submit receipt
  can coexist with the advanced open-position lifecycle state.
- Mirrored the Q5E-6 filled local order and open position into the paper-account
  mirror for Q5-11 reconciliation.
- Updated Q5-11, Q5-14, Q5-15, cockpit, and dashboard checks so they distinguish
  a local open-position lifecycle state from close/resize/cancel or broker-write
  authority.

## Verification

```bash
.venv/bin/python scripts/check_phase5_exit_submitted_paper_order.py
.venv/bin/python scripts/check_phase5_exit_paper_submit_path.py
.venv/bin/python scripts/check_phase5_exit_open_position.py
.venv/bin/python scripts/check_phase5_paper_submit_enablement.py
.venv/bin/python scripts/check_phase5_position_monitor.py
.venv/bin/python scripts/check_phase5_paper_trade_drill.py
.venv/bin/python scripts/check_phase5_certification.py
.venv/bin/python scripts/check_phase5_system_map.py
.venv/bin/python scripts/check_cockpit_status.py
node scripts/check_dashboard_mission_control.js
node scripts/check_dashboard_phase5_system_map.js
node scripts/check_dashboard_phase5_paper_trade_drill.js
node scripts/check_dashboard_phase5_certification.js
```

All checks passed.

## Next Stage

The next required stage is Q5E-7: create the guarded closed-trade lifecycle
state from the Q5E-6 open position, while keeping broker POST, live capital,
autonomous close/resize/cancel authority, and Phase 7 proof credit disabled.
