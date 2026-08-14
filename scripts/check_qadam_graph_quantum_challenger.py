#!/usr/bin/env python3
"""Build and validate QEG-9."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.qadam_graph_quantum_challenger import build_graph_quantum_challenger, validate_graph_quantum_challenger


if __name__ == "__main__":
    state, build_errors = build_graph_quantum_challenger()
    errors = sorted(set([*build_errors, *validate_graph_quantum_challenger()]))
    print(f"status={'passed' if not errors else 'blocked'}")
    print(f"comparison_count={state.get('comparison_count', 0)}")
    print(f"new_hardware_job_count={state.get('new_hardware_job_count', 0)}")
    print(f"quantum_value_state={state.get('quantum_value_state')}")
    for error in errors:
        print(f"error={error}")
    raise SystemExit(1 if errors else 0)
