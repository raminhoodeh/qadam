# Qadam Quantum Local Simulator

This note defines the local-only simulator setup for Phase 3. The simulator track is optional and does not require quantum provider credentials.

## Baseline

The deterministic classical fallback is always available and remains the required baseline. It emits the same oracle result schema used by the optional Qiskit Aer path.

## Optional Local Dependencies

Install the optional local simulator dependencies only on the local machine:

```bash
.venv/bin/python -m pip install -e ".[quantum-local]"
```

Confirm imports:

```bash
.venv/bin/python -c "import qiskit, qiskit_aer; print('qiskit_local_ready=true')"
```

Then run:

```bash
.venv/bin/python scripts/check_quantum_local_simulator.py
.venv/bin/python scripts/check_quantum_oracle.py
```

## Safety Boundary

Qiskit Aer is a local simulator only. The Phase 3 local simulator track cannot call Q-CTRL, IBM Quantum, AWS Braket, Qiskit Runtime, brokers, order routers, or live-capital paths.

If Qiskit or Qiskit Aer is missing, or if the local simulator fails at runtime, the oracle must degrade to the deterministic classical fallback with the same output schema.
