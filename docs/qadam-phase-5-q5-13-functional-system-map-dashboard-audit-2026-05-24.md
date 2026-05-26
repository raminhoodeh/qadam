# Q5-13 Functional System Map Dashboard Audit - 2026-05-24

## Stage

Q5-13 - Functional System Map Dashboard.

## Objective

Render the full Layer B system map from backend status, not browser inference,
so the cockpit shows current source posture, blockers, kill-switch posture,
paper lifecycle state, and authority boundaries exactly as the public-safe
backend reports them.

## Implementation

- Added `orchestrator/phase5_system_map.py`.
- Added `scripts/check_phase5_system_map.py`.
- Added `scripts/check_dashboard_phase5_system_map.js`.
- Wired `phase5_system_map` into `orchestrator/cockpit_status.py`.
- Exposed Q5-13 counters through Mission Control `system_stack` and
  `phase5_layer_b`.
- Updated `landing-page-repo/dashboard.js` to render backend-provided lanes and
  nodes before falling back to the older browser-side map.
- Extended broad dashboard checks in `scripts/check_dashboard_renderer.js` and
  `scripts/check_dashboard_mission_control.js`.

## Verified State

```text
phase5_system_map_status=ok
phase5_system_map_node_count=27
phase5_system_map_lane_count=6
phase5_system_map_layer_b_node_count=10
phase5_system_map_backend_parity_error_count=0
phase5_system_map_unsafe_control_count=0
phase5_system_map_ui_inferred_node_count=0
phase5_system_map_event_log_written=True
phase5_system_map_event_log_total_events=1
phase5_system_map_yahoo_finance_role=supplemental_market_confirmation_only
phase5_system_map_preference_source_36=False
phase5_system_map_dashboard_claims_trading_now=False
phase5_system_map_live_capital_enabled=False
phase5_system_map_paper_submit_path_available_count=0
```

The latest local smoke run saw canonical replay posture as `0/35` from the
current local backend status. Q5-13 deliberately validates dashboard/backend
parity, source role boundaries, and authority boundaries; it does not certify
durable replay readiness. Durable replay should be refreshed separately before
any stage depends on full source coverage.

## Authority Boundary

Q5-13 is dashboard-only. It can display backend state and write the system-map
artifact/Event Log record, but it cannot approve trades, place orders, submit
paper orders, call brokers or venues, mutate kill switches, send live alerts, or
enable live capital.

## Verification

```bash
.venv/bin/python -m compileall orchestrator/phase5_system_map.py scripts/check_phase5_system_map.py orchestrator/cockpit_status.py scripts/check_cockpit_status.py
.venv/bin/ruff check orchestrator/phase5_system_map.py scripts/check_phase5_system_map.py orchestrator/cockpit_status.py scripts/check_cockpit_status.py
.venv/bin/python scripts/check_phase5_system_map.py
.venv/bin/python scripts/check_cockpit_status.py
node --check landing-page-repo/dashboard.js
node --check scripts/check_dashboard_phase5_system_map.js
node --check scripts/check_dashboard_mission_control.js
node --check scripts/check_dashboard_renderer.js
node scripts/check_dashboard_renderer.js
node scripts/check_dashboard_mission_control.js
node scripts/check_dashboard_system_map.js
node scripts/check_dashboard_phase5_system_map.js
```

## Result

Q5-13 is complete. The next stage is Q5-14 - End-To-End Paper Trade Drill.

Q5-14 must still create its own guarded paper-trade drill path and paper-submit
approval prerequisites. Q5-13 does not create a staged paper order, guarded
paper-submit path, open position, closed trade, broker write, prediction-market
write, or live-capital path.
