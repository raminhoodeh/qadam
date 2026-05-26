# Qadam Phase 3 Q3-2 Local Simulator Track Audit - 2026-05-23

This is the Stage Q3-2 Local Simulator Track audit for `docs/qadam-phase-3-implementation-plan.md`.

## Audit Decision

Q3-2 is complete.

The local simulator track now has an explicit public-safe contract. The deterministic classical fallback remains the always-available baseline, the optional Qiskit Aer path is selected only when local `qiskit` and `qiskit-aer` imports are available, and both paths must emit the same Phase 3 oracle schema for the same two bounded jobs: Pattern Recognition and Strategy Collapse / Ambiguity Score.

This audit does not authorize provider calls, hardware submissions, scheduler enablement, broker writes, trade-candidate creation from Head of Quant output, execution approvals, paper-order approvals, paper-order submission, or live-capital enablement.

## Certification Snapshot

```text
Date: 2026-05-23 15:17:22 CDT
Branch: main
Commit: 32603556194f6d014487b02eb1bdfa2c99882a4c
Worktree: dirty local workspace with accumulated pre-Phase-3 and Phase 3 artifacts
Nested landing-page-repo: dirty with dashboard and refreshed cockpit status artifacts
Local Qiskit imports: qiskit=False, qiskit_aer=False
Active local simulator backend: classical_fallback
```

## Implementation Summary

- Added `quantum_local_simulator_status()` and `validate_quantum_local_simulator_status()` in `orchestrator/quantum.py`.
- Added a public-safe `local_simulator` contract to the quantum oracle summary and cockpit export.
- Added `scripts/check_quantum_local_simulator.py`, a side-effect-free checker that runs both bounded jobs without writing oracle results to the store.
- Extended `scripts/check_quantum_oracle.py` to validate local simulator status, backend selection, schema consistency, job coverage, shot counts, and zero authority flags.
- Extended `scripts/check_cockpit_status.py` so cockpit status fails if the local simulator contract is missing, malformed, non-local, or has nonzero authority.
- Added the optional `quantum-local` dependency extra in `pyproject.toml`.
- Added local dependency guidance in `docs/qadam-quantum-local-simulator.md`.

## Local Simulator Contract

Current local simulator status:

```text
quantum_local_simulator_status=classical_fallback_ready
quantum_local_simulator_selected_backend=classical_fallback
quantum_local_simulator_qiskit_available=False
quantum_local_simulator_qiskit_aer_available=False
quantum_local_simulator_qiskit_dependencies=False
quantum_local_simulator_fallback_available=True
quantum_local_simulator_required_job_count=2
quantum_local_simulator_output_schema_version=1
```

Bounded local results:

```text
quantum_local_simulator_result=pattern_recognition,classical_fallback,ok,deterministic_classical_shadow
quantum_local_simulator_result=strategy_collapse,classical_fallback,ok,deterministic_classical_shadow
quantum_local_simulator_result_count=2
quantum_local_simulator_check=ok
```

## Commands Run

Focused static checks:

```bash
.venv/bin/python -m ruff check orchestrator/quantum.py orchestrator/cockpit_status.py scripts/check_quantum_local_simulator.py scripts/check_quantum_provider_readiness.py scripts/check_quantum_oracle.py scripts/check_cockpit_status.py
.venv/bin/python -m compileall orchestrator/quantum.py orchestrator/cockpit_status.py scripts/check_quantum_local_simulator.py scripts/check_quantum_provider_readiness.py scripts/check_quantum_oracle.py scripts/check_cockpit_status.py
```

Local simulator and oracle checks:

```bash
.venv/bin/python scripts/check_quantum_local_simulator.py
.venv/bin/python scripts/check_quantum_oracle.py
.venv/bin/python scripts/check_quantum_provider_readiness.py
```

Cockpit and dashboard checks:

```bash
./scripts/run_pre_phase3_operational_routine.sh --stage cockpit-export
./scripts/run_pre_phase3_operational_routine.sh --stage dashboard
./scripts/run_pre_phase3_operational_routine.sh --stage secret-scan
```

Repository hygiene checks:

```bash
.venv/bin/python -c "import tomllib; tomllib.load(open('pyproject.toml','rb')); print('pyproject_toml_parse=ok')"
rg -n 'QCTRL_API_KEY=|AIza[0-9A-Za-z_-]{20,}|ghp_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|sb_secret_[0-9A-Za-z_-]{12,}|[0-9]{6,}:[A-Za-z0-9_-]{20,}' orchestrator/quantum.py orchestrator/cockpit_status.py scripts/check_quantum_local_simulator.py scripts/check_quantum_oracle.py scripts/check_cockpit_status.py docs/qadam-quantum-local-simulator.md docs/qadam-phase-3-implementation-plan.md pyproject.toml
git diff --check
git -C landing-page-repo diff --check
```

## Verification Results

Static checks passed:

```text
All checks passed!
compileall=ok
pyproject_toml_parse=ok
```

The local simulator check passed:

```text
quantum_local_simulator_check=ok
```

The quantum oracle check passed:

```text
quantum_oracle_status=ok
quantum_oracle_job_count=2
quantum_oracle_result_count=2
quantum_oracle_backend=classical_fallback
quantum_oracle_backend_status=ok
quantum_oracle_local_simulation_mode=deterministic_classical_shadow
quantum_oracle_store_result_count=24
quantum_oracle_hardware_submitted_count=0
quantum_oracle_hardware_submission_allowed_count=0
quantum_oracle_hardware_scheduler_enabled_count=0
quantum_oracle_execution_allowed_count=0
quantum_oracle_paper_order_allowed_count=0
quantum_oracle_trade_candidate_created_count=0
quantum_oracle_qiskit_aer_available=False
quantum_oracle_qiskit_available=False
quantum_local_simulator_status=classical_fallback_ready
quantum_local_simulator_selected_backend=classical_fallback
quantum_local_simulator_qiskit_dependencies=False
quantum_local_simulator_fallback_available=True
quantum_local_simulator_required_job_count=2
quantum_oracle_check=ok
```

Provider readiness still passed:

```text
quantum_provider_readiness_status=ok
quantum_provider_qctrl_configured=True
quantum_provider_call_allowed_count=0
quantum_provider_hardware_submission_allowed_count=0
quantum_provider_hardware_scheduler_enabled_count=0
quantum_provider_execution_allowed_count=0
quantum_provider_paper_order_allowed_count=0
quantum_provider_trade_candidate_authority_count=0
quantum_provider_secret_value_exposed_count=0
quantum_provider_raw_response_exposed_count=0
quantum_provider_readiness_check=ok
```

Cockpit status passed and includes the public-safe local simulator contract:

```text
cockpit_status_check=ok
cockpit_status_quantum_oracle_status=ok
cockpit_status_quantum_oracle_result_count=24
cockpit_status_quantum_oracle_backend=classical_fallback
cockpit_status_quantum_oracle_mode=deterministic_classical_shadow
cockpit_status_live_capital_enabled=False
cockpit_status_boundary=Public-safe read-only snapshot. It cannot trigger trading and contains no secrets.
```

Dashboard and secret-scan checks passed:

```text
Dashboard renderer contract OK
Dashboard watching view contract OK
Dashboard cognition view contract OK
dashboard_mission_control=ok
dashboard_system_map=ok
dashboard_durable_spine=ok
dashboard_acceptance=ok
pre_phase3_secret_scan=ok
```

The explicit token-pattern scan returned no matches. `git diff --check` and `git -C landing-page-repo diff --check` passed.

## Optional Dependency Guidance

Optional local simulator dependencies are documented in `docs/qadam-quantum-local-simulator.md`.

The local extra is:

```text
quantum-local = qiskit, qiskit-aer
```

No package installation was performed during this stage.

## Safety Notes

The local simulator track is local-only and non-executable. It does not call Q-CTRL, IBM Quantum, AWS Braket, Qiskit Runtime, brokers, order endpoints, or live-capital paths.

Qiskit Aer is not installed in the current local environment, so the active verified path is `classical_fallback`. This is acceptable for Q3-2 because classical fallback remains the required always-available baseline.

## Git State

Root repo status remains dirty with accumulated pre-Phase-3 and Phase 3 artifacts. Q3-2 did not stage or commit.

Nested `landing-page-repo` status:

```text
 M dashboard.js
 M status/cockpit-status.json
 M status/cockpit-status.signature.json
```

No deployment was performed.

## Next Stage

The next implementable Phase 3 stage is Q3-3 Q-CTRL Readiness Contract.
