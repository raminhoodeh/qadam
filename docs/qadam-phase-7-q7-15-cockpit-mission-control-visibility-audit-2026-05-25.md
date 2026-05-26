# Qadam Phase 7 Q7-15 Cockpit And Mission Control Visibility Audit - 2026-05-25

## Scope

Q7-15 exposes the Phase 7 30-day demo-proof state in Cockpit and Mission
Control from backend artifacts only. It summarizes calendar progress, weekly
cadence, qualified setups, proof lifecycle, postmortems, expectancy, drawdown,
override state, source/signal evidence, and 100-trade maturity without granting
proof credit or live authority.

## Implementation

- Added `orchestrator/phase7_cockpit_visibility.py`.
- Added `scripts/check_phase7_cockpit_visibility.py`.
- Added `scripts/check_dashboard_phase7_demo_proof.js`.
- Updated `orchestrator/cockpit_status.py` to export `phase7_demo_proof`.
- Updated `landing-page-repo/dashboard.js` and
  `scripts/check_dashboard_renderer.js` to render and verify Q7-15 visibility.
- Runtime artifact: `data/runtime/phase7_cockpit_visibility.json`.
- Event log: `data/runtime/phase7_cockpit_visibility_events.jsonl`.
- History log: `data/runtime/phase7_cockpit_visibility_history.jsonl`.

## Current Result

The current Phase 7 demo-proof run has not started and has no proof trades:

- `phase7_cockpit_visibility_status=visible`
- `phase7_cockpit_visibility_stage_status=phase7_demo_proof_visible`
- `phase7_cockpit_visibility_backend_derived=True`
- `phase7_cockpit_visibility_display_derived_from_backend=True`
- `phase7_cockpit_visibility_dashboard_uses_backend_status=True`
- `phase7_cockpit_visibility_ui_inferred_readiness_count=0`
- `phase7_cockpit_visibility_source_artifact_count=14`
- `phase7_cockpit_visibility_source_missing_count=0`
- `phase7_cockpit_visibility_source_validation_error_count=0`
- `phase7_cockpit_visibility_completed_calendar_day_count=0`
- `phase7_cockpit_visibility_phase7_harness_day_count=30`
- `phase7_cockpit_visibility_proof_week_count=5`
- `phase7_cockpit_visibility_qualified_setup_count=0`
- `phase7_cockpit_visibility_missed_qualified_setup_count=0`
- `phase7_cockpit_visibility_submitted_paper_order_count=0`
- `phase7_cockpit_visibility_broker_receipt_count=0`
- `phase7_cockpit_visibility_open_position_count=0`
- `phase7_cockpit_visibility_closed_proof_trade_count=0`
- `phase7_cockpit_visibility_postmortem_due_count=0`
- `phase7_cockpit_visibility_drawdown_within_cap=True`
- `phase7_cockpit_visibility_override_count=0`
- `phase7_cockpit_visibility_sample_contaminated=False`
- `phase7_cockpit_visibility_complete_decision_chain_count=0`
- `phase7_cockpit_visibility_maturity_state=no_sample`
- `phase7_cockpit_visibility_mature_benchmark=100`
- `phase7_cockpit_visibility_maturity_progress_fraction=0.0`
- `phase7_cockpit_visibility_phase7_mature_benchmark_met=False`
- `phase7_cockpit_visibility_phase7_mature_status_blocked=True`
- `phase7_cockpit_visibility_phase7_statistical_immaturity_hidden=False`
- `phase7_cockpit_visibility_phase5_test_trades_count_for_phase7=False`
- `phase7_cockpit_visibility_phase7_proof_credit_allowed=False`
- `phase7_cockpit_visibility_live_capital_enabled=False`
- `phase7_cockpit_visibility_broker_post_called_count=0`
- `phase7_cockpit_visibility_alpaca_post_called_count=0`
- `phase7_cockpit_visibility_unsafe_write_counter_total=0`
- `phase7_cockpit_visibility_q7_16_weekly_review_pack_stage_allowed=True`

## Safety Findings

- Q7-15 is backend-derived and rejects UI-inferred readiness.
- Public status excludes raw payloads, private payloads, request/receipt
  bodies, local paths, secrets, and broker identifiers.
- Source status records must display backend status exactly and use relative
  `data/runtime/...` refs.
- A valid future paper lifecycle visibility probe with paper broker/Alpaca POST
  counters is accepted when proof credit and live capital remain disabled.
- Hidden statistical immaturity, contaminated samples, Phase 5 proof reuse,
  proof credit, live capital, source-display mismatch, local path refs, raw
  public payload leakage, and disabled Q7-16 handoff are rejected.

## Verification

```bash
.venv/bin/python scripts/check_phase7_cockpit_visibility.py
.venv/bin/python scripts/export_cockpit_status.py
node scripts/check_dashboard_phase7_demo_proof.js
node scripts/check_dashboard_renderer.js
.venv/bin/python -m ruff check orchestrator/phase7_cockpit_visibility.py scripts/check_phase7_cockpit_visibility.py
.venv/bin/python -m compileall orchestrator/phase7_cockpit_visibility.py scripts/check_phase7_cockpit_visibility.py
```

All checks passed.

## Handoff

Q7-15 allows Q7-16 - Weekly Review Pack. It does not infer readiness from the
UI, grant Phase 7 proof credit, count Phase 5 test trades, hide statistical
immaturity, mutate proof trades, write market orders, enable live capital, or
expose private runtime details.
