# Qadam Phase 5 Q5E-7 Closed Trade Audit - 2026-05-24

Q5E-7 is complete.

Q5E-7 creates one guarded local closed-trade lifecycle state from the Q5E-6
open position. The target remains `crude_oil_energy_security_disruption`.

This stage does not call Alpaca POST or any broker POST route. It records the
closed-trade lifecycle state locally, removes the current open position from the
paper-account mirror, and keeps postmortem due, live endpoints, live capital,
prediction-market writes, autonomous position mutation, and Phase 7 proof credit
disabled.

## Runtime State

The guarded closed-trade artifact now reports:

```text
status=closed_trade
source_order_ref=q5e5-paper-order-crude_oil_energy_security_disruption
source_position_ref=q5e6-open-position-crude_oil_energy_security_disruption
closed_trade_ref=q5e7-closed-trade-crude_oil_energy_security_disruption
postmortem_status=postmortem_pending_marker
instrument=crude_oil
side=buy
quantity=1.0
realized_pnl_gbp=0.0
r_multiple=0.0
```

Q5-11 now reports:

```text
submitted_order_count=1
mirrored_order_count=1
open_position_count=0
closed_trade_count=1
postmortem_due_count=0
failed_reconciliation_count=0
```

## Safety Boundary

Q5E-7 preserves the core boundary:

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

Q5-14 now advances past submitted-order, mirrored-order, open-position, and
closed-trade missing state, but it still remains blocked:

```text
paper_trade_drill_state=blocked_prerequisites_missing
phase5_paper_trade_drill_exit_gate_passed=False
blockers=execution_adapter_not_staging_ready,postmortem_due_missing
submitted_paper_order_count=1
open_position_count=0
position_open_lifecycle_satisfied=True
closed_trade_count=1
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
closed_trade_count=1
postmortem_due_count=0
live_capital_enabled_count=0
```

## Implementation

- Added `scripts/check_phase5_exit_closed_trade.py`.
- Added the guarded local closed-trade artifact in
  `orchestrator/phase5_position_monitor.py`.
- Added `postmortem_pending_marker` as a valid closed-trade mirror state so
  closed trade and postmortem due can remain separate lifecycle stages.
- Updated Q5-14 and Q5-15 so a closed trade satisfies the prior open-position
  lifecycle step without keeping a fake current open position.
- Updated cockpit and dashboard checks so closed-trade lifecycle evidence is
  allowed while postmortem due, broker writes, live capital, and Phase 7 proof
  credit remain blocked.

## Verification

```bash
.venv/bin/python scripts/check_phase5_exit_closed_trade.py
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

The next required stage is Q5E-8: create the guarded postmortem due marker from
the Q5E-7 closed trade, while keeping broker POST, live capital, autonomous
position mutation, and Phase 7 proof credit disabled.
