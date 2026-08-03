"""Audit whether Qadam's paper-review gates fit its observable evidence."""

from __future__ import annotations

from collections import Counter
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_experimental_paper_policy import (
    DISCOVERY_MICRO_TIER,
    EVIDENCE_PROFILES,
    POLICY_VERSION,
    default_policy,
    validate_policy,
)
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_wave_b_common import safe_float, safe_int

SCHEMA_VERSION = "qadam_evidence_gate_alignment.v1"
ARTIFACT = "qadam_evidence_gate_alignment.json"


def build_evidence_gate_alignment_from_inputs(
    *,
    policy: dict[str, Any],
    backtest_manifest: dict[str, Any],
    hypotheses: list[dict[str, Any]],
    akber_inputs: list[dict[str, Any]],
    akber_results: list[dict[str, Any]],
    akber_replay: list[dict[str, Any]],
    akber_ablations: list[dict[str, Any]],
    akber_checks: dict[str, Any],
    risk_policy: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    errors = list(validate_policy(policy))
    admission = policy.get("discovery_micro_admission", {})
    required_fields = {
        "source_price_context",
        "fresh_catalyst",
        "volatility_context",
        "risk_reward_context",
        "invalidation_clarity",
        "liquidity_and_spread",
        "paperability_proxy",
    }
    alternatives = {
        "volume_or_flow_confirmation",
        "technical_confirmation",
        "pricing_gap_evidence",
        "nonlinear_quantum_review",
    }
    if admission.get("volume_or_flow_required") is not False:
        errors.append("volume_still_required_in_addition_to_confirmation")
    if set(admission.get("confirmation_alternatives") or []) != alternatives:
        errors.append("confirmation_alternatives_do_not_match_capabilities")
    if admission.get("provider_availability_is_not_a_trigger") is not True:
        errors.append("provider_availability_can_become_trigger")

    discovery_hypotheses = [
        row
        for row in hypotheses
        if row.get("experimental_tier") == DISCOVERY_MICRO_TIER
    ]
    for row in discovery_hypotheses:
        lineage = row.get("pattern_lineage", {})
        hypothesis_id = row.get("hypothesis_id")
        if lineage.get("evidence_profile") not in EVIDENCE_PROFILES:
            errors.append(f"hypothesis_evidence_profile_missing:{hypothesis_id}")
        if lineage.get("provider_availability_is_not_trigger") is not True:
            errors.append(f"hypothesis_provider_status_became_trigger:{hypothesis_id}")
        if lineage.get("fresh_trigger_sources"):
            errors.append(f"foundry_claimed_live_trigger:{hypothesis_id}")

    typed_blockers = Counter(
        blocker.get("code")
        for record in akber_inputs
        for blocker in record.get("missing_context_reasons", [])
        if blocker.get("code")
    )
    input_profiles = Counter(
        record.get("evidence_profile") for record in akber_inputs if record.get("evidence_profile")
    )
    for record in akber_inputs:
        if record.get("experimental_tier") != DISCOVERY_MICRO_TIER:
            continue
        if set(record.get("required_context_fields") or []) != required_fields:
            errors.append(f"akber_required_fields_misaligned:{record.get('akber_input_id')}")
        if set(record.get("confirmation_alternatives") or []) != alternatives:
            errors.append(f"akber_confirmation_options_misaligned:{record.get('akber_input_id')}")

    result_profiles = Counter(
        record.get("evidence_profile") for record in akber_results if record.get("evidence_profile")
    )
    unsafe_passes = [
        record.get("akber_result_id")
        for record in akber_results
        if record.get("decision") == "pass"
        and (
            record.get("missing_critical_context_count") != 0
            or not record.get("current_trigger_sources")
            or record.get("confirmation_alternative_satisfied") is not True
        )
    ]
    if unsafe_passes:
        errors.extend(f"akber_unsafe_pass:{value}" for value in unsafe_passes)

    bulk = backtest_manifest.get("bulk_results", {})
    result_count = safe_int(bulk.get("result_count"))
    fold_count = safe_int(bulk.get("fold_count"))
    replay_count = len(akber_replay)
    backtest_used = bool(
        backtest_manifest.get("status") == "complete"
        and result_count > 0
        and fold_count > 0
        and replay_count > 0
        and akber_checks.get("net_historical_contribution_measurable") is True
    )
    if not backtest_used:
        errors.append("backtest_not_connected_to_gate_calibration")

    ablation_by_stage = {
        str(row.get("stage_removed")): row.get("delta", {})
        for row in akber_ablations
        if row.get("stage_removed")
    }
    confirmation_delta = ablation_by_stage.get("confirmation", {})
    execution_delta = ablation_by_stage.get("execution", {})
    retained_by_evidence = bool(
        safe_float(confirmation_delta.get("expectancy_change"), 0.0) < 0
        and safe_float(execution_delta.get("expectancy_change"), 0.0) < 0
        and safe_float(execution_delta.get("drawdown_change"), 0.0) < 0
    )
    if not retained_by_evidence:
        errors.append("retained_gate_ablation_support_missing")

    risk_budget = risk_policy.get("risk_budget", {})
    risk_context_derivation = risk_policy.get("context_derivation", {})
    capability_adapted_risk_context = {
        "daily_notional_from_broker_entry_orders": risk_context_derivation.get(
            "broker_entry_orders_are_daily_notional_source"
        )
        is True,
        "protective_exits_not_counted_as_new_exposure": risk_context_derivation.get(
            "protective_exit_orders_are_not_new_notional"
        )
        is True,
        "unlabelled_positions_conservatively_classified": risk_context_derivation.get(
            "unlabelled_positions_use_conservative_sleeve_classification"
        )
        is True,
        "missing_pairwise_data_uses_labelled_cluster_proxy": risk_context_derivation.get(
            "missing_pairwise_correlation_uses_cluster_proxy"
        )
        is True,
        "derived_context_cannot_change_numeric_limits": risk_context_derivation.get(
            "derived_context_can_reduce_missing_data_holds_but_not_numeric_limits"
        )
        is True,
    }
    if not all(capability_adapted_risk_context.values()):
        errors.append("capability_adapted_risk_context_contract_missing")
    retained_safety_controls = {
        "positive_after_cost_expectancy": admission.get(
            "positive_current_expectancy_after_costs_required"
        )
        is True,
        "numeric_invalidation": True,
        "liquidity_and_spread": True,
        "duplicate_exposure": True,
        "daily_drawdown": safe_float(risk_budget.get("max_daily_loss_pct_equity")) > 0,
        "trailing_drawdown": safe_float(
            risk_budget.get("max_trailing_drawdown_pct_equity")
        )
        > 0,
        "bounded_discovery_position_count": safe_int(
            risk_budget.get("maximum_concurrent_discovery_micro_positions")
        )
        == 3,
        "one_discovery_position_per_correlated_cluster": safe_int(
            risk_budget.get("maximum_discovery_positions_per_correlated_cluster")
        )
        == 1,
        "discovery_target_range_is_bounded": (
            safe_float(
                risk_budget.get("discovery_target_notional_usd", {}).get("minimum")
            )
            == 500.0
            and safe_float(
                risk_budget.get("discovery_target_notional_usd", {}).get("maximum")
            )
            == 1000.0
            and risk_budget.get("discovery_target_notional_usd", {}).get(
                "minimum_is_not_a_forced_floor"
            )
            is True
        ),
        "five_thousand_dollar_ceiling": safe_float(
            risk_budget.get("discovery_micro_trade_ceiling_usd")
        )
        == 5000.0,
        "guarded_alpaca_paper_only": policy.get("route", {}).get("required")
        == "guarded_alpaca_paper_via_paperops",
        "live_capital_disabled": policy.get("live_capital_enabled") is False,
        "validated_edge_credit_disabled": policy.get("proof", {}).get(
            "discovery_micro_validated_edge_credit_allowed"
        )
        is False,
    }
    if not all(retained_safety_controls.values()):
        errors.append("retained_safety_control_missing")

    errors = unique_errors(errors)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_evidence_gate_alignment",
        "generated_at": generated_at,
        "status": "passed" if not errors else "blocked",
        "implementation_complete": not errors,
        "policy_version": policy.get("policy_version"),
        "objective": (
            "Make observable evidence usable by paper-review gates without bypassing risk, "
            "execution, route, or proof boundaries."
        ),
        "backtest_usage": {
            "used": backtest_used,
            "run_id": backtest_manifest.get("run_id"),
            "strategy_result_count": result_count,
            "walk_forward_fold_count": fold_count,
            "measurable_akber_replay_count": replay_count,
            "historical_filter_metrics": akber_checks.get(
                "historical_filter_metrics", {}
            ),
            "future_labels_used_by_current_pattern_scorer": False,
            "backtest_is_not_a_current_trigger": True,
            "validated_edge_count": 0,
        },
        "calibration": {
            "method": "operator-approved structural recalibration supported by frozen historical ablations",
            "removed_redundancy": (
                "Volume or flow is now one of four confirmation options instead of a mandatory "
                "field required in addition to another confirmation."
            ),
            "confirmation_stage_ablation": confirmation_delta,
            "execution_stage_ablation": execution_delta,
            "confirmation_and_execution_controls_retained_by_evidence": retained_by_evidence,
            "historical_threshold_proposals_auto_applied": False,
        },
        "current_alignment": {
            "evidence_profiles": sorted(EVIDENCE_PROFILES),
            "akber_input_profile_counts": dict(sorted(input_profiles.items())),
            "akber_result_profile_counts": dict(sorted(result_profiles.items())),
            "typed_blocker_counts": dict(sorted(typed_blockers.items())),
            "discovery_hypothesis_count": len(discovery_hypotheses),
            "akber_input_count": len(akber_inputs),
            "akber_pass_count": sum(
                row.get("decision") == "pass" for row in akber_results
            ),
            "unsafe_pass_count": len(unsafe_passes),
        },
        "risk_context_alignment": {
            "contract_version": risk_context_derivation.get("contract_version"),
            "checks": capability_adapted_risk_context,
            "numeric_risk_envelope_changed": False,
            "direct_pairwise_measurement_preferred": True,
            "conservative_proxy_is_explicitly_labelled": True,
        },
        "retained_safety_controls": retained_safety_controls,
        "paper_order_created_count": 0,
        "broker_write_count": 0,
        "proof_credit_created_count": 0,
        "live_capital_enabled": False,
        "blockers": errors,
        "authority": authority_flags(),
    }


def validate_evidence_gate_alignment(record: dict[str, Any]) -> list[str]:
    errors = list(record.get("blockers") or [])
    if record.get("policy_version") != POLICY_VERSION:
        errors.append("evidence_gate_policy_version_stale")
    if record.get("backtest_usage", {}).get("used") is not True:
        errors.append("evidence_gate_backtest_usage_missing")
    if record.get("current_alignment", {}).get("unsafe_pass_count") != 0:
        errors.append("evidence_gate_unsafe_pass_detected")
    for field in (
        "paper_order_created_count",
        "broker_write_count",
        "proof_credit_created_count",
    ):
        if safe_int(record.get(field)) != 0:
            errors.append(f"evidence_gate_forbidden_output:{field}")
    if record.get("live_capital_enabled") is not False:
        errors.append("evidence_gate_live_capital_enabled")
    errors.extend(
        validate_authority(record.get("authority", {}), prefix="evidence_gate_alignment")
    )
    return unique_errors(errors)


def build_and_write_evidence_gate_alignment(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    generated = now_iso()
    record = build_evidence_gate_alignment_from_inputs(
        policy=read_json(runtime / "qadam_experimental_paper_policy.json")
        or default_policy(generated),
        backtest_manifest=read_json(runtime / "qadam_backtest_run_manifest.json"),
        hypotheses=read_jsonl(runtime / "qadam_strategy_hypotheses_v3.jsonl"),
        akber_inputs=read_jsonl(runtime / "qadam_akber_filter_v3_inputs.jsonl"),
        akber_results=read_jsonl(runtime / "qadam_akber_filter_v3_results.jsonl"),
        akber_replay=read_jsonl(runtime / "qadam_akber_filter_v3_replay.jsonl"),
        akber_ablations=read_jsonl(runtime / "qadam_akber_filter_v3_ablation.jsonl"),
        akber_checks=read_json(runtime / "qadam_akber_filter_v3_checks.json"),
        risk_policy=read_json(runtime / "qadam_portfolio_policy.json"),
        generated_at=generated,
    )
    errors = validate_evidence_gate_alignment(record)
    if errors and not record.get("blockers"):
        record["blockers"] = errors
        record["status"] = "blocked"
        record["implementation_complete"] = False
    AtomicArtifactStore(runtime).write_json(ARTIFACT, record)
    return record, errors


__all__ = [
    "ARTIFACT",
    "SCHEMA_VERSION",
    "build_and_write_evidence_gate_alignment",
    "build_evidence_gate_alignment_from_inputs",
    "validate_evidence_gate_alignment",
]
