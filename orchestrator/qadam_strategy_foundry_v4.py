"""QEG-10 immutable graph-backed strategy versions and rejections."""

from __future__ import annotations

from collections import Counter
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_operator_ready_common import now_iso, read_json, read_jsonl, runtime_dir, sha256_json, write_json_atomic
from orchestrator.qadam_qeg_common import EXPERIMENT_BRIDGE_ARTIFACT, PATTERN_CANDIDATES_ARTIFACT, STRATEGY_VERSIONS_ARTIFACT, qeg_authority, stable_id, write_phase_status
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
    policy = read_json(runtime / "qadam_experimental_paper_policy.json")
    strategy_evidence = read_json(runtime / "qadam_strategy_evidence_map_v3.json")
    edges = read_jsonl(runtime / "qadam_edge_registry.jsonl")
    directions = _direction_index(read_jsonl(runtime / "qadam_direction_resolutions.jsonl"))
    candidates = patterns.get("candidates") if isinstance(patterns.get("candidates"), list) else []
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
    graph_records: list[dict[str, Any]] = []

    for candidate in candidates:
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
        blockers: list[str] = []
        evidence_class = "validated_paper_strategy" if edge else "experimental_unvalidated"
        if not edge:
            if float(candidate.get("research_rank") or 0) < minimum_score:
                blockers.append("research_score_below_discovery_micro_minimum")
            if not candidate.get("current_trigger_active"):
                blockers.append("current_profile_trigger_inactive")
            if direction.get("actionable_direction") not in ACTIONABLE_DIRECTIONS:
                blockers.append("direction_unresolved")
            if provisional_net is None:
                blockers.append("positive_provisional_after_cost_expectancy_missing")
            if candidate.get("actionability_blockers"):
                blockers.extend(str(item) for item in candidate.get("actionability_blockers") or [])
            if not experiment or not experiment.get("preregistered_before_outcome"):
                blockers.append("frozen_experiment_preregistration_missing")
        elif str(edge.get("status") or edge.get("edge_state") or "") not in {
            "validated", "validated_edge", "admitted", "active"
        }:
            blockers.append("edge_not_in_validated_state")

        blockers = sorted(set(blockers))
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
            "cost_model": "current spread plus slippage and proxy basis-risk haircut",
            "akber_requirements": ["context", "catalyst", "confirmation", "risk", "execution", "postmortem_learning"],
            "paper_risk_tier": "validated_paper" if edge else "discovery_micro",
            "maximum_notional_usd": 5000.0 if edge else 1000.0,
            "exposure_cluster": candidate.get("market_family") or family,
            "activation_rule": "deterministic paper admission only",
            "expiry_rule": "expire with current trigger or admission receipt",
            "rollback_rule": "return to research on any stale, adverse, or lineage failure",
            "monitoring_rule": "same-generation evidence and canonical lifecycle polling",
            "experimental_economics": {
                "provisional_net_expectancy_after_costs": provisional_net,
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
    payload = {
        "schema_version": "qadam_strategy_foundry_v4.v1",
        "artifact_type": "qadam_strategy_foundry_v4",
        "generated_at": generated_at,
        "status": "passed" if not errors else "blocked",
        "candidate_count": len(candidates),
        "strategy_version_count": len(versions),
        "core_refinement_count": sum(row["contract"]["destination"] == "core_family_refinement" for row in versions),
        "emerging_strategy_count": sum(row["contract"]["destination"] == "emerging_pattern_sourced_strategy" for row in versions),
        "rejection_count": len(rejections),
        "rejection_reason_counts": dict(Counter(reason for row in rejections for reason in row["reasons"])),
        "versions": versions,
        "rejections": rejections,
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
