# Qadam Phase 4 Implementation Plan

This document breaks Phase 4 Strategy Manifestation into staged work that can be implemented one stage at a time.

Phase 4 starts after the 2026-05-23 Phase 3A certification and Q3-11 hardware enablement proposal. Phase 3B hardware implementation remains blocked. Phase 4 may define and approve strategy, but it must not create execution authority.

## 1. Current Phase 4 Boundary

Phase 4 is allowed to turn observed read-only system behavior into an approved strategy document.

Phase 4 is not allowed to:

- create trade candidates
- approve risk
- approve execution
- approve paper orders
- stage paper orders
- submit paper orders
- write to brokers
- enable live capital
- enable quantum provider calls or hardware submissions
- promote Yahoo Finance from supplemental market confirmation into a canonical source without a separate registry decision

Every Phase 4 stage must preserve these counters and flags at zero or false where they exist:

```text
durable_replay_write_authority=False
durable_replay_signal_authority=False
durable_replay_order_authority=False
signal_integrity_trade_candidate_created_count=0
risk_agent_execution_allowed_count=0
risk_agent_paper_order_allowed_count=0
risk_agent_broker_write_allowed_count=0
execution_policy_execution_allowed_count=0
execution_policy_staged_paper_order_allowed_count=0
execution_policy_broker_write_allowed_count=0
staged_paper_order_execution_allowed_count=0
staged_paper_order_broker_write_allowed_count=0
paper_submit_receipt_broker_write_allowed_count=0
paper_account_write_authority=False
paper_account_live_capital_enabled=False
quantum_oracle_hardware_submitted_count=0
quantum_oracle_execution_allowed_count=0
quantum_oracle_paper_order_allowed_count=0
quantum_oracle_trade_candidate_created_count=0
yahoo_finance_execution_allowed=False
yahoo_finance_paper_order_allowed=False
yahoo_finance_broker_write_allowed=False
```

## 2. Current Starting Point

Already implemented or available:

- Phase 2 durable replay can produce non-executable Research Analyst and Strategy Lead context from local Timescale observations.
- Strategy Lead packets are challenge-only and cannot create risk approvals, trade candidates, orders, broker writes, or live-capital authority.
- Signal Integrity includes a market-confirmation policy. Yahoo Finance is supplemental read-only market confirmation only, not an execution venue, not a broker, and not a canonical 36th source.
- The Head of Quant oracle has local/fallback output, provider readiness status, public-safe cockpit status, hardware submission blocked, and Phase 3A certification.
- Resource Registry entries exist in `orchestrator/resource_registry.py` and `docs/qadam-resource-registry.md`.
- Trust Score seed logic exists in `orchestrator/trust_scores.py`; real observation-backed recalculation remains incomplete.
- World-model claim cards exist in `orchestrator/world_model.py`; they are private priors and not factual evidence or trade triggers.
- Event Log exists as an append-only local JSONL fallback in `orchestrator/event_log.py`.
- Cockpit status already exposes public-safe source, cognition, safety, trade, paper-account, Yahoo Finance, and quantum state.

Phase 4 should deepen these into a strategy-governance layer, not an execution layer.

## 3. Stage Overview

| Stage | Name | Purpose | May Implement Now? | Exit Gate |
| --- | --- | --- | --- | --- |
| Q4-0 | Re-Entry Baseline and Safety Contract | Refresh Phase 3A and durable replay truth before Phase 4 work starts. | Yes | Baseline evidence is current and zero-authority. |
| Q4-1 | Phase 4 Artifact Schema | Define the report, manifest, toggle, and approval record shapes. | Yes | Schemas exist and fail closed. |
| Q4-2 | Triple-Mirror Audit | Compare master/spec intent, registered resources, and observed runtime behavior. | Yes | Drift report exists with no automatic promotion. |
| Q4-3 | Data Veracity Audit | Score source coverage, freshness, latency, degradation, and corroboration posture. | Yes | Veracity report separates observed evidence from priors. |
| Q4-4 | Trust Score Recalculation | Replace seed-only scores with observation-backed provisional scores where evidence exists. | Yes | Trust Score matrix explains evidence basis and quarantine state. |
| Q4-5 | Resource Registry Validation | Promote, demote, or mark resources provisional for strategy use. | Yes | Every active strategy reference has a validation status. |
| Q4-6 | World-Model Lens Validation | Mark private world-model frames as validated, provisional, rejected, or untestable. | Yes | No world-model frame can count as factual evidence. |
| Q4-7 | Candidate Strategy Universe | Derive candidate instruments, catalyst classes, source weights, quantum role, and risk assumptions. | Yes | Candidates are strategy drafts, not trade candidates. |
| Q4-8 | Manifested Strategy Draft | Write the human-readable Manifested Strategy Document. | Yes | Draft covers instruments, catalysts, sources, models, quantum role, and risks. |
| Q4-9 | Strategy Toggle Contract | Add inactive/approved-shadow toggle state without execution routing. | Yes | Toggles are visible and logged but cannot execute. |
| Q4-10 | Fund Manager Approval Record | Capture approval, rejection, or required amendments in Event Log. | Yes | Approval event exists, or Phase 4 remains incomplete. |
| Q4-11 | Cockpit Strategy Visibility | Show public-safe strategy manifestation state in Mission Control/cockpit. | Yes | Cockpit displays strategy state without implying execution readiness. |
| Q4-12 | Phase 4 Certification | Certify the strategy manifestation package and Phase 5 readiness boundary. | Yes | Phase 4 exit gate passes and no execution occurred. |

## 4. Stage Q4-0 - Re-Entry Baseline and Safety Contract

Objective: prove the system is still in the certified non-executing state before Phase 4 begins.

Work:

- Run the Phase 3 readiness routine before relying on Phase 3A evidence.
- Run durable replay and Strategy Lead durable context checks.
- Run cockpit status checks to confirm public-safe zero-authority state.
- Record root repo branch, commit, dirty status, and nested `landing-page-repo` status.
- Record Phase 4 safety counters in a Q4-0 audit document.

Verification:

```bash
./scripts/run_pre_phase3_operational_routine.sh --stage phase3-readiness
.venv/bin/python scripts/check_phase2_durable_replay_cycle.py
.venv/bin/python scripts/check_strategy_lead_durable_context.py
.venv/bin/python scripts/check_cockpit_status.py
git status --short
git -C landing-page-repo status --short
```

Acceptance:

- Phase 3 readiness remains green or clearly degrades closed.
- Durable replay is available before using observation-backed evidence.
- Strategy Lead remains challenge-only.
- Cockpit status contains no secret values.
- All execution, paper-order, broker-write, hardware, and live-capital counters remain blocked.

Current status: Complete as of 2026-05-23. Q4-0 refreshed the Phase 3A readiness routine, durable replay cycle, Strategy Lead durable context, cockpit public-safe status, root repo state, and nested static-site repo state. Q4-1 may begin under the same no-execution boundary.

Latest audit record: `docs/qadam-phase-4-q4-0-re-entry-baseline-audit-2026-05-23.md`.

## 5. Stage Q4-1 - Phase 4 Artifact Schema

Objective: define the structured artifacts Phase 4 will produce before implementing audits.

Work:

- Add a Phase 4 schema module or contract document for:
  - Triple-Mirror Audit report.
  - Data Veracity Audit report.
  - Trust Score recalculation report.
  - Resource validation report.
  - World-model validation report.
  - Manifested Strategy Document metadata.
  - Strategy toggle snapshot.
  - Fund Manager approval Event Log payload.
- Define status enums for `draft`, `provisional`, `validated`, `rejected`, `untestable`, `approved_shadow`, and `inactive`.
- Define the Phase 4 authority boundary fields that must always be false.
- Add a check script that validates sample Phase 4 artifacts.

Verification:

```bash
.venv/bin/python -m compileall orchestrator scripts
.venv/bin/python scripts/check_phase4_artifact_schema.py
```

Acceptance:

- Phase 4 artifacts can be validated independently.
- Missing approval fails closed.
- `approved_shadow` does not imply execution, order, broker, or live-capital authority.
- Schema payloads are public-safe by default.

Current status: Complete as of 2026-05-23. Q4-1 added `orchestrator/phase4_artifacts.py` and `scripts/check_phase4_artifact_schema.py`, covering all eight Phase 4 artifact contracts, seven status enums, shared false authority boundaries, approval fail-closed behavior, and `approved_shadow` non-execution behavior.

Latest audit record: `docs/qadam-phase-4-q4-1-artifact-schema-audit-2026-05-23.md`.

## 6. Stage Q4-2 - Triple-Mirror Audit

Objective: compare what Qadam says it should be, what its registered resources imply, and what the runtime actually does.

Work:

- Build a Triple-Mirror Audit that compares:
  - master implementation plan and modular plan expectations
  - Resource Registry references and mapped modules
  - observed runtime health from cockpit status, durable replay, Strategy Lead, Signal Integrity, Risk Agent, Execution Policy, paper account, Yahoo Finance, and Head of Quant
- Flag drift as `aligned`, `missing_runtime`, `implemented_not_documented`, `resource_unmapped`, or `authority_mismatch`.
- Write a JSON artifact and a human-readable audit note.
- Keep all findings advisory; no resource or strategy is promoted automatically.

Verification:

```bash
.venv/bin/python scripts/check_phase4_triple_mirror_audit.py
```

Acceptance:

- Drift report is generated.
- Any authority mismatch fails the check.
- Runtime behavior is observed, not inferred from docs alone.
- The report names gaps without creating new authority.

Current status: Complete as of 2026-05-23. Q4-2 added `orchestrator/phase4_triple_mirror.py` and `scripts/check_phase4_triple_mirror_audit.py`. The audit writes `data/runtime/phase4_triple_mirror_audit.json`, compares plan, Resource Registry, and runtime mirrors, and fails closed on authority mismatch while remaining advisory only.

Latest audit record: `docs/qadam-phase-4-q4-2-triple-mirror-audit-2026-05-23.md`.

## 7. Stage Q4-3 - Data Veracity Audit

Objective: score the data environment using observed replay/live-source evidence rather than seed priors alone.

Work:

- Use durable replay status, source observation coverage, source degradation, latency/freshness metadata, and market-confirmation policy results.
- Separate canonical 35-source coverage from supplemental Yahoo Finance market-confirmation coverage.
- Treat Yahoo Finance as corroboration only; a Yahoo-only market confirmation remains a hold condition.
- Produce source-level veracity fields:
  - `coverage_status`
  - `freshness_status`
  - `latency_status`
  - `degradation_status`
  - `corroboration_status`
  - `evidence_basis`
  - `routing_boundary`
- Add a check script that proves the report contains no broker, fill, receipt, reconciliation, or execution authority.

Verification:

```bash
.venv/bin/python scripts/check_phase4_data_veracity_audit.py
```

Acceptance:

- Canonical and supplemental sources are clearly separated.
- Every scored source has an evidence basis.
- Missing or degraded evidence reduces confidence or quarantines the source.
- No source can create a trade candidate or order.

Current status: Complete as of 2026-05-23, amended by PREF-6 on 2026-05-24. Q4-3 added `orchestrator/phase4_data_veracity.py` and `scripts/check_phase4_data_veracity_audit.py`. The audit writes `data/runtime/phase4_data_veracity_audit.json`, scores all 35 canonical sources plus Yahoo Finance and Preference/PREF MCP as separate supplemental sources, quarantines degraded evidence, and rejects source-level authority flags.

Latest audit record: `docs/qadam-phase-4-q4-3-data-veracity-audit-2026-05-23.md`.

## 8. Stage Q4-4 - Trust Score Recalculation

Objective: move Trust Scores from seed-only priors toward observation-backed provisional scores.

Work:

- Extend the Trust Score service with a Phase 4 recalculation report.
- Preserve seed score, observed score, final provisional score, and reason codes.
- Apply quarantine below the existing trust threshold.
- Require observation evidence for upgrades.
- Record whether the score came from deterministic sample, durable replay, live read-only observation, or supplemental market confirmation.
- Ensure Yahoo Finance can only affect market-confirmation notes, not canonical source rank, unless a future source-registry decision changes that.

Verification:

```bash
.venv/bin/python scripts/check_trust_score_seed.py
.venv/bin/python scripts/check_phase4_trust_score_recalculation.py
```

Acceptance:

- Trust Score matrix exists.
- Each changed score has an evidence basis and reason code.
- Quarantined sources are explicit.
- Scores cannot route execution or paper orders.

Current status: Complete as of 2026-05-23, amended by PREF-6 on 2026-05-24. Q4-4 added `orchestrator/phase4_trust_scores.py` and `scripts/check_phase4_trust_score_recalculation.py`. The recalculation writes `data/runtime/phase4_trust_score_recalculation.json`, preserves seed scores, records observed and final provisional scores, quarantines degraded evidence below the trust threshold, and keeps Yahoo Finance and Preference/PREF MCP out of canonical scoring and canonical rank impact.

Latest audit record: `docs/qadam-phase-4-q4-4-trust-score-recalculation-audit-2026-05-23.md`.

## 9. Stage Q4-5 - Resource Registry Validation

Objective: decide which non-live resources can inform the Manifested Strategy Document.

Work:

- Add validation metadata for each Resource Registry entry used by Phase 4.
- Classify resources as:
  - `validated_strategy_reference`
  - `architecture_reference`
  - `provisional_reference`
  - `rejected_reference`
  - `private_foundational_prior`
- Require every active strategy reference to map to at least one module, one decision note, and one risk boundary.
- Keep private world-model material separate from live data sources.
- Produce a resource validation report.

Verification:

```bash
.venv/bin/python scripts/check_phase4_resource_validation.py
```

Acceptance:

- Every resource used by an active strategy is validated or explicitly provisional.
- Resource Registry entries are not treated as live observations.
- Rejected resources cannot appear in active strategy provenance.

Current status: Complete as of 2026-05-23, amended by PREF-6 on 2026-05-24. Q4-5 added `orchestrator/phase4_resource_validation.py` and `scripts/check_phase4_resource_validation.py`. The validation writes `data/runtime/phase4_resource_validation.json`, now classifies all 30 Resource Registry entries including Preference/PREF MCP as a `supplemental_data_plane` architecture reference, marks 7 as validated strategy references, 17 as architecture references, 5 as provisional references, 1 as a private foundational prior, and keeps active strategy references, live observations, rejected-active references, and authority violations at zero.

Latest audit record: `docs/qadam-phase-4-q4-5-resource-registry-validation-audit-2026-05-23.md`.

## 10. Stage Q4-6 - World-Model Lens Validation

Objective: score private world-model frames against observed outcomes without letting them become evidence by themselves.

Work:

- Add Phase 4 validation fields to world-model claim cards or a companion report:
  - `validation_status`
  - `observed_support`
  - `observed_contradiction`
  - `testability`
  - `allowed_strategy_role`
  - `evidence_boundary`
- Classify each frame as `validated`, `provisional`, `rejected`, or `untestable`.
- Require live-source or durable replay corroboration for any `validated` status.
- Keep world-model output as hypothesis generation and red-team prompting only.

Verification:

```bash
.venv/bin/python scripts/check_phase4_world_model_validation.py
```

Acceptance:

- Private frames used by active strategies have validation status.
- Untestable or rejected frames cannot increase confidence.
- World-model frames remain private priors, not factual evidence or trade triggers.

Current status: Complete as of 2026-05-23. Q4-6 added `orchestrator/phase4_world_model_validation.py` and `scripts/check_phase4_world_model_validation.py`. The validation writes `data/runtime/phase4_world_model_validation.json`, classifies all 5 world-model claim cards as provisional, records 29 durable replay source checks, keeps observed support, observed contradiction, active strategy frames, confidence increase, factual evidence, trade triggers, and authority violations at zero, and redacts private claim text from the public-safe artifact.

Latest audit record: `docs/qadam-phase-4-q4-6-world-model-lens-validation-audit-2026-05-23.md`.

## 11. Stage Q4-7 - Candidate Strategy Universe

Objective: convert audits into draft strategy candidates without creating trade candidates.

Work:

- Derive candidate strategy families from:
  - durable replay observations
  - Signal Integrity review patterns
  - Strategy Lead challenge packets
  - Data Veracity Audit results
  - Trust Score recalculation
  - Resource Registry validation
  - World-model validation
  - Head of Quant shadow annotations
- For each candidate strategy family, define:
  - instrument universe
  - catalyst classes
  - required source groups
  - source weights
  - model weights
  - market-confirmation requirements
  - quantum role
  - risk assumptions
  - invalidation conditions
  - no-trade conditions
- Name the object `strategy_candidate` or `strategy_family_candidate`; do not use `trade_candidate`.

Verification:

```bash
.venv/bin/python scripts/check_phase4_candidate_strategy_universe.py
```

Acceptance:

- Strategy candidates exist only as draft strategic hypotheses.
- Every candidate includes no-trade and invalidation conditions.
- No candidate can be passed to Risk Agent or Execution Policy as an executable object.

Current status: Complete as of 2026-05-23. Q4-7 added `candidate_strategy_universe` as the ninth Phase 4 artifact contract, plus `orchestrator/phase4_candidate_strategy_universe.py` and `scripts/check_phase4_candidate_strategy_universe.py`. The universe writes `data/runtime/phase4_candidate_strategy_universe.json`, defines 5 `strategy_family_candidate` draft hypotheses across prediction markets, crude oil, defence, silver, and semiconductors, and keeps trade candidates, Risk Agent handoff, Execution Policy handoff, execution, paper orders, broker writes, live capital, and authority violations at zero.

Latest audit record: `docs/qadam-phase-4-q4-7-candidate-strategy-universe-audit-2026-05-23.md`.

## 12. Stage Q4-8 - Manifested Strategy Draft

Objective: write the first complete Manifested Strategy Document.

Work:

- Generate `docs/qadam-manifested-strategy.md`.
- Include:
  - active instruments
  - excluded instruments
  - catalyst classes
  - source weights
  - model weights
  - Head of Quant role
  - Yahoo Finance supplemental market-confirmation role
  - private world-model role and boundaries
  - risk assumptions
  - no-trade conditions
  - approval requirements
  - Phase 5 handoff constraints
- Make the draft explicit that it is not execution approval.

Verification:

```bash
.venv/bin/python scripts/check_phase4_manifested_strategy.py
rg -n "active instruments|catalyst classes|source weights|model weights|quantum role|risk assumptions|No execution" docs/qadam-manifested-strategy.md
```

Acceptance:

- Manifested Strategy draft exists.
- All Phase 4 exit-gate fields are present.
- The draft distinguishes strategy approval from trade approval.

Current status: Complete as of 2026-05-23. Q4-8 added `docs/qadam-manifested-strategy.md`, `orchestrator/phase4_manifested_strategy.py`, and `scripts/check_phase4_manifested_strategy.py`. The draft covers 5 active instruments, 14 catalyst classes, 5 strategy-family candidates, source weights, model weights, market-confirmation requirements, quantum role, world-model boundaries, risk assumptions, invalidation conditions, no-trade conditions, approval requirements, and an explicit no-execution boundary. The metadata artifact writes `data/runtime/phase4_manifested_strategy_metadata.json` with fingerprint `4cf64304cd3438d8ec7bc35412311e3c9c453dcfaca4b9471186fed40f6f3362`, approval still `not_requested`, approved-shadow readiness false, and trade candidate count zero.

Latest audit record: `docs/qadam-phase-4-q4-8-manifested-strategy-draft-audit-2026-05-23.md`.

## 13. Stage Q4-9 - Strategy Toggle Contract

Objective: create visible strategy toggles that control strategy availability for future phases without routing execution.

Work:

- Define toggle states:
  - `inactive`
  - `draft`
  - `approved_shadow`
  - `suspended`
  - `retired`
- Add a local strategy-toggle artifact or module.
- Ensure toggles can be logged to Event Log.
- Ensure `approved_shadow` means approved for future Phase 5 orchestration design only, not approved for orders.
- Add guardrails preventing toggles from calling Risk Agent, Execution Policy, broker adapters, paper-submit receipts, or live-capital code.

Verification:

```bash
.venv/bin/python scripts/check_phase4_strategy_toggles.py
.venv/bin/python scripts/check_event_log.py
```

Acceptance:

- Toggles exist and are observable.
- Toggle changes write Event Log entries.
- No toggle state enables execution or paper orders.

Current status: Complete as of 2026-05-23 and approved-shadow after Q5-0 on
2026-05-24. Q4-9 added `orchestrator/phase4_strategy_toggles.py` and
`scripts/check_phase4_strategy_toggles.py`. The toggle snapshot writes
`data/runtime/phase4_strategy_toggle_snapshot.json` and a local Event Log record
at `data/runtime/phase4_strategy_toggle_events.jsonl`. All 5 strategy-family
toggles are visible; after explicit approval they are `approved_shadow`, which
means approved for Phase 5 orchestration design only. Trade candidates, Risk
Agent handoff, Execution Policy handoff, execution, paper orders, broker writes,
live capital, quantum provider calls, hardware submission, and schedulers remain
disabled. Audits:
`docs/qadam-phase-4-q4-9-strategy-toggle-contract-audit-2026-05-23.md` and
`docs/qadam-phase-5-q5-0-re-entry-gate-audit-2026-05-24.md`.

## 14. Stage Q4-10 - Fund Manager Approval Record

Objective: record Ramin's approval, rejection, or amendment request in the Event Log.

Work:

- Add an approval command or script that writes a structured Event Log entry.
- Approval payload must include:
  - strategy document version
  - strategy artifact fingerprint
  - approved strategy families
  - rejected strategy families
  - required amendments
  - explicit no-execution boundary
  - approver identity label
  - approval timestamp
- Require exact approval of the Manifested Strategy Document before Phase 4 can certify.

Verification:

```bash
.venv/bin/python scripts/check_phase4_approval_record.py
```

Acceptance:

- Approval, rejection, or amendment state is replayable from Event Log.
- Missing approval blocks Phase 4 certification.
- Approval does not enable broker writes, paper orders, or live capital.

Current status: Complete as of 2026-05-23 and approved on 2026-05-24. Q4-10
added `orchestrator/phase4_approval_record.py` and
`scripts/check_phase4_approval_record.py`. The approval record writes
`data/runtime/phase4_fund_manager_approval_event.json` and a local Event Log
record at `data/runtime/phase4_approval_events.jsonl`. Q5-0 later logged the
explicit Fund Manager approval; the runtime state is now `approved`, all 5
strategy toggles are `approved_shadow`, and trade candidates, Risk Agent handoff,
Execution Policy handoff, execution, paper orders, broker writes, live capital,
quantum provider calls, hardware submission, and schedulers remain disabled.
Audits: `docs/qadam-phase-4-q4-10-fund-manager-approval-record-audit-2026-05-23.md`
and `docs/qadam-phase-5-q5-0-re-entry-gate-audit-2026-05-24.md`.

## 15. Stage Q4-11 - Cockpit Strategy Visibility

Objective: expose Phase 4 status to the Fund Manager without implying execution readiness.

Work:

- Add public-safe Phase 4 status to cockpit status.
- Show:
  - Phase 4 stage status
  - audit completion state
  - strategy document status
  - approved-shadow strategy toggles
  - approval event status
  - no-execution boundary
- Update static cockpit rendering if needed.
- Keep all strategy details public-safe and secret-free.

Verification:

```bash
.venv/bin/python scripts/check_cockpit_status.py
node --check landing-page-repo/dashboard.js
node scripts/check_dashboard_renderer.js
node scripts/check_dashboard_mission_control.js
node scripts/check_dashboard_phase4_strategy.js
```

Acceptance:

- Cockpit reflects Phase 4 state.
- Dashboard language separates strategy approval from paper/live execution.
- Public status contains no private strategy text that should remain local.
- Cockpit does not expose broker-write, paper-order, hardware, or live-capital authority.

Current status: Complete as of 2026-05-23 and updated by Q5-0 on 2026-05-24.
Q4-11 added public-safe `phase4_strategy` status to the cockpit export,
surfaced Phase 4 state in Mission Control, and added a dedicated Strategy
Manifestation cockpit panel. The panel now shows Q4-12 certified state, validated
strategy document state, `approved` approval state, 5 visible approved-shadow
strategy toggles, the Yahoo Finance supplemental market-confirmation boundary,
and the no-execution boundary. Trade candidates, risk approval, execution, paper
orders, broker writes, quantum provider calls, hardware submission, schedulers,
and live capital remain disabled. Audits:
`docs/qadam-phase-4-q4-11-cockpit-strategy-visibility-audit-2026-05-23.md` and
`docs/qadam-phase-5-q5-0-re-entry-gate-audit-2026-05-24.md`.

## 16. Stage Q4-12 - Phase 4 Certification

Objective: certify Phase 4 as complete and define the exact handoff boundary to Phase 5.

Work:

- Run every Phase 4 check script.
- Run the existing Phase 2/3 zero-authority checks.
- Confirm the Manifested Strategy Document exists and is approved.
- Confirm strategy toggles are logged and remain non-executing.
- Confirm private world-model frames are validated, provisional, rejected, or untestable.
- Confirm active instruments, catalyst classes, source weights, model weights, quantum role, and risk assumptions are explicit.
- Write a Phase 4 certification audit document.
- Update the master implementation plan with the Phase 4 certification outcome.

Verification:

```bash
./scripts/run_pre_phase3_operational_routine.sh --stage phase3-readiness
.venv/bin/python scripts/check_phase2_durable_replay_cycle.py
.venv/bin/python scripts/check_strategy_lead_durable_context.py
.venv/bin/python scripts/check_phase4_artifact_schema.py
.venv/bin/python scripts/check_phase4_triple_mirror_audit.py
.venv/bin/python scripts/check_phase4_data_veracity_audit.py
.venv/bin/python scripts/check_phase4_trust_score_recalculation.py
.venv/bin/python scripts/check_phase4_resource_validation.py
.venv/bin/python scripts/check_phase4_world_model_validation.py
.venv/bin/python scripts/check_phase4_candidate_strategy_universe.py
.venv/bin/python scripts/check_phase4_manifested_strategy.py
.venv/bin/python scripts/check_phase4_strategy_toggles.py
.venv/bin/python scripts/check_phase4_approval_record.py
.venv/bin/python scripts/check_phase4_certification.py
.venv/bin/python scripts/check_cockpit_status.py
```

Acceptance:

- Approved Manifested Strategy Document exists.
- Active instruments, catalyst classes, source weights, model weights, quantum role, and risk assumptions are explicit.
- Private world-model frames used by active strategies are marked validated, provisional, rejected, or untestable.
- Approval is logged in Event Log.
- Phase 5 can begin only as guarded orchestration design.
- No execution occurred before approval.
- Broker-write, paper-order, hardware-submission, provider-call, scheduler, and live-capital authority remain disabled.

Current status: Certified on 2026-05-24 after being evaluated as fail-closed on
2026-05-23. Q4-12 added
`orchestrator/phase4_certification.py` and `scripts/check_phase4_certification.py`.
The certification artifact writes `data/runtime/phase4_certification.json` and a
local Event Log record at `data/runtime/phase4_certification_events.jsonl`. All
Phase 4 artifacts validate, the Manifested Strategy Document is complete, the
strategy universe has explicit active instruments, catalyst classes, source
weights, model weights, quantum role, and risk assumptions, world-model frames
are classified, Phase 2/3 zero-authority posture holds, the replayable Fund
Manager approval record is `approved`, and Phase 5 handoff is allowed. Audits:
`docs/qadam-phase-4-q4-12-phase-4-certification-audit-2026-05-23.md` and
`docs/qadam-phase-5-q5-0-re-entry-gate-audit-2026-05-24.md`.

Data-source closeout update as of 2026-05-24: Q4-10 and Q4-12 now include the
Yahoo Finance and Preference/PREF MCP amendments that landed after the original
Q4-12 evaluation. Yahoo Finance remains supplemental market confirmation only.
Preference/PREF MCP remains a supplemental data plane; its PREF-12
source-promotion decision artifact must be validated, must promote zero
upstream sources, must keep the canonical source count at 35, and must keep
`preference_mcp_source_36=False` before Phase 4 can certify. The closeout is
recorded in
`docs/qadam-phase-4-data-source-closeout-audit-2026-05-24.md`.

## 17. Phase 4 Done Definition

Phase 4 is complete when:

- Q4-0 through Q4-12 are implemented and verified.
- `docs/qadam-manifested-strategy.md` exists.
- The Manifested Strategy Document has a replayable Fund Manager approval event.
- Strategy toggles exist only in non-executing states.
- Cockpit status shows Phase 4 state without implying paper/live readiness.
- The master implementation plan names Phase 5 as the next build target.

Q4-12 is implemented and certified after Q5-0 logged explicit Fund Manager
approval. All implementable Phase 4 work for the current Yahoo Finance and
Preference/PREF MCP data-source model is complete.

Pre-Phase-5 readiness update as of 2026-05-24: `docs/qadam-phase-5-layer-b-readiness-audit-2026-05-24.md`
adds a fail-closed Layer B readiness gate. Q5-0 later logged approval and reran
the gate, so Phase 5 implementation is now allowed while orchestration start
remains false.

Qadam can now proceed to Q5-1 - Layer B Artifact Schema And Authority Ledger. It
still cannot trade, stage orders, submit paper orders, write brokers, send live
execution alerts, or enable live capital until later Q5 gates explicitly create
and verify those contracts.
