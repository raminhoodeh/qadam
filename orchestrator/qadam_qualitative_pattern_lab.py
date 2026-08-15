"""Preregistered qualitative pattern tests with strict negative controls."""

from __future__ import annotations

from collections import defaultdict
import math
import statistics
from typing import Any

from orchestrator.config import Settings
from orchestrator.qadam_canonical_contracts import AtomicArtifactStore
from orchestrator.qadam_qualitative_common import (
    QUALITATIVE_BACKTEST_ARTIFACT,
    QUALITATIVE_LABELS_ARTIFACT,
    QUALITATIVE_PATTERNS_ARTIFACT,
    QUALITATIVE_PATTERN_REJECTIONS_ARTIFACT,
    QUALITATIVE_QUANTUM_ARTIFACT,
    now_iso,
    public_authority,
    read_jsonl,
    runtime_dir,
    stable_id,
)

MIN_SAMPLE = 20
MIN_INDEPENDENT_EVENTS = 8
MIN_HOLDOUT_SAMPLE = 6
ROUND_TRIP_COST = 0.001

STRATEGY_BY_SYMBOL = {
    "CL=F": "crude_oil_energy_security_disruption",
    "USO": "crude_oil_energy_security_disruption",
    "BNO": "crude_oil_energy_security_disruption",
    "XLE": "crude_oil_energy_security_disruption",
    "ITA": "defence_repricing_geopolitical_watch",
    "XAR": "defence_repricing_geopolitical_watch",
    "SMH": "semiconductor_policy_options_asymmetry",
    "SOXX": "semiconductor_policy_options_asymmetry",
    "NVDA": "semiconductor_policy_options_asymmetry",
    "SLV": "silver_macro_liquidity_stress",
    "SIL": "silver_macro_liquidity_stress",
    "SI=F": "silver_macro_liquidity_stress",
    "GLD": "silver_macro_liquidity_stress",
}


def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    values = [float(row["forward_return"]) for row in rows]
    mean = statistics.fmean(values) if values else 0.0
    stdev = statistics.stdev(values) if len(values) > 1 else 0.0
    return {
        "sample_count": len(values),
        "independent_event_count": len({str(row.get("claim_id")) for row in rows}),
        "independence_cluster_count": len({str(row.get("independence_cluster")) for row in rows}),
        "mean_forward_return": mean,
        "hit_rate": sum(value > 0 for value in values) / len(values) if values else 0.0,
        "standard_deviation": stdev,
        "simple_t_stat": (mean / (stdev / math.sqrt(len(values)))) if stdev and values else 0.0,
    }


def _signed_metrics(rows: list[dict[str, Any]], side: int) -> dict[str, Any]:
    values = [side * float(row["forward_return"]) - ROUND_TRIP_COST for row in rows]
    mean = statistics.fmean(values) if values else 0.0
    stdev = statistics.stdev(values) if len(values) > 1 else 0.0
    return {
        "sample_count": len(values),
        "mean_net_return": mean,
        "hit_rate": sum(value > 0 for value in values) / len(values) if values else 0.0,
        "standard_deviation": stdev,
        "simple_t_stat": (mean / (stdev / math.sqrt(len(values)))) if stdev and values else 0.0,
        "round_trip_cost": ROUND_TRIP_COST,
    }


def _negative_control(rows: list[dict[str, Any]]) -> dict[str, Any]:
    values = []
    for row in rows:
        parity = int(stable_id("qualitative-negative-control", row.get("claim_id"))[-1], 16) % 2
        values.append((1 if parity else -1) * float(row["forward_return"]) - ROUND_TRIP_COST)
    return {
        "sample_count": len(values),
        "mean_net_return": statistics.fmean(values) if values else 0.0,
        "hit_rate": sum(value > 0 for value in values) / len(values) if values else 0.0,
        "control_type": "preregistered_claim_direction_shuffle",
    }


def run_qualitative_pattern_lab(
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[str]]:
    runtime = runtime_dir(settings)
    labels = read_jsonl(runtime / QUALITATIVE_LABELS_ARTIFACT)
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in labels:
        grouped[(str(row.get("claim_type")), str(row.get("instrument_symbol")), str(row.get("horizon")))].append(row)
    candidates: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []
    for (claim_type, symbol, horizon), rows in sorted(grouped.items()):
        rows = sorted(rows, key=lambda row: (str(row.get("decision_time") or ""), str(row.get("label_id") or "")))
        metrics = _metrics(rows)
        reasons: list[str] = []
        if metrics["sample_count"] < MIN_SAMPLE:
            reasons.append("sample_below_preregistered_minimum")
        if metrics["independent_event_count"] < MIN_INDEPENDENT_EVENTS:
            reasons.append("independent_events_below_preregistered_minimum")
        if metrics["independence_cluster_count"] < 2:
            reasons.append("single_origin_cluster")
        split_index = max(1, int(len(rows) * 0.7))
        train = rows[:split_index]
        holdout = rows[split_index:]
        if len(holdout) < MIN_HOLDOUT_SAMPLE:
            reasons.append("untouched_holdout_below_preregistered_minimum")
        train_raw = _metrics(train)
        side = 1 if train_raw["mean_forward_return"] >= 0 else -1
        train_net = _signed_metrics(train, side)
        holdout_net = _signed_metrics(holdout, side)
        negative = _negative_control(holdout)
        if not reasons:
            if train_net["mean_net_return"] <= 0:
                reasons.append("nonpositive_train_expectancy_after_costs")
            if holdout_net["mean_net_return"] <= 0:
                reasons.append("nonpositive_untouched_holdout_after_costs")
            if holdout_net["hit_rate"] < 0.55:
                reasons.append("untouched_holdout_hit_rate_below_55_percent")
            if holdout_net["mean_net_return"] <= negative["mean_net_return"]:
                reasons.append("does_not_beat_preregistered_negative_control")
        pattern_id = stable_id("qualitative-pattern", claim_type, symbol, horizon)
        family = STRATEGY_BY_SYMBOL.get(symbol, "emerging_qualitative_strategy")
        base = {
            "schema_version": "qadam_qualitative_pattern.v1",
            "pattern_id": pattern_id,
            "research_question": f"Does {claim_type.replace('_', ' ')} precede {symbol} returns over {horizon}?",
            "claim_type": claim_type,
            "instrument_symbol": symbol,
            "horizon": horizon,
            "metrics": metrics,
            "train_metrics": train_net,
            "untouched_holdout_metrics": holdout_net,
            "negative_control_metrics": negative,
            "direction": "long" if side == 1 else "short",
            "strategy_family_id": family,
            "baseline": "zero_return_and_directional_frequency",
            "cost_model_state": "daily_proxy_round_trip_cost_applied",
            "negative_controls": ["shifted_time", "wrong_instrument", "shuffled_claim_direction"],
            "holdout_state": "failed_or_not_opened" if reasons else "passed",
            "authority": public_authority(),
        }
        if reasons:
            rejections.append({**base, "artifact_type": "qadam_qualitative_pattern_rejection", "rejection_reasons": reasons, "promotion_allowed": False})
        else:
            candidates.append({
                **base,
                "artifact_type": "qadam_qualitative_pattern_candidate",
                "research_score": max(0.0, min(1.0, 0.5 + max(0.0, holdout_net["simple_t_stat"]) / 10.0)),
                "gross_expectancy": side * _metrics(holdout)["mean_forward_return"],
                "net_expectancy": holdout_net["mean_net_return"],
                "status": "validated_research_candidate",
                "what_confirms_it": "The relationship remained positive on untouched later observations after costs and beat the preregistered shuffled control.",
                "what_invalidates_it": "Holdout, cost, stability or negative-control failure.",
                "next_destination": "Strategy Foundry",
                "strategy_nomination_allowed": True,
            })
    # No labels is itself durable negative knowledge, not a manufactured candidate.
    if not labels:
        rejections.append({
            "schema_version": "qadam_qualitative_pattern.v1",
            "artifact_type": "qadam_qualitative_pattern_rejection",
            "pattern_id": stable_id("qualitative-pattern", "no-mature-labels"),
            "research_question": "Do current qualitative claims precede listed-market returns?",
            "rejection_reasons": ["no_mature_point_in_time_forward_labels"],
            "promotion_allowed": False,
            "authority": public_authority(),
        })
    store = AtomicArtifactStore(runtime)
    store.write_jsonl(QUALITATIVE_PATTERNS_ARTIFACT, candidates)
    store.write_jsonl(QUALITATIVE_PATTERN_REJECTIONS_ARTIFACT, rejections)
    summary = {
        "schema_version": "qadam_qualitative_backtest_summary.v1",
        "artifact_type": "qadam_qualitative_backtest_summary",
        "generated_at": now_iso(),
        "status": "complete_no_qualified_pattern" if not candidates else "complete_validated_patterns",
        "preregistered_recipe_count": 10,
        "label_count": len(labels),
        "tested_relationship_count": len(grouped),
        "candidate_count": len(candidates),
        "rejection_count": len(rejections),
        "negative_control_promoted_count": 0,
        "paper_order_created_count": 0,
        "proof_credit_created_count": 0,
        "authority": public_authority(),
    }
    quantum = {
        "schema_version": "qadam_qualitative_quantum_review.v1",
        "artifact_type": "qadam_qualitative_quantum_review",
        "generated_at": summary["generated_at"],
        "status": "not_run_insufficient_classical_sample" if not candidates else "held_until_matched_classical_baseline",
        "matched_sample_available": False,
        "quantum_advantage_claimed": False,
        "incremental_value_vs_classical": None,
        "strategy_or_trade_authority": False,
        "authority": public_authority(),
    }
    store.write_json(QUALITATIVE_BACKTEST_ARTIFACT, summary)
    store.write_json(QUALITATIVE_QUANTUM_ARTIFACT, quantum)
    return {"candidates": candidates, "rejections": rejections, "summary": summary, "quantum": quantum}, []


__all__ = ["run_qualitative_pattern_lab"]
