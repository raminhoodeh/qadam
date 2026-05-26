# Qadam Phase 3 - Q3-6 Oracle Input Contract Audit

Date: 2026-05-23

Decision: Q3-6 is complete.

## Objective

Define exactly which upstream state can feed Head of Quant before oracle jobs are built.

## Implementation Summary

- Added a public-safe Head of Quant input contract in `orchestrator/quantum.py`.
- `build_quantum_oracle_job()` now rejects input before job construction unless the input contract is accepted.
- Accepted inputs must come from:
  - an existing Signal Integrity review; or
  - a certified shadow-review packet with a Signal Integrity boundary.
- The contract rejects:
  - missing evidence;
  - insufficient independent source context;
  - missing market-confirmation policy;
  - stale market confirmation;
  - unavailable market confirmation;
  - single-source Yahoo-only market confirmation;
  - inherited execution, paper-order, or trade-candidate authority;
  - missing Signal Integrity boundary.
- Yahoo Finance is allowed only as supplemental market confirmation. It can appear in an accepted input only when there is non-Yahoo market confirmation as well.
- Durable evidence context is required when present. A supplied durable replay context must be complete, read-only, and non-authoritative.
- Oracle jobs now persist `input_contract` beside the local-validation job metadata.
- Cockpit quantum oracle summary now exposes public-safe latest input-contract state.

## Files Changed For Q3-6

- `orchestrator/quantum.py`
- `orchestrator/cockpit_status.py`
- `scripts/check_quantum_oracle_input_contract.py`
- `scripts/check_quantum_oracle.py`
- `scripts/check_quantum_local_simulator.py`
- `scripts/check_cockpit_status.py`
- `docs/qadam-phase-3-implementation-plan.md`

## Verification

```bash
.venv/bin/python -m ruff check orchestrator/quantum.py orchestrator/cockpit_status.py scripts/check_quantum_oracle.py scripts/check_quantum_local_simulator.py scripts/check_quantum_oracle_input_contract.py scripts/check_cockpit_status.py
```

Result: passed.

```bash
.venv/bin/python -m compileall orchestrator/quantum.py orchestrator/cockpit_status.py scripts/check_quantum_oracle.py scripts/check_quantum_local_simulator.py scripts/check_quantum_oracle_input_contract.py scripts/check_cockpit_status.py
```

Result: passed.

```bash
.venv/bin/python scripts/check_quantum_oracle_input_contract.py
```

Observed:

- `quantum_oracle_input_contract_status=accepted`
- `quantum_oracle_input_source_type=signal_integrity_review`
- `quantum_oracle_input_market_confirmation_status=market_confirmation_corroboration_available`
- `quantum_oracle_input_yahoo_finance_role=supplemental_market_confirmation`
- `quantum_oracle_input_yahoo_only_market_confirmation=False`
- Certified shadow packet durable status: `available`
- Rejection probes passed for missing evidence, stale market confirmation, unavailable market confirmation, Yahoo-only market confirmation, inherited execution authority, missing Signal Integrity boundary, and missing market-confirmation policy.
- `quantum_oracle_input_contract_check=ok`

```bash
.venv/bin/python scripts/check_signal_integrity_gate.py
```

Observed:

- `signal_integrity_gate_status=ok`
- `signal_integrity_gate_review_count=5`
- `signal_integrity_gate_execution_allowed_count=0`
- `signal_integrity_gate_paper_order_allowed_count=0`
- `signal_integrity_gate_trade_candidate_created_count=0`
- Yahoo policy probes:
  - `synthetic_yahoo_single_source=market_confirmation_single_source_hold`
  - `synthetic_yahoo_stale=market_confirmation_stale`
  - `synthetic_market_unavailable=market_confirmation_unavailable`
- `signal_integrity_gate_check=ok`

```bash
.venv/bin/python scripts/check_quantum_oracle.py
```

Observed:

- `quantum_oracle_status=ok`
- `quantum_oracle_job_count=2`
- `quantum_oracle_result_count=2`
- `quantum_oracle_backend=classical_fallback`
- `quantum_oracle_input_contract_status=accepted`
- `quantum_oracle_input_source_type=signal_integrity_review`
- `quantum_oracle_input_market_confirmation_status=market_confirmation_corroboration_available`
- `quantum_oracle_input_yahoo_finance_role=supplemental_market_confirmation`
- `quantum_oracle_input_yahoo_only_market_confirmation=False`
- `quantum_oracle_input_durable_evidence_status=not_available`
- `quantum_oracle_hardware_submitted_count=0`
- `quantum_oracle_hardware_submission_allowed_count=0`
- `quantum_oracle_hardware_scheduler_enabled_count=0`
- `quantum_oracle_execution_allowed_count=0`
- `quantum_oracle_paper_order_allowed_count=0`
- `quantum_oracle_trade_candidate_created_count=0`
- `quantum_oracle_check=ok`

```bash
./scripts/run_pre_phase3_operational_routine.sh --stage cockpit-export
```

Observed:

- `cockpit_status_export=ok`
- `cockpit_status_check=ok`
- `cockpit_status_quantum_oracle_status=ok`
- `cockpit_status_quantum_oracle_result_count=36`
- `cockpit_status_live_capital_enabled=False`
- `pre_phase3_routine=ok`

## Safety Notes

- No broker route was opened.
- No paper order was created.
- No trade candidate was created by Head of Quant.
- No provider call was made.
- No Q-CTRL optimization job was submitted.
- No IBM Quantum or AWS Braket hardware job was submitted.
- No scheduler, queue writer, or background automation was created.
- No raw secret or API key was written to docs or exported status.

## Next Stage

Proceed to Q3-7 Oracle Output Routing.
