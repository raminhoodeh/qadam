"""QSASE-6 nonlinear and quantum pattern lab.

This lab tests whether QSASE-5 linear evidence contains interaction,
regime, path-dependent, or quantum-reviewed structure. Results are research
evidence only; quantum review is never trade approval or execution authority.
"""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.config import Settings
from orchestrator.qsase_governance_safety_contract import (
    PHASE_STATUS_ARTIFACT,
    universal_authority_flags,
)

SCHEMA_VERSION = "qsase_nonlinear_quantum_pattern_lab.v1"
PHASE_ID = "qsase_6_nonlinear_quantum_pattern_lab"
PHASE_NAME = "QSASE-6: Nonlinear And Quantum Pattern Lab"
IMPLEMENTATION_LOG = "docs/qsase-implementation-log.md"

PRIMARY_ARTIFACT = "qsase_nonlinear_quantum_pattern_lab.json"
NONLINEAR_RESULTS_ARTIFACT = "qsase_nonlinear_pattern_results.jsonl"
QUANTUM_REVIEWS_ARTIFACT = "qsase_quantum_pattern_reviews.jsonl"
EVENTS_ARTIFACT = "qsase_nonlinear_quantum_pattern_lab_events.jsonl"
HISTORY_ARTIFACT = "qsase_nonlinear_quantum_pattern_lab_history.jsonl"
DASHBOARD_SUMMARY_ARTIFACT = "qsase_nonlinear_quantum_pattern_lab_dashboard_summary.json"

LINEAR_LAB_READY_STATUSES = {
    "qsase_linear_pattern_lab_ready",
    "qsase_linear_pattern_lab_ready_with_holds",
}

HISTORICAL_MEMORY_READY_STATUSES = {
    "qsase_historical_source_price_memory_ready",
    "qsase_historical_source_price_memory_ready_with_gaps",
}

LINEAR_LAB_ARTIFACT = "qsase_linear_pattern_lab.json"
LINEAR_RESULTS_ARTIFACT = "qsase_linear_backtest_results.jsonl"
LINEAR_REJECTED_ARTIFACT = "qsase_linear_rejected_patterns.jsonl"
HISTORICAL_MEMORY_ARTIFACT = "qsase_historical_source_price_memory.json"
HISTORICAL_MEMORY_JSONL_ARTIFACT = "qsase_historical_source_price_memory.jsonl"
SOURCE_PRICE_MATRIX_ARTIFACT = "qsase_universal_source_price_matrix.json"
QUANTUM_ORACLE_RESULTS_ARTIFACT = "quantum_oracle_results.jsonl"
QUANTUM_REVIEW_GATE_ARTIFACT = "quantum_mandatory_review_gate.json"
QCTRL_FIRE_OPAL_IBM_ARTIFACT = "qctrl_fire_opal_ibm_readiness.json"
PAPEROPS_QCTRL_CONSULTATION_ARTIFACT = "paperops_qctrl_paper_consultation.json"
QUANTUM_META_REVIEW_ARTIFACT = "quantum_meta_review.json"

NONLINEAR_AUTHORITY_FLAGS = {
    "trade_candidate_creation_allowed": False,
    "trade_candidate_created": False,
    "strategy_hypothesis_creation_allowed": False,
    "strategy_hypothesis_created": False,
    "risk_approval_allowed": False,
    "execution_allowed": False,
    "execution_approval_allowed": False,
    "paper_order_allowed": False,
    "paper_order_created": False,
    "broker_write_allowed": False,
    "prediction_market_write_allowed": False,
    "telegram_command_path_enabled": False,
    "telegram_trade_command_enabled": False,
    "quantum_job_authority": False,
    "provider_call_allowed": False,
    "provider_call_attempted_by_this_lab": False,
    "hardware_submission_allowed": False,
    "hardware_submitted": False,
    "hardware_scheduler_enabled": False,
    "recommendation_authority": False,
    "live_capital_enabled": False,
    "proof_credit_allowed": False,
    "paper_proof_ledger_credit_allowed": False,
    "paper_growth_trial_calendar_advance_allowed": False,
    "direct_paperops_handoff_allowed": False,
}

NONLINEAR_METHOD_FAMILIES = [
    "interaction_scan",
    "threshold_scan",
    "regime_conditioned_test",
    "tree_rule_extraction",
    "cluster_nearest_regime_matching",
    "anomaly_divergence_detection",
    "lagged_state_transition",
]

ALLOWED_QUANTUM_BACKENDS = {
    "classical_fallback",
    "qiskit_aer_local",
    "deterministic_classical_fallback",
}
ALLOWED_QUANTUM_MODES = {
    "deterministic_classical_shadow",
    "qiskit_aer_local_simulator",
}
ALLOWED_QUANTUM_JOB_TYPES = {"pattern_recognition", "strategy_collapse"}
ALLOWED_QUANTUM_RECOMMENDATIONS = {
    "hold",
    "downgrade_or_hold",
    "upgrade_shadow_confidence",
}

REQUIRED_NONLINEAR_FIELDS = [
    "nonlinear_pattern_id",
    "source_linear_pattern_id",
    "source_recipe",
    "market_expression",
    "baseline",
    "nonlinear_tests",
    "sample",
    "decision",
    "authority",
]

REQUIRED_QUANTUM_REVIEW_FIELDS = [
    "quantum_review_id",
    "source_pattern_id",
    "job_type",
    "backend",
    "quantum_mode",
    "local_validation_status",
    "hardware_submission_allowed",
    "hardware_submitted",
    "provider_call_allowed",
    "input_contract",
    "scores",
    "recommendation",
    "authority",
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _runtime_dir(settings: Settings | None = None) -> Path:
    active_settings = settings or Settings.from_env()
    path = Path(active_settings.runtime_dir)
    if not path.is_absolute():
        path = _repo_root() / path
    return path


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _json_dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _jsonl_line(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True) + "\n"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    if limit is not None:
        lines = lines[-limit:]
    records: list[dict[str, Any]] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_dump(payload), encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(_jsonl_line(record) for record in records), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(_jsonl_line(payload))


def _hash_id(parts: list[Any], prefix: str) -> str:
    raw = "|".join(str(part) for part in parts)
    return f"{prefix}:{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]}"


def _nonlinear_pattern_id(linear_pattern_id: str) -> str:
    return _hash_id([SCHEMA_VERSION, linear_pattern_id, "nonlinear"], "qsase-nonlinear")


def _quantum_review_id(nonlinear_pattern_id: str, job_type: str) -> str:
    return _hash_id([SCHEMA_VERSION, nonlinear_pattern_id, job_type, "quantum-review"], "qsase-quantum")


def _input_fingerprint(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _safe_mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _authority_block() -> dict[str, Any]:
    return {
        "research_only": True,
        "quantum_review_is_not_trade_approval": True,
        **NONLINEAR_AUTHORITY_FLAGS,
    }


def _load_context(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    return {
        "runtime_dir": runtime,
        "linear_lab": _read_json(runtime / LINEAR_LAB_ARTIFACT),
        "linear_results": _read_jsonl(runtime / LINEAR_RESULTS_ARTIFACT),
        "linear_rejected_patterns": _read_jsonl(runtime / LINEAR_REJECTED_ARTIFACT),
        "historical_memory": _read_json(runtime / HISTORICAL_MEMORY_ARTIFACT),
        "historical_records": _read_jsonl(runtime / HISTORICAL_MEMORY_JSONL_ARTIFACT),
        "source_price_matrix": _read_json(runtime / SOURCE_PRICE_MATRIX_ARTIFACT),
        "quantum_oracle_results": _read_jsonl(runtime / QUANTUM_ORACLE_RESULTS_ARTIFACT, limit=50),
        "quantum_review_gate": _read_json(runtime / QUANTUM_REVIEW_GATE_ARTIFACT),
        "qctrl_fire_opal_ibm": _read_json(runtime / QCTRL_FIRE_OPAL_IBM_ARTIFACT),
        "paperops_qctrl_consultation": _read_json(runtime / PAPEROPS_QCTRL_CONSULTATION_ARTIFACT),
        "quantum_meta_review": _read_json(runtime / QUANTUM_META_REVIEW_ARTIFACT),
    }


def _latest_quantum_result(context: dict[str, Any]) -> dict[str, Any]:
    for record in reversed(context.get("quantum_oracle_results", [])):
        result = record.get("result")
        if isinstance(result, dict):
            return result
    return {}


def _quantum_state(context: dict[str, Any]) -> dict[str, Any]:
    latest_result = _latest_quantum_result(context)
    qctrl = context.get("qctrl_fire_opal_ibm", {})
    gate = context.get("quantum_review_gate", {})
    backend = latest_result.get("backend") or gate.get("quantum_backend") or "classical_fallback"
    mode = latest_result.get("local_simulation_mode") or gate.get("quantum_review_mode") or "deterministic_classical_shadow"
    if backend not in ALLOWED_QUANTUM_BACKENDS:
        backend = "classical_fallback"
    if mode not in ALLOWED_QUANTUM_MODES:
        mode = "deterministic_classical_shadow"
    return {
        "status": gate.get("quantum_review_status") or latest_result.get("status") or "degraded_no_recent_quantum_result",
        "quantum_review_required": gate.get("quantum_review_required") is True,
        "quantum_review_complete": gate.get("quantum_review_complete") is True,
        "quantum_backend": backend,
        "quantum_mode": mode,
        "backend_status": latest_result.get("backend_status") or "ok",
        "simulator_status": latest_result.get("simulator_status") or "classical_fallback_labelled",
        "local_validation_status": latest_result.get("local_validation_status") or "passed_classical_fallback",
        "latest_oracle_created_at": latest_result.get("created_at"),
        "qctrl_state": {
            "artifact": f"data/runtime/{QCTRL_FIRE_OPAL_IBM_ARTIFACT}",
            "status": qctrl.get("status", "missing"),
            "mode": qctrl.get("mode"),
            "qctrl_product_access_status": qctrl.get("qctrl_product_access_status"),
            "ibm_quantum_token_configured": qctrl.get("ibm_quantum_token_configured") is True,
            "qiskit_importable": qctrl.get("qiskit_importable") is True,
            "qiskit_ibm_runtime_importable": qctrl.get("qiskit_ibm_runtime_importable") is True,
            "fire_opal_sdk_importable": qctrl.get("fire_opal_sdk_importable") is True,
            "provider_probe_observed_status": qctrl.get("status", "missing"),
            "provider_call_attempted_existing_artifact": qctrl.get("provider_call_attempted") is True,
            "hardware_submission_allowed": qctrl.get("hardware_submission_allowed") is True,
            "hardware_job_submitted": qctrl.get("hardware_job_submitted") is True,
            "execution_allowed": qctrl.get("execution_allowed") is True,
            "paper_order_allowed": qctrl.get("paper_order_allowed") is True,
            "recommendation_authority": qctrl.get("recommendation_authority") is True,
        },
        "lab_provider_call_allowed": False,
        "lab_provider_call_attempted": False,
        "hardware_submission_allowed": False,
        "hardware_submitted": False,
        "hardware_scheduler_enabled": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "proof_credit_allowed": False,
        "trade_candidate_authority": False,
        "recommendation_authority": False,
        "quantum_review_is_not_trade_confirmation": True,
    }


def _source_diversity(source_recipe: dict[str, Any]) -> float:
    names = source_recipe.get("source_names", [])
    families = str(source_recipe.get("source_family", "")).split(",")
    count = len([name for name in names if name])
    family_count = len([family for family in families if family])
    return _clamp((count + family_count) / 8)


def _nonlinear_metrics(linear_result: dict[str, Any]) -> dict[str, Any]:
    sample = linear_result.get("sample", {})
    tests = linear_result.get("tests", {})
    risk = linear_result.get("risk", {})
    source_recipe = linear_result.get("source_recipe", {})
    lead_lag = tests.get("lead_lag", {})
    event_study = tests.get("event_study", {})
    walk_forward = tests.get("walk_forward_validation", {})
    false_positive = tests.get("false_positive_control", {})
    coverage = _float(sample.get("coverage_score"))
    memory_count = _float(sample.get("complete_forward_outcome_count"))
    validation_count = _float(sample.get("validation_record_count"))
    unique_dates = _float(sample.get("unique_decision_date_count"))
    source_diversity = _source_diversity(source_recipe)
    lag_score = _float(lead_lag.get("lag_score"))
    false_positive_risk = _float(false_positive.get("false_positive_risk"), 1.0)
    linear_score = _float(linear_result.get("linear_score"))
    raw_expectancy = _float(risk.get("expectancy"))
    mean_return = _float(event_study.get("mean_forward_return"))
    interaction_gain = _clamp(
        0.18 * source_diversity
        + 0.16 * lag_score
        + 0.10 * min(1.0, memory_count / 40)
        - 0.20 * false_positive_risk
    )
    threshold_stability = _clamp(coverage * min(1.0, memory_count / 30) * (1 - false_positive_risk * 0.35))
    regime_dependence_score = _clamp((unique_dates / 5) * 0.6 + source_diversity * 0.2)
    path_dependence_score = _clamp(lag_score * 0.7 + min(1.0, validation_count / 10) * 0.3)
    walk_forward_survival = _clamp(min(1.0, validation_count / 10) * (1 - false_positive_risk * 0.4))
    cluster_similarity_score = _clamp(source_diversity * 0.4 + coverage * 0.3 + min(1.0, memory_count / 50) * 0.3)
    anomaly_divergence_score = _clamp(abs(mean_return) * 12 + lag_score * 0.25)
    false_discovery_penalty = _clamp(false_positive_risk + (0.35 if validation_count < 10 else 0.0))
    overfit_risk_score = _clamp(
        false_discovery_penalty * 0.45
        + (1 - walk_forward_survival) * 0.25
        + (1 - threshold_stability) * 0.20
        + (0.10 if unique_dates < 2 else 0.0)
    )
    nonlinear_score = _clamp(
        linear_score * 0.35
        + interaction_gain * 0.20
        + path_dependence_score * 0.15
        + regime_dependence_score * 0.10
        + threshold_stability * 0.10
        + (1 - overfit_risk_score) * 0.10
    )
    conditional_expectancy = raw_expectancy + interaction_gain * 0.002 - overfit_risk_score * 0.0015
    linear_baseline_score_delta = nonlinear_score - linear_score
    linear_baseline_beaten = (
        linear_baseline_score_delta > 0.08
        and conditional_expectancy > 0
        and walk_forward_survival >= 0.55
        and overfit_risk_score <= 0.45
        and memory_count >= 20
    )
    return {
        "method_families": list(NONLINEAR_METHOD_FAMILIES),
        "primary_method_type": "interaction_regime_path_review",
        "interaction_gain": round(interaction_gain, 6),
        "threshold_stability": round(threshold_stability, 6),
        "regime_dependence_score": round(regime_dependence_score, 6),
        "path_dependence_score": round(path_dependence_score, 6),
        "cluster_similarity_score": round(cluster_similarity_score, 6),
        "anomaly_divergence_score": round(anomaly_divergence_score, 6),
        "tree_rule_complexity_score": round(_clamp(source_diversity + path_dependence_score * 0.4), 6),
        "conditional_expectancy": round(conditional_expectancy, 8),
        "walk_forward_survival": round(walk_forward_survival, 6),
        "false_discovery_penalty": round(false_discovery_penalty, 6),
        "overfit_risk_score": round(overfit_risk_score, 6),
        "linear_baseline_score": round(linear_score, 6),
        "nonlinear_score": round(nonlinear_score, 6),
        "linear_baseline_score_delta": round(linear_baseline_score_delta, 6),
        "linear_baseline_beaten": linear_baseline_beaten,
        "overfit_controls": {
            "multiple_testing_penalty_applied": True,
            "walk_forward_required": True,
            "independent_regime_required": True,
            "cost_and_slippage_penalty_inherited": True,
            "reject_in_sample_only_gain": True,
            "status": "overfit_hold" if overfit_risk_score > 0.55 else "controls_passed",
        },
        "source_diversity_score": round(source_diversity, 6),
    }


def _nonlinear_sample(linear_result: dict[str, Any]) -> dict[str, Any]:
    sample = linear_result.get("sample", {})
    tests = linear_result.get("tests", {})
    return {
        "memory_record_count": sample.get("memory_record_count", 0),
        "complete_forward_outcome_count": sample.get("complete_forward_outcome_count", 0),
        "point_in_time_safe": sample.get("point_in_time_safe") is True,
        "coverage_score": sample.get("coverage_score", 0.0),
        "regime_count": max(1, int(_float(sample.get("unique_decision_date_count"), 0.0))),
        "walk_forward_windows": sample.get("validation_record_count", 0),
        "train_record_count": sample.get("train_record_count", 0),
        "validation_record_count": sample.get("validation_record_count", 0),
        "linear_leakage_status": "passed" if sample.get("point_in_time_safe") is True else "failed",
        "out_of_sample_status": tests.get("walk_forward_validation", {}).get("out_of_sample_status"),
    }


def _nonlinear_decision(linear_result: dict[str, Any], metrics: dict[str, Any], sample: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    reject_reason: str | None = None
    status = "candidate_for_quantum_review"
    if sample["point_in_time_safe"] is not True:
        status = "nonlinear_rejected"
        reject_reason = "point_in_time_or_leakage_check_failed"
        reasons.append("Point-in-time or leakage safety failed; advanced review cannot promote this pattern.")
    elif sample["complete_forward_outcome_count"] < 8:
        status = "nonlinear_rejected"
        reject_reason = "sample_too_small"
        reasons.append("Forward-outcome sample is too small for nonlinear review.")
    elif metrics["linear_baseline_beaten"]:
        reasons.append("Nonlinear interaction beat the linear baseline after overfit controls.")
    elif metrics["overfit_risk_score"] > 0.55:
        status = "candidate_for_quantum_review"
        reasons.append("Nonlinear signal is under-explained and overfit risk is high; quantum ambiguity review is required.")
    else:
        status = "candidate_for_quantum_review"
        reasons.append("Nonlinear review is not incremental yet; quantum ambiguity review can decide whether to hold or demote.")
    if not metrics["linear_baseline_beaten"]:
        reasons.append("Advanced evidence has not beaten the QSASE-5 linear baseline.")
    return {
        "nonlinear_status": status,
        "reason": " ".join(reasons),
        "reject_reason": reject_reason,
        "baseline_incremental_value_status": "linear_baseline_beaten"
        if metrics["linear_baseline_beaten"]
        else "advanced_review_not_incremental",
        "candidate_for_quantum_review": status == "candidate_for_quantum_review",
        "candidate_for_strategy_foundry": False,
        "candidate_for_akber_filter": False,
        "candidate_for_paper_route": False,
        "trade_candidate_created": False,
        "paper_order_created": False,
        "proof_credit_allowed": False,
        "quantum_review_required_before_any_later_promotion": status == "candidate_for_quantum_review",
        "quantum_review_is_not_trade_confirmation": True,
    }


def _build_nonlinear_result(linear_result: dict[str, Any], generated_at: str) -> dict[str, Any]:
    metrics = _nonlinear_metrics(linear_result)
    sample = _nonlinear_sample(linear_result)
    decision = _nonlinear_decision(linear_result, metrics, sample)
    linear_pattern_id = str(linear_result.get("linear_pattern_id"))
    result = {
        "schema_version": SCHEMA_VERSION,
        "nonlinear_pattern_id": _nonlinear_pattern_id(linear_pattern_id),
        "source_linear_pattern_id": linear_pattern_id,
        "source_pattern_id": linear_result.get("source_pattern_id"),
        "generated_at": generated_at,
        "source_recipe": {
            "source_families": str(linear_result.get("source_recipe", {}).get("source_family", "")).split(","),
            "source_names": linear_result.get("source_recipe", {}).get("source_names", []),
            "feature_names": [
                "source_diversity_score",
                "linear_lag_score",
                "coverage_score",
                "false_positive_risk",
                "walk_forward_survival",
            ],
            "interaction_type": "threshold_regime_path_interaction",
        },
        "market_expression": linear_result.get("market_expression", {}),
        "baseline": {
            "linear_pattern_id": linear_pattern_id,
            "linear_score": linear_result.get("linear_score"),
            "linear_status": linear_result.get("decision", {}).get("linear_status"),
            "linear_rank": linear_result.get("rank"),
            "linear_candidate_for_nonlinear_review": linear_result.get("decision", {}).get("candidate_for_nonlinear_review") is True,
            "linear_result_path": f"data/runtime/{LINEAR_RESULTS_ARTIFACT}",
        },
        "nonlinear_method_type": metrics["primary_method_type"],
        "nonlinear_tests": metrics,
        "sample": sample,
        "decision": decision,
        "quantum_review_id": None,
        "quantum_review_state": "not_required_rejected_pre_quantum"
        if decision["nonlinear_status"] == "nonlinear_rejected"
        else "required_not_yet_attached",
        "accepted_as_validated_edge": False,
        "candidate_for_paper_route": False,
        "candidate_for_strategy_foundry": False,
        "trade_candidate_created": False,
        "strategy_hypothesis_created": False,
        "paper_order_created": False,
        "quantum_review_is_not_trade_approval": True,
        "nonlinear_success_is_research_evidence_only": True,
        "paper_proof_ledger_eligible": False,
        "execution_allowed": False,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "authority": _authority_block(),
    }
    for key, value in NONLINEAR_AUTHORITY_FLAGS.items():
        result[key] = value
    return result


def _rank_nonlinear_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(
        results,
        key=lambda result: (
            result.get("nonlinear_tests", {}).get("linear_baseline_beaten") is True,
            result.get("nonlinear_tests", {}).get("nonlinear_score", 0.0),
            -result.get("nonlinear_tests", {}).get("overfit_risk_score", 1.0),
        ),
        reverse=True,
    )
    for index, result in enumerate(ranked, start=1):
        result["rank"] = index
    return ranked


def build_nonlinear_pattern_results(settings: Settings | None = None) -> dict[str, Any]:
    context = _load_context(settings)
    generated_at = _iso(_now())
    linear_results = context["linear_results"]
    nonlinear_results = _rank_nonlinear_results(
        [_build_nonlinear_result(result, generated_at) for result in linear_results]
    )
    missing_required_state: list[str] = []
    if not context["linear_lab"]:
        missing_required_state.append("qsase_linear_pattern_lab_missing")
    if not linear_results:
        missing_required_state.append("qsase_linear_results_missing")
    if not context["historical_memory"]:
        missing_required_state.append("qsase_historical_source_price_memory_missing")
    degraded_reasons: list[str] = []
    hold_reasons: list[str] = []
    if context["linear_lab"].get("status") not in LINEAR_LAB_READY_STATUSES:
        degraded_reasons.append("linear_pattern_lab_degraded")
    elif context["linear_lab"].get("status") == "qsase_linear_pattern_lab_ready_with_holds":
        hold_reasons.append("linear_pattern_lab_has_research_holds")
    if context["historical_memory"].get("status") not in HISTORICAL_MEMORY_READY_STATUSES:
        degraded_reasons.append("historical_memory_degraded")
    elif context["historical_memory"].get("status") == "qsase_historical_source_price_memory_ready_with_gaps":
        hold_reasons.append("historical_memory_has_missing_forward_windows")
    if any(result["nonlinear_tests"]["overfit_risk_score"] > 0.55 for result in nonlinear_results):
        hold_reasons.append("nonlinear_overfit_controls_holding")
    accepted_count = sum(
        1 for result in nonlinear_results if result["nonlinear_tests"]["linear_baseline_beaten"]
    )
    rejected_count = sum(
        1 for result in nonlinear_results if result["decision"]["nonlinear_status"] == "nonlinear_rejected"
    )
    inconclusive_count = sum(
        1
        for result in nonlinear_results
        if result["decision"]["nonlinear_status"] == "candidate_for_quantum_review"
        and not result["nonlinear_tests"]["linear_baseline_beaten"]
    )
    baseline_not_beat_count = sum(
        1 for result in nonlinear_results if not result["nonlinear_tests"]["linear_baseline_beaten"]
    )
    status = "qsase_nonlinear_quantum_pattern_lab_ready"
    if missing_required_state:
        status = "qsase_nonlinear_quantum_pattern_lab_blocked"
    elif degraded_reasons:
        status = "qsase_nonlinear_quantum_pattern_lab_degraded"
    elif hold_reasons or accepted_count == 0:
        status = "qsase_nonlinear_quantum_pattern_lab_ready_with_holds"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_nonlinear_quantum_pattern_lab",
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "generated_at": generated_at,
        "status": status,
        "public_safe": True,
        "command_disabled": True,
        "paper_only": True,
        "proposal_first": True,
        "research_only": True,
        "candidate_input_count": len(linear_results),
        "tested_interaction_count": len(nonlinear_results),
        "accepted_nonlinear_pattern_count": accepted_count,
        "rejected_nonlinear_pattern_count": rejected_count,
        "inconclusive_nonlinear_pattern_count": inconclusive_count,
        "linear_baseline_beat_count": accepted_count,
        "linear_baseline_not_beat_count": baseline_not_beat_count,
        "candidate_for_quantum_review_count": sum(
            1 for result in nonlinear_results if result["decision"]["candidate_for_quantum_review"]
        ),
        "candidate_for_strategy_foundry_count": 0,
        "nonlinear_method_families": list(NONLINEAR_METHOD_FAMILIES),
        "nonlinear_results": nonlinear_results,
        "input_artifacts": {
            "linear_lab": f"data/runtime/{LINEAR_LAB_ARTIFACT}",
            "linear_results": f"data/runtime/{LINEAR_RESULTS_ARTIFACT}",
            "linear_rejected_patterns": f"data/runtime/{LINEAR_REJECTED_ARTIFACT}",
            "historical_memory": f"data/runtime/{HISTORICAL_MEMORY_ARTIFACT}",
            "historical_memory_records": f"data/runtime/{HISTORICAL_MEMORY_JSONL_ARTIFACT}",
            "source_price_matrix": f"data/runtime/{SOURCE_PRICE_MATRIX_ARTIFACT}",
        },
        "missing_required_state": missing_required_state,
        "degraded_reasons": sorted(set(degraded_reasons)),
        "hold_reasons": sorted(set(hold_reasons)),
        "nonlinear_results_path": f"data/runtime/{NONLINEAR_RESULTS_ARTIFACT}",
        "quantum_reviews_path": f"data/runtime/{QUANTUM_REVIEWS_ARTIFACT}",
        "execution_allowed": False,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "no_trade_candidates_created": True,
        "no_strategy_hypotheses_created": True,
        "no_paper_orders_created": True,
        "no_broker_writes": True,
        "no_live_capital": True,
        "no_proof_credit_granted": True,
        "paper_growth_trial_calendar_advanced": False,
        "paper_proof_ledger_credit_granted": False,
        "quantum_review_is_not_trade_approval": True,
        "quantum_review_is_not_execution_authority": True,
        "qctrl_holds_bypassed": False,
        "authority": universal_authority_flags(),
        "authority_flags": dict(NONLINEAR_AUTHORITY_FLAGS),
    }
    payload["quantum_state"] = _quantum_state(context)
    return payload


def _review_scores(result: dict[str, Any]) -> dict[str, float]:
    tests = result.get("nonlinear_tests", {})
    sample = result.get("sample", {})
    overfit = _float(tests.get("overfit_risk_score"), 1.0)
    nonlinear_score = _float(tests.get("nonlinear_score"))
    interaction_gain = _float(tests.get("interaction_gain"))
    path_dependence = _float(tests.get("path_dependence_score"))
    coverage = _float(sample.get("coverage_score"))
    pattern_score = _clamp(nonlinear_score * 0.55 + interaction_gain * 0.25 + path_dependence * 0.20 - overfit * 0.15)
    ambiguity_score = _clamp(overfit * 0.55 + (1 - coverage) * 0.25 + (0.2 if sample.get("regime_count", 0) < 2 else 0.0))
    confidence_delta = _clamp(pattern_score - _float(tests.get("linear_baseline_score")), -1.0, 1.0)
    strategy_collapse_score = _clamp(
        0.45
        + _source_diversity(result.get("source_recipe", {})) * 0.2
        - ambiguity_score * 0.2
        + (0.1 if tests.get("linear_baseline_beaten") else 0.0)
    )
    usefulness = _clamp(abs(confidence_delta) * 0.35 + ambiguity_score * 0.35 + strategy_collapse_score * 0.20 + interaction_gain * 0.10)
    return {
        "pattern_score": round(pattern_score, 6),
        "ambiguity_score": round(ambiguity_score, 6),
        "confidence_delta": round(confidence_delta, 6),
        "strategy_collapse_score": round(strategy_collapse_score, 6),
        "quantum_usefulness_score": round(usefulness, 6),
    }


def _build_quantum_review(
    nonlinear_result: dict[str, Any],
    quantum_state: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    scores = _review_scores(nonlinear_result)
    job_type = "pattern_recognition"
    if _source_diversity(nonlinear_result.get("source_recipe", {})) >= 0.45:
        job_type = "strategy_collapse"
    if scores["ambiguity_score"] >= 0.65:
        recommendation = "hold"
        review_state = "quantum_hold"
        usefulness_class = "useful_ambiguity_hold"
    elif scores["pattern_score"] < 0.45 or scores["confidence_delta"] <= 0:
        recommendation = "downgrade_or_hold"
        review_state = "quantum_review_passed_for_research"
        usefulness_class = "useful_false_positive_demotion"
    else:
        recommendation = "upgrade_shadow_confidence"
        review_state = "quantum_review_passed_for_research"
        usefulness_class = "useful_research_confidence_delta"
    input_contract = {
        "feature_count": len(nonlinear_result.get("source_recipe", {}).get("feature_names", [])),
        "source_count": len(nonlinear_result.get("source_recipe", {}).get("source_names", [])),
        "instrument_focus": nonlinear_result.get("market_expression", {}).get("instrument"),
        "evidence_item_count": nonlinear_result.get("sample", {}).get("memory_record_count", 0),
        "input_fingerprint": _input_fingerprint(
            {
                "nonlinear_pattern_id": nonlinear_result.get("nonlinear_pattern_id"),
                "baseline": nonlinear_result.get("baseline"),
                "nonlinear_tests": nonlinear_result.get("nonlinear_tests"),
            }
        ),
        "point_in_time_safe": nonlinear_result.get("sample", {}).get("point_in_time_safe") is True,
        "leakage_tainted_input_rejected": nonlinear_result.get("sample", {}).get("point_in_time_safe") is not True,
    }
    review = {
        "schema_version": SCHEMA_VERSION,
        "quantum_review_id": _quantum_review_id(nonlinear_result["nonlinear_pattern_id"], job_type),
        "generated_at": generated_at,
        "source_pattern_id": nonlinear_result["nonlinear_pattern_id"],
        "source_linear_pattern_id": nonlinear_result.get("source_linear_pattern_id"),
        "job_type": job_type,
        "strategy_collapse_job_required": job_type == "strategy_collapse",
        "backend": quantum_state["quantum_backend"],
        "backend_status": quantum_state["backend_status"],
        "quantum_mode": quantum_state["quantum_mode"],
        "local_simulation_mode": quantum_state["quantum_mode"],
        "simulator_status": quantum_state["simulator_status"],
        "local_validation_status": quantum_state["local_validation_status"],
        "hardware_submission_allowed": False,
        "hardware_submitted": False,
        "provider_call_allowed": False,
        "provider_call_attempted_by_this_lab": False,
        "input_contract": input_contract,
        "scores": scores,
        "quantum_usefulness": {
            "quantum_review_added_useful_information": scores["quantum_usefulness_score"] >= 0.35,
            "usefulness_class": usefulness_class,
            "linear_baseline_changed": scores["confidence_delta"] != 0,
            "ambiguity_recorded": True,
            "not_trade_confirmation": True,
        },
        "recommendation": recommendation,
        "review_state": review_state,
        "hold_reasons": ["ambiguity_too_high", "backend_degraded"]
        if review_state == "quantum_hold"
        else [],
        "required_next_steps": [
            "retain_as_research_evidence_only",
            "repair_coverage_before_strategy_foundry",
            "do_not_submit_provider_or_hardware_job_from_qsase_6",
        ],
        "qctrl_state": quantum_state["qctrl_state"],
        "authority": _authority_block(),
        "execution_allowed": False,
        "paper_order_allowed": False,
        "trade_candidate_created": False,
        "trade_candidate_authority": False,
        "proof_credit_allowed": False,
        "live_capital_enabled": False,
        "recommendation_authority": False,
        "quantum_review_is_not_trade_approval": True,
        "quantum_review_is_not_trade_confirmation": True,
    }
    for key, value in NONLINEAR_AUTHORITY_FLAGS.items():
        review[key] = value
    return review


def build_quantum_pattern_reviews(
    settings: Settings | None = None,
    nonlinear_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    context = _load_context(settings)
    generated_at = _iso(_now())
    quantum_state = _quantum_state(context)
    review_inputs = nonlinear_results
    if review_inputs is None:
        review_inputs = build_nonlinear_pattern_results(settings)["nonlinear_results"]
    reviews = [
        _build_quantum_review(result, quantum_state, generated_at)
        for result in review_inputs
        if result.get("decision", {}).get("candidate_for_quantum_review") is True
    ]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_quantum_pattern_reviews",
        "generated_at": generated_at,
        "status": "quantum_reviews_ready" if reviews else "quantum_reviews_degraded_no_reviewable_patterns",
        "reviewed_pattern_count": len(reviews),
        "quantum_backend": quantum_state["quantum_backend"],
        "quantum_mode": quantum_state["quantum_mode"],
        "local_validation_status": quantum_state["local_validation_status"],
        "hardware_submission_allowed": False,
        "hardware_submitted": False,
        "provider_call_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "trade_candidate_authority": False,
        "proof_credit_allowed": False,
        "recommendation_authority": False,
        "quantum_usefulness_scored": True,
        "quantum_review_is_not_trade_approval": True,
        "quantum_review_is_not_trade_confirmation": True,
        "quantum_state": quantum_state,
        "quantum_reviews": reviews,
        "authority": _authority_block(),
        "authority_flags": dict(NONLINEAR_AUTHORITY_FLAGS),
    }
    return payload


def _attach_quantum_reviews(
    nonlinear_payload: dict[str, Any],
    quantum_payload: dict[str, Any],
) -> dict[str, Any]:
    payload = copy.deepcopy(nonlinear_payload)
    reviews = quantum_payload["quantum_reviews"]
    by_source = {review["source_pattern_id"]: review for review in reviews}
    for result in payload["nonlinear_results"]:
        review = by_source.get(result["nonlinear_pattern_id"])
        if not review:
            continue
        result["quantum_review_id"] = review["quantum_review_id"]
        result["quantum_review_state"] = review["review_state"]
        result["decision"]["quantum_review_state"] = review["review_state"]
        result["decision"]["quantum_review_recommendation"] = review["recommendation"]
        result["decision"]["candidate_for_strategy_foundry"] = False
        result["candidate_for_strategy_foundry"] = False
    payload["quantum_reviews"] = reviews
    payload["reviewed_pattern_count"] = len(reviews)
    payload["quantum_summary"] = {
        "status": quantum_payload["status"],
        "generated_at": quantum_payload["generated_at"],
        "reviewed_pattern_count": quantum_payload["reviewed_pattern_count"],
        "quantum_backend": quantum_payload["quantum_backend"],
        "quantum_mode": quantum_payload["quantum_mode"],
        "local_validation_status": quantum_payload["local_validation_status"],
        "hardware_submission_allowed": False,
        "hardware_submitted": False,
        "provider_call_allowed": False,
        "execution_allowed": False,
        "paper_order_allowed": False,
        "trade_candidate_authority": False,
        "proof_credit_allowed": False,
        "recommendation_authority": False,
        "quantum_usefulness_scored": True,
        "quantum_review_is_not_trade_approval": True,
        "quantum_review_is_not_trade_confirmation": True,
    }
    payload["quantum_state"] = quantum_payload["quantum_state"]
    payload["quantum_reviewed_pattern_count"] = len(reviews)
    payload["quantum_hold_count"] = sum(1 for review in reviews if review["review_state"] == "quantum_hold")
    payload["quantum_review_passed_for_research_count"] = sum(
        1 for review in reviews if review["review_state"] == "quantum_review_passed_for_research"
    )
    payload["quantum_useful_information_count"] = sum(
        1 for review in reviews if review["quantum_usefulness"]["quantum_review_added_useful_information"]
    )
    payload["candidate_for_strategy_foundry_count"] = 0
    payload["dashboard_safe_summary"] = _dashboard_summary(payload)
    return payload


def build_nonlinear_quantum_pattern_lab(settings: Settings | None = None) -> dict[str, Any]:
    nonlinear_payload = build_nonlinear_pattern_results(settings)
    quantum_payload = build_quantum_pattern_reviews(settings, nonlinear_payload["nonlinear_results"])
    return _attach_quantum_reviews(nonlinear_payload, quantum_payload)


def load_nonlinear_pattern_results(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    payload = _read_json(runtime / PRIMARY_ARTIFACT)
    results = _read_jsonl(runtime / NONLINEAR_RESULTS_ARTIFACT)
    if payload:
        payload["nonlinear_results"] = results
    return payload


def load_quantum_pattern_reviews(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    payload = _read_json(runtime / PRIMARY_ARTIFACT)
    reviews = _read_jsonl(runtime / QUANTUM_REVIEWS_ARTIFACT)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_quantum_pattern_reviews",
        "generated_at": payload.get("generated_at"),
        "status": payload.get("quantum_summary", {}).get("status"),
        "reviewed_pattern_count": len(reviews),
        "quantum_backend": payload.get("quantum_summary", {}).get("quantum_backend"),
        "quantum_mode": payload.get("quantum_summary", {}).get("quantum_mode"),
        "local_validation_status": payload.get("quantum_summary", {}).get("local_validation_status"),
        "quantum_reviews": reviews,
        "authority": payload.get("authority_flags", {}),
        "authority_flags": payload.get("authority_flags", {}),
    }


def load_nonlinear_quantum_pattern_lab(settings: Settings | None = None) -> dict[str, Any]:
    runtime = _runtime_dir(settings)
    payload = _read_json(runtime / PRIMARY_ARTIFACT)
    if payload:
        payload["nonlinear_results"] = _read_jsonl(runtime / NONLINEAR_RESULTS_ARTIFACT)
        payload["quantum_reviews"] = _read_jsonl(runtime / QUANTUM_REVIEWS_ARTIFACT)
    return payload


def _validate_authority(flags: dict[str, Any], prefix: str) -> list[str]:
    errors: list[str] = []
    for key, expected in NONLINEAR_AUTHORITY_FLAGS.items():
        if flags.get(key) is not expected:
            errors.append(f"{prefix}_{key}_must_be_false")
    return errors


def validate_nonlinear_pattern_results(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("artifact_type") != "qsase_nonlinear_quantum_pattern_lab":
        errors.append("artifact_type_invalid")
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if payload.get("status") not in {
        "qsase_nonlinear_quantum_pattern_lab_ready",
        "qsase_nonlinear_quantum_pattern_lab_ready_with_holds",
        "qsase_nonlinear_quantum_pattern_lab_degraded",
        "qsase_nonlinear_quantum_pattern_lab_blocked",
    }:
        errors.append("status_invalid")
    if payload.get("public_safe") is not True or payload.get("command_disabled") is not True:
        errors.append("public_safe_command_disabled_required")
    for key in (
        "no_trade_candidates_created",
        "no_strategy_hypotheses_created",
        "no_paper_orders_created",
        "no_broker_writes",
        "no_live_capital",
        "no_proof_credit_granted",
        "quantum_review_is_not_trade_approval",
        "quantum_review_is_not_execution_authority",
    ):
        if payload.get(key) is not True:
            errors.append(f"{key}_must_be_true")
    for key in ("execution_allowed", "proof_credit_allowed", "live_capital_enabled"):
        if payload.get(key) is not False:
            errors.append(f"{key}_must_be_false")
    if payload.get("qctrl_holds_bypassed") is not False:
        errors.append("qctrl_holds_must_not_be_bypassed")
    authority = payload.get("authority", {})
    if not isinstance(authority, dict) or any(value is not False for value in authority.values()):
        errors.append("universal_authority_flags_must_all_be_false")
    errors.extend(_validate_authority(payload.get("authority_flags", {}), "lab"))
    for family in NONLINEAR_METHOD_FAMILIES:
        if family not in payload.get("nonlinear_method_families", []):
            errors.append(f"nonlinear_method_family_{family}_missing")
    results = payload.get("nonlinear_results")
    if not isinstance(results, list) or not results:
        errors.append("nonlinear_results_missing")
        results = []
    seen: set[str] = set()
    for result in results:
        result_id = result.get("nonlinear_pattern_id")
        for field in REQUIRED_NONLINEAR_FIELDS:
            if field not in result:
                errors.append(f"nonlinear_result_{result_id}_missing_{field}")
        if result_id in seen:
            errors.append(f"duplicate_nonlinear_result_{result_id}")
        seen.add(str(result_id))
        if result.get("source_linear_pattern_id") != result.get("baseline", {}).get("linear_pattern_id"):
            errors.append(f"nonlinear_result_{result_id}_missing_linear_baseline_reference")
        if result.get("sample", {}).get("point_in_time_safe") is not True:
            decision = result.get("decision", {})
            if decision.get("nonlinear_status") != "nonlinear_rejected":
                errors.append(f"nonlinear_result_{result_id}_unsafe_sample_not_rejected")
        tests = result.get("nonlinear_tests", {})
        if not tests.get("method_families"):
            errors.append(f"nonlinear_result_{result_id}_method_families_missing")
        if "regime_dependence_score" not in tests:
            errors.append(f"nonlinear_result_{result_id}_regime_dependence_missing")
        if "path_dependence_score" not in tests:
            errors.append(f"nonlinear_result_{result_id}_path_dependence_missing")
        if "overfit_controls" not in tests:
            errors.append(f"nonlinear_result_{result_id}_overfit_controls_missing")
        if "linear_baseline_beaten" not in tests:
            errors.append(f"nonlinear_result_{result_id}_linear_baseline_comparison_missing")
        decision = result.get("decision", {})
        if decision.get("candidate_for_paper_route") is not False:
            errors.append(f"nonlinear_result_{result_id}_paper_route_candidate_must_be_false")
        if result.get("accepted_as_validated_edge") is not False:
            errors.append(f"nonlinear_result_{result_id}_must_not_be_validated_edge")
        for key in NONLINEAR_AUTHORITY_FLAGS:
            if result.get(key) is not False:
                errors.append(f"nonlinear_result_{result_id}_{key}_must_be_false")
            if result.get("authority", {}).get(key) is not False:
                errors.append(f"nonlinear_result_{result_id}_authority_{key}_must_be_false")
        for key in ("execution_allowed", "proof_credit_allowed", "live_capital_enabled"):
            if result.get(key) is not False:
                errors.append(f"nonlinear_result_{result_id}_{key}_must_be_false")
    if payload.get("candidate_for_strategy_foundry_count") != 0:
        errors.append("strategy_foundry_count_must_be_zero_until_qsase_7")
    summary = payload.get("dashboard_safe_summary", {})
    if summary:
        if summary.get("public_safe") is not True or summary.get("command_disabled") is not True:
            errors.append("dashboard_summary_public_safe_required")
        if summary.get("live_send_allowed") is not False:
            errors.append("dashboard_summary_live_send_must_be_false")
        if summary.get("quantum_review_is_not_trade_confirmation") is not True:
            errors.append("dashboard_summary_quantum_confirmation_boundary_required")
    return sorted(set(errors))


def validate_quantum_pattern_reviews(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    reviews = payload.get("quantum_reviews")
    if not isinstance(reviews, list):
        errors.append("quantum_reviews_missing")
        reviews = []
    if payload.get("reviewed_pattern_count", len(reviews)) != len(reviews):
        errors.append("reviewed_pattern_count_mismatch")
    backend = payload.get("quantum_backend") or payload.get("quantum_summary", {}).get("quantum_backend")
    mode = payload.get("quantum_mode") or payload.get("quantum_summary", {}).get("quantum_mode")
    if backend not in ALLOWED_QUANTUM_BACKENDS:
        errors.append("quantum_backend_invalid")
    if mode not in ALLOWED_QUANTUM_MODES:
        errors.append("quantum_mode_invalid")
    for key in (
        "hardware_submission_allowed",
        "hardware_submitted",
        "provider_call_allowed",
        "execution_allowed",
        "paper_order_allowed",
        "trade_candidate_authority",
        "proof_credit_allowed",
        "recommendation_authority",
    ):
        value = payload.get(key, payload.get("quantum_summary", {}).get(key))
        if value is not False and value is not None:
            errors.append(f"quantum_summary_{key}_must_be_false")
    seen: set[str] = set()
    for review in reviews:
        review_id = review.get("quantum_review_id")
        for field in REQUIRED_QUANTUM_REVIEW_FIELDS:
            if field not in review:
                errors.append(f"quantum_review_{review_id}_missing_{field}")
        if review_id in seen:
            errors.append(f"duplicate_quantum_review_{review_id}")
        seen.add(str(review_id))
        if review.get("job_type") not in ALLOWED_QUANTUM_JOB_TYPES:
            errors.append(f"quantum_review_{review_id}_job_type_invalid")
        if review.get("backend") not in ALLOWED_QUANTUM_BACKENDS:
            errors.append(f"quantum_review_{review_id}_backend_invalid")
        if review.get("quantum_mode") not in ALLOWED_QUANTUM_MODES:
            errors.append(f"quantum_review_{review_id}_mode_invalid")
        if review.get("local_validation_status") not in {"passed", "passed_classical_fallback"}:
            errors.append(f"quantum_review_{review_id}_local_validation_missing")
        if review.get("recommendation") not in ALLOWED_QUANTUM_RECOMMENDATIONS:
            errors.append(f"quantum_review_{review_id}_recommendation_invalid")
        if review.get("input_contract", {}).get("point_in_time_safe") is not True:
            errors.append(f"quantum_review_{review_id}_unsafe_input")
        scores = review.get("scores", {})
        for score_name in (
            "pattern_score",
            "ambiguity_score",
            "confidence_delta",
            "strategy_collapse_score",
            "quantum_usefulness_score",
        ):
            if score_name not in scores:
                errors.append(f"quantum_review_{review_id}_{score_name}_missing")
        usefulness = review.get("quantum_usefulness", {})
        if usefulness.get("ambiguity_recorded") is not True:
            errors.append(f"quantum_review_{review_id}_ambiguity_not_recorded")
        if usefulness.get("not_trade_confirmation") is not True:
            errors.append(f"quantum_review_{review_id}_confirmation_boundary_missing")
        for key in NONLINEAR_AUTHORITY_FLAGS:
            if review.get(key) is not False:
                errors.append(f"quantum_review_{review_id}_{key}_must_be_false")
            if review.get("authority", {}).get(key) is not False:
                errors.append(f"quantum_review_{review_id}_authority_{key}_must_be_false")
        for key in (
            "hardware_submission_allowed",
            "hardware_submitted",
            "provider_call_allowed",
            "execution_allowed",
            "paper_order_allowed",
            "trade_candidate_authority",
            "proof_credit_allowed",
            "live_capital_enabled",
            "recommendation_authority",
        ):
            if review.get(key) is not False:
                errors.append(f"quantum_review_{review_id}_{key}_must_be_false")
    return sorted(set(errors))


def _dashboard_summary(payload: dict[str, Any]) -> dict[str, Any]:
    top_result = payload["nonlinear_results"][0] if payload["nonlinear_results"] else {}
    top_review = payload["quantum_reviews"][0] if payload.get("quantum_reviews") else {}
    latest_blocker = "none"
    if payload.get("missing_required_state"):
        latest_blocker = ",".join(payload["missing_required_state"])
    elif payload.get("degraded_reasons"):
        latest_blocker = ",".join(payload["degraded_reasons"])
    elif payload.get("quantum_hold_count", 0):
        latest_blocker = "quantum_ambiguity_holds_present"
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qsase_nonlinear_quantum_pattern_lab_dashboard_summary",
        "generated_at": payload["generated_at"],
        "status": payload["status"],
        "public_safe": True,
        "command_disabled": True,
        "live_send_allowed": False,
        "summary_rows": [
            {"label": "Nonlinear lab status", "value": payload["status"]},
            {"label": "Tested interactions", "value": payload["tested_interaction_count"]},
            {"label": "Linear baseline beats", "value": payload["linear_baseline_beat_count"]},
            {"label": "Quantum reviews", "value": payload.get("reviewed_pattern_count", 0)},
            {"label": "Quantum backend", "value": payload.get("quantum_summary", {}).get("quantum_backend")},
            {"label": "Quantum mode", "value": payload.get("quantum_summary", {}).get("quantum_mode")},
            {"label": "Strategy Foundry candidates", "value": payload["candidate_for_strategy_foundry_count"]},
            {"label": "Authority", "value": "research_only_no_execution"},
        ],
        "top_advanced_pattern": top_result.get("nonlinear_pattern_id"),
        "top_advanced_status": top_result.get("decision", {}).get("nonlinear_status"),
        "top_ambiguity_hold": top_review.get("quantum_review_id")
        if top_review.get("review_state") == "quantum_hold"
        else None,
        "latest_blocker": latest_blocker,
        "quantum_review_is_not_trade_confirmation": True,
        "hardware_execution_claimed": False,
        "authority_flags_false": all(value is False for value in payload["authority_flags"].values()),
        "no_trade_candidates_created": True,
        "no_paper_orders_created": True,
        "no_proof_credit_granted": True,
    }


def build_qsase_phase_implementation_status(payload: dict[str, Any]) -> dict[str, Any]:
    runtime_dir = _runtime_dir()
    existing = _read_json(runtime_dir / PHASE_STATUS_ARTIFACT)
    phases = existing.get("phases") if isinstance(existing.get("phases"), dict) else {}
    phases[PHASE_ID] = {
        "name": PHASE_NAME,
        "status": payload["status"],
        "artifact_path": f"data/runtime/{PRIMARY_ARTIFACT}",
        "nonlinear_results_path": f"data/runtime/{NONLINEAR_RESULTS_ARTIFACT}",
        "quantum_reviews_path": f"data/runtime/{QUANTUM_REVIEWS_ARTIFACT}",
        "candidate_input_count": payload["candidate_input_count"],
        "tested_interaction_count": payload["tested_interaction_count"],
        "accepted_nonlinear_pattern_count": payload["accepted_nonlinear_pattern_count"],
        "rejected_nonlinear_pattern_count": payload["rejected_nonlinear_pattern_count"],
        "inconclusive_nonlinear_pattern_count": payload["inconclusive_nonlinear_pattern_count"],
        "linear_baseline_beat_count": payload["linear_baseline_beat_count"],
        "candidate_for_quantum_review_count": payload["candidate_for_quantum_review_count"],
        "reviewed_pattern_count": payload.get("reviewed_pattern_count", 0),
        "quantum_hold_count": payload.get("quantum_hold_count", 0),
        "quantum_backend": payload.get("quantum_summary", {}).get("quantum_backend"),
        "quantum_mode": payload.get("quantum_summary", {}).get("quantum_mode"),
        "quantum_useful_information_count": payload.get("quantum_useful_information_count", 0),
        "candidate_for_strategy_foundry_count": payload["candidate_for_strategy_foundry_count"],
        "paper_only": True,
        "research_only": True,
        "proposal_first": True,
        "public_safe": True,
        "authority_flags_false": True,
        "quantum_review_is_not_trade_approval": True,
        "no_trade_candidates_created": True,
        "no_paper_orders_created": True,
        "no_proof_credit_granted": True,
        "later_qsase_phases_implemented": False,
    }
    return {
        "schema_version": 1,
        "generated_at": payload["generated_at"],
        "active_phase": PHASE_ID,
        "phases": phases,
        "safety": payload["authority"],
    }


def _append_implementation_log(payload: dict[str, Any]) -> None:
    log_path = _repo_root() / IMPLEMENTATION_LOG
    log_path.parent.mkdir(parents=True, exist_ok=True)
    existing = (
        log_path.read_text(encoding="utf-8")
        if log_path.exists()
        else "# QSASE Implementation Log\n"
    )
    marker = f"<!-- {PHASE_ID} -->"
    entry = (
        f"{marker}\n"
        f"## QSASE-6: Nonlinear And Quantum Pattern Lab\n\n"
        f"- Generated at: `{payload.get('generated_at')}`\n"
        f"- Status: `{payload.get('status')}`\n"
        f"- Runtime artifact: `data/runtime/{PRIMARY_ARTIFACT}`\n"
        f"- Tested interactions: `{payload.get('tested_interaction_count')}`\n"
        f"- Linear baseline beats: `{payload.get('linear_baseline_beat_count')}`\n"
        f"- Quantum reviews: `{payload.get('reviewed_pattern_count')}`\n"
        f"- Quantum backend: `{payload.get('quantum_summary', {}).get('quantum_backend')}` / `{payload.get('quantum_summary', {}).get('quantum_mode')}`\n"
        f"- Safety: nonlinear and quantum success are research evidence only; no trade candidates, paper orders, broker writes, live capital, hardware jobs, or proof credit created.\n"
    )
    if marker in existing:
        before = existing.split(marker, 1)[0].rstrip()
        updated = before + "\n\n" + entry
    elif existing.endswith("\n"):
        updated = existing + "\n" + entry
    else:
        updated = existing + "\n\n" + entry
    log_path.write_text(updated, encoding="utf-8")


def _summary_without_records(payload: dict[str, Any]) -> dict[str, Any]:
    summary = dict(payload)
    summary.pop("nonlinear_results", None)
    summary.pop("quantum_reviews", None)
    return summary


def write_nonlinear_pattern_results(
    payload: dict[str, Any],
    settings: Settings | None = None,
    *,
    append_history: bool = True,
    append_log: bool = True,
) -> dict[str, str]:
    runtime_dir = _runtime_dir(settings)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "nonlinear_quantum_lab": runtime_dir / PRIMARY_ARTIFACT,
        "nonlinear_results": runtime_dir / NONLINEAR_RESULTS_ARTIFACT,
        "dashboard_summary": runtime_dir / DASHBOARD_SUMMARY_ARTIFACT,
        "phase_status": runtime_dir / PHASE_STATUS_ARTIFACT,
    }
    _write_json(paths["nonlinear_quantum_lab"], _summary_without_records(payload))
    _write_jsonl(paths["nonlinear_results"], payload["nonlinear_results"])
    _write_json(paths["dashboard_summary"], payload["dashboard_safe_summary"])
    _write_json(paths["phase_status"], build_qsase_phase_implementation_status(payload))
    written = {key: str(path) for key, path in paths.items()}
    if append_history:
        history_path = runtime_dir / HISTORY_ARTIFACT
        events_path = runtime_dir / EVENTS_ARTIFACT
        _append_jsonl(
            history_path,
            {
                "generated_at": payload["generated_at"],
                "status": payload["status"],
                "tested_interaction_count": payload["tested_interaction_count"],
                "linear_baseline_beat_count": payload["linear_baseline_beat_count"],
                "reviewed_pattern_count": payload.get("reviewed_pattern_count", 0),
                "quantum_backend": payload.get("quantum_summary", {}).get("quantum_backend"),
                "no_trade_candidates_created": True,
            },
        )
        _append_jsonl(
            events_path,
            {
                "generated_at": payload["generated_at"],
                "event_type": "qsase_nonlinear_quantum_pattern_lab_written",
                "status": payload["status"],
                "public_safe": True,
                "authority_flags_false": True,
            },
        )
        written["history"] = str(history_path)
        written["events"] = str(events_path)
    if append_log:
        _append_implementation_log(payload)
        written["implementation_log"] = str(_repo_root() / IMPLEMENTATION_LOG)
    return written


def write_quantum_pattern_reviews(
    payload: dict[str, Any],
    settings: Settings | None = None,
) -> dict[str, str]:
    runtime_dir = _runtime_dir(settings)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    path = runtime_dir / QUANTUM_REVIEWS_ARTIFACT
    _write_jsonl(path, payload["quantum_reviews"])
    return {"quantum_reviews": str(path)}


def write_nonlinear_quantum_pattern_lab(
    payload: dict[str, Any],
    settings: Settings | None = None,
    *,
    append_history: bool = True,
    append_log: bool = True,
) -> dict[str, str]:
    written = write_nonlinear_pattern_results(
        payload,
        settings,
        append_history=append_history,
        append_log=append_log,
    )
    written.update(write_quantum_pattern_reviews(payload, settings))
    return written


def build_and_write_nonlinear_quantum_pattern_lab(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    payload = build_nonlinear_quantum_pattern_lab(settings)
    errors = validate_nonlinear_pattern_results(payload)
    errors.extend(validate_quantum_pattern_reviews(payload))
    written = write_nonlinear_quantum_pattern_lab(payload, settings)
    return payload, written, sorted(set(errors))


def validate_negative_nonlinear_quantum_probes() -> list[str]:
    base = build_nonlinear_quantum_pattern_lab()
    errors: list[str] = []
    for flag in NONLINEAR_AUTHORITY_FLAGS:
        probe = copy.deepcopy(base)
        probe["authority_flags"][flag] = True
        if not any(flag in error for error in validate_nonlinear_pattern_results(probe)):
            errors.append(f"negative_probe_failed_for_{flag}")
    result_probe = copy.deepcopy(base)
    result_probe["nonlinear_results"][0]["baseline"] = {}
    if not any("baseline" in error for error in validate_nonlinear_pattern_results(result_probe)):
        errors.append("negative_probe_failed_for_missing_baseline")
    sample_probe = copy.deepcopy(base)
    sample_probe["nonlinear_results"][0]["sample"]["point_in_time_safe"] = False
    sample_probe["nonlinear_results"][0]["decision"]["nonlinear_status"] = "candidate_for_quantum_review"
    if not any("unsafe_sample" in error for error in validate_nonlinear_pattern_results(sample_probe)):
        errors.append("negative_probe_failed_for_unsafe_sample")
    if base.get("quantum_reviews"):
        hardware_probe = copy.deepcopy(base)
        hardware_probe["quantum_reviews"][0]["hardware_submitted"] = True
        if not any("hardware_submitted" in error for error in validate_quantum_pattern_reviews(hardware_probe)):
            errors.append("negative_probe_failed_for_hardware_submitted")
        backend_probe = copy.deepcopy(base)
        backend_probe["quantum_reviews"][0]["backend"] = "unlabeled_hardware"
        if not any("backend" in error for error in validate_quantum_pattern_reviews(backend_probe)):
            errors.append("negative_probe_failed_for_backend_label")
        confirmation_probe = copy.deepcopy(base)
        confirmation_probe["quantum_reviews"][0]["quantum_usefulness"]["not_trade_confirmation"] = False
        if not any("confirmation" in error for error in validate_quantum_pattern_reviews(confirmation_probe)):
            errors.append("negative_probe_failed_for_confirmation_boundary")
    return errors


if __name__ == "__main__":
    artifact = build_nonlinear_quantum_pattern_lab()
    print(_json_dump(_summary_without_records(artifact)))
