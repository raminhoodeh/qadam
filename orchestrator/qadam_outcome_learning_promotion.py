"""EF-8 real-outcome attribution and bounded paper-strategy promotion.

Learning is evidence accounting, not authority. The module may admit a proven
emerging strategy to the paper strategy registry only inside the frozen risk
envelope. It never creates a trade candidate, risk approval, handoff, or order.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from orchestrator.config import Settings
from orchestrator.contracts.costs import cost_evidence
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_operator_ready_common import (
    authority_flags,
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    sha256_json,
    unique_errors,
    validate_authority,
)
from orchestrator.qadam_portfolio_risk_engine import default_portfolio_policy
from orchestrator.qadam_forward_evaluation import evaluate_forward_version
from orchestrator.qadam_forward_tournament import forward_tournament
from orchestrator.qadam_wave_b_common import safe_float, stable_id

SCHEMA_VERSION = "qadam_outcome_learning_promotion.v1"
PHASE_ID = "EF-8"
PROMOTION_POLICY_VERSION = "qadam-paper-strategy-promotion.2-matched-forward"
MIN_REAL_FORWARD_OUTCOMES = 20

OUTCOMES_ARTIFACT = "qadam_active_discovery_outcomes.jsonl"
ATTRIBUTION_ARTIFACT = "qadam_gate_attribution_ledger.jsonl"
PROPOSALS_ARTIFACT = "qadam_strategy_promotion_proposals.jsonl"
ADMISSIONS_ARTIFACT = "qadam_strategy_admission_decisions.jsonl"
VERSION_REGISTRY_ARTIFACT = "qadam_strategy_version_registry.json"
CHECK_ARTIFACT = "qadam_outcome_learning_promotion_checks.json"

TRIAL_EVALUATIONS_ARTIFACT = "qadam_active_discovery_trial_evaluations.jsonl"
SHADOW_OUTCOMES_ARTIFACT = "qadam_forward_shadow_outcomes.jsonl"
PAPER_POSTMORTEMS_ARTIFACT = "qadam_paper_postmortems_v3.jsonl"
HYPOTHESES_ARTIFACT = "qadam_strategy_hypotheses_v3.jsonl"
EDGE_REGISTRY_ARTIFACT = "qadam_edge_registry.jsonl"
SOURCE_CONTRACT_ARTIFACT = "qadam_strategy_source_contract.json"
RISK_POLICY_ARTIFACT = "qadam_portfolio_policy.json"
QUANTUM_SUMMARY_ARTIFACT = "qadam_quantum_usefulness_summary.json"
QUANTUM_COMPARISONS_ARTIFACT = "qadam_quantum_classical_comparison.jsonl"

PROMOTION_STATES = (
    "research_observation",
    "discovery_micro_eligible",
    "forward_evidence_collecting",
    "validated_edge_candidate",
    "emerging_paper_strategy",
    "validated_paper_strategy",
)


def _strategy_id(record: dict[str, Any]) -> str:
    mapping = record.get("strategy_mapping")
    mapping = mapping if isinstance(mapping, dict) else {}
    return str(
        record.get("strategy_family_id")
        or record.get("strategy_id")
        or record.get("strategy_family")
        or mapping.get("strategy_family_id")
        or "unclassified"
    )


def _lineage(record: dict[str, Any]) -> dict[str, Any]:
    value = record.get("lineage")
    if isinstance(value, dict):
        return value
    return {
        "hypothesis_id": record.get("hypothesis_id"),
        "edge_id": record.get("edge_id"),
        "shadow_evidence_id": record.get("outcome_id"),
        "score_id": record.get("score_id"),
    }


def _shadow_outcome_row(record: dict[str, Any], generated_at: str) -> dict[str, Any]:
    akber = str(record.get("akber_decision") or "")
    outcome_type = (
        "veto"
        if akber == "veto"
        else "hold"
        if akber == "hold_missing_context"
        else "shadow"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_active_discovery_outcome",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "outcome_record_id": stable_id("ef8-shadow-outcome", record.get("outcome_id")),
        "source_artifact": SHADOW_OUTCOMES_ARTIFACT,
        "source_record_id": record.get("outcome_id"),
        "outcome_type": outcome_type,
        "measurement_state": "mature_real_elapsed_forward_outcome",
        "matured": record.get("simulated_elapsed_time") is False
        and record.get("outcome_available_at") is not None,
        "simulated_elapsed_time": record.get("simulated_elapsed_time"),
        "strategy_family_id": _strategy_id(record),
        "instrument": record.get("instrument")
        or record.get("entry_observation", {}).get("instrument"),
        "hypothesis_id": record.get("hypothesis_id"),
        "lineage": _lineage(record),
        "net_return_after_costs": record.get("net_return"),
        "gross_return": record.get("gross_return"),
        "cost_bps": record.get("cost_bps"),
        "costs_measured": record.get("costs_measured") is True,
        "cost_measurement_source": record.get("cost_measurement_source"),
        "cost_model_version": record.get("cost_model_version"),
        "costs_are_modelled_not_live_execution_costs": record.get("costs_are_modelled_not_live_execution_costs") is True,
        "direction_correct": record.get("direction_correct"),
        "akber_decision": akber,
        "counterfactuals": record.get("counterfactuals", {}),
        "paper_order_created": False,
        "proof_credit_granted": False,
        "authority": authority_flags(),
    }


def _evaluation_outcome_row(record: dict[str, Any], generated_at: str) -> dict[str, Any]:
    root = str(record.get("primary_root_cause") or "")
    akber = str(record.get("akber_decision") or "")
    if root in {"mapping_defect", "evidence_conversion_defect", "source_outage", "route_failure"}:
        outcome_type = "implementation_defect"
    elif akber == "veto":
        outcome_type = "veto"
    elif akber == "hold_missing_context":
        outcome_type = "hold"
    elif record.get("current_trigger_state") != "active":
        outcome_type = "inactive_trigger"
    else:
        outcome_type = "missed_opportunity_pending"
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_active_discovery_outcome",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "outcome_record_id": stable_id(
            "ef8-evaluation-outcome", record.get("evaluation_id")
        ),
        "source_artifact": TRIAL_EVALUATIONS_ARTIFACT,
        "source_record_id": record.get("evaluation_id"),
        "outcome_type": outcome_type,
        "measurement_state": "pending_real_horizon" if outcome_type == "missed_opportunity_pending" else "decision_state_recorded",
        "matured": False,
        "simulated_elapsed_time": False,
        "strategy_family_id": _strategy_id(record),
        "instrument": record.get("instrument"),
        "hypothesis_id": record.get("hypothesis_id"),
        "lineage": _lineage(record),
        "net_return_after_costs": None,
        "current_trigger_state": record.get("current_trigger_state"),
        "current_trigger_ids": record.get("current_trigger_ids", []),
        "akber_decision": akber,
        "risk_state": record.get("risk_state"),
        "router_state": record.get("router_state"),
        "primary_root_cause": root or None,
        "paper_order_created": False,
        "proof_credit_granted": False,
        "authority": authority_flags(),
    }


def _paper_outcome_row(record: dict[str, Any], generated_at: str) -> dict[str, Any]:
    metrics = record.get("metrics") if isinstance(record.get("metrics"), dict) else {}
    attributable = bool(
        record.get("learning_attribution_allowed") is True
        and metrics.get("real_close_verified") is True
        and metrics.get("realized_net_pnl") is not None
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_active_discovery_outcome",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "outcome_record_id": stable_id("ef8-paper-outcome", record.get("postmortem_id")),
        "source_artifact": PAPER_POSTMORTEMS_ARTIFACT,
        "source_record_id": record.get("postmortem_id"),
        "outcome_type": "paper" if attributable else "implementation_defect",
        "measurement_state": "verified_paper_outcome" if attributable else "mirror_only_not_attributable",
        "matured": attributable,
        "simulated_elapsed_time": False,
        "strategy_family_id": _strategy_id(record),
        "instrument": record.get("instrument"),
        "hypothesis_id": record.get("lineage", {}).get("strategy_hypothesis_id"),
        "lineage": _lineage(record),
        "realized_net_pnl": metrics.get("realized_net_pnl"),
        "holding_period_seconds": metrics.get("holding_period_seconds"),
        "completion_requirements_missing": record.get("completion_requirements_missing", []),
        "paper_order_created": False,
        "proof_credit_granted": False,
        "authority": authority_flags(),
    }


def build_outcome_records(
    trial_evaluations: list[dict[str, Any]],
    shadow_outcomes: list[dict[str, Any]],
    paper_postmortems: list[dict[str, Any]],
    *,
    generated_at: str,
) -> list[dict[str, Any]]:
    rows = [
        *(_shadow_outcome_row(row, generated_at) for row in shadow_outcomes),
        *(_evaluation_outcome_row(row, generated_at) for row in trial_evaluations),
        *(_paper_outcome_row(row, generated_at) for row in paper_postmortems),
    ]
    deduplicated = {str(row["outcome_record_id"]): row for row in rows}
    return sorted(deduplicated.values(), key=lambda row: str(row["outcome_record_id"]))


def _quantum_usefulness(
    summary: dict[str, Any], comparisons: list[dict[str, Any]]
) -> dict[str, Any]:
    useful = [
        row
        for row in comparisons
        if row.get("experiment_lane") == "quantum"
        and safe_float(row.get("incremental_holdout_value"), 0.0) > 0
        and row.get("verdict") in {"reliable_incremental_value", "useful"}
        and row.get("classical_equal_or_better") is False
    ]
    positive = bool(
        useful
        and int(summary.get("useful_quantum_comparison_count") or 0) > 0
        and summary.get("quantum_advantage_claim_allowed") is True
    )
    return {
        "state": "positive_incremental_value" if positive else "not_positive",
        "positive_usefulness_attribution_allowed": positive,
        "matched_reliable_positive_comparison_count": len(useful),
        "summary_status": summary.get("status"),
        "reason": (
            "Quantum beat a matched classical baseline reliably."
            if positive
            else "No reliable positive matched-classical quantum increment is recorded."
        ),
    }


def build_attribution_ledger(
    outcomes: list[dict[str, Any]], quantum: dict[str, Any], *, generated_at: str
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for outcome in outcomes:
        matured = outcome.get("matured") is True
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "qadam_gate_attribution",
                "phase_id": PHASE_ID,
                "generated_at": generated_at,
                "attribution_id": stable_id(
                    "ef8-gate-attribution", outcome.get("outcome_record_id")
                ),
                "outcome_record_id": outcome.get("outcome_record_id"),
                "outcome_type": outcome.get("outcome_type"),
                "strategy_family_id": outcome.get("strategy_family_id"),
                "instrument": outcome.get("instrument"),
                "lineage": outcome.get("lineage", {}),
                "components": {
                    "source_support": {"state": "linked" if outcome.get("lineage") else "not_attributable"},
                    "current_trigger": {"state": outcome.get("current_trigger_state") or "not_recorded"},
                    "market_confirmation": {"state": "measured" if matured else "pending_or_not_reached"},
                    "direction_resolver": {"state": "measured" if outcome.get("direction_correct") is not None else "not_measurable"},
                    "akber": {"state": outcome.get("akber_decision") or "not_reached"},
                    "portfolio_risk": {"state": outcome.get("risk_state") or "not_reached"},
                    "router": {"state": outcome.get("router_state") or "not_reached"},
                    "proxy_basis": {"state": "not_measurable_without_linked_proxy_basis"},
                    "costs": cost_evidence(outcome),
                    "execution_quality": {"state": outcome.get("measurement_state")},
                    "quantum_review": quantum,
                },
                "proposal_only": True,
                "strategy_mutated": False,
                "risk_policy_mutated": False,
                "paper_order_created": False,
                "proof_credit_granted": False,
                "authority": authority_flags(),
            }
        )
    return rows


def _expected_risk_envelope(policy: dict[str, Any]) -> dict[str, Any]:
    risk = policy.get("risk_budget", {})
    return {
        "policy_version": policy.get("policy_version"),
        "max_position_notional_usd": risk.get("max_position_notional_usd"),
        "discovery_micro_trade_ceiling_usd": risk.get("discovery_micro_trade_ceiling_usd"),
        "maximum_concurrent_discovery_micro_positions": risk.get("maximum_concurrent_discovery_micro_positions"),
        "maximum_discovery_positions_per_correlated_cluster": risk.get("maximum_discovery_positions_per_correlated_cluster"),
        "max_risk_per_position_pct_equity": risk.get("max_risk_per_position_pct_equity"),
        "max_daily_loss_pct_equity": risk.get("max_daily_loss_pct_equity"),
        "max_trailing_drawdown_pct_equity": risk.get("max_trailing_drawdown_pct_equity"),
        "max_gross_notional_pct_equity": risk.get("max_gross_notional_pct_equity"),
    }


def evaluate_strategy_promotion(
    strategy: dict[str, Any],
    edge: dict[str, Any] | None,
    shadow_outcomes: list[dict[str, Any]],
    risk_policy: dict[str, Any],
    *,
    generated_at: str,
    registered_evaluation: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    strategy_id = _strategy_id(strategy)
    version_id = strategy.get("strategy_version_id")
    real_outcomes = [
        row
        for row in shadow_outcomes
        if row.get("simulated_elapsed_time") is False
        and row.get("outcome_available_at")
        and version_id and row.get("strategy_version_id") == version_id
        and _strategy_id(row) == strategy_id
    ]
    evaluation = registered_evaluation if registered_evaluation is not None else evaluate_forward_version(version_id, real_outcomes, as_of=generated_at)
    mean_return = evaluation["mean_net_return"]
    edge_valid = bool(
        edge
        and (
            edge.get("validated_edge") is True
            or edge.get("promotion_class") == "validated_research_edge"
            or edge.get("status") in {"validated_edge", "validated"}
        )
    )
    canonical_envelope = _expected_risk_envelope(default_portfolio_policy(generated_at))
    current_envelope = _expected_risk_envelope(risk_policy)
    risk_envelope_unchanged = current_envelope == canonical_envelope
    blockers: list[str] = []
    blockers.extend(evaluation["blockers"])
    if evaluation["independent_outcome_count"] < MIN_REAL_FORWARD_OUTCOMES:
        blockers.append("insufficient_real_forward_outcomes")
    if mean_return is None or mean_return <= 0:
        blockers.append("positive_forward_net_return_not_demonstrated")
    if not risk_envelope_unchanged:
        blockers.append("risk_envelope_changed")
    admitted = not blockers
    state = (
        "emerging_paper_strategy"
        if admitted
        else "validated_edge_candidate"
        if edge_valid
        else "forward_evidence_collecting"
        if real_outcomes
        else "discovery_micro_eligible"
        if strategy.get("experimental_tier") == "discovery_micro"
        else "research_observation"
    )
    definition = {
        "strategy_family_id": strategy_id,
        "entry": strategy.get("direction_horizon"),
        "source_recipe": strategy.get("source_recipe") or strategy.get("pattern_lineage"),
        "proxy": strategy.get("instrument_proxy_mapping"),
        "invalidation": strategy.get("invalidation"),
        "risk_concept": strategy.get("risk_concept"),
    }
    version_id = version_id or stable_id("unregistered-legacy-strategy", strategy_id, definition)
    proposal = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_strategy_promotion_proposal",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "promotion_proposal_id": stable_id("ef8-promotion-proposal", version_id),
        "promotion_policy_version": PROMOTION_POLICY_VERSION,
        "strategy_family_id": strategy_id,
        "strategy_version_id": version_id,
        "hypothesis_id": strategy.get("hypothesis_id"),
        "edge_id": edge.get("edge_id") if edge else None,
        "current_promotion_state": state,
        "real_forward_outcome_count": len(real_outcomes),
        "forward_evaluation": evaluation,
        "historical_edge_required_for_discovery_continuation": False,
        "historical_edge_required_for_emerging_review": False,
        "mean_forward_net_return_after_costs": mean_return,
        "validated_edge_present": edge_valid,
        "risk_envelope_unchanged": risk_envelope_unchanged,
        "blockers": blockers,
        "automatic_paper_admission_recommended": admitted,
        "automatic_risk_envelope_expansion_allowed": False,
        "proposal_only": True,
        "paper_order_created": False,
        "authority": authority_flags(),
    }
    decision = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_strategy_admission_decision",
        "phase_id": PHASE_ID,
        "generated_at": generated_at,
        "admission_decision_id": stable_id("ef8-admission", version_id, admitted),
        "promotion_policy_version": PROMOTION_POLICY_VERSION,
        "strategy_family_id": strategy_id,
        "strategy_version_id": version_id,
        "decision": "admitted_emerging_paper_strategy" if admitted else "not_admitted",
        "promotion_state": state,
        "paper_strategy_admitted": admitted,
        "live_strategy_admitted": False,
        "risk_envelope_mutated": False,
        "execution_approval_created": False,
        "paper_order_created": False,
        "proof_credit_granted": False,
        "blockers": blockers,
        "authority": authority_flags(),
    }
    return proposal, decision


def _focused_programmes(
    outcomes: list[dict[str, Any]], source_contract: dict[str, Any]
) -> list[dict[str, Any]]:
    source_rows = {
        str(row.get("source_key") or ""): row
        for row in source_contract.get("sources", [])
        if isinstance(row, dict) and row.get("source_key")
    }
    programmes = (
        ("prediction_market_disagreement", ("kalshi", "polymarket")),
        ("stock_act_sector_repricing", ("stock_act",)),
        ("unusual_whales_confirmation", ("unusual_whales",)),
    )
    rows: list[dict[str, Any]] = []
    for name, sources in programmes:
        source_contract_ready = all(
            source_rows.get(source, {}).get("provider_backed") is True
            and source_rows.get(source, {}).get("availability_state")
            not in {"excluded", "unavailable", "temporarily_degraded"}
            for source in sources
        )
        linked_outcomes = [
            row
            for row in outcomes
            if row.get("matured") is True
            and any(source in str(row).lower() for source in sources)
        ]
        rows.append({
            "programme_id": name,
            "required_sources": list(sources),
            "provider_contract_present": all(source in source_rows for source in sources),
            "provider_backed_programme_evidence_ready": source_contract_ready,
            "new_matured_outcome_count": len(linked_outcomes),
            "incremental_challenger_state": (
                "ready_for_incremental_retest"
                if linked_outcomes and source_contract_ready
                else "waiting_for_provider_backed_matured_outcome"
            ),
            "rules_frozen": True,
            "automatic_threshold_change_allowed": False,
        })
    return rows


def validate_outcome_learning_promotion(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if tuple(state["version_registry"].get("promotion_states", [])) != PROMOTION_STATES:
        errors.append("strategy_promotion_state_machine_invalid")
    for outcome in state["outcomes"]:
        if outcome.get("simulated_elapsed_time") is True:
            errors.append("simulated_outcome_entered_learning")
        if outcome.get("paper_order_created") is not False:
            errors.append("outcome_learning_created_order")
    for row in [*state["attribution"], *state["proposals"], *state["admissions"]]:
        if row.get("paper_order_created") is not False:
            errors.append("promotion_pipeline_created_order")
        if row.get("risk_envelope_mutated") is True:
            errors.append("promotion_pipeline_mutated_risk_envelope")
        errors.extend(validate_authority(row.get("authority", {}), prefix="ef8_learning"))
    for decision in state["admissions"]:
        if decision.get("paper_strategy_admitted") is True and (
            decision.get("promotion_state") != "emerging_paper_strategy"
            or decision.get("risk_envelope_mutated") is not False
        ):
            errors.append("automatic_paper_admission_boundary_invalid")
        if decision.get("live_strategy_admitted") is not False:
            errors.append("live_strategy_admission_created")
    quantum = state["quantum_usefulness"]
    if quantum.get("positive_usefulness_attribution_allowed") is True and quantum.get(
        "matched_reliable_positive_comparison_count"
    ) <= 0:
        errors.append("quantum_positive_attribution_without_matched_value")
    if state["version_registry"].get("automatic_risk_envelope_expansion_allowed") is not False:
        errors.append("strategy_registry_allows_risk_expansion")
    return unique_errors(errors)


def build_outcome_learning_promotion_state(
    settings: Settings | None = None, *, generated_at: str | None = None
) -> dict[str, Any]:
    runtime = runtime_dir(settings)
    generated = generated_at or now_iso()
    trial = read_jsonl(runtime / TRIAL_EVALUATIONS_ARTIFACT)
    shadows = read_jsonl(runtime / SHADOW_OUTCOMES_ARTIFACT)
    postmortems = read_jsonl(runtime / PAPER_POSTMORTEMS_ARTIFACT)
    hypotheses = read_jsonl(runtime / HYPOTHESES_ARTIFACT)
    edges = read_jsonl(runtime / EDGE_REGISTRY_ARTIFACT)
    source_contract = read_json(runtime / SOURCE_CONTRACT_ARTIFACT)
    risk_policy = read_json(runtime / RISK_POLICY_ARTIFACT) or default_portfolio_policy(generated)
    quantum_summary = read_json(runtime / QUANTUM_SUMMARY_ARTIFACT)
    quantum_comparisons = read_jsonl(runtime / QUANTUM_COMPARISONS_ARTIFACT)
    outcomes = build_outcome_records(trial, shadows, postmortems, generated_at=generated)
    strategy_by_hypothesis = {
        str(row.get("hypothesis_id") or ""): _strategy_id(row) for row in hypotheses
    }
    for outcome in outcomes:
        if outcome.get("strategy_family_id") != "unclassified":
            continue
        inferred = strategy_by_hypothesis.get(str(outcome.get("hypothesis_id") or ""))
        if inferred:
            outcome["strategy_family_id"] = inferred
            outcome["strategy_family_inference_basis"] = "exact_hypothesis_identity"
    quantum = _quantum_usefulness(quantum_summary, quantum_comparisons)
    attribution = build_attribution_ledger(outcomes, quantum, generated_at=generated)
    edge_by_hypothesis = {
        str(row.get("hypothesis_id") or row.get("strategy_hypothesis_id") or ""): row
        for row in edges
    }
    proposals: list[dict[str, Any]] = []
    admissions: list[dict[str, Any]] = []
    tournament, freeze_registry = forward_tournament(
        runtime, shadows, generated_at=generated,
        active_versions=[row["strategy_version_id"] for row in hypotheses if row.get("strategy_version_id")])
    registered = {row["strategy_version_id"]: row for row in tournament["candidates"]}
    for hypothesis in hypotheses:
        evaluation = registered.get(hypothesis.get("strategy_version_id"))
        if evaluation is None:
            evaluation = evaluate_forward_version(hypothesis.get("strategy_version_id"), [], as_of=generated)
            evaluation["blockers"].append("canonical_preregistration_missing")
            evaluation["eligible_for_emerging_review"] = False
        proposal, decision = evaluate_strategy_promotion(
            hypothesis,
            edge_by_hypothesis.get(str(hypothesis.get("hypothesis_id") or "")),
            shadows,
            risk_policy,
            generated_at=generated,
            registered_evaluation=evaluation,
        )
        proposals.append(proposal)
        admissions.append(decision)
    definitions: dict[str, dict[str, Any]] = {}
    for proposal in proposals:
        definitions[str(proposal["strategy_version_id"])] = {
            "strategy_family_id": proposal["strategy_family_id"],
            "strategy_version_id": proposal["strategy_version_id"],
            "promotion_state": proposal["current_promotion_state"],
            "promotion_policy_version": PROMOTION_POLICY_VERSION,
            "automatic_paper_admission_recommended": proposal[
                "automatic_paper_admission_recommended"
            ],
        }
    version_registry = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_strategy_version_registry",
        "phase_id": PHASE_ID,
        "generated_at": generated,
        "promotion_policy_version": PROMOTION_POLICY_VERSION,
        "promotion_states": list(PROMOTION_STATES),
        "strategy_versions": list(definitions.values()),
        "strategy_version_count": len(definitions),
        "risk_policy_version": risk_policy.get("policy_version"),
        "risk_envelope_digest": sha256_json(_expected_risk_envelope(risk_policy)),
        "automatic_emerging_paper_admission_allowed": True,
        "automatic_validated_strategy_admission_allowed": False,
        "automatic_risk_envelope_expansion_allowed": False,
        "live_capital_authority_granted": False,
        "focused_programmes": _focused_programmes(outcomes, source_contract),
        "authority": authority_flags(),
    }
    return {
        "tournament": tournament,
        "freeze_registry": freeze_registry,
        "outcomes": outcomes,
        "attribution": attribution,
        "proposals": proposals,
        "admissions": admissions,
        "version_registry": version_registry,
        "quantum_usefulness": quantum,
    }


def build_and_write_outcome_learning_promotion(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    state = build_outcome_learning_promotion_state(settings)
    errors = validate_outcome_learning_promotion(state)
    outcome_counts = Counter(row.get("outcome_type") for row in state["outcomes"])
    promotion_counts = Counter(row.get("promotion_state") for row in state["admissions"])
    checks = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "qadam_outcome_learning_promotion_checks",
        "phase_id": PHASE_ID,
        "generated_at": now_iso(),
        "status": "passed" if not errors else "blocked",
        "implementation_complete": not errors,
        "outcome_record_count": len(state["outcomes"]),
        "outcome_type_counts": dict(sorted(outcome_counts.items())),
        "mature_real_outcome_count": sum(
            row.get("matured") is True for row in state["outcomes"]
        ),
        "gate_attribution_count": len(state["attribution"]),
        "promotion_proposal_count": len(state["proposals"]),
        "promotion_state_counts": dict(sorted(promotion_counts.items())),
        "automatic_emerging_paper_admission_count": sum(
            row.get("paper_strategy_admitted") is True for row in state["admissions"]
        ),
        "risk_envelope_mutation_count": 0,
        "live_strategy_admission_count": 0,
        "quantum_positive_usefulness_attribution_allowed": state[
            "quantum_usefulness"
        ]["positive_usefulness_attribution_allowed"],
        "paper_order_created_count": 0,
        "proof_credit_granted_count": 0,
        "validation_error_count": len(errors),
        "validation_errors": errors,
        "authority": authority_flags(),
    }
    store = AtomicArtifactStore(runtime)
    store.write_jsonl(OUTCOMES_ARTIFACT, state["outcomes"])
    store.write_jsonl(ATTRIBUTION_ARTIFACT, state["attribution"])
    store.write_jsonl(PROPOSALS_ARTIFACT, state["proposals"])
    store.write_jsonl(ADMISSIONS_ARTIFACT, state["admissions"])
    store.write_json(VERSION_REGISTRY_ARTIFACT, state["version_registry"])
    store.write_json("qadam_forward_strategy_tournament.json", state["tournament"])
    store.write_json("qadam_forward_research_freeze_registry.json", state["freeze_registry"])
    store.write_json(CHECK_ARTIFACT, checks)
    return state, checks, errors


__all__ = [
    "ADMISSIONS_ARTIFACT",
    "ATTRIBUTION_ARTIFACT",
    "CHECK_ARTIFACT",
    "OUTCOMES_ARTIFACT",
    "PROPOSALS_ARTIFACT",
    "PROMOTION_STATES",
    "VERSION_REGISTRY_ARTIFACT",
    "build_and_write_outcome_learning_promotion",
    "build_outcome_learning_promotion_state",
    "evaluate_strategy_promotion",
    "validate_outcome_learning_promotion",
]
