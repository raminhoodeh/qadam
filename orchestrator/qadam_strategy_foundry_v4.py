"""QEG-10 immutable graph-backed strategy versions and rejections."""

from __future__ import annotations

from collections import Counter
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_discovery_micro_conversion import (
    CURRENT_EXPECTANCY_ARTIFACT,
    build_current_expectancy_v2,
    market_records,
)
from orchestrator.qadam_operator_ready_common import now_iso, read_json, read_jsonl, runtime_dir, sha256_json, write_json_atomic
from orchestrator.qadam_qeg_common import ACTIONABILITY_QUEUE_ARTIFACT, EXPERIMENT_BRIDGE_ARTIFACT, PATTERN_CANDIDATES_ARTIFACT, STRATEGY_VERSIONS_ARTIFACT, qeg_authority, stable_id, write_phase_status
from orchestrator.qadam_temporal_graph_contracts import build_edge, build_node
from orchestrator.qadam_temporal_graph_store import TemporalGraphStore

CORE_FAMILIES = {
    "crude_oil_energy_security_disruption",
    "defence_repricing_geopolitical_watch",
    "prediction_market_geopolitical_dislocation",
    "semiconductor_policy_options_asymmetry",
    "silver_macro_liquidity_stress",
}
ACTIONABLE_DIRECTIONS = {"long", "short"}


def strategy_destination(family: str) -> str:
    return "core_family_refinement" if family in CORE_FAMILIES else "emerging_pattern_sourced_strategy"


def _direction_index(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (str(row.get("strategy_family_id") or ""), str(row.get("instrument") or ""))
        if key not in result or str(row.get("generated_at") or "") > str(result[key].get("generated_at") or ""):
            result[key] = row
    return result


def _provisional_net_expectancy(
    historical_result: dict[str, Any], actionable_direction: str
) -> float | None:
    """Shrink a rejected historical mean and preserve its observed sign.

    The historical strategy evidence is a signed forward return. A positive
    result can support a bounded long experiment; a short experiment requires
    a negative historical mean. This estimate remains research context, never
    validated expectancy or execution authority.
    """

    historical_net = historical_result.get("mean_net_return")
    if historical_net is None or actionable_direction not in ACTIONABLE_DIRECTIONS:
        return None
    signed_return = float(historical_net)
    direction_adjusted = (
        signed_return if actionable_direction == "long" else -signed_return
    )
    return direction_adjusted * 0.25 if direction_adjusted > 0 else None


def build_strategy_foundry_v4(settings: Settings | None = None) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    generated_at = now_iso()
    patterns = read_json(runtime / PATTERN_CANDIDATES_ARTIFACT)
    bridge = read_json(runtime / EXPERIMENT_BRIDGE_ARTIFACT)
    queue = read_json(runtime / ACTIONABILITY_QUEUE_ARTIFACT)
    policy = read_json(runtime / "qadam_experimental_paper_policy.json")
    strategy_evidence = read_json(runtime / "qadam_strategy_evidence_map_v3.json")
    edges = read_jsonl(runtime / "qadam_edge_registry.jsonl")
    directions = _direction_index(read_jsonl(runtime / "qadam_direction_resolutions.jsonl"))
    current_market = market_records(read_json(runtime / "market_context_packet.json"))
    candidates = patterns.get("candidates") if isinstance(patterns.get("candidates"), list) else []
    candidates_by_pattern = {
        str(row.get("pattern_relationship_id") or ""): row
        for row in candidates
        if row.get("pattern_relationship_id")
    }
    queue_rows = queue.get("rows") if isinstance(queue.get("rows"), list) else []
    experiments = {
        str(row.get("pattern_relationship_id")): row
        for row in bridge.get("experiments") or []
        if row.get("pattern_relationship_id")
    }
    edge_index = {
        (str(row.get("strategy_family_id") or ""), str(row.get("instrument") or "")): row
        for row in edges
        if row.get("validated_edge_id") or row.get("edge_id")
    }
    evidence_by_family = {
        str(row.get("strategy_family_id") or ""): row
        for row in strategy_evidence.get("strategies") or []
        if isinstance(row, dict) and row.get("strategy_family_id")
    }
    micro = policy.get("discovery_micro_admission") if isinstance(policy.get("discovery_micro_admission"), dict) else {}
    minimum_score = float(micro.get("minimum_research_score") or 0.45)
    versions: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []
    research_holds: list[dict[str, Any]] = []
    expectancy_records: list[dict[str, Any]] = []
    graph_records: list[dict[str, Any]] = []

    for queue_row in queue_rows:
        pattern_id = str(queue_row.get("pattern_relationship_id") or "")
        candidate = candidates_by_pattern.get(pattern_id, {})
        if not candidate:
            rejections.append(
                {
                    "rejection_id": stable_id("qeg-strategy-rejection", pattern_id, "queue_candidate_missing"),
                    "pattern_relationship_id": pattern_id,
                    "strategy_family_id": queue_row.get("strategy_family_id"),
                    "instrument": queue_row.get("instrument"),
                    "destination": strategy_destination(str(queue_row.get("strategy_family_id") or "")),
                    "reasons": ["actionability_queue_candidate_missing"],
                    "state": "rejected_before_akber",
                    "next_action": "repair producer-consumer actionability contract",
                    "is_trade_candidate": False,
                    "paper_order_created": False,
                    "authority": qeg_authority(),
                }
            )
            continue
        if queue_row.get("state") != "ready_for_preregistered_experiment":
            research_holds.append(
                {
                    "hold_id": stable_id("qeg-strategy-hold", pattern_id, queue_row.get("blockers")),
                    "pattern_relationship_id": pattern_id,
                    "strategy_family_id": candidate.get("strategy_family_id"),
                    "instrument": candidate.get("instrument"),
                    "state": "research_hold_before_foundry",
                    "reasons": list(queue_row.get("blockers") or []),
                    "next_action": queue_row.get("next_action"),
                    "is_trade_candidate": False,
                    "paper_order_created": False,
                    "authority": qeg_authority(),
                }
            )
            continue
        family = str(candidate.get("strategy_family_id") or "no_core_family_fit")
        instrument = str(candidate.get("instrument") or "")
        experiment = experiments.get(str(candidate.get("pattern_relationship_id") or ""))
        edge = edge_index.get((family, instrument))
        direction = directions.get((family, instrument), {})
        family_evidence = evidence_by_family.get(family, {})
        best_rejected = family_evidence.get("best_observed_rejected_result")
        best_rejected = best_rejected if isinstance(best_rejected, dict) else {}
        provisional_net = _provisional_net_expectancy(
            best_rejected,
            str(direction.get("actionable_direction") or ""),
        )
        current_expectancy = build_current_expectancy_v2(
            candidate,
            direction,
            current_market.get(instrument, {}),
            best_rejected,
            policy,
            generated_at=generated_at,
        )
        expectancy_records.append(current_expectancy)
        blockers: list[str] = []
        evidence_class = "validated_paper_strategy" if edge else "experimental_unvalidated"
        if not edge:
            if float(candidate.get("research_rank") or 0) < minimum_score:
                blockers.append("research_score_below_discovery_micro_minimum")
            if not candidate.get("current_trigger_active"):
                blockers.append("current_profile_trigger_inactive")
            if direction.get("actionable_direction") not in ACTIONABLE_DIRECTIONS:
                blockers.append("direction_unresolved")
            if candidate.get("actionability_blockers"):
                blockers.extend(str(item) for item in candidate.get("actionability_blockers") or [])
            if not experiment or not experiment.get("preregistered_before_outcome"):
                blockers.append("frozen_experiment_preregistration_missing")
            if current_expectancy.get("ready_for_discovery_micro_review") is not True:
                blockers.extend(str(item) for item in current_expectancy.get("blockers") or [])
        elif str(edge.get("status") or edge.get("edge_state") or "") not in {
            "validated", "validated_edge", "admitted", "active"
        }:
            blockers.append("edge_not_in_validated_state")

        blockers = sorted(set(blockers))
        temporary_blockers = {
            "actionable_current_market_context_missing",
            "current_price_missing",
            "current_volatility_missing",
            "current_spread_missing",
            "independent_live_market_confirmation_missing",
            "direction_unresolved",
        }
        if blockers and set(blockers).issubset(temporary_blockers):
            research_holds.append(
                {
                    "hold_id": stable_id("qeg-strategy-hold", pattern_id, blockers),
                    "pattern_relationship_id": pattern_id,
                    "strategy_family_id": family,
                    "instrument": instrument,
                    "state": "waiting_for_current_tradeability_context",
                    "reasons": blockers,
                    "next_action": "retry on the next fresh actionable market observation",
                    "current_expectancy_id": current_expectancy.get("current_expectancy_id"),
                    "is_trade_candidate": False,
                    "paper_order_created": False,
                    "authority": qeg_authority(),
                }
            )
            continue
        if blockers:
            rejections.append(
                {
                    "rejection_id": stable_id("qeg-strategy-rejection", candidate.get("pattern_relationship_id"), blockers),
                    "pattern_relationship_id": candidate.get("pattern_relationship_id"),
                    "strategy_family_id": family,
                    "instrument": instrument,
                    "destination": strategy_destination(family),
                    "reasons": blockers,
                    "state": "rejected_before_akber",
                    "next_action": "resolve typed evidence blockers or wait for a new independent trigger",
                    "is_trade_candidate": False,
                    "paper_order_created": False,
                    "authority": qeg_authority(),
                }
            )
            continue

        version_contract = {
            "strategy_family_id": family,
            "destination": strategy_destination(family),
            "instrument": instrument,
            "execution_proxy": instrument,
            "direction_rule": direction.get("actionable_direction") if not edge else "resolved_at_decision_time",
            "entry_rule": "fresh profile-specific trigger plus independent current market confirmation",
            "invalidation_rule": "source correction, trigger expiry, adverse price confirmation, or risk veto",
            "exit_rule": "time horizon, invalidation, risk stop, or governed lifecycle close",
            "time_horizon": candidate.get("horizon") or "5d_forward",
            "cost_model": "current_expectancy_v2_current_spread_slippage_and_proxy_basis",
            "akber_requirements": ["context", "catalyst", "confirmation", "risk", "execution", "postmortem_learning"],
            "paper_risk_tier": "validated_paper" if edge else "discovery_micro",
            "maximum_notional_usd": (
                min(
                    float(policy.get("risk", {}).get("absolute_trade_ceiling_usd") or 5000.0),
                    float(policy.get("risk", {}).get("discovery_target_notional_usd", {}).get("maximum") or 1000.0),
                )
                if not edge
                else float(policy.get("risk", {}).get("absolute_trade_ceiling_usd") or 5000.0)
            ),
            "exposure_cluster": candidate.get("market_family") or family,
            "activation_rule": "deterministic paper admission only",
            "expiry_rule": "expire with current trigger or admission receipt",
            "rollback_rule": "return to research on any stale, adverse, or lineage failure",
            "monitoring_rule": "same-generation evidence and canonical lifecycle polling",
            "experimental_economics": {
                "provisional_net_expectancy_after_costs": provisional_net,
                "current_expectancy_id": current_expectancy.get("current_expectancy_id"),
                "current_expectancy_state": current_expectancy.get("status"),
                "gross_expectancy": current_expectancy.get("economics", {}).get("gross_expectancy"),
                "current_net_expectancy_after_costs": current_expectancy.get("economics", {}).get("net_expectancy"),
                "current_total_cost": current_expectancy.get("economics", {}).get("total_cost"),
                "current_expectancy_source": "provider_backed_decision_time_expectancy_v2",
                "source_hypothesis_id": best_rejected.get("hypothesis_id"),
                "source_method_id": best_rejected.get("method_id"),
                "source_rejection_reasons": best_rejected.get("rejection_reasons", []),
                "shrinkage_multiplier": 0.25 if provisional_net is not None else None,
                "expected_reward_to_risk": 1.50,
                "not_a_validated_expectancy": True,
                "not_a_return_guarantee": True,
            },
        }
        version_id = stable_id(
            "qeg-strategy-version", candidate.get("pattern_relationship_id"), sha256_json(version_contract),
            edge.get("validated_edge_id") if edge else experiment.get("experiment_id"),
        )
        record = {
            "strategy_version_id": version_id,
            "version": 1,
            "created_at": generated_at,
            "immutable_contract_hash": sha256_json(version_contract),
            "contract": version_contract,
            "evidence_class": evidence_class,
            "admission_state": "paper_discovery_eligible",
            "pattern_relationship_id": candidate.get("pattern_relationship_id"),
            "research_goal_id": experiment.get("definition", {}).get("research_goal_id") if experiment else None,
            "experiment_id": experiment.get("experiment_id") if experiment else None,
            "edge_id": edge.get("validated_edge_id") or edge.get("edge_id") if edge else None,
            "score_id": candidate.get("score_id"),
            "direction_resolution_id": direction.get("direction_resolution_id"),
            "evidence_hash": sha256_json({"candidate": candidate, "experiment": experiment, "edge": edge, "direction": direction}),
            "supersedes_strategy_version_id": None,
            "reversible": True,
            "execution_approval_created": False,
            "paper_order_created": False,
            "authority": qeg_authority(),
        }
        versions.append(record)
        graph_records.extend(
            [
                build_node(
                    "strategy_version", version_id, layer="governed", evidence_state="governed_projection",
                    payload=record, available_at=generated_at, source_artifact=f"data/runtime/{STRATEGY_VERSIONS_ARTIFACT}",
                    node_id=version_id,
                ),
                build_edge(
                    "generated_strategy", str(candidate.get("pattern_relationship_id")), version_id,
                    layer="governed", evidence_state="governed_projection",
                    payload={"evidence_class": evidence_class}, available_at=generated_at,
                    source_artifact=f"data/runtime/{STRATEGY_VERSIONS_ARTIFACT}",
                ),
            ]
        )

    errors: list[str] = []
    if bridge.get("status") != "passed":
        errors.append("experiment_bridge_not_passed")
    if any(row.get("paper_order_created") or row.get("execution_approval_created") for row in versions):
        errors.append("strategy_foundry_authority_violation")
    if any(not row.get("immutable_contract_hash") or not row.get("reversible") for row in versions):
        errors.append("strategy_version_not_immutable_or_reversible")
    store = TemporalGraphStore(settings)
    append = store.append(graph_records) if graph_records else {"written": 0}
    manifest = store.rebuild()
    AtomicArtifactStore(runtime).write_jsonl(CURRENT_EXPECTANCY_ARTIFACT, expectancy_records)
    payload = {
        "schema_version": "qadam_strategy_foundry_v4.v1",
        "artifact_type": "qadam_strategy_foundry_v4",
        "generated_at": generated_at,
        "status": "passed" if not errors else "blocked",
        "source_candidate_count": len(candidates),
        "candidate_count": len(queue_rows),
        "queue_ready_count": sum(
            row.get("state") == "ready_for_preregistered_experiment" for row in queue_rows
        ),
        "strategy_version_count": len(versions),
        "core_refinement_count": sum(row["contract"]["destination"] == "core_family_refinement" for row in versions),
        "emerging_strategy_count": sum(row["contract"]["destination"] == "emerging_pattern_sourced_strategy" for row in versions),
        "rejection_count": len(rejections),
        "rejection_reason_counts": dict(Counter(reason for row in rejections for reason in row["reasons"])),
        "research_hold_count": len(research_holds),
        "research_hold_reason_counts": dict(
            Counter(reason for row in research_holds for reason in row["reasons"])
        ),
        "current_expectancy_record_count": len(expectancy_records),
        "current_expectancy_ready_count": sum(
            row.get("ready_for_discovery_micro_review") is True
            for row in expectancy_records
        ),
        "versions": versions,
        "rejections": rejections,
        "research_holds": research_holds,
        "graph_records_written": append["written"],
        "graph_generation_id": manifest.get("generation_id"),
        "validation_errors": errors,
        "authority": qeg_authority(),
    }
    write_json_atomic(runtime / STRATEGY_VERSIONS_ARTIFACT, payload)
    return payload, errors


def validate_strategy_foundry_v4(settings: Settings | None = None) -> list[str]:
    payload = read_json(runtime_dir(settings) / STRATEGY_VERSIONS_ARTIFACT)
    errors = list(payload.get("validation_errors") or [])
    for row in payload.get("versions") or []:
        if sha256_json(row.get("contract") or {}) != row.get("immutable_contract_hash"):
            errors.append("strategy_version_contract_hash_mismatch")
        if row.get("contract", {}).get("maximum_notional_usd", 0) > 5000:
            errors.append("strategy_version_risk_ceiling_expanded")
    if any(row.get("state") != "rejected_before_akber" for row in payload.get("rejections") or []):
        errors.append("weak_strategy_not_rejected_before_akber")
    return sorted(set(errors))
