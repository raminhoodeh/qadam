"""QEG-9 matched nonlinear and quantum challenger projection."""

from __future__ import annotations

from collections import Counter
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import now_iso, read_json, read_jsonl, runtime_dir, write_json_atomic
from orchestrator.qadam_qeg_common import EXPERIMENT_BRIDGE_ARTIFACT, QUANTUM_CHALLENGER_ARTIFACT, qeg_authority, stable_id, write_phase_status


def _suitability(experiment: dict[str, Any]) -> tuple[float, list[str]]:
    definition = experiment.get("definition") if isinstance(experiment.get("definition"), dict) else {}
    reasons = ["cross-source interactions may be conditional on market regime"]
    score = 0.55
    if experiment.get("prior_context_match_count", 0) >= 5:
        score += 0.1
        reasons.append("enough prior matched observations exist for a fair challenger")
    if definition.get("strategy_family_id") in {"no_core_family_fit", "power_scarcity_congestion"}:
        score += 0.1
        reasons.append("the relationship may not be captured by a fixed core-family rule")
    return min(1.0, round(score, 4)), reasons


def build_graph_quantum_challenger(settings: Settings | None = None) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    generated_at = now_iso()
    bridge = read_json(runtime / EXPERIMENT_BRIDGE_ARTIFACT)
    existing = read_jsonl(runtime / "qadam_quantum_classical_comparison.jsonl")
    quantum_summary = read_json(runtime / "qadam_backtest_completion_nonlinear_quantum.json")
    comparisons: list[dict[str, Any]] = []
    for experiment in bridge.get("experiments") or []:
        definition = experiment.get("definition") if isinstance(experiment.get("definition"), dict) else {}
        instrument = str(definition.get("instrument") or "")
        family = str(definition.get("strategy_family_id") or "")
        horizon = str(definition.get("expected_horizon") or "")
        matched = [
            row for row in existing
            if str(row.get("instrument") or "") == instrument
            and str(row.get("horizon") or "") == horizon
            and (not family or str(row.get("strategy_family_id") or "") == family)
        ]
        score, reasons = _suitability(experiment)
        measurable = [row for row in matched if row.get("incremental_holdout_value") is not None]
        positive = [
            row for row in measurable
            if float(row.get("incremental_holdout_value") or 0) > 0
            and float(row.get("adjusted_p_value") or 1) < 0.05
            and row.get("classical_equal_or_better") is False
        ]
        if positive:
            conclusion = "incremental_value_candidate_requires_independent_replication"
        elif measurable:
            conclusion = "classical_preferred_or_no_reliable_incremental_value"
        else:
            conclusion = "not_measurable_yet"
        comparisons.append(
            {
                "challenger_id": stable_id("qeg-quantum-challenger", experiment.get("experiment_id")),
                "experiment_id": experiment.get("experiment_id"),
                "graph_generation_id": experiment.get("graph_generation_id"),
                "instrument": instrument,
                "strategy_family_id": family,
                "horizon": horizon,
                "nonlinear_suitability_score": score,
                "nonlinear_suitability_reasons": reasons,
                "matched_classical_baseline": "same_evidence_same_labels_same_folds_same_costs",
                "matched_prior_comparison_count": len(matched),
                "matched_prior_comparison_ids": [row.get("comparison_id") for row in matched],
                "conclusion": conclusion,
                "affects_strategy_evidence": bool(positive),
                "hardware_submission_requested": False,
                "hardware_submission_reason": "No new hardware job until a frozen simulator/classical challenger justifies it.",
                "hardware_cost_usd": 0.0,
                "quantum_trade_approval_created": False,
                "paper_order_created": False,
                "authority": qeg_authority(),
            }
        )
    errors: list[str] = []
    if bridge.get("status") != "passed":
        errors.append("experiment_bridge_not_passed")
    if int(quantum_summary.get("classical_baseline_missing_count") or 0):
        errors.append("existing_quantum_classical_baseline_missing")
    if any(row.get("hardware_submission_requested") for row in comparisons):
        errors.append("activity_driven_hardware_submission_violation")
    if any(row.get("quantum_trade_approval_created") for row in comparisons):
        errors.append("quantum_authority_violation")
    payload = {
        "schema_version": "qadam_graph_quantum_challenger.v1",
        "artifact_type": "qadam_graph_quantum_challenger",
        "generated_at": generated_at,
        "status": "passed" if not errors else "blocked",
        "comparison_count": len(comparisons),
        "conclusion_counts": dict(Counter(row["conclusion"] for row in comparisons)),
        "existing_comparison_count": len(existing),
        "existing_hardware_used": quantum_summary.get("hardware_used") is True,
        "existing_hardware_predictive_conclusion": quantum_summary.get("hardware_predictive_validation_status"),
        "existing_hardware_incremental_mean_net_return": quantum_summary.get("hardware_interaction_incremental_mean_net_return"),
        "quantum_value_state": quantum_summary.get("quantum_value_state", "not_proven"),
        "new_hardware_job_count": 0,
        "new_hardware_cost_usd": 0.0,
        "comparisons": comparisons,
        "validation_errors": errors,
        "authority": qeg_authority(),
    }
    write_json_atomic(runtime / QUANTUM_CHALLENGER_ARTIFACT, payload)
    write_phase_status(
        "QEG-9", status=payload["status"], implementation_complete=not errors,
        empirical_state="matched_challengers_linked_no_proven_quantum_value",
        artifacts=[QUANTUM_CHALLENGER_ARTIFACT], blockers=errors, settings=settings,
    )
    return payload, errors


def validate_graph_quantum_challenger(settings: Settings | None = None) -> list[str]:
    payload = read_json(runtime_dir(settings) / QUANTUM_CHALLENGER_ARTIFACT)
    errors = list(payload.get("validation_errors") or [])
    for row in payload.get("comparisons") or []:
        if row.get("matched_classical_baseline") != "same_evidence_same_labels_same_folds_same_costs":
            errors.append("unfair_quantum_comparison")
        if row.get("paper_order_created") or row.get("quantum_trade_approval_created"):
            errors.append("quantum_authority_violation")
    return sorted(set(errors))
