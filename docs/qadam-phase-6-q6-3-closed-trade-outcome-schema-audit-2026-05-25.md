# Qadam Phase 6 - Q6-3 Closed Trade And Outcome Schema Audit

Date: 2026-05-25

## Scope

Q6-3 normalized the Q5E guarded closed paper trade into a Phase 6
`closed_trade_outcome` artifact. The stage is read-only and prepares the
canonical outcome shape needed before Q6-4 postmortem packet contracts.

## Implemented Files

- `orchestrator/phase6_closed_trade_outcome.py`
- `scripts/check_phase6_closed_trade_outcome.py`
- `data/runtime/phase6_closed_trade_outcome.json`
- `data/runtime/phase6_closed_trade_outcome_history.jsonl`
- `data/runtime/phase6_closed_trade_outcome_events.jsonl`

## Runtime Evidence

`scripts/check_phase6_closed_trade_outcome.py` reports:

- `phase6_closed_trade_outcome_status=read_only`
- `phase6_closed_trade_outcome_closed_trade_ref=q5e7-closed-trade-crude_oil_energy_security_disruption`
- `phase6_closed_trade_outcome_outcome_status=closed_trade_outcome_normalized`
- `phase6_closed_trade_outcome_record_count=1`
- `phase6_closed_trade_outcome_broker_truth_separated=True`
- `phase6_closed_trade_outcome_unknown_field_count=5`
- `phase6_closed_trade_outcome_deferred_field_count=6`
- `phase6_closed_trade_outcome_learning_write_allowed=False`
- `phase6_closed_trade_outcome_knowledge_graph_write_created=False`
- `phase6_closed_trade_outcome_phase5_source_artifacts_mutated=False`
- `phase6_closed_trade_outcome_source_hash_mutation_count=0`
- `phase6_closed_trade_outcome_phase7_proof_credit_allowed=False`
- `phase6_closed_trade_outcome_unsafe_write_counter_total=0`
- `phase6_closed_trade_outcome_blocker_count=0`
- `phase6_closed_trade_outcome_event_log_replay_total_events=1`
- `phase6_closed_trade_outcome_check=ok`

## Normalized Outcome Record

The Q6-3 artifact records one outcome:

- `outcome_ref=q6-3-outcome-q5e7-closed-trade-crude_oil_energy_security_disruption`
- `strategy_family_key=crude_oil_energy_security_disruption`
- `instrument=crude_oil`
- `realized_pnl_gbp=0.0`
- `r_multiple=0.0`
- `outcome_bucket=flat`
- `postmortem_status=postmortem_due`
- `phase5_test_trade=True`
- `phase7_proof_credit_allowed=False`

Q6-3 intentionally does not invent the specific catalyst. It carries the
source-backed catalyst classes from Q5-2 and marks the specific expected
catalyst, actual catalyst, pricing read, regime read, execution-quality read,
source-quality read, and learning actions as unknown or deferred for later
postmortem stages.

## Source Coverage

The outcome links to:

- Q6-2 learning source intake
- Q5E guarded closed trade
- Q5E guarded postmortem-due marker
- Q5E guarded paper-submit receipt
- Q5 paper-order staging gate
- Q5 position monitor
- Q5 risk sizing review
- Q5 approval-policy decision
- Q5 execution adapter status
- Signal Integrity review
- Yahoo Finance supplemental market context
- Preference/PREF MCP shadow context and provenance
- Preference source-promotion decisions
- optional Head of Quant shadow annotations

## Safety And Authority

Q6-3 keeps these blocked:

- postmortem draft creation
- learning writes
- Knowledge Graph writes
- model-weight updates
- trust-score updates
- policy mutation
- broker POST calls
- Alpaca POST calls
- live endpoints
- live capital
- Phase 7 proof credit from Phase 5 test trades

The validator also rejects hidden learning writes, Knowledge Graph writes,
broker-truth confusion, invented catalysts, missing deferred-field markers,
local absolute source paths, source mutation flags, and Phase 7 proof credit.

## Verification

Passed:

```bash
.venv/bin/python scripts/check_phase6_closed_trade_outcome.py
.venv/bin/python -m ruff check orchestrator/phase6_closed_trade_outcome.py scripts/check_phase6_closed_trade_outcome.py
.venv/bin/python -m compileall orchestrator/phase6_closed_trade_outcome.py scripts/check_phase6_closed_trade_outcome.py
```

## Next Stage

Q6-4 - Postmortem Packet Contract.
