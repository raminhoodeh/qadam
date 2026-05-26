# Qadam Phase 6 - Q6-14 Shadow Strategy Runner Audit

Date: 2026-05-25

## Scope

Q6-14 created the shadow strategy replay gate. The gate can compare actual
guarded Phase 5 lifecycle evidence with what-would-have-happened strategy
variants only after explicit approved postmortem learning evidence exists.

Current upstream state remains blocked: Q6-9 approval is explicitly `deferred`, and
Q6-13 trust-score update proposals are blocked. Q6-14 therefore records
blocked no-op replay variants and keeps all candidate, order, execution,
broker, policy, strategy, learning-write, and proof-credit paths disabled.

## Implemented Files

- `orchestrator/phase6_shadow_strategy_runner.py`
- `scripts/check_phase6_shadow_strategy_runner.py`
- `data/runtime/phase6_shadow_strategy_replay.json`
- `data/runtime/phase6_shadow_strategy_replay_history.jsonl`
- `data/runtime/phase6_shadow_strategy_replay_events.jsonl`

## Runtime Evidence

`scripts/check_phase6_shadow_strategy_runner.py` reports:

- `phase6_shadow_strategy_runner_status=blocked`
- `phase6_shadow_strategy_runner_replay_state=blocked_pending_learning_approval`
- `phase6_shadow_strategy_runner_source_trust_score_status=blocked`
- `phase6_shadow_strategy_runner_source_approval_state=deferred`
- `phase6_shadow_strategy_runner_source_approved_evidence_count=0`
- `phase6_shadow_strategy_runner_approved_fact_count=0`
- `phase6_shadow_strategy_runner_variant_record_count=3`
- `phase6_shadow_strategy_runner_active_replay_count=0`
- `phase6_shadow_strategy_runner_blocked_replay_count=3`
- `phase6_shadow_strategy_runner_evaluated_variant_count=0`
- `phase6_shadow_strategy_runner_actual_vs_hypothetical_comparison_count=3`
- `phase6_shadow_strategy_runner_evaluated_comparison_count=0`
- `phase6_shadow_strategy_runner_replay_output_exists=True`
- `phase6_shadow_strategy_runner_shadow_strategy_replay_allowed=False`
- `phase6_shadow_strategy_runner_shadow_strategy_replay_created=False`
- `phase6_shadow_strategy_runner_trade_candidate_creation_allowed=False`
- `phase6_shadow_strategy_runner_trade_candidate_created=False`
- `phase6_shadow_strategy_runner_trade_candidate_created_count=0`
- `phase6_shadow_strategy_runner_order_creation_allowed=False`
- `phase6_shadow_strategy_runner_paper_order_allowed=False`
- `phase6_shadow_strategy_runner_paper_order_allowed_count=0`
- `phase6_shadow_strategy_runner_paper_order_created=False`
- `phase6_shadow_strategy_runner_paper_order_created_count=0`
- `phase6_shadow_strategy_runner_execution_allowed=False`
- `phase6_shadow_strategy_runner_execution_allowed_count=0`
- `phase6_shadow_strategy_runner_execution_intent_created=False`
- `phase6_shadow_strategy_runner_execution_intent_created_count=0`
- `phase6_shadow_strategy_runner_broker_post_allowed=False`
- `phase6_shadow_strategy_runner_alpaca_post_allowed=False`
- `phase6_shadow_strategy_runner_broker_post_called_count=0`
- `phase6_shadow_strategy_runner_alpaca_post_called_count=0`
- `phase6_shadow_strategy_runner_learning_write_created=False`
- `phase6_shadow_strategy_runner_knowledge_graph_write_created=False`
- `phase6_shadow_strategy_runner_knowledge_graph_commit_created=False`
- `phase6_shadow_strategy_runner_chroma_write_created=False`
- `phase6_shadow_strategy_runner_graph_backend_write_created=False`
- `phase6_shadow_strategy_runner_model_weight_update_created=False`
- `phase6_shadow_strategy_runner_trust_score_update_created=False`
- `phase6_shadow_strategy_runner_policy_mutation_created=False`
- `phase6_shadow_strategy_runner_strategy_mutation_created=False`
- `phase6_shadow_strategy_runner_raw_payload_copied_count=0`
- `phase6_shadow_strategy_runner_private_payload_copied_count=0`
- `phase6_shadow_strategy_runner_local_path_exposed_count=0`
- `phase6_shadow_strategy_runner_secret_ref_exposed_count=0`
- `phase6_shadow_strategy_runner_source_hash_mutation_count=0`
- `phase6_shadow_strategy_runner_phase5_source_artifacts_mutated=False`
- `phase6_shadow_strategy_runner_phase5_test_trades_count_for_phase7=False`
- `phase6_shadow_strategy_runner_phase7_proof_credit_allowed=False`
- `phase6_shadow_strategy_runner_unsafe_write_counter_total=0`
- `phase6_shadow_strategy_runner_blocker_count=2`
- `phase6_shadow_strategy_runner_event_log_replay_total_events=1`
- `phase6_shadow_strategy_runner_validation_error_count=0`
- `phase6_shadow_strategy_runner_readiness_error_count=0`
- `phase6_shadow_strategy_runner_schema_summary_status=ok`
- `phase6_shadow_strategy_runner_trust_score_error_count=0`
- `phase6_shadow_strategy_runner_check=ok`

## Replay Guard

Q6-14 records three blocked variants:

- baseline current strategy replay
- model-weight counterfactual replay
- trust-score counterfactual replay

Each variant is reference-only and has `trade_candidate_created=False`,
`paper_order_allowed=False`, `execution_allowed=False`,
`broker_post_allowed=False`, and `alpaca_post_allowed=False`.

## Validator Probes

The Q6-14 verifier rejects:

- Phase 6 shadow-runner authority
- unapproved replay enablement
- trade-candidate creation
- paper-order creation or allowance
- execution-intent creation
- broker or Alpaca POST allowance
- model-weight, trust-score, policy, or strategy mutation
- replay-record action enablement
- nonzero replay action deltas
- raw/private payload copying
- forbidden payload fields
- local absolute source refs
- invalid source trust-score or approval states
- cockpit-safe forbidden fields
- cockpit-safe count/state mismatches
- Phase 5 source mutation
- Phase 7 proof credit
- Phase 5 test-trade proof credit
- unsafe broker/write counters
- source artifact hash mutation

## Verification

Passed:

```bash
.venv/bin/python scripts/check_phase6_shadow_strategy_runner.py
.venv/bin/python -m ruff check orchestrator/phase6_shadow_strategy_runner.py scripts/check_phase6_shadow_strategy_runner.py
.venv/bin/python -m compileall orchestrator/phase6_shadow_strategy_runner.py scripts/check_phase6_shadow_strategy_runner.py
```

## Next Stage

Q6-15 - Architect Learning Summary.
