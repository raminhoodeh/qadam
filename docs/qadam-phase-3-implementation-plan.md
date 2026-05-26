# Qadam Phase 3 Implementation Plan

This document breaks Phase 3 Quantum Integration into staged work that can be implemented one stage at a time.

It starts from the 2026-05-22 pre-Phase-3 certification in `docs/qadam-pre-phase-3-certification-2026-05-22.md`. That certification permits Phase 3 to resume only as non-executing provider and scheduler readiness work.

## 1. Current Phase 3 Boundary

Phase 3 is allowed to proceed, but only under these locks:

- no quantum hardware submissions
- no hardware scheduler enablement
- no broker writes
- no trade-candidate creation from Head of Quant output
- no execution approvals
- no paper-order approvals
- no paper-order submission
- no live-capital enablement

Every stage must preserve these counters at zero:

```text
quantum_oracle_hardware_submitted_count=0
quantum_oracle_hardware_submission_allowed_count=0
quantum_oracle_hardware_scheduler_enabled_count=0
quantum_oracle_execution_allowed_count=0
quantum_oracle_paper_order_allowed_count=0
quantum_oracle_trade_candidate_created_count=0
```

## 2. Current Starting Point

Already implemented:

- `orchestrator/quantum.py` defines `QuantumProvider`, `QuantumBackend`, `QuantumOracleJob`, `QuantumOracleResult`, local validation, deterministic classical fallback, optional Qiskit Aer local backend, circuit blueprint, measurement counts, input fingerprint, weekly cadence metadata, JSONL result storage, and public-safe health summary.
- `scripts/check_quantum_oracle.py` validates Pattern Recognition and Strategy Collapse / Ambiguity Score jobs.
- Cockpit status exposes sanitized Head of Quant state.
- The pre-Phase-3 routine is repeatable through `scripts/run_pre_phase3_operational_routine.sh`.
- Durable replay is green when OrbStack/Postgres is running.
- Phase 2 can produce non-executable Research Analyst and Strategy Lead context from durable replay.
- Signal Integrity includes market-confirmation policy, including Yahoo Finance as supplemental context only.

Current provider posture from local secret/status checks:

```text
qiskit_aer=missing_optional_package; credential_configured=True
qctrl=configured; credential_configured=True
ibm_quantum=missing_secret; credential_configured=False
aws_braket=missing_secret; credential_configured=False
```

The Q-CTRL API key is already configured locally. It must remain a local secret only, stored outside Git. Do not paste it into docs, logs, dashboard status, screenshots, or chat. Phase 3 may use this fact for readiness status, but no Q-CTRL API call should happen unless a later stage explicitly asks for an opt-in live readiness probe.

## 3. Stage Overview

| Stage | Name | Purpose | May Implement Now? | Exit Gate |
| --- | --- | --- | --- | --- |
| Q3-0 | Re-Entry Guard | Refresh pre-Phase-3 truth before any Phase 3 work. | Yes | P3-9 evidence is current and zero-authority. |
| Q3-1 | Provider Readiness Ledger | Make quantum provider readiness explicit and public-safe. | Yes | Qiskit, Q-CTRL, IBM, and AWS states are exported without secrets or calls. |
| Q3-2 | Local Simulator Track | Promote local Qiskit/Aer validation when dependencies exist. | Yes | Local simulator passes or degrades to classical fallback. |
| Q3-3 | Q-CTRL Readiness Contract | Treat Q-CTRL as configured for future error suppression without side effects. | Yes | Credential-aware status exists; default check makes no provider call. |
| Q3-4 | Hardware Provider Stubs | Add IBM/AWS readiness contracts without hardware submission. | Yes | Missing/configured state is public-safe; no backend job route exists. |
| Q3-5 | Scheduler Dry Contract | Model weekly oracle scheduling without enabling a scheduler. | Yes | Next-due jobs are described, not submitted. |
| Q3-6 | Oracle Input Contract | Define exactly which Signal Integrity reviews can feed Head of Quant. | Yes | Inputs require durable evidence and market-confirmation context. |
| Q3-7 | Oracle Output Routing | Route Head of Quant output as shadow annotation only. | Yes | No trade candidate, risk approval, or order state can be created. |
| Q3-8 | Cockpit Phase 3 Visibility | Show provider/scheduler/input/output state safely. | Yes | Cockpit matches local checks and exposes no secrets. |
| Q3-9 | Phase 3 Operational Routine | Add one repeatable Phase 3 readiness command. | Yes | Full Phase 3 readiness routine returns ok. |
| Q3-10 | Phase 3A Certification | Certify provider/scheduler readiness. | Yes | Non-executing Phase 3A complete. |
| Q3-11 | Hardware Enablement Proposal | Write the later approval plan for actual hardware probes. | Docs only | A separate future certification is required before any hardware call. |

## 4. Stage Q3-0 - Re-Entry Guard

Objective: ensure the local system is still in the certified pre-Phase-3 state before touching Phase 3.

Work:

- Run the pre-Phase-3 routine.
- Run the quantum scaffold check.
- Confirm local Postgres/Timescale replay is green, or stop if durable replay is unavailable.
- Record branch, commit, dirty worktree status, and nested `landing-page-repo` status.
- Confirm Q-CTRL is configured without printing the key.

Verification:

```bash
./scripts/run_pre_phase3_operational_routine.sh --stage all
.venv/bin/python scripts/check_quantum_oracle.py
git status --short
git -C landing-page-repo status --short
```

Acceptance:

- `pre_phase3_routine=ok`
- `quantum_oracle_check=ok`
- durable replay is green
- all quantum authority counters remain zero
- Q-CTRL status is credential-configured without exposing the secret value

Latest audit record: `docs/qadam-phase-3-q3-0-re-entry-guard-audit-2026-05-23.md`.

## 5. Stage Q3-1 - Provider Readiness Ledger

Objective: make quantum provider readiness explicit, structured, and public-safe.

Work:

- Extend or validate `quantum_providers()` as the single provider-readiness source.
- Keep Qiskit Aer, Q-CTRL, IBM Quantum, and AWS Braket in one structured ledger.
- Distinguish these states:
  - `available_without_secret`
  - `missing_optional_package`
  - `configured`
  - `missing_secret`
  - `disabled_by_policy`
- Add a provider-readiness check script if the existing quantum check is too broad.
- Ensure provider status can be consumed by cockpit without secret names becoming values.

Verification:

```bash
.venv/bin/python scripts/check_quantum_oracle.py
.venv/bin/python -m compileall orchestrator/quantum.py scripts/check_quantum_oracle.py
```

Acceptance:

- Q-CTRL appears as configured when `QCTRL_API_KEY` exists locally.
- IBM/AWS can remain missing without blocking Phase 3A.
- No provider readiness check submits jobs.
- No provider readiness check calls broker, order, or live-capital code.
- Public status contains no raw tokens, local secret-file contents, or cloud response payloads.

Latest audit record: `docs/qadam-phase-3-q3-1-provider-readiness-ledger-audit-2026-05-23.md`.

## 6. Stage Q3-2 - Local Simulator Track

Objective: make the local simulator path boring before any provider or hardware work.

Work:

- Keep deterministic classical fallback as the always-available baseline.
- Add explicit local dependency guidance for `qiskit` and `qiskit-aer`; see `docs/qadam-quantum-local-simulator.md`.
- When dependencies exist, require Qiskit Aer to run the same two bounded jobs:
  - Pattern Recognition
  - Strategy Collapse / Ambiguity Score
- Keep the output schema identical across Qiskit Aer and classical fallback.
- Add failure handling so import/runtime errors degrade to classical fallback.

Verification:

```bash
.venv/bin/python scripts/check_quantum_local_simulator.py
.venv/bin/python scripts/check_quantum_oracle.py
```

Optional after deliberately installing local simulator dependencies:

```bash
.venv/bin/python -m pip install -e ".[quantum-local]"
.venv/bin/python -c "import qiskit, qiskit_aer; print('qiskit_local_ready=true')"
.venv/bin/python scripts/check_quantum_local_simulator.py
.venv/bin/python scripts/check_quantum_oracle.py
```

Acceptance:

- Local simulator output validates through the existing result schema.
- Classical fallback remains available.
- No hardware provider is selected.
- No hardware submission flag can become true.

Latest audit record: `docs/qadam-phase-3-q3-2-local-simulator-track-audit-2026-05-23.md`.

## 7. Stage Q3-3 - Q-CTRL Readiness Contract

Objective: use the existing Q-CTRL credential as readiness context without creating side effects.

Work:

- Treat Q-CTRL as future error-suppression/optimization support, not as a hardware backend.
- Add a Q-CTRL readiness section to the provider ledger if needed:
  - credential configured
  - SDK/package importable
  - live probe disabled by default
  - no optimization job submitted
  - no hardware job submitted
- If a later live readiness probe is needed, require an explicit flag such as `--live-qctrl-readiness`.
- Live readiness, if added later, must be metadata-only and must not submit an optimization, circuit, or hardware task.

Verification:

```bash
.venv/bin/python scripts/check_qctrl_readiness.py
.venv/bin/python scripts/check_quantum_oracle.py
./scripts/run_pre_phase3_operational_routine.sh --stage secret-scan
```

Acceptance:

- Q-CTRL credential presence is confirmed as configured without displaying the key.
- Default checks make zero Q-CTRL API calls.
- No raw provider responses are stored in public status.
- Q-CTRL cannot change recommendations, create signals, or advance execution.

Latest audit record: `docs/qadam-phase-3-q3-3-qctrl-readiness-contract-audit-2026-05-23.md`.

## 8. Stage Q3-4 - IBM/AWS Hardware Provider Stubs

Objective: prepare provider contracts for IBM Quantum and AWS Braket without enabling hardware jobs.

Work:

- Keep IBM Quantum and AWS Braket as future hardware providers.
- Add public-safe readiness states for missing/configured credentials.
- Define provider-specific prerequisites:
  - IBM Quantum token present
  - AWS region and credentials present
  - local simulator validation passed
  - explicit hardware policy approval present
- Do not implement a submitting backend in this stage.

Verification:

```bash
.venv/bin/python scripts/check_quantum_hardware_provider_stubs.py
.venv/bin/python scripts/check_quantum_oracle.py
./scripts/run_pre_phase3_operational_routine.sh --stage secret-scan
```

Acceptance:

- IBM/AWS missing credentials degrade clearly.
- Configured IBM/AWS credentials would still be blocked by policy.
- Hardware submission allowed count remains zero.
- Hardware submitted count remains zero.

Latest audit record: `docs/qadam-phase-3-q3-4-hardware-provider-stubs-audit-2026-05-23.md`.

## 9. Stage Q3-5 - Scheduler Dry Contract

Objective: model the weekly oracle scheduler without enabling autonomous scheduling.

Work:

- Add a scheduler state contract:
  - cadence
  - last run
  - next due
  - due/not due
  - scheduler enabled false
  - hardware scheduler enabled false
- Add a dry-run scheduler check that can say which jobs would be queued.
- Ensure scheduler output cannot submit jobs.
- Ensure scheduler output cannot bypass Signal Integrity, Strategy Lead, Risk Agent, Execution Policy, broker reconciliation, or receipt gates.

Verification:

```bash
.venv/bin/python scripts/check_quantum_scheduler_dry_run.py
.venv/bin/python scripts/check_quantum_oracle.py
```

Acceptance:

- Scheduler metadata is deterministic and public-safe.
- Dry-run scheduler can describe intended jobs.
- No background automation or recurring job is created.
- `hardware_scheduler_enabled_count=0`.

Latest audit record: `docs/qadam-phase-3-q3-5-scheduler-dry-contract-audit-2026-05-23.md`.

## 10. Stage Q3-6 - Oracle Input Contract

Objective: define which upstream state can feed Head of Quant.

Work:

- Require input to come from existing Signal Integrity reviews or a certified shadow-review packet.
- Require durable evidence context when available.
- Require market-confirmation policy to be present.
- Treat Yahoo Finance as supplemental market confirmation only.
- Reject inputs with:
  - missing evidence
  - stale or unavailable market confirmation
  - single-source Yahoo-only market confirmation
  - execution authority already set
  - missing Signal Integrity boundary

Verification:

```bash
.venv/bin/python scripts/check_quantum_oracle_input_contract.py
.venv/bin/python scripts/check_signal_integrity_gate.py
.venv/bin/python scripts/check_quantum_oracle.py
```

Acceptance:

- Head of Quant cannot originate its own signal.
- Head of Quant only consumes reviewed shadow context.
- Yahoo Finance can contribute market context but cannot move a signal forward alone.

Latest audit record: `docs/qadam-phase-3-q3-6-oracle-input-contract-audit-2026-05-23.md`.

## 11. Stage Q3-7 - Oracle Output Routing

Objective: route Head of Quant output as shadow-only decision context.

Work:

- Store oracle output as an annotation or review result, not as a trade object.
- Preserve recommendation classes:
  - `upgrade_shadow_confidence`
  - `downgrade_or_hold`
  - `hold`
- Ensure Strategy Lead and Signal Integrity can read the output as context only.
- Prevent routing into:
  - trade candidate creation
  - Risk Agent approval
  - Execution Policy approval
  - staged paper orders
  - broker reconciliation
  - paper-submit receipts

Verification:

```bash
.venv/bin/python scripts/check_quantum_oracle_output_routing.py
.venv/bin/python scripts/check_quantum_oracle.py
.venv/bin/python scripts/run_phase2_shadow_cycle.py --durable-replay
.venv/bin/python scripts/check_signal_integrity_gate.py
.venv/bin/python scripts/check_risk_agent_policy_router.py
.venv/bin/python scripts/check_execution_policy_router.py
```

Acceptance:

- Oracle output can be inspected.
- Oracle output cannot create or advance trade state.
- Safety-chain counters remain zero.

Latest audit record: `docs/qadam-phase-3-q3-7-oracle-output-routing-audit-2026-05-23.md`.

## 12. Stage Q3-8 - Cockpit Phase 3 Visibility

Objective: make provider readiness, scheduler state, and oracle output visible without overstating readiness.

Work:

- Add or validate cockpit fields for:
  - provider readiness
  - Q-CTRL configured status
  - Qiskit/Aer local simulator availability
  - IBM/AWS missing/configured status
  - scheduler dry-run state
  - latest oracle recommendation
  - authority counters
- Keep public status free of:
  - API keys
  - secret file paths
  - raw provider responses
  - cloud job IDs from future live providers unless explicitly sanitized
  - local absolute paths

Verification:

```bash
./scripts/run_pre_phase3_operational_routine.sh --stage cockpit-export
./scripts/run_pre_phase3_operational_routine.sh --stage dashboard
./scripts/run_pre_phase3_operational_routine.sh --stage secret-scan
```

Acceptance:

- Cockpit says Phase 3 is provider/scheduler readiness, not execution readiness.
- Q-CTRL appears as configured without leaking the key.
- Hardware submission and scheduler authority remain visibly blocked.

Latest audit record: `docs/qadam-phase-3-q3-8-cockpit-phase-3-visibility-audit-2026-05-23.md`.

## 13. Stage Q3-9 - Phase 3 Operational Routine

Objective: make Phase 3 readiness repeatable in one command.

Work:

- Add a Phase 3 readiness runner or extend the pre-Phase-3 runner with a `phase3-readiness` stage.
- Include:
  - pre-Phase-3 routine
  - provider ledger check
  - local simulator check
  - Q-CTRL readiness contract
  - scheduler dry-run contract
  - cockpit export
  - dashboard checks
  - secret scan
- Keep each substage runnable independently.

Verification:

```bash
./scripts/run_pre_phase3_operational_routine.sh --stage phase3-readiness
./scripts/run_pre_phase3_operational_routine.sh --stage phase3-quantum
./scripts/run_pre_phase3_operational_routine.sh --stage all
.venv/bin/python scripts/check_quantum_oracle.py
```

Acceptance:

- A fresh session can refresh Phase 3 readiness without rereading the repo.
- The command fails closed if any authority counter becomes non-zero.
- The command does not perform hardware, broker, notification, or live-capital side effects.

Latest audit record: `docs/qadam-phase-3-q3-9-operational-routine-audit-2026-05-23.md`.

## 14. Stage Q3-10 - Phase 3A Certification

Objective: certify that provider/scheduler readiness is complete while execution remains disabled.

Work:

- Record branch, commit, dirty status, and date.
- Record provider states:
  - Qiskit/Aer
  - Q-CTRL
  - IBM Quantum
  - AWS Braket
- Record scheduler state.
- Record oracle result counts and latest backend.
- Record all authority counters.
- Decide whether Phase 3B may begin as a separate planning track.

Certification template:

```text
Date:
Branch:
Commit:
Qiskit/Aer:
Q-CTRL:
IBM Quantum:
AWS Braket:
Scheduler enabled:
Hardware scheduler enabled:
Latest oracle backend:
Oracle result count:
Hardware submission allowed count:
Hardware submitted count:
Execution allowed count:
Paper order allowed count:
Trade candidate created count:
Cockpit status:
Secret scan:
Decision:
```

Acceptance:

- Phase 3A passes only if every authority counter is zero.
- Any live provider call requires a separate explicit record.
- Any hardware submission remains blocked.

Latest audit record: `docs/qadam-phase-3-q3-10-phase-3a-certification-audit-2026-05-23.md`.

## 15. Stage Q3-11 - Hardware Enablement Proposal

Objective: prepare the later plan for actual hardware probes without implementing them yet.

Work:

- Define what a future hardware-readiness certification would require.
- Define explicit human approvals.
- Define budget and rate limits.
- Define provider-specific dry-run and cancellation behavior.
- Define public-safe status for future provider job IDs.
- Define emergency stop criteria.

Current status:

- Complete as documentation only.
- Blocked for implementation.
- Proposal: `docs/qadam-phase-3-q3-11-hardware-enablement-proposal-2026-05-23.md`.
- Requires a separate future certification before any Q-CTRL live probe, IBM Quantum call, AWS Braket call, provider-mediated hardware job, hardware scheduler, or recurring quantum automation can be submitted.

Latest audit record: `docs/qadam-phase-3-q3-11-hardware-enablement-proposal-audit-2026-05-23.md`.

## 16. Recommended Implementation Order

Use this order:

1. Q3-0 Re-Entry Guard.
2. Q3-1 Provider Readiness Ledger.
3. Q3-2 Local Simulator Track.
4. Q3-3 Q-CTRL Readiness Contract.
5. Q3-4 IBM/AWS Hardware Provider Stubs.
6. Q3-5 Scheduler Dry Contract.
7. Q3-6 Oracle Input Contract.
8. Q3-7 Oracle Output Routing.
9. Q3-8 Cockpit Phase 3 Visibility.
10. Q3-9 Phase 3 Operational Routine.
11. Q3-10 Phase 3A Certification.
12. Q3-11 Hardware Enablement Proposal.

Phase 3A is certified and Q3-11 is complete as documentation only. Phase 3B hardware implementation remains blocked. The master plan now names Phase 4 Strategy Manifestation as the next explicit build target unless the Fund Manager explicitly chooses a separate Phase 3B planning track first.
