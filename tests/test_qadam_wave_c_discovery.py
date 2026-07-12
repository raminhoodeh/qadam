from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

import pytest
from qiskit_machine_learning.kernels import FidelityQuantumKernel

from orchestrator import qadam_local_quantum_discovery as local_quantum
from orchestrator.qadam_classical_discovery import (
    ClassicalDiscoveryPolicy,
    run_classical_discovery,
)
from orchestrator.qadam_discovery_backend import (
    ZERO_AUTHORITY_FIELDS,
    validate_discovery_input_batch,
    validate_discovery_result,
    validate_research_candidate,
)
from orchestrator.qadam_discovery_contract_fixture import (
    build_wave_c_contract_fixture_batch,
    build_wave_c_null_fixture_batch,
)
from orchestrator.qadam_local_quantum_discovery import (
    LocalQuantumDiscoveryPolicy,
    QiskitLocalQuantumDiscoveryBackend,
    local_quantum_dependency_truth,
)

EXPECTED_INTERACTION = ["source_density", "source_agreement"]
pytestmark = pytest.mark.filterwarnings(
    "ignore:Since backends now support running jobs.*:DeprecationWarning"
)


def _classical():
    batch = build_wave_c_contract_fixture_batch()
    return batch, run_classical_discovery(batch)


def test_discovery_batch_is_deterministic_label_blind_and_non_executable():
    first = build_wave_c_contract_fixture_batch().to_dict()
    second = build_wave_c_contract_fixture_batch().to_dict()

    assert first == second
    assert first["labels_present"] is False
    assert first["contract_fixture_only"] is True
    assert len(first["matrix"]) == 16
    assert len(first["feature_names"]) == 6
    assert validate_discovery_input_batch(first) == []
    assert all(first["authority"][field] is False for field in ZERO_AUTHORITY_FIELDS)


def test_discovery_batch_hash_tamper_is_rejected():
    payload = build_wave_c_contract_fixture_batch().to_dict()
    payload["shared_manifest_hash"] = "tampered"
    assert "batch_manifest_hash_mismatch" in validate_discovery_input_batch(payload)


def test_classical_lane_runs_all_strong_reference_families_deterministically():
    batch, first = _classical()
    second = run_classical_discovery(batch)
    payload = first.to_dict()
    methods = {item["method"] for item in payload["method_results"]}

    assert payload == second.to_dict()
    assert {
        "linear_correlation_scan",
        "contemporaneous_logistic_relationship",
        "rbf_kernel_similarity",
        "change_point_mean_shift",
        "lagged_state_transition",
        "multivariate_anomaly_scan",
        "rbf_spectral_clustering_structure",
        "depth_two_tree_interaction",
    } == methods
    assert len(payload["matched_quantum_methods"]) == 3
    assert validate_discovery_result(payload) == []


def test_classical_lane_detects_fixture_interaction_without_promoting_it():
    _batch, result = _classical()
    payload = result.to_dict()
    interaction = next(
        item for item in payload["method_results"] if item["method"] == "depth_two_tree_interaction"
    )
    candidate = payload["research_candidates"][0]

    assert interaction["feature_pair"] == EXPECTED_INTERACTION
    assert interaction["structural_score"] > 0.9
    assert candidate["feature_pair"] == EXPECTED_INTERACTION
    assert candidate["candidate_persistence_allowed"] is False
    assert candidate["validation_contribution"] == "not_tested"
    assert candidate["validated_edge_created"] is False
    assert candidate["strategy_hypothesis_created"] is False
    assert candidate["trade_candidate_created"] is False
    assert candidate["paper_order_created"] is False
    assert validate_research_candidate(candidate) == []


def test_classical_policy_is_frozen_and_null_dataset_is_rejected():
    batch = build_wave_c_contract_fixture_batch()
    first = run_classical_discovery(batch)
    changed = run_classical_discovery(
        batch,
        policy=ClassicalDiscoveryPolicy(rbf_gamma=0.8, random_seed=batch.random_seed),
    )
    assert first.policy_hash != changed.policy_hash
    with pytest.raises(ValueError, match="rbf_gamma_invalid"):
        run_classical_discovery(
            batch,
            policy=ClassicalDiscoveryPolicy(rbf_gamma=0.0),
        )
    with pytest.raises(ValueError, match="null_dataset"):
        run_classical_discovery(build_wave_c_null_fixture_batch())


def test_local_quantum_dependencies_and_qml_kernel_contract_are_available():
    truth = local_quantum_dependency_truth()
    assert truth["qiskit_version"] == "2.4.1"
    assert truth["qiskit_aer_version"] == "0.17.2"
    assert truth["qiskit_machine_learning_version"] == "0.9.0"
    assert truth["ideal_simulation_available"] is True
    assert truth["finite_shot_simulation_available"] is True
    assert FidelityQuantumKernel.__name__ == "FidelityQuantumKernel"


def test_ideal_quantum_lane_is_reproducible_and_detects_fixture_interaction():
    batch, classical = _classical()
    backend = QiskitLocalQuantumDiscoveryBackend()
    first = backend.run(batch, mode="ideal", matched_classical_result=classical)
    second = backend.run(batch, mode="ideal", matched_classical_result=classical)
    payload = first.to_dict()
    interaction = next(
        item
        for item in payload["method_results"]
        if item["method"] == "quantum_fidelity_interaction_scan"
    )

    assert payload == second.to_dict()
    assert interaction["feature_pair"] == EXPECTED_INTERACTION
    assert interaction["structural_score"] > 0.5
    assert payload["matched_classical_result_id"] == classical.result_id
    assert payload["shared_manifest_hash"] == classical.shared_manifest_hash
    assert 4 <= payload["qubit_count"] <= 8
    assert payload["landmark_count"] == 8
    assert payload["circuit_evaluation_count"] <= 256
    assert payload["quantum_simulation_completed"] is True
    assert payload["hardware_experiment_completed"] is False
    assert payload["provider_call_attempted"] is False
    assert validate_discovery_result(payload) == []


def test_finite_shot_quantum_lane_is_seeded_and_reproducible():
    batch, classical = _classical()
    backend = QiskitLocalQuantumDiscoveryBackend()
    first = backend.run(
        batch,
        mode="finite_shot",
        shots=128,
        matched_classical_result=classical,
    )
    second = backend.run(
        batch,
        mode="finite_shot",
        shots=128,
        matched_classical_result=classical,
    )

    assert first.to_dict() == second.to_dict()
    assert first.execution_mode == "qiskit_aer_finite_shot"
    assert first.shots == 128
    assert first.classical_fallback_used is False
    assert first.to_dict()["hardware_experiment_completed"] is False
    with pytest.raises(ValueError, match="shots_invalid"):
        backend.run(
            batch,
            mode="finite_shot",
            shots=0,
            matched_classical_result=classical,
        )


def test_local_quantum_lane_rejects_nulls_budget_overrun_and_baseline_mismatch():
    batch, classical = _classical()
    backend = QiskitLocalQuantumDiscoveryBackend()
    null_batch = build_wave_c_null_fixture_batch()
    null_classical = replace(
        classical,
        result_id="classical-discovery:null-contract-baseline",
        shared_manifest_hash=null_batch.shared_manifest_hash,
        research_candidates=(),
    )
    with pytest.raises(ValueError, match="null_dataset"):
        backend.run(
            null_batch,
            mode="ideal",
            matched_classical_result=null_classical,
        )

    constrained = QiskitLocalQuantumDiscoveryBackend(
        LocalQuantumDiscoveryPolicy(maximum_circuit_evaluations=4)
    )
    with pytest.raises(ValueError, match="circuit_budget_exceeded"):
        constrained.run(batch, mode="ideal", matched_classical_result=classical)

    with pytest.raises(ValueError, match="baseline_manifest_mismatch"):
        backend.run(
            build_wave_c_null_fixture_batch(),
            mode="ideal",
            matched_classical_result=classical,
        )


def test_missing_quantum_dependency_is_explicit_classical_fallback(
    monkeypatch: pytest.MonkeyPatch,
):
    batch, classical = _classical()
    monkeypatch.setattr(
        local_quantum,
        "local_quantum_dependency_truth",
        lambda: {
            "qiskit_importable": False,
            "qiskit_version": None,
            "qiskit_aer_importable": False,
            "qiskit_aer_version": None,
            "qiskit_machine_learning_importable": False,
            "qiskit_machine_learning_version": None,
            "ideal_simulation_available": False,
            "finite_shot_simulation_available": False,
            "quantum_ml_contract_available": False,
            "hardware_available": False,
        },
    )
    result = QiskitLocalQuantumDiscoveryBackend().run(
        batch,
        mode="ideal",
        matched_classical_result=classical,
    )
    payload = result.to_dict()

    assert payload["backend_name"] == "classical_fallback"
    assert payload["quantum_simulation_completed"] is False
    assert payload["quantum_execution_claim"] is False
    assert payload["classical_fallback_used"] is True
    assert payload["research_candidates"] == ()
    assert validate_discovery_result(payload) == []


def test_quantum_candidate_cannot_self_validate_or_escalate_authority():
    batch, classical = _classical()
    result = QiskitLocalQuantumDiscoveryBackend().run(
        batch,
        mode="ideal",
        matched_classical_result=classical,
    ).to_dict()
    candidate = deepcopy(result["research_candidates"][0])
    candidate["validation_contribution"] = "quantum_strengthened"
    candidate["authority"]["paper_order_allowed"] = True
    errors = validate_research_candidate(candidate)

    assert "candidate_self_validation_attempted" in errors
    assert "candidate_authority_escalated:paper_order_allowed" in errors
