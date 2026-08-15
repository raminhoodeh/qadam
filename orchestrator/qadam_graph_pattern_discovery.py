"""QEG-7 graph-backed pattern discovery over Qadam's scored universe."""

from __future__ import annotations

from collections import Counter
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_discovery_micro_conversion import (
    adapt_discovery_blockers,
    evidence_profile_for_strategy,
)
from orchestrator.qadam_operator_ready_common import now_iso, read_json, read_jsonl, runtime_dir, write_json_atomic
from orchestrator.qadam_qeg_common import PATTERN_CANDIDATES_ARTIFACT, qeg_authority, stable_id, write_phase_status
from orchestrator.qadam_temporal_graph_contracts import build_edge, build_node
from orchestrator.qadam_temporal_graph_store import TemporalGraphStore


def _question(row: dict[str, Any]) -> str:
    family = str(row.get("strategy_label") or row.get("market_family") or "this evidence relationship")
    instrument = str(row.get("instrument") or "the watched market")
    horizon = str(row.get("horizon_hypothesis") or "the declared horizon").replace("_", " ")
    return f"Does {family.lower()} repeatedly precede a tradeable move in {instrument} over {horizon}?"


def _mechanism(row: dict[str, Any]) -> str:
    label = str(row.get("strategy_label") or row.get("market_family") or "cross-source evidence")
    return f"Independent observations associated with {label} may reach listed-market pricing at different speeds."


def _actionability(
    row: dict[str, Any],
    *,
    profile_trigger_active: bool,
    sources: list[dict[str, Any]],
    policy: dict[str, Any],
) -> tuple[float, list[str], dict[str, Any]]:
    score = float(row.get("raw_pattern_score") or 0)
    missing = [str(item) for item in row.get("missing_critical_features", [])]
    missing, support = adapt_discovery_blockers(missing, sources, policy)
    features = row.get("features") if isinstance(row.get("features"), dict) else {}
    components = {
        "current_trigger": 1.0 if profile_trigger_active else 0.0,
        "complete_score_features": 1.0 if not missing else 0.0,
        "paperability": float(features.get("paperability_context") or 0),
        "market_price": float(features.get("current_market_price") or 0),
        "liquidity_or_flow": float(features.get("volume_or_flow_context") or 0),
    }
    value = score * (
        0.25 + 0.25 * components["current_trigger"] + 0.20 * components["complete_score_features"]
        + 0.10 * components["paperability"] + 0.10 * components["market_price"]
        + 0.10 * components["liquidity_or_flow"]
    )
    blockers = list(missing)
    if not profile_trigger_active:
        blockers.append("no_current_directional_trigger")
    return round(min(1.0, value), 6), sorted(set(blockers)), support


def _active_trigger_families(runtime) -> set[str]:
    active: set[str] = set()
    specifications = (
        ("qadam_current_event_triggers.jsonl", "trigger_state", {"active"}),
        (
            "qadam_current_regime_observations.jsonl",
            "regime_state",
            {"active", "active_long", "active_short"},
        ),
        ("qadam_current_market_dislocations.jsonl", "measurement_state", {"active"}),
    )
    for artifact, state_field, active_values in specifications:
        for row in read_jsonl(runtime / artifact):
            if str(row.get(state_field) or "") in active_values and row.get(
                "strategy_family_id"
            ):
                active.add(str(row["strategy_family_id"]))
    return active


def build_graph_patterns(settings: Settings | None = None, *, candidate_limit: int = 20) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    scores = [
        row for row in read_jsonl(runtime / "qadam_pattern_score_v3_records.jsonl")
        if not row.get("negative_control") and float(row.get("raw_pattern_score") or 0) > 0
    ]
    policy = read_json(runtime / "qadam_experimental_paper_policy.json")
    active_trigger_families = _active_trigger_families(runtime)
    candidates: list[dict[str, Any]] = []
    graph_records: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in sorted(scores, key=lambda item: float(item.get("raw_pattern_score") or 0), reverse=True):
        key = (str(row.get("strategy_family_id") or row.get("market_family")), str(row.get("instrument")))
        if key in seen:
            continue
        seen.add(key)
        sources = [
            {
                "source_key": item.get("source_key"),
                "fresh": bool(item.get("fresh")),
                "quorum_eligible": bool(item.get("quorum_eligible")),
                "independence_cluster_id": item.get("independence_cluster_id"),
                "available_at": item.get("available_at"),
                "trust_score": item.get("trust_score"),
                "mapping_class": item.get("mapping_class"),
            }
            for item in row.get("feature_inputs", [])
            if isinstance(item, dict) and item.get("source_key")
        ]
        family = str(row.get("strategy_family_id") or "")
        profile_trigger_active = family in active_trigger_families
        actionability, blockers, support = _actionability(
            row,
            profile_trigger_active=profile_trigger_active,
            sources=sources,
            policy=policy,
        )
        horizon = str(row.get("horizon_hypothesis") or "5d_forward")
        candidate_id = stable_id("qeg-pattern", key[0], key[1], horizon)
        candidate = {
            "pattern_relationship_id": candidate_id,
            "score_id": row.get("score_id"),
            "research_question": _question(row),
            "economic_mechanism": _mechanism(row),
            "alternative_explanations": ["broad market beta", "already-priced public information", "shared upstream source dependence"],
            "falsifier": "The relationship fails untouched holdout, costs, stability, or forward observation.",
            "instrument": row.get("instrument"),
            "market_family": row.get("market_family"),
            "strategy_family_id": row.get("strategy_family_id"),
            "strategy_label": row.get("strategy_label"),
            "research_rank": float(row.get("raw_pattern_score") or 0),
            "research_rank_type": "pattern_score_not_probability",
            "actionability_rank": actionability,
            "actionability_blockers": blockers,
            "current_trigger_active": profile_trigger_active,
            "profile_specific_current_trigger_active": profile_trigger_active,
            "source_path": sources,
            "source_count": len(sources),
            "fresh_source_count": sum(item["fresh"] for item in sources),
            "independent_source_cluster_count": len({item["independence_cluster_id"] for item in sources if item["independence_cluster_id"]}),
            "first_observation_at": min((item["available_at"] for item in sources if item["available_at"]), default=None),
            "latest_observation_at": max((item["available_at"] for item in sources if item["available_at"]), default=None),
            "trusted_support": support,
            "evidence_profile": evidence_profile_for_strategy(family),
            "horizon": horizon,
            "novelty_state": "candidate_requires_experiment_memory_check",
            "paperability_state": "research_only_not_yet_trade_candidate",
            "next_action": "build preregistered historical and forward experiment" if not blockers else f"resolve: {', '.join(blockers[:3])}",
            "is_strategy": False,
            "is_trade_candidate": False,
            "paper_order_created": False,
            "authority": qeg_authority(),
        }
        candidates.append(candidate)
        pattern_node = build_node(
            "pattern_relationship", candidate_id, layer="inferred",
            evidence_state="interesting_unvalidated", payload=candidate,
            available_at=row.get("scoring_as_of") or row.get("generated_at"),
            source_artifact="data/runtime/qadam_pattern_score_v3_records.jsonl",
            node_id=candidate_id,
        )
        graph_records.append(pattern_node)
        instrument_node_id = stable_id(
            "prediction_contract" if ":" in str(row.get("instrument")) else "instrument",
            row.get("instrument"),
        )
        graph_records.append(
            build_edge(
                "affects", pattern_node["node_id"], instrument_node_id, layer="inferred",
                evidence_state="interesting_unvalidated", payload={"direction": row.get("direction_hypothesis")},
                available_at=pattern_node["available_at"],
                source_artifact="data/runtime/qadam_pattern_score_v3_records.jsonl",
            )
        )
        for source in sources:
            graph_records.append(
                build_edge(
                    "supports", stable_id("source_feed", source["source_key"]), pattern_node["node_id"],
                    layer="inferred", evidence_state="interesting_unvalidated",
                    payload={"fresh": source["fresh"], "quorum_eligible": source["quorum_eligible"]},
                    available_at=source["available_at"] or pattern_node["available_at"],
                    source_artifact="data/runtime/qadam_pattern_score_v3_records.jsonl",
                )
            )
        if len(candidates) >= candidate_limit:
            break
    candidates.sort(key=lambda row: (row["actionability_rank"], row["research_rank"]), reverse=True)
    payload = {
        "schema_version": "qadam_graph_pattern_discovery.v1",
        "artifact_type": "qadam_graph_pattern_candidates",
        "generated_at": now_iso(),
        "status": "complete" if candidates else "complete_no_positive_score_rows",
        "full_universe_search_scope": {"source_count": 41, "instrument_count": 19, "pair_count": 779},
        "candidate_count": len(candidates),
        "strategy_agnostic_candidate_count": sum(not row.get("strategy_family_id") for row in candidates),
        "active_trigger_candidate_count": sum(row["current_trigger_active"] for row in candidates),
        "candidates": candidates,
        "patterns_are_not_strategies": True,
        "authority": qeg_authority(),
    }
    errors: list[str] = []
    if len({row["pattern_relationship_id"] for row in candidates}) != len(candidates):
        errors.append("duplicate_pattern_identity")
    if any(row["is_strategy"] or row["is_trade_candidate"] or row["paper_order_created"] for row in candidates):
        errors.append("pattern_authority_boundary_violation")
    store = TemporalGraphStore(settings)
    append = store.append(graph_records) if graph_records else {"written": 0, "duplicates": 0}
    manifest = store.rebuild()
    payload["graph_records_written"] = append["written"]
    payload["graph_generation_id"] = manifest["generation_id"]
    write_json_atomic(runtime / PATTERN_CANDIDATES_ARTIFACT, payload)
    return payload, errors
