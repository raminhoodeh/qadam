from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import json

import pytest

from orchestrator.qadam_classical_discovery import run_classical_discovery
from orchestrator.qadam_discovery_contract_fixture import (
    build_wave_c_contract_fixture_batch,
)
from orchestrator.qadam_hybrid_candidate_merger import (
    HybridMergeContext,
    discovery_evidence_records,
    merge_hybrid_candidates,
    validate_hybrid_candidate_state,
    write_hybrid_candidate_state,
)
from orchestrator.qadam_independent_quantum_value import (
    IndependentEvaluationInput,
    IndependentEvaluationPolicy,
    evaluate_independent_quantum_value,
    no_holdout_evaluation_input,
    validate_independent_evaluation_state,
    write_independent_evaluation_state,
)
from orchestrator.qadam_local_quantum_discovery import (
    QiskitLocalQuantumDiscoveryBackend,
)
from orchestrator.qadam_quantum_discovery_evidence import stable_hash

pytestmark = pytest.mark.filterwarnings(
    "ignore:Since backends now support running jobs.*:DeprecationWarning"
)

EVALUATED_AT = "2026-07-12T12:00:00+00:00"


def _context(**overrides) -> HybridMergeContext:
    values = {
        "source_transform_key": "wave-c-nonlinear-contract-features.v1",
        "feature_pair": ("source_density", "source_agreement"),
        "economic_target": "crude oil repricing",
        "outcome_definition": "BNO one-day directional return",
        "relationship_key": "source density x source agreement",
        "direction_or_question": "nonlinear interaction",
        "horizon": "one_day",
        "regime": "all_regimes",
        "accepted_instruments": ("BNO", "USO"),
        "relationship": "Source density and source agreement move together nonlinearly.",
        "interpretation": (
            "A broad and mutually confirming source regime may precede crude-oil repricing."
        ),
        "confirmation": "Repeat the relationship on untouched point-in-time evidence.",
        "falsifier": "No holdout improvement over the matched classical baseline.",
        "blocker": "No empirical chronological holdout exists yet.",
        "next_action": "Backfill provider evidence and run independent evaluation.",
    }
    values.update(overrides)
    return HybridMergeContext(**values)


@pytest.fixture(scope="module")
def hybrid_fixture():
    batch = build_wave_c_contract_fixture_batch()
    classical = run_classical_discovery(batch)
    quantum = QiskitLocalQuantumDiscoveryBackend().run(
        batch,
        mode="ideal",
        matched_classical_result=classical,
    )
    evidence = [
        *discovery_evidence_records(classical),
        *discovery_evidence_records(quantum),
    ]
    state = merge_hybrid_candidates(
        [_context()],
        evidence,
        generated_at="2026-07-12T11:00:00+00:00",
    )
    return batch, classical, quantum, evidence, state


def _alternating_outcomes(count: int = 40) -> tuple[float, ...]:
    return tuple(0.01 if index % 2 == 0 else -0.01 for index in range(count))


def _aligned_scores(outcomes: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(0.9 if outcome > 0 else 0.1 for outcome in outcomes)


def _opposed_scores(outcomes: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(0.1 if outcome > 0 else 0.9 for outcome in outcomes)


def _synthetic_input(
    state: dict,
    batch,
    *,
    suffix: str,
    outcomes: tuple[float, ...],
    classical_scores: tuple[float, ...],
    quantum_scores: tuple[float, ...],
    provider_cost_usd: float = 0.0,
) -> IndependentEvaluationInput:
    candidate = state["candidates"][0]
    classical_evidence = next(
        row
        for row in candidate["evidence_records"]
        if row["discovery_origin"] == "classical_discovery"
    )
    quantum_evidence = next(
        row
        for row in candidate["evidence_records"]
        if row["discovery_origin"] == "quantum_assisted_discovery"
    )
    return IndependentEvaluationInput(
        candidate_id=candidate["candidate_id"],
        candidate_hash=candidate["candidate_hash"],
        discovery_origin=candidate["discovery_origin"],
        shared_manifest_hash=batch.shared_manifest_hash,
        chronological_split_identity=f"chronological-split:{suffix}",
        training_validation_manifest_hash=stable_hash(["train-validation", suffix]),
        holdout_manifest_hash=stable_hash(["untouched-holdout", suffix]),
        matched_classical_baseline_id=classical_evidence["source_result_id"],
        matched_classical_policy_hash=classical_evidence["policy_hash"],
        quantum_method_id=quantum_evidence["source_candidate_id"],
        quantum_policy_hash=quantum_evidence["policy_hash"],
        evidence_class="synthetic_control",
        holdout_start="2025-01-01T00:00:00+00:00",
        holdout_end="2025-02-10T00:00:00+00:00",
        thresholds_frozen_at="2026-07-12T09:00:00+00:00",
        holdout_unsealed_at="2026-07-12T10:00:00+00:00",
        untouched_chronological_holdout=True,
        holdout_used_for_selection=False,
        outcomes=outcomes,
        classical_scores=classical_scores,
        quantum_scores=quantum_scores,
        provider_mode="local_finite_shot_simulator",
        hardware_experiment_completed=False,
        hardware_receipt_hash=None,
        shot_count=256,
        noise_sensitivity=0.01,
        classical_latency_seconds=0.05,
        quantum_latency_seconds=0.25,
        provider_cost_usd=provider_cost_usd,
        reproducibility_scores=(0.99, 0.98, 0.99),
        contract_fixture_only=True,
    )


def test_candidate_identity_collapses_proxy_duplicates_but_not_distinct_outcomes():
    canonical = _context()
    proxy = _context(accepted_instruments=("USO",))
    distinct_outcome = _context(outcome_definition="USO five-day volatility change")

    assert canonical.candidate_id == proxy.candidate_id
    assert canonical.candidate_id != distinct_outcome.candidate_id


def test_classical_and_quantum_evidence_merge_into_one_joint_candidate(hybrid_fixture):
    _batch, _classical, _quantum, _evidence, state = hybrid_fixture
    candidate = state["candidates"][0]

    assert state["summary"]["candidate_count"] == 1
    assert state["summary"]["joint_candidate_count"] == 1
    assert state["summary"]["provenance_count"] == 2
    assert candidate["discovery_origin"] == "joint_discovery"
    assert candidate["discovery_origins"] == [
        "classical_discovery",
        "quantum_assisted_discovery",
    ]
    assert candidate["validation_contribution"] == "not_tested"
    assert candidate["contract_fixture_only"] is True
    assert candidate["candidate_persistence_allowed"] is False
    validate_hybrid_candidate_state(state)


def test_merger_deduplicates_evidence_and_records_unmatched_rejections(hybrid_fixture):
    _batch, _classical, _quantum, evidence, _state = hybrid_fixture
    deduplicated = merge_hybrid_candidates(
        [_context()],
        [*evidence, *evidence],
        generated_at="2026-07-12T11:01:00+00:00",
    )
    rejected = merge_hybrid_candidates(
        [_context(accepted_instruments=("USO",))],
        evidence,
        generated_at="2026-07-12T11:02:00+00:00",
    )

    assert deduplicated["candidates"][0]["evidence_record_count"] == 2
    assert deduplicated["summary"]["provenance_count"] == 2
    assert rejected["summary"]["candidate_count"] == 0
    assert rejected["summary"]["rejection_count"] == 2
    assert {row["reason"] for row in rejected["rejections"]} == {
        "no_identity_context_match"
    }


def test_merge_never_promotes_candidate_or_creates_execution_authority(hybrid_fixture):
    _batch, _classical, _quantum, _evidence, state = hybrid_fixture
    candidate = state["candidates"][0]

    assert state["summary"]["validated_edge_count"] == 0
    assert state["summary"]["strategy_hypothesis_count"] == 0
    assert state["summary"]["trade_candidate_count"] == 0
    assert state["summary"]["paper_order_count"] == 0
    assert candidate["validated_edge_created"] is False
    assert candidate["paper_order_created"] is False
    assert not any(candidate["authority"].values())


def test_current_fixture_truth_is_not_measurable_and_does_not_mutate_candidate(
    hybrid_fixture,
):
    batch, _classical, _quantum, _evidence, state = hybrid_fixture
    before = deepcopy(state)
    evaluation = evaluate_independent_quantum_value(
        state,
        [
            no_holdout_evaluation_input(
                state["candidates"][0],
                shared_manifest_hash=batch.shared_manifest_hash,
            )
        ],
        evaluated_at=EVALUATED_AT,
    )
    result = evaluation["evaluations"][0]

    assert state == before
    assert result["validation_contribution"] == "not_measurable"
    assert result["control_verdict"] == "not_measurable"
    assert result["measurability_blockers"] == [
        "empirical_untouched_holdout_missing"
    ]
    assert result["candidate_mutated"] is False
    assert evaluation["summary"]["quantum_edge_claimed"] is False
    validate_independent_evaluation_state(evaluation)


def test_positive_synthetic_control_exercises_math_without_claiming_edge(hybrid_fixture):
    batch, _classical, _quantum, _evidence, state = hybrid_fixture
    outcomes = _alternating_outcomes()
    evaluation = evaluate_independent_quantum_value(
        state,
        [
            _synthetic_input(
                state,
                batch,
                suffix="positive",
                outcomes=outcomes,
                classical_scores=tuple(0.6 for _ in outcomes),
                quantum_scores=_aligned_scores(outcomes),
            )
        ],
        evaluated_at=EVALUATED_AT,
    )
    result = evaluation["evaluations"][0]

    assert result["control_verdict"] == "quantum_strengthened"
    assert result["validation_contribution"] == "not_measurable"
    assert result["empirical_claim_allowed"] is False
    assert result["metrics"]["net_incremental_value"] > 0
    assert result["fdr_adjusted_p_value"] <= 0.05
    assert evaluation["summary"]["quantum_edge_claimed"] is False


def test_classical_preferred_and_joint_control_branches_are_distinct(hybrid_fixture):
    batch, _classical, _quantum, _evidence, state = hybrid_fixture
    outcomes = _alternating_outcomes()
    classical_preferred = _synthetic_input(
        state,
        batch,
        suffix="classical-preferred",
        outcomes=outcomes,
        classical_scores=_aligned_scores(outcomes),
        quantum_scores=_opposed_scores(outcomes),
    )
    joint = _synthetic_input(
        state,
        batch,
        suffix="joint",
        outcomes=outcomes,
        classical_scores=_aligned_scores(outcomes),
        quantum_scores=_aligned_scores(outcomes),
    )
    evaluation = evaluate_independent_quantum_value(
        state,
        [classical_preferred, joint],
        evaluated_at=EVALUATED_AT,
    )

    assert [row["control_verdict"] for row in evaluation["evaluations"]] == [
        "classical_preferred",
        "joint_corroboration",
    ]
    assert all(
        row["validation_contribution"] == "not_measurable"
        for row in evaluation["evaluations"]
    )


def test_null_control_cannot_create_quantum_strengthened_verdict(hybrid_fixture):
    batch, _classical, _quantum, _evidence, state = hybrid_fixture
    outcomes = tuple(0.0 for _ in range(40))
    control = _synthetic_input(
        state,
        batch,
        suffix="null",
        outcomes=outcomes,
        classical_scores=tuple(0.6 for _ in outcomes),
        quantum_scores=tuple(0.6 for _ in outcomes),
    )
    evaluation = evaluate_independent_quantum_value(
        state,
        [control],
        evaluated_at=EVALUATED_AT,
    )

    assert evaluation["evaluations"][0]["control_verdict"] == "weakened"
    assert evaluation["summary"]["control_verdict_counts"]["quantum_strengthened"] == 0
    assert evaluation["summary"]["quantum_edge_claimed"] is False


def test_multiple_testing_adjustment_is_applied_across_controls(hybrid_fixture):
    batch, _classical, _quantum, _evidence, state = hybrid_fixture
    outcomes = _alternating_outcomes()
    inputs = [
        _synthetic_input(
            state,
            batch,
            suffix=f"fdr-{index}",
            outcomes=outcomes,
            classical_scores=tuple(0.6 for _ in outcomes),
            quantum_scores=_aligned_scores(outcomes),
        )
        for index in range(3)
    ]
    evaluation = evaluate_independent_quantum_value(
        state,
        inputs,
        evaluated_at=EVALUATED_AT,
    )

    assert evaluation["overfit_audit"]["fdr_control_applied"] is True
    assert all(
        row["fdr_adjusted_p_value"] >= row["metrics"]["raw_p_value"]
        for row in evaluation["evaluations"]
    )


def test_holdout_selection_and_fixture_empiricism_fail_closed(hybrid_fixture):
    batch, _classical, _quantum, _evidence, state = hybrid_fixture
    outcomes = _alternating_outcomes()
    base = _synthetic_input(
        state,
        batch,
        suffix="holdout-misuse",
        outcomes=outcomes,
        classical_scores=tuple(0.6 for _ in outcomes),
        quantum_scores=_aligned_scores(outcomes),
    )
    mislabeled = replace(
        base,
        evidence_class="empirical_untouched_holdout",
        contract_fixture_only=False,
        holdout_used_for_selection=True,
    )
    evaluation = evaluate_independent_quantum_value(
        state,
        [mislabeled],
        evaluated_at=EVALUATED_AT,
    )
    result = evaluation["evaluations"][0]

    assert result["validation_contribution"] == "not_measurable"
    assert "holdout_used_for_method_selection" in result["measurability_blockers"]
    assert "candidate_empirical_evidence_missing" in result["measurability_blockers"]
    assert evaluation["overfit_audit"]["holdout_selection_violation_count"] == 1


def test_operational_cost_penalty_can_erase_apparent_quantum_lift(hybrid_fixture):
    batch, _classical, _quantum, _evidence, state = hybrid_fixture
    outcomes = _alternating_outcomes()
    control = _synthetic_input(
        state,
        batch,
        suffix="provider-cost",
        outcomes=outcomes,
        classical_scores=tuple(0.6 for _ in outcomes),
        quantum_scores=_aligned_scores(outcomes),
        provider_cost_usd=100.0,
    )
    policy = IndependentEvaluationPolicy(provider_cost_penalty_per_usd=0.1)
    evaluation = evaluate_independent_quantum_value(
        state,
        [control],
        evaluated_at=EVALUATED_AT,
        policy=policy,
    )
    result = evaluation["evaluations"][0]

    assert result["metrics"]["raw_incremental_value"] > 0
    assert result["metrics"]["net_incremental_value"] < 0
    assert result["control_verdict"] != "quantum_strengthened"


def test_authority_tampering_and_unearned_hardware_claim_fail_safely(hybrid_fixture):
    batch, _classical, _quantum, _evidence, state = hybrid_fixture
    outcomes = _alternating_outcomes()
    base = _synthetic_input(
        state,
        batch,
        suffix="tamper",
        outcomes=outcomes,
        classical_scores=tuple(0.6 for _ in outcomes),
        quantum_scores=_aligned_scores(outcomes),
    ).to_dict()
    authority_tamper = deepcopy(base)
    authority_tamper["authority"]["paper_order_allowed"] = True
    hardware_tamper = deepcopy(base)
    hardware_tamper["provider_mode"] = "ibm_quantum_via_fire_opal"
    baseline_tamper = deepcopy(base)
    baseline_tamper["matched_classical_baseline_id"] = "invented-baseline"
    evaluation = evaluate_independent_quantum_value(
        state,
        [authority_tamper, hardware_tamper, baseline_tamper],
        evaluated_at=EVALUATED_AT,
    )

    assert all(
        row["validation_contribution"] == "failed_safely"
        for row in evaluation["evaluations"]
    )
    assert any(
        "evaluation_input_authority_escalated:paper_order_allowed"
        in row["validation_errors"]
        for row in evaluation["evaluations"]
    )
    assert any(
        "evaluation_input_hardware_mode_mismatch" in row["validation_errors"]
        for row in evaluation["evaluations"]
    )
    assert any(
        "evaluation_matched_classical_lineage_invalid" in row["validation_errors"]
        for row in evaluation["evaluations"]
    )
    assert evaluation["summary"]["paper_order_count"] == 0
    assert evaluation["summary"]["hardware_submission_attempted"] is False


def test_durable_ledgers_are_public_safe_and_result_tampering_is_rejected(
    tmp_path,
    hybrid_fixture,
):
    batch, _classical, _quantum, _evidence, state = hybrid_fixture
    evaluation = evaluate_independent_quantum_value(
        state,
        [
            no_holdout_evaluation_input(
                state["candidates"][0],
                shared_manifest_hash=batch.shared_manifest_hash,
            )
        ],
        evaluated_at=EVALUATED_AT,
    )
    hybrid_paths = write_hybrid_candidate_state(tmp_path, state)
    evaluation_paths = write_independent_evaluation_state(tmp_path, evaluation)
    public_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [*hybrid_paths.values(), *evaluation_paths.values()]
    )

    assert all(path.exists() for path in [*hybrid_paths.values(), *evaluation_paths.values()])
    assert "qasm_circuits" not in public_text
    assert "raw_provider_response" not in public_text
    assert "provider_job_ids" not in public_text
    assert "api_key" not in public_text
    assert json.loads(evaluation_paths["summary"].read_text(encoding="utf-8"))[
        "quantum_edge_claimed"
    ] is False

    tampered = deepcopy(evaluation)
    tampered["evaluations"][0]["validation_contribution"] = "quantum_strengthened"
    with pytest.raises(ValueError, match="non_empirical_evaluation_claimed"):
        validate_independent_evaluation_state(tampered)

    hash_tampered = deepcopy(evaluation)
    hash_tampered["evaluations"][0]["candidate_hash"] = "tampered"
    with pytest.raises(ValueError, match="independent_evaluation_hash_mismatch"):
        validate_independent_evaluation_state(hash_tampered)
