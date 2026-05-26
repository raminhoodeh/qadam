# Qadam Phase 5 Q5E-8 Postmortem Due Audit - 2026-05-24

Q5E-8 is complete.

Q5E-8 creates one guarded local postmortem-due marker from the Q5E-7 closed
trade. The target remains `crude_oil_energy_security_disruption`.

This stage does not call Alpaca POST or any broker POST route. It updates the
local paper-account mirror so the closed trade is marked `postmortem_due`, and
keeps broker writes, live endpoints, live capital, prediction-market writes,
autonomous position mutation, and Phase 7 proof credit disabled.

## Runtime State

The guarded postmortem-due artifact now reports:

```text
status=postmortem_due
source_order_ref=q5e5-paper-order-crude_oil_energy_security_disruption
source_closed_trade_ref=q5e7-closed-trade-crude_oil_energy_security_disruption
postmortem_due_ref=q5e8-postmortem-due-crude_oil_energy_security_disruption
postmortem_status=postmortem_due
postmortem_due_count=1
```

Q5-11 now reports:

```text
submitted_order_count=1
mirrored_order_count=1
open_position_count=0
closed_trade_count=1
postmortem_due_count=1
failed_reconciliation_count=0
```

## Safety Boundary

Q5E-8 preserves the core boundary:

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

Q5-14 now advances past the postmortem-due missing state, but it still remains
blocked:

```text
paper_trade_drill_state=blocked_prerequisites_missing
phase5_paper_trade_drill_exit_gate_passed=False
blockers=execution_adapter_not_staging_ready
submitted_paper_order_count=1
open_position_count=0
position_open_lifecycle_satisfied=True
closed_trade_count=1
postmortem_due_count=1
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
postmortem_due_count=1
live_capital_enabled_count=0
```

## Implementation

- Added `scripts/check_phase5_exit_postmortem_due.py`.
- Added the guarded local postmortem-due artifact in
  `orchestrator/phase5_position_monitor.py`.
- Updated Q5-14, Q5-15, cockpit, and dashboard checks so postmortem-due
  lifecycle evidence is allowed only when backed by a closed trade.
- Kept all broker POST, Alpaca POST, position mutation, live-capital, and Phase
  7 proof-credit counters at zero.

## Verification

```bash
.venv/bin/python scripts/check_phase5_exit_postmortem_due.py
.venv/bin/python scripts/check_phase5_position_monitor.py
.venv/bin/python scripts/check_phase5_paper_trade_drill.py
.venv/bin/python scripts/check_phase5_certification.py
.venv/bin/python scripts/check_cockpit_status.py
node scripts/check_dashboard_mission_control.js
node scripts/check_dashboard_phase5_system_map.js
node scripts/check_dashboard_phase5_paper_trade_drill.js
node scripts/check_dashboard_phase5_certification.js
```

All checks passed.

## Next Stage

The next required stage is Q5E-9: resolve the remaining Q5-14 blocker,
`execution_adapter_not_staging_ready`, without enabling broker POST, live
capital, autonomous execution, or Phase 7 proof credit.
