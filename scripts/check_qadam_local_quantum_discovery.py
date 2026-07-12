#!/usr/bin/env python3
"""Verify ideal and finite-shot Wave C local quantum discovery."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qiskit_machine_learning.kernels import FidelityQuantumKernel  # noqa: E402,F401

from orchestrator.qadam_classical_discovery import run_classical_discovery  # noqa: E402
from orchestrator.qadam_discovery_backend import validate_discovery_result  # noqa: E402
from orchestrator.qadam_discovery_contract_fixture import (  # noqa: E402
    build_wave_c_contract_fixture_batch,
)
from orchestrator.qadam_local_quantum_discovery import (  # noqa: E402
    QiskitLocalQuantumDiscoveryBackend,
    local_quantum_dependency_truth,
)
from orchestrator.qadam_quantum_discovery_evidence import (  # noqa: E402
    _runtime_dir,
    _write_json_atomic,
)

ARTIFACT = "qadam_local_quantum_discovery_contract.json"


def main() -> int:
    batch = build_wave_c_contract_fixture_batch()
    classical = run_classical_discovery(batch)
    backend = QiskitLocalQuantumDiscoveryBackend()
    ideal = backend.run(batch, mode="ideal", matched_classical_result=classical)
    ideal_repeat = backend.run(
        batch,
        mode="ideal",
        matched_classical_result=classical,
    )
    finite = backend.run(
        batch,
        mode="finite_shot",
        shots=256,
        matched_classical_result=classical,
    )
    ideal_payload = ideal.to_dict()
    finite_payload = finite.to_dict()
    errors = [
        *validate_discovery_result(ideal_payload),
        *validate_discovery_result(finite_payload),
    ]
    deterministic = ideal_payload == ideal_repeat.to_dict()
    pair = next(
        item["feature_pair"]
        for item in ideal_payload["method_results"]
        if item["method"] == "quantum_fidelity_interaction_scan"
    )
    output = {
        "schema_version": "qadam_local_quantum_discovery_check.v1",
        "status": "local_quantum_discovery_ready" if deterministic and not errors else "blocked",
        "dependency_truth": local_quantum_dependency_truth(),
        "shared_manifest_hash": batch.shared_manifest_hash,
        "contract_fixture_only": True,
        "ideal_result": ideal_payload,
        "finite_shot_result": finite_payload,
        "ideal_rebuild_deterministic": deterministic,
        "hardware_execution_authorized": False,
        "hardware_experiment_completed": False,
        "provider_call_attempted": False,
    }
    artifact = _write_json_atomic(_runtime_dir() / ARTIFACT, output)

    print(f"local_quantum_discovery_artifact={artifact}")
    print(f"local_quantum_discovery_status={output['status']}")
    print(f"local_quantum_discovery_manifest_hash={batch.shared_manifest_hash}")
    print(f"local_quantum_discovery_dependency_truth={output['dependency_truth']}")
    print(f"local_quantum_discovery_detected_pair={pair}")
    print(f"local_quantum_discovery_qubit_count={ideal.qubit_count}")
    print(f"local_quantum_discovery_landmark_count={ideal.landmark_count}")
    print(f"local_quantum_discovery_circuit_evaluations={ideal.circuit_evaluation_count}")
    print(f"local_quantum_discovery_ideal_deterministic={deterministic}")
    print(f"local_quantum_discovery_finite_shots={finite.shots}")
    print(f"local_quantum_discovery_hardware_completed={finite_payload['hardware_experiment_completed']}")
    print(f"local_quantum_discovery_paper_order_created={finite_payload['paper_order_created']}")
    print(f"local_quantum_discovery_errors={errors}")
    return 0 if deterministic and not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
