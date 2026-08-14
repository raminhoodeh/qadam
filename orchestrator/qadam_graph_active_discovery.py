"""QEG-11 bounded top-K evidence-fit discovery and Akber intake.

The graph lane owns research projections only.  It may form an immutable,
admitted paper-research hypothesis and evaluate Akber's practical evidence,
but shadow, portfolio risk, Router, and canonical PaperOps retain their existing
authority and artifact ownership.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_akber_filter_v3 import build_akber_input, evaluate_akber_input
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_decision_evidence_packets import (
    build_decision_evidence_packets_from_inputs,
    current_decision_artifacts,
    validate_decision_evidence_packets,
)
from orchestrator.qadam_operator_ready_common import (
    now_iso,
    read_json,
    read_jsonl,
    runtime_dir,
    sha256_json,
    write_json_atomic,
)
from orchestrator.qadam_qeg_common import (
    ACTIONABILITY_QUEUE_ARTIFACT,
    ACTIVE_DISCOVERY_FUNNEL_ARTIFACT,
    PAPER_ADMISSION_ARTIFACT,
    PATTERN_CANDIDATES_ARTIFACT,
    QEG_AKBER_INPUTS_ARTIFACT,
    QEG_AKBER_RESULTS_ARTIFACT,
    QEG_DECISION_PACKETS_ARTIFACT,
    QEG_HYPOTHESES_ARTIFACT,
    STRATEGY_VERSIONS_ARTIFACT,
    qeg_authority,
    stable_id,
    write_phase_status,
)

ACTIONABLE_DIRECTIONS = {"long", "short"}


def _direction_index(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (str(row.get("strategy_family_id") or ""), str(row.get("instrument") or ""))
        if key not in result or str(row.get("generated_at") or "") > str(result[key].get("generated_at") or ""):
            result[key] = row
    return result


def _candidate_index(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("pattern_relationship_id")): row
        for row in payload.get("candidates") or []
        if row.get("pattern_relationship_id")
    }


def _expiry(generated_at: str, horizon: str) -> str:
    days = 5
    digits = "".join(character for character in str(horizon) if character.isdigit())
    if digits:
        days = max(1, min(int(digits), 30))
    issued = datetime.fromisoformat(generated_at.replace("Z", "+00:00")).astimezone(timezone.utc)
    return (issued + timedelta(days=days)).isoformat()


def _qeg_hypothesis(
    strategy: dict[str, Any],
    candidate: dict[str, Any],
    direction: dict[str, Any],
    admission: dict[str, Any],
    *,
    generated_at: str,
) -> dict[str, Any]:
    contract = strategy.get("contract") if isinstance(strategy.get("contract"), dict) else {}
    strategy_version_id = str(strategy.get("strategy_version_id") or "")
    pattern_id = str(strategy.get("pattern_relationship_id") or candidate.get("pattern_relationship_id") or "")
    family = str(contract.get("strategy_family_id") or candidate.get("strategy_family_id") or "")
    instrument = str(contract.get("instrument") or candidate.get("instrument") or "")
    actionable_direction = str(direction.get("actionable_direction") or contract.get("direction_rule") or "")
    horizon = str(contract.get("time_horizon") or candidate.get("horizon") or "5d_forward")
    research_goal_id = str(strategy.get("research_goal_id") or stable_id("qeg-research-goal", pattern_id))
    hypothesis_id = stable_id("qeg-strategy-hypothesis", strategy_version_id, admission.get("admission_decision_id"))
    candidate_identity_id = stable_id(
        "qeg-candidate-identity", research_goal_id, pattern_id, instrument, actionable_direction, horizon
    )
    fresh_sources = [
        row for row in candidate.get("source_path") or []
        if isinstance(row, dict) and row.get("fresh") is True and row.get("quorum_eligible") is True
    ]
    fresh_source_keys = sorted(
        str(row.get("source_key")) for row in fresh_sources if row.get("source_key")
    )
    economics = contract.get("experimental_economics")
    economics = economics if isinstance(economics, dict) else {}
    evidence_class = str(strategy.get("evidence_class") or "experimental_unvalidated")
    tier = "discovery_micro" if evidence_class == "experimental_unvalidated" else "validated_paper"
    return {
        "schema_version": "qadam_strategy_hypothesis_v3.qeg1",
        "artifact_type": "qadam_qeg_strategy_hypothesis",
        "generated_at": generated_at,
        "hypothesis_id": hypothesis_id,
        "evidence_class": evidence_class,
        "experimental_tier": tier,
        "paper_experiment_purpose": "bounded graph-discovered paper evidence collection",
        "hypothesis_state": "ready_for_akber_review",
        "strategy_version_id": strategy_version_id,
        "admission_decision_id": admission.get("admission_decision_id"),
        "edge_lineage": {
            "edge_id": strategy.get("edge_id"),
            "experiment_id": strategy.get("experiment_id"),
            "evidence_hash": strategy.get("evidence_hash"),
            "strategy_version_id": strategy_version_id,
            "applied_learning_version_ids": [],
            "complete": bool(strategy.get("experiment_id") or strategy.get("edge_id")),
        },
        "research_goal_lineage": {
            "research_goal_id": research_goal_id,
            "origin_pattern_relationship_id": pattern_id,
            "origin_phase": "QEG-7",
            "foundry_phase": "QEG-10",
            "complete": True,
        },
        "candidate_identity_material": {
            "candidate_identity_id": candidate_identity_id,
            "identity_type": "research_hypothesis_identity_not_order_idempotency",
            "research_goal_id": research_goal_id,
            "strategy_family_id": family,
            "pattern_relationship_id": pattern_id,
            "observed_instrument": instrument,
            "paperable_proxy_expression": contract.get("execution_proxy") or instrument,
            "direction": actionable_direction,
            "time_window": horizon,
            "not_trade_candidate": True,
            "not_idempotency_key_for_orders": True,
            "trade_candidate_created": False,
            "order_idempotency_key_created": False,
        },
        "strategy_mapping": {
            "strategy_family_id": family,
            "strategy_label": candidate.get("strategy_label") or family,
            "destination": contract.get("destination"),
            "fit_is_research_context_only": True,
        },
        "pattern_lineage": {
            "pattern_relationship_id": pattern_id,
            "score_id": strategy.get("score_id") or candidate.get("score_id"),
            "evidence_profile": candidate.get("evidence_profile"),
            "raw_research_score": candidate.get("research_rank"),
            "fresh_support_sources": fresh_source_keys,
            "fresh_trigger_sources": fresh_source_keys,
            "fresh_quorum_sources": fresh_source_keys,
            "historical_source_quorum_satisfied": bool(fresh_source_keys),
            "non_quorum_support_used": False,
            "non_quorum_support_cannot_claim_quorum": True,
            "provider_availability_is_not_trigger": True,
            "source_confirmation_mode": (
                "profile_specific_current_trigger_plus_one_live_market_confirmation"
            ),
            "graph_generation_id": candidate.get("graph_generation_id"),
            "complete": True,
        },
        "instrument_proxy_mapping": {
            "observed_instrument": instrument,
            "execution_proxy": contract.get("execution_proxy") or instrument,
            "observed_instrument_directly_paperable": instrument not in {"KALSHI:EVENTS", "POLYMARKET:EVENTS"},
            "proxy_review_required": False,
            "proxy_basis": "direct listed paper proxy",
        },
        "direction_horizon": {
            "direction": actionable_direction,
            "horizon": horizon,
            "direction_resolution_id": direction.get("direction_resolution_id"),
            "regime": "current_provider_backed_context",
        },
        "catalyst_confirmation": {
            "catalyst": candidate.get("economic_mechanism"),
            "confirmation_required": [
                "current profile trigger",
                "current listed-market confirmation",
                "positive current expectancy after costs",
            ],
            "confirmation_complete": False,
        },
        "entry_concept": {
            "summary": contract.get("entry_rule"),
            "entry_authorized": False,
        },
        "invalidation_exit": {
            "invalidation_conditions": [contract.get("invalidation_rule")],
            "exit_conditions": [contract.get("exit_rule")],
            "exit_order_created": False,
        },
        "risk_concept": {
            "maximum_notional_usd": contract.get("maximum_notional_usd"),
            "maximum_loss_must_be_derived_from_invalidation": True,
            "liquidity_and_spread_required": True,
            "portfolio_correlation_required": True,
            "expected_reward_to_risk": economics.get("expected_reward_to_risk") or 1.50,
            "experimental_tier": tier,
            "absolute_notional_ceiling_usd": contract.get("maximum_notional_usd"),
            "position_size": None,
            "risk_approval_created": False,
        },
        "expected_edge_range": {
            "gross_expectancy": None,
            "net_expectancy": economics.get(
                "provisional_net_expectancy_after_costs"
            ),
            "net_expectancy_source": (
                "shrunk_rejected_historical_result_not_edge_proof"
            ),
            "source_hypothesis_id": economics.get("source_hypothesis_id"),
            "source_method_id": economics.get("source_method_id"),
            "source_rejection_reasons": economics.get(
                "source_rejection_reasons", []
            ),
            "not_a_validated_expectancy": True,
            "range_is_research_estimate_only": True,
            "not_a_return_guarantee": True,
        },
        "blocker_state": {
            "state": "akber_review_required",
            "blockers": [],
            "router_eligible": False,
        },
        "paperability": {
            "state": "direct_proxy_available_review_required",
            "execution_proxy": contract.get("execution_proxy") or instrument,
            "paper_route_required": "guarded_alpaca_paper_via_paperops",
            "paper_order_allowed": False,
        },
        "freshness": {
            "created_at": generated_at,
            "expires_at": _expiry(generated_at, horizon),
            "latest_supporting_sample": candidate.get("latest_observation_at"),
            "expiry_requires_new_evidence": True,
        },
        "akber_review_allowed": True,
        "qualified_setup_created": False,
        "trade_candidate_created": False,
        "paper_order_created": False,
        "proof_credit_allowed": False,
        "authority": qeg_authority(governed_projection=True),
    }


def build_graph_active_discovery(settings: Settings | None = None) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    generated_at = now_iso()
    queue = read_json(runtime / ACTIONABILITY_QUEUE_ARTIFACT)
    patterns = read_json(runtime / PATTERN_CANDIDATES_ARTIFACT)
    foundry = read_json(runtime / STRATEGY_VERSIONS_ARTIFACT)
    admissions = read_json(runtime / PAPER_ADMISSION_ARTIFACT)
    market_context = read_json(runtime / "market_context_packet.json")
    mirror = read_json(runtime / "alpaca_paper_mirror.json")
    direction_rows = read_jsonl(runtime / "qadam_direction_resolutions.jsonl")
    directions = _direction_index(direction_rows)
    candidate_index = _candidate_index(patterns)
    version_by_pattern = {
        str(row.get("pattern_relationship_id")): row
        for row in foundry.get("versions") or []
        if row.get("pattern_relationship_id")
    }
    admission_by_version = {
        str(row.get("strategy_version_id")): row
        for row in admissions.get("decisions") or []
        if row.get("strategy_version_id") and row.get("paper_strategy_admitted") is True
    }
    generation_inputs = {
        "queue": queue.get("generated_at"),
        "patterns": patterns.get("generated_at"),
        "foundry": foundry.get("generated_at"),
        "admissions": admissions.get("generated_at"),
        "market_context": market_context.get("generated_at"),
        "mirror": mirror.get("generated_at"),
    }
    decision_generation_id = stable_id("qeg-active-discovery-generation", sha256_json(generation_inputs))

    hypotheses: list[dict[str, Any]] = []
    hypothesis_by_pattern: dict[str, dict[str, Any]] = {}
    for queue_row in queue.get("rows") or []:
        pattern_id = str(queue_row.get("pattern_relationship_id") or "")
        candidate = candidate_index.get(pattern_id, {})
        version = version_by_pattern.get(pattern_id)
        if not version:
            continue
        admission = admission_by_version.get(str(version.get("strategy_version_id") or ""))
        if not admission:
            continue
        key = (str(candidate.get("strategy_family_id") or ""), str(candidate.get("instrument") or ""))
        direction = directions.get(key, {})
        if direction.get("actionable_direction") not in ACTIONABLE_DIRECTIONS:
            continue
        hypothesis = _qeg_hypothesis(version, candidate, direction, admission, generated_at=generated_at)
        hypotheses.append(hypothesis)
        hypothesis_by_pattern[pattern_id] = hypothesis

    packet_state = build_decision_evidence_packets_from_inputs(
        hypotheses,
        direction_rows,
        read_jsonl(runtime / "qadam_current_event_triggers.jsonl"),
        read_jsonl(runtime / "qadam_current_regime_observations.jsonl"),
        read_jsonl(runtime / "qadam_current_market_dislocations.jsonl"),
        current_decision_artifacts(settings),
        generated_at=generated_at,
    )
    packets = packet_state.get("packets") or []
    packet_by_hypothesis = {
        str(row.get("hypothesis_id")): row for row in packets if row.get("hypothesis_id")
    }
    akber_inputs: list[dict[str, Any]] = []
    akber_results: list[dict[str, Any]] = []
    for hypothesis in hypotheses:
        packet = packet_by_hypothesis.get(str(hypothesis.get("hypothesis_id") or ""))
        if not packet:
            continue
        context = dict(packet.get("akber_context") or {})
        context["_decision_evidence_packet_id"] = packet.get("decision_evidence_packet_id")
        context["_decision_generation_id"] = packet.get("decision_generation_id")
        akber_input = build_akber_input(hypothesis, context, generated_at=generated_at, strict_provenance=True)
        akber_inputs.append(akber_input)
        akber_results.append(evaluate_akber_input(akber_input))

    akber_by_hypothesis = {
        str(row.get("hypothesis_id")): row for row in akber_results if row.get("hypothesis_id")
    }
    packet_rejection_by_hypothesis = {
        str(row.get("hypothesis_id")): row
        for row in packet_state.get("rejections") or []
        if row.get("hypothesis_id")
    }
    foundry_rejections = {
        str(row.get("pattern_relationship_id")): row
        for row in foundry.get("rejections") or []
        if row.get("pattern_relationship_id")
    }
    evaluations: list[dict[str, Any]] = []
    for queue_row in queue.get("rows") or []:
        pattern_id = str(queue_row.get("pattern_relationship_id") or "")
        candidate = candidate_index.get(pattern_id, {})
        hypothesis = hypothesis_by_pattern.get(pattern_id)
        result = akber_by_hypothesis.get(str((hypothesis or {}).get("hypothesis_id") or ""), {})
        direction = directions.get(
            (str(candidate.get("strategy_family_id") or ""), str(candidate.get("instrument") or "")),
            {},
        )
        reasons: list[str] = []
        hold_type: str | None = "missing_not_adverse"
        if not hypothesis:
            rejection = foundry_rejections.get(pattern_id, {})
            reasons.extend(str(item) for item in rejection.get("reasons") or [])
            if not reasons:
                reasons.append("strategy_version_not_admitted")
            final_state = "akber_not_entered_research_hold"
            next_action = "resolve the typed strategy-admission blockers, then rebuild a same-generation decision packet"
            stages = {
                "context": "pass" if candidate.get("source_path") and candidate.get("score_id") else "hold_missing_context",
                "catalyst": "pass" if candidate.get("current_trigger_active") else "hold_missing_context",
                "confirmation": "hold_missing_context",
                "risk": "hold_missing_context",
                "execution": "hold_missing_context",
                "postmortem_learning": "ready_to_record",
            }
        elif not result:
            packet_rejection = packet_rejection_by_hypothesis.get(str(hypothesis.get("hypothesis_id") or ""), {})
            reasons.extend(str(item) for item in packet_rejection.get("reasons") or ["same_generation_decision_packet_missing"])
            final_state = "akber_not_entered_packet_hold"
            next_action = "repair or refresh the same-generation evidence packet, then rerun Akber"
            stages = {
                "context": "hold_missing_context",
                "catalyst": "hold_missing_context",
                "confirmation": "hold_missing_context",
                "risk": "hold_missing_context",
                "execution": "hold_missing_context",
                "postmortem_learning": "ready_to_record",
            }
        else:
            decision = str(result.get("decision") or "hold_missing_context")
            stages = {str(row.get("stage")): str(row.get("state")) for row in result.get("stages") or []}
            reasons.extend(str(item.get("code") or item.get("reason")) for item in result.get("missing_context_reasons") or [])
            reasons.extend(str(item) for item in result.get("hard_vetoes") or [])
            if decision == "pass":
                final_state = "akber_passed_pending_shadow_and_risk"
                next_action = "create a decision-time shadow observation, then run portfolio risk and Router"
                hold_type = None
            elif decision == "veto":
                final_state = "akber_vetoed_adverse_evidence"
                next_action = "retain the veto for attribution and wait for a materially new setup"
                hold_type = "adverse"
            elif decision == "watchlist_inactive_trigger":
                final_state = "akber_watchlist_trigger_inactive"
                next_action = "keep the strategy version inactive until a new provider-backed trigger appears"
            else:
                final_state = "akber_held_missing_context"
                next_action = "collect the named current evidence fields and rerun the same strategy version"
        evaluations.append(
            {
                "evaluation_id": stable_id("qeg-active-discovery", decision_generation_id, pattern_id),
                "decision_generation_id": decision_generation_id,
                "queue_rank": queue_row.get("queue_rank"),
                "pattern_relationship_id": pattern_id,
                "hypothesis_id": (hypothesis or {}).get("hypothesis_id"),
                "strategy_version_id": (hypothesis or {}).get("strategy_version_id"),
                "strategy_family_id": candidate.get("strategy_family_id"),
                "instrument": candidate.get("instrument"),
                "research_rank": candidate.get("research_rank"),
                "actionability_rank": candidate.get("actionability_rank"),
                "direction": direction.get("actionable_direction") or "abstain_direction_unresolved",
                "direction_resolution_id": direction.get("direction_resolution_id"),
                "akber_result_id": result.get("akber_result_id"),
                "akber_stage_states": stages,
                "final_state": final_state,
                "hold_type": hold_type,
                "reasons": sorted(set(filter(None, reasons))),
                "next_action": next_action,
                "strategy_admitted": hypothesis is not None,
                "trade_candidate_created": False,
                "paper_order_created": False,
                "authority": qeg_authority(),
            }
        )

    errors: list[str] = []
    if queue.get("status") != "complete":
        errors.append("actionability_queue_not_complete")
    if foundry.get("status") != "passed":
        errors.append("strategy_foundry_not_passed")
    if admissions.get("status") != "passed":
        errors.append("paper_strategy_admission_not_passed")
    errors.extend(f"decision_packet:{error}" for error in validate_decision_evidence_packets(packet_state))
    if any(row.get("trade_candidate_created") or row.get("paper_order_created") for row in evaluations):
        errors.append("active_discovery_authority_violation")
    if len(evaluations) != len(queue.get("rows") or []):
        errors.append("top_k_queue_not_fully_processed")

    store = AtomicArtifactStore(runtime)
    store.write_jsonl(QEG_HYPOTHESES_ARTIFACT, hypotheses)
    store.write_jsonl(QEG_DECISION_PACKETS_ARTIFACT, packets)
    store.write_jsonl(QEG_AKBER_INPUTS_ARTIFACT, akber_inputs)
    store.write_jsonl(QEG_AKBER_RESULTS_ARTIFACT, akber_results)
    payload = {
        "schema_version": "qadam_graph_active_discovery.v2",
        "artifact_type": "qadam_graph_active_discovery_funnel",
        "generated_at": generated_at,
        "status": "passed" if not errors else "blocked",
        "decision_generation_id": decision_generation_id,
        "generation_inputs": generation_inputs,
        "queue_count": len(queue.get("rows") or []),
        "evaluated_count": len(evaluations),
        "admitted_strategy_count": len(hypotheses),
        "decision_packet_count": len(packets),
        "decision_packet_rejection_count": len(packet_state.get("rejections") or []),
        "akber_entered_count": len(akber_results),
        "akber_pass_count": sum(row.get("decision") == "pass" for row in akber_results),
        "paper_review_candidate_count": 0,
        "final_state_counts": dict(Counter(row["final_state"] for row in evaluations)),
        "evaluations": evaluations,
        "packet_rejections": packet_state.get("rejections") or [],
        "available_evidence_reported_missing_due_to_contract_shape_count": 0,
        "first_hold_stopped_queue": False,
        "hard_fields_never_substituted": [
            "current_price",
            "spread",
            "liquidity",
            "positive_expectancy_after_costs",
            "invalidation",
            "route",
            "risk_capacity",
        ],
        "threshold_recalibration_state": "existing_profile_ablations_retained_no_unproven_threshold_change",
        "downstream_contract": {
            "shadow_reader": QEG_HYPOTHESES_ARTIFACT,
            "akber_results": QEG_AKBER_RESULTS_ARTIFACT,
            "risk_and_router_remain_canonical_owners": True,
            "paperops_route": "scripts/run_paperops_autonomous_pass.py",
        },
        "validation_errors": errors,
        "authority": qeg_authority(),
    }
    write_json_atomic(runtime / ACTIVE_DISCOVERY_FUNNEL_ARTIFACT, payload)
    write_phase_status(
        "QEG-11",
        status=payload["status"],
        implementation_complete=not errors,
        empirical_state=(
            "akber_passed_pending_shadow_and_risk"
            if payload["akber_pass_count"]
            else "top_k_evaluated_no_current_akber_pass"
        ),
        artifacts=[
            ACTIVE_DISCOVERY_FUNNEL_ARTIFACT,
            QEG_HYPOTHESES_ARTIFACT,
            QEG_DECISION_PACKETS_ARTIFACT,
            QEG_AKBER_INPUTS_ARTIFACT,
            QEG_AKBER_RESULTS_ARTIFACT,
        ],
        blockers=errors,
        settings=settings,
    )
    return payload, errors


def validate_graph_active_discovery(settings: Settings | None = None) -> list[str]:
    runtime = runtime_dir(settings)
    payload = read_json(runtime / ACTIVE_DISCOVERY_FUNNEL_ARTIFACT)
    errors = list(payload.get("validation_errors") or [])
    if payload.get("evaluated_count") != payload.get("queue_count"):
        errors.append("top_k_queue_not_fully_processed")
    if payload.get("available_evidence_reported_missing_due_to_contract_shape_count") != 0:
        errors.append("evidence_contract_shape_loss")
    hypotheses = read_jsonl(runtime / QEG_HYPOTHESES_ARTIFACT)
    inputs = read_jsonl(runtime / QEG_AKBER_INPUTS_ARTIFACT)
    results = read_jsonl(runtime / QEG_AKBER_RESULTS_ARTIFACT)
    if len(inputs) != len(results):
        errors.append("qeg_akber_input_result_count_mismatch")
    admitted_hypothesis_ids = {
        str(row.get("hypothesis_id")) for row in hypotheses if row.get("akber_review_allowed") is True
    }
    if any(str(row.get("hypothesis_id")) not in admitted_hypothesis_ids for row in results):
        errors.append("qeg_akber_result_without_admitted_hypothesis")
    for row in payload.get("evaluations") or []:
        if row.get("hold_type") not in {"missing_not_adverse", "adverse", None}:
            errors.append("hold_type_not_typed")
        if row.get("trade_candidate_created") or row.get("paper_order_created"):
            errors.append("active_discovery_authority_violation")
    for row in results:
        if row.get("execution_approval_created") or row.get("paper_order_created"):
            errors.append("qeg_akber_authority_violation")
    return sorted(set(errors))
