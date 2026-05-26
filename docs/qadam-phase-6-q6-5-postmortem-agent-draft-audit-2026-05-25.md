# Qadam Phase 6 - Q6-5 Postmortem Agent Draft Audit

Date: 2026-05-25

## Scope

Q6-5 created the first backend-derived postmortem draft for the Q5E guarded
paper lifecycle seed. The draft is deterministic and source-cited; it does not
use an LLM, approve a postmortem, or write learning state.

## Implemented Files

- `orchestrator/phase6_postmortem_agent.py`
- `scripts/check_phase6_postmortem_agent.py`
- `data/runtime/phase6_postmortem_draft.json`
- `data/runtime/phase6_postmortem_draft_history.jsonl`
- `data/runtime/phase6_postmortem_draft_events.jsonl`

## Runtime Evidence

`scripts/check_phase6_postmortem_agent.py` reports:

- `phase6_postmortem_agent_status=draft`
- `phase6_postmortem_agent_draft_state=deterministic_postmortem_draft_created`
- `phase6_postmortem_agent_postmortem_draft_created=True`
- `phase6_postmortem_agent_postmortem_approved=False`
- `phase6_postmortem_agent_approval_state=not_requested`
- `phase6_postmortem_agent_source_outcome_ref=q6-3-outcome-q5e7-closed-trade-crude_oil_energy_security_disruption`
- `phase6_postmortem_agent_packet_section_count=13`
- `phase6_postmortem_agent_source_assertion_count=20`
- `phase6_postmortem_agent_unknown_marker_count=5`
- `phase6_postmortem_agent_deferred_marker_count=6`
- `phase6_postmortem_agent_missing_ref_count=3`
- `phase6_postmortem_agent_llm_used=False`
- `phase6_postmortem_agent_learning_write_created=False`
- `phase6_postmortem_agent_knowledge_graph_write_created=False`
- `phase6_postmortem_agent_model_weight_update_created=False`
- `phase6_postmortem_agent_trust_score_update_created=False`
- `phase6_postmortem_agent_policy_mutation_created=False`
- `phase6_postmortem_agent_strategy_mutation_created=False`
- `phase6_postmortem_agent_source_hash_mutation_count=0`
- `phase6_postmortem_agent_phase7_proof_credit_allowed=False`
- `phase6_postmortem_agent_unsafe_write_counter_total=0`
- `phase6_postmortem_agent_blocker_count=0`
- `phase6_postmortem_agent_event_log_replay_total_events=1`
- `phase6_postmortem_agent_check=ok`

## Draft Content

The draft fills every Q6-4 packet section:

- thesis
- timeline
- catalyst_read
- pricing_read
- regime_read
- execution_read
- override_readiness_read
- source_quality
- mistakes
- useful_signals
- harmful_signals
- uncertainty
- proposed_learning_actions

All packet assertions cite public-safe source refs or are explicitly marked as
hypotheses with review required. The draft explicitly carries the Q6-3 unknown
fields, deferred fields, and missing broker-fill reference markers rather than
inventing evidence.

## Validator Probes

The Q6-5 verifier rejects:

- postmortem approval hidden in the draft
- learning-write authority or learning-write records
- Knowledge Graph writes
- model-weight, trust-score, policy, or strategy mutation
- LLM-used payloads
- nested packet write flags
- narrative-only packet payloads
- local absolute source paths
- missing unknown-field markers
- missing deferred-field markers
- missing broker-fill reference markers
- Phase 7 proof credit

## Safety And Authority

Q6-5 keeps these blocked:

- postmortem approval
- learning writes
- Knowledge Graph writes
- model-weight updates
- trust-score updates
- policy mutation
- strategy mutation
- broker POST calls
- Alpaca POST calls
- live endpoints
- live capital
- Phase 7 proof credit from Phase 5 test trades

## Verification

Passed:

```bash
.venv/bin/python scripts/check_phase6_postmortem_agent.py
.venv/bin/python -m ruff check orchestrator/phase6_postmortem_agent.py scripts/check_phase6_postmortem_agent.py
.venv/bin/python -m compileall orchestrator/phase6_postmortem_agent.py scripts/check_phase6_postmortem_agent.py
```

## Next Stage

Q6-6 - Analysis Sub-Agent Packets.
