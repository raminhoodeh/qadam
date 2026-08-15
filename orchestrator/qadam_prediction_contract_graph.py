"""Deterministic cross-venue compatibility graph for prediction contracts."""

from __future__ import annotations

import re
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_prediction_market_normalization import normalize_prediction_contracts
from orchestrator.qadam_qualitative_common import (
    PREDICTION_GRAPH_ARTIFACT,
    now_iso,
    public_authority,
    runtime_dir,
    stable_id,
)

STOPWORDS = {"will", "the", "a", "an", "by", "in", "of", "to", "and", "or", "be", "is", "on", "for"}


def _tokens(question: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", question.lower()) if token not in STOPWORDS and len(token) > 2}


def build_prediction_contract_graph(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[str]]:
    contracts, _, errors = normalize_prediction_contracts(settings)
    kalshi = [row for row in contracts if row["venue"] == "kalshi"]
    polymarket = [row for row in contracts if row["venue"] == "polymarket"]
    edges: list[dict[str, Any]] = []
    for left in kalshi:
        left_tokens = _tokens(str(left.get("canonical_question") or ""))
        if not left_tokens:
            continue
        ranked: list[tuple[float, dict[str, Any]]] = []
        for right in polymarket:
            right_tokens = _tokens(str(right.get("canonical_question") or ""))
            union = left_tokens | right_tokens
            similarity = len(left_tokens & right_tokens) / len(union) if union else 0.0
            if similarity >= 0.35:
                ranked.append((similarity, right))
        for similarity, right in sorted(ranked, key=lambda item: item[0], reverse=True)[:3]:
            edges.append({
                "edge_id": stable_id("prediction-compatibility", left["contract_id"], right["contract_id"]),
                "from_contract_id": left["contract_id"],
                "to_contract_id": right["contract_id"],
                "relationship": "candidate_cross_venue_equivalence",
                "lexical_similarity": round(similarity, 6),
                "semantic_compatibility": "requires_human_or_model_semantics_review",
                "deterministic_arbitrage_claimed": False,
                "source_independence_state": "same_underlying_event_not_independent_fact",
                "authority": public_authority(),
            })
    graph = {
        "schema_version": "qadam_prediction_contract_graph.v1",
        "artifact_type": "qadam_prediction_contract_graph",
        "generated_at": now_iso(),
        "status": "ready" if contracts else "blocked_no_contracts",
        "node_count": len(contracts),
        "edge_count": len(edges),
        "nodes": [{"contract_id": row["contract_id"], "venue": row["venue"], "question": row["canonical_question"]} for row in contracts],
        "edges": edges,
        "false_deterministic_arbitrage_count": 0,
        "authority": public_authority(),
    }
    AtomicArtifactStore(runtime_dir(settings)).write_json(PREDICTION_GRAPH_ARTIFACT, graph)
    return graph, errors


__all__ = ["build_prediction_contract_graph"]
