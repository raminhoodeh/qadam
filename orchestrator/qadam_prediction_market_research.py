"""Belief, liquidity and cross-venue research over prediction-market history."""

from __future__ import annotations

from collections import defaultdict
import math
import statistics
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_prediction_contract_graph import build_prediction_contract_graph
from orchestrator.qadam_prediction_market_normalization import iter_prediction_history, normalize_prediction_contracts
from orchestrator.qadam_qualitative_common import (
    PREDICTION_BELIEFS_ARTIFACT,
    PREDICTION_CONSISTENCY_ARTIFACT,
    PREDICTION_CROSS_ASSET_ARTIFACT,
    PREDICTION_INTELLIGENCE_ARTIFACT,
    PREDICTION_PAPER_REGISTRY_ARTIFACT,
    PREDICTION_QUALITY_ARTIFACT,
    PREDICTION_RESEARCH_ARTIFACT,
    now_iso,
    public_authority,
    runtime_dir,
    stable_id,
)


def _identity(venue: str, row: dict[str, Any]) -> str | None:
    if venue == "kalshi":
        value = str(row.get("market_ticker") or row.get("event_ticker") or "")
        return f"kalshi:{value}" if value else None
    value = str(row.get("condition_id") or row.get("market_id") or "")
    outcome = str(row.get("outcome") or row.get("token_id") or "market")
    return f"polymarket:{value}:{outcome}" if value else None


def _probability(venue: str, row: dict[str, Any]) -> float | None:
    value: Any = row.get("price")
    if venue == "kalshi" and isinstance(value, dict):
        value = value.get("close") or value.get("mean")
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if result > 1.0:
        result /= 100.0
    return max(0.001, min(0.999, result))


def _number(value: Any) -> float | None:
    if isinstance(value, dict):
        value = value.get("close")
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_prediction_market_research(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[str]]:
    contracts, _, errors = normalize_prediction_contracts(settings)
    graph, graph_errors = build_prediction_contract_graph(settings)
    errors.extend(graph_errors)
    by_identity: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for venue in ("kalshi", "polymarket"):
        for row in iter_prediction_history(venue):
            identity = _identity(venue, row)
            probability = _probability(venue, row)
            if identity and probability is not None:
                by_identity[identity].append({**row, "venue": venue, "probability": probability})
    contract_by_identity = {str(row["venue_contract_identity"]): row for row in contracts}
    beliefs: list[dict[str, Any]] = []
    for identity, observations in sorted(by_identity.items()):
        contract = contract_by_identity.get(identity)
        if contract is None:
            continue
        ordered = sorted(observations, key=lambda row: str(row.get("source_available_at") or row.get("event_timestamp") or ""))
        latest = ordered[-1]
        probabilities = [float(row["probability"]) for row in ordered[-20:]]
        prior = probabilities[-2] if len(probabilities) > 1 else probabilities[-1]
        current = probabilities[-1]
        bid = _number(latest.get("yes_bid"))
        ask = _number(latest.get("yes_ask"))
        spread = ask - bid if ask is not None and bid is not None else None
        volatility = statistics.pstdev(probabilities) if len(probabilities) > 1 else 0.0
        beliefs.append({
            "schema_version": "qadam_prediction_belief_state.v1",
            "artifact_type": "qadam_prediction_belief_state",
            "belief_state_id": stable_id("prediction-belief", contract["contract_id"], latest.get("source_available_at")),
            "contract_id": contract["contract_id"],
            "venue": latest["venue"],
            "decision_time": latest.get("source_available_at") or latest.get("event_timestamp"),
            "probability": current,
            "bounded_log_odds": math.log(current / (1.0 - current)),
            "probability_change": current - prior,
            "filtered_belief_volatility": volatility,
            "jump_state": "jump" if abs(current - prior) >= 0.1 else "normal",
            "spread": spread,
            "depth": None,
            "price_impact": None,
            "activity": _number(latest.get("volume")),
            "concentration": None,
            "liquidity_regime": "measured_spread" if spread is not None else "historical_liquidity_incomplete",
            "shock_regime": "high" if volatility >= 0.15 else "normal",
            "linked_contract_constraint": "not_deterministically_verified",
            "constraint_residual": None,
            "cross_venue_compatibility": "see_contract_graph",
            "mapped_listed_instruments": contract["listed_proxy_mapping"]["symbols"],
            "economic_mechanism": contract["listed_proxy_mapping"]["mechanism"],
            "horizon": "research_specific_not_assumed",
            "missingness": [name for name, value in (("depth", None), ("price_impact", None), ("spread", spread)) if value is None],
            "staleness": "historical_archive",
            "cost_state": "direct_execution_cost_incomplete",
            "settlement_risk": "not_evaluated_for_direct_trade",
            "classification": "historical_research",
            "direct_trade_allowed": False,
            "authority": public_authority(),
        })
    belief_by_contract = {str(row["contract_id"]): row for row in beliefs}
    disagreements: list[dict[str, Any]] = []
    for edge in graph.get("edges", []):
        left = belief_by_contract.get(str(edge.get("from_contract_id")))
        right = belief_by_contract.get(str(edge.get("to_contract_id")))
        if not left or not right:
            continue
        gap = abs(float(left["probability"]) - float(right["probability"]))
        disagreements.append({
            "signal_id": stable_id("prediction-disagreement", edge.get("edge_id"), left.get("decision_time"), right.get("decision_time")),
            "edge_id": edge.get("edge_id"),
            "from_contract_id": edge.get("from_contract_id"),
            "to_contract_id": edge.get("to_contract_id"),
            "probability_gap": gap,
            "state": "historical_large_disagreement" if gap >= 0.15 else "historical_agreement",
            "liquidity_qualified": left.get("spread") is not None and right.get("spread") is not None,
            "decision_time_eligible": False,
            "strategy_nomination_allowed": False,
            "authority": public_authority(),
        })
    runtime = runtime_dir(settings)
    store = AtomicArtifactStore(runtime)
    store.write_jsonl(PREDICTION_BELIEFS_ARTIFACT, beliefs)
    paper_registry = {
        "schema_version": "qadam_prediction_market_paper_registry.v1",
        "artifact_type": "qadam_prediction_market_paper_registry",
        "generated_at": now_iso(),
        "status": "methodology_references_only",
        "papers": [
            {
                "paper_id": "arxiv:2510.15205v2",
                "title": "Toward Black-Scholes for Prediction Markets",
                "use": "Candidate probability-volatility and jump-state methodology.",
                "empirical_credit_allowed": False,
            },
            {
                "paper_id": "arxiv:2508.03474",
                "title": "Unravelling the Probabilistic Forest: Arbitrage in Prediction Markets",
                "use": "Candidate linked-contract consistency and constraint-residual methodology.",
                "empirical_credit_allowed": False,
            },
            {
                "paper_id": "arxiv:2604.10005",
                "title": "What Happens When Institutional Liquidity Enters Prediction Markets?",
                "status": "withdrawn_no_method_or_empirical_credit",
                "use": "Recorded for audit only; excluded from methods, parameters and promotion.",
                "empirical_credit_allowed": False,
            },
            {
                "paper_id": "arxiv:2603.03136v1",
                "title": "The Anatomy of Polymarket",
                "use": "Candidate transaction decomposition and venue-mechanics methodology.",
                "empirical_credit_allowed": False,
            },
        ],
        "authority": public_authority(),
    }
    quality = {
        "schema_version": "qadam_prediction_market_quality.v1",
        "artifact_type": "qadam_prediction_market_quality",
        "generated_at": now_iso(),
        "status": "historical_quality_measured",
        "contract_count": len(contracts),
        "belief_state_count": len(beliefs),
        "spread_measured_count": sum(row.get("spread") is not None for row in beliefs),
        "depth_measured_count": sum(row.get("depth") is not None for row in beliefs),
        "price_impact_measured_count": sum(row.get("price_impact") is not None for row in beliefs),
        "liquidity_complete_count": sum(not row.get("missingness") for row in beliefs),
        "decision_time_eligible_count": 0,
        "retained_onchain_activity_record_count": 0,
        "transaction_decomposition_state": "not_applicable_no_onchain_activity_records_retained",
        "naive_gross_activity_labelled_as_volume_count": 0,
        "withdrawn_paper_empirical_credit_count": 0,
        "direct_trade_allowed": False,
        "authority": public_authority(),
    }
    cross_asset_signals = [
        {
            **row,
            "mapped_instruments": sorted(
                {
                    symbol
                    for endpoint in (belief_by_contract.get(str(row.get("from_contract_id"))), belief_by_contract.get(str(row.get("to_contract_id"))))
                    if endpoint
                    for symbol in endpoint.get("mapped_listed_instruments") or []
                }
            ),
        }
        for row in disagreements
        if row.get("liquidity_qualified") is True and row.get("decision_time_eligible") is True
    ]
    store.write_json(PREDICTION_PAPER_REGISTRY_ARTIFACT, paper_registry)
    store.write_json(PREDICTION_QUALITY_ARTIFACT, quality)
    store.write_jsonl(PREDICTION_CONSISTENCY_ARTIFACT, disagreements)
    store.write_jsonl(PREDICTION_CROSS_ASSET_ARTIFACT, cross_asset_signals)
    research = {
        "schema_version": "qadam_prediction_market_research.v1",
        "artifact_type": "qadam_prediction_market_research",
        "generated_at": now_iso(),
        "status": "historical_research_ready_direct_execution_disabled",
        "contract_count": len(contracts),
        "belief_state_count": len(beliefs),
        "cross_venue_candidate_edge_count": len(graph.get("edges", [])),
        "disagreement_record_count": len(disagreements),
        "disagreement_count": len(disagreements),
        "large_disagreement_count": sum(row["state"] == "historical_large_disagreement" for row in disagreements),
        "liquidity_qualified_disagreement_count": sum(bool(row["liquidity_qualified"]) for row in disagreements),
        "disagreements": disagreements[:100],
        "negative_controls_required_before_promotion": True,
        "direct_prediction_market_trade_allowed": False,
        "unrelated_alpaca_proxy_mapping_allowed": False,
        "strategy_nomination_count": 0,
        "validation_errors": sorted(set(errors)),
        "authority": public_authority(),
    }
    store.write_json(PREDICTION_RESEARCH_ARTIFACT, research)
    store.write_json(
        PREDICTION_INTELLIGENCE_ARTIFACT,
        {
            "schema_version": "qadam_prediction_market_intelligence_summary.v1",
            "artifact_type": "qadam_prediction_market_intelligence_summary",
            "generated_at": now_iso(),
            "status": "research_only_no_qualified_strategy_nomination",
            "contract_count": len(contracts),
            "belief_state_count": len(beliefs),
            "consistency_record_count": len(disagreements),
            "large_disagreement_count": research["large_disagreement_count"],
            "liquidity_qualified_disagreement_count": research["liquidity_qualified_disagreement_count"],
            "cross_asset_signal_count": len(cross_asset_signals),
            "strategy_nomination_count": 0,
            "why_not_promoted": (
                "Historical records do not yet provide complete decision-time liquidity, "
                "cost and forward-outcome evidence for a listed-market strategy."
            ),
            "direct_prediction_market_trade_allowed": False,
            "authority": public_authority(),
        },
    )
    return research, sorted(set(errors))


__all__ = ["build_prediction_market_research"]
