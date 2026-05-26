# Qadam Phase 7 Q7-11 Drawdown Risk Sentinel Audit - 2026-05-25

## Scope

Q7-11 implements the Phase 7 Demo Proof drawdown and risk sentinel. It
consumes the Q7-10 performance evaluator, computes realized drawdown,
accounts for unrealized drawdown availability, compares combined drawdown
against the 20 percent cap, and freezes new Phase 7 proof-trade staging and
submission when the cap is breached.

This stage can record local risk-halt state only. It cannot certify Phase 7,
grant proof credit, create proof trades, mutate policy or strategy, call
broker or Alpaca POST routes, write prediction-market or crypto-perps orders,
permit manual trade-level overrides, or enable live capital.

## Files

- `orchestrator/phase7_drawdown_risk_sentinel.py`
- `scripts/check_phase7_drawdown_risk_sentinel.py`
- `data/runtime/phase7_drawdown_risk_sentinel.json`
- `data/runtime/phase7_drawdown_risk_sentinel_history.jsonl`
- `data/runtime/phase7_drawdown_risk_sentinel_events.jsonl`

## Runtime Result

The Q7-11 checker writes the local runtime artifact and records one Event Log
entry.

Key outputs:

- `phase7_drawdown_status=ready_no_drawdown_sample`
- `phase7_drawdown_stage_status=drawdown_sentinel_ready_no_closed_trades`
- `phase7_drawdown_schema_version=1`
- `phase7_drawdown_source_performance_status=ready_no_closed_trades`
- `phase7_drawdown_source_performance_stage_status=performance_evaluator_ready_no_closed_trades`
- `phase7_drawdown_q7_12_override_stage_allowed=True`
- `phase7_drawdown_risk_halt_write_allowed=True`
- `phase7_drawdown_risk_halt_active=False`
- `phase7_drawdown_new_proof_trades_frozen=False`
- `phase7_drawdown_new_proof_order_staging_allowed=True`
- `phase7_drawdown_new_proof_trade_submission_allowed=True`
- `phase7_drawdown_source_closed_proof_trade_count=0`
- `phase7_drawdown_source_evaluated_trade_count=0`
- `phase7_drawdown_current_equity_gbp=1000.0`
- `phase7_drawdown_peak_equity_gbp=1000.0`
- `phase7_drawdown_realized_drawdown_fraction_observed=0.0`
- `phase7_drawdown_unrealized_drawdown_fraction_observed=0.0`
- `phase7_drawdown_max_drawdown_fraction_observed=0.0`
- `phase7_drawdown_drawdown_within_cap=True`
- `phase7_drawdown_drawdown_state=no_sample_within_cap`
- `phase7_drawdown_phase7_certification_blocked_by_drawdown=False`
- `phase7_drawdown_phase7_proof_credit_allowed=False`
- `phase7_drawdown_live_capital_enabled=False`
- `phase7_drawdown_broker_post_called_count=0`
- `phase7_drawdown_alpaca_post_called_count=0`
- `phase7_drawdown_unsafe_write_counter_total=0`
- `phase7_drawdown_blocker_count=0`
- `phase7_drawdown_event_log_replay_total_events=1`

## Interpretation

Q7-11 is ready, but Q7-10 currently has zero evaluated proof trades. The
sentinel therefore records starting equity and peak equity at GBP 1000.00,
zero realized drawdown, zero unrealized drawdown, zero combined drawdown, no
active risk halt, and no proof-trade freeze.

The new authority added by this stage is narrow
`risk_halt_write_allowed=True`. It is limited to local drawdown/risk-halt
state. In the current no-breach state, new Phase 7 proof-order staging and
submission remain allowed by the sentinel; if a synthetic breach exceeds the
20 percent cap, validation requires those new-trade paths to freeze.

## Guard Probes

The checker verifies that the following sentinel and safety conditions are
enforced:

- valid synthetic within-cap drawdown sample is accepted
- valid synthetic drawdown breach sample is accepted only with risk halt active
- drawdown breaches that do not freeze new proof trades are rejected
- false freezes without a breach are rejected
- certification blocker drift on breach is rejected
- drawdown-cap drift is rejected
- Phase 7 proof credit remains disabled
- broker POST and Alpaca POST remain disabled
- live capital remains disabled
- prediction-market and crypto-perps writes remain disabled
- manual trade-level override authority remains disabled
- Preference/PREF source-quorum credit and Q-CTRL execution truth are rejected
- local absolute path leakage is rejected
- disabled Q7-11 stage gate is rejected
- disabled Q7-12 override-detector handoff gate is rejected
- open positions without unrealized mark-to-market coverage are rejected

## Verification

Commands run:

```bash
.venv/bin/python scripts/check_phase7_drawdown_risk_sentinel.py
.venv/bin/python -m ruff check orchestrator/phase7_drawdown_risk_sentinel.py scripts/check_phase7_drawdown_risk_sentinel.py
.venv/bin/python -m compileall orchestrator/phase7_drawdown_risk_sentinel.py scripts/check_phase7_drawdown_risk_sentinel.py
```

Results:

- `phase7_drawdown_risk_sentinel_check=ok`
- `All checks passed!`
- `compileall` succeeded

## Handoff

Q7-11 is complete. The next explicit build target is Q7-12 - Override
Detector.
