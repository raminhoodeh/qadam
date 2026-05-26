# Qadam Phase 6 Learning Loop Implementation Plan

This document breaks Phase 6 - Learning Loop into staged work that can be
implemented one stage at a time after the Q5E-11 handoff visibility gate.

Phase 6 is allowed to be planned because Q5E-10/Q5E-11 reports
`phase6_learning_loop_plan_allowed=True`. It is not yet allowed to write
learning state: `phase6_learning_loop_implementation_allowed=False`,
`phase6_learning_write_allowed=False`, and
`phase6_knowledge_graph_write_allowed=False`.

## 1. Current Handoff State

Phase 5 is certified for Phase 6 planning:

```text
Q5-14 paper_trade_drill_complete=True
Q5-14 phase5_paper_trade_drill_exit_gate_passed=True
Q5-14 blocker_count=0
Q5-15 phase5_certified=True
Q5-15 phase5_exit_gate=True
Q5-15 phase6_handoff_allowed=True
Q5-15 phase7_planning_allowed=True
Q5-15 phase7_proof_credit_allowed=False
Q5E-10/Q5E-11 phase6_learning_loop_plan_allowed=True
Q5E-10/Q5E-11 phase6_learning_loop_implementation_allowed=False
Q5E-10/Q5E-11 phase6_learning_write_allowed=False
Q5E-10/Q5E-11 phase6_knowledge_graph_write_allowed=False
Q5E-10/Q5E-11 live_capital_enabled_count=0
```

The first learning seed is the guarded local paper lifecycle for
`crude_oil_energy_security_disruption`:

- paper-size eligible setup
- staged Alpaca paper-order record
- dry-run request preview
- guarded local submitted paper order
- local broker receipt
- mirrored submitted order
- guarded local open/closed lifecycle records
- postmortem-due marker

This seed is Phase 5 test data. It can be used to test Phase 6 learning
contracts, but it cannot count toward Phase 7 proof.

## 2. Non-Negotiable Boundaries

Every Phase 6 stage must preserve these constraints unless a later explicitly
approved stage changes them:

- no broker POST calls
- no Alpaca POST calls
- no live endpoints
- no prediction-market writes
- no crypto-perps writes
- no live capital
- no autonomous execution
- no Phase 7 proof credit from Phase 5 test trades
- no hidden policy mutation
- no destructive rewrites of Phase 5 artifacts
- no UI-inferred readiness
- no source-quorum credit from Yahoo Finance or Preference/PREF MCP alone

Phase 6 records must be append-only, Event Log backed, provenance linked,
public-safe, and reversible by superseding record.

## 3. Data-Source Rules

- Yahoo Finance remains supplemental market-confirmation context only. It may
  help explain price, volume, and options context around a trade, but it cannot
  be fill truth, broker echo, receipt evidence, reconciliation truth, or a
  single-source learning verdict.
- Preference/PREF MCP remains supplemental multi-source context. Polymarket,
  Kalshi, SEC, vessel, weather, wallet, and other PREF-derived signals can
  enrich postmortems only with provenance and only under source-promotion
  policy. PREF context cannot create source-quorum credit by itself.
- Q-CTRL and quantum outputs remain shadow annotations unless a later hardware
  gate explicitly changes that role. They cannot become execution proof or
  learning truth on their own.
- Learning artifacts must separate execution evidence, market context,
  source provenance, model interpretation, and governance approval.

## 4. Stage Map

| Stage | Name | Purpose | Authority |
| --- | --- | --- | --- |
| Q6-0 | Re-Entry And Plan Gate | Validate Q5E-11, freeze Phase 6 scope, and keep implementation blocked until checks pass. | Planning only |
| Q6-1 | Artifact Schema And Authority Ledger | Define Phase 6 schemas, authority flags, source refs, and event contracts. | Schema only |
| Q6-2 | Learning Source Intake | Read Phase 5 lifecycle artifacts and build a postmortem-due inventory. | Read-only |
| Q6-3 | Closed Trade And Outcome Schema | Normalize closed trade, thesis, risk, execution, receipt, and outcome fields. | Read-only |
| Q6-4 | Postmortem Packet Contract | Create draft postmortem packet shape and validation rules. | Draft only |
| Q6-5 | Postmortem Agent Drafting | Generate a first backend-derived postmortem draft from the Q5E seed. | Draft only |
| Q6-6 | Analysis Sub-Agent Packets | Add catalyst, pricing, regime, execution, and override analysis packets. | Draft only |
| Q6-7 | Reducer And Review Gate | Reduce analysis packets into a human-reviewable postmortem. | Approval gate only |
| Q6-8 | Outcome Linker | Link postmortem outcome to source, strategy, risk, execution, and quantum context. | Link-only |
| Q6-9 | Learning Approval Ledger | Record explicit approval/deferral/rejection before any learning write. | Governance only |
| Q6-10 | Knowledge Graph Staged Writes | Stage approved catalyst-memory writes with supersession semantics. | Staged write only |
| Q6-11 | Knowledge Graph Read Path | Add read/search and cockpit-safe visibility for approved learning entries. | Read path |
| Q6-12 | Model Weight Update Proposals | Produce Bayesian update proposals without applying them. | Proposal only |
| Q6-13 | Trust Score Update Proposals | Produce source trust-score update proposals without applying them. | Proposal only |
| Q6-14 | Shadow Strategy Runner | Replay what-would-have-happened variants without creating candidates/orders. | Replay only |
| Q6-15 | Architect Learning Summary | Summarize policy/strategy recommendations without mutating policy. | Recommendation only |
| Q6-16 | Journal And Cockpit Visibility | Render backend-derived postmortems, learning state, and proposals. | Visibility only |
| Q6-17 | Phase 6 Certification | Certify reviewed postmortem, learning artifacts, and Phase 7 handoff readiness. | Certification only |

## 5. Stage Details

### Q6-0 - Re-Entry And Plan Gate

Objective: prove Phase 6 can start without accidentally opening learning writes.

Work:

- Add a Q6 re-entry check that reads Q5E-11 handoff state.
- Require Q5-14 complete, Q5-15 certified, and Q5E-10/Q5E-11 plan allowed.
- Require all Phase 6 implementation/write flags to remain false.
- Write a Q6-0 audit note.
- Update cockpit only if needed to show Phase 6 remains gated.

Acceptance:

- `phase6_learning_loop_plan_allowed=True`
- `phase6_learning_loop_implementation_allowed=False`
- `phase6_learning_write_allowed=False`
- `phase6_knowledge_graph_write_allowed=False`
- `phase7_proof_credit_allowed=False`
- no broker/live/prediction-market/crypto-perps write counters are nonzero

Expected files:

- `orchestrator/phase6_readiness.py`
- `scripts/check_phase6_readiness.py`
- `docs/qadam-phase-6-q6-0-re-entry-gate-audit-YYYY-MM-DD.md`

Completion note: Q6-0 is complete in
`docs/qadam-phase-6-q6-0-re-entry-gate-audit-2026-05-24.md`. It writes
`data/runtime/phase6_readiness.json`, reports
`phase6_re_entry_gate_passed=True`, keeps
`phase6_learning_loop_implementation_allowed=False`,
`phase6_learning_write_allowed=False`,
`phase6_knowledge_graph_write_allowed=False`, and permits only
`q6_1_artifact_schema_stage_allowed=True`.

### Q6-1 - Artifact Schema And Authority Ledger

Objective: define the common Phase 6 artifact contract before learning data is
created.

Work:

- Add Phase 6 schema versioning.
- Define authority defaults and unsafe counters.
- Define source-ref and provenance conventions.
- Define Event Log event names for postmortem draft, review, staged learning
  write, update proposal, and certification.
- Add dishonest-payload probes for hidden learning writes, policy mutation,
  Phase 7 proof credit, and live capital.

Acceptance:

- Phase 6 authority defaults are all false.
- Validators reject missing provenance, unsafe counters, weak boundary text,
  local path leakage, and unapproved write flags.

Expected files:

- `orchestrator/phase6_artifacts.py`
- `scripts/check_phase6_artifact_schema.py`
- `docs/qadam-phase-6-q6-1-artifact-schema-authority-ledger-audit-YYYY-MM-DD.md`

Completion note: Q6-1 is complete in
`docs/qadam-phase-6-q6-1-artifact-schema-authority-ledger-audit-2026-05-24.md`.
It defines 17 Phase 6 artifact contracts, 20 authority flags defaulting false,
15 unsafe counters defaulting zero, required Event Log categories, source-ref
and provenance conventions, and dishonest-payload probes for hidden learning
writes, policy mutation, Phase 7 proof credit, live capital, weak boundaries,
and local path leakage.

### Q6-2 - Learning Source Intake

Objective: build a read-only inventory of eligible learning inputs.

Work:

- Read Q5E paper lifecycle artifacts and Event Log refs.
- Identify all `postmortem_due` markers.
- Include source refs for Signal Integrity, Strategy Lead, Risk Agent,
  Execution Policy, paper order, broker receipt, position monitor, Yahoo
  Finance context, Preference/PREF MCP context, and Head of Quant annotations.
- Mark missing optional refs without failing open.

Acceptance:

- At least one postmortem-due marker is discovered from the Q5E seed.
- Phase 5 source artifacts are not mutated.
- No learning write is created.

Expected files:

- `orchestrator/phase6_learning_source_intake.py`
- `scripts/check_phase6_learning_source_intake.py`
- `docs/qadam-phase-6-q6-2-learning-source-intake-audit-YYYY-MM-DD.md`

Completion note: Q6-2 is complete in
`docs/qadam-phase-6-q6-2-learning-source-intake-audit-2026-05-24.md`.
It writes `data/runtime/phase6_learning_source_intake.json`, discovers one
`postmortem_due` marker from the Q5E seed, records 20 source refs across 11
required and nine optional contexts, confirms `phase5_hash_mutation_count=0`,
and keeps `learning_write_created=False`,
`knowledge_graph_write_created=False`, `phase7_proof_credit_allowed=False`,
and `unsafe_write_counter_total=0`.

### Q6-3 - Closed Trade And Outcome Schema

Objective: normalize the closed paper trade into an outcome record.

Work:

- Define closed-trade outcome fields: thesis, expected catalyst, actual
  catalyst, entry/exit state, sizing, risk decision, execution path,
  receipt/prewrite refs, market context, source context, invalidation, and
  realized outcome.
- Keep `learning_write_allowed=False`.
- Include unknown/deferred fields rather than inventing missing evidence.

Acceptance:

- One closed-trade outcome record exists for the Q5E seed.
- It distinguishes local lifecycle state from broker truth.
- It has no Knowledge Graph write and no model/trust-score mutation.

Expected files:

- `orchestrator/phase6_closed_trade_outcome.py`
- `scripts/check_phase6_closed_trade_outcome.py`
- `docs/qadam-phase-6-q6-3-closed-trade-outcome-schema-audit-YYYY-MM-DD.md`

Completion note: Q6-3 is complete in
`docs/qadam-phase-6-q6-3-closed-trade-outcome-schema-audit-2026-05-25.md`.
It writes `data/runtime/phase6_closed_trade_outcome.json`, normalizes one
Q5E closed-trade outcome record, separates local guarded lifecycle state from
broker fill truth, carries five unknown fields and six deferred fields for
later postmortem analysis, confirms `source_hash_mutation_count=0`, and keeps
`learning_write_allowed=False`, `knowledge_graph_write_created=False`,
`phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`.

### Q6-4 - Postmortem Packet Contract

Objective: define the packet shape that the Postmortem Agent must fill.

Work:

- Define sections for thesis, timeline, catalyst read, pricing read, regime
  read, execution read, override/readiness read, source quality, mistakes,
  useful signals, harmful signals, uncertainty, and proposed learning actions.
- Require each assertion to cite source refs or be marked as hypothesis.
- Add validation against narrative-only postmortems.

Acceptance:

- Packet validator rejects uncited conclusions and missing outcome refs.
- Draft packets cannot update scores, graph entries, policy, or strategies.

Expected files:

- `orchestrator/phase6_postmortem_packets.py`
- `scripts/check_phase6_postmortem_packet_contract.py`
- `docs/qadam-phase-6-q6-4-postmortem-packet-contract-audit-YYYY-MM-DD.md`

Completion note: Q6-4 is complete in
`docs/qadam-phase-6-q6-4-postmortem-packet-contract-audit-2026-05-25.md`.
It writes `data/runtime/phase6_postmortem_packet_contract.json`, defines 13
required postmortem packet sections, requires assertions to cite source refs or
be marked as hypotheses, rejects narrative-only packets and uncited
conclusions, confirms `source_hash_mutation_count=0`, and keeps
`postmortem_draft_created=False`, `learning_write_created=False`,
`knowledge_graph_write_created=False`, `phase7_proof_credit_allowed=False`,
and `unsafe_write_counter_total=0`.

### Q6-5 - Postmortem Agent Drafting

Objective: generate the first backend-derived postmortem draft from the Q5E
seed.

Work:

- Build deterministic draft generation from source artifacts.
- Do not require an LLM for the first draft.
- Mark all unknowns and missing refs explicitly.
- Emit Event Log entry for draft creation.

Acceptance:

- One postmortem draft exists for the Q5E seed.
- `postmortem_approved=False`
- all learning write flags remain false

Expected files:

- `orchestrator/phase6_postmortem_agent.py`
- `scripts/check_phase6_postmortem_agent.py`
- `docs/qadam-phase-6-q6-5-postmortem-agent-draft-audit-YYYY-MM-DD.md`

Completion note: Q6-5 is complete in
`docs/qadam-phase-6-q6-5-postmortem-agent-draft-audit-2026-05-25.md`.
It writes `data/runtime/phase6_postmortem_draft.json`, creates one
deterministic backend-derived postmortem draft for the Q5E seed, fills all 13
Q6-4 packet sections with 20 source-cited assertions, marks five unknown
fields, six deferred fields, and three missing broker-fill refs, confirms
`source_hash_mutation_count=0`, and keeps `postmortem_approved=False`,
`learning_write_created=False`, `knowledge_graph_write_created=False`,
`model_weight_update_created=False`, `trust_score_update_created=False`,
`policy_mutation_created=False`, `strategy_mutation_created=False`,
`phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`.

### Q6-6 - Analysis Sub-Agent Packets

Objective: split the postmortem into focused analysis packets.

Work:

- Add Catalyst Analysis packet.
- Add Pricing Analysis packet.
- Add Regime Analysis packet.
- Add Execution Analysis packet.
- Add Override Analysis packet.
- Keep these as deterministic/local packets first; LLM summaries can be added
  later behind a separate provider-safe gate.

Acceptance:

- Each packet has source refs, confidence, uncertainty, and missing evidence.
- No packet can approve learning writes or policy changes.

Expected files:

- `orchestrator/phase6_postmortem_analysis.py`
- `scripts/check_phase6_postmortem_analysis.py`
- `docs/qadam-phase-6-q6-6-analysis-packets-audit-YYYY-MM-DD.md`

Completion note: Q6-6 is complete in
`docs/qadam-phase-6-q6-6-analysis-packets-audit-2026-05-25.md`.
It writes `data/runtime/phase6_postmortem_analysis_packets.json`, creates five
deterministic local analysis packets for catalyst, pricing, regime, execution,
and override readiness, carries 10 source-cited claims, five confidence
records, five uncertainty markers, and nine missing-evidence markers, confirms
`source_hash_mutation_count=0`, and keeps `postmortem_approved=False`,
`approval_state=not_requested`, `learning_write_created=False`,
`knowledge_graph_write_created=False`, `model_weight_update_created=False`,
`trust_score_update_created=False`, `policy_mutation_created=False`,
`strategy_mutation_created=False`, `phase7_proof_credit_allowed=False`, and
`unsafe_write_counter_total=0`.

### Q6-7 - Reducer And Review Gate

Objective: reduce the analysis packets into a reviewable postmortem without
approving learning writes.

Work:

- Aggregate analysis packets into one reduced postmortem.
- Compute proposed classifications: useful, harmful, neutral, untestable.
- Add governance states: `draft`, `review_required`, `approved`,
  `rejected`, `deferred`.
- Keep approved state false until explicit review.

Acceptance:

- Reduced postmortem exists.
- Review state is explicit.
- Dishonest approved payload without reviewer/Event Log is rejected.

Expected files:

- `orchestrator/phase6_postmortem_reducer.py`
- `scripts/check_phase6_postmortem_reducer.py`
- `docs/qadam-phase-6-q6-7-reducer-review-gate-audit-YYYY-MM-DD.md`

Completion note: Q6-7 is complete in
`docs/qadam-phase-6-q6-7-reducer-review-gate-audit-2026-05-25.md`.
It writes `data/runtime/phase6_postmortem_reduced_review.json`, reduces five
deterministic analysis packets into one human-reviewable postmortem, reports
`review_state=review_required`, `governance_state=review_required`, proposed
classification counts of useful=2, harmful=0, neutral=1, untestable=2, five
review-queue items, `postmortem_approved=False`, `approval_state=not_requested`,
`approval_logged=False`, `learning_action_count=0`,
`learning_action_approved_count=0`, `source_hash_mutation_count=0`,
`learning_write_created=False`, `knowledge_graph_write_created=False`,
`model_weight_update_created=False`, `trust_score_update_created=False`,
`policy_mutation_created=False`, `strategy_mutation_created=False`,
`phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`.

### Q6-8 - Outcome Linker

Objective: create durable links between outcome, evidence, and system decisions.

Work:

- Link closed-trade outcome to Strategy Lead, Signal Integrity, Risk Agent,
  Execution Policy, staged order, dry-run receipt, local broker receipt,
  Position Monitor, postmortem due marker, source context, Yahoo context,
  Preference/PREF context, and quantum shadow annotation.
- Validate that links are references, not copied private/raw payloads.

Acceptance:

- One complete outcome-link artifact exists for the Q5E seed.
- Missing optional source contexts are represented safely.
- No source artifact is mutated.

Expected files:

- `orchestrator/phase6_outcome_linker.py`
- `scripts/check_phase6_outcome_linker.py`
- `docs/qadam-phase-6-q6-8-outcome-linker-audit-YYYY-MM-DD.md`

Completion note: Q6-8 is complete in
`docs/qadam-phase-6-q6-8-outcome-linker-audit-2026-05-25.md`.
It writes `data/runtime/phase6_outcome_links.json`, creates one complete
reference-only outcome-link artifact for the guarded Q5E seed, reports
`linked_ref_count=21`, `required_link_present_count=12`,
`missing_required_link_count=0`, `optional_link_present_count=9`,
`missing_optional_link_count=0`, `reference_only_link_count=21`,
`raw_payload_copied_count=0`, `private_payload_copied_count=0`,
`local_path_exposed_count=0`, `secret_ref_exposed_count=0`,
`source_hash_mutation_count=0`, `link_write_allowed=False`,
`postmortem_approved=False`, `approval_state=not_requested`,
`approval_logged=False`, `learning_action_count=0`,
`learning_action_approved_count=0`, `learning_write_created=False`,
`knowledge_graph_write_created=False`, `model_weight_update_created=False`,
`trust_score_update_created=False`, `policy_mutation_created=False`,
`strategy_mutation_created=False`, `phase5_test_trades_count_for_phase7=False`,
`phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`.

### Q6-9 - Learning Approval Ledger

Objective: require explicit governance approval before learning writes.

Work:

- Define approval record for postmortem learning actions.
- Include reviewer, scope, approved actions, rejected actions, deferred
  actions, and expiry/review date.
- Require approval before Knowledge Graph staged writes, model-weight proposals,
  trust-score proposals, or strategy-learning proposals can advance.

Acceptance:

- Ledger records approval/deferral/rejection.
- No default approval exists.
- Missing approval blocks all downstream learning writes.

Expected files:

- `orchestrator/phase6_learning_approval.py`
- `scripts/check_phase6_learning_approval.py`
- `docs/qadam-phase-6-q6-9-learning-approval-ledger-audit-YYYY-MM-DD.md`

Completion note: Q6-9 is complete in
`docs/qadam-phase-6-q6-9-learning-approval-ledger-audit-2026-05-25.md`.
It writes `data/runtime/phase6_learning_approval_ledger.json` and, after the
Q6-17 unblock pass, records the Fund Manager instruction as an explicit
deferral for all five proposed postmortem learning actions. It reports
`status=deferred`, `approval_state=deferred`, `approval_logged=True`,
`reviewer_label=fund_manager_ramin`,
`approval_event_log_ref=data/runtime/phase6_learning_approval_ledger_events.jsonl`,
`default_approval_exists=False`,
`missing_approval_blocks_downstream=True`, `approved_action_count=0`,
`rejected_action_count=0`, `deferred_action_count=5`,
`pending_review_action_count=0`, `learning_action_approved_count=0`,
`downstream_advance_allowed=False`, `downstream_blocked_gate_count=4`,
`knowledge_graph_staged_write_allowed=False`,
`model_weight_update_proposal_allowed=False`,
`trust_score_update_proposal_allowed=False`,
`strategy_learning_proposal_allowed=False`, `source_hash_mutation_count=0`,
`learning_write_created=False`, `knowledge_graph_write_created=False`,
`model_weight_update_created=False`, `trust_score_update_created=False`,
`policy_mutation_created=False`, `strategy_mutation_created=False`,
`phase5_test_trades_count_for_phase7=False`,
`phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`.

### Q6-10 - Knowledge Graph Staged Writes

Objective: stage approved catalyst-memory writes before committing graph state.

Work:

- Create staged Knowledge Graph entries from approved postmortem facts.
- Include source refs, catalyst taxonomy, outcome classification, confidence,
  supersession id, and rollback path.
- Keep actual Chroma/graph commit disabled until staged-write validation passes.

Acceptance:

- Staged graph entry exists only when approval permits it.
- `phase6_knowledge_graph_write_allowed` remains false unless explicitly
  changed by this stage's validated gate.
- No destructive overwrite is possible.

Expected files:

- `orchestrator/phase6_knowledge_graph_staging.py`
- `scripts/check_phase6_knowledge_graph_staging.py`
- `docs/qadam-phase-6-q6-10-knowledge-graph-staged-writes-audit-YYYY-MM-DD.md`

Completion note: Q6-10 is complete in
`docs/qadam-phase-6-q6-10-knowledge-graph-staged-writes-audit-2026-05-25.md`.
It writes `data/runtime/phase6_knowledge_graph_staged_writes.json`, carries
the five Q6-9 candidate learning actions forward as blocked action records,
and reports `status=blocked`, `kg_write_state=blocked_pending_learning_approval`,
`source_approval_state=deferred`, `source_approved_action_count=0`,
`candidate_action_count=5`, `blocked_action_count=5`,
`staged_entry_count=0`, `staged_write_allowed=False`,
`knowledge_graph_staged_write_allowed=False`,
`missing_approval_blocks_staging=True`,
`knowledge_graph_commit_allowed=False`, `chroma_write_allowed=False`,
`graph_backend_write_allowed=False`, `actual_graph_commit_created=False`,
`learning_write_created=False`, `knowledge_graph_write_created=False`,
`destructive_overwrite_allowed=False`, `supersession_required=True`,
`rollback_available=True`, `source_hash_mutation_count=0`,
`phase5_source_artifacts_mutated=False`,
`phase5_test_trades_count_for_phase7=False`,
`phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`.

### Q6-11 - Knowledge Graph Read Path

Objective: expose approved learning entries for search and cockpit visibility.

Work:

- Add read/search over approved/staged learning entries.
- Surface source refs, approval state, supersession state, and confidence.
- Keep raw private payloads, local paths, and secrets out of cockpit export.

Acceptance:

- Search returns the Q5E seed learning entry or staged entry.
- Cockpit-safe status exposes counts and states only.
- Read path cannot mutate graph entries.

Expected files:

- `orchestrator/phase6_knowledge_graph_read_path.py`
- `scripts/check_phase6_knowledge_graph_read_path.py`
- `docs/qadam-phase-6-q6-11-knowledge-graph-read-path-audit-YYYY-MM-DD.md`

Completion note: Q6-11 is complete in
`docs/qadam-phase-6-q6-11-knowledge-graph-read-path-audit-2026-05-25.md`.
It writes `data/runtime/phase6_knowledge_graph_read_view.json`, exposes one
read-only Q5E seed-context result because Q6-10 has no approved staged entries,
and reports `status=read_only`,
`read_view_state=read_only_seed_context_available`,
`source_staging_status=blocked`, `source_approval_state=deferred`,
`source_staged_entry_count=0`, `source_blocked_action_count=5`,
`result_count=1`, `seed_result_count=1`, `staged_result_count=0`,
`approved_learning_entry_count=0`, `search_enabled=True`,
`crude_oil_search_result_count=1`, `paper_lifecycle_search_result_count=1`,
`write_allowed=False`, `learning_write_created=False`,
`knowledge_graph_write_created=False`, `knowledge_graph_commit_created=False`,
`chroma_write_created=False`, `graph_backend_write_created=False`,
`raw_payload_copied_count=0`, `private_payload_copied_count=0`,
`local_path_exposed_count=0`, `secret_ref_exposed_count=0`,
`source_hash_mutation_count=0`, `phase5_source_artifacts_mutated=False`,
`phase5_test_trades_count_for_phase7=False`,
`phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`.

### Q6-12 - Model Weight Update Proposals

Objective: produce model-weight update proposals without applying them.

Work:

- Generate Bayesian before/after deltas from approved postmortem evidence.
- Explain evidence, uncertainty, and impact.
- Keep `model_weight_update_applied=False`.

Acceptance:

- Proposal exists with before/after values and audit trail.
- No active model weights are changed.
- Approval state is explicit.

Expected files:

- `orchestrator/phase6_model_weight_updates.py`
- `scripts/check_phase6_model_weight_updates.py`
- `docs/qadam-phase-6-q6-12-model-weight-update-proposals-audit-YYYY-MM-DD.md`

Completion note: Q6-12 is complete in
`docs/qadam-phase-6-q6-12-model-weight-update-proposals-audit-2026-05-25.md`.
It writes `data/runtime/phase6_model_weight_update_proposals.json`, records a
blocked no-op proposal because Q6-9 approval is explicitly deferred, and
reports `status=blocked`, `proposal_state=blocked_pending_learning_approval`,
`source_read_path_status=read_only`, `source_approval_state=deferred`,
`source_approved_learning_entry_count=0`, `source_staged_result_count=0`,
`source_seed_result_count=1`, `proposal_record_count=1`,
`active_proposal_count=0`, `blocked_proposal_count=1`,
`approved_evidence_count=0`, `bayesian_update_count=0`,
`before_weight_count=7`, `after_weight_count=7`, `before_weight_sum=1.0`,
`after_weight_sum=1.0`, `weight_delta_total_abs=0.0`,
`weights_normalized=True`, `model_weight_update_proposal_allowed=False`,
`model_weight_update_proposed=False`, `apply_allowed=False`,
`model_weight_update_allowed=False`, `model_weight_update_applied=False`,
`active_model_weight_mutated=False`, `learning_write_created=False`,
`knowledge_graph_write_created=False`, `knowledge_graph_commit_created=False`,
`chroma_write_created=False`, `graph_backend_write_created=False`,
`model_weight_update_created=False`, `trust_score_update_created=False`,
`policy_mutation_created=False`, `strategy_mutation_created=False`,
`source_hash_mutation_count=0`, `phase5_source_artifacts_mutated=False`,
`phase5_test_trades_count_for_phase7=False`,
`phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`.

### Q6-13 - Trust Score Update Proposals

Objective: produce source trust-score update proposals without applying them.

Work:

- Score source usefulness, error, staleness, provenance quality, and
  corroboration history.
- Keep Yahoo Finance and Preference/PREF bounded by their supplemental roles.
- Keep trust-score application behind explicit approval.

Acceptance:

- Proposal exists with before/after values and source refs.
- No source trust score is changed without approval.
- Single-source or supplemental-only verdicts are rejected.

Expected files:

- `orchestrator/phase6_trust_score_updates.py`
- `scripts/check_phase6_trust_score_updates.py`
- `docs/qadam-phase-6-q6-13-trust-score-update-proposals-audit-YYYY-MM-DD.md`

Completion note: Q6-13 is complete in
`docs/qadam-phase-6-q6-13-trust-score-update-proposals-audit-2026-05-25.md`.
It writes `data/runtime/phase6_trust_score_update_proposals.json`, records
blocked no-op proposals because Q6-9 approval is explicitly deferred, and
reports `status=blocked`, `proposal_state=blocked_pending_learning_approval`,
`source_model_weight_status=blocked`, `source_approval_state=deferred`,
`source_approved_evidence_count=0`, `canonical_source_score_count=35`,
`supplemental_policy_record_count=2`, `proposal_record_count=35`,
`active_proposal_count=0`, `blocked_proposal_count=35`,
`approved_evidence_count=0`, `trust_score_update_count=0`,
`before_score=0.539143`, `after_score=0.539143`,
`score_delta_total_abs=0.0`, `trust_score_update_proposal_allowed=False`,
`trust_score_update_proposed=False`, `apply_allowed=False`,
`trust_score_update_allowed=False`, `trust_score_update_applied=False`,
`active_trust_score_mutated=False`, `canonical_rank_mutated=False`,
`source_quorum_credit_granted=False`, `single_source_verdict_rejected=True`,
`supplemental_only_verdict_rejected=True`,
`yahoo_finance_score_included=False`,
`preference_mcp_source_quorum_credit_allowed=False`,
`learning_write_created=False`, `knowledge_graph_write_created=False`,
`knowledge_graph_commit_created=False`, `chroma_write_created=False`,
`graph_backend_write_created=False`, `model_weight_update_created=False`,
`trust_score_update_created=False`, `policy_mutation_created=False`,
`strategy_mutation_created=False`, `source_hash_mutation_count=0`,
`phase5_source_artifacts_mutated=False`,
`phase5_test_trades_count_for_phase7=False`,
`phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`.

### Q6-14 - Shadow Strategy Runner

Objective: replay what-would-have-happened variants without creating trade
candidates or orders.

Work:

- Run counterfactual strategy variants from approved postmortem facts.
- Compare actual vs hypothetical decisions.
- Mark outputs as replay/proposal only.

Acceptance:

- Replay output exists.
- `trade_candidate_created_count=0`
- `paper_order_allowed_count=0`
- `execution_allowed_count=0`

Expected files:

- `orchestrator/phase6_shadow_strategy_runner.py`
- `scripts/check_phase6_shadow_strategy_runner.py`
- `docs/qadam-phase-6-q6-14-shadow-strategy-runner-audit-YYYY-MM-DD.md`

Completion note: Q6-14 is complete in
`docs/qadam-phase-6-q6-14-shadow-strategy-runner-audit-2026-05-25.md`.
It writes `data/runtime/phase6_shadow_strategy_replay.json`, records blocked
no-op shadow variants because Q6-9 approval is explicitly deferred, and
reports `status=blocked`, `replay_state=blocked_pending_learning_approval`,
`source_trust_score_status=blocked`, `source_approval_state=deferred`,
`source_approved_evidence_count=0`, `approved_fact_count=0`,
`variant_record_count=3`, `active_replay_count=0`,
`blocked_replay_count=3`, `evaluated_variant_count=0`,
`actual_vs_hypothetical_comparison_count=3`,
`evaluated_comparison_count=0`, `replay_output_exists=True`,
`shadow_strategy_replay_allowed=False`, `shadow_strategy_replay_created=False`,
`trade_candidate_creation_allowed=False`, `trade_candidate_created=False`,
`trade_candidate_created_count=0`, `order_creation_allowed=False`,
`paper_order_allowed=False`, `paper_order_allowed_count=0`,
`paper_order_created=False`, `paper_order_created_count=0`,
`execution_allowed=False`, `execution_allowed_count=0`,
`execution_intent_created=False`, `execution_intent_created_count=0`,
`broker_post_allowed=False`, `alpaca_post_allowed=False`,
`broker_post_called_count=0`, `alpaca_post_called_count=0`,
`learning_write_created=False`, `knowledge_graph_write_created=False`,
`knowledge_graph_commit_created=False`, `chroma_write_created=False`,
`graph_backend_write_created=False`, `model_weight_update_created=False`,
`trust_score_update_created=False`, `policy_mutation_created=False`,
`strategy_mutation_created=False`, `source_hash_mutation_count=0`,
`phase5_source_artifacts_mutated=False`,
`phase5_test_trades_count_for_phase7=False`,
`phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`.

### Q6-15 - Architect Learning Summary

Objective: let the Architect Agent recommend changes without mutating policy.

Work:

- Summarize approved postmortem, graph entries, update proposals, and replay
  outputs.
- Produce policy/strategy recommendations.
- Keep all recommendations pending explicit governance.

Acceptance:

- Architect summary exists.
- No policy, source weight, model weight, trust score, or risk limit is changed.
- Recommendations link back to evidence and approval state.

Expected files:

- `orchestrator/phase6_architect_learning.py`
- `scripts/check_phase6_architect_learning.py`
- `docs/qadam-phase-6-q6-15-architect-learning-summary-audit-YYYY-MM-DD.md`

Completion note: Q6-15 is complete in
`docs/qadam-phase-6-q6-15-architect-learning-summary-audit-2026-05-25.md`.
It writes `data/runtime/phase6_architect_learning_summary.json`, records
blocked recommendation records because Q6-9 approval is explicitly deferred,
and reports `status=blocked`,
`summary_state=blocked_pending_learning_approval`,
`source_shadow_replay_status=blocked`,
`source_approval_state=deferred`, `source_approved_fact_count=0`,
`approved_fact_count=0`, `architect_summary_created=True`,
`recommendation_count=4`, `recommendation_record_count=4`,
`active_recommendation_count=0`, `blocked_recommendation_count=4`,
`governance_pending_count=4`, `policy_recommendation_count=1`,
`strategy_recommendation_count=1`, `risk_limit_recommendation_count=1`,
`source_model_trust_recommendation_count=1`,
`recommendation_apply_allowed=False`, `policy_mutation_allowed=False`,
`policy_mutation_created=False`, `strategy_mutation_allowed=False`,
`strategy_mutation_created=False`, `risk_limit_update_allowed=False`,
`risk_limit_update_created=False`, `source_weight_update_allowed=False`,
`source_weight_update_created=False`, `model_weight_update_allowed=False`,
`model_weight_update_created=False`, `trust_score_update_allowed=False`,
`trust_score_update_created=False`, `learning_write_created=False`,
`knowledge_graph_write_created=False`, `knowledge_graph_commit_created=False`,
`chroma_write_created=False`, `graph_backend_write_created=False`,
`source_hash_mutation_count=0`, `phase5_source_artifacts_mutated=False`,
`phase5_test_trades_count_for_phase7=False`,
`phase7_proof_credit_allowed=False`, and `unsafe_write_counter_total=0`.

### Q6-16 - Journal And Cockpit Visibility

Objective: expose Phase 6 state in cockpit and dashboard from backend artifacts.

Work:

- Add public-safe cockpit Phase 6 status.
- Add Mission Control Phase 6 learning state.
- Add dashboard journal/postmortem panel.
- Add display/backend parity and XSS/escaping checks.

Acceptance:

- Dashboard shows postmortem due/resolved counts, approval state, staged graph
  entries, proposals, and blocked authorities.
- UI does not infer readiness.
- Public export contains no raw payloads, local paths, secrets, or broker ids.

Expected files:

- `orchestrator/phase6_cockpit_visibility.py`
- `scripts/check_phase6_cockpit_visibility.py`
- cockpit additions in `orchestrator/cockpit_status.py`
- dashboard additions in `landing-page-repo/dashboard.js`
- `scripts/check_dashboard_phase6_learning_loop.js`
- `docs/qadam-phase-6-q6-16-journal-cockpit-visibility-audit-YYYY-MM-DD.md`

Completion note: Q6-16 is complete in
`docs/qadam-phase-6-q6-16-journal-cockpit-visibility-audit-2026-05-25.md`.
It writes `data/runtime/phase6_cockpit_learning_visibility.json`, exports
`phase6_learning_loop` into the cockpit and static dashboard snapshot, and
renders the Q6-16 Learning Loop Journal Visibility panel from backend artifacts
only. Current state is `status=visible`,
`visibility_state=backend_derived_deferred_learning_visible`,
`learning_state=deferred_learning_visible`,
`backend_derived=True`, `ui_inferred_readiness_count=0`,
`backend_parity_error_count=0`, `postmortem_due_count=1`,
`postmortem_resolved_count=0`, `approval_state=deferred`,
`pending_review_action_count=0`, `deferred_action_count=5`,
`explicitly_deferred_action_count=5`,
`learning_actions_review_satisfied=True`,
`staged_graph_entry_count=0`, `knowledge_graph_read_result_count=1`,
`model_weight_proposal_count=1`, `trust_score_proposal_count=35`,
`shadow_replay_variant_count=3`, `architect_recommendation_count=4`,
`blocked_authority_count=20`, `unsafe_write_counter_total=0`,
`raw_payload_exposed_count=0`, `local_path_exposed_count=0`,
`secret_ref_exposed_count=0`, and `broker_identifier_exposed_count=0`.

### Q6-17 - Phase 6 Certification

Objective: certify Phase 6 learning loop readiness and define the Phase 7
handoff.

Work:

- Validate Q6-0 through Q6-16 artifacts.
- Require reviewed postmortem coverage for all Phase 6 scoped closed trades.
- Require approved or explicitly deferred learning actions.
- Require Knowledge Graph entries/proposals, model/trust proposals, replay
  outputs, Architect summaries, cockpit visibility, and no unsafe authority.
- Determine whether Phase 7 demo-proof planning is allowed.

Acceptance:

- `phase6_certified=True` only when all input gates pass.
- `phase7_demo_proof_planning_allowed=True` may be set after certification.
- `phase7_proof_credit_allowed=False` remains false for Phase 5 test trades.
- Live capital and broker writes remain disabled.

Expected files:

- `orchestrator/phase6_certification.py`
- `scripts/check_phase6_certification.py`
- `docs/qadam-phase-6-q6-17-phase-6-certification-audit-YYYY-MM-DD.md`

Completion note: Q6-17 is complete in
`docs/qadam-phase-6-q6-17-phase-6-certification-audit-2026-05-25.md`.
It writes `data/runtime/phase6_certification.json`, exports
`phase6_certification` into the public cockpit/static dashboard snapshot, and
renders the Q6-17 Phase 6 Certification panel from backend artifacts only.
Current state after the explicit deferral pass is `status=certified`,
`stage_status=phase6_certified`, `phase6_certified=True`,
`phase6_exit_gate=True`, `phase7_demo_proof_planning_allowed=True`,
`phase7_proof_credit_allowed=False`,
`phase5_test_trades_count_for_phase7=False`, `input_gate_count=17`,
`input_gate_passed_count=17`, `input_gate_blocked_count=0`,
`certification_blocker_count=0`,
`postmortem_due_count=1`, `postmortem_resolved_count=0`,
`postmortem_explicitly_deferred_count=1`, `unresolved_postmortem_count=0`,
`reviewed_postmortem_coverage_satisfied=True`,
`approval_state=deferred`, `proposed_action_count=5`,
`approved_action_count=0`, `explicitly_deferred_action_count=5`,
`pending_review_action_count=0`, `learning_actions_review_satisfied=True`,
`knowledge_graph_requirement_satisfied=True`,
`knowledge_graph_read_result_count=1`, `model_weight_proposal_count=1`,
`trust_score_proposal_count=35`, `shadow_replay_variant_count=3`,
`architect_recommendation_count=4`, `cockpit_visibility_status=visible`,
`blocking_unsafe_count=0`, and `unsafe_write_counter_total=0`.

## 6. Recommended Verification Suite

Run the relevant stage check plus the current safety baseline:

```bash
.venv/bin/python scripts/defer_phase6_learning_review_for_certification.py
.venv/bin/python scripts/check_phase6_readiness.py
.venv/bin/python scripts/check_phase6_artifact_schema.py
.venv/bin/python scripts/check_phase6_learning_source_intake.py
.venv/bin/python scripts/check_phase6_closed_trade_outcome.py
.venv/bin/python scripts/check_phase6_postmortem_packet_contract.py
.venv/bin/python scripts/check_phase6_postmortem_agent.py
.venv/bin/python scripts/check_phase6_postmortem_analysis.py
.venv/bin/python scripts/check_phase6_postmortem_reducer.py
.venv/bin/python scripts/check_phase6_outcome_linker.py
.venv/bin/python scripts/check_phase6_learning_approval.py
.venv/bin/python scripts/check_phase6_knowledge_graph_staging.py
.venv/bin/python scripts/check_phase6_knowledge_graph_read_path.py
.venv/bin/python scripts/check_phase6_model_weight_updates.py
.venv/bin/python scripts/check_phase6_trust_score_updates.py
.venv/bin/python scripts/check_phase6_shadow_strategy_runner.py
.venv/bin/python scripts/check_phase6_architect_learning.py
.venv/bin/python scripts/check_phase6_cockpit_visibility.py
.venv/bin/python scripts/check_phase6_certification.py
.venv/bin/python scripts/check_phase5_phase6_handoff.py
.venv/bin/python scripts/check_phase5_certification.py
.venv/bin/python scripts/check_cockpit_status.py
node scripts/check_dashboard_mission_control.js
node scripts/check_dashboard_phase5_phase6_handoff.js
node scripts/check_dashboard_phase6_learning_loop.js
node scripts/check_dashboard_phase6_certification.js
```

## 7. Audit Naming

Use one audit note per stage:

```text
docs/qadam-phase-6-q6-0-re-entry-gate-audit-YYYY-MM-DD.md
docs/qadam-phase-6-q6-1-artifact-schema-authority-ledger-audit-YYYY-MM-DD.md
docs/qadam-phase-6-q6-2-learning-source-intake-audit-YYYY-MM-DD.md
docs/qadam-phase-6-q6-3-closed-trade-outcome-schema-audit-YYYY-MM-DD.md
docs/qadam-phase-6-q6-4-postmortem-packet-contract-audit-YYYY-MM-DD.md
docs/qadam-phase-6-q6-5-postmortem-agent-draft-audit-YYYY-MM-DD.md
docs/qadam-phase-6-q6-6-analysis-packets-audit-YYYY-MM-DD.md
docs/qadam-phase-6-q6-7-reducer-review-gate-audit-YYYY-MM-DD.md
docs/qadam-phase-6-q6-8-outcome-linker-audit-YYYY-MM-DD.md
docs/qadam-phase-6-q6-9-learning-approval-ledger-audit-YYYY-MM-DD.md
docs/qadam-phase-6-q6-10-knowledge-graph-staged-writes-audit-YYYY-MM-DD.md
docs/qadam-phase-6-q6-11-knowledge-graph-read-path-audit-YYYY-MM-DD.md
docs/qadam-phase-6-q6-12-model-weight-update-proposals-audit-YYYY-MM-DD.md
docs/qadam-phase-6-q6-13-trust-score-update-proposals-audit-YYYY-MM-DD.md
docs/qadam-phase-6-q6-14-shadow-strategy-runner-audit-YYYY-MM-DD.md
docs/qadam-phase-6-q6-15-architect-learning-summary-audit-YYYY-MM-DD.md
docs/qadam-phase-6-q6-16-journal-cockpit-visibility-audit-YYYY-MM-DD.md
docs/qadam-phase-6-q6-17-phase-6-certification-audit-YYYY-MM-DD.md
```

## 8. Current Next Step

Q6-17 now certifies Phase 6 after
`scripts/defer_phase6_learning_review_for_certification.py` records the
explicit Fund Manager deferral of the pending Q6 learning approval/postmortem
review and reruns Q6-9 through Q6-17. Current handoff state is
`phase6_certified=True`, `phase6_exit_gate=True`,
`phase7_demo_proof_planning_allowed=True`,
`phase7_proof_credit_allowed=False`, and `live_capital_enabled=False`.

The next executable step is to draft the Phase 7 Demo Proof implementation
plan. Phase 5 test trades and Q6 deferred-learning artifacts still cannot count
as Phase 7 proof credit.
