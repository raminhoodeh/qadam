# Qadam Phase 6 - Q6-15 Architect Learning Summary Audit

Date: 2026-05-25

## Scope

Q6-15 created the Architect learning summary and recommendation surface. The
summary can aggregate approved postmortem facts, Knowledge Graph read results,
model-weight proposals, trust-score proposals, and shadow replay outputs for
explicit governance review.

Current upstream state remains blocked: Q6-9 approval is explicitly `deferred`, and
Q6-14 shadow replay is blocked. Q6-15 therefore records blocked recommendation
records and keeps all policy, strategy, risk-limit, source-weight,
model-weight, trust-score, learning-write, graph-write, and proof-credit paths
disabled.

## Implemented Files

- `orchestrator/phase6_architect_learning.py`
- `scripts/check_phase6_architect_learning.py`
- `data/runtime/phase6_architect_learning_summary.json`
- `data/runtime/phase6_architect_learning_summary_history.jsonl`
- `data/runtime/phase6_architect_learning_summary_events.jsonl`

## Runtime Evidence

`scripts/check_phase6_architect_learning.py` reports:

- `phase6_architect_learning_status=blocked`
- `phase6_architect_learning_summary_state=blocked_pending_learning_approval`
- `phase6_architect_learning_source_shadow_replay_status=blocked`
- `phase6_architect_learning_source_approval_state=deferred`
- `phase6_architect_learning_source_approved_fact_count=0`
- `phase6_architect_learning_approved_fact_count=0`
- `phase6_architect_learning_architect_summary_created=True`
- `phase6_architect_learning_recommendation_count=4`
- `phase6_architect_learning_recommendation_record_count=4`
- `phase6_architect_learning_active_recommendation_count=0`
- `phase6_architect_learning_blocked_recommendation_count=4`
- `phase6_architect_learning_governance_pending_count=4`
- `phase6_architect_learning_policy_recommendation_count=1`
- `phase6_architect_learning_strategy_recommendation_count=1`
- `phase6_architect_learning_risk_limit_recommendation_count=1`
- `phase6_architect_learning_source_model_trust_recommendation_count=1`
- `phase6_architect_learning_recommendation_apply_allowed=False`
- `phase6_architect_learning_policy_mutation_allowed=False`
- `phase6_architect_learning_policy_mutation_created=False`
- `phase6_architect_learning_strategy_mutation_allowed=False`
- `phase6_architect_learning_strategy_mutation_created=False`
- `phase6_architect_learning_risk_limit_update_allowed=False`
- `phase6_architect_learning_risk_limit_update_created=False`
- `phase6_architect_learning_source_weight_update_allowed=False`
- `phase6_architect_learning_source_weight_update_created=False`
- `phase6_architect_learning_model_weight_update_allowed=False`
- `phase6_architect_learning_model_weight_update_created=False`
- `phase6_architect_learning_trust_score_update_allowed=False`
- `phase6_architect_learning_trust_score_update_created=False`
- `phase6_architect_learning_learning_write_created=False`
- `phase6_architect_learning_knowledge_graph_write_created=False`
- `phase6_architect_learning_knowledge_graph_commit_created=False`
- `phase6_architect_learning_chroma_write_created=False`
- `phase6_architect_learning_graph_backend_write_created=False`
- `phase6_architect_learning_raw_payload_copied_count=0`
- `phase6_architect_learning_private_payload_copied_count=0`
- `phase6_architect_learning_local_path_exposed_count=0`
- `phase6_architect_learning_secret_ref_exposed_count=0`
- `phase6_architect_learning_source_hash_mutation_count=0`
- `phase6_architect_learning_phase5_source_artifacts_mutated=False`
- `phase6_architect_learning_phase5_test_trades_count_for_phase7=False`
- `phase6_architect_learning_phase7_proof_credit_allowed=False`
- `phase6_architect_learning_unsafe_write_counter_total=0`
- `phase6_architect_learning_blocker_count=2`
- `phase6_architect_learning_event_log_replay_total_events=1`
- `phase6_architect_learning_validation_error_count=0`
- `phase6_architect_learning_readiness_error_count=0`
- `phase6_architect_learning_schema_summary_status=ok`
- `phase6_architect_learning_shadow_replay_error_count=0`
- `phase6_architect_learning_check=ok`

## Recommendation Guard

Q6-15 records four blocked recommendation records:

- learning governance policy guardrail review
- crude-oil energy-security strategy review
- paper lifecycle risk-limit review
- source/model/trust update surface review

Each record is reference-only, governance-required, linked to source refs and
approval state, and non-applicable until explicit learning approval exists.

## Validator Probes

The Q6-15 verifier rejects:

- Architect policy-mutation authority
- unapproved active recommendations
- policy mutation
- strategy mutation
- risk-limit update
- source-weight update
- model-weight update
- trust-score update
- recommendation-record action enablement
- raw/private payload copying
- forbidden payload fields
- local absolute source refs
- invalid source shadow-replay or approval states
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
.venv/bin/python scripts/check_phase6_architect_learning.py
.venv/bin/python -m ruff check orchestrator/phase6_architect_learning.py scripts/check_phase6_architect_learning.py
.venv/bin/python -m compileall orchestrator/phase6_architect_learning.py scripts/check_phase6_architect_learning.py
```

## Next Stage

Q6-16 - Journal And Cockpit Visibility.
