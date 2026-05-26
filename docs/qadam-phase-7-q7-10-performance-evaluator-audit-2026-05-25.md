# Qadam Phase 7 Q7-10 Performance Evaluator Audit - 2026-05-25

## Scope

Q7-10 implements the Phase 7 Demo Proof performance evaluator. It consumes
the Q7-9 postmortem contract and computes local proof-sample performance
metrics only for postmortem-covered closed Q7 proof trades.

This stage can calculate expectancy after estimated costs, R-multiple
distribution, win rate, average win/loss, Sharpe/Sortino when the sample
permits, rolling seven-day and 30-day expectancy, max drawdown, and sample
maturity labels. It cannot certify Phase 7, grant proof credit, mutate policy
or strategy, call broker or Alpaca POST routes, write prediction-market or
crypto-perps orders, permit manual trade-level overrides, or enable live
capital.

## Files

- `orchestrator/phase7_performance_evaluator.py`
- `scripts/check_phase7_performance_evaluator.py`
- `data/runtime/phase7_performance_evaluator.json`
- `data/runtime/phase7_performance_evaluator_history.jsonl`
- `data/runtime/phase7_performance_evaluator_events.jsonl`

## Runtime Result

The Q7-10 checker writes the local runtime artifact and records one Event Log
entry.

Key outputs:

- `phase7_performance_status=ready_no_closed_trades`
- `phase7_performance_stage_status=performance_evaluator_ready_no_closed_trades`
- `phase7_performance_schema_version=1`
- `phase7_performance_source_postmortem_status=ready_no_closed_trades`
- `phase7_performance_source_postmortem_stage_status=proof_postmortem_contract_ready_no_closed_trades`
- `phase7_performance_q7_11_drawdown_stage_allowed=True`
- `phase7_performance_write_allowed=True`
- `phase7_performance_closed_proof_trade_count=0`
- `phase7_performance_evaluated_trade_count=0`
- `phase7_performance_metric_record_count=0`
- `phase7_performance_expectancy_after_costs_gbp=None`
- `phase7_performance_expectancy_after_costs_positive=False`
- `phase7_performance_win_rate=None`
- `phase7_performance_loss_rate=None`
- `phase7_performance_max_drawdown_fraction_observed=0.0`
- `phase7_performance_drawdown_within_cap=True`
- `phase7_performance_statistical_maturity_state=no_sample`
- `phase7_performance_phase7_proof_credit_allowed=False`
- `phase7_performance_live_capital_enabled=False`
- `phase7_performance_broker_post_called_count=0`
- `phase7_performance_alpaca_post_called_count=0`
- `phase7_performance_unsafe_write_counter_total=0`
- `phase7_performance_blocker_count=0`
- `phase7_performance_event_log_replay_total_events=1`

## Interpretation

Q7-10 is ready, but Q7-9 currently has zero closed proof trades. The evaluator
therefore records zero trade metrics, no expectancy, no win/loss rate, zero
observed drawdown, and a `no_sample` maturity label. It does not overstate
maturity or create proof credit from Phase 5 trades, Q6 deferred learning, or
supplemental source context.

The only new authority added by this stage is narrow
`phase7_performance_evaluation_write_allowed=True`. It is limited to local
evaluation artifacts derived from Q7-9 postmortem-covered proof trades.

## Guard Probes

The checker verifies that the following evaluator and safety conditions are
enforced:

- valid synthetic positive performance sample is accepted
- evaluated trade records missing R-multiples are rejected
- inconsistent net P&L is rejected
- negative expectancy blocker drift is rejected
- drawdown blocker drift is rejected
- statistical maturity label drift is rejected
- cost-count drift is rejected
- Phase 7 proof credit remains disabled
- broker POST and Alpaca POST remain disabled
- live capital remains disabled
- prediction-market and crypto-perps writes remain disabled
- manual trade-level override authority remains disabled
- Preference/PREF source-quorum credit and Q-CTRL execution truth are rejected
- local absolute path leakage is rejected
- disabled Q7-10 stage gate is rejected
- disabled Q7-11 drawdown sentinel handoff gate is rejected

## Verification

Commands run:

```bash
.venv/bin/python scripts/check_phase7_performance_evaluator.py
.venv/bin/python -m ruff check orchestrator/phase7_performance_evaluator.py scripts/check_phase7_performance_evaluator.py
.venv/bin/python -m compileall orchestrator/phase7_performance_evaluator.py scripts/check_phase7_performance_evaluator.py
```

Results:

- `phase7_performance_evaluator_check=ok`
- `All checks passed!`
- `compileall` succeeded

## Handoff

Q7-10 is complete. The next explicit build target is Q7-11 - Drawdown And
Risk Sentinel.
