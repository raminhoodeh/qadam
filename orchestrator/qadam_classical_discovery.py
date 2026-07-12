"""Strong label-blind classical discovery baselines for Quantum Edge Wave C."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any

import numpy as np

from orchestrator.qadam_discovery_backend import (
    ClassicalDiscoveryResult,
    DiscoveryInputBatch,
    build_research_candidate,
    validate_discovery_input_batch,
    validate_discovery_result,
)
from orchestrator.qadam_quantum_discovery_evidence import stable_hash

POLICY_SCHEMA_VERSION = "qadam.ClassicalDiscoveryPolicy.v1"


@dataclass(frozen=True, kw_only=True)
class ClassicalDiscoveryPolicy:
    rbf_gamma: float = 0.5
    logistic_iterations: int = 240
    logistic_learning_rate: float = 0.08
    interaction_candidate_threshold: float = 0.2
    change_point_candidate_threshold: float = 0.65
    anomaly_candidate_threshold: float = 0.8
    transaction_cost_bps: float = 10.0
    threshold_selection_scope: str = "training_and_validation_only"
    final_holdout_scope: str = "untouched"
    multiple_testing_policy: str = "benjamini_hochberg_fdr_0.05"
    random_seed: int = 1729

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": POLICY_SCHEMA_VERSION, **asdict(self)}

    @property
    def policy_hash(self) -> str:
        return stable_hash(self.to_dict())


def validate_classical_discovery_policy(policy: ClassicalDiscoveryPolicy) -> None:
    if policy.rbf_gamma <= 0:
        raise ValueError("classical_policy_rbf_gamma_invalid")
    if policy.logistic_iterations <= 0 or policy.logistic_learning_rate <= 0:
        raise ValueError("classical_policy_logistic_invalid")
    for name, threshold in (
        ("interaction", policy.interaction_candidate_threshold),
        ("change_point", policy.change_point_candidate_threshold),
        ("anomaly", policy.anomaly_candidate_threshold),
    ):
        if not 0 <= threshold <= 1:
            raise ValueError(f"classical_policy_threshold_invalid:{name}")
    if policy.transaction_cost_bps < 0:
        raise ValueError("classical_policy_transaction_cost_invalid")
    if policy.threshold_selection_scope != "training_and_validation_only":
        raise ValueError("classical_policy_threshold_scope_invalid")
    if policy.final_holdout_scope != "untouched":
        raise ValueError("classical_policy_holdout_scope_invalid")
    if policy.multiple_testing_policy != "benjamini_hochberg_fdr_0.05":
        raise ValueError("classical_policy_multiple_testing_invalid")
    if isinstance(policy.random_seed, bool) or policy.random_seed < 0:
        raise ValueError("classical_policy_random_seed_invalid")


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 12)


def _pair_name(names: tuple[str, ...], left: int, right: int) -> list[str]:
    return [names[left], names[right]]


def _rbf_kernel(matrix: np.ndarray, gamma: float) -> np.ndarray:
    squared = np.sum((matrix[:, None, :] - matrix[None, :, :]) ** 2, axis=2)
    return np.exp(-gamma * squared)


def _linear_relationships(matrix: np.ndarray, names: tuple[str, ...]) -> dict[str, Any]:
    correlation = np.nan_to_num(np.corrcoef(matrix, rowvar=False), nan=0.0)
    best = (0.0, 0, 1)
    records = []
    for left in range(matrix.shape[1]):
        for right in range(left + 1, matrix.shape[1]):
            value = float(correlation[left, right])
            records.append({"feature_pair": _pair_name(names, left, right), "correlation": round(value, 12)})
            if abs(value) > best[0]:
                best = (abs(value), left, right)
    return {
        "method": "linear_correlation_scan",
        "structural_score": _clamp(best[0]),
        "strongest_feature_pair": _pair_name(names, best[1], best[2]),
        "signed_correlation": next(
            item["correlation"]
            for item in records
            if item["feature_pair"] == _pair_name(names, best[1], best[2])
        ),
        "pair_count": len(records),
        "point_in_time_label_blind": True,
    }


def _logistic_relationship(matrix: np.ndarray, names: tuple[str, ...], policy: ClassicalDiscoveryPolicy) -> dict[str, Any]:
    target_index = 2 if matrix.shape[1] > 2 else matrix.shape[1] - 1
    target = (matrix[:, target_index] > np.median(matrix[:, target_index])).astype(float)
    baseline = max(float(np.mean(target)), 1.0 - float(np.mean(target)))
    best = (baseline, 0)
    for feature_index in range(matrix.shape[1]):
        if feature_index == target_index:
            continue
        design = np.column_stack([np.ones(matrix.shape[0]), matrix[:, feature_index]])
        weights = np.zeros(2, dtype=float)
        for _ in range(policy.logistic_iterations):
            logits = np.clip(design @ weights, -30, 30)
            probabilities = 1.0 / (1.0 + np.exp(-logits))
            gradient = design.T @ (probabilities - target) / len(target)
            weights -= policy.logistic_learning_rate * gradient
        predictions = ((1.0 / (1.0 + np.exp(-np.clip(design @ weights, -30, 30)))) >= 0.5).astype(float)
        accuracy = float(np.mean(predictions == target))
        if accuracy > best[0]:
            best = (accuracy, feature_index)
    improvement = (best[0] - baseline) / max(1e-12, 1.0 - baseline)
    return {
        "method": "contemporaneous_logistic_relationship",
        "structural_score": _clamp(improvement),
        "predictor_feature": names[best[1]],
        "state_feature": names[target_index],
        "accuracy": round(best[0], 12),
        "majority_baseline_accuracy": round(baseline, 12),
        "future_market_label_used": False,
    }


def _rbf_similarity(matrix: np.ndarray, policy: ClassicalDiscoveryPolicy) -> tuple[dict[str, Any], np.ndarray]:
    kernel = _rbf_kernel(matrix, policy.rbf_gamma)
    off_diagonal = kernel[~np.eye(kernel.shape[0], dtype=bool)]
    nearest = np.partition(kernel + np.eye(kernel.shape[0]) * -2.0, -1, axis=1)[:, -1]
    return (
        {
            "method": "rbf_kernel_similarity",
            "structural_score": _clamp(float(np.mean(nearest))),
            "gamma": policy.rbf_gamma,
            "mean_off_diagonal_similarity": round(float(np.mean(off_diagonal)), 12),
            "kernel_hash": stable_hash(np.round(kernel, 12).tolist()),
            "matched_quantum_method": "fidelity_kernel",
        },
        kernel,
    )


def _change_point_scan(matrix: np.ndarray, names: tuple[str, ...]) -> dict[str, Any]:
    midpoint = matrix.shape[0] // 2
    pooled_scale = np.std(matrix, axis=0) + 1e-12
    shifts = np.abs(np.mean(matrix[:midpoint], axis=0) - np.mean(matrix[midpoint:], axis=0)) / pooled_scale
    index = int(np.argmax(shifts))
    score = 1.0 - math.exp(-float(shifts[index]))
    return {
        "method": "change_point_mean_shift",
        "structural_score": _clamp(score),
        "feature": names[index],
        "standardized_shift": round(float(shifts[index]), 12),
        "split_index": midpoint,
    }


def _state_transition_scan(matrix: np.ndarray, names: tuple[str, ...]) -> dict[str, Any]:
    centered = matrix - np.median(matrix, axis=0)
    states = (centered >= 0).astype(int)
    persistence = []
    for feature_index in range(matrix.shape[1]):
        same = np.mean(states[1:, feature_index] == states[:-1, feature_index])
        persistence.append(abs(float(same) - 0.5) * 2.0)
    index = int(np.argmax(persistence))
    return {
        "method": "lagged_state_transition",
        "structural_score": _clamp(persistence[index]),
        "feature": names[index],
        "state_persistence_or_alternation": round(float(persistence[index]), 12),
        "future_market_label_used": False,
    }


def _anomaly_scan(matrix: np.ndarray) -> dict[str, Any]:
    distances = np.linalg.norm(matrix, axis=1) / math.sqrt(matrix.shape[1])
    index = int(np.argmax(distances))
    score = 1.0 - math.exp(-float(distances[index]) / 2.0)
    return {
        "method": "multivariate_anomaly_scan",
        "structural_score": _clamp(score),
        "row_index": index,
        "standardized_distance": round(float(distances[index]), 12),
    }


def _spectral_structure(kernel: np.ndarray) -> dict[str, Any]:
    degree = np.sum(kernel, axis=1)
    normalized = kernel / np.sqrt(np.outer(degree, degree) + 1e-12)
    eigenvalues = np.sort(np.real(np.linalg.eigvalsh(normalized)))[::-1]
    eigengap = float(eigenvalues[1] - eigenvalues[2]) if len(eigenvalues) > 2 else 0.0
    return {
        "method": "rbf_spectral_clustering_structure",
        "structural_score": _clamp(max(0.0, eigengap)),
        "leading_eigenvalues": [round(float(value), 12) for value in eigenvalues[:4]],
        "matched_quantum_method": "fidelity_kernel_spectral_structure",
    }


def _group_mse(target: np.ndarray, groups: np.ndarray) -> float:
    residual = 0.0
    for group in np.unique(groups):
        selected = target[groups == group]
        residual += float(np.sum((selected - np.mean(selected)) ** 2))
    return residual / len(target)


def _tree_interaction_scan(matrix: np.ndarray, names: tuple[str, ...]) -> dict[str, Any]:
    target_index = 2 if matrix.shape[1] > 2 else matrix.shape[1] - 1
    target = matrix[:, target_index]
    baseline_mse = float(np.var(target)) + 1e-12
    best = (0.0, 0, 1, baseline_mse, baseline_mse)
    for left in range(matrix.shape[1]):
        if left == target_index:
            continue
        left_group = (matrix[:, left] > np.median(matrix[:, left])).astype(int)
        left_mse = _group_mse(target, left_group)
        for right in range(left + 1, matrix.shape[1]):
            if right == target_index:
                continue
            right_group = (matrix[:, right] > np.median(matrix[:, right])).astype(int)
            right_mse = _group_mse(target, right_group)
            joint_group = left_group * 2 + right_group
            joint_mse = _group_mse(target, joint_group)
            best_single = min(left_mse, right_mse)
            interaction_gain = max(0.0, (best_single - joint_mse) / baseline_mse)
            if interaction_gain > best[0]:
                best = (interaction_gain, left, right, best_single, joint_mse)
    return {
        "method": "depth_two_tree_interaction",
        "structural_score": _clamp(best[0]),
        "feature_pair": _pair_name(names, best[1], best[2]),
        "state_feature": names[target_index],
        "best_single_split_mse": round(float(best[3]), 12),
        "joint_split_mse": round(float(best[4]), 12),
        "predictive_outcome_claim": False,
    }


def run_classical_discovery(
    batch: DiscoveryInputBatch,
    *,
    policy: ClassicalDiscoveryPolicy | None = None,
) -> ClassicalDiscoveryResult:
    batch_errors = validate_discovery_input_batch(batch.to_dict())
    if batch_errors:
        raise ValueError(f"classical_batch_invalid:{','.join(batch_errors)}")
    active_policy = policy or ClassicalDiscoveryPolicy(random_seed=batch.random_seed)
    validate_classical_discovery_policy(active_policy)
    matrix = np.asarray(batch.matrix, dtype=float)
    if np.max(np.std(matrix, axis=0)) <= 1e-12:
        raise ValueError("classical_discovery_null_dataset")

    linear = _linear_relationships(matrix, batch.feature_names)
    logistic = _logistic_relationship(matrix, batch.feature_names, active_policy)
    rbf, kernel = _rbf_similarity(matrix, active_policy)
    change = _change_point_scan(matrix, batch.feature_names)
    transition = _state_transition_scan(matrix, batch.feature_names)
    anomaly = _anomaly_scan(matrix)
    spectral = _spectral_structure(kernel)
    interaction = _tree_interaction_scan(matrix, batch.feature_names)
    methods = (linear, logistic, rbf, change, transition, anomaly, spectral, interaction)

    candidates: list[dict[str, Any]] = []
    if interaction["structural_score"] >= active_policy.interaction_candidate_threshold:
        pair = tuple(interaction["feature_pair"])
        candidates.append(
            build_research_candidate(
                batch=batch,
                discovery_origin="classical_discovery",
                method=interaction["method"],
                feature_pair=(str(pair[0]), str(pair[1])),
                structural_score=float(interaction["structural_score"]),
                question=(
                    f"Does the interaction between {pair[0]} and {pair[1]} describe "
                    f"a reproducible contemporaneous regime in {batch.target_instrument}?"
                ),
            )
        )

    result_material = {
        "manifest": batch.shared_manifest_hash,
        "policy": active_policy.policy_hash,
        "methods": methods,
        "candidates": candidates,
    }
    result = ClassicalDiscoveryResult(
        result_id=f"classical-discovery:{stable_hash(result_material)[:24]}",
        shared_manifest_hash=batch.shared_manifest_hash,
        backend_name="qadam_strong_classical_reference",
        execution_mode="deterministic_label_blind_structure_discovery",
        policy_hash=active_policy.policy_hash,
        policy_contract=active_policy.to_dict(),
        method_results=methods,
        matched_quantum_methods=(
            {"quantum_method": "fidelity_kernel", "classical_method": "rbf_kernel_similarity"},
            {
                "quantum_method": "fidelity_kernel_spectral_structure",
                "classical_method": "rbf_spectral_clustering_structure",
            },
            {"quantum_method": "nearest_regime", "classical_method": "rbf_kernel_similarity"},
        ),
        research_candidates=tuple(candidates),
        contract_fixture_only=batch.contract_fixture_only,
    )
    errors = validate_discovery_result(result.to_dict())
    if errors:
        raise ValueError(f"classical_discovery_result_invalid:{','.join(errors)}")
    return result
