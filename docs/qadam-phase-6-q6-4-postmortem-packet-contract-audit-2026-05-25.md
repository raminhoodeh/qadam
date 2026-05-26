# Qadam Phase 6 - Q6-4 Postmortem Packet Contract Audit

Date: 2026-05-25

## Scope

Q6-4 defined the packet shape that Q6-5 Postmortem Agent Drafting must fill.
This stage is contract-only: it creates no postmortem draft, approves no
postmortem, and writes no learning state.

## Implemented Files

- `orchestrator/phase6_postmortem_packets.py`
- `scripts/check_phase6_postmortem_packet_contract.py`
- `data/runtime/phase6_postmortem_packet_contract.json`
- `data/runtime/phase6_postmortem_packet_contract_history.jsonl`
- `data/runtime/phase6_postmortem_packet_contract_events.jsonl`

## Runtime Evidence

`scripts/check_phase6_postmortem_packet_contract.py` reports:

- `phase6_postmortem_packet_contract_status=schema_only`
- `phase6_postmortem_packet_contract_source_outcome_ref=q6-3-outcome-q5e7-closed-trade-crude_oil_energy_security_disruption`
- `phase6_postmortem_packet_contract_source_closed_trade_ref=q5e7-closed-trade-crude_oil_energy_security_disruption`
- `phase6_postmortem_packet_contract_packet_section_count=13`
- `phase6_postmortem_packet_contract_assertion_source_refs_required=True`
- `phase6_postmortem_packet_contract_uncited_conclusion_allowed=False`
- `phase6_postmortem_packet_contract_narrative_only_allowed=False`
- `phase6_postmortem_packet_contract_postmortem_draft_created=False`
- `phase6_postmortem_packet_contract_learning_write_created=False`
- `phase6_postmortem_packet_contract_knowledge_graph_write_created=False`
- `phase6_postmortem_packet_contract_source_hash_mutation_count=0`
- `phase6_postmortem_packet_contract_phase7_proof_credit_allowed=False`
- `phase6_postmortem_packet_contract_unsafe_write_counter_total=0`
- `phase6_postmortem_packet_contract_blocker_count=0`
- `phase6_postmortem_packet_contract_event_log_replay_total_events=1`
- `phase6_postmortem_packet_contract_check=ok`

## Required Sections

The contract requires these sections:

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

Each section requires assertions to cite public-safe source refs or be explicitly
marked as a hypothesis with review required. Uncited conclusions and
narrative-only packet payloads are rejected.

## Validator Probes

The Q6-4 verifier rejects:

- missing outcome refs
- uncited conclusions
- narrative-only postmortems
- missing required sections
- local absolute source paths
- hidden postmortem draft creation
- hidden learning writes
- hidden Knowledge Graph writes
- hidden model-weight, trust-score, policy, or strategy mutation
- Phase 7 proof credit

The hypothesis probe is accepted only when `is_hypothesis=True`,
`hypothesis_reason` is present, and `review_required=True`.

## Safety And Authority

Q6-4 keeps these blocked:

- postmortem draft creation
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
.venv/bin/python scripts/check_phase6_postmortem_packet_contract.py
.venv/bin/python -m ruff check orchestrator/phase6_postmortem_packets.py scripts/check_phase6_postmortem_packet_contract.py
.venv/bin/python -m compileall orchestrator/phase6_postmortem_packets.py scripts/check_phase6_postmortem_packet_contract.py
```

## Next Stage

Q6-5 - Postmortem Agent Drafting.
