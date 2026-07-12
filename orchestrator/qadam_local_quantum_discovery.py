"""Bounded local quantum-assisted discovery backend for Quantum Edge Wave C."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import importlib.util
from importlib.metadata import PackageNotFoundError, version
import math
from typing import Any, Callable

import numpy as np

from orchestrator.qadam_discovery_backend import (
    ClassicalDiscoveryResult,
    DiscoveryInputBatch,
    QuantumDiscoveryBackendResult,
    build_research_candidate,
    validate_discovery_input_batch,
    validate_discovery_result,
)
from orchestrator.qadam_quantum_discovery_evidence import stable_hash

POLICY_SCHEMA_VERSION = "qadam.LocalQuantumDiscoveryPolicy.v1"


@dataclass(frozen=True, kw_only=True)
class LocalQuantumDiscoveryPolicy:
    minimum_qubits: int = 4
    maximum_qubits: int = 8
    maximum_landmarks: int = 8
    maximum_batch_rows: int = 64
    maximum_circuit_evaluations: int = 256
    ideal_mode: str = "statevector"
    finite_shot_count: int = 1024
    interaction_candidate_threshold: float = 0.25
    classical_rbf_gamma: float = 0.5
    nystrom_ridge: float = 1e-8
    random_seed: int = 1729

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": POLICY_SCHEMA_VERSION, **asdict(self)}

    @property
    def policy_hash(self) -> str:
        return stable_hash(self.to_dict())


def _package_version(package: str) -> str | None:
    try:
        return version(package)
    except PackageNotFoundError:
        return None


def local_quantum_dependency_truth() -> dict[str, Any]:
    qiskit = importlib.util.find_spec("qiskit") is not None
    aer = importlib.util.find_spec("qiskit_aer") is not None
    machine_learning = importlib.util.find_spec("qiskit_machine_learning") is not None
    return {
        "qiskit_importable": qiskit,
        "qiskit_version": _package_version("qiskit") if qiskit else None,
        "qiskit_aer_importable": aer,
        "qiskit_aer_version": _package_version("qiskit-aer") if aer else None,
        "qiskit_machine_learning_importable": machine_learning,
        "qiskit_machine_learning_version": (
            _package_version("qiskit-machine-learning") if machine_learning else None
        ),
        "ideal_simulation_available": qiskit,
        "finite_shot_simulation_available": qiskit and aer,
        "quantum_ml_contract_available": qiskit and machine_learning,
        "hardware_available": False,
    }


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 12)


def _validate_policy(policy: LocalQuantumDiscoveryPolicy) -> None:
    if not 4 <= policy.minimum_qubits <= policy.maximum_qubits <= 8:
        raise ValueError("local_quantum_qubit_policy_invalid")
    if not 1 <= policy.maximum_landmarks <= policy.maximum_batch_rows:
        raise ValueError("local_quantum_landmark_policy_invalid")
    if policy.maximum_circuit_evaluations <= 0 or policy.finite_shot_count <= 0:
        raise ValueError("local_quantum_budget_policy_invalid")
    if not 0 <= policy.interaction_candidate_threshold <= 1:
        raise ValueError("local_quantum_candidate_threshold_invalid")
    if policy.classical_rbf_gamma <= 0:
        raise ValueError("local_quantum_classical_gamma_invalid")
    if policy.nystrom_ridge <= 0:
        raise ValueError("local_quantum_nystrom_ridge_invalid")
    if isinstance(policy.random_seed, bool) or policy.random_seed < 0:
        raise ValueError("local_quantum_random_seed_invalid")


def _feature_map_circuit(vector: np.ndarray, qubit_count: int):
    from qiskit import QuantumCircuit

    circuit = QuantumCircuit(qubit_count)
    clipped = np.clip(vector, -3.0, 3.0)
    for qubit in range(qubit_count):
        circuit.h(qubit)
    for index, value in enumerate(clipped):
        qubit = index % qubit_count
        circuit.ry(float(value) * math.pi / 2.0, qubit)
        circuit.rz(float(value * value) * math.pi / 4.0, qubit)
    for qubit in range(qubit_count):
        neighbor = (qubit + 1) % qubit_count
        left = float(clipped[qubit % len(clipped)])
        right = float(clipped[neighbor % len(clipped)])
        circuit.rzz(left * right * math.pi / 2.0, qubit, neighbor)
    for index in range(qubit_count, len(clipped)):
        circuit.rx(float(clipped[index]) * math.pi / 3.0, index % qubit_count)
    return circuit


def _circuit_hash(circuit: Any) -> str:
    from qiskit.qasm2 import dumps

    return stable_hash(dumps(circuit))


def _landmark_indices(row_count: int, maximum_landmarks: int) -> tuple[int, ...]:
    count = min(row_count, maximum_landmarks)
    if count == row_count:
        return tuple(range(row_count))
    return tuple(sorted(set(int(index) for index in np.linspace(0, row_count - 1, count))))


def _nystrom_kernel(
    row_count: int,
    landmarks: tuple[int, ...],
    pair_fidelity: Callable[[int, int], float],
    *,
    ridge: float,
    maximum_evaluations: int,
) -> tuple[np.ndarray, int]:
    cache: dict[tuple[int, int], float] = {}

    def evaluate(left: int, right: int) -> float:
        key = (min(left, right), max(left, right))
        if key not in cache:
            if len(cache) >= maximum_evaluations:
                raise ValueError("local_quantum_circuit_budget_exceeded")
            cache[key] = _clamp(pair_fidelity(left, right))
        return cache[key]

    columns = np.asarray(
        [[evaluate(row, landmark) for landmark in landmarks] for row in range(row_count)],
        dtype=float,
    )
    landmark_kernel = np.asarray(
        [[evaluate(left, right) for right in landmarks] for left in landmarks],
        dtype=float,
    )
    inverse = np.linalg.pinv(
        landmark_kernel + np.eye(len(landmarks), dtype=float) * ridge
    )
    approximation = columns @ inverse @ columns.T
    approximation = np.clip((approximation + approximation.T) / 2.0, 0.0, 1.0)
    np.fill_diagonal(approximation, 1.0)
    return approximation, len(cache)


def _ideal_pair_function(circuits: list[Any]) -> Callable[[int, int], float]:
    from qiskit.quantum_info import Statevector

    states = [np.asarray(Statevector.from_instruction(circuit).data) for circuit in circuits]

    def fidelity(left: int, right: int) -> float:
        overlap = np.vdot(states[left], states[right])
        return float(abs(overlap) ** 2)

    return fidelity


def _shot_pair_function(
    circuits: list[Any],
    *,
    shots: int,
    random_seed: int,
) -> Callable[[int, int], float]:
    from qiskit import transpile
    from qiskit_aer import AerSimulator

    simulator = AerSimulator(seed_simulator=random_seed)

    def fidelity(left: int, right: int) -> float:
        overlap = circuits[right].compose(circuits[left].inverse())
        overlap.measure_all()
        compiled = transpile(
            overlap,
            simulator,
            optimization_level=0,
            seed_transpiler=random_seed + left * 257 + right,
        )
        result = simulator.run(
            compiled,
            shots=shots,
            seed_simulator=random_seed + left * 257 + right,
        ).result()
        counts = result.get_counts()
        return float(counts.get("0" * overlap.num_qubits, 0)) / shots

    return fidelity


def _centered_alignment(left: np.ndarray, right: np.ndarray) -> float:
    count = left.shape[0]
    centering = np.eye(count) - np.ones((count, count)) / count
    left_centered = centering @ left @ centering
    right_centered = centering @ right @ centering
    denominator = np.linalg.norm(left_centered) * np.linalg.norm(right_centered)
    if denominator <= 1e-12:
        return 0.0
    return _clamp(float(np.sum(left_centered * right_centered) / denominator))


def _rbf_kernel(matrix: np.ndarray, gamma: float) -> np.ndarray:
    squared = np.sum((matrix[:, None, :] - matrix[None, :, :]) ** 2, axis=2)
    return np.exp(-gamma * squared)


def _nonlinear_interaction_scan(
    matrix: np.ndarray,
    names: tuple[str, ...],
    quantum_kernel: np.ndarray,
    *,
    classical_gamma: float,
) -> dict[str, Any]:
    classical_kernel = _rbf_kernel(matrix, classical_gamma)
    kernel_delta = np.linalg.norm(quantum_kernel - classical_kernel) / max(
        np.linalg.norm(quantum_kernel), 1e-12
    )
    state_index = 2 if matrix.shape[1] > 2 else matrix.shape[1] - 1
    state_kernel = _rbf_kernel(matrix[:, state_index].reshape(-1, 1), classical_gamma)
    best = (0.0, 0.0, 0.0, 0.0, 0, 1)
    for left in range(matrix.shape[1]):
        if left == state_index:
            continue
        for right in range(left + 1, matrix.shape[1]):
            if right == state_index:
                continue
            left_values = matrix[:, left]
            right_values = matrix[:, right]
            interaction_representation = np.column_stack(
                [
                    left_values,
                    right_values,
                    left_values * right_values,
                    (left_values - right_values) ** 2,
                ]
            )
            interaction_kernel = _rbf_kernel(interaction_representation, classical_gamma)
            quantum_alignment = _centered_alignment(quantum_kernel, interaction_kernel)
            state_alignment = _centered_alignment(interaction_kernel, state_kernel)
            left_alignment = _centered_alignment(
                _rbf_kernel(left_values.reshape(-1, 1), classical_gamma), state_kernel
            )
            right_alignment = _centered_alignment(
                _rbf_kernel(right_values.reshape(-1, 1), classical_gamma), state_kernel
            )
            interaction_gain = max(
                0.0,
                state_alignment - max(left_alignment, right_alignment),
            )
            combined = interaction_gain * 0.75 + quantum_alignment * 0.25
            if combined > best[0]:
                best = (
                    combined,
                    interaction_gain,
                    state_alignment,
                    quantum_alignment,
                    left,
                    right,
                )
    score = _clamp(best[0] * 0.8 + min(1.0, float(kernel_delta)) * 0.2)
    return {
        "method": "quantum_fidelity_interaction_scan",
        "structural_score": score,
        "feature_pair": [names[best[4]], names[best[5]]],
        "state_feature": names[state_index],
        "incremental_interaction_alignment": round(float(best[1]), 12),
        "interaction_state_alignment": round(float(best[2]), 12),
        "quantum_interaction_alignment": round(float(best[3]), 12),
        "quantum_vs_classical_kernel_delta": round(float(kernel_delta), 12),
        "matched_classical_method": "rbf_kernel_similarity",
        "validation_contribution": "not_tested",
    }


def _spectral_structure(kernel: np.ndarray) -> dict[str, Any]:
    degree = np.sum(kernel, axis=1)
    normalized = kernel / np.sqrt(np.outer(degree, degree) + 1e-12)
    eigenvalues = np.sort(np.real(np.linalg.eigvalsh(normalized)))[::-1]
    eigengap = float(eigenvalues[1] - eigenvalues[2]) if len(eigenvalues) > 2 else 0.0
    return {
        "method": "fidelity_kernel_spectral_structure",
        "structural_score": _clamp(max(0.0, eigengap)),
        "leading_eigenvalues": [round(float(value), 12) for value in eigenvalues[:4]],
        "matched_classical_method": "rbf_spectral_clustering_structure",
    }


class QiskitLocalQuantumDiscoveryBackend:
    key = "qiskit_local_quantum_discovery"

    def __init__(self, policy: LocalQuantumDiscoveryPolicy | None = None) -> None:
        self.policy = policy or LocalQuantumDiscoveryPolicy()
        _validate_policy(self.policy)

    def run(
        self,
        batch: DiscoveryInputBatch,
        *,
        mode: str,
        shots: int | None = None,
        matched_classical_result: ClassicalDiscoveryResult | dict[str, Any],
    ) -> QuantumDiscoveryBackendResult:
        batch_errors = validate_discovery_input_batch(batch.to_dict())
        if batch_errors:
            raise ValueError(f"local_quantum_batch_invalid:{','.join(batch_errors)}")
        if mode not in {"ideal", "finite_shot"}:
            raise ValueError("local_quantum_mode_invalid")
        classical_payload = (
            matched_classical_result.to_dict()
            if isinstance(matched_classical_result, ClassicalDiscoveryResult)
            else matched_classical_result
        )
        classical_errors = validate_discovery_result(classical_payload)
        if classical_errors:
            raise ValueError(
                f"local_quantum_classical_baseline_invalid:{','.join(classical_errors)}"
            )
        if classical_payload.get("shared_manifest_hash") != batch.shared_manifest_hash:
            raise ValueError("local_quantum_classical_baseline_manifest_mismatch")
        classical_methods = {
            item.get("method")
            for item in classical_payload.get("method_results", [])
            if isinstance(item, dict)
        }
        required_classical_methods = {
            "rbf_kernel_similarity",
            "rbf_spectral_clustering_structure",
            "depth_two_tree_interaction",
        }
        if not required_classical_methods.issubset(classical_methods):
            raise ValueError("local_quantum_matched_classical_methods_missing")
        if len(batch.matrix) > self.policy.maximum_batch_rows:
            raise ValueError("local_quantum_batch_budget_exceeded")
        dependency = local_quantum_dependency_truth()
        if not dependency["ideal_simulation_available"]:
            return _blocked_fallback_result(
                batch,
                policy=self.policy,
                mode=mode,
                blocker="qiskit_not_importable_classical_fallback_only",
                matched_classical_payload=classical_payload,
            )
        if mode == "finite_shot" and not dependency["finite_shot_simulation_available"]:
            return _blocked_fallback_result(
                batch,
                policy=self.policy,
                mode=mode,
                blocker="qiskit_aer_not_importable_classical_fallback_only",
                matched_classical_payload=classical_payload,
            )

        matrix = np.asarray(batch.matrix, dtype=float)
        if np.max(np.std(matrix, axis=0)) <= 1e-12:
            raise ValueError("local_quantum_null_dataset")
        qubit_count = min(
            self.policy.maximum_qubits,
            max(self.policy.minimum_qubits, matrix.shape[1]),
        )
        circuits = [_feature_map_circuit(row, qubit_count) for row in matrix]
        circuit_hashes = tuple(_circuit_hash(circuit) for circuit in circuits)
        landmarks = _landmark_indices(len(circuits), self.policy.maximum_landmarks)
        resolved_shots = self.policy.finite_shot_count if shots is None else shots
        if mode == "ideal":
            pair_fidelity = _ideal_pair_function(circuits)
            execution_mode = "qiskit_statevector_ideal"
            simulation_mode = "ideal_local_quantum_simulation"
            result_shots = None
        else:
            if resolved_shots <= 0:
                raise ValueError("local_quantum_shots_invalid")
            pair_fidelity = _shot_pair_function(
                circuits,
                shots=resolved_shots,
                random_seed=self.policy.random_seed,
            )
            execution_mode = "qiskit_aer_finite_shot"
            simulation_mode = "finite_shot_local_quantum_simulation"
            result_shots = resolved_shots

        kernel, evaluation_count = _nystrom_kernel(
            len(circuits),
            landmarks,
            pair_fidelity,
            ridge=self.policy.nystrom_ridge,
            maximum_evaluations=self.policy.maximum_circuit_evaluations,
        )
        interaction = _nonlinear_interaction_scan(
            matrix,
            batch.feature_names,
            kernel,
            classical_gamma=self.policy.classical_rbf_gamma,
        )
        spectral = _spectral_structure(kernel)
        methods = (
            {
                "method": "fidelity_kernel",
                "structural_score": _clamp(float(np.mean(kernel))),
                "kernel_hash": stable_hash(np.round(kernel, 12).tolist()),
                "kernel_shape": list(kernel.shape),
                "landmark_count": len(landmarks),
                "nystrom_approximation": len(landmarks) < len(circuits),
                "matched_classical_method": "rbf_kernel_similarity",
            },
            spectral,
            interaction,
            {
                "method": "local_dependency_truth",
                "structural_score": 0.0,
                **dependency,
            },
        )
        candidates: list[dict[str, Any]] = []
        if interaction["structural_score"] >= self.policy.interaction_candidate_threshold:
            pair = interaction["feature_pair"]
            candidates.append(
                build_research_candidate(
                    batch=batch,
                    discovery_origin="quantum_assisted_discovery",
                    method=interaction["method"],
                    feature_pair=(str(pair[0]), str(pair[1])),
                    structural_score=float(interaction["structural_score"]),
                    question=(
                        f"Does a nonlinear interaction between {pair[0]} and {pair[1]} "
                        f"describe a reproducible regime in {batch.target_instrument}?"
                    ),
                )
            )

        kernel_hash = stable_hash(np.round(kernel, 12).tolist())
        result_material = {
            "manifest": batch.shared_manifest_hash,
            "policy": self.policy.policy_hash,
            "mode": mode,
            "shots": result_shots,
            "kernel_hash": kernel_hash,
            "methods": methods,
            "candidates": candidates,
        }
        result = QuantumDiscoveryBackendResult(
            result_id=f"local-quantum-discovery:{stable_hash(result_material)[:24]}",
            shared_manifest_hash=batch.shared_manifest_hash,
            backend_name=self.key,
            execution_mode=execution_mode,
            simulation_mode=simulation_mode,
            policy_hash=self.policy.policy_hash,
            policy_contract=self.policy.to_dict(),
            matched_classical_result_id=str(classical_payload["result_id"]),
            matched_classical_policy_hash=str(classical_payload["policy_hash"]),
            kernel_hash=kernel_hash,
            kernel_shape=(len(circuits), len(circuits)),
            circuit_hashes=circuit_hashes,
            qubit_count=qubit_count,
            circuit_depth_max=max(circuit.depth() for circuit in circuits),
            shots=result_shots,
            landmark_count=len(landmarks),
            circuit_evaluation_count=evaluation_count,
            quantum_simulation_completed=True,
            quantum_execution_claim=True,
            classical_fallback_used=False,
            method_results=methods,
            research_candidates=tuple(candidates),
            contract_fixture_only=batch.contract_fixture_only,
            blocker=None,
        )
        errors = validate_discovery_result(result.to_dict())
        if errors:
            raise ValueError(f"local_quantum_result_invalid:{','.join(errors)}")
        return result


def _blocked_fallback_result(
    batch: DiscoveryInputBatch,
    *,
    policy: LocalQuantumDiscoveryPolicy,
    mode: str,
    blocker: str,
    matched_classical_payload: dict[str, Any],
) -> QuantumDiscoveryBackendResult:
    result = QuantumDiscoveryBackendResult(
        result_id=f"local-quantum-blocked:{stable_hash([batch.shared_manifest_hash, mode, blocker])[:24]}",
        shared_manifest_hash=batch.shared_manifest_hash,
        backend_name="classical_fallback",
        execution_mode="blocked_dependency_classical_fallback",
        simulation_mode="no_quantum_simulation",
        policy_hash=policy.policy_hash,
        policy_contract=policy.to_dict(),
        matched_classical_result_id=str(matched_classical_payload["result_id"]),
        matched_classical_policy_hash=str(matched_classical_payload["policy_hash"]),
        kernel_hash=None,
        kernel_shape=(0, 0),
        circuit_hashes=(),
        qubit_count=0,
        circuit_depth_max=0,
        shots=None,
        landmark_count=0,
        circuit_evaluation_count=0,
        quantum_simulation_completed=False,
        quantum_execution_claim=False,
        classical_fallback_used=True,
        method_results=(
            {
                "method": "classical_fallback_boundary",
                "structural_score": 0.0,
                "fallback_is_quantum_result": False,
                "blocker": blocker,
            },
        ),
        research_candidates=(),
        contract_fixture_only=batch.contract_fixture_only,
        blocker=blocker,
    )
    errors = validate_discovery_result(result.to_dict())
    if errors:
        raise ValueError(f"local_quantum_fallback_invalid:{','.join(errors)}")
    return result


def select_local_quantum_discovery_backend(
    policy: LocalQuantumDiscoveryPolicy | None = None,
) -> QiskitLocalQuantumDiscoveryBackend:
    return QiskitLocalQuantumDiscoveryBackend(policy)
