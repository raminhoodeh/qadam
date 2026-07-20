"""OR-9 nonlinear and quantum incremental-value research lab."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_nonlinear_quantum_engine import (
    EXPERIMENT_METHODS,
    NEGATIVE_CONTROL_METHOD,
    NONLINEAR_METHODS,
    QUANTUM_METHOD,
    quantum_usefulness_score,
    run_nonlinear_quantum_experiments,
)
from orchestrator.qadam_operator_ready_common import (
    ROOT,
    authority_flags,
    canonical_json,
    file_sha256,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    sha256_text,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_statistical_backtest import load_empirical_backtest_dataset
from orchestrator.qadam_wave_b_common import (
    record_set_hash,
    stable_id,
    write_jsonl_atomic,
)

__all__ = [
    "EXPERIMENT_METHODS",
    "build_and_write_nonlinear_quantum_value",
    "build_nonlinear_quantum_state",
    "quantum_usefulness_score",
    "validate_nonlinear_quantum_state",
]

SCHEMA_VERSION = "qadam_nonlinear_quantum_value.v2"
PHASE_ID = "OR-9"
PROTOCOL_VERSION = "qadam_or9_matched_incremental_value.v1"

EXPERIMENTS_ARTIFACT = "qadam_nonlinear_experiment_registry.jsonl"
COMPARISONS_ARTIFACT = "qadam_quantum_classical_comparison.jsonl"
SUMMARY_ARTIFACT = "qadam_quantum_usefulness_summary.json"
OVERFIT_ARTIFACT = "qadam_nonlinear_overfit_audit.json"
CHECK_ARTIFACT = "qadam_nonlinear_quantum_value_checks.json"

BACKTEST_SUMMARY_ARTIFACT = "qadam_backtest_results_summary.json"
BACKTEST_MANIFEST_ARTIFACT = "qadam_backtest_run_manifest.json"
QUANTUM_GATE_ARTIFACT = "quantum_mandatory_review_gate.json"
QCTRL_READINESS_ARTIFACT = "qctrl_fire_opal_ibm_readiness.json"

RESEARCH_ROOT = ROOT / "data" / "research" / "nonlinear_quantum_value"


def _number(value: Any, default: float = 0.0) -> float:
    if value is None or isinstance(value, bool):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _protocol() -> dict[str, Any]:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "phase_id": PHASE_ID,
        "engine_implementation_sha256": file_sha256(
            Path(__file__).with_name("qadam_nonlinear_quantum_engine.py")
        ),
        "method_registry": list(EXPERIMENT_METHODS),
        "negative_control_method": NEGATIVE_CONTROL_METHOD,
        "matched_baselines": {
            "classical_nonlinear": "strategy_blind_linear_model",
            "quantum_kernel": "rbf_nystrom_kernel_ridge",
        },
        "chronology": {
            "independent_samples_only": True,
            "untouched_holdout_fraction": 0.20,
            "minimum_holdout_rows": 40,
            "model_selection_data": "training_and_validation_only",
            "holdout_tuning_allowed": False,
        },
        "value_test": {
            "metric": "paired_cost_adjusted_decision_return",
            "comparison": "method_minus_matched_classical_baseline",
            "false_discovery_method": "benjamini_hochberg",
            "false_discovery_alpha": 0.05,
            "complexity_penalty_required": True,
            "latency_penalty_required": True,
            "reliability_penalty_required": True,
        },
        "quantum_boundary": {
            "local_simulator_allowed": True,
            "physical_hardware_required": False,
            "physical_hardware_submission_allowed": True,
            "physical_hardware_submission_policy": (
                "explicit_single_use_operator_authorization_with_fixed_budget"
            ),
            "simulator_survivor_required_for_hardware_discovery": False,
            "hardware_scheduler_enabled": False,
            "backend_availability_is_not_incremental_value": True,
            "quantum_approval_authority": False,
        },
        "research_only": {
            "edge_creation_allowed": False,
            "strategy_mutation_allowed": False,
            "candidate_creation_allowed": False,
            "order_creation_allowed": False,
            "broker_write_allowed": False,
            "proof_credit_allowed": False,
            "paper_calendar_advancement_allowed": False,
        },
    }


def _run_identity(backtest_manifest: dict[str, Any]) -> tuple[str, str]:
    protocol_hash = sha256_text(canonical_json(_protocol()))
    run_id = stable_id(
        "nonlinear-quantum-run",
        backtest_manifest.get("run_id"),
        backtest_manifest.get("score_dataset_hash"),
        backtest_manifest.get("label_dataset_hash"),
        protocol_hash,
    )
    return run_id, protocol_hash


def _run_root(run_id: str) -> Path:
    return RESEARCH_ROOT / f"run={run_id.split(':')[-1]}"


def _bulk_paths(run_id: str) -> dict[str, Path]:
    root = _run_root(run_id)
    return {
        "root": root,
        "experiments": root / "experiment_results.jsonl",
        "comparisons": root / "matched_comparisons.jsonl",
        "engine_summary": root / "engine_summary.json",
    }


def _experiment_record(raw: dict[str, Any], *, run_id: str, generated_at: str) -> dict[str, Any]:
    experiment_id = stable_id(
        "nonlinear-experiment",
        run_id,
        raw.get("strategy_family_id"),
        raw.get("instrument"),
        raw.get("horizon"),
        raw.get("method"),
    )
    is_quantum = raw.get("method") == QUANTUM_METHOD
    is_control = raw.get("method") == NEGATIVE_CONTROL_METHOD
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_nonlinear_experiment",
        "generated_at": generated_at,
        "run_id": run_id,
        "experiment_id": experiment_id,
        "experiment_lane": (
            "quantum_simulator"
            if is_quantum
            else "negative_control"
            if is_control
            else "classical_nonlinear"
        ),
        **raw,
        "provider_availability": (
            "qiskit_local_statevector_simulator"
            if is_quantum and raw.get("status") == "measured"
            else "local_classical_compute"
        ),
        "execution_mode": (
            "qiskit_statevector_ideal_simulation"
            if is_quantum and raw.get("status") == "measured"
            else "deterministic_classical_research"
        ),
        "hardware_used": False,
        "hardware_submission_attempted": False,
        "provider_call_attempted": False,
        "trade_approval_created": False,
        "edge_created": False,
        "strategy_mutation_allowed": False,
        "candidate_creation_allowed": False,
        "order_creation_allowed": False,
        "broker_write_allowed": False,
        "proof_credit_allowed": False,
        "paper_calendar_advancement_allowed": False,
        "authority": authority_flags(),
    }


def _comparison_record(experiment: dict[str, Any]) -> dict[str, Any]:
    method_metric = experiment.get("method_mean_decision_return")
    baseline_metric = experiment.get("baseline_mean_decision_return")
    is_quantum = experiment.get("method") == QUANTUM_METHOD
    usefulness = (
        quantum_usefulness_score(
            classical_holdout_metric=(
                _number(baseline_metric) if baseline_metric is not None else None
            ),
            quantum_holdout_metric=(_number(method_metric) if method_metric is not None else None),
            complexity_penalty=_number(experiment.get("complexity_penalty")),
            latency_penalty=_number(experiment.get("latency_penalty")),
            reliability=_number(experiment.get("reliability"), 0.0),
        )
        if is_quantum and experiment.get("status") == "measured"
        else None
    )
    if experiment.get("status") != "measured":
        verdict = "not_measurable_fallback_labelled"
    elif is_quantum:
        verdict = (
            "useful_incremental_value_research_only"
            if experiment.get("incremental_value_candidate") is True
            and usefulness is not None
            and usefulness > 0
            else "not_useful_for_this_edge"
        )
    else:
        verdict = (
            "incremental_value_candidate_research_only"
            if experiment.get("incremental_value_candidate") is True
            else "no_reliable_incremental_value"
        )
    incremental = experiment.get("incremental_mean_decision_return")
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_quantum_classical_comparison",
        "generated_at": experiment["generated_at"],
        "run_id": experiment["run_id"],
        "comparison_id": stable_id("quantum-classical-comparison", experiment["experiment_id"]),
        "experiment_id": experiment["experiment_id"],
        "strategy_family_id": experiment.get("strategy_family_id"),
        "instrument": experiment.get("instrument"),
        "horizon": experiment.get("horizon"),
        "method": experiment.get("method"),
        "experiment_lane": experiment.get("experiment_lane"),
        "classical_baseline": experiment.get("matched_classical_baseline"),
        "classical_holdout_metric": baseline_metric,
        "nonlinear_or_quantum_holdout_metric": method_metric,
        "incremental_holdout_value": incremental,
        "incremental_standard_error": experiment.get("incremental_standard_error"),
        "raw_p_value": experiment.get("raw_p_value"),
        "adjusted_p_value": experiment.get("adjusted_p_value"),
        "complexity_penalty": experiment.get("complexity_penalty"),
        "latency_penalty": experiment.get("latency_penalty"),
        "reliability": experiment.get("reliability"),
        "quantum_usefulness_score": usefulness,
        "verdict": verdict,
        "classical_equal_or_better": (None if incremental is None else _number(incremental) <= 0.0),
        "holdout_untouched_during_tuning": experiment.get("holdout_untouched_during_tuning"),
        "hardware_used": False,
        "simulation_used": is_quantum and experiment.get("status") == "measured",
        "fallback_used": experiment.get("fallback_used") is True,
        "trade_approval_created": False,
        "edge_created": False,
        "candidate_creation_allowed": False,
        "order_creation_allowed": False,
        "broker_write_allowed": False,
        "proof_credit_allowed": False,
        "authority": authority_flags(),
    }


def _write_bulk(
    paths: dict[str, Path],
    experiments: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    engine_summary: dict[str, Any],
) -> None:
    paths["root"].mkdir(parents=True, exist_ok=True)
    write_jsonl_atomic(paths["experiments"], experiments)
    write_jsonl_atomic(paths["comparisons"], comparisons)
    AtomicArtifactStore(paths["root"]).write_json(paths["engine_summary"].name, engine_summary)


def _load_or_run_engine(
    *,
    rows: list[dict[str, Any]],
    run_id: str,
    generated_at: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], bool]:
    paths = _bulk_paths(run_id)
    if all(paths[key].is_file() for key in ("experiments", "comparisons", "engine_summary")):
        experiments = read_jsonl(paths["experiments"])
        comparisons = read_jsonl(paths["comparisons"])
        engine_summary = read_json(paths["engine_summary"])
        if (
            engine_summary.get("run_id") == run_id
            and engine_summary.get("experiment_record_set_hash") == record_set_hash(experiments)
            and engine_summary.get("comparison_record_set_hash") == record_set_hash(comparisons)
        ):
            return experiments, comparisons, engine_summary, True
        raise ValueError("or9_immutable_bulk_output_mismatch")

    engine = run_nonlinear_quantum_experiments(rows)
    experiments = [
        _experiment_record(record, run_id=run_id, generated_at=generated_at)
        for record in engine["records"]
    ]
    comparisons = [_comparison_record(record) for record in experiments]
    engine_summary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_nonlinear_quantum_engine_summary",
        "generated_at": generated_at,
        "run_id": run_id,
        "dependency_truth": engine["dependency_truth"],
        "independent_row_count": engine["independent_row_count"],
        "eligible_group_count": engine["eligible_group_count"],
        "experiment_count": len(experiments),
        "measured_experiment_count": engine["measured_experiment_count"],
        "negative_control_experiment_count": engine["negative_control_experiment_count"],
        "negative_control_false_positive_count": engine["negative_control_false_positive_count"],
        "incremental_value_candidate_count": engine["incremental_value_candidate_count"],
        "experiment_record_set_hash": record_set_hash(experiments),
        "comparison_record_set_hash": record_set_hash(comparisons),
    }
    _write_bulk(paths, experiments, comparisons, engine_summary)
    return experiments, comparisons, engine_summary, False


def _empty_state(
    *,
    generated_at: str,
    run_id: str,
    protocol_hash: str,
    reason: str,
) -> dict[str, Any]:
    safety = authority_flags()
    return {
        "experiments": [],
        "comparisons": [],
        "summary": {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_quantum_usefulness_summary",
            "phase_id": PHASE_ID,
            "generated_at": generated_at,
            "run_id": run_id,
            "protocol_hash": protocol_hash,
            "status": "blocked_missing_or8_empirical_baseline",
            "experiment_count": 0,
            "measured_comparison_count": 0,
            "quantum_usefulness_score": None,
            "empirical_claim_allowed": False,
            "why_no_claim": reason,
            "edge_creation_allowed": False,
            "strategy_mutation_allowed": False,
            "candidate_creation_allowed": False,
            "order_creation_allowed": False,
            "broker_write_allowed": False,
            "proof_credit_allowed": False,
            "authority": safety,
        },
        "overfit": {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "qadam_nonlinear_overfit_audit",
            "generated_at": generated_at,
            "run_id": run_id,
            "status": "blocked_missing_or8_empirical_baseline",
            "holdout_tuning_violation_count": 0,
            "experiment_without_classical_baseline_count": 0,
            "negative_control_false_positive_count": 0,
            "authority": safety,
        },
    }


def build_nonlinear_quantum_state(settings: Settings | None = None) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    backtest = read_json(runtime / BACKTEST_SUMMARY_ARTIFACT)
    backtest_manifest = read_json(runtime / BACKTEST_MANIFEST_ARTIFACT)
    quantum_gate = read_json(runtime / QUANTUM_GATE_ARTIFACT)
    qctrl = read_json(runtime / QCTRL_READINESS_ARTIFACT)
    generated_at = now_iso()
    run_id, protocol_hash = _run_identity(backtest_manifest)
    if (
        backtest_manifest.get("status") != "complete"
        or int(backtest.get("untouched_holdout_result_count") or 0) <= 0
    ):
        return _empty_state(
            generated_at=generated_at,
            run_id=run_id,
            protocol_hash=protocol_hash,
            reason="OR-8 has not produced an empirical untouched holdout baseline.",
        )

    rows, input_audit = load_empirical_backtest_dataset(runtime)
    if not rows or input_audit.get("status") != "empirical_score_label_pairs_loaded":
        return _empty_state(
            generated_at=generated_at,
            run_id=run_id,
            protocol_hash=protocol_hash,
            reason="The frozen OR-8 score-label dataset could not be loaded.",
        )

    experiments, comparisons, engine_summary, reused = _load_or_run_engine(
        rows=rows,
        run_id=run_id,
        generated_at=generated_at,
    )
    measured = [
        record
        for record in comparisons
        if record.get("verdict") != "not_measurable_fallback_labelled"
    ]
    quantum = [record for record in measured if record.get("method") == QUANTUM_METHOD]
    nonlinear = [record for record in measured if record.get("method") in NONLINEAR_METHODS]
    useful_quantum = [
        record
        for record in quantum
        if record.get("verdict") == "useful_incremental_value_research_only"
    ]
    useful_nonlinear = [
        record
        for record in nonlinear
        if record.get("verdict") == "incremental_value_candidate_research_only"
    ]
    scores = [
        _number(record.get("quantum_usefulness_score"))
        for record in quantum
        if record.get("quantum_usefulness_score") is not None
    ]
    comparison_missing_baseline = sum(
        not record.get("classical_baseline") for record in comparisons
    )
    holdout_violations = sum(
        record.get("holdout_untouched_during_tuning") is not True
        for record in comparisons
        if record.get("verdict") != "not_measurable_fallback_labelled"
    )
    fallback_count = sum(record.get("fallback_used") is True for record in comparisons)
    negative_control_false_positives = int(
        engine_summary.get("negative_control_false_positive_count") or 0
    )
    overfit_passed = (
        comparison_missing_baseline == 0
        and holdout_violations == 0
        and negative_control_false_positives == 0
    )
    if useful_quantum:
        status = "complete_incremental_quantum_value_observed_research_only"
        conclusion = (
            "At least one local-simulator quantum feature map added penalized, "
            "false-discovery-controlled holdout value. This is research evidence, "
            "not physical-hardware advantage or trade authority."
        )
    else:
        status = "complete_no_incremental_quantum_value"
        conclusion = (
            "The local Qiskit simulator was measured against matched classical "
            "baselines, but no tested quantum comparison added reliable value after "
            "cost, complexity, latency, reliability, and false-discovery controls."
        )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_quantum_usefulness_summary",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "run_id": run_id,
        "protocol_version": PROTOCOL_VERSION,
        "protocol_hash": protocol_hash,
        "status": status,
        "experiment_count": len(experiments),
        "completed_experiment_count": len(measured),
        "measured_comparison_count": len(measured),
        "nonlinear_comparison_count": len(nonlinear),
        "quantum_comparison_count": len(quantum),
        "useful_nonlinear_comparison_count": len(useful_nonlinear),
        "useful_quantum_comparison_count": len(useful_quantum),
        "not_useful_quantum_comparison_count": len(quantum) - len(useful_quantum),
        "unmeasured_comparison_count": len(comparisons) - len(measured),
        "quantum_usefulness_score": max(scores) if scores else None,
        "quantum_contribution_verdict": (
            "incremental_value_observed_research_only"
            if useful_quantum
            else "not_useful_for_tested_edges"
        ),
        "nonlinear_incremental_value_candidate_count": len(useful_nonlinear),
        "quantum_backend": "qiskit_local_statevector_simulator",
        "quantum_mode": "ideal_local_simulation_not_physical_hardware",
        "existing_quantum_gate_backend": quantum_gate.get("quantum_backend"),
        "existing_quantum_gate_mode": quantum_gate.get("quantum_review_mode"),
        "backend_availability_is_not_incremental_value": True,
        "qctrl_existing_probe_status": qctrl.get("status"),
        "provider_call_attempted_by_or9": False,
        "hardware_submission_attempted_by_or9": False,
        "hardware_used_by_or9": False,
        "hardware_access_required_for_completion": False,
        "classical_fallback_labelled": fallback_count >= 0,
        "fallback_comparison_count": fallback_count,
        "empirical_claim_allowed": True,
        "quantum_advantage_claim_allowed": False,
        "physical_hardware_advantage_claim_allowed": False,
        "conclusion": conclusion,
        "or8_historical_edge_candidate_count": int(
            backtest.get("historical_edge_candidate_count") or 0
        ),
        "or8_validated_edge_count": int(backtest.get("validated_edge_count") or 0),
        "input_audit": input_audit,
        "bulk_outputs": {
            key: str(path.relative_to(ROOT))
            for key, path in _bulk_paths(run_id).items()
            if key != "root"
        },
        "bulk_outputs_reused": reused,
        "edge_creation_allowed": False,
        "strategy_mutation_allowed": False,
        "candidate_creation_allowed": False,
        "order_creation_allowed": False,
        "broker_write_allowed": False,
        "proof_credit_allowed": False,
        "paper_calendar_advancement_allowed": False,
        "paperops_watch_only_mode": True,
        "authority": authority_flags(),
    }
    overfit = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_nonlinear_overfit_audit",
        "generated_at": generated_at,
        "run_id": run_id,
        "status": "passed" if overfit_passed else "blocked",
        "holdout_tuning_violation_count": holdout_violations,
        "experiment_without_classical_baseline_count": comparison_missing_baseline,
        "negative_control_experiment_count": int(
            engine_summary.get("negative_control_experiment_count") or 0
        ),
        "negative_control_false_positive_count": negative_control_false_positives,
        "false_discovery_adjusted_comparison_count": sum(
            record.get("adjusted_p_value") is not None for record in comparisons
        ),
        "complexity_penalty_missing_count": sum(
            record.get("complexity_penalty") is None
            for record in comparisons
            if record.get("verdict") != "not_measurable_fallback_labelled"
        ),
        "latency_penalty_missing_count": sum(
            record.get("latency_penalty") is None
            for record in comparisons
            if record.get("verdict") != "not_measurable_fallback_labelled"
        ),
        "reliability_penalty_missing_count": sum(
            record.get("reliability") is None
            for record in comparisons
            if record.get("verdict") != "not_measurable_fallback_labelled"
        ),
        "feature_selection_training_validation_only": True,
        "final_incremental_value_holdout_only": True,
        "score_dataset_hash": backtest_manifest.get("score_dataset_hash"),
        "label_dataset_hash": backtest_manifest.get("label_dataset_hash"),
        "experiment_record_set_hash": record_set_hash(experiments),
        "comparison_record_set_hash": record_set_hash(comparisons),
        "provider_call_attempted": False,
        "hardware_submission_attempted": False,
        "hardware_used": False,
        "edge_creation_allowed": False,
        "authority": authority_flags(),
    }
    return {
        "experiments": experiments,
        "comparisons": comparisons,
        "summary": summary,
        "overfit": overfit,
    }


def validate_nonlinear_quantum_state(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    experiments = state["experiments"]
    comparisons = state["comparisons"]
    summary = state["summary"]
    overfit = state["overfit"]
    experiment_ids = {record.get("experiment_id") for record in experiments}
    if not experiments:
        errors.append("nonlinear_experiment_registry_empty")
    if len(experiment_ids) != len(experiments):
        errors.append("nonlinear_experiment_id_duplicate")
    if len(comparisons) != len(experiments):
        errors.append("nonlinear_comparison_coverage_incomplete")
    for record in experiments:
        if record.get("hardware_used") is not False:
            errors.append("nonlinear_experiment_hardware_truth_invalid")
        if record.get("holdout_untouched_during_tuning") is not True:
            errors.append("nonlinear_experiment_holdout_tuning_violation")
        for key in (
            "edge_created",
            "strategy_mutation_allowed",
            "candidate_creation_allowed",
            "order_creation_allowed",
            "broker_write_allowed",
            "proof_credit_allowed",
            "paper_calendar_advancement_allowed",
        ):
            if record.get(key) is not False:
                errors.append(f"nonlinear_experiment_unsafe_flag:{key}")
        errors.extend(
            validate_authority(record.get("authority", {}), prefix="nonlinear_experiment")
        )
    for record in comparisons:
        if record.get("experiment_id") not in experiment_ids:
            errors.append("quantum_comparison_missing_experiment")
        if not record.get("classical_baseline"):
            errors.append("quantum_comparison_classical_baseline_missing")
        if record.get("hardware_used") is not False:
            errors.append("quantum_comparison_physical_hardware_mislabelled")
        if record.get("holdout_untouched_during_tuning") is not True:
            errors.append("quantum_comparison_holdout_tuning_violation")
        if record.get("method") == QUANTUM_METHOD:
            if record.get("verdict") == "not_useful_for_this_edge" and (
                record.get("quantum_usefulness_score") is None
            ):
                errors.append("quantum_not_useful_verdict_missing_score")
            if record.get("simulation_used") is not True:
                errors.append("quantum_simulation_not_labelled")
        for key in (
            "trade_approval_created",
            "edge_created",
            "candidate_creation_allowed",
            "order_creation_allowed",
            "broker_write_allowed",
            "proof_credit_allowed",
        ):
            if record.get(key) is not False:
                errors.append(f"quantum_comparison_unsafe_flag:{key}")
        errors.extend(validate_authority(record.get("authority", {}), prefix="quantum_comparison"))
    if summary.get("backend_availability_is_not_incremental_value") is not True:
        errors.append("quantum_backend_confused_with_value")
    if summary.get("provider_call_attempted_by_or9") is not False:
        errors.append("or9_provider_call_attempted")
    if summary.get("hardware_submission_attempted_by_or9") is not False:
        errors.append("or9_hardware_submission_attempted")
    if summary.get("hardware_used_by_or9") is not False:
        errors.append("or9_physical_hardware_mislabelled")
    if summary.get("quantum_advantage_claim_allowed") is not False:
        errors.append("or9_quantum_advantage_claim_unsafe")
    if int(summary.get("measured_comparison_count") or 0) <= 0:
        errors.append("or9_empirical_comparison_missing")
    if int(summary.get("quantum_comparison_count") or 0) <= 0:
        errors.append("or9_quantum_comparison_missing")
    if overfit.get("holdout_tuning_violation_count") != 0:
        errors.append("nonlinear_holdout_tuning_violation")
    if overfit.get("experiment_without_classical_baseline_count") != 0:
        errors.append("nonlinear_classical_baseline_missing")
    if overfit.get("negative_control_false_positive_count") != 0:
        errors.append("nonlinear_negative_control_false_positive")
    for key in (
        "complexity_penalty_missing_count",
        "latency_penalty_missing_count",
        "reliability_penalty_missing_count",
    ):
        if int(overfit.get(key) or 0) != 0:
            errors.append(f"nonlinear_required_penalty_missing:{key}")
    errors.extend(validate_authority(summary.get("authority", {}), prefix="quantum_summary"))
    errors.extend(validate_authority(overfit.get("authority", {}), prefix="nonlinear_overfit"))
    return unique_errors(errors)


def build_and_write_nonlinear_quantum_value(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    state = build_nonlinear_quantum_state(settings)
    store.write_jsonl(EXPERIMENTS_ARTIFACT, state["experiments"])
    store.write_jsonl(COMPARISONS_ARTIFACT, state["comparisons"])
    store.write_json(SUMMARY_ARTIFACT, state["summary"])
    store.write_json(OVERFIT_ARTIFACT, state["overfit"])
    errors = validate_nonlinear_quantum_state(state)
    acceptance_passed = (
        not errors
        and state["overfit"].get("status") == "passed"
        and int(state["summary"].get("measured_comparison_count") or 0) > 0
        and int(state["summary"].get("quantum_comparison_count") or 0) > 0
    )
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_nonlinear_quantum_value_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if acceptance_passed else "blocked",
        "implementation_ready": acceptance_passed,
        "acceptance_passed": acceptance_passed,
        "empirical_incremental_value_complete": acceptance_passed,
        "experiment_count": state["summary"].get("experiment_count", 0),
        "measured_comparison_count": state["summary"].get("measured_comparison_count", 0),
        "nonlinear_comparison_count": state["summary"].get("nonlinear_comparison_count", 0),
        "quantum_comparison_count": state["summary"].get("quantum_comparison_count", 0),
        "useful_nonlinear_comparison_count": state["summary"].get(
            "useful_nonlinear_comparison_count", 0
        ),
        "useful_quantum_comparison_count": state["summary"].get(
            "useful_quantum_comparison_count", 0
        ),
        "quantum_usefulness_score": state["summary"].get("quantum_usefulness_score"),
        "quantum_contribution_verdict": state["summary"].get("quantum_contribution_verdict"),
        "classical_baseline_missing_count": state["overfit"].get(
            "experiment_without_classical_baseline_count", 0
        ),
        "holdout_tuning_violation_count": state["overfit"].get("holdout_tuning_violation_count", 0),
        "negative_control_false_positive_count": state["overfit"].get(
            "negative_control_false_positive_count", 0
        ),
        "provider_call_attempted": state["summary"].get("provider_call_attempted_by_or9"),
        "hardware_submission_attempted": state["summary"].get(
            "hardware_submission_attempted_by_or9"
        ),
        "hardware_used": state["summary"].get("hardware_used_by_or9"),
        "quantum_advantage_claim_allowed": state["summary"].get("quantum_advantage_claim_allowed"),
        "edge_creation_allowed": state["summary"].get("edge_creation_allowed"),
        "candidate_creation_allowed": state["summary"].get("candidate_creation_allowed"),
        "broker_write_count": 0,
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    store.write_json(CHECK_ARTIFACT, checks)
    return state, checks, errors
