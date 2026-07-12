"""Independent, holdout-only quantum value evaluation for Quantum Edge Wave E."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
import math
from pathlib import Path
import random
from typing import Any, Iterable

from orchestrator.qadam_hybrid_candidate_merger import (
    WAVE_E_ZERO_AUTHORITY_FIELDS,
    validate_hybrid_candidate_state,
)
from orchestrator.qadam_quantum_discovery_evidence import stable_hash

POLICY_SCHEMA_VERSION = "qadam.IndependentQuantumValuePolicy.v1"
INPUT_SCHEMA_VERSION = "qadam.IndependentQuantumValueInput.v1"
RESULT_SCHEMA_VERSION = "qadam.IndependentQuantumValueResult.v1"
BATCH_SCHEMA_VERSION = "qadam.IndependentQuantumValueBatch.v1"
OVERFIT_SCHEMA_VERSION = "qadam.IndependentQuantumOverfitAudit.v1"

EVALUATION_ARTIFACT = "qadam_independent_quantum_value_evaluations.jsonl"
SUMMARY_ARTIFACT = "qadam_independent_quantum_value_summary.json"
OVERFIT_ARTIFACT = "qadam_independent_quantum_overfit_audit.json"

VALID_VERDICTS = (
    "quantum_strengthened",
    "joint_corroboration",
    "classical_preferred",
    "weakened",
    "inconclusive",
    "not_measurable",
    "failed_safely",
)

EVIDENCE_CLASSES = (
    "empirical_untouched_holdout",
    "synthetic_control",
    "no_holdout",
)

PROVIDER_MODES = (
    "classical_only",
    "local_ideal_simulator",
    "local_finite_shot_simulator",
    "ibm_quantum_via_fire_opal",
    "no_quantum_result",
)

FORBIDDEN_PUBLIC_KEYS = {
    "action_id",
    "api_key",
    "backend_name",
    "credentials",
    "password",
    "provider_job_ids",
    "qasm_circuits",
    "raw_provider_response",
    "secret",
    "token",
}


def _authority() -> dict[str, bool]:
    return {field_name: False for field_name in WAVE_E_ZERO_AUTHORITY_FIELDS}


def _contains_forbidden_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in FORBIDDEN_PUBLIC_KEYS:
                return True
            if _contains_forbidden_key(child):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_forbidden_key(child) for child in value)
    return False


def _parse_timestamp(value: str | None, *, field_name: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name}_missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field_name}_invalid") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field_name}_timezone_missing")
    return parsed


def _is_finite_sequence(values: Iterable[float]) -> bool:
    try:
        return all(math.isfinite(float(value)) for value in values)
    except (TypeError, ValueError):
        return False


@dataclass(frozen=True, kw_only=True)
class IndependentEvaluationPolicy:
    decision_threshold: float = 0.5
    minimum_holdout_observations: int = 32
    transaction_cost_bps: float = 10.0
    false_discovery_rate_alpha: float = 0.05
    minimum_net_incremental_value: float = 0.0005
    equivalence_margin: float = 0.00025
    material_underperformance: float = 0.0005
    minimum_directional_agreement: float = 0.75
    minimum_reproducibility_runs: int = 3
    minimum_reproducibility_score: float = 0.90
    maximum_noise_sensitivity: float = 0.20
    complexity_penalty: float = 0.00005
    latency_penalty_per_second: float = 0.000001
    provider_cost_penalty_per_usd: float = 0.00001
    noise_penalty_weight: float = 0.00050
    reproducibility_penalty_weight: float = 0.00050
    permutation_iterations: int = 4096
    random_seed: int = 260712

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": POLICY_SCHEMA_VERSION, **asdict(self)}

    @property
    def policy_hash(self) -> str:
        return stable_hash(self.to_dict())


def validate_evaluation_policy(policy: IndependentEvaluationPolicy) -> None:
    if not 0 < policy.decision_threshold < 1:
        raise ValueError("evaluation_policy_threshold_invalid")
    if policy.minimum_holdout_observations < 16:
        raise ValueError("evaluation_policy_holdout_too_small")
    if not 0 <= policy.transaction_cost_bps <= 1000:
        raise ValueError("evaluation_policy_transaction_cost_invalid")
    if not 0 < policy.false_discovery_rate_alpha < 1:
        raise ValueError("evaluation_policy_fdr_invalid")
    if policy.minimum_net_incremental_value <= 0:
        raise ValueError("evaluation_policy_incremental_value_invalid")
    if not 0 <= policy.equivalence_margin < policy.minimum_net_incremental_value:
        raise ValueError("evaluation_policy_equivalence_margin_invalid")
    if policy.material_underperformance <= 0:
        raise ValueError("evaluation_policy_underperformance_invalid")
    if not 0 <= policy.minimum_directional_agreement <= 1:
        raise ValueError("evaluation_policy_agreement_invalid")
    if policy.minimum_reproducibility_runs < 2:
        raise ValueError("evaluation_policy_reproducibility_runs_invalid")
    if not 0 <= policy.minimum_reproducibility_score <= 1:
        raise ValueError("evaluation_policy_reproducibility_score_invalid")
    if not 0 <= policy.maximum_noise_sensitivity <= 1:
        raise ValueError("evaluation_policy_noise_invalid")
    if policy.permutation_iterations < 999:
        raise ValueError("evaluation_policy_permutation_budget_invalid")


@dataclass(frozen=True, kw_only=True)
class IndependentEvaluationInput:
    candidate_id: str
    candidate_hash: str
    discovery_origin: str
    shared_manifest_hash: str
    chronological_split_identity: str
    training_validation_manifest_hash: str
    holdout_manifest_hash: str | None
    matched_classical_baseline_id: str
    matched_classical_policy_hash: str
    quantum_method_id: str
    quantum_policy_hash: str
    evidence_class: str
    holdout_start: str | None
    holdout_end: str | None
    thresholds_frozen_at: str | None
    holdout_unsealed_at: str | None
    untouched_chronological_holdout: bool
    holdout_used_for_selection: bool
    outcomes: tuple[float, ...]
    classical_scores: tuple[float, ...]
    quantum_scores: tuple[float, ...]
    provider_mode: str
    hardware_experiment_completed: bool
    hardware_receipt_hash: str | None
    shot_count: int | None
    noise_sensitivity: float | None
    classical_latency_seconds: float
    quantum_latency_seconds: float
    provider_cost_usd: float
    reproducibility_scores: tuple[float, ...]
    contract_fixture_only: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": INPUT_SCHEMA_VERSION,
            **asdict(self),
            "authority": _authority(),
        }


def no_holdout_evaluation_input(
    candidate: dict[str, Any],
    *,
    shared_manifest_hash: str,
) -> IndependentEvaluationInput:
    """Build an explicit no-holdout record for current infrastructure truth."""

    return IndependentEvaluationInput(
        candidate_id=str(candidate["candidate_id"]),
        candidate_hash=str(candidate["candidate_hash"]),
        discovery_origin=str(candidate["discovery_origin"]),
        shared_manifest_hash=shared_manifest_hash,
        chronological_split_identity="unavailable_pending_empirical_backfill",
        training_validation_manifest_hash="unavailable_pending_empirical_backfill",
        holdout_manifest_hash=None,
        matched_classical_baseline_id="matched_classical_baseline_pending",
        matched_classical_policy_hash="matched_classical_policy_pending",
        quantum_method_id="quantum_method_pending",
        quantum_policy_hash="quantum_policy_pending",
        evidence_class="no_holdout",
        holdout_start=None,
        holdout_end=None,
        thresholds_frozen_at=None,
        holdout_unsealed_at=None,
        untouched_chronological_holdout=False,
        holdout_used_for_selection=False,
        outcomes=(),
        classical_scores=(),
        quantum_scores=(),
        provider_mode="no_quantum_result",
        hardware_experiment_completed=False,
        hardware_receipt_hash=None,
        shot_count=None,
        noise_sensitivity=None,
        classical_latency_seconds=0.0,
        quantum_latency_seconds=0.0,
        provider_cost_usd=0.0,
        reproducibility_scores=(),
        contract_fixture_only=True,
    )


def _hard_input_errors(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != INPUT_SCHEMA_VERSION:
        errors.append("evaluation_input_schema_invalid")
    for field_name in (
        "candidate_id",
        "candidate_hash",
        "discovery_origin",
        "shared_manifest_hash",
        "chronological_split_identity",
        "training_validation_manifest_hash",
        "matched_classical_baseline_id",
        "matched_classical_policy_hash",
        "quantum_method_id",
        "quantum_policy_hash",
    ):
        if not str(payload.get(field_name) or "").strip():
            errors.append(f"evaluation_input_missing:{field_name}")
    if payload.get("evidence_class") not in EVIDENCE_CLASSES:
        errors.append("evaluation_input_evidence_class_invalid")
    if not isinstance(payload.get("contract_fixture_only"), bool):
        errors.append("evaluation_input_fixture_flag_invalid")
    if payload.get("provider_mode") not in PROVIDER_MODES:
        errors.append("evaluation_input_provider_mode_invalid")
    outcomes = payload.get("outcomes")
    classical = payload.get("classical_scores")
    quantum = payload.get("quantum_scores")
    if not all(isinstance(values, (list, tuple)) for values in (outcomes, classical, quantum)):
        errors.append("evaluation_input_series_invalid")
    else:
        if len({len(outcomes), len(classical), len(quantum)}) != 1:
            errors.append("evaluation_input_series_length_mismatch")
        if not _is_finite_sequence(outcomes):
            errors.append("evaluation_input_outcomes_not_finite")
        if not _is_finite_sequence(classical) or not _is_finite_sequence(quantum):
            errors.append("evaluation_input_scores_not_finite")
        if any(not 0 <= float(score) <= 1 for score in (*classical, *quantum)):
            errors.append("evaluation_input_score_out_of_range")
    for field_name in (
        "classical_latency_seconds",
        "quantum_latency_seconds",
        "provider_cost_usd",
    ):
        value = payload.get(field_name)
        try:
            if not math.isfinite(float(value)) or float(value) < 0:
                errors.append(f"evaluation_input_invalid:{field_name}")
        except (TypeError, ValueError):
            errors.append(f"evaluation_input_invalid:{field_name}")
    noise = payload.get("noise_sensitivity")
    if noise is not None:
        try:
            if not 0 <= float(noise) <= 1:
                errors.append("evaluation_input_noise_sensitivity_invalid")
        except (TypeError, ValueError):
            errors.append("evaluation_input_noise_sensitivity_invalid")
    reproducibility = payload.get("reproducibility_scores")
    if not isinstance(reproducibility, (list, tuple)) or not _is_finite_sequence(
        reproducibility
    ):
        errors.append("evaluation_input_reproducibility_invalid")
    elif any(not 0 <= float(score) <= 1 for score in reproducibility):
        errors.append("evaluation_input_reproducibility_out_of_range")
    hardware_completed = payload.get("hardware_experiment_completed") is True
    receipt_hash = payload.get("hardware_receipt_hash")
    hardware_mode = payload.get("provider_mode") == "ibm_quantum_via_fire_opal"
    if hardware_completed != hardware_mode:
        errors.append("evaluation_input_hardware_mode_mismatch")
    if hardware_completed and not str(receipt_hash or "").strip():
        errors.append("evaluation_input_hardware_receipt_missing")
    if not hardware_completed and receipt_hash is not None:
        errors.append("evaluation_input_unearned_hardware_receipt")
    for field_name in WAVE_E_ZERO_AUTHORITY_FIELDS:
        if payload.get("authority", {}).get(field_name) is not False:
            errors.append(f"evaluation_input_authority_escalated:{field_name}")
    if _contains_forbidden_key(payload):
        errors.append("evaluation_input_forbidden_public_key")
    return sorted(set(errors))


def _measurability_blockers(
    payload: dict[str, Any],
    policy: IndependentEvaluationPolicy,
    *,
    evaluated_at: str,
) -> list[str]:
    blockers: list[str] = []
    if payload.get("evidence_class") == "no_holdout":
        return ["empirical_untouched_holdout_missing"]
    outcomes = payload.get("outcomes", ())
    if len(outcomes) < policy.minimum_holdout_observations:
        blockers.append("holdout_observation_count_below_frozen_minimum")
    if payload.get("untouched_chronological_holdout") is not True:
        blockers.append("untouched_chronological_holdout_not_proven")
    if payload.get("holdout_used_for_selection") is not False:
        blockers.append("holdout_used_for_method_selection")
    if not str(payload.get("holdout_manifest_hash") or "").strip():
        blockers.append("holdout_manifest_hash_missing")
    try:
        start = _parse_timestamp(payload.get("holdout_start"), field_name="holdout_start")
        end = _parse_timestamp(payload.get("holdout_end"), field_name="holdout_end")
        frozen = _parse_timestamp(
            payload.get("thresholds_frozen_at"),
            field_name="thresholds_frozen_at",
        )
        unsealed = _parse_timestamp(
            payload.get("holdout_unsealed_at"),
            field_name="holdout_unsealed_at",
        )
        evaluation_time = _parse_timestamp(evaluated_at, field_name="evaluated_at")
        if start >= end:
            blockers.append("holdout_chronology_invalid")
        if frozen > unsealed:
            blockers.append("thresholds_not_frozen_before_holdout_unsealed")
        if unsealed > evaluation_time:
            blockers.append("holdout_unsealed_after_evaluation")
    except ValueError as exc:
        blockers.append(str(exc))
    if not payload.get("reproducibility_scores"):
        blockers.append("reproducibility_runs_missing")
    if payload.get("noise_sensitivity") is None:
        blockers.append("noise_sensitivity_missing")
    return sorted(set(blockers))


def _positions(scores: tuple[float, ...], threshold: float) -> list[int]:
    return [1 if float(score) >= threshold else -1 for score in scores]


def _net_returns(
    outcomes: tuple[float, ...],
    positions: list[int],
    *,
    transaction_cost_bps: float,
) -> list[float]:
    cost_rate = transaction_cost_bps / 10_000.0
    previous = 0
    rows: list[float] = []
    for outcome, position in zip(outcomes, positions, strict=True):
        turnover = abs(position - previous)
        rows.append(float(position) * float(outcome) - turnover * cost_rate)
        previous = position
    return rows


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _paired_sign_flip_p_value(
    differences: list[float],
    *,
    iterations: int,
    random_seed: int,
) -> float:
    nonzero = [float(value) for value in differences if abs(float(value)) > 1e-15]
    if not nonzero:
        return 1.0
    observed = abs(_mean(nonzero))
    if len(nonzero) <= 16:
        extreme = 0
        total = 1 << len(nonzero)
        for mask in range(total):
            permuted = [
                value if mask & (1 << index) else -value
                for index, value in enumerate(nonzero)
            ]
            if abs(_mean(permuted)) >= observed - 1e-15:
                extreme += 1
        return extreme / total
    rng = random.Random(random_seed)
    extreme = 0
    for _ in range(iterations):
        permuted_mean = _mean(
            [value if rng.random() >= 0.5 else -value for value in nonzero]
        )
        if abs(permuted_mean) >= observed - 1e-15:
            extreme += 1
    return (extreme + 1) / (iterations + 1)


def _benjamini_hochberg(raw_p_values: list[float]) -> list[float]:
    if not raw_p_values:
        return []
    count = len(raw_p_values)
    ordered = sorted(enumerate(raw_p_values), key=lambda row: row[1])
    adjusted = [1.0] * count
    running = 1.0
    for reverse_rank, (index, raw) in enumerate(reversed(ordered), start=1):
        rank = count - reverse_rank + 1
        running = min(running, float(raw) * count / rank)
        adjusted[index] = min(1.0, running)
    return adjusted


def _build_metrics(
    payload: dict[str, Any],
    policy: IndependentEvaluationPolicy,
) -> dict[str, Any]:
    outcomes = tuple(float(value) for value in payload["outcomes"])
    classical_scores = tuple(float(value) for value in payload["classical_scores"])
    quantum_scores = tuple(float(value) for value in payload["quantum_scores"])
    classical_positions = _positions(classical_scores, policy.decision_threshold)
    quantum_positions = _positions(quantum_scores, policy.decision_threshold)
    classical_returns = _net_returns(
        outcomes,
        classical_positions,
        transaction_cost_bps=policy.transaction_cost_bps,
    )
    quantum_returns = _net_returns(
        outcomes,
        quantum_positions,
        transaction_cost_bps=policy.transaction_cost_bps,
    )
    differences = [
        quantum - classical
        for quantum, classical in zip(quantum_returns, classical_returns, strict=True)
    ]
    agreement = _mean(
        [
            1.0 if quantum == classical else 0.0
            for quantum, classical in zip(
                quantum_positions,
                classical_positions,
                strict=True,
            )
        ]
    )
    direction = [1 if outcome >= 0 else -1 for outcome in outcomes]
    classical_accuracy = _mean(
        [
            1.0 if predicted == actual else 0.0
            for predicted, actual in zip(classical_positions, direction, strict=True)
        ]
    )
    quantum_accuracy = _mean(
        [
            1.0 if predicted == actual else 0.0
            for predicted, actual in zip(quantum_positions, direction, strict=True)
        ]
    )
    reproducibility = tuple(
        float(value) for value in payload.get("reproducibility_scores", ())
    )
    minimum_reproducibility = min(reproducibility) if reproducibility else 0.0
    noise_sensitivity = float(payload.get("noise_sensitivity") or 0.0)
    latency_delta = max(
        0.0,
        float(payload["quantum_latency_seconds"])
        - float(payload["classical_latency_seconds"]),
    )
    penalties = {
        "complexity": policy.complexity_penalty,
        "latency": latency_delta * policy.latency_penalty_per_second,
        "provider_cost": (
            float(payload["provider_cost_usd"])
            * policy.provider_cost_penalty_per_usd
            / max(1, len(outcomes))
        ),
        "noise": noise_sensitivity * policy.noise_penalty_weight,
        "reproducibility": (
            max(0.0, 1.0 - minimum_reproducibility)
            * policy.reproducibility_penalty_weight
        ),
    }
    total_penalty = sum(penalties.values())
    raw_incremental = _mean(differences)
    return {
        "observation_count": len(outcomes),
        "classical_mean_net_return": _mean(classical_returns),
        "quantum_mean_net_return": _mean(quantum_returns),
        "classical_cumulative_net_return": sum(classical_returns),
        "quantum_cumulative_net_return": sum(quantum_returns),
        "classical_directional_accuracy": classical_accuracy,
        "quantum_directional_accuracy": quantum_accuracy,
        "lane_directional_agreement": agreement,
        "raw_incremental_value": raw_incremental,
        "operational_penalties": penalties,
        "total_operational_penalty": total_penalty,
        "net_incremental_value": raw_incremental - total_penalty,
        "raw_p_value": _paired_sign_flip_p_value(
            differences,
            iterations=policy.permutation_iterations,
            random_seed=policy.random_seed,
        ),
        "minimum_reproducibility_score": minimum_reproducibility,
        "reproducibility_run_count": len(reproducibility),
        "noise_sensitivity": noise_sensitivity,
    }


def _classify(
    metrics: dict[str, Any],
    *,
    adjusted_p_value: float,
    policy: IndependentEvaluationPolicy,
) -> str:
    net_incremental = float(metrics["net_incremental_value"])
    classical = float(metrics["classical_mean_net_return"])
    quantum = float(metrics["quantum_mean_net_return"])
    significant = adjusted_p_value <= policy.false_discovery_rate_alpha
    reliable = (
        int(metrics["reproducibility_run_count"])
        >= policy.minimum_reproducibility_runs
        and float(metrics["minimum_reproducibility_score"])
        >= policy.minimum_reproducibility_score
        and float(metrics["noise_sensitivity"])
        <= policy.maximum_noise_sensitivity
    )
    if (
        significant
        and reliable
        and net_incremental >= policy.minimum_net_incremental_value
    ):
        return "quantum_strengthened"
    if (
        reliable
        and abs(net_incremental) <= policy.equivalence_margin
        and classical > 0
        and quantum > 0
        and float(metrics["lane_directional_agreement"])
        >= policy.minimum_directional_agreement
    ):
        return "joint_corroboration"
    if (
        significant
        and net_incremental <= -policy.material_underperformance
        and classical > quantum
    ):
        return "classical_preferred"
    if classical <= 0 and quantum <= 0:
        return "weakened"
    return "inconclusive"


def evaluate_independent_quantum_value(
    hybrid_state: dict[str, Any],
    evaluation_inputs: Iterable[IndependentEvaluationInput | dict[str, Any]],
    *,
    evaluated_at: str,
    policy: IndependentEvaluationPolicy | None = None,
) -> dict[str, Any]:
    """Evaluate matched lanes without mutating or promoting hybrid candidates."""

    validate_hybrid_candidate_state(hybrid_state)
    _parse_timestamp(evaluated_at, field_name="evaluated_at")
    active_policy = policy or IndependentEvaluationPolicy()
    validate_evaluation_policy(active_policy)
    candidate_index = {
        candidate["candidate_id"]: candidate for candidate in hybrid_state["candidates"]
    }
    supplied_payloads = [
        item.to_dict() if isinstance(item, IndependentEvaluationInput) else dict(item)
        for item in evaluation_inputs
    ]
    payloads = list(
        {
            stable_hash(payload): payload
            for payload in supplied_payloads
        }.values()
    )
    provisional: list[dict[str, Any]] = []
    measurable_indexes: list[int] = []
    raw_p_values: list[float] = []
    for payload in payloads:
        candidate = candidate_index.get(payload.get("candidate_id"))
        hard_errors = _hard_input_errors(payload)
        if candidate is None:
            hard_errors.append("evaluation_candidate_not_found")
        elif payload.get("candidate_hash") != candidate.get("candidate_hash"):
            hard_errors.append("evaluation_candidate_hash_mismatch")
        elif payload.get("discovery_origin") != candidate.get("discovery_origin"):
            hard_errors.append("evaluation_discovery_origin_mismatch")
        elif payload.get("shared_manifest_hash") not in candidate.get(
            "source_chain", {}
        ).get("shared_manifest_hashes", []):
            hard_errors.append("evaluation_shared_manifest_not_in_candidate_lineage")
        if candidate is not None and payload.get("evidence_class") != "no_holdout":
            candidate_evidence = candidate.get("evidence_records", [])
            classical_matches = [
                record
                for record in candidate_evidence
                if record.get("discovery_origin") == "classical_discovery"
                and record.get("source_result_id")
                == payload.get("matched_classical_baseline_id")
                and record.get("policy_hash")
                == payload.get("matched_classical_policy_hash")
            ]
            quantum_matches = [
                record
                for record in candidate_evidence
                if record.get("discovery_origin") == "quantum_assisted_discovery"
                and record.get("source_candidate_id")
                == payload.get("quantum_method_id")
                and record.get("policy_hash") == payload.get("quantum_policy_hash")
            ]
            if len(classical_matches) != 1:
                hard_errors.append("evaluation_matched_classical_lineage_invalid")
            if len(quantum_matches) != 1:
                hard_errors.append("evaluation_quantum_method_lineage_invalid")
        blockers = (
            []
            if hard_errors
            else _measurability_blockers(
                payload,
                active_policy,
                evaluated_at=evaluated_at,
            )
        )
        if (
            not hard_errors
            and payload.get("evidence_class") == "empirical_untouched_holdout"
            and (
                payload.get("contract_fixture_only") is not False
                or candidate.get("contract_fixture_only") is not False
                or int(candidate.get("empirical_evidence_count") or 0) <= 0
            )
        ):
            blockers.append("candidate_empirical_evidence_missing")
            blockers = sorted(set(blockers))
        metrics = None
        if not hard_errors and payload.get("evidence_class") != "no_holdout":
            metrics = _build_metrics(payload, active_policy)
        provisional.append(
            {
                "payload": payload,
                "candidate": candidate,
                "hard_errors": sorted(set(hard_errors)),
                "blockers": blockers,
                "metrics": metrics,
            }
        )
        if metrics is not None and not blockers and not hard_errors:
            measurable_indexes.append(len(provisional) - 1)
            raw_p_values.append(float(metrics["raw_p_value"]))

    adjusted_values = _benjamini_hochberg(raw_p_values)
    adjusted_by_index = dict(zip(measurable_indexes, adjusted_values, strict=True))
    results: list[dict[str, Any]] = []
    for index, row in enumerate(provisional):
        payload = row["payload"]
        metrics = row["metrics"]
        evidence_class = payload.get("evidence_class")
        if row["hard_errors"]:
            control_verdict = "failed_safely"
            verdict = "failed_safely"
            adjusted_p_value = None
        elif row["blockers"]:
            control_verdict = "not_measurable"
            verdict = "not_measurable"
            adjusted_p_value = None
        else:
            adjusted_p_value = adjusted_by_index[index]
            control_verdict = _classify(
                metrics,
                adjusted_p_value=adjusted_p_value,
                policy=active_policy,
            )
            verdict = (
                control_verdict
                if evidence_class == "empirical_untouched_holdout"
                and payload.get("contract_fixture_only") is False
                else "not_measurable"
            )
        sensitivity = {
            "provider_mode": payload.get("provider_mode"),
            "hardware_experiment_completed": payload.get(
                "hardware_experiment_completed"
            ),
            "hardware_receipt_hash": payload.get("hardware_receipt_hash"),
            "shot_count": payload.get("shot_count"),
            "noise_sensitivity": payload.get("noise_sensitivity"),
            "classical_latency_seconds": payload.get("classical_latency_seconds"),
            "quantum_latency_seconds": payload.get("quantum_latency_seconds"),
            "provider_cost_usd": payload.get("provider_cost_usd"),
            "reproducibility_scores": payload.get("reproducibility_scores"),
        }
        result_material = {
            "candidate_id": payload.get("candidate_id"),
            "candidate_hash": payload.get("candidate_hash"),
            "evaluator_policy_hash": active_policy.policy_hash,
            "evidence_class": evidence_class,
            "holdout_manifest_hash": payload.get("holdout_manifest_hash"),
            "matched_classical_baseline_id": payload.get(
                "matched_classical_baseline_id"
            ),
            "matched_classical_policy_hash": payload.get(
                "matched_classical_policy_hash"
            ),
            "quantum_method_id": payload.get("quantum_method_id"),
            "quantum_policy_hash": payload.get("quantum_policy_hash"),
            "control_verdict": control_verdict,
            "verdict": verdict,
            "metrics": metrics,
            "adjusted_p_value": adjusted_p_value,
            "measurability_blockers": row["blockers"],
            "validation_errors": row["hard_errors"],
            "sensitivity": sensitivity,
        }
        result_hash = stable_hash(result_material)
        results.append(
            {
                "schema_version": RESULT_SCHEMA_VERSION,
                "evaluation_id": f"quantum-value-evaluation:{result_hash[:24]}",
                "evaluation_hash": result_hash,
                "candidate_id": payload.get("candidate_id"),
                "candidate_hash": payload.get("candidate_hash"),
                "discovery_origin": payload.get("discovery_origin"),
                "validation_contribution": verdict,
                "control_verdict": control_verdict,
                "evidence_class": evidence_class,
                "empirical_claim_allowed": verdict not in {
                    "not_measurable",
                    "failed_safely",
                },
                "matched_classical_baseline_id": payload.get(
                    "matched_classical_baseline_id"
                ),
                "matched_classical_policy_hash": payload.get(
                    "matched_classical_policy_hash"
                ),
                "quantum_method_id": payload.get("quantum_method_id"),
                "quantum_policy_hash": payload.get("quantum_policy_hash"),
                "shared_manifest_hash": payload.get("shared_manifest_hash"),
                "chronological_split_identity": payload.get(
                    "chronological_split_identity"
                ),
                "training_validation_manifest_hash": payload.get(
                    "training_validation_manifest_hash"
                ),
                "holdout_manifest_hash": payload.get("holdout_manifest_hash"),
                "thresholds_frozen_at": payload.get("thresholds_frozen_at"),
                "holdout_unsealed_at": payload.get("holdout_unsealed_at"),
                "measurability_blockers": row["blockers"],
                "validation_errors": row["hard_errors"],
                "metrics": metrics,
                "fdr_adjusted_p_value": adjusted_p_value,
                "sensitivity": sensitivity,
                "candidate_mutated": False,
                "validated_edge_created": False,
                "strategy_hypothesis_created": False,
                "trade_candidate_created": False,
                "risk_approval_created": False,
                "execution_approval_created": False,
                "paper_order_created": False,
                "proof_eligible": False,
                "evaluated_at": evaluated_at,
                "authority": _authority(),
            }
        )

    verdict_counts = {verdict: 0 for verdict in VALID_VERDICTS}
    control_verdict_counts = {verdict: 0 for verdict in VALID_VERDICTS}
    for result in results:
        verdict_counts[result["validation_contribution"]] += 1
        control_verdict_counts[result["control_verdict"]] += 1
    measurable_count = sum(
        result["validation_contribution"] not in {"not_measurable", "failed_safely"}
        for result in results
    )
    summary = {
        "schema_version": BATCH_SCHEMA_VERSION,
        "status": (
            "independent_evaluation_measured"
            if measurable_count
            else "independent_evaluation_not_measurable"
        ),
        "evaluated_at": evaluated_at,
        "evaluator_policy": active_policy.to_dict(),
        "evaluator_policy_hash": active_policy.policy_hash,
        "evaluation_count": len(results),
        "empirical_measured_count": measurable_count,
        "synthetic_control_count": sum(
            result["evidence_class"] == "synthetic_control" for result in results
        ),
        "verdict_counts": verdict_counts,
        "control_verdict_counts": control_verdict_counts,
        "quantum_edge_claimed": verdict_counts["quantum_strengthened"] > 0,
        "hardware_evaluation_count": sum(
            result["sensitivity"]["hardware_experiment_completed"] is True
            for result in results
        ),
        "provider_call_attempted": False,
        "hardware_submission_attempted": False,
        "candidate_promotion_count": 0,
        "validated_edge_count": 0,
        "strategy_hypothesis_count": 0,
        "trade_candidate_count": 0,
        "paper_order_count": 0,
        "authority": _authority(),
    }
    overfit = {
        "schema_version": OVERFIT_SCHEMA_VERSION,
        "evaluated_at": evaluated_at,
        "status": (
            "failed_safely"
            if any(row["hard_errors"] for row in provisional)
            else "measured"
            if measurable_count
            else "not_measurable"
        ),
        "evaluation_count": len(results),
        "matched_classical_baseline_missing_count": sum(
            not str(row["payload"].get("matched_classical_baseline_id") or "").strip()
            for row in provisional
        ),
        "holdout_selection_violation_count": sum(
            row["payload"].get("holdout_used_for_selection") is True
            for row in provisional
        ),
        "untouched_holdout_missing_count": sum(
            "untouched_chronological_holdout_not_proven" in row["blockers"]
            for row in provisional
        ),
        "threshold_freeze_violation_count": sum(
            "thresholds_not_frozen_before_holdout_unsealed" in row["blockers"]
            for row in provisional
        ),
        "fdr_control_applied": bool(raw_p_values),
        "transaction_costs_applied": bool(raw_p_values),
        "synthetic_controls_can_create_empirical_claim": False,
        "discovery_model_self_evaluation_allowed": False,
        "provider_call_attempted": False,
        "hardware_submission_attempted": False,
        "authority": _authority(),
    }
    state = {
        "schema_version": BATCH_SCHEMA_VERSION,
        "evaluations": results,
        "summary": summary,
        "overfit_audit": overfit,
    }
    validate_independent_evaluation_state(state)
    return state


def validate_independent_evaluation_state(state: dict[str, Any]) -> None:
    if state.get("schema_version") != BATCH_SCHEMA_VERSION:
        raise ValueError("independent_evaluation_state_schema_invalid")
    evaluations = state.get("evaluations")
    if not isinstance(evaluations, list):
        raise ValueError("independent_evaluations_invalid")
    evaluation_ids: set[str] = set()
    for result in evaluations:
        verdict = result.get("validation_contribution")
        control_verdict = result.get("control_verdict")
        if verdict not in VALID_VERDICTS or control_verdict not in VALID_VERDICTS:
            raise ValueError("independent_evaluation_verdict_invalid")
        if result.get("evidence_class") != "empirical_untouched_holdout" and verdict != "not_measurable":
            if verdict != "failed_safely":
                raise ValueError("non_empirical_evaluation_claimed")
        if result.get("empirical_claim_allowed") is not (
            verdict not in {"not_measurable", "failed_safely"}
        ):
            raise ValueError("independent_evaluation_claim_flag_mismatch")
        result_material = {
            "candidate_id": result.get("candidate_id"),
            "candidate_hash": result.get("candidate_hash"),
            "evaluator_policy_hash": state.get("summary", {}).get(
                "evaluator_policy_hash"
            ),
            "evidence_class": result.get("evidence_class"),
            "holdout_manifest_hash": result.get("holdout_manifest_hash"),
            "matched_classical_baseline_id": result.get(
                "matched_classical_baseline_id"
            ),
            "matched_classical_policy_hash": result.get(
                "matched_classical_policy_hash"
            ),
            "quantum_method_id": result.get("quantum_method_id"),
            "quantum_policy_hash": result.get("quantum_policy_hash"),
            "control_verdict": control_verdict,
            "verdict": verdict,
            "metrics": result.get("metrics"),
            "adjusted_p_value": result.get("fdr_adjusted_p_value"),
            "measurability_blockers": result.get("measurability_blockers"),
            "validation_errors": result.get("validation_errors"),
            "sensitivity": result.get("sensitivity"),
        }
        expected_hash = stable_hash(result_material)
        if result.get("evaluation_hash") != expected_hash:
            raise ValueError("independent_evaluation_hash_mismatch")
        if result.get("evaluation_id") != (
            f"quantum-value-evaluation:{expected_hash[:24]}"
        ):
            raise ValueError("independent_evaluation_id_mismatch")
        if result.get("evaluation_id") in evaluation_ids:
            raise ValueError("independent_evaluation_id_duplicate")
        evaluation_ids.add(result.get("evaluation_id"))
        for key in (
            "candidate_mutated",
            "validated_edge_created",
            "strategy_hypothesis_created",
            "trade_candidate_created",
            "risk_approval_created",
            "execution_approval_created",
            "paper_order_created",
            "proof_eligible",
        ):
            if result.get(key) is not False:
                raise ValueError(f"independent_evaluation_downstream_state:{key}")
        for field_name in WAVE_E_ZERO_AUTHORITY_FIELDS:
            if result.get("authority", {}).get(field_name) is not False:
                raise ValueError(f"independent_evaluation_authority_escalated:{field_name}")
        if any(value is not False for value in result.get("authority", {}).values()):
            raise ValueError("independent_evaluation_unrecognized_authority")
    summary = state.get("summary", {})
    if summary.get("evaluation_count") != len(evaluations):
        raise ValueError("independent_evaluation_summary_count_mismatch")
    policy = summary.get("evaluator_policy")
    if not isinstance(policy, dict) or policy.get("schema_version") != POLICY_SCHEMA_VERSION:
        raise ValueError("independent_evaluation_summary_policy_invalid")
    if summary.get("evaluator_policy_hash") != stable_hash(policy):
        raise ValueError("independent_evaluation_summary_policy_hash_mismatch")
    expected_verdict_counts = {verdict: 0 for verdict in VALID_VERDICTS}
    expected_control_counts = {verdict: 0 for verdict in VALID_VERDICTS}
    for result in evaluations:
        expected_verdict_counts[result["validation_contribution"]] += 1
        expected_control_counts[result["control_verdict"]] += 1
    if summary.get("verdict_counts") != expected_verdict_counts:
        raise ValueError("independent_evaluation_summary_verdict_mismatch")
    if summary.get("control_verdict_counts") != expected_control_counts:
        raise ValueError("independent_evaluation_summary_control_verdict_mismatch")
    if summary.get("quantum_edge_claimed") is not (
        expected_verdict_counts["quantum_strengthened"] > 0
    ):
        raise ValueError("independent_evaluation_summary_edge_claim_mismatch")
    for key in (
        "candidate_promotion_count",
        "validated_edge_count",
        "strategy_hypothesis_count",
        "trade_candidate_count",
        "paper_order_count",
    ):
        if summary.get(key) != 0:
            raise ValueError(f"independent_evaluation_summary_promoted:{key}")
    if summary.get("provider_call_attempted") is not False:
        raise ValueError("independent_evaluation_provider_call_attempted")
    if summary.get("hardware_submission_attempted") is not False:
        raise ValueError("independent_evaluation_hardware_submission_attempted")
    if any(value is not False for value in summary.get("authority", {}).values()):
        raise ValueError("independent_evaluation_summary_authority_escalated")
    overfit = state.get("overfit_audit")
    if not isinstance(overfit, dict) or overfit.get("schema_version") != OVERFIT_SCHEMA_VERSION:
        raise ValueError("independent_evaluation_overfit_audit_invalid")
    if overfit.get("synthetic_controls_can_create_empirical_claim") is not False:
        raise ValueError("independent_evaluation_synthetic_claim_allowed")
    if overfit.get("discovery_model_self_evaluation_allowed") is not False:
        raise ValueError("independent_evaluation_self_evaluation_allowed")
    if any(value is not False for value in overfit.get("authority", {}).values()):
        raise ValueError("independent_evaluation_overfit_authority_escalated")
    if _contains_forbidden_key(state):
        raise ValueError("independent_evaluation_forbidden_public_key")


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def write_independent_evaluation_state(
    runtime_dir: str | Path,
    state: dict[str, Any],
) -> dict[str, Path]:
    validate_independent_evaluation_state(state)
    root = Path(runtime_dir)
    evaluations_path = root / EVALUATION_ARTIFACT
    _atomic_write(
        evaluations_path,
        "".join(
            json.dumps(row, sort_keys=True) + "\n" for row in state["evaluations"]
        ),
    )
    summary_path = root / SUMMARY_ARTIFACT
    _atomic_write(
        summary_path,
        json.dumps(state["summary"], indent=2, sort_keys=True) + "\n",
    )
    overfit_path = root / OVERFIT_ARTIFACT
    _atomic_write(
        overfit_path,
        json.dumps(state["overfit_audit"], indent=2, sort_keys=True) + "\n",
    )
    return {
        "evaluations": evaluations_path,
        "summary": summary_path,
        "overfit_audit": overfit_path,
    }
